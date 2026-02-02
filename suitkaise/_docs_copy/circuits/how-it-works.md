# How `circuits` actually works

`circuits` is 2 circuit breaker classes, that help you manage failures in your code.

- `Circuit` - auto-resetting circuit that sleeps and continues
- `BreakingCircuit` - stays broken until manually reset

Both classes have:
- thread safety
- native async support
- exponential backoff (with jitter and max sleep time)
- super simple API


## `Circuit`

`Circuit` is an auto-resetting circuit that sleeps, and then automatically resets to continue.

When the short counter reaches the `num_shorts_to_trip` threshold, the circuit trips.

```
short() -> increment counter -> if shorts == num_shorts_to_trip? -> trip -> sleep and reset
```

`Circuit` uses a `threading.RLock` to ensure that internal state is thread-safe.

### Tracking state

`_num_shorts_to_trip: int`
Number of shorts required before the circuit trips. Set at initialization.

`_times_shorted: int`
Counter tracking shorts since the last trip. Resets to 0 after each trip.

`_total_trips: int`
Lifetime count of all trips. Never resets.

`_current_sleep_time: float`
Current sleep duration after backoff is applied. Starts at `sleep_time_after_trip` and grows with each trip.

`_lock: threading.RLock`
Reentrant lock for thread-safe state access.

## Properties

`num_shorts_to_trip`: Number of shorts required before the circuit trips.
- `int`
- read-only

`times_shorted`: Counter tracking shorts since the last trip. Resets to 0 after each trip.
- `int`
- read-only

`total_trips`: Lifetime count of all trips. Never resets.
- `int`
- read-only

`current_sleep_time`: Current sleep duration after backoff is applied. Starts at `sleep_time_after_trip` and grows with each trip.
- `float`
- read-only

### Methods

#### `short(custom_sleep: float | None = None) -> bool`

Increments `_times_shorted` by 1, calling `_trip_circuit()` if the `num_shorts_to_trip` threshold is reached.

If `custom_sleep` is provided, it will be used instead of `_current_sleep_time`.

1. Acquires `self._lock`
2. Increments `_times_shorted` by 1
3. Checks if `_times_shorted` >= `num_shorts_to_trip`
4. Releases `self._lock`
5. If `_times_shorted` >= `num_shorts_to_trip`:
   - Acquires `self._lock`
   - Increments `_total_trips` by 1
   - Resets `_times_shorted` to 0
   - Releases `self._lock`
   - Applies jitter to sleep duration
   - Sleeps for `_current_sleep_time` or `custom_sleep` if provided
   - Applies backoff factor to `_current_sleep_time`
6. Returns `True` if slept, `False` otherwise

### `trip(custom_sleep: float | None = None) -> None`

`trip()` immediately triggers the circuit, bypassing the short counter.

If `custom_sleep` is provided, it will be used instead of `_current_sleep_time`.

1. Acquires `self._lock`
2. Increments `_total_trips` by 1
3. Resets `_times_shorted` to 0
4. Releases `self._lock`
5. Applies jitter to sleep duration
6. Sleeps for `_current_sleep_time` or `custom_sleep` if provided
7. Applies backoff factor to `_current_sleep_time`
8. Returns `None`

### `reset_backoff() -> None`

Restores the original sleep time to `sleep_time_after_trip`.

1. Acquires `self._lock`
2. Sets `_current_sleep_time` to `sleep_time_after_trip`
3. Releases `self._lock`
4. Returns `None`

### Exponential Backoff

`Circuit` supports exponential backoff to progressively increase sleep time after repeated trips.
 
```python
circ = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,  # initial sleep time == 1.0s
    backoff_factor=2.0,         # double it each time it is tripped
    max_sleep_time=30.0         # sleep time is capped at 30s
)
```

With the above parameters:
- Trip 1: sleep 1.0s
- Trip 2: sleep 2.0s
- Trip 3: sleep 4.0s
- Trip 4: sleep 8.0s
- Trip 5: sleep 16.0s
- Trip 6: sleep 30.0s (capped)
- Trip 7: sleep 30.0s (capped)
- ...


Formula for calculating the next sleep time:
```python
_current_sleep_time = min(
    _current_sleep_time * backoff_factor,
    max_sleep_time
)
```

#### Jitter and max sleep time

Jitter adds randomness to sleep durations.

When multiple processes trip their circuits at the same time, they all wake up at the same time, which puts pressure on the system. Jitter spreads out the wake-up times to prevent this.

The `jitter` parameter is a decimal (0.2), not a percentage (20).

Values are clamped to `[0.0, 1.0]`.

For a `jitter` of 0.2 and a `sleep_duration` of 1.0, the range is `[0.8, 1.2]`.

### Thread Safety

All state access is protected by a reentrant lock (`threading.RLock`).

A reentrant lock is needed because  `_trip_circuit()` may be called from `short()` and `trip()` and both need lock access.

The sleep operation itself happens outside the lock to avoid blocking other threads during the sleep.

All public properties acquire the lock for reads.
```python
@property
def times_shorted(self) -> int:
    with self._lock:
        return self._times_shorted
```

