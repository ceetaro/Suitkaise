# Verification System - Complete Guide

## Quick Answer

**Yes!** After serializing and deserializing the WorstPossibleObject, you can run:

```python
passed, failures = original.verify(restored)
```

This tells you **exactly** what's intact and what's missing with detailed failure messages.

## What You Get

### ✅ 80+ Automated Checks

The verification system automatically checks:
- **Primitive values**: All ints, floats, strings, bytes, etc.
- **Complex object states**: Lock locked/unlocked, Event set/unset, Queue sizes
- **File states**: Positions, contents, modes
- **Function correctness**: Actually calls functions to verify they compute correctly
- **Regex functionality**: Tests patterns actually match
- **SQLite integrity**: Checks row counts and data
- **Circular references**: Verifies identity is preserved (A → B → A points to same objects)
- **Weak references**: Checks objects are still alive
- **And more...**

### ✅ Clear Pass/Fail Output

**When it works:**
```
✅ PERFECT RECONSTRUCTION!
   All verification checks passed.
   Total checks: 87
```

**When it fails:**
```
❌ VERIFICATION FAILED
   12 checks failed

  [LOCKS] - 3 failures:
    • lock_acquired_locked: expected True, got False
    • rlock_acquired_locked: expected True, got False
    • semaphore_value: expected 3, got 5

  [FUNCTIONS] - 2 failures:
    • function: error calling - 'NoneType' object is not callable
    • partial_function: does not compute correctly
```

## How to Use

### Basic Usage

```python
from worst_possible_obj import WorstPossibleObject
import cerial

# 1. Create
original = WorstPossibleObject()

# 2. Serialize
serialized = cerial.serialize(original)

# 3. Deserialize
restored = cerial.deserialize(serialized)

# 4. Verify (THIS IS THE KEY!)
passed, failures = original.verify(restored)

if passed:
    print("✅ Perfect!")
else:
    print(f"❌ {len(failures)} failures:")
    for failure in failures:
        print(f"  - {failure}")

# 5. Cleanup
original.cleanup()
restored.cleanup()
```

### With Debugging

```python
# Create with verbose logging
original = WorstPossibleObject(
    verbose=True,
    debug_log_file='verification_test.log'
)

# Serialize
serialized = cerial.serialize(original)

# Deserialize
restored = cerial.deserialize(serialized)

# Verify with detailed output
passed, failures = original.verify(restored)

if not passed:
    # Show what failed
    print(f"{len(failures)} failures found:")
    for failure in failures:
        print(f"  {failure}")
    
    # Generate debug report
    print(original.generate_debug_report())
```

### Testing Specific Categories

```python
# Test ONLY locks (skip everything else)
obj = WorstPossibleObject(
    skip_types={'functions', 'queues', 'files', ...}
)

serialized = cerial.serialize(obj)
restored = cerial.deserialize(serialized)

passed, failures = obj.verify(restored)
# Now any failures are ONLY from lock objects
```

## Example Scripts

### 1. `simple_verification_example.py`
The absolute simplest example - just 30 lines showing the basic flow.

```bash
python simple_verification_example.py
```

### 2. `test_full_cycle.py`
Complete test with detailed output and multiple modes.

```bash
# Verbose mode (full details)
python test_full_cycle.py verbose

# Quiet mode (just results)
python test_full_cycle.py quiet

# Selective mode (test categories one by one)
python test_full_cycle.py selective
```

### 3. `test_verification.py` (from earlier)
Shows verification working on two identical objects.

```bash
python test_verification.py
```

## What Gets Verified

### Category 1: Primitives (23 checks)
```
int_value: 42 == 42 ✓
float_value: 3.14159 == 3.14159 ✓
str_value: "test string" == "test string" ✓
bytes_value: b"raw bytes" == b"raw bytes" ✓
complex_value: (2+3j) == (2+3j) ✓
...
```

### Category 2: Collections (15 checks)
```
tuple_value: (1, 2, 3) == (1, 2, 3) ✓
list_value: [1, 2, 3, 4, 5] == [1, 2, 3, 4, 5] ✓
dict_value: {"key": "val"} == {"key": "val"} ✓
set_value: {1, 2, 3} == {1, 2, 3} ✓
...
```

### Category 3: Threading Objects (10 checks)
```
lock_acquired_locked: True == True ✓
event_set_is_set: True == True ✓
semaphore_value: 3 == 3 ✓
thread_local_value: "data" == "data" ✓
...
```

