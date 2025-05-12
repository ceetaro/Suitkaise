# -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0 or the GNU General Public License v3.
#
# ~~ Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
#
# ~~ GNU General Public License, Version 3 (http://www.gnu.org/licenses/gpl-3.0.html)
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -------------------------------------------------------------------------------------

# suitkaise/int/time/sktime.py

"""
Time utilities for the project.

Use sktime.setup_time() to set up time for the project.

Additionally, using sktime.now() instead of time.time() is recommended for 
clarity and uniformity.

"""
import datetime
import time
from typing import Optional, Union, Any, Dict, Type
from enum import Enum, auto
from zoneinfo import ZoneInfo

# datetime objects, iso format strings, and floats
TimeValue = Union[datetime.datetime, str, float, int]

# ========= TIME INITIALIZATION =========================================

def setup_time():
    """
    Set globals start_time and timezone.

    Call right at the beginning of the program.
    
    """
    # set start time
    set_start_time()

    # set timezone
    set_timezone(Timezone.PST)

    # print start time
    st = get_start_time()
    print(f"Start time: "
          f"{to_custom_time_format(st, CustomTime.YMD_HMS6)}")

    # print current timezone
    print(f"Current timezone: {current_timezone_str()}")

    # set the global yawns dictionary
    set_yawns_global()


# ========================================================================


class CustomTime(Enum):
    """
    Enum for custom time formats.

    Use with to_custom_time_format().

    """
    YMD_HMS6 = "%Y-%m-%d %H:%M:%S.%f" # 2025-12-25 12:00:00.000000

class CustomTimeDiff(Enum):
    """
    Enum for custom time difference formats.

    Use with to_custom_time_diff_format().

    """
    # 0h 0m 0.000000s
    HMS6 = "{hours}h {minutes}m {seconds}.{microseconds}s"
    # 0hrs 0mins 0.000000secs
    HMS6_2 = "{hours}hrs {minutes}mins {seconds}.{microseconds}secs"
    # 0h 0m 0s
    HMS = "{hours}h {minutes}m {seconds}s"
    # 0hrs 0mins 0secs
    HMS_2 = "{hours}hrs {minutes}mins {seconds}secs"
    # 0h 0m 0.0000000000s
    HMS10 = "{hours}h {minutes}m {seconds}.{nanoseconds}s"
    # 0hrs 0mins 0.0000000000secs
    HMS10_2 = "{hours}hrs {minutes}mins {seconds}.{nanoseconds}secs"
    # 0.0000000000s
    S10 = "{seconds}.{nanoseconds}s"
    # 0.0000000000secs
    S10_2 = "{seconds}.{nanoseconds}secs"
    # 0.000000s
    S6 = "{seconds}.{microseconds}s"
    # 0.000000secs
    S6_2 = "{seconds}.{microseconds}secs"



# ========== TIMEZONE ================================================

class Timezone(Enum):
    """
    Enum for timezone values.

    Current supported timezones:
    - UTC

    - US timezones:
        - EST (Eastern Standard Time)
        - CST (Central Standard Time)
        - MST (Mountain Standard Time)
        - PST (Pacific Standard Time)

    
    """
    UTC = ZoneInfo("UTC")
    EST = ZoneInfo("America/New_York")
    CST = ZoneInfo("America/Chicago")
    MST = ZoneInfo("America/Denver")
    PST = ZoneInfo("America/Los_Angeles")


def set_timezone(tz: Timezone) -> None:
    """
    Set the timezone for the project.

    All created time objects will assume this timezone,
    if applicable.

    Args:
        timezone: The Timezone to set.

    """
    global timezone
    timezone = tz


def current_timezone() -> Timezone:
    """
    Get the current timezone for the project.

    Returns:
        Timezone: The current timezone.

    """
    global timezone
    return timezone.value if 'timezone' in globals() else Timezone.UTC.value

def current_timezone_str() -> str:
    """
    Get the current timezone as a string.

    Returns:
        str: The current timezone as a string.

    """
    tz = current_timezone()
    if tz == Timezone.UTC.value:
        return "UTC"
    elif tz == Timezone.EST.value:
        return "EST"
    elif tz == Timezone.CST.value:
        return "CST"
    elif tz == Timezone.MST.value:
        return "MST"
    elif tz == Timezone.PST.value:
        return "PST"
    else:
        return "Unknown Timezone"


# ========= TIME ==================================================

def now(dprint: bool = False) -> float:
    """
    Get the current UNIX timestamp.

    Args:
        dprint: If True, print debug information.

    """
    time_now = time.time()
    if dprint and 'start_time' in globals():
        print("Created a new timestamp: "
              f"{to_custom_time_format(time_now, CustomTime.YMD_HMS6)}")
        print(f"{to_custom_time_diff_format(time_now - start_time, CustomTimeDiff.HMS6)}"
              " since start time.")
    return time_now


