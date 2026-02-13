# How to use `processing`

`processing` provides powerful subprocess execution, parallel processing, and shared memory across process boundaries.

`Skprocess`: Base class for easy, class based subprocess execution.
- inherit from `Skprocess`
- implement the lifecycle methods
- easy to make and use
- `tell()` and `listen()` for queue based communication
- serializes with `cucumber`
- automatic reconnection of live resources with `autoreconnect`
- automatic timing
- automatic retries
- automatic timeouts
- automatic looping
- simple class pattern

`Pool`: Parallel batch processing.
- `map`: returns a list, ordered by input
- `unordered_map`: returns an unordered list, fastest items first
- `imap`: returns an iterator, ordered by input
- `unordered_imap`: returns an iterator, unordered
- `.star()` modifier: unpacks tuples as function arguments
- supports `sk` modifiers: `.timeout()`, `.background()`, `.asynced()`

`Share`: Shared memory container that works across processes.
- best feature in the entire library
- literally just create a `Share` and add any objects to it, like a regular class
- pass the `Share` to your subprocesses
- access and update the objects normally
- everything remains in sync

`Pipe`: upgraded `multiprocessing.Pipe`
- super fast cross process communication
- uses `cucumber` for serialization
- ensures one pipe endpoint remains locked in the parent process
- easy to use and understand

## Importing

```python
from suitkaise import processing
```

```python
from suitkaise.processing import Skprocess, Pool, Share, Pipe, autoreconnect, ProcessTimers, ProcessError, PreRunError, RunError, PostRunError, OnFinishError, ResultError, ErrorHandlerError, ProcessTimeoutError, ResultTimeoutError
```

---

## `Skprocess`

Base class for subprocess execution. Inherit from this class and implement lifecycle methods.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):
    def __init__(self):
        self.counter = 0
        self.process_config.runs = 10
    
    def __run__(self):
        self.counter += 1
    
    def __result__(self):
        return self.counter

process = MyProcess()
process.start()
process.wait()
result = process.result()  # 10
```

### Lifecycle Methods

Define any of these methods in your subclass. All are optional except `__run__()`.

`__run__()`: main work method
- required
- no need to write looping code

`__prerun__()`: setup before each iteration (run)
- optional
- use for setup that needs to happen before each run

`__postrun__()`: cleanup after each iteration (run)
- optional
- use for cleanup that needs to happen after every run

`__onfinish__()`: cleanup/teardown after the process ends
- optional
- use for cleanup that needs to happen before the process ends

`__result__()`: return data when the process completes
- optional
- whatever is returned here is what `process.result()` returns

`__error__()`: return data when the process fails
- optional
- allows you more flexibility when an error occurs

#### `__prerun__()`

Called before each `__run__()` iteration.

```python
def __prerun__(self):
    self.data = fetch_next_batch()
```

Use for:
- Fetching data for the next iteration
- Setup that needs to happen before each run
- Checking conditions before running

#### `__run__()`

Main work method. Called each iteration.

```python
def __run__(self):
    for item in self.data:
        process(item)
```

This is where your core logic goes.

#### `__postrun__()`

Called after each `__run__()` iteration completes.

```python
def __postrun__(self):
    self.results.append(self.batch_result)
    self.batch_result = None
```

Use for:
- Cleanup after each iteration
- Recording results
- State transitions

#### `__onfinish__()`

Called when the process ends (stop signal or run limit reached).

```python
def __onfinish__(self):
    self.cleanup_resources()
    self.save_final_state()
```

Use for:
- Final cleanup
- Saving state
- Closing connections

#### `__result__()`

Return data when process completes. This is what `process.result()` returns.

```python
def __result__(self):
    return {
        'count': self.counter,
        'results': self.results,
        'status': 'completed'
    }
```

NOTE: Your process will not return a result unless you define `__result__()`.

#### `__error__()`

Handle errors when all lives are exhausted. Receives the error via `self.error`.

```python
def __error__(self):
    log_error(self.error)
    return {'status': 'failed', 'error': str(self.error)}
