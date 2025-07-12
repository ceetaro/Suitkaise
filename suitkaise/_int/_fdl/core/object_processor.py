"""
Object Processor for fdl - Time, Date, and Elapsed Object Handling

This module provides concrete object processing for fdl's time/date/elapsed patterns.
Handles object-specific commands like timezone, 12-hour format, and time suffixes.

Supported Objects:
- <time:> / <time:timestamp> - Time formatting
- <date:> / <date:timestamp> - Date formatting  
- <datelong:> / <datelong:timestamp> - Long date format
- <elapsed:duration> - Elapsed time formatting
- <elapsed2:duration> - Alternative elapsed format
- <timeprefix:duration> - Time unit names

Supported Commands:
- 12hr - 12-hour format
- tz <timezone> - Timezone conversion with DST
- time ago / time until - Time suffixes  
- no sec - Remove seconds from display
"""

import time
import warnings
from datetime import datetime, timezone, timedelta
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
    """
    use_12hr: bool = False
    timezone: Optional[str] = None
    time_suffix: Optional[str] = None
    hide_seconds: bool = False
    
    def validate(self) -> None:
        """Validate command combination for conflicts."""
        # Can't have both time ago and time until
        if self.time_suffix not in [None, 'ago', 'until']:
            raise InvalidObjectError(f"Invalid time suffix: {self.time_suffix}")


class _TimeZoneHandler:
    """
    Handles timezone conversion with daylight savings support using float timestamps.
    
    Works purely with Unix timestamps (floats) for maximum performance and simplicity.
    Supports automatic daylight savings time conversion for supported timezones.
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
        # Cache for timezone conversions
        self._offset_cache: Dict[Tuple[str, float], float] = {}
    
    def convert_timestamp(self, timestamp: float, target_tz: str) -> float:
        """
        Convert Unix timestamp to target timezone, returning adjusted timestamp.
        
        Args:
            timestamp (float): Unix timestamp (UTC)
            target_tz (str): Target timezone (e.g., 'pst', 'America/Los_Angeles')
            
        Returns:
            float: Adjusted timestamp for target timezone
            
        Raises:
            ObjectProcessorError: If timezone conversion fails
            
        The returned timestamp can be used with time.strftime() or similar
        functions to get the correct local time representation.
        """
        try:
            # Check cache first (rounded to minute for efficiency)
            cache_key = (target_tz.lower(), int(timestamp // 60) * 60)
            if cache_key in self._offset_cache:
                cached_offset = self._offset_cache[cache_key]
                return timestamp + cached_offset
            
            # Normalize timezone name
            tz_name = self._normalize_timezone(target_tz)
            
            # Handle UTC special case
            if tz_name == 'UTC':
                return timestamp
            
            # Calculate timezone offset using datetime temporarily for conversion
            # but return pure float
            utc_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
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
            
            # Return adjusted timestamp
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
    formatted time/date/elapsed strings.
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
            
        Example:
            # <time:login_time> with commands ["12hr", "tz pst"]
            result, new_idx = processor.process_object(
                "time:login_time", ["12hr", "tz pst"], (1640995200,), 0
            )
            # Returns: ("6:00 PM", 1)
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
            elif obj_type == 'elapsed2':
                result = self._process_elapsed2_object(value, parsed_commands)
            elif obj_type == 'timeprefix':
                result = self._process_timeprefix_object(value, parsed_commands)
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
        """
        Parse object content into type and variable.
        
        Args:
            obj_content (str): Object content like "time:timestamp" or "elapsed:"
            
        Returns:
            Tuple[str, str]: (object_type, variable_name)
        """
        if ':' not in obj_content:
            raise InvalidObjectError(f"Invalid object content: {obj_content}")
        
        obj_type, obj_var = obj_content.split(':', 1)
        obj_type = obj_type.strip()
        obj_var = obj_var.strip()
        
        # Validate object type
        valid_types = ['time', 'date', 'datelong', 'elapsed', 'elapsed2', 'timeprefix']
        if obj_type not in valid_types:
            raise UnsupportedObjectError(f"Unsupported object type: {obj_type}")
        
        return obj_type, obj_var
    
    def _parse_commands(self, commands: List[str]) -> _ObjectCommands:
        """
        Parse object-specific commands into structured format.
        
        Args:
            commands (List[str]): List of command strings
            
        Returns:
            _ObjectCommands: Parsed command structure
        """
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
            elif command.startswith('tz '):
                if parsed.timezone is not None:
                    raise InvalidObjectError("Cannot specify multiple timezones")
                parsed.timezone = command[3:].strip()
            else:
                warnings.warn(f"Unknown object command ignored: {command}", UserWarning)
        
        return parsed
    
    def _process_time_object(self, timestamp: Optional[float], commands: _ObjectCommands) -> str:
        """
        Process time object: <time:> or <time:timestamp>
        
        Args:
            timestamp (Optional[float]): Unix timestamp or None for current time
            commands (_ObjectCommands): Parsed commands
            
        Returns:
            str: Formatted time string
        """
        # Get timestamp (current time if None)
        if timestamp is None:
            timestamp = time.time()
        
        # Apply timezone conversion if specified
        if commands.timezone:
            adjusted_timestamp = self.timezone_handler.convert_timestamp(timestamp, commands.timezone)
        else:
            adjusted_timestamp = timestamp
        
        # Convert to time components using adjusted timestamp
        time_struct = time.localtime(adjusted_timestamp)
        
        # Format time
        if commands.use_12hr:
            if commands.hide_seconds:
                time_str = time.strftime('%I:%M %p', time_struct)
            else:
                time_str = time.strftime('%I:%M:%S %p', time_struct)
        else:
            if commands.hide_seconds:
                time_str = time.strftime('%H:%M', time_struct)
            else:
                # Include fractional seconds
                microseconds = int((adjusted_timestamp % 1) * 1000000)
                base_time = time.strftime('%H:%M:%S', time_struct)
                time_str = f"{base_time}.{microseconds:06d}"
        
        # Add suffix if specified
        if commands.time_suffix:
            time_str += f" {commands.time_suffix}"
        
        return time_str
    
    def _process_date_object(self, timestamp: Optional[float], commands: _ObjectCommands) -> str:
        """
        Process date object: <date:> or <date:timestamp>
        
        Args:
            timestamp (Optional[float]): Unix timestamp or None for current time
            commands (_ObjectCommands): Parsed commands
            
        Returns:
            str: Formatted date string (dd/mm/yy hh:mm:ss format)
        """
        # Get timestamp (current time if None)
        if timestamp is None:
            timestamp = time.time()
        
        # Apply timezone conversion if specified
        if commands.timezone:
            adjusted_timestamp = self.timezone_handler.convert_timestamp(timestamp, commands.timezone)
        else:
            adjusted_timestamp = timestamp
        
        # Convert to time components using adjusted timestamp
        time_struct = time.localtime(adjusted_timestamp)
        
        # Format as date with time
        if commands.use_12hr:
            if commands.hide_seconds:
                date_str = time.strftime('%d/%m/%y %I:%M %p', time_struct)
            else:
                date_str = time.strftime('%d/%m/%y %I:%M:%S %p', time_struct)
        else:
            if commands.hide_seconds:
                date_str = time.strftime('%d/%m/%y %H:%M', time_struct)
            else:
                date_str = time.strftime('%d/%m/%y %H:%M:%S', time_struct)
        
        # Add suffix if specified
        if commands.time_suffix:
            date_str += f" {commands.time_suffix}"
        
        return date_str
    
    def _process_datelong_object(self, timestamp: Optional[float], commands: _ObjectCommands) -> str:
        """
        Process datelong object: <datelong:> or <datelong:timestamp>
        
        Args:
            timestamp (Optional[float]): Unix timestamp or None for current time
            commands (_ObjectCommands): Parsed commands
            
        Returns:
            str: Formatted long date string (e.g., "July 4, 2025")
        """
        # Get timestamp (current time if None)
        if timestamp is None:
            timestamp = time.time()
        
        # Apply timezone conversion if specified
        if commands.timezone:
            adjusted_timestamp = self.timezone_handler.convert_timestamp(timestamp, commands.timezone)
        else:
            adjusted_timestamp = timestamp
        
        # Convert to time components using adjusted timestamp
        time_struct = time.localtime(adjusted_timestamp)
        
        # Format as long date
        date_str = time.strftime('%B %d, %Y', time_struct)
        
        # Add suffix if specified (though unusual for long dates)
        if commands.time_suffix:
            date_str += f" {commands.time_suffix}"
        
        return date_str
    
    def _process_elapsed_object(self, duration: float, commands: _ObjectCommands) -> str:
        """
        Process elapsed object: <elapsed:duration>
        
        Args:
            duration (float): Duration in seconds
            commands (_ObjectCommands): Parsed commands
            
        Returns:
            str: Formatted elapsed time (e.g., "2:17:54.123456")
        """
        if duration is None:
            raise InvalidObjectError("Elapsed objects require a duration value")
        
        # Convert to absolute value (handle negative durations)
        abs_duration = abs(float(duration))
        
        # Calculate hours, minutes, seconds
        hours = int(abs_duration // 3600)
        minutes = int((abs_duration % 3600) // 60)
        seconds = abs_duration % 60
        
        # Format based on commands
        if commands.hide_seconds:
            elapsed_str = f"{hours}:{minutes:02d}"
        else:
            # Include fractional seconds
            elapsed_str = f"{hours}:{minutes:02d}:{seconds:09.6f}"
        
        # Add suffix if specified
        if commands.time_suffix:
            elapsed_str += f" {commands.time_suffix}"
        
        return elapsed_str
    
    def _process_elapsed2_object(self, duration: float, commands: _ObjectCommands) -> str:
        """
        Process elapsed2 object: <elapsed2:duration>
        
        Args:
            duration (float): Duration in seconds
            commands (_ObjectCommands): Parsed commands
            
        Returns:
            str: Alternative elapsed format (e.g., "22h 46m 40.000000s")
        """
        if duration is None:
            raise InvalidObjectError("Elapsed2 objects require a duration value")
        
        # Convert to absolute value
        abs_duration = abs(float(duration))
        
        # Calculate hours, minutes, seconds
        hours = int(abs_duration // 3600)
        minutes = int((abs_duration % 3600) // 60)
        seconds = abs_duration % 60
        
        # Format in alternative style
        if commands.hide_seconds:
            elapsed_str = f"{hours}h {minutes}m"
        else:
            elapsed_str = f"{hours}h {minutes}m {seconds:.6f}s"
        
        # Add suffix if specified
        if commands.time_suffix:
            elapsed_str += f" {commands.time_suffix}"
        
        return elapsed_str
    
    def _process_timeprefix_object(self, duration: float, commands: _ObjectCommands) -> str:
        """
        Process timeprefix object: <timeprefix:duration>
        
        Args:
            duration (float): Duration in seconds
            commands (_ObjectCommands): Parsed commands
            
        Returns:
            str: Time unit name (e.g., "hours", "minutes", "seconds")
        """
        if duration is None:
            raise InvalidObjectError("Timeprefix objects require a duration value")
        
        # Convert to absolute value
        abs_duration = abs(float(duration))
        
        # Determine primary unit
        if abs_duration >= 3600:
            return "hours"
        elif abs_duration >= 60:
            return "minutes"
        else:
            return "seconds"
    
    def get_performance_stats(self) -> Dict[str, int]:
        """
        Get performance statistics.
        
        Returns:
            Dict[str, int]: Processing statistics
        """
        return {
            'objects_processed': self._processed_count,
            'processing_errors': self._error_count,
            'success_rate': (self._processed_count - self._error_count) / max(self._processed_count, 1)
        }


# Global object processor instance
_global_object_processor: Optional[_ObjectProcessor] = None


def _get_object_processor() -> _ObjectProcessor:
    """
    Get the global object processor instance.
    
    Returns:
        _ObjectProcessor: Global processor instance
        
    Creates the processor on first call, returns cached instance afterward.
    """
    global _global_object_processor
    if _global_object_processor is None:
        _global_object_processor = _ObjectProcessor()
    return _global_object_processor


def set_auto_dst(enabled: bool) -> None:
    """
    Enable or disable automatic daylight savings handling.
    
    Args:
        enabled (bool): Whether to automatically handle DST
    """
    global _global_object_processor
    if _global_object_processor is not None:
        _global_object_processor.timezone_handler.auto_dst = enabled
    # If processor doesn't exist yet, it will use the default when created


# Test script for Object Processor
if __name__ == "__main__":
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
            if not re.match(r'\d{2}:\d{2}:\d{2}\.\d{3}', result):
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
        
        # Test 2: Time with 12hr format
        def test_12hr_time(proc):
            timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
            result, _ = proc.process_object("time:ts", ["12hr"], (timestamp,), 0)
            
            if "AM" not in result and "PM" not in result:
                print(f"❌ 12hr format missing AM/PM: '{result}'")
                return False
            
            print(f"✓ 12hr time: '{result}'")
            return True
        
        # Test 3: Time with timezone
        def test_timezone_time(proc):
            timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
            result, _ = proc.process_object("time:ts", ["tz pst"], (timestamp,), 0)
            
            # PST is UTC-8, so should be 16:00:00 on Dec 31, 2021
            if "16:00:00" not in result:
                print(f"❌ Timezone conversion incorrect: '{result}'")
                return False
            
            print(f"✓ Timezone time: '{result}'")
            return True
        
        # Test 4: Date objects
        def test_date_objects(proc):
            timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
            
            # Regular date
            result, _ = proc.process_object("date:ts", [], (timestamp,), 0)
            if not re.match(r'\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}', result):
                print(f"❌ Date format invalid: '{result}'")
                return False
            
            # Long date
            result, _ = proc.process_object("datelong:ts", [], (timestamp,), 0)
            if "January 01, 2022" not in result:
                print(f"❌ Long date format invalid: '{result}'")
                return False
            
            print(f"✓ Date objects: '{result}'")
            return True
        
        # Test 5: Elapsed objects
        def test_elapsed_objects(proc):
            duration = 8274.743462  # 2:17:54.743462
            
            # Regular elapsed
            result, _ = proc.process_object("elapsed:dur", [], (duration,), 0)
            if not result.startswith("2:17:54"):
                print(f"❌ Elapsed format invalid: '{result}'")
                return False
            
            # Alternative elapsed
            result, _ = proc.process_object("elapsed2:dur", [], (duration,), 0)
            if not result.startswith("2h 17m"):
                print(f"❌ Elapsed2 format invalid: '{result}'")
                return False
            
            print(f"✓ Elapsed objects: '{result}'")
            return True
        
        # Test 6: Time prefix
        def test_timeprefix(proc):
            # Hours
            result, _ = proc.process_object("timeprefix:dur", [], (7200,), 0)  # 2 hours
            if result != "hours":
                print(f"❌ Hours prefix wrong: '{result}'")
                return False
            
            # Minutes  
            result, _ = proc.process_object("timeprefix:dur", [], (120,), 0)  # 2 minutes
            if result != "minutes":
                print(f"❌ Minutes prefix wrong: '{result}'")
                return False
            
            # Seconds
            result, _ = proc.process_object("timeprefix:dur", [], (30,), 0)  # 30 seconds
            if result != "seconds":
                print(f"❌ Seconds prefix wrong: '{result}'")
                return False
            
            print(f"✓ Time prefixes work")
            return True
        
        # Test 7: Time suffixes
        def test_time_suffixes(proc):
            timestamp = 1640995200.0
            
            # Time ago
            result, _ = proc.process_object("time:ts", ["time ago"], (timestamp,), 0)
            if not result.endswith(" ago"):
                print(f"❌ Time ago suffix missing: '{result}'")
                return False
            
            # Time until
            result, _ = proc.process_object("time:ts", ["time until"], (timestamp,), 0)
            if not result.endswith(" until"):
                print(f"❌ Time until suffix missing: '{result}'")
                return False
            
            print(f"✓ Time suffixes work")
            return True
        
        # Test 8: Complex combinations
        def test_complex_combinations(proc):
            timestamp = 1640995200.0
            commands = ["12hr", "tz pst", "time ago", "no sec"]
            
            result, _ = proc.process_object("time:ts", commands, (timestamp,), 0)
            
            # Should have 12hr format (AM/PM)
            if "AM" not in result and "PM" not in result:
                print(f"❌ Missing 12hr format")
                return False
            
            # Should have ago suffix
            if not result.endswith(" ago"):
                print(f"❌ Missing ago suffix")
                return False
            
            # Should not have seconds (due to no sec)
            if re.search(r':\d{2}\s', result):  # seconds pattern
                print(f"❌ Seconds not hidden: '{result}'")
                return False
            
            print(f"✓ Complex combination: '{result}'")
            return True
        
        # Test 9: Error handling
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
        
        # Run all tests
        run_test("Basic time objects", test_basic_time)
        run_test("12-hour time format", test_12hr_time)
        run_test("Timezone conversion", test_timezone_time)
        run_test("Date objects", test_date_objects)
        run_test("Elapsed objects", test_elapsed_objects)
        run_test("Time prefix objects", test_timeprefix)
        run_test("Time suffixes", test_time_suffixes)
        run_test("Complex command combinations", test_complex_combinations)
        run_test("Error handling", test_error_handling)
        
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