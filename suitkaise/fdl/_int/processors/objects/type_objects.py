# processors/objects/type_objects.py
"""
Type Objects Processor for FDL.

Handles type annotation objects that display the type of a variable instead of its value.
"""

from ...core.object_registry import _ObjectProcessor, _object_processor
from ...core.format_state import _FormatState


@_object_processor
class _TypeObjectProcessor(_ObjectProcessor):
    """
    Processor for type annotation objects.
    
    Handles:
    - <type:variable> - Display type of variable instead of value
    
    Behavior:
    - Regular mode: Shows type name (e.g., "int", "str", "list")
    - Debug mode: Shows "type[typename]" in aquamarine color
    """
    
    @classmethod
    def get_supported_object_types(cls):
        """Return the set of object types this processor supports."""
        return {'type'}
    
    @classmethod
    def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
        """
        Process a type object and return the formatted type string.
        
        Args:
            obj_type: The object type (should be 'type')
            variable: Variable name to get type of
            format_state: Current format state
            
        Returns:
            str: Formatted type string
        """
        if obj_type != 'type':
            return f'[UNKNOWN_OBJECT_TYPE:{obj_type}]'
        
        # Get the value to determine its type
        if variable and format_state.has_more_values():
            value = format_state.get_next_value()
            value_type = type(value).__name__
        else:
            # No variable or no values available
            return '[NO_VALUE_FOR_TYPE]'
        
        if format_state.debug_mode:
            # Debug mode: Show "type[typename]" in aquamarine
            type_text = f'type[{value_type}]'
            # Aquamarine ANSI color code: \033[96m (bright cyan)
            return f'\033[96m{type_text}\033[39m'  # 39m resets to default foreground
        else:
            # Regular mode: Just show the type name with current formatting
            return value_type