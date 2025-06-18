#!/usr/bin/env python3
"""
Test module for SKTime functionality.

This module contains comprehensive tests for the SKTime system, including
basic time functions, stopwatch functionality, timing accuracy, and
error handling.

Run with:
    python3.11 -. pytest tests/test_suitkaise/test_sktime/test_sktime.py -v

Or with unittest:
    python3.11 -m unittest tests.test_suitkaise.test_sktime.test_sktime -v

"""
import unittest
import time
import threading
import sys
from pathlib import Path

# add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Visual indicators for test output
INFO = "⬜️" * 40 + "\n\n\n"
FAIL = "\n\n   " + "❌" * 10 + " "
SUCCESS = "\n\n   " + "🟩" * 10 + " "
RUNNING = "🔄" * 40 + "\n\n"
CHECKING = "🧳" * 40 + "\n"
WARNING = "\n\n   " + "🟨" * 10 + " "

from suitkaise.sktime import now, sleep, elapsed, Stopwatch

class TestBasicTimeFunctions(unittest.TestCase):
    """Test basic time utility functions."""

    def test_now_returns_float(self):
        """
        Test that now() returns a float timestamp.

        This test:
        - calls sktime.now() function
        - verifies return type is float
        - checks that timestamp makes sense
        
        """
        current_time = now()

        # check return type
        self.assertIsInstance(current_time, float)

        # check that time is after 2024
        self.assertGreater(current_time, 1700000000.0, "Timestamp should be after 2024")

        # check that time is before 2030
        self.assertLess(current_time, 1900000000.0, "Timestamp should be before 2030")


    def test_now_progression(self):
        """
        Test that now() returns increasing values over time.

        This test:
        - takes multiple timestamps with small delays
        - verifies that time is progressing forward
        
        """
        timestamps = []

        for i in range(3):
            timestamps.append(now())
            time.sleep(0.01)

        for i in range(1, len(timestamps)):
            self.assertGreater(timestamps[i], timestamps[i-1],
                             f"Timestamp {i} should be greater than timestamp {i-1}")
            
    def test_sleep_basic(self):
        """
        Test basic sleep functionality.
        
        This test:
        - Records start time
        - Sleeps for a specified duration
        - Records end time
        - Verifies actual sleep time is close to requested time
        """
        sleep_duration = 0.1  # 100ms
        tolerance = 0.05      # 50ms tolerance for system timing variations
        
        start_time = now()
        sleep(sleep_duration)
        end_time = now()
        
        actual_duration = end_time - start_time
        
        # Check that actual duration is close to requested duration
        self.assertGreater(actual_duration, sleep_duration - tolerance,
                          f"Sleep duration {actual_duration} too short")
        self.assertLess(actual_duration, sleep_duration + tolerance,
                       f"Sleep duration {actual_duration} too long")
        
    def test_sleep_with_zero(self):
        """
        Test sleep with zero duration.
        
        This test:
        - Calls sleep(0)
        - Verifies it returns quickly without error
        - Ensures minimal time has passed
        """
        start_time = now()
        sleep(0)
        end_time = now()
        
        # Should complete very quickly (within 10ms)
        actual_duration = end_time - start_time
        self.assertLess(actual_duration, 0.01)
    
    def test_sleep_with_fractional_seconds(self):
        """
        Test sleep with fractional seconds.
        
        This test:
        - Sleeps for a fractional amount (0.05 seconds)
        - Verifies timing accuracy with fractional values
        """
        sleep_duration = 0.05  # 50ms
        tolerance = 0.02       # 20ms tolerance
        
        start_time = now()
        sleep(sleep_duration)
        end_time = now()
        
        actual_duration = end_time - start_time
        self.assertAlmostEqual(actual_duration, sleep_duration, delta=tolerance)

    def test_elapsed_calculation(self):
        """
        Test elapsed time calculation function.
        
        This test:
        - Creates start and end timestamps
        - Calculates elapsed time using elapsed() function
        - Verifies the calculation is correct
        """
        start_time = 1000.0
        end_time = 1005.5
        expected_elapsed = 5.5
        
        calculated_elapsed = elapsed(start_time, end_time)
        
        self.assertEqual(calculated_elapsed, expected_elapsed)
        self.assertIsInstance(calculated_elapsed, float)
    
    def test_elapsed_with_real_times(self):
        """
        Test elapsed calculation with real timestamps.
        
        This test:
        - Takes real timestamps around a sleep
        - Uses elapsed() function to calculate duration
        - Compares with direct subtraction
        """
        start = now()
        sleep(0.05)  # 50ms
        end = now()
        
        elapsed_time = elapsed(start, end)
        direct_calculation = end - start
        
        # Both methods should give the same result
        self.assertEqual(elapsed_time, direct_calculation)
        
        # Should be approximately 50ms
        self.assertAlmostEqual(elapsed_time, 0.05, delta=0.02)

