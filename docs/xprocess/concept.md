# 🚀 Suitkaise Multiprocessing - Concepts Guide

A comprehensive guide to understanding the core concepts and patterns of the Suitkaise multiprocessing engine.

## Table of Contents

1. [Basic Process Creation](#1-basic-process-creation)
2. [Process Lifecycle Hooks](#2-process-lifecycle-hooks)
3. [Process Configuration](#3-process-configuration)
4. [Error Handling & Recovery](#4-error-handling--recovery)
5. [Timing & Performance Measurement](#5-timing--performance-measurement)
6. [Process Pools](#6-process-pools)
7. [Function-Based Tasks](#7-function-based-tasks)
8. [Subprocess Management](#8-subprocess-management)
9. [Multiple Process Coordination](#9-multiple-process-coordination)
10. [Process Control & Flow Management](#10-process-control--flow-management)

---

## 1. Basic Process Creation

### Concept Overview

The foundation of Suitkaise multiprocessing is the `Process` class. Unlike traditional multiprocessing where you manage threads, locks, and communication manually, Suitkaise processes follow a simple pattern:

1. **Inherit** from `Process`
2. **Implement** `__loop__()` with your work logic
3. **Optionally implement** `__result__()` to return data
4. **Run** using `CrossProcessing` manager

### Core Pattern

```python
class SimpleProcess(Process):
    def __init__(self):
        super().__init__(num_loops=3)  # Will loop 3 times
        self.counter = 0
    
    def __loop__(self):
        # This runs once per loop iteration
        self.counter += 1
        print(f"Loop {self.counter}")
        time.sleep(0.1)
    
    def __result__(self):
        # This runs once at the end, returns data to main process
        return f"Completed {self.counter} loops"
```

### Key Concepts

- **`num_loops`**: Controls how many times `__loop__()` executes
  - `num_loops=5` → runs exactly 5 times
  - `num_loops=None` → runs infinitely (until stopped)
  
- **`__loop__()`**: Your main work logic
  - Called automatically by the engine
  - Don't return values from here (use `__result__()` instead)
  - Can access `self.current_loop` to see which iteration you're on
  
- **`__result__()`**: Return final results
  - Called once when process finishes
  - Must return serializable data (strings, numbers, lists, dicts)
  - This is what `get_process_result()` retrieves
  - Uses custom Cerial engine to support a multitude of usually non-serializable objects (NSOs) that you can return as well.

- **Process Names**: Each process gets a unique `self.name` for identification

### When to Use

- **Simple parallel tasks** where you need to repeat work
- **Data processing** where you process items one by one
- **Any CPU-intensive work** that can be broken into iterations

---

## 2. Process Lifecycle Hooks

### Concept Overview

Processes have a rich lifecycle with hooks for setup, work, cleanup, and finalization. This gives you fine-grained control over resource management and allows for clean, organized code.

### Complete Lifecycle

```python
class LifecycleProcess(Process):
    def __init__(self):
        super().__init__(num_loops=2)
        self.data = []
    
    def __preloop__(self):
        # Called BEFORE each __loop__() iteration
        print(f"Setting up for loop {self.current_loop}")
        # Perfect for: opening files, connecting to databases, allocating resources
    
    def __loop__(self):
        # Called FOR each iteration (main work)
        self.data.append(f"work_{self.current_loop}")
        time.sleep(0.1)
    
    def __postloop__(self):
        # Called AFTER each __loop__() iteration
        print(f"Cleaning up after loop {self.current_loop}")
        # Perfect for: saving progress, closing connections, freeing resources
    
    def __onfinish__(self):
        # Called ONCE when entire process is finishing
        print("Process finished!")
        # Perfect for: final cleanup, logging, sending notifications
    
    def __result__(self):
        # Called ONCE to get final result
        return self.data
```

### Execution Order

For a process with `num_loops=3`:

```
0. __init__()
1. __preloop__()   (loop 1)
2. __loop__()      (loop 1)
3. __postloop__()  (loop 1)
4. __preloop__()   (loop 2)
5. __loop__()      (loop 2)
6. __postloop__()  (loop 2)
7. __preloop__()   (loop 3)
8. __loop__()      (loop 3)
9. __postloop__()  (loop 3)
10. __onfinish__()
11. __result__()
```

### Hook Use Cases

|       Hook       |       Best For        | Examples
|------------------|-----------------------|---------------
| `__preloop__()`  | Per-iteration setup   | Open file, start transaction, allocate memory
| `__loop__()`     | Main work             | Process data, make calculations, API calls
| `__postloop__()` | Per-iteration cleanup | Save progress, close connections, log status
| `__onfinish__()` | Final cleanup         | Send completion email, update status, final logging
| `__result__()`   | Return data           | Aggregate results, create summary, format output

### Error Handling in Hooks

Each hook can fail independently and will be caught with specific error types:

- `PreloopError` - Error in `__preloop__()`
- `MainLoopError` - Error in `__loop__()`
- `PostLoopError` - Error in `__postloop__()`

This helps with debugging by showing exactly where failures occur.

---

## 3. Process Configuration

### Concept Overview

`PConfig` gives you fine-grained control over process behavior, timeouts, restart logic, and monitoring. Instead of hardcoding behavior, you can configure processes for different environments and use cases.

### Basic Configuration

```python
config = PConfig(
    join_after=3,      # Stop after 3 loops (overrides num_loops)
    log_loops=True     # Show detailed execution logs
)
```

### Complete Configuration Options

```python
config = PConfig(
    # Termination Control - If neither are set, assumes infinite looping and manual rejoining
    join_in=30.0,           # Auto-terminate after 30 seconds
    join_after=100,         # Auto-terminate after 100 loops
    
    # Error Handling
    crash_restart=True,     # Restart process if it crashes
    max_restarts=3,         # Maximum restart attempts
    
    # Timeouts (for individual operations)
    preloop_timeout=30.0,   # Timeout for __preloop__() 
    loop_timeout=300.0,     # Timeout for __loop__()
    postloop_timeout=60.0,  # Timeout for __postloop__()
    
    # Process Management
    startup_timeout=60.0,   # Timeout for process startup/initialization
    shutdown_timeout=20.0,  # Timeout for graceful shutdown
    
    # Monitoring
    log_loops=True,         # Log each loop iteration
    heartbeat_interval=5.0, # Health check frequency
    resource_monitoring=False # Enable resource usage tracking
)
```

### Configuration Presets

```python
# Quick timeouts for fast processes
config.set_quick_timeouts()
# preloop_timeout=5s, loop_timeout=30s, postloop_timeout=10s

# Long timeouts for slow processes  
config.set_long_timeouts()
# preloop_timeout=120s, loop_timeout=1800s, postloop_timeout=300s

# Disable all timeouts (dangerous!)
config.disable_timeouts()
# All timeouts set to None
```

### Configuration Patterns

**Development/Testing:**
```python
dev_config = PConfig(
    log_loops=True,         # Detailed logging
    crash_restart=False,    # Let crashes happen for debugging
    join_in=10.0           # Short timeout for testing
)
```

**Production:**
```python
prod_config = PConfig(
    crash_restart=True,     # Auto-recover from crashes
    max_restarts=3,         # Limit restart attempts
    log_loops=False,        # Reduce log noise
    resource_monitoring=True # Track performance
)
```

**Long-Running Tasks:**
```python
batch_config = PConfig(
    join_in=3600.0,        # 1 hour timeout
    set_long_timeouts(),   # Generous operation timeouts
    heartbeat_interval=30.0 # Less frequent health checks
)
```

### When Configuration Overrides Process Settings

- `num_loops` overrides `join_after`
- `join_in` can terminate before looping completes
- Timeouts apply to individual operations, not total runtime (loop n's `__preloop__()` instead of all preloops)

---

## 4. Error Handling & Recovery

### Concept Overview

Traditional multiprocessing leaves you to handle crashes manually. Suitkaise provides automatic crash detection, detailed error reporting, and configurable restart logic, making your applications robust by default.

### Automatic Error Detection

```python
class ErrorProneProcess(Process):
    def __init__(self):
        super().__init__(num_loops=5)
        self.attempts = 0
    
    def __loop__(self):
        self.attempts += 1
        if self.attempts <= 2:  # Fail first 2 times
            raise ValueError(f"Oops! Attempt {self.attempts}")
        print(f"Success on attempt {self.attempts}")
```

The engine automatically:
1. **Catches the error**
2. **Logs detailed information** (error type, location, stack trace)
3. **Updates process status** to `CRASHED`
4. **Triggers restart logic** (if enabled)

### Restart Configuration

```python
restart_config = PConfig(
    crash_restart=True,     # Enable automatic restart
    max_restarts=3          # Try up to 3 restarts
)
```

### Restart Behavior

When a process crashes:

1. **First crash**: Status → `CRASHED`, restart attempt 1
2. **Second crash**: Status → `CRASHED`, restart attempt 2  
3. **Third crash**: Status → `CRASHED`, restart attempt 3
4. **Fourth crash**: Status → `CRASHED`, **no more restarts** (limit reached)

Each restart is a **completely new process** with fresh memory and state.

### Error Types & Locations

The engine provides specific error types for each lifecycle phase:

```python
try:
    # Process execution
    pass
except PreloopError as e:
    print(f"Setup failed: {e}")
except MainLoopError as e:
    print(f"Main work failed: {e}")
except PostLoopError as e:
    print(f"Cleanup failed: {e}")
```

Each error includes:
- **Original exception** and message
- **Process name** that failed
- **Loop number** where failure occurred
- **Full stack trace** for debugging

### Timeout Handling

Different timeout types for different operations:

```python
config = PConfig(
    preloop_timeout=30.0,   # __preloop__() must complete in 30s
    loop_timeout=300.0,     # __loop__() must complete in 5 minutes
    postloop_timeout=60.0   # __postloop__() must complete in 1 minute
)
```

Timeouts generate specific timeout errors:
- `PreloopTimeoutError`
- `MainLoopTimeoutError` 
- `PostLoopTimeoutError`

### Production Error Strategies

**Fail Fast (Development):**
```python
config = PConfig(crash_restart=False)  # Let errors bubble up
```

**Resilient (Production):**
```python
config = PConfig(
    crash_restart=True,
    max_restarts=3,
    set_long_timeouts()  # Be generous with timeouts
)
```

**Critical Systems:**
```python
config = PConfig(
    crash_restart=True,
    max_restarts=10,      # Many restart attempts
    heartbeat_interval=1.0 # Frequent health checks
)
```

---

## 5. Timing & Performance Measurement

### Concept Overview

Suitkaise includes built-in timing capabilities that let you measure performance without external tools. You can time different parts of your process lifecycle and access timing data programmatically.

### Basic Timing Setup

```python
class TimedProcess(Process):
    def __init__(self):
        super().__init__(num_loops=3)
        
        # Configure what to time
        self.start_timer_before_loop()  # Start timing before __loop__()
        self.end_timer_after_loop()     # End timing after __loop__()
        
        self.times = []
    
    def __loop__(self):
        time.sleep(0.1)  # Simulate work
    
    def __postloop__(self):
        # Access timing after each loop
        loop_time = self.last_loop_time
        self.times.append(loop_time)
        print(f"Loop {self.current_loop} took {loop_time:.3f}s")
```

### Timing Configuration Options

You can time different portions of your process lifecycle:

```python
# Time just the main work (DEFAULT)
self.start_timer_before_loop()
self.end_timer_after_loop()

# Time just setup + work
self.start_timer_before_preloop()
self.end_timer_after_loop()

# Time setup + work + cleanup (less intuitive)
self.start_timer_before_preloop()
self.end_timer_after_postloop()

# Time work + cleanup (much less intuitive)
self.start_timer_before_loop()
self.end_timer_after_postloop()
```

### Accessing Timing Data

**During Execution:**
```python
def __postloop__(self):
    # Get timing for the loop that just completed
    duration = self.last_loop_time
    print(f"This loop took {duration:.3f} seconds")
```

**After Completion:**
```python
# Get process statistics
stats = xp.get_process_stats("process_name")
print(f"Average loop time: {stats['average_loop_time']:.3f}s")
print(f"Fastest loop: {stats['fastest_loop']:.3f}s") 
print(f"Slowest loop: {stats['slowest_loop']:.3f}s")
```

### Performance Monitoring Patterns

**Real-time Monitoring:**
```python
def __postloop__(self):
    if self.current_loop % 100 == 0:  # Every 100 loops
        avg_time = sum(self.recent_times[-100:]) / 100
        print(f"Recent average: {avg_time:.3f}s/loop")
```

**Adaptive Performance:**
```python
def __postloop__(self):
    if self.last_loop_time > 1.0:  # If loop took too long
        print("Performance degraded, reducing batch size")
        self.batch_size = max(1, self.batch_size // 2)
```

**Performance Targets:**
```python
def __loop__(self):
    start_time = time.time()
    
    # Do work
    self.process_data()
    
    # Ensure minimum loop time for rate limiting
    elapsed = time.time() - start_time
    if elapsed < self.min_loop_time:
        time.sleep(self.min_loop_time - elapsed)
```

### Timing Use Cases

|               Pattern               |     Use Case      | Example 
|-------------------------------------|-------------------|----------------
| `before_loop` → `after_loop`        | Core performance  | Time just the work
| `before_preloop` → `after_postloop` | Full cycle time   | Time setup + work + cleanup
| `before_preloop` → `after_loop`     | Work + setup time | Time preparation and execution
| No timing                           | Simple processes  | When performance doesn't matter

---

## 6. Process Pools

### Concept Overview

Process pools manage multiple worker processes for batch processing. Instead of manually creating and coordinating processes, pools handle worker lifecycle, task distribution, and result collection automatically.

### Pool Modes

**Async Mode (DEFAULT):**
- Tasks start as workers become available
- Good for: Mixed task durations, streaming work

**Parallel Mode:**
- Tasks start and finish in synchronized batches
- Good for: Uniform tasks, coordinated processing

### Basic Pool Usage

```python
# still building from Process class
class PoolWorker(Process):
    def __init__(self, task_id):
        super().__init__(num_loops=1)
        self.task_id = task_id
    
    def __loop__(self):
        time.sleep(0.2)  # Simulating work
    
    def __result__(self):
        return f"Task {self.task_id} completed"

# Create and use pool
with ProcessPool(size=3, mode=PoolMode.ASYNC) as pool:
    # Submit multiple tasks
    for i in range(5):
        worker = PoolWorker(i)
        pool.submit_process(f"task_{i}", worker)
    
    # Get all results when complete
    results = pool.get_all_results()
    print(f"Completed {len(results)} tasks")
```

### Pool Architecture

```
ProcessPool (size=3)
├── Worker 1 ──> Task A ──> Task D
├── Worker 2 ──> Task B ──> Task E  
└── Worker 3 ──> Task C ──> (idle)
```

**Benefits:**
- **Automatic load balancing** - tasks distributed to available workers
- **Resource management** - fixed number of processes, controlled resource usage
- **Error isolation** - one task failure doesn't affect others
- **Parallel execution** - multiple tasks run simultaneously

### Async vs Parallel Mode

**Async Mode:**
```python
pool = ProcessPool(size=4, mode=PoolMode.ASYNC)
# Tasks start immediately when workers available
# Good for: Variable task durations, real-time processing
```

**Parallel Mode:**
```python
pool = ProcessPool(size=4, mode=PoolMode.PARALLEL)
# Tasks start in batches of pool size
# Good for: Synchronized processing, uniform workloads
```

### Task Submission Patterns

**Process-based tasks:**
```python
pool.submit_process("task_name", MyProcess())
```

**Multiple submissions:**
```python
tasks = [MyProcess(data) for data in datasets]
for i, task in enumerate(tasks):
    pool.submit_process(f"task_{i}", task)
```

**Multi-type submissions:**
```python
tasks = [MyProcess(data) for data in datasets]
for i, task in enumerate(tasks):
    pool.submit_process(f"task_{i}", task)

# when tasks are done, run this other set of tasks
tasks = [MyOtherProcess(data) for data in datasets]
for i, task in enumerate(tasks):
    pool.submit_process(f"task_{i}", task)
```

**Dynamic submission:**
```python
with ProcessPool(size=4) as pool:
    for item in data_stream:
        worker = DataProcessor(item)
        pool.submit_process(f"process_{item.id}", worker)
    
    results = pool.get_all_results()
```

### Error Handling in Pools

Pools provide comprehensive error handling:

```python
try:
    results = pool.get_all_results()
    # All tasks succeeded
except PoolTaskError as e:
    # Some tasks failed
    print(f"{len(e.failed_tasks)} tasks failed")
    for task in e.failed_tasks:
        print(f"Task {task['key']} failed: {task['error']}")
```

**Individual task results:**
```python
# get result by worker name
results = pool.get_result("worker_name")

# get result by order of submission
results = pool.get_result(3) # fourth submitted task
```

### Pool Performance Patterns

**CPU-bound tasks:**
```python
# Match pool size to CPU cores
import os
pool_size = os.cpu_count()
```

**I/O-bound tasks:**
```python
# Can use more workers than CPU cores
pool_size = os.cpu_count() * 2
```

**Memory-intensive tasks:**
```python
# Smaller pool to control memory usage
pool_size = max(1, os.cpu_count() // 2)
```

---

## 7. Function-Based Tasks

### Concept Overview

For simple tasks that don't need the full process lifecycle, you can submit functions directly to pools. This is perfect for quick calculations, data transformations, or any stateless work.

### Basic Function Tasks

```python
def simple_function(x, multiplier=2):
    time.sleep(0.1)  # Simulate work
    return x * multiplier

with ProcessPool(size=2) as pool:
    # Submit function tasks
    for i in range(4):
        pool.submit_function(
            key=f"calc_{i}",
            func=simple_function,
            args=(i,),
            kwargs={"multiplier": 3}
        )
    
    results = pool.get_all_results()
    for result in results:
        print(f"{result.key}: {result.result}")
```

### Function vs Process Comparison

**Functions - Best for:**
- ✅ Simple, stateless calculations
- ✅ Data transformations
- ✅ Quick API calls
- ✅ Mathematical operations
- ✅ One-shot tasks

**Processes - Best for:**
- ✅ Complex workflows with setup/cleanup
- ✅ Stateful operations
- ✅ Resource management (files, connections)
- ✅ Multi-step processing
- ✅ Performance monitoring

### Function Task Patterns

**Data Processing Pipeline:**
```python
def clean_data(raw_data):
    return raw_data.strip().lower()

def validate_data(clean_data):
    return len(clean_data) > 0

def transform_data(valid_data):
    return {"processed": valid_data, "length": len(valid_data)}

# Process pipeline
with ProcessPool(size=4) as pool:
    # Stage 1: Clean
    for i, data in enumerate(raw_dataset):
        pool.submit_function(f"clean_{i}", clean_data, args=(data,))
    
    clean_results = pool.get_all_results()
    # Continue with stages 2 and 3...
```

**Mathematical Operations:**
```python
import math

def calculate_stats(numbers):
    return {
        "mean": sum(numbers) / len(numbers),
        "std": math.sqrt(sum((x - mean)**2 for x in numbers) / len(numbers)),
        "min": min(numbers),
        "max": max(numbers)
    }

# Parallel statistics
with ProcessPool(size=4) as pool:
    data_chunks = [dataset[i:i+1000] for i in range(0, len(dataset), 1000)]
    
    for i, chunk in enumerate(data_chunks):
        pool.submit_function(f"stats_{i}", calculate_stats, args=(chunk,))
    
    results = pool.get_all_results()
```

### Function Configuration

Functions use `QPConfig` (Quick Process Config) instead of full `PConfig`:

```python
quick_config = QPConfig(
    join_in=30.0,           # 30 second timeout
    function_timeout=25.0,  # Function must complete in 25s
    crash_restart=False     # Usually don't restart functions
)

pool.submit_function(
    "long_calc", 
    complex_calculation, 
    args=(large_dataset,),
    config=quick_config
)
```

### Function Error Handling

Functions can fail just like processes:

```python
def risky_function(data):
    if not data:
        raise ValueError("No data provided!")
    return process(data)

try:
    results = pool.get_all_results()
except PoolTaskError as e:
    # Handle function failures
    for failed_task in e.failed_tasks:
        print(f"Function {failed_task['key']} failed: {failed_task['error']}")
```

### When to Use Functions vs Processes

|          Scenario          | Use Functions | Use Processes 
|----------------------------|---------------|----------------
| Simple calculation         | ✅            | ❌ 
| File processing with setup | ❌            | ✅ 
| API calls                  | ✅            | ❌ 
| Database operations        | ❌            | ✅ 
| Stateless transforms       | ✅            | ❌ 
| Multi-step workflows       | ❌            | ✅ 
| Need timing/monitoring     | ❌            | ✅ 
| Resource management        | ❌            | ✅ 

---

## 8. Subprocess Management

### Concept Overview

Subprocesses allow you to create processes within processes, enabling complex hierarchical workflows. This is perfect for divide-and-conquer algorithms, parallel analysis, or any scenario where you need coordinated sub-tasks.

### Basic Subprocess Pattern

```python
class MainProcess(Process):
    def __init__(self):
        super().__init__(num_loops=1)
        self.subprocess_result = None
    
    def __loop__(self):
        # Create subprocess within main process
        with SubProcessing() as sub_mgr:
            sub_process = SimpleProcess()  # Any process class
            sub_mgr.create_process("sub_task", sub_process)
            sub_mgr.join_all()
            self.subprocess_result = sub_mgr.get_subprocess_result("sub_task")
    
    def __result__(self):
        return f"Main process got: {self.subprocess_result}"
```

### Subprocess Architecture

```
Main Process
└── SubProcessing Manager
    ├── Subprocess A
    ├── Subprocess B  
    └── Subprocess C
```

**Key Features:**
- **Automatic coordination** - main process waits for subprocesses
- **Isolated execution** - subprocess failures don't crash main process
- **Result aggregation** - collect results from all subprocesses
- **Resource cleanup** - automatic cleanup when main process finishes

### Multi-Level Analysis Example

```python
class DataAnalyzer(Process):
    def __init__(self, dataset):
        super().__init__(num_loops=1)
        self.dataset = dataset
        self.analysis_results = {}
    
    def __loop__(self):
        with SubProcessing() as sub_mgr:
            # Create multiple analysis subprocesses
            stats_analyzer = StatisticalAnalyzer(self.dataset)
            pattern_analyzer = PatternAnalyzer(self.dataset)
            
            sub_mgr.create_process("stats", stats_analyzer)
            sub_mgr.create_process("patterns", pattern_analyzer)
            
            # Wait for all analyses
            sub_mgr.join_all()
            
            # Collect results
            self.analysis_results["statistics"] = sub_mgr.get_subprocess_result("stats")
            self.analysis_results["patterns"] = sub_mgr.get_subprocess_result("patterns")
    
    def __result__(self):
        return self.analysis_results

class StatisticalAnalyzer(Process):
    def __init__(self, data):
        super().__init__(num_loops=len(data))
        self.data = data
        self.stats = {"sum": 0, "count": 0}
    
    def __loop__(self):
        value = self.data[self.current_loop - 1]
        self.stats["sum"] += value
        self.stats["count"] += 1
    
    def __result__(self):
        return {
            "mean": self.stats["sum"] / self.stats["count"],
            "total": self.stats["sum"]
        }
```

### Subprocess Coordination Patterns

**Parallel Analysis:**
```python
def __loop__(self):
    with SubProcessing() as sub_mgr:
        # Split data into chunks for parallel processing
        chunk_size = len(self.data) // 4
        
        for i in range(4):
            start = i * chunk_size
            end = start + chunk_size if i < 3 else len(self.data)
            chunk = self.data[start:end]
            
            processor = ChunkProcessor(chunk)
            sub_mgr.create_process(f"chunk_{i}", processor)
        
        sub_mgr.join_all()
        
        # Aggregate results from all chunks
        self.results = []
        for i in range(4):
            chunk_result = sub_mgr.get_subprocess_result(f"chunk_{i}")
            self.results.extend(chunk_result)
```

**Sequential Pipeline:**
```python
def __loop__(self):
    with SubProcessing() as sub_mgr:
        # Stage 1: Data cleaning
        cleaner = DataCleaner(self.raw_data)
        sub_mgr.create_process("clean", cleaner)
        sub_mgr.join_process("clean")
        clean_data = sub_mgr.get_subprocess_result("clean")
        
        # Stage 2: Data validation  
        validator = DataValidator(clean_data)
        sub_mgr.create_process("validate", validator)
        sub_mgr.join_process("validate")
        valid_data = sub_mgr.get_subprocess_result("validate")
        
        # Stage 3: Data transformation
        transformer = DataTransformer(valid_data)
        sub_mgr.create_process("transform", transformer)
        sub_mgr.join_all()
        
        self.final_data = sub_mgr.get_subprocess_result("transform")
```

### Nesting Limitations

Suitkaise prevents infinite nesting for safety:

- **Depth 0**: Main processes (in `CrossProcessing`)
- **Depth 1**: Subprocesses (in `SubProcessing`)
- **Depth 2**: Sub-subprocesses (maximum depth)

Trying to create deeper nesting will raise an error.

### Subprocess Error Handling

Subprocess failures are isolated:

```python
def __loop__(self):
    with SubProcessing() as sub_mgr:
        # Some subprocesses might fail
        for i in range(5):
            processor = RiskyProcessor(data[i])
            sub_mgr.create_process(f"risky_{i}", processor)
        
        sub_mgr.join_all()
        
        # Check which succeeded
        self.successful_results = []
        for i in range(5):
            try:
                result = sub_mgr.get_subprocess_result(f"risky_{i}")
                if result is not None:
                    self.successful_results.append(result)
            except Exception:
                print(f"Subprocess risky_{i} failed")
```

### When to Use Subprocesses

**Good Use Cases:**
- ✅ **Divide and conquer** - split large problems into smaller parts
- ✅ **Parallel analysis** - multiple analyses of same data
- ✅ **Multi-stage pipelines** - sequential processing stages
- ✅ **Fault isolation** - separate risky operations
- ✅ **Resource coordination** - manage multiple resource-intensive tasks

**Avoid When:**
- ❌ **Simple parallel tasks** - use `ProcessPool` instead
- ❌ **Independent operations** - use multiple main processes
- ❌ **Deep nesting** - flatten hierarchy if possible

---

## 9. Multiple Process Coordination

### Concept Overview

Running multiple processes simultaneously is one of the most powerful features of Suitkaise. The `CrossProcessing` manager handles coordination, monitoring, and result collection across all your processes automatically.

### Basic Multiple Process Pattern

```python
class Worker(Process):
    def __init__(self, worker_id):
        super().__init__(num_loops=2)
        self.worker_id = worker_id
        self.work_done = 0
    
    def __loop__(self):
        self.work_done += 1
        print(f"Worker {self.worker_id} doing work {self.work_done}")
        time.sleep(0.1)
    
    def __result__(self):
        return f"Worker {self.worker_id} completed {self.work_done} tasks"

with CrossProcessing() as xp:
    # Create multiple workers
    for i in range(3):
        worker = Worker(i)
        xp.create_process(f"worker_{i}", worker)
    
    # Wait for all to complete
    xp.join_all()
    
    # Collect all results
    for i in range(3):
        result = xp.get_process_result(f"worker_{i}")
        print(f"Result: {result}")
```

### Process Coordination Patterns

**Parallel Data Processing:**
```python
class DataProcessor(Process):
    def __init__(self, data_chunk, chunk_id):
        super().__init__(num_loops=len(data_chunk))
        self.data_chunk = data_chunk
        self.chunk_id = chunk_id
        self.processed_items = []
    
    def __loop__(self):
        item = self.data_chunk[self.current_loop - 1]
        processed = self.process_item(item)
        self.processed_items.append(processed)
    
    def __result__(self):
        return {
            "chunk_id": self.chunk_id,
            "items_processed": len(self.processed_items),
            "results": self.processed_items
        }

# Split data across multiple processes
with CrossProcessing() as xp:
    chunk_size = len(large_dataset) // 4
    
    for i in range(4):
        start = i * chunk_size
        end = start + chunk_size if i < 3 else len(large_dataset)
        chunk = large_dataset[start:end]
        
        processor = DataProcessor(chunk, i)
        xp.create_process(f"processor_{i}", processor)
    
    xp.join_all()
    
    # Aggregate results from all processors
    all_results = []
    for i in range(4):
        chunk_result = xp.get_process_result(f"processor_{i}")
        all_results.extend(chunk_result["results"])
```

**Producer-Consumer Pattern:**
```python
class DataProducer(Process):
    def __init__(self, num_items):
        super().__init__(num_loops=num_items)
        self.produced_items = []
    
    def __loop__(self):
        item = f"item_{self.current_loop}"
        self.produced_items.append(item)
        time.sleep(0.05)  # Simulate production time
    
    def __result__(self):
        return self.produced_items

class DataConsumer(Process):
    def __init__(self, consumer_id):
        super().__init__(num_loops=100)  # Will be stopped by config
        self.consumer_id = consumer_id
        self.consumed_count = 0
    
    def __loop__(self):
        # Simulate consuming data
        time.sleep(0.1)
        self.consumed_count += 1
    
    def __result__(self):
        return f"Consumer {self.consumer_id} processed {self.consumed_count} items"

# Different configurations for different roles
producer_config = PConfig(log_loops=True)
consumer_config = PConfig(join_in=5.0)  # Stop consumers after 5 seconds

with CrossProcessing() as xp:
    # One producer
    producer = DataProducer(50)
    xp.create_process("producer", producer, producer_config)
    
    # Multiple consumers
    for i in range(3):
        consumer = DataConsumer(i)
        xp.create_process(f"consumer_{i}", consumer, consumer_config)
    
    xp.join_all()
```

### Process Status Monitoring

```python
with CrossProcessing() as xp:
    # Create processes
    for i in range(5):
        worker = LongRunningWorker(i)
        xp.create_process(f"worker_{i}", worker)
    
    # Monitor progress
    while True:
        process_list = xp.list_processes()
        
        running_count = sum(1 for p in process_list.values() if p['is_alive'])
        print(f"Running processes: {running_count}/5")
        
        if running_count == 0:
            break
            
        time.sleep(2)  # Check every 2 seconds
    
    print("All processes completed!")
```

### Error Handling with Multiple Processes

```python
with CrossProcessing() as xp:
    # Mix of reliable and unreliable processes
    reliable_config = PConfig(crash_restart=False)
    unreliable_config = PConfig(crash_restart=True, max_restarts=2)
    
    # Reliable processes
    for i in range(3):
        worker = ReliableWorker(i)
        xp.create_process(f"reliable_{i}", worker, reliable_config)
    
    # Unreliable processes with restart
    for i in range(2):
        worker = UnreliableWorker(i)
        xp.create_process(f"unreliable_{i}", worker, unreliable_config)
    
    xp.join_all()
    
    # Check which processes succeeded
    for key in xp.list_processes():
        status = xp.get_process_status(key)
        result = xp.get_process_result(key)
        
        if status == PStatus.FINISHED and result:
            print(f"✅ {key}: {result}")
        else:
            print(f"❌ {key}: Failed with status {status}")
```

### Performance Optimization Patterns

**CPU-Bound Work:**
```python
import os

# Match process count to CPU cores
num_processes = os.cpu_count()

with CrossProcessing() as xp:
    for i in range(num_processes):
        worker = CPUIntensiveWorker(i)
        xp.create_process(f"cpu_worker_{i}", worker)
    
    xp.join_all()
```

**I/O-Bound Work:**
```python
# Can use more processes than CPU cores for I/O
num_processes = os.cpu_count() * 2

with CrossProcessing() as xp:
    for i in range(num_processes):
        worker = IOBoundWorker(i)
        xp.create_process(f"io_worker_{i}", worker)
    
    xp.join_all()
```

**Memory-Constrained Work:**
```python
# Fewer processes to control memory usage
num_processes = max(2, os.cpu_count() // 2)

with CrossProcessing() as xp:
    for i in range(num_processes):
        worker = MemoryIntensiveWorker(i)
        xp.create_process(f"memory_worker_{i}", worker)
    
    xp.join_all()
```

### Coordination Best Practices

1. **Use meaningful process names** - helps with debugging and monitoring
2. **Configure processes appropriately** - different configs for different roles
3. **Monitor process status** - check progress on long-running tasks
4. **Handle partial failures** - some processes might fail while others succeed
5. **Match process count to workload** - CPU-bound vs I/O-bound vs memory-bound
6. **Use consistent result formats** - makes aggregation easier

---

## 10. Process Control & Flow Management

### Concept Overview

Processes don't always need to run to completion. Suitkaise provides control methods that let you stop processes gracefully, handle dynamic conditions, and manage process flow based on runtime conditions.

### Basic Process Control

```python
class ControllableProcess(Process):
    def __init__(self):
        super().__init__(num_loops=10)  # Would normally run 10 times
        self.loops_completed = 0
    
    def __loop__(self):
        self.loops_completed += 1
        print(f"Completed loop {self.loops_completed}")
        
        # Conditional stopping
        if self.loops_completed == 3:
            print("Requesting graceful stop...")
            self.rejoin()  # Stop after current loop completes
        
        time.sleep(0.1)
    
    def __result__(self):
        return f"Stopped after {self.loops_completed} loops"
```

### Control Methods

**`rejoin()` - Graceful Stop:**
```python
def __loop__(self):
    if some_condition:
        self.rejoin()  # Finish current loop, then stop
    # Current loop continues to completion
```

**`skip_and_rejoin()` - Immediate Stop:**
```python
def __loop__(self):
    if emergency_condition:
        self.skip_and_rejoin()  # Stop immediately, skip to __onfinish__()
    # Code after this won't execute
```

**`instakill()` - Force Termination:**
```python
def __loop__(self):
    if critical_error:
        self.instakill()  # Terminate immediately, no cleanup
    # Process dies immediately
```

### Control Method Behavior

| Method | Current Loop | `__postloop__()` | `__onfinish__()` | `__result__()` |
|--------|--------------|------------------|------------------|----------------|
| `rejoin()` | ✅ Completes | ✅ Called | ✅ Called | ✅ Called |
| `skip_and_rejoin()` | ❌ Stops | ❌ Skipped | ✅ Called | ✅ Called |
| `instakill()` | ❌ Stops | ❌ Skipped | ❌ Skipped | ❌ Skipped |

### Dynamic Flow Control

**Condition-Based Stopping:**
```python
class DataProcessor(Process):
    def __init__(self, target_accuracy=0.95):
        super().__init__(num_loops=1000)  # Maximum iterations
        self.target_accuracy = target_accuracy
        self.current_accuracy = 0.0
        self.iterations = 0
    
    def __loop__(self):
        # Do processing work
        self.iterations += 1
        self.current_accuracy = self.calculate_accuracy()
        
        # Stop early if target reached
        if self.current_accuracy >= self.target_accuracy:
            print(f"Target accuracy {self.target_accuracy} reached!")
            self.rejoin()
    
    def __result__(self):
        return {
            "iterations": self.iterations,
            "final_accuracy": self.current_accuracy,
            "target_reached": self.current_accuracy >= self.target_accuracy
        }
```

**Resource-Based Control:**
```python
class ResourceAwareProcess(Process):
    def __init__(self):
        super().__init__(num_loops=None)  # Run indefinitely
        self.processed_items = 0
    
    def __loop__(self):
        # Check system resources
        memory_usage = self.get_memory_usage()
        cpu_usage = self.get_cpu_usage()
        
        if memory_usage > 0.90:  # 90% memory usage
            print("High memory usage, stopping gracefully...")
            self.rejoin()
        elif cpu_usage > 0.95:  # 95% CPU usage
            print("High CPU usage, emergency stop...")
            self.skip_and_rejoin()
        
        # Normal processing
        self.process_next_item()
        self.processed_items += 1
    
    def __result__(self):
        return f"Processed {self.processed_items} items before stopping"
```

**External Signal Control:**
```python
class SignalControlledProcess(Process):
    def __init__(self, control_file="stop_signal.txt"):
        super().__init__(num_loops=None)
        self.control_file = control_file
        self.work_completed = 0
    
    def __loop__(self):
        # Check for external stop signal
        if os.path.exists(self.control_file):
            print("External stop signal received")
            os.remove(self.control_file)  # Clean up
            self.rejoin()
        
        # Do work
        self.do_work()
        self.work_completed += 1
        time.sleep(1)
    
    def __result__(self):
        return f"Completed {self.work_completed} work units"

# External control: touch stop_signal.txt to stop the process
```

### Flow Control Patterns

**Early Success:**
```python
def __loop__(self):
    result = self.attempt_operation()
    
    if result.success:
        print("Operation succeeded early!")
        self.success_result = result
        self.rejoin()  # Stop, we got what we needed
    
    # Continue trying if not successful
```

**Error Threshold:**
```python
def __loop__(self):
    try:
        self.risky_operation()
        self.error_count = 0  # Reset on success
    except Exception as e:
        self.error_count += 1
        
        if self.error_count >= self.max_errors:
            print(f"Too many errors ({self.error_count}), stopping...")
            self.skip_and_rejoin()
```

**Time-Based Control:**
```python
def __loop__(self):
    if time.time() - self.start_time > self.max_runtime:
        print("Maximum runtime exceeded")
        self.rejoin()
    
    # Regular work
    self.do_work()
```

**Progress-Based Control:**
```python
def __loop__(self):
    progress = self.current_loop / self.total_work
    
    if progress >= 0.8:  # 80% complete
        print("80% complete, that's enough for now")
        self.rejoin()
    
    self.do_work()
```

### Control in Multi-Process Scenarios

**Coordinated Stopping:**
```python
# Use shared file or database to coordinate stops
class CoordinatedWorker(Process):
    def __loop__(self):
        # Check if any worker has signaled stop
        if self.check_global_stop_signal():
            self.rejoin()
        
        self.do_work()
        
        # Signal stop to other workers if condition met
        if self.should_signal_stop():
            self.set_global_stop_signal()
            self.rejoin()
```

**Leader-Follower Pattern:**
```python
class LeaderProcess(Process):
    def __loop__(self):
        if self.work_complete():
            # Signal followers to stop
            self.write_stop_signal("followers_stop.txt")
            self.rejoin()

class FollowerProcess(Process):
    def __loop__(self):
        if os.path.exists("followers_stop.txt"):
            self.rejoin()
        
        self.do_follower_work()
```

### Best Practices for Process Control

1. **Use `rejoin()` for normal stopping** - ensures cleanup happens
2. **Reserve `skip_and_rejoin()` for urgent situations** - skips cleanup
3. **Avoid `instakill()` unless absolutely necessary** - no cleanup at all
4. **Check conditions early in `__loop__()`** - minimize wasted work
5. **Clean up external resources** - files, connections, etc.
6. **Log why processes are stopping** - helps with debugging
7. **Handle control gracefully** - don't leave systems in bad states

---

## Summary

The Suitkaise multiprocessing engine provides a comprehensive, intuitive framework for parallel processing that eliminates the complexity traditionally associated with multiprocessing while providing enterprise-grade features like automatic error handling, restart capabilities, and performance monitoring.

### Key Design Principles

1. **Simplicity** - Inherit from `Process`, implement `__loop__()`, and you're done
2. **Robustness** - Automatic error handling, crash detection, and restart logic
3. **Flexibility** - Processes, pools, subprocesses, and functions all work together
4. **Monitoring** - Built-in timing, statistics, and performance measurement
5. **Control** - Fine-grained control over process lifecycle and flow

### When to Use What

- **Simple parallel tasks** → Process Pools with functions
- **Complex workflows** → Process classes with lifecycle hooks  
- **Hierarchical processing** → Subprocesses
- **Resource-intensive work** → Multiple processes with CrossProcessing
- **Critical systems** → Error handling with automatic restart
- **Performance optimization** → Built-in timing and monitoring

The engine scales from simple parallel calculations to complex data processing pipelines, making it suitable for everything from data science workloads to production systems requiring high reliability and performance.