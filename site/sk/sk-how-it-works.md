/*

synced from suitkaise-docs/sk/how-it-works.md

*/

rows = 2
columns = 1

# 1.1

title = "How `sk` works"

# 1.2

text = "
`<suitkaise-api>sk</suitkaise-api>` attaches modifiers and async support to classes and functions without changing how you call them. It also pre-computes `_shared_meta` for `<suitkaise-api>Share</suitkaise-api>` compatibility.

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           <suitkaise-api>@sk</suitkaise-api> decorator or <suitkaise-api>sk</suitkaise-api>()                            │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         Input: class or function                     │  │
│  └─────────────────────────────────┬────────────────────────────────────┘  │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      AST Analysis (analyzer.py)                     │   │
│  │                                                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │   │
│  │  │ Attribute Reads │  │ Attribute Writes│  │ Blocking Detection  │  │   │
│  │  │ (self.x reads)  │  │ (self.x writes) │  │ (time.sleep, I/O)   │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │   │
│  └─────────────────────────────────┬───────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                          Attach Features                            │   │
│  │                                                                     │   │
│  │  Classes:                      Functions:                           │   │
│  │  - _shared_meta                - has_blocking_calls                 │   │
│  │  - _blocking_methods           - blocking_calls                     │   │
│  │  - .<suitkaise-api>asynced</suitkaise-api>()                  - .<suitkaise-api>asynced</suitkaise-api>()                         │   │
│  │  - Method modifiers            - .<suitkaise-api>retry</suitkaise-api>()                           │   │
│  │                                - .<suitkaise-api>timeout</suitkaise-api>()                         │   │
│  │                                - .<suitkaise-api>background</suitkaise-api>()                      │   │
│  │                                - .rate_limit()                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│                                    ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Return Original (enhanced)                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

## Blocking Detection

The `sk` module detects blocking code to decide whether `.<suitkaise-api>asynced</suitkaise-api>()` and `.<suitkaise-api>background</suitkaise-api>()` are allowed.

### Detection Order

1. Check for `<suitkaise-api>@blocking</suitkaise-api>` decorator - if a function/method has `<suitkaise-api>@blocking</suitkaise-api>`, it's immediately marked as blocking. AST analysis for blocking calls is skipped (performance optimization).

2. AST analysis - if no `<suitkaise-api>@blocking</suitkaise-api>` decorator, parse the source code and look for known blocking patterns.

### Known Blocking Calls

The analyzer maintains a set of known blocking calls:

```python
BLOCKING_CALLS = {
    # time module
    'time.sleep', 'sleep',
    
    # file I/O
    'open', 'read', 'write', 'readline', 'readlines',
    
    # subprocess
    'subprocess.run', 'subprocess.call', 'subprocess.check_call',
    
    # requests
    'requests.get', 'requests.post', 'requests.put', ...
    
    # database connectors
    'sqlite3.connect', 'psycopg2.connect', 'pymysql.connect', ...
    
    # for the whole list, see the blocking calls page
}
```

### Blocking Method Patterns

The analyzer also recognizes method name patterns that typically indicate blocking:

```python
BLOCKING_METHOD_PATTERNS = {
    'sleep', 'wait', 'join',
    'recv', 'send', 'accept', 'connect',
    'read', 'write', 'fetch', 'fetchone', 'fetchall',
    'execute', 'commit', 'rollback',
    # for the whole list, see the blocking calls page
}
```

### How `_BlockingCallVisitor` Works

1. Parse AST - convert function source to abstract syntax tree
2. Visit all `ast.Call` nodes - for each function/method call in the code
3. Extract full name - build the dotted name (`time.sleep`, `self.db.execute`)
4. Check against known patterns:
   - Direct match in `BLOCKING_CALLS`
   - Method name ends with pattern in `BLOCKING_METHOD_PATTERNS`
   - Broad pattern match with I/O context hints

```python
class _BlockingCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.<suitkaise-api>blocking_calls</suitkaise-api>: List[str] = []
    
    def visit_Call(self, node: ast.Call):
        call_name = self._get_call_name(node)
        
        if call_name:
            # check exact match
            if call_name.lower() in BLOCKING_CALLS:
                self.<suitkaise-api>blocking_calls</suitkaise-api>.append(call_name)
            
            # check method pattern
            elif call_name.split('.')[-1] in BLOCKING_METHOD_PATTERNS:
                self.<suitkaise-api>blocking_calls</suitkaise-api>.append(call_name)
        
        self.generic_visit(node)
```



