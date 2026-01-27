"""
Skpath Exceptions

Custom exceptions for path detection and handling operations.
"""


class PathDetectionError(Exception):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.paths import PathDetectionError
        ```
    ────────────────────────────────────────────────────────\n

    Raised when path or project root detection fails.
    
    This exception is raised when:
    - Project root cannot be determined
    - Caller file path cannot be detected
    - A string cannot be interpreted as a valid path or encoded ID
    - Module path lookup fails
    """
    pass


class NotAFileError(IsADirectoryError):
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.paths import NotAFileError
        ```
    ────────────────────────────────────────────────────────\n

    Raised when a file operation is attempted on a directory.
    
    Inherits from IsADirectoryError for compatibility with standard
    exception handling, but provides a more intuitive name.
    """
    pass
