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
    timestamp,
    
    # Quick helpers
    quick_debug,
    trace,
)

# Re-export everything for direct import from module
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

# Module-level convenience - expose main functions at module level
# This allows: import suitkaise.fdprint; suitkaise.fdprint.fprint("Hello")
__version__ = "0.1.0"
__author__ = "Suitkaise Development Team"