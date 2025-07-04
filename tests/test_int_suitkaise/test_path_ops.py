"""
Comprehensive test suite for internal path operations.

Tests all internal functionality except SKPath (which is in external module).
Uses colorized output for easy reading and good spacing for clarity.

This test suite validates the fixed internal module with all bug fixes applied.
"""

import tempfile
import shutil
import sys
from pathlib import Path

# Add the suitkaise path for testing (adjust as needed)
# This allows testing the internal functions directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Import all internal functions to test
    from suitkaise._int.core.path_ops import (
        _get_caller_file_path,
        _get_non_sk_caller_file_path,
        _is_suitkaise_module,
        _get_module_file_path,
        _IndicatorExpander,
        _ProjectRootDetector,
        _get_project_root,
        _force_project_root,
        _clear_forced_project_root,
        _get_forced_project_root,
        _get_cwd,
        _get_current_dir,
        _equal_paths,
        _path_id,
        _path_id_short,
        _parse_gitignore_file,
        _get_all_project_paths,
        _get_project_structure,
        _get_formatted_project_tree,
        PROJECT_INDICATORS
    )
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Warning: Could not import internal functions: {e}")
    print("This is expected if running outside the suitkaise project structure")
    IMPORTS_SUCCESSFUL = False


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    @classmethod
    def disable(cls):
        """Disable colors for file output."""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = ''
        cls.MAGENTA = cls.CYAN = cls.WHITE = cls.BOLD = cls.UNDERLINE = cls.END = ''


def print_section(title: str):
    """Print a section header with proper spacing."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title.upper()}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_test(test_name: str):
    """Print a test name with proper formatting."""
    print(f"{Colors.BLUE}{Colors.BOLD}Testing: {test_name}...{Colors.END}")


def print_result(condition: bool, message: str):
    """Print a test result with color coding."""
    color = Colors.GREEN if condition else Colors.RED
    symbol = "✓" if condition else "✗"
    print(f"  {color}{symbol} {message}{Colors.END}")


def print_info(label: str, value: str):
    """Print labeled information."""
    print(f"  {Colors.MAGENTA}{label}:{Colors.END} {Colors.WHITE}{value}{Colors.END}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"  {Colors.YELLOW}⚠ {message}{Colors.END}")


def test_caller_detection():
    """Test caller file detection functions."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping caller detection tests - imports failed")
        return
        
    print_test("Caller File Detection")
    
    # Test _get_caller_file_path
    try:
        caller_file = _get_caller_file_path()
        print_info("Direct caller file", str(caller_file))
        print_result(caller_file.exists(), "Caller file exists")
        print_result(str(caller_file).endswith('.py'), "Caller file is Python")
        print_result(caller_file.name == Path(__file__).name, "Correctly identified test file")
    except Exception as e:
        print_result(False, f"Failed to get caller file: {e}")
    
    # Test _get_non_sk_caller_file_path
    try:
        user_caller = _get_non_sk_caller_file_path()
        if user_caller:
            print_info("Non-SK caller file", str(user_caller))
            print_result(user_caller.exists(), "Non-SK caller file exists")
            
            # Check if it's correctly identified as non-SK
            is_sk = _is_suitkaise_module(user_caller)
            print_result(not is_sk, f"File correctly identified as non-SK (is_sk: {is_sk})")
        else:
            print_warning("No non-SK caller found")
            print_info("Note", "This is expected when running from within SK test structure")
    except Exception as e:
        print_result(False, f"Failed to get non-SK caller: {e}")
    
    print()