def set_start_time() -> None:
    """
    Set the start time for the project.

    This is used to calculate project runtime.

    """
    global start_time
    start_time = now()

def get_start_time() -> float:
    """
    Get the start time for the project.

    Returns:
        float: The start time as a UNIX timestamp.

    """
    global start_time
    return start_time if 'start_time' in globals() else None

def to_datetime(value: TimeValue) -> Optional[datetime.datetime]:
    """
    Convert a value to a datetime object.

    Args:
        value: The value to convert.

    Returns:
        The converted datetime object, or None if conversion fails.

    """
    if isinstance(value, datetime.datetime):
        return value
    elif isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        return datetime.datetime.fromtimestamp(value)
    else:
        return None
    
def to_unix(value: TimeValue) -> Optional[float]:
    """
    Convert a value to a UNIX timestamp (float).

    Args:
        value: The value to convert.

    Returns:
        The converted float, or None if conversion fails.

    """
    if isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, str):
        # try to convert iso format string to float
        try:
            dt = datetime.datetime.fromisoformat(value)
            return dt.timestamp()
        except ValueError:
            print(f"Error converting string to float: {value}")
            print("returning None.\n")
            return None
    elif isinstance(value, datetime.datetime):
        return value.timestamp()
    else:
        return None
    

def to_iso(value: TimeValue) -> Optional[str]:
    """
    Convert a value to an ISO format string.

    Args:
        value: The value to convert.

    Returns:
        The converted ISO format string, or None if conversion fails.

    """
    dt = to_datetime(value)
    if dt is None:
        return None
    else:
        return dt.isoformat()
    
def elapsed(start: TimeValue, end: TimeValue = now()) -> Optional[float]:
    """
    Calculate the elapsed time between two values.

    Args:
        start: The start value.
        end: The end value.
            If None, the current time is used.

    Returns:
        The elapsed time in seconds, or None if conversion fails.

    """
    start_float = to_unix(start)
    end_float = to_unix(end)
    if start_float is None or end_float is None:
        print(f"Error converting start or end value to float: {start}, {end}")
        return None
    else:
        return end_float - start_float
    
    
def to_custom_time_format(value: TimeValue, 
                          fmt: CustomTime = CustomTime.YMD_HMS6
                          ) -> Optional[str]:
    """
    Convert a value to a custom format string.

    Args:
        value: The value to convert.
        fmt: The custom format to use.

    Returns:
        The converted string, or None if conversion fails.

    """
    tz = current_timezone()
    dt = to_datetime(value)
    if dt is None:
        return None
    else:
        return dt.astimezone(tz).strftime(fmt.value)
    
def to_custom_time_diff_format(value: Union[int, float], 
                               fmt: CustomTimeDiff = CustomTimeDiff.HMS6_2
                               ) -> Optional[str]:
    """
    Convert a time difference value to a custom format string.

    Args:
        value: The time difference in seconds to convert.
        fmt: The custom format to use.

    Returns:
        The formatted time difference string, or None if conversion fails.

    """
    if not isinstance(value, (int, float)):
        return None

    # Calculate hours, minutes, seconds, microseconds
    seconds = float(value)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Extract whole seconds and microseconds
    whole_seconds = int(seconds)
    microseconds = int((seconds - whole_seconds) * 1000000)
    nanoseconds = int((seconds - whole_seconds) * 1000000000)
    
    # Create a dictionary with the values to substitute
    time_parts = {
        "hours": f"{int(hours)}",
        "minutes": f"{int(minutes):2d}",
        "seconds": f"{whole_seconds:2d}",
        "microseconds": f"{microseconds:06d}",
        "nanoseconds": f"{nanoseconds:010d}"
    }
    
    # Use the format string from the enum with our values
    try:
        return fmt.value.format(**time_parts)
    except Exception as e:
        print(f"Error formatting time difference: {e}")
        return None


# ========== TIME DELAY =========================================

def sleep(seconds: float, message_on_sleep: str = None, dprint: bool = False) -> None:
    """
    Sleep for a specified number of seconds with optional messaging.
    
    Args:
        seconds: The number of seconds to sleep
        message_on_sleep: Optional message to display before sleeping
        dprint: If True, print debug information about the sleep
    
    Example:
        sleep(5, message_on_sleep="Waiting for resource to become available")
    """
    if message_on_sleep:
        print(message_on_sleep)
        
    if dprint:
        print(f"Sleeping for {seconds} seconds...")
        
    time.sleep(seconds)
    
    if dprint:
        print(f"Slept for {seconds} seconds.")



