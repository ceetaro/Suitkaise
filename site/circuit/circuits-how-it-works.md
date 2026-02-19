/*

synced from suitkaise-docs/circuits/how-it-works.md

*/

rows = 2
columns = 1

# 1.1

title = "How `circuits` actually works"

# 1.2

text = "
`<suitkaise-api>circuits</suitkaise-api>` is 2 circuit breaker classes, that help you manage failures in your code.

- `<suitkaise-api>Circuit</suitkaise-api>` - auto-resetting circuit that sleeps and continues
- `<suitkaise-api>BreakingCircuit</suitkaise-api>` - stays broken until manually reset

Both classes have:
- Thread safety
- Native async support
- Exponential backoff (with jitter and max sleep time)
- Super simple API


## `<suitkaise-api>Circuit</suitkaise-api>`

`<suitkaise-api>Circuit</suitkaise-api>` is an auto-resetting circuit that sleeps, and then automatically resets to continue.

When the short counter reaches the `num_shorts_to_trip` threshold, the circuit trips.

```
<suitkaise-api>short</suitkaise-api>() -> increment counter -> if shorts == num_shorts_to_trip? -> trip -> sleep and reset
```

`<suitkaise-api>Circuit</suitkaise-api>` uses a `threading.RLock` to ensure that internal state is thread-safe.

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

### Properties

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

#### `<suitkaise-api>short</suitkaise-api>(custom_sleep: float | None = None) -> bool`

Increments `_times_shorted` by 1, calling `_trip_circuit()` if the `num_shorts_to_trip` threshold is reached.

If `custom_sleep` is provided, it will be used instead of `_current_sleep_time`.

1. Acquires `self._lock`
2. Increments `_times_shorted` by 1
3. Checks if `_times_shorted` >= `num_shorts_to_trip`
4. Releases `self._lock`
5. If `_times_shorted` >= `num_shorts_to_trip`, calls `_trip_circuit()`:
   - Acquires `self._lock`
   - Captures `sleep_duration` (`custom_sleep` or `_current_sleep_time`)
   - Increments `_total_trips` by 1
   - Resets `_times_shorted` to 0
   - Applies backoff factor to `_current_sleep_time` (if `backoff_factor` != 1.0)
   - Releases `self._lock`
   - Applies jitter to `sleep_duration`
   - Sleeps for `sleep_duration`
6. Returns `True` if slept, `False` otherwise

#### `<suitkaise-api>trip</suitkaise-api>(custom_sleep: float | None = None) -> bool`

`<suitkaise-api>trip</suitkaise-api>()` immediately triggers the circuit, bypassing the short counter.

If `custom_sleep` is provided, it will be used instead of `_current_sleep_time`.

1. Calls `_trip_circuit()`:
   - Acquires `self._lock`
   - Captures `sleep_duration` (`custom_sleep` or `_current_sleep_time`)
   - Increments `_total_trips` by 1
   - Resets `_times_shorted` to 0
   - Applies backoff factor to `_current_sleep_time` (if `backoff_factor` != 1.0)
   - Releases `self._lock`
   - Applies jitter to `sleep_duration`
   - Sleeps for `sleep_duration`
2. Returns `True` (always sleeps)

#### `<suitkaise-api>reset_backoff</suitkaise-api>() -> None`

Restores the original sleep time to `sleep_time_after_trip`.

1. Acquires `self._lock`
2. Sets `_current_sleep_time` to `sleep_time_after_trip`
3. Releases `self._lock`
4. Returns `None`

### Exponential Backoff

`<suitkaise-api>Circuit</suitkaise-api>` supports exponential backoff to progressively increase sleep time after repeated trips.
 
```python
<suitkaise-api>circ</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,  # initial sleep time == 1.0s
    backoff_factor=2.0,         # double it each time it is tripped
    max_sleep_time=30.0         # sleep time is capped at 30s
)
```

**With the above parameters:**
- Trip 1: sleep 1.0s
- Trip 2: sleep 2.0s
- Trip 3: sleep 4.0s
- Trip 4: sleep 8.0s
- Trip 5: sleep 16.0s
- Trip 6: sleep 30.0s (capped)
- Trip 7: sleep 30.0s (capped)
- ...


**Formula for calculating the next sleep time:**
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

A reentrant lock is needed because  `_trip_circuit()` may be called from `<suitkaise-api>short</suitkaise-api>()` and `<suitkaise-api>trip</suitkaise-api>()` and both need lock access.

The sleep operation itself happens outside the lock to avoid blocking other threads during the sleep.

All public properties acquire the lock for reads.
```python
@property
def <suitkaise-api>times_shorted</suitkaise-api>(self) -> int:
    with self._lock:
        return self._times_shorted
```

This ensures that all reads are consistent and thread-safe.

### Async Support

`<suitkaise-api>Circuit</suitkaise-api>` supports async usage via the `_AsyncableMethod` pattern from `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>sk</suitkaise-api>`.

`_AsyncableMethod` wraps a sync method and an async method into a single attribute that can be called either way.

