# How to use `<suitkaise-api>sk</suitkaise-api>`

`<suitkaise-api>sk</suitkaise-api>` adds powerful modifiers to your functions and classes. No wrapper objects, no changed calls.

`<suitkaise-api>sk</suitkaise-api>`: works as a decorator or a regular function.
- works on functions and classes
- adds `.<suitkaise-api>asynced</suitkaise-api>()`, `.<suitkaise-api>retry</suitkaise-api>()`, `.<suitkaise-api>timeout</suitkaise-api>()`, `.<suitkaise-api>background</suitkaise-api>()`, `.rate_limit()`
- generates `_shared_meta` for Share compatibility
- auto-detects blocking code

`@<suitkaise-api>blocking</suitkaise-api>` decorator: explicitly mark blocking code.
- use when AST detection misses CPU-intensive work
- skips AST analysis (faster)

## Importing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>, <suitkaise-api>blocking</suitkaise-api>
```

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>sk</suitkaise-api> import <suitkaise-api>FunctionTimeoutError</suitkaise-api>, <suitkaise-api>SkModifierError</suitkaise-api>
```

## `<suitkaise-api>sk</suitkaise-api>` on Functions

Use as a decorator or call directly.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>
import requests

# as a decorator
@<suitkaise-api>sk</suitkaise-api>
def fetch_data(url):
    return requests.get(url).json()

# or as a function
def fetch_data(url):
    return requests.get(url).json()

fetch_data = <suitkaise-api>sk</suitkaise-api>(fetch_data)
```

The function works exactly as before:

```python
data = fetch_data("https://api.example.com/data")
```

But now you have modifiers:

```python
# async version
data = await fetch_data.<suitkaise-api>asynced</suitkaise-api>()("https://api.example.com/data")
```
```python
# with retry
data = fetch_data.<suitkaise-api>retry</suitkaise-api>(times=3, delay=1.0)("https://api.example.com/data")
```
```python
# with timeout
data = fetch_data.<suitkaise-api>timeout</suitkaise-api>(5.0)("https://api.example.com/data")
```
```python
# <suitkaise-api>run</suitkaise-api> in <suitkaise-api>background</suitkaise-api> (returns Future)
future = fetch_data.<suitkaise-api>background</suitkaise-api>()("https://api.example.com/data")
<suitkaise-api>result</suitkaise-api> = future.<suitkaise-api>result</suitkaise-api>()
```
```python
# rate limited
data = fetch_data.rate_limit(2.0)("https://api.example.com/data")
```

### Chaining Modifiers

Modifiers can be chained in any order. The execution order is always consistent:

```python
# these are equivalent
data = fetch_data.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)("https://example.com")
data = fetch_data.<suitkaise-api>timeout</suitkaise-api>(5.0).<suitkaise-api>retry</suitkaise-api>(3)("https://example.com")
```

Both will retry up to 3 times, with a 5-second timeout per attempt.

### Checking for Blocking Calls

```python
@<suitkaise-api>sk</suitkaise-api>
def slow_fetch(url):
    return requests.get(url).text

print(slow_fetch.<suitkaise-api>has_blocking_calls</suitkaise-api>) # True
print(slow_fetch.<suitkaise-api>blocking_calls</suitkaise-api>) # ['requests.get']
```

## `<suitkaise-api>sk</suitkaise-api>` on Classes

Use as a decorator or call directly.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>

# as a decorator
@<suitkaise-api>sk</suitkaise-api>
class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.results = []
    
    def process(self, data):
        # heavy <suitkaise-api>processing</suitkaise-api>
        return transform(data)
    
    def save(self, path):
        with open(path, 'w') as f:
            f.write(json.dumps(self.results))

# or as a function
class DataProcessor:
    ...

DataProcessor = <suitkaise-api>sk</suitkaise-api>(DataProcessor)
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
await processor.process.<suitkaise-api>asynced</suitkaise-api>()(data)

# with timeout
processor.save.<suitkaise-api>timeout</suitkaise-api>(10.0)("output.json")

# with retry
processor.process.<suitkaise-api>retry</suitkaise-api>(3)(data)

# in background
future = processor.save.<suitkaise-api>background</suitkaise-api>()("output.json")
```

### Class Level Async

Get an async version of the entire class:

```python
AsyncProcessor = DataProcessor.<suitkaise-api>asynced</suitkaise-api>()
processor = AsyncProcessor(config)

# all <suitkaise-api>blocking</suitkaise-api> methods are now async
await processor.process(data)
await processor.save("output.json")
```

