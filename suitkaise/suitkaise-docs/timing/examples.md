# `<suitkaise-api>timing</suitkaise-api>` Examples

## Basic Examples

### Simple Timing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# Basic start/stop <suitkaise-api>timing</suitkaise-api>
# 
# The simplest way to time something: start, do work, <suitkaise-api>stop</suitkaise-api>.
# The <suitkaise-api>elapsed</suitkaise-api> time is returned by <suitkaise-api>stop</suitkaise-api>() and also stored in the <suitkaise-api>timer</suitkaise-api>.
# ──────────────────────────────────────────────────────────────────────────────

# create a new timer instance
# - no arguments needed for basic usage
timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

# start the timer
# - records current high-resolution timestamp
# - uses perf_counter() internally for accurate measurements
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

# do some work
# - this is what we're measuring
# - could be any code: function calls, loops, I/O operations
for i in range(1000000):
    _ = i * i

# stop the timer and get <suitkaise-api>elapsed</suitkaise-api> time
# - returns <suitkaise-api>elapsed</suitkaise-api> time in seconds as a float
# - also stores the measurement in <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>times</suitkaise-api> for statistics
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

# print the <suitkaise-api>result</suitkaise-api>
# - :.3f formats to 3 decimal places (millisecond precision)
print(f"Elapsed: {<suitkaise-api>elapsed</suitkaise-api>:.3f}s")

# you can also access the last measurement via property
# - most_recent is an alias for the last recorded time
# - <suitkaise-api>result</suitkaise-api> is also an alias for most_recent
print(f"Same value: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")
```

### Using elapsed()

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# Using <suitkaise-api>elapsed</suitkaise-api>() for simple time differences
#
# <suitkaise-api>elapsed</suitkaise-api>() calculates the difference between two timestamps.
# If you only provide one timestamp, it uses current time as the second.
# Order doesn't matter - always returns positive value.
# ──────────────────────────────────────────────────────────────────────────────

# get the current Unix timestamp
# - equivalent to time.time()
# - returns seconds since epoch as a float
start = <suitkaise-api>timing</suitkaise-api>.time()

# do real work
import hashlib
payload = b"elapsed_example"
for _ in range(20000):
    payload = hashlib.sha256(payload).digest()

# calculate <suitkaise-api>elapsed</suitkaise-api> time with one argument
# - uses current time as the second timestamp
# - same as: <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start, <suitkaise-api>timing</suitkaise-api>.time())
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start)
print(f"Elapsed: {<suitkaise-api>elapsed</suitkaise-api>:.3f}s")  # ~0.500s

# calculate <suitkaise-api>elapsed</suitkaise-api> time with two arguments
# - explicitly provide both timestamps
end = <suitkaise-api>timing</suitkaise-api>.time()
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start, end)
print(f"Elapsed: {<suitkaise-api>elapsed</suitkaise-api>:.3f}s")

# order doesn't matter - always returns positive value
# - internally uses abs() so you can't get negative results
# - useful when you're not sure which timestamp is earlier
elapsed_reversed = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(end, start)
print(f"Reversed: {elapsed_reversed:.3f}s")  # same value
```

### Multiple Measurements

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib

# ──────────────────────────────────────────────────────────────────────────────
# Collecting multiple measurements for statistics
#
# Run the same operation multiple times and collect <suitkaise-api>timing</suitkaise-api> data.
# <suitkaise-api>Sktimer</suitkaise-api> accumulates all measurements and provides statistical analysis.
# ──────────────────────────────────────────────────────────────────────────────

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

# <suitkaise-api>run</suitkaise-api> 100 iterations of the same operation
# - each iteration is timed independently
# - all times are stored in <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>times</suitkaise-api> list
for i in range(100):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    
    # variable work based on input size
    payload = b"x" * (2000 + (i % 5) * 500)
    hashlib.sha256(payload).hexdigest()
    
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

