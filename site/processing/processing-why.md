/*

synced from suitkaise-docs/processing/why.md

*/

rows = 2
columns = 1

# 1.1

title = "Why you should use `<suitkaise-api>processing</suitkaise-api>`"

# 1.2

text = "
## TLDR

- **Anything works in parallel** - Locally-defined functions, lambdas, closures, live connections all work
- **Easiest shared state possible** - `share.counter = 0` just works across processes
- **Class-based processes** - No more giant, messy functions. Lifecycle hooks organize your code naturally.
- **Crash and restart** - `<suitkaise-api>lives</suitkaise-api>=3` and your process auto-retries. No try/except loops.
- **Timeouts** - Advanced timeout system that works on all platforms.
- **Database connections just work** - `@<suitkaise-api>autoreconnect</suitkaise-api>` brings live connections into subprocesses. Normally impossible.
- **Sync and async in one API** - Same code, add `.<suitkaise-api>asynced</suitkaise-api>()` when you need it.

---

## See it in action

Try sharing a logger, a list, and a counter across 4 parallel processes using standard `multiprocessing`:

```python
share.counter = 0
share.results = []
share.log = logging.getLogger("worker")
```

Just kidding, you can't. `multiprocessing.Manager` doesn't support loggers. `pickle` will choke. You'd need to redesign everything.

Not with `<suitkaise-api>processing</suitkaise-api>`.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
import logging

# put anything on <suitkaise-api>Share</suitkaise-api> — literally anything
share = <suitkaise-api>Share</suitkaise-api>()
share.counter = 0
share.results = []
share.log = logging.getLogger("worker")

class Worker(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, share, item):
        self.share = share
        self.item = item

    def <suitkaise-api>__run__</suitkaise-api>(self):
        <suitkaise-api>result</suitkaise-api> = self.item * 2
        self.share.results.append(<suitkaise-api>result</suitkaise-api>)       # shared list
        self.share.counter += 1                 # shared counter
        self.share.log.info(f"done: {<suitkaise-api>result</suitkaise-api>}")  # shared logger

pool = <suitkaise-api>Pool</suitkaise-api>(workers=4)
pool.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>(Worker, [(share, x) for x in range(20)])

print(share.counter)         # 20
print(len(share.results))    # 20
print(share.log.handlers)    # still works
```

A list, a counter, and a logger — shared across 4 processes, all in sync, all updated like normal Python. No queues, no locks, no Manager, no pickle errors. No redesigning your code around what the serializer can handle.

`<suitkaise-api>processing</suitkaise-api>` makes parallel code regular code.

---

## Python has a parallel processing problem.

Python uses a Global Interpreter Lock (GIL).

What this means
- no memory leaks or corruption
- no garbage collection issues
- thread safe built-in types
- can work with C extensions

Hey, that sounds pretty good! 

### Maybe it doesn't sound that good

Python also has one major issue: no simultaneous bytecode execution.

This means that threads don't speed up CPU-bound work, and makes Python essentially single-threaded.

16 cores running 16 threads will not speed up work.

In a time where almost all major programs parallelize their code, Python is stuck in the past.

### Or is it?

We can spawn multiple processes using Python's `multiprocessing` module.
- each with their own GIL
- each with their own interpreter
- each with their own memory space

True parallelism. Problem solved!

Wrong. The problem is not solved yet.

### 1. `pickle` can't serialize your code

You are trying to run something in parallel.

```python
def process_data(items):
    def transform(x):
        return x * 2

    for item in items:
        <suitkaise-api>result</suitkaise-api> = transform(item)
        results.append(<suitkaise-api>result</suitkaise-api>)
    return results

    
with <suitkaise-api>Pool</suitkaise-api>(4) as pool:
    return pool.<suitkaise-api>map</suitkaise-api>(transform, lists_of_items)
