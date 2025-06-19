# suitkaise/cereal/cereal.py

# add license here

from typing import Any, Dict, Optional, Type, Union
from multiprocessing.managers import DictProxy, ListProxy

from suitkaise.cereal.protocols import SerializerProtocol
from suitkaise.cereal.exceptions import SerializerNotFoundError
from suitkaise.cereal.internal import InternalSerializer
from suitkaise.cereal.external import ExternalSerializer

class Cereal:
    """
    Enhanced serialization and deserialization for Python objects.

    Provides a unified interface for internal (cross-process with multiprocessing support),
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
    
    def serializable(self, obj: Any, mode: str = 'internal') -> bool:
        """
        Check if an object is serializable in the specified mode.
        
        Args:
            obj: Object to test
            mode: Serialization mode to test against
            
        Returns:
            bool: True if serializable, False otherwise
        """
        serializer = self._serializers.get(mode)
        if not serializer:
            return False
            
        # Use enhanced serialization check if available
        if hasattr(serializer, 'is_serializable'):
            return serializer.is_serializable(obj)
        
        # Fallback to basic test
        try:
            serializer.serialize(obj)
            return True
        except Exception:
            return False
    
    def create_shared_dict(self, initial_data: Optional[Dict] = None) -> DictProxy:
        """
        Create a shared dictionary for cross-process communication.
        
        Args:
            initial_data: Optional initial data for the dictionary
            
        Returns:
            DictProxy: Shared dictionary with enhanced serialization
        """
        internal_serializer = self._serializers['internal']
        if hasattr(internal_serializer, 'create_shared_dict'):
            return internal_serializer.create_shared_dict(initial_data)
        else:
            raise NotImplementedError("Shared dict creation not supported by current internal serializer")
    
    def create_shared_list(self, initial_data: Optional[list] = None) -> ListProxy:
        """
        Create a shared list for cross-process communication.
        
        Args:
            initial_data: Optional initial data for the list
            
        Returns:
            ListProxy: Shared list with enhanced serialization
        """
        internal_serializer = self._serializers['internal']
        if hasattr(internal_serializer, 'create_shared_list'):
            return internal_serializer.create_shared_list(initial_data)
        else:
            raise NotImplementedError("Shared list creation not supported by current internal serializer")
    
    def get_internal_manager(self):
        """
        Get the internal serializer's manager for advanced multiprocessing.
        
        Returns:
            Manager instance for advanced usage
        """
        internal_serializer = self._serializers['internal']
        if hasattr(internal_serializer, 'get_manager'):
            return internal_serializer.get_manager()
        else:
            raise NotImplementedError("Manager access not supported by current internal serializer")
    
    def enable_enhanced_multiprocessing(self):
        """Enable enhanced multiprocessing globally."""
        internal_serializer = self._serializers['internal']
        if hasattr(internal_serializer, 'enable_enhanced_multiprocessing'):
            internal_serializer.enable_enhanced_multiprocessing()
    
    def disable_enhanced_multiprocessing(self):
        """Disable enhanced multiprocessing globally."""
        internal_serializer = self._serializers['internal']
        if hasattr(internal_serializer, 'disable_enhanced_multiprocessing'):
            internal_serializer.disable_enhanced_multiprocessing()
    
    def cleanup(self):
        """Clean up serialization resources."""
        internal_serializer = self._serializers['internal']
        if hasattr(internal_serializer, 'cleanup'):
            internal_serializer.cleanup()
    
    def register_serializer(self, name: str, serializer: SerializerProtocol) -> None:
        """
        Register a new serializer.
        
        Args:
            name: The name of the serializer.
            serializer: The serializer instance.
        """
        self._serializers[name] = serializer

