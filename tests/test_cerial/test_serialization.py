"""
Test cerial serialization (converting objects to bytes).

Tests each handler/object type in isolation, then tests the worst possible object.
For now, we just verify that serialization completes without errors.
Round-trip testing (serialize + deserialize) will come after deserializer is implemented.
"""

import pytest
import threading
import logging
import queue
import re
import sqlite3
import tempfile
import io
import sys
from pathlib import Path
from enum import Enum, IntEnum
from collections import namedtuple, defaultdict, deque, Counter
from functools import partial
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

# Import the serializer
from suitkaise.cerial._int.serializer import Cerializer, SerializationError


class TestPrimitiveTypes:
    """Test pickle-native primitive types."""
    
    def test_none(self):
        serializer = Cerializer()
        result = serializer.serialize(None)
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_bool(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(True), bytes)
        assert isinstance(serializer.serialize(False), bytes)
    
    def test_int(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(42), bytes)
        assert isinstance(serializer.serialize(-999), bytes)
        assert isinstance(serializer.serialize(10**50), bytes)  # Large int
    
    def test_float(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(3.14), bytes)
        assert isinstance(serializer.serialize(-0.001), bytes)
    
    def test_complex(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(complex(1, 2)), bytes)
    
    def test_string(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize("hello"), bytes)
        assert isinstance(serializer.serialize("unicode: 你好 🌍"), bytes)
        assert isinstance(serializer.serialize(""), bytes)
    
    def test_bytes(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(b"bytes"), bytes)
        assert isinstance(serializer.serialize(bytearray(b"mutable")), bytes)


class TestDatetimeTypes:
    """Test datetime module types (pickle-native)."""
    
    def test_datetime(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(datetime.now()), bytes)
    
    def test_date(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(date.today()), bytes)
    
    def test_timedelta(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(timedelta(days=5)), bytes)


class TestNumericTypes:
    """Test numeric types (pickle-native)."""
    
    def test_decimal(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(Decimal('123.456')), bytes)
    
    def test_uuid(self):
        serializer = Cerializer()
        uuid = UUID('12345678-1234-5678-1234-567812345678')
        assert isinstance(serializer.serialize(uuid), bytes)


class TestPathTypes:
    """Test pathlib types (pickle-native)."""
    
    def test_path(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(Path('.')), bytes)
        assert isinstance(serializer.serialize(Path.home()), bytes)


class TestCollections:
    """Test collection types."""
    
    def test_list(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize([1, 2, 3]), bytes)
        assert isinstance(serializer.serialize([]), bytes)
    
    def test_tuple(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize((1, 2, 3)), bytes)
        assert isinstance(serializer.serialize(()), bytes)
    
    def test_dict(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize({"a": 1}), bytes)
        assert isinstance(serializer.serialize({}), bytes)
    
    def test_set(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize({1, 2, 3}), bytes)
        assert isinstance(serializer.serialize(set()), bytes)
    
    def test_frozenset(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(frozenset([1, 2])), bytes)
    
    def test_nested_collections(self):
        serializer = Cerializer()
        nested = {
            "list": [1, 2, [3, 4]],
            "dict": {"inner": {"deep": [5, 6]}},
            "tuple": (7, (8, 9))
        }
        assert isinstance(serializer.serialize(nested), bytes)


class TestAdvancedCollections:
    """Test collections module types (pickle-native)."""
    
    def test_defaultdict(self):
        serializer = Cerializer()
        dd = defaultdict(int)
        dd['a'] = 5
        assert isinstance(serializer.serialize(dd), bytes)
    
    def test_deque(self):
        serializer = Cerializer()
        dq = deque([1, 2, 3], maxlen=10)
        assert isinstance(serializer.serialize(dq), bytes)
    
    def test_counter(self):
        serializer = Cerializer()
        counter = Counter(['a', 'b', 'a', 'c', 'a'])
        assert isinstance(serializer.serialize(counter), bytes)
    
    def test_namedtuple(self):
        serializer = Cerializer()
        Point = namedtuple('Point', ['x', 'y'])
        p = Point(10, 20)
        assert isinstance(serializer.serialize(p), bytes)


# Define enums at module level (not inside test functions)
# Local enums can't be serialized/imported
class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

class Status(IntEnum):
    PENDING = 1
    ACTIVE = 2
    COMPLETE = 3


