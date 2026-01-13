"""
Cerial Primitives Tests

Tests serialization of primitive types:
- int, float, str, bytes, bool, None
- lists, dicts, tuples, sets
"""

import sys

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

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
        return failed == 0


# =============================================================================
# Integer Tests
# =============================================================================

def test_int_positive():
    """Positive integers should round-trip."""
    original = 42
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original
    assert type(result) == int


def test_int_negative():
    """Negative integers should round-trip."""
    original = -42
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_int_zero():
    """Zero should round-trip."""
    original = 0
    data = serialize(original)
    result = deserialize(data)
    
    assert result == 0


def test_int_large():
    """Large integers should round-trip."""
    original = 10**100
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# Float Tests
# =============================================================================

def test_float_positive():
    """Positive floats should round-trip."""
    original = 3.14159
    data = serialize(original)
    result = deserialize(data)
    
    assert abs(result - original) < 0.0001


def test_float_negative():
    """Negative floats should round-trip."""
    original = -3.14159
    data = serialize(original)
    result = deserialize(data)
    
    assert abs(result - original) < 0.0001


def test_float_zero():
    """Zero float should round-trip."""
    original = 0.0
    data = serialize(original)
    result = deserialize(data)
    
    assert result == 0.0


def test_float_scientific():
    """Scientific notation floats should round-trip."""
    original = 1.23e-45
    data = serialize(original)
    result = deserialize(data)
    
    assert abs(result - original) < 1e-50


# =============================================================================
# String Tests
# =============================================================================

def test_str_simple():
    """Simple strings should round-trip."""
    original = "hello world"
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_str_empty():
    """Empty strings should round-trip."""
    original = ""
    data = serialize(original)
    result = deserialize(data)
    
    assert result == ""


def test_str_unicode():
    """Unicode strings should round-trip."""
    original = "Hello 世界 🌍"
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_str_special_chars():
    """Strings with special chars should round-trip."""
    original = "line1\nline2\ttab"
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# Bytes Tests
# =============================================================================

def test_bytes_simple():
    """Simple bytes should round-trip."""
    original = b"hello"
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_bytes_empty():
    """Empty bytes should round-trip."""
    original = b""
    data = serialize(original)
    result = deserialize(data)
    
    assert result == b""


def test_bytes_binary():
    """Binary bytes should round-trip."""
    original = bytes([0, 1, 255, 128, 64])
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# Bool Tests
# =============================================================================

def test_bool_true():
    """True should round-trip."""
    original = True
    data = serialize(original)
    result = deserialize(data)
    
    assert result == True
    assert type(result) == bool


def test_bool_false():
    """False should round-trip."""
    original = False
    data = serialize(original)
    result = deserialize(data)
    
    assert result == False
    assert type(result) == bool


# =============================================================================
# None Tests
# =============================================================================

def test_none():
    """None should round-trip."""
    original = None
    data = serialize(original)
    result = deserialize(data)
    
    assert result is None


# =============================================================================
# List Tests
# =============================================================================

def test_list_empty():
    """Empty list should round-trip."""
    original = []
    data = serialize(original)
    result = deserialize(data)
    
    assert result == []


def test_list_simple():
    """Simple list should round-trip."""
    original = [1, 2, 3, 4, 5]
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_list_mixed():
    """Mixed-type list should round-trip."""
    original = [1, "two", 3.0, True, None]
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_list_nested():
    """Nested list should round-trip."""
    original = [[1, 2], [3, [4, 5]]]
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# Dict Tests
# =============================================================================

def test_dict_empty():
    """Empty dict should round-trip."""
    original = {}
    data = serialize(original)
    result = deserialize(data)
    
    assert result == {}


def test_dict_simple():
    """Simple dict should round-trip."""
    original = {"a": 1, "b": 2, "c": 3}
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_dict_nested():
    """Nested dict should round-trip."""
    original = {"outer": {"inner": {"deep": 42}}}
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


def test_dict_mixed_keys():
    """Dict with various value types should round-trip."""
    original = {
        "int": 42,
        "str": "hello",
        "float": 3.14,
        "list": [1, 2, 3],
        "none": None,
    }
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# Tuple Tests
# =============================================================================

def test_tuple_empty():
    """Empty tuple should round-trip."""
    original = ()
    data = serialize(original)
    result = deserialize(data)
    
    assert result == ()
    assert type(result) == tuple


def test_tuple_simple():
    """Simple tuple should round-trip."""
    original = (1, 2, 3)
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original
    assert type(result) == tuple


def test_tuple_nested():
    """Nested tuple should round-trip."""
    original = ((1, 2), (3, (4, 5)))
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# Set Tests
# =============================================================================

def test_set_empty():
    """Empty set should round-trip."""
    original = set()
    data = serialize(original)
    result = deserialize(data)
    
    assert result == set()
    assert type(result) == set


def test_set_simple():
    """Simple set should round-trip."""
    original = {1, 2, 3, 4, 5}
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original
    assert type(result) == set


def test_set_strings():
    """String set should round-trip."""
    original = {"apple", "banana", "cherry"}
    data = serialize(original)
    result = deserialize(data)
    
    assert result == original


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all primitive tests."""
    runner = TestRunner("Cerial Primitives Tests")
    
    # Integer tests
    runner.run_test("int positive", test_int_positive)
    runner.run_test("int negative", test_int_negative)
    runner.run_test("int zero", test_int_zero)
    runner.run_test("int large", test_int_large)
    
    # Float tests
    runner.run_test("float positive", test_float_positive)
    runner.run_test("float negative", test_float_negative)
    runner.run_test("float zero", test_float_zero)
    runner.run_test("float scientific", test_float_scientific)
    
    # String tests
    runner.run_test("str simple", test_str_simple)
    runner.run_test("str empty", test_str_empty)
    runner.run_test("str unicode", test_str_unicode)
    runner.run_test("str special chars", test_str_special_chars)
    
    # Bytes tests
    runner.run_test("bytes simple", test_bytes_simple)
    runner.run_test("bytes empty", test_bytes_empty)
    runner.run_test("bytes binary", test_bytes_binary)
    
    # Bool tests
    runner.run_test("bool True", test_bool_true)
    runner.run_test("bool False", test_bool_false)
    
    # None tests
    runner.run_test("None", test_none)
    
    # List tests
    runner.run_test("list empty", test_list_empty)
    runner.run_test("list simple", test_list_simple)
    runner.run_test("list mixed", test_list_mixed)
    runner.run_test("list nested", test_list_nested)
    
    # Dict tests
    runner.run_test("dict empty", test_dict_empty)
    runner.run_test("dict simple", test_dict_simple)
    runner.run_test("dict nested", test_dict_nested)
    runner.run_test("dict mixed keys", test_dict_mixed_keys)
    
    # Tuple tests
    runner.run_test("tuple empty", test_tuple_empty)
    runner.run_test("tuple simple", test_tuple_simple)
    runner.run_test("tuple nested", test_tuple_nested)
    
    # Set tests
    runner.run_test("set empty", test_set_empty)
    runner.run_test("set simple", test_set_simple)
    runner.run_test("set strings", test_set_strings)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
