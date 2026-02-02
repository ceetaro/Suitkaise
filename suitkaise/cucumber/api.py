"""
────────────────────────────────────────────────────────
    ```python
    from suitkaise import cucumber
    ```
────────────────────────────────────────────────────────\n

API for the cucumber module.

Includes functions for serialization and deserialization,
as well as options to convert to an intermediate representation (IR)
and also an option to convert to JSON.

Additionally, includes a function to reconnect all live objects that need to 
be reauthenticated or reinitialized after serialization.
"""

from ._int.serializer import Serializer, SerializationError
from ._int.deserializer import Deserializer, DeserializationError
from ._int.ir_json import ir_to_json as _ir_to_json
from ._int.ir_json import ir_to_jsonable as _ir_to_jsonable
from ._int.handlers.reconnector import Reconnector

# convenient default instances
_default_serializer = Serializer()
_default_deserializer = Deserializer()


def serialize(obj, debug: bool = False, verbose: bool = False) -> bytes:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cucumber
        
        # Serialize any object to bytes
        data = cucumber.serialize(obj)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize any Python object to bytes.
    
    Handles many Python objects that otherwise be unserializable.

    Some objects cannot be truly serialized due to Python's design.
    This is what we do:

    1. try to keep the exact object intact
    2. recreate an exact copy of the object using the object's state at serialization time
    3. give a placeholder object that can be used to recreate an exact copy of the object
    4. give info on the object's state pre-serialization
    
    Args:
        obj: Object to serialize
        debug: Enable debug mode for detailed error messages
        verbose: Enable verbose mode to print serialization progress
        
    Returns:
        bytes: Serialized representation
        
    Raises:
        SerializationError: If serialization fails
    
    ────────────────────────────────────────────────────────
        ```python
        # Serialize an object with locks, loggers, and a database connection
        import threading
        import logging
        
        class ComplexService:
            def __init__(self):
                self.lock = threading.Lock()
                self.logger = logging.getLogger("service")
                self.conn = psycopg2.connect(
                    host="localhost",
                    database="mydatabase",
                    user="myuser",
                    password="mypassword",
                )
        
        service = ComplexService()
        
        # cucumber handles all of these objects automatically
        serialized = cucumber.serialize(service)
        ```
    ────────────────────────────────────────────────────────
    """
    if debug or verbose:
        serializer = Serializer(debug=debug, verbose=verbose)
        return serializer.serialize(obj)
    return _default_serializer.serialize(obj)


def serialize_ir(obj, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cucumber
        
        ir = cucumber.serialize_ir(my_complex_object)
        ```
    ────────────────────────────────────────────────────────\n

    Build and return the intermediate representation (IR) 
    without converting fully to bytes.
    
    Args:
        obj: Object to convert to IR
        debug: Enable debug mode for detailed error messages
        verbose: Enable verbose mode to print serialization progress
        
    Returns:
        IR: Nested dict/list structure of pickle-native types

    ```python
    {
        "__cucumber_type__": "lock",
        "__handler__": "LockHandler",
        "__object_id__": 140234567890,
        "state": {
            "locked": False
        }
    }
    """
    if debug or verbose:
        serializer = Serializer(debug=debug, verbose=verbose)
        return serializer.serialize_ir(obj)
    return _default_serializer.serialize_ir(obj)