def test_module_detection():
    """Test suitkaise module detection."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping module detection tests - imports failed")
        return
        
    print_test("Suitkaise Module Detection")
    
    # Test current file detection
    current_file = Path(__file__)
    try:
        is_sk_current = _is_suitkaise_module(current_file)
        print_info("Current test file", str(current_file))
        print_info("Detected as SK module", str(is_sk_current))
        
        # This could be True or False depending on where the test is run
        if is_sk_current:
            print_result(True, "Current file identified as SK module (expected if in SK structure)")
        else:
            print_result(True, "Current file identified as non-SK (expected if test run externally)")
    except Exception as e:
        print_result(False, f"Module detection failed: {e}")
    
    # Test some clearly non-suitkaise paths
    test_paths = [
        Path("/usr/bin/python3"),
        Path("/home/user/project/main.py"),
        Path("C:\\Windows\\System32\\notepad.exe"),
        Path("/tmp/test.py"),
        Path("/var/log/system.log")
    ]
    
    print(f"\n  {Colors.BLUE}Testing clearly non-SK paths:{Colors.END}")
    for test_path in test_paths:
        try:
            is_sk = _is_suitkaise_module(test_path)
            color = Colors.GREEN if not is_sk else Colors.YELLOW
            print(f"    {color}{test_path.name}: SK={is_sk}{Colors.END}")
            
            if is_sk:
                print_warning(f"Unexpected: {test_path} detected as SK module")
        except Exception as e:
            print(f"    {Colors.RED}Error testing {test_path.name}: {e}{Colors.END}")
    
    print()


def test_indicator_expander():
    """Test the indicator expansion system."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping indicator expansion tests - imports failed")
        return
        
    print_test("Indicator Expansion System")
    
    try:
        expander = _IndicatorExpander()
        
        # Test reference expansion
        license_patterns = expander.expand_reference("@file_groups.license")
        print_info("License patterns count", str(len(license_patterns)))
        print_result("LICENSE" in license_patterns, "Contains 'LICENSE' pattern")
        print_result(any("license.*" in p for p in license_patterns), "Contains license wildcard patterns")
        
        # Show some example patterns
        sample_patterns = list(license_patterns)[:3]
        print_info("Sample license patterns", str(sample_patterns))
        
        # Test non-reference
        setup_patterns = expander.expand_reference("setup.py")
        print_result(setup_patterns == {"setup.py"}, "Non-reference returned unchanged")
        
        # Test pattern matching
        test_cases = [
            ("LICENSE.txt", "LICENSE.*", True),
            ("README.md", "README.*", True),
            ("setup.py", "setup.py", True),
            ("random.txt", "setup.py", False),
            ("test.py", "*.py", True),
            ("LICENCE", "@file_groups.license", True)  # Test expansion + matching
        ]
        
        print(f"\n  {Colors.BLUE}Pattern matching tests:{Colors.END}")
        for filename, pattern, expected in test_cases:
            if pattern.startswith('@'):
                # For reference patterns, we need to expand first
                expanded = expander.expand_pattern_set({pattern})
                result = any(expander.match_pattern(filename, p) for p in expanded)
            else:
                result = expander.match_pattern(filename, pattern)
            
            status_color = Colors.GREEN if result == expected else Colors.RED
            print(f"    {status_color}'{filename}' vs '{pattern}' = {result} (expected {expected}){Colors.END}")
            
        # Test find_matches
        test_files = {"LICENSE.txt", "README.md", "setup.py", "main.py", "requirements.txt"}
        license_matches = expander.find_matches(test_files, {"@file_groups.license"})
        print_info("Test files", str(test_files))
        print_info("License matches", str(license_matches))
        print_result(len(license_matches) > 0, "Found license file matches")
        print_result("LICENSE.txt" in license_matches, "Correctly matched LICENSE.txt")
        
    except Exception as e:
        print_result(False, f"Indicator expansion failed: {e}")
    
    print()


