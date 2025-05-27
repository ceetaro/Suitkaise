# add license here

# suitkaise/skroot/skroot.py

"""
SKRoot - Project Resource Management System

Phase 1: Core Structure
- SKRoot: Global project coordinator (singleton)
- SKBranch: Directory/section manager with hierarchy
- SKLeaf: Individual resource nodes

This module provides a hierarchical system for managing project resources,
tracking usage, and organizing project structure. Integrates with SKGlobal
for cross-process coordination.

Usage:
    # Initialize project root
    root = SKRoot.create_root()
    
    # Create branches for different project sections
    api_branch = root.create_branch("api", path="src/api/")
    data_branch = root.create_branch("data", path="data/")
    
    # Add resources to branches
    config_leaf = api_branch.create_leaf("config", resource_type="file", 
                                        path="src/api/config.json")
    
    # Access from anywhere in the project
    root = SKRoot.get_root()
    api_config = root.get_leaf("api.config")
"""

import os
import json
from typing import Optional, Dict, List, Any, Set # using | for Union.
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
import threading

# Import suitkaise modules
from suitkaise.skglobals import SKGlobal, GlobalLevel, get_project_root, SKGlobalStorage
import suitkaise.skpath.skpath as skpath
import suitkaise.sktime.sktime as sktime
from suitkaise.cereal import serialize, deserialize, serializable

class SKRootError(Exception):
    """Base exception for SKRoot system."""
    pass

class SKRootNotInitializedError(SKRootError):
    """Raised when trying to access root before initialization."""
    pass

class SKBranchError(SKRootError):
    """Exception for branch-related errors."""
    pass

class SKLeafError(SKRootError):
    """Exception for leaf-related errors."""
    pass

# Resource Types (extensible for Phase 2)
class ResourceType(Enum):
    """Types of resources that can be managed."""
    FILE = "file"
    DIRECTORY = "directory"
    CONFIG = "config"
    DATABASE = "database"
    API_ENDPOINT = "api_endpoint"
    SERVICE = "service"
    CUSTOM = "custom"

@dataclass
class ResourceMetadata:
    """Metadata for tracked resources."""
    resource_type: ResourceType
    path: Optional[str] = None
    created_at: float = field(default_factory=sktime.now)
    last_accessed: float = field(default_factory=sktime.now)
    access_count: int = 0
    size_bytes: Optional[int] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'resource_type': self.resource_type.value,
            'path': self.path,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'access_count': self.access_count,
            'size_bytes': self.size_bytes,
            'properties': self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceMetadata':
        """Create from dictionary."""
        return cls(
            resource_type=ResourceType(data['resource_type']),
            path=data.get('path'),
            created_at=data.get('created_at', sktime.now()),
            last_accessed=data.get('last_accessed', sktime.now()),
            access_count=data.get('access_count', 0),
            size_bytes=data.get('size_bytes'),
            properties=data.get('properties', {})
        )

