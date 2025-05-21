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

# suitkaise/int/eventsys/core/bridge/event_bridge.py

"""
Module containing the highest level component of the event system, the EventBridge.

The EventBridge, or Bridge, is a unique component that doesn't directly handle events
or hold an event history. Instead, its main purpose is to facilitate communication
between the 2 MainStations: IntStation and ExtStation, which are responsible for
events in the source code (under suitkaise/int) and events created by user imported
code (under suitkaise/ext) respectively.

The bridge is responsible for managing the flow of events between these two
stations, ensuring that events can be sent when allowed, but giving the user the 
option to separate the event system into two to test their code without interference
from internal events.

The EventBridge is a singleton with two key attributes:
- 'BridgeDirection': This attribute determines how events can flow between the two
  stations. It has 4 values:
    open: Events can flow freely in both directions.
    closed: Events cannot flow in either direction, and systems are effectively separate.
    only_to_int: Events can only flow from ExtStation to IntStation.
    only_to_ext: Events can only flow from IntStation to ExtStation.

- 'BridgeState': This attribute controls how and if BridgeDirection can be changed.
    It has 4 values:
    locked: The bridge is locked to the current BridgeDirection, until the user unlocks it.
    unlocked: The bridge is unlocked and BridgeDirection can be changed by code.
    force_open: The bridge is forced to change to BridgeDirection open, and then the
        bridge acts as if it were locked.
    force_closed: The bridge is forced to change to BridgeDirection closed, and then
        the bridge acts as if it were locked.

The bridge is also responsible for syncing the 2 MainStations. It does this by waiting
for each of them to call EventBridge.sync(), then combines the event histories and
sets the event histories of both MainStations to the combined history. This allows
the two MainStations to work independently, but still be able to share events when
they need to.

NOTE: MainStation class might need a method so bridge can edit event history.

"""
import threading
from typing import Optional, Dict, Any, Tuple, List, Type, Union

from suitkaise_app.int.eventsys.events.base_event import Event
from suitkaise_app.int.eventsys.data.enums.enums import BridgeDirection, BridgeState
from suitkaise_app.int.eventsys.core.station.int_station import IntStation
from suitkaise_app.int.eventsys.core.station.ext_station import ExtStation
import suitkaise_app.int.utils.time.sktime as sktime

class BridgeError(Exception):
    """Custom exception for the EventBridge."""
    pass

class BridgeConnectionError(BridgeError):
    """Exception raised when the bridge cannot connect to both MainStations."""
    pass

class BridgeCycleError(BridgeError):
    """Exception raised when the bridge cycle cannot be completed."""
    pass

class EventBridge:
    """
    EventBridge singleton that facilitates communication between IntStation and ExtStation.

    The EventBridge is responsible for managing the flow of events between the two
    MainStations: IntStation and ExtStation. It allows events to be sent between
    the two stations, while also giving the user the option to separate the event
    system into two to test their code without interference from internal events.
    
    Has 2 main attributes, BridgeDirection and BridgeState.

    Also responsible for syncing the 2 MainStations by combining their event histories
    and setting the event histories of both MainStations to the combined history.
    
    """
    _bridge = None
    _bridge_lock = threading.RLock()

    def __new__(cls):
        """Control instance creation for the singleton pattern."""
        with cls._bridge_lock:
            if cls._bridge is None:
                cls._bridge = super(EventBridge, cls).__new__(cls)
        return cls._bridge
    
    def __init__(self, 
                 initial_direction: Optional[BridgeDirection] = None,
                 initial_state: Optional[BridgeState] = None):
        """
        Initialize the EventBridge singleton.

        This will only execute once, when the singleton is first created.
        Subsequent calls to EventBridge() will return the existing instance
        without re-initializing.
        
        """
        if hasattr(self, '_initialized') and self._initialized:
            return  
        
        self.name = "BRIDGE"

        # Initialize the bridge direction and state
        self._bridge_direction = initial_direction or BridgeDirection.CLOSED
        self._bridge_state = initial_state or BridgeState.UNLOCKED


        # Initialize the stations
        self.int_station = None
        self.ext_station = None
        self.stations_connected = None
        self._connect_to_main_stations()
        
        # processing thread
        self._bridge_background_thread = None

        # TODO finish once EventCycle is finished
        # NOTE: EventCycle needs to be built off of Cycle class,
        #       which is also not yet finished.