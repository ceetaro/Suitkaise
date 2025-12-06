"""
Suitkaise Processing - Subprocess-based task execution.

Usage:
    from suitkaise.processing import Process, timesection
    
    class MyWorker(Process):
        def __init__(self):
            self.data = []
            self.config.num_loops = 100
        
        @timesection()
        def __loop__(self):
            self.data.append(process_item())
        
        def __result__(self):
            return self.data
"""

from .api import (
    # Main class
    Process,
    
    # Configuration
    ProcessConfig,
    TimeoutConfig,
    
    # Timers
    ProcessTimers,
    
    # Errors
    PreloopError,
    MainLoopError,
    PostLoopError,
    OnFinishError,
    ResultError,
    TimeoutError,
    
    # Decorator
    timesection,
)

__all__ = [
    'Process',
    'ProcessConfig',
    'TimeoutConfig',
    'ProcessTimers',
    'PreloopError',
    'MainLoopError',
    'PostLoopError',
    'OnFinishError',
    'ResultError',
    'TimeoutError',
    'timesection',
]

