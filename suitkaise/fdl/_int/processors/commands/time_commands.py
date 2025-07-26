# processors/commands/_time_commands.py
from ...core.command_registry import _CommandProcessor, _command_processor
from ...core.format_state import _FormatState

@_command_processor(priority=20)
class _TimeCommandProcessor(_CommandProcessor):
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        command = command.strip().lower()
        return (
            command == '12hr' or
            command.startswith('tz ') or
            command in ['no sec', 'no min', 'no hr'] or
            command.startswith('decimal ') or
            command == 'round sec'
        )
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        command_lower = command.strip().lower()
        
        if command_lower == '12hr':
            format_state.twelve_hour_time = True
        elif command_lower.startswith('tz '):
            format_state.timezone = command[3:].strip()
        elif command_lower == 'no sec':
            format_state.use_seconds = False
        elif command_lower == 'no min':
            format_state.use_minutes = False
            format_state.use_seconds = False
        elif command_lower == 'no hr':
            format_state.use_hours = False
            format_state.use_minutes = False
            format_state.use_seconds = False
        elif command_lower == 'round sec':
            format_state.round_seconds = True
        elif command_lower.startswith('decimal '):
            try:
                places = int(command[8:].strip())
                if 0 <= places <= 9:
                    format_state.decimal_places = places
            except ValueError:
                pass
        
        return format_state