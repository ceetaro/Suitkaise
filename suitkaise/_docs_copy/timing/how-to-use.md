# timing: How to Use

This guide covers all public API in `suitkaise.timing`.

```python
from suitkaise import timing
from suitkaise.timing import Sktimer, TimeThis, timethis
```

## Simple timing functions

### `time() -> float`

```python
start = timing.time()
```

Returns the current Unix timestamp (`time.time()`).

### `sleep(seconds: float) -> float`

```python
end_time = timing.sleep(2.5)
```

Returns the current time after sleeping. Async usage:

```python
await timing.sleep.asynced()(2.5)
```

### `elapsed(time1, time2=None) -> float`

```python
elapsed = timing.elapsed(start_time)
```

If `time2` is omitted, current time is used. The result is always positive.

## `Sktimer`

### Basic usage

```python
t = Sktimer()
t.start()
do_work()
t.stop()
print(t.most_recent)
```

### Rolling window

```python
t = Sktimer(max_times=100)
```

### Lap and pause

```python
t.start()
do_work()
t.lap()       # record and continue
t.pause()
wait_for_input()
t.resume()
t.stop()
```

### Statistics

```python
t.mean
t.median
t.stdev
t.percentile(90)
```

## `TimeThis` context manager

One-off timing:

```python
with TimeThis() as timer:
    do_work()
print(timer.most_recent)
```

With explicit timer:

```python
shared = Sktimer()
with TimeThis(shared):
    do_work()
```

### Threshold filtering

```python
with TimeThis(threshold=0.05) as timer:
    do_work()
```

Times below threshold are discarded.

## `timethis` decorator

### Auto-created timer

```python
@timethis()
def fn():
    do_work()

fn()
print(fn.timer.mean)
```

### Explicit timer

```python
t = Sktimer()

@timethis(t)
def fn():
    do_work()
```

### Multiple timers

```python
@timethis()
@timethis(shared_timer)
def fn():
    do_work()
```

## `clear_global_timers()`

```python
timing.clear_global_timers()
```

Clears all timers created implicitly by `@timethis()` without an explicit timer.
