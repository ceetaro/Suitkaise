"""
Tests for reconnect_all() with overrides and auto_reconnect decorator.
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
from suitkaise.cerial._int.handlers.network_handler import DbReconnector, PostgresReconnector


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

        return failed == 0


# =============================================================================
# Mock Reconnectors for Testing
# =============================================================================

class MockDbReconnector(Reconnector):
    """Mock DbReconnector that captures overrides."""
    def __init__(self, module: str, class_name: str, details: dict = None):
        self.module = module
        self.class_name = class_name
        self.details = details or {}
        self.last_overrides = None
    
    def reconnect(self, **overrides):
        self.last_overrides = overrides
        # Merge details with overrides
        merged = dict(self.details)
        merged.update(overrides)
        return f"connected:{self.module}.{self.class_name}:{merged}"


class SimpleReconnector(Reconnector):
    """Simple reconnector that returns a fixed value."""
    def __init__(self, value):
        self.value = value
    
    def reconnect(self, **kwargs):
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

def test_reconnect_all_overrides_type_key():
    """reconnect_all should look up overrides by type key."""
    rec = MockDbReconnector("psycopg2.extensions", "connection")
    obj = {"db": rec}
    
    overrides = {
        "psycopg2.Connection": {
            "*": {"password": "secret123"}
        }
    }
    
    reconnect_all(obj, **overrides)
    
    assert rec.last_overrides == {"password": "secret123"}, \
        f"Expected {{'password': 'secret123'}}, got {rec.last_overrides}"


def test_reconnect_all_overrides_attr_specific():
    """reconnect_all should use attr-specific overrides over defaults."""
    rec1 = MockDbReconnector("psycopg2.extensions", "connection")
    rec2 = MockDbReconnector("psycopg2.extensions", "connection")
    
    class Container:
        def __init__(self):
            self.main_db = rec1
            self.analytics_db = rec2
    
    obj = Container()
    
    overrides = {
        "psycopg2.Connection": {
            "*": {"password": "default_pass"},
            "analytics_db": {"password": "analytics_pass"},
        }
    }
    
    reconnect_all(obj, **overrides)
    
    assert rec1.last_overrides == {"password": "default_pass"}, \
        f"main_db should get default, got {rec1.last_overrides}"
    assert rec2.last_overrides == {"password": "analytics_pass"}, \
        f"analytics_db should get specific, got {rec2.last_overrides}"


def test_reconnect_all_overrides_merge():
    """Attr-specific overrides should merge with defaults."""
    rec = MockDbReconnector("psycopg2.extensions", "connection")
    
    class Container:
        def __init__(self):
            self.db = rec
    
    obj = Container()
    
    overrides = {
        "psycopg2.Connection": {
            "*": {"host": "localhost", "password": "default"},
            "db": {"password": "specific"},  # Override password, keep host
        }
    }
    
    reconnect_all(obj, **overrides)
    
    assert rec.last_overrides == {"host": "localhost", "password": "specific"}, \
        f"Should merge, got {rec.last_overrides}"


def test_reconnect_all_overrides_multiple_types():
    """reconnect_all should handle multiple DB types."""
    pg_rec = MockDbReconnector("psycopg2.extensions", "connection")
    redis_rec = MockDbReconnector("redis", "Redis")
    
    class Container:
        def __init__(self):
            self.db = pg_rec
            self.cache = redis_rec
    
    obj = Container()
    
    overrides = {
        "psycopg2.Connection": {
            "*": {"password": "pg_pass"}
        },
        "redis.Redis": {
            "*": {"password": "redis_pass"}
        }
    }
    
    reconnect_all(obj, **overrides)
    
    assert pg_rec.last_overrides == {"password": "pg_pass"}
    assert redis_rec.last_overrides == {"password": "redis_pass"}


def test_reconnect_all_overrides_no_match():
    """reconnect_all should pass empty kwargs if no override matches."""
    rec = MockDbReconnector("unknown.module", "UnknownClass")
    obj = {"conn": rec}
    
    overrides = {
        "psycopg2.Connection": {
            "*": {"password": "secret"}
        }
    }
    
    reconnect_all(obj, **overrides)
    
    assert rec.last_overrides == {}, f"Should get empty overrides, got {rec.last_overrides}"


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
        
        overrides = {
            expected_key: {
                "*": {"test": "value"}
            }
        }
        
        reconnect_all(obj, **overrides)
        
        # Should match and get the override
        assert rec.last_overrides == {"test": "value"}, \
            f"Key {expected_key} should match {module}.{class_name}, got {rec.last_overrides}"


# =============================================================================
# Tests: auto_reconnect decorator
# =============================================================================

def test_auto_reconnect_decorator_sets_flags():
    """@auto_reconnect should set class attributes."""
    from suitkaise.processing import Skprocess, auto_reconnect
    
    @auto_reconnect(**{
        "psycopg2.Connection": {"*": {"password": "test"}}
    })
    class TestProcess(Skprocess):
        def __run__(self):
            pass
    
    assert hasattr(TestProcess, '_auto_reconnect_enabled')
    assert TestProcess._auto_reconnect_enabled is True
    assert hasattr(TestProcess, '_auto_reconnect_kwargs')
    assert TestProcess._auto_reconnect_kwargs == {
        "psycopg2.Connection": {"*": {"password": "test"}}
    }


def test_auto_reconnect_empty():
    """@auto_reconnect() with no args should enable reconnect with empty overrides."""
    from suitkaise.processing import Skprocess, auto_reconnect
    
    @auto_reconnect()
    class TestProcess(Skprocess):
        def __run__(self):
            pass
    
    assert TestProcess._auto_reconnect_enabled is True
    assert TestProcess._auto_reconnect_kwargs == {}


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
    captured_kwargs = {}
    def mock_reconnect(**kwargs):
        captured_kwargs.update(kwargs)
        return "mocked"
    rec.reconnect = mock_reconnect
    
    overrides = {
        "psycopg2.Connection": {
            "*": {"user": "testuser", "password": "testpass"}
        }
    }
    
    reconnect_all(obj, **overrides)
    
    assert captured_kwargs == {"user": "testuser", "password": "testpass"}, \
        f"Expected user/password overrides, got {captured_kwargs}"


# =============================================================================
# Main
# =============================================================================

def run_all_tests():
    runner = TestRunner("Reconnect Tests")
    
    # Basic functionality
    runner.run_test("reconnect_all no overrides", test_reconnect_all_no_overrides)
    runner.run_test("reconnect_all in dict", test_reconnect_all_in_dict)
    runner.run_test("reconnect_all in list", test_reconnect_all_in_list)
    runner.run_test("reconnect_all in object dict", test_reconnect_all_in_object_dict)
    
    # Overrides
    runner.run_test("overrides type key lookup", test_reconnect_all_overrides_type_key)
    runner.run_test("overrides attr-specific", test_reconnect_all_overrides_attr_specific)
    runner.run_test("overrides merge", test_reconnect_all_overrides_merge)
    runner.run_test("overrides multiple types", test_reconnect_all_overrides_multiple_types)
    runner.run_test("overrides no match", test_reconnect_all_overrides_no_match)
    runner.run_test("type key normalization", test_reconnect_all_type_key_normalization)
    
    # auto_reconnect decorator
    runner.run_test("auto_reconnect sets flags", test_auto_reconnect_decorator_sets_flags)
    runner.run_test("auto_reconnect empty", test_auto_reconnect_empty)
    
    # Real DbReconnector
    runner.run_test("real DbReconnector type key", test_real_db_reconnector_type_key)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
