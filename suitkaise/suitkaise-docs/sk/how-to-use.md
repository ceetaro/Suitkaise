# How to use `sk`

`sk` adds powerful modifiers to your functions and classes. No wrapper objects, no changed calls.

`sk`: works as a decorator or a regular function.
- works on functions and classes
- adds `.asynced()`, `.retry()`, `.timeout()`, `.background()`, `.rate_limit()`
- generates `_shared_meta` for Share compatibility
- auto-detects blocking code

`@blocking` decorator: explicitly mark blocking code.
- use when AST detection misses CPU-intensive work
- skips AST analysis (faster)

## Importing

```python
from suitkaise import sk, blocking
```

```python
from suitkaise.sk import FunctionTimeoutError, SkModifierError
```

## `sk` on Functions

Use as a decorator or call directly.

```python
from suitkaise import sk
import requests

# as a decorator
@sk
def fetch_data(url):
    return requests.get(url).json()

# or as a function
def fetch_data(url):
    return requests.get(url).json()

fetch_data = sk(fetch_data)
```

The function works exactly as before:

```python
data = fetch_data("https://api.example.com/data")
```

But now you have modifiers:

```python
# async version
data = await fetch_data.asynced()("https://api.example.com/data")
```
```python
# with retry
data = fetch_data.retry(times=3, delay=1.0)("https://api.example.com/data")
```
```python
# with timeout
data = fetch_data.timeout(5.0)("https://api.example.com/data")
```
```python
# run in background (returns Future)
future = fetch_data.background()("https://api.example.com/data")
result = future.result()
```
```python
# rate limited
data = fetch_data.rate_limit(2.0)("https://api.example.com/data")
```

### Chaining Modifiers

Modifiers can be chained in any order. The execution order is always consistent:

```python
# these are equivalent
data = fetch_data.retry(3).timeout(5.0)("https://example.com")
data = fetch_data.timeout(5.0).retry(3)("https://example.com")
```

Both will retry up to 3 times, with a 5-second timeout per attempt.

### Checking for Blocking Calls

```python
@sk
def slow_fetch(url):
    return requests.get(url).text

print(slow_fetch.has_blocking_calls) # True
print(slow_fetch.blocking_calls) # ['requests.get']
```

## `sk` on Classes

Use as a decorator or call directly.

```python
from suitkaise import sk

# as a decorator
@sk
class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.results = []
    
    def process(self, data):
        # heavy processing
        return transform(data)
    
    def save(self, path):
        with open(path, 'w') as f:
            f.write(json.dumps(self.results))

# or as a function
class DataProcessor:
    ...

DataProcessor = sk(DataProcessor)
```

Use normally:

```python
processor = DataProcessor(config)
processor.process(data)
processor.save("output.json")
```

Use with modifiers:

```python
# async
await processor.process.asynced()(data)

# with timeout
processor.save.timeout(10.0)("output.json")

# with retry
processor.process.retry(3)(data)

# in background
future = processor.save.background()("output.json")
```

### Class Level Async

Get an async version of the entire class:

```python
AsyncProcessor = DataProcessor.asynced()
processor = AsyncProcessor(config)

# all blocking methods are now async
await processor.process(data)
await processor.save("output.json")
```

Only available if the class has blocking calls:

```python
@sk
class Counter:
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1

Counter.asynced()  # raises SkModifierError - no blocking calls
```

### `Share` Compatibility

`@sk` generates `_shared_meta` automatically.

```python
from suitkaise.processing import Share

@sk
class Counter:
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1

share = Share()
share.counter = Counter()

# works across processes
share.counter.increment()
print(share.counter.value)
```

## `@blocking` Decorator

Explicitly mark code as blocking when AST detection doesn't catch it.

### On Functions

```python
from suitkaise import sk, blocking

@sk
@blocking
def heavy_computation():
    # CPU intensive work that AST can't detect
    return sum(x**2 for x in range(10_000_000))

# now .asynced() and .background() are available
result = await heavy_computation.asynced()()
```

### On Methods

```python
@sk
class Worker:
    @blocking
    def compute(self):
        # CPU-intensive work
        return complex_calculation()
    
    def quick_check(self):
        # not blocking
        return self.ready

# compute is blocking, quick_check is not
print(Worker._blocking_methods)  # {'compute': ['@blocking']}
```

### Why use `@blocking`?

