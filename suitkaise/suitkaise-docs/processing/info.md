# How `processing` actually works

`processing` has no dependencies outside of the standard library (except for `cerial`, another suitkaise module).

- uses Python's `multiprocessing` module for subprocess spawning
- uses `suitkaise.cerial` for serialization of complex objects between processes
- all lifecycle methods are timed using `suitkaise.sktime.Timer`
- communication between parent and subprocess happens via `multiprocessing.Queue`

---

## Overview

`processing` uses a subprocess-based architecture.

The parent process creates the `Process` instance, starts the subprocess, waits for results.

The subprocess runs the engine, executing your lifecycle methods.

## Process Lifecycle

### Lifecycle Methods

The `Process` class defines six lifecycle methods that users can override in their inheriting class.

1. `__prerun__()` — Called before each run iteration
2. `__run__()` — REQUIRED - main work — called each iteration
3. `__postrun__()` — Called after each run iteration
4. `__onfinish__()` — Called when process ends (stop/limit reached)
5. `__result__()` — Returns data when process completes successfully
6. `__error__()` — Returns data when process fails and has no lives remaining

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
- All user-defined attributes from `__init__`
- Configuration attributes
- Cycle method references (captured as class attributes)

This allows complex objects (database connections, loggers, custom classes) to be passed to the subprocess without a `PicklingError`.

### Flow

1. **Before start()** — `Process._serialize_with_user()` captures:
   - `instance.__dict__` (all attributes)
   - Class name and lifecycle methods
   - User's custom `__serialize__` if defined

2. **Subprocess** — `Process._deserialize_with_user()` reconstructs:
   - Creates new instance via `__new__` (bypasses `__init__`)
   - Restores all attributes from serialized state
   - Re-attaches lifecycle methods
   - Sets up timed method wrappers

3. **When Complete** — Result and timers serialized back via Queue

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

## Timer System

### Using `sktime`

`processing` uses another `suitkaise` module, `sktime`, to time the lifecycle methods.

`sktime` is a time-tracking module that provides a simple interface for timing code.

The base `Timer` class is used to time the lifecycle methods, the same one that is used in the `@timethis` decorator.

### Automatic Timer Attachment

When a user defines a lifecycle method, `processing` automatically wraps it to provide timer access:

```python
class MyProcess(Process):
    def __run__(self):
        # do work
        pass

# After start()/wait():
p.__run__.timer  # → Timer object
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
# In engine._run_section_timed():
timer = process.timers._ensure_timer(timer_name)
timer.start()
try:
    run_with_timeout(method, timeout, section, current_run)
    timer.stop()  # Only record on success
except ProcessTimeoutError:
    timer.discard()  # Discard failed timing
    raise
except Exception as e:
    timer.discard()  # Discard failed timing
    raise error_class(current_run, e) from e
```

This is the same `start()`/`stop()` pattern used by `sktime.timethis`, with `discard()` for failures.

### ProcessTimers

The `ProcessTimers` class holds all timers:

- `prerun` — Timer for `__prerun__`
- `run` — Timer for `__run__`
- `postrun` — Timer for `__postrun__`
- `onfinish` — Timer for `__onfinish__`
- `result` — Timer for `__result__`
- `error` — Timer for `__error__`
- `full_run` — Aggregates prerun + run + postrun per iteration

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
   - Failed timing already discarded via `timer.discard()`
   - Restart from `__prerun__` of the current run
3. If no lives remain:
   - Call `__error__()`
   - Send error result via Queue

### On Retry

On retry, everything is preserved except the failed timing (discarded via `timer.discard()`).

```python
# In engine._engine_main_inner():
if lives_remaining > 0:
    # Keep user state and run counter - retry current iteration
    # Failed timings already discarded via timer.discard()
    process.config.lives = lives_remaining
    continue  # retry current iteration
```

User state, run counter, and previous times are preserved.

`config.lives` is decremented.

## Timeout System

### Platform Specifics

`processing` uses different timeout strategies per platform:

Unix (Linux/mac) — Signal-based (`SIGALRM`):
- Actually interrupts blocking code
- Uses `signal.alarm()` to trigger after timeout
- Handler raises `ProcessTimeoutError`

