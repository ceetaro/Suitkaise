# How to use `<suitkaise-api>cucumber</suitkaise-api>`

`<suitkaise-api>cucumber</suitkaise-api>` is a module that handles serialization and deserialization of Python objects.

Basically any object in Python will work, and it covers more types than `pickle`, `cloudpickle`, and `dill` combined.

- extensive type coverage
- superior speed for simple types compared to `cloudpickle` and `dill`
- handles all circular references
- works on class objects defined in `__main__`
- and more

To see a list of supported types, see the supported types page.

To see how `<suitkaise-api>cucumber</suitkaise-api>` stacks up against other serialization libraries, see the performance page.

`<suitkaise-api>cucumber</suitkaise-api>` is mainly meant for internal, cross-process communication, not for external or cross-language serialization.

However, you can convert the intermediate representation (IR) to JSON, and you are welcome to use that to send data to other languages using your own tools.

## Importing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>
```

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>cucumber</suitkaise-api> import <suitkaise-api>serialize</suitkaise-api>, <suitkaise-api>deserialize</suitkaise-api>, <suitkaise-api>serialize_ir</suitkaise-api>, <suitkaise-api>deserialize_ir</suitkaise-api>, <suitkaise-api>ir_to_jsonable</suitkaise-api>, <suitkaise-api>ir_to_json</suitkaise-api>, <suitkaise-api>to_jsonable</suitkaise-api>, <suitkaise-api>to_json</suitkaise-api>, <suitkaise-api>reconnect_all</suitkaise-api>
```

## `<suitkaise-api>serialize</suitkaise-api>()`

Serializes any Python object to bytes using `<suitkaise-api>cucumber</suitkaise-api>`'s intermediate representation (IR).

```python
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj)
```

Arguments
`obj`: Any Python object
- `Any`
- required

`debug`: Enables deep error context and path reporting.
- `bool = False`
- keyword only

`verbose`: Prints progress and handler selection information.
- `bool = False`
- keyword only

Returns
`bytes`: `<suitkaise-api>cucumber</suitkaise-api>` IR as bytes.

Raises
`<suitkaise-api>SerializationError</suitkaise-api>`: If serialization fails.

This is a `<suitkaise-api>SerializationError</suitkaise-api>` that appears when you try to serialize a `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api>.<suitkaise-api>Pipe</suitkaise-api>.Anchor` point.
```text
Traceback (most recent call last):
  File "my_app.py", line 42, in <module>
    payload = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj)
  File ".../<suitkaise-api>suitkaise</suitkaise-api>/<suitkaise-api>cucumber</suitkaise-api>/api.py", line 90, in <suitkaise-api>serialize</suitkaise-api>
    return _default_serializer.<suitkaise-api>serialize</suitkaise-api>(obj)
  File ".../<suitkaise-api>suitkaise</suitkaise-api>/<suitkaise-api>cucumber</suitkaise-api>/_int/serializer.py", line 113, in <suitkaise-api>serialize</suitkaise-api>
    raise <suitkaise-api>SerializationError</suitkaise-api>(message)
<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>cucumber</suitkaise-api>._int.serializer.<suitkaise-api>SerializationError</suitkaise-api>:
======================================================================
HANDLER FAILED
======================================================================
Path: Anchor
Handler: ClassInstanceHandler
Object: Anchor

The handler failed to extract state from this object.

Error: Locked pipe endpoint cannot be serialized. Keep it in the parent process.
======================================================================
```

### `debug` and `verbose`

`debug` and `verbose` are keyword only arguments.

When `debug=True`, `<suitkaise-api>cucumber</suitkaise-api>` shows you where it failed to serialize an object.
```text
======================================================================
HANDLER FAILED
======================================================================
Path: Anchor@1234567890
Handler: ClassInstanceHandler
Object: Anchor

The handler failed to extract state from this object.

Error: Locked pipe endpoint cannot be serialized. Keep it in the parent process.
======================================================================
```

When `verbose=True`, `<suitkaise-api>cucumber</suitkaise-api>` prints the path it's taking through your object, color-coded by depth.

