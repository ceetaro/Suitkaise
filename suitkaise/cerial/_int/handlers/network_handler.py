"""
Handler for network-related objects.

Includes HTTP sessions, socket connections, and other network objects.
These are challenging because network connections don't transfer across processes.
"""

import socket
from typing import Any, Dict, Optional
from .base_class import Handler

# Try to import requests, but it's optional
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None  # type: ignore


class NetworkSerializationError(Exception):
    """Raised when network object serialization fails."""
    pass


class HTTPSessionHandler(Handler):
    """
    Serializes requests.Session objects.
    
    HTTP sessions maintain cookies, authentication, and connection pooling.
    We serialize the configuration and recreate a fresh session.
    
    Important: Active connections are NOT preserved - we create a new
    session with the same configuration.
    """
    
    type_name = "http_session"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a requests.Session.
        
        We check for requests library availability.
        """
        if not HAS_REQUESTS:
            return False
        return isinstance(obj, requests.Session)
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract HTTP session state.
        
        What we capture:
        - cookies: Session cookies (as dict)
        - headers: Default headers (as dict)
        - auth: Authentication tuple (username, password) or None
        - proxies: Proxy configuration (as dict)
        - verify: SSL verification setting
        - cert: Client certificate path
        - max_redirects: Maximum number of redirects
        
        Note: We serialize configuration, not active connections.
        Connection pools are recreated fresh in the target process.
        """
        # Extract cookies
        cookies = {}
        if hasattr(obj, 'cookies'):
            try:
                cookies = dict(obj.cookies)
            except Exception:
                cookies = {}
        
        # Extract headers
        headers = dict(obj.headers) if hasattr(obj, 'headers') else {}
        
        # Extract auth (might be tuple or auth object)
        auth = obj.auth if hasattr(obj, 'auth') else None
        
        # Extract other settings
        proxies = dict(obj.proxies) if hasattr(obj, 'proxies') else {}
        verify = obj.verify if hasattr(obj, 'verify') else True
        cert = obj.cert if hasattr(obj, 'cert') else None
        
        # Get redirect settings
        max_redirects = 30  # default
        if hasattr(obj, 'max_redirects'):
            max_redirects = obj.max_redirects
        
        return {
            "cookies": cookies,
            "headers": headers,
            "auth": auth,
            "proxies": proxies,
            "verify": verify,
            "cert": cert,
            "max_redirects": max_redirects,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> 'requests.Session':  # type: ignore
        """
        Reconstruct HTTP session.
        
        Creates new session and applies saved configuration.
        """
        if not HAS_REQUESTS:
            raise NetworkSerializationError(
                "Cannot reconstruct requests.Session: 'requests' library not installed. "
                "Install it with: pip install requests"
            )
        
        # Create new session
        session = requests.Session()
        
        # Apply configuration
        session.headers.update(state["headers"])
        
        # Set cookies
        for name, value in state["cookies"].items():
            session.cookies.set(name, value)
        
        # Set other properties
        session.auth = state["auth"]
        session.proxies = state["proxies"]
        session.verify = state["verify"]
        session.cert = state["cert"]
        session.max_redirects = state["max_redirects"]
        
        return session


class SocketHandler(Handler):
    """
    Serializes socket.socket objects.
    
    Sockets are low-level network connections. We serialize connection
    parameters and attempt to reconnect.
    
    Important: The actual connection is NOT preserved. We serialize enough
    info to recreate the socket, but user must reconnect.
    """
    
    type_name = "socket"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a socket."""
        return isinstance(obj, socket.socket)
    
    def extract_state(self, obj: socket.socket) -> Dict[str, Any]:
        """
        Extract socket state.
        
        What we capture:
        - family: Address family (AF_INET, AF_INET6, etc.)
        - type: Socket type (SOCK_STREAM, SOCK_DGRAM, etc.)
        - proto: Protocol number
        - timeout: Socket timeout
        - blocking: Whether socket is blocking
        
        We DON'T capture:
        - The actual connection
        - Remote address
        - Buffer contents
        
        User must reconnect after deserialization.
        """
        return {
            "family": obj.family.value if hasattr(obj.family, 'value') else obj.family,
            "type": obj.type.value if hasattr(obj.type, 'value') else obj.type,
            "proto": obj.proto,
            "timeout": obj.gettimeout(),
            "blocking": obj.getblocking(),
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> socket.socket:
        """
        Reconstruct socket.
        
        Creates new unconnected socket with same properties.
        User must call connect() or bind() as appropriate.
        """
        # Create new socket
        sock = socket.socket(
            family=state["family"],
            type=state["type"],
            proto=state["proto"]
        )
        
        # Set timeout
        if state["timeout"] is not None:
            sock.settimeout(state["timeout"])
        
        # Set blocking mode
        sock.setblocking(state["blocking"])
        
        return sock


class DatabaseConnectionHandler(Handler):
    """
    Generic handler for database connections.
    
    Handles connections from psycopg2 (PostgreSQL), pymysql (MySQL),
    pymongo (MongoDB), redis, etc.
    
    Strategy: Extract connection parameters for documentation purposes.
    Note: Actual reconnection requires passwords which we don't serialize for security.
    """
    
    type_name = "db_connection"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a database connection.
        
        We check for common database connection types.
        """
        obj_type_name = type(obj).__name__.lower()
        obj_module = getattr(type(obj), '__module__', '').lower()
        
        # Check for known database connection types
        db_keywords = ['connection', 'client', 'redis', 'mongo']
        db_modules = ['psycopg2', 'pymysql', 'pymongo', 'redis', 'mysql']
        
        has_db_keyword = any(kw in obj_type_name for kw in db_keywords)
        has_db_module = any(mod in obj_module for mod in db_modules)
        
        return has_db_keyword and has_db_module
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract database connection parameters.
        
        This is challenging because each database library has different
        attributes for connection parameters. We try common patterns.
        """
        state = {
            "module": type(obj).__module__,
            "class_name": type(obj).__name__,
        }
        
        # Try to extract connection parameters (varies by library)
        # PostgreSQL (psycopg2)
        if hasattr(obj, 'info'):
            try:
                state["host"] = obj.info.host
                state["port"] = obj.info.port
                state["dbname"] = obj.info.dbname
                state["user"] = obj.info.user
            except (AttributeError, Exception):
                pass
        
        # MySQL (pymysql/mysql-connector)
        if hasattr(obj, 'host'):
            state["host"] = obj.host
        if hasattr(obj, 'port'):
            state["port"] = obj.port
        if hasattr(obj, 'user'):
            state["user"] = obj.user
        if hasattr(obj, 'db') or hasattr(obj, 'database'):
            state["database"] = getattr(obj, 'db', getattr(obj, 'database', None))
        
        # Redis
        if hasattr(obj, 'connection_pool'):
            pool = obj.connection_pool
            if hasattr(pool, 'connection_kwargs'):
                state["connection_kwargs"] = pool.connection_kwargs
        
        return state
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct database connection.
        
        This is not implemented for security reasons - database passwords
        should not be serialized. Users should:
        1. Use custom __serialize__/__deserialize__ methods on their database wrapper class
        2. Store connection config separately and reconnect manually
        3. Use connection pools that handle reconnection automatically
        
        For internal multiprocessing use, consider passing connection parameters
        separately and having each process create its own connection.
        """
        raise NetworkSerializationError(
            f"Cannot automatically reconstruct {state['class_name']} connection. "
            f"Database passwords are not serialized for security reasons. "
            f"For multiprocessing, each process should create its own database connection. "
            f"You can implement custom __serialize__/__deserialize__ methods if needed."
        )

