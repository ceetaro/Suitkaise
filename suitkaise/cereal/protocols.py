# add license here

# suitkaise/cereal/protocols.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union, Type

class SerializerProtocol(ABC):
    """Protocol for backend serializers."""

    @abstractmethod
    def serialize(self, obj: Any) -> bytes:
        """
        Serialize an object to bytes.
        
        Custom serializers can use this method to convert unserializable or
        complex objects into a serializable format before serialization.
        
        """
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes back to an object."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the serializer."""
        pass