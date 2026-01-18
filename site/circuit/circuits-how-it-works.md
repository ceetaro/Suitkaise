/*

how the circuit module actually works.

*/

rows = 2
columns = 1

# 1.1

title = "How `circuit` actually works"

# 1.2

text = "

`circuit` has no dependencies outside of the standard library.

It contains one class: `Circuit`.

---

## `Circuit` class

A "circuit breaker" that trips and can stop execution after a certain number of `short()` calls (failures), or immediately if you call `trip()`.

Initialize with:
- `num_shorts_to_trip`: Maximum number of shorts before the circuit trips (int)
- `sleep_time_after_trip`: Sleep duration in seconds when circuit trips (`float`, default `0.0`)
- `jitter`: Random +/- percent of sleep time to spread retries (`float`, default `0.0`)

```python
from suitkaise.circuit import Circuit

# Create a circuit that trips after 5 shorts
breaker = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=0.5)
```

### `Circuit.__init__()`

1. Stores `num_shorts_to_trip` as the threshold limit
2. Stores `sleep_time_after_trip` as the default sleep duration
3. Sets `broken` to `False` (circuit starts operational)
4. Sets `times_shorted` to `0` (no failures yet)
5. Sets `total_failures` to `0` (lifetime failure counter)
6. Creates `_lock` as a `threading.RLock()` for thread safety

The circuit is now ready to track failures.

---

## Properties

### `Circuit.broken`

Boolean indicating whether the circuit has broken.

- `False` — circuit is operational, loop should continue
- `True` — circuit has broken, loop should exit

Typical usage:
```python
# while the circuit hasn't broken...
while not breaker.broken:
    # ... your loop logic ...
```

### `Circuit.times_shorted`

Integer counter tracking how many times `short()` has been called since last reset.

Resets to `0` when the circuit trips or when `reset()` is called.

### `Circuit.total_failures`

Integer counter tracking the total number of failures over the lifetime of the circuit.

Incremented by:
- Each call to `short()`
- Each call to `trip()`

Never resets — persists across `reset()` calls. Useful for monitoring overall failure rate.

---

## Methods

### `Circuit.short()`

Increments the failure count and trips the circuit if the limit is reached.

Arguments:
- `custom_sleep`: Optional override for sleep duration if this short causes a trip (float)

Returns:
- None

1. Increments `times_shorted` by 1
2. Increments `total_failures` by 1
3. Checks if `times_shorted >= num_shorts_to_trip`:
   - *If True:*
     - Calls `_break_circuit()` with the sleep duration
     - Uses `custom_sleep` if provided, otherwise uses `sleep_time_after_trip`
   - *If False:*
     - Does nothing (just counts the failure)

```python
breaker = circuit.Circuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

breaker.short()  # times_shorted = 1, total_failures = 1, broken = False
breaker.short()  # times_shorted = 2, total_failures = 2, broken = False
breaker.short()  # times_shorted = 3 -> 0, total_failures = 4, broken = True, sleeps 1.0s
```

### `Circuit.trip()`

Immediately trips the circuit, bypassing short counting.

Arguments:
- `custom_sleep`: Optional override for sleep duration (float)

Returns:
- None

1. Increments `total_failures` by 1
2. Calls `_break_circuit()` immediately
3. Uses `custom_sleep` if provided, otherwise uses `sleep_time_after_trip`

This is useful when you want to force the circuit to trip regardless of the current short count. In circuit breaker terminology, when a breaker activates it 'trips'.

```python
breaker = circuit.Circuit(num_shorts_to_trip=10, sleep_time_after_trip=0.5)

# Something catastrophic happened, trip immediately
if critical_failure:
    breaker.trip()  # broken = True, sleeps 0.5s
```

### `Circuit.reset()`

Resets the circuit to its initial operational state.

Arguments:
- None

Returns:
- None

1. Sets `broken` to `False`
2. Sets `times_shorted` to `0`

This allows you to reuse the same circuit after it has broken.

```python
breaker = circuit.Circuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

# First batch of operations
while not breaker.broken:
    try:
        risky_operation()
    except Error:
        breaker.short()

# Reset for next batch
breaker.reset()

# Second batch of operations (total_failures persists)
while not breaker.broken:
    # ...
```

---

## Internal Methods

### `Circuit._break_circuit()`

Internal method that handles the actual circuit tripping.

Arguments:
- `sleep_duration`: How long to sleep after tripping (float)

Returns:
- None

1. Sets `broken` to `True`
2. Resets `times_shorted` to `0`
3. If `sleep_duration > 0`:
   - Calls `sktime.sleep(sleep_duration)`

The sleep gives downstream systems time to recover before the next attempt (if the circuit is reset).

---

## State Transitions

The circuit has two states:

### Running State (`broken = False`)
- Loop continues running
- `short()` increments counter
- Transitions to Broken when `times_shorted >= num_shorts_to_trip` or when `trip()` is called

### Broken State (`broken = True`)
- Loop should exit
- Counter is reset to 0
- Transitions back to Running via `reset()`

---

When the circuit breaks, `times_shorted` is reset to 0.

Use `total_failures` to track lifetime failures across resets.

---

By default, `sleep_time_after_trip=0` (no sleep). Set it if you want a cooldown:

```python
breaker = circuit.Circuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)  # Sleeps 1s on trip
```

The `custom_sleep` parameter on `short()` and `trip()` allows per-call overrides:

```python
breaker = circuit.Circuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

# Normal failure
breaker.short()  # Would sleep 1.0s if this trips

# Critical failure with longer cooldown
breaker.short(custom_sleep=5.0)  # Would sleep 5.0s if this trips
```

---

## Thread Safety

`Circuit` is thread-safe. All property access and state modifications are protected by an internal `threading.RLock()`.

You can safely use a single `Circuit` instance across multiple threads:

```python
import threading
from suitkaise import circuit

breaker = circuit.Circuit(num_shorts_to_trip=5)

def worker():
    while not breaker.broken:  # Thread-safe read
        try:
            do_work()
        except Error:
            breaker.short()  # Thread-safe modification

# Multiple threads can share the same breaker
threads = [threading.Thread(target=worker) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

(This section should be a dropdown that users can expand.)
*What is a reentrant lock?*

A reentrant lock is a lock that can be acquired by the same thread multiple times without deadlocking.

This is useful for thread safety, as it allows the same thread to acquire the lock multiple times from different code or methods.
(End of dropdown)

---

## Error Handling

The `Circuit` class does not raise exceptions. All methods are safe to call:

- `short()` — never raises
- `trip()` — never raises
- `reset()` — never raises

The only potential exception is from `sktime.sleep()` if interrupted, which would propagate normally.

---

## Memory

Each `Circuit` instance stores 6 values:
- `num_shorts_to_trip` (int) — ~28 bytes
- `sleep_time_after_trip` (float) — ~24 bytes
- `_broken` (bool) — ~28 bytes
- `_times_shorted` (int) — ~28 bytes
- `_total_failures` (int) — ~28 bytes
- `_lock` (RLock) — ~56 bytes

Total: ~192 bytes per instance. (very lightweight)

"