class TestStopwatchBasic(unittest.TestCase):
    """Test basic Stopwatch functionality."""
    
    def setUp(self):
        """
        Set up test fixtures before each test.
        
        Creates a fresh Stopwatch instance for each test to ensure
        test isolation.
        """
        self.stopwatch = Stopwatch()
    
    def test_stopwatch_initialization(self):
        """
        Test Stopwatch initialization state.
        
        This test:
        - Creates a new Stopwatch
        - Verifies all initial values are correct
        - Ensures it's in the expected initial state
        """
        # Check initial state
        self.assertIsNone(self.stopwatch.start_time)
        self.assertIsNone(self.stopwatch.end_time)
        self.assertEqual(self.stopwatch.paused_time, 0)
        self.assertIsNone(self.stopwatch._pause_start)

    def test_basic_start_stop(self):
        """
        Test basic start and stop functionality.
        
        This test:
        - Starts the stopwatch
        - Waits a short time
        - Stops the stopwatch
        - Verifies the elapsed time is reasonable
        """
        # Start the stopwatch
        self.stopwatch.start()
        
        # Verify start_time was set
        self.assertIsNotNone(self.stopwatch.start_time)
        self.assertIsNone(self.stopwatch.end_time)
        
        # Wait a bit
        sleep(0.05)  # 50ms
        
        # Stop and get elapsed time
        elapsed_time = self.stopwatch.stop()
        
        # Verify timing
        self.assertIsInstance(elapsed_time, float)
        self.assertGreater(elapsed_time, 0.04)  # At least 40ms
        self.assertLess(elapsed_time, 0.1)      # Less than 100ms
        
        # Verify end_time was set
        self.assertIsNotNone(self.stopwatch.end_time)

    def test_multiple_start_stop_cycles(self):
        """
        Test multiple start/stop cycles.
        
        This test:
        - Runs multiple start/stop cycles
        - Verifies each cycle works independently
        - Ensures previous state is reset properly
        """
        timings = []
        
        for i in range(3):
            self.stopwatch.start()
            sleep(0.02)  # 20ms each
            elapsed_time = self.stopwatch.stop()
            timings.append(elapsed_time)
        
        # All timings should be reasonable
        for i, timing in enumerate(timings):
            self.assertGreater(timing, 0.01, f"Timing {i} too short: {timing}")
            self.assertLess(timing, 0.05, f"Timing {i} too long: {timing}")

    def test_restart_behavior(self):
        """
        Test that starting again resets the stopwatch.
        
        This test:
        - Starts stopwatch
        - Starts again (should reset)
        - Verifies state was properly reset
        """
        # First start
        self.stopwatch.start()
        first_start_time = self.stopwatch.start_time
        sleep(0.01)
        
        # Start again (should reset)
        self.stopwatch.start()
        second_start_time = self.stopwatch.start_time
        
        # Second start time should be later than first
        self.assertGreater(second_start_time, first_start_time)
        
        # Paused time should be reset to 0
        self.assertEqual(self.stopwatch.paused_time, 0)
        self.assertIsNone(self.stopwatch._pause_start)

