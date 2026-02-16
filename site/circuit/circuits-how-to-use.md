/*

synced from suitkaise-docs/circuits/how-to-use.md

*/

rows = 2
columns = 1

# 1.1

title = "How to use `<suitkaise-api>circuits</suitkaise-api>`"

# 1.2

text = "
`<suitkaise-api>circuits</suitkaise-api>` provides two circuit breaker classes for managing failures and rate limiting in your code.

- `<suitkaise-api>Circuit</suitkaise-api>` — auto-resets after sleeping. Use for rate limiting and temporary failures.
- `<suitkaise-api>BreakingCircuit</suitkaise-api>` — stays broken until you manually reset. Use for failure thresholds and coordinated shutdown.

## Importing

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>, <suitkaise-api>BreakingCircuit</suitkaise-api>
```

## `<suitkaise-api>Circuit</suitkaise-api>`

### Creating a Circuit

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=5,           # shorts before the circuit trips
    sleep_time_after_trip=1.0,      # seconds to sleep on trip
    backoff_factor=1.0,             # multiply sleep time after each <suitkaise-api>trip</suitkaise-api> (1.0 = no backoff)
    max_sleep_time=30.0,            # maximum sleep time cap
    jitter=0.0                      # randomness added to sleep (0.0 to 1.0)
)
```

All parameters except `num_shorts_to_trip` and `sleep_time_after_trip` have defaults.

Minimal:

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)
```

### `<suitkaise-api>short</suitkaise-api>(custom_sleep=None)`

Record a failure. After `num_shorts_to_trip` failures, the circuit trips: sleeps, then resets the counter automatically.

```python
try:
    <suitkaise-api>result</suitkaise-api> = call_service()
except ServiceError:
    circuit.<suitkaise-api>short</suitkaise-api>()  # count the failure
```

Returns `True` if the circuit tripped and slept, `False` otherwise.

Pass `custom_sleep` to override the sleep duration for this specific trip:

```python
except RateLimitError as e:
    circuit.<suitkaise-api>short</suitkaise-api>(custom_sleep=e.retry_after)  # use the server's suggested wait time
```

### `<suitkaise-api>trip</suitkaise-api>(custom_sleep=None)`

Immediately trip the circuit, bypassing the counter. Use for catastrophic failures where you don't want to wait for the threshold.

```python
try:
    <suitkaise-api>result</suitkaise-api> = call_service()
except CriticalError:
    circuit.<suitkaise-api>trip</suitkaise-api>()  # skip the counter, trip immediately
except MinorError:
    circuit.<suitkaise-api>short</suitkaise-api>()  # count normally
```

Always returns `True` (always sleeps).

### `<suitkaise-api>reset_backoff</suitkaise-api>()`

Reset the sleep duration back to the original `sleep_time_after_trip`. Use after a successful operation to prevent the backoff from snowballing.

```python
<suitkaise-api>result</suitkaise-api> = call_service()  # success!
circuit.<suitkaise-api>reset_backoff</suitkaise-api>()   # back to original sleep time
```

### Properties

```python
circuit.<suitkaise-api>num_shorts_to_trip</suitkaise-api>   # int — threshold before <suitkaise-api>trip</suitkaise-api> (read-only)
circuit.<suitkaise-api>times_shorted</suitkaise-api>        # int — failures since last trip
circuit.<suitkaise-api>total_trips</suitkaise-api>          # int — lifetime trip count
circuit.<suitkaise-api>current_sleep_time</suitkaise-api>   # float — current sleep duration (after backoff)
```

### Exponential Backoff

Set `backoff_factor` > 1.0 to increase sleep time after each trip:

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(
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
circuit = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=5,
    sleep_time_after_trip=5.0,
    jitter=0.2  # ±20% randomness
)

# sleep durations will be between 4.0s and 6.0s
```

The `jitter` parameter is a decimal (0.2), not a percentage (20). Values are clamped to `[0.0, 1.0]`.

---

## `<suitkaise-api>BreakingCircuit</suitkaise-api>`

### Creating a BreakingCircuit