```

This looks like it should work. But it doesn't, because you put a locally-defined function in the pool.

There are a bunch of random things that `pickle` can't handle, many of which are pretty common things you use when writing code.

- locally-defined functions
- lambdas
- closures
- dynamically created classes
- and most other complex code patterns that you would actually use when multiprocessing

Figuring out what works and what doesn't is a nightmare.

#### Just use `cloudpickle` or `dill`. They're better than `pickle`.

`cloudpickle` and `dill` are cool but they just lessen this problem, not solve it.

- `cloudpickle` is fast, and has a little more coverage than `pickle`, but not enough
- `dill` has a lot more coverage than `pickle`, but is very slow in exchange

However: Python's `multiprocessing` doesn't use them by default.

The standard library's `multiprocessing.<suitkaise-api>Pool</suitkaise-api>` is hardcoded to use `pickle`. To use `cloudpickle` or `dill`, you have to:

```python
# option 1: monkey-patch the serializer (risky, affects entire process)
import multiprocessing
import cloudpickle

multiprocessing.reduction.ForkingPickler.dumps = cloudpickle.dumps
multiprocessing.reduction.ForkingPickler.loads = cloudpickle.loads

# let's hope nothing else in your codebase depends on regular pickle
```

```python
# option 2: use multiprocess (a fork of multiprocessing that uses dill)
# pip install multiprocess
import multiprocess as mp 

with mp.<suitkaise-api>Pool</suitkaise-api>(4) as pool:
    results = pool.<suitkaise-api>map</suitkaise-api>(my_function, items)

# dill is slow
# 2 libraries to keep track of
```

```python
# option 3: use concurrent.futures with a custom executor
from concurrent.futures import ProcessPoolExecutor
import cloudpickle

# you need to write a custom executor class that overrides the serializer
```

None of these just work, but they all do waste your time.

And even after all that, you still have limitations. Your code is now more complex, in exchange for... not as many serialization errors?

#### So what CAN you do?

You could learn every limitation of whatever you use, and tiptoe around objects or patterns that will fail.

You could learn every limitation of whatever you use, and write custom code to handle unsupported objects haphazardly.

Or, you could just use `<suitkaise-api>processing</suitkaise-api>`.

## `<suitkaise-api>processing</suitkaise-api>` uses `<suitkaise-api>cucumber</suitkaise-api>` instead of `pickle`

By default, `<suitkaise-api>processing</suitkaise-api>` uses `<suitkaise-api>cucumber</suitkaise-api>`, `<suitkaise-api>suitkaise</suitkaise-api>`'s serialization engine, instead of `pickle`.

### Problem actually solved

`<suitkaise-api>cucumber</suitkaise-api>` handles everything.

- handles everything from ints to complex user created classes with live connections
- better than `pickle`
- better than `cloudpickle`
- better than `dill`
- automatically used by `<suitkaise-api>processing</suitkaise-api>`

`<suitkaise-api>cucumber</suitkaise-api>` actually solves the problem of things not being serializable. And the problem of actually being compatible with multiprocessing.

(For more info, see the `<suitkaise-api>cucumber</suitkaise-api>` pages)

## Python's `multiprocessing` module also has problems

Python's `multiprocessing` module also has problems.

Outside of the serialization problem, a large problem still exists with `multiprocessing`.

### 2. Using `multiprocessing` is complicated and not intuitive

`multiprocessing` is a powerful tool, but it is also a pain in the ass to actually use, especially for complex tasks. A lot of this is just due to the fact that you sort of have to actually manage everything yourself.

Python gives us the bare minimum to parallelize code, but outside of that, everything is left to you.
- setup
- cleanup
- teardown
- sharing state
- error handling
- performance timing
- crash handling
- looping code
- more
- and your actual task you need to do

This is a long list of things that you need in order to have solid code when parallelizing.

#### Making this situation worse

Notice what is passed into `multiprocessing` to run a single parallel process.

```python
import multiprocessing

def process_data(items):
    
    # process your data
    return data


# <suitkaise-api>run</suitkaise-api> the single process (not even in a <suitkaise-api>Pool</suitkaise-api>)
process = multiprocessing.Process(target=process_data, args=(items,))
process.<suitkaise-api>start</suitkaise-api>()
```

It's a function. 

You have to add all of those things from that list into a single function.

For the case above, passing in a simple function is fine, you just want to get compute and get the data faster in parallel.

But the case above doesn't scratch the surface of what you could do with parallel processing.

Not only does having to pass a function make implementing and debugging very difficult, but it also goes against the entire point of object-oriented programming -- where you encapsulate your code into different class objects -- by forcing you to make one giant god function that does everything.

#### Making the situation better

What is something in programming that we can use to split up a giant god function into a more manageable set of pieces?

Classes. 

Everyone knows how to work with classes. They are the fundamental building block of object-oriented programming.

So why not pass a class into `multiprocessing` instead of a function?

```python
import multiprocessing

