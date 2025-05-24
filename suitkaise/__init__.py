# add license here

# suitkaise/__init__.py

"""
Suitkaise - A comprehensive Python library for project management utilities.

Suitkaise provides tools for:
- Global variable management with cross-process support (skglobals)
- Path utilities and automatic path detection (skpath)  
- Time utilities (sktime)
- Enhanced serialization with multiprocessing support (cereal)

Main modules:
    skglobals: Global variable management
    skpath: Path utilities and autopath decorator
    sktime: Time utilities
    cereal: Enhanced serialization

Quick start:
    from suitkaise.skglobals import SKGlobal, GlobalLevel
    from suitkaise.skpath import autopath, normalize_path
    from suitkaise.sktime import now, sleep
    
    # Create a global variable
    my_global = SKGlobal(name="counter", value=0)
    
    # Use autopath decorator
    @autopath()
    def process_file(path: str = None):
        print(f"Processing: {path}")
    
    # Time utilities
    start = now()
    sleep(1.0)
    elapsed = now() - start
"""

# Import main components
from suitkaise import skglobals
from suitkaise import skpath
from suitkaise import sktime
from suitkaise import cereal

# Version info
__version__ = "0.1.0"
__author__ = "Suitkaise Team"
__description__ = "A comprehensive Python library for project management utilities"

# Expose main public APIs for convenience
from suitkaise.skglobals import (
    SKGlobal,
    GlobalLevel,
    get_project_root,
    create_global,
    get_global,
)

from suitkaise.skpath import (
    autopath,
    normalize_path,
    resolve_path,
    get_caller_file_path,
)

from suitkaise.sktime import (
    now,
    sleep,
)

from suitkaise.cereal import (
    serialize,
    deserialize,
    serializable,
)

# Main public API
__all__ = [
    # Modules
    'skglobals',
    'skpath', 
    'sktime',
    'cereal',
    
    # Main classes and functions
    'SKGlobal',
    'GlobalLevel',
    'get_project_root',
    'create_global',
    'get_global',
    'autopath',
    'normalize_path',
    'resolve_path',
    'get_caller_file_path',
    'now',
    'sleep',
    'serialize',
    'deserialize',
    'serializable',
    
    # Metadata
    '__version__',
    '__author__',
    '__description__',
]

def get_info():
    """Get information about the Suitkaise library."""
    return {
        'version': __version__,
        'author': __author__, 
        'description': __description__,
        'modules': ['skglobals', 'skpath', 'sktime', 'cereal'],
        'main_classes': ['SKGlobal', 'GlobalLevel'],
        'decorators': ['autopath'],
        'utilities': ['get_project_root', 'normalize_path', 'now', 'sleep'],
    }