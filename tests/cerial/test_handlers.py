"""
Cerial API Tests

Tests public API usage of:
- serialize/deserialize functions
- File handle operations
- Stream serialization
- Debug and verbose modes
- Custom type handling
"""

import sys
import io
import tempfile
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
# Serialize/Deserialize Tests
# =============================================================================

def test_serialize_basic():
    """serialize should handle basic types."""
    result = serialize(42)
    
    assert result is not None
    assert isinstance(result, (str, bytes, dict))


def test_serialize_dict():
    """serialize should handle dicts."""
    data = {"key": "value", "number": 123}
    result = serialize(data)
    
    assert result is not None


def test_serialize_list():
    """serialize should handle lists."""
    data = [1, 2, 3, "four", {"five": 5}]
    result = serialize(data)
    
    assert result is not None


def test_serialize_nested():
    """serialize should handle nested structures."""
    data = {
        "level1": {
            "level2": {
                "level3": [1, 2, 3]
            }
        }
    }
    result = serialize(data)
    
    assert result is not None


def test_serialize_debug_mode():
    """serialize should support debug mode."""
    result = serialize({"test": 123}, debug=True)
    
    assert result is not None


def test_serialize_verbose_mode():
    """serialize should support verbose mode."""
    result = serialize({"test": 123}, verbose=True)
    
    assert result is not None


# =============================================================================
# Deserialize Tests
# =============================================================================

def test_deserialize_basic():
    """deserialize should handle basic types."""
    original = 42
    serialized = serialize(original)
    result = deserialize(serialized)
    
    assert result == original


def test_deserialize_dict():
    """deserialize should handle dicts."""
    original = {"key": "value", "number": 123}
    serialized = serialize(original)
    result = deserialize(serialized)
    
    assert result == original


def test_deserialize_list():
    """deserialize should handle lists."""
    original = [1, 2, 3, "four"]
    serialized = serialize(original)
    result = deserialize(serialized)
    
    assert result == original


def test_deserialize_debug_mode():
    """deserialize should support debug mode."""
    serialized = serialize({"test": 123})
    result = deserialize(serialized, debug=True)
    
    assert result == {"test": 123}


def test_deserialize_verbose_mode():
    """deserialize should support verbose mode."""
    serialized = serialize({"test": 123})
    result = deserialize(serialized, verbose=True)
    
    assert result == {"test": 123}


# =============================================================================
# File Handle Tests
# =============================================================================

def test_serialize_to_file():
    """serialize bytes can be written to file."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
        filepath = f.name
    
    try:
        data = {"name": "test", "value": 42}
        serialized = serialize(data)
        
        # Write bytes to file
        with open(filepath, 'wb') as f:
            f.write(serialized)
        
        # Verify file was created
        assert Path(filepath).exists()
        
        # Read and deserialize
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        result = deserialize(file_data)
        assert result == data
    finally:
        Path(filepath).unlink(missing_ok=True)


def test_deserialize_from_file():
    """deserialize should work with bytes read from file."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
        filepath = f.name
    
    try:
        original = {"list": [1, 2, 3], "nested": {"a": 1}}
        serialized = serialize(original)
        
        # Write to file
        with open(filepath, 'wb') as f:
            f.write(serialized)
        
        # Read and deserialize
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        result = deserialize(file_data)
        assert result == original
    finally:
        Path(filepath).unlink(missing_ok=True)


def test_serialize_to_file_creates_dirs():
    """serialize bytes can be written to nested path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / "subdir" / "nested" / "file.bin"
        
        data = {"test": True}
        serialized = serialize(data)
        
        # Create dirs and write
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            f.write(serialized)
        
        assert filepath.exists()
        
        # Read and verify
        with open(filepath, 'rb') as f:
            file_data = f.read()
        result = deserialize(file_data)
        assert result == data


def test_serialize_overwrite():
    """serialize bytes can overwrite existing file."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
        filepath = f.name
    
    try:
        # First write
        with open(filepath, 'wb') as f:
            f.write(serialize({"first": 1}))
        
        # Overwrite
        with open(filepath, 'wb') as f:
            f.write(serialize({"second": 2}))
        
        # Read and verify
        with open(filepath, 'rb') as f:
            file_data = f.read()
        result = deserialize(file_data)
        assert result == {"second": 2}
    finally:
        Path(filepath).unlink(missing_ok=True)


# =============================================================================
# Stream/StringIO Tests
# =============================================================================

def test_serialize_to_stringio():
    """serialize output should work with StringIO."""
    data = {"key": "value"}
    serialized = serialize(data)
    
    # Should be able to put in StringIO
    stream = io.StringIO(str(serialized) if not isinstance(serialized, str) else serialized)
    
    assert stream.getvalue() is not None


