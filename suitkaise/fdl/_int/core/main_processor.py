# core/_processor.py
import re
from typing import List, Dict, Tuple, Optional
from .format_state import _FormatState, _create_format_state
from ..elements.base_element import _ElementProcessor
from ..elements.text_element import _TextElement
from ..elements.variable_element import _VariableElement, _is_valid_variable_pattern
from ..elements.command_element import _CommandElement
from ..elements.object_element import _ObjectElement, _is_valid_object_pattern

class _FDLProcessor:
    """Private main FDL processor that orchestrates everything."""
    
    def __init__(self):
        # Ensure processors are registered
        from ..processors import commands, objects
        
        # Regex for parsing
        self._all_brackets_pattern = re.compile(r'<[^>]*>')
    
    def process_string(self, fdl_string: str, values: Tuple = ()) -> Dict[str, str]:
        """Process FDL string and return all output formats."""
        # Create initial state
        format_state = _create_format_state(values)
        
        # Parse into elements
        elements = self._parse_sequential(fdl_string)
        
        # Process each element
        for element in elements:
            format_state = element.process(format_state)
        
        # Apply final formatting
        self._apply_final_formatting(format_state)
        
        return format_state.get_final_outputs()
    
    def _parse_sequential(self, fdl_string: str) -> List[_ElementProcessor]:
        """Parse FDL string into sequential elements."""
        elements = []
        last_end = 0
        
        for match in self._all_brackets_pattern.finditer(fdl_string):
            start_idx = match.start()
            end_idx = match.end()
            bracket_content = match.group(0)
            
            # Add text before bracket
            if start_idx > last_end:
                text_content = fdl_string[last_end:start_idx]
                if text_content:
                    elements.append(_TextElement(text_content))
            
            # Parse bracket element
            element = self._parse_bracket_element(bracket_content)
            if element:
                elements.append(element)
            
            last_end = end_idx
        
        # Add remaining text
        if last_end < len(fdl_string):
            remaining = fdl_string[last_end:]
            if remaining:
                elements.append(_TextElement(remaining))
        
        return elements
    
    def _parse_bracket_element(self, bracket_content: str) -> Optional[_ElementProcessor]:
        """Parse bracket content into appropriate element."""
        inner = bracket_content[1:-1]  # Remove < >
        
        if not inner:
            return None
        
        try:
            # Command (starts with /)
            if inner.startswith('/'):
                return _CommandElement(inner[1:])
            
            # Object (contains : and is valid)
            if ':' in inner and _is_valid_object_pattern(inner):
                return _ObjectElement.create_from_content(inner)
            
            # Variable (valid identifier)
            if _is_valid_variable_pattern(inner):
                return _VariableElement(inner)
            
            # Invalid - treat as literal text
            return _TextElement(bracket_content)
            
        except Exception:
            # Any parsing error - treat as literal text
            return _TextElement(bracket_content)
    
    def _apply_final_formatting(self, format_state: _FormatState):
        """Apply final formatting like wrapping and justification."""
        # For now, just add reset codes to terminal output
        if format_state.terminal_output:
            # Add reset at end to prevent format bleeding
            format_state.terminal_output.append('\033[0m')
        
        # TODO: Add text wrapping and justification here