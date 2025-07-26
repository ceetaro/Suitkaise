"""
Private Unified Object Element for FDL processing.

This element handles all <objtype:variable> patterns centrally and routes
to registered object processors through the registry system.

This is internal to the FDL engine and not exposed to users.
"""

from typing import Optional
from .base_element import _ElementProcessor
from ..core.format_state import _FormatState
from ..core.object_registry import (_ObjectRegistry, UnsupportedObjectError, 
                              _parse_object_content)


class _ObjectElement(_ElementProcessor):
    """
    Private unified processor for all object patterns: <objtype:variable>
    
    Handles validation and routing to registered object processors.
    Uses the object registry to automatically route to appropriate processors
    without hardcoded processor lists.
    
    This class is internal and should never be exposed to end users.
    """
    
    def __init__(self, obj_type: str, variable: Optional[str] = None):
        """
        Initialize object element.
        
        Args:
            obj_type: Type of object (e.g., 'time', 'date', 'spinner')
            variable: Variable name for value substitution (None for current/default)
            
        Raises:
            _UnsupportedObjectError: If object type is not supported by any processor
        """
        self.obj_type = obj_type.strip()
        self.variable = variable.strip() if variable else None
        
        # Validate object type is supported through registry
        if not _ObjectRegistry.is_supported_type(self.obj_type):
            raise UnsupportedObjectError(f"Unsupported object type: '{self.obj_type}'")
    
    def process(self, format_state: _FormatState) -> _FormatState:
        """
        Process object by routing to appropriate processor through registry.
        
        Args:
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        # Process the object using the registry
        formatted_result = _ObjectRegistry.process_object(
            obj_type=self.obj_type,
            variable=self.variable,
            format_state=format_state
        )
        
        # Add result to appropriate output
        if format_state.in_box:
            format_state.box_content.append(formatted_result)
        else:
            self._add_to_outputs(format_state, formatted_result)
        
        return format_state
    
    @classmethod
    def create_from_content(cls, object_content: str) -> '_ObjectElement':
        """
        Create ObjectElement from object content string.
        
        Args:
            object_content: Content without brackets (e.g., "time:timestamp")
            
        Returns:
            _ObjectElement: Created object element
            
        Raises:
            ValueError: If object content format is invalid
            _UnsupportedObjectError: If object type is not supported
        """
        obj_type, variable = _parse_object_content(object_content)
        return cls(obj_type, variable)
    
    def get_object_summary(self) -> str:
        """
        Get human-readable summary of this object.
        
        Returns:
            str: Summary of object
        """
        if self.variable:
            return f"{self.obj_type}:{self.variable}"
        else:
            return f"{self.obj_type}: (current/default)"
    
    def get_object_info(self) -> dict:
        """
        Get detailed information about this object.
        
        Returns:
            dict: Information about the object and its processor
        """
        registry_info = _ObjectRegistry.get_object_info(self.obj_type)
        
        return {
            'obj_type': self.obj_type,
            'variable': self.variable,
            'processor': registry_info['processor'],
            'is_supported': registry_info['is_supported'],
            'processor_supported_types': registry_info['supported_types'],
            'element_type': 'object'
        }
    
    def validate_object(self) -> dict:
        """
        Validate this object without processing it.
        
        Returns:
            dict: Validation results
        """
        is_supported = _ObjectRegistry.is_supported_type(self.obj_type)
        processor = _ObjectRegistry.get_processor_for_type(self.obj_type)
        
        return {
            'obj_type': self.obj_type,
            'variable': self.variable,
            'is_supported': is_supported,
            'processor': processor.__name__ if processor else None,
            'is_valid': is_supported
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"_ObjectElement(type={self.obj_type!r}, variable={self.variable!r})"


def _create_object_element(object_content: str) -> _ObjectElement:
    """
    Factory function to create an object element with validation.
    
    Args:
        object_content: Object content without brackets
        
    Returns:
        _ObjectElement: Created object element
        
    Raises:
        ValueError: If object content format is invalid
        _UnsupportedObjectError: If object type is not supported
    """
    return _ObjectElement.create_from_content(object_content)


def _is_valid_object_pattern(content: str) -> bool:
    """
    Check if content is a valid object pattern.
    
    Args:
        content: Content to check (without brackets)
        
    Returns:
        bool: True if valid and supported object pattern
    """
    try:
        obj_type, _ = _parse_object_content(content)
        return _ObjectRegistry.is_supported_type(obj_type)
    except (ValueError, _UnsupportedObjectError):
        return False


def _get_supported_object_types() -> set:
    """
    Get set of all supported object types from registry.
    
    Returns:
        set: Set of supported object type names
    """
    return _ObjectRegistry.get_supported_types()


def _get_object_type_info(obj_type: str) -> dict:
    """
    Get information about a specific object type.
    
    Args:
        obj_type: Object type to check
        
    Returns:
        dict: Information about the object type
    """
    return _ObjectRegistry.get_object_info(obj_type)


def _get_available_object_processors() -> dict:
    """
    Get information about all registered object processors.
    
    Returns:
        dict: Information about registered processors
    """
    processors = _ObjectRegistry.get_registered_processors()
    
    processor_info = {}
    for obj_type, processor_class in processors.items():
        processor_name = processor_class.__name__
        if processor_name not in processor_info:
            processor_info[processor_name] = {
                'class': processor_name,
                'supported_types': []
            }
        processor_info[processor_name]['supported_types'].append(obj_type)
    
    return {
        'total_object_types': len(processors),
        'total_processors': len(processor_info),
        'processors': list(processor_info.values()),
        'type_mapping': processors
    }