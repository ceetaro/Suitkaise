"""
Sk module API - Skclass, Skfunction, @sk decorator.

Provides automatic _shared_meta generation and .asynced() support for user classes.
"""

from typing import Type, TypeVar, Generic, Callable, Any, Dict, List, Tuple, ParamSpec
import inspect
from concurrent.futures import Future

from ._int.analyzer import analyze_class, get_blocking_methods, has_blocking_calls
from ._int.analyzer import _analyze_method, _BlockingCallVisitor, _get_method_source
from ._int.async_wrapper import create_async_class
from ._int.function_wrapper import (
    create_async_wrapper,
    create_retry_wrapper,
    create_async_retry_wrapper,
    create_timeout_wrapper,
    create_async_timeout_wrapper,
    create_background_wrapper,
    create_async_timeout_wrapper_v2,
    create_async_retry_wrapper_v2,
    FunctionTimeoutError,
)
from ._int.asyncable import _ModifiableMethod, _AsyncModifiableMethod


T = TypeVar('T')
P = ParamSpec('P')
R = TypeVar('R')


class NotAsyncedError(Exception):
    """
    Raised when .asynced() is called on a class/function with no blocking calls.
    
    This indicates that there's nothing to make async - all operations are
    already non-blocking (CPU-bound), so wrapping with to_thread() would
    add overhead without benefit.
    
    Example:
        >>> @sk
        ... class Counter:
        ...     def increment(self):
        ...         self.value += 1
        ...
        >>> Counter.asynced()  # Raises NotAsyncedError
        NotAsyncedError: Counter has no blocking calls
    """
    pass


