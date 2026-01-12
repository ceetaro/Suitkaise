# Verification System - Complete Example

## How It Works

After serialization and deserialization, the `verify()` method tells you **exactly** what's intact and what's missing.

## Simple Example

```python
from worst_possible_obj import WorstPossibleObject
import cerial

# Step 1: Create original object
original = WorstPossibleObject()

# Step 2: Serialize
serialized_bytes = cerial.serialize(original)

# Step 3: Deserialize
restored = cerial.deserialize(serialized_bytes)

# Step 4: Verify reconstruction
passed, failures = original.verify(restored)

if passed:
    print("✅ PERFECT! Everything reconstructed correctly!")
else:
    print(f"❌ FAILED: {len(failures)} problems found:")
    for failure in failures:
        print(f"  - {failure}")

# Step 5: Cleanup
original.cleanup()
restored.cleanup()
```

## What Gets Verified

The `verify()` method checks **80+ attributes** across all categories:

### 1. Primitive Values
```python
# Checks exact value equality
'int_value': expected 42, got 42 ✓
'str_value': expected 'test string', got 'test string' ✓
'float_value': expected 3.14159, got 3.14159 ✓
```

### 2. Complex Object States
```python
# Checks that locks maintain their locked/unlocked state
'lock_acquired_locked': expected True, got True ✓

# Checks that events maintain their set/unset state
'event_set_is_set': expected True, got True ✓

# Checks queue sizes are preserved
'queue_size': expected 3, got 3 ✓
```

### 3. File States
```python
# Checks file positions
'temp_file_position': expected 0, got 0 ✓

# Checks file contents
'string_io_value': expected 'StringIO content here', got 'StringIO content here' ✓
```

### 4. Function Correctness
```python
# Checks functions are callable
'function_callable': expected True, got True ✓

# Actually calls functions to verify they compute correctly
function(5, 10): expected 15, got 15 ✓
lambda_function(10): expected 20, got 20 ✓
partial_function(y=5): expected 15, got 15 ✓
```

### 5. Regex Functionality
```python
# Checks regex patterns
'regex_pattern_pattern': expected r'\d+\.\d+', got r'\d+\.\d+' ✓

# Tests regex actually matches
regex_pattern.search("version 2.71"): match found ✓
```

### 6. SQLite Data Integrity
```python
# Checks database contents
'sqlite_table_count': expected 2 rows, got 2 rows ✓
'sqlite_complex_users_count': expected 2 rows, got 2 rows ✓
'sqlite_complex_posts_count': expected 3 rows, got 3 rows ✓
```

### 7. Circular Reference Identity
```python
# Checks circular references point to same object
'circular_dict_is_circular': circular_dict["self"] is circular_dict ✓

# Checks cross-references are maintained
'ref_a_points_to_b': ref_a["points_to_b"] is ref_b ✓
'ref_b_points_to_a': ref_b["points_to_a"] is ref_a ✓
```

### 8. Weak References
```python
# Checks weak references are alive
'weak_reference_alive': expected True, got True ✓
```

## Example Output

### When Everything Works

```
======================================================================
VERIFICATION RESULTS
======================================================================

✅  PERFECT RECONSTRUCTION!
   All verification checks passed.
   Total checks: 87

🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 

   CERIAL WORKS PERFECTLY!
   Can serialize the worst possible object!

🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 🎉 
```

### When Something Fails

```
======================================================================
VERIFICATION RESULTS
======================================================================

❌  VERIFICATION FAILED
   12 checks failed

  [LOCKS] - 3 failures:
    • lock_acquired_locked: expected True, got False
    • rlock_acquired_locked: expected True, got False
    • semaphore_value: expected 3, got 5

  [FUNCTIONS] - 2 failures:
    • function: error calling - 'NoneType' object is not callable
    • partial_function: does not compute correctly

  [CIRCULAR] - 2 failures:
    • circular_dict: multiple references don't point to same object
    • circular_nested: nested circular reference broken

  [SQLITE] - 1 failure:
    • sqlite_table_count: expected 2, got 0

  [FILES] - 4 failures:
    • temp_file_position: expected 0, got None
    • string_io_value: expected 'StringIO content', got ''
    • bytes_io_value: error during verification - 'NoneType' object has no attribute 'getvalue'
    • temp_file_mid_position_pos: expected 14, got None
```

## What Each Failure Means

### "expected X, got Y"
The value changed during serialization/deserialization. The handler isn't preserving state correctly.

### "error calling - NoneType"
The object wasn't reconstructed at all - it's None instead of the expected object.

### "does not compute correctly"
The function was reconstructed but doesn't work right - maybe closure values lost.

### "multiple references don't point to same object"
Circular reference identity was broken - each reference created a new copy instead of pointing to same object.

### "error during verification - AttributeError"
The object structure is wrong - missing attributes or wrong type entirely.

## Debugging Failed Verifications

### Strategy 1: Check the Failure Category

```python
# If [LOCKS] failures, test locks in isolation
obj = WorstPossibleObject(
    skip_types={'functions', 'queues', 'files', ...}  # Everything except locks
)
serialized = cerial.serialize(obj)
restored = cerial.deserialize(serialized)
passed, failures = obj.verify(restored)
# Now failures are ONLY from lock objects
```

### Strategy 2: Inspect the Failing Object

```python
# If "lock_acquired_locked" fails:
print(obj.inspect_object('lock_acquired'))

# Shows:
# Type: <class 'threading.Lock'>
# Locked: True
# ...

# Compare to restored:
print(restored.inspect_object('lock_acquired'))
```

### Strategy 3: Check Base Pickle

```python
# See if base pickle can handle it
results = obj.test_serialization_by_type('locks')
for name, (success, msg) in results.items():
    print(f"{name}: {'✓' if success else '✗'} {msg}")

# If base pickle fails too, you need a custom handler
# If base pickle works but cerial fails, check your handler dispatch
```

## Advanced: Verification Checksums

The object pre-computes 80+ checksums during initialization:

```python
obj = WorstPossibleObject()

# Automatically computed:
obj._verification_checksums = {
    'int_value': 42,
    'float_value': 3.14159,
    'lock_acquired_locked': True,
    'queue_size': 3,
    'logger_level': 10,
    'temp_file_position': 0,
    'regex_pattern_pattern': r'\d+\.\d+',
    'sqlite_table_count': 2,
    'circular_dict_is_circular': True,
    'function_callable': True,
    # ... 70+ more
}

# verify() compares all of these
passed, failures = obj.verify(other_obj)
```

## Complete Test Script

The `test_full_cycle.py` script automates everything:

```bash
# Verbose mode (shows everything)
python test_full_cycle.py verbose

# Quiet mode (just results)
python test_full_cycle.py quiet

# Selective mode (test categories individually)
python test_full_cycle.py selective
```

## Summary

✅ **What you get:**
- Automatic verification of 80+ attributes
- Detailed failure messages showing exactly what's wrong
- Categorized failures (locks, functions, files, etc.)
- Functional testing (functions actually compute correctly)
- Identity testing (circular references preserved)
- Data integrity testing (SQLite contents intact)

✅ **How to use:**
1. Create object
2. Serialize with cerial
3. Deserialize with cerial
4. Run `original.verify(restored)`
5. Get detailed pass/fail report

✅ **When it fails:**
- See exactly which attributes failed
- Use `skip_types` to isolate the problem
- Use `inspect_object` to understand the objects
- Use `test_serialization_by_type` to check base pickle
- Fix the handler for that specific type
- Iterate until all pass!

The verification system makes testing cerial **systematic and precise** instead of guesswork.

