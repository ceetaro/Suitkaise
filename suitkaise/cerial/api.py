"""
Cerial API - Serialization for the Unpicklable

This module provides user-friendly serialization for objects that 
standard pickle cannot handle: locks, loggers, file handles, 
thread-local data, and more.

Key Features:
- Serialize complex objects with locks, loggers, and other unpicklables
- Automatic circular reference handling
- Handlers for common unpicklable types
- Clear error messages for debugging
"""

from ._int.serializer import Cerializer, SerializationError
from ._int.deserializer import Decerializer, DeserializationError
from ._int.ir_json import ir_to_json as _ir_to_json
from ._int.ir_json import ir_to_jsonable as _ir_to_jsonable
from ._int.handlers.reconnector import Reconnector

# convenient default instances
_default_serializer = Cerializer()
_default_deserializer = Decerializer()


def serialize(obj, debug: bool = False, verbose: bool = False) -> bytes:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        # Serialize any object to bytes
        data = cerial.serialize(my_complex_object)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize any Python object to bytes.
    
    Handles objects that standard pickle cannot serialize, including:
    - Objects with locks (threading.Lock, threading.RLock, etc.)
    - Objects with loggers (logging.Logger instances)
    - Objects with file handles
    - Objects with circular references
    - Custom classes with unpicklable attributes
    
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
        # Serialize an object with locks and loggers
        import threading
        import logging
        
        class ComplexService:
            def __init__(self):
                self.lock = threading.Lock()
                self.logger = logging.getLogger("service")
                self.data = {"users": [], "config": {}}
        
        service = ComplexService()
        
        # Cerial handles locks and loggers automatically
        serialized = cerial.serialize(service)
        ```
    ────────────────────────────────────────────────────────
    """
    if debug or verbose:
        serializer = Cerializer(debug=debug, verbose=verbose)
        return serializer.serialize(obj)
    return _default_serializer.serialize(obj)


def serialize_ir(obj, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        ir = cerial.serialize_ir(my_complex_object)
        ```
    ────────────────────────────────────────────────────────\n

    Build and return the intermediate representation (IR) without pickling.
    
    Args:
        obj: Object to convert to IR
        debug: Enable debug mode for detailed error messages
        verbose: Enable verbose mode to print serialization progress
        
    Returns:
        IR: Nested dict/list structure of pickle-native types
    """
    if debug or verbose:
        serializer = Cerializer(debug=debug, verbose=verbose)
        return serializer.serialize_ir(obj)
    return _default_serializer.serialize_ir(obj)


def deserialize(data: bytes, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        # Deserialize bytes back to an object
        my_object = cerial.deserialize(data)
        ```
    ────────────────────────────────────────────────────────\n

    Deserialize bytes back to a Python object.
    
    Reconstructs objects serialized with cerial.serialize(), including:
    - Recreating locks (as new, unlocked locks)
    - Recreating loggers (reconnected to logging system)
    - Rebuilding circular references
    - Restoring custom class instances
    
    Args:
        data: Serialized bytes from cerial.serialize()
        debug: Enable debug mode for detailed error messages
        verbose: Enable verbose mode to print deserialization progress
        
    Returns:
        Reconstructed Python object
        
    Raises:
        DeserializationError: If deserialization fails
    
    ────────────────────────────────────────────────────────
        ```python
        # Round-trip example
        original = ComplexService()
        original.data["users"].append("alice")
        
        # Serialize
        serialized = cerial.serialize(original)
        
        # Deserialize
        restored = cerial.deserialize(serialized)
        
        # State is preserved
        assert restored.data["users"] == ["alice"]
        
        # Locks are recreated (new, unlocked)
        assert restored.lock.acquire(blocking=False)  # Can acquire
        restored.lock.release()
        ```
    ────────────────────────────────────────────────────────
    """
    if debug or verbose:
        deserializer = Decerializer(debug=debug, verbose=verbose)
        return deserializer.deserialize(data)
    return _default_deserializer.deserialize(data)


