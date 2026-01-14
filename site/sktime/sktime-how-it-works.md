/*

how the sktime module actually works.

*/

rows = 2
columns = 1

# 1.1

title = "How `sktime` actually works"


# 1.2

text = "

`sktime` has no dependencies outside of the standard library.

- uses Unix timestamp (seconds since January 1, 1970)

- only calculates times using floats, no datetime objects are used


### `time()`

Calls Python's `time.time()` function, and returns the current time as a float.

- Uses real world time, not performance counter time

---

### `sleep()`

`sleep()` is an enhanced version of Python's `time.sleep()` function.

It pauses the current thread for a given number of seconds, just like `time.sleep()`, and then returns the current time.

Arguments:
- `seconds`: Number of seconds to sleep (can be fractional)

Returns:
- Current time after sleeping

```python
from suitkaise import sktime

# 2 ways to use `sleep()`

start_time = sktime.time()
end_time = sktime.sleep(2) # sleeps and returns the current time

# or ...

start_time = sktime.time()
sktime.sleep(2) # just sleeps, doesn't return
end_time = sktime.time()
```

1. calls Python's `time.sleep()` function with the given number of seconds
2. after sleeping, calls `time()` to get the current time.
3. returns the current time after sleeping as a float

---

### `elapsed()`

Calculates how much time has passed between two times. Order doesn't matter - always returns a positive float time.

Arguments:
- `time1`: First time
- `time2`: Second time (defaults to current time if `None`)

Returns:
- Positive elapsed time (in seconds) as a float

```python
from suitkaise import sktime

# 2 ways to use `elapsed()`

start_time = sktime.time()
end_time = sktime.sleep(2)

elapsed = sktime.elapsed(start_time, end_time)

# or ...

start_time = sktime.time()
sktime.sleep(2)
elapsed = sktime.elapsed(start_time)
```

1. If `time2` is `None`, `elapsed()` uses the current time as the end time (calls `sktime.time()`)
2. Calculates absolute difference using `math.fabs(time2 - time1)`
   - `math.fabs()` is used instead of `abs()` for best precision with float numbers
3. Returns the positive difference in seconds as a float

`fabs()` is a built-in function in the `math` module that returns the absolute value of a number, and is more precise than `abs()` for floating point numbers.

---

## `Yawn` Class

The `Yawn` class is a sleep controller that only sleeps after being called a certain number of times.

Unlike `suitkaise.Circuit` (which breaks and stops the loop), `Yawn` sleeps and continues. The counter auto-resets after each sleep.

Initialize with:
- `sleep_duration`: how long to sleep when threshold is reached (float)
- `yawn_threshold`: number of yawns needed before sleeping (int)
- `log_sleep`: whether to print messages when sleeping (`bool`, default `False`)

For readability, I recommend using keyword arguments when initializing the `Yawn` class.

```python
from suitkaise import sktime

y = sktime.Yawn(sleep_duration=2, yawn_threshold=3, log_sleep=True)
```

1. Creates a `Yawn` instance

2. stores the following attributes:
    - `sleep_duration`: how long to sleep when threshold is reached (float)

    - `yawn_threshold`: number of yawns needed before sleeping (int)

    - `log_sleep`: whether to print messages when sleeping
    
    - `yawn_count`: counter starting at 0

    - `total_sleeps`: tracks how many times we've slept (starts at 0)

    - `_lock`: creates a `threading.RLock()` for thread safety

The lock ensures multiple threads can safely use the same `Yawn` instance without race conditions.

### `Yawn.yawn()`

Registers a yawn and possibly sleeps if the threshold is reached.

Arguments:
- None

Returns:
- `True` if sleep occurred, `False` otherwise

1. Acquires the thread lock
2. Increments `yawn_count` by 1

3. Checks if `yawn_count >= yawn_threshold`:
   - *If `True`:*
     - If `log_sleep` is True, prints a message about sleeping
     - Calls `time.sleep(sleep_duration)` to actually sleep
     - Resets `yawn_count` to 0
     - Increments `total_sleeps` by 1
     - Returns `True`

   - *If `False`:*
     - Returns `False`

4. Releases the thread lock

The automatic counter reset means you don't have to manually reset it after sleeping.

### `Yawn.reset()`

Resets the yawn counter without sleeping.

Arguments:
- None

