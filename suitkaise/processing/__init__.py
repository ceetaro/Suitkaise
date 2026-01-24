"""
Suitkaise Processing - Subprocess-based task execution.

Usage:
    from suitkaise.processing import Skprocess, Pool, Share
    
    class MyWorker(Skprocess):
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
    
    # Shared state between processes
    with Share() as share:
        share.timer = Sktimer()  # Auto-wrapped for cross-process sharing
        share.timer.add_time(1.0)
"""

from .api import (
    # Main classes
    Skprocess,
    Pool,
    
    # Decorators
    auto_reconnect,
    
    # Timers
    ProcessTimers,
    
    # Errors (all inherit from ProcessError)
    ProcessError,
    PreRunError,
    RunError,
    PostRunError,
    OnFinishError,
    ResultError,
    ErrorHandlerError,
    ProcessTimeoutError,
    ResultTimeoutError,
)

from ._int.share import Share

# Share provides cross-process shared state for processing users

__all__ = [
    'Skprocess',
    'Pool',
    'Share',
    'auto_reconnect',
    'ProcessTimers',
    'ProcessError',
    'PreRunError',
    'RunError',
    'PostRunError',
    'OnFinishError',
    'ResultError',
    'ErrorHandlerError',
    'ProcessTimeoutError',
    'ResultTimeoutError',
]
