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

# suitkaise/int/eventsys/core/station/bus_station.py

"""
Module holding BusStation class for process-level event handling. Each process creates
a BusStation instance to handle events. This class inherits from the Station class 
and implements the required methods for process-level event handling, including 
communication with both the relevant MainStation and its thread-level EventBuses.

BusStations serve as intermediaries between EventBuses in different threads
and MainStations in different processes. They aggregate events from all threads
in a process and coordinate with the appropriate MainStation.

The BusStation manages:
1. Event collection from all EventBuses in the process
2. Event distribution to interested EventBuses
3. Event synchronization with the appropriate MainStation
4. Efficient memory management through event compression and filtering

"""
import os
import multiprocessing
import threading
import time
import pickle
import weakref
from typing import Dict, List, Set, Type, Optional, Any, Union, Tuple

import suitkaise.int.time.sktime as sktime
from suitkaise.int.eventsys.data.enums.enums import (
    StationLevel, EventState, EventPriority, CompressionLevel, SKDomain
)
from suitkaise.int.eventsys.events.base_event import Event
import suitkaise.int.eventsys.keyreg.keyreg as keyreg
from suitkaise.int.eventsys.core.station.station import Station
import suitkaise.int.domain.get_domain as get_domain

class BusStation(Station):
    """
    Process-level event station that manages events from all threads in a process.

    The BusStation serves as an intermediary between thread-level EventBuses and
    the domain-level MainStation. It aggregates events from all threads in this
    process and coordinates with the appropriate MainStation.

    Each process has one BusStation, which is a singleton per process. It maintains
    a mapping of registered EventBuses and their interests, and manages the flow of
    events between buses and the MainStation.

    Events buses can choose to propagate their events directly to the MainStation,
    and if this is the case the BusStation will still handle it. Sometimes, just 
    process level information is good enough, hence why the BusStation works at
    the process level.

    The BusStation does not directly communicate with other BusStations in other
    processes. Instead, it communicates with the MainStation, which is responsible
    for inter-process communication.


    Features:
    - Singleton pattern per process
      - only one BusStation instance per process, but the main process will
        also have a MainStation instance (either IntStation or ExtStation)
    - Thread-safe event handling
    - Interest-based event distribution
    - Compression management
    - MainStation synchronization

    """

    # dict mapping process IDs to BusStation instances
    _instances: Dict[int, 'BusStation'] = {}

    # lock for thread safe singleton access
    _instances_lock = threading.RLock()

    # station level (always LOCAL for BusStations)
    _station_level = StationLevel.LOCAL

    @classmethod
    def get_bus_station(cls, name: str = None) -> 'BusStation':
        """
        Get the singleton instance of the BusStation for the current process.

        Args:
            level (StationLevel): The station level to get. Defaults to LOCAL.

        Returns:
            BusStation: The singleton instance of the BusStation.
        """
        pid = os.getpid()

        with cls._instances_lock:
            if pid not in cls._instances:
                # create a new BusStation name
                if name:
                    station_name = f"BusStation-{pid} ({name})"
                elif not name:
                    station_name = f"BusStation-{pid}"
                # check if the name is already in use
                if station_name in cls._instances:
                    print(f"BusStation with name {station_name} already exists. "
                          f"Using existing instance.")
                    # get the existing instance's pid
                    existing_pid = next((key for key, value in cls._instances.items()
                                        if value.name == station_name), None)
                    if existing_pid:
                        return cls._instances[existing_pid]
                else:
                    # create a new BusStation instance
                    cls._instances[pid] = cls(station_name)
                    print(f"Created new BusStation instance with name {station_name}.")
                    return cls._instances[pid]
                
    
    def __init__(self, name: str):
        """
        Initialize a new BusStation.

        Args:
            name: a descriptive name for the BusStation instance.

        """
        super().__init__(name)

        # dictionary of registered EventBuses
        self.registered_buses = {}

        # communication with the MainStation
        self.domain = get_domain.get_domain()
        self.main_connection = None # bool
        self.connected_station = None # either IntStation or ExtStation
        self._main_station_lock = threading.RLock()

        # configuration
        self.sync_interval = 5.0
        self.compression_interval = 30.0
        self.history_size_limit = 15 * 1024 * 1024 # 15 MB
        self.compress_threshold = 10 * 1024 * 1024 # 10 MB

        # background
        self._sync_thread = None
        self._compression_thread = None
        self._running = False

        # initialization
        self._init_background()

        print(f"Initialized {self.__class__.__name__} '{self.name}' "
              f"for process {self.process_id}")
        
    def _init_background(self):
        """
        Initialize and start background tasks for maintenance.

        This starts threads for:
        1. Periodic syncing with the MainStation.
        2. Periodic compression of events.
        
        """
        self._running = True

        # start the sync thread
        self._sync_thread = threading.Thread(
            target=self._sync_with_main_station,
            name=f"SyncThread-{self.process_id}",
            daemon=True
            )
        
        self._sync_thread.start()

        # start the compression thread
        self._compression_thread = threading.Thread(
            target=self._compress_station_history,
            name=f"CompressionThread-{self.process_id}",
            daemon=True
            )
        self._compression_thread.start()

        print(f"Started background tasks for {self.name} "
              f"with PID {self.process_id}.")
        
    def _sync_with_main_station(self):
        """
        Periodically synchronize with the MainStation.

        This runs in a separate thread dedicated to syncing with
        the MainStation. It sends and receives events at regular intervals.
        
        """
        while self._running:
            try:
                id = self.station_name
                # only sync if the connection is established
                if self.main_connection and self.connected_station:
                    self._sync_with_main()
                    print(f"Completed sync with {self.connected_station.name} for {self.name}.")
                    sktime.sleep(self.sync_interval)

                elif self.able_to_connect():
                    self._connect_to_main_station()

                else:
                    print(f"MainStation connection not established for {self.name}.")
                    sktime.yawn(3, 5, 10, id, dprint=True)
                    # sleep for a second before trying again
                    sktime.sleep(1)
            except Exception as e:
                print(f"Error in sync thread for {self.name}: {e}")
                sktime.yawn(3, 5, 10, id, dprint=True)
                sktime.sleep(1)

    def _compress_station_history(self):
        """
        Periodically check for and compress events.

        This runs in a separate background thread dedicated to
        compressing events.
        
        """
        while self._running:
            try:
                # check if comporession is needed
                if self.needs_compressing == True:
                    self.compress_events() # from Station class
                    print(f"Compressed events for {self.name}.")

                sktime.sleep(self.compression_interval)

            except Exception as e:
                print(f"Error in compression thread for {self.name}: {e}")
                sktime.yawn(3, 10, 40, self.station_name, dprint=True)
                sktime.sleep(1)


    def able_to_connect(self) -> bool:
        """
        Check if the BusStation can connect to the MainStation.

        Returns:
            bool: True if the BusStation can connect to the MainStation,
                  False otherwise.
        """
        try:
            if self.main_connection is not False:
                return True
            else:
                raise ValueError(f"{self.name} cannot connect to the MainStation.")
        except Exception as e:
            print(f"Error checking connection for {self.name}: {e}")
            return False

    def _connect_to_main_station(self, domain: str):
        """
        Connect to the appropriate MainStation, based on the domain.

        Args:
            domain: The domain to connect to. This can be either
                    "internal" or "external".

        """
        with self._main_station_lock:
            if self.domain == SKDomain.INTERNAL:
                # connect to the IntStation
                from suitkaise.int.eventsys.core.station.int_station import IntStation
                self.connected_station = IntStation.get_connection()
                if self.connected_station:
                    self.main_connection = True
                    print(f"Connected to IntStation for {self.name}.")
                else:
                    print(f"Failed to connect to IntStation for {self.name}.")
                    self.main_connection = False
                    self.connected_station = None

            elif self.domain == SKDomain.EXTERNAL:
                # connect to the ExtStation
                from suitkaise.int.eventsys.core.station.ext_station import ExtStation
                self.connected_station = ExtStation.get_connection()
                if self.connected_station:
                    self.main_connection = True
                    print(f"Connected to ExtStation for {self.name}.")
                else:
                    print(f"Failed to connect to ExtStation for {self.name}.")
                    self.main_connection = False
                    self.connected_station = None
            else:
                raise ValueError(f"Unknown domain: {self.domain}")
            
            print(f"Connected to {self.connected_station.name} for {self.name}.")


    def _sync_with_main(self):
        """
        Synchronize with the MainStation.

        This sends local events to the MainStation and retrieves
        events back from the MainStation.
        
        """
        with self._main_station_lock:
            if not self.main_connection:
                if self.able_to_connect():
                    self._connect_to_main_station(self.domain)
                    if not self.main_connection:
                        raise ValueError(f"{self.name} cannot connect to the MainStation.")
                else:
                    raise ValueError(f"{self.name} cannot connect to the MainStation.")
                
            try:
                # send events to the MainStation
                serialized_events = self._serialize_events(self.event_history)
                self.connected_station.send(('events', serialized_events))

                # receive events from the MainStation
                self.connected_station.send(('get_events', None))
                message_type, data = self.connected_station.receive()

                if message_type == 'events':
                    remote_events = self._deserialize_events(data)
                    self._add_events_to_history(remote_events)
                    print(f"{self.name}: Received {len(remote_events)} events from "
                          f"{self.connected_station.name}.")
                    
                else: 
                    print(f"{self.name}: Unexpected message type from "
                          f"{self.connected_station.name}: {message_type}.")
                    
                self.last_sync = sktime.now()

            except Exception as e:
                print(f"{self.name}: Error syncing with MainStation: {e}")
                

    def register_bus(self, bus, interests=None):
        """
        Register an EventBus with this BusStation.

        Args:
            bus: The EventBus to register.
            interests: Optional list of event types the bus is interested in.
        
        """
        with self.lock:
            # store a weak reference to the bus
            bus_ref = weakref.ref(bus)
            self.registered_buses[bus_ref] = interests or set()

            # clean up any dead references
            self._clean_registered_buses()

            print(f"{self.name}: Registered EventBus from thread "
                  f"{bus.thread_name} ({bus.thread_id}) with "
                  f"{len(interests or set())} interests.\n")
            
    def unregister_bus(self, bus):
        """
        Unregister an EventBus from this BusStation.

        Args:
            bus: The EventBus to unregister.
        
        """
        with self.lock:
            # find and remove the bus reference
            for bus_ref in list(self.registered_buses.keys()):
                referenced_bus = bus_ref()
                if referenced_bus is bus or referenced_bus is None:
                    self.registered_buses.pop(bus_ref, None)

                print(f"{self.name}: Unregistered EventBus from thread "
                        f"{bus.thread_name} ({bus.thread_id}).\n")
                
        
    def _clean_registered_buses(self):
        """
        Clean up any dead bus references.

        This removes any weakrefs to buses that have been garbage collected.
    
        """
        for bus_ref in list(self.registered_buses.keys()):
            if bus_ref() is None:
                self.registered_buses.pop(bus_ref, None)
                print(f"{self.name}: Cleaned up dead bus reference.\n")

    def distribute_events(self, events: List[Event]):
        """
        Distribute events to interested EventBuses.

        This sends events to all registered buses that have indicated
        interest in the event's type.

        Args:
            events: List of events to distribute.
        
        """
        if not events:
            return
        
        with self.lock:
            # clean up any dead references
            self._clean_registered_buses()

            # for each bus, send events it is interested in
            for bus_ref, interests in self.registered_buses.items():
                bus = bus_ref()
                if bus is None:
                    continue

                # filter events based on interests
                if not interests:
                    continue

                matching_events = []
                for event in events:
                    if self._type_matches_interests(event, interests):
                        matching_events.append(event)

                
                if matching_events:
                    try:
                        bus._add_events_to_history(matching_events)
                        print(f"{self.name}: Distributed {len(matching_events)} "
                              f"events to bus {bus.thread_name}.\n")
                    except Exception as e:
                        print(f"{self.name}: Error distributing events to bus "
                                f"{bus.thread_name}: {e}\n")
                        

                        









