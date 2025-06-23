# SKTime - Comprehensive Time & Performance Utilities

SKTime is a powerful Python library that makes timing, performance measurement, and date/time handling incredibly easy. Whether you're timing a single function or analyzing performance across multiple processes, SKTime has you covered.

## 🚀 What Can SKTime Do?

- ⏱️ **Time anything** - Functions, code blocks, or long-running processes
- 📊 **Automatic performance tracking** - Just add a decorator and get detailed stats
- 🔄 **Cross-process timing** - Share timing data between different Python processes
- 📅 **Smart date formatting** - Turn timestamps into human-readable text
- 🎯 **Rate limiting** - Control how often functions can be called
- 📈 **Performance analysis** - Find your slowest functions and bottlenecks
- 💾 **Persistent timing data** - Keep timing stats even after your program restarts

## Quick Start

### Installation
```python
# SKTime is part of the Suitkaise package
from suitkaise.sktime import Timer, timethis, fmttime, fmtdate
```

### Time a Code Block (Easiest Way)
```python
from suitkaise.sktime import Timer, fmttime

# Automatic timing with context manager
with Timer() as timer:
    # Your code here
    expensive_calculation()
    data_processing()

# Get results
print(f"Operation took: {fmttime(timer.elapsed_time)}")
# Output: "Operation took: 2.34s"
```

### Time a Function Automatically
```python
from suitkaise.sktime import timethis

@timethis(print_result=True)
def slow_function():
    import time
    time.sleep(1)
    return "done"

result = slow_function()
# Output: ⏱️ slow_function() took 1.00s
```

## 📚 Core Features

### 1. Basic Timing Functions

```python
from suitkaise.sktime import now, sleep, elapsed, fmttime

# Get current timestamp
start = now()

# Sleep for a while  
sleep(0.5)  # 500 milliseconds

# Calculate elapsed time
end = now()
duration = elapsed(start, end)

# Format it nicely
print(f"That took {fmttime(duration)}")  # "That took 500ms"
```

### 2. Timer Class - The Workhorse

The Timer class is your main tool for timing anything:

```python
from suitkaise.sktime import Timer

# Method 1: Context Manager (Recommended)
with Timer() as timer:
    do_work()
    timer.lap("phase 1")  # Record a checkpoint
    do_more_work()
    timer.lap("phase 2")
    
print(f"Total time: {timer.elapsed_time:.2f}s")

# Method 2: Manual Control
timer = Timer()
timer.start()
do_work()
timer.pause()    # Pause timing
take_a_break()   # This time won't count
timer.resume()   # Continue timing
do_more_work()
duration = timer.stop()
```

### 3. Lap Timing for Multi-Stage Operations

```python
with Timer() as timer:
    # Stage 1
    load_data()
    timer.lap("data loading")
    
    # Stage 2  
    process_data()
    timer.lap("processing")
    
    # Stage 3
    save_results()
    timer.lap("saving")

# Get detailed breakdown
for lap in timer.get_laps():
    print(f"{lap.name}: {fmttime(lap.lap_time)}")

# Output:
# data loading: 1.23s
# processing: 4.56s  
# saving: 789ms
```

## 🎯 Automatic Function Timing

### @timethis - The Swiss Army Knife

The `@timethis` decorator is incredibly flexible:

```python
from suitkaise.sktime import timethis

# Basic usage - stores timing on function
@timethis()
def calculate_pi(precision):
    # ... complex calculation ...
    return 3.14159

result = calculate_pi(1000)
last_time = calculate_pi.get_last_timing()
print(f"Calculation took: {last_time['duration']:.3f}s")

# Track multiple calls with statistics
@timethis(track_calls=True, print_result=True)
def api_call():
    import time
    time.sleep(0.1)  # Simulate API call
    return "response"

# Call it multiple times
for i in range(5):
    api_call()

# Get comprehensive stats
stats = api_call.get_timing_stats()
print(f"Average time: {stats['avg_time']:.3f}s")
print(f"Total calls: {stats['call_count']}")
print(f"Success rate: {stats['success_rate']:.1%}")
```

