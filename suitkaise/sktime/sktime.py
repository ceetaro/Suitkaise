# add license here

# suitkaise/sktime/sktime.py

"""
Time utilities for Suitkaise.

This module provides comprehensive timing functionality including:
- Basic time functions (now, sleep, elapsed)
- Timer class with context manager and pause/resume support
- Timing decorators (timeout, retry)
- Benchmarking utilities
- Time formatting functions

"""
import time
import signal
import statistics
import threading
import functools
import datetime
import os
from typing import Tuple, Any, Callable, Optional, Dict, List, Union, NamedTuple
from contextlib import contextmanager

import suitkaise.skfunction.skfunction as skfunction
from suitkaise.skglobal.skglobal import create_global, get_global, SKGlobalError, GlobalLevel
from suitkaise.rej.rej import RejSingleton, Rej


class SKTimeError(Exception):
    """Error class for errors that occur when something goes wrong in SKTime."""
    pass


def now() -> float:
    """
    Get the current unix time.
    
    Returns:
        float: Current timestamp in seconds since Unix epoch
        
    Example:
        timestamp = now()  # 1703123456.789
    """
    return time.time()


def sleep(seconds: float) -> None:
    """
    Sleep for a given number of seconds.
    
    Args:
        seconds (float): Number of seconds to sleep
        
    Example:
        sleep(0.1)  # Sleep for 100 milliseconds
    """
    time.sleep(seconds)


def elapsed(start_time: float, end_time: float) -> float:
    """
    Calculate the elapsed time between two timestamps.

    Args:
        start_time (float): The start time timestamp
        end_time (float): The end time timestamp

    Returns:
        float: The elapsed time in seconds

    Raises:
        SKTimeError: If end_time is less than start_time
        
    Example:
        start = now()
        sleep(1.0)
        end = now()
        duration = elapsed(start, end)  # ~1.0
    """
    if end_time < start_time:
        raise SKTimeError("End time must be greater than start time.")
    return end_time - start_time


def fmttime(seconds: float, precision: int = 2) -> str:
    """
    Format a duration in seconds into human-readable format.
    
    Args:
        seconds (float): Duration in seconds
        precision (int): Number of decimal places for seconds
        
    Returns:
        str: Formatted duration string
        
    Example:
        duration = fmttime(3661.5)    # "1h 1m 1.50s"
        quick = fmttime(0.003, 3)     # "3.000ms"
        negative = fmttime(-5.2)      # "-5.20s"
    """
    if seconds < 0:
        return f"-{fmttime(-seconds, precision)}"  # Fixed recursive call
    
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


def fmtdate(date_input: Union[float, datetime.datetime, str], 
           style: str = "relative", 
           reference_time: Optional[float] = None,
           precision: str = "auto",
           timezone: Optional[str] = None,
           custom_format: Optional[str] = None) -> str:
    """
    Format dates and timestamps into human-readable formats.
    
    Args:
        date_input: Date/time to format (timestamp, datetime, or ISO string)
        style: Format style - "relative", "absolute", "full", "short", "custom"
        reference_time: Reference time for relative formatting (default: now)
        precision: Precision level - "auto", "seconds", "minutes", "hours", "days"
        timezone: Timezone name (e.g., "UTC", "US/Pacific") - None for local
        custom_format: Custom strftime format when style="custom"
        
    Returns:
        str: Formatted date string
        
    Examples:
        # Relative formatting (default)
        fmtdate(now() - 3600)           # "1 hour ago"
        fmtdate(now() + 7200)          # "in 2 hours"
        fmtdate(now() - 86400 * 3)     # "3 days ago"
        
        # Absolute formatting  
        fmtdate(now(), style="absolute")     # "Jan 15, 2025 3:30 PM"
        fmtdate(now(), style="full")         # "Wednesday, January 15, 2025 3:30:45 PM"
        fmtdate(now(), style="short")        # "1/15/25 3:30 PM"
        
        # Custom formatting
        fmtdate(now(), style="custom", custom_format="%Y-%m-%d %H:%M")  # "2025-01-15 15:30"
        
        # With timezone
        fmtdate(now(), style="absolute", timezone="UTC")  # "Jan 15, 2025 8:30 PM UTC"
    """
    try:
        # Convert input to datetime object
        dt = _parse_date_input(date_input, timezone)
        
        # Handle custom format first
        if style == "custom":
            if custom_format is None:
                raise SKTimeError("custom_format required when style='custom'")
            result = dt.strftime(custom_format)
            if timezone:
                result += f" {timezone}"
            return result
        
        # For relative formatting
        if style == "relative":
            ref_time = reference_time if reference_time is not None else now()
            ref_dt = _parse_date_input(ref_time, timezone)
            return _format_relative_date(dt, ref_dt, precision)
        
        # For absolute formatting styles
        return _format_absolute_date(dt, style, timezone)
        
    except Exception as e:
        return f"<invalid date: {e}>"


def _parse_date_input(date_input: Union[float, datetime.datetime, str], 
                     timezone: Optional[str] = None) -> datetime.datetime:
    """
    Parse various date input formats into datetime object.
    
    Args:
        date_input: Date input in various formats
        timezone: Target timezone name
        
    Returns:
        datetime.datetime: Parsed datetime object
    """
    if isinstance(date_input, datetime.datetime):
        dt = date_input
    elif isinstance(date_input, (int, float)):
        dt = datetime.datetime.fromtimestamp(date_input)
    elif isinstance(date_input, str):
        # Try to parse ISO format string
        try:
            dt = datetime.datetime.fromisoformat(date_input.replace('Z', '+00:00'))
        except ValueError:
            # Try common formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"]:
                try:
                    dt = datetime.datetime.strptime(date_input, fmt)
                    break
                except ValueError:
                    continue
            else:
                raise SKTimeError(f"Unable to parse date string: {date_input}")
    else:
        raise SKTimeError(f"Unsupported date input type: {type(date_input)}")
    
    # Handle timezone conversion if needed
    if timezone and timezone.upper() == "UTC":
        # Convert to UTC if not already timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    return dt


def _format_relative_date(target_dt: datetime.datetime, 
                         reference_dt: datetime.datetime,
                         precision: str) -> str:
    """
    Format date as relative time (e.g., "2 hours ago", "in 3 days").
    
    Args:
        target_dt: Target datetime
        reference_dt: Reference datetime (usually now)
        precision: Precision level
        
    Returns:
        str: Relative time string
    """
    # Calculate time difference
    if target_dt.tzinfo != reference_dt.tzinfo:
        # Convert reference to same timezone as target for comparison
        if target_dt.tzinfo is None and reference_dt.tzinfo is not None:
            target_dt = target_dt.replace(tzinfo=reference_dt.tzinfo)
        elif target_dt.tzinfo is not None and reference_dt.tzinfo is None:
            reference_dt = reference_dt.replace(tzinfo=target_dt.tzinfo)
    
    diff = target_dt - reference_dt
    total_seconds = diff.total_seconds()
    abs_seconds = abs(total_seconds)
    
    is_future = total_seconds > 0
    
    # Determine appropriate time unit based on precision and magnitude
    if precision == "auto":
        if abs_seconds < 60:
            unit = "seconds"
        elif abs_seconds < 3600:
            unit = "minutes"
        elif abs_seconds < 86400:
            unit = "hours"
        elif abs_seconds < 604800:  # 7 days
            unit = "days"
        elif abs_seconds < 2629746:  # ~30.44 days (average month)
            unit = "weeks"
        elif abs_seconds < 31556952:  # ~365.24 days (average year)
            unit = "months"
        else:
            unit = "years"
    else:
        unit = precision
    
    # Calculate value based on unit
    if unit == "seconds":
        value = abs_seconds
        unit_name = "second"
    elif unit == "minutes":
        value = abs_seconds / 60
        unit_name = "minute"
    elif unit == "hours":
        value = abs_seconds / 3600
        unit_name = "hour"
    elif unit == "days":
        value = abs_seconds / 86400
        unit_name = "day"
    elif unit == "weeks":
        value = abs_seconds / 604800
        unit_name = "week"
    elif unit == "months":
        value = abs_seconds / 2629746
        unit_name = "month"
    elif unit == "years":
        value = abs_seconds / 31556952
        unit_name = "year"
    else:
        value = abs_seconds
        unit_name = "second"
    
    # Round to appropriate precision
    if value < 2:
        rounded_value = round(value, 1)
    else:
        rounded_value = round(value)
    
    # Handle special cases
    if abs_seconds < 1:
        return "just now"
    elif abs_seconds < 60 and precision == "auto":
        return f"{int(rounded_value)} second{'s' if rounded_value != 1 else ''} {'ago' if not is_future else 'from now'}"
    
    # Format with proper pluralization
    if rounded_value == 1:
        unit_text = unit_name
    else:
        unit_text = unit_name + "s"
    
    # Handle fractional display
    if rounded_value != int(rounded_value) and rounded_value < 10:
        value_text = f"{rounded_value:.1f}"
    else:
        value_text = str(int(rounded_value))
    
    if is_future:
        return f"in {value_text} {unit_text}"
    else:
        return f"{value_text} {unit_text} ago"


