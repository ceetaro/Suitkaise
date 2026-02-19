/*

synced from suitkaise-docs/timing/how-it-works.md

*/

rows = 2
columns = 1

# 1.1

title = "How `timing` actually works"

# 1.2

text = "
`<suitkaise-api>timing</suitkaise-api>` provides simple and powerful timing utilities for measuring execution time, collecting statistics, and analyzing performance.

- `<suitkaise-api>Sktimer</suitkaise-api>` - statistical timer with thread-safe concurrent sessions
- `TimerStats` - frozen snapshot of timer statistics
- `<suitkaise-api>TimeThis</suitkaise-api>` - context manager for timing code blocks
- `<suitkaise-api>timethis</suitkaise-api>` - decorator for timing function executions
- Simple functions: `time()`, `sleep()`, `<suitkaise-api>elapsed</suitkaise-api>()`

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

sleep.asynced = _sleep_impl.<suitkaise-api>asynced</suitkaise-api>
```

Arguments
`seconds`: Number of seconds to sleep.
- `float`
- Required

Returns
`float`: Current time after sleeping.

The function uses `_AsyncableFunction` to provide both sync and async implementations:
- Sync: Uses `time.sleep()` internally
- Async: Uses `asyncio.sleep()` internally via `.<suitkaise-api>asynced</suitkaise-api>()`

### `<suitkaise-api>elapsed</suitkaise-api>()`

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
- Required

`time2`: Second timestamp.
- `float | None = None`
- Defaults to current time

Returns
`float`: Absolute elapsed time in seconds.

Uses `math.fabs()` to always return positive value regardless of argument order.

## `<suitkaise-api>Sktimer</suitkaise-api>`

Statistical timer for collecting and analyzing execution times.

Arguments
`max_times`: Rolling window size.
- `int | None = None`
- If `None`, keeps all measurements

Returns
`<suitkaise-api>Sktimer</suitkaise-api>`: A new timer instance.

### Tracking State

`original_start_time: float | None`
Earliest start time across all sessions. Set on first `<suitkaise-api>start</suitkaise-api>()` call.

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

`<suitkaise-api>Sktimer</suitkaise-api>` uses a session-per-thread model for concurrent safety.

```text
Thread 1                    Thread 2
   │                           │
   ├─ <suitkaise-api>start</suitkaise-api>() ──────────┐      ├─ <suitkaise-api>start</suitkaise-api>() ──────────┐
   │                    │      │                    │
   │  TimerSession 1    │      │  TimerSession 2    │
   │   └─ frames: [f1]  │      │   └─ frames: [f2]  │
   │                    │      │                    │
   ├─ <suitkaise-api>stop</suitkaise-api>() ───────────┘      ├─ <suitkaise-api>stop</suitkaise-api>() ───────────┘
   │                           │
   └───────────────────────────┴─────────────────────→ times[]
```

Each thread gets its own `TimerSession`. Results aggregate into shared `times` list protected by `_lock`.

### `<suitkaise-api>start</suitkaise-api>()`

Start timing a new measurement.

```python
def <suitkaise-api>start</suitkaise-api>(self) -> float:
    # warn if there's already an active frame
    if self._has_active_frame():
        warnings.warn(
            "<suitkaise-api>Sktimer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>() called while <suitkaise-api>timing</suitkaise-api> is already in progress. "
            "This creates a nested <suitkaise-api>timing</suitkaise-api> frame.",
            UserWarning,
            stacklevel=2
        )
    
    # get or create session for current thread
    sess = self._get_or_create_session()
    started = sess.<suitkaise-api>start</suitkaise-api>()
    
    with self._lock:
        if self.original_start_time is None:
            self.original_start_time = started
    return started
```

1. Check if current thread already has an active timing frame
2. Warn if nesting (user might not intend this)
3. Get or create a `TimerSession` for current thread
4. Call `sess.<suitkaise-api>start</suitkaise-api>()` to push a new frame
5. Record `original_start_time` if this is the first ever start

Returns
`float`: Start timestamp from `perf_counter()`.

### `<suitkaise-api>stop</suitkaise-api>()`

Stop timing and record the measurement.

```python
def <suitkaise-api>stop</suitkaise-api>(self) -> float:
    sess = self._get_or_create_session()
    elapsed, paused_total = sess.<suitkaise-api>stop</suitkaise-api>()
    
    with self._lock:
        self.<suitkaise-api>times</suitkaise-api>.append(elapsed)
        self._paused_durations.append(paused_total)
        self._trim_to_max()
    return elapsed
