# cerial: serialization engine for suitkaise

## scope

focused on internal python serialization for passing data across processes. not focused on external/cross-language serialization.

## design philosophy

cerial prioritizes **capability and consistency** over raw speed:

- builds directly on base pickle (no dill or other dependencies)
- all objects go through handlers for uniform behavior and control
- slightly slower on simple objects, but still uses base pickle for them
- slightly slower on objects that are commonly handled by cloudpickle/dill/etc.
- can handle objects that are not supported by base pickle or other libraries, such as locks, loggers, file handles, database connections, etc.
- therefore, massively faster on complex objects (automatic vs hours of manual reconstruction boilerplate)

**the trade-off:**
if you need maximum speed for simple data structures, use pickle directly. 
if you need to serialize "impossible" objects (locks, loggers, files, functions in `__main__`, nested classes), use cerial.
if you don't want to think about how to serialize objects, use cerial. we handle everything for you at a small speed tradeoff.

**the guarantee:**
"if you can create it in python, cerial can serialize it."

## core problem

"can't pickle X" when using multiprocessing/distributed computing. objects with loggers, locks, file handles, database connections, etc. fail to serialize, forcing developers to:
- manually reconstruct objects in each worker (verbose, error-prone)
- use global state (bad for testing, races)
- restructure code to be stateless (sometimes impossible)
- use dill (still fails on locks/loggers/connections)

cerial solves this by serializing the instructions and metadata needed to reconstruct these objects correctly in the target process.

## how it works

cerial intelligently serializes objects by understanding their structure and current state, without requiring manual serialization code.

- uses precoded handlers meant specifically for different object types.
- these handlers dissect the object state and extract the necessary information needed to reconstruct the object correctly in the target process.
- the state object is then serialized to bytes using base pickle.
- then, on the other end, the deserializer uses the same handlers to reconstruct the object correctly in the target process.

### automatic serialization

cerial automatically handles serialization by:
1. inspecting the object's type and selecting the appropriate handler
2. extracting the object's current state (instance attributes)
3. recursively serializing nested objects
4. tracking circular references and object identities
5. preserving reconstruction instructions with the serialized data

no need to write custom serialization logic - cerial figures it out.

but if you want to, you can!

use the `__serialize__` / `__deserialize__` methods to add extra control over the serialization/deserialization process.

__serialize__: extract the object's state and return it as a dictionary.

__deserialize__: reconstruct the object from the given state, updating attributes if needed.

cerial won't update attributes like current time, attempt to gather network data, or do anything else that might change object state. it will only store the state before serialization, and then reconstruct the object using that exact state.

### optional customization

cerial tries multiple strategies for class instances (in priority order):

**1. custom `__serialize__` / `__deserialize__` methods** (highest priority)
```python
class MyCustomClass:
    def __serialize__(self):
        return {"state": self.complex_state}
    
    @classmethod
    def __deserialize__(cls, data):
        obj = cls.__new__(cls)
        obj.complex_state = data["state"]
        return obj
```

**2. `to_dict()` / `from_dict()` pattern** (common library pattern)
```python
class Point:
    def to_dict(self):
        return {"x": self.x, "y": self.y}
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
```

**3. automatic `__dict__` extraction** (fallback for any class)

cerial automatically detects and uses whichever method is available, with no configuration needed.

this is used when no other methods are available, and cerial attempts to recursively serialize the object's state and any nested objects within.

### usage

```python
# serialize any object
serialized_data = cerial.serialize(obj)

# deserialize to get exact copy
obj_copy = cerial.deserialize(serialized_data)

# works with complex objects
processor = DataProcessor()  # has loggers, locks, file handles, etc.
serialized = cerial.serialize(processor)
# ... send to worker process
processor_copy = cerial.deserialize(serialized)  # exact state restored
```

note that this will cause the object to exist in both the source and target processes. just keep this in mind!

