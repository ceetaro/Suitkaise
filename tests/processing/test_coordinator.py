"""
Coordinator Tests

Exercises coordinator main loop and helper methods in-process.
"""

from __future__ import annotations

import sys
import threading
import time
import multiprocessing
import io
import contextlib

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import cerial
from suitkaise.processing._int.share.coordinator import _Coordinator, _coordinator_main
from suitkaise.processing._int.share.primitives import _AtomicCounterRegistry

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
# Test Objects
# =============================================================================

class Counter:
    def __init__(self):
        self.value = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount


# =============================================================================
# Coordinator Tests
# =============================================================================

def test_coordinator_register_get_queue():
    """Coordinator should register and retrieve objects."""
    coordinator = _Coordinator()
    coordinator.start()
    try:
        obj = Counter()
        coordinator.register_object("counter", obj, attrs={"value"})
        fetched = coordinator.get_object("counter")
        assert fetched.value == 0
        coordinator.queue_command("counter", "inc", (2,), {}, ["value"])
        # Give the coordinator time to process the queue (Windows can be slower)
        deadline = time.time() + (1.5 if sys.platform == "win32" else 0.5)
        while time.time() < deadline:
            if coordinator.get_object("counter").value == 2:
                break
            time.sleep(0.05)
        assert coordinator.get_object("counter").value == 2
    finally:
        coordinator.stop()


def test_coordinator_read_wait_and_clear():
    """Coordinator should wait for reads and clear."""
    coordinator = _Coordinator()
    coordinator.start()
    try:
        obj = Counter()
        coordinator.register_object("counter", obj, attrs={"value"})
        key = "counter.value"
        coordinator.increment_pending(key)
        assert coordinator.get_read_target(key) >= 1
        coordinator.queue_command("counter", "inc", (1,), {}, ["value"])
        ok = coordinator.wait_for_read([key], timeout=1.0)
        assert ok is True
        coordinator.clear()
    finally:
        coordinator.stop()


def test_coordinator_main_loop_in_process():
    """Coordinator main loop should process commands in-process."""
    manager = multiprocessing.Manager()
    command_queue = manager.Queue()
    source_store = manager.dict()
    source_lock = manager.Lock()
    stop_event = multiprocessing.Event()
    error_event = multiprocessing.Event()
    registry = _AtomicCounterRegistry(manager)
    registry.register_keys("counter", {"value"})

    obj = Counter()
    source_store["counter"] = cerial.serialize(obj)

    def _run():
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                _coordinator_main(
                    command_queue,
                    registry,
                    source_store,
                    source_lock,
                    stop_event,
                    error_event,
                    0.05,
                )
            except Exception:
                # _coordinator_main is expected to raise here; swallow to avoid thread error.
                pass

    thread = threading.Thread(
        target=_run,
        args=(
        ),
        daemon=True,
    )
    thread.start()

    command_queue.put(("counter", "inc", cerial.serialize((3,)), cerial.serialize({}), ["value"]))
    command_queue.put(("__clear__", None, None, None, None))
    command_queue.put(("missing", "inc", cerial.serialize((1,)), cerial.serialize({}), ["value"]))
    time.sleep(0.2)
    stop_event.set()
    thread.join(timeout=2)

    updated = cerial.deserialize(source_store["counter"])
    assert updated.value == 3
    registry.reset()
    manager.shutdown()


def test_coordinator_start_stop_idempotent():
    """Coordinator should handle repeated start/stop calls."""
    coordinator = _Coordinator()
    coordinator.start()
    coordinator.start()
    assert coordinator.is_alive is True
    assert coordinator.stop() is True
    assert coordinator.stop() is True


def test_coordinator_repr_error_state():
    """__repr__ should include error status when error flag is set."""
    coordinator = _Coordinator()
    coordinator._error_event = multiprocessing.Event()
    coordinator._error_event.set()
    text = repr(coordinator)
    assert "error" in text


def test_coordinator_main_sets_error_event():
    """Coordinator main should set error_event on fatal error."""
    manager = multiprocessing.Manager()
    command_queue = manager.Queue()
    source_store = manager.dict()
    source_lock = manager.Lock()
    stop_event = multiprocessing.Event()
    error_event = multiprocessing.Event()
    registry = _AtomicCounterRegistry(manager)
    registry.register_keys("counter", {"value"})

    def _run():
        with contextlib.redirect_stderr(io.StringIO()):
            _coordinator_main(
                command_queue,
                registry,
                source_store,
                source_lock,
                stop_event,
                error_event,
                0.05,
            )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    command_queue.put(("counter", "inc", b"bad", b"bad", ["value"]))
    time.sleep(0.2)
    assert error_event.is_set() is True
    stop_event.set()
    thread.join(timeout=1.0)
    registry.reset()
    manager.shutdown()


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all coordinator tests."""
    runner = TestRunner("Coordinator Tests")

    runner.run_test("Coordinator register/get/queue", test_coordinator_register_get_queue)
    runner.run_test("Coordinator read wait/clear", test_coordinator_read_wait_and_clear)
    runner.run_test("Coordinator main loop in-process", test_coordinator_main_loop_in_process)
    runner.run_test("Coordinator start/stop idempotent", test_coordinator_start_stop_idempotent)
    runner.run_test("Coordinator repr error state", test_coordinator_repr_error_state)
    runner.run_test("Coordinator main sets error event", test_coordinator_main_sets_error_event)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