class TestStopwatchPauseResume(unittest.TestCase):
    """Test Stopwatch pause and resume functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stopwatch = Stopwatch()
    
    def test_pause_resume_basic(self):
        """
        Test basic pause and resume functionality.
        
        This test:
        - Starts stopwatch
        - Runs for a bit
        - Pauses for a bit  
        - Resumes and runs more
        - Verifies paused time is excluded from total
        """
        # Start and run for ~25ms
        self.stopwatch.start()
        sleep(0.025)
        
        # Pause
        self.stopwatch.pause()
        pause_time = now()
        
        # Verify pause state
        self.assertIsNotNone(self.stopwatch._pause_start)
        
        # Stay paused for ~50ms (this should NOT count toward elapsed time)
        sleep(0.05)
        
        # Resume
        self.stopwatch.resume()
        resume_time = now()
        
        # Verify resume state
        self.assertIsNone(self.stopwatch._pause_start)
        
        # Run for another ~25ms
        sleep(0.025)
        
        # Stop and check total time
        total_elapsed = self.stopwatch.stop()
        
        # Total should be approximately 50ms (25ms + 25ms), 
        # NOT 100ms (which would include the pause time)
        self.assertGreater(total_elapsed, 0.04)   # At least 40ms
        self.assertLess(total_elapsed, 0.08)      # Less than 80ms
        
        # Verify paused_time was tracked
        self.assertGreater(self.stopwatch.paused_time, 0.04)  # At least 40ms pause
    
    def test_multiple_pause_resume_cycles(self):
        """
        Test multiple pause/resume cycles.
        
        This test:
        - Does several pause/resume cycles
        - Verifies cumulative pause time is tracked correctly
        """
        self.stopwatch.start()
        
        total_run_time = 0
        total_pause_time = 0
        
        # Do 3 cycles of run/pause
        for i in range(3):
            # Run for 20ms
            sleep(0.02)
            total_run_time += 0.02
            
            # Pause for 10ms
            self.stopwatch.pause()
            sleep(0.01)
            total_pause_time += 0.01
            self.stopwatch.resume()
        
        # Final measurement
        elapsed_time = self.stopwatch.stop()
        
        # Elapsed should be close to total_run_time, not total_run_time + total_pause_time
        expected_min = total_run_time * 0.8  # 80% of expected (timing tolerance)
        expected_max = total_run_time * 1.3  # 130% of expected (timing tolerance)
        
        self.assertGreater(elapsed_time, expected_min)
        self.assertLess(elapsed_time, expected_max)
    
    def test_pause_time_accumulation(self):
        """
        Test that pause time accumulates correctly.
        
        This test:
        - Pauses multiple times
        - Verifies paused_time accumulates correctly
        """
        self.stopwatch.start()
        
        # First pause
        self.stopwatch.pause()
        sleep(0.02)
        self.stopwatch.resume()
        
        first_pause_time = self.stopwatch.paused_time
        self.assertGreater(first_pause_time, 0.015)  # At least 15ms
        
        # Second pause  
        self.stopwatch.pause()
        sleep(0.03)
        self.stopwatch.resume()
        
        second_pause_time = self.stopwatch.paused_time
        
        # Second pause time should be greater than first
        self.assertGreater(second_pause_time, first_pause_time)
        
        # Difference should be approximately 30ms
        pause_difference = second_pause_time - first_pause_time
        self.assertGreater(pause_difference, 0.025)  # At least 25ms
        self.assertLess(pause_difference, 0.05)      # Less than 50ms


class TestStopwatchErrorHandling(unittest.TestCase):
    """Test Stopwatch error handling and edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stopwatch = Stopwatch()
    
    def test_stop_without_start_error(self):
        """
        Test error when stopping without starting.
        
        This test:
        - Attempts to stop a stopwatch that hasn't been started
        - Verifies appropriate RuntimeError is raised
        - Checks the error message is descriptive
        """
        with self.assertRaises(RuntimeError) as context:
            self.stopwatch.stop()
        
        self.assertIn("not been started", str(context.exception))
    
    def test_pause_without_start_error(self):
        """
        Test error when pausing without starting.
        
        This test:
        - Attempts to pause a stopwatch that hasn't been started
        - Verifies appropriate RuntimeError is raised
        """
        with self.assertRaises(RuntimeError) as context:
            self.stopwatch.pause()
        
        self.assertIn("not been started", str(context.exception))
    
    def test_resume_without_pause_error(self):
        """
        Test error when resuming without pausing.
        
        This test:
        - Starts stopwatch but doesn't pause
        - Attempts to resume
        - Verifies appropriate RuntimeError is raised
        """
        self.stopwatch.start()
        
        with self.assertRaises(RuntimeError) as context:
            self.stopwatch.resume()
        
        self.assertIn("not paused", str(context.exception))
    
    def test_double_pause_error(self):
        """
        Test error when pausing twice without resume.
        
        This test:
        - Starts and pauses stopwatch
        - Attempts to pause again
        - Verifies appropriate RuntimeError is raised
        """
        self.stopwatch.start()
        self.stopwatch.pause()
        
        with self.assertRaises(RuntimeError) as context:
            self.stopwatch.pause()
        
        self.assertIn("already paused", str(context.exception))
    
    def test_stop_while_paused_error(self):
        """
        Test error when stopping while paused.
        
        This test:
        - Starts and pauses stopwatch
        - Attempts to stop while paused
        - Verifies appropriate RuntimeError is raised
        """
        self.stopwatch.start()
        self.stopwatch.pause()
        
        with self.assertRaises(RuntimeError) as context:
            self.stopwatch.stop()
        
        self.assertIn("paused", str(context.exception))
    
    def test_resume_without_pause_after_start_error(self):
        """
        Test resume error in various states.
        
        This test:
        - Tries resume in different invalid states
        - Verifies errors are raised appropriately
        """
        # Case 1: Resume without any start
        with self.assertRaises(RuntimeError):
            self.stopwatch.resume()
        
        # Case 2: Start, then resume without pause
        self.stopwatch.start()
        with self.assertRaises(RuntimeError):
            self.stopwatch.resume()


