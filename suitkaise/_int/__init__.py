"""
Internal Suitkaise Operations

This package contains internal implementation details for Suitkaise modules.
These are not part of the public API and should not be imported directly by users.

The internal operations provide the core functionality that powers the user-facing
APIs while maintaining clean separation of concerns.

Structure:
- core/: Core internal operations for each module
- format_ops: Internal formatting operations for FDPrint
- (Future: path_ops, time_ops, process_ops, etc.)

Note: This is an internal package. Use the public APIs instead:
- suitkaise.fdprint for formatting operations
- suitkaise.skpath for path operations (coming soon)
- suitkaise.sktime for timing operations (coming soon)
"""

# This is an internal package - no public exports
__all__ = []

# Internal package metadata
__version__ = "0.1.0"
__description__ = "Internal operations for Suitkaise modules"

# Prevent direct import of internal modules
import warnings

def __getattr__(name):
    """Warn users about importing internal modules."""
    warnings.warn(
        f"Importing from suitkaise._int.{name} is not recommended. "
        f"Use the public APIs from suitkaise.fdprint, suitkaise.skpath, etc. instead.",
        UserWarning,
        stacklevel=2
    )
    # Allow the import to proceed for internal use
    return globals().get(name)