"""
Share Proxy Tests

Exercises Share, coordinator, and proxy behaviors.
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

from suitkaise.processing import Share
from suitkaise.processing._int.share.proxy import _ObjectProxy
from suitkaise.processing._int.share.coordinator import _Coordinator

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
# Shared Objects
# =============================================================================

class Counter:
    _shared_meta = {
        "methods": {"inc": {"writes": ["value"]}},
        "properties": {"value": {"reads": ["value"]}},
    }

    def __init__(self):
        self.value = 0
        self.note = "hi"

    def inc(self, amount: int = 1) -> None:
        self.value += amount


# =============================================================================
# Proxy Tests
# =============================================================================

def test_share_proxy_method_and_property():
    """Proxy should queue method and allow property reads."""
    share = Share()
    try:
        share.counter = Counter()
        share.counter.inc(2)
        # Allow coordinator to process
        time.sleep(0.1)
        assert share.counter.value == 2
    finally:
        share.stop()


def test_share_proxy_setattr():
    """Proxy setattr should queue and commit updates."""
    share = Share()
    try:
        share.counter = Counter()
        share.counter.note = "updated"
        time.sleep(0.1)
        assert share.counter.note == "updated"
    finally:
        share.stop()


def test_share_non_proxy_value():
    """Non-proxy values should be stored directly."""
    share = Share()
    try:
        share.count = 5
        assert share.count == 5
        share.count = 7
        assert share.count == 7
    finally:
        share.stop()


def test_share_clear_and_repr():
    """Share should clear objects and provide repr."""
    share = Share()
    try:
        share.value = 1
        assert "Share(" in repr(share)
        share.clear()
        try:
            _ = share.value
            assert False, "Expected missing attribute"
        except AttributeError:
            pass
    finally:
        share.stop()


def test_share_serialize_deserialize():
    """Share should serialize and deserialize objects."""
    share = Share()
    try:
        share.counter = Counter()
        state = share.__serialize__()
        restored = Share.__deserialize__(state)
        try:
            assert hasattr(restored, "counter")
        finally:
            restored.stop()
    finally:
        share.stop()


# =============================================================================
# Coordinator/Proxy Direct Tests
# =============================================================================

def test_object_proxy_fallback_attr():
    """Object proxy should read non-meta attrs through coordinator."""
    coordinator = _Coordinator()
    coordinator.start()
    try:
        obj = Counter()
        coordinator.register_object("counter", obj, attrs={"value"})
        proxy = _ObjectProxy("counter", coordinator, type(obj))
        assert proxy.note == "hi"
    finally:
        coordinator.stop()


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all share proxy tests."""
    runner = TestRunner("Share Proxy Tests")

    runner.run_test("Proxy method/property", test_share_proxy_method_and_property)
    runner.run_test("Proxy setattr", test_share_proxy_setattr)
    runner.run_test("Non-proxy value", test_share_non_proxy_value)
    runner.run_test("Share clear/repr", test_share_clear_and_repr)
    runner.run_test("Share serialize/deserialize", test_share_serialize_deserialize)
    runner.run_test("Proxy fallback attr", test_object_proxy_fallback_attr)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
