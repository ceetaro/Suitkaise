"""
Skprocess base class for subprocess-based task execution.

Users inherit from Skprocess, define lifecycle methods, and the engine
handles running, timing, error recovery, and subprocess management.
"""

import asyncio
import multiprocessing
import queue as queue_module
from typing import Any, TYPE_CHECKING

from .config import ProcessConfig
from .timers import ProcessTimers
from .errors import ResultTimeoutError
from suitkaise.sk._int.asyncable import _ModifiableMethod

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event
    from multiprocessing import Queue
    from suitkaise.timing import Sktimer


class TimedMethod:
    """
    Wrapper for lifecycle methods that provides a .timer attribute.
    
    Usage:
        p = MyProcess()
        p.start()
        p.wait()
        
        # Access timing data
        print(p.__run__.timer.mean)
        print(p.__prerun__.timer.total)
    """
    
    def __init__(self, method, process: "Skprocess", timer_name: str):
        self._method = method
        self._process = process
        self._timer_name = timer_name
    
    def __call__(self, *args, **kwargs):
        return self._method(*args, **kwargs)
    
    @property
    def timer(self) -> "Sktimer | None":
        """Get the timer for this method, or None if not yet timed."""
        if self._process.timers is None:
            return None
        return getattr(self._process.timers, self._timer_name, None)


