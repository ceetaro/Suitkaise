# `timing` Examples

## Basic Examples

### Simple Timing

```python
from suitkaise import timing

# ──────────────────────────────────────────────────────────────────────────────
# Basic start/stop timing
# 
# The simplest way to time something: start, do work, stop.
# The elapsed time is returned by stop() and also stored in the timer.
# ──────────────────────────────────────────────────────────────────────────────

# create a new timer instance
# - no arguments needed for basic usage
timer = timing.Sktimer()

# start the timer
# - records current high-resolution timestamp
# - uses perf_counter() internally for accurate measurements
timer.start()

# do some work
# - this is what we're measuring
# - could be any code: function calls, loops, I/O operations
for i in range(1000000):
    _ = i * i

# stop the timer and get elapsed time
# - returns elapsed time in seconds as a float
# - also stores the measurement in timer.times for statistics
elapsed = timer.stop()

# print the result
# - :.3f formats to 3 decimal places (millisecond precision)
print(f"Elapsed: {elapsed:.3f}s")

# you can also access the last measurement via property
# - most_recent is an alias for the last recorded time
# - result is also an alias for most_recent
print(f"Same value: {timer.most_recent:.3f}s")
```

### Using elapsed()

```python
from suitkaise import timing

# ──────────────────────────────────────────────────────────────────────────────
# Using elapsed() for simple time differences
#
# elapsed() calculates the difference between two timestamps.
# If you only provide one timestamp, it uses current time as the second.
# Order doesn't matter - always returns positive value.
# ──────────────────────────────────────────────────────────────────────────────

# get the current Unix timestamp
# - equivalent to time.time()
# - returns seconds since epoch as a float
start = timing.time()

# simulate some work
# - sleep() pauses execution for the specified seconds
# - also returns current time after sleeping (bonus feature)
timing.sleep(0.5)

# calculate elapsed time with one argument
# - uses current time as the second timestamp
# - same as: timing.elapsed(start, timing.time())
elapsed = timing.elapsed(start)
print(f"Elapsed: {elapsed:.3f}s")  # ~0.500s

# calculate elapsed time with two arguments
# - explicitly provide both timestamps
end = timing.time()
elapsed = timing.elapsed(start, end)
print(f"Elapsed: {elapsed:.3f}s")

# order doesn't matter - always returns positive value
# - internally uses abs() so you can't get negative results
# - useful when you're not sure which timestamp is earlier
elapsed_reversed = timing.elapsed(end, start)
print(f"Reversed: {elapsed_reversed:.3f}s")  # same value
```

### Multiple Measurements

```python
from suitkaise import timing
import random

# ──────────────────────────────────────────────────────────────────────────────
# Collecting multiple measurements for statistics
#
# Run the same operation multiple times and collect timing data.
# Sktimer accumulates all measurements and provides statistical analysis.
# ──────────────────────────────────────────────────────────────────────────────

timer = timing.Sktimer()

# run 100 iterations of the same operation
# - each iteration is timed independently
# - all times are stored in timer.times list
for i in range(100):
    timer.start()
    
    # simulate variable-time work
    # - random sleep creates natural variance in measurements
    # - real-world operations have similar variance from I/O, CPU load, etc.
    timing.sleep(random.uniform(0.01, 0.05))
    
    timer.stop()

# access statistics
# - num_times: how many measurements we collected
# - mean: average of all measurements
# - median: middle value when sorted (less affected by outliers)
# - stdev: standard deviation (measure of variance)
# - min/max: fastest and slowest measurements
print(f"Measurements: {timer.num_times}")
print(f"Mean: {timer.mean:.3f}s")
print(f"Median: {timer.median:.3f}s")
print(f"Std Dev: {timer.stdev:.3f}s")
print(f"Min: {timer.min:.3f}s")
print(f"Max: {timer.max:.3f}s")

# calculate percentiles
# - percentile(95) means 95% of measurements are at or below this value
# - useful for understanding "worst case" performance
p95 = timer.percentile(95)
p99 = timer.percentile(99)
print(f"95th percentile: {p95:.3f}s")
print(f"99th percentile: {p99:.3f}s")
```

