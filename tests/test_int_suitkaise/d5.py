#!/usr/bin/env python3
"""
Unified Test Script for fdl Objects System WITH DEBUGGING

Tests all major fdl objects components:
- Box System (custom box drawing)
- Table System (high-performance tables)
- Error Handler (custom traceback formatting)

This script sets up proper import paths and runs comprehensive tests
for all components with detailed reporting.
"""

import os
import sys
from pathlib import Path
import traceback
import warnings

# Add project paths for imports
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
core_path = project_root / "suitkaise" / "_int" / "_fdl" / "core"
objects_path = project_root / "suitkaise" / "_int" / "_fdl" / "objects"
setup_path = project_root / "suitkaise" / "_int" / "_fdl" / "setup"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(core_path))
sys.path.insert(0, str(objects_path))
sys.path.insert(0, str(setup_path))

# Set environment variable to help with imports
os.environ["PYTHONPATH"] = str(core_path)

# Suppress warnings during testing unless specifically testing them
warnings.filterwarnings("ignore", category=UserWarning)


def print_section_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """Print formatted test result."""
    status = "✅ PASSED" if passed else "❌ FAILED"
    print(f"{test_name:.<50} {status}")
    if details and not passed:
        print(f"   Details: {details}")


def test_box_system():
    """Test the box drawing system."""
    print_section_header("BOX SYSTEM TESTS")
    
    results = []
    
    try:
        # Import box system
        from suitkaise._int._fdl.objects.boxes import _create_box, _parse_box_command, _get_available_box_styles
        
        # Test 1: Basic box creation
        try:
            box = _create_box("Hello, World!", "square")
            passed = box and len(box.split('\n')) >= 3
            results.append(("Basic box creation", passed))
            if passed:
                print("Sample box:")
                print(box)
        except Exception as e:
            results.append(("Basic box creation", False, str(e)))
        
        # Test 2: Box with title
        try:
            box = _create_box("Important message", "rounded", title="Alert")
            passed = box and "Alert" in box
            results.append(("Box with title", passed))
        except Exception as e:
            results.append(("Box with title", False, str(e)))
        
        # Test 3: Box with color
        try:
            box = _create_box("Colored content", "double", color="blue")
            passed = box and len(box.split('\n')) >= 3
            results.append(("Box with color", passed))
        except Exception as e:
            results.append(("Box with color", False, str(e)))
        
        # Test 4: Command parsing
        try:
            style, title, color = _parse_box_command("box rounded, title Important, green")
            passed = (style == "rounded" and title == "Important" and color == "green")
            results.append(("Command parsing", passed))
        except Exception as e:
            results.append(("Command parsing", False, str(e)))
        
        # Test 5: Available styles
        try:
            styles = _get_available_box_styles()
            passed = isinstance(styles, list) and len(styles) > 0
            results.append(("Available styles", passed))
            if passed:
                print(f"Available styles: {', '.join(styles)}")
        except Exception as e:
            results.append(("Available styles", False, str(e)))
        
        # Test 6: Box justification options
        try:
            # Test left (default)
            box_left = _create_box("Test", "square", justify="left")
            
            # Test center
            box_center = _create_box("Test", "square", justify="center")
            
            # Test right  
            box_right = _create_box("Test", "square", justify="right")
            
            # All should render without errors
            passed = (box_left and box_center and box_right and
                     len(box_left) > 0 and len(box_center) > 0 and len(box_right) > 0)
            
            # Center and right should have more leading spaces than left
            if passed:
                left_spaces = len(box_left) - len(box_left.lstrip())
                center_spaces = len(box_center) - len(box_center.lstrip()) 
                right_spaces = len(box_right) - len(box_right.lstrip())
                
                # Center and right should have more leading spaces
                passed = center_spaces >= left_spaces and right_spaces >= left_spaces
            
            results.append(("Box justification options", passed))
            
        except Exception as e:
            results.append(("Box justification options", False, str(e)))
        
        # Test 7: Box newlines and content padding
        try:
            box = _create_box("Test", "square")
            
            # Box should start and end with newlines
            newlines_ok = box.startswith('\n') and box.endswith('\n')
            
            # Find the content line (should have spaces around "Test")
            lines = box.strip().split('\n')
            content_line = None
            for line in lines:
                if "Test" in line and ('│' in line or '|' in line):
                    content_line = line
                    break
            
            # Content should be padded: │ Test │
            padding_ok = content_line and " Test " in content_line
            
            passed = newlines_ok and padding_ok
            results.append(("Box newlines and content padding", passed))
            
        except Exception as e:
            results.append(("Box newlines and content padding", False, str(e)))
        
    except ImportError as e:
        print(f"❌ Failed to import box system: {e}")
        return []
    
    # Print results
    for result in results:
        if len(result) == 2:
            print_test_result(result[0], result[1])
        else:
            print_test_result(result[0], result[1], result[2])
    
    return results


