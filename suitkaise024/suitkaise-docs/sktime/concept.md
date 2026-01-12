# How to use the `sktime` module

## `sktime` saves you time.

- Functionality far beyond basic `time.time()` calls
- Utilities for both real-world time tracking and code performance timing
- Automatically thread safe

## `@timethis`, the one-line function auto-timer

The core feature of `sktime`.

Automatically times a function every time it is called.

- 1 line, zero setup
- thread safe
- large set of statistics that you can access

```python
from suitkaise import sktime

@sktime.timethis()
def my_function():
    # Your code here
    pass

# run my_function many times
for i in range(100):
    my_function()

# get stats via the organized stats namespace
mean = my_function.timer.mean
stdev = my_function.timer.stdev

# or get a frozen snapshot
snapshot = my_function.timer.get_stats()
```

You can also use the `@timethis` decorator with a given `Timer` object.

```python
from suitkaise import sktime

# time multiple functions with this one timer
t = sktime.Timer()

def MyClass:
    @sktime.timethis(timer=t)
    def my_function(self):
        # Your code here
        pass

    @sktime.timethis(timer=t)
    def my_function_2(self):
        # Your code here
        pass

# a bunch of MyClass instances are created and their functions are called

# get stats on my_function and my_function_2 execution times
print(t.mean)
print(t.percentile(95))
```

You can stack `@timethis` decorators on the same function.

```python
from suitkaise import sktime

t = sktime.Timer()

@sktime.timethis()
@sktime.timethis(timer=t)
def my_function():
    # Your code here
    pass

@sktime.timethis()
@sktime.timethis(timer=t)
def my_function_2():
    # Your code here
    pass

# ...

# get stats on my_function and my_function_2 execution times
print(t.mean)

# get stats only on my_function
print(my_function.timer.mean)

# get stats only on my_function_2
print(my_function_2.timer.mean)
```
---

## `Timer` class

Class that allows you to easily time parts of your code.

Powers the `@timethis` decorator and the `TimeThis` context manager (below)

### `start()` and `stop()`

```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()
sktime.sleep(60)
time_after_sleeping = timer.stop() # returns a float
```

When you call `start()`, the timer starts recording the time.

When you call `stop()`, the timer stops recording the time and returns the difference between the stop and start times as a float.

Note: calling `start()` while timing is already in progress will issue a `UserWarning` (it creates a nested timing frame).

Timing multiple times over:
```python
from suitkaise import sktime

timer = sktime.Timer()

for i in range(100):

    timer.start()
    sktime.sleep(60)
    timer.stop()

# access stats through the stats namespace
mean = timer.mean
std = timer.stdev
p95 = timer.percentile(95)

# or get a frozen snapshot
snapshot = timer.get_stats()
```

### `discard()`

Stop timing but do NOT record the measurement. Useful when an error occurs or for warm-up runs.

```python
from suitkaise import sktime

timer = sktime.Timer()

timer.start()
try:
    result = risky_operation()
    timer.stop()  # Record successful timing
except Exception:
    timer.discard()  # Stop but don't pollute stats with failed run
```

### `lap()`

```python
from suitkaise import sktime

timer = sktime.Timer()
timer.start()

for i in range(100):

    my_function()

    # stops and instantly starts a new measurement
    timer.lap()

# 100 measurements recorded
print(timer.mean)
```

### `pause()` and `resume()`

```python
from suitkaise import sktime

timer = sktime.Timer()
timer.start()

# Unzip and load a large file
current_file = unzip_and_load_file("Users/joe/Documents/large_file.zip")

# Pause timer while user decides what to do next
timer.pause()

# time user takes to answer won't be counted - we are paused!
user_choice = input(f"Process {current_file} now? (y/n): ")  

# Resume once input is received
timer.resume()

# Process the file
if user_choice.lower().strip() == 'y':
    process_loaded_file()

elapsed = timer.stop()  # Records measurement in statistics
print(f"Total processing time: {elapsed:.2f}s (excluding user input)")
```

### `add_time()`

Add a float time to the timer.

```python
from suitkaise import sktime

timer = sktime.Timer()
timer.add_time(10.0)
timer.add_time(15.0)

print(timer.mean)  # 12.5
```

### `reset()`

Reset the timer back to its initial state as if it was just created.

### All `Timer` statistics

All statistics are accessed through the organized `stats` namespace:

