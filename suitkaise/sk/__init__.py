"""
────────────────────────────────────────────────────────
    ```python
    from suitkaise.sk import Skclass, sk
    
    # Using Skclass directly
    class Counter:
        def __init__(self):
            self.value = 0
        
        def increment(self):
            self.value += 1
    
    SkCounter = Skclass(Counter)
    counter = SkCounter()
    
    # Using @sk decorator
    @sk
    class Sktimer:
        ...
    ```
────────────────────────────────────────────────────────\n

Suitkaise Sk - Class and function wrappers for Share and async support.
"""

from .api import (
    Skclass,
    Skfunction,
    sk,
    blocking,
    SkModifierError,
    FunctionTimeoutError,
)

__all__ = [
    'Skclass',
    'Skfunction',
    'sk',
    'blocking',
    'SkModifierError',
    'FunctionTimeoutError',
]
