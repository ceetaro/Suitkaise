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
        cyclebuilder.add_part("EventBridge")
        cyclebuilder.split("IntStation", "ExtStation")
        cyclebuilder.add_part_to_split(part_name="ExtStationConfig", split_name="ExtStation")
        cyclebuilder.add_part("BusStation") # adds this part to both the IntStation and ExtStation split
        cyclebuilder.add_part("EventBus")

        self.event_loop = cyclebuilder.build() # builds the cycle with all parts and splits

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


