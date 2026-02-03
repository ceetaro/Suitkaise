# `processing` Examples

## Basic `Skprocess`

### Simple Counter Process

A minimal process that counts iterations.

```python
from suitkaise.processing import Skprocess

class CounterProcess(Skprocess):
    """
    A simple process that counts up to a specified number.
    
    - Basic __init__ with process_config.runs
    - __run__ for main work
    - __result__ to return data
    """
    
    def __init__(self, target: int = 10):
        # store target count
        # (process_config is already initialized by Skprocess._setup)
        self.target = target
        self.counter = 0
        
        # configure: run exactly 'target' iterations
        self.process_config.runs = target
    
    def __run__(self):
        # increment counter each iteration
        self.counter += 1
    
    def __result__(self):
        # return final count when process completes
        return self.counter


# create process with target of 100
process = CounterProcess(target=100)

# start the subprocess
process.start()

# wait for completion (blocks until done)
process.wait()

# get the result
result = process.result()
print(f"Final count: {result}")  # Final count: 100
```

### Using `run()`

```python
from suitkaise.processing import Skprocess

class QuickProcess(Skprocess):
    """
    A process that does quick work.
    
    Using run() to start, wait, and get result in one call
    """
    
    def __init__(self, data: list):
        self.data = data
        self.results = []
        self.process_config.runs = len(data)
    
    def __run__(self):
        # process one item per run
        item = self.data[self._current_run]
        self.results.append(item * 2)
    
    def __result__(self):
        return self.results


# run() combines start(), wait(), and result()
process = QuickProcess([1, 2, 3, 4, 5])
results = process.run()
print(results)  # [2, 4, 6, 8, 10]
```

### Full Lifecycle Process

```python
from suitkaise.processing import Skprocess

class DataProcessor(Skprocess):
    """
    A process demonstrating all lifecycle methods.
    
    - __prerun__: Setup before each run
    - __run__: Main work
    - __postrun__: Cleanup after each run
    - __onfinish__: Final cleanup
    - __result__: Return data
    """
    
    def __init__(self, batch_size: int = 5):
        # configure process
        self.batch_size = batch_size
        self.process_config.runs = 3  # process 3 batches
        
        # state tracking
        self.current_batch = None
        self.processed_batches = []
        self.total_items = 0
    
    def __prerun__(self):
        # called before each __run__
        # fetch the next batch of data
        batch_number = self._current_run
        self.current_batch = [
            f"item_{batch_number}_{i}" 
            for i in range(self.batch_size)
        ]
        print(f"[prerun] Fetched batch {batch_number}: {len(self.current_batch)} items")
    
    def __run__(self):
        # called each iteration - do the main work
        # process each item in the current batch
        processed = []
        for item in self.current_batch:
            result = item.upper()
            processed.append(result)
            self.total_items += 1
        
        # store for postrun
        self._processed = processed
        print(f"[run] Processed {len(processed)} items")
    
    def __postrun__(self):
        # called after each __run__
        # save results and cleanup
        self.processed_batches.append(self._processed)
        self.current_batch = None  # clear for next iteration
        self._processed = None
        print(f"[postrun] Saved batch, total batches: {len(self.processed_batches)}")
    
    def __onfinish__(self):
        # called once when process ends (stop signal or run limit)
        # final cleanup and summary
        print(f"[onfinish] Finished processing {self.total_items} total items")
    
    def __result__(self):
        # return the final data
        return {
            'batches': self.processed_batches,
            'total_items': self.total_items,
            'num_batches': len(self.processed_batches)
        }

    # NOTE: not implementing __error__ to let Skprocess decide what error to raise


process = DataProcessor(batch_size=3)
result = process.run()

print(f"\nResult: {result['num_batches']} batches, {result['total_items']} items")
# Output:
# [prerun] Fetched batch 0: 3 items
# [run] Processed 3 items
# [postrun] Saved batch, total batches: 1
# [prerun] Fetched batch 1: 3 items
# [run] Processed 3 items
# [postrun] Saved batch, total batches: 2
# [prerun] Fetched batch 2: 3 items
# [run] Processed 3 items
# [postrun] Saved batch, total batches: 3
# [onfinish] Finished processing 9 total items

# Result: 3 batches, 9 items
```

### Indefinite Process with `stop()`

```python
from suitkaise.processing import Skprocess
from suitkaise import timing

class MonitorProcess(Skprocess):
    """
    A process that runs indefinitely until stopped.
    
    - `process_config.runs=None` for indefinite execution
    - Using stop() from the parent process
    - Graceful shutdown with __onfinish__
    """
    
    def __init__(self):
        # no run limit - runs until stop() is called
        self.process_config.runs = None
        self.events = []
    
    def __run__(self):
        # record timestamp and system info each iteration
        import os
        self.events.append({
            'run': self._current_run,
            'time': timing.time(),
            'pid': os.getpid(),
            'memory': self._get_memory_usage()
        })
        # small delay to avoid spinning CPU
        timing.sleep(0.1)
    
    def _get_memory_usage(self):
        """Get current process memory usage in MB."""
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
    
    def __onfinish__(self):
        # called when stop() signal is received
        print(f"Monitor shutting down after {len(self.events)} events")
    
    def __result__(self):
        return self.events


# start the monitor
process = MonitorProcess()
process.start()

# let it collect some data
timing.sleep(0.5)

# signal graceful stop
process.stop()

# wait for it to finish
process.wait()

# get results
events = process.result()
print(f"Captured {len(events)} events")
```

### Time-Limited Process with `process_config.join_in`

```python
from suitkaise.processing import Skprocess

class TimeBoundProcess(Skprocess):
    """
    A process that runs for a maximum amount of time.
    
    - `process_config.join_in` to set maximum runtime
    - `process_config.runs=None` combined with `process_config.join_in` for time-based limits
    """
    
    def __init__(self, max_seconds: float = 10.0):
        self.process_config.runs = None # this is the default
        self.process_config.join_in = max_seconds
        
        self.iterations = 0
    
    def __run__(self):
        self.iterations += 1

    
    def __result__(self):
        return self.iterations


process = TimeBoundProcess(max_seconds=1.0)
result = process.run()
print(f"Completed {result} iterations in ~1 second")
# Completed ~10 iterations in ~1 second
```

### Process with Retries (Lives)

```python
import random
from suitkaise.processing import Skprocess, RunError

class UnreliableProcess(Skprocess):
    """
    A process that may fail but retries automatically.
    
    - `process_config.lives` for automatic retry on failure
    - State preservation across retries
    - __error__ for handling final failure
    """
    
    def __init__(self, fail_probability: float = 0.3):
        self.fail_probability = fail_probability
        self.process_config.runs = 10
        # allow 3 total attempts (2 retries)
        self.process_config.lives = 3
        
        self.successful_runs = 0
        self.attempt_count = 0
    
    def __prerun__(self):
        # track attempts
        self.attempt_count += 1
    
    def __run__(self):
        # randomly fail based on probability
        if random.random() < self.fail_probability:
            raise RuntimeError(f"Random failure on run {self._current_run}")
        
        # success!
        self.successful_runs += 1
    
    def __error__(self):
        # called when all lives exhausted
        # self.error contains the exception
        print(f"Process failed after {self.attempt_count} attempts")
        print(f"Error: {self.error}")
        
        # return partial results
        return {
            'status': 'failed',
            'successful_runs': self.successful_runs,
            'error': str(self.error)
        }
    
    def __result__(self):
        return {
            'status': 'success',
            'successful_runs': self.successful_runs,
            'total_attempts': self.attempt_count
        }


# set seed for reproducibility
random.seed(42)

process = UnreliableProcess(fail_probability=0.2)
try:
    result = process.run()
    print(f"Result: {result}")
except Exception as e:
    print(f"Process ultimately failed: {e}")
```

