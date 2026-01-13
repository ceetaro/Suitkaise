"""
Platform-specific timeout implementations.

Unix/Linux/macOS: Uses signal.SIGALRM for clean interruption of blocking code.
Windows: Falls back to timer thread (can't interrupt blocking code, but detects timeout).
"""

import platform
import threading
from typing import Callable, TypeVar, Any

from .errors import ProcessTimeoutError

T = TypeVar('T')


def _signal_based_timeout(
    func: Callable[[], T],
    timeout: float | None,
    section: str,
    current_run: int
) -> T:
    """
    Run function with signal-based timeout (Unix only).
    
    Uses SIGALRM to interrupt blocking code when timeout is reached.
    This actually interrupts most blocking operations (syscalls, sleep, etc.).
    """
    if timeout is None:
        return func()
    
    import signal
    
    def handler(signum, frame):
        raise ProcessTimeoutError(section, timeout, current_run)
    
    # Save old handler and set new one
    old_handler = signal.signal(signal.SIGALRM, handler)
    
    # Set alarm (only supports integer seconds, so we round up)
    signal.alarm(int(timeout) + 1 if timeout % 1 else int(timeout))
    
    try:
        return func()
    finally:
        # Cancel alarm and restore old handler
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def _thread_based_timeout(
    func: Callable[[], T],
    timeout: float | None,
    section: str,
    current_run: int
) -> T:
    """
    Run function with thread-based timeout (cross-platform fallback).
    
    Runs function in a thread and waits for completion with timeout.
    Cannot actually interrupt blocking code - the thread continues running
    as a "zombie" but we detect the timeout and raise.
    
    Limitation: If user code has infinite loops or long-blocking calls,
    the timeout fires but the code keeps running in the background.
    The zombie thread dies when the subprocess terminates.
    """
    if timeout is None:
        return func()
    
    result: list[Any] = [None]
    exception: list[BaseException | None] = [None]
    completed = threading.Event()
    
    def wrapper():
        try:
            result[0] = func()
        except BaseException as e:
            exception[0] = e
        finally:
            completed.set()
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    
    # Wait for completion or timeout
    finished = completed.wait(timeout=timeout)
    
    if not finished:
        # Thread is still running - we can't kill it, but we know timeout occurred
        raise ProcessTimeoutError(section, timeout, current_run)
    
    # Thread finished - check for exception
    if exception[0] is not None:
        raise exception[0]
    
    return result[0]


# Select implementation based on platform
if platform.system() != 'Windows':
    run_with_timeout = _signal_based_timeout
else:
    run_with_timeout = _thread_based_timeout


__all__ = ['run_with_timeout']

