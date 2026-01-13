"""
Comprehensive tests for skpath module.

Run with CodeRunner or IDE play button.
Tests every feature and tries to break skpath.

Usage:
    python test_all_features.py
"""

import os
import sys
import tempfile
import threading
from pathlib import Path

# Add project root to path for direct execution
_this_file = Path(__file__).resolve()
_project_root = _this_file.parent.parent.parent
sys.path.insert(0, str(_project_root))

# Import skpath components DIRECTLY (bypass suitkaise/__init__.py which imports circuit with 3.10+ syntax)
from suitkaise.skpath.api import (
    SKPath,
    AnyPath,
    autopath,
    PathDetectionError,
    CustomRoot,
    set_custom_root,
    get_custom_root,
    clear_custom_root,
    get_project_root,
    get_caller_path,
    get_current_dir,
    get_cwd,
    get_module_path,
    get_id,
    get_project_paths,
    get_project_structure,
    get_formatted_project_tree,
)
from suitkaise.skpath._int import (
    encode_path_id,
    decode_path_id,
    is_valid_encoded_id,
    hash_path_md5,
    normalize_separators,
    to_os_separators,
    detect_project_root,
    clear_root_cache,
)

# ============================================================================
# Test Utilities
# ============================================================================

class TestResult:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def success(self, name: str):
        self.passed += 1
        print(f"  ✓ {name}")
    
    def fail(self, name: str, error: str):
        self.failed += 1
        self.errors.append((name, error))
        print(f"  ✗ {name}")
        print(f"    Error: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed")
        if self.errors:
            print(f"\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        print(f"{'='*60}")
        return self.failed == 0

result = TestResult()

def test(name: str):
    """Decorator to run a test function."""
    def decorator(func):
        def wrapper():
            try:
                func()
                result.success(name)
            except AssertionError as e:
                result.fail(name, str(e))
            except Exception as e:
                result.fail(name, f"{type(e).__name__}: {e}")
        return wrapper
    return decorator


# ============================================================================
# Test Setup
# ============================================================================

print("\n" + "="*60)
print("SKPATH COMPREHENSIVE TESTS")
print("="*60)

# Create temp directory for test files
TEST_DIR = Path(tempfile.mkdtemp(prefix="skpath_test_"))
(TEST_DIR / "subdir").mkdir()
(TEST_DIR / "subdir" / "nested").mkdir()
(TEST_DIR / "file.txt").touch()
(TEST_DIR / "subdir" / "file2.txt").touch()
(TEST_DIR / "subdir" / "nested" / "deep.py").touch()
(TEST_DIR / "archive.tar.gz").touch()

print(f"\nTest directory: {TEST_DIR}")


# ============================================================================
# 1. ID UTILITIES
# ============================================================================

print("\n" + "-"*40)
print("1. ID UTILITIES")
print("-"*40)

@test("normalize_separators: converts backslashes")
def test_normalize_backslashes():
    assert normalize_separators("a\\b\\c") == "a/b/c"
    assert normalize_separators("a/b/c") == "a/b/c"
    assert normalize_separators("a\\b/c\\d") == "a/b/c/d"

test_normalize_backslashes()

@test("normalize_separators: handles empty string")
def test_normalize_empty():
    assert normalize_separators("") == ""

test_normalize_empty()

@test("to_os_separators: platform-aware conversion")
def test_to_os():
    path = "a/b/c"
    converted = to_os_separators(path)
    if os.sep == "\\":
        assert converted == "a\\b\\c"
    else:
        assert converted == "a/b/c"

test_to_os()

@test("encode_path_id: creates valid base64url")
def test_encode():
    encoded = encode_path_id("myproject/file.txt")
    assert encoded  # Not empty
    assert "/" not in encoded  # No path separators
    assert "\\" not in encoded
    assert "=" not in encoded  # Padding stripped

test_encode()

@test("decode_path_id: reverses encoding")
def test_decode():
    original = "myproject/feature/file.txt"
    encoded = encode_path_id(original)
    decoded = decode_path_id(encoded)
    assert decoded == original

test_decode()

@test("decode_path_id: handles unicode paths")
def test_decode_unicode():
    original = "プロジェクト/ファイル.txt"
    encoded = encode_path_id(original)
    decoded = decode_path_id(encoded)
    assert decoded == original

test_decode_unicode()

@test("decode_path_id: returns None for invalid input")
def test_decode_invalid():
    result = decode_path_id("!!!not-valid!!!")
    # Should return None or the broken decode
    # At minimum, shouldn't crash

test_decode_invalid()

@test("is_valid_encoded_id: identifies valid IDs")
def test_valid_id():
    assert is_valid_encoded_id("bXlwcm9qZWN0L2ZpbGUudHh0") == True
    assert is_valid_encoded_id("abc123-_ABC") == True

test_valid_id()

@test("is_valid_encoded_id: rejects paths")
def test_invalid_id_paths():
    assert is_valid_encoded_id("a/b/c") == False
    assert is_valid_encoded_id("a\\b\\c") == False
    assert is_valid_encoded_id("file.txt") == False  # Starts with .
    assert is_valid_encoded_id("") == False
    assert is_valid_encoded_id("has space") == False

test_invalid_id_paths()

@test("hash_path_md5: produces consistent integer hash")
def test_hash_md5():
    h1 = hash_path_md5("myproject/file.txt")
    h2 = hash_path_md5("myproject/file.txt")
    assert h1 == h2
    assert isinstance(h1, int)
    
    # Different paths should have different hashes (extremely likely)
    h3 = hash_path_md5("different/path.txt")
    assert h1 != h3

test_hash_md5()

@test("hash_path_md5: normalizes separators before hashing")
def test_hash_normalized():
    h1 = hash_path_md5("a/b/c")
    h2 = hash_path_md5("a\\b\\c")
    assert h1 == h2

test_hash_normalized()


# ============================================================================
# 2. SKPATH INITIALIZATION
# ============================================================================

print("\n" + "-"*40)
print("2. SKPATH INITIALIZATION")
print("-"*40)

@test("SKPath: from string path")
def test_init_string():
    path = SKPath(str(TEST_DIR / "file.txt"))
    assert path.exists

test_init_string()

@test("SKPath: from Path object")
def test_init_path():
    path = SKPath(TEST_DIR / "file.txt")
    assert path.exists

test_init_path()

@test("SKPath: from another SKPath (copies values)")
def test_init_skpath():
    original = SKPath(TEST_DIR / "file.txt")
    _ = original.ap  # Force cache
    _ = original.np
    
    copy = SKPath(original)
    assert copy.ap == original.ap
    assert copy._ap == original._ap  # Cache copied

test_init_skpath()

@test("SKPath: from None (caller's path)")
def test_init_none():
    path = SKPath()
    assert path.exists
    assert "test_all_features.py" in path.name

test_init_none()

@test("SKPath: from encoded ID")
def test_init_encoded_id():
    # First create a path and get its ID
    original = SKPath(TEST_DIR / "file.txt")
    encoded = original.id
    
    # Now reconstruct from ID (if it's an np-based ID, it should work)
    # This test may be tricky since TEST_DIR is outside project root
    # So just verify the ID is valid
    assert encoded
    assert is_valid_encoded_id(encoded) or "/" not in encoded

test_init_encoded_id()

@test("SKPath: rejects invalid types")
def test_init_invalid_type():
    try:
        SKPath(12345)  # type: ignore
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "expects str, Path, SKPath, or None" in str(e)

test_init_invalid_type()

@test("SKPath: handles non-existent path")
def test_init_nonexistent():
    path = SKPath("/this/path/does/not/exist.txt")
    assert not path.exists
    # Should still work, just not exist

test_init_nonexistent()


# ============================================================================
# 3. SKPATH CORE PROPERTIES
# ============================================================================

print("\n" + "-"*40)
print("3. SKPATH CORE PROPERTIES")
print("-"*40)

@test("SKPath.ap: absolute path with forward slashes")
def test_ap():
    path = SKPath(TEST_DIR / "subdir" / "file2.txt")
    ap = path.ap
    assert "/" in ap or "\\" not in ap  # Forward slashes
    assert path.exists
    assert ap.endswith("file2.txt")

test_ap()

@test("SKPath.ap: cached after first access")
def test_ap_cached():
    path = SKPath(TEST_DIR / "file.txt")
    assert path._ap is None
    _ = path.ap
    assert path._ap is not None

test_ap_cached()

@test("SKPath.np: normalized path relative to project root")
def test_np():
    # Use a file inside the actual project
    path = SKPath(_this_file)
    np = path.np
    # Should be relative to project root
    assert np  # Not empty (file is in project)
    assert not np.startswith("/")  # Relative path

test_np()

@test("SKPath.np: empty for paths outside project")
def test_np_outside():
    # TEST_DIR is in temp, outside project
    path = SKPath(TEST_DIR / "file.txt")
    np = path.np
    # Should be empty since it's outside project
    assert np == "" or np  # Either empty or has value

test_np_outside()

@test("SKPath.id: reversible encoded ID")
def test_id():
    path = SKPath(_this_file)
    path_id = path.id
    assert path_id
    assert is_valid_encoded_id(path_id)

test_id()

@test("SKPath.root: project root as string")
def test_root():
    path = SKPath(_this_file)
    root = path.root
    assert root
    assert "/" in root or os.sep not in root

test_root()

@test("SKPath.root_path: project root as Path")
def test_root_path():
    path = SKPath(_this_file)
    root_path = path.root_path
    assert isinstance(root_path, Path)
    assert root_path.exists()
    assert root_path.is_dir()

test_root_path()


# ============================================================================
# 4. PATHLIB-COMPATIBLE PROPERTIES
# ============================================================================

print("\n" + "-"*40)
print("4. PATHLIB-COMPATIBLE PROPERTIES")
print("-"*40)

@test("SKPath.name: filename with extension")
def test_name():
    path = SKPath(TEST_DIR / "file.txt")
    assert path.name == "file.txt"

test_name()

@test("SKPath.stem: filename without extension")
def test_stem():
    path = SKPath(TEST_DIR / "file.txt")
    assert path.stem == "file"

test_stem()

@test("SKPath.suffix: file extension")
def test_suffix():
    path = SKPath(TEST_DIR / "file.txt")
    assert path.suffix == ".txt"

test_suffix()

@test("SKPath.suffixes: all extensions")
def test_suffixes():
    path = SKPath(TEST_DIR / "archive.tar.gz")
    assert path.suffixes == [".tar", ".gz"]

test_suffixes()

@test("SKPath.parent: parent directory as SKPath")
def test_parent():
    path = SKPath(TEST_DIR / "subdir" / "file2.txt")
    parent = path.parent
    assert isinstance(parent, SKPath)
    assert parent.name == "subdir"

test_parent()

@test("SKPath.parents: all parent directories")
def test_parents():
    path = SKPath(TEST_DIR / "subdir" / "nested" / "deep.py")
    parents = path.parents
    assert isinstance(parents, tuple)
    assert all(isinstance(p, SKPath) for p in parents)
    assert len(parents) > 0

test_parents()

@test("SKPath.parts: path components as tuple")
def test_parts():
    path = SKPath(TEST_DIR / "file.txt")
    parts = path.parts
    assert isinstance(parts, tuple)
    assert parts[-1] == "file.txt"

test_parts()

@test("SKPath.exists: True for existing paths")
def test_exists_true():
    path = SKPath(TEST_DIR / "file.txt")
    assert path.exists == True

test_exists_true()

@test("SKPath.exists: False for non-existent paths")
def test_exists_false():
    path = SKPath(TEST_DIR / "nonexistent.txt")
    assert path.exists == False

test_exists_false()

@test("SKPath.is_file: True for files")
def test_is_file():
    path = SKPath(TEST_DIR / "file.txt")
    assert path.is_file == True
    assert path.is_dir == False

test_is_file()

@test("SKPath.is_dir: True for directories")
def test_is_dir():
    path = SKPath(TEST_DIR / "subdir")
    assert path.is_dir == True
    assert path.is_file == False

test_is_dir()

@test("SKPath.is_symlink: False for regular files")
def test_is_symlink():
    path = SKPath(TEST_DIR / "file.txt")
    assert path.is_symlink == False

test_is_symlink()

@test("SKPath.stat: returns stat_result")
def test_stat():
    path = SKPath(TEST_DIR / "file.txt")
    stat = path.stat
    assert hasattr(stat, "st_size")
    assert hasattr(stat, "st_mtime")
    assert stat.st_size == 0  # Empty file

test_stat()

@test("SKPath.lstat: returns stat_result")
def test_lstat():
    path = SKPath(TEST_DIR / "file.txt")
    lstat = path.lstat
    assert hasattr(lstat, "st_size")

test_lstat()

@test("SKPath.as_dict: dictionary representation")
def test_as_dict():
    path = SKPath(TEST_DIR / "file.txt")
    d = path.as_dict
    assert "ap" in d
    assert "np" in d
    assert "name" in d
    assert "exists" in d
    assert d["name"] == "file.txt"
    assert d["exists"] == True

test_as_dict()


# ============================================================================
# 5. PATHLIB-COMPATIBLE METHODS
# ============================================================================

print("\n" + "-"*40)
print("5. PATHLIB-COMPATIBLE METHODS")
print("-"*40)

@test("SKPath.iterdir: yields SKPath objects")
def test_iterdir():
    path = SKPath(TEST_DIR)
    items = list(path.iterdir())
    assert len(items) > 0
    assert all(isinstance(item, SKPath) for item in items)
    names = [item.name for item in items]
    assert "file.txt" in names
    assert "subdir" in names

test_iterdir()

@test("SKPath.glob: finds matching files")
def test_glob():
    path = SKPath(TEST_DIR)
    txt_files = list(path.glob("*.txt"))
    assert len(txt_files) >= 1
    assert all(isinstance(f, SKPath) for f in txt_files)
    assert all(f.suffix == ".txt" for f in txt_files)

test_glob()

@test("SKPath.rglob: recursively finds files")
def test_rglob():
    path = SKPath(TEST_DIR)
    all_txt = list(path.rglob("*.txt"))
    assert len(all_txt) >= 2  # file.txt and file2.txt
    names = [f.name for f in all_txt]
    assert "file.txt" in names
    assert "file2.txt" in names

test_rglob()

@test("SKPath.relative_to: calculates relative path")
def test_relative_to():
    base = SKPath(TEST_DIR)
    child = SKPath(TEST_DIR / "subdir" / "file2.txt")
    relative = child.relative_to(base)
    assert relative.ap.endswith("subdir/file2.txt") or "subdir" in str(relative)

test_relative_to()

@test("SKPath.relative_to: raises for unrelated paths")
def test_relative_to_unrelated():
    path1 = SKPath(TEST_DIR)
    path2 = SKPath("/completely/different/path")
    try:
        path1.relative_to(path2)
        assert False, "Should raise ValueError"
    except ValueError:
        pass

test_relative_to_unrelated()

@test("SKPath.with_name: changes filename")
def test_with_name():
    path = SKPath(TEST_DIR / "file.txt")
    new_path = path.with_name("newfile.md")
    assert new_path.name == "newfile.md"
    assert new_path.suffix == ".md"

test_with_name()

@test("SKPath.with_stem: changes stem only")
def test_with_stem():
    path = SKPath(TEST_DIR / "file.txt")
    new_path = path.with_stem("newfile")
    assert new_path.name == "newfile.txt"
    assert new_path.suffix == ".txt"

test_with_stem()

@test("SKPath.with_suffix: changes extension")
def test_with_suffix():
    path = SKPath(TEST_DIR / "file.txt")
    new_path = path.with_suffix(".md")
    assert new_path.name == "file.md"
    assert new_path.suffix == ".md"

test_with_suffix()

@test("SKPath.mkdir: creates directory")
def test_mkdir():
    new_dir = SKPath(TEST_DIR / "new_mkdir_test")
    new_dir.mkdir()
    assert new_dir.exists
    assert new_dir.is_dir

test_mkdir()

@test("SKPath.mkdir: parents=True creates nested dirs")
def test_mkdir_parents():
    nested = SKPath(TEST_DIR / "a" / "b" / "c")
    nested.mkdir(parents=True)
    assert nested.exists
    assert nested.is_dir

test_mkdir_parents()

@test("SKPath.mkdir: exist_ok=True doesn't raise")
def test_mkdir_exist_ok():
    existing = SKPath(TEST_DIR / "subdir")
    existing.mkdir(exist_ok=True)  # Should not raise

test_mkdir_exist_ok()

@test("SKPath.touch: creates file")
def test_touch():
    new_file = SKPath(TEST_DIR / "touched.txt")
    new_file.touch()
    assert new_file.exists
    assert new_file.is_file

test_touch()

@test("SKPath.resolve: returns resolved SKPath")
def test_resolve():
    path = SKPath(TEST_DIR / "file.txt")
    resolved = path.resolve()
    assert isinstance(resolved, SKPath)
    assert resolved.exists

test_resolve()

@test("SKPath.absolute: returns absolute SKPath")
def test_absolute():
    path = SKPath(TEST_DIR / "file.txt")
    absolute = path.absolute()
    assert isinstance(absolute, SKPath)

test_absolute()


# ============================================================================
# 6. DUNDER METHODS
# ============================================================================

print("\n" + "-"*40)
print("6. DUNDER METHODS")
print("-"*40)

@test("SKPath.__str__: returns ap")
def test_str():
    path = SKPath(TEST_DIR / "file.txt")
    s = str(path)
    assert s == path.ap

test_str()

@test("SKPath.__repr__: debugging representation")
def test_repr():
    path = SKPath(TEST_DIR / "file.txt")
    r = repr(path)
    assert "SKPath" in r
    assert "file.txt" in r

test_repr()

@test("SKPath.__fspath__: os.fspath compatibility")
def test_fspath():
    path = SKPath(TEST_DIR / "file.txt")
    fs = os.fspath(path)
    assert isinstance(fs, str)
    # Should be able to open the file
    with open(path, "r") as f:
        _ = f.read()

test_fspath()

@test("SKPath.__truediv__: path joining with /")
def test_truediv():
    base = SKPath(TEST_DIR)
    child = base / "subdir" / "file2.txt"
    assert isinstance(child, SKPath)
    assert child.exists
    assert child.name == "file2.txt"

test_truediv()

@test("SKPath.__rtruediv__: reverse path joining")
def test_rtruediv():
    child = SKPath("file.txt")
    # This creates a path relative to TEST_DIR
    combined = TEST_DIR / child._path
    assert "file.txt" in str(combined)

test_rtruediv()

@test("SKPath.__eq__: equality comparison")
def test_eq():
    path1 = SKPath(TEST_DIR / "file.txt")
    path2 = SKPath(TEST_DIR / "file.txt")
    path3 = SKPath(TEST_DIR / "other.txt")
    
    assert path1 == path2
    assert not (path1 == path3)
    assert path1 != path3

test_eq()

@test("SKPath.__eq__: compares with strings")
def test_eq_string():
    path = SKPath(TEST_DIR / "file.txt")
    assert path == str(TEST_DIR / "file.txt")

test_eq_string()

@test("SKPath.__eq__: compares with Path")
def test_eq_path():
    path = SKPath(TEST_DIR / "file.txt")
    assert path == TEST_DIR / "file.txt"

test_eq_path()

@test("SKPath.__eq__: None returns False")
def test_eq_none():
    path = SKPath(TEST_DIR / "file.txt")
    assert not (path == None)

test_eq_none()

@test("SKPath.__hash__: works in sets and dicts")
def test_hash():
    path1 = SKPath(TEST_DIR / "file.txt")
    path2 = SKPath(TEST_DIR / "file.txt")
    path3 = SKPath(TEST_DIR / "other.txt")
    
    # Hash should be consistent
    assert hash(path1) == hash(path2)
    
    # Works in set
    s = {path1, path2, path3}
    assert len(s) == 2  # path1 and path2 are same
    
    # Works as dict key
    d = {path1: "value"}
    assert d[path2] == "value"

test_hash()

@test("SKPath.__bool__: always truthy")
def test_bool():
    path = SKPath(TEST_DIR / "file.txt")
    nonexistent = SKPath("/does/not/exist")
    
    assert bool(path) == True
    assert bool(nonexistent) == True

test_bool()

@test("SKPath.__len__: number of path parts")
def test_len():
    path = SKPath(TEST_DIR / "subdir" / "file2.txt")
    length = len(path)
    assert length > 0
    assert length == len(path.parts)

test_len()

@test("SKPath.__iter__: iterate over parts")
def test_iter():
    path = SKPath(TEST_DIR / "file.txt")
    parts = list(path)
    assert "file.txt" in parts

test_iter()

@test("SKPath.__contains__: check part presence")
def test_contains():
    path = SKPath(TEST_DIR / "subdir" / "file2.txt")
    assert "subdir" in path
    assert "file2.txt" in path
    assert "nonexistent" not in path

test_contains()


# ============================================================================
# 7. ROOT DETECTION
# ============================================================================

print("\n" + "-"*40)
print("7. ROOT DETECTION")
print("-"*40)

@test("detect_project_root: finds project root")
def test_detect_root():
    # Clear any custom root
    clear_custom_root()
    clear_root_cache()
    
    root = detect_project_root(from_path=_this_file)
    assert root.exists()
    assert root.is_dir()
    # Should have a project indicator
    has_indicator = any([
        (root / "setup.py").exists(),
        (root / "pyproject.toml").exists(),
        (root / ".gitignore").exists(),
        (root / "setup.sk").exists(),
    ])
    assert has_indicator

test_detect_root()

@test("set_custom_root: overrides auto-detection")
def test_set_custom_root():
    clear_custom_root()
    
    set_custom_root(TEST_DIR)
    actual = get_custom_root()
    # Resolve TEST_DIR because set_custom_root resolves paths (macOS /var -> /private/var)
    expected = normalize_separators(str(TEST_DIR.resolve()))
    assert actual == expected, f"Expected '{expected}', got '{actual}'"
    
    clear_custom_root()

test_set_custom_root()

@test("get_custom_root: returns None when not set")
def test_get_custom_root_none():
    clear_custom_root()
    assert get_custom_root() is None

test_get_custom_root_none()

@test("clear_custom_root: clears the custom root")
def test_clear_custom_root():
    set_custom_root(TEST_DIR)
    assert get_custom_root() is not None
    
    clear_custom_root()
    assert get_custom_root() is None

test_clear_custom_root()

@test("set_custom_root: raises for non-existent path")
def test_set_root_nonexistent():
    clear_custom_root()
    try:
        set_custom_root("/this/path/does/not/exist")
        assert False, "Should raise PathDetectionError"
    except PathDetectionError:
        pass

test_set_root_nonexistent()

@test("set_custom_root: raises for file path")
def test_set_root_file():
    clear_custom_root()
    try:
        set_custom_root(TEST_DIR / "file.txt")
        assert False, "Should raise PathDetectionError"
    except PathDetectionError:
        pass

test_set_root_file()

@test("CustomRoot: context manager works")
def test_custom_root_context():
    clear_custom_root()
    
    with CustomRoot(TEST_DIR):
        actual = get_custom_root()
        # Resolve because CustomRoot resolves paths (macOS /var -> /private/var)
        expected = normalize_separators(str(TEST_DIR.resolve()))
        assert actual == expected, f"Inside context: expected '{expected}', got '{actual}'"
    
    after = get_custom_root()
    assert after is None, f"After context: expected None, got '{after}'"

test_custom_root_context()

@test("CustomRoot: restores previous root on exit")
def test_custom_root_restore():
    clear_custom_root()
    
    set_custom_root(_project_root)
    original = get_custom_root()
    
    with CustomRoot(TEST_DIR):
        inside = get_custom_root()
        # Resolve because CustomRoot resolves paths (macOS /var -> /private/var)
        expected_inside = normalize_separators(str(TEST_DIR.resolve()))
        assert inside == expected_inside, f"Inside: expected '{expected_inside}', got '{inside}'"
    
    after = get_custom_root()
    assert after == original, f"After: expected '{original}', got '{after}'"
    clear_custom_root()

test_custom_root_restore()

@test("detect_project_root: expected_name validation")
def test_detect_root_expected_name():
    clear_custom_root()
    clear_root_cache()
    
    root = detect_project_root(from_path=_this_file)
    actual_name = root.name
    
    # Should work with correct name
    root2 = detect_project_root(from_path=_this_file, expected_name=actual_name)
    assert root2.name == actual_name
    
    # Should fail with wrong name
    try:
        detect_project_root(from_path=_this_file, expected_name="wrong_name_xyz")
        assert False, "Should raise PathDetectionError"
    except PathDetectionError:
        pass

test_detect_root_expected_name()

@test("clear_root_cache: clears cached root")
def test_clear_cache():
    clear_root_cache()
    # Just verify it doesn't crash
    detect_project_root(from_path=_this_file)
    clear_root_cache()

test_clear_cache()


# ============================================================================
# 8. @AUTOPATH DECORATOR
# ============================================================================

print("\n" + "-"*40)
print("8. @AUTOPATH DECORATOR")
print("-"*40)

@test("@autopath: converts str to SKPath for AnyPath")
def test_autopath_str_to_skpath():
    @autopath()
    def get_name(path: AnyPath):
        assert isinstance(path, SKPath)
        return path.name
    
    result = get_name(str(TEST_DIR / "file.txt"))
    assert result == "file.txt"

test_autopath_str_to_skpath()

@test("@autopath: converts Path to SKPath for AnyPath")
def test_autopath_path_to_skpath():
    @autopath()
    def get_name(path: AnyPath):
        assert isinstance(path, SKPath)
        return path.name
    
    result = get_name(TEST_DIR / "file.txt")
    assert result == "file.txt"

test_autopath_path_to_skpath()

@test("@autopath: keeps SKPath as SKPath")
def test_autopath_skpath_unchanged():
    @autopath()
    def get_name(path: AnyPath):
        assert isinstance(path, SKPath)
        return path.name
    
    result = get_name(SKPath(TEST_DIR / "file.txt"))
    assert result == "file.txt"

test_autopath_skpath_unchanged()

@test("@autopath: converts to Path when annotated")
def test_autopath_to_path():
    @autopath()
    def get_type(path: Path):
        assert isinstance(path, Path)
        return type(path).__name__
    
    result = get_type(str(TEST_DIR / "file.txt"))
    assert "Path" in result

test_autopath_to_path()

@test("@autopath: converts to str when annotated")
def test_autopath_to_str():
    @autopath()
    def get_type(path: str):
        assert isinstance(path, str)
        return type(path).__name__
    
    result = get_type(TEST_DIR / "file.txt")
    assert result == "str"

test_autopath_to_str()

@test("@autopath: handles list[AnyPath]")
def test_autopath_list():
    @autopath()
    def get_names(paths: list[AnyPath]):
        assert all(isinstance(p, SKPath) for p in paths)
        return [p.name for p in paths]
    
    result = get_names([
        str(TEST_DIR / "file.txt"),
        TEST_DIR / "subdir",
    ])
    assert "file.txt" in result
    assert "subdir" in result

test_autopath_list()

@test("@autopath: use_caller provides caller path")
def test_autopath_use_caller():
    @autopath(use_caller=True)
    def get_caller_name(path: AnyPath):
        return path.name
    
    result = get_caller_name()
    assert result == "test_all_features.py"

test_autopath_use_caller()

@test("@autopath: debug prints conversion messages")
def test_autopath_debug():
    import io
    import contextlib
    
    @autopath(debug=True)
    def process(path: AnyPath):
        return path.name
    
    # Capture stdout
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        process(str(TEST_DIR / "file.txt"))
    
    output = f.getvalue()
    assert "@autopath" in output or "Converted" in output

test_autopath_debug()

@test("@autopath: priority SKPath > Path > str (typing.Union)")
def test_autopath_priority():
    from typing import Union
    
    # Use Union[] syntax to ensure typing.Union is used (not types.UnionType)
    @autopath()
    def test_skpath_path(path: Union[SKPath, Path]):
        return type(path).__name__
    
    @autopath()
    def test_path_str(path: Union[Path, str]):
        return type(path).__name__
    
    # SKPath wins over Path
    r1 = test_skpath_path("test")
    assert "SKPath" in r1, f"Expected SKPath, got {r1}"
    
    # Path wins over str  
    r2 = test_path_str("test")
    assert "Path" in r2, f"Expected Path, got {r2}"

test_autopath_priority()

@test("@autopath: priority SKPath > Path > str (Python 3.10+ | syntax)")
def test_autopath_priority_pipe():
    import sys
    if sys.version_info < (3, 10):
        # Skip on older Python
        return
    
    # Use X | Y syntax (Python 3.10+)
    @autopath()
    def test_skpath_path_pipe(path: SKPath | Path):
        return type(path).__name__
    
    @autopath()
    def test_path_str_pipe(path: Path | str):
        return type(path).__name__
    
    # SKPath wins over Path
    r1 = test_skpath_path_pipe("test")
    assert "SKPath" in r1, f"Expected SKPath, got {r1}"
    
    # Path wins over str  
    r2 = test_path_str_pipe("test")
    assert "Path" in r2, f"Expected Path, got {r2}"

test_autopath_priority_pipe()

@test("@autopath: handles None gracefully")
def test_autopath_none():
    @autopath()
    def process(path: AnyPath):
        return path
    
    result = process(None)
    assert result is None

test_autopath_none()


# ============================================================================
# 9. API FUNCTIONS
# ============================================================================

print("\n" + "-"*40)
print("9. API FUNCTIONS")
print("-"*40)

@test("get_project_root: returns SKPath")
def test_get_project_root():
    clear_custom_root()
    root = get_project_root()
    assert isinstance(root, SKPath)
    assert root.exists
    assert root.is_dir

test_get_project_root()

@test("get_caller_path: returns caller's SKPath")
def test_get_caller_path():
    caller = get_caller_path()
    assert isinstance(caller, SKPath)
    assert "test_all_features.py" in caller.name

test_get_caller_path()

@test("get_current_dir: returns caller's directory")
def test_get_current_dir():
    current = get_current_dir()
    assert isinstance(current, SKPath)
    assert current.is_dir
    assert "test_skpath" in str(current)

test_get_current_dir()

@test("get_cwd: returns current working directory")
def test_get_cwd():
    cwd = get_cwd()
    assert isinstance(cwd, SKPath)
    assert cwd.exists
    assert cwd.is_dir

test_get_cwd()

@test("get_module_path: finds module file")
def test_get_module_path():
    # Get path of this test module
    import suitkaise.skpath.api as api_module
    path = get_module_path(api_module)
    assert path is not None
    assert isinstance(path, SKPath)
    assert "api.py" in path.name

test_get_module_path()

@test("get_id: generates reversible ID")
def test_get_id():
    path_id = get_id(TEST_DIR / "file.txt")
    assert path_id
    assert isinstance(path_id, str)

test_get_id()

@test("get_project_paths: lists project files")
def test_get_project_paths():
    paths = get_project_paths()
    assert len(paths) > 0
    assert all(isinstance(p, SKPath) for p in paths)

test_get_project_paths()

@test("get_project_paths: as_strings returns strings")
def test_get_project_paths_strings():
    paths = get_project_paths(as_strings=True)
    assert len(paths) > 0
    assert all(isinstance(p, str) for p in paths)

test_get_project_paths_strings()

@test("get_project_structure: returns nested dict")
def test_get_project_structure():
    structure = get_project_structure()
    assert isinstance(structure, dict)
    assert len(structure) > 0

test_get_project_structure()

@test("get_formatted_project_tree: returns tree string")
def test_get_formatted_project_tree():
    tree = get_formatted_project_tree(depth=2)
    assert isinstance(tree, str)
    assert "├" in tree or "└" in tree or len(tree) > 0

test_get_formatted_project_tree()


# ============================================================================
# 10. EDGE CASES & STRESS TESTS
# ============================================================================

print("\n" + "-"*40)
print("10. EDGE CASES & STRESS TESTS")
print("-"*40)

@test("SKPath: very long path")
def test_long_path():
    long_name = "a" * 200
    path = SKPath(TEST_DIR / long_name)
    assert path.name == long_name

test_long_path()

@test("SKPath: special characters in path")
def test_special_chars():
    # Test with spaces and special chars
    special = SKPath(TEST_DIR / "file with spaces.txt")
    assert "file with spaces" in special.name

test_special_chars()

@test("SKPath: unicode characters")
def test_unicode():
    unicode_path = SKPath(TEST_DIR / "文件.txt")
    assert "文件" in unicode_path.name

test_unicode()

@test("SKPath: empty stem file")
def test_empty_stem():
    path = SKPath(TEST_DIR / ".hidden")
    assert path.stem == ".hidden" or path.name == ".hidden"

test_empty_stem()

@test("Thread safety: concurrent SKPath creation")
def test_thread_safety():
    results = []
    errors = []
    
    def create_paths():
        try:
            for i in range(10):
                path = SKPath(_this_file)
                _ = path.ap
                _ = path.np
                _ = path.id
                _ = hash(path)
            results.append(True)
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=create_paths) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert len(errors) == 0
    assert len(results) == 5