### Timeouts on Lifecycle Methods

```python
from suitkaise.processing import Skprocess, ProcessTimeoutError

class SlowProcess(Skprocess):
    """
    A process with timeout protection on lifecycle methods.
    
    - Setting timeouts for individual lifecycle sections
    - ProcessTimeoutError when timeouts are exceeded
    """
    
    def __init__(self):
        self.process_config.runs = 5
        
        # set timeouts for each section
        self.process_config.timeouts.prerun = 1.0   # 1 second max
        self.process_config.timeouts.run = 2.0      # 2 seconds max
        self.process_config.timeouts.postrun = 1.0  # 1 second max
        
        self.completed_runs = 0
    
    def __prerun__(self):
        # quick prerun - well within timeout
        pass
    
    def __run__(self):
        # CPU-intensive work that varies in duration
        if self._current_run == 3:
            # this run will exceed timeout - compute intensive fibonacci
            self._fibonacci(40)  # takes several seconds
        else:
            # normal quick computation
            self._fibonacci(25)
        
        self.completed_runs += 1
    
    def _fibonacci(self, n):
        """Recursive fibonacci - intentionally slow for large n."""
        if n <= 1:
            return n
        return self._fibonacci(n - 1) + self._fibonacci(n - 2)
    
    def __error__(self):
        # handle timeout error
        if isinstance(self.error, ProcessTimeoutError):
            print(f"Timeout in {self.error.section} after {self.error.timeout}s")
        return {
            'status': 'timeout',
            'completed_runs': self.completed_runs
        }
    
    def __result__(self):
        return {
            'status': 'success',
            'completed_runs': self.completed_runs
        }


process = SlowProcess()
result = process.run()
print(f"Result: {result}")
# Timeout in __run__ after 2.0s
# Result: {'status': 'timeout', 'completed_runs': 3}
```

### Accessing Timing Data

```python
from suitkaise.processing import Skprocess
import random
import hashlib

class TimedProcess(Skprocess):
    """
    A process demonstrating timing access.
    
    - Accessing per-method timers
    - Using process_timer for aggregate stats
    - Timer statistics (mean, min, max, percentile)
    """
    
    def __init__(self, runs: int = 20):
        self.process_config.runs = runs
        self.data = [f"data_block_{i}" for i in range(1000)]
    
    def __prerun__(self):
        # variable prerun work - shuffle data
        random.shuffle(self.data)
    
    def __run__(self):
        # variable run work - hash computations
        iterations = random.randint(50, 150)
        for _ in range(iterations):
            for item in self.data[:100]:
                hashlib.sha256(item.encode()).hexdigest()
    
    def __postrun__(self):
        # quick postrun - sort a slice
        sorted(self.data[:50])
    
    def __result__(self):
        return "done"


process = TimedProcess(runs=20)
process.run()

# access individual timers
print(f"__prerun__ timing:")
print(f"  mean:   {process.__prerun__.timer.mean:.4f}s")
print(f"  min:    {process.__prerun__.timer.min:.4f}s")
print(f"  max:    {process.__prerun__.timer.max:.4f}s")

print(f"\n__run__ timing:")
print(f"  mean:   {process.__run__.timer.mean:.4f}s")
print(f"  p50:    {process.__run__.timer.percentile(50):.4f}s")
print(f"  p95:    {process.__run__.timer.percentile(95):.4f}s")

print(f"\n__postrun__ timing:")
print(f"  total:  {process.__postrun__.timer.total_time:.4f}s")

# aggregate timer for full iterations
print(f"\nFull iteration timing (prerun + run + postrun):")
print(f"  mean:   {process.process_timer.mean:.4f}s")
print(f"  total:  {process.process_timer.total_time:.4f}s")
print(f"  count:  {process.process_timer.num_times}")
```

### Async Process Execution

```python
import asyncio
import hashlib
from suitkaise.processing import Skprocess

class AsyncFriendlyProcess(Skprocess):
    """
    Running processes in async code.
    
    - Using .asynced() modifier on wait() and result()
    - Running multiple processes concurrently
    """
    
    def __init__(self, process_id: int, data_chunks: list):
        self.process_id = process_id
        self.data_chunks = data_chunks
        self.process_config.runs = len(data_chunks)
        self.results = []
    
    def __run__(self):
        # process a data chunk - compute hash
        chunk = self.data_chunks[self._current_run]
        hash_result = hashlib.sha256(chunk.encode()).hexdigest()
        self.results.append({
            'process': self.process_id,
            'run': self._current_run,
            'hash': hash_result[:16]
        })
    
    def __result__(self):
        return self.results


async def run_processes_concurrently():
    """Run multiple processes and wait for all concurrently."""
    
    # create data for each process
    all_data = [
        [f"process_0_chunk_{i}" for i in range(5)],
        [f"process_1_chunk_{i}" for i in range(5)],
        [f"process_2_chunk_{i}" for i in range(5)],
    ]
    
    # create and start multiple processes
    processes = []
    for i, data in enumerate(all_data):
        p = AsyncFriendlyProcess(process_id=i, data_chunks=data)
        p.start()
        processes.append(p)
    
    # wait for all concurrently using asynced()
    wait_tasks = [p.wait.asynced()() for p in processes]
    await asyncio.gather(*wait_tasks)
    
    # get all results
    results = [p.result() for p in processes]
    
    return results


# run the async code
results = asyncio.run(run_processes_concurrently())
for i, r in enumerate(results):
    print(f"Process {i}: {len(r)} results")
```

### Background Execution with Future

```python
from suitkaise.processing import Skprocess
from suitkaise import timing
import math

class BackgroundProcess(Skprocess):
    """
    Running a process in the background.
    
    - Using .background() modifier
    - Doing other work while process runs
    - Getting result from Future
    """
    
    def __init__(self, numbers: list):
        self.numbers = numbers
        self.process_config.runs = len(numbers)
        self.results = []
    
    def __run__(self):
        # compute prime factorization for each number
        n = self.numbers[self._current_run]
        factors = self._prime_factors(n)
        self.results.append({'number': n, 'factors': factors})
    
    def _prime_factors(self, n):
        """Find prime factors of n."""
        factors = []
        d = 2
        while d * d <= n:
            while n % d == 0:
                factors.append(d)
                n //= d
            d += 1
        if n > 1:
            factors.append(n)
        return factors
    
    def __result__(self):
        return self.results


# start process and get Future immediately
numbers = [123456789, 987654321, 1000000007, 999999937, 2147483647]
process = BackgroundProcess(numbers)
future = process.run.background()()

# do other work while process runs
print("Process running in background...")
main_thread_work = []
for i in range(5):
    # compute something in main thread
    main_thread_work.append(math.factorial(100 + i))
    print(f"  Main thread computed factorial({100 + i})")

# now get the result (may block if not done)
result = future.result()
print(f"\nProcess computed {len(result)} factorizations")
for r in result[:3]:
    print(f"  {r['number']} = {r['factors']}")
```

