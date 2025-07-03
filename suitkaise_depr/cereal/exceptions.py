# add license here

# suitkaise/cereal/exceptions.py

class CerealError(Exception):
    """Base exception for Cereal."""
    pass

class SerializationError(CerealError):
    """Exception raised for serialization errors."""
    pass

class DeserializationError(CerealError):
    """Exception raised for deserialization errors."""
    pass

class UnsupportedTypeError(CerealError):
    """Exception raised for unsupported types."""
    pass

class SerializerNotFoundError(CerealError):
    """Exception raised when a serializer is not found."""
    pass