# SKTime Concept

## Overview

sktime is an expansion on basic timing functionality, providing intuitive timing operations, performance measurement, and time-based utilities that make time handling easier and more powerful.

## Core Philosophy

SKTime provides a comprehensive timing toolkit that goes beyond basic `time.time()` calls, offering specialized classes and utilities for different timing scenarios.

## Key Components

### Basic Time Operations
- **Current time**: `sktime.now()` and `sktime.get_current_time()`
- **Sleep functionality**: `sktime.sleep(seconds)`
- **Time differences**: `sktime.elapsed(time1, time2)` with flexible argument handling

### Yawn Class - Conditional Sleep
The `Yawn` class provides a unique approach to rate limiting and conditional sleeping:
- **Sleep after N actions**: Sleep for X seconds after Y occurrences
- **Automatic reset**: Counter resets after sleep occurs
- **Logging support**: Optional logging when sleep occurs

### Stopwatch Class - Precise Timing
Professional stopwatch functionality with:
- **Start/pause/resume**: Full control over timing sessions
- **Lap timing**: Record intermediate times
- **Total time tracking**: Complete session duration
- **State management**: Proper handling of timing states

### Timer Class - Performance Measurement
Advanced timing for performance analysis:
- **Decorator support**: `@sktime.timethis(timer)` for function timing
- **Context manager**: `with sktime.Timer() as timer:` for block timing
- **Statistical analysis**: Mean, median, min, max, standard deviation
- **Historical data**: Access to all recorded times
- **Performance tracking**: Long-term performance monitoring

## Usage Patterns

### Rate Limiting with Yawn
```python
# Sleep for 3 seconds after every 4 operations
_yawn = sktime.Yawn(3, 4, log_sleep=True)

for operation in operations:
    _yawn.yawn()  # Will sleep on 4th, 8th, 12th calls, etc.
    perform_operation()
```

### Performance Monitoring with Timer
```python
timer = sktime.Timer()

@sktime.timethis(timer)
def expensive_function():
    # Your code here
    pass

# After many calls, analyze performance
print(f"Average: {timer.mean:.3f}s")
print(f"Slowest: {timer.longest:.3f}s")
```

### Precise Measurement with Stopwatch
```python
sw = sktime.Stopwatch()
sw.start()

# Do work
sw.pause()
# Break
sw.resume()
# More work
sw.lap()  # Record lap time

total_time = sw.total_time
lap_time = sw.get_laptime(1)
```

## Integration Benefits
- **Cross-module compatibility**: Works seamlessly with other SK modules
- **Performance integration**: Built-in timing for XProcess and other modules
- **Flexible time handling**: Order-independent elapsed time calculation
- **Professional timing**: Enterprise-grade timing utilities

## Examples

### Basic Time Operations

```python
from suitkaise import sktime

# get current time (same as time.time())
now = sktime.now()
# longer, clearer alias
now = sktime.get_current_time()

# sleep for n seconds
sktime.sleep(2)

# find the difference between 2 times
time1 = now
time2 = now - 72

# order doesn't matter! result: 72
time_diff = sktime.elapsed(time2, time1)

# if only one time is added, assumes second time is current time
# result: still 72!
time_diff = sktime.elapsed(time2)
```

### Yawn Class - Conditional Sleep

```python
# sleep after yawning twice

# setup to sleep for 3 seconds after yawning 4 times
# log_sleep will tell you when sleep occurs due to yawn if set to true
_yawn = sktime.Yawn(3, 4, log_sleep=True)

# doesnt sleep
_yawn.yawn()
# doesnt sleep
_yawn.yawn()
# doesnt sleep
_yawn.yawn()
# sleeps for 3 seconds!
_yawn.yawn()

# later...
# doesnt sleep
_yawn.yawn()
# doesnt sleep
_yawn.yawn()
# doesnt sleep
_yawn.yawn()
# sleeps for 3 seconds!
_yawn.yawn()
```

### Stopwatch Operations

```python
# time operations with a stopwatch
sw = sktime.Stopwatch()

# start the stopwatch
sw.start()
sktime.sleep(2)

# pause the stopwatch
sw.pause()
sktime.sleep(999)

# resume the stopwatch
sw.resume()
sktime.sleep(3)

# lap the stopwatch (about 5 seconds will be the result here)
sw.lap()
lap1 = sw.get_laptime(1)

sktime.sleep(2)

# stop the stopwatch
sw.stop()

# get results
total = sw.total_time
lap2 = sw.get_laptime(2)
```

### Timer for Performance Measurement

```python
# time execution with a decorator or context manager
timer = sktime.Timer()

@sktime.timethis(timer)
def do_work():
    # do some work
    pass

# when function finishes, time is logged to timer.
counter = 0
while counter < 100:
    do_work()
    counter += 1

last_time = timer.mostrecent
mean_time = timer.mean
median_time = timer.median
max_time = timer.longest
min_time = timer.shortest
std = timer.std
time36 = timer.get_time(36)
```

### Context Manager Usage

```python
# using context manager without and with Timer initialization

# without initalization, we only get most recent result
counter = 0
while counter < 100:
    with sktime.Timer() as timer:
        do_work()
    counter += 1

# will only get most recent result
result = timer.result

# with initialization, we get access to full statistics
_timer = sktime.Timer()

counter = 0
while counter < 100:
    with _timer.TimeThis() as timer:
        do_work()
    counter += 1

last_time = _timer.mostrecent
mean_time = _timer.mean
median_time = _timer.median
max_time = _timer.longest
min_time = _timer.shortest
std = _timer.std

if _timer.times >= 82:
    time82 = _timer.get_time(82)
```