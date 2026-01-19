"""
Timeout Utilities Tests

Tests run_with_timeout and internal timeout implementations.
"""

from __future__ import annotations

import sys
import time
import signal

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing._int.timeout import (
    run_with_timeout,
    _signal_based_timeout,
    _thread_based_timeout,
)
from suitkaise.processing._int.errors import ProcessTimeoutError

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
# Timeout Tests
# =============================================================================

def _fast_result():
    return "ok"


def _slow_sleep(seconds: float):
    time.sleep(seconds)
    return "done"


def test_run_with_timeout_none():
    """run_with_timeout should allow no timeout."""
    result = run_with_timeout(_fast_result, None, "run", 1)
    assert result == "ok"


def test_signal_based_timeout_raises():
    """Signal timeout should raise ProcessTimeoutError."""
    if not hasattr(signal, "SIGALRM"):
        # Windows does not support SIGALRM
        return
    try:
        _signal_based_timeout(lambda: _slow_sleep(1.5), 1.0, "run", 2)
        assert False, "Expected timeout"
    except ProcessTimeoutError as e:
        assert e.section == "run"


def test_thread_based_timeout_raises():
    """Thread timeout should raise ProcessTimeoutError."""
    try:
        _thread_based_timeout(lambda: _slow_sleep(0.2), 0.05, "run", 3)
        assert False, "Expected timeout"
    except ProcessTimeoutError as e:
        assert e.section == "run"


def test_thread_based_timeout_success():
    """Thread timeout should return result when fast."""
    result = _thread_based_timeout(lambda: _fast_result(), 0.2, "run", 4)
    assert result == "ok"


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all timeout tests."""
    runner = TestRunner("Timeout Utilities Tests")

    runner.run_test("run_with_timeout no timeout", test_run_with_timeout_none)
    runner.run_test("signal timeout raises", test_signal_based_timeout_raises)
    runner.run_test("thread timeout raises", test_thread_based_timeout_raises)
    runner.run_test("thread timeout success", test_thread_based_timeout_success)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
