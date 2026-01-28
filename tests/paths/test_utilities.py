"""
Path Utilities Tests

Tests path utility functions:
- is_valid_filename()
- streamline_path()
- get_caller_path()
- get_current_dir()
- get_cwd()
"""

import sys
import os
import tempfile
from pathlib import Path

# Add project root to path (this script is in tests/paths/, so go up two levels)
project_root = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(project_root))

from suitkaise.paths import (
    is_valid_filename,
    streamline_path,
    streamline_path_quick,
    get_caller_path,
    get_current_dir,
    get_cwd,
    get_module_path,
    CustomRoot,
    PathDetectionError,
    NotAFileError,
    Skpath,
)


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
# is_valid_filename Tests
# =============================================================================

def test_valid_filename_simple():
    """Valid simple filenames should pass."""
    assert is_valid_filename("file.txt") == True
    assert is_valid_filename("myfile.py") == True
    assert is_valid_filename("document.pdf") == True


def test_valid_filename_with_dash():
    """Filenames with dashes should be valid."""
    assert is_valid_filename("my-file.txt") == True
    assert is_valid_filename("test-file-123.py") == True


def test_valid_filename_with_underscore():
    """Filenames with underscores should be valid."""
    assert is_valid_filename("my_file.txt") == True
    assert is_valid_filename("test_file_123.py") == True


def test_invalid_filename_with_slash():
    """Filenames with slashes should be invalid."""
    assert is_valid_filename("path/file.txt") == False
    assert is_valid_filename("path\\file.txt") == False


def test_invalid_filename_with_special():
    """Filenames with special chars should be invalid."""
    assert is_valid_filename("file?.txt") == False
    assert is_valid_filename("file*.txt") == False
    assert is_valid_filename("file<>.txt") == False


def test_invalid_filename_empty():
    """Empty filename should be invalid."""
    assert is_valid_filename("") == False


# =============================================================================
# streamline_path Tests
# =============================================================================

def test_streamline_basic():
    """streamline_path should handle basic paths."""
    result = streamline_path("my file.txt")
    
    # Should replace spaces or handle them
    assert " " not in result or result == "my file.txt"


def test_streamline_long_path():
    """streamline_path should handle max_len."""
    long_name = "a" * 200
    result = streamline_path(long_name, max_len=50)
    
    assert len(result) <= 50


def test_streamline_invalid_chars():
    """streamline_path should replace invalid chars."""
    result = streamline_path("file?*.txt", replacement_char="_")
    
    assert "?" not in result
    assert "*" not in result


def test_streamline_lowercase():
    """streamline_path should handle lowercase option."""
    result = streamline_path("MyFile.TXT", lowercase=True)
    
    assert result == result.lower()


def test_streamline_strip():
    """streamline_path should strip whitespace."""
    result = streamline_path("  file.txt  ")
    
    assert result == result.strip()


def test_streamline_path_quick_example():
    """streamline_path_quick should match docstring example."""
    result = streamline_path_quick("My File<1>файл.txt")
    assert result == "My_File_1_____.txt"


# =============================================================================
# Docstring Examples
# =============================================================================

def test_doc_get_caller_path_example():
    """Docstring example: get_caller_path equivalent to Skpath()."""
    path = get_caller_path()
    skpath = Skpath()
    assert path.ap == skpath.ap


def test_doc_get_current_dir_example():
    """Docstring example: get_current_dir equivalent to Skpath().parent."""
    current_dir = get_current_dir()
    skpath_parent = Skpath().parent
    assert current_dir.ap == skpath_parent.ap


def test_doc_get_cwd_example():
    """Docstring example: get_cwd returns current working directory."""
    cwd = get_cwd()
    assert cwd.ap == Skpath(Path.cwd()).ap


def test_doc_streamline_path_examples():
    """Docstring examples for streamline_path()."""
    basic = streamline_path("My File<1>.txt", chars_to_replace=" ")
    assert basic == "My_File_1_.txt"
    
    lowered = streamline_path(
        "My Long Filename.txt",
        max_len=10,
        lowercase=True,
        chars_to_replace=" ",
    )
    assert lowered == "my_long_fi.txt"
    
    replaced = streamline_path("file:name.txt", replacement_char="-")
    assert replaced == "file-name.txt"
    
    ascii_only = streamline_path("файл.txt", allow_unicode=False)
    assert ascii_only == "____.txt"


