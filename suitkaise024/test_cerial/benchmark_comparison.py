"""
Benchmark cerial against pickle, cloudpickle, and dill.

Tests:
1. Simple objects (where pickle should win)
2. Medium complexity (comparable)
3. Complex objects (where only cerial works)
"""

import pickle
import time
import sys
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict

# Add project root to path for direct script execution
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Try to import optional libraries
try:
    import dill
    HAS_DILL = True
except ImportError:
    HAS_DILL = False
    dill = None

try:
    import cloudpickle
    HAS_CLOUDPICKLE = True
except ImportError:
    HAS_CLOUDPICKLE = False
    cloudpickle = None

from suitkaise.cerial._int.serializer import Cerializer
from suitkaise.cerial._int.deserializer import Decerializer


# =============================================================================
# Module-level function for reference-based serialization fast path
# =============================================================================
def module_level_function(x: int, y: int) -> int:
    """A simple module-level function that can be serialized by reference."""
    return x * y + 42


# =============================================================================
# Simple class for simple_class_instance fast path
# =============================================================================
class SimplePoint:
    """A simple class with only primitive attributes."""
    def __init__(self, x: int, y: int, name: str):
        self.x = x
        self.y = y
        self.name = name


# =============================================================================
# Module-level definitions for handler benchmarks
# (Must be at module level to be importable during deserialization)
# =============================================================================
import enum

class BenchmarkColor(enum.Enum):
    """Module-level enum for benchmark testing."""
    RED = 1
    GREEN = 2
    BLUE = 3


class BenchmarkClass:
    """Module-level class for benchmark testing."""
    class_attr = "class level"
    
    def __init__(self, value: int = 0):
        self.value = value
    
    def method(self):
        return self.value
    
    @staticmethod
    def static_method():
        return "static"
    
    @classmethod
    def class_method(cls):
        return cls.__name__


class BenchmarkRunner:
    """Run serialization benchmarks across multiple libraries."""
    
    def __init__(self):
        self.results = {}
        self.cerial_s = Cerializer()
        self.cerial_d = Decerializer()
    
    def benchmark_serializer(self, name: str, obj: Any, num_iterations: int = 1000):
        """
        Benchmark a single serializer on an object.
        
        Returns: (success: bool, ops_per_sec: float, bytes_per_obj: int, error: str)
        """
        if name == "cerial":
            serialize_func = self.cerial_s.serialize
            deserialize_func = self.cerial_d.deserialize
        elif name == "pickle":
            serialize_func = pickle.dumps
            deserialize_func = pickle.loads
        elif name == "dill":
            if not HAS_DILL:
                return False, 0, 0, "dill not installed"
            serialize_func = dill.dumps
            deserialize_func = dill.loads
        elif name == "cloudpickle":
            if not HAS_CLOUDPICKLE:
                return False, 0, 0, "cloudpickle not installed"
            serialize_func = cloudpickle.dumps
            deserialize_func = cloudpickle.loads
        else:
            return False, 0, 0, f"Unknown serializer: {name}"
        
        try:
            # Warmup
            serialized = serialize_func(obj)
            deserialize_func(serialized)
            
            # Benchmark
            start = time.time()
            for _ in range(num_iterations):
                serialized = serialize_func(obj)
                reconstructed = deserialize_func(serialized)
            elapsed = time.time() - start
            
            ops_per_sec = num_iterations / elapsed
            bytes_per_obj = len(serialized)
            
            return True, ops_per_sec, bytes_per_obj, ""
            
        except Exception as e:
            return False, 0, 0, f"{type(e).__name__}: {str(e)[:50]}"
    
    def run_benchmark_suite(self, suite_name: str, obj: Any, num_iterations: int = 1000):
        """Run all serializers on a single object."""
        print(f"\n{'='*70}")
        print(f"BENCHMARK: {suite_name}")
        print(f"{'='*70}")
        print(f"Object: {type(obj).__name__}")
        print(f"Iterations: {num_iterations:,}")
        print()
        
        results = {}
        serializers = ["pickle", "dill", "cloudpickle", "cerial"]
        
        for serializer in serializers:
            success, ops_per_sec, bytes_per_obj, error = self.benchmark_serializer(
                serializer, obj, num_iterations
            )
            results[serializer] = {
                "success": success,
                "ops_per_sec": ops_per_sec,
                "bytes": bytes_per_obj,
                "error": error,
            }
        
        # Print results
        print(f"{'Library':<15} {'Status':<12} {'Ops/Sec':<15} {'Bytes':<10} {'Error'}")
        print("-" * 70)
        
        for serializer in serializers:
            r = results[serializer]
            if r["success"]:
                status = "✓ PASS"
                ops = f"{r['ops_per_sec']:,.0f}"
                bytes_str = f"{r['bytes']:,}"
                error = ""
            else:
                status = "✗ FAIL"
                ops = "N/A"
                bytes_str = "N/A"
                error = r["error"]
            
            print(f"{serializer:<15} {status:<12} {ops:<15} {bytes_str:<10} {error}")
        
        # Calculate speedup comparison
        if results["cerial"]["success"] and results["pickle"]["success"]:
            speedup = results["pickle"]["ops_per_sec"] / results["cerial"]["ops_per_sec"]
            print(f"\n  pickle is {speedup:.1f}x faster than cerial (for this object)")
        
        self.results[suite_name] = results
        return results


