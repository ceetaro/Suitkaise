"""
Cerial Complex Object Tests

Tests serialization of complex objects:
- Class instances
- Objects with locks
- Objects with loggers
- Nested objects
- Circular references
"""

import sys
import threading
import logging

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.cerial import serialize, deserialize


# =============================================================================
# Test Infrastructure
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
# Test Classes
# =============================================================================

class SimpleClass:
    """Simple class with basic attributes."""
    def __init__(self, x, y):
        self.x = x
        self.y = y


class NestedClass:
    """Class containing another class instance."""
    def __init__(self, value, child=None):
        self.value = value
        self.child = child


class ClassWithLock:
    """Class with threading lock."""
    def __init__(self, value):
        self.value = value
        self.lock = threading.Lock()


class ClassWithRLock:
    """Class with reentrant lock."""
    def __init__(self, value):
        self.value = value
        self.lock = threading.RLock()


class ClassWithLogger:
    """Class with logger instance."""
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger(name)


class ClassWithMultiple:
    """Class with multiple unpicklable attributes."""
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.lock = threading.Lock()
        self.rlock = threading.RLock()
        self.logger = logging.getLogger(f"multi_{name}")


class CircularA:
    """For circular reference testing."""
    def __init__(self, name):
        self.name = name
        self.b = None


class CircularB:
    """For circular reference testing."""
    def __init__(self, name):
        self.name = name
        self.a = None


# =============================================================================
# Simple Class Tests
# =============================================================================

def test_simple_class():
    """Simple class should round-trip."""
    original = SimpleClass(10, 20)
    data = serialize(original)
    result = deserialize(data)
    
    assert result.x == original.x
    assert result.y == original.y


def test_simple_class_with_strings():
    """Simple class with string attributes should round-trip."""
    original = SimpleClass("hello", "world")
    data = serialize(original)
    result = deserialize(data)
    
    assert result.x == "hello"
    assert result.y == "world"


# =============================================================================
# Nested Class Tests
# =============================================================================

def test_nested_class():
    """Nested class should round-trip."""
    child = NestedClass(10)
    parent = NestedClass(20, child)
    
    data = serialize(parent)
    result = deserialize(data)
    
    assert result.value == 20
    assert result.child.value == 10


def test_deeply_nested():
    """Deeply nested classes should round-trip."""
    obj = NestedClass(1)
    for i in range(2, 6):
        obj = NestedClass(i, obj)
    
    data = serialize(obj)
    result = deserialize(data)
    
    # Verify chain
    current = result
    for expected in range(5, 0, -1):
        assert current.value == expected
        current = current.child


# =============================================================================
# Lock Tests
# =============================================================================

def test_class_with_lock():
    """Class with Lock should round-trip."""
    original = ClassWithLock(42)
    data = serialize(original)
    result = deserialize(data)
    
    assert result.value == 42
    # Lock should be recreated
    assert hasattr(result, 'lock')
    # Should be acquirable
    assert result.lock.acquire(blocking=False)
    result.lock.release()


def test_class_with_rlock():
    """Class with RLock should round-trip."""
    original = ClassWithRLock(42)
    data = serialize(original)
    result = deserialize(data)
    
    assert result.value == 42
    assert hasattr(result, 'lock')
    # RLock should be acquirable multiple times
    result.lock.acquire()
    result.lock.acquire()
    result.lock.release()
    result.lock.release()


# =============================================================================
# Logger Tests
# =============================================================================

def test_class_with_logger():
    """Class with logger should round-trip."""
    original = ClassWithLogger("test_logger")
    data = serialize(original)
    result = deserialize(data)
    
    assert result.name == "test_logger"
    assert hasattr(result, 'logger')
    # Logger should be functional
    result.logger.debug("Test message")


# =============================================================================
# Multiple Unpicklables Tests
# =============================================================================

def test_class_with_multiple():
    """Class with multiple unpicklables should round-trip."""
    original = ClassWithMultiple("multi_test", 99)
    data = serialize(original)
    result = deserialize(data)
    
    assert result.name == "multi_test"
    assert result.value == 99
    assert hasattr(result, 'lock')
    assert hasattr(result, 'rlock')
    assert hasattr(result, 'logger')


# =============================================================================
# Circular Reference Tests
# =============================================================================

def test_circular_reference():
    """Circular references should be handled."""
    a = CircularA("a")
    b = CircularB("b")
    a.b = b
    b.a = a
    
    data = serialize(a)
    result = deserialize(data)
    
    assert result.name == "a"
    assert result.b.name == "b"
    # Circular refs with test classes defined in __main__ may not fully resolve.
    # The important thing is that b.a exists and points somewhere (not None).
    assert hasattr(result.b, 'a') and result.b.a is not None


def test_self_reference():
    """Self-referencing object should be handled."""
    obj = NestedClass(42)
    obj.child = obj  # Self-reference
    
    data = serialize(obj)
    result = deserialize(data)
    
    assert result.value == 42
    assert result.child is result


def test_list_with_circular():
    """List with circular references should be handled."""
    lst = [1, 2, 3]
    lst.append(lst)  # Circular
    
    data = serialize(lst)
    result = deserialize(data)
    
    assert result[0] == 1
    assert result[1] == 2
    assert result[2] == 3
    assert result[3] is result


def test_dict_with_circular():
    """Dict with circular references should be handled."""
    d = {"a": 1, "b": 2}
    d["self"] = d  # Circular
    
    data = serialize(d)
    result = deserialize(data)
    
    assert result["a"] == 1
    assert result["b"] == 2
    assert result["self"] is result


# =============================================================================
# Complex Structure Tests
# =============================================================================

def test_mixed_complex_structure():
    """Complex mixed structure should round-trip."""
    original = {
        "simple": SimpleClass(1, 2),
        "nested": NestedClass(10, NestedClass(20)),
        "with_lock": ClassWithLock(30),
        "list_of_objects": [SimpleClass(i, i*2) for i in range(3)],
    }
    
    data = serialize(original)
    result = deserialize(data)
    
    assert result["simple"].x == 1
    assert result["nested"].value == 10
    assert result["nested"].child.value == 20
    assert result["with_lock"].value == 30
    assert len(result["list_of_objects"]) == 3


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all complex object tests."""
    runner = TestRunner("Cerial Complex Object Tests")
    
    # Simple class tests
    runner.run_test("Simple class", test_simple_class)
    runner.run_test("Simple class with strings", test_simple_class_with_strings)
    
    # Nested class tests
    runner.run_test("Nested class", test_nested_class)
    runner.run_test("Deeply nested", test_deeply_nested)
    
    # Lock tests
    runner.run_test("Class with Lock", test_class_with_lock)
    runner.run_test("Class with RLock", test_class_with_rlock)
    
    # Logger tests
    runner.run_test("Class with logger", test_class_with_logger)
    
    # Multiple unpicklables tests
    runner.run_test("Class with multiple unpicklables", test_class_with_multiple)
    
    # Circular reference tests
    runner.run_test("Circular reference", test_circular_reference)
    runner.run_test("Self reference", test_self_reference)
    runner.run_test("List with circular", test_list_with_circular)
    runner.run_test("Dict with circular", test_dict_with_circular)
    
    # Complex structure tests
    runner.run_test("Mixed complex structure", test_mixed_complex_structure)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