```text
[CUCUMBER] Starting serialization of dict
  [1] dict
    [2] dict → Widget
        ↳ Handler: ClassInstanceHandler
      [3] dict → Widget → dict
        [4] dict → Widget → dict → dict
          [5] dict → Widget → dict → dict → list
          [5] dict → Widget → dict → dict → dict
        [4] dict → Widget → dict → dict
          [5] dict → Widget → dict → dict → tuple
    [2] dict → dict
      [3] dict → dict → list
    [2] dict → list
      [3] dict → list → dict
        [4] dict → list → dict → set
      [3] dict → list → tuple
[CUCUMBER] Built IR successfully, size: 1464 chars
[CUCUMBER] Serialization complete, bytes: 760
```

`[5] dict → Widget → dict → dict → tuple` colors:
- `dict` is red
- `Widget` is orange
- `dict` is yellow
- `dict` is green
- `tuple` is blue
- the next object would be purple
- the object after that would be red again

Colors will only display if your terminal supports color.

## `<suitkaise-api>deserialize</suitkaise-api>()`

Reconstructs a Python object from bytes created by `<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>`.

Will not work if the object was serialized with `pickle`, `cloudpickle`, or `dill`, as these libraries do not use `<suitkaise-api>cucumber</suitkaise-api>`'s IR.

- restores all circular references before reconstructing objects
- `Reconnector` objects are returned for certain types

```python
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj)

restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
```

Arguments
`data`: Serialized bytes from `<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>`.
- `bytes`
- required

`debug`: Enables deep error context and path reporting.
- `bool = False`
- keyword only

`verbose`: Prints progress and handler selection information.
- `bool = False`
- keyword only

Returns
`obj`: Reconstructed Python object.
- `Any`

Raises
`<suitkaise-api>DeserializationError</suitkaise-api>`: If deserialization/reconstruction fails.

This is a `<suitkaise-api>DeserializationError</suitkaise-api>` that appears when you try to deserialize an object that is missing a required key.
```text
Traceback (most recent call last):
  File "my_app.py", line 44, in <module>
    restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
  File ".../<suitkaise-api>suitkaise</suitkaise-api>/<suitkaise-api>cucumber</suitkaise-api>/api.py", line 177, in <suitkaise-api>deserialize</suitkaise-api>
    return _default_deserializer.<suitkaise-api>deserialize</suitkaise-api>(data)
  File ".../<suitkaise-api>suitkaise</suitkaise-api>/<suitkaise-api>cucumber</suitkaise-api>/_int/deserializer.py", line 88, in <suitkaise-api>deserialize</suitkaise-api>
    raise <suitkaise-api>DeserializationError</suitkaise-api>(message)
<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>cucumber</suitkaise-api>._int.deserializer.<suitkaise-api>DeserializationError</suitkaise-api>:
======================================================================
DESERIALIZATION FAILED
======================================================================
Path: Payload -> 1 -> state
Handler: ClassInstanceHandler
Object: dict

The handler failed to reconstruct this object.

Error: Missing key 'state' for class reconstruction
======================================================================
```

## `<suitkaise-api>reconnect_all</suitkaise-api>()` and `Reconnectors`

`Reconnector` objects are returned for certain types when you deserialize an object.

These objects are placeholders for certain objects that cannot be directly serialized and deserialized for various reasons.

- `DbReconnector` --> database connections
- `SocketReconnector` --> network sockets
- `PipeReconnector` --> OS pipes (not `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api>.<suitkaise-api>Pipe</suitkaise-api>` objects)
- `ThreadReconnector` --> threads
- `SubprocessReconnector` --> subprocesses
- `MatchReconnector` --> compiled regex matches

Each `Reconnector` has a `reconnect()` method that creates a new live resource, using stored metadata. If the resource requires authentication, you must provide it again. We do not store secrets in the IR for security reasons.

For more information on each `Reconnector`, see the how it works page.

`<suitkaise-api>reconnect_all</suitkaise-api>()` allows you to reconnect all `Reconnectors` in an object at once.

Arguments
`obj`: Object or container to traverse for `Reconnectors`.
- `Any`
- required

`start_threads`: Auto-start reconnected threads.
- `bool = False`
- keyword only

`**auth`: Mapping of type key to secrets (authentication).
- `dict[str, dict[str, str]]`
- keyword only
- default: `{}` (no auth)

