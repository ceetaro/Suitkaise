# add license here

# suitkaise/cereal/internal.py
import cloudpickle
from typing import Any

from suitkaise.cereal.protocols import SerializerProtocol
from suitkaise.cereal.exceptions import SerializationError, DeserializationError

class InternalSerializer(SerializerProtocol):
    """
    Handles internal serialization using cloudpickle.

    This serializer is meant for internal, cross-process communication within
    an application or program.

    """

    @property
    def name(self) -> str:
        return "internal"
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object using cloudpickle."""
        try:
            return cloudpickle.dumps(obj)
        except Exception as e:
            raise SerializationError(f"Serialization failed: {e}")
        
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes using cloudpickle."""
        try:
            return cloudpickle.loads(data)
        except Exception as e:
            raise DeserializationError(f"Deserialization failed: {e}")

    