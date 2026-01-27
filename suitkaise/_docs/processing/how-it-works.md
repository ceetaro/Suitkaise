# How `processing` actually works

`processing` has no dependencies outside of the standard library.

- uses Python's `multiprocessing` module for subprocess spawning
- uses `suitkaise.cerial` for serialization of complex objects between processes
- all lifecycle methods are timed using `suitkaise.sktime.Sktimer` (timing module alias)
- communication between parent and subprocess happens via `multiprocessing.Queue` and `multiprocessing.Event`
- `Share` uses a coordinator process + `multiprocessing.Manager` to keep a source of truth and synchronize proxy access

---

## Overview

`processing` uses a subprocess-based architecture.

The parent process creates the `Skprocess` instance, starts the subprocess, waits for results.

The subprocess runs the engine, executing your lifecycle methods.

## Skprocess Lifecycle

### Lifecycle Methods

The `Skprocess` class defines six lifecycle methods that users can override in their inheriting class.

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
2. `process_config.runs` limit reached (`_current_run >= process_config.runs`)
3. `process_config.join_in` time limit reached (elapsed time since start)

## Serialization

### How `cerial` is used

`processing` uses another `suitkaise` module, `cerial`, to serialize the entire `Skprocess` instance.

Serializes:
- all user-defined attributes from `__init__`
- configuration attributes
- cycle method references (captured as class attributes)

This allows complex objects (database connections, loggers, custom classes) to be passed to the subprocess without a `PicklingError`.

### Flow

1. **Before start()** — `cerial.serialize()` captures the entire Skprocess instance.
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

If a class defines `__serialize__` and `__deserialize__`, those are called alongside the Skprocess serialization:

```python
class MyProcess(Skprocess):
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

`processing` uses another `suitkaise` module, `sktime` (alias of `timing`), to time the lifecycle methods.

`sktime` is a time-tracking module that provides a simple interface for timing code.

The base `Sktimer` class is used to time the lifecycle methods, the same one that is used in the `@timethis` decorator.

### Automatic Sktimer Attachment

When a user defines a lifecycle method, `processing` automatically wraps it to provide timer access:

```python
class MyProcess(Skprocess):
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

The wrapper is created in `_setup_timed_methods()` during `Skprocess._setup()`.

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
    process.process_config.lives = lives_remaining
    continue  # retry current iteration
```

User state, run counter, and previous times are preserved.

`process_config.lives` is decremented.

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
self.process_config.timeouts.prerun = 5.0   # 5 second timeout
self.process_config.timeouts.run = 10.0     # 10 second timeout
self.process_config.timeouts.result = 2.0   # 2 second timeout
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

## Skprocess Control

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

- full Skprocess instance deserialized
- timers accumulate measurements in memory
- all state released when subprocess exits

### Large Results

For large results, consider:
- streaming to files instead of returning directly
- using `Share` to store the result in a shared memory location
- chunking results across multiple runs

---

## `Pool`

### Overview

The `Pool` class provides batch parallel processing using multiple worker subprocesses.

Like `Skprocess`, it uses `cerial` for serialization, allowing complex objects and `Skprocess` classes.

### Methods (by behavior)

`fc` = function or class of type["processing.Skprocess"]

`workers` controls the maximum number of processes that can work concurrently.
- `None` (default) = one worker per item (no cap)
- integer = cap concurrent workers to that count

#### `map(fc, items)`

- Blocking call that returns a list of results in input order
- For each item, spawns a dedicated worker process
- Each worker has its own result queue

#### `imap(fc, items)`

- Returns an iterator yielding results in input order
- Blocks on each `next()` until that specific worker finishes
- Internally spawns one worker per item (same as `map`)

#### `unordered_imap(fc, items)`

- Returns an iterator yielding results as workers complete
- Order is based on completion time (fastest first)
- Internally spawns one worker per item

### What each map does (practical view)

- `map` — full list, ordered, blocks until all items finish
- `imap` — ordered stream, blocks on each next result
- `unordered_imap` — completion stream, yields as soon as any finishes

#### `star()`

- Modifier that changes argument passing
- If the item is a tuple, it is unpacked as `fn(*item)`
- If the item is not a tuple, it is wrapped as `(item,)`
- Works with `map/imap/unordered_imap`

#### `close()` / `terminate()`

- `close()` joins all active worker processes (graceful)
- `terminate()` force-kills all active workers (no cleanup)
- Both clear the internal `_active_processes` list

### How It Works

```python
pool = Pool(workers=4)

