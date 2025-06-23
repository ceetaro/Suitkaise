# add license here

# suitkaise/skpath/__init__.py

"""
SKPath - Path utilities and automatic path detection.

This module provides utilities for working with file paths, including
automatic path detection, normalization, and the @autopath decorator
for functions that need to work with file paths.

Main functions:
    normalize_path: Convert path to normalized POSIX string
    get_caller_file_path: Get path of calling file
    get_current_file_path: Get path of current file
    get_current_directory: Get directory of current file
    get_project_root: Get the root directory of the project
    equalpaths: Check if two paths are equivalent
    id: Generate reproducible ID from path
    idshort: Generate short ID from path

Decorators:
    autopath: Automatically inject normalized paths into functions

Usage:
    from suitkaise.skpath import autopath, normalize_path
    
    @autopath()
    def process_file(path: str = None):
        print(f"Processing: {path}")
        
    # path will be automatically filled with caller's file path
    process_file()
    
    # Or normalize paths manually
    clean_path = normalize_path("/some/messy/../path")
"""

from suitkaise.skpath.skpath import (
    # Main path functions
    normalize_path,
    get_caller_file_path,
    get_current_file_path,
    get_current_directory,
    get_project_root,
    equalpaths,
    id,
    idshort,
    
    # Decorators
    autopath,
    
    # Exceptions
    AutopathError,
)

# Version info
__version__ = "0.1.0"

# Expose main public API
__all__ = [
    # Path functions
    'normalize_path',
    'get_caller_file_path',
    'get_current_file_path',
    'get_current_directory',
    'get_project_root',
    'equalpaths',
    'id',
    'idshort',
    
    # Decorators
    'autopath',
    
    # Exceptions
    'AutopathError',
    
    # Version
    '__version__',
]