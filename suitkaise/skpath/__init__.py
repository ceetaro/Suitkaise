"""
SKPath - Smart Path Operations for Suitkaise

This module provides intelligent path handling with dual-path architecture,
automatic project root detection, and magical caller detection.

Key Features:
- SKPath objects with absolute and normalized paths  
- Zero-configuration initialization with automatic caller detection
- AutoPath decorator for automatic path conversion
- Complete project structure analysis
- Path utilities with cross-module compatibility
"""

# Import all API functions and classes
from .api import *
from .api import __all__

# Module-level convenience - expose the main class at module level
# This allows: import suitkaise.skpath; then use skpath.SKPath() to get a SKPath object, for example.
__version__ = "0.1.2"
__author__ = "Suitkaise Development Team"