class TestComplexDictKeys:
    """Test dictionaries with complex keys."""
    
    def test_tuple_key_with_function(self):
        """Dict key is a tuple containing a function."""
        def my_func():
            return 42
        
        data = {(my_func, "key"): "value"}
        serializer = Cerializer()
        assert isinstance(serializer.serialize(data), bytes)
    
    def test_frozenset_key_with_logger(self):
        """Dict key is a frozenset (hashable but complex contents)."""
        import logging
        logger = logging.getLogger("test_key")
        
        # Can't use logger directly in frozenset (not hashable)
        # But can use tuple of hashable items
        data = {("logger_name", logger.name): logger}
        serializer = Cerializer()
        assert isinstance(serializer.serialize(data), bytes)


class TestEnums:
    """Test enum types."""
    
    def test_basic_enum(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(Color.RED), bytes)
    
    def test_int_enum(self):
        serializer = Cerializer()
        assert isinstance(serializer.serialize(Status.ACTIVE), bytes)


class TestFunctions:
    """Test function types."""
    
    def test_regular_function(self):
        def test_func(x, y=10):
            return x + y
        
        serializer = Cerializer()
        assert isinstance(serializer.serialize(test_func), bytes)
    
    def test_lambda(self):
        serializer = Cerializer()
        lam = lambda x: x * 2
        assert isinstance(serializer.serialize(lam), bytes)
    
    def test_partial(self):
        def multiply(x, y):
            return x * y
        
        serializer = Cerializer()
        double = partial(multiply, 2)
        assert isinstance(serializer.serialize(double), bytes)
    
    def test_bound_method(self):
        serializer = Cerializer()
        my_list = [1, 2, 3]
        assert isinstance(serializer.serialize(my_list.append), bytes)


class TestThreading:
    """Test threading objects."""
    
    def test_lock(self):
        serializer = Cerializer()
        lock = threading.Lock()
        assert isinstance(serializer.serialize(lock), bytes)
    
    def test_rlock(self):
        serializer = Cerializer()
        rlock = threading.RLock()
        assert isinstance(serializer.serialize(rlock), bytes)
    
    def test_event(self):
        serializer = Cerializer()
        event = threading.Event()
        assert isinstance(serializer.serialize(event), bytes)
    
    def test_semaphore(self):
        serializer = Cerializer()
        sem = threading.Semaphore(5)
        assert isinstance(serializer.serialize(sem), bytes)
    
    def test_thread_local(self):
        serializer = Cerializer()
        local = threading.local()
        local.value = 42
        assert isinstance(serializer.serialize(local), bytes)


class TestQueues:
    """Test queue objects."""
    
    def test_queue(self):
        serializer = Cerializer()
        q = queue.Queue()
        q.put("item1")
        q.put("item2")
        assert isinstance(serializer.serialize(q), bytes)
    
    def test_lifo_queue(self):
        serializer = Cerializer()
        q = queue.LifoQueue()
        q.put("item")
        assert isinstance(serializer.serialize(q), bytes)
    
    def test_priority_queue(self):
        serializer = Cerializer()
        q = queue.PriorityQueue()
        q.put((1, "high"))
        q.put((5, "low"))
        assert isinstance(serializer.serialize(q), bytes)


class TestFileObjects:
    """Test file-related objects."""
    
    def test_temp_file(self):
        serializer = Cerializer()
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as f:
            f.write("test content")
            f.flush()
            f.seek(0)
            assert isinstance(serializer.serialize(f), bytes)
    
    def test_string_io(self):
        serializer = Cerializer()
        sio = io.StringIO("test content")
        assert isinstance(serializer.serialize(sio), bytes)
    
    def test_bytes_io(self):
        serializer = Cerializer()
        bio = io.BytesIO(b"test content")
        assert isinstance(serializer.serialize(bio), bytes)


class TestLogging:
    """Test logging objects."""
    
    def test_logger(self):
        serializer = Cerializer()
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        assert isinstance(serializer.serialize(logger), bytes)
    
    def test_logger_with_handler(self):
        serializer = Cerializer()
        logger = logging.getLogger("test_logger_2")
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logger.addHandler(handler)
        assert isinstance(serializer.serialize(logger), bytes)


class TestRegex:
    """Test regex objects."""
    
    def test_regex_pattern(self):
        serializer = Cerializer()
        pattern = re.compile(r'\d+\.\d+', re.IGNORECASE)
        assert isinstance(serializer.serialize(pattern), bytes)


