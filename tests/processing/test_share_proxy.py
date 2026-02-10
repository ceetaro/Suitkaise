"""
Share Proxy Tests

Exercises Share, coordinator, and proxy behaviors.
"""

from __future__ import annotations

import sys
import time
import threading
import warnings

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


class MultiAttr:
    _shared_meta = {
        "methods": {
            "set_a": {"writes": ["a"]},
            "set_b": {"writes": ["b"]},
        },
        "properties": {
            "total": {"reads": ["a", "b"]},
        },
    }
    
    def __init__(self):
        self.a = 0
        self.b = 0
    
    def set_a(self, value: int) -> None:
        self.a = value
    
    def set_b(self, value: int) -> None:
        self.b = value
    
    @property
    def total(self) -> int:
        return self.a + self.b


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


def test_share_proxy_warns_when_stopped():
    """Proxy should warn when coordinator is stopped."""
    share = Share()
    try:
        share.counter = Counter()
        share.stop()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            share.counter.inc(1)
            share.counter.note = "stopped"
        assert any(issubclass(w.category, RuntimeWarning) for w in caught)
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


def test_share_proxy_read_barrier_multiple_attrs():
    """Proxy should wait for all read deps before property access."""
    share = Share()
    try:
        share.obj = MultiAttr()
        share.obj.set_a(2)
        share.obj.set_b(3)
        time.sleep(0.1)
        assert share.obj.total == 5
    finally:
        share.stop()


def test_share_proxy_concurrent_reads_and_writes():
    """Concurrent reads should not error during writes."""
    share = Share()
    try:
        share.obj = MultiAttr()
        errors = []
        
        def writer():
            for i in range(20):
                share.obj.set_a(i)
                share.obj.set_b(i)
        
        def reader():
            for _ in range(20):
                try:
                    _ = share.obj.total
                except Exception as e:
                    errors.append(e)
        
        threads = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        time.sleep(0.1)
        assert errors == []
        assert share.obj.total >= 0
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
# Sktimer Blocked Methods in Share
# =============================================================================

def test_sktimer_blocked_start():
    """Sktimer.start() should raise TypeError when accessed through Share proxy."""
    from suitkaise.timing import Sktimer
    share = Share()
    try:
        share.timer = Sktimer()
        try:
            share.timer.start()
            raise AssertionError("Expected TypeError for start()")
        except TypeError as e:
            assert "start()" in str(e)
            assert "add_time" in str(e)
    finally:
        share.stop()


def test_sktimer_blocked_stop():
    """Sktimer.stop() should raise TypeError when accessed through Share proxy."""
    from suitkaise.timing import Sktimer
    share = Share()
    try:
        share.timer = Sktimer()
        try:
            share.timer.stop()
            raise AssertionError("Expected TypeError for stop()")
        except TypeError as e:
            assert "stop()" in str(e)
    finally:
        share.stop()


def test_sktimer_blocked_pause_resume_lap_discard():
    """pause/resume/lap/discard should all raise TypeError through Share proxy."""
    from suitkaise.timing import Sktimer
    share = Share()
    try:
        share.timer = Sktimer()
        for method_name in ('pause', 'resume', 'lap', 'discard'):
            try:
                getattr(share.timer, method_name)()
                raise AssertionError(f"Expected TypeError for {method_name}()")
            except TypeError as e:
                assert method_name in str(e)
    finally:
        share.stop()


def test_sktimer_add_time_allowed():
    """Sktimer.add_time() should work through Share proxy."""
    from suitkaise.timing import Sktimer
    share = Share()
    try:
        share.timer = Sktimer()
        share.timer.add_time(1.5)
        share.timer.add_time(2.5)
        assert share.timer.num_times == 2
        assert abs(share.timer.mean - 2.0) < 0.01
    finally:
        share.stop()


def test_sktimer_read_properties_allowed():
    """Sktimer read properties should work through Share proxy."""
    from suitkaise.timing import Sktimer
    share = Share()
    try:
        share.timer = Sktimer()
        share.timer.add_time(3.0)
        assert share.timer.num_times == 1
        assert abs(share.timer.most_recent - 3.0) < 0.01
        assert abs(share.timer.total_time - 3.0) < 0.01
        assert abs(share.timer.mean - 3.0) < 0.01
    finally:
        share.stop()


def test_sktimer_reset_allowed():
    """Sktimer.reset() should work through Share proxy."""
    from suitkaise.timing import Sktimer
    share = Share()
    try:
        share.timer = Sktimer()
        share.timer.add_time(1.0)
        assert share.timer.num_times == 1
        share.timer.reset()
        assert share.timer.num_times == 0
    finally:
        share.stop()


def test_sktimer_read_methods_return_values():
    """Sktimer read-only methods (percentile, get_time, etc.) should return values, not None."""
    from suitkaise.timing import Sktimer
    share = Share()
    try:
        share.timer = Sktimer()
        share.timer.add_time(1.0)
        share.timer.add_time(2.0)
        share.timer.add_time(3.0)

        # percentile() must return a float, not None
        p95 = share.timer.percentile(95)
        assert p95 is not None, f"percentile(95) returned None"
        assert isinstance(p95, float), f"percentile(95) returned {type(p95)}, expected float"
        assert p95 > 0, f"percentile(95) = {p95}, expected > 0"

        # get_time() must return the recorded value
        t0 = share.timer.get_time(0)
        assert t0 is not None, f"get_time(0) returned None"
        assert abs(t0 - 1.0) < 0.01, f"get_time(0) = {t0}, expected 1.0"

        # get_statistics() must return a stats object
        stats = share.timer.get_statistics()
        assert stats is not None, f"get_statistics() returned None"
    finally:
        share.stop()


