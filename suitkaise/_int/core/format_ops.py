"""
Complete Formatting Operations System for Suitkaise.

This module provides internal formatting functionality that powers the FDPrint module.
It includes sophisticated data structure formatting, time/date formatting, and 
debug output capabilities with color support and priority filtering.

Key Features:
- Dual-mode formatting: display (clean) vs debug (verbose with type info)
- Comprehensive time/date formatting with multiple format options
- Smart data type detection and appropriate formatting
- Color-coded output with visual hierarchy
- Priority-based debug filtering
- String interpolation with format specifiers

The internal operations handle all the complex formatting logic and visual styling.
"""

import time
import datetime
import re
import sys
from typing import Any, Dict, List, Set, Tuple, Union, Optional, Callable
from collections.abc import Mapping, Sequence
from enum import Enum


class _FormatMode(Enum):
    """Formatting mode enumeration."""
    DISPLAY = "display"  # Clean, user-friendly formatting
    DEBUG = "debug"      # Verbose with type annotations


class _Colors:
    """ANSI color codes for terminal output."""
    # Basic colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'
    
    # Data type colors
    TYPE_LABEL = '\033[36m'      # Cyan for type labels
    STRING_VAL = '\033[92m'      # Green for strings
    NUMBER_VAL = '\033[94m'      # Blue for numbers
    BOOL_VAL = '\033[95m'        # Magenta for booleans
    NONE_VAL = '\033[90m'        # Gray for None
    COLLECTION = '\033[93m'      # Yellow for collections
    TIME_VAL = '\033[96m'        # Cyan for timestamps
    
    _enabled = True
    
    @classmethod
    def enable(cls):
        """Enable color output."""
        cls._enabled = True
    
    @classmethod
    def disable(cls):
        """Disable color output (for file output, etc.)."""
        cls._enabled = False
        
    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not cls._enabled:
            return text
        return f"{color}{text}{cls.RESET}"


# Comprehensive time/date format specifications
_TIME_FORMATS = {
    # Basic time formats
    'time': '%H:%M:%S',                    # 14:30:45
    'time12': '%I:%M:%S %p',              # 02:30:45 PM  
    'hms': '%H:%M:%S',                    # 14:30:45
    'hm': '%H:%M',                        # 14:30
    'hms12': '%I:%M:%S %p',               # 02:30:45 PM
    'hm12': '%I:%M %p',                   # 02:30 PM
    
    # Time with microseconds
    'time6': '%H:%M:%S.%f',               # 14:30:45.123456
    'hms6': '%H:%M:%S.%f',                # 14:30:45.123456
    'time3': '%H:%M:%S',                  # Custom handler for milliseconds
    'hms3': '%H:%M:%S',                   # Custom handler for milliseconds
    
    # Basic date formats
    'date': '%Y-%m-%d',                   # 2024-03-15
    'dateiso': '%Y-%m-%d',                # 2024-03-15
    'dateus': '%m/%d/%Y',                 # 03/15/2024
    'dateeu': '%d/%m/%Y',                 # 15/03/2024
    'dateuk': '%d/%m/%Y',                 # 15/03/2024
    'dateshort': '%m/%d/%y',              # 03/15/24
    'datelong': '%B %d, %Y',              # March 15, 2024
    'dateword': '%A, %B %d, %Y',          # Friday, March 15, 2024
    
    # Combined datetime formats
    'datetime': '%Y-%m-%d %H:%M:%S',      # 2024-03-15 14:30:45
    'datetimeiso': '%Y-%m-%dT%H:%M:%S',   # 2024-03-15T14:30:45
    'dt': '%Y-%m-%d %H:%M:%S',            # 2024-03-15 14:30:45
    'dtiso': '%Y-%m-%dT%H:%M:%S',         # 2024-03-15T14:30:45
    'dtus': '%m/%d/%Y %I:%M:%S %p',       # 03/15/2024 02:30:45 PM
    'dteu': '%d/%m/%Y %H:%M:%S',          # 15/03/2024 14:30:45
    
    # Timezone-aware formats (will add timezone info programmatically)
    'timetz': '%H:%M:%S %Z',              # 14:30:45 PST
    'datetz': '%Y-%m-%d %Z',              # 2024-03-15 PST  
    'datetimetz': '%Y-%m-%d %H:%M:%S %Z', # 2024-03-15 14:30:45 PST
    'dttz': '%Y-%m-%d %H:%M:%S %Z',       # 2024-03-15 14:30:45 PST
    
    # Specific timezone formats
    'timepst': '%H:%M:%S PST',            # Custom handler
    'datepst': '%Y-%m-%d PST',            # Custom handler
    'datetimepst': '%Y-%m-%d %H:%M:%S PST', # Custom handler
    'timeest': '%H:%M:%S EST',            # Custom handler
    'dateest': '%Y-%m-%d EST',            # Custom handler
    'datetimeest': '%Y-%m-%d %H:%M:%S EST', # Custom handler
    'timeutc': '%H:%M:%S UTC',            # Custom handler
    'dateutc': '%Y-%m-%d UTC',            # Custom handler
    'datetimeutc': '%Y-%m-%d %H:%M:%S UTC', # Custom handler
    
    # Relative and special formats
    'timestamp': None,                    # Raw timestamp (custom handler)
    'epoch': None,                        # Raw timestamp (custom handler)
    'ago': None,                          # "5 minutes ago" (custom handler)
    'since': None,                        # "5 minutes ago" (custom handler)
    'elapsed': None,                      # Duration format (custom handler)
    'duration': None,                     # Duration format (custom handler)
    
    # Compact formats
    'compact': '%y%m%d_%H%M%S',           # 240315_143045
    'compactiso': '%Y%m%dT%H%M%S',        # 20240315T143045
    'filename': '%Y-%m-%d_%H-%M-%S',      # 2024-03-15_14-30-45
    
    # Log-friendly formats
    'log': '%Y-%m-%d %H:%M:%S.%f',        # 2024-03-15 14:30:45.123456
    'logshort': '%m-%d %H:%M:%S',         # 03-15 14:30:45
    'syslog': '%b %d %H:%M:%S',           # Mar 15 14:30:45
}


