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
            
            if format_state.debug_mode:
                # Debug mode - special formatting with type annotations
                text_value = self._format_debug_value(value)
            else:
                # Regular mode - process strings through FDL processor for formatting
                text_value = self._format_regular_value(value, format_state)
            
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
    
    def _format_debug_value(self, value) -> str:
        """
        Format a value for debug mode display.
        
        Debug mode rules:
        - All values are bold and italic
        - Numbers (int, float, complex): cyan
        - True: standard green  
        - False: standard red
        - None: deep ocean blue
        - Strings: raw display with grayish green quotes
        - Type annotation in dim gray
        
        Args:
            value: Value to format
            
        Returns:
            str: Formatted debug string
        """
        value_type = type(value).__name__
        
        # ANSI color codes
        BOLD_ITALIC = '\033[1;3m'  # Bold + Italic
        RESET_FORMATTING = '\033[22;23m'  # Reset bold + italic
        CYAN = '\033[36m'  # Numbers
        GREEN = '\033[32m'  # True
        RED = '\033[31m'  # False  
        BLUE = '\033[34m'  # None (deep ocean blue)
        GRAYISH_GREEN = '\033[90;32m'  # String quotes (dim + green)
        DIM_GRAY = '\033[90m'  # Type annotations
        RESET_COLOR = '\033[39m'  # Reset to default foreground
        
        # Format the value based on its type
        if isinstance(value, bool):
            # Handle booleans first (before int, since bool is a subclass of int)
            if value:
                colored_value = f'{GREEN}{BOLD_ITALIC}True{RESET_FORMATTING}{RESET_COLOR}'
            else:
                colored_value = f'{RED}{BOLD_ITALIC}False{RESET_FORMATTING}{RESET_COLOR}'
        elif isinstance(value, (int, float, complex)):
            # Numbers: cyan, bold, italic
            colored_value = f'{CYAN}{BOLD_ITALIC}{value}{RESET_FORMATTING}{RESET_COLOR}'
        elif value is None:
            # None: deep ocean blue, bold, italic  
            colored_value = f'{BLUE}{BOLD_ITALIC}None{RESET_FORMATTING}{RESET_COLOR}'
        elif isinstance(value, str):
            # Strings: raw display with grayish green quotes
            # The string content is not processed for FDL commands
            colored_value = f'{GRAYISH_GREEN}{BOLD_ITALIC}"{RESET_FORMATTING}{RESET_COLOR}{value}{GRAYISH_GREEN}{BOLD_ITALIC}"{RESET_FORMATTING}{RESET_COLOR}'
        else:
            # Other types: cyan (like numbers), bold, italic
            colored_value = f'{CYAN}{BOLD_ITALIC}{value}{RESET_FORMATTING}{RESET_COLOR}'
        
        # Add type annotation in dim gray
        type_annotation = f' {DIM_GRAY}({value_type}){RESET_COLOR}'
        
        return colored_value + type_annotation
    
    def _format_regular_value(self, value, format_state: _FormatState) -> str:
        """
        Format a value for regular mode display.
        
        In regular mode:
        - Strings are processed through FDL processor for formatting
        - Other types are converted to string normally
        
        Args:
            value: Value to format
            format_state: Current format state
            
        Returns:
            str: Formatted value string
        """
        if isinstance(value, str):
            # Process strings through FDL processor to handle embedded formatting
            from ..core.main_processor import _FDLProcessor
            processor = _FDLProcessor()
            
            # Process the string with the current format state values
            # We need to create a temporary format state to avoid modifying the current one
            temp_result = processor.process_string(value, ())
            
            # Return just the terminal output without the final reset
            terminal_output = temp_result.get('terminal', str(value))
            # Remove the final reset code that's automatically added
            if terminal_output.endswith('\x1b[0m'):
                terminal_output = terminal_output[:-4]
            
            return terminal_output
        else:
            # Non-strings: just convert to string
            return str(value)
    
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