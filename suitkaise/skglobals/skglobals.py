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
from typing import Optional
from pathlib import Path

from suitkaise.skglobals._project_indicators import project_indicators

class SKGlobalError(Exception):
    """Custom exception for SKGlobal."""
    pass

class PlatformNotFoundError(Exception):
    """Custom exception for platform not found."""
    pass

import os
import sys
from pathlib import Path
from typing import Optional

from suitkaise.skglobals._project_indicators import project_indicators

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

class TopLevel:
    pass


class SKGlobal:
    pass

class SKGlobalVar:
    pass

class GlobalStorage:
    pass

def main():
    """
    Main function to run the SKGlobal module.
    
    This function is a placeholder for future implementation.
    
    """
    root = get_project_root()
    print(f"Project root: {root}")


if __name__ == "__main__":
    main()