```

Default behavior: Returns `self.error`, which will be raised by `process.result()`.

### `process_config`

Configuration object available in your `__init__`. Set these to control process behavior.

#### `runs`

Number of run iterations before auto-stopping.

```python
def __init__(self):
    # run 100 iterations, then stop
    self.process_config.runs = 100
```

- `int`: Run this many iterations
- `None`: Run indefinitely until `stop()` is called

#### `join_in`

Maximum total runtime in seconds before auto-stopping.

```python
def __init__(self):
    # stop after 60 seconds
    self.process_config.join_in = 60.0 
```

- `float`: Maximum seconds to run
- `None`: No time limit

#### `lives`

Number of times to retry after a crash before giving up.

```python
def __init__(self):
    # retry up to 2 times (3 total attempts)
    self.process_config.lives = 3  
```

- `1`: No retries (fail on first error)
- `n > 1`: Retry `n-1` times on error

When the process crashes:
1. Current run state is preserved
2. Process restarts from where it left off
3. `lives` is decremented
4. If `lives` reaches 0, `__error__()` is called

#### `timeouts`

Timeout settings for each lifecycle section.

```python
def __init__(self):
    self.process_config.timeouts.prerun = 5.0
    self.process_config.timeouts.run = 30.0
    self.process_config.timeouts.postrun = 5.0
    self.process_config.timeouts.onfinish = 10.0
    self.process_config.timeouts.result = 5.0
    self.process_config.timeouts.error = 5.0
```

All default to `None` (no timeout). Set a value to enable timeout for that section.

If a section times out, `ProcessTimeoutError` is raised. This counts against `lives`.

### Control Methods

These are all of the methods you use to actually run and control `Skprocess` made subprocesses.

#### `start()`

Start the process in a new subprocess.

```python
process = MyProcess()
process.start()
```

- Serializes the `Skprocess` object
- Spawns a subprocess that runs your `Skprocess` object
- Returns immediately (non-blocking)

#### `stop()`

Signal the process to stop gracefully.

```python
process.stop()
```

- Non-blocking (returns immediately)
- Process finishes current section
- Then runs `__onfinish__()` and `__result__()`
- Use `wait()` after `stop()` to block until finished

#### `kill()`

Forcefully terminate the process immediately.

```python
process.kill()
```

- Bypasses the lives system
- No cleanup, no `__onfinish__()`, no result
- Use only as a last resort

#### `wait()`

Wait for the process to finish.

```python
finished = process.wait() # blocks until done

finished = process.wait(timeout=10.0) # returns False if timeout
```

Arguments
`timeout`: Maximum seconds to wait.
- `float | None = None`
- `None` = wait forever

Returns
`bool`: True if process finished, False if timeout reached.

Modifiers:
```python
# async
await process.wait.asynced()()
```

If the process crashes and has lives remaining, `wait()` continues blocking during the restart.

#### `result()`

Get the result from the process.

Will block until the process finishes if not already done.

Returns whatever `__result__()` returned.

```python
data = process.result()  # blocks until result ready
```

Raises
`ProcessError`: If the process failed (after exhausting lives).

Modifiers:
```python
# with timeout
data = process.result.timeout(10.0)()

# background - returns Future
future = process.result.background()()
data = future.result()

# async
data = await process.result.asynced()()
```

#### `run()`

Start, wait, and return the result in one call.

```python
result = process.run()
```

Equivalent to:
```python
process.start()
process.wait()
result = process.result()
```

Returns whatever `__result__()` returned.

Raises
`ProcessError`: If the process failed (after exhausting lives).

Modifiers:
```python
# with timeout
result = process.run.timeout(30.0)()

# background - returns Future
future = process.run.background()()
# ... do other work ...
result = future.result()

# async
result = await process.run.asynced()()
```

### Queue based communication with `tell()` and `listen()`

Bidirectional communication between parent and subprocess.

#### `tell()`

Send data to the other side.

```python
# from parent
process.tell({"command": "update_config", "value": 100})

# from subprocess (in lifecycle methods)
def __postrun__(self):
    self.tell({"status": "batch_complete", "count": len(self.batch)})
