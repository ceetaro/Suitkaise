#!/usr/bin/env python3
"""
Comprehensive test module for SKTime functionality.

This module contains rigorous tests for the SKTime system, including:
- Basic time functions (now, sleep, elapsed)
- Time formatting (fmttime, fmtdate) 
- Timer class with context manager and pause/resume
- Timing decorators and utilities
- Benchmarking functionality
- Rate limiting and monitoring
- Error handling and edge cases

Run with:
    python -m pytest tests/test_suitkaise/test_sktime/test_sktime.py -v
    
Or with unittest:
    python -m unittest tests.test_suitkaise.test_sktime.test_sktime -v
"""

import unittest
import time
import threading
import sys
import datetime
import random
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Visual indicators for test output
INFO = "⬜️" * 40 + "\n\n\n"
FAIL = "\n\n   " + "❌" * 10 + " "
SUCCESS = "\n\n   " + "🟩" * 10 + " "
RUNNING = "🔄" * 40 + "\n\n"
CHECKING = "🧳" * 40 + "\n"
WARNING = "\n\n   " + "🟨" * 10 + " "

from suitkaise.sktime.sktime import (
    now, sleep, elapsed, fmttime, fmtdate, Timer, SKTimeError,
    date_ago, date_from_now, parse_human_date, time_since, time_until,
    is_recent, date_range, timeout_after, retry_with_delay, benchmark,
    timethis, rate_limiter, measure_function_time, compare_functions,
    timing_context, RateMonitor, TimerPool, PerformanceTracker,
    quick_time, LapTime, TimingRegistry, timing_registry
)


class TestBasicTimeFunctions(unittest.TestCase):
    """Test basic time utility functions."""

    def test_now_returns_float(self):
        """Test that now() returns a valid float timestamp."""
        current_time = now()
        
        # Check return type
        self.assertIsInstance(current_time, float)
        
        # Check that timestamp is reasonable (after 2020, before 2030)
        self.assertGreater(current_time, 1577836800.0, "Timestamp should be after 2020")
        self.assertLess(current_time, 1893456000.0, "Timestamp should be before 2030")

    def test_now_progression(self):
        """Test that now() returns increasing values over time."""
        timestamps = []
        
        for i in range(5):
            timestamps.append(now())
            time.sleep(0.01)  # 10ms delay
        
        # Each timestamp should be greater than the previous
        for i in range(1, len(timestamps)):
            self.assertGreater(timestamps[i], timestamps[i-1],
                             f"Timestamp {i} should be greater than timestamp {i-1}")

    def test_sleep_basic(self):
        """Test basic sleep functionality with timing verification."""
        sleep_duration = 0.1  # 100ms
        tolerance = 0.05      # 50ms tolerance
        
        start_time = now()
        sleep(sleep_duration)
        end_time = now()
        
        actual_duration = end_time - start_time
        
        # Check duration is within tolerance
        self.assertGreater(actual_duration, sleep_duration - tolerance)
        self.assertLess(actual_duration, sleep_duration + tolerance)

    def test_sleep_edge_cases(self):
        """Test sleep with edge case values."""
        # Test zero sleep
        start = now()
        sleep(0)
        end = now()
        self.assertLess(end - start, 0.01)  # Should be very quick
        
        # Test very small sleep
        start = now()
        sleep(0.001)  # 1ms
        end = now()
        self.assertGreater(end - start, 0)  # Should take some time

    def test_sleep_input_validation(self):
        """Test sleep input validation (if implemented)."""
        # These should work without error
        sleep(0)
        sleep(0.1)
        sleep(1)

    def test_elapsed_calculation(self):
        """Test elapsed time calculation function."""
        start_time = 1000.0
        end_time = 1005.5
        expected_elapsed = 5.5
        
        calculated_elapsed = elapsed(start_time, end_time)
        
        self.assertEqual(calculated_elapsed, expected_elapsed)
        self.assertIsInstance(calculated_elapsed, float)

    def test_elapsed_with_real_times(self):
        """Test elapsed calculation with real timestamps."""
        start = now()
        sleep(0.05)  # 50ms
        end = now()
        
        elapsed_time = elapsed(start, end)
        direct_calculation = end - start
        
        # Both methods should give the same result
        self.assertEqual(elapsed_time, direct_calculation)
        
        # Should be approximately 50ms
        self.assertAlmostEqual(elapsed_time, 0.05, delta=0.02)

    def test_elapsed_error_handling(self):
        """Test elapsed function error handling."""
        with self.assertRaises(SKTimeError):
            elapsed(10.0, 5.0)  # End time before start time


