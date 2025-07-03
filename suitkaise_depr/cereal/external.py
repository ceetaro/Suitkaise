# add license here

# suitkaise/cereal/external.py
import json
from typing import Any, Dict

from suitkaise_depr.cereal.protocols import SerializerProtocol
from suitkaise_depr.cereal.exceptions import (
    SerializationError, DeserializationError, UnsupportedTypeError)

class ExternalSerializer(SerializerProtocol):
    """
    Handle external serialization for cross-language communication,
    and other external systems.

    This is a placeholder using JSON.
    Will be replaced with Protocol Buffers later.
    
    """

    @property
    def name(self) -> str:
        return "external"
    
    @property
    def mode(self) -> str:
        return "external"
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object to bytes for external use."""
        valid_types = (dict, list, str, int, float, bool, type(None))
        try:
            if isinstance(obj, valid_types):
                return json.dumps(obj).encode('utf-8')
            else:
                raise UnsupportedTypeError(f"Unsupported type: {type(obj)}")
        except Exception as e:
            raise SerializationError(f"Serialization failed: {e}") from e
        
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes back to an object."""
        try:
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            raise DeserializationError(f"Deserialization failed: {e}") from e
        
    def is_serializable(self, obj: Any) -> bool:
        """Check if the object is serializable."""
        valid_types = (dict, list, str, int, float, bool, type(None))
        return isinstance(obj, valid_types)

