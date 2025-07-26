"""
Private Variable Element for FDL processing.

This module handles variable substitution patterns like <variable_name>
that get replaced with values from the provided tuple.

This is internal to the FDL engine and not exposed to users.
"""

from .base_element import _ElementProcessor
from ..core.format_state import _FormatState


class _VariableElement(_ElementProcessor):
    """
    Private processor for variable substitution.
    
    Handles variable patterns like <variable_name> that get replaced
    with values from the provided tuple.
    
    This class is internal and should never be exposed to end users.
    """
    
    def __init__(self, variable_name: str):
        """
        Initialize variable element.
        
        Args:
            variable_name: Name of variable to substitute
        """
        self.variable_name = variable_name.strip()
        
        if not self.variable_name:
            raise ValueError("Variable name cannot be empty")
        
        if not self._is_valid_variable_name(self.variable_name):
            raise ValueError(f"Invalid variable name: '{self.variable_name}'")
    
    def process(self, format_state: _FormatState) -> _FormatState:
        """
        Process variable substitution.
        
        Args:
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        try:
            # Get next value from tuple
            value = format_state.get_next_value()
            
            # Convert to string
            text_value = str(value)
            
            if format_state.in_box:
                # Inside a box - accumulate content
                format_state.box_content.append(text_value)
            else:
                # Outside box - add to output streams
                self._add_to_outputs(format_state, text_value)
            
            return format_state
            
        except IndexError:
            # No more values available
            error_text = f"[MISSING_VALUE_{self.variable_name}]"
            
            if format_state.in_box:
                format_state.box_content.append(error_text)
            else:
                self._add_to_outputs(format_state, error_text)
            
            return format_state
    
    def _is_valid_variable_name(self, name: str) -> bool:
        """
        Check if string is a valid variable name.
        
        Args:
            name: Name to validate
            
        Returns:
            bool: True if valid variable name
        """
        if not name:
            return False
        
        # Must start with letter or underscore, followed by letters, digits, or underscores
        import re
        return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name) is not None
    
    def get_variable_info(self) -> dict:
        """
        Get information about this variable element.
        
        Returns:
            dict: Variable information
        """
        return {
            'variable_name': self.variable_name,
            'is_valid': self._is_valid_variable_name(self.variable_name),
            'element_type': 'variable'
        }
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"_VariableElement({self.variable_name!r})"


def _is_valid_variable_pattern(content: str) -> bool:
    """
    Check if content is a valid variable pattern.
    
    Args:
        content: Content to check (without brackets)
        
    Returns:
        bool: True if valid variable pattern
    """
    if not content:
        return False
    
    import re
    return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', content) is not None


def _create_variable_element(content: str) -> _VariableElement:
    """
    Factory function to create a variable element with validation.
    
    Args:
        content: Variable content (without brackets)
        
    Returns:
        _VariableElement: Created variable element
        
    Raises:
        ValueError: If content is not a valid variable name
    """
    return _VariableElement(content)