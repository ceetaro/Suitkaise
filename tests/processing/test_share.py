"""
Share Class Tests

Tests Share functionality:
- Coordinator lifecycle (start/stop)
- Object registration and proxying
- Sktimer sharing
- Circuit sharing
- User class sharing with @sk
- Multiple workers accessing shared state
- Read/write synchronization
"""

import sys
import time
import signal
import threading
import warnings
import logging
import sqlite3
import tempfile
import traceback
import os
import io

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing import Share
from suitkaise.timing import Sktimer
from suitkaise.circuits import Circuit
from suitkaise.sk import sk
from suitkaise.sk.api import Skclass
from suitkaise.cucumber._int.handlers.sqlite_handler import SQLiteConnectionReconnector

# Import test classes from separate module (required for multiprocessing)
from tests.processing.test_classes import Counter, DataStore, NestedObject


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
            tb = traceback.format_exc()
            self.results.append(
                TestResult(
                    name,
                    False,
                    error=str(e),
                    traceback_text=tb,
                )
            )
        except TimeoutError as e:
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
# Sktimer _shared_meta Tests
# =============================================================================

def test_timer_has_shared_meta():
    """Sktimer should have _shared_meta for Share compatibility."""
    assert hasattr(Sktimer, '_shared_meta')


def test_timer_shared_meta_structure():
    """Sktimer._shared_meta should have correct structure."""
    meta = Sktimer._shared_meta
    
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
    """Sktimer._shared_meta methods should declare writes."""
    meta = Sktimer._shared_meta
    
    # start() writes to _sessions and original_start_time
    start_meta = meta['methods']['start']
    assert 'writes' in start_meta
    assert '_sessions' in start_meta['writes']
    
    # add_time() writes to times
    add_meta = meta['methods']['add_time']
    assert 'writes' in add_meta
    assert 'times' in add_meta['writes']


def test_timer_shared_meta_reads():
    """Sktimer._shared_meta properties should declare reads."""
    meta = Sktimer._shared_meta
    
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
    assert share.is_running
    share.exit()


def test_share_start_stop():
    """Share should start and stop coordinator."""
    share = Share()
    
    assert share.is_running
    share.exit()
    assert not share.is_running


def test_share_exit_alias():
    """Share.exit should stop coordinator."""
    share = Share()
    
    assert share.is_running
    share.exit()
    assert not share.is_running


def test_share_set_timer():
    """Share should accept Sktimer."""
    share = Share()
    try:
        share.timer = Sktimer()
        assert hasattr(share, 'timer')
    finally:
        share.exit()


def test_share_clear():
    """Share.clear should remove objects and counters."""
    share = Share()
    try:
        share.counter = Counter()
        share.timer = Sktimer()
        share.clear()
        try:
            _ = share.counter
            assert False, "Expected AttributeError after clear"
        except AttributeError:
            pass
    finally:
        share.exit()


def test_share_set_circuit():
    """Share should accept Circuit."""
    share = Share()
    try:
        # Circuit requires num_shorts_to_trip
        share.circuit = Circuit(num_shorts_to_trip=3)
        assert hasattr(share, 'circuit')
    finally:
        share.exit()


def test_share_set_user_class():
    """Share should accept @sk user classes."""
    share = Share()
    try:
        share.counter = Counter()
        assert hasattr(share, 'counter')
    finally:
        share.exit()


def test_share_set_multiple_objects():
    """Share should accept multiple objects."""
    share = Share()
    try:
        share.timer = Sktimer()
        share.circuit = Circuit(num_shorts_to_trip=3)
        share.counter = Counter()
        
        assert hasattr(share, 'timer')
        assert hasattr(share, 'circuit')
        assert hasattr(share, 'counter')
    finally:
        share.exit()


def test_share_warns_when_stopped_setattr():
    """Share should warn when setting attrs while stopped."""
    share = Share()
    try:
        share.stop()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            share.count = 1
        assert any(issubclass(w.category, RuntimeWarning) for w in caught)
    finally:
        share.exit()


