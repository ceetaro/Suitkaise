# Improvements Implementation Plan

## Creating a New `suitkaise` Directory

At some point, I will create a brand new `suitkaise` directory, and rename the old one to `suitkaise-depr`. this file is in the new directory.

I will then copy over all code contents from the old `suitkaise` directory to the new one.

This serves as a checkpoint so that the old code remains in case things go south.

When I start this new dir, I will apply module name changes.

<!-- ## Before Creation of a New `suitkaise` Directory

### 1. Improve `cerial` function serialization speed using references when possible

function serialization (cerial improvement):

reference vs full serialization
- goal: serialize functions faster by using references when possible
- reference: just store module path + qualname, look up on other end
- full: serialize bytecode, globals, closures, etc (slow but complete)

when to use reference
- function must be guaranteed to be exactly the same on both ends
- module-level functions: yes
- class methods: yes
- both sides have the same codebase/module installed

when to fall back to full serialization
- lambdas: anonymous, no unique name to look up
- closures: depend on captured variables from outer scope
- dynamically created functions: runtime generated, don't exist in module
- anything where lookup might give a different function

the check
- has __module__ and __qualname__
- qualname doesn't contain '<lambda>' or '<locals>'
- can actually look it up and get the same object back
- if any of these fail, fall back to full serialization

performance difference
- reference: ~50-100 bytes, ~1-10μs to serialize
- full: ~1-10KB, ~1-10ms to serialize
- 100-1000x faster with references

implementation
- try reference first
- if can_use_reference() fails, fall back to full
- deserialize by importing module and walking qualname

### 2. Improve `cerial` simple instance serialization speed

problem
- simple class instances produce heavily nested IR
- example: `Point(x=1, y=2)` creates 5+ levels of nesting
- lots of overhead: handler lookups, dict allocations, wrapping

current flow for simple instance
```python
{
    "__cerial_type__": "class_instance",
    "__handler__": "ClassInstanceHandler",
    "__object_id__": 123456,
    "state": {
        "__cerial_type__": "dict",
        "items": [
            ("module", "__main__"),
            ("qualname", "Point"),
            ("strategy", "dict"),
            ("instance_dict", {
                "__cerial_type__": "dict",
                "items": [("x", 1), ("y", 2)]
            }),
        ]
    }
}
```

overhead sources
- find handler: loop through all handlers, O(n)
- _determine_strategy(): 4+ hasattr() calls
- extract_state(): builds metadata dict with string keys
- recursive serialize on state dict: another handler lookup + wrapping
- recursive serialize on instance_dict: another handler lookup + wrapping
- every primitive wrapped in items list
- circular ref tracking for every object: id() + dict lookup

solution: fast path for simple instances
- detect "simple" instances that can skip most overhead
- simple means: module-level class, no slots, no custom serialize, only primitive attrs
- use flat IR instead of nested

fast path IR
```python
{
    "__cerial_type__": "simple_class_instance",
    "module": "__main__",
    "qualname": "Point",
    "attrs": {"x": 1, "y": 2}  # direct, no wrapping
}
```

_is_simple_instance() check
- qualname doesn't contain '<locals>'
- no __slots__ on class
- no __serialize__ method
- all attrs in __dict__ are primitives (None, bool, int, float, str, bytes)

fast path reconstruction
- import class via module + qualname
- create instance with __new__ (skip __init__)
- update __dict__ directly

skip circular ref tracking for simple instances
- simple instances with only primitive attrs cannot have circular refs
- add check in _is_circular_capable() to skip tracking

### 3. Improve handler lookup speed with caching

problem
- _find_handler() loops through all handlers for every object
- same type always gets same handler
- redundant work for repeated types

solution: cache handler by type
```python
self._handler_cache: Dict[type, Handler] = {}

def _find_handler(self, obj: Any) -> Optional[Handler]:
    obj_type = type(obj)
    if obj_type in self._handler_cache:
        return self._handler_cache[obj_type]
    
    handler = self._find_handler_slow(obj)
    self._handler_cache[obj_type] = handler
    return handler
```

cache invalidation
- cache lives for duration of serialize() call
- reset in serialize() along with other state
- or: keep across calls if handlers are static (which i think they are)

### 4. Batch primitive serialization by direct copying for primitive dicts

