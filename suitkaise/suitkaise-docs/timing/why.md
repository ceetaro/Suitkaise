# Why you should use `timing`

## TLDR

- **1-line setup** - `@timethis()` or `with TimeThis()`, done
- **Deep statistics** - mean, median, stdev, variance, percentiles (way better than `timeit`)
- **Pause/resume** - exclude user input or delays from measurements
- **Thread-safe** - time concurrent operations without race conditions
- **Discard bad runs** - throw away failed attempts without polluting stats
- **Rolling windows** - bound memory in long-running processes
- **Threshold filtering** - only record slow operations
- **Frozen snapshots** - capture stats at a point in time
- **Native async support** - `.asynced()` for async contexts

---

I was so tired of using `time.time()`, running some code, calling `time.time()` again, and then subtracting the difference to get how long it took.

```python
start_time = time.time()

# some code

end_time = time.time()

time_taken = end_time - start_time
```

And it gets even more annoying when you need to time multiple things.

```python
start_time = time.time()
# some code
end_time = time.time()

time_taken = end_time - start_time

# then ...

start_time2 = time.time()
# some code
end_time2 = time.time()

time_taken2 = end_time2 - start_time2
# ...
```

Or when I wanted to time a specific function, I had to return the resulting time with it as a tuple.

```python
def my_function():
    start_time = time.time()

    # whatever the function actually does

    end_time = time.time()

    return function_result, end_time - start_time

# later...
result, time_taken = my_function()
```

Then I had to manually add the times to a list.

```python
times1.append(time_taken)
```

And then calculate stats.

```python
import statistics

mean = statistics.mean(times1)
median = statistics.median(times1)
```

And you have to do this for every function you need to time.

```python
times2.append(time_taken)

times3.append(time_taken)

# and so on...
```

I wanted a super quick way to do this, that also made sense.

Result:
- 100% coverage of your code (you can time anything and everything)
- 1-line setup
- thread safety
- deep statistical analysis, much better than `timeit`
- native async support

## `@timethis` decorator

Without `timing` - *7 lines*
(start of dropdown)
```python
import time # 1
from typing import Any

times_my_function = [] # 2

def my_function() -> tuple[Any, float]:
    start_time = time.time() # 3

    # whatever the function actually does

    end_time = time.time() # 4

    return function_result, end_time - start_time # 5

result, time_taken = my_function() # 6

times_my_function.append(time_taken) # 7
```
(end of dropdown)

With `timing` - *2 lines*

```python
from suitkaise.timing import timethis # 1

@timethis() # 2
def my_function():

    # whatever the function actually does

    return result

result = my_function()
```

- you can just slap `@timethis()` on any function you need to time
- stored as a property of the function
- don't have to edit a function to time it

## `TimeThis` context manager

This covers everything that `@timethis` doesn't in a context manager pattern.

Without `timing` - *6 lines*
(start of dropdown)
```python
import time # 1

times = [] # 2

start_time = time.time() # 3

# whatever you need to time

end_time = time.time() # 4

time_taken = end_time - start_time # 5
times.append(time_taken) # 6
```
(end of dropdown)

With `timing` - *2 lines*

```python
from suitkaise.timing import TimeThis # 1

with TimeThis() as timer: # 2

    # whatever you need to time

time_taken = timer.most_recent # 3
```

- no manual tracking
- context manager makes it clear what is being timed
- error proof
- clear indication of what is being timed

## Deep Statistical Analysis

`timeit` gives you a single number. That's not enough.

You need mean, median, standard deviation, variance, and percentiles to actually understand performance.

Without `timing` - *10+ lines*
```python
import time # 1
import statistics # 2

times = [] # 3

for i in range(100):
    start = time.perf_counter() # 4
    do_work()
    end = time.perf_counter() # 5
    times.append(end - start) # 6

mean = statistics.mean(times) # 7
median = statistics.median(times) # 8
stdev = statistics.stdev(times) # 9

# percentiles? have fun
sorted_times = sorted(times) # 10
p95 = sorted_times[int(0.95 * len(sorted_times))] # 11

# and more stats calculations...
```

With `timing` - *2 lines*
```python
from suitkaise import timing # 1

for i in range(100):
    with timing.TimeThis() as timer: # 2
        do_work()

# all statistics automatically available, no extra work
timer.mean
timer.median
timer.stdev
timer.variance
timer.min
timer.max
timer.percentile(95)
timer.percentile(99)
```

One object. Every stat you could want. No manual calculation.

## Pause and Resume

You're timing a database query, but you need to ask the user something in the middle.

Without `timing`
```python
import time

start = time.perf_counter()

results = database.query("SELECT * FROM users")

# pause timing... manually?
pause_start = time.perf_counter()
user_input = input("Export to CSV? (y/n): ")
pause_end = time.perf_counter()
pause_duration = pause_end - pause_start

if user_input == 'y':
    export_to_csv(results)

end = time.perf_counter()

# manually subtract pause time
elapsed = (end - start) - pause_duration
```

With `timing`
```python
from suitkaise import timing

timer = timing.Sktimer()
timer.start()

results = database.query("SELECT * FROM users")

timer.pause()
user_input = input("Export to CSV? (y/n): ")
timer.resume()

if user_input == 'y':
    export_to_csv(results)

elapsed = timer.stop()  # user input time excluded
```

