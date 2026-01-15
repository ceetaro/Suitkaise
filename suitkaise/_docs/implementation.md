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

## After Creation of a New `suitkaise` Directory

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
```

---

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
```

### Test Requirements

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
- NotAsyncedError: raised for non-blocking

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
```

## Update docs

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
- [ done ] sk-how-it-works.md

## Final additions

add type stubs for IDE autocompletion

add downloadable tests to the site and pytest fixtures

add a CLI

add async variants

create a changelog for tracking versions

add badges (coverage, CI status, etc) to the README

add a quick start guide to the README and the site

on site and in the README, add pronunciation (its pronounced exactly like suitcase)

add at least a couple of examples to each module's examples page

- examples should also come with a downloadable version of the example code, complete with comments, a runnable result, and verbose output

run all tests on windows and linux (if possible)

maybe update the homepage to have more real content (like a running blog)

add a motto that relates to the suitcase concept