```

Arguments
`data`: Any serializable data to send.
- `Any`
- required

Non-blocking - returns immediately after queuing the data.

#### `listen()`

Receive data from the other side.

```python
# from parent
data = process.listen() # blocks until data received
data = process.listen(timeout=5.0) # returns None if timeout

# from subprocess (in lifecycle methods)
def __prerun__(self):
    command = self.listen(timeout=1.0)
    if command:
        self.handle_command(command)
```

Arguments
`timeout`: Maximum seconds to wait.
- `float | None = None`
- `None` = wait forever

Returns
`Any | None`: Data sent by the other side, or `None` if timeout.

Modifiers:
```python
# background
future = process.listen.background()(timeout=5.0)

# async
data = await process.listen.asynced()()
```

### Timing

Every lifecycle method is automatically timed.

```python
process.start()
process.wait()

# access timing data
print(process.__run__.timer.mean)
print(process.__prerun__.timer.total_time)
print(process.__postrun__.timer.percentile(95))

# aggregate timer for full iterations (prerun + run + postrun)
print(process.process_timer.mean)
```

Each timer is an `Sktimer` with full statistics: `mean`, `median`, `stdev`, `min`, `max`, `percentile()`, ...

### Properties

`current_run`: Current run iteration number (0-indexed).
- `int`
- first run is run 0

`is_alive`: Whether the subprocess is currently running.
- `bool`

`timers`: Container with all lifecycle timers.
- `ProcessTimers | None`

`error`: The error that caused the process to fail (available in `__error__()`).
- `BaseException | None`

---

## `Pool`

Process pool for parallel batch processing.

```python
from suitkaise.processing import Pool

pool = Pool(workers=4)

# basic usage
results = pool.map(process_item, items)
```

### Constructor

Arguments
`workers`: Maximum concurrent workers.
- `int | None = None`
- `None` = number of CPUs

### `map`

Apply function to each item, return list of results.

```python
results = pool.map(fn, items)
```

- Blocks until all items are processed
- Results are in the same order as inputs
- Works with both functions and `Skprocess` classes

Arguments
`fn_or_process`: Function or `Skprocess` class to apply.
- `Callable | type[Skprocess]`
- required

`iterable`: Items to process.
- `Iterable`
- required

Returns
`list`: Results in order.

#### Modifiers

```python
# star - unpacks tuples as function arguments
results = pool.star().map(fn, [(1, 2), (3, 4)])
# fn(1, 2), fn(3, 4) instead of fn((1, 2), ), fn((3, 4), )

# with timeout
results = pool.map.timeout(30.0)(fn, items)

# background - returns Future
future = pool.map.background()(fn, items)
results = future.result()

# async
results = await pool.map.asynced()(fn, items)

# combine modifiers
future = pool.map.timeout(30.0).background()(fn, items)
results = await pool.map.asynced().timeout(30.0)(fn, items)

# star composes with all modifiers
results = pool.star().map.timeout(30.0)(fn, args_tuples)
future = pool.star().map.background()(fn, args_tuples)
results = await pool.star().map.asynced()(fn, args_tuples)
```

### `unordered_map`

Apply function to each item, return list in completion order.

```python
results = pool.unordered_map(fn, items)
```

- Returns a list (like `map`)
- Results are in completion order, not input order (like `unordered_imap`)
- Fastest when you need all results as a list but don't care about order

Arguments and returns same as `map`, but results are in completion order.

#### Modifiers

```python
# star - unpacks tuples as function arguments
results = pool.star().unordered_map(fn, [(1, 2), (3, 4)])

# with timeout
results = pool.unordered_map.timeout(30.0)(fn, items)

# background - returns Future
future = pool.unordered_map.background()(fn, items)
results = future.result()

# async
results = await pool.unordered_map.asynced()(fn, items)

# star composes with all modifiers
results = pool.star().unordered_map.timeout(30.0)(fn, args_tuples)
future = pool.star().unordered_map.background()(fn, args_tuples)
results = await pool.star().unordered_map.asynced()(fn, args_tuples)
```

### `imap`

Apply function to each item, return iterator of results.

```python
for result in pool.imap(fn, items):
    process(result)