class ProcessData(multiprocessing.Process):
    def __init__(self, items, result_queue):
        self.items = items
        self.result_queue = result_queue  # need a Queue to communicate
        super().__init__()
    
    def <suitkaise-api>run</suitkaise-api>(self):
        # do work
        <suitkaise-api>result</suitkaise-api> = process_items(self.items)
        self.result_queue.put(<suitkaise-api>result</suitkaise-api>)  # send back via queue

queue = multiprocessing.Queue()
process = ProcessData(items, queue)
process.<suitkaise-api>start</suitkaise-api>()
process.join()
<suitkaise-api>result</suitkaise-api> = queue.get()  # retrieve from queue, not process.<suitkaise-api>result</suitkaise-api>
```

This is a step in the right direction, but it is by no means perfect.
- still sort of confusing in general
- you have to manually manage the queue
- this will still use base `pickle`
- you have to manually call `super().__init__()` and implement `<suitkaise-api>run</suitkaise-api>()`
- still no automatic retries, timeouts, timing, or error handling

## `<suitkaise-api>Skprocess</suitkaise-api>`

A class is the overall solution that should've been used all along.

But we still have no structure and no lifecycle.
- missing actual methods to split up code into smaller pieces
- missing good error handling
- hard to share state, must bring in a different object just for that
- overall, code is still missing a lot of the structure and automation that is expected

`<suitkaise-api>Skprocess</suitkaise-api>` is a class that goes above and beyond for you.
- automatically uses `<suitkaise-api>cucumber</suitkaise-api>`
- supports `<suitkaise-api>Share</suitkaise-api>` (very important later)
- provides standard lifecycle methods to help you split up code into smaller pieces
- all result gathering is done using attributes and regular return statements
- clear error handling, even telling you what part of the code it failed on
- retries when the process crashes
- live resources can automatically reconnect
- automatic timing of every lifecycle method
- simple shared state, any object can be shared
- code loops for you
- no need to call `super().__init__()` when inheriting
- high level of control using a simple config
- fast and controlled bidirectional communication with `<suitkaise-api>Pipe</suitkaise-api>`

Let's make a process that queries a database for user data based on given input from a parent process.

Requirements:
- Receive query parameters from parent
- Connect to database and execute query
- Handle connection failures with retry
- Timeout if query takes too long
- Track timing statistics
- Return results to parent
- Clean up connection on exit

Without `<suitkaise-api>Skprocess</suitkaise-api>` - *92 lines*

```python
# comments and whitespace excluded from line count
import multiprocessing
import signal
import time
import psycopg2
from multiprocessing import Queue, Event, Value
from ctypes import c_double

