# How `timing` actually works

`timing` provides simple and powerful timing utilities for measuring execution time, collecting statistics, and analyzing performance.

- `Sktimer` - statistical timer with thread-safe concurrent sessions
- `TimerStats` - frozen snapshot of timer statistics
- `TimeThis` - context manager for timing code blocks
- `timethis` - decorator for timing function executions
- Simple functions: `time()`, `sleep()`, `elapsed()`

## Simple Functions

### `time()`

Get the current Unix timestamp.

```python
def time() -> float:
    return time.time()
```

Returns
`float`: Current Unix timestamp.

Directly wraps Python's `time.time()`.

### `sleep()`

Sleep the current thread.

```python
def _sync_sleep(seconds: float) -> float:
    time.sleep(seconds)
    return time.time()

async def _async_sleep(seconds: float) -> float:
    await asyncio.sleep(seconds)
    return time.time()

_sleep_impl = _AsyncableFunction(_sync_sleep, _async_sleep, name='sleep')

def sleep(seconds: float) -> float:
    return _sleep_impl(seconds)

sleep.asynced = _sleep_impl.asynced
```

Arguments
`seconds`: Number of seconds to sleep.
- `float`
- required

Returns
`float`: Current time after sleeping.

The function uses `_AsyncableFunction` to provide both sync and async implementations:
- Sync: Uses `time.sleep()` internally
- Async: Uses `asyncio.sleep()` internally via `.asynced()`

### `elapsed()`

Calculate elapsed time between timestamps.

```python
def _elapsed_time(time1: float, time2: Optional[float] = None) -> float:
    if time2 is None:
        time2 = time.time()
    
    # return absolute difference so order doesn't matter
    return fabs(time2 - time1)
```

Arguments
`time1`: First timestamp.
- `float`
- required

`time2`: Second timestamp.
- `float | None = None`
- defaults to current time

Returns
`float`: Absolute elapsed time in seconds.

Uses `math.fabs()` to always return positive value regardless of argument order.

## `Sktimer`

Statistical timer for collecting and analyzing execution times.

Arguments
`max_times`: Rolling window size.
- `int | None = None`
- if `None`, keeps all measurements

Returns
`Sktimer`: A new timer instance.

### Tracking State

`original_start_time: float | None`
Earliest start time across all sessions. Set on first `start()` call.

`times: list[float]`
Aggregated list of all recorded measurements across all sessions.

`_paused_durations: list[float]`
Parallel list of paused durations for each recorded measurement.

`_max_times: int | None`
Rolling window size. `None` means keep all.

`_lock: threading.RLock`
Thread safety lock for manager state.

`_sessions: dict[int, TimerSession]`
Per-thread timing sessions, keyed by thread ident.

### Thread Model

`Sktimer` uses a session-per-thread model for concurrent safety.

```text
Thread 1                    Thread 2
   │                           │
   ├─ start() ──────────┐      ├─ start() ──────────┐
   │                    │      │                    │
   │  TimerSession 1    │      │  TimerSession 2    │
   │   └─ frames: [f1]  │      │   └─ frames: [f2]  │
   │                    │      │                    │
   ├─ stop() ───────────┘      ├─ stop() ───────────┘
   │                           │
   └───────────────────────────┴─────────────────────→ times[]
```

Each thread gets its own `TimerSession`. Results aggregate into shared `times` list protected by `_lock`.

### `start()`

Start timing a new measurement.

```python
def start(self) -> float:
    # warn if there's already an active frame
    if self._has_active_frame():
        warnings.warn(
            "Sktimer.start() called while timing is already in progress. "
            "This creates a nested timing frame.",
            UserWarning,
            stacklevel=2
        )
    
    # get or create session for current thread
    sess = self._get_or_create_session()
    started = sess.start()
    
    with self._lock:
        if self.original_start_time is None:
            self.original_start_time = started
    return started
```

1. Check if current thread already has an active timing frame
2. Warn if nesting (user might not intend this)
3. Get or create a `TimerSession` for current thread
4. Call `sess.start()` to push a new frame
5. Record `original_start_time` if this is the first ever start

Returns
`float`: Start timestamp from `perf_counter()`.

### `stop()`

Stop timing and record the measurement.

```python
def stop(self) -> float:
    sess = self._get_or_create_session()
    elapsed, paused_total = sess.stop()
    
    with self._lock:
        self.times.append(elapsed)
        self._paused_durations.append(paused_total)
        self._trim_to_max()
    return elapsed
```

1. Get session for current thread
2. Call `sess.stop()` to pop frame and get elapsed time
3. Under lock: append to `times` and `_paused_durations`
4. Trim to rolling window if configured

