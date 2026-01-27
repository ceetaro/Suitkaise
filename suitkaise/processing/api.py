"""
────────────────────────────────────────────────────────
    ```python
    from suitkaise.processing import Skprocess, Pool, Share
    ```
────────────────────────────────────────────────────────\n

Api for processing
"""

# import internal components
from ._int.process_class import Skprocess
from ._int.timers import ProcessTimers
from ._int.pool import Pool
from ._int.share import Share
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


def autoreconnect(**auth):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.processing import Skprocess, autoreconnect
        
        auth = {
            "psycopg2.Connection": {"*": "secret"},
            "redis.Redis": {"*": "redis_pass"},
        }
        @autoreconnect(**auth)
        class MyProcess(Skprocess):
            def __run__(self):
                ...
        ```
    ────────────────────────────────────────────────────────\n

    Class decorator that automatically reconnects all Reconnector objects.
    
    When a Skprocess decorated with @autoreconnect is deserialized in the
    child process, reconnect_all() is called automatically to restore any
    Reconnector objects (database connections, sockets, etc.).
    
    Args:
        **auth: Reconnection parameters keyed by type, then by attr name.
            Use "*" as the attr key for defaults that apply to all instances.
    
    ────────────────────────────────────────────────────────
    ```python
        @autoreconnect(**{
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
    ```
    ────────────────────────────────────────────────────────
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
    'Share',
    
    # Decorators
    'autoreconnect',
    
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
