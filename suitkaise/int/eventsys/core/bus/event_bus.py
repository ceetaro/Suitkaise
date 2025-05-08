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

# suitkaise/int/eventsys/core/bus/event_bus.py

"""
This module defines the EventBus class, which is an event bus for managing
events within a single thread. It provides methods for posting events,
subscribing to events, and communicating with BusStations. The EventBus
maintains a history of events and allows for filtering and notifying
subscribers based on event types and keys. It also sends these events to
the local station (BusStation) and can propagate them to the main station if needed.

"""

import threading
import bisect
import suitkaise.int.time.sktime as sktime
from typing import Dict, Any, List, Tuple, Optional, Callable, Type, Union, Set
from math import sqrt

from suitkaise.int.eventsys.data.enums.enums import EventState, ValueType, StationLevel
from suitkaise.int.eventsys.events.base_event import Event
import suitkaise.int.domain.get_domain as get_domain

from suitkaise.int.eventsys.context.thread_context import (
    get_or_create_bus, get_current_collector, set_bus
)

class EventBus:
    """
    Thread local event bus that manages events within a single thread.

    The EventBus maintains an event history local to each thread and
    provides methods to publish and subscribe to events. It also provides
    methods to communicate with BusStations.

    Features:
    - thread local event history with chronological ordering
    - subscription system for event callbacks
    - interest based event filtering
    - communication with BusStations for cross thread, or even cross process
      event handling

    Usage:

        bus = EventBus.get_current_bus() # get current thread's bus

        # subscribe to an event
        bus.subscribe(event_type, callback, {'key': value})

        # post an event (usually done by Event._post())
        bus.post(event)

        # sync with the station
        bus.to_station() # send event to a station

        bus.from_station() # receive a new bus from a station

        bus.round_trip() # do both to_station and from_station
    
    """

    def __init__(self):
        """Initialize a new EventBus instance for the current thread."""
        self.event_history = [] # Chronological list of events
        self.subscribers = {}    # {event_type: [{'callback': func, 'keys': {}}]}
        self.lock = threading.Lock() # Lock for thread safety
        self.interests = set() # Event types this bus is interested in

        self.domain = get_domain.get_domain() # Get the current domain

        # collectors
        self.collectors = [] # List of collectors registered with this bus

        # record thread information
        self.thread_id = threading.get_ident()
        self.thread_name = threading.current_thread().name

        # config
        self.history_limit = None # max events to keep in history

        print(f"Created new EventBus for thread: {self.thread_name} ({self.thread_id})")

    @classmethod
    def get_current_bus(cls):
        """
        Get or create the EventBus for the current thread.

        This is the main entry point for accessing the bus.

        Returns:
            EventBus: The EventBus for the current thread.
        
        """
        return get_or_create_bus(cls)


    def post(self, event, to_station=False, 
             station_level: StationLevel = StationLevel.LOCAL):
        """
        Add an event to the bus and notify subscribers.

        This method:
        1. Adds the event to the history in chronological order
        2. Notifies all matching subscribers
        3. Handles collector events if present
        4. Optionally, sends the event to the station immediately
        
        Args:
            event: The event to post
            to_station: Whether to send the event to the station immediately
            station_level: The level of the station to send the event to
                - always travels through the local station first

        """
        with self.lock:
            # add the event to the history
            self._add_to_history(event)

            # notify subscribers
            self._notify_subscribers(event)

            # handle event collectors (events using Event.collect())
            self._handle_collectors(event)

            print(f"Posted event: {event.event_type_name} ({event.idshort}) "
                  f"to bus in thread {self.thread_name} ({self.thread_id})\n")
            
        # send to station if specified, outside the lock
        if to_station:
            self._event_to_station(event, station_level)


    def _event_to_station(self, event, station_level: StationLevel = None):
        """
        Send a single event to the station without creating a new bus.

        This is a lighter operation that is useful when you know a single
        CollectedEvent and its data will be needed by other threads.

        Args:
            event: The event to send to the station
            station_level: The level of the station to send the event to
                - always travels through the local station first
        
        """
        from suitkaise.int.eventsys.core.station import BusStation

        try:
            # first, always send to the local station
            local_station = BusStation.get_station(StationLevel.LOCAL)
            local_station.add_event(event)

            # if the station level is MAIN, send to the main station
            if station_level == StationLevel.MAIN:
                # let the local station handle sending to the main station
                local_station.event_to_main_station(event)

            print(f"Sent event {event.id} to {station_level.name.lower} station")
        except Exception as e:
            print(f"Error sending event to station: {e}")
            
    
    def subscribe(self, event_type, callback, keys=None):
        """
        Register interest in specific events.

        Args:
            event_type: The type of event to subscribe to
            callback: Function to call when matching event occurs
            keys: Optional dict of key-value pairs the event must have.
                  For example: {'file_path': '/path/to/file.py'}
        
        """
        with self.lock:
            # add this event type to our interests
            self.interests.add(event_type)

            # create subscriber entry
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []

            # add the subscription
            self.subscribers[event_type].append({
                'callback': callback,
                'keys': keys if keys else {}
            })

            print(f"Subscribed to {event_type.__name__} "
                  f"events in thread {self.thread_name} ({self.thread_id})")
            
    def unsubscribe(self, event_type, callback):
        """
        Remove a subscription.

        Args:
            event_type: The type of event to unsubscribe from
            callback: The callback function to remove
        
        """
        with self.lock:
            if event_type in self.subscribers:
                # filter out the matching callback
                self.subscribers[event_type] = [
                    sub for sub in self.subscribers[event_type]
                    if sub['callback'] != callback
                ]

                # if no subscribers left, remove the event type
                if not self.subscribers[event_type]:
                    self.subscribers.pop(event_type)
                    self.interests.discard(event_type)


    def to_station(self, station_level: StationLevel = StationLevel.LOCAL):
        """
        Send events to a station.

        If StationLevel is MAIN, this will travel to both the local station
        and then the main station.

        This will:
        1. Add the current bus's events to the station(s) event history
        2. Create a fresh bus for this thread

        Args:
            station_level: The level of the station to send the events to
                - always travels through the local station first

        Returns:
            EventBus: A new bus instance for the current thread

        """
        from suitkaise.int.eventsys.core.station import BusStation
        
        with self.lock:
            # Send events to the appropriate station(s)
            local_station = BusStation.get_station(StationLevel.LOCAL)
            
            # Send all events to the local station
            for event in self.event_history:
                local_station.add_event(event)
            
            # Propagate to main if requested
            if station_level == StationLevel.MAIN:
                local_station.propagate_all_to_main()
            
            # Create a new bus for this thread
            new_bus = self.__class__()
            
            # Set it as the current bus using thread_context
            set_bus(new_bus)
            
            print(f"Sent {len(self.event_history)} events to {station_level.name} station")
            
            # Return the new bus
            return new_bus

        

    def from_station(self, interests=None, station_level=StationLevel.LOCAL, round_trip=False):
        """
        Retrieve events from a station.

        This will get events from the specified station level that 
        match this bus's interests, or only the provided interests if specified.

        Args:
            interests: Optional set of event types to retrieve
                - if not specified, will use this bus's interests
            station_level: The level of the station to retrieve events from
                - always travels through the local station first

        Returns:
            EventBus: This bus instance (for chaining)
    
        """
        from suitkaise.int.eventsys.core.station import BusStation

        with self.lock:
            # use provided interests or default to our own
            event_interests = interests if interests is not None else self.interests

            # skip if no interests
            if not event_interests:
                print("No interests to retrieve from station")
                return self
            
            # get the local station
            local_station = BusStation.get_station(StationLevel.LOCAL)

            # get events from the main station if specified
            if station_level == StationLevel.MAIN:
                # NOTE: from_main_station() will update the main station's history
                # with its own events first (to_main_station() is called)
                if round_trip:
                    events = local_station.from_main_station(round_trip=True)
                else:
                    events = local_station.from_main_station(event_interests)
            else:
                # get events from the local station
                events = local_station.get_events(event_interests)

            # add the events to this bus's history
            self._add_events_to_history(events)

            print(f"Retrieved {len(events)} events from {station_level.name.lower} station")
            if round_trip:
                print(f"Round trip completed.")
            return self
        
    def round_trip(self, station_level=StationLevel.LOCAL):
        """
        Perform a round trip to a station.
        This performs to_station and from_station in direct succession.

        Effectively synchronizes this bus with the station.
        
        Args:
            station_level: The level of the station to send and retrieve events from
                - always travels through the local station first

        Returns:
            EventBus: The new bus instance for the current thread
        
        """
        interests = self.interests.copy()

        # send to station and create a new bus
        new_bus = self.to_station(station_level)

        # retrieve events from the station
        return new_bus.from_station(interests, station_level, round_trip=True)
    
    def _add_to_history(self, event):
        """
        Add an event to the history in chronological order.

        Uses binary search to find correct index for insertion.

        Args:
            event: The event to add
        
        """
        # get the event's timestamp
        metadata = event.data['metadata']
        
        timestamp = metadata['timestamps'].get('posted', None)
        if timestamp is None:
            timestamp = sktime.now()
            metadata['timestamps']['posted'] = timestamp
            print(f"{event.event_type} event ({event.id}) "
                  "has no timestamp, using current time")
            
        # use binary search to find the correct index
        def get_event_timestamp(e):
            timestamps = e.data['metadata']['timestamps']
            timestamp = timestamps.get('posted', 0)
            if timestamp == 0:
                print(f"Found no timestamp for event {e.id}")
            return timestamp
        
        # find insertion index
        timestamps = [get_event_timestamp(e) for e in self.event_history]
        index = bisect.bisect_left(timestamps, timestamp)

        # insert the event at the correct index
        self.event_history.insert(index, event)

    def _add_events_to_history(self, events: List):
        """
        Add multiple events to the history in one batch.
        
        Instead of inserting each event individually with binary search,
        this method:
        1. Combines the existing events and new events
        2. Sorts them all at once by timestamp
        3. Replaces the event history with the sorted result
        
        This is significantly more efficient for large batches.
        
        Args:
            events: List of events to add

        """
        if not events:
            return
            
        with self.lock:
            # If history is empty, just use the new events
            if not self.event_history:
                # Sort the incoming events first
                sorted_events = sorted(events, 
                                    key=lambda e: e.data['metadata']['timestamps'].get('posted', 0))
                self.event_history = sorted_events
                return
                
            # Combine existing history with new events
            combined = self.event_history + events
            
            # Define a key function to get timestamps consistently
            def get_timestamp(event):
                try:
                    return event.data['metadata']['timestamps'].get('posted', 0)
                except (KeyError, AttributeError):
                    print(f"Warning: Event {getattr(event, 'id', 'unknown')} has invalid timestamp data")
                    return 0
            
            # Sort all events at once
            sorted_events = sorted(combined, key=get_timestamp)
            
            # Replace the event history with the sorted result
            self.event_history = sorted_events

    
    def _notify_subscribers(self, event):
        """
        Notify subscribers of an event.

        This method checks the event type and any key filters
        before calling the subscriber's callback function.

        Args:
            event: The event to notify subscribers about
        
        """
        event_type = event.event_type
        
        # check for subs to this event type
        if event_type in self.subscribers:
            self._call_matching_subscribers(event, event_type)

        # check for subs to parent event types recursively
        def check_parent_subs(event_type):
            # check if the event type has a parent
            current = event_type
            parent = current.__bases__[0] if current.__bases__ else None
            while parent and parent != object:
                if parent in self.subscribers:
                    self._call_matching_subscribers(event, parent)
                current = parent
                parent = current.__bases__[0] if current.__bases__ else None

        check_parent_subs(event_type)

    def _call_matching_subscribers(self, event, event_type):
        """
        Call subscribers that match the event type and keys.

        Args:
            event: The event to check against
            event_type: The type of event to check
        
        """
        for subscriber in self.subscribers.get(event_type, []):
            callback = subscriber['callback']
            required_keys = subscriber['keys']

            # skip if keys don't match
            if required_keys:
                # check if all required keys are present in the event
                if not all(event.data.get(k) == v for k, v in required_keys.items()):
                    continue

            # call the callback function
            try:
                callback(event)
            except Exception as e:
                print(f"Error calling subscriber {callback.__name__} "
                      f"for event {event.event_type}: {e}")
                
    
    def _handle_collectors(self, event):
        """Notify collectors about an event."""
        # Use a set to track which collectors have been notified
        notified_collectors = set()
        
        # Check thread-local collector
        collector = get_current_collector()
        if collector and hasattr(collector, 'collect_event'):
            try:
                collector.collect_event(event)
                notified_collectors.add(id(collector))
            except Exception as e:
                print(f"Error notifying collector: {e}")
        
        # Check bus-registered collectors
        for collector in self.collectors:
            # Skip if already notified through thread context
            if id(collector) in notified_collectors:
                continue
                
            if hasattr(collector, 'collect_event'):
                try:
                    collector.collect_event(event)
                except Exception as e:
                    print(f"Error notifying registered collector: {e}")

    def register_collector(self, collector):
        """
        Register an event collector with this bus.
        
        Args:
            collector: The collector to register

        """
        with self.lock:
            if not hasattr(self, 'collectors'):
                self.collectors = []
            if collector not in self.collectors:
                self.collectors.append(collector)
                print(f"Registered collector {collector.idshort} with bus\n")

    def unregister_collector(self, collector):
        """
        Unregister an event collector from this bus.
        
        Args:
            collector: The collector to unregister

        """
        with self.lock:
            if hasattr(self, 'collectors') and collector in self.collectors:
                self.collectors.remove(collector)
                print(f"Unregistered collector {collector.idshort} from bus\n")


    def get_recent_events(self, event_type=None, keys=None, count=None):
        """
        Get recent events from the history.

        This method optionally filters events by type and keys,
        and limits the number of events returned.

        Args:
            event_type: Optional type of event to filter by
            keys: Optional dict of key-value pairs to filter by
            count: Optional maximum number of events to return
        
        """
        if count is None:
            min_count = 20
            count = round(len(self.event_history) // sqrt(3 * len(self.event_history)))
            if count < min_count:
                count = min_count

        with self.lock:
            # filter events by type and keys
            filtered_events = []
            if event_type:
                for event in self.event_history:
                    if isinstance(event, event_type):
                        if keys:
                            if all(event.data.get(k) == v for k, v in keys.items()):
                                filtered_events.append(event)
                        else:
                            filtered_events.append(event)
            else:
                filtered_events = self.event_history
            
            return filtered_events[-count:]


        


            
        


            











        

        
            



        






