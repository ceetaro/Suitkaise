"""
Processing API - Subprocess-based task execution for Suitkaise

This module provides a Process base class for running tasks in subprocesses
with automatic lifecycle management, error handling, and timing support.
Also provides Pool for batch parallel processing.

Key Features:
- Lifecycle methods: __prerun__, __run__, __postrun__, __onfinish__, __result__, __error__
- Automatic subprocess management with cerial serialization
- Configurable timeouts, run limits, and retry (lives) system
- Automatic timing for any lifecycle method you define
- Inter-process communication via tell() and listen()
- Pool for batch parallel processing with star() modifier

Usage:
    from suitkaise.processing import Process, Pool
    
    class MyProcess(Process):
        def __init__(self, value):
            self.value = value
        
        def __run__(self):
            self.result_value = self.value * 2
        
        def __result__(self):
            return self.result_value
    
    # Single process
    process = MyProcess(5)
    process.start()
    process.wait()
    print(process.result())  # 10
    
    # Batch processing with Pool
    pool = Pool(workers=8)
    results = pool.map(MyProcess, [1, 2, 3, 4, 5])
    print(results)  # [2, 4, 6, 8, 10]
    
    # Access timing data (automatic, no decorator needed)
    print(process.__run__.timer.mean)
"""

# Import internal components
from ._int.process_class import Process
from ._int.config import ProcessConfig, TimeoutConfig
from ._int.timers import ProcessTimers
from ._int.pool import Pool, AsyncResult, StarModifier
from ._int.errors import (
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
    # Main classes
    'Process',
    'Pool',
    
    # Pool helpers
    'AsyncResult',
    'StarModifier',
    
    # Configuration
    'ProcessConfig',
    'TimeoutConfig',
    
    # Timers
    'ProcessTimers',
    
    # Errors (all inherit from ProcessError)
    'ProcessError',
    'PreRunError',
    'RunError',
    'PostRunError',
    'OnFinishError',
    'ResultError',
    'ErrorError',
    'ProcessTimeoutError',
]
