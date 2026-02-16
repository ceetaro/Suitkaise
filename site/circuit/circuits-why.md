/*

synced from suitkaise-docs/circuits/why.md

*/

rows = 2
columns = 1

# 1.1

title = "Why you should use `<suitkaise-api>circuits</suitkaise-api>`"

# 1.2

text = "
## TLDR

- **Prevent cascading failures** - Stop hammering a failing service
- **Built-in exponential backoff** - Automatic retry delay increase
- **Jitter** - Prevent thundering herd when multiple clients retry simultaneously
- **Two patterns** - Auto-reset (`<suitkaise-api>Circuit</suitkaise-api>`) vs manual control (`<suitkaise-api>BreakingCircuit</suitkaise-api>`)
- **Thread-safe** - Safe for concurrent use without manual locking
- **Native async support** - `.<suitkaise-api>asynced</suitkaise-api>()` for async/await contexts
- **Rate limiting** - Natural fit for API rate limits

---

## What makes `<suitkaise-api>circuits</suitkaise-api>` different

Most circuit breaker libraries handle a single use case: retry an external service with backoff. `<suitkaise-api>circuits</suitkaise-api>` does that, but it also does something others can't: **coordinate failure handling across threads and processes**.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>
import threading

shutdown = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=1)

def worker(worker_id):
    while not shutdown.<suitkaise-api>broken</suitkaise-api>:
        try:
            process_next_item()
        except FatalError:
            shutdown.<suitkaise-api>short</suitkaise-api>()  # all workers see this immediately
    print(f"Worker {worker_id}: shutting down gracefully")

threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
for t in threads:
    t.<suitkaise-api>start</suitkaise-api>()
```

One worker hits a fatal error. All four workers see `shutdown.<suitkaise-api>broken</suitkaise-api>` and stop gracefully. Thread-safe out of the box.

And with `<suitkaise-api>Share</suitkaise-api>` from `<suitkaise-api>processing</suitkaise-api>`, this works across processes too -- not just threads. More on that below.

---

Your code calls an external service. Sometimes that service fails.

What do you do?

1. The naive approach: retry immediately

```python
while True:
    try:
        <suitkaise-api>result</suitkaise-api> = call_external_service()
        break
    except ServiceError:
        pass  # retry immediately
```

This hammers the failing service with requests. If it's overloaded, you're making it worse. If it's rate-limiting you, you'll get banned.

2. The slightly better approach: add a delay

```python
import time

while True:
    try:
        <suitkaise-api>result</suitkaise-api> = call_external_service()
        break
    except ServiceError:
        time.sleep(1)
```

Better, sort of.
- Fixed delay is either too long (wasting time) or too short (still hammering)
- No escalation if failures continue
- No limit on retries

3. Actually use exponential backoff

```python
import time
import random

max_retries = 5
base_delay = 1.0
max_delay = 30.0

for attempt in range(max_retries):
    try:
        <suitkaise-api>result</suitkaise-api> = call_external_service()
        break
    except ServiceError:
        if attempt == max_retries - 1:
            raise
        
        # exponential backoff with jitter
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, delay * 0.1)
        time.sleep(delay + jitter)
```

This is dozens of lines of boilerplate. And, you have to do it every time, or create a helper function.

Also, you still need to handle:
- Thread safety if multiple threads share the retry logic
- Async support if you're using asyncio
- Different backoff strategies for different services

You are far away from being done. You are far away from a professional level solution.

4. The Solution

The solution is `<suitkaise-api>circuits</suitkaise-api>`.

```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>Circuit</suitkaise-api>

circuit = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0,
    jitter=0.1
)

while True:
    try:
        <suitkaise-api>result</suitkaise-api> = call_external_service()
        break
    except ServiceError:
        circuit.<suitkaise-api>short</suitkaise-api>()  # handles everything
```

One object. Clear and simple API.

---

## `<suitkaise-api>Circuit</suitkaise-api>` vs `<suitkaise-api>BreakingCircuit</suitkaise-api>`: the difference

### `<suitkaise-api>Circuit</suitkaise-api>` - Auto-resets

After N failures, sleeps and continues. The counter resets automatically.

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

for request in requests:
    try:
        process(request)
    except RateLimitError:
        circuit.<suitkaise-api>short</suitkaise-api>()  # after 5 shorts, sleeps 1s and continues
```

- Rate limit requests
- Throttle request rates
- When you have temporary failures that resolve themselves

