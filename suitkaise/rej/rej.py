# suitkaise/rej/rej.py

"""
Rej - Simple registry classes for storing and managing collections of objects.

Rej provides basic registry functionality, while RejSingleton creates globally
accessible registries that can be shared across processes using SKGlobal storage.

Quick Start:
    # Get a global registry
    my_registry = getrej("my_items")
    
    # Register something
    my_registry.register("key1", some_object)
    
    # Get it back
    obj = my_registry.get("key1")
    
    # List all registries
    all_registries = listrej()
"""
import threading
from typing import Any, Dict, Optional, List, Callable, TypeVar, Generic, Union
from enum import Enum, auto
from dataclasses import dataclass, field

from suitkaise.skglobals import SKGlobal, GlobalLevel
from suitkaise.cereal import Cereal
import suitkaise.sktime.sktime as sktime

T = TypeVar('T')

class RejError(Exception):
    """Something went wrong with a registry operation."""
    pass

class RejKeyError(RejError):
    """The registry key you're looking for doesn't exist."""
    pass

class RejDuplicateError(RejError):
    """You tried to register something with a key that already exists."""
    pass

class RejSerializationError(RejError):
    """The item you're trying to register can't be serialized for cross-process use."""
    pass

class Rej(Generic[T]):
    """
    A basic registry for storing key-value pairs of any type.
    
    Think of this as a smart dictionary that:
    - Handles duplicate keys intelligently
    - Tracks metadata about stored items  
    - Can test if items work with cross-process serialization
    - Is thread-safe for concurrent access
    
    Example:
        # Create a registry for database connections
        db_registry = Rej[DatabaseConnection]("databases")
        
        # Register items
        db_registry.register("main", main_db_connection)
        db_registry.register("cache", cache_db_connection)
        
        # Get items back
        main_db = db_registry.get("main")
        
        # Find items
        all_dbs = db_registry.find(lambda key, db: db.is_connected())
    """
    
    class Ruleset:
        """
        Rules and settings that control how the registry behaves.
        
        This keeps all rule-related enums and settings organized in one place.
        """
        
        class OnDuplicate(Enum):
            """
            How to handle when you try to register something with a key that already exists.
            
            - CREATE_NEW: Make a new key by adding _1, _2, etc.
            - OVERWRITE: Replace the existing item with the new one
            - IGNORE: Keep the existing item, ignore the new one  
            - RAISE_ERROR: Stop everything and raise an error
            """
            CREATE_NEW = auto()
            OVERWRITE = auto()
            IGNORE = auto()
            RAISE_ERROR = auto()
    
    class Dataset:
        """
        Data structures and classes related to what gets stored in the registry.
        
        This keeps all data-related classes organized in one place.
        """
        
        @dataclass
        class RejMetadata:
            """
            Information that gets automatically tracked for each registered item.
            
            This helps you understand when items were added, how often they're used, etc.
            """
            created_at: float = field(default_factory=sktime.now)
            modified_at: float = field(default_factory=sktime.now)
            access_count: int = 0
            created_by_process: str = field(default_factory=lambda: str(__import__('os').getpid()))
            is_serializable: bool = False
            
            def record_access(self):
                """Mark that this item was accessed (retrieved from registry)."""
                self.access_count += 1
            
            def record_modification(self):
                """Mark that this item was modified (updated in registry)."""
                self.modified_at = sktime.now()
    
    def __init__(self, 
                 name: str,
                 on_duplicate: 'Rej.Ruleset.OnDuplicate' = None,
                 auto_serialize_check: bool = True):
        """
        Create a new registry.
        
        Args:
            name: A human-readable name for this registry
            on_duplicate: What to do when someone tries to register a duplicate key
            auto_serialize_check: Whether to test if items can be serialized for cross-process use
        """
        self.name = name
        self.on_duplicate = on_duplicate or Rej.Ruleset.OnDuplicate.RAISE_ERROR
        self.auto_serialize_check = auto_serialize_check
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Storage
        self._items: Dict[str, T] = {}
        self._metadata: Dict[str, Rej.Dataset.RejMetadata] = {}
        
        # Serialization testing
        self._cereal = Cereal() if auto_serialize_check else None
        
        # Registry info
        self.created_at = sktime.now()
        
    def register(self, key: str, item: T, metadata: Optional[Dict] = None) -> str:
        """
        Add an item to the registry.
        
        Args:
            key: The name to store the item under
            item: The actual item to store
            metadata: Optional extra information to store with the item
            
        Returns:
            str: The actual key that was used (might be different if duplicate handling changed it)
            
        Raises:
            RejDuplicateError: If key exists and on_duplicate is RAISE_ERROR
            RejSerializationError: If auto_serialize_check is True and item can't be serialized
        """
        with self._lock:
            # Test serialization if requested
            is_serializable = False
            if self.auto_serialize_check and self._cereal:
                try:
                    is_serializable = self._cereal.serializable(item, mode='internal')
                    if not is_serializable:
                        raise RejSerializationError(
                            f"Item with key '{key}' cannot be serialized for cross-process use. "
                            f"Set auto_serialize_check=False if you don't need cross-process access."
                        )
                except Exception as e:
                    raise RejSerializationError(f"Serialization test failed for key '{key}': {e}")
            
            # Handle duplicates
            final_key = self._handle_duplicate_key(key)
            
            # Create metadata
            item_metadata = Rej.Dataset.RejMetadata(
                is_serializable=is_serializable,
                created_by_process=str(__import__('os').getpid())
            )
            
            # Add any extra metadata provided
            if metadata:
                for attr_name, value in metadata.items():
                    if hasattr(item_metadata, attr_name):
                        setattr(item_metadata, attr_name, value)
            
            # Store the item
            self._items[final_key] = item
            self._metadata[final_key] = item_metadata
            
            return final_key
    
    def get(self, key: str) -> Optional[T]:
        """
        Get an item from the registry by its key.
        
        Args:
            key: The key to look for
            
        Returns:
            The item if found, None if not found
        """
        with self._lock:
            if key in self._items:
                # Record that this item was accessed
                self._metadata[key].record_access()
                return self._items[key]
            return None
    
    def get_required(self, key: str) -> T:
        """
        Get an item from the registry, raising an error if not found.
        
        Args:
            key: The key to look for
            
        Returns:
            The item
            
        Raises:
            RejKeyError: If the key doesn't exist
        """
        item = self.get(key)
        if item is None:
            raise RejKeyError(f"Key '{key}' not found in registry '{self.name}'")
        return item
    
    def update(self, key: str, item: T) -> bool:
        """
        Update an existing item in the registry.
        
        Args:
            key: The key to update
            item: The new item to store
            
        Returns:
            True if the key existed and was updated, False if key didn't exist
        """
        with self._lock:
            if key not in self._items:
                return False
            
            # Test serialization if needed
            if self.auto_serialize_check and self._cereal:
                try:
                    is_serializable = self._cereal.serializable(item, mode='internal')
                    if not is_serializable:
                        raise RejSerializationError(
                            f"Updated item with key '{key}' cannot be serialized for cross-process use."
                        )
                    self._metadata[key].is_serializable = is_serializable
                except Exception as e:
                    raise RejSerializationError(f"Serialization test failed for updated key '{key}': {e}")
            
            # Update the item
            self._items[key] = item
            self._metadata[key].record_modification()
            
            return True
    
    def remove(self, key: str) -> bool:
        """
        Remove an item from the registry.
        
        Args:
            key: The key to remove
            
        Returns:
            True if the key existed and was removed, False if key didn't exist
        """
        with self._lock:
            if key in self._items:
                del self._items[key]
                del self._metadata[key]
                return True
            return False
    
    def list_keys(self) -> List[str]:
        """Get a list of all keys in the registry."""
        with self._lock:
            return list(self._items.keys())
    
    def list_items(self) -> Dict[str, T]:
        """Get a copy of all items in the registry."""
        with self._lock:
            return dict(self._items)
    
    def find(self, filter_func: Callable[[str, T], bool]) -> Dict[str, T]:
        """
        Find items that match a condition.
        
        Args:
            filter_func: A function that takes (key, item) and returns True if it matches
            
        Returns:
            Dictionary of matching key-item pairs
            
        Example:
            # Find all items whose keys start with "test"
            test_items = registry.find(lambda key, item: key.startswith("test"))
            
            # Find all items that are instances of a specific class
            db_items = registry.find(lambda key, item: isinstance(item, DatabaseConnection))
        """
        with self._lock:
            matches = {}
            for key, item in self._items.items():
                try:
                    if filter_func(key, item):
                        matches[key] = item
                        # Record access
                        self._metadata[key].record_access()
                except Exception:
                    # Skip items that cause errors in the filter function
                    continue
            return matches
    
    def get_metadata(self, key: str) -> Optional['Rej.Dataset.RejMetadata']:
        """Get metadata information for a specific key."""
        with self._lock:
            return self._metadata.get(key)
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get summary information about this registry.
        
        Returns:
            Dictionary with registry statistics and info
        """
        with self._lock:
            total_items = len(self._items)
            serializable_count = sum(1 for meta in self._metadata.values() if meta.is_serializable)
            total_accesses = sum(meta.access_count for meta in self._metadata.values())
            
            return {
                'name': self.name,
                'total_items': total_items,
                'serializable_items': serializable_count,
                'total_accesses': total_accesses,
                'on_duplicate': self.on_duplicate.name,
                'auto_serialize_check': self.auto_serialize_check,
                'created_at': self.created_at,
                'keys': self.list_keys()
            }
    
    def clear(self) -> int:
        """
        Remove all items from the registry.
        
        Returns:
            Number of items that were removed
        """
        with self._lock:
            count = len(self._items)
            self._items.clear()
            self._metadata.clear()
            return count
    
    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the registry using 'in' operator."""
        with self._lock:
            return key in self._items
    
    def __len__(self) -> int:
        """Get the number of items in the registry."""
        with self._lock:
            return len(self._items)
    
    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"Rej(name='{self.name}', items={len(self._items)}, on_duplicate={self.on_duplicate.name})"
    
    def _handle_duplicate_key(self, key: str) -> str:
        """
        Handle duplicate key based on the registry's policy.
        
        Returns the final key to use.
        """
        if key not in self._items:
            return key
        
        if self.on_duplicate == Rej.Ruleset.OnDuplicate.RAISE_ERROR:
            raise RejDuplicateError(f"Key '{key}' already exists in registry '{self.name}'")
        
        elif self.on_duplicate == Rej.Ruleset.OnDuplicate.IGNORE:
            return key  # Will be ignored by caller
        
        elif self.on_duplicate == Rej.Ruleset.OnDuplicate.OVERWRITE:
            return key  # Will overwrite existing
        
        elif self.on_duplicate == Rej.Ruleset.OnDuplicate.CREATE_NEW:
            # Find the next available key like key_1, key_2, etc.
            counter = 1
            while f"{key}_{counter}" in self._items:
                counter += 1
            return f"{key}_{counter}"
        
        else:
            raise RejError(f"Unknown duplicate handling strategy: {self.on_duplicate}")



