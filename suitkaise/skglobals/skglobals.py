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
from typing import Optional, Any, Dict, List, Tuple, Callable
from pathlib import Path
from enum import IntEnum
import json
import threading
import atexit
import fcntl
import contextlib
import shutil
import weakref
import hashlib
from dataclasses import dataclass, field
from collections import defaultdict


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

class SKGlobalStorageError(SKGlobalError):
    """Custom exception for SKGlobalStorage errors."""
    pass

class SKGlobalSyncError(SKGlobalError):
    """Custom exception for SKGlobal synchronization errors."""
    pass

class SKGlobalTransactionError(SKGlobalError):
    """Custom exception for SKGlobal transaction errors."""
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

@dataclass
class StorageStats:
    """Statistics for storage usage."""
    reads: int = 0
    writes: int = 0
    errors: int = 0
    last_accessed: float = field(default_factory=sktime.now)
    cache_hits: int = 0
    cache_misses: int = 0

    def record_read(self):
        self.reads += 1
        self.last_accessed = sktime.now()

    def record_write(self):
        self.writes += 1
        self.last_accessed = sktime.now()

    def record_error(self):
        self.errors += 1
        self.last_accessed = sktime.now()
    
    def record_cache_hit(self):
        self.cache_hits += 1
    
    def record_cache_miss(self):
        self.cache_misses += 1    

@contextlib.contextmanager
def file_lock(filepath: str, timeout: float = 5.0):
    """Context manager for cross process file locking."""
    lock_file = f"{filepath}.lock"
    lock_fd = None

    try:
        # Ensure the lock file directory exists
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)

        start_time = sktime.now()
        while sktime.now() - start_time < timeout:
            try:
                # Try to acquire the lock
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                yield lock_fd
                return
            except (IOError, BlockingIOError, OSError):
                # If we can't acquire the lock, wait briefly and retry
                sktime.sleep(0.1)

        raise SKGlobalError(f"Timeout while trying to acquire lock on {lock_file}")
    
    finally:
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)  # Release the lock
                os.close(lock_fd)
            except:
                # If we can't release the lock, just ignore it
                pass

        # cleanup lock file
        try:
            os.unlink(lock_file)
        except:
            pass

class StorageTransaction:
    """Wrapper for storage operations with rollback support."""

    def __init__(self, storage: 'SKGlobalStorage', name: str, data: dict):
        self.storage = storage
        self.name = name
        self.data = data
        self.rollback_data = {}
        self.completed = False
        self.transaction_id = hashlib.md5(f"{storage.path}:{name}:{sktime.now()}".encode()).hexdigest()[:8]

    def execute(self):
        """Execute transaction and rollback if it fails."""
        if self.completed:
            raise SKGlobalTransactionError("Transaction already completed.")
        
        try:
            # prepare the rollback data
            self._prepare_rollback()

            # execute operations
            self._execute_local()
            if self.storage.level == GlobalLevel.UNDER:
                self._execute_top_sync()

            # persist changes and mark as completed
            self._persist_changes()

            self.completed = True

        except Exception as e:
            print(f"Warning: Transaction {self.transaction_id} failed, rolling back: {e}")
            self._rollback()
            raise SKGlobalTransactionError(f"Storage transaction failed: {e}") from e
        
    def _prepare_rollback(self):
        """Prepare data for potential rollback."""
        # Add null safety checks
        if (self.storage._storage is not None and 
            'local_data' in self.storage._storage and
            self.name in self.storage._storage['local_data']):
            self.rollback_data['local'] = dict(self.storage._storage['local_data'][self.name])

        if (self.storage._top_storage and 
            self.storage._top_storage._storage is not None and
            'local_data' in self.storage._top_storage._storage):
            path_key = f"{self.storage.path}::{self.name}"
            if path_key in self.storage._top_storage._storage['local_data']:
                self.rollback_data['top'] = dict(self.storage._top_storage._storage['local_data'][path_key])

    def _execute_local(self):
        """Execute local storage operations."""
        if self.storage._storage is None:
            raise SKGlobalTransactionError("Storage is not initialized.")
        self.storage._storage['local_data'][self.name] = self.data
        

    def _execute_top_sync(self):
        """Execute synchronization with top-level storage."""
        """Execute TOP storage sync."""
        if self.storage._top_storage:
            path_key = f"{self.storage.path}::{self.name}"
            with self.storage._top_storage._lock:
                self.storage._top_storage._storage['local_data'][path_key] = self.data

    def _persist_changes(self):
        """Persist all changes to disk."""
        # Save TOP first (most critical)
        if self.storage._top_storage:
            self.storage._top_storage._save_to_file()
        
        # Then save local
        self.storage._save_to_file()

    def _rollback(self):
        """Rollback changes on failure."""
        try:
            if 'local' in self.rollback_data:
                self.storage._storage['local_data'][self.name] = self.rollback_data['local']
            elif self.name in self.storage._storage['local_data']:
                self.storage._storage['local_data'].pop(self.name, None)

            if 'top' in self.rollback_data and self.storage._top_storage:
                path_key = f"{self.storage.path}::{self.name}"
                with self.storage._top_storage._lock:
                    self.storage._top_storage._storage['local_data'][path_key] = self.rollback_data['top']

        except Exception as e:
            print(f"Critical: Rollback failed for transaction {self.transaction_id}: {e}")