def test_share_stop_queue_then_start():
    """Queued commands while stopped should apply after start()."""
    share = Share()
    try:
        share.counter = Counter()
        share.stop()
        share.counter.increment()
        share.start()
        time.sleep(0.6 if sys.platform == "win32" else 0.2)
        counter = share._coordinator.get_object('counter')
        assert counter is not None
        assert counter.value == 1
    finally:
        share.exit()


def test_share_concurrent_increments():
    """Concurrent increments should serialize correctly."""
    share = Share()
    try:
        share.counter = Counter()
        num_threads = 5
        increments_per_thread = 50
        
        def worker():
            for _ in range(increments_per_thread):
                share.counter.increment()
        
        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        time.sleep(0.6 if sys.platform == "win32" else 0.2)
        counter = share._coordinator.get_object('counter')
        assert counter is not None
        assert counter.value == num_threads * increments_per_thread
    finally:
        share.exit()


# =============================================================================
# Share Deletion Tests
# =============================================================================

def test_share_delete_object_cleans_state():
    """Deleting a shared object should clean coordinator state."""
    share = Share()
    try:
        share.counter = Counter()
        # ensure registration
        assert "counter" in share._coordinator._source_store
        assert "counter" in list(share._coordinator._object_names)
        assert share._coordinator.get_object_keys("counter")

        del share.counter

        assert "counter" not in share._coordinator._source_store
        assert "counter" not in list(share._coordinator._object_names)
        assert share._coordinator.get_object_keys("counter") == []
        try:
            _ = share.counter
            assert False, "Expected AttributeError after deletion"
        except AttributeError:
            pass
    finally:
        share.exit()


# =============================================================================
# Share Operations Tests
# =============================================================================

def test_share_timer_add_time():
    """Share.timer should support add_time()."""
    share = Share()
    try:
        share.timer = Sktimer()
        
        # Add some times
        share.timer.add_time(1.0)
        share.timer.add_time(2.0)
        share.timer.add_time(3.0)
        
        # Wait for writes to process
        time.sleep(0.6 if sys.platform == "win32" else 0.2)
        
        # Read back
        timer = share._coordinator.get_object('timer')
        assert timer is not None
        assert len(timer.times) == 3
    finally:
        share.exit()


def test_share_counter_increment():
    """Share.counter should support increment()."""
    share = Share()
    try:
        share.counter = Counter()
        
        # Increment multiple times
        for _ in range(5):
            share.counter.increment()
        
        # Wait for writes to process
        time.sleep(0.6 if sys.platform == "win32" else 0.2)
        
        # Read back
        counter = share._coordinator.get_object('counter')
        assert counter is not None
        assert counter.value == 5
    finally:
        share.exit()


def test_share_datastore_operations():
    """Share.datastore should support multiple operations."""
    share = Share()
    try:
        share.store = DataStore()
        
        # Perform operations
        share.store.add_item("item1")
        share.store.add_item("item2")
        share.store.set_meta("key", "value")
        
        # Wait for writes to process
        time.sleep(0.6 if sys.platform == "win32" else 0.2)
        
        # Read back
        store = share._coordinator.get_object('store')
        assert store is not None
        assert len(store.items) == 2
        assert store.metadata.get("key") == "value"
    finally:
        share.exit()


# =============================================================================
# Share Serialization Tests
# =============================================================================

def test_share_timer_serializes():
    """Sktimer should serialize correctly in Share."""
    share = Share()
    try:
        timer = Sktimer()
        timer.add_time(1.5)
        timer.add_time(2.5)
        
        share.timer = timer
        
        # Read back from source of truth
        stored_timer = share._coordinator.get_object('timer')
        assert stored_timer is not None
        assert len(stored_timer.times) == 2
        assert 1.5 in stored_timer.times
        assert 2.5 in stored_timer.times
    finally:
        share.exit()


