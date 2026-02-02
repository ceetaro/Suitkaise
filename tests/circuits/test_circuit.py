"""
Circuit Class Tests

Tests all Circuit functionality:
- Short counting
- Trip behavior
- Auto-reset after trip
- Exponential backoff
- reset_backoff()
- Properties
- Thread safety
"""

import sys
import time
import threading

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.circuits import Circuit
from suitkaise.circuits import api as circuits_api


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
# Creation Tests
# =============================================================================

def test_circuit_creation():
    """Circuit should be created with correct initial state."""
    circ = Circuit(5, sleep_time_after_trip=0.1)
    
    assert circ.num_shorts_to_trip == 5
    assert circ.sleep_time_after_trip == 0.1
    assert circ.times_shorted == 0
    assert circ.total_trips == 0
    assert circ.current_sleep_time == 0.1


def test_circuit_default_values():
    """Circuit should have sensible defaults."""
    circ = Circuit(3)
    
    assert circ.sleep_time_after_trip == 0.0
    assert circ.backoff_factor == 1.0
    assert circ.max_sleep_time == 10.0
    assert circ.jitter == 0.0


def test_circuit_requires_num_shorts_to_trip():
    """Circuit should require num_shorts_to_trip."""
    try:
        Circuit(0)
    except ValueError:
        pass
    else:
        assert False, "Expected ValueError when num_shorts_to_trip is falsy"


# =============================================================================
# Short Counting Tests
# =============================================================================

def test_circuit_short_counting():
    """Circuit should count shorts correctly."""
    circ = Circuit(5, sleep_time_after_trip=0.0)
    
    circ.short()
    assert circ.times_shorted == 1
    
    circ.short()
    circ.short()
    assert circ.times_shorted == 3


def test_circuit_short_returns_false():
    """short() should return False when not tripping."""
    circ = Circuit(5, sleep_time_after_trip=0.0)
    
    for _ in range(4):
        result = circ.short()
        assert result == False, "Should return False when not tripping"


def test_circuit_short_returns_true_on_trip():
    """short() should return True when tripping."""
    circ = Circuit(3, sleep_time_after_trip=0.0)
    
    circ.short()  # 1
    circ.short()  # 2
    result = circ.short()  # 3 - trips
    
    assert result == True, "Should return True when tripping"


# =============================================================================
# Trip Behavior Tests
# =============================================================================

def test_circuit_trips_at_threshold():
    """Circuit should trip when shorts reach threshold."""
    circ = Circuit(3, sleep_time_after_trip=0.0)
    
    circ.short()  # 1
    circ.short()  # 2
    circ.short()  # 3 - should trip
    
    assert circ.total_trips == 1, f"Should have tripped once, got {circ.total_trips}"


def test_circuit_auto_resets():
    """Circuit should auto-reset counter after trip."""
    circ = Circuit(3, sleep_time_after_trip=0.0)
    
    circ.short()  # 1
    circ.short()  # 2
    circ.short()  # 3 - trips, auto-resets
    
    # Counter should be reset
    assert circ.times_shorted == 0, f"Should reset to 0, got {circ.times_shorted}"


def test_circuit_sleeps_on_trip():
    """Circuit should sleep when tripping."""
    circ = Circuit(2, sleep_time_after_trip=0.02)
    
    circ.short()  # 1
    
    start = time.perf_counter()
    circ.short()  # 2 - trips and sleeps
    elapsed = time.perf_counter() - start
    
    assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"


def test_circuit_trip_direct():
    """trip() should immediately trip without counting."""
    circ = Circuit(10, sleep_time_after_trip=0.0)
    
    result = circ.trip()
    
    assert result == True
    assert circ.total_trips == 1
    assert circ.times_shorted == 0  # Reset


def test_circuit_trip_sleeps():
    """trip() should sleep."""
    circ = Circuit(10, sleep_time_after_trip=0.02)
    
    start = time.perf_counter()
    circ.trip()
    elapsed = time.perf_counter() - start
    
    assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"


def test_circuit_jitter_applies():
    """Sleep duration should include jitter."""
    circ = Circuit(1, sleep_time_after_trip=0.02, jitter=0.5)
    
    original_uniform = circuits_api.random.uniform
    try:
        circuits_api.random.uniform = lambda low, high: high  # max jitter
        start = time.perf_counter()
        circ.short()  # trip and sleep
        elapsed = time.perf_counter() - start
    finally:
        circuits_api.random.uniform = original_uniform
    
    assert elapsed >= 0.026, f"Should sleep with jitter, got {elapsed}"


