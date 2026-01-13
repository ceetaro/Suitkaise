"""
Test classes for Share tests.

These classes are defined in a separate module so they can be properly
serialized/deserialized by cerial across processes.

Classes defined in __main__ cannot be deserialized in subprocess because
the subprocess has a different __main__ module.
"""

import sys
import time
from typing import Any, Dict, List

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.sk import sk


@sk
class Counter:
    """Simple counter class for testing."""
    def __init__(self, initial: int = 0):
        self.value = initial
    
    def increment(self):
        self.value += 1
    
    def decrement(self):
        self.value -= 1
    
    def add(self, amount: int):
        self.value += amount
    
    def reset(self):
        self.value = 0


@sk
class DataStore:
    """Complex data store for testing."""
    def __init__(self):
        self.items: Dict[str, Any] = {}
        self.history: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def set(self, key: str, value: Any):
        self.items[key] = value
        self.history.append(f"set:{key}")
    
    def get(self, key: str) -> Any:
        self.history.append(f"get:{key}")
        return self.items.get(key)
    
    def delete(self, key: str):
        if key in self.items:
            del self.items[key]
            self.history.append(f"delete:{key}")
    
    def clear(self):
        self.items.clear()
        self.history.append("clear")
    
    # Aliases for test_share.py
    def add_item(self, item):
        """Alias for test_share compatibility."""
        key = str(len(self.items))
        self.set(key, item)
    
    def set_meta(self, key, value):
        """Alias for test_share compatibility."""
        self.metadata[key] = value


@sk
class NestedObject:
    """Object with nested structures for testing."""
    def __init__(self):
        self.level1 = {"a": 1, "b": 2}
        self.level2 = {"nested": {"deep": {"value": 42}}}
        self.lists = [[1, 2], [3, 4], [5, 6]]
        self.tuples = ((1, 2), (3, 4))
        self.mixed = {"list": [1, 2], "tuple": (3, 4), "nested": {"x": 10}}
        # Additional for test_share.py compatibility
        self.data = {
            'list': [1, 2, 3],
            'dict': {'a': 1, 'b': 2},
            'nested': {'deep': {'value': 42}}
        }
        self.counter = 0
    
    def modify_level1(self, key: str, value: Any):
        self.level1[key] = value
    
    def get_deep_value(self) -> int:
        return self.level2["nested"]["deep"]["value"]
    
    def set_deep_value(self, value: int):
        self.level2["nested"]["deep"]["value"] = value
    
    # Aliases for test_share.py
    def increment(self):
        self.counter += 1
    
    def add_to_list(self, item):
        self.data['list'].append(item)
    
    def set_nested(self, key, value):
        self.data['nested'][key] = value


@sk
class SlowWorker:
    """Worker with blocking operations for async testing."""
    def __init__(self):
        self.result = None
        self.work_done = 0
    
    def do_work(self, duration: float = 0.01):
        time.sleep(duration)
        self.work_done += 1
        self.result = f"completed_{self.work_done}"
        return self.result
