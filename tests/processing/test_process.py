"""
Process Class Tests

Tests Process functionality:
- Basic lifecycle (__run__, __result__, __error__)
- start/wait/result pattern
- Error handling
- Timing
- Parallel execution
"""

import sys
import time
import signal
import multiprocessing
import socket
import sqlite3
import subprocess
import re

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing import Skprocess, ProcessError, RunError, auto_reconnect
from suitkaise.processing._int.process_class import Skprocess

Process = Skprocess
from suitkaise.processing._int.timers import ProcessTimers
from suitkaise import cerial
from suitkaise.cerial._int.handlers.reconnector import Reconnector
from suitkaise.cerial._int.handlers.network_handler import DbReconnector, SocketReconnector
from suitkaise.cerial._int.handlers.pipe_handler import PipeReconnector
from suitkaise.cerial._int.handlers.threading_handler import ThreadReconnector
from suitkaise.cerial._int.handlers.subprocess_handler import SubprocessReconnector
from suitkaise.cerial._int.handlers.regex_handler import MatchReconnector, MatchObjectHandler

# Import test classes from separate module for multiprocessing compatibility
from tests.processing.test_process_classes import (
    SimpleProcess, SlowProcess, FailingProcess, ProcessWithCallbacks,
    InfiniteCounterProcess, LimitedCounterProcess, HangingProcess,
    SelfStoppingProcess
)


# =============================================================================
# Process Subclasses for Retry/Restart Tests
# =============================================================================

class ProgressRetryProcess(Process):
    """Process that fails once mid-run then continues, preserving progress."""
    def __init__(self):
        self.progress: list[tuple[int, int, str]] = []
        self.run_calls = 0
        self.process_config.runs = 3
        self.process_config.lives = 2

    def __run__(self):
        self.run_calls += 1
        self.progress.append((self._current_run, self.run_calls, "start"))
        if self.run_calls == 2:
            self.progress.append((self._current_run, self.run_calls, "failed"))
            raise ValueError("intentional failure")
        time.sleep(0.02)

    def __result__(self):
        return {
            "progress": self.progress,
            "run_calls": self.run_calls,
            "current_run": self._current_run,
        }


class WaitRetryProcess(Process):
    """Process that fails once, then succeeds after retry."""
    def __init__(self):
        self.attempts = 0
        self.process_config.runs = 1
        self.process_config.lives = 2

    def __run__(self):
        self.attempts += 1
        time.sleep(0.2)
        if self.attempts == 1:
            raise ValueError("first attempt failure")
        time.sleep(0.2)

    def __result__(self):
        return self.attempts


# =============================================================================
# Serialization and Internal Behavior Tests (no subprocess)
# =============================================================================

class NoInitProcess(Process):
    """Process subclass without __init__ to hit default __init__ wrapper."""
    def __run__(self):
        return None


class UserStateProcess(Process):
    """Process with custom serialize/deserialize for user state restoration."""
    def __init__(self):
        self.value = 2
        self.process_config.runs = 1

    def __run__(self):
        return None

    def __serialize__(self):
        return {"value": self.value, "flag": "user"}

    @classmethod
    def __deserialize__(cls, state):
        obj = cls.__new__(cls)
        obj.value = state["value"] + 1
        obj.user_flag = state["flag"]
        return obj


class StaticUserStateProcess(Process):
    """Process with staticmethod deserialize to hit staticmethod branch."""
    def __init__(self):
        self.value = 5
        self.process_config.runs = 1

    def __run__(self):
        return None

    def __serialize__(self):
        return {"value": self.value}

    @staticmethod
    def __deserialize__(cls, state):
        obj = cls.__new__(cls)
        obj.value = state["value"] * 2
        obj.static_flag = "static"
        return obj


class _DummyReconnector(Reconnector):
    def __init__(self, value: str):
        self.value = value
    def reconnect(self, **kwargs):
        return f"connected-{self.value}"


@auto_reconnect()
class AutoReconnectProcess(Process):
    """Process that auto-reconnects Reconnector fields on deserialize."""
    def __init__(self):
        self.resource = _DummyReconnector("alpha")
        self.nested = {"item": _DummyReconnector("beta")}
        self.process_config.runs = 1


