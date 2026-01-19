"""
TimeThis Context Manager Tests

Tests the TimeThis context manager functionality:
- Basic usage with auto-created timer
- Usage with explicit timer
- Threshold parameter
- Pause/resume within context
- Lap timing within context
- Exception handling
"""

import sys
import time as stdlib_time

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.timing import Sktimer, TimeThis


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
# Basic TimeThis Tests
# =============================================================================

def test_timethis_auto_timer():
    """TimeThis() without timer should create one."""
    with TimeThis() as timer:
        stdlib_time.sleep(0.01)
    
    assert timer.num_times == 1, f"Should have 1 measurement, got {timer.num_times}"
    assert timer.most_recent >= 0.008, f"Should be ~10ms, got {timer.most_recent}"


def test_timethis_returns_timer():
    """TimeThis should yield the timer."""
    with TimeThis() as timer:
        pass
    
    assert isinstance(timer, Sktimer), "Should yield a Sktimer"


def test_timethis_times_block():
    """TimeThis should time the code block."""
    with TimeThis() as timer:
        stdlib_time.sleep(0.02)
    
    assert timer.most_recent >= 0.018, f"Should time ~20ms, got {timer.most_recent}"
    assert timer.most_recent < 0.05, f"Should not be too long, got {timer.most_recent}"


# =============================================================================
# TimeThis with Explicit Sktimer Tests
# =============================================================================

def test_timethis_explicit_timer():
    """TimeThis with explicit timer should use it."""
    my_timer = Sktimer()
    
    with TimeThis(my_timer) as timer:
        stdlib_time.sleep(0.01)
    
    assert timer is my_timer, "Should return same timer"
    assert my_timer.num_times == 1


def test_timethis_explicit_timer_accumulates():
    """Multiple TimeThis blocks should accumulate in explicit timer."""
    my_timer = Sktimer()
    
    for _ in range(5):
        with TimeThis(my_timer):
            stdlib_time.sleep(0.005)
    
    assert my_timer.num_times == 5, f"Should have 5 measurements, got {my_timer.num_times}"


def test_timethis_explicit_timer_preserves_existing():
    """TimeThis should preserve existing times in explicit timer."""
    my_timer = Sktimer()
    my_timer.add_time(1.0)
    my_timer.add_time(2.0)
    
    with TimeThis(my_timer):
        stdlib_time.sleep(0.01)
    
    assert my_timer.num_times == 3, f"Should have 3 measurements, got {my_timer.num_times}"
    assert my_timer.times[0] == 1.0
    assert my_timer.times[1] == 2.0


# =============================================================================
# TimeThis Threshold Tests
# =============================================================================

def test_timethis_threshold_records():
    """TimeThis should record times above threshold."""
    timer = Sktimer()
    
    with TimeThis(timer, threshold=0.005):
        stdlib_time.sleep(0.02)  # Above threshold
    
    assert timer.num_times == 1, "Should record time above threshold"


def test_timethis_threshold_discards():
    """TimeThis should discard times below threshold."""
    timer = Sktimer()
    
    with TimeThis(timer, threshold=0.1):
        pass  # Nearly instant, below threshold
    
    assert timer.num_times == 0, f"Should not record below threshold, got {timer.num_times}"


def test_timethis_threshold_at_boundary():
    """TimeThis should handle times at boundary."""
    timer = Sktimer()
    
    # Time that's exactly at threshold
    with TimeThis(timer, threshold=0.0):
        pass
    
    assert timer.num_times == 1, "Threshold 0 should record everything"


# =============================================================================
# TimeThis Pause/Resume Tests
# =============================================================================

def test_timethis_pause_resume():
    """TimeThis should support pause/resume via timer."""
    timer = Sktimer()
    
    with TimeThis(timer) as t:
        stdlib_time.sleep(0.01)  # 10ms active
        t.pause()
        stdlib_time.sleep(0.02)  # 20ms paused (excluded)
        t.resume()
        stdlib_time.sleep(0.01)  # 10ms active
    
    # Should record ~20ms, not 40ms
    assert timer.most_recent >= 0.015, f"Should be ~20ms, got {timer.most_recent}"
    assert timer.most_recent < 0.035, f"Should exclude pause, got {timer.most_recent}"


def test_timethis_multiple_pauses():
    """TimeThis should handle multiple pause/resume cycles."""
    timer = Sktimer()
    
    with TimeThis(timer) as t:
        for _ in range(3):
            stdlib_time.sleep(0.005)  # 5ms active
            t.pause()
            stdlib_time.sleep(0.01)  # 10ms paused
            t.resume()
        stdlib_time.sleep(0.005)  # 5ms active
    
    # Total active: 4 * 5ms = 20ms
    assert timer.most_recent >= 0.015, f"Should be ~20ms active"
    assert timer.most_recent < 0.045, f"Should exclude pauses"


# =============================================================================
# TimeThis Lap Tests
# =============================================================================