class RejSingleton(Rej[T]):
    """
    A singleton registry that's globally accessible and can be shared across processes.
    
    This uses SKGlobal storage at the TOP level, so all RejSingleton registries
    are available anywhere in your project and can be accessed from multiple processes.
    
    Example:
        # Get or create a global registry
        global_funcs = RejSingleton.get_registry("functions")
        
        # Register something
        global_funcs.register("my_func", some_function)
        
        # Access from anywhere else in your project
        same_registry = RejSingleton.get_registry("functions")
        my_func = same_registry.get("my_func")  # Gets the same function
    """
    
    _registries: Dict[str, 'RejSingleton'] = {}
    _registry_lock = threading.RLock()
    
    @classmethod
    def get_registry(cls, 
                     name: str,
                     on_duplicate: 'Rej.Ruleset.OnDuplicate' = None,
                     auto_serialize_check: bool = True) -> 'RejSingleton[T]':
        """
        Get or create a singleton registry by name.
        
        If a registry with this name already exists, returns the existing one.
        If not, creates a new one with the specified settings.
        
        Args:
            name: Unique name for this registry
            on_duplicate: How to handle duplicate keys (only used if creating new registry)
            auto_serialize_check: Whether to test serialization (only used if creating new registry)
            
        Returns:
            The singleton registry instance
        """
        with cls._registry_lock:
            if name not in cls._registries:
                # Create new singleton registry
                registry = cls._create_singleton(name, on_duplicate or Rej.Ruleset.OnDuplicate.RAISE_ERROR, auto_serialize_check)
                cls._registries[name] = registry
                return registry
            else:
                return cls._registries[name]
    
    @classmethod
    def _create_singleton(cls, name: str, on_duplicate: 'Rej.Ruleset.OnDuplicate', auto_serialize_check: bool) -> 'RejSingleton[T]':
        """Create a new singleton registry and store it in SKGlobal."""
        # Create the registry instance
        registry = cls.__new__(cls)
        registry.__init__(name, on_duplicate, auto_serialize_check)
        
        # Store it in SKGlobal at TOP level
        global_var = SKGlobal(
            level=GlobalLevel.TOP,
            name=f"rejsingleton_{name}",
            value=registry,
            auto_sync=True,
            auto_create=True
        )
        
        registry._global_var = global_var
        return registry
    
    @classmethod
    def list_registries(cls) -> List[str]:
        """Get a list of all singleton registry names that exist."""
        with cls._registry_lock:
            return list(cls._registries.keys())
    
    @classmethod
    def remove_registry(cls, name: str) -> bool:
        """
        Remove a singleton registry entirely.
        
        Warning: This removes the registry from global storage and memory.
        Any existing references to it will become stale.
        
        Args:
            name: Name of the registry to remove
            
        Returns:
            True if registry existed and was removed, False if it didn't exist
        """
        with cls._registry_lock:
            if name in cls._registries:
                registry = cls._registries[name]
                
                # Remove from SKGlobal storage
                if hasattr(registry, '_global_var'):
                    registry._global_var.remove()
                
                # Remove from local cache
                del cls._registries[name]
                return True
            return False
    
    def __init__(self, 
                 name: str,
                 on_duplicate: 'Rej.Ruleset.OnDuplicate' = None,
                 auto_serialize_check: bool = True):
        """
        Initialize singleton registry.
        
        Note: You should use get_registry() instead of calling this directly.
        """
        super().__init__(name, on_duplicate or Rej.Ruleset.OnDuplicate.RAISE_ERROR, auto_serialize_check)
        self._global_var: Optional[SKGlobal] = None
    
    def sync_to_global(self):
        """Manually sync this registry to global storage."""
        if self._global_var:
            self._global_var.set(self)
    
    def get_global_info(self) -> Dict[str, Any]:
        """Get information about this registry's global storage."""
        base_info = self.get_info()
        if self._global_var:
            base_info.update({
                'global_storage_name': self._global_var.name,
                'global_storage_path': self._global_var.path,
                'stored_globally': True
            })
        else:
            base_info['stored_globally'] = False
        return base_info
    
    def __getstate__(self):
        """Prepare RejSingleton for cross-process serialization."""
        try:
            from suitkaise.cereal.skpickle import enhanced_getstate
            return enhanced_getstate(self)
        except ImportError:
            # Fallback if enhanced_getstate is not available
            state = self.__dict__.copy()
            # Remove unserializable items
            if '_lock' in state:
                del state['_lock']
            if '_cereal' in state:
                del state['_cereal']
            return state

    def __setstate__(self, state):
        """Restore RejSingleton after cross-process deserialization."""
        try:
            from suitkaise.cereal.skpickle import enhanced_setstate
            enhanced_setstate(self, state)
        except ImportError:
            # Fallback if enhanced_setstate is not available
            self.__dict__.update(state)
            # Recreate unserializable items
            self._lock = threading.RLock()
            self._cereal = Cereal() if getattr(self, 'auto_serialize', True) else None