### Using lap()

```python
from suitkaise import timing

# ──────────────────────────────────────────────────────────────────────────────
# Using lap() for continuous measurements
#
# lap() records the current measurement and immediately starts the next one.
# It's like calling stop() + start() in one operation.
# Useful for timing iterations without the overhead of separate stop/start.
# ──────────────────────────────────────────────────────────────────────────────

timer = timing.Sktimer()

# start timing
timer.start()

# process multiple items, recording time for each
items = ["item1", "item2", "item3", "item4", "item5"]

for item in items:
    # simulate processing each item
    timing.sleep(0.1)
    
    # record lap time and continue
    # - records time since last lap() or start()
    # - immediately begins new measurement
    # - returns the elapsed time for this lap
    lap_time = timer.lap()
    print(f"Processed {item}: {lap_time:.3f}s")

# after the loop, there's still an active measurement running
# - we need to either stop() or discard() it
# - discard() stops timing without recording (since we already recorded with lap())
timer.discard()

# we have 5 measurements (one per lap)
print(f"\nTotal measurements: {timer.num_times}")
print(f"Total time: {timer.total_time:.3f}s")
print(f"Average per item: {timer.mean:.3f}s")
```

### Pause and Resume

```python
from suitkaise import timing

# ──────────────────────────────────────────────────────────────────────────────
# Pausing timing during user interaction
#
# Sometimes you want to exclude certain time from measurements.
# pause()/resume() let you temporarily stop the clock without ending the session.
# Useful for excluding user input, network waits, or other external delays.
# ──────────────────────────────────────────────────────────────────────────────

timer = timing.Sktimer()

timer.start()

# phase 1: initial processing (timed)
print("Phase 1: Processing data...")
timing.sleep(0.2)

# pause timing during user interaction
# - time spent paused is tracked separately
# - will be excluded from the final elapsed time
timer.pause()

# simulate user thinking time (not timed)
# - in real code: user_input = input("Continue? ")
print("Waiting for user input (not timed)...")
timing.sleep(1.0)  # simulate user delay

# resume timing
# - clock starts again from where it paused
timer.resume()

# phase 2: more processing (timed)
print("Phase 2: More processing...")
timing.sleep(0.2)

# stop and get elapsed time
elapsed = timer.stop()

# elapsed should be ~0.4s, not ~1.4s
# - the 1.0s pause is excluded
print(f"\nActive work time: {elapsed:.3f}s")
print(f"Time spent paused: {timer.total_time_paused:.3f}s")
```

## Context Manager Examples

### Basic TimeThis

```python
from suitkaise import timing

# ──────────────────────────────────────────────────────────────────────────────
# TimeThis context manager for clean timing syntax
#
# TimeThis wraps a code block with automatic start/stop.
# The 'as timer' gives you access to the timer inside and after the block.
# Perfect for one-off measurements without explicit start/stop calls.
# ──────────────────────────────────────────────────────────────────────────────

# time a code block using context manager
# - automatically calls start() on entry
# - automatically calls stop() on exit
# - creates a new Sktimer if none provided
with timing.TimeThis() as timer:
    # all code in this block is timed
    total = 0
    for i in range(1000000):
        total += i

# after the block, timer has the measurement
print(f"Loop took: {timer.most_recent:.3f}s")

# compare two operations
# ─────────────────────────────────────────────────────────────────────────────

# time operation A
with timing.TimeThis() as timer_a:
    result_a = sum(range(1000000))

# time operation B
with timing.TimeThis() as timer_b:
    result_b = 0
    for i in range(1000000):
        result_b += i

print(f"\nBuilt-in sum(): {timer_a.most_recent:.6f}s")
print(f"Manual loop:   {timer_b.most_recent:.6f}s")
print(f"Ratio: {timer_b.most_recent / timer_a.most_recent:.1f}x slower")
```

### Shared Timer with TimeThis

