# How to use `circuits`

`circuits` provides circuit breakers that can handle failures and manage resources.

There are 2 types.

- `Circuit` — Auto-resets after sleeping.
- `BreakingCircuit` — Stays broken until manually reset.

## `Circuit`

When it trips, it sleeps, automatically resets, and continues without a manual reset.

```python
from suitkaise.circuits import Circuit

rate_limiter = Circuit(
    num_shorts_to_trip=10,       # trip after 10 shorts
    sleep_time_after_trip=1.0,   # sleep 1 second when tripped
    backoff_factor=1.5,          # increase sleep by 1.5x each trip
    max_sleep_time=30.0          # cap sleep at 30 seconds
)

for request in requests:
    if is_rate_limited():
        rate_limiter.short()  # sleeps and continues after threshold
    else:
        process(request)
```

### `short()`

Short the circuit.

Count a failure. If threshold reached, sleep and auto-reset. 

Arguments
- `custom_sleep`: Optional override for sleep duration if this short causes a trip (float)

Returns
- `True` if sleep occurred, `False` otherwise

```python
circ = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=0.5)

circ.short()  # times_shorted = 1
circ.short()  # times_shorted = 2
circ.short()  # times_shorted = 3
circ.short()  # times_shorted = 4
circ.short()  # times_shorted = 5 → sleeps 0.5s → auto-resets to 0

# returns True if sleep occurred
if circ.short():
    print("Circuit tripped and slept")
```

### `trip()`

Trip the circuit.

Immediately break the circuit, sleep, and reset the circuit to work again.

Arguments
- `custom_sleep`: Optional override for sleep duration (float)

```python
if something_pretty_bad_happened:
    circ.trip()  # immediately sleep and reset

circ.trip(custom_sleep=5.0)  # sleep 5 seconds instead of default
```

### Exponential Backoff

Each trip multiplies the sleep time by `backoff_factor`.

```python
circ = Circuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=60.0
)

# trip 1: sleeps 1.0s
# trip 2: sleeps 2.0s  (1.0 × 2.0)
# trip 3: sleeps 4.0s  (2.0 × 2.0)
# trip 4: sleeps 8.0s  (4.0 × 2.0)
# trip 5: sleeps 16.0s (8.0 × 2.0)
# trip 6: sleeps 32.0s (16.0 × 2.0)
# trip 7: sleeps 60.0s (32.0 × 2.0) capped at max_sleep_time
```

```python
circ.reset_backoff()  # reset sleep time to original
```

### Properties

- `times_shorted` — shorts since last trip
- `total_trips` — lifetime count of all trips
- `current_sleep_time` — current sleep duration (after backoff)

### Async

Both `short()` and `trip()` support `.asynced()`.

```python
did_sleep = await circ.short.asynced()()
```

```python
await circ.trip.asynced()(custom_sleep=5.0)
```

---

## `BreakingCircuit`

When it trips, it stays broken until you manually call `reset()`. 

```python
from suitkaise.circuits import BreakingCircuit

api_circuit = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0
)

def fetch_with_retry(url):
    while not api_circuit.broken:
        try:
            response = requests.get(url, timeout=5)
            return response.json()
        except requests.RequestException:
            api_circuit.short()  # trip after 3 failures
    
    return None  # circuit broken, give up
```

### `short()`

Short the circuit.

Count a failure. If threshold reached, break the circuit.

```python
breaker = BreakingCircuit(num_shorts_to_trip=3)

breaker.short()  # times_shorted = 1, broken = False
breaker.short()  # times_shorted = 2, broken = False
breaker.short()  # times_shorted = 3, broken = True, sleeps

breaker.short(custom_sleep=2.0)
```

### `trip()`

Trip the circuit.

Immediately break the circuit.

```python
if something_pretty_bad_happened:
    breaker.trip()  # immediately broken

breaker.trip(custom_sleep=5.0)  # sleep 5 seconds when breaking
```

### `reset()`

Manually reset the `BreakingCircuit`.

```python
while not breaker.broken:
    try:
        something_that_might_fail()
    except Error:
        breaker.short()

# circuit broken, reset manually
breaker.reset()
```

Backoff is applied on reset if `backoff_factor != 1.0`.

```python
# reset to original sleep time
breaker.reset_backoff()
```

### Properties

- `broken` — Whether circuit has tripped
- `times_shorted` — Shorts since last trip/reset
- `total_failures` — Lifetime count of all failures
- `current_sleep_time` — Current sleep duration (after backoff)

### Async

Both `short()` and `trip()` support `.asynced()`.

```python
await breaker.short.asynced()()
```

```python
await breaker.trip.asynced()()
```