```

1. Get session for current thread
2. Call `sess.<suitkaise-api>stop</suitkaise-api>()` to pop frame and get elapsed time
3. Under lock: append to `times` and `_paused_durations`
4. Trim to rolling window if configured

Returns
`float`: Elapsed time for this measurement.

Raises
`RuntimeError`: If timer was not started.

### `<suitkaise-api>discard</suitkaise-api>()`

Stop timing but do NOT record.

```python
def <suitkaise-api>discard</suitkaise-api>(self) -> float:
    sess = self._get_or_create_session()
    elapsed, _ = sess.<suitkaise-api>stop</suitkaise-api>()
    # intentionally NOT appending to times or _paused_durations
    return elapsed
```

1. Get session for current thread
2. Call `sess.<suitkaise-api>stop</suitkaise-api>()` to pop frame
3. Return elapsed time without recording

Returns
`float`: Elapsed time that was discarded.

### `<suitkaise-api>lap</suitkaise-api>()`

Record a lap time (stop + start in one call).

```python
def <suitkaise-api>lap</suitkaise-api>(self) -> float:
    sess = self._get_or_create_session()
    elapsed, paused_total = sess.<suitkaise-api>lap</suitkaise-api>()
    
    with self._lock:
        self.<suitkaise-api>times</suitkaise-api>.append(elapsed)
        self._paused_durations.append(paused_total)
        self._trim_to_max()
    return elapsed
```

1. Get session for current thread
2. Call `sess.<suitkaise-api>lap</suitkaise-api>()` which records elapsed and restarts frame
3. Under lock: append to lists and trim

Returns
`float`: Elapsed time for this lap.

### `<suitkaise-api>pause</suitkaise-api>()` / `<suitkaise-api>resume</suitkaise-api>()`

Pause and resume the current timing measurement.

```python
def <suitkaise-api>pause</suitkaise-api>(self) -> None:
    sess = self._get_or_create_session()
    sess.<suitkaise-api>pause</suitkaise-api>()

def <suitkaise-api>resume</suitkaise-api>(self) -> None:
    sess = self._get_or_create_session()
    sess.<suitkaise-api>resume</suitkaise-api>()
```

Delegates to session which tracks pause state in the current frame.

### `<suitkaise-api>add_time</suitkaise-api>()`

Manually add a timing measurement.

```python
def <suitkaise-api>add_time</suitkaise-api>(self, elapsed_time: float) -> None:
    with self._lock:
        self.<suitkaise-api>times</suitkaise-api>.append(elapsed_time)
        self._paused_durations.append(0.0)
        self._trim_to_max()
```

Directly appends to `times` with zero paused duration.

### `<suitkaise-api>set_max_times</suitkaise-api>()`

Set the rolling window size.

```python
def <suitkaise-api>set_max_times</suitkaise-api>(self, max_times: Optional[int]) -> None:
    if max_times is not None and max_times <= 0:
        raise ValueError("max_times must be a positive integer or None")
    
    with self._lock:
        self._max_times = max_times
        self._trim_to_max()

def _trim_to_max(self) -> None:
    if self._max_times is None:
        return
    excess = len(self.<suitkaise-api>times</suitkaise-api>) - self._max_times
    if excess <= 0:
        return
    del self.<suitkaise-api>times</suitkaise-api>[:excess]
    del self._paused_durations[:excess]
```

When `max_times` is set, oldest measurements are discarded to keep only the most recent N.

### `<suitkaise-api>reset</suitkaise-api>()`

Clear all timing measurements.

```python
def <suitkaise-api>reset</suitkaise-api>(self) -> None:
    with self._lock:
        self.<suitkaise-api>times</suitkaise-api>.clear()
        self.original_start_time = None
        self._sessions.clear()
        self._paused_durations.clear()
```

Resets all state including per-thread sessions.

### Statistics Properties

All statistics properties are computed live from `times` list under lock.

```python
@property
def <suitkaise-api>mean</suitkaise-api>(self) -> Optional[float]:
    with self._lock:
        return statistics.mean(self.<suitkaise-api>times</suitkaise-api>) if self.<suitkaise-api>times</suitkaise-api> else None

@property
def <suitkaise-api>stdev</suitkaise-api>(self) -> Optional[float]:
    with self._lock:
        if len(self.<suitkaise-api>times</suitkaise-api>) <= 1:
            return None
        return statistics.stdev(self.<suitkaise-api>times</suitkaise-api>)
```

**Available properties:**
- `num_times`, `most_recent`, `result`, `most_recent_index`
- `total_time`, `total_time_paused`
- `mean`, `median`, `min`, `max`
- `fastest_time`, `slowest_time`, `fastest_index`, `slowest_index`
- `stdev`, `variance`, `max_times`

### `<suitkaise-api>percentile</suitkaise-api>()`

Calculate any percentile using linear interpolation.

```python
def <suitkaise-api>percentile</suitkaise-api>(self, percent: float) -> Optional[float]:
    with self._lock:
        if not self.<suitkaise-api>times</suitkaise-api>:
            return None
        
        if not 0 <= percent <= 100:
            raise ValueError("Percentile must be between 0 and 100")
        
        sorted_times = sorted(self.<suitkaise-api>times</suitkaise-api>)
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
        if not self.<suitkaise-api>times</suitkaise-api>:
            return None
        return TimerStats(self.<suitkaise-api>times</suitkaise-api>, self.original_start_time, self._paused_durations)