Returns
`obj`: Object with all `Reconnectors` replaced by live resources.
- `Any`

Raises
- Nothing by default. `<suitkaise-api>reconnect_all</suitkaise-api>()` swallows reconnect errors and keeps the original `Reconnector` in place if reconnect fails.

### `**auth`

`**auth` is a mapping of type key to secrets (authentication).

Type keys are the actual connection types (`module.ClassName` strings).

`"psycopg2.Connection"`, `"redis.Redis"`, ...

Each of these type keys maps to a dict.

- Use `"*"` to provide the default authentication for all instances of that type
- Use attribute names to override the default for that given attribute

```python
auth = {
    "psycopg2.Connection": {
        "*": "default_psycopg2_password",
        "analytics_db": "analytics_password"  # used for obj.analytics_db specifically
    },
    "redis.Redis": {
        "*": "default_redis_password"
    }
}

restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>(restored, start_threads=True, **auth)
```

If no `auth` is provided for a reconnector, `reconnect()` and `<suitkaise-api>reconnect_all</suitkaise-api>()` are still called.

This is fine in most cases unless you are using database connections that require authentication (a password, token, ...).

### `DbReconnector` supported database types

- `psycopg2.Connection` (PostgreSQL / psycopg2): auth required
- `psycopg.Connection` (PostgreSQL / psycopg3): auth required
- `pymysql.Connection` (MySQL / PyMySQL): auth required
- `mysql.connector.connection.MySQLConnection` (MySQL / mysql-connector): auth required
- `mariadb.Connection` (MariaDB): auth required
- `sqlite3.Connection` (SQLite): no auth (file/":memory:" path)
- `pymongo.MongoClient` (MongoDB): auth required for protected deployments
- `redis.Redis` (Redis): auth required for protected deployments
- `sqlalchemy.Engine` (SQLAlchemy): auth required if the URL requires it
- `cassandra.Cluster` (Cassandra): auth required for protected deployments
- `elasticsearch.Elasticsearch` (Elasticsearch): auth required for protected deployments
- `neo4j.Driver` (Neo4j): auth required
- `influxdb_client.InfluxDBClient` (InfluxDB): auth required (token)
- `pyodbc.Connection` (ODBC): auth required
- `clickhouse_driver.Client` (ClickHouse): auth required for protected deployments
- `pymssql.Connection` (MS SQL Server): auth required
- `oracledb.Connection` (Oracle): auth required
- `cx_Oracle.Connection` (Oracle / cx_Oracle): auth required
- `snowflake.Connection` (Snowflake): auth required
- `duckdb.Connection` (DuckDB): no auth (file/":memory:" path)

## IR, `<suitkaise-api>serialize_ir</suitkaise-api>()` and deserializing an IR

`<suitkaise-api>cucumber</suitkaise-api>` converts Python objects into an intermediate representation (IR) that is solely comprised of `pickle` native types. Then, `pickle` is used to serialize the IR to bytes.

```python
{
    "__cucumber_type__": "class_instance",
    "__handler__": "ClassInstanceHandler",
    "__object_id__": 140123456789232,
    "module": "my_app.models",
    "class_name": "User",
    "state": {
        "id": 1,
        "name": "alice",
        "roles": ["admin", "editor"],
    }
}
```

### `<suitkaise-api>serialize_ir</suitkaise-api>()`

Returns the IR without converting to bytes.

Use this to inspect the IR of an object.
- debugging
- inspection
- custom tooling

```python
ir = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize_ir</suitkaise-api>(obj)
```

Arguments
`obj`: Any Python object
- `Any`
- required

`debug`: Enables deep error context and path reporting.
- `bool = False`
- keyword only

`verbose`: Prints progress and handler selection information.
- `bool = False`
- keyword only

Returns
A `pickle` native IR (nested `dict`/`list` structure)

Raises
`<suitkaise-api>SerializationError</suitkaise-api>`: If serialization fails.

### Deserializing an IR

In order to deserialize an IR, you must first convert it to bytes using `pickle.dumps()`.

Generally, when serializing to an ir, you are doing it to inspect it, or directly work with it.

