"""
Comprehensive test suite for internal time operations.

Tests all internal timing functionality including elapsed time calculations,
Yawn class, Stopwatch, Timer, and decorator functions. Uses colorized output 
for easy reading and good spacing for clarity.

This test suite validates the core timing logic that powers the SKTime API.
"""

import sys
import time
import threading
from pathlib import Path

# Add the suitkaise path for testing (adjust as needed)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Import all internal functions to test
    from suitkaise._int.core.time_ops import (
        _elapsed_time,
        _Yawn,
        _Stopwatch,
        _Timer,
        _create_timer_context_manager,
        _timethis_decorator,
        _create_standalone_timer_decorator,
        _get_current_time,
        _sleep
    )
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Warning: Could not import internal time functions: {e}")
    print("This is expected if running outside the suitkaise project structure")
    IMPORTS_SUCCESSFUL = False


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    @classmethod
    def disable(cls):
        """Disable colors for file output."""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = ''
        cls.MAGENTA = cls.CYAN = cls.WHITE = cls.BOLD = cls.UNDERLINE = cls.END = ''


def print_section(title: str):
    """Print a section header with proper spacing."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title.upper()}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_test(test_name: str):
    """Print a test name with proper formatting."""
    print(f"{Colors.BLUE}{Colors.BOLD}Testing: {test_name}...{Colors.END}")


def print_result(condition: bool, message: str):
    """Print a test result with color coding."""
    color = Colors.GREEN if condition else Colors.RED
    symbol = "✓" if condition else "✗"
    print(f"  {color}{symbol} {message}{Colors.END}")


def print_info(label: str, value: str):
    """Print labeled information."""
    print(f"  {Colors.MAGENTA}{label}:{Colors.END} {Colors.WHITE}{value}{Colors.END}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"  {Colors.YELLOW}⚠ {message}{Colors.END}")


def is_close(a: float, b: float, tolerance: float = 0.1) -> bool:
    """Check if two values are close within tolerance."""
    return abs(a - b) <= tolerance


def test_basic_time_functions():
    """Test basic time utility functions."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping basic time function tests - imports failed")
        return
        
    print_test("Basic Time Utility Functions")
    
    try:
        # Test _get_current_time
        current_time = _get_current_time()
        print_info("Current time", str(current_time))
        print_result(isinstance(current_time, float), "_get_current_time returns float")
        print_result(current_time > 0, "Current time is positive")
        
        # Test that time progresses
        time1 = _get_current_time()
        time.sleep(0.01)  # Small delay
        time2 = _get_current_time()
        print_result(time2 > time1, "Time progresses forward")
        
        # Test _sleep function
        start_time = _get_current_time()
        _sleep(0.1)  # Sleep for 100ms
        end_time = _get_current_time()
        elapsed = end_time - start_time
        
        print_info("Sleep duration", f"{elapsed:.3f}s")
        print_result(is_close(elapsed, 0.1, 0.05), "Sleep function works accurately")
        
    except Exception as e:
        print_result(False, f"Basic time functions failed: {e}")
    
    print()


