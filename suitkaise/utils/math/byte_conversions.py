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

# suitkaise/utils/math/byte_conversions.py

"""
import suitkaise.utils.math.byte_conversions as byteconv

File that converts byte counts to other unit scales, like
kilobytes (KB), megabytes (MB), gigabytes (GB), and terabytes (TB).
"""

# file that converts byte counts to other units
# and formats them for display
from typing import Union


def convert_bytes(num, rounding: int = 'inf') -> str:
    """
    Convert bytes to a different scale of measurement.

    If you want to reconvert the number back to bytes, please
    set rounding to 0 for perfect accuracy.

    Args:
        num (int): The number of bytes to convert.
        rounding (int, optional): The number of decimal places to round to. Defaults to 2.

    Returns:
        str: The converted number with the appropriate unit suffix.
    
    """
    # Define the suffixes for different units
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    
    # Determine the appropriate scale
    for i, suffix in enumerate(suffixes):
        if num < 1024:
            break
        num /= 1024.0
    
    # Format the number to the specified number of decimal places
    if rounding and rounding != 'inf':
        formatted_num = f"{num:.{rounding}f}"
    else:
        formatted_num = str(int(num))
    
    return f"{formatted_num} {suffix}"

def back_to_bytes(num_to_convert: Union[str, int, float]) -> int:
    """
    Convert a number in a different scale back to bytes.

    Note: This will NOT be perfect unless the number has 
    NEVER been rounded since the original byte conversion.

    Args:
        num_to_convert (str, int, float): The number to convert back to bytes.

    Returns:
        int: The number in bytes.
    
    """
    # Define the suffixes for different units
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    
    # Check if the input is a string and split it into number and suffix
    if isinstance(num_to_convert, str):
        parts = num_to_convert.split()
        num = float(parts[0])
        suffix = parts[1]
    else:
        num = float(num_to_convert)
        suffix = 'B'

    # Find the index of the suffix
    if suffix in suffixes:
        index = suffixes.index(suffix)
    else:
        raise ValueError(f"Unknown suffix: {suffix}")
    
    # Convert the number back to bytes
    bytes_num = num * (1024 ** index)

    return int(bytes_num)