---

## `Pool`

### Basic `map`

```python
from suitkaise.processing import Pool

def square(x):
    """Simple function to square a number."""
    return x * x


# create a pool with 4 workers
pool = Pool(workers=4)

# map applies the function to each item
# results are returned in the same order as inputs
items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
results = pool.map(square, items)

print(results)  # [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]

# always close the pool when done
pool.close()
```

### `Pool` as Context Manager

```python
from suitkaise.processing import Pool
import hashlib
import json

def process_data(data):
    """Process a single data item - normalize and hash."""
    # normalize the data
    normalized = data.strip().lower()
    
    # compute a hash
    data_hash = hashlib.md5(normalized.encode()).hexdigest()
    
    # return processed result
    return {
        'original': data,
        'normalized': normalized,
        'hash': data_hash[:8]
    }


# use context manager for automatic cleanup
with Pool(workers=4) as pool:
    items = ["  Apple  ", "BANANA", "Cherry", "  DATE", "elderberry"]

    results = pool.map(process_data, items)

    for r in results:
        print(f"{r['original']:>12} -> {r['normalized']:<12} ({r['hash']})")

        
# pool is automatically closed when exiting the 'with' block
```

### Using `star()` for Tuple Unpacking

```python
from suitkaise.processing import Pool

def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(x, y, z):
    """Multiply three numbers."""
    return x * y * z


with Pool(workers=4) as pool:
    # without star(): each item is passed as a single argument
    # the function receives a tuple
    # pool.map(add, [(1, 2), (3, 4)])  # ERROR: add() expects 2 args, got 1 tuple
    
    # with star(): tuples are unpacked into positional arguments
    pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]
    sums = pool.star().map(add, pairs)
    print(f"Sums: {sums}")  # Sums: [3, 7, 11, 15]
    
    # works with any number of arguments
    triples = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
    products = pool.star().map(multiply, triples)
    print(f"Products: {products}")  # Products: [6, 120, 504]
```

### `unordered_map` for Fastest List

```python
from suitkaise.processing import Pool
import hashlib

def variable_work(item):
    """Work that takes variable time based on input."""
    # compute variable number of hashes based on item value
    iterations = (item % 10 + 1) * 500  # 500 to 5000 iterations
    
    data = str(item).encode()
    for _ in range(iterations):
        data = hashlib.sha256(data).digest()
    
    return {
        'item': item,
        'iterations': iterations,
        'hash': hashlib.sha256(data).hexdigest()[:12]
    }


with Pool(workers=4) as pool:
    items = list(range(20))
    
    # unordered_map returns a list (like map)
    # but results are in completion order (like unordered_imap)
    results = pool.unordered_map(variable_work, items)
    
    print(f"Got {len(results)} results")
    print(f"Order received: {[r['item'] for r in results]}")
    # Order is NOT sequential - items with fewer iterations complete first
    
    # useful when you need all results but don't care about order
    # faster than map() because you don't wait for slow items to unblock fast ones
```

### `imap` for Memory Efficiency

```python
from suitkaise.processing import Pool
import hashlib

def heavy_computation(item):
    """Compute SHA-256 hash multiple times, return large result."""
    # do real computation - iterative hashing
    data = str(item).encode()
    for _ in range(1000):
        data = hashlib.sha256(data).digest()
    
    # return result with computed hash and derived data
    final_hash = hashlib.sha256(data).hexdigest()
    return {
        'input': item,
        'hash': final_hash,
        'derived': [final_hash[i:i+4] for i in range(0, 64, 4)]  # 16 chunks
    }


with Pool(workers=4) as pool:
    # imap returns an iterator - results are yielded one at a time
    # this is memory efficient for large datasets
    items = range(100)
    
    processed = 0
    for result in pool.imap(heavy_computation, items):
        # process each result as it arrives (in order)
        processed += 1
        if processed % 20 == 0:
            print(f"Processed {processed} items, latest hash: {result['hash'][:16]}...")
    
    print(f"Done! Processed {processed} total items")
```

### `unordered_imap` for Fastest Results

```python
from suitkaise.processing import Pool
import hashlib

def variable_work(item):
    """Work that takes variable time based on input."""
    # compute variable number of hashes based on item value
    # larger items = more work = longer time
    iterations = (item % 10 + 1) * 500  # 500 to 5000 iterations
    
    data = str(item).encode()
    for _ in range(iterations):
        data = hashlib.sha256(data).digest()
    
    return {
        'item': item,
        'iterations': iterations,
        'hash': hashlib.sha256(data).hexdigest()[:12]
    }


with Pool(workers=4) as pool:
    items = list(range(20))
    
    print("Using unordered_imap - fastest results first:")
    results = []
    for result in pool.unordered_imap(variable_work, items):
        # results arrive as they complete (NOT in order)
        results.append(result)
        print(f"  Got item {result['item']:2d} ({result['iterations']:4d} iters)")
    
    print(f"\nOrder received: {[r['item'] for r in results]}")
    # Order is NOT sequential - items with fewer iterations complete first
```

### `Pool` with Timeout

```python
from suitkaise.processing import Pool

def slow_function(x):
    """Function that might be slow - recursive fibonacci."""
    def fib(n):
        if n <= 1:
            return n
        return fib(n - 1) + fib(n - 2)
    
    if x == 5:
        # this one computes a large fibonacci - takes several seconds
        return fib(40)
    else:
        # quick computation
        return fib(20 + x)


with Pool(workers=4) as pool:
    items = [1, 2, 3, 4, 5, 6, 7, 8]
    
    try:
        # timeout applies to the entire operation
        results = pool.map.timeout(2.0)(slow_function, items)
        print(results)
    except TimeoutError as e:
        print(f"Operation timed out: {e}")
    
    # timeout also works with imap - use items that complete quickly
    try:
        for result in pool.imap.timeout(5.0)(slow_function, [1, 2, 3]):
            print(f"Got: {result}")
    except TimeoutError:
        print("imap timed out")
```

### Background Execution with `Pool`

