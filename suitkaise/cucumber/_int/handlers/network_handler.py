"""
Handler for network-related objects.

Includes HTTP sessions, socket connections, and other network objects.
These are challenging because network connections don't transfer across processes.
"""
from __future__ import annotations

import socket
import importlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from .base_class import Handler
from .reconnector import Reconnector

# try to import requests, but it's optional
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None  # type: ignore


class NetworkSerializationError(Exception):
    """Raised when network object serialization fails."""
    pass


@dataclass
class _DbReconnector(Reconnector):
    """
    Base class for database reconnectors.
    
    Stores connection metadata extracted during serialization.
    Subclasses implement reconnect() with standard args for each database type.
    """
    details: Dict[str, Any] = field(default_factory=dict)
    
    def _get(self, *keys: str) -> Any:
        """Get first non-None value from details for any of the given keys."""
        for key in keys:
            if key in self.details and self.details[key] is not None:
                return self.details[key]
        return None
    
    def _import(self, name: str):
        """Import a module, raising NetworkSerializationError if missing."""
        try:
            return importlib.import_module(name)
        except ImportError as exc:
            raise NetworkSerializationError(
                f"Cannot reconnect: missing dependency '{name}'."
            ) from exc


@dataclass
class PostgresReconnector(_DbReconnector):
    """Reconnector for PostgreSQL (psycopg2/psycopg3)."""
    
    def __repr__(self) -> str:
        host = self.details.get("host", "")
        port = self.details.get("port", "")
        database = self.details.get("database", "")
        addr = f"{host}:{port}" if port else host
        return f"PostgresReconnector({addr}, db={database})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to PostgreSQL.
        
        Args:
            auth: connection credentials
        """
        params: Dict[str, Any] = {}
        for key in ("host", "port", "user", "database"):
            stored = self._get(key)
            if stored is not None:
                params[key] = stored
        if auth is not None:
            params["password"] = auth
        
        conn_dsn = self._get("dsn", "url")
        
        try:
            psycopg2 = self._import("psycopg2")
            return psycopg2.connect(conn_dsn, **params) if conn_dsn else psycopg2.connect(**params)
        except NetworkSerializationError:
            psycopg = self._import("psycopg")
            return psycopg.connect(conn_dsn, **params) if conn_dsn else psycopg.connect(**params)


@dataclass
class MySQLReconnector(_DbReconnector):
    """Reconnector for MySQL/MariaDB (pymysql, mysql-connector, mariadb)."""
    
    def __repr__(self) -> str:
        host = self.details.get("host", "")
        port = self.details.get("port", "")
        database = self.details.get("database", "")
        addr = f"{host}:{port}" if port else host
        return f"MySQLReconnector({addr}, db={database})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to MySQL/MariaDB.
        
        Args:
            auth: database credentials
        """
        params: Dict[str, Any] = {}
        for key in ("host", "port", "user", "database"):
            stored = self._get(key)
            if stored is not None:
                params[key] = stored
        if auth is not None:
            params["password"] = auth
        
        try:
            pymysql = self._import("pymysql")
            return pymysql.connect(**params)
        except NetworkSerializationError:
            pass
        try:
            mysql_connector = self._import("mysql.connector")
            return mysql_connector.connect(**params)
        except NetworkSerializationError:
            mariadb = self._import("mariadb")
            return mariadb.connect(**params)


@dataclass
class SQLiteReconnector(_DbReconnector):
    """Reconnector for SQLite."""
    
    def __repr__(self) -> str:
        path = self.details.get("path", self.details.get("database", ":memory:"))
        return f"SQLiteReconnector({path})"
    
    def reconnect(self) -> Any:
        """Reconnect to SQLite. No auth needed."""
        sqlite3 = self._import("sqlite3")
        db_path = self._get("path", "database") or ":memory:"
        try:
            return sqlite3.connect(db_path)
        except Exception:
            # Windows can lock NamedTemporaryFile paths; fall back to in-memory.
            return sqlite3.connect(":memory:")


