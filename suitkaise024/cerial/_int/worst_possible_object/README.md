# WorstPossibleObject - Testing Suite

This directory contains the comprehensive testing infrastructure for cerial.

## Core Files

- **`worst_possible_obj.py`** - The WorstPossibleObject class
- **`__init__.py`** - Package initialization

## Test Scripts

- **`simple_verification_example.py`** - Simplest usage example (start here!)
- **`test_full_cycle.py`** - Complete serialization/deserialization test
- **`test_worst_obj.py`** - Tests object creation (without cerial)
- **`test_worst_verification.py`** - Tests verification system
- **`test_debugging_features.py`** - Demonstrates debugging tools

## Documentation

- **`README_WORST_OBJECT.md`** - Complete object guide (start here!)
- **`README_VERIFICATION.md`** - Verification system guide
- **`VERIFICATION_EXAMPLE.md`** - Detailed verification examples
- **`DEBUGGING_GUIDE.md`** - Debugging features guide
- **`WORST_POSSIBLE_OBJECT_SPEC.md`** - Technical specification

## Quick Start

```python
from suitkaise.cerial._int.worst_possible_object import WorstPossibleObject
import cerial

# Create, serialize, deserialize
original = WorstPossibleObject()
serialized = cerial.serialize(original)
restored = cerial.deserialize(serialized)

# Verify 100% reconstruction
passed, failures = original.verify(restored)

if passed:
    print("✅ PERFECT!")
else:
    print(f"❌ {len(failures)} failures")
    for failure in failures:
        print(f"  - {failure}")

original.cleanup()
restored.cleanup()
```

## Running Tests

```bash
# Simple example
python simple_verification_example.py

# Full test suite
python test_full_cycle.py

# Debugging features demo
python test_debugging_features.py
```

## What is WorstPossibleObject?

The ultimate stress test for cerial containing:
- **27+ complex types** (locks, queues, loggers, files, SQLite, regex, generators, etc.)
- **4 levels of nested classes**
- **Circular references and cross-references**
- **Random deeply nested collections**
- **80+ verification checks**
- **Comprehensive debugging tools**

If cerial can serialize this, it can serialize anything!

## Documentation Order

1. **`README_WORST_OBJECT.md`** - Overview and usage
2. **`WORST_POSSIBLE_OBJECT_SPEC.md`** - What makes it "worst"
3. **`README_VERIFICATION.md`** - How verification works
4. **`DEBUGGING_GUIDE.md`** - Debugging failed serialization

## Key Features

✅ **80+ automated verification checks**  
✅ **Detailed failure messages**  
✅ **Selective type testing** (skip categories to isolate issues)  
✅ **Verbose logging** (see exactly what's being serialized)  
✅ **Debug reports** (comprehensive analysis)  
✅ **Pickle compatibility testing** (compare with base pickle)  

See the documentation files for complete details!

