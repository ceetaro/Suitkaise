"""
SKTime API - Smart Timing Operations for Suitkaise

This module provides user-friendly timing functionality with statistical analysis,
sophisticated timing classes, and convenient decorators for performance measurement.

Key Features:
- Simple timing functions (now, sleep, elapsed)
- Yawn class for delayed sleep operations  
- Timer for statistical timing analysis, pause and resume, context manager and decorator

Philosophy: Make timing operations intuitive while providing powerful analysis capabilities.
"""

import time
import threading
from typing import List, Optional, Union, Callable, Any, Dict
from functools import wraps

# Import internal time operations with fallback
try:
    from .._int.core.time_ops import (
        _elapsed_time,
        _Yawn,
        _Timer,
        _timethis_decorator,
        _get_current_time,
        _sleep,
        _TimerStats
    )
except ImportError:
    raise ImportError(
        "Internal time operations could not be imported. "
        "Ensure that the internal time operations module is available."
    )


# ============================================================================
# Simple Timing Functions
# ============================================================================

def now() -> float:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import sktime
        
        start_time = sktime.now()
        ```
    ────────────────────────────────────────────────────────\n

    Get current Unix timestamp. Same as `get_current_time()`. 
    
    Equivalent to `time.time()`.
    
    Returns:
        Current Unix timestamp as a float
    """
    return _get_current_time()


def get_current_time() -> float:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import sktime
        
        start_time = sktime.get_current_time()
        ```
    ────────────────────────────────────────────────────────\n

    Get current Unix timestamp. Same as `now()`. 
    
    Equivalent to `time.time()`.
    
    Returns:
        Current Unix timestamp as float
    """
    return _get_current_time()


def sleep(seconds: float) -> float:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import sktime

        start_time = sktime.now()
        
        # sleep for 2 seconds
        sktime.sleep(2)

        end_time = sktime.now()

        # elapsed time should be about 2 seconds
        elapsed_time = end_time - start_time
        ```
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import sktime
        
        start_time = sktime.now()
        
        end_time = sktime.sleep(2)
        ```
    ────────────────────────────────────────────────────────\n

    Sleep the current thread for a given number of seconds.

    Optionally returns the current time after sleeping.
    
    Sleep is functionally equivalent to `time.sleep()`.
    
    Args:
        `seconds`: Number of seconds to sleep (can be fractional)

    Returns:
        Current time after sleeping
    """
    _sleep(seconds)

    return now()