supports serialization of (importance rating 1-100, where number = % of users who need this):
- functions (95)
- loggers (90) *
- partial functions (85)
- bound methods (80)
- file handles (75) *
- locks (70) *
- queues (65) *
- http sessions (60) *
- database connections (55) *
- event objects (50) *
- generators (45)
- regex patterns (40) *
- context managers (40)
- subprocess objects (35)
- sqlite connections (30) *
- decorators (25)
- async objects (24)
- weak references (20)
- dynamic modules (18)
- socket connections (15) *
- database cursors (15) *
- semaphores/barriers (12) *
- iterators with state (10) *
- memory-mapped files (9) *
- thread objects (8) *
- executors (7) *
- pipes (6) *
- temporary files (5) *
- manager/proxy objects (4) *
- raw file descriptors (3) *
- shared memory (3) *
- code/frame objects (2) *
- properties/descriptors (2) *
- contextvars (2) *
- threading.local (2) *
- circular reference handling (2)
- suitkaise specific objects (predicted for cerial users: 98)

## api

cerial provides a simple two-method api:

```python
cerial.serialize(obj) -> bytes
```
serialize any python object to bytes. automatically handles complex types, nested structures, and circular references.

```python
cerial.deserialize(data: bytes) -> object
```
deserialize bytes back to the original object with exact state restoration.

both methods will call optional `__serialize__` / `__deserialize__` methods if defined on custom classes, otherwise use automatic handlers.

## internals

### core architecture

cerial uses a **central manager** with specialized handlers:

**central serializer:**
- coordinates the entire serialization process
- handles recursion through nested structures
- tracks circular references via object IDs
- dispatches to appropriate handlers based on type
- wraps handler output in uniform metadata

**handlers:**
- each handler knows how to extract/reconstruct one type
- handlers extract state as simple dicts/lists (no recursion logic)
- handlers never call other handlers (clean separation)
- central serializer recursively processes the extracted state

**flow:**
```python
# Serialize
obj = ComplexObject()
serializer = CerialSerializer()

# 1. Serializer checks: is this a primitive type?
# 1a. Yes - pass through to base pickle
# 2. No - get handler for ComplexObject
# 3. Handler extracts: {"attr1": <Lock>, "attr2": 42}
# 4. Serializer recursively processes extracted state:
#    - Sees <Lock>, gets LockHandler, extracts lock state
#    - Sees 42, passes through (primitive)
# 5. Result: nested dict of primitives, ready for basic pickle
# 6. Base pickle serializes the result to bytes
# 7. Bytes are sent to the target process
# 8. Deserializer receives bytes
# 9. Deserializer uses the same handlers to reconstruct the object correctly in the target process
# 10. Result: exact copy of the original object when it was serialized into bytes
```

**benefits:**
- handlers are simple and focused
- no dependencies between handlers
- central coordination of complex logic
- easy to add new handlers
- easy to test

### what gets serialized

for class instances, cerial serializes:
- **class identity**: module name + class name (using `__qualname__` for nested classes)
- **nested class definitions**: any classes defined inside the class (serialized first, bottom-up)
- **instance state**: the object's `__dict__` with all attribute values
- **object IDs**: for tracking circular references

**class methods are NOT serialized** - they already exist in the class definition in the target process.

**function attributes ARE serialized** - these are values stored in the instance's `__dict__`, not class methods.

### extraction strategy hierarchy

for class instances, cerial tries multiple strategies in priority order:

**1. custom `__serialize__` / `__deserialize__` (highest priority)**
```python
class MyClass:
    def __serialize__(self):
        return {"custom": "state"}
    
    @classmethod
    def __deserialize__(cls, state):
        obj = cls.__new__(cls)
        # custom reconstruction logic
        return obj
```

user explicitly controls serialization. cerial calls these methods if they exist.

**2. `to_dict()` / `from_dict()` pattern**
```python
class MyClass:
    def to_dict(self):
        return {"x": self.x, "y": self.y}
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
```

common library pattern (dataclasses, pydantic, attrs). cerial automatically uses these if both methods exist.

**3. direct `__dict__` access (fallback)**
```python
# Standard approach for any class with __dict__
obj = MyClass.__new__(MyClass)
obj.__dict__ = deserialized_state
```

generic fallback that works for most classes.

**benefits:**
- works automatically with existing libraries that use to_dict/from_dict
- gives users three levels of control
- no breaking changes if libraries already have serialization logic
- falls through gracefully to __dict__ for simple classes

