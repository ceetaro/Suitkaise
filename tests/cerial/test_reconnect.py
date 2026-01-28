"""
Tests for reconnect_all() with overrides and autoreconnect decorator.
"""

import sys
from pathlib import Path

# Add project root to path
def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import cerial
from suitkaise.cerial import reconnect_all
from suitkaise.cerial._int.handlers.reconnector import Reconnector
from suitkaise.cerial._int.handlers.network_handler import (
    DbReconnector,
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
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'

    def run_test(self, name: str, test_func):
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))

    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*70}{self.RESET}\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed

        for result in self.results:
            if result.passed:
                status = f"{self.GREEN}✓ PASS{self.RESET}"
            else:
                status = f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")

        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")

        if failed != 0:
            print(f"{self.BOLD}{self.RED}Failed tests (recap):{self.RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  {self.RED}✗ {result.name}{self.RESET}")
                    if result.error:
                        print(f"     {self.RED}└─ {result.error}{self.RESET}")
            print()

        try:
            from tests._failure_registry import record_failures
            record_failures(self.suite_name, [r for r in self.results if not r.passed])
        except Exception:
            pass

        return failed == 0


# =============================================================================
# Mock Reconnectors for Testing
# =============================================================================

class MockDbReconnector(Reconnector):
    """Mock DbReconnector that captures password."""
    def __init__(self, module: str, class_name: str, details: dict | None = None):
        self.module = module
        self.class_name = class_name
        self.details = details or {}
        self.last_password: str | None = None
    
    def reconnect(self, auth: str | None = None, **kwargs):
        self.last_password = auth
        return f"connected:{self.module}.{self.class_name}:{auth}"


class SimpleReconnector(Reconnector):
    """Simple reconnector that returns a fixed value."""
    def __init__(self, value):
        self.value = value
    
    def reconnect(self, auth: str | None = None, **kwargs):
        return f"reconnected-{self.value}"


# =============================================================================
# Tests: reconnect_all basic functionality
# =============================================================================

def test_reconnect_all_no_overrides():
    """reconnect_all without overrides should call reconnect() with no kwargs."""
    rec = SimpleReconnector("test")
    result = reconnect_all(rec)
    assert result == "reconnected-test", f"Expected 'reconnected-test', got {result}"


def test_reconnect_all_in_dict():
    """reconnect_all should recurse into dicts."""
    rec = SimpleReconnector("nested")
    obj = {"key": rec}
    result = reconnect_all(obj)
    assert result["key"] == "reconnected-nested"


def test_reconnect_all_in_list():
    """reconnect_all should recurse into lists."""
    rec = SimpleReconnector("item")
    obj = [1, rec, 3]
    result = reconnect_all(obj)
    assert result[1] == "reconnected-item"


def test_reconnect_all_in_object_dict():
    """reconnect_all should recurse into object __dict__."""
    class Container:
        def __init__(self):
            self.conn = SimpleReconnector("attr")
    
    obj = Container()
    result = reconnect_all(obj)
    assert result.conn == "reconnected-attr"


# =============================================================================
# Tests: reconnect_all with overrides
# =============================================================================

def test_reconnect_all_password_type_key():
    """reconnect_all should look up password by type key."""
    rec = MockDbReconnector("psycopg2.extensions", "connection")
    obj = {"db": rec}
    
    passwords = {
        "psycopg2.Connection": {
            "*": "secret123"
        }
    }
    
    reconnect_all(obj, **passwords)
    
    assert rec.last_password == "secret123", \
        f"Expected 'secret123', got {rec.last_password}"


def test_reconnect_all_password_attr_specific():
    """reconnect_all should use attr-specific password over default."""
    rec1 = MockDbReconnector("psycopg2.extensions", "connection")
    rec2 = MockDbReconnector("psycopg2.extensions", "connection")
    
    class Container:
        def __init__(self):
            self.main_db = rec1
            self.analytics_db = rec2
    
    obj = Container()
    
    passwords = {
        "psycopg2.Connection": {
            "*": "default_pass",
            "analytics_db": "analytics_pass",
        }
    }
    
    reconnect_all(obj, **passwords)
    
    assert rec1.last_password == "default_pass", \
        f"main_db should get default, got {rec1.last_password}"
    assert rec2.last_password == "analytics_pass", \
        f"analytics_db should get specific, got {rec2.last_password}"


def test_reconnect_all_password_multiple_types():
    """reconnect_all should handle multiple DB types."""
    pg_rec = MockDbReconnector("psycopg2.extensions", "connection")
    redis_rec = MockDbReconnector("redis", "Redis")
    
    class Container:
        def __init__(self):
            self.db = pg_rec
            self.cache = redis_rec
    
    obj = Container()
    
    passwords = {
        "psycopg2.Connection": {
            "*": "pg_pass"
        },
        "redis.Redis": {
            "*": "redis_pass"
        }
    }
    
    reconnect_all(obj, **passwords)
    
    assert pg_rec.last_password == "pg_pass"
    assert redis_rec.last_password == "redis_pass"