def yawn(yawn_limit: int = 2, 
         yawn_for: float = 10.0, 
         sleep_for: float = 1.0,
         id: str = None, 
         message_on_sleep: str = None,
         exception_on_sleep: Type[Exception] = None,
         dprint: bool = False) -> bool:
    """
    Circuit breaker pattern for graceful handling of repeated error conditions.
    
    If this function is called with the same ID multiple times within a short period,
    it will trigger a sleep after reaching the specified threshold. This provides
    a safety mechanism for preventing overload during error conditions.
    
    Args:
        yawn_limit: Number of yawns required to trigger a sleep (first call counts as 1)
        yawn_for: Time window in seconds during which yawns are counted
        sleep_for: Duration in seconds to sleep when limit is reached
        id: Unique identifier for this circuit breaker
        message_on_sleep: Optional message to display when sleeping
        exception_on_sleep: Optional exception type to raise instead of sleeping
        dprint: If True, print debug information
        
    Returns:
        bool: True if the function caused sleep or raised an exception, False otherwise
        
    Raises:
        ValueError: If id is None on first call
        Exception: The specified exception_on_sleep type if provided and triggered
        
    Examples:
        # Simple usage
        yawn(3, 30, 5, "database_connection")
        
        # With custom message
        yawn(2, 10, 30, "api_rate_limit", message_on_sleep="API rate limit exceeded, pausing...")
        
        # With exception instead of sleep
        yawn(3, 60, 0, "critical_service", exception_on_sleep=ServiceUnavailableError)
    """
    global yawns
    triggered = False
    current_time = now()

    # Validate ID
    if id is None:
        raise ValueError("id cannot be None when creating a yawn circuit breaker")

    # Clean up expired yawns
    if id in yawns:
        yawndata = yawns[id]
        elapsed = current_time - yawndata['yawn_start']

        # If the yawn has expired, remove it
        if elapsed > yawndata['yawn_for'] and not yawndata['sleeping']:
            if dprint:
                print(f"Circuit breaker {id} expired after {elapsed:.2f} seconds (reset)")
            del yawns[id]

    # Process existing circuit breaker
    if id in yawns:
        yawndata = yawns[id]

        # If already sleeping, just return
        if yawndata['sleeping']:
            if dprint:
                print(f"Circuit breaker {id} is already in sleep state")
            return False
        
        # Calculate time since first yawn
        elapsed = current_time - yawndata['yawn_start']

        # If within the time window, increment count
        if elapsed <= yawndata['yawn_for']:
            yawndata['yawn_count'] += 1
            if dprint:
                print(f"Circuit breaker {id}: {yawndata['yawn_count']}/{yawndata['yawn_limit']} "
                      f"events within {elapsed:.2f}s window")
                
        # Check if limit reached
        if yawndata['yawn_count'] >= yawndata['yawn_limit']:
            yawndata['sleeping'] = True
            triggered = True
            
            # Compose message
            display_message = message_on_sleep
            if display_message is None:
                display_message = (f"Circuit breaker {id} triggered: "
                                  f"{yawndata['yawn_count']} events in "
                                  f"{elapsed:.2f}s exceeded limit of {yawndata['yawn_limit']}")
                
            # Either raise exception or sleep
            if exception_on_sleep is not None:
                if dprint:
                    print(f"Circuit breaker {id} raising {exception_on_sleep.__name__}")
                del yawns[id]  # Clean up
                raise exception_on_sleep(display_message)
            else:
                # Display message and sleep
                print(display_message)
                if dprint:
                    print(f"Sleeping for {yawndata['sleep_for']} seconds...")
                    
                sleep(yawndata['sleep_for'], dprint=dprint)
                
                if dprint:
                    print(f"Circuit breaker {id} reset after sleep")
                    
                del yawns[id]  # Clean up after sleeping
    else:
        # Initialize new circuit breaker
        yawns[id] = {
            'yawn_start': current_time,
            'yawn_limit': yawn_limit,
            'yawn_count': 1,
            'yawn_for': yawn_for,
            'sleep_for': sleep_for,
            'sleeping': False
        }

        if dprint:
            print(f"Circuit breaker {id} initialized: {yawn_limit} events within "
                  f"{yawn_for}s will trigger a {sleep_for}s pause")
    
    return triggered

def set_yawns_global() -> None:
    """
    Initialize the yawns dictionary.

    This dictionary will hold all yawns that are currently active.

    """
    global yawns
    yawns = {}

    



            


            
                




    
    
    