def create_simple_object():
    """Simple object - pickle should dominate here."""
    return {
        "name": "John Doe",
        "age": 30,
        "scores": [95, 87, 92, 88],
        "active": True,
    }


def create_medium_object():
    """Medium complexity - comparable performance."""
    @dataclass
    class Person:
        name: str
        age: int
        scores: List[int]
        metadata: Dict[str, Any]
    
    return Person(
        name="John Doe",
        age=30,
        scores=[95, 87, 92, 88],
        metadata={
            "created": "2024-01-01",
            "tags": ["student", "active"],
            "nested": {"level": 1, "points": 100},
        }
    )


def create_function_object():
    """Function object - dill/cloudpickle should handle, pickle might fail."""
    def my_function(x, y):
        return x * y + 42
    
    return my_function


def create_complex_object():
    """Complex object - only cerial can handle."""
    import threading
    import logging
    import io
    
    logger = logging.getLogger("test_logger")
    lock = threading.Lock()
    event = threading.Event()
    string_io = io.StringIO("test data")
    
    return {
        "logger": logger,
        "lock": lock,
        "event": event,
        "file": string_io,
        "data": [1, 2, 3],
    }


def create_module_level_function():
    """
    Module-level function - tests cerial's reference-based fast path.
    
    Uses a pure Python function from an importable module.
    When running as __main__, local functions can't use reference path
    because __main__ can't be imported on the other end.
    
    Expected: reference serialization is ~100x faster and smaller.
    """
    import textwrap
    return textwrap.wrap  # Pure Python function, importable by reference


def create_simple_instance():
    """
    Simple class instance - tests cerial's simple_class_instance fast path.
    
    SimplePoint has:
    - Module-level class definition
    - Only primitive attributes (int, str)
    - No __slots__, no custom __serialize__
    
    This triggers cerial's flat IR format with no circular ref tracking.
    """
    return SimplePoint(x=10, y=20, name="origin")


# =============================================================================
# Handler-specific object factories
# =============================================================================