problem
- currently calls _serialize_recursive() on each attribute
- for dicts with only primitive values, this is wasted work
- each call has overhead: depth check, path tracking, type checks

solution: detect primitive dicts and copy directly
```python
def _all_primitive_dict(self, d: dict) -> bool:
    """Check if dict contains only primitive values."""
    for value in d.values():
        if not isinstance(value, (type(None), bool, int, float, str, bytes)):
            return False
    return True

# In _serialize_recursive for dicts:
if self._all_primitive_dict(obj):
    # Fast path: direct copy, no recursion
    return dict(obj)
else:
    # Slow path: recurse on each value
    return {k: self._serialize_recursive(v) for k, v in obj.items()}
```

applies to
- instance __dict__ with only primitive attrs
- any dict in extracted state that's all primitives
- config dicts, metadata dicts, etc.

combined with simple instance fast path
- simple instance check already requires all primitive attrs
- can directly copy __dict__ without any recursion -->


<!-- ## During Creation of a New `suitkaise` Directory

### 1. Rename modules

`skpath` -> `paths`

`processing` -> `processing` (no change)

`sktime` -> `timing`

`cerial` -> `cerial` (no change)

`circuit` -> `circuits`

New Import Usage:

supports direct import from suitkaise dir

```python
from suitkaise import TimeThis
```

supports import from suitkaise.(module_name)

```python
from suitkaise.timing import TimeThis
```

### 1a. update object names

SKPath to Skpath -->


<!-- ### 2. Upgrade `circuits` module

basic ideas:

- move `Yawn` to `circuits` module
  - renamed to `Circuit`
  - methods updated to short() and trip()

```python
from suitkaise import Circuit

circ = Circuit(
    num_shorts_to_trip=5, 
    sleep_time_after_trip=0.5,
    factor=1 # exponential backoff factor default is 1
    max_sleep_time=10.0 # max sleep time default is 10.0
    )

circ.short()
circ.short()
circ.short()
circ.short()    
circ.short()

# sleeps here
# auto resets, applying factor 
# (no broken property)
```

- `Circuit` -> `BreakingCircuit`
  - implementation changes to include exponential backoff

```python
from suitkaise import BreakingCircuit

circ = BreakingCircuit(
    num_shorts_to_trip=5, 
    sleep_time_after_trip=0.5,
    factor=1.1, # this one is using exponential backoff
    max_sleep_time=10.0 # this matters now
)

while not circ.broken:
    
    circ.short()
    circ.short()
    circ.short()
    circ.short()    
    circ.short()

    # sleeps here
    # does not reset

# exits block, circ.broken has been set to True


if circ.broken:
    print("Circuit broken, resetting")
    circ.reset() # resets state via manual call

# applies factor when reset() is called
# has the broken flag
```

you could even have BreakingCircuit inherit from Circuit and add the reset() and broken flag

whatever you do, make sure code for mirroring functionality is the same in both classes. -->

<!-- ### Update `paths` module

change `Skpath.np` to `Skpath.rp`
- same implementation, just different name to avoid Numpy as np conflict

Add utils

- is_valid_filename() - checks if a filename is valid

- streamline_path() - sanitizes a path by removing invalid characters

    this is something the user can use to streamline path names
    - cut down to a max length
    - replace invalid characters with a different character
    - lowercase the path
    - strip whitespace
    - allow/disallow unicode characters

### Update `timing` module

add a threshold arg to TimeThis and timethis that only records a time above a certain threshold. default is 0.0. -->

<!-- ## After Creation of a New `suitkaise` Directory

### Add `Share`

`Share` is a class that allows you to share data between processes. 

```python
from suitkaise.processing import Share
from suitkaise.timing import Sktimer

share = Share()
share.timer = Sktimer() # actually a Sktimer.shared() instance
```

### Streamline all module objects

All module objects need to have:

- a regular/sync version (what it is now)
- an async version
- a shared state version that works with Share() instances

How? we wrap each object and function in a class that does this:

```python
from suitkaise.timing import Sktimer

# regular version
timer = Sktimer()

# async version
async_timer = Sktimer.asynced()

# shared state version (users don't see this)
shared_timer = Sktimer.shared()
```

```python
class Sktimer:


    class regular:

    class asynced:

    class shared:
```

