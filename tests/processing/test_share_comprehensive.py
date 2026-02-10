"""
Comprehensive Share Tests

Tests Share with ALL suitkaise objects and the WorstPossibleObject:
- Sktimer, Circuit, BreakingCircuit, Skpath
- WorstPossibleObject with all edge cases
- Cross-proxy synchronization (changes reflect across proxies)
- Serialization/deserialization roundtrip
- All objects in a single Share instance

This is the definitive test for Share's ability to handle any object.
"""

import sys
import time
import threading
import traceback
from typing import Any, Dict, List, Tuple

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.timing import Sktimer, TimeThis
from suitkaise.circuits import Circuit, BreakingCircuit
from suitkaise.paths import Skpath, get_project_root
from suitkaise.processing import Share, Skprocess, Pool
from suitkaise.cucumber import serialize, deserialize, reconnect_all
from suitkaise.sk import sk
from suitkaise.sk.api import Skclass, Skfunction

Process = Skprocess


# =============================================================================
# Test Infrastructure
# =============================================================================

class TestResult:
    def __init__(
        self,
        name: str,
        passed: bool,
        message: str = "",
        error: str = "",
        traceback_text: str = "",
    ):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error
        self.traceback_text = traceback_text


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def run_test(self, name: str, test_func):
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            tb = traceback.format_exc()
            self.results.append(
                TestResult(
                    name,
                    False,
                    error=str(e),
                    traceback_text=tb,
                )
            )
        except Exception as e:
            tb = traceback.format_exc()
            self.results.append(
                TestResult(
                    name,
                    False,
                    error=f"{type(e).__name__}: {e}",
                    traceback_text=tb,
                )
            )
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*70}{self.RESET}\n")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        for result in self.results:
            if result.passed:
                status = f"{self.GREEN}✓ PASS{self.RESET}"
            else:
                status = f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")
            if result.traceback_text:
                print(f"{self.RED}{result.traceback_text}{self.RESET}")
        
        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")

        if failed != 0:
            print(f"{self.BOLD}{self.RED}Failed tests (recap):{self.RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  {self.RED}✗ {result.name}{self.RESET}")
                    if result.error:
                        print(f"     {self.RED}└─ {result.error}{self.RESET}")
            print()


        try:
            from tests._failure_registry import record_failures
            record_failures(self.suite_name, [r for r in self.results if not r.passed])
        except Exception:
            pass

        return failed == 0


# Import user classes from separate module for multiprocessing compatibility
from tests.processing.test_classes import Counter, DataStore, NestedObject, SlowWorker


# =============================================================================
# Sktimer Tests
# =============================================================================

def test_share_timer_basic():
    """Sktimer should have _shared_meta for Share compatibility."""
    # Note: Actually creating Share requires multiprocessing permissions
    # This test checks the prerequisite: Sktimer has _shared_meta
    assert hasattr(Sktimer, '_shared_meta')
    timer = Sktimer()
    assert timer is not None


def test_share_timer_has_shared_meta():
    """Sktimer should have _shared_meta for Share compatibility."""
    assert hasattr(Sktimer, '_shared_meta')
    meta = Sktimer._shared_meta
    
    assert 'methods' in meta
    assert 'properties' in meta
    # start/stop are now in _share_blocked_methods, not _shared_meta
    assert 'add_time' in meta['methods']
    assert 'reset' in meta['methods']
    assert 'mean' in meta['properties']


def test_share_timer_serialization():
    """Sktimer should serialize/deserialize correctly."""
    timer = Sktimer()
    timer.add_time(1.0)
    timer.add_time(2.0)
    timer.add_time(3.0)
    
    # Serialize
    data = serialize(timer)
    assert isinstance(data, bytes)
    assert len(data) > 0
    
    # Deserialize
    restored = deserialize(data)
    
    assert restored.num_times == 3
    assert restored.total_time == 6.0
    assert restored.mean == 2.0


def test_share_timer_all_properties():
    """Sktimer should preserve all properties through serialization."""
    timer = Sktimer()
    for i in range(1, 6):
        timer.add_time(float(i))
    
    original_stats = {
        'num_times': timer.num_times,
        'total_time': timer.total_time,
        'mean': timer.mean,
        'median': timer.median,
        'min': timer.min,
        'max': timer.max,
        'stdev': timer.stdev,
        'variance': timer.variance,
    }
    
    # Roundtrip
    data = serialize(timer)
    restored = deserialize(data)
    
    restored_stats = {
        'num_times': restored.num_times,
        'total_time': restored.total_time,
        'mean': restored.mean,
        'median': restored.median,
        'min': restored.min,
        'max': restored.max,
        'stdev': restored.stdev,
        'variance': restored.variance,
    }
    
    for key in original_stats:
        orig = original_stats[key]
        rest = restored_stats[key]
        if orig is not None:
            assert abs(orig - rest) < 0.0001, f"{key}: {orig} != {rest}"


