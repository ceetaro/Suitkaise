# SKTime Info

## Module Status
- **Implementation**: In development
- **Priority**: Medium (Gateway module)
- **Dependencies**: None (foundational module)

## Key Components

### Basic Time Functions
- `sktime.now()` and `sktime.get_current_time()` - Current time access
- `sktime.sleep()` - Enhanced sleep functionality  
- `sktime.elapsed()` - Flexible time difference calculation

### Yawn Class
- Conditional sleep after N operations
- Automatic counter reset
- Optional logging support
- Rate limiting functionality

### Stopwatch Class
- Professional timing with start/pause/resume
- Lap timing capabilities
- Total time tracking
- State management

### Timer Class
- Performance measurement and analysis
- Decorator and context manager support
- Statistical analysis (mean, median, min, max, std)
- Historical data access

## Integration Points
- **XProcess**: Built-in timing for process performance
- **Report**: Time-based logging and metrics
- **SKPerf**: Performance monitoring integration

## Use Cases
- Performance measurement and profiling
- Rate limiting and throttling
- Precise timing operations
- Statistical analysis of execution times
- Process timing and monitoring

## Performance Features
- Order-independent elapsed time calculation
- Efficient statistical calculations
- Minimal overhead timing
- Flexible measurement contexts