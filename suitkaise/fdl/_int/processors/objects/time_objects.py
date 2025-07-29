# processors/objects/_time_objects.py
import time
from ...core.object_registry import _ObjectProcessor, _object_processor
from ...core.format_state import _FormatState

@_object_processor
class _TimeObjectProcessor(_ObjectProcessor):
    
    @classmethod
    def get_supported_object_types(cls):
        return {'time', 'date', 'date_words', 'day', 'time_elapsed', 'time_ago', 'time_until'}
    
    @classmethod
    def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
        # Get timestamp
        if variable:
            try:
                timestamp = format_state.get_next_value()
                if not isinstance(timestamp, (int, float)):
                    timestamp = time.time()
            except IndexError:
                timestamp = time.time()
        else:
            timestamp = time.time()
        
        # Route to appropriate method
        if obj_type == 'time':
            return cls._format_time(timestamp, format_state)
        elif obj_type == 'date':
            return cls._format_date(timestamp, format_state)
        elif obj_type == 'date_words':
            return cls._format_date_words(timestamp, format_state)
        elif obj_type == 'day':
            return cls._format_day(timestamp, format_state)
        elif obj_type in ['time_elapsed', 'time_ago', 'time_until']:
            return cls._format_elapsed(timestamp, format_state, obj_type)
        
        return f"[UNKNOWN_TIME_TYPE:{obj_type}]"
    
    @classmethod
    def _format_time(cls, timestamp: float, format_state: _FormatState) -> str:
        time_struct = time.gmtime(timestamp)
        
        if format_state.twelve_hour_time:
            return cls._format_12hour(time_struct, format_state)
        else:
            return cls._format_24hour(time_struct, format_state)
    
    @classmethod
    def _format_12hour(cls, time_struct, format_state: _FormatState) -> str:
        hour = time_struct.tm_hour
        minute = time_struct.tm_min
        second = time_struct.tm_sec
        
        # Convert to 12-hour
        if hour == 0:
            display_hour = 12
            ampm = "AM"
        elif hour < 12:
            display_hour = hour
            ampm = "AM"
        elif hour == 12:
            display_hour = 12
            ampm = "PM"
        else:
            display_hour = hour - 12
            ampm = "PM"
        
        if format_state.use_seconds:
            return f"{display_hour}:{minute:02d}:{second:02d} {ampm}"
        else:
            return f"{display_hour}:{minute:02d} {ampm}"
    
    @classmethod
    def _format_24hour(cls, time_struct, format_state: _FormatState) -> str:
        if format_state.use_seconds:
            return time.strftime('%H:%M:%S', time_struct)
        else:
            return time.strftime('%H:%M', time_struct)
    
    @classmethod
    def _format_date(cls, timestamp: float, format_state: _FormatState) -> str:
        time_struct = time.gmtime(timestamp)
        date_part = time.strftime('%d/%m/%y', time_struct)
        time_part = cls._format_24hour(time_struct, format_state)
        return f"{date_part} {time_part}"
    
    @classmethod
    def _format_date_words(cls, timestamp: float, format_state: _FormatState) -> str:
        time_struct = time.gmtime(timestamp)
        return time.strftime('%B %d, %Y', time_struct)
    
    @classmethod
    def _format_day(cls, timestamp: float, format_state: _FormatState) -> str:
        time_struct = time.gmtime(timestamp)
        return time.strftime('%A', time_struct)
    
    @classmethod
    def _format_elapsed(cls, timestamp: float, format_state: _FormatState, obj_type: str) -> str:
        current = time.time()
        duration = abs(current - timestamp)
        
        days = int(duration // 86400)
        hours = int((duration % 86400) // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = duration % 60
        
        parts = []
        if days > 0: parts.append(f"{days}d")
        if hours > 0: parts.append(f"{hours}h")
        if minutes > 0: parts.append(f"{minutes}m")
        if format_state.use_seconds and (seconds > 0 or not parts):
            if format_state.round_seconds:
                parts.append(f"{int(seconds)}s")
            else:
                parts.append(f"{seconds:.{format_state.decimal_places}f}s")
        
        result = " ".join(parts) if parts else "0s"
        
        if obj_type == 'time_ago':
            result += " ago"
        elif obj_type == 'time_until':
            result += " until"
        
        return result