@auto_reconnect()
class AutoReconnectProcessAll(Process):
    """Process that auto-reconnects multiple reconnector types."""
    def __init__(self):
        match = re.search(r"a(b)c", "zabc")
        self.reconnectors = {
            "pipe": PipeReconnector(),
            "socket": SocketReconnector(state={
                "family": socket.AF_INET,
                "type": socket.SOCK_STREAM,
                "proto": 0,
                "timeout": None,
                "blocking": True,
                "local_addr": None,
                "remote_addr": None,
            }),
            "db": DbReconnector(module="sqlite3", class_name="Connection", details={"path": ":memory:"}),
            "proc": SubprocessReconnector(state={
                "args": [sys.executable, "-c", "print('x')"],
                "returncode": 0,
                "pid": 123,
                "poll_result": 0,
                "stdout_data": None,
                "stderr_data": None,
            }),
            "match": MatchReconnector(state=MatchObjectHandler().extract_state(match)),
            "thread": ThreadReconnector(state={
                "name": "worker",
                "daemon": True,
                "target": lambda: None,
                "args": (),
                "kwargs": {},
                "is_alive": False,
            }),
        }
        self.process_config.runs = 1


class BadSignatureDeserializeProcess(Process):
    """Process with invalid deserialize signature to hit fallback branch."""
    def __init__(self):
        self.value = 7
        self.process_config.runs = 1

    def __run__(self):
        return None

    def __serialize__(self):
        return {"value": self.value}

    def __deserialize__(state):  # type: ignore[no-redef]
        obj = BadSignatureDeserializeProcess.__new__(BadSignatureDeserializeProcess)
        obj.value = state["value"] + 3
        obj.fallback_flag = "fallback"
        return obj


class DummySubprocess:
    def __init__(self, alive: bool):
        self._alive = alive

    def is_alive(self):
        return self._alive


class DummyQueueEmpty:
    def get(self, timeout=None):
        import queue as queue_module
        raise queue_module.Empty


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
        
        # Set up timeout (Unix only)
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
        except (AttributeError, ValueError):
            pass  # Windows or other issue
        
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
            # Disable alarm
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
# Class Structure Tests
# =============================================================================

def test_process_import():
    """Process should be importable."""
    assert Process is not None


def test_process_creation():
    """Process should be creatable."""
    proc = SimpleProcess(5)
    
    assert proc is not None
    assert proc.value == 5


def test_process_has_run_method():
    """Process should have __run__ method."""
    proc = SimpleProcess(5)
    
    assert hasattr(proc, '__run__')
    assert callable(proc.__run__)


def test_process_has_result_method():
    """Process should have __result__ method."""
    proc = SimpleProcess(5)
    
    assert hasattr(proc, '__result__')
    assert callable(proc.__result__)


def test_process_has_start_method():
    """Process should have start() method."""
    proc = SimpleProcess(5)
    
    assert hasattr(proc, 'start')
    assert callable(proc.start)


def test_process_has_wait_method():
    """Process should have wait() method."""
    proc = SimpleProcess(5)
    
    assert hasattr(proc, 'wait')
    assert callable(proc.wait)


def test_process_has_result_accessor():
    """Process should have result() method."""
    proc = SimpleProcess(5)
    
    assert hasattr(proc, 'result')
    assert callable(proc.result)


def test_process_has_run_helper():
    """Process should have run() helper method."""
    proc = SimpleProcess(5)
    
    assert hasattr(proc, 'run')
    assert callable(proc.run)


# =============================================================================
# Error Class Tests
# =============================================================================

def test_process_error_exists():
    """ProcessError should exist."""
    assert ProcessError is not None


def test_run_error_exists():
    """RunError should exist."""
    assert RunError is not None


def test_process_error_inheritance():
    """ProcessError should be an Exception."""
    assert issubclass(ProcessError, Exception)


# =============================================================================
# Direct Run Tests (no subprocess)
# =============================================================================

