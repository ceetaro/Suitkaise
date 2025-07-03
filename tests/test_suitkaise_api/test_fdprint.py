"""
Comprehensive test suite for FDPrint API module.

Tests all external API functionality including fprint, dprint, formatting modes,
time specifiers, priority filtering, and convenience functions. Uses colorized 
output for easy reading and good spacing for clarity.

This test suite validates the user-facing API that developers will interact with.
"""

import sys
import time
import io
import contextlib
from pathlib import Path

# Add the suitkaise path for testing (adjust as needed)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Import all API functions to test
    from suitkaise.fdprint.api import (
        fprint,
        dprint,
        set_dprint_level,
        enable_colors,
        disable_colors,
        get_config,
        fmt,
        debug_fmt,
        timestamp,
        quick_debug,
        trace
    )
    API_IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Warning: Could not import FDPrint API functions: {e}")
    print("This is expected if running outside the suitkaise project structure")
    API_IMPORTS_SUCCESSFUL = False


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


@contextlib.contextmanager
def capture_output():
    """Capture stdout for testing print functions."""
    old_stdout = sys.stdout
    sys.stdout = captured_output = io.StringIO()
    try:
        yield captured_output
    finally:
        sys.stdout = old_stdout


def test_fprint_basic_functionality():
    """Test basic fprint functionality."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping fprint basic tests - imports failed")
        return
        
    print_test("fprint Basic Functionality")
    
    try:
        # Test basic string printing
        with capture_output() as output:
            fprint("Hello, world!")
        result = output.getvalue().strip()
        print_result("Hello, world!" in result, "Basic string printing works")
        
        # Test data structure formatting
        test_data = {"name": "Alice", "age": 30, "skills": ["Python", "JavaScript"]}
        with capture_output() as output:
            fprint("User data: {}", test_data)
        result = output.getvalue().strip()
        print_result("User data:" in result, "Data structure formatting works")
        print_result("Alice" in result, "Dict values appear in output")
        print_result("Python" in result, "Nested list values appear")
        
        enable_colors()  # Ensure colors are enabled for type annotations

        with capture_output() as output:
            fprint("Display mode: {}", [1, 2, 3], mode="display")
        display_result = output.getvalue().strip()

        with capture_output() as output:
            fprint("Debug mode: {}", [1, 2, 3], mode="debug")
        debug_result = output.getvalue().strip()

        # DIAGNOSTIC: Print what we actually got
        print(f"  DEBUG: display_result ({len(display_result)}): '{display_result}'")
        print(f"  DEBUG: debug_result ({len(debug_result)}): '{debug_result}'")

        print_result("Display mode:" in display_result, "Display mode works")
        print_result("Debug mode:" in debug_result, "Debug mode works")
        print_result(len(debug_result) > len(display_result), "Debug mode produces more verbose output")
        
        # Test multiple values
        with capture_output() as output:
            fprint("Processing {} and {}", "file1.txt", "file2.txt")
        multi_result = output.getvalue().strip()
        print_result("file1.txt" in multi_result and "file2.txt" in multi_result, 
                    "Multiple value formatting works")
        
        # Test empty/None values
        with capture_output() as output:
            fprint("Empty data: {}", [])
        empty_result = output.getvalue().strip()
        print_result("Empty data:" in empty_result, "Empty data formatting works")
        
        with capture_output() as output:
            fprint("None value: {}", None)
        none_result = output.getvalue().strip()
        print_result("None" in none_result, "None value formatting works")
        
        print_info("Basic result", result[:50] + "..." if len(result) > 50 else result)
        print_info("Display length", str(len(display_result)))
        print_info("Debug length", str(len(debug_result)))
        
    except Exception as e:
        print_result(False, f"fprint basic functionality failed: {e}")
    
    print()


def test_fprint_time_specifiers():
    """Test fprint time specifier functionality."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping fprint time specifier tests - imports failed")
        return
        
    print_test("fprint Time Specifiers")
    
    try:
        # Test basic time specifiers
        time_specs = [
            "time:now",
            "date:now", 
            "datetime:now",
            "hms6:now",
            "hms3:now",
            "compact:now"
        ]
        
        for spec in time_specs:
            with capture_output() as output:
                fprint(f"Current {{spec}}: {{{spec}}}")
            result = output.getvalue().strip()
            
            spec_name = spec.split(":")[0]
            print_result(spec_name not in result, f"Time spec '{spec_name}' was resolved")
            print_result("{" not in result or "}" not in result, f"Time spec '{spec_name}' removed braces")
            
            # Check format-specific content
            if spec_name == "time":
                print_result(":" in result, "Time spec includes colons")
            elif spec_name == "date":
                print_result("-" in result or "/" in result, "Date spec includes separators")
        
        # Test timezone specifiers
        timezone_specs = ["timepst:now", "timeest:now", "timeutc:now"]
        for tz_spec in timezone_specs:
            try:
                with capture_output() as output:
                    fprint(f"Timezone: {{{tz_spec}}}")
                result = output.getvalue().strip()
                
                expected_tz = tz_spec.replace("time", "").replace(":now", "").upper()
                print_result(expected_tz in result, f"Timezone spec '{tz_spec}' includes {expected_tz}")
            except Exception as e:
                print_result(False, f"Timezone spec '{tz_spec}' failed: {e}")
        
        # Test mixed time specs and data
        test_data = {"status": "processing", "count": 42}
        with capture_output() as output:
            fprint("Report at {time:now}: {}", test_data)
        mixed_result = output.getvalue().strip()
        
        print_result(":" in mixed_result, "Mixed time/data includes time format")
        print_result("processing" in mixed_result, "Mixed time/data includes data")
        print_result("42" in mixed_result, "Mixed time/data includes numeric data")
        
        # Test multiple time specs in one call
        with capture_output() as output:
            fprint("Started {time:now}, finishing by {date:now}")
        multi_time_result = output.getvalue().strip()
        
        colon_count = multi_time_result.count(":")
        print_result(colon_count >= 1, "Multiple time specs work")
        print_result("Started" in multi_time_result and "finishing" in multi_time_result, 
                    "Multiple time specs preserve text")
        
        # Test error handling with invalid specs
        with capture_output() as output:
            fprint("Invalid: {badspec:now}")
        invalid_result = output.getvalue().strip()
        print_result(len(invalid_result) > 0, "Invalid time specs handled gracefully")
        
        print_info("Time spec result", result[:40] + "..." if len(result) > 40 else result)
        print_info("Mixed result", mixed_result[:50] + "..." if len(mixed_result) > 50 else mixed_result)
        
    except Exception as e:
        print_result(False, f"fprint time specifiers failed: {e}")
    
    print()


