# circuits: How to Use

This guide covers all public API for `Circuit` and `BreakingCircuit`.

```python
from suitkaise import Circuit, BreakingCircuit
```

## `Circuit`

Auto-resetting circuit breaker with backoff and jitter.

### Constructor

```python
Circuit(
    num_shorts_to_trip: int,
    sleep_time_after_trip: float = 0.0,
    backoff_factor: float = 1.0,
    max_sleep_time: float = 10.0,
    jitter: float = 0.0,
)
```

- `num_shorts_to_trip`: number of shorts before sleep
- `sleep_time_after_trip`: base sleep duration
- `backoff_factor`: multiplier applied after each trip
- `max_sleep_time`: cap for backoff
- `jitter`: random +/- fraction of sleep time (0.2 = +/- 20%)

### Properties

- `times_shorted`: shorts since last trip
- `total_trips`: lifetime trip count
- `current_sleep_time`: sleep time after backoff

### `short(custom_sleep: float | None = None) -> bool`

```python
circ = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=0.5)
if circ.short():
    print("tripped and slept")
```

- Increments short count.
- Trips when count reaches threshold.
- Returns `True` if sleep occurred.

Async usage:

```python
await circ.short.asynced()()
```

### `trip(custom_sleep: float | None = None) -> bool`

Trips immediately without waiting for short count.

```python
circ.trip()
await circ.trip.asynced()()
```

### `reset_backoff() -> None`

```python
circ.reset_backoff()
```

Resets sleep time to the original `sleep_time_after_trip`.

## `BreakingCircuit`

Manual reset circuit that stays broken after trip.

### Constructor

```python
BreakingCircuit(
    num_shorts_to_trip: int,
    sleep_time_after_trip: float = 0.0,
    backoff_factor: float = 1.0,
    max_sleep_time: float = 10.0,
    jitter: float = 0.0,
)
```

### Properties

- `broken`: whether the circuit is tripped
- `times_shorted`: shorts since last trip/reset
- `total_failures`: lifetime failures
- `current_sleep_time`: sleep time after backoff

### `short(custom_sleep: float | None = None) -> None`

```python
breaker = BreakingCircuit(num_shorts_to_trip=3)
try:
    risky_call()
except Exception:
    breaker.short()
```

Trips when short count reaches threshold and sets `broken = True`.

Async usage:

```python
await breaker.short.asynced()()
```

### `trip(custom_sleep: float | None = None) -> None`

Immediate trip without waiting for short count.

```python
breaker.trip()
await breaker.trip.asynced()()
```

### `reset() -> None`

Resets the breaker:

```python
breaker.reset()
```

- `broken = False`
- short counter resets
- backoff applied to `current_sleep_time`

### `reset_backoff() -> None`

Resets sleep time to `sleep_time_after_trip` without changing `broken`.

## Common patterns

### Rate limiting

```python
rate_limiter = Circuit(num_shorts_to_trip=10, sleep_time_after_trip=1.0)
for req in requests:
    if is_rate_limited():
        rate_limiter.short()
    else:
        process(req)
```

### Stop after failures

```python
breaker = BreakingCircuit(num_shorts_to_trip=5)
while not breaker.broken:
    try:
        do_work()
    except Exception:
        breaker.short()
```
