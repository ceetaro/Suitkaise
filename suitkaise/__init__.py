"""
Suitkaise - A Python Toolkit for Robust Development

Suitkaise provides a collection of utilities for common development needs:
- timing: Smart timing operations with statistical analysis
- paths: Enhanced path operations with project root detection
- circuits: Circuit breaker pattern for controlled failure handling
- cerial: Serialization for unpicklable objects
- processing: Subprocess-based task execution with pools
- sk: Class/function decorators for async, retry, timeout, background execution

Usage:
    # Direct imports from suitkaise
    from suitkaise import TimeThis, Sktimer, Skpath, Circuit, sk, blocking
    
    # Module-level imports
    from suitkaise.timing import TimeThis
    from suitkaise.paths import Skpath
    from suitkaise.circuits import Circuit
    from suitkaise.cerial import serialize, deserialize
    from suitkaise.processing import Skprocess, Pool
    from suitkaise.sk import sk, blocking
"""

# ============================================================================
# Timing Module Exports
# ============================================================================
from .timing import (
    # Simple timing functions
    time,
    sleep,
    elapsed,
    
    # Timing classes
    Sktimer,
    
    # Context managers
    TimeThis,
    
    # Decorators
    timethis,
    clear_global_timers,
)


# ============================================================================
# Paths Module Exports
# ============================================================================
from .paths import (
    # Core class
    Skpath,
    
    # Types
    AnyPath,
    
    # Decorator
    autopath,
    
    # Exceptions
    PathDetectionError,
    
    # Root management
    CustomRoot,
    set_custom_root,
    get_custom_root,
    clear_custom_root,
    get_project_root,
    
    # Path functions
    get_caller_path,
    get_current_dir,
    get_cwd,
    get_module_path,
    get_id,
    
    # Project functions
    get_project_paths,
    get_project_structure,
    get_formatted_project_tree,
    
    # Path utilities
    is_valid_filename,
    streamline_path,
)

# ============================================================================
# Circuits Module Exports
# ============================================================================
from .circuits import (
    Circuit,
    BreakingCircuit,
)

# ============================================================================
# Cerial Module Exports
# ============================================================================
from .cerial import (
    # Main functions
    serialize,
    deserialize,
    reconnect_all,
    
    # Exceptions
    SerializationError,
    DeserializationError,
)

# ============================================================================
# Processing Module Exports
# ============================================================================
from .processing import (
    # Main classes
    Skprocess,
    Pool,
    Share,
    
    # Decorators
    auto_reconnect,
    
    # Errors
    ProcessError,
    PreRunError,
    RunError,
    PostRunError,
    OnFinishError,
    ResultError,
    ErrorHandlerError,
    ProcessTimeoutError,
)

# ============================================================================
# Sk Module Exports
# ============================================================================
from .sk import (
    sk,
    blocking,
    SkModifierError,
    FunctionTimeoutError,
)

# ============================================================================
# Module Metadata
# ============================================================================
__version__ = "0.3.0"
__author__ = "Suitkaise Development Team"

__all__ = [
    # Timing
    "time",
    "sleep",
    "elapsed",
    "Sktimer",
    "TimeThis",
    "timethis",
    "clear_global_timers",
    
    # Paths
    "Skpath",
    "AnyPath",
    "autopath",
    "PathDetectionError",
    "CustomRoot",
    "set_custom_root",
    "get_custom_root",
    "clear_custom_root",
    "get_project_root",
    "get_caller_path",
    "get_current_dir",
    "get_cwd",
    "get_module_path",
    "get_id",
    "get_project_paths",
    "get_project_structure",
    "get_formatted_project_tree",
    "is_valid_filename",
    "streamline_path",
    
    # Circuits
    "Circuit",
    "BreakingCircuit",
    
    # Cerial
    "serialize",
    "deserialize",
    "SerializationError",
    "DeserializationError",
    
    # Processing
    "Skprocess",
    "Pool",
    "Share",
    "auto_reconnect",
    "ProcessError",
    "PreRunError",
    "RunError",
    "PostRunError",
    "OnFinishError",
    "ResultError",
    "ErrorHandlerError",
    "ProcessTimeoutError",
    
    # Sk
    "sk",
    "blocking",
    "SkModifierError",
    "FunctionTimeoutError",
]