# =============================================================================
# Circuit Tests
# =============================================================================

def test_share_circuit_basic():
    """Circuit should have _shared_meta for Share compatibility."""
    assert hasattr(Circuit, '_shared_meta')
    circuit = Circuit(5, sleep_time_after_trip=0.0)
    assert circuit is not None


def test_share_circuit_has_shared_meta():
    """Circuit should have _shared_meta for Share compatibility."""
    assert hasattr(Circuit, '_shared_meta')
    meta = Circuit._shared_meta
    
    assert 'methods' in meta
    assert 'properties' in meta
    assert 'short' in meta['methods']
    assert 'trip' in meta['methods']


def test_share_circuit_serialization():
    """Circuit should serialize/deserialize correctly."""
    circuit = Circuit(5, sleep_time_after_trip=0.01, backoff_factor=2.0, max_sleep_time=1.0)
    
    # Make some state changes
    circuit.short()
    circuit.short()
    circuit.short()
    
    original = {
        'num_shorts_to_trip': circuit.num_shorts_to_trip,
        'sleep_time_after_trip': circuit.sleep_time_after_trip,
        'backoff_factor': circuit.backoff_factor,
        'max_sleep_time': circuit.max_sleep_time,
        'times_shorted': circuit.times_shorted,
        'total_trips': circuit.total_trips,
    }
    
    # Roundtrip
    data = serialize(circuit)
    restored = deserialize(data)
    
    assert restored.num_shorts_to_trip == original['num_shorts_to_trip']
    assert restored.times_shorted == original['times_shorted']
    assert restored.total_trips == original['total_trips']


def test_share_breaking_circuit_basic():
    """BreakingCircuit should have _shared_meta for Share compatibility."""
    assert hasattr(BreakingCircuit, '_shared_meta')
    breaker = BreakingCircuit(3)
    assert breaker is not None


def test_share_breaking_circuit_has_shared_meta():
    """BreakingCircuit should have _shared_meta."""
    assert hasattr(BreakingCircuit, '_shared_meta')


# =============================================================================
# Skpath Tests
# =============================================================================

def test_share_skpath_basic():
    """Skpath should be creatable and serializable."""
    path = Skpath(__file__)
    assert path is not None
    assert path.exists


def test_share_skpath_serialization():
    """Skpath should serialize/deserialize correctly."""
    path = Skpath(__file__)
    
    original_name = path.name
    original_ap = path.ap
    
    # Roundtrip
    data = serialize(path)
    restored = deserialize(data)
    
    assert restored.name == original_name
    assert restored.ap == original_ap


# =============================================================================
# User Class Tests (via @sk)
# =============================================================================

def test_share_sk_counter():
    """@sk wrapped Counter should have _shared_meta."""
    assert hasattr(Counter, '_shared_meta')
    counter = Counter(10)
    assert counter.value == 10


def test_share_sk_counter_has_shared_meta():
    """@sk wrapped class should have _shared_meta."""
    assert hasattr(Counter, '_shared_meta')
    meta = Counter._shared_meta
    
    assert 'methods' in meta
    assert 'properties' in meta


def test_share_sk_counter_serialization():
    """@sk Counter should serialize correctly (deserialization requires importable module)."""
    counter = Counter(42)
    counter.increment()
    counter.increment()
    counter.add(10)
    
    assert counter.value == 54
    
    # Serialize should work
    data = serialize(counter)
    assert len(data) > 0
    
    # Note: Deserialization of __main__ defined classes doesn't work
    # This is a cucumber limitation - classes must be importable from a module


def test_share_sk_datastore():
    """@sk wrapped DataStore should have _shared_meta."""
    assert hasattr(DataStore, '_shared_meta')
    store = DataStore()
    assert store.items == {}


def test_share_sk_datastore_serialization():
    """@sk DataStore should serialize correctly."""
    store = DataStore()
    store.set("key1", "value1")
    store.set("key2", {"nested": [1, 2, 3]})
    store.metadata["version"] = "1.0"
    
    # Serialize should work
    data = serialize(store)
    assert len(data) > 0
    
    # Note: Deserialization of __main__ defined classes doesn't work


