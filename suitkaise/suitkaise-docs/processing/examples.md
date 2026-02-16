# `<suitkaise-api>processing</suitkaise-api>` Examples

## Basic `<suitkaise-api>Skprocess</suitkaise-api>`

### Simple Counter Process

A minimal process that counts iterations.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class CounterProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A simple process that counts up to a specified number.
    
    - Basic __init__ with <suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api>
    - <suitkaise-api>__run__</suitkaise-api> for main work
    - <suitkaise-api>__result__</suitkaise-api> to return data
    """
    
    def __init__(self, target: int = 10):
        # store target count
        # (<suitkaise-api>process_config</suitkaise-api> is already initialized by <suitkaise-api>Skprocess</suitkaise-api>._setup)
        self.target = target
        self.counter = 0
        
        # configure: <suitkaise-api>run</suitkaise-api> exactly 'target' iterations
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = target
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # increment counter each iteration
        self.counter += 1
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        # return final count when process completes
        return self.counter


# create process with target of 100
process = CounterProcess(target=100)

# start the subprocess
process.<suitkaise-api>start</suitkaise-api>()

# wait for completion (blocks until done)
process.<suitkaise-api>wait</suitkaise-api>()

# get the <suitkaise-api>result</suitkaise-api>
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>result</suitkaise-api>()
print(f"Final count: {<suitkaise-api>result</suitkaise-api>}")  # Final count: 100
```

### Using `<suitkaise-api>run</suitkaise-api>()`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class QuickProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that does quick work.
    
    Using <suitkaise-api>run</suitkaise-api>() to start, wait, and get <suitkaise-api>result</suitkaise-api> in one call
    """
    
    def __init__(self, data: list):
        self.data = data
        self.results = []
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = len(data)
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # process one item per <suitkaise-api>run</suitkaise-api>
        item = self.data[self._current_run]
        self.results.append(item * 2)
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.results


# <suitkaise-api>run</suitkaise-api>() combines <suitkaise-api>start</suitkaise-api>(), <suitkaise-api>wait</suitkaise-api>(), and <suitkaise-api>result</suitkaise-api>()
process = QuickProcess([1, 2, 3, 4, 5])
results = process.<suitkaise-api>run</suitkaise-api>()
print(results)  # [2, 4, 6, 8, 10]
```

### Full Lifecycle Process

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class DataProcessor(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process demonstrating all lifecycle methods.
    
    - <suitkaise-api>__prerun__</suitkaise-api>: Setup before each <suitkaise-api>run</suitkaise-api>
    - <suitkaise-api>__run__</suitkaise-api>: Main work
    - <suitkaise-api>__postrun__</suitkaise-api>: Cleanup after each <suitkaise-api>run</suitkaise-api>
    - <suitkaise-api>__onfinish__</suitkaise-api>: Final cleanup
    - <suitkaise-api>__result__</suitkaise-api>: Return data
    """
    
    def __init__(self, batch_size: int = 5):
        # configure process
        self.batch_size = batch_size
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 3  # process 3 batches
        
        # state tracking
        self.current_batch = None
        self.processed_batches = []
        self.total_items = 0
    
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        # called before each <suitkaise-api>__run__</suitkaise-api>
        # fetch the next batch of data
        batch_number = self._current_run
        self.current_batch = [
            f"item_{batch_number}_{i}" 
            for i in range(self.batch_size)
        ]
        print(f"[<suitkaise-api>prerun</suitkaise-api>] Fetched batch {batch_number}: {len(self.current_batch)} items")
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # called each iteration - do the main work
        # process each item in the current batch
        processed = []
        for item in self.current_batch:
            <suitkaise-api>result</suitkaise-api> = item.upper()
            processed.append(<suitkaise-api>result</suitkaise-api>)
            self.total_items += 1
        
        # store for <suitkaise-api>postrun</suitkaise-api>
        self._processed = processed
        print(f"[<suitkaise-api>run</suitkaise-api>] Processed {len(processed)} items")
    
    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        # called after each <suitkaise-api>__run__</suitkaise-api>
        # save results and cleanup
        self.processed_batches.append(self._processed)
        self.current_batch = None  # clear for next iteration
        self._processed = None
        print(f"[<suitkaise-api>postrun</suitkaise-api>] Saved batch, total batches: {len(self.processed_batches)}")
    
    def <suitkaise-api>__onfinish__</suitkaise-api>(self):
        # called once when process ends (stop signal or <suitkaise-api>run</suitkaise-api> limit)
        # final cleanup and summary
        print(f"[<suitkaise-api>onfinish</suitkaise-api>] Finished <suitkaise-api>processing</suitkaise-api> {self.total_items} total items")
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        # return the final data
        return {
            'batches': self.processed_batches,
            'total_items': self.total_items,
            'num_batches': len(self.processed_batches)
        }

    # NOTE: not implementing <suitkaise-api>__error__</suitkaise-api> to let <suitkaise-api>Skprocess</suitkaise-api> decide what <suitkaise-api>error</suitkaise-api> to raise


process = DataProcessor(batch_size=3)
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>run</suitkaise-api>()

print(f"\nResult: {<suitkaise-api>result</suitkaise-api>['num_batches']} batches, {<suitkaise-api>result</suitkaise-api>['total_items']} items")
# Output:
# [<suitkaise-api>prerun</suitkaise-api>] Fetched batch 0: 3 items
# [<suitkaise-api>run</suitkaise-api>] Processed 3 items
# [<suitkaise-api>postrun</suitkaise-api>] Saved batch, total batches: 1
# [<suitkaise-api>prerun</suitkaise-api>] Fetched batch 1: 3 items
# [<suitkaise-api>run</suitkaise-api>] Processed 3 items
# [<suitkaise-api>postrun</suitkaise-api>] Saved batch, total batches: 2
# [<suitkaise-api>prerun</suitkaise-api>] Fetched batch 2: 3 items
# [<suitkaise-api>run</suitkaise-api>] Processed 3 items
# [<suitkaise-api>postrun</suitkaise-api>] Saved batch, total batches: 3
# [<suitkaise-api>onfinish</suitkaise-api>] Finished <suitkaise-api>processing</suitkaise-api> 9 total items

# Result: 3 batches, 9 items
```

### Indefinite Process with `<suitkaise-api>stop</suitkaise-api>()`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>

class MonitorProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that <suitkaise-api>runs</suitkaise-api> indefinitely until stopped.
    
    - `<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api>=None` for indefinite execution
    - Using <suitkaise-api>stop</suitkaise-api>() from the parent process
    - Graceful shutdown with <suitkaise-api>__onfinish__</suitkaise-api>
    """
    
    def __init__(self):
        # no <suitkaise-api>run</suitkaise-api> limit - <suitkaise-api>runs</suitkaise-api> until <suitkaise-api>stop</suitkaise-api>() is called
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = None
        self.events = []
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # record timestamp and system info each iteration
        import os
        import hashlib
        payload = f"{self._current_run}:{os.getpid()}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        self.events.append({
            '<suitkaise-api>run</suitkaise-api>': self._current_run,
            'time': <suitkaise-api>timing</suitkaise-api>.time(),
            'pid': os.getpid(),
            'memory': self._get_memory_usage(),
            'hash': digest[:12],
        })
    
    def _get_memory_usage(self):
        """Get current process memory usage in MB."""
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024
    
    def <suitkaise-api>__onfinish__</suitkaise-api>(self):
        # called when <suitkaise-api>stop</suitkaise-api>() signal is received
        print(f"Monitor shutting down after {len(self.events)} events")
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.events


# start the monitor
process = MonitorProcess()
process.<suitkaise-api>start</suitkaise-api>()

# do some work while it collects data
import hashlib
data = b"monitor_work"
for _ in range(2000):
    data = hashlib.sha256(data).digest()

# signal graceful stop
<suitkaise-api>timing</suitkaise-api>.sleep(0.05)
process.<suitkaise-api>stop</suitkaise-api>()

# wait for it to finish
process.<suitkaise-api>wait</suitkaise-api>()

# get results
events = process.<suitkaise-api>result</suitkaise-api>()
print(f"Captured {len(events)} events")
```

### Time-Limited Process with `<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>join_in</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class TimeBoundProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that <suitkaise-api>runs</suitkaise-api> for a maximum amount of time.
    
    - `<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>join_in</suitkaise-api>` to set maximum runtime
    - `<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api>=None` combined with `<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>join_in</suitkaise-api>` for time-based limits
    """
    
    def __init__(self, max_seconds: float = 10.0):
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = None # this is the default
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>join_in</suitkaise-api> = max_seconds
        
        self.iterations = 0
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        import hashlib
        payload = f"iter_{self._current_run}".encode()
        digest = hashlib.sha256(payload).digest()
        self.iterations += digest[0]

    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.iterations


