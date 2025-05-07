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

# tests/eventsys/core/bus/test_event_bus.py

# Main file being tested: suitkaise/eventsys/core/bus/event_bus.py

"""
This file is responsible for testing the interactions between events
and event buses. It does not include any tests with BusStations.

Tests in this file:
- basic test: a test to check the basic event context manager 
    and (enter) --> (exit and post to bus) cycle
- bus test: a test to check the event bus functionality
    includes subscribing to events, calling callbacks, and
    getting recent events from the bus's history
- collector test: a test to check the Event.collect()() modifier
    includes testing the cycle of collecting events,
    and checking that collect related event modifiers are working

"""

import threading

from suitkaise.eventsys.events.base_event import Event
from suitkaise.eventsys.core.bus.event_bus import EventBus
import suitkaise.time.sktime as sktime
import suitkaise.utils.formatting.format_data as fmt
from suitkaise.eventsys.data.enums.enums import EventState

# define test events
class TestEvent(Event):
    pass

class TestEvent2(Event):
    pass

class CollectTestEvent(Event):
    pass

# define a callback for testing
def test_callback(event):
    state = event.get_state()
    if state == EventState.SUCCESS:
        print(f"Callback received event {event.event_type_name} with state SUCCESS\n")
    elif state == EventState.FAILURE:
        print(f"Callback received event {event.event_type_name} with state FAILURE\n")
    else:
        print(f"Callback received event {event.event_type_name} with state NONE\n")

def run_basic_test():
    """Test basic functionality of the event system."""
    print("\n=== Running Basic Test ===\n")

    # create and use a simple event
    with TestEvent() as event:
        print(f"Created event: {event.event_type_name} ({event.idshort})\n")
        event.add_data("key1", "value1")
        if event.data.get("key1"):
            print(f"Data added successfully to event: {event.data}\n")
            event.success()
        else:
            print(f"Failed to add data to event {event.event_type_name} ({event.idshort})\n")
            event.failure()

    # create and use a simple event
    with TestEvent() as event:
        print(f"Created event: {event.event_type_name} ({event.idshort})\n")
        event.add_data("key2", "value1")
        if event.data.get("key1"):
            print(f"Data added successfully to event: {event.data}\n")
            event.success()
        else:
            print(f"Failed to add data to event {event.event_type_name} ({event.idshort})\n")
            event.failure()

def run_bus_test():
    """Test if buses are working correctly."""
    print("\n=== Running Bus Test ===\n")

    # get the current thread's bus
    bus = EventBus.get_current_bus()

    # subscribe to the event
    bus.subscribe(TestEvent, test_callback)

    # post a TestEvent
    import random
    with TestEvent() as event:
        num = random.randint(1, 2)
        event.add_data("test_num", num)
        if num == 1:
            event.success()
        else:
            event.failure()

    # check recent events
    recent_events = bus.get_recent_events()
    print(f"Bus has {len(recent_events)} recent events in history\n")

    # post a different event
    with TestEvent2() as event:
        num = random.randint(1, 2)
        print(f"Random number: {num}")
        if num == 1:
            event.add_data("test_num", num)
        else:
            event.add_data("test_num", "number")

        if isinstance(event.data["test_num"], int):
            event.success()
        else: 
            event.failure()

    # check filtered events
    test_events1 = bus.get_recent_events(event_type=TestEvent)
    print(f"Example event data: {fmt.format_data(test_events1[0].data)}")
    test_events2 = bus.get_recent_events(event_type=TestEvent2)
    print(f"Bus has {len(test_events1)} recent events of type TestEvent")
    print(f"Bus has {len(test_events2)} recent events of type TestEvent2\n")