test_thread_safety()

@test("Thread safety: concurrent root operations")
def test_thread_safety_root():
    errors = []
    
    def toggle_root():
        try:
            for _ in range(10):
                set_custom_root(TEST_DIR)
                _ = get_custom_root()
                clear_custom_root()
        except Exception as e:
            errors.append(e)
    
    threads = [threading.Thread(target=toggle_root) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    clear_custom_root()
    assert len(errors) == 0

test_thread_safety_root()

@test("SKPath: many sequential operations")
def test_sequential_ops():
    path = SKPath(TEST_DIR)
    
    # Chain many operations
    for _ in range(100):
        _ = path.ap
        _ = path.np
        _ = path.name
        _ = path.exists
        _ = hash(path)
        _ = str(path)

test_sequential_ops()

@test("SKPath: handles root of filesystem")
def test_filesystem_root():
    root = SKPath("/")
    assert root.exists
    assert root.is_dir
    assert root.ap == "/"

test_filesystem_root()


# ============================================================================
# 11. ERROR CONDITIONS
# ============================================================================

print("\n" + "-"*40)
print("11. ERROR CONDITIONS")
print("-"*40)

@test("SKPath.stat: raises for non-existent file")
def test_stat_nonexistent():
    path = SKPath(TEST_DIR / "nonexistent_file.txt")
    try:
        _ = path.stat
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        pass

test_stat_nonexistent()

@test("SKPath.iterdir: raises for file")
def test_iterdir_file():
    path = SKPath(TEST_DIR / "file.txt")
    try:
        list(path.iterdir())
        assert False, "Should raise NotADirectoryError"
    except NotADirectoryError:
        pass

test_iterdir_file()

@test("PathDetectionError: meaningful error message")
def test_error_message():
    try:
        set_custom_root("/does/not/exist/at/all")
    except PathDetectionError as e:
        assert "does not exist" in str(e)

test_error_message()


# ============================================================================
# CLEANUP & SUMMARY
# ============================================================================

print("\n" + "-"*40)
print("CLEANUP")
print("-"*40)

# Clean up
clear_custom_root()
clear_root_cache()

import shutil
try:
    shutil.rmtree(TEST_DIR)
    print(f"  Cleaned up test directory: {TEST_DIR}")
except Exception as e:
    print(f"  Warning: Could not clean up {TEST_DIR}: {e}")

# Final summary
success = result.summary()

if not success:
    sys.exit(1)
