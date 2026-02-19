/*

synced from suitkaise-docs/timing/why.md

*/

rows = 2
columns = 1

# 1.1

title = "Why you should use `timing`"

# 1.2

text = "
## TLDR

- **1-line setup** - `<suitkaise-api>@timethis()</suitkaise-api>` or `<suitkaise-api>with TimeThis()</suitkaise-api>`, done
- **Deep statistics** - `mean`, `median`, `stdev`, `variance`, `percentiles` (way better than `timeit`)
- **Pause/resume** - exclude user input or delays from measurements
- **Thread-safe** - time concurrent operations without race conditions
- **Discard bad runs** - throw away failed attempts without polluting stats
- **Rolling windows** - bound memory in long-running processes
- **Threshold filtering** - only record slow operations
- **Frozen snapshots** - capture stats at a point in time
- **Native async support** - `<suitkaise-api>.asynced()</suitkaise-api>` for async contexts

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

**Result:**
- 100% coverage of your code (you can time anything and everything)
- 1-line setup
- Thread safety
- Deep statistical analysis, much better than `timeit`
- Native async support

## `<suitkaise-api>@timethis</suitkaise-api>` decorator

**Without it** - *7 lines*

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

**With `<suitkaise-api>timing</suitkaise-api>`** - *2 lines*

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>timethis</suitkaise-api> # 1

<suitkaise-api>@timethis()</suitkaise-api> # 2
def my_function():

    # whatever the function actually does

    return result

result = my_function()
```

- You can just slap `<suitkaise-api>@timethis()</suitkaise-api>` on any function you need to time
- Stored as a property of the function
- Don't have to edit a function to time it

## `<suitkaise-api>TimeThis</suitkaise-api>` context manager

This covers everything that `<suitkaise-api>@timethis</suitkaise-api>` doesn't in a context manager pattern.

**Without it** - *6 lines*

```python
import time # 1

times = [] # 2

start_time = time.time() # 3

# whatever you need to time

end_time = time.time() # 4

time_taken = end_time - start_time # 5
times.append(time_taken) # 6
```

**With `<suitkaise-api>timing</suitkaise-api>`** - *2 lines*

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>TimeThis</suitkaise-api> # 1

with <suitkaise-api>TimeThis(</suitkaise-api>) as timer: # 2

    # whatever you need to time

time_taken = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api> # 3
```

- No manual tracking
- Context manager makes it clear what is being timed
- Error-proof
- Clear indication of what is being timed

## Deep Statistical Analysis

`timeit` gives you a single number. That's not enough.

You need mean, median, standard deviation, variance, and percentiles to actually understand performance.

**Without it** - *10+ lines*
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

**With `<suitkaise-api>timing</suitkaise-api>`** - *2 lines*
```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api> # 1

for i in range(100):
    with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis(</suitkaise-api>) as timer: # 2
        do_work()

# all statistics automatically available, no extra work
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>median</suitkaise-api>
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>variance</suitkaise-api>
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>min</suitkaise-api>
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>max</suitkaise-api>
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95)
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(99)
```

One object. Every stat you could want. No manual calculation.

## Pause and Resume

You're timing a database query, but you need to ask the user something in the middle.

**Without it**
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

**With `<suitkaise-api>timing</suitkaise-api>`**
```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

results = database.query("SELECT * FROM users")

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>pause</suitkaise-api>()
user_input = input("Export to CSV? (y/n): ")
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>resume</suitkaise-api>()

if user_input == 'y':
    export_to_csv(results)

elapsed = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()  # user input time excluded
```

`<suitkaise-api>pause</suitkaise-api>()` and `<suitkaise-api>resume</suitkaise-api>()`. That's it. The timer handles the math.

## Discard Bad Measurements

Sometimes things fail. You don't want failed attempts polluting your statistics.

**Without it**
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

**With `<suitkaise-api>timing</suitkaise-api>`**
```python
timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

for i in range(100):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    try:
        result = unreliable_operation()
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()  # success - record it
    except Exception:
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()  # failure - forget it

# statistics only reflect successful operations
```

`<suitkaise-api>discard</suitkaise-api>()` cleanly abandons the measurement. Your stats stay clean.

## Thread Safety

Multiple threads timing the same thing? No problem.

```python
timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)  # thread-safe by default

def worker():
    for _ in range(100):
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        do_work()
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

# spawn 4 threads...
# stats just work
print(<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
```

`<suitkaise-api>Sktimer</suitkaise-api>` is thread-safe out of the box. Each thread gets its own session. Results aggregate automatically.

## Lap Timing

Timing items in a loop? `<suitkaise-api>lap</suitkaise-api>()` is stop + start in one call.

**Without it**
```python
times = []
start = time.perf_counter()

for item in items:
    process(item)
    now = time.perf_counter()
    times.append(now - start)
    start = now  # easy to forget this
```

