/*

synced from suitkaise-docs/timing/how-to-use.md

*/

rows = 2
columns = 1

# 1.1

title = "How to use `<suitkaise-api>timing</suitkaise-api>`"

# 1.2

text = "
`<suitkaise-api>timing</suitkaise-api>` provides simple and powerful timing utilities for measuring execution time, collecting statistics, and analyzing performance.

- Everything runs using `<suitkaise-api>Sktimer</suitkaise-api>`
Statistical timer that collects timing measurements and provides comprehensive statistics (mean, median, stdev, percentiles). Has more statistics that `timeit`.

- `<suitkaise-api>timethis</suitkaise-api>`
Decorator for timing function executions with automatic statistics collection.

- `<suitkaise-api>TimeThis</suitkaise-api>`
Context manager for timing code blocks with automatic start/stop.

With `<suitkaise-api>timethis</suitkaise-api>` and `<suitkaise-api>TimeThis</suitkaise-api>` you have 100% coverage. Anything and everything can be timed with one line of code.

Includes:
- thread safety
- deep statistical analysis
- one-line setup
- native async support

## Importing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
```

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>, <suitkaise-api>TimeThis</suitkaise-api>, <suitkaise-api>timethis</suitkaise-api>, time, sleep, <suitkaise-api>elapsed</suitkaise-api>, <suitkaise-api>clear_global_timers</suitkaise-api>
```

## Simple Functions

### `time()`

Get the current Unix timestamp.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

start_time = <suitkaise-api>timing</suitkaise-api>.time()
```

Wraps `time.time()` so that you don't have to import both `<suitkaise-api>timing</suitkaise-api>` and `time`.

Returns
`float`: Current Unix timestamp.

### `sleep()`

Sleep the current thread for a given number of seconds.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# sleep for 2 seconds
<suitkaise-api>timing</suitkaise-api>.sleep(2)

# returns current time after sleeping
end_time = <suitkaise-api>timing</suitkaise-api>.sleep(2)
```

Arguments
`seconds`: Number of seconds to sleep.
- `float`
- required

Returns
`float`: Current time after sleeping.

#### Async Support

Use `.<suitkaise-api>asynced</suitkaise-api>()` for async contexts.

```python
# in an async function
end_time = await <suitkaise-api>timing</suitkaise-api>.sleep.<suitkaise-api>asynced</suitkaise-api>()(2)
```

Uses `asyncio.sleep` internally.

### `<suitkaise-api>elapsed</suitkaise-api>()`

Get the elapsed time between two timestamps.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

start_time = <suitkaise-api>timing</suitkaise-api>.time()
<suitkaise-api>timing</suitkaise-api>.sleep(2)
end_time = <suitkaise-api>timing</suitkaise-api>.time()

# with two times
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start_time, end_time)  # 2.0

# with one time (uses current time as end)
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start_time)
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

(start of dropdown "`<suitkaise-api>Sktimer</suitkaise-api>`")
## `<suitkaise-api>Sktimer</suitkaise-api>`

Statistical timer for collecting and analyzing execution times.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

for i in range(100):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    do_work()
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

print(f"Mean: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"Std Dev: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>:.3f}s")
print(f"95th percentile: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95):.3f}s")
```

### Constructor

Arguments
`max_times`: Keep only the most recent N measurements (rolling window).
- `int | None = None`
- if `None`, keeps all measurements

(start of dropdown "Control Methods")
### Control Methods

#### `<suitkaise-api>start</suitkaise-api>()`

Start timing a new measurement.

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
```

Returns
`float`: Start timestamp.

Raises
`UserWarning`: If called while timing is already in progress (creates nested frame).

#### `<suitkaise-api>stop</suitkaise-api>()`

Stop timing and record the measurement.

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
do_work()
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()  # returns <suitkaise-api>elapsed</suitkaise-api> time, records it
```

Returns
`float`: Elapsed time for this measurement.

Raises
`RuntimeError`: If timer was not started.

#### `<suitkaise-api>discard</suitkaise-api>()`

Stop timing but do NOT record the measurement.

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
try:
    <suitkaise-api>result</suitkaise-api> = risky_operation()
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()  # record successful <suitkaise-api>timing</suitkaise-api>
except Exception:
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()  # don't record failed <suitkaise-api>timing</suitkaise-api>
```

Use when you want to abandon the current timing without polluting statistics.

Returns
`float`: Elapsed time that was discarded.

Raises
`RuntimeError`: If timer was not started.

