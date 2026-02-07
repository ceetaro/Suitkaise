"""
Handler for sqlite3 database connection objects.

SQLite connections are database handles. We serialize the database path
and optionally the schema and data, then reconnect in the target process.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple
from .base_class import Handler
from .reconnector import Reconnector


class SQLiteSerializationError(Exception):
    """Raised when SQLite serialization fails."""
    pass


@dataclass
class SQLiteConnectionReconnector(Reconnector):
    """
    Reconnector for sqlite3.Connection objects.
    
    Call reconnect() to create a new live connection. For in-memory databases,
    this will also restore the schema and data that was captured during serialization.
    """
    _lazy_reconnect_on_access = True
    state: Dict[str, Any]
    _conn: sqlite3.Connection | None = field(default=None, init=False, repr=False)
    
    def __repr__(self) -> str:
        db = self.state.get("database", ":memory:")
        return f"SQLiteConnectionReconnector({db!r})"
    
    def reconnect(self) -> sqlite3.Connection:
        """
        Create a new SQLite connection.
        
        For file-based databases: connects to the database file.
        For in-memory databases: creates new connection and restores schema/data.
        """
        if self._conn is not None:
            return self._conn

        state = self.state
        
        # connect to database
        conn = sqlite3.connect(state["database"])
        
        # set isolation level
        conn.isolation_level = state["isolation_level"]
        
        # for in-memory databases, restore schema and data
        if state["is_memory"] and (state["schema"] or state["data"]):
            cursor = conn.cursor()
            
            # execute CREATE statements
            for create_stmt in state["schema"]:
                try:
                    cursor.execute(create_stmt)
                except sqlite3.Error:
                    # table might already exist, continue
                    pass
            
            # insert data
            for table_name, rows in state["data"]:
                if rows:
                    # validate table name
                    if not table_name.replace('_', '').isalnum():
                        continue  # Skip invalid table names
                    
                    # build INSERT statement
                    placeholders = ','.join('?' * len(rows[0]))
                    insert_stmt = f"INSERT INTO {table_name} VALUES ({placeholders})"
                    
                    try:
                        cursor.executemany(insert_stmt, rows)
                    except sqlite3.Error:
                        # continue on error
                        pass
            
            conn.commit()
        
        self._conn = conn
        return conn



@dataclass
class SQLiteCursorReconnector(Reconnector):
    """
    Reconnector for sqlite3.Cursor objects.
    
    Call reconnect() to create a new cursor. If the connection is also a
    reconnector, it will be reconnected first.
    
    Note: The original query result set is NOT restored - you must re-execute
    your query after reconnecting.
    """
    _lazy_reconnect_on_access = True
    state: Dict[str, Any]
    _conn: sqlite3.Connection | None = field(default=None, init=False, repr=False)
    _cursor: sqlite3.Cursor | None = field(default=None, init=False, repr=False)
    
    def __repr__(self) -> str:
        return "SQLiteCursorReconnector()"
    
    def reconnect(self) -> sqlite3.Cursor:
        """
        Create a new cursor from the connection.
        
        If the connection is a SQLiteConnectionReconnector, reconnects it first.
        """
        if self._cursor is not None:
            return self._cursor

        conn = self.connection

        # create new cursor
        cursor = conn.cursor()
        cursor.arraysize = self.state["arraysize"]

        self._cursor = cursor
        return cursor

    @property
    def connection(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn

        conn = self.state["connection"]

        # if connection is a reconnector, reconnect it first
        if isinstance(conn, SQLiteConnectionReconnector):
            conn = conn.reconnect()

        self._conn = conn
        return conn



class SQLiteConnectionHandler(Handler):
    """
    Serializes sqlite3.Connection objects.
    
    Strategy:
    - For file-based databases: serialize path and reconnect
    - For in-memory databases: serialize path, schema, and all data
    - Capture isolation_level and other connection settings
    
    Important: For in-memory databases (':memory:'), we must serialize
    the entire database content since it won't exist in the target process.
    For file-based databases, we assume the file is accessible.
    """
    
    type_name = "sqlite_connection"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a sqlite3.Connection."""
        return isinstance(obj, sqlite3.Connection)
    
    def extract_state(self, obj: sqlite3.Connection) -> Dict[str, Any]:
        """
        Extract SQLite connection state.
        
        What we capture:
        - database: Database path or ':memory:'
        - isolation_level: Transaction isolation level (None, 'DEFERRED', etc.)
        - is_memory: Whether this is an in-memory database
        
        For in-memory databases, we also capture:
        - schema: CREATE TABLE statements
        - data: All table data
        
        Note: Serializing data is expensive for large databases!
        This is primarily for small in-memory databases used in testing.
        """
        # get database path
        # NOTE: In Python 3.7+, we can use connection.execute("PRAGMA database_list")
        # for older versions, we try to access internal attributes
        try:
            cursor = obj.execute("PRAGMA database_list")
            db_info = cursor.fetchone()
            database_path = db_info[2] if db_info else ':memory:'
        except (AttributeError, TypeError):
            # PRAGMA not supported or returns unexpected format - assume in-memory
            database_path = ':memory:'
        except Exception as e:
            # unexpected error querying database info - log and assume in-memory
            import warnings
            warnings.warn(f"Failed to get SQLite database path: {e}")
            database_path = ':memory:'
        
        is_memory = database_path == ':memory:' or database_path == ''
        
        # get connection settings
        isolation_level = obj.isolation_level
        
        # for in-memory databases, we need to dump schema and data
        if is_memory:
            schema, data = self._dump_database(obj)
        else:
            schema = []
            data = []
        
        return {
            "database": database_path,
            "isolation_level": isolation_level,
            "is_memory": is_memory,
            "schema": schema,
            "data": data,
        }
    
    def _dump_database(self, conn: sqlite3.Connection) -> Tuple[List[str], List[Tuple[str, List]]]:
        """
        Dump entire database schema and data.
        
        Returns:
            schema: List of CREATE statements
            data: List of (table_name, rows) tuples
        """
        cursor = conn.cursor()
        
        # get all table names (excluding sqlite internal tables)
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # get schema (CREATE statements)
        schema = []
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        for row in cursor.fetchall():
            if row[0]:  # sql might be None for some tables
                schema.append(row[0])
        
        # get all data
        data = []
        for table in tables:
            # validate table name is a safe identifier
            if not table.replace('_', '').isalnum():
                raise SQLiteSerializationError(
                    f"Invalid table name '{table}' - contains unsafe characters"
                )
            # use parameterized query would be ideal, but table names can't be parameterized
            # since table names come from sqlite_master (trusted source), this is safe
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            data.append((table, rows))
        
        return schema, data
    
    def reconstruct(self, state: Dict[str, Any]) -> SQLiteConnectionReconnector:
        """
        Reconstruct SQLite connection.
        
        Returns a SQLiteConnectionReconnector. Call reconnect() to create
        a new live connection. For in-memory databases, reconnect() will
        also restore the schema and data.
        """
        return SQLiteConnectionReconnector(state=state)


class SQLiteCursorHandler(Handler):
    """
    Serializes sqlite3.Cursor objects.
    
    Cursors are stateful objects that iterate over query results.
    We serialize the connection and cursor state.
    """
    
    type_name = "sqlite_cursor"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a sqlite3.Cursor."""
        return isinstance(obj, sqlite3.Cursor)
    
    def extract_state(self, obj: sqlite3.Cursor) -> Dict[str, Any]:
        """
        Extract cursor state.
        
        What we capture:
        - connection: The database connection (will be recursively serialized)
        - lastrowid: Last modified row ID
        - arraysize: Array size for fetchmany()
        
        NOTE: We DON'T serialize the current result set, as that's typically
        not needed and could be large. User should re-query in target process.
        """
        return {
            "connection": obj.connection,  # will be recursively serialized
            "lastrowid": obj.lastrowid,
            "arraysize": obj.arraysize,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> SQLiteCursorReconnector:
        """
        Reconstruct cursor.
        
        Returns a SQLiteCursorReconnector. Call reconnect() to create a new
        live cursor. The result set is NOT restored - you must re-execute
        your query after reconnecting.
        """
        return SQLiteCursorReconnector(state=state)