```python
from suitkaise.processing import Pool
import math

def compute(x):
    """CPU-intensive computation - prime factorization."""
    def prime_factors(n):
        factors = []
        d = 2
        while d * d <= n:
            while n % d == 0:
                factors.append(d)
                n //= d
            d += 1
        if n > 1:
            factors.append(n)
        return factors
    
    # compute prime factors of a large number
    large_num = 10**9 + x * 1000 + 7
    return {'input': x, 'number': large_num, 'factors': prime_factors(large_num)}


with Pool(workers=4) as pool:
    items = list(range(20))
    
    # start map in background - returns Future immediately
    future = pool.map.background()(compute, items)
    
    # do other work while pool processes
    print("Pool working in background...")
    main_work = []
    for i in range(3):
        # compute something in main thread
        result = math.factorial(500 + i * 100)
        main_work.append(len(str(result)))
        print(f"  Main thread computed factorial, {main_work[-1]} digits")
    
    # get results (blocks if not done)
    results = future.result()
    print(f"Got {len(results)} factorizations")
    print(f"First result: {results[0]}")
```

### Async `Pool` Operations

```python
import asyncio
import hashlib
from suitkaise.processing import Pool

def cpu_work(x):
    """CPU-bound work - compute hash chain."""
    data = str(x).encode()
    for _ in range(1000):
        data = hashlib.sha256(data).digest()
    return {'input': x, 'hash': hashlib.sha256(data).hexdigest()[:16]}


async def process_batches():
    """Process multiple batches concurrently."""
    
    with Pool(workers=4) as pool:
        # create multiple async map operations
        batch1 = list(range(10))
        batch2 = list(range(10, 20))
        batch3 = list(range(20, 30))
        
        # run all batches concurrently using asynced()
        results = await asyncio.gather(
            pool.map.asynced()(cpu_work, batch1),
            pool.map.asynced()(cpu_work, batch2),
            pool.map.asynced()(cpu_work, batch3),
        )
        
        return results


results = asyncio.run(process_batches())
print(f"Batch 1: {len(results[0])} items, first: {results[0][0]}")
print(f"Batch 2: {len(results[1])} items, first: {results[1][0]}")
print(f"Batch 3: {len(results[2])} items, first: {results[2][0]}")
```

### Using `Skprocess` with `Pool`

```python
from suitkaise.processing import Pool, Skprocess
import hashlib
import json

class DataTransformer(Skprocess):
    """
    A Skprocess that can be used with Pool.
    
    Pool creates an instance for each item and runs it.
    """
    
    def __init__(self, input_data: dict):
        # receive input through __init__
        self.input_data = input_data
        self.process_config.runs = 1  # single run per item
        
        self.transformed = None
    
    def __run__(self):
        # transform the data - real computation
        data = self.input_data
        
        # compute a hash of the input
        data_json = json.dumps(data, sort_keys=True)
        data_hash = hashlib.sha256(data_json.encode()).hexdigest()
        
        # transform the value
        self.transformed = {
            'original_id': data['id'],
            'original_value': data['value'],
            'doubled': data['value'] * 2,
            'squared': data['value'] ** 2,
            'hash': data_hash[:12],
            'processed': True
        }
    
    def __result__(self):
        return self.transformed


# create input data
items = [
    {'id': 1, 'value': 10},
    {'id': 2, 'value': 20},
    {'id': 3, 'value': 30},
    {'id': 4, 'value': 40},
]

with Pool(workers=2) as pool:
    # Pool creates DataTransformer(item) for each item
    # and runs it, collecting results
    results = pool.map(DataTransformer, items)
    
    for r in results:
        print(f"ID {r['original_id']}: {r['original_value']} -> doubled={r['doubled']}, squared={r['squared']}")
# ID 1: 10 -> doubled=20, squared=100
# ID 2: 20 -> doubled=40, squared=400
# ID 3: 30 -> doubled=60, squared=900
# ID 4: 40 -> doubled=80, squared=1600
```

### Combining `star()` with Modifiers

```python
from suitkaise.processing import Pool
import asyncio
import math

def process_pair(x, y):
    """Process a pair of values - compute combination and factorial ratio."""
    # compute nCr (n choose r) where x >= y
    n, r = max(x, y), min(x, y)
    result = math.comb(n * 10, r * 2)
    return {'inputs': (x, y), 'comb': result, 'digits': len(str(result))}


async def main():
    with Pool(workers=4) as pool:
        pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]
        
        # star() composes with all modifiers
        
        # star + timeout
        results = pool.star().map.timeout(5.0)(process_pair, pairs)
        print(f"star + timeout: {[r['digits'] for r in results]} digits")
        
        # star + background
        future = pool.star().map.background()(process_pair, pairs)
        results = future.result()
        print(f"star + background: {[r['digits'] for r in results]} digits")
        
        # star + async
        results = await pool.star().map.asynced()(process_pair, pairs)
        print(f"star + async: {[r['digits'] for r in results]} digits")
        
        # star + imap
        print("star + imap:", end=" ")
        for result in pool.star().imap(process_pair, pairs):
            print(f"{result['inputs']}", end=" ")
        print()
        
        # star + unordered_imap
        print("star + unordered_imap:", end=" ")
        for result in pool.star().unordered_imap(process_pair, pairs):
            print(f"{result['inputs']}", end=" ")
        print()


asyncio.run(main())
```

### Error Handling in `Pool`

```python
from suitkaise.processing import Pool

def risky_function(x):
    """Function that might raise an error."""
    if x == 3:
        raise ValueError(f"Cannot process {x}")
    return x * 2


with Pool(workers=4) as pool:
    items = [1, 2, 3, 4, 5]
    
    try:
        # error in any worker propagates to main process
        results = pool.map(risky_function, items)
    except ValueError as e:
        print(f"Caught error: {e}")
    
    # process the items that don't cause errors
    safe_items = [1, 2, 4, 5]
    results = pool.map(risky_function, safe_items)
    print(f"Safe results: {results}")  # [2, 4, 8, 10]
```

---

## `Share`

### Basic Shared Counter using `Share`

```python
from suitkaise.processing import Share, Pool, Skprocess

# create a Share and assign a counter
share = Share()
share.counter = 0


class CounterProcess(Skprocess):
    """
    A process that increments a shared counter.
    
    Demonstrates basic Share usage across processes.
    """
    # pass the Share instance to the process
    def __init__(self, shared: Share, amount: int = 1):
        self.shared = shared
        self.amount = amount
        self.process_config.runs = 10  # increment 10 times
    
    def __postrun__(self):
        # increment the shared counter
        # this works across process boundaries!
        self.shared.counter += self.amount
    
    def __result__(self):
        return "done"


# run 5 processes, each incrementing 10 times
with Pool(workers=4) as pool:
    # pass the same share instance to all processes
    pool.map(CounterProcess, [share] * 5)

# counter was incremented 50 times (5 processes × 10 runs each)
print(f"Final counter: {share.counter}") # will be 50

# always stop share when done to save resources
share.stop()
```

### Sharing Complex Objects (like `Sktimer`)

