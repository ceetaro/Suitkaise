"""
Path ID Encoding/Decoding Tests

Tests the path ID encoding functions:
- get_id()
- Skpath.id property
- encode_path_id()
- decode_path_id()
- normalize_separators()
"""

import sys
from pathlib import Path

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.paths import Skpath, get_id
# Internal utilities - import from _int
from suitkaise.paths._int import encode_path_id, decode_path_id, normalize_separators


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
# get_id() Tests
# =============================================================================

def test_get_id_returns_string():
    """get_id should return a string."""
    result = get_id("/some/path/file.txt")
    
    assert isinstance(result, str), f"Should return string, got {type(result)}"


def test_get_id_non_empty():
    """get_id should return non-empty string."""
    result = get_id("/some/path")
    
    assert len(result) > 0, "Should not be empty"


def test_get_id_from_string():
    """get_id should work with string path."""
    result = get_id("/path/to/file.txt")
    
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_id_from_path():
    """get_id should work with pathlib.Path."""
    result = get_id(Path("/path/to/file.txt"))
    
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_id_from_skpath():
    """get_id should work with Skpath."""
    sk = Skpath("/path/to/file.txt")
    result = get_id(sk)
    
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_id_different_paths():
    """Different paths should have different IDs."""
    id1 = get_id("/path/file1.txt")
    id2 = get_id("/path/file2.txt")
    
    assert id1 != id2, "Different paths should have different IDs"


def test_get_id_same_path():
    """Same path should have same ID."""
    id1 = get_id("/path/to/file.txt")
    id2 = get_id("/path/to/file.txt")
    
    assert id1 == id2, "Same path should have same ID"


def test_get_id_deterministic():
    """get_id should be deterministic."""
    path = "/some/path/file.txt"
    
    ids = [get_id(path) for _ in range(10)]
    
    assert all(i == ids[0] for i in ids), "Should always return same ID"


# =============================================================================
# Skpath.id Tests
# =============================================================================

def test_skpath_id_property():
    """Skpath should have id property."""
    sk = Skpath("/some/path")
    
    assert hasattr(sk, 'id'), "Should have id property"


def test_skpath_id_returns_string():
    """Skpath.id should return string."""
    sk = Skpath("/some/path")
    
    assert isinstance(sk.id, str)


def test_skpath_id_matches_get_id():
    """Skpath.id should match get_id()."""
    path_str = "/some/path/file.txt"
    
    sk = Skpath(path_str)
    func_id = get_id(path_str)
    
    assert sk.id == func_id, f"IDs should match: {sk.id} vs {func_id}"


def test_skpath_id_consistent():
    """Skpath.id should be consistent across access."""
    sk = Skpath("/path/to/file.txt")
    
    id1 = sk.id
    id2 = sk.id
    
    assert id1 == id2


# =============================================================================
# encode_path_id() Tests
# =============================================================================

def test_encode_path_id_returns_string():
    """encode_path_id should return string."""
    result = encode_path_id("/some/path")
    
    assert isinstance(result, str)


def test_encode_path_id_non_empty():
    """encode_path_id should return non-empty string."""
    result = encode_path_id("/path")
    
    assert len(result) > 0


def test_encode_path_id_safe_chars():
    """encode_path_id should use URL-safe characters."""
    result = encode_path_id("/path/with/slashes")
    
    # Should be base64url safe (no +, /)
    unsafe_chars = set('+/=')
    # Allow = for padding, but check the rest
    result_chars = set(result.replace('=', ''))
    
    # Should only contain alphanumeric, -, _
    for char in result_chars:
        assert char.isalnum() or char in '-_', f"Unsafe char: {char}"


def test_encode_path_id_different_inputs():
    """encode_path_id should produce different outputs for different inputs."""
    e1 = encode_path_id("path1")
    e2 = encode_path_id("path2")
    
    assert e1 != e2


