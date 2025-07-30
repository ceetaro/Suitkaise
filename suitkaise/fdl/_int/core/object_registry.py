"""
Internal Object Processor Registry for FDL.

This module provides a registration system for object processors,
allowing new object types to be added without modifying core code.

This is internal to the FDL engine and not exposed to users.
"""

import threading
from typing import Dict, Set, Type, Optional, Union
from abc import ABC, abstractmethod
from .format_state import _FormatState


class UnsupportedObjectError(Exception):
    """Raised when object type is not supported."""
    pass


class _ObjectProcessor(ABC):
    """
    Abstract base class for object processors.
    
    All object processors must inherit from this and implement
    the required methods for registration and processing.
    """
    
    @classmethod
    @abstractmethod
    def get_supported_object_types(cls) -> Set[str]:
        """
        Get set of object types this processor supports.

        Ex: 'time', 'datelong', 'type', 'spinner'
        
        Returns:
            Set[str]: Set of supported object type names
        """
        pass
    
    @classmethod
    @abstractmethod
    def process_object(cls, obj_type: str, variable: Optional[str], 
                      format_state: _FormatState) -> str:
        """
        Process an object and return formatted result.
        
        Args:
            obj_type: Type of object to process
            variable: Variable name for value substitution
            format_state: Current format state (for settings and values)
            
        Returns:
            str: Formatted object result
        """
        pass
    
    @classmethod
    def validate_object_type(cls, obj_type: str) -> bool:
        """
        Validate that this processor supports the object type.
        
        Args:
            obj_type: Object type to validate
            
        Returns:
            bool: True if supported
        """
        return obj_type in cls.get_supported_object_types()