### Category 4: Queues (4 checks)
```
queue_size: 3 == 3 ✓
lifo_queue_size: 2 == 2 ✓
priority_queue_size: 2 == 2 ✓
...
```

### Category 5: Files (8 checks)
```
temp_file_position: 0 == 0 ✓
string_io_value: "content" == "content" ✓
bytes_io_value: b"binary" == b"binary" ✓
...
```

### Category 6: Functions (6 checks)
```
function_callable: True == True ✓
function(5, 10): 15 == 15 ✓  # Actually calls it!
lambda_function(10): 20 == 20 ✓
partial_function(y=5): 15 == 15 ✓
...
```

### Category 7: Regex (4 checks)
```
regex_pattern_pattern: r'\d+\.\d+' == r'\d+\.\d+' ✓
regex_pattern_flags: 10 == 10 ✓
regex_pattern.search("3.14"): Match found ✓
...
```

### Category 8: SQLite (3 checks)
```
sqlite_table_count: 2 rows == 2 rows ✓
sqlite_complex_users_count: 2 rows == 2 rows ✓
sqlite_complex_posts_count: 3 rows == 3 rows ✓
```

### Category 9: Loggers (3 checks)
```
logger_name: "test_logger_123" == "test_logger_123" ✓
logger_level: 10 (DEBUG) == 10 (DEBUG) ✓
logger_handlers_count: 2 == 2 ✓
```

### Category 10: Circular References (4 checks)
```
circular_dict_is_circular: dict["self"] is dict ✓
circular_list_is_circular: list[3] is list ✓
ref_a_points_to_b: a["b"] is b ✓
ref_b_points_to_a: b["a"] is a ✓
```

## Debugging Workflow

When verification fails:

### Step 1: See What Failed
```python
passed, failures = original.verify(restored)

if not passed:
    print(f"{len(failures)} failures:")
    for failure in failures[:10]:  # First 10
        print(f"  {failure}")
```

### Step 2: Isolate the Category
```python
# If [LOCKS] has most failures, test only locks
obj = WorstPossibleObject(
    skip_types={'functions', 'queues', 'files', 'regex', 'sqlite', ...}
)
```

### Step 3: Inspect Failing Objects
```python
# If lock_acquired fails:
print(obj.inspect_object('lock_acquired'))
print(restored.inspect_object('lock_acquired'))
# Compare them
```

### Step 4: Check Base Pickle
```python
# Can base pickle handle it?
results = obj.test_serialization_by_type('locks')
for name, (success, msg) in results.items():
    print(f"{name}: {msg}")
```

### Step 5: Fix Handler
Based on the failures, fix the cerial handler for that type.

### Step 6: Test Again
Run verification again until all pass!

## Files in This Directory

### Documentation
- **`README_VERIFICATION.md`** (this file) - Complete verification guide
- **`VERIFICATION_EXAMPLE.md`** - Detailed examples with sample output
- **`DEBUGGING_GUIDE.md`** - How to use debugging features
- **`WORST_POSSIBLE_OBJECT_SPEC.md`** - Full specification
- **`README_WORST_OBJECT.md`** - Complete object guide

### Implementation
- **`worst_possible_obj.py`** - The WorstPossibleObject class
- **`test_worst_obj.py`** - Tests object creation (without cerial)
- **`test_worst_verification.py`** - Tests verification system

### Testing with Cerial
- **`simple_verification_example.py`** - Simplest example (30 lines)
- **`test_full_cycle.py`** - Complete test with multiple modes
- **`test_debugging_features.py`** - Demonstrates debugging tools

## Key Points

✅ **Automatic**: No manual checking needed - `verify()` does it all

✅ **Comprehensive**: 80+ checks covering every object type

✅ **Detailed**: Exact failure messages showing what's wrong

✅ **Functional**: Actually tests that functions compute correctly, regex matches, etc.

✅ **Identity-aware**: Verifies circular references point to same objects

✅ **Debuggable**: Integration with debugging tools for isolation

✅ **Systematic**: Makes testing cerial precise instead of guesswork

## Summary

**Question:** "After serializing and deserializing, can we verify the object is fully intact?"

**Answer:** **YES!**

```python
passed, failures = original.verify(restored)

if passed:
    # 100% perfect reconstruction
    # Every single attribute matches
    # All functions work
    # All circular refs intact
    # Everything is perfect!
else:
    # Detailed list of exactly what's wrong
    # Categorized by type (locks, functions, etc.)
    # With suggested debugging steps
```

**That's the entire verification system in 3 lines of code!**