# =============================================================================
# decode_path_id() Tests
# =============================================================================

def test_decode_path_id_roundtrip():
    """decode_path_id should reverse encode_path_id."""
    original = "project/feature/file.txt"
    
    encoded = encode_path_id(original)
    decoded = decode_path_id(encoded)
    
    assert decoded == original, f"Roundtrip failed: {original} -> {encoded} -> {decoded}"


def test_decode_path_id_with_slashes():
    """decode_path_id should handle paths with slashes."""
    original = "/absolute/path/to/file.txt"
    
    encoded = encode_path_id(original)
    decoded = decode_path_id(encoded)
    
    assert decoded == original


def test_decode_path_id_with_spaces():
    """decode_path_id should handle paths with spaces."""
    original = "path with spaces/file name.txt"
    
    encoded = encode_path_id(original)
    decoded = decode_path_id(encoded)
    
    assert decoded == original


def test_decode_path_id_with_unicode():
    """decode_path_id should handle unicode paths."""
    original = "путь/файл.txt"
    
    encoded = encode_path_id(original)
    decoded = decode_path_id(encoded)
    
    assert decoded == original


def test_decode_path_id_with_special_chars():
    """decode_path_id should handle special characters."""
    original = "path/file[1](2).txt"
    
    encoded = encode_path_id(original)
    decoded = decode_path_id(encoded)
    
    assert decoded == original


def test_decode_path_id_empty():
    """decode_path_id should handle empty string."""
    encoded = encode_path_id("")
    decoded = decode_path_id(encoded)
    
    assert decoded == ""


# =============================================================================
# normalize_separators() Tests
# =============================================================================

def test_normalize_separators_forward_slash():
    """normalize_separators should keep forward slashes."""
    result = normalize_separators("path/to/file")
    
    assert "/" in result
    assert "\\" not in result


def test_normalize_separators_backslash():
    """normalize_separators should convert backslashes."""
    result = normalize_separators("path\\to\\file")
    
    assert "\\" not in result, f"Should remove backslashes: {result}"


def test_normalize_separators_mixed():
    """normalize_separators should handle mixed separators."""
    result = normalize_separators("path/to\\file/name")
    
    # Should have consistent separators
    assert "\\" not in result


def test_normalize_separators_no_change():
    """normalize_separators should not change already normalized."""
    original = "path/to/file.txt"
    result = normalize_separators(original)
    
    assert result == original


def test_normalize_separators_empty():
    """normalize_separators should handle empty string."""
    result = normalize_separators("")
    
    assert result == ""


# =============================================================================
# Integration Tests
# =============================================================================

def test_id_can_reconstruct_skpath():
    """ID should be usable to reconstruct/identify path."""
    original_path = "myproject/feature/module.py"
    
    path_id = get_id(original_path)
    
    # In a real system, you'd store the ID and lookup the path
    # Here we just verify the ID is deterministic
    assert get_id(original_path) == path_id


def test_encode_decode_various_paths():
    """encode/decode should work for various path patterns."""
    test_paths = [
        "simple.txt",
        "dir/file.py",
        "/absolute/path/file.txt",
        "path with spaces.txt",
        "path/with/many/levels/deep/file.txt",
        "file.multiple.dots.txt",
        "UPPERCASE/File.TXT",
        "unicode/путь/файл.txt",
        "special/[brackets](parens).txt",
        "",
    ]
    
    for path in test_paths:
        encoded = encode_path_id(path)
        decoded = decode_path_id(encoded)
        assert decoded == path, f"Failed for: {path}"


def test_skpath_id_reversible():
    """Skpath.id should be based on reversible encoding."""
    path_str = "myproject/src/module.py"
    sk = Skpath(path_str)
    
    # The ID should be deterministic
    assert sk.id == get_id(path_str)


# =============================================================================
# Edge Cases Tests
# =============================================================================