## `_shared_meta` Generation

`_shared_meta` tells `<suitkaise-api>Share</suitkaise-api>` which attributes each method reads and writes. This enables efficient synchronization.

### How `_AttributeVisitor` Works

1. Parse AST - convert method source to abstract syntax tree
2. Visit all Attribute nodes - for each `self.something` access
3. Check context:
   - `ast.Store` context → write (`self.x = 1`)
   - `ast.Load` context → read (`y = self.x`)
4. Handle augmented assignment - `self.x += 1` is both read and write

```python
class _AttributeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.reads: Set[str] = set()
        self.writes: Set[str] = set()
    
    def visit_Attribute(self, node: ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            attr_name = node.attr
            
            if isinstance(node.ctx, ast.Store):
                self.writes.add(attr_name)
            elif isinstance(node.ctx, ast.Load):
                self.reads.add(attr_name)
        
        self.generic_visit(node)
    
    def visit_AugAssign(self, node: ast.AugAssign):
        # self.x += 1 is both read and write
        if isinstance(node.target, ast.Attribute):
            if isinstance(node.target.value, ast.Name) and node.target.value.id == 'self':
                attr_name = node.target.attr
                self.reads.add(attr_name)
                self.writes.add(attr_name)
        
        self.visit(node.value)
```

### `_shared_meta` Structure

```python
_shared_meta = {
    'methods': {
        'increment': {'writes': ['counter']},
        'reset': {'writes': ['counter', 'history']},
        'get_value': {'writes': []},
    },
    'properties': {
        'value': {'reads': ['counter']},
        'is_empty': {'reads': ['counter']},
    },
}
```



## `<suitkaise-api>sk</suitkaise-api>` on Functions

When you apply `<suitkaise-api>sk</suitkaise-api>` to a function (as a decorator or function call):

```python
# as decorator
<suitkaise-api>@sk</suitkaise-api>
def slow_fetch(url):
    return requests.get(url).text

# or as function call
def slow_fetch(url):
    return requests.get(url).text

slow_fetch = <suitkaise-api>sk</suitkaise-api>(slow_fetch)
```

### What Happens

1. Detect blocking calls - check for `<suitkaise-api>@blocking</suitkaise-api>` or analyze AST
2. Attach attributes:
   - `func.<suitkaise-api>has_blocking_calls</suitkaise-api>` - `bool`
   - `func.<suitkaise-api>blocking_calls</suitkaise-api>` - list of detected calls
3. Attach modifier methods - each returns an `Skfunction` for chaining

```python
def <suitkaise-api>sk</suitkaise-api>(func):
    # detect blocking calls
    blocking_calls = detect_blocking(func)
    
    # attach attributes
    func.<suitkaise-api>has_blocking_calls</suitkaise-api> = len(blocking_calls) > 0
    func.<suitkaise-api>blocking_calls</suitkaise-api> = blocking_calls
    
    # attach modifier methods
    func.<suitkaise-api>asynced</suitkaise-api> = lambda: Skfunction(func).<suitkaise-api>asynced</suitkaise-api>()
    func.<suitkaise-api>retry</suitkaise-api> = lambda *args, **kwargs: Skfunction(func).<suitkaise-api>retry</suitkaise-api>(*args, **kwargs)
    func.<suitkaise-api>timeout</suitkaise-api> = lambda seconds: Skfunction(func).<suitkaise-api>timeout</suitkaise-api>(seconds)
    func.<suitkaise-api>background</suitkaise-api> = lambda: Skfunction(func).<suitkaise-api>background</suitkaise-api>()
    func.rate_limit = lambda per_second: Skfunction(func).rate_limit(per_second)
    
    return func  # return original function
```

### Modifier Chaining

When you call a modifier, it creates an `Skfunction` wrapper:

```python
slow_fetch.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)("https://example.com")
```

1. `slow_fetch.<suitkaise-api>retry</suitkaise-api>(3)` → creates `Skfunction` with retry config
2. `.<suitkaise-api>timeout</suitkaise-api>(5.0)` → returns new `Skfunction` with both retry and timeout
3. `("https://example.com")` → executes with both modifiers applied