```python
from suitkaise.timing import Sktimer
from suitkaise.processing import Share

share = Share()

share.timer = Sktimer() # actually a Sktimer.shared() instance
share.counter = 0
share.results = {}
```

Async versions will be done manually, not with to_thread() for the actual module objs. for user objects, to_thread() will be used for async versions.

### Add `Skfunction`

(ensure that this module name does not conflict with base python code or types)

This module will contain a class that wraps user's functions and allows them to follow the *.asynced() pattern.

```python
from suitkaise import Skfunction

def add(x, y):
    return x + y

add = Skfunction(add)

# then...
result = await add.asynced(1, 2)
```

### Add `Skclass`

This will contain a way that wraps classes and allows them to follow the *.shared() pattern, and allow all methods to follow the *.asynced() pattern and work with Share() instances.

```python
from suitkaise import Skclass
import threading

class Counter:

    def __init__(self):
        self.lock = threading.RLock()
        self.total = 0

    def increment(self):
        with self.lock:
            self.total += 1

    def decrement(self):
        with self.lock:
            self.total -= 1

    @property
    def value(self):
        with self.lock:
            return self.total


counter = Skclass(Counter)
```

### Add `@sk` decorator

This decorator can be used to wrap user functions and classes and convert them to the appropriate Skfunction or Skclass instances.

```python
from suitkaise import sk

@sk # or @sk() whatever makes more sense implementing
def my_function():
    return 1

@sk # or @sk() whatever makes more sense implementing
class MyClass:
    def __init__(self):
        self.total = 0

    def increment(self):
        self.total += 1

    def decrement(self):
        self.total -= 1

    @property
    def value(self):
        return self.total
``` -->

<!-- ---

## Testing Plan

### Structure

```
tests/
  timing/
    test_timer.py           # Sktimer class tests
    test_timethis.py        # TimeThis context manager tests
    test_functions.py       # time(), sleep(), elapsed(), sleep.asynced()
    test_decorators.py      # @timethis decorator tests
    benchmarks.py           # Timing module benchmarks
    run_all_tests.py        # Run all timing tests
    run_all_benchmarks.py   # Run all timing benchmarks
  
  circuits/
    test_circuit.py         # Circuit class tests
    test_breaking_circuit.py # BreakingCircuit class tests
    test_async.py           # .asynced() method tests
    benchmarks.py           # Circuits module benchmarks
    run_all_tests.py
    run_all_benchmarks.py
  
  paths/
    test_skpath.py          # Skpath class tests
    test_utilities.py       # Utility function tests
    test_root_detection.py  # Project root detection tests
    benchmarks.py
    run_all_tests.py
    run_all_benchmarks.py
  
  cerial/
    test_primitives.py      # Primitive serialization tests
    test_complex.py         # Complex object serialization tests
    test_edge_cases.py      # Edge cases and error handling
    benchmarks.py
    run_all_tests.py
    run_all_benchmarks.py
  
  processing/
    test_process.py         # Process class tests
    test_pool.py            # Pool class tests
    test_share.py           # Share class tests
    test_share_integration.py # Share with Sktimer, Circuit, user classes
    benchmarks.py
    run_all_tests.py
    run_all_benchmarks.py
  
  sk/
    test_skclass.py         # Skclass wrapper tests
    test_skfunction.py      # Skfunction wrapper tests
    test_decorator.py       # @sk decorator tests
    test_async_chaining.py  # AsyncSkfunction chaining tests
    benchmarks.py
    run_all_tests.py
    run_all_benchmarks.py
  
  integration/
    test_share_timer.py     # Share + Sktimer multiprocess
    test_share_circuit.py   # Share + Circuit multiprocess
    test_async_patterns.py  # Async patterns across modules
    run_all_tests.py
  
  run_all_tests.py          # Run ALL tests across all modules
  run_all_benchmarks.py     # Run ALL benchmarks across all modules
``` -->

<!-- ### Test Requirements

1. **IDE Runnable**: Every test file has `if __name__ == '__main__':` block
2. **Self-contained**: Each test file can run independently
3. **Comprehensive**: Test happy paths, edge cases, error conditions
4. **Async Support**: Use `asyncio.run()` for async tests (no pytest-asyncio dependency)
5. **Clear Output**: Print pass/fail status with descriptive messages

### Test Categories Per Module

