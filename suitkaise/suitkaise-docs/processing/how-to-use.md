# How to use `<suitkaise-api>processing</suitkaise-api>`

`<suitkaise-api>processing</suitkaise-api>` provides powerful subprocess execution, parallel processing, and shared memory across process boundaries.

`<suitkaise-api>Skprocess</suitkaise-api>`: Base class for easy, class based subprocess execution.
- inherit from `<suitkaise-api>Skprocess</suitkaise-api>`
- implement the lifecycle methods
- easy to make and use
- `<suitkaise-api>tell</suitkaise-api>()` and `<suitkaise-api>listen</suitkaise-api>()` for queue based communication
- serializes with `<suitkaise-api>cucumber</suitkaise-api>`
- automatic reconnection of live resources with `<suitkaise-api>autoreconnect</suitkaise-api>`
- automatic timing
- automatic retries
- automatic timeouts
- automatic looping
- simple class pattern

`<suitkaise-api>Pool</suitkaise-api>`: Parallel batch processing.
- `map`: returns a list, ordered by input
- `unordered_map`: returns an unordered list, fastest items first
- `imap`: returns an iterator, ordered by input
- `unordered_imap`: returns an iterator, unordered
- `.<suitkaise-api>star</suitkaise-api>()` modifier: unpacks tuples as function arguments
- supports `<suitkaise-api>sk</suitkaise-api>` modifiers: `.<suitkaise-api>timeout</suitkaise-api>()`, `.<suitkaise-api>background</suitkaise-api>()`, `.<suitkaise-api>asynced</suitkaise-api>()`

`<suitkaise-api>Share</suitkaise-api>`: Shared memory container that works across processes.
- best feature in the entire library
- literally just create a `<suitkaise-api>Share</suitkaise-api>` and add any objects to it, like a regular class
- pass the `<suitkaise-api>Share</suitkaise-api>` to your subprocesses
- access and update the objects normally
- everything remains in sync

`<suitkaise-api>Pipe</suitkaise-api>`: upgraded `multiprocessing.<suitkaise-api>Pipe</suitkaise-api>`
- super fast cross process communication
- uses `<suitkaise-api>cucumber</suitkaise-api>` for serialization
- ensures one pipe endpoint remains locked in the parent process
- easy to use and understand

## Importing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>processing</suitkaise-api>
```

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pipe</suitkaise-api>, <suitkaise-api>autoreconnect</suitkaise-api>, <suitkaise-api>ProcessTimers</suitkaise-api>, <suitkaise-api>ProcessError</suitkaise-api>, <suitkaise-api>PreRunError</suitkaise-api>, <suitkaise-api>RunError</suitkaise-api>, <suitkaise-api>PostRunError</suitkaise-api>, <suitkaise-api>OnFinishError</suitkaise-api>, <suitkaise-api>ResultError</suitkaise-api>, <suitkaise-api>ErrorHandlerError</suitkaise-api>, <suitkaise-api>ProcessTimeoutError</suitkaise-api>, <suitkaise-api>ResultTimeoutError</suitkaise-api>
```

---

## `<suitkaise-api>Skprocess</suitkaise-api>`

Base class for subprocess execution. Inherit from this class and implement lifecycle methods.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class MyProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self):
        self.counter = 0
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 10
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.counter += 1
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.counter

process = MyProcess()
process.<suitkaise-api>start</suitkaise-api>()
process.<suitkaise-api>wait</suitkaise-api>()
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>result</suitkaise-api>()  # 10
```

### Lifecycle Methods

Define any of these methods in your subclass. All are optional except `<suitkaise-api>__run__</suitkaise-api>()`.

`<suitkaise-api>__run__</suitkaise-api>()`: main work method
- required
- no need to write looping code

`<suitkaise-api>__prerun__</suitkaise-api>()`: setup before each iteration (run)
- optional
- use for setup that needs to happen before each run

`<suitkaise-api>__postrun__</suitkaise-api>()`: cleanup after each iteration (run)
- optional
- use for cleanup that needs to happen after every run

`<suitkaise-api>__onfinish__</suitkaise-api>()`: cleanup/teardown after the process ends
- optional
- use for cleanup that needs to happen before the process ends

`<suitkaise-api>__result__</suitkaise-api>()`: return data when the process completes
- optional
- whatever is returned here is what `process.<suitkaise-api>result</suitkaise-api>()` returns

`<suitkaise-api>__error__</suitkaise-api>()`: return data when the process fails
- optional
- allows you more flexibility when an error occurs

#### `<suitkaise-api>__prerun__</suitkaise-api>()`

Called before each `<suitkaise-api>__run__</suitkaise-api>()` iteration.

```python
def <suitkaise-api>__prerun__</suitkaise-api>(self):
    self.data = fetch_next_batch()
