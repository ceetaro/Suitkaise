"""
Non-Serializable Object Handlers

This package contains specialized handlers for objects that cannot be serialized
by standard pickle. Each handler implements the _NSO_Handler interface and
provides custom serialization/deserialization logic for specific object types.

Available NSO handlers:
- locks: Threading and multiprocessing synchronization primitives
- sk_objects: Suitkaise-specific objects (SKPath, Timer, etc.)
- functions: Lambda functions and complex function objects (coming soon)
- file_handles: File objects and I/O streams (coming soon)
- generators: Generator objects and iterator state (coming soon)

Handlers are automatically discovered and registered by the cerial_core registry
system, providing transparent enhanced serialization for complex objects while
maintaining compatibility with standard pickle for simple types.

Warning: This is an internal package. The APIs here may change without notice.
Use the cerial_core public APIs instead.
"""

# Internal package - no public exports
__all__ = []

# Internal NSO handlers metadata
__version__ = "0.1.0"
__description__ = "Non-serializable object handlers for enhanced cross-process serialization"