#### timing
- Sktimer: start/stop, lap, pause/resume, reset, statistics (mean, median, stdev, etc.)
- Sktimer: concurrent/multi-threaded usage, nested timing
- TimeThis: context manager, with explicit Sktimer, threshold
- sleep: basic sleep, sleep.asynced()
- timethis decorator: auto timer, explicit timer, threshold

#### circuits
- Circuit: short counting, trip behavior, auto-reset, backoff, reset_backoff
- Circuit: short.asynced(), trip.asynced()
- BreakingCircuit: short, trip, broken flag, manual reset, backoff
- BreakingCircuit: short.asynced(), trip.asynced()

#### paths
- Skpath: creation, path operations, relative paths
- Root detection: find project root, custom root
- Utilities: is_valid_filename, streamline_path, get_caller_path

#### cerial
- Primitives: int, float, str, bytes, bool, None
- Collections: list, dict, tuple, set
- Complex: class instances, nested objects, circular references
- Functions: module-level, lambdas, closures
- Edge cases: unpicklable objects, large objects

#### processing
- Process: lifecycle (__run__, __result__, __error__), timing
- Pool: map, starmap, async results
- Share: with Sktimer, Circuit, user classes
- Share: auto-wrap with Skclass, proxy behavior

#### sk
- Skclass: auto _shared_meta, blocking detection, .asynced()
- Skfunction: .asynced(), .retry(), .timeout(), .background()
- AsyncSkfunction: chaining .timeout().retry()
- @sk decorator: on classes, on functions
- SkModifierError: raised for unsupported modifiers

### Benchmark Categories

#### timing
- Sktimer.start/stop overhead
- Statistics calculation speed (1K, 10K, 100K measurements)
- sleep precision

#### circuits
- Circuit.short() throughput
- Backoff calculation overhead

#### cerial
- Primitive serialization speed
- Complex object serialization speed
- Large object handling

#### processing
- Process spawn overhead
- Pool.map throughput
- Share read/write latency

#### sk
- Skclass wrapping overhead
- Skfunction call overhead vs raw function
- AST analysis speed

### Benchmark Format

```python
def benchmark_timer_start_stop():
    """Measure Sktimer.start/stop overhead."""
    timer = Sktimer()
    iterations = 100_000
    
    start = time.perf_counter()
    for _ in range(iterations):
        timer.start()
        timer.stop()
    elapsed = time.perf_counter() - start
    
    ops_per_sec = iterations / elapsed
    us_per_op = (elapsed / iterations) * 1_000_000
    
    print(f"Sktimer.start/stop: {ops_per_sec:,.0f} ops/sec ({us_per_op:.2f} µs/op)")
```

### Running Tests

```bash
# Run single test file (IDE or command line)
python tests/timing/test_timer.py

# Run all tests for a module
python tests/timing/run_all_tests.py

# Run all benchmarks for a module
python tests/timing/run_all_benchmarks.py

# Run ALL tests
python tests/run_all_tests.py

# Run ALL benchmarks
python tests/run_all_benchmarks.py
``` -->

<!-- ## Update docs

Here is the current progress on the docs:

cerial:

- [ done ] how-to-use.md
- [ done ] how-it-works.md
- [ done ] supported-types.md

processing:

- [ done ] processing-how-to-use.md
- [ done ] processing-how-it-works.md

paths:

- [ done ] paths-how-to-use.md
- [ done ] paths-how-it-works.md

timing:

- [ done ] timing-how-to-use.md
- [ done ] timing-how-it-works.md

circuits:

- [ done ] circuits-how-to-use.md
- [ done ] circuits-how-it-works.md

sk:

- [ done ] sk-how-to-use.md
- [ done ] sk-how-it-works.md -->

## Final additions

add downloadable tests to the site

add badges (coverage, CI status, etc) to the README

add a quick start guide to the README and the site

on site add pronunciation (its pronounced exactly like the word suitcase)

add at least a couple of examples to each module's examples page

- examples should also come with a downloadable version of the example code, complete with comments, a runnable result, and verbose output

run all tests on windows and linux (if possible)

maybe update the homepage to have more real content (like a running blog)

add a motto that relates to the suitcase concept

update the docs downloader to work

fix benchmark tests on windows


<!-- add Skpath.copy_to() and Skpath.move_to() methods