### `<suitkaise-api>BreakingCircuit</suitkaise-api>` - Manual Reset

After N failures, stays broken until you manually reset.

```python
breaker = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

while not breaker.<suitkaise-api>broken</suitkaise-api>:
    try:
        <suitkaise-api>result</suitkaise-api> = risky_operation()
    except CriticalError:
        breaker.<suitkaise-api>short</suitkaise-api>()  # after 3 failures, circuit breaks

if breaker.<suitkaise-api>broken</suitkaise-api>:
    # decide what to do - fail gracefully, alert, etc.
    handle_failure()
    breaker.<suitkaise-api>reset</suitkaise-api>()  # manually reset when ready
```

- Operations where you need to decide how to proceed
- Coordinating multiple workers (one breaks, others see it)
- Graceful degradation with human or programmatic intervention

---

## Exponential Backoff

Each trip increases the sleep time.

Without `<suitkaise-api>circuits</suitkaise-api>`
```python
delay = 1.0
max_delay = 30.0
backoff_factor = 2.0

# somewhere in your retry loop
delay = min(delay * backoff_factor, max_delay)
time.sleep(delay)

# don't forget to track this state!
# don't forget thread safety!
# don't forget to reset it so it doesn't snowball!
```

With `<suitkaise-api>circuits</suitkaise-api>`
```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=5,
    sleep_time_after_trip=1.0,
    backoff_factor=2.0,
    max_sleep_time=30.0
)

# backoff is automatic
# 1st trip: 1.0s
# 2nd trip: 2.0s
# 3rd trip: 4.0s
# 4th trip: 8.0s
# 5th trip: 16.0s
# 6th trip: 30.0s (capped)
# 7th+ trip: 30.0s (capped)
```

Need to reset the backoff after a successful operation?

```python
circuit.<suitkaise-api>reset_backoff</suitkaise-api>()  # back to original sleep time
```

---

## Jitter

When many clients fail at the same time, they all retry at the same time. This causes a "thundering herd" that overwhelms the recovering service. This is especially bad if the service call needs to be rate limited.

Jitter adds randomness to the sleep time.

Without `<suitkaise-api>circuits</suitkaise-api>`
```python
import random

delay = 5.0
jitter_percent = 0.1

jittered_delay = delay + random.uniform(-delay * jitter_percent, delay * jitter_percent)
time.sleep(jittered_delay)
```

With `<suitkaise-api>circuits</suitkaise-api>`
```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=5,
    sleep_time_after_trip=5.0,
    jitter=0.1  # +/- 10% randomness
)

# delays will be between 4.5s and 5.5s
# clients naturally spread out their retries
```

---

## Thread Safety

Multiple threads calling the same circuit? No problem.

Without `<suitkaise-api>circuits</suitkaise-api>`
```python
import threading

lock = threading.Lock()
failure_count = 0
max_failures = 5

def handle_failure():
    global failure_count
    with lock:  # don't forget!
        failure_count += 1
        if failure_count >= max_failures:
            # do something
            failure_count = 0
```

With `<suitkaise-api>circuits</suitkaise-api>`
```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

def worker():
    # multiple threads can call this safely
    circuit.<suitkaise-api>short</suitkaise-api>()
```

`<suitkaise-api>Circuit</suitkaise-api>` and `<suitkaise-api>BreakingCircuit</suitkaise-api>` use `threading.RLock` internally. All operations are atomic.

---

## Native Async Support

Using asyncio? Just add `.<suitkaise-api>asynced</suitkaise-api>()`.

Without `<suitkaise-api>circuits</suitkaise-api>`
```python
import asyncio

# you need separate sync and async implementations
def sync_sleep_with_backoff():
    time.sleep(delay)

async def async_sleep_with_backoff():
    await asyncio.sleep(delay)
```

With `<suitkaise-api>circuits</suitkaise-api>`
```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

# sync
circuit.<suitkaise-api>short</suitkaise-api>()

# async
await circuit.<suitkaise-api>short</suitkaise-api>.<suitkaise-api>asynced</suitkaise-api>()()
```

Same circuit, same state, works in both contexts.

---

## Rate Limiting

`<suitkaise-api>Circuit</suitkaise-api>` is perfect for rate limiting.

```python
rate_limiter = <suitkaise-api>Circuit</suitkaise-api>(
    num_shorts_to_trip=100,      # 100 requests per window
    sleep_time_after_trip=60.0,  # wait 60s when limit hit
)

for request in requests:
    rate_limiter.<suitkaise-api>short</suitkaise-api>()  # counts each request
    process(request)
```

