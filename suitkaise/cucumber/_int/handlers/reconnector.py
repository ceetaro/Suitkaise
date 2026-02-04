"""
Base classes for reconnection helpers.
"""

from __future__ import annotations

from typing import Any

from suitkaise.sk._int.analyzer import analyze_class


class Reconnector:
    """
    Base class for reconnection helpers.
    
    Subclasses should implement reconnect() to create or reattach the resource.
    
    - No-auth types: reconnect() with no args
    - Auth types: reconnect(auth) with auth arg
    
    Example:
        >>> from suitkaise.cucumber import deserialize
        >>> from suitkaise.cucumber._int.handlers import Reconnector
        >>> restored = deserialize(payload)
        >>> for item in restored:
        ...     if isinstance(item, Reconnector):
        ...         item = item.reconnect()
        ...     # use item as normal
    """

    def reconnect(self, *args, **kwargs) -> Any:
        raise NotImplementedError("reconnect() must be implemented by subclasses.")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        try:
            meta, _ = analyze_class(cls)
            cls._shared_meta = meta
        except Exception:
            pass


try:
    _meta, _ = analyze_class(Reconnector)
    Reconnector._shared_meta = _meta
except Exception:
    pass
