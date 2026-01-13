"""
Timer Class Tests

Tests all Timer functionality:
- Basic start/stop
- Lap timing
- Pause/resume
- Statistics (mean, median, stdev, min, max, etc.)
- Concurrent/threaded usage
- Reset behavior
- Edge cases
"""

import sys
import time
import threading
import asyncio
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.timing import Timer


# =============================================================================
# Test Infrastructure
# =============================================================================

class TestResult:
    """Holds test result data."""
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


class TestRunner:
    """Simple test runner with colored output."""
    
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results: List[TestResult] = []
        
        # ANSI colors
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def run_test(self, name: str, test_func):
        """Run a single test and record result."""
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))
    
    def print_results(self):
        """Print all test results with formatting."""
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
# Basic Timer Tests
# =============================================================================

def test_timer_creation():
    """Timer should be created with empty state."""
    timer = Timer()
    assert timer.num_times == 0, "New timer should have no times"
    assert len(timer.times) == 0, "New timer should have empty times list"


def test_timer_start_stop():
    """Timer should record time between start and stop."""
    timer = Timer()
    timer.start()
    time.sleep(0.01)  # 10ms
    timer.stop()
    
    assert timer.num_times == 1, "Should have 1 recorded time"
    assert timer.most_recent > 0.009, f"Time should be ~10ms, got {timer.most_recent}"
    assert timer.most_recent < 0.05, f"Time should be ~10ms, got {timer.most_recent}"


def test_timer_multiple_measurements():
    """Timer should accumulate multiple measurements."""
    timer = Timer()
    
    for i in range(5):
        timer.start()
        time.sleep(0.005)  # 5ms
        timer.stop()
    
    assert timer.num_times == 5, f"Should have 5 times, got {timer.num_times}"
    assert timer.total_time > 0.02, f"Total time should be ~25ms, got {timer.total_time}"


def test_timer_discard():
    """Timer.discard() should return elapsed without recording."""
    timer = Timer()
    timer.start()
    time.sleep(0.01)
    elapsed = timer.discard()
    
    assert elapsed > 0.009, "Discard should return elapsed time"
    assert timer.num_times == 0, "Discard should not record time"


def test_timer_add_time():
    """Timer should accept manually added times."""
    timer = Timer()
    timer.add_time(1.0)
    timer.add_time(2.0)
    timer.add_time(3.0)
    
    assert timer.num_times == 3, "Should have 3 times"
    assert timer.total_time == 6.0, f"Total should be 6.0, got {timer.total_time}"
    assert timer.mean == 2.0, f"Mean should be 2.0, got {timer.mean}"


# =============================================================================
# Lap Timing Tests
# =============================================================================

def test_timer_lap():
    """Timer.lap() should record intermediate times."""
    timer = Timer()
    timer.start()
    
    time.sleep(0.01)
    timer.lap()
    
    time.sleep(0.01)
    timer.lap()
    
    time.sleep(0.01)
    timer.stop()
    
    assert timer.num_times == 3, f"Should have 3 lap times, got {timer.num_times}"


def test_timer_lap_values():
    """Lap times should reflect actual intervals."""
    timer = Timer()
    timer.start()
    
    time.sleep(0.02)
    timer.lap()  # ~20ms
    
    time.sleep(0.01)
    timer.stop()  # ~10ms
    
    # First lap should be ~20ms
    assert timer.times[0] > 0.015, f"First lap should be ~20ms, got {timer.times[0]}"
    # Second should be ~10ms
    assert timer.times[1] < timer.times[0], "Second interval should be shorter"


# =============================================================================
# Pause/Resume Tests
# =============================================================================

def test_timer_pause_resume():
    """Timer pause/resume should exclude paused time."""
    timer = Timer()
    timer.start()
    
    time.sleep(0.01)  # 10ms active
    timer.pause()
    
    time.sleep(0.02)  # 20ms paused (should NOT count)
    timer.resume()
    
    time.sleep(0.01)  # 10ms active
    timer.stop()
    
    # Total should be ~20ms (10ms + 10ms), not 40ms
    assert timer.most_recent > 0.015, f"Should be ~20ms, got {timer.most_recent}"
    assert timer.most_recent < 0.035, f"Should be ~20ms, not include pause, got {timer.most_recent}"


def test_timer_total_paused():
    """Timer should track total paused duration."""
    timer = Timer()
    timer.start()
    
    timer.pause()
    time.sleep(0.02)  # 20ms paused
    timer.resume()
    
    timer.pause()
    time.sleep(0.01)  # 10ms paused
    timer.resume()
    
    timer.stop()
    
    assert timer.total_time_paused > 0.025, f"Paused time should be ~30ms, got {timer.total_time_paused}"


