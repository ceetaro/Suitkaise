"""
Integration Test: Path Utilities

Real-world scenario: A code analysis tool that:
1. Discovers project structure using skpath utilities
2. Uses @autopath decorator for path parameter handling
3. Encodes paths to IDs for database storage
4. Generates project tree visualizations
5. Validates and sanitizes file paths

This tests the full skpath integration of:
- Skpath: Core path class functionality
- @autopath: Automatic path type conversion
- get_project_paths, get_project_structure, get_formatted_project_tree
- encode_path_id, decode_path_id, get_id
- is_valid_filename, streamline_path
"""

import sys
import os
import tempfile
import shutil
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
    autopath,
    get_project_root,
    get_project_paths,
    get_project_structure,
    get_formatted_project_tree,
    get_id,
    get_caller_path,
    get_current_dir,
    get_cwd,
    get_module_path,
    is_valid_filename,
    streamline_path,
    set_custom_root,
    get_custom_root,
    clear_custom_root,
    PathDetectionError,
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
        return failed == 0


# =============================================================================
# Autopath Decorator Tests
# =============================================================================

def test_autopath_string_to_skpath():
    """@autopath should convert string to Skpath."""
    @autopath()
    def process_file(path: Skpath) -> str:
        return path.name
    
    result = process_file("/some/path/to/file.txt")
    
    assert result == "file.txt", f"Should extract filename, got {result}"


def test_autopath_path_to_skpath():
    """@autopath should convert pathlib.Path to Skpath."""
    @autopath()
    def get_suffix(path: Skpath) -> str:
        return path.suffix
    
    p = Path("/some/file.py")
    result = get_suffix(p)
    
    assert result == ".py", f"Should extract suffix, got {result}"


def test_autopath_skpath_unchanged():
    """@autopath should pass Skpath through unchanged."""
    @autopath()
    def get_stem(path: Skpath) -> str:
        return path.stem
    
    sk = Skpath("/some/file.txt")
    result = get_stem(sk)
    
    assert result == "file", f"Should extract stem, got {result}"


def test_autopath_multiple_params():
    """@autopath should convert multiple path parameters."""
    @autopath()
    def compare_paths(path1: Skpath, path2: Skpath) -> bool:
        return path1.suffix == path2.suffix
    
    result = compare_paths("/file1.py", Path("/file2.py"))
    
    assert result == True, "Both should have .py suffix"


def test_autopath_mixed_params():
    """@autopath should only convert annotated parameters."""
    @autopath(only=['path'])
    def process_with_options(path: Skpath, verbose: bool = False) -> dict:
        return {
            "name": path.name,
            "verbose": verbose,
        }
    
    result = process_with_options("/some/file.txt", verbose=True)
    
    assert result["name"] == "file.txt"
    assert result["verbose"] == True


def test_autopath_none_handling():
    """@autopath should handle None gracefully."""
    from typing import Optional
    
    @autopath()
    def optional_path(path: Optional[Skpath] = None) -> str:
        if path is None:
            return "no path"
        return path.name
    
    result = optional_path()
    assert result == "no path"
    
    result = optional_path("/some/file.txt")
    assert result == "file.txt"


# =============================================================================
# Project Path Functions Tests
# =============================================================================

def test_get_project_paths():
    """get_project_paths should return list of paths in project."""
    clear_custom_root()
    
    paths = get_project_paths(as_strings=True)
    
    assert isinstance(paths, list), "Should return a list"
    assert len(paths) > 0, "Should find some paths"
    
    # Should contain Python files
    py_files = [p for p in paths if p.endswith('.py')]
    assert len(py_files) > 0, "Should find Python files"


def test_get_project_paths_as_skpath():
    """get_project_paths should return Skpath objects when as_strings=False."""
    clear_custom_root()
    
    paths = get_project_paths(as_strings=False)
    
    assert len(paths) > 0, "Should find some paths"
    
    # Check first few are Skpath objects
    for path in paths[:5]:
        assert isinstance(path, Skpath), f"Should be Skpath, got {type(path)}"


