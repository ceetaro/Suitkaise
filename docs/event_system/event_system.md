# Suitkaise Event System

## Section 1: Structure Overview

Suitkaise (SK)'s event system is precise at each operating level -- instead of 
just one event bus that controls the whole system, there are multiple tiers of 
what you would usually call an "event bus". This allows for a more precise control
over what events are sent and received, and allows for a more modular system.

This in turn saves data and increases performance, as events are only sent exactly
to where they are needed.

There are 7 separate components that make up 3 distinct levels of event handling.
For more information on how to use these components, refer to `how_to_use.md`.

For more detailed information on the components themselves, refer to `components.md`.

1. **Event and its subclasses**: The class Event is the base class for all events
we use. This class implements the context manager protocol, allowing events
to be used in a with statement, and automatically posting the event when the block
exits. 

2. **keyreg**: The keyreg module is comprised of two singleton classes,
EventKeyRegistry and OptionalKeyRegistry. These in tandem are called "keyreg", as
that is the name of the module where they are located. 

EventKeyRegistry tracks registered key-value pairs, where the key is a name
and the value is a data type. When we use the `add_data()` method in an event,
the method will check with the EventKeyRegistry to see if the key is registered, and if it is, it will check if the data type is correct.

OptionalKeyRegistry is a class that tracks only keys from the EventKeyRegistry
that are "optional". This means that the key and its data can be removed after an
event calls its callback function, when event histories need to be compressed.

Note: for beginners, a "singleton" is just a class that can only be instantiated once!

It also handles state tracking, data storage and conversion, and includes
a few basic modifiers that make the class a lot more adaptable to your needs.
These will be explained in detail in the next section, "How to use the event system".

3. **EventBus**: The EventBus class is different from the usual single event bus
that many programs use. This event bus handles all events, but only for a single
thread in a single process.     

The EventBus maintains an event history local to each thread and provides methods to publish and subscribe to events. It also provides methods to communicate with BusStations.

4. **BusStation**: The BusStation class is a level higher than the EventBus, handling
events across all threads in a single process. It communicates with both its EventBuses
in each thread, and with the relevant MainStation. 

It also keeps a history of all events, but at the process level. EventBuses can "go" to and from BusStations, giving the station their newest data, and receiving the data from the station that the EventBus needs to know about.

5. **IntStation**: The IntStation (Internal Station) is a level higher than the 
Bustations that we have active in each process. This station resides on the internal
side of the entire system, and is responsible for tracking all events from each 
BusStation. 

What makes it internal? The IntStation handles all events that originate from 
SK source code, under the root "suitkaise". 

The IntStation communicates with its "local" BusStations in each internal process,
and with the ExtStation through the Bridge.

6. **ExtStation**: The ExtStation (External Station) is also a level higher than the
BusStations that we have active in each process. However, this station resides on the
external side of the entire system.

What makes it external? The ExtStation handles all events that originate from
user imported code, which gets imported under the root "ext". When we have external
code imported into the application, some processes will be dedicated to handling
that code instead of the internal code.

The ExtStation communicates with its "local" BusStations in each external process,
and with the IntStation through the Bridge.

7. **Bridge**: The Bridge is the final component of the event system. It is a
singleton that manages the point of communication between the IntStation and the
ExtStation. It is responsible for sending and receiving events between the two
stations with instructions for use when they reach the other side.

The bridge has 2 main functions that affect how events can travel between internal
code and external code. 

- Event Filtering: The bridge can filter events with 4 options:
    - Open: IntStation and ExtStation can send and receive events to each other.
    - Closed: IntStation and ExtStation cannot send or receive events to each other,
      and act as 2 separate systems.
    - OnlyToExt: IntStation can send events to ExtStation, but ExtStation cannot
      send events to IntStation. 
    - OnlyToInt: ExtStation can send events to IntStation, but IntStation cannot
      send events to ExtStation.

When you want to launch your application, you should be putting the bridge in 
the "Closed" state. This will run your application exactly as it would if you
weren't running it through Suitkaise. 

- Locking/Unlocking: The bridge can be locked or unlocked manually by the user.

  Locking the bridge will override filtering changes made in code by either side,
  and will prevent the bridge from changing its filtering state. Unlocking the bridge
  will again allow the bridge to change its filtering state without user intervention.

  The main state you would lock into would be "closed", but you can also lock the bridge into any other state if you want to change how you test your application
  on the fly.

## Section 2: How to use the event system (basic overview)
For a more in depth manual on how to use the event system, refer to `how_to_use.md`.


    