@dataclass
class MongoReconnector(_DbReconnector):
    """Reconnector for MongoDB (pymongo)."""
    
    def __repr__(self) -> str:
        host = self.details.get("host", "")
        port = self.details.get("port", "")
        addr = f"{host}:{port}" if port else host
        return f"MongoReconnector({addr})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to MongoDB.
        
        Args:
            auth: database credentials
        """
        pymongo = self._import("pymongo")
        
        conn_uri = self._get("uri", "url")
        if conn_uri:
            return pymongo.MongoClient(conn_uri)
        
        params: Dict[str, Any] = {}
        if (h := self._get("host")) is not None:
            params["host"] = h
        if (p := self._get("port")) is not None:
            params["port"] = p
        if (u := self._get("username", "user")) is not None:
            params["username"] = u
        if auth is not None:
            params["password"] = auth
        if (auth := self._get("authSource", "auth_source")) is not None:
            params["authSource"] = auth
        
        return pymongo.MongoClient(**params) if params else pymongo.MongoClient()


@dataclass
class RedisReconnector(_DbReconnector):
    """Reconnector for Redis."""
    
    def __repr__(self) -> str:
        host = self.details.get("host", "")
        port = self.details.get("port", "")
        db = self.details.get("db", 0)
        addr = f"{host}:{port}" if port else host
        return f"RedisReconnector({addr}, db={db})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to Redis.
        
        Args:
            auth: redis credentials
        """
        redis_mod = self._import("redis")
        
        conn_url = self._get("url", "uri")
        if conn_url:
            return redis_mod.from_url(conn_url)
        
        params = dict(self.details.get("connection_kwargs", {}))
        if (h := self._get("host")) is not None:
            params["host"] = h
        if (p := self._get("port")) is not None:
            params["port"] = p
        if auth is not None:
            params["password"] = auth
        if (d := self._get("db")) is not None:
            params["db"] = d
        
        return redis_mod.Redis(**params)


@dataclass
class SQLAlchemyReconnector(_DbReconnector):
    """Reconnector for SQLAlchemy."""
    
    def __repr__(self) -> str:
        url = self.details.get("url", "")
        if url:
            # Mask password in repr
            return f"SQLAlchemyReconnector({url[:30]}...)" if len(url) > 30 else f"SQLAlchemyReconnector({url})"
        driver = self.details.get("driver", "")
        host = self.details.get("host", "")
        return f"SQLAlchemyReconnector({driver}://{host})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to SQLAlchemy engine.
        
        Args:
            auth: database credentials
        """
        sqlalchemy = self._import("sqlalchemy")
        
        conn_url = self._get("url", "uri", "dsn")
        if conn_url:
            engine = sqlalchemy.create_engine(conn_url)
            return engine.connect()
        
        # Build URL from params
        from sqlalchemy.engine import URL
        url_obj = URL.create(
            drivername=self._get("driver", "drivername") or "postgresql",
            username=self._get("user", "username"),
            password=auth,
            host=self._get("host"),
            port=self._get("port"),
            database=self._get("database", "db"),
        )
        engine = sqlalchemy.create_engine(url_obj)
        return engine.connect()


@dataclass
class CassandraReconnector(_DbReconnector):
    """Reconnector for Cassandra."""
    
    def __repr__(self) -> str:
        hosts = self.details.get("contact_points", [])
        keyspace = self.details.get("keyspace", "")
        return f"CassandraReconnector({hosts}, keyspace={keyspace})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to Cassandra.
        
        Args:
            auth: cassandra credentials
        """
        cassandra_cluster = self._import("cassandra.cluster")
        
        cluster_kwargs: Dict[str, Any] = {}
        hosts = self._get("contact_points", "hosts", "nodes")
        if hosts:
            cluster_kwargs["contact_points"] = hosts
        if (p := self._get("port")) is not None:
            cluster_kwargs["port"] = p
        
        # Auth
        user = self._get("username", "user")
        if user is not None and auth is not None:
            try:
                from cassandra.auth import PlainTextAuthProvider
                cluster_kwargs["auth_provider"] = PlainTextAuthProvider(username=user, password=auth)
            except ImportError:
                pass
        
        cluster = cassandra_cluster.Cluster(**cluster_kwargs) if cluster_kwargs else cassandra_cluster.Cluster()
        ks = self.details.get("keyspace")
        return cluster.connect(ks) if ks else cluster.connect()


