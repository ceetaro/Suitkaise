"""
Suitkaise Processing - Subprocess-based task execution.

Usage:
    from suitkaise.processing import Process
    
    class MyWorker(Process):
        def __init__(self):
            self.data = []
            self.config.runs = 100
        
        def __run__(self):
            self.data.append(process_item())
        
        def __result__(self):
            return self.data
    
    worker = MyWorker()
    worker.start()
    worker.wait()
    
    # Access results
    result = worker.result
    
    # Access timing (automatic for any lifecycle method)
    print(worker.__run__.timer.mean)
"""

from .api import (
    # Main class
    Process,
    
    # Configuration
    ProcessConfig,
    TimeoutConfig,
    
    # Timers
    ProcessTimers,
    
    # Errors (all inherit from ProcessError)
    ProcessError,
    PreRunError,
    RunError,
    PostRunError,
    OnFinishError,
    ResultError,
    ErrorError,
    ProcessTimeoutError,
)

__all__ = [
    'Process',
    'ProcessConfig',
    'TimeoutConfig',
    'ProcessTimers',
    'ProcessError',
    'PreRunError',
    'RunError',
    'PostRunError',
    'OnFinishError',
    'ResultError',
    'ErrorError',
    'ProcessTimeoutError',
]