# =============================================================================
# Tests
# =============================================================================

if __name__ == "__main__":
    def run_tests():
        """Run basic functionality tests for Rej and RejSingleton."""
        print("🧪 Starting Rej Registry Tests...")
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
        
        # Test basic registry creation
        def test_basic_creation():
            registry = Rej[str]("test_registry")
            assert registry.name == "test_registry"
            assert len(registry) == 0
            assert registry.auto_serialize_check == True  # default
            print(f"   Created registry: {registry}")
        
        test("Basic Registry Creation", test_basic_creation)
        
        # Test basic registration and retrieval
        def test_basic_register_get():
            registry = Rej[str]("test_basic")
            
            # Register an item
            key = registry.register("test_key", "test_value")
            assert key == "test_key"
            assert len(registry) == 1
            assert "test_key" in registry
            
            # Get the item back
            value = registry.get("test_key")
            assert value == "test_value"
            
            # Test get_required
            value2 = registry.get_required("test_key")
            assert value2 == "test_value"
            
            # Test metadata
            metadata = registry.get_metadata("test_key")
            assert metadata is not None
            assert metadata.access_count == 2  # Called get twice
            assert metadata.is_serializable == True  # string is serializable
            
            print(f"   Registered and retrieved: {key} -> {value}")
            print(f"   Access count: {metadata.access_count}")
        
        test("Basic Register and Get", test_basic_register_get)
        
        # Test duplicate handling - CREATE_NEW
        def test_duplicate_create_new():
            registry = Rej[str]("test_duplicates", 
                               on_duplicate=Rej.Ruleset.OnDuplicate.CREATE_NEW)
            
            # Register original
            key1 = registry.register("duplicate", "value1")
            assert key1 == "duplicate"
            
            # Register duplicate - should create new key
            key2 = registry.register("duplicate", "value2")
            assert key2 == "duplicate_1"
            
            # Register another duplicate
            key3 = registry.register("duplicate", "value3")
            assert key3 == "duplicate_2"
            
            # Verify all values exist
            assert registry.get("duplicate") == "value1"
            assert registry.get("duplicate_1") == "value2"
            assert registry.get("duplicate_2") == "value3"
            assert len(registry) == 3
            
            print(f"   Created keys: {key1}, {key2}, {key3}")
        
        test("Duplicate Handling - CREATE_NEW", test_duplicate_create_new)
        
        # Test duplicate handling - OVERWRITE
        def test_duplicate_overwrite():
            registry = Rej[str]("test_overwrite", 
                               on_duplicate=Rej.Ruleset.OnDuplicate.OVERWRITE)
            
            # Register original
            key1 = registry.register("overwrite_key", "original_value")
            assert registry.get("overwrite_key") == "original_value"
            assert len(registry) == 1
            
            # Register duplicate - should overwrite
            key2 = registry.register("overwrite_key", "new_value")
            assert key2 == "overwrite_key"  # Same key
            assert registry.get("overwrite_key") == "new_value"
            assert len(registry) == 1  # Still only one item
            
            print(f"   Overwritten value: {registry.get('overwrite_key')}")
        
        test("Duplicate Handling - OVERWRITE", test_duplicate_overwrite)
        
        # Test duplicate handling - RAISE_ERROR
        def test_duplicate_raise_error():
            registry = Rej[str]("test_error", 
                               on_duplicate=Rej.Ruleset.OnDuplicate.RAISE_ERROR)
            
            # Register original
            registry.register("error_key", "value1")
            
            # Try to register duplicate - should raise error
            try:
                registry.register("error_key", "value2")
                raise AssertionError("Should have raised RejDuplicateError")
            except RejDuplicateError:
                pass  # Expected
            
            # Original value should still be there
            assert registry.get("error_key") == "value1"
            assert len(registry) == 1
            
            print("   Correctly raised RejDuplicateError")
        
        test("Duplicate Handling - RAISE_ERROR", test_duplicate_raise_error)
        
        # Test find functionality
        def test_find():
            registry = Rej[str]("test_find")
            
            # Register several items
            registry.register("apple", "fruit")
            registry.register("banana", "fruit")
            registry.register("carrot", "vegetable")
            registry.register("app_config", "settings")
            
            # Find items by value
            fruits = registry.find(lambda key, value: value == "fruit")
            assert len(fruits) == 2
            assert "apple" in fruits
            assert "banana" in fruits
            
            # Find items by key pattern
            app_items = registry.find(lambda key, value: key.startswith("app"))
            assert len(app_items) == 2
            assert "apple" in app_items
            assert "app_config" in app_items
            
            print(f"   Found fruits: {list(fruits.keys())}")
            print(f"   Found app items: {list(app_items.keys())}")
        
        test("Find Functionality", test_find)
        
        # Test update and remove
        def test_update_remove():
            registry = Rej[str]("test_update_remove")
            
            # Register item
            registry.register("update_me", "original")
            assert registry.get("update_me") == "original"
            
            # Update item
            updated = registry.update("update_me", "updated")
            assert updated == True
            assert registry.get("update_me") == "updated"
            
            # Try to update non-existent item
            updated_false = registry.update("doesnt_exist", "value")
            assert updated_false == False
            
            # Remove item
            removed = registry.remove("update_me")
            assert removed == True
            assert registry.get("update_me") is None
            assert len(registry) == 0
            
            # Try to remove non-existent item
            removed_false = registry.remove("doesnt_exist")
            assert removed_false == False
            
            print("   Update and remove operations successful")
        
        test("Update and Remove", test_update_remove)
        
        # Test list operations
        def test_list_operations():
            registry = Rej[str]("test_lists")
            
            # Add some items
            registry.register("key1", "value1")
            registry.register("key2", "value2")
            registry.register("key3", "value3")
            
            # Test list_keys
            keys = registry.list_keys()
            assert len(keys) == 3
            assert "key1" in keys
            assert "key2" in keys
            assert "key3" in keys
            
            # Test list_items
            items = registry.list_items()
            assert len(items) == 3
            assert items["key1"] == "value1"
            assert items["key2"] == "value2"
            assert items["key3"] == "value3"
            
            # Test clear
            cleared_count = registry.clear()
            assert cleared_count == 3
            assert len(registry) == 0
            assert len(registry.list_keys()) == 0
            
            print(f"   Listed {len(keys)} keys and cleared {cleared_count} items")
        
        test("List Operations", test_list_operations)
        
        # Test RejSingleton - this should now work with __getstate__/__setstate__
        def test_singleton():
            # Get singleton registry
            registry1 = RejSingleton.get_registry("test_singleton")
            registry1.register("singleton_key", "singleton_value")
            
            # Get the same registry from different call
            registry2 = RejSingleton.get_registry("test_singleton")
            
            # Should be the same registry
            assert registry1 is registry2
            assert registry2.get("singleton_key") == "singleton_value"
            
            # List registries
            registries = RejSingleton.list_registries()
            assert "test_singleton" in registries
            
            print(f"   Singleton registries: {registries}")
        
        test("RejSingleton Basic", test_singleton)
        
        # Test RejSingleton global info
        def test_singleton_global_info():
            registry = RejSingleton.get_registry("test_global_info")
            registry.register("info_key", "info_value")
            
            # Test global info
            global_info = registry.get_global_info()
            assert global_info['stored_globally'] == True
            assert 'global_storage_name' in global_info
            assert global_info['total_items'] == 1
            
            print(f"   Global info keys: {list(global_info.keys())}")
        
        test("RejSingleton Global Info", test_singleton_global_info)
        
        # Test RejSingleton serialization methods
        def test_singleton_serialization():
            registry = RejSingleton.get_registry("test_serialization")
            registry.register("serial_key", "serial_value")
            
            # Test __getstate__ method
            state = registry.__getstate__()
            assert isinstance(state, dict)
            assert 'name' in state
            assert '_items' in state
            # Should not contain locks or cereal in the state
            assert '_lock' not in state or state.get('_skpickle_excluded') is not None
            
            # Test __setstate__ method (create new instance and restore)
            new_registry = RejSingleton.__new__(RejSingleton)
            new_registry.__setstate__(state)
            
            # Should have all the data
            assert new_registry.name == registry.name
            assert new_registry.get("serial_key") == "serial_value"
            # Should have recreated locks
            assert hasattr(new_registry, '_lock')
            
            print("   Serialization methods work correctly")
        
        test("RejSingleton Serialization", test_singleton_serialization)
        
        # Test registry info and metadata
        def test_info_metadata():
            registry = Rej[str]("test_info")
            
            # Add some items with custom metadata
            registry.register("item1", "value1", metadata={"priority": "high"})
            registry.register("item2", "value2", metadata={"priority": "low"})
            
            # Access items to increase access count
            registry.get("item1")
            registry.get("item1")
            registry.get("item2")
            
            # Check metadata
            meta1 = registry.get_metadata("item1")
            meta2 = registry.get_metadata("item2")
            
            assert meta1.access_count == 2
            assert meta2.access_count == 1
            # Note: Your version doesn't have user_metadata field in RejMetadata
            
            # Check registry info
            info = registry.get_info()
            assert info["total_items"] == 2
            assert info["total_accesses"] == 3
            assert "item1" in info["keys"]
            assert "item2" in info["keys"]
            assert info["auto_serialize_check"] == True
            
            print(f"   Registry info: {info['total_items']} items, {info['total_accesses']} accesses")
        
        test("Info and Metadata", test_info_metadata)
        
        # Test error cases
        def test_error_cases():
            registry = Rej[str]("test_errors")
            
            # Test get_required with missing key
            try:
                registry.get_required("missing_key")
                raise AssertionError("Should have raised RejKeyError")
            except RejKeyError:
                pass  # Expected
            
            # Test get with missing key (should return None, not raise)
            result = registry.get("missing_key")
            assert result is None
            
            # Test get_metadata with missing key
            missing_meta = registry.get_metadata("missing_key")
            assert missing_meta is None
            
            print("   Error cases handled correctly")
        
        test("Error Cases", test_error_cases)
        
        # Test serialization settings
        def test_serialization_settings():
            # Test with auto_serialize_check=True (default)
            registry_auto = Rej[dict]("test_auto_serialize", auto_serialize_check=True)
            
            # This should work (dict is serializable)
            test_dict = {"key": "value", "number": 42}
            registry_auto.register("serializable_dict", test_dict)
            
            metadata = registry_auto.get_metadata("serializable_dict")
            assert metadata.is_serializable == True
            
            # Test with auto_serialize_check=False
            registry_no_auto = Rej[dict]("test_no_auto_serialize", auto_serialize_check=False)
            registry_no_auto.register("any_dict", test_dict)
            
            metadata_no_auto = registry_no_auto.get_metadata("any_dict")
            assert metadata_no_auto.is_serializable == False  # Not tested when auto_serialize_check=False
            
            print("   Serialization settings work correctly")
        
        test("Serialization Settings", test_serialization_settings)
        
        # Print results
        print("\n" + "=" * 60)
        print(f"🏁 Test Results: {passed}/{total} passed")
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {total - passed} tests failed")
        print("=" * 60)
        
        # Cleanup - remove test registries
        try:
            RejSingleton.remove_registry("test_singleton")
            RejSingleton.remove_registry("test_global_info")
            RejSingleton.remove_registry("test_serialization")
            print("🧹 Cleaned up test registries")
        except Exception as e:
            print(f"🧹 Cleanup warning: {e}")
    
    # Run the tests
    run_tests()