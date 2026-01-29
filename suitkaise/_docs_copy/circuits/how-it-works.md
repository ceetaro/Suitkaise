# circuits: How it Works

The `circuits` module provides two circuit breaker variants with built-in backoff, jitter, and async support:

- `Circuit`: auto-resetting
- `BreakingCircuit`: breaks until manually reset

Both are implemented in `suitkaise/circuits/api.py`.

## Shared architecture

### Core state

Both classes maintain these internal fields:

- `_times_shorted`: count of shorts since last trip/reset
- `_current_sleep_time`: current sleep duration (after backoff)
- `_lock`: `threading.RLock` to guard state

Each class also maintains its own lifetime counters:

- `Circuit`: `_total_trips`
- `BreakingCircuit`: `_total_failures`, `_broken`

### Thread safety

All reads/writes to state are guarded by a re-entrant lock:

- properties acquire the lock for reads
- mutating methods acquire the lock for writes

This makes `Circuit` and `BreakingCircuit` safe to use across threads.

### Backoff

Backoff is implemented as a multiplier applied to `_current_sleep_time`:

- `Circuit`: backoff applied **after each trip**
- `BreakingCircuit`: backoff applied **on reset**

```python
_current_sleep_time = min(_current_sleep_time * backoff_factor, max_sleep_time)
```

### Jitter

Jitter randomizes sleep duration to avoid synchronized retries:

```python
delta = sleep_duration * abs(jitter)
sleep_duration = max(0.0, sleep_duration + random.uniform(-delta, delta))
```

If `sleep_duration <= 0` or `jitter == 0`, the original value is used.

### Async support

Both classes expose `.asynced()` on `short` and `trip` via `_AsyncableMethod`:

- Sync execution uses `suitkaise.timing.sleep`
- Async execution uses `asyncio.sleep`

The async methods duplicate state updates but run the sleep step asynchronously.

### Share integration

Both classes expose `_shared_meta` describing read/write access so `Share` can synchronize state across processes. Example for `Circuit`:

```python
_shared_meta = {
    "methods": {
        "short": {"writes": ["_times_shorted", "_total_trips", "_current_sleep_time"]},
        "trip": {"writes": ["_times_shorted", "_total_trips", "_current_sleep_time"]},
        "reset_backoff": {"writes": ["_current_sleep_time"]},
    },
    "properties": {
        "times_shorted": {"reads": ["_times_shorted"]},
        "total_trips": {"reads": ["_total_trips"]},
        "current_sleep_time": {"reads": ["_current_sleep_time"]},
    },
}
```

## `Circuit` internals

### `short(custom_sleep=None)`

1. Acquire lock
2. Increment `_times_shorted`
3. If `_times_shorted >= num_shorts_to_trip` then trip
4. If tripped:
   - increment `_total_trips`
   - reset `_times_shorted` to 0
   - apply backoff to `_current_sleep_time`
   - sleep (with jitter)

Returns `True` if a sleep occurred, else `False`.

### `trip(custom_sleep=None)`

Immediate trip without incrementing the short counter. Internally calls `_trip_circuit`:

- increments `_total_trips`
- resets `_times_shorted`
- applies backoff
- sleeps (with jitter)

Returns `True`.

### `reset_backoff()`

Resets `_current_sleep_time` to the original `sleep_time_after_trip`.

## `BreakingCircuit` internals

### `short(custom_sleep=None)`

1. Acquire lock
2. Increment `_times_shorted` and `_total_failures`
3. If `_times_shorted >= num_shorts_to_trip`, break
4. `_break_circuit` sets `_broken = True`, resets `_times_shorted`, sleeps

Return value is `None` (the call is for state mutation).

### `trip(custom_sleep=None)`

Immediate break without waiting for short count.

### `reset()`

Manual reset:

- `_broken = False`
- `_times_shorted = 0`
- applies backoff to `_current_sleep_time`

### `reset_backoff()`

Resets `_current_sleep_time` to the original `sleep_time_after_trip` without changing `_broken`.

## Key differences

- `Circuit` auto-resets after sleeping; `BreakingCircuit` stays broken
- `Circuit` applies backoff after each trip; `BreakingCircuit` applies backoff when you reset
- `Circuit.short()` returns a bool; `BreakingCircuit.short()` returns `None`
