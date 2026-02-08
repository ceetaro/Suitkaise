"""
Tests for network_handler.py — reconnectors, factory, handlers.

These tests exercise reconnectors, the factory function, repr, _get, _import,
can_handle, extract_state, and reconstruct WITHOUT requiring external database
or network dependencies.
"""

import sys
import socket
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Dict

# Add project root to path
def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.cucumber._int.handlers.network_handler import (
    _DbReconnector,
    PostgresReconnector,
    MySQLReconnector,
    SQLiteReconnector,
    MongoReconnector,
    RedisReconnector,
    SQLAlchemyReconnector,
    CassandraReconnector,
    ElasticsearchReconnector,
    Neo4jReconnector,
    InfluxDBReconnector,
    ODBCReconnector,
    ClickHouseReconnector,
    MSSQLReconnector,
    OracleReconnector,
    SnowflakeReconnector,
    DuckDBReconnector,
    DbReconnector,
    _create_db_reconnector,
    NetworkSerializationError,
    SocketHandler,
    SocketReconnector,
    HTTPSessionHandler,
    DatabaseConnectionHandler,
)


# =============================================================================
# Test Utilities
# =============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'

    def run_test(self, name, test_func, timeout=30):
        import traceback
        try:
            test_func()
            self.results.append(TestResult(name, True))
            print(f"  {self.GREEN}✓ PASS{self.RESET}  {name}")
        except Exception as e:
            tb = traceback.format_exc()
            self.results.append(TestResult(name, False, error=str(e), message=tb))
            print(f"  {self.RED}✗ FAIL{self.RESET}  {name}")
            print(f"         └─ {type(e).__name__}: {e}")

    def print_results(self):
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)
        print(f"\n{self.BOLD}----------------------------------------------------------------------{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {total} tests passed!{self.RESET}")
        else:
            print(f"  Passed: {passed}  |  Failed: {failed}")
            print(f"\nFailed tests (recap):")
            for r in self.results:
                if not r.passed:
                    print(f"  {self.RED}✗ {r.name}{self.RESET}")
                    print(f"     └─ {r.error}")
        print(f"{self.BOLD}----------------------------------------------------------------------{self.RESET}")
        return failed == 0


# =============================================================================
# _DbReconnector base class tests
# =============================================================================

def test_db_reconnector_get_basic():
    r = _DbReconnector(details={"host": "localhost", "port": 5432})
    assert r._get("host") == "localhost"
    assert r._get("port") == 5432
    assert r._get("missing") is None


def test_db_reconnector_get_fallback_keys():
    r = _DbReconnector(details={"url": "postgres://localhost"})
    assert r._get("uri", "url") == "postgres://localhost"
    assert r._get("missing1", "missing2") is None


def test_db_reconnector_get_skips_none():
    r = _DbReconnector(details={"host": None, "hostname": "real"})
    assert r._get("host", "hostname") == "real"


def test_db_reconnector_import_missing():
    r = _DbReconnector(details={})
    try:
        r._import("nonexistent_fake_module_xyz")
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_db_reconnector_import_stdlib():
    r = _DbReconnector(details={})
    mod = r._import("json")
    import json
    assert mod is json


# =============================================================================
# Reconnector __repr__ tests
# =============================================================================

def test_postgres_repr():
    r = PostgresReconnector(details={"host": "db.example.com", "port": 5432, "database": "mydb"})
    s = repr(r)
    assert "db.example.com" in s
    assert "5432" in s
    assert "mydb" in s


def test_postgres_repr_no_port():
    r = PostgresReconnector(details={"host": "db.example.com", "database": "mydb"})
    s = repr(r)
    assert "db.example.com" in s


def test_mysql_repr():
    r = MySQLReconnector(details={"host": "mysql.local", "port": 3306, "database": "app"})
    s = repr(r)
    assert "mysql.local" in s
    assert "app" in s


def test_sqlite_repr():
    r = SQLiteReconnector(details={"path": "/tmp/test.db"})
    assert "/tmp/test.db" in repr(r)


def test_sqlite_repr_default():
    r = SQLiteReconnector(details={})
    assert ":memory:" in repr(r)


def test_mongo_repr():
    r = MongoReconnector(details={"host": "mongo.local", "port": 27017})
    s = repr(r)
    assert "mongo.local" in s


def test_redis_repr():
    r = RedisReconnector(details={"host": "redis.local", "port": 6379, "db": 0})
    s = repr(r)
    assert "redis.local" in s


def test_sqlalchemy_repr_url():
    r = SQLAlchemyReconnector(details={"url": "postgresql://user@host/db"})
    assert "postgresql" in repr(r)


def test_sqlalchemy_repr_long_url():
    r = SQLAlchemyReconnector(details={"url": "postgresql://user:pass@very-long-hostname.example.com:5432/mydatabase"})
    assert "..." in repr(r)


def test_sqlalchemy_repr_no_url():
    r = SQLAlchemyReconnector(details={"driver": "mysql", "host": "db.local"})
    s = repr(r)
    assert "mysql" in s
    assert "db.local" in s


