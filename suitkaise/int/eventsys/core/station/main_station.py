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

# suitkaise/int/eventsys/core/station/main_station.py

"""
Module holding the abstract MainStation class for managing all events on one side of 
the EventBridge. This class inherits from the Station class, and is the main manager 
and chronicler of either all internal (IntStation) or external (ExtStation) events. 
IntStation and ExtStation inherit from this abstract class, and implement the methods
specific to their respective event systems. Communicates will all BusStations
in processes dedicated to their side of the EventBridge. Responsible for all cross-process
communication and event management, and gathers events from all BusStations and the
opposite MainStation.

"""

import threading
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Type, Optional, Any, Tuple

from suitkaise.int.eventsys.data.enums.enums import (
    StationLevel, BridgeDirection, BridgeState, SKDomain
    )
from suitkaise.int.eventsys.events.base_event import Event
from suitkaise.int.eventsys.core.station.station import Station
from suitkaise.int.eventsys.core.station.bus_station import BusStation
import suitkaise.int.time.sktime as sktime
import suitkaise.int.domain.get_domain as get_domain

class MainStation(Station, ABC):
    """
    Abstract base class for main event stations (IntStation and ExtStation).

    The MainStation acts as the central repository for either all internal
    or all external events, and interfaces (works) with:

    1. All BusStations on its side of the Bridge (SKDomain.INTERNAL or SKDomain.EXTERNAL)
    2. The other MainStation through the EventBridge

    MainStation is responsible for:
    - Cross-process communication with BusStations
    - Distributing events to appropriate BusStations
    - Communication with the opposite MainStation through the EventBridge
    - Maintaining a complete history of all events on its side

    This is an abstract class - use IntStation or ExtStation.
    
    """

    def __init__(self):
        """
        Initialize the MainStation.

        The MainStation's name will be either IntStation or ExtStation, depending on
        the process it is running in. The station name will be handled by IntStation or
        ExtStation, and is not specifically set here.
        
        """
        super().__init__()
        
        # registry of connected BusStations
        self.bus_stations = {} # dict of BusStations by process ID
        self.bus_stations_lock = threading.Lock()   

        # connection to EventBridge
        self.bridge = None

        # station level
        self.station_level = StationLevel.MAIN

        # inter station messaging
        self.received_messages = {} # maps bus name to received message
        self.requests = {} # maps bus id to request
        self.replies = {} # maps bus id to processed replies

        # settings and state
        self.domain = get_domain.get_domain()
        self.auto_sync = True
        self.ext_sync_interval = 15.0 # seconds between syncs
        self.compression_interval = 90.0 # seconds between compressions
        self.history_size_limit = 150 * 1024 * 1024 # 150 MB
        self.compress_threshold = 100 * 1024 * 1024 # 100 MB

        self._sync_thread = None
        self._compression_thread = None
        self._running = False

        self._init_background()

        print(f"Created {self.__class__.__name__} with domain {self.domain.name}")

    @abstractmethod
    def _init_background(self) -> None:
        """
        Initialize and start background tasks for the MainStation.

        IntStation and ExtStation will implement this method to start their
        specific background tasks. This is called during the initialization
        of the MainStation.

        This should:
        1. Start the thread to periodically sync with the other MainStation
        using the EventBridge.
        2. Start the thread to periodically compress events in the event
        history.
        
        """
        pass


    def _sync_yawn(self) -> None:
        """
        Circuit breaker for the synchronization thread.
        
        This will pause the synchronization thread if too many errors occur,
        rather than raising exceptions, since we want the thread to continue
        running after a cooling-off period.
        
        """
        id = f"{self.name}_sync"
        message = f"{self.name} sync raised errors 3 times within 20 seconds. " \
                 f"Pausing sync operations for 30 seconds."
        
        sktime.yawn(3, 20, 30, id, message_on_sleep=message, dprint=True)

    def _bridge_error_yawn(self) -> bool:
        """
        Circuit breaker for bridge communication errors.
        
        This will raise an exception if too many bridge errors occur,
        as bridge errors likely indicate a serious problem that requires
        attention.
        
        Returns:
            bool: True if an exception was raised, False otherwise
        
        Raises:
            BridgeCommunicationError: If too many bridge errors occur

        """
        id = f"{self.name}_bridge"
        message = f"{self.name} encountered multiple bridge communication errors."
        
        try:
            return sktime.yawn(3, 15, 0, id,
                             message_on_sleep=message,
                             exception_on_sleep=RuntimeError,
                             dprint=True)
        except RuntimeError as e:
            # Log the error before re-raising
            print(message)
            raise