```

- Results are yielded in order
- Blocks on `next()` if the next result isn't ready
- Memory efficient for large datasets

Arguments and returns same as `map`, but returns `Iterator` instead of `list`.

#### Modifiers

```python
# star - unpacks tuples as function arguments
for result in pool.star().imap(fn, [(1, 2), (3, 4)]):
    process(result)

# with timeout (per-item)
for result in pool.imap.timeout(10.0)(fn, items):
    process(result)

# background - collects to list
future = pool.imap.background()(fn, items)
results = future.result()  # list

# async - collects to list
results = await pool.imap.asynced()(fn, items)  # list

# star composes with all modifiers
for result in pool.star().imap.timeout(10.0)(fn, args_tuples):
    process(result)
future = pool.star().imap.background()(fn, args_tuples)
results = await pool.star().imap.asynced()(fn, args_tuples)
```

### `unordered_imap`

Apply function to each item, yield results as they complete.

```python
for result in pool.unordered_imap(fn, items):
    process(result)
```

- Fastest way to get results
- Order is NOT preserved
- Results are yielded as soon as they're ready

Arguments and returns same as `imap`.

#### Modifiers

```python
# star - unpacks tuples as function arguments
for result in pool.star().unordered_imap(fn, [(1, 2), (3, 4)]):
    process(result)

# with timeout
for result in pool.unordered_imap.timeout(30.0)(fn, items):
    process(result)

# background - collects to list
future = pool.unordered_imap.background()(fn, items)
results = future.result()  # list

# async - collects to list
results = await pool.unordered_imap.asynced()(fn, items)  # list

# star composes with all modifiers
for result in pool.star().unordered_imap.timeout(30.0)(fn, args_tuples):
    process(result)
future = pool.star().unordered_imap.background()(fn, args_tuples)
results = await pool.star().unordered_imap.asynced()(fn, args_tuples)
```

### `star()` Modifier

Unpack tuples as function arguments.

```python
# without star: fn receives a single tuple argument
pool.map(fn, [(1, 2), (3, 4)])
# fn((1, 2), ), fn((3, 4), )

# with star: fn receives unpacked arguments
pool.star().map(fn, [(1, 2), (3, 4)])
# fn(1, 2), fn(3, 4)
```

Works with all methods:
```python
pool.star().map(fn, args_tuples)
pool.star().imap(fn, args_tuples)
pool.star().unordered_imap(fn, args_tuples)
pool.star().unordered_map(fn, args_tuples)
```

Works with other modifiers:
```python
pool.star().map.timeout(30.0)(fn, args_tuples)
await pool.star().imap.asynced()(fn, args_tuples)
```

### Using `Skprocess` with `Pool`

```python
class ProcessItem(Skprocess):
    def __init__(self, item):
        self.item = item
        self.process_config.runs = 1
    
    def __run__(self):
        self.result_data = heavy_computation(self.item)
    
    def __result__(self):
        return self.result_data

# Pool creates instances and runs them
results = pool.map(ProcessItem, items)
```

The pool:
1. Creates a `ProcessItem` instance for each item
2. Runs each instance in a subprocess
3. Collects and returns the results

### Context Manager

```python
with Pool(workers=4) as pool:

    results = pool.map(fn, items)

# pool is closed on exit
```

### `close()` and `terminate()`

```python
pool.close()      # wait for all active processes to finish
pool.terminate()  # forcefully terminate all processes
```

---

## `Share`

Container for shared memory across process boundaries.

The easiest and greatest way to share data between processes.

Uses `cucumber` for serialization, so now you can easily share anything you want.

```python
from suitkaise.processing import Share
from suitkaise.timing import Sktimer

share = Share()
share.timer = Sktimer()
share.counter = 0
```

### Basic Usage

```python
share = Share()
share.counter = 0

class IncrementProcess(Skprocess):
    def __init__(self, share):
        self.share = share
        self.process_config.runs = 10
    
    def __postrun__(self):
        self.share.counter += 1

pool = Pool(workers=4)
pool.map(IncrementProcess, [share] * 10)