class SKLeaf:
    """
    Individual resource node in the project hierarchy.

    Represents files, configs, or any project resource that belongs to a branch.
    Tracks basic usage and metadata, with foundation for monitoring.
    
    """

    @skpath.autopath()
    def __init__(self, name: str,
                 branch: 'SKBranch',
                 resource_type: ResourceType | str,
                 path: Optional[str] = None,
                 value: Any = None,
                 properties: Optional[Dict[str, Any]] = None):
        """
        Initialize a leaf resource.

        Args:
            name: Unique name within the branch
            branch: Parent branch this leaf belongs to
            resource_type: Type of resource (file, config, etc.)
            path: File system path if applicable
            value: Associated value/data
            properties: Additional properties

        """
        self.name = name
        self.branch = branch
        self.value = value

        # handle resource type
        if isinstance(resource_type, str):
            try:
                resource_type = ResourceType(resource_type)
            except ValueError:
                resource_type = ResourceType.CUSTOM

        self.metadata = ResourceMetadata(
            resource_type=resource_type,
            path=path,
            properties=properties or {}
        )

        # auto detect file info if path is provided
        if path and os.path.exists(skpath.normalize_path(path)):
            self._update_file_info()

        self._lock = threading.RLock()

    def _update_file_info(self):
        """Update metadata for file resources."""
        if self.metadata.path and os.path.exists(self.metadata.path):
            try:
                stat = os.stat(self.metadata.path)
                self.metadata.size_bytes = stat.st_size
                self.metadata.properties['modified_at'] = stat.st_mtime
            except OSError:
                pass

    def access(self) -> Any:
        """Access the resource, updating usage metadata."""
        with self._lock:
            self.metadata.last_accessed = sktime.now()
            self.metadata.access_count += 1
            
            # Update branch statistics
            self.branch._record_leaf_access(self.name)
            
            return self.value

    def set_value(self, value: Any):
        """Set the leaf value."""
        with self._lock:
            self.value = value
            self.metadata.last_accessed = sktime.now()

    def get_full_path(self) -> str:
        """Get the full hierarchical path (branch.leaf)."""
        return f"{self.branch.get_full_path()}.{self.name}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'branch_path': self.branch.get_full_path(),
            'value': self.value if serializable(self.value) else str(self.value),
            'metadata': self.metadata.to_dict()
        }
    
    def __repr__(self) -> str:
        return f"SKLeaf(name='{self.name}', type={self.metadata.resource_type.value}, branch='{self.branch.name}')"


