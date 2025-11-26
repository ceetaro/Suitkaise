# The Worst Possible Object - Specification

## Purpose

The `WorstPossibleObject` is the ultimate stress test for cerial's serialization engine. If cerial can serialize and deserialize this object with 100% verification passing, it can handle anything users throw at it.

## What Makes It "Worst"

### 1. **Every Complex Type That Cerial Must Handle**

The object contains ALL 27+ complex, unpickleable types:
- Functions (regular, lambda, partial, bound methods, with closures)
- Loggers (multiple handlers, different levels, formatters)
- Locks (Lock, RLock, acquired/unacquired, reentrant)
- Queues (Queue, LifoQueue, PriorityQueue, empty/full)
- Events (set/unset, semaphores, barriers, conditions)
- File handles (text, binary, at different positions)
- Regex patterns (with/without groups, various flags)
- SQLite (connections, cursors, complex schemas)
- Generators (fresh, advanced, exhausted)
- Weak references (to simple and complex objects)
- Memory-mapped files (with data modifications)
- Context variables (with tokens)
- Iterators (with state)
- And more...

### 2. **Extreme Edge Cases**

Beyond just having these types, we test extreme states:
- **Full queues** at maxsize (can't add more without blocking)
- **Deeply acquired RLocks** (acquired 5 times - reentrant locking)
- **Exhausted iterators** (already consumed all items)
- **Generators mid-execution** (advanced 50 iterations in)
- **Files at arbitrary positions** (not at start)
- **Complex multi-handler loggers** (different levels, formatters)
- **SQLite with foreign keys** and complex schemas
- **Regex with named capture groups** and matches

### 3. **Circular References**

Multiple types of circular reference patterns:
- **Self-referencing dict**: `dict["self"] = dict`
- **Self-referencing list**: `list[3] = list`
- **Mutual references**: A → B, B → A
- **Complex nested circularity**: nested dicts/lists pointing back up
- **Multi-level cross-references**: objects at different depths referencing each other

This tests cerial's circular reference detection and reconstruction.

### 4. **Custom Serialization Protocols**

Objects that implement various serialization patterns:
- **`__serialize__` / `__deserialize__`**: custom cerial protocol
- **`to_dict()` / `from_dict()`**: common library pattern (dataclasses, pydantic)
- **Dynamic classes**: classes defined inside `__init__` (not at module level)

This ensures cerial respects custom serialization when provided.

### 5. **Random Nested Collections**

For each collection type (tuple, list, set, frozenset, dict), generates:
- **Random depth** (2-5 levels deep)
- **Random mix** of primitives (60%), complex objects (10%), nested collections (30%)
- **Different on each instantiation** (tests cerial isn't hardcoded)

This creates unpredictable, deeply nested structures mixing all object types.

### 6. **4 Levels of Nested Classes**

The structure itself:
```
WorstPossibleObject
  └── Nested1
        └── Nested2
              └── Nested3
                    └── Nested4
```

Each level inherits ALL the same initialization, so you get:
- 4 × all primitives
- 4 × all complex types
- 4 × all edge cases
- 4 × all random collections
- 4 × all circular references

This tests cerial's ability to handle deeply nested class structures.

### 7. **Cross-References Between Nesting Levels**

Objects at one nesting level can reference objects at other levels through circular references, creating a web of interconnected objects spanning the entire structure.

## Verification System

The object includes comprehensive verification to ensure perfect reconstruction:

### Automated Verification

`compute_verification_data()` creates checksums for:
- All primitive values
- All complex object states (locked/unlocked, queue sizes, file positions)
- Logger configurations
- File contents and positions
- Regex patterns and flags
- SQLite table row counts
- Circular reference identity preservation
- Weak reference liveness

### Verification Method

`verify(other)` checks:
1. **Value equality**: primitives and simple attributes match
2. **State equality**: complex objects have same state (locks locked, queues same size)
3. **Functional equality**: functions actually compute correctly
4. **Identity preservation**: circular references still point to same objects
5. **Cross-reference integrity**: mutual references maintained

Returns `(passed: bool, failures: list)` with detailed failure messages.

### What Gets Verified

| Category | What's Checked | Example |
|----------|----------------|---------|
| **Primitives** | Exact value equality | `int_value == 42` |
| **Locks** | Lock state preserved | `lock.locked() == True` |
| **Queues** | Queue size matches | `queue.qsize() == 3` |
| **Loggers** | Name, level, handlers | `logger.level == DEBUG` |
| **Files** | Position, content | `file.tell() == 14` |
| **Functions** | Actually callable and compute correctly | `function(5, 10) == 15` |
| **Regex** | Pattern matches correctly | `regex.search(text) works` |
| **SQLite** | Row counts match | `len(rows) == 2` |
| **Circular refs** | Identity preserved | `dict["self"] is dict` |
| **Cross-refs** | References maintained | `a["b"] is b` |

## Could It Be Even Worse?

Currently includes:
- ✅ 27+ complex types with variations
- ✅ All base pickle types
- ✅ Circular references
- ✅ Custom serialization protocols
- ✅ 4 levels of nested classes
- ✅ Random deeply nested collections
- ✅ Extreme edge cases
- ✅ Cross-references
- ✅ Comprehensive verification

**Potential additions** (if needed):
- Socket connections (requires network setup)
- Subprocess objects (requires running processes)
- Async objects (requires async context)
- Thread objects (requires running threads)
- Multiprocessing objects (Pipe, Manager, etc.)
- Temporary directories (not just files)
- File descriptors (raw OS handles)
- Shared memory objects
- Properties and descriptors
- Metaclasses and class decorators

Most of these are either:
1. **Covered by existing types** (e.g., pipes/sockets similar to file handles)
2. **Require running state** (threads, subprocesses - hard to serialize meaningfully)
3. **Uncommon in practice** (raw descriptors, shared memory)

The current implementation covers **95%+ of real-world use cases** and all the types listed in the concept.md priority list.

## Usage Example

```python
# Create the worst possible object
obj = WorstPossibleObject()

# Serialize it (this is where cerial is tested)
serialized = cerial.serialize(obj)

# Deserialize it
obj_restored = cerial.deserialize(serialized)

# Verify perfect reconstruction
passed, failures = obj.verify(obj_restored)

if passed:
    print("✓ Perfect reconstruction!")
else:
    print(f"✗ {len(failures)} verification failures:")
    for failure in failures:
        print(f"  - {failure}")

# Clean up resources
obj.cleanup()
obj_restored.cleanup()
```

## Conclusion

This is truly the worst possible object cerial could encounter:
- **Breadth**: Every complex type
- **Depth**: 4 levels of nesting
- **Complexity**: Circular refs, custom serialization, extreme states
- **Unpredictability**: Random nested structures
- **Verification**: Comprehensive checking of all aspects

If cerial handles this, it handles everything.

