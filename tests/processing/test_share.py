"""
Share Class Tests

Tests Share functionality:
- Coordinator lifecycle (start/stop)
- Object registration and proxying
- Timer sharing
- Circuit sharing
- User class sharing with @sk
- Multiple workers accessing shared state
- Read/write synchronization
"""

import sys
import time
import signal

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.processing import Share
from suitkaise.timing import Timer
from suitkaise.circuits import Circuit
from suitkaise.sk import Skclass, sk

# Import test classes from separate module (required for multiprocessing)
from tests.processing.test_classes import Counter, DataStore, NestedObject


# =============================================================================
# Test Infrastructure
# =============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


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
    
    def run_test(self, name: str, test_func, timeout: float = 10.0):
        """Run a test with a timeout."""
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Test timed out after {timeout}s")
        
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
        except (AttributeError, ValueError):
            pass
        
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except TimeoutError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))
        finally:
            try:
                signal.alarm(0)
                if old_handler:
                    signal.signal(signal.SIGALRM, old_handler)
            except (AttributeError, ValueError):
                pass
    
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
        
        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")
        return failed == 0


# =============================================================================
# Import and Structure Tests
# =============================================================================

def test_share_import():
    """Share should be importable."""
    assert Share is not None


def test_share_class_exists():
    """Share class should exist and be a class."""
    assert isinstance(Share, type)


def test_share_has_enter():
    """Share should have __enter__ for context manager."""
    assert hasattr(Share, '__enter__')


def test_share_has_exit():
    """Share should have __exit__ for context manager."""
    assert hasattr(Share, '__exit__')


def test_share_has_setattr():
    """Share should have __setattr__ for attribute assignment."""
    assert hasattr(Share, '__setattr__')


def test_share_has_getattr():
    """Share should have __getattr__ for attribute access."""
    assert hasattr(Share, '__getattr__')


def test_share_has_start():
    """Share should have start() method."""
    assert hasattr(Share, 'start')


def test_share_has_stop():
    """Share should have stop() method."""
    assert hasattr(Share, 'stop')


# =============================================================================
# Timer _shared_meta Tests
# =============================================================================

def test_timer_has_shared_meta():
    """Timer should have _shared_meta for Share compatibility."""
    assert hasattr(Timer, '_shared_meta')


def test_timer_shared_meta_structure():
    """Timer._shared_meta should have correct structure."""
    meta = Timer._shared_meta
    
    assert 'methods' in meta
    assert 'properties' in meta
    
    # Check key methods
    assert 'start' in meta['methods']
    assert 'stop' in meta['methods']
    assert 'add_time' in meta['methods']
    assert 'reset' in meta['methods']
    
    # Check key properties
    assert 'mean' in meta['properties']
    assert 'median' in meta['properties']


def test_timer_shared_meta_writes():
    """Timer._shared_meta methods should declare writes."""
    meta = Timer._shared_meta
    
    # start() writes to _sessions and original_start_time
    start_meta = meta['methods']['start']
    assert 'writes' in start_meta
    assert '_sessions' in start_meta['writes']
    
    # add_time() writes to times
    add_meta = meta['methods']['add_time']
    assert 'writes' in add_meta
    assert 'times' in add_meta['writes']


def test_timer_shared_meta_reads():
    """Timer._shared_meta properties should declare reads."""
    meta = Timer._shared_meta
    
    # mean reads from times
    mean_meta = meta['properties']['mean']
    assert 'reads' in mean_meta
    assert 'times' in mean_meta['reads']


# =============================================================================
# Circuit _shared_meta Tests
# =============================================================================

def test_circuit_has_shared_meta():
    """Circuit should have _shared_meta for Share compatibility."""
    assert hasattr(Circuit, '_shared_meta')


def test_circuit_shared_meta_structure():
    """Circuit._shared_meta should have correct structure."""
    meta = Circuit._shared_meta
    
    assert 'methods' in meta
    assert 'properties' in meta
    
    # Check key methods
    assert 'short' in meta['methods']
    assert 'trip' in meta['methods']


# =============================================================================
# Skclass Tests
# =============================================================================

def test_skclass_import():
    """Skclass should be importable."""
    assert Skclass is not None


