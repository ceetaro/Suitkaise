# Why you should use `processing`

## TLDR

- **Anything works in parallel** - Locally-defined functions, lambdas, closures, live connections all work
- **Easiest shared state possible** - `share.counter = 0` just works across processes
- **Class-based processes** - No more giant, messy functions. Lifecycle hooks organize your code naturally.
- **Crash and restart** - `lives=3` and your process auto-retries. No try/except loops.
- **Timeouts** - Advanced timeout system that works on all platforms.
- **Database connections just work** - `@autoreconnect` brings live connections into subprocesses. Normally impossible.
- **Sync and async in one API** - Same code, add `.asynced()` when you need it.

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
        result = transform(item)
        results.append(result)
    return results

    
with Pool(4) as pool:
    return pool.map(transform, lists_of_items)
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

The standard library's `multiprocessing.Pool` is hardcoded to use `pickle`. To use `cloudpickle` or `dill`, you have to:

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

with mp.Pool(4) as pool:
    results = pool.map(my_function, items)

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

Or, you could just use `processing`.

## `processing` uses `cucumber` instead of `pickle`

By default, `processing` uses `cucumber`, `suitkaise`'s serialization engine, instead of `pickle`.

### Problem actually solved

`cucumber` handles everything.

- handles everything from ints to complex user created classes with live connections
- better than `pickle`
- better than `cloudpickle`
- better than `dill`
- automatically used by `processing`

`cucumber` actually solves the problem of things not being serializable. And the problem of actually being compatible with multiprocessing.

(For more info, see the `cucumber` pages)

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


# run the single process (not even in a Pool)
process = multiprocessing.Process(target=process_data, args=(items,))
process.start()
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
    
    def run(self):
        # do work
        result = process_items(self.items)
        self.result_queue.put(result)  # send back via queue

queue = multiprocessing.Queue()
process = ProcessData(items, queue)
process.start()
process.join()
result = queue.get()  # retrieve from queue, not process.result
```

This is a step in the right direction, but it is by no means perfect.
- still sort of confusing in general
- you have to manually manage the queue
- this will still use base `pickle`
- you have to manually call `super().__init__()` and implement `run()`
- still no automatic retries, timeouts, timing, or error handling

## `Skprocess`

A class is the overall solution that should've been used all along.

But we still have no structure and no lifecycle.
- missing actual methods to split up code into smaller pieces
- missing good error handling
- hard to share state, must bring in a different object just for that
- overall, code is still missing a lot of the structure and automation that is expected

`Skprocess` is a class that goes above and beyond for you.
- automatically uses `cucumber`
- supports `Share` (very important later)
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
- fast and controlled bidirectional communication with `Pipe`

Let's make a process that queries a database for user data based on given input from a parent process.

Requirements:
- Receive query parameters from parent
- Connect to database and execute query
- Handle connection failures with retry
- Timeout if query takes too long
- Track timing statistics
- Return results to parent
- Clean up connection on exit

Without `Skprocess` - *92 lines*

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
        self.total_time = total_time
        self.query_count = query_count
        self.stop_event = stop_event
        self.db_config = db_config
        self.timeout = 30
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
    
    def run(self):
        # manual connection setup
        self._connect()
        
        # manual signal handling for timeouts
        signal.signal(signal.SIGALRM, self._timeout_handler)
        
        try:
            while not self.stop_event.is_set():
                # check for incoming query (non-blocking)
                try:
                    query_params = self.task_queue.get(timeout=0.1)
                except:
                    # no query received
                    self.result_queue.put({'status': 'no query', 'data': None})
                    continue
                
                # manual timing
                start = time.time()
                signal.alarm(self.timeout)
                
                try:
                    cursor = self.conn.cursor()
                    cursor.execute(query_params['sql'], query_params.get('params'))
                    results = cursor.fetchall()
                    cursor.close()
                    
                    signal.alarm(0)
                    elapsed = time.time() - start
                    
                    # manual stats tracking with locks
                    with self.stats_lock:
                        self.total_time.value += elapsed
                        self.query_count.value += 1
                    
                    # different status based on results
                    if not results:
                        self.result_queue.put({'status': 'error', 'data': None})
                    else:
                        self.result_queue.put({'status': 'ok', 'data': results})
                    
                except TimeoutError:
                    signal.alarm(0)
                    self.result_queue.put({'status': 'error', 'error': 'timeout'})
                except Exception as e:
                    signal.alarm(0)
                    self.result_queue.put({'status': 'error', 'error': str(e)})
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
worker.start()

# list of queries to run (counted as a single line)
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
    result = result_queue.get(timeout=30)  # need manual timeout here too
    results.append(result)

# signal stop and wait for cleanup
stop_event.set()
worker.join()

# manual timing calculation
if query_count.value > 0:
    avg_time = total_time.value / query_count.value
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

With `Skprocess` - *40 lines*

```python
# comments and whitespace excluded from line count
from suitkaise.processing import Skprocess, autoreconnect
import psycopg2

