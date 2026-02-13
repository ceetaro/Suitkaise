/*

synced from suitkaise-docs/timing/how-to-use.md

*/

rows = 2
columns = 1

# 1.1

title = "How to use `timing`"

# 1.2

text = "
`timing` provides simple and powerful timing utilities for measuring execution time, collecting statistics, and analyzing performance.

- Everything runs using `Sktimer`
Statistical timer that collects timing measurements and provides comprehensive statistics (mean, median, stdev, percentiles). Has more statistics that `timeit`.

- `timethis`
Decorator for timing function executions with automatic statistics collection.

- `TimeThis`
Context manager for timing code blocks with automatic start/stop.

With `timethis` and `TimeThis` you have 100% coverage. Anything and everything can be timed with one line of code.

Includes:
- thread safety
- deep statistical analysis
- one-line setup
- native async support

## Importing

```python
from suitkaise import timing
```

```python
from suitkaise.timing import Sktimer, TimeThis, timethis, time, sleep, elapsed, clear_global_timers
```

## Simple Functions

### `time()`

Get the current Unix timestamp.

```python
from suitkaise import timing

start_time = timing.time()
```

Wraps `time.time()` so that you don't have to import both `timing` and `time`.

Returns
`float`: Current Unix timestamp.

### `sleep()`

Sleep the current thread for a given number of seconds.

```python
from suitkaise import timing

# sleep for 2 seconds
timing.sleep(2)

# returns current time after sleeping
end_time = timing.sleep(2)
```

Arguments
`seconds`: Number of seconds to sleep.
- `float`
- required

Returns
`float`: Current time after sleeping.

#### Async Support

Use `.asynced()` for async contexts.

```python
# in an async function
end_time = await timing.sleep.asynced()(2)
```

Uses `asyncio.sleep` internally.

### `elapsed()`

Get the elapsed time between two timestamps.

```python
from suitkaise import timing

start_time = timing.time()
timing.sleep(2)
end_time = timing.time()

# with two times
elapsed = timing.elapsed(start_time, end_time)  # 2.0

# with one time (uses current time as end)
elapsed = timing.elapsed(start_time)
```

Arguments
`time1`: First timestamp.
- `float`
- required

`time2`: Second timestamp.
- `float | None = None`
- if `None`, uses current time

Returns
`float`: Absolute elapsed time in seconds.

Note: Order doesn't matter - always returns positive elapsed time.

(start of dropdown "`Sktimer`")
## `Sktimer`

Statistical timer for collecting and analyzing execution times.

```python
from suitkaise import timing

timer = timing.Sktimer()

for i in range(100):
    timer.start()
    do_work()
    timer.stop()

print(f"Mean: {timer.mean:.3f}s")
print(f"Std Dev: {timer.stdev:.3f}s")
print(f"95th percentile: {timer.percentile(95):.3f}s")
```

### Constructor

Arguments
`max_times`: Keep only the most recent N measurements (rolling window).
- `int | None = None`
- if `None`, keeps all measurements

(start of dropdown "Control Methods")
### Control Methods

#### `start()`

Start timing a new measurement.

```python
timer.start()
```

Returns
`float`: Start timestamp.

Raises
`UserWarning`: If called while timing is already in progress (creates nested frame).

#### `stop()`

Stop timing and record the measurement.

```python
timer.start()
do_work()
elapsed = timer.stop()  # returns elapsed time, records it
```

Returns
`float`: Elapsed time for this measurement.

Raises
`RuntimeError`: If timer was not started.

#### `discard()`

Stop timing but do NOT record the measurement.

```python
timer.start()
try:
    result = risky_operation()
    timer.stop()  # record successful timing
except Exception:
    timer.discard()  # don't record failed timing
```

Use when you want to abandon the current timing without polluting statistics.

Returns
`float`: Elapsed time that was discarded.

Raises
`RuntimeError`: If timer was not started.

#### `lap()`

Record a lap time (stop + start in one call).

```python
timer.start()

for i in range(100):
    do_work()
    timer.lap()  # records time since last lap/start, continues timing

timer.discard()  # don't record the 101st measurement still running

print(timer.mean)  # 100 measurements recorded
```

Returns
`float`: Elapsed time for this lap.

Raises
`RuntimeError`: If timer was not started.

#### `pause()`

Pause the current timing measurement.

```python
timer.start()
do_work()

timer.pause()
user_input = input("Continue? ")  # not counted in timing
timer.resume()

do_more_work()
elapsed = timer.stop()  # only counts work, not user input
```

