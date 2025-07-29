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