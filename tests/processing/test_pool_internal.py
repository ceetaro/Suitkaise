"""
Pool Internal Tests

Covers internal helpers in pool implementation.
"""

from __future__ import annotations

import sys
import time
import multiprocessing

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise import cerial
from suitkaise.processing._int.pool import _pool_worker, _run_process_inline, _ordered_results, _unordered_results
from suitkaise.processing import Process
from suitkaise.processing._int.errors import RunError, ProcessTimeoutError

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
# Helper Processes
# =============================================================================

class InlineProcess(Process):
    def __init__(self):
        self.process_config.runs = 2
        self.value = 0

    def __run__(self):
        self.value += 1

    def __result__(self):
        return self.value


class InlineFailProcess(Process):
    def __init__(self):
        self.process_config.runs = 1
        self.process_config.lives = 1

    def __run__(self):
        raise ValueError("fail")


class InlineTimeoutProcess(Process):
    def __init__(self):
        self.process_config.runs = 1
        self.process_config.timeouts.run = 1.0

    def __run__(self):
        time.sleep(2.0)


def _result_worker(q, value):
    q.put({"type": "result", "data": cerial.serialize(value)})


def _delayed_result_worker(q, delay, value):
    time.sleep(delay)
    q.put({"type": "result", "data": cerial.serialize(value)})


def _error_worker(q):
    q.put({"type": "error", "data": cerial.serialize(RuntimeError("boom"))})


class DoubleProcess(Process):
    def __init__(self, value):
        self.process_config.runs = 1
        self.value = value

    def __run__(self):
        self.value *= 2

    def __result__(self):
        return self.value


# =============================================================================
# Pool Helper Tests
# =============================================================================

def test_pool_worker_function():
    """_pool_worker should serialize result for function."""
    q = multiprocessing.Queue()
    _pool_worker(cerial.serialize(lambda x: x + 1), cerial.serialize(2), False, q)
    msg = q.get(timeout=1)
    assert msg["type"] == "result"
    assert cerial.deserialize(msg["data"]) == 3


def test_pool_worker_error():
    """_pool_worker should serialize errors."""
    q = multiprocessing.Queue()
    def boom(_):
        raise RuntimeError("boom")
    _pool_worker(cerial.serialize(boom), cerial.serialize(1), False, q)
    msg = q.get(timeout=1)
    assert msg["type"] == "error"


def test_run_process_inline_success():
    """_run_process_inline should run and return result."""
    proc = InlineProcess()
    result = _run_process_inline(proc)
    assert result == 2


def test_run_process_inline_error():
    """_run_process_inline should raise wrapped errors."""
    proc = InlineFailProcess()
    try:
        _run_process_inline(proc)
        assert False, "Expected error"
    except RunError:
        pass


def test_run_process_inline_timeout():
    """_run_process_inline should timeout when configured."""
    proc = InlineTimeoutProcess()
    try:
        _run_process_inline(proc)
        assert False, "Expected timeout"
    except ProcessTimeoutError:
        pass


def test_pool_worker_star():
    """_pool_worker should handle star args."""
    q = multiprocessing.Queue()
    def add(a, b):
        return a + b
    _pool_worker(cerial.serialize(add), cerial.serialize((2, 3)), True, q)
    msg = q.get(timeout=1)
    assert cerial.deserialize(msg["data"]) == 5


def test_pool_worker_process_class():
    """_pool_worker should handle Skprocess classes."""
    q = multiprocessing.Queue()
    _pool_worker(cerial.serialize(DoubleProcess), cerial.serialize(3), False, q)
    msg = q.get(timeout=1)
    assert cerial.deserialize(msg["data"]) == 6


def test_ordered_results():
    """_ordered_results should yield in order."""
    queues = []
    workers = []
    active = []

    for i in range(2):
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_result_worker, args=(q, i))
        p.start()
        queues.append(q)
        workers.append(p)
        active.append(p)

    results = list(_ordered_results(queues, workers, active, timeout=2))
    assert results == [0, 1]


def test_ordered_results_error():
    """_ordered_results should raise on error messages."""
    queues = []
    workers = []
    active = []
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_error_worker, args=(q,))
    p.start()
    queues.append(q)
    workers.append(p)
    active.append(p)
    try:
        list(_ordered_results(queues, workers, active, timeout=2))
        assert False, "Expected error"
    except Exception:
        pass


def test_unordered_results():
    """_unordered_results should yield results as ready."""
    queues = []
    workers = []
    active = []

    for delay, value in [(0.05, 1), (0.01, 2)]:
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=_delayed_result_worker, args=(q, delay, value))
        p.start()
        queues.append(q)
        workers.append(p)
        active.append(p)

    results = list(_unordered_results(queues, workers, active, timeout=2))
    assert sorted(results) == [1, 2]


def test_unordered_results_timeout():
    """_unordered_results should timeout when workers never finish."""
    queues = []
    workers = []
    active = []
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=_delayed_result_worker, args=(q, 1.0, 1))
    p.start()
    queues.append(q)
    workers.append(p)
    active.append(p)
    try:
        list(_unordered_results(queues, workers, active, timeout=0.05))
        assert False, "Expected timeout"
    except TimeoutError:
        pass


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all pool internal tests."""
    runner = TestRunner("Pool Internal Tests")

    runner.run_test("pool worker function", test_pool_worker_function)
    runner.run_test("pool worker error", test_pool_worker_error)
    runner.run_test("run process inline success", test_run_process_inline_success)
    runner.run_test("run process inline error", test_run_process_inline_error)
    runner.run_test("run process inline timeout", test_run_process_inline_timeout)
    runner.run_test("pool worker star", test_pool_worker_star)
    runner.run_test("pool worker process class", test_pool_worker_process_class)
    runner.run_test("ordered results", test_ordered_results)
    runner.run_test("ordered results error", test_ordered_results_error)
    runner.run_test("unordered results", test_unordered_results)
    runner.run_test("unordered results timeout", test_unordered_results_timeout)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
