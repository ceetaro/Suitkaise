"""
FDPrint API - Smart Formatting and Debug Printing for Suitkaise

This module provides user-friendly formatting functionality that transforms ugly Python
data structures into beautiful, readable output while providing powerful debugging
capabilities with automatic timestamping and priority-based filtering.

Key Features:
- fprint(): Smart formatted printing with custom interpolation and time specifiers
- dprint(): Debug printing with priority levels and automatic timestamps
- Dual formatting modes: Display (clean) and Debug (verbose with type annotations)
- Color-coded output for enhanced readability
- Time/date formatting with custom specifiers (time:now, date:now, hms6:now, etc.)
- Priority-based debug message filtering

Philosophy: "Make ugly data beautiful" - Transform raw Python output into readable,
scannable formats that enhance debugging and user experience.
"""

import re
from typing import Any, Tuple, Optional, Union

# Import internal formatting operations with fallback
try:
    from .._int.core.format_ops import (
        _format_data_structure,
        _format_timestamp,
        _interpolate_string,
        _create_debug_message,
        _set_debug_print_level,
        _get_debug_print_level,
        _should_print_debug,
        _get_current_time_formatted,
        _Colors,
        _FormatMode
    )
except ImportError:
    # Fallback implementations if internal module unavailable
    def _format_data_structure(obj, mode="display"):
        return str(obj)
    
    def _format_timestamp(timestamp, format_spec="time"):
        import time
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%H:%M:%S.%f")[:-3]
    
    def _interpolate_string(template, *args):
        return template
    
    def _create_debug_message(message, data=None, priority=1):
        import time
        timestamp = time.strftime("%H:%M:%S")
        return f"{message} - {timestamp}"
    
    def _set_debug_print_level(level):
        pass
    
    def _get_debug_print_level():
        return 1
    
    def _should_print_debug(priority):
        return True
    
    def _get_current_time_formatted(format_spec):
        import time
        import datetime
        dt = datetime.datetime.fromtimestamp(time.time())
        return dt.strftime("%H:%M:%S.%f")[:-3]
    
    class _Colors:
        RESET = ''
        @classmethod
        def enable(cls):
            pass
        @classmethod
        def disable(cls):
            pass
    
    class _FormatMode:
        DISPLAY = "display"
        DEBUG = "debug"


# ============================================================================
# Core Formatting Functions
# ============================================================================

def fprint(format_string: str, *values, mode: str = "display", **kwargs) -> None:
    """
    Smart formatted printing with custom interpolation and time specifiers.
    
    Supports both standard Python string formatting and custom time specifiers.
    Automatically formats complex data structures in a readable way.
    
    Args:
        format_string: Format string with placeholders and time specifiers
        *values: Values to interpolate into the format string
        mode: Formatting mode ("display" for clean, "debug" for verbose)
        **kwargs: Additional formatting options
        
    Examples:
        ```python
        # Basic formatting with beautiful data structures
        data = {"key1": "value1", "key2": [1, 2, 3]}
        fprint("Processing data: {}", data)
        
        # Time specifiers
        fprint("Report generated at {time:now}")
        fprint("Data from {date:now}")
        fprint("Precise timing: {hms6:now}")
        fprint("Timezone aware: {datePST:now}")
        
        # Mixed formatting
        results = [1, 2, 3, 4, 5]
        fprint("Analysis completed at {time:now}: {}", results)
        
        # Debug mode for detailed output
        fprint("Debug data: {}", data, mode="debug")
        ```
    """
    try:
        # Convert mode string to internal enum
        format_mode = _FormatMode.DEBUG if mode == "debug" else _FormatMode.DISPLAY
        
        # Handle time specifiers and basic interpolation
        processed_format = _interpolate_string(format_string, *values)
        
        # If we have values and no placeholders were filled, format them manually
        if values and '{}' in processed_format:
            # Format each value through our data structure formatter
            formatted_values = []
            for value in values:
                formatted_value = _format_data_structure(value, format_mode)
                formatted_values.append(formatted_value)
            
            # Replace {} placeholders with formatted values
            try:
                result = processed_format.format(*formatted_values)
            except (IndexError, ValueError):
                # Fallback if formatting fails
                result = processed_format + " " + " ".join(formatted_values)
        else:
            result = processed_format
        
        print(result)
        
    except Exception as e:
        # Graceful fallback for any formatting errors
        print(f"fprint error: {e}")
        print(f"Raw: {format_string} {values}")


