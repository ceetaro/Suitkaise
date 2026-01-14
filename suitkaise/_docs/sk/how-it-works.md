# How `sk` actually works

`sk` has no dependencies outside of the standard library.

- uses AST analysis to detect blocking calls in methods/functions
- generates `_shared_meta` through static analysis
- creates async wrappers using `asyncio.to_thread()`

---

## Overview

The `sk` module provides two main capabilities:

1. **Blocking Call Detection** — analyzes source code to find blocking operations
2. **Async Wrapping** — creates async versions of blocking code

```
Source Code → AST Analysis → Blocking Calls Detected → Async Wrapper Created
```

---

## Blocking Call Detection

### How It Works

The analyzer uses Python's `ast` (Abstract Syntax Tree) module to statically analyze function and method source code.

1. Gets source code using `inspect.getsource()`
2. Parses into AST using `ast.parse()`
3. Walks the tree looking for blocking call patterns
4. Returns list of detected blocking calls

### `_BlockingCallVisitor`

A custom AST visitor that identifies blocking operations.

Detected patterns include:

**Time Operations**
- `time.sleep`
- `sleep` (if imported from time)
- `timing.sleep`, `sktime.sleep` (suitkaise)

**Network/HTTP**
- `requests.get`, `requests.post`, `requests.put`, etc.
- `urllib.request.urlopen`
- `http.client` methods
- `socket` operations

**File I/O**
- `open()` calls
- file object methods: `read()`, `write()`, `readline()`

**Database**
- `cursor.execute()`
- `connection.commit()`

**Subprocess**
- `subprocess.run`, `subprocess.call`, `subprocess.Popen`
- `.communicate()`, `.wait()`

**Suitkaise**
- `Pool.map`, `Pool.imap`, `Pool.starmap`
- `Circuit.short`, `Circuit.trip` (may sleep)

The visitor walks the AST and collects all matching call patterns into a list.

### Class Analysis

For classes, `analyze_class()` performs additional work:

1. Iterates through all methods
2. Analyzes each method for blocking calls
3. Generates `_shared_meta` for Share compatibility
4. Returns both the metadata and blocking method mapping

```python
def analyze_class(cls):
    shared_meta = {'methods': {}, 'properties': {}}
    blocking_methods = {}
    
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        # analyze method
        blocking_calls = analyze_method(method)
        if blocking_calls:
            blocking_methods[name] = blocking_calls
        
        # generate _shared_meta entry
        writes, reads = analyze_attribute_access(method)
        shared_meta['methods'][name] = {'writes': writes, 'reads': reads}
    
    return shared_meta, blocking_methods
```

---

## `_shared_meta` Generation

The analyzer generates `_shared_meta` by detecting which instance attributes each method reads from or writes to.

### Attribute Detection

Uses AST analysis to find:

**Writes** — assignments to `self.attribute`:
```python
def increment(self):
    self.value += 1  # writes to 'value'
```

**Reads** — access to `self.attribute` without assignment:
```python
def get_double(self):
    return self.value * 2  # reads from 'value'
```

### Output Format

```python
_shared_meta = {
    'methods': {
        'increment': {'writes': ['value']},
        'get_value': {'reads': ['value']},
    },
    'properties': {
        'current': {'reads': ['value']},
    }
}
```

This metadata is used by the Share system for synchronization.

---

## Async Wrapper Creation

### `create_async_class()`

Creates an async version of a class by wrapping blocking methods.

1. Creates a new class that inherits from the original
2. For each blocking method, replaces with an async wrapper
3. Non-blocking methods remain unchanged

```python
def create_async_class(original_class, blocking_methods):
    class AsyncWrapper(original_class):
        pass
    
    for method_name in blocking_methods:
        original_method = getattr(original_class, method_name)
        async_method = create_async_method_wrapper(original_method)
        setattr(AsyncWrapper, method_name, async_method)
    
    return AsyncWrapper
```

### Async Method Wrapper

Each blocking method is wrapped to run in a thread:

```python
async def async_wrapper(self, *args, **kwargs):
    return await asyncio.to_thread(original_method, self, *args, **kwargs)
```

