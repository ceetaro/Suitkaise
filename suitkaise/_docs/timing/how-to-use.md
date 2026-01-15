# How to use the `timing` module

## `timing` saves you time.

- functionality far beyond basic `time.time()` calls
- utilities for both real-world time tracking and code performance timing
- automatically thread safe

## `@timethis`, the one-line auto-timer for functions and methods

The core feature of `timing`.

Automatically times a function/method every time it is called.

- 1 line, zero setup
- thread safe
- large set of statistics that you can access (more than `timeit`)

```python
from suitkaise import timing

@timing.timethis()
def my_function():
    # your code here
    pass

# run my_function many times
for i in range(100):
    my_function()

# get stats directly on the timer
mean = my_function.timer.mean
stdev = my_function.timer.stdev

# or get a frozen snapshot
snapshot = my_function.timer.get_stats()
```

You can also use the `@timethis` decorator with a given `Sktimer` object. (see more about the `Sktimer` class below)

```python
from suitkaise import timing

# time multiple functions with this one timer
t = timing.Sktimer()

class MyClass:
    @timing.timethis(timer=t)
    def my_function(self):
        # your code here
        pass

    @timing.timethis(timer=t)
    def my_function_2(self):
        # your code here
        pass

# a bunch of MyClass instances are created and their functions are called

# get stats on my_function and my_function_2 execution times
print(t.mean)
print(t.percentile(95))
```

You can stack `@timethis` decorators on the same function.

```python
from suitkaise import timing

t = timing.Sktimer()
another_t = timing.Sktimer()

@timing.timethis()
@timing.timethis(timer=t)
def my_function():
    # your code here
    pass

@timing.timethis()
@timing.timethis(timer=t)
@timing.timethis(timer=another_t)
def my_function_2():
    # your code here
    pass

# ...

# get stats on my_function and my_function_2 execution times
print(t.mean)

# get stats only on my_function
print(my_function.timer.mean)

# get stats only on my_function_2
print(my_function_2.timer.mean)
```

### `threshold` parameter

Allows you to only record times above a minimum threshold.

```python
from suitkaise import timing

# only record times >= 0.1 seconds
@timing.timethis(threshold=0.1)
def quick_function():
    # very fast operations won't pollute statistics
    pass
```

### `clear_global_timers()`

If you're using auto-created `@timethis()` timers, you can clear them to reset all accumulated stats.

```python
from suitkaise import timing

timing.clear_global_timers()
```

---

## `TimeThis` context manager

For the cases when the code you want to time is not a function, you can use the `TimeThis` context manager.

The context manager automatically starts the timer when the context is entered and stops it when the context is exited.

- cleaner than manually starting and stopping the timer
- error proof
- clear indication of what is being timed

```python
from suitkaise import timing

with timing.TimeThis() as timer:
    # your code here
    pass

# get the time that was just recorded (returns the Sktimer object)
print(timer.most_recent)
```

When using it like this, a new timer is created each time.

If you want to use the same timer every time that code is ran, you can create a timer and pass it to the context manager.

```python
from suitkaise import timing

t = timing.Sktimer()

# uses t every time
# lets you gather multiple measurements
with timing.TimeThis(timer=t):
    # your code here
    pass

print(t.mean)
```

### `threshold` parameter

Only record times above a minimum threshold:

```python
from suitkaise import timing

# only record times >= 0.5 seconds
with timing.TimeThis(threshold=0.5) as timer:
    quick_operation()  # if < 0.5s, won't be recorded

# useful for filtering out fast operations in loops
timer = timing.Sktimer()

for item in items:
    with timing.TimeThis(timer=timer, threshold=0.1):
        process(item)  # only slow items recorded

print(f"Slow operations: {timer.num_times}")
print(f"Average slow time: {timer.mean}")
```

---

## `Sktimer` class

Class that allows you to easily time parts of your code.

Powers the `@timethis` decorator and the `TimeThis` context manager, as well as `Skprocess` lifecycle method timers.

### `start()` and `stop()`

```python
from suitkaise import timing

timer = timing.Sktimer()

timer.start()
timing.sleep(60)
time_after_sleeping = timer.stop() # returns a float
```

When you call `start()`, the timer starts recording the time.

When you call `stop()`, the timer stops recording the time and returns the difference between the stop and start times as a `float`.

Note: calling `start()` while timing is already in progress will issue a `UserWarning`, and then create a nested timing frame.

#### Timing multiple times over
```python
from suitkaise import timing

timer = timing.Sktimer()

for i in range(100):

    timer.start()
    timing.sleep(60)
    timer.stop()

# access stats directly on the timer
mean = timer.mean
std = timer.stdev
p95 = timer.percentile(95)

# or get a frozen snapshot
snapshot = timer.get_stats()
```

### `discard()`

Stop timing but do NOT record the measurement. Useful when an error occurs, or for warm up runs.