@autoreconnect(**{"psycopg2.Connection": {"*": "password"}})
class DatabaseWorker(Skprocess):

    def __init__(self, db_connection)

        # this automatically reconnects
        self.db = db_connection

        # built in configuration
        # run indefinitely until stop() is called
        self.process_config.runs = None
        # NOTE: this is the default: here for clarity, not counted in line count

        # 3 lives (2 extra attempts after the first failure)
        self.process_config.lives = 3

        # 30 second timeout per query
        self.process_config.timeouts.run = 30.0
    
    def __prerun__(self):
        # receive query from parent (non-blocking check)
        msg = self.listen(timeout=0.1)
        self.query = msg if msg else None
    
    def __run__(self):
        if not self.query:
            return
        cursor = self.db.cursor()
        cursor.execute(self.query['sql'], self.query.get('params'))
        self.results = cursor.fetchall()
        cursor.close()
    
    def __postrun__(self):

        if self.query:
            if not self.results:
                self.tell({'status': 'error', 'data': None})
            else:
                self.tell({'status': 'ok', 'data': self.results})

        else:
            self.tell({'status': 'no query', 'data': None})
    
    def __onfinish__(self):
        self.db.close()

# usage

# connect to the database
db = psycopg2.connect(host='localhost', database='mydb', password='secret')

# init and start the worker process
worker = DatabaseWorker(db)
worker.start()

# list of queries to run (counted as a single line)
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
    worker.tell(query)
    result = worker.listen(timeout=timeout)
    results.append(result)

# request stop (join) and wait for it to finish
worker.stop()
worker.wait()

# automatically timed
print(f"Avg query time: {worker.__run__.timer.mean:.3f}s")
```

- 2x less code
- 1 import line for all of your multiprocessing
- nothing is manual
- everything is organized
- uses `cucumber` for serialization
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


## `Share`

`Share` is the ultimate solution to shared state in Python.

Pros:
- literally add any object to it and it will work the same exact way in shared memory
- as simple as it gets
- uses `cucumber` for serialization, so all objects work
- ensures that everything stays in sync
- works across any number of processes

Cons:
- slowest overall option
- overhead
- cannot share `multiprocessing.*` objects (Python limitation)

```python
from suitkaise.processing import Skprocess, Share, Pool
import logging

share = Share()
share.counter = 0
share.log = logging.getLogger("ShareLog")



class ShareCounter(Skprocess):

    # pass the Share instance to the process
    def __init__(self, share: Share):
        self.share = share
        self.process_config.runs = 10

    def __run__(self):
        self.share.counter += 1
        self.share.log.info(f"{self.share.counter}")



# just add share
process = MyProcess(share)

pool = Pool(workers=4)
pool.map(ShareCounter, [share] * 10)

print(share.counter) # 100 (10 total workers, 10 runs each)
print(share.log.messages) # ['1', '2', '3', '4', '5', ..., '100'] in order
```

In 20 lines, I made a counter that works in a parallel pool, that will loop exactly 10 times, logging its progress. Not a single result is needed, as everything just got added to shared memory, and that shared memory was 100% in sync.

### 100% worth the slow speed

`Share` is about 3x slower than `multiprocessing.Manager`.

But every object works exactly the same.

To add them: assign them to attributes.

To use them: access and update them as normal.

## `processing` still has 2 more options for sharing state

`processing` has 2 high speed options for sharing state.

### 1. `Skprocess.tell()` and `Skprocess.listen()`

The 2 queue-like methods that are a part of `Skprocess` (and all inheriting classes).

These are automatically 2 way, and use `cucumber`.

```python
from suitkaise.processing import Skprocess