`asyncio.to_thread()` runs the synchronous blocking code in a thread pool, allowing other async code to run while it blocks.

### `create_async_wrapper()` for Functions

Similar to class methods, but for standalone functions:

```python
def create_async_wrapper(func):
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper
```

---

## Retry Wrapper

### `create_retry_wrapper()`

Wraps a function to retry on failure with optional exponential backoff.

```python
def create_retry_wrapper(func, times, delay, backoff_factor, exceptions):
    def wrapper(*args, **kwargs):
        last_exception = None
        sleep_time = delay
        
        for attempt in range(times):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < times - 1:
                    time.sleep(sleep_time)
                    sleep_time *= backoff_factor
        
        raise last_exception
    return wrapper
```

The `backoff_factor` multiplier increases sleep time between attempts:
- attempt 1: fails, sleep 1.0s (initial delay)
- attempt 2: fails, sleep 2.0s (1.0 × 2.0)
- attempt 3: fails, sleep 4.0s (2.0 × 2.0)
- ...

### Async Retry

The async version uses `asyncio.sleep()` instead:

```python
async def async_wrapper(*args, **kwargs):
    # ... same logic ...
    await asyncio.sleep(sleep_time)
    # ...
```

---

## Timeout Wrapper

### `create_timeout_wrapper()`

For synchronous functions, uses threading with a timeout:

```python
def create_timeout_wrapper(func, seconds):
    def wrapper(*args, **kwargs):
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=seconds)
        
        if thread.is_alive():
            raise FunctionTimeoutError(f"Timeout after {seconds}s")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    return wrapper
```

Note: The daemon thread continues running after timeout. This is a limitation of Python threading.

### Async Timeout

Uses `asyncio.wait_for()` for cleaner cancellation:

```python
async def async_wrapper(*args, **kwargs):
    try:
        return await asyncio.wait_for(
            async_func(*args, **kwargs),
            timeout=seconds
        )
    except asyncio.TimeoutError:
        raise FunctionTimeoutError(f"Timeout after {seconds}s")
```

---

## Background Wrapper

### `create_background_wrapper()`

Uses `concurrent.futures.ThreadPoolExecutor` to run functions in background threads:

```python
from concurrent.futures import ThreadPoolExecutor, Future

_executor = ThreadPoolExecutor(max_workers=10)

def create_background_wrapper(func):
    def wrapper(*args, **kwargs) -> Future:
        return _executor.submit(func, *args, **kwargs)
    return wrapper
```

The returned `Future` object provides:
- `future.result()` — block and get result
- `future.result(timeout=5)` — block with timeout
- `future.done()` — check if complete (non-blocking)
- `future.cancel()` — attempt to cancel
- `future.exception()` — get raised exception

---

## `Skclass` Wrapper

The `Skclass` wrapper manages all class-related functionality:

```python
class Skclass:
    def __init__(self, cls):
        self._original_class = cls
        self._shared_meta, self._blocking_methods = analyze_class(cls)
        self._async_class = None
        
        # attach metadata to original class
        cls._shared_meta = self._shared_meta
    
    def __call__(self, *args, **kwargs):
        # creates instance of original class
        return self._original_class(*args, **kwargs)
    
    def asynced(self):
        if not self._blocking_methods:
            raise NotAsyncedError(f"{self._original_class.__name__} has no blocking calls")
        
        if self._async_class is None:
            self._async_class = create_async_class(
                self._original_class,
                self._blocking_methods
            )
        
        return self._async_class
```

### Caching

The async class is cached on first creation to avoid re-analysis:

```python
SkCounter = Skclass(Counter)

# first call creates and caches
AsyncCounter1 = SkCounter.asynced()

# subsequent calls return cached version
AsyncCounter2 = SkCounter.asynced()

# same class object
assert AsyncCounter1 is AsyncCounter2
```

---

## `Skfunction` Wrapper

Similar to `Skclass`, but for standalone functions. Uses a config-based approach where modifiers set configuration flags instead of creating nested wrappers.