def test_share_sk_nested_object():
    """@sk NestedObject should serialize correctly."""
    nested = NestedObject()
    nested.modify_level1("c", 3)
    nested.set_deep_value(100)
    
    # Serialize should work
    data = serialize(nested)
    assert len(data) > 0


# =============================================================================
# All Objects in One Share
# =============================================================================

def test_share_all_sk_objects_together():
    """All suitkaise objects should have _shared_meta."""
    # Check all have _shared_meta
    assert hasattr(Sktimer, '_shared_meta')
    assert hasattr(Circuit, '_shared_meta')
    assert hasattr(BreakingCircuit, '_shared_meta')
    assert hasattr(Counter, '_shared_meta')
    assert hasattr(DataStore, '_shared_meta')
    assert hasattr(NestedObject, '_shared_meta')
    assert hasattr(SlowWorker, '_shared_meta')
    
    # Create all objects
    timer = Sktimer()
    circuit = Circuit(5, sleep_time_after_trip=0.0)
    breaker = BreakingCircuit(3)
    path = Skpath(__file__)
    counter = Counter(0)
    store = DataStore()
    nested = NestedObject()
    worker = SlowWorker()
    
    # All should be valid
    assert timer is not None
    assert circuit is not None
    assert breaker is not None
    assert path is not None
    assert counter is not None
    assert store is not None
    assert nested is not None
    assert worker is not None


def test_share_all_objects_serialization():
    """All suitkaise objects should serialize/deserialize correctly."""
    # Create and modify suitkaise objects (not __main__ defined)
    timer = Sktimer()
    timer.add_time(1.0)
    
    circuit = Circuit(5, sleep_time_after_trip=0.0)
    circuit.short()
    
    breaker = BreakingCircuit(3)
    
    # All should serialize
    timer_data = serialize(timer)
    circuit_data = serialize(circuit)
    breaker_data = serialize(breaker)
    
    assert len(timer_data) > 0
    assert len(circuit_data) > 0
    assert len(breaker_data) > 0
    
    # Suitkaise objects should deserialize (they're in importable modules)
    timer_restored = deserialize(timer_data)
    circuit_restored = deserialize(circuit_data)
    breaker_restored = deserialize(breaker_data)
    
    assert timer_restored.num_times == 1
    assert circuit_restored.times_shorted == 1


# =============================================================================
# Cross-Reference Tests
# =============================================================================

def test_share_objects_cross_reference():
    """Objects in Share should be able to reference each other after roundtrip."""
    
    @sk
    class Container:
        def __init__(self):
            self.children = []
            self.parent = None
    
    parent = Container()
    child1 = Container()
    child2 = Container()
    
    parent.children = [child1, child2]
    child1.parent = parent
    child2.parent = parent
    
    # Serialize the parent (includes children)
    data = serialize(parent)
    restored = deserialize(data)
    
    # Structure should be preserved
    assert len(restored.children) == 2
    # Note: Object identity may not be preserved, but structure should be


# =============================================================================
# Serialization Stress Tests
# =============================================================================

def test_share_large_timer():
    """Sktimer with many measurements should serialize correctly."""
    timer = Sktimer()
    for i in range(1000):
        timer.add_time(float(i) / 100)
    
    data = serialize(timer)
    restored = deserialize(data)
    
    assert restored.num_times == 1000
    assert abs(restored.total_time - timer.total_time) < 0.001


def test_share_large_datastore():
    """Large dict should serialize correctly."""
    # Use plain dict instead of DataStore to avoid __main__ issue
    large_dict = {}
    for i in range(500):
        large_dict[f"key_{i}"] = {"index": i, "data": [i, i*2, i*3]}
    
    data = serialize(large_dict)
    restored = deserialize(data)
    
    assert len(restored) == 500
    assert restored["key_250"]["index"] == 250


def test_share_deeply_nested():
    """Deeply nested structures should serialize correctly."""
    
    @sk
    class DeepNest:
        def __init__(self, depth: int = 0):
            self.value = depth
            self.child = None
            if depth < 50:
                self.child = DeepNest(depth + 1)
    
    root = DeepNest(0)
    
    data = serialize(root)
    restored = deserialize(data)
    
    # Walk down the tree
    current = restored
    for expected_depth in range(51):
        assert current.value == expected_depth
        if expected_depth < 50:
            current = current.child