# each item is processed in a separate subprocess
results = pool.map(fc, [1, 2, 3, 4])
```

Internally, Pool:
1. Serializes the function/class once with `cerial`
2. Serializes each item (or arg tuple for `star()`)
3. Spawns one worker process per item, up to the `workers` cap at a time
   - if `workers=None`, all items spawn at once (per-item model)
   - if `workers` is set, workers are started in batches as others finish
4. Worker deserializes, executes, and sends `{type, data}` via a result queue
5. Parent joins workers, deserializes results, and returns them in order (or completion order for `unordered_imap`)

### Result Ordering

- `map()` returns results in input order
- `imap()` yields results in input order (blocking on each next item)
- `unordered_imap()` yields as each worker completes (fastest first)

### Timeouts and Errors

- A timeout applies per worker: the parent `join()`s each worker with that timeout
- If a worker exceeds timeout, it is terminated and a `TimeoutError` is raised
- Worker errors are serialized and re-raised in the parent
- If error serialization fails, the worker sends a serialized `RuntimeError` with traceback text

### Modifiers

Each of `map/imap/unordered_imap` exposes:
- `.timeout(seconds)` — timeout per worker
- `.background()` — run in shared thread pool, returns `Future`
- `.asynced()` — run in `asyncio.to_thread`, returns coroutine

Timeout modifiers are layered:
- `map.timeout(...)` applies timeout in the parent join loop
- `imap.timeout(...)` / `unordered_imap.timeout(...)` apply timeout to each worker join

### Internal Flow (implementation detail)

`Pool` uses a simple per-item worker model:

1. `_spawn_workers()` serializes `fc` once and each item separately
2. Each worker runs `_pool_worker(serialized_fn, serialized_item, is_star, result_queue)`
3. The worker deserializes with `cerial`, executes, and puts:
   - `{type: "result", data: <serialized result>}` or
   - `{type: "error", data: <serialized exception>}`
4. Parent collects each queue in order (`map/imap`) or by completion (`unordered_imap`)

### `Skprocess` inside Pool

If the target is a `Skprocess` class:
- the worker instantiates it with the item/tuple args
- the lifecycle runs inline in the worker (no extra subprocess)
- full `process_config` behavior is respected (runs, lives, timeouts, join_in)
- lifecycle timers are created and updated as normal

### Skprocess Classes in Pool

You can use `Skprocess` subclasses in Pool:

```python
class MyProcess(Skprocess):
    def __init__(self, value):
        self.value = value
        self.process_config.runs = 3
    
    def __run__(self):
        self.value *= 2
    
    def __result__(self):
        return self.value

