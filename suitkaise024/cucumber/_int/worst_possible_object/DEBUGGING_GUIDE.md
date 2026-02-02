# WorstPossibleObject - Debugging Guide

## Overview

The `WorstPossibleObject` now includes comprehensive debugging features to help pinpoint exactly what goes wrong during cucumber serialization/deserialization testing.

## Quick Start

```python
from worst_possible_obj import WorstPossibleObject

# Create with verbose logging
obj = WorstPossibleObject(verbose=True)

# Or save logs to a file
obj = WorstPossibleObject(debug_log_file='debug.log')

# Skip certain types for isolated testing
obj = WorstPossibleObject(skip_types={'functions', 'locks'})
```

## Debugging Features

### 1. Verbose Mode

**What it does**: Prints detailed initialization progress to stdout

**When to use**: You want to see exactly what's being initialized in real-time

**Example**:
```python
obj = WorstPossibleObject(verbose=True)
```

**Output**:
```
======================================================================
INITIALIZING WORST POSSIBLE OBJECT
======================================================================

[INIT] Base pickle primitives
  ✓ none_value: NoneType
  ✓ bool_true/false: bool
  ✓ int_value/large/negative: int
  ...

[INIT] Functions
  ✓ function: function
  ✓ lambda_function: function
  ✓ partial_function: functools.partial
  ...
```

### 2. Debug Log File

**What it does**: Writes all debug output to a file instead of stdout

**When to use**: You want to keep logs for later analysis or avoid cluttering console

**Example**:
```python
obj = WorstPossibleObject(
    verbose=False,  # Don't print
    debug_log_file='worst_obj_debug.log'
)
```

### 3. Selective Type Skipping

**What it does**: Skip certain type categories to test others in isolation

**When to use**: Cucumber fails on serialization and you want to narrow down which type category is failing

**Available skip types**:
- `'primitives'` - Skip all base pickle primitives
- `'functions'` - Skip functions, lambdas, partials, bound methods
- `'loggers'` - Skip logging objects
- `'locks'` - Skip Lock, RLock, threading primitives
- `'queues'` - Skip Queue, LifoQueue, PriorityQueue
- `'events'` - Skip Event, Semaphore, etc.
- `'files'` - Skip file handles, StringIO, BytesIO
- `'regex'` - Skip regex patterns
- `'sqlite'` - Skip SQLite connections and cursors
- `'generators'` - Skip generators
- `'weakrefs'` - Skip weak references
- `'mmap'` - Skip memory-mapped files
- `'contextvars'` - Skip context variables
- `'iterators'` - Skip iterators
- `'edge_cases'` - Skip custom serialization classes
- `'circular'` - Skip circular references

**Example**:
```python
# Test ONLY functions (everything else skipped)
obj = WorstPossibleObject(
    verbose=True,
    skip_types={
        'locks', 'queues', 'events', 'files', 'regex',
        'sqlite', 'generators', 'weakrefs', 'mmap',
        'contextvars', 'iterators', 'edge_cases', 'circular'
    }
)
```

### 4. Initialization Report

**What it does**: Shows summary of what was initialized

**When to use**: You want to verify the object contains what you expect

**Example**:
```python
obj = WorstPossibleObject()
print(obj.get_initialization_report())
```

**Output**:
```
======================================================================
WORST POSSIBLE OBJECT - INITIALIZATION REPORT
======================================================================

Skipped types: None

Total verification checksums: 87

[PRIMITIVES] - 15 items:
  - none_value: NoneType
  - bool_true/false: bool
  - int_value/large/negative: int
  ...

[COMPLEX] - 42 items:
  - function: function
  - lock: Lock
  - queue (size=3): Queue
  ...
```

### 5. List All Attributes

**What it does**: Groups all attributes by their type

**When to use**: You want to see everything in the object organized by category

**Example**:
```python
obj = WorstPossibleObject()
attrs = obj.list_all_attributes()

for category, items in attrs.items():
    if items:
        print(f"{category}: {len(items)} items")
        for item in items[:3]:
            print(f"  - {item}")
```

**Output**:
```
functions: 6 items
  - function (function)
  - lambda_function (function)
  - partial_function (partial)

locks: 7 items
  - lock (Lock)
  - lock_acquired (Lock)
  - rlock (RLock)

queues: 4 items
  - queue (Queue, size=3)
  - queue_empty (Queue, size=0)
  - lifo_queue (LifoQueue, size=2)
```

### 6. Inspect Specific Attribute

**What it does**: Shows detailed information about a specific object

**When to use**: Cucumber fails on a specific object and you need to understand it better

**Example**:
```python
obj = WorstPossibleObject()
print(obj.inspect_object('lock_acquired'))
```

**Output**:
```
======================================================================
INSPECTING: lock_acquired
======================================================================
Type: <class 'threading.Lock'>
Type name: lock
Module: _thread
Locked: True
======================================================================
```

### 7. Test Pickle Compatibility by Type

**What it does**: Tests which objects can/can't be pickled using base pickle

**When to use**: You want to see which objects need cucumber handlers vs work with base pickle

**Example**:
```python
obj = WorstPossibleObject()
results = obj.test_serialization_by_type('functions')

for name, (success, msg) in results.items():
    status = "✓" if success else "✗"
    print(f"{status} {name}: {msg}")
```

