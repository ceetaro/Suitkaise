"""
The Worst Possible Object - A comprehensive test for cerial's serialization capabilities.

This object represents the ultimate challenge: every difficult-to-serialize type
nested within complex data structures. If cerial can serialize and deserialize this,
it can handle anything.

Goal: serialize this object, deserialize it, and verify every field matches exactly.
"""

import logging
import threading
import multiprocessing
import queue
import re
import sqlite3
import weakref
from functools import partial
from pathlib import Path
import tempfile
from collections import defaultdict
from typing import Any, Dict, List
# TODO add sk object imports below


class WorstPossibleObject:
    """
    The nightmare scenario - an object containing every difficult type cerial handles.
    
    This tests:
    - All critical types (functions, loggers, partials, bound methods)
    - All very common types (file handles, locks, queues, db connections, events)
    - All common types (generators, regex, context managers, etc.)
    - Deep nesting
    - Circular references
    - Collection types
    - Suitkaise-specific objects
    """
    class NestedTestClass:
        
        def __init__(self):
            # ===== SIMPLE TYPES (baseline) =====
            self.simple_int = 42
            self.simple_float = 3.14159
            self.simple_str = "test string with unicode: 你好 🚀"
            self.simple_bool = True
            self.simple_none = None
            self.simple_bytes = b"binary data \x00\xff"
            
            # ===== FUNCTIONS (95% importance) =====
            self.lambda_func = lambda x: x * 2
            self.nested_func = self._create_nested_function()
            self.closure_func = self._create_closure()
            
            # ===== LOGGERS (90% importance) =====
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            
            # ===== PARTIAL FUNCTIONS (85% importance) =====
            def multiply(a, b, c):
                return a * b * c
            self.partial_func = partial(multiply, 10, 20)
            
            # ===== BOUND METHODS (80% importance) =====
            self.bound_method = self.instance_method
            
            # ===== FILE HANDLES (75% importance) =====
            self.temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False)
            self.temp_file.write("test data at position 0\n")
            self.temp_file.write("more data at position 24\n")
            self.temp_file.flush()
            self.temp_file.seek(10)  # Positioned at byte 10
            
            # ===== LOCKS (70% importance) =====
            self.lock = threading.Lock()
            self.rlock = threading.RLock()
            self.lock.acquire()  # Acquired state
            
            # ===== QUEUES (65% importance) =====
            self.thread_queue = queue.Queue()
            self.thread_queue.put("item1")
            self.thread_queue.put("item2")
            self.process_queue = multiprocessing.Queue()
            
            # ===== EVENT OBJECTS (50% importance) =====
            self.thread_event = threading.Event()
            self.thread_event.set()  # Set state
            self.process_event = multiprocessing.Event()
            
            # ===== GENERATORS (45% importance) =====
            self.generator = self._create_generator()
            next(self.generator)  # Advance state
            next(self.generator)
            
            # ===== REGEX PATTERNS (40% importance) =====
            self.regex_pattern = re.compile(r'(\w+)@(\w+)\.(\w+)', re.IGNORECASE)
            
            # ===== CONTEXT MANAGERS (40% importance) =====
            self.context_manager = self._create_context_manager()
            
            # ===== SQLITE CONNECTIONS (30% importance) =====
            self.db_conn = sqlite3.connect(':memory:')
            cursor = self.db_conn.cursor()
            cursor.execute('CREATE TABLE test (id INTEGER, value TEXT)')
            cursor.execute('INSERT INTO test VALUES (1, "data1")')
            cursor.execute('INSERT INTO test VALUES (2, "data2")')
            self.db_conn.commit()
            
            # ===== DECORATORS (25% importance) =====
            self.decorated_func = self._create_decorated_function()
            
            # ===== WEAK REFERENCES (20% importance) =====
            self.referenced_obj = {"data": "for weak reference"}
            self.weak_ref = weakref.ref(self.referenced_obj)
            
            # ===== SEMAPHORES/BARRIERS (12% importance) =====
            self.semaphore = threading.Semaphore(3)
            self.semaphore.acquire()
            self.barrier = threading.Barrier(2)
            self.bounded_semaphore = threading.BoundedSemaphore(5)
            self.condition = threading.Condition()
            
            # ===== COLLECTIONS =====
            self.list_data = [1, 2, 3, "four", 5.0, None, True]
            self.dict_data = {"key1": "value1", "nested": {"key2": "value2"}}
            self.set_data = {1, 2, 3, "four"}
            self.tuple_data = (1, 2, "three", 4.0)
            self.defaultdict_data = defaultdict(list)
            self.defaultdict_data['key1'].append("value1")
            
            # ===== NESTED COMPLEXITY =====
            # Level 1: Dict containing various types
            self.nested_level_1 = {
                "logger": logging.getLogger("nested.logger"),
                "lock": threading.Lock(),
                "func": lambda x: x + 1,
                "list": [1, 2, 3],
            }
            
            # Level 2: List of dicts with complex objects
            self.nested_level_2 = [
                {
                    "id": 1,
                    "queue": queue.Queue(),
                    "event": threading.Event(),
                    "regex": re.compile(r'\d+'),
                },
                {
                    "id": 2,
                    "partial": partial(sum, [1, 2, 3]),
                    "file": tempfile.NamedTemporaryFile(mode='w+', delete=False),
                }
            ]
            
            # Level 3: Object containing nested structures
            self.nested_level_3 = {
                "depth": 3,
                "contains": {
                    "more_nesting": [
                        {"lock": threading.RLock(), "data": [1, 2, 3]},
                        {"event": threading.Event(), "func": self.lambda_func},
                    ],
                    "logger": self.logger,
                    "semaphore": threading.Semaphore(2),
                }
            }
            
            # ===== CIRCULAR REFERENCES =====
            self.circular_dict = {"name": "circular"}
            self.circular_dict["self_ref"] = self.circular_dict
            self.circular_list = [1, 2, 3]
            self.circular_list.append(self.circular_list)
            
            # ===== SUITKAISE-SPECIFIC OBJECTS =====
            # These will be imported and added dynamically
            self.skpath_obj = None
            self.sktime_timer = None
            
            # Try to import and create suitkaise objects
            try:
                from suitkaise.skpath.api import SKPath
                self.skpath_obj = SKPath(".")
            except ImportError:
                pass
                
            try:
                from suitkaise.sktime.api import Timer
                self.sktime_timer = Timer()
                self.sktime_timer.start()
                import time
                time.sleep(0.1)
                self.sktime_timer.stop()
            except ImportError:
                pass
        
        def instance_method(self, x):
            """Method to test bound method serialization."""
            return x * self.simple_int
        
        def _create_nested_function(self):
            """Create a nested function for testing."""
            def outer(x):
                def inner(y):
                    return x + y
                return inner
            return outer(10)
        
        def _create_closure(self):
            """Create a closure with captured variables."""
            captured_value = 100
            def closure(x):
                return x + captured_value
            return closure
        
        def _create_generator(self):
            """Create a generator with state."""
            for i in range(10):
                yield i * 2
        
        def _create_context_manager(self):
            """Create a custom context manager."""
            class CustomContextManager:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
            return CustomContextManager()
        
        def _create_decorated_function(self):
            """Create a decorated function."""
            def decorator(func):
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs) * 2
                return wrapper
            
            @decorator
            def func(x):
                return x + 1
            
            return func
        
        def verify_equality(self, other: 'WorstPossibleObject') -> Dict[str, bool]:
            """
            Verify that a deserialized object matches the original.
            
            Returns a dict of field_name -> bool indicating if they match.
            """
            results = {}
            
            # Simple types - should match exactly
            results['simple_int'] = self.simple_int == other.simple_int
            results['simple_float'] = self.simple_float == other.simple_float
            results['simple_str'] = self.simple_str == other.simple_str
            results['simple_bool'] = self.simple_bool == other.simple_bool
            results['simple_none'] = self.simple_none == other.simple_none
            results['simple_bytes'] = self.simple_bytes == other.simple_bytes
            
            # Functions - test that they work the same
            results['lambda_func'] = self.lambda_func(5) == other.lambda_func(5)
            results['nested_func'] = self.nested_func(5) == other.nested_func(5)
            results['closure_func'] = self.closure_func(5) == other.closure_func(5)
            
            # Logger - check name and level
            results['logger'] = (self.logger.name == other.logger.name and 
                                self.logger.level == other.logger.level)
            
            # Partial - test that it works
            results['partial_func'] = self.partial_func(5) == other.partial_func(5)
            
            # Bound method - test that it works
            results['bound_method'] = self.bound_method(5) == other.bound_method(5)
            
            # File handle - check position
            results['temp_file'] = self.temp_file.tell() == other.temp_file.tell()
            
            # Locks - check type (can't check exact state easily)
            results['lock'] = type(self.lock) == type(other.lock)
            results['rlock'] = type(self.rlock) == type(other.rlock)
            
            # Queues - check type
            results['thread_queue'] = type(self.thread_queue) == type(other.thread_queue)
            results['process_queue'] = type(self.process_queue) == type(other.process_queue)
            
            # Events - check if set/clear state matches
            results['thread_event'] = self.thread_event.is_set() == other.thread_event.is_set()
            
            # Regex - test pattern matching
            test_string = "test@example.com"
            results['regex_pattern'] = (bool(self.regex_pattern.match(test_string)) == 
                                    bool(other.regex_pattern.match(test_string)))
            
            # Collections
            results['list_data'] = self.list_data == other.list_data
            results['dict_data'] = self.dict_data == other.dict_data
            results['set_data'] = self.set_data == other.set_data
            results['tuple_data'] = self.tuple_data == other.tuple_data
            
            # Suitkaise objects
            if self.skpath_obj and other.skpath_obj:
                results['skpath_obj'] = str(self.skpath_obj) == str(other.skpath_obj)
            if self.sktime_timer and other.sktime_timer:
                results['sktime_timer'] = type(self.sktime_timer) == type(other.sktime_timer)
            
            return results
        
        def cleanup(self):
            """Clean up resources."""
            if hasattr(self, 'temp_file') and self.temp_file:
                try:
                    self.temp_file.close()
                    Path(self.temp_file.name).unlink(missing_ok=True)
                except:
                    pass
            
            if hasattr(self, 'db_conn') and self.db_conn:
                try:
                    self.db_conn.close()
                except:
                    pass
            
            # Clean up nested temp files
            if hasattr(self, 'nested_level_2'):
                for item in self.nested_level_2:
                    if 'file' in item:
                        try:
                            item['file'].close()
                            Path(item['file'].name).unlink(missing_ok=True)
                        except:
                            pass
            
            # Release locks
            if hasattr(self, 'lock') and self.lock.locked():
                try:
                    self.lock.release()
                except:
                    pass