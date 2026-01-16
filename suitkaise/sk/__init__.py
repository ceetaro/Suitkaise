"""
Suitkaise Sk - Class and function wrappers for Share and async support.

Usage:
    from suitkaise.sk import Skclass, sk, SkModifierError
    
    # Using Skclass directly
    class Counter:
        def __init__(self):
            self.value = 0
        
        def increment(self):
            self.value += 1
        
        def slow_op(self):
            time.sleep(1)
            self.value += 10
    
    SkCounter = Skclass(Counter)
    counter = SkCounter()
    
    # Async version (if has blocking calls)
    AsyncCounter = SkCounter.asynced()
    async_counter = AsyncCounter()
    await async_counter.slow_op()  # Uses to_thread()
    
    # Using @sk decorator
    @sk
    class Sktimer:
        ...
    
    # Share compatibility (auto _shared_meta)
    share.counter = SkCounter()
"""

from .api import (
    Skclass,
    Skfunction,
    sk,
    SkModifierError,
    FunctionTimeoutError,
)

__all__ = [
    'Skclass',
    'Skfunction',
    'sk',
    'SkModifierError',
    'FunctionTimeoutError',
]