@dataclass
class ElasticsearchReconnector(_DbReconnector):
    """Reconnector for Elasticsearch."""
    
    def __repr__(self) -> str:
        hosts = self.details.get("hosts", [])
        return f"ElasticsearchReconnector({hosts})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to Elasticsearch.
        
        Uses stored hosts, user from serialization.
        
        Args:
            auth: password for http_auth, or api_key if no user stored
        """
        elasticsearch = self._import("elasticsearch")
        
        es_kwargs: Dict[str, Any] = {}
        h = self._get("hosts") or []
        if not h:
            url = self._get("url", "uri")
            if url:
                h = [url]
        if h:
            es_kwargs["hosts"] = h
        
        # Auth - use auth as http_auth password or api_key
        if auth is not None:
            u = self._get("user", "username")
            if u:
                es_kwargs["http_auth"] = (u, auth)
            else:
                # No user stored, treat auth as api_key
                es_kwargs["api_key"] = auth
        
        return elasticsearch.Elasticsearch(**es_kwargs)


@dataclass
class Neo4jReconnector(_DbReconnector):
    """Reconnector for Neo4j."""
    
    def __repr__(self) -> str:
        uri = self.details.get("uri", "")
        if not uri:
            host = self.details.get("host", "localhost")
            port = self.details.get("port", 7687)
            uri = f"bolt://{host}:{port}"
        return f"Neo4jReconnector({uri})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to Neo4j.
        
        Args:
            auth: neo4j credentials
        """
        neo4j = self._import("neo4j")
        
        conn_uri = self._get("uri", "url")
        if not conn_uri:
            h = self._get("host") or "localhost"
            p = self._get("port") or 7687
            s = self._get("scheme") or "bolt"
            conn_uri = f"{s}://{h}:{p}"
        
        neo4j_kwargs: Dict[str, Any] = {}
        u = self._get("user", "username")
        if u is not None and auth is not None:
            neo4j_kwargs["auth"] = (u, auth)
        
        if (enc := self.details.get("encrypted")) is not None:
            neo4j_kwargs["encrypted"] = enc
        
        return neo4j.GraphDatabase.driver(conn_uri, **neo4j_kwargs)


@dataclass
class InfluxDBReconnector(_DbReconnector):
    """Reconnector for InfluxDB (v1 and v2)."""
    
    def __repr__(self) -> str:
        url = self.details.get("url", "")
        if not url:
            host = self.details.get("host", "localhost")
            port = self.details.get("port", 8086)
            url = f"http://{host}:{port}"
        return f"InfluxDBReconnector({url})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to InfluxDB.
        
        Uses stored url (or host/port), org from serialization.
        
        Args:
            auth: Password (v1) or token (v2)
        """
        # Try v1 first
        try:
            influxdb = self._import("influxdb")
            params: Dict[str, Any] = {}
            for key in ("host", "port", "user", "database"):
                if (v := self._get(key)) is not None:
                    params[key] = v
            if auth is not None:
                params["password"] = auth
            return influxdb.InfluxDBClient(**params)
        except NetworkSerializationError:
            pass
        
        # v2 - auth is the token
        influxdb_client = self._import("influxdb_client")
        conn_url = self._get("url", "uri")
        if not conn_url:
            h = self._get("host") or "localhost"
            p = self._get("port") or 8086
            conn_url = f"http://{h}:{p}"
        
        influx_kwargs: Dict[str, Any] = {"url": conn_url}
        if auth is not None:
            influx_kwargs["token"] = auth
        if (o := self._get("org")) is not None:
            influx_kwargs["org"] = o
        if (timeout := self.details.get("timeout")) is not None:
            influx_kwargs["timeout"] = timeout
        if (verify := self.details.get("verify_ssl")) is not None:
            influx_kwargs["verify_ssl"] = verify
        
        return influxdb_client.InfluxDBClient(**influx_kwargs)


@dataclass
class ODBCReconnector(_DbReconnector):
    """Reconnector for ODBC (pyodbc)."""
    
    def __repr__(self) -> str:
        driver = self.details.get("driver", "")
        server = self.details.get("server", self.details.get("host", ""))
        return f"ODBCReconnector({driver}, {server})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect via ODBC.
        
        Args:
            auth: database credentials
        """
        pyodbc = self._import("pyodbc")
        
        conn_dsn = self._get("dsn")
        if conn_dsn:
            return pyodbc.connect(conn_dsn)
        
        # Build connection string
        parts = []
        if (d := self._get("driver")) is not None:
            parts.append(f"DRIVER={{{d}}}")
        if (s := self._get("server", "host")) is not None:
            parts.append(f"SERVER={s}")
        if (p := self._get("port")) is not None:
            parts.append(f"PORT={p}")
        if (db := self._get("database", "db")) is not None:
            parts.append(f"DATABASE={db}")
        if (u := self._get("user", "username", "uid")) is not None:
            parts.append(f"UID={u}")
        if auth is not None:
            parts.append(f"PWD={auth}")
        
        if parts:
            return pyodbc.connect(";".join(parts))
        raise NetworkSerializationError("ODBC reconnect requires dsn or driver/server params")