def test_process_run_directly():
    """Process __run__ can be called directly."""
    proc = SimpleProcess(5)
    
    proc.__run__()
    
    assert proc._result_value == 10


def test_process_result_directly():
    """Process __result__ can be called after __run__."""
    proc = SimpleProcess(5)
    
    proc.__run__()
    result = proc.__result__()
    
    assert result == 10


def test_process_callbacks_direct():
    """Process callbacks can be called directly."""
    proc = ProcessWithCallbacks()
    
    # Simulate the lifecycle (correct method names)
    proc.__prerun__()
    proc.__run__()
    result = proc.__result__()
    proc.__onfinish__()
    
    assert proc.pre_run_called
    assert proc.run_called
    assert result == "completed"


def test_process_default_init_wrapper():
    """Process without __init__ should still get setup state."""
    proc = NoInitProcess()
    assert hasattr(proc, "process_config")
    assert proc._current_run == 0


def test_process_custom_serialize_deserialize_classmethod():
    """Custom classmethod deserialize should restore user state."""
    proc = UserStateProcess()
    data = cerial.serialize(proc)
    restored = cerial.deserialize(data)
    assert isinstance(restored, Skprocess)
    assert restored.user_flag == "user"
    assert restored.value == 2


def test_process_custom_serialize_deserialize_staticmethod():
    """Custom staticmethod deserialize should restore user state."""
    proc = StaticUserStateProcess()
    data = cerial.serialize(proc)
    restored = cerial.deserialize(data)
    assert restored.static_flag == "static"


def test_process_custom_serialize_deserialize_fallback():
    """Fallback deserialize signature should still work."""
    proc = BadSignatureDeserializeProcess()
    data = cerial.serialize(proc)
    restored = cerial.deserialize(data)
    assert restored.fallback_flag == "fallback"


def test_process_auto_reconnect():
    """auto_reconnect should run reconnect_all during deserialization."""
    proc = AutoReconnectProcess()
    data = cerial.serialize(proc)
    restored = cerial.deserialize(data)
    assert restored.resource == "connected-alpha"
    assert restored.nested["item"] == "connected-beta"


def test_process_auto_reconnect_all_types():
    """auto_reconnect should reconnect all reconnector types."""
    proc = AutoReconnectProcessAll()
    data = cerial.serialize(proc)
    restored = cerial.deserialize(data)
    rec = restored.reconnectors
    assert hasattr(rec["pipe"], "send")
    assert isinstance(rec["socket"], socket.socket)
    assert isinstance(rec["db"], sqlite3.Connection)
    assert isinstance(rec["proc"], subprocess.Popen)
    assert isinstance(rec["match"], re.Match)
    assert isinstance(rec["thread"], threading.Thread)
    # Cleanup
    try:
        rec["proc"].wait(timeout=5)
    except Exception:
        try:
            rec["proc"].terminate()
        except Exception:
            pass
    rec["socket"].close()
    rec["db"].close()
    try:
        rec["pipe"].close()
    except Exception:
        pass


def test_process_drain_result_queue_error_non_exception():
    """_drain_result_queue should wrap non-exception errors."""
    proc = SimpleProcess(1)
    proc._result_queue = multiprocessing.Queue()
    proc._has_result = False
    message = {
        "type": "error",
        "data": cerial.serialize("oops"),
        "timers": None,
    }
    proc._result_queue.put(message)
    proc._drain_result_queue()
    assert proc._has_result is True
    assert isinstance(proc._result, ProcessError)


def test_process_drain_result_queue_empty_noop():
    """_drain_result_queue should ignore Empty."""
    proc = SimpleProcess(1)
    proc._result_queue = DummyQueueEmpty()
    proc._has_result = False
    proc._drain_result_queue()
    assert proc._has_result is False


def test_process_tell_listen_errors():
    """tell/listen should error when process not started."""
    proc = SimpleProcess(1)
    try:
        proc.tell("data")
        assert False, "Expected RuntimeError on tell without start"
    except RuntimeError:
        pass
    try:
        proc.listen()
        assert False, "Expected RuntimeError on listen without start"
    except RuntimeError:
        pass


