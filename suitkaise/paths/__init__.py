"""
────────────────────────────────────────────────────────
    ```python
    from suitkaise import Skpath
    from suitkaise.paths import Skpath, AnyPath, autopath
    
    # Create Skpath from caller's file
    path = Skpath()
    
    # Create from string or Path
    path = Skpath("myproject/feature/file.txt")
    
    # Use the decorator for automatic type conversion
    @autopath()
    def process(path: AnyPath):
        return path.id
    ```
────────────────────────────────────────────────────────\n

Paths - Smart Path Operations for Suitkaise

Enhanced path functionality with automatic project root detection,
cross-platform path normalization, and powerful path utilities.
"""

from .api import (
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
    streamline_path_quick,
)

__all__ = [
    # Core class
    "Skpath",
    
    # Types
    "AnyPath",
    
    # Decorator
    "autopath",
    
    # Exceptions
    "PathDetectionError",
    "NotAFileError",
    
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
    
    # Path utilities
    "is_valid_filename",
    "streamline_path",
    "streamline_path_quick",
]

# Module metadata
__version__ = "0.4.13"
__author__ = "Casey Eddings"