# access statistics
# - num_times: how many measurements we collected
# - mean: average of all measurements
# - median: middle value when sorted (less affected by outliers)
# - stdev: standard deviation (measure of variance)
# - min/max: fastest and slowest measurements
print(f"Measurements: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Mean: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"Median: {<suitkaise-api>timer</suitkaise-api>.median:.3f}s")
print(f"Std Dev: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>:.3f}s")
print(f"Min: {<suitkaise-api>timer</suitkaise-api>.min:.3f}s")
print(f"Max: {<suitkaise-api>timer</suitkaise-api>.max:.3f}s")

# calculate percentiles
# - <suitkaise-api>percentile</suitkaise-api>(95) means 95% of measurements are at or below this value
# - useful for understanding "worst case" performance
p95 = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95)
p99 = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(99)
print(f"95th percentile: {p95:.3f}s")
print(f"99th percentile: {p99:.3f}s")
```

### Using lap()

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# Using <suitkaise-api>lap</suitkaise-api>() for continuous measurements
#
# <suitkaise-api>lap</suitkaise-api>() records the current measurement and immediately starts the next one.
# It's like calling <suitkaise-api>stop</suitkaise-api>() + <suitkaise-api>start</suitkaise-api>() in one operation.
# Useful for <suitkaise-api>timing</suitkaise-api> iterations without the overhead of separate stop/<suitkaise-api>start</suitkaise-api>.
# ──────────────────────────────────────────────────────────────────────────────

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

# start <suitkaise-api>timing</suitkaise-api>
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

# process multiple items, recording time for each
items = ["item1", "item2", "item3", "item4", "item5"]

for item in items:
    # real work per item
    import hashlib
    payload = (item * 1000).encode()
    hashlib.sha256(payload).hexdigest()
    
    # record lap time and continue
    # - records time since last <suitkaise-api>lap</suitkaise-api>() or <suitkaise-api>start</suitkaise-api>()
    # - immediately begins new measurement
    # - returns the <suitkaise-api>elapsed</suitkaise-api> time for this lap
    lap_time = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>lap</suitkaise-api>()
    print(f"Processed {item}: {lap_time:.3f}s")

# after the loop, there's still an active measurement running
# - we need to either <suitkaise-api>stop</suitkaise-api>() or <suitkaise-api>discard</suitkaise-api>() it
# - <suitkaise-api>discard</suitkaise-api>() stops <suitkaise-api>timing</suitkaise-api> without recording (since we already recorded with <suitkaise-api>lap</suitkaise-api>())
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()

# we have 5 measurements (one per lap)
print(f"\nTotal measurements: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Total time: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>:.3f}s")
print(f"Average per item: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
```

### Pause and Resume

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# Pausing <suitkaise-api>timing</suitkaise-api> during user interaction
#
# Sometimes you want to exclude certain time from measurements.
# <suitkaise-api>pause</suitkaise-api>()/<suitkaise-api>resume</suitkaise-api>() let you temporarily stop the clock without ending the session.
# Useful for excluding user input, network waits, or other external delays.
# ──────────────────────────────────────────────────────────────────────────────

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

# phase 1: initial <suitkaise-api>processing</suitkaise-api> (timed)
print("Phase 1: Processing data...")
import hashlib
data = b"phase1"
for _ in range(20000):
    data = hashlib.sha256(data).digest()

# pause <suitkaise-api>timing</suitkaise-api> during user interaction
# - time spent paused is tracked separately
# - will be excluded from the final <suitkaise-api>elapsed</suitkaise-api> time
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>pause</suitkaise-api>()

# do work while paused (not timed)
# - in real code: user_input = input("Continue? ")
print("Waiting for user input (not timed)...")
data = b"paused_work"
for _ in range(30000):
    data = hashlib.sha256(data).digest()

# resume <suitkaise-api>timing</suitkaise-api>
# - clock starts again from where it paused
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>resume</suitkaise-api>()

# phase 2: more <suitkaise-api>processing</suitkaise-api> (timed)
print("Phase 2: More <suitkaise-api>processing</suitkaise-api>...")
data = b"phase2"
for _ in range(20000):
    data = hashlib.sha256(data).digest()

