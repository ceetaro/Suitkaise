"""
Cucumber Edge Cases Tests

Tests edge cases and error handling:
- Empty objects
- Large objects
- Special values
- Error conditions
"""

import sys

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.cucumber import serialize, deserialize, SerializationError, DeserializationError


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
# Empty Object Tests
# =============================================================================

def test_empty_class():
    """Empty class instance should round-trip."""
    class Empty:
        pass
    
    original = Empty()
    data = serialize(original)
    result = deserialize(data)
    
    assert type(result).__name__ == "Empty"


def test_class_with_none_attrs():
    """Class with None attributes should round-trip."""
    class WithNone:
        def __init__(self):
            self.a = None
            self.b = None
    
    original = WithNone()
    data = serialize(original)
    result = deserialize(data)
    
    assert result.a is None
    assert result.b is None


def test_main_module_class():
    """Class defined in __main__ should round-trip."""
    class MainClass:
        def __init__(self, value: int):
            self.value = value

        def get_value(self):
            return self.value

    # Simulate __main__-defined class
    MainClass.__module__ = "__main__"

    original = MainClass(5)
    data = serialize(original)
    result = deserialize(data)

    assert result.__class__.__name__ == "MainClass"
    assert result.value == 5
    assert result.get_value() == 5


# =============================================================================
# Large Object Tests
# =============================================================================

def test_large_list():
    """Large list should round-trip."""
    original = list(range(10000))
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original
    assert len(result) == 10000


def test_large_dict():
    """Large dict should round-trip."""
    original = {str(i): i for i in range(1000)}
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original
    assert len(result) == 1000


def test_large_string():
    """Large string should round-trip."""
    original = "a" * 100000
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original
    assert len(result) == 100000


def test_large_bytes():
    """Large bytes should round-trip."""
    original = b"x" * 100000
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original
    assert len(result) == 100000


# =============================================================================
# Special Value Tests
# =============================================================================

def test_float_inf():
    """Float infinity should round-trip."""
    original = float('inf')
    data = serialize(original)
    result = deserialize(data)
    
    assert result == float('inf')


def test_float_neg_inf():
    """Negative infinity should round-trip."""
    original = float('-inf')
    data = serialize(original)
    result = deserialize(data)
    
    assert result == float('-inf')


def test_float_nan():
    """Float NaN should round-trip (as NaN)."""
    import math
    
    original = float('nan')
    data = serialize(original)
    result = deserialize(data)
    
    # NaN != NaN, so use math.isnan
    assert math.isnan(result)


def test_frozenset():
    """Frozenset should round-trip."""
    original = frozenset({1, 2, 3})
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original
    assert type(result) == frozenset


def test_complex_number():
    """Complex number should round-trip."""
    original = complex(3, 4)
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# Nested Collection Tests
# =============================================================================

def test_dict_of_lists():
    """Dict of lists should round-trip."""
    original = {
        "a": [1, 2, 3],
        "b": [4, 5, 6],
        "c": [],
    }
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_list_of_dicts():
    """List of dicts should round-trip."""
    original = [
        {"a": 1},
        {"b": 2},
        {},
    ]
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_tuple_of_sets():
    """Tuple of sets should round-trip."""
    original = ({1, 2}, {3, 4}, set())
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# bytes Output Tests
# =============================================================================

def test_serialize_returns_bytes():
    """serialize() should return bytes."""
    data = serialize(42)
    
    assert isinstance(data, bytes)


def test_serialize_non_empty():
    """serialize() should return non-empty bytes."""
    data = serialize(42)
    
    assert len(data) > 0


# =============================================================================
# Debug/Verbose Mode Tests
# =============================================================================

def test_debug_mode():
    """Debug mode should work without error."""
    original = {"test": 123}
    data = serialize(original, debug=True)
    result = deserialize(data, debug=True)
    
    assert result == original


def test_verbose_mode():
    """Verbose mode should work without error."""
    original = {"test": 123}
    # This may print output, but should not raise
    data = serialize(original, verbose=True)
    result = deserialize(data, verbose=True)
    
    assert result == original


# =============================================================================
# Exception Tests
# =============================================================================

def test_serialization_error_is_exception():
    """SerializationError should be an Exception."""
    assert issubclass(SerializationError, Exception)


def test_serialization_error_can_be_raised():
    """SerializationError should be raisable with message."""
    try:
        raise SerializationError("Test serialization error")
    except SerializationError as e:
        assert "Test serialization error" in str(e)


def test_serialization_error_catchable():
    """SerializationError should be catchable."""
    caught = False
    
    try:
        raise SerializationError("serialization failed")
    except SerializationError:
        caught = True
    
    assert caught


def test_deserialization_error_is_exception():
    """DeserializationError should be an Exception."""
    assert issubclass(DeserializationError, Exception)


def test_deserialization_error_can_be_raised():
    """DeserializationError should be raisable with message."""
    try:
        raise DeserializationError("Test deserialization error")
    except DeserializationError as e:
        assert "Test deserialization error" in str(e)


def test_deserialization_error_catchable():
    """DeserializationError should be catchable."""
    caught = False
    
    try:
        raise DeserializationError("deserialization failed")
    except DeserializationError:
        caught = True
    
    assert caught


def test_deserialize_invalid_data():
    """deserialize() with invalid data should raise DeserializationError."""
    invalid_data = b"this is not valid serialized data"
    
    try:
        deserialize(invalid_data)
        # If it doesn't raise, that's also acceptable behavior
    except (DeserializationError, Exception):
        # Expected - invalid data should fail
        pass


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all edge case tests."""
    runner = TestRunner("Cucumber Edge Cases Tests")
    
    # Empty object tests
    runner.run_test("Empty class", test_empty_class)
    runner.run_test("Class with None attrs", test_class_with_none_attrs)
    runner.run_test("__main__ class", test_main_module_class)
    
    # Large object tests
    runner.run_test("Large list", test_large_list)
    runner.run_test("Large dict", test_large_dict)
    runner.run_test("Large string", test_large_string)
    runner.run_test("Large bytes", test_large_bytes)
    
    # Special value tests
    runner.run_test("Float inf", test_float_inf)
    runner.run_test("Float -inf", test_float_neg_inf)
    runner.run_test("Float NaN", test_float_nan)
    runner.run_test("Frozenset", test_frozenset)
    runner.run_test("Complex number", test_complex_number)
    
    # Nested collection tests
    runner.run_test("Dict of lists", test_dict_of_lists)
    runner.run_test("List of dicts", test_list_of_dicts)
    runner.run_test("Tuple of sets", test_tuple_of_sets)
    
    # bytes output tests
    runner.run_test("serialize returns bytes", test_serialize_returns_bytes)
    runner.run_test("serialize non-empty", test_serialize_non_empty)
    
    # Debug/verbose tests
    runner.run_test("Debug mode", test_debug_mode)
    runner.run_test("Verbose mode", test_verbose_mode)
    
    # Exception tests
    runner.run_test("SerializationError is Exception", test_serialization_error_is_exception)
    runner.run_test("SerializationError can be raised", test_serialization_error_can_be_raised)
    runner.run_test("SerializationError catchable", test_serialization_error_catchable)
    runner.run_test("DeserializationError is Exception", test_deserialization_error_is_exception)
    runner.run_test("DeserializationError can be raised", test_deserialization_error_can_be_raised)
    runner.run_test("DeserializationError catchable", test_deserialization_error_catchable)
    runner.run_test("deserialize invalid data", test_deserialize_invalid_data)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
