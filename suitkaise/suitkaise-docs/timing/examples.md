# `timing` Examples

## Basic Examples

### Simple Timing

```python
from suitkaise import timing

timer = timing.Sktimer()

timer.start()
total = sum(i * i for i in range(1_000_000))
elapsed = timer.stop()

print(f"Elapsed: {elapsed:.3f}s")
print(f"Same value: {timer.most_recent:.3f}s")  # also accessible as a property
```

### Using elapsed()

```python
from suitkaise import timing

start = timing.time()
timing.sleep(0.5)
end = timing.time()

# one argument: uses current time as second timestamp
print(f"Elapsed: {timing.elapsed(start):.3f}s")

# two arguments: explicit timestamps
print(f"Elapsed: {timing.elapsed(start, end):.3f}s")

# order doesn't matter — always positive
print(f"Reversed: {timing.elapsed(end, start):.3f}s")  # same value
```

### Multiple Measurements

```python
from suitkaise import timing
import json

timer = timing.Sktimer()

# run 100 iterations, each timed independently
for i in range(100):
    timer.start()
    data = {"id": i, "values": list(range(500))}
    json.dumps(data)
    timer.stop()

print(f"Measurements: {timer.num_times}")
print(f"Mean: {timer.mean:.6f}s")
print(f"Median: {timer.median:.6f}s")
print(f"Std Dev: {timer.stdev:.6f}s")
print(f"Min: {timer.min:.6f}s")
print(f"Max: {timer.max:.6f}s")
print(f"95th percentile: {timer.percentile(95):.6f}s")
print(f"99th percentile: {timer.percentile(99):.6f}s")
```

### Using lap()

```python
from suitkaise import timing
import json

timer = timing.Sktimer()
timer.start()

pipeline = [
    ("parse",     lambda: json.loads('{"users": ' + json.dumps(list(range(5000))) + '}')),
    ("validate",  lambda: [x for x in range(5000) if isinstance(x, int)]),
    ("transform", lambda: {str(k): k * 2 for k in range(5000)}),
    ("serialize", lambda: json.dumps(list(range(5000)))),
]

for stage_name, stage_fn in pipeline:
    stage_fn()
    lap_time = timer.lap()
    print(f"{stage_name}: {lap_time:.4f}s")

timer.discard()  # clean up the last pending measurement

print(f"\nTotal pipeline time: {timer.total_time:.4f}s")
print(f"Slowest stage: {timer.max:.4f}s")
```

### Pause and Resume

```python
from suitkaise import timing
import time

timer = timing.Sktimer()
timer.start()

# phase 1: actual work (timed)
total = sum(range(2_000_000))

# pause during a simulated user prompt
timer.pause()
time.sleep(1.0)  # pretend: input("Export results? (y/n): ")
timer.resume()

# phase 2: more work (timed)
squared = [x * x for x in range(500_000)]

elapsed = timer.stop()

print(f"Active work time: {elapsed:.3f}s")              # ~0.1s (only work)
print(f"Time spent paused: {timer.total_time_paused:.3f}s")  # ~1.0s (the prompt)
```

## Context Manager Examples

### Basic TimeThis

```python
from suitkaise import timing

with timing.TimeThis() as timer:
    total = sum(range(1_000_000))

print(f"Loop took: {timer.most_recent:.3f}s")

# quick A/B comparison
with timing.TimeThis() as timer_a:
    result_a = sum(range(1_000_000))

with timing.TimeThis() as timer_b:
    result_b = 0
    for i in range(1_000_000):
        result_b += i

print(f"\nBuilt-in sum(): {timer_a.most_recent:.6f}s")
print(f"Manual loop:   {timer_b.most_recent:.6f}s")
print(f"Ratio: {timer_b.most_recent / timer_a.most_recent:.1f}x slower")
```

### Shared Timer with TimeThis

