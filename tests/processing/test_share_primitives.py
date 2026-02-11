"""
Share Primitive Tests

Tests low-level share primitives for counters, queues, and source of truth.
"""

from __future__ import annotations

import sys
import time

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing._int.share.primitives import (
    _WriteCounter,
    _CounterRegistry,
    _AtomicCounterRegistry,
    _CommandQueue,
    _SourceOfTruth,
)

try:
    from _suitkaise_wip.fdl._int.setup.text_wrapping import _TextWrapper
except Exception:
    _TextWrapper = None


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
        self._wrapper = _TextWrapper(width=72) if _TextWrapper else None

    def _wrap(self, text: str) -> list[str]:
        if self._wrapper:
            return self._wrapper.wrap_text(text, preserve_newlines=True)
        return [text]

    def run_test(self, name: str, test_func):
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))

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
                for line in self._wrap(result.error):
                    print(f"         {self.RED}└─ {line}{self.RESET}")

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
# _WriteCounter Tests
# =============================================================================

def test_write_counter_increment_decrement():
    """WriteCounter should increment and decrement."""
    counter = _WriteCounter()
    assert counter.pending == 0
    assert counter.increment() == 1
    assert counter.increment() == 2
    assert counter.decrement() == 1
    assert counter.decrement() == 0
    assert counter.decrement() == 0


def test_write_counter_wait():
    """WriteCounter should wait for clear."""
    counter = _WriteCounter()
    counter.increment()
    start = time.perf_counter()
    cleared = counter.wait_for_clear(timeout=0.05)
    elapsed = time.perf_counter() - start
    assert cleared is False
    assert elapsed >= 0.05
    counter.decrement()
    assert counter.wait_for_clear(timeout=0.05) is True


# =============================================================================
# _CounterRegistry Tests
# =============================================================================

def test_counter_registry_basic():
    """CounterRegistry should track increments and decrements."""
    registry = _CounterRegistry()
    key = "obj.attr"
    assert registry.get_count(key) == 0
    assert registry.increment(key) == 1
    assert registry.increment(key) == 2
    assert registry.decrement(key) == 1
    assert registry.is_clear(key) is False
    assert registry.decrement(key) == 0
    assert registry.is_clear(key) is True
    assert key in registry.keys()


def test_counter_registry_wait():
    """CounterRegistry should wait for key clearance."""
    registry = _CounterRegistry()
    key = "obj.attr"
    registry.increment(key)
    assert registry.wait_for_key(key, timeout=0.05) is False
    registry.decrement(key)
    assert registry.wait_for_key(key, timeout=0.05) is True


# =============================================================================
# _AtomicCounterRegistry Tests
# =============================================================================

def test_atomic_registry_register_and_wait():
    """Atomic registry should register keys and wait for reads."""
    registry = _AtomicCounterRegistry()
    registry.register_keys("obj", {"a", "b"})
    keys = registry.keys_for_object("obj")
    assert "obj.a" in keys
    assert "obj.b" in keys
    assert registry.increment_pending("obj.a") == 1
    registry.update_after_write("obj.a")
    assert registry.wait_for_read(["obj.a"], timeout=0.1) is True
    registry.reset()


def test_atomic_registry_multiple_keys_wait():
    """Atomic registry should wait for multiple keys."""
    registry = _AtomicCounterRegistry()
    registry.register_keys("obj", {"a", "b"})
    registry.increment_pending("obj.a")
    registry.increment_pending("obj.b")
    
    registry.update_after_write("obj.a")
    registry.update_after_write("obj.b")
    assert registry.wait_for_read(["obj.a", "obj.b"], timeout=0.1) is True
    registry.reset()


def test_atomic_registry_remove_object():
    """Atomic registry should remove object counters."""
    registry = _AtomicCounterRegistry()
    registry.register_keys("obj", {"a", "b"})
    keys_before = registry.keys_for_object("obj")
    assert keys_before
    registry.remove_object("obj")
    assert registry.keys_for_object("obj") == []
    registry.reset()

def test_atomic_registry_recovers_closed_manager_handle():
    """Atomic registry should recover if manager proxy handle is closed."""
    registry = _AtomicCounterRegistry()
    registry.register_keys("obj", {"a"})

    # Prime lock proxy connection, then forcibly close it to simulate
    # stale manager handles in long-running worker processes.
    registry.increment_pending("obj.a")
    lock_tls = getattr(registry._lock, "_tls", None)
    lock_conn = getattr(lock_tls, "connection", None) if lock_tls is not None else None
    if lock_conn is not None:
        lock_conn.close()

    # Next operation should reconnect and succeed.
    value = registry.increment_pending("obj.a")
    assert value >= 1
    registry.reset()


# =============================================================================
# _CommandQueue Tests
# =============================================================================

def test_command_queue_roundtrip():
    """CommandQueue should queue and return commands."""
    q = _CommandQueue()
    assert q.empty() is True
    q.put("obj", "method", (1, 2), {"x": 3}, ["attr"])
    time.sleep(0.05)
    assert q.empty() is False
    cmd = q.get(timeout=1.0)
    assert cmd is not None, "Expected command from queue"
    assert cmd[0] == "obj"
    assert q.get_nowait() is None


# =============================================================================
# _SourceOfTruth Tests
# =============================================================================

def test_source_of_truth_basic():
    """SourceOfTruth should store and retrieve objects."""
    store = _SourceOfTruth()
    store.set("a", {"x": 1})
    assert store.get("a") == {"x": 1}
    raw = store.get_raw("a")
    assert raw is not None
    store.set_raw("b", raw)
    assert store.get("b") == {"x": 1}
    assert "a" in store.keys()
    assert "a" in store
    assert store.delete("a") is True
    assert store.delete("missing") is False


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all share primitive tests."""
    runner = TestRunner("Share Primitives Tests")

    runner.run_test("WriteCounter inc/dec", test_write_counter_increment_decrement)
    runner.run_test("WriteCounter wait", test_write_counter_wait)
    runner.run_test("CounterRegistry basic", test_counter_registry_basic)
    runner.run_test("CounterRegistry wait", test_counter_registry_wait)
    runner.run_test("Atomic registry register/wait", test_atomic_registry_register_and_wait)
    runner.run_test("Atomic registry multi-key wait", test_atomic_registry_multiple_keys_wait)
    runner.run_test("Atomic registry remove object", test_atomic_registry_remove_object)
    runner.run_test("Atomic registry recovers closed handle", test_atomic_registry_recovers_closed_manager_handle)
    runner.run_test("CommandQueue roundtrip", test_command_queue_roundtrip)
    runner.run_test("SourceOfTruth basic", test_source_of_truth_basic)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
