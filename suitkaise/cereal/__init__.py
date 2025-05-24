# add license here

# suitkaise/cereal/__init__.py
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