```python
from suitkaise import timing
import json

api_timer = timing.Sktimer()

def serialize(obj):
    with timing.TimeThis(api_timer):
        return json.dumps(obj)

def deserialize(data):
    with timing.TimeThis(api_timer):
        return json.loads(data)

objects = [{"id": i, "values": list(range(500))} for i in range(100)]

for obj in objects:
    data = serialize(obj)
    deserialize(data)

# 100 objects × 2 operations = 200 measurements
print(f"Total calls: {api_timer.num_times}")
print(f"Total time: {api_timer.total_time:.3f}s")
print(f"Average: {api_timer.mean:.6f}s")
print(f"Slowest: {api_timer.max:.6f}s")
print(f"p95: {api_timer.percentile(95):.6f}s")
```

### TimeThis with Threshold

```python
from suitkaise import timing
import time

@timing.timethis(threshold=0.1)
def handle_request(request_id):
    """Simulate request handling — every 10th request is slow."""
    delay = 0.01 if request_id % 10 != 0 else 0.2
    time.sleep(delay)

for i in range(50):
    handle_request(i)

# only the slow requests (>= 0.1s) are recorded
print(f"Slow requests: {handle_request.timer.num_times}")  # ~5
print(f"Mean slow time: {handle_request.timer.mean:.3f}s")
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

import random

@timing.timethis()
def sort_data(data):
    """Sort a list using Python's built-in sort."""
    return sorted(data)

# generate random datasets
datasets = [random.sample(range(100_000), 10_000) for _ in range(20)]

for data in datasets:
    sort_data(data)

# each call = one measurement
print(f"Calls: {sort_data.timer.num_times}")         # 20
print(f"Mean: {sort_data.timer.mean:.4f}s")
print(f"Fastest: {sort_data.timer.min:.4f}s")
print(f"Slowest: {sort_data.timer.max:.4f}s")
print(f"p95: {sort_data.timer.percentile(95):.4f}s")
```

### Shared Timer Across Functions

```python
from suitkaise import timing
import json

io_timer = timing.Sktimer()

@timing.timethis(io_timer)
def serialize(obj):
    return json.dumps(obj)

@timing.timethis(io_timer)
def deserialize(data):
    return json.loads(data)

objects = [{"id": i, "values": list(range(500))} for i in range(100)]

for obj in objects:
    data = serialize(obj)
    deserialize(data)

print(f"Total I/O operations: {io_timer.num_times}")    # 200
print(f"Total I/O time: {io_timer.total_time:.3f}s")
print(f"Average operation: {io_timer.mean:.6f}s")
```

### Stacked Decorators

```python
from suitkaise import timing
import json

db_timer = timing.Sktimer()

@timing.timethis()           # per-function timer
@timing.timethis(db_timer)   # shared timer
def db_read(key):
    return json.loads('{"users": 100}').get(key)

@timing.timethis()           # per-function timer
@timing.timethis(db_timer)   # shared timer
def db_write(key, value):
    json.dumps({key: value})

for i in range(100):
    db_read(f"key_{i}")
    db_write(f"key_{i}", f"value_{i}")

# combined stats
print(f"Total DB ops: {db_timer.num_times}")     # 200
print(f"Overall mean: {db_timer.mean:.6f}s")

# per-function breakdown
print(f"Read mean:  {db_read.timer.mean:.6f}s")  # 100 reads
print(f"Write mean: {db_write.timer.mean:.6f}s") # 100 writes
```

### Rolling Window

```python
from suitkaise import timing
import json

@timing.timethis(max_times=10)
def process_request():
    json.dumps({"data": list(range(1000))})

for i in range(100):
    process_request()

    if (i + 1) % 25 == 0:
        t = process_request.timer
        print(f"After {i+1} requests: {t.num_times} kept, mean: {t.mean:.6f}s")

# stats always reflect only the last 10 measurements — memory stays bounded
print(f"\nFinal (last 10): mean={process_request.timer.mean:.6f}s")
```

## Advanced Examples

### Concurrent Timing

```python
from suitkaise import timing
import threading
import hashlib

timer = timing.Sktimer()

def worker(worker_id, num_iterations):
    """Worker function that times its operations."""
    for i in range(num_iterations):
        timer.start()
        data = f"worker_{worker_id}_item_{i}".encode()
        for _ in range(5000):
            data = hashlib.sha256(data).digest()
        timer.stop()

threads = [threading.Thread(target=worker, args=(i, 25)) for i in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# 4 workers × 25 iterations = 100 measurements, aggregated automatically
print(f"Total measurements: {timer.num_times}")
print(f"Mean: {timer.mean:.3f}s")
print(f"Std Dev: {timer.stdev:.3f}s")
print(f"p95: {timer.percentile(95):.3f}s")
```

