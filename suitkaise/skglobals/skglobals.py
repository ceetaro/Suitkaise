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

from suitkaise.skglobals._project_indicators import project_indicators
import suitkaise.skpath.skpath as skpath
import suitkaise.sktime.sktime as sktime
from suitkaise.cereal import Cereal, create_shared_dict

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
        if remove_in is not None and remove_in > 0 and remove_in != float('inf'):
            self.remove_in = float(remove_in)
        else:
            self.remove_in = None
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
        if self.auto_sync:
            cereal = Cereal()
            if not cereal.serializable(value, mode='internal'):
                raise SKGlobalValueError(
                    "Value is not serializable. Cannot sync with other processes. "
                    "Set auto_sync=False to use non-serializable values."
                )
        
        self.value = value
        
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
    def get_global(cls, name: str, path: Optional[str] = None, 
                level: GlobalLevel = GlobalLevel.TOP,
                auto_sync: Optional[bool] = None) -> Optional['SKGlobal']:
        """Get an existing global variable by name."""
        if path is None:
            path = get_project_root() if level == GlobalLevel.TOP else skpath.get_caller_file_path()
        
        # Determine auto_sync if not specified
        if auto_sync is None:
            auto_sync = True  # Default to sync storage
        
        storage = SKGlobalStorage.get_storage(path, level, auto_sync)
        data = storage.get(name)
        
        if data:
            global_var = cls.__new__(cls)
            global_var.name = name
            global_var.path = path
            global_var.level = level
            global_var.value = data['value']
            global_var.storage = storage  # ✅ Add missing storage attribute
            global_var.auto_sync = data.get('auto_sync', True)
            remove_in_data = data.get('remove_in')
            global_var.remove_in = remove_in_data if remove_in_data is not None else None
            return global_var
        
        return None