def _format_timestamp(timestamp: float, format_spec: str) -> str:
    """
    Format a timestamp according to the given format specification.
    
    Args:
        timestamp: Unix timestamp to format
        format_spec: Format specification string
        
    Returns:
        Formatted time string
    """
    if format_spec not in _TIME_FORMATS:
        # Try to use as direct strftime format
        try:
            dt = datetime.datetime.fromtimestamp(timestamp)
            return dt.strftime(format_spec)
        except (ValueError, TypeError):
            return str(timestamp)
    
    format_string = _TIME_FORMATS[format_spec]
    
    # Handle special cases that need custom logic
    if format_spec in ['timestamp', 'epoch']:
        return str(timestamp)
    
    elif format_spec in ['ago', 'since']:
        return _format_relative_time(timestamp)
    
    elif format_spec in ['elapsed', 'duration']:
        current_time = time.time()
        duration = abs(current_time - timestamp)
        return _format_duration(duration)
    
    elif format_spec in ['time3', 'hms3']:
        dt = datetime.datetime.fromtimestamp(timestamp)
        base_time = dt.strftime('%H:%M:%S')
        milliseconds = int((timestamp % 1) * 1000)
        return f"{base_time}.{milliseconds:03d}"
    
    elif format_spec.endswith('pst'):
        # Handle PST timezone (simplified - would need proper timezone handling in production)
        dt = datetime.datetime.fromtimestamp(timestamp)
        base_format = format_string.replace(' PST', '')
        return dt.strftime(base_format) + ' PST'
    
    elif format_spec.endswith('est'):
        # Handle EST timezone
        dt = datetime.datetime.fromtimestamp(timestamp)
        base_format = format_string.replace(' EST', '')
        return dt.strftime(base_format) + ' EST'
    
    elif format_spec.endswith('utc'):
        # Handle UTC timezone
        dt = datetime.datetime.utcfromtimestamp(timestamp)
        base_format = format_string.replace(' UTC', '')
        return dt.strftime(base_format) + ' UTC'
    
    else:
        # Standard strftime formatting
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime(format_string)


def _format_relative_time(timestamp: float) -> str:
    """Format timestamp as relative time (e.g., '5 minutes ago')."""
    current_time = time.time()
    diff = current_time - timestamp
    
    if diff < 0:
        diff = abs(diff)
        suffix = "from now"
    else:
        suffix = "ago"
    
    if diff < 60:
        return f"{int(diff)} seconds {suffix}"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} {suffix}"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} {suffix}"
    else:
        days = int(diff / 86400)
        return f"{days} day{'s' if days != 1 else ''} {suffix}"


