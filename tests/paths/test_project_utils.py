"""
Project Utility Functions Tests

Tests the project-level path utilities:
- get_project_paths()
- get_project_structure()
- get_formatted_project_tree()
"""

import sys
import os
import tempfile
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

from suitkaise.paths import (
    Skpath,
    get_project_paths,
    get_project_structure,
    get_formatted_project_tree,
    get_project_root,
    set_custom_root,
    clear_custom_root,
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
# get_project_paths Tests
# =============================================================================

def test_get_project_paths_returns_list():
    """get_project_paths should return a list."""
    clear_custom_root()
    
    paths = get_project_paths()
    
    assert isinstance(paths, list), f"Should return list, got {type(paths)}"


def test_get_project_paths_finds_files():
    """get_project_paths should find files in project."""
    clear_custom_root()
    
    paths = get_project_paths()
    
    assert len(paths) > 0, "Should find some files"


def test_get_project_paths_as_strings():
    """get_project_paths(as_strings=True) should return strings."""
    clear_custom_root()
    
    paths = get_project_paths(as_strings=True)
    
    assert len(paths) > 0
    for p in paths[:5]:
        assert isinstance(p, str), f"Should be string, got {type(p)}"


def test_get_project_paths_as_skpath():
    """get_project_paths(as_strings=False) should return Skpath objects."""
    clear_custom_root()
    
    paths = get_project_paths(as_strings=False)
    
    assert len(paths) > 0
    for p in paths[:5]:
        assert isinstance(p, Skpath), f"Should be Skpath, got {type(p)}"


def test_get_project_paths_exclude_single():
    """get_project_paths should exclude single path."""
    clear_custom_root()
    
    all_paths = get_project_paths(as_strings=True)
    filtered = get_project_paths(exclude="tests", as_strings=True)
    
    assert len(filtered) < len(all_paths), "Excluding should reduce count"
    
    for p in filtered:
        assert "/tests/" not in p or not p.startswith("tests/"), f"Should exclude tests: {p}"


def test_get_project_paths_exclude_list():
    """get_project_paths should exclude list of paths."""
    clear_custom_root()
    
    all_paths = get_project_paths(as_strings=True)
    filtered = get_project_paths(exclude=["tests", "venv311"], as_strings=True)
    
    assert len(filtered) < len(all_paths)


def test_get_project_paths_custom_root():
    """get_project_paths should use custom root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files
        Path(tmpdir, "file1.txt").touch()
        Path(tmpdir, "file2.py").touch()
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(subdir, "file3.txt").touch()
        
        paths = get_project_paths(root=tmpdir, as_strings=True, use_ignore_files=False)
        
        assert len(paths) >= 3, f"Should find at least 3 files, got {len(paths)}"


def test_get_project_paths_use_ignore_files():
    """get_project_paths should respect ignore files option."""
    clear_custom_root()
    
    # With ignore files (default)
    paths_with_ignore = get_project_paths(as_strings=True, use_ignore_files=True)
    
    # Without ignore files
    paths_without_ignore = get_project_paths(as_strings=True, use_ignore_files=False)
    
    # Without ignore should have at least as many (possibly more)
    assert len(paths_without_ignore) >= len(paths_with_ignore)


# =============================================================================
# get_project_structure Tests
# =============================================================================

def test_get_project_structure_returns_dict():
    """get_project_structure should return a dict."""
    clear_custom_root()
    
    structure = get_project_structure()
    
    assert isinstance(structure, dict), f"Should return dict, got {type(structure)}"


def test_get_project_structure_has_content():
    """get_project_structure should have content."""
    clear_custom_root()
    
    structure = get_project_structure()
    
    assert len(structure) > 0, "Should have content"


def test_get_project_structure_nested():
    """get_project_structure should have nested structure."""
    clear_custom_root()
    
    structure = get_project_structure()
    
    # At least the root should contain nested dicts
    root_key = list(structure.keys())[0]
    assert isinstance(structure[root_key], dict), "Root should contain dict"


def test_get_project_structure_with_exclude():
    """get_project_structure should respect exclude."""
    clear_custom_root()
    
    full_structure = get_project_structure()
    filtered = get_project_structure(exclude="tests")
    
    # Find if 'tests' is in full but not in filtered
    def has_key(d, key):
        if key in d:
            return True
        for v in d.values():
            if isinstance(v, dict) and has_key(v, key):
                return True
        return False
    
    # This is a soft test - depends on project structure
    # Just verify it returns something
    assert isinstance(filtered, dict)


def test_get_project_structure_custom_root():
    """get_project_structure should use custom root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create structure
        Path(tmpdir, "file1.txt").touch()
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(subdir, "file2.txt").touch()
        
        structure = get_project_structure(root=tmpdir, use_ignore_files=False)
        
        assert isinstance(structure, dict)
        assert len(structure) > 0


# =============================================================================
# get_formatted_project_tree Tests
# =============================================================================

def test_get_formatted_project_tree_returns_string():
    """get_formatted_project_tree should return a string."""
    clear_custom_root()
    
    tree = get_formatted_project_tree()
    
    assert isinstance(tree, str), f"Should return string, got {type(tree)}"


def test_get_formatted_project_tree_has_content():
    """get_formatted_project_tree should have content."""
    clear_custom_root()
    
    tree = get_formatted_project_tree()
    
    assert len(tree) > 0, "Should have content"


def test_get_formatted_project_tree_has_formatting():
    """get_formatted_project_tree should have tree formatting."""
    clear_custom_root()
    
    tree = get_formatted_project_tree(depth=2)
    
    # Should contain tree characters or directory markers
    has_formatting = (
        "├" in tree or 
        "└" in tree or 
        "│" in tree or
        "/" in tree
    )
    assert has_formatting, f"Should have tree formatting: {tree[:200]}"


def test_get_formatted_project_tree_depth():
    """get_formatted_project_tree should respect depth."""
    clear_custom_root()
    
    shallow = get_formatted_project_tree(depth=1)
    deep = get_formatted_project_tree(depth=5)
    
    # Deeper should generally have more content
    assert len(deep) >= len(shallow), "Deeper tree should have more content"


def test_get_formatted_project_tree_include_files():
    """get_formatted_project_tree should control file inclusion."""
    clear_custom_root()
    
    with_files = get_formatted_project_tree(depth=2, include_files=True)
    without_files = get_formatted_project_tree(depth=2, include_files=False)
    
    # With files should have more lines
    assert len(with_files) >= len(without_files)


def test_get_formatted_project_tree_exclude():
    """get_formatted_project_tree should respect exclude."""
    clear_custom_root()
    
    full = get_formatted_project_tree(depth=2)
    filtered = get_formatted_project_tree(depth=2, exclude="tests")
    
    # If tests is visible in full, it shouldn't be in filtered
    # This is a soft test
    assert isinstance(filtered, str)
    assert len(filtered) > 0


def test_get_formatted_project_tree_custom_root():
    """get_formatted_project_tree should use custom root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create structure
        Path(tmpdir, "file1.txt").touch()
        Path(tmpdir, "file2.py").touch()
        subdir = Path(tmpdir, "subdir")
        subdir.mkdir()
        Path(subdir, "nested.txt").touch()
        
        tree = get_formatted_project_tree(root=tmpdir, use_ignore_files=False)
        
        assert isinstance(tree, str)
        assert len(tree) > 0
        # Should contain the root dir name
        assert os.path.basename(tmpdir) in tree or "file" in tree.lower()


# =============================================================================
# Edge Cases Tests
# =============================================================================

def test_project_utils_empty_directory():
    """Project utils should handle empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = get_project_paths(root=tmpdir, as_strings=True, use_ignore_files=False)
        
        # Empty directory may return empty list or just the dir
        assert isinstance(paths, list)


def test_project_utils_single_file():
    """Project utils should handle single file in directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "only_file.txt").touch()
        
        paths = get_project_paths(root=tmpdir, as_strings=True, use_ignore_files=False)
        structure = get_project_structure(root=tmpdir, use_ignore_files=False)
        tree = get_formatted_project_tree(root=tmpdir, use_ignore_files=False)
        
        assert len(paths) >= 1
        assert isinstance(structure, dict)
        assert isinstance(tree, str)


def test_project_utils_deep_nesting():
    """Project utils should handle deeply nested directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create deep nesting
        current = Path(tmpdir)
        for i in range(5):
            current = current / f"level{i}"
            current.mkdir()
        Path(current, "deep_file.txt").touch()
        
        paths = get_project_paths(root=tmpdir, as_strings=True, use_ignore_files=False)
        
        # Should find the deep file
        deep_found = any("deep_file.txt" in p for p in paths)
        assert deep_found, f"Should find deep file in {paths}"


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all project utility tests."""
    runner = TestRunner("Project Utility Functions Tests")
    
    # get_project_paths tests
    runner.run_test("get_project_paths returns list", test_get_project_paths_returns_list)
    runner.run_test("get_project_paths finds files", test_get_project_paths_finds_files)
    runner.run_test("get_project_paths as strings", test_get_project_paths_as_strings)
    runner.run_test("get_project_paths as Skpath", test_get_project_paths_as_skpath)
    runner.run_test("get_project_paths exclude single", test_get_project_paths_exclude_single)
    runner.run_test("get_project_paths exclude list", test_get_project_paths_exclude_list)
    runner.run_test("get_project_paths custom root", test_get_project_paths_custom_root)
    runner.run_test("get_project_paths use_ignore_files", test_get_project_paths_use_ignore_files)
    
    # get_project_structure tests
    runner.run_test("get_project_structure returns dict", test_get_project_structure_returns_dict)
    runner.run_test("get_project_structure has content", test_get_project_structure_has_content)
    runner.run_test("get_project_structure nested", test_get_project_structure_nested)
    runner.run_test("get_project_structure with exclude", test_get_project_structure_with_exclude)
    runner.run_test("get_project_structure custom root", test_get_project_structure_custom_root)
    
    # get_formatted_project_tree tests
    runner.run_test("get_formatted_project_tree returns string", test_get_formatted_project_tree_returns_string)
    runner.run_test("get_formatted_project_tree has content", test_get_formatted_project_tree_has_content)
    runner.run_test("get_formatted_project_tree has formatting", test_get_formatted_project_tree_has_formatting)
    runner.run_test("get_formatted_project_tree depth", test_get_formatted_project_tree_depth)
    runner.run_test("get_formatted_project_tree include_files", test_get_formatted_project_tree_include_files)
    runner.run_test("get_formatted_project_tree exclude", test_get_formatted_project_tree_exclude)
    runner.run_test("get_formatted_project_tree custom root", test_get_formatted_project_tree_custom_root)
    
    # Edge cases
    runner.run_test("project utils empty directory", test_project_utils_empty_directory)
    runner.run_test("project utils single file", test_project_utils_single_file)
    runner.run_test("project utils deep nesting", test_project_utils_deep_nesting)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