```python
from suitkaise import timing
import random

# ──────────────────────────────────────────────────────────────────────────────
# Accumulating statistics across multiple TimeThis blocks
#
# Pass a pre-created Sktimer to TimeThis to collect multiple measurements.
# Each context manager block adds one measurement to the shared timer.
# Great for timing the same operation in different parts of your code.
# ──────────────────────────────────────────────────────────────────────────────

# create a shared timer for all API calls
api_timer = timing.Sktimer()

def fetch_user(user_id):
    """Simulate fetching a user from an API."""
    # pass the shared timer to TimeThis
    # - each call adds one measurement to api_timer
    with timing.TimeThis(api_timer):
        # simulate API latency
        timing.sleep(random.uniform(0.05, 0.15))
        return {"id": user_id, "name": f"User {user_id}"}

def fetch_posts(user_id):
    """Simulate fetching posts for a user."""
    with timing.TimeThis(api_timer):
        # simulate API latency
        timing.sleep(random.uniform(0.08, 0.20))
        return [{"id": i, "title": f"Post {i}"} for i in range(3)]

# make several API calls
# - each call is timed and added to api_timer
for user_id in range(5):
    user = fetch_user(user_id)
    posts = fetch_posts(user_id)

# analyze combined API performance
# - 5 users × 2 calls each = 10 measurements
print(f"Total API calls: {api_timer.num_times}")
print(f"Total API time: {api_timer.total_time:.3f}s")
print(f"Average call: {api_timer.mean:.3f}s")
print(f"Slowest call: {api_timer.max:.3f}s")
print(f"95th percentile: {api_timer.percentile(95):.3f}s")
```

### TimeThis with Threshold

```python
from suitkaise import timing
import random

# ──────────────────────────────────────────────────────────────────────────────
# Filtering out fast operations with threshold
#
# The threshold parameter only records times above a minimum value.
# Useful when you only care about "slow" operations for analysis.
# Fast operations are silently discarded.
# ──────────────────────────────────────────────────────────────────────────────

slow_timer = timing.Sktimer()

def process_item(item):
    """Process an item, sometimes slow."""
    # only record times >= 0.1 seconds
    # - fast operations won't be recorded
    # - helps focus analysis on problematic cases
    with timing.TimeThis(slow_timer, threshold=0.1):
        # simulate variable processing time
        # - 20% chance of being slow
        if random.random() < 0.2:
            timing.sleep(0.15)  # slow path
        else:
            timing.sleep(0.02)  # fast path

# process 50 items
for i in range(50):
    process_item(i)

# only slow operations were recorded
# - expected: ~10 measurements (20% of 50)
print(f"Slow operations detected: {slow_timer.num_times}")
if slow_timer.num_times > 0:
    print(f"Average slow time: {slow_timer.mean:.3f}s")
```

## Decorator Examples

### Basic @timethis

```python
from suitkaise import timing

# ──────────────────────────────────────────────────────────────────────────────
# Timing functions with @timethis decorator
#
# @timethis() automatically times every call to the decorated function.
# The timer is attached to the function as .timer attribute.
# Call the function multiple times to build statistics.
# ──────────────────────────────────────────────────────────────────────────────

@timing.timethis()
def fibonacci(n):
    """Calculate nth Fibonacci number (inefficient recursive version)."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# first call
result = fibonacci(20)
print(f"fib(20) = {result}")
print(f"Time: {fibonacci.timer.most_recent:.3f}s")

# call multiple times to build statistics
# - each call adds a measurement to fibonacci.timer
for n in [15, 18, 20, 22, 25]:
    result = fibonacci(n)
    print(f"fib({n}) = {result}, time: {fibonacci.timer.most_recent:.3f}s")

# view statistics
print(f"\nTotal calls: {fibonacci.timer.num_times}")
print(f"Mean time: {fibonacci.timer.mean:.3f}s")
print(f"Min time: {fibonacci.timer.min:.3f}s")
print(f"Max time: {fibonacci.timer.max:.3f}s")
```

### Shared Timer Across Functions