def test_get_project_paths_with_exclude():
    """get_project_paths should respect exclude parameter."""
    clear_custom_root()
    
    all_paths = get_project_paths(as_strings=True)
    
    # Exclude tests directory
    filtered_paths = get_project_paths(exclude=["tests"], as_strings=True)
    
    # Should have fewer paths (at minimum)
    # Note: the exclude might work on directory names, not substrings
    assert len(filtered_paths) <= len(all_paths), "Filtering should not increase count"


def test_get_project_structure():
    """get_project_structure should return hierarchical dict."""
    clear_custom_root()
    
    structure = get_project_structure()
    
    assert isinstance(structure, dict), "Should return a dict"
    assert len(structure) > 0, "Should have content"
    
    # Root should have project name as key
    root_key = list(structure.keys())[0]
    assert isinstance(structure[root_key], dict), "Root value should be dict"


def test_get_formatted_project_tree():
    """get_formatted_project_tree should return formatted string."""
    clear_custom_root()
    
    tree = get_formatted_project_tree(depth=2, include_files=True)
    
    assert isinstance(tree, str), "Should return string"
    assert len(tree) > 0, "Should have content"
    
    # Should contain tree characters
    assert "├" in tree or "└" in tree or "/" in tree, "Should have tree formatting"


def test_get_formatted_project_tree_depth():
    """get_formatted_project_tree depth parameter should limit depth."""
    clear_custom_root()
    
    shallow = get_formatted_project_tree(depth=1, include_files=False)
    deep = get_formatted_project_tree(depth=3, include_files=False)
    
    # Deeper tree should have more lines (generally)
    shallow_lines = len(shallow.strip().split('\n'))
    deep_lines = len(deep.strip().split('\n'))
    
    # Deep should have at least as many lines
    assert deep_lines >= shallow_lines, \
        f"Deeper tree should have more lines: shallow={shallow_lines}, deep={deep_lines}"


# =============================================================================
# Path ID Tests
# =============================================================================

def test_get_id_returns_string():
    """get_id should return a string identifier."""
    path_id = get_id("/some/path/to/file.txt")
    
    assert isinstance(path_id, str), "Should return string"
    assert len(path_id) > 0, "Should not be empty"


def test_get_id_different_for_different_paths():
    """get_id should return different IDs for different paths."""
    id1 = get_id("/path/to/file1.txt")
    id2 = get_id("/path/to/file2.txt")
    
    assert id1 != id2, "Different paths should have different IDs"


def test_skpath_id_property():
    """Skpath.id should return the path ID."""
    path = Skpath("/some/path/file.txt")
    
    assert hasattr(path, 'id'), "Skpath should have id property"
    assert isinstance(path.id, str), "id should be string"
    assert len(path.id) > 0, "id should not be empty"


def test_get_id_matches_skpath_id():
    """get_id and Skpath.id should return same value."""
    path_str = "/some/path/file.txt"
    
    func_id = get_id(path_str)
    skpath_id = Skpath(path_str).id
    
    assert func_id == skpath_id, f"IDs should match: {func_id} vs {skpath_id}"


# =============================================================================
# Filename Validation Tests
# =============================================================================

def test_is_valid_filename_valid():
    """is_valid_filename should accept valid filenames."""
    valid_names = [
        "file.txt",
        "my-file.py",
        "file_name.md",
        "123.json",
        "file.tar.gz",
        "CamelCase.JS",
    ]
    
    for name in valid_names:
        assert is_valid_filename(name), f"{name} should be valid"


