# core/main_processor.py
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
    
    def process_string(self, fdl_string: str, values: Tuple = (), 
                      check_progress_bar: bool = True) -> Dict[str, str]:
        """
        Process FDL string and return all output formats.
        
        Args:
            fdl_string: FDL string to process
            values: Tuple of values for variable substitution
            check_progress_bar: Whether to check for active progress bars
            
        Returns:
            Dict[str, str]: All output formats
        """
        # Create initial state
        format_state = _create_format_state(values)
        
        # Check if progress bar is active and integrate with format state
        if check_progress_bar:
            self._integrate_progress_bar_state(format_state)
        
        # Parse into elements
        elements = self._parse_sequential(fdl_string)
        
        # Process each element
        for element in elements:
            format_state = element.process(format_state)
        
        # Apply final formatting
        self._apply_final_formatting(format_state)
        
        return format_state.get_final_outputs()
    
    def _integrate_progress_bar_state(self, format_state: _FormatState) -> None:
        """Integrate progress bar state with format state."""
        try:
            # Import here to avoid circular imports
            from ..processors.objects.progress_bars import _ProgressBarManager
            
            active_bar = _ProgressBarManager.get_active_bar()
            if active_bar and not active_bar.is_stopped:
                # Start progress bar mode in format state
                format_state.start_progress_bar_mode(active_bar)
        except ImportError:
            # Progress bar module not available, continue normally
            pass
    
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
        # Apply text wrapping and justification to all output streams
        self._apply_wrapping_and_justification(format_state)
        
        # Add reset codes to appropriate output streams
        if format_state.terminal_output or format_state.queued_terminal_output:
            # Add reset at end to prevent format bleeding
            if format_state.bar_active:
                format_state.queued_terminal_output.append('\033[0m')
            else:
                format_state.terminal_output.append('\033[0m')
    
    def _apply_wrapping_and_justification(self, format_state: _FormatState):
        """
        Apply text wrapping and justification to all output streams.
        
        Correct order: ANSI codes already applied → wrap text → justify text
        Uses visual width calculations to handle ANSI codes properly.
        """
        from ..setup.text_wrapping import _TextWrapper
        from ..setup.text_justification import _TextJustifier
        
        # Get terminal width for consistent formatting
        terminal_width = format_state.terminal_width
        
        # Create wrapper and justifier with same terminal width
        wrapper = _TextWrapper(width=terminal_width)
        justifier = _TextJustifier(terminal_width=terminal_width)
        
        # Get justification setting
        justify_mode = format_state.justify or 'left'
        
        # Helper function to avoid code duplication
        def process_output_stream(output_list):
            """Process a single output stream with wrapping and justification."""
            if not output_list:
                return
            
            content = ''.join(output_list)
            if content.strip():  # Only process non-empty content
                # Step 1: Wrap text (returns list of lines, handles ANSI codes with visual width)
                wrapped_lines = wrapper.wrap_text(content)
                # Step 2: Join lines and justify (preserves ANSI codes)
                wrapped_text = '\n'.join(wrapped_lines)
                justified = justifier.justify_text(wrapped_text, justify_mode)
                output_list[:] = [justified]  # Replace contents in-place
        
        # Apply to all output streams
        process_output_stream(format_state.terminal_output)
        process_output_stream(format_state.queued_terminal_output) 
        process_output_stream(format_state.plain_output)
        process_output_stream(format_state.markdown_output)