# 
# Bus registration methods
#

    def register_bus_station(self, station: BusStation) -> None:
        """
        Register a BusStation with this MainStation.

        This establishes a connection between the MainStation and a 
        BusStation on its side of the EventBridge. This can be BusStations
        from other processes, or the local BusStation in the same process.
        The MainStation will then be able to send and receive events
        from this BusStation.

        Args:
            station (BusStation): The BusStation to register.
        
        """
        with self.bus_stations_lock:
            process_id = station.process_id

            if process_id in self.bus_stations:
                # BusStation already registered
                print(f"BusStation {process_id} already registered with {self.name}")
                return
            
            # Register the BusStation
            self.bus_stations[process_id] = station
            print(f"Registered BusStation {process_id} with {self.name}")


    def unregister_bus_station(self, process_id: int) -> None:
        """
        Unregister a BusStation from this MainStation.

        This removes the connection between the MainStation and a
        BusStation on its side of the EventBridge.

        Args:
            process_id (int): The process ID of the BusStation to unregister.

        """
        with self.bus_stations_lock:
            if process_id not in self.bus_stations:
                # BusStation not registered
                print(f"BusStation {process_id} not registered with {self.name}")
                return
            
            # Unregister the BusStation
            del self.bus_stations[process_id]
            print(f"Unregistered BusStation {process_id} from {self.name}")

    
    def get_bus_station(self, process_id: int) -> Optional[BusStation]:
        """
        Get a BusStation by process ID.

        Args:
            process_id (int): The process ID of the BusStation to get.

        Returns:
            Optional[BusStation]: The BusStation with the given process ID, 
            or None if not found.
        
        """
        with self.bus_stations_lock:
            return self.bus_stations.get(process_id, None)
        
    
    def get_bus_station_by_name(self, name: str) -> Optional[BusStation]:
        """
        Get a BusStation by name.

        Args:
            name (str): The name of the BusStation to get.

        Returns:
            Optional[BusStation]: The BusStation with the given name, 
            or None if not found.
        
        """
        with self.bus_stations_lock:
            for station in self.bus_stations.values():
                if station.name == name:
                    return station
            return None
        
        
# 
# Event distribution methods
#

    def has_interest_in(self, event_type: Type) -> bool:
        """
        Check if this MainStation has interest in a specific event type.

        Args:
            event_type (Type[Event]): The event type to check.

        Returns:
            bool: True if the MainStation has interest in the event type,
            False otherwise.
        
        """
        # MainStation is interested in all events
        return True

    def distribute_events(self, events: List[Event]) -> None:
        """
        Distribute events to all registered BusStations,
        based on their interests.

        Args:
            events (List[Event]): The list of events to distribute.

        """
        # group events by type for distribution
        events_by_type = {}
        for event in events:
            event_type = event.event_type
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)

        # distribute events to BusStations
        with self.bus_stations_lock:
            for event_type, event_list in events_by_type.items():
                for process_id, station in self.bus_stations.items():
                    if station.has_interest_in(event_type):
                        try:
                            station.add_event(event)
                            print(f"Distributed {event.idshort} to BusStation "
                                  f"{process_id} from {self.name}")
                            
                        except Exception as e:
                            print(f"Error distributing event {event.idshort} to "
                                  f"BusStation {process_id}: {e}")
                            
    
    def distribute_event(self, event: Event) -> None:
        """
        Distribute a single event to all registered BusStations,
        based on their interests.

        Args:
            event (Event): The event to distribute.

        """
        self.distribute_events([event])

    
