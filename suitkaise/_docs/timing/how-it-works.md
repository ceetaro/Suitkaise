# How `timing` actually works

`timing` has no dependencies outside of the standard library.

- uses Unix timestamp (seconds since January 1, 1970)

- only calculates times using floats, no datetime objects are used


### `time()`

Calls Python's `time.time()` function, and returns the current time as a `float`.

- uses real world time, not performance counter time

---

### `sleep()`

`sleep()` is an enhanced version of Python's `time.sleep()` function.

It pauses the current thread for a given number of seconds, just like `time.sleep()`, and then returns the current time.

Arguments
- `seconds` - Number of seconds to sleep (can be fractional)

Returns
- current time after sleeping

```python
from suitkaise import timing

# 2 ways to use `sleep()`

start_time = timing.time()
end_time = timing.sleep(2) # sleeps and returns the current time

# or ...

start_time = timing.time()
timing.sleep(2) # just sleeps, doesn't return
end_time = timing.time()
```

1. calls Python's `time.sleep()` function with the given number of seconds
2. after sleeping, calls `time()` to get the current time.
3. returns the current time after sleeping as a `float`

### `sleep.asynced()`

`sleep()` supports `.asynced()` for async code.

```python
end_time = await timing.sleep.asynced()(2)
```

The async version uses `asyncio.sleep()` internally instead of `time.sleep()`, making it compatible with async/await patterns.

---

### `elapsed()`

Calculates how much time has passed between two times. Order doesn't matter - always returns a positive `float` time.

Arguments
- `time1` - First time
- `time2` - Second time (defaults to current time if `None`)

Returns
- positive elapsed time (in seconds) as a `float`

```python
from suitkaise import timing

# 2 ways to use `elapsed()`

start_time = timing.time()
end_time = timing.sleep(2)

elapsed = timing.elapsed(start_time, end_time)

# or ...

start_time = timing.time()
timing.sleep(2)
elapsed = timing.elapsed(start_time)
```

1. If `time2` is `None`, `elapsed()` uses the current time as the end time (calls `timing.time()`)
2. Calculates absolute difference using `math.fabs(time2 - time1)`
   - `math.fabs()` is used instead of `abs()` for best precision with `float` numbers
3. Returns the positive difference in seconds as a `float`

`fabs()` is a built-in function in the `math` module that returns the absolute value of a number, and is more precise than `abs()` for floating point numbers.

---

## `Sktimer` Class

`Sktimer` is an advanced timer that can be used to time code execution, complete with statistics and pause/resume functionality.

It is also the base for the context manager `TimeThis`, the timing decorator `@timethis`, and `processing.Skprocess` timers.

You can optionally set a rolling window size to keep only the last N measurements.

```python
from suitkaise import timing

t = timing.Sktimer()
t_rolling = timing.Sktimer(max_times=100)
```

1. Creates a `Sktimer` instance
2. stores the following attributes:
   - `original_start_time` - set to `None` (will be set on first `start()`)
   - `times` - empty list to store all recorded measurements
   - `_paused_durations` - empty list to track pause time for each measurement
   - `_lock` - creates a `threading.RLock()` for thread safety
   - `_sessions` - empty dictionary to track timing sessions per thread (keyed by thread ID)
   - `_max_times` - rolling window size (None means keep all measurements)
Each timing operation is tracked separately. If you start timing from multiple places at once (like in parallel code), they won't interfere with each other — each gets its own independent tracking.

### Statistics properties and methods

All statistics are accessed directly on the timer as properties and methods.

```python
timer = timing.Sktimer()
# ... record some timings ...

# access statistics directly on the timer
print(timer.mean)
print(timer.stdev)
print(timer.percentile(95))
print(timer.num_times)
```

All statistics are live - they always reflect the current state of the timer. All property accesses are thread-safe.

### `Sktimer.start()`

Starts timing a new measurement.

Arguments
- none

Returns
- time (in seconds) when the measurement started, as a `float`

If called while timing is already in progress, issues a `UserWarning` (it creates a nested timing frame).

1. Checks if there's already an active timing frame for this thread
   - if yes, issues a `UserWarning`

