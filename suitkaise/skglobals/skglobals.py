# add license here

# suitkaise/skglobals/skglobals.py

"""
Module for creating and managing global variables and registries.

- Create hierarchical global variables using directory-based storage
- Cross-process global storage with multiprocessing.Manager support  
- Two-tier storage system: local storage + cross-process storage
- Synchronized removal timing across all processes and storages
- TOP level storage aggregates all UNDER level storages
"""

import os
import sys
from typing import Optional, Any, Dict, List, Tuple, Callable, Union
from pathlib import Path
from enum import IntEnum
import json
import threading
import time
import atexit
from dataclasses import dataclass

from suitkaise.skglobals._project_indicators import project_indicators
import suitkaise.skpath.skpath as skpath
import suitkaise.sktime.sktime as sktime
from suitkaise.cereal import Cereal, create_shared_dict

# TODO make sure .sk files are created in the project root directory, not the current directory

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

@dataclass
class RemovalSchedule:
    """Schedule for variable removal."""
    variable_name: str
    storage_path: str
    removal_timestamp: float
    created_at: float

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
    """Enum for global variable levels."""
    TOP = 0
    UNDER = 1


class RemovalManager:
    """Manages synchronized removal of variables across all storages."""
    
    _instance: Optional['RemovalManager'] = None
    _lock = threading.RLock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._scheduled_removals: Dict[str, RemovalSchedule] = {}
        self._cleanup_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._initialized = True
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
    
    def _start_cleanup_thread(self):
        """Start the background cleanup thread."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_worker,
                daemon=True,
                name="SKGlobal-RemovalManager"
            )
            self._cleanup_thread.start()
    
    def _cleanup_worker(self):
        """Background worker that handles scheduled removals."""
        while not self._shutdown_event.is_set():
            try:
                current_time = sktime.now()
                removals_to_process = []
                
                with self._lock:
                    # Find removals that are due
                    for key, schedule in self._scheduled_removals.items():
                        if current_time >= schedule.removal_timestamp:
                            removals_to_process.append(schedule)
                    
                    # Remove from schedule
                    for schedule in removals_to_process:
                        key = f"{schedule.storage_path}::{schedule.variable_name}"
                        self._scheduled_removals.pop(key, None)
                
                # Process removals (outside lock to avoid deadlock)
                for schedule in removals_to_process:
                    self._execute_removal(schedule)
                
                # Sleep briefly before next check
                self._shutdown_event.wait(0.1)
                
            except Exception as e:
                print(f"Warning: RemovalManager cleanup error: {e}")
                self._shutdown_event.wait(1.0)
    
    def _execute_removal(self, schedule: RemovalSchedule):
        """Execute a scheduled removal across all storages."""
        try:
            # Get the storage and remove the variable
            storage = SKGlobalStorage.get_storage(schedule.storage_path, auto_sync=True)
            if storage:
                storage.remove_variable(schedule.variable_name, synchronized=True)
        except Exception as e:
            print(f"Warning: Failed to execute scheduled removal for {schedule.variable_name}: {e}")
    
    def schedule_removal(self, variable_name: str, storage_path: str, remove_in_seconds: float):
        """Schedule a variable for removal."""
        current_time = sktime.now()
        removal_time = current_time + remove_in_seconds
        
        schedule = RemovalSchedule(
            variable_name=variable_name,
            storage_path=storage_path,
            removal_timestamp=removal_time,
            created_at=current_time
        )
        
        with self._lock:
            key = f"{storage_path}::{variable_name}"
            self._scheduled_removals[key] = schedule
        
        # Ensure cleanup thread is running
        self._start_cleanup_thread()
    
    def cancel_removal(self, variable_name: str, storage_path: str):
        """Cancel a scheduled removal."""
        with self._lock:
            key = f"{storage_path}::{variable_name}"
            self._scheduled_removals.pop(key, None)
    
    def get_scheduled_removals(self) -> List[RemovalSchedule]:
        """Get all scheduled removals."""
        with self._lock:
            return list(self._scheduled_removals.values())
    
    def shutdown(self):
        """Shutdown the removal manager."""
        self._shutdown_event.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=1.0)


class SKGlobal:
    """
    Global variable with hierarchical directory-based cross-process storage.
    
    Variables are stored in a two-tier system:
    - TOP level: Project root storage that aggregates all UNDER storages
    - UNDER level: Directory-specific storage that syncs with TOP
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
            auto_create: If True, create immediately. If False, return creator function.
            remove_in: Number of seconds that global variable stays in memory.
        """
        # Validate inputs
        if level is not None and not isinstance(level, GlobalLevel):
            raise SKGlobalValueError("Invalid level. Must be an instance of GlobalLevel.")
        
        # Set default values
        self.level = level if level is not None else GlobalLevel.TOP
        self.auto_sync = auto_sync
        if remove_in is not None and remove_in > 0 and remove_in != float('inf'):
            self.remove_in = float(remove_in)
        else:
            self.remove_in = None
            
        # Determine path
        if path is None:
            if self.level == GlobalLevel.TOP:
                self.path = get_project_root()
            else:
                caller_path = skpath.get_caller_file_path()
                self.path = os.path.dirname(caller_path)
        else:
            self.path = skpath.normalize_path(path)

        # Set name, generate if not provided
        if name is None:
            name = f"global_{int(sktime.now() * 1000000) % 1000000}"
        self.name = name


        # Check if value is serializable for syncing with other processes
        if self.auto_sync and value is not None:
            try:
                cereal = Cereal()
                # First check if it's serializable
                is_serializable = cereal.serializable(value, mode='internal')
                if not is_serializable:
                    raise SKGlobalValueError(
                        "Value is not serializable. Cannot sync with other processes. "
                        "Set auto_sync=False to use non-serializable values."
                    )
                # Double-check by actually trying to serialize
                cereal.serialize(value, mode='internal')
            except SKGlobalValueError:
                # Re-raise our own errors
                raise
            except Exception as e:
                # Any other serialization error means it's not serializable
                raise SKGlobalValueError(
                    f"Value failed serialization test: {e}. "
                    "Set auto_sync=False to use non-serializable values."
                )
        
        self.value = value
        
        # Get the global storage
        self.storage = SKGlobalStorage.get_storage(self.path, self.auto_sync)

        if auto_create:
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
        current_process_id = str(os.getpid())
        current_time = sktime.now()
        
        vardata = {
            'name': self.name,
            'path': self.path,
            'level': self.level,
            'value': self.value,
            'auto_sync': self.auto_sync,
            'created_at': current_time,
            'last_updated': current_time,
            'remove_in': self.remove_in,
            'created_by_process': current_process_id
        }

        self.storage.set_local(self.name, vardata)

        # Schedule removal if specified
        if self.remove_in:
            removal_manager = RemovalManager()
            removal_manager.schedule_removal(self.name, self.path, self.remove_in)

    def get(self) -> Any:
        """Get the value of the global variable."""
        data = self.storage.get_local(self.name)
        if data is None:
            # Check cross-process data
            data = self.storage.get_cross_process(self.name)
        return data['value'] if data else None
    
    def set(self, value: Any) -> None:
        """Set the value of the global variable."""
        self.value = value
        data = self.storage.get_local(self.name)
        if data:
            data['value'] = value
            data['last_updated'] = sktime.now()
            self.storage.set_local(self.name, data)

    def remove(self) -> None:
        """Remove the global variable from storage."""
        # Cancel scheduled removal
        if self.remove_in:
            removal_manager = RemovalManager()
            removal_manager.cancel_removal(self.name, self.path)
        
        self.storage.remove_variable(self.name)

    @classmethod
    def get_global(cls, name: str, path: Optional[str] = None, 
                level: GlobalLevel = GlobalLevel.TOP,
                auto_sync: Optional[bool] = None) -> Optional['SKGlobal']:
        """Get an existing global variable by name."""
        if path is None:
            path = get_project_root() if level == GlobalLevel.TOP else skpath.get_caller_file_path()
        
        if auto_sync is None:
            auto_sync = True
        
        storage = SKGlobalStorage.get_storage(path, auto_sync)
        data = storage.get_local(name)
        
        if data:
            global_var = cls.__new__(cls)
            global_var.name = name
            global_var.path = path
            global_var.level = level
            global_var.value = data['value']
            global_var.storage = storage
            global_var.auto_sync = data.get('auto_sync', True)
            remove_in_data = data.get('remove_in')
            global_var.remove_in = remove_in_data if remove_in_data is not None else None
            return global_var
        
        return None


class SKGlobalStorage:
    """
    Hierarchical directory-based storage with two-tier system:
    
    Each directory gets:
    - storage: Direct data (local_data + cross_process_data by process)
    - cross_process_storage: Data from other directories (organized by path)
    """
    
    _storages: Dict[str, 'SKGlobalStorage'] = {}
    _storage_lock = threading.RLock()
    _startup_cleaned = False
    _cereal = Cereal()
    
    @classmethod
    @skpath.autopath()
    def get_storage(cls, path: str, auto_sync: bool = True) -> 'SKGlobalStorage':
        """
        Get or create directory-based storage.

        Args:
            path: Directory path for storage.
            auto_sync: Whether to enable cross-process synchronization.

        Returns:
            SKGlobalStorage: The storage instance for this directory.
        """
        # Normalize path
        path = str(Path(path).resolve())
        
        with cls._storage_lock:
            # Create unique key for this directory and sync setting
            key = f"{path}_{auto_sync}"
            
            if key not in cls._storages:
                cls._storages[key] = cls(path, auto_sync)
            
            return cls._storages[key]
        
    @classmethod
    def get_top_level_storage(cls, auto_sync: bool = True) -> 'SKGlobalStorage':
        """
        Get or create the top-level storage for the project root directory.
        
        Args:
            auto_sync: Whether to enable cross-process synchronization.
            
        Returns:
            SKGlobalStorage: The top-level storage instance.

        """
        project_root = get_project_root()
        return cls.get_storage(project_root, auto_sync)
    
    def __init__(self, path: str, auto_sync: bool = True):
        """Initialize directory-based storage with two-tier system."""
        self._ensure_clean_startup()

        # Validate path exists before normalization
        if not os.path.exists(path):
            raise SKGlobalError(f"Storage path does not exist: {path}")
        
        # Normalize path after validation
        self.path = skpath.normalize_path(path)
        
        # Double-check normalized path exists
        if not os.path.exists(self.path):
            raise SKGlobalError(f"Normalized storage path does not exist: {self.path}")
        
        # Auto-detect level based on path
        project_root = get_project_root()
        if self.path == project_root:
            self.level = GlobalLevel.TOP
            self._top_storage = None  # This IS the top storage
        else:
            self.level = GlobalLevel.UNDER
            # Get reference to THE top storage (singleton)
            self._top_storage = SKGlobalStorage.get_storage(project_root, auto_sync)
        
        self.auto_sync = auto_sync
        self._current_process_id = str(os.getpid())
        
        # Initialize two-tier storage system
        if auto_sync:
            try:
                # Tier 1: Direct storage (local + cross-process data for THIS directory)
                self._storage = self._cereal.create_shared_dict()
                self._storage['local_data'] = self._cereal.create_shared_dict()
                self._storage['cross_process_data'] = self._cereal.create_shared_dict()
                
                # Tier 2: Cross-storage data (from OTHER directories via TOP)
                self._cross_process_storage = self._cereal.create_shared_dict()
                
                self._multiprocessing_available = hasattr(self._storage, '_manager')
                if not self._multiprocessing_available:
                    print(f"Warning: Multiprocessing not available for storage at {self.path}")
            except Exception as e:
                print(f"Warning: Failed to create shared storage: {e}")
                self._storage = {
                    'local_data': {},
                    'cross_process_data': {}
                }
                self._cross_process_storage = {}
                self._multiprocessing_available = False
        else:
            self._storage = {
                'local_data': {},
                'cross_process_data': {}
            }
            self._cross_process_storage = {}
            self._multiprocessing_available = False

        self._lock = threading.RLock()
        
        # Create storage file path
        self.storage_file = self._create_storage_file_path()
        
        # Load existing data from storage file
        self._load_from_file()
    
    @classmethod   
    def _ensure_clean_startup(cls):
        """Ensure clean startup by resetting old status flags."""
        if not cls._startup_cleaned:
            try:
                cls._reset_all_loaded_statuses()
                cls._startup_cleaned = True
            except Exception as e:
                print(f"Warning: Failed to clean startup state: {e}")
                cls._startup_cleaned = False

    @classmethod
    def _reset_all_loaded_statuses(cls):
        """Reset all loaded statuses in existing storage files"""    
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

    def set_local(self, name: str, data: Dict[str, Any]) -> None:
        """Set local data in this storage and sync up to TOP if needed."""
        with self._lock:
            try:
                # Add metadata
                enhanced_data = {
                    **data,
                    '_stored_by_process': self._current_process_id,
                    '_stored_at': sktime.now(),
                    '_storage_path': self.path
                }
                
                self._storage['local_data'][name] = enhanced_data
                
                # If UNDER storage, sync up to TOP storage
                if self.level == GlobalLevel.UNDER and self._top_storage:
                    with self._top_storage._lock:
                        path_key = f"{self.path}::{name}"
                        self._top_storage._storage['local_data'][path_key] = enhanced_data
                        self._top_storage._save_to_file()
                
                self._save_to_file()
            except Exception as e:
                print(f"Warning: Failed to set local data: {e}")
                self._save_to_file()

    def get_local(self, name: str) -> Optional[Dict[str, Any]]:
        """Get local data from this storage."""
        with self._lock:
            try:
                if name in self._storage['local_data']:
                    return dict(self._storage['local_data'][name])
            except Exception as e:
                print(f"Warning: Failed to get local data: {e}")
        return None

    def set_cross_process(self, name: str, data: Dict[str, Any], from_process_id: str) -> None:
        """Store cross-process data (same variable, different process)."""
        with self._lock:
            try:
                if from_process_id not in self._storage['cross_process_data']:
                    if self.auto_sync and self._multiprocessing_available:
                        self._storage['cross_process_data'][from_process_id] = self._cereal.create_shared_dict()
                    else:
                        self._storage['cross_process_data'][from_process_id] = {}
                
                enhanced_data = {
                    **data,
                    '_received_from_process': from_process_id,
                    '_received_at': sktime.now()
                }
                
                self._storage['cross_process_data'][from_process_id][name] = enhanced_data
                self._save_to_file()
            except Exception as e:
                print(f"Warning: Failed to set cross-process data: {e}")

    def get_cross_process(self, name: str, from_process_id: str = None) -> Optional[Dict[str, Any]]:
        """Get cross-process data for same variable from other processes."""
        with self._lock:
            try:
                if from_process_id:
                    if (from_process_id in self._storage['cross_process_data'] and
                        name in self._storage['cross_process_data'][from_process_id]):
                        return dict(self._storage['cross_process_data'][from_process_id][name])
                else:
                    # Return from any process (first found)
                    for process_id, process_data in self._storage['cross_process_data'].items():
                        if name in process_data:
                            return dict(process_data[name])
            except Exception as e:
                print(f"Warning: Failed to get cross-process data: {e}")
        return None

    def receive_from_other_storage(self, source_path: str, name: str, data: Dict[str, Any]) -> None:
        """Receive data from another storage via TOP."""
        with self._lock:
            try:
                if source_path not in self._cross_process_storage:
                    if self.auto_sync and self._multiprocessing_available:
                        self._cross_process_storage[source_path] = self._cereal.create_shared_dict()
                    else:
                        self._cross_process_storage[source_path] = {}
                
                enhanced_data = {
                    **data,
                    '_received_from_storage': source_path,
                    '_received_at': sktime.now()
                }
                
                self._cross_process_storage[source_path][name] = enhanced_data
                self._save_to_file()
            except Exception as e:
                print(f"Warning: Failed to receive data from other storage: {e}")

    def get_from_other_storage(self, source_path: str, name: str) -> Optional[Dict[str, Any]]:
        """Get data from another storage."""
        with self._lock:
            try:
                if (source_path in self._cross_process_storage and
                    name in self._cross_process_storage[source_path]):
                    return dict(self._cross_process_storage[source_path][name])
            except Exception as e:
                print(f"Warning: Failed to get data from other storage: {e}")
        return None

    def sync_from_top(self, source_path: str = None) -> Dict[str, int]:
        """
        Pull data from other storages via TOP storage.
        
        Args:
            source_path: Specific path to sync from (None = sync from all paths)
            
        Returns:
            Dict mapping source paths to count of variables synced
        """
        if self.level != GlobalLevel.UNDER or not self._top_storage:
            return {}
        
        synced_count = {}
        
        with self._top_storage._lock:
            for key, value in self._top_storage._storage['local_data'].items():
                if "::" in key:  # Data from other UNDER storages
                    key_source_path, var_name = key.split("::", 1)
                    
                    # Skip our own data
                    if key_source_path == self.path:
                        continue
                    
                    # Filter by source if specified
                    if source_path and key_source_path != source_path:
                        continue
                    
                    # Store in cross-process storage
                    self.receive_from_other_storage(key_source_path, var_name, dict(value))
                    synced_count[key_source_path] = synced_count.get(key_source_path, 0) + 1
        
        return synced_count

    def remove_variable(self, name: str, synchronized: bool = False) -> None:
        """
        Remove a variable from all storage tiers.
        
        Args:
            name: Variable name to remove
            synchronized: If True, this is a synchronized removal (don't cancel schedule)
        """
        with self._lock:
            try:
                # Remove from local data
                if name in self._storage['local_data']:
                    del self._storage['local_data'][name]
                
                # Remove from cross-process data
                for process_data in self._storage['cross_process_data'].values():
                    if name in process_data:
                        del process_data[name]
                
                # Remove from cross-storage data
                for storage_data in self._cross_process_storage.values():
                    if name in storage_data:
                        del storage_data[name]
                
                # If UNDER storage, also remove from TOP storage
                if self.level == GlobalLevel.UNDER and self._top_storage:
                    with self._top_storage._lock:
                        path_key = f"{self.path}::{name}"
                        if path_key in self._top_storage._storage['local_data']:
                            del self._top_storage._storage['local_data'][path_key]
                        self._top_storage._save_to_file()
                
                self._save_to_file()
                
                # Cancel scheduled removal if not synchronized
                if not synchronized:
                    removal_manager = RemovalManager()
                    removal_manager.cancel_removal(name, self.path)
                    
            except Exception as e:
                print(f"Warning: Failed to remove variable: {e}")

    def list_all_data(self) -> Dict[str, Any]:
        """List all data available in this storage."""
        result = {
            'local_data': [],
            'cross_process_data': {},
            'cross_storage_data': {},
            'path': self.path,
            'level': self.level.name
        }
        
        with self._lock:
            try:
                # Local data
                result['local_data'] = list(self._storage['local_data'].keys())
                
                # Cross-process data
                for process_id, process_data in self._storage['cross_process_data'].items():
                    result['cross_process_data'][process_id] = list(process_data.keys())
                
                # Cross-storage data
                for source_path, storage_data in self._cross_process_storage.items():
                    result['cross_storage_data'][source_path] = list(storage_data.keys())
                    
            except Exception as e:
                print(f"Warning: Failed to list data: {e}")
        
        return result

    def get_storage_info(self) -> Dict[str, Any]:
        """Get comprehensive information about this storage instance."""
        return {
            'path': self.path,
            'level': self.level,
            'auto_sync': self.auto_sync,
            'multiprocessing_available': self._multiprocessing_available,
            'storage_file': self.storage_file,
            'current_process_id': self._current_process_id,
            'data_summary': self.list_all_data()
        }

    def is_multiprocessing_enabled(self) -> bool:
        """Check if this storage instance has multiprocessing enabled."""
        return self.auto_sync and self._multiprocessing_available

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
                
                # Load storage data
                if 'storage' in data:
                    storage_data = data['storage']
                    if 'local_data' in storage_data:
                        for name, var_data in storage_data['local_data'].items():
                            try:
                                self._storage['local_data'][name] = var_data
                            except Exception as e:
                                print(f"Warning: Failed to load local variable {name}: {e}")
                    
                    if 'cross_process_data' in storage_data:
                        for process_id, process_data in storage_data['cross_process_data'].items():
                            try:
                                if self.auto_sync and self._multiprocessing_available:
                                    self._storage['cross_process_data'][process_id] = self._cereal.create_shared_dict()
                                else:
                                    self._storage['cross_process_data'][process_id] = {}
                                
                                for name, var_data in process_data.items():
                                    self._storage['cross_process_data'][process_id][name] = var_data
                            except Exception as e:
                                print(f"Warning: Failed to load cross-process data for {process_id}: {e}")
                
                # Load cross-storage data
                if 'cross_process_storage' in data:
                    for source_path, source_data in data['cross_process_storage'].items():
                        try:
                            if self.auto_sync and self._multiprocessing_available:
                                self._cross_process_storage[source_path] = self._cereal.create_shared_dict()
                            else:
                                self._cross_process_storage[source_path] = {}
                            
                            for name, var_data in source_data.items():
                                self._cross_process_storage[source_path][name] = var_data
                        except Exception as e:
                            print(f"Warning: Failed to load cross-storage data from {source_path}: {e}")
                
                return True
        except (json.JSONDecodeError, OSError, KeyError) as e:
            print(f"Warning: Could not load storage file {self.storage_file}: {e}")
        
        return False

    def _save_to_file(self) -> None:
        """Save current variables to JSON file."""
        try:
            with self._lock:
                # Convert storage data to serializable format
                storage_data = {}
                cross_storage_data = {}
                
                try:
                    # Convert storage to dict
                    storage_data = {
                        'local_data': dict(self._storage['local_data']) if self._storage['local_data'] else {},
                        'cross_process_data': {}
                    }
                    
                    # Convert cross-process data
                    for process_id, process_data in self._storage['cross_process_data'].items():
                        storage_data['cross_process_data'][process_id] = dict(process_data) if process_data else {}
                    
                    # Convert cross-storage data
                    for source_path, source_data in self._cross_process_storage.items():
                        cross_storage_data[source_path] = dict(source_data) if source_data else {}
                        
                except Exception as e:
                    print(f"Warning: Could not convert storage to dict: {e}")
                    storage_data = {'local_data': {}, 'cross_process_data': {}}
                    cross_storage_data = {}
                
                data = {
                    "path": self.path,
                    "level": self.level.name,
                    "auto_sync": self.auto_sync,
                    "multiprocessing_available": self._multiprocessing_available,
                    "current_process_id": self._current_process_id,
                    "created_at": sktime.now(),
                    "last_saved": sktime.now(),
                    "storage": storage_data,
                    "cross_process_storage": cross_storage_data
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
        with self._lock:
            try:
                # Get our local variables
                keys_to_sync = list(self._storage['local_data'].keys())
                if key_filter:
                    keys_to_sync = [k for k in keys_to_sync if key_filter(k)]
                
                # Copy data from this storage to other storage
                for key in keys_to_sync:
                    data = self.get_local(key)
                    if data:
                        other_storage.receive_from_other_storage(self.path, key, data)
            except Exception as e:
                print(f"Warning: Sync operation failed: {e}")

    def has_variable(self, name: str) -> bool:
        """Check if a variable with the given name exists."""
        return (self.get_local(name) is not None or 
                self.get_cross_process(name) is not None)
        
    def contains(self, item) -> bool:
        """Check if a variable exists in storage."""
        return self.__contains__(item)

    def __contains__(self, item) -> bool:
        """Check if a variable exists in storage using 'in' operator."""
        if isinstance(item, SKGlobal):
            return self.has_variable(item.name)
        elif isinstance(item, str):
            return self.has_variable(item)
        else:
            return False
    
    def __repr__(self) -> str:
        """String representation of the storage."""
        multiprocessing_status = "enabled" if self._multiprocessing_available else "disabled"
        return (f"SKGlobalStorage(path='{self.path}', level={self.level.name}, "
                f"auto_sync={self.auto_sync}, multiprocessing={multiprocessing_status})")


# Module cleanup
def _cleanup_on_exit():
    """Clean up resources on module exit."""
    try:
        removal_manager = RemovalManager()
        removal_manager.shutdown()
    except Exception:
        pass

atexit.register(_cleanup_on_exit)


if __name__ == "__main__":
    import tempfile
    import shutil
    
    def run_tests():
        """Run basic functionality tests."""
        print("🧪 Starting SKGlobal Hierarchical Storage Tests...")
        print("=" * 60)
        
        # Test counters
        passed = 0
        total = 0
        
        def test(name: str, test_func):
            nonlocal passed, total
            total += 1
            try:
                print(f"\n🔍 Testing: {name}")
                test_func()
                print(f"   ✅ PASSED: {name}")
                passed += 1
            except Exception as e:
                print(f"   ❌ FAILED: {name}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Test project root detection
        def test_project_root():
            root = get_project_root()
            assert os.path.exists(root), f"Project root doesn't exist: {root}"
            print(f"   Project root: {root}")
        
        test("Project Root Detection", test_project_root)
        
        # Test basic storage creation
        def test_storage_creation():
            storage = SKGlobalStorage.get_storage(get_project_root(), auto_sync=True)
            assert storage.level == GlobalLevel.TOP
            print(f"   Storage info: {storage.get_storage_info()}")
        
        test("Storage Creation", test_storage_creation)
        
        # Test basic global creation
        def test_basic_global():
            global_var = SKGlobal(
                name="test_basic",
                value="Hello Hierarchical World",
                auto_create=True
            )
            assert global_var.get() == "Hello Hierarchical World"
            global_var.remove()
        
        test("Basic Global Variable", test_basic_global)
        
        # Test hierarchical storage
        def test_hierarchical_storage():
            # Create TOP storage
            top_storage = SKGlobalStorage.get_storage(get_project_root(), auto_sync=True)
            
            # Create test data
            test_data = {
                'name': 'hierarchical_test',
                'value': 'hierarchical_value',
                'created_at': sktime.now()
            }
            
            top_storage.set_local("hierarchical_test", test_data)
            retrieved = top_storage.get_local("hierarchical_test")
            assert retrieved is not None
            assert retrieved['value'] == 'hierarchical_value'
            
            # Clean up
            top_storage.remove_variable("hierarchical_test")
        
        test("Hierarchical Storage", test_hierarchical_storage)
        
        # Test removal manager
        def test_removal_manager():
            removal_manager = RemovalManager()
            
            # Create a global with timed removal
            global_var = SKGlobal(
                name="test_removal",
                value="will_be_removed",
                remove_in=0.1,
                auto_create=True
            )
            
            # Check it exists
            assert global_var.get() == "will_be_removed"
            
            # Check scheduled removals
            scheduled = removal_manager.get_scheduled_removals()
            assert len(scheduled) >= 1
            
            # Manual cleanup
            global_var.remove()
        
        test("Removal Manager", test_removal_manager)
        
        # Print results
        print("\n" + "=" * 60)
        print(f"🏁 Test Results: {passed}/{total} passed")
        if passed == total:
            print("🎉 All basic tests passed!")
        else:
            print(f"⚠️  {total - passed} tests failed")
        print("=" * 60)
    
    # Run the tests
    run_tests()