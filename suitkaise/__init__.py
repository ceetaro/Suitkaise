"""
────────────────────────────────────────────────────────
    ```python
    # Direct imports from suitkaise
    from suitkaise import TimeThis, Sktimer, Skpath, Circuit, sk, blocking
    
    # Module-level imports
    from suitkaise.timing import TimeThis
    from suitkaise.paths import Skpath
    from suitkaise.circuits import Circuit
    from suitkaise.cucumber import serialize, deserialize
    from suitkaise.processing import Skprocess, Pool
    from suitkaise.sk import sk, blocking
    ```
────────────────────────────────────────────────────────\n

suitkaise - 


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
    NotAFileError,
    
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
# Cucumber Module Exports
# ============================================================================
from .cucumber import (
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
    
    # Timers
    ProcessTimers,
    
    # Errors
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

# Decorators
from .processing.api import autoreconnect

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
# Docs Module
# ============================================================================
from . import docs

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
    "NotAFileError",
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
    
    # Cucumber
    "serialize",
    "deserialize",
    "reconnect_all",
    "SerializationError",
    "DeserializationError",
    
    # Processing
    "Skprocess",
    "Pool",
    "Share",
    "autoreconnect",
    "ProcessTimers",
    "ProcessError",
    "PreRunError",
    "RunError",
    "PostRunError",
    "OnFinishError",
    "ResultError",
    "ErrorHandlerError",
    "ProcessTimeoutError",
    "ResultTimeoutError",
    
    # Sk
    "sk",
    "blocking",
    "SkModifierError",
    "FunctionTimeoutError",

    # Docs
    "docs",
]
