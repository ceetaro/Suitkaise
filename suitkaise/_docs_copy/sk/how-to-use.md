# sk: How to Use

This guide covers the public API from `suitkaise.sk`.

```python
from suitkaise import sk, blocking
from suitkaise.sk import FunctionTimeoutError, SkModifierError
```

## `@sk` decorator

### For functions

```python
@sk
def slow_fetch(url):
    return requests.get(url).text
```

Available modifiers on the function:

- `slow_fetch.asynced()`
- `slow_fetch.retry(times=3, delay=1.0, backoff_factor=1.0, exceptions=(Exception,))`
- `slow_fetch.timeout(seconds)`
- `slow_fetch.background()`
- `slow_fetch.rate_limit(per_second)`

Example:

```python
result = slow_fetch.retry(3).timeout(5.0)("https://example.com")
```

### For classes

```python
@sk
class Worker:
    def compute(self):
        return sum(range(1_000_000))
```

The decorator:

- Adds `_shared_meta` for Share compatibility
- Wraps methods with the same modifiers as functions
- Adds `Worker.asynced()` if blocking calls are detected

Example:

```python
AsyncWorker = Worker.asynced()
worker = AsyncWorker()
await worker.compute.asynced()()
```

## `@blocking` decorator

Explicitly mark a function or method as blocking if AST detection is insufficient:

```python
@sk
@blocking
def heavy_cpu():
    return sum(range(10_000_000))
```

On a class method:

```python
@sk
class Worker:
    @blocking
    def heavy_cpu(self):
        return sum(range(10_000_000))
```

## Errors

- `SkModifierError`: raised when `.asynced()` is called on non-blocking code
- `FunctionTimeoutError`: raised by `.timeout()` when the function exceeds the limit

## Modifier semantics

Modifiers are chainable and apply in a consistent internal order:

1. Rate limit
2. Retry
3. Timeout
4. Function call

This means these are equivalent:

```python
f.retry(3).timeout(5.0)(...)
f.timeout(5.0).retry(3)(...)
```

## Async variants

If blocking calls are detected, `.asynced()` uses `asyncio.to_thread()` internally:

```python
await slow_fetch.asynced()("https://example.com")
```

Async functions exposed via `.asynced()` still support:

- `.timeout(...)`
- `.retry(...)`
- `.rate_limit(...)`

## `AsyncSkfunction`

`AsyncSkfunction` is returned by `Skfunction.asynced()` and by `@sk`-decorated functions.
You typically do not instantiate it directly.

```python
async_fn = slow_fetch.asynced()
result = await async_fn.timeout(5.0)("https://example.com")
```
