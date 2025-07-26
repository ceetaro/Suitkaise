# processors/commands/_text_commands.py
from ...core.command_registry import _CommandProcessor, _command_processor
from ...core.format_state import _FormatState
from ...setup.color_conversion import _get_named_colors, _is_valid_color

@_command_processor(priority=10)
class _TextCommandProcessor(_CommandProcessor):
    
    # Get named colors from centralized color conversion system
    NAMED_COLORS = _get_named_colors()
    
    TEXT_FORMATTING = {'bold', 'italic', 'underline', 'strikethrough'}
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        """
        Check if this processor can handle the given command.
        
        Supports:
        - Text formatting: bold, italic, underline, strikethrough
        - Named colors: red, green, blue, etc.
        - Hex colors: #RGB, #RRGGBB
        - RGB colors: rgb(r, g, b)
        - Background colors: bkg <color>
        - End commands: end <formatting/color>
        - Reset command: reset
        
        Args:
            command: Command string to check
            
        Returns:
            bool: True if this processor can handle the command
        """
        command = command.strip().lower()
        
        # Basic formatting and reset
        if command in cls.TEXT_FORMATTING or command == 'reset':
            return True
        
        # Named colors
        if command in cls.NAMED_COLORS:
            return True
        
        # Hex colors
        if command.startswith('#'):
            return _is_valid_color(command)
        
        # RGB colors
        if command.startswith('rgb(') and command.endswith(')'):
            return _is_valid_color(command)
        
        # Background colors
        if command.startswith('bkg '):
            bg_color = command[4:].strip()
            return _is_valid_color(bg_color)
        
        # End commands
        if command.startswith('end '):
            target = command[4:].strip()
            return (
                target in cls.TEXT_FORMATTING or
                target in cls.NAMED_COLORS or
                target.startswith('#') or
                target.startswith('rgb(') or
                target.startswith('bkg')
            )
        
        return False
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a text formatting command and update format state.
        
        Args:
            command: Command to process
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        command = command.strip()
        command_lower = command.lower()
        
        # Reset all formatting
        if command_lower == 'reset':
            format_state.reset_formatting()
        
        # Text formatting
        elif command_lower in cls.TEXT_FORMATTING:
            setattr(format_state, command_lower, True)
        
        # Named colors
        elif command_lower in cls.NAMED_COLORS:
            format_state.text_color = command_lower
        
        # Hex colors
        elif command_lower.startswith('#') and _is_valid_color(command_lower):
            format_state.text_color = command_lower
        
        # RGB colors
        elif command_lower.startswith('rgb(') and _is_valid_color(command_lower):
            format_state.text_color = command_lower
        
        # Background colors
        elif command_lower.startswith('bkg '):
            bg_color = command[4:].strip()
            if _is_valid_color(bg_color):
                format_state.background_color = bg_color
        
        # End commands
        elif command_lower.startswith('end '):
            cls._process_end_command(command[4:].strip(), format_state)
        
        return format_state
    
    @classmethod
    def _process_end_command(cls, target: str, format_state: _FormatState):
        """
        Process an end command to disable specific formatting.
        
        Args:
            target: Target formatting to end
            format_state: Current format state to modify
        """
        target_lower = target.lower()
        
        # End text formatting
        if target_lower in cls.TEXT_FORMATTING:
            setattr(format_state, target_lower, False)
        
        # End text colors (named, hex, or rgb)
        elif (target_lower in cls.NAMED_COLORS or 
              target_lower.startswith('#') or 
              target_lower.startswith('rgb(')):
            format_state.text_color = None
        
        # End background colors
        elif target_lower.startswith('bkg'):
            format_state.background_color = None
        
        # Special case: end all formatting
        elif target_lower in ['all', 'everything']:
            format_state.reset_formatting()