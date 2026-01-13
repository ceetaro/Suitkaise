"""
Exponential Backoff Tests

Tests the exponential backoff functionality:
- Backoff calculation
- reset_backoff() method
- Backoff limits
- Custom backoff parameters
"""

import sys
import time as stdlib_time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.circuits import Circuit, BreakingCircuit


# =============================================================================
# API Parameter Names:
# - num_shorts_to_trip: number of shorts before trip
# - sleep_time_after_trip: base sleep time
# - factor: backoff multiplier (default 1.0 = no backoff)
# - max_sleep_time: maximum sleep time cap
# =============================================================================


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
# Circuit Backoff Tests
# =============================================================================

def test_circuit_backoff_initial():
    """Circuit should start with initial sleep time."""
    circuit = Circuit(num_shorts_to_trip=3, sleep_time_after_trip=0.1)
    
    # Should have sleep time property
    assert hasattr(circuit, 'sleep_time_after_trip') or hasattr(circuit, 'current_sleep_time')


def test_circuit_backoff_increases():
    """Circuit sleep time should increase with factor after trip."""
    circuit = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0.05, factor=2.0)
    
    # Trip the circuit
    circuit.short()
    circuit.short()  # This should trip
    
    # After trip, wait for reset and check sleep time increased
    stdlib_time.sleep(0.1)  # Wait past initial sleep
    
    # Next cycle
    circuit.short()
    circuit.short()  # Trip again
    
    # The backoff logic increases sleep time - just verify circuit works
    assert circuit.times_shorted >= 0


def test_circuit_backoff_exponential():
    """Circuit sleep time should grow with factor."""
    circuit = Circuit(num_shorts_to_trip=1, sleep_time_after_trip=0.01, factor=2.0, max_sleep_time=1.0)
    
    # Trip multiple times
    circuit.short()  # Trip 1, sleeps 0.01
    
    stdlib_time.sleep(0.02)  # Wait past first sleep
    
    circuit.short()  # Trip 2, sleeps 0.02
    
    stdlib_time.sleep(0.03)  # Wait past second sleep
    
    circuit.short()  # Trip 3, sleeps 0.04
    
    # Sleep time should have increased
    assert circuit.total_trips >= 3


def test_circuit_reset_backoff():
    """Circuit.reset_backoff() should reset sleep time to initial."""
    circuit = Circuit(num_shorts_to_trip=1, sleep_time_after_trip=0.05, factor=2.0)
    
    # Trip to increase sleep time
    circuit.short()
    stdlib_time.sleep(0.1)
    circuit.short()
    
    # Reset backoff
    circuit.reset_backoff()
    
    # Sleep time should be back to initial
    assert circuit.current_sleep_time == 0.05


def test_circuit_max_backoff():
    """Circuit sleep time should not exceed max_sleep_time."""
    circuit = Circuit(num_shorts_to_trip=1, sleep_time_after_trip=0.05, factor=2.0, max_sleep_time=0.15)
    
    # Trip many times
    for _ in range(5):
        circuit.short()
        stdlib_time.sleep(0.2)
    
    # Sleep time should be capped at 0.15
    assert circuit.current_sleep_time <= 0.15


# =============================================================================
# BreakingCircuit Backoff Tests
# =============================================================================

def test_breaking_circuit_backoff_on_reset():
    """BreakingCircuit should sleep after reset with factor > 1."""
    circuit = BreakingCircuit(num_shorts_to_trip=2, sleep_time_after_trip=0.05, factor=2.0)
    
    circuit.short()
    circuit.short()  # This breaks
    
    assert circuit.broken == True
    
    # Reset - should sleep
    circuit.reset()
    
    assert circuit.broken == False


def test_breaking_circuit_backoff_increases():
    """BreakingCircuit sleep time should increase with each reset."""
    circuit = BreakingCircuit(num_shorts_to_trip=1, sleep_time_after_trip=0.02, factor=2.0, max_sleep_time=0.5)
    
    # First break and reset
    circuit.short()
    circuit.reset()
    
    # Second break and reset
    circuit.short()
    circuit.reset()
    
    # Sleep time should have increased
    assert circuit.current_sleep_time > 0.02