2. Gets or creates a `TimerSession` for the current thread by calling `_get_or_create_session()`

   - uses `threading.get_ident()` to get current thread ID

   - looks up session in `_sessions` dictionary

   - if not found, creates new `TimerSession` and stores it

3. Calls `session.start()` which:
    - acquires session lock

    - creates a new "frame" (measurement context) with:
        - `start_time` - current time from `perf_counter()`
        - `paused` - `False`
        - `pause_started_at` - `None`
        - `total_paused` - `0.0`

    - pushes frame onto the session's stack (supports nested timings)

    - releases session lock

4. If this is the first start ever, sets `original_start_time` to the start timestamp

5. Returns the start timestamp

*What is `perf_counter()` and why is it used?*

Python has two main ways to get the current time:

- `time.time()` — gives you the real-world clock time (like "3:45 PM"). But if your computer's clock gets adjusted (daylight saving, syncing with the internet, etc.), this number can jump forward or backward unexpectedly.

- `time.perf_counter()` — gives you a "stopwatch" time that only counts upward. It doesn't know what time of day it is, but it's extremely precise and never gets adjusted.

For measuring how long code takes to run, `perf_counter()` is the better choice because you want consistent, accurate measurements — not times that might suddenly shift because your computer synced its clock.

*What is a frame and a stack?*

Think of a stack like a stack of plates. You can only add plates to the top, and you can only remove plates from the top.

A **frame** is one "plate" — it represents a single timing measurement that's currently in progress.

A **stack** of frames lets you nest timings inside each other:

```python
timer.start()          # frame 1 added to stack
  # do some work
  timer.start()        # frame 2 added on top (warning issued)
    # do inner work
  timer.stop()         # frame 2 removed, returns inner time
  # do more work
timer.stop()           # frame 1 removed, returns total time
```

Each `start()` pushes a new frame onto the stack. Each `stop()` pops the top frame off and calculates how long that specific measurement took. This lets you measure the total time of something while also measuring individual pieces inside it.

### `Sktimer.stop()`

Stops timing the current measurement and returns the elapsed time.

Arguments
- none

Returns
- elapsed time (in seconds) as a `float`

1. Gets the current thread's session

2. Calls `session.stop()` which:
    - acquires session lock

    - gets the top frame from the stack

    - calculates elapsed time:
        - gets current time from `perf_counter()`
        - if currently paused, adds the current pause duration
        - formula: `(end_time - start_time) - (total_paused + current_pause_duration)`
     
    - calculates total pause duration
    
    - pops the frame from the stack
    
    - returns tuple of `(elapsed_time, total_paused)` to the caller (`Sktimer.stop()`)

    - releases session lock

3. Acquires the `Sktimer` manager lock
4. Appends elapsed time to `times` list
5. Appends pause duration to `_paused_durations` list
6. Releases the lock
7. Returns just the elapsed time (unwraps the tuple)

The elapsed time excludes any paused periods, giving you only the total time the timer was running.

### `Sktimer.discard()`

Stops timing but does NOT record the measurement.

Use this when you want to abandon the current timing session without polluting your statistics (e.g., an error occurred, or this was a warm-up run).

Arguments
- none

Returns
- elapsed time that was discarded (for reference) as a `float`

1. Gets the current thread's session

2. Calls `session.stop()` which works the same as in `Sktimer.stop()`

3. Does NOT append to `times` or `_paused_durations` lists

