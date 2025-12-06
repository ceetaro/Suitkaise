"""
Errors for processing lifecycle hooks.

These errors wrap the original exception using Python's exception chaining.
The original error and traceback are preserved in __cause__ AND in the
`original_error` attribute (for serialization across processes).

Usage in engine:
    try:
        self.__preloop__()
    except Exception as e:
        raise PreloopError(current_lap, e) from e

Output when raised:
    Traceback (most recent call last):
      File "user_code.py", line 12, in __preloop__
        raise ValueError("bad data")
    ValueError: bad data

    The above exception was the direct cause of the following exception:

    Traceback (most recent call last):
      File "engine.py", line 48, in run_section
        raise PreloopError(current_lap, e) from e
    PreloopError: Error in __preloop__ on lap 3

Accessing the original error:
    error.__cause__              # the original exception (local only)
    error.original_error         # the original exception (survives serialization)
"""


class PreloopError(Exception):
    """Error raised when __preloop__() fails."""
    
    def __init__(self, current_lap: int, original_error: BaseException | None = None):
        self.current_lap = current_lap
        self.original_error = original_error
        super().__init__(f"Error in __preloop__ on lap {current_lap}")


class MainLoopError(Exception):
    """Error raised when __loop__() fails."""
    
    def __init__(self, current_lap: int, original_error: BaseException | None = None):
        self.current_lap = current_lap
        self.original_error = original_error
        super().__init__(f"Error in __loop__ on lap {current_lap}")


class PostLoopError(Exception):
    """Error raised when __postloop__() fails."""
    
    def __init__(self, current_lap: int, original_error: BaseException | None = None):
        self.current_lap = current_lap
        self.original_error = original_error
        super().__init__(f"Error in __postloop__ on lap {current_lap}")


class OnFinishError(Exception):
    """Error raised when __onfinish__() fails."""
    
    def __init__(self, current_lap: int, original_error: BaseException | None = None):
        self.current_lap = current_lap
        self.original_error = original_error
        super().__init__(f"Error in __onfinish__ on lap {current_lap}")


class ResultError(Exception):
    """Error raised when __result__() fails."""
    
    def __init__(self, current_lap: int, original_error: BaseException | None = None):
        self.current_lap = current_lap
        self.original_error = original_error
        super().__init__(f"Error in __result__ on lap {current_lap}")


class TimeoutError(Exception):
    """Error raised when a lifecycle section times out."""
    
    def __init__(self, section: str, timeout: float, current_lap: int):
        self.section = section
        self.timeout = timeout
        self.current_lap = current_lap
        super().__init__(f"Timeout in {section} after {timeout}s on lap {current_lap}")