def elapsed(time1: float, time2: Optional[float] = None) -> float:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import sktime
        
        start_time = sktime.now()
        
        sktime.sleep(2)
        
        elapsed = sktime.elapsed(start_time) # end time automatically set to current time
        
        # with 2 times
        start_time = sktime.now() # 100
        sktime.sleep(2)
        end_time = sktime.now() # 102
        
        elapsed1 = sktime.elapsed(start_time, end_time)  # |100 - 102| = 2
        elapsed2 = sktime.elapsed(end_time, start_time)  # |102 - 100| = 2
        
        elapsed3 = sktime.elapsed(start_time)       # Uses current time as end
        ```
    ────────────────────────────────────────────────────────\n

    Order-independent elapsed time calculation with automatic precision.
    
    Order doesn't matter - always returns positive elapsed time.
    If only one time is provided, calculates elapsed time from that time to when `elapsed()` is called.
    Uses `math.fabs()` for best precision when calculating absolute value of floats.
    
    Args:
        `time1`: First timestamp
        `time2`: Second timestamp (defaults to current time if `None`)
        
    Returns:
        Absolute elapsed time in seconds as a float
    
    """
    return _elapsed_time(time1, time2)


# ============================================================================
# Yawn Class - Delayed Sleep Operations
# ============================================================================

class Yawn:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import sktime
        
        # use it to sleep a program using too much memory
        mem_use_limiter = sktime.Yawn(sleep_duration=3, yawn_threshold=5)
        
        # while the program is running, this loop will not do work while the memory usage is too high
        while program_running:
            if mem_usage > max_recommended_mem:
                mem_use_limiter.yawn()
                sktime.sleep(0.5)
            else:
                do_work() # run your program code
                sktime.sleep(0.5)
        ```
    ────────────────────────────────────────────────────────\n

    Sleep controller that sleeps after a specified number of "yawns".
    
    `Yawn` lets you add delays that only happen after multiple calls, instead of 
    delaying every single time. Use this to rate limit requests to APIs or manage 
    program pauses due to user input, wait for processing to finish, etc. Also 
    helpful for reducing memory pressure during high usage periods.
    
    When you might use `Yawn`:
    - Limit API calls to stay under rate limits
    - Delay request batches to websites to avoid being blocked
    - Let the system cool down during high usage periods
    - Retry failed network requests with increasing delays

    Key Features:
    - Automatic counter reset after sleep
    - Optional logging when sleep occurs
    - No sleep overhead until threshold is reached
    
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: Web scraping with respectful rate limiting
        from suitkaise import sktime
        import requests
        
        # Sleep for 10 seconds after every 20 requests
        rate_limiter = sktime.Yawn(sleep_duration=10, yawn_threshold=20, log_sleep=True)
        
        urls_to_scrape = [
            "https://api.github.com/users/octocat",
            "https://api.github.com/users/torvalds",
            # ... hundreds more URLs
        ]
        
        for url in urls_to_scrape:
            # Make the request
            response = requests.get(url)
            process_response(response)
            
            # Check if we should take a break
            rate_limiter.yawn()  # Only sleeps after 20 calls
            
            # Small delay between each request
            sktime.sleep(0.1)
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Real use case: File processing with cooling breaks
        from suitkaise import sktime
        
        processor = sktime.Yawn(sleep_duration=5, yawn_threshold=50)
        
        for image_file in large_image_directory:
            # Process intensive image operations
            resize_image(image_file)
            apply_filters(image_file)
            
            processor.yawn()  # Take a 5-second break every 50 images
        ```
    ────────────────────────────────────────────────────────
    """
    
    def __init__(self, sleep_duration: float, yawn_threshold: int, log_sleep: bool = False):
        """
        ────────────────────────────────────────────────────────
            ```python
            # Sleep for 2 seconds after every 5 yawns, with logging
            yawn_controller = Yawn(sleep_duration=2.0, yawn_threshold=5, log_sleep=True)
            ```
        ────────────────────────────────────────────────────────\n
        Initialize a `Yawn` controller.
        
        Args:
            `sleep_duration`: How long to sleep when threshold is reached
            `yawn_threshold`: Number of yawns before sleeping
            `log_sleep`: Whether to print when sleep occurs
        """
        self._yawn = _Yawn(sleep_duration, yawn_threshold, log_sleep)
    
    def yawn(self) -> bool:
        """
        ────────────────────────────────────────────────────────
            ```python
            # yawn
            yawn_controller.yawn()

            # yawn returns True if sleep occurred, False otherwise
            if yawn_controller.yawn():
                print("Just slept!")
            else:
                print("Still counting yawns...")
            ```
        ────────────────────────────────────────────────────────\n

        Register a yawn. Sleep if threshold is reached.
        
        Returns:
            `True` if sleep occurred, `False` otherwise
        """
        return self._yawn.yawn()
    
    def reset(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # reset the yawn counter
            yawn_controller.reset()  # Start counting from 0 again
            ```
        ────────────────────────────────────────────────────────\n

        Reset the yawn counter without sleeping.
        """
        self._yawn.reset()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        ────────────────────────────────────────────────────────
            ```python
            # get statistics about yawn behavior
            stats = yawn_controller.get_stats()

            # access the statistics
            print(f"Current yawns: {stats['current_yawns']}")
            print(f"Number of yawns required to sleep: {stats['yawn_threshold']}")
            print(f"Yawns until sleep: {stats['yawns_until_sleep']}")
            print(f"Total sleeps so far: {stats['total_sleeps']}")
            print(f"Sleep duration: {stats['sleep_duration']}")
            ```
        ────────────────────────────────────────────────────────\n

        Get statistics about yawn behavior.
        
        Returns:
            Dictionary with yawn statistics
        """
        return self._yawn.get_stats()


# ============================================================================
# Timer Class - Statistical Timing Analysis
# ============================================================================

