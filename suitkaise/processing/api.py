"""
Processing API - Subprocess-based task execution for Suitkaise

This module provides a Skprocess base class for running tasks in subprocesses
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
    from suitkaise.processing import Skprocess, Pool
    
    class MyProcess(Skprocess):
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
from ._int.process_class import Skprocess
# ProcessConfig is internal - not exported
from ._int.timers import ProcessTimers
from ._int.pool import Pool
from ._int.errors import (
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


Process = Skprocess  # Backwards-compatible alias


def auto_reconnect(**kwargs):
    """
    Class decorator to enable automatic reconnects after deserialization.
    
    When a Skprocess decorated with @auto_reconnect is deserialized in the
    child process, reconnect_all() is called automatically to restore any
    Reconnector objects (database connections, sockets, etc.).
    
    Args:
        **kwargs: Reconnection parameters keyed by type, then by attr name.
            Use "*" as the attr key for defaults that apply to all instances.
    
    Example:
        @auto_reconnect(**{
            "psycopg2.Connection": {
                "*": {"host": "localhost", "password": "secret"},
                "analytics_db": {"password": "other_pass"},
            },
            "redis.Redis": {
                "*": {"password": "redis_pass"},
            },
        })
        class MyProcess(Skprocess):
            def __init__(self):
                self.db = psycopg2.connect(...)
                self.analytics_db = psycopg2.connect(...)
                self.cache = redis.Redis(...)
            
            def __run__(self):
                # db, analytics_db, cache are all reconnected automatically
                ...
    """
    def decorator(cls):
        cls._auto_reconnect_enabled = True
        cls._auto_reconnect_kwargs = dict(kwargs) if kwargs else {}
        return cls
    return decorator


__all__ = [
    # Main classes
    'Skprocess',
    'Process',
    'Pool',
    
    # Decorators
    'auto_reconnect',
    
    # Timers
    'ProcessTimers',
    
    # Errors (all inherit from ProcessError)
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
