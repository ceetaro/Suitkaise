"""
Suitkaise Processing - Subprocess-based task execution.

Usage:
    from suitkaise.processing import Process, Pool
    
    class MyWorker(Process):
        def __init__(self, value):
            self.value = value
        
        def __run__(self):
            self.result_value = self.value * 2
        
        def __result__(self):
            return self.result_value
    
    # Single process
    worker = MyWorker(5)
    worker.start()
    worker.wait()
    result = worker.result()  # 10
    
    # Batch processing with Pool
    pool = Pool(workers=8)
    results = pool.map(MyWorker, [1, 2, 3, 4, 5])
    # results = [2, 4, 6, 8, 10]
    
    # Access timing (automatic for any lifecycle method)
    print(worker.__run__.timer.mean)
"""

from .api import (
    # Main classes
    Process,
    Pool,
    
    # Pool helpers
    AsyncResult,
    StarModifier,
    
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
    'Pool',
    'AsyncResult',
    'StarModifier',
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
