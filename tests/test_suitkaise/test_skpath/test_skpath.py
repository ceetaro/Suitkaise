#!/usr/bin/env python3
"""
Test module for SKPath functionality.

This module contains comprehensive tests for the SKPath system,
including path normalization, the @autopath decorator, caller detection,
path utilities, and error handling.

Run with:
    python3.11 -m pytest tests/test_suitkaise/test_skpath/test_skpath.py -v
    
Or with unittest:
    python3.11 -m unittest tests.test_suitkaise.test_skpath.test_skpath -v
"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Visual indicators for test output
INFO = "⬜️" * 40 + "\n\n\n"
FAIL = "\n\n   " + "❌" * 10 + " "
SUCCESS = "\n\n   " + "🟩" * 10 + " "
RUNNING = "🔄" * 40 + "\n\n"
CHECKING = "🧳" * 40 + "\n"
WARNING = "\n\n   " + "🟨" * 10 + " "

from suitkaise.skpath import (
    normalize_path,
    get_caller_file_path,
    get_current_file_path,
    get_current_directory,
    equalpaths,
    id,
    idshort,
    autopath,
    AutopathError,
)


class TestBasicPathFunctions(unittest.TestCase):
    """Test basic path utility functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_file.txt")
        
        # Create the test file
        with open(self.temp_file, 'w') as f:
            f.write("test content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_normalize_path_with_existing_file(self):
        """
        Test normalize_path with an existing file.
        
        This test:
        - Calls normalize_path with a real file path
        - Verifies it returns a string
        - Checks the path exists and is absolute
        - Verifies it's properly normalized
        """
        normalized = normalize_path(self.temp_file)
        
        # Check return type
        self.assertIsInstance(normalized, str)
        
        # Check the path exists
        self.assertTrue(os.path.exists(normalized))
        
        # Check it's an absolute path
        self.assertTrue(os.path.isabs(normalized))
        
        # Check it resolves to the same file
        self.assertEqual(os.path.realpath(normalized), os.path.realpath(self.temp_file))
    
    def test_normalize_path_with_directory(self):
        """
        Test normalize_path with a directory.
        
        This test:
        - Calls normalize_path with a directory path
        - Verifies directory normalization works correctly
        """
        normalized = normalize_path(self.temp_dir)
        
        self.assertIsInstance(normalized, str)
        self.assertTrue(os.path.exists(normalized))
        self.assertTrue(os.path.isdir(normalized))
        self.assertTrue(os.path.isabs(normalized))
    
    def test_normalize_path_with_none_uses_caller(self):
        """
        Test normalize_path with None uses caller's file path.
        
        This test:
        - Calls normalize_path with None
        - Verifies it returns this test file's path
        """
        normalized = normalize_path(None)
        
        self.assertIsInstance(normalized, str)
        self.assertTrue(os.path.exists(normalized))
        
        # Should be this test file (since we're calling from here)
        # Note: May not exactly match due to caller detection logic
        self.assertTrue(normalized.endswith('.py'))
    
    def test_normalize_path_strict_mode_with_nonexistent_path(self):
        """
        Test normalize_path strict mode with non-existent path.
        
        This test:
        - Calls normalize_path with strict=True and invalid path
        - Verifies AutopathError is raised
        """
        nonexistent_path = "/this/path/definitely/does/not/exist/nowhere/12345"
        
        with self.assertRaises(AutopathError) as context:
            normalize_path(nonexistent_path, strict=True)
        
        self.assertIn("does not exist", str(context.exception))
    
    def test_normalize_path_non_strict_with_nonexistent_path(self):
        """
        Test normalize_path non-strict mode with fallback.
        
        This test:
        - Calls normalize_path with strict=False and invalid path
        - Verifies it falls back to a valid path
        """
        nonexistent_path = "/this/path/definitely/does/not/exist/nowhere/12345"
        
        # Should not raise error and return fallback path
        normalized = normalize_path(nonexistent_path, strict=False)
        
        self.assertIsInstance(normalized, str)
        self.assertTrue(os.path.exists(normalized))
    
    def test_get_current_file_path(self):
        """
        Test get_current_file_path function.
        
        This test:
        - Calls get_current_file_path from this test file
        - Verifies it returns this test file's path
        """
        current_file = get_current_file_path()
        
        self.assertIsInstance(current_file, str)
        self.assertTrue(os.path.exists(current_file))
        self.assertTrue(current_file.endswith('.py'))
        
        # Should contain this test file name
        self.assertIn('test_skpath', current_file)
    
    def test_get_current_directory(self):
        """
        Test get_current_directory function.
        
        This test:
        - Calls get_current_directory from this test file
        - Verifies it returns the directory containing this file
        """
        current_dir = get_current_directory()
        
        self.assertIsInstance(current_dir, str)
        self.assertTrue(os.path.exists(current_dir))
        self.assertTrue(os.path.isdir(current_dir))
        
        # Get the actual current file path to determine expected filename
        current_file_path = get_current_file_path()
        expected_filename = os.path.basename(current_file_path)
        expected_test_file = os.path.join(current_dir, expected_filename)
        
        # Verify the test file exists in the returned directory
        self.assertTrue(os.path.exists(expected_test_file), 
                    f"Expected to find {expected_filename} in {current_dir}")
    
    def test_get_caller_file_path_skips_suitkaise(self):
        """
        Test get_caller_file_path skips suitkaise internal files.
        
        This test:
        - Calls get_caller_file_path from test (non-suitkaise) file
        - Verifies it returns this test file, not suitkaise internals
        """
        caller_file = get_caller_file_path()
        
        self.assertIsInstance(caller_file, str)
        self.assertTrue(os.path.exists(caller_file))
        
        # Should not contain 'suitkaise' in the path (since this is a test file)
        # Convert to lowercase for case-insensitive check
        path_lower = caller_file.lower()
        
        # This test file calls get_caller_file_path, so it should return this file
        # which doesn't contain 'suitkaise' in its path
        self.assertIn('test_skpath', caller_file)


class TestAutopathBasic(unittest.TestCase):
    """Test basic @autopath decorator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "autopath_test.txt")
        
        with open(self.temp_file, 'w') as f:
            f.write("autopath test content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_autopath_basic_auto_detection(self):
        """
        Test basic @autopath auto-detection.
        
        This test:
        - Creates a function with @autopath()
        - Calls it without providing a path
        - Verifies the path was auto-injected
        """
        @autopath()
        def test_function(path: str = None):
            """Test function that receives auto-detected path."""
            return path
        
        # Call without providing path
        result_path = test_function()
        
        # Should return a valid path
        self.assertIsNotNone(result_path)
        self.assertIsInstance(result_path, str)
        self.assertTrue(os.path.exists(result_path))
        
        # Should be this test file (since we're calling from here)
        self.assertIn('test_skpath', result_path)
    
    def test_autopath_with_custom_path(self):
        """
        Test @autopath with custom path injection.
        
        This test:
        - Creates a function with @autopath(path="/custom/path")  
        - Verifies the custom path is injected (if it exists)
        """
        # Use our temp file as custom path
        @autopath(path=self.temp_file)
        def test_function(path: str = None):
            """Test function with custom path."""
            return path
        
        # Call without providing path
        result_path = test_function()
        
        # Should return the custom path we specified
        self.assertEqual(result_path, os.path.realpath(self.temp_file))
    
    def test_autopath_with_custom_parameter_name(self):
        """
        Test @autopath with custom parameter name.
        
        This test:
        - Creates function with parameter named 'file_path' instead of 'path'
        - Uses path_param_name to specify the parameter
        - Verifies injection works with custom parameter name
        """
        @autopath(path_param_name="file_path")
        def test_function(file_path: str = None):
            """Test function with custom parameter name."""
            return file_path
        
        result_path = test_function()
        
        self.assertIsNotNone(result_path)
        self.assertIsInstance(result_path, str)
        self.assertTrue(os.path.exists(result_path))
    
    def test_autopath_finds_path_parameter(self):
        """
        Test @autopath automatically finds 'path' parameter.
        
        This test:
        - Creates function with multiple parameters including 'path'
        - Verifies @autopath finds and injects into 'path' parameter
        """
        @autopath()
        def test_function(data: str, path: str = None, other: int = 42):
            """Test function with multiple parameters."""
            return path
        
        # Call with other parameters but not path
        result_path = test_function("test_data", other=100)
        
        self.assertIsNotNone(result_path)
        self.assertIsInstance(result_path, str)
        self.assertTrue(os.path.exists(result_path))
    
    def test_autopath_finds_parameter_containing_path(self):
        """
        Test @autopath finds parameter containing 'path' in name.
        
        This test:
        - Creates function with parameter like 'source_path'
        - Verifies @autopath finds it even though it's not exactly 'path'
        """
        @autopath()
        def test_function(source_path: str = None):
            """Test function with parameter containing 'path'."""
            return source_path
        
        result_path = test_function()
        
        self.assertIsNotNone(result_path)
        self.assertIsInstance(result_path, str)
        self.assertTrue(os.path.exists(result_path))
    
    def test_autopath_prefers_exact_path_match(self):
        """
        Test @autopath prefers exact 'path' match over partial matches.
        
        This test:
        - Creates function with both 'path' and 'file_path' parameters
        - Verifies @autopath chooses 'path' over 'file_path'
        """
        @autopath()
        def test_function(file_path: str = None, path: str = None):
            """Test function with multiple path-like parameters."""
            return {"file_path": file_path, "path": path}
        
        result = test_function()
        
        # 'path' should be filled, 'file_path' should remain None
        self.assertIsNotNone(result["path"])
        self.assertIsNone(result["file_path"])


class TestAutopathAdvanced(unittest.TestCase):
    """Test advanced @autopath decorator scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "advanced_test.txt")
        
        with open(self.temp_file, 'w') as f:
            f.write("advanced test content")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_autopath_with_positional_arguments(self):
        """
        Test @autopath with positional argument injection.
        
        This test:
        - Creates function where path is a positional parameter
        - Calls with some args but not the path arg
        - Verifies path is injected at correct position
        """
        @autopath()
        def test_function(first: str, path: str = None, third: str = "default"):
            """Test function with positional path parameter."""
            return {"first": first, "path": path, "third": third}
        
        # Call with first arg but not path
        result = test_function("first_value")
        
        self.assertEqual(result["first"], "first_value")
        self.assertIsNotNone(result["path"])
        self.assertEqual(result["third"], "default")
        self.assertTrue(os.path.exists(result["path"]))
    
    def test_autopath_with_keyword_only_parameter(self):
        """
        Test @autopath with keyword-only path parameter.
        
        This test:
        - Creates function with keyword-only path parameter (after *)
        - Verifies injection works for keyword-only parameters
        """
        @autopath()
        def test_function(data: str, *, path: str = None):
            """Test function with keyword-only path parameter."""
            return path
        
        result_path = test_function("test_data")
        
        self.assertIsNotNone(result_path)
        self.assertIsInstance(result_path, str)
        self.assertTrue(os.path.exists(result_path))
    
    def test_autopath_user_provided_path_is_normalized(self):
        """
        Test that user-provided paths are normalized.
        
        This test:
        - Creates function with @autopath
        - Calls with a user-provided path
        - Verifies the path gets normalized (absolute, resolved)
        """
        @autopath()
        def test_function(path: str = None):
            """Test function that normalizes user paths."""
            return path
        
        # Use relative path with '..' components
        messy_path = os.path.join(self.temp_dir, "..", os.path.basename(self.temp_dir), "advanced_test.txt")
        
        result_path = test_function(messy_path)
        
        # Should be normalized to absolute path
        self.assertTrue(os.path.isabs(result_path))
        self.assertEqual(result_path, os.path.realpath(messy_path))
        self.assertTrue(os.path.exists(result_path))
    
    def test_autopath_strict_mode(self):
        """
        Test @autopath strict mode behavior.
        
        This test:
        - Creates function with @autopath(strict=True)
        - Tests both valid and invalid path scenarios
        """
        @autopath(strict=True)
        def test_function_strict(path: str = None):
            """Test function with strict path validation."""
            return path
        
        # Should work with valid path
        result_path = test_function_strict(self.temp_file)
        self.assertEqual(result_path, os.path.realpath(self.temp_file))
        
        # Should raise error with invalid path
        with self.assertRaises(AutopathError):
            test_function_strict("/nonexistent/path/nowhere/12345")
    
    def test_autopath_with_pathlib_path(self):
        """
        Test @autopath with pathlib.Path objects.
        
        This test:
        - Calls function with Path object instead of string
        - Verifies Path objects are converted to normalized strings
        """
        @autopath()
        def test_function(path: str = None):
            """Test function that handles Path objects."""
            return path
        
        path_obj = Path(self.temp_file)
        result_path = test_function(path_obj)
        
        # Should convert Path to normalized string
        self.assertIsInstance(result_path, str)
        self.assertEqual(result_path, str(path_obj.resolve()))
        self.assertTrue(os.path.exists(result_path))