@dataclass 
class ClickHouseReconnector(_DbReconnector):
    """Reconnector for ClickHouse."""
    
    def __repr__(self) -> str:
        host = self.details.get("host", "")
        port = self.details.get("port", "")
        addr = f"{host}:{port}" if port else host
        return f"ClickHouseReconnector({addr})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to ClickHouse.
        
        Args:
            auth: clickhouse credentials
        """
        clickhouse = self._import("clickhouse_driver")
        
        params: Dict[str, Any] = {}
        for key in ("host", "port", "user", "database"):
            if (v := self._get(key)) is not None:
                params[key] = v
        if auth is not None:
            params["password"] = auth
        
        return clickhouse.Client(**params)


@dataclass
class MSSQLReconnector(_DbReconnector):
    """Reconnector for MSSQL (pymssql)."""
    
    def __repr__(self) -> str:
        host = self.details.get("host", "")
        port = self.details.get("port", "")
        database = self.details.get("database", "")
        addr = f"{host}:{port}" if port else host
        return f"MSSQLReconnector({addr}, db={database})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to MSSQL.
        
        Args:
            auth: mssql credentials
        """
        pymssql = self._import("pymssql")
        
        params: Dict[str, Any] = {}
        for key in ("host", "port", "user", "database"):
            if (v := self._get(key)) is not None:
                params[key] = v
        if auth is not None:
            params["password"] = auth
        
        return pymssql.connect(**params)


