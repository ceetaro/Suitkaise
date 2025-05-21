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

# suitkaise/int/utils/formatting/format_data.py

"""
This module provides functions to format data into a more readable string representation.
Useful for logging, debugging, or displaying data in a more user-readable format.

"""
# format data like dicts and lists into better looking strings


def format_data(data):
    """
    Format data into a more readable string.

    Recursively formats nested structures like dicts and lists into a string representation.
    
    Args:
        data: The data to format, can be a dict, list, or other types.
        NOTE: currently only supports dicts, lists, and sets.
    
    Returns:
        str: The formatted string.

    """
    if isinstance(data, dict):
        return format_dict(data)
    elif isinstance(data, list):
        return format_list(data)
    elif isinstance(data, set):
        return format_set(data)
    else:
        return str(data)  # Fallback for other types
    
def format_dict(data):
    """
    Format a dictionary into a string.
    If there are other dictionaries or lists inside, they will be formatted as well.

    Args:
        data (dict): The dictionary to format.
    
    Returns:
        str: The formatted string.

    """
    formatted_items = []
    for key, value in data.items():
        formatted_key = f'"{key}"'
        formatted_value = format_data(value)
        formatted_items.append(f"{formatted_key}: {formatted_value}")
    return "{\n    " + ",\n    ".join(formatted_items) + "\n}"
    

def format_list(data):
    """
    Format a list into a string.
    If there are other dictionaries or lists inside, they will be formatted as well.

    Args:
        data (list): The list to format.

    Returns:
        str: The formatted string.

    """
    formatted_items = [format_data(item) for item in data]
    return "[ " + ", ".join(formatted_items) + " ]"

def format_set(data):
    """
    Format a set into a string.
    If there are other dictionaries or lists inside, they will be formatted as well.

    Args:
        data (set): The set to format.

    Returns:
        str: The formatted string.

    """
    formatted_items = [format_data(item) for item in data]
    return "{ " + ", ".join(formatted_items) + " }"