add Skprocess.run() that does start + wait + result

add rate_limit() modifier for sk -->

<!-- ```python
@sk
def my_function():
    time.sleep(1)
    return "Hello, world!"

my_function.rate_limit(per_second=N)
``` -->

<!--
add more blocking call patterns (boto3, redis, pymongo, etc)

add timethis.asynced() for native async funcs

add rolling stats to Sktimer (keep only last N measurements)
- how do we determine how many measurements to keep?

```python
from suitkaise.timing import Sktimer, timethis

t = Sktimer(max_times=100)

@timethis(max_times=100)
def my_function():
    time.sleep(1)
    return "Hello, world!"

for i in range(100):
    my_function()

print(t.mean)

```

add a JSON output converter for cerial IRs

```python
from suitkaise import cerial

# serializes to python dict IR and then converts to JSON
cerial.to_json(obj)
``` -->

retest new implementation on window

find a way to advertise cerial when people look up "cant pickle X"

update cerial benchmarks in docs and supported types to reflect improvements

refactor site to have a more interactive home page that shows off things more

upload version to test pypi

2 paragraph summary on how modules work and finish quick start guide

```text
Think of the printing press, an invention that made production of paper media faster, more standardized, and less prone to human error. People didn't have to write books by hand anymore, saving them a large amount of time and effort.

The result: the world was flooded with books, and the "Information Age" began.

There are many things in Python that need their own printing press to make using them faster, more standardized, and less prone to human error.

Parallel processing, Python-to-Python serialization, file path handling, and more.

`suitkaise` gives you these printing presses.

The name is inspired by "hacker laptops", where the user opens a briefcase and hacks some mainframe in 5 seconds.

- `processing` - Unlocks the full potential of parallel programming in Python.

60% of parallel processing is batch processing, where you process N number of items at once instead of just 1. `processing` gives you a `Pool` class that makes batch processing easy, with 3 standard pooling patterns.

The other 40% is creating long-running, complex subprocesses that do more than just look up data or compute something. Creating these is generally a nightmare even for experienced developers. `processing` gives you a `Skprocess` class that makes creating these easy, with coded lifecycle methods to setup, run, cleanup, and more. These classes include timing, error handling, and run the process internally, so you don't have to worry about managing the process yourself.

Finally, `processing` gives you a `Share` class.

Every developer knows how to create a class instance and add objects to it.

And that's all you have to do with `Share`. Instantiate it, add objects to it, and pass it to your subprocesses. It ensures that everything syncs up and remains in sync for you. Even complex classes can be added and used just like you would use it normally.

How? `cerial`, the serialization engine that can handle a vast amount of things that `pickle`, `cloudpickle`, and `dill` cannot, including complex, user created class instances that would fail to serialize with the other options.

- `cerial` - Serialize (almost) anything.

`cerial` outperforms all competitors in coverage, almost entirely eliminating errors when converting to and from bytes. Things like locks, generators, file handles, and more are all covered. Additionally, it has faster speed than `cloudpickle` and `dill` for many simple types, and is also faster in most cases for the more complex types as well.

Why is this awesome? You don't have to worry about errors anymore. You now have access to a custom class, the objects you want to use in it but couldn't before, and the ability to just share data between processes without thinking, all powered by this engine. You don't even have to use the other modules to get an upgrade. This is just simply better.

- `paths` - everything path related is so much more simple

It includes `Skpath`, a path object that uses an auto-detected project root to normalize all of your paths for you. It is cross platform compatible. An `Skpath` made on Jeff's Mac will be the same as the same `Skpath` made on Sarah's Windows laptop.

It also includes an `@autopath` decorator that can be used to automatically streamline all of your paths to a specific type.

- `timing` - times your code with one line

`timing` gives you a `Sktimer` class that is the core piece of this module. It powers `@timethis` and the `TimeThis` context manager.

Both of these allow you to time your code with one line, and have full control of the resulting timer data with 2.

- `circuits` - manage your execution flow more cleanly

`circuits` gives you two patterns to manage your code. 

  - `Circuit` - auto-resets after sleeping, great for rate limiting, resource management, and more
  - `BreakingCircuit` - stays broken until manually reset, great for stopping execution after a certain number of failures with extra control

- `sk` - modify your functions and methods without changing their code

`sk` can be used as a decorator or a function, and adds some special modifiers to your functions and methods (if you decorate/convert the class). Using `sk` on a class will also make it run quicker in `Share`.

  - `.retry()` - retry it when it fails
  - `.timeout()` - return an error if it takes too long
  - `.background()` - run it in the background and get the result later
  - `.asynced()` - get an async version of it if it has calls that block your code from running
  - .rate_limit() - limit the number of calls it makes per second
```


