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

# suitkaise/int/eventsys/core/cycle/cycle.py

"""
NOTE: this module might split into multiple modules in the future, (cycle.py,
cycle_registry.py, cycle_part.py, cycle_builder.py...) if the code becomes too large

Module containing the Cycle class, which manages the event loop logic, facilitating
synchronization between all layers of the event system.

Includes:
- Cycle: The main class that manages code loops and handles events,
    using context manager protocol to generate reports and log stats.
- CycleRegistry: A registry for all built cycles and built CycleParts.
- CyclePart: A class that represents a part of the event loop, which can be used to 
    split parts of the event loop at sensible points.
    In this case, we split the event loop into 3 main parts:
    - EventBridge sync with MainStations (IntStation and ExtStation)
    - MainStation sync with their BusStations
    - BusStation sync with their Buses
- CycleBuilder: A class that builds the cycle using registered parts.

    
    Like Cycle itself, CyclePart uses context manager protocol to generate reports and log stats
    for the specific part of the event loop.

Example usage:
    # in event_bridge.py
    CyclePart.create_new_part(
        part_name="EventBridge",
        obj_instance=EventBridge.get_bridge(),
        obj_lock=EventBridge._bridge_lock,
        ready_flag=EventBridge._bridge_ready,
        started_flag=EventBridge._bridge_sync_started,
        finished_flag=EventBridge._bridge_sync_finished,
        stopped_flag=EventBridge._bridge_sync_stopped
        )

    # in event_mgr.py
    with CycleBuilder() as cyclebuilder:
        cyclebuilder.add_cycle_name("EventLoop")
        cyclebuilder.add_part("EventBridge")
        cyclebuilder.split("IntStation", "ExtStation")
        cyclebuilder.add_part_to_split(part_name="ExtStationConfig", split_name="ExtStation")
        cyclebuilder.add_part("BusStation") # adds this part to both the IntStation and ExtStation split
        cyclebuilder.add_part("EventBus")

    # on con. mgr exit:
    cyclebuilder.build() # builds the cycle with all parts and registers it in the CycleRegistry

    with Cycle(cycle=self.event_loop, on_exit=attempt_restart()) as cycle:

        if not cycle.running:
            cycle.start() # sets running flag to True and starts the cycle

        while cycle.running:
            try:
                cycle.run() # whole event loop, using EventCycle context manager protocol
            except Exception as e:
                cycle.handle_exception(e)


    # if cycle fully exits, we follow the context manager protocol and 
    # process whatever is in on_exit. This can be a function to call or an exception to raise.

"""

class CycleError(Exception):
    """Custom exception for cycle errors."""
    pass

class CycleRuntimeError(CycleError):
    """Custom exception for errors that occur when cycle is running."""
    pass

class CycleBuilderError(Exception):
    """Custom exception for cycle builder errors."""
    pass

class CyclePartError(Exception):
    """Custom exception for cycle part errors."""
    pass

class CycleRegistryError(Exception):
    """Custom exception for cycle registry errors."""
    pass

import threading
from typing import Optional, Dict, Any, Type, Union, Callable


class Cycle:
    """
    Cycle is the main class responsible for running code loops.

    It uses a cycle built by CycleBuilder to execute looping code
    with control and order across multiple threads and processes.

    Cycles act as managers, updating flags, checking for exceptions,
    managing timeouts, and logging stats across multiple threads,
    processes, and modules.
    
    """