def test_process_listen_empty_returns_none():
    """listen should return None on timeout/empty."""
    proc = SimpleProcess(1)
    proc._listen_queue = DummyQueueEmpty()
    assert proc.listen(timeout=0.01) is None


def test_process_wait_without_subprocess():
    """wait should return True if no subprocess exists."""
    proc = SimpleProcess(1)
    proc._subprocess = None
    assert proc.wait() is True


def test_process_properties():
    """process_timer/current_run/is_alive should reflect state."""
    proc = SimpleProcess(1)
    proc.timers = None
    assert proc.process_timer is None
    proc.timers = ProcessTimers()
    assert proc.process_timer is proc.timers.full_run
    proc._current_run = 4
    assert proc.current_run == 4
    proc._subprocess = DummySubprocess(alive=True)
    assert proc.is_alive is True


def test_process_failing_run():
    """Failing process should raise exception."""
    proc = FailingProcess("test failure")
    
    try:
        proc.__run__()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "test failure" in str(e)


# =============================================================================
# Actual Subprocess Tests
# =============================================================================

def test_process_actual_run():
    """Process should run in actual subprocess."""
    proc = SimpleProcess(5)
    proc.start()
    proc.wait(timeout=5.0)
    
    result = proc.result()
    
    assert result == 10


def test_process_result():
    """Process.result() should return __result__."""
    proc = SimpleProcess(10)
    proc.start()
    proc.wait(timeout=5.0)
    
    result = proc.result()
    
    assert result == 20


def test_process_run_helper_returns_result():
    """run() should start, wait, and return result."""
    proc = SimpleProcess(7)
    
    result = proc.run()
    
    assert result == 14


def test_process_slow_run():
    """Process should handle slow operations."""
    proc = SlowProcess(0.1)  # 100ms
    
    start = time.perf_counter()
    proc.start()
    proc.wait(timeout=5.0)
    elapsed = time.perf_counter() - start
    
    assert elapsed >= 0.09, f"Should take ~100ms, got {elapsed}"
    assert proc.result() == "done"


def test_process_start_returns_immediately():
    """Process.start() should return without blocking."""
    proc = SlowProcess(0.5)  # 500ms
    
    start = time.perf_counter()
    proc.start()
    start_time = time.perf_counter() - start
    
    # start() should return quickly (< 100ms)
    assert start_time < 0.1, f"start() should be fast, took {start_time}"
    
    proc.wait(timeout=5.0)
    proc.result()  # Clean up


def test_process_error_propagates():
    """Process errors should propagate on result()."""
    proc = FailingProcess("test failure")
    proc.start()
    proc.wait(timeout=5.0)
    
    try:
        proc.result()
        assert False, "Should have raised error"
    except ProcessError:
        pass  # Expected


def test_multiple_processes():
    """Multiple processes should run independently."""
    procs = [SimpleProcess(i) for i in range(5)]
    
    for p in procs:
        p.start()
    
    for p in procs:
        p.wait(timeout=5.0)
    
    results = [p.result() for p in procs]
    
    assert results == [0, 2, 4, 6, 8]


def test_concurrent_processes():
    """Concurrent processes should run in parallel."""
    # 5 processes, each sleeps 100ms
    procs = [SlowProcess(0.1) for _ in range(5)]
    
    start = time.perf_counter()
    
    for p in procs:
        p.start()
    
    for p in procs:
        p.wait(timeout=5.0)
    
    elapsed = time.perf_counter() - start
    
    # Windows process startup is slower; allow a larger threshold there
    max_elapsed = 1.0 if sys.platform == "win32" else 0.4
    # Should complete in ~100-200ms (parallel), not 500ms (sequential)
    assert elapsed < max_elapsed, f"Concurrent should be ~100ms, got {elapsed}"