print(share.counter)  # 100 (10 processes × 10 runs each)
```

### How It Works

1. Assign objects as Share attributes
2. Pass Share to processes
3. Access/update attributes normally
4. Share coordinates reads and writes across processes

Share uses a coordinator-proxy system:
- **Coordinator**: Background process that handles all writes
- **Proxy**: Intercepts attribute access and queues commands
- **Source of Truth**: Serialized state in shared memory

### Supported Objects

**With `_shared_meta`** (suitkaise objects):
- `Sktimer`, `Circuit`, `BreakingCircuit`, ...
- Full method and property tracking
- Efficient barrier waits

**User classes**:
- Auto-wrapped with `Skclass` to generate `_shared_meta`
- Works automatically

**Primitives**:
- `int`, `str`, `float`, `bool`, `list`, `dict`, ...
- Stored directly in source of truth
- No proxy needed

**Iterators** (`enumerate`, `zip`, `map`, ...):
- Serialized by `cucumber` by exhausting remaining values
- Reconstruction returns a plain iterator over remaining values (not the original iterator type)

**Not Supported**:
- `multiprocessing.*` objects (queues, managers, events, shared_memory, connections)
- These are process-bound IPC primitives; use `Share` primitives instead
- `os.pipe()` file handles / pipe-backed `io.FileIO`

### Start and Stop

```python
share = Share()  # auto-starts

# stop sharing (frees resources)
share.stop()
# or
share.exit()

# start again
share.start()
```

While stopped, changes are queued but won't take effect until `start()` is called.

### Reconnect All

`Share.reconnect_all()` reconnects all `cucumber` Reconnector objects currently stored in Share and returns a dict of reconnected objects by name.

```python
share = Share()
share.db = sqlite3.connect(":memory:")

# share.db is a Reconnector in Share
reconnected = share.reconnect_all()

# now it's a live connection again
conn = reconnected["db"]
```

### Context Manager

```python
with Share() as share:
    share.counter = 0
    # ... use share ...
# automatically stopped on exit
```

### Properties

`is_running`: Whether the coordinator is running.
- `bool`

`has_error`: Whether the coordinator encountered an error.
- `bool`

### Methods

`start()`: Start the coordinator.

`stop(timeout=5.0)`: Stop the coordinator gracefully.
- Returns `True` if stopped cleanly, `False` if timed out.

`exit(timeout=5.0)`: Alias for `stop()`.

`clear()`: Clear all shared objects and counters.

---

## `Pipe`

Fast, direct parent/child communication using `multiprocessing.Pipe`.

This is the fastest way to communicate between processes.

```python
from suitkaise.processing import Pipe

# create a pipe pair
anchor, point = Pipe.pair()
```

### Creating Pipes

```python
# bidirectional (default)
anchor, point = Pipe.pair()

# one-way
anchor, point = Pipe.pair(one_way=True)
```

For one-way pipes, the anchor is the send-only end (parent), and the point
is the receive-only end (child).

### Anchor vs Point

**Anchor**:
- Stays in the parent process
- Always locked (cannot be transferred)
- Use for the "stable" end of the pipe

**Point**:
- Can be transferred to a subprocess
- Unlocked by default
- Use for the "mobile" end

### Sending and Receiving

```python
# from anchor (parent)
anchor.send({"data": [1, 2, 3]})
response = anchor.recv()

# from point (subprocess)
data = point.recv()
point.send({"status": "received"})
```

`send(obj)`: Serialize with `cucumber` and send.
- Non-blocking

`recv()`: Receive and deserialize with `cucumber`.
- Blocking

`close()`: Close the connection.

### Usage with Skprocess

```python
class PipeProcess(Skprocess):
    def __init__(self, pipe_point):
        self.pipe = pipe_point
        self.process_config.runs = 1
    
    def __run__(self):
        # receive command
        command = self.pipe.recv()
        
        # process it
        result = process_command(command)
        
        # send result back
        self.pipe.send(result)

# parent
anchor, point = Pipe.pair()

process = PipeProcess(point)
process.start()

anchor.send({"action": "compute", "value": 42})
result = anchor.recv()

process.wait()
```

### Lock/Unlock

```python
point.lock()    # prevent transfer
point.unlock()  # allow transfer

