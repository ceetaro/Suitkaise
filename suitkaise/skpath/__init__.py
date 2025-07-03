"""
SKPath - Smart Path Operations for Suitkaise

This module provides intelligent path handling with dual-path architecture,
automatic project root detection, and magical caller detection.

Key Features:
- SKPath objects with absolute and normalized paths  
- Zero-configuration initialization with automatic caller detection
- AutoPath decorator for automatic path conversion
- Complete project structure analysis
- Path utilities with cross-module compatibility
"""

# Import all API functions and classes
from .api import (
    # Main class
    SKPath,
    
    # Convenience functions
    get_project_root,
    get_caller_path, 
    get_current_dir,
    get_cwd,
    equalpaths,
    equalnormpaths,
    path_id,
    path_id_short,
    get_all_project_paths,
    get_project_structure,
    get_formatted_project_tree,
    
    # Project root management
    force_project_root,
    clear_forced_project_root, 
    get_forced_project_root,
    
    # Decorators
    autopath,
    
    # Factory functions
    create,
)

# Re-export everything for direct import from module
__all__ = [
    # Main class
    'SKPath',
    
    # Convenience functions
    'get_project_root',
    'get_caller_path', 
    'get_current_dir',
    'get_cwd',
    'equalpaths',
    'equalnormpaths',
    'path_id',
    'path_id_short',
    'get_all_project_paths',
    'get_project_structure',
    'get_formatted_project_tree',
    
    # Project root management
    'force_project_root',
    'clear_forced_project_root', 
    'get_forced_project_root',
    
    # Decorators
    'autopath',
    
    # Factory functions
    'create',
]

# Module-level convenience - expose the main class at module level
# This allows: import suitkaise.skpath; path = suitkaise.skpath.SKPath()
__version__ = "0.1.0"
__author__ = "Suitkaise Development Team"