"""
Base classes for reconnection helpers.
"""

from __future__ import annotations

from typing import Any

from suitkaise.sk._int.analyzer import analyze_class


_LAZY_RECONNECT_SENTINEL = object()


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

    _lazy_reconnect_on_access = False

    def reconnect(self, *args, **kwargs) -> Any:
        raise NotImplementedError("reconnect() must be implemented by subclasses.")

    def _lazy_reconnect_target(self) -> Any:
        try:
            target = object.__getattribute__(self, "_lazy_target")
        except AttributeError:
            target = _LAZY_RECONNECT_SENTINEL

        if target is _LAZY_RECONNECT_SENTINEL:
            target = self.reconnect()
            try:
                object.__setattr__(self, "_lazy_target", target)
            except Exception:
                pass

        return target

    def __getattr__(self, name: str) -> Any:
        if not type(self)._lazy_reconnect_on_access:
            raise AttributeError(f"{type(self).__name__!s} object has no attribute {name!r}")

        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(f"{type(self).__name__!s} object has no attribute {name!r}")

        target = self._lazy_reconnect_target()
        if target is None:
            raise AttributeError(
                f"{type(self).__name__!s} object has no attribute {name!r} "
                f"(reconnect() returned None)"
            )
        return getattr(target, name)

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