def test_reconnect_all_password_no_match():
    """reconnect_all should pass None if no password matches."""
    rec = MockDbReconnector("unknown.module", "UnknownClass")
    obj = {"conn": rec}
    
    passwords = {
        "psycopg2.Connection": {
            "*": "secret"
        }
    }
    
    reconnect_all(obj, **passwords)
    
    assert rec.last_password is None, f"Should get None, got {rec.last_password}"


def test_reconnect_all_type_key_normalization():
    """Type key should normalize module.classname correctly."""
    # Test various module formats
    test_cases = [
        ("psycopg2", "connection", "psycopg2.Connection"),
        ("psycopg2.extensions", "connection", "psycopg2.Connection"),
        ("redis", "Redis", "redis.Redis"),
        ("redis.client", "Redis", "redis.Redis"),
        ("pymongo", "MongoClient", "pymongo.Mongoclient"),
    ]
    
    for module, class_name, expected_key in test_cases:
        rec = MockDbReconnector(module, class_name)
        obj = {"conn": rec}
        
        passwords = {
            expected_key: {
                "*": "test_password"
            }
        }
        
        reconnect_all(obj, **passwords)
        
        # Should match and get the password
        assert rec.last_password == "test_password", \
            f"Key {expected_key} should match {module}.{class_name}, got {rec.last_password}"


# =============================================================================
# Tests: autoreconnect decorator
# =============================================================================

def test_auto_reconnect_decorator_sets_flags():
    """@autoreconnect should set class attributes."""
    from suitkaise.processing import Skprocess, autoreconnect  # type: ignore[attr-defined]
    
    @autoreconnect(**{
        "psycopg2.Connection": {"*": "test_password"}
    })
    class TestProcess(Skprocess):
        def __run__(self):
            pass
    
    assert getattr(TestProcess, "_auto_reconnect_enabled", False) is True
    assert getattr(TestProcess, "_auto_reconnect_kwargs", None) == {
        "psycopg2.Connection": {"*": "test_password"}
    }


def test_auto_reconnect_docstring_example():
    """Docstring example should set auth mapping correctly."""
    from suitkaise.processing import Skprocess, autoreconnect  # type: ignore[attr-defined]
    
    auth = {
        "psycopg2.Connection": {"*": "secret"},
        "redis.Redis": {"*": "redis_pass"},
    }
    
    @autoreconnect(**auth)
    class MyProcess(Skprocess):
        def __run__(self):
            pass
    
    assert getattr(MyProcess, "_auto_reconnect_enabled", False) is True
    assert getattr(MyProcess, "_auto_reconnect_kwargs", None) == auth


def test_auto_reconnect_empty():
    """@autoreconnect() with no args should enable reconnect with empty overrides."""
    from suitkaise.processing import Skprocess, autoreconnect  # type: ignore[attr-defined]
    
    @autoreconnect()
    class TestProcess(Skprocess):
        def __run__(self):
            pass
    
    assert getattr(TestProcess, "_auto_reconnect_enabled", False) is True
    assert getattr(TestProcess, "_auto_reconnect_kwargs", None) == {}


# =============================================================================
# Tests: Real DbReconnector type key matching
# =============================================================================

def test_real_db_reconnector_type_key():
    """Real PostgresReconnector should match type keys correctly."""
    # Create a real PostgresReconnector like cerial would
    rec = PostgresReconnector(details={"host": "localhost", "port": 5432})
    
    class Container:
        def __init__(self):
            self.db = rec
    
    obj = Container()
    
    # Mock the reconnect to capture what's passed
    captured_password = [None]
    def mock_reconnect(auth=None, **kwargs):
        captured_password[0] = auth
        return "mocked"
    rec.reconnect = mock_reconnect
    
    passwords = {
        "psycopg2.Connection": {
            "*": "testpass"
        }
    }
    
    reconnect_all(obj, **passwords)
    
    assert captured_password[0] == "testpass", \
        f"Expected 'testpass', got {captured_password[0]}"