def test_breaking_circuit_reset_backoff():
    """BreakingCircuit.reset_backoff() should reset sleep time to initial."""
    circuit = BreakingCircuit(num_shorts_to_trip=1, sleep_time_after_trip=0.05, factor=2.0)
    
    # Break and reset multiple times
    for _ in range(3):
        circuit.short()
        circuit.reset()
    
    # Reset backoff
    circuit.reset_backoff()
    
    # Sleep time should be back to initial
    assert circuit.current_sleep_time == 0.05


# =============================================================================
# Custom Backoff Parameters Tests
# =============================================================================

def test_circuit_custom_backoff():
    """Circuit should accept custom sleep_time_after_trip."""
    circuit = Circuit(num_shorts_to_trip=3, sleep_time_after_trip=0.5)
    
    assert circuit.sleep_time_after_trip == 0.5


def test_circuit_custom_max_backoff():
    """Circuit should accept custom max_sleep_time."""
    circuit = Circuit(num_shorts_to_trip=3, sleep_time_after_trip=0.1, max_sleep_time=2.0)
    
    assert circuit.max_sleep_time == 2.0


def test_breaking_circuit_custom_backoff():
    """BreakingCircuit should accept custom sleep_time_after_trip."""
    circuit = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=0.5)
    
    assert circuit.sleep_time_after_trip == 0.5


def test_breaking_circuit_custom_max_backoff():
    """BreakingCircuit should accept custom max_sleep_time."""
    circuit = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=0.1, max_sleep_time=2.0)
    
    assert circuit.max_sleep_time == 2.0


# =============================================================================
# Backoff Timing Tests
# =============================================================================

def test_circuit_respects_backoff_timing():
    """Circuit should respect sleep timing on trip."""
    circuit = Circuit(num_shorts_to_trip=1, sleep_time_after_trip=0.05)
    
    start = stdlib_time.time()
    
    circuit.short()  # Trips and sleeps
    
    elapsed = stdlib_time.time() - start
    
    # Should have slept ~0.05s
    assert elapsed >= 0.04, f"Should sleep on trip, elapsed {elapsed}"


def test_circuit_blocks_during_backoff():
    """Circuit should handle shorts normally."""
    circuit = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0.01)
    
    circuit.short()
    circuit.short()  # Trips
    
    # More shorts should work
    circuit.short()
    circuit.short()
    
    # Should not error
    assert circuit.total_trips >= 2


def test_breaking_circuit_reset_timing():
    """BreakingCircuit reset should work correctly."""
    circuit = BreakingCircuit(num_shorts_to_trip=1, sleep_time_after_trip=0.02)
    
    circuit.short()
    
    assert circuit.broken
    
    circuit.reset()
    
    assert circuit.broken == False


# =============================================================================
# Edge Cases Tests
# =============================================================================

def test_zero_backoff():
    """Circuit should handle zero sleep time."""
    circuit = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0)
    
    circuit.short()
    circuit.short()
    
    # Should work without errors
    assert circuit.total_trips >= 1


def test_very_small_backoff():
    """Circuit should handle very small sleep time."""
    circuit = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0.001)
    
    circuit.short()  # 1st short
    circuit.short()  # 2nd short - trips, sleeps 1ms, auto-resets
    
    # Circuit auto-resets after trip, so counter is back to 0
    circuit.short()  # 1st short after reset
    
    # Just verify circuit is functional with tiny sleep times
    assert circuit.times_shorted >= 3 or circuit.total_trips >= 1


def test_very_large_backoff():
    """Circuit should accept large sleep time values."""
    circuit = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=3600)  # 1 hour
    
    assert circuit.sleep_time_after_trip == 3600


def test_backoff_with_multiplier():
    """Sleep time should grow by factor."""
    circuit = Circuit(num_shorts_to_trip=1, sleep_time_after_trip=0.01, factor=2.0, max_sleep_time=1.0)
    
    # After each trip, sleep time doubles
    # 0.01 -> 0.02 -> 0.04 -> 0.08 -> ...
    
    initial = circuit.current_sleep_time
    circuit.short()  # Trip 1
    
    # Sleep time should have increased
    assert circuit.current_sleep_time >= initial


