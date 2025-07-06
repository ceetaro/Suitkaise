"""
Xprocess Internal Cross-processing Engine - Central Module

This module provides the core process management functionality that powers 
cross-process execution in Suitkaise. Built on multiprocessing with enhanced 
lifecycle management and automatic error handling.

This is an INTERNAL module. Front-facing APIs are provided in separate modules.

Key Features:
- Declarative process lifecycle management
- Graceful shutdown with multiple termination strategies  
- Loop timing and performance tracking
- Process status monitoring and crash recovery
- Clean separation between user code and process management
- Function-based quick process execution (internal implementation)
- Class-based advanced process management

Architecture:
- CrossProcessing: Main process manager and registry
- _Process: User-defined process class with lifecycle hooks
- _ProcessRunner: Internal execution engine that runs in subprocess
- _FunctionProcess: Internal wrapper for function-based execution
"""

# Central imports - everything available from base module
from .exceptions import (
    XProcessError,
    PreloopError, MainLoopError, PostLoopError,
    PreloopTimeoutError, MainLoopTimeoutError, PostLoopTimeoutError
)

from .configs import (
    _PConfig,
    _QPConfig
)

from .stats import ProcessStats

from .processes import (
    PStatus,
    _Process, 
    _FunctionProcess
)

from .runner import _ProcessRunner

from .pdata import (
    _PData,
    ProcessResultError
)

from .pool import (
    PoolMode,
    PoolTaskError,
    _PTask,
    _PTaskResult,
    ProcessPool
)
__all__ = [
    # Exceptions
    'XProcessError',
    'PreloopError', 'MainLoopError', 'PostLoopError',
    'PreloopTimeoutError', 'MainLoopTimeoutError', 'PostLoopTimeoutError',
    
    # Configuration (internal classes with underscore prefix)
    '_PConfig',
    '_QPConfig', 
    
    # Process Data
    '_PData',
    'ProcessResultError',
    
    # Stats
    'ProcessStats',
    
    # Process classes (internal classes with underscore prefix)
    'PStatus',
    '_Process',
    '_FunctionProcess',
    
    # Runner
    '_ProcessRunner',
    
    # Managers
    'CrossProcessing',
    'SubProcessing',
    
    # Process Pool
    'PoolMode',
    'PoolTaskError', 
    '_PTask',
    '_PTaskResult',
    'ProcessPool'
]


# Utility functions for internal use
def _create_default_config():
    """Create a default process configuration."""
    return _PConfig()


def _create_default_quick_config():
    """Create a default quick process configuration."""
    return _QPConfig()


# Version info for debugging
__version__ = "0.0.0"
__engine__ = "Suitkaise internal cross-processing engine"