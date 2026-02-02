# How to use `circuits`

`circuits` is a module that provides circuit breaker pattern implementations for controlled failure handling.

It helps you:
- Rate limit operations with progressive backoff
- Stop processing after too many failures
- Prevent runaway loops from overwhelming systems
- Add graceful degradation to retry logic

## Importing

```python
from suitkaise import Circuit, BreakingCircuit
```

```python
from suitkaise.circuits import Circuit, BreakingCircuit
```

## `Circuit`

Auto-resetting circuit for rate limiting and progressive backoff.

When the failure threshold is reached, the circuit trips, sleeps, and automatically resets to continue.

```python
from suitkaise import Circuit

circ = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0,
    jitter=0.1
)

for request in requests:
    if is_rate_limited():
        circ.short()  # after 5 shorts, sleeps and auto-resets
    else:
        process(request)
```

### Constructor Arguments

`num_shorts_to_trip`: Number of shorts before circuit trips.
- `int`
- required

`sleep_time_after_trip`: Base sleep duration (seconds) when circuit trips.
- `float = 0.0`
- keyword only

`backoff_factor`: Exponential backoff multiplier applied after each trip.
- `float = 1.0` (no backoff)
- keyword only
- After each trip, `current_sleep_time` is multiplied by this factor
- Example with `backoff_factor=2.0`: 1s → 2s → 4s → 8s → ...

`max_sleep_time`: Maximum sleep duration cap.
- `float = 10.0`
- keyword only
- `current_sleep_time` will never exceed this value

`jitter`: Random +/- percent of sleep time to prevent thundering herd.
- `float = 0.0`
- keyword only
- expects a decimal (0.2), NOT a percentage (20)
- With `jitter=0.2` and `sleep_time=1.0`, actual sleep is random in `[0.8, 1.2]`

### Properties

`num_shorts_to_trip`: Number of shorts before trip.
- `int`
- read-only

`times_shorted`: Number of shorts since last trip.
- `int`
- read-only

`total_trips`: Lifetime count of all trips.
- `int`
- read-only

`current_sleep_time`: Current sleep duration after backoff is applied.
- `float`
- read-only

### `short()`

Count a failure and trip the circuit if threshold is reached.

```python
circ.short()

# returns True if sleep occurred
if circ.short():
    print("Circuit tripped and slept")

# custom sleep duration for this short only
circ.short(custom_sleep=2.0)
```

Arguments
`custom_sleep`: Override sleep duration for this short only.
- `float | None = None`

Returns
`bool`: `True` if the circuit tripped and slept, `False` otherwise.

#### Async usage

```python
await circ.short.asynced()()

# with custom sleep
await circ.short.asynced()(custom_sleep=2.0)
```

Uses `asyncio.sleep()` instead of blocking sleep.

### `trip()`

Immediately trip the circuit, bypassing the short counter.

```python
circ.trip()

# custom sleep duration
circ.trip(custom_sleep=5.0)
```

Arguments
`custom_sleep`: Override sleep duration for this trip.
- `float | None = None`

Returns
`bool`: Always `True` (always sleeps).

#### Async usage

```python
await circ.trip.asynced()()
```

### `reset_backoff()`

Reset the backoff sleep time to the original value.

```python
circ.reset_backoff()
```

Returns
`None`

This resets `current_sleep_time` back to `sleep_time_after_trip`, undoing any backoff that has accumulated.

### `Circuit` example: rate limiter with backoff

```python
from suitkaise import Circuit

rate_limiter = Circuit(
    num_shorts_to_trip=10,
    sleep_time_after_trip=1.0,
    backoff_factor=1.5,
    max_sleep_time=30.0,
    jitter=0.1
)

for request in request_queue:
    if api_says_rate_limited():
        rate_limiter.short()
    else:
        process(request)
```

### `Circuit` example: async rate limiting

```python
import asyncio
from suitkaise import Circuit

rate_limiter = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=0.5,
    backoff_factor=1.5
)

async def fetch_all(urls):
    results = []
    for url in urls:
        if is_rate_limited():
            await rate_limiter.short.asynced()()
        result = await fetch(url)
        results.append(result)
    return results
```

### `Circuit` example: checking trip status

```python
from suitkaise import Circuit

circ = Circuit(
    num_shorts_to_trip=5, 
    sleep_time_after_trip=1.0,
    backoff_factor=2.0
)

for item in items:
    tripped = circ.short()
    if tripped:
        print(f"Tripped! Total trips: {circ.total_trips}")
        print(f"Next sleep will be: {circ.current_sleep_time}s")
```

### `Circuit` example: shared circuit with `Share`

`Circuit` includes `_shared_meta` for integration with `suitkaise.processing.Share`:

```python
from suitkaise import Circuit
from suitkaise.processing import Share

circ = Circuit(num_shorts_to_trip=10, sleep_time_after_trip=1.0)
shared_circ = Share(circ)

# Now multiple processes can share the same circuit state
# Shorts from any process count towards the same threshold
```

## `BreakingCircuit`

Breaking circuit that stops when the failure threshold is reached.