class CycleRegistry:
    """
    CycleRegistry is a singleton registry for all built Cycles and CycleParts.

    It allows for easy access to all registered cycles and parts,
    and provides methods to add, remove, and retrieve cycles and parts.

    """
    _cycle_registry = None
    _cycle_registry_lock = threading.RLock()

    def __new__(cls):
        with cls._cycle_registry_lock:
            if cls._cycle_registry is None:
                cls._cycle_registry = super(CycleRegistry, cls).__new__(cls)
        return cls._cycle_registry
    

    def __init__(self):
        """
        Initialize the CycleRegistry singleton.

        This will only execute once, when the singleton is first created.
        Subsequent calls to CycleRegistry() will return the existing instance
        without re-initializing.
        
        """
        if hasattr(self, '_initialized') and self._initialized:
            return  
        
        self.name = "CycleRegistry"

        self.cycle_parts = {} # maps part names to CyclePart instances
        self.cycles = {} # maps cycle names to Cycle instances

        self._initialized = True

    @classmethod
    def get_instance(cls) -> 'CycleRegistry':
        """
        Get the singleton instance of CycleRegistry.
        
        Returns:
            CycleRegistry: The singleton instance of CycleRegistry.

        """
        if cls._cycle_registry is None:
            cls._cycle_registry = cls()
        return cls._cycle_registry
    

    def register_part(self, part_name: str, part_instance: 'CyclePart') -> None:
        """
        Register a CyclePart.

        This method adds the CyclePart to the registry,
        allowing it to be accessed later.

        Args:
            part_name (str): The name of the CyclePart.
            part_instance (CyclePart): The CyclePart instance to register.

        """
        if part_name in self.cycle_parts:
            raise CycleRegistryError(f"CyclePart with name {part_name} already exists.")
        with self._cycle_registry_lock:
            self.cycle_parts[part_name] = part_instance


    def unregister_part(self, part_name: str) -> None:
        """
        Unregister a CyclePart.

        This method removes the CyclePart from the registry.

        Args:
            part_name (str): The name of the CyclePart to unregister.

        """
        if part_name not in self.cycle_parts:
            raise CycleRegistryError(f"CyclePart with name {part_name} does not exist.")
        with self._cycle_registry_lock:
            del self.cycle_parts[part_name]

    
    def get_part(self, part_name: str) -> Optional['CyclePart']:
        """
        Get a CyclePart by name.

        This method retrieves the CyclePart from the registry.

        Args:
            part_name (str): The name of the CyclePart to retrieve.

        Returns:
            CyclePart: The CyclePart instance, or None if not found.

        """
        with self._cycle_registry_lock:
            return self.cycle_parts.get(part_name, None)


    def _part_registered(self, part_name: str) -> bool:
        """
        Check if a CyclePart with the given name is registered.

        Args:
            part_name (str): The name of the CyclePart to check.

        Returns:
            bool: True if the CyclePart is registered, False otherwise.

        """
        if part_name in self.cycle_parts:
            return True
        return False
    

    def _part_already_exists(self, part_name: str) -> bool:
        """
        Check if a CyclePart with the given name already exists in the registry.

        Args:
            part_name (str): The name of the CyclePart to check.

        Returns:
            bool: True if the CyclePart exists, False otherwise.

        """
        if part_name in self.cycle_parts:
            return True
        return False




