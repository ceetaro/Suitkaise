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
- **Flowing state**: Circuit is operational (`circ.flowing` = True)
- **Broken state**: Circuit has exceeded limits (`circ.broken` = True)
- **Manual breaking**: Force circuit break with `circ.break()`
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

circ = Circuit(shorts=4)  # Break after 4 shorts

while circ.flowing:
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
    
    while circ.flowing:
        memory_usage = get_memory_usage()
        
        if memory_usage > max_threshold:
            circ.break(5)  # Break and sleep 5 seconds
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
        circ.break()  # Stop immediately
    
    if circ.broken:
        break
        
    process_item(item)
```

## State Management

### Circuit States
- **Flowing**: `circ.flowing` returns True, operations continue
- **Broken**: `circ.broken` returns True, operations should stop
- **Short count**: `circ.times_shorted` tracks failure count

### Breaking vs Shorting
- **Short**: `circ.short()` - increment failure count, break if limit reached
- **Break**: `circ.break()` - immediately break circuit
- **Sleep on break**: Both methods accept sleep duration parameter

## Integration Benefits
- **Loop control**: Clean while loop management
- **Resource safety**: Prevent resource exhaustion
- **Error handling**: Graceful failure management
- **Performance**: Lightweight state tracking