#### `<suitkaise-api>lap</suitkaise-api>()`

Record a lap time (stop + start in one call).

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

for i in range(100):
    do_work()
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>lap</suitkaise-api>()  # records time since last lap/start, continues <suitkaise-api>timing</suitkaise-api>

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()  # don't record the 101st measurement still running

print(<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)  # 100 measurements recorded
```

Returns
`float`: Elapsed time for this lap.

Raises
`RuntimeError`: If timer was not started.

#### `<suitkaise-api>pause</suitkaise-api>()`

Pause the current timing measurement.

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
do_work()

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>pause</suitkaise-api>()
user_input = input("Continue? ")  # not counted in <suitkaise-api>timing</suitkaise-api>
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>resume</suitkaise-api>()

do_more_work()
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()  # only counts work, not user input
```

Time spent paused is excluded from the final elapsed time.

Raises
`RuntimeError`: If timer is not running.
`UserWarning`: If already paused.

#### `<suitkaise-api>resume</suitkaise-api>()`

Resume a paused timing measurement.

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>resume</suitkaise-api>()
```

Raises
`RuntimeError`: If timer is not running.
`UserWarning`: If not currently paused.

#### `<suitkaise-api>add_time</suitkaise-api>()`

Manually add a timing measurement to the `<suitkaise-api>Sktimer</suitkaise-api>`.

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(1.5)
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(2.3)
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(1.8)

print(<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)  # 1.867
```

Arguments
`elapsed_time`: Time to add to statistics (in seconds).
- `float`
- required

#### `<suitkaise-api>set_max_times</suitkaise-api>()`

Set the rolling window size for stored measurements.

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>set_max_times</suitkaise-api>(100)  # keep only last 100 measurements
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>set_max_times</suitkaise-api>(None)  # keep all measurements
```

Arguments
`max_times`: Keep only the most recent N times.
- `int | None`
- `None` keeps all

#### `<suitkaise-api>reset</suitkaise-api>()`

Clear all timing measurements.

```python
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>reset</suitkaise-api>()  # clears all measurements, like a new <suitkaise-api>Sktimer</suitkaise-api>()
```

(end of dropdown "Control Methods")

(start of dropdown "Statistics Properties")
### Statistics Properties

All statistics are accessed directly on the timer and are always up-to-date.

`num_times`: Number of recorded measurements.
- `int`

`most_recent`: Most recent timing measurement.
- `float | None`

`<suitkaise-api>result</suitkaise-api>`: Alias for `most_recent`.
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
first_time = <suitkaise-api>timer</suitkaise-api>.get_time(0)
last_time = <suitkaise-api>timer</suitkaise-api>.get_time(-1)
```

Arguments
`index`: 0-based index of measurement.
- `int`

Returns
`float | None`: Timing measurement or `None` if index is invalid.

#### `<suitkaise-api>percentile</suitkaise-api>()`

Calculate any percentile of timing measurements.

```python
p50 = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(50)   # median
p95 = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95)   # 95th percentile
p99 = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(99)   # 99th percentile
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
snapshot = <suitkaise-api>timer</suitkaise-api>.get_statistics()

# snapshot won't change even if timer continues
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
do_more_work()
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

# snapshot still has old values
print(snapshot.<suitkaise-api>mean</suitkaise-api>)
```

Returns a `TimerStats` object containing all statistics calculated at the moment the method was called.

Returns
`TimerStats | None`: Snapshot or `None` if no measurements.

### `TimerStats`

Frozen snapshot of `<suitkaise-api>Sktimer</suitkaise-api>` statistics returned by `<suitkaise-api>Sktimer</suitkaise-api>.get_statistics()`.

All values are pre-computed and won't change even if the timer continues recording.

### Properties

All properties from `<suitkaise-api>Sktimer</suitkaise-api>` are available:
- `times`, `num_times`, `most_recent`, `most_recent_index`
- `total_time`, `total_time_paused`
- `mean`, `median`, `min`, `max`
- `slowest_time`, `fastest_time`, `slowest_index`, `fastest_index`
- `stdev`, `variance`

### Methods

#### `<suitkaise-api>percentile</suitkaise-api>()`

Same as `<suitkaise-api>Sktimer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>()`.

```python
p95 = snapshot.<suitkaise-api>percentile</suitkaise-api>(95)
```

#### `get_time()`

Same as `<suitkaise-api>Sktimer</suitkaise-api>.get_time()`.

```python
first = snapshot.get_time(0)
```
(end of dropdown "`<suitkaise-api>Sktimer</suitkaise-api>`")


