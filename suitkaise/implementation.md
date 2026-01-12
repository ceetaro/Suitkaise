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

- `Circuit` --> `BreakingCircuit`
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

### Update `paths` module

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

add a threshold arg to TimeThis and timethis that only records a time above a certain threshold. default is 0.0.

## After Creation of a New `suitkaise` Directory

### Add `Share`

`Share` is a class that allows you to share data between processes. 

```python
from suitkaise.processing import Share
from suitkaise.timing import Timer

share = Share()
share.timer = Timer() # actually a Timer.shared() instance
```

### Streamline all module objects

All module objects need to have:

- a regular/sync version (what it is now)
- an async version
- a shared state version that works with Share() instances

How? we wrap each object and function in a class that does this:

```python
from suitkaise.timing import Timer

# regular version
timer = Timer()

# async version
async_timer = Timer.asynced()

# shared state version (users don't see this)
shared_timer = Timer.shared()
```

```python
class Timer:


    class regular:

    class asynced:

    class shared:
```

```python
from suitkaise.timing import Timer
from suitkaise.processing import Share

share = Share()

share.timer = Timer() # actually a Timer.shared() instance
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