```python
from suitkaise import timing
import random

# ──────────────────────────────────────────────────────────────────────────────
# Single timer tracking multiple functions
#
# Pass an explicit Sktimer to @timethis() to share across functions.
# All decorated functions contribute to the same statistics.
# Useful for measuring total time spent on a category of operations.
# ──────────────────────────────────────────────────────────────────────────────

# create a shared timer for all math operations
math_timer = timing.Sktimer()

@timing.timethis(math_timer)
def add(a, b):
    timing.sleep(random.uniform(0.001, 0.005))
    return a + b

@timing.timethis(math_timer)
def multiply(a, b):
    timing.sleep(random.uniform(0.001, 0.005))
    return a * b

@timing.timethis(math_timer)
def divide(a, b):
    timing.sleep(random.uniform(0.001, 0.005))
    return a / b if b != 0 else 0

# perform many operations
# - all times go into math_timer
for _ in range(100):
    a, b = random.randint(1, 100), random.randint(1, 100)
    add(a, b)
    multiply(a, b)
    divide(a, b)

# combined statistics across all math functions
# - 100 iterations × 3 functions = 300 measurements
print(f"Total math operations: {math_timer.num_times}")
print(f"Total math time: {math_timer.total_time:.3f}s")
print(f"Average operation: {math_timer.mean:.6f}s")
```

### Stacked Decorators

```python
from suitkaise import timing
import random

# ──────────────────────────────────────────────────────────────────────────────
# Both shared and per-function timing
#
# Stack multiple @timethis() decorators to track at different granularities.
# One timer for combined stats, another for per-function stats.
# Useful for detailed performance analysis.
# ──────────────────────────────────────────────────────────────────────────────

# shared timer for all database operations
db_timer = timing.Sktimer()

@timing.timethis()           # per-function timer (auto-attached)
@timing.timethis(db_timer)   # shared timer
def db_read(key):
    """Simulate database read."""
    timing.sleep(random.uniform(0.01, 0.03))
    return f"value_{key}"

@timing.timethis()           # per-function timer (auto-attached)
@timing.timethis(db_timer)   # shared timer
def db_write(key, value):
    """Simulate database write."""
    timing.sleep(random.uniform(0.02, 0.05))
    return True

# perform operations
for i in range(20):
    db_read(f"key_{i}")
    db_write(f"key_{i}", f"value_{i}")

# combined database statistics
print("=== Combined DB Stats ===")
print(f"Total operations: {db_timer.num_times}")  # 40
print(f"Total time: {db_timer.total_time:.3f}s")
print(f"Mean: {db_timer.mean:.3f}s")

# per-function statistics
print("\n=== Read Stats ===")
print(f"Read operations: {db_read.timer.num_times}")  # 20
print(f"Read mean: {db_read.timer.mean:.3f}s")

print("\n=== Write Stats ===")
print(f"Write operations: {db_write.timer.num_times}")  # 20
print(f"Write mean: {db_write.timer.mean:.3f}s")
```

### Rolling Window

```python
from suitkaise import timing
import random

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
@timing.timethis(max_times=10)
def process_request():
    """Simulate processing a web request."""
    timing.sleep(random.uniform(0.01, 0.05))

# process 100 requests
for i in range(100):
    process_request()
    
    # check stats periodically
    if (i + 1) % 25 == 0:
        # num_times is capped at 10 (our max_times)
        print(f"After {i + 1} requests: "
              f"{process_request.timer.num_times} measurements, "
              f"mean: {process_request.timer.mean:.3f}s")

# final stats are based on only the last 10 requests
print(f"\nFinal stats (last 10 only):")
print(f"Mean: {process_request.timer.mean:.3f}s")
print(f"Min: {process_request.timer.min:.3f}s")
print(f"Max: {process_request.timer.max:.3f}s")
```

## Advanced Examples

### Concurrent Timing

