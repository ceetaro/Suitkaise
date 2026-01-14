# How `processing` actually works

`processing` has no dependencies outside of the standard library.

- uses Python's `multiprocessing` module for subprocess spawning
- uses `suitkaise.cerial` for serialization of complex objects between processes
- all lifecycle methods are timed using `suitkaise.sktime.Sktimer`
- communication between parent and subprocess happens via `multiprocessing.Queue` and `multiprocessing.Event`

---

## Overview

`processing` uses a subprocess-based architecture.

The parent process creates the `Process` instance, starts the subprocess, waits for results.

The subprocess runs the engine, executing your lifecycle methods.

## Process Lifecycle

### Lifecycle Methods

The `Process` class defines six lifecycle methods that users can override in their inheriting class.

1. `__prerun__()` — called before each run iteration
2. `__run__()` — required - main work — called each iteration
3. `__postrun__()` — called after each run iteration
4. `__onfinish__()` — called when process ends (stop/limit reached)
5. `__result__()` — returns data when process completes successfully
6. `__error__()` — returns data when process fails and has no lives remaining

### How the cycle works

```
start()
    │
    ▼
┌─────────────────────────────────────────┐
│  while _should_continue():              │
│      __prerun__()                       │
│      __run__()                          │
│      __postrun__()                      │
│      _current_run += 1                  │
└─────────────────────────────────────────┘
    │
    ▼
__onfinish__()
    │
    ▼
__result__() or __error__()
    │
    ▼
send result via Queue
    │
    ▼
cleanup queues and exit
```

### Stop Conditions

The run loop stops when any of these conditions are met:

1. `stop_event` is set (via `stop()` or `kill()`)
2. `config.runs` limit reached (`_current_run >= config.runs`)
3. `config.join_in` time limit reached (elapsed time since start)

## Serialization

### How `cerial` is used

`processing` uses another `suitkaise` module, `cerial`, to serialize the entire `Process` instance.

Serializes:
- all user-defined attributes from `__init__`
- configuration attributes
- cycle method references (captured as class attributes)

This allows complex objects (database connections, loggers, custom classes) to be passed to the subprocess without a `PicklingError`.

### Flow

1. **Before start()** — `cerial.serialize()` captures the entire Process instance.
   - `instance.__dict__` (all attributes)
   - class name and lifecycle methods
   - user's custom `__serialize__` if defined

2. **Subprocess** — `cerial.deserialize()` reconstructs.
   - creates new instance via class reconstruction
   - restores all attributes from serialized state
   - re-attaches lifecycle methods
   - sets up timed method wrappers

3. **When Complete** — result and timers serialized back via Queue

### Custom Serialization

If a class defines `__serialize__` and `__deserialize__`, those are called alongside the Process serialization:

```python
class MyProcess(Process):
    def __serialize__(self):
        return {"custom": self.custom_data}
    
    @classmethod
    def __deserialize__(cls, state):
        obj = cls.__new__(cls)
        obj.custom_data = state["custom"]
        return obj
```

---

## Sktimer System

### Using `sktime`

`processing` uses another `suitkaise` module, `sktime`, to time the lifecycle methods.

`sktime` is a time-tracking module that provides a simple interface for timing code.

The base `Sktimer` class is used to time the lifecycle methods, the same one that is used in the `@timethis` decorator.

### Automatic Sktimer Attachment

When a user defines a lifecycle method, `processing` automatically wraps it to provide timer access:

```python
class MyProcess(Process):
    def __run__(self):
        # do work
        pass

# after start()/wait():
p.__run__.timer  # → Sktimer object
```

### TimedMethod Wrapper

The `TimedMethod` class wraps lifecycle methods:

```python
class TimedMethod:
    def __init__(self, method, process, timer_name):
        self._method = method
        self._process = process
        self._timer_name = timer_name
    
    def __call__(self, *args, **kwargs):
        return self._method(*args, **kwargs)
    
    @property
    def timer(self):
        return getattr(self._process.timers, self._timer_name, None)
```

The wrapper is created in `_setup_timed_methods()` during `Process._setup()`.

### How Timing Works

Timing happens in the subprocess (engine), not in the wrapper:

```python
# in engine._run_section_timed():
timer = process.timers._ensure_timer(timer_name)
timer.start()
try:
    run_with_timeout(method, timeout, section, current_run)
    timer.stop()  # only record on success
except ProcessTimeoutError:
    timer.discard()  # discard failed timing
    raise
except Exception as e:
    timer.discard()  # discard failed timing
    raise error_class(current_run, e) from e
```

This is the same `start()`/`stop()` pattern used by `sktime.timethis`, with `discard()` for failures.

### ProcessTimers

The `ProcessTimers` class holds all timers:

- `prerun` — timer for `__prerun__`
- `run` — timer for `__run__`
- `postrun` — timer for `__postrun__`
- `onfinish` — timer for `__onfinish__`
- `result` — timer for `__result__`
- `error` — timer for `__error__`
- `full_run` — aggregates prerun + run + postrun per iteration

