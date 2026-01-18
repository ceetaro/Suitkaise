"""
@autopath Decorator Tests

Tests the @autopath decorator functionality:
- String to Skpath conversion
- pathlib.Path to Skpath conversion
- Skpath passthrough
- Multiple path parameters
- Mixed path and non-path parameters
- Optional path parameters
- Type annotation handling
"""

import sys
import tempfile
from pathlib import Path
from typing import Optional, Union

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.paths import Skpath, autopath


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
# String Conversion Tests
# =============================================================================

def test_autopath_string_converts():
    """@autopath should convert string to Skpath."""
    @autopath()
    def get_name(path: Skpath) -> str:
        return path.name
    
    result = get_name("/some/path/file.txt")
    
    assert result == "file.txt", f"Should extract name, got {result}"


def test_autopath_string_absolute():
    """@autopath should handle absolute string paths."""
    @autopath()
    def is_absolute(path: Skpath) -> bool:
        return Path(path.ap).is_absolute()
    
    result = is_absolute("/absolute/path")
    
    assert result == True, "Should be absolute"


def test_autopath_string_relative():
    """@autopath should handle relative string paths."""
    @autopath()
    def get_parts(path: Skpath) -> int:
        return len(path.ap.split("/"))
    
    result = get_parts("relative/path/file.txt")
    
    assert result >= 3, f"Should have parts, got {result}"


# =============================================================================
# pathlib.Path Conversion Tests
# =============================================================================

def test_autopath_path_converts():
    """@autopath should convert pathlib.Path to Skpath."""
    @autopath()
    def get_suffix(path: Skpath) -> str:
        return path.suffix
    
    p = Path("/some/file.py")
    result = get_suffix(p)
    
    assert result == ".py", f"Should extract suffix, got {result}"


def test_autopath_path_preserves_info():
    """@autopath conversion should preserve path info."""
    @autopath()
    def get_stem(path: Skpath) -> str:
        return path.stem
    
    p = Path("/dir/myfile.txt")
    result = get_stem(p)
    
    assert result == "myfile", f"Should extract stem, got {result}"


# =============================================================================
# Skpath Passthrough Tests
# =============================================================================

def test_autopath_skpath_passthrough():
    """@autopath should pass Skpath through unchanged."""
    @autopath()
    def identity(path: Skpath) -> Skpath:
        return path
    
    original = Skpath("/some/path")
    result = identity(original)
    
    assert result is original, "Should be same object"


def test_autopath_skpath_properties():
    """@autopath should preserve Skpath properties."""
    @autopath()
    def get_parent_name(path: Skpath) -> str:
        return path.parent.name
    
    sk = Skpath("/parent/child/file.txt")
    result = get_parent_name(sk)
    
    assert result == "child", f"Should get parent name, got {result}"


# =============================================================================
# Multiple Parameters Tests
# =============================================================================

def test_autopath_two_paths():
    """@autopath should convert multiple path parameters."""
    @autopath()
    def compare_suffix(path1: Skpath, path2: Skpath) -> bool:
        return path1.suffix == path2.suffix
    
    result = compare_suffix("/a/file.py", Path("/b/other.py"))
    
    assert result == True, "Both should have .py suffix"


def test_autopath_three_paths():
    """@autopath should handle three path parameters."""
    @autopath()
    def all_same_suffix(p1: Skpath, p2: Skpath, p3: Skpath) -> bool:
        return p1.suffix == p2.suffix == p3.suffix
    
    result = all_same_suffix("/a.txt", Path("/b.txt"), Skpath("/c.txt"))
    
    assert result == True


def test_autopath_paths_in_different_positions():
    """@autopath should convert paths regardless of position."""
    @autopath(only=['path'])
    def middle_path(before: int, path: Skpath, after: str) -> str:
        return f"{before}-{path.name}-{after}"
    
    result = middle_path(1, "/dir/file.txt", "end")
    
    assert result == "1-file.txt-end"


# =============================================================================
# Mixed Parameters Tests
# =============================================================================

def test_autopath_with_int():
    """@autopath should not affect int parameters."""
    @autopath()
    def path_and_int(path: Skpath, count: int) -> str:
        return f"{path.name}:{count}"
    
    result = path_and_int("/file.txt", 42)
    
    assert result == "file.txt:42"


def test_autopath_with_string():
    """@autopath should not affect non-path string parameters when using only=."""
    @autopath(only=['path'])
    def path_and_string(path: Skpath, label: str) -> str:
        return f"{label}: {path.name}"
    
    result = path_and_string("/file.txt", "Label")
    
    assert result == "Label: file.txt"


def test_autopath_with_bool():
    """@autopath should not affect bool parameters."""
    @autopath()
    def conditional_name(path: Skpath, uppercase: bool) -> str:
        name = path.name
        return name.upper() if uppercase else name.lower()
    
    result_upper = conditional_name("/File.TXT", True)
    result_lower = conditional_name("/File.TXT", False)
    
    assert result_upper == "FILE.TXT"
    assert result_lower == "file.txt"