class Skclass(Generic[T]):
    """
    Wrapper for user classes that provides:
    - Auto-generated _shared_meta for Share compatibility
    - .asynced() for async version (if class has blocking calls)
    
    Usage:
        class Counter:
            def __init__(self):
                self.value = 0
            
            def increment(self):
                self.value += 1
            
            def slow_increment(self):
                time.sleep(1)
                self.value += 1
        
        SkCounter = Skclass(Counter)
        
        # Regular usage
        counter = SkCounter()
        counter.increment()
        
        # Async usage (only for classes with blocking calls)
        AsyncCounter = SkCounter.asynced()
        async_counter = AsyncCounter()
        await async_counter.slow_increment()  # Uses to_thread()
        
        # Share usage
        share.counter = SkCounter()  # _shared_meta auto-generated
    """
    
    def __init__(self, cls: Type[T]):
        """
        Wrap a class with Skclass functionality.
        
        Args:
            cls: The class to wrap
        """
        self._original_class = cls
        self._shared_meta, self._blocking_methods = analyze_class(cls)
        self._async_class: Type | None = None
        
        # Attach _shared_meta to the original class so Share can detect it
        cls._shared_meta = self._shared_meta
        
        # Copy class metadata (these must be plain strings, not properties)
        # This helps with introspection and error messages
        object.__setattr__(self, '__name__', cls.__name__)
        object.__setattr__(self, '__qualname__', cls.__qualname__)
        object.__setattr__(self, '__module__', cls.__module__)
    
    def __call__(self, *args, **kwargs) -> T:
        """
        Create an instance of the wrapped class.
        
        Returns:
            Instance of the original class
        """
        return self._original_class(*args, **kwargs)
    
    def __repr__(self) -> str:
        return f"Skclass({self._original_class.__name__})"
    
    @property
    def _shared_meta(self) -> Dict[str, Any]:
        """Access the auto-generated _shared_meta."""
        return self.__dict__['_shared_meta']
    
    @_shared_meta.setter
    def _shared_meta(self, value: Dict[str, Any]) -> None:
        self.__dict__['_shared_meta'] = value
    
    @property
    def has_blocking_calls(self) -> bool:
        """Check if this class has any blocking calls."""
        return len(self._blocking_methods) > 0
    
    @property
    def blocking_methods(self) -> Dict[str, List[str]]:
        """Get dict of method names to their blocking calls."""
        return self._blocking_methods.copy()
    
    def asynced(self) -> Type[T]:
        """
        Get the async version of this class.
        
        Methods with blocking calls are wrapped with asyncio.to_thread().
        Methods without blocking calls remain synchronous.
        
        Returns:
            Async version of the wrapped class
            
        Raises:
            NotAsyncedError: If the class has no blocking calls
        """
        if not self.has_blocking_calls:
            raise NotAsyncedError(
                f"{self._original_class.__name__} has no blocking calls"
            )
        
        # Cache the async class
        if self._async_class is None:
            self._async_class = create_async_class(
                self._original_class,
                self._blocking_methods,
            )
            # Also attach _shared_meta to the async class
            self._async_class._shared_meta = self._shared_meta
        
        return self._async_class
    
    # Forward class attributes
    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to the original class."""
        return getattr(self._original_class, name)
    


class Skfunction(Generic[P, R]):
    """
    Wrapper for user functions that provides:
    - .asynced() for async version (if function has blocking calls)
    - .retry() for automatic retry with delay
    - .timeout() for execution time limits
    - .background() for fire-and-forget execution
    
    Modifiers can be chained in any order - they are always applied consistently:
    1. Retry (outermost) - retries the whole operation
    2. Timeout (inside retry) - times out each attempt
    3. Function call (innermost)
    
    Usage:
        import time
        import requests
        
        def slow_fetch(url):
            return requests.get(url).text
        
        sk_fetch = Skfunction(slow_fetch)
        
        # Async version (uses to_thread)
        result = await sk_fetch.asynced()("https://example.com")
        
        # Retry on failure
        result = sk_fetch.retry(times=3, delay=1.0)("https://flaky-api.com")
        
        # Timeout
        result = sk_fetch.timeout(5.0)("https://slow-api.com")
        
        # Background execution (returns Future)
        future = sk_fetch.background()("https://example.com")
        result = future.result()  # Block when needed
        
        # Chain them (order doesn't matter - behavior is consistent)
        result = sk_fetch.retry(3).timeout(10.0)("https://api.com")
        result = sk_fetch.timeout(10.0).retry(3)("https://api.com")  # same behavior
    """
    
    def __init__(
        self,
        func: Callable[P, R],
        *,
        _config: Dict[str, Any] | None = None,
        _blocking_calls: List[str] | None = None,
    ):
        """
        Wrap a function with Skfunction functionality.
        
        Args:
            func: The function to wrap
            _config: Internal - modifier configuration
            _blocking_calls: Internal - cached blocking calls
        """
        self._func = func
        self._config = _config or {}
        self._blocking_calls = _blocking_calls if _blocking_calls is not None else self._detect_blocking_calls()
    
    def _copy_with(self, **config_updates) -> "Skfunction[P, R]":
        """Create a copy with updated config."""
        new_config = {**self._config, **config_updates}
        return Skfunction(
            self._func,
            _config=new_config,
            _blocking_calls=self._blocking_calls,
        )
    
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """
        Call the wrapped function with all modifiers applied.
        
        Modifiers are applied in consistent order:
        1. Retry (outermost)
        2. Timeout (inside retry)
        3. Function call (innermost)
        """
        import time as time_module
        from concurrent.futures import ThreadPoolExecutor
        import concurrent.futures
        
        # Extract config
        retry_config = self._config.get('retry')
        timeout_config = self._config.get('timeout')
        
        # Build the execution
        func = self._func
        
        # If no modifiers, just call directly
        if not retry_config and not timeout_config:
            return func(*args, **kwargs)
        
        # Define the core execution (with timeout if configured)
        def execute_once():
            if timeout_config:
                seconds = timeout_config['seconds']
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    try:
                        return future.result(timeout=seconds)
                    except concurrent.futures.TimeoutError:
                        raise FunctionTimeoutError(
                            f"{func.__name__} timed out after {seconds} seconds"
                        )
            else:
                return func(*args, **kwargs)
        
        # Apply retry logic if configured
        if retry_config:
            times = retry_config['times']
            delay = retry_config['delay']
            backoff_factor = retry_config['backoff_factor']
            exceptions = retry_config['exceptions']
            
            last_exception = None
            sleep_time = delay
            
            for attempt in range(times):
                try:
                    return execute_once()
                except exceptions as e:
                    last_exception = e
                    if attempt < times - 1:
                        time_module.sleep(sleep_time)
                        sleep_time *= backoff_factor
            
            raise last_exception  # type: ignore
        else:
            return execute_once()
    
    def __repr__(self) -> str:
        modifiers = []
        if self._config.get('retry'):
            modifiers.append('retry')
        if self._config.get('timeout'):
            modifiers.append('timeout')
        mod_str = f", modifiers={modifiers}" if modifiers else ""
        return f"Skfunction({self._func.__name__}{mod_str})"
    
    def _detect_blocking_calls(self) -> List[str]:
        """Detect blocking calls in the function."""
        import ast
        import textwrap
        
        try:
            source = inspect.getsource(self._func)
            source = textwrap.dedent(source)
            tree = ast.parse(source)
        except (OSError, TypeError, SyntaxError):
            return []
        
        visitor = _BlockingCallVisitor()
        visitor.visit(tree)
        return visitor.blocking_calls
    
    @property
    def has_blocking_calls(self) -> bool:
        """Check if this function has any blocking calls."""
        return len(self._blocking_calls) > 0
    
    @property
    def blocking_calls(self) -> List[str]:
        """Get list of detected blocking calls."""
        return self._blocking_calls.copy()
    
    def asynced(self) -> "AsyncSkfunction[P, R]":
        """
        Get the async version of this function.
        
        Returns an AsyncSkfunction that can be further chained with
        .timeout(), .retry(), etc.
        
        Uses asyncio.to_thread() to run the sync function.
        
        Returns:
            AsyncSkfunction wrapping the async version
            
        Raises:
            NotAsyncedError: If the function has no blocking calls
        """
        if not self.has_blocking_calls:
            raise NotAsyncedError(
                f"{self._func.__name__} has no blocking calls"
            )
        
        # Pass config to AsyncSkfunction
        return AsyncSkfunction(
            self._func,
            _config=self._config.copy(),
            _blocking_calls=self._blocking_calls,
        )
    
    def retry(
        self,
        times: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 1.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> "Skfunction[P, R]":
        """
        Add retry behavior.
        
        Args:
            times: Maximum number of attempts (default 3)
            delay: Delay between retries in seconds (default 1.0)
            backoff_factor: Multiplier for delay after each retry (default 1.0)
            exceptions: Exception types to retry on (default: all)
            
        Returns:
            Skfunction with retry configured
        """
        return self._copy_with(retry={
            'times': times,
            'delay': delay,
            'backoff_factor': backoff_factor,
            'exceptions': exceptions,
        })
    
    def timeout(self, seconds: float) -> "Skfunction[P, R]":
        """
        Add timeout behavior.
        
        Args:
            seconds: Maximum execution time per attempt
            
        Returns:
            Skfunction with timeout configured
        """
        return self._copy_with(timeout={'seconds': seconds})
    
    def background(self) -> Callable[P, Future[R]]:
        """
        Get a version that runs in a background thread.
        
        Returns a Future that can be used to get the result later.
        Note: background() applies all configured modifiers.
        
        Returns:
            Function that returns a Future
            
        Example:
            future = sk_func.background()("arg1", "arg2")
            # ... do other work ...
            result = future.result()  # Block when needed
        """
        from concurrent.futures import ThreadPoolExecutor
        
        executor = ThreadPoolExecutor(max_workers=4)
        
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Future[R]:
            # Submit the full __call__ (with modifiers) to background
            return executor.submit(self.__call__, *args, **kwargs)
        
        return wrapper


class AsyncSkfunction(Generic[P, R]):
    """
    Async version of Skfunction, returned by Skfunction.asynced().
    
    Supports chaining with .timeout(), .retry() for async operations.
    Modifiers can be chained in any order - behavior is consistent.
    
    Usage:
        sk_func = Skfunction(slow_fetch)
        
        # Chain async with timeout
        result = await sk_func.asynced().timeout(5.0)("https://api.com")
        
        # Chain async with retry
        result = await sk_func.asynced().retry(3, delay=1.0)("https://api.com")
        
        # Chain multiple (order doesn't matter)
        result = await sk_func.asynced().retry(3).timeout(10.0)("https://api.com")
        result = await sk_func.asynced().timeout(10.0).retry(3)("https://api.com")
    """
    
    def __init__(
        self,
        func: Callable[P, R],
        *,
        _config: Dict[str, Any] | None = None,
        _blocking_calls: List[str] | None = None,
    ):
        """
        Wrap a function for async execution.
        
        Args:
            func: The original sync function
            _config: Internal - modifier configuration
            _blocking_calls: Internal - cached blocking calls
        """
        self._func = func
        self._config = _config or {}
        self._blocking_calls = _blocking_calls or []
    
    def _copy_with(self, **config_updates) -> "AsyncSkfunction[P, R]":
        """Create a copy with updated config."""
        new_config = {**self._config, **config_updates}
        return AsyncSkfunction(
            self._func,
            _config=new_config,
            _blocking_calls=self._blocking_calls,
        )
    
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """
        Call the wrapped function asynchronously with all modifiers applied.
        
        Modifiers are applied in consistent order:
        1. Retry (outermost)
        2. Timeout (inside retry)
        3. Function call via to_thread (innermost)
        """
        import asyncio
        
        # Extract config
        retry_config = self._config.get('retry')
        timeout_config = self._config.get('timeout')
        
        # Define the core async execution (with timeout if configured)
        async def execute_once():
            if timeout_config:
                seconds = timeout_config['seconds']
                try:
                    return await asyncio.wait_for(
                        asyncio.to_thread(self._func, *args, **kwargs),
                        timeout=seconds,
                    )
                except asyncio.TimeoutError:
                    raise FunctionTimeoutError(
                        f"{self._func.__name__} timed out after {seconds} seconds"
                    )
            else:
                return await asyncio.to_thread(self._func, *args, **kwargs)
        
        # Apply retry logic if configured
        if retry_config:
            times = retry_config['times']
            delay = retry_config['delay']
            backoff_factor = retry_config['backoff_factor']
            exceptions = retry_config['exceptions']
            
            last_exception = None
            sleep_time = delay
            
            for attempt in range(times):
                try:
                    return await execute_once()
                except exceptions as e:
                    last_exception = e
                    if attempt < times - 1:
                        await asyncio.sleep(sleep_time)
                        sleep_time *= backoff_factor
            
            raise last_exception  # type: ignore
        else:
            return await execute_once()
    
    def __repr__(self) -> str:
        modifiers = []
        if self._config.get('retry'):
            modifiers.append('retry')
        if self._config.get('timeout'):
            modifiers.append('timeout')
        mod_str = f", modifiers={modifiers}" if modifiers else ""
        func_name = getattr(self._func, '__name__', 'async_function')
        return f"AsyncSkfunction({func_name}{mod_str})"
    
    def timeout(self, seconds: float) -> "AsyncSkfunction[P, R]":
        """
        Add timeout behavior.
        
        Args:
            seconds: Maximum execution time per attempt
            
        Returns:
            AsyncSkfunction with timeout configured
        """
        return self._copy_with(timeout={'seconds': seconds})
    
    def retry(
        self,
        times: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 1.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> "AsyncSkfunction[P, R]":
        """
        Add retry behavior.
        
        Args:
            times: Maximum number of attempts (default 3)
            delay: Delay between retries in seconds (default 1.0)
            backoff_factor: Multiplier for delay after each retry (default 1.0)
            exceptions: Exception types to retry on (default: all)
            
        Returns:
            AsyncSkfunction with retry configured
        """
        return self._copy_with(retry={
            'times': times,
            'delay': delay,
            'backoff_factor': backoff_factor,
            'exceptions': exceptions,
        })


def sk(cls_or_func):
    """
    Decorator that attaches Sk functionality directly to a class or function.
    
    For classes: Attaches to the original class:
                 - _shared_meta for Share compatibility
                 - .asynced() staticmethod for async version
                 - .has_blocking_calls class attribute
                 - .blocking_methods class attribute
    
    For functions: Attaches to the original function:
                 - .has_blocking_calls attribute
                 - .blocking_calls attribute
                 - .asynced() method
                 - .retry() method
                 - .timeout() method
                 - .background() method
    
    The original class/function is returned - no wrapper objects.
    Skfunction/Skclass are used internally for chaining but not exposed.
    
    Usage:
        @sk
        class Counter:
            def __init__(self):
                self.value = 0
            
            def slow_increment(self):
                time.sleep(1)
                self.value += 1
        
        # Counter is still the original class
        counter = Counter()
        Counter.asynced()  # Get async version (if has blocking calls)
        Counter.has_blocking_calls  # True
        
        @sk
        def slow_fetch(url):
            return requests.get(url).text
        
        # slow_fetch is still the original function
        slow_fetch("https://example.com")  # Call directly
        await slow_fetch.asynced()("https://example.com")  # Async
        slow_fetch.retry(3).timeout(10)("https://example.com")  # Chain
    """
    if isinstance(cls_or_func, type):
        # It's a class - attach methods directly to the class
        cls = cls_or_func
        shared_meta, blocking_methods = analyze_class(cls)
        
        # Attach metadata directly to the class
        cls._shared_meta = shared_meta
        cls._blocking_methods = blocking_methods
        cls.has_blocking_calls = len(blocking_methods) > 0
        cls.blocking_methods = blocking_methods
        
        # Create asynced staticmethod
        def asynced():
            """Get async version of this class. Raises NotAsyncedError if no blocking calls."""
            if not blocking_methods:
                raise NotAsyncedError(f"{cls.__name__} has no blocking calls")
            async_cls = create_async_class(cls, blocking_methods)
            async_cls._shared_meta = shared_meta
            return async_cls
        
        cls.asynced = staticmethod(asynced)

        # Attach modifiers to instance methods
        for name, member in list(cls.__dict__.items()):
            if name.startswith("__"):
                continue
            if isinstance(member, (staticmethod, classmethod, property)):
                continue
            if isinstance(member, _ModifiableMethod):
                continue
            if inspect.iscoroutinefunction(member):
                setattr(
                    cls,
                    name,
                    _AsyncModifiableMethod(member, name=name),
                )
                continue
            if not inspect.isfunction(member):
                continue
            try:
                signature = inspect.signature(member)
                has_timeout_param = "timeout" in signature.parameters
            except (TypeError, ValueError):
                has_timeout_param = False
            setattr(
                cls,
                name,
                _ModifiableMethod(
                    member,
                    None,
                    name=name,
                    timeout_error=FunctionTimeoutError,
                    has_timeout_modifier=not has_timeout_param,
                ),
            )
        
        # Return the original class
        return cls
        
    elif callable(cls_or_func):
        # It's a function - attach methods directly to the function
        func = cls_or_func
        
        # Detect blocking calls
        import ast
        import textwrap
        
        blocking_calls = []
        try:
            source = inspect.getsource(func)
            source = textwrap.dedent(source)
            tree = ast.parse(source)
            visitor = _BlockingCallVisitor()
            visitor.visit(tree)
            blocking_calls = visitor.blocking_calls
        except (OSError, TypeError, SyntaxError):
            pass
        
        # Attach attributes
        func.has_blocking_calls = len(blocking_calls) > 0
        func.blocking_calls = blocking_calls
        
        # Attach methods that use Skfunction internally for chaining
        def asynced():
            """Get async version. Raises NotAsyncedError if no blocking calls."""
            if not blocking_calls:
                raise NotAsyncedError(f"{func.__name__} has no blocking calls")
            return Skfunction(func).asynced()
        
        def retry(times: int = 3, delay: float = 1.0, backoff_factor: float = 1.0, exceptions: tuple = (Exception,)):
            """Get version that retries on failure."""
            return Skfunction(func).retry(times, delay, backoff_factor, exceptions)
        
        def timeout(seconds: float):
            """Get version with execution timeout."""
            return Skfunction(func).timeout(seconds)
        
        def background():
            """Get version that runs in background thread."""
            return Skfunction(func).background()
        
        func.asynced = asynced
        func.retry = retry
        func.timeout = timeout
        func.background = background
        
        # Return the original function
        return func
        
    else:
        raise TypeError(f"@sk can only decorate classes or functions, got {type(cls_or_func)}")


__all__ = [
    'Skclass',
    'Skfunction',
    'AsyncSkfunction',
    'sk',
    'NotAsyncedError',
    'FunctionTimeoutError',
]
