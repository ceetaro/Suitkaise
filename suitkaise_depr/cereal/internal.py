# suitkaise/cereal/internal.py

# add license here

import cloudpickle
from typing import Any, Dict
from multiprocessing.managers import DictProxy, ListProxy

from suitkaise_depr.cereal.protocols import SerializerProtocol
from suitkaise_depr.cereal.exceptions import SerializationError, DeserializationError
from suitkaise_depr.cereal.skpickle import SKPickle

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
    
    @property
    def mode(self) -> str:
        return "internal"
    
    def serialize(self, obj: Any) -> bytes:
        """Serialize an object using cloudpickle with enhanced capabilities."""
        try:
            return SKPickle.serialize(obj)
        except Exception as e:
            raise SerializationError(f"Internal serialization failed: {e}") from e
        
    def deserialize(self, data: bytes) -> Any:
        """Deserialize bytes back to an object using cloudpickle with enhanced capabilities."""
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
    
    def create_shared_dict(self, initial_data: Dict = None) -> DictProxy | Dict:
        """
        Create a shared dictionary for cross-process use, with fallback to regular dict.
        
        Args:
            initial_data: Optional initial data
            
        Returns:
            DictProxy or Dict: Shared dictionary using enhanced serialization, 
                               or regular dict if multiprocessing is not available

        """
        try:
            return SKPickle.create_shared_dict(initial_data)
        except Exception as e:
            # Log the multiprocessing failure but continue with fallback
            print(f"Warning: Multiprocessing not available, using regular dict: {e}")
            if initial_data:
                return dict(initial_data)
            return dict()
    
    def create_shared_list(self, initial_data: list = None) -> ListProxy | list:
        """
        Create a shared list for cross-process use, with fallback to regular list.
        
        Args:
            initial_data: Optional initial data
            
        Returns:
            ListProxy or list: Shared list using enhanced serialization, 
                               or regular list if multiprocessing is not available

        """
        try:
            return SKPickle.create_shared_list(initial_data)
        except Exception as e:
            # Log the multiprocessing failure but continue with fallback
            print(f"Warning: Multiprocessing not available, using regular list: {e}")
            if initial_data:
                return list(initial_data)
            return list()
    
    def get_manager(self):
        """
        Get the underlying SKPickle manager for advanced usage.
        
        Returns:
            CloudPickleManager: The manager instance
            
        Raises:
            RuntimeError: If manager is not available
        """
        if not SKPickle.manager_is_available():
            raise RuntimeError("CloudPickle manager is not available. "
                             "Multiprocessing may not be supported in this environment.")
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

    def multiprocessing_is_available(self) -> bool:
        """
        Check if multiprocessing is available.
        
        Returns:
            bool: True if multiprocessing is available, False if using fallback mode
        """
        return SKPickle.manager_is_available() and not SKPickle.in_fallback_mode()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the internal serializer.
        
        Returns:
            Dict[str, Any]: Status information including multiprocessing availability
        """
        return {
            "name": self.name,
            "mode": self.mode,
            "multiprocessing_available": self.multiprocessing_is_available(),
            "manager_available": SKPickle.manager_is_available(),
            "fallback_mode": SKPickle.in_fallback_mode()
        }
    

    