def reconnect_all(obj, **kwargs):
    """
    Recursively reconnect Reconnector objects inside a structure.
    
    This walks lists, tuples, sets, dict keys/values, object __dict__ values,
    and __slots__ when available. If a Reconnector is found, its reconnect()
    method is called and the result is placed back into the structure.
    
    Args:
        obj: Object or container to traverse.
        **kwargs: Reconnection parameters keyed by type. Unpack a dict:
            reconnect_all(obj, **{
                "psycopg2.Connection": {
                    "*": {"host": "...", "password": "..."},  # default
                    "analytics_db": {"password": "other"},    # specific attr
                },
                ...
            })
            The "*" key provides defaults for all instances of that type.
            Specific attr names override/merge with the defaults.
    """
    visited: set[int] = set()
    
    def _get_reconnector_type_key(reconnector: Reconnector) -> str | None:
        """Get the type key for looking up kwargs."""
        # Map specific reconnector classes to user-friendly type keys
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
        
        # Fallback: check for module/class_name attributes (for mocks/custom reconnectors)
        module = getattr(reconnector, 'module', None)
        orig_class_name = getattr(reconnector, 'class_name', None)
        if module and orig_class_name:
            base_module = module.split('.')[0]
            normalized_class = orig_class_name.title().replace('_', '')
            return f"{base_module}.{normalized_class}"
        
        return None
    
    def _get_kwargs_for(reconnector: Reconnector, attr_name: str | None) -> dict:
        """Look up kwargs for a reconnector based on type and attr name."""
        type_key = _get_reconnector_type_key(reconnector)
        if not type_key or type_key not in kwargs:
            return {}
        
        type_kwargs = kwargs[type_key]
        if not isinstance(type_kwargs, dict):
            return {}
        
        # Start with defaults from "*"
        result = dict(type_kwargs.get("*", {}))
        
        # Merge specific attr kwargs on top
        if attr_name and attr_name in type_kwargs:
            result.update(type_kwargs[attr_name])
        
        return result
    
    def _recurse(item, attr_name: str | None = None):
        if isinstance(item, Reconnector):
            try:
                reconnect_kwargs = _get_kwargs_for(item, attr_name)
                return item.reconnect(**reconnect_kwargs)
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
                # Use dict key as attr_name for reconnector lookup
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
        from suitkaise import cerial
        
        ir = cerial.serialize_ir(obj)
        jsonable = cerial.ir_to_jsonable(ir)
        ```
    ────────────────────────────────────────────────────────\n

    Convert a cerial IR into a JSON-serializable structure.
    """
    return _ir_to_jsonable(ir)


def ir_to_json(ir, *, indent: int | None = 2, sort_keys: bool = True) -> str:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        ir = cerial.serialize_ir(obj)
        json_text = cerial.ir_to_json(ir)
        ```
    ────────────────────────────────────────────────────────\n

    Convert a cerial IR into JSON text.
    """
    return _ir_to_json(ir, indent=indent, sort_keys=sort_keys)


def to_jsonable(obj, debug: bool = False, verbose: bool = False):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import cerial
        
        jsonable = cerial.to_jsonable(obj)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize an object to IR and return a JSON-serializable structure.
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
        from suitkaise import cerial
        
        json_text = cerial.to_json(obj)
        ```
    ────────────────────────────────────────────────────────\n

    Serialize an object to IR and return JSON text.
    """
    ir = serialize_ir(obj, debug=debug, verbose=verbose)
    return _ir_to_json(ir, indent=indent, sort_keys=sort_keys)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main functions
    'serialize',
    'serialize_ir',
    'deserialize',
    'reconnect_all',
    'ir_to_jsonable',
    'ir_to_json',
    'to_jsonable',
    'to_json',
    
    # Classes for advanced usage
    'Cerializer',
    'Decerializer',
    
    # Exceptions
    'SerializationError',
    'DeserializationError',
]