```

Use for:
- Fetching data for the next iteration
- Setup that needs to happen before each run
- Checking conditions before running

#### `<suitkaise-api>__run__</suitkaise-api>()`

Main work method. Called each iteration.

```python
def <suitkaise-api>__run__</suitkaise-api>(self):
    for item in self.data:
        process(item)
```

This is where your core logic goes.

#### `<suitkaise-api>__postrun__</suitkaise-api>()`

Called after each `<suitkaise-api>__run__</suitkaise-api>()` iteration completes.

```python
def <suitkaise-api>__postrun__</suitkaise-api>(self):
    self.results.append(self.batch_result)
    self.batch_result = None
```

Use for:
- Cleanup after each iteration
- Recording results
- State transitions

#### `<suitkaise-api>__onfinish__</suitkaise-api>()`

Called when the process ends (stop signal or run limit reached).

```python
def <suitkaise-api>__onfinish__</suitkaise-api>(self):
    self.cleanup_resources()
    self.save_final_state()
```

Use for:
- Final cleanup
- Saving state
- Closing connections

#### `<suitkaise-api>__result__</suitkaise-api>()`

Return data when process completes. This is what `process.<suitkaise-api>result</suitkaise-api>()` returns.

```python
def <suitkaise-api>__result__</suitkaise-api>(self):
    return {
        'count': self.counter,
        'results': self.results,
        'status': 'completed'
    }
```

NOTE: Your process will not return a result unless you define `<suitkaise-api>__result__</suitkaise-api>()`.

#### `<suitkaise-api>__error__</suitkaise-api>()`

Handle errors when all lives are exhausted. Receives the error via `self.<suitkaise-api>error</suitkaise-api>`.

```python
def <suitkaise-api>__error__</suitkaise-api>(self):
    log_error(self.<suitkaise-api>error</suitkaise-api>)
    return {'status': 'failed', '<suitkaise-api>error</suitkaise-api>': str(self.<suitkaise-api>error</suitkaise-api>)}
```

Default behavior: Returns `self.<suitkaise-api>error</suitkaise-api>`, which will be raised by `process.<suitkaise-api>result</suitkaise-api>()`.

### `<suitkaise-api>process_config</suitkaise-api>`

Configuration object available in your `__init__`. Set these to control process behavior.

#### `<suitkaise-api>runs</suitkaise-api>`

Number of run iterations before auto-stopping.

```python
def __init__(self):
    # <suitkaise-api>run</suitkaise-api> 100 iterations, then stop
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 100
```

- `int`: Run this many iterations
- `None`: Run indefinitely until `<suitkaise-api>stop</suitkaise-api>()` is called

#### `<suitkaise-api>join_in</suitkaise-api>`

Maximum total runtime in seconds before auto-stopping.

```python
def __init__(self):
    # stop after 60 seconds
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>join_in</suitkaise-api> = 60.0 
```

- `float`: Maximum seconds to run
- `None`: No time limit

#### `<suitkaise-api>lives</suitkaise-api>`

Number of times to retry after a crash before giving up.

```python
def __init__(self):
    # retry up to 2 <suitkaise-api>times</suitkaise-api> (3 total attempts)
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>lives</suitkaise-api> = 3  
```

- `1`: No retries (fail on first error)
- `n > 1`: Retry `n-1` times on error

When the process crashes:
1. Current run state is preserved
2. Process restarts from where it left off
3. `<suitkaise-api>lives</suitkaise-api>` is decremented
4. If `<suitkaise-api>lives</suitkaise-api>` reaches 0, `<suitkaise-api>__error__</suitkaise-api>()` is called

#### `<suitkaise-api>timeouts</suitkaise-api>`

Timeout settings for each lifecycle section.

```python
def __init__(self):
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>prerun</suitkaise-api> = 5.0
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>run</suitkaise-api> = 30.0
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>postrun</suitkaise-api> = 5.0
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>onfinish</suitkaise-api> = 10.0
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>result</suitkaise-api> = 5.0
    self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>error</suitkaise-api> = 5.0