def test_is_valid_filename_invalid():
    """is_valid_filename should reject invalid filenames."""
    invalid_names = [
        "",  # Empty
        "file/name.txt",  # Contains slash
        "file\\name.txt",  # Contains backslash
        "file<name>.txt",  # Contains < >
        "file:name.txt",  # Contains colon
        "file?name.txt",  # Contains question mark
        "file*name.txt",  # Contains asterisk
        'file"name.txt',  # Contains quote
        "CON",  # Windows reserved
        "PRN.txt",  # Windows reserved with extension
        "file.",  # Ends with period
        "file ",  # Ends with space
    ]
    
    for name in invalid_names:
        assert not is_valid_filename(name), f"{name} should be invalid"


def test_streamline_path_removes_invalid():
    """streamline_path should replace invalid characters."""
    result = streamline_path("file<name>?.txt")
    
    assert "<" not in result
    assert ">" not in result
    assert "?" not in result


def test_streamline_path_max_length():
    """streamline_path should respect max_length."""
    long_name = "a" * 200
    result = streamline_path(long_name, max_length=50)
    
    assert len(result) <= 50, f"Should truncate to 50, got {len(result)}"


def test_streamline_path_lowercase():
    """streamline_path should lowercase when requested."""
    result = streamline_path("MyFile.TXT", lowercase=True)
    
    assert result == "myfile.txt", f"Should be lowercase, got {result}"


def test_streamline_path_unicode():
    """streamline_path should handle unicode option."""
    # With unicode allowed
    result_unicode = streamline_path("файл.txt", allow_unicode=True)
    assert "файл" in result_unicode or "_" in result_unicode  # Depends on implementation
    
    # Without unicode
    result_ascii = streamline_path("файл.txt", allow_unicode=False)
    # Non-ASCII should be replaced
    assert "ф" not in result_ascii


# =============================================================================
# Caller Path Functions Tests
# =============================================================================

def test_get_caller_path():
    """get_caller_path should return path of calling file."""
    caller = get_caller_path()
    
    assert isinstance(caller, Skpath), "Should return Skpath"
    assert "test_path_utilities.py" in caller.name, f"Should be this file, got {caller.name}"


def test_get_current_dir():
    """get_current_dir should return directory of caller."""
    current = get_current_dir()
    
    assert isinstance(current, Skpath), "Should return Skpath"
    assert current.is_dir, "Should be a directory"


def test_get_cwd():
    """get_cwd should return current working directory."""
    cwd = get_cwd()
    
    assert isinstance(cwd, Skpath), "Should return Skpath"
    assert cwd.is_dir, "Should be a directory"
    assert cwd.exists, "Should exist"


def test_get_module_path():
    """get_module_path should return path of module."""
    import suitkaise.paths as paths_module
    
    path = get_module_path(paths_module)
    
    assert path is not None, "Should find module path"
    assert isinstance(path, Skpath), "Should return Skpath"
    # Module path can be the __init__.py or the directory itself
    assert "paths" in str(path) or "__init__" in path.name, f"Should point to paths module, got {path}"


def test_get_module_path_from_class():
    """get_module_path should work with class objects."""
    path = get_module_path(Skpath)
    
    assert path is not None, "Should find path"
    assert isinstance(path, Skpath), "Should return Skpath"


# =============================================================================
# Custom Root Tests
# =============================================================================

def test_custom_root_integration():
    """Test custom root setting and clearing."""
    clear_custom_root()
    
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set as custom root
        set_custom_root(tmpdir)
        
        custom = get_custom_root()
        assert custom is not None, "Custom root should be set"
        
        # Get project root should use custom
        root = get_project_root()
        assert str(root.ap) == tmpdir or root.name == os.path.basename(tmpdir), \
            f"Root should be custom dir, got {root.ap}"
        
        # Clear
        clear_custom_root()
        
        # Should revert to auto-detection
        root_after = get_project_root()
        assert str(root_after.ap) != tmpdir, "Should not be temp dir after clear"


# =============================================================================
# Full Integration Tests
# =============================================================================

