/*

synced from suitkaise-docs/circuits/quick-start.md

*/

rows = 2
columns = 1

# 1.1

title = "`<suitkaise-api>circuits</suitkaise-api>` quick start guide"

# 1.2

text = "
```bash
pip install <suitkaise-api>suitkaise</suitkaise-api>
```

## Auto-resetting circuit (`<suitkaise-api>Circuit</suitkaise-api>`)

Sleeps after N failures, then resets and continues.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

<suitkaise-api>circuit</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>num_shorts_to_trip=5, sleep_time_after_trip=1.0<suitkaise-api>)</suitkaise-api>

for request in incoming_requests:
    try:
        process(request)
    except ServiceError:
        <suitkaise-api>circuit.short()</suitkaise-api>  # after 5 failures, sleeps 1s, then resets
```

## Breaking circuit (`<suitkaise-api>BreakingCircuit</suitkaise-api>`)

Stays broken after N failures until you manually reset.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

<suitkaise-api>breaker</suitkaise-api> = <suitkaise-api>BreakingCircuit(</suitkaise-api>num_shorts_to_trip=3, sleep_time_after_trip=1.0<suitkaise-api>)</suitkaise-api>

while not <suitkaise-api>breaker.broken</suitkaise-api>:
    try:
        <suitkaise-api>result</suitkaise-api> = risky_operation()
        break
    except OperationError:
        <suitkaise-api>breaker.short()</suitkaise-api>

if <suitkaise-api>breaker.broken</suitkaise-api>:
    handle_failure()
    <suitkaise-api>breaker.reset()</suitkaise-api>  # manually reset when ready
```

## Exponential backoff (with jitter and max sleep time)

```python
<suitkaise-api>circuit</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,    # double sleep time after each trip
    max_sleep_time=30.0    # cap at 30 seconds
<suitkaise-api>)</suitkaise-api>
# Trip 1: 1s, Trip 2: 2s, Trip 3: 4s, Trip 4: 8s, ...
```

## Jitter (randomness to prevent thundering herd)

```python
<suitkaise-api>circuit</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
    num_shorts_to_trip=5,
    sleep_time_after_trip=5.0,
    jitter=0.2  # ±20% randomness to prevent thundering herd
<suitkaise-api>)</suitkaise-api>
```

## Immediate trip (bypass the counter)

```python
try:
    <suitkaise-api>result</suitkaise-api> = call_service()
except CriticalError:
    <suitkaise-api>circuit.trip()</suitkaise-api>  # skip the counter, trip immediately
except MinorError:
    <suitkaise-api>circuit.short()</suitkaise-api>  # count normally
```

## Async support (native async support)

```python
# sync
<suitkaise-api>circuit.short()</suitkaise-api>

# async — .asynced() returns the async version, second () calls it
await <suitkaise-api>circuit.short.asynced()()</suitkaise-api>

# equivalent to:
<suitkaise-api>async_short</suitkaise-api> = <suitkaise-api>circuit.short.asynced()</suitkaise-api>
await <suitkaise-api>async_short()</suitkaise-api>
```

## Check state (get the current state of the circuit)

```python
<suitkaise-api>circuit.times_shorted</suitkaise-api>       # failures since last trip
<suitkaise-api>circuit.total_trips</suitkaise-api>         # lifetime trip count
<suitkaise-api>circuit.current_sleep_time</suitkaise-api>  # current backoff delay

<suitkaise-api>breaker.broken</suitkaise-api>              # is it broken?
```

## Reset backoff after success

```python
<suitkaise-api>circuit</suitkaise-api> = <suitkaise-api>Circuit(</suitkaise-api>
    num_shorts_to_trip=3,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=60.0
<suitkaise-api>)</suitkaise-api>

for batch in get_batches():
    try:
        result = process_batch(batch)
        <suitkaise-api>circuit.reset_backoff()</suitkaise-api>  # success! next failure starts at 1s, not wherever backoff left off
    except BatchError:
        <suitkaise-api>circuit.short()</suitkaise-api>
```

## Want to learn more?

- **Why page** — why `<suitkaise-api>circuits</suitkaise-api>` exists, coordinated shutdown, and cross-process circuit breaking
- **How to use** — full API reference for `<suitkaise-api>Circuit</suitkaise-api>` and `<suitkaise-api>BreakingCircuit</suitkaise-api>`
- **Examples** — progressively complex examples into a full script
- **How it works** — internal architecture (locks, backoff, `<suitkaise-api>Share</suitkaise-api>` integration) (level: beginner-intermediate)
"
