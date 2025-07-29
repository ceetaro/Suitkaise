# SKTime Examples

## Basic Time Operations

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

## Yawn Class - Conditional Sleep

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

## Stopwatch Operations

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

## Timer for Performance Measurement

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

## Context Manager Usage

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