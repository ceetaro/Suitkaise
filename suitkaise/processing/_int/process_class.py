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
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.processing import Skprocess
        
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

        # access timing (automatic for any lifecycle method you define)
        print(process.__run__.timer.mean)
        ```
    ────────────────────────────────────────────────────────\n

    Base class for subprocess execution.
    
    Inherit from this class and implement the lifecycle methods.

    - __prerun__(): Called before each run iteration
    - __run__(): Main work (required) - called each iteration
    - __postrun__(): Called after each run iteration  
    - __onfinish__(): Called when process ends (stop/limit reached)
    - __result__(): Return data when process completes
    - __error__(): Handle errors when all lives exhausted

    Your Skprocess inheriting class will not return a result unless you define the __result__ method.
    """
    
    # class-level attribute declarations for type checking
    process_config: ProcessConfig
    timers: ProcessTimers | None
    error: BaseException | None
    _current_run: int
    _start_time: float | None
    _stop_event: "Event | None"
    _result_queue: "Queue[Any] | None"
    _tell_queue: "Queue[Any] | None"  # parent to child communication
    _listen_queue: "Queue[Any] | None"  # child to parent communication
    _subprocess: multiprocessing.Process | None
    _result: Any
    _has_result: bool
    
    # class-level flag to track if __init_subclass__ should wrap __init__
    _is_base_class = True
    
    # internal attribute names (used for serialization filtering)
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
        
        # only wrap if this class defines its own __init__
        if '__init__' in cls.__dict__:
            original_init = cls.__dict__['__init__']
            
            def wrapped_init(self, *args, **kwargs):
                # run parent setup first
                Skprocess._setup(self)
                # then run user's __init__
                original_init(self, *args, **kwargs)
            
            # preserve function metadata for introspection
            wrapped_init.__name__ = original_init.__name__
            wrapped_init.__doc__ = original_init.__doc__
            cls.__init__ = wrapped_init
        else:
            # no __init__ defined but setup still needs to run
            def default_init(self, *args, **kwargs):
                Skprocess._setup(self)
            
            cls.__init__ = default_init
        
        # handle serialization methods for cerial compatibility
        #   cerial requires these to be in the class's own __dict__ (not inherited)
        #   for locally-defined classes.

        # NOTE: cerial handles locally-defined vs module-level classes differently

        # - locally defined (has <locals> in qualname): requires staticmethod with (cls, state) signature
        #   cerial calls: deserialize_func(cls, state["custom_state"])

        # - module level: expects classmethod with (state) signature (cls is implicit)
        #   cerial calls: cls.__deserialize__(state["custom_state"])

        # if user defined their own __serialize__/__deserialize__, we capture them
        # and wrap to include Skprocess internals alongside user's custom state.
        
        user_serialize = cls.__dict__.get('__serialize__')
        user_deserialize = cls.__dict__.get('__deserialize__')
        
        # create the __serialize__ method that handles both Skprocess state and user state
        def make_serialize(user_ser):
            def __serialize__(self):
                return Skprocess._serialize_with_user(self, user_ser)
            return __serialize__
        
        cls.__serialize__ = make_serialize(user_serialize)
        
        # determine if this is a locally-defined class
        is_local = "<locals>" in cls.__qualname__
        
        if is_local:
            # for locally-defined classes use staticmethod with (cls, state) signature
            # cerial calls deserialize_func(cls, state["custom_state"])
            def make_deserialize_static(user_deser):
                def __deserialize__(reconstructed_cls, state):
                    return Skprocess._deserialize_with_user(reconstructed_cls, state, user_deser)
                return staticmethod(__deserialize__)
            
            cls.__deserialize__ = make_deserialize_static(user_deserialize)
        else:
            # for module-level classes use classmethod with (state) signature
            # cerial calls cls.__deserialize__(state["custom_state"])
            def make_deserialize_classmethod(user_deser):
                @classmethod
                def __deserialize__(inner_cls, state):
                    return Skprocess._deserialize_with_user(inner_cls, state, user_deser)
                return __deserialize__
            
            cls.__deserialize__ = make_deserialize_classmethod(user_deserialize)
    


    # serialization support for cerial
    
    # lifecycle method names that need to be captured during serialization
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
        
        # capture lifecycle methods defined on this class only
        lifecycle_methods = {}
        for name in Skprocess._LIFECYCLE_METHODS:
            if name in cls.__dict__:
                # this is a method defined on the subclass
                lifecycle_methods[name] = cls.__dict__[name]
        
        # capture class-level attributes that are not dunder or private
        class_attrs = {}
        for name, value in cls.__dict__.items():
            if name.startswith('_'):
                continue
            if name in lifecycle_methods:
                continue
            # include class variables, but not inherited stuff
            class_attrs[name] = value
        
        # prepare instance dict and skip TimedMethod wrappers
        # they are recreated after deserialization
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
        
        # include user custom state if __serialize__ is defined
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
        # build class dict with lifecycle methods and class attributes
        class_dict = {}
        class_dict.update(state.get('class_attrs', {}))
        class_dict.update(state['lifecycle_methods'])
        
        # create the subclass dynamically
        # note this triggers __init_subclass__ which sets up __init__ wrapping
        new_class = type(
            state['class_name'],
            (Skprocess,),
            class_dict
        )
        
        # create instance without calling __init__
        # bypass __init__ because state is restored directly
        obj = object.__new__(new_class)
        
        # restore instance state directly including config and timers
        obj.__dict__.update(state['instance_dict'])
        
        # set up timed method wrappers
        Skprocess._setup_timed_methods(obj)
        
        # apply user __deserialize__ if present
        if state.get('has_user_serialize') and user_deserialize is not None:
            # user's __deserialize__ should be a classmethod that takes (cls, state)
            # we call it with the user's custom state portion
            user_state = state.get('user_custom_state', {})
            
            # handle both classmethod and staticmethod signatures
            # the user_deserialize we captured is the raw method/function
            if isinstance(user_deserialize, classmethod):
                # it's already a classmethod descriptor, extract the function
                user_func = user_deserialize.__func__
                user_result = user_func(new_class, user_state)
            elif isinstance(user_deserialize, staticmethod):
                # it's a staticmethod, extract and call with (cls, state)
                user_func = user_deserialize.__func__
                user_result = user_func(new_class, user_state)
            else:
                # regular function or unbound method - try calling as classmethod style
                try:
                    user_result = user_deserialize(new_class, user_state)
                except TypeError:
                    # try to see if it expects state
                    user_result = user_deserialize(user_state)
            
            # if user deserialize returned an object merge its attributes
            if user_result is not None and hasattr(user_result, '__dict__'):
                # merge user's restored attributes into our obj
                for key, value in user_result.__dict__.items():
                    if key not in obj.__dict__:
                        obj.__dict__[key] = value
        
        # auto-reconnect if enabled via @autoreconnect decorator
        if getattr(new_class, '_auto_reconnect_enabled', False):
            try:
                from suitkaise.cerial.api import reconnect_all
                reconnect_kwargs = getattr(new_class, '_auto_reconnect_kwargs', {})
                obj = reconnect_all(obj, **reconnect_kwargs)
            except Exception:
                pass
        
        return obj
    
    # fallback for direct calls on Skprocess base class
    def __serialize__(self) -> dict:
        """Serialize this Skprocess instance (base class fallback)."""
        return Skprocess._serialize_with_user(self, None)
    
    @classmethod
    def __deserialize__(cls, state: dict) -> "Skprocess":
        """Deserialize for module-level classes (base class fallback)."""
        return Skprocess._deserialize_with_user(cls, state, None)
    


    # internal setup

    @staticmethod
    def _setup(instance: "Skprocess") -> None:
        """
        Initialize internal process state.
        
        Called automatically before user's __init__.
        """
        # configuration with defaults
        instance.process_config = ProcessConfig()
        
        # timers container created when needed
        instance.timers = None
        
        # runtime state
        instance._current_run = 0
        instance._start_time = None
        
        # error state set when error occurs for __error__
        instance.error = None
        
        # communication primitives created on start
        instance._stop_event = None
        instance._result_queue = None
        instance._tell_queue = None  # Parent → Child
        instance._listen_queue = None  # Child → Parent
        
        # subprocess handle
        instance._subprocess = None
        
        # result storage populated after process completes
        instance._result = None
        instance._has_result = False
        
        # set up timed method wrappers
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
            # check if user defined this method on the subclass
            if method_name in cls.__dict__:
                # get the actual method
                method = getattr(instance, method_name)
                # create wrapper
                wrapper = TimedMethod(method, instance, timer_name)
                # store as instance attribute (shadows class method)
                setattr(instance, method_name, wrapper)
    


    # lifecycle methods (override these in subclass)

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
    

    # control methods (called from parent process)

    
    def start(self) -> None:
        """
        ────────────────────────────────────────────────────────
        ```python
        process = MyProcess()
        process.start()
        ```
        ────────────────────────────────────────────────────────\n

        Start the process in a new subprocess.
        
        Serializes this Skprocess object, spawns a subprocess, and runs
        the engine there.
        """
        # import here to avoid circular imports
        from .engine import _engine_main
        from suitkaise import cerial
        
        # ensure timers exist for this run
        if self.timers is None:
            self.timers = ProcessTimers()
        
        # serialize current state for subprocess transfer
        serialized = cerial.serialize(self)
        
        # save original state for retries in the lives system
        original_state = serialized
        
        # create communication primitives for control and results
        self._stop_event = multiprocessing.Event()
        self._result_queue = multiprocessing.Queue()
        self._tell_queue = multiprocessing.Queue()  # Parent → Child
        self._listen_queue = multiprocessing.Queue()  # Child → Parent
        
        # record start time for join_in and timers
        from suitkaise import timing
        self._start_time = timing.time()
        
        # spawn subprocess to run the engine
        self._subprocess = multiprocessing.Process(
            target=_engine_main,
            args=(serialized, self._stop_event, self._result_queue, 
                  original_state, self._tell_queue, self._listen_queue)
        )
        self._subprocess.start()

    def run(self) -> Any:
        """
        ────────────────────────────────────────────────────────
        ```python
        process = MyProcess()
        result = process.run()
        ```
        ────────────────────────────────────────────────────────\n
        
        Start, wait, and return the result in one call.
        """
        self.start()
        self.wait()
        return self.result()
    
    def stop(self) -> None:
        """
        ────────────────────────────────────────────────────────
        ```python
        process = MyProcess()
        process.start()

        # signal to stop (finishes current run)
        process.stop()
        ```
        ────────────────────────────────────────────────────────\n
        
        Signal the process to stop gracefully.
        
        Does NOT block - returns immediately after setting the stop signal.
        The process will finish its current section, run __onfinish__(),
        and send its result back via __result__() or __error__().
        
        Use wait() after stop() if you need to block until finished.
        """
        if self._stop_event is not None:
            self._stop_event.set()
    
    def kill(self) -> None:
        """
        ────────────────────────────────────────────────────────
        ```python
        process = MyProcess()
        process.start()

        # if program has an issue...

        # kill the process
        process.kill()

        # result will be None
        ```
        ────────────────────────────────────────────────────────\n
        
        Forcefully terminate the process immediately.
        
        Bypasses the lives system - process is killed immediately.
        No cleanup, no __onfinish__, no result. The process is just killed.

        Result will be None.
        """
        if self._subprocess is not None and self._subprocess.is_alive():
            self._subprocess.terminate()
            self._subprocess.join(timeout=5)
            
            # if still alive after terminate, force kill
            if self._subprocess.is_alive():
                self._subprocess.kill()
    


    # async wait implementation for modifiers
    
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
        
        # must drain result queue BEFORE waiting for subprocess
        # otherwise deadlock: subprocess can't exit until queue is drained,
        # but we can't drain until subprocess exits
        self._drain_result_queue()
        
        self._subprocess.join(timeout=timeout)
        self._drain_result_queue()
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
        # sync - blocks until finished
        finished = process.wait()

        # or with timeout
        finished = process.wait(timeout=10.0)
        ```
    ────────────────────────────────────────────────────────
        ```python
        # async
        finished = await process.wait.asynced()()

        # with several concurrent processes
        wait_coro1 = process1.wait.asynced()()
        wait_coro2 = process2.wait.asynced()()

        # wait for both to finish
        finished1, finished2 = await asyncio.gather(wait_coro1, wait_coro2)
        ```
    ────────────────────────────────────────────────────────\n
    
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
            # non-blocking read; subprocess may still be producing
            get_nowait = getattr(self._result_queue, "get_nowait", None)
            if get_nowait is not None:
                try:
                    message = get_nowait()
                except queue_module.Empty:
                    message = self._result_queue.get(timeout=0.5)
            else:
                message = self._result_queue.get(timeout=0.5)
            
            # update timers from subprocess
            if 'timers' in message and message['timers'] is not None:
                self.timers = cerial.deserialize(message['timers'])
                Skprocess._setup_timed_methods(self)
            
            if message["type"] == "error":
                error_data = cerial.deserialize(message["data"])
                # if __error__() returned a non-exception, wrap it
                if isinstance(error_data, BaseException):
                    self._result = error_data
                else:
                    # create a generic ProcessError wrapping the error info
                    from .errors import ProcessError
                    self._result = ProcessError(f"Process failed: {error_data}")
            else:
                self._result = cerial.deserialize(message["data"])
            
            self._has_result = True
        except queue_module.Empty:
            # no result yet - subprocess may still be running
            pass
    

    # async result implementation for modifiers
    
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
        # wait drains the queue and stores result
        self.wait()
        
        if self._has_result:
            if isinstance(self._result, BaseException):
                raise self._result
            return self._result
        
        # no result retrieved - subprocess may have crashed silently
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
        # sync - blocks until result ready
        data = process.result()
        
        # with timeout - raises ProcessTimeoutError if exceeded
        data = process.result.timeout(10.0)()
        
        # background - returns Future immediately
        future = process.result.background()()
        # ... do other work ...
        data = future.result()
        
        # async - await in async code
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
        ────────────────────────────────────────────────────────
        ```python
        # parent tells subprocess
        
        p = MyProcess() # Skprocess instance
        p.start()

        data = get_new_data()
        if data:
            p.tell(new_data)

        p.wait()

        result = p.result()

        print(result)
        ```
        ────────────────────────────────────────────────────────
        ```python
        # subprocess tells parent
        from suitkaise import Skprocess

        class MyProcess(Skprocess):

            # ...

            def __run__(self):

                do_something()


            def __postrun__(self):

                if found_what_we_need:
                    self.tell("hey, we found what we need")

                self.stop()
        ```
        ────────────────────────────────────────────────────────\n
        
        Send data to the other side.
        This method is non-blocking - returns immediately after queuing the data.
        
        Args:
            data: Any serializable data to send to the other side.
        """
        if self._tell_queue is None:
            raise RuntimeError("Cannot tell() - process not started")
        
        from suitkaise import cerial
        serialized = cerial.serialize(data)
        self._tell_queue.put(serialized)
    

    
    # async listen implementation for modifiers
    
    async def _async_listen(self, timeout: float | None = None) -> Any:
        """Async implementation of listen()."""
        return await asyncio.to_thread(self._sync_listen, timeout)
    
    def _sync_listen(self, timeout: float | None = None) -> Any:
        """
        Receive data from the other side.
        
        Blocks until data is received from the other side.
        
        Args:
            timeout: Maximum seconds to wait. None = wait forever.
        
        Returns:
            The data sent by the other side, or None if timeout reached.
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
        # parent listening for data from subprocess

        # sync - blocks until data received
        data = process.listen()

        # with timeout - returns None if timeout reached
        data = process.listen(timeout=5.0)
        
        # background - returns Future immediately
        future = process.listen.background()(timeout=a_timeout)
        
        # async - get coroutine or await in async code
        listen_coro = process.listen.asynced()
        data = await process.listen.asynced()()
        ```
    ────────────────────────────────────────────────────────
        ```python
        # subprocess listening for data from parent
        from suitkaise import Skprocess

        class UIManager(Skprocess):

            def __init__(self):
                self.commands = []

            def __prerun__(self):

                commands = self.listen(timeout=1.0)

                if commands:
                    self.commands.append(commands)

            def __run__(self):

                for command in self.commands:
                    process_command(command)
                    self.commands.remove(command)
        ```
    ────────────────────────────────────────────────────────\n
    
    Receive data from the other side.
    
    Blocks until data is received from the other side via tell().
    
    Args:
        timeout: Maximum seconds to wait. None = wait forever.
    
    Returns:
        The data sent by the other side, or None if timeout reached.
    
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
