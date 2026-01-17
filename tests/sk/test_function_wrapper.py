"""
Function Wrapper Tests

Tests retry/timeout/background helpers for Skfunction.
"""

from __future__ import annotations

import asyncio
import sys
import time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.sk._int.function_wrapper import (
    create_retry_wrapper,
    create_async_retry_wrapper,
    create_timeout_wrapper,
    create_async_timeout_wrapper,
    create_background_wrapper,
    create_async_wrapper,
    create_async_timeout_wrapper_v2,
    create_async_retry_wrapper_v2,
    FunctionTimeoutError,
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
        return failed == 0


# =============================================================================
# Wrapper Tests
# =============================================================================

def test_retry_wrapper_success():
    """Retry wrapper should succeed after failures."""
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("fail")
        return "ok"

    wrapped = create_retry_wrapper(flaky, times=3, delay=0.01, factor=1.0)
    assert wrapped() == "ok"
    assert calls["count"] == 3


def test_retry_wrapper_exhausted():
    """Retry wrapper should raise after all attempts."""
    def always_fail():
        raise RuntimeError("nope")

    wrapped = create_retry_wrapper(always_fail, times=2, delay=0.01, factor=1.0)
    try:
        wrapped()
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


def test_async_retry_wrapper():
    """Async retry wrapper should succeed after retries."""
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 2:
            raise ValueError("fail")
        return "ok"

    async def run():
        wrapped = create_async_retry_wrapper(flaky, times=3, delay=0.01, factor=1.0)
        return await wrapped()

    assert asyncio.run(run()) == "ok"


def test_timeout_wrapper_raises():
    """Timeout wrapper should raise FunctionTimeoutError."""
    def slow():
        time.sleep(0.2)
        return "done"

    wrapped = create_timeout_wrapper(slow, seconds=0.05)
    try:
        wrapped()
        assert False, "Expected timeout"
    except FunctionTimeoutError:
        pass


def test_timeout_wrapper_success():
    """Timeout wrapper should return when fast."""
    wrapped = create_timeout_wrapper(lambda: "ok", seconds=0.2)
    assert wrapped() == "ok"


def test_async_timeout_wrapper_raises():
    """Async timeout wrapper should raise FunctionTimeoutError."""
    def slow():
        time.sleep(0.2)
        return "done"

    async def run():
        wrapped = create_async_timeout_wrapper(slow, seconds=0.05)
        await wrapped()

    try:
        asyncio.run(run())
        assert False, "Expected timeout"
    except FunctionTimeoutError:
        pass


def test_background_wrapper():
    """Background wrapper should return Future with result."""
    wrapped = create_background_wrapper(lambda x: x + 1)
    future = wrapped(2)
    assert future.result(timeout=1) == 3


def test_async_wrapper():
    """Async wrapper should run sync function in thread."""
    async def run():
        wrapped = create_async_wrapper(lambda x: x * 2)
        return await wrapped(3)

    assert asyncio.run(run()) == 6


def test_async_timeout_wrapper_v2():
    """Async timeout v2 should time out async functions."""
    async def slow_async():
        await asyncio.sleep(0.2)
        return "ok"

    async def run():
        wrapped = create_async_timeout_wrapper_v2(slow_async, seconds=0.05)
        await wrapped()

    try:
        asyncio.run(run())
        assert False, "Expected timeout"
    except FunctionTimeoutError:
        pass


def test_async_retry_wrapper_v2():
    """Async retry v2 should succeed after retries."""
    calls = {"count": 0}

    async def flaky_async():
        calls["count"] += 1
        if calls["count"] < 2:
            raise ValueError("fail")
        return "ok"

    async def run():
        wrapped = create_async_retry_wrapper_v2(flaky_async, times=3, delay=0.01, factor=1.0)
        return await wrapped()

    assert asyncio.run(run()) == "ok"


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all function wrapper tests."""
    runner = TestRunner("Function Wrapper Tests")

    runner.run_test("Retry wrapper success", test_retry_wrapper_success)
    runner.run_test("Retry wrapper exhausted", test_retry_wrapper_exhausted)
    runner.run_test("Async retry wrapper", test_async_retry_wrapper)
    runner.run_test("Timeout wrapper raises", test_timeout_wrapper_raises)
    runner.run_test("Timeout wrapper success", test_timeout_wrapper_success)
    runner.run_test("Async timeout wrapper raises", test_async_timeout_wrapper_raises)
    runner.run_test("Background wrapper", test_background_wrapper)
    runner.run_test("Async wrapper", test_async_wrapper)
    runner.run_test("Async timeout v2", test_async_timeout_wrapper_v2)
    runner.run_test("Async retry v2", test_async_retry_wrapper_v2)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
