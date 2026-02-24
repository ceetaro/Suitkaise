"""
"""

from .api import (
    # Main classes
    Skprocess,
    Pool,
    Share,
    Pipe,
    
    # Decorators
    autoreconnect,
    
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

__all__ = [
    'Skprocess',
    'Pool',
    'Share',
    'Pipe',
    'autoreconnect',
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

# Module metadata
__version__ = "0.4.12"
__author__ = "Casey Eddings"