process = TimeBoundProcess(max_seconds=1.0)
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>run</suitkaise-api>()
print(f"Completed {<suitkaise-api>result</suitkaise-api>} iterations in ~1 second")
# Completed ~10 iterations in ~1 second
```

### Process with Retries (Lives)

```python
import hashlib
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>RunError</suitkaise-api>, <suitkaise-api>ProcessError</suitkaise-api>

class UnreliableProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that may fail but retries automatically.
    
    - `<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>lives</suitkaise-api>` for automatic retry on failure
    - State preservation across retries
    - <suitkaise-api>__error__</suitkaise-api> for handling final failure
    """
    
    def __init__(self):
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 10
        # allow 3 total attempts (2 retries)
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>lives</suitkaise-api> = 3
        
        self.successful_runs = 0
        self.attempt_count = 0
    
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        # track attempts
        self.attempt_count += 1
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # deterministic failure based on real work
        payload = f"<suitkaise-api>run</suitkaise-api>:{self._current_run}".encode()
        digest = hashlib.sha256(payload).digest()
        if digest[0] % 5 == 0:
            raise RuntimeError(f"Content failure on <suitkaise-api>run</suitkaise-api> {self._current_run}")
        
        # success!
        self.successful_runs += 1
    
    def <suitkaise-api>__error__</suitkaise-api>(self):
        # called when all <suitkaise-api>lives</suitkaise-api> exhausted
        # self.<suitkaise-api>error</suitkaise-api> contains the exception
        print(f"Process failed after {self.attempt_count} attempts")
        print(f"Error: {self.<suitkaise-api>error</suitkaise-api>}")
        
        # return partial results
        return {
            'status': 'failed',
            'successful_runs': self.successful_runs,
            '<suitkaise-api>error</suitkaise-api>': str(self.<suitkaise-api>error</suitkaise-api>)
        }
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return {
            'status': 'success',
            'successful_runs': self.successful_runs,
            'total_attempts': self.attempt_count
        }


# set seed for reproducibility
process = UnreliableProcess()
try:
    <suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>run</suitkaise-api>()
    print(f"Result: {<suitkaise-api>result</suitkaise-api>}")
except <suitkaise-api>ProcessError</suitkaise-api> as e:
    print(f"Process ultimately failed: {e}")
```

### Timeouts on Lifecycle Methods

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>ProcessTimeoutError</suitkaise-api>

class SlowProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process with timeout protection on lifecycle methods.
    
    - Setting <suitkaise-api>timeouts</suitkaise-api> for individual lifecycle sections
    - <suitkaise-api>ProcessTimeoutError</suitkaise-api> when <suitkaise-api>timeouts</suitkaise-api> are exceeded
    """
    
    def __init__(self):
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 5
        
        # set <suitkaise-api>timeouts</suitkaise-api> for each section
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>prerun</suitkaise-api> = 1.0   # 1 second max
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>run</suitkaise-api> = 2.0      # 2 seconds max
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>postrun</suitkaise-api> = 1.0  # 1 second max
        
        self.completed_runs = 0
    
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        # quick <suitkaise-api>prerun</suitkaise-api> - well within timeout
        pass
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # CPU-intensive work that varies in duration
        if self._current_run == 3:
            # this <suitkaise-api>run</suitkaise-api> will exceed timeout - compute intensive fibonacci
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
    
    def <suitkaise-api>__error__</suitkaise-api>(self):
        # handle timeout <suitkaise-api>error</suitkaise-api>
        if isinstance(self.<suitkaise-api>error</suitkaise-api>, <suitkaise-api>ProcessTimeoutError</suitkaise-api>):
            print(f"Timeout in {self.<suitkaise-api>error</suitkaise-api>.section} after {self.<suitkaise-api>error</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>}s")
        return {
            'status': 'timeout',
            'completed_runs': self.completed_runs
        }
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return {
            'status': 'success',
            'completed_runs': self.completed_runs
        }


process = SlowProcess()
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>run</suitkaise-api>()
print(f"Result: {<suitkaise-api>result</suitkaise-api>}")
# Timeout in <suitkaise-api>__run__</suitkaise-api> after 2.0s
# Result: {'status': 'timeout', 'completed_runs': 3}
```

### Accessing Timing Data

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>
import hashlib

class TimedProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process demonstrating <suitkaise-api>timing</suitkaise-api> access.
    
    - Accessing per-method timers
    - Using process_timer for aggregate stats
    - Timer statistics (mean, min, max, percentile)
    """
    
    def __init__(self, <suitkaise-api>runs</suitkaise-api>: int = 20):
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = <suitkaise-api>runs</suitkaise-api>
        self.data = [f"data_block_{i}" for i in range(1000)]
    
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        # variable <suitkaise-api>prerun</suitkaise-api> work - rotate data
        self.data = self.data[-1:] + self.data[:-1]
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # variable <suitkaise-api>run</suitkaise-api> work - hash computations
        iterations = 50 + (self._current_run * 7 % 100)
        for _ in range(iterations):
            for item in self.data[:100]:
                hashlib.sha256(item.encode()).hexdigest()
    
    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        # quick <suitkaise-api>postrun</suitkaise-api> - sort a slice
        sorted(self.data[:50])
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return "done"


process = TimedProcess(<suitkaise-api>runs</suitkaise-api>=20)
process.<suitkaise-api>run</suitkaise-api>()

# access individual timers
print(f"<suitkaise-api>__prerun__</suitkaise-api> <suitkaise-api>timing</suitkaise-api>:")
print(f"  mean:   {process.<suitkaise-api>__prerun__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.4f}s")
print(f"  min:    {process.<suitkaise-api>__prerun__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.min:.4f}s")
print(f"  max:    {process.<suitkaise-api>__prerun__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.max:.4f}s")

print(f"\n__run__ <suitkaise-api>timing</suitkaise-api>:")
print(f"  mean:   {process.<suitkaise-api>__run__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.4f}s")
print(f"  p50:    {process.<suitkaise-api>__run__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(50):.4f}s")
print(f"  p95:    {process.<suitkaise-api>__run__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95):.4f}s")

print(f"\n__postrun__ <suitkaise-api>timing</suitkaise-api>:")
print(f"  total:  {process.<suitkaise-api>__postrun__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>:.4f}s")

# aggregate timer for full iterations
print(f"\nFull iteration <suitkaise-api>timing</suitkaise-api> (<suitkaise-api>prerun</suitkaise-api> + <suitkaise-api>run</suitkaise-api> + <suitkaise-api>postrun</suitkaise-api>):")
print(f"  mean:   {process.process_timer.<suitkaise-api>mean</suitkaise-api>:.4f}s")
print(f"  total:  {process.process_timer.<suitkaise-api>total_time</suitkaise-api>:.4f}s")
print(f"  count:  {process.process_timer.<suitkaise-api>num_times</suitkaise-api>}")
```

### Async Process Execution