```python
breaker = <suitkaise-api>BreakingCircuit</suitkaise-api>(
    num_shorts_to_trip=3,           # shorts before the circuit breaks
    sleep_time_after_trip=1.0,      # seconds to sleep when breaking
    backoff_factor=1.0,             # multiply sleep time after each reset
    max_sleep_time=30.0,            # maximum sleep time cap
    jitter=0.0                      # randomness added to sleep (0.0 to 1.0)
)
```

Minimal:

```python
breaker = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=3, sleep_time_after_trip=1.0)
```

### `<suitkaise-api>short</suitkaise-api>(custom_sleep=None)`

Record a failure. After `num_shorts_to_trip` failures, the circuit breaks: sleeps, then stays broken.

```python
while not breaker.<suitkaise-api>broken</suitkaise-api>:
    try:
        <suitkaise-api>result</suitkaise-api> = risky_operation()
        break  # success
    except OperationError:
        breaker.<suitkaise-api>short</suitkaise-api>()  # count the failure

if breaker.<suitkaise-api>broken</suitkaise-api>:
    handle_failure()
```

Returns `None`.

### `<suitkaise-api>trip</suitkaise-api>(custom_sleep=None)`

Immediately break the circuit, bypassing the counter.

```python
try:
    <suitkaise-api>result</suitkaise-api> = call_service()
except CriticalError:
    breaker.<suitkaise-api>trip</suitkaise-api>()  # immediately broken
```

Returns `None`.

### `<suitkaise-api>reset</suitkaise-api>()`

Reset the circuit to operational state. Clears the broken flag, resets the short counter, and applies exponential backoff to the sleep time.

```python
if breaker.<suitkaise-api>broken</suitkaise-api>:
    # decide what to do...
    handle_failure()
    breaker.<suitkaise-api>reset</suitkaise-api>()  # ready to use again
```

Note: `<suitkaise-api>reset</suitkaise-api>()` applies the backoff factor. This means the next time the circuit breaks, it will sleep longer.

### `<suitkaise-api>reset_backoff</suitkaise-api>()`

Reset the sleep duration back to the original `sleep_time_after_trip` without changing the broken state.

```python
breaker.<suitkaise-api>reset</suitkaise-api>()           # reset broken state (applies backoff)
breaker.<suitkaise-api>reset_backoff</suitkaise-api>()   # also reset sleep time to original
```

### Properties

```python
breaker.<suitkaise-api>num_shorts_to_trip</suitkaise-api>   # int — threshold before break (read-only)
breaker.<suitkaise-api>broken</suitkaise-api>               # bool — whether circuit is currently broken
breaker.<suitkaise-api>times_shorted</suitkaise-api>        # int — failures since last trip/reset
breaker.<suitkaise-api>total_trips</suitkaise-api>          # int — lifetime trip count
breaker.<suitkaise-api>current_sleep_time</suitkaise-api>   # float — current sleep duration (after backoff)
```

### Exponential Backoff

Unlike `<suitkaise-api>Circuit</suitkaise-api>` (which applies backoff on trip), `<suitkaise-api>BreakingCircuit</suitkaise-api>` applies backoff on `<suitkaise-api>reset</suitkaise-api>()`. This means the sleep time increases each time you reset and the circuit breaks again.

```python
breaker = <suitkaise-api>BreakingCircuit</suitkaise-api>(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0
)

# Break 1: sleeps 1.0s
# <suitkaise-api>reset</suitkaise-api>() → next sleep will be 2.0s
# Break 2: sleeps 2.0s
# <suitkaise-api>reset</suitkaise-api>() → next sleep will be 4.0s
# Break 3: sleeps 4.0s
# ...
```

---

## Thread Safety

Both `<suitkaise-api>Circuit</suitkaise-api>` and `<suitkaise-api>BreakingCircuit</suitkaise-api>` are thread-safe. All state access is protected by `threading.RLock`.