### Real world example

poker machine simulation

6 different ML models play poker against each other in shared memory

-------

creating a language app based on the most common words

- scan japanese website text and find the most common words and characters


---

# Reconnectors

## What are Reconnectors?

When `cerial` serializes objects, some resources cannot be directly pickled:
- Database connections (sockets to remote servers)
- Network sockets
- File handles and pipes
- Threads
- Compiled regex matches

Instead of failing, `cerial` replaces these with **Reconnector** placeholder objects that store enough metadata to recreate the resource later.

```
Original Object ──serialize──> Reconnector Placeholder ──reconnect()──> New Live Resource
```

### Reconnector types in cerial

| Reconnector | Original Type | Stored Metadata |
|-------------|--------------|-----------------|
| `DbReconnector` | Database connections | module, class_name, connection params |
| `SocketReconnector` | `socket.socket` | family, type, proto, addresses |
| `PipeReconnector` | Pipe file objects | mode, direction |
| `ThreadReconnector` | `threading.Thread` | name, daemon, target, args |
| `SubprocessReconnector` | `subprocess.Popen` | args, returncode, output |
| `MatchReconnector` | `re.Match` | pattern, string, pos, groups |

---

## Using Reconnector.reconnect()

Each Reconnector has a `reconnect()` method that creates a new live resource.

### Resources that don't need auth

These reconnect with no args (`reconnect()`):

```python
from suitkaise import cerial

# Serialize object with sockets, pipes, threads, sqlite, duckdb, etc.
data = cerial.serialize(my_object)
restored = cerial.deserialize(data)

# restored.socket is a SocketReconnector, not a socket
# Call reconnect() to get a live socket
restored.socket = restored.socket.reconnect()

# Or reconnect everything at once
restored = cerial.reconnect_all(restored)
```

### Resources that need auth/credentials

Only password needs to be passed - connection metadata (host, port, user, database) is stored during serialization:

```python
# Deserialize - db connection becomes PostgresReconnector
restored = cerial.deserialize(data)

# restored.db has stored host, port, user, database
# Only password needs to be provided
restored.db = restored.db.reconnect("secret")
```

For Elasticsearch, `password` can be the api_key if no user was stored.
For InfluxDB v2, `password` represents the token.

---

## Using reconnect_all()

Instead of calling `.reconnect()` on each Reconnector individually, use `reconnect_all()` to traverse an object and reconnect everything:

```python
from suitkaise import cerial

data = cerial.serialize(my_object)
restored = cerial.deserialize(data)

# Reconnect all - just passwords, connection metadata is stored
restored = cerial.reconnect_all(restored, **{
    "psycopg2.Connection": {
        "*": "secret",
    },
    "redis.Redis": {
        "*": "redis_pass",
    },
})
```

### Password structure

```python
{
    "TypeKey": {
        "*": "password",           # default password for all instances
        "attr_name": "password",   # specific password for attr named "attr_name"
    }
}
```

- **Type keys** are `"module.ClassName"` (e.g., `"psycopg2.Connection"`)
- **`"*"`** provides default password for all instances of that type
- **Specific attr names** override the default
- Connection metadata (host, port, user, database) is stored during serialization

### Multiple connections of same type

```python
restored = cerial.reconnect_all(restored, **{
    "psycopg2.Connection": {
        "*": "default_pass",
        "analytics_db": "analytics_pass",  # override for self.analytics_db
    },
})
```

### No password needed

For resources without auth, just call with no args:

```python
# Sockets, threads, pipes, sqlite, duckdb, regex matches, etc.
restored = cerial.reconnect_all(restored)
```

---

## Supported database kwargs

Only secret details need to be passed - connection metadata (host, port, user, database) is stored during serialization:

### PostgreSQL (psycopg2)

```python
"psycopg2.Connection": {
    "*": {"password": "secret"}  # host/port/user/database stored
}
```

### MySQL (pymysql)