def run_collector_test():
    """Test if collectors are working correctly."""
    print("\n=== Running Collector Test ===\n")

    collector_id = None

    with TestEvent.collect()() as event:
        print(f"Created collecting event: {event.event_type_name} ({event.idshort})\n")
        collector_id = event.id

        # add child events
        with TestEvent() as event1:
            print(f"Created event: {event1.event_type_name} ({event1.idshort})\n")
            event1.add_data("test_child", "child1")
            if isinstance(event1.data["test_child"], str):
                event1.success()
            else:
                event1.failure()

        with TestEvent.invert()() as event2:
            print(f"Created inverted event: {event2.event_type_name} ({event2.idshort})\n")
            event2.add_data("test_child", "child2")
            if isinstance(event2.data["test_child"], str):
                event2.failure()
            else:
                event2.success()

        with TestEvent2.uncollectable()() as event3:
            print(f"Created uncollectable event: {event3.event_type_name} ({event3.idshort})\n")
            event3.add_data("test_child", "child3")
            if event3.data["test_child"] == "child4":
                event3.success()
            else:
                event3.failure()

        with TestEvent2.optional()() as event4:
            print(f"Created optional event: {event4.event_type_name} ({event4.idshort})\n")
            event4.add_data("test_child", "child4")
            if event4.data["test_child"] == "child4":
                event4.success()
            else:
                event4.failure()

    # collector should collect events automatically
    bus = EventBus.get_current_bus()
    recent_events = bus.get_recent_events()

    print("\n--- COLLECTOR ANALYSIS ---")
    
    # Find our collector in the recent events
    collector_event = None
    for event in recent_events:
        if hasattr(event, 'event_type_name') and 'Collecting' in event.event_type_name:
            if collector_id and hasattr(event, 'id') and event.id == collector_id:
                collector_event = event
                print(f"Found collector: {event.event_type_name} ({event.idshort})")
                break
    
    # If we didn't find the exact collector, look for any collector
    if not collector_event:
        for event in recent_events:
            if hasattr(event, 'event_type_name') and 'Collecting' in event.event_type_name:
                collector_event = event
                print(f"Found alternative collector: {event.event_type_name} ({event.idshort})")
                break
    
    if collector_event:
        print(f"Collector final state: {collector_event.state.name}")
        
        # Examine what was collected
        if 'events' in collector_event.data:
            collected = collector_event.data['events']
            print(f"Number of collected events: {len(collected)}")
            
            # Check for duplicates
            event_ids = []
            duplicate_count = 0
            
            for i, evt in enumerate(collected):
                # Extract metadata - handle both direct metadata and nested metadata
                if 'metadata' in evt:
                    metadata = evt['metadata']
                else:
                    metadata = {}
                
                event_type = metadata.get('event_type_name', 'Unknown')
                event_id = metadata.get('idshort', f"unknown-{i}")
                state = metadata.get('state', 'Unknown')
                optional = evt.get('is_optional', False)
                
                # Check for duplicates
                if event_id in event_ids:
                    duplicate_count += 1
                    print(f"  DUPLICATE FOUND: {event_type} ({event_id})")
                event_ids.append(event_id)
                
                # Print event details
                print(f"\nCollected Event {i+1}:")
                print(f"  Type: {event_type}")
                print(f"  ID: {event_id}")
                print(f"  State: {state}")
                print(f"  Optional: {optional}")
                
                # Show test_child value if present
                if 'test_child' in evt:
                    print(f"  test_child: {evt['test_child']}")
            
            if duplicate_count > 0:
                print(f"\nFOUND {duplicate_count} DUPLICATE EVENTS!")
        else:
            print("No events were collected!")
        
        # Check metadata for state tracking
        if 'metadata' in collector_event.data:
            metadata = collector_event.data['metadata']
            
            if 'failed_states' in metadata:
                print(f"\nFailed states count: {len(metadata['failed_states'])}")
                for state in metadata['failed_states']:
                    print(f"  {state.get('event_type_name', 'Unknown')} ({state.get('idshort', 'Unknown')})")
            
            if 'succeeded_states' in metadata:
                print(f"\nSucceeded states count: {len(metadata['succeeded_states'])}")
                for state in metadata['succeeded_states']:
                    print(f"  {state.get('event_type_name', 'Unknown')} ({state.get('idshort', 'Unknown')})")
    else:
        print("Couldn't find any collector in the recent events!")
        
    print("\n--- END COLLECTOR ANALYSIS ---")



def main():
    """Run all tests."""
    print("STARTING EVENT SYSTEM TESTS")
    print("==========================")
    
    # Initialize time
    sktime.setup_time()
    
    # Run the tests
    run_basic_test()
    run_bus_test()
    run_collector_test()

    start_time = sktime.get_start_time()
    end_time = sktime.now()
    elapsed = sktime.elapsed(start_time, end_time)
    fmtd_elapsed = sktime.to_custom_time_diff_format(elapsed, 
                            sktime.CustomTimeDiffFormats.S10_2)
    print(f"\nElapsed time: {fmtd_elapsed} ({elapsed})")


if __name__ == "__main__":
    main()