```python
from suitkaise.processing import Share, Pool, Skprocess
from suitkaise.timing import Sktimer
from suitkaise import timing
import hashlib
import random

# create Share and assign a timer
share = Share()
share.timer = Sktimer()


class TimedWorker(Skprocess):
    """
    A process that records timing to a shared timer.
    
    Demonstrates sharing suitkaise objects with _shared_meta.
    """
    
    def __init__(self, shared: Share, work_count: int = 5):
        self.shared = shared
        self.process_config.runs = work_count
    
    def __run__(self):
        # variable hash iterations
        with timing.TimeThis() as run_timer:
            iterations = random.randint(500, 2000)
            data = b"benchmark_data"
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
        
        # add timing to shared timer
        self.shared.timer.add_time(run_timer.most_recent)
    
    def __result__(self):
        return "done"


# run multiple workers
workers = 4
with Pool(workers=workers) as pool:
    pool.map(TimedWorker, [share] * workers)

stats = share.timer.get_stats()

# will be 20 (4 workers × 5 runs each)
num_times = stats.num_times

mean = stats.mean
min = stats.min
max = stats.max
stdev = stats.stdev
variance = stats.variance

share.stop()
```

### `Share` as Context Manager

```python
from suitkaise.processing import Share, Pool, Skprocess

class Counter:
    """A simple counter class (will be auto-wrapped by Share)."""
    def __init__(self):
        self.value = 0
    
    def increment(self, amount=1):
        self.value += amount


class WorkerProcess(Skprocess):
    def __init__(self, shared: Share):
        self.shared = shared
        self.process_config.runs = 10
    
    def __postrun__(self):
        self.shared.my_counter.increment(1)
    
    def __result__(self):
        return "done"


# use Share as context manager for automatic cleanup
with Share() as share:

    # assign custom object - auto-wrapped with Skclass
    share.counter = Counter()
    
    with Pool(workers=2) as pool:
        pool.map(WorkerProcess, [share] * 3)
    
    print(f"Final value: {share.counter.value}") # 30

# Share automatically stopped after 'with' block
```

### Multiple Shared Objects

```python
from suitkaise.processing import Share, Pool, Skprocess
from suitkaise import timing
import hashlib
import random

class Stats:
    """Track statistics across processes."""
    def __init__(self):
        self.processed = 0
        self.errors = 0
        self.successes = 0
    
    def record_success(self):
        self.processed += 1
        self.successes += 1
    
    def record_error(self):
        self.processed += 1
        self.errors += 1


class DataProcessor(Skprocess):
    """
    Process that uses multiple shared objects.
    """
    
    def __init__(self, shared: Share, item: dict):
        self.shared = shared
        self.item = item
        self.process_config.runs = 1
    
    def __run__(self):
        # time the processing
        with timing.TimeThis() as run_timer:
            try:
                # process the data - hash computation
                data = self.item['data'].encode()
                
                # randomly fail based on data content
                if hash(self.item['data']) % 5 == 0:
                    raise RuntimeError(f"Failed processing {self.item['id']}")
                
                # compute hash chain
                for _ in range(1000):
                    data = hashlib.sha256(data).digest()
                
                self.shared.stats.record_success()
                
            except Exception:
                self.shared.stats.record_error()
        
        self.shared.timer.add_time(run_timer.most_recent)
    
    def __result__(self):
        return self.item['id']


with Share() as share:
    # multiple shared objects
    share.stats = Stats()
    share.timer = timing.Sktimer()
    
    # create work items
    items = [{'id': i, 'data': f'item_{i}'} for i in range(20)]
    
    with Pool(workers=4) as pool:
        # use star() to pass both share and item
        args = [(share, item) for item in items]
        pool.star().map(DataProcessor, args)
    
    # access aggregated results
    print(f"Processed: {share.stats.processed}")
    print(f"Successes: {share.stats.successes}")
    print(f"Errors: {share.stats.errors}")
    print(f"Avg time: {share.timer.mean:.4f}s")
```

### Sharing with single `Skprocess`

```python
from suitkaise.processing import Share, Skprocess
from suitkaise.timing import Sktimer, TimeThis
import hashlib
import random

class IterativeWorker(Skprocess):
    """
    A long-running process that updates shared state.
    """
    
    def __init__(self, shared: Share):
        self.shared = shared
        self.process_config.runs = 100
    
    def __run__(self):
        # variable work - hash computation with random iterations
        with TimeThis() as run_timer:
            iterations = random.randint(200, 800)
            data = f"iteration_{self._current_run}".encode()
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
        
        # update shared state
        self.shared.progress += 1
        self.shared.timer.add_time(run_timer.most_recent)
    
    def __result__(self):
        return "complete"


with Share() as share:
    share.progress = 0
    share.timer = Sktimer()
    
    # run single process
    process = IterativeWorker(share)
    process.start()
    
    # monitor progress from parent
    while process.is_alive:
        print(f"Progress: {share.progress}/100")
        timing.sleep(0.5)
    
    process.wait()
    
    print(f"\nFinal progress: {share.progress}")
    print(f"Total time: {share.timer.total_time:.2f}s")
    print(f"Avg iteration: {share.timer.mean:.4f}s")
```

### `Share.start()` and `Share.stop()` control

```python
from suitkaise.processing import Share

# create Share without auto-start
share = Share(auto_start=False)

# Share is not running - operations will warn
share.counter = 0  # warning: Share is stopped

# explicitly start
share.start()
print(f"Running: {share.is_running}")  # Running: True

# normal operations
share.counter = 100

# stop to free resources
share.stop()
print(f"Running: {share.is_running}")  # Running: False

# can restart
share.start()
print(f"Counter: {share.counter}")  # Counter: 100
share.stop()
```

### Clearing `Share` State

```python
from suitkaise.processing import Share, Pool, Skprocess

class Incrementer(Skprocess):
    def __init__(self, shared: Share):
        self.shared = shared
        self.process_config.runs = 10
    
    def __postrun__(self):
        self.shared.count += 1
    
    def __result__(self):
        return "done"


with Share() as share:
    share.count = 0
    
    # first batch
    with Pool(workers=2) as pool:
        pool.map(Incrementer, [share] * 2)
    
    print(f"After batch 1: {share.count}")  # 20
    
    # clear all shared state
    share.clear()
    
    # re-initialize
    share.count = 0
    
    # second batch
    with Pool(workers=2) as pool:
        pool.map(Incrementer, [share] * 3)
    
    print(f"After batch 2: {share.count}")  # 30
```

---

## `Pipe`

### Basic `Pipe` Communication

```python
from suitkaise.processing import Pipe, Skprocess

class PipeWorker(Skprocess):
    """
    A process that communicates via Pipe.
    
    - Receiving the point end of a pipe
    - Bidirectional communication with parent
    """
    
    def __init__(self, pipe_point: Pipe.Point):
        self.pipe = pipe_point
        self.process_config.runs = 1
    
    def __run__(self):
        # receive command from parent
        command = self.pipe.recv()
        print(f"[Child] Received: {command}")
        
        # process the command
        result = command['value'] * 2
        
        # send result back
        self.pipe.send({'result': result, 'status': 'ok'})
        print(f"[Child] Sent result: {result}")
    
    def __result__(self):
        return "pipe_complete"


# create a pipe pair
# anchor stays in parent, point goes to child
anchor, point = Pipe.pair()

# start process with pipe point
process = PipeWorker(point)
process.start()

# send command through anchor
print("[Parent] Sending command...")
anchor.send({'action': 'compute', 'value': 21})

# receive response
response = anchor.recv()
print(f"[Parent] Received response: {response}")

# wait for process to finish
process.wait()

# close the pipe
anchor.close()
```

