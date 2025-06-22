# add license here

# suitkaise/sktime/sktime.py

"""
Time utilities for Suitkaise.

"""
import time
from typing import Tuple, Any, Callable, Optional
from contextlib import contextmanager

import suitkaise.skglobal.skglobal as skglobal
import suitkaise.skfunction.skfunction as skfunction

# todo combine timer and stopwatch into timer and add pause and resume functionality to timer from stopwatch

class SKTimeError(Exception):
    """Error class for errors that occur when something goes wrong in SKTime."""
    pass

def now() -> float:
    """Get the current unix time."""
    return time.time()

def sleep(seconds: float) -> None:
    """Sleep for a given number of seconds."""
    time.sleep(seconds)

def elapsed(start_time: float, end_time: float) -> float:
    """
    Calculate the elapsed time between two timestamps.

    Args:
        start_time (float): The start time.
        end_time (float): The end time.

    Returns:
        float: The elapsed time in seconds.
    """
    if end_time < start_time:
        raise SKTimeError("End time must be greater than start time.")
    return end_time - start_time

def fmttime(seconds: float, precision: int = 2) -> str:
    """
    Format a duration in seconds into human-readable format.
    
    Args:
        seconds: Duration in seconds
        precision: Number of decimal places
        
    Returns:
        str: Formatted duration string
        
    Example:
        duration = format_duration(3661.5)  # "1h 1m 1.50s"
        quick = format_duration(0.003, 3)   # "3.000ms"
    """
    if seconds < 0:
        return f"-{format_duration(-seconds, precision)}"
    
    if seconds < 1e-6:  # Less than 1 microsecond
        return f"{seconds * 1e9:.{precision}f}ns"
    elif seconds < 1e-3:  # Less than 1 millisecond
        return f"{seconds * 1e6:.{precision}f}μs"
    elif seconds < 1:  # Less than 1 second
        return f"{seconds * 1e3:.{precision}f}ms"
    elif seconds < 60:  # Less than 1 minute
        return f"{seconds:.{precision}f}s"
    elif seconds < 3600:  # Less than 1 hour
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.{precision}f}s"
    elif seconds < 86400:  # Less than 1 day
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.{precision}f}s"
    else:  # 1 day or more
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{days}d {hours}h {minutes}m {secs:.{precision}f}s"
    
def timeout_after(seconds: float):
    """
    Decorator to add timeout to functions.
    
    Args:
        seconds: Timeout in seconds
        
    Returns:
        decorator: Function decorator
        
    Example:
        @timeout_after(5.0)
        def slow_function():
            sleep(10)  # Will raise SKTimeError after 5 seconds
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise SKTimeError(f"Function '{func.__name__}' timed out after {seconds} seconds")
            
            # Set timeout (Unix-like systems only)
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(seconds))
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    signal.alarm(0)  # Cancel alarm
                    signal.signal(signal.SIGALRM, old_handler)
                    
            except AttributeError:
                # Windows doesn't have SIGALRM, use basic timing check
                start = now()
                result = func(*args, **kwargs)
                if elapsed(start, now()) > seconds:
                    raise SKTimeError(f"Function '{func.__name__}' exceeded timeout of {seconds} seconds")
                return result
                
        return wrapper
    return decorator

def retry_with_delay(max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 1.0):
    """
    Decorator to retry functions with configurable delay.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        backoff_factor: Multiplier for delay after each failure
        
    Returns:
        decorator: Function decorator
        
    Example:
        @retry_with_delay(max_attempts=3, delay=1.0, backoff_factor=2.0)
        def flaky_function():
            # Will retry up to 3 times with delays: 1s, 2s, 4s
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:  # Don't sleep on last attempt
                        sleep(current_delay)
                        current_delay *= backoff_factor
            
            # All attempts failed
            raise SKTimeError(
                f"Function '{func.__name__}' failed after {max_attempts} attempts. "
                f"Last error: {last_exception}"
            ) from last_exception
            
        return wrapper
    return decorator