`pause()` and `resume()`. That's it. The timer handles the math.

## Discard Bad Measurements

Sometimes things fail. You don't want failed attempts polluting your statistics.

Without `timing`
```python
times = []

for i in range(100):
    start = time.perf_counter()
    try:
        result = unreliable_operation()
        end = time.perf_counter()
        times.append(end - start)
    except Exception:
        pass  # awkward - start was recorded, now what?
```

With `timing`
```python
timer = timing.Sktimer()

for i in range(100):
    timer.start()
    try:
        result = unreliable_operation()
        timer.stop()  # success - record it
    except Exception:
        timer.discard()  # failure - forget it

# statistics only reflect successful operations
```

`discard()` cleanly abandons the measurement. Your stats stay clean.

## Thread Safety

Multiple threads timing the same thing? No problem.

```python
timer = timing.Sktimer()  # thread-safe by default

def worker():
    for _ in range(100):
        timer.start()
        do_work()
        timer.stop()

# spawn 4 threads...
# stats just work
print(timer.mean)
```

`Sktimer` is thread-safe out of the box. Each thread gets its own session. Results aggregate automatically.

## Lap Timing

Timing items in a loop? `lap()` is stop + start in one call.

Without `timing`
```python
times = []
start = time.perf_counter()

for item in items:
    process(item)
    now = time.perf_counter()
    times.append(now - start)
    start = now  # easy to forget this
```

With `timing`
```python
timer = timing.Sktimer()
timer.start()

for item in items:
    process(item)
    timer.lap()  # records time, continues timing

timer.discard()  # clean up the last pending measurement
```

## Rolling Windows

Long-running server? Can't keep every measurement forever.

Without `timing`
```python
from collections import deque

MAX_TIMES = 1000
times = deque(maxlen=MAX_TIMES)
lock = threading.Lock()

# now manually manage this everywhere
```

With `timing`
```python
timer = timing.Sktimer(max_times=1000)

# that's it - automatically keeps only the last 1000 measurements
```
One parameter. Memory bound. Statistics always reflect recent performance.

## Threshold Filtering

Only care about slow operations? Filter out the fast ones automatically.

```python
@timing.timethis(threshold=0.1)
def handle_request():
    # only records times >= 0.1 seconds
    ...
```

Fast operations are silently discarded. Your statistics focus on what matters.

## Stacked Decorators

Want both combined stats AND per-function stats?

```python
perf_timer = timing.Sktimer()

@timing.timethis()             # per-function timer
@timing.timethis(perf_timer)   # shared timer
def db_read():
    ...

@timing.timethis()             # per-function timer
@timing.timethis(perf_timer)   # shared timer
def db_write():
    ...

# combined stats
print(perf_timer.mean)

# individual stats
print(db_read.timer.mean)
print(db_write.timer.mean)
```

Stack decorators. Each records independently. Zero manual list management.

## Frozen Snapshots

Need to capture statistics at a point in time?

```python
snapshot = timer.get_statistics()

# timer continues recording...
timer.start()
do_more_work()
timer.stop()

# snapshot still has the old values
print(snapshot.mean)  # unchanged
```

`get_statistics()` returns an immutable `TimerStats` object. Perfect for logging or reporting.

## `elapsed()` Just Works

Order doesn't matter. Always returns positive.

```python
from suitkaise import timing

start = timing.time()
timing.sleep(1)
end = timing.time()

timing.elapsed(start, end)  # 1.0
timing.elapsed(end, start)  # 1.0 (same!)
timing.elapsed(start)       # uses current time
```

No more `abs()` everywhere. No more "which one was first?" bugs.

## Async Support

```python
# sync
timing.sleep(1)

# async
await timing.sleep.asynced()(1)
```

Same API. Just add `.asynced()` when you need it.

This works with `TimeThis` too:

```python
async def fetch_all():
    async with TimeThis() as timer:
        await fetch_users()
        await fetch_orders()
    
    print(f"Total: {timer.most_recent:.3f}s")
```

And with `@timethis`:

```python
@timethis()
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        return await session.get("https://api.example.com")

await fetch_data()
print(fetch_data.timer.mean)
```

Sync and async, same interface. No separate implementations needed.

## Works with `Share` — timing across processes

`Sktimer` works natively inside `Share`. This means you can aggregate timing data across multiple processes without any extra code.

```python
from suitkaise.processing import Share, Pool, Skprocess
from suitkaise.timing import Sktimer

share = Share()
share.timer = Sktimer()

class TimedWorker(Skprocess):
    def __init__(self, share, data):
        self.share = share
        self.data = data
        self.process_config.runs = 1

    def __run__(self):
        self.share.timer.start()
        process(self.data)
        self.share.timer.stop()

pool = Pool(workers=4)
pool.star().map(TimedWorker, [(share, item) for item in work_items])

# all 4 processes contributed to the same timer
print(f"Mean across all workers: {share.timer.mean:.3f}s")
print(f"p95 across all workers: {share.timer.percentile(95):.3f}s")
```

Every process writes to the same timer. Stats aggregate automatically. No manual list management, no locks, no merging results.

`Skprocess` also has built-in timers for every lifecycle method -- access them via `process.__run__.timer`, `process.__prerun__.timer`, etc. These are `Sktimer` objects with all the same statistical depth.