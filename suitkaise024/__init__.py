"""
Suitkaise - Democratizing Complex Application Development

Suitkaise makes sophisticated multiprocessing, global state management, and 
cross-process communication accessible to developers of all skill levels.

Philosophy: "Grand ideas, little coding experience" - enabling anyone with 
great ideas to build complex, production-ready applications.

Core Modules:
- cucumber: Serialization for the unpicklable (locks, loggers, file handles)
- circuit: Circuit breaker pattern for controlled failure handling
- processing: Subprocess-based task execution with lifecycle management
- skpath: Smart path operations with dual-path architecture
- sktime: Smart timing operations with statistical analysis

Import Usage Examples:
    ```python
    from suitkaise import cucumber, circuit, skpath, sktime
    
    # Serialize objects with locks and loggers
    data = cucumber.serialize(complex_object)
    
    # Circuit breaker for retry loops
    breaker = circuit.Circuit(shorts=3)
    
    # Smart path handling
    path = skpath.SKPath("my/file.txt")
    
    # Timing operations
    timer = sktime.Timer()
    ```
"""

# Import core modules for direct access
try:
    from . import cucumber
    _cucumber_available = True
except ImportError:
    cucumber = None
    _cucumber_available = False

try:
    from . import circuit
    _circuit_available = True
except ImportError:
    circuit = None
    _circuit_available = False

try:
    from . import skpath
    _skpath_available = True
except ImportError:
    skpath = None
    _skpath_available = False

try:
    from . import sktime
    _sktime_available = True
except ImportError:
    sktime = None
    _sktime_available = False

try:
    from . import processing
    _processing_available = True
except ImportError:
    processing = None
    _processing_available = False

# Package metadata
__version__ = "0.2.4"
__author__ = "Casey Eddings"
__description__ = "Democratizing complex application development for Python"
__url__ = "https://github.com/caseyeddings/suitkaise"

# Available modules (expanding as more modules are added)
__all__ = []

# Add available modules to __all__
if _cucumber_available:
    __all__.append('cucumber')
if _circuit_available:
    __all__.append('circuit')
if _processing_available:
    __all__.append('processing')
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

# Cucumber convenience imports (when available)
if _cucumber_available:
    try:
        from .cucumber import serialize, deserialize
        __all__.extend(['serialize', 'deserialize'])
    except ImportError:
        pass  # Graceful degradation

# Circuit convenience imports (when available)
if _circuit_available:
    try:
        from .circuit import Circuit
        __all__.append('Circuit')
    except ImportError:
        pass  # Graceful degradation

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
    
    if _cucumber_available:
        try:
            modules['cucumber'] = {
                'available': True,
                'version': cucumber.__version__ if hasattr(cucumber, '__version__') else __version__,
                'description': 'Serialization for the unpicklable'
            }
        except:
            modules['cucumber'] = {'available': True, 'version': 'unknown', 'description': 'Serialization for the unpicklable'}
    else:
        modules['cucumber'] = {'available': False, 'description': 'Serialization for the unpicklable'}
    
    if _circuit_available:
        try:
            modules['circuit'] = {
                'available': True,
                'version': circuit.__version__ if hasattr(circuit, '__version__') else __version__,
                'description': 'Circuit breaker pattern'
            }
        except:
            modules['circuit'] = {'available': True, 'version': 'unknown', 'description': 'Circuit breaker pattern'}
    else:
        modules['circuit'] = {'available': False, 'description': 'Circuit breaker pattern'}
    
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
    
    if _processing_available:
        try:
            modules['processing'] = {
                'available': True,
                'version': processing.__version__ if hasattr(processing, '__version__') else __version__,
                'description': 'Subprocess-based task execution'
            }
        except:
            modules['processing'] = {'available': True, 'version': 'unknown', 'description': 'Subprocess-based task execution'}
    else:
        modules['processing'] = {'available': False, 'description': 'Subprocess-based task execution'}
    
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
    
    print("\nCommon imports:")
    print("  from suitkaise import cucumber, circuit, processing, skpath, sktime")
    print("  from suitkaise import serialize, deserialize  # cucumber shortcuts")
    print("  from suitkaise.processing import Process, timesection  # processing")
    
    print(f"\nFor more information: {__url__}")


# =============================================================================
# Module-level convenience
# =============================================================================

# Show a helpful message if someone tries to access unavailable modules
def __getattr__(name):
    if name == 'cucumber' and not _cucumber_available:
        raise ImportError("cucumber module is not available. Check installation.")
    elif name == 'circuit' and not _circuit_available:
        raise ImportError("circuit module is not available. Check installation.")
    elif name == 'processing' and not _processing_available:
        raise ImportError("processing module is not available. Check installation.")
    elif name == 'skpath' and not _skpath_available:
        raise ImportError("skpath module is not available. Check installation.")
    elif name == 'sktime' and not _sktime_available:
        raise ImportError("sktime module is not available. Check installation.")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
