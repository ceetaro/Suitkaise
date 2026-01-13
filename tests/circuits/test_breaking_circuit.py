"""
BreakingCircuit Class Tests

Tests all BreakingCircuit functionality:
- Short counting
- Breaking behavior
- Manual reset required
- Exponential backoff on reset
- Properties
- Thread safety
"""

import sys
import time
import threading

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.circuits import BreakingCircuit


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
        return failed == 0


# =============================================================================
# Creation Tests
# =============================================================================

def test_breaking_circuit_creation():
    """BreakingCircuit should be created with correct initial state."""
    circ = BreakingCircuit(5, sleep_time_after_trip=0.1)
    
    assert circ.num_shorts_to_trip == 5
    assert circ.sleep_time_after_trip == 0.1
    assert circ.broken == False
    assert circ.times_shorted == 0
    assert circ.total_failures == 0
    assert circ.current_sleep_time == 0.1


def test_breaking_circuit_defaults():
    """BreakingCircuit should have sensible defaults."""
    circ = BreakingCircuit(3)
    
    assert circ.sleep_time_after_trip == 0.0
    assert circ.factor == 1.0
    assert circ.max_sleep_time == 10.0


# =============================================================================
# Short Counting Tests
# =============================================================================

def test_breaking_short_counting():
    """BreakingCircuit should count shorts."""
    circ = BreakingCircuit(10, sleep_time_after_trip=0.0)
    
    circ.short()
    circ.short()
    circ.short()
    
    assert circ.times_shorted == 3
    assert circ.total_failures == 3  # Each short is a failure


def test_breaking_short_no_return():
    """short() on BreakingCircuit returns None."""
    circ = BreakingCircuit(10, sleep_time_after_trip=0.0)
    
    result = circ.short()
    
    assert result is None


# =============================================================================
# Breaking Behavior Tests
# =============================================================================

def test_breaking_breaks_at_threshold():
    """BreakingCircuit should break at threshold."""
    circ = BreakingCircuit(3, sleep_time_after_trip=0.0)
    
    assert circ.broken == False
    
    circ.short()  # 1
    circ.short()  # 2
    circ.short()  # 3 - breaks
    
    assert circ.broken == True


def test_breaking_stays_broken():
    """BreakingCircuit should stay broken without manual reset."""
    circ = BreakingCircuit(2, sleep_time_after_trip=0.0)
    
    circ.short()
    circ.short()  # Breaks
    
    assert circ.broken == True
    
    # Additional shorts don't unbreak it
    circ.short()
    circ.short()
    
    assert circ.broken == True


def test_breaking_sleeps_when_breaking():
    """BreakingCircuit should sleep when breaking."""
    circ = BreakingCircuit(2, sleep_time_after_trip=0.02)
    
    circ.short()  # 1
    
    start = time.perf_counter()
    circ.short()  # 2 - breaks and sleeps
    elapsed = time.perf_counter() - start
    
    assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"


def test_breaking_trip_direct():
    """trip() should immediately break."""
    circ = BreakingCircuit(100, sleep_time_after_trip=0.0)
    
    circ.trip()
    
    assert circ.broken == True
    assert circ.total_failures == 1


def test_breaking_trip_sleeps():
    """trip() should sleep."""
    circ = BreakingCircuit(100, sleep_time_after_trip=0.02)
    
    start = time.perf_counter()
    circ.trip()
    elapsed = time.perf_counter() - start
    
    assert elapsed >= 0.018, f"Should sleep ~20ms, got {elapsed}"


def test_breaking_custom_sleep():
    """short/trip should accept custom_sleep."""
    circ = BreakingCircuit(2, sleep_time_after_trip=0.1)
    
    circ.short()  # 1
    
    start = time.perf_counter()
    circ.short(custom_sleep=0.02)  # 2 - breaks with custom sleep
    elapsed = time.perf_counter() - start
    
    assert elapsed >= 0.018, "Should sleep with custom duration"
    assert elapsed < 0.05, "Should not use default sleep"


# =============================================================================
# Reset Tests
# =============================================================================