anchor.lock()   # always locked
anchor.unlock() # raises PipeEndpointError
```

---

## `autoreconnect` Decorator

Automatically reconnect resources (database connections, sockets, ...) when an `Skprocess` is deserialized in the child process.

Since `Skprocess` is serialized with `cucumber`, it gives you placeholders for live resources that can be reconnected.

Usually, you need to call `cucumber.reconnect_all()` to reconnect all resources in an object.

However, with `@autoreconnect`, you can decorate a `Skprocess` class and it will automatically reconnect all resources when the `Skprocess` is deserialized in the child process.

```python
from suitkaise.processing import Skprocess, autoreconnect

@autoreconnect(
    start_threads=True,
    **{
        "psycopg2.Connection": {"*": "secret"},
        "redis.Redis": {"*": "redis_pass"},
    }
)
class MyProcess(Skprocess):
    def __init__(self, db_connection, cache_connection):
        self.db = db_connection
        self.cache = cache_connection
    
    def __run__(self):
        # db and cache are automatically reconnected
        self.db.execute(...)
        self.cache.get(...)
```

Arguments:
`start_threads`: If `True`, auto-start any deserialized threads.
- `bool = False`
- keyword only

`**auth`: Reconnection parameters keyed by type, then by attribute name.
- Use `"*"` as the attr key for defaults that apply to all instances


When `cucumber` deserializes the `Skprocess`:
1. Resources like database connections become `Reconnector` objects
2. `@autoreconnect` calls `reconnect_all()` automatically
3. Each `Reconnector` is replaced with a live connection using the provided auth


### Multiple Connections

```python
@autoreconnect(**{
    "psycopg2.Connection": {
        "*": "default_password",           # default for all psycopg2 connections
        "analytics_db": "analytics_secret", # specific override for analytics_db attr
    },
})
class MyProcess(Skprocess):
    def __init__(self):
        self.main_db = psycopg2.connect(...)      # uses "*" auth
        self.analytics_db = psycopg2.connect(...) # uses "analytics_db" auth
```

---

## `ProcessTimers`

Container for timing lifecycle sections.

```python
from suitkaise.processing import ProcessTimers

# usually accessed via process.timers
process.start()
process.wait()

timers = process.timers
print(timers.run.mean)
print(timers.prerun.total_time)
print(timers.full_run.percentile(95))
```

### Properties

Each property is an `Sktimer | None`:

`prerun`: Timer for `__prerun__()` calls.

`run`: Timer for `__run__()` calls.

`postrun`: Timer for `__postrun__()` calls.

`onfinish`: Timer for `__onfinish__()` call.

`result`: Timer for `__result__()` call.

`error`: Timer for `__error__()` call.

`full_run`: Aggregate timer for complete iterations (prerun + run + postrun).

---

## Exceptions

All exceptions inherit from `ProcessError`.

### `ProcessError`

Base class for all Process-related errors.

```python
from suitkaise.processing import ProcessError

try:
    result = process.result()
except ProcessError as e:
    print(f"Process failed: {e}")
```

Properties:
- `current_run`: Run iteration where error occurred
- `original_error`: The underlying exception

### `PreRunError`

Raised when `__prerun__()` fails.

### `RunError`

Raised when `__run__()` fails.

### `PostRunError`

Raised when `__postrun__()` fails.

### `OnFinishError`

Raised when `__onfinish__()` fails.

### `ResultError`

Raised when `__result__()` fails.

### `ErrorHandlerError`

Raised when `__error__()` fails.

### `ProcessTimeoutError`

Raised when a lifecycle section times out.

```python
from suitkaise.processing import ProcessTimeoutError

try:
    result = process.result()
except ProcessTimeoutError as e:
    print(f"Timeout in {e.section} after {e.timeout}s on run {e.current_run}")
```

Properties:
- `section`: Which lifecycle method timed out
- `timeout`: The timeout value that was exceeded

### `ResultTimeoutError`

Raised when `result()`, `wait()`, or `listen()` times out via `.timeout()` modifier.

```python
from suitkaise.processing import ResultTimeoutError

try:
    result = process.result.timeout(10.0)()
except ResultTimeoutError as e:
    print("Timed out waiting for result")
```
