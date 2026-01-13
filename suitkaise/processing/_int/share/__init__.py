"""
Share - Process-safe shared state for Suitkaise.

This module provides the Share container for sharing data between processes
with automatic synchronization, read barriers, and coordinator-based writes.
"""

# Internal primitives - not exported, used by other internal modules
from .primitives import (
    _WriteCounter,
    _CounterRegistry,
    _CommandQueue,
    _SourceOfTruth,
)

from .coordinator import (
    _Coordinator,
)

from .proxy import (
    _ObjectProxy,
    _MethodProxy,
)

from .share import (
    Share,
)

# Public exports
__all__ = [
    'Share',
]