def test_process_progress_preserved_on_retry():
    """Progress should persist across a failed run retry."""
    proc = ProgressRetryProcess()
    proc.start()
    proc.wait(timeout=10.0)
    result = proc.result()

    progress = result["progress"]
    run_calls = result["run_calls"]
    current_run = result["current_run"]

    assert run_calls == 4, f"Expected 4 run calls, got {run_calls}"
    assert current_run == 3, f"Expected 3 successful runs, got {current_run}"
    assert any(entry[2] == "failed" for entry in progress), "Failure marker missing"
    failed_idx = next(i for i, entry in enumerate(progress) if entry[2] == "failed")
    failed_run = progress[failed_idx][0]
    assert any(
        i > failed_idx and entry[0] == failed_run and entry[2] == "start"
        for i, entry in enumerate(progress)
    ), "Retry should occur on same run index"
    assert progress[-1][0] == 2, "Final run should be the last run index"


def test_wait_blocks_until_retry_success():
    """wait() should not return until a retry succeeds."""
    proc = WaitRetryProcess()
    start = time.perf_counter()
    proc.start()
    finished = proc.wait(timeout=10.0)
    elapsed = time.perf_counter() - start

    assert finished, "wait() should return True after successful retry"
    assert elapsed >= 0.35, f"wait() returned too early ({elapsed:.3f}s)"
    assert proc.result() == 2, "Process should have retried once"


# =============================================================================
# Stop and Kill Tests
# =============================================================================

def test_stop_infinite_process():
    """stop() should gracefully stop an infinitely running process."""
    proc = InfiniteCounterProcess()
    proc.start()
    
    # Let it run for a bit (longer to allow for subprocess startup)
    time.sleep(0.3)
    
    # Stop it
    proc.stop()
    
    # Wait for it to finish
    proc.wait(timeout=5.0)
    
    # Should have counted some iterations
    result = proc.result()
    assert result >= 1, f"Should have counted at least once, got {result}"


def test_stop_limited_process():
    """stop() should gracefully stop a limited process early."""
    proc = LimitedCounterProcess(1000)  # Would take 10+ seconds normally
    proc.start()
    
    # Let it run for a bit (200ms to allow for subprocess startup)
    time.sleep(0.2)
    
    # Stop it early
    proc.stop()
    
    # Wait for it to finish
    proc.wait(timeout=5.0)
    
    # Should have counted some, but not all 1000
    result = proc.result()
    assert result >= 1, f"Should have counted at least once, got {result}"
    assert result < 1000, f"Should not have reached limit, got {result}"


def test_stop_returns_immediately():
    """stop() should return immediately without blocking."""
    proc = InfiniteCounterProcess()
    proc.start()
    
    # Let it run for a bit
    time.sleep(0.05)
    
    # stop() should be non-blocking
    start = time.perf_counter()
    proc.stop()
    stop_time = time.perf_counter() - start
    
    assert stop_time < 0.05, f"stop() should be instant, took {stop_time}"
    
    # Clean up
    proc.wait(timeout=5.0)


def test_kill_hanging_process():
    """kill() should forcefully terminate a hanging process."""
    proc = HangingProcess()
    proc.start()
    
    # Wait a bit for it to start
    time.sleep(0.1)
    
    # Process should be alive
    assert proc.is_alive, "Process should be running"
    
    # Kill it
    start = time.perf_counter()
    proc.kill()
    kill_time = time.perf_counter() - start
    
    # kill() should complete relatively quickly (within 6 seconds including join timeout)
    assert kill_time < 7, f"kill() should complete quickly, took {kill_time}"
    
    # Process should be dead
    assert not proc.is_alive, "Process should be dead after kill()"


def test_kill_running_process():
    """kill() should forcefully terminate a running process."""
    proc = InfiniteCounterProcess()
    proc.start()
    
    # Let it run for a bit
    time.sleep(0.1)
    
    # Kill it
    proc.kill()
    
    # Process should be dead
    assert not proc.is_alive, "Process should be dead after kill()"


def test_stop_then_result():
    """After stop(), result() should return the final state."""
    proc = InfiniteCounterProcess()
    proc.start()
    
    # Let it run for a bit (longer to allow for subprocess startup)
    time.sleep(0.3)
    
    # Stop it
    proc.stop()
    proc.wait(timeout=5.0)
    
    # Should be able to get result
    result = proc.result()
    assert isinstance(result, int), f"Result should be int, got {type(result)}"
    assert result >= 1, f"Should have counted at least once, got {result}"