```

All default to `None` (no timeout). Set a value to enable timeout for that section.

If a section times out, `<suitkaise-api>ProcessTimeoutError</suitkaise-api>` is raised. This counts against `<suitkaise-api>lives</suitkaise-api>`.

### Control Methods

These are all of the methods you use to actually run and control `<suitkaise-api>Skprocess</suitkaise-api>` made subprocesses.

#### `<suitkaise-api>start</suitkaise-api>()`

Start the process in a new subprocess.

```python
process = MyProcess()
process.<suitkaise-api>start</suitkaise-api>()
```

- Serializes the `<suitkaise-api>Skprocess</suitkaise-api>` object
- Spawns a subprocess that runs your `<suitkaise-api>Skprocess</suitkaise-api>` object
- Returns immediately (non-blocking)

#### `<suitkaise-api>stop</suitkaise-api>()`

Signal the process to stop gracefully.

```python
process.<suitkaise-api>stop</suitkaise-api>()
```

- Non-blocking (returns immediately)
- Process finishes current section
- Then runs `<suitkaise-api>__onfinish__</suitkaise-api>()` and `<suitkaise-api>__result__</suitkaise-api>()`
- Use `<suitkaise-api>wait</suitkaise-api>()` after `<suitkaise-api>stop</suitkaise-api>()` to block until finished

#### `<suitkaise-api>kill</suitkaise-api>()`

Forcefully terminate the process immediately.

```python
process.<suitkaise-api>kill</suitkaise-api>()
```

- Bypasses the lives system
- No cleanup, no `<suitkaise-api>__onfinish__</suitkaise-api>()`, no result
- Use only as a last resort

#### `<suitkaise-api>wait</suitkaise-api>()`

Wait for the process to finish.

```python
finished = process.<suitkaise-api>wait</suitkaise-api>() # blocks until done

finished = process.<suitkaise-api>wait</suitkaise-api>(timeout=10.0) # returns False if timeout
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
await process.<suitkaise-api>wait</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
```

If the process crashes and has lives remaining, `<suitkaise-api>wait</suitkaise-api>()` continues blocking during the restart.

#### `<suitkaise-api>result</suitkaise-api>()`

Get the result from the process.

Will block until the process finishes if not already done.

Returns whatever `<suitkaise-api>__result__</suitkaise-api>()` returned.

```python
data = process.<suitkaise-api>result</suitkaise-api>()  # blocks until <suitkaise-api>result</suitkaise-api> ready
```

Raises
`<suitkaise-api>ProcessError</suitkaise-api>`: If the process failed (after exhausting lives).

Modifiers:
```python
# with timeout
data = process.<suitkaise-api>result</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(10.0)()

# background - returns Future
future = process.<suitkaise-api>result</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()()
data = future.<suitkaise-api>result</suitkaise-api>()

# async
data = await process.<suitkaise-api>result</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
```

#### `<suitkaise-api>run</suitkaise-api>()`

Start, wait, and return the result in one call.

```python
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>run</suitkaise-api>()
```

Equivalent to:
```python
process.<suitkaise-api>start</suitkaise-api>()
process.<suitkaise-api>wait</suitkaise-api>()
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>result</suitkaise-api>()
```

Returns whatever `<suitkaise-api>__result__</suitkaise-api>()` returned.

Raises
`<suitkaise-api>ProcessError</suitkaise-api>`: If the process failed (after exhausting lives).

Modifiers:
```python
# with timeout
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>run</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0)()

# background - returns Future
future = process.<suitkaise-api>run</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()()
# ... do other work ...
<suitkaise-api>result</suitkaise-api> = future.<suitkaise-api>result</suitkaise-api>()

