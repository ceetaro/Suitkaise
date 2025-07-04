"""
Internal Serialization Operations

This package contains the internal serialization implementation for Suitkaise.
It provides the cross-process communication engine that powers XProcess and
global state management systems.

Available internal operations:
- cerial_core: Core serialization engine with enhanced NSO handling
- nso/: Non-serializable object handlers for complex types
- mp_integration: Multiprocessing Manager integration (coming soon)
- recovery: Error recovery and fallback systems (coming soon)

The serialization system provides transparent enhanced serialization for objects
that standard pickle cannot handle, while maintaining full compatibility and
graceful fallback behavior.

Warning: This is an internal package. The APIs here may change without notice.
Use the public APIs instead.
"""

# Internal package - no public exports
__all__ = []

# Internal serialization metadata
__version__ = "0.1.0"
__description__ = "Internal serialization operations for Suitkaise cross-process communication"