### One-Way `Pipe`

```python
from suitkaise.processing import Pipe, Skprocess

class DataReceiver(Skprocess):
    """
    A process that only receives data (one-way pipe).
    """
    
    def __init__(self, pipe_point: Pipe.Point):
        self.pipe = pipe_point
        self.process_config.runs = 1
        self.received_data = []
    
    def __run__(self):
        # receive all data until None sentinel
        while True:
            data = self.pipe.recv()
            if data is None:
                break
            self.received_data.append(data)
            print(f"[Child] Received: {data}")
    
    def __result__(self):
        return self.received_data


# create one-way pipe (parent sends, child receives)
anchor, point = Pipe.pair(one_way=True)

process = DataReceiver(point)
process.start()

# send multiple items
for i in range(5):
    anchor.send({'id': i, 'value': i * 10})

# send sentinel to signal end
anchor.send(None)

# get results
result = process.run()
print(f"Received {len(result)} items")

anchor.close()
```

### Multiple `Pipe`s

```python
from suitkaise.processing import Pipe, Skprocess

class DualPipeWorker(Skprocess):
    """
    A process with separate command and data pipes.
    """
    
    def __init__(self, cmd_pipe: Pipe.Point, data_pipe: Pipe.Point):
        self.cmd_pipe = cmd_pipe
        self.data_pipe = data_pipe
        self.process_config.runs = None  # run until stop
    
    def __run__(self):
        # check for commands (non-blocking would need timeout)
        try:
            cmd = self.cmd_pipe.recv()
            
            if cmd['action'] == 'process':
                # get data from data pipe
                data = self.data_pipe.recv()
                result = sum(data)
                self.cmd_pipe.send({'status': 'done', 'result': result})
            
            elif cmd['action'] == 'stop':
                self.stop()
                
        except Exception as e:
            self.cmd_pipe.send({'status': 'error', 'error': str(e)})
    
    def __result__(self):
        return "worker_stopped"


# create two pipe pairs
cmd_anchor, cmd_point = Pipe.pair()
data_anchor, data_point = Pipe.pair()

process = DualPipeWorker(cmd_point, data_point)
process.start()

# send process command
cmd_anchor.send({'action': 'process'})

# send data on data pipe
data_anchor.send([1, 2, 3, 4, 5])

# get result on command pipe
result = cmd_anchor.recv()
print(f"Result: {result}")  # Result: {'status': 'done', 'result': 15}

# stop the worker
cmd_anchor.send({'action': 'stop'})
process.wait()

cmd_anchor.close()
data_anchor.close()
```

---

## `Skprocess.tell()` and `Skprocess.listen()`

### Basic usage

```python
from suitkaise.processing import Skprocess
from suitkaise import timing
import hashlib

class CommandableProcess(Skprocess):
    """
    A process that receives commands via listen().
    
    - listen() from subprocess
    - tell() from parent
    - Bidirectional communication without Pipe
    """
    
    def __init__(self):
        self.process_config.runs = None  # run indefinitely
        self.multiplier = 1
        self.results = []
    
    def __prerun__(self):
        # check for commands (non-blocking with timeout)
        command = self.listen(timeout=0.1)
        
        if command is not None:
            if command.get('action') == 'set_multiplier':
                self.multiplier = command['value']
                print(f"[Child] Multiplier set to {self.multiplier}")
            
            elif command.get('action') == 'stop':
                self.stop()
    
    def __run__(self):
        # do some real work - compute hash
        data = f"run_{self._current_run}_mult_{self.multiplier}".encode()
        for _ in range(100 * self.multiplier):
            data = hashlib.sha256(data).digest()
        
        value = int.from_bytes(data[:4], 'big') % 1000
        self.results.append({'run': self._current_run, 'value': value})
        
        # notify parent of progress
        if self._current_run % 5 == 0:
            self.tell({'progress': self._current_run, 'latest': value})
    
    def __result__(self):
        return self.results


process = CommandableProcess()
process.start()

# let it run a bit
timing.sleep(0.3)

# send command to change multiplier
process.tell({'action': 'set_multiplier', 'value': 10})

# listen for progress updates
timing.sleep(0.3)
while True:
    msg = process.listen(timeout=0.1)
    if msg is None:
        break
    print(f"[Parent] Progress: {msg}")

# stop the process
process.tell({'action': 'stop'})
process.wait()

results = process.result()
print(f"Got {len(results)} results")
```

### Async usage

```python
import asyncio
import hashlib
from suitkaise.processing import Skprocess

class AsyncWorker(Skprocess):
    """
    A worker that uses tell/listen in async code.
    """
    
    def __init__(self, data_items: list):
        self.data_items = data_items
        self.process_config.runs = len(data_items)
        self.results = []
    
    def __run__(self):
        # process data item - compute hash
        item = self.data_items[self._current_run]
        hash_result = hashlib.sha256(item.encode()).hexdigest()
        self.results.append(hash_result[:16])
        
        # send status every 5 runs
        if self._current_run % 5 == 0:
            self.tell({
                'run': self._current_run,
                'status': 'working',
                'last_hash': hash_result[:8]
            })
    
    def __result__(self):
        return self.results


async def monitor_process():
    """Monitor a process using async listen."""
    
    data = [f"async_data_item_{i}" for i in range(20)]
    process = AsyncWorker(data)
    process.start()
    
    # monitor with async listen
    while process.is_alive:
        # use asynced() for non-blocking listen in async code
        msg = await process.listen.asynced()(timeout=0.2)
        if msg:
            print(f"Status: {msg}")
    
    await process.wait.asynced()()
    result = process.result()
    print(f"Final: {len(result)} hashes computed")


asyncio.run(monitor_process())
```

---

## `autoreconnect`

### Basic `autoreconnect`

```python
from suitkaise.processing import Skprocess, autoreconnect, Pool

# NOTE: This example shows the pattern - actual database would need real connection

@autoreconnect(
    start_threads=False,
    **{
        "psycopg2.Connection": {"*": "secret"},  # auth value is the password string
    }
)
class DatabaseWorker(Skprocess):
    """
    A process that uses a database connection.
    
    @autoreconnect ensures the connection is re-established
    in the subprocess after serialization.
    """
    
    def __init__(self, db_connection, query: str):
        self.db = db_connection
        self.query = query
        self.process_config.runs = 1
        self.results = None
    
    def __run__(self):
        # db connection was auto-reconnected in subprocess
        # self.db is now a live connection, not a Reconnector
        cursor = self.db.cursor()
        cursor.execute(self.query)
        self.results = cursor.fetchall()
        cursor.close()
    
    def __result__(self):
        return self.results


# Usage (conceptual):
# db = psycopg2.connect(host="localhost", database="mydb", password="secret")
# 
# with Pool(workers=2) as pool:
#     queries = [
#         (db, "SELECT * FROM users LIMIT 10"),
#         (db, "SELECT * FROM orders LIMIT 10"),
#     ]
#     results = pool.star().map(DatabaseWorker, queries)
```