# async
<suitkaise-api>result</suitkaise-api> = await process.<suitkaise-api>run</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
```

### Queue based communication with `<suitkaise-api>tell</suitkaise-api>()` and `<suitkaise-api>listen</suitkaise-api>()`

Bidirectional communication between parent and subprocess.

#### `<suitkaise-api>tell</suitkaise-api>()`

Send data to the other side.

```python
# from parent
process.<suitkaise-api>tell</suitkaise-api>({"command": "update_config", "value": 100})

# from subprocess (in lifecycle methods)
def <suitkaise-api>__postrun__</suitkaise-api>(self):
    self.<suitkaise-api>tell</suitkaise-api>({"status": "batch_complete", "count": len(self.batch)})
```

Arguments
`data`: Any serializable data to send.
- `Any`
- required

Non-blocking - returns immediately after queuing the data.

#### `<suitkaise-api>listen</suitkaise-api>()`

Receive data from the other side.

```python
# from parent
data = process.<suitkaise-api>listen</suitkaise-api>() # blocks until data received
data = process.<suitkaise-api>listen</suitkaise-api>(timeout=5.0) # returns None if timeout

# from subprocess (in lifecycle methods)
def <suitkaise-api>__prerun__</suitkaise-api>(self):
    command = self.<suitkaise-api>listen</suitkaise-api>(timeout=1.0)
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
future = process.<suitkaise-api>listen</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(timeout=5.0)

# async
data = await process.<suitkaise-api>listen</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
```

### Timing

Every lifecycle method is automatically timed.

```python
process.<suitkaise-api>start</suitkaise-api>()
process.<suitkaise-api>wait</suitkaise-api>()

# access <suitkaise-api>timing</suitkaise-api> data
print(process.<suitkaise-api>__run__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
print(process.<suitkaise-api>__prerun__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>)
print(process.<suitkaise-api>__postrun__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95))

# aggregate timer for full iterations (<suitkaise-api>prerun</suitkaise-api> + <suitkaise-api>run</suitkaise-api> + <suitkaise-api>postrun</suitkaise-api>)
print(process.process_timer.<suitkaise-api>mean</suitkaise-api>)
```

Each timer is an `<suitkaise-api>Sktimer</suitkaise-api>` with full statistics: `mean`, `median`, `stdev`, `min`, `max`, `<suitkaise-api>percentile</suitkaise-api>()`, ...

### Properties

`current_run`: Current run iteration number (0-indexed).
- `int`
- first run is run 0

`is_alive`: Whether the subprocess is currently running.
- `bool`

`timers`: Container with all lifecycle timers.
- `<suitkaise-api>ProcessTimers</suitkaise-api> | None`

`<suitkaise-api>error</suitkaise-api>`: The error that caused the process to fail (available in `<suitkaise-api>__error__</suitkaise-api>()`).
- `BaseException | None`

---

## `<suitkaise-api>Pool</suitkaise-api>`

Process pool for parallel batch processing.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>

pool = <suitkaise-api>Pool</suitkaise-api>(workers=4)

# basic usage
results = pool.<suitkaise-api>map</suitkaise-api>(process_item, items)
```

### Constructor

Arguments
`workers`: Maximum concurrent workers.
- `int | None = None`
- `None` = number of CPUs

### `map`

Apply function to each item, return list of results.

```python
results = pool.<suitkaise-api>map</suitkaise-api>(fn, items)
```

- Blocks until all items are processed
- Results are in the same order as inputs
- Works with both functions and `<suitkaise-api>Skprocess</suitkaise-api>` classes

Arguments
`fn_or_process`: Function or `<suitkaise-api>Skprocess</suitkaise-api>` class to apply.
- `Callable | type[<suitkaise-api>Skprocess</suitkaise-api>]`
- required

`iterable`: Items to process.
- `Iterable`
- required

Returns
`list`: Results in order.

#### Modifiers

