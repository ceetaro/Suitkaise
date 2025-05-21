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
from typing import Callable, Dict, Optional, List, Any, Tuple, Union

import suitkaise_app.int.utils.fib.fib as fib

class ProcessingInitRegistryError(Exception):
    """Custom exception for errors in the InitializationRegistry."""
    pass

class ProcessingInitRegistry:
    """
    Registry for process and thread initialization functions.

    This singleton class allows registering and retrieving initialization 
    functions for processes that should be called when new processes or threads 
    are created. 

    Functions can be registered with priorities to control the order in 
    which they are called, and can be registered with a keyword that can
    be used to toggle them on or off during initialization.
    
    """
    _processing_init_registry = None
    _processing_init_registry_lock = threading.Lock()

    def __new__(cls):
        with cls._init_registry_lock:
            if cls._instance is None:
                cls._instance = super(ProcessingInitRegistry, cls).__new__(cls)
                cls._init_processing_init_registry()
            return cls._instance
        
    def _init_processing_init_registry(self):
        """
        Initialize the ProcessingInitRegistry instance.

        This method is called only once when the singleton instance is created.

        """
        # registry for process initialization functions
        self.process_initializers = {}

        # registry for thread initialization functions
        self.thread_initializers = {}

        print("InitRegistry initialized.")

    def register_process_initializer(self, func: Callable, 
                                     name: str = None,
                                     priority: int = 100) -> None:
        """
        Register a process initialization function.

        Args:
            func (Callable): The function to register.
            name (str, optional): The name of the function. If None, the function's 
                __name__ attribute will be used.
            priority (int, optional): The priority of the function. The first function
                called to initialize is the lowest number.

        """
        with self._processing_init_registry_lock:
            if priority not in self.process_initializers:
                self.process_initializers[priority] = []

            func_name = name if name else func.__name__
            self.process_initializers[priority].append((func_name, func))
            print(f"Registered process initializer: {func_name} with priority {priority}")


    def register_thread_initializer(self, func: Callable,
                                    name: str = None,
                                    priority: int = 100) -> None:
            """
            Register a thread initialization function.
    
            Args:
                func (Callable): The function to register.
                name (str, optional): The name of the function. If None, the function's 
                    __name__ attribute will be used.
                priority (int, optional): The priority of the function. The first function
                    called to initialize is the lowest number.
    
            """
            with self._processing_init_registry_lock:
                if priority not in self.thread_initializers:
                    self.thread_initializers[priority] = []
    
                func_name = name if name else func.__name__
                self.thread_initializers[priority].append((func_name, func))
                print(f"Registered thread initializer: {func_name} with priority {priority}")


    def deregister_process_initializer(self,
                                       initializer: Union[Callable, str]) -> None:
        """
        Unregister a process initializer function.

        Args:
            initializer (Union[Callable, str]): The function or name of the function to deregister.

        """
        with self._processing_init_registry_lock:
            for priority, initializers in self.process_initializers.items():
                for i, (name, func) in enumerate(initializers):
                    if func == initializer or name == initializer:
                        del initializers[i]
                        print(f"Deregistered process initializer: {name}")
                        return
                    
            raise ProcessingInitRegistryError(f"Process initializer {initializer} not found.")
        
    
    def deregister_thread_initializer(self,
                                       initializer: Union[Callable, str]) -> None:
        """
        Unregister a thread initializer function.

        Args:
            initializer (Union[Callable, str]): The function or name of the function to deregister.

        """
        with self._processing_init_registry_lock:
            for priority, initializers in self.thread_initializers.items():
                for i, (name, func) in enumerate(initializers):
                    if func == initializer or name == initializer:
                        del initializers[i]
                        print(f"Deregistered thread initializer: {name}")
                        return
                    
            raise ProcessingInitRegistryError(f"Thread initializer {initializer} not found.")
        

    def execute_process_initializers(self) -> Dict[str, Any]:
        """
        Execute all registered process initialization functions in order of priority.

        """
        results = {}

        # sort the initializers by priority
        sorted_priorities = sorted(self.process_initializers.keys())

        for priority in sorted_priorities:
            initializers = self.process_initializers[priority]

            for name, func in initializers:
                try:
                    result = func()
                    results[name] = result
                    print(f"Executed process initializer: {name}")
                except Exception as e:
                    raise ProcessingInitRegistryError(f"Error executing process initializer {name}: {e}")
                
        return results
    
    def execute_thread_initializers(self) -> Dict[str, Any]:
        """
        Execute all registered thread initialization functions in order of priority.

        """
        results = {}

        # sort the initializers by priority
        sorted_priorities = sorted(self.thread_initializers.keys())

        for priority in sorted_priorities:
            initializers = self.thread_initializers[priority]

            for name, func in initializers:
                try:
                    result = func()
                    results[name] = result
                    print(f"Executed thread initializer: {name}")
                except Exception as e:
                    raise ProcessingInitRegistryError(f"Error executing thread initializer {name}: {e}")
                
        return results
                    
        
    
                    