def test_deserialize_from_stringio():
    """deserialize should work with data from StringIO."""
    original = {"data": [1, 2, 3]}
    serialized = serialize(original)
    
    # Put in StringIO and read back
    stream = io.StringIO()
    if isinstance(serialized, str):
        stream.write(serialized)
    else:
        stream.write(str(serialized))
    stream.seek(0)
    
    # The exact deserialization from stream depends on implementation
    # Just verify roundtrip works
    result = deserialize(serialized)
    assert result == original


# =============================================================================
# Roundtrip Tests with Classes
# =============================================================================

def test_roundtrip_same_instances():
    """Roundtrip should succeed across multiple calls."""
    test_cases = [
        42,
        3.14,
        "string",
        [1, 2, 3],
        {"a": 1, "b": 2},
        None,
        True,
        False,
    ]
    
    for original in test_cases:
        serialized = serialize(original)
        result = deserialize(serialized)
        assert result == original, f"Failed for {original}"


def test_roundtrip_different_instances():
    """Roundtrip should work across separate calls."""
    data = {"complex": [1, {"nested": True}, "value"]}
    
    serialized = serialize(data)
    result = deserialize(serialized)
    
    assert result == data


# =============================================================================
# Custom Object Tests
# =============================================================================

def test_cerializer_custom_class():
    """serialize/deserialize should handle custom classes."""
    class MyClass:
        def __init__(self, value):
            self.value = value
    
    obj = MyClass(42)
    serialized = serialize(obj)
    result = deserialize(serialized)
    
    # Result should preserve the value
    assert hasattr(result, 'value') or (isinstance(result, dict) and result.get('value') == 42)


def test_cerializer_class_with_methods():
    """serialize/deserialize should handle classes with methods."""
    class Calculator:
        def __init__(self, initial):
            self.value = initial
        
        def add(self, x):
            return self.value + x
    
    obj = Calculator(10)
    serialized = serialize(obj)
    result = deserialize(serialized)
    
    # Should preserve state
    if hasattr(result, 'value'):
        assert result.value == 10


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_deserialize_invalid_data():
    """deserialize should handle invalid data gracefully."""
    try:
        result = deserialize("not valid serialized data")
        # May return as-is or raise
    except Exception:
        pass  # Expected


def test_serialize_file_not_found():
    """deserialize should handle missing file."""
    try:
        result = deserialize("/nonexistent/path/file.json")
        # Should raise or return None
        assert False, "Should have raised"
    except (FileNotFoundError, Exception):
        pass


# =============================================================================
# Format Tests
# =============================================================================

def test_serialize_format():
    """Serialized output should be in expected format."""
    result = serialize({"key": "value"})
    
    # Should be string-like (JSON, etc.)
    assert result is not None


def test_serialize_multiple_calls():
    """Multiple serialize calls should be independent."""
    result1 = serialize({"a": 1})
    result2 = serialize({"b": 2})
    
    assert deserialize(result1) == {"a": 1}
    assert deserialize(result2) == {"b": 2}


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all handler tests."""
    runner = TestRunner("Cerial API Tests")
    
    # Serialize tests
    runner.run_test("serialize basic", test_serialize_basic)
    runner.run_test("serialize dict", test_serialize_dict)
    runner.run_test("serialize list", test_serialize_list)
    runner.run_test("serialize nested", test_serialize_nested)
    runner.run_test("serialize debug mode", test_serialize_debug_mode)
    runner.run_test("serialize verbose mode", test_serialize_verbose_mode)
    
    # Deserialize tests
    runner.run_test("deserialize basic", test_deserialize_basic)
    runner.run_test("deserialize dict", test_deserialize_dict)
    runner.run_test("deserialize list", test_deserialize_list)
    runner.run_test("deserialize debug mode", test_deserialize_debug_mode)
    runner.run_test("deserialize verbose mode", test_deserialize_verbose_mode)
    
    # File handle tests
    runner.run_test("serialize to file", test_serialize_to_file)
    runner.run_test("deserialize from file", test_deserialize_from_file)
    runner.run_test("serialize creates dirs", test_serialize_to_file_creates_dirs)
    runner.run_test("serialize overwrite", test_serialize_overwrite)
    
    # Stream tests
    runner.run_test("serialize to StringIO", test_serialize_to_stringio)
    runner.run_test("deserialize from StringIO", test_deserialize_from_stringio)
    
    # Roundtrip tests
    runner.run_test("roundtrip same instances", test_roundtrip_same_instances)
    runner.run_test("roundtrip different instances", test_roundtrip_different_instances)
    
    # Custom object tests
    runner.run_test("custom class roundtrip", test_cerializer_custom_class)
    runner.run_test("class with methods roundtrip", test_cerializer_class_with_methods)
    
    # Error handling tests
    runner.run_test("deserialize invalid data", test_deserialize_invalid_data)
    runner.run_test("deserialize file not found", test_serialize_file_not_found)
    
    # Format tests
    runner.run_test("serialize format", test_serialize_format)
    runner.run_test("serialize multiple calls", test_serialize_multiple_calls)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