```python
ir = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize_ir</suitkaise-api>(obj)
data = pickle.dumps(ir)

restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize_ir</suitkaise-api>(ir)
```

Raises
`<suitkaise-api>DeserializationError</suitkaise-api>`: If deserialization fails.


## JSON conversion

`<suitkaise-api>cucumber</suitkaise-api>` provides 4 ways to convert an IR to JSON.

2 of them convert the IR to a JSON-serializable structure, and the other 2 convert the IR directly to a JSON string.

### What is the difference between a JSON-serializable structure and a JSON string?

A JSON-serializable structure is a Python `dict`/`list` tree that only uses JSON-safe types (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`). 

A JSON string is the final serialized text output (the result of `json.dumps`). The structure is useful if you want to inspect or modify the IR in Python before turning it into a string.

### `<suitkaise-api>to_jsonable</suitkaise-api>()`

Serialize an object to IR and return a JSON-serializable structure.

```python
jsonable = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>to_jsonable</suitkaise-api>(obj)
```

Arguments
`obj`: Any Python object to convert to IR before JSON conversion.
- `Any`
- required

`debug`: Enables deep error context and path reporting.
- `bool = False`
- keyword only

`verbose`: Prints progress and handler selection information.
- `bool = False`
- keyword only

Returns
`Any`: A JSON-serializable structure.

Raises
`<suitkaise-api>SerializationError</suitkaise-api>`: If serialization fails.

### `<suitkaise-api>to_json</suitkaise-api>()`

Serialize an object to IR and return a JSON string.

```python
json_text = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>to_json</suitkaise-api>(obj)
```

Arguments
`obj`: Any Python object to convert to IR before JSON conversion.
- `Any`
- required

`indent`: The number of spaces to use for indentation.
- `int | None = 2`
- keyword only

`sort_keys`: Sort keys in the JSON output.
- `bool = True`
- keyword only

`debug`: Enables deep error context and path reporting.
- `bool = False`
- keyword only

`verbose`: Prints progress and handler selection information.
- `bool = False`
- keyword only

Returns
`str`: A JSON string.

Raises
`<suitkaise-api>SerializationError</suitkaise-api>`: If serialization fails.


### `<suitkaise-api>ir_to_jsonable</suitkaise-api>()`

Convert an IR to a JSON-serializable structure.

```python
ir = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize_ir</suitkaise-api>(obj)
jsonable = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>ir_to_jsonable</suitkaise-api>(ir)
```

Arguments
`ir`: The IR to convert.
- `Any`
- required

Returns
`Any`: A JSON-serializable structure.

Raises
`<suitkaise-api>SerializationError</suitkaise-api>`: If conversion fails.

### `<suitkaise-api>ir_to_json</suitkaise-api>()`

Convert an IR to a JSON string.

```python
ir = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize_ir</suitkaise-api>(obj)
json_text = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>ir_to_json</suitkaise-api>(ir)
```

Arguments
`ir`: The IR to convert.
- `Any`
- required

`indent`: The number of spaces to use for indentation.
- `int | None = 2`
- keyword only

`sort_keys`: Sort keys in the JSON output.
- `bool = True`
- keyword only

Returns
`str`: A JSON string.

Raises
`<suitkaise-api>SerializationError</suitkaise-api>`: If conversion fails.

### Crossing programming language boundaries using JSON

`<suitkaise-api>cucumber</suitkaise-api>` is meant to work solely within Python.

Here are the steps to convert a Python object to an object in another programming language:

1. Convert a Python object to a JSON-serializable IR using `<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>to_jsonable</suitkaise-api>()` (or directly to text using `<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>to_json</suitkaise-api>()`), then write it out.

```python
class Counter:

    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def decrement(self):
        self.count -= 1

counter = Counter()

jsonable = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>to_jsonable</suitkaise-api>(counter)
with open("counter.json", "w") as f:
    json.dump(jsonable, f)
```

2. Load the JSON data in the target language.

3. Interpret the IR nodes (`__cucumber_type__`, `__handler__`) and map them to equivalent types or a custom schema.

4. Replace Python-only concepts (modules, class names, callables) with your own equivalents or drop them.

5. Reconstruct the object graph in the target language.





