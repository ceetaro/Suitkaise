"""
Circuit - Circuit Breaker for Controlled Failure Handling

This module provides a circuit breaker pattern implementation for 
controlled failure handling and resource management in loops.

Philosophy: Prevent runaway processes and provide graceful degradation.
"""

# Import all API functions and classes
from .api import *
from .api import __all__

# Module metadata
__version__ = "0.1.0"
__author__ = "Suitkaise Development Team"

