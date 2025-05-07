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

# suitkaise/eventsys/keyreg/register_keys.py

"""
Setup file that registers all the default keys for the event system, which are
mostly keys that the event itself will add, like the event type, event ID, etc.

Use this file and its functions in event_mgr.py to register the keys before using
the event system.

"""

import uuid
import threading
from typing import Dict, Any, Type, List, Set, Optional, Union, Callable

from .keyreg import (
    EventKeyRegistry,
    OptionalKeyRegistry,
    register,
    validate,
    is_optional,
)

from suitkaise.eventsys.data.enums.enums import (
    EventState, EventPriority, CompressionLevel
)

def register_default_keys():
    """
    Register a set of default keys on startup.

    This should be called once during initialization of the event system,
    to set up all of the standard keys used.
    
    """
    # register metadata keys
    register("metadata", dict,
                description="Container for event metadata")
    
    register("event_type", type,
                description="Type of event")
    
    register("event_type_name", str,
                description="Name of event type")
    
    register("id", str,
                validator=lambda x: len(x) == 36,
                description="Unique identifier for the event")
    
    register("idshort", str,
                validator=lambda x: len(x) == 8,
                description="First 8 characters of the event ID")
    
    register("state", EventState,
                description="State of the event")
    
    register("priority", EventPriority,
                description="Priority level of the event")
    
    register("timestamps", dict,
                description="Timestamps for the event")
    
    register("created", float,
                description="Creation time of the event",
                optional=True)
    
    register("modified", float,
                description="Last modified time of the event",
                optional=True)
    
    register("completed", float,
                description="Completion time of the event",
                optional=True)
    
    register("posted", float,
                description="Time when the event was posted")
    
    register("thread_data", dict,
                description="Contains thread id and name")
    
    register("thread_id", int,
                description="Id of thread that created the event")
    
    register("thread_name", str,
                description="Name of thread that created the event")
    
    register("lock", str,
                validator=lambda x: any('Lock', 'RLock') in x,
                description="Lock for the event",
                optional=True)
    
    register("kwargs", dict,
                description="Keyword arguments for the event")
    
    register("fixable_exceptions", list,
                description="List of exceptions event's type can handle",
                optional=True)
    
    register("exception", dict,
                description="Exception data if the event failed",
                optional=True)
    
    register("is_optional", bool,
                description="Whether the event is optional")
    
    register("is_uncollectable", bool,
                description="Whether the event can be collected by another event")
    
    register("original_class", type,
                description="Original class of the event before any modifiers")
    
    register("original_class_name", str,
                description="Original class name of the event before any modifiers")
    
    register("failed_states", list,
                description="List of failed states for the event",
                optional=True)
    
    register("succeeded_states", list,
                description="List of succeeded states for the event",
                optional=True)
    
    register("optional_states", list,
                description="List of optional states for the event",
                optional=True)
    
    register("is_compressed", bool,
                description="Whether the event is compressed")
    
    register("highest_compression_level",  CompressionLevel,
                description="Highest level of compression applied to the event")
    
    print("Default keys registered successfully.")
    
    

    

    
    

      
             
             