class SKBranch:
    """
    Directory/section manager in the project hierarchy.

    Represents logical project sections, manages hierarchy relationships, 
    and contains leaves and sub-branches with basic policy foundation.
    
    """

    def __init__(self,
                 name: str,
                 path: Optional[str] = None,
                 parent: Optional['SKBranch'] = None,
                 description: Optional[str] = None,
                 properties: Optional[Dict[str, Any]] = None):
        """
        Initialize a branch.

        Args:
        name: branch name (unique within parent)
        path: file system path for this branch (optional)
        parent: parent branch (None for root)
        description: optional description for the branch
        properties: additional metadata properties

        """
        self.name = name
        self.path = skpath.normalize_path(path) if path else None
        self.parent = parent
        self.description = description or ""
        self.properties = properties or {}

        # children
        self.child_branches: Dict[str, 'SKBranch'] = {}
        self.leaves: Dict[str, SKLeaf] = {}

        # metadata
        self.created_at = sktime.now()
        self.last_accessed = sktime.now()
        self.access_count = 0
        self.leaf_access_counts: Dict[str, int] = {}

        # policy
        self.policies: Dict[str, Any] = {}

        self._lock = threading.RLock()

        # store in global storage
        if self.path:
            try:
                storage = SKGlobalStorage.get_storage(path=self.path)
                if not storage:
                    raise SKBranchError(f"Failed to initialize storage for branch path '{self.path}'.")

            except Exception as e:
                raise SKBranchError(f"Failed to initialize storage for branch path '{self.path}': {e}")
        else:
            # assume user wants this branch stored in top level global storage
            try:
                self.path = get_project_root()
                storage = SKGlobalStorage.get_top_level_storage()
            except Exception as e:
                raise SKBranchError(f"Failed to initialize top level storage for branch '{self.name}': {e}")
        
        info = storage.get_storage_info()
        if not info:
            raise SKBranchError(f"Failed to retrieve storage info for branch '{self.name}'.")
        self.level = info.get('level', None)
        if not self.level:
            raise SKBranchError(f"Branch '{self.name}' has no storage level defined.")
        
        self._storage_key = f"skroot_branch--{self.get_full_path()}"
        self._sync_to_global_storage()

        
    def get_full_path(self) -> str:
        """
        Get the full hierarchical path of this branch.

        This is not the file system path, but the logical path from 
        the SKRoot to this branch, following SKRoot/MainBranch/Other/Branches/ThisBranch.
        
        """
        if self.parent:
            return f"{self.parent.get_full_path()}.{self.name}"
        return self.name
    
    def create_child_branch(self, name: str,
                            path: Optional[str] = None,
                            description: Optional[str] = None,
                            **kwargs) -> 'SKBranch':
        """
        Create a new child branch under this branch.

        Args:
            name: Unique name for the new branch
            path: Optional file system path for the branch
            description: Optional description for the branch
            **kwargs: Additional properties or metadata

        Returns:
            SKBranch: The newly created child branch
        
        """
        with self._lock:
            if name in self.child_branches:
                raise SKBranchError(f"Child branch '{name}' already exists in '{self.name}'.")

            new_branch = SKBranch(name=name,
                                  path=path,
                                  parent=self,
                                  description=description,
                                  properties=kwargs.get('properties', {}))
            self.child_branches[name] = new_branch
            self._sync_to_global_storage()

            return new_branch
        
    def create_leaf(self,
                    name: str,
                    resource_type: ResourceType | str,
                    path: Optional[str] = None,
                    value: Any = None,
                    **kwargs) -> SKLeaf:
        """
        Create a leaf resource in this branch.

        Args:
            name: leaf name
            resource_type: type of resource (file, config, etc.)
            path: optional file system path for the resource
            value: initial value for the resource
            **properties: additional properties for the resource

        Returns:
            SKLeaf: The newly created leaf resource
        
        """
        with self._lock:
            if name in self.leaves:
                raise SKLeafError(f"Leaf '{name}' already exists in branch '{self.name}'.")
            
            new_leaf = SKLeaf(name=name,
                              branch=self,
                              resource_type=resource_type,
                              path=path,
                              value=value,
                              properties=kwargs.get('properties', {}))
            self.leaves[name] = new_leaf
            self._sync_to_global_storage()

            return new_leaf
        
    def get_child_branch(self, name: str) -> Optional['SKBranch']:
        """Get a child branch by name."""
        return self.child_branches.get(name)
        
    def get_leaf(self, name: str) -> Optional[SKLeaf]:  
        """Get a leaf resource by name."""
        return self.leaves.get(name)
            
    def find_resource(self, path: str) -> Optional['SKBranch' | SKLeaf]:
        """
        Find a resource by its hierarchical path. (not file system path)

        Args:
            path: hierarchical path to the resource
            Example: api.config or data.database.table1.table1relationships
        
        Returns:
            found branch or leaf resource, or None if not found.

        """
        parts = path.split('.')
        current = self

        # navigate through branches
        for part in parts[:-1]:
            if part in current.child_branches:
                current = current.child_branches[part]
            else:
                return None
            
        # last part can be a leaf or branch
        final = parts[-1]
        if final in current.child_branches:
            return current.child_branches[final]
        elif final in current.leaves:
            return current.leaves[final]
        
        return None
        
    def list_all_resources(self, incl_metadata: bool = False) -> Dict[str, Any]:
        """
        List all resources (branches and leaves) in this branch.

        Args:
            incl_metadata: If True, include metadata for each resource

        Returns:
            Dict[str, Any]: Dictionary of all resources.

        """
        result = {
            'branch_info': {
                'name': self.name,
                'full_path': self.get_full_path(),
                'path': self.path,
                'description': self.description
            },
            'children': {},
            'leaves': {}
        }
        
        if incl_metadata:
            result['branch_info'].update({
                'created_at': self.created_at,
                'last_accessed': self.last_accessed,
                'access_count': self.access_count,
                'leaf_access_stats': self.leaf_access_counts,
                'properties': self.properties
            })
        
        for name, child in self.child_branches.items():
            result['children'][name] = child.list_all_resources(incl_metadata)

        for name, leaf in self.leaves.items():
            if incl_metadata:
                result['leaves'][name] = leaf.to_dict()
            else:
                result['leaves'][name] = {
                    'name': leaf.name,
                    'type': leaf.metadata.resource_type.value,
                    'path': leaf.metadata.path,
                }

        return result
    
    def _record_leaf_access(self, leaf_name: str):
        """Record access to a leaf resource."""
        with self._lock:
            self.last_accessed = sktime.now()
            self.access_count += 1
            self.leaf_access_counts[leaf_name] = self.leaf_access_counts.get(leaf_name, 0) + 1

    def _sync_to_global_storage(self):
        """Sync branch data to global storage."""
        try:
            # create serialized representation
            data = {
                'name': self.name,
                'path': self.path,
                'level': self.level,
                'parent_path': self.parent.get_full_path() if self.parent else None,
                'description': self.description,
                'properties': self.properties,
                'created_at': self.created_at,
                'last_accessed': self.last_accessed,
                'access_count': self.access_count,
                'leaf_access_stats': self.leaf_access_counts,
                'policies': self.policies,
                'child_branches': list(self.child_branches.keys()),
                'leaves_data': {name: leaf.to_dict() for name, leaf in self.leaves.items()}
            }

            # store in appropriate global storage
            if self.level == GlobalLevel.TOP:
                # ensure we get the top-level storage
                storage_path = get_project_root()
            else:
                # get storage for this branch's path
                storage_path = self.path

            global_var = SKGlobal(
                name=self._storage_key,
                value=data,
                level=self.level,
                path=storage_path,
                auto_sync=True
            )

        except Exception as e:
            raise SKBranchError(f"Failed to sync branch '{self.name}' to global storage: {e}")
        
    def __repr__(self) -> str:
        child_count = len(self.child_branches)
        leaf_count = len(self.leaves)
        return f"SKBranch(name='{self.name}', children={child_count}, leaves={leaf_count})"
    
