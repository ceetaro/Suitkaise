# processors/commands/_text_commands.py
from core.command_registry import _CommandProcessor, _command_processor
from core.format_state import _FormatState

@_command_processor(priority=10)
class _TextCommandProcessor(_CommandProcessor):
    
    NAMED_COLORS = {
        'red', 'green', 'blue', 'yellow', 'purple', 'cyan', 'magenta',
        'orange', 'pink', 'brown', 'tan', 'black', 'white', 'gray'
    }
    
    TEXT_FORMATTING = {'bold', 'italic', 'underline', 'strikethrough'}
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        command = command.strip().lower()
        return (
            command in cls.TEXT_FORMATTING or
            command in cls.NAMED_COLORS or
            command == 'reset' or
            command.startswith('end ') or
            command.startswith('bkg ') or
            command.startswith('#') or
            command.startswith('rgb(')
        )
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        command = command.strip()
        command_lower = command.lower()
        
        if command_lower == 'reset':
            format_state.reset_formatting()
        elif command_lower in cls.TEXT_FORMATTING:
            setattr(format_state, command_lower, True)
        elif command_lower in cls.NAMED_COLORS:
            format_state.text_color = command_lower
        elif command_lower.startswith('bkg '):
            format_state.background_color = command[4:].strip()
        elif command_lower.startswith('end '):
            cls._process_end_command(command[4:].strip(), format_state)
        # TODO: Add hex and RGB color support
        
        return format_state
    
    @classmethod
    def _process_end_command(cls, target: str, format_state: _FormatState):
        target_lower = target.lower()
        if target_lower in cls.TEXT_FORMATTING:
            setattr(format_state, target_lower, False)
        elif target_lower in cls.NAMED_COLORS or target_lower.startswith('#') or target_lower.startswith('rgb('):
            format_state.text_color = None
        elif target_lower.startswith('bkg'):
            format_state.background_color = None