/*

how the cerial module actually works.

*/


rows = 2
columns = 1

# 1.1

title = "How `cerial` actually works"

# 1.2

text = "
# How `cerial` actually works

`cerial` has no dependencies outside of the standard library.

`cerial` is a serialization engine that handles complex Python objects that `pickle`, `cloudpickle`, and `dill` cannot

---

## Overview

Cerial uses a two-phase approach.

1. **Transform** — Convert unpickleable objects into an intermediate representation (IR) using handlers for complex objects

2. **Serialize** — Use standard `pickle.dumps()` on the IR

Deserialization is the reverse.

1. **Deserialize** — Use `pickle.loads()` to get the IR

2. **Reconstruct** — Convert the IR back into the original objects using the handlers

```
Object → Handler(s) → IR (nested dicts) → pickle.dumps() → bytes

bytes → pickle.loads() → IR → Handler(s) → Object
```

---

## Intermediate Representation (IR)

The intermediate representation is a nested `dict` containing only pickle native types.

- dicts, lists, tuples, sets
- ints, strings, bools, None
- other pickle-native types (datetime, Decimal, etc.)

Complex objects get converted to dicts with special markers.

```python
{
    "__cerial_type__": "lock",           # type identifier
    "__handler__": "LockHandler",        # which handler serialized it
    "__object_id__": 140234567890,       # for circular reference tracking
    "state": {                           # actual data (handler-specific)
        "locked": False
    }
}
```

- Mirrors the original object structure
- Can nest infinitely deep
- Lets primitive types pass through untouched
- Gives complex types their own dict at each level

---

## Handlers

Handlers are responsible for serializing and deserializing specific object types.

Each handler:
- Defines a `type_name` (e.g., "lock", "logger", "class_instance")
- Implements `can_handle(obj)` to check if it handles this type
- Implements `extract_state(obj)` to extract serializable state
- Implements `reconstruct(state)` to rebuild the object

### Handler Priority

Handlers are checked in order. Specialized handlers (locks, loggers, etc.) are checked before general ones:

1. function handlers
2. `logging` handlers
3. `threading` handlers
4. `queue` handlers
5. file handlers
6. database handlers
7. network handlers
8. generator and iterator handlers
9. subprocess handlers
10. async handlers
11. context manager handlers
12. module handlers
13. class object handlers
14. class instance handler

For more info on exactly what is covered under each handler, navigate down to "What Can Cerial Handle?"

---

## Central Serializer (`Cerializer`)

Coordinates the entire process.

### Serialization Flow

1. **Reset state** — Clear circular reference tracker, depth counter, etc.
2. **Recursive serialization** — Build the IR by walking the object tree
3. **Pickle** — Call `pickle.dumps()` on the IR
4. **Return bytes**

### `_serialize_recursive()`

This is the main function that builds the intermediate representation.

1. **Check recursion depth** — Prevent stack overflow on deeply nested objects

2. **Check for circular references**
   - If we've seen this exact object before, return a reference marker
   - If not, mark it as seen and continue

3. **Check if pickle-native**
   - Primitives (int, str, None, etc.) → return as-is
   - Collections (dict, list, tuple, set) → recursively serialize contents

4. **Find handler** — Match the object to a handler

5. **Extract state** — Handler converts object to a dict/list

6. **Recursively serialize state** — The extracted state might contain more complex objects!

7. **Wrap in metadata** — Add `__cerial_type__`, `__handler__`, `__object_id__`

8. **Return** — The fully serialized structure

Step 6 is especially important in the quest to serialize any complex object. Some objects may have other complex objects inside them.

Cerial recursively processes everything until the entire representation is pickle native.

---

## Circular Reference Handling

Objects can reference each other or themselves:

```python
obj.self_ref = obj  # self-reference
obj_a.ref = obj_b   # mutual reference
obj_b.ref = obj_a
```

Cerial handles this with object ID tracking:

### During Serialization

1. Each object gets a unique ID (`id(obj)`)
2. Before serializing, check if we've seen this ID
3. If yes, return a reference marker instead of re-serializing
4. If no, add to seen set and continue

Reference markers look like:
```python
{"__cerial_ref__": 140234567890}
```

### Deserialization

Some circular structures need two passes.

**Pass 1: Create shells**
- Create empty/placeholder objects
- Store by object ID in a lookup table

**Pass 2: Fill in state**
- Now that all objects exist, populate their state
- References can be resolved because all objects are in the lookup