### Store Results Globally (Cross-Process!)

```python
# Store timing data in global storage that all processes can access
@timethis(store_in_global="api_performance", track_calls=True)
def important_api_call():
    return make_api_request()

# Call from any process
important_api_call()

# Access from another process or script
from suitkaise.sktime import get_global_timing
timing_data = get_global_timing("api_performance")
print(f"API called {len(timing_data['timings'])} times")
```

### Other Useful Decorators

```python
# Print timing automatically
@time_function
def quick_task():
    return "done"

# Limit how often a function can be called
@rate_limiter(max_calls_per_second=2.0)
def rate_limited_api():
    return "response"

# Track detailed call statistics
@profile_function_calls(print_stats=True)
def monitored_function():
    return "result"
```

## 📊 Performance Analysis & Registries

### Timing Registries - Organize Your Performance Data

```python
from suitkaise.sktime import get_timing_registry

# Get named registries for different parts of your app
api_registry = get_timing_registry("api_calls")
db_registry = get_timing_registry("database")

# Register functions with specific registries
@timethis(callback=api_registry.record_timing)
def api_endpoint():
    return "response"

@timethis(callback=db_registry.record_timing)  
def database_query():
    return "data"

# Call functions to build up timing data
for i in range(10):
    api_endpoint()
    database_query()

# Analyze performance
api_registry.print_summary()
# 📊 Timing Registry Summary - api_calls
# ==================================================
# Unique functions: 1
# Total function calls: 10
# Total duration: 1.23s
# Average duration: 123ms

# Find problematic functions
slow_functions = api_registry.find_functions(
    lambda name, timings: statistics.mean([t['duration'] for t in timings]) > 0.1
)

# Get top functions by different metrics
busiest = api_registry.get_top_functions(limit=5, sort_by="call_count")
slowest = api_registry.get_top_functions(limit=5, sort_by="avg_time")
```

### Cross-Process Shared Timers

```python
from suitkaise.sktime import create_shared_timer

# Process 1: Start a long-running operation
shared_timer = create_shared_timer("batch_job")
shared_timer.start()
# ... do work ...
shared_timer.lap("phase 1 complete")

# Process 2: Monitor progress from anywhere
monitor = create_shared_timer("batch_job")
status = monitor.get_shared_status()
if status:
    print(f"Job running for: {fmttime(status['elapsed_time'])}")
    print(f"Current phase: {len(status['laps'])}")
```

## 📅 Date & Time Formatting

### Human-Readable Time Durations

```python
from suitkaise.sktime import fmttime

# Format various durations
print(fmttime(0.003))        # "3.00ms"
print(fmttime(1.5))          # "1.50s"
print(fmttime(75))           # "1m 15.00s"
print(fmttime(3661))         # "1h 1m 1.00s"
print(fmttime(86400 + 3600)) # "1d 1h 0m 0.00s"
```

### Human-Readable Dates

```python
from suitkaise.sktime import fmtdate, now, date_ago, date_from_now

current_time = now()

# Relative formatting (default)
print(fmtdate(date_ago(hours=2)))      # "2 hours ago"
print(fmtdate(date_from_now(days=3)))  # "in 3 days"
print(fmtdate(now() - 30))             # "30 seconds ago"

# Absolute formatting
print(fmtdate(current_time, style="absolute"))  # "Jan 15, 2025 3:30 PM"
print(fmtdate(current_time, style="full"))      # "Wednesday, January 15, 2025 3:30:45 PM"
print(fmtdate(current_time, style="short"))     # "1/15/25 3:30 PM"

# Custom formatting
print(fmtdate(current_time, style="custom", custom_format="%Y-%m-%d %H:%M"))  # "2025-01-15 15:30"
```

### Parse Human Date Strings

```python
from suitkaise.sktime import parse_human_date

# Parse natural language dates
yesterday = parse_human_date("yesterday")
in_2_hours = parse_human_date("2 hours from now")
last_week = parse_human_date("7 days ago")

if yesterday:
    print(f"Yesterday was: {fmtdate(yesterday, style='absolute')}")
```

## 🛠️ Advanced Features

### Benchmarking & Function Comparison