class DatabaseWorker(multiprocessing.Process):
    def __init__(self, task_queue, result_queue, stats_lock, 
                 total_time, query_count, stop_event, db_config):
        super().__init__()
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.stats_lock = stats_lock
        self.<suitkaise-api>total_time</suitkaise-api> = total_time
        self.query_count = query_count
        self.stop_event = stop_event
        self.db_config = db_config
        self.<suitkaise-api>timeout</suitkaise-api> = 30
        self.max_retries = 3
        self.conn = None
    
    def _connect(self):
        # manual retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                self.conn = psycopg2.connect(**self.db_config)
                return
            except psycopg2.OperationalError:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
    
    def _timeout_handler(self, signum, frame):
        raise TimeoutError("Query timed out")
    
    def <suitkaise-api>run</suitkaise-api>(self):
        # manual connection setup
        self._connect()
        
        # manual signal handling for <suitkaise-api>timeouts</suitkaise-api>
        signal.signal(signal.SIGALRM, self._timeout_handler)
        
        try:
            while not self.stop_event.is_set():
                # check for incoming query (non-<suitkaise-api>blocking</suitkaise-api>)
                try:
                    query_params = self.task_queue.get(timeout=0.1)
                except:
                    # no query received
                    self.result_queue.put({'status': 'no query', 'data': None})
                    continue
                
                # manual <suitkaise-api>timing</suitkaise-api>
                start = time.time()
                signal.alarm(self.<suitkaise-api>timeout</suitkaise-api>)
                
                try:
                    cursor = self.conn.cursor()
                    cursor.execute(query_params['sql'], query_params.get('params'))
                    results = cursor.fetchall()
                    cursor.close()
                    
                    signal.alarm(0)
                    <suitkaise-api>elapsed</suitkaise-api> = time.time() - start
                    
                    # manual stats tracking with locks
                    with self.stats_lock:
                        self.<suitkaise-api>total_time</suitkaise-api>.value += <suitkaise-api>elapsed</suitkaise-api>
                        self.query_count.value += 1
                    
                    # different status based on results
                    if not results:
                        self.result_queue.put({'status': '<suitkaise-api>error</suitkaise-api>', 'data': None})
                    else:
                        self.result_queue.put({'status': 'ok', 'data': results})
                    
                except TimeoutError:
                    signal.alarm(0)
                    self.result_queue.put({'status': '<suitkaise-api>error</suitkaise-api>', '<suitkaise-api>error</suitkaise-api>': 'timeout'})
                except Exception as e:
                    signal.alarm(0)
                    self.result_queue.put({'status': '<suitkaise-api>error</suitkaise-api>', '<suitkaise-api>error</suitkaise-api>': str(e)})
        finally:
            # manual cleanup
            if self.conn:
                self.conn.close()


# usage

# connect to the database (credentials stored separately)
db_config = {'host': 'localhost', 'database': 'mydb', 'password': 'secret'}

# create all the shared state machinery
manager = multiprocessing.Manager()
task_queue = Queue()
result_queue = Queue()
stats_lock = manager.Lock()
total_time = Value(c_double, 0.0)
query_count = Value('i', 0)
stop_event = Event()

# init and start the worker process
worker = DatabaseWorker(
    task_queue, result_queue, stats_lock, total_time, 
    query_count, stop_event, db_config,
    timeout=30, max_retries=3
)
worker.<suitkaise-api>start</suitkaise-api>()

# list of queries to <suitkaise-api>run</suitkaise-api> (counted as a single line)
queries = [
    {'sql': 'SELECT * FROM users WHERE id = %s', 'params': (123,)},
    {'sql': 'SELECT * FROM users WHERE id = %s', 'params': (456,)},
    {'sql': 'SELECT * FROM users WHERE id = %s', 'params': (789,)},
    # ...
]

# create a list to store the results
results = []

# send each query to the worker
for query in queries:
    task_queue.put(query)
    <suitkaise-api>result</suitkaise-api> = result_queue.get(timeout=30)  # need manual timeout here too
    results.append(<suitkaise-api>result</suitkaise-api>)

# signal stop and wait for cleanup
stop_event.set()
worker.join()

# manual <suitkaise-api>timing</suitkaise-api> calculation
if query_count.value > 0:
    avg_time = <suitkaise-api>total_time</suitkaise-api>.value / query_count.value
    print(f"Avg query time: {avg_time:.3f}s")
```

There are a lot of problems here.

1. 6 import statements
2. 12 parameters in `__init__`, most of which are just trying to setup infrastructure
3. `super().__init__()` has to be called and is easy to forget
4. manual retry logic
5. manual performance timing
6. multiple different timeouts need to be handled manually
7. several queues to manage
8. have to handle signals, which don't even work on Windows
9. awkward `.value` access for shared state
10. have to use a separate event object for stopping
11. `Manager` for locks, something else that needs to be coordinated
12. manual cleanup in `finally`
13. statistics done by hand
14. passing database credentials around as a dict
15. uses `pickle`

This is a simple example: you already have to do this much for this little.

With `<suitkaise-api>Skprocess</suitkaise-api>` - *40 lines*

```python
# comments and whitespace excluded from line count
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>autoreconnect</suitkaise-api>
import psycopg2