class SimpleCache:
    """Simple, LRU style cache for storage data."""

    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_order: List[str] = []
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get an item from the cache."""
        with self._lock:
            if key in self.cache:
                # Move to end to mark as most recently used
                self.access_order.remove(key)
                self.access_order.append(key)
                return self.cache[key]
            return None
        
    def put(self, key: str, value: Any):
        """Put item in cache."""
        with self._lock:
            if key in self.cache:
                # Update existing
                self.cache[key] = value
                self.access_order.remove(key)
                self.access_order.append(key)
            else:
                # Add new
                if len(self.cache) >= self.max_size:
                    # Remove least recently used
                    lru_key = self.access_order.pop(0)
                    del self.cache[lru_key]
                
                self.cache[key] = value
                self.access_order.append(key)

    def clear(self):
        """Clear cache."""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self.cache)
        
class ResourceManager:
    """Centralized resource management for SKGlobals."""

    def __init__(self):
        self._active_storages = weakref.WeakValueDictionary()
        self._removal_manager: Optional['RemovalManager'] = None
        self._cleanup_registered = False
        self._lock = threading.RLock()
        self._stats = defaultdict(StorageStats)

    def register_storage(self, storage: 'SKGlobalStorage'):
        """Register a storage instance."""
        with self._lock:
            key = f"{storage.path}_{storage.auto_sync}"
            self._active_storages[key] = storage

            if not self._cleanup_registered:
                atexit.register(self.cleanup_all)
                self._cleanup_registered = True

    def get_stats(self) -> Dict[str, StorageStats]:
        """Get resource usage statistics."""
        with self._lock:
            return dict(self._stats)
        
    def record_operation(self, storage_path: str, operation: str):
        """Record a storage operation for stats."""
        with self._lock:
            stats = self._stats[storage_path]
            if operation == 'read':
                stats.record_read()
            elif operation == 'write':
                stats.record_write()
            elif operation == 'error':
                stats.record_error()
            elif operation == 'cache_hit':
                stats.record_cache_hit()
            elif operation == 'cache_miss':
                stats.record_cache_miss()

    def cleanup_all(self):
        """Clean up all resources."""
        print("Info: Starting resource cleanup...")
        
        # Instead of full cleanup, just save data and clear caches
        with self._lock:
            storages_to_cleanup = list(self._active_storages.values())
        
        for storage in storages_to_cleanup:
            try:
                # Save data but don't destroy storage structure
                storage._save_to_file()
                storage._cache.clear()
            except Exception as e:
                print(f"Warning: Storage save failed: {e}")
        
        # Cleanup removal manager
        if self._removal_manager:
            try:
                self._removal_manager.shutdown()
            except Exception as e:
                print(f"Warning: RemovalManager shutdown failed: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all managed resources."""
        health_report = {
            'status': 'healthy',
            'active_storages': 0,
            'total_operations': 0,
            'total_errors': 0,
            'issues': []
        }
        
        try:
            with self._lock:
                health_report['active_storages'] = len(self._active_storages)
                
                for path, stats in self._stats.items():
                    health_report['total_operations'] += stats.reads + stats.writes
                    health_report['total_errors'] += stats.errors
                    
                    # Check for concerning error rates
                    total_ops = stats.reads + stats.writes
                    if total_ops > 0 and stats.errors / total_ops > 0.1:  # >10% error rate
                        health_report['issues'].append(f"High error rate for {path}: {stats.errors}/{total_ops}")
                        health_report['status'] = 'degraded'
                
                # Check removal manager
                if self._removal_manager:
                    scheduled = self._removal_manager.get_scheduled_removals()
                    if len(scheduled) > 100:  # Too many pending removals
                        health_report['issues'].append(f"Too many pending removals: {len(scheduled)}")
                        health_report['status'] = 'degraded'
        
        except Exception as e:
            health_report['status'] = 'unhealthy'
            health_report['issues'].append(f"Health check failed: {e}")
        
        return health_report