This handles cases like:
```python
a = SomeClass()
b = SomeClass()
a.ref = b
b.ref = a  # both need to exist before either can be fully populated
```

---

## Class Instance Handler

The most complex handler — handles all user-defined class instances.

### Extraction Strategy Hierarchy

1. **Custom methods** — `__serialize__` / `__deserialize__` (highest priority)
2. **Common patterns** — `to_dict()` / `from_dict()` 
3. **Fallback** — `__dict__` access

### Strategy 1: Custom Serialize

If a class has `__serialize__` and `__deserialize__`:

```python
class MyClass:
    def __serialize__(self):
        return {"custom": "state"}
    
    @classmethod
    def __deserialize__(cls, state):
        obj = cls.__new__(cls)
        obj.custom = state["custom"]
        return obj
```

This gives you full control over what gets serialized.

### Strategy 2: to_dict / from_dict

Common pattern in many libraries:

```python
class Config:
    def to_dict(self):
        return {"key": self.key, "value": self.value}
    
    @classmethod
    def from_dict(cls, data):
        return cls(key=data["key"], value=data["value"])
```

### Strategy 3: __dict__ Fallback

Works for most simple classes:

```python
# Extraction
state = obj.__dict__.copy()

# Reconstruction
new_obj = SomeClass.__new__(SomeClass)
new_obj.__dict__.update(state)
```

### Handling Special Cases

- **Nested classes** — Stores module and qualname for lookup
- **Classes in `__main__`** — Handled specially (pickle can't normally do this)
- **Classes with `__slots__`** — Iterates over slot names
- **Classes with both `__dict__` and `__slots__`** — Handles both

---

(start of drop down)
## What Can Cerial Handle?

### Functions
- Regular functions
- Nested functions
- Functions in `__main__`
- Lambdas
- `functools.partial` functions
- Bound methods
- `@staticmethod` and `@classmethod`
- `@property` methods

### Classes and Instances
- Dataclasses
- Enums
- Instances with `__dict__`
- Instances with `__slots__`
- Instances with both
- Nested classes
- Dynamic classes (created with `type()`)
- NamedTuples

### Threading
- `Lock` and `RLock`
- `Semaphore` and `BoundedSemaphore`
- `Barrier`
- `Condition`
- `Event`
- `threading.local`

### Queues
- `queue.Queue`, `LifoQueue`, `PriorityQueue`
- `multiprocessing.Queue`, `Event`

### File and I/O
- File handles (open files)
- Temporary files (`tempfile.NamedTemporaryFile`)
- `StringIO`
- `BytesIO`
- Memory-mapped files (`mmap`)

### Logging
- `Logger`
- `StreamHandler`, `FileHandler`
- `Formatter`

### Database
- SQLite connections and cursors

### Network
- HTTP sessions (`requests.Session`)
- Sockets

### Subprocess
- `subprocess.Popen`
- `subprocess.CompletedProcess`

### Async
- Coroutines
- Async generators
- `asyncio.Task`
- `asyncio.Future`

### Advanced Python
- Generators (with state)
- Iterators
- Regex patterns (`re.Pattern`)
- Weak references
- Code objects
- Properties and descriptors
- Context variables
- Pipes
- Shared memory
- Executors
(end of drop down)

---

## Debug and Verbose Modes

### `verbose=True`

Prints the path through your object as it serializes:

```
  [1] MyService
    [2] MyService → config
      [3] MyService → config → dict
        [4] ... → config → dict → database
```

Color-coded by depth for easy reading.

### `debug=True`

Provides detailed error messages when something fails:

```
======================================================================
SERIALIZATION ERROR
======================================================================

Error: Cannot serialize object

Path: MyService → config → handler

Type: custom_object
Handler: ClassInstanceHandler

Object repr: <MyHandler at 0x...>
======================================================================
```

The path tells you exactly where in your nested object the failure occurred.

---

## Performance Considerations

- **Primitive types** — Pass through with minimal overhead
- **Collections** — Contents are processed recursively
- **Complex objects** — Handler lookup + state extraction + recursion
- **Circular references** — Handled with O(1) lookup in seen set

Cerial is optimized for correctness over raw speed. If you need the fastest serialization for simple types, use base `pickle`. If you need to serialize complex objects that others can't handle, use cerial.

---

## Thread Safety

The serializer is designed for single-threaded use within a single serialize/deserialize call. Each call gets fresh state (seen objects, depth counter, etc.).

If you need to serialize from multiple threads, create separate calls — don't share state between them.