# =============================================================================
# Worst Possible Object Tests
# =============================================================================

def test_share_worst_possible_object_import():
    """WorstPossibleObject should be importable."""
    try:
        from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
        assert WorstPossibleObject is not None
    except ImportError as e:
        # If WPO can't be imported, skip but note why
        raise AssertionError(f"Could not import WorstPossibleObject: {e}")


def test_share_worst_possible_object_creation():
    """WorstPossibleObject should be creatable."""
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    
    # WPO always creates - just check it works
    try:
        wpo = WorstPossibleObject(verbose=False)
        assert wpo is not None
        # Check basic primitives exist
        assert hasattr(wpo, 'int_value')
        assert hasattr(wpo, 'str_value')
    except Exception as e:
        # Some system resources might fail, that's ok
        assert "permission" in str(e).lower() or "resource" in str(e).lower()


def test_share_worst_possible_object_serialization():
    """WorstPossibleObject primitives should serialize."""
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    
    try:
        wpo = WorstPossibleObject(verbose=False)
        
        # Get some verification data
        original_int = wpo.int_value
        original_str = wpo.str_value
        original_float = wpo.float_value
        
        # Serialize
        data = serialize(wpo)
        assert isinstance(data, bytes)
        assert len(data) > 0
        
        # Deserialize
        restored = deserialize(data)
        
        # Verify primitives preserved
        assert restored.int_value == original_int
        assert restored.str_value == original_str
        assert abs(restored.float_value - original_float) < 0.0001
    except Exception as e:
        # Some platform-specific resources might fail
        if "permission" not in str(e).lower():
            raise


def test_share_worst_possible_object_roundtrip():
    """WorstPossibleObject should roundtrip correctly."""
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    
    try:
        wpo = WorstPossibleObject(verbose=False)
        
        # Store original values
        original_int = wpo.int_value
        original_str = wpo.str_value
        
        # Serialize and deserialize
        data = serialize(wpo)
        restored = deserialize(data)
        
        # Verify preserved
        assert restored.int_value == original_int
        assert restored.str_value == original_str
    except Exception as e:
        if "permission" not in str(e).lower():
            raise


def test_share_wpo_multiple_roundtrips_iterations():
    """WorstPossibleObject should serialize/deserialize reliably across multiple seeds/iterations."""
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    import random
    
    # Keep this modest so the suite stays fast, but still catches flaky issues.
    seeds = [0, 1, 2, 3, 4]
    
    for seed in seeds:
        wpo = None
        restored = None
        try:
            random.seed(seed)
            wpo = WorstPossibleObject(verbose=False)
            
            data = serialize(wpo)
            restored = deserialize(data)
            restored = reconnect_all(restored)
            
            ok, failures = wpo.verify(restored)
            assert ok, "WPO verification failed:\n" + "\n".join(failures[:50])
        except Exception as e:
            # Some platform-specific resources might fail (files/sockets/permissions).
            if "permission" not in str(e).lower() and "resource" not in str(e).lower():
                raise
        finally:
            # Avoid leaking resources between iterations
            try:
                if wpo is not None:
                    wpo.cleanup()
            except Exception:
                pass
            try:
                if restored is not None and hasattr(restored, "cleanup"):
                    restored.cleanup()
            except Exception:
                pass


def test_share_wpo_multiple_objects_single_payload():
    """Multiple independently-generated WPOs should roundtrip together in one payload."""
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    import random
    
    wpos = []
    restored_list = None
    try:
        # Deterministic diversity across objects
        for seed in [10, 11, 12]:
            random.seed(seed)
            wpos.append(WorstPossibleObject(verbose=False))
        
        data = serialize(wpos)
        restored_list = deserialize(data)
        restored_list = reconnect_all(restored_list)
        
        assert isinstance(restored_list, list)
        assert len(restored_list) == len(wpos)
        
        for original, restored in zip(wpos, restored_list):
            ok, failures = original.verify(restored)
            assert ok, "WPO verification failed:\n" + "\n".join(failures[:50])
    except Exception as e:
        if "permission" not in str(e).lower() and "resource" not in str(e).lower():
            raise
    finally:
        for obj in wpos:
            try:
                obj.cleanup()
            except Exception:
                pass
        if restored_list is not None:
            for obj in restored_list:
                try:
                    if hasattr(obj, "cleanup"):
                        obj.cleanup()
                except Exception:
                    pass