### `autoreconnect` with Multiple Connection Types

```python
from suitkaise.processing import Skprocess, autoreconnect

@autoreconnect(
    start_threads=False,
    **{
        # PostgreSQL connections - auth value is the password string
        "psycopg2.Connection": {
            "*": "default_pass",           # default for all psycopg2 connections
            "analytics_db": "analytics_pass"  # specific override for analytics_db attr
        },
        # Redis connections
        "redis.Redis": {
            "*": "redis_secret"
        },
        # MongoDB connections
        "pymongo.MongoClient": {
            "*": "mongo_pass"
        }
    }
)
class MultiDbWorker(Skprocess):
    """
    A process that uses multiple database connections.
    
    Each connection type can have its own auth configuration.
    Use "*" for defaults, attr name for specific overrides.
    """
    
    def __init__(self, main_db, analytics_db, cache, mongo):
        self.main_db = main_db            # uses "*" auth
        self.analytics_db = analytics_db  # uses "analytics_db" auth
        self.cache = cache                # Redis with its auth
        self.mongo = mongo                # MongoDB with its auth
        self.process_config.runs = 1
    
    def __run__(self):
        # all connections are auto-reconnected in subprocess
        # ... use connections ...
        pass
    
    def __result__(self):
        return "done"
```

---

## Full-on distributed task queue

Goal: Build a production-ready task processing system that can handle thousands of jobs with automatic retries, failure tracking, and performance monitoring.

Say you have a batch of data transformation tasks (processing uploaded files, running ML inference on images, generating reports) that need to run in parallel with:
- Automatic retry when individual tasks fail (network issues, transient errors)
- Centralized statistics tracking (how many succeeded, failed, retried)
- Performance metrics (average processing time, P95 latency)
- Timeout protection (kill tasks that hang)

What this script does
1. Takes a list of 50 tasks, each with an ID and data payload
2. Distributes them across 4 parallel workers
3. Each task computes a cryptographic hash chain (this represents real CPU work)
4. Some tasks fail deterministically (simulating failures)
5. Failed tasks are automatically retried up to 3 times
6. All timing and success/failure stats are aggregated across workers
7. Prints a summary report with task statistics and performance metrics

```python
"""
A complete example of a distributed task queue using processing.

Features used:
- Pool for parallel worker management
- Share for tracking global state across processes
- Skprocess for structured task execution with lifecycle hooks
- Timing for performance metrics collection
- lives for automatic retry on failure
"""

from suitkaise.processing import Pool, Share, Skprocess
from suitkaise.timing import Sktimer
from suitkaise import timing
import random
import hashlib


class TaskStats:
    """
    Tracks statistics across all workers.
    
    This class will be auto-wrapped by Share with Skclass.
    """
    
    def __init__(self):
        self.total_tasks = 0
        self.completed = 0
        self.failed = 0
        self.retried = 0
    
    def record_complete(self):
        self.completed += 1
        self.total_tasks += 1
    
    def record_fail(self):
        self.failed += 1
        self.total_tasks += 1
    
    def record_retry(self):
        self.retried += 1


class TaskWorker(Skprocess):
    """
    A worker that processes a single task.
    
    Features:
    - Configurable failure probability for testing
    - Retry support via lives
    - Timing recorded to shared timer
    - Stats recorded to shared stats object
    """
    
    def __init__(self, shared: Share, task: dict, fail_prob: float = 0.1):
        # store references
        self.shared = shared
        self.task = task
        self.fail_prob = fail_prob
        
        # configure process
        self.process_config.runs = 1      # one run per task
        self.process_config.lives = 3     # retry up to 2 times
        self.process_config.timeouts.run = 5.0  # 5 second timeout
        
        # result storage
        self.result_data = None
        self.attempts = 0
    
    def __prerun__(self):
        # track retry attempts
        self.attempts += 1
        if self.attempts > 1:
            # this is a retry
            self.shared.stats.record_retry()
    
    def __run__(self):
        # record timing
        start = timing.time()
        
        try:
            # real work - compute hash chain with variable iterations
            iterations = random.randint(500, 2000)
            data = self.task['data'].encode()
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
            
            # deterministic "failure" based on task data for reproducibility
            if hash(self.task['data']) % 100 < int(self.fail_prob * 100):
                raise RuntimeError(f"Task {self.task['id']} failed (deterministic)")
            
            # process the task
            self.result_data = {
                'task_id': self.task['id'],
                'input': self.task['data'],
                'output': hashlib.sha256(data).hexdigest()[:32],
                'iterations': iterations,
                'attempts': self.attempts,
                'status': 'success'
            }
            
            # record success
            self.shared.stats.record_complete()
            
        finally:
            # always record timing
            elapsed = timing.elapsed(start)
            self.shared.timer.add_time(elapsed)
    
    def __error__(self):
        # all retries exhausted
        self.shared.stats.record_fail()
        
        return {
            'task_id': self.task['id'],
            'input': self.task['data'],
            'output': None,
            'attempts': self.attempts,
            'status': 'failed',
            'error': str(self.error)
        }
    
    def __result__(self):
        return self.result_data


def run_task_queue(tasks: list[dict], workers: int = 4, fail_prob: float = 0.1):
    """
    Process a list of tasks using a distributed worker pool.
    
    Args:
        tasks: List of task dicts with 'id' and 'data' keys
        workers: Number of parallel workers
        fail_prob: Probability of random failure (for testing)
    
    Returns:
        Dict with results and statistics
    """
    
    # set up shared state
    with Share() as share:
        share.stats = TaskStats()
        share.timer = Sktimer()
        
        # create argument tuples for star()
        args = [(share, task, fail_prob) for task in tasks]
        
        # process all tasks in parallel
        with Pool(workers=workers) as pool:
            results = pool.star().map(TaskWorker, args)
        
        # collect statistics
        stats = {
            'total_tasks': share.stats.total_tasks,
            'completed': share.stats.completed,
            'failed': share.stats.failed,
            'retried': share.stats.retried,
            'timing': {
                'total': share.timer.total_time,
                'mean': share.timer.mean,
                'min': share.timer.min,
                'max': share.timer.max,
                'p95': share.timer.percentile(95),
            }
        }
    
    return {
        'results': results,
        'stats': stats
    }


# example usage
if __name__ == "__main__":
    # create tasks
    tasks = [
        {'id': i, 'data': f'task_data_{i}'}
        for i in range(50)
    ]
    print(f"Processing {len(tasks)} tasks...")

    start = timing.time()
    
    # run the queue
    output = run_task_queue(tasks, workers=4, fail_prob=0.15)
    
    elapsed = timing.elapsed(start)
    
    # print results
    print(f"\n{'='*50}")
    print(f"TASK QUEUE RESULTS")
    print(f"{'='*50}")
    print(f"Total time: {elapsed:.2f}s")
    print(f"\nTask Statistics:")
    print(f"  Total processed: {output['stats']['total_tasks']}")
    print(f"  Completed:       {output['stats']['completed']}")
    print(f"  Failed:          {output['stats']['failed']}")
    print(f"  Retried:         {output['stats']['retried']}")
    print(f"\nTiming Statistics:")
    print(f"  Total work time: {output['stats']['timing']['total']:.2f}s")
    print(f"  Mean per task:   {output['stats']['timing']['mean']:.4f}s")
    print(f"  Min:             {output['stats']['timing']['min']:.4f}s")
    print(f"  Max:             {output['stats']['timing']['max']:.4f}s")
    print(f"  P95:             {output['stats']['timing']['p95']:.4f}s")
    
    # show sample results
    print(f"\nSample Results:")
    for r in output['results'][:5]:
        status = r['status']
        attempts = r['attempts']
        print(f"  Task {r['task_id']}: {status} (attempts: {attempts})")
```

