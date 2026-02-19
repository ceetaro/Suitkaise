# `circuits` quick start guide

```bash
pip install suitkaise
```

## Auto-resetting circuit (`Circuit`)

Sleeps after N failures, then resets and continues.

```python
from suitkaise import Circuit

circuit = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

for request in incoming_requests:
    try:
        process(request)
    except ServiceError:
        circuit.short()  # after 5 failures, sleeps 1s, then resets
```

## Breaking circuit (`BreakingCircuit`)

Stays broken after N failures until you manually reset.

```python
from suitkaise import BreakingCircuit

breaker = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

while not breaker.broken:
    try:
        result = risky_operation()
        break
    except OperationError:
        breaker.short()

if breaker.broken:
    handle_failure()
    breaker.reset()  # manually reset when ready
```

## Exponential backoff (with jitter and max sleep time)

```python
circuit = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,    # double sleep time after each trip
    max_sleep_time=30.0    # cap at 30 seconds
)
# Trip 1: 1s, Trip 2: 2s, Trip 3: 4s, Trip 4: 8s, ...
```

## Jitter (randomness to prevent thundering herd)

```python
circuit = Circuit(
    num_shorts_to_trip=5,
    sleep_time_after_trip=5.0,
    jitter=0.2  # ±20% randomness to prevent thundering herd
)
```

## Immediate trip (bypass the counter)

```python
try:
    result = call_service()
except CriticalError:
    circuit.trip()  # skip the counter, trip immediately
except MinorError:
    circuit.short()  # count normally
```

## Async support (native async support)

```python
# sync
circuit.short()

# async — .asynced() returns the async version, second () calls it
await circuit.short.asynced()()

# equivalent to:
async_short = circuit.short.asynced()
await async_short()
```

## Check state (get the current state of the circuit)

```python
circuit.times_shorted       # failures since last trip
circuit.total_trips         # lifetime trip count
circuit.current_sleep_time  # current backoff delay

breaker.broken              # is it broken?
```

## Reset backoff after success

```python
circuit = Circuit(
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=60.0
)

for batch in get_batches():
    try:
        result = process_batch(batch)
        circuit.reset_backoff()  # success! next failure starts at 1s, not wherever backoff left off
    except BatchError:
        circuit.short()
```

## Want to learn more?

- **Why page** — why `circuits` exists, coordinated shutdown, and cross-process circuit breaking
- **How to use** — full API reference for `Circuit` and `BreakingCircuit`
- **Examples** — progressively complex examples into a full script
- **How it works** — internal architecture (locks, backoff, `Share` integration) (level: beginner-intermediate)