def test_circuit_custom_sleep():
    """short/trip should accept custom_sleep."""
    circ = Circuit(2, sleep_time_after_trip=0.1)
    
    circ.short()  # 1
    
    start = time.perf_counter()
    circ.short(custom_sleep=0.02)  # 2 - trips with custom sleep
    elapsed = time.perf_counter() - start
    
    # Should use custom sleep (20ms), not default (100ms)
    assert elapsed >= 0.018, "Should sleep with custom duration"
    assert elapsed < 0.05, "Should not use default sleep"


# =============================================================================
# Exponential Backoff Tests
# =============================================================================

def test_circuit_backoff_applies():
    """Circuit should apply backoff factor after trip."""
    circ = Circuit(2, sleep_time_after_trip=0.01, backoff_factor=2.0)
    
    assert circ.current_sleep_time == 0.01
    
    circ.short()
    circ.short()  # Trip 1
    
    # Sleep time should double
    assert circ.current_sleep_time == 0.02, f"Should be 0.02, got {circ.current_sleep_time}"


def test_circuit_backoff_accumulates():
    """Backoff should accumulate across trips."""
    circ = Circuit(1, sleep_time_after_trip=0.01, backoff_factor=2.0)
    
    circ.short()  # Trip 1: 0.01 -> 0.02
    circ.short()  # Trip 2: 0.02 -> 0.04
    circ.short()  # Trip 3: 0.04 -> 0.08
    
    assert abs(circ.current_sleep_time - 0.08) < 0.001, f"Should be 0.08, got {circ.current_sleep_time}"


def test_circuit_backoff_max_cap():
    """Backoff should be capped at max_sleep_time."""
    circ = Circuit(1, sleep_time_after_trip=0.5, backoff_factor=2.0, max_sleep_time=1.0)
    
    circ.short()  # 0.5 -> 1.0
    circ.short()  # Would be 2.0, capped at 1.0
    
    assert circ.current_sleep_time == 1.0, f"Should cap at 1.0, got {circ.current_sleep_time}"


def test_circuit_no_backoff_with_factor_1():
    """Factor=1 should not change sleep time."""
    circ = Circuit(1, sleep_time_after_trip=0.01, backoff_factor=1.0)
    
    circ.short()  # Trip 1
    circ.short()  # Trip 2
    circ.short()  # Trip 3
    
    assert circ.current_sleep_time == 0.01, f"Should stay 0.01, got {circ.current_sleep_time}"


# =============================================================================
# reset_backoff Tests
# =============================================================================

def test_circuit_reset_backoff():
    """reset_backoff() should reset sleep time to original."""
    circ = Circuit(1, sleep_time_after_trip=0.01, backoff_factor=2.0)
    
    circ.short()  # 0.01 -> 0.02
    circ.short()  # 0.02 -> 0.04
    
    assert circ.current_sleep_time == 0.04
    
    circ.reset_backoff()
    
    assert circ.current_sleep_time == 0.01, f"Should reset to 0.01, got {circ.current_sleep_time}"


def test_circuit_reset_backoff_preserves_counts():
    """reset_backoff() should not affect trip counts."""
    circ = Circuit(1, sleep_time_after_trip=0.01, backoff_factor=2.0)
    
    circ.short()  # Trip 1
    circ.short()  # Trip 2
    
    circ.reset_backoff()
    
    assert circ.total_trips == 2, "Should preserve total_trips"


# =============================================================================
# Property Tests
# =============================================================================

def test_circuit_times_shorted_property():
    """times_shorted should reflect current count."""
    circ = Circuit(10, sleep_time_after_trip=0.0)
    
    for i in range(5):
        circ.short()
        assert circ.times_shorted == i + 1


def test_circuit_total_trips_property():
    """total_trips should accumulate lifetime trips."""
    circ = Circuit(2, sleep_time_after_trip=0.0)
    
    circ.short()
    circ.short()  # Trip 1
    circ.short()
    circ.short()  # Trip 2
    circ.trip()   # Trip 3
    
    assert circ.total_trips == 3


def test_circuit_current_sleep_time_property():
    """current_sleep_time should reflect current value."""
    circ = Circuit(1, sleep_time_after_trip=0.05, backoff_factor=1.5)
    
    assert circ.current_sleep_time == 0.05
    
    circ.short()
    
    expected = 0.05 * 1.5
    assert abs(circ.current_sleep_time - expected) < 0.001


# =============================================================================
# Thread Safety Tests
# =============================================================================

