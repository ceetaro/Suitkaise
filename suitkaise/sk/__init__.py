"""
────────────────────────────────────────────────────────
    ```python
    from suitkaise.sk import sk
    
    # Using @sk decorator
    @sk
    class Sktimer:
        ...
    ```
────────────────────────────────────────────────────────\n

Suitkaise Sk - Class and function wrappers for Share and async support.
"""

from .api import (
    sk,
    blocking,
    SkModifierError,
    FunctionTimeoutError,
)

__all__ = [
    'sk',
    'blocking',
    'SkModifierError',
    'FunctionTimeoutError',
]