```

Returns
A `TimerStats` object with copied data that won't change.

### Share Integration

`<suitkaise-api>Sktimer</suitkaise-api>` defines `_shared_meta` for use with `<suitkaise-api>suitkaise</suitkaise-api>.<suitkaise-api>processing</suitkaise-api>.<suitkaise-api>Share</suitkaise-api>`:

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

This metadata declares which attributes each method/property reads or writes, enabling the `<suitkaise-api>Share</suitkaise-api>` to coordinate synchronization.

## `TimerSession`

Per-thread timing session supporting nested frames.

```python
class TimerSession:
    def __init__(self, manager: <suitkaise-api>Sktimer</suitkaise-api>):
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

### `<suitkaise-api>start</suitkaise-api>()`

Push a new frame onto the stack.

```python
def <suitkaise-api>start</suitkaise-api>(self) -> float:
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

### `<suitkaise-api>stop</suitkaise-api>()`

Pop the top frame and return elapsed time.

```python
def <suitkaise-api>stop</suitkaise-api>(self) -> tuple[float, float]:
    with self._lock:
        frame = self._top()
        elapsed = self._elapsed_from_frame(frame)
        paused_total = self._paused_total_from_frame(frame)
        self._frames.pop()
        return elapsed, paused_total
```

### `<suitkaise-api>lap</suitkaise-api>()`

Record elapsed time and restart the frame.

```python
def <suitkaise-api>lap</suitkaise-api>(self) -> tuple[float, float]:
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

### `<suitkaise-api>pause</suitkaise-api>()` / `<suitkaise-api>resume</suitkaise-api>()`

```python
def <suitkaise-api>pause</suitkaise-api>(self) -> None:
    with self._lock:
        frame = self._top()
        if frame['paused']:
            warnings.warn("<suitkaise-api>Sktimer</suitkaise-api> is already paused.", UserWarning, stacklevel=2)
            return
        frame['paused'] = True
        frame['pause_started_at'] = self._now()

def <suitkaise-api>resume</suitkaise-api>(self) -> None:
    with self._lock:
        frame = self._top()
        if not frame['paused']:
            warnings.warn("<suitkaise-api>Sktimer</suitkaise-api> is not paused.", UserWarning, stacklevel=2)
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
        self.<suitkaise-api>times</suitkaise-api> = times.copy()  # copy for immutability
        
        self.original_start_time = original_start_time
        self.<suitkaise-api>num_times</suitkaise-api> = len(times)
        self.<suitkaise-api>most_recent</suitkaise-api> = times[-1] if times else None
        self.most_recent_index = len(times) - 1 if times else None
        self.<suitkaise-api>total_time</suitkaise-api> = sum(times) if times else None
        self.total_time_paused = sum(paused_durations) if paused_durations else None
        
        self.<suitkaise-api>mean</suitkaise-api> = statistics.mean(times) if times else None
        self.median = statistics.median(times) if times else None
        self.min = min(times) if times else None
        self.max = max(times) if times else None
        self.<suitkaise-api>stdev</suitkaise-api> = statistics.stdev(times) if len(times) > 1 else None
        self.<suitkaise-api>variance</suitkaise-api> = statistics.variance(times) if len(times) > 1 else None
        # ... etc
```

All values are computed once at construction time and stored as attributes.

### `<suitkaise-api>percentile</suitkaise-api>()`

Same algorithm as `<suitkaise-api>Sktimer</suitkaise-api>.<suitkaise-api>percentile</suitkaise-api>()` but operates on the frozen `times` copy.

## `<suitkaise-api>TimeThis</suitkaise-api>` Context Manager

Context manager wrapper around `<suitkaise-api>Sktimer</suitkaise-api>`.

```python
class <suitkaise-api>TimeThis</suitkaise-api>:
    def __init__(self, timer: Optional[<suitkaise-api>Sktimer</suitkaise-api>] = None, threshold: float = 0.0):
        self.<suitkaise-api>timer</suitkaise-api> = timer or <suitkaise-api>Sktimer(</suitkaise-api>)
        self.threshold = threshold

    def __enter__(self):
        self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
        return self.<suitkaise-api>timer</suitkaise-api>
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Get elapsed time without recording
        elapsed = self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()
        
        # Only record if above threshold
        if elapsed >= self.threshold:
            self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(elapsed)
```