This ensures that all reads are consistent and thread-safe.

### Async Support

`Circuit` supports async usage via the `_AsyncableMethod` pattern from `suitkaise.sk`.

`_AsyncableMethod` wraps a sync method and an async method into a single attribute that can be called either way.

```python
short = _AsyncableMethod(_sync_short, _async_short)
```

Usage:
```python
# sync usage
circ.short()

# async usage
await circ.short.asynced()()
```

The async versions use `asyncio.sleep()` instead of blocking `time.sleep()`:

```python
async def _async_trip_circuit(self, custom_sleep: float | None = None) -> bool:
    with self._lock:
        sleep_duration = custom_sleep if custom_sleep is not None else self._current_sleep_time
        self._total_trips += 1
        self._times_shorted = 0
        
        if self.backoff_factor != 1.0:
            self._current_sleep_time = min(
                self._current_sleep_time * self.backoff_factor,
                self.max_sleep_time
            )
    
    sleep_duration = self._apply_jitter(sleep_duration)
    if sleep_duration > 0:
        await asyncio.sleep(sleep_duration)
    
    return True
```

The lock usage is the same - only the sleep call differs.

Methods with async support:
- `short()` - via `short.asynced()()`
- `trip()` - via `trip.asynced()()`

Methods like `reset_backoff()` and properties do not need async versions because they don't sleep.

### Share Integration

`Circuit` includes `_shared_meta` for integration with `suitkaise.processing.Share`.

`_shared_meta` is a dictionary that declares which attributes each method/property reads from or writes to. The `Share` class uses this metadata to synchronize state across processes.

```python
_shared_meta = {
    'methods': {
        'short': {'writes': ['_times_shorted', '_total_trips', '_current_sleep_time']},
        'trip': {'writes': ['_times_shorted', '_total_trips', '_current_sleep_time']},
        'reset_backoff': {'writes': ['_current_sleep_time']},
    },
    'properties': {
        'times_shorted': {'reads': ['_times_shorted']},
        'total_trips': {'reads': ['_total_trips']},
        'current_sleep_time': {'reads': ['_current_sleep_time']},
    }
}
```

This allows a `Share` instance to wrap a circuit and automatically synchronize state across multiple processes.

### Sleep Implementation

`Circuit` uses `suitkaise.timing.sleep()` for blocking sleeps:

```python
from suitkaise.timing import api as timing

# in _trip_circuit():
timing.sleep(sleep_duration)
```

This uses the timing module's sleep implementation, which provides consistent behavior across different environments.

## `BreakingCircuit`

Breaking circuit that stops when the failure threshold is reached.

Unlike `Circuit`, it stays broken until you manually reset it. Use this for stopping after a threshold is reached and deciding what to do next.

### State Tracking

`BreakingCircuit` tracks internal state using private attributes protected by a reentrant lock (`threading.RLock`).

`_num_shorts_to_trip: int`

Number of shorts required before the circuit breaks. Set at initialization.

`_broken: bool`

Whether the circuit is currently broken. Set to `True` when tripped, must be manually reset to `False`.

`_times_shorted: int`

Counter tracking shorts since the last trip/reset. Resets to 0 when circuit breaks.

`_total_trips: int`

Lifetime count of all trips. Never resets.

`_current_sleep_time: float`

Current sleep duration after backoff is applied. Starts at `sleep_time_after_trip` and grows on each `reset()`.

`_lock: threading.RLock`

Reentrant lock for thread-safe state access.

### The `short()` Flow

`short()` is the primary method for counting failures.

```
1. Acquire lock
2. Increment _times_shorted
3. Increment _total_trips
4. Check if _times_shorted >= num_shorts_to_trip
5. Release lock
6. If threshold reached:
   a. Acquire lock
   b. Set _broken = True
   c. Reset _times_shorted to 0
   d. Release lock
   e. Apply jitter to sleep duration
   f. Sleep for the duration
```

Key differences from `Circuit.short()`:
- Does not return a value (`None` instead of `bool`)
- Sets `_broken = True` and stays broken
- Increments `_total_trips` on every short (not just trips)

### The `trip()` Method

`trip()` immediately breaks the circuit, bypassing the short counter.

Useful for critical failures that should immediately stop processing.

```python
breaker.trip()  # immediately break, don't wait for threshold
breaker.trip(custom_sleep=5.0)  # break with custom sleep duration
```

Internally, `trip()` calls the same `_break_circuit()` method that `short()` uses when threshold is reached.

### The `reset()` Method

`reset()` restores the circuit to operational state.

```python
breaker.reset()
```

This:
- Sets `_broken` back to `False`
- Resets `_times_shorted` to 0
- Applies the backoff factor to `_current_sleep_time`

Note: backoff is applied on `reset()`, not when the circuit breaks. This is because the circuit stays broken until you decide to continue, so the next sleep time only matters after you reset.

### Exponential Backoff

`BreakingCircuit` supports exponential backoff to progressively increase sleep time after repeated break/reset cycles.

