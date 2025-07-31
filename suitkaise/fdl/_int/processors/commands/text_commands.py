# processors/commands/_text_commands.py
from ...core.command_registry import _CommandProcessor, _command_processor
from ...core.format_state import _FormatState
from ...setup.color_conversion import _get_named_colors, _ColorConverter

@_command_processor(priority=10)
class _TextCommandProcessor(_CommandProcessor):
    
    # Get named colors from centralized color conversion system
    NAMED_COLORS = _get_named_colors()
    
    TEXT_FORMATTING = {'bold', 'italic', 'underline', 'strikethrough'}
    
    # ANSI codes for text formatting
    FORMATTING_CODES = {
        'bold': '\033[1m',
        'italic': '\033[3m', 
        'underline': '\033[4m',
        'strikethrough': '\033[9m'
    }
    
    # Create color converter instance
    _color_converter = _ColorConverter()
    
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
        - Comma-separated commands: red, bold, etc.
        
        Args:
            command: Command string to check
            
        Returns:
            bool: True if this processor can handle the command
        """
        command = command.strip().lower()
        
        # Handle comma-separated commands (but not inside parentheses)
        if ',' in command:
            # Check if comma is inside parentheses (like in rgb(255, 0, 0))
            paren_count = 0
            for char in command:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == ',' and paren_count == 0:
                    # Comma is outside parentheses, so it's a separator
                    parts = [part.strip() for part in command.split(',')]
                    return all(cls._can_process_single_command(part) for part in parts)
            
            # If we get here, all commas are inside parentheses
            return cls._can_process_single_command(command)
        else:
            return cls._can_process_single_command(command)
    
    @classmethod
    def _can_process_single_command(cls, command: str) -> bool:
        """Check if a single command (no commas) can be processed."""
        command = command.strip().lower()
        
        # Basic formatting and reset
        if command in cls.TEXT_FORMATTING or command == 'reset':
            return True
        
        # Named colors
        if command in cls.NAMED_COLORS:
            return True
        
        # Hex colors
        if command.startswith('#'):
            return cls._color_converter.is_valid_color(command)
        
        # RGB colors
        if command.startswith('rgb(') and command.endswith(')'):
            return cls._color_converter.is_valid_color(command)
        
        # Background colors
        if command.startswith('bkg '):
            bg_color = command[4:].strip()
            return cls._color_converter.is_valid_color(bg_color)
        
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
            command: Command to process (may be comma-separated)
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        command = command.strip()
        command_lower = command.lower()
        
        # Handle comma-separated commands (but not inside parentheses)
        if ',' in command_lower:
            # Check if comma is inside parentheses (like in rgb(255, 0, 0))
            paren_count = 0
            for char in command_lower:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
                elif char == ',' and paren_count == 0:
                    # Comma is outside parentheses, so it's a separator
                    parts = [part.strip() for part in command_lower.split(',')]
                    for part in parts:
                        format_state = cls._process_single_command(part, format_state)
                    return format_state
            
            # If we get here, all commas are inside parentheses
            return cls._process_single_command(command_lower, format_state)
        else:
            return cls._process_single_command(command_lower, format_state)
    
    @classmethod
    def _process_single_command(cls, command: str, format_state: _FormatState) -> _FormatState:
        """Process a single command (no commas)."""
        # In debug mode, ignore all text formatting commands except reset
        if format_state.debug_mode and command not in ['reset', 'end all']:
            # Debug mode strips all formatting from regular text
            return format_state
        
        # Reset all formatting
        if command == 'reset':
            format_state.reset_formatting()
            format_state.debug_mode = False  # Reset also exits debug mode
            cls._add_ansi_code(format_state, '\033[0m')  # ANSI reset code
        
        # Text formatting
        elif command in cls.TEXT_FORMATTING:
            setattr(format_state, command, True)
            ansi_code = cls.FORMATTING_CODES.get(command, '')
            if ansi_code:
                cls._add_ansi_code(format_state, ansi_code)
        
        # Named colors
        elif command in cls.NAMED_COLORS:
            format_state.text_color = command
            ansi_code = cls._color_converter.to_ansi_fg(command)
            cls._add_ansi_code(format_state, ansi_code)
        
        # Hex colors
        elif command.startswith('#') and cls._color_converter.is_valid_color(command):
            format_state.text_color = command
            ansi_code = cls._color_converter.to_ansi_fg(command)
            cls._add_ansi_code(format_state, ansi_code)
        
        # RGB colors
        elif command.startswith('rgb(') and cls._color_converter.is_valid_color(command):
            format_state.text_color = command
            ansi_code = cls._color_converter.to_ansi_fg(command)
            cls._add_ansi_code(format_state, ansi_code)
        
        # Background colors
        elif command.startswith('bkg '):
            bg_color = command[4:].strip()
            if cls._color_converter.is_valid_color(bg_color):
                format_state.background_color = bg_color
                ansi_code = cls._color_converter.to_ansi_bg(bg_color)
                cls._add_ansi_code(format_state, ansi_code)
        
        # End commands
        elif command.startswith('end '):
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
            # Generate ANSI code to turn off specific formatting
            cls._add_end_formatting_ansi(format_state, target_lower)
        
        # End text colors (named, hex, or rgb)
        elif (target_lower in cls.NAMED_COLORS or 
              target_lower.startswith('#') or 
              target_lower.startswith('rgb(')):
            format_state.text_color = None
            cls._add_ansi_code(format_state, '\033[39m')  # Reset to default foreground color
        
        # End background colors
        elif target_lower.startswith('bkg'):
            format_state.background_color = None
            cls._add_ansi_code(format_state, '\033[49m')  # Reset to default background color
        
        # Special case: end all formatting
        elif target_lower in ['all', 'everything']:
            format_state.reset_formatting()
            format_state.debug_mode = False  # End all also exits debug mode
            cls._add_ansi_code(format_state, '\033[0m')  # ANSI reset code
    
    @classmethod
    def _add_ansi_code(cls, format_state: _FormatState, ansi_code: str):
        """
        Add ANSI code to terminal output streams only.
        
        Args:
            format_state: Current format state
            ansi_code: ANSI escape code to add
        """
        # Only add ANSI codes to terminal output, not plain text or other formats
        if format_state.bar_active:
            # Add to queued output if progress bar is active
            format_state.queued_terminal_output.append(ansi_code)
        else:
            # Add to normal terminal output
            format_state.terminal_output.append(ansi_code)
    
    @classmethod
    def _add_end_formatting_ansi(cls, format_state: _FormatState, formatting_type: str):
        """
        Add ANSI code to end specific formatting.
        
        Args:
            format_state: Current format state
            formatting_type: Type of formatting to end
        """
        # ANSI codes to end specific formatting
        end_codes = {
            'bold': '\033[22m',      # End bold/dim
            'italic': '\033[23m',    # End italic
            'underline': '\033[24m', # End underline
            'strikethrough': '\033[29m'  # End strikethrough
        }
        
        ansi_code = end_codes.get(formatting_type)
        if ansi_code:
            cls._add_ansi_code(format_state, ansi_code)