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
from typing import Optional, Union, Any
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
          f"{to_custom_time_format(st, CustomTimeFormats.YMD_HMS6)}")

    # print current timezone
    print(f"Current timezone: {current_timezone_str()}")

    # set the global yawns dictionary
    set_yawns_global()


# ========================================================================


class CustomTimeFormats(Enum):
    """
    Enum for custom time formats.

    Use with to_custom_time_format().

    """
    YMD_HMS6 = "%Y-%m-%d %H:%M:%S.%f" # 2025-12-25 12:00:00.000000

class CustomTimeDiffFormats(Enum):
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
              f"{to_custom_time_format(time_now, CustomTimeFormats.YMD_HMS6)}")
        print(f"{to_custom_time_diff_format(time_now - start_time, CustomTimeDiffFormats.HMS6)}"
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
    
def elapsed(start: TimeValue, end: TimeValue) -> Optional[float]:
    """
    Calculate the elapsed time between two values.

    Args:
        start: The start value.
        end: The end value.

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
                          fmt: CustomTimeFormats = CustomTimeFormats.YMD_HMS6
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
                               fmt: CustomTimeDiffFormats = CustomTimeDiffFormats.HMS6_2
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

def sleep(seconds: float, dprint: bool = False) -> None:
    """
    Sleep for a specified number of seconds.

    Args:
        seconds: The number of seconds to sleep.

    """
    if dprint:
        print(f"Sleeping for {seconds} seconds...")
    time.sleep(seconds)
    if dprint:
        print(f"Slept for {seconds} seconds.")




def yawn(num_yawns: int = 2, yawn_for: float = 10.0, sleep_for: float = 1.0,
         id: str = None, dprint: bool = False) -> None:
    """
    Yawn for a specified number of seconds.

    If another yawn by the same id happens within the yawn_for time,
    the program will sleep for sleep_for seconds.

    Uses the parameters from the first call to determine the yawn_for
    and sleep_for values.

    Allows for some better flexibility than just instant sleep calls.

    Uses:
    - sleep daemon threads after a high resource usage has been 
    detected and did not reduce after a certain time.
    - sleep background threads if no user input has been detected for a
    certain time.
    - sleep threads that are waiting for a certain event to happen if the
    event won't happen for a certain time.
    - time out busy loops

    Args:
        num_yawns: number of yawns until the program sleeps
        - first call counts as 1 yawn
        - sleeps once the number of yawns is reached.
        yawn_for: time to yawn for, in seconds
        sleep_for: time to sleep for, in seconds
        id: id of the yawn
        - will raise an error if the id is None
        dprint: if True, will print debug information

    """
    global yawns

    current_time = now()

    # clean up expired yawns
    if id in yawns:
        yawndata = yawns[id]
        elapsed = current_time - yawndata['yawn_start']

        # if the yawn has expired, remove it
        if elapsed > yawndata['yawn_for'] and not yawndata['sleeping']:
            if dprint:
                print(f"{id}'s yawn expired after {elapsed:.2f} seconds. "
                      f"Removing {id} from yawns.")
            del yawns[id]
            

    # now check if id exists
    if id in yawns:
        yawndata = yawns[id]

        # check if we are already sleeping
        if yawndata['sleeping']:
            if dprint:
                print(f"Yawn {id} is already sleeping.")
            return
        
        # calc elapsed time since first yawn
        elapsed = current_time - yawndata['yawn_start']

        # if another yawn happens within the yawn_for time,
        # increment the number of yawns
        if elapsed <= yawndata['yawn_for']:
            yawndata['yawn_count'] += 1
            if dprint:
                print(f"Another yawn happened within the yawn_for time for id {id}."
                      f"Number of yawns: {yawndata['yawn_count']}")
                
        # check if we reached the number of yawns
        if yawndata['yawn_count'] >= yawndata['num_yawns']:
            # sleep for the specified time
            if dprint:
                print(f"{yawndata['num_yawns']} yawns have been detected. "
                      f"{id} going to sleep...")
        
            yawndata['sleeping'] = True
            sleep(yawndata['sleep_for'], dprint=dprint)

            if dprint:
                print(f"{id} slept for {yawndata['sleep_for']} seconds due to a yawn.")

            # remove this yawn, it's job is complete
            del yawns[id]

    else:
        # if the id is not in the yawns dictionary, create a new entry
        if id is None:
            raise ValueError("id cannot be None when creating a new yawn.")
        yawns[id] = {
            'yawn_start': current_time,
            'num_yawns': num_yawns,
            'yawn_count': 1,
            'yawn_for': yawn_for,
            'sleep_for': sleep_for,
            'sleeping': False
        }

        if dprint:
            print(f"First yawn registered for id {id}.\n"
                  f"Will sleep for {sleep_for} seconds "
                  f"if {num_yawns} yawns are detected within {yawn_for} seconds.")
            


def set_yawns_global() -> None:
    """
    Initialize the yawns dictionary.

    This dictionary will hold all yawns that are currently active.

    """
    global yawns
    yawns = {}

    



            


            
                




    
    
    
