The first rendition of the Process class concept is very complicated.

I want it to be simpler and more intuitive.

Uses my Cerial module to handle data serialization and deserialization.

- User makes a class that inherits from Process
- user defines initial attributes in __init__(), as well as update the self.config subobject.

No more:
- config object
- complicated timing
- complicated configuration

Instead, all configuration is done by the user in the __init__() method using attributes.

- Process splits into 3 parts:

Process: untimed process that runs until it ends itself or is asked to rejoin

```python
# runs until it calls __onfinish__() itself or is asked to rejoin
class MyProcess(Process):
```

What remains:
- __preloop__(), __loop__(), __postloop__()
- respective error classes (PreloopError, MainLoopError, PostLoopError)

Setting up a process

```python
from suitkaise.process import Process

class MyProcess(Process):
    
    def __init__(self):
        self.counter = 0
    
    # called before every __loop__() iteration
    def __preloop__(self):
        print("Preloop")
        self.counter += 1
        

    # this is where the user does their core work
    # this code should NOT loop itself, the engine loops for you
    def __loop__(self):
        print("Loop")
        self.counter += 1
        
    # called after every __loop__() iteration
    def __postloop__(self):
        print("Postloop")
        self.counter += 1

        if self.counter >= 10:
            self.stop()

    # called when self.stop() is called or a limit (time or number of loops) is reached
    def __onfinish__(self):
        print("Onfinish")
        self.counter += 1

    # called after __onfinish__() to return data in a predictable package
    def __result__(self):
        return self.counter

    # called after a section if an error occurs in that section
    # for example: the system would raise a PreloopError that will raise the error it caught. that is what is stored in self.error. that way user can see where in loop error occurred and what the actual error was.
    def __error__(self):
        print(f"Error caught: {self.error}")
        return self.error
        
```

Automatic initialization (no `super().__init__()` needed)

When you inherit from `Process`, you don't need to call `super().__init__()`. The `Process` class uses Python's `__init_subclass__` to automatically wrap your `__init__` method and run the parent's initialization behind the scenes.

```python
# ✅ Just write your __init__ naturally
class MyProcess(Process):
    def __init__(self, data):
        self.data = data
        self.config.num_loops = 10

# ❌ No need for this
class MyProcess(Process):
    def __init__(self, data):
        super().__init__()  # Not required!
        self.data = data
```

This automatic initialization:
- Sets up internal process state (name, status, communication channels, etc.)
- Creates the `self.config` object with default values
- Lets your `__init__` override defaults by simply assigning to `self.config.*`
- Works for all subclasses, even if you inherit from your own Process subclass

How it works under the hood:

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
```

This means every class that inherits from `Process` (or a `Process` subclass) automatically gets the parent setup, with zero boilerplate from the user.


Process config options:

```python

# for regular Process objects
class MyProcess(Process):

    def __init__(self):

        # number of loops to run before calling __onfinish__()
        # if this threshold is reached, self.stop() is called
        self.config.num_loops = 10

        # time to run before calling __onfinish__()
        # if this threshold is reached, self.stop() is called
        self.config.join_in = 30.0

        # number of times to restart the process if it crashes before just calling __error__()
        self.config.lives = 10

        # timeout for __preloop__()
        # if this threshold is reached, self.error() is called
        self.config.timeouts.preloop = 30.0 

        # timeout for __loop__()
        # if this threshold is reached, self.error() is called
        self.config.timeouts.loop = 300.0 

        # timeout for __postloop__()
        # if this threshold is reached, self.error() is called
        self.config.timeouts.postloop = 60.0 

        # timeout for __onfinish__()
        # if this threshold is reached, process will be killed
        self.config.timeouts.onfinish = 60.0
```


Creating and rejoining a process

```python
from suitkaise.processing import Process

class MyProcess(Process):

    # ...

# create the process obj
process = MyProcess()

# start the process
# this automatically creates a new process for you using your Process object
process.start()

# wait for the process to finish (blocks until done)
# will raise an error if called from inside the process
process.wait()

# stop the process
# if called from outside the process, this works by sending the stop signal. process checks for stop signal between each part of the loop.
process.stop()

# kill the process without finishing gracefully
# this just kills the process without finishing current and calling __onfinish__()
process.kill()

# get results
try:
    process_result = process.result()
except Exception as e:
    print(f"Error: {e}")

```


Running multiple processes

```python
class Worker(Process):
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.config.num_loops = 5
    
    def __loop__(self):
        # do work
        pass
    
    def __result__(self):
        return f"Worker {self.worker_id} done"

# create multiple processes
processes = [Worker(i) for i in range(5)]

# start all
for p in processes:
    p.start()

# wait for all to finish
for p in processes:
    p.wait()

# collect results
results = [p.result() for p in processes]
```

The wait loop iterates in order, but waiting on an already-finished process returns immediately. So if process 3 finishes before process 0, you'll block on process 0, and when you reach process 3 it returns instantly.

Total wall-clock time = duration of the slowest process (not the sum of all).

```
Timeline example:

Process 0: ████████████░░░░░░░░░░ (finishes at 12s)
Process 1: ████░░░░░░░░░░░░░░░░░░ (finishes at 4s)  
Process 2: ██████████████████████ (finishes at 22s) <- slowest
Process 3: ██████░░░░░░░░░░░░░░░░ (finishes at 6s)
Process 4: ████████░░░░░░░░░░░░░░ (finishes at 8s)

Wait loop:
  p[0].wait() -> blocks 12s
  p[1].wait() -> already done, instant
  p[2].wait() -> blocks 10 more seconds
  p[3].wait() -> already done, instant
  p[4].wait() -> already done, instant

Total time: 22 seconds
```


How to time the process to record statistics

```python
from suitkaise.processing import Process

class MyProcess(Process):
    
    def __init__(self):

        self.custom_timer = sktime.Timer()

        # ...

# automatically use section timers

    @processing.timethis()
    def __preloop__(self):

    @processing.timethis()
    def __loop__(self):

    @processing.timethis()
    def __postloop__(self):

    @processing.timethis()
    def __onfinish__(self):


# manually use custom timers using sktime
from suitkaise import sktime

    def __preloop__(self):
        with sktime.TimeThis(self.custom_timer) as timer:


    def __loop__(self):
        with sktime.TimeThis(self.custom_timer) as timer:


# accessing the times

# a timer is added to timers for every @processing.timethis() decorated function it knows what timer to use.

# each of these acts just like an sktime.Timer instance. you can use all the same methods on it.
self.timers.preloop
self.timers.loop
self.timers.postloop
self.timers.onfinish

# this is a special timer that adds up the most recent time from existing self.timers.preloop, loop, and postloop.
# if one of the timers is not used, the full_loop timer will not use it either.
self.timers.full_loop

# accessing custom timer is the same as accessing any other sktime.Timer instance.

# get the most recent time from the custom timer
self.custom_timer.most_recent
```


Other statistics:

```python
# get the current runthrough of the loop
self.current_lap
```


---

## Internal Architecture

### Integration with other suitkaise modules

- **cerial**: Serializes the Process object to send to a subprocess. Handles complex objects like locks, loggers, timers, etc. that might be in user's process object.
- **sktime**: Powers the `@processing.timethis()` decorator and `self.timers.*` statistics.

### Subprocess mechanics

Processing uses Python's `multiprocessing` module. When `process.start()` is called:

1. The Process object is serialized with cerial
2. A new subprocess is spawned
3. The subprocess deserializes and runs the engine loop
4. Results are serialized back to the parent process

Threading support will be added later as a separate module.

### Communication between parent and child

Uses a hybrid approach (Option C) for efficiency:

- **`multiprocessing.Event`** for stop signal - nearly zero-cost to check
- **`multiprocessing.Queue`** for results/errors - flexible serialized data

**Why this approach:**

| Approach | Fast stop check | Send results | Complexity |
|----------|-----------------|--------------|------------|
| Event only | ✅ | ❌ (need separate mechanism) | Low |
| Queue only | ❌ (must poll with get_nowait) | ✅ | Medium |
| **Hybrid (chosen)** | ✅ | ✅ | Low |

The Event is a shared memory flag - `is_set()` is essentially just reading a boolean. The Queue handles the complexity of serializing result objects back to the parent.

**Communication primitives:**

```python
self._stop_event = multiprocessing.Event()   # Parent → Child: stop signal
self._result_queue = multiprocessing.Queue() # Child → Parent: result or error
```

**Flow diagram:**

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
process.result()
  ├─► _result_queue.get()
  ├─► deserialize
  ├─► if error, raise it
  └─► return result
```

**Future extensibility:**

If we later need parent → child commands (pause/resume, dynamic config updates), we can add a `_cmd_queue` without changing the existing primitives. The code is structured to allow this:

```python
# Future addition (not in v1):
# self._cmd_queue = multiprocessing.Queue()  # Parent → Child: commands
```

### The engine

The engine is the code that runs in the child process. It orchestrates the lifecycle:

- User defines *what* happens (`__preloop__`, `__loop__`, `__postloop__`, etc.)
- Engine defines *when* and *how* those things get called

The engine handles:
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

## Timeout Implementation

### The challenge

How do you interrupt arbitrary Python code that's blocking (infinite loop, stuck network call, etc.)?

| Approach | Can interrupt blocking code? | Cross-platform? | Clean termination? |
|----------|------------------------------|-----------------|-------------------|
| **Signal (SIGALRM)** | Yes | Unix only | Yes |
| **Timer thread** | No (zombie continues) | Yes | No |
| **Subprocess per section** | Yes | Yes | Yes (but heavy overhead) |

### Our approach: Platform-specific with fallback

**On Unix/Linux/macOS**: Use `signal.SIGALRM`
- Signals are handled at the OS level
- Can interrupt most blocking operations (syscalls, sleep, etc.)
- Clean and reliable

**On Windows**: Fall back to timer thread
- Windows doesn't have `SIGALRM`
- Timer thread detects timeout but can't forcefully interrupt blocking code
- The "zombie" thread continues running until subprocess terminates

