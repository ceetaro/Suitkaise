"""
Skpath Caller Path Detection

Utilities for detecting the caller's file path by inspecting the call stack.
Skips all suitkaise module files to find the "real" caller.
"""

from __future__ import annotations

import inspect
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Any

from .exceptions import PathDetectionError
from .id_utils import normalize_separators

# thread-safe lock
_caller_lock = threading.RLock()

# suitkaise package path (detected once, cached)
_suitkaise_path: str | None = None


def _get_suitkaise_path() -> str:
    """Get the suitkaise package path for filtering stack frames."""
    global _suitkaise_path
    
    with _caller_lock:
        if _suitkaise_path is None:
            # get the path to the suitkaise package
            current_file = Path(__file__).resolve()
            # go up from _int/caller_paths.py to suitkaise/
            _suitkaise_path = normalize_separators(
                str(current_file.parent.parent.parent)
            )
        return _suitkaise_path


def _is_suitkaise_frame(frame_info: inspect.FrameInfo) -> bool:
    """Check if a frame is from within the suitkaise package."""
    filename = normalize_separators(frame_info.filename)
    suitkaise_path = _get_suitkaise_path()
    return filename.startswith(suitkaise_path)


def get_caller_frame(skip_frames: int = 0) -> inspect.FrameInfo | None:
    """
    Get the frame info of the first caller outside suitkaise.
    
    Args:
        skip_frames: Additional frames to skip beyond suitkaise frames
        
    Returns:
        FrameInfo of the caller, or None if not found
    """
    stack = inspect.stack()
    
    # skip internal frames and find first external caller
    external_frame_count = 0
    
    for frame_info in stack:
        if _is_suitkaise_frame(frame_info):
            continue
        
        # skip built-in/frozen modules
        if frame_info.filename.startswith("<"):
            continue
        
        # found an external frame
        if external_frame_count >= skip_frames:
            return frame_info
        
        external_frame_count += 1
    
    return None


def get_caller_path_raw(skip_frames: int = 0) -> Path | None:
    """
    Get the file path of the caller outside suitkaise.
    
    Args:
        skip_frames: Additional frames to skip
        
    Returns:
        Path to the caller's file, or None if not found
    """
    frame_info = get_caller_frame(skip_frames)
    
    if frame_info is None:
        return None
    
    return Path(frame_info.filename).resolve()


def detect_caller_path(skip_frames: int = 0) -> Path:
    """
    Detect the caller's file path.
    
    Args:
        skip_frames: Additional frames to skip
        
    Returns:
        Path to the caller's file
        
    Raises:
        PathDetectionError: If caller cannot be detected
    """
    path = get_caller_path_raw(skip_frames)
    
    if path is None:
        raise PathDetectionError(
            "Could not detect caller file path. "
            "This may happen when called from an interactive shell or compiled code."
        )
    
    return path


def detect_current_dir(skip_frames: int = 0) -> Path:
    """
    Detect the directory containing the caller's file.
    
    Args:
        skip_frames: Additional frames to skip
        
    Returns:
        Path to the caller's directory
        
    Raises:
        PathDetectionError: If caller cannot be detected
    """
    caller_path = detect_caller_path(skip_frames)
    return caller_path.parent


def get_module_file_path(obj: Any) -> Path | None:
    """
    Get the file path of the module where an object is defined.
    
    Args:
        obj: Object to inspect. Can be:
            - A module object
            - A module name string
            - Any object with __module__ attribute
            
    Returns:
        Path to the module file, or None if not found
        
    Raises:
        ImportError: If obj is a module name string that cannot be imported
    """
    module: ModuleType | None = None
    
    # handle module name strings
    if isinstance(obj, str):
        if obj in sys.modules:
            module = sys.modules[obj]
        else:
            # try to import it
            import importlib
            module = importlib.import_module(obj)
    
    # handle module objects
    elif isinstance(obj, ModuleType):
        module = obj
    
    # handle objects with __module__ attribute
    elif hasattr(obj, "__module__"):
        module_name = obj.__module__
        if module_name in sys.modules:
            module = sys.modules[module_name]
    
    if module is None:
        return None
    
    # get the file from the module
    module_file = getattr(module, "__file__", None)
    
    if module_file is None:
        return None
    
    return Path(module_file).resolve()


def get_cwd_path() -> Path:
    """
    Get the current working directory as a Path.
    
    Returns:
        Current working directory as Path
    """
    return Path.cwd().resolve()
