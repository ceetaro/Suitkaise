/*

synced from suitkaise-docs/cucumber/quick-start.md

*/

rows = 2
columns = 1

# 1.1

title = "Quick Start: `<suitkaise-api>cucumber</suitkaise-api>`"

# 1.2

text = "
```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Serialize and deserialize

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>

# <suitkaise-api>serialize</suitkaise-api> any object to bytes
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(my_object)

# <suitkaise-api>deserialize</suitkaise-api> back
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

# classes defined in __main__
class MyClass:
    def __init__(self):
        self.value = 42

data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(MyClass())
restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
print(restored.value)  # 42
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

For connections that require passwords:

```python
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>(restored, **{
    "psycopg2.Connection": {"*": "my_password"}
})
```

`Reconnectors` that don't require authentication will lazily reconnect on first access.

## Debug mode

When something goes wrong:

```python
# see where serialization failed
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj, debug=True)

# see the full serialization path in real-time
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj, verbose=True)
```

## Inspect the intermediate representation

```python
ir = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize_ir</suitkaise-api>(my_object)
print(ir)  # dict/list structure showing how <suitkaise-api>cucumber</suitkaise-api> sees your object
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
