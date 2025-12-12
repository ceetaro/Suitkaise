"""
Process base class for subprocess-based task execution.

Users inherit from Process, define lifecycle methods, and the engine
handles looping, timing, error recovery, and subprocess management.
"""

import multiprocessing
from typing import Any, TYPE_CHECKING

from .config import ProcessConfig
from .timers import ProcessTimers

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event
    from multiprocessing import Queue


class Process:
    """
    Base class for subprocess-based process execution.
    
    Inherit from this class and implement lifecycle methods:
    - __preloop__(): Called before each loop iteration
    - __loop__(): Main work (required) - called each iteration
    - __postloop__(): Called after each loop iteration  
    - __onfinish__(): Called when process ends (stop/limit reached)
    - __result__(): Return data when process completes
    - __error__(): Handle errors when all lives exhausted
    
    Usage:
        class MyProcess(Process):
            def __init__(self):
                self.counter = 0
                self.config.num_loops = 10
            
            def __loop__(self):
                self.counter += 1
            
            def __result__(self):
                return self.counter
        
        process = MyProcess()
        process.start()
        process.wait()
        result = process.result
    """
    
    # Class-level attribute declarations for type checking
    config: ProcessConfig
    timers: ProcessTimers | None
    error: BaseException | None
    _current_lap: int
    _start_time: float | None
    _stop_event: "Event | None"
    _result_queue: "Queue[Any] | None"
    _subprocess: multiprocessing.Process | None
    _result: Any
    _has_result: bool
    
    # Class-level flag to track if __init_subclass__ should wrap __init__
    _is_base_class = True
    
    def __init_subclass__(cls, **kwargs):
        """
        Automatically wrap subclass __init__ to call parent setup first.
        
        This means users don't need to call super().__init__() - it happens
        automatically before their __init__ runs.
        
        Also handles serialization for cerial:
        - If user defined __serialize__/__deserialize__, we wrap them to include
          Process internals (lifecycle methods, class attrs) while preserving
          user's custom state.
        - If not defined, we provide Process's serialization methods.
        """
        super().__init_subclass__(**kwargs)
        
        # Only wrap if this class defines its own __init__
        if '__init__' in cls.__dict__:
            original_init = cls.__dict__['__init__']
            
            def wrapped_init(self, *args, **kwargs):
                # Run parent setup first
                Process._setup(self)
                # Then run user's __init__
                original_init(self, *args, **kwargs)
            
            # Preserve function metadata
            wrapped_init.__name__ = original_init.__name__
            wrapped_init.__doc__ = original_init.__doc__
            cls.__init__ = wrapped_init
        else:
            # No __init__ defined, but we still need setup to run
            def default_init(self, *args, **kwargs):
                Process._setup(self)
            
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
        # and wrap to include Process internals alongside user's custom state.
        
        user_serialize = cls.__dict__.get('__serialize__')
        user_deserialize = cls.__dict__.get('__deserialize__')
        
        # Create the __serialize__ method that handles both Process state and user state
        def make_serialize(user_ser):
            def __serialize__(self):
                return Process._serialize_with_user(self, user_ser)
            return __serialize__
        
        cls.__serialize__ = make_serialize(user_serialize)
        
        # Determine if this is a locally-defined class
        is_local = "<locals>" in cls.__qualname__
        
        if is_local:
            # For locally-defined classes: staticmethod with (cls, state) signature
            # cerial calls: deserialize_func(cls, state["custom_state"])
            def make_deserialize_static(user_deser):
                def __deserialize__(reconstructed_cls, state):
                    return Process._deserialize_with_user(reconstructed_cls, state, user_deser)
                return staticmethod(__deserialize__)
            
            cls.__deserialize__ = make_deserialize_static(user_deserialize)
        else:
            # For module-level classes: classmethod with (state) signature (cls is implicit)
            # cerial calls: cls.__deserialize__(state["custom_state"])
            def make_deserialize_classmethod(user_deser):
                @classmethod
                def __deserialize__(inner_cls, state):
                    return Process._deserialize_with_user(inner_cls, state, user_deser)
                return __deserialize__
            
            cls.__deserialize__ = make_deserialize_classmethod(user_deserialize)
    
    # =========================================================================
    # Serialization support for cerial
    # =========================================================================
    
    # Lifecycle method names that need to be captured during serialization
    _LIFECYCLE_METHODS = (
        '__preloop__', '__loop__', '__postloop__', 
        '__onfinish__', '__result__', '__error__'
    )
    
    @staticmethod
    def _serialize_with_user(instance: "Process", user_serialize=None) -> dict:
        """
        Serialize this Process instance for cerial.
        
        Captures:
        - Instance __dict__ (all instance attributes)
        - Lifecycle methods defined on the subclass
        - Class name for reconstruction
        - User's custom state if they defined __serialize__
        
        Args:
            instance: The Process instance to serialize
            user_serialize: User's __serialize__ method (if they defined one)
        """
        cls = instance.__class__
        
        # Capture lifecycle methods defined on THIS class (not inherited from Process)
        lifecycle_methods = {}
        for name in Process._LIFECYCLE_METHODS:
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
        
        state = {
            'instance_dict': instance.__dict__.copy(),
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
    def _deserialize_with_user(reconstructed_cls: type, state: dict, user_deserialize=None) -> "Process":
        """
        Deserialize a Process instance from cerial state.
        
        Args:
            reconstructed_cls: The class cerial reconstructed (we ignore this and build our own)
            state: The serialized state dict
            user_deserialize: User's __deserialize__ method (if they defined one)
        
        Recreates the subclass dynamically with type() and restores state.
        If user had custom deserialize, applies it after Process reconstruction.
        """
        # Build class dict with lifecycle methods and class attributes
        class_dict = {}
        class_dict.update(state.get('class_attrs', {}))
        class_dict.update(state['lifecycle_methods'])
        
        # Create the subclass dynamically
        # Note: This triggers __init_subclass__ which sets up __init__ wrapping
        new_class = type(
            state['class_name'],
            (Process,),
            class_dict
        )
        
        # Create instance without calling __init__
        # We bypass __init__ because we're restoring state directly
        obj = object.__new__(new_class)
        
        # Restore instance state directly (includes config, timers, etc.)
        obj.__dict__.update(state['instance_dict'])
        
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
    
    # Fallback for direct calls on Process base class
    def __serialize__(self) -> dict:
        """Serialize this Process instance (base class fallback)."""
        return Process._serialize_with_user(self, None)
    
    @classmethod
    def __deserialize__(cls, state: dict) -> "Process":
        """Deserialize for module-level classes (base class fallback)."""
        return Process._deserialize_with_user(cls, state, None)
    
    # =========================================================================
    # Internal setup
    # =========================================================================
    
    @staticmethod
    def _setup(instance: "Process") -> None:
        """
        Initialize internal process state.
        
        Called automatically before user's __init__.
        """
        # Configuration with defaults
        instance.config = ProcessConfig()
        
        # Timers container (created lazily by @timethis decorator)
        instance.timers = None
        
        # Runtime state
        instance._current_lap = 0
        instance._start_time = None
        
        # Error state (set when error occurs, used by __error__)
        instance.error = None
        
        # Communication primitives (created on start())
        instance._stop_event = None
        instance._result_queue = None
        
        # Subprocess handle
        instance._subprocess = None
        
        # Result storage (populated after process completes)
        instance._result = None
        instance._has_result = False
    
    # =========================================================================
    # Lifecycle methods (override these in subclass)
    # =========================================================================
    
    def __preloop__(self) -> None:
        """Called before each __loop__() iteration. Override in subclass."""
        pass
    
    def __loop__(self) -> None:
        """Main work method. Called each iteration. Override in subclass."""
        pass
    
    def __postloop__(self) -> None:
        """Called after each __loop__() iteration. Override in subclass."""
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
        
        Serializes this Process object, spawns a subprocess, and runs
        the engine loop there.
        """
        # Import here to avoid circular imports
        from .engine import _engine_main
        from suitkaise import cerial
        
        # Serialize current state
        serialized = cerial.serialize(self)
        
        # Save original state for retries (lives system)
        original_state = serialized
        
        # Create communication primitives
        self._stop_event = multiprocessing.Event()
        self._result_queue = multiprocessing.Queue()
        
        # Record start time
        from suitkaise import sktime
        self._start_time = sktime.now()
        
        # Spawn subprocess
        self._subprocess = multiprocessing.Process(
            target=_engine_main,
            args=(serialized, self._stop_event, self._result_queue, original_state)
        )
        self._subprocess.start()
    
    def stop(self) -> None:
        """
        Signal the process to stop gracefully.
        
        The process will finish its current section, run __onfinish__(),
        and send its result back.
        
        If called from inside the process (in a lifecycle method),
        this sets the stop signal that the engine checks between sections.
        """
        if self._stop_event is not None:
            self._stop_event.set()
    
    def kill(self) -> None:
        """
        Forcefully terminate the process immediately.
        
        No cleanup, no __onfinish__, no result. The process is just killed.
        """
        if self._subprocess is not None and self._subprocess.is_alive():
            self._subprocess.terminate()
            self._subprocess.join(timeout=5)
            
            # If still alive after terminate, force kill
            if self._subprocess.is_alive():
                self._subprocess.kill()
    
    def wait(self, timeout: float | None = None) -> bool:
        """
        Wait for the process to finish.
        
        Args:
            timeout: Maximum seconds to wait. None = wait forever.
        
        Returns:
            True if process finished, False if timeout reached.
        
        Raises:
            RuntimeError: If called from inside the process.
        """
        if self._subprocess is None:
            return True
        
        self._subprocess.join(timeout=timeout)
        return not self._subprocess.is_alive()
    
    @property
    def result(self) -> Any:
        """
        Get the result from the process.
        
        Blocks until the process finishes if not already done.
        
        Returns:
            Whatever __result__() returned.
        
        Raises:
            The error if the process failed (after exhausting lives).
        """
        if self._has_result:
            # Already retrieved
            if isinstance(self._result, BaseException):
                raise self._result
            return self._result
        
        # Wait for result from queue
        if self._result_queue is None:
            return None
        
        # Wait for process to finish first
        self.wait()
        
        # Get result from queue
        # Note: Don't use queue.empty() - it's unreliable in multiprocessing.
        # The message might be in transit even after wait() returns.
        from suitkaise import cerial
        import queue as queue_module
        
        try:
            # Give a small timeout to account for message transit time
            message = self._result_queue.get(timeout=1.0)
            
            if message["type"] == "error":
                self._result = cerial.deserialize(message["data"])
                self._has_result = True
                raise self._result
            else:
                self._result = cerial.deserialize(message["data"])
                self._has_result = True
                return self._result
        except queue_module.Empty:
            # No message received - subprocess may have crashed silently
            return None
    
    @property
    def current_lap(self) -> int:
        """Current loop iteration number (0-indexed)."""
        return self._current_lap
    
    @property
    def is_alive(self) -> bool:
        """Whether the subprocess is currently running."""
        return self._subprocess is not None and self._subprocess.is_alive()