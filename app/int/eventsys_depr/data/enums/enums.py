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

# suitkaise/int/eventsys/data/enums/enums.py

# enums for events

"""
This module contains enums for the event system that will 
likely be used in more than one file/module.

"""

from enum import Enum, auto, IntEnum
from typing import Any, Dict, Type


class EventState(Enum):
    """
    Enum for the state of an event.

    """
    NONE = None # state before processing
    SUCCESS = 'success' # event completed successfully
    FAILURE = 'failure' # event failed


class EventPriority(IntEnum):
    """
    Enum for the priority of an event.

    This is used for determining what events should get compressed
    or cleaned first from event histories if they reach size limits.

    Also useful for sorting events, either in a queue or for analysis.
    Some events with high priority may be logged when others are not.

    """
    LOWEST = 1 # lowest priority
    LOW = 2 # low priority
    NORMAL = 3 # normal priority
    HIGH = 4 # high priority
    HIGHEST = 5 # highest priority

class ValueType(Enum):
    """
    Enum for the type of value in an event.

    """
    ANY = auto() # any value
    DICT = auto() # dictionary value
    LIST = auto() # list value


class StationLevel(Enum):
    """
    Enum for BusStation levels.

    """
    LOCAL = auto() # local bus station
    MAIN = auto() # main bus station


class CompressionLevel(IntEnum):
    """
    Enum for compression levels.

    """
    NONE = 0 # no compression
    LOW = 1 # low compression
    NORMAL = 2 # normal compression
    HIGH = 3 # high compression


class BridgeDirection(Enum):
    """
    Enum for the direction of communication across the event bridge.

    This defines how events can flow between the internal and external domains.
    - OPEN: Events can flow in both directions.
    - CLOSED: No events can flow in either direction.
    - ONLY_TO_EXT: Events can only flow from internal to external.
    - ONLY_TO_INT: Events can only flow from external to internal.
    
    """
    OPEN = auto() # events can flow in both directions
    CLOSED = auto() # no events can flow in either direction
    ONLY_TO_EXT = auto() # events can only flow from internal to external
    ONLY_TO_INT = auto() # events can only flow from external to internal


class BridgeState(Enum):
    """
    Enum for the control state of the event bridge, which gets changed
    manually by the user.

    - LOCKED: The bridge is locked to the current BridgeDirection.
    - UNLOCKED: The bridge is unlocked and BridgeDirection can be changed by code.
    - FORCE_OPEN: Forces BridgeDirection to change to OPEN, and locks it there.
    - FORCE_CLOSED: Forces BridgeDirection to change to CLOSED, and locks it there.
    
    """
    LOCKED = auto() # bridge is locked to current BridgeDirection
    UNLOCKED = auto() # bridge is unlocked, BridgeDirection can be changed by code
    FORCE_OPEN = auto() # forces BridgeDirection to OPEN, and locks it there
    FORCE_CLOSED = auto() # forces BridgeDirection to CLOSED, and locks it there


    