@<suitkaise-api>autoreconnect</suitkaise-api>(**{"psycopg2.Connection": {"*": "password"}})
class DatabaseWorker(<suitkaise-api>Skprocess</suitkaise-api>):

    def __init__(self, db_connection):
        # this automatically reconnects
        self.db = db_connection

        # built in configuration
        # <suitkaise-api>run</suitkaise-api> indefinitely until <suitkaise-api>stop</suitkaise-api>() is called
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = None
        # NOTE: this is the default: here for clarity, not counted in line count

        # 3 <suitkaise-api>lives</suitkaise-api> (2 extra attempts after the first failure)
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>lives</suitkaise-api> = 3

        # 30 second timeout per query
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>timeouts</suitkaise-api>.<suitkaise-api>run</suitkaise-api> = 30.0
    
    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        # receive query from <suitkaise-api>parent</suitkaise-api> (non-<suitkaise-api>blocking</suitkaise-api> check)
        msg = self.<suitkaise-api>listen</suitkaise-api>(timeout=0.1)
        self.query = msg if msg else None
    
    def <suitkaise-api>__run__</suitkaise-api>(self):
        if not self.query:
            return
        cursor = self.db.cursor()
        cursor.execute(self.query['sql'], self.query.get('params'))
        self.results = cursor.fetchall()
        cursor.close()
    
    def <suitkaise-api>__postrun__</suitkaise-api>(self):

        if self.query:
            if not self.results:
                self.<suitkaise-api>tell</suitkaise-api>({'status': '<suitkaise-api>error</suitkaise-api>', 'data': None})
            else:
                self.<suitkaise-api>tell</suitkaise-api>({'status': 'ok', 'data': self.results})

        else:
            self.<suitkaise-api>tell</suitkaise-api>({'status': 'no query', 'data': None})
    
    def <suitkaise-api>__onfinish__</suitkaise-api>(self):
        self.db.close()

# usage

# connect to the database
db = psycopg2.connect(host='localhost', database='mydb', password='secret')

# init and start the worker process
worker = DatabaseWorker(db)
worker.<suitkaise-api>start</suitkaise-api>()

# list of queries to <suitkaise-api>run</suitkaise-api> (counted as a single line)
queries = [
    {'sql': 'SELECT * FROM users WHERE id = %s', 'params': (123,)},
    {'sql': 'SELECT * FROM users WHERE id = %s', 'params': (456,)},
    {'sql': 'SELECT * FROM users WHERE id = %s', 'params': (789,)},
    # ...
]

# create a list to store the results
results = []

# send each query to the worker
for query in queries:
    worker.<suitkaise-api>tell</suitkaise-api>(query)
    <suitkaise-api>result</suitkaise-api> = worker.<suitkaise-api>listen</suitkaise-api>(timeout=30)
    results.append(<suitkaise-api>result</suitkaise-api>)

# request <suitkaise-api>stop</suitkaise-api> (join) and wait for it to finish
worker.<suitkaise-api>stop</suitkaise-api>()
worker.<suitkaise-api>wait</suitkaise-api>()