def test_skclass_creates_shared_meta():
    """Skclass should create _shared_meta on wrapped class."""
    
    class SimpleCounter:
        def __init__(self):
            self.value = 0
        
        def increment(self):
            self.value += 1
    
    SkSimpleCounter = Skclass(SimpleCounter)
    
    assert hasattr(SkSimpleCounter, '_shared_meta')


def test_sk_decorator_works():
    """@sk decorator should work on classes."""
    
    assert hasattr(Counter, '_shared_meta')
    assert hasattr(DataStore, '_shared_meta')


def test_sk_counter_meta_structure():
    """@sk Counter should have correct _shared_meta structure."""
    meta = Counter._shared_meta
    
    assert 'methods' in meta
    assert 'properties' in meta
    
    # Check methods
    assert 'increment' in meta['methods']
    assert 'add' in meta['methods']
    assert 'reset' in meta['methods']


def test_sk_datastore_meta_structure():
    """@sk DataStore should have correct _shared_meta structure."""
    meta = DataStore._shared_meta
    
    assert 'methods' in meta
    
    # Check methods
    assert 'add_item' in meta['methods']
    assert 'set_meta' in meta['methods']
    assert 'clear' in meta['methods']


# =============================================================================
# Share Creation Tests (with multiprocessing)
# =============================================================================

def test_share_creation():
    """Share should be creatable."""
    share = Share()
    
    assert share is not None
    assert not share.is_running


def test_share_start_stop():
    """Share should start and stop coordinator."""
    share = Share()
    
    share.start()
    assert share.is_running
    
    share.stop()
    assert not share.is_running


def test_share_context_manager():
    """Share should work as context manager."""
    with Share() as share:
        assert share.is_running
    
    assert not share.is_running


def test_share_set_timer():
    """Share should accept Timer."""
    with Share() as share:
        share.timer = Timer()
        
        assert hasattr(share, 'timer')


def test_share_set_circuit():
    """Share should accept Circuit."""
    with Share() as share:
        # Circuit requires num_shorts_to_trip
        share.circuit = Circuit(num_shorts_to_trip=3)
        
        assert hasattr(share, 'circuit')


def test_share_set_user_class():
    """Share should accept @sk user classes."""
    with Share() as share:
        share.counter = Counter()
        
        assert hasattr(share, 'counter')


def test_share_set_multiple_objects():
    """Share should accept multiple objects."""
    with Share() as share:
        share.timer = Timer()
        share.circuit = Circuit(num_shorts_to_trip=3)
        share.counter = Counter()
        
        assert hasattr(share, 'timer')
        assert hasattr(share, 'circuit')
        assert hasattr(share, 'counter')


# =============================================================================
# Share Operations Tests
# =============================================================================

def test_share_timer_add_time():
    """Share.timer should support add_time()."""
    with Share() as share:
        share.timer = Timer()
        
        # Add some times
        share.timer.add_time(1.0)
        share.timer.add_time(2.0)
        share.timer.add_time(3.0)
        
        # Wait for writes to process
        time.sleep(0.2)
        
        # Read back
        timer = share._coordinator.get_object('timer')
        assert timer is not None
        assert len(timer.times) == 3


def test_share_counter_increment():
    """Share.counter should support increment()."""
    with Share() as share:
        share.counter = Counter()
        
        # Increment multiple times
        for _ in range(5):
            share.counter.increment()
        
        # Wait for writes to process
        time.sleep(0.2)
        
        # Read back
        counter = share._coordinator.get_object('counter')
        assert counter is not None
        assert counter.value == 5


def test_share_datastore_operations():
    """Share.datastore should support multiple operations."""
    with Share() as share:
        share.store = DataStore()
        
        # Perform operations
        share.store.add_item("item1")
        share.store.add_item("item2")
        share.store.set_meta("key", "value")
        
        # Wait for writes to process
        time.sleep(0.2)
        
        # Read back
        store = share._coordinator.get_object('store')
        assert store is not None
        assert len(store.items) == 2
        assert store.metadata.get("key") == "value"


# =============================================================================
# Share Serialization Tests
# =============================================================================

def test_share_timer_serializes():
    """Timer should serialize correctly in Share."""
    with Share() as share:
        timer = Timer()
        timer.add_time(1.5)
        timer.add_time(2.5)
        
        share.timer = timer
        
        # Read back from source of truth
        stored_timer = share._coordinator.get_object('timer')
        assert stored_timer is not None
        assert len(stored_timer.times) == 2
        assert 1.5 in stored_timer.times
        assert 2.5 in stored_timer.times