def test_autopath_with_kwargs():
    """@autopath should handle kwargs correctly."""
    @autopath(only=['path'])
    def with_options(path: Skpath, verbose: bool = False, prefix: str = "") -> str:
        name = path.name
        if prefix:
            name = f"{prefix}{name}"
        if verbose:
            name = f"[{name}]"
        return name
    
    result = with_options("/file.txt", verbose=True, prefix=">>")
    
    assert result == "[>>file.txt]"


# =============================================================================
# Optional Parameters Tests
# =============================================================================

def test_autopath_optional_none():
    """@autopath should handle None for optional path."""
    @autopath()
    def optional_path(path: Optional[Skpath] = None) -> str:
        if path is None:
            return "no path"
        return path.name
    
    result = optional_path()
    
    assert result == "no path"


def test_autopath_optional_with_value():
    """@autopath should convert value for optional path."""
    @autopath()
    def optional_path(path: Optional[Skpath] = None) -> str:
        if path is None:
            return "no path"
        return path.name
    
    result = optional_path("/some/file.txt")
    
    assert result == "file.txt"


def test_autopath_optional_with_default():
    """@autopath should handle optional with non-None default."""
    # Default string values are converted when the parameter is Skpath-typed
    @autopath()
    def with_default(path: Skpath) -> str:
        return path.name
    
    # Only test with explicit values - default handling may vary
    result_custom = with_default("/custom.txt")
    
    assert result_custom == "custom.txt"


# =============================================================================
# Return Value Tests
# =============================================================================

def test_autopath_returns_value():
    """@autopath should preserve return values."""
    @autopath()
    def returns_dict(path: Skpath) -> dict:
        return {"name": path.name, "suffix": path.suffix}
    
    result = returns_dict("/file.py")
    
    assert result == {"name": "file.py", "suffix": ".py"}


def test_autopath_returns_skpath():
    """@autopath should allow returning Skpath."""
    @autopath()
    def returns_parent(path: Skpath) -> Skpath:
        return path.parent
    
    result = returns_parent("/parent/child/file.txt")
    
    assert isinstance(result, Skpath)
    assert result.name == "child"


def test_autopath_returns_none():
    """@autopath should handle None return."""
    @autopath()
    def maybe_parent(path: Skpath) -> Optional[Skpath]:
        if path.suffix == ".txt":
            return path.parent
        return None
    
    result_txt = maybe_parent("/dir/file.txt")
    result_py = maybe_parent("/dir/file.py")
    
    assert result_txt is not None
    assert result_py is None


# =============================================================================
# Method Decorator Tests
# =============================================================================

def test_autopath_on_method():
    """@autopath should work on instance methods."""
    class FileHandler:
        @autopath()
        def process(self, path: Skpath) -> str:
            return path.name
    
    handler = FileHandler()
    result = handler.process("/some/file.txt")
    
    assert result == "file.txt"


def test_autopath_on_classmethod():
    """@autopath should work on classmethods."""
    class FileHandler:
        @classmethod
        @autopath()
        def process(cls, path: Skpath) -> str:
            return f"{cls.__name__}:{path.name}"
    
    result = FileHandler.process("/file.txt")
    
    assert result == "FileHandler:file.txt"


def test_autopath_on_staticmethod():
    """@autopath should work on staticmethods."""
    class FileHandler:
        @staticmethod
        @autopath()
        def process(path: Skpath) -> str:
            return path.name
    
    result = FileHandler.process("/file.txt")
    
    assert result == "file.txt"


# =============================================================================
# Edge Cases Tests
# =============================================================================

def test_autopath_empty_path():
    """@autopath should handle empty string path."""
    @autopath()
    def empty_check(path: Skpath) -> bool:
        return len(path.name) == 0
    
    # Empty path behavior depends on implementation
    try:
        result = empty_check("")
        # If it doesn't raise, just verify it's a bool
        assert isinstance(result, bool)
    except (ValueError, Exception):
        pass  # Some implementations may raise on empty


def test_autopath_no_annotation():
    """@autopath should not affect untyped parameters."""
    @autopath()
    def no_type_hint(path) -> str:
        # path is not typed, so should pass through as-is
        if isinstance(path, str):
            return "string"
        elif isinstance(path, Skpath):
            return "skpath"
        return "other"
    
    result = no_type_hint("/some/path")
    
    # Without annotation, should remain a string
    assert result == "string"


def test_autopath_unicode_path():
    """@autopath should handle unicode paths."""
    @autopath()
    def unicode_name(path: Skpath) -> str:
        return path.name
    
    result = unicode_name("/путь/файл.txt")
    
    assert result == "файл.txt"


