# How `sktime` actually works

## Table of Contents

1. [Simple Timing Functions](#simple-timing-functions)
2. [`Yawn` Class](#yawn-class)
3. [`Timer` Class](#timer-class)
4. [`TimeThis` Context Manager](#timethis-context-manager)
5. [`@timethis` Decorator](#timethis-decorator)
6. [Misc](#misc)
7. [Internal Architecture](#internal-architecture)

---

## Simple Timing Functions

### `now()` and `get_current_time()`

Both functions do exactly the same thing - just use the one you prefer.

**How it works:**
1. Calls internal `_get_current_time()` from `time_ops.py`
2. `_get_current_time()` calls Python's `time.time()`
3. Returns current Unix timestamp as a float (seconds since January 1, 1970)

These use real world time, not performance counter time, so you can compare real timestamps that can be converted to human readable time.

---

### `sleep(seconds)`

Pauses the current thread for a specified amount of time, then returns the current time.

**How it works:**
1. Calls internal `_sleep(seconds)` from `time_ops.py`
2. `_sleep()` calls Python's `time.sleep(seconds)`
3. After sleeping, calls `now()` to get current time
4. Returns the timestamp after sleeping

This is useful because you can capture the time after sleeping without needing two lines of code.

---

### `elapsed(time1, time2=None)`

Calculates how much time has passed between two timestamps. Order doesn't matter - always returns a positive number.

**How it works:**
1. Calls internal `_elapsed_time(time1, time2)` from `time_ops.py`

2. If `time2` is `None`:
   - Sets `time2` to current time using `time.time()`

3. Calculates absolute difference using `math.fabs(time2 - time1)`
   - `math.fabs()` is used instead of `abs()` for best precision with float numbers

4. Returns the positive difference in seconds

The key feature is using `math.fabs()` which is optimized for floating point absolute values, giving better precision than regular `abs()`.

---

## Yawn Class

A sleep controller that only sleeps after being called a certain number of times. Useful for rate limiting or progressive delays.

### Initialization: `Yawn(sleep_duration, yawn_threshold, log_sleep=False)`

**How it works:**
1. Creates internal `_Yawn` instance from `time_ops.py`

2. `_Yawn.__init__()` stores:
   - `sleep_duration`: how long to sleep when threshold is reached
   - `yawn_threshold`: number of yawns needed before sleeping
   - `log_sleep`: whether to print messages when sleeping
   - `yawn_count`: counter starting at 0
   - `total_sleeps`: tracks how many times we've slept (starts at 0)
   - `_lock`: creates a `threading.RLock()` for thread safety

The lock ensures multiple threads can safely use the same Yawn instance without race conditions.

---

### `yawn()`

Registers a yawn and possibly sleeps.

**How it works:**
1. Acquires the thread lock

2. Increments `yawn_count` by 1

3. Checks if `yawn_count >= yawn_threshold`:
   - **If yes:**
     - If `log_sleep` is True, prints a message about sleeping
     - Calls `time.sleep(sleep_duration)` to actually sleep
     - Resets `yawn_count` to 0
     - Increments `total_sleeps` by 1
     - Returns `True`
   - **If no:**
     - Returns `False`

4. Releases the thread lock

The automatic counter reset means you don't have to manually reset it after sleeping.

---

### `reset()`

Resets the yawn counter without sleeping.

**How it works:**
1. Acquires the thread lock
2. Sets `yawn_count` to 0
3. Releases the thread lock

This is useful if you want to restart the counting without waiting for a sleep to happen.

---

### `get_stats()`

Returns a dictionary with current yawn statistics.

**How it works:**
1. Acquires the thread lock

2. Creates a dictionary with:
   - `current_yawns`: current yawn counter value
   - `yawn_threshold`: the threshold setting
   - `total_sleeps`: how many times we've slept so far
   - `sleep_duration`: how long each sleep lasts
   - `yawns_until_sleep`: calculated as `yawn_threshold - yawn_count`

3. Releases the thread lock

4. Returns the dictionary

All reads happen under the lock to ensure you get a consistent snapshot of the stats.

---

## Timer Class

A sophisticated timer for collecting timing measurements and calculating statistics. Supports pause/resume, lap timing, and can be used across multiple threads.

### Initialization: `Timer()`

**How it works:**
1. Creates internal `_Timer` instance from `time_ops.py`

2. `_Timer.__init__()` initializes:
   - `original_start_time`: set to `None` (will be set on first `start()`)
   - `times`: empty list to store all recorded measurements
   - `_paused_durations`: empty list to track pause time for each measurement
   - `_lock`: creates `threading.RLock()` for thread safety
   - `_sessions`: empty dictionary to track timing sessions per thread (keyed by thread ID)

The timer uses a session-based architecture where each thread gets its own session, allowing concurrent timing operations.

---

### `Timer.start()`

Starts timing a new measurement.

**How it works:**
1. Gets or creates a `_TimerSession` for the current thread:

   - Uses `threading.get_ident()` to get current thread ID

   - Looks up session in `_sessions` dictionary

   - If not found, creates new `_TimerSession` and stores it

2. Calls `session.start()` which:
   - Creates a new "frame" (measurement context) with:

     - `start_time`: current time from `perf_counter()` (high-resolution monotonic clock)
     - `paused`: `False`
     - `pause_started_at`: `None`
     - `total_paused`: `0.0`

   - Pushes frame onto the session's stack (supports nested timings)

3. If this is the first start ever, sets `original_start_time` to the start timestamp
4. Returns the start timestamp

The use of `perf_counter()` instead of `time.time()` provides more accurate interval measurements because it's not affected by system clock adjustments.

---

### `Timer.stop()`

Stops timing and records the measurement.

**How it works:**
1. Gets the current thread's session

2. Calls `session.stop()` which:
   - Gets the top frame from the stack

   - Calculates elapsed time:

     - Gets current time from `perf_counter()`
     - If currently paused, adds the current pause duration
     - Formula: `(end_time - start_time) - (total_paused + current_pause_duration)`

   - Calculates total pause duration

   - Pops the frame from the stack

   - Returns tuple of `(elapsed_time, total_paused)`

3. Acquires the manager lock

4. Appends elapsed time to `times` list

5. Appends pause duration to `_paused_durations` list

6. Releases the lock

7. Returns just the elapsed time (unwraps the tuple)

The elapsed time excludes any paused periods, giving you only the total time the timer was running.

---

### `Timer.lap()`

Records a lap time without stopping the timer.

**How it works:**
1. Gets the current thread's session

2. Calls `session.lap()` which:
   - Gets the top frame from the stack

   - Calculates elapsed time (same as `stop()`)

   - Calculates total pause duration

   - **Restarts the frame** by:

     - Setting `start_time` to current time
     - Resetting `total_paused` to `0.0`
     - Setting `paused` to `False`
     - Setting `pause_started_at` to `None`

   - Returns tuple of `(elapsed_time, total_paused)`

3. Acquires the manager lock

4. Appends elapsed time to `times` list

5. Appends pause duration to `_paused_durations` list

6. Releases the lock

7. Returns just the elapsed time

The key difference from `stop()` is the frame stays on the stack and restarts, so timing continues.

---

### `Timer.pause()`

Pauses the current timing measurement.

**How it works:**
1. Gets the current thread's session

2. Calls `session.pause()` which:

   - Gets the top frame from the stack

   - Checks if already paused:
     - If yes, issues a warning and returns

   - Sets `paused` to `True`

   - Records current time in `pause_started_at`


The pause time is tracked but not included in the final elapsed time calculation.

---

### `Timer.resume()`

Resumes a paused timing measurement.

**How it works:**
1. Gets the current thread's session

2. Calls `session.resume()` which:

   - Gets the top frame from the stack

   - Checks if not paused:
     - If not paused, issues a warning and returns

   - Calculates pause duration: `current_time - pause_started_at`
   - Adds pause duration to `total_paused`
   - Sets `paused` to `False`
   - Sets `pause_started_at` to `None`

Each pause/resume cycle accumulates in `total_paused`, which is subtracted from the final elapsed time.

---

### `Timer.add_time(time_measurement)`

Manually adds a pre-measured time to the statistics.

**How it works:**
1. Acquires the manager lock
2. Appends `time_measurement` to `times` list
3. Releases the lock

This bypasses the start/stop mechanism and directly adds a measurement. Useful for importing times from other sources.

---

### `Timer` Properties

All properties work similarly by acquiring the lock and calculating from the `times` list:

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

**`fastest_time_index`**: Returns the index of the fastest time

**`slowest_time_index`**: Returns the index of the slowest time

**`stdev`**: Uses `statistics.stdev(times)`, requires at least 2 measurements, returns `None` otherwise

**`variance`**: Uses `statistics.variance(times)`, requires at least 2 measurements, returns `None` otherwise

All property accesses acquire the lock to ensure thread-safe reads.

---

### `get_time(index)`

Gets a specific measurement by index.

**How it works:**
1. Acquires the lock
2. Checks if `0 <= index < len(times)`
3. If valid, returns `times[index]`
4. If invalid, returns `None`
5. Releases the lock

---

### `percentile(percent)`

Calculates a percentile of all measurements.

**How it works:**
1. Acquires the lock

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

---

### `get_stats()`

Creates a snapshot of all statistics.

**How it works:**
1. Acquires the lock

2. Returns `None` if no times recorded

3. Creates a new `_TimerStats` instance with:
   - Copy of the `times` list
   - The `original_start_time`
   - Copy of the `_paused_durations` list

4. Releases the lock

5. Returns the `_TimerStats` instance

The `_TimerStats` object calculates and stores all statistics at 
creation time.

Once created, the `_TimerStats` object is a frozen snapshot. You can access all the same properties and methods (like `percentile()`) without acquiring locks, making it fast for repeated access.

---

### `Timer.reset()`

Clears all timing data.

**How it works:**
1. Acquires the lock
2. Clears the `times` list
3. Sets `original_start_time` to `None`
4. Clears the `_sessions` dictionary (removes all thread sessions)
5. Clears the `_paused_durations` list
6. Releases the lock

This completely resets the timer as if it was just created.

---

## TimeThis Context Manager

A context manager that automatically starts and stops a timer when entering and exiting a code block.

### Initialization: `TimeThis(timer=None)`

**How it works:**
1. If `timer` is provided:
   - Stores the provided `Timer` instance

2. If `timer` is `None`:
   - Creates a new `Timer` instance

3. Stores the timer in `self.timer`

The context manager can either use an existing timer (to accumulate statistics) or create its own (for one-off measurements).

---

### Context Manager Methods

**`__enter__()`**:
1. Calls `self.timer.start()`
2. Returns `self.timer` (so you can access it with `as`)

**`__exit__(exc_type, exc_val, exc_tb)`**:
1. Calls `self.timer.stop()`
2. Records the measurement
3. Returns `None` (doesn't suppress exceptions)

Even if an exception occurs in the with-block, the timer is stopped and the measurement is recorded.

---

### Helper Methods

**`pause()`**: Calls `self.timer.pause()`

**`resume()`**: Calls `self.timer.resume()`

**`lap()`**: Calls `self.timer.lap()`

These allow you to control the timer from within the context block.

---

## Timethis Decorator

A decorator that automatically times function calls and accumulates statistics.

### `@timethis(timer_instance=None)`

This decorator has two modes depending on whether you provide a timer.

**Mode 1: Auto-created global timer (`timer_instance=None`)**

How it works:
1. At decoration time (when Python processes the `@timethis()` line):

   - Gets the current frame using `inspect.currentframe()`

   - Extracts the module name from `frame.f_back.f_globals['__name__']`

   - Strips package path to get just the module name

   - Checks `func.__qualname__` to determine if function is in a class:
     - If contains `.`: function is a class method → `module_ClassName_methodname_timer`

     - If no `.`: function is module-level → `module_functionname_timer`

   - Creates a global dictionary `timethis._global_timers` (thread-safe with lock) if it doesn't exist

   - Creates a new `Timer` with the generated name and stores it in `_global_timers`

   - Calls `_timethis_decorator(timer._timer)` to create the actual decorator

   - Attaches the timer to the wrapper function as `wrapper.timer`

2. At call time (each time the decorated function is called):
   - Calls `timer.start()`
   - Executes the function
   - Calls `timer.stop()` in a `finally` block (always runs, even with exceptions)
   - Returns the function's result

You can access the auto-created timer via `function_name.timer`.

**Mode 2: Explicit timer (`timer_instance` provided)**

How it works:
1. At decoration time:
   - Uses the provided `timer_instance._timer` (internal timer)
   - Calls `_timethis_decorator(timer._timer)` to create the actual decorator

2. At call time:
   - Same as Mode 1 - starts timer, calls function, stops timer

The difference is the timer is shared across multiple functions if you pass the same instance.

---

### `_timethis_decorator(timer_instance)`

The internal decorator implementation.

**How it works:**
1. Takes a `_Timer` instance (internal timer)

2. Returns a decorator function

3. The decorator creates a wrapper using `@wraps(func)`:
   - Preserves function name, docstring, and metadata
   - `start()` is called before function execution
   - Function is executed
   - `stop()` is called in `finally` block (always runs)
   - Returns function result

The `finally` block ensures timing is always recorded, even if the function raises an exception.

---

## Misc

### `clear_global_timers()`

Clears all auto-created global timers from the `@timethis()` decorator.

**How it works:**
1. Checks if `timethis._timers_lock` and `timethis._global_timers` exist

2. If they exist:
   - Acquires the lock
   - Gets the `_global_timers` dictionary
   - Calls `.clear()` on the dictionary (removes all entries)
   - Releases the lock

This is useful in long-running processes or test suites where you want to release memory or reset statistics.

---

## Internal Architecture

### Thread Safety

All timing classes use `threading.RLock()` (reentrant locks) for thread safety:
- **Reentrant** means the same thread can acquire the lock multiple times without deadlocking
- All state modifications happen inside lock context managers
- Property reads also acquire locks to ensure consistent snapshots

### Timer Session Architecture

The `_Timer` uses a sophisticated session-based system:

- Each thread gets its own `_TimerSession` (keyed by thread ID)

- Each session has a stack of "frames" (timing contexts)

- Frames support nested timings (start within a start)

- Sessions use `perf_counter()` for high-resolution monotonic timing

- The main `_Timer` aggregates results from all sessions into the shared `times` list

This architecture allows:
- Multiple threads to time concurrently without conflicts
- Nested timing contexts within the same thread
- All results merged for unified statistics

### Clock Choices

**Wall clock (`time.time()`)**: Used for `now()`, `get_current_time()`, and `elapsed()`
- Represents actual real-world time
- Can jump forward/backward with system clock adjustments
- Used when you need actual timestamps

**Performance counter (`perf_counter()`)**: Used for `Timer` intervals
- Monotonically increasing (never goes backward)
- High resolution (nanosecond precision on most systems)
- Not affected by system clock adjustments
- Used when you need accurate interval measurements

### Pause/Resume Mechanism

Pausing works by:
1. Recording the time when pause started
2. Accumulating pause durations in `total_paused`
3. Subtracting `total_paused` from the elapsed time calculation

This means:
- Paused time is tracked but excluded from measurements
- Multiple pause/resume cycles accumulate correctly
- Works correctly even if you stop while paused (current pause duration is included)

### Statistics Calculation

Statistics use Python's `statistics` module:
- `mean()`: arithmetic average
- `median()`: middle value when sorted
- `stdev()`: sample standard deviation (requires n ≥ 2)
- `variance()`: sample variance (requires n ≥ 2)

Percentiles use linear interpolation between data points for smooth results.

### Memory Management

The `Timer` stores all measurements in memory:
- Each measurement is a single float (8 bytes)
- Each pause duration is a single float (8 bytes)
- 1 million measurements ≈ 16 MB of memory
- Use `reset()` periodically if running indefinitely

### Error Handling

- Timer operations raise `RuntimeError` if called in wrong state (e.g., `stop()` without `start()`)

- Pause/resume issues a `UserWarning` if called in wrong state (e.g., `pause()` when already paused)

- Percentile calculations raise `ValueError` if percent is not in range 0-100

- The `@timethis` decorator always records timing, even if the function raises an exception