# Global resource manager instance
_resource_manager = ResourceManager()


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
    
    # Variables to track potential roots
    potential_roots = []
    
    # Walk up the directory tree
    max_depth = 20  # Prevent infinite loops
    depth = 0
    
    while depth < max_depth:
        # Stop if we've reached an OS-level directory
        if os.path.basename(current) in common_ospaths or current in common_ospaths:
            break
            
        score = 0
        required_files_found = False
        found_indicators = []

        # Check files in current directory
        files = file_children(current)
        for filename in files:
            # Check necessary files
            for pattern_set in indicators['common_proj_root_files']['necessary']:
                if matches_pattern(filename, pattern_set):
                    required_files_found = True
                    found_indicators.append(f"necessary:{filename}")
                    break
            
            # Check indicator files
            for pattern_set in indicators['common_proj_root_files']['indicators']:
                if matches_pattern(filename, pattern_set):
                    score += 3
                    found_indicators.append(f"indicator:{filename}")
                    
            # Check weak indicator files  
            for pattern_set in indicators['common_proj_root_files']['weak_indicators']:
                if matches_pattern(filename, pattern_set):
                    score += 1
                    found_indicators.append(f"weak:{filename}")

        # Check directories in current directory
        dirs = dir_children(current)
        for dirname in dirs:
            # Check strong indicator directories
            for pattern_set in indicators['common_proj_root_dirs']['strong_indicators']:
                if matches_pattern(dirname, pattern_set):
                    score += 10
                    found_indicators.append(f"strong_dir:{dirname}")
                    
            # Check indicator directories
            for pattern_set in indicators['common_proj_root_dirs']['indicators']:
                if matches_pattern(dirname, pattern_set):
                    score += 3
                    found_indicators.append(f"indicator_dir:{dirname}")

        # If we found required files and sufficient score, this could be the root
        if required_files_found and score >= 15:
            # Check for strong main project indicators
            strong_main_indicators = ['setup.py', 'pyproject.toml', 'setup.cfg', 'Cargo.toml', 'package.json']
            has_strong_file_indicator = any(filename in strong_main_indicators for filename in files)
            has_git_dir = '.git' in dirs
            
            # Calculate priority score for this potential root
            priority_score = score
            if has_strong_file_indicator:
                priority_score += 50  # Big bonus for main project files
            if has_git_dir:
                priority_score += 30  # Big bonus for git repository
            
            # Store this as a potential root
            potential_roots.append({
                'path': current,
                'score': score,
                'priority_score': priority_score,
                'depth': depth,
                'has_strong_indicators': has_strong_file_indicator or has_git_dir,
                'indicators': found_indicators
            })
            
            # If this has very strong indicators, prefer it immediately
            if has_strong_file_indicator or has_git_dir:
                return current

        # Move up one directory
        parent = os.path.dirname(current)
        if parent == current:  # Reached filesystem root
            break
        current = parent
        depth += 1

    # If we found potential roots, pick the best one
    if potential_roots:
        # Sort by priority score (highest first), then by depth (closer to start)
        potential_roots.sort(key=lambda x: (-x['priority_score'], x['depth']))
        best_root = potential_roots[0]
        return best_root['path']

    # If no potential roots found, raise error
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
        self._shutdown_complete = threading.Event()
        self._initialized = True
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        # Register with resource manager
        _resource_manager._removal_manager = self
    
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
                
                # Process removals
                for schedule in removals_to_process:
                    try:
                        self._execute_removal(schedule)
                    except Exception as e:
                        print(f"Error: Failed to execute scheduled removal for {schedule.variable_name}: {e}")
                
                # Sleep briefly before next check
                self._shutdown_event.wait(0.1)
                
            except Exception as e:
                print(f"Error: RemovalManager cleanup worker error: {e}")
                self._shutdown_event.wait(1.0)
    
    def _execute_removal(self, schedule: RemovalSchedule):
        """Execute a scheduled removal across all storages."""
        try:
            # Get the storage and remove the variable
            storage = SKGlobalStorage.get_storage(schedule.storage_path, auto_sync=True)
            if storage:
                storage.remove_variable(schedule.variable_name, synchronized=True)
        except Exception as e:
            print(f"Error: Failed to execute scheduled removal for {schedule.variable_name}: {e}")
    
    def schedule_removal(self, variable_name: str, storage_path: str, remove_in_seconds: float):
        """Schedule a variable for removal."""
        if remove_in_seconds <= 0:
            raise SKGlobalValueError("remove_in_seconds must be positive")
            
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
    
    def shutdown(self, timeout: float = 5.0):
        """Proper shutdown with timeout."""
        if self._shutdown_event.is_set():
            return  # Already shutting down
        
        print("Info: Shutting down RemovalManager...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for cleanup thread to finish
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=timeout)
            
            if self._cleanup_thread.is_alive():
                print("Warning: RemovalManager cleanup thread did not shut down cleanly")
        
        # Process any remaining removals immediately
        self._process_remaining_removals()
        
        self._shutdown_complete.set()
        print("Info: RemovalManager shutdown complete")

    def _process_remaining_removals(self):
        """Process any remaining scheduled removals immediately."""
        try:
            with self._lock:
                rem = list(self._scheduled_removals.values())
                self._scheduled_removals.clear()

            for schedule in rem:
                try:
                    self._execute_removal(schedule)
                except Exception as e:
                    print(f"Error: Failed to execute remaining scheduled removal for {schedule.variable_name}: {e}")

        except Exception as e:
            print(f"Error: Failed to process remaining removals: {e}")
                    

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
        try:
            self.storage = SKGlobalStorage.get_storage(self.path, self.auto_sync)
        except Exception as e:
            print(f"Error: Failed to get storage for path '{self.path}': {e}")
            raise SKGlobalError(f"Failed to initialize storage: {e}") from e

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

        try:
            self.storage.set_local(self.name, vardata)

            # Schedule removal if specified
            if self.remove_in:
                removal_manager = RemovalManager()
                removal_manager.schedule_removal(self.name, self.path, self.remove_in)
        except Exception as e:
            print(f"Error: Failed to create global variable '{self.name}': {e}")
            raise SKGlobalError(f"Failed to create global variable: {e}") from e


    def get(self) -> Any:
        """Get the value of the global variable."""
        try:
            data = self.storage.get_local(self.name)
            if data is None:
                # Check cross-process data
                data = self.storage.get_cross_process(self.name)
            return data['value'] if data else None
        except Exception as e:
            print(f"Error: Failed to get global variable '{self.name}': {e}")
            return None
    
    def set(self, value: Any) -> None:
        """Set the value of the global variable."""
        try:
            self.value = value
            data = self.storage.get_local(self.name)
            if data:
                data['value'] = value
                data['last_updated'] = sktime.now()
                self.storage.set_local(self.name, data)
            else:
                # If data doesn't exist, create it
                self._create_global_variable()
        except Exception as e:
            print(f"Error: Failed to set global variable '{self.name}': {e}")
            raise SKGlobalError(f"Failed to set global variable: {e}") from e

    def remove(self) -> None:
        """Remove the global variable from storage."""
        try:
            # Cancel scheduled removal
            if self.remove_in:
                removal_manager = RemovalManager()
                removal_manager.cancel_removal(self.name, self.path)
            
            self.storage.remove_variable(self.name)
        except Exception as e:
            print(f"Error: Failed to remove global variable '{self.name}': {e}")
            raise SKGlobalError(f"Failed to remove global variable: {e}") from e

    @classmethod
    def get_global(cls, name: str, path: Optional[str] = None, 
                level: GlobalLevel = GlobalLevel.TOP,
                auto_sync: Optional[bool] = None) -> Optional['SKGlobal']:
        """Get an existing global variable by name."""
        try:
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
        except Exception as e:
            print(f"Error: Failed to get global variable '{name}': {e}")
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
        try:
            path = skpath.normalize_path(path, strict=True)
        except skpath.AutopathError as e:
            raise SKGlobalError(f"Invalid storage path: {path}") from e
        
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
            raise SKGlobalStorageError(f"Storage path does not exist: {path}")
        
        # Normalize path after validation
        try:
            self.path = skpath.normalize_path(path, strict=True)
        except Exception as e:
            raise SKGlobalStorageError(f"Failed to normalize path '{path}': {e}") from e
        
        # Auto-detect level based on path
        try:
            project_root = get_project_root()
            if self.path == project_root:
                self.level = GlobalLevel.TOP
                self._top_storage = None  # This IS the top storage
            else:
                self.level = GlobalLevel.UNDER
                # Get reference to THE top storage (singleton)
                self._top_storage = SKGlobalStorage.get_storage(project_root, auto_sync)
        except Exception as e:
            print(f"Error: Failed to determine storage level for path '{path}': {e}")
            # Default to UNDER level if we can't determine
            self.level = GlobalLevel.UNDER
            self._top_storage = None
        
        self.auto_sync = auto_sync
        self._current_process_id = str(os.getpid())
        self._resources_to_cleanup = []
        
        # Performance features
        self._cache = SimpleCache(max_size=100)
        self._stats = StorageStats()
        
        # Initialize two-tier storage system
        if auto_sync:
            try:
                self._storage = self._cereal.create_shared_dict()
                self._storage['local_data'] = self._cereal.create_shared_dict()
                self._storage['cross_process_data'] = self._cereal.create_shared_dict()
                
                self._cross_process_storage = self._cereal.create_shared_dict()
                
                self._multiprocessing_available = hasattr(self._storage, '_manager')
                if not self._multiprocessing_available:
                    print(f"Warning: Multiprocessing not available for storage at {self.path}")
            except Exception as e:
                print(f"Error: Failed to create shared storage for '{self.path}': {e}")
                # CRITICAL: Ensure _storage is never None
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
        try:
            self.storage_file = self._create_storage_file_path()
        except Exception as e:
            print(f"Error: Failed to create storage file path: {e}")
            # Create a fallback storage file path
            self.storage_file = os.path.join(os.path.dirname(self.path), f"fallback_storage_{os.getpid()}.sk")
        
        # Load existing data from storage file
        try:
            self._load_from_file()
        except Exception as e:
            print(f"Error: Failed to load storage from file '{self.storage_file}': {e}")
            # Continue with empty storage rather than failing
        
        # Register for cleanup
        _resource_manager.register_storage(self)

        if self._storage is None:
            raise SKGlobalStorageError(f"Storage initialization failed for path: {self.path}")

    def _validate_storage_data(self, data: dict) -> bool:
        """Validate storage data integrity."""
        required_fields = ['path', 'level', 'storage']
        
        for field in required_fields:
            if field not in data:
                print(f"Error: Storage validation failed: Missing required field: {field}")
                return False
        
        if data['path'] != self.path:
            print(f"Error: Storage validation failed: Path mismatch: expected {self.path}, got {data['path']}")
            return False
        
        return True
    
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
        if not name or not isinstance(data, dict):
            raise SKGlobalValueError("Invalid name or data for set_local")
            
        with self._lock:
            try:
                # Add metadata
                enhanced_data = {
                    **data,
                    '_stored_by_process': self._current_process_id,
                    '_stored_at': sktime.now(),
                    '_storage_path': self.path
                }
                
                # Use transaction for atomicity
                transaction = StorageTransaction(self, name, enhanced_data)
                transaction.execute()
                
                # Update cache
                self._cache.put(name, enhanced_data)
                
                # Record statistics
                self._stats.record_write()
                _resource_manager.record_operation(self.path, 'write')
                
            except SKGlobalStorageError:
                # Re-raise storage errors
                self._stats.record_error()
                _resource_manager.record_operation(self.path, 'error')
                raise
            except Exception as e:
                print(f"Error: Failed to set local data for '{name}': {e}")
                self._stats.record_error()
                _resource_manager.record_operation(self.path, 'error')
                raise SKGlobalStorageError(f"Failed to set local data: {e}") from e
            

    def get_local(self, name: str) -> Optional[Dict[str, Any]]:
        """Get local data from this storage."""
        with self._lock:
            try:
                # Check cache first
                cached_data = self._cache.get(name)
                if cached_data is not None:
                    self._stats.record_cache_hit()
                    _resource_manager.record_operation(self.path, 'cache_hit')
                    self._stats.record_read()
                    _resource_manager.record_operation(self.path, 'read')
                    return dict(cached_data)
                
                # Cache miss - check storage
                self._stats.record_cache_miss()
                _resource_manager.record_operation(self.path, 'cache_miss')
                
                if name in self._storage['local_data']:
                    data = dict(self._storage['local_data'][name])
                    # Update cache
                    self._cache.put(name, data)
                    self._stats.record_read()
                    _resource_manager.record_operation(self.path, 'read')
                    return data
                    
            except Exception as e:
                print(f"Error: Failed to get local data for '{name}': {e}")
                self._stats.record_error()
                _resource_manager.record_operation(self.path, 'error')
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
                
                self._stats.record_write()
                _resource_manager.record_operation(self.path, 'write')
                
            except Exception as e:
                print(f"Error: Failed to set cross-process data for '{name}': {e}")
                self._stats.record_error()
                _resource_manager.record_operation(self.path, 'error')
                raise SKGlobalStorageError(f"Failed to set cross-process data: {e}") from e


    def get_cross_process(self, name: str, from_process_id: str = None) -> Optional[Dict[str, Any]]:
        """Get cross-process data for same variable from other processes."""
        with self._lock:
            try:
                if from_process_id:
                    if (from_process_id in self._storage['cross_process_data'] and
                        name in self._storage['cross_process_data'][from_process_id]):
                        self._stats.record_read()
                        _resource_manager.record_operation(self.path, 'read')
                        return dict(self._storage['cross_process_data'][from_process_id][name])
                else:
                    # Return from any process (first found)
                    for process_id, process_data in self._storage['cross_process_data'].items():
                        if name in process_data:
                            self._stats.record_read()
                            _resource_manager.record_operation(self.path, 'read')
                            return dict(process_data[name])
            except Exception as e:
                print(f"Error: Failed to get cross-process data for '{name}': {e}")
                self._stats.record_error()
                _resource_manager.record_operation(self.path, 'error')
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
                
                self._stats.record_write()
                _resource_manager.record_operation(self.path, 'write')
                
            except Exception as e:
                print(f"Error: Failed to receive data from other storage: {e}")
                self._stats.record_error()
                _resource_manager.record_operation(self.path, 'error')
                raise SKGlobalStorageError(f"Failed to receive data from other storage: {e}") from e


    def get_from_other_storage(self, source_path: str, name: str) -> Optional[Dict[str, Any]]:
        """Get data from another storage."""
        with self._lock:
            try:
                if (source_path in self._cross_process_storage and
                    name in self._cross_process_storage[source_path]):
                    self._stats.record_read()
                    _resource_manager.record_operation(self.path, 'read')
                    return dict(self._cross_process_storage[source_path][name])
            except Exception as e:
                print(f"Error: Failed to get data from other storage: {e}")
                self._stats.record_error()
                _resource_manager.record_operation(self.path, 'error')
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
        
        try:
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
        except Exception as e:
            print(f"Error: Failed to sync from top storage: {e}")
            raise SKGlobalSyncError(f"Sync from top failed: {e}") from e
        
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
                # Remove from cache
                self._cache.put(name, None)  # Invalidate cache entry
                
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
                    try:
                        with self._top_storage._lock:
                            path_key = f"{self.path}::{name}"
                            if path_key in self._top_storage._storage['local_data']:
                                del self._top_storage._storage['local_data'][path_key]
                            self._top_storage._save_to_file()
                    except Exception as e:
                        print(f"Error: Failed to remove from top storage: {e}")
                
                self._save_to_file()
                
                # Cancel scheduled removal if not synchronized
                if not synchronized:
                    try:
                        removal_manager = RemovalManager()
                        removal_manager.cancel_removal(name, self.path)
                    except Exception as e:
                        print(f"Error: Failed to cancel scheduled removal: {e}")
                
                self._stats.record_write()
                _resource_manager.record_operation(self.path, 'write')
                    
            except Exception as e:
                print(f"Error: Failed to remove variable '{name}': {e}")
                self._stats.record_error()
                _resource_manager.record_operation(self.path, 'error')
                raise SKGlobalStorageError(f"Failed to remove variable: {e}") from e
            

    def list_all_data(self) -> Dict[str, Any]:
        """List all data available in this storage."""
        result = {
            'local_data': [],
            'cross_process_data': {},
            'cross_storage_data': {},
            'path': self.path,
            'level': self.level.name,
            'statistics': {
                'reads': self._stats.reads,
                'writes': self._stats.writes,
                'errors': self._stats.errors,
                'cache_hits': self._stats.cache_hits,
                'cache_misses': self._stats.cache_misses,
                'cache_size': self._cache.size(),
                'last_access': self._stats.last_accessed
            }
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
                print(f"Error: Failed to list storage data: {e}")
        
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
            'data_summary': self.list_all_data(),
            'performance': {
                'cache_hit_rate': (self._stats.cache_hits / max(1, self._stats.cache_hits + self._stats.cache_misses)) * 100,
                'error_rate': (self._stats.errors / max(1, self._stats.reads + self._stats.writes)) * 100,
                'total_operations': self._stats.reads + self._stats.writes
            }
        }

    def is_multiprocessing_enabled(self) -> bool:
        """Check if this storage instance has multiprocessing enabled."""
        return self.auto_sync and self._multiprocessing_available

    def clear_cache(self):
        """Clear the storage cache."""
        self._cache.clear()

    def cleanup(self):
        """Clean up all resources associated with this storage."""
        try:
            # Save any pending data
            self._save_to_file()
            
            # Clear cache
            self._cache.clear()
            
            # Cleanup shared memory resources
            if hasattr(self._storage, '_manager'):
                try:
                    self._storage._manager.shutdown()
                except:
                    pass
            
            # Cleanup any file handles
            for resource in self._resources_to_cleanup:
                try:
                    if hasattr(resource, 'close'):
                        resource.close()
                except:
                    pass
            
            # DON'T set _storage to None - this breaks singleton reuse!
            # Only clear the data, not the structure
            if self._storage is not None:
                self._storage['local_data'].clear()
                self._storage['cross_process_data'].clear()
            
            if self._cross_process_storage is not None:
                self._cross_process_storage.clear()
            
        except Exception as e:
            print(f"Warning: Cleanup failed for storage {self.path}: {e}")
    
    def __del__(self):
        """Ensure cleanup on garbage collection."""
        try:
            self.cleanup()
        except:
            pass

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
        try:
            root = get_project_root()
            sk_dir = os.path.join(root, '.sk')
            os.makedirs(sk_dir, exist_ok=True)
            return sk_dir
        except Exception as e:
            print(f"Error: Failed to create .sk directory: {e}")
            # Fallback to current directory
            fallback_dir = os.path.join(os.getcwd(), '.sk')
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir
        

    def _load_from_file(self) -> bool:
        """Load stored variables from JSON file."""
        if not os.path.exists(self.storage_file):
            return False
            
        try:
            with file_lock(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                
                # Validate file format
                if not self._validate_storage_data(data):
                    print(f"Warning: Storage file validation failed: {self.storage_file}")
                    return False
                
                # Load storage data
                if 'storage' in data:
                    storage_data = data['storage']
                    if 'local_data' in storage_data:
                        for name, var_data in storage_data['local_data'].items():
                            try:
                                self._storage['local_data'][name] = var_data
                                # Populate cache with loaded data
                                self._cache.put(name, var_data)
                            except Exception as e:
                                print(f"Error: Failed to load local variable {name}: {e}")
                    
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
                                print(f"Error: Failed to load cross-process data for {process_id}: {e}")
                
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
                            print(f"Error: Failed to load cross-storage data from {source_path}: {e}")
                
                return True
                
        except Exception as e:
            print(f"Error: Failed to load storage file {self.storage_file}: {e}")
            return False

    def _save_to_file(self) -> None:
        """Save current variables to JSON file with file locking and validation."""
        if self._storage is None:
            print("Warning: Cannot save - storage not initialized")
            return
        
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
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
                        print(f"Error: Failed to convert storage to dict: {e}")
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
                        "cross_process_storage": cross_storage_data,
                        "statistics": {
                            "reads": self._stats.reads,
                            "writes": self._stats.writes,
                            "errors": self._stats.errors,
                            "cache_hits": self._stats.cache_hits,
                            "cache_misses": self._stats.cache_misses
                        }
                    }
                    
                    # Use file locking for atomic operations
                    with file_lock(self.storage_file):
                        # Create backup if original exists
                        if os.path.exists(self.storage_file):
                            backup_file = self.storage_file + '.backup'
                            shutil.copy2(self.storage_file, backup_file)
                        
                        # Atomic write operation
                        temp_file = self.storage_file + f'.tmp.{os.getpid()}'
                        
                        with open(temp_file, 'w') as f:
                            json.dump(data, f, indent=2, default=str)
                        
                        # Validate written data
                        with open(temp_file, 'r') as f:
                            validated_data = json.load(f)
                            if not self._validate_storage_data(validated_data):
                                raise ValueError("Data validation failed after write")
                        
                        # Replace original file atomically
                        os.replace(temp_file, self.storage_file)
                    
                    # Success - return
                    return
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Warning: Save attempt {attempt + 1} failed, retrying: {e}")
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    # This is a CRITICAL error - don't swallow it
                    print(f"Error: Failed to save storage after {max_retries} attempts: {e}")
                    raise SKGlobalStorageError(f"Failed to save storage after {max_retries} attempts: {e}") from e


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
                print(f"Error: Sync operation failed: {e}")
                raise SKGlobalSyncError(f"Sync operation failed: {e}") from e

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
    
    def reset_for_testing(self):
        """Reset storage state for testing purposes."""
        with self._lock:
            if self._storage is not None:
                self._storage['local_data'].clear()
                self._storage['cross_process_data'].clear()
            
            if self._cross_process_storage is not None:
                self._cross_process_storage.clear()
                
            self._cache.clear()
            
            # Reset stats
            self._stats = StorageStats()

    @classmethod
    def reset_all_storages_for_testing(cls):
        """Reset all singleton storages for testing."""
        with cls._storage_lock:
            for storage in cls._storages.values():
                if hasattr(storage, 'reset_for_testing'):
                    storage.reset_for_testing()

