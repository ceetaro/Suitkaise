# How to use `circuits`

`circuits` provides circuit breaker patterns for controlled failure handling.

Use circuit breakers to prevent runaway processes and manage failures gracefully.

- `Circuit` - auto-resetting circuit that sleeps and continues
- `BreakingCircuit` - stays broken until manually reset

Both classes have:
- thread safety
- native async support
- exponential backoff with jitter
- simple API

## Importing

```python
from suitkaise import Circuit, BreakingCircuit
```

```python
from suitkaise.circuits import Circuit, BreakingCircuit
```

## `Circuit`

Auto-resetting circuit for rate limiting and progressive backoff.

When the failure count reaches the threshold, the circuit trips, sleeps, and automatically resets.

```python
from suitkaise import Circuit

circ = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0,
    jitter=0.2
)

while doing_work:
    if something_went_wrong():
        circ.short()  # after 5 shorts, sleeps and auto-resets
    else:
        do_work()
```

### `__init__()`

`num_shorts_to_trip`: Number of shorts before the circuit trips.
- `int`
- required

`sleep_time_after_trip`: Base sleep duration (seconds) when circuit trips.
- `float = 0.0`
- keyword only

`backoff_factor`: Exponential backoff multiplier.
- `float = 1.0`
- keyword only
- `1.0` means no backoff

`max_sleep_time`: Maximum sleep duration cap (seconds).
- `float = 10.0`
- keyword only

`jitter`: Random +/- percentage of sleep time to prevent thundering herd.
- `float = 0.0`
- keyword only
- expects a decimal (0.2), NOT a percentage (20)
- values are clamped to `[0.0, 1.0]`

### Properties

`num_shorts_to_trip`: Number of shorts before the circuit trips.
- `int`
- read-only

`times_shorted`: Number of shorts since the last trip.
- `int`
- read-only

`total_trips`: Lifetime count of all trips.
- `int`
- read-only

`current_sleep_time`: Current sleep duration after backoff is applied.
- `float`
- read-only

### `short()`

Increment failure count and trip if the threshold is reached.

When tripped, sleeps for `current_sleep_time`, applies backoff, and auto-resets.

```python
circ.short()

# returns True if sleep occurred
if circ.short():
    print("Circuit tripped and slept")

# custom sleep duration for this call only
circ.short(custom_sleep=5.0)
```

Arguments
`custom_sleep`: Override sleep duration for this call.
- `float | None = None`
- positional or keyword

Returns
`bool`: `True` if the circuit tripped and slept, `False` otherwise.

### `trip()`

Immediately trip the circuit, bypassing the short counter.

```python
circ.trip()

# custom sleep duration
circ.trip(custom_sleep=10.0)
```

Arguments
`custom_sleep`: Override sleep duration for this call.
- `float | None = None`
- positional or keyword

Returns
`bool`: Always `True` (always sleeps).

### `reset_backoff()`

Reset the backoff sleep time to the original value.

```python
circ.reset_backoff()
```

Arguments
None.

Returns
`None`

### Async Usage

Both `short()` and `trip()` support async usage via `.asynced()`.

```python
# sync
circ.short()
circ.trip()

# async
await circ.short.asynced()()
await circ.trip.asynced()()
```

The async versions use `asyncio.sleep()` instead of blocking `time.sleep()`.

### Exponential Backoff

Exponential backoff progressively increases sleep time after repeated trips.

```python
circ = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0
)
```

With the above parameters:
- Trip 1: sleep 1.0s
- Trip 2: sleep 2.0s
- Trip 3: sleep 4.0s
- Trip 4: sleep 8.0s
- Trip 5: sleep 16.0s
- Trip 6: sleep 30.0s (capped)
- Trip 7+: sleep 30.0s (capped)

Use `reset_backoff()` to restore the original sleep time.

### Jitter

Jitter adds randomness to sleep durations.

When multiple processes trip their circuits at the same time, they all wake up at the same time, which puts pressure on the system. Jitter spreads out the wake-up times.

```python
circ = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    jitter=0.2  # +/- 20%
)
```

For a `jitter` of 0.2 and a `sleep_duration` of 1.0, the actual sleep time will be randomly chosen from `[0.8, 1.2]`.