Windows — Thread-based (fallback):
- Runs function in daemon thread
- Waits for completion with timeout
- Cannot interrupt blocking code (function thread continues running)
- Detects timeout and raises `ProcessTimeoutError`
- Function thread dies when subprocess terminates

### Timeout Enforcement

Each lifecycle method can have its own timeout:

```python
self.config.timeouts.prerun = 5.0   # 5 second timeout
self.config.timeouts.run = 10.0     # 10 second timeout
self.config.timeouts.result = 2.0   # 2 second timeout
```

When timeout is reached, `ProcessTimeoutError` is raised with:
- Section name (e.g., "run")
- Timeout value
- Current run number

---

## Error Handling

All other errors inherit from `ProcessError`:

### Error Wrapping

Errors in lifecycle methods are caught and wrapped:

```python
# In engine._run_section_timed():
timer.start()
try:
    run_with_timeout(method, timeout, method_name, current_run)
    timer.stop()  # Record successful timing
except ProcessTimeoutError:
    timer.discard()  # Don't record failed timing
    raise
except Exception as e:
    timer.discard()  # Don't record failed timing
    raise error_class(current_run, e) from e
```

The original error is accessible via `e.original_error` when caught:

```python
except ProcessError as e:
    print(e.original_error)  # The original exception
    print(e.current_run)     # Which run it failed on
```

### Error Flow

1. Error occurs in lifecycle method
2. Engine catches and wraps in appropriate error class
3. If lives remain → retry
4. If no lives → call `__error__()`, send error via Queue
5. Parent process raises error when `result` property accessed


## Subprocess Communication

### Queue-Based Messaging

Communication uses `multiprocessing.Queue`.

```python
# Subprocess sends:
result_queue.put({
    'type': 'result',      # or 'error'
    'result': result,       # serialized result
    'timers': timer_bytes,  # serialized ProcessTimers
})

# Parent receives:
message = self._result_queue.get(timeout=...)
```

### Message Types

- `result` — Successful completion with `__result__()` output
- `error` — Failure with exception object

### Result Retrieval

The `result` property blocks until message received.

```python
@property
def result(self):
    if not self._has_result:
        # Block waiting for message
        message = self._result_queue.get()
        
        if message['type'] == 'error':
            self._result = message['error']
        else:
            self._result = message['result']
            # Restore timers
            self.timers = cerial.deserialize(message['timers'])
        
        self._has_result = True
    
    if isinstance(self._result, ProcessError):
        raise self._result
    
    return self._result
```

---

## Process Control

### start()

1. Validates process not already started
2. Creates `multiprocessing.Event` for stop signaling
3. Creates `multiprocessing.Queue` for results
4. Serializes process instance with `cerial`
5. Spawns subprocess with `_engine_main` as target
6. Records start time

### stop()

1. Sets the stop event
2. Does NOT block (returns immediately)
3. Subprocess checks event in `_should_continue()`
4. Subprocess finishes current run, then exits gracefully

### kill()

1. Calls `subprocess.terminate()`
2. Bypasses lives system
3. No cleanup methods called
4. `result` will be `None`

### wait()

1. Calls `subprocess.join(timeout)`
2. Blocks until subprocess completes
3. Returns `True` if finished, `False` if still running
4. Will not return during retries (subprocess keeps running)

---

## Thread Safety

### Parent Process

- `result` property is thread-safe (uses Queue)
- Multiple threads can call `stop()` (Event is thread-safe)
- `wait()` can be called from any thread

### Subprocess

- Single-threaded execution
- No locks needed in engine
- Timers use their own internal locks (from `sktime.Timer`)

---

## Memory Considerations

### In Parent Process

- Process instance kept in memory for result retrieval
- Queue holds serialized result until retrieved
- Timers transferred from subprocess after completion

### In Subprocess

- Full Process instance deserialized
- Timers accumulate measurements in memory
- All state released when subprocess exits

### Large Results

For large results, consider:
- Streaming to files instead of returning directly
- Using shared memory (`multiprocessing.shared_memory`)
- Chunking results across multiple runs