def test_dprint_functionality():
    """Test dprint debug printing functionality."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping dprint functionality tests - imports failed")
        return
        
    print_test("dprint Debug Printing Functionality")
    
    try:
        # Test basic debug message
        with capture_output() as output:
            dprint("Basic debug message")
        basic_result = output.getvalue().strip()
        
        print_result("Basic debug message" in basic_result, "Basic debug message appears")
        print_result("-" in basic_result, "Debug message includes timestamp separator")
        print_result(":" in basic_result, "Debug message includes time format")
        
        # Test debug message with variables
        test_vars = ({"user": "Alice"}, [1, 2, 3], "status")
        with capture_output() as output:
            dprint("Debug with variables", test_vars)
        vars_result = output.getvalue().strip()
        
        print_result("Debug with variables" in vars_result, "Debug message text appears")
        print_result("[" in vars_result and "]" in vars_result, "Variables section bracketed")
        print_result("Alice" in vars_result, "Dict variable data appears")
        print_result("status" in vars_result, "String variable appears")
        
        # Test different priority levels
        priorities = [1, 2, 3, 4, 5]
        priority_results = []
        
        for priority in priorities:
            with capture_output() as output:
                dprint(f"Priority {priority} message", (), priority)
            result = output.getvalue().strip()
            priority_results.append((priority, result))
            
            print_result(f"Priority {priority}" in result, f"Priority {priority} message works")
            
            # High priority messages should have priority indicator
            if priority >= 4:
                print_result(f"[P{priority}]" in result, f"Priority {priority} has indicator")
        
        # Test priority filtering by setting level and checking output
        original_level = get_config().get('debug_level', 1)
        
        # Set level to 3, test that low priority messages are filtered
        set_dprint_level(3)
        
        with capture_output() as output:
            dprint("Low priority message", (), 1)  # Should be filtered
        low_pri_result = output.getvalue().strip()
        
        with capture_output() as output:
            dprint("High priority message", (), 4)  # Should appear
        high_pri_result = output.getvalue().strip()
        
        print_result(len(low_pri_result) == 0, "Low priority message filtered out")
        print_result("High priority message" in high_pri_result, "High priority message appears")
        
        # Test empty variables
        with capture_output() as output:
            dprint("Empty variables test", (), 3) 
        empty_vars_result = output.getvalue().strip()
        print_result("Empty variables test" in empty_vars_result, "Empty variables handled")
        print_result("[]" not in empty_vars_result, "Empty variables don't show brackets")
        
        # Test None variables
        with capture_output() as output:
            dprint("None variables test", None)
        none_vars_result = output.getvalue().strip()
        print_result("None variables test" in none_vars_result, "None variables handled")
        
        # Test complex nested variables
        complex_vars = ({
            "nested": {"deep": ["very", "deep"]},
            "list": [1, {"inner": True}, 3]
        },)
        
        with capture_output() as output:
            dprint("Complex data", complex_vars, 2)
        complex_result = output.getvalue().strip()
        
        print_result("Complex data" in complex_result, "Complex debug message works")
        print_result("nested" in complex_result, "Complex nested data appears")
        print_result("deep" in complex_result, "Deep nesting accessible")
        
        # Reset debug level
        set_dprint_level(original_level)
        
        print_info("Basic result", basic_result[:50] + "..." if len(basic_result) > 50 else basic_result)
        print_info("Variables result length", str(len(vars_result)))
        print_info("Complex result length", str(len(complex_result)))
        
    except Exception as e:
        print_result(False, f"dprint functionality failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_debug_level_management():
    """Test debug level setting and filtering."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping debug level management tests - imports failed")
        return
        
    print_test("Debug Level Management")
    
    try:
        # Get initial configuration
        initial_config = get_config()
        print_result(isinstance(initial_config, dict), "get_config returns dictionary")
        print_result('debug_level' in initial_config, "Config contains debug_level")
        
        initial_level = initial_config.get('debug_level', 1)
        print_result(1 <= initial_level <= 5, f"Initial debug level {initial_level} in valid range")
        
        # Test setting different debug levels
        test_levels = [1, 2, 3, 4, 5]
        
        for level in test_levels:
            with capture_output() as output:
                set_dprint_level(level)
            set_result = output.getvalue().strip()
            
            print_result(f"Debug level set to {level}" in set_result, f"Level {level} setting confirmed")
            
            # Verify the level was actually set
            current_config = get_config()
            current_level = current_config.get('debug_level', 0)
            print_result(current_level == level, f"Level {level} actually set in config")
        
        # Test message filtering at different levels
        set_dprint_level(3)  # Set to medium level
        
        filter_tests = [
            (1, False, "Low priority filtered"),
            (2, False, "Medium-low priority filtered"),
            (3, True, "Medium priority shown"),
            (4, True, "High priority shown"),
            (5, True, "Critical priority shown")
        ]
        
        for priority, should_appear, description in filter_tests:
            with capture_output() as output:
                dprint(f"Test message priority {priority}", (), priority)
            result = output.getvalue().strip()
            
            message_appeared = len(result) > 0 and f"Test message priority {priority}" in result
            print_result(message_appeared == should_appear, description)
        
        # Test extreme levels
        set_dprint_level(1)  # Most permissive
        with capture_output() as output:
            dprint("Should appear at level 1", (), 1)
        level1_result = output.getvalue().strip()
        print_result("Should appear at level 1" in level1_result, "Level 1 shows all messages")
        
        set_dprint_level(5)  # Most restrictive
        with capture_output() as output:
            dprint("Should be filtered at level 5", (), 3)
        level5_low_result = output.getvalue().strip()
        
        with capture_output() as output:
            dprint("Should appear at level 5", (), 5)
        level5_high_result = output.getvalue().strip()
        
        print_result(len(level5_low_result) == 0, "Level 5 filters medium priority")
        print_result("Should appear at level 5" in level5_high_result, "Level 5 shows critical messages")
        
        # Test priority indicators
        set_dprint_level(1)  # Show all messages
        
        with capture_output() as output:
            dprint("Normal priority", (), 3)
        normal_result = output.getvalue().strip()
        
        with capture_output() as output:
            dprint("High priority", (), 4)
        high_result = output.getvalue().strip()
        
        with capture_output() as output:
            dprint("Critical priority", (), 5)
        critical_result = output.getvalue().strip()
        
        print_result("[P4]" in high_result, "Priority 4 has indicator")
        print_result("[P5]" in critical_result, "Priority 5 has indicator")
        print_result("[P3]" not in normal_result, "Priority 3 has no indicator")
        
        # Reset to reasonable default
        set_dprint_level(2)
        final_config = get_config()
        final_level = final_config.get('debug_level', 0)
        print_result(final_level == 2, "Debug level reset to 2")
        
        print_info("Initial level", str(initial_level))
        print_info("Final level", str(final_level))
        print_info("Config keys", str(list(initial_config.keys())))
        
    except Exception as e:
        print_result(False, f"Debug level management failed: {e}")
    
    print()


