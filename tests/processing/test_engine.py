"""
Engine Tests

Covers internal engine helpers for running Skprocess lifecycle.
"""

from __future__ import annotations

import sys
import multiprocessing
import time
import io
import contextlib

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise import cerial
from suitkaise.processing import Process
from suitkaise.processing._int.engine import (
    _engine_main,
    _engine_main_inner,
    _run_finish_sequence,
    _send_error,
    _should_continue,
    _run_section_timed,
)
from suitkaise.processing._int.errors import RunError, ResultError
from suitkaise.processing._int.timers import ProcessTimers
from suitkaise.processing._int.process_class import Skprocess

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
        return failed == 0


# =============================================================================
# Process Fixtures
# =============================================================================

class EngineSuccessProcess(Process):
    def __init__(self):
        self.value = 0
        self.process_config.runs = 1

    def __prerun__(self):
        self.value += 1

    def __run__(self):
        self.value += 2

    def __postrun__(self):
        self.value += 3

    def __onfinish__(self):
        self.value += 4

    def __result__(self):
        return self.value

    def __error__(self):
        return {"error": str(self.error)}


class EngineFailOnceProcess(Process):
    def __init__(self):
        self.attempts = 0
        self.process_config.runs = 1
        self.process_config.lives = 2

    def __run__(self):
        self.attempts += 1
        if self.attempts == 1:
            raise ValueError("fail once")

    def __result__(self):
        return self.attempts


class EngineResultErrorProcess(Process):
    def __init__(self):
        self.process_config.runs = 1

    def __run__(self):
        return None

    def __result__(self):
        raise ValueError("bad result")


class EngineErrorHandlerProcess(Process):
    def __init__(self):
        self.process_config.runs = 1

    def __run__(self):
        raise ValueError("boom")

    def __result__(self):
        return "never"

    def __error__(self):
        raise RuntimeError("error handler failed")


# =============================================================================
# Engine Tests
# =============================================================================

def test_engine_success_flow():
    """Engine should run full lifecycle and return result."""
    proc = EngineSuccessProcess()
    serialized = cerial.serialize(proc)
    stop_event = multiprocessing.Event()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    _engine_main_inner(serialized, stop_event, result_queue, serialized)
    result = result_queue.get(timeout=2.0)

    assert result["type"] == "result"
    assert cerial.deserialize(result["data"]) == 10


def test_engine_retry_on_failure():
    """Engine should retry when lives remain."""
    proc = EngineFailOnceProcess()
    serialized = cerial.serialize(proc)
    stop_event = multiprocessing.Event()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    _engine_main_inner(serialized, stop_event, result_queue, serialized)
    result = result_queue.get(timeout=2.0)

    assert result["type"] == "result"
    assert cerial.deserialize(result["data"]) == 2


def test_run_finish_sequence_result_error():
    """_run_finish_sequence should send error on result failure."""
    proc = EngineResultErrorProcess()
    proc.timers = ProcessTimers()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()

    _run_finish_sequence(proc, stop_event, result_queue)
    result = result_queue.get(timeout=2.0)

    assert result["type"] == "error"
    err = cerial.deserialize(result["data"])
    assert isinstance(err, (Exception, ResultError))


def test_send_error_fallback():
    """_send_error should fall back to original error if handler fails."""
    proc = EngineErrorHandlerProcess()
    proc.timers = ProcessTimers()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()

    _send_error(proc, ValueError("boom"), result_queue)
    result = result_queue.get(timeout=2.0)

    assert result["type"] == "error"
    err = cerial.deserialize(result["data"])
    assert isinstance(err, Exception)


def test_run_section_timed_wraps_error():
    """_run_section_timed wraps errors with RunError."""
    proc = EngineSuccessProcess()
    proc.timers = ProcessTimers()
    proc.process_config.timeouts.run = None
    proc._current_run = 0
    proc._stop_event = multiprocessing.Event()

    def bad_run():
        raise ValueError("bad")

    proc.__run__ = bad_run
    try:
        _run_section_timed(proc, "__run__", "run", RunError, proc._stop_event)
        assert False, "Expected RunError"
    except RunError as e:
        assert isinstance(e.original_error, ValueError)


def test_run_section_timed_uses_timed_method():
    """_run_section_timed should unwrap TimedMethod wrappers."""
    proc = EngineSuccessProcess()
    proc.timers = ProcessTimers()
    proc.process_config.timeouts.run = None
    proc._current_run = 0
    proc._stop_event = multiprocessing.Event()
    Skprocess._setup_timed_methods(proc)
    _run_section_timed(proc, "__run__", "run", RunError, proc._stop_event)
    assert proc.timers.run.num_times == 1


def test_engine_main_error_reporting():
    """_engine_main should report errors to result queue."""
    stop_event = multiprocessing.Event()
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    with contextlib.redirect_stderr(io.StringIO()):
        _engine_main(b"bad", stop_event, result_queue, b"bad")
    result = result_queue.get(timeout=2.0)
    assert result["type"] == "error"


def test_should_continue_conditions():
    """_should_continue should stop on stop_event, runs, or join_in."""
    proc = EngineSuccessProcess()
    proc.process_config.runs = 1
    proc._current_run = 1

    stop_event = multiprocessing.Event()
    stop_event.set()
    assert _should_continue(proc, stop_event) is False

    stop_event.clear()
    assert _should_continue(proc, stop_event) is False

    proc.process_config.runs = None
    proc.process_config.join_in = 0.01
    proc._start_time = time.time() - 1.0
    assert _should_continue(proc, stop_event) is False


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all engine tests."""
    runner = TestRunner("Engine Tests")

    runner.run_test("Engine success flow", test_engine_success_flow)
    runner.run_test("Engine retry on failure", test_engine_retry_on_failure)
    runner.run_test("Finish sequence result error", test_run_finish_sequence_result_error)
    runner.run_test("Error handler fallback", test_send_error_fallback)
    runner.run_test("Section timed wraps error", test_run_section_timed_wraps_error)
    runner.run_test("Section timed unwraps TimedMethod", test_run_section_timed_uses_timed_method)
    runner.run_test("Engine main error reporting", test_engine_main_error_reporting)
    runner.run_test("Should continue conditions", test_should_continue_conditions)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
