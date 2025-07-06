"""
Xprocess Internal Cross-processing Engine - Exception Classes

This module contains all custom exception classes for the multiprocessing system.
These exceptions provide detailed information about errors in different lifecycle
phases to make debugging easier.
"""


class XProcessError(Exception):
    """Base exception for XProcess-related errors."""
    pass


class PreloopError(XProcessError):
    """
    Raised when an error occurs during __preloop__() execution.
    
    This error specifically identifies problems in the setup phase
    of each loop iteration, making debugging easier.
    """
    def __init__(self, original_error: Exception, process_name: str, loop_number: int):
        self.original_error = original_error
        self.process_name = process_name
        self.loop_number = loop_number
        super().__init__(
            f"Error in __preloop__() for process '{process_name}' loop {loop_number}: {original_error}"
        )


class MainLoopError(XProcessError):
    """
    Raised when an error occurs during __loop__() execution.
    
    This error specifically identifies problems in the main work phase
    of each loop iteration, making debugging easier.
    """
    def __init__(self, original_error: Exception, process_name: str, loop_number: int):
        self.original_error = original_error
        self.process_name = process_name
        self.loop_number = loop_number
        super().__init__(
            f"Error in __loop__() for process '{process_name}' loop {loop_number}: {original_error}"
        )


class PostLoopError(XProcessError):
    """
    Raised when an error occurs during __postloop__() execution.
    
    This error specifically identifies problems in the cleanup phase
    of each loop iteration, making debugging easier.
    """
    def __init__(self, original_error: Exception, process_name: str, loop_number: int):
        self.original_error = original_error
        self.process_name = process_name
        self.loop_number = loop_number
        super().__init__(
            f"Error in __postloop__() for process '{process_name}' loop {loop_number}: {original_error}"
        )


class PreloopTimeoutError(PreloopError):
    """Raised when __preloop__() exceeds its configured timeout."""
    def __init__(self, timeout_duration: float, process_name: str, loop_number: int):
        self.timeout_duration = timeout_duration
        self.process_name = process_name
        self.loop_number = loop_number
        Exception.__init__(self, 
            f"__preloop__() timeout ({timeout_duration}s) for process '{process_name}' loop {loop_number}"
        )


class MainLoopTimeoutError(MainLoopError):
    """Raised when __loop__() exceeds its configured timeout."""
    def __init__(self, timeout_duration: float, process_name: str, loop_number: int):
        self.timeout_duration = timeout_duration
        self.process_name = process_name
        self.loop_number = loop_number
        Exception.__init__(self, 
            f"__loop__() timeout ({timeout_duration}s) for process '{process_name}' loop {loop_number}"
        )


class PostLoopTimeoutError(PostLoopError):
    """Raised when __postloop__() exceeds its configured timeout."""
    def __init__(self, timeout_duration: float, process_name: str, loop_number: int):
        self.timeout_duration = timeout_duration
        self.process_name = process_name
        self.loop_number = loop_number
        Exception.__init__(self, 
            f"__postloop__() timeout ({timeout_duration}s) for process '{process_name}' loop {loop_number}"
        )