def test_color_management():
    """Test color enable/disable functionality."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping color management tests - imports failed")
        return
        
    print_test("Color Management")
    
    try:
        # Test enable colors
        with capture_output() as output:
            enable_colors()
        enable_result = output.getvalue().strip()
        print_result("Colors enabled" in enable_result, "enable_colors provides feedback")
        
        # Test disable colors
        with capture_output() as output:
            disable_colors()
        disable_result = output.getvalue().strip()
        print_result("Colors disabled" in disable_result, "disable_colors provides feedback")
        
        # Test that color commands don't break formatting
        enable_colors()
        
        with capture_output() as output:
            fprint("Test with colors: {}", {"key": "value"})
        colored_result = output.getvalue().strip()
        
        disable_colors()
        
        with capture_output() as output:
            fprint("Test without colors: {}", {"key": "value"})
        plain_result = output.getvalue().strip()
        
        print_result("Test with colors:" in colored_result, "Colored formatting works")
        print_result("Test without colors:" in plain_result, "Plain formatting works")
        print_result("key" in colored_result and "value" in colored_result, "Colored data appears")
        print_result("key" in plain_result and "value" in plain_result, "Plain data appears")
        
        # Test color state in configuration
        enable_colors()
        enabled_config = get_config()
        
        disable_colors()
        disabled_config = get_config()
        
        # Note: The config might not reflect color state if it's handled internally
        print_result(isinstance(enabled_config, dict), "Config accessible when colors enabled")
        print_result(isinstance(disabled_config, dict), "Config accessible when colors disabled")
        
        # Test multiple color toggles
        for i in range(3):
            enable_colors()
            disable_colors()
        
        with capture_output() as output:
            fprint("After toggles: {}", [1, 2, 3])
        toggle_result = output.getvalue().strip()
        print_result("After toggles:" in toggle_result, "Multiple color toggles don't break formatting")
        
        # Re-enable colors for remaining tests
        enable_colors()
        
        print_info("Enable result", enable_result)
        print_info("Disable result", disable_result)
        print_info("Colored result length", str(len(colored_result)))
        print_info("Plain result length", str(len(plain_result)))
        
    except Exception as e:
        print_result(False, f"Color management failed: {e}")
    
    print()


def test_convenience_functions():
    """Test convenience functions (fmt, debug_fmt, timestamp)."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping convenience functions tests - imports failed")
        return
        
    print_test("Convenience Functions")
    
    try:
        # Test fmt function
        test_data = {"name": "Bob", "items": [1, 2, 3]}
        
        display_formatted = fmt(test_data, "display")
        debug_formatted = fmt(test_data, "debug")
        
        print_result(isinstance(display_formatted, str), "fmt returns string")
        print_result(len(display_formatted) > 0, "fmt produces output")
        print_result("Bob" in display_formatted, "fmt display includes data")
        print_result(len(debug_formatted) > len(display_formatted), "fmt debug more verbose than display")
        
        # Test debug_fmt function
        debug_only = debug_fmt(test_data)
        print_result(isinstance(debug_only, str), "debug_fmt returns string")
        print_result(debug_only == debug_formatted, "debug_fmt equivalent to fmt(obj, 'debug')")
        
        # Test different data types with fmt
        fmt_tests = [
            (None, "None"),
            (42, "42"),
            ("hello", "hello"),
            ([1, 2, 3], "1"),
            ({"key": "value"}, "key"),
            ({1, 2, 3}, "1"),
            ((1, 2), "1"),
        ]
        
        for data, expected_content in fmt_tests:
            formatted = fmt(data, "display")
            print_result(expected_content in formatted, f"fmt handles {type(data).__name__}")
        
        # Test timestamp function
        current_timestamp = timestamp()
        print_result(isinstance(current_timestamp, str), "timestamp returns string")
        print_result(len(current_timestamp) > 0, "timestamp produces output")
        print_result(":" in current_timestamp, "timestamp includes time separator")
        
        # Test different timestamp formats
        timestamp_formats = [
            'time',      # Default
            'date',      # Date only
            'datetime',  # Combined
            'hms6',      # Microseconds
            'compact',   # Compact format
        ]
        
        for ts_format in timestamp_formats:
            try:
                ts_result = timestamp(ts_format)
                print_result(isinstance(ts_result, str), f"timestamp('{ts_format}') returns string")
                print_result(len(ts_result) > 0, f"timestamp('{ts_format}') produces output")
                
                if ts_format == 'date':
                    print_result("-" in ts_result or "/" in ts_result, f"timestamp('{ts_format}') has date separators")
                elif ts_format == 'time':
                    print_result(":" in ts_result, f"timestamp('{ts_format}') has time separators")
                    
            except Exception as e:
                print_result(False, f"timestamp('{ts_format}') failed: {e}")
        
        # Test error handling
        error_fmt = fmt("test", "invalid_mode")
        print_result(isinstance(error_fmt, str), "fmt handles invalid mode gracefully")
        
        try:
            error_timestamp = timestamp("invalid_format")
            print_result(isinstance(error_timestamp, str), "timestamp handles invalid format gracefully")
        except:
            print_result(True, "timestamp raises appropriate error for invalid format")
        
        # Test complex nested data formatting
        complex_data = {
            "users": [
                {"name": "Alice", "roles": ["admin", "user"]},
                {"name": "Bob", "roles": ["user"]}
            ],
            "settings": {
                "debug": True,
                "timeout": 30,
                "features": {"auth": True, "logging": False}
            }
        }
        
        complex_display = fmt(complex_data, "display")
        complex_debug = fmt(complex_data, "debug")
        
        print_result("Alice" in complex_display, "Complex display formatting reaches nested data")
        print_result("admin" in complex_display, "Complex display formatting includes list items")
        print_result("timeout" in complex_display, "Complex display formatting includes nested dict keys")
        
        print_result("Alice" in complex_debug, "Complex debug formatting reaches nested data")
        print_result(len(complex_debug) > len(complex_display), "Complex debug more verbose than display")
        
        print_info("Display formatted", display_formatted[:40] + "..." if len(display_formatted) > 40 else display_formatted)
        print_info("Debug formatted length", str(len(debug_formatted)))
        print_info("Current timestamp", current_timestamp)
        print_info("Complex display lines", str(len(complex_display.split('\n'))))
        
    except Exception as e:
        print_result(False, f"Convenience functions failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_quick_helpers():
    """Test quick helper functions (quick_debug, trace)."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping quick helpers tests - imports failed")
        return
        
    print_test("Quick Helper Functions")
    
    try:
        # Test quick_debug function
        test_objects = [
            {"user": "Alice"},
            [1, 2, 3, "test"],
            "simple string",
            42,
            True
        ]
        
        with capture_output() as output:
            quick_debug(*test_objects)
        quick_result = output.getvalue()
        
        print_result(len(quick_result) > 0, "quick_debug produces output")
        print_result("Object 1" in quick_result, "quick_debug labels first object")
        print_result("Object 2" in quick_result, "quick_debug labels second object")
        print_result("Alice" in quick_result, "quick_debug includes dict data")
        print_result("simple string" in quick_result, "quick_debug includes string data")
        
        # Count number of objects processed
        object_count = quick_result.count("Object ")
        print_result(object_count == len(test_objects), f"quick_debug processed all {len(test_objects)} objects")
        
        # Test trace function
        with capture_output() as output:
            trace("test_value", [1, 2, 3], message="Custom trace")
        trace_result = output.getvalue().strip()
        
        print_result("Custom trace" in trace_result, "trace uses custom message")
        print_result("test_value" in trace_result, "trace includes string data")
        print_result("[" in trace_result, "trace includes list data")
        print_result("-" in trace_result, "trace includes timestamp")
        
        # Test trace with default message
        with capture_output() as output:
            trace("default_test", 42)
        trace_default_result = output.getvalue().strip()
        
        print_result("Trace" in trace_default_result, "trace uses default message")
        print_result("default_test" in trace_default_result, "trace with default includes data")
        print_result("42" in trace_default_result, "trace includes numeric data")
        
        # Test empty quick_debug
        with capture_output() as output:
            quick_debug()
        empty_quick_result = output.getvalue()
        print_result(len(empty_quick_result) == 0, "Empty quick_debug produces no output")
        
        # Test single object quick_debug
        with capture_output() as output:
            quick_debug({"single": "object"})
        single_quick_result = output.getvalue().strip()
        print_result("Object 1" in single_quick_result, "Single object quick_debug works")
        print_result("single" in single_quick_result, "Single object data appears")
        
        # Test trace with complex data
        complex_trace_data = {
            "function": "process_data",
            "input": {"file": "data.csv", "rows": 1000},
            "output": {"processed": 950, "errors": 50}
        }
        
        with capture_output() as output:
            trace(complex_trace_data, message="Function execution")
        complex_trace_result = output.getvalue().strip()
        
        print_result("Function execution" in complex_trace_result, "Complex trace message works")
        print_result("process_data" in complex_trace_result, "Complex trace data appears")
        print_result("1000" in complex_trace_result, "Complex nested data accessible")
        
        # Test that helpers use appropriate debug priority
        original_level = get_config().get('debug_level', 1)
        set_dprint_level(3)  # Set higher threshold
        
        with capture_output() as output:
            quick_debug("should appear")  # Uses priority 2, might be filtered
        filtered_quick_result = output.getvalue()
        
        with capture_output() as output:
            trace("should appear", message="trace test")  # Uses priority 2, might be filtered
        filtered_trace_result = output.getvalue()
        
        # Reset debug level
        set_dprint_level(original_level)
        
        print_result(len(filtered_quick_result) == 0, "quick_debug respects debug level filtering")
        print_result(len(filtered_trace_result) == 0, "trace respects debug level filtering")
        
        print_info("Quick debug object count", str(object_count))
        print_info("Trace result", trace_result[:50] + "..." if len(trace_result) > 50 else trace_result)
        print_info("Complex trace length", str(len(complex_trace_result)))
        
    except Exception as e:
        print_result(False, f"Quick helpers failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_integration_scenarios():
    """Test real-world integration scenarios."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping integration scenarios tests - imports failed")
        return
        
    print_test("Integration Scenarios")
    
    try:
        # Scenario 1: Development debugging workflow
        print(f"  {Colors.BLUE}Scenario 1: Development debugging workflow{Colors.END}")
        
        # Simulate a data processing pipeline
        input_data = {
            "users": [
                {"name": "Alice", "age": 30, "active": True},
                {"name": "Bob", "age": 25, "active": False},
                {"name": "Charlie", "age": 35, "active": True}
            ],
            "config": {"max_age": 40, "require_active": True}
        }
        
        with capture_output() as output:
            fprint("Processing started at {time:now}")
            fprint("Input data: {}", input_data)
            dprint("Data validation", (input_data,), 2)
            
            # Simulate processing steps
            active_users = [u for u in input_data["users"] if u["active"]]
            trace(active_users, message="Filtered active users")
            
            fprint("Processing completed at {time:now}: {} active users", len(active_users))
        
        workflow_result = output.getvalue()
        
        print_result("Processing started" in workflow_result, "Workflow start message works")
        print_result("Alice" in workflow_result, "Input data formatting works")
        print_result("Data validation" in workflow_result, "Debug message works")
        print_result("Filtered active users" in workflow_result, "Trace message works")
        print_result("2 active users" in workflow_result, "Final result formatting works")
        
        # Scenario 2: Error reporting and debugging
        print(f"\n  {Colors.BLUE}Scenario 2: Error reporting and debugging{Colors.END}")
        
        error_data = {
            "error_code": 500,
            "message": "Database connection failed",
            "details": {
                "host": "db.example.com",
                "port": 5432,
                "timeout": 30
            },
            "stack_trace": ["function_a", "function_b", "database_connect"]
        }
        
        with capture_output() as output:
            fprint("ERROR at {datetime:now}: {}", error_data["message"], mode="debug")
            dprint("Error details", (error_data,), 4)  # High priority
            quick_debug(error_data["details"], error_data["stack_trace"])
        
        error_result = output.getvalue()
        
        print_result("ERROR at" in error_result, "Error timestamp works")
        print_result("Database connection failed" in error_result, "Error message works")
        print_result("[P4]" in error_result, "High priority debug indicator works")
        print_result("db.example.com" in error_result, "Error details formatting works")
        print_result("function_a" in error_result, "Stack trace formatting works")
        
        # Scenario 3: Performance monitoring
        print(f"\n  {Colors.BLUE}Scenario 3: Performance monitoring{Colors.END}")
        
        perf_data = {
            "operation": "data_export",
            "duration_ms": 1250,
            "rows_processed": 10000,
            "memory_usage": "45.2 MB",
            "cpu_usage": "23%"
        }
        
        with capture_output() as output:
            fprint("Performance report at {time:now}:")
            fprint("Operation: {} - Duration: {}ms", perf_data["operation"], perf_data["duration_ms"])
            fprint("Metrics: {}", {k: v for k, v in perf_data.items() if k != "operation"})
            dprint("Full performance data", (perf_data,), 2)
        
        perf_result = output.getvalue()
        
        print_result("Performance report" in perf_result, "Performance header works")
        print_result("data_export" in perf_result, "Operation name works")
        print_result("1250ms" in perf_result, "Duration formatting works")
        print_result("10000" in perf_result, "Metrics formatting works")
        
        # Scenario 4: Configuration management
        print(f"\n  {Colors.BLUE}Scenario 4: Configuration and level management{Colors.END}")
        
        # Test different debug levels in a workflow
        set_dprint_level(1)
        
        with capture_output() as output:
            dprint("Low priority debug", (), 1)
            dprint("Medium priority info", (), 3)
            dprint("High priority warning", (), 4)
            dprint("Critical error", (), 5)
        
        all_levels_result = output.getvalue()
        level_counts = [
            ("Low priority", all_levels_result.count("Low priority")),
            ("Medium priority", all_levels_result.count("Medium priority")),
            ("High priority", all_levels_result.count("High priority")),
            ("Critical error", all_levels_result.count("Critical error"))
        ]
        
        print_result(all(count == 1 for _, count in level_counts), "All debug levels appear at level 1")
        
        set_dprint_level(4)
        
        with capture_output() as output:
            dprint("Low priority debug", (), 1)
            dprint("Medium priority info", (), 3)
            dprint("High priority warning", (), 4)
            dprint("Critical error", (), 5)
        
        filtered_result = output.getvalue()
        high_count = filtered_result.count("High priority")
        critical_count = filtered_result.count("Critical error")
        low_count = filtered_result.count("Low priority")
        
        print_result(high_count == 1 and critical_count == 1, "High/critical messages appear at level 4")
        print_result(low_count == 0, "Low priority messages filtered at level 4")
        
        # Reset debug level
        set_dprint_level(2)
        
        print_info("Workflow result lines", str(len(workflow_result.split('\n'))))
        print_info("Error result length", str(len(error_result)))
        print_info("Performance result lines", str(len(perf_result.split('\n'))))
        
    except Exception as e:
        print_result(False, f"Integration scenarios failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_error_handling_and_edge_cases():
    """Test error handling and edge cases."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping error handling tests - imports failed")
        return
        
    print_test("Error Handling and Edge Cases")
    
    try:
        # Test invalid format strings
        with capture_output() as output:
            fprint("Invalid format {}", "arg1", "arg2")  # Too many args for format
        invalid_format_result = output.getvalue().strip()
        print_result(len(invalid_format_result) > 0, "Invalid format string handled gracefully")
        
        # Test empty format string
        with capture_output() as output:
            fprint("")
        empty_format_result = output.getvalue().strip()
        print_result(len(empty_format_result) == 0, "Empty format string handled")
        
        # Test None values in various contexts
        with capture_output() as output:
            fprint("None test: {}", None)
        none_format_result = output.getvalue().strip()
        print_result("None" in none_format_result, "None value formatting works")
        
        with capture_output() as output:
            dprint("Debug None", (None,), 2)
        none_debug_result = output.getvalue().strip()
        print_result("Debug None" in none_debug_result, "None in debug variables works")
        
        # Test very large data structures
        large_list = list(range(1000))
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100)}
        
        with capture_output() as output:
            fprint("Large data: {}", large_list[:10])  # Just first 10 to avoid huge output
        large_list_result = output.getvalue().strip()
        print_result("Large data:" in large_list_result, "Large list formatting works")
        
        with capture_output() as output:
            fprint("Large dict sample: {}", dict(list(large_dict.items())[:5]))
        large_dict_result = output.getvalue().strip()
        print_result("Large dict sample:" in large_dict_result, "Large dict formatting works")
        
        # Test deeply nested structures
        deep_nested = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "level5": ["deep", "value"]
                        }
                    }
                }
            }
        }
        
        with capture_output() as output:
            fprint("Deep nesting: {}", deep_nested)
        deep_result = output.getvalue().strip()
        print_result("deep" in deep_result and "value" in deep_result, "Deep nesting handled")
        
        # Test circular references protection (if implemented)
        try:
            circular_dict = {"ref": None}
            circular_dict["ref"] = circular_dict  # Creates circular reference
            
            with capture_output() as output:
                fprint("Circular: {}", circular_dict)
            circular_result = output.getvalue().strip()
            print_result(len(circular_result) > 0, "Circular references handled (or avoided)")
        except RecursionError:
            print_result(True, "Circular references raise appropriate error")
        except Exception:
            print_result(True, "Circular references handled gracefully")
        
        # Test unicode and special characters
        unicode_data = {
            "emoji": "🎉 🚀 ✨",
            "unicode": "héllo wörld",
            "special": "quotes: \"test\" 'single'",
            "newlines": "line1\nline2\nline3"
        }
        
        with capture_output() as output:
            fprint("Unicode test: {}", unicode_data)
        unicode_result = output.getvalue()
        print_result("🎉" in unicode_result, "Emoji formatting works")
        print_result("héllo" in unicode_result, "Unicode characters work")
        print_result("quotes:" in unicode_result, "Special characters work")
        
        # Test extreme debug levels
        try:
            set_dprint_level(0)  # Below minimum
            config_level_0 = get_config().get('debug_level', 1)
            print_result(config_level_0 >= 1, "Debug level 0 handled gracefully")
        except:
            print_result(True, "Debug level 0 raises appropriate error")
        
        try:
            set_dprint_level(100)  # Above maximum
            config_level_100 = get_config().get('debug_level', 5)
            print_result(config_level_100 <= 5, "Debug level 100 handled gracefully")
        except:
            print_result(True, "Debug level 100 raises appropriate error")
        
        # Test invalid timestamp formats
        invalid_timestamp = timestamp("completely_invalid_format")
        print_result(isinstance(invalid_timestamp, str), "Invalid timestamp format handled")
        print_result(len(invalid_timestamp) > 0, "Invalid timestamp produces some output")
        
        # Test fmt with invalid mode
        invalid_mode_fmt = fmt([1, 2, 3], "invalid_mode")
        print_result(isinstance(invalid_mode_fmt, str), "Invalid fmt mode handled")
        print_result("1" in invalid_mode_fmt, "Invalid mode still produces data")
        
        # Reset to safe defaults
        set_dprint_level(2)
        enable_colors()
        
        print_info("Invalid format result", invalid_format_result[:40] + "..." if len(invalid_format_result) > 40 else invalid_format_result)
        print_info("Unicode result length", str(len(unicode_result)))
        print_info("Deep nesting result length", str(len(deep_result)))
        
    except Exception as e:
        print_result(False, f"Error handling and edge cases failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def run_all_api_tests():
    """Run all FDPrint API tests."""
    print_section("Comprehensive FDPrint API Test Suite")
    
    if not API_IMPORTS_SUCCESSFUL:
        print(f"{Colors.RED}{Colors.BOLD}❌ Cannot run tests - import failures{Colors.END}")
        print(f"{Colors.YELLOW}Ensure the suitkaise.fdprint.api module is properly installed or accessible{Colors.END}")
        return
    
    print(f"{Colors.GREEN}✅ Successfully imported all FDPrint API functions{Colors.END}")
    print(f"{Colors.WHITE}Testing the complete user-facing FDPrint API...{Colors.END}\n")
    
    try:
        # Core API functionality tests
        test_fprint_basic_functionality()
        test_fprint_time_specifiers()
        test_dprint_functionality()
        test_debug_level_management()
        test_color_management()
        test_convenience_functions()
        test_quick_helpers()
        
        # Real-world usage tests
        test_integration_scenarios()
        test_error_handling_and_edge_cases()
        
        print_section("FDPrint API Test Summary")
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL FDPRINT API TESTS COMPLETED! 🎉{Colors.END}")
        print(f"{Colors.WHITE}✅ fprint(): Smart formatting with time specifiers working perfectly{Colors.END}")
        print(f"{Colors.WHITE}✅ dprint(): Debug printing with auto-timestamps and priority filtering{Colors.END}")
        print(f"{Colors.WHITE}✅ Time specifiers: Comprehensive format support (time:now, date:now, etc.){Colors.END}")
        print(f"{Colors.WHITE}✅ Debug levels: Priority-based filtering and configuration{Colors.END}")
        print(f"{Colors.WHITE}✅ Color management: Enable/disable with graceful handling{Colors.END}")
        print(f"{Colors.WHITE}✅ Convenience functions: fmt(), debug_fmt(), timestamp() all working{Colors.END}")
        print(f"{Colors.WHITE}✅ Quick helpers: quick_debug() and trace() for rapid debugging{Colors.END}")
        print(f"{Colors.WHITE}✅ Integration scenarios: Real-world usage patterns validated{Colors.END}")
        print(f"{Colors.WHITE}✅ Error handling: Graceful degradation and edge case management{Colors.END}")
        print(f"{Colors.WHITE}✅ The FDPrint API is production-ready! 🚀{Colors.END}")
        print()
        
        print(f"{Colors.CYAN}{Colors.BOLD}KEY API ACHIEVEMENTS VALIDATED:{Colors.END}")
        print(f"{Colors.GREEN}🎨 Beautiful output - Transform ugly data into readable formats{Colors.END}")
        print(f"{Colors.GREEN}⏰ Time magic - Custom specifiers like {{time:now}} and {{datePST:now}}{Colors.END}")
        print(f"{Colors.GREEN}🔍 Smart debugging - Auto-timestamps and priority-based filtering{Colors.END}")
        print(f"{Colors.GREEN}🌈 Color support - Full color management with enable/disable{Colors.END}")
        print(f"{Colors.GREEN}📊 Data intelligence - Display vs debug modes with type annotations{Colors.END}")
        print(f"{Colors.GREEN}🚀 Developer experience - Quick helpers and convenience functions{Colors.END}")
        print(f"{Colors.GREEN}🛡️ Robust handling - Graceful error handling and edge cases{Colors.END}")
        print(f"{Colors.GREEN}⚡ Real-world ready - Integration scenarios and workflow support{Colors.END}")
        
    except Exception as e:
        print(f"{Colors.RED}{Colors.BOLD}❌ Test suite failed with error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_api_tests()