```python
from suitkaise import timing

timer = timing.Sktimer()

timer.start()
try:
    result = something_that_might_fail()
    timer.stop()  # record successful timing
except Exception:
    timer.discard()  # stop but add to list of recorded times
```

### `lap()`

```python
from suitkaise import timing

timer = timing.Sktimer()
timer.start()

for i in range(100):

    my_function()

    # stops and instantly starts a new measurement
    timer.lap()

# stop the timer without recording a 101st measurement
timer.discard()

# 100 measurements recorded
print(timer.mean)
```

### `pause()` and `resume()`

```python
from suitkaise import timing

timer = timing.Sktimer()
timer.start()

# unzip and load a large file
current_file = unzip_and_load_file("Users/joe/Documents/large_file.zip")

# pause timer while user decides what to do next
timer.pause()

# time user takes to answer won't be counted because the timer is paused
user_choice = input(f"Process {current_file} now? (y/n): ")  

# resume once input is received
timer.resume()

# process the file
if user_choice.lower().strip() == 'y':
    process_loaded_file()

elapsed = timer.stop()  # records measurement in Sktimer and returns the elapsed time
print(f"Total processing time: {elapsed:.2f}s (excluding user input)")
```

### `add_time()`

Add a custom `float` time to the timer.

```python
from suitkaise import timing

timer = timing.Sktimer()
timer.add_time(10.0)
timer.add_time(15.0)

print(timer.mean)  # 12.5
```

### `reset()`

Reset the timer back to its initial state as if it was just created.


### `get_statistics()` / `get_stats()`

Get a frozen snapshot of all timer statistics. The snapshot won't change even if the timer continues recording.

```python
from suitkaise import timing

timer = timing.Sktimer()

# ... record some timings ...

# get a frozen snapshot
snapshot = timer.get_stats()  # or timer.get_statistics()

# access all the same properties
print(snapshot.mean)
print(snapshot.stdev)
print(snapshot.percentile(95))
```

### All `Sktimer` statistics

Properties
- `num_times` - number of times recorded
- `most_recent` - most recent time
- `most_recent_index` - index of most recent time
- `result` - most recent time (alias)
- `total_time` - sum of all times
- `total_time_paused` - total time spent paused
- `mean` - average of all times
- `median` - median of all times
- `min` / `fastest_time` - minimum time
- `max` / `slowest_time` - maximum time
- `stdev` - standard deviation
- `variance` - variance
- `slowest_index` - index of slowest time
- `fastest_index` - index of fastest time
- `original_start_time` - original start time of the timer

Methods
- `get_time(index)` - get time by standard 0-based index
- `percentile(percent)` - calculate any percentile (0-100)

```python
# to get the real world time passed since the timer started, you can use this
real_world_time = timing.time() - timer.original_start_time
```

---

## `time()`

`time()` uses `time.time()`. 

It is simply here so you don't have to import `time` as well as `timing`.

```python
from suitkaise import timing

current_timestamp = timing.time()
```

---

## `sleep()`

`sleep()` is built off of `time.sleep()`, but it can also return the current time after sleeping in the same line.

Arguments
- `seconds` - Number of seconds to sleep (can be fractional)

Returns
- current time after sleeping as a `float`

without `timing` - *3 lines*
```python
import time # 1

time.sleep(1) # 2
current_timestamp = time.time() # 3
```

with `timing` - *2 lines*
```python
from suitkaise import timing # 1

current_timestamp = timing.sleep(1) # 2
```

You can also use it without a variable assignment.

```python
timing.sleep(1)
```

### Async Support

`sleep()` supports `.asynced()` for async code, by using `asyncio.sleep()`.

```python
from suitkaise import timing

# .asynced() returns a coroutine
end_time = await timing.sleep.asynced()(2)
```

---

## `elapsed()`

Easy way to calculate elapsed time.

Arguments
- `time1` - First timestamp
- `time2` - Second timestamp (defaults to current time if `None`)

Returns
- elapsed time as a `float`

without `timing` - *8 lines*
```python
import time # 1
from math import fabs # 2

start_time = time.time() # 3
# ... do work ...
end_time = time.time() # 4

try: # 5

    # have to use absolute value to avoid negative values when order is wrong
    elapsed = fabs(end_time - start_time) # 6

except TypeError: # 7
    print("Error: start_time and end_time must be of type float") # 8
```

with `timing` - *3-4 lines*

    - if giving two times, order doesn't matter
    - if giving one time, current time is used as end time automatically
    - error handling for type mismatches

```python
from suitkaise import timing # 1

start_time = timing.time() # 2

# ... do work ...

# current time is end time automatically
time_to_complete = timing.elapsed(start_time) # 3
```

```python
# or give 2 times
from suitkaise import timing # 1

start_time = timing.time() # 2
end_time = timing.time() + 60 # 3

time_to_complete = timing.elapsed(start_time, end_time) # 4
```

---