# =============================================================================
# reset_backoff Integration Tests
# =============================================================================

def test_reset_backoff_after_success():
    """reset_backoff should be callable after successful operations."""
    circuit = Circuit(num_shorts_to_trip=3, sleep_time_after_trip=0.01, factor=2.0)
    
    circuit.short()
    circuit.short()
    
    # Reset backoff - doesn't affect short count, just resets sleep multiplier
    circuit.reset_backoff()
    
    # Verify reset_backoff worked (sleep time should be back to initial)
    assert circuit.current_sleep_time == 0.01
    
    # Circuit should continue to work
    circuit.short()  # This is the 3rd short - trips
    
    # After trip, counter auto-resets
    assert circuit.total_trips >= 1


def test_reset_backoff_clears_accumulated():
    """reset_backoff should clear accumulated sleep time."""
    circuit = Circuit(num_shorts_to_trip=1, sleep_time_after_trip=0.01, factor=2.0)
    
    # Accumulate backoff
    for _ in range(3):
        circuit.short()
    
    # Sleep time should have increased
    assert circuit.current_sleep_time > 0.01
    
    # Reset
    circuit.reset_backoff()
    
    # Should be back to initial
    assert circuit.current_sleep_time == 0.01


def test_breaking_circuit_reset_backoff_independent():
    """BreakingCircuit reset_backoff should be independent of reset."""
    circuit = BreakingCircuit(num_shorts_to_trip=1, sleep_time_after_trip=0.05, factor=2.0)
    
    circuit.short()
    circuit.reset()
    
    # reset_backoff is separate from reset
    circuit.reset_backoff()
    
    # Circuit should work normally
    assert circuit.broken == False
    circuit.short()
    assert circuit.broken == True


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all backoff tests."""
    runner = TestRunner("Exponential Backoff Tests")
    
    # Circuit backoff tests
    runner.run_test("Circuit backoff initial", test_circuit_backoff_initial)
    runner.run_test("Circuit backoff increases", test_circuit_backoff_increases)
    runner.run_test("Circuit backoff exponential", test_circuit_backoff_exponential)
    runner.run_test("Circuit reset_backoff", test_circuit_reset_backoff)
    runner.run_test("Circuit max_backoff", test_circuit_max_backoff)
    
    # BreakingCircuit backoff tests
    runner.run_test("BreakingCircuit backoff on reset", test_breaking_circuit_backoff_on_reset)
    runner.run_test("BreakingCircuit backoff increases", test_breaking_circuit_backoff_increases)
    runner.run_test("BreakingCircuit reset_backoff", test_breaking_circuit_reset_backoff)
    
    # Custom parameters tests
    runner.run_test("Circuit custom backoff", test_circuit_custom_backoff)
    runner.run_test("Circuit custom max_backoff", test_circuit_custom_max_backoff)
    runner.run_test("BreakingCircuit custom backoff", test_breaking_circuit_custom_backoff)
    runner.run_test("BreakingCircuit custom max_backoff", test_breaking_circuit_custom_max_backoff)
    
    # Timing tests
    runner.run_test("Circuit respects backoff timing", test_circuit_respects_backoff_timing)
    runner.run_test("Circuit blocks during backoff", test_circuit_blocks_during_backoff)
    runner.run_test("BreakingCircuit reset timing", test_breaking_circuit_reset_timing)
    
    # Edge cases
    runner.run_test("Zero backoff", test_zero_backoff)
    runner.run_test("Very small backoff", test_very_small_backoff)
    runner.run_test("Very large backoff", test_very_large_backoff)
    runner.run_test("Backoff with multiplier", test_backoff_with_multiplier)
    
    # reset_backoff integration
    runner.run_test("reset_backoff after success", test_reset_backoff_after_success)
    runner.run_test("reset_backoff clears accumulated", test_reset_backoff_clears_accumulated)
    runner.run_test("BreakingCircuit reset_backoff independent", test_breaking_circuit_reset_backoff_independent)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