# automatically timed
print(f"Avg query time: {worker.<suitkaise-api>__run__</suitkaise-api>.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>mean</suitkaise-api>:.3f}s")
```

- 2x less code
- 1 import line for all of your multiprocessing
- nothing is manual
- everything is organized
- uses `<suitkaise-api>cucumber</suitkaise-api>` for serialization
- automatically reconnects the db connection
- times, errors, and statistics are handled




## Shared state in Python

Sharing state across process boundaries is one of the most functionally important parts of multiprocessing in Python.

There are generally 6 patterns for doing this:

1. `Value` and `Array`

Shared memory, but just for primitive types.

Pros: Fast, no serialization
Cons: Only primitives, not even dicts or lists

2. `multiprocessing.Manager`

Proxy objects that wrap Python types.

Pros: Supports dict, list, and other Python types (uses `pickle`)
Cons: Slow. Manager is a separate process, so not truly shared memory

3. `multiprocessing.shared_memory`

Raw shared memory blocks. Only available in Python 3.8+.

Pros: True shared memory, fast
Cons: Manual buffer management, no serialization, have to handle syncing yourself

4. Queues (message passing)

Isn't exactly shared state, but functionally similar.

Pros: Safe, decently fasts, works with any serializable object
Cons: Not actually shared - each process has its own copy

5. Files/Databases

Write to disk so that other processes can read.

Pros: simple and persistent
Cons: slow IO, race conditions, not real-time

6. External services

Use an external process to hold state, like Redis or Memcached.

Pros: atomic operations, pub/sub, works across machines
Cons: External depedency, network overhead, more to manage

The problem with all of these:
- none of these are easy or simple in practice
- you have to choose the right mechanism
- handle serialization, or be limited in what you can share
- sync manually
- lots of boilerplate


## `<suitkaise-api>Share</suitkaise-api>`

`<suitkaise-api>Share</suitkaise-api>` is the ultimate solution to shared state in Python.

Pros:
- literally add any object to it and it will work the same exact way in shared memory
- as simple as it gets
- uses `<suitkaise-api>cucumber</suitkaise-api>` for serialization, so all objects work
- ensures that everything stays in sync
- works across any number of processes

Cons:
- slowest overall option
- overhead
- cannot share `multiprocessing.*` objects (Python limitation)

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>, <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>
import logging

share = <suitkaise-api>Share</suitkaise-api>()
share.counter = 0
share.log = logging.getLogger("ShareLog")



class ShareCounter(<suitkaise-api>Skprocess</suitkaise-api>):

    # pass the <suitkaise-api>Share</suitkaise-api> instance to the process
    def __init__(self, share: <suitkaise-api>Share</suitkaise-api>):
        self.share = share
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 10

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.share.counter += 1
        self.share.log.info(f"{self.share.counter}")



# just add share
pool = <suitkaise-api>Pool</suitkaise-api>(workers=4)
pool.<suitkaise-api>map</suitkaise-api>(ShareCounter, [share] * 10)

print(share.counter) # 100 (10 total workers, 10 <suitkaise-api>runs</suitkaise-api> each)
print(share.log.messages) # ['1', '2', '3', '4', '5', ..., '100'] in order
```

In 20 lines, I made a counter that works in a parallel pool, that will loop exactly 10 times, logging its progress. Not a single result is needed, as everything just got added to shared memory, and that shared memory was 100% in sync.

### 100% worth the slow speed

`<suitkaise-api>Share</suitkaise-api>` is about 3x slower than `multiprocessing.Manager`.

But every object works exactly the same.

To add them: assign them to attributes.

To use them: access and update them as normal.

#### Why the 3x doesn't matter in practice

The overhead is on the coordinator IPC layer, the per-operation cost of syncing state. For long-running parallel work (the kind where you actually need multiprocessing), that cost gets diluted as you perform longer running tasks.

If your process runs for 30 seconds and does 1,000 share operations, the overhead is a few extra milliseconds total. Meanwhile, the alternative is hours of your time debugging `Manager` + `pickle` errors + race conditions + manual sync logic.

`<suitkaise-api>Share</suitkaise-api>` trades microseconds of IPC overhead for the ability to turn your brain off and never write shared state boilerplate again. You create it, assign to it, and read from it -- exactly like you learned in your first programming class.

That's a tradeoff worth making.

## `<suitkaise-api>processing</suitkaise-api>` still has 2 more options for sharing state

`<suitkaise-api>processing</suitkaise-api>` has 2 high speed options for sharing state.

### 1. `<suitkaise-api>Skprocess</suitkaise-api>.<suitkaise-api>tell</suitkaise-api>()` and `<suitkaise-api>Skprocess</suitkaise-api>.<suitkaise-api>listen</suitkaise-api>()`

The 2 queue-like methods that are a part of `<suitkaise-api>Skprocess</suitkaise-api>` (and all inheriting classes).

These are automatically 2 way, and use `<suitkaise-api>cucumber</suitkaise-api>`.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Skprocess</suitkaise-api>

class MyProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    def <suitkaise-api>__prerun__</suitkaise-api>(self):

        self.command = self.<suitkaise-api>listen</suitkaise-api>(timeout=1.0)

    def <suitkaise-api>__run__</suitkaise-api>(self):

        if self.command == "stop":
            self.<suitkaise-api>stop</suitkaise-api>()

        elif self.command == "print":
            print("hello")

        else:
            raise ValueError(f"Unknown command: {self.command}")

    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        self.command = None
        self.<suitkaise-api>tell</suitkaise-api>("command received")
        