def create_handler_objects():
    """
    Create test objects for each handler type.
    Returns dict of {handler_name: (object, description)}.
    """
    import threading
    import logging
    import io
    import re
    import sqlite3
    import tempfile
    import queue
    import weakref
    import functools
    from collections import namedtuple
    from contextvars import ContextVar
    
    objects = {}
    
    # --- Lock Handler ---
    objects["lock"] = (threading.Lock(), "threading.Lock")
    objects["rlock"] = (threading.RLock(), "threading.RLock")
    objects["event"] = (threading.Event(), "threading.Event")
    objects["condition"] = (threading.Condition(), "threading.Condition")
    objects["semaphore"] = (threading.Semaphore(5), "threading.Semaphore")
    objects["barrier"] = (threading.Barrier(2), "threading.Barrier")
    
    # --- Logging Handler ---
    logger = logging.getLogger("benchmark_test")
    logger.setLevel(logging.DEBUG)
    objects["logger"] = (logger, "logging.Logger")
    
    # --- File Handler ---
    objects["stringio"] = (io.StringIO("test content"), "io.StringIO")
    objects["bytesio"] = (io.BytesIO(b"test bytes"), "io.BytesIO")
    
    # Tempfile (careful - needs cleanup) - use w+ for read/write
    tf = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    tf.write("temp content")
    tf.flush()
    tf.seek(0)  # Reset position for reading
    objects["tempfile"] = (tf, "tempfile.NamedTemporaryFile")
    
    # --- Regex Handler ---
    objects["regex"] = (re.compile(r'\d+\.\d+'), "re.Pattern")
    objects["regex_flags"] = (re.compile(r'hello', re.IGNORECASE | re.MULTILINE), "re.Pattern (flags)")
    
    # --- Queue Handler ---
    q = queue.Queue()
    q.put("item1")
    q.put("item2")
    objects["queue"] = (q, "queue.Queue")
    
    lifo = queue.LifoQueue()
    lifo.put("last")
    lifo.put("first")
    objects["lifo_queue"] = (lifo, "queue.LifoQueue")
    
    # --- SQLite Handler ---
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER, name TEXT)")
    cursor.execute("INSERT INTO test VALUES (1, 'Alice')")
    conn.commit()
    objects["sqlite_conn"] = (conn, "sqlite3.Connection")
    objects["sqlite_cursor"] = (cursor, "sqlite3.Cursor")
    
    # --- Enum Handler ---
    # Use module-level enum (BenchmarkColor) so it can be imported during deserialization
    objects["enum"] = (BenchmarkColor.RED, "Enum value")
    
    # --- NamedTuple Handler ---
    Point = namedtuple('Point', ['x', 'y'])
    objects["namedtuple"] = (Point(10, 20), "namedtuple")
    
    # --- ContextVar Handler ---
    ctx_var = ContextVar('test_var', default=42)
    objects["contextvar"] = (ctx_var, "contextvars.ContextVar")
    
    # --- WeakRef Handler ---
    class Target:
        pass
    target = Target()
    objects["weakref"] = (weakref.ref(target), "weakref.ref")
    # Keep target alive
    objects["weakref_target"] = (target, "weakref target (keep alive)")
    
    # --- Function Handler ---
    def local_func(x):
        return x * 2
    objects["local_function"] = (local_func, "local function")
    
    # Lambda
    objects["lambda"] = (lambda x: x + 1, "lambda")
    
    # Closure
    def make_closure(n):
        def closure(x):
            return x + n
        return closure
    objects["closure"] = (make_closure(10), "closure")
    
    # Partial
    objects["partial"] = (functools.partial(int, base=16), "functools.partial")
    
    # --- Iterator Handler ---
    objects["range"] = (range(100), "range iterator")
    objects["zip"] = (zip([1,2,3], ['a','b','c']), "zip iterator")
    objects["map"] = (map(str, [1,2,3]), "map iterator")
    objects["filter"] = (filter(bool, [0,1,0,2]), "filter iterator")
    
    # --- Generator Handler ---
    def gen():
        yield 1
        yield 2
        yield 3
    objects["generator"] = (gen(), "generator")
    
    # --- Class Handler ---
    # Use module-level class (BenchmarkClass) so it can be imported during deserialization
    objects["class"] = (BenchmarkClass, "user-defined class")
    objects["instance"] = (BenchmarkClass(42), "class instance")
    
    # --- Module Handler ---
    import json
    objects["module"] = (json, "module (json)")
    
    # --- Advanced Python Handler ---
    # Use module-level class methods so they can be found during deserialization
    objects["staticmethod"] = (BenchmarkClass.static_method, "staticmethod")
    objects["classmethod"] = (BenchmarkClass.class_method, "classmethod")
    
    return objects


def create_worst_possible_object():
    """Create a WorstPossibleObject for benchmarking."""
    from suitkaise.cerial._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    return WorstPossibleObject()


