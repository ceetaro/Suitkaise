# sk: How it Works

The `sk` module attaches modifiers and async support to classes and functions without changing call sites. It also generates `_shared_meta` for `Share` compatibility.

Core files:

- `suitkaise/sk/api.py` (public API)
- `suitkaise/sk/_int/analyzer.py` (AST analysis)
- `suitkaise/sk/_int/asyncable.py` (descriptor/modifier system)
- `suitkaise/sk/_int/function_wrapper.py` (retry/timeout/rate limit wrappers)
- `suitkaise/sk/_int/async_wrapper.py` (async class generation)

## Blocking detection

Blocking detection is used to decide whether `.asynced()` and `.background()` are allowed.

1. If a function/method is decorated with `@blocking`, it is treated as blocking.
2. Otherwise, `analyzer._BlockingCallVisitor` parses the AST and looks for known blocking call patterns.

Results:

- For functions: `func.has_blocking_calls`, `func.blocking_calls`
- For classes: `cls._blocking_methods` mapping method -> calls

## `@sk` on functions

`sk(func)` attaches methods directly to the original function:

- `asynced()` -> returns an `AsyncSkfunction` (uses `asyncio.to_thread`)
- `retry(times, delay, backoff_factor, exceptions)`
- `timeout(seconds)`
- `background()`
- `rate_limit(per_second)`

Internally, these methods instantiate a temporary `Skfunction` wrapper which holds config and applies modifiers in a fixed order:

1. Rate limit
2. Retry
3. Timeout
4. Function call

## `@sk` on classes

`sk(cls)` performs analysis and modifies methods on the class:

- Generates `_shared_meta` (method/property read/write sets)
- Creates `cls.asynced()` which returns an async class if blocking methods exist
- Wraps methods with `_ModifiableMethod` / `_AsyncModifiableMethod`

These descriptors expose the same modifiers on instance methods:

- `.asynced()`
- `.retry()`
- `.timeout()`
- `.background()`
- `.rate_limit()`

## Async class generation

`async_wrapper.create_async_class` generates a new class:

- Name: `_Async{ClassName}`
- Blocking methods run in `asyncio.to_thread`
- Non-blocking methods stay synchronous
- Metadata copied and `_shared_meta` preserved

## Modifier internals

### Retry

`create_retry_wrapper` retries `times` with exponential backoff:

```
sleep_time = delay
for attempt in range(times):
    try: return func()
    except exceptions:
        if attempt < times - 1:
            time.sleep(sleep_time)
            sleep_time *= backoff_factor
```

### Timeout

Sync timeouts use a `ThreadPoolExecutor` and raise `FunctionTimeoutError` if exceeded.  
Async timeouts use `asyncio.wait_for`.

### Background

`background()` uses a thread pool and returns a `Future` immediately.

### Rate limiting

`RateLimiter` uses a per-second token-bucket style mechanism and supports both sync and async acquire calls.

## Share integration

`analyzer.analyze_class` inspects class methods and properties, collecting:

- attributes read
- attributes written
- blocking calls

This information is encoded in `_shared_meta` so `Share` can synchronize access safely across processes.