Every 100 requests, it pauses for 60 seconds. No external rate limit tracking needed.

---

## Immediate Trip

Sometimes you know something is catastrophically wrong and want to trip immediately.

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=10, sleep_time_after_trip=5.0)

try:
    <suitkaise-api>result</suitkaise-api> = call_service()
except CriticalError:
    circuit.<suitkaise-api>trip</suitkaise-api>()  # skip the counter, trip immediately
except MinorError:
    circuit.<suitkaise-api>short</suitkaise-api>()  # increment counter normally
```

---

## Custom Sleep Per Call

Override the sleep time for a specific failure.

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

try:
    <suitkaise-api>result</suitkaise-api> = call_service()
except RateLimitError as e:
    # API told us to wait 30 seconds
    circuit.<suitkaise-api>short</suitkaise-api>(custom_sleep=e.retry_after)
except OtherError:
    circuit.<suitkaise-api>short</suitkaise-api>()  # use default
```

---

## Coordinated Shutdown

`<suitkaise-api>BreakingCircuit</suitkaise-api>` is great for coordinating multiple workers.

```python
import threading

shutdown_circuit = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=1)

def worker(worker_id):
    while not shutdown_circuit.<suitkaise-api>broken</suitkaise-api>:
        try:
            process_next_item()
        except FatalError:
            shutdown_circuit.<suitkaise-api>short</suitkaise-api>()  # signals all workers to stop
    
    print(f"Worker {worker_id} shutting down")

# start workers
threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
for t in threads:
    t.<suitkaise-api>start</suitkaise-api>()

# one worker hits a fatal <suitkaise-api>error</suitkaise-api>
# all workers see shutdown_circuit.<suitkaise-api>broken</suitkaise-api> and stop gracefully
```

---

## Tracking State

Both circuits track useful state:

```python
circuit = <suitkaise-api>Circuit</suitkaise-api>(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

circuit.<suitkaise-api>times_shorted</suitkaise-api>      # failures since last trip
circuit.<suitkaise-api>total_trips</suitkaise-api>        # lifetime trip count
circuit.<suitkaise-api>current_sleep_time</suitkaise-api> # current backoff delay

breaker = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=3)

breaker.<suitkaise-api>broken</suitkaise-api>             # is it broken?
breaker.<suitkaise-api>times_shorted</suitkaise-api>      # failures since last reset
breaker.<suitkaise-api>total_trips</suitkaise-api>        # lifetime trip count
```

---

## Cross-process circuit breaking with `<suitkaise-api>Share</suitkaise-api>`

The coordinated shutdown example above works with threads. But with `<suitkaise-api>Share</suitkaise-api>` from `<suitkaise-api>processing</suitkaise-api>`, it works across entirely separate processes.

```python
from <suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api> import <suitkaise-api>Share</suitkaise-api>, <suitkaise-api>Pool</suitkaise-api>, <suitkaise-api>Skprocess</suitkaise-api>
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>BreakingCircuit</suitkaise-api>

share = <suitkaise-api>Share</suitkaise-api>()
share.circuit = <suitkaise-api>BreakingCircuit</suitkaise-api>(num_shorts_to_trip=3)

class ResilientWorker(<suitkaise-api>Skprocess</suitkaise-api>):
    def __init__(self, share):
        self.share = share

    def <suitkaise-api>__run__</suitkaise-api>(self):
        if self.share.circuit.<suitkaise-api>broken</suitkaise-api>:
            self.<suitkaise-api>stop</suitkaise-api>()
            return
        
        try:
            <suitkaise-api>result</suitkaise-api> = call_flaky_service()
        except ServiceError:
            self.share.circuit.<suitkaise-api>short</suitkaise-api>()

pool = <suitkaise-api>Pool</suitkaise-api>(workers=8)
pool.<suitkaise-api>map</suitkaise-api>(ResilientWorker, [share] * 8)
```

Eight separate processes, each with their own GIL, their own memory space -- and they all see the same circuit state. When three failures accumulate from any combination of workers, the circuit trips and all workers can respond.

This is the kind of cross-process coordination that normally requires Redis or a database. With `<suitkaise-api>circuits</suitkaise-api>` + `<suitkaise-api>Share</suitkaise-api>`, it's zero infrastructure.
"