def test_circuit_concurrent_shorts():
    """Circuit should handle concurrent shorts safely."""
    circ = Circuit(1000, sleep_time_after_trip=0.0)
    num_threads = 10
    shorts_per_thread = 100
    
    def do_shorts():
        for _ in range(shorts_per_thread):
            circ.short()
    
    threads = [threading.Thread(target=do_shorts) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should have exactly 1000 shorts (= num_threads * shorts_per_thread)
    # Since threshold is 1000, it should trip exactly once at 1000
    expected_shorts = num_threads * shorts_per_thread
    # After trip, times_shorted resets, but total_trips should be 1
    assert circ.total_trips == 1, f"Should trip once at 1000, got {circ.total_trips} trips"


# =============================================================================
# Edge Cases
# =============================================================================

def test_circuit_zero_sleep():
    """Circuit should work with zero sleep time."""
    circ = Circuit(2, sleep_time_after_trip=0.0)
    
    start = time.perf_counter()
    circ.short()
    circ.short()  # Trips with 0 sleep
    elapsed = time.perf_counter() - start
    
    assert elapsed < 0.01, "Zero sleep should be fast"
    assert circ.total_trips == 1


def test_circuit_single_short_threshold():
    """Circuit with threshold=1 should trip on every short."""
    circ = Circuit(1, sleep_time_after_trip=0.0)
    
    for i in range(5):
        circ.short()
        assert circ.total_trips == i + 1


def test_circuit_very_large_threshold():
    """Circuit should handle large threshold."""
    circ = Circuit(1_000_000, sleep_time_after_trip=0.0)
    
    for _ in range(100):
        circ.short()
    
    assert circ.times_shorted == 100
    assert circ.total_trips == 0


# =============================================================================
# Docstring Examples
# =============================================================================

def test_doc_circuit_basic_example():
    """Docstring example: basic Circuit usage."""
    circ = Circuit(
        num_shorts_to_trip=5,
        sleep_time_after_trip=0.0,
        backoff_factor=1.5,
        max_sleep_time=10.0,
        jitter=0.2,
    )
    for _ in range(5):
        circ.short(custom_sleep=0.0)
    assert circ.total_trips >= 1


def test_doc_circuit_rate_limit_example():
    """Docstring example: rate limiting with short()."""
    rate_limiter = Circuit(
        num_shorts_to_trip=10,
        sleep_time_after_trip=0.0,
        backoff_factor=1.5,
        max_sleep_time=30.0,
        jitter=0.1,
    )
    for _ in range(10):
        rate_limiter.short(custom_sleep=0.0)
    assert rate_limiter.total_trips >= 1


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all Circuit tests."""
    runner = TestRunner("Circuit Class Tests")
    
    # Creation tests
    runner.run_test("Circuit creation", test_circuit_creation)
    runner.run_test("Circuit defaults", test_circuit_default_values)
    
    # Short counting tests
    runner.run_test("Circuit short counting", test_circuit_short_counting)
    runner.run_test("Circuit short returns False", test_circuit_short_returns_false)
    runner.run_test("Circuit short returns True on trip", test_circuit_short_returns_true_on_trip)
    
    # Trip behavior tests
    runner.run_test("Circuit trips at threshold", test_circuit_trips_at_threshold)
    runner.run_test("Circuit auto-resets", test_circuit_auto_resets)
    runner.run_test("Circuit sleeps on trip", test_circuit_sleeps_on_trip)
    runner.run_test("Circuit trip() direct", test_circuit_trip_direct)
    runner.run_test("Circuit trip() sleeps", test_circuit_trip_sleeps)
    runner.run_test("Circuit custom sleep", test_circuit_custom_sleep)
    
    # Backoff tests
    runner.run_test("Circuit backoff applies", test_circuit_backoff_applies)
    runner.run_test("Circuit backoff accumulates", test_circuit_backoff_accumulates)
    runner.run_test("Circuit backoff max cap", test_circuit_backoff_max_cap)
    runner.run_test("Circuit no backoff with backoff_factor=1", test_circuit_no_backoff_with_factor_1)
    
    # reset_backoff tests
    runner.run_test("Circuit reset_backoff()", test_circuit_reset_backoff)
    runner.run_test("Circuit reset_backoff preserves counts", test_circuit_reset_backoff_preserves_counts)
    
    # Property tests
    runner.run_test("Circuit times_shorted property", test_circuit_times_shorted_property)
    runner.run_test("Circuit total_trips property", test_circuit_total_trips_property)
    runner.run_test("Circuit current_sleep_time property", test_circuit_current_sleep_time_property)
    
    # Thread safety tests
    runner.run_test("Circuit concurrent shorts", test_circuit_concurrent_shorts)
    
    # Edge cases
    runner.run_test("Circuit zero sleep", test_circuit_zero_sleep)
    runner.run_test("Circuit single short threshold", test_circuit_single_short_threshold)
    runner.run_test("Circuit large threshold", test_circuit_very_large_threshold)
    
    # docstring examples
    runner.run_test("doc: Circuit basic", test_doc_circuit_basic_example)
    runner.run_test("doc: Circuit rate limit", test_doc_circuit_rate_limit_example)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
