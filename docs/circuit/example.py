# Circuit Examples

## Basic Circuit Usage

```python
from suitkaise import Circuit

objs_to_check = [dict1, dict2, dict3, dict4, dict5]  # a bunch of dicts
index = 0

# create a Circuit object
circ = Circuit(shorts=4)

# while we have a flowing circuit
while circ.flowing:
    current_obj = objs_to_check[index]

    for item in current_obj.items():
        # we should only add up to 3 LargeSizedObjs total across all dicts
        if isinstance(item, LargeSizedObj):
            # short the circuit. if this circuit shorts 4 times, it will break
            circ.short()
        if isinstance(item, ComplexObject):
            # immediately break the circuit
            circ.break()

        # if the circuit has broken (opposite of flowing, flowing gets set to False)
        if circ.broken:
            break

    # check if circuit has broken.
    if circ.broken:
        pass
    else:
        dicts_with_valid_items.append(current_obj)
    index += 1
```

## Memory Management with Circuit

```python
# sleeping after a circuit break

while program.running:
    circ = Circuit(100)

    while circ.flowing:
        current_mem_usage = mem_mgr.get_current_usage()

        if current_mem_usage > max_mem_threshold:
            # will sleep execution for 5 seconds if circ.break() is called here
            circ.break(5)

        if current_mem_usage > recc_mem_threshold:
            # will sleep execution for 0.05 seconds if this short causes a break
            circ.short(0.05)
            print(f"Shorted circuit {circ.times_shorted} times.")

        # if circ.broken (or "if not circ.flowing")
        if circ.broken:
            print("Pausing execution because memory usage exceeds max threshold.")
            break
        
        # do actual work
        do_memory_intensive_work()
```

## Error Threshold Management

```python
from suitkaise import Circuit

def process_risky_data(data_items):
    circ = Circuit(shorts=3)  # Allow 3 failures before breaking
    successful_items = []
    
    for item in data_items:
        if not circ.flowing:
            print("Circuit broken, stopping processing")
            break
            
        try:
            result = risky_processing(item)
            successful_items.append(result)
        except MinorError:
            circ.short()  # Count this as a failure
            print(f"Minor error, shorts: {circ.times_shorted}")
        except CriticalError:
            circ.break()  # Immediately break on critical error
            print("Critical error, breaking circuit")
            break
    
    return successful_items
```

## Resource Monitoring Pattern

```python
import psutil
from suitkaise import Circuit

def resource_aware_processing(tasks):
    circ = Circuit(shorts=5)
    completed_tasks = []
    
    for task in tasks:
        if not circ.flowing:
            print("Resource limits exceeded, stopping")
            break
        
        # Check system resources
        cpu_percent = psutil.cpu_percent()
        memory_percent = psutil.virtual_memory().percent
        
        if cpu_percent > 90:
            circ.break(2)  # Break and sleep 2 seconds
            print("CPU usage too high")
            break
        elif cpu_percent > 75:
            circ.short(0.1)  # Short and maybe brief pause
        
        if memory_percent > 85:
            circ.break(3)  # Break and sleep 3 seconds
            print("Memory usage too high")
            break
        elif memory_percent > 70:
            circ.short()  # Just count as a short
        
        # Process the task if circuit is still flowing
        if circ.flowing:
            result = process_task(task)
            completed_tasks.append(result)
    
    return completed_tasks
```

## Conditional Loop Control

```python
from suitkaise import Circuit

def smart_retry_loop(operation, max_attempts=10):
    circ = Circuit(shorts=3)  # Allow 3 failures before giving up
    attempt = 0
    
    while circ.flowing and attempt < max_attempts:
        try:
            result = operation()
            return result  # Success!
        except RetryableError as e:
            circ.short()
            print(f"Attempt {attempt + 1} failed: {e}")
            attempt += 1
        except FatalError as e:
            circ.break()  # Don't retry fatal errors
            print(f"Fatal error: {e}")
            break
    
    if circ.broken:
        print("Too many failures, circuit broken")
    elif attempt >= max_attempts:
        print("Max attempts reached")
    
    return None  # Failed
```