from typing import Any, Dict
from abc import ABC, abstractmethod


class Handler(ABC):
    """
    Base class for handlers that serialize/deserialize specific object types.
    
    Handlers extract state from objects and reconstruct objects from state.
    They do NOT handle recursion or metadata wrapping - the central serializer does that.
    
    Each handler must define:
    - type_name: identifier for this type (e.g., "lock", "logger")
    - can_handle(): whether this handler can process a given object
    - extract_state(): extract object's current state as dict/list of primitives or serializable objects
    - reconstruct(): recreate object from extracted state
    """
    
    # Subclasses must define this
    type_name: str  # e.g., "lock", "logger", "class_instance"
    
    @abstractmethod
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can handle the given object.
        
        Returns:
            bool: True if this handler can serialize/deserialize this object type
        """
        raise NotImplementedError
    
    @abstractmethod
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract the object's current state for serialization.
        
        Return a dict containing only:
        - Primitives (int, str, bool, None, etc.)
        - Collections (list, dict, tuple, set)
        - Other objects (central serializer will recursively serialize them)
        
        Do NOT include metadata like __object_id__ or __handler__ - 
        the central serializer adds that.
        
        Args:
            obj: The object to extract state from
            
        Returns:
            dict: State needed to reconstruct the object
        """
        raise NotImplementedError
    
    @abstractmethod
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct an object from extracted state.
        
        The state dict will have been recursively deserialized by the central
        deserializer, so all nested objects are already reconstructed.
        
        Args:
            state: The deserialized state dict
            
        Returns:
            object: The reconstructed object
        """
        raise NotImplementedError