def deserialize(data: bytes, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cucumber
        
        # Deserialize bytes back to an object
        obj = cucumber.deserialize(data)
        ```
    ────────────────────────────────────────────────────────\n

    Deserialize bytes back to a Python object.
    
    Reconstructs objects serialized with cucumber.serialize().
    
    Args:
        data: Serialized bytes from cucumber.serialize()
        debug: Enable debug mode for detailed error messages
        verbose: Enable verbose mode to print deserialization progress
        
    Returns:
        Reconstructed Python object
        
    Raises:
        DeserializationError: If deserialization fails
    
    ────────────────────────────────────────────────────────
        ```python
        # round-trip
        original = ComplexService()
        
        # serialize
        serialized = cucumber.serialize(original)
        
        # deserialize
        restored = cucumber.deserialize(serialized)
        
        # state is preserved
        with restored.lock: # will work

        # once reconnected, conn will work
        restored.conn.reconnect(auth="mypassword")
        ```
    ────────────────────────────────────────────────────────
    """
    if debug or verbose:
        deserializer = Deserializer(debug=debug, verbose=verbose)
        return deserializer.deserialize(data)
    return _default_deserializer.deserialize(data)


def reconnect_all(obj, *, start_threads: bool = False, **auth):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cucumber
        
        auth = {
            "psycopg2.Connection": {"*": "secret"},
            "redis.Redis": {"*": "redis_pass"},
        }
        
        cucumber.reconnect_all(obj, **auth)
        ```
    ────────────────────────────────────────────────────────\n

    Recursively reconnect `Reconnector` objects inside a structure.
    
    This walks lists, tuples, sets, dict keys/values, object __dict__ values,
    and __slots__ when available. If a `Reconnector` is found, its `reconnect()`
    method is called and the result is placed back into the structure.
    
    Args:
        obj: Object or container to traverse.
        start_threads: If True, auto-start any reconnected threads.
        **auth: Credentials keyed by type. dict[str, str] pattern
            ```python 
            auth = {
                "psycopg2.Connection": {
                    "*": "secret",           # default auth
                    "analytics_db": "other", # specific attr auth
                },
                "redis.Redis": {
                    "*": "your_redis_password",
                },
            })

            reconnect_all(obj, **auth)
            ```
            The `"*"` key provides default auth for all instances of that type.
            Specific attr names override the default.
    """
    import threading
    
    visited: set[int] = set()
    
    def _get_reconnector_type_key(reconnector: Reconnector) -> str | None:
        """Get the type key for looking up kwargs."""
        # map specific reconnector classes to user-friendly type keys
        class_name = type(reconnector).__name__
        type_key_map = {
            "PostgresReconnector": "psycopg2.Connection",
            "MySQLReconnector": "pymysql.Connection",
            "SQLiteReconnector": "sqlite3.Connection",
            "MongoReconnector": "pymongo.MongoClient",
            "RedisReconnector": "redis.Redis",
            "SQLAlchemyReconnector": "sqlalchemy.Engine",
            "CassandraReconnector": "cassandra.Cluster",
            "ElasticsearchReconnector": "elasticsearch.Elasticsearch",
            "Neo4jReconnector": "neo4j.Driver",
            "InfluxDBReconnector": "influxdb_client.InfluxDBClient",
            "ODBCReconnector": "pyodbc.Connection",
            "ClickHouseReconnector": "clickhouse_driver.Client",
            "MSSQLReconnector": "pymssql.Connection",
            "OracleReconnector": "oracledb.Connection",
            "SnowflakeReconnector": "snowflake.Connection",
            "DuckDBReconnector": "duckdb.Connection",
        }
        if class_name in type_key_map:
            return type_key_map[class_name]
        
        # fallback: check for module/class_name attributes (for mocks/custom reconnectors)
        module = getattr(reconnector, 'module', None)
        orig_class_name = getattr(reconnector, 'class_name', None)
        if module and orig_class_name:
            base_module = module.split('.')[0]
            normalized_class = orig_class_name.title().replace('_', '')
            return f"{base_module}.{normalized_class}"
        
        return None
    
    def _get_auth_for(reconnector: Reconnector, attr_name: str | None) -> str | None:
        """Look up auth for a reconnector based on type and attr name."""
        type_key = _get_reconnector_type_key(reconnector)
        if not type_key or type_key not in auth:
            return None
        
        type_auth = auth[type_key]
        if not isinstance(type_auth, dict):
            return None
        
        # Check for specific attr auth first, then fall back to "*" default
        if attr_name and attr_name in type_auth:
            return type_auth[attr_name]
        return type_auth.get("*")
    
    def _recurse(item, attr_name: str | None = None):
        if isinstance(item, Reconnector):
            try:
                auth_value = _get_auth_for(item, attr_name)
                if auth_value is None:
                    result = item.reconnect()
                else:
                    try:
                        result = item.reconnect(auth_value)
                    except TypeError:
                        try:
                            result = item.reconnect(auth=auth_value)
                        except TypeError:
                            result = item.reconnect(password=auth_value)
                if start_threads and isinstance(result, threading.Thread):
                    try:
                        if not result.is_alive():
                            result.start()
                    except RuntimeError:
                        pass
                return result
            except Exception:
                return item
        
        item_id = id(item)
        if item_id in visited:
            return item
        
        # containers
        if isinstance(item, list):
            visited.add(item_id)
            for idx, value in enumerate(item):
                item[idx] = _recurse(value, None)
            return item
        
        if isinstance(item, tuple):
            visited.add(item_id)
            return tuple(_recurse(value, None) for value in item)
        
        if isinstance(item, set):
            visited.add(item_id)
            try:
                return {_recurse(value, None) for value in item}
            except TypeError:
                return item
        
        if isinstance(item, dict):
            visited.add(item_id)
            updated = {}
            changed = False
            for key, value in item.items():
                new_key = _recurse(key, None)
                # use dict key as attr_name for reconnector lookup
                new_value = _recurse(value, key if isinstance(key, str) else None)
                if new_key is not key or new_value is not value:
                    changed = True
                updated[new_key] = new_value
            if changed:
                item.clear()
                item.update(updated)
            return item
        
        # objects with instance dict
        if hasattr(item, "__dict__"):
            visited.add(item_id)
            for key, value in list(item.__dict__.items()):
                new_value = _recurse(value, key)
                if new_value is not value:
                    item.__dict__[key] = new_value
        
        # objects with slots
        slots = getattr(item, "__slots__", None)
        if slots:
            visited.add(item_id)
            if isinstance(slots, str):
                slots = (slots,)
            for slot in slots:
                try:
                    value = getattr(item, slot)
                except AttributeError:
                    continue
                new_value = _recurse(value, slot)
                if new_value is not value:
                    try:
                        setattr(item, slot, new_value)
                    except AttributeError:
                        pass
            return item
        
        return item
    
    return _recurse(obj, None)


def ir_to_jsonable(ir):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cucumber
        
        ir = cucumber.serialize_ir(obj)
        jsonable = cucumber.ir_to_jsonable(ir)
        ```
    ────────────────────────────────────────────────────────\n

    Convert a cucumber IR into a JSON-serializable structure.
    """
    return _ir_to_jsonable(ir)


def ir_to_json(ir, *, indent: int | None = 2, sort_keys: bool = True) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cucumber
        
        ir = cucumber.serialize_ir(obj)
        json_text = cucumber.ir_to_json(ir)
        ```
    ────────────────────────────────────────────────────────\n

    Convert a cucumber IR into JSON text.
    """
    return _ir_to_json(ir, indent=indent, sort_keys=sort_keys)


def to_jsonable(obj, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cucumber
        
        jsonable = cucumber.to_jsonable(obj)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize an object to IR and return a JSON-serializable structure.

    This is just like calling `serialize_ir()` and then `ir_to_jsonable()`.
    """
    ir = serialize_ir(obj, debug=debug, verbose=verbose)
    return _ir_to_jsonable(ir)


def to_json(
    obj,
    *,
    indent: int | None = 2,
    sort_keys: bool = True,
    debug: bool = False,
    verbose: bool = False,
) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cucumber
        
        json_text = cucumber.to_json(obj)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize an object to IR and return JSON text.

    This is just like calling `serialize_ir()` and then `ir_to_json()`.
    """
    ir = serialize_ir(obj, debug=debug, verbose=verbose)
    return _ir_to_json(ir, indent=indent, sort_keys=sort_keys)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # main functions
    'serialize',
    'serialize_ir',
    'deserialize',
    'reconnect_all',
    'ir_to_jsonable',
    'ir_to_json',
    'to_jsonable',
    'to_json',
    
    # exceptions
    'SerializationError',
    'DeserializationError',
]