```python
from suitkaise.sktime import benchmark, compare_functions

# Benchmark a single function
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

results = benchmark(fibonacci, iterations=1000, n=10)
print(f"Average time: {results['avg_time']:.6f}s")
print(f"Operations per second: {results['ops_per_second']:.0f}")

# Compare multiple approaches
def method1(data):
    return sorted(data)

def method2(data):
    return list(sorted(data))

comparison = compare_functions(method1, method2, iterations=1000, data=list(range(100)))
# Automatically prints performance ranking
```

### Rate Monitoring

```python
from suitkaise.sktime import RateMonitor

monitor = RateMonitor(window_size=10.0)  # 10-second sliding window

for item in large_dataset:
    process_item(item)
    monitor.tick()  # Record one operation
    
    if monitor.operation_count % 100 == 0:
        current_rate = monitor.get_current_rate()
        print(f"Processing {current_rate:.1f} items/sec")
```

### Context Managers for Different Scenarios

```python
# Simple timing with automatic output
from suitkaise.sktime import timing_context

with timing_context("data processing"):
    process_large_dataset()
# Output: ✅ Data processing completed in 2.34s

# Timeout protection
from suitkaise.sktime import timeout_context

with timeout_context(5.0, "Database query timed out"):
    slow_database_query()  # Will raise error after 5 seconds

# Rate monitoring
from suitkaise.sktime import rate_monitor_context

with rate_monitor_context("file processing", report_interval=50) as monitor:
    for file in files:
        process_file(file)
        monitor.tick()  # Prints rate every 50 operations
```

## 🔄 Integration Features

### SKGlobal Integration (Cross-Process Storage)

```python
# Store timing data that persists across process restarts
@timethis(store_in_global="persistent_timings", track_calls=True)
def important_function():
    return "result"

# Export registry data to global storage
api_registry = get_timing_registry("api_calls")
api_registry.sync_to_skglobal("api_performance_report")

# Load data from global storage in another process
api_registry.load_from_skglobal("api_performance_report")
```

### Context Manager with Global Storage

```python
from suitkaise.sktime import skglobal_timing_context

with skglobal_timing_context("batch_processing") as timer:
    process_data()
    timer.lap("stage1")
    more_processing()

# Results automatically stored in global storage
# Accessible from other processes under "timing_batch_processing"
```

## 📋 Common Use Cases

### 1. API Performance Monitoring

```python
# Set up registry for API calls
api_registry = get_timing_registry("api_monitoring")

@timethis(callback=api_registry.record_timing, print_result=True)
def api_endpoint(endpoint_name):
    # Simulate API call
    response = make_request(endpoint_name)
    return response

# Use throughout your application
api_endpoint("users")
api_endpoint("orders") 
api_endpoint("products")

# Analyze performance
api_registry.print_summary()
slow_endpoints = api_registry.find_functions(
    lambda name, timings: statistics.mean([t['duration'] for t in timings]) > 1.0
)
```

### 2. Database Query Optimization

```python
db_registry = get_timing_registry("database_queries")

@timethis(callback=db_registry.record_timing)
def execute_query(sql):
    return database.execute(sql)

# After running your application for a while
expensive_queries = db_registry.get_top_functions(sort_by="avg_time")
print("Slowest queries:")
for query_stats in expensive_queries[:5]:
    print(f"  {query_stats['function_name']}: {fmttime(query_stats['avg_time'])}")
```

### 3. Long-Running Process Monitoring

```python
# Process 1: Long-running job
shared_timer = create_shared_timer("data_pipeline")
shared_timer.start()

for i, batch in enumerate(data_batches):
    process_batch(batch)
    shared_timer.lap(f"batch_{i}")

shared_timer.stop()

# Process 2: Monitoring dashboard
def check_pipeline_status():
    timer = create_shared_timer("data_pipeline")
    status = timer.get_shared_status()
    
    if status and status['is_running']:
        print(f"Pipeline running for: {fmttime(status['elapsed_time'])}")
        print(f"Batches completed: {len(status['laps'])}")
    else:
        print("Pipeline not running")
```

