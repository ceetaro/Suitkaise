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
- Terminal-aware smart wrapping for dictionaries
- Value-over-key truncation with 40-character minimum width
- 2-space indentation per nesting level

The internal operations handle all the complex formatting logic and visual styling.
"""

import time
import datetime
import re
import sys
import shutil
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
    CYAN = '\033[38;5;117m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'
    
    # Data type colors
    TYPE_LABEL = '\033[38;5;117m'  # Soft blue-cyan for type labels
    STRING_VAL = '\033[92m'        # Green for strings
    NUMBER_VAL = '\033[94m'        # Blue for numbers
    BOOL_VAL = '\033[95m'          # Magenta for booleans (legacy)
    NONE_VAL = '\033[90m'          # Gray for None
    COLLECTION = '\033[93m'        # Yellow for collections
    TIME_VAL = '\033[38;5;117m'    # Soft blue-cyan for timestamps
    
    # Enhanced boolean colors
    BOOL_TRUE = '\033[1;32m'         # Bold green for True
    BOOL_FALSE = '\033[1;91m'        # Bold light red for False
    
    # Tuple and dictionary colors
    TUPLE_BRACKET = '\033[97m'       # White for tuple parentheses in display mode
    
    # Rainbow cycle colors for nested dictionary keys (all light/pastel)
    DICT_KEY_COLORS = [
        '\033[38;5;120m',  # Pastel green (#80ef80 equivalent)
        '\033[38;5;159m',  # Light cyan
        '\033[38;5;183m',  # Light magenta
        '\033[38;5;217m',  # Light red/pink
        '\033[38;5;223m',  # Light orange/peach
        '\033[38;5;228m',  # Light yellow
        '\033[38;5;147m',  # Light blue
    ]
    
    # Special formatting colors
    RANGE_STEP = '\033[2;37m'        # Dim gray for range step info
    BINARY_LABEL = '\033[2;37m'      # Dim gray for binary labels
    TRUNCATION_LABEL = '\033[38;5;207m'  # Neon pink for truncation indicators
    
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


def _get_terminal_width() -> int:
    """Get current terminal width with fallback and minimum width enforcement."""
    try:
        width = shutil.get_terminal_size().columns
        return max(width, 40)  # Minimum width of 40
    except:
        return 80  # Fallback to 80 columns


def _truncate_string(text: str, max_length: int) -> str:
    """Truncate string to max_length with ellipsis."""
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return "..."
    return text[:max_length-3] + "..."


def _clean_ansi(text: str) -> str:
    """Remove ANSI escape codes from text for length calculation."""
    return re.sub(r'\033\[[0-9;]*m', '', text)


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
        # Standard strftime formatting with 12-hour format cleanup
        dt = datetime.datetime.fromtimestamp(timestamp)
        result = dt.strftime(format_string)
        
        # Clean up 12-hour formats - remove leading zeros from hours
        if format_spec in ['hms12', 'hm12', 'time12']:
            # Replace leading zero in hour (e.g., "04:30 AM" -> "4:30 AM")
            result = re.sub(r'^0(\d)', r'\1', result)
        
        return result


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
    """Format numeric values with scientific notation for very large numbers."""
    if isinstance(value, int):
        # Format very large integers in scientific notation
        if abs(value) > 9_999_999_999:
            formatted = f"{value:.8g}"  # Use g format for automatic scientific notation
        else:
            formatted = str(value)
    elif isinstance(value, float):
        # Keep at least one decimal place for small floats
        if abs(value) < 0.01 and value != 0:
            # Format as scientific notation but ensure readable format with single space
            formatted = f"{value:.1e}".replace('e-0', ' e-').replace('e+0', ' e+').replace('e-', ' e-').replace('e+', ' e+')
            # Fix double spaces that might occur
            formatted = re.sub(r'  +', ' ', formatted)
        else:
            formatted = str(value)
    elif isinstance(value, complex):
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
    """Format boolean values with bold text and appropriate colors."""
    if value:
        return _Colors.colorize(str(value), _Colors.BOOL_TRUE)
    else:
        return _Colors.colorize(str(value), _Colors.BOOL_FALSE)


def _format_none_value(mode: _FormatMode) -> str:
    """Format None value."""
    return _Colors.colorize("None", _Colors.NONE_VAL)


def _format_bytes_value(value: Union[bytes, bytearray], mode: _FormatMode) -> str:
    """Format bytes/bytearray values with better binary handling."""
    try:
        # Try to decode as UTF-8 for display
        decoded = value.decode('utf-8')
        if mode == _FormatMode.DEBUG:
            return _Colors.colorize(f"b'{decoded}'", _Colors.STRING_VAL)
        else:
            return _Colors.colorize(decoded, _Colors.STRING_VAL)
    except UnicodeDecodeError:
        # If can't decode, show as hex with truncation
        if len(value) == 0:
            return _Colors.colorize("<empty bytes>", _Colors.STRING_VAL)
        
        # Show first 5 bytes as hex
        hex_parts = []
        show_count = min(5, len(value))
        for i in range(show_count):
            hex_parts.append(f"{value[i]:02x}")
        
        hex_display = ", ".join(hex_parts)
        
        # Add truncation indicator if needed
        if len(value) > 5:
            hex_display += f", ... (+{len(value) - 5} more)"
        
        # Add binary label
        binary_label = _Colors.colorize(" (binary)", _Colors.BINARY_LABEL)
        return _Colors.colorize(hex_display, _Colors.STRING_VAL) + binary_label


def _format_range_value(value: range, mode: _FormatMode) -> str:
    """Format range objects with step information."""
    if mode == _FormatMode.DEBUG:
        return _Colors.colorize(f"range({value.start}, {value.stop}, {value.step})", _Colors.COLLECTION)
    else:
        # Show as start, stop for display mode
        base = _Colors.colorize(f"{value.start}, {value.stop}", _Colors.COLLECTION)
        if value.step != 1:
            step_info = _Colors.colorize(f" (+{value.step})", _Colors.RANGE_STEP)
            return base + step_info
        return base


def _format_list_display(items: List[Any], indent: int = 0, available_width: int = None, nesting_level: int = 0, use_rainbow: bool = False) -> str:
    """Format list for display mode with optional rainbow coloring for sub-items."""
    if not items:
        return ""
    
    # Truncate long lists to 5 items
    if len(items) > 5:
        display_items = items[:5]
        truncated = True
        remaining_count = len(items) - 5
    else:
        display_items = items
        truncated = False
        remaining_count = 0
    
    formatted_items = []
    for i, item in enumerate(display_items):
        if use_rainbow and isinstance(item, (list, tuple)):
            # Use rainbow colors for sub-lists/tuples - each gets a different color
            rainbow_color = _get_dict_key_color(i)
            if isinstance(item, list):
                # Format sub-list items with the rainbow color
                sub_items = []
                for sub_item in item:
                    sub_formatted = _format_single_value(sub_item, _FormatMode.DISPLAY, indent + 1, nesting_level)
                    # Apply rainbow color to the entire sub-item
                    sub_items.append(_Colors.colorize(str(sub_item), rainbow_color))
                formatted_item = ", ".join(sub_items)
            elif isinstance(item, tuple):
                # Format tuple items with the rainbow color
                sub_items = []
                for sub_item in item:
                    sub_items.append(_Colors.colorize(str(sub_item), rainbow_color))
                formatted_item = _Colors.colorize("(", _Colors.TUPLE_BRACKET) + ", ".join(sub_items) + _Colors.colorize(")", _Colors.TUPLE_BRACKET)
            else:
                formatted_item = _format_single_value(item, _FormatMode.DISPLAY, indent, nesting_level)
        else:
            formatted_item = _format_single_value(item, _FormatMode.DISPLAY, indent, nesting_level)
        formatted_items.append(formatted_item)
    
    result = ", ".join(formatted_items)
    
    if truncated:
        truncation_text = _Colors.colorize(f" ...({remaining_count} more)", _Colors.TRUNCATION_LABEL)
        result += truncation_text
    
    return result


def _format_list_debug(items: List[Any], indent: int = 0) -> str:
    """Format list for debug mode (structured with type info)."""
    if not items:
        return "[]"
    
    indent_str = "  " * indent  # 2 spaces per level
    next_indent_str = "  " * (indent + 1)
    
    # Format items with proper indentation
    formatted_items = []
    for item in items:
        formatted_item = _format_single_value(item, _FormatMode.DEBUG, indent + 1)
        formatted_items.append(f"{next_indent_str}{formatted_item}")
    
    result = "[\n" + ",\n".join(formatted_items) + f"\n{indent_str}]"
    return _Colors.colorize(result, _Colors.COLLECTION)


def _format_tuple_display(items: Tuple[Any, ...], indent: int = 0, available_width: int = None) -> str:
    """Format tuple for display mode with colored parentheses."""
    if not items:
        return _Colors.colorize("()", _Colors.TUPLE_BRACKET)
    
    # Format the contents
    formatted_items = []
    for item in items:
        formatted_item = _format_single_value(item, _FormatMode.DISPLAY, indent)
        formatted_items.append(formatted_item)
    
    content = ", ".join(formatted_items)
    
    # Handle single item tuple
    if len(items) == 1:
        content += ","
    
    # Add colored parentheses
    open_paren = _Colors.colorize("(", _Colors.TUPLE_BRACKET)
    close_paren = _Colors.colorize(")", _Colors.TUPLE_BRACKET)
    
    return f"{open_paren}{content}{close_paren}"


def _get_dict_key_color(nesting_level: int) -> str:
    """Get the appropriate color for dictionary keys based on nesting level."""
    return _Colors.DICT_KEY_COLORS[nesting_level % len(_Colors.DICT_KEY_COLORS)]


def _format_dict_display(items: Dict[Any, Any], indent: int = 0, prefix_length: int = 0, nesting_level: int = 0) -> str:
    """Format dictionary with smart terminal-width wrapping, 2-space indentation, and rainbow key colors."""
    if not items:
        return ""
    
    # Get terminal width and calculate available space
    terminal_width = _get_terminal_width()
    # Subtract 2 spaces per indentation level
    indent_space = indent * 2
    available_width = terminal_width - prefix_length - indent_space
    
    # Minimum usable width of 40
    if available_width < 40:
        available_width = 40
    
    formatted_pairs = []
    
    # Get the key color for this nesting level
    key_color = _get_dict_key_color(nesting_level)
    
    for key, value in items.items():
        # Format key with current level color (and color the colon too)
        key_str = _Colors.colorize(str(key), key_color)
        colon_str = _Colors.colorize(":", key_color)
        
        # Format value with potential truncation
        if isinstance(value, dict):
            # Handle nested dictionaries with increased nesting level
            nested_pairs = []
            next_nesting_level = nesting_level + 1
            for nested_key, nested_value in value.items():
                nested_key_color = _get_dict_key_color(next_nesting_level)
                nested_key_str = _Colors.colorize(str(nested_key), nested_key_color)
                nested_colon_str = _Colors.colorize(":", nested_key_color)
                nested_value_str = _format_single_value(nested_value, _FormatMode.DISPLAY, indent + 1, next_nesting_level)
                nested_pairs.append(f"{nested_key_str}{nested_colon_str} {nested_value_str}")
            value_str = ", ".join(nested_pairs)
        elif isinstance(value, list):
            # Check if this is a list of lists (like the big list case)
            if value and isinstance(value[0], (list, tuple)):
                # Use rainbow coloring for sub-lists
                value_str = _format_list_display(value, indent + 1, available_width, nesting_level, use_rainbow=True)
            else:
                # Regular list formatting
                value_str = _format_list_display(value, indent + 1, available_width, nesting_level)
        elif isinstance(value, tuple):
            value_str = _format_tuple_display(value, indent + 1, available_width, nesting_level)
        elif isinstance(value, set):
            value_str = _format_set_display(value, indent + 1, nesting_level)
        else:
            # Handle simple values
            value_str = _format_single_value(value, _FormatMode.DISPLAY, indent + 1, nesting_level)
        
        # Create the key-value pair with colored colon
        pair = f"{key_str}{colon_str} {value_str}"
        
        # Check if this pair fits in available width
        clean_pair = _clean_ansi(pair)
        
        if len(clean_pair) > available_width:
            # Truncate the value part (prioritize key over value)
            key_part = f"{key_str}{colon_str} "
            clean_key_part = _clean_ansi(key_part)
            value_space = available_width - len(clean_key_part) - 3  # 3 for "..."
            
            if value_space > 5:  # Only truncate if we have reasonable space
                # Truncate the clean value and reapply basic formatting
                clean_value = _clean_ansi(value_str)
                truncated_value = _truncate_string(clean_value, value_space)
                # Note: We lose the original coloring, but that's acceptable for truncated values
                pair = f"{key_str}{colon_str} {truncated_value}"
        
        formatted_pairs.append(pair)
    
    # Join pairs with commas and check for line wrapping
    result = ", ".join(formatted_pairs)
    
    # If the entire result is too long, format it with line breaks
    clean_result = _clean_ansi(result)
    if len(clean_result) > available_width:
        # Format with line breaks for better readability
        lines = []
        current_line = ""
        indent_str = "  " * (indent + 1)  # 2 spaces per level
        
        for i, pair in enumerate(formatted_pairs):
            clean_pair = _clean_ansi(pair)
            
            # Check if adding this pair would exceed the width
            if current_line and len(_clean_ansi(current_line + ", " + pair)) > available_width:
                # Add current line and start a new one
                lines.append(current_line)
                current_line = f"{indent_str}{pair}"
            elif current_line:
                current_line += f", {pair}"
            else:
                if i == 0:
                    # First item doesn't need indentation
                    current_line = pair
                else:
                    current_line = f"{indent_str}{pair}"
        
        # Add the last line
        if current_line:
            lines.append(current_line)
        
        result = "\n".join(lines)
    
    return result


def _format_dict_debug(items: Dict[Any, Any], indent: int = 0) -> str:
    """Format dictionary for debug mode."""
    if not items:
        return "{}"
    
    indent_str = "  " * indent  # 2 spaces per level
    next_indent_str = "  " * (indent + 1)
    
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
    
    indent_str = "  " * indent  # 2 spaces per level
    next_indent_str = "  " * (indent + 1)
    
    formatted_items = []
    for item in sorted(items, key=str):  # Sort for consistent output
        formatted_item = _format_single_value(item, _FormatMode.DEBUG, indent + 1)
        formatted_items.append(f"{next_indent_str}{formatted_item}")
    
    result = "\n" + ",\n".join(formatted_items) + f"\n{indent_str}"
    return _Colors.colorize(result, _Colors.COLLECTION)


def _format_single_value(value: Any, mode: _FormatMode, indent: int = 0, nesting_level: int = 0) -> str:
    """
    Format a single value according to the specified mode.
    
    Args:
        value: Value to format
        mode: Formatting mode (DISPLAY or DEBUG)
        indent: Current indentation level (used for nested structures)
        nesting_level: Current dictionary nesting level for rainbow colors
        
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
    
    # Handle lists
    elif isinstance(value, list):
        if mode == _FormatMode.DISPLAY:
            # Check if this is a list of lists for rainbow coloring
            use_rainbow = value and isinstance(value[0], (list, tuple))
            formatted = _format_list_display(value, indent, None, nesting_level, use_rainbow)
        else:
            formatted = _format_list_debug(value, indent)
    
    # Handle tuples
    elif isinstance(value, tuple):
        if mode == _FormatMode.DISPLAY:
            formatted = _format_tuple_display(value, indent, None, nesting_level)
        else:
            content = _format_list_debug(list(value), indent)
            if content != "[]":
                formatted = f"({content[1:-1]})" if len(value) != 1 else f"({content[1:-1]},)"
            else:
                formatted = "()"
    
    # Handle dictionaries
    elif isinstance(value, dict):
        if mode == _FormatMode.DISPLAY:
            formatted = _format_dict_display(value, indent, 0, nesting_level)
        else:
            formatted = _format_dict_debug(value, indent)
    
    # Handle sets and frozensets
    elif isinstance(value, (set, frozenset)):
        if mode == _FormatMode.DISPLAY:
            formatted = _format_set_display(value, indent, nesting_level)
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


