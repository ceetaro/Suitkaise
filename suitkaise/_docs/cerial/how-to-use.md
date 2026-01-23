# How to use `cerial`

`cerial` is a serialization engine that handles complex Python objects that `pickle`, `cloudpickle`, and `dill` cannot.

Meant for internal, cross-process communication, not for external or cross-language serialization.

It contains a few core API functions.

- `cerial.serialize(obj)` - serialize an object to bytes
- `cerial.deserialize(bytes)` - deserialize bytes back to an object
- `cerial.serialize_ir(obj)` - build the intermediate representation (IR)
- `cerial.to_json(obj)` - serialize to IR and return JSON text

```python
from suitkaise import cerial

obj = MyClass()

bytes = cerial.serialize(obj)

my_class = cerial.deserialize(bytes)
```

## IR + JSON output

If you want to inspect the IR or emit JSON for debugging/logging, use the IR helpers.

```python
from suitkaise import cerial

obj = MyClass()

# get a python IR
ir = cerial.serialize_ir(obj)

# 
json_text = cerial.to_json(obj)
```

## Custom serialization and deserialization

Sometimes, `cerial` might not be able to serialize/deserialize an object correctly.

If this happens, you can override the default behavior.

Use `__serialize__` and `__deserialize__` methods in your classes to override the default behavior.

In order for `__serialize__` to work, data must be reduced down to a `dict` with only native `pickle` types. Do not convert to bytes, `cerial` will do that for you.

`__deserialize__` needs to take this representation and reconstruct the object.

```python
from suitkaise import cerial

class MyClass:

    def __serialize__(self):
        return {"custom": "state"}
    
    @classmethod
    def __deserialize__(cls, state):
        obj = cls.__new__(cls)
        obj.custom = state["custom"]
        # custom reconstruction logic...
        return obj
```

## Debugging

The `serialize` and `deserialize` functions have 2 optional params.

- `debug` - when True, provides detailed error messages showing exactly where serialization/deserialization failed, including path trails
- `verbose` - when True, prints color-coded progress as it walks through nested structures

```python
data = cerial.serialize(obj, debug=True, verbose=True)

obj = cerial.deserialize(data, debug=True, verbose=True)
```

### `verbose` output

When `verbose=True`, cerial prints the path it's taking through your object, color-coded by depth:

```
  [1] MyService (red)
    [2] MyService → config (orange)
      [3] MyService → config → dict (yellow)
        [4] ... → config → dict → database (green)
        [4] ... → config → dict → api_keys (green)
    [2] MyService → lock (orange)
    [2] MyService → logger (orange)
```

This helps you see exactly which attributes are being serialized.

### `debug` error example

When something goes wrong and `debug=True`, cerial shows you where it happened:

```
======================================================================
DESERIALIZATION ERROR
======================================================================

Error: AttributeError: type object 'MyClass' has no attribute 'from_state'

Path: MyService → config → handler

Type: custom_object
Handler: CustomObjectHandler

IR Data: {'__cerial_type__': 'custom_object', '__module__': 'myapp.handlers', ...}
======================================================================
```

The path tells you exactly where in your nested object the failure occurred.

## Printing a serialized nested `dict` for a complex object

To see what cerial's intermediate representation looks like, serialize the object with `cerial` and deserialize it with `pickle`.

This is useful for understanding how cerial transforms your objects.

```python
from suitkaise import cerial
import pickle

class GameState:
    def __init__(self):
        self.player = "Gurphy"
        self.score = 100
        self.items = ["sword", "shield"]

obj = GameState()

# serialize with cerial
data = cerial.serialize(obj)

# deserialize with pickle to see the intermediate representation
ir = pickle.loads(data)
print(ir)
```

Output (simplified):

```python
{
    '__cerial_type__': 'class_instance',
    '__handler__': 'ClassInstanceHandler',
    '__object_id__': 4371208656,
    'state': {
        '__cerial_type__': 'dict',
        'items': [
            ('module', '__main__'),
            ('qualname', 'GameState'),
            ('strategy', 'dict'),
            ('instance_dict', {
                '__cerial_type__': 'dict',
                'items': [
                    ('player', 'Gurphy'),
                    ('score', 100),
                    ('items', {
                        '__cerial_type__': 'list',
                        'items': ['sword', 'shield']
                    })
                ]
            })
        ]
    }
}
```

The representation includes:
- `__cerial_type__` - the type of object (class_instance, dict, list, lock, logger, etc.)
- `__handler__` - which handler serialized/deserializes this object
- `__object_id__` - unique ID for handling circular references
- `state` or `items` - the actual data

For objects with locks, loggers, or other unpicklables, you'll see how cerial represents them in a pickle-safe format.

Simple class instances and functions may look slightly different, as they are not subjected to the entire process.

---

## `Reconnectors`

When `cerial` serializes objects, some resources cannot be directly pickled.
- Database connections (sockets to remote servers)
- Network sockets
- File handles and pipes
- Threads
- Compiled regex matches

Instead of giving you nothing, `cerial` replaces these with `Reconnector` objects.

Use `reconnect_all()` to reconnect all `Reconnector` objects in a structure.

### Using `reconnect_all()`

```python
from suitkaise import cerial

data = cerial.serialize(my_object)
restored = cerial.deserialize(data)

# reconnect all Reconnectors with credentials
restored = cerial.reconnect_all(restored, **{
    "psycopg2.Connection": {
        "*": {
            "host": "localhost",
            "user": "myuser",
            "password": "secret",
            "database": "mydb",
        },
    },
    "redis.Redis": {
        "*": {"password": "redis_pass"},
    },
})
```

### kwargs structure

```python
{
    "TypeKey": {
        "*": {...},           # defaults for all instances of this type
        "attr_name": {...},   # specific kwargs for attr named "attr_name"
    }
}
```

- **Type keys** are `"module.ClassName"` (e.g., `"psycopg2.Connection"`, `"redis.Redis"`)
- **`"*"`** provides defaults for all instances of that type
- **Specific attr names** override/merge with defaults

### Multiple connections of same type

```python
restored = cerial.reconnect_all(restored, **{
    "psycopg2.Connection": {
        "*": {  # default for all postgres connections
            "host": "localhost",
            "user": "myuser",
            "password": "default_pass",
        },
        "analytics_db": {  # override for self.analytics_db
            "password": "analytics_pass",
        },
    },
})
```

### No kwargs needed

For resources without credentials (sockets, threads, pipes, sqlite files, regex matches), just call with no kwargs:

```python
restored = cerial.reconnect_all(restored)
```

---

JSON Output (Simplified)

```json
{
  "__cerial_type__": "class_instance",
  "__handler__": "ClassInstanceHandler",
  "__object_id__": 4371208656,
  "state": {
    "__cerial_type__": "dict",
    "items": {
      "__cerial_json__": "dict",
      "items": [
        ["module", "__main__"],
        ["qualname", "GameState"],
        ["strategy", "dict"],
        ["instance_dict", {
          "__cerial_type__": "dict",
          "items": {
            "__cerial_json__": "dict",
            "items": [
              ["player", "Gurphy"],
              ["score", 100],
              ["items", {
                "__cerial_type__": "list",
                "items": ["sword", "shield"]
              }]
            ]
          }
        }]
      ]
    }
  }
}
```
