# add license here

# suitkaise/cereal/__init__.py
from suitkaise.cereal.cereal import Cereal
from suitkaise.cereal.exceptions import (
    CerealError,
    SerializationError,
    DeserializationError,
    UnsupportedTypeError,
    SerializerNotFoundError,
)

# default serializer instance
default_serializer = Cereal()

# expose main functions
serialize = default_serializer.serialize
deserialize = default_serializer.deserialize
serializable = default_serializer.serializable

__all__ = [
    'Cereal',
    'serialize',
    'deserialize',
    'serializable',
    'CerealError',
    'SerializationError',
    'DeserializationError',
    'UnsupportedTypeError',
]