def _format_duration(seconds: float) -> str:
    """Format seconds as duration string."""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        remaining_minutes = int((seconds % 3600) / 60)
        return f"{hours}h {remaining_minutes}m"
    else:
        days = int(seconds / 86400)
        remaining_hours = int((seconds % 86400) / 3600)
        return f"{days}d {remaining_hours}h"


def _get_current_time_formatted(format_spec: str) -> str:
    """Get current time in specified format."""
    current_timestamp = time.time()
    return _format_timestamp(current_timestamp, format_spec)


def _get_type_name(obj: Any) -> str:
    """Get clean type name for an object."""
    type_name = type(obj).__name__
    
    # Handle special cases for cleaner names
    if type_name == 'NoneType':
        return 'None'
    elif type_name == 'str':
        return 'string'
    elif type_name == 'int':
        return 'integer'
    elif type_name == 'float':
        return 'float'
    elif type_name == 'bool':
        return 'boolean'
    elif type_name == 'list':
        return 'list'
    elif type_name == 'dict':
        return 'dict'
    elif type_name == 'set':
        return 'set'
    elif type_name == 'tuple':
        return 'tuple'
    elif type_name == 'frozenset':
        return 'frozenset'
    elif type_name == 'bytes':
        return 'bytes'
    elif type_name == 'bytearray':
        return 'bytearray'
    elif type_name == 'complex':
        return 'complex'
    elif type_name == 'range':
        return 'range'
    else:
        return type_name


def _format_string_value(value: str, mode: _FormatMode) -> str:
    """Format string values with appropriate quoting."""
    if mode == _FormatMode.DEBUG:
        # In debug mode, show quotes and escape sequences
        repr_str = repr(value)
        return _Colors.colorize(repr_str, _Colors.STRING_VAL)
    else:
        # In display mode, show clean string without quotes
        return _Colors.colorize(value, _Colors.STRING_VAL)

def _format_number_value(value: Union[int, float, complex], mode: _FormatMode) -> str:
    """Format numeric values."""
    if isinstance(value, complex):
        # Special handling for complex numbers - preserve integer formatting
        real_part = int(value.real) if value.real.is_integer() else value.real
        imag_part = int(value.imag) if value.imag.is_integer() else value.imag
        
        if mode == _FormatMode.DEBUG:
            formatted = f"({real_part} + {imag_part}j)"
        else:
            formatted = f"{real_part} + {imag_part}j"
    else:
        formatted = str(value)
    
    return _Colors.colorize(formatted, _Colors.NUMBER_VAL)


def _format_boolean_value(value: bool, mode: _FormatMode) -> str:
    """Format boolean values."""
    return _Colors.colorize(str(value), _Colors.BOOL_VAL)


def _format_none_value(mode: _FormatMode) -> str:
    """Format None value."""
    return _Colors.colorize("None", _Colors.NONE_VAL)


def _format_bytes_value(value: Union[bytes, bytearray], mode: _FormatMode) -> str:
    """Format bytes/bytearray values."""
    try:
        # Try to decode as UTF-8 for display
        decoded = value.decode('utf-8')
        if mode == _FormatMode.DEBUG:
            return _Colors.colorize(f"b'{decoded}'", _Colors.STRING_VAL)
        else:
            return _Colors.colorize(decoded, _Colors.STRING_VAL)
    except UnicodeDecodeError:
        # If can't decode, show as hex
        hex_repr = value.hex()
        if mode == _FormatMode.DEBUG:
            return _Colors.colorize(f"b'\\x{hex_repr}'", _Colors.STRING_VAL)
        else:
            return _Colors.colorize(f"<{len(value)} bytes>", _Colors.STRING_VAL)


def _format_range_value(value: range, mode: _FormatMode) -> str:
    """Format range objects."""
    if mode == _FormatMode.DEBUG:
        return _Colors.colorize(f"range({value.start}, {value.stop}, {value.step})", _Colors.COLLECTION)
    else:
        # Show as start, stop for display mode
        return _Colors.colorize(f"{value.start}, {value.stop}", _Colors.COLLECTION)