# =============================================================================
# get_caller_path Tests
# =============================================================================

def test_get_caller_path():
    """get_caller_path should return this file's path."""
    path = get_caller_path()
    
    assert isinstance(path, Skpath)
    assert "test_utilities.py" in path.name


# =============================================================================
# get_current_dir Tests
# =============================================================================

def test_get_current_dir():
    """get_current_dir should return directory of caller."""
    dir_path = get_current_dir()
    
    assert isinstance(dir_path, Skpath)
    assert dir_path.is_dir


# =============================================================================
# get_cwd Tests
# =============================================================================

def test_get_cwd():
    """get_cwd should return current working directory."""
    cwd = get_cwd()
    
    assert isinstance(cwd, Skpath)
    assert cwd.is_dir
    assert cwd.ap == os.getcwd() or cwd.exists


# =============================================================================
# get_module_path Tests
# =============================================================================

def test_get_module_path_with_class():
    """get_module_path should return path of module where class is defined."""
    # Use Skpath as test subject - it's defined in skpath.py
    path = get_module_path(Skpath)
    
    assert path is not None
    assert isinstance(path, Skpath)
    assert "skpath" in path.name.lower()


def test_get_module_path_with_function():
    """get_module_path should return path of module where function is defined."""
    path = get_module_path(is_valid_filename)
    
    assert path is not None
    assert isinstance(path, Skpath)


def test_get_module_path_with_builtin():
    """get_module_path should return None for builtins."""
    path = get_module_path(len)  # Built-in function
    
    # Builtins don't have a file path
    assert path is None


def test_get_module_path_with_module_object():
    """get_module_path should work with module object."""
    import suitkaise.paths as paths_module
    
    path = get_module_path(paths_module)
    
    assert path is not None
    assert isinstance(path, Skpath)


# =============================================================================
# CustomRoot Context Manager Tests
# =============================================================================

def test_custom_root_context_manager():
    """CustomRoot should temporarily set project root."""
    from suitkaise.paths import get_project_root, clear_custom_root
    
    clear_custom_root()
    original_root = get_project_root()
    
    # Use temporary directory that exists on all platforms
    with tempfile.TemporaryDirectory() as tmpdir:
        with CustomRoot(tmpdir):
            temp_root = get_project_root()
            assert Path(tmpdir).name == temp_root.name or str(temp_root.ap) == str(Path(tmpdir).resolve())
    
    # After context, should restore
    restored_root = get_project_root()
    assert restored_root.ap == original_root.ap


def test_custom_root_nested():
    """Nested CustomRoot should work correctly."""
    from suitkaise.paths import get_project_root, clear_custom_root
    
    clear_custom_root()
    
    with tempfile.TemporaryDirectory() as outer_tmp:
        with CustomRoot(outer_tmp):
            outer = get_project_root()
            
            with tempfile.TemporaryDirectory() as inner_tmp:
                with CustomRoot(inner_tmp):
                    inner = get_project_root()
                    assert Path(inner_tmp).name == inner.name or str(inner.ap) == str(Path(inner_tmp).resolve())
            
            # Back to outer context
            after_inner = get_project_root()
            assert after_inner.ap == outer.ap


def test_custom_root_exception_cleanup():
    """CustomRoot should restore root even if exception occurs."""
    from suitkaise.paths import get_project_root, clear_custom_root
    
    clear_custom_root()
    original_root = get_project_root()
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            with CustomRoot(tmpdir):
                raise ValueError("Test exception")
    except ValueError:
        pass
    
    # Should still restore
    restored_root = get_project_root()
    assert restored_root.ap == original_root.ap


# =============================================================================
# PathDetectionError Tests
# =============================================================================

def test_path_detection_error_is_exception():
    """PathDetectionError should be an Exception."""
    assert issubclass(PathDetectionError, Exception)