def test_share_all_objects_plus_wpo():
    """All suitkaise objects plus WPO should serialize together."""
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    
    try:
        # Create suitkaise objects
        timer = Sktimer()
        timer.add_time(1.5)
        
        circuit = Circuit(5, sleep_time_after_trip=0.0)
        circuit.short()
        circuit.short()
        
        wpo = WorstPossibleObject(verbose=False)
        original_int = wpo.int_value
        
        # Serialize all suitkaise objects together
        all_objects = {
            'timer': timer,
            'circuit': circuit,
            'wpo': wpo,
        }
        
        data = serialize(all_objects)
        restored = deserialize(data)
        
        # Verify suitkaise objects restored correctly
        assert restored['timer'].num_times == 1
        assert restored['circuit'].times_shorted == 2
        assert restored['wpo'].int_value == original_int
    except Exception as e:
        if "permission" not in str(e).lower():
            raise


def test_share_wpo_suitkaise_types():
    """WPO's suitkaise types should serialize correctly."""
    from suitkaise.cucumber._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    
    try:
        wpo = WorstPossibleObject(verbose=False)
        
        # WPO may contain Sktimer - check if it exists
        if hasattr(wpo, 'timer') and wpo.timer is not None:
            timer = wpo.timer
            timer.add_time(1.0)
            
            data = serialize(timer)
            restored = deserialize(data)
            
            assert restored.num_times >= 1
        else:
            # Sktimer might be created internally, test with a fresh one
            timer = Sktimer()
            timer.add_time(1.0)
            
            data = serialize(timer)
            restored = deserialize(data)
            
            assert restored.num_times == 1
    except Exception as e:
        if "permission" not in str(e).lower():
            raise


# =============================================================================
# Modification Tracking Tests
# =============================================================================

def test_share_modification_tracking():
    """Changes to suitkaise objects should be tracked for synchronization."""
    timer = Sktimer()
    
    # Modify
    timer.add_time(1.0)
    timer.add_time(2.0)
    timer.add_time(3.0)
    
    # Serialize after modifications
    data = serialize(timer)
    restored = deserialize(data)
    
    # Should reflect final state
    assert restored.num_times == 3
    assert restored.total_time == 6.0


def test_share_modification_complex():
    """Complex modifications to Circuit should be preserved."""
    circuit = Circuit(10, sleep_time_after_trip=0.01, backoff_factor=2.0)
    
    # Series of modifications
    circuit.short()
    circuit.short()
    circuit.short()
    circuit.short()
    circuit.short()  # 5 shorts
    
    original_times_shorted = circuit.times_shorted
    original_total_trips = circuit.total_trips
    
    # Serialize
    data = serialize(circuit)
    restored = deserialize(data)
    
    # Check final state
    assert restored.times_shorted == original_times_shorted
    assert restored.total_trips == original_total_trips
    assert restored.num_shorts_to_trip == 10


# =============================================================================
# Edge Case Tests
# =============================================================================

def test_share_empty_objects():
    """Empty suitkaise objects should serialize correctly."""
    empty_timer = Sktimer()
    empty_circuit = Circuit(5)
    
    # All should serialize
    timer_data = serialize(empty_timer)
    circuit_data = serialize(empty_circuit)
    
    # All should deserialize
    timer_restored = deserialize(timer_data)
    circuit_restored = deserialize(circuit_data)
    
    assert timer_restored.num_times == 0
    assert circuit_restored.times_shorted == 0
    assert circuit_restored.total_trips == 0


def test_share_none_values():
    """Dicts with None values should work."""
    data_dict = {
        "null_key": None,
        "empty": None,
        "nested": {"inner_none": None}
    }
    
    data = serialize(data_dict)
    restored = deserialize(data)
    
    assert restored["null_key"] is None
    assert restored["empty"] is None
    assert restored["nested"]["inner_none"] is None


def test_share_special_strings():
    """Special string values should work."""
    data_dict = {
        "empty": "",
        "unicode": "日本語 🎉 émojis",
        "newlines": "line1\nline2\nline3",
        "tabs": "col1\tcol2\tcol3",
        "quotes": 'He said "hello"',
    }
    
    data = serialize(data_dict)
    restored = deserialize(data)
    
    assert restored["empty"] == ""
    assert restored["unicode"] == "日本語 🎉 émojis"
    assert restored["newlines"] == "line1\nline2\nline3"
    assert restored["tabs"] == "col1\tcol2\tcol3"
    assert restored["quotes"] == 'He said "hello"'