```python
short = _AsyncableMethod(_sync_short, _async_short)
```

**Usage:**
```python
# sync usage
<suitkaise-api>circ.short()</suitkaise-api>

# async usage
await <suitkaise-api>circ.short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
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

**Methods with async support:**
- `<suitkaise-api>short</suitkaise-api>()` - via `<suitkaise-api>short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()`
- `<suitkaise-api>trip</suitkaise-api>()` - via `<suitkaise-api>trip</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()`

Methods like `<suitkaise-api>reset_backoff</suitkaise-api>()` and properties do not need async versions because they don't sleep.

### Share Integration

`<suitkaise-api>Circuit</suitkaise-api>` includes `_shared_meta` for integration with `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api>.<suitkaise-api>Share</suitkaise-api>`.

`_shared_meta` is a dictionary that declares which attributes each method/property reads from or writes to. The `<suitkaise-api>Share</suitkaise-api>` class uses this metadata to synchronize state across processes.

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

This allows a `<suitkaise-api>Share</suitkaise-api>` instance to wrap a circuit and automatically synchronize state across multiple processes.

### Sleep Implementation

`<suitkaise-api>Circuit</suitkaise-api>` uses `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api>.sleep()` for blocking sleeps:

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import api as <suitkaise-api>timing</suitkaise-api>

# in _trip_circuit():
<suitkaise-api>timing</suitkaise-api>.sleep(sleep_duration)
```

This uses the timing module's sleep implementation, which provides consistent behavior across different environments.

## `<suitkaise-api>BreakingCircuit</suitkaise-api>`

Breaking circuit that stops when the failure threshold is reached.

Unlike `<suitkaise-api>Circuit</suitkaise-api>`, it stays broken until you manually reset it. Use this for stopping after a threshold is reached and deciding what to do next.

When the short counter reaches the `num_shorts_to_trip` threshold, the circuit breaks.

```
<suitkaise-api>short</suitkaise-api>() -> increment counter -> if shorts >= num_shorts_to_trip? -> break -> sleep (but stay broken)
```

`<suitkaise-api>BreakingCircuit</suitkaise-api>` uses a `threading.RLock` to ensure that internal state is thread-safe.

### Tracking state

`_num_shorts_to_trip: int`
Number of shorts required before the circuit breaks. Set at initialization.

`_times_shorted: int`
Counter tracking shorts since the last trip/reset. Resets to 0 after each trip or reset.

`_total_trips: int`
Lifetime count of all trips. Incremented on every `<suitkaise-api>short</suitkaise-api>()` call, never resets.

`_current_sleep_time: float`
Current sleep duration after backoff is applied. Starts at `sleep_time_after_trip` and grows with each `<suitkaise-api>reset</suitkaise-api>()`.

`_broken: bool`
Whether the circuit is currently broken. Set to `True` on trip, cleared by `<suitkaise-api>reset</suitkaise-api>()`.

`_lock: threading.RLock`
Reentrant lock for thread-safe state access.

### Properties

`num_shorts_to_trip`: Number of shorts required before the circuit breaks.
- `int`
- read-only

`broken`: Whether the circuit is currently broken.
- `bool`
- read-only

`times_shorted`: Counter tracking shorts since the last trip/reset. Resets to 0 after each trip or reset.
- `int`
- read-only

`total_trips`: Lifetime count of all trips. Never resets.
- `int`
- read-only

`current_sleep_time`: Current sleep duration after backoff is applied. Starts at `sleep_time_after_trip` and grows with each `<suitkaise-api>reset</suitkaise-api>()`.
- `float`
- read-only

### Methods

#### `<suitkaise-api>short</suitkaise-api>(custom_sleep: float | None = None) -> None`

Increments `_times_shorted` and `_total_trips` by 1, calling `_break_circuit()` if the `num_shorts_to_trip` threshold is reached.

If `custom_sleep` is provided, it will be used instead of `_current_sleep_time`.

1. Captures `sleep_duration` (`custom_sleep` or `_current_sleep_time`)
2. Acquires `self._lock`
3. Increments `_times_shorted` by 1
4. Increments `_total_trips` by 1
5. Checks if `_times_shorted` >= `num_shorts_to_trip`
6. Releases `self._lock`
7. If `_times_shorted` >= `num_shorts_to_trip`, calls `_break_circuit()`:
   - Acquires `self._lock`
   - Sets `_broken` to `True`
   - Resets `_times_shorted` to 0
   - Releases `self._lock`
   - Applies jitter to `sleep_duration`
   - Sleeps for `sleep_duration`
8. Returns `None`

Note: Unlike `<suitkaise-api>Circuit</suitkaise-api>`, `<suitkaise-api>BreakingCircuit</suitkaise-api>` increments `_total_trips` on every `<suitkaise-api>short</suitkaise-api>()` call, not just when the circuit trips.

#### `<suitkaise-api>trip</suitkaise-api>(custom_sleep: float | None = None) -> None`