class _ObjectRegistry:
    """
    Registry for object processors with automatic type mapping.
    
    This class manages all object processors and routes object processing
    to the appropriate processor based on object type.
    """
    
    _type_to_processor: Dict[str, Type[_ObjectProcessor]] = {}
    _lock = threading.RLock()  # Thread-safe access to registry
    
    
    @classmethod
    def register(cls, processor_class: Type[_ObjectProcessor]) -> None:
        """
        Register an object processor for all its supported types.
        
        Args:
            processor_class: Object processor class to register
            
        Raises:
            TypeError: If processor doesn't inherit from _ObjectProcessor
            ValueError: If processor supports types already registered
        """
        with cls._lock:
            if not issubclass(processor_class, _ObjectProcessor):
                raise TypeError(f"Processor must inherit from _ObjectProcessor: {processor_class}")
            
            supported_types = processor_class.get_supported_object_types()
            
            # Check for conflicts
            conflicts = supported_types & set(cls._type_to_processor.keys())
            if conflicts:
                existing_processors = {obj_type: cls._type_to_processor[obj_type].__name__ 
                                    for obj_type in conflicts}
                raise ValueError(f"Object types already registered: {existing_processors}")
            
            # Register all supported types
            for obj_type in supported_types:
                cls._type_to_processor[obj_type] = processor_class

    @classmethod
    def is_registered(cls, processor_class: Type[_ObjectProcessor]) -> bool:
        """
        Check if an object processor is registered.
        
        Args:
            processor_class: Object processor class to check
            
        Returns:
            bool: True if the processor is registered
        """
        with cls._lock:
            return any(issubclass(proc, processor_class) for proc in cls._type_to_processor.values())
    
    @classmethod
    def unregister(cls, processor_class: Union[Type[_ObjectProcessor], str]) -> None:
        """
        Unregister an object processor.
        
        Args:
            processor_class: Object processor class to unregister
        """
        with cls._lock:
            if not isinstance(processor_class, str):
                processor_class = processor_class.__name__

            # Remove all types handled by this processor
            types_to_remove = []
            for obj_type, processor in cls._type_to_processor.items():
                if processor == processor_class:
                    types_to_remove.append(obj_type)
            
            for obj_type in types_to_remove:
                del cls._type_to_processor[obj_type]
    
    @classmethod
    def is_supported_type(cls, obj_type: str) -> bool:
        """
        Check if object type is supported by any registered processor.
        
        Args:
            obj_type: Object type to check
            
        Returns:
            bool: True if object type is supported
        """
        return obj_type in cls._type_to_processor
    
    @classmethod
    def process_object(cls, obj_type: str, variable: Optional[str], 
                      format_state: _FormatState) -> str:
        """
        Process an object by routing to the appropriate processor.
        
        Args:
            obj_type: Type of object to process
            variable: Variable name for value substitution
            format_state: Current format state
            
        Returns:
            str: Formatted object result
            
        Raises:
            _UnsupportedObjectError: If object type is not supported
        """
        if obj_type not in cls._type_to_processor:
            raise UnsupportedObjectError(f"Unsupported object type: '{obj_type}'")
        
        processor_class = cls._type_to_processor[obj_type]
        return processor_class.process_object(obj_type, variable, format_state)
    
    @classmethod
    def get_supported_types(cls) -> Set[str]:
        """
        Get set of all supported object types.
        
        Returns:
            Set[str]: Set of all supported object type names
        """
        return set(cls._type_to_processor.keys())
    
    @classmethod
    def get_registered_processors(cls) -> Dict[str, Type[_ObjectProcessor]]:
        """
        Get mapping of object types to their processors.
        
        Returns:
            Dict[str, Type[_ObjectProcessor]]: Type to processor mapping
        """
        return cls._type_to_processor.copy()
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered processors (useful for testing)."""
        with cls._lock:
            cls._type_to_processor.clear()
    
    @classmethod
    def get_processor_for_type(cls, obj_type: str) -> Optional[Type[_ObjectProcessor]]:
        """
        Get the processor class that handles a specific object type.
        
        Args:
            obj_type: Object type to look up
            
        Returns:
            Optional[Type[_ObjectProcessor]]: Processor class or None if not found
        """
        return cls._type_to_processor.get(obj_type)
    
    @classmethod
    def get_object_info(cls, obj_type: str) -> dict:
        """
        Get information about an object type.
        
        Args:
            obj_type: Object type to check
            
        Returns:
            dict: Information about the object type
        """
        processor = cls._type_to_processor.get(obj_type)
        
        if processor:
            return {
                'processor': processor.__name__,
                'supported_types': list(processor.get_supported_object_types()),
                'is_supported': True
            }
        else:
            return {
                'processor': None,
                'supported_types': [],
                'is_supported': False
            }
    
    @classmethod
    def get_registry_info(cls) -> dict:
        """
        Get information about the entire registry.
        
        Returns:
            dict: Information about all registered processors and types
        """
        return {
            'total_processors': len(set(cls._type_to_processor.values())),
            'total_types': len(cls._type_to_processor),
            'supported_types': list(cls._type_to_processor.keys()),
            'processors': {name: proc.__name__ for name, proc in cls._type_to_processor.items()}
        }


def _register_object_processor(processor_class: Type[_ObjectProcessor]) -> None:
    """
    Convenience function to register an object processor.
    
    Args:
        processor_class: Object processor class to register
    """
    _ObjectRegistry.register(processor_class)


def _process_object(obj_type: str, variable: Optional[str], format_state: _FormatState) -> str:
    """
    Convenience function to process an object.
    
    Args:
        obj_type: Type of object to process
        variable: Variable name for value substitution
        format_state: Current format state
        
    Returns:
        str: Formatted object result
    """
    return _ObjectRegistry.process_object(obj_type, variable, format_state)


def _is_supported_object_type(obj_type: str) -> bool:
    """
    Convenience function to check if object type is supported.
    
    Args:
        obj_type: Object type to check
        
    Returns:
        bool: True if supported
    """
    return _ObjectRegistry.is_supported_type(obj_type)


# Registry decorator for easy registration
def _object_processor(processor_class: Type[_ObjectProcessor]):
    """
    Decorator to automatically register object processors.
    
    Usage:
        @_object_processor
        class _MyObjectProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_types(cls):
                return {'my_type'}
            
            @classmethod
            def process_object(cls, obj_type, variable, format_state):
                return "formatted result"
    """
    _ObjectRegistry.register(processor_class)
    return processor_class


def _parse_object_content(object_content: str) -> tuple[str, Optional[str]]:
    """
    Parse object content into type and variable.
    
    Args:
        object_content: Content without brackets (e.g., "time:timestamp")
        
    Returns:
        tuple: (obj_type, variable) where variable can be None
        
    Raises:
        ValueError: If object content format is invalid
    """
    if ':' not in object_content:
        raise ValueError(f"Invalid object format: '{object_content}' (missing ':')")
    
    obj_type, obj_var = object_content.split(':', 1)
    obj_type = obj_type.strip()
    obj_var = obj_var.strip()
    
    if not obj_type:
        raise ValueError(f"Invalid object format: '{object_content}' (empty object type)")
    
    # Variable can be empty (means current/default value)
    variable = obj_var if obj_var else None
    
    return obj_type, variable