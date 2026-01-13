"""
Sk module API - Skclass, Skfunction, @sk decorator.

Provides automatic _shared_meta generation and .asynced() support for user classes.
"""

from typing import Type, TypeVar, Generic, Callable, Any, Dict, List, Tuple, ParamSpec
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
    - .retry() for automatic retry with backoff
    - .timeout() for execution time limits
    - .background() for fire-and-forget execution
    
    Usage:
        import time
        import requests
        
        def slow_fetch(url):
            return requests.get(url).text
        
        sk_fetch = Skfunction(slow_fetch)
        
        # Async version (uses to_thread)
        result = await sk_fetch.asynced()("https://example.com")
        
        # Retry on failure
        result = sk_fetch.retry(times=3, backoff=2.0)("https://flaky-api.com")
        
        # Timeout
        result = sk_fetch.timeout(5.0)("https://slow-api.com")
        
        # Background execution (returns Future)
        future = sk_fetch.background()("https://example.com")
        result = future.result()  # Block when needed
        
        # Chain them
        result = sk_fetch.retry(3).timeout(10.0)("https://api.com")
    """
    
    def __init__(self, func: Callable[P, R]):
        """
        Wrap a function with Skfunction functionality.
        
        Args:
            func: The function to wrap
        """
        self._func = func
        self._blocking_calls = self._detect_blocking_calls()
    
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Call the wrapped function directly."""
        return self._func(*args, **kwargs)
    
    def __repr__(self) -> str:
        return f"Skfunction({self._func.__name__})"
    
    def _detect_blocking_calls(self) -> List[str]:
        """Detect blocking calls in the function."""
        import ast
        import inspect
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
        
        async_func = create_async_wrapper(self._func)
        return AsyncSkfunction(async_func)
    
    def retry(
        self,
        times: int = 3,
        backoff: float = 1.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> "Skfunction[P, R]":
        """
        Get a version that retries on failure.
        
        Args:
            times: Maximum number of attempts (default 3)
            backoff: Multiplier for sleep between retries (default 1.0)
            exceptions: Exception types to retry on (default: all)
            
        Returns:
            New Skfunction with retry behavior
        """
        wrapped = create_retry_wrapper(self._func, times, backoff, exceptions)
        return Skfunction(wrapped)
    
    def timeout(self, seconds: float) -> "Skfunction[P, R]":
        """
        Get a version with execution timeout.
        
        Args:
            seconds: Maximum execution time
            
        Returns:
            New Skfunction with timeout behavior
            
        Raises:
            TimeoutError: When function exceeds timeout
        """
        wrapped = create_timeout_wrapper(self._func, seconds)
        return Skfunction(wrapped)
    
    def background(self) -> Callable[P, Future[R]]:
        """
        Get a version that runs in a background thread.
        
        Returns a Future that can be used to get the result later.
        
        Returns:
            Function that returns a Future
            
        Example:
            future = sk_func.background()("arg1", "arg2")
            # ... do other work ...
            result = future.result()  # Block when needed
        """
        return create_background_wrapper(self._func)


class AsyncSkfunction(Generic[P, R]):
    """
    Async version of Skfunction, returned by Skfunction.asynced().
    
    Supports chaining with .timeout(), .retry() for async operations.
    
    Usage:
        sk_func = Skfunction(slow_fetch)
        
        # Chain async with timeout
        result = await sk_func.asynced().timeout(5.0)("https://api.com")
        
        # Chain async with retry
        result = await sk_func.asynced().retry(3, backoff=2.0)("https://api.com")
        
        # Chain multiple
        result = await sk_func.asynced().retry(3).timeout(10.0)("https://api.com")
    """
    
    def __init__(self, async_func: Callable[P, R]):
        """
        Wrap an async function.
        
        Args:
            async_func: The async function to wrap
        """
        self._func = async_func
    
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        """Call the wrapped async function."""
        return await self._func(*args, **kwargs)
    
    def __repr__(self) -> str:
        func_name = getattr(self._func, '__name__', 'async_function')
        return f"AsyncSkfunction({func_name})"
    
    def timeout(self, seconds: float) -> "AsyncSkfunction[P, R]":
        """
        Get a version with execution timeout.
        
        Args:
            seconds: Maximum execution time
            
        Returns:
            New AsyncSkfunction with timeout behavior
            
        Raises:
            FunctionTimeoutError: When function exceeds timeout
        """
        wrapped = create_async_timeout_wrapper_v2(self._func, seconds)
        return AsyncSkfunction(wrapped)
    
    def retry(
        self,
        times: int = 3,
        backoff: float = 1.0,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> "AsyncSkfunction[P, R]":
        """
        Get a version that retries on failure.
        
        Args:
            times: Maximum number of attempts (default 3)
            backoff: Multiplier for sleep between retries (default 1.0)
            exceptions: Exception types to retry on (default: all)
            
        Returns:
            New AsyncSkfunction with retry behavior
        """
        wrapped = create_async_retry_wrapper_v2(self._func, times, backoff, exceptions)
        return AsyncSkfunction(wrapped)


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
        
        # Return the original class
        return cls
        
    elif callable(cls_or_func):
        # It's a function - attach methods directly to the function
        func = cls_or_func
        
        # Detect blocking calls
        import ast
        import inspect
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
        
        def retry(times: int = 3, backoff: float = 1.0, exceptions: tuple = (Exception,)):
            """Get version that retries on failure."""
            return Skfunction(func).retry(times, backoff, exceptions)
        
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
