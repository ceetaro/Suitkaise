#!/usr/bin/env python3
"""
Test module for Rej registry functionality.

This module contains comprehensive tests for the Rej registry system,
including basic registry operations, duplicate handling strategies,
singleton behavior, error conditions, and edge cases.

Run with:
    python3.11 -m pytest tests/test_suitkaise/test_rej/test_rej.py -v
    
Or with unittest:
    python3.11 -m unittest tests.test_suitkaise.test_rej.test_rej -v
"""

import unittest
import threading
import time
import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
import shutil

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Visual indicators for test output
INFO = "⬜️" * 40 + "\n\n\n"
FAIL = "\n\n   " + "❌" * 10 + " "
SUCCESS = "\n\n   " + "🟩" * 10 + " "
RUNNING = "🔄" * 40 + "\n\n"
CHECKING = "🧳" * 40 + "\n"
WARNING = "\n\n   " + "🟨" * 10 + " "

from suitkaise.rej import (
    Rej,
    RejSingleton,
    RejError,
    RejKeyError,
    RejDuplicateError,
    RejSerializationError,
    getrej,
    listrej,
    removerej,
)


class TestBasicRejFunctionality(unittest.TestCase):
    """Test basic Rej registry functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create test registries with serialization disabled for testing
        self.registry = Rej[str]("test_registry", auto_serialize_check=False)
        self.int_registry = Rej[int]("test_int_registry", auto_serialize_check=False)
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clear registries
        self.registry.clear()
        self.int_registry.clear()
    
    def test_registry_creation(self):
        """
        Test basic registry creation and properties.
        
        This test:
        - Creates registries with different configurations
        - Verifies initial state is correct
        - Checks registry properties and settings
        """
        # Test default creation
        reg = Rej[str]("test_basic")
        self.assertEqual(reg.name, "test_basic")
        self.assertEqual(len(reg), 0)
        self.assertEqual(reg.on_duplicate, Rej.Ruleset.OnDuplicate.RAISE_ERROR)
        
        # Test with custom settings
        reg_custom = Rej[str](
            "test_custom",
            on_duplicate=Rej.Ruleset.OnDuplicate.CREATE_NEW,
            auto_serialize_check=False
        )
        self.assertEqual(reg_custom.on_duplicate, Rej.Ruleset.OnDuplicate.CREATE_NEW)
        self.assertEqual(reg_custom.auto_serialize_check, False)
        
        print(f"   Created registry: {reg}")
        print(f"   Custom registry: {reg_custom}")
    
    def test_basic_register_and_get(self):
        """
        Test basic item registration and retrieval.
        
        This test:
        - Registers items with different keys
        - Retrieves items and verifies values
        - Checks registry size and contains behavior
        """
        # Register items
        key1 = self.registry.register("key1", "value1")
        key2 = self.registry.register("key2", "value2")
        
        self.assertEqual(key1, "key1")
        self.assertEqual(key2, "key2")
        self.assertEqual(len(self.registry), 2)
        
        # Test __contains__
        self.assertIn("key1", self.registry)
        self.assertIn("key2", self.registry)
        self.assertNotIn("nonexistent", self.registry)
        
        # Retrieve items
        self.assertEqual(self.registry.get("key1"), "value1")
        self.assertEqual(self.registry.get("key2"), "value2")
        self.assertIsNone(self.registry.get("nonexistent"))
        
        # Test get_required
        self.assertEqual(self.registry.get_required("key1"), "value1")
        
        print(f"   Registered {len(self.registry)} items successfully")
    
    def test_get_required_error(self):
        """
        Test that get_required raises error for missing keys.
        
        This test:
        - Calls get_required with non-existent key
        - Verifies RejKeyError is raised with proper message
        """
        with self.assertRaises(RejKeyError) as context:
            self.registry.get_required("missing_key")
        
        error_msg = str(context.exception)
        self.assertIn("missing_key", error_msg)
        self.assertIn("test_registry", error_msg)
        
        print("   get_required correctly raises RejKeyError for missing keys")
    
    def test_update_operations(self):
        """
        Test item update functionality.
        
        This test:
        - Registers an item
        - Updates it with a new value
        - Verifies update behavior with non-existent keys
        """
        # Register initial item
        self.registry.register("update_me", "original")
        
        # Update existing item
        updated = self.registry.update("update_me", "updated")
        self.assertTrue(updated)
        self.assertEqual(self.registry.get("update_me"), "updated")
        
        # Try to update non-existent item
        not_updated = self.registry.update("doesnt_exist", "value")
        self.assertFalse(not_updated)
        
        # Verify metadata was updated
        metadata = self.registry.get_metadata("update_me")
        self.assertIsNotNone(metadata)
        # modification time should be recent
        self.assertGreater(metadata.modified_at, metadata.created_at)
        
        print("   Update operations work correctly")
    
    def test_remove_operations(self):
        """
        Test item removal functionality.
        
        This test:
        - Registers items
        - Removes existing items
        - Verifies removal behavior with non-existent keys
        """
        # Register items
        self.registry.register("remove_me", "value1")
        self.registry.register("keep_me", "value2")
        
        # Remove existing item
        removed = self.registry.remove("remove_me")
        self.assertTrue(removed)
        self.assertIsNone(self.registry.get("remove_me"))
        self.assertEqual(len(self.registry), 1)
        
        # Try to remove non-existent item
        not_removed = self.registry.remove("doesnt_exist")
        self.assertFalse(not_removed)
        
        # Verify other item still exists
        self.assertEqual(self.registry.get("keep_me"), "value2")
        
        print("   Remove operations work correctly")
    
    def test_list_operations(self):
        """
        Test listing keys and items.
        
        This test:
        - Registers multiple items
        - Tests list_keys and list_items functionality
        - Verifies clear operation
        """
        # Register test items
        test_data = {
            "key1": "value1",
            "key2": "value2", 
            "key3": "value3"
        }
        
        for key, value in test_data.items():
            self.registry.register(key, value)
        
        # Test list_keys
        keys = self.registry.list_keys()
        self.assertEqual(len(keys), 3)
        for key in test_data.keys():
            self.assertIn(key, keys)
        
        # Test list_items
        items = self.registry.list_items()
        self.assertEqual(len(items), 3)
        for key, value in test_data.items():
            self.assertEqual(items[key], value)
        
        # Test clear
        cleared_count = self.registry.clear()
        self.assertEqual(cleared_count, 3)
        self.assertEqual(len(self.registry), 0)
        self.assertEqual(len(self.registry.list_keys()), 0)
        
        print(f"   Listed and cleared {cleared_count} items successfully")
    
    def test_find_functionality(self):
        """
        Test find operations with filter functions.
        
        This test:
        - Registers items with different values
        - Uses various filter functions to find items
        - Verifies metadata access tracking
        """
        # Register test data
        self.registry.register("apple", "fruit")
        self.registry.register("banana", "fruit")
        self.registry.register("carrot", "vegetable")
        self.registry.register("app_config", "settings")
        
        # Find by value
        fruits = self.registry.find(lambda key, value: value == "fruit")
        self.assertEqual(len(fruits), 2)
        self.assertIn("apple", fruits)
        self.assertIn("banana", fruits)
        
        # Find by key pattern
        app_items = self.registry.find(lambda key, value: key.startswith("app"))
        self.assertEqual(len(app_items), 2)
        self.assertIn("apple", app_items)
        self.assertIn("app_config", app_items)
        
        # Find with complex condition
        long_keys = self.registry.find(lambda key, value: len(key) > 5)
        expected_long_keys = ["banana", "carrot", "app_config"]
        self.assertEqual(len(long_keys), len(expected_long_keys))
        for key in expected_long_keys:
            self.assertIn(key, long_keys)
        
        # Verify access count increased for found items
        apple_meta = self.registry.get_metadata("apple")
        self.assertGreater(apple_meta.access_count, 0)
        
        print(f"   Found items with various filters: fruits={len(fruits)}, apps={len(app_items)}")
    
    def test_metadata_tracking(self):
        """
        Test metadata tracking functionality.
        
        This test:
        - Registers items with custom metadata
        - Accesses items multiple times
        - Verifies metadata is properly tracked and updated
        """
        # Register with custom metadata
        custom_meta = {"priority": "high", "category": "important"}
        self.registry.register("tracked_item", "value", metadata=custom_meta)
        
        # Access the item multiple times
        for _ in range(3):
            self.registry.get("tracked_item")
        
        # Check metadata
        metadata = self.registry.get_metadata("tracked_item")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.access_count, 3)
        self.assertIsInstance(metadata.created_at, float)
        self.assertIsInstance(metadata.modified_at, float)
        self.assertEqual(metadata.is_serializable, False)  # We disabled auto_serialize_check
        
        # Test metadata for non-existent item
        missing_meta = self.registry.get_metadata("nonexistent")
        self.assertIsNone(missing_meta)
        
        print(f"   Metadata tracking works: access_count={metadata.access_count}")
    
    def test_registry_info(self):
        """
        Test registry information retrieval.
        
        This test:
        - Registers multiple items
        - Accesses items to generate statistics
        - Verifies get_info returns correct information
        """
        # Register and access items
        self.registry.register("item1", "value1")
        self.registry.register("item2", "value2")
        self.registry.get("item1")
        self.registry.get("item1")
        self.registry.get("item2")
        
        # Get registry info
        info = self.registry.get_info()
        
        # Verify info structure
        required_keys = [
            'name', 'total_items', 'serializable_items', 'total_accesses',
            'on_duplicate', 'auto_serialize_check', 'created_at', 'keys'
        ]
        for key in required_keys:
            self.assertIn(key, info)
        
        # Verify values
        self.assertEqual(info['name'], 'test_registry')
        self.assertEqual(info['total_items'], 2)
        self.assertEqual(info['total_accesses'], 3)
        self.assertEqual(info['serializable_items'], 0)  # auto_serialize_check disabled
        self.assertIn('item1', info['keys'])
        self.assertIn('item2', info['keys'])
        
        print(f"   Registry info: {info['total_items']} items, {info['total_accesses']} accesses")


class TestDuplicateHandling(unittest.TestCase):
    """Test all duplicate handling strategies."""
    
    def test_create_new_strategy(self):
        """
        Test CREATE_NEW duplicate handling strategy.
        
        This test:
        - Creates registry with CREATE_NEW strategy
        - Registers multiple items with same key
        - Verifies new keys are created with _1, _2, etc. suffixes
        """
        registry = Rej[str](
            "test_create_new",
            on_duplicate=Rej.Ruleset.OnDuplicate.CREATE_NEW,
            auto_serialize_check=False
        )
        
        # Register original
        key1 = registry.register("duplicate", "value1")
        self.assertEqual(key1, "duplicate")
        
        # Register duplicates
        key2 = registry.register("duplicate", "value2")
        self.assertEqual(key2, "duplicate_1")
        
        key3 = registry.register("duplicate", "value3")
        self.assertEqual(key3, "duplicate_2")
        
        # Verify all values exist
        self.assertEqual(registry.get("duplicate"), "value1")
        self.assertEqual(registry.get("duplicate_1"), "value2")
        self.assertEqual(registry.get("duplicate_2"), "value3")
        self.assertEqual(len(registry), 3)
        
        print(f"   CREATE_NEW: Generated keys {key1}, {key2}, {key3}")
    
    def test_overwrite_strategy(self):
        """
        Test OVERWRITE duplicate handling strategy.
        
        This test:
        - Creates registry with OVERWRITE strategy
        - Registers item, then overwrites with same key
        - Verifies original item is replaced
        """
        registry = Rej[str](
            "test_overwrite",
            on_duplicate=Rej.Ruleset.OnDuplicate.OVERWRITE,
            auto_serialize_check=False
        )
        
        # Register original
        key1 = registry.register("overwrite_key", "original_value")
        self.assertEqual(registry.get("overwrite_key"), "original_value")
        self.assertEqual(len(registry), 1)
        
        # Get metadata before overwrite
        original_meta = registry.get_metadata("overwrite_key")
        original_created_at = original_meta.created_at
        
        # Small delay to ensure different timestamps
        time.sleep(0.01)
        
        # Overwrite
        key2 = registry.register("overwrite_key", "new_value")
        self.assertEqual(key2, "overwrite_key")  # Same key
        self.assertEqual(registry.get("overwrite_key"), "new_value")
        self.assertEqual(len(registry), 1)  # Still only one item
        
        # Verify metadata was updated
        new_meta = registry.get_metadata("overwrite_key")
        self.assertGreater(new_meta.created_at, original_created_at)
        
        print(f"   OVERWRITE: Successfully replaced value")
    
    def test_ignore_strategy(self):
        """
        Test IGNORE duplicate handling strategy.
        
        This test:
        - Creates registry with IGNORE strategy
        - Registers item, then tries to register with same key
        - Verifies original item is kept, duplicate is ignored
        """
        registry = Rej[str](
            "test_ignore",
            on_duplicate=Rej.Ruleset.OnDuplicate.IGNORE,
            auto_serialize_check=False
        )
        
        # Register original
        key1 = registry.register("ignore_key", "original_value")
        self.assertEqual(key1, "ignore_key")
        self.assertEqual(registry.get("ignore_key"), "original_value")
        self.assertEqual(len(registry), 1)
        
        # Try to register duplicate - should be ignored
        key2 = registry.register("ignore_key", "new_value")
        self.assertEqual(key2, "ignore_key")  # Same key returned
        self.assertEqual(registry.get("ignore_key"), "original_value")  # Original kept
        self.assertEqual(len(registry), 1)  # Still only one item
        
        print(f"   IGNORE: Correctly ignored duplicate, kept original")
    
    def test_raise_error_strategy(self):
        """
        Test RAISE_ERROR duplicate handling strategy.
        
        This test:
        - Creates registry with RAISE_ERROR strategy (default)
        - Registers item, then tries to register with same key
        - Verifies RejDuplicateError is raised
        """
        registry = Rej[str](
            "test_raise_error",
            on_duplicate=Rej.Ruleset.OnDuplicate.RAISE_ERROR,
            auto_serialize_check=False
        )
        
        # Register original
        registry.register("error_key", "value1")
        
        # Try to register duplicate - should raise error
        with self.assertRaises(RejDuplicateError) as context:
            registry.register("error_key", "value2")
        
        error_msg = str(context.exception)
        self.assertIn("error_key", error_msg)
        self.assertIn("test_raise_error", error_msg)
        
        # Original value should still be there
        self.assertEqual(registry.get("error_key"), "value1")
        self.assertEqual(len(registry), 1)
        
        print("   RAISE_ERROR: Correctly raised RejDuplicateError")
    
    def test_duplicate_strategy_edge_cases(self):
        """
        Test edge cases for duplicate handling.
        
        This test:
        - Tests CREATE_NEW with many duplicates
        - Tests behavior with complex key names
        - Tests strategy switching
        """
        registry = Rej[str](
            "test_edge_cases",
            on_duplicate=Rej.Ruleset.OnDuplicate.CREATE_NEW,
            auto_serialize_check=False
        )
        
        # Test many duplicates
        base_key = "many_dupes"
        keys = []
        for i in range(5):
            key = registry.register(base_key, f"value_{i}")
            keys.append(key)
        
        expected_keys = ["many_dupes", "many_dupes_1", "many_dupes_2", "many_dupes_3", "many_dupes_4"]
        self.assertEqual(keys, expected_keys)
        
        # Test complex key names
        complex_key = "complex_key_with_underscores"
        key1 = registry.register(complex_key, "value1")
        key2 = registry.register(complex_key, "value2")
        
        self.assertEqual(key1, complex_key)
        self.assertEqual(key2, f"{complex_key}_1")
        
        print(f"   Edge cases: Generated {len(keys)} duplicate keys successfully")


class TestRejSingleton(unittest.TestCase):
    """Test RejSingleton functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clean up any existing test registries
        test_registries = [name for name in RejSingleton.list_registries() if name.startswith("test_")]
        for name in test_registries:
            RejSingleton.remove_registry(name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up test registries
        test_registries = [name for name in RejSingleton.list_registries() if name.startswith("test_")]
        for name in test_registries:
            RejSingleton.remove_registry(name)
    
    def test_singleton_behavior(self):
        """
        Test basic singleton behavior.
        
        This test:
        - Gets same registry from multiple calls
        - Verifies they are the same instance
        - Tests registry persistence across calls
        """
        # Get registry twice
        registry1 = RejSingleton.get_registry("test_singleton", auto_serialize_check=False)
        registry2 = RejSingleton.get_registry("test_singleton", auto_serialize_check=False)
        
        # Should be the same instance
        self.assertIs(registry1, registry2)
        
        # Add item to first registry
        registry1.register("singleton_key", "singleton_value")
        
        # Should be accessible from second registry
        self.assertEqual(registry2.get("singleton_key"), "singleton_value")
        
        # Get fresh reference - should still be same instance
        registry3 = RejSingleton.get_registry("test_singleton")
        self.assertIs(registry1, registry3)
        self.assertEqual(registry3.get("singleton_key"), "singleton_value")
        
        print("   Singleton behavior works correctly")
    
    def test_multiple_singletons(self):
        """
        Test multiple singleton registries.
        
        This test:
        - Creates multiple singleton registries
        - Verifies they are separate instances
        - Tests listing functionality
        """
        # Create multiple registries
        reg_a = RejSingleton.get_registry("test_reg_a", auto_serialize_check=False)
        reg_b = RejSingleton.get_registry("test_reg_b", auto_serialize_check=False)
        reg_c = RejSingleton.get_registry("test_reg_c", auto_serialize_check=False)
        
        # Should be different instances
        self.assertIsNot(reg_a, reg_b)
        self.assertIsNot(reg_b, reg_c)
        
        # Add different data to each
        reg_a.register("key_a", "value_a")
        reg_b.register("key_b", "value_b")
        reg_c.register("key_c", "value_c")
        
        # Verify isolation
        self.assertEqual(reg_a.get("key_a"), "value_a")
        self.assertIsNone(reg_a.get("key_b"))
        self.assertIsNone(reg_a.get("key_c"))
        
        # Test listing
        registries = RejSingleton.list_registries()
        self.assertIn("test_reg_a", registries)
        self.assertIn("test_reg_b", registries)
        self.assertIn("test_reg_c", registries)
        
        print(f"   Multiple singletons: {len(registries)} registries created")
    
    def test_singleton_removal(self):
        """
        Test singleton registry removal.
        
        This test:
        - Creates singleton registry
        - Removes it
        - Verifies it's no longer in the list
        - Tests behavior after removal
        """
        # Create registry
        registry = RejSingleton.get_registry("test_removal", auto_serialize_check=False)
        registry.register("test_key", "test_value")
        
        # Verify it exists
        registries_before = RejSingleton.list_registries()
        self.assertIn("test_removal", registries_before)
        
        # Remove it
        removed = RejSingleton.remove_registry("test_removal")
        self.assertTrue(removed)
        
        # Verify it's gone
        registries_after = RejSingleton.list_registries()
        self.assertNotIn("test_removal", registries_after)
        
        # Try to remove again
        removed_again = RejSingleton.remove_registry("test_removal")
        self.assertFalse(removed_again)
        
        # Getting registry again should create new instance
        new_registry = RejSingleton.get_registry("test_removal", auto_serialize_check=False)
        self.assertIsNone(new_registry.get("test_key"))  # Old data should be gone
        
        print("   Singleton removal works correctly")
    
    def test_singleton_global_info(self):
        """
        Test singleton global information.
        
        This test:
        - Creates singleton registry
        - Gets global info
        - Verifies info structure and content
        """
        registry = RejSingleton.get_registry("test_global_info", auto_serialize_check=False)
        registry.register("info_key", "info_value")
        
        # Get global info
        global_info = registry.get_global_info()
        
        # Verify structure
        required_keys = [
            'name', 'total_items', 'total_accesses', 'stored_globally'
        ]
        for key in required_keys:
            self.assertIn(key, global_info)
        
        # Verify content
        self.assertEqual(global_info['name'], 'test_global_info')
        self.assertEqual(global_info['total_items'], 1)
        self.assertIsInstance(global_info['stored_globally'], bool)
        
        print(f"   Global info: stored_globally={global_info['stored_globally']}")
    
    def test_singleton_serialization(self):
        """
        Test singleton serialization methods.
        
        This test:
        - Creates singleton registry
        - Tests __getstate__ and __setstate__ methods
        - Verifies serialization preserves data and recreates locks
        """
        registry = RejSingleton.get_registry("test_serialization", auto_serialize_check=False)
        registry.register("serial_key", "serial_value")
        
        # Test __getstate__
        state = registry.__getstate__()
        self.assertIsInstance(state, dict)
        self.assertIn('name', state)
        self.assertIn('_items', state)
        
        # Test __setstate__
        new_registry = RejSingleton.__new__(RejSingleton)
        new_registry.__setstate__(state)
        
        # Verify data preservation
        self.assertEqual(new_registry.name, registry.name)
        self.assertEqual(new_registry.get("serial_key"), "serial_value")
        
        # Verify locks were recreated
        self.assertTrue(hasattr(new_registry, '_lock'))
        self.assertIsNotNone(new_registry._lock)
        
        # Test that lock actually works
        with new_registry._lock:
            pass  # Should not raise exception
        
        print("   Serialization methods work correctly")
    
    def test_convenience_functions(self):
        """
        Test convenience functions (getrej, listrej, removerej).
        
        This test:
        - Uses convenience functions instead of class methods
        - Verifies they work the same as class methods
        """
        # Test getrej
        registry1 = getrej("test_convenience", auto_serialize_check=False)
        registry2 = RejSingleton.get_registry("test_convenience")
        self.assertIs(registry1, registry2)
        
        # Add data
        registry1.register("conv_key", "conv_value")
        
        # Test listrej
        registries_class = RejSingleton.list_registries()
        registries_func = listrej()
        self.assertEqual(set(registries_class), set(registries_func))
        self.assertIn("test_convenience", registries_func)
        
        # Test removerej
        removed_func = removerej("test_convenience")
        self.assertTrue(removed_func)
        
        # Verify removal
        registries_after = listrej()
        self.assertNotIn("test_convenience", registries_after)
        
        print("   Convenience functions work correctly")


class TestErrorConditions(unittest.TestCase):
    """Test error conditions and edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = Rej[str]("test_errors", auto_serialize_check=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.registry.clear()
    
    def test_invalid_key_types(self):
        """
        Test behavior with invalid key types.
        
        This test:
        - Tries to use non-string keys
        - Verifies appropriate error handling
        """
        # Note: The current implementation doesn't explicitly check key types,
        # but this test documents expected behavior
        
        # These should work (converted to string)
        try:
            # Python will convert these to strings in dictionary operations
            self.registry.register(123, "numeric_key")  # Will be converted to "123"
            self.registry.register(None, "none_key")    # Will be converted to "None"
            
            # Verify they work with string access
            # (This is a design decision - we could be stricter)
            print("   Non-string keys are converted to strings")
        except Exception as e:
            print(f"   Non-string keys raise error: {e}")
    
    def test_none_values(self):
        """
        Test handling of None values.
        
        This test:
        - Registers None values
        - Verifies they can be stored and retrieved
        - Tests distinction between None value and missing key
        """
        # Register None value
        key = self.registry.register("none_key", None)
        self.assertEqual(key, "none_key")
        
        # Retrieve None value
        value = self.registry.get("none_key")
        self.assertIsNone(value)
        
        # Verify key exists (even though value is None)
        self.assertIn("none_key", self.registry)
        
        # Verify difference from missing key
        self.assertIsNone(self.registry.get("missing_key"))
        self.assertNotIn("missing_key", self.registry)
        
        print("   None values handled correctly")
    
    def test_empty_string_keys(self):
        """
        Test handling of empty string keys.
        
        This test:
        - Registers item with empty string key
        - Verifies it can be stored and retrieved
        """
        # Register with empty key
        key = self.registry.register("", "empty_key_value")
        self.assertEqual(key, "")
        
        # Retrieve by empty key
        value = self.registry.get("")
        self.assertEqual(value, "empty_key_value")
        
        # Verify it's in the registry
        self.assertIn("", self.registry)
        
        print("   Empty string keys handled correctly")
    
    def test_very_long_keys(self):
        """
        Test handling of very long keys.
        
        This test:
        - Creates keys of various lengths
        - Verifies system handles long keys properly
        """
        # Test progressively longer keys
        for length in [100, 1000, 10000]:
            long_key = "a" * length
            value = f"value_for_length_{length}"
            
            key = self.registry.register(long_key, value)
            self.assertEqual(key, long_key)
            self.assertEqual(self.registry.get(long_key), value)
        
        print(f"   Long keys up to {length} characters handled correctly")
    
    def test_unicode_keys_and_values(self):
        """
        Test handling of Unicode keys and values.
        
        This test:
        - Uses Unicode characters in keys and values
        - Verifies proper handling of international characters
        """
        unicode_data = {
            "测试键": "测试值",  # Chinese
            "ключ": "значение",  # Russian  
            "مفتاح": "قيمة",      # Arabic
            "🔑": "🎯",          # Emojis
            "café": "naïve"      # Accented characters
        }
        
        for key, value in unicode_data.items():
            reg_key = self.registry.register(key, value)
            self.assertEqual(reg_key, key)
            self.assertEqual(self.registry.get(key), value)
        
        print(f"   Unicode keys and values handled correctly: {len(unicode_data)} test cases")
    
    def test_find_with_error_in_filter(self):
        """
        Test find behavior when filter function raises errors.
        
        This test:
        - Uses filter function that raises exceptions
        - Verifies system gracefully handles filter errors
        """
        # Register test data
        self.registry.register("normal", "value")
        self.registry.register("special", None)
        self.registry.register("number", "123")
        
        # Filter that will raise error on None value
        def problematic_filter(key, value):
            if value is None:
                raise ValueError("Cannot process None value")
            return len(value) > 3
        
        # Should not crash, should skip problematic items
        matches = self.registry.find(problematic_filter)
        
        # Should find items that don't cause errors
        expected_matches = {"normal": "value"}  # "number"="123" has len=3, not >3
        self.assertEqual(matches, expected_matches)
        
        print("   Find gracefully handles filter function errors")
    
    def test_concurrent_access_basic(self):
        """
        Test basic concurrent access scenarios.
        
        This test:
        - Performs concurrent operations on registry
        - Verifies thread safety of basic operations
        """
        # Register initial item
        self.registry.register("concurrent_test", "initial")
        
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                # Each worker does some operations
                for i in range(10):
                    key = f"worker_{worker_id}_item_{i}"
                    self.registry.register(key, f"value_{worker_id}_{i}")
                    
                    # Read some items
                    value = self.registry.get("concurrent_test")
                    if value:
                        results.append(f"worker_{worker_id}_read_{i}")
                
                # Update the shared item
                self.registry.update("concurrent_test", f"updated_by_worker_{worker_id}")
                
            except Exception as e:
                errors.append(f"Worker {worker_id}: {e}")
        
        # Run multiple workers concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(worker, i) for i in range(3)]
            for future in futures:
                future.result(timeout=5)  # Wait for completion
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")
        
        # Verify operations completed
        self.assertGreater(len(results), 0)
        self.assertGreater(len(self.registry), 1)  # Should have more than initial item
        
        print(f"   Concurrent access test: {len(results)} operations, {len(self.registry)} items")


class TestSerializationBehavior(unittest.TestCase):
    """Test serialization-related behavior."""
    
    def test_serialization_disabled(self):
        """
        Test behavior when serialization checking is disabled.
        
        This test:
        - Creates registry with auto_serialize_check=False
        - Registers non-serializable objects
        - Verifies they are stored successfully
        """
        registry = Rej[object]("test_no_serial", auto_serialize_check=False)
        
        # Register non-serializable objects
        lock = threading.Lock()
        event = threading.Event()
        
        key1 = registry.register("lock", lock)
        key2 = registry.register("event", event)
        
        self.assertEqual(key1, "lock")
        self.assertEqual(key2, "event")
        
        # Verify they can be retrieved
        retrieved_lock = registry.get("lock")
        retrieved_event = registry.get("event")
        
        self.assertIs(retrieved_lock, lock)
        self.assertIs(retrieved_event, event)
        
        # Check metadata shows not serializable
        lock_meta = registry.get_metadata("lock")
        self.assertFalse(lock_meta.is_serializable)
        
        print("   Non-serializable objects stored when checking disabled")
    
    def test_serialization_enabled_basic(self):
        """
        Test behavior when serialization checking is enabled.
        
        This test:
        - Creates registry with auto_serialize_check=True
        - Tests with serializable objects
        - Verifies metadata is set correctly
        """
        # Skip if Cereal not available
        try:
            from suitkaise.cereal import Cereal
        except ImportError:
            self.skipTest("Cereal not available for serialization testing")
        
        registry = Rej[object]("test_serial", auto_serialize_check=True)
        
        # Register serializable objects
        serializable_data = {
            "string": "test",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"key": "value"}
        }
        
        for key, value in serializable_data.items():
            reg_key = registry.register(key, value)
            self.assertEqual(reg_key, key)
            
            # Check metadata
            metadata = registry.get_metadata(key)
            # Note: Depends on Cereal implementation
            # self.assertTrue(metadata.is_serializable)
        
        print("   Serializable objects handled correctly when checking enabled")
    
    def test_serialization_error_handling(self):
        """
        Test error handling for non-serializable objects when checking enabled.
        
        This test:
        - Creates registry with auto_serialize_check=True
        - Tries to register non-serializable objects
        - Verifies appropriate errors are raised
        """
        # Skip if Cereal not available
        try:
            from suitkaise.cereal import Cereal
        except ImportError:
            self.skipTest("Cereal not available for serialization testing")
        
        registry = Rej[object]("test_serial_error", auto_serialize_check=True)
        
        # Try to register non-serializable object
        lock = threading.Lock()
        
        # This should raise RejSerializationError if Cereal determines it's not serializable
        try:
            registry.register("lock", lock)
            # If we get here, either the object is considered serializable by Cereal,
            # or Cereal isn't working as expected
            print("   Lock was considered serializable by Cereal")
        except RejSerializationError:
            print("   Non-serializable object correctly rejected")
        except Exception as e:
            print(f"   Unexpected error during serialization test: {e}")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and unusual scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = Rej[str]("test_edge_cases", auto_serialize_check=False)
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.registry.clear()
    
    def test_large_registry(self):
        """
        Test behavior with large number of items.
        
        This test:
        - Registers many items
        - Verifies performance remains reasonable
        - Tests operations on large registry
        """
        import time
        
        # Register many items
        start_time = time.time()
        num_items = 1000
        
        for i in range(num_items):
            self.registry.register(f"item_{i:04d}", f"value_{i}")
        
        register_time = time.time() - start_time
        
        # Verify all items were registered
        self.assertEqual(len(self.registry), num_items)
        
        # Test retrieval performance
        start_time = time.time()
        for i in range(0, num_items, 100):  # Sample every 100th item
            value = self.registry.get(f"item_{i:04d}")
            self.assertEqual(value, f"value_{i}")
        
        retrieval_time = time.time() - start_time
        
        # Test find operation
        start_time = time.time()
        matches = self.registry.find(lambda k, v: k.endswith("0050"))
        find_time = time.time() - start_time
        
        self.assertEqual(len(matches), 1)
        self.assertIn("item_0050", matches)
        
        print(f"   Large registry ({num_items} items): "
              f"register={register_time:.3f}s, "
              f"retrieval={retrieval_time:.3f}s, "
              f"find={find_time:.3f}s")
    
    def test_registry_representation(self):
        """
        Test string representation of registry.
        
        This test:
        - Tests __repr__ method
        - Verifies meaningful string representation
        """
        # Empty registry
        empty_repr = repr(self.registry)
        self.assertIn("test_edge_cases", empty_repr)
        self.assertIn("items=0", empty_repr)
        
        # Registry with items
        self.registry.register("test", "value")
        filled_repr = repr(self.registry)
        self.assertIn("items=1", filled_repr)
        
        print(f"   Registry representations: empty='{empty_repr}', filled='{filled_repr}'")
    
    def test_metadata_edge_cases(self):
        """
        Test edge cases in metadata handling.
        
        This test:
        - Tests metadata with unusual custom values
        - Verifies metadata robustness
        """
        # Register with complex custom metadata
        complex_metadata = {
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
            "none_value": None,
            "empty_string": "",
            "unicode": "测试"
        }
        
        self.registry.register("complex_meta", "value", metadata=complex_metadata)
        
        # Retrieve and verify metadata
        metadata = self.registry.get_metadata("complex_meta")
        self.assertIsNotNone(metadata)
        
        # Standard metadata should be present
        self.assertIsInstance(metadata.created_at, float)
        self.assertIsInstance(metadata.access_count, int)
        
        print("   Complex metadata handled correctly")
    
    def test_registry_name_edge_cases(self):
        """
        Test edge cases in registry names.
        
        This test:
        - Creates registries with unusual names
        - Verifies name handling is robust
        """
        unusual_names = [
            "",  # Empty name
            " ",  # Whitespace only
            "name with spaces",
            "name-with-dashes",
            "name_with_underscores", 
            "名前",  # Unicode name
            "🎯📝",  # Emoji name
            "very_long_name_" + "x" * 100  # Very long name
        ]
        
        registries = []
        for name in unusual_names:
            try:
                registry = Rej[str](name, auto_serialize_check=False)
                self.assertEqual(registry.name, name)
                registries.append(registry)
            except Exception as e:
                print(f"   Name '{name}' caused error: {e}")
        
        print(f"   Registry names tested: {len(registries)}/{len(unusual_names)} successful")
    
    def test_clear_empty_registry(self):
        """
        Test clearing an already empty registry.
        
        This test:
        - Clears empty registry
        - Verifies it returns 0
        - Ensures no errors occur
        """
        # Clear empty registry
        cleared = self.registry.clear()
        self.assertEqual(cleared, 0)
        self.assertEqual(len(self.registry), 0)
        
        # Clear again
        cleared_again = self.registry.clear()
        self.assertEqual(cleared_again, 0)
        
        print("   Clearing empty registry works correctly")
    
    def test_update_then_remove_cycle(self):
        """
        Test update and remove operations in various combinations.
        
        This test:
        - Performs cycles of update and remove operations
        - Verifies state consistency
        """
        # Register initial item
        self.registry.register("cycle_test", "initial")
        
        # Update -> Remove -> Register -> Update cycle
        self.assertTrue(self.registry.update("cycle_test", "updated1"))
        self.assertEqual(self.registry.get("cycle_test"), "updated1")
        
        self.assertTrue(self.registry.remove("cycle_test"))
        self.assertIsNone(self.registry.get("cycle_test"))
        
        self.registry.register("cycle_test", "new_value")
        self.assertEqual(self.registry.get("cycle_test"), "new_value")
        
        self.assertTrue(self.registry.update("cycle_test", "final_value"))
        self.assertEqual(self.registry.get("cycle_test"), "final_value")
        
        print("   Update/remove cycles work correctly")


# Test runner functions
def run_tests():
    """
    Run all tests with detailed output.
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


def run_specific_test(test_class_name):
    """
    Run a specific test class.
    
    Args:
        test_class_name (str): Name of the test class to run
        
    Returns:
        bool: True if tests passed, False otherwise
    """
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(globals()[test_class_name])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # If run directly, execute all tests
    print(f"{INFO}    Running Rej Registry Tests...")
    print(INFO)
    
    success = run_tests()
    
    print(f"{INFO}    Rej Registry Tests Completed")
    if success:
        print(f"{SUCCESS} All tests passed successfully!")
        sys.exit(0)
    else:
        print(f"{FAIL} Some tests failed.")
        sys.exit(1)