"""
SQLite Database Connections Serialization Handler

This module provides serialization support for SQLite database connections
and related database objects that cannot be pickled due to their connection
to external resources and system-level state.

SUPPORTED OBJECTS:
==================

1. SQLITE3 CONNECTIONS:
   - sqlite3.Connection objects
   - Database connections to file-based databases
   - In-memory database connections (:memory:)

2. SQLITE3 CURSORS:
   - sqlite3.Cursor objects
   - Active cursors with ongoing queries

3. DATABASE ROWS:
   - sqlite3.Row objects (when row_factory is set)
   - Custom row factory results

4. PREPARED STATEMENTS:
   - Cached prepared statements
   - Compiled SQL queries

SERIALIZATION STRATEGY:
======================

Database connection serialization requires different approaches:

1. **File Databases**: Store database path, connection parameters, and settings
2. **Memory Databases**: Store complete database schema and data (if small)
3. **Cursors**: Store connection info and query state
4. **Transactions**: Handle active transactions appropriately

Our approach:
- **Preserve connection parameters** (database path, timeout, isolation level)
- **Store database schema** when possible
- **Handle in-memory databases** by dumping/restoring data
- **Recreate connections** with same configuration
- **Provide transaction warnings** for active transactions

LIMITATIONS: # TODO address these later
============
- Active transactions are lost during serialization
- Large databases are not fully serialized (only connection info)
- Custom functions and aggregates registered on connections are lost
- Cursors lose their query state and results
- Concurrent access issues may arise if database is modified externally
- WAL mode and other advanced features may not be preserved

"""