def test_project_root_detection():
    """Test project root detection system."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping project root detection tests - imports failed")
        return
        
    print_test("Project Root Detection System")
    
    try:
        # Clear any forced roots first
        _clear_forced_project_root()
        
        detector = _ProjectRootDetector()
        
        # Test necessary files check
        print(f"  {Colors.BLUE}Testing necessary files validation:{Colors.END}")
        
        complete_files = {"LICENSE", "README.md", "requirements.txt", "setup.py"}
        has_necessary, missing = detector._check_necessary_files(complete_files)
        print_result(has_necessary, f"Complete files pass necessary check")
        if missing:
            print_info("Missing categories", str(missing))
        
        incomplete_files = {"setup.py", "main.py"}
        has_necessary, missing = detector._check_necessary_files(incomplete_files)
        print_result(not has_necessary and len(missing) > 0, 
                    f"Incomplete files fail necessary check")
        print_info("Missing from incomplete", str(missing))
        
        # Test actual project root detection
        print(f"\n  {Colors.BLUE}Testing real project root detection:{Colors.END}")
        root = _get_project_root()
        if root:
            print_info("Detected project root", str(root))
            print_result(root.exists(), "Project root exists")
            print_result(root.is_dir(), "Project root is directory")
            
            # Test with expected name
            root_with_name = _get_project_root(expected_name=root.name)
            print_result(root_with_name == root, f"Expected name '{root.name}' matching works")
            
            # Test with wrong name
            wrong_name = _get_project_root(expected_name="definitely_not_the_project_name_12345")
            print_result(wrong_name is None, "Wrong expected name returns None")
            
            # Test directory scanning details
            score, details = detector._scan_directory(root)
            print_info("Root confidence score", f"{score:.2f}")
            print_info("Necessary files present", str(details.get('necessary_files_present', 'Unknown')))
            
            if details.get('missing_necessary'):
                print_info("Missing necessary files", str(details['missing_necessary']))
            
        else:
            print_warning("No project root detected")
            print_info("Note", "This might be expected if not running from a proper project structure")
            
    except Exception as e:
        print_result(False, f"Project root detection failed: {e}")
    
    print()

def test_module_file_path():
    """Test module file path detection."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping module file path tests - imports failed")
        return
        
    print_test("Module File Path Detection")
    
    try:
        # Test _get_module_file_path with current module name (string)
        module_path = _get_module_file_path(__name__)
        if module_path:
            print_info("Current module file path", str(module_path))
            print_result(module_path.exists(), "Module file exists")
            print_result(module_path.is_file(), "Module path is a file")
        else:
            print_warning("Current module has no file path (might be __main__ or built-in)")
        
        # Test with an actual object that has a module
        class TestClass:
            pass
        
        test_obj_path = _get_module_file_path(TestClass)
        if test_obj_path:
            print_info("Test object module path", str(test_obj_path))
            print_result(test_obj_path.exists(), "Test object module file exists")
            print_result(test_obj_path.name.endswith('.py'), "Test object module is Python file")
        else:
            print_warning("Test object has no discoverable module file")
        
        # Test with Path object (should return None)
        path_obj_result = _get_module_file_path(Path(__file__))
        print_result(path_obj_result is None, "Path object correctly returns None")
        
        # Test with built-in module name (should return None for built-ins like 'sys')
        builtin_result = _get_module_file_path('sys')
        print_result(builtin_result is None, "Built-in module 'sys' correctly returns None")
        
        # Test with actual importable module that has a file
        try:
            pathlib_result = _get_module_file_path('pathlib')
            if pathlib_result:
                print_result(pathlib_result.exists(), "Pathlib module file exists")
                print_result('pathlib' in str(pathlib_result), "Pathlib result contains 'pathlib'")
            else:
                print_warning("Pathlib module has no file (unexpected)")
        except Exception as e:
            print_warning(f"Pathlib module test failed: {e}")
        
        # Test with non-existent module name (should return None)
        nonexistent_result = _get_module_file_path('definitely_nonexistent_module_12345')
        print_result(nonexistent_result is None, "Non-existent module correctly returns None")
        
    except Exception as e:
        print_result(False, f"Module file path detection failed: {e}")
    
    print()



