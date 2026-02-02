/*

how to use the cucumber module. this is the default page when entered from the home page "learn more" or nav bar sidebar "cucumber" link.

*/


rows = 2
columns = 1

# 1.1

title = "How to use `cucumber`"

# 1.2

text = "
`cucumber` is a serialization engine that handles complex Python objects that `pickle`, `cloudpickle`, and `dill` cannot.

Meant for internal, cross-process communication, not for external or cross-language serialization.

It contains a few core API functions.

- `cucumber.serialize(obj)` - serialize an object to bytes
- `cucumber.deserialize(bytes)` - deserialize bytes back to an object
- `cucumber.serialize_ir(obj)` - build the intermediate representation (IR)
- `cucumber.to_json(obj)` - serialize to IR and return JSON text

```python
from suitkaise import cucumber

obj = MyClass()

bytes = cucumber.serialize(obj)

my_class = cucumber.deserialize(bytes)
```

## IR + JSON output

If you want to inspect the IR or emit JSON for debugging/logging, use the IR helpers.

```python
from suitkaise import cucumber

obj = MyClass()

ir = cucumber.serialize_ir(obj)
json_text = cucumber.to_json(obj)
```

## Custom serialization and deserialization

Sometimes, `cucumber` might not be able to serialize/deserialize an object correctly.

If this happens, you can override the default behavior.

Use `__serialize__` and `__deserialize__` methods in your classes to override the default behavior.

In order for `__serialize__` to work, data must be reduced down to a `dict` with only native `pickle` types. Do not convert to bytes, `cucumber` will do that for you.

`__deserialize__` needs to take this representation and reconstruct the object.

```python
from suitkaise import cucumber

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
data = cucumber.serialize(obj, debug=True, verbose=True)

obj = cucumber.deserialize(data, debug=True, verbose=True)
```

### `verbose` output

When `verbose=True`, cucumber prints the path it's taking through your object, color-coded by depth:

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

When something goes wrong and `debug=True`, cucumber shows you where it happened:

```
======================================================================
DESERIALIZATION ERROR
======================================================================

Error: AttributeError: type object 'MyClass' has no attribute 'from_state'

Path: MyService → config → handler

Type: custom_object
Handler: CustomObjectHandler

IR Data: {'__cucumber_type__': 'custom_object', '__module__': 'myapp.handlers', ...}
======================================================================
```

The path tells you exactly where in your nested object the failure occurred.

## Printing a serialized nested `dict` for a complex object

To see what cucumber's intermediate representation looks like, serialize the object with `cucumber` and deserialize it with `pickle`.

This is useful for understanding how cucumber transforms your objects.

```python
from suitkaise import cucumber
import pickle

class GameState:
    def __init__(self):
        self.player = "Gurphy"
        self.score = 100
        self.items = ["sword", "shield"]

obj = GameState()

# serialize with cucumber
data = cucumber.serialize(obj)

# deserialize with pickle to see the intermediate representation
ir = pickle.loads(data)
print(ir)
```

Output (simplified):

```python
{
    '__cucumber_type__': 'class_instance',
    '__handler__': 'ClassInstanceHandler',
    '__object_id__': 4371208656,
    'state': {
        '__cucumber_type__': 'dict',
        'items': [
            ('module', '__main__'),
            ('qualname', 'GameState'),
            ('strategy', 'dict'),
            ('instance_dict', {
                '__cucumber_type__': 'dict',
                'items': [
                    ('player', 'Gurphy'),
                    ('score', 100),
                    ('items', {
                        '__cucumber_type__': 'list',
                        'items': ['sword', 'shield']
                    })
                ]
            })
        ]
    }
}
```

The representation includes:
- `__cucumber_type__` - the type of object (class_instance, dict, list, lock, logger, etc.)
- `__handler__` - which handler serialized/deserializes this object
- `__object_id__` - unique ID for handling circular references
- `state` or `items` - the actual data

For objects with locks, loggers, or other unpicklables, you'll see how cucumber represents them in a pickle-safe format.

Simple class instances and functions may look slightly different, as they are not subjected to the entire process.

## JSON Output (Simplified)

```json
{
  "__cucumber_type__": "class_instance",
  "__handler__": "ClassInstanceHandler",
  "__object_id__": 4371208656,
  "state": {
    "__cucumber_type__": "dict",
    "items": {
      "__cucumber_json__": "dict",
      "items": [
        ["module", "__main__"],
        ["qualname", "GameState"],
        ["strategy", "dict"],
        ["instance_dict", {
          "__cucumber_type__": "dict",
          "items": {
            "__cucumber_json__": "dict",
            "items": [
              ["player", "Gurphy"],
              ["score", 100],
              ["items", {
                "__cucumber_type__": "list",
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