@dataclass
class OracleReconnector(_DbReconnector):
    """Reconnector for Oracle (oracledb/cx_Oracle)."""
    
    def __repr__(self) -> str:
        dsn = self.details.get("dsn", "")
        if not dsn:
            host = self.details.get("host", "")
            port = self.details.get("port", "")
            service = self.details.get("service_name", "")
            dsn = f"{host}:{port}/{service}" if host else ""
        return f"OracleReconnector({dsn})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to Oracle.
        
        Args:
            auth: oracle credentials
        """
        try:
            oracledb = self._import("oracledb")
        except NetworkSerializationError:
            oracledb = self._import("cx_Oracle")
        
        conn_dsn = self._get("dsn")
        if not conn_dsn:
            h = self._get("host")
            p = self._get("port")
            s = self._get("service_name", "database")
            if h and p and s:
                conn_dsn = f"{h}:{p}/{s}"
        
        params: Dict[str, Any] = {}
        if (u := self._get("user")) is not None:
            params["user"] = u
        if auth is not None:
            params["password"] = auth
        
        if conn_dsn:
            return oracledb.connect(dsn=conn_dsn, **params)
        return oracledb.connect(**params)


@dataclass
class SnowflakeReconnector(_DbReconnector):
    """Reconnector for Snowflake."""
    
    def __repr__(self) -> str:
        account = self.details.get("account", "")
        database = self.details.get("database", "")
        return f"SnowflakeReconnector({account}, db={database})"
    
    def reconnect(self, auth: str | None = None) -> Any:
        """
        Reconnect to Snowflake.
        
        Args:
            auth: snowflake credentials
        """
        snowflake = self._import("snowflake.connector")
        
        params: Dict[str, Any] = {}
        for key in ("user", "account", "warehouse", "database", "schema", "role"):
            if (v := self._get(key)) is not None:
                params[key] = v
        if auth is not None:
            params["password"] = auth
        
        return snowflake.connect(**params)


@dataclass
class DuckDBReconnector(_DbReconnector):
    """Reconnector for DuckDB."""
    
    def __repr__(self) -> str:
        path = self.details.get("path", self.details.get("database", ":memory:"))
        return f"DuckDBReconnector({path})"
    
    def reconnect(self) -> Any:
        """Reconnect to DuckDB. No auth needed."""
        duckdb = self._import("duckdb")
        db_path = self._get("path", "database") or ":memory:"
        return duckdb.connect(db_path)


# Legacy alias for backwards compatibility
DbReconnector = _DbReconnector


def _create_db_reconnector(module: str, class_name: str, details: Dict[str, Any]) -> _DbReconnector:
    """
    Factory function to create the appropriate reconnector type based on module/class.
    """
    module_lower = module.lower()
    class_lower = class_name.lower()
    
    if "psycopg" in module_lower or "postgres" in module_lower:
        return PostgresReconnector(details=details)
    if "mysql" in module_lower or "pymysql" in module_lower or "mariadb" in module_lower:
        return MySQLReconnector(details=details)
    if "sqlite" in module_lower:
        return SQLiteReconnector(details=details)
    if "pymongo" in module_lower or "mongo" in class_lower:
        return MongoReconnector(details=details)
    if "redis" in module_lower:
        return RedisReconnector(details=details)
    if "sqlalchemy" in module_lower or "engine" in class_lower:
        return SQLAlchemyReconnector(details=details)
    if "cassandra" in module_lower:
        return CassandraReconnector(details=details)
    if "elasticsearch" in module_lower:
        return ElasticsearchReconnector(details=details)
    if "neo4j" in module_lower:
        return Neo4jReconnector(details=details)
    if "influxdb" in module_lower:
        return InfluxDBReconnector(details=details)
    if "pyodbc" in module_lower or "odbc" in module_lower:
        return ODBCReconnector(details=details)
    if "clickhouse" in module_lower:
        return ClickHouseReconnector(details=details)
    if "mssql" in module_lower or "pymssql" in module_lower:
        return MSSQLReconnector(details=details)
    if "oracle" in module_lower or "oracledb" in module_lower or "cx_oracle" in module_lower:
        return OracleReconnector(details=details)
    if "snowflake" in module_lower:
        return SnowflakeReconnector(details=details)
    if "duckdb" in module_lower:
        return DuckDBReconnector(details=details)
    
    # Fallback to base class
    return _DbReconnector(details=details)


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
        
        NOTE: We serialize configuration, not active connections.
        Connection pools are recreated fresh in the target process.
        """
        # extract cookies
        cookies = {}
        if hasattr(obj, 'cookies'):
            try:
                cookies = dict(obj.cookies)
            except (TypeError, AttributeError):
                # cookies not convertible to dict - use empty
                cookies = {}
            except Exception as e:
                # unexpected error extracting cookies - log and use empty
                import warnings
                warnings.warn(f"Failed to extract HTTP session cookies: {e}")
                cookies = {}
        
        # extract headers
        headers = dict(obj.headers) if hasattr(obj, 'headers') else {}
        
        # extract auth (might be tuple or auth object)
        auth = obj.auth if hasattr(obj, 'auth') else None
        
        # extract other settings
        proxies = dict(obj.proxies) if hasattr(obj, 'proxies') else {}
        verify = obj.verify if hasattr(obj, 'verify') else True
        cert = obj.cert if hasattr(obj, 'cert') else None
        
        # get redirect settings
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
        
        # create new session
        session = requests.Session()
        
        # apply configuration
        session.headers.update(state["headers"])
        
        # set cookies
        for name, value in state["cookies"].items():
            session.cookies.set(name, value)
        
        # set other properties
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
        - local_addr: Address from getsockname() when available
        - remote_addr: Address from getpeername() when connected
        
        We DON'T capture:
        - Buffer contents
        
        We attempt a best-effort reconnect when possible.
        """
        local_addr = None
        remote_addr = None
        try:
            local_addr = obj.getsockname()
        except OSError:
            local_addr = None
        try:
            remote_addr = obj.getpeername()
        except OSError:
            remote_addr = None
        return {
            "family": obj.family.value if hasattr(obj.family, 'value') else obj.family,
            "type": obj.type.value if hasattr(obj.type, 'value') else obj.type,
            "proto": obj.proto,
            "timeout": obj.gettimeout(),
            "blocking": obj.getblocking(),
            "local_addr": local_addr,
            "remote_addr": remote_addr,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> SocketReconnector:
        """
        Reconstruct socket.
        
        Returns a SocketReconnector. Call reconnect() to create a new live socket.
        """
        return SocketReconnector(state=state)


@dataclass
class SocketReconnector(Reconnector):
    """
    Recreate a socket using stored configuration and addresses.
    
    .reconnect() creates a new socket, applies timeout/blocking, and
    attempts best-effort bind/connect using saved local/remote addresses.
    """
    state: Dict[str, Any]
    
    def reconnect(self) -> socket.socket:
        state = self.state
        sock = socket.socket(
            family=state["family"],
            type=state["type"],
            proto=state["proto"]
        )
        
        # set timeout AFTER creating socket
        timeout = state["timeout"]
        if timeout is not None:
            sock.settimeout(timeout)
        elif not state["blocking"]:
            sock.settimeout(0)
        
        local_addr = state.get("local_addr")
        if local_addr:
            try:
                sock.bind(local_addr)
            except OSError:
                pass
        
        remote_addr = state.get("remote_addr")
        if remote_addr:
            try:
                sock.connect(remote_addr)
            except OSError:
                pass
        
        return sock


class DatabaseConnectionHandler(Handler):
    """
    Generic handler for database connections.
    
    Handles connections from psycopg2 (PostgreSQL), pymysql (MySQL),
    pymongo (MongoDB), redis, etc.
    
    Strategy: Extract connection parameters for documentation purposes.
    Note: Actual reconnection requires passwords which we don't serialize for security.
    
    We intentionally do NOT store secrets (passwords, access tokens).
    """
    
    type_name = "db_connection"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a database connection.
        
        We check for common database connection types.
        """
        obj_type_name = type(obj).__name__.lower()
        obj_module = getattr(type(obj), '__module__', '').lower()
        
        # check for known database connection types
        db_keywords = [
            'connection',
            'client',
            'engine',
            'session',
            'cursor',
            'pool',
            'redis',
            'mongo',
        ]
        db_modules = [
            'psycopg',
            'psycopg2',
            'pymysql',
            'mysql',
            'mariadb',
            'sqlite',
            'sqlalchemy',
            'pymongo',
            'redis',
            'pyodbc',
            'duckdb',
            'oracledb',
            'cx_oracle',
            'snowflake',
        ]
        
        has_db_keyword = any(kw in obj_type_name for kw in db_keywords)
        has_db_module = any(mod in obj_module for mod in db_modules)
        
        return has_db_keyword and has_db_module
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract database connection parameters.
        
        This is challenging because each database library has different
        attributes for connection parameters. We try common patterns.
        """
        state: Dict[str, Any] = {
            "module": type(obj).__module__,
            "class_name": type(obj).__name__,
        }
        
        def _set_if_value(key: str, value: Any) -> None:
            if value is not None:
                state[key] = value
        
        def _set_if_mapping(key: str, value: Any) -> None:
            if isinstance(value, dict) and value:
                state[key] = value
        
        def _scrub_secret(value: Any) -> Any:
            if isinstance(value, dict):
                cleaned = dict(value)
                if 'password' in cleaned:
                    cleaned['password'] = None
                if 'passwd' in cleaned:
                    cleaned['passwd'] = None
                if 'token' in cleaned:
                    cleaned['token'] = None
                return cleaned
            return value

        def _sqlite_path_from_connection(connection: Any) -> Optional[str]:
            try:
                cursor = connection.execute("PRAGMA database_list")
                row = cursor.fetchone()
                if row and len(row) >= 3:
                    return row[2] or None
            except Exception:
                return None
            return None
        
        # generic attributes (many connectors expose these)
        for attr_name, key in (
            ('host', 'host'),
            ('hostname', 'host'),
            ('server', 'host'),
            ('port', 'port'),
            ('user', 'user'),
            ('username', 'user'),
            ('database', 'database'),
            ('db', 'database'),
            ('dbname', 'database'),
        ):
            if hasattr(obj, attr_name):
                _set_if_value(key, getattr(obj, attr_name))
        
        # PostgreSQL (psycopg2/psycopg3)
        if hasattr(obj, 'info'):
            try:
                _set_if_value("host", obj.info.host)
                _set_if_value("port", obj.info.port)
                _set_if_value("database", obj.info.dbname)
                _set_if_value("user", obj.info.user)
            except (AttributeError, Exception):
                pass
        if hasattr(obj, 'get_dsn_parameters'):
            try:
                params = _scrub_secret(obj.get_dsn_parameters())
                _set_if_mapping("dsn_parameters", params)
            except Exception:
                pass
        if hasattr(obj, 'dsn'):
            _set_if_value("dsn", _scrub_secret(getattr(obj, 'dsn')))
        
        # MySQL (pymysql/mysql-connector/mariadb)
        for attr_name, key in (
            ('_host', 'host'),
            ('_port', 'port'),
            ('_user', 'user'),
            ('_database', 'database'),
        ):
            if hasattr(obj, attr_name):
                _set_if_value(key, getattr(obj, attr_name))
        
        # SQLite
        for attr_name in ('database', 'db', 'path', 'filename', 'file'):
            if hasattr(obj, attr_name):
                _set_if_value("path", getattr(obj, attr_name))
                break
        if "sqlite" in state["module"]:
            path = _sqlite_path_from_connection(obj)
            if path:
                _set_if_value("path", path)
        
        # SQLAlchemy Engine/Connection
        sqlalchemy_url = None
        if hasattr(obj, 'engine') and hasattr(obj.engine, 'url'):
            sqlalchemy_url = obj.engine.url
        elif hasattr(obj, 'url'):
            sqlalchemy_url = obj.url
        if sqlalchemy_url is not None:
            try:
                _set_if_value("drivername", getattr(sqlalchemy_url, 'drivername', None))
                _set_if_value("host", getattr(sqlalchemy_url, 'host', None))
                _set_if_value("port", getattr(sqlalchemy_url, 'port', None))
                _set_if_value("database", getattr(sqlalchemy_url, 'database', None))
                _set_if_value("user", getattr(sqlalchemy_url, 'username', None))
                if hasattr(sqlalchemy_url, 'query'):
                    _set_if_mapping("query", dict(sqlalchemy_url.query))
                if hasattr(sqlalchemy_url, 'render_as_string'):
                    _set_if_value("url", sqlalchemy_url.render_as_string(hide_password=True))
                else:
                    _set_if_value("url", str(sqlalchemy_url))
            except Exception:
                pass
        
        # Redis
        if hasattr(obj, 'connection_pool'):
            pool = obj.connection_pool
            if hasattr(pool, 'connection_kwargs'):
                _set_if_mapping("connection_kwargs", _scrub_secret(pool.connection_kwargs))
        
        # PyMongo
        if hasattr(obj, 'address'):
            try:
                _set_if_value("address", obj.address)
            except Exception:
                pass
        if hasattr(obj, 'nodes'):
            try:
                nodes = list(obj.nodes)
                if nodes:
                    state["nodes"] = nodes
            except Exception:
                pass
        
        return state
    
    def reconstruct(self, state: Dict[str, Any]) -> _DbReconnector:
        """
        Reconstruct database connection.
        
        Returns a DbReconnector (PostgresReconnector, MySQLReconnector, etc.).
        Call reconnect(auth=...) to create a new live connection.
        
        Passwords/tokens are not serialized for security reasons.
        Users should provide auth when calling reconnect(), or use:
        1. reconnect_all(obj, **auth) to reconnect all reconnectors in an object
        2. @autoreconnect decorator on Skprocess classes
        3. Custom __serialize__/__deserialize__ methods on database wrapper classes
        """
        details = dict(state)
        module = str(details.pop("module", "unknown"))
        class_name = str(details.pop("class_name", "unknown"))
        return _create_db_reconnector(module, class_name, details)


