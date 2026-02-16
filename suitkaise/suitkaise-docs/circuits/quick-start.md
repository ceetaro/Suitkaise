# Quick Start: `<suitkaise-api>circuits</suitkaise-api>`

```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Auto-resetting circuit (`<suitkaise-api>Circuit</suitkaise-api>`)

Sleeps after N failures, then resets and continues.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

for request in incoming_requests:
    try:
        process(request)
    except ServiceError:
        circuit.<suitkaise-api>short</suitkaise-api>()  # after 5 failures, sleeps 1s, then resets
```

## Breaking circuit (`<suitkaise-api>BreakingCircuit</suitkaise-api>`)

Stays broken after N failures until you manually reset.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

breaker = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

while not breaker.<suitkaise-api>broken</suitkaise-api>:
    try:
        <suitkaise-api>result</suitkaise-api> = risky_operation()
        break
    except OperationError:
        breaker.<suitkaise-api>short</suitkaise-api>()

if breaker.<suitkaise-api>broken</suitkaise-api>:
    handle_failure()
    breaker.<suitkaise-api>reset</suitkaise-api>()  # manually reset when ready
```

## Exponential backoff (with jitter and max sleep time)

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,    # double sleep time after each trip
    max_sleep_time=30.0    # cap at 30 seconds
)
# Trip 1: 1s, Trip 2: 2s, Trip 3: 4s, Trip 4: 8s, ...
```

## Jitter (randomness to prevent thundering herd)

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=5,
    sleep_time_after_trip=5.0,
    jitter=0.2  # ±20% randomness to prevent thundering herd
)
```

## Immediate trip (bypass the counter)

```python
try:
    <suitkaise-api>result</suitkaise-api> = call_service()
except CriticalError:
    circuit.<suitkaise-api>trip</suitkaise-api>()  # skip the counter, trip immediately
except MinorError:
    circuit.<suitkaise-api>short</suitkaise-api>()  # count normally
```

## Async support (native async support)

```python
# sync
circuit.<suitkaise-api>short</suitkaise-api>()

# async
await circuit.<suitkaise-api>short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
```

## Check state (get the current state of the circuit)

```python
circuit.<suitkaise-api>times_shorted</suitkaise-api>       # failures since last trip
circuit.<suitkaise-api>total_trips</suitkaise-api>         # lifetime trip count
circuit.<suitkaise-api>current_sleep_time</suitkaise-api>  # current backoff delay

breaker.<suitkaise-api>broken</suitkaise-api>              # is it broken?
```

## Want to learn more?

- **Why page** — why `<suitkaise-api>circuits</suitkaise-api>` exists, coordinated shutdown, and cross-process circuit breaking
- **How to use** — full API reference for `<suitkaise-api>Circuit</suitkaise-api>` and `<suitkaise-api>BreakingCircuit</suitkaise-api>`
- **Examples** — progressively complex examples into a full script
- **How it works** — internal architecture (locks, backoff, `<suitkaise-api>Share</suitkaise-api>` integration) (level: beginner-intermediate)
