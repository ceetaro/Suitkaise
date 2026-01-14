# How `circuits` actually works

`circuits` has no dependencies outside of the standard library (uses `suitkaise.timing` for sleep).

It contains two classes: `Circuit` and `BreakingCircuit`.

---

## `Circuit` class

An auto-resetting circuit for rate limiting and progressive backoff.

Unlike `BreakingCircuit` (which breaks and stops), `Circuit` sleeps and continues. The counter auto-resets after each sleep, and exponential backoff is applied.

### `Circuit.__init__()`

Arguments:
- `num_shorts_to_trip`: Number of shorts before circuit trips and sleeps (int)
- `sleep_time_after_trip`: Base sleep duration in seconds when circuit trips (float, default `0.0`)
- `backoff_factor`: Exponential backoff multiplier (float, default `1.0`)
- `max_sleep_time`: Maximum sleep duration cap (float, default `10.0`)

1. Stores configuration values
2. Sets `_times_shorted` to `0` (no failures yet)
3. Sets `_total_trips` to `0` (lifetime counter)
4. Sets `_current_sleep_time` to `sleep_time_after_trip` (starts at base)
5. Creates `_lock` as a `threading.RLock()` for thread safety

---

### Properties

#### `Circuit.times_shorted`

Integer counter tracking how many times `short()` has been called since last trip.

Auto-resets to `0` when the circuit trips.

#### `Circuit.total_trips`

Integer counter tracking total trips over the lifetime of the circuit.

Incremented by:
- each trip caused by `short()` reaching threshold
- each call to `trip()`

Never resets — persists across trips.

#### `Circuit.current_sleep_time`

Current sleep duration in seconds, after backoff has been applied.

Starts at `sleep_time_after_trip`, multiplied by `backoff_factor` after each trip, capped at `max_sleep_time`.

---

### Methods

#### `Circuit.short()`

Increments the failure count and trips if limit is reached.

Arguments:
- `custom_sleep`: Optional override for sleep duration if this short causes a trip (float)

Returns:
- `True` if sleep occurred, `False` otherwise

1. Acquires lock
2. Increments `_times_shorted` by 1
3. Checks if `_times_shorted >= num_shorts_to_trip`:
   - **If True:** calls `_trip_circuit()`, returns `True`
   - **If False:** releases lock, returns `False`

#### `Circuit.trip()`

Immediately trips the circuit, bypassing short counting.

Arguments:
- `custom_sleep`: Optional override for sleep duration (float)

Returns:
- `True` (always sleeps)

1. Calls `_trip_circuit()` immediately
2. Returns `True`

#### `Circuit._trip_circuit()`

Internal method that handles the actual tripping.

1. Acquires lock
2. Gets sleep duration (custom_sleep or current_sleep_time)
3. Increments `_total_trips` by 1
4. Resets `_times_shorted` to `0` (auto-reset)
5. If `backoff_factor != 1.0`:
   - multiplies `_current_sleep_time` by `backoff_factor`
   - caps at `max_sleep_time`
6. Releases lock
7. If `sleep_duration > 0`, calls `timing.sleep()`
8. Returns `True`

#### `Circuit.reset_backoff()`

Resets the backoff sleep time to the original value.

1. Acquires lock
2. Sets `_current_sleep_time` back to `sleep_time_after_trip`
3. Releases lock

---

### Async Methods

Both `short()` and `trip()` are `_AsyncableMethod` instances that support `.asynced()`.

#### `Circuit.short.asynced()`

Returns an async version that uses `asyncio.sleep()` instead of `time.sleep()`:

```python
await circ.short.asynced()()
```

Internally:
1. Same logic as sync version for incrementing and checking
2. Uses `await asyncio.sleep(sleep_duration)` for the actual sleep

#### `Circuit.trip.asynced()`

```python
await circ.trip.asynced()()
```

Same pattern as `short.asynced()`.

---

## `BreakingCircuit` class

A breaking circuit that stays broken until manually reset.

Unlike `Circuit` (which auto-resets), `BreakingCircuit` stays in a broken state and must be manually reset with `reset()`.

### `BreakingCircuit.__init__()`

Arguments (same as `Circuit`):
- `num_shorts_to_trip`: Maximum shorts before circuit trips (int)
- `sleep_time_after_trip`: Base sleep duration when circuit trips (float, default `0.0`)
- `backoff_factor`: Exponential backoff multiplier applied on reset (float, default `1.0`)
- `max_sleep_time`: Maximum sleep duration cap (float, default `10.0`)

1. Stores configuration values
2. Sets `_broken` to `False` (circuit starts operational)
3. Sets `_times_shorted` to `0`
4. Sets `_total_failures` to `0` (lifetime failure counter)
5. Sets `_current_sleep_time` to `sleep_time_after_trip`
6. Creates `_lock` as a `threading.RLock()`

