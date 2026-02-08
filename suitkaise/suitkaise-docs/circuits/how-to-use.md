# How to use `circuits`

`circuits` provides two circuit breaker classes for managing failures and rate limiting in your code.

- `Circuit` — auto-resets after sleeping. Use for rate limiting and temporary failures.
- `BreakingCircuit` — stays broken until you manually reset. Use for failure thresholds and coordinated shutdown.

## Importing

```python
from suitkaise import Circuit, BreakingCircuit
```

## `Circuit`

### Creating a Circuit

```python
circuit = Circuit(
    num_shorts_to_trip=5,           # shorts before the circuit trips
    sleep_time_after_trip=1.0,      # seconds to sleep on trip
    backoff_factor=1.0,             # multiply sleep time after each trip (1.0 = no backoff)
    max_sleep_time=30.0,            # maximum sleep time cap
    jitter=0.0                      # randomness added to sleep (0.0 to 1.0)
)
```

All parameters except `num_shorts_to_trip` and `sleep_time_after_trip` have defaults.

Minimal:

```python
circuit = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)
```

### `short(custom_sleep=None)`

Record a failure. After `num_shorts_to_trip` failures, the circuit trips: sleeps, then resets the counter automatically.

```python
try:
    result = call_service()
except ServiceError:
    circuit.short()  # count the failure
```

Returns `True` if the circuit tripped and slept, `False` otherwise.

Pass `custom_sleep` to override the sleep duration for this specific trip:

```python
except RateLimitError as e:
    circuit.short(custom_sleep=e.retry_after)  # use the server's suggested wait time
```

### `trip(custom_sleep=None)`

Immediately trip the circuit, bypassing the counter. Use for catastrophic failures where you don't want to wait for the threshold.

```python
try:
    result = call_service()
except CriticalError:
    circuit.trip()  # skip the counter, trip immediately
except MinorError:
    circuit.short()  # count normally
```

Always returns `True` (always sleeps).

### `reset_backoff()`

Reset the sleep duration back to the original `sleep_time_after_trip`. Use after a successful operation to prevent the backoff from snowballing.

```python
result = call_service()  # success!
circuit.reset_backoff()   # back to original sleep time
```

### Properties

```python
circuit.num_shorts_to_trip   # int — threshold before trip (read-only)
circuit.times_shorted        # int — failures since last trip
circuit.total_trips          # int — lifetime trip count
circuit.current_sleep_time   # float — current sleep duration (after backoff)
```

### Exponential Backoff

Set `backoff_factor` > 1.0 to increase sleep time after each trip:

```python
circuit = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0
)

# Trip 1: sleeps 1.0s
# Trip 2: sleeps 2.0s
# Trip 3: sleeps 4.0s
# Trip 4: sleeps 8.0s
# Trip 5: sleeps 16.0s
# Trip 6+: sleeps 30.0s (capped)
```

### Jitter

Set `jitter` to add randomness and prevent thundering herd:

```python
circuit = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=5.0,
    jitter=0.2  # ±20% randomness
)

# sleep durations will be between 4.0s and 6.0s
```

The `jitter` parameter is a decimal (0.2), not a percentage (20). Values are clamped to `[0.0, 1.0]`.

---

## `BreakingCircuit`

### Creating a BreakingCircuit

```python
breaker = BreakingCircuit(
    num_shorts_to_trip=3,           # shorts before the circuit breaks
    sleep_time_after_trip=1.0,      # seconds to sleep when breaking
    backoff_factor=1.0,             # multiply sleep time after each reset
    max_sleep_time=30.0,            # maximum sleep time cap
    jitter=0.0                      # randomness added to sleep (0.0 to 1.0)
)
```

Minimal:

```python
breaker = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)
```

### `short(custom_sleep=None)`

Record a failure. After `num_shorts_to_trip` failures, the circuit breaks: sleeps, then stays broken.

```python
while not breaker.broken:
    try:
        result = risky_operation()
        break  # success
    except OperationError:
        breaker.short()  # count the failure

if breaker.broken:
    handle_failure()
```

Returns `None`.

### `trip(custom_sleep=None)`

Immediately break the circuit, bypassing the counter.

```python
try:
    result = call_service()
except CriticalError:
    breaker.trip()  # immediately broken
```