# stop and get <suitkaise-api>elapsed</suitkaise-api> time
<suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

# <suitkaise-api>elapsed</suitkaise-api> should be ~0.4s, not ~1.4s
# - the 1.0s pause is excluded
print(f"\nActive work time: {<suitkaise-api>elapsed</suitkaise-api>:.3f}s")
print(f"Time spent paused: {<suitkaise-api>timer</suitkaise-api>.total_time_paused:.3f}s")
```

## Context Manager Examples

### Basic TimeThis

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# <suitkaise-api>TimeThis</suitkaise-api> context manager for clean <suitkaise-api>timing</suitkaise-api> syntax
#
# <suitkaise-api>TimeThis</suitkaise-api> wraps a code block with automatic start/<suitkaise-api>stop</suitkaise-api>.
# The 'as timer' gives you access to the timer inside and after the block.
# Perfect for one-off measurements without explicit start/stop calls.
# ──────────────────────────────────────────────────────────────────────────────

# time a code block using context manager
# - automatically calls <suitkaise-api>start</suitkaise-api>() on entry
# - automatically calls <suitkaise-api>stop</suitkaise-api>() on exit
# - creates a new <suitkaise-api>Sktimer</suitkaise-api> if none provided
with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>() as timer:
    # all code in this block is timed
    total = 0
    for i in range(1000000):
        total += i

# after the block, timer has the measurement
print(f"Loop took: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")

# compare two operations
# ─────────────────────────────────────────────────────────────────────────────

# time operation A
with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>() as timer_a:
    result_a = sum(range(1000000))

# time operation B
with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>() as timer_b:
    result_b = 0
    for i in range(1000000):
        result_b += i

print(f"\nBuilt-in sum(): {timer_a.<suitkaise-api>most_recent</suitkaise-api>:.6f}s")
print(f"Manual loop:   {timer_b.<suitkaise-api>most_recent</suitkaise-api>:.6f}s")
print(f"Ratio: {timer_b.<suitkaise-api>most_recent</suitkaise-api> / timer_a.<suitkaise-api>most_recent</suitkaise-api>:.1f}x slower")
```

### Shared Timer with TimeThis

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
from pathlib import Path
import json
import hashlib

# ──────────────────────────────────────────────────────────────────────────────
# Accumulating statistics across multiple <suitkaise-api>TimeThis</suitkaise-api> blocks
#
# Pass a pre-created <suitkaise-api>Sktimer</suitkaise-api> to <suitkaise-api>TimeThis</suitkaise-api> to collect multiple measurements.
# Each context manager block adds one measurement to the shared <suitkaise-api>timer</suitkaise-api>.
# Great for <suitkaise-api>timing</suitkaise-api> the same operation in different parts of your code.
# ──────────────────────────────────────────────────────────────────────────────

# create a shared timer for all API-like file reads
api_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

# seed local data files
data_dir = Path("data/api")
data_dir.mkdir(parents=True, exist_ok=True)
for user_id in range(5):
    (data_dir / f"user_{user_id}.json").write_text(
        json.dumps({"id": user_id, "name": f"User {user_id}"})
    )
    (data_dir / f"posts_{user_id}.json").write_text(
        json.dumps([{"id": i, "title": f"Post {i}"} for i in range(3)])
    )

def fetch_user(user_id):
    """Fetch a user from disk."""
    # pass the shared timer to <suitkaise-api>TimeThis</suitkaise-api>
    # - each call adds one measurement to api_timer
    with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>(api_timer):
        text = (data_dir / f"user_{user_id}.json").read_text()
        digest = hashlib.sha256(text.encode()).hexdigest()
        return {**json.loads(text), "digest": digest[:8]}

def fetch_posts(user_id):
    """Fetch posts for a user from disk."""
    with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>(api_timer):
        text = (data_dir / f"posts_{user_id}.json").read_text()
        posts = json.loads(text)
        for post in posts:
            post["hash"] = hashlib.sha256(post["title"].encode()).hexdigest()[:8]
        return posts