## `BreakingCircuit`

Breaking circuit that stays broken until manually reset.

When the failure count reaches the threshold, the circuit breaks and stays broken. You decide what to do next.

```python
from suitkaise import BreakingCircuit

circ = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0,
    jitter=0.1
)

while not circ.broken:
    try:
        result = something_that_might_fail()
    except SomeError:
        circ.short()  # breaks after 3 failures

if circ.broken:
    print("Circuit broken, handling failure...")
    circ.reset()  # manual reset, applies backoff
```

### `__init__()`

`num_shorts_to_trip`: Number of shorts before the circuit breaks.
- `int`
- required

`sleep_time_after_trip`: Base sleep duration (seconds) when circuit breaks.
- `float = 0.0`
- keyword only

`backoff_factor`: Exponential backoff multiplier (applied on `reset()`).
- `float = 1.0`
- keyword only
- `1.0` means no backoff

`max_sleep_time`: Maximum sleep duration cap (seconds).
- `float = 10.0`
- keyword only

`jitter`: Random +/- percentage of sleep time to prevent thundering herd.
- `float = 0.0`
- keyword only
- expects a decimal (0.2), NOT a percentage (20)
- values are clamped to `[0.0, 1.0]`

### Properties

`num_shorts_to_trip`: Number of shorts before the circuit breaks.
- `int`
- read-only

`broken`: Whether the circuit is currently broken.
- `bool`
- read-only

`times_shorted`: Number of shorts since the last trip/reset.
- `int`
- read-only

`total_trips`: Lifetime count of all trips.
- `int`
- read-only
- Note: incremented on every `short()` call, not just when the circuit breaks

`current_sleep_time`: Current sleep duration after backoff is applied.
- `float`
- read-only

### `short()`

Increment failure count and break the circuit if the threshold is reached.

```python
circ.short()

# custom sleep duration for this call only
circ.short(custom_sleep=5.0)
```

Arguments
`custom_sleep`: Override sleep duration for this call.
- `float | None = None`
- positional or keyword

Returns
`None`

### `trip()`

Immediately break the circuit, bypassing the short counter.

```python
circ.trip()

# custom sleep duration
circ.trip(custom_sleep=10.0)
```

Arguments
`custom_sleep`: Override sleep duration for this call.
- `float | None = None`
- positional or keyword

Returns
`None`

### `reset()`

Reset the circuit to operational state.

Clears the `broken` flag, resets the short counter, and applies exponential backoff.

```python
circ.reset()
```

Arguments
None.

Returns
`None`

Note: Backoff is applied on `reset()`, not on trip. This means the next trip will use the increased sleep time.

### `reset_backoff()`

Reset the backoff sleep time to the original value.

Does NOT reset the broken state - use `reset()` for that.

```python
circ.reset_backoff()
```

Arguments
None.

Returns
`None`

### Async Usage

Both `short()` and `trip()` support async usage via `.asynced()`.

```python
# sync
circ.short()
circ.trip()

# async
await circ.short.asynced()()
await circ.trip.asynced()()
```

The async versions use `asyncio.sleep()` instead of blocking `time.sleep()`.

Note: `reset()` and `reset_backoff()` do not have async versions because they don't sleep.

### Exponential Backoff

Exponential backoff progressively increases sleep time after repeated resets.

Unlike `Circuit` (which applies backoff on trip), `BreakingCircuit` applies backoff on `reset()`.

```python
circ = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0
)
```

With the above parameters:
- Trip 1: sleep 1.0s, then reset() → next sleep will be 2.0s
- Trip 2: sleep 2.0s, then reset() → next sleep will be 4.0s
- Trip 3: sleep 4.0s, then reset() → next sleep will be 8.0s
- ...

Use `reset_backoff()` to restore the original sleep time.

### Jitter

Jitter adds randomness to sleep durations.

When multiple processes trip their circuits at the same time, they all wake up at the same time, which puts pressure on the system. Jitter spreads out the wake-up times.

```python
circ = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    jitter=0.2  # +/- 20%
)
```

For a `jitter` of 0.2 and a `sleep_duration` of 1.0, the actual sleep time will be randomly chosen from `[0.8, 1.2]`.