Returns
`float`: Elapsed time for this measurement.

Raises
`RuntimeError`: If timer was not started.

### `discard()`

Stop timing but do NOT record.

```python
def discard(self) -> float:
    sess = self._get_or_create_session()
    elapsed, _ = sess.stop()
    # intentionally NOT appending to times or _paused_durations
    return elapsed
```

1. Get session for current thread
2. Call `sess.stop()` to pop frame
3. Return elapsed time without recording

Returns
`float`: Elapsed time that was discarded.

### `lap()`

Record a lap time (stop + start in one call).

```python
def lap(self) -> float:
    sess = self._get_or_create_session()
    elapsed, paused_total = sess.lap()
    
    with self._lock:
        self.times.append(elapsed)
        self._paused_durations.append(paused_total)
        self._trim_to_max()
    return elapsed
```

1. Get session for current thread
2. Call `sess.lap()` which records elapsed and restarts frame
3. Under lock: append to lists and trim

Returns
`float`: Elapsed time for this lap.

### `pause()` / `resume()`

Pause and resume the current timing measurement.

```python
def pause(self) -> None:
    sess = self._get_or_create_session()
    sess.pause()

def resume(self) -> None:
    sess = self._get_or_create_session()
    sess.resume()
```

Delegates to session which tracks pause state in the current frame.

### `add_time()`

Manually add a timing measurement.

```python
def add_time(self, elapsed_time: float) -> None:
    with self._lock:
        self.times.append(elapsed_time)
        self._paused_durations.append(0.0)
        self._trim_to_max()
```

Directly appends to `times` with zero paused duration.

### `set_max_times()`

Set the rolling window size.

```python
def set_max_times(self, max_times: Optional[int]) -> None:
    if max_times is not None and max_times <= 0:
        raise ValueError("max_times must be a positive integer or None")
    
    with self._lock:
        self._max_times = max_times
        self._trim_to_max()

def _trim_to_max(self) -> None:
    if self._max_times is None:
        return
    excess = len(self.times) - self._max_times
    if excess <= 0:
        return
    del self.times[:excess]
    del self._paused_durations[:excess]
```

When `max_times` is set, oldest measurements are discarded to keep only the most recent N.

### `reset()`

Clear all timing measurements.

```python
def reset(self) -> None:
    with self._lock:
        self.times.clear()
        self.original_start_time = None
        self._sessions.clear()
        self._paused_durations.clear()
```

Resets all state including per-thread sessions.

### Statistics Properties

All statistics properties are computed live from `times` list under lock.

```python
@property
def mean(self) -> Optional[float]:
    with self._lock:
        return statistics.mean(self.times) if self.times else None

@property
def stdev(self) -> Optional[float]:
    with self._lock:
        if len(self.times) <= 1:
            return None
        return statistics.stdev(self.times)
```

Available properties:
- `num_times`, `most_recent`, `result`, `most_recent_index`
- `total_time`, `total_time_paused`
- `mean`, `median`, `min`, `max`
- `fastest_time`, `slowest_time`, `fastest_index`, `slowest_index`
- `stdev`, `variance`, `max_times`

### `percentile()`

Calculate any percentile using linear interpolation.

```python
def percentile(self, percent: float) -> Optional[float]:
    with self._lock:
        if not self.times:
            return None
        
        if not 0 <= percent <= 100:
            raise ValueError("Percentile must be between 0 and 100")
        
        sorted_times = sorted(self.times)
        index = (percent / 100) * (len(sorted_times) - 1)
        
        if index == int(index):
            return sorted_times[int(index)]
        
        # linear interpolation
        lower_index = int(index)
        upper_index = lower_index + 1
        weight = index - lower_index
        return (sorted_times[lower_index] * (1 - weight) + 
                sorted_times[upper_index] * weight)
```

### `get_statistics()` / `get_stats()`

Get a frozen snapshot.

```python
def get_statistics(self) -> Optional[TimerStats]:
    with self._lock:
        if not self.times:
            return None
        return TimerStats(self.times, self.original_start_time, self._paused_durations)
```

Returns a `TimerStats` object with copied data that won't change.

### Share Integration

`Sktimer` defines `_shared_meta` for use with `suitkaise.processing.Share`:

```python
_shared_meta = {
    'methods': {
        'start': {'writes': ['_sessions', 'original_start_time']},
        'stop': {'writes': ['times', '_paused_durations']},
        'discard': {'writes': []},
        'lap': {'writes': ['times', '_paused_durations']},
        'pause': {'writes': ['_sessions']},
        'resume': {'writes': ['_sessions']},
        'add_time': {'writes': ['times', '_paused_durations']},
        'set_max_times': {'writes': ['times', '_paused_durations', '_max_times']},
        'reset': {'writes': ['times', '_sessions', '_paused_durations', 'original_start_time']},
        'get_statistics': {'writes': []},
        'get_stats': {'writes': []},
        'get_time': {'writes': []},
        'percentile': {'writes': []},
    },
    'properties': {
        'num_times': {'reads': ['times']},
        'most_recent': {'reads': ['times']},
        # ... etc
    }
}
```

This metadata declares which attributes each method/property reads or writes, enabling the Share to coordinate synchronization.

## `TimerSession`

Per-thread timing session supporting nested frames.

```python
class TimerSession:
    def __init__(self, manager: Sktimer):
        self._manager = manager
        self._frames: Deque[Dict[str, Any]] = deque()
        self._lock = threading.RLock()
```

### Frame Structure

Each timing frame is a dict:

```python
frame = {
    'start_time': float,       # perf_counter() at start
    'paused': bool,            # currently paused?
    'pause_started_at': float, # when pause began (or None)
    'total_paused': float,     # accumulated paused time
}
```

### `start()`

Push a new frame onto the stack.

```python
def start(self) -> float:
    with self._lock:
        frame = {
            'start_time': self._now(),
            'paused': False,
            'pause_started_at': None,
            'total_paused': 0.0,
        }
        self._frames.append(frame)
        return frame['start_time']
```

Uses `perf_counter()` for high-resolution monotonic timing.

### `stop()`

Pop the top frame and return elapsed time.

```python
def stop(self) -> tuple[float, float]:
    with self._lock:
        frame = self._top()
        elapsed = self._elapsed_from_frame(frame)
        paused_total = self._paused_total_from_frame(frame)
        self._frames.pop()
        return elapsed, paused_total
```

### `lap()`

Record elapsed time and restart the frame.

```python
def lap(self) -> tuple[float, float]:
    with self._lock:
        frame = self._top()
        elapsed = self._elapsed_from_frame(frame)
        paused_total = self._paused_total_from_frame(frame)
        # restart frame
        frame['start_time'] = self._now()
        frame['total_paused'] = 0.0
        frame['paused'] = False
        frame['pause_started_at'] = None
        return elapsed, paused_total
```

Keeps the frame but resets its timing state.

### `pause()` / `resume()`

```python
def pause(self) -> None:
    with self._lock:
        frame = self._top()
        if frame['paused']:
            warnings.warn("Sktimer is already paused.", UserWarning, stacklevel=2)
            return
        frame['paused'] = True
        frame['pause_started_at'] = self._now()

def resume(self) -> None:
    with self._lock:
        frame = self._top()
        if not frame['paused']:
            warnings.warn("Sktimer is not paused.", UserWarning, stacklevel=2)
            return
        pause_duration = self._now() - frame['pause_started_at']
        frame['total_paused'] += pause_duration
        frame['paused'] = False
        frame['pause_started_at'] = None
```

### Elapsed Calculation

```python
def _elapsed_from_frame(self, frame: Dict[str, Any]) -> float:
    end = self._now()
    paused_extra = 0.0
    # if currently paused, add time since pause started
    if frame['paused'] and frame['pause_started_at'] is not None:
        paused_extra = end - frame['pause_started_at']
    
    return (end - frame['start_time']) - (frame['total_paused'] + paused_extra)
```

Total elapsed = (end - start) - total paused time.

## `TimerStats`

Frozen snapshot of timer statistics.

```python
class TimerStats:
    def __init__(self, times: List[float], original_start_time: Optional[float], paused_durations: List[float]):
        self.times = times.copy()  # copy for immutability
        
        self.original_start_time = original_start_time
        self.num_times = len(times)
        self.most_recent = times[-1] if times else None
        self.most_recent_index = len(times) - 1 if times else None
        self.total_time = sum(times) if times else None
        self.total_time_paused = sum(paused_durations) if paused_durations else None
        
        self.mean = statistics.mean(times) if times else None
        self.median = statistics.median(times) if times else None
        self.min = min(times) if times else None
        self.max = max(times) if times else None
        self.stdev = statistics.stdev(times) if len(times) > 1 else None
        self.variance = statistics.variance(times) if len(times) > 1 else None
        # ... etc
```

All values are computed once at construction time and stored as attributes.

### `percentile()`

Same algorithm as `Sktimer.percentile()` but operates on the frozen `times` copy.

