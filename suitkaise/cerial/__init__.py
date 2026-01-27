"""
────────────────────────────────────────────────────────
    ```python
    from suitkaise import cerial
    ```
────────────────────────────────────────────────────────\n

Cerial - Serialization for the Unpicklable

This module provides serialization capabilities for objects that 
standard pickle cannot handle: locks, loggers, file handles, 
thread-local data, circular references, and more.

Philosophy: "If it exists in Python, Cerial should serialize it."
"""

# Import all API functions and classes
from .api import *
from .api import __all__

# Module metadata
__version__ = "0.3.0"
__author__ = "Suitkaise Development Team"