p = MyProcess()
p.<suitkaise-api>start</suitkaise-api>()
for i in range(10):
    p.<suitkaise-api>tell</suitkaise-api>("print")
    <suitkaise-api>result</suitkaise-api> = p.<suitkaise-api>listen</suitkaise-api>(timeout=1.0)
    if <suitkaise-api>result</suitkaise-api> != "command received":
        break

p.<suitkaise-api>tell</suitkaise-api>("stop")
p.<suitkaise-api>wait</suitkaise-api>()
```

### 2. `<suitkaise-api>Pipe</suitkaise-api>`

The fastest, most direct way to communicate between processes.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pipe</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

anchor, point = <suitkaise-api>Pipe</suitkaise-api>.pair()

class MyProcess(<suitkaise-api>Skprocess</suitkaise-api>):

    def __init__(self, pipe_point: <suitkaise-api>Pipe</suitkaise-api>.Point):
        self.pipe = pipe_point
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.pipe.send("hello")
        <suitkaise-api>result</suitkaise-api> = self.pipe.recv()
        print(<suitkaise-api>result</suitkaise-api>)

process = MyProcess(point)
process.<suitkaise-api>start</suitkaise-api>()

anchor.send("hello")

<suitkaise-api>result</suitkaise-api> = anchor.recv()
print(<suitkaise-api>result</suitkaise-api>)

process.<suitkaise-api>wait</suitkaise-api>()
```

One way pipe:
```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pipe</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>

# one way pipe: only anchor can send data, point can only receive
anchor, point = <suitkaise-api>Pipe</suitkaise-api>.pair(one_way=True)

class MyProcess(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, pipe_point: <suitkaise-api>Pipe</suitkaise-api>.Point):
        self.pipe = pipe_point
        self.<suitkaise-api>process_config</suitkaise-api>.<suitkaise-api>runs</suitkaise-api> = 1

    def <suitkaise-api>__prerun__</suitkaise-api>(self):
        self.data_to_process = self.pipe.recv()

    def <suitkaise-api>__run__</suitkaise-api>(self):
        self.process_data(self.data_to_process)

    def <suitkaise-api>__postrun__</suitkaise-api>(self):
        self.data_to_process = None
```

### So, which one should you use?

Most of the time, you should just use `<suitkaise-api>Share</suitkaise-api>`.

If you want simpler, faster, 2-way communication without setup, use `<suitkaise-api>tell</suitkaise-api>()` and `<suitkaise-api>listen</suitkaise-api>()`.

But if you still need speed, or want more manual control, use `<suitkaise-api>Pipe</suitkaise-api>`.

## Putting it all together

Throughout this page, you might have seen something called `<suitkaise-api>Pool</suitkaise-api>`.

`<suitkaise-api>Pool</suitkaise-api>` is an upgraded wrapper around `multiprocessing.<suitkaise-api>Pool</suitkaise-api>` used for parallel batch processing.

What this enables:
- process pools support `<suitkaise-api>Share</suitkaise-api>`
- process pools using `<suitkaise-api>cucumber</suitkaise-api>` for serialization
- process pools using `<suitkaise-api>Skprocess</suitkaise-api>` class objects
- process pools get access to `<suitkaise-api>sk</suitkaise-api>` modifiers

So, already, `<suitkaise-api>Pool</suitkaise-api>` is vastly more powerful than `multiprocessing.<suitkaise-api>Pool</suitkaise-api>`. especially because you can use `<suitkaise-api>Share</suitkaise-api>`.

### `<suitkaise-api>Pool</suitkaise-api>` is better, but still familiar to users

It has the 4 main map methods, with clearer names.

`map`: returns a list, ordered by input. Each item gets added to the list in the order it was added to the pool.
```python
list_in_order = <suitkaise-api>Pool</suitkaise-api>.<suitkaise-api>map</suitkaise-api>(fn_or_skprocess, items)
```

`unordered_map`: returns a list, unordered. Whatever finishes first, gets added to the list first.
```python
unordered_list = <suitkaise-api>Pool</suitkaise-api>.<suitkaise-api>unordered_map</suitkaise-api>(fn_or_skprocess, items)
```

