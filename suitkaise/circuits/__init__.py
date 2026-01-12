"""
Circuits - Circuit Breaker for Controlled Failure Handling

This module provides a circuit breaker pattern implementation for 
controlled failure handling and resource management in loops.

Usage:
    from suitkaise import Circuit
    from suitkaise.circuits import Circuit

Philosophy: Prevent runaway processes and provide graceful degradation.
"""

# Import all API functions and classes
from .api import Circuit, BreakingCircuit

__all__ = [
    'Circuit',
    'BreakingCircuit',
]

# Module metadata
__version__ = "0.3.0"
__author__ = "Suitkaise Development Team"

