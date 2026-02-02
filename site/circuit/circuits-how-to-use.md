/*

how to use the circuit module. this is the default page when entered from the home page "learn more" or nav bar sidebar "circuit" link.

*/

rows = 2
columns = 1

# 1.1

title = "How to use `circuit`"

# 1.2

text = "

`circuit` is here as a simple, easy to use module to improve your code readability and quality of life in certain situations.

Perfect for things like resource usage monitoring.

Clearer than just using `while True:` with `break` statements everywhere.

### Difference between `Circuit` and `sktime.Yawn`

`Circuit` needs to be manually `reset()` after it has tripped.

`Yawn` automatically resets after each sleep.

```python
from suitkaise import circuit

circ = circuit.Circuit(num_shorts_to_trip=4, sleep_time_after_trip=0.5)

while not circ.broken:
    try:
        something_that_might_fail()

    except Exception:
        circ.short()

```

```python
from suitkaise import circuit

objs_to_check = [dict1, dict2, dict3, dict4, dict5]  # a bunch of dicts
index = 0

# create a Circuit object
circ = circuit.Circuit(num_shorts_to_trip=4, sleep_time_after_trip=0.5)

# while we have a flowing circuit
while not circ.broken:
    current_obj = objs_to_check[index]

    for item in current_obj.items():
        # we should only add up to 3 LargeSizedObjs total across all dicts
        if isinstance(item, LargeSizedObj):
            # short the circuit. if this circuit shorts 4 times, it will trip
            circ.short()
        if isinstance(item, ComplexObject):
            # immediately trip the circuit
            circ.trip()

        # if the circuit has tripped
        if circ.broken:
            break

    # check if circuit has tripped
    if circ.broken:
        pass
    else:
        dicts_with_valid_items.append(current_obj)
    index += 1
```

```python
# sleeping after a circuit trip

while program.running:
    circ = circuit.Circuit(num_shorts_to_trip=100, sleep_time_after_trip=0.1)

    while not circ.broken:
        current_mem_usage = mem_mgr.get_current_usage()

        if current_mem_usage > max_mem_threshold:
            # will sleep execution for 5 seconds when trip() is called
            circ.trip(custom_sleep=5)

        if current_mem_usage > recc_mem_threshold:
            # will sleep execution for 0.05 seconds instead of default 0.1 if this short causes a trip
            circ.short(custom_sleep=0.05)
            print(f"Shorted circuit {circ.times_shorted} times. Total trips: {circ.total_trips}")

        # if circ.broken
        if circ.broken:
            print("Pausing execution because memory usage exceeds max threshold.")
            break
        
        # do actual work
        do_memory_intensive_work()
```
"