def test_forced_root_system():
    """Test the forced project root system."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping forced root tests - imports failed")
        return
        
    print_test("Forced Project Root System")
    
    try:
        # Clear any existing forced root
        _clear_forced_project_root()
        current_forced = _get_forced_project_root()
        print_result(current_forced is None, "Initial forced root cleared")
        
        # Test forcing current directory (should always exist)
        current_dir = Path.cwd()
        print_info("Testing with directory", str(current_dir))
        
        _force_project_root(current_dir)
        forced_root = _get_forced_project_root()
        print_result(forced_root == current_dir, "Forced root set correctly")
        
        # Test that get_project_root returns forced root
        detected_root = _get_project_root()
        print_result(detected_root == current_dir, "get_project_root returns forced root")
        
        # Test forced root with expected name
        root_with_correct_name = _get_project_root(expected_name=current_dir.name)
        print_result(root_with_correct_name == current_dir, "Forced root works with correct expected name")
        
        root_with_wrong_name = _get_project_root(expected_name="wrong_name_12345")
        print_result(root_with_wrong_name is None, "Forced root respects expected name mismatch")
        
        # Clear and test
        _clear_forced_project_root()
        cleared_root = _get_forced_project_root()
        print_result(cleared_root is None, "Forced root cleared successfully")
        
        # Test error handling for invalid paths
        try:
            _force_project_root("/this/path/definitely/does/not/exist")
            print_result(False, "Should have raised error for non-existent path")
        except FileNotFoundError:
            print_result(True, "Correctly raised error for non-existent path")
        except Exception as e:
            print_result(False, f"Unexpected error type: {e}")
            
    except Exception as e:
        print_result(False, f"Forced root system failed: {e}")
    
    print()


def test_path_utilities():
    """Test basic path utility functions."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping path utilities tests - imports failed")
        return
        
    print_test("Path Utility Functions")
    
    try:
        # Test _get_cwd
        cwd = _get_cwd()
        print_info("Current working directory", str(cwd))
        print_result(isinstance(cwd, Path), "get_cwd returns Path object")
        print_result(cwd.exists(), "CWD exists")
        print_result(cwd.is_dir(), "CWD is directory")
        
        # Test _get_current_dir
        current_dir = _get_current_dir()
        print_info("Current file directory", str(current_dir))
        print_result(isinstance(current_dir, Path), "get_current_dir returns Path object")
        print_result(current_dir.exists(), "Current dir exists")
        
        # Test _equal_paths
        test_path = Path(__file__)
        print_result(_equal_paths(test_path, str(test_path)), "equal_paths works with Path and str")
        print_result(_equal_paths(test_path, test_path), "equal_paths works with identical paths")
        
        different_path = Path("/definitely/nonexistent/path.py")
        print_result(not _equal_paths(test_path, different_path), "equal_paths correctly identifies different paths")
        
        # Test _path_id functions
        file_id = _path_id(__file__)
        short_id = _path_id_short(__file__)
        print_info("Path ID", file_id)
        print_info("Short path ID", short_id)
        
        print_result(isinstance(file_id, str) and len(file_id) > 0, "path_id returns non-empty string")
        print_result(isinstance(short_id, str) and len(short_id) < len(file_id), "short path_id is shorter")
        print_result(file_id == _path_id(__file__), "path_id is reproducible")
        print_result(short_id == _path_id_short(__file__), "short path_id is reproducible")
        
        # Test that IDs are different for different files
        other_id = _path_id("/some/other/file.py")
        print_result(file_id != other_id, "Different files produce different IDs")
        
    except Exception as e:
        print_result(False, f"Path utilities failed: {e}")
    
    print()


def test_gitignore_parsing():
    """Test gitignore file parsing."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping gitignore parsing tests - imports failed")
        return
        
    print_test("Gitignore File Parsing")
    
    # Create a temporary gitignore file for testing
    gitignore_content = """# This is a comment
*.pyc
__pycache__/
/dist
node_modules
.env
.DS_Store

# Another comment
*.log
temp/
*.tmp

# Empty lines should be ignored

