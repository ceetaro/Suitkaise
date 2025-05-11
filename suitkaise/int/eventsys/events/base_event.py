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

# suitkaise/int/eventsys/events/base_event.py

"""
This module contains the base event class for the event system. Events that 
want to use the main event system should inherit from the Event class in this
module. This class implements the context manager protocol, allowing events
to be used in a with statement, and automatically posting the event when the block
exits. It also handles state tracking, data storage, and event posting.

"""

import contextlib
import uuid
import datetime
import threading
import suitkaise.int.utils.time.sktime as sktime
from typing import Dict, Any, Optional, Tuple, Union, Type, List

from suitkaise.int.eventsys.data.enums.enums import EventState, EventPriority

from suitkaise.int.eventsys.context.thread_context import (
    push_collector, pop_collector, set_parent_collector, get_parent_collector
)

import suitkaise.int.eventsys.keyreg.keyreg as keyreg
import suitkaise.int.utils.formatting.format_data as fmt

class Event:
    """
    Base event class using context manager protocol.

    This class is the foundation for all events in the system. It implements:
    - Context managers to create auto posting event blocks
    - State tracking
    - Data storage and validation
    - Event posting mechanism

    Usage:
    with MyEvent() as event:
    
        # do something
        if success_condition_met:
            event.success()
        else:
            event.failure()
        event.add_data('key', value)

    * auto post on __exit__
    
    """
    def __init__(self, **kwargs):
        """
        Initialize a new event.

        Args:
            **kwargs: Additional parameters for the event
        
        """
        self.event_type = self.__class__
        self.event_type_name = self.get_event_type_name()
        self.id = str(uuid.uuid4())
        self.idshort = self.id[:8] # short id for debugging
        self.state = EventState.NONE
        self.priority = None # set to default in _set_default_event_priority()
        self._set_default_event_priority() # set self.priority to default
        self.data = {} 
        self.kwargs = kwargs

        # store timestamps
        self.timestamps = {
            'created': sktime.now(), # creation time
            'modified': None, # time self.data last modified
            'completed': None, # time event block exits
            'posted': None # time event actually posted
        }

        self.fixable_exceptions = [] # list of exceptions that can be fixed

        self._lock = threading.RLock() # nested functions might need the lock too!

    def __enter__(self):
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit the context manager.

        This also handles:
        - Exception handling
        - Event completion
        - Event posting

        Args:
            exc_type: Exception type
            exc_value: Exception value
            traceback: Traceback object

        Returns:
            False: don't suppress exceptions
        
        """
        # handle exceptions
        if exc_type is not None:
            if exc_type in self._get_fixable_exc_types():
                self._fix(exc_type, exc_value, traceback)
            else:
                self.failure()
                self.add_data('exception', {
                    'type': exc_type,
                    'value': exc_value,
                    'traceback': traceback
                })

        # complete the event
        self._complete() # sets completion time and compiles embedded event state data

        if self.state == EventState.SUCCESS:
            self._succeeded()
        elif self.state == EventState.FAILURE:
            self._failed()
        else:
            self.failure()
            self._failed()

        self._convert_to_data() # convert event to data object
        self._post() # post the event

        return False # do not suppress exceptions
    
    
    def success(self):
        """Set the event state to success."""
        if self.state != EventState.FAILURE:
            with self._lock:
                self.state = EventState.SUCCESS
                self.timestamps['modified'] = sktime.now()
        
        print(f"{self.event_type_name} {self.idshort} changed to success state.")

    def failure(self):
        """Set the event state to failure."""
        with self._lock:
            self.state = EventState.FAILURE
            self.timestamps['modified'] = sktime.now()

        print(f"{self.event_type_name} {self.idshort} changed to failure state.")


    def add_data(self, key: str, value: Any): 
        """
        Add data to the event context.

        Args:
            key: Key for the data
            value: Value for the data

        Note:
            keys must be registered in the EventKeyRegistry (keyreg)
            and value type must match that of the value type registered 
            with the key.

            If this is a large piece of data, it might be subject to 
            compression if this event goes over the size limit.
        
        """
        with self._lock:
            if keyreg.validate(key, value):
                if key not in self.data.keys():
                    self.data[key] = value
                    self.timestamps['modified'] = sktime.now()

        print(f"{self.event_type_name} {self.idshort} added data: {key} = {value}")

    def group_add_data(self, 
                       data: Union[Dict[str, Any], List[Dict[str, Any]]]):
        """
        Add multiple separate data entries using one call.

        Use this if you have a list of dicts or a dict of key-value pairs
        that you want to add to the event data as separate entries.

        Args:
            data: Dictionary of key-value pairs to add
                - dict: each key-value pair in the dict is added separately
                - list: each item in the list is a key-value pair
        
        """
        with self._lock:
            if isinstance(data, dict):
                for key, value in data.items():
                    if keyreg.validate(key, value):
                        if key not in self.data.keys():
                            self.data[key] = value
                            self.timestamps['modified'] = sktime.now()
            elif isinstance(data, list):
                # each item in the list is a key-value pair
                for item in data:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if keyreg.validate(key, value):
                                if key not in self.data.keys():
                                    self.data[key] = value
                                    self.timestamps['modified'] = sktime.now()
                    else:
                        print(f"Item {item} is not a key-value pair.")

        print(f"{self.event_type_name} {self.idshort} added data: "
              f"{fmt.format_data(data)}\n")

    def _convert_to_data(self, other_vars: Optional[List[str]] = None):
        """
        Turn the event into one data object.

        Self vars to convert:
        - event_type
        - id
        - state
        - kwargs
        - timestamps
        - fixable_exceptions

        Thread info to convert:
        - lock as a string (for debugging)
        - thread name
        - thread id

        Other vars would be any variables passed in by class modifiers
        like invert() or optional().
        
        """
        if hasattr(self.data, 'metadata'):
            if isinstance(self.data['metadata'], dict):
                pass
            else:
                self.data['metadata'] = {}
        else:
            self.data['metadata'] = {}

        # add self vars to metadata
        self.data['metadata']['event_type'] = self.event_type
        self.data['metadata']['event_type_name'] = self.event_type_name
        self.data['metadata']['id'] = self.id
        self.data['metadata']['idshort'] = self.idshort
        self.data['metadata']['state'] = self.state
        self.data['metadata']['priority'] = self.priority
        self.data['metadata']['kwargs'] = self.kwargs
        self.data['metadata']['timestamps'] = self.timestamps
        self.data['metadata']['fixable_exceptions'] = self.fixable_exceptions

        # add thread info to metadata
        self.data['metadata']['thread_data'] = {}

        thread_data = self.data['metadata']['thread_data']
        thread_data['name'] = threading.current_thread().name
        thread_data['id'] = threading.get_ident()
        thread_data['lock'] = str(self._lock)

        if other_vars is not None:
            for var in other_vars:
                if hasattr(self, var):
                    self.data['metadata'][var] = getattr(self, var)
                else:
                    print(f"Variable {var} not found in event class.")



    def _succeeded(self):
        """
        Handle successful event completion.

        This is called when the event's state becomes 
        and remains success until __exit__.
        
        """
        with self._lock:
            self.state = EventState.SUCCESS

    def _failed(self):
        """
        Handle failed event completion.

        This is called when the event fails due to state or exception.
        
        """
        with self._lock:
            self.state = EventState.FAILURE

    def _complete(self):
        """
        Complete the event.
        This runs in __exit__ after exception handling.

        Sets the completion time and changes state if event data has
        other event's state data in it.
        
        """
        with self._lock:
            self.timestamps['completed'] = sktime.now()

            necessary_metadata = ['failed_states', 'successful_states', 'optional_states']
            
            # create metadata if not already present
            if hasattr(self.data, 'metadata'):
                if isinstance(self.data['metadata'], dict):
                    pass
                else:
                    self.data['metadata'] = {}
            else:
                self.data['metadata'] = {}

            # add metadata if not present
            for meta in necessary_metadata:
                if meta not in self.data['metadata']:
                    self.data['metadata'][meta] = []

            def create_meta_copy(data):
                """Create a copy of the event to add to metadata."""
                metadata = data.get('metadata', {})  # Use the event's metadata
                meta_copy = {}
                meta_copy['id'] = metadata.get('id', None)
                meta_copy['idshort'] = metadata.get('idshort', None)
                meta_copy['event_type'] = metadata.get('event_type', None)
                meta_copy['event_type_name'] = metadata.get('event_type_name', None)
                meta_copy['state'] = metadata.get('state', None)
                return meta_copy

            # check for collected events
            if 'events' in self.data and self.data['events']:
                for event_data in self.data['events']:

                    meta_copy = create_meta_copy(event_data)

                    event_state = event_data.get('metadata', {}).get('state', EventState.NONE)

                    if not event_data.get('is_optional', False):
                        # check if this collected event is optional
                    
                        # check if this collected event failed
                        if self.state == EventState.SUCCESS or self.state == EventState.NONE:
                            if event_state == EventState.FAILURE:
                                # update our own state to failure
                                self.state = EventState.FAILURE
                                self.data['metadata']['failed_states'].append(meta_copy)
                            elif event_state == EventState.SUCCESS:
                                if self.state == EventState.NONE:
                                    self.state = EventState.SUCCESS
                                self.data['metadata']['successful_states'].append(meta_copy)
                        elif self.state == EventState.FAILURE:
                            if event_state == EventState.SUCCESS:
                                # do NOT update state, as we are already in failure state
                                self.data['metadata']['successful_states'].append(meta_copy)
                            elif event_state == EventState.FAILURE:
                                self.data['metadata']['failed_states'].append(meta_copy)

                        metadata = event_data['metadata']
                        print(f"{self.event_type_name} {self.idshort} collected event: "
                            f"{metadata['event_type_name']} ({metadata['idshort']}) "
                            f"with state {metadata['state'].name}\n")
                        if self.state == EventState.FAILURE:
                            print(f"Failing events: {self.data['metadata']['failed_states']}")
                    else:
                        # event is optional, so just add it without changing state
                        self.data['metadata']['optional_states'].append(meta_copy)
                        metadata = event_data['metadata']
                        print(f"{self.event_type_name} {self.idshort} collected optional event: "
                            f"{metadata['event_type_name']} ({metadata['idshort']}) "
                            f"with state {metadata['state'].name}\n")


    def _post(self):
        """
        Post the event using the event posting mechanism.
        
        """
        with self._lock:
            self.data['metadata']['timestamps']['posted'] = sktime.now()

        print(f"{self.event_type_name} {self.idshort} posted.")
        print(f"State: {self.state.name}")
        print(f"Posted at: {sktime.to_custom_time_format(self.timestamps['posted'])}\n")

        from suitkaise.int.eventsys.core_depr.bus.event_bus import EventBus
        bus = EventBus.get_current_bus()
        bus.post(self)

# ========== Priority ==========================================

    def _set_default_event_priority(self) -> None:
        """
        Set this event's priority.

        Subclasses can override this method to set a different default priority.

        """
        if self.priority is None:
            self.priority = EventPriority.NORMAL


    def set_event_priority(self, priority: EventPriority) -> None:
        """
        Set the event priority.

        Args:
            priority: The event priority
        
        """
        if priority is None:
            self._set_default_event_priority()
        else:
            self.priority = priority

        print(f"{self.event_type_name} {self.idshort} event priority set to {self.priority.name}")

    
    def upgrade_event_priority(self, highest: bool = False) -> None:
        """
        Upgrade the event priority to the next level.

        This is useful if you want to increase the priority of an event
        after it has been created.

        Args:
            highest: If True, set the event priority to the highest level.
                Otherwise, set it to the next level.
                
        """
        if not self.priority:
            self._set_default_event_priority()

        if highest:
            self.priority = EventPriority.HIGHEST
        else:
            # IntEnum, so we can just add 1 to the value
            if self.priority != EventPriority.HIGHEST:
                self.priority = EventPriority(self.priority.value + 1)

        print(f"{self.event_type_name} {self.idshort} "
              f"event priority upgraded to {self.priority.name}")
        
    def downgrade_event_priority(self, lowest: bool = False) -> None:
        """
        Downgrade the event priority to the next level.

        This is useful if you want to decrease the priority of an event
        after it has been created.

        If you set the priority to the lowest level, it will
        likely be compressed or cleaned from event histories on next sweep.

        Args:
            lowest: If True, set the event priority to the lowest level.
                Otherwise, set it to the next level lower.
                
        """
        if not self.priority:
            self._set_default_event_priority()

        if lowest:
            self.priority = EventPriority.LOWEST
        else:
            # IntEnum, so we can just subtract 1 from the value
            if self.priority != EventPriority.LOWEST:
                self.priority = EventPriority(self.priority.value - 1)

        print(f"{self.event_type_name} {self.idshort} "
              f"event priority downgraded to {self.priority.name}")


    def get_event_priority(self) -> EventPriority:
        """
        Get the event priority.

        Returns:
            EventPriority: The event priority
        
        """
        if not self.priority:
            self._set_default_event_priority()

        return self.priority


    
    def _get_fixable_exc_types(self):
        pass

    def _fix(self, exc_type, exc_value, traceback):
        pass

# =========== Modifiers ==========================================
    @classmethod
    def invert(cls):
        """
        Invert the final state of the event, after _complete() is called.

        Usage:
        with MyEvent.invert()() as event:
        
            # successes and failures get added...

        __exit__() will call _succeeded() if the event is in failure state
        and _failed() if the event is in success state.
        
        """
        class InvertedEvent(cls):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                # store the original class name (Event instead of InvertedEvent)
                if not hasattr(self, 'original_class'):
                    self.original_class_name = cls.__name__
                    self.original_class = cls

            def _succeeded(self):
                super()._failed()

            def _failed(self):
                super()._succeeded()

            def _convert_to_data(self, other_vars=None):
                vars_to_add = ['original_class_name', 'original_class']
                if other_vars:
                    vars_to_add.extend(other_vars)
                super()._convert_to_data(vars_to_add)

        InvertedEvent.__name__ = f"Inverted{cls.__name__}"
        return InvertedEvent
    
    @classmethod
    def optional(cls):
        """
        Mark the event as optional.

        This event will still post normally, 
        but will NOT affect the state of the parent event.

        Usage:
        with MyEvent.optional()() as event:
        
            # successes and failures get added...

        the parent event's _complete() will ignore this event's state
        and not change its own state because of this event.
        
        """
        class OptionalEvent(cls):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.data['is_optional'] = True
                # get the original class name (Event instead of OptionalEvent)
                if not hasattr(self, 'original_class'):
                    self.original_class_name = cls.__name__
                    self.original_class = cls

            def _convert_to_data(self, other_vars=None):
                vars_to_add = ['original_class_name', 'original_class']
                if other_vars:
                    vars_to_add.extend(other_vars)
                super()._convert_to_data(vars_to_add)

        OptionalEvent.__name__ = f"Optional{cls.__name__}"
        return OptionalEvent
    
    @classmethod
    def uncollectable(cls):
        """
        Mark the event as uncollectable.

        This event will NOT be collected by the parent event.
        This is useful for events that are not part of the main event flow,
        but still need to be executed and posted.

        Usage:
        with EventOne.collect([EventTwo, EventTwo]) as event_one:
        
            with EventTwo as event_two:
            
                # do something
        
            with EventTwo.uncollectable() as event_two:
            
                # do something

            with EventTwo as event_two:
            
                # do something

            
        * EventOne will collect the first EventTwo and the last EventTwo,
          but not the second EventTwo.

        """
        class UncollectableEvent(cls):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                if not hasattr(self, 'original_class'):
                    self.original_class_name = cls.__name__
                    self.original_class = cls

                self.is_uncollectable = True
                
            def _convert_to_data(self, other_vars=None):
                vars_to_add = [
                    'original_class_name', 
                    'original_class',
                    'is_uncollectable'
                    ]
                if other_vars:
                    vars_to_add.extend(other_vars)
                super()._convert_to_data(vars_to_add)

        UncollectableEvent.__name__ = f"Uncollectable{cls.__name__}"
        return UncollectableEvent

    

    @classmethod
    def collect(cls, events: Optional[List[Type['Event']]] = None):
        """
        Collect event data and add it to this event.

        This includes the state of events. If collect() is used,
        this event's state will depend on the state of the collected events.

        Usage:
        with MyEvent.collect() as event:
            
            with EventOne() as event_one:
                # do something
                event_one.success()
                event_one.add_data('key', value)

            with EventTwo() as event_two:
                # do something
                event_two.failure()
                event_two.add_data('key', value)

        * MyEvent automatically adds each event's data to its own data
        * if EventOne and EventTwo are both successful, MyEvent will be successful
        * if either EventOne or EventTwo is not a success, MyEvent will be a failure

        Collection Behavior:
        The events list specifies not just which types to collect, but also the exact
        sequence. Each event type in the list represents a "slot" that will be filled
        by the first matching event instance encountered.
        
        For example, [Event1, Event2, Event1, Event2] would collect:
        - The first instance of Event1
        - The first instance of Event2
        - The second instance of Event1
        - The second instance of Event2
        
        Each event type is "consumed" from the list as it's collected, allowing
        for precise control over which instances are collected.
        
        Using with uncollectable():
        Events marked with uncollectable() are ignored by collectors:
        
        Example:
        with EventOne.collect([EventTwo, EventTwo]) as event_one:
            with EventTwo() as event_two:
                # This is collected (first slot)
                pass
            
            with EventTwo.uncollectable() as event_two:
                # This is skipped entirely
                pass
                
            with EventTwo() as event_two:
                # This is collected (second slot)
                pass

        Args:
            events: List of events to explicitly collect from
            NOTE: if events is not provided, this event will collect
            all events in its context manager block that aren't marked
            as uncollectable.
        """
        class CollectingEvent(cls):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                if not hasattr(self, 'original_class'):
                    self.original_class_name = cls.__name__
                    self.original_class = cls

                # initialize the events dict
                if 'events' not in self.data:
                    self.data['events'] = []
                    
                # store event types to collect
                self._event_types_to_collect = events
                self._original_event_types_to_collect = events

                self._collected_events = []

                self._collected_events_lock = threading.RLock()
                self._collected_events_lock_name = str(self._collected_events_lock)

                self._parent_collector = None

            def _convert_to_data(self, other_vars=None):
                vars_to_add = [
                    'original_class_name', 
                    'original_class',
                    '_original_event_types_to_collect',
                    '_collected_events',
                    '_collected_events_lock_name',
                    '_parent_collector'
                ]
                if other_vars:
                    vars_to_add.extend(other_vars)
                super()._convert_to_data(vars_to_add)

            def __enter__(self):
                # Store the parent collector from thread local (if present)
                self._parent_collector = get_parent_collector()

                # Push this collector onto the stack
                push_collector(self)

                # Set this collector as the current collector
                set_parent_collector(self)

                # Register this with the bus
                from suitkaise.int.eventsys.core_depr.bus.event_bus import EventBus
                bus = EventBus.get_current_bus()
                bus.register_collector(self)

                return super().__enter__()

            def __exit__(self, exc_type, exc_value, traceback):
                # Process collected events before exiting
                with self._collected_events_lock:
                    for event in self._collected_events:
                        self._process_collected_event(event)

                # Pop this collector from the stack
                pop_collector()

                # Restore parent as current
                if self._parent_collector:
                    set_parent_collector(self._parent_collector)
                
                # Unregister this collector from the bus
                from suitkaise.int.eventsys.core_depr.bus.event_bus import EventBus
                bus = EventBus.get_current_bus()
                bus.unregister_collector(self)

                # Call the parent __exit__
                return super().__exit__(exc_type, exc_value, traceback)
            
            def _process_collected_event(self, event):
                """
                Process a collected event,
                storing its data (which includes its state).
                """
                # Check if event is marked as uncollectable - skip if it is
                if hasattr(event, 'is_uncollectable') and event.is_uncollectable:
                    return
                    
                # Check if we should collect this event type
                if self._event_types_to_collect is not None:
                    if event.__class__ not in self._event_types_to_collect:
                        return

                    # handle cases like [Event1, Event2, Event1, Event2]
                    # where we consume each event type in sequence
                    with self._lock:
                        for i, collected_event in enumerate(self._event_types_to_collect):
                            if collected_event == event.__class__:
                                # remove the first matching event type from the list
                                self._event_types_to_collect.pop(i)
                                break
                        else: # after for loop
                            # No matching event type found in the list
                            return

                # store event data
                event_data = event.data.copy()

                with self._lock:
                    # add the event data to this event's data
                    self.data['events'].append(event_data)

            def collect_event(self, event):
                """Called when an event is posted."""
                with self._collected_events_lock:
                    # add the event to the collected events
                    self._collected_events.append(event)

        CollectingEvent.__name__ = f"Collecting{cls.__name__}"
        return CollectingEvent
    
    @classmethod
    def wait(cls, event_pairs: List[Tuple[Type['Event'], Type['Event']]],
             keys: Optional[List[Dict[str, Any]]] = None,
             if_keys: Optional[List[Dict[str, Any]]] = None,
             for_keys: Optional[List[Dict[str, Any]]] = None):
        """
        Wait for a specific event or events to occur.

        Blocking modifier that will check the event bus from the most 
        recent event backwards.

        If the more recent event is if_event, it will execute its code, and instead
        subscribe to the for_event.

        If the more recent event is for_event, it will execute its code as normal.

        If there is a key argued, it will check each event for the key, and ignore events
        that do not match all keys.

        For higher precision, you can alternatively use if_keys and/or for_keys 
        instead of keys.

        Args:
            event_pairs: List of tuples containing the event classes to wait for
                - first event is the if_event
                - second event is the for_event
            keys: Optional list of keys to check for in the events
            if_keys: Optional list of keys to check for in the if_event
            for_keys: Optional list of keys to check for in the for_event
            NOTE: if either if_keys or for_keys are provided, keys will be ignored

        """
        pass
        # wait needs to take into account modified names of classes and look
        # for those as well


# =========== Utilities ==========================================

    def get_event_type_name(self) -> str:
        """
        Get the event name.

        Returns:
            str: The event name
        
        """
        return self.__class__.__name__ # ex. EventOne
    
    def get_state(self) -> EventState:
        """
        Get the event state.

        Returns:
            EventState: The event state
        
        """
        try:
            if self.state:
                return self.state
            elif self.data:
                if hasattr(self.data, 'metadata'):
                    metadata = self.data['metadata']
                    if hasattr(metadata, 'state'):
                        return metadata['state']
                    else:
                        return EventState.NONE
                else:
                    return EventState.NONE
            else:
                return EventState.NONE
        except Exception as e:
            print(f"Error getting event state: {e}")
            return EventState.NONE
        

    