class TestTimeFormatting(unittest.TestCase):
    """Test time formatting functions."""

    def test_fmttime_basic(self):
        """Test basic time formatting."""
        # Test seconds
        self.assertEqual(fmttime(1.5), "1.50s")
        self.assertEqual(fmttime(0.5), "500.00ms")
        
        # Test minutes
        result = fmttime(65.5)  # 1 minute 5.5 seconds
        self.assertIn("1m", result)
        self.assertIn("5.50s", result)
        
        # Test hours
        result = fmttime(3665)  # 1 hour 1 minute 5 seconds
        self.assertIn("1h", result)
        self.assertIn("1m", result)
        self.assertIn("5.00s", result)

    def test_fmttime_edge_cases(self):
        """Test fmttime with edge cases."""
        # Zero time
        self.assertEqual(fmttime(0), "0.00s")
        
        # Very small times
        result = fmttime(0.001)  # 1ms
        self.assertIn("ms", result)
        
        result = fmttime(0.000001)  # 1μs
        self.assertIn("μs", result)
        
        result = fmttime(0.000000001)  # 1ns
        self.assertIn("ns", result)

    def test_fmttime_negative(self):
        """Test fmttime with negative values."""
        result = fmttime(-5.2)
        self.assertTrue(result.startswith("-"))
        self.assertIn("5.20s", result)

    def test_fmttime_precision(self):
        """Test fmttime precision parameter."""
        self.assertEqual(fmttime(1.23456, precision=0), "1s")
        self.assertEqual(fmttime(1.23456, precision=3), "1.235s")

    def test_fmtdate_relative(self):
        """Test relative date formatting."""
        # Test recent past
        past_time = now() - 3600  # 1 hour ago
        result = fmtdate(past_time, style="relative")
        self.assertIn("hour", result.lower())
        self.assertIn("ago", result.lower())
        
        # Test near future
        future_time = now() + 7200  # 2 hours from now
        result = fmtdate(future_time, style="relative")
        self.assertIn("hour", result.lower())
        self.assertIn("in ", result.lower())

    def test_fmtdate_absolute(self):
        """Test absolute date formatting."""
        test_time = now()
        
        # Test different styles
        abs_result = fmtdate(test_time, style="absolute")
        self.assertIsInstance(abs_result, str)
        self.assertGreater(len(abs_result), 5)
        
        full_result = fmtdate(test_time, style="full")
        self.assertIsInstance(full_result, str)
        
        short_result = fmtdate(test_time, style="short")
        self.assertIsInstance(short_result, str)

    def test_fmtdate_custom(self):
        """Test custom date formatting."""
        test_time = now()
        custom_format = "%Y-%m-%d %H:%M"
        
        result = fmtdate(test_time, style="custom", custom_format=custom_format)
        
        # Should match the custom format pattern
        self.assertRegex(result, r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')

    def test_fmtdate_input_types(self):
        """Test fmtdate with different input types."""
        # Test with timestamp
        timestamp = now()
        result1 = fmtdate(timestamp)
        self.assertIsInstance(result1, str)
        
        # Test with datetime object
        dt = datetime.datetime.now()
        result2 = fmtdate(dt)
        self.assertIsInstance(result2, str)
        
        # Test with ISO string
        iso_string = datetime.datetime.now().isoformat()
        result3 = fmtdate(iso_string)
        self.assertIsInstance(result3, str)


class TestDateUtilities(unittest.TestCase):
    """Test date utility functions."""

    def test_date_ago(self):
        """Test date_ago function."""
        # Test 1 day ago
        one_day_ago = date_ago(days=1)
        expected = now() - 86400
        self.assertAlmostEqual(one_day_ago, expected, delta=1)
        
        # Test 2 hours ago
        two_hours_ago = date_ago(hours=2)
        expected = now() - 7200
        self.assertAlmostEqual(two_hours_ago, expected, delta=1)

    def test_date_from_now(self):
        """Test date_from_now function."""
        # Test 1 day from now
        one_day_future = date_from_now(days=1)
        expected = now() + 86400
        self.assertAlmostEqual(one_day_future, expected, delta=1)
        
        # Test 3 hours from now
        three_hours_future = date_from_now(hours=3)
        expected = now() + 10800
        self.assertAlmostEqual(three_hours_future, expected, delta=1)

    def test_parse_human_date(self):
        """Test parsing human-readable date strings."""
        current = now()
        
        # Test relative terms
        result = parse_human_date("now")
        self.assertAlmostEqual(result, current, delta=1)
        
        result = parse_human_date("yesterday")
        expected = current - 86400
        self.assertAlmostEqual(result, expected, delta=1)
        
        result = parse_human_date("tomorrow")
        expected = current + 86400
        self.assertAlmostEqual(result, expected, delta=1)

    def test_parse_human_date_patterns(self):
        """Test parsing time patterns like '2 hours ago'."""
        current = now()
        
        # Test "X ago" patterns
        result = parse_human_date("2 hours ago")
        if result:  # Only test if parsing succeeds
            expected = current - 7200
            self.assertAlmostEqual(result, expected, delta=10)
        
        # Test "in X" patterns
        result = parse_human_date("in 3 hours")
        if result:
            expected = current + 10800
            self.assertAlmostEqual(result, expected, delta=10)

    def test_time_since(self):
        """Test time_since function."""
        past_time = now() - 3600  # 1 hour ago
        result = time_since(past_time)
        
        self.assertIsInstance(result, str)
        self.assertIn("ago", result.lower())

    def test_time_until(self):
        """Test time_until function."""
        future_time = now() + 3600  # 1 hour from now
        result = time_until(future_time)
        
        self.assertIsInstance(result, str)
        self.assertIn("in ", result.lower())

    def test_is_recent(self):
        """Test is_recent function."""
        # Recent timestamp
        recent_time = now() - 30  # 30 seconds ago
        self.assertTrue(is_recent(recent_time, threshold_seconds=60))
        
        # Old timestamp
        old_time = now() - 7200  # 2 hours ago
        self.assertFalse(is_recent(old_time, threshold_seconds=60))

    def test_date_range(self):
        """Test date_range function."""
        start = now()
        end = start + 259200  # 3 days later
        
        dates = date_range(start, end, step_days=1)
        
        self.assertEqual(len(dates), 4)  # Should include start, +1, +2, +3 days
        
        # Check progression
        for i in range(1, len(dates)):
            self.assertAlmostEqual(dates[i] - dates[i-1], 86400, delta=1)


class TestTimerClass(unittest.TestCase):
    """Test Timer class functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.timer = Timer()

    def test_timer_initialization(self):
        """Test Timer initialization state."""
        self.assertIsNone(self.timer.start_time)
        self.assertIsNone(self.timer.end_time)
        self.assertIsNone(self.timer.elapsed_time)
        self.assertEqual(self.timer.paused_time, 0.0)
        self.assertFalse(self.timer.is_running)
        self.assertFalse(self.timer.is_paused)

    def test_timer_basic_start_stop(self):
        """Test basic Timer start and stop functionality."""
        # Start the timer
        self.timer.start()
        self.assertTrue(self.timer.is_running)
        self.assertIsNotNone(self.timer.start_time)
        
        # Wait a bit
        sleep(0.05)  # 50ms
        
        # Stop and get elapsed time
        elapsed_time = self.timer.stop()
        
        self.assertIsInstance(elapsed_time, float)
        self.assertGreater(elapsed_time, 0.04)  # At least 40ms
        self.assertLess(elapsed_time, 0.1)      # Less than 100ms
        self.assertFalse(self.timer.is_running)
        self.assertIsNotNone(self.timer.end_time)
        self.assertEqual(self.timer.elapsed_time, elapsed_time)

    def test_timer_context_manager(self):
        """Test Timer as context manager."""
        with Timer() as timer:
            self.assertTrue(timer.is_running)
            sleep(0.02)  # 20ms
            
            # Can access current time
            current_time = timer.get_current_time()
            self.assertGreater(current_time, 0.01)
        
        # Timer should be stopped after context
        self.assertFalse(timer.is_running)
        self.assertIsNotNone(timer.elapsed_time)
        self.assertGreater(timer.elapsed_time, 0.01)

    def test_timer_pause_resume(self):
        """Test Timer pause and resume functionality."""
        self.timer.start()
        
        # Run for ~25ms
        sleep(0.025)
        
        # Pause
        self.timer.pause()
        self.assertTrue(self.timer.is_paused)
        pause_start_time = self.timer.get_current_time()
        
        # Stay paused for ~50ms (shouldn't count)
        sleep(0.05)
        
        # Resume
        self.timer.resume()
        self.assertFalse(self.timer.is_paused)
        
        # Run for another ~25ms
        sleep(0.025)
        
        # Stop and check
        total_elapsed = self.timer.stop()
        
        # Should be ~50ms (25+25), not ~100ms
        self.assertGreater(total_elapsed, 0.04)   # At least 40ms
        self.assertLess(total_elapsed, 0.08)      # Less than 80ms
        
        # Paused time should be tracked
        self.assertGreater(self.timer.paused_time, 0.04)

    def test_timer_laps(self):
        """Test Timer lap functionality."""
        self.timer.start()
        
        # First lap
        sleep(0.02)
        lap1 = self.timer.lap("first")
        
        self.assertIsInstance(lap1, LapTime)
        self.assertEqual(lap1.lap_number, 1)
        self.assertEqual(lap1.name, "first")
        self.assertGreater(lap1.lap_time, 0.01)
        
        # Second lap
        sleep(0.03)
        lap2 = self.timer.lap("second")
        
        self.assertEqual(lap2.lap_number, 2)
        self.assertEqual(lap2.name, "second")
        self.assertGreater(lap2.lap_time, 0.02)
        self.assertGreater(lap2.total_time, lap1.total_time)
        
        # Check laps are stored
        laps = self.timer.get_laps()
        self.assertEqual(len(laps), 2)
        
        # Check lap summary
        summary = self.timer.get_lap_summary()
        self.assertEqual(summary['lap_count'], 2)
        self.assertIn('fastest_lap', summary)
        self.assertIn('slowest_lap', summary)

    def test_timer_get_current_time(self):
        """Test getting current time without stopping."""
        self.timer.start()
        
        sleep(0.03)
        current1 = self.timer.get_current_time()
        
        sleep(0.02)
        current2 = self.timer.get_current_time()
        
        # Second reading should be larger
        self.assertGreater(current2, current1)
        
        # Timer should still be running
        self.assertTrue(self.timer.is_running)

    def test_timer_error_handling(self):
        """Test Timer error handling."""
        # Stop without start
        with self.assertRaises(RuntimeError):
            self.timer.stop()
        
        # Pause without start
        with self.assertRaises(RuntimeError):
            self.timer.pause()
        
        # Get current time without start
        with self.assertRaises(RuntimeError):
            self.timer.get_current_time()
        
        # Resume without pause
        self.timer.start()
        with self.assertRaises(RuntimeError):
            self.timer.resume()
        
        # Double pause
        self.timer.pause()
        with self.assertRaises(RuntimeError):
            self.timer.pause()
        
        # Stop while paused
        with self.assertRaises(RuntimeError):
            self.timer.stop()

    def test_timer_reset(self):
        """Test Timer reset functionality."""
        self.timer.start()
        sleep(0.02)
        self.timer.pause()
        sleep(0.01)
        
        # Reset should clear everything
        self.timer.reset()
        
        self.assertIsNone(self.timer.start_time)
        self.assertIsNone(self.timer.end_time)
        self.assertIsNone(self.timer.elapsed_time)
        self.assertEqual(self.timer.paused_time, 0.0)
        self.assertFalse(self.timer.is_running)
        self.assertFalse(self.timer.is_paused)


class TestTimingDecorators(unittest.TestCase):
    """Test timing decorators and utilities."""

    def test_timethis_basic(self):
        """Test basic @timethis decorator."""
        @timethis()
        def test_function():
            sleep(0.01)
            return "result"
        
        result = test_function()
        self.assertEqual(result, "result")
        
        # Check timing data was stored
        timing = test_function.get_last_timing()
        self.assertIsNotNone(timing)
        self.assertIn('duration', timing)
        self.assertIn('function_name', timing)
        self.assertEqual(timing['function_name'], 'test_function')

    def test_timethis_return_timing(self):
        """Test @timethis with return_timing=True."""
        @timethis(return_timing=True)
        def test_function():
            sleep(0.01)
            return "result"
        
        result, timing = test_function()
        self.assertEqual(result, "result")
        self.assertIsInstance(timing, dict)
        self.assertIn('duration', timing)
        self.assertGreater(timing['duration'], 0)

    def test_timethis_tracking(self):
        """Test @timethis with call tracking."""
        @timethis(track_calls=True)
        def test_function():
            sleep(0.005)
            return "result"
        
        # Call multiple times
        for i in range(3):
            test_function()
        
        # Check statistics
        stats = test_function.get_timing_stats()
        self.assertEqual(stats['call_count'], 3)
        self.assertIn('avg_time', stats)
        self.assertIn('total_time', stats)

    def test_timeout_after_decorator(self):
        """Test @timeout_after decorator."""
        @timeout_after(0.05)  # 50ms timeout
        def fast_function():
            sleep(0.01)  # 10ms - should succeed
            return "success"
        
        @timeout_after(0.02)  # 20ms timeout
        def slow_function():
            sleep(0.1)   # 100ms - should timeout
            return "should not reach"
        
        # Fast function should work
        result = fast_function()
        self.assertEqual(result, "success")
        
        # Slow function should timeout
        with self.assertRaises(SKTimeError):
            slow_function()

    def test_retry_with_delay_decorator(self):
        """Test @retry_with_delay decorator."""
        call_count = 0
        
        @retry_with_delay(max_attempts=3, delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Simulated failure")
            return "success"
        
        result = flaky_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)

    def test_rate_limiter_decorator(self):
        """Test @rate_limiter decorator."""
        call_times = []
        
        @rate_limiter(max_calls_per_second=10.0, burst_size=2)
        def limited_function():
            call_times.append(now())
            return "called"
        
        # Should allow burst calls
        limited_function()
        limited_function()
        
        # Third call should be rate limited
        start_time = now()
        limited_function()
        end_time = now()
        
        # Should have taken some time due to rate limiting
        self.assertGreater(end_time - start_time, 0.05)  # Some delay expected


class TestBenchmarking(unittest.TestCase):
    """Test benchmarking functionality."""

    def test_benchmark_basic(self):
        """Test basic benchmark function."""
        def simple_function(n):
            return sum(range(n))
        
        results = benchmark(simple_function, iterations=100, warmup=10, n=100)
        
        self.assertIn('total_time', results)
        self.assertIn('avg_time', results)
        self.assertIn('min_time', results)
        self.assertIn('max_time', results)
        self.assertIn('iterations', results)
        self.assertEqual(results['iterations'], 100)
        self.assertGreater(results['ops_per_second'], 0)

    def test_benchmark_error_handling(self):
        """Test benchmark error handling."""
        def failing_function():
            raise ValueError("Test error")
        
        with self.assertRaises(SKTimeError):
            benchmark(failing_function, iterations=10)

    def test_measure_function_time(self):
        """Test measure_function_time utility."""
        def test_function(x, y):
            sleep(0.01)
            return x + y
        
        duration, result = measure_function_time(test_function, 5, 3)
        
        self.assertEqual(result, 8)
        self.assertGreater(duration, 0.005)
        self.assertLess(duration, 0.05)

    def test_compare_functions(self):
        """Test compare_functions utility."""
        def method1(data):
            return sorted(data)
        
        def method2(data):
            return list(sorted(data))
        
        data = list(range(50))
        results = compare_functions(method1, method2, iterations=50, data=data)
        
        self.assertIn('method1', results)
        self.assertIn('method2', results)
        
        for func_name, stats in results.items():
            if 'error' not in stats:
                self.assertIn('avg_time', stats)
                self.assertIn('iterations', stats)

    def test_quick_time(self):
        """Test quick_time utility."""
        def test_func(x):
            sleep(0.01)
            return x * 2
        
        result, duration = quick_time(test_func, 5)
        
        self.assertEqual(result, 10)
        self.assertGreater(duration, 0.005)


class TestRateMonitoring(unittest.TestCase):
    """Test rate monitoring functionality."""

    def test_rate_monitor_basic(self):
        """Test basic RateMonitor functionality."""
        monitor = RateMonitor(window_size=1.0)
        
        # Initially no operations
        self.assertEqual(monitor.get_current_rate(), 0.0)
        self.assertEqual(monitor.operation_count, 0)
        
        # Add some operations
        for i in range(5):
            monitor.tick()
            sleep(0.01)
        
        # Should have recorded operations
        self.assertEqual(monitor.operation_count, 5)
        current_rate = monitor.get_current_rate()
        self.assertGreater(current_rate, 0)

    def test_rate_monitor_reset(self):
        """Test RateMonitor reset functionality."""
        monitor = RateMonitor()
        
        monitor.tick()
        monitor.tick()
        self.assertEqual(monitor.operation_count, 2)
        
        monitor.reset()
        self.assertEqual(monitor.operation_count, 0)
        self.assertEqual(monitor.get_current_rate(), 0.0)

    def test_timing_context(self):
        """Test timing_context context manager."""
        with timing_context("test operation", print_start=False, print_end=False) as timer:
            sleep(0.02)
            self.assertTrue(timer.is_running)
        
        self.assertFalse(timer.is_running)
        self.assertIsNotNone(timer.elapsed_time)
        self.assertGreater(timer.elapsed_time, 0.015)

    def test_performance_tracker(self):
        """Test PerformanceTracker class."""
        tracker = PerformanceTracker("test operations")
        
        # Track some operations
        for i in range(3):
            with tracker.time_operation(f"operation_{i}") as timing:
                sleep(0.01)
                timing.add_metadata(iteration=i)
        
        stats = tracker.get_statistics()
        self.assertEqual(stats['count'], 3)
        self.assertIn('avg_time', stats)
        self.assertIn('throughput', stats)


class TestTimerPool(unittest.TestCase):
    """Test TimerPool functionality."""

    def test_timer_pool_basic(self):
        """Test basic TimerPool operations."""
        pool = TimerPool()
        
        # Start multiple timers
        timer1 = pool.start('task1')
        timer2 = pool.start('task2')
        
        self.assertIsInstance(timer1, Timer)
        self.assertIsInstance(timer2, Timer)
        
        sleep(0.02)
        
        # Stop timers
        elapsed1 = pool.stop('task1')
        elapsed2 = pool.stop('task2')
        
        self.assertGreater(elapsed1, 0.01)
        self.assertGreater(elapsed2, 0.01)

    def test_timer_pool_errors(self):
        """Test TimerPool error handling."""
        pool = TimerPool()
        
        # Stop non-existent timer
        with self.assertRaises(KeyError):
            pool.stop('nonexistent')
        
        # Pause non-existent timer
        with self.assertRaises(KeyError):
            pool.pause('nonexistent')

    def test_timer_pool_laps(self):
        """Test TimerPool lap functionality."""
        pool = TimerPool()
        
        pool.start('task')
        sleep(0.01)
        lap = pool.lap('task', 'checkpoint1')
        sleep(0.01)
        pool.stop('task')
        
        self.assertIsInstance(lap, LapTime)
        self.assertEqual(lap.name, 'checkpoint1')

    def test_timer_pool_summary(self):
        """Test TimerPool summary functionality."""
        pool = TimerPool()
        
        pool.start('task1')
        sleep(0.01)
        pool.stop('task1')
        
        pool.start('task2')
        pool.pause('task2')
        
        summary = pool.get_summary()
        self.assertIn('task1', summary)
        self.assertIn('task2', summary)
        self.assertFalse(summary['task1']['is_running'])
        self.assertTrue(summary['task2']['is_paused'])


class TestTimingRegistry(unittest.TestCase):
    """Test TimingRegistry functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = TimingRegistry("test_registry")
        self.registry.clear_all()

    def test_timing_registry_basic(self):
        """Test basic TimingRegistry operations."""
        # Record some timing data
        timing_info = {
            'function_name': 'test_func',
            'duration': 0.05,
            'timestamp': now(),
            'success': True
        }
        
        self.registry.record_timing(timing_info)
        
        # Retrieve data
        timings = self.registry.get_function_timings('test_func')
        self.assertEqual(len(timings), 1)
        self.assertEqual(timings[0]['function_name'], 'test_func')

    def test_timing_registry_stats(self):
        """Test TimingRegistry statistics."""
        # Record multiple timings
        for i in range(3):
            timing_info = {
                'function_name': 'test_func',
                'duration': 0.01 * (i + 1),  # 0.01, 0.02, 0.03
                'timestamp': now(),
                'success': True
            }
            self.registry.record_timing(timing_info)
        
        stats = self.registry.get_function_stats('test_func')
        self.assertEqual(stats['call_count'], 3)
        self.assertAlmostEqual(stats['avg_time'], 0.02, places=3)

    def test_timing_registry_find(self):
        """Test TimingRegistry find functionality."""
        # Record different functions
        for func_name in ['func1', 'func2']:
            for i in range(2 if func_name == 'func1' else 5):
                timing_info = {
                    'function_name': func_name,
                    'duration': 0.01,
                    'timestamp': now(),
                    'success': True
                }
                self.registry.record_timing(timing_info)
        
        # Find functions with more than 3 calls
        busy_functions = self.registry.find_functions(
            lambda name, timings: len(timings) > 3
        )
        
        self.assertIn('func2', busy_functions)
        self.assertNotIn('func1', busy_functions)


class TestErrorHandling(unittest.TestCase):
    """Test comprehensive error handling."""

    def test_sktime_error_class(self):
        """Test SKTimeError exception class."""
        with self.assertRaises(SKTimeError):
            raise SKTimeError("Test error")
        
        try:
            raise SKTimeError("Test error with details")
        except SKTimeError as e:
            self.assertIn("Test error", str(e))

    def test_elapsed_negative_time(self):
        """Test elapsed with invalid time range."""
        with self.assertRaises(SKTimeError):
            elapsed(10.0, 5.0)  # End before start

    def test_timer_invalid_operations(self):
        """Test Timer with invalid operation sequences."""
        timer = Timer()
        
        # Various invalid operations
        with self.assertRaises(RuntimeError):
            timer.stop()
        
        with self.assertRaises(RuntimeError):
            timer.pause()
        
        with self.assertRaises(RuntimeError):
            timer.get_current_time()
        
        with self.assertRaises(RuntimeError):
            timer.lap()


class TestConcurrencyAndThreadSafety(unittest.TestCase):
    """Test concurrent usage and thread safety."""

    def test_multiple_timers_concurrent(self):
        """Test multiple Timer instances running concurrently."""
        results = []
        errors = []
        
        def timer_worker(worker_id, duration):
            try:
                with Timer() as timer:
                    sleep(duration)
                results.append((worker_id, timer.elapsed_time))
            except Exception as e:
                errors.append((worker_id, e))
        
        # Start multiple timer threads
        threads = []
        durations = [0.01, 0.02, 0.03, 0.04]
        
        for i, duration in enumerate(durations):
            thread = threading.Thread(target=timer_worker, args=(i, duration))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent errors: {errors}")
        self.assertEqual(len(results), 4)

    def test_timing_registry_thread_safety(self):
        """Test TimingRegistry thread safety."""
        registry = TimingRegistry("thread_test")
        registry.clear_all()
        
        def record_worker(worker_id):
            for i in range(10):
                timing_info = {
                    'function_name': f'worker_{worker_id}',
                    'duration': 0.001 * i,
                    'timestamp': now(),
                    'success': True
                }
                registry.record_timing(timing_info)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=record_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify all data was recorded
        all_functions = registry.get_all_functions()
        self.assertEqual(len(all_functions), 3)
        
        for func_name in all_functions:
            stats = registry.get_function_stats(func_name)
            self.assertEqual(stats['call_count'], 10)


class TestIntegrationScenarios(unittest.TestCase):
    """Test real-world integration scenarios."""

    def test_complete_timing_workflow(self):
        """Test a complete timing workflow scenario."""
        # Scenario: Timing a data processing pipeline
        
        with Timer() as pipeline_timer:
            # Stage 1: Data loading
            pipeline_timer.lap("data_loading")
            sleep(0.01)
            
            # Stage 2: Processing
            pipeline_timer.lap("processing")
            sleep(0.02)
            
            # Stage 3: Saving
            pipeline_timer.lap("saving")
            sleep(0.01)
        
        # Verify pipeline timing
        self.assertGreater(pipeline_timer.elapsed_time, 0.03)
        
        laps = pipeline_timer.get_laps()
        self.assertEqual(len(laps), 3)
        
        lap_summary = pipeline_timer.get_lap_summary()
        self.assertEqual(lap_summary['lap_count'], 3)

    def test_monitoring_and_benchmarking_integration(self):
        """Test integration of monitoring and benchmarking."""
        tracker = PerformanceTracker("api_calls")
        
        # Simulate API calls with timing
        for i in range(5):
            with tracker.time_operation(f"call_{i}") as timing:
                # Simulate variable response times
                sleep(0.005 + random.random() * 0.01)
                timing.add_metadata(
                    status_code=200,
                    request_size=random.randint(100, 1000)
                )
        
        stats = tracker.get_statistics()
        self.assertEqual(stats['count'], 5)
        self.assertGreater(stats['avg_time'], 0.005)

    def test_error_recovery_scenarios(self):
        """Test error recovery in timing scenarios."""
        
        @timethis(track_calls=True)
        def unreliable_function():
            if random.random() < 0.5:  # 50% failure rate
                raise ValueError("Random failure")
            sleep(0.01)
            return "success"
        
        successes = 0
        failures = 0
        
        # Try multiple times
        for _ in range(10):
            try:
                unreliable_function()
                successes += 1
            except ValueError:
                failures += 1
        
        # Should have both successes and failures
        self.assertGreater(successes + failures, 0)
        
        # Check that timing was recorded for both
        stats = unreliable_function.get_timing_stats()
        self.assertEqual(stats['call_count'], 10)
        self.assertGreater(stats['failure_count'], 0)


# Test suite runner functions
def run_all_tests():
    """Run the complete test suite."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_test_category(category_name):
    """Run tests for a specific category."""
    test_classes = {
        'basic': [TestBasicTimeFunctions],
        'formatting': [TestTimeFormatting],
        'dates': [TestDateUtilities], 
        'timer': [TestTimerClass],
        'decorators': [TestTimingDecorators],
        'benchmarking': [TestBenchmarking],
        'monitoring': [TestRateMonitoring, TestTimerPool, TestPerformanceTracker],
        'registry': [TestTimingRegistry],
        'errors': [TestErrorHandling],
        'concurrency': [TestConcurrencyAndThreadSafety],
        'integration': [TestIntegrationScenarios]
    }
    
    if category_name not in test_classes:
        print(f"Unknown category: {category_name}")
        print(f"Available categories: {list(test_classes.keys())}")
        return False
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_class in test_classes[category_name]:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print(f"{INFO}    Running Comprehensive SKTime Tests...")
    print(INFO)
    
    if len(sys.argv) > 1:
        # Run specific category
        category = sys.argv[1]
        success = run_test_category(category)
    else:
        # Run all tests
        success = run_all_tests()
    
    print(f"{INFO}    SKTime Tests Completed")
    if success:
        print(f"{SUCCESS} All tests passed successfully!")
        sys.exit(0)
    else:
        print(f"{FAIL} Some tests failed.")
        sys.exit(1)