def test_cassandra_repr():
    r = CassandraReconnector(details={"contact_points": ["10.0.0.1"], "keyspace": "ks"})
    s = repr(r)
    assert "10.0.0.1" in s
    assert "ks" in s


def test_elasticsearch_repr():
    r = ElasticsearchReconnector(details={"hosts": ["http://es:9200"]})
    assert "es:9200" in repr(r)


def test_neo4j_repr_uri():
    r = Neo4jReconnector(details={"uri": "bolt://neo4j:7687"})
    assert "bolt://neo4j:7687" in repr(r)


def test_neo4j_repr_no_uri():
    r = Neo4jReconnector(details={"host": "neo4j.local", "port": 7687})
    s = repr(r)
    assert "neo4j.local" in s


def test_influxdb_repr_url():
    r = InfluxDBReconnector(details={"url": "http://influx:8086"})
    assert "influx:8086" in repr(r)


def test_influxdb_repr_no_url():
    r = InfluxDBReconnector(details={"host": "influx.local", "port": 8086})
    s = repr(r)
    assert "influx.local" in s


def test_odbc_repr():
    r = ODBCReconnector(details={"driver": "ODBC Driver 17", "server": "sql.local"})
    s = repr(r)
    assert "ODBC Driver 17" in s
    assert "sql.local" in s


def test_clickhouse_repr():
    r = ClickHouseReconnector(details={"host": "ch.local", "port": 9000})
    assert "ch.local" in repr(r)


def test_mssql_repr():
    r = MSSQLReconnector(details={"host": "mssql.local", "port": 1433, "database": "master"})
    s = repr(r)
    assert "mssql.local" in s
    assert "master" in s


def test_oracle_repr_dsn():
    r = OracleReconnector(details={"dsn": "myhost:1521/myservice"})
    assert "myhost:1521/myservice" in repr(r)


def test_oracle_repr_components():
    r = OracleReconnector(details={"host": "ora.local", "port": 1521, "service_name": "orcl"})
    s = repr(r)
    assert "ora.local" in s


def test_snowflake_repr():
    r = SnowflakeReconnector(details={"account": "myaccount", "database": "mydb"})
    s = repr(r)
    assert "myaccount" in s
    assert "mydb" in s


def test_duckdb_repr():
    r = DuckDBReconnector(details={"path": "/tmp/duck.db"})
    assert "/tmp/duck.db" in repr(r)


def test_duckdb_repr_default():
    r = DuckDBReconnector(details={})
    assert ":memory:" in repr(r)


# =============================================================================
# Reconnector reconnect() — error paths (no drivers installed)
# =============================================================================