def test_path_detection_error_can_be_raised():
    """PathDetectionError should be raisable with message."""
    try:
        raise PathDetectionError("Test error message")
    except PathDetectionError as e:
        assert "Test error message" in str(e)


def test_path_detection_error_catchable():
    """PathDetectionError should be catchable."""
    caught = False
    
    try:
        raise PathDetectionError("detection failed")
    except PathDetectionError:
        caught = True
    
    assert caught


# =============================================================================
# NotAFileError Tests
# =============================================================================

def test_not_a_file_error_is_exception():
    """NotAFileError should be an Exception."""
    assert issubclass(NotAFileError, Exception)


def test_not_a_file_error_can_be_raised():
    """NotAFileError should be raisable with message."""
    try:
        raise NotAFileError("Not a file")
    except NotAFileError as e:
        assert "Not a file" in str(e)


def test_not_a_file_error_catchable():
    """NotAFileError should be catchable."""
    caught = False
    try:
        raise NotAFileError("not a file")
    except NotAFileError:
        caught = True
    assert caught


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all path utility tests."""
    runner = TestRunner("Path Utilities Tests")
    
    # is_valid_filename tests
    runner.run_test("is_valid_filename simple", test_valid_filename_simple)
    runner.run_test("is_valid_filename with dash", test_valid_filename_with_dash)
    runner.run_test("is_valid_filename with underscore", test_valid_filename_with_underscore)
    runner.run_test("is_valid_filename with slash (invalid)", test_invalid_filename_with_slash)
    runner.run_test("is_valid_filename with special (invalid)", test_invalid_filename_with_special)
    runner.run_test("is_valid_filename empty (invalid)", test_invalid_filename_empty)
    
    # streamline_path tests
    runner.run_test("streamline_path basic", test_streamline_basic)
    runner.run_test("streamline_path long path", test_streamline_long_path)
    runner.run_test("streamline_path invalid chars", test_streamline_invalid_chars)
    runner.run_test("streamline_path lowercase", test_streamline_lowercase)
    runner.run_test("streamline_path strip", test_streamline_strip)
    runner.run_test("streamline_path_quick example", test_streamline_path_quick_example)
    
    # get_caller_path tests
    runner.run_test("get_caller_path", test_get_caller_path)
    
    # get_current_dir tests
    runner.run_test("get_current_dir", test_get_current_dir)
    
    # get_cwd tests
    runner.run_test("get_cwd", test_get_cwd)
    
    # get_module_path tests
    runner.run_test("get_module_path with class", test_get_module_path_with_class)
    runner.run_test("get_module_path with function", test_get_module_path_with_function)
    runner.run_test("get_module_path with builtin", test_get_module_path_with_builtin)
    runner.run_test("get_module_path with module", test_get_module_path_with_module_object)
    
    # CustomRoot context manager tests
    runner.run_test("CustomRoot context manager", test_custom_root_context_manager)
    runner.run_test("CustomRoot nested", test_custom_root_nested)
    runner.run_test("CustomRoot exception cleanup", test_custom_root_exception_cleanup)
    
    # PathDetectionError tests
    runner.run_test("PathDetectionError is Exception", test_path_detection_error_is_exception)
    runner.run_test("PathDetectionError can be raised", test_path_detection_error_can_be_raised)
    runner.run_test("PathDetectionError catchable", test_path_detection_error_catchable)
    
    # NotAFileError tests
    runner.run_test("NotAFileError is Exception", test_not_a_file_error_is_exception)
    runner.run_test("NotAFileError can be raised", test_not_a_file_error_can_be_raised)
    runner.run_test("NotAFileError catchable", test_not_a_file_error_catchable)
    
    # docstring examples
    runner.run_test("doc: get_caller_path", test_doc_get_caller_path_example)
    runner.run_test("doc: get_current_dir", test_doc_get_current_dir_example)
    runner.run_test("doc: get_cwd", test_doc_get_cwd_example)
    runner.run_test("doc: streamline_path", test_doc_streamline_path_examples)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