`imap`: returns an iterator, ordered by input. Each item gets added to the iterator in the order it was added to the pool.
```python
for item in <suitkaise-api>Pool</suitkaise-api>.<suitkaise-api>imap</suitkaise-api>(fn_or_skprocess, items):
    print(item)
```

`unordered_imap`: returns an iterator, unordered. Whatever finishes first, gets added to the iterator first.
```python
for item in <suitkaise-api>Pool</suitkaise-api>.<suitkaise-api>unordered_imap</suitkaise-api>(fn_or_skprocess, items):
    print(item)
```

Since you can use `<suitkaise-api>Skprocess</suitkaise-api>` objects that can `<suitkaise-api>stop</suitkaise-api>()` themselves (or set a number of runs), you can theoretically keep running the pool and let the processes run until they are done. This opens up a lot of possibilities for complex parallel processing tasks.

### Modifiers are what make it reach the next level

`<suitkaise-api>sk</suitkaise-api>` modifiers are from another `<suitkaise-api>suitkaise</suitkaise-api>` module, and are available on most `<suitkaise-api>suitkaise</suitkaise-api>` functions and methods, including `<suitkaise-api>Pool</suitkaise-api>`.

- timeouts
- native async support
- background execution with `Future`s

And, `<suitkaise-api>Pool</suitkaise-api>` itself has a special modifier, `<suitkaise-api>star</suitkaise-api>()`, that allows you to unpack tuples into function arguments.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Pool</suitkaise-api>
import asyncio

# get a coroutine for map with a timeout
coro = <suitkaise-api>Pool</suitkaise-api>.<suitkaise-api>map</suitkaise-api>.<suitkaise-api>timeout</suitkaise-api>(20.0).<suitkaise-api>asynced</suitkaise-api>()
results = await coro(fn_or_skprocess, items)

# or, <suitkaise-api>run</suitkaise-api> in the background, get a Future
# and unpack tuples across function arguments (instead of adding the whole tuple as a single argument)
future = <suitkaise-api>Pool</suitkaise-api>.<suitkaise-api>star</suitkaise-api>().<suitkaise-api>map</suitkaise-api>.<suitkaise-api>background</suitkaise-api>()(fn_or_skprocess, items)
```

`<suitkaise-api>asynced</suitkaise-api>()` and `<suitkaise-api>background</suitkaise-api>()` do not work with each other (they do the same thing in different ways), but other than that, everything else is combinable.

These modifiers work with all map methods.

For more info on how to use these modifiers, see the `<suitkaise-api>sk</suitkaise-api>` pages or look at the `<suitkaise-api>processing</suitkaise-api>` examples.

## Works with the rest of `<suitkaise-api>suitkaise</suitkaise-api>`

`<suitkaise-api>processing</suitkaise-api>` doesn't exist in a vacuum. It's designed to work with the rest of the `<suitkaise-api>suitkaise</suitkaise-api>` ecosystem.

- `<suitkaise-api>cucumber</suitkaise-api>` handles all serialization automatically. You never think about pickle errors.
- `<suitkaise-api>timing</suitkaise-api>` provides `<suitkaise-api>Sktimer</suitkaise-api>` objects that work natively inside `<suitkaise-api>Share</suitkaise-api>` -- aggregate timing statistics across processes without any extra code.
- `<suitkaise-api>sk</suitkaise-api>` generates `_shared_meta` for your classes, which tells `<suitkaise-api>Share</suitkaise-api>` exactly which attributes each method reads and writes. This is what makes `<suitkaise-api>Share</suitkaise-api>` efficient.
- `<suitkaise-api>circuits</suitkaise-api>` provides circuit breakers that work inside `<suitkaise-api>Share</suitkaise-api>` -- one process trips the circuit, every other process sees it immediately. Cross-process fault tolerance with zero setup.
- `<suitkaise-api>paths</suitkaise-api>` gives you `<suitkaise-api>Skpath</suitkaise-api>` objects that serialize cleanly through `<suitkaise-api>cucumber</suitkaise-api>` and work the same on every machine.

Each module is useful on its own, but they were designed together. When you use `<suitkaise-api>processing</suitkaise-api>`, you get the full benefit of that integration.
"