Time spent paused is excluded from the final elapsed time.

Raises
`RuntimeError`: If timer is not running.
`UserWarning`: If already paused.

#### `resume()`

Resume a paused timing measurement.

```python
timer.resume()
```

Raises
`RuntimeError`: If timer is not running.
`UserWarning`: If not currently paused.

#### `add_time()`

Manually add a timing measurement to the `Sktimer`.

```python
timer.add_time(1.5)
timer.add_time(2.3)
timer.add_time(1.8)

print(timer.mean)  # 1.867
```

Arguments
`elapsed_time`: Time to add to statistics (in seconds).
- `float`
- required

#### `set_max_times()`

Set the rolling window size for stored measurements.

```python
timer.set_max_times(100)  # keep only last 100 measurements
timer.set_max_times(None)  # keep all measurements
```

Arguments
`max_times`: Keep only the most recent N times.
- `int | None`
- `None` keeps all

#### `reset()`

Clear all timing measurements.

```python
timer.reset()  # clears all measurements, like a new Sktimer()
```

(end of dropdown "Control Methods")

(start of dropdown "Statistics Properties")
### Statistics Properties

All statistics are accessed directly on the timer and are always up-to-date.

`num_times`: Number of recorded measurements.
- `int`

`most_recent`: Most recent timing measurement.
- `float | None`

`result`: Alias for `most_recent`.
- `float | None`

`total_time`: Sum of all times.
- `float | None`

`total_time_paused`: Total time spent paused across all measurements.
- `float | None`

`mean`: Average of all times.
- `float | None`

`median`: Median of all times.
- `float | None`

`min`: Minimum (fastest) time.
- `float | None`

`max`: Maximum (slowest) time.
- `float | None`

`fastest_time`: Alias for `min`.
- `float | None`

`slowest_time`: Alias for `max`.
- `float | None`

`fastest_index`: Index of fastest measurement.
- `int | None`

`slowest_index`: Index of slowest measurement.
- `int | None`

`stdev`: Standard deviation.
- `float | None`
- requires at least 2 measurements

`variance`: Variance.
- `float | None`
- requires at least 2 measurements

`max_times`: Current rolling window size.
- `int | None`

(end of dropdown "Statistics Properties")

### Statistics Methods

#### `get_time()`

Get a specific measurement by index.

```python
first_time = timer.get_time(0)
last_time = timer.get_time(-1)
```

Arguments
`index`: 0-based index of measurement.
- `int`

Returns
`float | None`: Timing measurement or `None` if index is invalid.

#### `percentile()`

Calculate any percentile of timing measurements.

```python
p50 = timer.percentile(50)   # median
p95 = timer.percentile(95)   # 95th percentile
p99 = timer.percentile(99)   # 99th percentile
```

Arguments
`percent`: Percentile to calculate (0-100).
- `float`

Returns
`float | None`: Percentile value or `None` if no measurements.

Raises
`ValueError`: If percent is not between 0 and 100.

#### `get_statistics()` / `get_stats()`

Get a frozen snapshot of all timing statistics.

```python
snapshot = timer.get_statistics()

# snapshot won't change even if timer continues
timer.start()
do_more_work()
timer.stop()

# snapshot still has old values
print(snapshot.mean)
```

Returns a `TimerStats` object containing all statistics calculated at the moment the method was called.

Returns
`TimerStats | None`: Snapshot or `None` if no measurements.

### `TimerStats`

Frozen snapshot of `Sktimer` statistics returned by `Sktimer.get_statistics()`.

All values are pre-computed and won't change even if the timer continues recording.

### Properties

All properties from `Sktimer` are available:
- `times`, `num_times`, `most_recent`, `most_recent_index`
- `total_time`, `total_time_paused`
- `mean`, `median`, `min`, `max`
- `slowest_time`, `fastest_time`, `slowest_index`, `fastest_index`
- `stdev`, `variance`

### Methods

#### `percentile()`

Same as `Sktimer.percentile()`.

```python
p95 = snapshot.percentile(95)
```

#### `get_time()`

Same as `Sktimer.get_time()`.

```python
first = snapshot.get_time(0)
```
(end of dropdown "`Sktimer`")


## `timethis` Decorator

Decorator that times function executions and records results in a `Sktimer`.