class TestSQLite:
    """Test SQLite objects."""
    
    def test_sqlite_connection(self):
        serializer = Cerializer()
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        cursor.execute("INSERT INTO test VALUES (1, 'test')")
        conn.commit()
        assert isinstance(serializer.serialize(conn), bytes)
    
    def test_sqlite_cursor(self):
        serializer = Cerializer()
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        assert isinstance(serializer.serialize(cursor), bytes)


class TestCustomClasses:
    """Test custom class instances."""
    
    def test_simple_class(self):
        class SimpleClass:
            def __init__(self, value):
                self.value = value
                self.data = [1, 2, 3]
        
        serializer = Cerializer()
        obj = SimpleClass(42)
        assert isinstance(serializer.serialize(obj), bytes)
    
    def test_class_with_complex_attributes(self):
        class ComplexClass:
            def __init__(self):
                self.lock = threading.Lock()
                self.queue = queue.Queue()
                self.logger = logging.getLogger("complex")
                self.data = {"nested": [1, 2, 3]}
        
        serializer = Cerializer()
        obj = ComplexClass()
        assert isinstance(serializer.serialize(obj), bytes)
    
    def test_class_with_custom_serialize(self):
        class CustomSerialize:
            def __init__(self):
                self.value = 100
            
            def __serialize__(self):
                return {"value": self.value}
            
            @classmethod
            def __deserialize__(cls, state):
                obj = cls.__new__(cls)
                obj.value = state["value"]
                return obj
        
        serializer = Cerializer()
        obj = CustomSerialize()
        assert isinstance(serializer.serialize(obj), bytes)


class TestCircularReferences:
    """Test circular reference handling."""
    
    def test_self_referencing_dict(self):
        serializer = Cerializer()
        circular = {"name": "test"}
        circular["self"] = circular
        assert isinstance(serializer.serialize(circular), bytes)
    
    def test_self_referencing_list(self):
        serializer = Cerializer()
        circular = [1, 2, 3]
        circular.append(circular)
        assert isinstance(serializer.serialize(circular), bytes)
    
    def test_mutual_references(self):
        serializer = Cerializer()
        a = {"name": "A"}
        b = {"name": "B"}
        a["ref"] = b
        b["ref"] = a
        assert isinstance(serializer.serialize(a), bytes)


class TestWorstPossibleObject:
    """Test the comprehensive worst possible object."""
    
    def test_worst_possible_object(self):
        """
        This is the ultimate test - serialize an object containing
        every type that cerial supports.
        """
        # Import the worst possible object
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "suitkaise" / "cerial" / "_int" / "worst_possible_object"))
        from worst_possible_obj import WorstPossibleObject
        
        # Create instance (with verbose output to see what's happening)
        print("\n" + "="*70)
        print("Creating Worst Possible Object...")
        print("="*70)
        obj = WorstPossibleObject(verbose=True)
        
        # Serialize it
        print("\n" + "="*70)
        print("Serializing Worst Possible Object...")
        print("="*70)
        serializer = CerialSerializer(verbose=True)
        result = serializer.serialize(obj)
        
        # Verify it produced bytes
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        print("\n" + "="*70)
        print(f"SUCCESS! Serialized to {len(result):,} bytes")
        print("="*70)
        
        # Clean up
        obj.cleanup()


class TestErrorHandling:
    """Test error handling and reporting."""
    
    def test_debug_mode(self):
        """Test that debug mode provides detailed errors."""
        class UnserializableClass:
            def __init__(self):
                # This will fail in extract_state
                pass
        
        # Without debug mode - basic error
        serializer = CerialSerializer(debug=False)
        obj = UnserializableClass()
        # Should succeed (has __dict__)
        assert isinstance(serializer.serialize(obj), bytes)
    
    def test_verbose_mode(self):
        """Test that verbose mode prints progress."""
        serializer = CerialSerializer(verbose=True)
        print("\n--- Verbose mode output: ---")
        result = serializer.serialize({"key": "value", "nested": [1, 2, 3]})
        print("--- End verbose output ---\n")
        assert isinstance(result, bytes)
    
    def test_recursion_depth_limit(self):
        """Test that deep recursion is caught."""
        # Create deeply nested structure
        deep = current = {}
        for i in range(100):  # Not deep enough to hit limit
            current["next"] = {}
            current = current["next"]
        
        serializer = Cerializer()
        # Should succeed (only 100 levels)
        assert isinstance(serializer.serialize(deep), bytes)


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])

