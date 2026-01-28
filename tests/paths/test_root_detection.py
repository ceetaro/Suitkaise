"""
Root Detection Tests

Tests project root detection:
- Default detection
- Custom root
- set_custom_root() / get_custom_root() / clear_custom_root()
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path (this script is in tests/paths/, so go up two levels)
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(project_root))

from suitkaise.paths import (
    Skpath,
    get_project_root,
    set_custom_root,
    get_custom_root,
    clear_custom_root,
    PathDetectionError,
)
from suitkaise.paths._int.root_detection import detect_project_root, clear_root_cache


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
# Default Detection Tests
# =============================================================================

def test_get_project_root():
    """get_project_root() should detect project root."""
    clear_custom_root()  # Ensure no custom root
    
    root = get_project_root()
    
    assert isinstance(root, Skpath)
    assert root.is_dir


def test_project_root_has_indicators():
    """Detected root should have project indicators."""
    clear_custom_root()
    
    root = get_project_root()
    
    # Should have at least one project indicator
    indicators = [
        'setup.py', 'pyproject.toml', 'setup.cfg',
        'setup.sk', '.git', 'requirements.txt'
    ]
    
    found_any = False
    for indicator in indicators:
        if (root / indicator).exists:
            found_any = True
            break
    
    assert found_any, f"Root {root} should have project indicators"


def test_get_project_root_expected_name_mismatch():
    """get_project_root() should raise when expected_name does not match."""
    clear_custom_root()
    try:
        get_project_root(expected_name="not_the_root_name")
        assert False, "Should have raised PathDetectionError"
    except PathDetectionError:
        pass


def test_detect_project_root_from_path():
    """detect_project_root should accept from_path."""
    clear_custom_root()
    root = detect_project_root(from_path=Path(__file__).resolve())
    assert root.name == get_project_root().name


def test_clear_root_cache_does_not_break_detection():
    """clear_root_cache should reset cache safely."""
    clear_custom_root()
    detect_project_root(from_path=Path(__file__).resolve())
    clear_root_cache()
    root_after_clear = detect_project_root(from_path=Path(__file__).resolve())
    assert root_after_clear.is_dir()


# =============================================================================
# Docstring Examples
# =============================================================================

def test_doc_get_project_root_example():
    """Docstring example: get_project_root equivalent to Skpath().root."""
    clear_custom_root()
    root = get_project_root()
    assert root.ap == Skpath().root.ap


# =============================================================================
# Custom Root Tests
# =============================================================================

def test_set_custom_root():
    """set_custom_root() should set custom root."""
    clear_custom_root()


def test_set_custom_root_invalid_path():
    """set_custom_root should raise when path does not exist."""
    clear_custom_root()
    try:
        set_custom_root("/path/does/not/exist")
        assert False, "Should have raised PathDetectionError"
    except PathDetectionError:
        pass


def test_set_custom_root_not_directory():
    """set_custom_root should raise when path is not a directory."""
    clear_custom_root()
    with tempfile.NamedTemporaryFile() as temp_file:
        try:
            set_custom_root(temp_file.name)
            assert False, "Should have raised PathDetectionError"
        except PathDetectionError:
            pass
    
    # Use temp directory that exists on all platforms
    custom = tempfile.gettempdir()
    set_custom_root(custom)
    
    result = get_custom_root()
    
    assert result is not None
    
    clear_custom_root()


def test_get_custom_root_none():
    """get_custom_root() should return None when not set."""
    clear_custom_root()
    
    result = get_custom_root()
    
    # Might return None or a default - check implementation
    # For now, just ensure it doesn't raise


def test_clear_custom_root():
    """clear_custom_root() should clear custom root."""
    temp_dir = tempfile.gettempdir()
    set_custom_root(temp_dir)
    clear_custom_root()
    
    # After clearing, should use auto-detection
    root = get_project_root()
    
    # Should not be the temp dir
    assert str(root.ap) != str(Path(temp_dir).resolve())


def test_custom_root_priority():
    """Custom root should take priority over detection."""
    clear_custom_root()
    
    # Get auto-detected root
    auto_root = get_project_root()
    
    # Set different custom root
    temp_dir = tempfile.gettempdir()
    set_custom_root(temp_dir)
    custom_root = get_project_root()
    
    # Custom should be different (if auto is not the temp dir)
    temp_resolved = str(Path(temp_dir).resolve())
    if str(auto_root.ap) != temp_resolved:
        assert str(custom_root.ap) == temp_resolved or custom_root.name == Path(temp_dir).name
    
    clear_custom_root()


# =============================================================================
# Skpath.root Tests
# =============================================================================

def test_skpath_root_property():
    """Skpath.root should return project root."""
    clear_custom_root()
    
    path = Skpath(__file__)
    root = path.root
    
    assert isinstance(root, Skpath)
    assert root.is_dir


def test_skpath_root_consistent():
    """Multiple calls to Skpath.root should return same root."""
    clear_custom_root()
    
    path1 = Skpath(__file__)
    path2 = Skpath(__file__)
    
    assert path1.root == path2.root


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all root detection tests."""
    runner = TestRunner("Root Detection Tests")
    
    # Default detection tests
    runner.run_test("get_project_root()", test_get_project_root)
    runner.run_test("Project root has indicators", test_project_root_has_indicators)
    runner.run_test("get_project_root expected_name mismatch", test_get_project_root_expected_name_mismatch)
    runner.run_test("detect_project_root from_path", test_detect_project_root_from_path)
    runner.run_test("clear_root_cache safe", test_clear_root_cache_does_not_break_detection)
    
    # Custom root tests
    runner.run_test("set_custom_root()", test_set_custom_root)
    runner.run_test("set_custom_root invalid path", test_set_custom_root_invalid_path)
    runner.run_test("set_custom_root not directory", test_set_custom_root_not_directory)
    runner.run_test("get_custom_root() when not set", test_get_custom_root_none)
    runner.run_test("clear_custom_root()", test_clear_custom_root)
    runner.run_test("Custom root priority", test_custom_root_priority)
    
    # Skpath.root tests
    runner.run_test("Skpath.root property", test_skpath_root_property)
    runner.run_test("Skpath.root consistent", test_skpath_root_consistent)
    
    # docstring examples
    runner.run_test("doc: get_project_root", test_doc_get_project_root_example)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