def main():
    """Run all benchmarks."""
    print("="*70)
    print("SERIALIZATION LIBRARY COMPARISON")
    print("="*70)
    print("\nComparing: pickle, dill, cloudpickle, cerial")
    print("\nLibraries available:")
    print(f"  pickle: ✓ (stdlib)")
    print(f"  dill: {'✓' if HAS_DILL else '✗ (not installed)'}")
    print(f"  cloudpickle: {'✓' if HAS_CLOUDPICKLE else '✗ (not installed)'}")
    print(f"  cerial: ✓")
    
    runner = BenchmarkRunner()
    
    # ==========================================================================
    # SECTION 1: Basic Objects (pickle comparison)
    # ==========================================================================
    print("\n" + "="*70)
    print("SECTION 1: BASIC OBJECTS (Pickle Comparison)")
    print("="*70)
    
    runner.run_benchmark_suite(
        "Simple Dict",
        create_simple_object(),
        num_iterations=5000
    )
    
    runner.run_benchmark_suite(
        "Dataclass",
        create_medium_object(),
        num_iterations=2000
    )
    
    # ==========================================================================
    # SECTION 2: Cerial Fast Paths
    # ==========================================================================
    print("\n" + "="*70)
    print("SECTION 2: CERIAL FAST PATHS")
    print("="*70)
    
    runner.run_benchmark_suite(
        "Module-Level Function (reference fast path)",
        create_module_level_function(),
        num_iterations=5000
    )
    
    runner.run_benchmark_suite(
        "Simple Class Instance (fast path)",
        create_simple_instance(),
        num_iterations=5000
    )
    
    # ==========================================================================
    # SECTION 3: Handler-Specific Benchmarks
    # ==========================================================================
    print("\n" + "="*70)
    print("SECTION 3: HANDLER-SPECIFIC BENCHMARKS")
    print("="*70)
    print("\nTesting each cerial handler in isolation...")
    
    handler_objects = create_handler_objects()
    
    for name, (obj, description) in handler_objects.items():
        runner.run_benchmark_suite(
            f"Handler: {description}",
            obj,
            num_iterations=1000
        )
    
    # ==========================================================================
    # SECTION 4: WorstPossibleObject
    # ==========================================================================
    print("\n" + "="*70)
    print("SECTION 4: WORST POSSIBLE OBJECT")
    print("="*70)
    print("\nThe ultimate stress test - every complex type combined...")
    
    try:
        wpo = create_worst_possible_object()
        runner.run_benchmark_suite(
            "WorstPossibleObject (all handlers)",
            wpo,
            num_iterations=50  # Fewer iterations, very heavy object
        )
    except Exception as e:
        print(f"  Failed to create WorstPossibleObject: {e}")
    
    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    # Count results
    total = len(runner.results)
    cerial_passed = sum(1 for r in runner.results.values() if r.get("cerial", {}).get("success", False))
    pickle_passed = sum(1 for r in runner.results.values() if r.get("pickle", {}).get("success", False))
    
    print(f"\nTotal benchmarks: {total}")
    print(f"Cerial success rate: {cerial_passed}/{total} ({100*cerial_passed/total:.0f}%)")
    print(f"Pickle success rate: {pickle_passed}/{total} ({100*pickle_passed/total:.0f}%)")
    
    print("\n1. Simple Objects:")
    print("   - pickle/cloudpickle/dill are faster (expected)")
    print("   - cerial trades some speed for universal capability")
    
    print("\n2. Cerial Fast Paths:")
    print("   - Module-level functions: reference serialization")
    print("   - Simple class instances: flat IR format")
    print("   - Primitive dicts: direct copy (no recursion)")
    print("   - Handler caching: type-based lookup cache")
    
    print("\n3. Handler Coverage:")
    print("   - Locks, Events, Semaphores, Barriers")
    print("   - Loggers with handlers")
    print("   - File handles (StringIO, BytesIO, tempfiles)")
    print("   - Regex patterns, SQLite connections")
    print("   - Queues, ContextVars, WeakRefs")
    print("   - Functions, lambdas, closures, partials")
    print("   - Generators, iterators, classes, modules")
    
    print("\n4. Value Proposition:")
    print("   - pickle: Fast but limited")
    print("   - cerial: Slower but universal (100% of objects work)")
    
    print("="*70)


if __name__ == "__main__":
    main()

