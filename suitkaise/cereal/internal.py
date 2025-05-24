# suitkaise/cereal/internal.py

# add license here

import cloudpickle
from typing import Any, Dict, Union
from multiprocessing.managers import DictProxy, ListProxy

from suitkaise.cereal.protocols import SerializerProtocol
from suitkaise.cereal.exceptions import SerializationError, DeserializationError
from suitkaise.cereal.skpickle import SKPickle

class InternalSerializer(SerializerProtocol):
    """
    Enhanced internal serializer using SKPickle for multiprocessing support.

    This serializer provides both regular cloudpickle serialization and 
    enhanced multiprocessing capabilities through SKPickle integration.
    
    Use this for internal, cross-process communication within your application.
    """

    @property
    def name(self) -> str:
        return "internal"
    
    def serialize(self, obj: Any) -> bytes:
        """
        Serialize an object using cloudpickle with multiprocessing enhancements.
        
        Args:
            obj: Object to serialize
            
        Returns:
            bytes: Serialized data
            
        Raises:
            SerializationError: If serialization fails
        """
        try:
            return SKPickle.serialize(obj)
        except Exception as e:
            raise SerializationError(f"Internal serialization failed: {e}") from e
        
    def deserialize(self, data: bytes) -> Any:
        """
        Deserialize bytes using cloudpickle.
        
        Args:
            data: Serialized data
            
        Returns:
            Any: Deserialized object
            
        Raises:
            DeserializationError: If deserialization fails
        """
        try:
            return SKPickle.deserialize(data)
        except Exception as e:
            raise DeserializationError(f"Internal deserialization failed: {e}") from e
    
    def is_serializable(self, obj: Any) -> bool:
        """
        Check if an object can be serialized for cross-process use.
        
        Args:
            obj: Object to test
            
        Returns:
            bool: True if serializable, False otherwise
        """
        return SKPickle.test_serialization(obj)
    
    def create_shared_dict(self, initial_data: Dict = None) -> DictProxy:
        """
        Create a shared dictionary for cross-process use.
        
        Args:
            initial_data: Optional initial data
            
        Returns:
            DictProxy: Shared dictionary using enhanced serialization
        """
        return SKPickle.create_shared_dict(initial_data)
    
    def create_shared_list(self, initial_data: list = None) -> ListProxy:
        """
        Create a shared list for cross-process use.
        
        Args:
            initial_data: Optional initial data
            
        Returns:
            ListProxy: Shared list using enhanced serialization  
        """
        return SKPickle.create_shared_list(initial_data)
    
    def get_manager(self):
        """
        Get the underlying SKPickle manager for advanced usage.
        
        Returns:
            CloudPickleManager: The manager instance
        """
        return SKPickle.get_manager()
    
    def enable_enhanced_multiprocessing(self):
        """Enable enhanced multiprocessing globally."""
        SKPickle.enable_cloudpickle_globally()
    
    def disable_enhanced_multiprocessing(self):
        """Disable enhanced multiprocessing globally.""" 
        SKPickle.disable_cloudpickle_globally()
    
    def cleanup(self):
        """Clean up multiprocessing resources."""
        SKPickle.shutdown_manager()