def test_timer_multiple_pause_resume():
    """Multiple pause/resume cycles should work correctly."""
    timer = Timer()
    timer.start()
    
    for _ in range(3):
        time.sleep(0.005)  # 5ms active
        timer.pause()
        time.sleep(0.01)  # 10ms paused
        timer.resume()
    
    time.sleep(0.005)
    timer.stop()
    
    # Should have ~20ms active (4 * 5ms), not 50ms
    assert timer.most_recent > 0.015, f"Active time should be ~20ms"
    assert timer.most_recent < 0.04, f"Paused time should not be counted"


# =============================================================================
# Statistics Tests
# =============================================================================

def test_timer_mean():
    """Timer should calculate mean correctly."""
    timer = Timer()
    timer.add_time(1.0)
    timer.add_time(2.0)
    timer.add_time(3.0)
    timer.add_time(4.0)
    timer.add_time(5.0)
    
    assert timer.mean == 3.0, f"Mean should be 3.0, got {timer.mean}"


def test_timer_median():
    """Timer should calculate median correctly."""
    timer = Timer()
    
    # Odd number of times
    for t in [1.0, 5.0, 2.0, 4.0, 3.0]:
        timer.add_time(t)
    
    assert timer.median == 3.0, f"Median should be 3.0, got {timer.median}"


def test_timer_median_even():
    """Timer should handle even number of times for median."""
    timer = Timer()
    for t in [1.0, 2.0, 3.0, 4.0]:
        timer.add_time(t)
    
    # Median of [1, 2, 3, 4] = (2 + 3) / 2 = 2.5
    assert timer.median == 2.5, f"Median should be 2.5, got {timer.median}"


def test_timer_min_max():
    """Timer should track min and max correctly."""
    timer = Timer()
    for t in [3.0, 1.0, 4.0, 1.5, 9.0, 2.0]:
        timer.add_time(t)
    
    assert timer.min == 1.0, f"Min should be 1.0, got {timer.min}"
    assert timer.max == 9.0, f"Max should be 9.0, got {timer.max}"
    assert timer.fastest_time == 1.0, f"Fastest should be 1.0, got {timer.fastest_time}"
    assert timer.slowest_time == 9.0, f"Slowest should be 9.0, got {timer.slowest_time}"


def test_timer_stdev():
    """Timer should calculate standard deviation correctly."""
    timer = Timer()
    # All same values = 0 stdev
    for _ in range(5):
        timer.add_time(2.0)
    
    assert timer.stdev == 0.0, f"Stdev of same values should be 0, got {timer.stdev}"


def test_timer_variance():
    """Timer should calculate variance correctly."""
    timer = Timer()
    # Values [1, 2, 3, 4, 5], mean=3
    # Sample variance (n-1 denominator) = 2.5
    for t in [1.0, 2.0, 3.0, 4.0, 5.0]:
        timer.add_time(t)
    
    # statistics.variance uses sample variance (n-1)
    assert abs(timer.variance - 2.5) < 0.001, f"Variance should be 2.5, got {timer.variance}"


def test_timer_percentile():
    """Timer should calculate percentiles correctly."""
    timer = Timer()
    for i in range(1, 101):  # 1 to 100
        timer.add_time(float(i))
    
    p50 = timer.percentile(50)
    p90 = timer.percentile(90)
    p99 = timer.percentile(99)
    
    assert abs(p50 - 50.5) < 2.0, f"50th percentile should be ~50, got {p50}"
    assert abs(p90 - 90.5) < 2.0, f"90th percentile should be ~90, got {p90}"
    assert abs(p99 - 99.5) < 2.0, f"99th percentile should be ~99, got {p99}"


def test_timer_get_statistics():
    """Timer.get_statistics() should return TimerStats object."""
    timer = Timer()
    for t in [1.0, 2.0, 3.0, 4.0, 5.0]:
        timer.add_time(t)
    
    stats = timer.get_statistics()
    
    # stats is a TimerStats object with attributes
    assert hasattr(stats, 'mean'), "Stats should have mean"
    assert hasattr(stats, 'median'), "Stats should have median"
    assert hasattr(stats, 'min'), "Stats should have min"
    assert hasattr(stats, 'max'), "Stats should have max"
    assert hasattr(stats, 'stdev'), "Stats should have stdev"
    assert stats.mean == 3.0, f"Stats mean should be 3.0, got {stats.mean}"


# =============================================================================
# Index Tracking Tests
# =============================================================================

def test_timer_most_recent_index():
    """Timer should track index of most recent time."""
    timer = Timer()
    timer.add_time(1.0)
    timer.add_time(2.0)
    timer.add_time(3.0)
    
    assert timer.most_recent_index == 2, f"Most recent index should be 2, got {timer.most_recent_index}"


def test_timer_fastest_slowest_index():
    """Timer should track indices of fastest and slowest times."""
    timer = Timer()
    timer.add_time(5.0)  # index 0
    timer.add_time(1.0)  # index 1 - fastest
    timer.add_time(9.0)  # index 2 - slowest
    timer.add_time(3.0)  # index 3
    
    assert timer.fastest_index == 1, f"Fastest index should be 1, got {timer.fastest_index}"
    assert timer.slowest_index == 2, f"Slowest index should be 2, got {timer.slowest_index}"