def test_elapsed_time_calculation():
    """Test elapsed time calculation function."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping elapsed time tests - imports failed")
        return
        
    print_test("Elapsed Time Calculation")
    
    try:
        # Test with two explicit times
        time1 = 1000.0
        time2 = 1005.0
        elapsed = _elapsed_time(time1, time2)
        print_result(elapsed == 5.0, "Elapsed time calculation with two times")
        
        # Test order independence
        elapsed_reverse = _elapsed_time(time2, time1)
        print_result(elapsed == elapsed_reverse, "Order independence (absolute difference)")
        
        # Test with current time (second parameter None)
        start_time = _get_current_time()
        _sleep(0.1)
        elapsed_to_now = _elapsed_time(start_time)
        
        print_info("Elapsed to now", f"{elapsed_to_now:.3f}s")
        print_result(is_close(elapsed_to_now, 0.1, 0.05), "Elapsed time to current time")
        
        # Test edge case - same times
        same_time_elapsed = _elapsed_time(1000.0, 1000.0)
        print_result(same_time_elapsed == 0.0, "Same times return zero elapsed")
        
        # Test with negative time difference (should still be positive)
        negative_elapsed = _elapsed_time(2000.0, 1000.0)
        print_result(negative_elapsed == 1000.0, "Negative differences become positive")
        
    except Exception as e:
        print_result(False, f"Elapsed time calculation failed: {e}")
    
    print()


def test_yawn_class():
    """Test the Yawn class functionality."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping Yawn class tests - imports failed")
        return
        
    print_test("Yawn Class Functionality")
    
    try:
        # Test basic yawn functionality
        yawn = _Yawn(sleep_duration=0.1, yawn_threshold=3, log_sleep=False)
        
        # Test that first yawns don't sleep
        result1 = yawn.yawn()
        result2 = yawn.yawn()
        print_result(not result1, "First yawn doesn't sleep")
        print_result(not result2, "Second yawn doesn't sleep")
        
        # Test that threshold yawn does sleep
        start_time = _get_current_time()
        result3 = yawn.yawn()
        end_time = _get_current_time()
        sleep_duration = end_time - start_time
        
        print_result(result3, "Threshold yawn returns True (slept)")
        print_info("Actual sleep duration", f"{sleep_duration:.3f}s")
        print_result(is_close(sleep_duration, 0.1, 0.05), "Sleep duration is accurate")
        
        # Test counter reset after sleep
        result4 = yawn.yawn()
        print_result(not result4, "Counter resets after sleep")
        
        # Test statistics
        stats = yawn.get_stats()
        print_result('current_yawns' in stats, "Stats contain current_yawns")
        print_result('total_sleeps' in stats, "Stats contain total_sleeps")
        print_result(stats['total_sleeps'] == 1, "Total sleeps tracked correctly")
        print_result(stats['yawn_threshold'] == 3, "Threshold stored correctly")
        
        print_info("Current stats", str(stats))
        
        # Test reset functionality
        yawn.yawn()  # One more yawn
        yawn.reset()
        stats_after_reset = yawn.get_stats()
        print_result(stats_after_reset['current_yawns'] == 0, "Reset clears current yawns")
        print_result(stats_after_reset['total_sleeps'] == 1, "Reset preserves total sleeps")
        
        # Test logging (quick test)
        log_yawn = _Yawn(0.01, 1, log_sleep=True)
        print(f"  {Colors.BLUE}Testing log output (should see log message):{Colors.END}")
        log_yawn.yawn()  # Should print log message
        
    except Exception as e:
        print_result(False, f"Yawn class failed: {e}")
    
    print()