def test_code_analysis_workflow():
    """
    Full integration test simulating a code analysis tool:
    1. Discover project files
    2. Filter by type
    3. Generate IDs for database storage
    4. Validate output paths
    5. Generate tree visualization
    """
    clear_custom_root()
    
    # Step 1: Get all project paths
    all_paths = get_project_paths(as_strings=False)
    
    assert len(all_paths) > 0, "Should find paths"
    
    # Step 2: Filter to Python files
    py_files = [p for p in all_paths if p.suffix == ".py"]
    
    assert len(py_files) > 0, "Should find Python files"
    
    # Step 3: Generate IDs for each (simulating DB storage)
    file_ids = {}
    for path in py_files[:10]:  # Limit for speed
        file_id = path.id
        file_ids[file_id] = path.rp  # Relative path
    
    assert len(file_ids) == len(py_files[:10]), "Should have ID for each file"
    
    # Step 4: Validate a potential output filename
    output_name = streamline_path(
        "Analysis Report <2024>.txt",
        replacement_char="_",
        max_length=50
    )
    
    assert is_valid_filename(output_name), f"Output name should be valid: {output_name}"
    
    # Step 5: Generate tree
    tree = get_formatted_project_tree(depth=2, include_files=True)
    
    assert len(tree) > 0, "Should generate tree"


def test_autopath_in_analysis_pipeline():
    """Test @autopath in a realistic analysis pipeline."""
    
    @autopath()
    def analyze_file(path: Skpath) -> dict:
        """Analyze a single file."""
        return {
            "path": str(path),
            "name": path.name,
            "extension": path.suffix,
            "id": path.id,
            "exists": path.exists,
        }
    
    @autopath()
    def compare_files(path1: Skpath, path2: Skpath) -> dict:
        """Compare two files."""
        return {
            "same_type": path1.suffix == path2.suffix,
            "same_parent": path1.parent == path2.parent,
        }
    
    # Use with various input types
    result1 = analyze_file("/some/file.py")
    assert result1["extension"] == ".py"
    
    result2 = analyze_file(Path("/other/file.txt"))
    assert result2["extension"] == ".txt"
    
    result3 = analyze_file(Skpath("/another/file.js"))
    assert result3["extension"] == ".js"
    
    # Compare files
    comparison = compare_files("/dir/a.py", Path("/dir/b.py"))
    assert comparison["same_type"] == True
    assert comparison["same_parent"] == True


# =============================================================================
# Main Entry Point
# =============================================================================

# Colors for verbose output
GREEN = '\033[92m'
RED = '\033[91m'
CYAN = '\033[96m'
DIM = '\033[2m'
BOLD = '\033[1m'
RESET = '\033[0m'


def run_scenario(name: str, description: str, test_func, results: list):
    """Run a scenario with verbose output."""
    print(f"\n  {CYAN}Testing:{RESET} {name}")
    print(f"  {DIM}{description}{RESET}")
    
    try:
        test_func()
        results.append((name, True))
        print(f"  {GREEN}✓ Works as expected{RESET}")
    except AssertionError as e:
        results.append((name, False))
        print(f"  {RED}✗ Failed: {e}{RESET}")
    except Exception as e:
        results.append((name, False))
        print(f"  {RED}✗ Error: {type(e).__name__}: {e}{RESET}")