```python
# star - unpacks tuples as function arguments
results = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(fn, [(1, 2), (3, 4)])
# fn(1, 2), fn(3, 4) instead of fn((1, 2), ), fn((3, 4), )

# with timeout
results = pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0)(fn, items)

# background - returns Future
future = pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn, items)
results = future.<suitkaise-api>result</suitkaise-api>()

# async
results = await pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, items)

# combine modifiers
future = pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0).<suitkaise-api>background</suitkaise-api>()(fn, items)
results = await pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>().<suitkaise-api>timeout</suitkaise-api>(30.0)(fn, items)

# star composes with all modifiers
results = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0)(fn, args_tuples)
future = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn, args_tuples)
results = await pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, args_tuples)
```

### `unordered_map`

Apply function to each item, return list in completion order.

```python
results = pool.<suitkaise-api>unordered_map</suitkaise-api>(fn, items)
```

- Returns a list (like `map`)
- Results are in completion order, not input order (like `unordered_imap`)
- Fastest when you need all results as a list but don't care about order

Arguments and returns same as `map`, but results are in completion order.

#### Modifiers

```python
# star - unpacks tuples as function arguments
results = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_map</suitkaise-api>(fn, [(1, 2), (3, 4)])

# with timeout
results = pool.<suitkaise-api>unordered_map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0)(fn, items)

# background - returns Future
future = pool.<suitkaise-api>unordered_map</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn, items)
results = future.<suitkaise-api>result</suitkaise-api>()

# async
results = await pool.<suitkaise-api>unordered_map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, items)

# star composes with all modifiers
results = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0)(fn, args_tuples)
future = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_map</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn, args_tuples)
results = await pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, args_tuples)
```

### `imap`

Apply function to each item, return iterator of results.

```python
for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>imap</suitkaise-api>(fn, items):
    process(<suitkaise-api>result</suitkaise-api>)
```

- Results are yielded in order
- Blocks on `next()` if the next result isn't ready
- Memory efficient for large datasets

Arguments and returns same as `map`, but returns `Iterator` instead of `list`.

#### Modifiers

```python
# star - unpacks tuples as function arguments
for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>imap</suitkaise-api>(fn, [(1, 2), (3, 4)]):
    process(<suitkaise-api>result</suitkaise-api>)

# with <suitkaise-api>timeout</suitkaise-api> (per-item)
for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>imap</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(10.0)(fn, items):
    process(<suitkaise-api>result</suitkaise-api>)

# background - collects to list
future = pool.<suitkaise-api>imap</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn, items)
results = future.<suitkaise-api>result</suitkaise-api>()  # list

# async - collects to list
results = await pool.<suitkaise-api>imap</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, items)  # list

# star composes with all modifiers
for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>imap</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(10.0)(fn, args_tuples):
    process(<suitkaise-api>result</suitkaise-api>)
future = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>imap</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn, args_tuples)
results = await pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>imap</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, args_tuples)
```

### `unordered_imap`

Apply function to each item, yield results as they complete.

```python
for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>unordered_imap</suitkaise-api>(fn, items):
    process(<suitkaise-api>result</suitkaise-api>)
```

- Fastest way to get results
- Order is NOT preserved
- Results are yielded as soon as they're ready

Arguments and returns same as `imap`.

#### Modifiers

```python
# star - unpacks tuples as function arguments
for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_imap</suitkaise-api>(fn, [(1, 2), (3, 4)]):
    process(<suitkaise-api>result</suitkaise-api>)

# with timeout
for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>unordered_imap</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0)(fn, items):
    process(<suitkaise-api>result</suitkaise-api>)

# background - collects to list
future = pool.<suitkaise-api>unordered_imap</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn, items)
results = future.<suitkaise-api>result</suitkaise-api>()  # list

# async - collects to list
results = await pool.<suitkaise-api>unordered_imap</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, items)  # list

# star composes with all modifiers
for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_imap</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0)(fn, args_tuples):
    process(<suitkaise-api>result</suitkaise-api>)
future = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_imap</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn, args_tuples)
results = await pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_imap</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, args_tuples)
```

### `<suitkaise-api>star</suitkaise-api>()` Modifier

Unpack tuples as function arguments.

```python
# without star: fn receives a single tuple argument
pool.<suitkaise-api>map</suitkaise-api>(fn, [(1, 2), (3, 4)])
# fn((1, 2), ), fn((3, 4), )

# with star: fn receives unpacked arguments
pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(fn, [(1, 2), (3, 4)])
# fn(1, 2), fn(3, 4)
```