```python
import asyncio
import hashlib
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class AsyncFriendlyProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    Running processes in async code.
    
    - Using .<suitkaise-api>asynced</suitkaise-api>() modifier on <suitkaise-api>wait</suitkaise-api>() and <suitkaise-api>result</suitkaise-api>()
    - Running multiple processes concurrently
    """
    
    def __init__(self, process_id: int, data_chunks: list):
        self.process_id = process_id
        self.data_chunks = data_chunks
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = len(data_chunks)
        self.results = []
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # process a data chunk - compute hash
        chunk = self.data_chunks[self._current_run]
        hash_result = hashlib.sha256(chunk.encode()).hexdigest()
        self.results.append({
            'process': self.process_id,
            '<suitkaise-api>run</suitkaise-api>': self._current_run,
            'hash': hash_result[:16]
        })
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
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
        p.<suitkaise-api>start</suitkaise-api>()
        processes.append(p)
    
    # wait for all concurrently using <suitkaise-api>asynced</suitkaise-api>()
    wait_tasks = [p.<suitkaise-api>wait</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()() for p in processes]
    await asyncio.gather(*wait_tasks)
    
    # get all results
    results = [p.<suitkaise-api>result</suitkaise-api>() for p in processes]
    
    return results


# <suitkaise-api>run</suitkaise-api> the async code
results = asyncio.<suitkaise-api>run</suitkaise-api>(run_processes_concurrently())
for i, r in enumerate(results):
    print(f"Process {i}: {len(r)} results")
```

### Background Execution with Future

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import math

class BackgroundProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    Running a process in the <suitkaise-api>background</suitkaise-api>.
    
    - Using .<suitkaise-api>background</suitkaise-api>() modifier
    - Doing other work while process <suitkaise-api>runs</suitkaise-api>
    - Getting <suitkaise-api>result</suitkaise-api> from Future
    """
    
    def __init__(self, numbers: list):
        self.numbers = numbers
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = len(numbers)
        self.results = []
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
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
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.results


# start process and get Future immediately
numbers = [123456789, 987654321, 1000000007, 999999937, 2147483647]
process = BackgroundProcess(numbers)
future = process.<suitkaise-api>run</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()()

# do other work while process <suitkaise-api>runs</suitkaise-api>
print("Process running in <suitkaise-api>background</suitkaise-api>...")
main_thread_work = []
for i in range(5):
    # compute something in main thread
    main_thread_work.append(math.factorial(100 + i))
    print(f"  Main thread computed factorial({100 + i})")

# now get the <suitkaise-api>result</suitkaise-api> (may block if not done)
<suitkaise-api>result</suitkaise-api> = future.<suitkaise-api>result</suitkaise-api>()
print(f"\nProcess computed {len(<suitkaise-api>result</suitkaise-api>)} factorizations")
for r in <suitkaise-api>result</suitkaise-api>[:3]:
    print(f"  {r['number']} = {r['factors']}")
```

---

## `<suitkaise-api>Pool</suitkaise-api>`

### Basic `map`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>

def square(x):
    """Simple function to square a number."""
    return x * x


# create a pool with 4 workers
pool = <suitkaise-api>Pool</suitkaise-api>(workers=4)

# map applies the function to each item
# results are returned in the same order as inputs
items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
results = pool.<suitkaise-api>map</suitkaise-api>(square, items)

print(results)  # [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]

# always close the pool when done
pool.close()
```

### `<suitkaise-api>Pool</suitkaise-api>` as Context Manager

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>
import hashlib
import json

def process_data(data):
    """Process a single data item - normalize and hash."""
    # normalize the data
    normalized = data.strip().lower()
    
    # compute a hash
    data_hash = hashlib.md5(normalized.encode()).hexdigest()
    
    # return processed <suitkaise-api>result</suitkaise-api>
    return {
        'original': data,
        'normalized': normalized,
        'hash': data_hash[:8]
    }


# use context manager for automatic cleanup
with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    items = ["  Apple  ", "BANANA", "Cherry", "  DATE", "elderberry"]

    results = pool.<suitkaise-api>map</suitkaise-api>(process_data, items)

    for r in results:
        print(f"{r['original']:>12} -> {r['normalized']:<12} ({r['hash']})")

        
# pool is automatically closed when exiting the 'with' block
```

### Using `<suitkaise-api>star</suitkaise-api>()` for Tuple Unpacking

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>

def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(x, y, z):
    """Multiply three numbers."""
    return x * y * z


with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    # without <suitkaise-api>star</suitkaise-api>(): each item is passed as a single argument
    # the function receives a tuple
    # pool.<suitkaise-api>map</suitkaise-api>(add, [(1, 2), (3, 4)])  # ERROR: add() expects 2 args, got 1 tuple
    
    # with <suitkaise-api>star</suitkaise-api>(): tuples are unpacked into positional arguments
    pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]
    sums = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(add, pairs)
    print(f"Sums: {sums}")  # Sums: [3, 7, 11, 15]
    
    # works with any number of arguments
    triples = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]
    products = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(multiply, triples)
    print(f"Products: {products}")  # Products: [6, 120, 504]
```

### `unordered_map` for Fastest List

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>
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


with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    items = list(range(20))
    
    # unordered_map returns a list (like map)
    # but results are in completion order (like unordered_imap)
    results = pool.<suitkaise-api>unordered_map</suitkaise-api>(variable_work, items)
    
    print(f"Got {len(results)} results")
    print(f"Order received: {[r['item'] for r in results]}")
    # Order is NOT sequential - items with fewer iterations complete first
    
    # useful when you need all results but don't care about order
    # faster than <suitkaise-api>map</suitkaise-api>() because you don't wait for slow items to unblock fast ones
```

### `imap` for Memory Efficiency

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>
import hashlib

def heavy_computation(item):
    """Compute SHA-256 hash multiple times, return large <suitkaise-api>result</suitkaise-api>."""
    # do real computation - iterative hashing
    data = str(item).encode()
    for _ in range(1000):
        data = hashlib.sha256(data).digest()
    
    # return <suitkaise-api>result</suitkaise-api> with computed hash and derived data
    final_hash = hashlib.sha256(data).hexdigest()
    return {
        'input': item,
        'hash': final_hash,
        'derived': [final_hash[i:i+4] for i in range(0, 64, 4)]  # 16 chunks
    }


with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    # imap returns an iterator - results are yielded one at a time
    # this is memory efficient for large datasets
    items = range(100)
    
    processed = 0
    for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>imap</suitkaise-api>(heavy_computation, items):
        # process each <suitkaise-api>result</suitkaise-api> as it arrives (in order)
        processed += 1
        if processed % 20 == 0:
            print(f"Processed {processed} items, latest hash: {<suitkaise-api>result</suitkaise-api>['hash'][:16]}...")
    
    print(f"Done! Processed {processed} total items")
```

### `unordered_imap` for Fastest Results

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>
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


with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    items = list(range(20))
    
    print("Using unordered_imap - fastest results first:")
    results = []
    for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>unordered_imap</suitkaise-api>(variable_work, items):
        # results arrive as they complete (NOT in order)
        results.append(<suitkaise-api>result</suitkaise-api>)
        print(f"  Got item {<suitkaise-api>result</suitkaise-api>['item']:2d} ({<suitkaise-api>result</suitkaise-api>['iterations']:4d} iters)")
    
    print(f"\nOrder received: {[r['item'] for r in results]}")
    # Order is NOT sequential - items with fewer iterations complete first
```

### `<suitkaise-api>Pool</suitkaise-api>` with Timeout

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>

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


with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    items = [1, 2, 3, 4, 5, 6, 7, 8]
    
    try:
        # timeout applies to the entire operation
        results = pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(2.0)(slow_function, items)
        print(results)
    except TimeoutError as e:
        print(f"Operation timed out: {e}")
    
    # timeout also works with imap - use items that complete quickly
    try:
        for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>imap</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(5.0)(slow_function, [1, 2, 3]):
            print(f"Got: {<suitkaise-api>result</suitkaise-api>}")
    except TimeoutError:
        print("imap timed out")
```

### Background Execution with `<suitkaise-api>Pool</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>
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


with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    items = list(range(20))
    
    # start map in background - returns Future immediately
    future = pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(compute, items)
    
    # do other work while pool processes
    print("<suitkaise-api>Pool</suitkaise-api> working in <suitkaise-api>background</suitkaise-api>...")
    main_work = []
    for i in range(3):
        # compute something in main thread
        <suitkaise-api>result</suitkaise-api> = math.factorial(500 + i * 100)
        main_work.append(len(str(<suitkaise-api>result</suitkaise-api>)))
        print(f"  Main thread computed factorial, {main_work[-1]} digits")
    
    # get results (blocks if not done)
    results = future.<suitkaise-api>result</suitkaise-api>()
    print(f"Got {len(results)} factorizations")
    print(f"First <suitkaise-api>result</suitkaise-api>: {results[0]}")
```

### Async `<suitkaise-api>Pool</suitkaise-api>` Operations

```python
import asyncio
import hashlib
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>

def cpu_work(x):
    """CPU-bound work - compute hash chain."""
    data = str(x).encode()
    for _ in range(1000):
        data = hashlib.sha256(data).digest()
    return {'input': x, 'hash': hashlib.sha256(data).hexdigest()[:16]}


async def process_batches():
    """Process multiple batches concurrently."""
    
    with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
        # create multiple async map operations
        batch1 = list(range(10))
        batch2 = list(range(10, 20))
        batch3 = list(range(20, 30))
        
        # <suitkaise-api>run</suitkaise-api> all batches concurrently using <suitkaise-api>asynced</suitkaise-api>()
        results = await asyncio.gather(
            pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(cpu_work, batch1),
            pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(cpu_work, batch2),
            pool.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(cpu_work, batch3),
        )
        
        return results


results = asyncio.<suitkaise-api>run</suitkaise-api>(process_batches())
print(f"Batch 1: {len(results[0])} items, first: {results[0][0]}")
print(f"Batch 2: {len(results[1])} items, first: {results[1][0]}")
print(f"Batch 3: {len(results[2])} items, first: {results[2][0]}")
```

### Using `<suitkaise-api>Skprocess</suitkaise-api>` with `<suitkaise-api>Pool</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
import hashlib
import json

class DataTransformer(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A <suitkaise-api>Skprocess</suitkaise-api> that can be used with <suitkaise-api>Pool</suitkaise-api>.
    
    <suitkaise-api>Pool</suitkaise-api> creates an instance for each item and <suitkaise-api>runs</suitkaise-api> it.
    """
    
    def __init__(self, input_data: dict):
        # receive input through __init__
        self.input_data = input_data
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1  # single <suitkaise-api>run</suitkaise-api> per item
        
        self.transformed = None
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
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
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.transformed


