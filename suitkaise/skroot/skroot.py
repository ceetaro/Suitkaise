# add license here

# suitkaise/skroot/skroot.py

"""
Module for creating and managing SKRoots and SKLeaves.

- SKRoot is an object that represents a root.
- SKLeaf is a root like object that is not actually the project root.

Say you want to have mulitple instances of a singleton registry at differnt levels
in your project, with the main path being myproject/level1/level2/level3.

An SKRoot would get created for myproject. that doesn't mean it is created in myproject,
but rather when created, points to myproject.

If you want a different registry at level1, level2, or level3, but want them to sync
with the root SKRoot, you can create a SKLeaf for each of those levels. The SKLeaf acts
exactly the same as a pointer to the directory it was made for, but with the added bonus
of being able to sync with the SKRoot.

If the SKRoot and an SKLeaf have the same object type in storage, the root will be able 
to send changes or sync to the leaf if we want, and vice versa.

"""
import os
import uuid
from typing import Dict, Optional, Set, List, Union
from pathlib import Path
import weakref
import threading

from suitkaise.skglobals.skglobals import (
    SKGlobal, GlobalLevel, get_project_root)

def equalpaths(path1: str | Path, path2: str | Path) -> bool:
    """Check if two paths are equal."""
    return str(Path(path1).resolve()) == str(Path(path2).resolve())

class SKRootError(Exception):
    """Custom exception for SKRoot."""
    pass

class SKRootLevelError(SKRootError):
    """Custom exception for SKRoot level errors."""
    pass

class SKLeafError(Exception):
    """Custom exception for SKLeaf."""
    pass

class RootProperties:
    """
    Common properties for SKRoot and SKLeaf.
    
    """

    def __init__(self, path: str | Path, name: Optional[str] = None):
       self._path = Path(path).resolve()
       self._name = name or self.path.name
       self._id = str(uuid.uuid4())
       self._children: Set[weakref.ref] = set()
       self._parent: Optional[weakref.ref] = None

    @property
    def path(self) -> Path:
        """Get the path of the root."""
        return self._path
    
    @property
    def name(self) -> str:
        """Get the name of the root."""
        return self._name
    
    @property
    def id(self) -> str:
        """Get the ID of the root."""
        return self._id
    
    def contains(self, path: str | Path) -> bool:
        """
        Check if the provided path is contained within this root/leaf.

        Args:
            path (str | Path): The path to check.

        Returns:
            bool: True if the path is contained within this root/leaf, False otherwise.
        
        """
        path = Path(path).resolve()
        return str(path).startswith(str(self.path))
    
    def relpath(self, path: str | Path) -> Optional[Path]:
        """
        Get the relative path from this root/leaf to the provided path.

        Args:
            path (str | Path): The path to get the relative path to.

        Returns:
            Optional[Path]: The relative path if contained, None otherwise.
        
        """
        path = Path(path).resolve()
        if self.contains(path):
            return path.relative_to(self.path)
        return None
    
    def is_parent_of(self, other: 'RootProperties') -> bool:
        """Check if this root/leaf is a parent of another root/leaf."""
        return self.contains(other.path) and self.path != other.path
    
    def is_child_of(self, other: 'RootProperties') -> bool:
        """Check if this root/leaf is a child of another root/leaf."""
        return other.contains(self.path) and self.path != other.path
    
    def __repr__(self) -> str:
        """String representation of the root/leaf."""
        return f"{self.__class__.__name__}('{self.name}', {self.path})"
    
    def __contains__(self, item: str | Path) -> bool:
        """Check if the provided path is contained within this root/leaf."""
        return self.contains(item)
    

class SKRoot(RootProperties):
    """
    Represents the root of a project.

    Acts as a pointer to a specific directory and provides methods related to 
    paths and working with SKLeaf objects.

    There can only be one level containing SKRoots, but you can choose how you structure
    your roots:
    - create one root at the top most level
    - create multiple roots at one level for different parts of the project
      - tests, main app, etc.
      - you cannot create multiple roots at the highest possible level.
      - will create a MainRoot in the background to point to the top most level,
      - but MainRoot will not be directly accessible.
    
    """
    _instances: Dict[str, 'SKRoot'] = {} # can be one or multiple
    _instance_lock = threading.RLock() # lock for thread safety
    _root_level: Optional[str] = None # level where roots have to be created
    _main_root: Optional['MainRoot'] = None # main root if SKRoot not at top level

    def __new__(cls, path: str | Path, name: Optional[str] = None) -> 'SKRoot' | 'MainRoot':
        """
        Create a new SKRoot instance or return an existing one.

        Args:
            path (str | Path): The path for the root.
            name (Optional[str]): The name of the root.

        Returns:
            SKRoot or MainRoot: The SKRoot instance or MainRoot instance.
        
        """
        with cls._instance_lock:
            resolved_path = str(Path(path).resolve())
            project_root = get_project_root(resolved_path)

            if not os.path.exists(resolved_path):
                raise SKRootError(f"Path does not exist: {resolved_path}")
            if not os.path.isdir(resolved_path):
                raise SKRootError(f"Path is not a directory: {resolved_path}")

            
                
            
class SKLeaf(RootProperties):
    pass     
            
        
        
SKPath = str | Path | SKRoot | SKLeaf
                 



class MainRoot(RootProperties):
    """
    Manager for SKRoot instances that resides at the project root and operates
    in the background. Singleton pattern.
    
    """






