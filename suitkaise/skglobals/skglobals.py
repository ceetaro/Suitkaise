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
from typing import Optional, Any, Dict, List, Union, Tuple, Callable
from pathlib import Path
from enum import IntEnum
import json
import threading
from multiprocessing import Manager

from suitkaise.skglobals._project_indicators import project_indicators
import suitkaise.skpath.skpath as skpath
import suitkaise.sktime.sktime as sktime
from suitkaise.cereal.cereal import Cereal

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

def get_project_root(start_path: Optional[str] = None) -> str:
    """
    Get the project root of your project based on common indicators.
    
    Args:
        start_path: Path to start searching from. If None, uses caller's file path.
        
    Returns:
        str: Path to the project root.
        
    Raises:
        SKGlobalError: If project root cannot be found.
    """
    if start_path is None:
        start_path = skpath.get_caller_file_path()
    
    # Start from the directory containing the file
    if os.path.isfile(start_path):
        current = os.path.dirname(start_path)
    else:
        current = start_path

    def dir_children(path: str) -> List[str]:
        """Get directory children of a path."""
        try:
            return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        except (OSError, PermissionError):
            return []

    def file_children(path: str) -> List[str]:
        """Get file children of a path."""
        try:
            return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        except (OSError, PermissionError):
            return []

    def preprocess_indicators(indicators: dict) -> dict:
        """Resolve string references in indicators."""
        processed = {k: v.copy() if isinstance(v, dict) else v for k, v in indicators.items()}
        
        # Process file group references
        for section_name in ['common_proj_root_files']:
            if section_name not in processed:
                continue
                
            section = processed[section_name]
            for key, values in section.items():
                if not isinstance(values, set):
                    values = set(values)
                
                new_values = set()
                for value in values:
                    if isinstance(value, str) and value.startswith("file_groups{") and value.endswith("}"):
                        # Extract group name: "file_groups{'license'}" -> "license"
                        group_name = value[12:-2].strip("'\"")
                        if group_name in processed.get('file_groups', {}):
                            new_values.update(processed['file_groups'][group_name])
                    else:
                        new_values.add(value)
                section[key] = new_values
        
        # Process dir group references  
        for section_name in ['common_proj_root_dirs']:
            if section_name not in processed:
                continue
                
            section = processed[section_name]
            for key, values in section.items():
                if not isinstance(values, set):
                    values = set(values)
                
                new_values = set()
                for value in values:
                    if isinstance(value, str) and value.startswith("dir_groups{") and value.endswith("}"):
                        # Extract group name: "dir_groups{'test'}" -> "test"
                        group_name = value[11:-2].strip("'\"")
                        if group_name in processed.get('dir_groups', {}):
                            new_values.update(processed['dir_groups'][group_name])
                    else:
                        new_values.add(value)
                section[key] = new_values
        
        return processed

    def matches_pattern(name: str, patterns: set) -> bool:
        """Check if a name matches any pattern in the set."""
        for pattern in patterns:
            if pattern.endswith('.*'):
                # Handle patterns like "README.*"
                prefix = pattern[:-2]
                if name.startswith(prefix):
                    return True
            elif pattern.endswith('*'):
                # Handle patterns like "requirements*"
                prefix = pattern[:-1]
                if name.startswith(prefix):
                    return True
            elif pattern == name:
                # Exact match
                return True
        return False

    # Get platform-specific OS paths to stop at
    platform = sys.platform
    if platform == 'win32':
        common_ospaths = set(project_indicators['common_ospaths']['windows'])
    elif platform == 'linux':
        common_ospaths = set(project_indicators['common_ospaths']['linux'])
    elif platform == 'darwin':
        common_ospaths = set(project_indicators['common_ospaths']['macOS'])
    else:
        raise PlatformNotFoundError(f"Unsupported platform: {platform}")

    indicators = preprocess_indicators(project_indicators)
    
    # Walk up the directory tree
    max_depth = 20  # Prevent infinite loops
    depth = 0
    
    while depth < max_depth:
        # Stop if we've reached an OS-level directory
        if os.path.basename(current) in common_ospaths or current in common_ospaths:
            break
            
        score = 0
        required_files_found = False

        # Check files in current directory
        files = file_children(current)
        for filename in files:
            # Check necessary files
            for pattern_set in indicators['common_proj_root_files']['necessary']:
                if matches_pattern(filename, pattern_set):
                    required_files_found = True
                    break
            
            # Check indicator files
            for pattern_set in indicators['common_proj_root_files']['indicators']:
                if matches_pattern(filename, pattern_set):
                    score += 3
                    
            # Check weak indicator files  
            for pattern_set in indicators['common_proj_root_files']['weak_indicators']:
                if matches_pattern(filename, pattern_set):
                    score += 1

        # Check directories in current directory
        dirs = dir_children(current)
        for dirname in dirs:
            # Check strong indicator directories
            for pattern_set in indicators['common_proj_root_dirs']['strong_indicators']:
                if matches_pattern(dirname, pattern_set):
                    score += 10
                    
            # Check indicator directories
            for pattern_set in indicators['common_proj_root_dirs']['indicators']:
                if matches_pattern(dirname, pattern_set):
                    score += 3

        # If we found required files and sufficient score, this is likely the root
        if required_files_found and score >= 15:  # Lowered threshold for more flexibility
            return current

        # Move up one directory
        parent = os.path.dirname(current)
        if parent == current:  # Reached filesystem root
            break
        current = parent
        depth += 1

    raise SKGlobalError(f"Project root not found starting from path: {start_path}")