def _format_absolute_date(dt: datetime.datetime, style: str, timezone: Optional[str] = None) -> str:
    """
    Format date in absolute format styles.
    
    Args:
        dt: Datetime object to format
        style: Format style
        timezone: Timezone name for display
        
    Returns:
        str: Formatted date string
    """
    tz_suffix = f" {timezone}" if timezone else ""
    
    if style == "full":
        return dt.strftime("%A, %B %d, %Y %I:%M:%S %p") + tz_suffix
    elif style == "short":
        return dt.strftime("%m/%d/%y %I:%M %p") + tz_suffix
    elif style == "absolute":
        return dt.strftime("%b %d, %Y %I:%M %p") + tz_suffix
    elif style == "date_only":
        return dt.strftime("%B %d, %Y") + tz_suffix
    elif style == "time_only":
        return dt.strftime("%I:%M:%S %p") + tz_suffix
    elif style == "iso":
        return dt.isoformat() + tz_suffix
    else:
        # Default to absolute format
        return dt.strftime("%b %d, %Y %I:%M %p") + tz_suffix


def date_ago(days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> float:
    """
    Get timestamp for a time in the past.
    
    Args:
        days: Days ago
        hours: Hours ago  
        minutes: Minutes ago
        seconds: Seconds ago
        
    Returns:
        float: Timestamp for the specified time ago
        
    Example:
        yesterday = date_ago(days=1)
        two_hours_ago = date_ago(hours=2)
        formatted = fmtdate(yesterday)  # "1 day ago"
    """
    total_seconds = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
    return now() - total_seconds


def date_from_now(days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> float:
    """
    Get timestamp for a time in the future.
    
    Args:
        days: Days from now
        hours: Hours from now
        minutes: Minutes from now  
        seconds: Seconds from now
        
    Returns:
        float: Timestamp for the specified time in the future
        
    Example:
        tomorrow = date_from_now(days=1)
        in_two_hours = date_from_now(hours=2)
        formatted = fmtdate(tomorrow)  # "in 1 day"
    """
    total_seconds = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
    return now() + total_seconds


def parse_human_date(date_string: str) -> Optional[float]:
    """
    Parse human-readable date strings into timestamps.
    
    Args:
        date_string: Human-readable date string
        
    Returns:
        Optional[float]: Timestamp or None if parsing failed
        
    Example:
        timestamp = parse_human_date("2 hours ago")
        timestamp = parse_human_date("tomorrow")
        timestamp = parse_human_date("next Friday")
        timestamp = parse_human_date("Jan 15, 2025")
    """
    date_string = date_string.lower().strip()
    current_time = now()
    
    # Relative time patterns
    relative_patterns = {
        'now': 0,
        'just now': 0,
        'today': 0,
        'yesterday': -86400,
        'tomorrow': 86400,
    }
    
    if date_string in relative_patterns:
        return current_time + relative_patterns[date_string]
    
    # Pattern matching for "X ago" and "in X"
    import re
    
    # Match "X time_unit ago" or "X time_unit from now"
    ago_pattern = r'(\d+(?:\.\d+)?)\s+(second|minute|hour|day|week|month|year)s?\s+ago'
    future_pattern = r'(?:in\s+)?(\d+(?:\.\d+)?)\s+(second|minute|hour|day|week|month|year)s?(?:\s+from\s+now)?'
    
    ago_match = re.search(ago_pattern, date_string)
    future_match = re.search(future_pattern, date_string)
    
    if ago_match:
        value, unit = ago_match.groups()
        value = float(value)
        multiplier = _get_time_multiplier(unit)
        return current_time - (value * multiplier)
    
    if future_match:
        value, unit = future_match.groups()
        value = float(value)
        multiplier = _get_time_multiplier(unit)
        return current_time + (value * multiplier)
    
    # Try parsing absolute date formats
    try:
        dt = _parse_date_input(date_string)
        return dt.timestamp()
    except:
        pass
    
    return None


def _get_time_multiplier(unit: str) -> float:
    """Get seconds multiplier for time unit."""
    multipliers = {
        'second': 1,
        'minute': 60,
        'hour': 3600,
        'day': 86400,
        'week': 604800,
        'month': 2629746,  # Average month
        'year': 31556952   # Average year
    }
    return multipliers.get(unit, 1)


def time_since(timestamp: float, precision: str = "auto") -> str:
    """
    Get human-readable time since a timestamp.
    
    Args:
        timestamp: Unix timestamp
        precision: Precision level for formatting
        
    Returns:
        str: Human-readable time since
        
    Example:
        start_time = now()
        # ... do work ...
        duration = time_since(start_time)  # "2 minutes ago"
    """
    return fmtdate(timestamp, style="relative", precision=precision)


def time_until(timestamp: float, precision: str = "auto") -> str:
    """
    Get human-readable time until a timestamp.
    
    Args:
        timestamp: Unix timestamp in the future
        precision: Precision level for formatting
        
    Returns:
        str: Human-readable time until
        
    Example:
        deadline = date_from_now(days=5)
        remaining = time_until(deadline)  # "in 5 days"
    """
    return fmtdate(timestamp, style="relative", precision=precision)


def is_recent(timestamp: float, threshold_seconds: float = 3600) -> bool:
    """
    Check if a timestamp is recent (within threshold).
    
    Args:
        timestamp: Unix timestamp to check
        threshold_seconds: Threshold in seconds (default: 1 hour)
        
    Returns:
        bool: True if timestamp is within threshold of now
        
    Example:
        recent = is_recent(timestamp, threshold_seconds=300)  # Within 5 minutes
    """
    return abs(now() - timestamp) <= threshold_seconds


def date_range(start: Union[float, str], end: Union[float, str], 
               step_days: int = 1) -> List[float]:
    """
    Generate a range of timestamps between start and end dates.
    
    Args:
        start: Start date (timestamp or string)
        end: End date (timestamp or string)
        step_days: Step size in days
        
    Returns:
        List[float]: List of timestamps
        
    Example:
        # Get daily timestamps for the past week
        week_ago = date_ago(days=7)
        dates = date_range(week_ago, now(), step_days=1)
        
        for date in dates:
            print(fmtdate(date, style="date_only"))
    """
    if isinstance(start, str):
        start = parse_human_date(start) or now()
    if isinstance(end, str):
        end = parse_human_date(end) or now()
    
    if start > end:
        start, end = end, start
    
    dates = []
    current = start
    step_seconds = step_days * 86400
    
    while current <= end:
        dates.append(current)
        current += step_seconds
    
    return dates


def timeout_after(seconds: float):
    """
    Decorator to add timeout to functions.
    
    Args:
        seconds (float): Timeout in seconds
        
    Returns:
        Callable: Function decorator
        
    Example:
        @timeout_after(5.0)
        def slow_function():
            sleep(10)  # Will raise SKTimeError after 5 seconds
            return "Done"
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
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
        max_attempts (int): Maximum number of attempts
        delay (float): Initial delay between attempts in seconds
        backoff_factor (float): Multiplier for delay after each failure
        
    Returns:
        Callable: Function decorator
        
    Example:
        @retry_with_delay(max_attempts=3, delay=1.0, backoff_factor=2.0)
        def flaky_function():
            # Will retry up to 3 times with delays: 1s, 2s, 4s
            if random.random() < 0.7:  # 70% failure rate
                raise Exception("Random failure")
            return "Success"
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


def benchmark(func: Union[Callable, skfunction.SKFunction], 
              iterations: int = 1000, 
              warmup: int = 100,
              *args, **kwargs) -> Dict[str, Any]:
    """
    Benchmark a function with multiple iterations.
    
    Args:
        func: Function to benchmark (callable or SKFunction)
        iterations (int): Number of iterations to run for timing
        warmup (int): Number of warmup iterations (not counted in results)
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        dict: Benchmark results containing:
            - 'total_time': Total time for all iterations
            - 'avg_time': Average time per iteration
            - 'min_time': Fastest iteration time
            - 'max_time': Slowest iteration time
            - 'median_time': Median iteration time
            - 'std_dev': Standard deviation of iteration times
            - 'iterations': Number of iterations run
            - 'ops_per_second': Operations per second
            - 'warmup_time': Time spent in warmup iterations
        
    Example:
        def expensive_calc(n):
            return sum(i*i for i in range(n))
            
        results = benchmark(expensive_calc, iterations=1000, warmup=50, n=1000)
        print(f"Average time: {results['avg_time']:.6f}s")
        print(f"Ops/sec: {results['ops_per_second']:.0f}")
    """
    if iterations <= 0:
        raise SKTimeError("Iterations must be positive")
    if warmup < 0:
        raise SKTimeError("Warmup iterations cannot be negative")
    
    # Helper function to call the function appropriately
    def call_function():
        if isinstance(func, skfunction.SKFunction):
            return func.call(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    
    # Warmup phase
    warmup_start = now()
    for _ in range(warmup):
        try:
            call_function()
        except Exception as e:
            raise SKTimeError(f"Function failed during warmup: {e}") from e
    warmup_time = elapsed(warmup_start, now())
    
    # Benchmark phase
    times = []
    total_start = now()
    
    for i in range(iterations):
        iteration_start = now()
        try:
            result = call_function()
        except Exception as e:
            raise SKTimeError(f"Function failed on iteration {i+1}: {e}") from e
        iteration_end = now()
        
        iteration_time = elapsed(iteration_start, iteration_end)
        times.append(iteration_time)
    
    total_end = now()
    total_time = elapsed(total_start, total_end)
    
    # Calculate statistics
    avg_time = statistics.mean(times)
    min_time = min(times)
    max_time = max(times)
    median_time = statistics.median(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0.0
    ops_per_second = 1.0 / avg_time if avg_time > 0 else float('inf')
    
    return {
        'total_time': total_time,
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'median_time': median_time,
        'std_dev': std_dev,
        'iterations': iterations,
        'ops_per_second': ops_per_second,
        'warmup_time': warmup_time,
        'function_name': getattr(func, '__name__', str(func))
    }


class LapTime(NamedTuple):
    """
    Represents a lap time measurement.
    
    Attributes:
        lap_number (int): The lap number (starting from 1)
        timestamp (float): When this lap was recorded
        lap_time (float): Time for this specific lap
        total_time (float): Total elapsed time up to this lap
        name (str): Optional name/description for this lap
    """
    lap_number: int
    timestamp: float
    lap_time: float
    total_time: float
    name: str = ""


def timethis(store_in_global: str = None,
             return_timing: bool = False, 
             store_on_function: bool = True,
             callback: Callable = None,
             print_result: bool = False,
             track_calls: bool = True):
    """
    Decorator to time function execution with flexible storage options.
    
    Args:
        store_in_global (str): SKGlobal key to store timing results
        return_timing (bool): If True, return (result, timing_info) tuple
        store_on_function (bool): Store timing data on function object
        callback (Callable): Function to call with timing results
        print_result (bool): Whether to print timing results  
        track_calls (bool): Whether to track multiple calls with statistics
        
    Returns:
        Callable: Decorated function with timing capabilities
        
    Example:
        # Basic usage - access timing via function attribute
        @timethis()
        def calculate():
            return sum(range(1000))
        
        result = calculate()
        print(f"Took: {calculate.last_timing['duration']:.3f}s")
        
        # Store in SKGlobal
        @timethis(store_in_global="calc_time")
        def calculate():
            return sum(range(1000))
        
        result = calculate()
        timing = skglobal.get("calc_time")
        
        # Return timing with result
        @timethis(return_timing=True)
        def calculate():
            return sum(range(1000))
        
        result, timing_info = calculate()
        
        # Track multiple calls with statistics
        @timethis(track_calls=True, print_result=True)
        def api_call():
            sleep(0.1)
            return "response"
        
        # Call multiple times
        for i in range(5):
            api_call()
        
        stats = api_call.get_timing_stats()
        print(f"Average: {stats['avg_time']:.3f}s")
    """
    def decorator(func):
        # Initialize timing storage on the function
        if not hasattr(func, '_timing_data'):
            func._timing_data = {
                'last_timing': None,
                'all_timings': [],
                'call_count': 0,
                'total_time': 0.0
            }
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Start timing
            start_time = now()
            func_name = func.__name__
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                end_time = now()
                duration = elapsed(start_time, end_time)
                success = True
                error = None
                
            except Exception as e:
                end_time = now()
                duration = elapsed(start_time, end_time)
                success = False
                error = str(e)
                result = None
                raise
            
            finally:
                # Create timing info
                timing_info = {
                    'function_name': func_name,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'success': success,
                    'error': error,
                    'call_number': func._timing_data['call_count'] + 1,
                    'timestamp': end_time,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
                
                # Update function timing data
                if store_on_function:
                    func._timing_data['last_timing'] = timing_info
                    if track_calls:
                        func._timing_data['all_timings'].append(timing_info)
                        func._timing_data['call_count'] += 1
                        func._timing_data['total_time'] += duration
                
                # Store in SKGlobal if requested
                if store_in_global:
                    try:
                        if track_calls:
                            # Get or create global variable for tracking multiple calls
                            existing_global = get_global(store_in_global)
                            if existing_global:
                                # Update existing tracking data
                                existing_data = existing_global.get()
                                if existing_data and isinstance(existing_data, dict):
                                    existing_data.setdefault('timings', []).append(timing_info)
                                    existing_data['stats'] = _calculate_timing_stats(existing_data['timings'])
                                    existing_global.set(existing_data)
                                else:
                                    # Replace with proper tracking structure
                                    new_data = {
                                        'function_name': func_name,
                                        'timings': [timing_info],
                                        'stats': _calculate_timing_stats([timing_info])
                                    }
                                    existing_global.set(new_data)
                            else:
                                # Create new global variable with tracking
                                new_data = {
                                    'function_name': func_name,
                                    'timings': [timing_info],
                                    'stats': _calculate_timing_stats([timing_info])
                                }
                                create_global(
                                    name=store_in_global,
                                    value=new_data,
                                    level=GlobalLevel.TOP,
                                    persistent=True
                                )
                        else:
                            # Store just the latest timing
                            existing_global = get_global(store_in_global)
                            if existing_global:
                                existing_global.set(timing_info)
                            else:
                                create_global(
                                    name=store_in_global,
                                    value=timing_info,
                                    level=GlobalLevel.TOP,
                                    persistent=True
                                )
                    except SKGlobalError as e:
                        print(f"⚠️  Failed to store timing in SKGlobal '{store_in_global}': {e}")
                    except Exception as e:
                        print(f"⚠️  Unexpected error storing timing in SKGlobal '{store_in_global}': {e}")
                
                # Print result if requested
                if print_result and success:
                    formatted_time = fmttime(duration)
                    call_info = f" (call #{timing_info['call_number']})" if track_calls else ""
                    print(f"⏱️  {func_name}(){call_info} took {formatted_time}")
                elif print_result and not success:
                    formatted_time = fmttime(duration)
                    print(f"❌ {func_name}() failed after {formatted_time}: {error}")
                
                # Call callback if provided
                if callback:
                    try:
                        callback(timing_info)
                    except Exception as e:
                        print(f"⚠️  Timing callback failed: {e}")
            
            # Return result based on options
            if return_timing:
                return result, timing_info
            else:
                return result
        
        # Add convenience methods to the wrapped function
        def get_last_timing():
            """Get timing info from the last function call."""
            return func._timing_data.get('last_timing')
        
        def get_all_timings():
            """Get timing info from all function calls."""
            return func._timing_data.get('all_timings', []).copy()
        
        def get_timing_stats():
            """Get statistical summary of all timing data."""
            timings = func._timing_data.get('all_timings', [])
            if not timings:
                return {'call_count': 0}
            
            return _calculate_timing_stats(timings)
        
        def clear_timing_data():
            """Clear all stored timing data."""
            func._timing_data = {
                'last_timing': None,
                'all_timings': [],
                'call_count': 0,
                'total_time': 0.0
            }
        
        def print_timing_summary():
            """Print a formatted summary of timing statistics."""
            stats = get_timing_stats()
            if stats['call_count'] == 0:
                print(f"📊 {func.__name__}: No calls recorded")
                return
            
            print(f"📊 Timing Summary - {func.__name__}()")
            print("-" * 40)
            print(f"Total calls: {stats['call_count']}")
            print(f"Success rate: {stats['success_rate']:.1%}")
            print(f"Total time: {fmttime(stats['total_time'])}")
            print(f"Average time: {fmttime(stats['avg_time'])}")
            print(f"Fastest call: {fmttime(stats['min_time'])}")
            print(f"Slowest call: {fmttime(stats['max_time'])}")
            if stats['call_count'] > 1:
                print(f"Std deviation: {fmttime(stats['std_dev'])}")
        
        # Attach methods to wrapper function
        wrapper.get_last_timing = get_last_timing
        wrapper.get_all_timings = get_all_timings  
        wrapper.get_timing_stats = get_timing_stats
        wrapper.clear_timing_data = clear_timing_data
        wrapper.print_timing_summary = print_timing_summary
        wrapper._timing_data = func._timing_data
        
        return wrapper
    
    return decorator


def _calculate_timing_stats(timings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics from a list of timing records.
    
    Args:
        timings: List of timing dictionaries
        
    Returns:
        Dict with statistical summary
    """
    if not timings:
        return {'call_count': 0}
    
    durations = [t['duration'] for t in timings]
    successful_calls = [t for t in timings if t['success']]
    
    stats = {
        'call_count': len(timings),
        'success_count': len(successful_calls),
        'failure_count': len(timings) - len(successful_calls),
        'success_rate': len(successful_calls) / len(timings),
        'total_time': sum(durations),
        'avg_time': statistics.mean(durations),
        'min_time': min(durations),
        'max_time': max(durations),
        'median_time': statistics.median(durations),
        'first_call': timings[0]['timestamp'],
        'last_call': timings[-1]['timestamp']
    }
    
    if len(durations) > 1:
        stats['std_dev'] = statistics.stdev(durations)
    else:
        stats['std_dev'] = 0.0
    
    return stats


def get_global_timing(key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve timing data stored in SKGlobal.
    
    Args:
        key (str): SKGlobal key where timing data is stored
        
    Returns:
        Optional[Dict]: Timing data or None if not found
        
    Example:
        @timethis(store_in_global="my_function_timing")
        def my_function():
            return "result"
        
        my_function()
        timing = get_global_timing("my_function_timing")
        if timing:
            print(f"Duration: {timing['duration']:.3f}s")
    """
    try:
        timing_global = get_global(key)
        if timing_global:
            return timing_global.get()
        return None
    except SKGlobalError as e:
        print(f"⚠️  Failed to retrieve timing from SKGlobal '{key}': {e}")
        return None
    except Exception as e:
        print(f"⚠️  Unexpected error retrieving timing from SKGlobal '{key}': {e}")
        return None


def clear_global_timing(key: str) -> bool:
    """
    Clear timing data stored in SKGlobal.
    
    Args:
        key (str): SKGlobal key to clear
        
    Returns:
        bool: True if successfully cleared, False otherwise
    """
    try:
        timing_global = get_global(key)
        if timing_global:
            timing_global.remove()
            return True
        else:
            print(f"⚠️  No timing data found for key '{key}'")
            return False
    except SKGlobalError as e:
        print(f"⚠️  Failed to clear timing from SKGlobal '{key}': {e}")
        return False
    except Exception as e:
        print(f"⚠️  Unexpected error clearing timing from SKGlobal '{key}': {e}")
        return False


class TimingRegistry:
    """
    Global registry for function timing data using the Rej system.
    
    This is a timing-specific wrapper around RejSingleton that provides
    convenient methods for recording and analyzing function timing data.
    
    Example:
        # Get the global timing registry
        registry = TimingRegistry()
        
        # Or get a named registry
        api_registry = TimingRegistry("api_calls")
        
        @timethis(callback=registry.record_timing)
        def my_function():
            return "result"
        
        my_function()
        stats = registry.get_function_stats("my_function")
        registry.print_summary()
    """
    
    def __init__(self, registry_name: str = "default_timing"):
        """
        Initialize timing registry.
        
        Args:
            registry_name (str): Name of the registry (creates or gets existing)
        """
        self.registry_name = registry_name
        # Get or create the RejSingleton registry for timing data
        self._rej_registry = RejSingleton.get_registry(
            f"timing_{registry_name}",
            on_duplicate=Rej.Ruleset.OnDuplicate.OVERWRITE,  # Allow updating timing lists
            auto_serialize_check=True  # Ensure cross-process compatibility
        )
    
    def record_timing(self, timing_info: Dict[str, Any]):
        """
        Record a timing measurement.
        
        Args:
            timing_info: Timing data dictionary with function_name, duration, etc.
        """
        func_name = timing_info['function_name']
        
        # Get existing timing list or create new one
        existing_timings = self._rej_registry.get(func_name) or []
        
        # Add new timing
        existing_timings.append(timing_info)
        
        # Store back in registry
        self._rej_registry.register(func_name, existing_timings)
    
    def get_function_timings(self, func_name: str) -> List[Dict[str, Any]]:
        """Get all timing records for a specific function."""
        return self._rej_registry.get(func_name) or []
    
    def get_function_stats(self, func_name: str) -> Dict[str, Any]:
        """Get statistical summary for a specific function."""
        timings = self.get_function_timings(func_name)
        return _calculate_timing_stats(timings)
    
    def get_all_functions(self) -> List[str]:
        """Get list of all tracked function names."""
        return self._rej_registry.list_keys()
    
    def clear_function(self, func_name: str) -> bool:
        """Clear timing data for a specific function."""
        return self._rej_registry.remove(func_name)
    
    def clear_all(self):
        """Clear all timing data."""
        self._rej_registry.clear()
    
    def find_functions(self, filter_func: Callable[[str, List[Dict]], bool]) -> Dict[str, List[Dict]]:
        """
        Find functions that match a condition.
        
        Args:
            filter_func: Function that takes (function_name, timing_list) and returns bool
            
        Returns:
            Dict of matching function_name -> timing_list pairs
            
        Example:
            # Find functions with more than 10 calls
            busy_functions = registry.find_functions(
                lambda name, timings: len(timings) > 10
            )
            
            # Find functions with average time > 1 second
            slow_functions = registry.find_functions(
                lambda name, timings: statistics.mean([t['duration'] for t in timings]) > 1.0
            )
        """
        return self._rej_registry.find(filter_func)
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Get comprehensive information about this timing registry."""
        base_info = self._rej_registry.get_info()
        
        # Add timing-specific statistics
        all_timings = []
        for timings_list in self._rej_registry.list_items().values():
            all_timings.extend(timings_list)
        
        timing_stats = {
            'total_function_calls': len(all_timings),
            'unique_functions': len(self._rej_registry),
            'registry_name': self.registry_name
        }
        
        if all_timings:
            durations = [t['duration'] for t in all_timings]
            timing_stats.update({
                'total_duration': sum(durations),
                'avg_duration': statistics.mean(durations),
                'min_duration': min(durations),
                'max_duration': max(durations)
            })
        
        base_info.update(timing_stats)
        return base_info
    
    def print_summary(self):
        """Print a formatted summary of timing statistics."""
        info = self.get_registry_info()
        
        print(f"📊 Timing Registry Summary - {self.registry_name}")
        print("=" * 50)
        print(f"Unique functions: {info['unique_functions']}")
        print(f"Total function calls: {info['total_function_calls']}")
        
        if info['total_function_calls'] > 0:
            print(f"Total duration: {fmttime(info['total_duration'])}")
            print(f"Average duration: {fmttime(info['avg_duration'])}")
            print(f"Fastest call: {fmttime(info['min_duration'])}")
            print(f"Slowest call: {fmttime(info['max_duration'])}")
            
            print(f"\nPer-function breakdown:")
            for func_name in self.get_all_functions():
                stats = self.get_function_stats(func_name)
                if stats['call_count'] > 0:
                    print(f"  {func_name}: {stats['call_count']} calls, "
                          f"avg {fmttime(stats['avg_time'])}")
        else:
            print("No timing data recorded yet")
        
        print("=" * 50)
    
    def sync_to_skglobal(self, key: str, level: GlobalLevel = GlobalLevel.TOP):
        """
        Export timing data to SKGlobal for persistence/sharing.
        
        Args:
            key (str): SKGlobal key to store under
            level (GlobalLevel): Storage level
        """
        try:
            export_data = {
                'registry_name': self.registry_name,
                'exported_at': now(),
                'functions': {},
                'summary': self.get_registry_info()
            }
            
            # Export all function data with stats
            for func_name in self.get_all_functions():
                export_data['functions'][func_name] = {
                    'timings': self.get_function_timings(func_name),
                    'stats': self.get_function_stats(func_name)
                }
            
            # Store in SKGlobal
            existing_global = get_global(key)
            if existing_global:
                existing_global.set(export_data)
                print(f"✅ Updated SKGlobal '{key}' with timing data from {len(export_data['functions'])} functions")
            else:
                create_global(
                    name=key,
                    value=export_data,
                    level=level,
                    persistent=True
                )
                print(f"✅ Created SKGlobal '{key}' with timing data from {len(export_data['functions'])} functions")
                
        except Exception as e:
            print(f"❌ Failed to sync TimingRegistry to SKGlobal '{key}': {e}")
    
    def load_from_skglobal(self, key: str):
        """
        Import timing data from SKGlobal.
        
        Args:
            key (str): SKGlobal key to load from
        """
        try:
            timing_global = get_global(key)
            if timing_global:
                import_data = timing_global.get()
                if import_data and 'functions' in import_data:
                    # Import all function timing data
                    for func_name, func_data in import_data['functions'].items():
                        timings = func_data.get('timings', [])
                        if timings:
                            self._rej_registry.register(func_name, timings)
                    
                    print(f"✅ Loaded timing data for {len(import_data['functions'])} functions from SKGlobal '{key}'")
                else:
                    print(f"⚠️  No valid timing data found in SKGlobal '{key}'")
            else:
                print(f"⚠️  No data found in SKGlobal '{key}'")
        except Exception as e:
            print(f"❌ Failed to load TimingRegistry from SKGlobal '{key}': {e}")
    
    def get_top_functions(self, limit: int = 10, sort_by: str = "call_count") -> List[Dict[str, Any]]:
        """
        Get top functions by various metrics.
        
        Args:
            limit: Number of functions to return
            sort_by: Metric to sort by ("call_count", "total_time", "avg_time", "max_time")
            
        Returns:
            List of function statistics sorted by the specified metric
        """
        all_stats = []
        for func_name in self.get_all_functions():
            stats = self.get_function_stats(func_name)
            if stats['call_count'] > 0:
                stats['function_name'] = func_name
                all_stats.append(stats)
        
        # Sort by the specified metric
        if sort_by == "call_count":
            all_stats.sort(key=lambda x: x['call_count'], reverse=True)
        elif sort_by == "total_time":
            all_stats.sort(key=lambda x: x['total_time'], reverse=True)
        elif sort_by == "avg_time":
            all_stats.sort(key=lambda x: x['avg_time'], reverse=True)
        elif sort_by == "max_time":
            all_stats.sort(key=lambda x: x['max_time'], reverse=True)
        else:
            raise ValueError(f"Unknown sort metric: {sort_by}")
        
        return all_stats[:limit]
    
    @property
    def rej_registry(self) -> RejSingleton:
        """Access the underlying RejSingleton registry for advanced operations."""
        return self._rej_registry
    
    def get_function_timings(self, func_name: str) -> List[Dict[str, Any]]:
        """Get all timing records for a specific function."""
        with self.lock:
            return self.timings.get(func_name, []).copy()
    
    def get_function_stats(self, func_name: str) -> Dict[str, Any]:
        """Get statistical summary for a specific function."""
        timings = self.get_function_timings(func_name)
        return _calculate_timing_stats(timings)
    
    def get_all_functions(self) -> List[str]:
        """Get list of all tracked function names."""
        with self.lock:
            return list(self.timings.keys())
    
    def clear_function(self, func_name: str):
        """Clear timing data for a specific function."""
        with self.lock:
            self.timings.pop(func_name, None)
    
    def clear_all(self):
        """Clear all timing data."""
        with self.lock:
            self.timings.clear()
    
    def print_summary(self):
        """Print summary of all tracked functions."""
        with self.lock:
            if not self.timings:
                print("📊 Timing Registry: No functions tracked")
                return
            
            print("📊 Timing Registry Summary")
            print("=" * 50)
            
            for func_name, timings in self.timings.items():
                stats = _calculate_timing_stats(timings)
                print(f"\n{func_name}:")
                print(f"  Calls: {stats['call_count']}")
                print(f"  Success rate: {stats['success_rate']:.1%}")
                print(f"  Average time: {fmttime(stats['avg_time'])}")
                print(f"  Total time: {fmttime(stats['total_time'])}")


# Global timing registry instance
timing_registry = TimingRegistry()

def time_function(func: Callable = None, *, print_result: bool = True, 
                 format_time: bool = True) -> Callable:
    """
    Decorator to automatically time function execution.
    
    Args:
        func: Function to decorate (when used without arguments)
        print_result (bool): Whether to print timing results
        format_time (bool): Whether to format time using fmttime()
        
    Returns:
        Callable: Decorated function that prints execution time
        
    Example:
        @time_function
        def slow_operation():
            sleep(1.0)
            return "done"
            
        # Or with options:
        @time_function(print_result=True, format_time=True)
        def another_operation():
            pass
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start = now()
            try:
                result = f(*args, **kwargs)
                end = now()
                duration = elapsed(start, end)
                
                if print_result:
                    if format_time:
                        time_str = fmttime(duration)
                    else:
                        time_str = f"{duration:.6f}s"
                    print(f"⏱️  {f.__name__}() took {time_str}")
                
                return result
            except Exception as e:
                end = now()
                duration = elapsed(start, end)
                if print_result:
                    if format_time:
                        time_str = fmttime(duration)
                    else:
                        time_str = f"{duration:.6f}s"
                    print(f"⏱️  {f.__name__}() failed after {time_str}: {e}")
                raise
        return wrapper
    
    # Handle both @time_function and @time_function()
    if func is None:
        return decorator
    else:
        return decorator(func)


def rate_limiter(max_calls_per_second: float, burst_size: int = 1):
    """
    Decorator to limit function call rate using token bucket algorithm.
    
    Args:
        max_calls_per_second (float): Maximum calls allowed per second
        burst_size (int): Maximum burst size (token bucket capacity)
        
    Returns:
        Callable: Decorated function with rate limiting
        
    Example:
        @rate_limiter(max_calls_per_second=2.0, burst_size=5)
        def api_call():
            # Can be called max 2 times per second, with bursts up to 5
            return "API response"
    """
    def decorator(func):
        # Token bucket state
        tokens = burst_size
        last_update = now()
        lock = threading.Lock()
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal tokens, last_update
            
            with lock:
                current_time = now()
                # Add tokens based on elapsed time
                elapsed_time = current_time - last_update
                tokens = min(burst_size, tokens + elapsed_time * max_calls_per_second)
                last_update = current_time
                
                if tokens >= 1:
                    tokens -= 1
                    return func(*args, **kwargs)
                else:
                    # Calculate wait time
                    wait_time = (1 - tokens) / max_calls_per_second
                    print(f"🚦 Rate limit reached for {func.__name__}, waiting {fmttime(wait_time)}")
                    sleep(wait_time)
                    tokens = 0  # Reset tokens after wait
                    return func(*args, **kwargs)
        
        return wrapper
    return decorator


@contextmanager
def timeout_context(seconds: float, error_msg: str = None):
    """
    Context manager to add timeout to code blocks.
    
    Args:
        seconds (float): Timeout in seconds
        error_msg (str): Custom error message (optional)
        
    Yields:
        None
        
    Raises:
        SKTimeError: If timeout is exceeded
        
    Example:
        with timeout_context(5.0, "Database query timed out"):
            result = slow_database_query()
    """
    def timeout_handler(signum, frame):
        msg = error_msg or f"Operation timed out after {seconds} seconds"
        raise SKTimeError(msg)
    
    try:
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))
        yield
    except AttributeError:
        # Windows fallback - basic timeout checking
        start = now()
        yield
        if elapsed(start, now()) > seconds:
            msg = error_msg or f"Operation exceeded timeout of {seconds} seconds"
            raise SKTimeError(msg)
    finally:
        try:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        except AttributeError:
            pass


class RateMonitor:
    """
    Monitor and track operation rates in real-time.
    
    Useful for monitoring throughput of long-running operations.
    
    Example:
        monitor = RateMonitor(window_size=10.0)  # 10 second window
        
        for item in large_dataset:
            process_item(item)
            monitor.tick()
            
            if monitor.operation_count % 100 == 0:
                rate = monitor.get_current_rate()
                print(f"Processing rate: {rate:.1f} items/sec")
    """
    
    def __init__(self, window_size: float = 60.0):
        """
        Initialize rate monitor.
        
        Args:
            window_size (float): Time window for rate calculation in seconds
        """
        self.window_size = window_size
        self.timestamps: List[float] = []
        self.operation_count = 0
        self.start_time = now()
    
    def tick(self):
        """
        Record one operation occurrence.
        
        Call this each time the operation you're monitoring happens.
        """
        current_time = now()
        self.timestamps.append(current_time)
        self.operation_count += 1
        
        # Remove timestamps outside the window
        cutoff_time = current_time - self.window_size
        self.timestamps = [t for t in self.timestamps if t >= cutoff_time]
    
    def get_current_rate(self) -> float:
        """
        Get current operations per second rate.
        
        Returns:
            float: Operations per second in the current window
        """
        if len(self.timestamps) < 2:
            return 0.0
        
        current_time = now()
        cutoff_time = current_time - self.window_size
        
        # Count operations in window
        recent_ops = len([t for t in self.timestamps if t >= cutoff_time])
        
        if recent_ops == 0:
            return 0.0
        
        # Calculate rate
        window_start = max(cutoff_time, self.timestamps[0])
        window_duration = current_time - window_start
        
        if window_duration > 0:
            return recent_ops / window_duration
        return 0.0
    
    def get_average_rate(self) -> float:
        """
        Get average rate since monitoring started.
        
        Returns:
            float: Average operations per second since start
        """
        total_time = elapsed(self.start_time, now())
        if total_time > 0:
            return self.operation_count / total_time
        return 0.0
    
    def reset(self):
        """Reset all monitoring data."""
        self.timestamps.clear()
        self.operation_count = 0
        self.start_time = now()


class TimerPool:
    """
    Manage multiple named timers for complex timing scenarios.
    
    Useful when you need to time different parts of a system independently
    or track multiple concurrent operations.
    
    Example:
        pool = TimerPool()
        
        pool.start('database')
        pool.start('api_calls')
        
        # Do database work
        pool.lap('database', 'connected')
        
        # Do API work  
        pool.stop('api_calls')
        
        # Finish database work
        pool.stop('database')
        
        # Get results
        db_time = pool.get_elapsed('database')
        api_time = pool.get_elapsed('api_calls')
    """
    
    def __init__(self):
        """Initialize an empty timer pool."""
        self.timers: Dict[str, Timer] = {}
        self.lock = threading.Lock()
    
    def start(self, name: str) -> Timer:
        """
        Start a named timer.
        
        Args:
            name (str): Name of the timer
            
        Returns:
            Timer: The timer instance
        """
        with self.lock:
            if name not in self.timers:
                self.timers[name] = Timer()
            self.timers[name].start()
            return self.timers[name]
    
    def stop(self, name: str) -> float:
        """
        Stop a named timer.
        
        Args:
            name (str): Name of the timer
            
        Returns:
            float: Elapsed time
            
        Raises:
            KeyError: If timer doesn't exist
        """
        with self.lock:
            if name not in self.timers:
                raise KeyError(f"Timer '{name}' not found")
            return self.timers[name].stop()
    
    def pause(self, name: str):
        """Pause a named timer."""
        with self.lock:
            if name not in self.timers:
                raise KeyError(f"Timer '{name}' not found")
            self.timers[name].pause()
    
    def resume(self, name: str):
        """Resume a named timer."""
        with self.lock:
            if name not in self.timers:
                raise KeyError(f"Timer '{name}' not found")
            self.timers[name].resume()
    
    def lap(self, name: str, lap_name: str = "") -> LapTime:
        """
        Record a lap time for a named timer.
        
        Args:
            name (str): Name of the timer
            lap_name (str): Optional name for this lap
            
        Returns:
            LapTime: Lap timing information
        """
        with self.lock:
            if name not in self.timers:
                raise KeyError(f"Timer '{name}' not found")
            return self.timers[name].lap(lap_name)
    
    def get_elapsed(self, name: str) -> Optional[float]:
        """
        Get elapsed time for a named timer.
        
        Args:
            name (str): Name of the timer
            
        Returns:
            Optional[float]: Elapsed time or None if timer doesn't exist
        """
        with self.lock:
            if name not in self.timers:
                return None
            if self.timers[name].elapsed_time is not None:
                return self.timers[name].elapsed_time
            elif self.timers[name].is_running:
                return self.timers[name].get_current_time()
            return None
    
    def get_timer(self, name: str) -> Optional[Timer]:
        """
        Get a timer instance by name.
        
        Args:
            name (str): Name of the timer
            
        Returns:
            Optional[Timer]: Timer instance or None if not found
        """
        with self.lock:
            return self.timers.get(name)
    
    def list_timers(self) -> List[str]:
        """
        Get list of all timer names.
        
        Returns:
            List[str]: List of timer names
        """
        with self.lock:
            return list(self.timers.keys())
    
    def clear(self):
        """Remove all timers from the pool."""
        with self.lock:
            self.timers.clear()
    
    def get_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Get timing summary for all timers.
        
        Returns:
            Dict[str, Dict[str, Any]]: Summary of all timers
        """
        with self.lock:
            summary = {}
            for name, timer in self.timers.items():
                summary[name] = {
                    'is_running': timer.is_running,
                    'is_paused': timer.is_paused,
                    'elapsed_time': timer.elapsed_time,
                    'current_time': timer.get_current_time() if timer.is_running else None,
                    'lap_count': len(timer.laps) if hasattr(timer, 'laps') else 0
                }
            return summary


@contextmanager
def rate_monitor_context(operation_name: str = "operations", 
                        window_size: float = 10.0,
                        report_interval: int = 100):
    """
    Context manager for monitoring operation rates.
    
    Args:
        operation_name (str): Name to use in progress reports
        window_size (float): Time window for rate calculation
        report_interval (int): How often to print rate updates
        
    Yields:
        RateMonitor: Rate monitor instance
        
    Example:
        with rate_monitor_context("file processing", report_interval=50) as monitor:
            for file in files:
                process_file(file)
                monitor.tick()  # Prints rate every 50 operations
    """
    monitor = RateMonitor(window_size)
    print(f"🏁 Starting {operation_name} monitoring...")
    
    try:
        yield monitor
    finally:
        final_rate = monitor.get_average_rate()
        total_ops = monitor.operation_count
        total_time = elapsed(monitor.start_time, now())
        
        print(f"✅ {operation_name.capitalize()} completed:")
        print(f"   Total: {total_ops} operations")
        print(f"   Time: {fmttime(total_time)}")
        print(f"   Average rate: {final_rate:.1f} ops/sec")


def profile_function_calls(func: Callable = None, *, 
                          print_stats: bool = True,
                          track_memory: bool = False):
    """
    Decorator to profile function calls with detailed statistics.
    
    Args:
        func: Function to profile
        print_stats (bool): Whether to print statistics
        track_memory (bool): Whether to track memory usage (basic)
        
    Returns:
        Callable: Decorated function with profiling
        
    Example:
        @profile_function_calls
        def complex_operation(data):
            # Function will be profiled automatically
            return process(data)
    """
    def decorator(f):
        call_count = 0
        total_time = 0.0
        min_time = float('inf')
        max_time = 0.0
        times = []
        
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            nonlocal call_count, total_time, min_time, max_time
            
            call_count += 1
            start = now()
            
            try:
                result = f(*args, **kwargs)
                end = now()
                duration = elapsed(start, end)
                
                # Update statistics
                total_time += duration
                min_time = min(min_time, duration)
                max_time = max(max_time, duration)
                times.append(duration)
                
                if print_stats and call_count % 100 == 0:
                    avg_time = total_time / call_count
                    print(f"📊 {f.__name__}() stats after {call_count} calls:")
                    print(f"   Average: {fmttime(avg_time)}")
                    print(f"   Min: {fmttime(min_time)}")
                    print(f"   Max: {fmttime(max_time)}")
                    print(f"   Total: {fmttime(total_time)}")
                
                return result
                
            except Exception as e:
                end = now()
                duration = elapsed(start, end)
                total_time += duration
                
                if print_stats:
                    print(f"❌ {f.__name__}() failed after {fmttime(duration)}: {e}")
                raise
        
        # Add method to get stats
        def get_stats():
            if call_count == 0:
                return None
            
            return {
                'call_count': call_count,
                'total_time': total_time,
                'avg_time': total_time / call_count,
                'min_time': min_time if min_time != float('inf') else 0,
                'max_time': max_time,
                'function_name': f.__name__
            }
        
        wrapper.get_stats = get_stats
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)


class Timer:
    """
    Combined timer class with context manager support and pause/resume functionality.
    
    This class replaces both the old Timer and Stopwatch classes, providing:
    - Automatic timing via context manager
    - Manual start/stop control
    - Pause and resume functionality
    - Current time checking without stopping
    
    Usage as context manager (automatic):
        with Timer() as timer:
            # do some work
            work_part_1()
            
            timer.pause()
            # break time - doesn't count toward elapsed time
            take_break()
            timer.resume()
            
            # more work
            work_part_2()
            
        # Timer automatically stopped, elapsed time available
        print(f"Active work time: {timer.elapsed_time:.3f}s")
    
    Usage manually:
        timer = Timer()
        timer.start()
        # ... work ...
        timer.pause()
        # ... break ...
        timer.resume()
        # ... more work ...
        elapsed = timer.stop()
    """

    def __init__(self):
        """
        Initialize a new Timer.
        
        All timing values start as None/0, timer is not running.
        """
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed_time: Optional[float] = None
        self.paused_time: float = 0.0
        self._pause_start: Optional[float] = None
        self._is_running: bool = False
        self.laps: List[LapTime] = []
        self._last_lap_time: float = 0.0

    def __enter__(self):
        """
        Context manager entry - automatically start the timer.
        
        Returns:
            Timer: Self, so timer methods can be called within context
            
        Example:
            with Timer() as timer:
                # timer.start() already called automatically
                work()
                timer.pause()  # Can use timer methods
        """
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager exit - automatically stop the timer.
        
        Args:
            exc_type: Exception type (if any)
            exc_value: Exception value (if any) 
            traceback: Exception traceback (if any)
            
        This method ensures that elapsed_time is always available after
        the context exits, regardless of the timer's state.
        """
        if self._is_running:
            # If paused, resume briefly to stop cleanly
            was_paused = self._pause_start is not None
            if was_paused:
                self.resume()
            self.stop()
        
    def start(self):
        """
        Start the timer.
        
        This resets all state and begins timing from now.
        Can be called multiple times to restart timing.
        
        Example:
            timer = Timer()
            timer.start()  # Begin timing
            # ... work ...
            timer.start()  # Restart from zero
        """
        self.start_time = now()
        self.end_time = None
        self.elapsed_time = None
        self.paused_time = 0.0
        self._pause_start = None
        self._is_running = True
        self.laps.clear()
        self._last_lap_time = 0.0

    def pause(self):
        """
        Pause the timer.
        
        Time spent paused will not count toward elapsed time.
        Timer must be running and not already paused.
        
        Raises:
            RuntimeError: If timer not started or already paused
            
        Example:
            timer.start()
            work()
            timer.pause()
            break_time()  # This time won't count
            timer.resume()
        """
        if not self._is_running:
            raise RuntimeError("Timer has not been started.")
        if self._pause_start is not None:
            raise RuntimeError("Timer is already paused.")
        self._pause_start = now()

    def resume(self):
        """
        Resume the timer from a paused state.
        
        Adds the pause duration to total paused time and continues timing.
        Timer must be currently paused.
        
        Raises:
            RuntimeError: If timer not paused
            
        Example:
            timer.pause()
            break_time()
            timer.resume()  # Continue timing where we left off
        """
        if self._pause_start is None:
            raise RuntimeError("Timer is not paused.")
        self.paused_time += elapsed(self._pause_start, now())
        self._pause_start = None

    def stop(self) -> float:
        """
        Stop the timer and calculate final elapsed time.
        
        Returns:
            float: Total elapsed time in seconds (excluding paused time)
            
        Raises:
            RuntimeError: If timer not running or currently paused
            
        Example:
            timer.start()
            work()
            duration = timer.stop()  # Returns elapsed time
        """
        if not self._is_running:
            raise RuntimeError("Timer is not running.")
        if self._pause_start is not None:
            raise RuntimeError("Timer is paused. Resume it before stopping.")
        
        self.end_time = now()
        self.elapsed_time = elapsed(self.start_time, self.end_time) - self.paused_time
        self._is_running = False
        return self.elapsed_time
    
    def get_current_time(self) -> float:
        """
        Get the current elapsed time without stopping the timer.
        
        Returns:
            float: Current elapsed time in seconds (excluding paused time)
            
        Raises:
            RuntimeError: If timer not started
            
        This is useful for progress monitoring or intermediate measurements.
        
        Example:
            timer.start()
            for i in range(10):
                process_item(i)
                if i == 5:
                    halfway_time = timer.get_current_time()
                    print(f"Halfway done in {halfway_time:.2f}s")
        """
        if not self._is_running:
            raise RuntimeError("Timer has not been started.")
        
        current_time = now()
        
        if self._pause_start is not None:
            # Currently paused - don't count time since pause started
            return elapsed(self.start_time, self._pause_start) - self.paused_time
        else:
            # Currently running - count all time except previous pauses
            return elapsed(self.start_time, current_time) - self.paused_time

    def lap(self, name: str = "") -> LapTime:
        """
        Record a lap time without stopping the timer.
        
        Args:
            name (str): Optional name/description for this lap
            
        Returns:
            LapTime: Information about this lap
            
        Raises:
            RuntimeError: If timer not running
            
        This is useful for tracking progress through multi-stage operations.
        
        Example:
            timer.start()
            
            setup_data()
            lap1 = timer.lap("data setup")
            
            process_data()
            lap2 = timer.lap("processing")
            
            save_results()
            final_time = timer.stop()
            
            print(f"Setup: {lap1.lap_time:.2f}s")
            print(f"Processing: {lap2.lap_time:.2f}s") 
        """
        if not self._is_running:
            raise RuntimeError("Timer has not been started.")
        
        current_total_time = self.get_current_time()
        lap_time = current_total_time - self._last_lap_time
        lap_number = len(self.laps) + 1
        
        lap = LapTime(
            lap_number=lap_number,
            timestamp=now(),
            lap_time=lap_time,
            total_time=current_total_time,
            name=name
        )
        
        self.laps.append(lap)
        self._last_lap_time = current_total_time
        
        print(f"⏱️  Lap {lap_number}" + (f" ({name})" if name else "") + 
              f": {fmttime(lap_time)} (total: {fmttime(current_total_time)})")
        
        return lap

    def get_laps(self) -> List[LapTime]:
        """
        Get all recorded lap times.
        
        Returns:
            List[LapTime]: All lap times recorded for this timer
        """
        return self.laps.copy()

    def get_lap_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for all laps.
        
        Returns:
            Dict[str, Any]: Summary including fastest/slowest laps, averages, etc.
        """
        if not self.laps:
            return {'lap_count': 0}
        
        lap_times = [lap.lap_time for lap in self.laps]
        
        return {
            'lap_count': len(self.laps),
            'fastest_lap': min(lap_times),
            'slowest_lap': max(lap_times),
            'average_lap': statistics.mean(lap_times),
            'median_lap': statistics.median(lap_times),
            'total_time': self.laps[-1].total_time if self.laps else 0,
            'laps': self.laps
        }

    def reset(self):
        """
        Reset the timer to initial state without starting.
        
        Clears all timing data and stops the timer if running.
        
        Example:
            timer.start()
            work()
            timer.reset()  # Back to initial state
            timer.start()  # Fresh start
        """
        self.start_time = None
        self.end_time = None
        self.elapsed_time = None
        self.paused_time = 0.0
        self._pause_start = None
        self._is_running = False
        self.laps.clear()
        self._last_lap_time = 0.0

    @property
    def is_running(self) -> bool:
        """
        Check if timer is currently running.
        
        Returns:
            bool: True if timer is running (may be paused), False if stopped
        """
        return self._is_running

    @property
    def is_paused(self) -> bool:
        """
        Check if timer is currently paused.
        
        Returns:
            bool: True if timer is paused, False otherwise
        """
        return self._pause_start is not None


def measure_function_time(func: Union[Callable, skfunction.SKFunction], 
                         *args, **kwargs) -> Tuple[float, Any]:
    """
    Measure the execution time of a function.

    Args:
        func: The function to measure (callable or SKFunction)
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Tuple[float, Any]: A tuple containing the elapsed time in seconds 
        and the function's return value

    Raises:
        SKTimeError: If an error occurs during function execution
        
    Example:
        def slow_calculation(n):
            return sum(i*i for i in range(n))
            
        time_taken, result = measure_function_time(slow_calculation, 10000)
        print(f"Calculation took {time_taken:.3f}s, result: {result}")
    """
    with Timer() as timer:
        try:
            if isinstance(func, skfunction.SKFunction):
                result = func.call(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
        except Exception as e:
            raise SKTimeError(f"An error occurred while measuring function time: {e}") from e
    
    return timer.elapsed_time, result


def compare_functions(*funcs, iterations: int = 1000, **shared_kwargs) -> Dict[str, Dict[str, Any]]:
    """
    Compare the performance of multiple functions.
    
    Args:
        *funcs: Functions to compare
        iterations (int): Number of iterations for each function
        **shared_kwargs: Keyword arguments to pass to all functions
        
    Returns:
        Dict[str, Dict[str, Any]]: Benchmark results for each function
        
    Example:
        def method1(data):
            return sorted(data)
            
        def method2(data):
            return list(sorted(data))
            
        results = compare_functions(method1, method2, 
                                  iterations=1000, data=list(range(100)))
        
        for func_name, stats in results.items():
            print(f"{func_name}: {stats['avg_time']:.6f}s avg")
    """
    results = {}
    test_data = list(range(100))  # Default test data
    
    print(f"🏁 Comparing {len(funcs)} functions with {iterations} iterations each...")
    
    for func in funcs:
        func_name = getattr(func, '__name__', str(func))
        print(f"⏱️  Benchmarking {func_name}...")
        
        try:
            # Use test data if no shared_kwargs provided
            kwargs = shared_kwargs if shared_kwargs else {'data': test_data}
            results[func_name] = benchmark(func, iterations=iterations, **kwargs)
        except Exception as e:
            print(f"❌ {func_name} failed: {e}")
            results[func_name] = {'error': str(e)}
    
    # Print comparison summary
    print(f"\n📊 Performance Comparison Results:")
    print("-" * 50)
    
    valid_results = {name: stats for name, stats in results.items() if 'error' not in stats}
    if valid_results:
        # Sort by average time (fastest first)
        sorted_results = sorted(valid_results.items(), key=lambda x: x[1]['avg_time'])
        
        fastest_time = sorted_results[0][1]['avg_time']
        
        for i, (func_name, stats) in enumerate(sorted_results):
            relative_speed = stats['avg_time'] / fastest_time
            print(f"{i+1}. {func_name}: {fmttime(stats['avg_time'])} avg ({relative_speed:.1f}x)")
    
    return results


def timing_context(name: str = "operation", print_start: bool = True, print_end: bool = True):
    """
    Simple context manager for timing code blocks with automatic printing.
    
    Args:
        name (str): Name of the operation being timed
        print_start (bool): Whether to print when starting
        print_end (bool): Whether to print timing results
        
    Example:
        with timing_context("data processing"):
            process_large_dataset()
        # Automatically prints: "Data processing took 2.34s"
    """
    @contextmanager
    def timed_context():
        if print_start:
            print(f"🏁 Starting {name}...")
        
        with Timer() as timer:
            yield timer
        
        if print_end:
            print(f"✅ {name.capitalize()} completed in {fmttime(timer.elapsed_time)}")
    
    return timed_context()


class PerformanceTracker:
    """
    Track performance metrics over time for analysis and optimization.
    
    Useful for monitoring long-running systems or analyzing performance trends.
    
    Example:
        tracker = PerformanceTracker("API requests")
        
        for request in requests:
            with tracker.time_operation() as timing:
                response = handle_request(request)
                timing.add_metadata(status_code=response.status_code)
        
        stats = tracker.get_statistics()
        print(f"Average response time: {stats['avg_time']:.3f}s")
    """
    
    def __init__(self, name: str = "operations"):
        """
        Initialize performance tracker.
        
        Args:
            name (str): Name for this tracker
        """
        self.name = name
        self.timings: List[Dict[str, Any]] = []
        self.start_time = now()
    
    @contextmanager
    def time_operation(self, operation_name: str = None):
        """
        Context manager to time an individual operation.
        
        Args:
            operation_name (str): Optional name for this specific operation
            
        Yields:
            Dict: Timing record that can be modified with metadata
        """
        timing_record = {
            'operation_name': operation_name,
            'start_time': now(),
            'metadata': {}
        }
        
        class TimingContext:
            def add_metadata(self, **kwargs):
                timing_record['metadata'].update(kwargs)
        
        context = TimingContext()
        
        try:
            yield context
        finally:
            timing_record['end_time'] = now()
            timing_record['duration'] = elapsed(timing_record['start_time'], timing_record['end_time'])
            self.timings.append(timing_record)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for all recorded timings.
        
        Returns:
            Dict[str, Any]: Performance statistics
        """
        if not self.timings:
            return {'count': 0}
        
        durations = [t['duration'] for t in self.timings]
        total_time = elapsed(self.start_time, now())
        
        return {
            'count': len(self.timings),
            'total_time': total_time,
            'avg_time': statistics.mean(durations),
            'min_time': min(durations),
            'max_time': max(durations),
            'median_time': statistics.median(durations),
            'std_dev': statistics.stdev(durations) if len(durations) > 1 else 0,
            'throughput': len(self.timings) / total_time if total_time > 0 else 0,
            'name': self.name
        }
    
    def print_summary(self):
        """Print a formatted summary of performance statistics."""
        stats = self.get_statistics()
        
        if stats['count'] == 0:
            print(f"📊 {self.name}: No operations recorded")
            return
        
        print(f"📊 Performance Summary - {self.name}")
        print("-" * 40)
        print(f"Total operations: {stats['count']}")
        print(f"Total time: {fmttime(stats['total_time'])}")
        print(f"Average time: {fmttime(stats['avg_time'])}")
        print(f"Fastest: {fmttime(stats['min_time'])}")
        print(f"Slowest: {fmttime(stats['max_time'])}")
        print(f"Throughput: {stats['throughput']:.1f} ops/sec")
        
        if stats['std_dev'] > 0:
            print(f"Std deviation: {fmttime(stats['std_dev'])}")


# Utility function for quick timing without classes
def quick_time(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Quickly time a single function call.
    
    Args:
        func: Function to time
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Tuple[Any, float]: (result, time_taken)
        
    Example:
        result, duration = quick_time(expensive_function, arg1, arg2)
        print(f"Function returned {result} in {duration:.3f}s")
    """
    start = now()
    result = func(*args, **kwargs)
    end = now()
    return result, elapsed(start, end)
