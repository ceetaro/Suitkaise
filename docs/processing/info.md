# `processing` Technical Information

This document covers the internal architecture and implementation details of the `processing` module. For user-facing documentation, see `concept.md`.

## Table of Contents

1. [Module Integration](#1-module-integration)
2. [Subprocess Mechanics](#2-subprocess-mechanics)
3. [Communication Architecture](#3-communication-architecture)
4. [The Engine](#4-the-engine)
5. [Timeout Implementation](#5-timeout-implementation)
6. [Error Handling Internals](#6-error-handling-internals)
7. [Lives System Flow](#7-lives-system-flow)
8. [Config Structure](#8-config-structure)
9. [Timers Structure](#9-timers-structure)
10. [File Structure](#10-file-structure)

---

## 1. Module Integration

The `processing` module integrates with other `suitkaise` modules:

- **cerial**: Serializes the `Process` object to send to a subprocess. Handles complex objects like locks, loggers, timers, custom classes, etc.
- **sktime**: Powers the `@timesection()` decorator and `self.timers.*` statistics.
- **circuit** (optional): Can be used inside lifecycle methods for failure tracking within loops.

---

## 2. Subprocess Mechanics

Processing uses Python's `multiprocessing` module. When `process.start()` is called:

1. The `Process` object is serialized with `cerial`
2. Original serialized state is saved (for retries)
3. A new subprocess is spawned
4. The subprocess deserializes and runs the engine loop
5. Results are serialized back to the parent process

### Why `multiprocessing` over `threading`?

- True parallelism (bypasses GIL)
- Process isolation (errors don't corrupt parent)
- Clean termination (can `kill()` subprocess)

Threading support may be added later as a separate module.

---

## 3. Communication Architecture

Uses a **hybrid approach** for efficiency:

- **`multiprocessing.Event`** for stop signal - nearly zero-cost to check
- **`multiprocessing.Queue`** for results/errors - flexible serialized data

### Why this approach?

| Approach | Fast stop check | Send results | Complexity |
|----------|-----------------|--------------|------------|
| Event only | ✅ | ❌ (need separate mechanism) | Low |
| Queue only | ❌ (must poll with `get_nowait`) | ✅ | Medium |
| **Hybrid (chosen)** | ✅ | ✅ | Low |

The Event is a shared memory flag - `is_set()` is essentially just reading a boolean. The Queue handles the complexity of serializing result objects back to the parent.

### Communication Primitives

```python
self._stop_event = multiprocessing.Event()   # Parent → Child: stop signal
self._result_queue = multiprocessing.Queue() # Child → Parent: result or error
```

### Flow Diagram

```
PARENT PROCESS                          CHILD PROCESS
─────────────────                       ─────────────────
process = MyProcess()
process.start()
  │
  ├─► create _stop_event (Event)
  ├─► create _result_queue (Queue)
  ├─► serialize process with cerial
  ├─► save original state for retries
  ├─► spawn subprocess ──────────────────►  deserialize process
  │                                         │
  │                                         ├─► run engine loop:
  │                                         │     check _stop_event
  │                                         │     __preloop__()
  │                                         │     check _stop_event
  │                                         │     __loop__()
  │                                         │     check _stop_event
  │                                         │     __postloop__()
  │                                         │     increment lap
  │                                         │     update full_loop timer
  │                                         │     (repeat until done)
  │                                         │
process.stop()                              │
  ├─► _stop_event.set() ─────────────────►  │ (sees signal between sections)
  │                                         ├─► __onfinish__()
  │                                         ├─► result = __result__()
  │                                         ├─► serialize result
  │                                         └─► _result_queue.put(result)
  │                                         
process.wait()                              
  ├─► subprocess.join()                     
  │
process.result
  ├─► _result_queue.get()
  ├─► deserialize
  ├─► if error, raise it
  └─► return result
```

### Future Extensibility

If we later need parent → child commands (pause/resume, dynamic config updates), we can add a `_cmd_queue` without changing the existing primitives:

```python
# Future addition (not in v1):
# self._cmd_queue = multiprocessing.Queue()  # Parent → Child: commands
```

---

## 4. The Engine

The engine is the code that runs in the child process. It orchestrates the lifecycle:

- **User defines** *what* happens (`__preloop__`, `__loop__`, `__postloop__`, etc.)
- **Engine defines** *when* and *how* those things get called

### Engine Responsibilities

- Calling lifecycle methods in order
- Checking stop signals between sections
- Enforcing timeouts on each section
- Managing the lives/retry system
- Tracking lap count and timers
- Sending results or errors back to parent

### stop() vs kill()

- `stop()` - Sets the stop event. Process finishes current section, runs `__onfinish__`, sends result.
- `kill()` - Calls `subprocess.terminate()` immediately. No cleanup, no result, abandoned.

---

## 5. Timeout Implementation

### The Challenge

How do you interrupt arbitrary Python code that's blocking (infinite loop, stuck network call, etc.)?

| Approach | Can interrupt blocking code? | Cross-platform? | Clean termination? |
|----------|------------------------------|-----------------|-------------------|
| **Signal (SIGALRM)** | Yes | Unix only | Yes |
| **Timer thread** | No (zombie continues) | Yes | No |
| **Subprocess per section** | Yes | Yes | Yes (but heavy overhead) |

### Our Approach: Platform-specific with Fallback

```python
import platform

if platform.system() != 'Windows':
    run_with_timeout = _signal_based_timeout
else:
    run_with_timeout = _thread_based_timeout
```

### Signal-based Timeout (Unix/Linux/macOS)

- Signals are handled at the OS level
- Can interrupt most blocking operations (syscalls, sleep, etc.)
- Clean and reliable

```python
import signal

def _signal_based_timeout(func, timeout, section_name, current_lap):
    if timeout is None:
        return func()
    
    def handler(signum, frame):
        raise TimeoutError(section_name, timeout, current_lap)
    
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(int(timeout) + 1)  # Round up for sub-second timeouts
    try:
        return func()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
```

### Timer Thread Fallback (Windows)

- Windows doesn't have `SIGALRM`
- Timer thread detects timeout but can't forcefully interrupt blocking code
- The "zombie" thread continues running until subprocess terminates

```python
import threading

def _thread_based_timeout(func, timeout, section_name, current_lap):
    if timeout is None:
        return func()
    
    result = [None]
    exception = [None]
    completed = threading.Event()
    
    def wrapper():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
        finally:
            completed.set()
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    
    finished = completed.wait(timeout=timeout)
    
    if not finished:
        raise TimeoutError(section_name, timeout, current_lap)
    
    if exception[0]:
        raise exception[0]
    return result[0]
```

### Windows Limitation Mitigation

On Windows, if user code has an infinite loop or long-blocking call, the timeout will fire but the code keeps running in a "zombie" thread. This is mitigated because:

1. We're already in a subprocess - zombie dies when subprocess terminates
2. On retry (lives system), we deserialize fresh original state, so zombie modifying old state doesn't affect new attempt
3. Most code isn't truly infinite - timeouts work for "slow but finite" operations

---

## 6. Error Handling Internals

### Error Wrapping

When an error occurs in a lifecycle method, it's wrapped in a section-specific error class:

| Error Class | Source Method | Attributes |
|-------------|---------------|------------|
| `PreloopError` | `__preloop__()` | `current_lap`, `original_error` |
| `MainLoopError` | `__loop__()` | `current_lap`, `original_error` |
| `PostLoopError` | `__postloop__()` | `current_lap`, `original_error` |
| `OnFinishError` | `__onfinish__()` | `current_lap`, `original_error` |
| `ResultError` | `__result__()` | `current_lap`, `original_error` |
| `TimeoutError` | Any section | `section`, `timeout`, `current_lap` |

### Error Class Structure

```python
class MainLoopError(Exception):
    def __init__(self, current_lap: int, original_error: Exception | None = None):
        self.current_lap = current_lap
        self.original_error = original_error  # Stored for serialization
        super().__init__(f"Error in __loop__ on lap {current_lap}")
```

The `original_error` attribute is stored explicitly because Python's `__cause__` (from `raise ... from e`) doesn't survive `cerial` serialization.

---

## 7. Lives System Flow

```
Error occurs in section
        │
        ▼
Wrap in *LoopError
        │
        ▼
Lives remaining > 1? ─── Yes ──► Decrement lives
        │                              │
        No                             ▼
        │                   Deserialize original state
        ▼                   (fresh copy, lives decremented)
Set self.error = wrapped error         │
        │                              ▼
        ▼                   Retry from beginning
Call __error__()
        │
        ▼
Serialize __error__() return value
        │
        ▼
Send to parent via queue
        │
        ▼
Parent's .result raises the error
```

### Key Implementation Details

- On retry, we deserialize the *original* process state (saved at `start()`)
- Only `lives` is decremented, everything else is fresh
- This ensures retries start clean, not with corrupted state
- `__error__()` return value is sent back like a normal result

---

## 8. Config Structure

Nested dataclasses with generous defaults:

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class TimeoutConfig:
    preloop: Optional[float] = 30.0    # 30 seconds
    loop: Optional[float] = 300.0       # 5 minutes
    postloop: Optional[float] = 60.0    # 1 minute
    onfinish: Optional[float] = 60.0    # 1 minute

@dataclass
class ProcessConfig:
    num_loops: Optional[int] = None     # None = infinite until stopped
    join_in: Optional[float] = None     # None = no time limit
    lives: int = 1                      # 1 = no retries (fail on first error)
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
```

Created automatically by `Process._setup()` before user's `__init__` runs.

---

## 9. Timers Structure

`self.timers` is only created if at least one `@timesection()` decorator exists.

```python
from typing import Optional
from suitkaise.sktime import Timer

class ProcessTimers:
    def __init__(self):
        self.preloop: Optional[Timer] = None
        self.loop: Optional[Timer] = None
        self.postloop: Optional[Timer] = None
        self.onfinish: Optional[Timer] = None
        self.full_loop: Timer = Timer()  # Always exists once timers is created
    
    def _update_full_loop(self):
        """Called by engine after each complete loop iteration."""
        total = 0.0
        for timer in [self.preloop, self.loop, self.postloop]:
            if timer is not None and timer.num_times > 0:
                total += timer.most_recent
        if total > 0:
            self.full_loop.add_time(total)
```

### How `@timesection()` Works

1. Checks if `self.timers` exists, creates `ProcessTimers` if not
2. Determines which timer slot based on method name (`__preloop__` → `self.timers.preloop`)
3. Creates a `Timer` in that slot if it doesn't exist
4. Wraps the method to time each call

---

## 10. File Structure

```
suitkaise/processing/
├── __init__.py              # Public exports: Process, timesection
├── api.py                   # Process class, timesection decorator (re-exports)
└── _int/
    ├── __init__.py          # Internal imports
    ├── process_class.py     # Process class implementation
    ├── config.py            # ProcessConfig, TimeoutConfig dataclasses
    ├── timers.py            # ProcessTimers container
    ├── errors.py            # PreloopError, MainLoopError, etc.
    ├── engine.py            # Loop runner that executes in subprocess
    └── timeout.py           # Platform-specific timeout implementations
```

### Module Responsibilities

| File | Responsibility |
|------|----------------|
| `process_class.py` | `Process` base class, `__init_subclass__`, control methods, `__serialize__`/`__deserialize__` |
| `config.py` | `ProcessConfig` and `TimeoutConfig` dataclasses |
| `timers.py` | `ProcessTimers` container with `full_loop` aggregation |
| `errors.py` | All custom exception classes with `original_error` storage |
| `engine.py` | `_engine_main` function that runs lifecycle in subprocess |
| `timeout.py` | `run_with_timeout` with platform detection |

---

## Auto-Initialization Internals

The `Process` class uses `__init_subclass__` to automatically wrap subclass `__init__` methods:

```python
class Process:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # Wrap the child's __init__ to auto-call parent setup
        if '__init__' in cls.__dict__:
            original_init = cls.__dict__['__init__']
            
            def wrapped_init(self, *args, **kwargs):
                Process._setup(self)  # Parent initialization
                original_init(self, *args, **kwargs)  # User's __init__
            
            cls.__init__ = wrapped_init
        else:
            # No custom __init__, still need setup
            def default_init(self, *args, **kwargs):
                Process._setup(self)
            
            cls.__init__ = default_init
```

This means:
- Every class that inherits from `Process` automatically gets parent setup
- User never needs to call `super().__init__()`
- Works for all subclasses, even nested inheritance

---

## Serialization Internals

The `Process` class implements custom `__serialize__` and `__deserialize__` methods for `cerial`:

```python
_LIFECYCLE_METHODS = (
    '__preloop__', '__loop__', '__postloop__',
    '__onfinish__', '__result__', '__error__'
)

def __serialize__(self) -> dict:
    """Capture instance state and lifecycle methods for cerial."""
    # Get user-defined lifecycle methods (not base class defaults)
    methods = {}
    for name in self._LIFECYCLE_METHODS:
        method = getattr(self.__class__, name, None)
        base_method = getattr(Process, name, None)
        if method is not None and method is not base_method:
            methods[name] = getattr(self, name).__func__
    
    return {
        '__dict__': self.__dict__.copy(),
        '__class_name__': self.__class__.__name__,
        '__methods__': methods,
    }

@classmethod
def __deserialize__(cls, state: dict) -> 'Process':
    """Recreate process from serialized state."""
    # Dynamically create the subclass with captured methods
    new_class = type(
        state['__class_name__'],
        (Process,),
        state['__methods__']
    )
    
    # Create instance without calling __init__
    instance = object.__new__(new_class)
    instance.__dict__.update(state['__dict__'])
    
    return instance
```

This custom serialization is necessary because:
1. `cerial`'s default class handler skips dunder methods
2. User-defined lifecycle methods must be preserved
3. Locally-defined classes (inside functions/tests) need special handling
