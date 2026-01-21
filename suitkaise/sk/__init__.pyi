from __future__ import annotations

from typing import Any, Callable, TypeVar

_F = TypeVar('_F', bound=Callable[..., Any])

class Skclass: ...
class Skfunction: ...
def sk(*args: Any, **kwargs: Any) -> Any: ...
def blocking(func: _F) -> _F:
    """
    Explicitly mark a method or function as blocking.
    
    Use this when a method is CPU-intensive but doesn't contain
    detectable blocking calls (like time.sleep, file I/O, etc.).
    
    This enables .background() and .asynced() for the method.
    """
    ...

class SkModifierError(Exception): ...
class FunctionTimeoutError(Exception): ...

__all__: list[str]