def _format_list_display(items: List[Any], indent: int = 0) -> str:
    """Format list for display mode (comma-separated)."""
    if not items:
        return ""
    
    formatted_items = []
    for item in items:
        formatted_item = _format_single_value(item, _FormatMode.DISPLAY, indent)
        formatted_items.append(formatted_item)
    
    return ", ".join(formatted_items)


def _format_list_debug(items: List[Any], indent: int = 0) -> str:
    """Format list for debug mode (structured with type info)."""
    if not items:
        return "[]"
    
    indent_str = "    " * indent
    next_indent_str = "    " * (indent + 1)
    
    # Format items with proper indentation
    formatted_items = []
    for item in items:
        formatted_item = _format_single_value(item, _FormatMode.DEBUG, indent + 1)
        formatted_items.append(f"{next_indent_str}{formatted_item}")
    
    result = "[\n" + ",\n".join(formatted_items) + f"\n{indent_str}]"
    return _Colors.colorize(result, _Colors.COLLECTION)


def _format_dict_display(items: Dict[Any, Any], indent: int = 0) -> str:
    """Format dictionary for display mode."""
    if not items:
        return ""
    
    formatted_pairs = []
    for key, value in items.items():
        # Format key and value in display mode (no type annotations)
        key_str = _format_single_value(key, _FormatMode.DISPLAY, indent)
        value_str = _format_single_value(value, _FormatMode.DISPLAY, indent)
        formatted_pairs.append(f"{key_str}: {value_str}")
    
    # Join with newlines for readable output
    return "\n".join(formatted_pairs)


def _format_dict_debug(items: Dict[Any, Any], indent: int = 0) -> str:
    """Format dictionary for debug mode."""
    if not items:
        return "{}"
    
    indent_str = "    " * indent
    next_indent_str = "    " * (indent + 1)
    
    formatted_pairs = []
    for key, value in items.items():
        # Format key in debug mode (adds type annotation)
        key_str = _format_single_value(key, _FormatMode.DEBUG, indent + 1)
        # Format value in debug mode (adds type annotation)  
        value_str = _format_single_value(value, _FormatMode.DEBUG, indent + 1)
        # Combine with proper indentation
        formatted_pairs.append(f"{next_indent_str}{key_str}: {value_str}")

    result = "{\n" + ",\n".join(formatted_pairs) + f"\n{indent_str}}}"
    
    return _Colors.colorize(result, _Colors.COLLECTION)

def _format_set_display(items: Set[Any], indent: int = 0) -> str:
    """Format set for display mode."""
    if not items:
        return ""
    
    formatted_items = []
    for item in sorted(items, key=str):  # Sort for consistent output
        formatted_item = _format_single_value(item, _FormatMode.DISPLAY, indent)
        formatted_items.append(formatted_item)
    
    return ", ".join(formatted_items) if formatted_items else "set()"


def _format_set_debug(items: Set[Any], indent: int = 0) -> str:
    """Format set for debug mode."""
    if not items:
        return "set()"
    
    indent_str = "    " * indent
    next_indent_str = "    " * (indent + 1)
    
    formatted_items = []
    for item in sorted(items, key=str):  # Sort for consistent output
        formatted_item = _format_single_value(item, _FormatMode.DEBUG, indent + 1)
        formatted_items.append(f"{next_indent_str}{formatted_item}")
    
    result = "\n" + ",\n".join(formatted_items) + f"\n{indent_str}"
    return _Colors.colorize(result, _Colors.COLLECTION)