def test_reconnect_all_db_reconnector_type_keys():
    """All DbReconnector subclasses should match type keys."""
    reconnectors = [
        (PostgresReconnector, "psycopg2.Connection", {"host": "localhost"}),
        (MySQLReconnector, "pymysql.Connection", {"host": "localhost"}),
        (SQLiteReconnector, "sqlite3.Connection", {"path": ":memory:"}),
        (MongoReconnector, "pymongo.MongoClient", {"host": "localhost"}),
        (RedisReconnector, "redis.Redis", {"host": "localhost"}),
        (SQLAlchemyReconnector, "sqlalchemy.Engine", {"url": "sqlite://"}),
        (CassandraReconnector, "cassandra.Cluster", {"hosts": ["localhost"]}),
        (ElasticsearchReconnector, "elasticsearch.Elasticsearch", {"hosts": ["localhost"]}),
        (Neo4jReconnector, "neo4j.Driver", {"uri": "bolt://localhost"}),
        (InfluxDBReconnector, "influxdb_client.InfluxDBClient", {"url": "http://localhost"}),
        (ODBCReconnector, "pyodbc.Connection", {"dsn": "db"}),
        (ClickHouseReconnector, "clickhouse_driver.Client", {"host": "localhost"}),
        (MSSQLReconnector, "pymssql.Connection", {"host": "localhost"}),
        (OracleReconnector, "oracledb.Connection", {"host": "localhost"}),
        (SnowflakeReconnector, "snowflake.Connection", {"account": "acct"}),
        (DuckDBReconnector, "duckdb.Connection", {"path": ":memory:"}),
    ]
    
    for cls, type_key, details in reconnectors:
        rec = cls(details=details)
        captured = {"auth": None}
        
        def reconnect(auth=None, **kwargs):
            captured["auth"] = auth
            return "ok"
        
        rec.reconnect = reconnect
        obj = {"db": rec}
        passwords = {type_key: {"*": "pw"}}
        reconnect_all(obj, **passwords)
        assert captured["auth"] == "pw", f"{cls.__name__} did not receive auth"


def test_reconnect_all_attr_specific_dict_key():
    """Dict keys should be used as attr_name for auth lookup."""
    rec = MockDbReconnector("psycopg2.extensions", "connection")
    obj = {"analytics_db": rec}
    passwords = {
        "psycopg2.Connection": {
            "*": "default",
            "analytics_db": "special",
        }
    }
    reconnect_all(obj, **passwords)
    assert rec.last_password == "special"


def test_reconnect_all_handles_failures():
    """reconnect_all should leave items when reconnect fails."""
    class FailingReconnector(Reconnector):
        def reconnect(self, **kwargs):
            raise RuntimeError("fail")
    
    rec = FailingReconnector()
    result = reconnect_all(rec)
    assert result is rec


def test_reconnect_all_handles_sets_and_cycles():
    """reconnect_all should handle sets and cycles."""
    rec1 = SimpleReconnector("a")
    rec2 = SimpleReconnector("b")
    payload = {rec1, rec2}
    restored = reconnect_all(payload)
    assert "reconnected-a" in restored
    assert "reconnected-b" in restored
    
    cycle = []
    cycle.append(cycle)
    cycle.append(SimpleReconnector("cycle"))
    reconnect_all(cycle)
    assert cycle[1] == "reconnected-cycle"


# =============================================================================
# Main
# =============================================================================

def run_all_tests():
    runner = TestRunner("Reconnect Tests")
    
    # Basic functionality
    runner.run_test("reconnect_all no passwords", test_reconnect_all_no_overrides)
    runner.run_test("reconnect_all in dict", test_reconnect_all_in_dict)
    runner.run_test("reconnect_all in list", test_reconnect_all_in_list)
    runner.run_test("reconnect_all in object dict", test_reconnect_all_in_object_dict)
    
    # Passwords
    runner.run_test("password type key lookup", test_reconnect_all_password_type_key)
    runner.run_test("password attr-specific", test_reconnect_all_password_attr_specific)
    runner.run_test("password multiple types", test_reconnect_all_password_multiple_types)
    runner.run_test("password no match", test_reconnect_all_password_no_match)
    runner.run_test("type key normalization", test_reconnect_all_type_key_normalization)
    
    # autoreconnect decorator
    runner.run_test("autoreconnect sets flags", test_auto_reconnect_decorator_sets_flags)
    runner.run_test("autoreconnect docstring example", test_auto_reconnect_docstring_example)
    runner.run_test("autoreconnect empty", test_auto_reconnect_empty)
    
    # Real DbReconnector
    runner.run_test("real PostgresReconnector type key", test_real_db_reconnector_type_key)
    runner.run_test("all DbReconnector type keys", test_reconnect_all_db_reconnector_type_keys)
    runner.run_test("attr-specific dict key", test_reconnect_all_attr_specific_dict_key)
    runner.run_test("reconnect_all handles failures", test_reconnect_all_handles_failures)
    runner.run_test("reconnect_all sets/cycles", test_reconnect_all_handles_sets_and_cycles)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