```python
class Skfunction:
    def __init__(self, func, *, _config=None, _blocking_calls=None):
        self._func = func
        self._config = _config or {}
        self._blocking_calls = _blocking_calls or self._detect_blocking_calls()
    
    def _copy_with(self, **config_updates):
        """create copy with updated config"""
        new_config = {**self._config, **config_updates}
        return Skfunction(self._func, _config=new_config, _blocking_calls=self._blocking_calls)
    
    def __call__(self, *args, **kwargs):
        # apply all modifiers in consistent order
        # 1. retry (outermost)
        # 2. timeout (inside retry)
        # 3. function call (innermost)
        ...
    
    def retry(self, times=3, delay=1.0, backoff_factor=1.0, exceptions=(Exception,)):
        return self._copy_with(retry={'times': times, 'delay': delay, ...})
    
    def timeout(self, seconds):
        return self._copy_with(timeout={'seconds': seconds})
    
    def asynced(self):
        if not self._blocking_calls:
            raise NotAsyncedError(...)
        return AsyncSkfunction(self._func, _config=self._config.copy(), ...)
```

### Config-Based Execution

When `__call__` is invoked, all modifiers are applied in a consistent order regardless of how they were chained:

```python
sk_func.retry(3).timeout(10)(args)
# config: {'retry': {...}, 'timeout': {...}}
# execution order:
# 1. retry logic (outermost)
# 2. timeout check (inside retry - each attempt times out)
# 3. function call (innermost)

sk_func.timeout(10).retry(3)(args)
# same config, same execution order
# order of chaining doesn't matter
```

This design ensures predictable behavior:
- timeouts apply to each retry attempt, not the total operation
- retry happens after timeout failures
- `background()` runs the fully modified function in a thread

---

## `@sk` Decorator

The `@sk` decorator attaches functionality directly to the original class/function:

### For Classes

```python
def sk(cls_or_func):
    if isinstance(cls_or_func, type):
        cls = cls_or_func
        shared_meta, blocking_methods = analyze_class(cls)
        
        # attach directly to class
        cls._shared_meta = shared_meta
        cls._blocking_methods = blocking_methods
        cls.has_blocking_calls = len(blocking_methods) > 0
        cls.blocking_methods = blocking_methods
        
        def asynced():
            if not blocking_methods:
                raise NotAsyncedError(f"{cls.__name__} has no blocking calls")
            return create_async_class(cls, blocking_methods)
        
        cls.asynced = staticmethod(asynced)
        
        return cls  # return original class, not wrapper
```

### For Functions

```python
    elif callable(cls_or_func):
        func = cls_or_func
        blocking_calls = detect_blocking_calls(func)
        
        # attach attributes
        func.has_blocking_calls = len(blocking_calls) > 0
        func.blocking_calls = blocking_calls
        
        # attach methods
        func.asynced = lambda: Skfunction(func).asynced()
        func.retry = lambda *a, **kw: Skfunction(func).retry(*a, **kw)
        func.timeout = lambda s: Skfunction(func).timeout(s)
        func.background = lambda: Skfunction(func).background()
        
        return func  # return original function
```

The key difference from `Skclass`/`Skfunction` is that `@sk` returns the original object with methods attached, not a wrapper.

---

## Thread Safety

The `sk` module is designed for use from any thread:

- analysis happens once at decoration/wrapping time
- async class creation is idempotent (safe to call multiple times)
- `asyncio.to_thread()` properly handles thread-local state
- `ThreadPoolExecutor` manages background thread lifecycle

---

## Limitations

### Source Code Requirement

Blocking call detection requires access to source code via `inspect.getsource()`.

Functions/methods without available source (built-ins, C extensions, lambda without assignment) cannot be analyzed and will report no blocking calls.

### Static Analysis

Detection is based on static AST analysis, not runtime behavior:

```python
def tricky():
    func = getattr(requests, 'get')
    func("https://example.com")  # not detected (dynamic call)
```

### Timeout Thread Cleanup

The timeout wrapper's daemon thread continues running after timeout. For truly cancellable operations, use the async version with `asyncio.wait_for()`.