class GlobalLevel(IntEnum):
    """
    Enum for global variable levels.
    
    """
    TOP = 0
    UNDER = 1

class SKGlobal:
    """
    Base class for creating global variables and shared storage.

    Manages global variables even across processes and threads,
    as long as it has permission to do so.

    """


    def __init__(self,
                 level: GlobalLevel = GlobalLevel.TOP,
                 path: Optional[str] = None,
                 name: Optional[str] = None,
                 value: Optional[Any] = None,
                 auto_sync: bool = True,
                 auto_create: bool = True,
                 remove_in: Optional[float] = None):
        """
        Create and initialize a global variable.

        Args:
            level: Level to store the global variable (TOP or UNDER).
            path: Path to store the global variable. If None, auto-detects.
            name: Name to give the global variable. If None, generates one.
            value: Value to initialize the global variable with.
            auto_sync: If True, automatically sync with other processes.
                Can be changed later.
            auto_create: If True, create immediately. If False, return creator function.
            remove_in: Number of seconds that global variable stays in memory.
            
        Returns:
            Tuple: (value, creator_function) - value if auto_create=True, else creator function.

        Raises:
            SKGlobalError: If the global variable cannot be created.
            ValueError: If the level is not valid.

        """
        # validate inputs
        if level is not None and not isinstance(level, GlobalLevel):
            raise SKGlobalValueError("Invalid level. Must be an instance of GlobalLevel.")
        
        # set default values
        self.level = level if level is not None else GlobalLevel.TOP
        self.auto_sync = auto_sync
        self.remove_in = float(remove_in) if remove_in is not None else float('inf')

        # determine path
        if path is None:
            if self.level == GlobalLevel.TOP:
                self.path = get_project_root()
            else:
                caller_path = skpath.get_caller_file_path()
                self.path = os.path.dirname(caller_path)

        else:
            # normalize_path will handle invalid paths
            self.path = skpath.normalize_path(path)

        # set name, generate if not provided
        if name is None:
            name = f"global_{int(sktime.now() * 1000000) % 1000000}"
        self.name = name

        # check if value is serializable for syncing with other processes
        cereal = Cereal()
        if self.auto_sync and cereal.serializable(value):
            # serialize the value
            self.value = value
        else:
            raise SKGlobalValueError(
                "Value is not serializable. Cannot sync with other processes."
                )
        
        # get the global storage path
        self.storage = SKGlobalStorage.get_storage(self.path, self.level, self.auto_sync)

        if auto_create:
            # create the global variable
            self._create_global_variable()

    @classmethod
    def create(cls, level=GlobalLevel.TOP, path=None, name=None, value=None, 
            auto_sync=True, auto_create=True, remove_in=None):
        """
        Factory method to create SKGlobal with optional delayed creation.
        
        Returns:
            Tuple: (SKGlobal_instance, creator_function) or (SKGlobal_instance, None)
        """
        instance = cls(level, path, name, value, auto_sync, False, remove_in)  # auto_create=False
        
        if auto_create:
            instance._create_global_variable()
            return instance, None
        else:
            def creator():
                instance._create_global_variable()
                return instance.value
            return instance, creator
        
    def _create_global_variable(self):
        """Internal method to create the global variable in storage."""
        vardata = {
            'name': self.name,
            'path': self.path,
            'level': self.level,
            'value': self.value,
            'auto_sync': self.auto_sync,
            'created_at': sktime.now(),
            'last_updated': sktime.now(),
            'remove_in': self.remove_in
        }

        self.storage.set(self.name, vardata)

        # set up removal if specified
        if self.remove_in:
            def remove_later():
                sktime.sleep(self.remove_in)
                try:
                    self.storage.remove(self.name)
                except:
                    pass # might be removed already

            timer_thread = threading.Thread(target=remove_later, daemon=True)
            timer_thread.start()

    def get(self) -> Any:
        """Get the value of the global variable."""
        data = self.storage.get(self.name)
        return data['value'] if data else None
    
    def set(self, value: Any) -> None:
        """Set the value of the global variable."""
        self.value = value
        data = self.storage.get(self.name)
        if data:
            data['value'] = value
            data['last_updated'] = sktime.now()
            self.storage.set(self.name, data)

    def remove(self) -> None:
        """Remove the global variable from storage."""
        self.storage.remove(self.name)

    @classmethod
    def get_global(cls,
                   name: str,
                   path: Optional[str | Path] = None,
                   level: Optional[GlobalLevel] = GlobalLevel.TOP,
                   auto_sync: Optional[bool] = None
                   ) -> Optional['SKGlobal']:
        """
        Get an existing global variable by name.

        Checks both syncing and non-syncing storage for the variable.

        Args:
            name: Name of the global variable.
            path: Path to search for the global variable. If None, auto-detects.
            level: Level where variable is stored.
            auto_sync: if True, check syncing storage.
                        if False, check non-syncing storage.
                        if None, check the closest storage.

        Returns:
            SKGlobal: The global variable if found, else None.
        
        """
        if path is None:
            if level == GlobalLevel.TOP:
                path = get_project_root()
            else:
                caller_path = skpath.get_caller_file_path()
                path = SKGlobalStorage.find_storage_path(caller_path)

        # normalize_path will handle invalid paths
        path = skpath.normalize_path(path)

        storage = SKGlobalStorage.get_storage(path, level, auto_sync)
        data = storage.get(name)

        if data:
            global_var = cls.__new__(cls)
            global_var.name = name
            global_var.path = path
            global_var.level = level
            global_var.value = data['value']
            global_var.auto_sync = data.get('auto_sync', True)
            global_var.remove_in = data.get('remove_in', float('inf'))
            return global_var
        
        return None


