# add license here

# suitkaise/sktime/sktime.py

"""
Time utilities for Suitkaise.

"""
import time

def now() -> float:
    """Get the current unix time."""
    return time.time()

def sleep(seconds: float) -> None:
    """Sleep for a given number of seconds."""
    time.sleep(seconds)