---

### Properties

#### `BreakingCircuit.broken`

Boolean indicating whether the circuit has broken.

- `False` — circuit is operational, loop should continue
- `True` — circuit has broken, loop should exit

```python
while not breaker.broken:
    # ... loop logic ...
```

#### `BreakingCircuit.times_shorted`

Shorts since last trip or reset. Resets to `0` when circuit breaks or when `reset()` is called.

#### `BreakingCircuit.total_failures`

Lifetime count of all failures. Incremented by:
- each call to `short()`
- each call to `trip()`

Never resets — persists across `reset()` calls.

#### `BreakingCircuit.current_sleep_time`

Current sleep duration after backoff. Backoff is applied when `reset()` is called (not when tripping).

---

### Methods

#### `BreakingCircuit.short()`

Increments failure count and breaks the circuit if limit is reached.

Arguments:
- `custom_sleep`: Optional override for sleep duration if this short causes a break (float)

Returns:
- none

1. Acquires lock
2. Increments `_times_shorted` by 1
3. Increments `_total_failures` by 1
4. Checks if `_times_shorted >= num_shorts_to_trip`:
   - **If True:** calls `_break_circuit()`
5. Releases lock

#### `BreakingCircuit.trip()`

Immediately breaks the circuit.

Arguments:
- `custom_sleep`: Optional override for sleep duration (float)

Returns:
- none

1. Increments `_total_failures` by 1
2. Calls `_break_circuit()`

#### `BreakingCircuit.reset()`

Resets the circuit to operational state.

Returns:
- none

1. Acquires lock
2. Sets `_broken` to `False`
3. Resets `_times_shorted` to `0`
4. If `backoff_factor != 1.0`:
   - multiplies `_current_sleep_time` by `backoff_factor`
   - caps at `max_sleep_time`
5. Releases lock

Note: Backoff is applied on `reset()`, not on break. This way each recovery cycle waits longer.

#### `BreakingCircuit.reset_backoff()`

Resets the backoff sleep time to original value.

Does NOT reset the broken state — use `reset()` for that.

1. Acquires lock
2. Sets `_current_sleep_time` back to `sleep_time_after_trip`
3. Releases lock

#### `BreakingCircuit._break_circuit()`

Internal method to break the circuit.

1. Acquires lock
2. Sets `_broken` to `True`
3. Resets `_times_shorted` to `0`
4. Releases lock
5. If `sleep_duration > 0`, calls `timing.sleep()`

---

### Async Methods

Same pattern as `Circuit`:

```python
await breaker.short.asynced()()
await breaker.trip.asynced()()
```

Uses `asyncio.sleep()` instead of `time.sleep()`.

---

## State Diagrams

### Circuit (Auto-Reset)

```
┌─────────────────────────────────────────────────────────────┐
│                         RUNNING                             │
│                                                             │
│  short() → increment counter                                │
│                                                             │
│  if counter >= threshold:                                   │
│      → sleep (with backoff)                                 │
│      → auto-reset counter to 0                              │
│      → continue RUNNING                                     │
│                                                             │
│  trip() → immediately sleep, reset counter, continue        │
│                                                             │
│  reset_backoff() → restore original sleep time              │
└─────────────────────────────────────────────────────────────┘
```

### BreakingCircuit (Manual Reset)

```
┌──────────────────────┐                ┌──────────────────────┐
│       RUNNING        │                │        BROKEN        │
│                      │                │                      │
│  broken = False      │    break       │  broken = True       │
│                      │  ───────────►  │                      │
│  short() increments  │                │  loop should exit    │
│  trip() breaks       │                │                      │
│                      │    reset()     │                      │
│                      │  ◄───────────  │                      │
└──────────────────────┘                └──────────────────────┘
```

---

## `_shared_meta`

Both classes define `_shared_meta` for Share compatibility:

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

This allows the circuits to be used with the Share system for cross-process synchronization.

---

## Thread Safety

Both `Circuit` and `BreakingCircuit` are fully thread-safe.

All property access and state modifications are protected by an internal `threading.RLock()`.

Multiple threads can safely use a single circuit instance:

```python
import threading

breaker = BreakingCircuit(num_shorts_to_trip=5)

def worker():
    while not breaker.broken:
        try:
            do_work()
        except Error:
            breaker.short()

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

The `RLock` is reentrant, allowing the same thread to acquire it multiple times without deadlock.

---

## Memory

Each circuit instance stores:
- configuration values (4 ints/floats) — ~112 bytes
- state values (2-3 ints/floats + 1 bool) — ~84-112 bytes
- `_lock` (RLock) — ~56 bytes

Total: ~250-280 bytes per instance.