Unlike `Circuit`, it stays broken until you manually reset it. Use this for stopping after a threshold is reached and deciding what to do next.

```python
from suitkaise import BreakingCircuit

breaker = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0,
    jitter=0.1
)

while not breaker.broken:
    try:
        result = risky_operation()
    except SomeError:
        breaker.short()  # after 3 failures, broken=True

if breaker.broken:
    print("Too many failures, giving up")
    breaker.reset()  # manual reset to try again
```

### Constructor Arguments

`num_shorts_to_trip`: Number of shorts before circuit breaks.
- `int`
- required

`sleep_time_after_trip`: Base sleep duration (seconds) when circuit breaks.
- `float = 0.0`
- keyword only

`backoff_factor`: Exponential backoff multiplier applied on reset.
- `float = 1.0` (no backoff)
- keyword only
- When `reset()` is called, `current_sleep_time` is multiplied by this factor
- Example with `backoff_factor=2.0`: 1s → 2s → 4s → 8s → ...

`max_sleep_time`: Maximum sleep duration cap.
- `float = 10.0`
- keyword only
- `current_sleep_time` will never exceed this value

`jitter`: Random +/- percent of sleep time to prevent thundering herd.
- `float = 0.0`
- keyword only
- expects a decimal (0.2), NOT a percentage (20)
- With `jitter=0.2` and `sleep_time=1.0`, actual sleep is random in `[0.8, 1.2]`

### Properties

`broken`: Whether the circuit is currently broken.
- `bool`
- read-only

`num_shorts_to_trip`: Number of shorts before break.
- `int`
- read-only

`times_shorted`: Number of shorts since last trip/reset.
- `int`
- read-only

`total_trips`: Lifetime count of all trips.
- `int`
- read-only

`current_sleep_time`: Current sleep duration after backoff is applied.
- `float`
- read-only

### `short()`

Count a failure and break the circuit if threshold is reached.

```python
breaker.short()

# custom sleep duration
breaker.short(custom_sleep=2.0)
```

Arguments
`custom_sleep`: Override sleep duration for this short only.
- `float | None = None`

Returns
`None`

#### Async usage

```python
await breaker.short.asynced()()

# with custom sleep
await breaker.short.asynced()(custom_sleep=2.0)
```

Uses `asyncio.sleep()` instead of blocking sleep.

### `trip()`

Immediately break the circuit, bypassing the short counter.

```python
breaker.trip()

# custom sleep duration
breaker.trip(custom_sleep=5.0)
```

Arguments
`custom_sleep`: Override sleep duration for this trip.
- `float | None = None`

Returns
`None`

#### Async usage

```python
await breaker.trip.asynced()()
```

### `reset()`

Reset the circuit to operational state.

```python
breaker.reset()
```

Returns
`None`

This:
- Sets `broken` back to `False`
- Resets `times_shorted` to 0
- Applies the backoff factor to `current_sleep_time`

### `reset_backoff()`

Reset the backoff sleep time to the original value.

```python
breaker.reset_backoff()
```

Returns
`None`

Does NOT reset the `broken` state - use `reset()` for that.

This resets `current_sleep_time` back to `sleep_time_after_trip`, undoing any backoff that has accumulated.

### `BreakingCircuit` example: retry with circuit breaker

```python
from suitkaise import BreakingCircuit
import requests

api_breaker = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0,
    jitter=0.1
)

def fetch_with_retry(url):
    while not api_breaker.broken:
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            api_breaker.short()
    
    return None  # circuit broken, give up

result = fetch_with_retry("https://api.example.com/data")
if result is None:
    api_breaker.reset()  # reset to try again later
```

### `BreakingCircuit` example: immediate trip for critical failures

```python
from suitkaise import BreakingCircuit

breaker = BreakingCircuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

while not breaker.broken:
    try:
        result = do_work()
    except RecoverableError:
        breaker.short()  # count towards threshold
    except CriticalError:
        breaker.trip()  # immediately break, don't count
        break
```

### `BreakingCircuit` example: retry loop with reset

```python
from suitkaise import BreakingCircuit

breaker = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=60.0
)

max_retries = 5
for attempt in range(max_retries):
    while not breaker.broken:
        try:
            result = risky_operation()
            break  # success, exit inner loop
        except SomeError:
            breaker.short()
    
    if breaker.broken:
        print(f"Attempt {attempt + 1} failed, resetting...")
        breaker.reset()  # applies backoff, try again
    else:
        break  # success, exit outer loop

if breaker.broken:
    print("All retries exhausted")
```

### `BreakingCircuit` example: shared circuit with `Share`

`BreakingCircuit` includes `_shared_meta` for integration with `suitkaise.processing.Share`:

```python
from suitkaise import BreakingCircuit
from suitkaise.processing import Share

breaker = BreakingCircuit(num_shorts_to_trip=10, sleep_time_after_trip=1.0)
shared_breaker = Share(breaker)

# Now multiple processes can share the same circuit state
# Shorts from any process count towards the same threshold
# When broken, all processes see broken=True
```

