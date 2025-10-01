"""
Suitkaise - Democratizing Complex Application Development

Suitkaise makes sophisticated multiprocessing, global state management, and 
cross-process communication accessible to developers of all skill levels.

Philosophy: "Grand ideas, little coding experience" - enabling anyone with 
great ideas to build complex, production-ready applications.

Core Modules:
- skpath: Smart path operations with dual-path architecture (coming soon)
- sktime: Smart timing operations with statistical analysis (coming soon)

Import Usage Examples:
    ```python
    ```
"""

# Import core modules for direct access
try:
    from . import skpath
    _skpath_available = True
except ImportError:
    # Graceful degradation if skpath module unavailable
    skpath = None
    _skpath_available = False

try:
    from . import sktime
    _sktime_available = True
except ImportError:
    # Graceful degradation if sktime module unavailable
    sktime = None
    _sktime_available = False

# Package metadata
__version__ = "0.0.0"
__author__ = "Suitkaise Development Team"
__description__ = "Democratizing complex application development for Python"
__url__ = "https://github.com/suitkaise/suitkaise"  # Update when you have a repo

# Available modules (expanding as more modules are added)
__all__ = []

# Add available modules to __all__
if _skpath_available:
    __all__.append('skpath')
if _sktime_available:
    __all__.append('sktime')

# =============================================================================
# Convenience Imports - Most Common Functions
# =============================================================================

# SKPath convenience imports (when available)
if _skpath_available:
    try:
        from .skpath import SKPath, autopath, get_project_root
        __all__.extend(['SKPath', 'autopath', 'get_project_root'])
    except ImportError:
        pass  # Graceful degradation

# SKTime module is available as `suitkaise.sktime` and via `from suitkaise import sktime`
# Objects should be imported from `suitkaise.sktime` per documentation.

# =============================================================================
# Package Information and Status
# =============================================================================

def get_available_modules():
    """
    Get information about available Suitkaise modules.
    
    Returns:
        dict: Module availability status and versions
    """
    modules = {}
    
    if _skpath_available:
        try:
            modules['skpath'] = {
                'available': True,
                'version': skpath.__version__ if hasattr(skpath, '__version__') else __version__,
                'description': 'Smart path operations'
            }
        except:
            modules['skpath'] = {'available': True, 'version': 'unknown', 'description': 'Smart path operations'}
    else:
        modules['skpath'] = {'available': False, 'description': 'Smart path operations'}
    
    if _sktime_available:
        try:
            modules['sktime'] = {
                'available': True,
                'version': sktime.__version__ if hasattr(sktime, '__version__') else __version__,
                'description': 'Smart timing operations'
            }
        except:
            modules['sktime'] = {'available': True, 'version': 'unknown', 'description': 'Smart timing operations'}
    else:
        modules['sktime'] = {'available': False, 'description': 'Smart timing operations'}
    
    return modules


def show_status():
    """
    Display the current status of Suitkaise modules.
    
    This function provides a quick overview of what's available in your
    Suitkaise installation.
    """
    print(f"Suitkaise v{__version__} - Democratizing Complex Application Development")
    print("=" * 70)
    
    modules = get_available_modules()
    
    for module_name, info in modules.items():
        status = "✅ Available" if info['available'] else "❌ Not Available"
        version = f"v{info['version']}" if info['available'] and 'version' in info else ""
        print(f"{module_name:12} {status:15} {version:10} - {info['description']}")
    
    print("\nMost common imports:")
    if _fdprint_available:
        print("  from suitkaise import fprint, dprint")
    print("  from suitkaise.fdprint import fmt, timestamp")
    
    print(f"\nFor more information: {__url__}")


# =============================================================================
# Module-level convenience
# =============================================================================

# This allows: import suitkaise; suitkaise.fprint("Hello")
# while still supporting: from suitkaise import fprint; fprint("Hello")

# Show a helpful message if someone tries to access unavailable modules
def __getattr__(name):
    if name == 'skpath' and not _skpath_available:
        raise ImportError("skpath module is not available. This module is coming soon!")
    elif name == 'sktime' and not _sktime_available:
        raise ImportError("sktime module is not available. This module is coming soon!")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")