## `TimeThis` Context Manager

Context manager wrapper around `Sktimer`.

```python
class TimeThis:
    def __init__(self, timer: Optional[Sktimer] = None, threshold: float = 0.0):
        self.timer = timer or Sktimer()
        self.threshold = threshold

    def __enter__(self):
        self.timer.start()
        return self.timer
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Get elapsed time without recording
        elapsed = self.timer.discard()
        
        # Only record if above threshold
        if elapsed >= self.threshold:
            self.timer.add_time(elapsed)
```

### Flow

1. `__enter__`: Call `timer.start()`, return timer for `as` clause
2. User code executes
3. `__exit__`: Call `timer.discard()` to get elapsed without recording
4. Only record via `add_time()` if above threshold

### Methods

Delegates to the underlying timer:

```python
def pause(self):
    self.timer.pause()

def resume(self):
    self.timer.resume()

def lap(self):
    self.timer.lap()
```

## `timethis` Decorator

Decorator that times function executions.

```python
def timethis(
    timer: Optional[Sktimer] = None,
    threshold: float = 0.0,
    max_times: Optional[int] = None,
) -> Callable:
```

### With Explicit Timer

```python
def decorator(func: Callable) -> Callable:
    if timer is not None:
        if max_times is not None:
            timer.set_max_times(max_times)
        wrapper = _timethis_decorator(timer, threshold)(func)
    # ...
    return wrapper
```

Uses provided timer directly.

### With Auto-Created Timer

```python
def decorator(func: Callable) -> Callable:
    # ...
    else:
        # extract module name
        frame = inspect.currentframe()
        module_name = frame.f_back.f_globals.get('__name__', 'unknown')
        if '.' in module_name:
            module_name = module_name.split('.')[-1]
        
        # build timer name from function qualname
        func_qualname = func.__qualname__
        if '.' in func_qualname:
            class_name, func_name = func_qualname.rsplit('.', 1)
            timer_name = f"{module_name}_{class_name}_{func_name}_timer"
        else:
            timer_name = f"{module_name}_{func_qualname}_timer"
        
        # get or create global timer (thread-safe)
        if not hasattr(timethis, '_global_timers'):
            setattr(timethis, '_global_timers', {})
            setattr(timethis, '_timers_lock', threading.RLock())
        
        lock = getattr(timethis, '_timers_lock')
        with lock:
            global_timers = getattr(timethis, '_global_timers')
            if timer_name not in global_timers:
                global_timers[timer_name] = Sktimer(max_times=max_times)
        
        wrapper = _timethis_decorator(global_timers[timer_name], threshold)(func)
        setattr(wrapper, 'timer', global_timers[timer_name])
    
    return wrapper
```

1. Extract module name from caller's frame
2. Build timer name from function's `__qualname__`
3. Get or create global timer (thread-safe with lock)
4. Attach timer to wrapped function as `.timer`

### Timer Naming Convention

- Module-level function `foo()` in `mymodule.py`: `mymodule_foo_timer`
- Class method `Bar.baz()` in `mymodule.py`: `mymodule_Bar_baz_timer`

### `_timethis_decorator()`

The actual timing wrapper:

```python
def _timethis_decorator(timer: Sktimer, threshold: float = 0.0):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # avoid nested timing frames on the same timer
            if timer._has_active_frame():
                start = perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed = perf_counter() - start
                    if elapsed >= threshold:
                        timer.add_time(elapsed)
            else:
                timer.start()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = timer.discard()
                    if elapsed >= threshold:
                        timer.add_time(elapsed)
        return wrapper
    return decorator
```

Two paths:
1. **Already timing**: Use `perf_counter()` directly to avoid nested frames
2. **Not timing**: Use `start()`/`discard()`/`add_time()` flow

Both paths only record if elapsed >= threshold.

## `clear_global_timers()`

Clear auto-created timers.

```python
def clear_global_timers() -> None:
    if hasattr(timethis, '_timers_lock') and hasattr(timethis, '_global_timers'):
        lock = getattr(timethis, '_timers_lock')
        with lock:
            timers = getattr(timethis, '_global_timers')
            timers.clear()
```

Thread-safe clearing of the global timer registry.

## Thread Safety

`Sktimer` is fully thread-safe:

1. **Manager-level lock** (`_lock`): Protects `times`, `_paused_durations`, `_sessions`
2. **Session-level lock**: Each `TimerSession` has its own lock for frame operations
3. **Global timer lock**: `timethis._timers_lock` protects auto-created timer registry

`threading.RLock` (reentrant lock) is used because operations may call each other.
