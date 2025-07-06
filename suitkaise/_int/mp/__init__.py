"""
Internal Cross-processing Engine

This package contains the internal multiprocessing implementation for Suitkaise.
It provides the cross-process execution engine that powers process management,
worker pools, and distributed task execution systems.

Available internal operations:
- base_multiprocessing: Core engine with all components
- managers: CrossProcessing and SubProcessing managers  
- pool: ProcessPool for batch task execution
- processes: _Process base class and lifecycle management
- runner: _ProcessRunner for subprocess execution
- configs: _PConfig and _QPConfig configuration classes
- pdata: _PData standardized process data containers
- stats: ProcessStats for performance monitoring
- exceptions: Custom error classes for detailed debugging

The multiprocessing system provides declarative process lifecycle management
with enhanced error handling, automatic restart capabilities, and comprehensive
monitoring while maintaining clean separation between user code and process
management infrastructure.

Warning: This is an internal package. The APIs here may change without notice.
Use the public APIs instead.
"""

# Internal package - no public exports
__all__ = []

# Internal multiprocessing metadata
__version__ = "0.1.0"
__description__ = "Internal cross-processing engine for Suitkaise multiprocessing systems"
__engine__ = "Suitkaise internal cross-processing engine"