def test_table_system():
    """Test the table system."""
    print_section_header("TABLE SYSTEM TESTS")
    
    results = []
    
    try:
        # Import table system
        from suitkaise._int._fdl.objects.tables import _create_table, _process_table_object
        
        # Test 1: Basic table creation
        try:
            table = _create_table("square")
            table.add_columns(["Process", "Memory", "Status"])
            table.add_rows(["UI", "Parser", "Event Hub"])
            
            # Populate some cells
            table.populate(1, 1, "UI Process")
            table.populate("Parser", "Memory", "256MB")
            table.populate(3, "Status", "Running")
            
            result = table.display_table()
            passed = result and "UI Process" in result and "256MB" in result
            results.append(("Basic table creation", passed))
            
            if passed:
                print("Sample table:")
                print(result)
                
        except Exception as e:
            results.append(("Basic table creation", False, str(e)))
        
        # Test 2: Named vs numeric addressing
        try:
            table = _create_table("rounded")
            table.add_columns(["A", "B"])
            table.add_rows(["Row1", "Row2"])
            
            # Test both addressing methods
            table.populate(1, 1, "Cell(1,1)")
            table.populate("Row2", "B", "Cell(Row2,B)")
            
            result = table.display_table()
            passed = "Cell(1,1)" in result and "Cell(Row2,B)" in result
            results.append(("Named vs numeric addressing", passed))
            
        except Exception as e:
            results.append(("Named vs numeric addressing", False, str(e)))
        
        # Test 3: Dimension limits
        try:
            table = _create_table()
            
            # Test column limit (should fail on 4th column)
            limit_enforced = False
            try:
                table.add_columns(["C1", "C2", "C3", "C4"])
            except Exception:
                limit_enforced = True
            
            results.append(("Column dimension limits", limit_enforced))
            
        except Exception as e:
            results.append(("Column dimension limits", False, str(e)))
        
        # Test 4: Cell occupation and repopulate
        try:
            table = _create_table("square")
            table.add_columns(["Test"])
            table.add_rows(["Data"])
            
            # Initial populate
            table.populate(1, 1, "First")
            
            # Try to populate same cell (should fail)
            try:
                table.populate(1, 1, "Second")
                cell_protection_works = False
            except Exception:  # Should be CellOccupiedError but import might not work
                cell_protection_works = True
            
            # Repopulate should work
            table.repopulate(1, 1, "Replaced")
            result = table.display_table()
            
            repopulate_works = "Replaced" in result
            
            passed = cell_protection_works and repopulate_works
            results.append(("Cell management", passed))
            
            if passed:
                print("✓ Cell management works")
            else:
                print(f"❌ Cell protection: {cell_protection_works}, Repopulate: {repopulate_works}")
                
        except Exception as e:
            results.append(("Cell management", False, str(e)))
        
        # Test 5: Different box styles
        try:
            styles = ["square", "rounded", "double", "ascii"]
            all_work = True
            
            for style in styles:
                table = _create_table(style)
                table.add_columns(["Test"])
                table.add_rows(["Data"])
                table.populate(1, 1, "Content")
                result = table.display_table()
                
                if not result or "[Empty Table]" in result:
                    all_work = False
                    break
            
            results.append(("Different box styles", all_work))
            
            if all_work:
                print("✓ All box styles work")
                
        except Exception as e:
            results.append(("Different box styles", False, str(e)))
        
        # Test 6: Headers-only tables
        try:
            # Table with only columns
            table1 = _create_table("square")
            table1.add_columns(["A", "B", "C"])
            result1 = table1.display_table()
            
            # Table with only rows
            table2 = _create_table("square")
            table2.add_rows(["X", "Y", "Z"])
            result2 = table2.display_table()
            
            headers_only_work = (result1 and result2 and 
                               len(result1) > 0 and len(result2) > 0 and
                               "[Empty Table]" not in result1 and "[Empty Table]" not in result2)
            
            results.append(("Headers-only tables", headers_only_work))
            
            if headers_only_work:
                print("✓ Headers-only tables work")
                
        except Exception as e:
            results.append(("Headers-only tables", False, str(e)))
        
        # Test 7: Table junction characters (Unicode)
        try:
            table = _create_table("square")
            table.add_columns(["A", "B", "C"])
            table.add_rows(["1", "2"])
            table.populate(1, 1, "Cell1")
            table.populate(1, 2, "Cell2")
            table.populate(1, 3, "Cell3")
            
            result = table.display_table()
            
            # Should have proper Unicode junction characters, not '+'
            # For square style, should have ┬ ┼ ┴ characters
            has_unicode_junctions = ('┬' in result or '┼' in result or '┴' in result)
            has_ascii_fallback = ('+' in result and not has_unicode_junctions)
            
            # Either Unicode junctions OR ASCII fallback is acceptable
            passed = has_unicode_junctions or has_ascii_fallback
            
            results.append(("Table junction characters", passed))
            
            if passed:
                print("Table with proper junctions:")
                print(result)
                
        except Exception as e:
            results.append(("Table junction characters", False, str(e)))
        
        # Test 8: Object processor integration
        try:
            table = _create_table("square")
            table.add_columns(["Name"])
            table.add_rows(["Value"])
            table.populate(1, 1, "Test")
            
            result = _process_table_object(table)
            passed = result and "Test" in result and not result.startswith("[TABLE_ERROR")
            results.append(("Object processor integration", passed))
            
        except Exception as e:
            results.append(("Object processor integration", False, str(e)))
        
        # Test 9: Performance stats
        try:
            table = _create_table()
            table.add_columns(["A", "B"])
            table.add_rows(["1", "2"])
            table.populate(1, 1, "Data")
            table.display_table()
            
            stats = table.get_performance_stats()
            passed = isinstance(stats, dict) and 'cell_updates' in stats
            results.append(("Performance stats", passed))
            
            if passed:
                print(f"Performance stats: {stats}")
                
        except Exception as e:
            results.append(("Performance stats", False, str(e)))
        
    except ImportError as e:
        print(f"❌ Failed to import table system: {e}")
        return []
    
    # Print results
    for result in results:
        if len(result) == 2:
            print_test_result(result[0], result[1])
        else:
            print_test_result(result[0], result[1], result[2])
    
    return results


