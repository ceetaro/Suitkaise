# add license here

# suitkaise/sktime/sktime.py

"""
Time utilities for Suitkaise.

"""
import time

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
    
def main():
    print(now())

if __name__ == '__main__':
    main()