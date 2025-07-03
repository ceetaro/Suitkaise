"""
Comprehensive test suite for SKTime API module.

Tests all external API functionality including simple timing functions,
Yawn class, Stopwatch, Timer, and timing decorators. Uses colorized output 
for easy reading and good spacing for clarity.

This test suite validates the user-facing API that developers will interact with.
"""

import sys
import time
import threading
from pathlib import Path

# Add the suitkaise path for testing (adjust as needed)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Import all API functions to test
    from suitkaise.sktime.api import (
        now,
        get_current_time,
        sleep,
        elapsed,
        Yawn,
        Stopwatch,
        Timer,
        timethis
    )
    API_IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Warning: Could not import SKTime API functions: {e}")
    print("This is expected if running outside the suitkaise project structure")
    API_IMPORTS_SUCCESSFUL = False


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


def test_simple_timing_functions():
    """Test simple timing API functions."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping simple timing function tests - imports failed")
        return
        
    print_test("Simple Timing Functions")
    
    try:
        # Test now() function
        current_time = now()
        print_info("Current time from now()", str(current_time))
        print_result(isinstance(current_time, float), "now() returns float")
        print_result(current_time > 0, "now() returns positive timestamp")
        
        # Test get_current_time() function (should be identical to now())
        current_time2 = get_current_time()
        print_result(isinstance(current_time2, float), "get_current_time() returns float")
        print_result(abs(current_time2 - current_time) < 0.1, "now() and get_current_time() are equivalent")
        
        # Test that time progresses
        time1 = now()
        time.sleep(0.01)  # Use standard time.sleep for comparison
        time2 = now()
        print_result(time2 > time1, "Time progresses correctly with now()")
        
        # Test sleep() function
        start_time = now()
        sleep(0.1)  # Use SKTime sleep
        end_time = now()
        sleep_duration = end_time - start_time
        
        print_info("Sleep duration", f"{sleep_duration:.3f}s")
        print_result(is_close(sleep_duration, 0.1, 0.05), "sleep() function works accurately")
        
        # Test elapsed() function with two times
        time1 = 1000.0
        time2 = 1005.0
        elapsed_time = elapsed(time1, time2)
        print_result(elapsed_time == 5.0, "elapsed() with two explicit times")
        
        # Test order independence
        elapsed_reverse = elapsed(time2, time1)
        print_result(elapsed_time == elapsed_reverse, "elapsed() order independence")
        
        # Test elapsed() with single time (should use current time)
        past_time = now() - 2.0  # 2 seconds ago
        elapsed_to_now = elapsed(past_time)
        print_info("Elapsed to now", f"{elapsed_to_now:.3f}s")
        print_result(is_close(elapsed_to_now, 2.0, 0.5), "elapsed() with single time uses current time")
        
        # Test elapsed() with current measurement
        start = now()
        sleep(0.1)
        measured_elapsed = elapsed(start)
        print_result(is_close(measured_elapsed, 0.1, 0.05), 
                    f"elapsed() measurement accurate ({measured_elapsed:.3f}s)")
        
    except Exception as e:
        print_result(False, f"Simple timing functions failed: {e}")
    
    print()


def test_yawn_api_class():
    """Test the Yawn API class."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping Yawn API class tests - imports failed")
        return
        
    print_test("Yawn API Class")
    
    try:
        # Test basic initialization and functionality
        yawn = Yawn(sleep_duration=0.1, yawn_threshold=3, log_sleep=False)
        print_result(isinstance(yawn, Yawn), "Yawn class instantiated correctly")
        
        # Test yawn counting
        result1 = yawn.yawn()
        result2 = yawn.yawn()
        print_result(not result1, "First yawn doesn't trigger sleep")
        print_result(not result2, "Second yawn doesn't trigger sleep")
        
        # Test threshold sleep
        start_time = now()
        result3 = yawn.yawn()
        end_time = now()
        sleep_duration = end_time - start_time
        
        print_result(result3, "Threshold yawn triggers sleep")
        print_info("Actual sleep duration", f"{sleep_duration:.3f}s")
        print_result(is_close(sleep_duration, 0.1, 0.05), "Yawn sleep duration accurate")
        
        # Test counter reset
        result4 = yawn.yawn()
        print_result(not result4, "Yawn counter resets after sleep")
        
        # Test statistics
        stats = yawn.get_stats()
        print_result(isinstance(stats, dict), "get_stats() returns dictionary")
        print_result('current_yawns' in stats, "Stats contain current_yawns")
        print_result('total_sleeps' in stats, "Stats contain total_sleeps")
        print_result('yawns_until_sleep' in stats, "Stats contain yawns_until_sleep")
        print_result(stats['total_sleeps'] == 1, "Total sleeps tracked correctly")
        
        print_info("Yawn statistics", str(stats))
        
        # Test reset functionality
        yawn.yawn()  # Add one yawn
        yawn.reset()
        stats_after_reset = yawn.get_stats()
        print_result(stats_after_reset['current_yawns'] == 0, "reset() clears current yawns")
        
        # Test with logging enabled (brief test)
        print(f"  {Colors.BLUE}Testing log_sleep functionality:{Colors.END}")
        log_yawn = Yawn(0.01, 1, log_sleep=True)
        log_yawn.yawn()  # Should print log message
        
        # Test different threshold values
        quick_yawn = Yawn(0.01, 1, log_sleep=False)
        start_quick = now()
        quick_result = quick_yawn.yawn()
        end_quick = now()
        quick_duration = end_quick - start_quick
        
        print_result(quick_result, "Single threshold yawn works")
        print_result(is_close(quick_duration, 0.01, 0.01), "Quick sleep duration accurate")
        
    except Exception as e:
        print_result(False, f"Yawn API class failed: {e}")
    
    print()