```python
"pymysql.Connection": {
    "*": {"password": "secret"}  # host/port/user/database stored
}
```

### MongoDB (pymongo)

```python
"pymongo.Mongoclient": {
    "*": {"password": "secret"}  # host/port/username/authSource stored
}
```

### Redis

```python
"redis.Redis": {
    "*": {"password": "secret"}  # host/port/db stored
}
```

### Cassandra

```python
"cassandra.Cluster": {
    "*": {"password": "secret"}  # contact_points/port/username stored
}
```

### Elasticsearch

```python
"elasticsearch.Elasticsearch": {
    "*": {"password": "secret"}  # hosts/user stored
}
```

### SQLAlchemy

```python
"sqlalchemy.Engine": {
    "*": {"password": "secret"}  # url or driver/host/port/user/database stored
}
```

### ODBC (pyodbc)

```python
"pyodbc.Connection": {
    "*": {"password": "secret"}  # dsn or driver/server/port/database/user stored
}
```

### Neo4j

```python
"neo4j.Driver": {
    "*": {"password": "secret"}  # uri or host/port/scheme/user stored
}
```

### InfluxDB v2

```python
"influxdb_client.Influxdbclient": {
    "*": {"token": "my-token"}  # url or host/port/org stored
}
```

### Snowflake

```python
"snowflake.Connection": {
    "*": {"password": "secret"}  # user/account/warehouse/database/schema stored
}
```

### Oracle (oracledb)

```python
"oracledb.Connection": {
    "*": {"password": "secret"}  # dsn or host/port/service_name/user stored
}
```

### ClickHouse

```python
"clickhouse_driver.Client": {
    "*": {"password": "secret"}  # host/port/user/database stored
}
```

### MSSQL (pymssql)

```python
"pymssql.Connection": {
    "*": {"password": "secret"}  # host/port/user/database stored
}
```

### SQLite

```python
# No kwargs needed - path is stored, no auth required
"sqlite3.Connection": {}
```

### DuckDB

```python
# No kwargs needed - path is stored, no auth required
"duckdb.Connection": {}
```

---

# autoreconnect (processing)

The `@autoreconnect` decorator makes `Skprocess` automatically call `reconnect_all()` after deserialization in the child process.

## Basic usage

```python
from suitkaise.processing import Skprocess, autoreconnect

@autoreconnect()
class MyProcess(Skprocess):
    def __init__(self):
        self.socket = socket.socket(...)  # becomes SocketReconnector
    
    def __run__(self):
        # self.socket is a live socket again
        self.socket.send(b"hello")
```

## With credentials

```python
from suitkaise.processing import Skprocess, autoreconnect

@autoreconnect(**{
    "psycopg2.Connection": {
        "*": "secret",
        "analytics_db": "other_pass",
    },
    "redis.Redis": {
        "*": "redis_pass",
    },
})
class MyProcess(Skprocess):
    def __init__(self):
        self.db = psycopg2.connect(...)
        self.analytics_db = psycopg2.connect(...)
        self.cache = redis.Redis(...)
    
    def __run__(self):
        # db, analytics_db, cache are all live connections
        cursor = self.db.cursor()
        ...
```

## Manual reconnect in __prerun__

If you need dynamic credentials (e.g., from env vars), use `reconnect_all()` directly:

```python
from suitkaise.processing import Skprocess
from suitkaise.cerial import reconnect_all
import os

class MyProcess(Skprocess):
    def __init__(self):
        self.db = psycopg2.connect(...)
    
    def __prerun__(self):
        reconnect_all(self, **{
            "psycopg2.Connection": {
                "*": os.environ["DB_PASSWORD"],
            },
        })
    
    def __run__(self):
        cursor = self.db.cursor()
        ...
```

# code review

review each modules code and streamline comments, checking that everything looks how it should.

## 1st pass - focus on code

- cerial - done
- circuits - done
- paths - done
- processing - done
- sk - done
- timing - done


## 2nd pass - focus on api docstrings

- cerial - done
- circuits - done

## 3rd pass - focus on tests

## 4th pass - focus on _docs

## 5th pass - focus on README and quick start guide

## 6th pass - review examples and create more for each module

## 7th pass - rereview examples

## 8th pass - final review of everything

## bump version to 1.0.0, publish to PyPI, and release