**Output**:
```
✓ function: Success
✓ lambda_function: Success
✗ partial_function: cannot pickle 'functools.partial' object
✗ bound_method: cannot pickle 'builtin_function_or_method' object
```

### 8. Comprehensive Debug Report

**What it does**: Generates a full report with all debugging information

**When to use**: You want a complete overview of the object and what can/can't be pickled

**Example**:
```python
obj = WorstPossibleObject()
print(obj.generate_debug_report(test_serialization=True))
```

**Output**:
```
======================================================================
WORST POSSIBLE OBJECT - DEBUG REPORT
======================================================================

Verbose mode: False
Skipped types: None
Verification checksums: 87

[INITIALIZATION SUMMARY]
  primitives: 15 items
  complex: 42 items
  collections: 12 items
  edge_cases: 8 items
  circular_refs: 0 items

[ATTRIBUTE COUNTS BY TYPE]
  primitives: 23
  collections: 15
  functions: 6
  locks: 7
  queues: 4
  files: 5
  regex: 4
  sqlite: 2

[PICKLE TEST RESULTS]
  primitives: 23 passed, 0 failed
  collections: 15 passed, 0 failed
  functions: 2 passed, 4 failed
    Failed:
      - partial_function: cannot pickle 'functools.partial' object
      - bound_method: cannot pickle 'builtin_function_or_method' o...
  locks: 0 passed, 7 failed
    Failed:
      - lock: cannot pickle '_thread.lock' object
      - lock_acquired: cannot pickle '_thread.lock' object
      ...
  queues: 0 passed, 4 failed
    Failed:
      - queue: cannot pickle '_queue.SimpleQueue' object
      ...
```

## Debugging Workflow

### Step 1: Start with Verbose Mode

```python
obj = WorstPossibleObject(verbose=True, debug_log_file='init.log')
```

See exactly what's being created. If initialization fails, you'll know where.

### Step 2: Try Serialization

```python
import cucumber

serialized = cucumber.serialize(obj)
```

If this fails, note the error message.

### Step 3: Generate Debug Report

```python
print(obj.generate_debug_report(test_serialization=True))
```

This shows which objects base pickle can handle. If cucumber fails on something base pickle can handle, the issue is with cucumber's handler dispatch logic.

### Step 4: Isolate the Problem

If cucumber fails, skip types to narrow down the problem:

```python
# Test without locks
obj = WorstPossibleObject(skip_types={'locks'})
serialized = cucumber.serialize(obj)  # Does this work?

# Test ONLY locks
obj = WorstPossibleObject(
    skip_types={'functions', 'queues', 'events', 'files', ...}
)
serialized = cucumber.serialize(obj)  # Isolate lock serialization
```

### Step 5: Inspect Failing Objects

```python
# If lock serialization fails:
print(obj.inspect_object('lock'))
print(obj.inspect_object('lock_acquired'))
print(obj.inspect_object('rlock'))
```

Understand the object's type, state, and attributes.

### Step 6: Test Individual Objects

```python
# Test which specific lock objects fail
results = obj.test_serialization_by_type('locks')
for name, (success, msg) in results.items():
    if not success:
        print(f"Failed: {name}")
        print(f"  Error: {msg}")
        print(obj.inspect_object(name))
```

### Step 7: Fix Handler and Iterate

Once you've identified the exact object and error:
1. Fix the cucumber handler for that type
2. Test again with verbose mode
3. Repeat until all types work

## Example: Debugging Failed Serialization

```python
from worst_possible_obj import WorstPossibleObject
import cucumber

# Try full object
obj = WorstPossibleObject(verbose=True)

try:
    serialized = cucumber.serialize(obj)
    print("✓ Serialization succeeded!")
except Exception as e:
    print(f"✗ Serialization failed: {e}")
    
    # Generate report to see what might be the issue
    print(obj.generate_debug_report(test_serialization=True))
    
    # If error mentions "Lock", test without locks
    print("\nTesting without locks...")
    obj_no_locks = WorstPossibleObject(skip_types={'locks'})
    try:
        cucumber.serialize(obj_no_locks)
        print("✓ Works without locks - lock handler needs fixing!")
        
        # Inspect the lock objects
        print(obj.inspect_object('lock'))
        print(obj.inspect_object('lock_acquired'))
        
    except Exception as e2:
        print(f"✗ Still fails: {e2}")
        # Continue isolating...

obj.cleanup()
```

## Tips

1. **Start broad, then narrow**: Begin with full object, then skip types to isolate
2. **Use log files**: Save verbose output for later review
3. **Test incrementally**: Add one type category at a time
4. **Compare with pickle**: If base pickle fails too, your handler can't help
5. **Inspect before fixing**: Understand the object before writing handler code

## Summary

The debugging features let you:
- ✅ See exactly what's being initialized (verbose mode)
- ✅ Skip problematic types to isolate issues (skip_types)
- ✅ Understand what's in the object (reports, listings)
- ✅ Inspect specific objects (inspect_object)
- ✅ Compare with base pickle (test_serialization_by_type)
- ✅ Get comprehensive overviews (generate_debug_report)

This makes debugging cucumber's handlers systematic instead of guesswork!

