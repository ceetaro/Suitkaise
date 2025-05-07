## How to use the event system if you are writing code in Suitkaise

### What imports do I need to create an event?

# TODO : Add imports that we use here

### Creating an event

We use context managers to create events, which allows us to automatically post the event when the block exits. This is done by using the `with` statement, and there
are many modifiers that can be used to change how the event block functions.

#### Basic event creation

Here is a basic example of how to create an event, using dummy event classes:

with MyEvent() as event:
    my_string = "Hello, world!"
    if my_string == "Hello, world!":
        event.success()
    else:
        event.failure()

First, we create an "event block" using the `with` statement. This is our
context manager in action!

Next, we get our required data. (my_string = "Hello, world!")

Then we check if we got the data we wanted. 
If we did, we call the `success()` method, which will set the event's state as successful. 

If we didn't, we call the `failure()` method, which will set the event's state as a
failure.

Finally the event block exits. In our context manager's "__exit__" method, we
do a couple of things: check the state, convert the event's variables (ex. self.state)
to data, and then post the event to the EventBus in the current thread.

##### more basic events

with MyEvent() as event:
    my_string = self.get_string()
    event.add_data(my_string)
    if my_string == "Hello, world!":
        event.success()
    else:
        event.failure()

In this example, we added one more method, `add_data()`, which allows us to add
data to the event for when it posts. Make sure that you have the key registered
in the EventKeyRegistry, or else the data will not be added!

#### Using basic modifiers

There are a few basic modifiers that the basic Event class comes with.
These are:

- collect: collect is a modifier that will "collect" the state of any events 
  that are called in the event block.

  Collect specific modifiers: optional, uncollectable

- invert: invert will reverse the state of the event when `__exit__` is called. 
  This means that if the event is a success, it will be a failure, and vice versa.

- wait: coming soon

##### advanced examples with modifiers

with MyEvent.invert()() as event:
    my_string = "Hello, world!"
    event.add_data(my_string)
    if my_string == "Hello, world!":
        event.success()
    else:
        event.failure()

ending state: failure

with MyEvent.collect()() as event:

    with Event1() as event1:
        my_string = "Hello, world!"
        event1.add_data(my_string)
        if my_string == "Hello, world!":
            event1.success()
        else:
            event1.failure()

    with Event2.uncollectable()() as event2:
        my_string = "Hello, world!"
        event2.add_data(my_string)
        if my_string == "Hello, world!":
            event2.success()
        else:
            event2.failure()

    with Event3.optional()() as event3:
        my_string = "Hello, world!"
        event3.add_data(my_string)
        if my_string == None:
            event3.success()
        else:
            event3.failure()

Here is what happens:

- we start with MyEvent.collect(), which will collect any 