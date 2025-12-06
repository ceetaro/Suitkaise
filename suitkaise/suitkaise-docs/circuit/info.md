# Circuit Info

## Module Status
- **Implementation**: In development
- **Priority**: Medium (Support module)
- **Dependencies**: None (foundational module)

## Key Components

### Circuit Class
- Circuit breaker pattern implementation
- Short counting and threshold management
- State tracking (flowing vs broken)
- Optional sleep on circuit break

### State Management
- `flowing` property - circuit operational status
- `broken` property - circuit failure status
- `times_shorted` counter - failure tracking
- Automatic state transitions

### Control Methods
- `short()` - increment failure count, break if threshold reached
- `break()` - immediately break circuit
- Sleep parameter support for both methods

## Integration Points
- **Loop Control**: While loop management and flow control
- **Error Handling**: Graceful failure management
- **Resource Management**: Memory, CPU, and resource monitoring
- **XProcess**: Process failure threshold management

## Use Cases
- Error threshold management
- Resource usage monitoring
- Memory leak prevention
- Rate limiting and throttling
- Graceful degradation patterns
- Retry logic with failure limits

## Performance Features
- Lightweight state tracking
- Minimal overhead for flow control
- Efficient failure counting
- Optional sleep for rate limiting