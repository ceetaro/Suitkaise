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
    
    # ap should be an absolute path (starts with / on Unix, or drive letter like C:/ on Windows)
    # On Windows, after normalization it would be like "C:/..." or just "/" on Unix
    assert path.ap.startswith("/") or (path.ap[1:2] == ":" and path.ap[2:3] == "/"), \
        f"ap should be absolute path, got: {path.ap}"


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


def test_skpath_suffixes():
    """Skpath.suffixes should return all suffixes."""
    path = Skpath("/path/archive.tar.gz")
    assert path.suffixes == [".tar", ".gz"]


def test_skpath_parts():
    """Skpath.parts should return path parts."""
    path = Skpath("/path/to/file.txt")
    assert "path" in path.parts


def test_skpath_parents():
    """Skpath.parents should return tuple of parents."""
    path = Skpath("/path/to/file.txt")
    parents = path.parents
    assert isinstance(parents, tuple)
    assert parents[0].name == "to"


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


def test_skpath_relative_to():
    """Skpath.relative_to should return relative Skpath."""
    base = Skpath("/path/to")
    child = Skpath("/path/to/sub/file.txt")
    rel = child.relative_to(base)
    assert rel.ap.endswith("sub/file.txt")


def test_skpath_with_name_stem_suffix():
    """Skpath should update name/stem/suffix."""
    path = Skpath("/path/to/file.txt")
    assert path.with_name("other.md").name == "other.md"
    assert path.with_stem("new").name == "new.txt"
    assert path.with_suffix(".py").name == "file.py"


def test_skpath_mkdir_touch_iterdir():
    """Skpath mkdir/touch/iterdir should operate on filesystem."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Skpath(tmpdir)
        sub = root / "sub"
        sub.mkdir(parents=True, exist_ok=True)
        file_path = sub / "a.txt"
        file_path.touch()
        entries = list(sub.iterdir())
        assert any(p.name == "a.txt" for p in entries)


def test_skpath_glob_rglob():
    """Skpath glob/rglob should find matching files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Skpath(tmpdir)
        (root / "a.txt").touch()
        (root / "b.md").touch()
        matches = list(root.glob("*.txt"))
        assert len(matches) == 1
        all_matches = list(root.rglob("*.*"))
        assert len(all_matches) >= 2