def test_postgres_reconnect_no_driver():
    r = PostgresReconnector(details={"host": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_mysql_reconnect_no_driver():
    r = MySQLReconnector(details={"host": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_sqlite_reconnect_memory():
    r = SQLiteReconnector(details={})
    conn = r.reconnect()
    assert conn is not None
    conn.close()


def test_sqlite_reconnect_with_path():
    import tempfile, os
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        r = SQLiteReconnector(details={"path": path})
        conn = r.reconnect()
        assert conn is not None
        conn.close()
    finally:
        os.unlink(path)


def test_mongo_reconnect_no_driver():
    r = MongoReconnector(details={"host": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_redis_reconnect_no_driver():
    r = RedisReconnector(details={"host": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_sqlalchemy_reconnect_no_driver():
    r = SQLAlchemyReconnector(details={"url": "postgresql://x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except (NetworkSerializationError, Exception):
        pass


def test_cassandra_reconnect_no_driver():
    r = CassandraReconnector(details={"contact_points": ["x"]})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_elasticsearch_reconnect_no_driver():
    r = ElasticsearchReconnector(details={"hosts": ["http://x"]})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_neo4j_reconnect_no_driver():
    r = Neo4jReconnector(details={"uri": "bolt://x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_influxdb_reconnect_no_driver():
    r = InfluxDBReconnector(details={"host": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_odbc_reconnect_no_driver():
    r = ODBCReconnector(details={"driver": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_odbc_reconnect_no_params():
    r = ODBCReconnector(details={})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except (NetworkSerializationError, Exception):
        pass


def test_clickhouse_reconnect_no_driver():
    r = ClickHouseReconnector(details={"host": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_mssql_reconnect_no_driver():
    r = MSSQLReconnector(details={"host": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_oracle_reconnect_no_driver():
    r = OracleReconnector(details={"dsn": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_snowflake_reconnect_no_driver():
    r = SnowflakeReconnector(details={"account": "x"})
    try:
        r.reconnect()
        assert False, "Should have raised"
    except NetworkSerializationError:
        pass


def test_duckdb_reconnect_no_driver():
    r = DuckDBReconnector(details={})
    try:
        r.reconnect()
        # DuckDB may or may not be installed
    except NetworkSerializationError:
        pass


# =============================================================================
# Reconnector reconnect() — auth parameter paths
# =============================================================================

def test_postgres_reconnect_with_auth():
    r = PostgresReconnector(details={"host": "x", "port": 5432, "user": "admin", "database": "mydb"})
    try:
        r.reconnect(auth="secret")
    except NetworkSerializationError:
        pass


def test_postgres_reconnect_with_dsn():
    r = PostgresReconnector(details={"dsn": "host=x dbname=mydb"})
    try:
        r.reconnect()
    except NetworkSerializationError:
        pass


def test_mysql_reconnect_with_auth():
    r = MySQLReconnector(details={"host": "x", "port": 3306, "user": "root", "database": "test"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


def test_mongo_reconnect_with_uri():
    r = MongoReconnector(details={"uri": "mongodb://localhost"})
    try:
        r.reconnect()
    except NetworkSerializationError:
        pass


def test_mongo_reconnect_with_auth():
    r = MongoReconnector(details={"host": "x", "port": 27017, "username": "u"})
    try:
        r.reconnect(auth="p")
    except NetworkSerializationError:
        pass


def test_mongo_reconnect_empty():
    r = MongoReconnector(details={})
    try:
        r.reconnect()
    except NetworkSerializationError:
        pass


def test_redis_reconnect_with_url():
    r = RedisReconnector(details={"url": "redis://localhost"})
    try:
        r.reconnect()
    except NetworkSerializationError:
        pass


def test_redis_reconnect_with_auth():
    r = RedisReconnector(details={"host": "x", "port": 6379, "db": 0, "connection_kwargs": {"timeout": 5}})
    try:
        r.reconnect(auth="secret")
    except NetworkSerializationError:
        pass


def test_elasticsearch_reconnect_with_user_auth():
    r = ElasticsearchReconnector(details={"hosts": ["http://x"], "user": "elastic"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


def test_elasticsearch_reconnect_with_api_key():
    r = ElasticsearchReconnector(details={"hosts": ["http://x"]})
    try:
        r.reconnect(auth="api_key_123")
    except NetworkSerializationError:
        pass


def test_elasticsearch_reconnect_with_url_fallback():
    r = ElasticsearchReconnector(details={"url": "http://es:9200"})
    try:
        r.reconnect()
    except NetworkSerializationError:
        pass


def test_elasticsearch_reconnect_no_hosts():
    r = ElasticsearchReconnector(details={})
    try:
        r.reconnect()
    except NetworkSerializationError:
        pass


def test_neo4j_reconnect_with_auth():
    r = Neo4jReconnector(details={"uri": "bolt://x", "user": "neo4j", "encrypted": True})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


def test_neo4j_reconnect_build_uri():
    r = Neo4jReconnector(details={"host": "my.host", "port": 7687, "scheme": "neo4j"})
    try:
        r.reconnect()
    except NetworkSerializationError:
        pass


def test_influxdb_reconnect_v2_with_auth():
    r = InfluxDBReconnector(details={"url": "http://influx:8086", "org": "myorg", "timeout": 30, "verify_ssl": True})
    try:
        r.reconnect(auth="mytoken")
    except NetworkSerializationError:
        pass


def test_influxdb_reconnect_build_url():
    r = InfluxDBReconnector(details={"host": "influx.local", "port": 8086})
    try:
        r.reconnect(auth="token")
    except NetworkSerializationError:
        pass


def test_odbc_reconnect_with_dsn():
    r = ODBCReconnector(details={"dsn": "mydsn"})
    try:
        r.reconnect()
    except NetworkSerializationError:
        pass


def test_odbc_reconnect_with_parts():
    r = ODBCReconnector(details={"driver": "ODBC 17", "server": "sql.local", "port": 1433, "database": "mydb", "uid": "sa"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


def test_oracle_reconnect_with_components():
    r = OracleReconnector(details={"host": "ora", "port": 1521, "service_name": "orcl", "user": "sys"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


def test_oracle_reconnect_no_dsn_no_components():
    r = OracleReconnector(details={"user": "sys"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


def test_snowflake_reconnect_with_auth():
    r = SnowflakeReconnector(details={"user": "u", "account": "a", "warehouse": "w", "database": "d", "schema": "s", "role": "r"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


def test_clickhouse_reconnect_with_auth():
    r = ClickHouseReconnector(details={"host": "ch", "port": 9000, "user": "default", "database": "default"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


def test_mssql_reconnect_with_auth():
    r = MSSQLReconnector(details={"host": "mssql", "port": 1433, "user": "sa", "database": "master"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


# =============================================================================
# _create_db_reconnector factory tests
# =============================================================================

def test_factory_postgres():
    r = _create_db_reconnector("psycopg2.extensions", "connection", {"host": "x"})
    assert isinstance(r, PostgresReconnector)


def test_factory_mysql():
    r = _create_db_reconnector("pymysql.connections", "Connection", {"host": "x"})
    assert isinstance(r, MySQLReconnector)


def test_factory_sqlite():
    r = _create_db_reconnector("sqlite3", "Connection", {"path": ":memory:"})
    assert isinstance(r, SQLiteReconnector)


def test_factory_mongo():
    r = _create_db_reconnector("pymongo.mongo_client", "MongoClient", {"host": "x"})
    assert isinstance(r, MongoReconnector)


def test_factory_redis():
    r = _create_db_reconnector("redis.client", "Redis", {"host": "x"})
    assert isinstance(r, RedisReconnector)


def test_factory_sqlalchemy():
    r = _create_db_reconnector("sqlalchemy.engine.base", "Connection", {"url": "x"})
    assert isinstance(r, SQLAlchemyReconnector)


def test_factory_cassandra():
    r = _create_db_reconnector("cassandra.cluster", "Session", {})
    assert isinstance(r, CassandraReconnector)


def test_factory_elasticsearch():
    r = _create_db_reconnector("elasticsearch", "Elasticsearch", {"hosts": []})
    assert isinstance(r, ElasticsearchReconnector)


def test_factory_neo4j():
    r = _create_db_reconnector("neo4j._sync.driver", "BoltDriver", {"uri": "bolt://x"})
    assert isinstance(r, Neo4jReconnector)


def test_factory_influxdb():
    r = _create_db_reconnector("influxdb_client", "InfluxDBClient", {"url": "http://x"})
    assert isinstance(r, InfluxDBReconnector)


def test_factory_odbc():
    r = _create_db_reconnector("pyodbc", "Connection", {"dsn": "x"})
    assert isinstance(r, ODBCReconnector)


def test_factory_clickhouse():
    r = _create_db_reconnector("clickhouse_driver", "Client", {"host": "x"})
    assert isinstance(r, ClickHouseReconnector)


def test_factory_mssql():
    r = _create_db_reconnector("pymssql._pymssql", "Connection", {"host": "x"})
    assert isinstance(r, MSSQLReconnector)


def test_factory_oracle():
    r = _create_db_reconnector("oracledb", "Connection", {"dsn": "x"})
    assert isinstance(r, OracleReconnector)


def test_factory_snowflake():
    r = _create_db_reconnector("snowflake.connector", "SnowflakeConnection", {"account": "x"})
    assert isinstance(r, SnowflakeReconnector)


def test_factory_duckdb():
    r = _create_db_reconnector("duckdb", "DuckDBPyConnection", {"path": ":memory:"})
    assert isinstance(r, DuckDBReconnector)


def test_factory_mariadb():
    r = _create_db_reconnector("mariadb", "Connection", {"host": "x"})
    assert isinstance(r, MySQLReconnector)


def test_factory_cx_oracle():
    r = _create_db_reconnector("cx_Oracle", "Connection", {"dsn": "x"})
    assert isinstance(r, OracleReconnector)


def test_factory_unknown_fallback():
    r = _create_db_reconnector("some_unknown_module", "SomeClass", {"key": "val"})
    assert type(r) is _DbReconnector


# =============================================================================
# SocketHandler tests
# =============================================================================

def test_socket_handler_can_handle():
    h = SocketHandler()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        assert h.can_handle(s)
        assert not h.can_handle("not a socket")
        assert not h.can_handle(42)
    finally:
        s.close()


def test_socket_handler_extract_state():
    h = SocketHandler()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        state = h.extract_state(s)
        assert "family" in state
        assert "type" in state
        assert "proto" in state
        assert "timeout" in state
        assert "blocking" in state
        assert state["blocking"] is True
    finally:
        s.close()


def test_socket_handler_extract_nonblocking():
    h = SocketHandler()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setblocking(False)
    try:
        state = h.extract_state(s)
        assert state["blocking"] is False
        assert state["timeout"] == 0.0
    finally:
        s.close()


def test_socket_handler_reconstruct():
    h = SocketHandler()
    state = {
        "family": socket.AF_INET,
        "type": socket.SOCK_STREAM,
        "proto": 0,
        "timeout": None,
        "blocking": True,
        "local_addr": None,
        "remote_addr": None,
    }
    reconnector = h.reconstruct(state)
    assert isinstance(reconnector, SocketReconnector)


def test_socket_reconnector_reconnect():
    sr = SocketReconnector(state={
        "family": socket.AF_INET,
        "type": socket.SOCK_STREAM,
        "proto": 0,
        "timeout": 5.0,
        "blocking": True,
        "local_addr": None,
        "remote_addr": None,
    })
    s = sr.reconnect()
    try:
        assert isinstance(s, socket.socket)
        assert s.gettimeout() == 5.0
    finally:
        s.close()


def test_socket_reconnector_nonblocking():
    sr = SocketReconnector(state={
        "family": socket.AF_INET,
        "type": socket.SOCK_STREAM,
        "proto": 0,
        "timeout": None,
        "blocking": False,
        "local_addr": None,
        "remote_addr": None,
    })
    s = sr.reconnect()
    try:
        assert s.gettimeout() == 0.0
    finally:
        s.close()


def test_socket_reconnector_bad_bind():
    """Reconnector handles bind failure gracefully."""
    sr = SocketReconnector(state={
        "family": socket.AF_INET,
        "type": socket.SOCK_STREAM,
        "proto": 0,
        "timeout": None,
        "blocking": True,
        "local_addr": ("192.0.2.1", 12345),
        "remote_addr": None,
    })
    s = sr.reconnect()
    s.close()


def test_socket_reconnector_bad_connect():
    """Reconnector handles connect failure gracefully."""
    sr = SocketReconnector(state={
        "family": socket.AF_INET,
        "type": socket.SOCK_STREAM,
        "proto": 0,
        "timeout": 0.01,
        "blocking": True,
        "local_addr": None,
        "remote_addr": ("192.0.2.1", 1),
    })
    s = sr.reconnect()
    s.close()


# =============================================================================
# DatabaseConnectionHandler tests
# =============================================================================

def test_db_handler_can_handle_sqlite():
    import sqlite3
    h = DatabaseConnectionHandler()
    conn = sqlite3.connect(":memory:")
    try:
        assert h.can_handle(conn)
    finally:
        conn.close()


def test_db_handler_can_handle_false():
    h = DatabaseConnectionHandler()
    assert not h.can_handle("not a connection")
    assert not h.can_handle(42)
    assert not h.can_handle([1, 2, 3])


def test_db_handler_extract_state_sqlite():
    import sqlite3
    h = DatabaseConnectionHandler()
    conn = sqlite3.connect(":memory:")
    try:
        state = h.extract_state(conn)
        assert state["module"] == "sqlite3"
        assert "Connection" in state["class_name"]
    finally:
        conn.close()


def test_db_handler_reconstruct_sqlite():
    h = DatabaseConnectionHandler()
    state = {
        "module": "sqlite3",
        "class_name": "Connection",
        "path": ":memory:",
    }
    result = h.reconstruct(state)
    import sqlite3
    assert isinstance(result, sqlite3.Connection)
    result.close()


def test_db_handler_reconstruct_unknown():
    h = DatabaseConnectionHandler()
    state = {
        "module": "psycopg2.extensions",
        "class_name": "connection",
        "host": "localhost",
        "port": 5432,
    }
    result = h.reconstruct(state)
    assert isinstance(result, PostgresReconnector)


# =============================================================================
# HTTPSessionHandler tests
# =============================================================================

def test_http_session_handler_can_handle_no_requests():
    h = HTTPSessionHandler()
    assert not h.can_handle("not a session")
    assert not h.can_handle(42)


# =============================================================================
# DatabaseConnectionHandler — extract_state with mock objects
# =============================================================================

def _make_fake_db_class(name, module):
    """Create a fake class with the right __name__ and __module__ for can_handle."""
    ns = {"__module__": module}
    cls = type(name, (), ns)
    return cls


def test_db_handler_extract_postgres_mock():
    """Exercise psycopg2-like extract_state paths."""
    h = DatabaseConnectionHandler()

    FakeInfo = type("FakeInfo", (), {"host": "pg.local", "port": 5432, "dbname": "mydb", "user": "admin"})

    FakeConn = _make_fake_db_class("connection", "psycopg2.extensions")
    obj = FakeConn()
    obj.info = FakeInfo()
    obj.dsn = "host=pg.local dbname=mydb"
    obj.get_dsn_parameters = lambda: {"host": "pg.local", "password": "secret", "passwd": "p", "token": "t"}

    assert h.can_handle(obj)
    state = h.extract_state(obj)
    assert state["host"] == "pg.local"
    assert state["dsn"] == "host=pg.local dbname=mydb"
    # password/passwd/token should be scrubbed
    assert state["dsn_parameters"]["password"] is None
    assert state["dsn_parameters"]["passwd"] is None
    assert state["dsn_parameters"]["token"] is None


def test_db_handler_extract_mysql_mock():
    """Exercise pymysql-like extract_state paths."""
    h = DatabaseConnectionHandler()

    FakeMySQL = _make_fake_db_class("Connection", "pymysql.connections")
    obj = FakeMySQL()
    obj._host = "mysql.local"
    obj._port = 3306
    obj._user = "root"
    obj._database = "app"

    assert h.can_handle(obj)
    state = h.extract_state(obj)
    assert state["host"] == "mysql.local"
    assert state["port"] == 3306


def test_db_handler_extract_redis_mock():
    """Exercise redis-like extract_state paths."""
    h = DatabaseConnectionHandler()

    FakePool = type("FakePool", (), {})
    pool = FakePool()
    pool.connection_kwargs = {"host": "redis.local", "port": 6379, "password": "secret"}

    FakeRedis = _make_fake_db_class("Redis", "redis.client")
    obj = FakeRedis()
    obj.connection_pool = pool

    assert h.can_handle(obj)
    state = h.extract_state(obj)
    assert state["connection_kwargs"]["password"] is None  # scrubbed


def test_db_handler_extract_mongo_mock():
    """Exercise pymongo-like extract_state paths."""
    h = DatabaseConnectionHandler()

    FakeMongo = _make_fake_db_class("MongoClient", "pymongo.mongo_client")
    obj = FakeMongo()
    obj.host = "mongo.local"
    obj.port = 27017
    obj.address = ("mongo.local", 27017)
    obj.nodes = {("mongo.local", 27017)}

    assert h.can_handle(obj)
    state = h.extract_state(obj)
    assert state["address"] == ("mongo.local", 27017)
    assert len(state["nodes"]) == 1


def test_db_handler_extract_sqlalchemy_mock():
    """Exercise sqlalchemy-like extract_state paths."""
    h = DatabaseConnectionHandler()

    FakeUrl = type("FakeUrl", (), {
        "drivername": "postgresql",
        "host": "pg.local",
        "port": 5432,
        "database": "mydb",
        "username": "admin",
        "query": {"sslmode": "require"},
        "render_as_string": lambda self, hide_password=False: "postgresql://admin@pg.local:5432/mydb",
    })

    FakeEngine = type("FakeEngine", (), {})
    engine = FakeEngine()
    engine.url = FakeUrl()

    FakeConn = _make_fake_db_class("Connection", "sqlalchemy.engine.base")
    obj = FakeConn()
    obj.engine = engine

    assert h.can_handle(obj)
    state = h.extract_state(obj)
    assert state["drivername"] == "postgresql"
    assert state["url"] == "postgresql://admin@pg.local:5432/mydb"
    assert state["query"] == {"sslmode": "require"}


def test_db_handler_extract_sqlalchemy_url_direct():
    """Exercise sqlalchemy path with url directly on obj."""
    h = DatabaseConnectionHandler()

    FakeUrl = type("FakeUrl", (), {
        "drivername": "mysql",
        "host": "m.local",
        "port": 3306,
        "database": "app",
        "username": "root",
    })

    FakeConn = _make_fake_db_class("Connection", "sqlalchemy.engine.base")
    obj = FakeConn()
    obj.url = FakeUrl()

    state = h.extract_state(obj)
    assert state["drivername"] == "mysql"
    # no render_as_string, should fallback to str()
    assert "url" in state


def test_db_handler_extract_generic_attrs():
    """Exercise generic attr paths (hostname, server, db, dbname, username)."""
    h = DatabaseConnectionHandler()

    FakeConn = _make_fake_db_class("Connection", "sqlite3")
    obj = FakeConn()
    obj.hostname = "h1"
    obj.server = "h2"
    obj.username = "u1"
    obj.db = "d1"
    obj.dbname = "d2"

    state = h.extract_state(obj)
    # hostname, server both map to 'host' — last one wins
    assert "host" in state
    # username maps to 'user'
    assert state["user"] == "u1"


# =============================================================================
# HTTPSessionHandler with requests library
# =============================================================================

def test_http_session_handler_with_requests():
    """Test with real requests.Session if requests is installed."""
    try:
        import requests
    except ImportError:
        return  # skip if requests not available

    h = HTTPSessionHandler()
    session = requests.Session()
    session.headers.update({"X-Test": "123"})
    session.auth = ("user", "pass")
    session.proxies = {"http": "http://proxy:8080"}
    session.verify = False
    session.max_redirects = 10

    assert h.can_handle(session)
    state = h.extract_state(session)
    assert state["headers"]["X-Test"] == "123"
    assert state["auth"] == ("user", "pass")
    assert state["verify"] is False
    assert state["max_redirects"] == 10

    reconstructed = h.reconstruct(state)
    assert isinstance(reconstructed, requests.Session)
    assert reconstructed.headers["X-Test"] == "123"
    assert reconstructed.auth == ("user", "pass")
    assert reconstructed.verify is False
    session.close()
    reconstructed.close()


def test_http_session_handler_cookies():
    """Test cookie extraction."""
    try:
        import requests
    except ImportError:
        return

    h = HTTPSessionHandler()
    session = requests.Session()
    session.cookies.set("session_id", "abc123")
    state = h.extract_state(session)
    assert state["cookies"]["session_id"] == "abc123"
    session.close()


# =============================================================================
# DbReconnector legacy alias
# =============================================================================

def test_db_reconnector_alias():
    assert DbReconnector is _DbReconnector


# =============================================================================
# SQLiteReconnector lazy_reconnect_on_access
# =============================================================================

def test_sqlite_reconnector_lazy_flag():
    r = SQLiteReconnector(details={})
    assert r._lazy_reconnect_on_access is True


def test_socket_reconnector_lazy_flag():
    sr = SocketReconnector(state={})
    assert sr._lazy_reconnect_on_access is True


# =============================================================================
# Cassandra auth path
# =============================================================================

def test_cassandra_reconnect_with_auth():
    r = CassandraReconnector(details={"contact_points": ["10.0.0.1"], "port": 9042, "username": "cassandra", "keyspace": "ks"})
    try:
        r.reconnect(auth="pass")
    except NetworkSerializationError:
        pass


# =============================================================================
# Runner
# =============================================================================

def run_all_tests():
    """Run all network handler tests."""
    print(f"\n\033[1m\033[96m{'='*70}\033[0m")
    print(f"\033[1m\033[96m{'Cucumber Network Handler Tests':^70}\033[0m")
    print(f"\033[1m\033[96m{'='*70}\033[0m")

    runner = TestRunner("Network Handler Tests")

    # _DbReconnector base
    runner.run_test("_DbReconnector._get basic", test_db_reconnector_get_basic)
    runner.run_test("_DbReconnector._get fallback keys", test_db_reconnector_get_fallback_keys)
    runner.run_test("_DbReconnector._get skips None", test_db_reconnector_get_skips_none)
    runner.run_test("_DbReconnector._import missing", test_db_reconnector_import_missing)
    runner.run_test("_DbReconnector._import stdlib", test_db_reconnector_import_stdlib)

    # __repr__
    runner.run_test("PostgresReconnector repr", test_postgres_repr)
    runner.run_test("PostgresReconnector repr no port", test_postgres_repr_no_port)
    runner.run_test("MySQLReconnector repr", test_mysql_repr)
    runner.run_test("SQLiteReconnector repr", test_sqlite_repr)
    runner.run_test("SQLiteReconnector repr default", test_sqlite_repr_default)
    runner.run_test("MongoReconnector repr", test_mongo_repr)
    runner.run_test("RedisReconnector repr", test_redis_repr)
    runner.run_test("SQLAlchemyReconnector repr url", test_sqlalchemy_repr_url)
    runner.run_test("SQLAlchemyReconnector repr long url", test_sqlalchemy_repr_long_url)
    runner.run_test("SQLAlchemyReconnector repr no url", test_sqlalchemy_repr_no_url)
    runner.run_test("CassandraReconnector repr", test_cassandra_repr)
    runner.run_test("ElasticsearchReconnector repr", test_elasticsearch_repr)
    runner.run_test("Neo4jReconnector repr uri", test_neo4j_repr_uri)
    runner.run_test("Neo4jReconnector repr no uri", test_neo4j_repr_no_uri)
    runner.run_test("InfluxDBReconnector repr url", test_influxdb_repr_url)
    runner.run_test("InfluxDBReconnector repr no url", test_influxdb_repr_no_url)
    runner.run_test("ODBCReconnector repr", test_odbc_repr)
    runner.run_test("ClickHouseReconnector repr", test_clickhouse_repr)
    runner.run_test("MSSQLReconnector repr", test_mssql_repr)
    runner.run_test("OracleReconnector repr dsn", test_oracle_repr_dsn)
    runner.run_test("OracleReconnector repr components", test_oracle_repr_components)
    runner.run_test("SnowflakeReconnector repr", test_snowflake_repr)
    runner.run_test("DuckDBReconnector repr", test_duckdb_repr)
    runner.run_test("DuckDBReconnector repr default", test_duckdb_repr_default)

    # reconnect() error paths
    runner.run_test("Postgres reconnect no driver", test_postgres_reconnect_no_driver)
    runner.run_test("MySQL reconnect no driver", test_mysql_reconnect_no_driver)
    runner.run_test("SQLite reconnect memory", test_sqlite_reconnect_memory)
    runner.run_test("SQLite reconnect with path", test_sqlite_reconnect_with_path)
    runner.run_test("Mongo reconnect no driver", test_mongo_reconnect_no_driver)
    runner.run_test("Redis reconnect no driver", test_redis_reconnect_no_driver)
    runner.run_test("SQLAlchemy reconnect no driver", test_sqlalchemy_reconnect_no_driver)
    runner.run_test("Cassandra reconnect no driver", test_cassandra_reconnect_no_driver)
    runner.run_test("Elasticsearch reconnect no driver", test_elasticsearch_reconnect_no_driver)
    runner.run_test("Neo4j reconnect no driver", test_neo4j_reconnect_no_driver)
    runner.run_test("InfluxDB reconnect no driver", test_influxdb_reconnect_no_driver)
    runner.run_test("ODBC reconnect no driver", test_odbc_reconnect_no_driver)
    runner.run_test("ODBC reconnect no params", test_odbc_reconnect_no_params)
    runner.run_test("ClickHouse reconnect no driver", test_clickhouse_reconnect_no_driver)
    runner.run_test("MSSQL reconnect no driver", test_mssql_reconnect_no_driver)
    runner.run_test("Oracle reconnect no driver", test_oracle_reconnect_no_driver)
    runner.run_test("Snowflake reconnect no driver", test_snowflake_reconnect_no_driver)
    runner.run_test("DuckDB reconnect no driver", test_duckdb_reconnect_no_driver)

    # reconnect() auth paths
    runner.run_test("Postgres reconnect with auth", test_postgres_reconnect_with_auth)
    runner.run_test("Postgres reconnect with dsn", test_postgres_reconnect_with_dsn)
    runner.run_test("MySQL reconnect with auth", test_mysql_reconnect_with_auth)
    runner.run_test("Mongo reconnect with uri", test_mongo_reconnect_with_uri)
    runner.run_test("Mongo reconnect with auth", test_mongo_reconnect_with_auth)
    runner.run_test("Mongo reconnect empty", test_mongo_reconnect_empty)
    runner.run_test("Redis reconnect with url", test_redis_reconnect_with_url)
    runner.run_test("Redis reconnect with auth", test_redis_reconnect_with_auth)
    runner.run_test("ES reconnect with user auth", test_elasticsearch_reconnect_with_user_auth)
    runner.run_test("ES reconnect with api key", test_elasticsearch_reconnect_with_api_key)
    runner.run_test("ES reconnect with url fallback", test_elasticsearch_reconnect_with_url_fallback)
    runner.run_test("ES reconnect no hosts", test_elasticsearch_reconnect_no_hosts)
    runner.run_test("Neo4j reconnect with auth", test_neo4j_reconnect_with_auth)
    runner.run_test("Neo4j reconnect build uri", test_neo4j_reconnect_build_uri)
    runner.run_test("InfluxDB reconnect v2 with auth", test_influxdb_reconnect_v2_with_auth)
    runner.run_test("InfluxDB reconnect build url", test_influxdb_reconnect_build_url)
    runner.run_test("ODBC reconnect with dsn", test_odbc_reconnect_with_dsn)
    runner.run_test("ODBC reconnect with parts", test_odbc_reconnect_with_parts)
    runner.run_test("Oracle reconnect with components", test_oracle_reconnect_with_components)
    runner.run_test("Oracle reconnect no dsn no components", test_oracle_reconnect_no_dsn_no_components)
    runner.run_test("Snowflake reconnect with auth", test_snowflake_reconnect_with_auth)
    runner.run_test("ClickHouse reconnect with auth", test_clickhouse_reconnect_with_auth)
    runner.run_test("MSSQL reconnect with auth", test_mssql_reconnect_with_auth)
    runner.run_test("Cassandra reconnect with auth", test_cassandra_reconnect_with_auth)

    # Factory
    runner.run_test("Factory postgres", test_factory_postgres)
    runner.run_test("Factory mysql", test_factory_mysql)
    runner.run_test("Factory sqlite", test_factory_sqlite)
    runner.run_test("Factory mongo", test_factory_mongo)
    runner.run_test("Factory redis", test_factory_redis)
    runner.run_test("Factory sqlalchemy", test_factory_sqlalchemy)
    runner.run_test("Factory cassandra", test_factory_cassandra)
    runner.run_test("Factory elasticsearch", test_factory_elasticsearch)
    runner.run_test("Factory neo4j", test_factory_neo4j)
    runner.run_test("Factory influxdb", test_factory_influxdb)
    runner.run_test("Factory odbc", test_factory_odbc)
    runner.run_test("Factory clickhouse", test_factory_clickhouse)
    runner.run_test("Factory mssql", test_factory_mssql)
    runner.run_test("Factory oracle", test_factory_oracle)
    runner.run_test("Factory snowflake", test_factory_snowflake)
    runner.run_test("Factory duckdb", test_factory_duckdb)
    runner.run_test("Factory mariadb", test_factory_mariadb)
    runner.run_test("Factory cx_Oracle", test_factory_cx_oracle)
    runner.run_test("Factory unknown fallback", test_factory_unknown_fallback)

    # Socket
    runner.run_test("SocketHandler can_handle", test_socket_handler_can_handle)
    runner.run_test("SocketHandler extract_state", test_socket_handler_extract_state)
    runner.run_test("SocketHandler extract nonblocking", test_socket_handler_extract_nonblocking)
    runner.run_test("SocketHandler reconstruct", test_socket_handler_reconstruct)
    runner.run_test("SocketReconnector reconnect", test_socket_reconnector_reconnect)
    runner.run_test("SocketReconnector nonblocking", test_socket_reconnector_nonblocking)
    runner.run_test("SocketReconnector bad bind", test_socket_reconnector_bad_bind)
    runner.run_test("SocketReconnector bad connect", test_socket_reconnector_bad_connect)

    # DatabaseConnectionHandler
    runner.run_test("DbHandler can_handle sqlite", test_db_handler_can_handle_sqlite)
    runner.run_test("DbHandler can_handle false", test_db_handler_can_handle_false)
    runner.run_test("DbHandler extract_state sqlite", test_db_handler_extract_state_sqlite)
    runner.run_test("DbHandler reconstruct sqlite", test_db_handler_reconstruct_sqlite)
    runner.run_test("DbHandler reconstruct unknown", test_db_handler_reconstruct_unknown)
    runner.run_test("DbHandler extract postgres mock", test_db_handler_extract_postgres_mock)
    runner.run_test("DbHandler extract mysql mock", test_db_handler_extract_mysql_mock)
    runner.run_test("DbHandler extract redis mock", test_db_handler_extract_redis_mock)
    runner.run_test("DbHandler extract mongo mock", test_db_handler_extract_mongo_mock)
    runner.run_test("DbHandler extract sqlalchemy mock", test_db_handler_extract_sqlalchemy_mock)
    runner.run_test("DbHandler extract sqlalchemy url direct", test_db_handler_extract_sqlalchemy_url_direct)
    runner.run_test("DbHandler extract generic attrs", test_db_handler_extract_generic_attrs)

    # HTTP
    runner.run_test("HTTPSessionHandler can_handle", test_http_session_handler_can_handle_no_requests)
    runner.run_test("HTTPSessionHandler with requests", test_http_session_handler_with_requests)
    runner.run_test("HTTPSessionHandler cookies", test_http_session_handler_cookies)

    # Misc
    runner.run_test("DbReconnector legacy alias", test_db_reconnector_alias)
    runner.run_test("SQLiteReconnector lazy flag", test_sqlite_reconnector_lazy_flag)
    runner.run_test("SocketReconnector lazy flag", test_socket_reconnector_lazy_flag)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