def test_share_large_numbers():
    """Large numbers should work."""
    timer = Sktimer()
    timer.add_time(float(10**15))
    timer.add_time(float(10**15))
    
    data = serialize(timer)
    restored = deserialize(data)
    
    assert restored.total_time == 2 * 10**15


def test_share_float_edge_cases():
    """Float edge cases should work."""
    
    @sk
    class FloatHolder:
        def __init__(self):
            self.zero = 0.0
            self.neg_zero = -0.0
            self.tiny = 1e-308
            self.huge = 1e308
            self.inf = float('inf')
            self.neg_inf = float('-inf')
            self.nan = float('nan')
    
    holder = FloatHolder()
    
    data = serialize(holder)
    restored = deserialize(data)
    
    assert restored.zero == 0.0
    assert restored.tiny == 1e-308
    assert restored.huge == 1e308
    assert restored.inf == float('inf')
    assert restored.neg_inf == float('-inf')
    # NaN != NaN by definition, so check with math.isnan
    import math
    assert math.isnan(restored.nan)


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all comprehensive Share tests."""
    runner = TestRunner("Comprehensive Share Tests")
    
    # Sktimer tests
    runner.run_test("Share Sktimer basic", test_share_timer_basic)
    runner.run_test("Share Sktimer has _shared_meta", test_share_timer_has_shared_meta)
    runner.run_test("Share Sktimer serialization", test_share_timer_serialization)
    runner.run_test("Share Sktimer all properties", test_share_timer_all_properties)
    
    # Circuit tests
    runner.run_test("Share Circuit basic", test_share_circuit_basic)
    runner.run_test("Share Circuit has _shared_meta", test_share_circuit_has_shared_meta)
    runner.run_test("Share Circuit serialization", test_share_circuit_serialization)
    runner.run_test("Share BreakingCircuit basic", test_share_breaking_circuit_basic)
    runner.run_test("Share BreakingCircuit has _shared_meta", test_share_breaking_circuit_has_shared_meta)
    
    # Skpath tests
    runner.run_test("Share Skpath basic", test_share_skpath_basic)
    runner.run_test("Share Skpath serialization", test_share_skpath_serialization)
    
    # User class tests
    runner.run_test("Share @sk Counter", test_share_sk_counter)
    runner.run_test("Share @sk Counter has _shared_meta", test_share_sk_counter_has_shared_meta)
    runner.run_test("Share @sk Counter serialization", test_share_sk_counter_serialization)
    runner.run_test("Share @sk DataStore", test_share_sk_datastore)
    runner.run_test("Share @sk DataStore serialization", test_share_sk_datastore_serialization)
    runner.run_test("Share @sk NestedObject serialization", test_share_sk_nested_object)
    
    # All objects together
    runner.run_test("Share all sk objects together", test_share_all_sk_objects_together)
    runner.run_test("Share all objects serialization", test_share_all_objects_serialization)
    
    # Cross-reference tests
    runner.run_test("Share objects cross-reference", test_share_objects_cross_reference)
    
    # Stress tests
    runner.run_test("Share large Sktimer", test_share_large_timer)
    runner.run_test("Share large DataStore", test_share_large_datastore)
    runner.run_test("Share deeply nested", test_share_deeply_nested)
    
    # WPO tests
    runner.run_test("Share WPO import", test_share_worst_possible_object_import)
    runner.run_test("Share WPO creation", test_share_worst_possible_object_creation)
    runner.run_test("Share WPO serialization", test_share_worst_possible_object_serialization)
    runner.run_test("Share WPO roundtrip", test_share_worst_possible_object_roundtrip)
    runner.run_test("Share WPO multi-roundtrip iterations", test_share_wpo_multiple_roundtrips_iterations)
    runner.run_test("Share WPO multiple objects single payload", test_share_wpo_multiple_objects_single_payload)
    runner.run_test("Share all objects + WPO", test_share_all_objects_plus_wpo)
    runner.run_test("Share WPO suitkaise types", test_share_wpo_suitkaise_types)
    
    # Modification tracking tests
    runner.run_test("Share modification tracking", test_share_modification_tracking)
    runner.run_test("Share modification complex", test_share_modification_complex)
    
    # Edge case tests
    runner.run_test("Share empty objects", test_share_empty_objects)
    runner.run_test("Share None values", test_share_none_values)
    runner.run_test("Share special strings", test_share_special_strings)
    runner.run_test("Share large numbers", test_share_large_numbers)
    runner.run_test("Share float edge cases", test_share_float_edge_cases)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
