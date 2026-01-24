"""
processing api
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


def auto_reconnect(**auth):
    """
    Class decorator to enable automatic reconnects after deserialization.
    
    When a Skprocess decorated with @auto_reconnect is deserialized in the
    child process, reconnect_all() is called automatically to restore any
    Reconnector objects (database connections, sockets, etc.).
    
    Args:
        **auth: Reconnection parameters keyed by type, then by attr name.
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
        # mark class for reconnect on deserialize in child process
        cls._auto_reconnect_enabled = True
        # store reconnect options by type and attribute name
        cls._auto_reconnect_kwargs = dict(auth) if auth else {}
        return cls
    return decorator


__all__ = [
    # Main classes
    'Skprocess',
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