class Skprocess:
    """
    Base class for subprocess-based process execution.
    
    Inherit from this class and implement lifecycle methods:
    - __prerun__(): Called before each run iteration
    - __run__(): Main work (required) - called each iteration
    - __postrun__(): Called after each run iteration  
    - __onfinish__(): Called when process ends (stop/limit reached)
    - __result__(): Return data when process completes
    - __error__(): Handle errors when all lives exhausted
    
    Usage:
        class MyProcess(Skprocess):
            def __init__(self):
                self.counter = 0
                self.process_config.runs = 10
            
            def __run__(self):
                self.counter += 1
            
            def __result__(self):
                return self.counter
        
        process = MyProcess()
        process.start()
        process.wait()
        result = process.result
        
        # Access timing (automatic for any lifecycle method you define)
        print(process.__run__.timer.mean)
    """
    
    # Class-level attribute declarations for type checking
    process_config: ProcessConfig
    timers: ProcessTimers | None
    process_timer: "Sktimer | None"  # Alias for full_run timer
    error: BaseException | None
    _current_run: int
    _start_time: float | None
    _stop_event: "Event | None"
    _result_queue: "Queue[Any] | None"
    _tell_queue: "Queue[Any] | None"  # Parent → Child communication
    _listen_queue: "Queue[Any] | None"  # Child → Parent communication
    _subprocess: multiprocessing.Process | None
    _result: Any
    _has_result: bool
    
    # Class-level flag to track if __init_subclass__ should wrap __init__
    _is_base_class = True
    
    # Internal attribute names (used for serialization filtering)
    _INTERNAL_ATTRS = frozenset({
        'process_config', 'timers', 'error', '_current_run', '_start_time',
        '_stop_event', '_result_queue', '_tell_queue', '_listen_queue',
        '_subprocess', '_result', '_has_result', '_timed_methods',
    })
    
    def __init_subclass__(cls, **kwargs):
        """
        Automatically wrap subclass __init__ to call parent setup first.
        
        This means users don't need to call super().__init__() - it happens
        automatically before their __init__ runs.
        
        Also handles serialization for cerial:
        - If user defined __serialize__/__deserialize__, we wrap them to include
          Skprocess internals (lifecycle methods, class attrs) while preserving
          user's custom state.
        - If not defined, we provide Skprocess's serialization methods.
        """
        super().__init_subclass__(**kwargs)
        
        # Only wrap if this class defines its own __init__
        if '__init__' in cls.__dict__:
            original_init = cls.__dict__['__init__']
            
            def wrapped_init(self, *args, **kwargs):
                # Run parent setup first
                Skprocess._setup(self)
                # Then run user's __init__
                original_init(self, *args, **kwargs)
            
            # Preserve function metadata
            wrapped_init.__name__ = original_init.__name__
            wrapped_init.__doc__ = original_init.__doc__
            cls.__init__ = wrapped_init
        else:
            # No __init__ defined, but we still need setup to run
            def default_init(self, *args, **kwargs):
                Skprocess._setup(self)
            
            cls.__init__ = default_init
        
        # Handle serialization methods for cerial compatibility.
        # cerial requires these to be in the class's own __dict__ (not inherited)
        # for locally-defined classes.
        #
        # IMPORTANT: cerial handles locally-defined vs module-level classes differently:
        # - Locally-defined (has <locals> in qualname): requires staticmethod with (cls, state) signature
        #   cerial calls: deserialize_func(cls, state["custom_state"])
        # - Module-level: expects classmethod with (state) signature (cls is implicit)
        #   cerial calls: cls.__deserialize__(state["custom_state"])
        #
        # If user defined their own __serialize__/__deserialize__, we capture them
        # and wrap to include Skprocess internals alongside user's custom state.
        
        user_serialize = cls.__dict__.get('__serialize__')
        user_deserialize = cls.__dict__.get('__deserialize__')
        
        # Create the __serialize__ method that handles both Skprocess state and user state
        def make_serialize(user_ser):
            def __serialize__(self):
                return Skprocess._serialize_with_user(self, user_ser)
            return __serialize__
        
        cls.__serialize__ = make_serialize(user_serialize)
        
        # Determine if this is a locally-defined class
        is_local = "<locals>" in cls.__qualname__
        
        if is_local:
            # For locally-defined classes: staticmethod with (cls, state) signature
            # cerial calls: deserialize_func(cls, state["custom_state"])
            def make_deserialize_static(user_deser):
                def __deserialize__(reconstructed_cls, state):
                    return Skprocess._deserialize_with_user(reconstructed_cls, state, user_deser)
                return staticmethod(__deserialize__)
            
            cls.__deserialize__ = make_deserialize_static(user_deserialize)
        else:
            # For module-level classes: classmethod with (state) signature (cls is implicit)
            # cerial calls: cls.__deserialize__(state["custom_state"])
            def make_deserialize_classmethod(user_deser):
                @classmethod
                def __deserialize__(inner_cls, state):
                    return Skprocess._deserialize_with_user(inner_cls, state, user_deser)
                return __deserialize__
            
            cls.__deserialize__ = make_deserialize_classmethod(user_deserialize)
    
    # =========================================================================
    # Serialization support for cerial
    # =========================================================================
    
    # Lifecycle method names that need to be captured during serialization
    _LIFECYCLE_METHODS = (
        '__prerun__', '__run__', '__postrun__', 
        '__onfinish__', '__result__', '__error__'
    )
    
    @staticmethod
    def _serialize_with_user(instance: "Skprocess", user_serialize=None) -> dict:
        """
        Serialize this Skprocess instance for cerial.
        
        Captures:
        - Instance __dict__ (all instance attributes)
        - Lifecycle methods defined on the subclass
        - Class name for reconstruction
        - User's custom state if they defined __serialize__
        
        Args:
            instance: The Skprocess instance to serialize
            user_serialize: User's __serialize__ method (if they defined one)
        """
        cls = instance.__class__
        
        # Capture lifecycle methods defined on THIS class (not inherited from Skprocess)
        lifecycle_methods = {}
        for name in Skprocess._LIFECYCLE_METHODS:
            if name in cls.__dict__:
                # This is a method defined on the subclass
                lifecycle_methods[name] = cls.__dict__[name]
        
        # Capture any other class-level attributes (non-dunder, non-private)
        class_attrs = {}
        for name, value in cls.__dict__.items():
            if name.startswith('_'):
                continue
            if name in lifecycle_methods:
                continue
            # Include class variables, but not inherited stuff
            class_attrs[name] = value
        
        # Prepare instance dict, excluding TimedMethod wrappers
        # (they'll be recreated on deserialization)
        instance_dict = {}
        for key, value in instance.__dict__.items():
            if isinstance(value, TimedMethod):
                continue
            instance_dict[key] = value
        
        state = {
            'instance_dict': instance_dict,
            'class_name': cls.__name__,
            'lifecycle_methods': lifecycle_methods,
            'class_attrs': class_attrs,
        }
        
        # If user defined their own __serialize__, call it and include that state
        if user_serialize is not None:
            state['user_custom_state'] = user_serialize(instance)
            state['has_user_serialize'] = True
        
        return state
    
    @staticmethod
    def _deserialize_with_user(reconstructed_cls: type, state: dict, user_deserialize=None) -> "Skprocess":
        """
        Deserialize a Skprocess instance from cerial state.
        
        Args:
            reconstructed_cls: The class cerial reconstructed (we ignore this and build our own)
            state: The serialized state dict
            user_deserialize: User's __deserialize__ method (if they defined one)
        
        Recreates the subclass dynamically with type() and restores state.
        If user had custom deserialize, applies it after Skprocess reconstruction.
        """
        # Build class dict with lifecycle methods and class attributes
        class_dict = {}
        class_dict.update(state.get('class_attrs', {}))
        class_dict.update(state['lifecycle_methods'])
        
        # Create the subclass dynamically
        # Note: This triggers __init_subclass__ which sets up __init__ wrapping
        new_class = type(
            state['class_name'],
            (Skprocess,),
            class_dict
        )
        
        # Create instance without calling __init__
        # We bypass __init__ because we're restoring state directly
        obj = object.__new__(new_class)
        
        # Restore instance state directly (includes config, timers, etc.)
        obj.__dict__.update(state['instance_dict'])
        
        # Set up timed method wrappers
        Skprocess._setup_timed_methods(obj)
        
        # If user defined their own __deserialize__, apply it now
        if state.get('has_user_serialize') and user_deserialize is not None:
            # User's __deserialize__ should be a classmethod that takes (cls, state)
            # We call it with the user's custom state portion
            user_state = state.get('user_custom_state', {})
            
            # Handle both classmethod and staticmethod signatures
            # The user_deserialize we captured is the raw method/function
            if isinstance(user_deserialize, classmethod):
                # It's already a classmethod descriptor, extract the function
                user_func = user_deserialize.__func__
                user_result = user_func(new_class, user_state)
            elif isinstance(user_deserialize, staticmethod):
                # It's a staticmethod, extract and call with (cls, state)
                user_func = user_deserialize.__func__
                user_result = user_func(new_class, user_state)
            else:
                # Regular function or unbound method - try calling as classmethod-style
                try:
                    user_result = user_deserialize(new_class, user_state)
                except TypeError:
                    # Maybe it just expects state
                    user_result = user_deserialize(user_state)
            
            # If user's __deserialize__ returned an object, use it to update our obj
            # This allows user to restore their custom attributes
            if user_result is not None and hasattr(user_result, '__dict__'):
                # Merge user's restored attributes into our obj
                for key, value in user_result.__dict__.items():
                    if key not in obj.__dict__:
                        obj.__dict__[key] = value
        
        return obj
    
    # Fallback for direct calls on Skprocess base class
    def __serialize__(self) -> dict:
        """Serialize this Skprocess instance (base class fallback)."""
        return Skprocess._serialize_with_user(self, None)
    
    @classmethod
    def __deserialize__(cls, state: dict) -> "Skprocess":
        """Deserialize for module-level classes (base class fallback)."""
        return Skprocess._deserialize_with_user(cls, state, None)
    
    # =========================================================================
    # Internal setup
    # =========================================================================
    
    @staticmethod
    def _setup(instance: "Skprocess") -> None:
        """
        Initialize internal process state.
        
        Called automatically before user's __init__.
        """
        # Configuration with defaults
        instance.process_config = ProcessConfig()
        
        # Timers container (created when needed)
        instance.timers = None
        
        # Runtime state
        instance._current_run = 0
        instance._start_time = None
        
        # Error state (set when error occurs, used by __error__)
        instance.error = None
        
        # Communication primitives (created on start())
        instance._stop_event = None
        instance._result_queue = None
        instance._tell_queue = None  # Parent → Child
        instance._listen_queue = None  # Child → Parent
        
        # Subprocess handle
        instance._subprocess = None
        
        # Result storage (populated after process completes)
        instance._result = None
        instance._has_result = False
        
        # Set up timed method wrappers
        Skprocess._setup_timed_methods(instance)
    
    @staticmethod
    def _setup_timed_methods(instance: "Skprocess") -> None:
        """
        Create TimedMethod wrappers for user-defined lifecycle methods.
        
        This enables access like process.__run__.timer
        """
        cls = instance.__class__
        
        method_to_timer = {
            '__prerun__': 'prerun',
            '__run__': 'run',
            '__postrun__': 'postrun',
            '__onfinish__': 'onfinish',
            '__result__': 'result',
            '__error__': 'error',
        }
        
        for method_name, timer_name in method_to_timer.items():
            # Check if user defined this method (not just inherited from Skprocess)
            if method_name in cls.__dict__:
                # Get the actual method
                method = getattr(instance, method_name)
                # Create wrapper
                wrapper = TimedMethod(method, instance, timer_name)
                # Store as instance attribute (shadows class method)
                setattr(instance, method_name, wrapper)
    
    # =========================================================================
    # Lifecycle methods (override these in subclass)
    # =========================================================================
    
    def __prerun__(self) -> None:
        """Called before each __run__() iteration. Override in subclass."""
        pass
    
    def __run__(self) -> None:
        """Main work method. Called each iteration. Override in subclass."""
        pass
    
    def __postrun__(self) -> None:
        """Called after each __run__() iteration. Override in subclass."""
        pass
    
    def __onfinish__(self) -> None:
        """Called when process ends (stop/limit reached). Override in subclass."""
        pass
    
    def __result__(self) -> Any:
        """Return data when process completes. Override in subclass."""
        return None
    
    def __error__(self) -> Any:
        """
        Handle errors when all lives exhausted.
        
        Default: returns the error, which will be raised by result property.
        Override to add logging, cleanup, or custom error transformation.
        """
        return self.error
    
    # =========================================================================
    # Control methods (called from parent process)
    # =========================================================================
    
    def start(self) -> None:
        """
        Start the process in a new subprocess.
        
        Serializes this Skprocess object, spawns a subprocess, and runs
        the engine there.
        """
        # Import here to avoid circular imports
        from .engine import _engine_main
        from suitkaise import cerial
        
        # Ensure timers exist
        if self.timers is None:
            self.timers = ProcessTimers()
        
        # Serialize current state
        serialized = cerial.serialize(self)
        
        # Save original state for retries (lives system)
        original_state = serialized
        
        # Create communication primitives
        self._stop_event = multiprocessing.Event()
        self._result_queue = multiprocessing.Queue()
        self._tell_queue = multiprocessing.Queue()  # Parent → Child
        self._listen_queue = multiprocessing.Queue()  # Child → Parent
        
        # Record start time
        from suitkaise import sktime
        self._start_time = sktime.time()
        
        # Spawn subprocess
        self._subprocess = multiprocessing.Process(
            target=_engine_main,
            args=(serialized, self._stop_event, self._result_queue, 
                  original_state, self._tell_queue, self._listen_queue)
        )
        self._subprocess.start()
    
    def stop(self) -> None:
        """
        Signal the process to stop gracefully.
        
        Does NOT block - returns immediately after setting the stop signal.
        The process will finish its current section, run __onfinish__(),
        and send its result back.
        
        Use wait() after stop() if you need to block until finished.
        """
        if self._stop_event is not None:
            self._stop_event.set()
    
    def kill(self) -> None:
        """
        Forcefully terminate the process immediately.
        
        Bypasses the lives system - process is killed immediately.
        No cleanup, no __onfinish__, no result. The process is just killed.
        """
        if self._subprocess is not None and self._subprocess.is_alive():
            self._subprocess.terminate()
            self._subprocess.join(timeout=5)
            
            # If still alive after terminate, force kill
            if self._subprocess.is_alive():
                self._subprocess.kill()
    
    # -------------------------------------------------------------------------
    # Async wait implementation for modifiers
    # -------------------------------------------------------------------------
    
    async def _async_wait(self, timeout: float | None = None) -> bool:
        """Async implementation of wait()."""
        return await asyncio.to_thread(self._sync_wait, timeout)
    
    def _sync_wait(self, timeout: float | None = None) -> bool:
        """
        Wait for the process to finish.
        
        Blocks until the process completes successfully. If the process
        crashes and has lives remaining, wait() continues blocking during
        the restart - it only returns when the process finishes (success
        or out of lives).
        
        Args:
            timeout: Maximum seconds to wait. None = wait forever.
        
        Returns:
            True if process finished, False if timeout reached.
        """
        if self._subprocess is None:
            return True
        
        # Must drain result queue BEFORE waiting for subprocess
        # Otherwise deadlock: subprocess can't exit until queue is drained,
        # but we can't drain until subprocess exits
        self._drain_result_queue()
        
        self._subprocess.join(timeout=timeout)
        return not self._subprocess.is_alive()
    
    wait = _ModifiableMethod(
        _sync_wait,
        _async_wait,
        timeout_error=ResultTimeoutError,
        has_timeout_modifier=False,
        has_background_modifier=False,
        has_retry_modifier=False,
    )
    """
    ────────────────────────────────────────────────────────
        ```python
        # Sync - blocks until finished
        finished = process.wait()
        finished = process.wait(timeout=10.0)
        
        # Async - await in async code
        finished = await process.wait.asynced()()
        ```
    ────────────────────────────────────────────────────────
    
    Wait for the process to finish.
    
    Blocks until the process completes successfully. If the process
    crashes and has lives remaining, wait() continues blocking during
    the restart - it only returns when the process finishes (success
    or out of lives).
    
    Args:
        timeout: Maximum seconds to wait. None = wait forever.
    
    Returns:
        True if process finished, False if timeout reached.
    
    Modifiers:
        .asynced(): Return coroutine for await
    """
    
    def _drain_result_queue(self) -> None:
        """
        Read result from queue and store internally.
        
        This allows the subprocess's QueueFeederThread to complete,
        which allows the subprocess to exit cleanly.
        """
        if self._has_result or self._result_queue is None:
            return
        
        from suitkaise import cerial
        import queue as queue_module
        
        try:
            # Use short timeout for polling - subprocess may still be producing
            message = self._result_queue.get(timeout=1.0)
            
            # Update timers from subprocess
            if 'timers' in message and message['timers'] is not None:
                self.timers = cerial.deserialize(message['timers'])
                Skprocess._setup_timed_methods(self)
            
            if message["type"] == "error":
                error_data = cerial.deserialize(message["data"])
                # If __error__() returned a non-exception, wrap it
                if isinstance(error_data, BaseException):
                    self._result = error_data
                else:
                    # Create a generic ProcessError wrapping the error info
                    from .errors import ProcessError
                    self._result = ProcessError(f"Process failed: {error_data}")
            else:
                self._result = cerial.deserialize(message["data"])
            
            self._has_result = True
        except queue_module.Empty:
            # No result yet - subprocess may still be running
            pass
    
    # -------------------------------------------------------------------------
    # Async result implementation for modifiers
    # -------------------------------------------------------------------------
    
    async def _async_result(self) -> Any:
        """Async implementation of result()."""
        await asyncio.to_thread(self.wait)
        
        if self._has_result:
            if isinstance(self._result, BaseException):
                raise self._result
            return self._result
        
        return None
    
    def _sync_result(self) -> Any:
        """
        Get the result from the process.
        
        Blocks until the process finishes if not already done.
        If the process crashes and has lives remaining, this continues
        blocking during restarts.
        
        Returns:
            Whatever __result__() returned.
        
        Raises:
            ProcessError: If the process failed (after exhausting lives).
        """
        # Wait drains the queue and stores result
        self.wait()
        
        if self._has_result:
            if isinstance(self._result, BaseException):
                raise self._result
            return self._result
        
        # No result retrieved - subprocess may have crashed silently
        return None
    
    result = _ModifiableMethod(
        _sync_result,
        _async_result,
        timeout_error=ResultTimeoutError,
        has_retry_modifier=False,
    )
    """
    ────────────────────────────────────────────────────────
        ```python
        # Sync - blocks until result ready
        data = process.result()
        
        # With timeout - raises ProcessTimeoutError if exceeded
        data = process.result.timeout(10.0)()
        
        # Background - returns Future immediately
        future = process.result.background()()
        # ... do other work ...
        data = future.result()
        
        # Async - await in async code
        data = await process.result.asynced()()
        ```
    ────────────────────────────────────────────────────────
    
    Get the result from the process.
    
    Blocks until the process finishes if not already done.
    If the process crashes and has lives remaining, this continues
    blocking during restarts.
    
    Returns:
        Whatever __result__() returned.
    
    Raises:
        ProcessError: If the process failed (after exhausting lives).
    
    Modifiers:
        .timeout(seconds): Raise ProcessTimeoutError if exceeded
        .background(): Return Future immediately
        .asynced(): Return coroutine for await
    """
    
    def tell(self, data: Any) -> None:
        """
        Send data to the subprocess.
        
        If the subprocess calls listen(), it will receive this data.
        This method is non-blocking - returns immediately after queuing the data.
        
        Args:
            data: Any serializable data to send to the subprocess.
        """
        if self._tell_queue is None:
            raise RuntimeError("Cannot tell() - process not started")
        
        from suitkaise import cerial
        serialized = cerial.serialize(data)
        self._tell_queue.put(serialized)
    
    # -------------------------------------------------------------------------
    # Async listen implementation for modifiers
    # -------------------------------------------------------------------------
    
    async def _async_listen(self, timeout: float | None = None) -> Any:
        """Async implementation of listen()."""
        return await asyncio.to_thread(self._sync_listen, timeout)
    
    def _sync_listen(self, timeout: float | None = None) -> Any:
        """
        Receive data from the subprocess.
        
        Blocks until data is received from the subprocess via tell().
        
        Args:
            timeout: Maximum seconds to wait. None = wait forever.
        
        Returns:
            The data sent by the subprocess, or None if timeout reached.
        """
        if self._listen_queue is None:
            raise RuntimeError("Cannot listen() - process not started")
        
        from suitkaise import cerial
        
        try:
            serialized = self._listen_queue.get(timeout=timeout)
            return cerial.deserialize(serialized)
        except queue_module.Empty:
            return None
    
    listen = _ModifiableMethod(
        _sync_listen,
        _async_listen,
        timeout_error=ResultTimeoutError,
        has_timeout_modifier=False,
    )
    """
    ────────────────────────────────────────────────────────
        ```python
        # Sync - blocks until data received
        data = process.listen()
        data = process.listen(timeout=5.0)
        
        # Background - returns Future immediately
        future = process.listen.background()()
        
        # Async - await in async code
        data = await process.listen.asynced()()
        ```
    ────────────────────────────────────────────────────────
    
    Receive data from the subprocess.
    
    Blocks until data is received from the subprocess via tell().
    
    Args:
        timeout: Maximum seconds to wait. None = wait forever.
    
    Returns:
        The data sent by the subprocess, or None if timeout reached.
    
    Modifiers:
        .background(): Return Future immediately
        .asynced(): Return coroutine for await
    """
    
    @property
    def process_timer(self) -> "Sktimer | None":
        """
        Get the aggregate timer for full run iterations.
        
        This timer accumulates the total time for each complete iteration
        (prerun + run + postrun combined).
        """
        if self.timers is None:
            return None
        return self.timers.full_run
    
    @property
    def current_run(self) -> int:
        """Current run iteration number (0-indexed)."""
        return self._current_run
    
    @property
    def is_alive(self) -> bool:
        """Whether the subprocess is currently running."""
        return self._subprocess is not None and self._subprocess.is_alive()