Works with all methods:
```python
pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(fn, args_tuples)
pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>imap</suitkaise-api>(fn, args_tuples)
pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_imap</suitkaise-api>(fn, args_tuples)
pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_map</suitkaise-api>(fn, args_tuples)
```

Works with other modifiers:
```python
pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(30.0)(fn, args_tuples)
await pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>imap</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(fn, args_tuples)
```

### Using `<suitkaise-api>Skprocess</suitkaise-api>` with `<suitkaise-api>Pool</suitkaise-api>`

```python
class ProcessItem(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, item):
        self.item = item
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.result_data = heavy_computation(self.item)
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.result_data

# <suitkaise-api>Pool</suitkaise-api> creates instances and <suitkaise-api>runs</suitkaise-api> them
results = pool.<suitkaise-api>map</suitkaise-api>(ProcessItem, items)
```

The pool:
1. Creates a `ProcessItem` instance for each item
2. Runs each instance in a subprocess
3. Collects and returns the results

### Context Manager

```python
with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:

    results = pool.<suitkaise-api>map</suitkaise-api>(fn, items)

# pool is closed on exit
```

### `close()` and `terminate()`

```python
pool.close()      # wait for all active processes to finish
pool.terminate()  # forcefully terminate all processes
```

---

## `<suitkaise-api>Share</suitkaise-api>`

Container for shared memory across process boundaries.

The easiest and greatest way to share data between processes.

Uses `<suitkaise-api>cucumber</suitkaise-api>` for serialization, so now you can easily share anything you want.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>

share = <suitkaise-api>Share</suitkaise-api>()
share.<suitkaise-api>timer</suitkaise-api> = <suitkaise-api>Sktimer</suitkaise-api>()
share.counter = 0
```

### Basic Usage

```python
share = <suitkaise-api>Share</suitkaise-api>()
share.counter = 0

class IncrementProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, share):
        self.share = share
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 10
    
    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        self.share.counter += 1

pool = <suitkaise-api>Pool</suitkaise-api>(workers=4)
pool.<suitkaise-api>map</suitkaise-api>(IncrementProcess, [share] * 10)

print(share.counter)  # 100 (10 processes × 10 <suitkaise-api>runs</suitkaise-api> each)
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
- `<suitkaise-api>Sktimer</suitkaise-api>`, `<suitkaise-api>Circuit</suitkaise-api>`, `<suitkaise-api>BreakingCircuit</suitkaise-api>`, ...
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
- Serialized by `<suitkaise-api>cucumber</suitkaise-api>` by exhausting remaining values
- Reconstruction returns a plain iterator over remaining values (not the original iterator type)

**Not Supported**:
- `multiprocessing.*` objects (queues, managers, events, shared_memory, connections)
- These are process-bound IPC primitives; use `<suitkaise-api>Share</suitkaise-api>` primitives instead
- `os.pipe()` file handles / pipe-backed `io.FileIO`

### Start and Stop

```python
share = <suitkaise-api>Share</suitkaise-api>()  # auto-starts

# stop sharing (frees resources)
share.<suitkaise-api>stop</suitkaise-api>()
# or
share.exit()

# start again
share.<suitkaise-api>start</suitkaise-api>()
```

While stopped, changes are queued but won't take effect until `<suitkaise-api>start</suitkaise-api>()` is called.

### Reconnect All

`<suitkaise-api>Share</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>()` reconnects all `<suitkaise-api>cucumber</suitkaise-api>` Reconnector objects currently stored in Share and returns a dict of reconnected objects by name.

```python
share = <suitkaise-api>Share</suitkaise-api>()
share.db = sqlite3.connect(":memory:")

# share.db is a Reconnector in <suitkaise-api>Share</suitkaise-api>
reconnected = share.<suitkaise-api>reconnect_all</suitkaise-api>()

# now it's a live connection again
conn = reconnected["db"]
```

### Context Manager