## `<suitkaise-api>sk</suitkaise-api>` on Classes

When you apply `<suitkaise-api>sk</suitkaise-api>` to a class (as a decorator or function call):

```python
# as decorator
<suitkaise-api>@sk</suitkaise-api>
class Counter:
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1

# or as function call
class Counter:
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1

Counter = <suitkaise-api>sk</suitkaise-api>(Counter)
```

### What Happens

1. Analyze all methods - generate `_shared_meta` and detect blocking calls
2. Attach class-level attributes:
   - `cls._shared_meta` - for `<suitkaise-api>Share</suitkaise-api>` compatibility
   - `cls._blocking_methods` - dict of method → blocking calls
   - `cls.<suitkaise-api>has_blocking_calls</suitkaise-api>` - `bool`
   - `cls.<suitkaise-api>asynced</suitkaise-api>()` - static method returning async class
3. Wrap methods with descriptors - each method gets modifier support

```python
def <suitkaise-api>sk</suitkaise-api>(cls):
    # analyze class
    shared_meta, blocking_methods = analyze_class(cls)
    
    # attach metadata
    cls._shared_meta = shared_meta
    cls._blocking_methods = blocking_methods
    cls.<suitkaise-api>has_blocking_calls</suitkaise-api> = len(blocking_methods) > 0
    
    # attach asynced() static method
    def <suitkaise-api>asynced</suitkaise-api>():
        if not blocking_methods:
            raise <suitkaise-api>SkModifierError</suitkaise-api>(f"{cls.__name__} has no <suitkaise-api>blocking</suitkaise-api> calls")
        return create_async_class(cls, blocking_methods)
    cls.<suitkaise-api>asynced</suitkaise-api> = staticmethod(asynced)
    
    # wrap methods with _ModifiableMethod descriptors
    for name, member in cls.__dict__.items():
        if is_regular_method(member):
            setattr(cls, name, _ModifiableMethod(member))
    
    return cls  # return original class
```

### Method Wrapping

Each method is wrapped with `_ModifiableMethod`, a descriptor that provides modifiers:

```python
class _ModifiableMethod:
    def __init__(self, sync_method, ...):
        self._sync_method = sync_method
    
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return _ModifiableBoundMethod(obj, self._sync_method, ...)
```

When you access a method on an instance, you get a `_ModifiableBoundMethod` that supports:

```python
counter.increment()                    # direct call
counter.increment.asynced()()          # async version using asyncio.to_thread()
counter.increment.retry(3)()           # with retry
counter.increment.timeout(5.0)()       # with timeout
counter.increment.background()()       # returns Future
counter.increment.rate_limit(2.0)()    # rate limited
```



## Async Class Generation

When you call `MyClass.<suitkaise-api>asynced</suitkaise-api>()`, it creates a new class with blocking methods wrapped.

### How `create_async_class` Works

1. Create new class - name it `_Async{ClassName}`
2. Copy all methods - non-blocking methods stay as-is
3. Wrap blocking methods - use `asyncio.to_thread()` wrapper
4. Copy metadata - preserve `_shared_meta` for `Share`

```python
def create_async_class(cls, blocking_methods):
    new_methods = {}
    
    for name in dir(cls):
        method = getattr(cls, name)
        
        if name in blocking_methods:
            # wrap with to_thread
            async def async_wrapper(self, *args, _method=method, **kwargs):
                return await asyncio.to_thread(_method, self, *args, **kwargs)
            new_methods[name] = async_wrapper
        else:
            # keep original
            new_methods[name] = method
    
    # create new class
    async_cls = type(f'_Async{cls.__name__}', (cls,), new_methods)
    async_cls._shared_meta = cls._shared_meta
    
    return async_cls
```



## Modifier Execution Order

Modifiers are always applied in a consistent order, regardless of how you chain them.

1. Rate limit (outermost) - throttles before each attempt
2. Retry (wraps attempts)
3. Timeout (inside retry) - times out each attempt
4. Function call (innermost)


This means these are equivalent:
```python
fn.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)(...)
fn.<suitkaise-api>timeout</suitkaise-api>(5.0).<suitkaise-api>retry</suitkaise-api>(3)(...)
```

