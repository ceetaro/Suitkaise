"""
Object Processor for fdl - Time, Date, and Elapsed Object Handling

This module provides concrete object processing for fdl's time/date/elapsed patterns.
Handles object-specific commands like timezone, 12-hour format, and time suffixes.

Supported Objects:
- <time:> / <time:timestamp> - Time formatting
- <date:> / <date:timestamp> - Date formatting  
- <datelong:> / <datelong:timestamp> - Long date format
- <elapsed:> / <elapsed:timestamp> - Elapsed time from timestamp to now (3d 2h 15m 30s format)

Supported Commands:
- 12hr - 12-hour format (removes leading zeros)
- tz <timezone> - Timezone conversion with DST
- time ago / time until - Calculate elapsed time from timestamp to now
- no sec - Remove seconds from display
"""

import time
import warnings
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import re

try:
    from zoneinfo import ZoneInfo
    ZONEINFO_AVAILABLE = True
except ImportError:
    # Fallback for Python < 3.9
    ZONEINFO_AVAILABLE = False
    import pytz
    ZoneInfo = None

warnings.simplefilter("always")  # Show all warnings, even duplicates

class ObjectProcessorError(Exception):
    """Raised when object processing fails."""
    pass


class InvalidObjectError(ObjectProcessorError):
    """Raised when object pattern is invalid."""
    pass


class UnsupportedObjectError(ObjectProcessorError):
    """Raised when object type is not supported."""
    pass


@dataclass
class _ObjectCommands:
    """
    Parsed object-specific commands for time/date formatting.
    
    Attributes:
        use_12hr (bool): Use 12-hour format instead of 24-hour
        timezone (Optional[str]): Timezone to convert to (e.g., 'pst', 'utc')
        time_suffix (Optional[str]): 'ago' or 'until' suffix
        hide_seconds (bool): Remove seconds from time display
        smart_units (Optional[int]): Show only N highest units (1 or 2)
        hide_hours (bool): Hide hours, minutes, seconds (show only days)
        hide_minutes (bool): Hide minutes and seconds (show days+hours only)
        round_seconds (bool): Round seconds to whole numbers, no decimals
    """
    use_12hr: bool = False
    timezone: Optional[str] = None
    time_suffix: Optional[str] = None
    hide_seconds: bool = False
    smart_units: Optional[int] = None
    hide_hours: bool = False
    hide_minutes: bool = False
    round_seconds: bool = False
    
    def validate(self) -> None:
        """Validate command combination for conflicts."""
        # Can't have both time ago and time until
        if self.time_suffix not in [None, 'ago', 'until']:
            raise InvalidObjectError(f"Invalid time suffix: {self.time_suffix}")
        
        # Smart units must be 1 or 2
        if self.smart_units is not None and self.smart_units not in [1, 2]:
            raise InvalidObjectError(f"Smart units must be 1 or 2, got: {self.smart_units}")
        
        # Can't combine hide_hours with hide_minutes (hide_hours is more restrictive)
        if self.hide_hours and self.hide_minutes:
            warnings.warn("'no hr' already includes 'no min' - 'no min' command ignored", UserWarning)