def dprint(message: str, variables: Tuple = (), priority: int = 1, **kwargs) -> None:
    """
    Debug printing with priority levels and automatic timestamps.
    
    Automatically formats variables in debug mode and adds readable timestamps
    to every message. Supports priority-based filtering to reduce debug noise.
    
    Args:
        message: Debug message to display
        variables: Tuple of variables to format and display
        priority: Priority level (1-5, higher = more important)
        **kwargs: Additional formatting options
        
    Examples:
        ```python
        # Basic debug message with auto-timestamp
        dprint("Starting processing")
        # Output: "Starting processing - 14:23:45.123"
        
        # Debug with variables (automatically formatted)
        user_data = {"name": "Alice", "age": 30}
        config = ["setting1", "setting2"]
        dprint("User login", (user_data, config))
        # Output: "User login [(dict) {...}, (list) [...]] - 14:23:45.123"
        
        # Priority-based filtering
        dprint("Minor detail", (), 1)           # Low priority
        dprint("Important event", (), 3)        # Medium priority  
        dprint("Critical error", (), 5)         # High priority
        
        # Set filter level to hide low priority messages
        set_dprint_level(3)  # Only show priority 3+ messages
        ```
    """
    try:
        # Check if this message should be displayed based on priority
        if not _should_print_debug(priority):
            return
        
        # Create the debug message with formatted variables and timestamp
        debug_message = _create_debug_message(message, variables, priority)
        
        # Add priority indicator for high priority messages
        if priority >= 4:
            priority_indicator = f"[P{priority}] "
            debug_message = priority_indicator + debug_message
        
        print(debug_message)
        
    except Exception as e:
        # Graceful fallback
        print(f"dprint error: {e}")
        print(f"Raw: {message} {variables}")


# ============================================================================
# Configuration Functions
# ============================================================================

def set_dprint_level(level: int) -> None:
    """
    Set the minimum debug priority level to display.
    
    Messages with priority below this level will be filtered out.
    Useful for reducing debug noise in production or focusing on important messages.
    
    Args:
        level: Minimum priority level (1-5)
               1 = Show all messages (most verbose)
               2 = Hide minor details
               3 = Show important events only
               4 = Show critical events only  
               5 = Show only highest priority messages
               
    Examples:
        ```python
        # Show all debug messages (default)
        set_dprint_level(1)
        
        # Hide low priority noise, show important events
        set_dprint_level(3)
        
        # Only show critical messages
        set_dprint_level(5)
        
        # Test different priority levels
        dprint("Trace message", (), 1)      # Hidden if level > 1
        dprint("Info message", (), 2)       # Hidden if level > 2
        dprint("Warning message", (), 3)    # Hidden if level > 3
        dprint("Error message", (), 4)      # Hidden if level > 4
        dprint("Critical message", (), 5)   # Always shown
        ```
    """
    try:
        _set_debug_print_level(level)
        print(f"Debug level set to {level}")
    except Exception as e:
        print(f"Error setting debug level: {e}")


def enable_colors() -> None:
    """
    Enable color output for enhanced readability.
    
    Colors help distinguish between different data types and improve
    the visual hierarchy of formatted output.
    
    Examples:
        ```python
        enable_colors()
        
        # Now output will be colorized
        data = {"numbers": [1, 2, 3], "text": "hello"}
        fprint("Colorized output: {}", data)
        ```
    """
    try:
        _Colors.enable()
        print("Colors enabled")
    except Exception as e:
        print(f"Error enabling colors: {e}")


def disable_colors() -> None:
    """
    Disable color output for plain text display.
    
    Useful for file output, logging systems, or terminals that don't support colors.
    
    Examples:
        ```python
        disable_colors()
        
        # Output will be plain text without ANSI color codes
        data = {"numbers": [1, 2, 3], "text": "hello"}
        fprint("Plain output: {}", data)
        ```
    """
    try:
        _Colors.disable()
        print("Colors disabled")
    except Exception as e:
        print(f"Error disabling colors: {e}")