```python
import threading
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

def worker():
    for _ in range(100):
        try:
            process_item()
        except ItemError:
            circuit.<suitkaise-api>short</suitkaise-api>()  # safe from multiple threads

threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.<suitkaise-api>start</suitkaise-api>()
for t in threads:
    t.join()
```

The sleep operation happens outside the lock, so other threads aren't blocked while one thread sleeps.

---

## Async Support

Both classes support async usage via `.<suitkaise-api>asynced</suitkaise-api>()`. The async versions use `asyncio.sleep()` instead of blocking `time.sleep()`.

```python
# sync
circuit.<suitkaise-api>short</suitkaise-api>()

# async
await circuit.<suitkaise-api>short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()

# sync
circuit.<suitkaise-api>trip</suitkaise-api>()

# async
await circuit.<suitkaise-api>trip</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
```

Methods that don't sleep (`<suitkaise-api>reset</suitkaise-api>()`, `<suitkaise-api>reset_backoff</suitkaise-api>()`, property access) don't need async versions.

```python
import asyncio
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

circuit = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=5,
    sleep_time_after_trip=2.0,
    backoff_factor=2.0,
    jitter=0.2
)

async def fetch(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 429:
                await circuit.<suitkaise-api>short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
                return None
            return await response.json()
    except aiohttp.ClientError:
        await circuit.<suitkaise-api>short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
        return None
```

---

## `<suitkaise-api>Share</suitkaise-api>` Integration

Both circuit classes include `_shared_meta` for integration with `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api>.<suitkaise-api>Share</suitkaise-api>`. This enables cross-process circuit breaking.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

share = <suitkaise-api>Share</suitkaise-api>()
share.circuit = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

class Worker(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, share):
        self.share = share

    def <suitkaise-api>__run__</suitkaise-api>(self):
        if self.share.circuit.<suitkaise-api>broken</suitkaise-api>:
            self.<suitkaise-api>stop</suitkaise-api>()
            return

        try:
            <suitkaise-api>result</suitkaise-api> = process_item()
        except FatalError:
            self.share.circuit.<suitkaise-api>short</suitkaise-api>()

pool = <suitkaise-api>Pool</suitkaise-api>(workers=4)
pool.<suitkaise-api>map</suitkaise-api>(Worker, [share] * 4)
```

When any process trips the circuit, all other processes see `share.circuit.<suitkaise-api>broken</suitkaise-api> == True` on their next check. This gives you cross-process coordinated failure handling with zero infrastructure.

---

## Choosing Between `<suitkaise-api>Circuit</suitkaise-api>` and `<suitkaise-api>BreakingCircuit</suitkaise-api>`

| Use Case | Class | Why |
|----------|-------|-----|
| Rate limiting API calls | `<suitkaise-api>Circuit</suitkaise-api>` | Auto-resets after cooldown, keeps processing |
| Retry with backoff | `<suitkaise-api>Circuit</suitkaise-api>` | Sleeps and continues automatically |
| Stop after too many failures | `<suitkaise-api>BreakingCircuit</suitkaise-api>` | Stays broken, you decide what to do |
| Coordinated worker shutdown | `<suitkaise-api>BreakingCircuit</suitkaise-api>` | One worker breaks it, all see it |
| Graceful degradation | Both | `<suitkaise-api>Circuit</suitkaise-api>` for primary, `<suitkaise-api>BreakingCircuit</suitkaise-api>` for fallback |

---

## Error Handling

Circuits don't raise exceptions themselves. They sleep (Circuit) or set a flag (BreakingCircuit). You handle the logic:

```python
# <suitkaise-api>Circuit</suitkaise-api>: check the return value of <suitkaise-api>short</suitkaise-api>()
tripped = circuit.<suitkaise-api>short</suitkaise-api>()
if tripped:
    print("<suitkaise-api>Circuit</suitkaise-api> tripped, just paused")

# <suitkaise-api>BreakingCircuit</suitkaise-api>: check the broken property
breaker.<suitkaise-api>short</suitkaise-api>()
if breaker.<suitkaise-api>broken</suitkaise-api>:
    print("<suitkaise-api>Circuit</suitkaise-api> broken, stopping")
```
"