Returns `None`.

### `reset()`

Reset the circuit to operational state. Clears the broken flag, resets the short counter, and applies exponential backoff to the sleep time.

```python
if breaker.broken:
    # decide what to do...
    handle_failure()
    breaker.reset()  # ready to use again
```

Note: `reset()` applies the backoff factor. This means the next time the circuit breaks, it will sleep longer.

### `reset_backoff()`

Reset the sleep duration back to the original `sleep_time_after_trip` without changing the broken state.

```python
breaker.reset()           # reset broken state (applies backoff)
breaker.reset_backoff()   # also reset sleep time to original
```

### Properties

```python
breaker.num_shorts_to_trip   # int — threshold before break (read-only)
breaker.broken               # bool — whether circuit is currently broken
breaker.times_shorted        # int — failures since last trip/reset
breaker.total_trips          # int — lifetime trip count
breaker.current_sleep_time   # float — current sleep duration (after backoff)
```

### Exponential Backoff

Unlike `Circuit` (which applies backoff on trip), `BreakingCircuit` applies backoff on `reset()`. This means the sleep time increases each time you reset and the circuit breaks again.

```python
breaker = BreakingCircuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0
)

# Break 1: sleeps 1.0s
# reset() → next sleep will be 2.0s
# Break 2: sleeps 2.0s
# reset() → next sleep will be 4.0s
# Break 3: sleeps 4.0s
# ...
```

---

## Thread Safety

Both `Circuit` and `BreakingCircuit` are thread-safe. All state access is protected by `threading.RLock`.

```python
import threading
from suitkaise import Circuit

circuit = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

def worker():
    for _ in range(100):
        try:
            process_item()
        except ItemError:
            circuit.short()  # safe from multiple threads

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

The sleep operation happens outside the lock, so other threads aren't blocked while one thread sleeps.

---

## Async Support

Both classes support async usage via `.asynced()`. The async versions use `asyncio.sleep()` instead of blocking `time.sleep()`.

```python
# sync
circuit.short()

# async
await circuit.short.asynced()()

# sync
circuit.trip()

# async
await circuit.trip.asynced()()
```

Methods that don't sleep (`reset()`, `reset_backoff()`, property access) don't need async versions.

```python
import asyncio
from suitkaise import Circuit

circuit = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=2.0,
    backoff_factor=2.0,
    jitter=0.2
)

async def fetch(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 429:
                await circuit.short.asynced()()
                return None
            return await response.json()
    except aiohttp.ClientError:
        await circuit.short.asynced()()
        return None
```

---

## `Share` Integration

Both circuit classes include `_shared_meta` for integration with `suitkaise.processing.Share`. This enables cross-process circuit breaking.

```python
from suitkaise.processing import Share, Pool, Skprocess
from suitkaise import BreakingCircuit

share = Share()
share.circuit = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

class Worker(Skprocess):
    def __init__(self, share):
        self.share = share

    def __run__(self):
        if self.share.circuit.broken:
            self.stop()
            return

        try:
            result = process_item()
        except FatalError:
            self.share.circuit.short()

pool = Pool(workers=4)
pool.map(Worker, [share] * 4)
```

When any process trips the circuit, all other processes see `share.circuit.broken == True` on their next check. This gives you cross-process coordinated failure handling with zero infrastructure.

---

## Choosing Between `Circuit` and `BreakingCircuit`

| Use Case | Class | Why |
|----------|-------|-----|
| Rate limiting API calls | `Circuit` | Auto-resets after cooldown, keeps processing |
| Retry with backoff | `Circuit` | Sleeps and continues automatically |
| Stop after too many failures | `BreakingCircuit` | Stays broken, you decide what to do |
| Coordinated worker shutdown | `BreakingCircuit` | One worker breaks it, all see it |
| Graceful degradation | Both | `Circuit` for primary, `BreakingCircuit` for fallback |

---

## Error Handling

Circuits don't raise exceptions themselves. They sleep (Circuit) or set a flag (BreakingCircuit). You handle the logic:

```python
# Circuit: check the return value of short()
tripped = circuit.short()
if tripped:
    print("Circuit tripped, just paused")

# BreakingCircuit: check the broken property
breaker.short()
if breaker.broken:
    print("Circuit broken, stopping")
```