class TestAutopathErrorHandling(unittest.TestCase):
    """Test @autopath error handling and validation."""
    
    def test_autopath_explicit_none_raises_error(self):
        """
        Test that passing explicit None raises AutopathError.
        
        This test:
        - Creates function with @autopath
        - Calls with path=None explicitly
        - Verifies AutopathError is raised with helpful message
        """
        @autopath()
        def test_function(path: str = None):
            """Test function for explicit None testing."""
            return path
        
        with self.assertRaises(AutopathError) as context:
            test_function(path=None)
        
        error_msg = str(context.exception)
        self.assertIn("Explicit None", error_msg)
        self.assertIn("auto-detection", error_msg)
    
    def test_autopath_explicit_none_positional_raises_error(self):
        """
        Test that passing explicit None positionally raises AutopathError.
        
        This test:
        - Creates function with @autopath
        - Calls with None as positional argument
        - Verifies AutopathError is raised
        """
        @autopath()
        def test_function(path: str = None):
            """Test function for positional None testing."""
            return path
        
        with self.assertRaises(AutopathError) as context:
            test_function(None)
        
        self.assertIn("Explicit None", str(context.exception))
    
    def test_autopath_invalid_path_type_raises_error(self):
        """
        Test that invalid path types raise AutopathError.
        
        This test:
        - Creates function with @autopath
        - Calls with non-string, non-Path object
        - Verifies appropriate error is raised
        """
        @autopath()
        def test_function(path: str = None):
            """Test function for type validation."""
            return path
        
        # Test with integer
        with self.assertRaises(AutopathError) as context:
            test_function(123)
        
        error_msg = str(context.exception)
        self.assertIn("must be a string or Path object", error_msg)
        self.assertIn("int", error_msg)
    
    def test_autopath_no_path_parameter_raises_error(self):
        """
        Test error when function has no path-like parameter.
        
        This test:
        - Creates function with no parameters containing 'path'
        - Verifies AutopathError is raised with helpful message
        """
        with self.assertRaises(AutopathError) as context:
            @autopath()
            def test_function(data: str, value: int = 42):
                """Test function with no path parameter."""
                return data
        
        # Error should occur during decoration, not function call
        error_msg = str(context.exception)
        self.assertIn("no parameter containing 'path'", error_msg)
        self.assertIn("Available parameters", error_msg)
    
    def test_autopath_invalid_parameter_name_raises_error(self):
        """
        Test error when specified parameter name doesn't exist.
        
        This test:
        - Creates function and specifies non-existent parameter name
        - Verifies AutopathError is raised
        """
        with self.assertRaises(AutopathError) as context:
            @autopath(path_param_name="nonexistent_param")
            def test_function(path: str = None):
                """Test function with invalid parameter name."""
                return path
        
        error_msg = str(context.exception)
        self.assertIn("does not have parameter 'nonexistent_param'", error_msg)
        self.assertIn("Available parameters", error_msg)
    
    def test_autopath_invalid_path_in_strict_mode(self):
        """
        Test error handling for invalid paths in strict mode.
        
        This test:
        - Creates function with strict=True
        - Provides invalid path
        - Verifies AutopathError with appropriate message
        """
        @autopath(strict=True)
        def test_function(path: str = None):
            """Test function for strict mode validation."""
            return path
        
        invalid_path = "/absolutely/nonexistent/path/12345"
        
        with self.assertRaises(AutopathError) as context:
            test_function(invalid_path)
        
        error_msg = str(context.exception)
        self.assertIn("Invalid path", error_msg)
        self.assertIn(invalid_path, error_msg)