**With `<suitkaise-api>timing</suitkaise-api>`**
```python
timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

for item in items:
    process(item)
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>lap</suitkaise-api>()  # records time, continues timing

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()  # clean up the last pending measurement
```

## Rolling Windows

Long-running server? Can't keep every measurement forever.

**Without it**
```python
from collections import deque

MAX_TIMES = 1000
times = deque(maxlen=MAX_TIMES)
lock = threading.Lock()

# now manually manage this everywhere
```

**With `<suitkaise-api>timing</suitkaise-api>`**
```python
timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>max_times=1000)

# that's it - automatically keeps only the last 1000 measurements
```
One parameter. Memory bound. Statistics always reflect recent performance.

## Threshold Filtering

Only care about slow operations? Filter out the fast ones automatically.

```python
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(threshold=0.1)
def handle_request():
    # only records times >= 0.1 seconds
    ...
```

Fast operations are silently discarded. Your statistics focus on what matters.

## Stacked Decorators

Want both combined stats AND per-function stats?

```python
perf_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()             # per-function timer
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(perf_timer)   # shared timer
def db_read():
    ...

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()             # per-function timer
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(perf_timer)   # shared timer
def db_write():
    ...

# combined stats
print(perf_timer.mean)

# individual stats
print(db_read.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
print(db_write.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
```

Stack decorators. Each records independently. Zero manual list management.

## Frozen Snapshots

Need to capture statistics at a point in time?

```python
snapshot = <suitkaise-api>timer</suitkaise-api>.get_statistics()

# timer continues recording...
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
do_more_work()
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

# snapshot still has the old values
print(snapshot.mean)  # unchanged
```

`get_statistics()` returns an immutable `TimerStats` object. Perfect for logging or reporting.

## `<suitkaise-api>elapsed</suitkaise-api>()` Just Works

Order doesn't matter. Always returns positive.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

start = <suitkaise-api>timing</suitkaise-api>.time()
<suitkaise-api>timing</suitkaise-api>.sleep(1)
end = <suitkaise-api>timing</suitkaise-api>.time()

<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start, end)  # 1.0
<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(end, start)  # 1.0 (same!)
<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start)       # uses current time
```

No more `abs()` everywhere. No more "which one was first?" bugs.

## Async Support

```python
# sync
<suitkaise-api>timing</suitkaise-api>.sleep(1)

# async
await <suitkaise-api>timing</suitkaise-api>.sleep.asynced()(1)
```

Same API. Just add `<suitkaise-api>.asynced()</suitkaise-api>` when you need it.

This works with `<suitkaise-api>TimeThis</suitkaise-api>` too:

```python
async def fetch_all():
    async with <suitkaise-api>TimeThis(</suitkaise-api>) as timer:
        await fetch_users()
        await fetch_orders()
    
    print(f"Total: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")
```

And with `<suitkaise-api>@timethis</suitkaise-api>`:

```python
<suitkaise-api>@timethis</suitkaise-api>()
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        return await session.get("https://api.example.com")

await fetch_data()
print(fetch_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>)
```

Sync and async, same interface. No separate implementations needed.

## Works with `<suitkaise-api>Share</suitkaise-api>` — timing across processes

`<suitkaise-api>Sktimer</suitkaise-api>` works natively inside `<suitkaise-api>Share</suitkaise-api>`. This means you can aggregate timing data across multiple processes without any extra code.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>

<suitkaise-api>share</suitkaise-api> = <suitkaise-api>Share(</suitkaise-api>)
<suitkaise-api>share.timer</suitkaise-api> = <suitkaise-api>Sktimer(</suitkaise-api>)

class TimedWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, share, data):
        self.share = share
        self.data = data
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.<suitkaise-api>share.timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        process(self.data)
        self.<suitkaise-api>share.timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

<suitkaise-api>pool</suitkaise-api> = <suitkaise-api>Pool(</suitkaise-api>workers=4)
<suitkaise-api>pool.star()</suitkaise-api>.<suitkaise-api>map</suitkaise-api>(TimedWorker, [(share, item) for item in work_items])

# all 4 processes contributed to the same timer
print(f"Mean across all workers: {<suitkaise-api>share.timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"p95 across all workers: {<suitkaise-api>share.timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95):.3f}s")
```

Every process writes to the same timer. Stats aggregate automatically. No manual list management, no locks, no merging results.

`<suitkaise-api>Skprocess</suitkaise-api>` also has built-in timers for every lifecycle method -- access them via `<suitkaise-api>process.__run__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>`, `<suitkaise-api>process.__prerun__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>`, etc. These are `<suitkaise-api>Sktimer</suitkaise-api>` objects with all the same statistical depth.
"
