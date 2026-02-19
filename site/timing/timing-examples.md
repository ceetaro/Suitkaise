/*

synced from suitkaise-docs/timing/examples.md

*/

rows = 2
columns = 1

# 1.1

title = "`timing` Examples"

# 1.2

text = "
(start of dropdown "Basic Examples")
## Basic Examples

### Simple Timing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
total = sum(i * i for i in range(1_000_000))
elapsed = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

print(f"Elapsed: {elapsed:.3f}s")
print(f"Same value: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")  # also accessible as a property
```

### Using elapsed()

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

start = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>time</suitkaise-api>()
<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>sleep</suitkaise-api>(0.5)
end = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>time</suitkaise-api>()

# one argument: uses current time as second timestamp
print(f"Elapsed: {<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start):.3f}s")

# two arguments: explicit timestamps
print(f"Elapsed: {<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start, end):.3f}s")

# order doesn't matter — always positive
print(f"Reversed: {<suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(end, start):.3f}s")  # same value
```

### Multiple Measurements

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import json

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

# run 100 iterations, each timed independently
for i in range(100):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    data = {"id": i, "values": list(range(500))}
    json.dumps(data)
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

print(f"Measurements: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Mean: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.6f}s")
print(f"Median: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>median</suitkaise-api>:.6f}s")
print(f"Std Dev: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>:.6f}s")
print(f"Min: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>min</suitkaise-api>:.6f}s")
print(f"Max: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>max</suitkaise-api>:.6f}s")
print(f"95th percentile: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95):.6f}s")
print(f"99th percentile: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(99):.6f}s")
```

### Using lap()

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import json

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

pipeline = [
    ("parse",     lambda: json.loads('{"users": ' + json.dumps(list(range(5000))) + '}')),
    ("validate",  lambda: [x for x in range(5000) if isinstance(x, int)]),
    ("transform", lambda: {str(k): k * 2 for k in range(5000)}),
    ("serialize", lambda: json.dumps(list(range(5000)))),
]

for stage_name, stage_fn in pipeline:
    stage_fn()
    lap_time = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>lap</suitkaise-api>()
    print(f"{stage_name}: {lap_time:.4f}s")

<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()  # clean up the last pending measurement

print(f"\nTotal pipeline time: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>:.4f}s")
print(f"Slowest stage: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>max</suitkaise-api>:.4f}s")
```

### Pause and Resume

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import time

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()

# phase 1: actual work (timed)
total = sum(range(2_000_000))

# pause during a simulated user prompt
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>pause</suitkaise-api>()
time.sleep(1.0)  # pretend: input("Export results? (y/n): ")
<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>resume</suitkaise-api>()

# phase 2: more work (timed)
squared = [x * x for x in range(500_000)]

elapsed = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

print(f"Active work time: {elapsed:.3f}s")              # ~0.1s (only work)
print(f"Time spent paused: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time_paused</suitkaise-api>:.3f}s")  # ~1.0s (the prompt)
```

(end of dropdown "Basic Examples")

(start of dropdown "Context Manager Examples")
## Context Manager Examples

### Basic TimeThis

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis(</suitkaise-api>) as <suitkaise-api>timer</suitkaise-api>:
    total = sum(range(1_000_000))

print(f"Loop took: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>most_recent</suitkaise-api>:.3f}s")

# quick A/B comparison
with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis(</suitkaise-api>) as timer_a:
    result_a = sum(range(1_000_000))

with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis(</suitkaise-api>) as timer_b:
    result_b = 0
    for i in range(1_000_000):
        result_b += i

print(f"\nBuilt-in sum(): {timer_a.<suitkaise-api>most_recent</suitkaise-api>:.6f}s")
print(f"Manual loop:   {timer_b.<suitkaise-api>most_recent</suitkaise-api>:.6f}s")
print(f"Ratio: {timer_b.<suitkaise-api>most_recent</suitkaise-api> / timer_a.<suitkaise-api>most_recent</suitkaise-api>:.1f}x slower")
```

### Shared Timer with TimeThis

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import json

api_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

def serialize(obj):
    with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis(</suitkaise-api>api_timer):
        return json.dumps(obj)