```python
with <suitkaise-api>Share</suitkaise-api>() as share:
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

`<suitkaise-api>start</suitkaise-api>()`: Start the coordinator.

`<suitkaise-api>stop</suitkaise-api>(timeout=5.0)`: Stop the coordinator gracefully.
- Returns `True` if stopped cleanly, `False` if timed out.

`exit(timeout=5.0)`: Alias for `<suitkaise-api>stop</suitkaise-api>()`.

`clear()`: Clear all shared objects and counters.

---

## `<suitkaise-api>Pipe</suitkaise-api>`

Fast, direct parent/child communication using `multiprocessing.<suitkaise-api>Pipe</suitkaise-api>`.

This is the fastest way to communicate between processes.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pipe</suitkaise-api>

# create a pipe pair
anchor, point = <suitkaise-api>Pipe</suitkaise-api>.pair()
```

### Creating Pipes

```python
# bidirectional (default)
anchor, point = <suitkaise-api>Pipe</suitkaise-api>.pair()

# one-way
anchor, point = <suitkaise-api>Pipe</suitkaise-api>.pair(one_way=True)
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

`send(obj)`: Serialize with `<suitkaise-api>cucumber</suitkaise-api>` and send.
- Non-blocking

`recv()`: Receive and deserialize with `<suitkaise-api>cucumber</suitkaise-api>`.
- Blocking

`close()`: Close the connection.

### Usage with Skprocess

```python
class PipeProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, pipe_point):
        self.pipe = pipe_point
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # receive command
        command = self.pipe.recv()
        
        # process it
        <suitkaise-api>result</suitkaise-api> = process_command(command)
        
        # send <suitkaise-api>result</suitkaise-api> back
        self.pipe.send(<suitkaise-api>result</suitkaise-api>)

# parent
anchor, point = <suitkaise-api>Pipe</suitkaise-api>.pair()

process = PipeProcess(point)
process.<suitkaise-api>start</suitkaise-api>()

anchor.send({"action": "compute", "value": 42})
<suitkaise-api>result</suitkaise-api> = anchor.recv()

process.<suitkaise-api>wait</suitkaise-api>()
```

### Lock/Unlock

```python
point.lock()    # prevent transfer
point.unlock()  # allow transfer

anchor.lock()   # always locked
anchor.unlock() # raises PipeEndpointError
```

---

## `<suitkaise-api>autoreconnect</suitkaise-api>` Decorator

Automatically reconnect resources (database connections, sockets, ...) when an `<suitkaise-api>Skprocess</suitkaise-api>` is deserialized in the child process.

Since `<suitkaise-api>Skprocess</suitkaise-api>` is serialized with `<suitkaise-api>cucumber</suitkaise-api>`, it gives you placeholders for live resources that can be reconnected.

Usually, you need to call `<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>()` to reconnect all resources in an object.

However, with `@<suitkaise-api>autoreconnect</suitkaise-api>`, you can decorate a `<suitkaise-api>Skprocess</suitkaise-api>` class and it will automatically reconnect all resources when the `<suitkaise-api>Skprocess</suitkaise-api>` is deserialized in the child process.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>autoreconnect</suitkaise-api>

@<suitkaise-api>autoreconnect</suitkaise-api>(
    start_threads=True,
    **{
        "psycopg2.Connection": {"*": "secret"},
        "redis.Redis": {"*": "redis_pass"},
    }
)
class MyProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, db_connection, cache_connection):
        self.db = db_connection
        self.cache = cache_connection
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
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


When `<suitkaise-api>cucumber</suitkaise-api>` deserializes the `<suitkaise-api>Skprocess</suitkaise-api>`:
1. Resources like database connections become `Reconnector` objects
2. `@<suitkaise-api>autoreconnect</suitkaise-api>` calls `<suitkaise-api>reconnect_all</suitkaise-api>()` automatically
3. Each `Reconnector` is replaced with a live connection using the provided auth


### Multiple Connections

```python
@<suitkaise-api>autoreconnect</suitkaise-api>(**{
    "psycopg2.Connection": {
        "*": "default_password",           # default for all psycopg2 connections
        "analytics_db": "analytics_secret", # specific override for analytics_db attr
    },
})
class MyProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self):
        self.main_db = psycopg2.connect(...)      # uses "*" auth
        self.analytics_db = psycopg2.connect(...) # uses "analytics_db" auth