def test_share_circuit_serializes():
    """Circuit should serialize correctly in Share."""
    with Share() as share:
        circuit = Circuit(
            num_shorts_to_trip=3,
            sleep_time_after_trip=0.5,
            factor=2.0
        )
        
        share.circuit = circuit
        
        # Read back
        stored_circuit = share._coordinator.get_object('circuit')
        assert stored_circuit is not None
        assert stored_circuit.num_shorts_to_trip == 3


def test_share_user_class_serializes():
    """User classes should serialize correctly in Share."""
    with Share() as share:
        counter = Counter()
        counter.value = 42
        
        share.counter = counter
        
        # Read back
        stored_counter = share._coordinator.get_object('counter')
        assert stored_counter is not None
        assert stored_counter.value == 42


def test_share_nested_object_serializes():
    """Nested objects should serialize correctly in Share."""
    with Share() as share:
        nested = NestedObject()
        nested.counter = 10
        nested.data['extra'] = 'value'
        
        share.nested = nested
        
        # Read back
        stored = share._coordinator.get_object('nested')
        assert stored is not None
        assert stored.counter == 10
        assert stored.data.get('extra') == 'value'


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all Share tests."""
    runner = TestRunner("Share Class Tests")
    
    # Import and structure tests (no subprocess)
    runner.run_test("Share import", test_share_import)
    runner.run_test("Share class exists", test_share_class_exists)
    runner.run_test("Share has __enter__", test_share_has_enter)
    runner.run_test("Share has __exit__", test_share_has_exit)
    runner.run_test("Share has __setattr__", test_share_has_setattr)
    runner.run_test("Share has __getattr__", test_share_has_getattr)
    runner.run_test("Share has start()", test_share_has_start)
    runner.run_test("Share has stop()", test_share_has_stop)
    
    # Timer _shared_meta tests
    runner.run_test("Timer has _shared_meta", test_timer_has_shared_meta)
    runner.run_test("Timer _shared_meta structure", test_timer_shared_meta_structure)
    runner.run_test("Timer _shared_meta writes", test_timer_shared_meta_writes)
    runner.run_test("Timer _shared_meta reads", test_timer_shared_meta_reads)
    
    # Circuit _shared_meta tests
    runner.run_test("Circuit has _shared_meta", test_circuit_has_shared_meta)
    runner.run_test("Circuit _shared_meta structure", test_circuit_shared_meta_structure)
    
    # Skclass tests
    runner.run_test("Skclass import", test_skclass_import)
    runner.run_test("Skclass creates _shared_meta", test_skclass_creates_shared_meta)
    runner.run_test("@sk decorator works", test_sk_decorator_works)
    runner.run_test("@sk Counter meta structure", test_sk_counter_meta_structure)
    runner.run_test("@sk DataStore meta structure", test_sk_datastore_meta_structure)
    
    # Share creation tests (with multiprocessing)
    runner.run_test("Share creation", test_share_creation, timeout=10)
    runner.run_test("Share start/stop", test_share_start_stop, timeout=10)
    runner.run_test("Share context manager", test_share_context_manager, timeout=10)
    runner.run_test("Share set Timer", test_share_set_timer, timeout=10)
    runner.run_test("Share set Circuit", test_share_set_circuit, timeout=10)
    runner.run_test("Share set user class", test_share_set_user_class, timeout=10)
    runner.run_test("Share set multiple objects", test_share_set_multiple_objects, timeout=10)
    
    # Share operations tests
    runner.run_test("Share Timer add_time()", test_share_timer_add_time, timeout=15)
    runner.run_test("Share Counter increment()", test_share_counter_increment, timeout=15)
    runner.run_test("Share DataStore operations", test_share_datastore_operations, timeout=15)
    
    # Share serialization tests
    runner.run_test("Share Timer serializes", test_share_timer_serializes, timeout=15)
    runner.run_test("Share Circuit serializes", test_share_circuit_serializes, timeout=15)
    runner.run_test("Share user class serializes", test_share_user_class_serializes, timeout=15)
    runner.run_test("Share nested object serializes", test_share_nested_object_serializes, timeout=15)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
