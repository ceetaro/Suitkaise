# processors/commands/fmt_commands.py
"""
Format Commands Processor for FDL.

Handles format substitution commands that replace named formats with their
stored command strings. This processor should run BEFORE other processors
to expand format references.
"""

from ...core.command_registry import _CommandProcessor, _command_processor
from ...core.format_state import _FormatState
from ...core.format_registry import get_format_registry


@_command_processor(priority=10)  # High priority to run before other processors
class _FormatCommandProcessor(_CommandProcessor):
    """
    Processor for format substitution commands.
    
    Handles:
    - </fmt format_name> - Substitute named format
    - </fmt format_name, other, commands> - Substitute format and combine with other commands
    
    Format substitution happens by replacing the fmt command with the stored
    format string, allowing other processors to handle the expanded commands.
    """
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        """
        Check if this processor can handle the given command.
        
        Args:
            command: Command string to check
            
        Returns:
            bool: True if this is a fmt command
        """
        command = command.strip().lower()
        
        # Handle comma-separated commands
        if ',' in command:
            # Check if any part starts with 'fmt '
            parts = [part.strip() for part in command.split(',')]
            return any(part.startswith('fmt ') for part in parts)
        else:
            return command.startswith('fmt ')
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a format substitution command.
        
        This method expands fmt commands by substituting them with their
        registered format strings, then processes the resulting commands
        through other processors.
        
        Args:
            command: Command to process (may be comma-separated)
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        command = command.strip()
        command_lower = command.lower()
        
        # Expand fmt commands in the command string
        expanded_command = cls._expand_fmt_commands(command_lower)
        
        # If no expansion occurred, this shouldn't have been processed by us
        if expanded_command == command_lower:
            return format_state
        
        # Process the expanded commands through the appropriate processors
        from ...core.command_registry import _CommandRegistry
        
        # Process the expanded command through other processors
        # We need to find processors that can handle the expanded commands
        for processor_class in _CommandRegistry.get_registered_processors():
            # Skip ourselves to avoid infinite recursion
            if processor_class == cls:
                continue
                
            if processor_class.can_process(expanded_command):
                format_state = processor_class.process(expanded_command, format_state)
                break
        
        return format_state
    
    @classmethod
    def _expand_fmt_commands(cls, command: str) -> str:
        """
        Expand fmt commands in a command string recursively.
        
        Args:
            command: Command string that may contain fmt commands
            
        Returns:
            str: Command string with fmt commands expanded
        """
        registry = get_format_registry()
        
        # Keep expanding until no more fmt commands are found
        max_expansions = 10  # Prevent infinite recursion
        expansion_count = 0
        
        while expansion_count < max_expansions:
            original_command = command
            command = cls._expand_fmt_commands_once(command, registry)
            
            # If no change occurred, we're done
            if command == original_command:
                break
                
            expansion_count += 1
        
        return command
    
    @classmethod
    def _expand_fmt_commands_once(cls, command: str, registry) -> str:
        """
        Expand fmt commands in a command string once (non-recursive).
        
        Args:
            command: Command string that may contain fmt commands
            registry: Format registry instance
            
        Returns:
            str: Command string with fmt commands expanded once
        """
        # Handle comma-separated commands
        if ',' in command:
            parts = [part.strip() for part in command.split(',')]
            expanded_parts = []
            
            for part in parts:
                if part.startswith('fmt '):
                    # Extract format name
                    format_name = part[4:].strip()  # Remove 'fmt '
                    
                    # Get format from registry
                    format_obj = registry.get_format(format_name)
                    if format_obj:
                        # Expand the format string and split into parts
                        format_commands = format_obj.format.strip()
                        # Remove leading </> if present
                        if format_commands.startswith('</') and format_commands.endswith('>'):
                            format_commands = format_commands[2:-1]
                        
                        # Split format commands by comma and add to parts
                        format_parts = [p.strip() for p in format_commands.split(',')]
                        expanded_parts.extend(format_parts)
                    else:
                        # Format not found - keep original command
                        expanded_parts.append(part)
                else:
                    # Not a fmt command - keep as is
                    expanded_parts.append(part)
            
            return ', '.join(expanded_parts)
        
        else:
            # Single command
            if command.startswith('fmt '):
                format_name = command[4:].strip()  # Remove 'fmt '
                
                format_obj = registry.get_format(format_name)
                if format_obj:
                    # Return the format string (remove </> wrapper if present)
                    format_commands = format_obj.format.strip()
                    if format_commands.startswith('</') and format_commands.endswith('>'):
                        format_commands = format_commands[2:-1]
                    return format_commands
                else:
                    # Format not found - return original
                    return command
            else:
                # Not a fmt command
                return command