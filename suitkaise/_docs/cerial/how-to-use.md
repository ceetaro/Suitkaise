# cerial: How to Use

This guide covers every public function in the `cerial` API and explains typical usage patterns.

Import options:

```python
from suitkaise import cerial
# or
from suitkaise.cerial import serialize, deserialize
```

## `serialize(obj, debug=False, verbose=False) -> bytes`

Serializes any Python object to bytes using cerial's IR.

```python
data = cerial.serialize(obj)
```

### Parameters

- `obj`: Any Python object.
- `debug`: Enables deep error context and path reporting.
- `verbose`: Prints progress and handler selection information.

### Returns

- `bytes`: Pickled IR payload.

### When to use

- For inter-process communication.
- For disk persistence when `pickle` fails.
- For sharing complex objects (locks, queues, sockets, etc.).

## `serialize_ir(obj, debug=False, verbose=False) -> Any`

Returns the intermediate representation (IR) without converting to bytes.

```python
ir = cerial.serialize_ir(obj)
```

### When to use

- For debugging serialization.
- For inspection or custom tooling.

## `deserialize(data, debug=False, verbose=False) -> Any`

Reconstructs Python objects from bytes created by `serialize`.

```python
restored = cerial.deserialize(data)
```

### Notes

- Circular references are restored.
- Reconnectors are returned for live resources (see below).
- Use `debug=True` if you need detailed error context.

## `reconnect_all(obj, *, start_threads=False, **auth) -> Any`

Replaces any `Reconnector` objects inside `obj` with live resources by calling `reconnect()`.

```python
auth = {
    "psycopg2.Connection": {"*": "secret"},
    "redis.Redis": {"*": "redis_pass"},
}
restored = cerial.deserialize(data)
restored = cerial.reconnect_all(restored, **auth)
```

### How auth mapping works

- Keys are `"module.ClassName"` strings.
- `*` provides defaults for all attributes.
- Attribute names override the default.

```python
auth = {
    "psycopg2.Connection": {
        "*": "default_password",
        "analytics_db": "analytics_password",
    }
}
```

If no auth is provided for a reconnector, `reconnect()` is called with no arguments.

### `start_threads`

If `start_threads=True`, any `threading.Thread` objects returned by reconnectors
are started automatically.

## `ir_to_jsonable(ir) -> Any`

Converts IR into a JSON-serializable structure for inspection.

```python
jsonable = cerial.ir_to_jsonable(ir)
```

### Note

This conversion is not round-trip safe. It is intended for debugging and logging.

## `ir_to_json(ir, indent=2, sort_keys=True) -> str`

Returns a JSON string from IR.

```python
json_text = cerial.ir_to_json(ir)
```

## `to_jsonable(obj, debug=False, verbose=False) -> Any`

Convenience: `serialize_ir()` + `ir_to_jsonable()`.

```python
jsonable = cerial.to_jsonable(obj)
```

## `to_json(obj, indent=2, sort_keys=True, debug=False, verbose=False) -> str`

Convenience: `serialize_ir()` + `ir_to_json()`.

```python
json_text = cerial.to_json(obj)
```

## Exceptions

All errors are raised with detailed context:

- `SerializationError`: When `serialize` or `serialize_ir` fails.
- `DeserializationError`: When `deserialize` fails.

## Practical usage patterns

### 1) Basic round trip

```python
data = cerial.serialize(obj)
restored = cerial.deserialize(data)
```

### 2) Debugging a failure

```python
try:
    data = cerial.serialize(obj, debug=True)
except cerial.SerializationError as exc:
    print(exc)
```

### 3) Reconnecting resources

```python
restored = cerial.deserialize(data)
restored = cerial.reconnect_all(restored, **{
    "psycopg2.Connection": {"*": "secret"},
    "redis.Redis": {"*": "redis_pass"},
})
```

### 4) Inspecting IR

```python
ir = cerial.serialize_ir(obj)
print(cerial.ir_to_json(ir))
```

### 5) JSON export for debugging

```python
json_text = cerial.to_json(obj, indent=2)
```