#
# EventBridge communication methods
#

    def connect_to_bridge(self) -> None:
        """
        Connect this MainStation to the EventBridge singleton.

        The EventBridge is used to faciliate communication with the opposite
        MainStation (IntStation or ExtStation).

        It manages the syncing of events between the two MainStations.
        
        """
        from suitkaise.int.eventsys.core.bridge.event_bridge import EventBridge
        self.bridge = EventBridge.get_connection()
        print(f"Connected {self.name} to EventBridge")
        if self.bridge is None:
            raise RuntimeError("Failed to connect to EventBridge")
        

    def _connected_to_bridge(self):
        """Ensure the bridge connection is established, with retry logic."""
        if not self.bridge:
            try:
                self.bridge = self.connect_to_bridge()
                if self.bridge:
                    print(f"{self.name}: connected to EventBridge")
                    return True
                else:
                    print(f"{self.name}: failed to connect to EventBridge")
                    return False
            except Exception as e:
                print(f"{self.name}: error connecting to EventBridge: {e}")
                return False
        return True

        
    
    def get_bridge_info(self) -> Tuple[BridgeDirection, BridgeState]:
        """
        Get information about the EventBridge connection.

        Returns:
            Tuple[BridgeDirection, BridgeState]: A tuple containing the direction
            and state of the EventBridge.
        
        """
        if not self._connected_to_bridge():
            raise RuntimeError(f"{self.name}: cannot connect to EventBridge")
        direction = self.get_bridge_direction()
        state = self.get_bridge_state()
        
    
    def get_bridge_direction(self) -> BridgeDirection:
        """
        Get the direction of communication across the EventBridge.

        Returns:
            BridgeDirection: The direction of communication (INTERNAL or EXTERNAL).
        
        """
        if not self._connected_to_bridge():
            raise RuntimeError("Not connected to EventBridge")
        return self.bridge.get_direction()
    
    
    def get_bridge_state(self) -> BridgeState:
        """
        Get the current state of the EventBridge.

        Returns:
            BridgeState: The current state of the EventBridge.
        
        """
        if not self._connected_to_bridge():
            raise RuntimeError("Not connected to EventBridge")
        return self.bridge.get_state()
    