class MyProcess(Skprocess):
    def __prerun__(self):

        self.command = self.listen(timeout=1.0)

    def __run__(self):

        if self.command == "stop":
            self.stop()

        elif self.command == "print":
            print("hello")

        else:
            raise ValueError(f"Unknown command: {self.command}")

    def __postrun__(self):
        self.command = None
        self.tell("command received")
        


p = MyProcess()
p.start()
for i in range(10):
    p.tell("print")
    result = p.listen(timeout=1.0)
    if result != "command received":
        break

p.tell("stop")
p.wait()
```

### 2. `Pipe`

The fastest, most direct way to communicate between processes.

```python
from suitkaise.processing import Pipe, Skprocess

anchor, point = Pipe.pair()

class MyProcess(Skprocess):

    def __init__(self, pipe_point: Pipe.Point):
        self.pipe = pipe_point
        self.process_config.runs = 1

    def __run__(self):
        self.pipe.send("hello")
        result = self.pipe.recv()
        print(result)

process = MyProcess(point)
process.start()

anchor.send("hello")

result = anchor.recv()
print(result)

process.wait()
```

One way pipe:
```python
from suitkaise.processing import Pipe, Skprocess

# one way pipe: only anchor can send data, point can only receive
anchor, point = Pipe.pair(one_way=True)

class MyProcess(Skprocess):
    def __init__(self, pipe_point: Pipe.Point):
        self.pipe = pipe_point
        self.process_config.runs = 1

    def __prerun__(self):
        self.data_to_process = self.pipe.recv()

    def __run__(self):
        self.process_data(self.data_to_process)

    def __postrun__(self):
        self.data_to_process = None
```

### So, which one should you use?

Most of the time, you should just use `Share`.

If you want simpler, faster, 2-way communication without setup, use `tell()` and `listen()`.

But if you still need speed, or want more manual control, use `Pipe`.

## Putting it all together

Throughout this page, you might have seen something called `Pool`.

`Pool` is an upgraded wrapper around `multiprocessing.Pool` used for parallel batch processing.

What this enables:
- process pools support `Share`
- process pools using `cucumber` for serialization
- process pools using `Skprocess` class objects
- process pools get access to `sk` modifiers

So, already, `Pool` is vastly more powerful than `multiprocessing.Pool`. especially because you can use `Share`.

### `Pool` is better, but still familiar to users

It has the 4 main map methods, with clearer names.

`map`: returns a list, ordered by input. Each item gets added to the list in the order it was added to the pool.
```python
list_in_order = Pool.map(fn_or_skprocess, items)
```

`unordered_map`: returns a list, unordered. Whatever finishes first, gets added to the list first.
```python
unordered_list = Pool.unordered_map(fn_or_skprocess, items)
```

`imap`: returns an iterator, ordered by input. Each item gets added to the iterator in the order it was added to the pool.
```python
for item in Pool.imap(fn_or_skprocess, items):
    print(item)
```

`unordered_imap`: returns an iterator, unordered. Whatever finishes first, gets added to the iterator first.
```python
for item in Pool.unordered_imap(fn_or_skprocess, items):
    print(item)
```

Since you can use `Skprocess` objects that can `stop()` themselves (or set a number of runs), you can theoretically keep running the pool and let the processes run until they are done. This opens up a lot of possibilities for complex parallel processing tasks.

### Modifiers are what make it reach the next level

`sk` modifiers are from another `suitkaise` module, and are available on most `suitkaise` functions and methods, including `Pool`.

- timeouts
- native async support
- background execution with `Future`s

And, `Pool` itself has a special modifier, `star()`, that allows you to unpack tuples into function arguments.

```python
from suitkaise.processing import Pool
import asyncio

# get a coroutine for map with a timeout
coro = Pool.map.timeout(20.0).asynced()
results = await coro(fn_or_skprocess, items)

# or, run in the background, get a Future
# and unpack tuples across function arguments (instead of adding the whole tuple as a single argument)
future = Pool.star().map.background()(fn_or_skprocess, items)
```

`asynced()` and `background()` do not work with each other (they do the same thing in different ways), but other than that, everything else is combinable.

These modifiers work with all map methods.

For more info on how to use these modifiers, see the `sk` pages or look at the `processing` examples.