# timing: How it Works

The `timing` module provides lightweight time utilities and a statistics-capable timer. Core implementation is in `suitkaise/timing/_int/time_ops.py`.

## Clocks and precision

- `time()` uses wall-clock `time.time()`
- `Sktimer` uses high-resolution monotonic `time.perf_counter()`

This avoids drift and ensures accurate duration measurement.

## `Sktimer` internals

### Thread sessions

Each thread gets its own `TimerSession`:

- Sessions store a stack of timing frames
- Frames support nesting and pause/resume

### Timing frames

Each frame stores:

- `start_time`
- `paused` flag
- `pause_started_at`
- `total_paused`

### Start/stop

`start()` pushes a new frame.  
`stop()` pops the top frame, computes elapsed time, and records it.

### Lap

`lap()` computes elapsed time and resets the frame without ending the session.

### Pause/resume

`pause()` marks the current frame as paused and records pause start time.  
`resume()` adds the paused duration to `total_paused`.

### Rolling windows

If `max_times` is set, older measurements are discarded as new ones are added.

### Statistics

Statistics are computed live from `times`:

- mean, median, min, max
- variance, stdev
- percentile with interpolation

`get_stats()` returns a frozen `TimerStats` snapshot.

## `TimeThis` context manager

`TimeThis` wraps an `Sktimer` and uses:

- `timer.start()` on enter
- `timer.discard()` on exit
- `timer.add_time()` if elapsed >= threshold

This design avoids double-counting when combined with other timing systems.

## `timethis` decorator

The decorator builds a wrapper from `_timethis_decorator`:

1. Computes elapsed time for each call
2. Applies threshold filtering
3. Records to `Sktimer`

If no timer is provided:

- a global timer is created and stored on the function as `func.timer`
- naming is based on module and class name
- access is locked by `RLock` to avoid races

## Async sleep support

`sleep` is wrapped by `_AsyncableFunction`:

- sync: `time.sleep`
- async: `asyncio.sleep`

This exposes `sleep.asynced()` without duplicating logic.