# 
# Communicating with BusStations
#

    def msg_from_bus_station(self, id: int,
                             message: str,
                             data: Optional[Any] = None) -> None:
        """
        Receive a message from a BusStation.
        Use this to send messages with data from the BusStation to the MainStation.

        Args:
            id (int): The process ID of the BusStation sending the message.
            message (str): The message to send.
            data (Optional[Any]): Optional data to send with the message.
        
        """
        if hasattr(self, "_instance_lock"):
            with self._instance_lock:
                if message in self._valid_msgs:
                    uuid = str(uuid.uuid4())
                    msg_dict = {
                        "process_id": id,
                        "uuid": uuid,
                        "message": message,
                        "data": data,
                        "time_received": sktime.now()
                    }
                    self.received_messages[uuid] = msg_dict
                    print(f"Received message from BusStation {id}: {message}")


    def req_from_bus_station(self, id: int,
                             message: str,
                             data: Optional[Any] = None) -> None:
        """
        Receive a request from a BusStation.
        Requests are messages that need a reply from the MainStation.

        Args:
            id (int): The process ID of the BusStation sending the request.
            message (str): The request message to send.
            data (Optional[Any]): Optional data to send with the request.
        
        """
        if hasattr(self, "_instance_lock"):
            with self._instance_lock:
                now = sktime.now()
                if message in self._valid_msgs:
                    uuid = str(uuid.uuid4())
                    msg_dict = {
                        "process_id": id,
                        "uuid": uuid,
                        "message": message,
                        "data": data,
                        "time_received": now,
                        "request": True
                    }
                    self.received_messages[uuid] = msg_dict
                    print(f"Received request from BusStation {id}: {message}")
        
                
                if message in self._valid_reqs:
                    req_dict = {
                        "process_id": id,
                        "uuid": uuid,
                        "message": message,
                        "data": data if data else None,
                        "time_received": now
                    }
                    self.requests[uuid] = req_dict
                    print(f"Received request from BusStation {id}: {message}")


    def _process_received_messages(self) -> None:
        """
        Process received messages and do something with them.
        This is called periodically to check for new messages and process them.

        How:
        1. Processes all messages that aren't requests.
        2. Processes all requests.
        3. Clears messages responded to.
        After step 3, the dict should be empty.
        
        """
        if hasattr(self, "_instance_lock"):
            with self._instance_lock:
                try:
                    now = sktime.now()
                    msgs_to_clear = []
                    for uuid, message in self.received_messages.items():
                        # check if the message is not a request
                        if not message.get("request", False):
                            # handle non requests now
                            if message.get("data", None) is not None:
                                # process the message
                                self._process_received_data(message)
                            else:
                                # for now, we don't have any messages without data
                                pass
                            msgs_to_clear.append(process_id)

                    # check if there are any requests to process
                    if self.requests:
                        # process the requests
                        self._reply_to_requests()
                        for uuid, message in self.received_messages.items():
                            # check if the request has been replied to
                            id = message.get("id", None)
                            time_received = message.get("time_received", None)
                            for req_id, req in self.requests.items():
                                if not req.get("id", None) == id \
                                and not req.get("time_received", None) == time_received:
                                    # the request has been replied to, so clear it
                                    msgs_to_clear.append(req_id)

                except Exception as e:
                    print(f"Error processing received messages: {e}")
                    raise e
                
                finally:
                    # clear the messages that have been processed
                    if msgs_to_clear:
                        for process_id in msgs_to_clear:
                            self.received_messages.pop(process_id, None)
                        print(f"Cleared {len(msgs_to_clear)} messages after processing")

        

    def _process_received_data(self, message: Dict[str, Any]) -> None:
        """
        Unpack and process received data from messages depending on the message type.
        
        """
        if hasattr(self, "_instance_lock"):
            with self._instance_lock:
                now = sktime.now()
                if message.get("message", None) == 'take_my_bus_station_events':
                    # unpack the data from the message
                    data = message.get("data", None)
                    if data is not None:
                        # process the data
                        events = self._deserialize_events(data)
                        self.add_multiple_events(events)
                    elif message.get("message", None) == 'bus_has_processed_reply':
                        # unpack the data from the message
                        data = message.get("data", None)
                        if data is not None:
                            # process the data
                            for reply in self.replies:
                                if reply == data:
                                    # remove the reply from the replies list
                                    self.replies.pop(reply, None)



    def _reply_to_requests(self):
        """
        Check if there are any requests from BusStations that need a reply,
        and add the reply and its data to the replies list.
        
        """
        if hasattr(self, "_instance_lock"):
            with self._instance_lock:
                try:
                    now = sktime.now()
                    requests_to_clear = []
                    for uuid, request in self.requests.items():
                        # check what the request is
                        if request.get("message", None) == 'get_your_main_station_events':
                            # send the events to the BusStation with this process ID
                            events = self.event_history.copy()
                            # filter based on bus interests
                            process_id = request.get("process_id", None)
                            if process_id is not None:
                                bus_station = self.get_bus_station(process_id)
                                if bus_station:
                                    for event in events:
                                        if not bus_station.has_interest_in(event.event_type):
                                            events.remove(event)

                            data = self._serialize_events(events)
                            # send the data to the BusStation
                            self.replies[process_id] = {
                                'reply_to_id': process_id,
                                'original_request': self.requests[process_id],
                                'message': 'my_main_station_events',
                                'data': data,
                                'time_sent': now
                            }
                            requests_to_clear.append(process_id)
                            print(f"Replied to request from BusStation {process_id}: "
                                  f"{self.requests[process_id]}")
                except Exception as e:
                    print(f"Error replying to requests: {e}")
                    raise e
                
                finally:
                    if requests_to_clear:
                        for process_id in requests_to_clear:
                            self.requests.pop(process_id, None)
                        print(f"Cleared {len(requests_to_clear)} requests after replying")


#
# get methods
#
        

    def get_domain(self) -> SKDomain:
        """
        Get the domain of this MainStation.

        Returns:
            SKDomain: The domain of this MainStation (INTERNAL or EXTERNAL).
        
        """
        return self.domain
    
    
    def get_station_level(self) -> StationLevel:
        """
        Get the station level of this MainStation.

        Returns:
            StationLevel: The station level of this MainStation (MAIN).
        
        """
        return StationLevel.MAIN

            

        

        