# make several API calls
# - each call is timed and added to api_timer
for user_id in range(5):
    user = fetch_user(user_id)
    posts = fetch_posts(user_id)

# analyze combined API performance
# - 5 users × 2 calls each = 10 measurements
print(f"Total API calls: {api_timer.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Total API time: {api_timer.<suitkaise-api>total_time</suitkaise-api>:.3f}s")
print(f"Average call: {api_timer.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"Slowest call: {api_timer.max:.3f}s")
print(f"95th percentile: {api_timer.<suitkaise-api>percentile</suitkaise-api>(95):.3f}s")
```

### TimeThis with Threshold

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib

# ──────────────────────────────────────────────────────────────────────────────
# Filtering out fast operations with threshold
#
# The threshold parameter only records times above a minimum value.
# Useful when you only care about "slow" operations for analysis.
# Fast operations are silently discarded.
# ──────────────────────────────────────────────────────────────────────────────

slow_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

def process_item(item):
    """Process an item, sometimes slow."""
    # only record times >= 0.1 seconds
    # - fast operations won't be recorded
    # - helps focus analysis on problematic cases
    with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>(slow_timer, threshold=0.1):
        # variable <suitkaise-api>processing</suitkaise-api> time based on item size
        data = f"item_{item}".encode()
        iterations = 40000 if item % 5 == 0 else 4000
        for _ in range(iterations):
            data = hashlib.sha256(data).digest()

# process 50 items
for i in range(50):
    process_item(i)

# only slow operations were recorded
# - expected: ~10 measurements (20% of 50)
print(f"Slow operations detected: {slow_timer.<suitkaise-api>num_times</suitkaise-api>}")
if slow_timer.<suitkaise-api>num_times</suitkaise-api> > 0:
    print(f"Average slow time: {slow_timer.<suitkaise-api>mean</suitkaise-api>:.3f}s")
```

## Decorator Examples

### Basic @timethis

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# Timing functions with @<suitkaise-api>timethis</suitkaise-api> decorator
#
# @<suitkaise-api>timethis</suitkaise-api>() automatically times every call to the decorated function.
# The timer is attached to the function as .<suitkaise-api>timer</suitkaise-api> attribute.
# Call the function multiple times to build statistics.
# ──────────────────────────────────────────────────────────────────────────────

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
def fibonacci(n):
    """Calculate nth Fibonacci number (inefficient recursive version)."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# first call
<suitkaise-api>result</suitkaise-api> = fibonacci(20)
print(f"fib(20) = {<suitkaise-api>result</suitkaise-api>}")
print(f"Time: {fibonacci.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")

# call multiple times to build statistics
# - each call adds a measurement to fibonacci.<suitkaise-api>timer</suitkaise-api>
for n in [15, 18, 20, 22, 25]:
    <suitkaise-api>result</suitkaise-api> = fibonacci(n)
    print(f"fib({n}) = {<suitkaise-api>result</suitkaise-api>}, time: {fibonacci.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")

# view statistics
print(f"\nTotal calls: {fibonacci.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Mean time: {fibonacci.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"Min time: {fibonacci.<suitkaise-api>timer</suitkaise-api>.min:.3f}s")
print(f"Max time: {fibonacci.<suitkaise-api>timer</suitkaise-api>.max:.3f}s")
```

### Shared Timer Across Functions

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib

# ──────────────────────────────────────────────────────────────────────────────
# Single timer tracking multiple functions
#
# Pass an explicit <suitkaise-api>Sktimer</suitkaise-api> to @<suitkaise-api>timethis</suitkaise-api>() to share across functions.
# All decorated functions contribute to the same statistics.
# Useful for measuring total time spent on a category of operations.
# ──────────────────────────────────────────────────────────────────────────────

# create a shared timer for all math operations
math_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(math_timer)
def add(a, b):
    hashlib.sha256(f"{a}+{b}".encode()).digest()
    return a + b

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(math_timer)
def multiply(a, b):
    hashlib.sha256(f"{a}*{b}".encode()).digest()
    return a * b

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(math_timer)
def divide(a, b):
    hashlib.sha256(f"{a}/{b}".encode()).digest()
    return a / b if b != 0 else 0

# perform many operations
# - all times go into math_timer
for i in range(1, 101):
    a, b = i, i + 1
    add(a, b)
    multiply(a, b)
    divide(a, b)

# combined statistics across all math functions
# - 100 iterations × 3 functions = 300 measurements
print(f"Total math operations: {math_timer.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Total math time: {math_timer.<suitkaise-api>total_time</suitkaise-api>:.3f}s")
print(f"Average operation: {math_timer.<suitkaise-api>mean</suitkaise-api>:.6f}s")
```

### Stacked Decorators

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
from pathlib import Path
import json

# ──────────────────────────────────────────────────────────────────────────────
# Both shared and per-function <suitkaise-api>timing</suitkaise-api>
#
# Stack multiple @<suitkaise-api>timethis</suitkaise-api>() decorators to track at different granularities.
# One timer for combined stats, another for per-function stats.
# Useful for detailed performance analysis.
# ──────────────────────────────────────────────────────────────────────────────

# shared timer for all database operations
db_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()           # per-function <suitkaise-api>timer</suitkaise-api> (auto-attached)
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(db_timer)   # shared timer
def db_read(key):
    """Read from a JSON file as a tiny local store."""
    data = json.loads(db_path.read_text())
    return data.get(key)

@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()           # per-function <suitkaise-api>timer</suitkaise-api> (auto-attached)
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(db_timer)   # shared timer
def db_write(key, value):
    """Write to a JSON file as a tiny local store."""
    data = json.loads(db_path.read_text())
    data[key] = value
    db_path.write_text(json.dumps(data))
    return True

db_path = Path("data/db.json")
db_path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
db_path.write_text(json.dumps({}))

# perform operations
for i in range(20):
    db_read(f"key_{i}")
    db_write(f"key_{i}", f"value_{i}")

# combined database statistics
print("=== Combined DB Stats ===")
print(f"Total operations: {db_timer.<suitkaise-api>num_times</suitkaise-api>}")  # 40
print(f"Total time: {db_timer.<suitkaise-api>total_time</suitkaise-api>:.3f}s")
print(f"Mean: {db_timer.<suitkaise-api>mean</suitkaise-api>:.3f}s")

# per-function statistics
print("\n=== Read Stats ===")
print(f"Read operations: {db_read.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")  # 20
print(f"Read mean: {db_read.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")

print("\n=== Write Stats ===")
print(f"Write operations: {db_write.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")  # 20
print(f"Write mean: {db_write.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
```

### Rolling Window

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib

# ──────────────────────────────────────────────────────────────────────────────
# Rolling window for recent measurements only
#
# max_times limits how many measurements are kept.
# Older measurements are automatically discarded.
# Useful for long-running processes where you only care about recent performance.
# ──────────────────────────────────────────────────────────────────────────────

# only keep last 10 measurements
# - older measurements are discarded as new ones arrive
# - memory stays bounded regardless of how many calls
@<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(max_times=10)
def process_request():
    """Process a request by hashing its payload."""
    payload = b"request_payload" * 500
    hashlib.sha256(payload).hexdigest()

# process 100 requests
for i in range(100):
    process_request()
    
    # check stats periodically
    if (i + 1) % 25 == 0:
        # num_times is capped at 10 (our max_times)
        print(f"After {i + 1} requests: "
              f"{process_request.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>} measurements, "
              f"mean: {process_request.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")

# final stats are based on only the last 10 requests
print(f"\nFinal stats (last 10 only):")
print(f"Mean: {process_request.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"Min: {process_request.<suitkaise-api>timer</suitkaise-api>.min:.3f}s")
print(f"Max: {process_request.<suitkaise-api>timer</suitkaise-api>.max:.3f}s")
```

## Advanced Examples

### Concurrent Timing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import threading
import hashlib

# ──────────────────────────────────────────────────────────────────────────────
# Thread-safe <suitkaise-api>timing</suitkaise-api> across multiple threads
#
# <suitkaise-api>Sktimer</suitkaise-api> is fully thread-safe using per-thread sessions.
# Multiple threads can time operations concurrently.
# All measurements aggregate into a single statistics pool.
# ──────────────────────────────────────────────────────────────────────────────

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()

def worker(worker_id, iterations):
    """Worker function that times its operations."""
    for i in range(iterations):
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        
        # real work with deterministic variation
        payload = f"worker_{worker_id}_{i}".encode()
        iterations = 2000 + (i % 5) * 500
        for _ in range(iterations):
            payload = hashlib.sha256(payload).digest()
        
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()
    
    print(f"Worker {worker_id} completed {iterations} iterations")

# create and start multiple threads
# - each thread times its own work independently
# - all times go into the same timer
threads = []
for i in range(4):
    t = threading.Thread(target=worker, args=(i, 25))
    threads.append(t)
    t.<suitkaise-api>start</suitkaise-api>()

# wait for all threads to complete
for t in threads:
    t.join()

# combined statistics from all threads
# - 4 workers × 25 iterations = 100 measurements
print(f"\n=== Combined Stats (all threads) ===")
print(f"Total measurements: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Total time: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>:.3f}s")
print(f"Mean: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"Std Dev: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>:.3f}s")
```

### Benchmarking Multiple Implementations

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# Comparing performance of different implementations
#
# Create separate timers for each implementation.
# Run multiple iterations to get statistically meaningful results.
# Compare using mean, std dev, and percentiles.
# ──────────────────────────────────────────────────────────────────────────────

def benchmark(name, func, iterations=100):
    """Run a function multiple times and return <suitkaise-api>timing</suitkaise-api> statistics."""
    timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()
    
    for _ in range(iterations):
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        func()
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()
    
    return {
        'name': name,
        'mean': <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>,
        'stdev': <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>,
        'p50': <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(50),
        'p95': <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95),
        'p99': <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(99),
    }

# implementations to compare
def list_append():
    <suitkaise-api>result</suitkaise-api> = []
    for i in range(10000):
        <suitkaise-api>result</suitkaise-api>.append(i)
    return <suitkaise-api>result</suitkaise-api>

def list_comprehension():
    return [i for i in range(10000)]

def list_constructor():
    return list(range(10000))

# <suitkaise-api>run</suitkaise-api> benchmarks
results = [
    benchmark("list.append()", list_append),
    benchmark("list comprehension", list_comprehension),
    benchmark("list(range())", list_constructor),
]

# print comparison table
print(f"{'Method':<20} {'Mean':>10} {'StdDev':>10} {'P95':>10} {'P99':>10}")
print("-" * 62)

for r in sorted(results, key=lambda x: x['mean']):
    print(f"{r['name']:<20} "
          f"{r['mean']*1000:>9.3f}ms "
          f"{r['stdev']*1000:>9.3f}ms "
          f"{r['p95']*1000:>9.3f}ms "
          f"{r['p99']*1000:>9.3f}ms")
```

### Discard Failed Operations

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib

# ──────────────────────────────────────────────────────────────────────────────
# Only recording successful operations
#
# Use <suitkaise-api>discard</suitkaise-api>() to stop <suitkaise-api>timing</suitkaise-api> without recording when an operation fails.
# Keeps statistics clean and meaningful (only successful times).
# The discarded time is still returned for logging if needed.
# ──────────────────────────────────────────────────────────────────────────────

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()
success_count = 0
failure_count = 0

def unreliable_operation(item_id: int):
    """Operation that sometimes fails based on content."""
    payload = f"item_{item_id}".encode()
    digest = hashlib.sha256(payload).digest()
    
    # deterministic failure for some inputs
    if digest[0] % 3 == 0:
        raise RuntimeError("Operation failed")
    
    return digest[:8].hex()

# <suitkaise-api>run</suitkaise-api> many operations
for i in range(100):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    
    try:
        <suitkaise-api>result</suitkaise-api> = unreliable_operation(i)
        # success - record the <suitkaise-api>timing</suitkaise-api>
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()
        success_count += 1
        
    except RuntimeError:
        # failure - discard <suitkaise-api>timing</suitkaise-api> (don't pollute statistics)
        # - returns <suitkaise-api>elapsed</suitkaise-api> time in case we want to log it
        discarded_time = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()
        failure_count += 1

# statistics only reflect successful operations
print(f"Successful operations: {success_count}")
print(f"Failed operations: {failure_count}")
print(f"Recorded measurements: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")  # equals success_count
print(f"Mean success time: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
```

### Async Timing

```python
import asyncio
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# Timing async operations
#
# The <suitkaise-api>timing</suitkaise-api> API works the same in async context.
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_data(item_id):
    """Async file read with real I/O."""
    from pathlib import Path
    path = Path(f"data/async_{item_id}.txt")
    path.<suitkaise-api>parent</suitkaise-api>.mkdir(parents=True, exist_ok=True)
    path.write_text("async data\n" * 1000)
    return await asyncio.to_thread(path.read_text)

async def main():
    timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()
    
    # time multiple async operations
    for i in range(5):
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        data = await fetch_data(i)
        <suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()
        print(f"Fetched {data}: {<suitkaise-api>elapsed</suitkaise-api>:.3f}s")
    
    print(f"\nMean fetch time: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")

# <suitkaise-api>run</suitkaise-api> the async code
asyncio.<suitkaise-api>run</suitkaise-api>(main())
```

## Full API Performance Monitor Script

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import threading
import hashlib
from dataclasses import dataclass
from typing import Dict, Optional

# ──────────────────────────────────────────────────────────────────────────────
# Full API Performance Monitor
#
# A complete system for monitoring API endpoint performance.
# Features:
# - Per-endpoint <suitkaise-api>timing</suitkaise-api> with separate statistics
# - Combined overall statistics
# - Thread-safe for concurrent requests
# - Rolling window to bound memory usage
# - Periodic reporting
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class EndpointStats:
    """Statistics for a single endpoint."""
    name: str
    timer: <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>
    
    def report(self) -> str:
        """Generate a report string for this endpoint."""
        if self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api> == 0:
            return f"{self.name}: no data"
        
        return (f"{self.name}: "
                f"n={self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}, "
                f"mean={self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>*1000:.1f}ms, "
                f"p95={self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95)*1000:.1f}ms, "
                f"max={self.<suitkaise-api>timer</suitkaise-api>.max*1000:.1f}ms")


class APIMonitor:
    """Monitor API endpoint performance."""
    
    def __init__(self, max_measurements: int = 1000):
        # overall timer for all endpoints
        # - tracks total API performance
        self.overall_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>(max_times=max_measurements)
        
        # per-endpoint timers
        # - allows drilling down into specific endpoint performance
        self._endpoints: Dict[str, EndpointStats] = {}
        self._lock = threading.RLock()
    
    def _get_endpoint(self, name: str) -> EndpointStats:
        """Get or create stats for an endpoint."""
        with self._lock:
            if name not in self._endpoints:
                # create new timer for this endpoint
                # - same max_times as overall to keep memory bounded
                self._endpoints[name] = EndpointStats(
                    name=name,
                    timer=<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>(max_times=1000)
                )
            return self._endpoints[name]
    
    def time_request(self, endpoint: str):
        """Context manager for <suitkaise-api>timing</suitkaise-api> a request to an endpoint."""
        # get the endpoint's timer
        endpoint_stats = self._get_endpoint(endpoint)
        
        # create a <suitkaise-api>TimeThis</suitkaise-api> that records to both timers
        class DualTimer:
            def __init__(self, overall, endpoint):
                self.overall = overall
                self.endpoint = endpoint
                
            def __enter__(self):
                self.overall.<suitkaise-api>start</suitkaise-api>()
                self.endpoint.<suitkaise-api>start</suitkaise-api>()
                return self
            
            def __exit__(self, *args):
                self.overall.<suitkaise-api>stop</suitkaise-api>()
                self.endpoint.<suitkaise-api>stop</suitkaise-api>()
        
        return DualTimer(self.overall_timer, endpoint_stats.<suitkaise-api>timer</suitkaise-api>)
    
    def report(self) -> str:
        """Generate a full performance report."""
        lines = ["=== API Performance Report ===", ""]
        
        # overall statistics
        overall = self.overall_timer
        if overall.<suitkaise-api>num_times</suitkaise-api> > 0:
            lines.append(f"Overall: {overall.<suitkaise-api>num_times</suitkaise-api>} requests, "
                        f"mean={overall.<suitkaise-api>mean</suitkaise-api>*1000:.1f}ms, "
                        f"p95={overall.<suitkaise-api>percentile</suitkaise-api>(95)*1000:.1f}ms")
            lines.append("")
        
        # per-endpoint statistics
        lines.append("Per-endpoint:")
        with self._lock:
            for stats in sorted(self._endpoints.values(), 
                              key=lambda s: s.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api> or 0, 
                              reverse=True):
                lines.append(f"  {stats.report()}")
        
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# API-like Workload
# ──────────────────────────────────────────────────────────────────────────────

def run_api_calls(monitor: APIMonitor, num_calls: int):
    """Run deterministic, real work for API-like calls."""
    endpoints = ["/users", "/posts", "/comments", "/search", "/health"]
    payloads = {
        "/users": b"user\n" * 2000,
        "/posts": b"post\n" * 4000,
        "/comments": b"comment\n" * 8000,
        "/search": b"search\n" * 20000,
        "/health": b"ok\n" * 200,
    }
    
    for i in range(num_calls):
        endpoint = endpoints[i % len(endpoints)]
        with monitor.time_request(endpoint):
            hashlib.sha256(payloads[endpoint]).digest()


def worker(monitor: APIMonitor, worker_id: int, num_calls: int):
    """Worker thread that makes API calls."""
    print(f"Worker {worker_id} starting {num_calls} calls...")
    run_api_calls(monitor, num_calls)
    print(f"Worker {worker_id} completed")


# create the monitor
# - max_measurements=1000 keeps memory bounded
monitor = APIMonitor(max_measurements=1000)

# spawn multiple worker threads
# - <suitkaise-api>runs</suitkaise-api> concurrent API-like work
threads = []
for i in range(4):
    t = threading.Thread(target=worker, args=(monitor, i, 50))
    threads.append(t)
    t.<suitkaise-api>start</suitkaise-api>()

# wait for all workers
for t in threads:
    t.join()

# print the final report
print("\n" + monitor.report())


# ──────────────────────────────────────────────────────────────────────────────
# Expected output (times will vary):
# 
# Worker 0 starting 50 calls...
# Worker 1 starting 50 calls...
# Worker 2 starting 50 calls...
# Worker 3 starting 50 calls...
# Worker 0 completed
# Worker 1 completed
# Worker 2 completed
# Worker 3 completed
#
# === API Performance Report ===
# 
# Overall: 200 requests, mean=35.2ms, p95=120.5ms
# 
# Per-endpoint:
#   /search: n=45, mean=98.5ms, p95=142.3ms, max=149.8ms
#   /users: n=38, mean=34.2ms, p95=48.7ms, max=49.9ms
#   /posts: n=42, mean=19.8ms, p95=28.9ms, max=29.8ms
#   /comments: n=35, mean=14.5ms, p95=19.2ms, max=19.9ms
#   /health: n=40, mean=2.8ms, p95=4.8ms, max=4.9ms
# ──────────────────────────────────────────────────────────────────────────────
```
