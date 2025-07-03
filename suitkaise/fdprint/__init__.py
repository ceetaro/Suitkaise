"""
FDPrint - Smart Formatting and Debug Printing for Suitkaise

This module provides powerful formatting functionality that transforms ugly Python
data structures into beautiful, readable output while providing debugging
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

Usage Examples:
    ```python
    from suitkaise.fdprint import fprint, dprint
    
    # Clean, user-friendly output
    data = {"users": ["Alice", "Bob"], "count": 2}
    fprint("Processing: {}", data)
    
    # Debug output with type annotations and timestamps
    dprint("Debug info", (data,), 3)
    
    # Time specifiers
    fprint("Report generated at {time:now}")
    fprint("Date: {date:now}, Time: {hms6:now}")
    ```
"""

# Import all API functions and classes
from .api import (
    # Core functions
    fprint,
    dprint,
    
    # Configuration
    set_dprint_level,
    enable_colors,
    disable_colors,
    get_config,
    
    # Convenience functions
    fmt,
    debug_fmt,
    display_fmt,
    timestamp,
    
    # Quick helpers
    quick_debug,
    trace,
    quick_print,
)

# Re-export everything for direct import from module
__all__ = [
    # Core functions - the main API
    'fprint',      # Clean, user-friendly formatting
    'dprint',      # Debug formatting with type annotations
    
    # Configuration
    'set_dprint_level',
    'enable_colors',
    'disable_colors',
    'get_config',
    
    # Convenience functions
    'fmt',           # Format object to string (choose mode)
    'debug_fmt',     # Force debug mode formatting
    'display_fmt',   # Force display mode formatting
    'timestamp',     # Get formatted timestamps
    
    # Quick helpers
    'quick_debug',   # Quick debug multiple objects
    'trace',         # Trace execution with data
    'quick_print',   # Quick print multiple objects
]

# Module metadata
__version__ = "0.1.0"
__author__ = "Suitkaise Development Team"
__description__ = "Smart formatting and debug printing - Make ugly data beautiful"

# Module-level convenience - expose main functions at module level
# This allows: import suitkaise.fdprint; suitkaise.fdprint.fprint("Hello")
# Or: from suitkaise import fdprint; fdprint.fprint("Hello")
# Or: from suitkaise.fdprint import fprint; fprint("Hello")