class CyclePart:
    """
    CyclePart is a class that represents a part of the event loop.

    It can be used to split parts of the event loop at sensible points,
    allowing for better control and management of the event loop.
    
    """

    def __init__(self,
                 part_name: str,
                 obj_instance: Any,
                 obj_lock: threading.RLock,
                 thread_to_use: threading.Thread,
                 part_function: Type[Callable],
                 ready_flag: threading.Event,
                 started_flag: threading.Event,
                 finished_flag: threading.Event,
                 stopped_flag: threading.Event,
                 ) -> None:
        """
        Create a new CyclePart that can be used in Cycles.

        This constructor initializes the CyclePart with the given parameters.

        Args:
            part_name (str): The name of the CyclePart.
            obj_instance (Any): The object instance that this CyclePart will reference.
            obj_lock (threading.RLock): The lock object to use for thread safety.
            thread_to_use (threading.Thread): The worker thread to use for this CyclePart.
                if None, try to call obj_instance.get_cycle_thread(part_name) for the thread to use.
            part_function (Type[Callable]): The function to run in this CyclePart.
                if None, try to call obj_instance.get_cycle_function(part_name) for the function to use.
            ready_flag (threading.Event): The event flag to signal when this CyclePart is ready
                to start.
            started_flag (threading.Event): The event flag to signal when this CyclePart
                has started running.
            finished_flag (threading.Event): The event flag to signal when this CyclePart
                has finished running.
            stopped_flag (threading.Event): The event flag to signal if this CyclePart
                has stopped running without finishing.
        
        """
        # Check if the part name already exists in the registry
        if CycleRegistry.get_instance()._part_already_exists(part_name):
            raise CyclePartError(f"CyclePart with name {part_name} already exists.")
        
        # Initialize the CyclePart
        self.part_name = part_name
        self.obj_instance = obj_instance
        if hasattr(obj_instance, obj_lock):
            self.obj_lock = getattr(obj_instance, obj_lock)
        else:
            raise CyclePartError(f"Object instance does not have lock: {obj_lock}")
        if thread_to_use is None:
            thread_finder = getattr(obj_instance, "get_cycle_thread", None)
            if thread_finder is not None:
                try:
                    found_thread_to_use = thread_finder(part_name)
                    if found_thread_to_use is not None:
                        self.thread_to_use = found_thread_to_use
                    else:
                        raise CyclePartError(f"Thread not found for CyclePart: {part_name}")
                except Exception as e:
                    raise CyclePartError(f"Failed to get thread for CyclePart: {e}")
            else:
                raise CyclePartError(
                    f"Object instance does not have method get_cycle_thread."
                    f" Cannot find thread for CyclePart: {part_name}"
                    )
        else:
            if hasattr(obj_instance, thread_to_use):
                self.thread_to_use = getattr(obj_instance, thread_to_use)

        if part_function is None:
            function_finder = getattr(obj_instance, "get_cycle_function", None)
            if function_finder is not None:
                try:
                    found_function = function_finder(part_name)
                    if found_function is not None:
                        self.part_function = found_function
                    else:
                        raise CyclePartError(f"Function not found for CyclePart: {part_name}")
                except Exception as e:
                    raise CyclePartError(f"Failed to get function for CyclePart: {e}")
            else:
                raise CyclePartError(
                    f"Object instance does not have method get_cycle_function."
                    f" Cannot find function for CyclePart: {part_name}"
                    )
        else:
            if hasattr(obj_instance, part_function):
                self.part_function = getattr(obj_instance, part_function)
            else:
                raise CyclePartError(f"Object instance does not have function: {part_function}")
            
        self.ready_flag = ready_flag
        self.started_flag = started_flag
        self.finished_flag = finished_flag
        self.stopped_flag = stopped_flag

        # other parts' flags
        self.previous_part = None

        # runtime attributes
        self.running = False
        self.current_cycle = 0
        self.current_cycle_start_time = None
        self.current_cycle_end_time = None
        self.current_cycle_duration = None
        self.current_cycle_report = None

        # register the CyclePart in the CycleRegistry
        self._register_part()


    def _register_part(self) -> None:
        """
        Register this CyclePart in the CycleRegistry.
        This method is called automatically when the CyclePart is created.
        
        """
        registry = CycleRegistry.get_instance()
        if registry._part_already_exists(self.part_name):
            raise CyclePartError(f"CyclePart with name {self.part_name} already exists.")
        registry.register_part(self.part_name, self)


     


class CycleBuilder:
    """
    CycleBuilder is a class that builds Cycle templates using registered CycleParts.

    It allows for easy addition and management of parts,
    and provides methods to build the cycle with all parts and split
    the cycle depending on user need. 

    Note that if you build a Cycle with a split, an additional worker thread
    will be used for each split so that looping can happen in parallel.
    
    """

    def __init__(self):
        """
        Initialize the CycleBuilder.

        This constructor initializes the CycleBuilder with the given parameters.
        
        """
        self._cycle_builder_lock = threading.RLock()
        self.registry = CycleRegistry.get_instance()

        self.cycle_name = None

        self