def _format_single_value(value: Any, mode: _FormatMode, indent: int = 0) -> str:
    """
    Format a single value according to the specified mode.
    
    Args:
        value: Value to format
        mode: Formatting mode (DISPLAY or DEBUG)
        indent: Current indentation level
        
    Returns:
        Formatted string representation
    """
    type_name = _get_type_name(value)
    
    # Handle None
    if value is None:
        formatted = _format_none_value(mode)
    
    # Handle strings
    elif isinstance(value, str):
        formatted = _format_string_value(value, mode)
    
    # Handle numbers
    elif isinstance(value, (int, float, complex)):
        formatted = _format_number_value(value, mode)
    
    # Handle booleans
    elif isinstance(value, bool):
        formatted = _format_boolean_value(value, mode)
    
    # Handle bytes/bytearray
    elif isinstance(value, (bytes, bytearray)):
        formatted = _format_bytes_value(value, mode)
    
    # Handle range
    elif isinstance(value, range):
        formatted = _format_range_value(value, mode)
    
    # Handle lists and tuples
    elif isinstance(value, (list, tuple)):
        if mode == _FormatMode.DISPLAY:
            content = _format_list_display(value, indent)
            if isinstance(value, tuple):
                formatted = f"({content})" if len(value) != 1 else f"({content},)"
            else:
                formatted = content
        else:
            content = _format_list_debug(value, indent)
            if isinstance(value, tuple):
                formatted = f"({content[1:-1]})" if content != "[]" else "()"
            else:
                formatted = content
    
    # Handle dictionaries
    elif isinstance(value, dict):
        if mode == _FormatMode.DISPLAY:
            formatted = _format_dict_display(value, indent)
        else:
            formatted = _format_dict_debug(value, indent)
    
    # Handle sets and frozensets
    elif isinstance(value, (set, frozenset)):
        if mode == _FormatMode.DISPLAY:
            formatted = _format_set_display(value, indent)
        else:
            formatted = _format_set_debug(value, indent)
    
    # Handle other types
    else:
        formatted = _Colors.colorize(str(value), _Colors.WHITE)
    
    # SINGLE TYPE ANNOTATION SECTION FOR DEBUG MODE
    if mode == _FormatMode.DEBUG:
        type_label = _Colors.colorize(f"({type_name})", _Colors.TYPE_LABEL)
        # Only add type label if it's not already there
        if not formatted.startswith(type_label):
            formatted = f"{type_label} {formatted}"
    
    return formatted

def _interpolate_string(template: str, *args) -> str:
    """
    Interpolate a template string with values and time format specifiers.
    """
    # Handle time format specifiers like {time:now}, {date:now}, etc.
    time_pattern = r'\{([^:}]+):now\}'
    
    def replace_time_spec(match):
        format_spec = match.group(1)
        return _get_current_time_formatted(format_spec)
    
    # Replace time specifications first
    result = re.sub(time_pattern, replace_time_spec, template)
    
    # Handle regular value interpolation
    if args:
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            values = args[0]
        else:
            values = args
        
        try:
            result = result.format(*values)
        except (IndexError, ValueError, KeyError):
            result = f"{template} {values}"
    
    return result


def _format_data_structure(data: Any, mode: _FormatMode = _FormatMode.DISPLAY) -> str:
    """
    Format any data structure according to the specified mode.
    
    Args:
        data: Data to format
        mode: Formatting mode
        
    Returns:
        Formatted string
    """
    return _format_single_value(data, mode, 0)


def _create_debug_message(message: str, data: Optional[Tuple[Any, ...]] = None, 
                         priority: int = 1) -> str:
    """
    Create a debug message with data formatting and timestamp.
    """
    # Format the base message
    result_parts = [message]
    
    # FIXED: Better handling of data
    if data is not None and len(data) > 0:
        formatted_data = []
        for item in data:
            try:
                formatted_item = _format_data_structure(item, _FormatMode.DEBUG)
                formatted_data.append(formatted_item)
            except Exception as e:
                # Handle formatting errors gracefully
                formatted_data.append(f"<error: {str(e)}>")
        
        if formatted_data:
            result_parts.append(" [")
            result_parts.append(", ".join(formatted_data))
            result_parts.append("]")
    
    # Add timestamp with error handling
    try:
        timestamp = _get_current_time_formatted('hms3')
        timestamp_colored = _Colors.colorize(timestamp, _Colors.TIME_VAL)
        result_parts.append(f" - {timestamp_colored}")
    except Exception as e:
        result_parts.append(f" - <time_error>")
    
    return "".join(result_parts)


# Global debug print level
_debug_print_level = 1


def _set_debug_print_level(level: int) -> None:
    """Set the global debug print level with validation."""
    global _debug_print_level
    
    # Clamp to valid range (1-5)
    if level < 1:
        level = 1
    elif level > 5:
        level = 5
    
    _debug_print_level = level


def _get_debug_print_level() -> int:
    """Get the current debug print level."""
    return _debug_print_level


def _should_print_debug(priority: int) -> bool:
    """Check if debug message should be printed based on priority."""
    return priority >= _debug_print_level