pool = Pool(workers=2)
results = pool.map(MyProcess, [1, 2, 3, 4])
# → [8, 16, 24, 32] (each ran 3 times, doubling each time)
```

When using `Skprocess` classes:
- full lifecycle is respected (`process_config.runs`, `process_config.lives`, `stop()`)
- each instance runs as it normally would, not just one run
- classes that do not set `process_config.runs` are expected to `stop()` themselves, `Pool` won't stop them for you
- results collected via `__result__()`

---

## `Share`

`Share` uses a coordinator process to manage shared state and proxies.

- Objects with `_shared_meta` are wrapped in proxies so method calls and property reads are synchronized.
- User class instances without `_shared_meta` are auto-wrapped via `Skclass` to generate metadata.
- Primitives and containers without metadata are stored directly in the coordinator.

The coordinator maintains a source of truth and routes reads/writes from all processes, so shared state stays consistent without manual locks in user code.

### Coordinator Process

The coordinator runs in its own process and uses:
- `multiprocessing.Manager` for the command queue and source-of-truth store
- atomic shared-memory counters (`multiprocessing.Value`) for pending/completed flags
  - keys are registered per attribute (with local lookup tables in each process)

When you assign `share.foo = obj`:
1. `Share` registers the object name and stores a serialized snapshot in `source_store`
2. If it has `_shared_meta`, a proxy is created for method/property interception
3. If not, a plain object is stored and reads fetch the whole object

### Command Format

Each queued command is a tuple:
```
(object_name, method_name, serialized_args, serialized_kwargs, written_attrs)
```

- `serialized_args/kwargs` are `cerial` bytes
- `written_attrs` is derived from `_shared_meta` (method writes)
- All command processing is serialized in the coordinator process

### Counters

`Share` uses a “pending/completed” counter per attribute:
- `pending` increments before a write is queued (atomic counter)
- `completed` increments after the write is applied (atomic counter)
- A read captures `target = completed + pending` at snapshot time
- The read waits until `completed >= target`
- This prevents read starvation and avoids waiting on new writes that arrive later


`Share` uses an **atomic counter registry** separate from the Manager dicts:

- Each counter is a `multiprocessing.Value(ctypes.c_int)`
- Counters live in shared memory and are protected by their own internal locks
- Each process keeps a **local cache** of counter handles (fast lookup)
- The registry itself (mapping key → counter handle) is stored in a Manager dict
  so counters can be created lazily and discovered by any process

Key format:

- `object_name.attr_name` → (`pending_name`, `completed_name`)


Registration:

1. When an object is assigned to `Share`, `_shared_meta` is used to collect attrs
2. The coordinator registers counters for all read/write attrs
3. Any later dynamic attr write will **auto-create** its counter on first use

Write path:

1. Proxy calls `increment_pending(key)` (atomic)
2. Command is enqueued
3. Coordinator applies the write
4. Coordinator calls `update_after_write(key)`:
   - pending = max(pending - 1, 0)
   - completed += 1

Read path:

1. Proxy determines relevant keys (read attrs)
2. Captures target = completed + pending for each key
3. Waits until completed >= target for each key
4. Reads the object from `source_store`

Why two counters:

- `pending` says "writes in flight"
- `completed` acts as a monotonically increasing commit index
- snapshotting `target = completed + pending` guarantees no starvation
  because later writes do not change the captured target

### Proxy Behavior

`_ObjectProxy` intercepts all access:
- **Method calls** queue a command and return immediately
- **Property reads** wait for pending writes, then read from source of truth
- **Attribute writes** queue a `__setattr__` command

The proxy never mutates the object directly; it always goes through the coordinator.

### `Share` Execution Flow (full chart)

```
PROCESS A (worker)                         COORDINATOR PROCESS
──────────────────────────                ──────────────────────────
share.obj.method(x)
    │
    ├─ _MethodProxy.__call__()
    │    ├─ increment_pending(key)
    │    └─ queue_command(
    │         obj_name, method_name,
    │         serialize(args/kwargs),
    │         written_attrs
    │       )
    │
    └─ return immediately
                                      ┌────────────────────────────┐
                                      │ command_queue.get(timeout) │
                                      └──────────────┬─────────────┘
                                                     │
                                                     ▼
                                             deserialize args/kwargs
                                                     │
                                                     ▼
                                       fetch object from source_store
                                                     │
                                                     ▼
                                        apply method / setattr locally
                                                     │
                                                     ▼
                                       serialize updated object state
                                                     │
                                                     ▼
                                       store back into source_store
                                                     │
                                                     ▼
                                   increment completed counters (writes)
                                                     │
                                                     ▼
                                             loop for next command


