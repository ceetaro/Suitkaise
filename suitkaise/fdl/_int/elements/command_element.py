"""
Private Command Element for FDL processing.

This element processes command strings and delegates to registered
command processors through the registry system.

This is internal to the FDL engine and not exposed to users.
"""

from typing import List
from .base_element import _ElementProcessor
from core.format_state import _FormatState
from core.command_registry import _CommandRegistry, UnknownCommandError


class _CommandElement(_ElementProcessor):
    """
    Private processor for FDL command strings using registry-based delegation.
    
    Handles command strings like:
    - </bold, red, 12 hr, tz pst> → multiple commands of various types
    - </box rounded, title Important> → box creation commands
    
    Uses the command registry to automatically route commands to appropriate
    processors without hardcoded processor lists.
    
    This class is internal and should never be exposed to end users.
    """
    
    def __init__(self, command_string: str):
        """
        Initialize command element.
        
        Args:
            command_string: Raw command string without </ /> delimiters
                          Examples: "bold, red", "12hr, tz pst", "box rounded"
        """
        self.command_string = command_string.strip()
        self.commands = self._parse_commands(command_string)
    
    def process(self, format_state: _FormatState) -> _FormatState:
        """
        Process all commands in this element using the registry.
        
        Args:
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
            
        Raises:
            _UnknownCommandError: If any command is not recognized by registry
        """
        # Process each command in order using the registry
        for command in self.commands:
            format_state = _CommandRegistry.process_command(command, format_state)
        
        return format_state
    
    def _parse_commands(self, command_string: str) -> List[str]:
        """
        Parse command string into individual commands.
        
        Handles comma-separated commands and special cases like box commands
        that should be kept together even if they contain commas.
        
        Args:
            command_string: Raw command string
            
        Returns:
            List[str]: Individual commands
        """
        if not command_string:
            return []
        
        is_end_string = self._is_end_command_string(command_string)
        
        # Special handling for box commands - they can contain commas in titles
        if self._is_box_command_string(command_string):
            return [command_string]  # Keep box commands together
        
        # Split on commas for regular commands
        commands = []
        for cmd in command_string.split(','):
            cmd = cmd.strip()
            if cmd:
                if cmd.lower() == 'reset':
                    # special case for reset command
                    cmd = 'reset'
                elif is_end_string and not cmd.lower().startswith('end '):
                    # add end to all commands in the string
                    cmd = f'end {cmd}'
                commands.append(cmd)
                
        return commands
    
    def _is_end_command_string(self, command_string: str) -> bool:
        """
        Check if this is an end command that should be processed differently.
        
        The /end command applies to all commands in that <>.

        Ex: </end bold, red> ends bold text and red text color.
        
        Args:
            command_string: Command string to check
            
        Returns:
            bool: True if this is an end command
        """
        command_lower = command_string.lower().strip()
        return (
            command_lower.startswith('end ') or
            command_lower == 'reset'
        )
    
    def _is_box_command_string(self, command_string: str) -> bool:
        """
        Check if this is a box command that should be kept together.
        
        Box commands can contain commas in titles, so we don't want to split them.
        
        Args:
            command_string: Command string to check
            
        Returns:
            bool: True if this is a box command
        """
        command_lower = command_string.lower().strip()
        if command_lower == 'end box':
            return True
        return (command_lower.startswith('box'))
    
    def get_command_summary(self) -> str:
        """
        Get a human-readable summary of commands in this element.
        
        Returns:
            str: Summary of commands
        """
        if not self.commands:
            return "No commands"
        
        if len(self.commands) == 1:
            return f"Command: {self.commands[0]}"
        else:
            return f"Commands: {', '.join(self.commands)}"
    
    def get_command_info(self) -> dict:
        """
        Get detailed information about each command in this element.
        
        Returns:
            dict: Information about commands and their processors
        """
        command_info = []
        
        for command in self.commands:
            info = _CommandRegistry.get_command_info(command)
            info['command'] = command
            command_info.append(info)
        
        return {
            'command_string': self.command_string,
            'parsed_commands': self.commands,
            'command_details': command_info,
            'total_commands': len(self.commands)
        }
    
    def validate_commands(self) -> dict:
        """
        Validate all commands without processing them.
        
        Returns:
            dict: Validation results for each command
        """
        results = {
            'valid_commands': [],
            'invalid_commands': [],
            'all_valid': True
        }
        
        for command in self.commands:
            try:
                info = _CommandRegistry.get_command_info(command)
                if info['can_process']:
                    results['valid_commands'].append({
                        'command': command,
                        'processor': info['processor']
                    })
                else:
                    results['invalid_commands'].append({
                        'command': command,
                        'error': 'No processor found'
                    })
                    results['all_valid'] = False
            except Exception as e:
                results['invalid_commands'].append({
                    'command': command,
                    'error': str(e)
                })
                results['all_valid'] = False
        
        return results
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"_CommandElement(commands={self.commands})"


def _create_command_element(command_string: str) -> _CommandElement:
    """
    Factory function to create a command element with validation.
    
    Args:
        command_string: Command string to parse
        
    Returns:
        _CommandElement: Created command element
        
    Raises:
        ValueError: If command string is invalid
    """
    if not command_string or not command_string.strip():
        raise ValueError("Command string cannot be empty")
    
    return _CommandElement(command_string)


def _get_available_command_processors() -> dict:
    """
    Get information about all registered command processors.
    
    Returns:
        dict: Information about registered processors
    """
    processors = _CommandRegistry.get_registered_processors()
    
    return {
        'total_processors': len(processors),
        'processors': [
            {
                'name': processor.__name__,
                'priority': processor.get_priority()
            }
            for processor in processors
        ]
    }