### 4. Performance Testing

```python
# Test multiple implementations
def test_sorting_performance():
    import random
    test_data = [random.randint(1, 1000) for _ in range(1000)]
    
    results = compare_functions(
        sorted,
        lambda x: list(x).sort() or x,
        iterations=1000,
        data=test_data.copy()
    )
    
    return results

# Benchmark with different data sizes
for size in [100, 1000, 10000]:
    data = list(range(size))
    results = benchmark(sorted, iterations=100, data=data)
    print(f"Size {size}: {results['ops_per_second']:.0f} ops/sec")
```

## 🎯 Best Practices

### 1. Choose the Right Tool

```python
# For one-off timing
with Timer() as timer:
    do_work()

# For automatic function timing
@timethis()
def my_function():
    pass

# For cross-process coordination
shared_timer = create_shared_timer("job_name")

# For systematic performance analysis
registry = get_timing_registry("my_component")
```

### 2. Organize Timing Data

```python
# Use separate registries for different components
api_registry = get_timing_registry("api")
db_registry = get_timing_registry("database") 
ml_registry = get_timing_registry("machine_learning")

# Export important data for analysis
api_registry.sync_to_skglobal("production_api_performance")
```

### 3. Handle Errors Gracefully

```python
@timethis(track_calls=True)
def might_fail():
    if random.random() < 0.1:  # 10% failure rate
        raise Exception("Random failure")
    return "success"

# The decorator tracks both successful and failed calls
stats = might_fail.get_timing_stats()
print(f"Success rate: {stats['success_rate']:.1%}")
```

### 4. Use Context for Complex Operations

```python
# Better than manual timer management
with Timer() as timer:
    setup_data()
    timer.lap("setup")
    
    process_data()
    timer.lap("processing")
    
    cleanup()
    timer.lap("cleanup")

# Results automatically available after the block
print(f"Total: {fmttime(timer.elapsed_time)}")
```

## 📖 API Reference

### Core Classes

- **`Timer`** - Main timing class with context manager, pause/resume, lap timing
- **`SharedTimer`** - Timer that syncs across processes via SKGlobal
- **`TimingRegistry`** - Rej-based registry for organizing timing data
- **`RateMonitor`** - Real-time throughput monitoring
- **`PerformanceTracker`** - Long-term performance analysis

### Decorators

- **`@timethis`** - Flexible function timing with storage options
- **`@time_function`** - Simple automatic timing with print output
- **`@rate_limiter`** - Control function call frequency
- **`@profile_function_calls`** - Detailed call statistics

### Utility Functions

- **`now()`** - Get current timestamp
- **`sleep(seconds)`** - Sleep for specified duration
- **`elapsed(start, end)`** - Calculate time difference
- **`fmttime(seconds)`** - Format duration as human-readable string
- **`fmtdate(timestamp)`** - Format date/time as human-readable string
- **`benchmark(func)`** - Comprehensive function benchmarking
- **`compare_functions(*funcs)`** - Compare performance of multiple functions

### Registry Functions

- **`get_timing_registry(name)`** - Get or create a timing registry
- **`list_timing_registries()`** - List all available registries
- **`clear_timing_registry(name)`** - Remove a registry

### Context Managers

- **`timing_context(name)`** - Simple timing with automatic output
- **`timeout_context(seconds)`** - Add timeout protection to code blocks
- **`skglobal_timing_context(name)`** - Timing with automatic SKGlobal storage

## 🚀 Why Use SKTime?

1. **Zero Configuration** - Works out of the box with sensible defaults
2. **Flexible** - From simple timing to complex cross-process analysis
3. **Performance Focused** - Minimal overhead on your actual code
4. **Cross-Process** - Share timing data between different Python processes
5. **Persistent** - Keep timing data even after program restarts
6. **Thread-Safe** - Use safely in multi-threaded applications
7. **Human-Friendly** - All output is easy to read and understand
8. **Comprehensive** - Everything you need for timing and performance analysis

Whether you're optimizing a single function or analyzing the performance of a distributed system, SKTime provides the tools you need with a clean, intuitive API.

Happy timing! ⏱️