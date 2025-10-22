"""
Handler for sqlite3 database connection objects.

SQLite connections are database handles. We serialize the database path
and optionally the schema and data, then reconnect in the target process.
"""

import sqlite3
from typing import Any, Dict, List, Tuple
from .base_class import Handler


class SQLiteSerializationError(Exception):
    """Raised when SQLite serialization fails."""
    pass


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
        # Get database path
        # Note: In Python 3.7+, we can use connection.execute("PRAGMA database_list")
        # For older versions, we try to access internal attributes
        try:
            cursor = obj.execute("PRAGMA database_list")
            db_info = cursor.fetchone()
            database_path = db_info[2] if db_info else ':memory:'
        except Exception:
            database_path = ':memory:'
        
        is_memory = database_path == ':memory:' or database_path == ''
        
        # Get connection settings
        isolation_level = obj.isolation_level
        
        # For in-memory databases, we need to dump schema and data
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
        
        # Get all table names (excluding sqlite internal tables)
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get schema (CREATE statements)
        schema = []
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)
        for row in cursor.fetchall():
            if row[0]:  # sql might be None for some tables
                schema.append(row[0])
        
        # Get all data
        data = []
        for table in tables:
            # Validate table name is a safe identifier
            if not table.replace('_', '').isalnum():
                raise SQLiteSerializationError(
                    f"Invalid table name '{table}' - contains unsafe characters"
                )
            # Use parameterized query would be ideal, but table names can't be parameterized
            # Since table names come from sqlite_master (trusted source), this is safe
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            data.append((table, rows))
        
        return schema, data
    
    def reconstruct(self, state: Dict[str, Any]) -> sqlite3.Connection:
        """
        Reconstruct SQLite connection.
        
        Process:
        1. Connect to database (or create new in-memory)
        2. If in-memory, restore schema and data
        3. Set connection properties
        """
        # Connect to database
        conn = sqlite3.connect(state["database"])
        
        # Set isolation level
        conn.isolation_level = state["isolation_level"]
        
        # For in-memory databases, restore schema and data
        if state["is_memory"] and (state["schema"] or state["data"]):
            cursor = conn.cursor()
            
            # Execute CREATE statements
            for create_stmt in state["schema"]:
                try:
                    cursor.execute(create_stmt)
                except sqlite3.Error as e:
                    # Table might already exist, continue
                    pass
            
            # Insert data
            for table_name, rows in state["data"]:
                if rows:
                    # Validate table name
                    if not table_name.replace('_', '').isalnum():
                        continue  # Skip invalid table names
                    
                    # Build INSERT statement
                    placeholders = ','.join('?' * len(rows[0]))
                    insert_stmt = f"INSERT INTO {table_name} VALUES ({placeholders})"
                    
                    try:
                        cursor.executemany(insert_stmt, rows)
                    except sqlite3.Error:
                        # Log error but continue
                        pass
            
            conn.commit()
        
        return conn


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
        
        Note: We DON'T serialize the current result set, as that's typically
        not needed and could be large. User should re-query in target process.
        """
        return {
            "connection": obj.connection,  # Will be recursively serialized
            "lastrowid": obj.lastrowid,
            "arraysize": obj.arraysize,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> sqlite3.Cursor:
        """
        Reconstruct cursor.
        
        Creates new cursor from the deserialized connection.
        Note: The result set is NOT restored - user must re-execute query.
        """
        # Connection has already been deserialized
        conn = state["connection"]
        
        # Create new cursor
        cursor = conn.cursor()
        cursor.arraysize = state["arraysize"]
        
        return cursor

