"""
Processing API - Subprocess-based task execution for Suitkaise

This module provides a Process base class for running tasks in subprocesses
with automatic lifecycle management, error handling, and timing support.

Key Features:
- Lifecycle methods: __preloop__, __loop__, __postloop__, __onfinish__, __result__
- Automatic subprocess management with cerial serialization
- Configurable timeouts, loop limits, and retry (lives) system
- Optional timing with @timesection() decorator

Usage:
    from suitkaise.processing import Process
    
    class MyProcess(Process):
        def __init__(self):
            self.counter = 0
            self.config.num_loops = 10
        
        def __loop__(self):
            self.counter += 1
        
        def __result__(self):
            return self.counter
    
    process = MyProcess()
    process.start()
    process.wait()
    print(process.result)  # 10
"""

from typing import Callable, TypeVar
from functools import wraps

# Import internal components
from ._int.process_class import Process
from ._int.config import ProcessConfig, TimeoutConfig
from ._int.timers import ProcessTimers
from ._int.errors import (
    PreloopError,
    MainLoopError, 
    PostLoopError,
    OnFinishError,
    ResultError,
    TimeoutError,
)

F = TypeVar('F', bound=Callable)


def timesection() -> Callable[[F], F]:
    """
    Decorator to time a Process lifecycle section.
    
    Automatically creates self.timers if it doesn't exist, and populates
    the appropriate timer (preloop, loop, postloop, onfinish) based on
    the method name.
    
    Usage:
        from suitkaise.processing import Process, timesection
        
        class MyProcess(Process):
            @timesection()
            def __preloop__(self):
                # timed
                pass
            
            @timesection()
            def __loop__(self):
                # timed  
                pass
        
        # After running:
        process.timers.preloop.mean      # average preloop time
        process.timers.loop.most_recent  # most recent loop time
        process.timers.full_loop.mean    # average full iteration time
    """
    def decorator(method: F) -> F:
        # Determine which timer slot based on method name
        method_name = method.__name__
        
        # Map method names to timer attribute names
        timer_map = {
            '__preloop__': 'preloop',
            '__loop__': 'loop',
            '__postloop__': 'postloop',
            '__onfinish__': 'onfinish',
        }
        
        timer_slot = timer_map.get(method_name)
        if timer_slot is None:
            raise ValueError(
                f"@timesection() can only be used on lifecycle methods: "
                f"{list(timer_map.keys())}, not '{method_name}'"
            )
        
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            # Ensure timers container exists
            if self.timers is None:
                self.timers = ProcessTimers()
            
            # Ensure this section's timer exists
            timer = self.timers._ensure_timer(timer_slot)
            
            # Time the method
            timer.start()
            try:
                result = method(self, *args, **kwargs)
            finally:
                timer.stop()
            
            return result
        
        return wrapper  # type: ignore
    
    return decorator


__all__ = [
    # Main class
    'Process',
    
    # Configuration
    'ProcessConfig',
    'TimeoutConfig',
    
    # Timers
    'ProcessTimers',
    
    # Errors
    'PreloopError',
    'MainLoopError',
    'PostLoopError',
    'OnFinishError',
    'ResultError',
    'TimeoutError',
    
    # Decorator
    'timesection',
]