```

---

## `<suitkaise-api>ProcessTimers</suitkaise-api>`

Container for timing lifecycle sections.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>ProcessTimers</suitkaise-api>

# usually accessed via process.timers
process.<suitkaise-api>start</suitkaise-api>()
process.<suitkaise-api>wait</suitkaise-api>()

timers = process.timers
print(timers.<suitkaise-api>run</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
print(timers.<suitkaise-api>prerun</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>)
print(timers.full_run.<suitkaise-api>percentile</suitkaise-api>(95))
```

### Properties

Each property is an `<suitkaise-api>Sktimer</suitkaise-api> | None`:

`<suitkaise-api>prerun</suitkaise-api>`: Timer for `<suitkaise-api>__prerun__</suitkaise-api>()` calls.

`<suitkaise-api>run</suitkaise-api>`: Timer for `<suitkaise-api>__run__</suitkaise-api>()` calls.

`<suitkaise-api>postrun</suitkaise-api>`: Timer for `<suitkaise-api>__postrun__</suitkaise-api>()` calls.

`<suitkaise-api>onfinish</suitkaise-api>`: Timer for `<suitkaise-api>__onfinish__</suitkaise-api>()` call.

`<suitkaise-api>result</suitkaise-api>`: Timer for `<suitkaise-api>__result__</suitkaise-api>()` call.

`<suitkaise-api>error</suitkaise-api>`: Timer for `<suitkaise-api>__error__</suitkaise-api>()` call.

`full_run`: Aggregate timer for complete iterations (prerun + run + postrun).

---

## Exceptions

All exceptions inherit from `<suitkaise-api>ProcessError</suitkaise-api>`.

### `<suitkaise-api>ProcessError</suitkaise-api>`

Base class for all Process-related errors.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>ProcessError</suitkaise-api>

try:
    <suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>result</suitkaise-api>()
except <suitkaise-api>ProcessError</suitkaise-api> as e:
    print(f"Process failed: {e}")
```

Properties:
- `current_run`: Run iteration where error occurred
- `original_error`: The underlying exception

### `<suitkaise-api>PreRunError</suitkaise-api>`

Raised when `<suitkaise-api>__prerun__</suitkaise-api>()` fails.

### `<suitkaise-api>RunError</suitkaise-api>`

Raised when `<suitkaise-api>__run__</suitkaise-api>()` fails.

### `<suitkaise-api>PostRunError</suitkaise-api>`

Raised when `<suitkaise-api>__postrun__</suitkaise-api>()` fails.

### `<suitkaise-api>OnFinishError</suitkaise-api>`

Raised when `<suitkaise-api>__onfinish__</suitkaise-api>()` fails.

### `<suitkaise-api>ResultError</suitkaise-api>`

Raised when `<suitkaise-api>__result__</suitkaise-api>()` fails.

### `<suitkaise-api>ErrorHandlerError</suitkaise-api>`

Raised when `<suitkaise-api>__error__</suitkaise-api>()` fails.

### `<suitkaise-api>ProcessTimeoutError</suitkaise-api>`

Raised when a lifecycle section times out.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>ProcessTimeoutError</suitkaise-api>

try:
    <suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>result</suitkaise-api>()
except <suitkaise-api>ProcessTimeoutError</suitkaise-api> as e:
    print(f"Timeout in {e.section} after {e.<suitkaise-api>timeout</suitkaise-api>}s on <suitkaise-api>run</suitkaise-api> {e.current_run}")
```

Properties:
- `section`: Which lifecycle method timed out
- `timeout`: The timeout value that was exceeded

### `<suitkaise-api>ResultTimeoutError</suitkaise-api>`

Raised when `<suitkaise-api>result</suitkaise-api>()`, `<suitkaise-api>wait</suitkaise-api>()`, or `<suitkaise-api>listen</suitkaise-api>()` times out via `.<suitkaise-api>timeout</suitkaise-api>()` modifier.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>ResultTimeoutError</suitkaise-api>

try:
    <suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>result</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(10.0)()
except <suitkaise-api>ResultTimeoutError</suitkaise-api> as e:
    print("Timed out waiting for <suitkaise-api>result</suitkaise-api>")
```
