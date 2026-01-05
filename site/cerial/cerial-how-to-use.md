/*

how to use the cerial module. this is the default page when entered from the home page "learn more" or nav bar sidebar "cerial" link.

*/


rows = 2
columns = 1

# 1.1

title = "How to use `cerial`"

# 1.2

text = "
## Cerial contains 2 API functions:

- `cerial.serialize(obj)` - serialize an object to bytes
- `cerial.deserialize(bytes)` - deserialize bytes back to an object

Use these to serialize and deserialize objects respectively.

```python
from suitkaise import cerial

obj = MyClass()
bytes = cerial.serialize(obj)
my_class = cerial.deserialize(bytes)
```

## Custom serialization and deserialization

Sometimes, `cerial` might not be able to serialize/deserialize an object correctly.

If this happens, you can override the default behavior.

Use `__serialize__` and `__deserialize__` methods in your classes to override the default behavior.

```python
from suitkaise import cerial

class MyClass:
    def __serialize__(self):

        return {"custom": "state"}
    
    @classmethod
    def __deserialize__(cls, state):
        obj = cls.__new__(cls)

        # custom reconstruction logic...

        return obj

bytes = cerial.serialize(MyClass())
my_class = cerial.deserialize(cerial.serialize(MyClass()))

assert my_class.custom == "state"
```

## Debugging with `debug` and `verbose` modes

The `serialize` and `deserialize` functions have 2 optional params:

- `debug` - when True, provides detailed error messages showing exactly where serialization/deserialization failed, including path breadcrumbs
- `verbose` - when True, prints color-coded progress as it walks through nested structures

```python
data = cerial.serialize(obj, debug=True, verbose=True)

obj = cerial.deserialize(data, debug=True, verbose=True)
```

### `verbose` output example

When `verbose=True`, cerial prints the path it's taking through your object, color-coded by depth:

```
  [1] MyService
    [2] MyService → config
      [3] MyService → config → dict
        [4] ... → config → dict → database
        [4] ... → config → dict → api_keys
    [2] MyService → lock
    [2] MyService → logger
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

IR Data: {'__cerial_type__': 'custom_object', '__module__': 'myapp.handlers'...
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

# Serialize with cerial
data = cerial.serialize(obj)

# Deserialize with pickle to see the intermediate representation
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