Returns:
- None

1. Acquires the thread lock
2. Resets `yawn_count` to 0
3. Releases the thread lock

This is useful if you want to restart the counting without waiting for a sleep to happen.

### `Yawn.get_stats()`

Returns a dictionary with current yawn statistics.

Arguments:
- None

Returns:
- Dictionary with:
  - `current_yawns`: current yawn counter value
  - `yawn_threshold`: the threshold setting
  - `total_sleeps`: how many times we've slept so far
  - `sleep_duration`: how long each sleep lasts
  - `yawns_until_sleep`: calculated as `yawn_threshold - yawn_count`

1. Acquires the thread lock
2. Creates a dictionary with the current values
3. Releases the thread lock
4. Returns the dictionary

All reads happen under the lock to ensure you get a consistent snapshot of the stats.

---

## `Sktimer` Class

The `Sktimer` is an advanced timer that can be used to time code execution, complete with statistics and pause/resume functionality.

It is also the base for the context manager `TimeThis`, the timing decorator `@timethis`, and the `processing` module's `@timesection` decorator.

No arguments are needed to initialize the `Sktimer` class.

```python
from suitkaise import sktime

t = sktime.Sktimer()
```

1. Creates a `Sktimer` instance
2. stores the following attributes:
   - `original_start_time`: set to `None` (will be set on first `start()`)
   - `times`: empty list to store all recorded measurements
   - `_paused_durations`: empty list to track pause time for each measurement
   - `_lock`: creates a `threading.RLock()` for thread safety
   - `_sessions`: empty dictionary to track timing sessions per thread (keyed by thread ID)
   - `_stats_view`: a `SktimerStatsView` instance for accessing statistics

Each timing operation is tracked separately. If you start timing from multiple places at once (like in parallel code), they won't interfere with each other — each gets its own independent tracking.

### `Sktimer.stats` property

The `stats` property returns a `SktimerStatsView` that provides organized access to all timer statistics.

```python
timer = sktime.Sktimer()
# ... record some timings ...

# Access statistics through the stats namespace
print(timer.mean)
print(timer.stdev)
print(timer.percentile(95))
print(timer.num_times)
```

The `SktimerStatsView` is a live view - it always reflects the current state of the timer. All property accesses are thread-safe.

### `Sktimer.start()`

Starts timing a new measurement.

Arguments:
- None

Returns:
- Time (in seconds) when the measurement started, as a float

If called while timing is already in progress, issues a `UserWarning` (it creates a nested timing frame).

1. Checks if there's already an active timing frame for this thread
   - If yes, issues a `UserWarning`

2. Gets or creates a `SktimerSession` for the current thread by calling `_get_or_create_session()`

   - Uses `threading.get_ident()` to get current thread ID

   - Looks up session in `_sessions` dictionary

   - If not found, creates new `SktimerSession` and stores it

3. Calls `session.start()` which:
    - Acquires session lock

    - Creates a new "frame" (measurement context) with:
        - `start_time`: current time from `perf_counter()`
        - `paused`: `False`
        - `pause_started_at`: `None`
        - `total_paused`: `0.0`

    - Pushes frame onto the session's stack (supports nested timings)

    - Releases session lock

4. If this is the first start ever, sets `original_start_time` to the start timestamp

5. Returns the start timestamp

(This section should be a dropdown that users can expand.)
*What is `perf_counter()` and why is it used?*

Python has two main ways to get the current time:

- `time.time()` — gives you the real-world clock time (like "3:45 PM"). But if your computer's clock gets adjusted (daylight saving, syncing with the internet, etc.), this number can jump forward or backward unexpectedly.

- `time.perf_counter()` — gives you a "stopwatch" time that only counts upward. It doesn't know what time of day it is, but it's extremely precise and never gets adjusted.

For measuring how long code takes to run, `perf_counter()` is the better choice because you want consistent, accurate measurements — not times that might suddenly shift because your computer synced its clock.

(This section should be a dropdown that users can expand.)
*What is a frame and a stack?*

Think of a stack like a stack of plates. You can only add plates to the top, and you can only remove plates from the top.

A **frame** is one "plate" — it represents a single timing measurement that's currently in progress.

A **stack** of frames lets you nest timings inside each other:

