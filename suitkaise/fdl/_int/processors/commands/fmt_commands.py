# processors/commands/fmt_commands.py
"""
Format Commands Processor for FDL.

Handles format substitution commands that replace named formats with their
stored command strings. This processor should run BEFORE other processors
to expand format references.
"""

from typing import Dict, Any
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
            bool: True if this is a fmt command or end format command
        """
        # Normalize whitespace: strip and replace multiple spaces with single space
        command = ' '.join(command.strip().lower().split())
        
        # Handle comma-separated commands
        if ',' in command:
            # Check if any part starts with 'fmt ' or 'end '
            parts = [part.strip() for part in command.split(',')]
            return any(part.startswith('fmt ') or part.startswith('end ') for part in parts)
        else:
            return command.startswith('fmt ') or command.startswith('end ')
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a format command (fmt or end).
        
        This method handles both format substitution and format ending.
        
        Args:
            command: Command to process (may be comma-separated)
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        # Normalize whitespace: strip and replace multiple spaces with single space
        command = ' '.join(command.strip().split())
        command_lower = command.lower()
        
        # Handle comma-separated commands
        if ',' in command_lower:
            parts = [part.strip() for part in command_lower.split(',')]
            processed_parts = []
            
            for part in parts:
                if part.startswith('fmt '):
                    # Handle fmt command
                    format_state = cls._process_fmt_command(part, format_state)
                elif part.startswith('end '):
                    # Handle end format command
                    format_state = cls._process_end_command(part, format_state)
                else:
                    # Keep non-fmt/end commands for other processors
                    processed_parts.append(part)
            
            # Process remaining commands through other processors
            if processed_parts:
                remaining_command = ', '.join(processed_parts)
                format_state = cls._process_through_other_processors(remaining_command, format_state)
        
        else:
            # Single command
            if command_lower.startswith('fmt '):
                format_state = cls._process_fmt_command(command_lower, format_state)
            elif command_lower.startswith('end '):
                format_state = cls._process_end_command(command_lower, format_state)
        
        return format_state
    
    @classmethod
    def _process_fmt_command(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a single fmt command and track the format.
        
        Args:
            command: fmt command (e.g., 'fmt myformat')
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        format_name = command[4:].strip()  # Remove 'fmt '
        registry = get_format_registry()
        format_obj = registry.get_format(format_name)
        
        if not format_obj:
            # Format not found - do nothing
            return format_state
        
        # Capture current formatting state before applying format
        current_state = cls._capture_current_formatting(format_state)
        
        # Expand and process the format commands
        format_commands = format_obj.format.strip()
        # Remove leading </> if present before expansion
        if format_commands.startswith('</') and format_commands.endswith('>'):
            format_commands = format_commands[2:-1]
        
        expanded_command = cls._expand_fmt_commands(format_commands)
        
        # Process the expanded commands
        format_state = cls._process_through_other_processors(expanded_command, format_state)
        
        # Track what formatting this format contributed
        new_state = cls._capture_current_formatting(format_state)
        format_contribution = cls._calculate_format_contribution(current_state, new_state)
        
        # Store the format as active with its contributions
        format_state.active_formats[format_name] = format_contribution
        
        return format_state
    
    @classmethod
    def _process_end_command(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process an end format command.
        
        Args:
            command: end command (e.g., 'end myformat')
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        format_name = command[4:].strip()  # Remove 'end '
        
        if format_name not in format_state.active_formats:
            # Format not active - do nothing
            return format_state
        
        # Get the format's contributions
        format_contribution = format_state.active_formats[format_name]
        
        # End only the formatting that came from this format
        cls._end_format_contributions(format_state, format_contribution)
        
        # Remove from active formats
        del format_state.active_formats[format_name]
        
        return format_state
    
    @classmethod
    def _process_through_other_processors(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a command through other processors.
        
        Args:
            command: Command to process
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        from ...core.command_registry import _CommandRegistry
        
        # Process through other processors
        for processor_class in _CommandRegistry.get_registered_processors():
            # Skip ourselves to avoid infinite recursion
            if processor_class == cls:
                continue
                
            if processor_class.can_process(command):
                format_state = processor_class.process(command, format_state)
                break
        
        return format_state
    
    @classmethod
    def _capture_current_formatting(cls, format_state: _FormatState) -> Dict[str, Any]:
        """
        Capture the current formatting state.
        
        Args:
            format_state: Current format state
            
        Returns:
            Dict[str, Any]: Current formatting settings
        """
        return {
            'text_color': format_state.text_color,
            'background_color': format_state.background_color,
            'bold': format_state.bold,
            'italic': format_state.italic,
            'underline': format_state.underline,
            'strikethrough': format_state.strikethrough,
        }
    
    @classmethod
    def _calculate_format_contribution(cls, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate what formatting a format contributed.
        
        Args:
            before: Formatting state before format
            after: Formatting state after format
            
        Returns:
            Dict[str, Any]: What the format contributed
        """
        contribution = {}
        
        # Track what changed
        for key in before:
            if before[key] != after[key]:
                contribution[key] = {
                    'before': before[key],
                    'after': after[key]
                }
        
        return contribution
    
    @classmethod
    def _end_format_contributions(cls, format_state: _FormatState, contribution: Dict[str, Any]) -> None:
        """
        End the formatting contributions of a format.
        
        Args:
            format_state: Current format state
            contribution: What the format contributed
        """
        # Revert formatting that was contributed by this format
        # Only revert if the current value matches what the format set
        for key, change in contribution.items():
            current_value = getattr(format_state, key)
            if current_value == change['after']:
                # The format's value is still active, revert it
                setattr(format_state, key, change['before'])
                
                # Add ANSI code to reset this specific formatting
                cls._add_end_ansi_for_attribute(format_state, key, change['before'])
    
    @classmethod
    def _add_end_ansi_for_attribute(cls, format_state: _FormatState, attr: str, value: Any) -> None:
        """
        Add ANSI code to end a specific formatting attribute.
        
        Args:
            format_state: Current format state
            attr: Attribute name
            value: Value to revert to
        """
        # Import the text commands processor to use its ANSI generation
        from .text_commands import _TextCommandProcessor
        
        if attr == 'text_color':
            if value is None:
                _TextCommandProcessor._add_ansi_code(format_state, '\033[39m')  # Reset foreground
        elif attr == 'background_color':
            if value is None:
                _TextCommandProcessor._add_ansi_code(format_state, '\033[49m')  # Reset background
        elif attr == 'bold':
            if not value:
                _TextCommandProcessor._add_ansi_code(format_state, '\033[22m')  # Reset bold
        elif attr == 'italic':
            if not value:
                _TextCommandProcessor._add_ansi_code(format_state, '\033[23m')  # Reset italic
        elif attr == 'underline':
            if not value:
                _TextCommandProcessor._add_ansi_code(format_state, '\033[24m')  # Reset underline
        elif attr == 'strikethrough':
            if not value:
                _TextCommandProcessor._add_ansi_code(format_state, '\033[29m')  # Reset strikethrough
    
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