# API for global variable management

def create_global(name: str, value: Any = None, level: GlobalLevel = GlobalLevel.TOP, 
                 path: Optional[str] = None, auto_sync: bool = True, 
                 remove_in: Optional[float] = None) -> SKGlobal:
    """
    Convenience function to create a global variable.
    
    Args:
        name: Name of the global variable
        value: Initial value
        level: Storage level (TOP or UNDER)
        path: Storage path (None for auto-detection)
        auto_sync: Enable cross-process synchronization
        remove_in: Seconds before automatic removal
        
    Returns:
        SKGlobal: The created global variable
    """
    return SKGlobal(
        level=level,
        path=path,
        name=name,
        value=value,
        auto_sync=auto_sync,
        auto_create=True,
        remove_in=remove_in
    )

def get_global(name: str, path: Optional[str] = None, 
              level: GlobalLevel = GlobalLevel.TOP,
              auto_sync: Optional[bool] = None) -> Optional[SKGlobal]:
    """
    Convenience function to get an existing global variable.
    
    Args:
        name: Name of the global variable
        path: Storage path (None for auto-detection)
        level: Storage level (TOP or UNDER)
        auto_sync: Enable cross-process synchronization
        
    Returns:
        SKGlobal or None: The global variable if found
    """
    return SKGlobal.get_global(name, path, level, auto_sync)

def get_skglobal(name: str) -> Optional[Any]:
    """Get a global variable value."""
    g = SKGlobal.get_global(name, level=GlobalLevel.TOP)
    return g.get() if g else None

def get_system_stats() -> Dict[str, Any]:
    """Get comprehensive system statistics for all SKGlobal components."""
    return {
        'resource_manager': _resource_manager.get_stats(),
        'health_check': _resource_manager.health_check(),
        'removal_manager': {
            'scheduled_removals': len(RemovalManager().get_scheduled_removals())
        }
    }

def health_check() -> Dict[str, Any]:
    """Perform a health check on the SKGlobal system."""
    return _resource_manager.health_check()

# Context manager for safe usage
@contextlib.contextmanager
def skglobal_session(cleanup_on_exit: bool = True):
    """Context manager for safe SKGlobal usage."""
    try:
        yield
    finally:
        if cleanup_on_exit:
            _resource_manager.cleanup_all()

# Module cleanup
def _cleanup_on_exit():
    """Clean up resources on module exit."""
    try:
        _resource_manager.cleanup_all()
    except Exception as e:
        print(f"Error: Module cleanup failed: {e}")

atexit.register(_cleanup_on_exit)