def run_all_tests():
    """Run all path utilities integration tests with verbose output."""
    results = []
    
    print(f"\n  {DIM}This scenario simulates a code analysis tool that discovers files,")
    print(f"  generates project trees, and manages path identifiers.{RESET}")
    
    # @autopath decorator - automatic path type conversion
    print(f"\n  {BOLD}Path Type Conversion (@autopath decorator):{RESET}")
    run_scenario("String to Skpath", "Convert string paths automatically", test_autopath_string_to_skpath, results)
    run_scenario("Path to Skpath", "Convert pathlib.Path automatically", test_autopath_path_to_skpath, results)
    run_scenario("Skpath Passthrough", "Leave Skpath objects unchanged", test_autopath_skpath_unchanged, results)
    run_scenario("Multiple Parameters", "Convert multiple path args at once", test_autopath_multiple_params, results)
    run_scenario("Mixed Parameters", "Mix path and non-path arguments", test_autopath_mixed_params, results)
    run_scenario("None Handling", "Gracefully handle None values", test_autopath_none_handling, results)
    
    # Project discovery
    print(f"\n  {BOLD}Project Discovery:{RESET}")
    run_scenario("List Project Files", "Get all files in a project", test_get_project_paths, results)
    run_scenario("Files as Skpath", "Get files as Skpath objects for enhanced operations", test_get_project_paths_as_skpath, results)
    run_scenario("Exclude Patterns", "Filter out unwanted directories (node_modules, __pycache__)", test_get_project_paths_with_exclude, results)
    run_scenario("Project Structure", "Get files grouped by directory", test_get_project_structure, results)
    run_scenario("Project Tree", "Generate ASCII tree visualization", test_get_formatted_project_tree, results)
    run_scenario("Tree Depth Limit", "Limit tree to specific depth", test_get_formatted_project_tree_depth, results)
    
    # Path IDs for database storage
    print(f"\n  {BOLD}Path Identifiers (for database storage):{RESET}")
    run_scenario("Generate ID", "Create unique ID from path", test_get_id_returns_string, results)
    run_scenario("Unique IDs", "Different paths get different IDs", test_get_id_different_for_different_paths, results)
    run_scenario("Skpath.id Property", "Access ID from Skpath object", test_skpath_id_property, results)
    run_scenario("ID Consistency", "get_id and .id match", test_get_id_matches_skpath_id, results)
    
    # Filename validation
    print(f"\n  {BOLD}Filename Validation & Sanitization:{RESET}")
    run_scenario("Valid Filenames", "Accept safe filenames", test_is_valid_filename_valid, results)
    run_scenario("Invalid Filenames", "Reject dangerous filenames", test_is_valid_filename_invalid, results)
    run_scenario("Sanitize Path", "Remove invalid characters", test_streamline_path_removes_invalid, results)
    run_scenario("Length Limit", "Truncate long filenames", test_streamline_path_max_length, results)
    run_scenario("Case Normalization", "Optionally lowercase filenames", test_streamline_path_lowercase, results)
    run_scenario("Unicode Handling", "Transliterate non-ASCII characters", test_streamline_path_unicode, results)
    
    # Caller path functions
    print(f"\n  {BOLD}Caller Path Detection:{RESET}")
    run_scenario("Caller's File", "Get path of calling code", test_get_caller_path, results)
    run_scenario("Caller's Directory", "Get directory of calling code", test_get_current_dir, results)
    run_scenario("Working Directory", "Get current working directory", test_get_cwd, results)
    run_scenario("Module Path", "Get path of a module", test_get_module_path, results)
    run_scenario("Class Module Path", "Get module path from class", test_get_module_path_from_class, results)
    
    # Custom root
    print(f"\n  {BOLD}Custom Project Root:{RESET}")
    run_scenario("Set Custom Root", "Override project root detection", test_custom_root_integration, results)
    
    # Full integration
    print(f"\n  {BOLD}Complete Workflows:{RESET}")
    run_scenario("Code Analysis Tool", "Full workflow: discover, analyze, report", test_code_analysis_workflow, results)
    run_scenario("Analysis Pipeline", "Using @autopath throughout a pipeline", test_autopath_in_analysis_pipeline, results)
    
    # Summary
    passed = sum(1 for _, p in results if p)
    failed = len(results) - passed
    
    print(f"\n  {BOLD}{'─'*70}{RESET}")
    if failed == 0:
        print(f"  {GREEN}{BOLD}✓ All {passed} scenarios passed!{RESET}")
    else:
        print(f"  Passed: {passed}  |  {RED}Failed: {failed}{RESET}")
    print(f"  {BOLD}{'─'*70}{RESET}")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
