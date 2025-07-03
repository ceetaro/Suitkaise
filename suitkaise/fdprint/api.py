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
        _create_debug_message_verbose,
        _set_debug_print_level,
        _get_debug_print_level,
        _should_print_debug,
        _get_current_time_formatted,
        _Colors,
        _FormatMode
    )
except ImportError:
    raise ImportError(
        "Internal format operations could not be imported. "
        "Ensure that the internal format operations module is available."
    )


# ============================================================================
# Core Formatting Functions
# ============================================================================

def fprint(format_string: str, *values, **kwargs) -> None:
    """
    Smart formatted printing with clean, user-friendly output.
    
    Always uses DISPLAY mode for clean, readable output without type annotations.
    Perfect for user-facing messages, logs, and general output.
    
    Args:
        format_string: Format string with placeholders and time specifiers
        *values: Values to interpolate into the format string
        **kwargs: Additional formatting options (reserved for future use)
        
    Examples:
        ```python
        # Clean, user-friendly output
        data = {"name": "Alice", "items": [1, 2, 3]}
        fprint("Processing: {}", data)
        # Output: Processing: name: Alice
        #                   items: 1, 2, 3
        
        # Time specifiers for timestamps
        fprint("Report generated at {time:now}")
        # Output: Report generated at 14:30:45
        
        # Mixed data and time
        fprint("Analysis at {time:now}: {}", results)
        ```
    """
    try:
        # ALWAYS use DISPLAY mode for clean output
        format_mode = _FormatMode.DISPLAY
        
        # Handle time specifiers first
        processed_format = re.sub(
            r'\{([^:}]+):now\}', 
            lambda m: _get_current_time_formatted(m.group(1)), 
            format_string
        )
        
        # Handle regular {} placeholders with values
        if values and '{}' in processed_format:
            # Format each value in clean display mode
            formatted_values = []
            for value in values:
                formatted_value = _format_data_structure(value, format_mode)
                formatted_values.append(formatted_value)
            
            # Replace {} placeholders with formatted values
            try:
                placeholder_count = processed_format.count('{}')
                values_to_use = formatted_values[:placeholder_count]
                result = processed_format.format(*values_to_use)
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
    Debug printing with verbose, detailed output and automatic timestamps.
    
    Always uses DEBUG mode for detailed output with type annotations and structure.
    Perfect for debugging, development, and detailed analysis.
    
    Args:
        message: Debug message to display
        variables: Tuple of variables to format and display in debug mode
        priority: Priority level (1-5, higher = more important)
        **kwargs: Additional formatting options (reserved for future use)
        
    Examples:
        ```python
        # Detailed debug output with timestamps
        user_data = {"name": "Alice", "age": 30}
        dprint("User login", (user_data,))
        # Output: User login [(dict) {
        #           (string) 'name': (string) 'Alice',
        #           (string) 'age': (integer) 30
        #         }] - 14:30:45.123
        
        # Priority-based filtering
        dprint("Minor detail", (), 1)           # Low priority
        dprint("Important event", (), 4)        # High priority with [P4] indicator
        ```
    """
    try:
        # Check if this message should be displayed based on priority
        if not _should_print_debug(priority):
            return
        
        # FIXED: Handle variables parameter more carefully
        if variables is None:
            variables = ()
        elif not isinstance(variables, (tuple, list)):
            variables = (variables,)  # Wrap single values in tuple
        
        # Create debug message with verbose formatting and timestamp
        debug_message = _create_debug_message_verbose(message, variables, priority)
        
        # Add priority indicator for high priority messages
        if priority >= 4:
            priority_indicator = f"[P{priority}] "
            debug_message = priority_indicator + debug_message
        
        print(debug_message)
        
    except Exception as e:
        # Graceful fallback - but still try to show something useful
        import time
        timestamp = time.strftime("%H:%M:%S")
        print(f"dprint error: {e}")
        print(f"Raw message: {message} - {timestamp}")
        if variables:
            print(f"Raw variables: {variables}")
        # ADDED: Show the actual error for debugging
        import traceback
        traceback.print_exc()


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
    
    Args:
        obj: Object to format
        mode: Formatting mode ("display" for clean, "debug" for verbose)
        
    Examples:
        ```python
        data = {"key": [1, 2, 3]}
        
        # Clean formatting (like fprint)
        clean = fmt(data, "display")
        
        # Verbose formatting (like dprint) 
        verbose = fmt(data, "debug")
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
    Same verbose formatting as dprint() but returns string instead of printing.
    
    Args:
        obj: Object to format
        
    Returns:
        Debug-formatted string representation (verbose with type annotations)
    """
    return fmt(obj, "debug")

def display_fmt(obj: Any) -> str:
    """
    Format object in display mode and return as string.
    
    Convenience function equivalent to fmt(obj, "display").
    Same clean formatting as fprint() but returns string instead of printing.
    
    Args:
        obj: Object to format
        
    Returns:
        Display-formatted string representation (clean, user-friendly)
    """
    return fmt(obj, "display")


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
    Quickly debug multiple objects with verbose formatting.
    
    Uses dprint() internally, so output is always in debug mode with type annotations.
    """
    try:
        for i, obj in enumerate(objects):
            dprint(f"Object {i+1}", (obj,), 2)  # Priority 2 for filtering
    except Exception as e:
        print(f"Quick debug error: {e}")


def trace(*objects, message: str = "Trace") -> None:
    """
    Trace execution with verbose object output.
    
    Uses dprint() internally, so output is always in debug mode with type annotations.
    """
    try:
        dprint(message, objects, 2)  # Priority 2 for filtering
    except Exception as e:
        print(f"Trace error: {e}")


def quick_print(*objects) -> None:
    """
    Quickly print multiple objects with clean formatting.
    
    Uses fprint() internally, so output is always in display mode (clean).
    Perfect for quick output without debug verbosity.
    """
    try:
        for i, obj in enumerate(objects):
            # FIXED: Use simple format string to avoid any placeholder conflicts
            fprint(f"Item {i + 1}: {{}}", obj)
    except Exception as e:
        print(f"Quick print error: {e}")



# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Core functions - now with clear separation
    'fprint',      # Always display mode (clean)
    'dprint',      # Always debug mode (verbose)
    
    # Configuration
    'set_dprint_level',
    'enable_colors',
    'disable_colors',
    'get_config',
    
    # Convenience functions
    'fmt',           # Choose mode explicitly
    'debug_fmt',     # Force debug mode
    'display_fmt',   # Force display mode (NEW)
    'timestamp',
    
    # Quick helpers
    'quick_debug',   # Verbose output via dprint
    'trace',         # Verbose output via dprint  
    'quick_print',   # Clean output via fprint (NEW)
]