def test_id_long_path():
    """ID should handle long paths."""
    long_path = "/".join([f"dir{i}" for i in range(50)]) + "/file.txt"
    
    result = get_id(long_path)
    
    assert isinstance(result, str)
    assert len(result) > 0


def test_encode_decode_long_path():
    """encode/decode should handle long paths."""
    long_path = "/".join([f"directory{i}" for i in range(20)]) + "/filename.txt"
    
    encoded = encode_path_id(long_path)
    decoded = decode_path_id(encoded)
    
    assert decoded == long_path


def test_id_single_char():
    """ID should handle single character path."""
    result = get_id("a")
    
    assert isinstance(result, str)
    assert len(result) > 0


def test_encode_decode_newlines():
    """encode/decode should handle paths with unusual chars."""
    # Note: newlines in paths are unusual but possible
    path = "path\nwith\nnewlines"
    
    encoded = encode_path_id(path)
    decoded = decode_path_id(encoded)
    
    assert decoded == path


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all path ID encoding tests."""
    runner = TestRunner("Path ID Encoding/Decoding Tests")
    
    # get_id tests
    runner.run_test("get_id returns string", test_get_id_returns_string)
    runner.run_test("get_id non-empty", test_get_id_non_empty)
    runner.run_test("get_id from string", test_get_id_from_string)
    runner.run_test("get_id from Path", test_get_id_from_path)
    runner.run_test("get_id from Skpath", test_get_id_from_skpath)
    runner.run_test("get_id different paths", test_get_id_different_paths)
    runner.run_test("get_id same path", test_get_id_same_path)
    runner.run_test("get_id deterministic", test_get_id_deterministic)
    
    # Skpath.id tests
    runner.run_test("Skpath.id property", test_skpath_id_property)
    runner.run_test("Skpath.id returns string", test_skpath_id_returns_string)
    runner.run_test("Skpath.id matches get_id", test_skpath_id_matches_get_id)
    runner.run_test("Skpath.id consistent", test_skpath_id_consistent)
    
    # encode_path_id tests
    runner.run_test("encode_path_id returns string", test_encode_path_id_returns_string)
    runner.run_test("encode_path_id non-empty", test_encode_path_id_non_empty)
    runner.run_test("encode_path_id safe chars", test_encode_path_id_safe_chars)
    runner.run_test("encode_path_id different inputs", test_encode_path_id_different_inputs)
    
    # decode_path_id tests
    runner.run_test("decode_path_id roundtrip", test_decode_path_id_roundtrip)
    runner.run_test("decode_path_id with slashes", test_decode_path_id_with_slashes)
    runner.run_test("decode_path_id with spaces", test_decode_path_id_with_spaces)
    runner.run_test("decode_path_id with unicode", test_decode_path_id_with_unicode)
    runner.run_test("decode_path_id with special chars", test_decode_path_id_with_special_chars)
    runner.run_test("decode_path_id empty", test_decode_path_id_empty)
    
    # normalize_separators tests
    runner.run_test("normalize_separators forward slash", test_normalize_separators_forward_slash)
    runner.run_test("normalize_separators backslash", test_normalize_separators_backslash)
    runner.run_test("normalize_separators mixed", test_normalize_separators_mixed)
    runner.run_test("normalize_separators no change", test_normalize_separators_no_change)
    runner.run_test("normalize_separators empty", test_normalize_separators_empty)
    
    # Integration tests
    runner.run_test("ID can reconstruct Skpath", test_id_can_reconstruct_skpath)
    runner.run_test("encode/decode various paths", test_encode_decode_various_paths)
    runner.run_test("Skpath.id reversible", test_skpath_id_reversible)
    
    # Edge cases
    runner.run_test("ID long path", test_id_long_path)
    runner.run_test("encode/decode long path", test_encode_decode_long_path)
    runner.run_test("ID single char", test_id_single_char)
    runner.run_test("encode/decode newlines", test_encode_decode_newlines)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