class TestStopwatchEdgeCases(unittest.TestCase):
    """Test Stopwatch edge cases and special scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stopwatch = Stopwatch()
    
    def test_very_short_timing(self):
        """
        Test very short time measurements.
        
        This test:
        - Measures very short durations
        - Verifies stopwatch works with minimal times
        - Ensures precision is maintained
        """
        self.stopwatch.start()
        
        # Minimal delay
        sleep(0.001)  # 1ms
        
        elapsed_time = self.stopwatch.stop()
        
        # Should be positive, even if very small
        self.assertGreater(elapsed_time, 0)
        self.assertLess(elapsed_time, 0.01)  # Should be less than 10ms
    
    def test_immediate_start_stop(self):
        """
        Test immediate start/stop with no delay.
        
        This test:
        - Starts and immediately stops stopwatch
        - Verifies timing is handled correctly
        """
        self.stopwatch.start()
        elapsed_time = self.stopwatch.stop()
        
        # Should be a very small positive number
        self.assertGreaterEqual(elapsed_time, 0)
        self.assertLess(elapsed_time, 0.001)  # Should be less than 1ms
    
    def test_immediate_pause_resume(self):
        """
        Test immediate pause/resume operations.
        
        This test:
        - Starts, immediately pauses, immediately resumes
        - Verifies state transitions work correctly
        """
        self.stopwatch.start()
        self.stopwatch.pause()
        self.stopwatch.resume()
        
        # Should be able to stop normally
        elapsed_time = self.stopwatch.stop()
        self.assertGreaterEqual(elapsed_time, 0)
    
    def test_zero_pause_time(self):
        """
        Test pause/resume with minimal pause time.
        
        This test:
        - Pauses and immediately resumes
        - Verifies minimal pause time is handled correctly
        """
        self.stopwatch.start()
        sleep(0.01)  # 10ms active
        
        self.stopwatch.pause()
        # No sleep - immediate resume
        self.stopwatch.resume()
        
        sleep(0.01)  # 10ms more active
        elapsed_time = self.stopwatch.stop()
        
        # Should be approximately 20ms (two 10ms periods)
        self.assertGreater(elapsed_time, 0.015)  # At least 15ms
        self.assertLess(elapsed_time, 0.03)      # Less than 30ms


class TestConcurrentStopwatches(unittest.TestCase):
    """Test multiple Stopwatch instances and concurrent usage."""
    
    def test_independent_stopwatches(self):
        """
        Test that multiple Stopwatch instances are independent.
        
        This test:
        - Creates multiple stopwatch instances
        - Runs them with different timing
        - Verifies they don't interfere with each other
        """
        stopwatch1 = Stopwatch()
        stopwatch2 = Stopwatch()
        
        # Start first stopwatch
        stopwatch1.start()
        sleep(0.02)  # 20ms
        
        # Start second stopwatch (later)
        stopwatch2.start()
        sleep(0.01)  # 10ms
        
        # Stop both
        elapsed1 = stopwatch1.stop()
        elapsed2 = stopwatch2.stop()
        
        # First should be longer than second
        self.assertGreater(elapsed1, elapsed2)
        
        # Verify approximate timings
        self.assertGreater(elapsed1, 0.025)  # At least 25ms
        self.assertGreater(elapsed2, 0.008)  # At least 8ms
        self.assertLess(elapsed2, 0.02)      # Less than 20ms
    
    def test_concurrent_stopwatch_operations(self):
        """
        Test concurrent operations on different stopwatches.
        
        This test:
        - Uses threading to operate stopwatches concurrently
        - Verifies thread safety and independence
        """
        results = []
        errors = []
        
        def worker(worker_id, duration):
            """
            Worker function for threading test.
            
            Args:
                worker_id (int): Unique identifier for this worker
                duration (float): How long to run the stopwatch
            """
            try:
                stopwatch = Stopwatch()
                stopwatch.start()
                sleep(duration)
                elapsed = stopwatch.stop()
                results.append((worker_id, elapsed))
            except Exception as e:
                errors.append((worker_id, e))
        
        # Create threads with different durations
        threads = []
        durations = [0.01, 0.02, 0.03]  # 10ms, 20ms, 30ms
        
        for i, duration in enumerate(durations):
            thread = threading.Thread(target=worker, args=(i, duration))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Concurrent errors: {errors}")
        self.assertEqual(len(results), 3, f"Expected 3 results, got {len(results)}")
        
        # Sort results by worker_id for consistent checking
        results.sort(key=lambda x: x[0])
        
        # Verify approximate timings
        for i, (worker_id, elapsed) in enumerate(results):
            expected_duration = durations[i]
            self.assertGreater(elapsed, expected_duration * 0.8,  # 80% tolerance
                             f"Worker {worker_id} time too short")
            self.assertLess(elapsed, expected_duration * 1.5,     # 150% tolerance
                           f"Worker {worker_id} time too long")


class TestIntegrationWithOtherFunctions(unittest.TestCase):
    """Test integration of Stopwatch with other SKTime functions."""
    
    def test_stopwatch_with_now_function(self):
        """
        Test Stopwatch timing compared to manual now() calls.
        
        This test:
        - Uses both Stopwatch and manual now() timing
        - Compares results for consistency
        - Verifies both methods give similar results
        """
        # Manual timing with now()
        manual_start = now()
        
        # Stopwatch timing
        stopwatch = Stopwatch()
        stopwatch.start()
        
        # Wait
        sleep(0.05)  # 50ms
        
        # Stop both
        manual_end = now()
        stopwatch_elapsed = stopwatch.stop()
        
        manual_elapsed = manual_end - manual_start
        
        # Both methods should give similar results
        difference = abs(manual_elapsed - stopwatch_elapsed)
        self.assertLess(difference, 0.001,  # Less than 1ms difference
                       f"Manual: {manual_elapsed}, Stopwatch: {stopwatch_elapsed}")
    
    def test_stopwatch_with_elapsed_function(self):
        """
        Test Stopwatch with the elapsed() utility function.
        
        This test:
        - Captures start/end times from Stopwatch
        - Uses elapsed() function to calculate duration
        - Compares with Stopwatch's internal calculation
        """
        stopwatch = Stopwatch()
        
        # Start and capture the time
        stopwatch.start()
        start_time = stopwatch.start_time
        
        sleep(0.03)  # 30ms
        
        # Stop and capture times
        stopwatch_elapsed = stopwatch.stop()
        end_time = stopwatch.end_time
        
        # Calculate using elapsed() function
        function_elapsed = elapsed(start_time, end_time)
        
        # Both should give identical results (since no pause was used)
        self.assertEqual(stopwatch_elapsed, function_elapsed)
    
    def test_stopwatch_pause_with_manual_timing(self):
        """
        Test Stopwatch pause functionality against manual timing.
        
        This test:
        - Uses Stopwatch with pauses
        - Manually tracks active time periods
        - Verifies Stopwatch correctly excludes pause time
        """
        stopwatch = Stopwatch()
        
        # Track manual active time
        manual_active_time = 0
        
        # Start
        stopwatch.start()
        period1_start = now()
        
        # Active period 1
        sleep(0.02)  # 20ms
        period1_end = now()
        manual_active_time += period1_end - period1_start
        
        # Pause (this time should not count)
        stopwatch.pause()
        sleep(0.01)  # 10ms pause (should be excluded)
        stopwatch.resume()
        
        # Active period 2
        period2_start = now()
        sleep(0.02)  # 20ms
        period2_end = now()
        manual_active_time += period2_end - period2_start
        
        # Stop
        stopwatch_elapsed = stopwatch.stop()
        
        # Stopwatch should be close to manual active time
        difference = abs(stopwatch_elapsed - manual_active_time)
        self.assertLess(difference, 0.005,  # 5ms tolerance
                       f"Stopwatch: {stopwatch_elapsed}, Manual: {manual_active_time}")


# Test runner functions
def run_tests():
    """
    Run all tests with detailed output.
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


def run_specific_test(test_class_name):
    """
    Run a specific test class.
    
    Args:
        test_class_name (str): Name of the test class to run
        
    Returns:
        bool: True if tests passed, False otherwise
    """
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(globals()[test_class_name])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # If run directly, execute all tests
    print(f"{INFO}    Running SKTime Tests...")
    print(INFO)
    
    success = run_tests()
    
    print(f"{INFO}    SKTime Tests Completed")
    if success:
        print(f"{SUCCESS} All tests passed successfully!")
        sys.exit(0)
    else:
        print(f"{FAIL} Some tests failed.")
        sys.exit(1)