Only available if the class has blocking calls:

```python
@<suitkaise-api>sk</suitkaise-api>
class Counter:
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1

Counter.<suitkaise-api>asynced</suitkaise-api>()  # raises <suitkaise-api>SkModifierError</suitkaise-api> - no <suitkaise-api>blocking</suitkaise-api> calls
```

### `<suitkaise-api>Share</suitkaise-api>` Compatibility

`@<suitkaise-api>sk</suitkaise-api>` generates `_shared_meta` automatically.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
class Counter:
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1

share = <suitkaise-api>Share</suitkaise-api>()
share.counter = Counter()

# works across processes
share.counter.increment()
print(share.counter.value)
```

## `@<suitkaise-api>blocking</suitkaise-api>` Decorator

Explicitly mark code as blocking when AST detection doesn't catch it.

### On Functions

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>sk</suitkaise-api>, <suitkaise-api>blocking</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
@<suitkaise-api>blocking</suitkaise-api>
def heavy_computation():
    # CPU intensive work that AST can't detect
    return sum(x**2 for x in range(10_000_000))

# now .<suitkaise-api>asynced</suitkaise-api>() and .<suitkaise-api>background</suitkaise-api>() are available
<suitkaise-api>result</suitkaise-api> = await heavy_computation.<suitkaise-api>asynced</suitkaise-api>()()
```

### On Methods

```python
@<suitkaise-api>sk</suitkaise-api>
class Worker:
    @<suitkaise-api>blocking</suitkaise-api>
    def compute(self):
        # CPU-intensive work
        return complex_calculation()
    
    def quick_check(self):
        # not <suitkaise-api>blocking</suitkaise-api>
        return self.ready

# compute is <suitkaise-api>blocking</suitkaise-api>, quick_check is not
print(Worker._blocking_methods)  # {'compute': ['@<suitkaise-api>blocking</suitkaise-api>']}
```

### Why use `@<suitkaise-api>blocking</suitkaise-api>`?

AST detection looks for known patterns like `time.sleep()`, `requests.get()`, file I/O, database calls, etc.

But it can't detect:
- pure CPU work (tight loops, number crunching)
- C extensions that block
- Custom blocking functions

Use `@<suitkaise-api>blocking</suitkaise-api>` when you know code will block the event loop.


## Modifiers reference

### `.<suitkaise-api>asynced</suitkaise-api>()`

Run the function asynchronously using `asyncio.to_thread()`.

```python
<suitkaise-api>result</suitkaise-api> = await fetch_data.<suitkaise-api>asynced</suitkaise-api>()("https://example.com")
```

Requirements:
- Function must have blocking calls
- Or be decorated with `@<suitkaise-api>blocking</suitkaise-api>`

Raises:
- `<suitkaise-api>SkModifierError</suitkaise-api>` if function has no blocking calls

### `.<suitkaise-api>retry</suitkaise-api>(times, delay, backoff_factor, exceptions)`

Retry on failure with configurable backoff.

```python
# basic: 3 attempts, 1 second delay
<suitkaise-api>result</suitkaise-api> = fetch_data.<suitkaise-api>retry</suitkaise-api>(times=3)("https://example.com")

# with exponential backoff
<suitkaise-api>result</suitkaise-api> = fetch_data.<suitkaise-api>retry</suitkaise-api>(
    times=5,
    delay=1.0,
    backoff_factor=2.0,  # 1s, 2s, 4s, 8s between retries
)("https://example.com")

# only retry specific exceptions
<suitkaise-api>result</suitkaise-api> = fetch_data.<suitkaise-api>retry</suitkaise-api>(
    times=3,
    exceptions=(ConnectionError, TimeoutError),
)("https://example.com")
```

Arguments:
- `times`: Maximum attempts (default: 3)
- `delay`: Initial delay between retries in seconds (default: 1.0)
- `backoff_factor`: Multiply delay after each retry (default: 1.0)
- `exceptions`: Exception types to retry on (default: all)

### `.<suitkaise-api>timeout</suitkaise-api>(seconds)`

Raise error if execution exceeds time limit.

```python
try:
    <suitkaise-api>result</suitkaise-api> = fetch_data.<suitkaise-api>timeout</suitkaise-api>(5.0)("https://slow-api.com")
except <suitkaise-api>FunctionTimeoutError</suitkaise-api>:
    print("Request timed out")
```