def deserialize(data):
    with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis(</suitkaise-api>api_timer):
        return json.loads(data)

objects = [{"id": i, "values": list(range(500))} for i in range(100)]

for obj in objects:
    data = serialize(obj)
    deserialize(data)

# 100 objects × 2 operations = 200 measurements
print(f"Total calls: {api_timer.num_times}")
print(f"Total time: {api_timer.total_time:.3f}s")
print(f"Average: {api_timer.mean:.6f}s")
print(f"Slowest: {api_timer.<suitkaise-api>max</suitkaise-api>:.6f}s")
print(f"p95: {api_timer.percentile(95):.6f}s")
```

### TimeThis with Threshold

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import time

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(<suitkaise-api>threshold</suitkaise-api>=0.1)
def handle_request(request_id):
    """Simulate request handling — every 10th request is slow."""
    delay = 0.01 if request_id % 10 != 0 else 0.2
    time.sleep(delay)

for i in range(50):
    handle_request(i)

# only the slow requests (>= 0.1s) are recorded
print(f"Slow requests: {handle_request.<suitkaise-api>timer.num_times</suitkaise-api>}")  # ~5
print(f"Mean slow time: {handle_request.<suitkaise-api>timer.mean</suitkaise-api>:.3f}s")
```

(end of dropdown "Context Manager Examples")

(start of dropdown "Decorator Examples")
## Decorator Examples

### Basic @timethis

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# ──────────────────────────────────────────────────────────────────────────────
# Timing functions with @timethis decorator
#
# @timethis() automatically times every call to the decorated function.
# The timer is attached to the function as .timer attribute.
# Call the function multiple times to build statistics.
# ──────────────────────────────────────────────────────────────────────────────

import random

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
def sort_data(data):
    """Sort a list using Python's built-in sort."""
    return sorted(data)

# generate random datasets
datasets = [random.sample(range(100_000), 10_000) for _ in range(20)]

for data in datasets:
    sort_data(data)

# each call = one measurement
print(f"Calls: {sort_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")         # 20
print(f"Mean: {sort_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.4f}s")
print(f"Fastest: {sort_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>min</suitkaise-api>:.4f}s")
print(f"Slowest: {sort_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>max</suitkaise-api>:.4f}s")
print(f"p95: {sort_data.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95):.4f}s")
```

### Shared Timer Across Functions

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import json

io_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(io_timer)
def serialize(obj):
    return json.dumps(obj)

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(io_timer)
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
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import json

db_timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()           # per-function timer
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(db_timer)   # shared timer
def db_read(key):
    return json.loads('{"users": 100}').get(key)

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()           # per-function timer
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(db_timer)   # shared timer
def db_write(key, value):
    json.dumps({key: value})

for i in range(100):
    db_read(f"key_{i}")
    db_write(f"key_{i}", f"value_{i}")

# combined stats
print(f"Total DB ops: {db_timer.num_times}")     # 200
print(f"Overall mean: {db_timer.mean:.6f}s")

# per-function breakdown
print(f"Read mean:  {db_read.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.6f}s")  # 100 reads
print(f"Write mean: {db_write.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.6f}s") # 100 writes
```

### Rolling Window

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import json

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(<suitkaise-api>max_times</suitkaise-api>=10)
def process_request():
    json.dumps({"data": list(range(1000))})

for i in range(100):
    process_request()

    if (i + 1) % 25 == 0:
        t = process_request.timer
        print(f"After {i+1} requests: {<suitkaise-api>t.num_times</suitkaise-api>} kept, mean: {<suitkaise-api>t.mean</suitkaise-api>:.6f}s")