Both will
1. Check rate limit
2. Start retry loop (up to 3 attempts)
3. For each attempt, apply 5-second timeout
4. Call the function

### Why Fixed Order Matters

- Timeout inside retry: Each attempt gets 5 seconds. Total time could be 15s.
- Retry inside timeout: All 3 attempts must complete in 5 seconds total.

Making this consistent means you don't have to worry about the exact order every time.

## `Skfunction` Internals

`Skfunction` is the internal wrapper that holds modifier configuration and applies it when you call the function.

### How It Stores Configuration

When you chain modifiers, each one returns a new `Skfunction` with updated config:

1. You call `.<suitkaise-api>retry</suitkaise-api>(3)` on an `Skfunction`
2. It creates a copy of itself with `retry: {times: 3, ...}` added to `_config`
3. You call `.<suitkaise-api>timeout</suitkaise-api>(5.0)` on that copy
4. It creates another copy with `timeout: {seconds: 5.0}` added
5. The final `Skfunction` has both retry and timeout in its `_config` dict

This copy-on-modify pattern is why chaining order doesn't matter - each modifier just adds its config, and execution order is determined at call time.

```python
class Skfunction:
    def __init__(self, func, *, _config=None, _blocking_calls=None):
        self._func = func
        self._config = _config or {}
        self._blocking_calls = _blocking_calls
    
    def _copy_with(self, **config_updates):
        new_config = {**self._config, **config_updates}
        return Skfunction(self._func, _config=new_config, _blocking_calls=self._blocking_calls)
    
    def <suitkaise-api>retry</suitkaise-api>(self, times=3, delay=1.0, backoff_factor=1.0, exceptions=(Exception,)):
        return self._copy_with(retry={'times': times, 'delay': delay, 'backoff_factor': backoff_factor, 'exceptions': exceptions})
    
    def <suitkaise-api>timeout</suitkaise-api>(self, seconds):
        return self._copy_with(timeout={'seconds': seconds})
```

### How Execution Works

When you finally call the `Skfunction` (e.g., `fn.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)("arg")`):

1. Extract all configs - pull retry, timeout, and rate_limit settings from `_config`

2. Check rate limit first - if rate limiting is configured, block until we're allowed to proceed. This happens before any execution attempts.

3. Build the execution function - create an inner function that:
   - If timeout is set: run the real function in a `ThreadPoolExecutor` with a timeout on `future.<suitkaise-api>result</suitkaise-api>()`
   - If no timeout: just call the function directly

4. Apply retry logic - if retry is configured:
   - Loop up to `times` attempts
   - On each failure, sleep for `delay` seconds (multiplied by `backoff_factor` each time)
   - If all attempts fail, raise the last exception

5. Return the result - either from the first successful attempt, or raise if all failed

```python
def __call__(self, *args, **kwargs):
    func = self._func
    retry_config = self._config.get('retry')
    timeout_config = self._config.get('timeout')
    rate_limit_config = self._config.get('rate_limit')
    
    # step 2: check rate limit first
    if rate_limit_config:
        rate_limit_config['limiter'].acquire()
    
    # step 3: build the execution function
    def execute_once():
        if timeout_config:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.<suitkaise-api>result</suitkaise-api>(timeout=timeout_config['seconds'])
                except TimeoutError:
                    raise <suitkaise-api>FunctionTimeoutError</suitkaise-api>(f"{func.__name__} timed out")
        else:
            return func(*args, **kwargs)
    
    # step 4: apply retry logic
    if retry_config:
        sleep_time = retry_config['delay']
        for attempt in range(retry_config['times']):
            try:
                return execute_once()
            except retry_config['exceptions'] as e:
                if attempt < retry_config['times'] - 1:
                    time.sleep(sleep_time)
                    sleep_time *= retry_config['backoff_factor']
                else:
                    raise
    else:
        return execute_once()
```

### Timeout Implementation

Timeouts use a `ThreadPoolExecutor` with a single worker:

1. Submit the function to the executor
2. Call `future.<suitkaise-api>result</suitkaise-api>(timeout=seconds)` which blocks up to the timeout
3. If it times out, raise `<suitkaise-api>FunctionTimeoutError</suitkaise-api>`