Arguments:
- `seconds`: Maximum execution time

Raises:
- `<suitkaise-api>FunctionTimeoutError</suitkaise-api>` if timeout exceeded

### `.<suitkaise-api>background</suitkaise-api>()`

Run in a background thread, return `Future` immediately.

```python
future = fetch_data.<suitkaise-api>background</suitkaise-api>()("https://example.com")

# do other work...

# block when you need the <suitkaise-api>result</suitkaise-api>
<suitkaise-api>result</suitkaise-api> = future.<suitkaise-api>result</suitkaise-api>()
```

Returns:
- `concurrent.futures.Future`

### `.rate_limit(per_second)`

Throttle calls to a maximum rate.

```python
# max 2 calls per second
<suitkaise-api>result</suitkaise-api> = fetch_data.rate_limit(2.0)("https://example.com")
```

Arguments:
- `per_second`: Maximum calls per second



## Async Modifiers

When using `.<suitkaise-api>asynced</suitkaise-api>()`, you can chain async-compatible modifiers:

```python
# async with timeout
<suitkaise-api>result</suitkaise-api> = await fetch_data.<suitkaise-api>asynced</suitkaise-api>().<suitkaise-api>timeout</suitkaise-api>(5.0)("https://example.com")

# async with retry
<suitkaise-api>result</suitkaise-api> = await fetch_data.<suitkaise-api>asynced</suitkaise-api>().<suitkaise-api>retry</suitkaise-api>(3)("https://example.com")

# async with rate limit
<suitkaise-api>result</suitkaise-api> = await fetch_data.<suitkaise-api>asynced</suitkaise-api>().rate_limit(2.0)("https://example.com")

# chain multiple
<suitkaise-api>result</suitkaise-api> = await fetch_data.<suitkaise-api>asynced</suitkaise-api>().<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(10.0)("https://example.com")
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
fn.<suitkaise-api>retry</suitkaise-api>(3).<suitkaise-api>timeout</suitkaise-api>(5.0)
fn.<suitkaise-api>timeout</suitkaise-api>(5.0).<suitkaise-api>retry</suitkaise-api>(3)

# execute as:
# 1. for each of 3 attempts:
# 2.   start 5-second timer
# 3.   call function
# 4.   if timeout or <suitkaise-api>error</suitkaise-api>, retry
```



## Error Handling

### `<suitkaise-api>SkModifierError</suitkaise-api>`

Raised when an invalid modifier is used.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>sk</suitkaise-api> import <suitkaise-api>SkModifierError</suitkaise-api>

@<suitkaise-api>sk</suitkaise-api>
def quick_fn():
    return 42

try:
    await quick_fn.<suitkaise-api>asynced</suitkaise-api>()()
except <suitkaise-api>SkModifierError</suitkaise-api> as e:
    print(e)  # "quick_fn has no <suitkaise-api>blocking</suitkaise-api> calls"
```

### `<suitkaise-api>FunctionTimeoutError</suitkaise-api>`

Raised when `.<suitkaise-api>timeout</suitkaise-api>()` is exceeded.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>sk</suitkaise-api> import <suitkaise-api>FunctionTimeoutError</suitkaise-api>

try:
    <suitkaise-api>result</suitkaise-api> = slow_fn.<suitkaise-api>timeout</suitkaise-api>(1.0)()
except <suitkaise-api>FunctionTimeoutError</suitkaise-api> as e:
    print(e)  # "slow_fn timed out after 1.0 seconds"
```



## Properties

### On Functions

After `@<suitkaise-api>sk</suitkaise-api>`:

```python
@<suitkaise-api>sk</suitkaise-api>
def my_fn():
    time.sleep(1)

my_fn.<suitkaise-api>has_blocking_calls</suitkaise-api> # True
my_fn.<suitkaise-api>blocking_calls</suitkaise-api> # ['time.sleep']
```

### On Classes

After `@<suitkaise-api>sk</suitkaise-api>`:

```python
@<suitkaise-api>sk</suitkaise-api>
class MyClass:
    def blocking_method(self):
        time.sleep(1)
    
    def quick_method(self):
        return 42

MyClass.<suitkaise-api>has_blocking_calls</suitkaise-api> # True
MyClass._blocking_methods # {'blocking_method': ['time.sleep']}
MyClass._shared_meta # {'methods': {...}, 'properties': {...}}
```