# add license here

# suitkaise/sktime/__init__.py

"""
SKTime - Time utilities for Suitkaise.

This module provides simple time utilities with a consistent interface.
All time values are in Unix timestamp format (seconds since epoch).

Main functions:
    now: Get current Unix timestamp
    sleep: Sleep for specified number of seconds

Usage:
    from suitkaise.sktime import now, sleep
    
    start_time = now()
    sleep(1.5)  # Sleep for 1.5 seconds
    elapsed = now() - start_time
    print(f"Elapsed: {elapsed:.2f} seconds")
"""

from suitkaise.sktime.sktime import (
    now,
    sleep,
    elapsed,
    Stopwatch
)

# Version info
__version__ = "0.1.0"

# Expose main public API
__all__ = [
    'now',
    'sleep',
    'elapsed',
    'Stopwatch',
    '__version__',
]