# stats always reflect only the last 10 measurements — memory stays bounded
print(f"\nFinal (last 10): mean={process_request.<suitkaise-api>timer.mean</suitkaise-api>:.6f}s")
```

(end of dropdown "Decorator Examples")

(start of dropdown "Advanced Examples")
## Advanced Examples

### Concurrent Timing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import threading
import hashlib

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

def worker(worker_id, num_iterations):
    """Worker function that times its operations."""
    for i in range(num_iterations):
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        data = f"worker_{worker_id}_item_{i}".encode()
        for _ in range(5000):
            data = hashlib.sha256(data).digest()
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

threads = [threading.Thread(target=worker, args=(i, 25)) for i in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# 4 workers × 25 iterations = 100 measurements, aggregated automatically
print(f"Total measurements: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Mean: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"Std Dev: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>:.3f}s")
print(f"p95: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95):.3f}s")
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
    timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)
    
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
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import random

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)
successes = 0
failures = 0

for i in range(100):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    try:
        if random.random() < 0.3:
            raise RuntimeError("transient failure")
        sorted(range(10_000))  # actual work
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()
        successes += 1
    except RuntimeError:
        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()  # don't pollute stats with failed runs
        failures += 1

print(f"Successes: {successes}, Failures: {failures}")
print(f"Recorded: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")  # equals successes
print(f"Mean success time: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.6f}s")
```

### Async Timing

```python
import asyncio
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

# @timethis works on async functions transparently
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
async def fetch_user(user_id):
    await asyncio.sleep(0.05)  # simulate network I/O
    return {"id": user_id, "name": f"User {user_id}"}

# TimeThis works as an async context manager
async def process_batch(user_ids):
    async with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis(</suitkaise-api>) as batch_timer:
        results = []
        for uid in user_ids:
            results.append(await fetch_user(uid))
    print(f"Batch took: {batch_timer.most_recent:.3f}s")
    return results

async def main():
    users = await process_batch(range(10))

    # per-fetch stats from @timethis
    print(f"Per-fetch mean: {fetch_user.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.4f}s")
    print(f"Per-fetch p95:  {fetch_user.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95):.4f}s")

asyncio.run(main())
```

### Frozen Snapshots

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

for _ in range(50):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    sorted(range(10_000))
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

# capture a frozen snapshot
snapshot = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>get_statistics</suitkaise-api>()

# timer continues recording new data...
for _ in range(50):
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
    sorted(range(10_000))
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()

# snapshot is immutable — still reflects the first 50 measurements
print(f"Snapshot mean (50 runs): {snapshot.mean:.4f}s")
print(f"Snapshot count: {snapshot.num_times}")         # 50

print(f"Live mean (100 runs): {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.4f}s")
print(f"Live count: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api>}")                # 100
```

### Importing External Measurements

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

timer = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api>)

# import timings from an external source (logs, another system, etc.)
external_measurements = [0.45, 0.52, 0.48, 0.71, 0.39, 0.55]
for t in external_measurements:
    <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(t)

# Sktimer isn't just a stopwatch — it's a statistical analysis tool
print(f"Mean: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
print(f"p95:  {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95):.3f}s")
print(f"Stdev: {<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>stdev</suitkaise-api>:.3f}s")
```

(end of dropdown "Advanced Examples")

## Full API Performance Monitor Script

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import threading

overall = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer(</suitkaise-api><suitkaise-api>max_times</suitkaise-api>=1000)

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(overall)
def handle_users():
    sorted(range(50_000))

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(overall)
def handle_search():
    {str(i): i for i in range(100_000)}

<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>()
<suitkaise-api>@timing</suitkaise-api>.<suitkaise-api>timethis</suitkaise-api>(overall)
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
print(f"Total requests: {overall.<suitkaise-api>num_times</suitkaise-api>}")
print(f"Overall mean: {overall.<suitkaise-api>mean</suitkaise-api>*1000:.1f}ms")
print(f"Overall p95:  {overall.<suitkaise-api>percentile</suitkaise-api>(95)*1000:.1f}ms")

# per-endpoint breakdown — stacked decorators give you both levels for free
for fn in [handle_users, handle_search, handle_health]:
    t = fn.<suitkaise-api>timer</suitkaise-api>
    print(f"  {fn.__name__}: n={<suitkaise-api>t.num_times</suitkaise-api>}, "
          f"mean={<suitkaise-api>t.mean</suitkaise-api>*1000:.1f}ms, p95={<suitkaise-api>t.percentile(</suitkaise-api>95)*1000:.1f}ms")
```
"