class SKRoot:
    """
    Global project coordinator (singleton).
    
    Discovers and maps project structure, maintains registry of all branches
    and leaves, provides central access point for the entire system.   
    
    """
    _instance: Optional['SKRoot'] = None
    _lock = threading.RLock()
    _storage_key = "skroot_globalroot"

    def __new__(cls):
        """Control instance creation for the singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SKRoot, cls).__new__(cls)
                cls._init_skroot(cls._instance)
        return cls._instance
    
    def _init_skroot(self):
        """Initialize the SKRoot singleton."""
        self.project_root = get_project_root()
        self.created_at = sktime.now()
        self.last_accessed = sktime.now()

        # registry of top level branches
        self.branches: Dict[str, SKBranch] = {}

        # project discovery metadata
        self.project_structure: Dict[str, Any] = {}
        self.discovered_at: Optional[float] = None

        # cross-process coordination
        self._sync_to_global_storage()

    @classmethod
    def create_root(cls, force_recreate: bool = False) -> 'SKRoot':
        """
        Create or retrieve the global project root.

        Args:
            force_recreate: If True, force re-creation of the root even if it exists.

        Returns:
            SKRoot: The global project root instance.
        
        """
        with cls._lock:
            if cls._instance is None or force_recreate:
                if force_recreate and cls._instance:
                    cls._instance._cleanup()

                cls._instance = cls.__new__(cls)
                cls._instance._init_skroot(cls._instance)

            return cls._instance
        
    @classmethod
    def get_root(cls) -> 'SKRoot':
        """
        Get the existing root instance.
        
        Returns:
            The SKRoot singleton instance
            
        Raises:
            SKRootNotInitializedError: If root hasn't been created yet
        """
        if cls._instance is None:
            # Try to load from global storage
            try:
                global_var = SKGlobal.get_global(cls._storage_key, level=GlobalLevel.TOP)
                if global_var:
                    # Restore from storage
                    cls._instance = cls._restore_from_storage(global_var.get())
                    return cls._instance
            except Exception as e:
                print(f"Warning: Could not restore root from storage: {e}")
            
            raise SKRootNotInitializedError("SKRoot not initialized. Call SKRoot.create_root() first.")
        
        return cls._instance
    
    @classmethod
    def _restore_from_storage(cls, data: Dict[str, Any]) -> 'SKRoot':
        """Restore root instance from storage data."""
        # Create new instance (bypassing singleton check)
        instance = object.__new__(cls)
        instance.project_root = data.get('project_root', get_project_root())
        instance.created_at = data.get('created_at', sktime.now())
        instance.last_accessed = sktime.now()
        instance.branches = {}
        instance.project_structure = data.get('project_structure', {})
        instance.discovered_at = data.get('discovered_at')
        
        # Restore branches (simplified for Phase 1)
        branch_registry = data.get('branch_registry', {})
        for name, branch_info in branch_registry.items():
            try:
                # Create branch without parent for now (will be linked in Phase 2)
                branch = SKBranch(
                    name=name,
                    path=branch_info.get('path'),
                    description=branch_info.get('description'),
                    properties=branch_info.get('properties', {})
                )
                instance.branches[name] = branch
            except Exception as e:
                print(f"Warning: Could not restore branch '{name}': {e}")
        
        cls._instance = instance
        return instance
    
    def create_branch(self, name: str, path: Optional[str] = None, 
                     description: Optional[str] = None, **properties) -> SKBranch:
        """
        Create a top-level branch.
        
        Args:
            name: Branch name
            path: File system path this branch represents
            description: Optional description
            **properties: Additional properties
            
        Returns:
            Created branch
        """
        with self._lock:
            if name in self.branches:
                raise SKBranchError(f"Branch '{name}' already exists")
            
            branch = SKBranch(name=name, path=path, parent=None, 
                            description=description, properties=properties)
            self.branches[name] = branch
            
            self.last_accessed = sktime.now()
            self._sync_to_global_storage()
            
            return branch
    
    def get_branch(self, name: str) -> Optional[SKBranch]:
        """Get a top-level branch by name."""
        return self.branches.get(name)
    
    def get_leaf(self, path: str) -> Optional[SKLeaf]:
        """
        Get a leaf by hierarchical path.
        
        Args:
            path: Dot-separated path (e.g., 'api.config')
            
        Returns:
            Found leaf or None
        """
        parts = path.split('.')
        if not parts:
            return None
        
        branch_name = parts[0]
        if branch_name not in self.branches:
            return None
        
        if len(parts) == 1:
            return None  # Path points to branch, not leaf
        
        resource = self.branches[branch_name].find_resource('.'.join(parts[1:]))
        return resource if isinstance(resource, SKLeaf) else None
    
    def find_resource(self, path: str) -> Optional[Union[SKBranch, SKLeaf]]:
        """
        Find any resource (branch or leaf) by hierarchical path.
        
        Args:
            path: Dot-separated path
            
        Returns:
            Found resource or None
        """
        parts = path.split('.')
        if not parts:
            return None
        
        branch_name = parts[0]
        if branch_name not in self.branches:
            return None
        
        branch = self.branches[branch_name]
        if len(parts) == 1:
            return branch
        
        return branch.find_resource('.'.join(parts[1:]))
    
    def discover_project_structure(self, max_depth: int = 3) -> Dict[str, Any]:
        """
        Auto-discover project structure and create branches.
        
        Args:
            max_depth: Maximum directory depth to scan
            
        Returns:
            Discovered structure information
        """
        structure = {
            'directories': {},
            'files': {},
            'discovered_at': sktime.now(),
            'project_root': self.project_root
        }
        
        try:
            # Scan project directory
            for root, dirs, files in os.walk(self.project_root):
                # Calculate depth
                relative_path = os.path.relpath(root, self.project_root)
                depth = len(relative_path.split(os.sep)) if relative_path != '.' else 0
                
                if depth > max_depth:
                    continue
                
                # Skip hidden and cache directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__']]
                
                # Record directory structure
                if relative_path != '.':
                    structure['directories'][relative_path] = {
                        'path': root,
                        'depth': depth,
                        'subdirs': dirs,
                        'files': len(files),
                        'python_files': len([f for f in files if f.endswith('.py')])
                    }
                    
                    # Auto-create branch for significant directories
                    if self._is_significant_directory(root, dirs, files):
                        branch_name = os.path.basename(root)
                        if branch_name not in self.branches:
                            try:
                                self.create_branch(
                                    name=branch_name,
                                    path=root,
                                    description=f"Auto-discovered: {relative_path}",
                                    auto_created=True,
                                    discovery_score=self._calculate_significance_score(root, dirs, files)
                                )
                            except Exception as e:
                                print(f"Warning: Could not auto-create branch for {root}: {e}")
        
        except Exception as e:
            print(f"Warning: Project discovery failed: {e}")
        
        self.project_structure = structure
        self.discovered_at = structure['discovered_at']
        self._sync_to_global_storage()
        
        return structure
    
    def _is_significant_directory(self, path: str, subdirs: List[str], files: List[str]) -> bool:
        """Determine if a directory is significant enough to become a branch."""
        # Has Python files
        if any(f.endswith('.py') for f in files):
            return True
        
        # Has configuration files
        config_files = [f for f in files if any(f.endswith(ext) for ext in ['.json', '.yaml', '.yml', '.toml', '.ini'])]
        if config_files:
            return True
        
        # Has multiple subdirectories
        if len(subdirs) >= 2:
            return True
        
        # Contains specific important files
        important_files = ['README.md', 'requirements.txt', 'setup.py', 'pyproject.toml']
        if any(f in files for f in important_files):
            return True
        
        return False
    
    def _calculate_significance_score(self, path: str, subdirs: List[str], files: List[str]) -> float:
        """Calculate significance score for auto-discovery."""
        score = 0.0
        
        # Python files
        python_files = [f for f in files if f.endswith('.py')]
        score += len(python_files) * 2
        
        # Configuration files
        config_files = [f for f in files if any(f.endswith(ext) for ext in ['.json', '.yaml', '.yml', '.toml'])]
        score += len(config_files) * 1.5
        
        # Subdirectories
        score += len(subdirs) * 1
        
        # Important files
        important_files = ['README.md', 'requirements.txt', 'setup.py']
        score += sum(3 for f in important_files if f in files)
        
        return score
    
    def get_project_overview(self) -> Dict[str, Any]:
        """Get comprehensive project overview."""
        return {
            'project_root': self.project_root,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'branches': {name: {
                'name': branch.name,
                'path': branch.path, 
                'description': branch.description,
                'children_count': len(branch.children),
                'leaves_count': len(branch.leaves),
                'access_count': branch.access_count
            } for name, branch in self.branches.items()},
            'project_structure': self.project_structure,
            'discovered_at': self.discovered_at,
            'total_branches': len(self.branches),
            'auto_created_branches': len([b for b in self.branches.values() 
                                        if b.properties.get('auto_created', False)])
        }
    
    def _sync_to_global_storage(self):
        """Sync root data to global storage."""
        try:
            data = {
                'project_root': self.project_root,
                'created_at': self.created_at,
                'last_accessed': self.last_accessed,
                'branch_registry': {name: {
                    'name': branch.name,
                    'path': branch.path,
                    'description': branch.description,
                    'properties': branch.properties,
                    'created_at': branch.created_at
                } for name, branch in self.branches.items()},
                'project_structure': self.project_structure,
                'discovered_at': self.discovered_at
            }
            
            global_var = SKGlobal(
                name=self._storage_key,
                value=data,
                level=GlobalLevel.TOP,
                auto_sync=True
            )
            
        except Exception as e:
            print(f"Warning: Failed to sync root to global storage: {e}")
    
    def _cleanup(self):
        """Clean up resources."""
        # Clear branches
        self.branches.clear()
        
        # Remove from global storage
        try:
            global_var = SKGlobal.get_global(self._storage_key, level=GlobalLevel.TOP)
            if global_var:
                global_var.remove()
        except Exception:
            pass
    
    def __repr__(self) -> str:
        return f"SKRoot(project_root='{self.project_root}', branches={len(self.branches)})"

# Convenience functions for quick access
def create_root(force_recreate: bool = False) -> SKRoot:
    """Create or get the global root instance."""
    return SKRoot.create_root(force_recreate)

def get_root() -> SKRoot:
    """Get the existing root instance."""
    return SKRoot.get_root()

def get_branch(name: str) -> Optional[SKBranch]:
    """Get a branch by name."""
    try:
        root = get_root()
        return root.get_branch(name)
    except SKRootNotInitializedError:
        return None

def get_leaf(path: str) -> Optional[SKLeaf]:
    """Get a leaf by hierarchical path."""
    try:
        root = get_root()
        return root.get_leaf(path)
    except SKRootNotInitializedError:
        return None

def find_resource(path: str) -> Optional[SKBranch | SKLeaf]:
    """Find any resource by hierarchical path."""
    try:
        root = get_root()
        return root.find_resource(path)
    except SKRootNotInitializedError:
        return None


   