def test_skpath_stat_lstat_symlink():
    """Skpath stat/lstat/is_symlink should behave."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Skpath(tmpdir)
        target = root / "target.txt"
        target.touch()
        link = root / "link.txt"
        try:
            os.symlink(target.ap, link.ap)
        except (OSError, NotImplementedError):
            return
        assert link.is_symlink
        assert link.lstat is not None
        assert link.stat is not None


def test_skpath_as_dict_and_platform():
    """Skpath.as_dict and platform should return metadata."""
    path = Skpath(__file__)
    data = path.as_dict
    assert data["ap"] == path.ap
    platform_path = path.platform
    assert isinstance(platform_path, str)
    assert platform_path.replace(os.sep, "/") == path.ap


def test_skpath_repr_fspath_and_hash():
    """Skpath string/representation helpers should work."""
    path = Skpath(__file__)
    assert str(path)
    assert "Skpath" in repr(path)
    # os.fspath uses OS-native separators, so normalize before comparing
    assert os.fspath(path).replace(os.sep, "/") == path.ap
    assert hash(path)


def test_skpath_bool_len_iter_contains():
    """Skpath bool/len/iter/contains should work."""
    path = Skpath("/path/to/file.txt")
    assert bool(path)
    assert len(path) > 0
    assert "file.txt" in path
    parts = list(iter(path))
    assert "path" in parts


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
# Ordering Comparison Tests
# =============================================================================

def test_skpath_less_than():
    """Skpath should support < comparison."""
    path_a = Skpath("/aaa/file.txt")
    path_b = Skpath("/bbb/file.txt")
    
    assert path_a < path_b, f"Expected {path_a} < {path_b}"
    assert not (path_b < path_a), f"Expected not {path_b} < {path_a}"


def test_skpath_greater_than():
    """Skpath should support > comparison."""
    path_a = Skpath("/aaa/file.txt")
    path_b = Skpath("/bbb/file.txt")
    
    assert path_b > path_a, f"Expected {path_b} > {path_a}"
    assert not (path_a > path_b), f"Expected not {path_a} > {path_b}"


def test_skpath_less_equal():
    """Skpath should support <= comparison."""
    path_a = Skpath("/aaa/file.txt")
    path_b = Skpath("/bbb/file.txt")
    path_a2 = Skpath("/aaa/file.txt")
    
    assert path_a <= path_b
    assert path_a <= path_a2  # equal paths
    assert not (path_b <= path_a)


def test_skpath_greater_equal():
    """Skpath should support >= comparison."""
    path_a = Skpath("/aaa/file.txt")
    path_b = Skpath("/bbb/file.txt")
    path_b2 = Skpath("/bbb/file.txt")
    
    assert path_b >= path_a
    assert path_b >= path_b2  # equal paths
    assert not (path_a >= path_b)


def test_skpath_compare_with_str():
    """Skpath ordering should work with str operands."""
    path = Skpath("/bbb/file.txt")
    
    assert path > "/aaa/file.txt"
    assert path < "/ccc/file.txt"


def test_skpath_compare_with_path():
    """Skpath ordering should work with pathlib.Path operands."""
    path = Skpath("/bbb/file.txt")
    
    assert path > Path("/aaa/file.txt")
    assert path < Path("/ccc/file.txt")


def test_skpath_sorted():
    """Skpath should work with sorted() for lexicographic ordering."""
    paths = [
        Skpath("/c/file.txt"),
        Skpath("/a/file.txt"),
        Skpath("/b/file.txt"),
    ]
    
    result = sorted(paths)
    names = [p.parts[1] for p in result]
    assert names == ['a', 'b', 'c'], f"Expected ['a', 'b', 'c'], got {names}"


def test_skpath_case_sensitive_ordering():
    """Skpath ordering must be case-sensitive on all platforms (uppercase < lowercase)."""
    upper = Skpath("/tmp/Apple")
    lower = Skpath("/tmp/banana")
    
    # 'A' (65) < 'b' (98) in ASCII — must hold even on Windows
    assert upper < lower, f"Expected case-sensitive: {upper} < {lower}"
    assert lower > upper


def test_skpath_compare_not_implemented():
    """Skpath ordering with non-path types should return NotImplemented."""
    path = Skpath("/a/file.txt")
    
    try:
        result = path < 42
        assert False, "Should have raised TypeError"
    except TypeError:
        pass  # expected — Python raises TypeError when both sides return NotImplemented


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
    runner.run_test("Skpath.suffixes", test_skpath_suffixes)
    runner.run_test("Skpath.parts", test_skpath_parts)
    runner.run_test("Skpath.parents", test_skpath_parents)
    
    # Path operations tests
    runner.run_test("Skpath / join", test_skpath_join)
    runner.run_test("Skpath.exists()", test_skpath_exists)
    runner.run_test("Skpath.is_file()", test_skpath_is_file)
    runner.run_test("Skpath.is_dir()", test_skpath_is_dir)
    runner.run_test("Skpath.relative_to()", test_skpath_relative_to)
    runner.run_test("Skpath.with_name/stem/suffix", test_skpath_with_name_stem_suffix)
    runner.run_test("Skpath.mkdir/touch/iterdir", test_skpath_mkdir_touch_iterdir)
    runner.run_test("Skpath.glob/rglob", test_skpath_glob_rglob)
    runner.run_test("Skpath.stat/lstat/symlink", test_skpath_stat_lstat_symlink)
    runner.run_test("Skpath.as_dict/platform", test_skpath_as_dict_and_platform)
    runner.run_test("Skpath repr/fspath/hash", test_skpath_repr_fspath_and_hash)
    runner.run_test("Skpath bool/len/iter/contains", test_skpath_bool_len_iter_contains)
    
    # Comparison tests
    runner.run_test("Skpath equality", test_skpath_equality)
    runner.run_test("Skpath inequality", test_skpath_inequality)
    runner.run_test("Skpath hash", test_skpath_hash)
    
    # Ordering comparison tests
    runner.run_test("Skpath <", test_skpath_less_than)
    runner.run_test("Skpath >", test_skpath_greater_than)
    runner.run_test("Skpath <=", test_skpath_less_equal)
    runner.run_test("Skpath >=", test_skpath_greater_equal)
    runner.run_test("Skpath < > with str", test_skpath_compare_with_str)
    runner.run_test("Skpath < > with Path", test_skpath_compare_with_path)
    runner.run_test("Skpath sorted()", test_skpath_sorted)
    runner.run_test("Skpath case-sensitive ordering", test_skpath_case_sensitive_ordering)
    runner.run_test("Skpath < non-path TypeError", test_skpath_compare_not_implemented)
    
    # String conversion tests
    runner.run_test("str(Skpath)", test_skpath_str)
    runner.run_test("repr(Skpath)", test_skpath_repr)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
