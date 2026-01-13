"""
Errors for processing lifecycle hooks.

All errors inherit from ProcessError, allowing users to catch any
Process-related error with a single `except ProcessError`.

These errors wrap the original exception using Python's exception chaining.
The original error and traceback are preserved in __cause__ AND in the
`original_error` attribute (for serialization across processes).

Usage in engine:
    try:
        self.__prerun__()
    except Exception as e:
        raise PreRunError(current_run, e) from e

Output when raised:
    Traceback (most recent call last):
      File "user_code.py", line 12, in __prerun__
        raise ValueError("bad data")
    ValueError: bad data

    The above exception was the direct cause of the following exception:

    Traceback (most recent call last):
      File "engine.py", line 48, in run_section
        raise PreRunError(current_run, e) from e
    PreRunError: Error in __prerun__ on run 3

Accessing the original error:
    error.__cause__              # the original exception (local only)
    error.original_error         # the original exception (survives serialization)
"""


class ProcessError(Exception):
    """
    Base class for all Process-related errors.
    
    Catch this to handle any error from a Process lifecycle method.
    
    Usage:
        try:
            result = process.result
        except ProcessError as e:
            print(f"Process failed: {e}")
    """
    
    def __init__(self, message: str, current_run: int = 0, original_error: BaseException | None = None):
        self.current_run = current_run
        self.original_error = original_error
        super().__init__(message)


class PreRunError(ProcessError):
    """Error raised when __prerun__() fails."""
    
    def __init__(self, current_run: int, original_error: BaseException | None = None):
        super().__init__(
            f"Error in __prerun__ on run {current_run}",
            current_run,
            original_error
        )


class RunError(ProcessError):
    """Error raised when __run__() fails."""
    
    def __init__(self, current_run: int, original_error: BaseException | None = None):
        super().__init__(
            f"Error in __run__ on run {current_run}",
            current_run,
            original_error
        )


class PostRunError(ProcessError):
    """Error raised when __postrun__() fails."""
    
    def __init__(self, current_run: int, original_error: BaseException | None = None):
        super().__init__(
            f"Error in __postrun__ on run {current_run}",
            current_run,
            original_error
        )


class OnFinishError(ProcessError):
    """Error raised when __onfinish__() fails."""
    
    def __init__(self, current_run: int, original_error: BaseException | None = None):
        super().__init__(
            f"Error in __onfinish__ on run {current_run}",
            current_run,
            original_error
        )


class ResultError(ProcessError):
    """Error raised when __result__() fails."""
    
    def __init__(self, current_run: int, original_error: BaseException | None = None):
        super().__init__(
            f"Error in __result__ on run {current_run}",
            current_run,
            original_error
        )


class ErrorHandlerError(ProcessError):
    """Error raised when __error__() fails."""
    
    def __init__(self, current_run: int, original_error: BaseException | None = None):
        super().__init__(
            f"Error in __error__ on run {current_run}",
            current_run,
            original_error
        )


class ProcessTimeoutError(ProcessError):
    """Error raised when a lifecycle section times out."""
    
    def __init__(self, section: str, timeout: float, current_run: int):
        self.section = section
        self.timeout = timeout
        super().__init__(
            f"Timeout in {section} after {timeout}s on run {current_run}",
            current_run,
            None
        )