AST detection looks for known patterns like `time.sleep()`, `requests.get()`, file I/O, database calls, etc.

But it can't detect:
- pure CPU work (tight loops, number crunching)
- C extensions that block
- Custom blocking functions

Use `@blocking` when you know code will block the event loop.


## Modifiers reference

### `.asynced()`

Run the function asynchronously using `asyncio.to_thread()`.

```python
result = await fetch_data.asynced()("https://example.com")
```

Requirements:
- Function must have blocking calls
- Or be decorated with `@blocking`

Raises:
- `SkModifierError` if function has no blocking calls

### `.retry(times, delay, backoff_factor, exceptions)`

Retry on failure with configurable backoff.

```python
# basic: 3 attempts, 1 second delay
result = fetch_data.retry(times=3)("https://example.com")

# with exponential backoff
result = fetch_data.retry(
    times=5,
    delay=1.0,
    backoff_factor=2.0,  # 1s, 2s, 4s, 8s between retries
)("https://example.com")

# only retry specific exceptions
result = fetch_data.retry(
    times=3,
    exceptions=(ConnectionError, TimeoutError),
)("https://example.com")
```

Arguments:
- `times`: Maximum attempts (default: 3)
- `delay`: Initial delay between retries in seconds (default: 1.0)
- `backoff_factor`: Multiply delay after each retry (default: 1.0)
- `exceptions`: Exception types to retry on (default: all)

### `.timeout(seconds)`

Raise error if execution exceeds time limit.

```python
try:
    result = fetch_data.timeout(5.0)("https://slow-api.com")
except FunctionTimeoutError:
    print("Request timed out")
```

Arguments:
- `seconds`: Maximum execution time

Raises:
- `FunctionTimeoutError` if timeout exceeded

### `.background()`

Run in a background thread, return `Future` immediately.

```python
future = fetch_data.background()("https://example.com")

# do other work...

# block when you need the result
result = future.result()
```

Returns:
- `concurrent.futures.Future`

### `.rate_limit(per_second)`

Throttle calls to a maximum rate.

```python
# max 2 calls per second
result = fetch_data.rate_limit(2.0)("https://example.com")
```

Arguments:
- `per_second`: Maximum calls per second



## Async Modifiers

When using `.asynced()`, you can chain async-compatible modifiers:

```python
# async with timeout
result = await fetch_data.asynced().timeout(5.0)("https://example.com")

# async with retry
result = await fetch_data.asynced().retry(3)("https://example.com")

# async with rate limit
result = await fetch_data.asynced().rate_limit(2.0)("https://example.com")

# chain multiple
result = await fetch_data.asynced().retry(3).timeout(10.0)("https://example.com")
```



## Modifier Execution Order

Modifiers always execute in this order, regardless of chain order:

1. Rate limit (outermost) - throttle before each attempt
2. Retry - retry loop
3. Timeout - per-attempt timeout
4. Function call (innermost)

This means:

```python
# both of these:
fn.retry(3).timeout(5.0)
fn.timeout(5.0).retry(3)

# execute as:
# 1. for each of 3 attempts:
# 2.   start 5-second timer
# 3.   call function
# 4.   if timeout or error, retry
```



## Error Handling

### `SkModifierError`

Raised when an invalid modifier is used.

```python
from suitkaise.sk import SkModifierError

@sk
def quick_fn():
    return 42

try:
    await quick_fn.asynced()()
except SkModifierError as e:
    print(e)  # "quick_fn has no blocking calls"
```

### `FunctionTimeoutError`

Raised when `.timeout()` is exceeded.

```python
from suitkaise.sk import FunctionTimeoutError

try:
    result = slow_fn.timeout(1.0)()
except FunctionTimeoutError as e:
    print(e)  # "slow_fn timed out after 1.0 seconds"
```



## Properties

### On Functions

After `@sk`:

```python
@sk
def my_fn():
    time.sleep(1)

my_fn.has_blocking_calls # True
my_fn.blocking_calls # ['time.sleep']
```

### On Classes

After `@sk`:

```python
@sk
class MyClass:
    def blocking_method(self):
        time.sleep(1)
    
    def quick_method(self):
        return 42

MyClass.has_blocking_calls # True
MyClass._blocking_methods # {'blocking_method': ['time.sleep']}
MyClass._shared_meta # {'methods': {...}, 'properties': {...}}
```