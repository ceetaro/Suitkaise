"""
────────────────────────────────────────────────────────
    ```python
    from suitkaise import TimeThis
    from suitkaise.timing import TimeThis, Sktimer
    ```
────────────────────────────────────────────────────────\n

Timing - Smart Timing Operations for Suitkaise

This module provides intuitive timing functionality with statistical analysis,
sophisticated timing classes, and convenient decorators for performance measurement.

Key Features:
- Simple timing functions (time, sleep, elapsed)
- Sktimer for statistical timing analysis with pause/resume and lap functionality
- TimeThis context manager for convenient timing of code blocks
- Comprehensive timing statistics and performance analysis

Philosophy: Make timing operations intuitive while providing powerful analysis capabilities.
"""

# Import all API functions and classes
from .api import *
from .api import __all__

# Module-level convenience - expose main classes at module level
# This allows: import suitkaise.timing; timer = suitkaise.timing.Sktimer()
__version__ = "0.3.0"
__author__ = "Suitkaise Development Team"