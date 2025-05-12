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

# suitkaise/int/processing/init_registry.py

"""
Registry for customizable process and thread initialization functions.

This module provides a central registry for process and thread intialization functions.
These functions are automatically called when processes or threads are created using the 
ProcessManager or ThreadManager classes. 

Uses the FIB (Function Instance Builder) to store function call instances for later
execution.

"""

import threading
from typing import Callable, Dict, Optional, List, Any, Tuple

import suitkaise.int.utils.fib.fib as fib

class InitRegistryError(Exception):
    """Custom exception for errors in the InitializationRegistry."""
    pass

class InitRegistry:
    """
    Registry for process and thread initialization functions.

    This singleton class allows registering and retrieving initialization 
    functions for processes that should be called when new processes or threads 
    are created. 

    Functions can be registered with priorities to control the order in 
    which they are called, and can be registered with a keyword that can
    be used to toggle them on or off during initialization.
    
    """
    _instance = None
    _init_registry_lock = threading.RLock()

    def __new__(cls):
        with cls._init_registry_lock:
            if cls._instance is None:
                cls._instance = super(InitRegistry, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
        
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        
        # registry for process initialization functions
        self.process_initializers = {}

        # registry for thread initialization functions
        self.thread_initializers = {}

        self._initialized = True

        print("InitRegistry initialized.")
