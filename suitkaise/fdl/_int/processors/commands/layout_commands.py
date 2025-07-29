# processors/commands/layout_commands.py
from ...core.command_registry import _CommandProcessor, _command_processor
from ...core.format_state import _FormatState
from ...setup.text_justification import _TextJustifier


@_command_processor(priority=15)  # Medium priority for layout commands
class _LayoutCommandProcessor(_CommandProcessor):
    """
    Processor for layout-related commands.
    
    Handles:
    - Text justification: </justify left>, </justify right>, </justify center>
    - End justification: </end justify>
    
    Default justification is left. Changing justification creates a newline
    unless the current justification is already left.
    """
    
    # Supported justification options
    SUPPORTED_JUSTIFY = {'left', 'right', 'center'}
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        """
        Check if this processor can handle the given command.
        
        Handles:
        - justify <direction>
        - end justify
        
        Args:
            command: Command string to check
            
        Returns:
            bool: True if this processor can handle the command
        """
        command = command.strip().lower()
        
        # End justify command
        if command == 'end justify':
            return True
        
        # Justify command
        if command.startswith('justify '):
            direction = command[8:].strip()
            return direction in cls.SUPPORTED_JUSTIFY
        
        return False
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a layout command and update format state.
        
        Args:
            command: Command to process
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        command = command.strip()
        command_lower = command.lower()
        
        if command_lower == 'end justify':
            return cls._process_end_justify(format_state)
        elif command_lower.startswith('justify '):
            direction = command[8:].strip().lower()
            return cls._process_justify(direction, format_state)
        
        return format_state
    
    @classmethod
    def _process_justify(cls, direction: str, format_state: _FormatState) -> _FormatState:
        """
        Process justify command.
        
        Args:
            direction: Justification direction ('left', 'right', 'center')
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        if direction not in cls.SUPPORTED_JUSTIFY:
            # Invalid direction, ignore
            return format_state
        
        # Get current justification (default to 'left' if None)
        current_justify = format_state.justify or 'left'
        
        # If changing from non-left justification, add newline
        # This ensures text on different justifications appears on separate lines
        if current_justify != 'left' and current_justify != direction:
            cls._add_newline_to_outputs(format_state)
        
        # Apply justification to current content if there's any
        cls._apply_justification_to_current_content(format_state, direction)
        
        # Set new justification for future content
        format_state.justify = direction
        
        return format_state
    
    @classmethod
    def _process_end_justify(cls, format_state: _FormatState) -> _FormatState:
        """
        Process end justify command - resets to left justification.
        
        Args:
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        current_justify = format_state.justify or 'left'
        
        # If ending non-left justification, add newline
        if current_justify != 'left':
            cls._add_newline_to_outputs(format_state)
        
        # Reset to default (left) justification
        format_state.justify = 'left'
        
        return format_state
    
    @classmethod
    def _add_newline_to_outputs(cls, format_state: _FormatState) -> None:
        """
        Add newline to all output streams.
        
        Args:
            format_state: Current format state
        """
        format_state.add_to_output_streams(
            terminal='\n',
            plain='\n',
            markdown='\n',
            html='<br>\n'
        )
    
    @classmethod
    def _apply_justification_to_current_content(cls, format_state: _FormatState, direction: str) -> None:
        """
        Apply justification to current content in output streams.
        
        Args:
            format_state: Current format state
            direction: Justification direction
        """
        # Only apply if there's content and we're not in a box (boxes handle their own justification)
        if format_state.in_box:
            return
            
        justifier = _TextJustifier(terminal_width=format_state.terminal_width)
        
        # Apply to terminal output
        if format_state.terminal_output:
            content = ''.join(format_state.terminal_output)
            if content.strip():
                justified = justifier.justify_text(content, direction)
                format_state.terminal_output = [justified]
        
        # Apply to queued terminal output
        if format_state.queued_terminal_output:
            content = ''.join(format_state.queued_terminal_output)
            if content.strip():
                justified = justifier.justify_text(content, direction)
                format_state.queued_terminal_output = [justified]
        
        # Apply to plain text output
        if format_state.plain_output:
            content = ''.join(format_state.plain_output)
            if content.strip():
                justified = justifier.justify_text(content, direction)
                format_state.plain_output = [justified]


def _is_layout_command(command: str) -> bool:
    """
    Check if command is a layout-related command.
    
    Args:
        command: Command to check
        
    Returns:
        bool: True if layout command
    """
    command_lower = command.strip().lower()
    return (
        command_lower == 'end justify' or
        command_lower.startswith('justify ')
    )