def test_share_circuit_serializes():
    """Circuit should serialize correctly in Share."""
    share = Share()
    try:
        circuit = Circuit(
            num_shorts_to_trip=3,
            sleep_time_after_trip=0.5,
            backoff_factor=2.0
        )
        
        share.circuit = circuit
        
        # Read back
        stored_circuit = share._coordinator.get_object('circuit')
        assert stored_circuit is not None
        assert stored_circuit.num_shorts_to_trip == 3
    finally:
        share.exit()


def test_share_user_class_serializes():
    """User classes should serialize correctly in Share."""
    share = Share()
    try:
        counter = Counter()
        counter.value = 42
        
        share.counter = counter
        
        # Read back
        stored_counter = share._coordinator.get_object('counter')
        assert stored_counter is not None
        assert stored_counter.value == 42
    finally:
        share.exit()


def test_share_nested_object_serializes():
    """Nested objects should serialize correctly in Share."""
    share = Share()
    try:
        nested = NestedObject()
        nested.counter = 10
        nested.data['extra'] = 'value'
        
        share.nested = nested
        
        # Read back
        stored = share._coordinator.get_object('nested')
        assert stored is not None
        assert stored.counter == 10
        assert stored.data.get('extra') == 'value'
    finally:
        share.exit()


def test_share_logger_serializes():
    """Loggers should serialize and still be usable from Share."""
    share = Share()
    logger = logging.getLogger("share.test.logger")
    old_handlers = list(logger.handlers)
    old_level = logger.level
    old_propagate = logger.propagate
    try:
        temp_file = tempfile.NamedTemporaryFile(prefix="share-logger-", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()

        logger.handlers = []
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = logging.FileHandler(temp_file_path, mode="w", encoding="utf-8")
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        share.logger = logger

        shared_logger = share.logger
        if isinstance(shared_logger, logging.Logger):
            assert shared_logger.name == "share.test.logger"
            assert shared_logger.level == logging.INFO
            assert shared_logger.propagate is False
            assert len(shared_logger.handlers) == 1
            assert isinstance(shared_logger.handlers[0], logging.FileHandler)

        shared_logger.info("hello from share")
        max_wait = 2.0 if sys.platform == "win32" else 1.0
        deadline = time.time() + max_wait
        contents = ""
        while time.time() < deadline:
            try:
                with open(temp_file_path, "r", encoding="utf-8") as handle:
                    contents = handle.read()
            except Exception:
                contents = ""
            if "share.test.logger - hello from share" in contents:
                break
            time.sleep(0.05)
        assert "share.test.logger - hello from share" in contents
    finally:
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate
        share.exit()


def test_share_db_connection_serializes_to_reconnector():
    """Database connections should be usable from Share via reconnect."""
    share = Share()
    conn = None
    try:
        conn = sqlite3.connect(":memory:")
        share.db = conn

        shared_db = share.db
        assert isinstance(shared_db, SQLiteConnectionReconnector)

        reconnected = shared_db.reconnect()
        try:
            cursor = reconnected.cursor()
            cursor.execute("CREATE TABLE t (id INTEGER)")
            cursor.execute("INSERT INTO t (id) VALUES (1)")
            reconnected.commit()
            cursor.execute("SELECT id FROM t")
            row = cursor.fetchone()
            assert row is not None and row[0] == 1
        finally:
            reconnected.close()
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        share.exit()


def test_share_reconnect_all():
    """Share.reconnect_all should reconnect stored Reconnectors."""
    share = Share()
    conn = None
    try:
        conn = sqlite3.connect(":memory:")
        share.db = conn

        stored = share._coordinator.get_object("db")
        assert isinstance(stored, SQLiteConnectionReconnector)

        reconnected = share.reconnect_all()
        updated = reconnected.get("db")
        assert isinstance(updated, sqlite3.Connection)
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        share.exit()


def test_share_rejects_os_pipe_handles():
    share = Share()
    r_fd, w_fd = os.pipe()
    pipe_handle = None
    try:
        pipe_handle = io.FileIO(r_fd, mode="rb", closefd=True)
        try:
            share.pipe = pipe_handle
            assert False, "Share should reject os.pipe() file handles"
        except ValueError:
            pass
    finally:
        if pipe_handle is not None and not pipe_handle.closed:
            try:
                pipe_handle.close()
            except Exception:
                pass
        try:
            os.close(w_fd)
        except Exception:
            pass
        share.exit()


def test_share_serialize_live_and_snapshot_modes():
    """Share.__serialize__ should reflect live vs snapshot mode."""
    share = Share()
    try:
        share.counter = Counter()
        live_state = share.__serialize__()
        assert live_state["mode"] == "live"
        assert live_state["coordinator_state"] is not None
        
        share.stop()
        snapshot_state = share.__serialize__()
        assert snapshot_state["mode"] == "snapshot"
        assert snapshot_state["coordinator_state"] is None
    finally:
        share.exit()


def test_share_deserialize_from_snapshot():
    """Share.__deserialize__ should restore objects from snapshot."""
    share = Share()
    try:
        share.counter = Counter()
        share.counter.increment()
        time.sleep(0.6 if sys.platform == "win32" else 0.2)
        share.stop()
        snapshot_state = share.__serialize__()
    finally:
        share.exit()
    
    restored = Share.__deserialize__(snapshot_state)
    try:
        counter = restored._coordinator.get_object('counter')
        assert counter is not None
        assert counter.value >= 1
    finally:
        restored.exit()


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
    
    # Sktimer _shared_meta tests
    runner.run_test("Sktimer has _shared_meta", test_timer_has_shared_meta)
    runner.run_test("Sktimer _shared_meta structure", test_timer_shared_meta_structure)
    runner.run_test("Sktimer _shared_meta writes", test_timer_shared_meta_writes)
    runner.run_test("Sktimer _shared_meta reads", test_timer_shared_meta_reads)
    
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
    runner.run_test("Share exit alias", test_share_exit_alias, timeout=10)
    runner.run_test("Share set Sktimer", test_share_set_timer, timeout=10)
    runner.run_test("Share set Circuit", test_share_set_circuit, timeout=10)
    runner.run_test("Share set user class", test_share_set_user_class, timeout=10)
    runner.run_test("Share set multiple objects", test_share_set_multiple_objects, timeout=10)
    runner.run_test("Share warns when stopped setattr", test_share_warns_when_stopped_setattr, timeout=10)
    runner.run_test("Share stop->queue->start", test_share_stop_queue_then_start, timeout=15)
    runner.run_test("Share concurrent increments", test_share_concurrent_increments, timeout=20)
    runner.run_test("Share clear", test_share_clear, timeout=10)
    runner.run_test("Share delete object cleans state", test_share_delete_object_cleans_state, timeout=10)
    
    # Share operations tests
    runner.run_test("Share Sktimer add_time()", test_share_timer_add_time, timeout=15)
    runner.run_test("Share Counter increment()", test_share_counter_increment, timeout=15)
    runner.run_test("Share DataStore operations", test_share_datastore_operations, timeout=15)
    
    # Share serialization tests
    runner.run_test("Share Sktimer serializes", test_share_timer_serializes, timeout=15)
    runner.run_test("Share Circuit serializes", test_share_circuit_serializes, timeout=15)
    runner.run_test("Share user class serializes", test_share_user_class_serializes, timeout=15)
    runner.run_test("Share nested object serializes", test_share_nested_object_serializes, timeout=15)
    runner.run_test("Share logger serializes", test_share_logger_serializes, timeout=15)
    runner.run_test("Share db connection serializes", test_share_db_connection_serializes_to_reconnector, timeout=15)
    runner.run_test("Share reconnect_all", test_share_reconnect_all, timeout=15)
    runner.run_test("Share rejects os.pipe handles", test_share_rejects_os_pipe_handles, timeout=15)
    runner.run_test("Share serialize live/snapshot", test_share_serialize_live_and_snapshot_modes, timeout=10)
    runner.run_test("Share deserialize snapshot", test_share_deserialize_from_snapshot, timeout=15)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