def test_breaking_reset():
    """reset() should clear broken state."""
    circ = BreakingCircuit(2, sleep_time_after_trip=0.0)
    
    circ.short()
    circ.short()  # Breaks
    
    assert circ.broken == True
    
    circ.reset()
    
    assert circ.broken == False


def test_breaking_reset_clears_counter():
    """reset() should clear times_shorted."""
    circ = BreakingCircuit(5, sleep_time_after_trip=0.0)
    
    circ.short()
    circ.short()
    circ.short()
    
    circ.reset()
    
    assert circ.times_shorted == 0


def test_breaking_reset_applies_backoff():
    """reset() should apply backoff factor."""
    circ = BreakingCircuit(2, sleep_time_after_trip=0.01, factor=2.0)
    
    circ.short()
    circ.short()  # Breaks
    
    assert circ.current_sleep_time == 0.01  # Not changed yet
    
    circ.reset()
    
    assert circ.current_sleep_time == 0.02  # Doubled


def test_breaking_reset_backoff_accumulates():
    """Backoff should accumulate across resets."""
    circ = BreakingCircuit(1, sleep_time_after_trip=0.01, factor=2.0)
    
    circ.short()  # Breaks
    circ.reset()  # 0.01 -> 0.02
    
    circ.short()  # Breaks again
    circ.reset()  # 0.02 -> 0.04
    
    circ.short()  # Breaks again
    circ.reset()  # 0.04 -> 0.08
    
    assert abs(circ.current_sleep_time - 0.08) < 0.001


def test_breaking_reset_backoff_max_cap():
    """Backoff should be capped at max_sleep_time on reset."""
    circ = BreakingCircuit(1, sleep_time_after_trip=0.5, factor=2.0, max_sleep_time=1.0)
    
    circ.short()  # Breaks
    circ.reset()  # 0.5 -> 1.0
    
    circ.short()  # Breaks
    circ.reset()  # Would be 2.0, capped at 1.0
    
    assert circ.current_sleep_time == 1.0


# =============================================================================
# reset_backoff Tests
# =============================================================================

def test_breaking_reset_backoff_method():
    """reset_backoff() should reset sleep time to original."""
    circ = BreakingCircuit(1, sleep_time_after_trip=0.01, factor=2.0)
    
    circ.short()  # Breaks
    circ.reset()  # 0.01 -> 0.02
    
    circ.reset_backoff()
    
    assert circ.current_sleep_time == 0.01


def test_breaking_reset_backoff_preserves_broken():
    """reset_backoff() should not affect broken state."""
    circ = BreakingCircuit(1, sleep_time_after_trip=0.01, factor=2.0)
    
    circ.short()  # Breaks
    
    assert circ.broken == True
    
    circ.reset_backoff()
    
    assert circ.broken == True  # Still broken


# =============================================================================
# Property Tests
# =============================================================================

def test_breaking_broken_property():
    """broken property should reflect state."""
    circ = BreakingCircuit(2, sleep_time_after_trip=0.0)
    
    assert circ.broken == False
    
    circ.short()
    assert circ.broken == False
    
    circ.short()
    assert circ.broken == True
    
    circ.reset()
    assert circ.broken == False


def test_breaking_total_failures_property():
    """total_failures should count all failures."""
    circ = BreakingCircuit(2, sleep_time_after_trip=0.0)
    
    circ.short()  # 1
    circ.short()  # 2 (breaks)
    circ.reset()
    circ.short()  # 3
    circ.trip()   # 4 (breaks)
    
    assert circ.total_failures == 4


# =============================================================================
# Loop Pattern Tests
# =============================================================================

def test_breaking_loop_pattern():
    """BreakingCircuit should work in while-not-broken loop."""
    circ = BreakingCircuit(3, sleep_time_after_trip=0.0)
    
    iterations = 0
    while not circ.broken:
        iterations += 1
        circ.short()
        if iterations > 10:
            break  # Safety
    
    assert iterations == 3
    assert circ.broken == True


