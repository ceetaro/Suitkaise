# processing: How it Works

The `processing` module provides process-based execution (`Skprocess`), parallel batch execution (`Pool`), and shared state (`Share`). Internals live in `suitkaise/processing/_int/`.

## `Skprocess` architecture

### Lifecycle model

`Skprocess` is a class-based subprocess model with explicit lifecycle hooks:

- `__prerun__()` (optional)
- `__run__()` (required)
- `__postrun__()` (optional)
- `__onfinish__()` (optional)
- `__result__()` (optional)
- `__error__()` (optional)

Each run iteration is timed, error-wrapped, and optionally retried.

### Process config

The configuration object is `ProcessConfig` (`_int/config.py`):

- `runs`: number of run iterations
- `join_in`: number of iterations before syncing state
- `lives`: number of retries on failure
- `timeouts`: per-section timeout configuration

### Timed methods

During `_setup()`, each lifecycle method is wrapped by `TimedMethod`:

- `__prerun__.timer`, `__run__.timer`, etc. are `Sktimer` instances
- Timers are aggregated into `ProcessTimers`
- Full iteration time is captured in `ProcessTimers.full_run`

### Engine entry point

Subprocesses start in `_engine_main` (`_int/engine.py`):

1. Deserialize the `Skprocess` instance with cerial
2. Initialize queues/events
3. Run `_engine_main_inner` loop

### Execution loop (simplified)

```
while lives_remaining > 0:
    while _should_continue():
        __prerun__()
        __run__()
        __postrun__()
        current_run += 1
    _run_finish_sequence()
    return success
except errors:
    lives_remaining -= 1
    if lives_remaining == 0:
        _send_error()
```

### Error handling

Each section is wrapped in `_run_section_timed()`:

- Exceptions are wrapped in `PreRunError`, `RunError`, `PostRunError`, etc.
- Timeouts raise `ProcessTimeoutError`
- When lives are exhausted, `__error__()` is called

All error classes inherit from `ProcessError`.

### Timeouts

Timeouts are implemented in `_int/timeout.py`:

- Unix: `SIGALRM` interrupts blocking code
- Windows: thread-based timeout detection (cannot interrupt blocking calls)

### Result delivery

`__result__()` (or `__error__()`) returns a value that is serialized and sent through the result queue. The parent process:

- drains the result queue
- joins the subprocess
- raises if the result is an error

## `Pool` architecture

### Execution model

`Pool` spawns one process per item (bounded by `workers`) using `_pool_worker`.  
Functions or `Skprocess` classes are serialized once, then reused for each item.

### Map modes

- `map`: returns list, ordered
- `imap`: returns iterator, ordered
- `unordered_imap`: returns iterator, completion order

### Modifiers

Map methods expose modifiers:

- `.timeout(seconds)` raises `ResultTimeoutError`
- `.background()` returns a future-like handle
- `.asynced()` returns awaitable variants
- `.star()` unpacks tuples before calling

## `Share` architecture

`Share` provides process-safe shared state via a coordinator process.

### Components

- `_Coordinator`: owns the authoritative state
- `_ObjectProxy`: proxy wrapper for each shared attribute
- `_AtomicCounterRegistry`: per-attribute pending-write counters
- `_SourceOfTruth`: serialized backing store

### Write flow

1. Proxy call or attribute set increments a write counter
2. Command is sent to the coordinator queue
3. Coordinator applies the change to the mirror object
4. State is serialized and stored
5. Counter is decremented

### Read flow

1. Proxy reads wait for counters to drop to zero
2. Value is read from the source-of-truth store

This enforces read-after-write consistency across processes.

## `autoreconnect` decorator

`@autoreconnect(**auth)` marks a `Skprocess` class for automatic `cerial.reconnect_all()` after deserialization in the child process.  
This restores DB connections and sockets before `__run__()` executes.