# create input data
items = [
    {'id': 1, 'value': 10},
    {'id': 2, 'value': 20},
    {'id': 3, 'value': 30},
    {'id': 4, 'value': 40},
]

with <suitkaise-api>Pool</suitkaise-api>(workers=2) as pool:
    # <suitkaise-api>Pool</suitkaise-api> creates DataTransformer(item) for each item
    # and <suitkaise-api>runs</suitkaise-api> it, collecting results
    results = pool.<suitkaise-api>map</suitkaise-api>(DataTransformer, items)
    
    for r in results:
        print(f"ID {r['original_id']}: {r['original_value']} -> doubled={r['doubled']}, squared={r['squared']}")
# ID 1: 10 -> doubled=20, squared=100
# ID 2: 20 -> doubled=40, squared=400
# ID 3: 30 -> doubled=60, squared=900
# ID 4: 40 -> doubled=80, squared=1600
```

### Combining `<suitkaise-api>star</suitkaise-api>()` with Modifiers

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>
import asyncio
import math

def process_pair(x, y):
    """Process a pair of values - compute combination and factorial ratio."""
    # compute nCr (n choose r) where x >= y
    n, r = max(x, y), min(x, y)
    <suitkaise-api>result</suitkaise-api> = math.comb(n * 10, r * 2)
    return {'inputs': (x, y), 'comb': <suitkaise-api>result</suitkaise-api>, 'digits': len(str(<suitkaise-api>result</suitkaise-api>))}


async def main():
    with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
        pairs = [(1, 2), (3, 4), (5, 6), (7, 8)]
        
        # <suitkaise-api>star</suitkaise-api>() composes with all modifiers
        
        # star + timeout
        results = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(5.0)(process_pair, pairs)
        print(f"star + timeout: {[r['digits'] for r in results]} digits")
        
        # star + background
        future = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(process_pair, pairs)
        results = future.<suitkaise-api>result</suitkaise-api>()
        print(f"star + background: {[r['digits'] for r in results]} digits")
        
        # star + async
        results = await pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(process_pair, pairs)
        print(f"star + async: {[r['digits'] for r in results]} digits")
        
        # star + imap
        print("star + imap:", end=" ")
        for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>imap</suitkaise-api>(process_pair, pairs):
            print(f"{<suitkaise-api>result</suitkaise-api>['inputs']}", end=" ")
        print()
        
        # star + unordered_imap
        print("star + unordered_imap:", end=" ")
        for <suitkaise-api>result</suitkaise-api> in pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>unordered_imap</suitkaise-api>(process_pair, pairs):
            print(f"{<suitkaise-api>result</suitkaise-api>['inputs']}", end=" ")
        print()


asyncio.<suitkaise-api>run</suitkaise-api>(main())
```

### Error Handling in `<suitkaise-api>Pool</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>

def risky_function(x):
    """Function that might raise an <suitkaise-api>error</suitkaise-api>."""
    if x == 3:
        raise ValueError(f"Cannot process {x}")
    return x * 2


with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    items = [1, 2, 3, 4, 5]
    
    try:
        # <suitkaise-api>error</suitkaise-api> in any worker propagates to main process
        results = pool.<suitkaise-api>map</suitkaise-api>(risky_function, items)
    except RuntimeError as e:
        print(f"Caught <suitkaise-api>error</suitkaise-api>: {e}")
    
    # process the items that don't cause errors
    safe_items = [1, 2, 4, 5]
    results = pool.<suitkaise-api>map</suitkaise-api>(risky_function, safe_items)
    print(f"Safe results: {results}")  # [2, 4, 8, 10]
```

---

## `<suitkaise-api>Share</suitkaise-api>`

### Basic Shared Counter using `<suitkaise-api>Share</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

# create a <suitkaise-api>Share</suitkaise-api> and assign a counter object
share = <suitkaise-api>Share</suitkaise-api>()

class Counter:
    def __init__(self):
        self.value = 0
    
    def increment(self, amount: int = 1):
        self.value += amount

share.counter = Counter()


class CounterProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that increments a shared counter.
    
    Demonstrates basic <suitkaise-api>Share</suitkaise-api> usage across processes.
    """
    # pass the <suitkaise-api>Share</suitkaise-api> instance to the process
    def __init__(self, shared: <suitkaise-api>Share</suitkaise-api>, amount: int = 1):
        self.shared = shared
        self.amount = amount
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 10  # increment 10 times
    
    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        # increment the shared counter
        # use a method to avoid read/modify/write races
        self.shared.counter.increment(self.amount)
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return "done"


# <suitkaise-api>run</suitkaise-api> 5 processes, each incrementing 10 times
with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
    # pass the same share instance to all processes
    pool.<suitkaise-api>map</suitkaise-api>(CounterProcess, [share] * 5)

# counter was incremented 50 <suitkaise-api>times</suitkaise-api> (5 processes × 10 <suitkaise-api>runs</suitkaise-api> each)
print(f"Final counter: {share.counter.value}") # will be 50

# always stop share when done to save resources
share.<suitkaise-api>stop</suitkaise-api>()
```

### Sharing Complex Objects (like `<suitkaise-api>Sktimer</suitkaise-api>`)

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib

# create <suitkaise-api>Share</suitkaise-api> and assign a timer
share = <suitkaise-api>Share</suitkaise-api>()
share.<suitkaise-api>timer</suitkaise-api> = <suitkaise-api>Sktimer</suitkaise-api>()


class TimedWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that records <suitkaise-api>timing</suitkaise-api> to a shared <suitkaise-api>timer</suitkaise-api>.
    
    Demonstrates sharing <suitkaise-api>suitkaise</suitkaise-api> objects with _shared_meta.
    """
    
    def __init__(self, shared: <suitkaise-api>Share</suitkaise-api>, work_count: int = 5):
        self.shared = shared
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = work_count
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # variable hash iterations (deterministic)
        with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>() as run_timer:
            data = b"benchmark_data"
            iterations = 500 + (self._current_run * 97 % 1500)
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
        
        # add <suitkaise-api>timing</suitkaise-api> to shared timer
        self.shared.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(run_timer.<suitkaise-api>most_recent</suitkaise-api>)
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return "done"


# <suitkaise-api>run</suitkaise-api> multiple workers
workers = 4
with <suitkaise-api>Pool</suitkaise-api>(workers=workers) as pool:
    pool.<suitkaise-api>map</suitkaise-api>(TimedWorker, [share] * workers)

stats = share.<suitkaise-api>timer</suitkaise-api>.get_stats()

# will be 20 (4 workers × 5 <suitkaise-api>runs</suitkaise-api> each)
num_times = stats.<suitkaise-api>num_times</suitkaise-api>

mean = stats.<suitkaise-api>mean</suitkaise-api>
min = stats.min
max = stats.max
stdev = stats.<suitkaise-api>stdev</suitkaise-api>
variance = stats.<suitkaise-api>variance</suitkaise-api>

share.<suitkaise-api>stop</suitkaise-api>()
```

### `<suitkaise-api>Share</suitkaise-api>` as Context Manager

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

class Counter:
    """A simple counter class (will be auto-wrapped by <suitkaise-api>Share</suitkaise-api>)."""
    def __init__(self):
        self.value = 0
    
    def increment(self, amount=1):
        self.value += amount


class WorkerProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, shared: <suitkaise-api>Share</suitkaise-api>):
        self.shared = shared
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 10
    
    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        self.shared.counter.increment(1)
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return "done"


# use <suitkaise-api>Share</suitkaise-api> as context manager for automatic cleanup
with <suitkaise-api>Share</suitkaise-api>() as share:

    # assign custom object - auto-wrapped with Skclass
    share.counter = Counter()
    
    with <suitkaise-api>Pool</suitkaise-api>(workers=2) as pool:
        pool.<suitkaise-api>map</suitkaise-api>(WorkerProcess, [share] * 3)
    
    print(f"Final value: {share.counter.value}") # 30

# <suitkaise-api>Share</suitkaise-api> automatically stopped after 'with' block
```

### Multiple Shared Objects

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib

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


