# SKTime TODO

## Core Implementation
- [ ] Implement `sktime.now()` and `sktime.get_current_time()`
- [ ] Enhanced `sktime.sleep()` function
- [ ] Flexible `sktime.elapsed()` with order-independent arguments
- [ ] Base time utilities and helpers

## Yawn Class
- [ ] Yawn class with sleep-after-N-operations logic
- [ ] Automatic counter reset after sleep
- [ ] Optional logging when sleep occurs
- [ ] Configurable sleep duration and trigger count

## Stopwatch Class
- [ ] Start/pause/resume functionality
- [ ] Lap timing system
- [ ] Total time calculation
- [ ] State management (started, paused, stopped)
- [ ] `get_laptime()` method for accessing specific laps

## Timer Class
- [ ] Decorator support (`@sktime.timethis()`)
- [ ] Context manager support (`with Timer()`)
- [ ] Statistical calculations (mean, median, min, max, std)
- [ ] Historical data storage and access
- [ ] `get_time()` method for accessing specific measurements

## Performance Analysis
- [ ] `mostrecent` property for latest timing
- [ ] Statistical property implementations
- [ ] Performance tracking over time
- [ ] Memory-efficient storage of timing data

## Integration Features
- [ ] XProcess timing integration
- [ ] Report module time formatting
- [ ] SKPerf performance monitoring hooks
- [ ] Cross-module timing utilities

## Testing & Documentation
- [ ] Unit tests for all timing classes
- [ ] Performance benchmarks
- [ ] Accuracy tests for timing measurements
- [ ] API documentation
- [ ] Usage examples and tutorials