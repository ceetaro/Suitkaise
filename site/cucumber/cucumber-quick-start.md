/*

synced from suitkaise-docs/cucumber/quick-start.md

*/

rows = 2
columns = 1

# 1.1

title = "`<suitkaise-api>cucumber</suitkaise-api>` quick start guide"

# 1.2

text = "
```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Serialize and deserialize

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>

# serialize any object to bytes
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(my_object)

# deserialize back
restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
```

## It works with things `pickle` can't handle

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>

# lambdas
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(lambda x: x * 2)

# closures
def make_multiplier(n):
    return lambda x: x * n

data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(make_multiplier(3))

# classes defined in __main__ — the reason this matters is pickle
# fails with __main__ classes across processes, cucumber doesn't
class Task:
    def __init__(self, n):
        self.n = n
    def compute(self):
        return self.n ** 2

data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(Task(7))
restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
print(restored.compute())  # 49 — class definition survived serialization
```

## Circular references? Handled automatically

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>

class Node:
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.children = []

root = Node("root")
child = Node("child")
root.children.append(child)
child.parent = root  # circular: child → root → child

data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(root)
restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
print(restored.children[0].parent.name)  # "root" — cycle preserved
```

## Live resources become `Reconnector` objects

Objects like database connections, sockets, and threads can't be directly transferred between processes. `<suitkaise-api>cucumber</suitkaise-api>` serializes them as `Reconnector` placeholders, then you reconnect them:

```python
import sqlite3
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>

conn = sqlite3.connect(":memory:")
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(conn)

restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
# restored is a Reconnector, not a live connection yet

<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>(restored)
# now it's a live sqlite3 connection again
```

**For connections that require passwords:**

```python
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>(restored, **{
    "psycopg2.Connection": {"*": "my_password"}
})
```

`Reconnector`s that don't require authentication will lazily reconnect on first access.

## Debug mode

**When something goes wrong:**

```python
# see where serialization failed
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj, debug=True)

# see the full serialization path in real-time
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj, verbose=True)
```

## Inspect the intermediate representation

```python
ir = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize_ir</suitkaise-api>(my_object)
print(ir)  # dict/list structure showing how cucumber sees your object
```

## Convert to JSON

```python
json_str = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>to_json</suitkaise-api>(my_object)
```

## Want to learn more?

- **Why page** — why `<suitkaise-api>cucumber</suitkaise-api>` exists and how it compares to `pickle`, `cloudpickle`, and `dill`
- **How to use** — full API reference
- **Supported types** — every type `<suitkaise-api>cucumber</suitkaise-api>` can handle
- **Performance** — benchmarks against other serializers
- **How it works** — internal architecture (IR, handlers, two-pass deserialization) (level: very advanced)
"
