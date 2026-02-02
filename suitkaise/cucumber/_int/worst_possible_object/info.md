# WorstPossibleObject — Complete Guide

The `WorstPossibleObject` is the **ultimate stress test** for cucumber’s serialization engine.  
If cucumber can round‑trip this object with 100% verification passing, it can handle real‑world data.

## Quick Start

```python
from suitkaise.cucumber._int.worst_possible_object import WorstPossibleObject
from suitkaise import cucumber

# Create, serialize, deserialize
original = WorstPossibleObject()
serialized = cucumber.serialize(original)
restored = cucumber.deserialize(serialized)

# Verify 100% reconstruction
passed, failures = original.verify(restored)

if passed:
    print("✅ PERFECT!")
else:
    print(f"❌ {len(failures)} failures")
    for failure in failures[:20]:
        print(f"  - {failure}")

original.cleanup()
restored.cleanup()
```

## What Makes It "Worst"

### Breadth (27+ complex types)
- Functions (regular, lambda, partial, bound methods, closures)
- Threading primitives (Lock, RLock, Event, Semaphore, Barrier, Condition)
- Queues (Queue, LifoQueue, PriorityQueue — empty/full/partial)
- Loggers (multiple handlers/formatters/levels)
- File handles (text/binary, StringIO/BytesIO, mid‑file positions)
- SQLite (connections, cursors, complex schemas)
- Regex patterns (flags, groups, and actual matches)
- Generators + iterators (mid‑execution/exhausted)
- Weak references
- Memory maps, context vars, thread‑locals, and more

### Depth + Chaos
- 4 levels of nested classes
- Randomly generated nested collections
- Multiple circular and cross‑reference patterns
- Edge cases: full queues, deeply acquired locks, exhausted iterators, etc.

## Verification System (80+ checks)

`verify(other)` validates:
- Primitive values
- Complex object state (locks, queues, files, loggers, regex)
- SQLite data integrity
- Circular reference identity
- Functional correctness (functions really compute)

```python
passed, failures = original.verify(restored)
```

### Typical Failure Output
```
❌ VERIFICATION FAILED
  12 checks failed

[LOCKS]
  • lock_acquired_locked: expected True, got False
[SQLITE]
  • sqlite_table_count: expected 2, got 0
```

## Debugging Toolkit

Use these options to isolate failures:
- `verbose=True` (see initialization order)
- `debug_log_file="path.log"` (save full logs)
- `skip_types={...}` (test categories in isolation)

```python
obj = WorstPossibleObject(
    verbose=True,
    skip_types={"locks", "queues", "sqlite"}
)
```

### Introspection helpers
- `get_initialization_report()`
- `list_all_attributes()`
- `inspect_object("lock_acquired")`
- `test_serialization_by_type("locks")`
- `generate_debug_report(test_serialization=True)`

## Scripts in This Directory

- `simple_verification_example.py` — shortest demo
- `test_full_cycle.py` — end‑confirm: serialize → deserialize → verify
- `test_worst_obj.py` — object creation + sanity checks
- `test_worst_verification.py` — verification system deep dive
- `test_debugging_features.py` — debugging tools demo

## Notes / Limitations

- Long‑running processes and OS handles can’t be meaningfully re‑attached.
- Some values (paths, IDs) may differ across machines.
- This suite aims to be **comprehensive**, not minimal.

If cucumber handles this, it handles anything.