This approach can interrupt blocking I/O because the main thread stops waiting, even if the worker thread continues.

---

## `<suitkaise-api>AsyncSkfunction</suitkaise-api>` Internals

Returned by `Skfunction.<suitkaise-api>asynced</suitkaise-api>()` for async execution.

### How It Differs from Sync

The async version follows the same modifier pattern, but:

1. Rate limiting uses `await limiter.acquire_async()` instead of blocking
2. Timeouts use `asyncio.wait_for()` instead of `ThreadPoolExecutor`
3. Function execution uses `asyncio.to_thread()` to run the sync function without blocking the event loop
4. Retry delays use `await asyncio.sleep()` instead of `time.sleep()`

### Execution Flow

1. Check rate limit - await the async limiter if configured
2. Build async execution - create a coroutine that:
   - Wraps the sync function in `asyncio.to_thread()`
   - If timeout is set, wraps that in `asyncio.wait_for()`
3. Apply retry logic - same loop as sync, but using `await` for the execution and `asyncio.sleep()` for delays
4. Return the result - the awaited result from the function

```python
async def __call__(self, *args, **kwargs):
    retry_config = self._config.get('retry')
    timeout_config = self._config.get('timeout')
    rate_limit_config = self._config.get('rate_limit')
    
    # step 1: check rate limit
    if rate_limit_config:
        await rate_limit_config['limiter'].acquire_async()
    
    # step 2: build async execution
    async def execute_once():
        if timeout_config:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(self._func, *args, **kwargs),
                    timeout=timeout_config['seconds'],
                )
            except asyncio.TimeoutError:
                raise <suitkaise-api>FunctionTimeoutError</suitkaise-api>(f"{self._func.__name__} timed out")
        else:
            return await asyncio.to_thread(self._func, *args, **kwargs)
    
    # step 3: apply retry logic
    if retry_config:
        sleep_time = retry_config['delay']
        for attempt in range(retry_config['times']):
            try:
                return await execute_once()
            except retry_config['exceptions'] as e:
                if attempt < retry_config['times'] - 1:
                    await asyncio.sleep(sleep_time)
                    sleep_time *= retry_config['backoff_factor']
                else:
                    raise
    else:
        return await execute_once()
```

---

## Rate Limiter

The rate limiter ensures a maximum number of calls per second using a simple interval-based approach.

### How It Works

1. Calculate minimum interval - if you want 2 calls/second, the minimum interval is 0.5 seconds between calls

2. Track last call time - store when the last call happened

3. On each acquire:
   - Calculate how long since the last call
   - If less than the minimum interval, sleep for the remaining time
   - Update the last call timestamp

4. Thread safety - the sync version uses a lock to prevent race conditions when multiple threads call simultaneously

### Sync vs Async

- Sync `acquire()`: Uses `time.sleep()` and a threading lock
- Async `acquire_async()`: Uses `await asyncio.sleep()` (no lock needed in async context)

```python
class RateLimiter:
    def __init__(self, per_second: float):
        self._per_second = per_second
        self._interval = 1.0 / per_second  # minimum time between calls
        self._last_call = 0.0
        self._lock = threading.Lock()
    
    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait_time = self._interval - (now - self._last_call)
            if wait_time > 0:
                time.sleep(wait_time)
            self._last_call = time.monotonic()
    
    async def acquire_async(self):
        now = time.monotonic()
        wait_time = self._interval - (now - self._last_call)
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        self._last_call = time.monotonic()
```



## Share Integration

When `<suitkaise-api>Share</suitkaise-api>` receives an `<suitkaise-api>@sk</suitkaise-api>`-decorated class, it can use `_shared_meta` for efficient synchronization.

### How It Works

1. `share.counter = Counter()` - share sees `Counter._shared_meta`
2. Share creates proxy that intercepts method calls
3. When `share.counter.increment()` is called:
   - Proxy looks up `_shared_meta['methods']['increment']['writes']`
   - Proxy increments pending counter for `counter.value`
   - Proxy queues the command
4. When reading `share.counter.value`:
   - Proxy looks up `_shared_meta['properties']['value']['reads']`
   - Proxy waits for pending writes to `counter.value`
   - Proxy fetches and returns the value

This ensures reads see the effects of prior writes.
"