```python
timer.start()          # Frame 1 added to stack
  # do some work
  timer.start()        # Frame 2 added on top (warning issued)
    # do inner work
  timer.stop()         # Frame 2 removed, returns inner time
  # do more work
timer.stop()           # Frame 1 removed, returns total time
```

Each `start()` pushes a new frame onto the stack. Each `stop()` pops the top frame off and calculates how long that specific measurement took. This lets you measure the total time of something while also measuring individual pieces inside it.

### `Sktimer.stop()`

Stops timing the current measurement and returns the elapsed time.

Arguments:
- None

Returns:
- elapsed time (in seconds) as a float

1. Gets the current thread's session

2. Calls `session.stop()` which:
    - Acquires session lock

    - Gets the top frame from the stack

    - Calculates elapsed time:
        - Gets current time from `perf_counter()`
        - If currently paused, adds the current pause duration
        - Formula: `(end_time - start_time) - (total_paused + current_pause_duration)`
     
    - Calculates total pause duration
    
    - Pops the frame from the stack
    
    - Returns tuple of `(elapsed_time, total_paused)` to the caller (`Sktimer.stop()`)

    - Releases session lock

3. Acquires the `Sktimer` manager lock
4. Appends elapsed time to `times` list
5. Appends pause duration to `_paused_durations` list
6. Releases the lock
7. Returns just the elapsed time (unwraps the tuple)

The elapsed time excludes any paused periods, giving you only the total time the timer was running.

### `Sktimer.discard()`

Stops timing but does NOT record the measurement.

Use this when you want to abandon the current timing session without polluting your statistics (e.g., an error occurred, or this was a warm-up run).

Arguments:
- None

Returns:
- elapsed time that was discarded (for reference) as a float

1. Gets the current thread's session

2. Calls `session.stop()` which works the same as in `Sktimer.stop()`

3. Does NOT append to `times` or `_paused_durations` lists