**example:**
```python
from dataclasses import dataclass, asdict

@dataclass
class Point:
    x: int
    y: int
    
    @classmethod
    def from_dict(cls, d):
        return cls(**d)
    
    def to_dict(self):
        return asdict(self)

# cerial automatically uses to_dict/from_dict
point = Point(10, 20)
serialized = cerial.serialize(point)
point2 = cerial.deserialize(serialized)
```

### reconstruction strategy

#### 1. bypass __init__ using __new__

never call `__init__` during deserialization because it would create new resources (new files, new loggers, new locks) that we'd have to replace. instead:

```python
# Create empty instance without calling __init__
obj = SomeClass.__new__(SomeClass)

# Directly populate attributes with deserialized state
obj.__dict__ = deserialized_state
```

this gives us exact state restoration without side effects.

#### 2. dependency-ordered class reconstruction

for objects with nested classes (classes defined inside other classes):

```python
class OuterClass:
    class NestedClass:
        def __init__(self):
            self.value = 42
```

serialization order:
1. scan for nested class definitions in the object's class
2. serialize nested class definitions first (methods, attributes, structure)
3. serialize the outer class instance
4. include nested class definitions in the serialized data

deserialization order:
1. reconstruct nested classes first using `type()` 
2. attach nested classes to the outer class
3. create the outer class instance using `__new__`
4. populate instance state

this handles arbitrary nesting depth by working bottom-up.

#### 3. type-specific handlers

each complex type has a handler that extracts reconstruction instructions:

**functions**: extract bytecode, captured closure values, globals, defaults
**loggers**: extract name, level, handlers, formatters, filters
**locks**: extract type and locked state
**file handles**: extract path (skpath-relative), mode, position, encoding
**queues**: extract type, maxsize, and drain current items
**events**: extract type and is_set state
**database connections**: extract path, schema, and data dump
**partial functions**: extract wrapped function and bound arguments
**bound methods**: extract instance reference and method name
... and more (add them all here)

handlers recursively serialize nested objects within their state.

#### 4. circular reference handling

use two-pass deserialization for circular references:

**pass 1**: create all objects as empty shells
```python
objects = {}
for obj_id, obj_data in serialized_data:
    objects[obj_id] = create_empty_instance(obj_data["__class__"])
```

**pass 2**: populate state with references to created objects
```python
for obj_id, obj_data in serialized_data:
    populate_state(objects[obj_id], obj_data["__dict__"], objects)
```

this allows `dict["self"] = dict` style circular references to work correctly.

#### 5. recursive descent

serialize nested structures (dicts, lists, tuples, sets) by recursively serializing their contents:

```python
def serialize_recursive(obj, seen=None):
    if seen is None:
        seen = {}
    
    obj_id = id(obj)
    if obj_id in seen:
        return {"__circular_ref__": obj_id}
    
    seen[obj_id] = True
    
    if isinstance(obj, dict):
        return {k: serialize_recursive(v, seen) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_recursive(item, seen) for item in obj]
    elif has_handler(obj):
        return handler.serialize(obj, seen)
    else:
        return obj  # primitive type
```

this handles arbitrarily deep nesting and complex objects within collections.

### error handling

fail hard with clear error messages:
- if an object can't be serialized, show exactly what type and where in the nesting structure
- if a file/resource doesn't exist during deserialization, error with clear instructions
- no silent fallbacks or degraded reconstruction

### thread safety

serialization should be atomic - the object shouldn't change while being serialized. handlers should acquire locks during serialization to ensure consistent snapshots of state.

### integration with suitkaise

cerial deeply integrates with other suitkaise modules:
- uses **skpath** for path resolution (relative to project root, works across machines as long as project root is the same)
- provides handlers for all other objects in other suitkaise modules

## validation: the worst possible object

cerial includes a comprehensive test object (`WorstPossibleObject`) that contains every difficult-to-serialize type in a nested structure:

the worst possible object contains every object type that cerial can handle in a class nested within another class.

TODO