The `full_run` timer is updated after each complete iteration:

```python
def _update_full_run(self):
    total = 0.0
    for timer in [self.prerun, self.run, self.postrun]:
        if timer and timer.num_times > 0:
            total += timer.most_recent or 0.0
    if total > 0:
        self.full_run.add_time(total)
```

---

## Lives System

### Retry Mechanism

When an error occurs in `__prerun__`, `__run__`, or `__postrun__`:

1. Decrement `lives_remaining`
2. If lives remain:
   - failed timing already discarded via `timer.discard()`
   - restart from `__prerun__` of the current run
3. If no lives remain:
   - call `__error__()`
   - send error result via Queue

### On Retry

On retry, everything is preserved except the failed timing (discarded via `timer.discard()`).

```python
# in engine._engine_main_inner():
if lives_remaining > 0:
    # keep user state and run counter - retry current iteration
    # failed timings already discarded via timer.discard()
    process.config.lives = lives_remaining
    continue  # retry current iteration
```

User state, run counter, and previous times are preserved.

`config.lives` is decremented.

## Timeout System

### Platform Specifics

`processing` uses different timeout strategies per platform.

Unix (Linux/mac) — signal-based (`SIGALRM`):
- actually interrupts blocking code
- uses `signal.alarm()` to trigger after timeout
- handler raises `ProcessTimeoutError`

Windows — thread-based (fallback):
- runs function in daemon thread
- waits for completion with timeout
- cannot interrupt blocking code (function thread continues running)
- detects timeout and raises `ProcessTimeoutError`
- function thread dies when subprocess terminates

### Timeout Enforcement

Each lifecycle method can have its own timeout.

```python
self.config.timeouts.prerun = 5.0   # 5 second timeout
self.config.timeouts.run = 10.0     # 10 second timeout
self.config.timeouts.result = 2.0   # 2 second timeout
```

When timeout is reached, `ProcessTimeoutError` is raised with:
- section name (e.g., "run")
- timeout value
- current run number

---

## Error Handling

All errors inherit from `ProcessError`.

- `ProcessError` — base class, wraps errors outside lifecycle methods
- `PreRunError` — error in `__prerun__`
- `RunError` — error in `__run__`
- `PostRunError` — error in `__postrun__`
- `OnFinishError` — error in `__onfinish__`
- `ResultError` — error in `__result__`
- `ErrorHandlerError` — error in `__error__` itself
- `ProcessTimeoutError` — timeout reached in any section

Each error wraps the original exception and includes:
- `original_error` — the actual exception that was raised
- `current_run` — which run number the error occurred on

### Error Wrapping

Errors in lifecycle methods are caught and wrapped.

```python
# in engine._run_section_timed():
timer.start()
try:
    run_with_timeout(method, timeout, method_name, current_run)
    timer.stop()  # record successful timing
except ProcessTimeoutError:
    timer.discard()  # don't record failed timing
    raise
except Exception as e:
    timer.discard()  # don't record failed timing
    raise error_class(current_run, e) from e
```

The original error is accessible via `e.original_error` when caught.

```python
except ProcessError as e:
    print(e.original_error)  # the original exception
    print(e.current_run)     # which run it failed on
```

### Error Flow

1. Error occurs in lifecycle method
2. Engine catches and wraps in appropriate error class
3. If lives remain → retry
4. If no lives → call `__error__()`, send error via Queue
5. Parent process raises error when `result()` is called

---

## Subprocess Communication

### Queue-Based Messaging

Communication uses `multiprocessing.Queue`. There are three queues:

1. **result_queue** — subprocess → parent (results and errors)
2. **tell_queue** — parent → subprocess (via `tell()`)
3. **listen_queue** — subprocess → parent (via `listen()`)

```python
# subprocess sends result:
result_queue.put({
    'type': 'result',       # or 'error'
    'data': serialized,     # cerial-serialized result
    'timers': timer_bytes,  # cerial-serialized ProcessTimers
})
```

### tell() and listen()

Parent and subprocess can exchange data during execution:

```python
# parent sends data to subprocess:
p.tell(some_data)

# subprocess receives in __run__:
def __run__(self):
    data = self.listen(timeout=1.0)  # blocks until data arrives
```

Internally, queues are swapped in the subprocess for symmetric API:
- parent's `tell()` puts in `tell_queue` → subprocess's `listen()` gets from it
- subprocess's `tell()` puts in `listen_queue` → parent's `listen()` gets from it

### Message Types

- `result` — successful completion with `__result__()` output
- `error` — failure with exception object or `__error__()` return value

### Result Retrieval

The `wait()` method drains the result queue before waiting for subprocess exit.
This prevents deadlock where the subprocess can't exit because its QueueFeederThread is blocked.