class _TimeZoneHandler:
    """
    Handles timezone conversion with daylight savings support using pure timestamp math.
    
    Works with Unix timestamps throughout, calculating offsets and applying them directly.
    """
    
    # Comprehensive timezone abbreviations to full names
    TIMEZONE_MAP = {
        # United States
        'pst': 'America/Los_Angeles',    # Pacific Standard Time
        'pdt': 'America/Los_Angeles',    # Pacific Daylight Time
        'mst': 'America/Denver',         # Mountain Standard Time
        'mdt': 'America/Denver',         # Mountain Daylight Time
        'cst': 'America/Chicago',        # Central Standard Time
        'cdt': 'America/Chicago',        # Central Daylight Time
        'est': 'America/New_York',       # Eastern Standard Time
        'edt': 'America/New_York',       # Eastern Daylight Time
        'pt': 'America/Los_Angeles',     # Pacific Time
        'mt': 'America/Denver',          # Mountain Time
        'ct': 'America/Chicago',         # Central Time
        'et': 'America/New_York',        # Eastern Time

        # Alaska
        'akst': 'America/Anchorage',     # Alaska Standard Time
        'akdt': 'America/Anchorage',     # Alaska Daylight Time
        'ast': 'America/Anchorage',      # Alaska Standard Time (alternate)
        'adt': 'America/Anchorage',      # Alaska Daylight Time (alternate)
        'alaska': 'America/Anchorage',
        
        # Hawaii
        'hst': 'Pacific/Honolulu',       # Hawaii Standard Time
        'hdt': 'Pacific/Honolulu',       # Hawaii Daylight Time (rarely used)
        'hawaii': 'Pacific/Honolulu',

        # Canada
        'nst': 'America/St_Johns',       # Newfoundland Standard Time
        'ndt': 'America/St_Johns',       # Newfoundland Daylight Time
        'newfoundland': 'America/St_Johns',
        'atlantic': 'America/Halifax',    # Atlantic Time
        'eastern_canada': 'America/Toronto',
        'central_canada': 'America/Winnipeg',
        'mountain_canada': 'America/Edmonton',
        'pacific_canada': 'America/Vancouver',
        
        # United Kingdom & Ireland
        'gmt': 'Europe/London',          # Greenwich Mean Time
        'bst': 'Europe/London',          # British Summer Time
        'utc': 'UTC',                    # Coordinated Universal Time
        'london': 'Europe/London',
        'uk': 'Europe/London',
        'britain': 'Europe/London',
        'england': 'Europe/London',
        'scotland': 'Europe/London',
        'wales': 'Europe/London',
        'ireland': 'Europe/Dublin',
        'dublin': 'Europe/Dublin',
        'ist': 'Europe/Dublin',          # Irish Standard Time

        # Australia (Major Cities)
        'aest': 'Australia/Sydney',      # Australian Eastern Standard Time
        'aedt': 'Australia/Sydney',      # Australian Eastern Daylight Time
        'acst': 'Australia/Adelaide',    # Australian Central Standard Time
        'acdt': 'Australia/Adelaide',    # Australian Central Daylight Time
        'awst': 'Australia/Perth',       # Australian Western Standard Time
        'awdt': 'Australia/Perth',       # Australian Western Daylight Time (rarely used)
        'sydney': 'Australia/Sydney',
        'melbourne': 'Australia/Melbourne',
        'brisbane': 'Australia/Brisbane',
        'adelaide': 'Australia/Adelaide',
        'perth': 'Australia/Perth',
        'darwin': 'Australia/Darwin',
        'hobart': 'Australia/Hobart',
        'canberra': 'Australia/Canberra',
        'australia_east': 'Australia/Sydney',
        'australia_central': 'Australia/Adelaide',
        'australia_west': 'Australia/Perth',

        # New Zealand
        'nzst': 'Pacific/Auckland',      # New Zealand Standard Time
        'nzdt': 'Pacific/Auckland',      # New Zealand Daylight Time
        'auckland': 'Pacific/Auckland',
        'wellington': 'Pacific/Auckland',
        'christchurch': 'Pacific/Auckland',
        'new_zealand': 'Pacific/Auckland',
        'nz': 'Pacific/Auckland',
        
        # South Africa
        'sast': 'Africa/Johannesburg',   # South African Standard Time
        'johannesburg': 'Africa/Johannesburg',
        'cape_town': 'Africa/Johannesburg',
        'durban': 'Africa/Johannesburg',
        'south_africa': 'Africa/Johannesburg',

        # other common timezones and abbreviations
        'hong_kong': 'Asia/Hong_Kong',
        'singapore': 'Asia/Singapore',
        'z': 'UTC',                      # Zulu time (military)
        'zulu': 'UTC',
        'greenwich': 'Europe/London'
    }
    
    def __init__(self, auto_dst: bool = True):
        """
        Initialize timezone handler.
        
        Args:
            auto_dst (bool): Whether to automatically handle daylight savings
        """
        self.auto_dst = auto_dst
        # Cache for timezone offset calculations
        self._offset_cache: Dict[Tuple[str, float], float] = {}
    
    def convert_timestamp(self, timestamp: float, target_tz: str) -> float:
        """
        Convert Unix timestamp to target timezone, returning adjusted timestamp for use with time.gmtime().
        
        Args:
            timestamp (float): Unix timestamp (UTC)
            target_tz (str): Target timezone (e.g., 'pst', 'America/Los_Angeles')
            
        Returns:
            float: Adjusted timestamp for use with time.gmtime()
            
        Raises:
            ObjectProcessorError: If timezone conversion fails
            
        The returned timestamp can be used with time.gmtime() to get the correct local time.
        """
        try:
            # Check cache first (rounded to hour for efficiency)
            cache_key = (target_tz.lower(), int(timestamp // 3600) * 3600)
            if cache_key in self._offset_cache:
                cached_offset = self._offset_cache[cache_key]
                return timestamp + cached_offset
            
            # Normalize timezone name
            tz_name = self._normalize_timezone(target_tz)
            
            # Handle UTC special case
            if tz_name == 'UTC':
                return timestamp
            
            # Calculate timezone offset using minimal datetime usage
            import datetime
            utc_dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
            
            if ZONEINFO_AVAILABLE:
                target_tz_obj = ZoneInfo(tz_name)
                local_dt = utc_dt.astimezone(target_tz_obj)
            else:
                # Fallback to pytz
                target_tz_obj = pytz.timezone(tz_name)
                local_dt = utc_dt.astimezone(target_tz_obj)
            
            # Calculate the offset in seconds
            offset_seconds = local_dt.utcoffset().total_seconds()
            
            # Cache the offset (cache for 1 hour to handle DST changes)
            self._offset_cache[cache_key] = offset_seconds
            
            # Return adjusted timestamp for use with time.gmtime()
            return timestamp + offset_seconds
                
        except Exception as e:
            raise ObjectProcessorError(f"Timezone conversion failed for '{target_tz}': {e}")
    
    def _normalize_timezone(self, tz_input: str) -> str:
        """
        Normalize timezone input to standard timezone name.
        
        Args:
            tz_input (str): User input timezone
            
        Returns:
            str: Normalized timezone name
        """
        tz_lower = tz_input.lower().strip()
        
        # Check common abbreviations first
        if tz_lower in self.TIMEZONE_MAP:
            return self.TIMEZONE_MAP[tz_lower]
        
        # Return as-is if not found (might be a full timezone name)
        return tz_input


class _ObjectProcessor:
    """
    Concrete object processor for fdl time/date/elapsed patterns.
    
    Processes object patterns and applies object-specific commands to generate
    formatted time/date/elapsed strings using pure timestamp math.
    """
    
    def __init__(self, auto_dst: bool = True):
        """
        Initialize object processor.
        
        Args:
            auto_dst (bool): Whether to automatically handle daylight savings
        """
        self.timezone_handler = _TimeZoneHandler(auto_dst)
        
        # Performance tracking
        self._processed_count = 0
        self._error_count = 0
    
    def process_object(self, obj_content: str, commands: List[str], 
                      values: Tuple, var_index: int) -> Tuple[str, int]:
        """
        Process an object pattern with its commands.
        
        Args:
            obj_content (str): Object content (e.g., "time:timestamp", "elapsed:duration")
            commands (List[str]): Object-specific commands at same position
            values (Tuple): Values tuple from user
            var_index (int): Current index in values tuple
            
        Returns:
            Tuple[str, int]: (formatted_text, new_var_index)
            
        Raises:
            InvalidObjectError: If object pattern is invalid
            UnsupportedObjectError: If object type is not supported
            ObjectProcessorError: If processing fails
        """
        self._processed_count += 1
        
        try:
            # Parse object content
            obj_type, obj_var = self._parse_object_content(obj_content)
            
            # Parse commands
            parsed_commands = self._parse_commands(commands)
            parsed_commands.validate()
            
            # Get value if needed
            value = None
            new_var_index = var_index
            
            if obj_var:  # Object has variable part
                if var_index >= len(values):
                    raise InvalidObjectError(f"No value provided for object variable '{obj_var}'")
                value = values[var_index]
                new_var_index = var_index + 1
            
            # Process based on object type
            if obj_type == 'time':
                result = self._process_time_object(value, parsed_commands)
            elif obj_type == 'date':
                result = self._process_date_object(value, parsed_commands)
            elif obj_type == 'datelong':
                result = self._process_datelong_object(value, parsed_commands)
            elif obj_type == 'elapsed':
                result = self._process_elapsed_object(value, parsed_commands)
            else:
                raise UnsupportedObjectError(f"Unsupported object type: {obj_type}")
            
            return result, new_var_index
            
        except Exception as e:
            self._error_count += 1
            if isinstance(e, (InvalidObjectError, UnsupportedObjectError, ObjectProcessorError)):
                raise
            else:
                raise ObjectProcessorError(f"Object processing failed: {e}")
    
    def _parse_object_content(self, obj_content: str) -> Tuple[str, str]:
        """Parse object content into type and variable."""
        if ':' not in obj_content:
            raise InvalidObjectError(f"Invalid object content: {obj_content}")
        
        obj_type, obj_var = obj_content.split(':', 1)
        obj_type = obj_type.strip()
        obj_var = obj_var.strip()
        
        # Validate object type
        valid_types = ['time', 'date', 'datelong', 'elapsed']
        if obj_type not in valid_types:
            raise UnsupportedObjectError(f"Unsupported object type: {obj_type}")
        
        return obj_type, obj_var
    
    def _parse_commands(self, commands: List[str]) -> _ObjectCommands:
        """Parse object-specific commands into structured format."""
        parsed = _ObjectCommands()
        
        for command in commands:
            command = command.strip()
            
            if command == '12hr':
                parsed.use_12hr = True
            elif command == 'no sec':
                parsed.hide_seconds = True
            elif command == 'time ago':
                if parsed.time_suffix == 'until':
                    raise InvalidObjectError("Cannot have both 'time ago' and 'time until'")
                parsed.time_suffix = 'ago'
            elif command == 'time until':
                if parsed.time_suffix == 'ago':
                    raise InvalidObjectError("Cannot have both 'time ago' and 'time until'")
                parsed.time_suffix = 'until'
            elif command == 'smart units 1':
                if parsed.smart_units is not None:
                    raise InvalidObjectError("Cannot specify multiple smart units commands")
                parsed.smart_units = 1
            elif command == 'smart units 2':
                if parsed.smart_units is not None:
                    raise InvalidObjectError("Cannot specify multiple smart units commands")
                parsed.smart_units = 2
            elif command == 'no hr':
                parsed.hide_hours = True
            elif command == 'no min':
                parsed.hide_minutes = True
            elif command == 'round sec':
                parsed.round_seconds = True
            elif command.startswith('tz '):
                if parsed.timezone is not None:
                    raise InvalidObjectError("Cannot specify multiple timezones")
                parsed.timezone = command[3:].strip()
            else:
                warnings.warn(f"Unknown object command ignored: {command}", UserWarning)
        
        return parsed
    
    def _format_12hr_time(self, time_struct: time.struct_time, hide_seconds: bool = False) -> str:
        """
        Format time in 12-hour format without leading zeros.
        
        Args:
            time_struct: Time structure from time.gmtime()
            hide_seconds: Whether to hide seconds
            
        Returns:
            str: Formatted 12-hour time (e.g., "4:00:00 PM")
        """
        hour = time_struct.tm_hour
        minute = time_struct.tm_min
        second = time_struct.tm_sec
        
        # Convert to 12-hour format
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
        
        # Format without leading zeros for hours
        if hide_seconds:
            return f"{display_hour}:{minute:02d} {ampm}"
        else:
            return f"{display_hour}:{minute:02d}:{second:02d} {ampm}"
    
    def _process_time_object(self, timestamp: Optional[float], commands: _ObjectCommands) -> str:
        """
        Process time object: <time:> or <time:timestamp>
        
        Time objects show absolute time only. time ago/until commands are invalid and ignored.
        """
        # Get timestamp (current time if None)
        if timestamp is None:
            timestamp = time.time()
        
        # Warn about invalid time ago/until commands for time objects
        if commands.time_suffix:
            warnings.warn(f"'{commands.time_suffix}' command only works with elapsed objects, not time objects", UserWarning)
        
        # Apply timezone conversion if specified
        if commands.timezone:
            adjusted_timestamp = self.timezone_handler.convert_timestamp(timestamp, commands.timezone)
        else:
            adjusted_timestamp = timestamp
        
        # Convert to time components using time.gmtime() (avoids local timezone issues)
        time_struct = time.gmtime(adjusted_timestamp)
        
        # Format time (never add suffixes - time objects show absolute time only)
        if commands.use_12hr:
            time_str = self._format_12hr_time(time_struct, commands.hide_seconds)
        else:
            if commands.hide_seconds:
                time_str = time.strftime('%H:%M', time_struct)
            else:
                # Include fractional seconds
                microseconds = int((adjusted_timestamp % 1) * 1000000)
                base_time = time.strftime('%H:%M:%S', time_struct)
                time_str = f"{base_time}.{microseconds:06d}"
        
        return time_str
    
    def _process_date_object(self, timestamp: Optional[float], commands: _ObjectCommands) -> str:
        """
        Process date object: <date:> or <date:timestamp>
        """
        # Get timestamp (current time if None)
        if timestamp is None:
            timestamp = time.time()
        
        # Warn about invalid time ago/until commands for date objects
        if commands.time_suffix:
            warnings.warn(f"'{commands.time_suffix}' command only works with elapsed objects, not date objects", UserWarning)
        
        # Apply timezone conversion if specified
        if commands.timezone:
            adjusted_timestamp = self.timezone_handler.convert_timestamp(timestamp, commands.timezone)
        else:
            adjusted_timestamp = timestamp
        
        # Convert to time components using time.gmtime()
        time_struct = time.gmtime(adjusted_timestamp)
        
        # Format as date with time (never add suffixes - date objects show absolute date/time only)
        if commands.use_12hr:
            if commands.hide_seconds:
                date_str = time.strftime('%d/%m/%y ', time_struct) + self._format_12hr_time(time_struct, True)
            else:
                date_str = time.strftime('%d/%m/%y ', time_struct) + self._format_12hr_time(time_struct, False)
        else:
            if commands.hide_seconds:
                date_str = time.strftime('%d/%m/%y %H:%M', time_struct)
            else:
                date_str = time.strftime('%d/%m/%y %H:%M:%S', time_struct)
        
        return date_str
    
    def _process_datelong_object(self, timestamp: Optional[float], commands: _ObjectCommands) -> str:
        """
        Process datelong object: <datelong:> or <datelong:timestamp>
        """
        # Get timestamp (current time if None)
        if timestamp is None:
            timestamp = time.time()
        
        # Warn about invalid time ago/until commands for datelong objects
        if commands.time_suffix:
            warnings.warn(f"'{commands.time_suffix}' command only works with elapsed objects, not datelong objects", UserWarning)
        
        # Apply timezone conversion if specified
        if commands.timezone:
            adjusted_timestamp = self.timezone_handler.convert_timestamp(timestamp, commands.timezone)
        else:
            adjusted_timestamp = timestamp
        
        # Convert to time components using time.gmtime()
        time_struct = time.gmtime(adjusted_timestamp)
        
        # Format as long date (never add suffixes - datelong objects show absolute date only)
        date_str = time.strftime('%B %d, %Y', time_struct)
        
        return date_str
    
    def _process_elapsed_object(self, timestamp: Optional[float], commands: _ObjectCommands) -> str:
        """
        Process elapsed object: <elapsed:> or <elapsed:timestamp>
        
        Takes a timestamp and calculates elapsed time from then to now.
        Format: "3d 2h 15m 30s" (only shows non-zero units)
        
        For "time until" commands, uses absolute value to handle future timestamps correctly.
        New smart formatting options control which units are displayed.
        """
        # Get timestamp (current time if None, which results in 0 elapsed)
        if timestamp is None:
            timestamp = time.time()
        
        # Calculate elapsed time from timestamp to now
        current_time = time.time()
        duration = current_time - timestamp
        
        # For "time until", use absolute value to handle future timestamps
        if commands.time_suffix == 'until':
            abs_duration = abs(duration)
        else:
            abs_duration = abs(duration)  # Always use abs for display
        
        # Calculate days, hours, minutes, seconds
        days = int(abs_duration // 86400)
        remaining = abs_duration % 86400
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        seconds = remaining % 60
        
        # Apply rounding to seconds if requested
        if commands.round_seconds:
            seconds = round(seconds)
        
        # Build parts list based on command precedence
        parts = self._build_elapsed_parts(days, hours, minutes, seconds, commands)
        
        # Ensure we have at least something to display
        if not parts:
            if commands.hide_seconds or commands.round_seconds:
                parts = ["0m"]
            else:
                parts = ["0.000000s"]
        
        elapsed_str = " ".join(parts)
        
        # Add suffix if specified
        if commands.time_suffix:
            elapsed_str += f" {commands.time_suffix}"
        
        return elapsed_str
    
    def _build_elapsed_parts(self, days: int, hours: int, minutes: int, seconds: float, 
                           commands: _ObjectCommands) -> List[str]:
        """
        Build the parts list for elapsed display based on commands.
        
        Args:
            days, hours, minutes, seconds: Calculated time units
            commands: Parsed commands controlling display
            
        Returns:
            List[str]: Parts to join for final display
        """
        # Handle restrictive display modes first
        if commands.hide_hours:
            # Only show days
            if days > 0:
                return [f"{days}d"]
            else:
                return []  # Will be handled by caller
        
        if commands.hide_minutes:
            # Show days and hours only
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            return parts
        
        # Handle smart units (show only N highest non-zero units)
        if commands.smart_units is not None:
            return self._build_smart_units_parts(days, hours, minutes, seconds, 
                                               commands.smart_units, commands)
        
        # Normal display logic
        return self._build_normal_parts(days, hours, minutes, seconds, commands)
    
    def _build_smart_units_parts(self, days: int, hours: int, minutes: int, seconds: float,
                                num_units: int, commands: _ObjectCommands) -> List[str]:
        """Build parts for smart units display (show only N highest units)."""
        # Create list of all non-zero units in descending order
        all_units = []
        
        if days > 0:
            all_units.append(f"{days}d")
        if hours > 0:
            all_units.append(f"{hours}h")
        if minutes > 0:
            all_units.append(f"{minutes}m")
        
        # Handle seconds based on commands
        if not commands.hide_seconds and seconds > 0:
            if commands.round_seconds:
                all_units.append(f"{int(seconds)}s")
            else:
                all_units.append(f"{seconds:.6f}s")
        
        # Return only the requested number of highest units
        return all_units[:num_units]
    
    def _build_normal_parts(self, days: int, hours: int, minutes: int, seconds: float,
                           commands: _ObjectCommands) -> List[str]:
        """Build parts for normal display (show all non-zero units)."""
        parts = []
        
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        # Handle seconds
        if not commands.hide_seconds and (seconds > 0 or len(parts) == 0):
            if commands.round_seconds:
                parts.append(f"{int(seconds)}s")
            else:
                parts.append(f"{seconds:.6f}s")
        elif commands.hide_seconds and len(parts) == 0:
            # If hiding seconds but no other units, show 0m
            parts.append("0m")
        
        return parts
    
    def get_performance_stats(self) -> Dict[str, int]:
        """Get performance statistics."""
        return {
            'objects_processed': self._processed_count,
            'processing_errors': self._error_count,
            'success_rate': (self._processed_count - self._error_count) / max(self._processed_count, 1)
        }


# Global object processor instance
_global_object_processor: Optional[_ObjectProcessor] = None


def _get_object_processor() -> _ObjectProcessor:
    """Get the global object processor instance."""
    global _global_object_processor
    if _global_object_processor is None:
        _global_object_processor = _ObjectProcessor()
    return _global_object_processor


def _set_auto_dst(enabled: bool) -> None:
    """Enable or disable automatic daylight savings handling."""
    global _global_object_processor
    if _global_object_processor is not None:
        _global_object_processor.timezone_handler.auto_dst = enabled


# Test script for Object Processor
if __name__ == "__main__":

    warnings.simplefilter("always")  # Show all warnings, even duplicates

    def test_object_processor():
        """Comprehensive test suite for the object processor."""
        
        print("=" * 60)
        print("OBJECT PROCESSOR TEST SUITE")
        print("=" * 60)
        
        processor = _ObjectProcessor()
        test_count = 0
        passed_count = 0
        
        def run_test(name: str, test_func):
            """Run a single test case."""
            nonlocal test_count, passed_count
            test_count += 1
            
            print(f"\nTest {test_count}: {name}")
            
            try:
                passed = test_func(processor)
                if passed:
                    print("✅ PASSED")
                    passed_count += 1
                else:
                    print("❌ FAILED")
                    
            except Exception as e:
                print(f"❌ EXCEPTION: {e}")
                import traceback
                traceback.print_exc()
                
            print("-" * 40)
        
        # Test 1: Basic time objects
        def test_basic_time(proc):
            # Test current time
            result, new_idx = proc.process_object("time:", [], (), 0)
            if not re.match(r'\d{2}:\d{2}:\d{2}\.\d{6}', result):
                print(f"❌ Current time format invalid: '{result}'")
                return False
            
            # Test specific timestamp
            timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
            result, new_idx = proc.process_object("time:ts", [], (timestamp,), 0)
            if new_idx != 1:
                print(f"❌ Variable index not incremented: {new_idx}")
                return False
            
            print(f"✓ Basic time: '{result}'")
            return True
        
        # Test 2: Time with 12hr format (should be "4:00:00 PM")
        def test_12hr_time(proc):
            timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
            result, _ = proc.process_object("time:ts", ["12hr"], (timestamp,), 0)
            
            # Should be "12:00:00 AM" (no leading zero, midnight UTC)
            if not result.startswith("12:00:00 AM"):
                print(f"❌ 12hr format incorrect: '{result}' (expected '12:00:00 AM')")
                return False
            
            print(f"✓ 12hr time: '{result}'")
            return True
        
        # Test 3: Time with timezone
        def test_timezone_time(proc):
            timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
            result, _ = proc.process_object("time:ts", ["tz pst"], (timestamp,), 0)
            
            # PST is UTC-8, so should be 16:00:00 on Dec 31, 2021
            if not result.startswith("16:00:00"):
                print(f"❌ Timezone conversion incorrect: '{result}' (expected '16:00:00')")
                return False
            
            print(f"✓ Timezone time: '{result}'")
            return True
        
        # Test 4: Date objects
        def test_date_objects(proc):
            timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
            
            # Regular date (UTC)
            result, _ = proc.process_object("date:ts", [], (timestamp,), 0)
            if not re.match(r'\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}', result):
                print(f"❌ Date format invalid: '{result}'")
                return False
            
            # Long date (UTC) - should be January 01, 2022
            result, _ = proc.process_object("datelong:ts", [], (timestamp,), 0)
            if "January 01, 2022" not in result:
                print(f"❌ Long date format invalid: '{result}' (expected 'January 01, 2022')")
                return False
            
            print(f"✓ Date objects: '{result}'")
            return True
        
        # Test 5: Elapsed objects with timestamps
        def test_elapsed_objects(proc):
            # Test with a timestamp 2 hours and 17 minutes ago
            hours_ago_timestamp = time.time() - 8274.0  # About 2:17:54 ago
            result, _ = proc.process_object("elapsed:ts", [], (hours_ago_timestamp,), 0)
            
            # Should show something like "2h 17m 54s" 
            if "h" not in result or "m" not in result:
                print(f"❌ Elapsed format should show hours and minutes: '{result}'")
                return False
            
            # Test with current time (should be very small elapsed)
            current_timestamp = time.time()
            result, _ = proc.process_object("elapsed:ts", [], (current_timestamp,), 0)
            
            # Should show seconds or be very small
            if not ("s" in result or "0m" in result):
                print(f"❌ Current time elapsed should show seconds or 0m: '{result}'")
                return False
            
            print(f"✓ Elapsed objects with timestamps: recent='{result}'")
            return True
        
        # Test 6: Time suffixes (should warn and ignore for time objects)
        def test_time_suffixes(proc):
            timestamp = 1640995200.0
            
            # Time ago with time object - should warn and ignore suffix
            result, _ = proc.process_object("time:ts", ["time ago"], (timestamp,), 0)
            if result.endswith(" ago"):
                print(f"❌ Time ago should be ignored for time objects: '{result}'")
                return False
            
            # Should show just the absolute time
            if "00:00:00" not in result:
                print(f"❌ Should show absolute time: '{result}'")
                return False
            
            print(f"✓ Time suffixes correctly ignored for time objects: '{result}'")
            return True
        
        # Test 7a: Complex combinations (with time object)
        def test_complex_combinations(proc):
            # Use a timestamp that's exactly 4 hours ago for predictable testing
            four_hours_ago = time.time() - (4 * 3600)  # 4 hours ago
            commands = ["12hr", "tz pst", "time ago", "no sec"]
            
            result, _ = proc.process_object("time:ts", commands, (four_hours_ago,), 0)
            
            # Should show "4 hours ago" (not absolute time)
            if "hours ago" in result:
                print(f"❌ Should not show 'hours ago' because not an <elapsed:obj> object: '{result}'")
                return False
            
            print(f"✓ Complex combination: '{result}'")
            return True
        
        # Test 7b: Complex combinations (with elapsed object)
        def test_complex_combinations2(proc):
            # Use a timestamp that's exactly 4 hours ago for predictable testing
            four_hours_ago = time.time() - (4 * 3600)  # 4 hours ago
            commands = ["12hr", "tz pst", "time ago", "no sec"]
            
            result, _ = proc.process_object("elapsed:ts", commands, (four_hours_ago,), 0)
            
            # Should show "4 hours ago" (not absolute time)
            if "h ago" not in result:
                print(f"❌ Should show 'hours ago' because this is an <elapsed:obj> object: '{result}'")
                return False
            
            print(f"✓ Complex combination: '{result}'")
            return True
        
        # Test 8: Error handling
        def test_error_handling(proc):
            try:
                # Invalid object type
                proc.process_object("invalid:ts", [], (1234,), 0)
                print("❌ Should have raised UnsupportedObjectError")
                return False
            except UnsupportedObjectError:
                pass  # Expected
            
            try:
                # Missing value for object variable
                proc.process_object("time:ts", [], (), 0)
                print("❌ Should have raised InvalidObjectError")
                return False
            except InvalidObjectError:
                pass  # Expected
            
            try:
                # Conflicting time suffixes
                proc.process_object("time:ts", ["time ago", "time until"], (1234,), 0)
                print("❌ Should have raised InvalidObjectError")
                return False
            except InvalidObjectError:
                pass  # Expected
            
            print("✓ Error handling works")
            return True
        
        # Test 9: New smart formatting commands
        def test_smart_formatting(proc):
            # Test duration: 2 days, 3 hours, 15 minutes, 30 seconds
            duration = (2 * 86400) + (3 * 3600) + (15 * 60) + 30
            test_timestamp = time.time() - duration
            
            # Test smart units 1 (only highest unit)
            result, _ = proc.process_object("elapsed:ts", ["smart units 1"], (test_timestamp,), 0)
            if "d" not in result or "h" in result or "m" in result:
                print(f"❌ Smart units 1 failed: '{result}' (should only show days)")
                return False
            
            # Test smart units 2 (2 highest units)
            result, _ = proc.process_object("elapsed:ts", ["smart units 2"], (test_timestamp,), 0)
            if "d" not in result or "h" not in result or "m" in result:
                print(f"❌ Smart units 2 failed: '{result}' (should show days and hours)")
                return False
            
            # Test no hr (only days)
            result, _ = proc.process_object("elapsed:ts", ["no hr"], (test_timestamp,), 0)
            if "d" not in result or "h" in result:
                print(f"❌ No hr failed: '{result}' (should only show days)")
                return False
            
            # Test no min (days and hours only)
            result, _ = proc.process_object("elapsed:ts", ["no min"], (test_timestamp,), 0)
            if "d" not in result or "h" not in result or "m" in result:
                print(f"❌ No min failed: '{result}' (should show days and hours only)")
                return False
            
            # Test round sec (no decimals)
            short_duration = 65.789  # 1 minute, 5.789 seconds
            short_timestamp = time.time() - short_duration
            result, _ = proc.process_object("elapsed:ts", ["round sec"], (short_timestamp,), 0)
            if "." in result:
                print(f"❌ Round sec failed: '{result}' (should have no decimals)")
                return False
            
            print(f"✓ Smart formatting commands work")
            return True
        
        # Run all tests
        run_test("Basic time objects", test_basic_time)
        run_test("12-hour time format", test_12hr_time)
        run_test("Timezone conversion", test_timezone_time)
        run_test("Date objects", test_date_objects)
        run_test("Elapsed objects with timestamps", test_elapsed_objects)
        run_test("Time suffixes", test_time_suffixes)
        run_test("Complex command combinations", test_complex_combinations)
        run_test("Complex command combinations 2", test_complex_combinations2)
        run_test("Error handling", test_error_handling)
        run_test("Smart formatting commands", test_smart_formatting)
        run_test("Smart formatting commands", test_smart_formatting)
        
        print("\n" + "=" * 60)
        print(f"TEST RESULTS: {passed_count}/{test_count} tests passed")
        if passed_count == test_count:
            print("🎉 ALL TESTS PASSED!")
            print("\n📊 PERFORMANCE STATS:")
            stats = processor.get_performance_stats()
            print(f"Objects processed: {stats['objects_processed']}")
            print(f"Processing errors: {stats['processing_errors']}")
            print(f"Success rate: {stats['success_rate']:.2%}")
        else:
            print(f"❌ {test_count - passed_count} tests failed")
        print("=" * 60)
        
        return passed_count == test_count
    
    # Run the tests
    test_object_processor()