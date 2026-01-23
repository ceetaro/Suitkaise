"""
Base classes for reconnection helpers.
"""

from __future__ import annotations

from typing import Any


class Reconnector:
    """
    Base class for reconnection helpers.
    
    Subclasses should implement reconnect() to create or reattach the resource.
    
    Example:
        >>> from suitkaise.cerial import deserialize
        >>> from suitkaise.cerial._int.handlers import Reconnector
        >>> restored = deserialize(payload)
        >>> for item in restored:
        ...     if isinstance(item, Reconnector):
        ...         item = item.reconnect()
        ...     # use item as normal
    """

    def reconnect(self, **kwargs: Any) -> Any:
        raise NotImplementedError("reconnect() must be implemented by subclasses.")