```python
from suitkaise import timing
import threading
import random

# ──────────────────────────────────────────────────────────────────────────────
# Thread-safe timing across multiple threads
#
# Sktimer is fully thread-safe using per-thread sessions.
# Multiple threads can time operations concurrently.
# All measurements aggregate into a single statistics pool.
# ──────────────────────────────────────────────────────────────────────────────

timer = timing.Sktimer()

def worker(worker_id, iterations):
    """Worker function that times its operations."""
    for i in range(iterations):
        timer.start()
        
        # simulate variable work
        timing.sleep(random.uniform(0.01, 0.03))
        
        timer.stop()
    
    print(f"Worker {worker_id} completed {iterations} iterations")

# create and start multiple threads
# - each thread times its own work independently
# - all times go into the same timer
threads = []
for i in range(4):
    t = threading.Thread(target=worker, args=(i, 25))
    threads.append(t)
    t.start()

# wait for all threads to complete
for t in threads:
    t.join()

# combined statistics from all threads
# - 4 workers × 25 iterations = 100 measurements
print(f"\n=== Combined Stats (all threads) ===")
print(f"Total measurements: {timer.num_times}")
print(f"Total time: {timer.total_time:.3f}s")
print(f"Mean: {timer.mean:.3f}s")
print(f"Std Dev: {timer.stdev:.3f}s")
```

### Benchmarking Multiple Implementations

```python
from suitkaise import timing

# ──────────────────────────────────────────────────────────────────────────────
# Comparing performance of different implementations
#
# Create separate timers for each implementation.
# Run multiple iterations to get statistically meaningful results.
# Compare using mean, std dev, and percentiles.
# ──────────────────────────────────────────────────────────────────────────────

def benchmark(name, func, iterations=100):
    """Run a function multiple times and return timing statistics."""
    timer = timing.Sktimer()
    
    for _ in range(iterations):
        timer.start()
        func()
        timer.stop()
    
    return {
        'name': name,
        'mean': timer.mean,
        'stdev': timer.stdev,
        'p50': timer.percentile(50),
        'p95': timer.percentile(95),
        'p99': timer.percentile(99),
    }

# implementations to compare
def list_append():
    result = []
    for i in range(10000):
        result.append(i)
    return result

def list_comprehension():
    return [i for i in range(10000)]

def list_constructor():
    return list(range(10000))

# run benchmarks
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
from suitkaise import timing
import random

# ──────────────────────────────────────────────────────────────────────────────
# Only recording successful operations
#
# Use discard() to stop timing without recording when an operation fails.
# Keeps statistics clean and meaningful (only successful times).
# The discarded time is still returned for logging if needed.
# ──────────────────────────────────────────────────────────────────────────────

timer = timing.Sktimer()
success_count = 0
failure_count = 0

def unreliable_operation():
    """Simulate an operation that sometimes fails."""
    timing.sleep(random.uniform(0.01, 0.05))
    
    # 30% chance of failure
    if random.random() < 0.3:
        raise RuntimeError("Operation failed")
    
    return "success"

# run many operations
for i in range(100):
    timer.start()
    
    try:
        result = unreliable_operation()
        # success - record the timing
        timer.stop()
        success_count += 1
        
    except RuntimeError:
        # failure - discard timing (don't pollute statistics)
        # - returns elapsed time in case we want to log it
        discarded_time = timer.discard()
        failure_count += 1

# statistics only reflect successful operations
print(f"Successful operations: {success_count}")
print(f"Failed operations: {failure_count}")
print(f"Recorded measurements: {timer.num_times}")  # equals success_count
print(f"Mean success time: {timer.mean:.3f}s")
```

### Async Timing

```python
import asyncio
from suitkaise import timing

# ──────────────────────────────────────────────────────────────────────────────
# Timing async operations
#
# Use timing.sleep.asynced() for async-compatible sleep.
# The rest of the timing API works the same in async context.
# ──────────────────────────────────────────────────────────────────────────────

async def fetch_data(url_id):
    """Simulate async network request."""
    # async-compatible sleep
    # - uses asyncio.sleep internally
    # - call .asynced() to get async version, then call with args
    await timing.sleep.asynced()(0.1)
    return f"data_{url_id}"

async def main():
    timer = timing.Sktimer()
    
    # time multiple async operations
    for i in range(5):
        timer.start()
        data = await fetch_data(i)
        elapsed = timer.stop()
        print(f"Fetched {data}: {elapsed:.3f}s")
    
    print(f"\nMean fetch time: {timer.mean:.3f}s")

# run the async code
asyncio.run(main())
```