class Timer:
    """
    ────────────────────────────────────────────────────────
        ```python
        # basic usage
        from suitkaise import sktime

        # create a timer
        timer = sktime.Timer()

        # start timing
        timer.start()

        # stop timing (returns elapsed time)
        elapsed_time = timer.stop()

        # pause timing
        timer.pause()

        # resume timing
        timer.resume()

        # lap timer (returns elapsed time for this lap)
        lap_time = timer.lap()

        # add a lap time to the timer manually
        timer.add_time(1.5)

        # get statistics about the times measured
        stats = timer.get_statistics()

        # reset the timer
        timer.reset()
        ```
    ────────────────────────────────────────────────────────\n

    Statistical timer for collecting and analyzing execution times.
    
    Provides comprehensive timing statistics including mean, median,
    standard deviation, and percentiles for performance analysis.
    Can be used as a context manager or with decorators. Can be paused 
    and resumed.

    ────────────────────────────────────────────────────────
        ```python
        # available statistics

        # original start time
        original_start_time = timer.original_start_time

        # number of times measured
        num_times = timer.num_times

        # most recent time measured and its index (0-based)
        most_recent = timer.most_recent
        most_recent_index = timer.most_recent_index

        # total time of all measurements
        total_time = timer.total_time

        # total time paused
        total_time_paused = timer.total_time_paused

        # mean, median, min, max, stdev, variance
        mean = timer.mean
        median = timer.median
        min = timer.min
        max = timer.max
        stdev = timer.stdev
        variance = timer.variance

        # percentile
        percentile = timer.percentile(n)

        # get time by index
        time_at_index = timer.get_time(index)

        # get slowest time and its index
        slowest_time = timer.slowest_time
        slowest_time_index = timer.slowest_time_index

        # get fastest time and its index
        fastest_time = timer.fastest_time
        fastest_time_index = timer.fastest_time_index

        # get statistics all at once
        statistics = timer.get_statistics()
        ```
    ────────────────────────────────────────────────────────\n
    
    Using `get_statistics()` creates an instance of the timer's current statistics, 
    and won't change further. You can freely use this instance to get statistics 
    quickly without needing to acquire a lock.

    You can access the statistics just like you would access them from the Timer itself.
    
    ────────────────────────────────────────────────────────
        ```python
        # basic timing with start() and stop()
        from suitkaise import sktime

        # create a timer
        timer = sktime.Timer()
        timer.start()
        
        # download a large file
        current_file = download_file("https://example.com/data.zip")
        
        # pause timer while user decides what to do next
        timer.pause()
        user_choice = input("Process file now? (y/n): ")  # This time won't be counted
        timer.resume()
        
        # process the file
        if user_choice.lower().strip() == 'y':
            process_downloaded_file()
        
        elapsed = timer.stop()  # records measurement in statistics
        print(f"Total processing time: {elapsed:.2f}s (excluding user input)")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # lap timing for batch operations
        from suitkaise import sktime

        # create a timer
        timer = sktime.Timer()
        timer.start()
        
        # process a batch of files
        files = ['data1.csv', 'data2.csv', 'data3.csv']
        for filename in files:
            process_csv_file(filename)
            timer.lap()  # Records time for this file and continues
        
        # stop timing and get statistics
        timer.stop()
        print(f"Average file processing: {timer.mean:.2f}s")
        print(f"Slowest file: {timer.slowest_time:.2f}s")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # adding pre-measured times
        from suitkaise import sktime

        # create a timer
        timer = sktime.Timer()

        # add a pre-measured time
        timer.add_time(1.5)  # Add a time you measured elsewhere

        # add another pre-measured time
        timer.add_time(2.1)  # Add another measurement

        # get statistics
        print(f"Average of added times: {timer.mean:.2f}s")
        ```
    ────────────────────────────────────────────────────────
    """
    
    def __init__(self):
        """Initialize a new timer."""
        self._timer = _Timer()
    
    def start(self) -> float:
        """
        ────────────────────────────────────────────────────────
            ```python
            start_time = timer.start()

            # ... do timed work ...
            ```
        ────────────────────────────────────────────────────────\n

        Start timing a new measurement.
        
        Returns:
            Start timestamp
        """
        return self._timer.start()
    
    def stop(self) -> float:
        """
        ────────────────────────────────────────────────────────
            ```python
            # if Timer has been started, stop() will record a measurement

            # and return the elapsed time
            elapsed = timer.stop()

            # you can also call stop() without an assigned variable
            timer.stop()
            ```
        ────────────────────────────────────────────────────────\n

        Stop timing and record the measurement.
        
        Returns:
            Elapsed time for this measurement
            
        Raises:
            `RuntimeError`: If timer was not started
        """
        result = self._timer.stop()
        # Internal may return float or (elapsed, paused_total)
        if isinstance(result, tuple):
            return result[0]
        return result

    def lap(self) -> float:
        """
        ────────────────────────────────────────────────────────
            ```python
            # if Timer has been started, lap() will record a lap time without stopping the timer

            # record a lap time
            lap_time = timer.lap()
            ```
        ────────────────────────────────────────────────────────\n

        Record a lap time.
        
        Returns:
            Elapsed time for this lap

        Raises:
            `RuntimeError`: If timer was not started
        """
        result = self._timer.lap()
        if isinstance(result, tuple):
            return result[0]
        return result

    def pause(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # if Timer has been started...

            # pause() will pause the timer and not record a measurement

            # pause the timer
            timer.pause()

            if timer.paused:
                # resume the timer
                timer.resume()
            ```
        ────────────────────────────────────────────────────────\n

        Pause the timer. Use `resume()` to resume timing.

        Raises:
            `RuntimeError`: If timer was not started
        """
        self._timer.pause()
    
    def resume(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # if Timer has been started and then paused...

            # resume() will resume the timer and continue timing for the current measurement

            # pause the timer
            timer.pause()

            # resume the timer
            timer.resume()
            ```
        ────────────────────────────────────────────────────────\n

        Resume the timer if it has been paused.

        Raises:
            `RuntimeError`: If timer was not started
        """
        self._timer.resume()
    
    def add_time(self, time_measurement: float) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # add a pre-measured time to a Timer manually
            # (uses next available index)

            timer.add_time(1.5)
            ```
        ────────────────────────────────────────────────────────\n

        Manually add a timing measurement.
        """
        self._timer.add_time(time_measurement)

    @property
    def num_times(self) -> int:
        """
        Number of times measured.
        """
        return self._timer.num_times

    @property
    def original_start_time(self) -> Optional[float]:
        """
        Original start time of the timer.
        """
        return self._timer.original_start_time

    @property
    def most_recent(self) -> Optional[float]:
        """
        Most recent time measured.
        """
        return self._timer.most_recent

    @property
    def most_recent_lap(self) -> Optional[int]:
        """
        Index of the most recent time measured.
        """
        return self._timer.most_recent_index

    @property
    def result(self) -> Optional[float]:
        """
        Alias for most_recent.
        """
        return self._timer.most_recent

    @property
    def total_time(self) -> Optional[float]:
        """
        Total time of all measurements.
        """
        return self._timer.total_time

    @property
    def total_time_paused(self) -> Optional[float]:
        """
        Total time paused across all times.
        """
        return self._timer.total_time_paused
    
    @property
    def mean(self) -> Optional[float]:
        """
        Mean time of all measurements.
        """
        return self._timer.mean

    @property
    def median(self) -> Optional[float]:
        """
        Median time of all measurements.
        """
        return self._timer.median

    @property
    def slowest_lap(self) -> Optional[float]:
        """
        Time of the slowest lap.
        """
        return self._timer.slowest_lap

    @property
    def fastest_lap(self) -> Optional[float]:
        """
        Time of the fastest lap.
        """
        return self._timer.fastest_lap

    @property
    def slowest_time(self) -> Optional[float]:
        """
        Time of the slowest time.
        """
        return self._timer.slowest_time

    @property
    def fastest_time(self) -> Optional[float]:
        """
        Time of the fastest time.
        """
        return self._timer.fastest_time

    @property
    def min(self) -> Optional[float]:
        """
        Minimum time of all measurements.
        """
        return self._timer.min

    @property
    def max(self) -> Optional[float]:
        """
        Maximum time of all measurements.
        """
        return self._timer.max

    @property
    def stdev(self) -> Optional[float]:
        """
        Standard deviation of all measurements.
        """
        return self._timer.stdev

    @property
    def variance(self) -> Optional[float]:
        """
        Variance of all measurements.
        """
        return self._timer.variance

    def get_time(self, index: int) -> Optional[float]:
        """
        Get time by index.
        """
        return self._timer.get_time(index)

    def percentile(self, percent: float) -> Optional[float]:
        """
        Get percentile of all measurements.
        """
        return self._timer.percentile(percent)

    def get_statistics(self) -> Optional[_TimerStats]:
        """
        Get statistics of all measurements.
        """
        return self._timer.get_statistics()

    def reset(self) -> None:
        """
        Reset the timer.
        """
        self._timer.reset()


# ============================================================================
# TimeThis Context Manager
# ============================================================================

class TimeThis:
    """
    ────────────────────────────────────────────────────────
        ```python
        # create a one-use timer
        from suitkaise import sktime

        with sktime.TimeThis() as timer:

            # ... timed ...

        # timer is automatically stopped and single measurement is recorded

        # ... untimed ...
        print(f"Time taken: {timer.most_recent:.3f}s")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # create a context manager for an existing timer
        from suitkaise import sktime

        my_timer = sktime.Timer()
    
        def function1():
            with sktime.TimeThis(my_timer):

                # ... timed ...
                return create_random_object()

        def function2(object):

            # ... untimed ...
            if not is_valid(object):
                return None

            with sktime.TimeThis(my_timer):

                # ... timed ...
                process_object(object)

            # a time measurement is recorded when you exit the context manager

            # ... untimed ...
            return generate_data()

        function1()
        function2()

        print(f"Total time: {my_timer.total_time:.3f}s")
        ```
    ────────────────────────────────────────────────────────\n

    Context manager for timing code blocks with automatic timer management.
    
    Provides clean, easy-to-read timing for code blocks. Can work with
    independent timing contexts or accumulate statistics with explicit `Timer`.
    Supports pause/resume and lap timing within context blocks.
    
    When to Use What:
    - Use `TimeThis()` without `Timer` for quick, one-off timing measurements
    - Use `TimeThis(timer)` with explicit `Timer` for statistical analysis across multiple runs
    
    ────────────────────────────────────────────────────────
        ```python
        # Independent timing context

        # Real example: File compression comparison
        from suitkaise import sktime

        large_dataset = get_large_dataset()

        with sktime.TimeThis() as gzip_timer:
            compress_file_with_gzip("large_dataset.csv")
        
        print(f"GZIP compression took: {gzip_timer.most_recent:.3f}s")
        
        with sktime.TimeThis() as lzma_timer:
            compress_file_with_lzma("large_dataset.csv")
            
        print(f"LZMA compression took: {lzma_timer.most_recent:.3f}s")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Independent timing context

        # Real example: Database query with user interaction
        from suitkaise import sktime

        exported = False

        with sktime.TimeThis() as timer:
            results = database.query("SELECT * FROM users WHERE active=1")
            
            # Pause timing while user reviews results
            timer.pause()
            user_wants_export = input(f"Found {len(results)} users. Export to CSV? (y/n): ")

            if user_wants_export.lower() == 'y':
                timer.resume()
                export_to_csv(results)
                timer.stop()

            else:
                timer.stop()

        print(f"Database operation took: {timer.most_recent:.3f}s (excluding user input)")
        ```
    ────────────────────────────────────────────────────────
        ```python
        # Explicit timer

        # Real example: API call performance monitoring
        from suitkaise import sktime
        import requests

        api_timer = sktime.Timer()
        
        # Time multiple API calls to build statistics
        with sktime.TimeThis(api_timer) as timer:
            response = requests.get("https://api.github.com/users/octocat")
        
        print(f"API call 1: {timer.most_recent:.3f}s")
        
        with sktime.TimeThis(api_timer) as timer:
            response = requests.get("https://api.github.com/users/torvalds")
        
        print(f"API call 2: {timer.most_recent:.3f}s")
        print(f"Average API time: {api_timer.mean:.3f}s")
        ```
        ────────────────────────────────────────────────────────\n
    """

    def __init__(self, timer: Optional[Timer] = None):
        self.timer = timer or Timer()

    def pause(self):
        self.timer.pause()

    def resume(self):
        self.timer.resume()

    def lap(self):
        self.timer.lap()

    def __enter__(self):
        self.timer.start()
        return self.timer
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.timer.stop()


# ============================================================================
# Timing Decorators
# ============================================================================

def timethis(timer_instance: Optional[Timer] = None) -> Callable:
    """
    Create a timing decorator that accumulates statistics in a `Timer` instance.
    
    The `@timethis` decorator supports both explicit `Timer` instances and automatic 
    global timer creation, providing the ultimate convenience.
    
    Args:
        `timer_instance`: `Timer` to accumulate timing data in. If `None`, creates
                       a global timer with name pattern: `module_[class_]function_timer`

    Returns:
        Decorator function

    ────────────────────────────────────────────────────────\n

    Auto-created `Timer` (quickest way to use `Timer`):

        ```python
        from suitkaise import sktime

        # No timer argument - creates global timer automatically
        @sktime.timethis()  
        def quick_function():
            # Code to time
            pass
        
        # Call the function
        quick_function()
        
        # Access the auto-created timer with super simple access
        print(f"Last execution: {quick_function.timer.most_recent:.3f}s")
        
        # Call multiple times to build statistics
        for i in range(100):
            quick_function()
        
        print(f"Average: {quick_function.timer.mean:.3f}s")
        ```
    ────────────────────────────────────────────────────────\n

    Explicit `Timer` (for gathering data from multiple functions):

        ```python
        from suitkaise import sktime
        import random

        performance_timer = sktime.Timer()
        
        @sktime.timethis()
        @sktime.timethis(performance_timer)
        def multiply(a: int, b: int) -> int:
            return a * b

        @sktime.timethis()
        @sktime.timethis(performance_timer)
        def divide(a: int, b: int) -> float:
            return a / b

        set_a = []
        set_b = []
        for i in range(1000):
            set_a.append(random.randint(1, 100))
            set_b.append(random.randint(1, 100))

        # Build statistics over many calls
        for a, b in zip(set_a, set_b):
            multiply(a, b)
            divide(a, b)

    
        # Analyze performance for each function separately
        print(f"Average execution: {multiply.timer.mean:.3f}s")
        print(f"Slowest execution: {multiply.timer.slowest_time:.3f}s")

        print(f"Average execution: {divide.timer.mean:.3f}s")
        print(f"Slowest execution: {divide.timer.slowest_time:.3f}s")

        # Analyze performance for both functions together
        print(f"Average execution: {performance_timer.mean:.3f}s")
        print(f"Slowest execution: {performance_timer.slowest_time:.3f}s")
        ```
    ────────────────────────────────────────────────────────\n
    
    Note:
        Global `@timethis` timer naming convention (for debugging):
        - Module-level functions: `module_function_timer`
        - Class methods: `module_ClassName_method_timer`
        - Each function gets its own dedicated timer
        - Zero runtime overhead looking up the timer (resolved at decoration time)

    Note:
        `@timethis` decorator supports multiple decorators on the same function.
        The `timer_instance` parameter is used to specify the timer to use.
        If `None`, a global timer is created.
        
    """
    def decorator(func: Callable) -> Callable:
        # Determine timer to use
        if timer_instance is not None:
            # Use provided timer
            actual_timer = timer_instance._timer
            wrapper = _timethis_decorator(actual_timer)(func)
        else:
            # Create global timer with naming convention (do this once at decoration time)
            import inspect
            
            frame = inspect.currentframe()
            if frame is not None and frame.f_back is not None:
                module_name = frame.f_back.f_globals.get('__name__', 'unknown')
            else:
                module_name = 'unknown'
            
            # Extract just the module name (remove package path)
            if '.' in module_name:
                module_name = module_name.split('.')[-1]
            
            # Check if function is in a class by looking at qualname
            func_qualname = func.__qualname__
            if '.' in func_qualname:
                # Function is in a class: Class.method
                class_name, func_name = func_qualname.rsplit('.', 1)
                timer_name = f"{module_name}_{class_name}_{func_name}_timer"
            else:
                # Function is at module level
                func_name = func_qualname
                timer_name = f"{module_name}_{func_name}_timer"
            
            # Get or create global timer (thread-safe)
            if not hasattr(timethis, '_global_timers'):
                setattr(timethis, '_global_timers', {})
                setattr(timethis, '_timers_lock', threading.RLock())
            
            lock = getattr(timethis, '_timers_lock')
            with lock:
                global_timers = getattr(timethis, '_global_timers')
                if timer_name not in global_timers:
                    global_timers[timer_name] = Timer()
            
            actual_timer = global_timers[timer_name]._timer
            wrapper = _timethis_decorator(actual_timer)(func)
            
            # Attach timer to function for easy access
            setattr(wrapper, 'timer', global_timers[timer_name])
        
        return wrapper
    
    return decorator


def clear_global_timers() -> None:
    """Clear all auto-created global timers used by the timethis decorator.

    This is useful for long-lived processes or test environments to release
    references and start fresh for subsequently decorated functions.
    """
    if hasattr(timethis, '_timers_lock') and hasattr(timethis, '_global_timers'):
        lock = getattr(timethis, '_timers_lock')
        with lock:
            timers = getattr(timethis, '_global_timers')
            timers.clear()


# Note: We've enhanced timethis() to support both explicit Timer instances and
# automatic global timer creation, providing the best of both worlds: convenience
# when you want quick timing, and explicit control when you need detailed analysis.


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Simple timing functions
    'now',
    'get_current_time', 
    'sleep',
    'elapsed',
    
    # Timing classes
    'Yawn',
    'Timer',

    # Context managers
    'TimeThis',
    
    # Decorators
    'timethis',
    'clear_global_timers',
]