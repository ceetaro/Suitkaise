# processors/commands/debug_commands.py
"""
Debug Commands Processor for FDL.

Handles debug mode commands that change how variables and formatting are processed.
Debug mode strips formatting from regular text and applies special coloring to variables.
"""

from ...core.command_registry import _CommandProcessor, _command_processor
from ...core.format_state import _FormatState


@_command_processor(priority=8)
class _DebugCommandProcessor(_CommandProcessor):
    """
    Processor for debug mode commands.
    
    Handles:
    - </debug> - Enter debug mode
    - </end debug> - Exit debug mode
    
    Debug mode behavior:
    - Strips all formatting from regular text (no colors, bold, italic, etc.)
    - Variables get special debug formatting with type annotations
    - Overrides other formatting until explicitly ended
    """
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        """
        Check if this processor can handle the given command.
        
        Supports:
        - debug - Enter debug mode
        - end debug - Exit debug mode
        
        Args:
            command: Command string to check
            
        Returns:
            bool: True if this processor can handle the command
        """
        command = command.strip().lower()
        
        if command == 'debug':
            return True
        
        if command == 'end debug':
            return True
            
        return False
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a debug command and update format state.
        
        Args:
            command: Command to process
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        command = command.strip().lower()
        
        if command == 'debug':
            # Enter debug mode
            format_state.debug_mode = True
            
            # Clear all current formatting when entering debug mode
            format_state.reset_formatting()
            
        elif command == 'end debug':
            # Exit debug mode
            format_state.debug_mode = False
        
        return format_state