4. Returns the elapsed time (for reference, even though it wasn't recorded)

```python
timer.start()
try:
    result = risky_operation()
    timer.stop()  # Record successful timing
except Exception:
    timer.discard()  # Stop but don't record failed timing
```

### `Sktimer.lap()`

Records a lap time without stopping the timer.

Arguments:
- None

Returns:
- elapsed time (in seconds) as a float

1. Gets the current thread's session

2. Calls `session.lap()` which:
    - Acquires session lock

    - Gets the top frame from the stack

    - Calculates elapsed time just like `session.stop()`
    
    - Calculates total pause duration

    - **Restarts the frame** by:
        - Setting `start_time` to current time
        - Resetting `total_paused` to `0.0`
        - Setting `paused` to `False`
        - Setting `pause_started_at` to `None`
    
    - Returns tuple of `(elapsed_time, total_paused)` to the caller (`Sktimer.lap()`)

    - Releases session lock
    
3. Acquires the `Sktimer` manager lock
4. Appends elapsed time to `times` list
5. Appends pause duration to `_paused_durations` list
6. Releases the lock
7. Returns just the elapsed time (unwraps the tuple)

The key difference from `stop()` is the frame stays on the stack and restarts, so timing continues. It's as if you called `Sktimer.start()` the instant after the previous `Sktimer.stop()` call.

### `Sktimer.pause()`

Pauses the current timing measurement.

Arguments:
- None

Returns:
- None

1. Gets the current thread's session

2. Calls `session.pause()` which:
    - Acquires session lock

    - Gets the top frame from the stack

    - Checks if already paused:
        - If yes, issues a `UserWarning` and returns
        - If no, sets `paused` to `True` and `pause_started_at` to current time

    - Releases session lock


The pause time is tracked but not included in the final elapsed time calculation.

### `Sktimer.resume()`

Resumes a paused timing measurement.

Arguments:
- None

Returns:
- None

1. Gets the current thread's session

2. Calls `session.resume()` which:
    - Acquires session lock

    - Gets the top frame from the stack

    - Checks if not paused:
        - If not paused, issues a `UserWarning` and returns

    - Calculates pause duration: `current_time - pause_started_at`
    - Adds pause duration to `total_paused`
    - Sets `paused` to `False`
    - Sets `pause_started_at` to `None`

    - Releases session lock

Each pause/resume cycle accumulates in `total_paused`, which is subtracted from the final elapsed time.

### `Sktimer.add_time()`

Manually adds a pre-measured time to the statistics (a float).

Arguments:
- `elapsed_time`: time to add to statistics (in seconds) as a float

Returns:
- None

1. Acquires the `Sktimer` manager lock
2. Appends `elapsed_time` to `times` list
3. Appends `0.0` to `_paused_durations` list
4. Releases the lock
5. Returns None

### `Sktimer` statistics properties

All statistics are accessed directly on the timer and work by acquiring the lock and calculating from the `times` list:

(This section should be a dropdown that users can expand.)
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
(End of dropdown)

All property accesses acquire the lock to ensure thread-safe reads.

### `Sktimer` statistics methods

#### `timer.get_time()`

Gets and returns a specific timing measurement by index.

Arguments:
- `index`: 0-based index of measurement

Returns:
- timing measurement (in seconds) as a float or `None` if index is out of range

1. Acquires the `Sktimer` manager lock
2. Checks if `0 <= index < len(times)`
3. If valid, returns `times[index]`
4. If invalid, returns `None`
5. Releases the lock

#### `timer.percentile()`

Calculates a percentile of all measurements.

Arguments:
- `percent`: percentile to calculate (between 0 and 100)

Returns:
- percentile value (in seconds) as a float or `None` if no measurements

1. Acquires the `Sktimer` manager lock
2. Checks if `times` is empty - returns `None` if so
3. Validates `percent` is between 0 and 100 - raises `ValueError` if not
4. Sorts the times list
5. Calculates index: `(percent / 100) * (len(sorted_times) - 1)`
6. If index is a whole number:
   - Returns the value at that exact index
7. If index is fractional:
   - Gets values at floor and ceiling indices
   - Performs linear interpolation: `value = lower * (1 - weight) + upper * weight`
   - Where `weight` is the fractional part of the index
8. Releases the lock
9. Returns the percentile value

Linear interpolation provides smooth percentile values between data points.

### `Sktimer.get_statistics()` / `Sktimer.get_stats()`

Creates a frozen snapshot of all statistics.

Arguments:
- None

Returns:
- a `SktimerStats` object or `None` if no measurements have been recorded

1. Acquires the `Sktimer` manager lock

2. Returns `None` if no measurements have been recorded

3. Creates a new `SktimerStats` object with:
    - Copy of the `times` list
    - The `original_start_time`
    - Copy of the `_paused_durations` list

4. Releases the lock

5. Returns the `SktimerStats` object

The `SktimerStats` object calculates and stores all statistics at creation time.

Once created, the `SktimerStats` object is a frozen snapshot. You can access all the same properties and methods (like `percentile()`) without acquiring locks, making it fast for repeated access.

`get_stats()` is an alias for `get_statistics()`.

### `Sktimer.reset()`

Clears all timing data.

Arguments:
- None

Returns:
- None

1. Acquires the `Sktimer` manager lock
2. Clears the `times` list
3. Sets `original_start_time` to `None`
4. Clears the `_sessions` dictionary (removes all thread sessions)
5. Clears the `_paused_durations` list
6. Releases the lock

This completely resets the timer as if it was just created.

---

## `TimeThis` context manager

A context manager that automatically starts and stops a timer when entering and exiting a code block.

Initialize with:
- `timer`: an optional `Sktimer` instance to use

If `timer` is provided, the context manager will use the provided `Sktimer` instance.

Otherwise, it will create a new `Sktimer` instance, which will only be used for this single timing operation.

The context manager returns the `Sktimer` instance directly:

```python
from suitkaise import sktime

with sktime.TimeThis() as timer:
    # code to time
    pass

# Access stats directly on the returned timer
print(timer.most_recent)
print(timer.mean)
```

### methods

#### `TimeThis.__enter__()`

Entry point for the context manager. Starts timing the code block.

1. Calls `self.timer.start()`
2. Returns the `Sktimer` instance (`self.timer`)

#### `TimeThis.__exit__(exc_type, exc_val, exc_tb)`

Exits the context manager. Stops timing the code block.

1. Calls `self.timer.stop()`
2. Returns `None` (doesn't suppress exceptions)

If an exception occurs in the code block, it will be raised after the context manager exits.

Even if an exception occurs in the code block, the timer is stopped and the measurement is recorded.

#### pausing, resuming, and lapping

Pausing, resuming, and lapping are all available as methods on the `TimeThis` context manager.

- `pause()`: Pauses the timer
- `resume()`: Resumes the timer
- `lap()`: Records a lap time

These work exactly the same as the ones in the `Sktimer` class.

---

## `timethis` decorator

Decorator that dedicates a `Sktimer` instance to the function it decorates, timing the function's execution every time it is called.

Arguments:
- `timer_instance`: an optional `Sktimer` instance to use

If `timer_instance` is provided, the decorator will use the provided `Sktimer` instance.

Otherwise, it will create a new `Sktimer` instance, dedicated to the function it decorates.

### Mode 1: Explicit timer (`timer_instance` provided)

When you pass a `Sktimer` to the decorator, it uses that timer directly.

1. At decoration time:
    - Receives your provided `Sktimer` instance
    - Creates a wrapper function around your original function

2. At call time (every time the decorated function runs):
    - Calls `timer_instance.start()` before the function runs
    - Runs your original function
    - Calls `timer_instance.stop()` after the function completes (even if it throws an error)
    - Returns the function's result

This is useful when you want multiple functions to share the same timer for combined statistics.

### Mode 2: Auto-created global function timer

When `timer_instance` is `None` (the default), the decorator creates and manages a timer for you.

1. At decoration time:
    - Uses Python's `inspect` module to figure out where the function is defined
    - Extracts the module name from `frame.f_back.f_globals.get('__name__')`
    - If the module name has dots (like `mypackage.submodule`), takes only the last part (`submodule`)
    
2. Builds a unique timer name based on the function's location:
    - Checks `func.__qualname__` to see if the function is inside a class
    - If inside a class (qualname contains a dot like `MyClass.my_method`):
        - Sktimer name becomes `{module}_{ClassName}_{method}_timer`
    - If at module level (no dot in qualname):
        - Sktimer name becomes `{module}_{function}_timer`

3. Creates or retrieves the global timer:
    - The `timethis` function itself stores a dictionary `_global_timers` and a lock `_timers_lock`
    - Acquires the lock (thread-safe)
    - If a timer with this name doesn't exist yet, creates a new `Sktimer()`
    - Retrieves the timer from the dictionary
    - Releases the lock

4. Creates the wrapper function (same as Mode 1)

5. Attaches the timer to the wrapper function:
    - Sets `wrapper.timer = the_timer`
    - This lets you access statistics via `your_function.timer.mean`, etc.

6. At call time (every time the decorated function runs):
    - Same as Mode 1: `start()`, run function, `stop()`

### Why this design?

The auto-created timer is stored globally (attached to the `timethis` function itself), not recreated each time. This means:

- The timer persists across all calls to the decorated function
- Statistics accumulate over the lifetime of your program
- You can access the timer anytime via `your_function.timer`
- Thread-safe: multiple threads can call the decorated function, and each gets its own timing session

### `clear_global_timers()`

Clears all auto-created global timers.

1. Checks if `_global_timers` and `_timers_lock` exist on the `timethis` function
2. If they do:
    - Acquires the lock
    - Calls `.clear()` on the `_global_timers` dictionary
    - Releases the lock

This is useful for long-running programs or test environments where you want to start fresh.

---

### Thread Safety

All timing classes use `threading.RLock()` (reentrant locks) for thread safety.

(This section should be a dropdown that users can expand.)
*What is a reentrant lock?*

A reentrant lock is a lock that can be acquired by the same thread multiple times without deadlocking.

This is useful for thread safety, as it allows the same thread to acquire the lock multiple times from different code or methods.
(End of dropdown)

### Memory Management

The `Sktimer` stores all measurements in memory:
- Each measurement is a single float (8 bytes)
- Each pause duration is a single float (8 bytes)
- 1 million measurements ≈ 16 MB of memory

Use `reset()` periodically if running indefinitely

### Error Handling

- `Sktimer.stop()` raises `RuntimeError` if called without `start()`

- `Sktimer.start()` issues a `UserWarning` if called while timing is already in progress

- `Sktimer.pause()` issues a `UserWarning` if called when already paused

- `Sktimer.resume()` issues a `UserWarning` if called when not paused

- Percentile calculations raise `ValueError` if percent is not in range 0-100

- The `@timethis` decorator always records timing, even if the function raises an exception