```python
def wait(self, timeout=None):
    # must drain result queue BEFORE waiting for subprocess
    # otherwise deadlock: subprocess can't exit until queue is drained
    self._drain_result_queue(timeout)
    
    self._subprocess.join(timeout=timeout)
    return not self._subprocess.is_alive()

def _drain_result_queue(self, timeout=None):
    """Read result from queue and store internally."""
    if self._has_result or self._result_queue is None:
        return
    
    try:
        message = self._result_queue.get(timeout=timeout or 1.0)
        
        # update timers from subprocess
        if message.get('timers'):
            self.timers = cerial.deserialize(message['timers'])
        
        if message["type"] == "error":
            error_data = cerial.deserialize(message["data"])
            if isinstance(error_data, BaseException):
                self._result = error_data
            else:
                self._result = ProcessError(f"Process failed: {error_data}")
        else:
            self._result = cerial.deserialize(message["data"])
        
        self._has_result = True
    except queue.Empty:
        pass  # no result yet

def result(self):
    """Get result - calls wait() first, then returns stored result."""
    self.wait()
    
    if self._has_result:
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result
    
    return None
```

### Queue Cleanup

Before the subprocess exits, it cancels feeder threads on `tell_queue` and `listen_queue` to allow clean exit:

```python
# in engine._engine_main():
for q in [tell_queue, listen_queue]:
    if q is not None:
        try:
            q.cancel_join_thread()
        except Exception:
            pass
```

This prevents the subprocess from hanging if the parent isn't consuming from these queues.
The `result_queue` is NOT canceled — the parent must call `result()` to get the data.

---

## Process Control

### start()

1. Validates process not already started
2. Serializes process instance with `cerial`
3. Creates `multiprocessing.Event` for stop signaling
4. Creates `multiprocessing.Queue` for results
5. Creates `multiprocessing.Queue` for tell (parent → subprocess)
6. Creates `multiprocessing.Queue` for listen (subprocess → parent)
7. Spawns subprocess with `_engine_main` as target
8. Records start time

### stop()

1. Sets the stop event
2. Does NOT block (returns immediately)
3. Subprocess checks event in `_should_continue()`
4. Subprocess finishes current section, runs `__onfinish__()`, then exits gracefully

### kill()

1. Calls `subprocess.terminate()`
2. Bypasses lives system
3. No cleanup methods called
4. `result()` will return `None`

### wait()

1. Drains result queue first (prevents deadlock)
2. Calls `subprocess.join(timeout)`
3. Blocks until subprocess completes
4. Returns `True` if finished, `False` if still running
5. Will not return during retries (subprocess keeps running)

### result()

1. Calls `wait()` (which drains queue)
2. If result stored, returns it (or raises if it's an exception)
3. Returns `None` if no result available

---

## Thread Safety

### Parent Process

- `result()` is thread-safe (uses Queue)
- multiple threads can call `stop()` (Event is thread-safe)
- `wait()` can be called from any thread
- `tell()` is thread-safe (Queue is thread-safe)
- `listen()` is thread-safe (Queue is thread-safe)

### Subprocess

- single-threaded execution
- no locks needed in engine
- timers use their own internal locks (from `sktime.Sktimer`)

---

## Memory Considerations

### In Parent Process

- process instance kept in memory for result retrieval
- queue holds serialized result until retrieved
- timers transferred from subprocess after completion

### In Subprocess

- full Process instance deserialized
- timers accumulate measurements in memory
- all state released when subprocess exits

### Large Results

For large results, consider:
- streaming to files instead of returning directly
- using shared memory (`multiprocessing.shared_memory`)
- chunking results across multiple runs

---

## Pool

### Overview

The `Pool` class provides batch parallel processing using multiple worker subprocesses.

Like `Process`, it uses `cerial` for serialization, allowing complex objects and `Process` classes.

### Methods

`fc = function or class of type ["processing.Process"]`

- `map(fc, items)` — blocking, returns `[results]`
- `imap(fc, items)` — blocking iterator, yields results in order
- `async_map(fc, items)` — non-blocking, returns `AsyncResult`
- `unordered_imap(fc, items)` — blocking iterator, yields results as completed
- `star(fc)` — modifier to unpack tuple arguments

### How It Works

```python
pool = Pool(workers=4)

# each item is processed in a separate subprocess
results = pool.map(fc, [1, 2, 3, 4])
```

Internally, Pool:
1. Creates worker subprocesses
2. Serializes function and arguments with `cerial`
3. Distributes work across workers
4. Collects and deserializes results
5. Returns results in the same order as input

### Process Classes in Pool

You can use `Process` subclasses in Pool:

```python
class MyProcess(Process):
    def __init__(self, value):
        self.value = value
        self.config.runs = 3
    
    def __run__(self):
        self.value *= 2
    
    def __result__(self):
        return self.value

pool = Pool(workers=2)
results = pool.map(MyProcess, [1, 2, 3, 4])
# → [8, 16, 24, 32] (each ran 3 times, doubling each time)
```

When using `Process` classes:
- full lifecycle is respected (`config.runs`, `config.lives`, `stop()`)
- each instance runs as it normally would
- results collected via `__result__()`