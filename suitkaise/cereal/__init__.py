# add license here

# suitkaise/cereal/__init__.py
from typing import Any
from suitkaise.cereal.cereal import Cereal
from suitkaise.cereal.skpickle import SKPickle
from suitkaise.cereal.exceptions import (
    CerealError,
    SerializationError,
    DeserializationError,
    UnsupportedTypeError,
    SerializerNotFoundError,
)

# Enhanced default serializer instance with multiprocessing support
default_serializer = Cereal()

def serializable(obj: Any, mode: str = 'internal') -> bool:
    """Check if an object is serializable in the specified mode."""
    return default_serializer.serializable(obj, mode)

def serializable_both(obj: Any) -> bool:
    """Check if object is serializable in both modes."""
    return (default_serializer.serializable(obj, 'internal') and 
            default_serializer.serializable(obj, 'external'))

# Expose main functions with enhanced capabilities
serialize = default_serializer.serialize
deserialize = default_serializer.deserialize
serializable = default_serializer.serializable
create_shared_dict = default_serializer.create_shared_dict
create_shared_list = default_serializer.create_shared_list

__all__ = [
    'Cereal',
    'serialize',
    'deserialize', 
    'serializable',
    'create_shared_dict',
    'create_shared_list',
    'SKPickle',
    'CerealError',
    'SerializationError', 
    'DeserializationError',
    'UnsupportedTypeError',
    'SerializerNotFoundError',
]