class SKGlobalStorage:
    """
    Container to store and manage global variables.

    Provides persistent storage with cross-process support,
    auto-syncing, auto-removal, and JSON backup.
    """
    
    _storages: Dict[str, 'SKGlobalStorage'] = {}
    _storage_lock = threading.RLock()
    _manager = Manager()
    _startup_cleaned = False
    
    def __init__(self, path: str, level: GlobalLevel, auto_sync: bool = True):
        """
        Initialize storage for a specific path and level.

        Args:
            path: Directory path for this storage.
            level: GlobalLevel for this storage.
            auto_sync: If True, sync with other processes. If False, no syncing.
        """
        # Ensure clean startup (only runs once)
        self._ensure_clean_startup()
        
        # Normalize and validate path
        self.path = str(Path(path).resolve())
        if not os.path.exists(self.path):
            raise SKGlobalError(f"Path does not exist: {self.path}")
        
        # Set properties
        self.level = level
        self.auto_sync = auto_sync
        
        # Create storage file path
        self.storage_file = self._create_storage_file_path()
        
        # Initialize storage backend
        if auto_sync:
            self._shared_storage = self._manager.dict()
        else:
            self._shared_storage = {}
        
        self._lock = threading.RLock()
        
        # Load existing data if available
        self._load_from_file()
    
    @classmethod
    def _ensure_clean_startup(cls):
        """Ensure clean startup by resetting any stale status flags."""
        if not cls._startup_cleaned:
            cls._reset_all_loaded_statuses()
            cls._startup_cleaned = True
    
    @classmethod
    def _reset_all_loaded_statuses(cls):
        """Reset all loaded statuses in existing storage files."""
        try:
            sk_dir = cls._get_sk_dir()
            for filename in os.listdir(sk_dir):
                if filename.startswith("gs_") and filename.endswith(".sk"):
                    filepath = os.path.join(sk_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        
                        # Reset load status if present
                        if "load_status" in data:
                            data["load_status"] = False
                            with open(filepath, 'w') as f:
                                json.dump(data, f, indent=2)
                    except (json.JSONDecodeError, OSError):
                        # Remove corrupted files
                        try:
                            os.remove(filepath)
                        except OSError:
                            pass
        except (OSError, PermissionError):
            # If we can't clean up, continue anyway
            pass
    
    @classmethod
    def get_storage(cls, path: str, level: GlobalLevel, auto_sync: bool = True) -> 'SKGlobalStorage':
        """
        Get or create storage for a specific path and level.

        Args:
            path: Directory path for storage.
            level: GlobalLevel for storage.
            auto_sync: Whether to enable cross-process synchronization.

        Returns:
            SKGlobalStorage: The storage instance.
        """
        # Normalize path
        path = str(Path(path).resolve())
        
        with cls._storage_lock:
            # For TOP level, always use project root
            if level == GlobalLevel.TOP:
                path = get_project_root()
            
            # Create unique key for this storage configuration
            key = f"{path}_{level.name}_{auto_sync}"
            
            if key not in cls._storages:
                cls._storages[key] = cls(path, level, auto_sync)
            
            return cls._storages[key]
    
    def set(self, name: str, data: Dict[str, Any]) -> None:
        """Store a global variable."""
        with self._lock:
            self._shared_storage[name] = data
            self._save_to_file()
    
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a global variable."""
        with self._lock:
            if name in self._shared_storage:
                return dict(self._shared_storage[name])
            return None
    
    def remove(self, name: str) -> None:
        """Remove a global variable."""
        with self._lock:
            if name in self._shared_storage:
                del self._shared_storage[name]
                self._save_to_file()
    
    def list_variables(self) -> List[str]:
        """List all global variables in this storage."""
        with self._lock:
            return list(self._shared_storage.keys())
    
    def clear(self) -> None:
        """Clear all global variables in this storage."""
        with self._lock:
            self._shared_storage.clear()
            self._save_to_file()
    
    def _create_storage_file_path(self) -> str:
        """Create the storage file path."""
        sk_dir = self._get_sk_dir()
        
        # Create unique filename based on path and level
        path_id = skpath.idshort(self.path, 6)
        dirname = os.path.basename(self.path) or "root"
        filename = f"gs_{dirname}_{self.level.name.lower()}_{path_id}.sk"
        
        return os.path.join(sk_dir, filename)
    
    @classmethod
    def _get_sk_dir(cls) -> str:
        """Get or create the .sk directory path."""
        root = get_project_root()
        sk_dir = os.path.join(root, '.sk')
        os.makedirs(sk_dir, exist_ok=True)
        return sk_dir
    
    def _load_from_file(self) -> bool:
        """Load stored variables from JSON file."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                
                # Validate file format
                if data.get('path') != self.path:
                    return False
                
                # Load variables
                variables = data.get('variables', {})
                for name, var_data in variables.items():
                    self._shared_storage[name] = var_data
                
                return True
        except (json.JSONDecodeError, OSError, KeyError):
            # If file is corrupted or unreadable, start fresh
            pass
        
        return False
    
    def _save_to_file(self) -> None:
        """Save current variables to JSON file."""
        try:
            with self._lock:
                # Prepare data to save
                data = {
                    "path": self.path,
                    "level": self.level.name,
                    "auto_sync": self.auto_sync,
                    "created_at": sktime.now(),
                    "last_saved": sktime.now(),
                    "variables": dict(self._shared_storage)
                }
                
                # Atomic write operation
                temp_file = self.storage_file + '.tmp'
                with open(temp_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                
                # Replace original file atomically
                os.replace(temp_file, self.storage_file)
                
        except (OSError, TypeError) as e:
            # Log warning but don't crash the application
            print(f"Warning: Could not save global storage to {self.storage_file}: {e}")
    
    def sync_with(self, other_storage: 'SKGlobalStorage', 
                  key_filter: Optional[Callable[[str], bool]] = None) -> None:
        """
        Synchronize variables with another storage.
        
        Args:
            other_storage: Storage to sync with.
            key_filter: Optional function to filter which keys to sync.
        """
        with self._lock, other_storage._lock:
            keys_to_sync = self.list_variables()
            if key_filter:
                keys_to_sync = [k for k in keys_to_sync if key_filter(k)]
            
            for key in keys_to_sync:
                data = self.get(key)
                if data:
                    other_storage.set(key, data)

    def has_variable(self, name: str) -> bool:
        """
        Check if a variable with the given name exists.
        
        Args:
            name: Variable name to check.
            
        Returns:
            bool: True if variable exists.
        """
        with self._lock:
            return name in self._shared_storage
        
    def contains(self, item) -> bool:
        """
        Explicit method to check if a variable exists in storage.
        
        Args:
            item: Either an SKGlobal instance or a variable name (string).
            
        Returns:
            bool: True if the variable exists in storage.
            
        Usage:
        ```python
        storage.contains(my_global) # SKGlobal instance
        storage.contains("var_name") # Variable name
        ```
        """
        return self.__contains__(item)

    def __contains__(self, item) -> bool:
        """
        Check if a variable exists in storage using 'in' operator.
        
        Args:
            item: Either an SKGlobal instance or a variable name (string).
            
        Returns:
            bool: True if the variable exists in storage.
            
        Usage:
        ```python
        if my_global in storage: # SKGlobal instance
        if "var_name" in storage: # Variable name
        ```
        """
        with self._lock:
            if isinstance(item, SKGlobal):
                return item.name in self._shared_storage
            elif isinstance(item, str):
                return item in self._shared_storage
            else:
                # For any other type, return False
                return False
    
    def __repr__(self) -> str:
        """String representation of the storage."""
        return f"SKGlobalStorage(path='{self.path}', level={self.level.name}, auto_sync={self.auto_sync})"      

if __name__ == "__main__":
    # test the SKGlobal module