4. Returns the elapsed time (for reference, even though it wasn't recorded)

```python
timer.start()
try:
    result = risky_operation()
    timer.stop()  # record successful timing
except Exception:
    timer.discard()  # stop but don't record failed timing
```

### `Sktimer.lap()`

Records a lap time without stopping the timer.

Arguments
- none

Returns
- elapsed time (in seconds) as a `float`

1. Gets the current thread's session

2. Calls `session.lap()` which:
    - acquires session lock

    - gets the top frame from the stack

    - calculates elapsed time just like `session.stop()`
    
    - calculates total pause duration

    - **Restarts the frame** by:
        - setting `start_time` to current time
        - resetting `total_paused` to `0.0`
        - setting `paused` to `False`
        - setting `pause_started_at` to `None`
    
    - returns tuple of `(elapsed_time, total_paused)` to the caller (`Sktimer.lap()`)

    - releases session lock
    
3. Acquires the `Sktimer` manager lock
4. Appends elapsed time to `times` list
5. Appends pause duration to `_paused_durations` list
6. Releases the lock
7. Returns just the elapsed time (unwraps the tuple)

The key difference from `stop()` is the frame stays on the stack and restarts, so timing continues. It's as if you called `Sktimer.start()` the instant after the previous `Sktimer.stop()` call.

### `Sktimer.pause()`

Pauses the current timing measurement.

Arguments
- none

Returns
- none

1. Gets the current thread's session

2. Calls `session.pause()` which:
    - acquires session lock

    - gets the top frame from the stack

    - checks if already paused:
        - if yes, issues a `UserWarning` and returns
        - if no, sets `paused` to `True` and `pause_started_at` to current time

    - releases session lock


The pause time is tracked but not included in the final elapsed time calculation.

### `Sktimer.resume()`

Resumes a paused timing measurement.

Arguments
- none

Returns
- none

1. Gets the current thread's session

2. Calls `session.resume()` which:
    - acquires session lock

    - gets the top frame from the stack

    - checks if not paused:
        - if not paused, issues a `UserWarning` and returns

    - calculates pause duration: `current_time - pause_started_at`
    - adds pause duration to `total_paused`
    - sets `paused` to `False`
    - sets `pause_started_at` to `None`

    - releases session lock

Each pause/resume cycle accumulates in `total_paused`, which is subtracted from the final elapsed time.

### `Sktimer.add_time()`

Manually adds a pre-measured time to the statistics (a `float`).

Arguments
- `elapsed_time` - time to add to statistics (in seconds) as a `float`

Returns
- none

1. Acquires the `Sktimer` manager lock
2. Appends `elapsed_time` to `times` list
3. Appends `0.0` to `_paused_durations` list
4. Releases the lock
5. Returns None

### `Sktimer` statistics properties

All statistics are accessed directly on the timer and work by acquiring the lock and calculating from the `times` list:

**`num_times`**: Returns `len(self.times)`

**`original_start_time`**: Returns the stored timestamp from the first `start()` call

**`most_recent`**: Returns `times[-1]` (last element) or `None` if empty

**`most_recent_index`**: Returns `len(times) - 1` or `None` if empty

**`result`**: Alias for `most_recent`

**`total_time`**: Returns `sum(times)` or `None` if empty

**`total_time_paused`**: Returns `sum(_paused_durations)` or `None` if empty

**`mean`**: Uses `statistics.mean(times)` or `None` if empty

**`median`**: Uses `statistics.median(times)` or `None` if empty

**`min` / `fastest_time`**: Returns `min(times)` or `None` if empty

**`max` / `slowest_time`**: Returns `max(times)` or `None` if empty

**`fastest_index`**: Returns the index of the fastest time

**`slowest_index`**: Returns the index of the slowest time

**`stdev`**: Uses `statistics.stdev(times)`, requires at least 2 measurements, returns `None` otherwise

**`variance`**: Uses `statistics.variance(times)`, requires at least 2 measurements, returns `None` otherwise

All property accesses acquire the lock to ensure thread-safe reads.

### `Sktimer` statistics methods

#### `timer.get_time()`

Gets and returns a specific timing measurement by index.

Arguments
- `index` - 0-based index of measurement

Returns
- timing measurement (in seconds) as a `float` or `None` if index is out of range

1. Acquires the `Sktimer` manager lock
2. Checks if `0 <= index < len(times)`
3. If valid, returns `times[index]`
4. If invalid, returns `None`
5. Releases the lock

#### `timer.percentile()`

Calculates a percentile of all measurements.

Arguments
- `percent` - percentile to calculate (between 0 and 100)

Returns
- percentile value (in seconds) as a `float` or `None` if no measurements

1. Acquires the `Sktimer` manager lock
2. Checks if `times` is empty - returns `None` if so
3. Validates `percent` is between 0 and 100 - raises `ValueError` if not
4. Sorts the times list
5. Calculates index: `(percent / 100) * (len(sorted_times) - 1)`
6. If index is a whole number:
   - returns the value at that exact index
7. If index is fractional:
   - gets values at floor and ceiling indices
   - performs linear interpolation: `value = lower * (1 - weight) + upper * weight`
   - where `weight` is the fractional part of the index
8. Releases the lock
9. Returns the percentile value

Linear interpolation provides smooth percentile values between data points.

### `Sktimer.get_statistics()` / `Sktimer.get_stats()`

Creates a frozen snapshot of all statistics.

Arguments
- none

Returns
- a `TimerStats` object or `None` if no measurements have been recorded

1. Acquires the `Sktimer` manager lock

2. Returns `None` if no measurements have been recorded

3. Creates a new `TimerStats` object with:
    - copy of the `times` list
    - the `original_start_time`
    - copy of the `_paused_durations` list

4. Releases the lock

5. Returns the `TimerStats` object

The `TimerStats` object calculates and stores all statistics at creation time.

Once created, the `TimerStats` object is a frozen snapshot. You can access all the same properties and methods (like `percentile()`) without acquiring locks, making it fast for repeated access.

`get_stats()` is an alias for `get_statistics()`.

### `Sktimer.reset()`

Clears all timing data.

Arguments
- none

Returns
- none

1. Acquires the `Sktimer` manager lock
2. Clears the `times` list
3. Sets `original_start_time` to `None`
4. Clears the `_sessions` dictionary (removes all thread sessions)
5. Clears the `_paused_durations` list
6. Releases the lock

This completely resets the timer as if it was just created.

---

## `TimerStats` class

A frozen snapshot of timer statistics returned by `Sktimer.get_statistics()`.

Unlike the live statistics on `Sktimer`, `TimerStats` is immutable and won't change even if the timer continues recording.

All statistics are pre-computed at creation time:

- `times` - List of all recorded timing measurements (copy)
- `num_times` - Number of timing measurements
- `original_start_time` - When the first measurement started
- `most_recent` - Most recent timing
- `most_recent_index` - Index of most recent timing
- `total_time` - Sum of all times
- `total_time_paused` - Total time spent paused
- `mean` - Average of all times
- `median` - Median of all times
- `min` / `max` - Fastest / slowest times
- `fastest_time` / `slowest_time` - Aliases for min/max
- `fastest_index` / `slowest_index` - Indices of fastest/slowest
- `stdev` - Standard deviation
- `variance` - Variance

Methods:
- `percentile(percent)` - Calculate any percentile (0-100)
- `get_time(index)` - Get specific measurement by index

---

## `TimeThis` context manager

A context manager that automatically starts and stops a timer when entering and exiting a code block.

Initialize with:
- `timer` - an optional `Sktimer` instance to use
- `threshold` - minimum elapsed time to record (default 0.0)

If `timer` is provided, the context manager will use the provided `Sktimer` instance.

Otherwise, it will create a new `Sktimer` instance, which will only be used for this single timing operation.

The context manager returns the `Sktimer` instance directly:

```python
from suitkaise import timing

with timing.TimeThis() as timer:
    # code to time
    pass

# access stats directly on the returned timer
print(timer.most_recent)
print(timer.mean)
```

### `threshold` parameter

Only record times above a minimum threshold:

```python
with timing.TimeThis(threshold=0.5) as timer:
    quick_operation()  # if < 0.5s, won't be recorded
```

This is useful for filtering out fast operations that you don't care about.

### methods

#### `TimeThis.__enter__()`

Entry point for the context manager. Starts timing the code block.

1. Calls `self.timer.start()`
2. Returns the `Sktimer` instance (`self.timer`)

#### `TimeThis.__exit__(exc_type, exc_val, exc_tb)`

Exits the context manager. Stops timing the code block.

1. Calls `self.timer.discard()` to get elapsed time without recording
2. If elapsed time >= threshold, calls `self.timer.add_time(elapsed)`
3. Returns `None` (doesn't suppress exceptions)

If an exception occurs in the code block, it will be raised after the context manager exits.

Even if an exception occurs in the code block, the timer is stopped but the measurement is only recorded if it meets the threshold.

#### pausing, resuming, and lapping

Pausing, resuming, and lapping are all available as methods on the `TimeThis` context manager.

- `pause()` - Pauses the timer
- `resume()` - Resumes the timer
- `lap()` - Records a lap time

These work exactly the same as the ones in the `Sktimer` class.

---

## `timethis` decorator

Decorator that dedicates a `Sktimer` instance to the function it decorates, timing the function's execution every time it is called.

Arguments
- `timer` - an optional `Sktimer` instance to use
- `threshold` - minimum elapsed time to record (default 0.0)

If `timer` is provided, the decorator will use the provided `Sktimer` instance.

Otherwise, it will create a new `Sktimer` instance, dedicated to the function it decorates.

### `threshold` parameter

Only record times above a minimum threshold:

```python
@timing.timethis(threshold=0.1)
def my_function():
    # very fast executions won't be recorded
    pass
```

### Mode 1: Explicit timer (`timer` provided)

When you pass a `Sktimer` to the decorator, it uses that timer directly.

1. At decoration time:
    - receives your provided `Sktimer` instance
    - creates a wrapper function around your original function

2. At call time (every time the decorated function runs):
    - calls `timer.start()` before the function runs
    - runs your original function
    - calls `timer.discard()` to get elapsed time
    - if elapsed >= threshold, calls `timer.add_time(elapsed)`
    - returns the function's result

This is useful when you want multiple functions to share the same timer for combined statistics.

### Mode 2: Auto-created global function timer

When `timer` is `None` (the default), the decorator creates and manages a timer for you.

1. At decoration time:
    - uses Python's `inspect` module to figure out where the function is defined
    - extracts the module name from `frame.f_back.f_globals.get('__name__')`
    - if the module name has dots (like `mypackage.submodule`), takes only the last part (`submodule`)
    
2. Builds a unique timer name based on the function's location:
    - checks `func.__qualname__` to see if the function is inside a class
    - if inside a class (qualname contains a dot like `MyClass.my_method`):
        - timer name becomes `{module}_{ClassName}_{method}_timer`
    - if at module level (no dot in qualname):
        - timer name becomes `{module}_{function}_timer`

3. Creates or retrieves the global timer:
    - the `timethis` function itself stores a dictionary `_global_timers` and a lock `_timers_lock`
    - acquires the lock (thread-safe)
    - if a timer with this name doesn't exist yet, creates a new `Sktimer()`
    - retrieves the timer from the dictionary
    - releases the lock

4. Creates the wrapper function (same as Mode 1)

5. Attaches the timer to the wrapper function:
    - sets `wrapper.timer = the_timer`
    - this lets you access statistics via `your_function.timer.mean`, etc.

6. At call time (every time the decorated function runs):
    - same as Mode 1: `start()`, run function, check threshold, record if above

### Why this design?

The auto-created timer is stored globally (attached to the `timethis` function itself), not recreated each time. This means:

- the timer persists across all calls to the decorated function
- statistics accumulate over the lifetime of your program
- you can access the timer anytime via `your_function.timer`
- thread-safe: multiple threads can call the decorated function, and each gets its own timing session

### `clear_global_timers()`

Clears all auto-created global timers.

1. Checks if `_global_timers` and `_timers_lock` exist on the `timethis` function
2. If they do:
    - acquires the lock
    - calls `.clear()` on the `_global_timers` dictionary
    - releases the lock

This is useful for long-running programs or test environments where you want to start fresh.

---

### Thread Safety

All timing classes use `threading.RLock()` (reentrant locks) for thread safety.

*What is a reentrant lock?*

A reentrant lock is a lock that can be acquired by the same thread multiple times without deadlocking.

This is useful for thread safety, as it allows the same thread to acquire the lock multiple times from different code or methods.

### Memory Management

The `Sktimer` stores all measurements in memory (unless `max_times` is set):
- each measurement is a single `float` (8 bytes)
- each pause duration is a single `float` (8 bytes)
- 1 million measurements ≈ 16 MB of memory

Use `reset()` periodically if running indefinitely

### Error Handling

- `Sktimer.stop()` raises `RuntimeError` if called without `start()`

- `Sktimer.start()` issues a `UserWarning` if called while timing is already in progress

- `Sktimer.pause()` issues a `UserWarning` if called when already paused

- `Sktimer.resume()` issues a `UserWarning` if called when not paused

- percentile calculations raise `ValueError` if percent is not in range 0-100

- the `@timethis` decorator always records timing (if above threshold), even if the function raises an exception