```python
import platform

if platform.system() != 'Windows':
    _run_with_timeout = _signal_based_timeout
else:
    _run_with_timeout = _thread_based_timeout
```

### Signal-based timeout (Unix)

```python
import signal

def _signal_based_timeout(func, timeout):
    if timeout is None:
        return func()
    
    def handler(signum, frame):
        raise TimeoutError(f"Section timed out after {timeout}s")
    
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(int(timeout))
    try:
        return func()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
```

### Timer thread fallback (Windows)

```python
import threading

def _thread_based_timeout(func, timeout):
    if timeout is None:
        return func()
    
    result = [None]
    exception = [None]
    
    def wrapper():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=wrapper)
    thread.start()
    thread.join(timeout=timeout)
    
    if thread.is_alive():
        # Thread still running - can't kill it, but we know timeout occurred
        raise TimeoutError(f"Section timed out after {timeout}s")
    
    if exception[0]:
        raise exception[0]
    return result[0]
```

### Windows limitation

On Windows, if user code has an infinite loop or long-blocking call, the timeout will fire but the code keeps running in a "zombie" thread. This is mitigated because:

1. We're already in a subprocess - zombie dies when subprocess terminates
2. On retry (lives system), we deserialize fresh original state, so zombie modifying old state doesn't affect new attempt
3. Most code isn't truly infinite - timeouts work for "slow but finite" operations


---

## Error Handling and Lives System

### Error wrapping

When an error occurs in a lifecycle method, it's wrapped in a section-specific error:

- `PreloopError` wraps errors from `__preloop__()`
- `MainLoopError` wraps errors from `__loop__()`
- `PostLoopError` wraps errors from `__postloop__()`

This lets users see both *where* the error occurred and *what* the actual error was:

```
PreloopError: RuntimeError: Connection refused
```

### Lives and retry flow

```
Error occurs in section
        │
        ▼
Wrap in *LoopError
        │
        ▼
Lives remaining? ─── Yes ──► Decrement lives
        │                         │
        No                        ▼
        │                   Deserialize original state
        ▼                   (fresh copy, lives decremented)
Set self.error = wrapped error    │
        │                         ▼
        ▼                   Retry from beginning
Call __error__()
        │
        ▼
Return error result to parent
        │
        ▼
Parent's result() raises the error
```

Key points:
- On retry, we deserialize the *original* process state (saved at start)
- Only `lives` is decremented, everything else is fresh
- This ensures retries start clean, not with corrupted state

### __error__() behavior

- Called when no lives remaining and an error occurred
- Receives error via `self.error` attribute
- Default behavior: returns the error
- User can override to add logging, cleanup, custom error transformation
- Whatever `__error__()` returns is sent back like a result

### result() behavior

- Blocks until process finishes (or call `wait()` first)
- Checks if result contains an error
- If error, raises it
- If not, returns the result (default: None if no `__result__` defined)


---

## Config Structure

Nested dataclasses with generous defaults:

```python
from dataclasses import dataclass, field

@dataclass
class TimeoutConfig:
    preloop: float | None = 30.0
    loop: float | None = 300.0
    postloop: float | None = 60.0
    onfinish: float | None = 60.0

@dataclass
class ProcessConfig:
    num_loops: int | None = None       # None = infinite until stopped
    join_in: float | None = None       # None = no time limit
    lives: int = 1                     # 1 = no retries (fail on first error)
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
```

Created automatically by `Process._setup()` before user's `__init__` runs.


---

## Timers Structure

`self.timers` is only created if at least one `@processing.timethis()` decorator exists.

```python
class ProcessTimers:
    def __init__(self):
        self.preloop: Timer | None = None
        self.loop: Timer | None = None
        self.postloop: Timer | None = None
        self.onfinish: Timer | None = None
        self.full_loop: Timer = Timer()  # always exists once timers is created
    
    def _update_full_loop(self):
        """Called by engine after each complete loop iteration"""
        total = 0.0
        for timer in [self.preloop, self.loop, self.postloop]:
            if timer is not None and timer.num_times > 0:
                total += timer.most_recent
        if total > 0:
            self.full_loop.add_time(total)
```

The `@processing.timethis()` decorator:
1. Checks if `self.timers` exists, creates `ProcessTimers` if not
2. Determines which timer slot based on method name (`__preloop__` → `self.timers.preloop`)
3. Creates a `Timer` in that slot if it doesn't exist
4. Wraps the method to time each call


---

## File Structure

```
suitkaise/processing/
├── __init__.py              # public exports
├── api.py                   # Process base class, timethis decorator
└── _int/
    ├── __init__.py
    ├── base_process.py      # Process class implementation
    ├── config.py            # ProcessConfig, TimeoutConfig dataclasses
    ├── timers.py            # ProcessTimers container
    ├── errors.py            # PreloopError, MainLoopError, PostLoopError
    ├── engine.py            # Loop runner that executes in subprocess
    └── timeout.py           # Platform-specific timeout implementations
```