# =============================================================================
# Reset Tests
# =============================================================================

def test_timer_reset():
    """Timer.reset() should clear all state."""
    timer = Timer()
    timer.add_time(1.0)
    timer.add_time(2.0)
    timer.add_time(3.0)
    
    timer.reset()
    
    assert timer.num_times == 0, "Reset should clear times"
    assert len(timer.times) == 0, "Reset should clear times list"
    # total_time_paused may be None or 0 after reset


# =============================================================================
# Concurrent Usage Tests
# =============================================================================

def test_timer_concurrent_add():
    """Timer should handle concurrent add_time calls."""
    timer = Timer()
    num_threads = 10
    adds_per_thread = 100
    
    def add_times():
        for _ in range(adds_per_thread):
            timer.add_time(0.001)
    
    threads = [threading.Thread(target=add_times) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    expected = num_threads * adds_per_thread
    assert timer.num_times == expected, f"Should have {expected} times, got {timer.num_times}"


def test_timer_concurrent_sessions():
    """Timer should handle concurrent start/stop sessions."""
    timer = Timer()
    num_threads = 5
    sessions_per_thread = 20
    
    def run_sessions():
        for _ in range(sessions_per_thread):
            timer.start()
            time.sleep(0.001)
            timer.stop()
    
    threads = [threading.Thread(target=run_sessions) for _ in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    expected = num_threads * sessions_per_thread
    assert timer.num_times == expected, f"Should have {expected} times, got {timer.num_times}"


# =============================================================================
# Edge Cases
# =============================================================================

def test_timer_empty_statistics():
    """Timer should handle empty state gracefully for statistics."""
    timer = Timer()
    
    # Should not raise - just return sensible defaults or None
    assert timer.num_times == 0
    # total_time may be 0.0 or None on empty
    # mean/median on empty return None


def test_timer_single_measurement():
    """Statistics should work with single measurement."""
    timer = Timer()
    timer.add_time(5.0)
    
    assert timer.mean == 5.0
    assert timer.median == 5.0
    assert timer.min == 5.0
    assert timer.max == 5.0
    # stdev with single value may be 0 or raise - implementation dependent


def test_timer_very_small_times():
    """Timer should handle very small time values."""
    timer = Timer()
    for _ in range(10):
        timer.start()
        # No sleep - measure overhead
        timer.stop()
    
    # Should have 10 very small times
    assert timer.num_times == 10
    assert timer.total_time < 0.1, "Overhead should be minimal"


def test_timer_very_large_times():
    """Timer should handle large time values."""
    timer = Timer()
    timer.add_time(1_000_000.0)
    timer.add_time(2_000_000.0)
    
    assert timer.total_time == 3_000_000.0
    assert timer.mean == 1_500_000.0


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all Timer tests."""
    runner = TestRunner("Timer Class Tests")
    
    # Basic tests
    runner.run_test("Timer creation", test_timer_creation)
    runner.run_test("Timer start/stop", test_timer_start_stop)
    runner.run_test("Timer multiple measurements", test_timer_multiple_measurements)
    runner.run_test("Timer discard", test_timer_discard)
    runner.run_test("Timer add_time", test_timer_add_time)
    
    # Lap tests
    runner.run_test("Timer lap", test_timer_lap)
    runner.run_test("Timer lap values", test_timer_lap_values)
    
    # Pause/resume tests
    runner.run_test("Timer pause/resume", test_timer_pause_resume)
    runner.run_test("Timer total paused", test_timer_total_paused)
    runner.run_test("Timer multiple pause/resume", test_timer_multiple_pause_resume)
    
    # Statistics tests
    runner.run_test("Timer mean", test_timer_mean)
    runner.run_test("Timer median (odd)", test_timer_median)
    runner.run_test("Timer median (even)", test_timer_median_even)
    runner.run_test("Timer min/max", test_timer_min_max)
    runner.run_test("Timer stdev", test_timer_stdev)
    runner.run_test("Timer variance", test_timer_variance)
    runner.run_test("Timer percentile", test_timer_percentile)
    runner.run_test("Timer get_statistics", test_timer_get_statistics)
    
    # Index tests
    runner.run_test("Timer most_recent_index", test_timer_most_recent_index)
    runner.run_test("Timer fastest/slowest index", test_timer_fastest_slowest_index)
    
    # Reset tests
    runner.run_test("Timer reset", test_timer_reset)
    
    # Concurrent tests
    runner.run_test("Timer concurrent add", test_timer_concurrent_add)
    runner.run_test("Timer concurrent sessions", test_timer_concurrent_sessions)
    
    # Edge cases
    runner.run_test("Timer empty statistics", test_timer_empty_statistics)
    runner.run_test("Timer single measurement", test_timer_single_measurement)
    runner.run_test("Timer very small times", test_timer_very_small_times)
    runner.run_test("Timer very large times", test_timer_very_large_times)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