### Flow

1. `__enter__`: Call `<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()`, return timer for `as` clause
2. User code executes
3. `__exit__`: Call `<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()` to get elapsed without recording
4. Only record via `<suitkaise-api>add_time</suitkaise-api>()` if above threshold

### Methods

Delegates to the underlying timer:

```python
def <suitkaise-api>pause</suitkaise-api>(self):
    self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>pause</suitkaise-api>()

def <suitkaise-api>resume</suitkaise-api>(self):
    self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>resume</suitkaise-api>()

def <suitkaise-api>lap</suitkaise-api>(self):
    self.<suitkaise-api>timer</suitkaise-api>.<suitkaise-api>lap</suitkaise-api>()
```

## `<suitkaise-api>timethis</suitkaise-api>` Decorator

Decorator that times function executions.

```python
def <suitkaise-api>timethis</suitkaise-api>(
    timer: Optional[<suitkaise-api>Sktimer</suitkaise-api>] = None,
    threshold: float = 0.0,
    max_times: Optional[int] = None,
) -> Callable:
```

### With Explicit Timer

```python
def decorator(func: Callable) -> Callable:
    if timer is not None:
        if max_times is not None:
            <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>set_max_times</suitkaise-api>(max_times)
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
        if not hasattr(<suitkaise-api>timethis</suitkaise-api>, '_global_timers'):
            setattr(<suitkaise-api>timethis</suitkaise-api>, '_global_timers', {})
            setattr(<suitkaise-api>timethis</suitkaise-api>, '_timers_lock', threading.RLock())
        
        lock = getattr(<suitkaise-api>timethis</suitkaise-api>, '_timers_lock')
        with lock:
            global_timers = getattr(<suitkaise-api>timethis</suitkaise-api>, '_global_timers')
            if timer_name not in global_timers:
                global_timers[timer_name] = <suitkaise-api>Sktimer(</suitkaise-api>max_times=max_times)
        
        wrapper = _timethis_decorator(global_timers[timer_name], threshold)(func)
        setattr(wrapper, 'timer', global_timers[timer_name])
    
    return wrapper
```

1. Extract module name from caller's frame
2. Build timer name from function's `__qualname__`
3. Get or create global timer (thread-safe with lock)
4. Attach timer to wrapped function as `.<suitkaise-api>timer</suitkaise-api>`

### Timer Naming Convention

- Module-level function `foo()` in `mymodule.py`: `mymodule_foo_timer`
- Class method `Bar.baz()` in `mymodule.py`: `mymodule_Bar_baz_timer`

### `_timethis_decorator()`

The actual timing wrapper:

```python
def _timethis_decorator(timer: <suitkaise-api>Sktimer</suitkaise-api>, threshold: float = 0.0):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # avoid nested timing frames on the same timer
            if <suitkaise-api>timer</suitkaise-api>._has_active_frame():
                start = perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed = perf_counter() - start
                    if elapsed >= threshold:
                        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(elapsed)
            else:
                <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>start</suitkaise-api>()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>discard</suitkaise-api>()
                    if elapsed >= threshold:
                        <suitkaise-api>timer</suitkaise-api>.<suitkaise-api>add_time</suitkaise-api>(elapsed)
        return wrapper
    return decorator
```

**Two paths:**
1. **Already timing**: Use `perf_counter()` directly to avoid nested frames
2. **Not timing**: Use `<suitkaise-api>start</suitkaise-api>()`/`<suitkaise-api>discard</suitkaise-api>()`/`<suitkaise-api>add_time</suitkaise-api>()` flow

Both paths only record if elapsed >= threshold.

## `<suitkaise-api>clear_global_timers</suitkaise-api>()`

Clear auto-created timers.

```python
def <suitkaise-api>clear_global_timers</suitkaise-api>() -> None:
    if hasattr(<suitkaise-api>timethis</suitkaise-api>, '_timers_lock') and hasattr(<suitkaise-api>timethis</suitkaise-api>, '_global_timers'):
        lock = getattr(<suitkaise-api>timethis</suitkaise-api>, '_timers_lock')
        with lock:
            timers = getattr(<suitkaise-api>timethis</suitkaise-api>, '_global_timers')
            timers.clear()
```

Thread-safe clearing of the global timer registry.

## Thread Safety

`<suitkaise-api>Sktimer</suitkaise-api>` is fully thread-safe:

1. **Manager-level lock** (`_lock`): Protects `times`, `_paused_durations`, `_sessions`
2. **Session-level lock**: Each `TimerSession` has its own lock for frame operations
3. **Global timer lock**: `<suitkaise-api>timethis</suitkaise-api>._timers_lock` protects auto-created timer registry

`threading.RLock` (reentrant lock) is used because operations may call each other.
"
