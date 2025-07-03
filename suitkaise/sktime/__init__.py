"""
SKTime - Smart Timing Operations for Suitkaise

This module provides intuitive timing functionality with statistical analysis,
sophisticated timing classes, and convenient decorators for performance measurement.

Key Features:
- Simple timing functions (now, sleep, elapsed)
- Yawn class for threshold-based delayed sleep operations
- Stopwatch with pause/resume and lap functionality  
- Timer for statistical timing analysis with context managers and decorators
- Comprehensive timing statistics and performance analysis

Philosophy: Make timing operations intuitive while providing powerful analysis capabilities.
"""

# Import all API functions and classes
from .api import (
    # Simple timing functions
    now,
    get_current_time, 
    sleep,
    elapsed,
    
    # Timing classes
    Yawn,
    Stopwatch,
    Timer,
    
    # Decorators
    timethis,
)

# Re-export everything for direct import from module
__all__ = [
    # Simple timing functions
    'now',
    'get_current_time', 
    'sleep',
    'elapsed',
    
    # Timing classes
    'Yawn',
    'Stopwatch',
    'Timer',
    
    # Decorators
    'timethis',
]

# Module-level convenience - expose main classes at module level
# This allows: import suitkaise.sktime; timer = suitkaise.sktime.Timer()
__version__ = "0.1.0"
__author__ = "Suitkaise Development Team"