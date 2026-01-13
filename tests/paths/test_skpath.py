"""
Skpath Class Tests

Tests Skpath functionality:
- Creation from various inputs
- Path properties (ap, rp, id)
- Path operations
- Root detection
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.paths import Skpath, PathDetectionError


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
# Creation Tests
# =============================================================================

def test_skpath_from_string():
    """Skpath should be created from string."""
    path = Skpath("/Users/test/file.txt")
    
    assert path is not None
    assert "file.txt" in path.name


def test_skpath_from_path():
    """Skpath should be created from pathlib.Path."""
    p = Path("/Users/test/file.txt")
    path = Skpath(p)
    
    assert path is not None


def test_skpath_from_skpath():
    """Skpath should be created from another Skpath."""
    path1 = Skpath("/Users/test/file.txt")
    path2 = Skpath(path1)
    
    assert path2.name == path1.name


def test_skpath_no_args():
    """Skpath() should detect caller's file."""
    path = Skpath()
    
    # Should point to this test file
    assert "test_skpath.py" in path.name


# =============================================================================
# Property Tests
# =============================================================================

def test_skpath_ap():
    """Skpath.ap should return absolute path string."""
    path = Skpath(".")
    
    # ap is a string starting with /
    assert path.ap.startswith("/")


def test_skpath_rp():
    """Skpath.rp should return relative path from root."""
    # Use a path we know exists
    path = Skpath(__file__)
    
    rp = path.rp
    
    # Should be relative (no leading /)
    # This depends on root detection
    assert rp is not None


def test_skpath_id():
    """Skpath.id should return a path identifier."""
    path = Skpath(__file__)
    
    id_val = path.id
    
    assert isinstance(id_val, str)
    assert len(id_val) > 0


def test_skpath_root():
    """Skpath.root should return project root."""
    path = Skpath(__file__)
    
    root = path.root
    
    assert root is not None
    # Root should be a directory
    assert root.is_dir


def test_skpath_name():
    """Skpath.name should return filename."""
    path = Skpath("/path/to/file.txt")
    
    assert path.name == "file.txt"


def test_skpath_stem():
    """Skpath.stem should return filename without extension."""
    path = Skpath("/path/to/file.txt")
    
    assert path.stem == "file"


def test_skpath_suffix():
    """Skpath.suffix should return file extension."""
    path = Skpath("/path/to/file.txt")
    
    assert path.suffix == ".txt"


def test_skpath_parent():
    """Skpath.parent should return parent Skpath."""
    path = Skpath("/path/to/file.txt")
    parent = path.parent
    
    assert isinstance(parent, Skpath)
    assert parent.name == "to"


# =============================================================================
# Path Operations Tests
# =============================================================================

def test_skpath_join():
    """Skpath / should join paths."""
    path = Skpath("/path/to")
    joined = path / "subdir" / "file.txt"
    
    assert isinstance(joined, Skpath)
    assert "subdir" in joined.ap
    assert "file.txt" in joined.ap


def test_skpath_exists():
    """Skpath.exists should check if path exists."""
    # This file exists
    path = Skpath(__file__)
    assert path.exists == True
    
    # This doesn't exist
    fake = Skpath("/definitely/not/a/real/path/abc123.xyz")
    assert fake.exists == False


def test_skpath_is_file():
    """Skpath.is_file should check if path is a file."""
    path = Skpath(__file__)
    
    assert path.is_file == True
    assert path.is_dir == False


def test_skpath_is_dir():
    """Skpath.is_dir should check if path is a directory."""
    path = Skpath(__file__)
    parent = path.parent
    
    assert parent.is_dir == True
    assert parent.is_file == False


# =============================================================================
# Comparison Tests
# =============================================================================

def test_skpath_equality():
    """Skpath should support equality comparison."""
    path1 = Skpath("/path/to/file.txt")
    path2 = Skpath("/path/to/file.txt")
    
    assert path1 == path2


def test_skpath_inequality():
    """Skpath should support inequality comparison."""
    path1 = Skpath("/path/to/file1.txt")
    path2 = Skpath("/path/to/file2.txt")
    
    assert path1 != path2


def test_skpath_hash():
    """Skpath should be hashable."""
    path1 = Skpath("/path/to/file.txt")
    path2 = Skpath("/path/to/file.txt")
    
    # Same path should have same hash
    assert hash(path1) == hash(path2)
    
    # Should work in sets/dicts
    path_set = {path1, path2}
    assert len(path_set) == 1


# =============================================================================
# String Conversion Tests
# =============================================================================

def test_skpath_str():
    """str(Skpath) should return path string."""
    path = Skpath("/path/to/file.txt")
    
    result = str(path)
    
    assert "/path/to/file.txt" in result or "file.txt" in result


def test_skpath_repr():
    """repr(Skpath) should return informative representation."""
    path = Skpath("/path/to/file.txt")
    
    result = repr(path)
    
    assert "Skpath" in result or "file.txt" in result


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all Skpath tests."""
    runner = TestRunner("Skpath Class Tests")
    
    # Creation tests
    runner.run_test("Skpath from string", test_skpath_from_string)
    runner.run_test("Skpath from Path", test_skpath_from_path)
    runner.run_test("Skpath from Skpath", test_skpath_from_skpath)
    runner.run_test("Skpath no args", test_skpath_no_args)
    
    # Property tests
    runner.run_test("Skpath.ap", test_skpath_ap)
    runner.run_test("Skpath.rp", test_skpath_rp)
    runner.run_test("Skpath.id", test_skpath_id)
    runner.run_test("Skpath.root", test_skpath_root)
    runner.run_test("Skpath.name", test_skpath_name)
    runner.run_test("Skpath.stem", test_skpath_stem)
    runner.run_test("Skpath.suffix", test_skpath_suffix)
    runner.run_test("Skpath.parent", test_skpath_parent)
    
    # Path operations tests
    runner.run_test("Skpath / join", test_skpath_join)
    runner.run_test("Skpath.exists()", test_skpath_exists)
    runner.run_test("Skpath.is_file()", test_skpath_is_file)
    runner.run_test("Skpath.is_dir()", test_skpath_is_dir)
    
    # Comparison tests
    runner.run_test("Skpath equality", test_skpath_equality)
    runner.run_test("Skpath inequality", test_skpath_inequality)
    runner.run_test("Skpath hash", test_skpath_hash)
    
    # String conversion tests
    runner.run_test("str(Skpath)", test_skpath_str)
    runner.run_test("repr(Skpath)", test_skpath_repr)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