```python
breaker = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,  # initial sleep: 1 second
    backoff_factor=2.0,         # double sleep time each reset
    max_sleep_time=30.0         # cap at 30 seconds
)
```

When `reset()` is called, the formula is:

```python
_current_sleep_time = min(
    _current_sleep_time * backoff_factor,
    max_sleep_time
)
```

Example progression with `backoff_factor=2.0`:
- Break 1: sleep 1.0s, reset → next sleep becomes 2.0s
- Break 2: sleep 2.0s, reset → next sleep becomes 4.0s
- Break 3: sleep 4.0s, reset → next sleep becomes 8.0s
- And so on...

Unlike `Circuit`, backoff is applied on `reset()`, not when the circuit breaks. This makes sense because you control when to reset, so the next sleep time matters for the next break cycle.

`reset_backoff()` restores the original sleep time without resetting the `broken` state:

```python
breaker.reset_backoff()  # _current_sleep_time = sleep_time_after_trip
```

### Jitter

Jitter adds randomness to sleep durations to prevent the "thundering herd" problem.

When multiple processes break their circuits at the same time, they would all wake up at the same time and potentially overload the system again. Jitter spreads out the wake-up times.

```python
breaker = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    jitter=0.2  # +/- 20% randomization
)
```

The `jitter` parameter is a decimal (0.2), not a percentage (20).

Values are clamped to `[0.0, 1.0]`.

The jitter calculation:

```python
def _apply_jitter(self, sleep_duration: float) -> float:
    if sleep_duration <= 0:
        return sleep_duration
    jitter_fraction = abs(self.jitter)
    if jitter_fraction <= 0:
        return sleep_duration
    delta = sleep_duration * jitter_fraction
    return max(0.0, sleep_duration + random.uniform(-delta, delta))
```

With `jitter=0.2` and `sleep_duration=1.0`:
- `delta = 1.0 * 0.2 = 0.2`
- Final sleep: random value in range `[0.8, 1.2]`

The result is always at least 0.0 (no negative sleeps).

### Thread Safety

All state access is protected by a reentrant lock (`threading.RLock`).

A reentrant lock allows the same thread to acquire the lock multiple times without deadlocking. This is needed because methods like `_break_circuit()` may be called from `short()`, and both need lock access.

```python
with self._lock:
    # read or modify state
    self._times_shorted += 1
    self._total_trips += 1
    if self._times_shorted >= self.num_shorts_to_trip:
        should_trip = True

# sleep happens OUTSIDE the lock
if should_trip:
    self._break_circuit(sleep_duration)
```

Important: sleep operations happen outside the lock to avoid blocking other threads during the sleep.

All public properties acquire the lock for reads:

```python
@property
def broken(self) -> bool:
    with self._lock:
        return self._broken
```

This ensures consistent reads even while another thread is modifying state.

### Async Support

`BreakingCircuit` supports async usage via the `_AsyncableMethod` pattern from `suitkaise.sk`.

`_AsyncableMethod` wraps a sync method and an async method into a single attribute that can be called either way:

```python
short = _AsyncableMethod(_sync_short, _async_short)
```

Usage:
```python
# sync usage
breaker.short()

# async usage
await breaker.short.asynced()()
```

The async versions use `asyncio.sleep()` instead of blocking `time.sleep()`:

```python
async def _async_break_circuit(self, sleep_duration: float) -> None:
    with self._lock:
        self._broken = True
        self._times_shorted = 0

    sleep_duration = self._apply_jitter(sleep_duration)
    if sleep_duration > 0:
        await asyncio.sleep(sleep_duration)
```

The lock usage is the same - only the sleep call differs.

Methods with async support:
- `short()` - via `short.asynced()()`
- `trip()` - via `trip.asynced()()`

Methods like `reset()`, `reset_backoff()`, and properties do not need async versions because they don't sleep.

### Share Integration

`BreakingCircuit` includes `_shared_meta` for integration with `suitkaise.processing.Share`.

`_shared_meta` is a dictionary that declares which attributes each method/property reads from or writes to. The `Share` class uses this metadata to synchronize state across processes.

```python
_shared_meta = {
    'methods': {
        'short': {'writes': ['_times_shorted', '_total_trips', '_broken']},
        'trip': {'writes': ['_total_trips', '_broken', '_times_shorted']},
        'reset': {'writes': ['_broken', '_times_shorted', '_current_sleep_time']},
        'reset_backoff': {'writes': ['_current_sleep_time']},
    },
    'properties': {
        'broken': {'reads': ['_broken']},
        'times_shorted': {'reads': ['_times_shorted']},
        'total_trips': {'reads': ['_total_trips']},
        'current_sleep_time': {'reads': ['_current_sleep_time']},
    }
}
```

This allows a `Share` instance to wrap a circuit and automatically synchronize state across multiple processes. When one process breaks the circuit, all processes see `broken=True`.

### Sleep Implementation

`BreakingCircuit` uses `suitkaise.timing.sleep()` for blocking sleeps:

```python
from suitkaise.timing import api as timing

# in _break_circuit():
timing.sleep(sleep_duration)
```

This uses the timing module's sleep implementation, which provides consistent behavior across different environments.