```python
from suitkaise import timing

@timing.timethis()
def quick_function():
    # ...
    pass

quick_function()

# access the auto-created timer
print(f"Last time: {quick_function.timer.most_recent:.3f}s")

# calling multiple times builds statistics
for i in range(100):
    quick_function()

print(f"Mean: {quick_function.timer.mean:.3f}s")
```

### Arguments

`timer`: Sktimer to accumulate timing data in.
- `Sktimer | None = None`
- if `None`, creates an auto-named global timer attached to the function

`threshold`: Minimum elapsed time to record.
- `float = 0.0`
- times below this threshold are discarded

`max_times`: Keep only the most recent N measurements.
- `int | None = None`

### Auto-Created Timers

When no timer is provided, the decorator creates a global timer with a naming convention:
- Module-level functions: `module_function_timer`
- Class methods: `module_ClassName_method_timer`

The timer is attached to the function as `.timer`:

```python
@timing.timethis()
def my_function():
    pass

my_function()
print(my_function.timer.mean)
```

### Shared Timer

Use a single timer across multiple functions:

```python
perf_timer = timing.Sktimer()
perf_timer.set_max_times(1000)

@timing.timethis(perf_timer)
def multiply(a, b):
    return a * b

@timing.timethis(perf_timer)
def divide(a, b):
    return a / b

for a, b in zip(range(1000), range(1, 1001)):
    multiply(a, b)
    divide(a, b)

print(f"Combined mean: {perf_timer.mean:.6f}s")
```

### Stacked Decorators

Use both a shared timer and a function-specific timer:

```python
perf_timer = timing.Sktimer()
overall_timer = timing.Sktimer()

# 2 stacked decorators on the same function
@timing.timethis(perf_timer)
@timing.timethis()
def multiply(a, b):
    return a * b

# supports infinite stacking
@timing.timethis(overall_timer)
@timing.timethis(perf_timer)
@timing.timethis()
def divide(a, b):
    return a / b

# ... call functions ...

# combined stats
print(f"Combined mean: {perf_timer.mean:.6f}s")

# individual stats
print(f"Multiply mean: {multiply.timer.mean:.6f}s")
print(f"Divide mean: {divide.timer.mean:.6f}s")
```

## `TimeThis` Context Manager

Context manager for timing code blocks with automatic timer management.

```python
from suitkaise import timing

with timing.TimeThis() as timer:
    do_work()

print(f"Time taken: {timer.most_recent:.3f}s")
```

### Constructor

Arguments
`timer`: Sktimer instance to use.
- `Sktimer | None = None`
- if `None`, creates a new Sktimer

`threshold`: Minimum elapsed time to record.
- `float = 0.0`
- times below this threshold are discarded

### One-Use Timer

For quick, one-off measurements:

```python
with timing.TimeThis() as timer:
    compress_file_with_gzip("data.csv")

print(f"Compression took: {timer.most_recent:.3f}s")
```

### Shared Timer

For accumulating statistics across multiple runs:

```python
api_timer = timing.Sktimer()

with timing.TimeThis(api_timer):
    response = requests.get("https://api.example.com/users")

with timing.TimeThis(api_timer):
    response = requests.get("https://api.example.com/posts")

print(f"Average API time: {api_timer.mean:.3f}s")
```

### Pause and Resume

```python
with timing.TimeThis() as timer:
    results = database.query("SELECT * FROM users")
    
    timer.pause()
    user_wants_export = input("Export to CSV? (y/n): ")
    timer.resume()
    
    if user_wants_export.lower() == 'y':
        export_to_csv(results)

print(f"Database operation took: {timer.most_recent:.3f}s (excluding user input)")
```

### Methods

`pause()`: Pause timing.

`resume()`: Resume timing.

`lap()`: Record a lap and continue timing.


## `clear_global_timers()`

Clear all auto-created global timers used by the `@timethis()` decorator.

```python
from suitkaise import timing

# ... many @timethis() decorated functions called ...

# clear data from auto-created timers to save resources
timing.clear_global_timers()
```

Useful for:
- Long-lived processes
- Test environments
- Releasing references and starting fresh

## Thread Safety

All `Sktimer` operations are thread-safe.

- Each thread gets its own timing session
- Multiple threads can time concurrently
- Statistics are aggregated across all threads

```python
import threading

timer = timing.Sktimer()

def worker():
    for _ in range(100):
        timer.start()
        do_work()
        timer.stop()

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# 400 total measurements across all threads (4 threads * 100 iterations)
print(f"Total measurements: {timer.num_times}")
print(f"Mean: {timer.mean:.3f}s")
```
"
