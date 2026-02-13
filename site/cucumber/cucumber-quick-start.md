/*

synced from suitkaise-docs/cucumber/quick-start.md

*/

rows = 2
columns = 1

# 1.1

title = "Quick Start: `cucumber`"

# 1.2

text = "
```bash
pip install suitkaise
```

## Serialize and deserialize

```python
from suitkaise import cucumber

# serialize any object to bytes
data = cucumber.serialize(my_object)

# deserialize back
restored = cucumber.deserialize(data)
```

## It works with things `pickle` can't handle

```python
from suitkaise import cucumber

# lambdas
data = cucumber.serialize(lambda x: x * 2)

# closures
def make_multiplier(n):
    return lambda x: x * n

data = cucumber.serialize(make_multiplier(3))

# classes defined in __main__
class MyClass:
    def __init__(self):
        self.value = 42

data = cucumber.serialize(MyClass())
restored = cucumber.deserialize(data)
print(restored.value)  # 42
```

## Live resources become `Reconnector` objects

Objects like database connections, sockets, and threads can't be directly transferred between processes. `cucumber` serializes them as `Reconnector` placeholders, then you reconnect them:

```python
import sqlite3
from suitkaise import cucumber

conn = sqlite3.connect(":memory:")
data = cucumber.serialize(conn)

restored = cucumber.deserialize(data)
# restored is a Reconnector, not a live connection yet

cucumber.reconnect_all(restored)
# now it's a live sqlite3 connection again
```

For connections that require passwords:

```python
cucumber.reconnect_all(restored, **{
    "psycopg2.Connection": {"*": "my_password"}
})
```

`Reconnector`s that don't require authentication will lazily reconnect on first access.

## Debug mode

When something goes wrong:

```python
# see where serialization failed
cucumber.serialize(obj, debug=True)

# see the full serialization path in real-time
cucumber.serialize(obj, verbose=True)
```

## Inspect the intermediate representation

```python
ir = cucumber.serialize_ir(my_object)
print(ir)  # dict/list structure showing how cucumber sees your object
```

## Convert to JSON

```python
json_str = cucumber.to_json(my_object)
```

## Want to learn more?

- **Why page** — why `cucumber` exists and how it compares to `pickle`, `cloudpickle`, and `dill`
- **How to use** — full API reference
- **Supported types** — every type `cucumber` can handle
- **Performance** — benchmarks against other serializers
- **How it works** — internal architecture (IR, handlers, two-pass deserialization) (level: very advanced)
"