import sqlite3
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional, List, Union

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class SQLiteConnectionsHandler(_NSO_Handler):
    """Handler for SQLite database connections and related objects."""
    
    def __init__(self):
        """Initialize the SQLite connections handler."""
        super().__init__()
        self._handler_name = "SQLiteConnectionsHandler"
        self._priority = 30  # High priority since database connections are critical
        
        # Size limit for dumping in-memory databases (10MB)
        self._memory_db_size_limit = 10 * 1024 * 1024
        
        # Lock for thread safety during serialization
        self._lock = threading.Lock()
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given SQLite object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for sqlite3.Connection objects
        - Check for sqlite3.Cursor objects  
        - Check for sqlite3.Row objects
        - Check for other sqlite3-related types
        """
        try:
            # SQLite3 Connection objects
            if isinstance(obj, sqlite3.Connection):
                return True
            
            # SQLite3 Cursor objects
            if isinstance(obj, sqlite3.Cursor):
                return True
            
            # SQLite3 Row objects (when row_factory is set to sqlite3.Row)
            if isinstance(obj, sqlite3.Row):
                return True
            
            # Check by type name for other SQLite objects
            obj_type_name = type(obj).__name__
            obj_module = getattr(type(obj), '__module__', '')
            
            if 'sqlite3' in obj_module and obj_type_name in [
                'Connection', 'Cursor', 'Row', 'PreparedStatement'
            ]:
                return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a SQLite object to a dictionary representation.
        
        Args:
            obj: SQLite object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the object
            
        SERIALIZATION PROCESS:
        1. Determine SQLite object type
        2. Extract connection parameters and metadata
        3. Handle special cases (memory databases, active transactions)
        4. Store schema and data when appropriate
        5. Provide recreation strategy
        """
        # Base serialization data
        data = {
            "sqlite_type": self._get_sqlite_type(obj),
            "object_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "serialization_strategy": None,  # Will be determined below
            "recreation_possible": False,
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        sqlite_type = data["sqlite_type"]
        
        if sqlite_type == "connection":
            data.update(self._serialize_connection(obj))
            data["serialization_strategy"] = "connection_recreation"
            
        elif sqlite_type == "cursor":
            data.update(self._serialize_cursor(obj))
            data["serialization_strategy"] = "cursor_recreation"
            
        elif sqlite_type == "row":
            data.update(self._serialize_row(obj))
            data["serialization_strategy"] = "row_recreation"
            
        else:
            # Unknown SQLite type
            data.update(self._serialize_unknown_sqlite(obj))
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a SQLite object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized SQLite data
            
        Returns:
            Recreated SQLite object (with limitations noted in documentation)
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Restore object with metadata and configuration
        4. Handle errors gracefully with placeholders
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        sqlite_type = data.get("sqlite_type", "unknown")
        
        try:
            if strategy == "connection_recreation":
                return self._deserialize_connection(data)
            
            elif strategy == "cursor_recreation":
                return self._deserialize_cursor(data)
            
            elif strategy == "row_recreation":
                return self._deserialize_row(data)
            
            elif strategy == "fallback_placeholder":
                return self._deserialize_unknown_sqlite(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a placeholder
            return self._create_error_placeholder(sqlite_type, str(e))
    
    # ========================================================================
    # SQLITE TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_sqlite_type(self, obj: Any) -> str:
        """
        Determine the specific type of SQLite object.
        
        Args:
            obj: SQLite object to analyze
            
        Returns:
            String identifying the SQLite object type
        """
        if isinstance(obj, sqlite3.Connection):
            return "connection"
        elif isinstance(obj, sqlite3.Cursor):
            return "cursor"
        elif isinstance(obj, sqlite3.Row):
            return "row"
        else:
            return "unknown"
    
    # ========================================================================
    # CONNECTION SERIALIZATION
    # ========================================================================
    
    def _serialize_connection(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Serialize SQLite connection objects.
        
        Extract connection parameters, settings, and optionally database content.
        """
        result = {
            "database_path": None,
            "is_memory_db": False,
            "connection_settings": {},
            "database_schema": None,
            "database_data": None,
            "has_active_transaction": False,
            "store_full_database": False
        }
        
        with self._lock:
            try:
                # Get database path - this is tricky because sqlite3.Connection
                # doesn't directly expose the database path
                # We'll try to get it from the connection's attributes
                
                # Check if it's an in-memory database
                # In-memory databases typically can't be queried for their path
                try:
                    # Try to get database list - this works for file databases
                    cursor = conn.execute("PRAGMA database_list")
                    databases = cursor.fetchall()
                    cursor.close()
                    
                    if databases:
                        main_db = databases[0]  # First entry is usually 'main'
                        db_file = main_db[2] if len(main_db) > 2 else None
                        
                        if db_file == '' or db_file is None:
                            result["is_memory_db"] = True
                            result["database_path"] = ":memory:"
                        else:
                            result["database_path"] = db_file
                            result["is_memory_db"] = False
                    else:
                        result["is_memory_db"] = True
                        result["database_path"] = ":memory:"
                        
                except sqlite3.Error:
                    # If we can't get database list, assume in-memory
                    result["is_memory_db"] = True
                    result["database_path"] = ":memory:"
                
                # Get connection settings
                try:
                    cursor = conn.execute("PRAGMA compile_options")
                    compile_options = [row[0] for row in cursor.fetchall()]
                    cursor.close()
                    result["connection_settings"]["compile_options"] = compile_options
                except sqlite3.Error:
                    pass
                
                # Get various PRAGMA settings
                pragma_settings = [
                    "journal_mode", "synchronous", "cache_size", "temp_store",
                    "locking_mode", "page_size", "auto_vacuum", "encoding",
                    "foreign_keys", "recursive_triggers", "timeout"
                ]
                
                for pragma in pragma_settings:
                    try:
                        cursor = conn.execute(f"PRAGMA {pragma}")
                        value = cursor.fetchone()
                        cursor.close()
                        if value:
                            result["connection_settings"][pragma] = value[0]
                    except sqlite3.Error:
                        pass
                
                # Check for active transactions
                try:
                    result["has_active_transaction"] = conn.in_transaction
                except AttributeError:
                    # Older Python versions might not have in_transaction
                    result["has_active_transaction"] = False
                
                # For in-memory databases or small databases, store schema and data
                if result["is_memory_db"] or self._should_store_full_database(result["database_path"]):
                    try:
                        result.update(self._dump_database_content(conn))
                        result["store_full_database"] = True
                    except Exception as e:
                        result["note"] = f"Could not dump database content: {e}"
                
                # Get schema for all databases (even if not storing full content)
                try:
                    result["database_schema"] = self._get_database_schema(conn)
                except Exception as e:
                    result["note"] = f"Could not extract schema: {e}"
                
            except Exception as e:
                result["note"] = f"Error serializing connection: {e}"
        
        result["recreation_possible"] = bool(
            result["database_path"] and 
            (result["store_full_database"] or not result["is_memory_db"])
        )
        
        if result["has_active_transaction"]:
            result["transaction_warning"] = "Active transaction will be lost during serialization"
        
        return result
    
    def _deserialize_connection(self, data: Dict[str, Any]) -> sqlite3.Connection:
        """
        Deserialize SQLite connection objects by recreating the connection.
        """
        database_path = data.get("database_path")
        is_memory_db = data.get("is_memory_db", False)
        connection_settings = data.get("connection_settings", {})
        store_full_database = data.get("store_full_database", False)
        database_schema = data.get("database_schema")
        database_data = data.get("database_data")
        
        if not database_path:
            raise ValueError("No database path available for connection recreation")
        
        try:
            # Create new connection
            if is_memory_db or database_path == ":memory:":
                # For in-memory databases, always create new :memory: database
                conn = sqlite3.connect(":memory:")
                
                # Restore schema and data if available
                if store_full_database and database_schema:
                    self._restore_database_content(conn, database_schema, database_data)
                    
            else:
                # For file databases, check if file exists
                if os.path.exists(database_path):
                    conn = sqlite3.connect(database_path)
                elif store_full_database and database_schema:
                    # File doesn't exist but we have full database content
                    # Create new file database and restore content
                    conn = sqlite3.connect(database_path)
                    self._restore_database_content(conn, database_schema, database_data)
                else:
                    raise FileNotFoundError(f"Database file {database_path} no longer exists")
            
            # Restore connection settings
            for setting, value in connection_settings.items():
                if setting not in ["compile_options"]:  # Skip read-only settings
                    try:
                        conn.execute(f"PRAGMA {setting} = ?", (value,))
                    except sqlite3.Error:
                        pass  # Some settings might not be settable
            
            # Commit any PRAGMA changes
            conn.commit()
            
            return conn
            
        except Exception as e:
            raise ValueError(f"Could not recreate SQLite connection: {e}")
    
    # ========================================================================
    # CURSOR SERIALIZATION
    # ========================================================================
    
    def _serialize_cursor(self, cursor: sqlite3.Cursor) -> Dict[str, Any]:
        """
        Serialize SQLite cursor objects.
        
        Store connection info and cursor state.
        """
        result = {
            "connection_info": None,
            "cursor_description": None,
            "row_count": None,
            "last_row_id": None
        }
        
        try:
            # Get connection information
            if cursor.connection:
                # Recursively serialize the connection (but avoid infinite recursion)
                result["connection_info"] = {
                    "database_path": self._get_connection_path(cursor.connection),
                    "is_memory": self._is_memory_connection(cursor.connection)
                }
            
            # Get cursor state
            result["cursor_description"] = cursor.description
            result["row_count"] = getattr(cursor, 'rowcount', -1)
            result["last_row_id"] = getattr(cursor, 'lastrowid', None)
            
        except Exception as e:
            result["note"] = f"Error serializing cursor: {e}"
        
        result["recreation_possible"] = bool(result["connection_info"])
        result["limitation"] = "Cursor query state and results will be lost"
        
        return result
    
    def _deserialize_cursor(self, data: Dict[str, Any]) -> sqlite3.Cursor:
        """
        Deserialize SQLite cursor objects by creating new cursor.
        """
        connection_info = data.get("connection_info")
        
        if not connection_info:
            raise ValueError("No connection info available for cursor recreation")
        
        try:
            # Recreate connection
            database_path = connection_info.get("database_path", ":memory:")
            
            if connection_info.get("is_memory", False):
                conn = sqlite3.connect(":memory:")
            else:
                conn = sqlite3.connect(database_path)
            
            # Create new cursor
            cursor = conn.cursor()
            
            return cursor
            
        except Exception as e:
            raise ValueError(f"Could not recreate SQLite cursor: {e}")
    
    # ========================================================================
    # ROW SERIALIZATION
    # ========================================================================
    
    def _serialize_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Serialize SQLite Row objects.
        
        Store row data and column information.
        """
        result = {
            "row_data": None,
            "column_names": None,
            "row_keys": None
        }
        
        try:
            # Get row data as tuple
            result["row_data"] = tuple(row)
            
            # Get column names (keys)
            result["column_names"] = row.keys() if hasattr(row, 'keys') else None
            
            # Store as dict for easier recreation
            if result["column_names"]:
                result["row_dict"] = dict(row)
            
        except Exception as e:
            result["note"] = f"Error serializing row: {e}"
        
        result["recreation_possible"] = result["row_data"] is not None
        
        return result
    
    def _deserialize_row(self, data: Dict[str, Any]) -> sqlite3.Row:
        """
        Deserialize SQLite Row objects by creating equivalent row.
        """
        row_data = data.get("row_data")
        column_names = data.get("column_names")
        row_dict = data.get("row_dict")
        
        if row_data is None:
            raise ValueError("No row data available for row recreation")
        
        try:
            # Create a temporary in-memory database with row factory
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            
            if column_names and len(column_names) == len(row_data):
                # Create temporary table with appropriate columns
                column_defs = ", ".join(f"col_{i} TEXT" for i in range(len(column_names)))
                conn.execute(f"CREATE TABLE temp_row ({column_defs})")
                
                # Insert the row data
                placeholders = ", ".join("?" * len(row_data))
                conn.execute(f"INSERT INTO temp_row VALUES ({placeholders})", row_data)
                
                # Fetch as Row object
                cursor = conn.execute("SELECT * FROM temp_row")
                recreated_row = cursor.fetchone()
                cursor.close()
                conn.close()
                
                return recreated_row if recreated_row else tuple(row_data)
            else:
                # Fallback: return as tuple
                conn.close()
                return tuple(row_data)
            
        except Exception as e:
            # Final fallback: return as tuple
            return tuple(row_data) if row_data else ()
    
    # ========================================================================
    # DATABASE CONTENT DUMP/RESTORE METHODS
    # ========================================================================
    
    def _should_store_full_database(self, database_path: Optional[str]) -> bool:
        """
        Determine if we should store the full database content.
        
        Args:
            database_path: Path to the database file
            
        Returns:
            True if the database is small enough to store completely
        """
        if not database_path or database_path == ":memory:":
            return True
        
        try:
            if os.path.exists(database_path):
                file_size = os.path.getsize(database_path)
                return file_size <= self._memory_db_size_limit
        except OSError:
            pass
        
        return False
    
    def _dump_database_content(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Dump complete database content (schema + data).
        
        Args:
            conn: SQLite connection to dump
            
        Returns:
            Dictionary with schema and data
        """
        result = {
            "schema_sql": [],
            "table_data": {}
        }
        
        # Get schema
        cursor = conn.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type IN ('table', 'index', 'view', 'trigger')
            AND sql IS NOT NULL
            ORDER BY type, name
        """)
        
        for row in cursor:
            if row[0]:
                result["schema_sql"].append(row[0])
        cursor.close()
        
        # Get table data
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
        table_names = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        for table_name in table_names:
            try:
                cursor = conn.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                cursor.close()
                result["table_data"][table_name] = rows
            except sqlite3.Error:
                pass  # Skip tables we can't read
        
        return result
    
    def _restore_database_content(self, conn: sqlite3.Connection, schema: List[str], data: Dict[str, List]) -> None:
        """
        Restore database content from schema and data.
        
        Args:
            conn: SQLite connection to restore to
            schema: List of SQL statements to create schema
            data: Dictionary of table data
        """
        # Execute schema statements
        for sql in schema:
            try:
                conn.execute(sql)
            except sqlite3.Error:
                pass  # Skip statements that fail
        
        # Insert data
        if data:
            for table_name, rows in data.items():
                if rows:
                    try:
                        # Get column count
                        cursor = conn.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        cursor.close()
                        
                        if columns:
                            placeholders = ", ".join("?" * len(columns))
                            conn.executemany(
                                f"INSERT INTO {table_name} VALUES ({placeholders})", 
                                rows
                            )
                    except sqlite3.Error:
                        pass  # Skip tables we can't insert into
        
        conn.commit()
    
    def _get_database_schema(self, conn: sqlite3.Connection) -> List[str]:
        """
        Get database schema as list of SQL statements.
        
        Args:
            conn: SQLite connection
            
        Returns:
            List of SQL statements
        """
        cursor = conn.execute("""
            SELECT sql FROM sqlite_master 
            WHERE sql IS NOT NULL
            ORDER BY type, name
        """)
        
        schema = [row[0] for row in cursor.fetchall() if row[0]]
        cursor.close()
        return schema
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _get_connection_path(self, conn: sqlite3.Connection) -> Optional[str]:
        """
        Try to get the database path from a connection.
        
        Args:
            conn: SQLite connection
            
        Returns:
            Database path or None if unknown
        """
        try:
            cursor = conn.execute("PRAGMA database_list")
            databases = cursor.fetchall()
            cursor.close()
            
            if databases:
                main_db = databases[0]
                return main_db[2] if len(main_db) > 2 else None
        except sqlite3.Error:
            pass
        
        return None
    
    def _is_memory_connection(self, conn: sqlite3.Connection) -> bool:
        """
        Check if a connection is to an in-memory database.
        
        Args:
            conn: SQLite connection
            
        Returns:
            True if connection is to in-memory database
        """
        path = self._get_connection_path(conn)
        return path == '' or path is None
    
    def _serialize_unknown_sqlite(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown SQLite types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_type": type(obj).__name__,
            "object_module": getattr(type(obj), '__module__', 'unknown'),
            "note": f"Unknown SQLite type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_sqlite(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown SQLite types with placeholder.
        """
        object_type = data.get("object_type", "unknown")
        
        class SQLitePlaceholder:
            def __init__(self, obj_type):
                self.obj_type = obj_type
            
            def __repr__(self):
                return f"<SQLitePlaceholder type='{self.obj_type}'>"
            
            def __getattr__(self, name):
                raise RuntimeError(f"SQLite object ({self.obj_type}) could not be recreated")
        
        return SQLitePlaceholder(object_type)
    
    def _create_error_placeholder(self, sqlite_type: str, error_message: str) -> Any:
        """
        Create a placeholder SQLite object for objects that failed to deserialize.
        """
        class SQLiteErrorPlaceholder:
            def __init__(self, obj_type, error):
                self.obj_type = obj_type
                self.error = error
            
            def __repr__(self):
                return f"<SQLiteErrorPlaceholder type='{self.obj_type}' error='{self.error}'>"
            
            def __getattr__(self, name):
                raise RuntimeError(f"SQLite object ({self.obj_type}) deserialization failed: {self.error}")
        
        return SQLiteErrorPlaceholder(sqlite_type, error_message)


# Create a singleton instance for auto-registration
sqlite_connections_handler = SQLiteConnectionsHandler()