def get_config() -> dict:
    """
    Get current formatting configuration.
    
    Returns:
        Dictionary with current configuration settings
        
    Examples:
        ```python
        config = get_config()
        print(f"Debug level: {config.get('debug_level', 'unknown')}")
        ```
    """
    try:
        return {
            'debug_level': _get_debug_print_level(),
            'colors_enabled': True  # Assume enabled since we can't easily check
        }
    except Exception as e:
        return {'error': str(e)}


# ============================================================================
# Convenience Functions and Aliases
# ============================================================================

def fmt(obj: Any, mode: str = "display") -> str:
    """
    Format any object and return as string (without printing).
    
    Useful for getting formatted strings to use in other contexts.
    
    Args:
        obj: Object to format
        mode: Formatting mode ("display" or "debug")
        
    Returns:
        Formatted string representation
        
    Examples:
        ```python
        data = {"key": [1, 2, 3]}
        
        # Get formatted string for display
        display_str = fmt(data, "display") 
        
        # Get formatted string for debugging
        debug_str = fmt(data, "debug")
        
        # Use in other contexts
        with open("output.txt", "w") as f:
            f.write(f"Data: {display_str}\n")
        ```
    """
    try:
        format_mode = _FormatMode.DEBUG if mode == "debug" else _FormatMode.DISPLAY
        return _format_data_structure(obj, format_mode)
    except Exception as e:
        return f"Format error: {e}"


def debug_fmt(obj: Any) -> str:
    """
    Format object in debug mode and return as string.
    
    Convenience function equivalent to fmt(obj, "debug").
    
    Args:
        obj: Object to format
        
    Returns:
        Debug-formatted string representation
        
    Examples:
        ```python
        data = [1, 2, {"nested": "value"}]
        debug_output = debug_fmt(data)
        print(f"Debug view: {debug_output}")
        ```
    """
    return fmt(obj, "debug")


def timestamp(format_spec: str = "time") -> str:
    """
    Get current timestamp in specified format.
    
    Args:
        format_spec: Format specification ("time", "date", "datetime", "hms6", etc.)
        
    Returns:
        Formatted timestamp string
        
    Examples:
        ```python
        # Different time formats
        print(f"Time: {timestamp('time')}")        # 14:23:45.123
        print(f"Date: {timestamp('date')}")        # 2024-03-15
        print(f"Full: {timestamp('datetime')}")    # 2024-03-15 14:23:45
        print(f"Precise: {timestamp('hms6')}")     # 14:23:45.123456
        ```
    """
    try:
        return _get_current_time_formatted(format_spec)
    except Exception as e:
        return f"Timestamp error: {e}"


# ============================================================================
# Quick Debug Helpers
# ============================================================================

def quick_debug(*objects) -> None:
    """
    Quickly debug multiple objects with automatic formatting.
    
    Convenience function for rapid debugging of multiple variables.
    
    Args:
        *objects: Any number of objects to debug
        
    Examples:
        ```python
        user = {"name": "Bob"}
        items = [1, 2, 3]
        status = True
        
        # Debug multiple objects at once
        quick_debug(user, items, status)
        # Shows each object with debug formatting and timestamp
        ```
    """
    try:
        for i, obj in enumerate(objects):
            dprint(f"Object {i+1}", (obj,), 3)
    except Exception as e:
        print(f"Quick debug error: {e}")


def trace(*objects, message: str = "Trace") -> None:
    """
    Trace execution with formatted object output.
    
    Useful for tracking values at different points in code execution.
    
    Args:
        *objects: Objects to trace
        message: Trace message prefix
        
    Examples:
        ```python
        def process_data(data):
            trace(data, message="Input data")
            
            processed = transform(data)
            trace(processed, message="After transform")
            
            result = finalize(processed)
            trace(result, message="Final result")
            
            return result
        ```
    """
    try:
        dprint(message, objects, 3)
    except Exception as e:
        print(f"Trace error: {e}")


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Core functions
    'fprint',
    'dprint',
    
    # Configuration
    'set_dprint_level',
    'enable_colors',
    'disable_colors',
    'get_config',
    
    # Convenience functions
    'fmt',
    'debug_fmt',
    'timestamp',
    
    # Quick helpers
    'quick_debug',
    'trace',
]