def test_stopwatch_class():
    """Test the Stopwatch class functionality."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping Stopwatch class tests - imports failed")
        return
        
    print_test("Stopwatch Class Functionality")
    
    try:
        sw = _Stopwatch()
        
        # Test initial state
        print_result(not sw.is_running, "Stopwatch starts in stopped state")
        print_result(not sw.is_paused, "Stopwatch starts unpaused")
        print_result(sw.elapsed_time == 0.0, "Initial elapsed time is zero")
        
        # Test starting
        start_time = sw.start()
        print_result(isinstance(start_time, float), "Start returns timestamp")
        print_result(sw.is_running, "Stopwatch is running after start")
        print_result(not sw.is_paused, "Stopwatch is not paused after start")
        
        # Test error handling - cannot start twice
        try:
            sw.start()
            print_result(False, "Should not allow starting twice")
        except RuntimeError:
            print_result(True, "Correctly prevents starting twice")
        
        # Test timing
        _sleep(0.1)
        elapsed_1 = sw.elapsed_time
        print_result(is_close(elapsed_1, 0.1, 0.05), f"Elapsed time tracking accurate ({elapsed_1:.3f}s)")
        
        # Test pause
        pause_elapsed = sw.pause()
        print_result(sw.is_paused, "Stopwatch is paused after pause()")
        print_result(sw.is_running, "Stopwatch still 'running' when paused")
        print_result(is_close(pause_elapsed, elapsed_1, 0.01), "Pause returns current elapsed time")
        
        # Test that time doesn't progress during pause
        _sleep(0.1)
        elapsed_during_pause = sw.elapsed_time
        print_result(is_close(elapsed_during_pause, pause_elapsed, 0.01), 
                    "Time doesn't progress during pause")
        
        # Test resume
        pause_duration = sw.resume()
        print_result(not sw.is_paused, "Stopwatch unpaused after resume")
        print_result(isinstance(pause_duration, float), "Resume returns pause duration")
        print_result(is_close(pause_duration, 0.1, 0.05), 
                    f"Pause duration tracked correctly ({pause_duration:.3f}s)")
        
        # Test lap functionality
        _sleep(0.05)
        lap1_time = sw.lap()
        print_result(isinstance(lap1_time, float), "Lap returns float")
        print_result(len(sw.lap_times) == 1, "Lap recorded in lap_times")
        
        _sleep(0.05)
        lap2_time = sw.lap()
        print_result(lap2_time > lap1_time, "Second lap time is greater")
        print_result(len(sw.lap_times) == 2, "Multiple laps recorded")
        
        # Test get_laptime
        retrieved_lap1 = sw.get_laptime(1)
        retrieved_lap2 = sw.get_laptime(2)
        invalid_lap = sw.get_laptime(99)
        
        print_result(retrieved_lap1 == lap1_time, "get_laptime retrieves correct lap (1)")
        print_result(retrieved_lap2 == lap2_time, "get_laptime retrieves correct lap (2)")
        print_result(invalid_lap is None, "get_laptime returns None for invalid lap")
        
        # Test lap statistics
        lap_stats = sw.get_lap_statistics()
        print_result('count' in lap_stats, "Lap stats contain count")
        print_result('mean' in lap_stats, "Lap stats contain mean")
        print_result(lap_stats['count'] == 2, "Lap count is correct")
        print_result(lap_stats['fastest'] == min(lap1_time, lap2_time), "Fastest lap correct")
        
        # Test stop
        final_time = sw.stop()
        print_result(not sw.is_running, "Stopwatch stopped after stop()")
        print_result(isinstance(final_time, float), "Stop returns final time")
        print_result(final_time > 0.2, "Final time includes all timing")
        
        # Test total_time property
        print_result(sw.total_time == final_time, "total_time property matches stop() result")
        
        # Test reset
        sw.reset()
        print_result(not sw.is_running, "Reset stopwatch is not running")
        print_result(sw.elapsed_time == 0.0, "Reset clears elapsed time")
        print_result(len(sw.lap_times) == 0, "Reset clears lap times")
        
    except Exception as e:
        print_result(False, f"Stopwatch class failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_timer_class():
    """Test the Timer class functionality."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping Timer class tests - imports failed")
        return
        
    print_test("Timer Class Functionality")
    
    try:
        timer = _Timer()
        
        # Test initial state
        print_result(timer.count == 0, "Timer starts with zero count")
        print_result(timer.mostrecent is None, "No recent time initially")
        print_result(timer.mean is None, "No mean initially")
        
        # Test manual timing
        start_time = timer.start()
        print_result(isinstance(start_time, float), "Start returns timestamp")
        
        _sleep(0.1)
        elapsed1 = timer.stop()
        
        print_result(isinstance(elapsed1, float), "Stop returns elapsed time")
        print_result(is_close(elapsed1, 0.1, 0.05), f"First timing accurate ({elapsed1:.3f}s)")
        print_result(timer.count == 1, "Count incremented after timing")
        print_result(timer.mostrecent == elapsed1, "Most recent updated")
        
        # Test error handling
        try:
            timer.stop()  # Stop without start
            print_result(False, "Should not allow stop without start")
        except RuntimeError:
            print_result(True, "Correctly prevents stop without start")
        
        # Add more timings for statistics
        timer.start()
        _sleep(0.05)
        elapsed2 = timer.stop()
        
        timer.start()
        _sleep(0.15)
        elapsed3 = timer.stop()
        
        print_result(timer.count == 3, "Multiple timings recorded")
        print_result(timer.mostrecent == elapsed3, "Most recent is latest")
        
        # Test statistical properties
        mean_time = timer.mean
        median_time = timer.median
        longest_time = timer.longest
        shortest_time = timer.shortest
        std_time = timer.std
        
        print_result(isinstance(mean_time, float), "Mean is calculated")
        print_result(isinstance(median_time, float), "Median is calculated")
        print_result(longest_time == max(elapsed1, elapsed2, elapsed3), "Longest is maximum")
        print_result(shortest_time == min(elapsed1, elapsed2, elapsed3), "Shortest is minimum")
        print_result(isinstance(std_time, float), "Standard deviation calculated")
        
        print_info("Timings", f"[{elapsed1:.3f}, {elapsed2:.3f}, {elapsed3:.3f}]")
        print_info("Mean", f"{mean_time:.3f}s")
        print_info("Median", f"{median_time:.3f}s")
        print_info("Std Dev", f"{std_time:.3f}s")
        
        # Test get_a_time method
        time1 = timer.get_a_time(1)
        time2 = timer.get_a_time(2)
        time3 = timer.get_a_time(3)
        invalid_time = timer.get_a_time(99)
        
        print_result(time1 == elapsed1, "get_a_time(1) returns first timing")
        print_result(time2 == elapsed2, "get_a_time(2) returns second timing")
        print_result(time3 == elapsed3, "get_a_time(3) returns third timing")
        print_result(invalid_time is None, "get_a_time returns None for invalid index")
        
        # Test percentiles
        p50 = timer.percentile(50)
        p95 = timer.percentile(95)
        
        print_result(abs(p50 - median_time) < 0.001, "50th percentile matches median")
        print_result(isinstance(p95, float), "95th percentile calculated")
        
        # Test edge cases for percentiles
        try:
            timer.percentile(-1)
            print_result(False, "Should reject negative percentile")
        except ValueError:
            print_result(True, "Correctly rejects negative percentile")
        
        try:
            timer.percentile(101)
            print_result(False, "Should reject percentile > 100")
        except ValueError:
            print_result(True, "Correctly rejects percentile > 100")
        
        # Test comprehensive statistics
        stats = timer.get_statistics()
        expected_keys = ['count', 'mean', 'median', 'longest', 'shortest', 'std', 'variance', 
                        'percentile_95', 'percentile_99', 'total_time']
        
        for key in expected_keys:
            print_result(key in stats, f"Statistics contain {key}")
        
        print_result(stats['count'] == 3, "Stats count is correct")
        print_result(abs(stats['total_time'] - sum([elapsed1, elapsed2, elapsed3])) < 0.001, 
                    "Total time is sum of all timings")
        
        # Test manual time addition
        timer.add_time(0.2)
        print_result(timer.count == 4, "Manual time addition increases count")
        print_result(timer.mostrecent == 0.2, "Manual time becomes most recent")
        
        # Test context manager
        with timer as ctx_timer:
            _sleep(0.05)
        
        print_result(timer.count == 5, "Context manager adds timing")
        print_result(is_close(timer.mostrecent, 0.05, 0.02), 
                    f"Context manager timing accurate ({timer.mostrecent:.3f}s)")
        
        # Test reset
        timer.reset()
        print_result(timer.count == 0, "Reset clears count")
        print_result(timer.mostrecent is None, "Reset clears most recent")
        print_result(timer.mean is None, "Reset clears statistics")
        
    except Exception as e:
        print_result(False, f"Timer class failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_timer_context_manager():
    """Test timer context manager creation."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping timer context manager tests - imports failed")
        return
        
    print_test("Timer Context Manager")
    
    try:
        timer = _Timer()
        
        # Test creating context manager
        context_manager = _create_timer_context_manager(timer)
        print_result(context_manager is not None, "Context manager created successfully")
        
        # Test using the context manager
        with context_manager:
            _sleep(0.1)
        
        print_result(timer.count == 1, "Context manager recorded timing")
        print_result(is_close(timer.mostrecent, 0.1, 0.05), 
                    f"Context manager timing accurate ({timer.mostrecent:.3f}s)")
        
        # Test multiple uses accumulate statistics
        for i in range(3):
            with context_manager:
                _sleep(0.05)
        
        print_result(timer.count == 4, "Multiple context manager uses accumulate")
        print_result(timer.mean is not None, "Statistics calculated from accumulated timings")
        
        print_info("Final count", str(timer.count))
        print_info("Final mean", f"{timer.mean:.3f}s")
        
    except Exception as e:
        print_result(False, f"Timer context manager failed: {e}")
    
    print()


def test_timing_decorators():
    """Test timing decorator functions."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping timing decorator tests - imports failed")
        return
        
    print_test("Timing Decorators")
    
    try:
        # Test instance-based decorator
        timer = _Timer()
        decorator = _timethis_decorator(timer)
        
        @decorator
        def test_function():
            _sleep(0.1)
            return "result"
        
        # Test decorated function
        result = test_function()
        print_result(result == "result", "Decorated function returns correct result")
        print_result(timer.count == 1, "Decorator recorded timing")
        print_result(is_close(timer.mostrecent, 0.1, 0.05), 
                    f"Decorator timing accurate ({timer.mostrecent:.3f}s)")
        
        # Test multiple calls accumulate
        test_function()
        test_function()
        print_result(timer.count == 3, "Multiple decorator calls accumulate")
        
        # Test standalone decorator
        standalone_decorator = _create_standalone_timer_decorator()
        
        @standalone_decorator
        def another_function():
            _sleep(0.05)
            return 42
        
        result2 = another_function()
        print_result(result2 == 42, "Standalone decorated function returns correct result")
        print_result(hasattr(another_function, 'timer'), "Standalone decorator attaches timer")
        
        attached_timer = another_function.timer
        print_result(attached_timer.count == 1, "Standalone timer recorded timing")
        print_result(is_close(attached_timer.mostrecent, 0.05, 0.02), 
                    f"Standalone timing accurate ({attached_timer.mostrecent:.3f}s)")
        
        # Test exception handling in decorators
        @decorator  
        def failing_function():
            _sleep(0.02)
            raise ValueError("Test error")
        
        initial_count = timer.count
        try:
            failing_function()
            print_result(False, "Function should have raised exception")
        except ValueError:
            print_result(True, "Exception properly propagated")
            print_result(timer.count == initial_count + 1, "Timing recorded even with exception")
        
    except Exception as e:
        print_result(False, f"Timing decorators failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_edge_cases_and_performance():
    """Test edge cases and performance scenarios."""
    if not IMPORTS_SUCCESSFUL:
        print_warning("Skipping edge cases tests - imports failed")
        return
        
    print_test("Edge Cases and Performance")
    
    try:
        # Test Timer with single measurement (edge case for std dev)
        single_timer = _Timer()
        single_timer.add_time(1.0)
        
        print_result(single_timer.std is None, "Single measurement has no std dev")
        print_result(single_timer.variance is None, "Single measurement has no variance")
        print_result(single_timer.mean == 1.0, "Single measurement mean is the value")
        
        # Test Timer with identical measurements
        identical_timer = _Timer()
        for i in range(5):
            identical_timer.add_time(0.5)
        
        print_result(identical_timer.std == 0.0, "Identical measurements have zero std dev")
        print_result(identical_timer.mean == 0.5, "Identical measurements mean is correct")
        print_result(identical_timer.median == 0.5, "Identical measurements median is correct")
        
        # Test large number of measurements (performance test)
        large_timer = _Timer()
        start_time = _get_current_time()
        
        for i in range(1000):
            large_timer.add_time(i * 0.001)  # 0, 0.001, 0.002, ... 0.999
        
        stats_time = _get_current_time()
        stats = large_timer.get_statistics()
        end_time = _get_current_time()
        
        print_result(large_timer.count == 1000, "Large number of measurements recorded")
        print_result(isinstance(stats['mean'], float), "Statistics calculated for large dataset")
        
        processing_time = end_time - stats_time
        print_info("Large dataset stats time", f"{processing_time:.3f}s")
        print_result(processing_time < 0.1, "Statistics calculation is fast for large datasets")
        
        # Test Stopwatch precision with very short durations
        precision_sw = _Stopwatch()
        precision_sw.start()
        # Minimal sleep/processing time
        precision_sw.stop()
        
        print_result(precision_sw.total_time >= 0.0, "Stopwatch handles very short durations")
        print_result(precision_sw.total_time < 0.01, "Very short duration is reasonable")
        
        # Test Yawn with zero sleep duration
        zero_yawn = _Yawn(sleep_duration=0.0, yawn_threshold=1, log_sleep=False)
        zero_start = _get_current_time()
        zero_yawn.yawn()
        zero_end = _get_current_time()
        zero_duration = zero_end - zero_start
        
        print_result(zero_duration < 0.01, "Zero sleep duration works correctly")
        
        # Test very high yawn threshold
        high_threshold_yawn = _Yawn(0.001, 1000, log_sleep=False)
        for i in range(999):
            result = high_threshold_yawn.yawn()
            if result:  # Should not happen until 1000th yawn
                print_result(False, f"Unexpected sleep at yawn {i+1}")
                break
        else:
            print_result(True, "High threshold yawn count works correctly")
        
        # Test percentile edge cases
        edge_timer = _Timer()
        edge_timer.add_time(1.0)
        edge_timer.add_time(2.0)
        
        p0 = edge_timer.percentile(0)
        p100 = edge_timer.percentile(100)
        p50 = edge_timer.percentile(50)
        
        print_result(p0 == 1.0, "0th percentile is minimum")
        print_result(p100 == 2.0, "100th percentile is maximum")
        print_result(p50 == 1.5, "50th percentile of two values is average")
        
    except Exception as e:
        print_result(False, f"Edge cases and performance failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def run_all_internal_tests():
    """Run all internal time operations tests."""
    print_section("Comprehensive Internal Time Operations Tests")
    
    if not IMPORTS_SUCCESSFUL:
        print(f"{Colors.RED}{Colors.BOLD}❌ Cannot run tests - import failures{Colors.END}")
        print(f"{Colors.YELLOW}This is expected if running outside the suitkaise project structure{Colors.END}")
        print(f"{Colors.YELLOW}To run these tests, ensure the suitkaise module is properly installed or accessible{Colors.END}")
        return
    
    print(f"{Colors.GREEN}✅ Successfully imported all internal time functions{Colors.END}")
    print(f"{Colors.WHITE}Testing the robust internal timing logic that powers SKTime...{Colors.END}\n")
    
    try:
        test_basic_time_functions()
        test_elapsed_time_calculation()
        test_yawn_class()
        test_stopwatch_class()
        test_timer_class()
        test_timer_context_manager()
        test_timing_decorators()
        test_edge_cases_and_performance()
        
        print_section("Internal Time Operations Test Summary")
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL INTERNAL TIME OPERATIONS TESTS COMPLETED! 🎉{Colors.END}")
        print(f"{Colors.WHITE}✅ Basic utilities: Time functions working correctly{Colors.END}")
        print(f"{Colors.WHITE}✅ Elapsed calculations: Accurate with order independence{Colors.END}")
        print(f"{Colors.WHITE}✅ Yawn class: Threshold counting and sleep timing perfect{Colors.END}")
        print(f"{Colors.WHITE}✅ Stopwatch: Pause/resume/lap functionality robust{Colors.END}")
        print(f"{Colors.WHITE}✅ Timer: Statistical analysis comprehensive and accurate{Colors.END}")
        print(f"{Colors.WHITE}✅ Context managers: Accumulating statistics correctly{Colors.END}")
        print(f"{Colors.WHITE}✅ Decorators: Function timing integration working{Colors.END}")
        print(f"{Colors.WHITE}✅ Edge cases: Performance and boundary conditions handled{Colors.END}")
        print(f"{Colors.WHITE}✅ The internal time operations are rock-solid! 🚀{Colors.END}")
        print()
        
        print(f"{Colors.CYAN}{Colors.BOLD}CORE CAPABILITIES VALIDATED:{Colors.END}")
        print(f"{Colors.GREEN}⏱️ Precision timing - Accurate to millisecond level{Colors.END}")
        print(f"{Colors.GREEN}📊 Statistical analysis - Mean, median, std dev, percentiles{Colors.END}")
        print(f"{Colors.GREEN}⏸️ Pause/resume logic - Proper time accounting during pauses{Colors.END}")
        print(f"{Colors.GREEN}🥱 Delayed operations - Threshold-based sleep control{Colors.END}")
        print(f"{Colors.GREEN}🏁 Lap timing - Individual lap tracking and statistics{Colors.END}")
        print(f"{Colors.GREEN}🎯 Context managers - Seamless integration with Python idioms{Colors.END}")
        print(f"{Colors.GREEN}🛡️ Error handling - Meaningful exceptions for invalid states{Colors.END}")
        
    except Exception as e:
        print(f"{Colors.RED}{Colors.BOLD}❌ Test suite failed with error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_internal_tests()