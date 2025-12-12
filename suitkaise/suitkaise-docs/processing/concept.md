# `processing` Concept

## Table of Contents

1. [Overview](#1-overview)
2. [Core Concepts](#2-core-concepts)
3. [`Process` Class](#3-process-class)
4. [Lifecycle Methods](#4-lifecycle-methods)
5. [Configuration](#5-configuration)
6. [Timing with `@timesection`](#6-timing-with-timesection)
7. [Error Handling](#7-error-handling)
8. [Control Methods](#8-control-methods)
9. [Why using `processing` is great](#9-why-using-processing-is-great)
10. [Real Examples](#10-real-examples)
11. [Function-by-Function Examples](#11-function-by-function-examples)
12. [Performance Considerations](#12-performance-considerations)
13. [Platform Support](#13-platform-support)
14. [Importing `processing`](#14-importing-processing)

***For a quick read of the most important parts, see sections 9-11.***

## 1. Overview

`processing` provides a simple, intuitive way to run Python code in subprocesses. Designed to make using multiple processes really easy.

It uses suitkaise's `cerial` engine as the base serializer, meaning you can send basically any object through without having to worry if it will work or not.

In a single, simple class structure, you can create a well managed process object that can use almost any object you want.

- clean sectioned Process class that allows you to better organize your code.
- runner that takes Process class and runs it as a subprocess.
- no need to manually serialize and deserialize objects, it's all handled for you.
- errors that tell you what part of the process failed and why.
- timing built off of sktime, with it's extended functionality and easy performance tracking.
- __result__() method is a central location to return resulting data from the process.

Instead of manually managing `multiprocessing.Process`, serialization, queues, and error handling, you just define a class with what you want to do, and `processing` handles the rest.

## 2. Core Concepts

`processing` makes multiprocessing *intuitive and class-based*. Define what your process does with simple methods, and let the engine handle when and how they run. Never boilerplate again. You get quick access to the beautiful world of multiprocessing with no BS.

**Key principles:**
- **Simplicity**: Define a class, create your `__methods__`, call `start()`. That's it.
- **No boilerplate**: No `super().__init__()` needed, no manual serialization, no queue management
- **Built-in statistics**: Timing, lap counts, and error tracking included.
- **Automatic retries**: `lives` system restarts failed processes from fresh state
- **Integration**: Works seamlessly with `sktime` for timing and `cerial` for serialization

### Why using cerial is great here

You can send essentially any object through without having to worry if it will work or not.

No more "cant pickle X" errors.

**The lifecycle flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│                        Each Loop Iteration                       │
├─────────────────────────────────────────────────────────────────┤
│   __preloop__()  →  __loop__()  →  __postloop__()  →  repeat   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    When stop signal or limit reached:
                              ↓
                      __onfinish__()
                              ↓
                       __result__() or __error__()
                              ↓
                    Result sent to parent
```

You don't need to define every one of these methods. You could literally just use `__loop__()` and `__result__()` and be done with it.

## 3. `Process` Class

The `Process` class is the base that you inherit from to create your own subprocesses.

### Basic Structure

```python
from suitkaise.processing import Process

class MyProcess(Process):
    def __init__(self):
        # Your initialization - self.config is already available!
        self.counter = 0
        self.config.num_loops = 10
    
    def __loop__(self):
        # Your core work happens here
        self.counter += 1
    
    def __result__(self):
        # Return whatever you want to retrieve from the subprocess
        return self.counter

# Usage
p = MyProcess()
p.start()
p.wait()
result = p.result  # Returns 10
```

That's it! Those 10-ish lines of code will allow you to run this simple counter process.

### No `super().__init__()` Needed!

When you inherit from `Process`, initialization is handled automatically via `__init_subclass__`:

```python
# ✅ Just write your __init__ naturally
class MyProcess(Process):
    def __init__(self, data):
        self.data = data
        self.config.num_loops = 10

# ❌ No need for this
class MyProcess(Process):
    def __init__(self, data):
        super().__init__()  # Not required!
        self.data = data
```

### All Available Properties

| Property      | Type                    | Description 
|---------------|-------------------------|--------------
| `config`      | `ProcessConfig`         | Configuration dataclass (num_loops, join_in, lives, timeouts) 
| `timers`      | `ProcessTimers \| None` | Timer container (created when `@timesection` is used) 
| `error`       | `Exception \| None`     | Stores error when `__error__()` is called 
| `current_lap` | `int`                   | Current loop iteration (0-indexed) 
| `is_alive`    | `bool`                  | Whether subprocess is currently running 
| `result`      | `Any`                   | Retrieves result from subprocess (blocks if needed, raises if error) 

## 4. Lifecycle Methods

All lifecycle methods are optional. Override only what you need.

### `__preloop__()`
Called **before** each `__loop__()` iteration. Use for setup or validation.

```python
def __preloop__(self):
    self.start_time = sktime.now()
    print(f"Starting lap {self.current_lap}")
```

### `__loop__()`
Your **core work** happens here. The engine loops this for you - don't write your own loop inside!

```python
def __loop__(self):
    item = self.items[self.current_lap]
    result = process_item(item)
    self.results.append(result)
```

### `__postloop__()`
Called **after** each `__loop__()` iteration. Use for validation or cleanup.

```python
def __postloop__(self):
    elapsed = sktime.elapsed(self.start_time)
    self.lap_times.append(elapsed)
```

### `__onfinish__()`
Called **once** when the process stops (via `stop()`, `num_loops` reached, or `join_in` timeout).

```python
def __onfinish__(self):
    self.summary = {
        "total_items": len(self.results),
        "mean_time": sum(self.lap_times) / len(self.lap_times)
    }
```

### `__result__()`
Called **after** `__onfinish__()`. Return whatever you want to retrieve from the subprocess.

```python
def __result__(self):
    return self.summary
```

### `__error__()`
Called when an error occurs and no `lives` remain. Receives error via `self.error`.

```python
def __error__(self):
    print(f"Process failed: {self.error}")
    return self.error  # Default behavior
```

## 5. Configuration

Configuration is done through `self.config` in your `__init__`:

```python
class MyProcess(Process):
    def __init__(self):
        # Number of loops before stopping (None = infinite)
        self.config.num_loops = 100
        
        # Time limit in seconds (None = no limit)
        self.config.join_in = 30.0
        
        # Retry attempts on error (1 = no retries)
        self.config.lives = 3
        
        # Per-section timeouts
        self.config.timeouts.preloop = 30.0
        self.config.timeouts.loop = 300.0
        self.config.timeouts.postloop = 60.0
        self.config.timeouts.onfinish = 60.0
```

### Config Defaults

| Option              | Default | Description 
|---------------------|---------|---------------------
| `num_loops`         | `None`  | Run until stopped 
| `join_in`           | `None`  | No time limit 
| `lives`             | `1`     | No retries 
| `timeouts.preloop`  | `30.0`  | 30 seconds 
| `timeouts.loop`     | `300.0` | 5 minutes 
| `timeouts.postloop` | `60.0`  | 1 minute 
| `timeouts.onfinish` | `60.0`  | 1 minute 

## 6. Timing with `@timesection`

Add timing statistics to any lifecycle method with `@timesection()`:

```python
from suitkaise import processing

class TimedProcess(processing.Process):
    def __init__(self):
        self.config.num_loops = 100
    
    @timesection()
    def __preloop__(self):
        setup_work()
    
    @timesection()
    def __loop__(self):
        do_main_work()
    
    @timesection()
    def __postloop__(self):
        cleanup()
    
    def __result__(self):
        return {
            "loop_mean": self.timers.loop.mean,
            "loop_min": self.timers.loop.min,
            "loop_max": self.timers.loop.max,
            "total_time": self.timers.full_loop.total_time,
        }
```

Note: `@timesection()` only works on `Process` lifecycle methods (`__preloop__`, `__loop__`, `__postloop__`, `__onfinish__`). For timing arbitrary functions, use `sktime.timethis()` instead.

### Available Timers

| Timer | Description |
|-------|-------------|
| `self.timers.preloop` | Times `__preloop__()` calls |
| `self.timers.loop` | Times `__loop__()` calls |
| `self.timers.postloop` | Times `__postloop__()` calls |
| `self.timers.onfinish` | Times `__onfinish__()` call |
| `self.timers.full_loop` | Aggregates preloop + loop + postloop per iteration |

Each timer is a full `sktime.Timer` with `.mean`, `.min`, `.max`, `.stdev`, `.total_time`, etc.

## 7. Error Handling

### Section-Specific Errors

When an error occurs, it's wrapped to show where it happened:

| Error | Source |
|-------|--------|
| `PreloopError` | Error in `__preloop__()` |
| `MainLoopError` | Error in `__loop__()` |
| `PostLoopError` | Error in `__postloop__()` |
| `OnFinishError` | Error in `__onfinish__()` |
| `ResultError` | Error in `__result__()` |
| `TimeoutError` | Section exceeded timeout |

```python
try:
    result = my_process.result
except Exception as e:
    print(f"Loop failed on lap {e.current_lap}")
    print(f"Original error: {e.original_error}")
```

### Lives System (Automatic Retries)

Set `self.config.lives` to automatically retry on failure:

```python
class RetryingProcess(Process):
    def __init__(self):
        self.config.lives = 3  # 3 attempts total
        self.config.num_loops = 1
    
    def __loop__(self):
        response = risky_api_call()
        if response.status != 200:
            raise ConnectionError("API failed")
```

How it works:
1. Error occurs → wrap in `*LoopError`
2. If `lives > 1` → decrement lives, deserialize fresh original state, retry
3. If `lives == 1` → call `__error__()`, send error to parent

## 8. Control Methods

### `start()`
Spawns the subprocess and begins execution.

```python
p = MyProcess()
p.start()  # Process is now running in background
```

### `wait()`
Blocks until the subprocess finishes.

```python
p.start()
p.wait()  # Blocks here
# Process is now done
```

### `stop()`
Signals the process to stop gracefully (finishes current iteration (loop), calls `__onfinish__`).

```python
p.start()
sktime.sleep(5)
p.stop()  # Signal stop
p.wait()  # Wait for graceful shutdown
```

### `kill()`
Forcefully terminates the subprocess immediately. No cleanup, no result.

```python
p.start()
p.kill()  # Immediate termination
# p.result will be None
```

### `result` (property)
Retrieves the result from the subprocess. Blocks if not finished, raises if error occurred.

```python
p.start()
p.wait()
try:
    data = p.result  # Deserializes and returns __result__() output
except MainLoopError as e:
    print(f"Process failed: {e}")
```

## 9. Why using `processing` is great

`processing` gets rid of boilerplate, and saves you time and effort. And if you don't know how to use multiprocessing, this allows you to skip the knowledge check. 

Instead of manually handling serialization, queues, error propagation, and timeouts, you just define what your process should do.

**What makes it so easy:**
- **One class for everything**: Define lifecycle methods, configure with attributes, done
- **No serialization hassle**: `cerial` handles complex objects automatically (timers, loggers, custom classes)
- **Built-in timing**: `@timesection` gives you professional-grade statistics with one decorator
- **Automatic retries**: `lives` system handles transient failures without extra code
- **Clean error tracking**: Know exactly where and why things failed
- **Cross-platform**: Works on Unix, Linux, macOS, and Windows
- **AI friendly**: Simple patterns that AI agents can understand and generate correctly

For more info on what cerial can do exactly, see the [cerial concept page](../cerial/concept.md).

To get your AI agent up to speed on this or any other suitkaise module, do this:

```python
from suitkaise import docs

docs.download("a/file/path")

# downloading to a place outside the user's project root
with docs.Permission():
    # auto adds to Downloads folder
    docs.download()
```

Then, just have the agent read the docs after placing them in a place where it can access them.

## 10. Real Examples

### Beginner/Learning Projects

#### 1. Batch File Processor
**Problem:** Need to process many files without blocking the main program.

```python
from suitkaise import processing
from suitkaise import sktime

class FileProcessor(processing.Process):
    def __init__(self, file_list):
        self.files = file_list
        self.results = []
        self.config.num_loops = len(file_list)
    
    @timesection()
    def __loop__(self):
        file_path = self.files[self.current_lap]
        result = process_file(file_path)
        self.results.append(result)
    
    def __result__(self):
        return {
            "processed": len(self.results),
            "avg_time": self.timers.loop.mean,
        }

# Usage
files = ["data1.csv", "data2.csv", "data3.csv"]
processor = FileProcessor(files)
processor.start()

# Do other work while processing...

processor.wait()
print(f"Processed {processor.result['processed']} files")
print(f"Average time per file: {processor.result['avg_time']:.2f}s")
```

#### 2. Web Scraper with Rate Limiting
**Problem:** Scrape multiple pages without being blocked.

```python
from suitkaise.processing import Process
from suitkaise import sktime
import requests

class WebScraper(Process):
    def __init__(self, urls):
        self.urls = urls
        self.data = []
        self.config.num_loops = len(urls)
        self.config.lives = 3  # Retry failed requests
    
    def __loop__(self):
        url = self.urls[self.current_lap]
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        self.data.append(response.json())
        
        # Rate limit: small delay between requests
        sktime.sleep(0.5)
    
    def __result__(self):
        return self.data

# Scrape in background
scraper = WebScraper(["https://api.example.com/1", "https://api.example.com/2"])
scraper.start()
scraper.wait()
print(f"Got {len(scraper.result)} responses")
```

#### 3. Progress Tracking Demo
**Problem:** Track progress of a long-running task.

```python
from suitkaise import processing
from suitkaise import sktime

class ProgressTracker(processing.Process):
    def __init__(self, total_items):
        self.total = total_items
        self.processed = 0
        self.config.num_loops = total_items
    
    @timesection()
    def __loop__(self):
        # Simulate work
        sktime.sleep(0.1)
        self.processed += 1
    
    def __result__(self):
        return {
            "completed": self.processed,
            "total": self.total,
            "avg_time": self.timers.loop.mean,
            "total_time": self.timers.loop.total_time,
        }

# Run and check result
p = ProgressTracker(50)
p.start()
p.wait()

result = p.result
print(f"Completed {result['completed']}/{result['total']}")
print(f"Total time: {result['total_time']:.2f}s")
print(f"Average per item: {result['avg_time']:.3f}s")
```

### Professional/Advanced Projects

#### 4. Worker Pool Pattern
**Problem:** Process tasks in parallel with multiple workers.

```python
from suitkaise import processing
from suitkaise import sktime

class TaskWorker(processing.Process):
    def __init__(self, worker_id, task_data):
        self.worker_id = worker_id
        self.task = task_data
        self.result_value = None
        self.config.num_loops = 1
    
    @timesection()
    def __loop__(self):
        # Heavy computation
        self.result_value = expensive_computation(self.task)
    
    def __result__(self):
        return {
            "worker": self.worker_id,
            "result": self.result_value,
            "time": self.timers.loop.most_recent,
        }

# Create worker pool
tasks = [generate_task(i) for i in range(8)]
workers = [TaskWorker(i, task) for i, task in enumerate(tasks)]

# Start all workers (parallel execution)
start = sktime.now()
for w in workers:
    w.start()

# Wait and collect results
for w in workers:
    w.wait()

elapsed = sktime.elapsed(start)
results = [w.result for w in workers]

print(f"8 tasks completed in {elapsed:.2f}s (parallel)")
# If sequential: would take sum of all task times
```

#### 5. Resilient Data Pipeline
**Problem:** Process unreliable data sources with automatic recovery.

```python
from suitkaise.processing import Process
from suitkaise import sktime

class DataPipeline(Process):
    def __init__(self, source_config):
        self.source = source_config
        self.batches_processed = 0
        self.errors_recovered = 0
        
        self.config.join_in = 300.0  # Run for 5 minutes
        self.config.lives = 5  # 5 retry attempts
        self.config.timeouts.loop = 60.0  # 1 min per batch
    
    def __preloop__(self):
        self.batch = fetch_next_batch(self.source)
    
    def __loop__(self):
        process_batch(self.batch)
        self.batches_processed += 1
    
    def __error__(self):
        # Log error but still return partial results
        self.errors_recovered = 5 - self.config.lives
        return {
            "status": "partial",
            "batches": self.batches_processed,
            "errors": self.errors_recovered,
            "last_error": str(self.error),
        }
    
    def __result__(self):
        return {
            "status": "complete",
            "batches": self.batches_processed,
        }

# Run pipeline
pipeline = DataPipeline(config)
pipeline.start()
pipeline.wait()

result = pipeline.result
if result["status"] == "complete":
    print(f"Pipeline finished: {result['batches']} batches")
else:
    print(f"Pipeline had issues: {result['errors']} recoveries")
```

#### 6. Monitoring with Circuit Breaker
**Problem:** Monitor a service but stop if too many failures occur.

```python
from suitkaise import processing
from suitkaise.circuit import Circuit
from suitkaise import sktime

class ServiceMonitor(processing.Process):
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.circuit = Circuit(shorts=5)  # Break after 5 failures
        self.health_checks = []
        self.config.join_in = 60.0  # Monitor for 1 minute
    
    @timesection()
    def __loop__(self):
        try:
            response = requests.get(self.endpoint, timeout=5)
            self.health_checks.append({
                "time": sktime.now(),
                "status": response.status_code,
                "latency": self.timers.loop.most_recent,
            }) 
        except Exception as e:
            self.circuit.short()
            self.health_checks.append({
                "time": sktime.now(),
                "error": str(e),
            })
        
        # Stop monitoring if circuit breaks
        if self.circuit.broken:
            self.stop()
        
        sktime.sleep(2)  # Check every 2 seconds
    
    def __result__(self):
        return {
            "checks": len(self.health_checks),
            "circuit_broken": self.circuit.broken,
            "avg_latency": self.timers.loop.mean,
            "history": self.health_checks[-10:],  # Last 10 checks
        }
```

## 11. Function-by-Function Examples

### Creating a Process

#### Without `processing`: ***18 lines***
- Manual subprocess creation
- Have to use base pickle
- No timing
- No restart mechanic
- No error handling
- Not object-oriented

```python
import multiprocessing # 1
import pickle # 2

# simple worker with no timing, retries, and barebones error handling
# not object-oriented
def worker(serialized_data, result_queue): # 3
    try: # 4
        data = pickle.loads(serialized_data) # 5
        # do work...
        result = {"value": 42}
        result_queue.put(pickle.dumps(result)) # 6
    except Exception as e: # 7
        result_queue.put(pickle.dumps(e)) # 8

# Setup
data = {"items": [1, 2, 3]} # 9
serialized = pickle.dumps(data) # 10
result_queue = multiprocessing.Queue() # 11

# Start
process = multiprocessing.Process(target=worker, args=(serialized, result_queue)) # 12
process.start() # 13
process.join() # 14

# Get result
serialized_result = result_queue.get() # 15
result = pickle.loads(serialized_result) # 16
if isinstance(result, Exception): # 17
    raise result # 18
```

#### With `processing`: ***10 lines***

```python
from suitkaise.processing import Process # 1

class MyWorker(Process): # 2
    def __init__(self, items): # 3
        self.items = items
        self.config.num_loops = 1 # 4
    
    def __loop__(self): # 5
        self.value = sum(self.items)
    
    def __result__(self): # 6
        return {"value": self.value}

# Usage
p = MyWorker([1, 2, 3]) # 7
p.start() # 8
p.wait() # 9
result = p.result  # 10 {"value": 6}
```

### Adding Timing

#### Without `processing`: ***add 50+ lines***

- even a 50 line implementation will not yield near the same functionality as suitkaise timing in `sktime` and `processing`.
- not well organized.

```python
import time

times = []
for i in range(100):
    start = time.time()
    do_work()
    elapsed = time.time() - start
    times.append(elapsed)

mean_time = sum(times) / len(times)
min_time = min(times)
max_time = max(times)
```

#### With `processing`: ***add 1 line***

```python

@timesection()  # 1
def __loop__(self):
    do_work()

# Then access statistics
self.timers.loop.mean  # Automatic!
self.timers.loop.min
self.timers.loop.max
```

### Retry Logic

#### Without `processing`: ***20+ lines***

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        result = risky_operation()
        break
    except Exception as e:
        if attempt == max_retries - 1:
            raise
        time.sleep(1)
```

#### With `processing`: ***1 line***

```python
class MyWorker(Process):

    def __init__(self):

        # just edit config.lives
        self.config.lives = 3  # 1

```

### Multiple Parallel Workers

#### Without `processing`: ***25+ lines***

```python
import multiprocessing

def worker(task_id, result_queue):
    result = do_task(task_id)
    result_queue.put((task_id, result))

if __name__ == "__main__":
    result_queue = multiprocessing.Queue()
    processes = []
    
    for i in range(4):
        p = multiprocessing.Process(target=worker, args=(i, result_queue))
        p.start()
        processes.append(p)
    
    for p in processes:
        p.join()
    
    results = {}
    while not result_queue.empty():
        task_id, result = result_queue.get()
        results[task_id] = result
```

#### With `processing`: ***6 lines***

```python
class Worker(Process):

    def __init__(self, task_id):
        self.task_id = task_id
        self.config.num_loops = 1
    
    def __loop__(self):
        self.result = do_task(self.task_id)
    
    def __result__(self):
        return (self.task_id, self.result)

# simple, easy to read for loops
workers = [Worker(i) for i in range(4)] # 1

for w in workers: # 2
    w.start() # 3

for w in workers: # 4
    w.wait() # 5

results = {tid: res for tid, res in (w.result for w in workers)} # 6
```

## 12. Performance Considerations

### Process Startup Overhead
- **~100ms** for process creation, serialization, spawn, and result retrieval
- Includes `cerial` serialization/deserialization
- Fixed cost regardless of work done - amortize over many loops

### Loop Overhead
- **~1ms per loop** for lifecycle method dispatching
- Includes stop signal checking, timeout management
- Negligible for any real work

### `@timesection` Overhead
- **Negligible** (within measurement noise)
- Safe to use on all lifecycle methods
- No performance reason to avoid it

### Parallelism Efficiency
- 8 parallel workers achieve **~75% of ideal speedup**
- Overhead from spawn coordination, not from framework
- Compare: raw `multiprocessing.Pool` achieves ~80-85% but sucks

### When to use `processing`
- when you want quick, easy, readable and consistent code out of the gate.
- quickly prototyping a new project.
- complex applications that should utilize multiprocessing.
- when you are using local class definitions.
- when you need the extra features that processing provides (you should always need these)
- working as a team and need communicative code
- auto supports cross platform
- serializes complex objects automatically, some that cloudpickle/dill can't even handle

### When to use raw multiprocessing
- Extreme hot paths where every millisecond counts
- Simple stateless functions
- When you don't need lifecycle management
- using basic primitives that stdlib pickle can handle

### Limitations

The `__main__` Limitation

When you run a script directly (`python script.py`), your code lives in a special module called `__main__`. On macOS and Windows, subprocesses start fresh Python interpreters that can't access classes defined in `__main__`.

**What happens:**
1. You define `class MyProcessor(Process)` in your script
2. `cerial` serializes it as `"__main__.MyProcessor"`
3. Subprocess starts → imports `__main__` → but it's different now (multiprocessing bootstrap code)
4. Your class methods aren't found

**What works:**
- Lifecycle methods (`__loop__`, `__result__`, etc.) - handled specially by `processing`
- Instance attributes - serialized in `__dict__`

**What doesn't work:**
- Custom helper methods you define on the class

**Solution:** Put your `Process` subclass in an importable module:

```python
# processors.py
from suitkaise.processing import Process

class MyProcessor(Process):
    def __loop__(self):
        result = self._helper()  # ✓ Works!
    
    def _helper(self):
        return "hello"
# main.py
from processors import MyProcessor  # Import from real module

p = MyProcessor()
p.start()
```
Do this:
```python
# main.py
from processors import MyProcessor  # Import from real module

p = MyProcessor()
p.start()
```
### Performance

There is NO SIGNIFICANT DIFFERENCE between using `processing` and raw `multiprocessing` for creating a single process.

The notable difference in performance is when you are creating multiple processes.

Run 1
======================================================================
  Parallel Scaling: Processing vs Raw Multiprocessing
  Compare parallelism efficiency across worker counts
======================================================================

  Workers          Raw MP   Processing    Raw Eff   Proc Eff
  ----------------------------------------------------------
  1              155.32ms     164.53ms       100%       100%
  2              163.64ms     165.14ms        95%       100%
  4              173.97ms     181.06ms        89%        91%
  8              208.21ms     226.25ms        75%        73%

  At 8 workers:
    Raw multiprocessing: 6.0x speedup (75% efficiency)
    Processing module:   5.8x speedup (73% efficiency)
    Processing overhead: +18.04ms (+8.7%)

Run 2
======================================================================
  Parallel Scaling: Processing vs Raw Multiprocessing
  Compare parallelism efficiency across worker counts
======================================================================

  Workers          Raw MP   Processing    Raw Eff   Proc Eff
  ----------------------------------------------------------
  1              153.18ms     167.43ms       100%       100%
  2              161.35ms     163.50ms        95%       102%
  4              173.24ms     180.55ms        88%        93%
  8              203.87ms     218.09ms        75%        77%

  At 8 workers:
    Raw multiprocessing: 6.0x speedup (75% efficiency)
    Processing module:   6.1x speedup (77% efficiency)
    Processing overhead: +14.22ms (+7.0%)

Run 3
======================================================================
  Parallel Scaling: Processing vs Raw Multiprocessing
  Compare parallelism efficiency across worker counts
======================================================================

  Workers          Raw MP   Processing    Raw Eff   Proc Eff
  ----------------------------------------------------------
  1              153.33ms     162.21ms       100%       100%
  2              160.41ms     165.04ms        96%        98%
  4              171.63ms     179.65ms        89%        90%
  8              204.74ms     220.38ms        75%        74%

  At 8 workers:
    Raw multiprocessing: 6.0x speedup (75% efficiency)
    Processing module:   5.9x speedup (74% efficiency)
    Processing overhead: +15.64ms (+7.6%)

## 13. Platform Support

| Platform | Timeout Mechanism | Notes |
|----------|------------------|-------|
| Unix/Linux | `signal.SIGALRM` | Can interrupt blocking code |
| macOS | `signal.SIGALRM` | Can interrupt blocking code |
| Windows | Timer thread | Detects timeout but can't interrupt blocking code |

**Windows limitation:** If code has an infinite loop, timeout fires but the loop continues as a "zombie thread" until subprocess terminates. This is mitigated because:
1. Zombie dies when subprocess terminates
2. Fresh state on retry (lives system)
3. Most code isn't truly infinite

## 14. Importing `processing`

Recommended import pattern:

Only using Process class:
```python
from suitkaise.processing import Process

class MyProcess(Process):
    def __loop__(self):
        pass
```


Using Process class and the timesection decorator:
```python
from suitkaise import processing

class MyProcess(processing.Process):
    @timesection()
    def __loop__(self):
        pass
```
---

`processing` transforms subprocess management from manual boilerplate into a clean, intuitive class-based workflow. Define what your process does, and let the engine handle the rest.