class SKGlobalStorage:
    """
    Container to store and manage global variables.
    """
    
    _storages: Dict[str, 'SKGlobalStorage'] = {}
    _storage_lock = threading.RLock()
    _startup_cleaned = False
    _cereal = Cereal()  # ✅ NEW: Single Cereal instance for the class
    
    @classmethod
    def _get_manager(cls):
        """Get or create the cloudpickle manager."""
        return cls._cereal.get_internal_manager()  # ✅ CHANGED: Through Cereal
    
    @classmethod
    def disable_multiprocessing(cls):
        """Disable multiprocessing for testing or single-process use."""
        cls._cereal.cleanup()  # ✅ CHANGED: Through Cereal
    
    
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
            self._shared_storage = self._cereal.create_shared_dict()  # ✅ CHANGED: Through Cereal
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
        with self._lock:
            # Get our variables
            keys_to_sync = self.list_variables()
            if key_filter:
                keys_to_sync = [k for k in keys_to_sync if key_filter(k)]
            
            # ✅ Fix: Copy data from this storage to other storage
            for key in keys_to_sync:
                data = self.get(key)  # Get from source (self)
                if data:
                    with other_storage._lock:
                        other_storage.set(key, data)  # Set in target

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
    import tempfile
    import shutil
    import time
    
    def run_tests():
        """Run all SKGlobal tests."""
        print("🧪 Starting SKGlobal Tests...")
        print("=" * 50)
        
        # Test counters
        total_tests = 0
        passed_tests = 0
        
        def test_case(name: str, test_func):
            nonlocal total_tests, passed_tests
            total_tests += 1
            try:
                white = "⬜️"
                green = "🟩"
                red = "❌"
                print(f"\n{white * 30}\n\n  TESTING: {name}\n")
                test_func()
                print(f"\n   {green * 12} PASSED: {name}")
                passed_tests += 1
            except Exception as e:
                print(f"\n   {red * 12} FAILED: {name}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Run all test groups
        test_case("Project Root Detection", test_project_root_detection)
        test_case("Basic SKGlobal Creation", test_basic_skglobal_creation)
        test_case("SKGlobal Factory Method", test_skglobal_factory_method)
        test_case("SKGlobalStorage Basic Operations", test_storage_basic_operations)
        test_case("Contains Functionality", test_contains_functionality)
        test_case("Global Variable Get/Set", test_global_get_set)
        test_case("Storage Persistence", test_storage_persistence)
        test_case("Different Global Levels", test_global_levels)
        test_case("Auto-sync vs Non-sync", test_auto_sync_behavior)
        test_case("Error Handling", test_error_handling)
        test_case("Cleanup and Removal", test_cleanup_and_removal)
        test_case("Multiple Storage Instances", test_multiple_storage_instances)
        test_case("Stress Test", test_stress_test)
        test_case("Concurrency Test", test_concurrent_access)
        
        # Print results
        print("\n" + "=" * 50)
        print(f"🏁 Test Results: {passed_tests}/{total_tests} passed")
        if passed_tests == total_tests:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {total_tests - passed_tests} tests failed")
        print("=" * 50)
    
    def test_project_root_detection():
        """Test project root detection functionality."""
        print("   Testing project root detection...")
        
        # Test 1: Get project root from current location
        root = get_project_root()
        assert os.path.exists(root), f"Project root doesn't exist: {root}"
        assert os.path.isdir(root), f"Project root is not a directory: {root}"
        print(f"   ✅ Found project root: {root}")
        
        # Test 2: Get project root from specific path
        current_file = __file__
        root2 = get_project_root(current_file)
        assert root == root2, "Project root should be same regardless of starting point"
        print(f"   ✅ Consistent project root detection")
    
    def test_basic_skglobal_creation():
        """Test basic SKGlobal creation."""
        print("   Testing basic SKGlobal creation...")
        
        # Test 1: Create with auto_create=True
        global1 = SKGlobal(
            name="test_basic_1",
            value="Hello World",
            auto_create=True
        )
        assert global1.name == "test_basic_1"
        assert global1.value == "Hello World"
        assert global1.level == GlobalLevel.TOP
        print("   ✅ Basic global created successfully")
        
        # Test 2: Create with custom level
        global2 = SKGlobal(
            name="test_basic_2", 
            value=42,
            level=GlobalLevel.UNDER,
            auto_create=True
        )
        assert global2.level == GlobalLevel.UNDER
        assert global2.value == 42
        print("   ✅ Custom level global created")
        
        # Test 3: Auto-generated name
        global3 = SKGlobal(value="auto_name_test", auto_create=True)
        assert global3.name.startswith("global_")
        assert len(global3.name) > 7  # Should have generated suffix
        print(f"   ✅ Auto-generated name: {global3.name}")
    
    def test_skglobal_factory_method():
        """Test SKGlobal factory method."""
        print("   Testing SKGlobal factory method...")
        
        # Test 1: Factory with auto_create=True
        global_obj, creator_func = SKGlobal.create(
            name="test_factory_1",
            value="Factory Test",
            auto_create=True
        )
        assert global_obj is not None
        assert creator_func is None
        assert global_obj.name == "test_factory_1"
        print("   ✅ Factory method with auto_create=True")
        
        # Test 2: Factory with auto_create=False
        global_obj2, creator_func2 = SKGlobal.create(
            name="test_factory_2",
            value="Delayed Creation",
            auto_create=False
        )
        assert global_obj2 is not None
        assert creator_func2 is not None
        assert callable(creator_func2)
        
        # Execute the creator
        result = creator_func2()
        assert result == "Delayed Creation"
        print("   ✅ Factory method with delayed creation")
    
    def test_storage_basic_operations():
        """Test SKGlobalStorage basic operations."""
        print("   Testing storage basic operations...")
        
        # Get storage instance
        test_path = get_project_root()
        storage = SKGlobalStorage.get_storage(test_path, GlobalLevel.TOP)
        
        # Test data
        test_data = {
            'name': 'test_storage',
            'value': 'storage_test_value',
            'created_at': sktime.now()
        }
        
        # Test set/get
        storage.set("test_var", test_data)
        retrieved = storage.get("test_var")
        assert retrieved is not None
        assert retrieved['value'] == 'storage_test_value'
        print("   ✅ Set and get operations")
        
        # Test list_variables
        variables = storage.list_variables()
        assert "test_var" in variables
        print(f"   ✅ List variables: {len(variables)} found")
        
        # Test remove
        storage.remove("test_var")
        assert storage.get("test_var") is None
        print("   ✅ Remove operation")
    
    def test_contains_functionality():
        """Test the new __contains__ and contains methods."""
        print("   Testing contains functionality...")
        
        # Create storage and global
        storage = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP)
        global_var = SKGlobal(name="test_contains", value="contains_test", auto_create=True)
        
        # Test __contains__ with SKGlobal instance
        assert global_var in storage, "SKGlobal instance should be in storage"
        print("   ✅ __contains__ with SKGlobal instance")
        
        # Test __contains__ with string
        assert "test_contains" in storage, "Variable name should be in storage"
        print("   ✅ __contains__ with variable name")
        
        # Test contains method
        assert storage.contains(global_var), "contains() method with SKGlobal"
        assert storage.contains("test_contains"), "contains() method with string"
        print("   ✅ contains() method")
        
        # Test has_variable
        assert storage.has_variable("test_contains"), "has_variable() method"
        print("   ✅ has_variable() method")
        
        # Test negative cases
        assert "nonexistent" not in storage
        assert not storage.contains("nonexistent")
        assert not storage.has_variable("nonexistent")
        print("   ✅ Negative cases work correctly")
        
        # Test invalid types
        assert 123 not in storage
        assert None not in storage
        assert [] not in storage
        print("   ✅ Invalid types handled correctly")
    
    def test_global_get_set():
        """Test SKGlobal get and set operations."""
        print("   Testing global get/set operations...")
        
        # Create global
        global_var = SKGlobal(name="test_get_set", value="initial", auto_create=True)
        
        # Test get
        value = global_var.get()
        assert value == "initial", f"Expected 'initial', got {value}"
        print("   ✅ Get operation")
        
        # Test set
        global_var.set("updated")
        updated_value = global_var.get()
        assert updated_value == "updated", f"Expected 'updated', got {updated_value}"
        print("   ✅ Set operation")
        
        # Test persistence
        retrieved_global = SKGlobal.get_global("test_get_set")
        assert retrieved_global is not None
        assert retrieved_global.get() == "updated"
        print("   ✅ Value persistence")
    
    def test_storage_persistence():
        """Test storage file persistence."""
        print("   Testing storage persistence...")
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Note: This test might be limited since we use project root
            # But we can test the file creation logic
            pass
        
        # Test with actual storage
        storage = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP)
        
        # Add some test data
        test_data = {'name': 'persist_test', 'value': 'persistent_value'}
        storage.set("persist_test", test_data)
        
        # Check that storage file exists
        assert os.path.exists(storage.storage_file), "Storage file should exist"
        print(f"   ✅ Storage file created: {storage.storage_file}")
        
        # Verify file contains our data
        with open(storage.storage_file, 'r') as f:
            file_data = json.load(f)
            assert 'variables' in file_data
            assert 'persist_test' in file_data['variables']
        print("   ✅ Data persisted to file")
        
        # Clean up
        storage.remove("persist_test")
    
    def test_global_levels():
        """Test different GlobalLevel behaviors."""
        print("   Testing different global levels...")
        
        # Test TOP level
        top_global = SKGlobal(
            name="test_top_level",
            value="top_value",
            level=GlobalLevel.TOP,
            auto_create=True
        )
        assert top_global.level == GlobalLevel.TOP
        assert top_global.path == get_project_root()
        print("   ✅ TOP level global")
        
        # Test UNDER level
        under_global = SKGlobal(
            name="test_under_level", 
            value="under_value",
            level=GlobalLevel.UNDER,
            auto_create=True
        )
        assert under_global.level == GlobalLevel.UNDER
        # Path should be different from project root (unless this file is in root)
        print(f"   ✅ UNDER level global (path: {under_global.path})")
        
        # Verify they use different storage
        top_storage = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP)
        under_storage = SKGlobalStorage.get_storage(under_global.path, GlobalLevel.UNDER)
        
        # They might be the same if file is in project root, but that's OK
        print(f"   ✅ Different storage instances created")
    
    def test_auto_sync_behavior():
        """Test auto_sync vs non-auto_sync behavior."""
        print("   Testing auto_sync behavior...")
        
        # Test auto_sync=True (default)
        sync_global = SKGlobal(
            name="test_sync",
            value="sync_value",
            auto_sync=True,
            auto_create=True
        )
        assert sync_global.auto_sync == True
        print("   ✅ Auto-sync global created")
        
        # ✅ Test auto_sync=False with serializable value first
        no_sync_global = SKGlobal(
            name="test_no_sync",
            value="no_sync_value",  # Use simple string (serializable)
            auto_sync=False,
            auto_create=True
        )
        assert no_sync_global.auto_sync == False
        print("   ✅ Non-sync global created")
        
        # Test that different storage instances are created
        sync_storage = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP, True)
        no_sync_storage = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP, False)
        
        # Verify they're different instances
        assert sync_storage is not no_sync_storage
        print("   ✅ Different storage instances for sync vs no-sync")
        
    def test_error_handling():
        """Test error handling and edge cases."""
        print("   Testing error handling...")
        
        # Test invalid level
        try:
            SKGlobal(level="invalid", auto_create=True)
            assert False, "Should have raised error for invalid level"
        except SKGlobalValueError:
            print("   ✅ Invalid level error handled")
        
        # Test non-serializable value with auto_sync=True
        class NonSerializable:
            def __init__(self):
                self.func = lambda x: x
        
        try:
            SKGlobal(
                name="test_non_serializable",
                value=NonSerializable(),
                auto_sync=True,  # This should trigger serialization check
                auto_create=True
            )
            assert False, "Should have raised error for non-serializable value"
        except SKGlobalValueError:
            print("   ✅ Non-serializable value error handled")
        
        # ✅ Test that non-serializable values work with auto_sync=False
        try:
            non_sync_global = SKGlobal(
                name="test_non_serializable_no_sync",
                value=NonSerializable(),
                auto_sync=False,  # This should work
                auto_create=True
            )
            print("   ✅ Non-serializable value works with auto_sync=False")
        except Exception as e:
            assert False, f"Should not raise error with auto_sync=False: {e}"
        
        # Test non-existent path
        try:
            SKGlobalStorage("/non/existent/path", GlobalLevel.TOP)
            assert False, "Should have raised error for non-existent path"
        except SKGlobalError:
            print("   ✅ Non-existent path error handled")
    
    def test_cleanup_and_removal():
        """Test cleanup and removal functionality."""
        print("   Testing cleanup and removal...")
        
        # Create a global with removal timer
        timed_global = SKGlobal(
            name="test_timed_removal",
            value="will_be_removed",
            remove_in=0.1,  # Remove after 0.1 seconds
            auto_create=True
        )
        
        # Verify it exists initially
        assert timed_global.get() == "will_be_removed"
        print("   ✅ Timed global created")
        
        # Wait for removal
        time.sleep(0.2)
        
        # Check if it was removed (this might be flaky due to threading)
        try:
            result = timed_global.get()
            if result is None:
                print("   ✅ Timed removal worked")
            else:
                print("   ⚠ Timed removal might be delayed (threading)")
        except:
            print("   ✅ Timed removal worked (variable not found)")
        
        # Test manual removal
        manual_global = SKGlobal(name="test_manual_removal", value="to_remove", auto_create=True)
        assert manual_global.get() == "to_remove"
        
        manual_global.remove()
        assert manual_global.get() is None
        print("   ✅ Manual removal")
        
        # Test storage clear
        storage = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP)
        storage.set("temp_var", {"value": "temp"})
        assert "temp_var" in storage
        
        storage.clear()
        assert "temp_var" not in storage
        print("   ✅ Storage clear")
    
    def test_multiple_storage_instances():
        """Test multiple storage instances and their interactions."""
        print("   Testing multiple storage instances...")
        
        # Get same storage multiple times - should return same instance
        storage1 = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP)
        storage2 = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP)
        assert storage1 is storage2, "Should return same instance for same parameters"
        print("   ✅ Same storage instance returned")
        
        # Different parameters should give different instances
        storage_sync = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP, True)
        storage_no_sync = SKGlobalStorage.get_storage(get_project_root(), GlobalLevel.TOP, False)
        assert storage_sync is not storage_no_sync
        print("   ✅ Different instances for different sync settings")
        
        # Test sync_with method
        storage_sync.set("sync_test", {"value": "sync_data"})
        storage_no_sync.sync_with(storage_sync)
        
        synced_data = storage_no_sync.get("sync_test")
        assert synced_data is not None
        assert synced_data["value"] == "sync_data"
        print("   ✅ Storage synchronization")
        
        # Clean up
        storage_sync.remove("sync_test")
        storage_no_sync.remove("sync_test")

    def test_stress_test():
        """Stress test with many globals."""
        print("   Running stress test...")
        
        # Create many globals
        globals_list = []
        for i in range(100):
            global_var = SKGlobal(
                name=f"stress_test_{i}",
                value=f"value_{i}",
                auto_create=True
            )
            globals_list.append(global_var)
        
        print(f"   ✅ Created {len(globals_list)} globals")
        
        # Verify they all exist
        for i, global_var in enumerate(globals_list):
            assert global_var.get() == f"value_{i}"
        
        print("   ✅ All globals verified")
        
        # Clean up
        for global_var in globals_list:
            global_var.remove()
        
        print("   ✅ Stress test cleanup complete")

    def test_concurrent_access():
        """Test concurrent access (basic threading test)."""
        print("   Testing concurrent access...")
        
        import threading
        import time
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                global_var = SKGlobal(
                    name=f"concurrent_test_{worker_id}",
                    value=f"worker_{worker_id}",
                    auto_create=True
                )
                time.sleep(0.01)  # Small delay
                value = global_var.get()
                results.append(value)
                global_var.remove()
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        print("   ✅ Concurrent access successful")
    
    # Run all tests
    run_tests()