## Full API Performance Monitor Script

```python
from suitkaise import timing
import random
import threading
from dataclasses import dataclass
from typing import Dict, Optional

# ──────────────────────────────────────────────────────────────────────────────
# Full API Performance Monitor
#
# A complete system for monitoring API endpoint performance.
# Features:
# - Per-endpoint timing with separate statistics
# - Combined overall statistics
# - Thread-safe for concurrent requests
# - Rolling window to bound memory usage
# - Periodic reporting
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class EndpointStats:
    """Statistics for a single endpoint."""
    name: str
    timer: timing.Sktimer
    
    def report(self) -> str:
        """Generate a report string for this endpoint."""
        if self.timer.num_times == 0:
            return f"{self.name}: no data"
        
        return (f"{self.name}: "
                f"n={self.timer.num_times}, "
                f"mean={self.timer.mean*1000:.1f}ms, "
                f"p95={self.timer.percentile(95)*1000:.1f}ms, "
                f"max={self.timer.max*1000:.1f}ms")


class APIMonitor:
    """Monitor API endpoint performance."""
    
    def __init__(self, max_measurements: int = 1000):
        # overall timer for all endpoints
        # - tracks total API performance
        self.overall_timer = timing.Sktimer(max_times=max_measurements)
        
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
                    timer=timing.Sktimer(max_times=1000)
                )
            return self._endpoints[name]
    
    def time_request(self, endpoint: str):
        """Context manager for timing a request to an endpoint."""
        # get the endpoint's timer
        endpoint_stats = self._get_endpoint(endpoint)
        
        # create a TimeThis that records to both timers
        class DualTimer:
            def __init__(self, overall, endpoint):
                self.overall = overall
                self.endpoint = endpoint
                
            def __enter__(self):
                self.overall.start()
                self.endpoint.start()
                return self
            
            def __exit__(self, *args):
                self.overall.stop()
                self.endpoint.stop()
        
        return DualTimer(self.overall_timer, endpoint_stats.timer)
    
    def report(self) -> str:
        """Generate a full performance report."""
        lines = ["=== API Performance Report ===", ""]
        
        # overall statistics
        overall = self.overall_timer
        if overall.num_times > 0:
            lines.append(f"Overall: {overall.num_times} requests, "
                        f"mean={overall.mean*1000:.1f}ms, "
                        f"p95={overall.percentile(95)*1000:.1f}ms")
            lines.append("")
        
        # per-endpoint statistics
        lines.append("Per-endpoint:")
        with self._lock:
            for stats in sorted(self._endpoints.values(), 
                              key=lambda s: s.timer.mean or 0, 
                              reverse=True):
                lines.append(f"  {stats.report()}")
        
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Simulate API Usage
# ──────────────────────────────────────────────────────────────────────────────

def simulate_api_calls(monitor: APIMonitor, num_calls: int):
    """Simulate random API calls."""
    endpoints = [
        ("/users", 0.02, 0.05),      # endpoint, min_time, max_time
        ("/posts", 0.01, 0.03),
        ("/comments", 0.01, 0.02),
        ("/search", 0.05, 0.15),     # slow endpoint
        ("/health", 0.001, 0.005),   # fast endpoint
    ]
    
    for _ in range(num_calls):
        # pick a random endpoint
        endpoint, min_time, max_time = random.choice(endpoints)
        
        # time the request using our monitor
        with monitor.time_request(endpoint):
            # simulate the request
            timing.sleep(random.uniform(min_time, max_time))


def worker(monitor: APIMonitor, worker_id: int, num_calls: int):
    """Worker thread that makes API calls."""
    print(f"Worker {worker_id} starting {num_calls} calls...")
    simulate_api_calls(monitor, num_calls)
    print(f"Worker {worker_id} completed")


# create the monitor
# - max_measurements=1000 keeps memory bounded
monitor = APIMonitor(max_measurements=1000)

# spawn multiple worker threads
# - simulates concurrent API usage
threads = []
for i in range(4):
    t = threading.Thread(target=worker, args=(monitor, i, 50))
    threads.append(t)
    t.start()

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
