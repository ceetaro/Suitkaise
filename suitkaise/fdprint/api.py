"""
FDPrint API - Smart Formatting and Debug Printing for Suitkaise

This module provides user-friendly formatting functionality that transforms ugly Python
data structures into beautiful, readable output while providing powerful debugging
capabilities with automatic timestamping and priority-based filtering.

Key Features:
- fprint(): Smart formatted printing with custom interpolation and time specifiers
- dprint(): Debug printing with priority levels and automatic timestamps
- Dual formatting modes: Display (clean) and Debug (verbose with type annotations)
- Color-coded output with enhanced readability
- Time/date formatting with custom specifiers (time:now, date:now, hms6:now, etc.)
- Priority-based debug message filtering
- Terminal-aware smart wrapping with dynamic width detection
- Rainbow color cycling for nested dictionary keys
- Rainbow color grouping for lists of sub-lists
- Scientific notation for very large numbers (>9.9 billion)
- Enhanced boolean colors (bold green/red)
- Neon pink truncation indicators

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
    Smart formatted printing with clean, user-friendly output and terminal-aware formatting.
    
    Always uses DISPLAY mode for clean, readable output without type annotations.
    Perfect for user-facing messages, logs, and general output with enhanced visual hierarchy.
    
    Args:
        format_string: Format string with placeholders and time specifiers
        *values: Values to interpolate into the format string
        **kwargs: Additional formatting options (reserved for future use)
        
    Enhanced Features:
        - Terminal width detection with 40-character minimum
        - Smart wrapping for dictionaries with 2-space indentation per level
        - Rainbow color cycling for nested dictionary keys (pastel green → cyan → magenta → red → orange → yellow → blue)
        - Rainbow grouping for lists containing sub-lists
        - Scientific notation for integers > 9,999,999,999
        - Bold green True / bold red False booleans
        - Neon pink truncation indicators
        - Value-over-key truncation priority
        - 12-hour time format without leading zeros (4:30 AM not 04:30 AM)
        
    Examples:
        ```python
        # Clean, user-friendly output with rainbow key colors
        data = {"user": {"name": "Alice", "details": {"age": 30, "city": "NYC"}}}
        fprint("Processing: {}", data)
        # Output: Processing: user: name: Alice, details: age: 30, city: NYC
        #         (user=pastel green, name/details=cyan, age/city=magenta)
        
        # Large lists with rainbow sub-list grouping
        big_list = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        fprint("Data groups: {}", big_list)
        # Output: Data groups: 1, 2, 3, 4, 5, 6, 7, 8, 9
        #         (each [1,2,3] group in different rainbow color)
        
        # Time specifiers with soft blue-cyan timestamps
        fprint("Report generated at {time:now}")
        # Output: Report generated at 14:30:45 (in soft blue-cyan)
        
        # Terminal-aware wrapping
        fprint("Long data: {}", very_long_dictionary)
        # Automatically wraps based on your current terminal width
        
        # Enhanced number formatting
        fprint("Large number: {}", 12345678901)
        # Output: Large number: 1.23457e+10
        
        # Enhanced boolean colors
        fprint("Status: {} Active: {}", True, False)
        # Output: Status: True Active: False (True=bold green, False=bold red)
        ```
    """
    try:
        # ALWAYS use DISPLAY mode for clean output
        format_mode = _FormatMode.DISPLAY
        
        # Handle time specifiers first with soft blue-cyan coloring
        def replace_time_spec(match):
            format_spec = match.group(1)
            formatted_time = _get_current_time_formatted(format_spec)
            return _Colors.colorize(formatted_time, _Colors.TIME_VAL)
        
        processed_format = re.sub(
            r'\{([^:}]+):now\}', 
            replace_time_spec,
            format_string
        )
        
        # Handle regular {} placeholders with values
        if values and '{}' in processed_format:
            # Calculate prefix length for the first value (for terminal-aware wrapping)
            prefix_parts = processed_format.split('{}', 1)
            prefix_length = len(re.sub(r'\033\[[0-9;]*m', '', prefix_parts[0])) if prefix_parts else 0
            
            # Format each value in clean display mode with width awareness
            formatted_values = []
            for i, value in enumerate(values):
                # Pass prefix length for first value only (for smart wrapping)
                current_prefix = prefix_length if i == 0 else 0
                formatted_value = _format_data_structure(value, format_mode, current_prefix)
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
    Perfect for debugging, development, and detailed analysis with enhanced formatting.
    
    Args:
        message: Debug message to display
        variables: Tuple of variables to format and display in debug mode
        priority: Priority level (1-5, higher = more important)
        **kwargs: Additional formatting options (reserved for future use)
        
    Enhanced Features:
        - Soft blue-cyan timestamps (instead of bright cyan)
        - Enhanced type annotations with better colors
        - Scientific notation for very large numbers
        - Bold boolean colors (green True, red False)
        - Detailed structure formatting with proper indentation
        
    Examples:
        ```python
        # Detailed debug output with enhanced timestamps
        user_data = {"name": "Alice", "age": 30, "active": True}
        dprint("User login", (user_data,))
        # Output: User login [(dict) {
        #           (string) 'name': (string) 'Alice',
        #           (string) 'age': (integer) 30,
        #           (string) 'active': (boolean) True
        #         }] - 14:30:45.123 (timestamp in soft blue-cyan)
        
        # Priority-based filtering with indicators
        dprint("Minor detail", (), 1)           # Low priority
        dprint("Important event", (), 4)        # [P4] Important event - timestamp
        dprint("Critical error", (), 5)         # [P5] Critical error - timestamp
        
        # Enhanced number formatting in debug mode
        large_num = 15000000000
        dprint("Processing", (large_num,))
        # Output: Processing [(integer) 1.5e+10] - timestamp
        
        # Enhanced boolean debugging
        status = {"connected": True, "authenticated": False}
        dprint("Connection status", (status,))
        # Shows booleans in bold green/red with type annotations
        ```
    """
    try:
        # Check if this message should be displayed based on priority
        if not _should_print_debug(priority):
            return
        
        # Handle variables parameter more carefully
        if variables is None:
            variables = ()
        elif not isinstance(variables, (tuple, list)):
            variables = (variables,)  # Wrap single values in tuple
        
        # Create debug message with verbose formatting and enhanced timestamp
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
        # Show the actual error for debugging
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
    the visual hierarchy of formatted output. Enhanced with rainbow
    cycling and improved color choices.
    
    Examples:
        ```python
        enable_colors()
        
        # Now output will be colorized with enhanced palette
        data = {"numbers": [1, 2, 3], "text": "hello", "flag": True}
        fprint("Colorized output: {}", data)
        # Keys in pastel green, numbers in blue, text in green, True in bold green
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
    Rainbow grouping and structure remain intact without color codes.
    
    Examples:
        ```python
        disable_colors()
        
        # Output will be plain text without ANSI color codes
        data = {"numbers": [1, 2, 3], "text": "hello"}
        fprint("Plain output: {}", data)
        # Still properly formatted, just without colors
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
        Dictionary with current configuration settings including
        debug level, colors status, and terminal width info
        
    Examples:
        ```python
        config = get_config()
        print(f"Debug level: {config.get('debug_level', 'unknown')}")
        print(f"Colors enabled: {config.get('colors_enabled', 'unknown')}")
        ```
    """
    try:
        import shutil
        return {
            'debug_level': _get_debug_print_level(),
            'colors_enabled': _Colors._enabled,
            'terminal_width': shutil.get_terminal_size().columns,
            'min_width': 40,
            'features': [
                'rainbow_keys',
                'rainbow_lists',
                'terminal_aware_wrapping',
                'scientific_notation',
                'enhanced_booleans',
                'neon_pink_truncation'
            ]
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
        mode: Formatting mode ("display" for clean with rainbow colors, "debug" for verbose)
        
    Examples:
        ```python
        data = {"user": {"name": "Alice", "items": [1, 2, 3]}}
        
        # Clean formatting with rainbow key colors
        clean = fmt(data, "display")
        # Returns: user: name: Alice, items: 1, 2, 3 (with rainbow colors)
        
        # Verbose formatting with type annotations
        verbose = fmt(data, "debug")
        # Returns: (dict) { (string) 'user': (dict) { ... } }
        ```
    """
    try:
        format_mode = _FormatMode.DEBUG if mode == "debug" else _FormatMode.DISPLAY
        return _format_data_structure(obj, format_mode, 0)
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
        
    Examples:
        ```python
        data = {"active": True, "count": 12345678901}
        debug_str = debug_fmt(data)
        # Returns detailed debug representation with type info
        ```
    """
    return fmt(obj, "debug")


def display_fmt(obj: Any) -> str:
    """
    Format object in display mode and return as string.
    
    Convenience function equivalent to fmt(obj, "display").
    Same clean formatting as fprint() but returns string instead of printing.
    Includes rainbow key colors and enhanced formatting.
    
    Args:
        obj: Object to format
        
    Returns:
        Display-formatted string representation (clean, user-friendly with colors)
        
    Examples:
        ```python
        nested_data = {"level1": {"level2": {"level3": "deep"}}}
        display_str = display_fmt(nested_data)
        # Returns clean representation with rainbow key hierarchy
        ```
    """
    return fmt(obj, "display")


def timestamp(format_spec: str = "time") -> str:
    """
    Get current timestamp in specified format with enhanced color support.
    
    Args:
        format_spec: Format specification ("time", "date", "datetime", "hms6", etc.)
        
    Returns:
        Formatted timestamp string (colored if colors enabled)
        
    Examples:
        ```python
        # Different time formats (all in soft blue-cyan if colors enabled)
        print(f"Time: {timestamp('time')}")        # 14:23:45
        print(f"Date: {timestamp('date')}")        # 2024-03-15
        print(f"Full: {timestamp('datetime')}")    # 2024-03-15 14:23:45
        print(f"Precise: {timestamp('hms6')}")     # 14:23:45.123456
        print(f"12-hour: {timestamp('hm12')}")     # 2:23 PM (no leading zero)
        ```
    """
    try:
        formatted_time = _get_current_time_formatted(format_spec)
        # Apply color if this is being called standalone
        return _Colors.colorize(formatted_time, _Colors.TIME_VAL)
    except Exception as e:
        return f"Timestamp error: {e}"


# ============================================================================
# Enhanced Quick Debug Helpers
# ============================================================================

def quick_debug(*objects) -> None:
    """
    Quickly debug multiple objects with verbose formatting and enhanced colors.
    
    Uses dprint() internally, so output includes type annotations, enhanced
    boolean colors, scientific notation, and soft blue-cyan timestamps.
    """
    try:
        for i, obj in enumerate(objects):
            dprint(f"Object {i+1}", (obj,), 2)  # Priority 2 for filtering
    except Exception as e:
        print(f"Quick debug error: {e}")


def trace(*objects, message: str = "Trace") -> None:
    """
    Trace execution with verbose object output and enhanced formatting.
    
    Uses dprint() internally with all enhanced features including rainbow
    colors for nested structures and improved type visibility.
    """
    try:
        dprint(message, objects, 2)  # Priority 2 for filtering
    except Exception as e:
        print(f"Trace error: {e}")


def quick_print(*objects) -> None:
    """
    Quickly print multiple objects with clean formatting and rainbow colors.
    
    Uses fprint() internally, so output includes rainbow key cycling,
    terminal-aware wrapping, and all enhanced display features.
    """
    try:
        for i, obj in enumerate(objects):
            fprint(f"Item {i + 1}: {{}}", obj)
    except Exception as e:
        print(f"Quick print error: {e}")


def rainbow_demo() -> None:
    """
    Demonstrate rainbow color cycling and enhanced formatting features.
    
    Shows examples of nested dictionaries with rainbow key colors,
    lists with rainbow sub-grouping, and enhanced number/boolean formatting.
    """
    try:
        print("🌈 Rainbow Color Demo:")
        
        # Nested dictionary with rainbow keys
        nested_dict = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "deep nesting"
                    }
                }
            }
        }
        fprint("Nested rainbow keys: {}", nested_dict)
        
        # List of sub-lists with rainbow grouping
        grouped_list = [[1, 2, 3], [4, 5, 6], [7, 8, 9], ["a", "b", "c"]]
        fprint("Rainbow grouped lists: {}", grouped_list)
        
        # Enhanced numbers and booleans
        enhanced_data = {
            "large_number": 15000000000,
            "small_float": 0.000001,
            "success": True,
            "error": False
        }
        fprint("Enhanced formatting: {}", enhanced_data)
        
        print("✨ Demo complete!")
        
    except Exception as e:
        print(f"Demo error: {e}")


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Core functions with enhanced formatting
    'fprint',      # Clean display mode with rainbow colors and terminal awareness
    'dprint',      # Verbose debug mode with enhanced colors and timestamps
    
    # Configuration
    'set_dprint_level',
    'enable_colors',
    'disable_colors',
    'get_config',
    
    # Convenience functions
    'fmt',           # Choose mode explicitly with enhanced features
    'debug_fmt',     # Force debug mode with type annotations
    'display_fmt',   # Force display mode with rainbow colors
    'timestamp',     # Enhanced timestamp with color support
    
    # Enhanced quick helpers
    'quick_debug',   # Verbose output with enhanced debug features
    'trace',         # Verbose tracing with rainbow formatting
    'quick_print',   # Clean output with rainbow colors and terminal awareness
    'rainbow_demo',  # Demonstrate rainbow and enhanced features
]