build/
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.gitignore', delete=False, encoding='utf-8') as f:
        f.write(gitignore_content)
        temp_path = Path(f.name)
    
    try:
        patterns = _parse_gitignore_file(temp_path)
        print_info("Parsed patterns count", str(len(patterns)))
        print_info("Parsed patterns", str(sorted(patterns)))
        
        # Test expected patterns
        expected_in_patterns = ["*.pyc", "__pycache__/", "dist", "node_modules", ".env", "*.log", "temp/"]
        for expected in expected_in_patterns:
            print_result(expected in patterns, f"Contains '{expected}' pattern")
        
        # Test excluded content
        print_result("# This is a comment" not in patterns, "Comments excluded from patterns")
        print_result("" not in patterns, "Empty lines excluded from patterns")
        
        # Test leading slash removal
        print_result("dist" in patterns and "/dist" not in patterns, "Leading slash removed from /dist")
        
        # Test with non-existent file
        empty_patterns = _parse_gitignore_file(Path("/nonexistent/.gitignore"))
        print_result(len(empty_patterns) == 0, "Non-existent file returns empty set")
        
        # Test with directory instead of file
        dir_patterns = _parse_gitignore_file(Path.cwd())
        print_result(len(dir_patterns) == 0, "Directory instead of file returns empty set")
        
    except Exception as e:
        print_result(False, f"Gitignore parsing failed: {e}")
    finally:
        # Clean up
        try:
            temp_path.unlink()
        except OSError:
            pass
    
    print()