# =============================================================================
# Circuit / BreakingCircuit in Share
# =============================================================================

def test_circuit_disallowed_in_share():
    """Circuit should raise TypeError when assigned to Share."""
    from suitkaise.circuits import Circuit
    share = Share()
    try:
        try:
            share.circ = Circuit(num_shorts_to_trip=3)
            raise AssertionError("Expected TypeError for Circuit in Share")
        except TypeError as e:
            assert "Circuit" in str(e)
            assert "BreakingCircuit" in str(e)
    finally:
        share.stop()


def test_breaking_circuit_allowed_in_share():
    """BreakingCircuit should be assignable to Share."""
    from suitkaise.circuits import BreakingCircuit
    share = Share()
    try:
        share.breaker = BreakingCircuit(num_shorts_to_trip=3)
        assert share.breaker.broken == False
        assert share.breaker.times_shorted == 0
    finally:
        share.stop()


def test_breaking_circuit_short_no_sleep():
    """BreakingCircuit.short() through Share should update state without sleeping."""
    from suitkaise.circuits import BreakingCircuit
    import time as _time

    share = Share()
    try:
        # large sleep to make it obvious if sleep actually fires
        share.breaker = BreakingCircuit(
            num_shorts_to_trip=2,
            sleep_time_after_trip=10.0,
        )

        t0 = _time.monotonic()
        share.breaker.short()  # 1st short
        share.breaker.short()  # 2nd short — trips, but should NOT sleep
        elapsed = _time.monotonic() - t0

        # if the 10s sleep fired, this would be > 10s
        assert elapsed < 2.0, f"short() slept in coordinator ({elapsed:.1f}s)"
        assert share.breaker.broken == True
        assert share.breaker.total_trips == 2
    finally:
        share.stop()


def test_breaking_circuit_trip_no_sleep():
    """BreakingCircuit.trip() through Share should break without sleeping."""
    from suitkaise.circuits import BreakingCircuit
    import time as _time

    share = Share()
    try:
        share.breaker = BreakingCircuit(
            num_shorts_to_trip=100,
            sleep_time_after_trip=10.0,
        )

        t0 = _time.monotonic()
        share.breaker.trip()
        elapsed = _time.monotonic() - t0

        assert elapsed < 2.0, f"trip() slept in coordinator ({elapsed:.1f}s)"
        assert share.breaker.broken == True
        assert share.breaker.total_trips == 1
    finally:
        share.stop()


def test_breaking_circuit_reset_in_share():
    """BreakingCircuit.reset() should work through Share."""
    from suitkaise.circuits import BreakingCircuit
    share = Share()
    try:
        share.breaker = BreakingCircuit(num_shorts_to_trip=1)
        share.breaker.short()  # trips immediately
        assert share.breaker.broken == True
        share.breaker.reset()
        assert share.breaker.broken == False
    finally:
        share.stop()


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all share proxy tests."""
    runner = TestRunner("Share Proxy Tests")

    runner.run_test("Proxy method/property", test_share_proxy_method_and_property)
    runner.run_test("Proxy setattr", test_share_proxy_setattr)
    runner.run_test("Proxy warns when stopped", test_share_proxy_warns_when_stopped)
    runner.run_test("Non-proxy value", test_share_non_proxy_value)
    runner.run_test("Proxy read barrier multi-attrs", test_share_proxy_read_barrier_multiple_attrs)
    runner.run_test("Proxy concurrent reads/writes", test_share_proxy_concurrent_reads_and_writes)
    runner.run_test("Share clear/repr", test_share_clear_and_repr)
    runner.run_test("Share serialize/deserialize", test_share_serialize_deserialize)
    runner.run_test("Proxy fallback attr", test_object_proxy_fallback_attr)
    runner.run_test("Sktimer blocked: start()", test_sktimer_blocked_start)
    runner.run_test("Sktimer blocked: stop()", test_sktimer_blocked_stop)
    runner.run_test("Sktimer blocked: pause/resume/lap/discard", test_sktimer_blocked_pause_resume_lap_discard)
    runner.run_test("Sktimer allowed: add_time()", test_sktimer_add_time_allowed)
    runner.run_test("Sktimer allowed: read properties", test_sktimer_read_properties_allowed)
    runner.run_test("Sktimer allowed: reset()", test_sktimer_reset_allowed)
    runner.run_test("Sktimer read methods return values", test_sktimer_read_methods_return_values)
    runner.run_test("Circuit disallowed in Share", test_circuit_disallowed_in_share)
    runner.run_test("BreakingCircuit allowed in Share", test_breaking_circuit_allowed_in_share)
    runner.run_test("BreakingCircuit short() no sleep", test_breaking_circuit_short_no_sleep)
    runner.run_test("BreakingCircuit trip() no sleep", test_breaking_circuit_trip_no_sleep)
    runner.run_test("BreakingCircuit reset() in Share", test_breaking_circuit_reset_in_share)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