### Benchmarking Multiple Implementations

```python
from suitkaise import timing

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

timer = timing.Sktimer()
successes = 0
failures = 0

for i in range(100):
    timer.start()
    try:
        if random.random() < 0.3:
            raise RuntimeError("transient failure")
        sorted(range(10_000))  # actual work
        timer.stop()
        successes += 1
    except RuntimeError:
        timer.discard()  # don't pollute stats with failed runs
        failures += 1

print(f"Successes: {successes}, Failures: {failures}")
print(f"Recorded: {timer.num_times}")  # equals successes
print(f"Mean success time: {timer.mean:.6f}s")
```

### Async Timing

```python
import asyncio
from suitkaise import timing

# @timethis works on async functions transparently
@timing.timethis()
async def fetch_user(user_id):
    await asyncio.sleep(0.05)  # simulate network I/O
    return {"id": user_id, "name": f"User {user_id}"}

# TimeThis works as an async context manager
async def process_batch(user_ids):
    async with timing.TimeThis() as batch_timer:
        results = []
        for uid in user_ids:
            results.append(await fetch_user(uid))
    print(f"Batch took: {batch_timer.most_recent:.3f}s")
    return results

async def main():
    users = await process_batch(range(10))

    # per-fetch stats from @timethis
    print(f"Per-fetch mean: {fetch_user.timer.mean:.4f}s")
    print(f"Per-fetch p95:  {fetch_user.timer.percentile(95):.4f}s")

asyncio.run(main())
```

### Frozen Snapshots

```python
from suitkaise import timing

timer = timing.Sktimer()

for _ in range(50):
    timer.start()
    sorted(range(10_000))
    timer.stop()

# capture a frozen snapshot
snapshot = timer.get_statistics()

# timer continues recording new data...
for _ in range(50):
    timer.start()
    sorted(range(10_000))
    timer.stop()

# snapshot is immutable — still reflects the first 50 measurements
print(f"Snapshot mean (50 runs): {snapshot.mean:.4f}s")
print(f"Snapshot count: {snapshot.num_times}")         # 50

print(f"Live mean (100 runs): {timer.mean:.4f}s")
print(f"Live count: {timer.num_times}")                # 100
```

### Importing External Measurements

```python
from suitkaise import timing

timer = timing.Sktimer()

# import timings from an external source (logs, another system, etc.)
external_measurements = [0.45, 0.52, 0.48, 0.71, 0.39, 0.55]
for t in external_measurements:
    timer.add_time(t)

# Sktimer isn't just a stopwatch — it's a statistical analysis tool
print(f"Mean: {timer.mean:.3f}s")
print(f"p95:  {timer.percentile(95):.3f}s")
print(f"Stdev: {timer.stdev:.3f}s")
```

## Full API Performance Monitor Script

```python
from suitkaise import timing
import threading

overall = timing.Sktimer(max_times=1000)

@timing.timethis()
@timing.timethis(overall)
def handle_users():
    sorted(range(50_000))

@timing.timethis()
@timing.timethis(overall)
def handle_search():
    {str(i): i for i in range(100_000)}

@timing.timethis()
@timing.timethis(overall)
def handle_health():
    pass

def worker(num_requests):
    endpoints = [handle_users, handle_search, handle_health]
    for i in range(num_requests):
        endpoints[i % len(endpoints)]()

# 4 threads, 100 requests each — thread-safe, automatic aggregation
threads = [threading.Thread(target=worker, args=(100,)) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# overall stats
print(f"Total requests: {overall.num_times}")
print(f"Overall mean: {overall.mean*1000:.1f}ms")
print(f"Overall p95:  {overall.percentile(95)*1000:.1f}ms")

# per-endpoint breakdown — stacked decorators give you both levels for free
for fn in [handle_users, handle_search, handle_health]:
    t = fn.timer
    print(f"  {fn.__name__}: n={t.num_times}, "
          f"mean={t.mean*1000:.1f}ms, p95={t.percentile(95)*1000:.1f}ms")
```