PROCESS B (reader)
──────────────────
value = share.obj.prop
    │
    ├─ _ObjectProxy._read_property()
    │    ├─ determine read_attrs from _shared_meta
    │    ├─ wait_for_read(keys)
    │    └─ coordinator.get_object(obj_name)
    │
    └─ return getattr(obj, prop)
```

### Coordinator Execution Flow

1. Dequeue next command (with a short poll timeout)
2. Deserialize args/kwargs via `cerial`
3. Fetch mirror object from `source_store` and deserialize it
4. Invoke method or setattr on mirror
5. Serialize updated object back into `source_store`
6. Increment completed counters for the written attributes
7. Loop until stop event is set

### Reads (properties and attrs)

Proxy reads are conservative:
- For properties, `_shared_meta` identifies read attributes
- For plain attrs, the proxy waits on all pending keys for the object
- After waiting, it fetches the latest object and reads the attr/property

### What is “shared”

Only the serialized state is shared. Each read returns a fresh deserialized copy.
Method calls are fire-and-forget; they queue a command and return immediately.

### Failure Behavior

- If the coordinator fails, `has_error` becomes `True`
- Proxies will still attempt reads/writes, but state will stop updating
- `Share.stop()` signals the coordinator to exit

### Lifecycle

- `Share()` auto-starts the coordinator process
- `share.start()` restarts it if you previously stopped it
- `share.stop()` / `share.exit()` shuts it down gracefully
- `share.clear()` clears all shared objects and counters

---

## `autoreconnect`

### The Problem

When a `Skprocess` is serialized, resources like database connections cannot be pickled. `cerial` replaces them with `Reconnector` placeholders containing metadata to recreate the connection.

After deserialization in the subprocess, these placeholders need to be converted back into live connections.

### How `@autoreconnect` Works

The `@autoreconnect(**kwargs)` decorator sets two class attributes:

```python
cls._auto_reconnect_enabled = True
cls._auto_reconnect_kwargs = {...}
```

During deserialization (`_deserialize_with_user`):

1. Check if `_auto_reconnect_enabled` is `True`
2. If so, call `reconnect_all(obj, **_auto_reconnect_kwargs)`
3. This walks the entire object, replacing Reconnectors with live resources

### Reconnection Flow

```
Parent Process                              Subprocess
──────────────                              ──────────
MyProcess instance
    │
    ├─ self.db = psycopg2.connect(...)
    │
    ▼
cerial.serialize()
    │
    ├─ db connection → DbReconnector
    │
    ▼
bytes ─────────────────────────────────────> cerial.deserialize()
                                                 │
                                                 ├─ DbReconnector restored
                                                 │
                                                 ▼
                                             _deserialize_with_user()
                                                 │
                                                 ├─ _auto_reconnect_enabled?
                                                 │
                                                 ▼
                                             reconnect_all(obj, **kwargs)
                                                 │
                                                 ├─ DbReconnector.reconnect(**merged)
                                                 │
                                                 ▼
                                             self.db = live connection
```

### Password Lookup

`reconnect_all()` uses type keys to find passwords:

1. Get type key from Reconnector (e.g., `"psycopg2.Connection"`)
2. Look up in kwargs dict
3. Check for attr-specific password first
4. Fall back to `"*"` default
5. Pass auth to `reconnect(auth)`

```python
# If kwargs is:
{
    "psycopg2.Connection": {
        "*": "default_pass",
        "analytics_db": "special_pass",
    }
}

# Then:
# self.db (any name) gets: reconnect("default_pass")
# self.analytics_db gets: reconnect("special_pass")
```

Connection metadata (host, port, user, database) is stored during serialization - only passwords need to be provided.

### Without Decorator

If you need dynamic credentials, call `reconnect_all()` manually in `__prerun__`:

```python
def __prerun__(self):
    from suitkaise.cerial import reconnect_all
    reconnect_all(self, **{
        "psycopg2.Connection": {
            "*": os.environ["DB_PASSWORD"],
        },
    })
```

This runs after deserialization but before `__run__`, giving you access to subprocess environment variables.