`<suitkaise-api>trip</suitkaise-api>()` immediately breaks the circuit, bypassing the short counter.

If `custom_sleep` is provided, it will be used instead of `_current_sleep_time`.

1. Acquires `self._lock`
2. Increments `_total_trips` by 1
3. Releases `self._lock`
4. Captures `sleep_duration` (`custom_sleep` or `_current_sleep_time`)
5. Calls `_break_circuit(sleep_duration)`:
   - Acquires `self._lock`
   - Sets `_broken` to `True`
   - Resets `_times_shorted` to 0
   - Releases `self._lock`
   - Applies jitter to `sleep_duration`
   - Sleeps for `sleep_duration`
6. Returns `None`

#### `<suitkaise-api>reset</suitkaise-api>() -> None`

Resets the circuit to operational state and applies exponential backoff.

1. Acquires `self._lock`
2. Sets `_broken` to `False`
3. Resets `_times_shorted` to 0
4. If `backoff_factor` != 1.0:
   - Sets `_current_sleep_time` to `min(_current_sleep_time * backoff_factor, max_sleep_time)`
5. Releases `self._lock`
6. Returns `None`

Note: Unlike `<suitkaise-api>Circuit</suitkaise-api>` which applies backoff on trip, `<suitkaise-api>BreakingCircuit</suitkaise-api>` applies backoff on `<suitkaise-api>reset</suitkaise-api>()`. This means the next trip will use the increased sleep time.

#### `<suitkaise-api>reset_backoff</suitkaise-api>() -> None`

Restores the original sleep time to `sleep_time_after_trip`.

1. Acquires `self._lock`
2. Sets `_current_sleep_time` to `sleep_time_after_trip`
3. Releases `self._lock`
4. Returns `None`

Note: Does NOT reset the broken state - use `<suitkaise-api>reset</suitkaise-api>()` for that.

### Exponential Backoff

`<suitkaise-api>BreakingCircuit</suitkaise-api>` supports exponential backoff to progressively increase sleep time after repeated resets.

```python
<suitkaise-api>circ</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,  # initial sleep time == 1.0s
    backoff_factor=2.0,         # double it each time reset() is called
    max_sleep_time=30.0         # sleep time is capped at 30s
)
```

**With the above parameters:**
- Trip 1: sleep 1.0s
- Reset 1: backoff applied, next sleep will be 2.0s
- Trip 2: sleep 2.0s
- Reset 2: backoff applied, next sleep will be 4.0s
- Trip 3: sleep 4.0s
- ...

**Formula for calculating the next sleep time (applied on `<suitkaise-api>reset</suitkaise-api>()`):**
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

A reentrant lock is needed because `_break_circuit()` may be called from `<suitkaise-api>short</suitkaise-api>()` and `<suitkaise-api>trip</suitkaise-api>()` and both need lock access.

The sleep operation itself happens outside the lock to avoid blocking other threads during the sleep.

All public properties acquire the lock for reads.
```python
@property
def <suitkaise-api>broken</suitkaise-api>(self) -> bool:
    with self._lock:
        return self._broken
```

This ensures that all reads are consistent and thread-safe.

### Async Support

`<suitkaise-api>BreakingCircuit</suitkaise-api>` supports async usage via the `_AsyncableMethod` pattern from `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>sk</suitkaise-api>`.

`_AsyncableMethod` wraps a sync method and an async method into a single attribute that can be called either way.

```python
short = _AsyncableMethod(_sync_short, _async_short)
```

**Usage:**
```python
# sync usage
<suitkaise-api>circ.short()</suitkaise-api>

# async usage
await <suitkaise-api>circ.short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
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

**Methods with async support:**
- `<suitkaise-api>short</suitkaise-api>()` - via `<suitkaise-api>short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()`
- `<suitkaise-api>trip</suitkaise-api>()` - via `<suitkaise-api>trip</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()`

Methods like `<suitkaise-api>reset</suitkaise-api>()`, `<suitkaise-api>reset_backoff</suitkaise-api>()`, and properties do not need async versions because they don't sleep.

### Share Integration

`<suitkaise-api>BreakingCircuit</suitkaise-api>` includes `_shared_meta` for integration with `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api>.<suitkaise-api>Share</suitkaise-api>`.

`_shared_meta` is a dictionary that declares which attributes each method/property reads from or writes to. The `<suitkaise-api>Share</suitkaise-api>` class uses this metadata to synchronize state across processes.

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

This allows a `<suitkaise-api>Share</suitkaise-api>` instance to wrap a circuit and automatically synchronize state across multiple processes.

### Sleep Implementation

`<suitkaise-api>BreakingCircuit</suitkaise-api>` uses `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api>.sleep()` for blocking sleeps:

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>timing</suitkaise-api> import api as <suitkaise-api>timing</suitkaise-api>

# in _break_circuit():
<suitkaise-api>timing</suitkaise-api>.sleep(sleep_duration)
```

This uses the timing module's sleep implementation, which provides consistent behavior across different environments.
"
