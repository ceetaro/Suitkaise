# add license here

# suitkaise/cereal/skcereal.py
from typing import Any, Dict, Optional, Type, Union

from suitkaise.cereal.protocols import SerializerProtocol
from suitkaise.cereal.exceptions import SerializerNotFoundError
from suitkaise.cereal.internal import InternalSerializer
from suitkaise.cereal.external import ExternalSerializer

class Cereal:
    """
    Serialization and deserialization for Python objects.

    Provides a unified interface for both internal (process to process)
    and external (cross-language) serialization.
    
    """

    def __init__(self):
        self._serializers: Dict[str, SerializerProtocol] = {
            'internal': InternalSerializer(),
            'external': ExternalSerializer()
        }

    def serialize(self, obj: Any, mode: str = 'internal') -> bytes:
        """
        Serialize an object using the specified mode.
        
        Args:
            obj: The object to serialize.
            mode: The serialization mode ('internal' or 'external').
        
        Returns:
            bytes: The serialized object.
        
        Raises:
            SerializerNotFoundError: If the specified mode is not found.

        """
        serializer = self._serializers.get(mode)
        if not serializer:
            raise SerializerNotFoundError(f"Serializer not found for mode: {mode}")
        
        return serializer.serialize(obj)
    
    def deserialize(self, data: bytes, mode: str = 'internal') -> Any:
        """
        Deserialize bytes back to an object using the specified mode.
        
        Args:
            data: The serialized data.
            mode: The serialization mode ('internal' or 'external').
        
        Returns:
            Any: The deserialized object.
        
        Raises:
            SerializerNotFoundError: If the specified mode is not found.

        """
        serializer = self._serializers.get(mode)
        if not serializer:
            raise SerializerNotFoundError(f"Serializer not found for mode: {mode}")
        
        return serializer.deserialize(data)
    
    def register_serializer(self, name: str, serializer: SerializerProtocol) -> None:
        """
        Register a new serializer.
        
        Args:
            name: The name of the serializer.
            serializer: The serializer instance.
        
        """
        self._serializers[name] = serializer

    def serializable(self, obj: Any, mode: str = 'internal') -> bool:
        """
        Check if an object is serializable using the specified mode.
        
        Args:
            obj: The object to check.
            mode: The serialization mode ('internal' or 'external').
        
        Returns:
            bool: True if the object is serializable, False otherwise.
        
        Raises:
            SerializerNotFoundError: If the specified mode is not found.

        """
        serializer = self._serializers.get(mode)
        if not serializer:
            raise SerializerNotFoundError(f"Serializer not found for mode: {mode}")
        
        return serializer._serializable(obj)



def serializable(obj: Any) -> bool:
    """
    Check if an object/value is serializable.
    
    This checks both internal and external serialization modes.

    If you want to check if an object is serializable in a specific mode,
    use: 
    
    ```python
    Cereal().serializable(obj, mode='internal' or 'external').
    
    """
    c1 = Cereal().serializable(obj, mode='internal')
    c2 = Cereal().serializable(obj, mode='external')
    return c1 and c2
    
if __name__ == "__main__":
    # Example usage
    my_obj = {"key": "value"}
    is_serializable = serializable(my_obj)
    print(f"Is the object serializable? {is_serializable}")

    class MyClass:
        def __init__(self, value: str):
            self.value = value

    obj2 = MyClass("Hello")
    is_serializable2 = serializable(obj2)
    print(f"Is the object serializable? {is_serializable2}")
    
    print("Internal serialization:")
    print(f"Is obj 2 serializable? {Cereal().serializable(obj2, mode='internal')}")