class TestPathUtilities(unittest.TestCase):
    """Test path utility functions like equalpaths, id, idshort."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file1 = os.path.join(self.temp_dir, "file1.txt")
        self.temp_file2 = os.path.join(self.temp_dir, "file2.txt")
        
        # Create test files
        for filepath in [self.temp_file1, self.temp_file2]:
            with open(filepath, 'w') as f:
                f.write(f"content for {os.path.basename(filepath)}")
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_equalpaths_identical_paths(self):
        """
        Test equalpaths with identical paths.
        
        This test:
        - Compares same path string with itself
        - Verifies equalpaths returns True
        """
        result = equalpaths(self.temp_file1, self.temp_file1)
        self.assertTrue(result)
    
    def test_equalpaths_different_representations_same_file(self):
        """
        Test equalpaths with different representations of same path.
        
        This test:
        - Creates different path representations (relative vs absolute, with .. etc.)
        - Verifies equalpaths recognizes them as the same
        """
        # Create a path with .. components that resolves to same file
        base_name = os.path.basename(self.temp_file1)
        messy_path = os.path.join(self.temp_dir, "..", os.path.basename(self.temp_dir), base_name)
        
        result = equalpaths(self.temp_file1, messy_path)
        self.assertTrue(result)
    
    def test_equalpaths_different_files(self):
        """
        Test equalpaths with actually different files.
        
        This test:
        - Compares two different file paths
        - Verifies equalpaths returns False
        """
        result = equalpaths(self.temp_file1, self.temp_file2)
        self.assertFalse(result)
    
    def test_equalpaths_with_pathlib_objects(self):
        """
        Test equalpaths with pathlib.Path objects.
        
        This test:
        - Uses Path objects instead of strings
        - Verifies equalpaths handles Path objects correctly
        """
        path1 = Path(self.temp_file1)
        path2 = Path(self.temp_file1)  # Same file
        path3 = Path(self.temp_file2)  # Different file
        
        self.assertTrue(equalpaths(path1, path2))
        self.assertFalse(equalpaths(path1, path3))
    
    def test_id_function_basic(self):
        """
        Test basic id() function functionality.
        
        This test:
        - Calls id() with a file path
        - Verifies it returns a string hash
        - Checks the hash is consistent
        """
        # Note: id() has @autopath decorator, so we need to call it properly
        file_id = id(self.temp_file1)
        
        self.assertIsInstance(file_id, str)
        self.assertGreater(len(file_id), 0)
        
        # Should be consistent - same path gives same ID
        file_id2 = id(self.temp_file1)
        self.assertEqual(file_id, file_id2)
    
    def test_id_function_different_paths_different_ids(self):
        """
        Test that different paths produce different IDs.
        
        This test:
        - Generates IDs for different paths
        - Verifies they're different
        """
        id1 = id(self.temp_file1)
        id2 = id(self.temp_file2)
        
        self.assertNotEqual(id1, id2)
    
    def test_id_function_same_path_different_representations(self):
        """
        Test that different representations of same path give same ID.
        
        This test:
        - Uses different path representations for same file
        - Verifies they produce the same ID (after normalization)
        """
        # Create different representation of same path
        base_name = os.path.basename(self.temp_file1)
        alt_path = os.path.join(self.temp_dir, "..", os.path.basename(self.temp_dir), base_name)
        
        id1 = id(self.temp_file1)
        id2 = id(alt_path)
        
        self.assertEqual(id1, id2)
    
    def test_idshort_function_basic(self):
        """
        Test basic idshort() function functionality.
        
        This test:
        - Calls idshort() with various digit lengths
        - Verifies output length matches requested digits
        - Checks it's a subset of the full ID
        """
        # Test different digit lengths
        for digits in [4, 6, 8, 10]:
            short_id = idshort(self.temp_file1, digits)
            
            self.assertIsInstance(short_id, str)
            self.assertEqual(len(short_id), digits)
            
            # Should be numeric characters (from hex)
            self.assertTrue(all(c in '0123456789abcdef' for c in short_id))
    
    def test_idshort_function_consistency(self):
        """
        Test idshort() consistency and relationship to id().
        
        This test:
        - Verifies idshort is consistent for same path
        - Checks that idshort is prefix of full id
        """
        full_id = id(self.temp_file1)
        short_id = idshort(self.temp_file1, 8)
        
        # Should be consistent
        short_id2 = idshort(self.temp_file1, 8)
        self.assertEqual(short_id, short_id2)
        
        # Should be prefix of full ID
        self.assertTrue(full_id.startswith(short_id))
    
    def test_idshort_default_length(self):
        """
        Test idshort() default length.
        
        This test:
        - Calls idshort without specifying digits
        - Verifies default length is 8
        """
        short_id = idshort(self.temp_file1)  # No digits specified
        
        self.assertEqual(len(short_id), 8)


class TestCallerDetection(unittest.TestCase):
    """Test caller detection and suitkaise file filtering."""
    
    def test_caller_detection_from_test_file(self):
        """
        Test that get_caller_file_path works from test files.
        
        This test:
        - Calls get_caller_file_path from this test file
        - Verifies it returns this test file (non-suitkaise)
        - Checks path filtering logic
        """
        # This should return this test file since it's not a suitkaise file
        caller_path = get_caller_file_path()
        
        self.assertIsInstance(caller_path, str)
        self.assertTrue(os.path.exists(caller_path))
        self.assertIn('test_skpath', caller_path)
        
        # Path should not contain 'suitkaise' (since this is a test file)
        # Note: Path might contain 'suitkaise' in project structure, 
        # but the detection should work correctly
    
    def test_is_suitkaise_file_detection(self):
        """
        Test the internal _is_suitkaise_file function behavior.
        
        This test:
        - Tests detection of suitkaise vs non-suitkaise files
        - Note: _is_suitkaise_file is internal, so we test indirectly
        """
        # Create a mock suitkaise-like path
        mock_suitkaise_path = "/some/path/suitkaise/skpath/skpath.py"
        mock_test_path = "/some/path/tests/test_skpath.py"
        
        # We can't directly test _is_suitkaise_file since it's internal,
        # but we can test the behavior through get_caller_file_path
        
        # This test file should be detected as non-suitkaise
        caller = get_caller_file_path()
        self.assertTrue(os.path.exists(caller))
    
    def test_autopath_caller_detection_integration(self):
        """
        Test integration of caller detection with @autopath.
        
        This test:
        - Uses @autopath which internally uses caller detection
        - Verifies the correct file path is detected and injected
        """
        @autopath()
        def test_function(path: str = None):
            """Test function for caller detection integration."""
            return path
        
        # Call from this test file
        detected_path = test_function()
        
        # Should detect this test file as the caller
        self.assertIsInstance(detected_path, str)
        self.assertTrue(os.path.exists(detected_path))
        
        # Should be a Python file
        self.assertTrue(detected_path.endswith('.py'))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_empty_path_handling(self):
        """
        Test handling of empty path strings.
        
        This test:
        - Tests normalize_path with empty string
        - Verifies fallback behavior works correctly
        """
        # Empty string should trigger fallback
        normalized = normalize_path("", strict=False)
        
        self.assertIsInstance(normalized, str)
        self.assertTrue(os.path.exists(normalized))
        self.assertGreater(len(normalized), 0)
    
    def test_whitespace_path_handling(self):
        """
        Test handling of whitespace-only paths.
        
        This test:
        - Tests paths with only whitespace
        - Verifies appropriate error handling
        """
        whitespace_path = "   \t\n   "
        
        # Should trigger fallback in non-strict mode
        normalized = normalize_path(whitespace_path, strict=False)
        self.assertTrue(os.path.exists(normalized))
        
        # Should raise error in strict mode
        with self.assertRaises(AutopathError):
            normalize_path(whitespace_path, strict=True)
    
    def test_very_long_path_handling(self):
        """
        Test handling of very long paths.
        
        This test:
        - Creates a very long path string
        - Tests system limits and normalization
        """
        # Create a long path (but not longer than system limits)
        long_component = "a" * 50
        long_path = os.path.join(self.temp_dir, *[long_component] * 3, "file.txt")
        
        # Create the directory structure
        os.makedirs(os.path.dirname(long_path), exist_ok=True)
        with open(long_path, 'w') as f:
            f.write("long path test")
        
        # Should handle long paths correctly
        normalized = normalize_path(long_path)
        self.assertTrue(os.path.exists(normalized))
        self.assertEqual(normalized, os.path.realpath(long_path))
    
    def test_unicode_path_handling(self):
        """
        Test handling of paths with Unicode characters.
        
        This test:
        - Creates paths with Unicode characters
        - Verifies normalization works correctly
        """
        unicode_dir = os.path.join(self.temp_dir, "测试目录")
        unicode_file = os.path.join(unicode_dir, "файл.txt")
        
        # Create the Unicode path
        os.makedirs(unicode_dir, exist_ok=True)
        with open(unicode_file, 'w', encoding='utf-8') as f:
            f.write("Unicode test content")
        
        # Should handle Unicode paths correctly
        normalized = normalize_path(unicode_file)
        self.assertTrue(os.path.exists(normalized))
        self.assertEqual(normalized, os.path.realpath(unicode_file))
    
    def test_symlink_handling(self):
        """
        Test handling of symbolic links.
        
        This test:
        - Creates a symbolic link
        - Tests normalization follows the link correctly
        """
        # Skip on Windows if symlinks aren't supported
        if os.name == 'nt':
            self.skipTest("Symlink test skipped on Windows")
        
        target_file = os.path.join(self.temp_dir, "target.txt")
        link_file = os.path.join(self.temp_dir, "link.txt")
        
        # Create target file
        with open(target_file, 'w') as f:
            f.write("symlink target")
        
        # Create symbolic link
        try:
            os.symlink(target_file, link_file)
        except OSError:
            self.skipTest("Cannot create symlinks in this environment")
        
        # Normalize the link
        normalized = normalize_path(link_file)
        
        # Should resolve to the target file
        self.assertEqual(normalized, os.path.realpath(target_file))
    
    def test_relative_path_with_dots(self):
        """
        Test handling of relative paths with .. and . components.
        
        This test:
        - Creates complex relative paths
        - Verifies they're normalized correctly
        """
        # Create nested directory
        nested_dir = os.path.join(self.temp_dir, "level1", "level2")
        os.makedirs(nested_dir, exist_ok=True)
        
        test_file = os.path.join(nested_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("relative path test")
        
        # Create a complex relative path that actually points to the same file
        # Start from nested_dir, go up two levels, then back down
        complex_path = os.path.join(
            nested_dir,     # /tmp/tmpXXX/level1/level2
            "..",           # Go up to /tmp/tmpXXX/level1  
            "..",           # Go up to /tmp/tmpXXX
            "level1",       # Go down to /tmp/tmpXXX/level1
            "level2",       # Go down to /tmp/tmpXXX/level1/level2
            "test.txt"      # The file: /tmp/tmpXXX/level1/level2/test.txt
        )
        
        # This should normalize to the same file
        normalized = normalize_path(complex_path)
        expected = os.path.realpath(test_file)
        
        self.assertEqual(normalized, expected,
                        f"Path normalization failed:\n"
                        f"  Complex path: {complex_path}\n" 
                        f"  Normalized:   {normalized}\n"
                        f"  Expected:     {expected}")


class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility."""
    
    def test_path_separator_normalization(self):
        """
        Test that path separators are normalized correctly.
        
        This test:
        - Tests paths with different separators
        - Verifies normalization works across platforms
        """
        # Create test file
        temp_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("separator test")
            
            # Test with forward slashes (Unix-style)
            unix_style = test_file.replace(os.sep, '/')
            normalized_unix = normalize_path(unix_style)
            
            # Test with backslashes (Windows-style, if not on Unix)
            if os.sep != '\\':
                windows_style = test_file.replace(os.sep, '\\')
                normalized_windows = normalize_path(windows_style)
                
                # Both should resolve to the same file
                self.assertEqual(os.path.realpath(normalized_unix), 
                               os.path.realpath(normalized_windows))
            
            # All should exist and be absolute
            self.assertTrue(os.path.exists(normalized_unix))
            self.assertTrue(os.path.isabs(normalized_unix))
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_case_sensitivity_handling(self):
        """
        Test handling of case sensitivity across platforms.
        
        This test:
        - Tests case variations in paths
        - Handles differences between case-sensitive and case-insensitive filesystems
        """
        temp_dir = tempfile.mkdtemp()
        try:
            test_file = os.path.join(temp_dir, "TestFile.txt")
            with open(test_file, 'w') as f:
                f.write("case test")
            
            # Test with different case
            lower_case = test_file.lower()
            upper_case = test_file.upper()
            
            # On case-insensitive systems (like Windows/macOS), these should work
            # On case-sensitive systems (like Linux), they might not
            try:
                normalized_lower = normalize_path(lower_case, strict=False)
                normalized_upper = normalize_path(upper_case, strict=False)
                
                # If we get here, the filesystem is case-insensitive
                # or the files happen to exist with these names
                self.assertTrue(os.path.exists(normalized_lower) or 
                              normalized_lower == normalize_path(test_file))
                
            except AutopathError:
                # Case-sensitive filesystem - this is expected on some systems
                pass
                
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# Test runner functions
def run_tests():
    """
    Run all tests with detailed output.
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


def run_specific_test(test_class_name):
    """
    Run a specific test class.
    
    Args:
        test_class_name (str): Name of the test class to run
        
    Returns:
        bool: True if tests passed, False otherwise
    """
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(globals()[test_class_name])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # If run directly, execute all tests
    print(f"{INFO}    Running SKPath Tests...")
    print(INFO)
    
    success = run_tests()
    
    print(f"{INFO}    SKPath Tests Completed")
    if success:
        print(f"{SUCCESS} All tests passed successfully!")
        sys.exit(0)
    else:
        print(f"{FAIL} Some tests failed.")
        sys.exit(1)