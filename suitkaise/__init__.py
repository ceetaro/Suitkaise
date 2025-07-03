"""
Suitkaise - Democratizing Complex Application Development

Suitkaise makes sophisticated multiprocessing, global state management, and 
cross-process communication accessible to developers of all skill levels.

Philosophy: "Grand ideas, little coding experience" - enabling anyone with 
great ideas to build complex, production-ready applications.

Core Modules:
- skpath: Smart path operations with dual-path architecture
- sktime: Smart timing operations with statistical analysis
- (Future modules: xprocess, sktree, skfunction, report, etc.)
"""

# Import core modules for direct access
try:
    from . import skpath
except ImportError:
    # Graceful degradation if skpath module unavailable
    skpath = None

try:
    from . import sktime
except ImportError:
    # Graceful degradation if sktime module unavailable
    sktime = None

# Package metadata
__version__ = "0.1.0"
__author__ = "Suitkaise Development Team"
__description__ = "Democratizing complex application development for Python"

# Available modules (expanding as more modules are added)
__all__ = [
    'skpath',
    'sktime',
]

# Optional: Create module-level convenience for most common operations
# This enables: from suitkaise import SKPath, Timer (most common use cases)
try:
    from .skpath import SKPath, autopath, get_project_root
    __all__.extend(['SKPath', 'autopath', 'get_project_root'])
except ImportError:
    pass  # Graceful degradation

try:
    from .sktime import Timer, Stopwatch, now, timethis
    __all__.extend(['Timer', 'Stopwatch', 'now', 'timethis'])
except ImportError:
    pass  # Graceful degradation