def test_self_stopping_process():
    """A process should be able to stop itself by calling self.stop()."""
    target_count = 5
    proc = SelfStoppingProcess(target=target_count)
    proc.start()
    
    # Wait for it to finish (it should stop itself)
    proc.wait(timeout=5.0)
    
    # Should have reached exactly the target count
    result = proc.result()
    assert result == target_count, f"Should have counted to {target_count}, got {result}"


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all Process tests."""
    runner = TestRunner("Process Class Tests")
    
    # Class structure tests (fast, no subprocess)
    runner.run_test("Process import", test_process_import)
    runner.run_test("Process creation", test_process_creation)
    runner.run_test("Process has __run__", test_process_has_run_method)
    runner.run_test("Process has __result__", test_process_has_result_method)
    runner.run_test("Process has start()", test_process_has_start_method)
    runner.run_test("Process has wait()", test_process_has_wait_method)
    runner.run_test("Process has result()", test_process_has_result_accessor)
    runner.run_test("Process has run()", test_process_has_run_helper)
    
    # Error class tests
    runner.run_test("ProcessError exists", test_process_error_exists)
    runner.run_test("RunError exists", test_run_error_exists)
    runner.run_test("ProcessError is Exception", test_process_error_inheritance)
    
    # Direct run tests (no subprocess, fast)
    runner.run_test("Process __run__ directly", test_process_run_directly)
    runner.run_test("Process __result__ directly", test_process_result_directly)
    runner.run_test("Process callbacks direct", test_process_callbacks_direct)
    runner.run_test("Process failing run", test_process_failing_run)
    runner.run_test("Default __init__ wrapper", test_process_default_init_wrapper)
    runner.run_test("Custom deserialize classmethod", test_process_custom_serialize_deserialize_classmethod)
    runner.run_test("Custom deserialize staticmethod", test_process_custom_serialize_deserialize_staticmethod)
    runner.run_test("Custom deserialize fallback", test_process_custom_serialize_deserialize_fallback)
    runner.run_test("Drain result queue error", test_process_drain_result_queue_error_non_exception)
    runner.run_test("Drain result queue empty", test_process_drain_result_queue_empty_noop)
    runner.run_test("tell/listen errors", test_process_tell_listen_errors)
    runner.run_test("listen empty returns None", test_process_listen_empty_returns_none)
    runner.run_test("wait without subprocess", test_process_wait_without_subprocess)
    runner.run_test("process properties", test_process_properties)
    
    # Actual subprocess tests (slower, may timeout in sandbox)
    runner.run_test("Process actual run", test_process_actual_run, timeout=10)
    runner.run_test("Process result", test_process_result, timeout=10)
    runner.run_test("Process run() helper", test_process_run_helper_returns_result, timeout=10)
    runner.run_test("Process slow run", test_process_slow_run, timeout=10)
    runner.run_test("Process.start() non-blocking", test_process_start_returns_immediately, timeout=10)
    runner.run_test("Process error propagates", test_process_error_propagates, timeout=10)
    runner.run_test("Multiple processes", test_multiple_processes, timeout=15)
    runner.run_test("Concurrent processes", test_concurrent_processes, timeout=15)
    runner.run_test("Progress preserved on retry", test_process_progress_preserved_on_retry, timeout=15)
    runner.run_test("wait() blocks until retry success", test_wait_blocks_until_retry_success, timeout=15)
    
    # Stop and kill tests
    runner.run_test("stop() infinite process", test_stop_infinite_process, timeout=10)
    runner.run_test("stop() limited process", test_stop_limited_process, timeout=10)
    runner.run_test("stop() returns immediately", test_stop_returns_immediately, timeout=10)
    runner.run_test("kill() hanging process", test_kill_hanging_process, timeout=15)
    runner.run_test("kill() running process", test_kill_running_process, timeout=10)
    runner.run_test("stop() then result()", test_stop_then_result, timeout=10)
    runner.run_test("self.stop() from within process", test_self_stopping_process, timeout=10)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
