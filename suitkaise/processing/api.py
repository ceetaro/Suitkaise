"""
Processing API - Subprocess-based task execution for Suitkaise

This module provides a Process base class for running tasks in subprocesses
with automatic lifecycle management, error handling, and timing support.

Key Features:
- Lifecycle methods: __prerun__, __run__, __postrun__, __onfinish__, __result__, __error__
- Automatic subprocess management with cerial serialization
- Configurable timeouts, run limits, and retry (lives) system
- Automatic timing for any lifecycle method you define

Usage:
    from suitkaise.processing import Process
    
    class MyProcess(Process):
        def __init__(self):
            self.counter = 0
            self.config.runs = 10
        
        def __run__(self):
            self.counter += 1
        
        def __result__(self):
            return self.counter
    
    process = MyProcess()
    process.start()
    process.wait()
    print(process.result)  # 10
    
    # Access timing data (automatic, no decorator needed)
    print(process.__run__.timer.mean)
"""

# Import internal components
from ._int.process_class import Process
from ._int.config import ProcessConfig, TimeoutConfig
from ._int.timers import ProcessTimers
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
    # Main class
    'Process',
    
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