class DataProcessor(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    Process that uses multiple shared objects.
    """
    
    def __init__(self, shared: <suitkaise-api>Share</suitkaise-api>, item: dict):
        self.shared = shared
        self.item = item
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # time the <suitkaise-api>processing</suitkaise-api>
        with <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>TimeThis</suitkaise-api>() as run_timer:
            try:
                # process the data - hash computation
                data = self.item['data'].encode()
                
                # deterministically fail based on content hash
                checksum = hashlib.sha256(data).digest()
                if checksum[0] % 5 == 0:
                    raise RuntimeError(f"Failed <suitkaise-api>processing</suitkaise-api> {self.item['id']}")
                
                # compute hash chain
                for _ in range(1000):
                    data = hashlib.sha256(data).digest()
                
                self.shared.stats.record_success()
                
            except Exception:
                self.shared.stats.record_error()
        
        self.shared.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(run_timer.<suitkaise-api>most_recent</suitkaise-api>)
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.item['id']


with <suitkaise-api>Share</suitkaise-api>() as share:
    # multiple shared objects
    share.stats = Stats()
    share.<suitkaise-api>timer</suitkaise-api> = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>Sktimer</suitkaise-api>()
    
    # create work items
    items = [{'id': i, 'data': f'item_{i}'} for i in range(20)]
    
    with <suitkaise-api>Pool</suitkaise-api>(workers=4) as pool:
        # use <suitkaise-api>star</suitkaise-api>() to pass both share and item
        args = [(share, item) for item in items]
        pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(DataProcessor, args)
    
    # access aggregated results
    print(f"Processed: {share.stats.processed}")
    print(f"Successes: {share.stats.successes}")
    print(f"Errors: {share.stats.errors}")
    print(f"Avg time: {share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.4f}s")
```

### Sharing with single `<suitkaise-api>Skprocess</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>, <suitkaise-api>TimeThis</suitkaise-api>
import hashlib

class IterativeWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A long-running process that updates shared state.
    """
    
    def __init__(self, shared: <suitkaise-api>Share</suitkaise-api>):
        self.shared = shared
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 100
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # variable work - hash computation with deterministic iterations
        with <suitkaise-api>TimeThis</suitkaise-api>() as run_timer:
            data = f"iteration_{self._current_run}".encode()
            iterations = 200 + (hashlib.sha256(data).digest()[0] % 600)
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
        
        # update shared state
        self.shared.progress += 1
        self.shared.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(run_timer.<suitkaise-api>most_recent</suitkaise-api>)
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return "complete"


with <suitkaise-api>Share</suitkaise-api>() as share:
    share.progress = 0
    share.<suitkaise-api>timer</suitkaise-api> = <suitkaise-api>Sktimer</suitkaise-api>()
    
    # <suitkaise-api>run</suitkaise-api> single process
    process = IterativeWorker(share)
    process.<suitkaise-api>start</suitkaise-api>()
    
    # monitor progress from parent
    while process.is_alive:
        print(f"Progress: {share.progress}/100")
        # do real work while waiting
        payload = b"progress"
        for _ in range(500):
            payload = hashlib.sha256(payload).digest()
    
    process.<suitkaise-api>wait</suitkaise-api>()
    
    print(f"\nFinal progress: {share.progress}")
    print(f"Total time: {share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>:.2f}s")
    print(f"Avg iteration: {share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.4f}s")
```

### `<suitkaise-api>Share</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()` and `<suitkaise-api>Share</suitkaise-api>.<suitkaise-api>stop</suitkaise-api>()` control

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>

# create <suitkaise-api>Share</suitkaise-api> without auto-start
share = <suitkaise-api>Share</suitkaise-api>(auto_start=False)

# <suitkaise-api>Share</suitkaise-api> is not running - operations will warn
share.counter = 0  # warning: <suitkaise-api>Share</suitkaise-api> is stopped

# explicitly start
share.<suitkaise-api>start</suitkaise-api>()
print(f"Running: {share.is_running}")  # Running: True

# normal operations
share.counter = 100

# stop to free resources
share.<suitkaise-api>stop</suitkaise-api>()
print(f"Running: {share.is_running}")  # Running: False

# can restart
share.<suitkaise-api>start</suitkaise-api>()
print(f"Counter: {share.counter}")  # Counter: 100
share.<suitkaise-api>stop</suitkaise-api>()
```

### Clearing `<suitkaise-api>Share</suitkaise-api>` State

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

class Incrementer(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, shared: <suitkaise-api>Share</suitkaise-api>):
        self.shared = shared
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 10
    
    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        self.shared.count += 1
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return "done"


with <suitkaise-api>Share</suitkaise-api>() as share:
    share.count = 0
    
    # first batch
    with <suitkaise-api>Pool</suitkaise-api>(workers=2) as pool:
        pool.<suitkaise-api>map</suitkaise-api>(Incrementer, [share] * 2)
    
    print(f"After batch 1: {share.count}")  # 20
    
    # clear all shared state
    share.clear()
    
    # re-initialize
    share.count = 0
    
    # second batch
    with <suitkaise-api>Pool</suitkaise-api>(workers=2) as pool:
        pool.<suitkaise-api>map</suitkaise-api>(Incrementer, [share] * 3)
    
    print(f"After batch 2: {share.count}")  # 30
```

---

## `<suitkaise-api>Pipe</suitkaise-api>`

### Basic `<suitkaise-api>Pipe</suitkaise-api>` Communication

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pipe</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

class PipeWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that communicates via <suitkaise-api>Pipe</suitkaise-api>.
    
    - Receiving the point end of a pipe
    - Bidirectional communication with parent
    """
    
    def __init__(self, pipe_point: <suitkaise-api>Pipe</suitkaise-api>.Point):
        self.pipe = pipe_point
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # receive command from parent
        command = self.pipe.recv()
        print(f"[Child] Received: {command}")
        
        # process the command
        <suitkaise-api>result</suitkaise-api> = command['value'] * 2
        
        # send <suitkaise-api>result</suitkaise-api> back
        self.pipe.send({'<suitkaise-api>result</suitkaise-api>': <suitkaise-api>result</suitkaise-api>, 'status': 'ok'})
        print(f"[Child] Sent <suitkaise-api>result</suitkaise-api>: {<suitkaise-api>result</suitkaise-api>}")
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return "pipe_complete"


# create a pipe pair
# anchor stays in parent, point goes to child
anchor, point = <suitkaise-api>Pipe</suitkaise-api>.pair()

# start process with pipe point
process = PipeWorker(point)
process.<suitkaise-api>start</suitkaise-api>()
point.close()

# send command through anchor
print("[Parent] Sending command...")
anchor.send({'action': 'compute', 'value': 21})

# receive response
response = anchor.recv()
print(f"[Parent] Received response: {response}")

# wait for process to finish
process.<suitkaise-api>wait</suitkaise-api>()

# close the pipe
anchor.close()
```

### One-Way `<suitkaise-api>Pipe</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pipe</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

class DataReceiver(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that only receives data (one-way pipe).
    """
    
    def __init__(self, pipe_point: <suitkaise-api>Pipe</suitkaise-api>.Point):
        self.pipe = pipe_point
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1
        self.received_data = []
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # receive all data until None sentinel
        while True:
            data = self.pipe.recv()
            if data is None:
                break
            self.received_data.append(data)
            print(f"[Child] Received: {data}")
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.received_data


# create one-way pipe (parent sends, child receives)
anchor, point = <suitkaise-api>Pipe</suitkaise-api>.pair(one_way=True)

process = DataReceiver(point)
process.<suitkaise-api>start</suitkaise-api>()
point.close()

# send multiple items
for i in range(5):
    anchor.send({'id': i, 'value': i * 10})

# send sentinel to signal end
anchor.send(None)

# get results
process.<suitkaise-api>wait</suitkaise-api>()
<suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>result</suitkaise-api>()
print(f"Received {len(<suitkaise-api>result</suitkaise-api>)} items")

anchor.close()
```

### Multiple `<suitkaise-api>Pipe</suitkaise-api>`s

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pipe</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

class DualPipeWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process with separate command and data pipes.
    """
    
    def __init__(self, cmd_pipe: <suitkaise-api>Pipe</suitkaise-api>.Point, data_pipe: <suitkaise-api>Pipe</suitkaise-api>.Point):
        self.cmd_pipe = cmd_pipe
        self.data_pipe = data_pipe
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = None  # <suitkaise-api>run</suitkaise-api> until stop
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # check for commands (non-<suitkaise-api>blocking</suitkaise-api> would need timeout)
        try:
            cmd = self.cmd_pipe.recv()
            
            if cmd['action'] == 'process':
                # get data from data pipe
                data = self.data_pipe.recv()
                <suitkaise-api>result</suitkaise-api> = sum(data)
                self.cmd_pipe.send({'status': 'done', '<suitkaise-api>result</suitkaise-api>': <suitkaise-api>result</suitkaise-api>})
            
            elif cmd['action'] == 'stop':
                self.<suitkaise-api>stop</suitkaise-api>()
                
        except Exception as e:
            self.cmd_pipe.send({'status': '<suitkaise-api>error</suitkaise-api>', '<suitkaise-api>error</suitkaise-api>': str(e)})
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return "worker_stopped"


# create two pipe pairs
cmd_anchor, cmd_point = <suitkaise-api>Pipe</suitkaise-api>.pair()
data_anchor, data_point = <suitkaise-api>Pipe</suitkaise-api>.pair()

process = DualPipeWorker(cmd_point, data_point)
process.<suitkaise-api>start</suitkaise-api>()
cmd_point.close()
data_point.close()

# send process command
cmd_anchor.send({'action': 'process'})

# send data on data pipe
data_anchor.send([1, 2, 3, 4, 5])

# get <suitkaise-api>result</suitkaise-api> on command pipe
<suitkaise-api>result</suitkaise-api> = cmd_anchor.recv()
print(f"Result: {<suitkaise-api>result</suitkaise-api>}")  # Result: {'status': 'done', '<suitkaise-api>result</suitkaise-api>': 15}

# stop the worker
cmd_anchor.send({'action': 'stop'})
process.<suitkaise-api>wait</suitkaise-api>()

cmd_anchor.close()
data_anchor.close()
```

---

## `<suitkaise-api>Skprocess</suitkaise-api>.<suitkaise-api>tell</suitkaise-api>()` and `<suitkaise-api>Skprocess</suitkaise-api>.<suitkaise-api>listen</suitkaise-api>()`

### Basic usage

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib

class CommandableProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that receives commands via <suitkaise-api>listen</suitkaise-api>().
    
    - <suitkaise-api>listen</suitkaise-api>() from subprocess
    - <suitkaise-api>tell</suitkaise-api>() from parent
    - Bidirectional communication without <suitkaise-api>Pipe</suitkaise-api>
    """
    
    def __init__(self):
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = None  # <suitkaise-api>run</suitkaise-api> indefinitely
        self.multiplier = 1
        self.results = []
    
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        # check for commands (non-<suitkaise-api>blocking</suitkaise-api> with timeout)
        command = self.<suitkaise-api>listen</suitkaise-api>(timeout=0.1)
        
        if command is not None:
            if command.get('action') == 'set_multiplier':
                self.multiplier = command['value']
                print(f"[Child] Multiplier set to {self.multiplier}")
            
            elif command.get('action') == 'stop':
                self.<suitkaise-api>stop</suitkaise-api>()
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # do some real work - compute hash
        data = f"run_{self._current_run}_mult_{self.multiplier}".encode()
        for _ in range(100 * self.multiplier):
            data = hashlib.sha256(data).digest()
        
        value = int.from_bytes(data[:4], 'big') % 1000
        self.results.append({'<suitkaise-api>run</suitkaise-api>': self._current_run, 'value': value})
        
        # notify parent of progress
        if self._current_run % 5 == 0:
            self.<suitkaise-api>tell</suitkaise-api>({'progress': self._current_run, 'latest': value})
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.results


process = CommandableProcess()
process.<suitkaise-api>start</suitkaise-api>()

# let it <suitkaise-api>run</suitkaise-api> while doing work in parent
import hashlib
data = b"parent_work"
for _ in range(1500):
    data = hashlib.sha256(data).digest()

# send command to change multiplier
process.<suitkaise-api>tell</suitkaise-api>({'action': 'set_multiplier', 'value': 10})

# listen for progress updates for a short window
data = b"parent_work_2"
for _ in range(1500):
    data = hashlib.sha256(data).digest()
for _ in range(20):
    msg = process.<suitkaise-api>listen</suitkaise-api>(timeout=0.1)
    if msg is not None:
        print(f"[Parent] Progress: {msg}")

# stop the process, then drain any remaining messages
process.<suitkaise-api>tell</suitkaise-api>({'action': 'stop'})
process.<suitkaise-api>wait</suitkaise-api>()
while True:
    msg = process.<suitkaise-api>listen</suitkaise-api>(timeout=0.1)
    if msg is None:
        break
    print(f"[Parent] Progress (late): {msg}")

results = process.<suitkaise-api>result</suitkaise-api>()
print(f"Got {len(results)} results")
```

### Async usage

```python
import asyncio
import hashlib
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class AsyncWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A worker that uses tell/listen in async code.
    """
    
    def __init__(self, data_items: list):
        self.data_items = data_items
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = len(data_items)
        self.results = []
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # process data item - compute hash
        item = self.data_items[self._current_run]
        hash_result = hashlib.sha256(item.encode()).hexdigest()
        self.results.append(hash_result[:16])
        
        # send status every 5 <suitkaise-api>runs</suitkaise-api>
        if self._current_run % 5 == 0:
            self.<suitkaise-api>tell</suitkaise-api>({
                '<suitkaise-api>run</suitkaise-api>': self._current_run,
                'status': 'working',
                'last_hash': hash_result[:8]
            })
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.results


async def monitor_process():
    """Monitor a process using async <suitkaise-api>listen</suitkaise-api>."""
    
    data = [f"async_data_item_{i}" for i in range(20)]
    process = AsyncWorker(data)
    process.<suitkaise-api>start</suitkaise-api>()
    
    # monitor with async listen
    while process.is_alive:
        # use <suitkaise-api>asynced</suitkaise-api>() for non-<suitkaise-api>blocking</suitkaise-api> listen in async code
        msg = await process.<suitkaise-api>listen</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()(timeout=0.2)
        if msg:
            print(f"Status: {msg}")
    
    await process.<suitkaise-api>wait</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
    <suitkaise-api>result</suitkaise-api> = process.<suitkaise-api>result</suitkaise-api>()
    print(f"Final: {len(<suitkaise-api>result</suitkaise-api>)} hashes computed")


asyncio.<suitkaise-api>run</suitkaise-api>(monitor_process())
```

---

## `<suitkaise-api>autoreconnect</suitkaise-api>`

### Basic `<suitkaise-api>autoreconnect</suitkaise-api>`

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>autoreconnect</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>

# NOTE: This example shows the pattern - actual database would need real connection

@<suitkaise-api>autoreconnect</suitkaise-api>(
    start_threads=False,
    **{
        "psycopg2.Connection": {"*": "secret"},  # auth value is the password string
    }
)
class DatabaseWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A process that uses a database connection.
    
    @<suitkaise-api>autoreconnect</suitkaise-api> ensures the connection is re-established
    in the subprocess after serialization.
    """
    
    def __init__(self, db_connection, query: str):
        self.db = db_connection
        self.query = query
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1
        self.results = None
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # db connection was auto-reconnected in subprocess
        # self.db is now a live connection, not a Reconnector
        cursor = self.db.cursor()
        cursor.execute(self.query)
        self.results = cursor.fetchall()
        cursor.close()
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.results


# Usage (conceptual):
# db = psycopg2.connect(host="localhost", database="mydb", password="secret")
# 
# with <suitkaise-api>Pool</suitkaise-api>(workers=2) as pool:
#     queries = [
#         (db, "SELECT * FROM users LIMIT 10"),
#         (db, "SELECT * FROM orders LIMIT 10"),
#     ]
#     results = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(DatabaseWorker, queries)
```

### `<suitkaise-api>autoreconnect</suitkaise-api>` with Multiple Connection Types

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>autoreconnect</suitkaise-api>

@<suitkaise-api>autoreconnect</suitkaise-api>(
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
class MultiDbWorker(<suitkaise-api>Skprocess</suitkaise-api>):
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
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # all connections are auto-reconnected in subprocess
        # ... use connections ...
        pass
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
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
4. Some tasks fail deterministically based on content
5. Failed tasks are automatically retried up to 3 times
6. All timing and success/failure stats are aggregated across workers
7. Prints a summary report with task statistics and performance metrics

```python
"""
A complete example of a distributed task queue using <suitkaise-api>processing</suitkaise-api>.

Features used:
- <suitkaise-api>Pool</suitkaise-api> for parallel worker management
- <suitkaise-api>Share</suitkaise-api> for tracking global state across processes
- <suitkaise-api>Skprocess</suitkaise-api> for structured task execution with lifecycle hooks
- Timing for performance metrics collection
- <suitkaise-api>lives</suitkaise-api> for automatic retry on failure
"""

from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib


class TaskStats:
    """
    Tracks statistics across all workers.
    
    This class will be auto-wrapped by <suitkaise-api>Share</suitkaise-api> with Skclass.
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


class TaskWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A worker that processes a single task.
    
    Features:
    - Deterministic failure based on task content
    - Retry support via <suitkaise-api>lives</suitkaise-api>
    - Timing recorded to shared timer
    - Stats recorded to shared stats object
    """
    
    def __init__(self, shared: <suitkaise-api>Share</suitkaise-api>, task: dict):
        # store references
        self.shared = shared
        self.task = task
        
        # configure process
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1      # one <suitkaise-api>run</suitkaise-api> per task
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>lives</suitkaise-api> = 3     # retry up to 2 times
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>run</suitkaise-api> = 5.0  # 5 second timeout
        
        # <suitkaise-api>result</suitkaise-api> storage
        self.result_data = None
        self.attempts = 0
    
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        # track retry attempts
        self.attempts += 1
        if self.attempts > 1:
            # this is a retry
            self.shared.stats.record_retry()
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        # record <suitkaise-api>timing</suitkaise-api>
        start = <suitkaise-api>timing</suitkaise-api>.time()
        
        try:
            # real work - compute hash chain with deterministic iterations
            iterations = 500 + (self.task['id'] * 37 % 1500)
            data = self.task['data'].encode()
            for _ in range(iterations):
                data = hashlib.sha256(data).digest()
            
            # deterministic failure based on task content
            checksum = hashlib.sha256(self.task['data'].encode()).digest()
            if checksum[0] % 10 == 0:
                raise RuntimeError(f"Task {self.task['id']} failed (content check)")
            
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
            # always record <suitkaise-api>timing</suitkaise-api>
            <suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start)
            self.shared.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(<suitkaise-api>elapsed</suitkaise-api>)
    
    def <suitkaise-api>__error__</suitkaise-api>(self):
        # all retries exhausted
        self.shared.stats.record_fail()
        
        return {
            'task_id': self.task['id'],
            'input': self.task['data'],
            'output': None,
            'attempts': self.attempts,
            'status': 'failed',
            '<suitkaise-api>error</suitkaise-api>': str(self.<suitkaise-api>error</suitkaise-api>)
        }
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
        return self.result_data


def run_task_queue(tasks: list[dict], workers: int = 4):
    """
    Process a list of tasks using a distributed worker pool.
    
    Args:
        tasks: List of task dicts with 'id' and 'data' keys
        workers: Number of parallel workers
    Returns:
        Dict with results and statistics
    """
    
    # set up shared state
    with <suitkaise-api>Share</suitkaise-api>() as share:
        share.stats = TaskStats()
        share.<suitkaise-api>timer</suitkaise-api> = <suitkaise-api>Sktimer</suitkaise-api>()
        
        # create argument tuples for <suitkaise-api>star</suitkaise-api>()
        args = [(share, task) for task in tasks]
        
        # process all tasks in parallel
        with <suitkaise-api>Pool</suitkaise-api>(workers=workers) as pool:
            results = pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(TaskWorker, args)
        
        # collect statistics
        stats = {
            'total_tasks': share.stats.total_tasks,
            'completed': share.stats.completed,
            'failed': share.stats.failed,
            'retried': share.stats.retried,
            '<suitkaise-api>timing</suitkaise-api>': {
                'total': share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>,
                'mean': share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>,
                'min': share.<suitkaise-api>timer</suitkaise-api>.min,
                'max': share.<suitkaise-api>timer</suitkaise-api>.max,
                'p95': share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>(95),
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

    start = <suitkaise-api>timing</suitkaise-api>.time()
    
    # <suitkaise-api>run</suitkaise-api> the queue
    output = run_task_queue(tasks, workers=4)
    
    <suitkaise-api>elapsed</suitkaise-api> = <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start)
    
    # print results
    print(f"\n{'='*50}")
    print(f"TASK QUEUE RESULTS")
    print(f"{'='*50}")
    print(f"Total time: {<suitkaise-api>elapsed</suitkaise-api>:.2f}s")
    print(f"\nTask Statistics:")
    print(f"  Total processed: {output['stats']['total_tasks']}")
    print(f"  Completed:       {output['stats']['completed']}")
    print(f"  Failed:          {output['stats']['failed']}")
    print(f"  Retried:         {output['stats']['retried']}")
    print(f"\nTiming Statistics:")
    print(f"  Total work time: {output['stats']['<suitkaise-api>timing</suitkaise-api>']['total']:.2f}s")
    print(f"  Mean per task:   {output['stats']['<suitkaise-api>timing</suitkaise-api>']['mean']:.4f}s")
    print(f"  Min:             {output['stats']['<suitkaise-api>timing</suitkaise-api>']['min']:.4f}s")
    print(f"  Max:             {output['stats']['<suitkaise-api>timing</suitkaise-api>']['max']:.4f}s")
    print(f"  P95:             {output['stats']['<suitkaise-api>timing</suitkaise-api>']['p95']:.4f}s")
    
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
3. Distributes items to workers in round-robin fashion via `<suitkaise-api>tell</suitkaise-api>()`
4. Each worker computes a hash transformation on received items
5. Workers report their status periodically via `<suitkaise-api>tell</suitkaise-api>()` back to parent
6. Results accumulate in shared state accessible from all processes
7. After stream ends, sends stop signal to all workers
8. Collects final statistics and prints summary

```python
"""
A real-time data pipeline using <suitkaise-api>processing</suitkaise-api>.

Features used:
- Indefinite process with stop signal (<suitkaise-api>runs</suitkaise-api>=None)
- tell/listen for real-time bidirectional communication
- <suitkaise-api>Share</suitkaise-api> for accumulating results across processes
- Graceful shutdown with <suitkaise-api>__onfinish__</suitkaise-api>
"""

from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>Share</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import <suitkaise-api>Sktimer</suitkaise-api>, <suitkaise-api>TimeThis</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>timing</suitkaise-api>
import hashlib


class Results:
    """Accumulates processed data."""
    def __init__(self):
        self.items = []
        self.count = 0
    
    def add(self, item):
        self.items.append(item)
        self.count += 1


class DataPipelineWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    """
    A worker that processes streaming data.
    
    - Runs indefinitely until parent sends stop
    - Receives data items via <suitkaise-api>listen</suitkaise-api>()
    - Processes and stores results in <suitkaise-api>Share</suitkaise-api>
    - Sends status updates via <suitkaise-api>tell</suitkaise-api>()
    """
    
    def __init__(self, shared: <suitkaise-api>Share</suitkaise-api>, worker_id: int):
        self.shared = shared
        self.worker_id = worker_id
        
        # <suitkaise-api>run</suitkaise-api> indefinitely
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = None
        
        self.processed = 0
    
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        # check for stop signal or data
        msg = self.<suitkaise-api>listen</suitkaise-api>(timeout=0.1)
        
        if msg is not None:
            if msg.get('action') == 'stop':
                # graceful shutdown
                self.<suitkaise-api>stop</suitkaise-api>()
            elif msg.get('action') == 'data':
                # store data for <suitkaise-api>processing</suitkaise-api>
                self._pending_data = msg['payload']
            else:
                self._pending_data = None
        else:
            self._pending_data = None
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        if self._pending_data is None:
            # no data to process
            return
        
        # process the data - real work
        with <suitkaise-api>TimeThis</suitkaise-api>() as run_timer:
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
            
            <suitkaise-api>result</suitkaise-api> = {
                'worker': self.worker_id,
                'input': data,
                'output': output,
                'timestamp': <suitkaise-api>timing</suitkaise-api>.time()
            }
        
        
        # store <suitkaise-api>result</suitkaise-api> in shared state
        self.shared.results.add(<suitkaise-api>result</suitkaise-api>)
        self.shared.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(run_timer.<suitkaise-api>most_recent</suitkaise-api>)
        
        self.processed += 1
        self._pending_data = None
    
    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        # send periodic status updates
        if self.processed > 0 and self.processed % 10 == 0:
            self.<suitkaise-api>tell</suitkaise-api>({
                'worker': self.worker_id,
                'processed': self.processed,
                'status': 'running'
            })
    
    def <suitkaise-api>__onfinish__</suitkaise-api>(self):
        # send final status
        self.<suitkaise-api>tell</suitkaise-api>({
            'worker': self.worker_id,
            'processed': self.processed,
            'status': 'finished'
        })
    
    def <suitkaise-api>__result__</suitkaise-api>(self):
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
        timeout: Maximum time to <suitkaise-api>run</suitkaise-api>
    
    Returns:
        Dict with results and worker stats
    """
    
    with <suitkaise-api>Share</suitkaise-api>() as share:
        share.results = Results()
        share.<suitkaise-api>timer</suitkaise-api> = <suitkaise-api>Sktimer</suitkaise-api>()
        
        # start workers
        workers = []
        for i in range(num_workers):
            worker = DataPipelineWorker(share, worker_id=i)
            worker.<suitkaise-api>start</suitkaise-api>()
            workers.append(worker)
        
        # distribute data to workers
        start_time = <suitkaise-api>timing</suitkaise-api>.time()
        worker_idx = 0
        
        for item in data_stream:
            # check timeout
            if <suitkaise-api>timing</suitkaise-api>.<suitkaise-api>elapsed</suitkaise-api>(start_time) > timeout:
                break
            
            # round-robin to workers (compute checksum in parent)
            import hashlib
            checksum = hashlib.sha256(str(item).encode()).hexdigest()[:8]
            workers[worker_idx].<suitkaise-api>tell</suitkaise-api>({
                'action': 'data',
                'payload': item,
                'checksum': checksum,
            })
            worker_idx = (worker_idx + 1) % num_workers
        
        # signal workers to stop
        for worker in workers:
            worker.<suitkaise-api>tell</suitkaise-api>({'action': 'stop'})
        
        # collect status messages
        statuses = []
        for worker in workers:
            while True:
                msg = worker.<suitkaise-api>listen</suitkaise-api>(timeout=0.5)
                if msg is None:
                    break
                statuses.append(msg)
        
        # wait for all workers
        for worker in workers:
            worker.<suitkaise-api>wait</suitkaise-api>()
        
        # collect results
        worker_results = [worker.<suitkaise-api>result</suitkaise-api>() for worker in workers]
        
        return {
            'results': share.results.items,
            'count': share.results.count,
            'worker_stats': worker_results,
            '<suitkaise-api>timing</suitkaise-api>': {
                'total': share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>total_time</suitkaise-api>,
                'mean': share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api> if share.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>num_times</suitkaise-api> > 0 else 0,
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
    print(f"  Total time: {output['<suitkaise-api>timing</suitkaise-api>']['total']:.2f}s")
    print(f"  Mean per item: {output['<suitkaise-api>timing</suitkaise-api>']['mean']:.4f}s")
    
    print(f"\nWorker Stats:")
    for ws in output['worker_stats']:
        print(f"  Worker {ws['worker_id']}: {ws['total_processed']} items")
    
    print(f"\nSample Results:")
    for r in output['results'][:5]:
        print(f"  {r['input']} -> {r['output']} (worker {r['worker']})")
```
