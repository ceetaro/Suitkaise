# add license here

# suitkaise/skglobals/skglobals.py

"""
Module for creating and managing global variables and registries.

- create leveled global variables using SKRoots/Leaves
- create cross process global storage and variables using multiprocessing.Manager
- global storage automatically created for each SKRoot/Leaf that needs to share data
- globals can auto-sync with each other if needed

"""
import os
import sys
from typing import Optional, Any, Dict, List, Union
from pathlib import Path
from enum import IntEnum

from suitkaise.skglobals._project_indicators import project_indicators

class SKGlobalError(Exception):
    """Custom exception for SKGlobal."""
    pass

class SKGlobalValueError(SKGlobalError):
    """Custom exception for SKGlobal value errors."""
    pass

class SKGlobalLevelError(SKGlobalError):
    """Custom exception for SKGlobal level errors."""
    pass

class PlatformNotFoundError(Exception):
    """Custom exception for platform not found."""
    pass

def get_project_root(name: Optional[str] = None) -> str:
    """
    Get the project root of your project based on common indicators and
    optionally the name of the project.
    """
    filepath = str(Path(__file__).resolve())
    path = os.path.dirname(filepath)


    def dir_children(path: str) -> list[str]:
        dir = os.path.dirname(path) if os.path.isfile(path) else path
        return [d for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]

    def file_children(path: str) -> list[str]:
        dir = os.path.dirname(path) if os.path.isfile(path) else path
        return [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]

    def preprocess_indicators(indicators: dict) -> dict:
        """Resolve string references in indicators."""
        for group, values in indicators['file_groups'].items():
            ref_name = f"file_groups['{group}']"
            for key, value in indicators['common_proj_root_files'].items():
                if ref_name in value:
                    indicators['common_proj_root_files'][key] = values['patterns']

        for group, values in indicators['dir_groups'].items():
            ref_name = f"dir_groups['{group}']"
            for key, value in indicators['common_proj_root_dirs'].items():
                if ref_name in value:
                    indicators['common_proj_root_dirs'][key] = values['patterns']

        return indicators

    indicators = preprocess_indicators(project_indicators)

    platform = sys.platform
    if platform == 'win32':
        common_ospaths = indicators['common_ospaths']['windows']
    elif platform == 'linux':
        common_ospaths = indicators['common_ospaths']['linux']
    elif platform == 'darwin':
        common_ospaths = indicators['common_ospaths']['macOS']
    else:
        raise PlatformNotFoundError(f"Unsupported platform: {platform}")

    current = path
    while current not in common_ospaths:
        score = 0
        required_files_found = False

        # Check files
        for child in file_children(current):
            for value in indicators['common_proj_root_files']['necessary']:
                if child in value:
                    required_files_found = True
            for value in indicators['common_proj_root_files']['indicators']:
                if child in value:
                    score += 3
            for value in indicators['common_proj_root_files']['weak_indicators']:
                if child in value:
                    score += 1

        # Check directories
        for child in dir_children(current):
            for value in indicators['common_proj_root_dirs']['strong_indicators']:
                if child in value:
                    score += 10
            for value in indicators['common_proj_root_dirs']['indicators']:
                if child in value:
                    score += 3

        if required_files_found and score >= 25:
            return current

        parent = os.path.dirname(current)
        if parent == current:  # Reached the root directory
            break
        current = parent

    raise SKGlobalError(f"Project root not found for path: {path}")

class GlobalLevel(IntEnum):
    """
    Enum for global variable levels.
    
    """
    TOP = 0
    UNDER = 1

class SKGlobal:
    """
    Base class for creating global variables and shared storage.

    Includes SKGlobal.edit, a function that opens a global variable
    for editing without having to call "global var_name".
    
    """
    
    def __init__(self,
                 level: GlobalLevel = GlobalLevel.TOP,
                 path: Optional[str] = None,
                 name: Optional[str] = None,
                 value: Optional[Any] = None,
                 auto_sync: bool = True,
                 auto_create: bool = True,
                 remove_at: Optional[float] = None) -> Tuple[Optional[Any], Optional[SKFunction]]:
        """
        Create, and initialize a global variable.

        Args:
            level (GlobalLevel): level to store the global variable.
                - this can either be GlobalLevel.TOP or GlobalLevel.UNDER
                - if under, use path to specify the parent
            path (str, optional): path to store the global variable.
            name (str, optional): name to give the global variable.
            value (Any, optional): value to initialize the global variable with.
            auto_sync (bool): if True, the global variable will be
                automatically synchronized with other processes.
            auto_create (bool): if True, the global variable will be
                automatically created if it does not exist.
                - if False, can return an executable SKFunction instance.
            remove_at (float, optional): if set, the global variable
                will be removed after this time.
                - this is useful for temporary global variables
                - if None, the global variable will not be removed.
            
        Returns:
            Tuple: the global variable's value and an SKFunction instance
                if auto_create is False.

        Raises:
            SKGlobalError: if the global variable cannot be created.
            ValueError: if the level is not valid.

        """
        pass
        


class SKGlobalStorage:
    """
    Container to store and manage global variables.

    Includes a method to write global variables to a file and load them back
    on next startup in the specified path's directory under a global_storage.sk file.
    (JSON file created automatically if not already present)
    
    """
    