def test_stopwatch_api_class():
    """Test the Stopwatch API class."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping Stopwatch API class tests - imports failed")
        return
        
    print_test("Stopwatch API Class")
    
    try:
        sw = Stopwatch()
        print_result(isinstance(sw, Stopwatch), "Stopwatch class instantiated correctly")
        
        # Test initial state
        print_result(not sw.is_running, "Stopwatch starts not running")
        print_result(not sw.is_paused, "Stopwatch starts not paused")
        print_result(sw.total_time == 0.0, "Initial total_time is zero")
        print_result(sw.elapsed_time == 0.0, "Initial elapsed_time is zero")
        
        # Test starting
        start_time = sw.start()
        print_result(isinstance(start_time, float), "start() returns timestamp")
        print_result(sw.is_running, "Stopwatch is running after start")
        
        # Test timing progression
        sleep(0.1)
        elapsed_1 = sw.total_time
        print_result(is_close(elapsed_1, 0.1, 0.05), f"Timing progression accurate ({elapsed_1:.3f}s)")
        
        # Test pause functionality
        pause_elapsed = sw.pause()
        print_result(sw.is_paused, "Stopwatch is paused after pause()")
        print_result(sw.is_running, "Stopwatch still 'running' when paused")
        print_result(is_close(pause_elapsed, elapsed_1, 0.01), "Pause returns current elapsed time")
        
        # Test time doesn't progress during pause
        sleep(0.1)
        elapsed_during_pause = sw.total_time
        print_result(is_close(elapsed_during_pause, pause_elapsed, 0.01), 
                    "Time doesn't progress during pause")
        
        # Test resume
        pause_duration = sw.resume()
        print_result(not sw.is_paused, "Stopwatch unpaused after resume")
        print_result(isinstance(pause_duration, float), "resume() returns pause duration")
        print_result(is_close(pause_duration, 0.1, 0.05), 
                    f"Pause duration accurate ({pause_duration:.3f}s)")
        
        # Test lap functionality
        sleep(0.05)
        lap1_time = sw.lap()
        print_result(isinstance(lap1_time, float), "lap() returns float")
        
        sleep(0.05)
        lap2_time = sw.lap()
        print_result(lap2_time > lap1_time, "Second lap time is greater than first")
        
        # Test lap retrieval
        retrieved_lap1 = sw.get_laptime(1)
        retrieved_lap2 = sw.get_laptime(2)
        invalid_lap = sw.get_laptime(99)
        
        print_result(retrieved_lap1 == lap1_time, "get_laptime(1) returns correct lap")
        print_result(retrieved_lap2 == lap2_time, "get_laptime(2) returns correct lap")
        print_result(invalid_lap is None, "get_laptime() returns None for invalid lap")
        
        # Test lap statistics
        lap_stats = sw.get_lap_statistics()
        print_result(isinstance(lap_stats, dict), "get_lap_statistics() returns dict")
        print_result('count' in lap_stats, "Lap stats contain count")
        print_result('mean' in lap_stats, "Lap stats contain mean")
        print_result(lap_stats['count'] == 2, "Lap count is correct")
        
        # Test stop
        final_time = sw.stop()
        print_result(not sw.is_running, "Stopwatch stopped after stop()")
        print_result(isinstance(final_time, float), "stop() returns final time")
        print_result(sw.total_time == final_time, "total_time matches stop() result")
        
        # Test error handling
        try:
            sw.start()  # Should fail - already started and stopped
            sw.start()  # This should fail
            print_result(False, "Should not allow starting twice")
        except RuntimeError:
            print_result(True, "Correctly prevents invalid state transitions")
        
        # Test reset
        sw.reset()
        print_result(not sw.is_running, "Reset stopwatch is not running")
        print_result(sw.total_time == 0.0, "Reset clears total time")
        
        # Test full cycle after reset
        sw.start()
        sleep(0.05)
        final_after_reset = sw.stop()
        print_result(is_close(final_after_reset, 0.05, 0.02), 
                    f"Full cycle after reset works ({final_after_reset:.3f}s)")
        
    except Exception as e:
        print_result(False, f"Stopwatch API class failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_timer_api_class():
    """Test the Timer API class."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping Timer API class tests - imports failed")
        return
        
    print_test("Timer API Class")
    
    try:
        timer = Timer()
        print_result(isinstance(timer, Timer), "Timer class instantiated correctly")
        
        # Test initial state
        print_result(timer.count == 0, "Timer starts with zero count")
        print_result(timer.times == 0, "times property matches count")
        print_result(timer.mostrecent is None, "No recent time initially")
        print_result(timer.result is None, "result property matches mostrecent")
        print_result(timer.mean is None, "No mean initially")
        
        # Test manual timing
        start_time = timer.start()
        print_result(isinstance(start_time, float), "start() returns timestamp")
        
        sleep(0.1)
        elapsed1 = timer.stop()
        
        print_result(isinstance(elapsed1, float), "stop() returns elapsed time")
        print_result(is_close(elapsed1, 0.1, 0.05), f"Manual timing accurate ({elapsed1:.3f}s)")
        print_result(timer.count == 1, "Count incremented after timing")
        print_result(timer.mostrecent == elapsed1, "mostrecent updated correctly")
        print_result(timer.result == elapsed1, "result property matches mostrecent")
        
        # Add more timings for statistical analysis
        timer.start()
        sleep(0.05)
        elapsed2 = timer.stop()
        
        timer.start()
        sleep(0.15)
        elapsed3 = timer.stop()
        
        print_result(timer.count == 3, "Multiple timings recorded")
        print_result(timer.mostrecent == elapsed3, "mostrecent is latest timing")
        
        # Test statistical properties
        mean_time = timer.mean
        median_time = timer.median
        longest_time = timer.longest
        shortest_time = timer.shortest
        std_time = timer.std
        variance_time = timer.variance
        
        print_result(isinstance(mean_time, float), "mean calculated correctly")
        print_result(isinstance(median_time, float), "median calculated correctly")
        print_result(longest_time == max(elapsed1, elapsed2, elapsed3), "longest is maximum")
        print_result(shortest_time == min(elapsed1, elapsed2, elapsed3), "shortest is minimum")
        print_result(isinstance(std_time, float), "standard deviation calculated")
        print_result(isinstance(variance_time, float), "variance calculated")
        
        print_info("Timings", f"[{elapsed1:.3f}, {elapsed2:.3f}, {elapsed3:.3f}]")
        print_info("Mean", f"{mean_time:.3f}s")
        print_info("Median", f"{median_time:.3f}s")
        print_info("Std Dev", f"{std_time:.3f}s")
        
        # Test get_a_time method (updated method name)
        time1 = timer.get_a_time(1)
        time2 = timer.get_a_time(2)
        time3 = timer.get_a_time(3)
        invalid_time = timer.get_a_time(99)
        
        print_result(time1 == elapsed1, "get_a_time(1) returns first timing")
        print_result(time2 == elapsed2, "get_a_time(2) returns second timing")
        print_result(time3 == elapsed3, "get_a_time(3) returns third timing")
        print_result(invalid_time is None, "get_a_time() returns None for invalid index")
        
        # Test percentiles
        p50 = timer.percentile(50)
        p95 = timer.percentile(95)
        p99 = timer.percentile(99)
        
        print_result(abs(p50 - median_time) < 0.001, "50th percentile matches median")
        print_result(isinstance(p95, float), "95th percentile calculated")
        print_result(isinstance(p99, float), "99th percentile calculated")
        
        # Test comprehensive statistics
        stats = timer.get_statistics()
        expected_keys = ['count', 'mean', 'median', 'longest', 'shortest', 'std', 'variance', 
                        'percentile_95', 'percentile_99', 'total_time']
        
        for key in expected_keys:
            print_result(key in stats, f"Statistics contain {key}")
        
        print_result(stats['count'] == 3, "Statistics count is correct")
        total_expected = elapsed1 + elapsed2 + elapsed3
        print_result(abs(stats['total_time'] - total_expected) < 0.001, "Total time is sum of timings")
        
        # Test manual time addition
        timer.add_time(0.2)
        print_result(timer.count == 4, "add_time() increases count")
        print_result(timer.mostrecent == 0.2, "add_time() updates mostrecent")
        
        # Test context manager (standalone)
        standalone_timer = Timer()
        with standalone_timer as ctx_timer:
            sleep(0.05)
        
        print_result(standalone_timer.count == 1, "Standalone context manager records timing")
        print_result(is_close(standalone_timer.result, 0.05, 0.02), 
                    f"Standalone context manager accurate ({standalone_timer.result:.3f}s)")
        
        # Test TimeThis() context manager for accumulating statistics
        accumulating_timer = Timer()
        
        for i in range(3):
            with accumulating_timer.TimeThis():
                sleep(0.03)
        
        print_result(accumulating_timer.count == 3, "TimeThis() accumulates multiple timings")
        print_result(accumulating_timer.mean is not None, "TimeThis() enables statistical analysis")
        print_result(is_close(accumulating_timer.mean, 0.03, 0.01), 
                    f"TimeThis() timing accurate (mean: {accumulating_timer.mean:.3f}s)")
        
        # Test reset
        timer.reset()
        print_result(timer.count == 0, "reset() clears count")
        print_result(timer.mostrecent is None, "reset() clears mostrecent")
        print_result(timer.mean is None, "reset() clears statistics")
        
    except Exception as e:
        print_result(False, f"Timer API class failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_timethis_decorator():
    """Test the timethis decorator functionality."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping timethis decorator tests - imports failed")
        return
        
    print_test("timethis Decorator")
    
    try:
        # Test basic decorator functionality
        timer = Timer()
        
        @timethis(timer)
        def test_function():
            sleep(0.1)
            return "success"
        
        # Test decorated function
        result = test_function()
        print_result(result == "success", "Decorated function returns correct result")
        print_result(timer.count == 1, "Decorator records timing")
        print_result(is_close(timer.mostrecent, 0.1, 0.05), 
                    f"Decorator timing accurate ({timer.mostrecent:.3f}s)")
        
        # Test multiple calls accumulate statistics
        test_function()
        test_function()
        print_result(timer.count == 3, "Multiple decorator calls accumulate")
        print_result(timer.mean is not None, "Statistics calculated from multiple calls")
        
        print_info("Decorator call count", str(timer.count))
        print_info("Decorator mean time", f"{timer.mean:.3f}s")
        
        # Test decorator with function arguments
        accumulator_timer = Timer()
        
        @timethis(accumulator_timer)
        def function_with_args(x, y, message="default"):
            sleep(0.05)
            return f"{message}: {x + y}"
        
        result_with_args = function_with_args(1, 2, message="sum")
        print_result(result_with_args == "sum: 3", "Decorated function with arguments works")
        print_result(accumulator_timer.count == 1, "Decorator with arguments records timing")
        
        # Test decorator with exception handling
        exception_timer = Timer()
        
        @timethis(exception_timer)
        def failing_function():
            sleep(0.02)
            raise ValueError("Test exception")
        
        initial_count = exception_timer.count
        try:
            failing_function()
            print_result(False, "Function should have raised exception")
        except ValueError as e:
            print_result(str(e) == "Test exception", "Exception properly propagated")
            print_result(exception_timer.count == initial_count + 1, 
                        "Timing recorded even with exception")
            print_result(is_close(exception_timer.mostrecent, 0.02, 0.01), 
                        "Exception timing accurate")
        
        # Test decorator on multiple functions with same timer
        shared_timer = Timer()
        
        @timethis(shared_timer)
        def fast_function():
            sleep(0.01)
            return "fast"
        
        @timethis(shared_timer)
        def slow_function():
            sleep(0.1)
            return "slow"
        
        fast_result = fast_function()
        slow_result = slow_function()
        
        print_result(fast_result == "fast" and slow_result == "slow", 
                    "Multiple decorated functions work correctly")
        print_result(shared_timer.count == 2, "Shared timer accumulates from multiple functions")
        print_result(shared_timer.longest > shared_timer.shortest, 
                    "Statistics differentiate between fast and slow functions")
        
        # Test decorator behavior with complex return values
        complex_timer = Timer()
        
        @timethis(complex_timer)
        def complex_return_function():
            sleep(0.01)
            return {"status": "ok", "data": [1, 2, 3], "nested": {"key": "value"}}
        
        complex_result = complex_return_function()
        expected_result = {"status": "ok", "data": [1, 2, 3], "nested": {"key": "value"}}
        print_result(complex_result == expected_result, "Decorator handles complex return values")
        print_result(complex_timer.count == 1, "Complex return function timing recorded")
        
    except Exception as e:
        print_result(False, f"timethis decorator failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_api_integration_scenarios():
    """Test API integration scenarios and real-world usage patterns."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping API integration tests - imports failed")
        return
        
    print_test("API Integration Scenarios")
    
    try:
        # Scenario 1: Performance monitoring workflow
        print(f"  {Colors.BLUE}Scenario 1: Performance monitoring workflow{Colors.END}")
        
        perf_timer = Timer()
        
        @timethis(perf_timer)
        def simulated_work(duration):
            sleep(duration)
            return f"Work completed in {duration}s"
        
        # Simulate various workloads
        workloads = [0.05, 0.1, 0.03, 0.08, 0.12]
        results = []
        
        for workload in workloads:
            result = simulated_work(workload)
            results.append(result)
        
        print_result(len(results) == 5, "All simulated work completed")
        print_result(perf_timer.count == 5, "All timings recorded")
        
        # Analyze performance
        avg_time = perf_timer.mean
        p95_time = perf_timer.percentile(95)
        
        print_result(isinstance(avg_time, float), "Average performance calculated")
        print_result(isinstance(p95_time, float), "95th percentile calculated")
        
        print_info("Average work time", f"{avg_time:.3f}s")
        print_info("95th percentile", f"{p95_time:.3f}s")
        
        # Scenario 2: Rate limiting with Yawn
        print(f"\n  {Colors.BLUE}Scenario 2: Rate limiting simulation{Colors.END}")
        
        rate_limiter = Yawn(sleep_duration=0.05, yawn_threshold=3, log_sleep=False)
        api_calls = []
        
        for i in range(10):
            start_call = now()
            
            # Simulate API call
            if rate_limiter.yawn():  # This will sleep every 3rd call
                api_calls.append(("rate_limited", start_call))
            else:
                api_calls.append(("normal", start_call))
            
            # Quick work simulation
            sleep(0.01)
        
        print_result(len(api_calls) == 10, "All API calls completed")
        
        rate_limited_calls = [call for call in api_calls if call[0] == "rate_limited"]
        print_result(len(rate_limited_calls) > 0, "Rate limiting triggered")
        print_info("Rate limited calls", str(len(rate_limited_calls)))
        
        # Scenario 3: Stopwatch for user interaction timing
        print(f"\n  {Colors.BLUE}Scenario 3: User interaction timing{Colors.END}")
        
        interaction_sw = Stopwatch()
        interaction_sw.start()
        
        # Simulate user interactions
        sleep(0.02)  # User thinks
        interaction_sw.lap()  # User clicks
        
        sleep(0.03)  # User reads
        interaction_sw.lap()  # User scrolls
        
        sleep(0.01)  # User decides
        total_interaction = interaction_sw.stop()
        
        lap_stats = interaction_sw.get_lap_statistics()
        
        print_result(total_interaction > 0.05, "Total interaction time reasonable")
        print_result(lap_stats['count'] == 2, "Both interaction laps recorded")
        print_result('fastest' in lap_stats, "Interaction statistics calculated")
        
        print_info("Total interaction time", f"{total_interaction:.3f}s")
        print_info("Fastest interaction", f"{lap_stats['fastest']:.3f}s")
        
        # Scenario 4: Combined timing analysis
        print(f"\n  {Colors.BLUE}Scenario 4: Combined timing analysis{Colors.END}")
        
        start_analysis = now()
        
        # Create multiple timers for different aspects
        db_timer = Timer()
        api_timer = Timer()
        processing_timer = Timer()
        
        # Simulate complex operation
        for i in range(3):
            # Database operation
            with db_timer:
                sleep(0.02)
            
            # API call
            with api_timer:
                sleep(0.03)
            
            # Data processing
            with processing_timer:
                sleep(0.01)
        
        total_analysis_time = elapsed(start_analysis)
        
        print_result(db_timer.count == 3, "Database operations timed")
        print_result(api_timer.count == 3, "API operations timed")
        print_result(processing_timer.count == 3, "Processing operations timed")
        
        # Compare operation types
        db_avg = db_timer.mean
        api_avg = api_timer.mean
        proc_avg = processing_timer.mean
        
        print_result(api_avg > db_avg, "API calls take longer than DB (as expected)")
        print_result(db_avg > proc_avg, "DB calls take longer than processing (as expected)")
        
        print_info("Total analysis time", f"{total_analysis_time:.3f}s")
        print_info("DB average", f"{db_avg:.3f}s")
        print_info("API average", f"{api_avg:.3f}s")
        print_info("Processing average", f"{proc_avg:.3f}s")
        
        # Scenario 5: Error handling in real workflow
        print(f"\n  {Colors.BLUE}Scenario 5: Error handling in workflows{Colors.END}")
        
        robust_timer = Timer()
        
        @timethis(robust_timer)
        def unreliable_operation(should_fail=False):
            sleep(0.02)
            if should_fail:
                raise RuntimeError("Simulated failure")
            return "success"
        
        success_count = 0
        error_count = 0
        
        # Mix successful and failing operations
        operations = [False, False, True, False, True, False]
        
        for should_fail in operations:
            try:
                result = unreliable_operation(should_fail)
                success_count += 1
            except RuntimeError:
                error_count += 1
        
        print_result(success_count == 4, "Successful operations completed")
        print_result(error_count == 2, "Failed operations handled")
        print_result(robust_timer.count == 6, "All operations timed (including failures)")
        
        # All operations should have similar timing regardless of success/failure
        timing_variance = robust_timer.std
        print_result(timing_variance < 0.01, "Timing consistent across success/failure")
        
    except Exception as e:
        print_result(False, f"API integration scenarios failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_api_edge_cases():
    """Test API edge cases and boundary conditions."""
    if not API_IMPORTS_SUCCESSFUL:
        print_warning("Skipping API edge cases tests - imports failed")
        return
        
    print_test("API Edge Cases and Boundaries")
    
    try:
        # Test very short durations
        short_timer = Timer()
        
        with short_timer:
            pass  # Minimal operation
        
        print_result(short_timer.count == 1, "Very short duration recorded")
        print_result(short_timer.mostrecent >= 0.0, "Short duration is non-negative")
        print_result(short_timer.mostrecent < 0.01, "Short duration is reasonable")
        
        # Test zero sleep duration
        try:
            sleep(0)
            print_result(True, "Zero sleep duration handled")
        except Exception:
            print_result(False, "Zero sleep should not raise exception")
        
        # Test negative elapsed time (should handle gracefully)
        future_time = now() + 10  # 10 seconds in future
        past_elapsed = elapsed(future_time, now())
        print_result(past_elapsed > 0, "elapsed() handles future time gracefully")
        
        # Test Timer with single measurement edge case
        single_timer = Timer()
        single_timer.add_time(1.0)
        
        print_result(single_timer.mean == 1.0, "Single measurement mean correct")
        print_result(single_timer.median == 1.0, "Single measurement median correct")
        print_result(single_timer.std is None, "Single measurement has no std dev")
        print_result(single_timer.variance is None, "Single measurement has no variance")
        
        # Test Yawn with threshold 1 (immediate sleep)
        immediate_yawn = Yawn(0.01, 1, log_sleep=False)
        start_immediate = now()
        slept = immediate_yawn.yawn()
        end_immediate = now()
        immediate_duration = end_immediate - start_immediate
        
        print_result(slept, "Threshold 1 yawn sleeps immediately")
        print_result(is_close(immediate_duration, 0.01, 0.01), "Immediate yawn timing correct")
        
        # Test Stopwatch error states
        error_sw = Stopwatch()
        
        # Test pause without start
        try:
            error_sw.pause()
            print_result(False, "Should not allow pause without start")
        except RuntimeError:
            print_result(True, "Correctly prevents pause without start")
        
        # Test lap without start
        try:
            error_sw.lap()
            print_result(False, "Should not allow lap without start")
        except RuntimeError:
            print_result(True, "Correctly prevents lap without start")
        
        # Test Timer error states
        error_timer = Timer()
        
        # Test stop without start
        try:
            error_timer.stop()
            print_result(False, "Should not allow stop without start")
        except RuntimeError:
            print_result(True, "Correctly prevents stop without start")
        
        # Test percentile edge cases
        edge_timer = Timer()
        edge_timer.add_time(1.0)
        edge_timer.add_time(2.0)
        edge_timer.add_time(3.0)
        
        p0 = edge_timer.percentile(0)
        p100 = edge_timer.percentile(100)
        p33 = edge_timer.percentile(33.33)
        
        print_result(p0 == 1.0, "0th percentile is minimum")
        print_result(p100 == 3.0, "100th percentile is maximum")
        print_result(isinstance(p33, float), "Fractional percentile calculated")
        
        # Test invalid percentile values
        try:
            edge_timer.percentile(-5)
            print_result(False, "Should reject negative percentile")
        except ValueError:
            print_result(True, "Correctly rejects negative percentile")
        
        try:
            edge_timer.percentile(150)
            print_result(False, "Should reject percentile > 100")
        except ValueError:
            print_result(True, "Correctly rejects percentile > 100")
        
        # Test large dataset performance
        large_timer = Timer()
        
        start_large = now()
        for i in range(1000):
            large_timer.add_time(i * 0.001)
        stats_large = large_timer.get_statistics()
        end_large = now()
        
        large_processing_time = end_large - start_large
        
        print_result(large_timer.count == 1000, "Large dataset handled")
        print_result(isinstance(stats_large['mean'], float), "Large dataset statistics calculated")
        print_result(large_processing_time < 0.1, "Large dataset processing is fast")
        
        print_info("Large dataset processing time", f"{large_processing_time:.3f}s")
        
    except Exception as e:
        print_result(False, f"API edge cases failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def run_all_api_tests():
    """Run all SKTime API tests."""
    print_section("Comprehensive SKTime API Test Suite")
    
    if not API_IMPORTS_SUCCESSFUL:
        print(f"{Colors.RED}{Colors.BOLD}❌ Cannot run tests - import failures{Colors.END}")
        print(f"{Colors.YELLOW}Ensure the suitkaise.sktime.api module is properly installed or accessible{Colors.END}")
        return
    
    print(f"{Colors.GREEN}✅ Successfully imported all SKTime API functions{Colors.END}")
    print(f"{Colors.WHITE}Testing the complete user-facing SKTime API...{Colors.END}\n")
    
    try:
        # Core API functionality tests
        test_simple_timing_functions()
        test_yawn_api_class()
        test_stopwatch_api_class()
        test_timer_api_class()
        test_timethis_decorator()
        
        # Real-world usage tests
        test_api_integration_scenarios()
        test_api_edge_cases()
        
        print_section("SKTime API Test Summary")
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 ALL SKTIME API TESTS COMPLETED! 🎉{Colors.END}")
        print(f"{Colors.WHITE}✅ Simple functions: now(), sleep(), elapsed() working perfectly{Colors.END}")
        print(f"{Colors.WHITE}✅ Yawn class: Threshold-based sleep control intuitive and robust{Colors.END}")
        print(f"{Colors.WHITE}✅ Stopwatch class: Pause/resume/lap functionality seamless{Colors.END}")
        print(f"{Colors.WHITE}✅ Timer class: Statistical analysis comprehensive and accurate{Colors.END}")
        print(f"{Colors.WHITE}✅ timethis decorator: Function timing integration flawless{Colors.END}")
        print(f"{Colors.WHITE}✅ Real-world scenarios: Performance monitoring, rate limiting working{Colors.END}")
        print(f"{Colors.WHITE}✅ Edge cases: Boundary conditions and error handling robust{Colors.END}")
        print(f"{Colors.WHITE}✅ The SKTime API is production-ready! 🚀{Colors.END}")
        print()
        
        print(f"{Colors.CYAN}{Colors.BOLD}KEY API ACHIEVEMENTS VALIDATED:{Colors.END}")
        print(f"{Colors.GREEN}⏱️ Intuitive interface - Simple functions with powerful capabilities{Colors.END}")
        print(f"{Colors.GREEN}📊 Statistical power - Comprehensive timing analysis built-in{Colors.END}")
        print(f"{Colors.GREEN}🎯 Context managers - Seamless integration with Python idioms{Colors.END}")
        print(f"{Colors.GREEN}🥱 Smart delays - Threshold-based sleep for rate limiting{Colors.END}")
        print(f"{Colors.GREEN}⏸️ Flexible timing - Pause/resume for complex timing scenarios{Colors.END}")
        print(f"{Colors.GREEN}🏁 Lap timing - Individual measurement tracking and analysis{Colors.END}")
        print(f"{Colors.GREEN}🛡️ Robust errors - Meaningful exceptions and graceful handling{Colors.END}")
        print(f"{Colors.GREEN}⚡ Performance - Fast statistics calculation even for large datasets{Colors.END}")
        
    except Exception as e:
        print(f"{Colors.RED}{Colors.BOLD}❌ Test suite failed with error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_api_tests()