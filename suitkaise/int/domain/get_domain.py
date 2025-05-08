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

# suitkaise/int/domain/get_domain.py

"""
Module for determining the domain (internal or external) of code execution.

In the Suitkaise architecture, code is divided into two domains:
- Internal: Code that is part of the Suitkaise application itself
- External: Code that was imported or created by a user

This module provides functions to determine which domain the calling code
belongs to. The domain is primarily determined by directory structure:
- Code in the 'int' directory is considered internal
- Code in the 'ext' directory is considered external

For components like EventBus and BusStation, it's recommended to store
the domain as an explicit attribute during initialization rather than
recalculating it:

    self.domain = determine_domain()
    
This makes domain information immediately available and self-documenting.

"""

import inspect
import os
import sys
import threading
from typing import Optional

from suitkaise.int.eventsys.data.enums.enums import SKDomain

def _get_calling_module(frames_back: int = 2) -> Optional[str]:
    """
    Get the module name of the calling function.

    Args:
        frames_back (int): The number of frames to go back in the stack.
            Default is 2 to skip the current function and the caller.

    Returns:
        Optional[str]: The module name of the calling function, or None if not found.

    """
    try:
        # get the frame that called '_get_calling_module'
        frame = inspect.currentframe()
        for _ in range(frames_back):
            if frame is None:
                return None
            frame = frame.f_back

        if frame is None:
            return None
        
        # get the module name from the frame
        module_name = frame.f_globals.get("__name__")
        return module_name
    
    except Exception as e:
        # Handle any exceptions that occur while getting the calling module
        print(f"Error in _get_calling_module: {e}")
        return None
    
    finally:
        # Clean up the frame reference to avoid reference cycles
        del frame


def _get_module_path(module_name: str) -> Optional[str]:
    """
    Get the file path of a module by its name.

    Args:
        module_name (str): The name of the module.

    Returns:
        Optional[str]: The file path of the module, or None if not found.

    """
    try:
       if module_name in sys.modules:
            module = sys.modules[module_name]
            return getattr(module, '__file__', None)
       return None
    except Exception as e:
        # Handle any exceptions that occur while getting the module path
        print(f"Error in get_module_path: {e}")
        return None
    

def determine_domain(module_name: Optional[str] = None,
               module_file: Optional[str] = None,
               frames_back: int = 2) -> SKDomain:
    """
    Determine the domain (internal or external) for a module.

    This function checks if a module belongs to the internal or external domain
    based on its file path.

    Args:
        module_name (Optional[str]): The name of the module. 
            If None, the calling module is used.
        module_file (Optional[str]): The file path of the module. 
            If None, it will be determined from the module name.
        frames_back (int): The number of frames to go back in the 
        stack to find the calling module.

    Returns:
        SKDomain: The domain of the module (INTERNAL, EXTERNAL, UNKNOWN)
    
    """
    # if no module name is provided, get the calling module
    if module_name is None:
        module_name = _get_calling_module(frames_back=frames_back)
        if module_name is None:
            return SKDomain.UNKNOWN
        
    # if no module file is provided, get the module file path
    if module_file is None:
        module_file = _get_module_path(module_name)
        if module_file is None:
            if 'suitkaise.int' in module_name or module_name.startswith('int.'):
                return SKDomain.INTERNAL
            elif 'suitkaise.ext' in module_name or module_name.startswith('ext.'):
                return SKDomain.EXTERNAL
            return SKDomain.UNKNOWN
        
    # check if the module file path is valid
    norm_path = os.path.normpath(module_file)

    if '/int/' in norm_path.replace('\\', '/') or '\\int\\' in norm_path:
        return SKDomain.INTERNAL
    elif '/ext/' in norm_path.replace('\\', '/') or '\\ext\\' in norm_path:
        return SKDomain.EXTERNAL
    
    if 'suitkaise.int' in module_name or module_name.startswith('int.'):
        return SKDomain.INTERNAL
    elif 'suitkaise.ext' in module_name or module_name.startswith('ext.'):
        return SKDomain.EXTERNAL
    
    return SKDomain.UNKNOWN

def get_domain(frames_back: int = 2) -> SKDomain:
    """
    Get the domain of the calling code.

    This is primarily intended for initialization of components like
    EventBus and BusStation, where the domain is needed for setup.
    For frequent use, consider storing the domain as an attribute.

    Args:
        frames_back: Number of frames to go back in the call stack.
            Default is 2 to skip the current function and the caller.

    Returns:
        SKDomain: The domain of the calling code (INTERNAL, EXTERNAL, UNKNOWN).

    """
    return determine_domain(frames_back=frames_back + 1)

def is_internal(frames_back: int = 2) -> bool:
    """
    Check if the calling code is in the internal domain.

    Args:
        frames_back: Number of frames to go back in the call stack.
            Default is 2 to skip the current function and the caller.

    Returns:
        bool: True if the calling code is in the internal domain, False otherwise.

    """
    return get_domain(frames_back=frames_back + 1) == SKDomain.INTERNAL

def is_external(frames_back: int = 2) -> bool:
    """
    Check if the calling code is in the external domain.

    Args:
        frames_back: Number of frames to go back in the call stack.
            Default is 2 to skip the current function and the caller.

    Returns:
        bool: True if the calling code is in the external domain, False otherwise.

    """
    return get_domain(frames_back=frames_back + 1) == SKDomain.EXTERNAL

def get_domain_name(frames_back: int = 2) -> str:
    """
    Get the name of the domain for the calling code.

    Args:
        frames_back: Number of frames to go back in the call stack.
            Default is 2 to skip the current function and the caller.

    Returns:
        str: The name of the domain ("internal", "external", "unknown").

    """
    domain = get_domain(frames_back=frames_back + 1)
    if domain == SKDomain.INTERNAL:
        return "internal"
    elif domain == SKDomain.EXTERNAL:
        return "external"
    else:
        return "unknown"