def benchmark(func: skfunction.AnyFunction, iterations: int = 1000, warmup: int = 100):
    """
    Benchmark a function with multiple iterations.
    
    Args:
        func: Function to benchmark (either a callable or SKFunction)
        iterations: Number of iterations to run
        warmup: Number of warmup iterations (not counted)
        
    Returns:
        dict: Benchmark results
        
    Example:
        results = benchmark(lambda: sum(range(1000)), iterations=5000)
        print(f"Average time: {results['avg_time']:.6f}s")
    """
    pass


class Timer:
    """
    Context manager for measuring elapsed time of a block of code.
    
    Usage:
    ```python
    with Timer() as timer:
    
        # ... some code ...

        elapsed_time = timer.stop() # call this before exiting the context manager
    ```
    """

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_time = None
        self.stopped = False

    def __enter__(self):
        """Start the timer."""
        self.start_time = now()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Stop the timer and calculate elapsed time."""
        if not self.stopped:
            raise RuntimeError("Timer has not been stopped.")
        
    def stop(self) -> float:
        """Stop the timer and return the elapsed time in seconds."""
        if self.start_time is None:
            raise RuntimeError("Timer has not been started.")
        self.end_time = now()
        self.elapsed_time = elapsed(self.start_time, self.end_time)
        self.stopped = True
        return self.elapsed_time




def measure_function_time(func: skfunction.AnyFunction, *args, **kwargs) -> Tuple[float, Any]:
    """
    Measure the execution time of a function.

    Args:
        skfunction.AnyFunction: The function to measure.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        Tuple[float, Any]: A tuple containing the elapsed time in seconds 
        and the function's return value.

    """
    start_time = now()
    error_occurred = False
    try:
        if isinstance(func, Callable):
            result = func(*args, **kwargs)

        elif isinstance(func, skfunction.SKFunction):
            # If the function is an SKFunction, we can call it directly
            extra_args = args if args else ()
            extra_kwargs = kwargs if kwargs else {}
            result = func.call(*extra_args, **extra_kwargs)

    except Exception as e:
        error_occurred = True
        result = None
        raise SKTimeError(f"An error occurred while measuring function time: {e}")
    
    finally:
        end_time = now()
        elapsed_time = elapsed(start_time, end_time)
        return elapsed_time, result if not error_occurred else None

class Stopwatch:
    """
    A simple stopwatch class to measure elapsed time with pause and resume functionality.

    Usage:
        stopwatch = Stopwatch()
        stopwatch.start()
        # ... some code ...
        stopwatch.pause()
        # ... paused ...
        stopwatch.resume()
        # ... some more code ...
        elapsed = stopwatch.stop()
    """

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.paused_time = 0
        self._pause_start = None

    def start(self):
        """Start the stopwatch."""
        self.start_time = now()
        self.paused_time = 0
        self._pause_start = None

    def pause(self):
        """Pause the stopwatch."""
        if self.start_time is None:
            raise RuntimeError("Stopwatch has not been started.")
        if self._pause_start is not None:
            raise RuntimeError("Stopwatch is already paused.")
        self._pause_start = now()

    def resume(self):
        """Resume the stopwatch."""
        if self._pause_start is None:
            raise RuntimeError("Stopwatch is not paused.")
        self.paused_time += now() - self._pause_start
        self._pause_start = None

    def stop(self) -> float:
        """Stop the stopwatch and return the elapsed time in seconds."""
        if self.start_time is None:
            raise RuntimeError("Stopwatch has not been started.")
        if self._pause_start is not None:
            raise RuntimeError("Stopwatch is paused. Resume it before stopping.")
        self.end_time = now()
        return elapsed(self.start_time, self.end_time) - self.paused_time
    
    def get_current_time(self) -> float:
        """Get the current elapsed time without stopping the stopwatch."""
        if self.start_time is None:
            raise RuntimeError("Stopwatch has not been started.")
        current_time = now()
        if self._pause_start is not None:
            return self._pause_start - self.start_time - self.paused_time
        return current_time - self.start_time - self.paused_time