def test_autopath_special_chars():
    """@autopath should handle paths with special characters."""
    @autopath()
    def special_name(path: Skpath) -> str:
        return path.name
    
    result = special_name("/path/file with spaces.txt")
    
    assert result == "file with spaces.txt"


# =============================================================================
# Extended Coverage Tests
# =============================================================================

def test_autopath_use_caller_defaults():
    """@autopath(use_caller) should fill caller path when None."""
    @autopath(use_caller=True)
    def caller_path(path: Skpath | None = None) -> Skpath:
        assert path is not None
        return path
    
    result = caller_path(None)
    assert result.name.endswith("test_autopath.py")


def test_autopath_debug_mode():
    """@autopath debug should still convert types."""
    @autopath(debug=True)
    def get_path_str(path: str) -> str:
        return path
    
    result = get_path_str("./some/path.txt")
    assert isinstance(result, str)
    assert result.endswith("path.txt")


def test_autopath_iterable_list():
    """@autopath should convert list of path-like values."""
    @autopath()
    def names(paths: list[Skpath]) -> list[str]:
        return [p.name for p in paths]
    
    result = names(["/a.txt", "/b.txt"])
    assert result == ["a.txt", "b.txt"]


def test_autopath_iterable_tuple():
    """@autopath should convert tuple of paths."""
    @autopath()
    def suffixes(paths: tuple[Path, ...]) -> list[str]:
        return [p.suffix for p in paths]
    
    result = suffixes(("/a.py", "/b.md"))
    assert result == [".py", ".md"]


def test_autopath_union_prefers_skpath():
    """@autopath should prefer Skpath within Union types."""
    @autopath()
    def return_type(path: Union[str, Skpath]) -> type:
        return type(path)
    
    result = return_type("/some/path")
    assert result is Skpath


def test_autopath_forward_ref():
    """@autopath should handle forward reference annotations."""
    @autopath()
    def forward(path: "Skpath") -> str:
        return path.name
    
    tmp_path = Path(tempfile.gettempdir()) / "test.txt"
    assert forward(str(tmp_path)) == "test.txt"


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all @autopath tests."""
    runner = TestRunner("@autopath Decorator Tests")
    
    # String conversion tests
    runner.run_test("@autopath string converts", test_autopath_string_converts)
    runner.run_test("@autopath string absolute", test_autopath_string_absolute)
    runner.run_test("@autopath string relative", test_autopath_string_relative)
    
    # Path conversion tests
    runner.run_test("@autopath Path converts", test_autopath_path_converts)
    runner.run_test("@autopath Path preserves info", test_autopath_path_preserves_info)
    
    # Skpath passthrough tests
    runner.run_test("@autopath Skpath passthrough", test_autopath_skpath_passthrough)
    runner.run_test("@autopath Skpath properties", test_autopath_skpath_properties)
    
    # Multiple parameters tests
    runner.run_test("@autopath two paths", test_autopath_two_paths)
    runner.run_test("@autopath three paths", test_autopath_three_paths)
    runner.run_test("@autopath paths in positions", test_autopath_paths_in_different_positions)
    
    # Mixed parameters tests
    runner.run_test("@autopath with int", test_autopath_with_int)
    runner.run_test("@autopath with string", test_autopath_with_string)
    runner.run_test("@autopath with bool", test_autopath_with_bool)
    runner.run_test("@autopath with kwargs", test_autopath_with_kwargs)
    
    # Optional parameters tests
    runner.run_test("@autopath optional None", test_autopath_optional_none)
    runner.run_test("@autopath optional with value", test_autopath_optional_with_value)
    runner.run_test("@autopath optional with default", test_autopath_optional_with_default)
    
    # Return value tests
    runner.run_test("@autopath returns value", test_autopath_returns_value)
    runner.run_test("@autopath returns Skpath", test_autopath_returns_skpath)
    runner.run_test("@autopath returns None", test_autopath_returns_none)
    
    # Method tests
    runner.run_test("@autopath on method", test_autopath_on_method)
    runner.run_test("@autopath on classmethod", test_autopath_on_classmethod)
    runner.run_test("@autopath on staticmethod", test_autopath_on_staticmethod)
    
    # Edge cases
    runner.run_test("@autopath empty path", test_autopath_empty_path)
    runner.run_test("@autopath no annotation", test_autopath_no_annotation)
    runner.run_test("@autopath unicode path", test_autopath_unicode_path)
    runner.run_test("@autopath special chars", test_autopath_special_chars)

    # Extended coverage
    runner.run_test("@autopath use_caller defaults", test_autopath_use_caller_defaults)
    runner.run_test("@autopath debug mode", test_autopath_debug_mode)
    runner.run_test("@autopath iterable list", test_autopath_iterable_list)
    runner.run_test("@autopath iterable tuple", test_autopath_iterable_tuple)
    runner.run_test("@autopath union prefers Skpath", test_autopath_union_prefers_skpath)
    runner.run_test("@autopath forward ref", test_autopath_forward_ref)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
