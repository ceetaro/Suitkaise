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

# suitkaise/int/eventsys/core/station/station.py

"""
This 

"""

import threading
import bisect
import weakref
import os
import pickle
from abc import ABC, abstractmethod
from typing import Dict, List, Set, Type, Optional, Any, Union

import suitkaise.int.time.sktime as sktime
import suitkaise.int.utils.math.byte_conversions as byteconv
from suitkaise.int.eventsys.data.enums.enums import (
    StationLevel, EventState, EventPriority, CompressionLevel
)
from suitkaise.int.eventsys.events.base_event import Event
import suitkaise.int.eventsys.keyreg.keyreg as keyreg
import suitkaise.int.eventsys.keyreg.compress_keys as compress_keys

class Station(ABC):
    """
    Abstract base class for all station types in the event system.
    
    Stations are responsible for storing, managing, and distributing events
    across different scopes. This class provides common functionality for
    event storage, chronological ordering, and indexing.
    
    The station hierarchy has two levels:
    1. BusStation: One per process, manages events from all threads in a process
    2. MainStation: Two stations (Internal and External) that communicate
       with BusStations and with each other through a Bridge
    
    This class should not be instantiated directly. Instead, use one of the
    concrete implementations:
    - BusStation: Process-level event management
    - IntStation/ExtStation: Domain-level event management

    """
    _valid_msgs = [
        'get_your_main_station_events', 
        'take_my_bus_station_events',
        'my_main_station_events'
        'bus_has_processed_reply'
        ]
    _valid_reqs = ['get_your_main_station_events']
    _valid_replies = ['my_main_station_events']

    def __init__(self):
        """
        Initialize a new Station.

        Args:
            
        """
        self.process_id = os.getpid() # process ID
        self.process_name = f"Process-{self.process_id}" # process name

        self.name = f"Station-{self.process_id}" # station name
        self.event_history = []

        # lazy indexes
        self.event_type_index = {} # index that maps event types to events
        self.time_posted_index = {} # index that maps event post times to events
        self.key_index = {} # index that maps registered keys to events
        self.thread_index = {} # index that maps threads to events
        self.state_index = {} # index that maps event states to events
        self.priority_index = {} # index that maps event priorities to events

        self.active_indexes = [] # list of indexes currently built

        self.lock = threading.RLock() # lock for thread-safe access

        # config
        self.history_size_limit = None # size limit for the history, in bytes
        self.current_history_size = 0 # current size of the history, in bytes
        self.compress_threshold = None # threshold for compression, in bytes
        self.needs_compressing = False # flag to indicate if compression is needed
        self.event_sizes = {} # cache of event sizes by id

        self.last_compress = None # last compression timestamp

        self.last_clear = None # last clear timestamp
        self.clearing = False # flag to indicate if clearing is in progress

        # last sync timestamp
        self.last_sync = sktime.now()

        print(f"Created new {self.__class__.__name__} '{self.name}' "
              f"with PID {self.process_id} and name {self.process_name}")
        

    #
    # ABSTRACT METHODS
    #

    @abstractmethod
    def get_station_level(self) -> StationLevel:
        """
        Get the station level.

        Returns:
            StationLevel: the station level
        
        """
        pass

    @abstractmethod
    def distribute_events(self, events: List[Event]) -> None:
        """
        Distribute events to the appropriate stations.

        Args:
            events (List[Event]): the events to distribute
        
        """
        pass
        
    #
    # EVENT MANAGEMENT METHODS
    #
    
    def add_event(self, event: Event) -> None:
        """
        Add an event to the station's history,
        in chronological order.

        Args:
            event (Event): the event to add
        
        """
        with self.lock:
            # add the event to the history
            self._add_to_history(event)

            # calculate the size of the event
            event_size = self._calculate_event_size(event)
            self.current_history_size += event_size
            
            # update the indexes
            # use the single event method for small batches
            self._update_indexes_single(event)

            # check if we need to manage the history size
            # and update the needs_compressing flag
            self._manage_history()

            # process the event according to station rules
            self.distribute_events([event])

            print(f"Added event {event.event_type_name} ({event.idshort}) "
                  f"to station '{self.name}'\n"
                  f"Event size: {event_size} bytes\n")
            
            
    def add_multiple_events(self, events: List[Event]) -> None:
        """
        Add multiple events to the station's history,

        More efficient than adding them one by one.

        Args:
            events (List[Event]): the events to add
        
        """
        if not events:
            return
        
        with self.lock:
            # calculate total size of new events
            batch_size = 0
            for event in events:
                event_size = self._calculate_event_size(event)
                batch_size += event_size

            # combine existing history with new events
            combined = self.event_history + events

            # sort the combined list by post time
            def get_timestamp(event):
                try:
                    return event.data['metadata']['timestamps'].get('posted', 0)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have a valid post time.")
                    return 0
                
            # check for duplicates
            seen_ids = set()
            for event in events:
                if hasattr(event, 'id') and event.id in seen_ids:
                    combined.remove(event)
                    print(f"Duplicate event {event.event_type_name} ({event.idshort}) "
                          "found in batch, skipping.")
                else:
                    seen_ids.add(event.id)
                
            self.event_history = sorted(combined, key=get_timestamp)

            # update the current history size
            self.current_history_size += batch_size

            # update active indexes
            self._update_indexes_multiple(events)

            # check if we need to manage the history size
            # and update the needs_compressing flag
            self._manage_history()

            # process the events according to station rules
            self.distribute_events(events)

            print(f"Added {len(events)} events to station '{self.name}'\n"
                  f"Batch size: {batch_size} bytes\n")
    
    def _add_to_history(self, event: Event) -> None:
        """
        Add a single event to the station's history,

        Args:
            event (Event): the event to add
        
        """
        # get the timestamp
        def get_timestamp(event):
            try:
                return event.data['metadata']['timestamps'].get('posted', 0)
            except (AttributeError, KeyError):
                print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                      "does not have a valid post time.")
                return 0
            
        timestamp = get_timestamp(event)

        # use binary search to find the correct position
        timestamps = [get_timestamp(e) for e in self.event_history]
        index = bisect.bisect_left(timestamps, timestamp)

        # insert the event at the correct position
        self.event_history.insert(index, event)
        
    def clear_history(self) -> None:
        """Clear the station's event history, and its indexes."""
        with self.lock:
            self.event_history = []
            self.event_type_index = {}
            self.time_posted_index = {}
            self.key_index = {}
            self.thread_index = {}
            self.state_index = {}
            self.priority_index = {}
            self.active_indexes = []

            # update the last clear timestamp
            self.last_clear = sktime.now()

            print(f"Cleared history and indexes for station '{self.name}'")

    #
    # INTERESTS
    # 

    def has_interest_in(self, event_type: Type) -> bool:
        """
        Check if the station is interested in a specific event.

        Should be overridden by subclasses.

        Args:
            event_type (Type): the event type to check

        Returns:
            bool: True if the event type is of interest, False otherwise
        
        """
        return False
            

    #
    # EVENT SIZE AND SPACE MANAGEMENT
    #
            
    def _calculate_event_size(self, event: Event) -> int:
        """
        Calculate the approximate size of an event in bytes,
        and cache it for future use.

        This uses pickle to serialize the event and get its size.

        Args:
            event (Event): the event to calculate size for

        Returns:
            int: the size of the event in bytes
        
        """
        # check if we have the event size cached
        if hasattr(event, 'id') and event.id in self.event_sizes:
            return self.event_sizes[event.id]
        
        try:
            # use pickle to get the size of the event
            serialized = pickle.dumps(event, protocol=pickle.HIGHEST_PROTOCOL)
            size = len(serialized)

            # cache the size
            if hasattr(event, 'id'):
                self.event_sizes[event.id] = size

            return size
        except Exception as e:
            print(f"Error calculating size for event "
                  f"{getattr(event, 'idshort', 'unknown')}: {e}")
            return 10000 # 10KB safety size for unknown events
            
    def _manage_history(self) -> None:
        """
        Manage the history size and set the needs_compressing flag.

        1. Trims the history if it exceeds size limit,
        by removing events of priority LOWEST.
        2. determines if compression is needed based on timing and size
        3. updates compression flags for background processing

        """
        now = sktime.now()

        # check if we need to trim the history
        if self.history_size_limit is not None \
        and self.current_history_size > self.history_size_limit:
            print(f"History size limit exceeded for station '{self.name}' "
                  f"({byteconv.convert_bytes(self.current_history_size)})\n"
                  f"Current limit: {byteconv.convert_bytes(self.history_size_limit)}\n")
            
            # first, run a compression manually
            self.needs_compressing = True
            # rush order on event compression with CompressionLevel.HIGH
            self._rush_compress_events()

            if self.current_history_size > self.history_size_limit:
                self._remove_events_from_history()

        # check if we need to compress the history
        should_compress = False
        if self.last_compress is None:
            if self.compress_threshold is not None \
            and self.current_history_size > self.compress_threshold:
                should_compress = True
        elif self.last_compress is not None:
            time_since_last = now - self.last_compress
            if self.compress_threshold is not None \
            and self.current_history_size > self.compress_threshold:
                if time_since_last > 300:
                    should_compress = True
            else:
                if time_since_last > 900:
                    should_compress = True


        should_clear = False
        priorities_to_clear = []
        # clear old events of lower priority at certain times
        if self.last_clear is None:
            last_clear = sktime.get_start_time()
            
        elif self.last_clear is not None:
            last_clear = self.last_clear

        # clear lowest priority events every 2 hours
        if (now - last_clear) > 7200:
            self.clearing = True
            priorities_to_clear = [EventPriority.LOWEST]
            self._clear_old_events(priorities_to_clear)
        # clear low and lowest priority events every 12 hours
        elif (now - last_clear) > 43200:
            self.clearing = True
            priorities_to_clear = [EventPriority.LOWEST, EventPriority.LOW]
            self._clear_old_events(priorities_to_clear)

        
        # update flags for background processing
        self.needs_compressing = should_compress
        if should_compress:
            print(f"Marking station '{self.name}' for compression.\n"
                  f"Current size: {byteconv.convert_bytes(self.current_history_size)}\n"
                  f"Compression threshold: {byteconv.convert_bytes(self.compress_threshold)}\n")

        if self.clearing:
            print(f"Marking station '{self.name}' as currently clearing.\n"
                  f"Clearing events of priority {', '.join([p.name for p in priorities_to_clear])}\n")
                
    def _remove_events_from_history(self) -> None:
        """
        Remove events from the history until it is below the size limit.
        
        This removes events with lowest priority and largest size first,
        progressing to higher priorities as needed.

        """
        removed_count = 0
        removed_size = 0
        bytes_over = self.current_history_size - self.history_size_limit
        
        # Use a copy of the event history to avoid modification issues
        for priority_level in range(EventPriority.LOWEST.value, EventPriority.HIGH.value):
            current_priority = EventPriority(priority_level)
            
            if removed_size >= bytes_over:
                break
                
            # Getting all events of this priority level
            if current_priority not in self.priority_index:
                continue
                
            events_of_priority = self.priority_index[current_priority].copy()
            if not events_of_priority:
                continue
                
            # Sort by size (largest first)
            events_of_priority.sort(key=lambda e: self.event_sizes.get(e.id, 0), reverse=True)
            
            # Remove events until below the limit or out of events
            for event in events_of_priority:
                if bytes_over <= 0:
                    break
                    
                event_size = self.event_sizes.get(event.id, 0)
                
                # Remove from history
                self.event_history.remove(event)
                
                # Update size tracking
                self.current_history_size -= event_size
                bytes_over -= event_size
                removed_count += 1
                removed_size += event_size
                
                # Remove from size cache
                if hasattr(event, 'id'):
                    self.event_sizes.pop(event.id, None)
        
        # Rebuild all indexes after removing events
        self._rebuild_indexes()
        
        print(f"Removed {removed_count} events "
            f"({byteconv.convert_bytes(removed_size)}) "
            f"from station '{self.name}' to meet size limit "
            f"({byteconv.convert_bytes(self.history_size_limit)})\n")
        

    def _clear_old_events(self, priorities: List[EventPriority]) -> None:
        """
        Clear old events with priorities in the given list.

        Args:
            priorities (List[EventPriority]): the priorities to clear
        
        """
        try:
            if not priorities:
                print(f"No priorities provided to clear events from station '{self.name}'")
                return
            
            cleared_count = 0
            cleared_size = 0
            now = sktime.now()

            # age threshold already set in _manage_history()
            for priority in priorities:
                if priority not in self.priority_index:
                    continue

                events = self.priority_index[priority].copy()
                if priority == EventPriority.LOWEST:
                    # remove events older than 2 hours
                    age_limit = now - 7200
                elif priority == EventPriority.LOW:
                    # remove events older than 12 hours
                    age_limit = now - 43200

                for event in events:
                    try:
                        timestamp = event.data['metadata']['timestamps'].get('posted', 0)

                        if timestamp < age_limit:
                            # remove the event from history
                            self.event_history.remove(event)

                            # update size tracking
                            event_size = self._calculate_event_size(event)
                            self.current_history_size -= event_size
                            cleared_size += event_size
                            cleared_count += 1

                            # remove from size cache
                            if hasattr(event, 'id'):
                                self.event_sizes.pop(event.id, None)
                    except (AttributeError, KeyError):
                        print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                            "does not have a valid post time.")
                        continue

            # Rebuild all indexes after removing events
            if cleared_count > 0:
                self._rebuild_indexes()
                self.last_clear = now
                print(f"Cleared {cleared_count} events "
                    f"({byteconv.convert_bytes(cleared_size)}) "
                    f"from station '{self.name}'\n")
        finally:
            # Always reset the clearing flag, even if an exception occurs
            self.clearing = False
        

    #
    # COMPRESSION METHODS
    #
    
    def compress_events(self, level: CompressionLevel = None) -> None:
        """
        Compress events based on priority and size.

        This will optimize memory usage, and will usually be called in the 
        background. Prioritizes compressing low priority events first.

        Will NOT compress events of priority HIGHEST.

        Args:
            level (CompressionLevel): the compression level to use
                (LOW, NORMAL, HIGH)

        """
        with self.lock:
            if self.clearing:
                # loop until the clearing is done
                while self.clearing:
                    loop_start = sktime.now()
                    sktime.sleep(0.5)
                    sktime.yawn(5, 3, 5, f"{self.name} waiting for clearing to finish", dprint=True)
                    loop_end = sktime.now()
                    # if we slept for 5 secs after hitting yawn_limit...
                    if sktime.elapsed(loop_start, loop_end) > 5:
                        print(f"{self.name} is clearing events, event compression paused.\n")


            start_time = sktime.now()
            print(f"Compressing events in station '{self.name}' "
                  f"with compression level {level.name}...\n")
            
            original_size = self.current_history_size
            
            # calculate what level to compress at based on size
            if level is None:
                size_range = 1 - (self.compress_threshold / self.history_size_limit)
                # split the range into 3 levels
                weak_range = self.compress_threshold + (0.4 * size_range)
                reg_range = self.compress_threshold + (0.7 * size_range)

                if (self.current_history_size / self.history_size_limit) < weak_range:
                    level = CompressionLevel.LOW
                elif (self.current_history_size / self.history_size_limit) < reg_range:
                    level = CompressionLevel.NORMAL
                else:
                    level = CompressionLevel.HIGH
            
            # collect events based on level.
            low_compress_events = []
            normal_compress_events = []
            high_compress_events = []
            if level == CompressionLevel.LOW:
                # compress low priority events
                low_compress_events = self.priority_index[EventPriority.LOW]
                high_compress_events = self.priority_index[EventPriority.LOWEST]

            elif level == CompressionLevel.NORMAL:
                # compress low and normal priority events
                low_compress_events = self.priority_index[EventPriority.NORMAL]
                normal_compress_events = self.priority_index[EventPriority.LOW]
                high_compress_events = self.priority_index[EventPriority.LOWEST]

            elif level == CompressionLevel.HIGH:
                # compress all events except EventPriority.HIGHEST
                normal_compress_events = self.priority_index[EventPriority.HIGH, EventPriority.NORMAL]
                high_compress_events = self.priority_index[EventPriority.LOW, EventPriority.LOWEST]

            # compress the events, and add a compressed key to metadata
            self._low_compression(low_compress_events)
            self._normal_compression(normal_compress_events)
            self._high_compression(high_compress_events)

            compress_count = len(low_compress_events) + \
                len(normal_compress_events) + len(high_compress_events)
            current_size = self.current_history_size
            size_reduction = original_size - current_size

            # update the last compression timestamp
            self.last_compress = sktime.now()

            # reset the needs_compressing flag
            self.needs_compressing = False

            elapsed_time = sktime.elapsed(start_time, self.last_compress)
            print(f"Compressed {compress_count} events "
                  f"({byteconv.convert_bytes(size_reduction)}) "
                  f"from station '{self.name}'.\n"
                  f"Original size: {byteconv.convert_bytes(original_size)}\n"
                  f"Current size: {byteconv.convert_bytes(current_size)}\n"
                  f"Compression took {elapsed_time} seconds\n")
            
            
    def _low_compression(self, events: List[Event]) -> None:
        """
        Apply low level compression to events designated as
        'low_compress_events' in the compress_events() method.

        Args:
            events (List[Event]): the events to compress at low level
        
        """
        for event in events:
            for key in event.data.keys():
                if keyreg.is_registered(key):
                    key_name = key.__name__
                    value = event.data[key]
                    compressed = compress_keys.compress(key_name, value, 
                                                        CompressionLevel.LOW)
                else:
                    print(f"Key '{key}' not registered with keyreg.")

                event.data[key] = key

    def _normal_compression(self, events: List[Event]) -> None:
        """
        Apply normal level compression to events designated as
        'normal_compress_events' in the compress_events() method.

        Args:
            events (List[Event]): the events to compress at normal level

        """
        for event in events:
            for key in event.data.keys():
                if keyreg.is_registered(key):
                    key_name = key.__name__
                    value = event.data[key]
                    compressed = compress_keys.compress(key_name, value, 
                                                        CompressionLevel.NORMAL)
                else:
                    print(f"Key '{key}' not registered with keyreg.")

                event.data[key] = key
        

    def _high_compression(self, events: List[Event]) -> None:
        """
        Apply high level compression to events designated as
        'high_compress_events' in the compress_events() method.

        Args:
            events (List[Event]): the events to compress at high level

        """
        for event in events:
            for key in event.data.keys():
                if keyreg.is_registered(key):
                    key_name = key.__name__
                    value = event.data[key]
                    compressed = compress_keys.compress(key_name, value, 
                                                        CompressionLevel.HIGH)
                    if compressed is None:
                        if keyreg.is_optional(key):
                            event.data.pop(key, None)

                else:
                    print(f"Key '{key}' not registered with keyreg.")

                event.data[key] = key

    def _rush_compress_events(self) -> None:
        """
        Rush compress events in the station's history.

        This is a high-priority compression that should be done
        immediately, regardless of the current compression level.
        
        """
        # TODO : once we setup background processing, implement this
        pass

    #
    # EVENT RETRIEVAL METHODS
    #
    
    def _type_matches_interests(self, event_or_type, interests):
        """
        Helper method to check if an event type matches any of the interests.
        
        Checks both direct matches and parent class matches.
        
        Args:
            event_type: The event type to check
            interests: Set of event types to match against
            
        Returns:
            bool: True if the event type matches any interest, False otherwise
        """
        def get_event_instance_from_type(self, event_type: Type) -> Optional[Event]:
            """Get an event instance from the event type."""
            with self.lock:
                for event in self.event_history:
                    if isinstance(event, event_type):
                        return event.copy()
                return None
            
        if isinstance(event_or_type, type):
            event = get_event_instance_from_type(event_or_type)
        elif isinstance(event_or_type, Event):
            event = event_or_type

        # Direct match
        if event.event_type in interests:
            return True
        elif event.original_class and event.original_class in interests:
            return True
        
        # check direct parent of original class
        if event.original_class and event.original_class.__bases__:
            for base in event.original_class.__bases__:
                if base in interests:
                    return True

        return False
    

    def get_events(self, interests: Optional[Set[Type[Event]]] = None) -> List[Event]:
        """
        Get all events from the station's history that match the given interests.

        Args:
            interests (Optional[Set[Type[Event]]]): a set of event types to filter by

        Returns:
            List[Event]: a list of events matching the interests
                to return to the bus.
        
        """
        with self.lock:
            if not interests:
                print(f"No interests provided to get events from station '{self.name}'")
                return self.event_history
            
            # use the type index for faster lookups
            result = []
            if 'event_type_index' not in self.active_indexes:
                self._build_event_type_index()
            
            # check the type index
            for event_type, events in self.event_type_index.items():
                if self._type_matches_interests(event, interests):
                    result.extend(events)

            # remove duplicates
            for event in result:
                if any(e.id == event.id for e in result if e != event):
                    print(f"Removing duplicate {event.event_type_name} {event.idshort} "
                          "from results list in station {self.name}'s get_events()")
                    result.remove(event)

            # sort by timestamp before returning
            def get_timestamp(event):
                try:
                    return event.data['metadata']['timestamps'].get('posted', 0)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have a valid post time.")
                    return 0
                
            return sorted(result, key=get_timestamp)
        

    def get_events_in_time_range(self, interests: Optional[Set[Type[Event]]] = None,
                                 start_time: Optional[sktime.TimeValue] = None,
                                 end_time: Optional[sktime.TimeValue] = None
                                 ) -> List[Event]:
        
        """
        Get events in a specific time range, filtered by event type interests.

        sktime.Timevalue = Union[datetime.datetime, str, float, int]

        Args:
            interests: a set of event types to filter by
            start_time: the start time of the range
            end_time: the end time of the range

        Returns:
            List[Event]: a list of events matching the interests and time range
        
        """
        with self.lock:
            # use the timestamp index for faster lookups before filtering by interests
            start_secs = sktime.to_unix(start_time) if start_time is not None else float('-inf')
            end_secs = sktime.to_unix(end_time) if end_time is not None else float('inf')

            if not start_secs or not end_secs:
                print(f"Invalid time range provided to get events from station '{self.name}'")
                return self.get_events(interests)

            if 'time_posted_index' not in self.active_indexes:
                self._build_time_posted_index()

            # filter events by time range first
            result = []
            valid_times = [time for time in self.time_posted_index.keys()
                            if start_secs <= time <= end_secs]
            for valid_time in valid_times:
                result.extend(self.time_posted_index[valid_time])

            # events can only have one timestamp, so no need to check for duplicates

            # filter by interests
            if interests:
                for event in result:
                    event_type = event.event_type if event.event_type else \
                        event.data['metadata'].get('event_type', None)
                    if not self._type_matches_interests(event_type, interests):
                        result.remove(event)

            # sort by timestamp before returning
            def get_timestamp(event):
                try:
                    return event.data['metadata']['timestamps'].get('posted', 0)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have a valid post time.")
                    return 0
                
            return sorted(result, key=get_timestamp)
                    
            
    def get_events_by_key(self, interests: Optional[Set[Type[Event]]] = None,
                          key: str = None) -> List[Event]:
        """
        Get events with a specific key in their event.data.

        Args:
            interests: a set of event types to filter by
            key: the key to filter by

        Returns:
            List[Event]: a list of events matching the interests and key

        """
        with self.lock:
            # use the key index for faster lookups before filtering by interests
            if not key:
                print(f"No key provided to get events from station '{self.name}'")
                return self.get_events(interests)
            
            if 'key_index' not in self.active_indexes:
                self._build_key_index()

            # filter events by key first
            result = []
            if key in self.key_index:
                result.extend(self.key_index[key])
            else:
                print(f"No events found with key '{key}' in station '{self.name}'")
                return []
            
            if interests:
                # filter by interests
                for event in result:
                    event_type = event.event_type if event.event_type else \
                        event.data['metadata'].get('event_type', None)
                    if not self._type_matches_interests(event_type, interests):
                        result.remove(event)

            # sort by timestamp before returning
            def get_timestamp(event):
                try:
                    return event.data['metadata']['timestamps'].get('posted', 0)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have a valid post time.")
                    return 0
                
            return sorted(result, key=get_timestamp)




    def get_events_by_thread(self, interests: Optional[Set[Type[Event]]] = None,
                             identifier = None) -> List[Event]:
        """
        Get events posted from a specific thread.

        Args:
            interests: a set of event types to filter by
            identifier: the thread ID or name to filter by

        Returns:
            List[Event]: a list of events matching the interests and thread
        
        """
        with self.lock:
            if not identifier:
                print(f"No thread identifier provided to get events from station '{self.name}'")
                return self.get_events(interests)

            # use the thread index for faster lookups before filtering by interests
            if 'thread_index' not in self.active_indexes:
                self._build_thread_index()

            # filter events by thread first
            matching_keys = []
            if isinstance(identifier, int):
                # lookup by thread_id
                matching_keys = [(id, name) for id, name in self.thread_index.keys()
                                 if id == identifier]
            elif isinstance(identifier, str):
                # lookup by thread_name
                matching_keys = [(id, name) for id, name in self.thread_index.keys()
                                 if name == identifier]
            elif isinstance(identifier, tuple) and len(identifier) == 2:
                # lookup by thread_id and thread_name
                matching_keys = [(id, name) for id, name in self.thread_index.keys()
                                 if id == identifier[0] and name == identifier[1]]
            else:
                print(f"Invalid thread identifier provided to get events from station '{self.name}'")
                return []
            
            result = []
            for key in matching_keys:
                result.extend(self.thread_index[key])

            if interests:
                # filter by interests
                for event in result:
                    event_type = event.event_type if event.event_type else \
                        event.data['metadata'].get('event_type', None)
                    if not self._type_matches_interests(event_type, interests):
                        result.remove(event)

            # no duplicates to check for, since events can only have one thread
            # sort by timestamp before returning
            def get_timestamp(event):
                try:
                    return event.data['metadata']['timestamps'].get('posted', 0)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have a valid post time.")
                    return 0
                
            return sorted(result, key=get_timestamp)
                

    def get_events_by_state(self, interests: Optional[Set[Type[Event]]] = None,
                            state: EventState = None) -> List[Event]:
        """
        Get events with a specific EventState.

        Args:
            interests: a set of event types to filter by
            state: the event state to filter by

        Returns:
            List[Event]: a list of events matching the interests and state
        
        """
        with self.lock:
            # use the state index for faster lookups before filtering by interests
            if state is None:
                print(f"No state provided to get events from station '{self.name}'")
                return self.get_events(interests)
            
            if 'state_index' not in self.active_indexes:
                self._build_state_index()

            # filter events by state first
            result = []
            if state in self.state_index:
                result.extend(self.state_index[state])

            if interests:
                # filter by interests
                for event in result:
                    event_type = event.event_type if event.event_type else \
                        event.data['metadata'].get('event_type', None)
                    if not self._type_matches_interests(event_type, interests):
                        result.remove(event)

            # no duplicates to check for, since events can only have one state
            # sort by timestamp before returning
            def get_timestamp(event):
                try:
                    return event.data['metadata']['timestamps'].get('posted', 0)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have a valid post time.")
                    return 0
                
            return sorted(result, key=get_timestamp)
            
    
    def get_events_by_priority_range(self, interests: Optional[Set[Type[Event]]] = None,
                                     min_priority: Union[int, EventPriority] = EventPriority.LOWEST,
                                     max_priority: Union[int, EventPriority] = EventPriority.HIGHEST
                                     ) -> List[Event]:
        """
        Get events with a specific EventPriority range.

        Args:
            interests: a set of event types to filter by
            min_priority: the minimum event priority to filter by
            max_priority: the maximum event priority to filter by

        """
        with self.lock:
            if not min_priority and not max_priority:
                print(f"No priority range provided to get events from station '{self.name}'")
                return self.get_events(interests)

            # use the priority index for faster lookups before filtering by interests
            if isinstance(min_priority, int):
                min_priority = EventPriority(min_priority)
            if isinstance(max_priority, int):
                max_priority = EventPriority(max_priority)

            if 'priority_index' not in self.active_indexes:
                self._build_priority_index()

            # filter events by priority first
            valid_priorities = []
            for priority in EventPriority:
                if priority > min_priority or priority < max_priority:
                    valid_priorities.append(priority)

            result = []
            for priority in valid_priorities:
                if priority in self.priority_index:
                    result.extend(self.priority_index[priority])

            if interests:
                # filter by interests
                for event in result:
                    event_type = event.event_type if event.event_type else \
                        event.data['metadata'].get('event_type', None)
                    if not self._type_matches_interests(event_type, interests):
                        result.remove(event)

            # no duplicates to check for, since events can only have one priority
            # sort by timestamp before returning
            def get_timestamp(event):
                try:
                    return event.data['metadata']['timestamps'].get('posted', 0)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have a valid post time.")
                    return 0

            return sorted(result, key=get_timestamp)

    #
    # INDEX MANAGEMENT METHODS
    #
    
    def _build_event_type_index(self) -> None:
        """
        Build/rebuild the event type index.

        Uses event_type, not event_type_name.

        Maps event types to lists of events of each type.
        Also adds the index to the active indexes list, self.active_indexes.
        
        """
        with self.lock:
            # use the event history to build the index

            # clear the existing index
            self.event_type_index = {}

            # iterate through the event history
            for event in self.event_history:
                event_type = event.event_type if event.event_type else \
                    event.data['metadata'].get('event_type', None)
                
                if event_type not in self.event_type_index:
                    self.event_type_index[event_type] = []

                self.event_type_index[event_type].append(event)

            if 'event_type_index' not in self.active_indexes:
                self.active_indexes.append('event_type_index')

            print(f"Built event type index for station '{self.name}' "
                  f"with {len(self.event_type_index)} event types")


    def _build_time_posted_index(self) -> None:
        """
        Build the time posted index.

        Maps timestamps to lists of events posted at that time.
        Also adds the index to the active indexes list, self.active_indexes.
        
        """
        with self.lock:
            # use the event history to build the index

            # clear the existing index
            self.time_posted_index = {}

            # iterate through the event history
            for event in self.event_history:
                try:
                    timestamp = event.data['metadata']['timestamps'].get('posted', 0)

                    if timestamp not in self.time_posted_index:
                        self.time_posted_index[timestamp] = []

                    self.time_posted_index[timestamp].append(event)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have a valid post time for indexing.")
                    

            if 'time_posted_index' not in self.active_indexes:
                self.active_indexes.append('time_posted_index')

            # get oldest and newest timestamps
            if self.time_posted_index:
                oldest = min(self.time_posted_index.keys())
                newest = max(self.time_posted_index.keys())

            fmtd_oldest = sktime.to_custom_time_format(oldest)
            fmtd_newest = sktime.to_custom_time_format(newest)

            print(f"Built time posted index for station '{self.name}' "
                    f"with {len(self.time_posted_index)} timestamps.\n"
                    f"Oldest timestamp: {fmtd_oldest}\n"
                    f"Newest timestamp: {fmtd_newest}\n")
                 

    def _build_key_index(self) -> None:
        """
        Build the key index.

        Maps registered keys to lists of events with that key.
        Also adds the index to the active indexes list, self.active_indexes.

        This will get more resource intensive the more keys you have
        registered in the EventKeyRegistry. If you want to use this index,
        it is recommended to use clear_index('key_index') to clear it right after.
        
        """
        with self.lock:
            # use the event history to build the index

            # clear the existing index
            self.key_index = {}

            # iterate through the keyreg
            for key in keyreg.get_all_key_names():
                self.key_index[key] = []

            for event in self.event_history:
                try:
                    # get the event keys
                    for key in event.data.keys():
                        if key in self.key_index:
                            self.key_index[key].append(event)
                except (AttributeError, KeyError):
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have valid keys for indexing.")
                    continue

            # finally, remove any empty index keys
            for key in list(self.key_index.keys()):
                if not self.key_index[key]:
                    del self.key_index[key]

            if 'key_index' not in self.active_indexes:
                self.active_indexes.append('key_index')

            print(f"Built key index for station '{self.name}' "
                  f"with {len(self.key_index)} keys present in events.\n")



    def _build_thread_index(self) -> None:
        """
        Build the thread index.

        Maps threads to lists of events posted by that thread.
        Also adds the index to the active indexes list, self.active_indexes.

        Each thread key is a tuple of (thread_id, thread_name), and either 
        the thread_id or thread_name can be used to identify the thread.
        
        """
        with self.lock:
            self.thread_index = {}

            for event in self.event_history:
                try:
                    # extract thread data from event metadata
                    thread_data = event.data['metadata'].get('thread_data', None)
                    thread_id = thread_data.get('id', None) if thread_data else None
                    thread_name = thread_data.get('name', None) if thread_data else None

                    # skip events without proper thread data
                    if not thread_id or not thread_name:
                        print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                              "does not have valid thread data for indexing.")
                        continue

                    # create a thread key
                    thread_key = (thread_id, thread_name)

                    # add to index
                    if thread_key not in self.thread_index:
                        self.thread_index[thread_key] = []

                    self.thread_index[thread_key].append(event)
                except (AttributeError, KeyError):
                    # skip events without proper metadata
                    print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                          "does not have valid metadata for indexing.")
                    continue

            # add to active indexes
            if 'thread_index' not in self.active_indexes:
                self.active_indexes.append('thread_index')

            print(f"Built thread index for station '{self.name}' "
                  f"with {len(self.thread_index)} threads")
            

    def _build_state_index(self) -> None:
        """
        Build the state index.

        Maps event states to lists of events with that state.
        Also adds the index to the active indexes list, self.active_indexes.

        """
        with self.lock:
            self.state_index = {}

            # add all 3 states to the index as keys
            self.state_index[EventState.NONE] = []
            self.state_index[EventState.SUCCESS] = []
            self.state_index[EventState.FAILURE] = []

            for event in self.event_history:
                # get the event state
                event_state = event.state if event.state else EventState.NONE

                self.state_index[event_state].append(event)

            # add to active indexes
            if 'state_index' not in self.active_indexes:
                self.active_indexes.append('state_index')

            print(f"Built state index for station '{self.name}' "
                  f"with {len(self.state_index)} states")
            

    def _build_priority_index(self) -> None:
        """
        Build the priority index.

        Maps event priorities to lists of events with that priority.
        Also adds the index to the active indexes list, self.active_indexes.

        """
        with self.lock:
            self.priority_index = {}

            # add all 5 priorities to the index as keys
            for priority in EventPriority:
                self.priority_index[priority] = []

            for event in self.event_history:
                # get the event priority
                event_priority = event.priority if event.priority else EventPriority.NORMAL

                self.priority_index[event_priority].append(event)

            # add to active indexes
            if 'priority_index' not in self.active_indexes:
                self.active_indexes.append('priority_index')

            print(f"Built priority index for station '{self.name}' "
                  f"with {len(self.priority_index)} priorities")

    def _update_indexes_single(self, event: Event) -> None:
        """
        Update the indexes with a single event.

        Args:
            event (Event): the event to add
        
        """
        # only update active indexes (others aren't built yet)
        if 'event_type_index' in self.active_indexes:
            event_type = event.event_type

            if event_type not in self.event_type_index:
                self.event_type_index[event_type] = []

            self.event_type_index[event_type].append(event)

        if 'time_posted_index' in self.active_indexes:
            try:
                timestamp = event.data['metadata']['timestamps'].get('posted', 0)

                if timestamp not in self.time_posted_index:
                    self.time_posted_index[timestamp] = []

                self.time_posted_index[timestamp].append(event)
            except (AttributeError, KeyError):
                print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                      "does not have a valid post time for indexing.")
                
        if 'key_index' in self.active_indexes:
            try:
                # get the event keys
                for key in event.data.keys():
                    if keyreg.is_registered_key(key):
                        if key not in self.key_index:
                            self.key_index[key] = []
                            self.key_index[key].append(event)

                        # add the event to the index
                        if event not in self.key_index[key]:
                            self.key_index[key].append(event)
            except (AttributeError, KeyError):
                print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                      "does not have valid keys for indexing.")
                pass


        if 'thread_index' in self.active_indexes:
            try:
                thread_data = event.data['metadata'].get('thread_data', None)
                thread_id = thread_data.get('id', None) if thread_data else None
                thread_name = thread_data.get('name', None) if thread_data else None

                if thread_id and thread_name:
                    thread_key = (thread_id, thread_name)

                    if thread_key not in self.thread_index:
                        self.thread_index[thread_key] = []

                    self.thread_index[thread_key].append(event)
            except (AttributeError, KeyError):
                print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                      "does not have valid thread data for indexing.")
                pass

        if 'state_index' in self.active_indexes:
            # get the event state
            event_state = event.state if event.state else EventState.NONE
            self.state_index[event_state].append(event)

        if 'priority_index' in self.active_indexes:
            # get the event priority
            event_priority = event.priority if event.priority else EventPriority.NORMAL
            self.priority_index[event_priority].append(event)

    def _update_indexes_multiple(self, events: List[Event]) -> None:
        """
        Update the indexes with a batch of events.

        Args:
            events (List[Event]): the events to add
        
        """
        if not events:
            print(f"Empty event list provided to update indexes for station '{self.name}'")
            return

        # for small batches, use the single event method
        if len(events) < 10:
            for event in events:
                self._update_indexes_single(event)
            return
        
        # for larger batches, use the multiple event method
        with self.lock:
            # process event type index
            if 'event_type_index' in self.active_indexes:
                events_by_type = {}
                for event in events:
                    event_type = event.event_type
                    if event_type not in events_by_type:
                        events_by_type[event_type] = []
                    events_by_type[event_type].append(event)

                # update the index with the batches
                for event_type, type_events in events_by_type.items():
                    if event_type not in self.event_type_index:
                        self.event_type_index[event_type] = []
                    self.event_type_index[event_type].extend(type_events)

            # process time posted index
            if 'time_posted_index' in self.active_indexes:
                events_by_time = {}
                for event in events:
                    try:
                        timestamp = event.data['metadata']['timestamps'].get('posted', 0)
                        if timestamp not in events_by_time:
                            events_by_time[timestamp] = []
                        events_by_time[timestamp].append(event)
                    except (AttributeError, KeyError):
                        print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                              "does not have a valid post time for indexing.")

                # update the index with the batches
                for timestamp, time_events in events_by_time.items():
                    if timestamp not in self.time_posted_index:
                        self.time_posted_index[timestamp] = []
                    self.time_posted_index[timestamp].extend(time_events)

            # process key index
            if 'key_index' in self.active_indexes:
                events_by_key = {}
                for event in events:
                    try:
                        # get the event keys
                        for key in event.data.keys():
                            if keyreg.is_registered(key):
                                if key not in events_by_key:
                                    events_by_key[key] = []
                                events_by_key[key].append(event)
                    except (AttributeError, KeyError):
                        print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                              "does not have valid keys for indexing.")

                # update the index with the batches
                for key, key_events in events_by_key.items():
                    if key not in self.key_index:
                        self.key_index[key] = []
                    self.key_index[key].extend(key_events)

            # process thread index
            if 'thread_index' in self.active_indexes:
                events_by_thread = {}
                for event in events:
                    try:
                        thread_data = event.data['metadata'].get('thread_data', None)
                        thread_id = thread_data.get('id', None) if thread_data else None
                        thread_name = thread_data.get('name', None) if thread_data else None

                        if thread_id and thread_name:
                            thread_key = (thread_id, thread_name)
                            if thread_key not in events_by_thread:
                                events_by_thread[thread_key] = []
                            events_by_thread[thread_key].append(event)
                    except (AttributeError, KeyError):
                        print(f"Warning: Event {getattr(event, 'idshort', 'unknown')} "
                              "does not have valid thread data for indexing.")

                # update the index with the batches
                for thread_key, thread_events in events_by_thread.items():
                    if thread_key not in self.thread_index:
                        self.thread_index[thread_key] = []
                    self.thread_index[thread_key].extend(thread_events)

            # process state index
            if 'state_index' in self.active_indexes:
                events_by_state = {
                    EventState.NONE: [],
                    EventState.SUCCESS: [],
                    EventState.FAILURE: []
                }

                for event in events:
                    # get the event state
                    event_state = event.state if event.state else EventState.NONE
                    events_by_state[event_state].append(event)

                # update the index with the batches
                for state, state_events in events_by_state.items():
                    if state_events:
                        self.state_index[state].extend(state_events)

            # process priority index
            if 'priority_index' in self.active_indexes:
                events_by_priority = {}
                for priority in EventPriority:
                    events_by_priority[priority] = []

                for event in events:
                    # get the event priority
                    event_priority = event.priority if event.priority else EventPriority.NORMAL
                    events_by_priority[event_priority].append(event)

                # update the index with the batches
                for priority, priority_events in events_by_priority.items():
                    if priority_events:
                        self.priority_index[priority].extend(priority_events)

            print(f"Updated indexes for {len(events)} events in station '{self.name}'")

    
    def _rebuild_indexes(self) -> None:
        """
        Rebuild all active indexes.

        This is called after the history size limit is exceeded
        AND events are removed from the history.
        
        """
        with self.lock:
            print(f"Rebuilding indexes for station '{self.name}'")
            if 'event_type_index' in self.active_indexes:
                self._build_event_type_index()

            if 'time_posted_index' in self.active_indexes:
                self._build_time_posted_index()

            if 'key_index' in self.active_indexes:
                self._build_key_index()

            if 'thread_index' in self.active_indexes:
                self._build_thread_index()

            if 'state_index' in self.active_indexes:
                self._build_state_index()

            if 'priority_index' in self.active_indexes:
                self._build_priority_index()

            print(f"Rebuilt {len(self.active_indexes)} indexes for station '{self.name}'")
        

    def clear_index(self, index_name: str) -> None:
        """
        Clear a specific index.

        Args:
            index_name (str): the name of the index to clear
        
        """
        with self.lock:
            if index_name in self.active_indexes:
                self.active_indexes.remove(index_name)
            else:
                print(f"Index '{index_name}' not found in active indexes "
                      f"for station '{self.name}'")

            if index_name == 'event_type_index':
                self.event_type_index = {}
            elif index_name == 'time_posted_index':
                self.time_posted_index = {}
            elif index_name == 'key_index':
                self.key_index = {}
            elif index_name == 'thread_index':
                self.thread_index = {}
            elif index_name == 'state_index':
                self.state_index = {}
            elif index_name == 'priority_index':
                self.priority_index = {}
            else:
                print(f"Unknown index name '{index_name}' for station '{self.name}'")


# 
# Serialization and Deserialization Methods
#

    def _serialize_events(self, events: List[Event]) -> bytes:
        """
        Serialize events for transmission to the MainStation.

        Args:
            events: List of events to serialize.

        Returns:
            bytes: Serialized events.
        
        """
        try:
            # use pickle to serialize events
            return pickle.dumps(events)
        except Exception as e:
            print(f"{self.name}: Error serializing events: {e}\n")
            return pickle.dumps([])
        

    def _deserialize_events(self, data: bytes) -> List[Event]:
        """
        Deserialize events received from the MainStation.

        Args:
            data: Serialized event data.

        Returns:
            List[Event]: Deserialized events.
        
        """
        try:
            # use pickle to deserialize events
            return pickle.loads(data)
        except Exception as e:
            print(f"{self.name}: Error deserializing events: {e}\n")
            return []