## `<suitkaise-api>timethis</suitkaise-api>` Decorator

Decorator that times function executions and records results in a `<suitkaise-api>Sktimer</suitkaise-api>`.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
def quick_function():
    # ...
    pass

quick_function()

# access the auto-created timer
print(f"Last time: {quick_function.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")

# calling multiple times builds statistics
for i in range(100):
    quick_function()

print(f"Mean: {quick_function.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
```

### Arguments

`timer`: Sktimer to accumulate timing data in.
- `<suitkaise-api>Sktimer</suitkaise-api> | None = None`
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

The timer is attached to the function as `.<suitkaise-api>timer</suitkaise-api>`:

```python
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
def my_function():
    pass

my_function()
print(my_function.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
```

### Shared Timer

Use a single timer across multiple functions:

```python
perf_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()
perf_timer.<suitkaise-api>set_max_times</suitkaise-api>(1000)

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(perf_timer)
def multiply(a, b):
    return a * b

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(perf_timer)
def divide(a, b):
    return a / b

for a, b in zip(range(1000), range(1, 1001)):
    multiply(a, b)
    divide(a, b)

print(f"Combined mean: {perf_timer.<suitkaise-api>mean</suitkaise-api>:.6f}s")
```

### Stacked Decorators

Use both a shared timer and a function-specific timer:

```python
perf_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()
overall_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

# 2 stacked decorators on the same function
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(perf_timer)
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
def multiply(a, b):
    return a * b

# supports infinite stacking
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(overall_timer)
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(perf_timer)
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
def divide(a, b):
    return a / b

# ... call functions ...

# combined stats
print(f"Combined mean: {perf_timer.<suitkaise-api>mean</suitkaise-api>:.6f}s")

# individual stats
print(f"Multiply mean: {multiply.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.6f}s")
print(f"Divide mean: {divide.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.6f}s")
```

## `<suitkaise-api>TimeThis</suitkaise-api>` Context Manager

Context manager for timing code blocks with automatic timer management.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>() as timer:
    do_work()

print(f"Time taken: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")
```

### Constructor

Arguments
`timer`: Sktimer instance to use.
- `<suitkaise-api>Sktimer</suitkaise-api> | None = None`
- if `None`, creates a new Sktimer

`threshold`: Minimum elapsed time to record.
- `float = 0.0`
- times below this threshold are discarded

### One-Use Timer

For quick, one-off measurements:

```python
with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>() as timer:
    compress_file_with_gzip("data.csv")

print(f"Compression took: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")
```

### Shared Timer

For accumulating statistics across multiple runs:

```python
api_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>(api_timer):
    response = requests.get("https://api.example.com/users")

with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>(api_timer):
    response = requests.get("https://api.example.com/posts")

print(f"Average API time: {api_timer.<suitkaise-api>mean</suitkaise-api>:.3f}s")
```

### Pause and Resume

```python
with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>() as timer:
    results = database.query("SELECT * FROM users")
    
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>pause</suitkaise-api>()
    user_wants_export = input("Export to CSV? (y/n): ")
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>resume</suitkaise-api>()
    
    if user_wants_export.lower() == 'y':
        export_to_csv(results)

print(f"Database operation took: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s (excluding user input)")
```

### Methods

`<suitkaise-api>pause</suitkaise-api>()`: Pause timing.

`<suitkaise-api>resume</suitkaise-api>()`: Resume timing.

`<suitkaise-api>lap</suitkaise-api>()`: Record a lap and continue timing.


## `<suitkaise-api>clear_global_timers</suitkaise-api>()`

Clear all auto-created global timers used by the `@<suitkaise-api>timethis</suitkaise-api>()` decorator.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ... many @<suitkaise-api>timethis</suitkaise-api>() decorated functions called ...

# clear data from auto-created timers to save resources
<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>clear_global_timers</suitkaise-api>()
```

Useful for:
- Long-lived processes
- Test environments
- Releasing references and starting fresh

## Thread Safety

All `<suitkaise-api>Sktimer</suitkaise-api>` operations are thread-safe.

- Each thread gets its own timing session
- Multiple threads can time concurrently
- Statistics are aggregated across all threads

```python
import threading

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

def worker():
    for _ in range(100):
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        do_work()
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.<suitkaise-api>start</suitkaise-api>()
for t in threads:
    t.join()

# 400 total measurements across all threads (4 threads * 100 iterations)
print(f"Total measurements: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Mean: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
```
"
