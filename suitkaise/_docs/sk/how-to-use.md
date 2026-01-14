# How to use the `sk` module

The `sk` module gives your classes and functions special powers.

By just using `sk`, you get...

### `.retry()`

Automatically retry on failure, with an option to exponentially increase the delay between retries.

Available for functions and methods of classes.

Arguments
- `times`: maximum number of attempts (default `3`)
- `delay`: delay between retries in seconds (default `1.0`)
- `backoff_factor`: multiplier for delay after each retry (default `1.0`)
- `exceptions`: tuple of exception types to retry on (default: `(Exception,)`)

```python
result = function.retry(times=3, delay=1.0, backoff_factor=2.0)(args, kwargs)
```

### `.timeout()`

Set a timeout period for the function/method.

Available for functions and methods of classes.

Arguments
- `seconds`: maximum execution time in seconds (default `5.0`)

```python
result = function.timeout(5.0)(args, kwargs)
```

### `.background()`

Run the function/method in a background thread.

Available for functions and methods of classes.

Returns a `concurrent.Future` object.

```python
future = function.background()(args, kwargs)
result = future.result()
```

### `asynced()`

An async version of the function/method.

Available for functions and methods of classes that have blocking calls like `time.sleep()`, `requests.get()`, ...

Returns a coroutine that can be awaited.

This will raise a `NotAsyncedError` if the function has no blocking calls.

```python
def my_function():
    time.sleep(1)
    return "Hello, world!"

async_my_function = my_function.asynced()
result = await async_my_function(args, kwargs)
```

```python
# or...
result = await my_function.asynced()(args, kwargs)
```

### Pre-computed shared state metadata

Classes and functions get precalculated data to work with `suitkaise.processing.Share` instances, saving you time and memory during runtime.

This is more important than you think it is.



## How to use `sk`

### `@sk` decorator

Works on both classes and functions.

```python
from suitkaise.sk import sk

@sk
class MyClass:
    ...

@sk
def my_function():
    ...
```

### `sk()` function

Works on both classes and functions.

```python
from suitkaise.sk import sk

# precompute shared state metadata for large classes and functions
for obj in large_sized_objects:
    sk(obj)
```

### Extra Properties You Get

- `.has_blocking_calls` - whether the class or function has blocking calls

- `.blocking_methods` - a `dict` of method names to their blocking calls. For functions, this just returns all blocking calls within that function (in the same `dict` format as classes)

### Async Usage With A Class

```python
from suitkaise.sk import sk
from suitkaise import timing
import requests

@sk
class WebpageHTMLFetcher:
"""A class that fetches the HTML content of a webpage."""

    def __init__(self, url):
        self.url = url
    
    def fetch(self):
        return requests.get(self.url).content

# get a regular class instance
fetcher = WebpageHTMLFetcher("https://api.example.com")

# regular sync call - will block until the request is complete
result = fetcher.fetch()


# get an async version of the class
try:
    WebpageHTMLFetcher_Async = WebpageHTMLFetcher.asynced()
except NotAsyncedError:
    print("WebpageHTMLFetcher has no blocking calls")
    raise

async_fetcher = WebpageHTMLFetcher_Async("https://api.example.com")

# retry async call (using asyncio.to_thread) 3 times with a 10 second timeout
try:
    result = await async_fetcher.fetch.retry(times=3).timeout(10.0)("https://api.example.com")
except Exception as e:
    raise e
```

### Async Usage With A Function

```python
from suitkaise.sk import sk
import requests

@sk
def fetch_data(url):
    return requests.get(url).text

# regular sync call
result = fetch_data("https://example.com")

# async version using asyncio.to_thread()
result = await fetch_data.asynced()("https://example.com")

# combine modifiers
future = fetch_data.retry(times=3).timeout(10.0).background()("https://example.com")
try:
    result = future.result()
except Exception as e:
    raise e
```

---


### Chaining Modifiers

Modifiers can be chained in any order without affecting the behavior.

When using `retry()` and `timeout()`, the timeout is applied to each retry attempt, not overall.

```python
# equivalent
result = sk_fetch.retry(3).timeout(10.0)("https://api.com")
result = sk_fetch.timeout(10.0).retry(3)("https://api.com")

# 1. retry (outermost) — retries the whole operation
# 2. timeout (inside retry) — each attempt has a timeout
# 3. function call (innermost)
```

```python
# async with timeout
result = await sk_fetch.asynced().timeout(5.0)("https://api.com")

# async with retry
result = await sk_fetch.asynced().retry(3, delay=1.0, backoff_factor=2.0)("https://api.com")

# async with both (order doesn't matter)
result = await sk_fetch.asynced().retry(3).timeout(10.0)("https://api.com")
result = await sk_fetch.asynced().timeout(10.0).retry(3)("https://api.com")
```


## Blocking Calls

How does `sk` detect blocking calls?

These are the detected blocking calls.

- `time.sleep`, `timing.sleep`, ...
- `requests.get`, `requests.post`, ...
- file operations (`open`, `read`, `write`)
- database operations (`cursor.execute`, `connection.commit`, ...)
- network operations (`socket`, `urllib`)
- subprocess operations (`subprocess.run`, `subprocess.Popen`, ...)
- suitkaise operations (`Pool.map`, `Circuit.short`, `Circuit.trip`, ...)

```python
@sk
class MyClass:

    def blocking_method(self):
        timing.sleep(1)

        response = requests.get("https://api.com")

        with open("file.txt") as f:
            data = f.read()

        return response.text, data

    def non_blocking_method(self):
        return "Hello, world!"

print(MyClass.has_blocking_calls) # True

print(MyClass.blocking_methods) # {'blocking_method': ['time.sleep', 'requests.get', 'open']}
```

## Errors

### `NotAsyncedError`

Raised when calling `.asynced()` on a class or function with no detected blocking calls.

```python
from suitkaise.sk import NotAsyncedError

try:
    AsyncVersion = NonBlockingClass.asynced()
except NotAsyncedError as e:
    print(f"Cannot create async version: {e}")
```

### `FunctionTimeoutError`

Raised when a function exceeds its timeout limit.

```python
from suitkaise.sk import FunctionTimeoutError

try:
    result = sk_func.timeout(1.0)()
except FunctionTimeoutError as e:
    print(f"Function timed out: {e}")
```
