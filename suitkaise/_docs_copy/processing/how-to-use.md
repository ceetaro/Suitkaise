# processing: How to Use

This guide covers all public APIs in `suitkaise.processing`.

```python
from suitkaise.processing import Skprocess, Pool, Share, autoreconnect
```

## `Skprocess`

`Skprocess` is a class-based subprocess. You subclass it and implement `__run__`.

### Basic example

```python
class MyProcess(Skprocess):
    def __init__(self, value):
        self.value = value

    def __run__(self):
        self.value += 1

    def __result__(self):
        return self.value

proc = MyProcess(1)
proc.start()
result = proc.result()
```

### Lifecycle hooks

- `__prerun__`: run before each iteration
- `__run__`: main work (required)
- `__postrun__`: run after each iteration
- `__onfinish__`: run after the final iteration
- `__result__`: produce final result
- `__error__`: invoked if all lives are exhausted

### Control methods

- `start()` starts the subprocess
- `run()` is start + wait + result
- `stop()` requests graceful stop
- `kill()` force terminates
- `wait(timeout=None)` waits for completion
- `result()` returns final result or raises error
- `tell(data)` sends data to the subprocess
- `listen(timeout=None)` receives data from the subprocess

### Timers

Each lifecycle method has a timer:

```python
proc.__run__.timer.mean
proc.process_timer.full_run.mean
```

### Modifiers

Some methods expose modifiers:

- `.timeout(seconds)` for `wait()`, `result()`, `listen()`
- `.background()` to run in background
- `.asynced()` to return awaitables

Example:

```python
await proc.result.asynced()()
proc.result.timeout(2.0)()
```

### Error classes

- `ProcessError` (base)
- `PreRunError`, `RunError`, `PostRunError`
- `OnFinishError`, `ResultError`, `ErrorHandlerError`
- `ProcessTimeoutError`, `ResultTimeoutError`

## `Pool`

`Pool` executes a function or `Skprocess` class over an iterable.

```python
pool = Pool(workers=4)
results = pool.map(fn, data)
```

### Map variants

- `map(fn, iterable)` -> list (ordered)
- `imap(fn, iterable)` -> iterator (ordered)
- `unordered_imap(fn, iterable)` -> iterator (completion order)

### Modifiers

```python
pool.map.timeout(5.0)(fn, data)
pool.map.background()(fn, data)
await pool.map.asynced()(fn, data)
pool.map.star()(fn, iterable_of_tuples)
```

### Using `Skprocess` in `Pool`

```python
results = pool.map(MyProcess, data)
```

Each item is passed to the process constructor.

## `Share`

`Share` provides synchronized shared state across processes.

```python
share = Share()
share.counter = 0
share.data = {}
```

Objects assigned to `Share` become proxied. Reads wait for pending writes; writes are serialized through a coordinator process.

### Best practices

- Prefer simple objects (numbers, dicts, lists)
- For custom classes, decorate with `@sk` for `_shared_meta`

## `ProcessTimers`

`ProcessTimers` is a container of `Sktimer` instances used by `Skprocess`:

- `prerun`, `run`, `postrun`, `onfinish`, `result`, `error`
- `full_run` (aggregate per-iteration timer)

You usually access these via a `Skprocess` instance:

```python
proc.__run__.timer.mean
proc.process_timer.full_run.total_time
```

## `autoreconnect`

Use `@autoreconnect` to rehydrate connections in child processes.

```python
@autoreconnect(**{
    "psycopg2.Connection": {"*": "secret"},
    "redis.Redis": {"*": "redis_pass"},
})
class DBProcess(Skprocess):
    def __init__(self):
        self.db = psycopg2.connect(...)
```

Connections are replaced with live resources before `__run__()` executes.

## Errors

All errors inherit from `ProcessError`:

- `PreRunError`, `RunError`, `PostRunError`
- `OnFinishError`, `ResultError`, `ErrorHandlerError`
- `ProcessTimeoutError`, `ResultTimeoutError`
