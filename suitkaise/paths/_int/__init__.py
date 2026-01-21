"""
Skpath Internal Module

Internal implementations for the skpath module.
All public APIs are exported from api.py.
"""

# Exceptions
from .exceptions import PathDetectionError, NotAFileError

# Types
from .types import AnyPath

# ID utilities
from .id_utils import (
    decode_path_id,
    encode_path_id,
    hash_path_md5,
    is_valid_encoded_id,
    normalize_separators,
    to_os_separators,
)

# Root detection
from .root_detection import (
    CustomRoot,
    clear_custom_root,
    clear_root_cache,
    detect_project_root,
    get_custom_root,
    set_custom_root,
)

# Caller paths
from .caller_paths import (
    detect_caller_path,
    detect_current_dir,
    get_caller_frame,
    get_caller_path_raw,
    get_cwd_path,
    get_module_file_path,
)

# Skpath class
from .skpath import Skpath

# Autopath decorator
from .autopath import autopath

# Project utilities
from .project_utils import (
    get_formatted_project_tree,
    get_project_paths,
    get_project_structure,
)

__all__ = [
    # Exceptions
    "PathDetectionError",
    "NotAFileError",
    
    # Types
    "AnyPath",
    
    # ID utilities
    "encode_path_id",
    "decode_path_id",
    "hash_path_md5",
    "is_valid_encoded_id",
    "normalize_separators",
    "to_os_separators",
    
    # Root detection
    "CustomRoot",
    "set_custom_root",
    "get_custom_root",
    "clear_custom_root",
    "clear_root_cache",
    "detect_project_root",
    
    # Caller paths
    "detect_caller_path",
    "detect_current_dir",
    "get_caller_frame",
    "get_caller_path_raw",
    "get_cwd_path",
    "get_module_file_path",
    
    # Skpath class
    "Skpath",
    
    # Autopath decorator
    "autopath",
    
    # Project utilities
    "get_project_paths",
    "get_project_structure",
    "get_formatted_project_tree",
]