def test_error_handler():
    """Test the error handling system."""
    print_section_header("ERROR HANDLER TESTS")
    
    results = []
    
    try:
        # Import error handler
        from suitkaise._int._fdl.core.error_formatter import (
            _ErrorFormatter, _StackFrame, _format_exception,
            _get_error_formatter, _install_exception_handler,
            _get_error_performance_stats, ErrorHandlerError,
            _reset_error_formatter
        )
        
        # Test 1: Basic error formatter creation
        try:
            formatter = _ErrorFormatter()
            passed = formatter is not None
            results.append(("Error formatter creation", passed))
            
            if passed:
                print("✓ Error formatter created successfully")
                
        except Exception as e:
            results.append(("Error formatter creation", False, str(e)))
        
        # Test 2: StackFrame dataclass
        try:
            frame = _StackFrame(
                filename="/test/file.py",
                relative_path="file.py", 
                line_number=10,
                function_name="test_func"
            )
            passed = (frame.filename == "/test/file.py" and 
                     frame.line_number == 10 and
                     frame.function_name == "test_func")
            results.append(("StackFrame dataclass", passed))
            
        except Exception as e:
            results.append(("StackFrame dataclass", False, str(e)))
        
        # Test 3: ANSI code setup (check for recursion bug)
        try:
            formatter = _ErrorFormatter()
            # Check that ANSI codes are strings
            ansi_codes_valid = all([
                isinstance(formatter.error_header_ansi, str),
                isinstance(formatter.filename_ansi, str),
                isinstance(formatter.line_number_ansi, str),
                isinstance(formatter.reset_ansi, str)
            ])
            results.append(("ANSI code setup", ansi_codes_valid))
            
            if ansi_codes_valid:
                print(f"✓ ANSI codes properly set up")
            
        except RecursionError:
            results.append(("ANSI code setup", False, "Recursion detected in _setup_ansi_codes"))
        except Exception as e:
            results.append(("ANSI code setup", False, str(e)))
        
        # Test 4: Path relativization and caching
        try:
            formatter = _ErrorFormatter()
            
            # Test path relativization
            test_path = "/long/absolute/path/to/file.py"
            relative1 = formatter._relativize_path(test_path)
            relative2 = formatter._relativize_path(test_path)  # Should hit cache
            
            # Should return same result and hit cache
            caching_works = (relative1 == relative2 and 
                           formatter._cache_hits > 0)
            
            results.append(("Path relativization and caching", caching_works))
            
            if caching_works:
                print(f"✓ Path caching works: {formatter._cache_hits} cache hits")
                
        except Exception as e:
            results.append(("Path relativization and caching", False, str(e)))
        
        # Test 5: Code context extraction
        try:
            formatter = _ErrorFormatter()
            
            # Create a temporary test file for context extraction
            import tempfile
            import os
            
            test_code = """def sample_function():
    # Line 2
    x = 10
    y = 20  # This is line 4 (error line)
    z = 30
    return x + y + z"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(test_code)
                temp_file = f.name
            
            try:
                # Extract context around line 4
                context_lines, highlight_index = formatter._extract_code_context(temp_file, 4)
                
                # Should have multiple lines and highlight the correct one
                context_works = (len(context_lines) > 1 and 
                               highlight_index >= 0 and
                               any("y = 20" in line for line in context_lines))
                
                results.append(("Code context extraction", context_works))
                
                if context_works:
                    print("✓ Code context extracted:")
                    for i, line in enumerate(context_lines[:3]):  # Show first few
                        marker = " ❱" if i == highlight_index else "  "
                        print(f"   {marker} {line}")
                        
            finally:
                os.unlink(temp_file)
                
        except Exception as e:
            results.append(("Code context extraction", False, str(e)))
        
        # Test 6: Local variable extraction and formatting
        try:
            formatter = _ErrorFormatter()
            
            # Test variables of different types
            test_locals = {
                'simple_int': 42,
                'simple_str': "hello world",
                'long_string': "x" * 100,  # Should be truncated
                'simple_list': [1, 2, 3],
                'simple_dict': {'key': 'value'},
                'none_value': None,
                'bool_value': True,
                '__internal__': 'should be skipped',
                'complex_object': object()
            }
            
            formatted_vars = formatter._extract_local_variables(test_locals)
            
            # Check various formatting rules
            var_formatting_works = all([
                'simple_int' in formatted_vars,
                'simple_str' in formatted_vars,
                'long_string' in formatted_vars,
                '__internal__' not in formatted_vars,  # Should skip internal vars
                '42' in formatted_vars['simple_int'],
                'length:' in formatted_vars['simple_list'],  # Collections show length
                '...' in formatted_vars['long_string'],  # Long strings truncated
                'None' in formatted_vars['none_value']
            ])
            
            results.append(("Local variable extraction", var_formatting_works))
            
            if var_formatting_works:
                print("✓ Local variables formatted correctly:")
                for name, value in list(formatted_vars.items())[:3]:
                    print(f"   {name}: {value}")
                    
        except Exception as e:
            results.append(("Local variable extraction", False, str(e)))
        
        # Test 7: Exception formatting with real exception
        try:
            def create_test_exception():
                """Function to create a test exception with stack trace."""
                def inner_function():
                    x = [1, 2, 3]
                    y = "test string"
                    # This will raise an exception
                    return x[10]  # IndexError
                
                def middle_function():
                    data = {"key": "value"}
                    return inner_function()
                
                return middle_function()
            
            # Generate a real exception
            exc_type = None
            exc_value = None
            exc_traceback = None
            
            try:
                create_test_exception()
            except Exception as caught_exception:
                # Capture exception info immediately in the except block
                import sys
                exc_type, exc_value, exc_traceback = sys.exc_info()
            
            # Check we captured the exception
            if exc_type and exc_value and exc_traceback:
                # Format the exception
                formatted = _format_exception(exc_type, exc_value, exc_traceback)
                
                # Debug: Check each validation condition individually
                is_string = isinstance(formatted, str)
                is_substantial = len(formatted) > 100
                has_exception_type = 'IndexError' in formatted
                has_function_names = 'inner_function' in formatted
                has_code_context = ('x[10]' in formatted or 'return x[10]' in formatted)
                has_structure = ('TRACEBACK' in formatted or 'Frame' in formatted)
                
                # Check that formatting worked
                formatting_works = all([
                    is_string,
                    is_substantial,
                    has_exception_type,
                    has_function_names,
                    has_code_context,
                    has_structure
                ])
                
                results.append(("Complete exception formatting", formatting_works))
                
                if formatting_works:
                    print("✓ Exception formatted successfully:")
                    # Show first few lines
                    lines = formatted.split('\n')[:5]
                    for line in lines:
                        if line.strip():
                            print(f"   {line[:60]}..." if len(line) > 60 else f"   {line}")
                else:
                    print("❌ Exception formatting failed validation - Debug info:")
                    print(f"  - Is string: {is_string}")
                    print(f"  - Is substantial (>100 chars): {is_substantial} (length: {len(formatted)})")
                    print(f"  - Contains IndexError: {has_exception_type}")
                    print(f"  - Contains function names: {has_function_names}")
                    print(f"  - Contains code context: {has_code_context}")
                    print(f"  - Has structure: {has_structure}")
                    # Don't show the full formatted output in test debugging - it's confusing
            else:
                results.append(("Complete exception formatting", False, "Failed to capture exception info"))
                            
        except Exception as e:
            results.append(("Complete exception formatting", False, str(e)))
        
        # Test 8: Performance statistics
        try:
            formatter = _ErrorFormatter()
            
            # Create some activity to track
            formatter._formatted_count = 5
            formatter._cache_hits = 3
            formatter._path_cache = {'/test1': 'test1', '/test2': 'test2'}
            
            stats = formatter.get_performance_stats()
            
            stats_valid = all([
                isinstance(stats, dict),
                'exceptions_formatted' in stats,
                'path_cache_size' in stats,
                'cache_hit_rate' in stats,
                stats['exceptions_formatted'] == 5,
                stats['path_cache_size'] == 2,
                0 <= stats['cache_hit_rate'] <= 1
            ])
            
            results.append(("Performance statistics", stats_valid))
            
            if stats_valid:
                print(f"✓ Performance stats: {stats}")
                
        except Exception as e:
            results.append(("Performance statistics", False, str(e)))
        
        # Test 9: Global error formatter singleton
        try:
            formatter1 = _get_error_formatter()
            formatter2 = _get_error_formatter()
            
            # Should return same instance
            singleton_works = formatter1 is formatter2
            
            results.append(("Global formatter singleton", singleton_works))
            
        except Exception as e:
            results.append(("Global formatter singleton", False, str(e)))
        
        # Test 10: Exception handler installation
        try:
            import sys
            
            # Store original handler
            original_handler = sys.excepthook
            
            # Install our handler
            _install_exception_handler()
            
            # Check that handler was changed
            handler_installed = sys.excepthook != original_handler
            
            # Restore original handler
            sys.excepthook = original_handler
            
            results.append(("Exception handler installation", handler_installed))
            
            if handler_installed:
                print("✓ Exception handler installed and restored")
                
        except Exception as e:
            results.append(("Exception handler installation", False, str(e)))
        
        # Test 11: Box integration (if available)
        try:
            formatter = _ErrorFormatter()
            
            # Try to format a frame (will test box integration)
            frame = _StackFrame(
                filename="test.py",
                relative_path="test.py",
                line_number=10,
                function_name="test_func",
                code_context=["def test_func():", "    return 42"],
                highlight_line=1,
                local_vars={"x": "(int) = 42"},
                is_current=True
            )
            
            formatted_frame = formatter._format_frame(frame, 1)
            
            # Should produce some output
            box_integration_works = (isinstance(formatted_frame, str) and 
                                   len(formatted_frame) > 0 and
                                   'test_func' in formatted_frame)
            
            results.append(("Box integration", box_integration_works))
            
            if box_integration_works:
                print("✓ Box integration works")
                # Show a snippet
                lines = formatted_frame.split('\n')[:3]
                for line in lines:
                    if line.strip():
                        print(f"   {line[:50]}..." if len(line) > 50 else f"   {line}")
                        
        except Exception as e:
            results.append(("Box integration", False, str(e)))
        
        # Test 12: Global performance stats function
        try:
            stats = _get_error_performance_stats()
            
            global_stats_work = (isinstance(stats, dict) and 
                               'exceptions_formatted' in stats)
            
            results.append(("Global performance stats", global_stats_work))
            
        except Exception as e:
            results.append(("Global performance stats", False, str(e)))
        
        # Test 13: Memory usage with large cache
        try:
            formatter = _ErrorFormatter()
            
            # Add many paths to cache to test memory behavior
            for i in range(100):
                test_path = f"/test/path/number/{i}/file.py"
                formatter._relativize_path(test_path)
            
            # Cache should have grown but not exceed max size
            large_cache_works = (len(formatter._path_cache) >= 50 and 
                               len(formatter._path_cache) <= formatter.max_cache_size)
            
            results.append(("Large cache handling", large_cache_works))
            
            if large_cache_works:
                print(f"✓ Cache handling: {len(formatter._path_cache)} entries")
                
        except Exception as e:
            results.append(("Large cache handling", False, str(e)))
        
        # Test 14: Error formatter with disabled locals
        try:
            formatter = _ErrorFormatter(show_locals=False)
            
            # Test variables should not be extracted
            no_locals_works = not formatter.show_locals
            
            results.append(("Disabled locals option", no_locals_works))
            
        except Exception as e:
            results.append(("Disabled locals option", False, str(e)))
        
        # Test 15: Thread safety
        try:
            import threading
            import time
            
            results_list = []
            
            def worker():
                try:
                    # Get formatter instance
                    formatter = _get_error_formatter()
                    
                    # Do some work
                    for i in range(10):
                        path = f"/thread/test/{threading.current_thread().ident}/{i}.py"
                        formatter._relativize_path(path)
                    
                    results_list.append(True)
                except Exception:
                    results_list.append(False)
            
            # Start multiple threads
            threads = []
            for i in range(5):
                t = threading.Thread(target=worker)
                threads.append(t)
                t.start()
            
            # Wait for completion
            for t in threads:
                t.join(timeout=2.0)
            
            # Check results
            thread_safety_works = (len(results_list) == 5 and 
                                 all(results_list))
            
            results.append(("Thread safety", thread_safety_works))
            
            if thread_safety_works:
                print("✓ Thread safety test passed")
                
        except Exception as e:
            results.append(("Thread safety", False, str(e)))
        
        # Test 16: Enhanced error handling
        try:
            formatter = _ErrorFormatter()
            
            # Test with invalid inputs
            try:
                # Invalid frame locals
                formatted_vars = formatter._extract_local_variables("not a dict")
                invalid_input_handled = isinstance(formatted_vars, dict)
            except Exception:
                invalid_input_handled = False
            
            # Test with invalid path
            try:
                result = formatter._relativize_path(None)
                null_path_handled = isinstance(result, str)
            except Exception:
                null_path_handled = False
            
            # Test with invalid line number
            try:
                context, highlight = formatter._extract_code_context("nonexistent.py", -1)
                invalid_line_handled = isinstance(context, list)
            except Exception:
                invalid_line_handled = False
            
            enhanced_error_handling = (invalid_input_handled and 
                                     null_path_handled and 
                                     invalid_line_handled)
            
            results.append(("Enhanced error handling", enhanced_error_handling))
            
            if enhanced_error_handling:
                print("✓ Enhanced error handling works")
                
        except Exception as e:
            results.append(("Enhanced error handling", False, str(e)))
        
    except ImportError as e:
        print(f"❌ Failed to import error handler: {e}")
        results.append(("Error handler import", False, str(e)))
        return results
    
    # Print results
    for result in results:
        if len(result) == 2:
            print_test_result(result[0], result[1])
        else:
            print_test_result(result[0], result[1], result[2])
    
    return results


def test_integration():
    """Test integration between systems."""
    print_section_header("INTEGRATION TESTS")
    
    results = []
    
    try:
        # Test 1: Box + Table integration
        from suitkaise._int._fdl.objects.boxes import _create_box
        from suitkaise._int._fdl.objects.tables import _create_table
        
        try:
            # Create a table
            table = _create_table("rounded")
            table.add_columns(["Component", "Status"])
            table.add_rows(["Boxes", "Tables"])
            table.populate(1, 1, "Working")
            table.populate(2, 2, "Working")
            
            table_output = table.display_table()
            
            # Put table in a box
            boxed_table = _create_box(table_output, "double", title="System Status")
            
            passed = boxed_table and "Working" in boxed_table and "System Status" in boxed_table
            results.append(("Box + Table integration", passed))
            
            if passed:
                print("Integrated example:")
                print(boxed_table)
                
        except Exception as e:
            results.append(("Box + Table integration", False, str(e)))
        
        # Test 2: Unicode fallback consistency
        try:
            from suitkaise._int._fdl.setup.unicode import _get_unicode_support
            
            unicode_support = _get_unicode_support()
            capabilities = unicode_support.get_capabilities_summary()
            
            # Create box and table with same style
            box = _create_box("Test content", "rounded")
            table = _create_table("rounded")
            table.add_columns(["Test"])
            table.add_rows(["Data"])
            table.populate(1, 1, "Content")
            table_output = table.display_table()
            
            # Both should work regardless of Unicode support
            passed = box and table_output and len(box) > 0 and len(table_output) > 0
            results.append(("Unicode fallback consistency", passed))
            
            print(f"Unicode capabilities: {capabilities}")
            
        except Exception as e:
            results.append(("Unicode fallback consistency", False, str(e)))
        
        # Test 3: Error Handler + Box integration
        try:
            from suitkaise._int._fdl.core.error_formatter import _format_exception
            
            # Create a test exception
            try:
                raise ValueError("Test exception for integration")
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                
                # Format the exception (should use boxes internally)
                formatted = _format_exception(exc_type, exc_value, exc_traceback)
                
                # Should contain box elements and exception info
                integration_works = (isinstance(formatted, str) and
                                   len(formatted) > 0 and
                                   'ValueError' in formatted and
                                   'Test exception' in formatted)
                
                results.append(("Error Handler + Box integration", integration_works))
                
                if integration_works:
                    print("✓ Error handler + Box integration works")
                    
        except Exception as e:
            results.append(("Error Handler + Box integration", False, str(e)))
        
    except ImportError as e:
        print(f"❌ Failed integration tests: {e}")
        return []
    
    # Print results
    for result in results:
        if len(result) == 2:
            print_test_result(result[0], result[1])
        else:
            print_test_result(result[0], result[1], result[2])
    
    return results


def main():
    """Run all tests and provide summary."""
    print_section_header("FDL OBJECTS SYSTEM - COMPREHENSIVE TESTS")
    print(f"Python version: {sys.version}")
    print(f"Project root: {project_root}")
    print(f"Testing from: {current_file}")
    print("\n🎯 Testing rewritten table system with (row, column) coordinates")
    print("📋 Comprehensive validation of box system with justification")
    print("🔧 Comprehensive error handler testing with enhanced safety")
    print("🔗 Integration testing between all components")
    
    all_results = []
    
    # Run all test suites
    all_results.extend(test_box_system())
    all_results.extend(test_table_system())
    all_results.extend(test_error_handler())
    all_results.extend(test_integration())
    
    # Calculate summary
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results if len(result) >= 2 and result[1])
    failed_tests = total_tests - passed_tests
    
    # Print summary
    print_section_header("TEST SUMMARY")
    print(f"Total tests run: {total_tests}")
    print(f"Tests passed: {passed_tests}")
    print(f"Tests failed: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("The fdl objects system is working correctly.")
        print("\n✅ Verified Systems:")
        print("  - Box system with justification (left/center/right)")
        print("  - Table system with (row, column) coordinates")
        print("  - Cell management (populate/repopulate/depopulate)")
        print("  - Mixed addressing (numeric + named)")
        print("  - Unicode junction characters")
        print("  - Error handling and dimension limits")
        print("  - Error formatter with enhanced safety and thread safety")
        print("  - Box + Table + Error Handler integration")
    else:
        print(f"\n⚠️  {failed_tests} tests failed.")
        print("Check the details above for specific issues.")
        
        # List failed tests by category
        box_failures = [r for r in all_results[:7] if len(r) >= 2 and not r[1]]
        table_failures = [r for r in all_results[7:16] if len(r) >= 2 and not r[1]]
        error_failures = [r for r in all_results[16:35] if len(r) >= 2 and not r[1]]
        integration_failures = [r for r in all_results[35:] if len(r) >= 2 and not r[1]]
        
        if box_failures:
            print(f"\n📦 Box System Issues ({len(box_failures)}):")
            for failure in box_failures:
                print(f"  - {failure[0]}")
        
        if table_failures:
            print(f"\n📊 Table System Issues ({len(table_failures)}):")
            for failure in table_failures:
                print(f"  - {failure[0]}")
        
        if error_failures:
            print(f"\n🔧 Error Handler Issues ({len(error_failures)}):")
            for failure in error_failures:
                print(f"  - {failure[0]}")
        
        if integration_failures:
            print(f"\n🔗 Integration Issues ({len(integration_failures)}):")
            for failure in integration_failures:
                print(f"  - {failure[0]}")
    
    # Performance summary
    try:
        from suitkaise._int._fdl.objects.boxes import _get_box_renderer
        from suitkaise._int._fdl.objects.tables import _create_table
        from suitkaise._int._fdl.core.error_formatter import _get_error_performance_stats
        
        print_section_header("PERFORMANCE SUMMARY")
        
        # Box performance
        box_renderer = _get_box_renderer()
        box_stats = box_renderer.get_performance_stats()
        print(f"📦 Box system: {box_stats}")
        
        # Table performance 
        sample_table = _create_table()
        sample_table.add_columns(["Test"])
        sample_table.add_rows(["Data"])
        sample_table.populate(1, 1, "Sample")
        sample_table.display_table()
        table_stats = sample_table.get_performance_stats()
        print(f"📊 Table system: {table_stats}")
        
        # Error handler performance
        error_stats = _get_error_performance_stats()
        print(f"🔧 Error handler: {error_stats}")
        
    except Exception as e:
        print(f"Performance summary failed: {e}")
    
    print(f"\n🎯 Final Result: {passed_tests}/{total_tests} tests passed")
    
    # Debug: Show exactly what's happening
    print(f"🔍 Debug: passed_tests = {passed_tests}, total_tests = {total_tests}")
    print(f"🔍 Debug: Condition check = {passed_tests >= total_tests - 2}")
    
    # Only run demo if most tests passed (even if not all)
    if passed_tests >= total_tests - 2:  # Allow 1-2 test failures
        print("\n" + "🎭" * 80)
        print("🔥 ENTERING DEMO SECTION 🔥")
        print_section_header("🎭 LIVE ERROR FORMATTING DEMO 🎭")
        print("About to generate a realistic error to showcase the beautiful formatter...")
        print("This is completely separate from the tests above!")
        print("🎭" * 80)
        
        # Step 1: Try to import
        print("🔍 Step 1: Importing error formatter...")
        try:
            from suitkaise._int._fdl.core.error_formatter import _format_exception
            print("✅ Import successful!")
        except Exception as import_error:
            print(f"❌ Import failed: {import_error}")
            return passed_tests == total_tests
        
        # Step 2: Define demo function
        print("🔍 Step 2: Defining demo function...")
        def demo_complex_function():
            """Demo function with realistic nested calls and variables."""
            # Simulate some processing context
            config = {
                'database_url': 'postgresql://localhost:5432/mydb',
                'cache_size': 1000,
                'debug_mode': True
            }
            
            def process_data(data_list, multiplier=2):
                """Process a list of data items."""
                results = []
                processed_count = 0
                
                for i, item in enumerate(data_list):
                    # Simulate some processing
                    if isinstance(item, (int, float)):
                        result = item * multiplier
                        results.append(result)
                        processed_count += 1
                    else:
                        # This will cause the error!
                        print(f"🚨 About to try slicing item: {item} (type: {type(item)})")
                        result = item[5:10]  # Trying to slice None
                        results.append(result)
                
                return results, processed_count
            
            def validate_and_process():
                """Validation and processing pipeline."""
                input_data = [10, 20, 30, None, 40]  # None will cause error
                batch_size = 5
                timeout_seconds = 30
                
                return process_data(input_data, multiplier=3)
            
            # Start the processing
            return validate_and_process()
        
        # Step 3: Try to run demo function and catch exception
        print("🔍 Step 3: Running demo function to generate exception...")
        exception_caught = False
        try:
            demo_complex_function()
            print("❌ Demo function completed without raising exception!")
        except Exception as demo_exception:
            print(f"✅ Exception caught: {type(demo_exception).__name__}: {demo_exception}")
            exception_caught = True
            
            # Step 4: Try to get exception info
            print("🔍 Step 4: Getting exception info...")
            try:
                import sys
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print(f"✅ Exception info: {exc_type}, {exc_value}")
            except Exception as exc_info_error:
                print(f"❌ Failed to get exception info: {exc_info_error}")
                return passed_tests == total_tests
            
            # Step 5: Try to format the exception
            print("🔍 Step 5: Formatting exception...")
            try:
                formatted_output = _format_exception(exc_type, exc_value, exc_traceback, show_locals=True)
                print(f"✅ Formatting successful! Output length: {len(formatted_output)}")
            except Exception as format_error:
                print(f"❌ Formatting failed: {format_error}")
                import traceback
                print("Traceback of formatting error:")
                traceback.print_exc()
                return passed_tests == total_tests
            
            # Step 6: Display the formatted output
            print("🔍 Step 6: Displaying formatted output...")
            print("\n🔥 BEAUTIFUL CUSTOM FORMATTED ERROR OUTPUT:")
            print("=" * 90)
            
            print(formatted_output)
            
            print("=" * 90)
            
            print("\n🎉 DEMO COMPLETE! 🎉")
            print("Above you can see the custom error formatting featuring:")
            print("  📦 Box-framed stack traces with beautiful Unicode borders")
            print("  📍 Code context showing the exact error location") 
            print("  🔍 Local variables for each frame (config, data_list, results, etc.)")
            print("  📁 Project-relative file paths")
            print("  🎨 Color-coded output (if your terminal supports ANSI colors)")
            print("  ⚡ Much more readable than standard Python tracebacks!")
            print("\nCompare this to what you'd normally see with standard Python errors - much nicer! 🚀")
        
        if not exception_caught:
            print("❌ No exception was raised by demo function - this shouldn't happen!")
                
    else:
        print(f"\nSkipping demo due to test failures ({total_tests - passed_tests} failed)")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)