1. ensure that the object has 3+ levels of nested classes
2. has nested objects/collections
3. has checks to ensure that object still functions correctly after serialization/deserialization

**the goal**: serialize and deserialize this object with 100% field verification passing. the object should work correctly and contain the same data state as before serialization.

if cerial can handle the worst possible object, it can handle anything users throw at it.

this serves as both a test suite and a proof of concept that demonstrates cerial's capabilities beyond what any other serialization library can do.

## serialization flow

**step-by-step process:**

1. get type of object
2. if type is in base pickle's supported types, serialize using base pickle directly
3. if type is not in base pickle, get handler for type
4. handler dissects object into state (made of base pickle types) and reconstruction instructions
5. return state + instructions wrapped in metadata for base pickle to serialize

**base pickle natively supports (cerial uses these directly):**

**primitives:**
- None
- True, False (booleans)
- int (integers, including arbitrarily large ones)
- float (floating-point numbers)
- complex (complex numbers)
- str (strings)
- bytes (byte strings)
- bytearray (mutable byte arrays)

**collections:**
- tuple
- list
- set
- frozenset
- dict
- range objects
- slice objects

**special singletons:**
- type (class objects at module level)
- Ellipsis (the ... object)
- NotImplemented

**everything else goes through handlers:**
- functions (all types)
- classes (all types, including nested)
- class instances (all types)
- locks, files, loggers, queues, events, etc.

this ensures uniform behavior and complete control over serialization/deserialization.

## state representation

cerial represents all object state as **nested dicts** - this creates a serialization intermediate representation (IR) that base pickle can serialize to bytes.

**pattern for every complex object:**
```python
{
    "__cerial_type__": "<type_name>",
    "__handler__": "<handler_name>",
    "__object_id__": <id>,
    "state": {
        # handler-extracted state (all pickle-native or recursively serialized)
    }
}
```

**example: WorstPossibleObject state structure:**
```python
{
    # metadata
    "__cerial_type__": "class_instance",
    "__module__": "suitkaise.cerial._int.worst_possible_obj",
    "__qualname__": "WorstPossibleObject",
    "__object_id__": 140235678901234,
    
    # nested class definitions (if any)
    "__nested_classes__": {
        "WorstPossibleObject.NestedTestClass": {
            # class definition data
        }
    },
    
    # instance state - recursively serialized
    "__dict__": {
        "simple_int": 42,  # pickle-native, pass through
        "simple_str": "test string",  # pickle-native
        
        "lock": {  # complex object - handler serialized
            "__cerial_type__": "lock",
            "__handler__": "threading_lock",
            "__object_id__": 140235678902345,
            "state": {
                "type": "Lock",
                "locked": True
            }
        },
        
        "logger": {  # complex object - handler serialized
            "__cerial_type__": "logger",
            "__handler__": "logging_logger",
            "__object_id__": 140235678903456,
            "state": {
                "name": "__main__",
                "level": 10,
                "handlers": [
                    {
                        "__cerial_type__": "stream_handler",
                        "state": {...}
                    }
                ]
            }
        },
        
        "nested_level_1": {  # dict with complex objects inside
            "logger": {
                "__cerial_type__": "logger",
                ...
            },
            "lock": {
                "__cerial_type__": "lock",
                ...
            },
            "list": [1, 2, 3]  # pickle-native
        },
        
        "circular_dict": {  # circular reference
            "__cerial_type__": "dict",
            "__object_id__": 140235678904567,
            "name": "circular",
            "self_ref": {
                "__cerial_ref__": 140235678904567  # reference by ID
            }
        }
    }
}
```

**why nested dicts work perfectly:**
1. **pickle-native** - entire structure is made of dicts, lists, strings, ints = base pickle can serialize it
2. **inspectable** - can print/debug the structure easily
3. **natural mapping** - dict structure mirrors object structure
4. **recursive by nature** - dicts contain dicts infinitely deep
5. **handles all cases** - primitives pass through, complex objects get their own dict with metadata
6. **human-readable** - could even output as JSON for debugging

**the pattern:**
- nested dicts all the way down
- base pickle types as the leaves
- object IDs enable circular reference tracking
- uniform structure for all complex objects