Properties:
- `timer.num_times` - Number of times recorded
- `timer.most_recent` - Most recent time
- `timer.most_recent_index` - Index of most recent time
- `timer.result` - Most recent time (alias)
- `timer.total_time` - Sum of all times
- `timer.total_time_paused` - Total time spent paused
- `timer.mean` - Average of all times
- `timer.median` - Median of all times
- `timer.min` / `timer.fastest_time` - Minimum time
- `timer.max` / `timer.slowest_time` - Maximum time
- `timer.stdev` - Standard deviation
- `timer.variance` - Variance
- `timer.slowest_index` - Index of slowest time
- `timer.fastest_index` - Index of fastest time
- `timer.original_start_time` - Original start time of the timer

Methods:
- `timer.get_time(index)` - Get time by standard 0-based index
- `timer.percentile(percent)` - Calculate any percentile (0-100)

```python
# to get the real world time passed since the timer started, you can use:

real_world_time = sktime.time() - timer.original_start_time
```

### `get_statistics()` / `get_stats()`

Get a frozen snapshot of all timer statistics. The snapshot won't change even if the timer continues recording.

```python
from suitkaise import sktime

timer = sktime.Timer()

# ... record some timings ...

# get a frozen snapshot
snapshot = timer.get_stats()  # or timer.get_statistics()

# access all the same properties
print(snapshot.mean)
print(snapshot.stdev)
print(snapshot.percentile(95))
```

---

## `TimeThis` context manager

For the cases when the code you want to time is not a function, you can use the `TimeThis` context manager.

The context manager automatically starts the timer when the context is entered and stops it when the context is exited.

- cleaner than manually starting and stopping the timer
- error proof
- clear indication of what is being timed

```python
from suitkaise import sktime

with sktime.TimeThis() as timer:
    # Your code here
    pass

# get the time that was just recorded (returns the Timer object)
print(timer.most_recent)
```

When using it like this, a new timer is created each time.

If you want to use the same timer every time that code is ran, you can create a timer and pass it to the context manager.

```python
from suitkaise import sktime

timer = sktime.Timer()

# uses your "timer" every time
# lets you gather multiple measurements
with sktime.TimeThis(timer=timer):
    # Your code here
    pass

print(timer.mean)
```
---

## `time()`

`time()` uses `time.time()`. 

It is simply here so you don't have to import `time` as well as `sktime`.

```python
from suitkaise import sktime

current_timestamp = sktime.time()
```

---

## `sleep()`

`sleep()` is built off of `time.sleep()`, but it can optionally return the current time after sleeping in the same line.

Arguments:
- `seconds`: Number of seconds to sleep (can be fractional)

Returns:
- Current time after sleeping as a float

without `sktime`: ***3 lines***
```python
import time # 1

time.sleep(1) # 2

current_timestamp = time.time() # 3
```

with `sktime`: ***2 lines***
```python
from suitkaise import sktime # 1

current_timestamp = sktime.sleep(1) # 2
```

---

## `elapsed()`

Easy way to calculate elapsed time.

Arguments:
- `time1`: First timestamp
- `time2`: Second timestamp (defaults to current time if `None`)

Returns:
- Elapsed time as a float

without `sktime`: ***8 lines***
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

with `sktime`: ***3-4 lines***

    - if giving two times, order doesn't matter
    - if giving one time, current time is used as end time automatically
    - error handling for type mismatches

```python
from suitkaise import sktime # 1

start_time = sktime.time() # 2

# ... do work ...

# current time is end time automatically
time_to_complete = sktime.elapsed(start_time) # 3
```

```python
# or give 2 times
from suitkaise import sktime # 1

start_time = sktime.time() # 2
end_time = sktime.time() + 60 # 3

time_to_complete = sktime.elapsed(start_time, end_time) # 4
```

---

## `Yawn` class

Sleep controller that sleeps after a specified number of "yawns".

Unlike `Circuit` (which breaks and stops), `Yawn` sleeps and continues. The counter auto-resets after each sleep.

Arguments:
- `sleep_duration`: How long to sleep when threshold is reached (`float`)
- `yawn_threshold`: Number of yawns before sleeping (`int`)
- `log_sleep`: Whether to print when sleep occurs (`bool`)

```python
from suitkaise import sktime

# create the controller
y = sktime.Yawn(sleep_duration=3, yawn_threshold=5)


while something:
    if something_went_wrong():
        y.yawn()  # After 5 yawns, sleeps for 3 seconds, then auto-resets
    else:
        do_work() # run your program code

```
If something goes wrong 5 times, the program will sleep for 3 seconds, then continue (counter resets).

---