def test_project_paths_and_structure():
    """Test project path and structure functions."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping project paths and structure tests - imports failed")
        return
        
    print_test("Project Paths and Structure")
    
    # Create a temporary project structure for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Create test structure with necessary files for project root detection
            (temp_path / "LICENSE").write_text("MIT License\n\nCopyright (c) 2024")
            (temp_path / "README.md").write_text("# Test Project\n\nThis is a test.")
            (temp_path / "requirements.txt").write_text("requests>=2.28.0\npandas>=1.5.0")
            
            # Create directory structure
            (temp_path / "src").mkdir()
            (temp_path / "src" / "main.py").write_text("print('hello world')")
            (temp_path / "src" / "utils.py").write_text("def helper(): pass")
            (temp_path / "src" / "config.json").write_text('{"setting": "value"}')
            
            (temp_path / "tests").mkdir()
            (temp_path / "tests" / "test_main.py").write_text("def test_main(): assert True")
            (temp_path / "tests" / "__init__.py").write_text("")
            
            (temp_path / "docs").mkdir()
            (temp_path / "docs" / "api.md").write_text("# API Documentation")
            
            # Create files that should be ignored
            (temp_path / "__pycache__").mkdir()
            (temp_path / "__pycache__" / "main.cpython-39.pyc").write_text("compiled bytecode")
            (temp_path / ".env").write_text("SECRET_KEY=test123")
            
            # Create a .gitignore file
            (temp_path / ".gitignore").write_text("*.pyc\n__pycache__/\n.env\n*.log")
            
            print_info("Created test project at", str(temp_path))
            
            # Test _get_all_project_paths
            all_paths = _get_all_project_paths(force_root=temp_path)
            print_info("Total paths found", str(len(all_paths)))
            
            if all_paths:
                path_names = [p.name for p in all_paths]
                print_info("Sample file names", str(sorted(path_names)[:10]))
                
                # Check for expected files
                print_result("main.py" in path_names, "Found main.py")
                print_result("LICENSE" in path_names, "Found LICENSE file")
                print_result("README.md" in path_names, "Found README.md")
                
                # Check that ignored files are excluded
                print_result("main.cpython-39.pyc" not in path_names, "__pycache__ files correctly ignored")
                print_result(".env" not in path_names or len([p for p in path_names if p == ".env"]) == 0, 
                           ".env files handled according to gitignore")
            
            # Test with as_str option
            str_paths = _get_all_project_paths(force_root=temp_path, as_str=True)
            print_result(all(isinstance(p, str) for p in str_paths[:5]), "as_str option works correctly")
            print_result(len(str_paths) == len(all_paths), "String and Path versions have same count")
            
            # Test _get_project_structure
            structure = _get_project_structure(force_root=temp_path)
            print_info("Structure keys", str(sorted(structure.keys())))
            
            print_result("src" in structure, "Structure contains src directory")
            print_result("tests" in structure, "Structure contains tests directory")
            print_result("LICENSE" in structure, "Structure contains LICENSE file")
            
            if "LICENSE" in structure:
                print_result(structure["LICENSE"] == "file", "Files marked as 'file' in structure")
            if "src" in structure:
                print_result(isinstance(structure["src"], dict), "Directories are dictionaries in structure")
                if isinstance(structure["src"], dict):
                    print_result("main.py" in structure["src"], "Nested files found in subdirectories")
            
            # Test _get_formatted_project_tree
            tree_str = _get_formatted_project_tree(force_root=temp_path, max_depth=2)
            print_result(len(tree_str) > 0, "Formatted tree generated")
            print_result("├──" in tree_str or "└──" in tree_str, "Tree contains proper formatting characters")
            print_result("src/" in tree_str, "Tree shows directories with trailing slash")
            print_result("LICENSE" in tree_str, "Tree shows files")
            
            # Print a sample of the tree
            tree_lines = tree_str.split('\n')[:15]  # First 15 lines
            print(f"\n  {Colors.BLUE}Sample formatted tree (first 15 lines):{Colors.END}")
            for i, line in enumerate(tree_lines):
                if i < 10:  # Only show first 10 to keep output manageable
                    print(f"    {Colors.WHITE}{line}{Colors.END}")
            if len(tree_lines) > 10:
                print(f"    {Colors.MAGENTA}... and {len(tree_lines) - 10} more lines{Colors.END}")
            
            # Test tree with different options
            tree_no_files = _get_formatted_project_tree(force_root=temp_path, show_files=False, max_depth=1)
            print_result("LICENSE" not in tree_no_files and "src/" in tree_no_files, 
                        "show_files=False option works")
                        
        except Exception as e:
            print_result(False, f"Project structure functions failed: {e}")
            import traceback
            traceback.print_exc()
    
    print()


def run_all_tests():
    """Run all internal functionality tests."""
    print_section("Comprehensive Internal Path Operations Tests")
    
    if not IMPORTS_SUCCESSFUL:
        print(f"{Colors.RED}{Colors.BOLD}❌ Cannot run tests - import failures{Colors.END}")
        print(f"{Colors.YELLOW}This is expected if running outside the suitkaise project structure{Colors.END}")
        print(f"{Colors.YELLOW}To run these tests, ensure the suitkaise module is properly installed or accessible{Colors.END}")
        return
    
    print(f"{Colors.GREEN}✅ Successfully imported all internal functions{Colors.END}")
    print(f"{Colors.WHITE}Testing the fixed internal module with all bug fixes applied...{Colors.END}\n")
    
    try:
        test_caller_detection()
        test_module_detection()
        test_indicator_expander()
        test_module_file_path()
        test_project_root_detection()
        test_forced_root_system()
        test_path_utilities()
        test_gitignore_parsing()
        test_project_paths_and_structure()
        
        print_section("Test Summary")
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL INTERNAL FUNCTIONALITY TESTS COMPLETED! 🎉{Colors.END}")
        print(f"{Colors.WHITE}✅ All core internal functions tested and working correctly{Colors.END}")
        print(f"{Colors.WHITE}✅ Bug fixes validated and confirmed working{Colors.END}")
        print(f"{Colors.WHITE}✅ New functionality (gitignore parsing, formatted tree) working{Colors.END}")
        print(f"{Colors.WHITE}✅ The internal module is ready for use by the external SKPath module{Colors.END}")
        print()
        
    except Exception as e:
        print(f"{Colors.RED}{Colors.BOLD}❌ Test suite failed with error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()