def test_breaking_retry_pattern():
    """BreakingCircuit should support retry pattern."""
    circ = BreakingCircuit(3, sleep_time_after_trip=0.0)
    
    # Simulate retrying 3 times
    for _ in range(3):
        if not circ.broken:
            circ.short()
    
    assert circ.broken == True
    
    # Reset and retry again
    circ.reset()
    
    for _ in range(2):
        if not circ.broken:
            circ.short()
    
    assert circ.broken == False


# =============================================================================
# Thread Safety Tests
# =============================================================================

def test_breaking_concurrent_shorts():
    """BreakingCircuit should handle concurrent shorts safely."""
    circ = BreakingCircuit(50, sleep_time_after_trip=0.0)
    num_threads = 10
    shorts_per_thread = 10
    
    def do_shorts():
        for _ in range(shorts_per_thread):
            if not circ.broken:
                circ.short()
    
    threads = [threading.Thread(target=do_shorts) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should be broken (50 shorts from 10*10 = 100 potential shorts)
    assert circ.broken == True


# =============================================================================
# Edge Cases
# =============================================================================

def test_breaking_zero_sleep():
    """BreakingCircuit should work with zero sleep."""
    circ = BreakingCircuit(2, sleep_time_after_trip=0.0)
    
    start = time.perf_counter()
    circ.short()
    circ.short()
    elapsed = time.perf_counter() - start
    
    assert elapsed < 0.01
    assert circ.broken == True


def test_breaking_single_threshold():
    """BreakingCircuit with threshold=1 should break on first short."""
    circ = BreakingCircuit(1, sleep_time_after_trip=0.0)
    
    circ.short()
    
    assert circ.broken == True
    assert circ.total_failures == 1


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all BreakingCircuit tests."""
    runner = TestRunner("BreakingCircuit Class Tests")
    
    # Creation tests
    runner.run_test("BreakingCircuit creation", test_breaking_circuit_creation)
    runner.run_test("BreakingCircuit defaults", test_breaking_circuit_defaults)
    
    # Short counting tests
    runner.run_test("BreakingCircuit short counting", test_breaking_short_counting)
    runner.run_test("BreakingCircuit short no return", test_breaking_short_no_return)
    
    # Breaking behavior tests
    runner.run_test("BreakingCircuit breaks at threshold", test_breaking_breaks_at_threshold)
    runner.run_test("BreakingCircuit stays broken", test_breaking_stays_broken)
    runner.run_test("BreakingCircuit sleeps when breaking", test_breaking_sleeps_when_breaking)
    runner.run_test("BreakingCircuit trip() direct", test_breaking_trip_direct)
    runner.run_test("BreakingCircuit trip() sleeps", test_breaking_trip_sleeps)
    runner.run_test("BreakingCircuit custom sleep", test_breaking_custom_sleep)
    
    # Reset tests
    runner.run_test("BreakingCircuit reset()", test_breaking_reset)
    runner.run_test("BreakingCircuit reset clears counter", test_breaking_reset_clears_counter)
    runner.run_test("BreakingCircuit reset applies backoff", test_breaking_reset_applies_backoff)
    runner.run_test("BreakingCircuit reset backoff accumulates", test_breaking_reset_backoff_accumulates)
    runner.run_test("BreakingCircuit reset backoff max cap", test_breaking_reset_backoff_max_cap)
    
    # reset_backoff tests
    runner.run_test("BreakingCircuit reset_backoff()", test_breaking_reset_backoff_method)
    runner.run_test("BreakingCircuit reset_backoff preserves broken", test_breaking_reset_backoff_preserves_broken)
    
    # Property tests
    runner.run_test("BreakingCircuit broken property", test_breaking_broken_property)
    runner.run_test("BreakingCircuit total_failures property", test_breaking_total_failures_property)
    
    # Loop pattern tests
    runner.run_test("BreakingCircuit loop pattern", test_breaking_loop_pattern)
    runner.run_test("BreakingCircuit retry pattern", test_breaking_retry_pattern)
    
    # Thread safety tests
    runner.run_test("BreakingCircuit concurrent shorts", test_breaking_concurrent_shorts)
    
    # Edge cases
    runner.run_test("BreakingCircuit zero sleep", test_breaking_zero_sleep)
    runner.run_test("BreakingCircuit single threshold", test_breaking_single_threshold)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
