"""
SKPath - Smart Path Operations for Suitkaise

Enhanced path functionality with automatic project root detection,
cross-platform path normalization, and powerful path utilities.

Usage:
    from suitkaise import skpath
    from suitkaise.skpath import SKPath, AnyPath, autopath
    
    # Create SKPath from caller's file
    path = SKPath()
    
    # Create from string or Path
    path = SKPath("myproject/feature/file.txt")
    
    # Use the decorator for automatic type conversion
    @autopath()
    def process(path: AnyPath):
        return path.id
"""

from .api import (
    # Core class
    SKPath,
    
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
)

__all__ = [
    # Core class
    "SKPath",
    
    # Types
    "AnyPath",
    
    # Decorator
    "autopath",
    
    # Exceptions
    "PathDetectionError",
    
    # Root management
    "CustomRoot",
    "set_custom_root",
    "get_custom_root",
    "clear_custom_root",
    "get_project_root",
    
    # Path functions
    "get_caller_path",
    "get_current_dir",
    "get_cwd",
    "get_module_path",
    "get_id",
    
    # Project functions
    "get_project_paths",
    "get_project_structure",
    "get_formatted_project_tree",
]