---

## Full-on data streaming pipeline

Goal: Build a streaming data processor that can handle a continuous flow of incoming data items, distribute them across multiple workers, and collect results in real-time.

Say you're building a system that processes a stream of events (log entries, sensor readings, user actions, webhook payloads) where:
- Data arrives continuously and needs to be processed as it comes
- Multiple workers process data in parallel for throughput
- Workers run indefinitely until explicitly stopped (not batch processing)
- Parent process can monitor progress and worker status in real-time
- System shuts down gracefully, finishing in-flight work before exiting

What this script does
1. Starts 3 worker processes that run indefinitely
2. Generates a stream of 100 data items ("item_0", "item_1", etc.)
3. Distributes items to workers in round-robin fashion via `tell()`
4. Each worker computes a hash transformation on received items
5. Workers report their status periodically via `tell()` back to parent
6. Results accumulate in shared state accessible from all processes
7. After stream ends, sends stop signal to all workers
8. Collects final statistics and prints summary

```python
"""
A real-time data pipeline using processing.

Features used:
- Indefinite process with stop signal (runs=None)
- tell/listen for real-time bidirectional communication
- Share for accumulating results across processes
- Graceful shutdown with __onfinish__
"""

from suitkaise.processing import Skprocess, Share
from suitkaise.timing import Sktimer
from suitkaise import timing
import hashlib


class Results:
    """Accumulates processed data."""
    def __init__(self):
        self.items = []
        self.count = 0
    
    def add(self, item):
        self.items.append(item)
        self.count += 1


class DataPipelineWorker(Skprocess):
    """
    A worker that processes streaming data.
    
    - Runs indefinitely until parent sends stop
    - Receives data items via listen()
    - Processes and stores results in Share
    - Sends status updates via tell()
    """
    
    def __init__(self, shared: Share, worker_id: int):
        self.shared = shared
        self.worker_id = worker_id
        
        # run indefinitely
        self.process_config.runs = None
        
        self.processed = 0
    
    def __prerun__(self):
        # check for stop signal or data
        msg = self.listen(timeout=0.1)
        
        if msg is not None:
            if msg.get('action') == 'stop':
                # graceful shutdown
                self.stop()
            elif msg.get('action') == 'data':
                # store data for processing
                self._pending_data = msg['payload']
            else:
                self._pending_data = None
        else:
            self._pending_data = None
    
    def __run__(self):
        if self._pending_data is None:
            # no data to process
            return
        
        # process the data - real work
        with TimeThis() as run_timer:
            data = self._pending_data
            
            # transform the data - compute hash and transform
            if isinstance(data, str):
                data_bytes = data.encode()
                # compute hash chain
                for _ in range(500):
                    data_bytes = hashlib.sha256(data_bytes).digest()
                output = hashlib.sha256(data_bytes).hexdigest()[:16]
            else:
                output = data * 2
            
            result = {
                'worker': self.worker_id,
                'input': data,
                'output': output,
                'timestamp': timing.time()
            }
        
        
        # store result in shared state
        self.shared.results.add(result)
        self.shared.timer.add_time(run_timer.most_recent)
        
        self.processed += 1
        self._pending_data = None
    
    def __postrun__(self):
        # send periodic status updates
        if self.processed > 0 and self.processed % 10 == 0:
            self.tell({
                'worker': self.worker_id,
                'processed': self.processed,
                'status': 'running'
            })
    
    def __onfinish__(self):
        # send final status
        self.tell({
            'worker': self.worker_id,
            'processed': self.processed,
            'status': 'finished'
        })
    
    def __result__(self):
        return {
            'worker_id': self.worker_id,
            'total_processed': self.processed
        }

def run_pipeline(data_stream, num_workers: int = 2, timeout: float = 5.0):
    """
    Run a data pipeline with multiple workers.
    
    Args:
        data_stream: Iterator of data items to process
        num_workers: Number of parallel workers
        timeout: Maximum time to run
    
    Returns:
        Dict with results and worker stats
    """
    
    with Share() as share:
        share.results = Results()
        share.timer = Sktimer()
        
        # start workers
        workers = []
        for i in range(num_workers):
            worker = DataPipelineWorker(share, worker_id=i)
            worker.start()
            workers.append(worker)
        
        # distribute data to workers
        start_time = timing.time()
        worker_idx = 0
        
        for item in data_stream:
            # check timeout
            if timing.elapsed(start_time) > timeout:
                break
            
            # round-robin to workers
            workers[worker_idx].tell({'action': 'data', 'payload': item})
            worker_idx = (worker_idx + 1) % num_workers
            
            # small delay to avoid flooding - allows workers to process
            timing.sleep(0.01)
        
        # signal workers to stop
        for worker in workers:
            worker.tell({'action': 'stop'})
        
        # collect status messages
        statuses = []
        for worker in workers:
            while True:
                msg = worker.listen(timeout=0.5)
                if msg is None:
                    break
                statuses.append(msg)
        
        # wait for all workers
        for worker in workers:
            worker.wait()
        
        # collect results
        worker_results = [worker.result() for worker in workers]
        
        return {
            'results': share.results.items,
            'count': share.results.count,
            'worker_stats': worker_results,
            'timing': {
                'total': share.timer.total_time,
                'mean': share.timer.mean if share.timer.num_times > 0 else 0,
            },
            'statuses': statuses
        }


# example usage
if __name__ == "__main__":
    # create a data stream
    def generate_data(n):
        for i in range(n):
            yield f"item_{i}"
    
    print("Starting pipeline...")
    output = run_pipeline(generate_data(100), num_workers=3, timeout=10.0)
    
    print(f"\nPipeline Results:")
    print(f"  Total processed: {output['count']}")
    print(f"  Total time: {output['timing']['total']:.2f}s")
    print(f"  Mean per item: {output['timing']['mean']:.4f}s")
    
    print(f"\nWorker Stats:")
    for ws in output['worker_stats']:
        print(f"  Worker {ws['worker_id']}: {ws['total_processed']} items")
    
    print(f"\nSample Results:")
    for r in output['results'][:5]:
        print(f"  {r['input']} -> {r['output']} (worker {r['worker']})")
```