def test_timethis_lap():
    """TimeThis should support lap timing."""
    timer = Sktimer()
    
    with TimeThis(timer) as t:
        stdlib_time.sleep(0.01)
        t.lap()
        stdlib_time.sleep(0.01)
        t.lap()
        stdlib_time.sleep(0.01)
    
    # lap() records intermediate times
    # Final exit records last segment
    # Total should be 3 or 4 measurements depending on implementation
    assert timer.num_times >= 3, f"Should have lap times, got {timer.num_times}"


# =============================================================================
# TimeThis Exception Handling Tests
# =============================================================================

def test_timethis_exception_still_times():
    """TimeThis should record time even on exception."""
    timer = Sktimer()
    
    try:
        with TimeThis(timer):
            stdlib_time.sleep(0.01)
            raise ValueError("test")
    except ValueError:
        pass
    
    assert timer.num_times == 1, f"Should record time on exception, got {timer.num_times}"


def test_timethis_exception_propagates():
    """TimeThis should propagate exceptions."""
    try:
        with TimeThis():
            raise TypeError("specific error")
        assert False, "Should have raised"
    except TypeError as e:
        assert "specific error" in str(e)


def test_timethis_exception_below_threshold():
    """TimeThis should not record if exception before threshold."""
    timer = Sktimer()
    
    try:
        with TimeThis(timer, threshold=0.1):
            raise ValueError("quick failure")
    except ValueError:
        pass
    
    # Quick exception, below 100ms threshold
    assert timer.num_times == 0, f"Should not record below threshold, got {timer.num_times}"


# =============================================================================
# TimeThis Nested Tests
# =============================================================================

def test_timethis_nested_different_timers():
    """Nested TimeThis with different timers should work."""
    outer_timer = Sktimer()
    inner_timer = Sktimer()
    
    with TimeThis(outer_timer):
        stdlib_time.sleep(0.01)
        with TimeThis(inner_timer):
            stdlib_time.sleep(0.01)
        stdlib_time.sleep(0.01)
    
    assert outer_timer.num_times == 1
    assert inner_timer.num_times == 1
    assert outer_timer.most_recent > inner_timer.most_recent


def test_timethis_nested_same_timer():
    """Nested TimeThis with same timer should record both."""
    timer = Sktimer()
    
    with TimeThis(timer):
        stdlib_time.sleep(0.01)
        with TimeThis(timer):
            stdlib_time.sleep(0.01)
    
    # Both contexts record to same timer
    assert timer.num_times == 2


# =============================================================================
# TimeThis Edge Cases
# =============================================================================

def test_timethis_empty_block():
    """TimeThis should handle empty block."""
    timer = Sktimer()
    
    with TimeThis(timer):
        pass
    
    assert timer.num_times == 1
    assert timer.most_recent < 0.01, "Empty block should be fast"


def test_timethis_quick_succession():
    """TimeThis should handle rapid successive uses."""
    timer = Sktimer()
    
    for _ in range(100):
        with TimeThis(timer):
            pass
    
    assert timer.num_times == 100


def test_timethis_access_timer_inside():
    """Should be able to access timer properties inside block."""
    with TimeThis() as timer:
        stdlib_time.sleep(0.01)
        # Can't check most_recent inside since stop() not called yet
        # But can verify timer exists
        assert timer is not None


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all TimeThis tests."""
    runner = TestRunner("TimeThis Context Manager Tests")
    
    # Basic tests
    runner.run_test("TimeThis auto timer", test_timethis_auto_timer)
    runner.run_test("TimeThis returns timer", test_timethis_returns_timer)
    runner.run_test("TimeThis times block", test_timethis_times_block)
    
    # Explicit timer tests
    runner.run_test("TimeThis explicit timer", test_timethis_explicit_timer)
    runner.run_test("TimeThis explicit accumulates", test_timethis_explicit_timer_accumulates)
    runner.run_test("TimeThis preserves existing", test_timethis_explicit_timer_preserves_existing)
    
    # Threshold tests
    runner.run_test("TimeThis threshold records", test_timethis_threshold_records)
    runner.run_test("TimeThis threshold discards", test_timethis_threshold_discards)
    runner.run_test("TimeThis threshold boundary", test_timethis_threshold_at_boundary)
    
    # Pause/resume tests
    runner.run_test("TimeThis pause/resume", test_timethis_pause_resume)
    runner.run_test("TimeThis multiple pauses", test_timethis_multiple_pauses)
    
    # Lap tests
    runner.run_test("TimeThis lap", test_timethis_lap)
    
    # Exception tests
    runner.run_test("TimeThis exception still times", test_timethis_exception_still_times)
    runner.run_test("TimeThis exception propagates", test_timethis_exception_propagates)
    runner.run_test("TimeThis exception below threshold", test_timethis_exception_below_threshold)
    
    # Nested tests
    runner.run_test("TimeThis nested different timers", test_timethis_nested_different_timers)
    runner.run_test("TimeThis nested same timer", test_timethis_nested_same_timer)
    
    # Edge cases
    runner.run_test("TimeThis empty block", test_timethis_empty_block)
    runner.run_test("TimeThis quick succession", test_timethis_quick_succession)
    runner.run_test("TimeThis access timer inside", test_timethis_access_timer_inside)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
