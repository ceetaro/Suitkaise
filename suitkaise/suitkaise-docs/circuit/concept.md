# Circuit Concept

## Overview

Circuit provides easy upgrades to incremental, conditional while looping and timeout after failing attempts. It implements a circuit breaker pattern for controlled failure handling and resource management.

## Core Philosophy

The Circuit class provides a clean, intuitive way to handle failure thresholds and resource limits in loops, preventing runaway processes and providing graceful degradation.

## Key Features

### Circuit Breaker Pattern
- **Shorts tracking**: Count failures up to a threshold
- **Automatic breaking**: Circuit breaks when short limit reached
- **State management**: `flowing` vs `broken` states
- **Sleep on break**: Optional sleep when circuit breaks

### Flow Control
- **Broken state**: Circuit has exceeded limits (`circ.broken` = True)
- **Manual breaking**: Force circuit break with `circ.trip()`
- **Short counting**: Track number of shorts with `circ.times_shorted`

### Resource Management
Circuit is perfect for:
- **Memory monitoring**: Break when memory usage too high
- **Error thresholds**: Stop after too many failures
- **Resource limits**: Prevent resource exhaustion
- **Rate limiting**: Control operation frequency

## Usage Patterns

### Basic Failure Threshold
```python
from suitkaise import Circuit

circ = Circuit(shorts=4, break_sleep=0.5)  # Break after 4 shorts, sleep 0.5 seconds after breaking

while not circ.broken:
    try:
        risky_operation()
    except Exception:
        circ.short()  # Count this failure
        
    if circ.broken:
        handle_circuit_break()
```

### Resource Monitoring
```python
while program.running:
    circ = Circuit(100)
    
    while not circ.broken:
        memory_usage = get_memory_usage()
        
        if memory_usage > max_threshold:
            circ.trip(5)  # Trip (break) and sleep 5 seconds
        elif memory_usage > warning_threshold:
            circ.short(0.05)  # Short and maybe sleep 0.05s
```

### Conditional Processing
```python
circ = Circuit(shorts=3)

for item in large_dataset:
    if isinstance(item, ProblematicType):
        circ.short()  # This type causes issues
    
    if isinstance(item, CriticalError):
        circ.trip()  # Stop immediately
    
    if circ.broken:
        break
        
    process_item(item)
```

## State Management

### Circuit States
- **Broken**: `circ.broken` returns True, operations should stop
- **Short count**: `circ.times_shorted` tracks failure count

### Breaking vs Shorting
- **Short**: `circ.short()` - increment failure count, break if limit reached
- **Trip**: `circ.trip()` - immediately trip (break) circuit
- **Sleep on break**: Both methods accept sleep duration parameter

## Integration Benefits
- **Loop control**: Clean while loop management
- **Resource safety**: Prevent resource exhaustion
- **Error handling**: Graceful failure management
- **Performance**: Lightweight state tracking

## Examples

### Basic Circuit Usage

```python
from suitkaise import Circuit

objs_to_check = [dict1, dict2, dict3, dict4, dict5]  # a bunch of dicts
index = 0

# create a Circuit object
circ = Circuit(shorts=4, break_sleep=0.5)

# while we have a flowing circuit
while not circ.broken:
    current_obj = objs_to_check[index]

    for item in current_obj.items():
        # we should only add up to 3 LargeSizedObjs total across all dicts
        if isinstance(item, LargeSizedObj):
            # short the circuit. if this circuit shorts 4 times, it will break
            circ.short()
        if isinstance(item, ComplexObject):
            # immediately trip (break) the circuit
            circ.trip()

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

### Memory Management with Circuit

```python
# sleeping after a circuit break

while program.running:
    circ = Circuit(100, 0.1)

    while not circ.broken:
        current_mem_usage = mem_mgr.get_current_usage()

        if current_mem_usage > max_mem_threshold:
            # will sleep execution for 5 seconds if circ.trip() is called here
            circ.trip(5)

        if current_mem_usage > recc_mem_threshold:
            # will sleep execution for 0.05 seconds instead of default 0.1 seconds if this short causes a break
            circ.short(0.05)
            print(f"Shorted circuit {circ.times_shorted} times.")

        # if circ.broken
        if circ.broken:
            print("Pausing execution because memory usage exceeds max threshold.")
            break
        
        # do actual work
        do_memory_intensive_work()
```

### Error Threshold Management

```python
from suitkaise import Circuit

def process_risky_data(data_items):
    circ = Circuit(shorts=3)  # Allow 3 failures before breaking
    successful_items = []
    
    for item in data_items:
        if circ.broken:
            print("Circuit broken, stopping processing")
            break
            
        try:
            result = risky_processing(item)
            successful_items.append(result)
        except MinorError:
            circ.short()  # Count this as a failure
            print(f"Minor error, shorts: {circ.times_shorted}")
        except CriticalError:
            circ.trip()  # Immediately trip on critical error
            print("Critical error, tripping circuit")
            break
    
    return successful_items
```

### Conditional Loop Control

```python
from suitkaise import Circuit

def smart_retry_loop(operation, max_attempts=10):
    circ = Circuit(shorts=3)  # Allow 3 failures before giving up
    attempt = 0
    
    while not circ.broken and attempt < max_attempts:
        try:
            result = operation()
            return result  # Success!
        except RetryableError as e:
            circ.short(0.05)
            print(f"Attempt {attempt + 1} failed: {e}")
            attempt += 1
        except FatalError as e:
            circ.trip(2)  # Don't retry fatal errors
            print(f"Fatal error: {e}")
            break
    
    if circ.broken:
        print("Too many failures, circuit broken")
    elif attempt >= max_attempts:
        print("Max attempts reached")
    
    return None  # Failed
```