def _format_data_structure(data: Any, mode: _FormatMode = _FormatMode.DISPLAY, prefix_length: int = 0) -> str:
    """
    Format any data structure according to the specified mode.
    
    Args:
        data: Data to format
        mode: Formatting mode
        prefix_length: Length of prefix text for width calculation
        
    Returns:
        Formatted string
    """
    if isinstance(data, dict) and mode == _FormatMode.DISPLAY:
        # For dictionaries in display mode, use the full formatting with width awareness
        return _format_dict_display(data, 0, prefix_length, 0)
    else:
        # For other types or debug mode, use the regular formatting
        return _format_single_value(data, mode, 0, 0)


def _create_debug_message(message: str, data: Optional[Tuple[Any, ...]] = None, 
                                 priority: int = 1) -> str:
    """
    Create a debug message with verbose formatting and timestamp.
    
    Always uses DEBUG mode for maximum detail and type information.
    """
    # Format the base message
    result_parts = [message]
    
    # Format data with verbose DEBUG mode
    if data is not None and len(data) > 0:
        formatted_data = []
        for item in data:
            try:
                # ALWAYS use DEBUG mode for maximum verbosity
                formatted_item = _format_data_structure(item, _FormatMode.DEBUG)
                formatted_data.append(formatted_item)
            except Exception as e:
                # Handle formatting errors gracefully
                formatted_data.append(f"<format_error: {type(item).__name__}>")
        
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
        # Fallback to simple timestamp
        import time
        simple_time = time.strftime("%H:%M:%S")
        result_parts.append(f" - {simple_time}")
    
    return "".join(result_parts)


def _create_debug_message_verbose(message: str, data: Optional[Tuple[Any, ...]] = None, 
                                 priority: int = 1) -> str:
    """
    Create a debug message with verbose formatting and timestamp.
    
    This is specifically for dprint() and always uses DEBUG mode for maximum detail.
    Different from _create_debug_message() in that it ALWAYS forces debug mode.
    
    Args:
        message: Debug message text
        data: Tuple of data to format in debug mode
        priority: Priority level
        
    Returns:
        Formatted debug message with verbose output and timestamp
    """
    # Format the base message
    result_parts = [message]
    
    # Format data with verbose DEBUG mode (ALWAYS)
    if data is not None and len(data) > 0:
        formatted_data = []
        for item in data:
            try:
                # ALWAYS use DEBUG mode for maximum verbosity in dprint
                formatted_item = _format_data_structure(item, _FormatMode.DEBUG)
                formatted_data.append(formatted_item)
            except Exception as e:
                # Handle formatting errors gracefully
                formatted_data.append(f"<format_error: {type(item).__name__}>")
        
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
        # Fallback to simple timestamp
        import time
        simple_time = time.strftime("%H:%M:%S")
        result_parts.append(f" - {simple_time}")
    
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