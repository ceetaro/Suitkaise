# How `processing` works

`processing` is built around subprocess execution with several key components.

## Architecture Overview

The `processing` module is built around subprocess execution with several key components:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              Parent Process                                │
│                                                                            │
│  ┌──────────────┐   ┌─────────────┐   ┌─────────────┐   ┌───────────────┐  │
│  │  Skprocess   │   │    Pool     │   │    Share    │   │     Pipe      │  │
│  │  (instance)  │   │  (workers)  │   │(coordinator)│   │(anchor/point) │  │
│  └──────┬───────┘   └──────┬──────┘   └──────┬──────┘   └───────┬───────┘  │
│         │                  │                 │                  │          │
│         │  cucumber        │  cucumber       │  manager         │  pickle  │
│         │  serialize       │  serialize      │  proxies         │  handles │
│         ▼                  ▼                 ▼                  ▼          │
└─────────┼──────────────────┼─────────────────┼──────────────────┼──────────┘
          │                  │                 │                  │
          │                  │                 │                  │
┌─────────┼──────────────────┼─────────────────┼──────────────────┼──────────┐
│         ▼                  ▼                 ▼                  ▼          │
│  ┌──────────────┐   ┌─────────────┐   ┌─────────────┐   ┌───────────────┐  │
│  │   Engine     │   │   Worker    │   │ Coordinator │   │    Point      │  │
│  │  (lifecycle) │   │  (inline)   │   │  (process)  │   │  (endpoint)   │  │
│  └──────────────┘   └─────────────┘   └─────────────┘   └───────────────┘  │
│                                                                            │
│                           Subprocess(es)                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## `Skprocess`

### Class Hierarchy and Initialization

When you define a subclass of `Skprocess`:

```python
class MyProcess(Skprocess):
    def __init__(self):
        self.counter = 0
```

The `__init_subclass__` hook runs automatically when your class is defined.
What happens when you define a Skprocess subclass
1. Python calls `__init_subclass__` on the parent class (`Skprocess`)
2. Skprocess wraps your `__init__` method to call `_setup()` first
3. Skprocess creates `__serialize__` and `__deserialize__` methods for `cucumber` to use
4. These serialization methods capture your class's lifecycle methods (`__run__`, etc.)

```python
# what happens under the hood
def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    
    # wrap __init__ if defined
    if '__init__' in cls.__dict__:
        original_init = cls.__dict__['__init__']
        
        def wrapped_init(self, *args, **kwargs):
            Skprocess._setup(self)       # parent setup first
            original_init(self, *args, **kwargs)  # then user's __init__
        
        cls.__init__ = wrapped_init
    
    # set up serialization methods
    cls.__serialize__ = make_serialize(user_serialize)
    cls.__deserialize__ = make_deserialize(user_deserialize)
```

1. When `class MyProcess(Skprocess)` is parsed, Python triggers `Skprocess.__init_subclass__`
2. Your original `__init__` is saved and replaced with a wrapper
3. The wrapper ensures `_setup()` runs before your code, initializing all internal state
4. Custom `__serialize__`/`__deserialize__` methods are generated that know how to capture your specific lifecycle methods

### Internal State (`_setup`)

`Skprocess._setup()` initializes all internal state before your `__init__` runs.

What `_setup()` creates
1. **Configuration** - `process_config` holds `runs`, `join_in`, `lives`, and `timeouts`
2. **Timing** - `timers` container (created lazily when first needed)
3. **Runtime tracking** - `_current_run` counter and `_start_time` timestamp
4. **Error state** - `error` attribute for `__error__` to access
5. **Communication queues** - `_tell_queue` (parent→child) and `_listen_queue` (child→parent)
6. **Process handle** - `_subprocess` holds the `multiprocessing.Process` object
7. **Result storage** - `_result` and `_has_result` for retrieving the final value
8. **TimedMethod wrappers** - Wraps lifecycle methods so `process.__run__.timer` works

```python
def _setup(instance):
    # configuration with defaults
    instance.process_config = ProcessConfig()
    
    # timers container (created when needed)
    instance.timers = None
    
    # runtime state
    instance._current_run = 0
    instance._start_time = None
    
    # error state (set when error occurs)
    instance.error = None
    
    # communication primitives (created on start)
    instance._stop_event = None
    instance._result_queue = None
    instance._tell_queue = None      # Parent → Child
    instance._listen_queue = None    # Child → Parent
    
    # subprocess handle
    instance._subprocess = None
    
    # result storage
    instance._result = None
    instance._has_result = False
    
    # set up TimedMethod wrappers
    Skprocess._setup_timed_methods(instance)
```

### TimedMethod Wrappers

Each lifecycle method is wrapped in a `TimedMethod` to enable timer access.

Why wrap lifecycle methods?
1. Allow `process.__run__.timer` syntax to get the timer for `__run__`
2. Keep the method callable as normal (`process.__run__()`)
3. Provide a uniform interface for the engine to access the underlying method

What `TimedMethod` does
1. Stores reference to the original method
2. Stores reference to the process (for timer access)
3. Stores the timer name (e.g., `"run"` for `__run__`)
4. On call, delegates to the original method
5. On `.timer` access, looks up the `Sktimer` from `process.timers`

```python
class TimedMethod:
    def __init__(self, method, process, timer_name):
        self._method = method
        self._process = process
        self._timer_name = timer_name
    
    def __call__(self, *args, **kwargs):
        return self._method(*args, **kwargs)
    
    @property
    def timer(self):
        # returns the Sktimer for this method
        if self._process.timers is None:
            return None
        return getattr(self._process.timers, self._timer_name, None)
```

This enables the `process.__run__.timer` access pattern:

```python
process.run()
print(process.__run__.timer.elapsed)  # Get timing for __run__ method
print(process.__prerun__.timer.elapsed)  # Get timing for __prerun__ method
```

### Serialization for Subprocess Transfer

When `start()` is called, the entire `Skprocess` object must be transferred to the subprocess. This uses `cucumber` serialization.

Serialization
1. Extract all instance attributes (except `TimedMethod` wrappers which aren't serializable)
2. Capture the class name for reconstruction
3. Extract all lifecycle method definitions (`__run__`, `__prerun__`, etc.) as actual function objects
4. Package into a dict that `cucumber` can serialize

```python
def __serialize__(self):
    return {
        'instance_dict': {k: v for k, v in self.__dict__.items() 
                          if not isinstance(v, TimedMethod)},
        'class_name': cls.__name__,
        'lifecycle_methods': {
            name: cls.__dict__[name] 
            for name in ['__prerun__', '__run__', '__postrun__', 
                        '__onfinish__', '__result__', '__error__']
            if name in cls.__dict__
        },
        'class_attrs': {...},
    }
```

Deserialization
1. Dynamically recreate the class using `type()` with the saved lifecycle methods
2. Create an instance using `object.__new__()` to skip `__init__` (state already captured)
3. Restore all instance attributes from the serialized dict
4. Re-wrap lifecycle methods with `TimedMethod` for timer access
5. If `@autoreconnect` was used, call `reconnect_all()` to restore live connections

```python
@staticmethod
def __deserialize__(state):
    # rebuild class with lifecycle methods
    new_class = type(
        state['class_name'],
        (Skprocess,),
        state['lifecycle_methods'] | state['class_attrs']
    )
    
    # create instance without calling __init__
    obj = object.__new__(new_class)
    obj.__dict__.update(state['instance_dict'])
    
    # set up timed methods
    Skprocess._setup_timed_methods(obj)
    
    # handle @autoreconnect
    if getattr(new_class, '_auto_reconnect_enabled', False):
        obj = reconnect_all(obj, **reconnect_kwargs)
    
    return obj
```

### `start()` flow

What happens when you call `process.start()`
1. **Initialize timers** - Create `ProcessTimers` if not already present
2. **Serialize the process** - Convert entire object to bytes using `cucumber`
3. **Create communication primitives**:
   - `_stop_event` - Signal to tell subprocess to stop
   - `_result_queue` - Subprocess sends final result/error here
   - `_tell_queue` - Parent sends messages to child
   - `_listen_queue` - Child sends messages to parent
4. **Record start time** - For `join_in` time limit checking
5. **Spawn subprocess** - Create `multiprocessing.Process` targeting the engine
6. **Start the subprocess** - Control returns immediately to parent

```python
def start(self):
    from .engine import _engine_main
    from suitkaise import cucumber
    
    # ensure timers exist
    if self.timers is None:
        self.timers = ProcessTimers()
    
    # serialize current state
    serialized = cucumber.serialize(self)
    
    # create communication primitives
    self._stop_event = multiprocessing.Event()
    self._result_queue = multiprocessing.Queue()
    self._tell_queue = multiprocessing.Queue()   # Parent → Child
    self._listen_queue = multiprocessing.Queue() # Child → Parent
    
    # record start time
    from suitkaise import timing
    self._start_time = timing.time()
    
    # spawn subprocess
    self._subprocess = multiprocessing.Process(
        target=_engine_main,
        args=(serialized, self._stop_event, self._result_queue,
              serialized, self._tell_queue, self._listen_queue)
    )
    self._subprocess.start()
```

After `start()` returns:
- Parent process continues executing (non-blocking)
- Subprocess begins deserializing and running the engine
- Communication queues are active between both processes

---

## Engine (Subprocess Execution)

The engine runs in the subprocess and orchestrates the lifecycle.

### Main Loop

Engine startup sequence
1. **Deserialize the process** - Reconstruct the `Skprocess` object from bytes
2. **Initialize timers** - Ensure `ProcessTimers` exists
3. **Track lives** - Copy `lives` from config for retry tracking
4. **Swap communication queues** - See "Queue Swapping" below
5. **Record subprocess start time** - For `join_in` tracking

Main execution loop
1. **Check continuation** - Should we keep running? (runs limit, join_in, stop signal)
2. **Run `__prerun__`** - Timed, with configured timeout
3. **Check stop** - Exit early if stop signal received
4. **Run `__run__`** - Your main work, timed with configured timeout
5. **Check stop** - Exit early if stop signal received
6. **Run `__postrun__`** - Cleanup after each run, timed
7. **Increment run counter** - Track how many iterations completed
8. **Update full_run timer** - Aggregate timing for this iteration
9. **Loop back to step 1** - Until continuation check fails

On success (loop exits normally)
- Run finish sequence (`__onfinish__` → `__result__`)
- Send result to parent via queue

On failure (exception in lifecycle method)
- Decrement `lives_remaining`
- If lives left: retry from step 1
- If no lives: run `__error__`, send error to parent

```python
def _engine_main_inner(serialized_process, stop_event, result_queue, 
                       original_state, tell_queue, listen_queue):
    # deserialize the process
    process = cucumber.deserialize(serialized_process)
    
    # ensure timers exist
    if process.timers is None:
        process.timers = ProcessTimers()
    
    # track lives
    lives_remaining = process.process_config.lives
    
    # set up communication (SWAPPED for symmetric API)
    process._stop_event = stop_event
    process._tell_queue = listen_queue   # subprocess tell() → parent listen()
    process._listen_queue = tell_queue   # parent tell() → subprocess listen()
    
    process._start_time = timing.time()
    
    while lives_remaining > 0:
        try:
            # main execution loop
            while _should_continue(process, stop_event):
                _run_section_timed(process, '__prerun__', 'prerun', PreRunError, stop_event)
                if stop_event.is_set(): break
                
                _run_section_timed(process, '__run__', 'run', RunError, stop_event)
                if stop_event.is_set(): break
                
                _run_section_timed(process, '__postrun__', 'postrun', PostRunError, stop_event)
                
                process._current_run += 1
                process.timers._update_full_run()
            
            # success - run finish sequence
            _run_finish_sequence(process, stop_event, result_queue)
            return
            
        except (PreRunError, RunError, PostRunError, ProcessTimeoutError) as e:
            lives_remaining -= 1
            
            if lives_remaining > 0:
                # retry with current state
                process.process_config.lives = lives_remaining
                continue
            else:
                # no lives - send error
                _send_error(process, e, result_queue)
                return
```

### Queue Swapping Explanation

The tell/listen queues are swapped in the subprocess to create a symmetric API.

Without swapping:
- Parent creates two queues: `tell_queue` and `listen_queue`
- Parent's `tell()` writes to `tell_queue`
- Parent's `listen()` reads from `listen_queue`
- If subprocess uses same assignment, `tell()` would write to... `tell_queue` (same as parent!)
- Both would write to same queue, both would read from same queue = broken

Swap in subprocess to maintain symmetry.

```
Parent Process:
    process._tell_queue = Queue()      # Parent → Child (parent writes here)
    process._listen_queue = Queue()    # Child → Parent (parent reads from here)

Subprocess (after deserialization):
    process._tell_queue = listen_queue   # Child writes here → Parent reads
    process._listen_queue = tell_queue   # Child reads from here ← Parent writes
```

Result - symmetric API.

This means both sides use the same mental model:
- `tell()` always sends TO the other side
- `listen()` always receives FROM the other side

### Continuation Checks

Checked before each iteration of the main loop
1. **Stop signal** - Has the parent called `stop()`? Check the multiprocessing event.
2. **Run count** - Have we completed `process_config.runs` iterations? (If `runs=None`, skip this check - run indefinitely)
3. **Time limit** - Have we exceeded `process_config.join_in` seconds? (If `join_in=None`, skip this check)

**Evaluation order matters:**

- Stop signal checked first (highest priority - explicit user request)
- Run count checked second (natural completion)
- Time limit checked last (graceful timeout)

```python
def _should_continue(process, stop_event):
    # check stop signal
    if stop_event.is_set():
        return False
    
    # check run count limit
    if process.process_config.runs is not None:
        if process._current_run >= process.process_config.runs:
            return False
    
    # check time limit (join_in)
    if process.process_config.join_in is not None:
        elapsed = timing.elapsed(process._start_time)
        if elapsed >= process.process_config.join_in:
            return False
    
    return True
```

### Section Timing

Each lifecycle section is timed individually.

How section timing works
1. **Get the method** - Unwrap from `TimedMethod` if necessary to get the raw function
2. **Get the timeout** - Look up configured timeout for this section (e.g., `timeouts.run`)
3. **Get or create timer** - Ensure an `Sktimer` exists for this section
4. **Start the timer** - Begin measuring
5. **Execute with timeout** - Run the method with platform-appropriate timeout handling
6. **Stop the timer** - Record elapsed time on success
7. **Handle failures**:
   - Timeout: Discard timing (don't pollute stats), re-raise `ProcessTimeoutError`
   - Exception: Discard timing, wrap in section-specific error (e.g., `RunError`)

```python
def _run_section_timed(process, method_name, timer_name, error_class, stop_event):
    # get method (unwrap TimedMethod if needed)
    method_attr = getattr(process, method_name)
    method = method_attr._method if hasattr(method_attr, '_method') else method_attr
    
    # get timeout
    timeout = getattr(process.process_config.timeouts, timer_name, None)
    
    # get or create timer
    timer = process.timers._ensure_timer(timer_name)
    
    timer.start()
    try:
        run_with_timeout(method, timeout, method_name, process._current_run)
        timer.stop()
    except ProcessTimeoutError:
        timer.discard()  # don't record failed timing
        raise
    except Exception as e:
        timer.discard()
        raise error_class(process._current_run, e) from e
```

### Timeout Implementation

Platform-specific timeout handling.

Unix/Linux/macOS (signal-based):

How signal-based timeout works:
1. If no timeout configured, just run the function directly
2. Install a custom `SIGALRM` handler that raises `ProcessTimeoutError`
3. Set an alarm to fire after `timeout` seconds
4. Run the function
5. Cancel the alarm when done (success or exception)
6. Restore the original signal handler

This approach can interrupt **any** code, including blocking I/O.

```python
def _signal_based_timeout(func, timeout, section, current_run):
    if timeout is None:
        return func()
    
    def handler(signum, frame):
        raise ProcessTimeoutError(section, timeout, current_run)
    
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(int(timeout) + 1)
    
    try:
        return func()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
```

Windows (thread-based fallback):

How thread-based timeout works
1. If no timeout configured, just run the function directly
2. Create shared containers for result and exception (lists for mutability)
3. Create a completion event
4. Spawn a daemon thread to run the function
5. Wait on the completion event with timeout
6. If event fires before timeout: return result or re-raise exception
7. If timeout elapses first: raise `ProcessTimeoutError`

Limitation: The thread-based approach cannot interrupt blocking code. The thread continues running as a "zombie" but the timeout is detected and raised.

```python
def _thread_based_timeout(func, timeout, section, current_run):
    if timeout is None:
        return func()
    
    result = [None]
    exception = [None]
    completed = threading.Event()
    
    def wrapper():
        try:
            result[0] = func()
        except BaseException as e:
            exception[0] = e
        finally:
            completed.set()
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    
    finished = completed.wait(timeout=timeout)
    
    if not finished:
        raise ProcessTimeoutError(section, timeout, current_run)
    
    if exception[0] is not None:
        raise exception[0]
    
    return result[0]
```

### Finish Sequence

What happens when the process completes successfully
1. **Run `__onfinish__`** - Final cleanup, timed with configured timeout
   - If it fails: Send `OnFinishError` to parent, abort
2. **Run `__result__`** - Extract the return value, timed
   - If it fails: Send `ResultError` to parent, abort
3. **Serialize the result** - Convert return value to bytes
4. **Serialize the timers** - Include all timing data for parent access
5. **Send to result queue** - Parent will receive `{"type": "result", ...}`

```python
def _run_finish_sequence(process, stop_event, result_queue):
    # run __onfinish__
    method = unwrap(process.__onfinish__)
    timeout = process.process_config.timeouts.onfinish
    timer = process.timers._ensure_timer('onfinish')
    
    timer.start()
    try:
        run_with_timeout(method, timeout, '__onfinish__', process._current_run)
    except Exception as e:
        _send_error(process, OnFinishError(process._current_run, e), result_queue)
        return
    finally:
        timer.stop()
    
    # run __result__
    result_method = unwrap(process.__result__)
    result_timeout = process.process_config.timeouts.result
    result_timer = process.timers._ensure_timer('result')
    
    result_timer.start()
    try:
        result = run_with_timeout(result_method, result_timeout, '__result__', process._current_run)
    except Exception as e:
        _send_error(process, ResultError(process._current_run, e), result_queue)
        return
    finally:
        result_timer.stop()
    
    # send success result with timers
    result_queue.put({
        "type": "result",
        "data": cucumber.serialize(result),
        "timers": cucumber.serialize(process.timers)
    })
```

### Error Handling

What happens when the process fails (no lives remaining)
1. **Set `process.error`** - Make the error accessible to `__error__` method
2. **Run `__error__`** - Give user a chance to handle/transform the error
   - Timed with configured timeout
   - If `__error__` itself fails: use the original error
3. **Serialize the error result** - Whatever `__error__` returned (or original error)
4. **Serialize the timers** - Include all timing data collected so far
5. **Send to result queue** - Parent will receive `{"type": "error", ...}`

```python
def _send_error(process, error, result_queue):
    # set error for __error__ to access
    process.error = error
    
    error_method = unwrap(process.__error__)
    error_timeout = process.process_config.timeouts.error
    error_timer = process.timers._ensure_timer('error')
    
    error_timer.start()
    try:
        error_result = run_with_timeout(error_method, error_timeout, '__error__', process._current_run)
    except Exception:
        # if __error__ fails, send original error
        error_result = error
    finally:
        error_timer.stop()
    
    # send error result
    result_queue.put({
        "type": "error",
        "data": cucumber.serialize(error_result),
        "timers": cucumber.serialize(process.timers)
    })
```

### Result Queue Draining

The parent must drain the result queue BEFORE joining the subprocess to avoid deadlock.

Why deadlock can occur
1. Subprocess puts result on queue and tries to exit
2. Multiprocessing queues use a background thread to flush data
3. If the queue isn't drained, the flush blocks waiting for space
4. Parent calls `join()` waiting for subprocess to exit
5. Subprocess can't exit because queue flush is blocked
6. **Deadlock**: Parent waits for subprocess, subprocess waits for queue drain

How `_sync_wait()` avoids deadlock
1. **Drain first** - Try to get result from queue before joining
2. **Join with timeout** - Wait for subprocess to exit
3. **Drain again** - Get any remaining data
4. **Return status** - Whether subprocess has exited

How `_drain_result_queue()` works
1. Skip if result already received
2. Try non-blocking `get_nowait()` first
3. Fall back to short timeout `get(timeout=0.5)`
4. Deserialize timers and update parent's timer state
5. Deserialize result/error data
6. Mark `_has_result = True` so subsequent calls skip

```python
def _sync_wait(self, timeout=None):
    if self._subprocess is None:
        return True
    
    # MUST drain result queue BEFORE waiting
    # otherwise: subprocess can't exit until queue is drained,
    # but we can't drain until subprocess exits = deadlock
    self._drain_result_queue()
    
    self._subprocess.join(timeout=timeout)
    self._drain_result_queue()
    return not self._subprocess.is_alive()

def _drain_result_queue(self):
    if self._has_result or self._result_queue is None:
        return
    
    try:
        message = self._result_queue.get_nowait()
    except queue.Empty:
        message = self._result_queue.get(timeout=0.5)
    except:
        return
    
    # update timers from subprocess
    if message.get('timers'):
        self.timers = cucumber.deserialize(message['timers'])
        Skprocess._setup_timed_methods(self)
    
    if message["type"] == "error":
        self._result = cucumber.deserialize(message["data"])
    else:
        self._result = cucumber.deserialize(message["data"])
    
    self._has_result = True
```

---

## `Pool`

### Internal Structure

What Pool creates on initialization
1. **Worker count** - Use provided count or default to CPU count
2. **Active process tracking** - List to track spawned workers
3. **Multiprocessing pool** - Built-in pool for efficient batch execution

```python
class Pool:
    def __init__(self, workers=None):
        self._workers = workers or multiprocessing.cpu_count()
        self._active_processes = []
        self._mp_pool = multiprocessing.Pool(processes=self._workers)
```

### Map Implementation

Two execution paths
1. **Fast path (no timeout)** - Use built-in `multiprocessing.Pool.map()` for efficiency
2. **Timeout path** - Manual worker management with individual timeouts

Fast path
1. Convert iterable to list (need length and multiple passes)
2. Return early if empty
3. Serialize the function/Skprocess once (reused for all items)
4. Build argument tuples: `(serialized_fn, serialized_item, is_star)`
5. Use `multiprocessing.Pool.map()` to distribute work
6. Deserialize results, raise if any worker returned an error
7. Return results in input order

Timeout path
1. Create result array pre-sized to input length
2. Track active workers and next item index
3. **Spawn loop**: Start workers up to `self._workers` limit
4. **Collect loop**: Wait for any worker to finish
   - If worker times out: terminate it and raise `TimeoutError`
   - If worker succeeds: deserialize result into correct position
   - If worker fails: raise the deserialized exception
5. Remove finished worker from active list
6. Repeat until all items processed
7. Return results in input order

```python
def _map_impl(self, fn_or_process, iterable, is_star, timeout=None):
    items = list(iterable)
    if not items:
        return []
    
    # serialize function once
    serialized_fn = cucumber.serialize(fn_or_process)
    
    # use built-in multiprocessing.Pool for efficiency when no timeout
    if timeout is None and self._mp_pool is not None:
        args = [
            (serialized_fn, cucumber.serialize(item), is_star)
            for item in items
        ]
        messages = self._mp_pool.map(_pool_worker_bytes_args, args)
        results = []
        for message in messages:
            if message["type"] == "error":
                raise cucumber.deserialize(message["data"])
            results.append(cucumber.deserialize(message["data"]))
        return results
    
    # manual worker management with timeout
    results = [None] * len(items)
    active = []
    next_index = 0
    
    while active or next_index < len(items):
        # start workers up to limit
        while next_index < len(items) and len(active) < self._workers:
            serialized_item = cucumber.serialize(items[next_index])
            queue, worker = self._spawn_worker(serialized_fn, serialized_item, is_star)
            active.append((next_index, queue, worker))
            next_index += 1
        
        # collect finished workers
        for idx, queue, worker in list(active):
            worker.join(timeout=timeout)
            
            if worker.is_alive():
                worker.terminate()
                raise TimeoutError(f"Worker {idx} timed out")
            
            message = queue.get()
            if message["type"] == "error":
                raise cucumber.deserialize(message["data"])
            results[idx] = cucumber.deserialize(message["data"])
            active.remove((idx, queue, worker))
            break
    
    return results
```

### Worker Function

What runs in each pool worker subprocess
1. **Deserialize function** - Reconstruct the function or Skprocess class
2. **Deserialize item** - Reconstruct the input data for this worker
3. **Handle star mode** - If `is_star=True`, unpack tuple as positional args
4. **Detect Skprocess** - Check if `fn_or_process` is an Skprocess subclass
5. **Execute**:
   - If Skprocess: Instantiate with args, run inline (already in subprocess)
   - If function: Call directly with args
6. **Send result** - Serialize and put on result queue
7. **Handle errors** - Catch exceptions, serialize, send as error

```python
def _pool_worker(serialized_fn, serialized_item, is_star, result_queue):
    try:
        fn_or_process = cucumber.deserialize(serialized_fn)
        item = cucumber.deserialize(serialized_item)
        
        # unpack if star mode
        if is_star:
            args = item if isinstance(item, tuple) else (item,)
        else:
            args = (item,)
        
        # check if Skprocess class
        if isinstance(fn_or_process, type) and issubclass(fn_or_process, Skprocess):
            process_instance = fn_or_process(*args)
            result = _run_process_inline(process_instance)
        else:
            result = fn_or_process(*args) if is_star else fn_or_process(item)
        
        result_queue.put({
            "type": "result",
            "data": cucumber.serialize(result)
        })
    except Exception as e:
        result_queue.put({
            "type": "error",
            "data": cucumber.serialize(e)
        })
```

### Inline Process Execution

When `Pool` runs a `Skprocess`, it runs inline since it's already in a subprocess. No need to spawn another subprocess.

Key differences from normal `Skprocess` execution
1. **No subprocess** - Already in a worker process
2. **`threading.Event`** - Uses thread event instead of multiprocessing event
3. **Direct return** - Returns result directly instead of via queue

Inline execution
1. **Initialize timers** - Create `ProcessTimers` if needed
2. **Initialize state** - Set run counter to 0, record start time
3. **Create stop event** - `threading.Event` for potential early termination
4. **Copy lives** - For retry tracking

Main loop (same as engine)
1. Check continuation conditions
2. Run `__prerun__` → `__run__` → `__postrun__` cycle
3. Increment run counter, update timers
4. On success: run `__onfinish__` → `__result__`, return result
5. On failure: decrement lives, retry or run `__error__`

```python
def _run_process_inline(process):
    # ensure timers exist
    if process.timers is None:
        process.timers = ProcessTimers()
    
    # initialize state
    process._current_run = 0
    process._start_time = timing.time()
    
    # create threading.Event (not multiprocessing.Event - already in subprocess)
    stop_event = threading.Event()
    process._stop_event = stop_event
    
    lives_remaining = process.process_config.lives
    
    while lives_remaining > 0:
        try:
            while _should_continue_inline():
                _run_section_timed('__prerun__', 'prerun', PreRunError)
                if stop_event.is_set(): break
                
                _run_section_timed('__run__', 'run', RunError)
                if stop_event.is_set(): break
                
                _run_section_timed('__postrun__', 'postrun', PostRunError)
                
                process._current_run += 1
                process.timers._update_full_run()
            
            return _run_finish_sequence_inline(process)
            
        except (PreRunError, RunError, PostRunError, ProcessTimeoutError) as e:
            lives_remaining -= 1
            if lives_remaining > 0:
                continue
            else:
                return _run_error_sequence_inline(process, e)
```

### Modifier System

Pool methods return modifier objects that allow chaining.

Modifier chaining
1. `pool.map` returns `_PoolMapModifier` instance
2. Calling it directly (`pool.map(fn, items)`) runs synchronously
3. Calling `.timeout(30)` returns `_PoolMapTimeoutModifier` with timeout stored
4. Calling `.background()` returns `_PoolMapBackgroundModifier` that returns a Future
5. Calling `.asynced()` returns `_PoolMapAsyncModifier` that returns a coroutine

Modifier pattern
```
pool.map                     → _PoolMapModifier          → sync execution
pool.map.timeout(30)         → _PoolMapTimeoutModifier   → sync with timeout
pool.map.background()        → _PoolMapBackgroundModifier→ returns Future
pool.map.asynced()           → _PoolMapAsyncModifier     → returns coroutine
```

```python
class _PoolMapModifier:
    def __init__(self, pool, is_star=False):
        self._pool = pool
        self._is_star = is_star
    
    def __call__(self, fn_or_process, iterable):
        return self._pool._map_impl(fn_or_process, iterable, self._is_star)
    
    def timeout(self, seconds):
        return _PoolMapTimeoutModifier(self._pool, self._is_star, seconds)
    
    def background(self):
        return _PoolMapBackgroundModifier(self._pool, self._is_star)
    
    def asynced(self):
        return _PoolMapAsyncModifier(self._pool, self._is_star)
```

`star()` modifier
Returns a `StarModifier` that configures `is_star=True` for all methods. This makes each method unpack tuples as positional arguments.

```python
class StarModifier:
    def __init__(self, pool):
        self._pool = pool
    
    @property
    def map(self):
        return _PoolMapModifier(self._pool, is_star=True)
    
    @property
    def imap(self):
        return _PoolImapModifier(self._pool, is_star=True)
    
    @property
    def unordered_imap(self):
        return _PoolUnorderedImapModifier(self._pool, is_star=True)
    
    @property
    def unordered_map(self):
        return _PoolUnorderedMapModifier(self._pool, is_star=True)
```

---

## `Share`

### Architecture

`Share` uses a coordinator-proxy system to enable safe concurrent access to shared objects.

All writes go through a single queue to a coordinator process, ensuring serialized (one-at-a-time) execution. Reads wait for pending writes to complete before fetching.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Share Container                               │
│                                                                         │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐                       │
│  │   timer    │   │  counter   │   │   config   │   (user objects)      │
│  │   (proxy)  │   │  (proxy)   │   │  (direct)  │                       │
│  └─────┬──────┘   └─────┬──────┘   └─────┬──────┘                       │
│        │                │                │                              │
│        │ getattr()      │ setattr()      │ fetch                        │
│        ▼                ▼                ▼                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                         Coordinator                              │   │
│  │                                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐              │   │
│  │  │  Command Q  │  │  Counters   │  │ Source Store │              │   │
│  │  │  (Manager)  │  │  (Atomic)   │  │  (Manager)   │              │   │
│  │  └─────────────┘  └─────────────┘  └──────────────┘              │   │
│  │                                                                  │   │
│  │  Background Process:                                             │   │
│  │  - Consumes commands                                             │   │
│  │  - Executes on mirrors                                           │   │
│  │  - Commits to source                                             │   │
│  │  - Updates counters                                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Object Registration

What happens when you assign to a Share attribute (`share.timer = Sktimer()`)
1. **Check if internal** - Skip internal attributes (`_SHARE_ATTRS`)
2. **Check for `_shared_meta`** - Does the object's class have sharing metadata?
3. **Auto-wrap user classes** - If no metadata, wrap with `Skclass()` to generate it
4. **Extract read/write dependencies** - From `_shared_meta`, determine which attributes each method reads/writes
5. **Register with coordinator** - Send serialized object to background process
6. **Create proxy** - If has metadata, create `_ObjectProxy` to intercept access
7. **Store proxy** - Future attribute access returns the proxy, not the real object

```python
def __setattr__(self, name, value):
    if name in self._SHARE_ATTRS:
        object.__setattr__(self, name, value)
        return
    
    # check for _shared_meta (suitkaise objects)
    has_meta = hasattr(type(value), '_shared_meta')
    
    # auto-wrap user classes
    if not has_meta and self._is_user_class_instance(value):
        Skclass(type(value))  # generates _shared_meta
        has_meta = True
    
    # extract read/write attrs from _shared_meta
    attrs = set()
    if has_meta:
        meta = getattr(type(value), '_shared_meta', {})
        for method_meta in meta.get('methods', {}).values():
            attrs.update(method_meta.get('writes', []))
            attrs.update(method_meta.get('reads', []))
        for prop_meta in meta.get('properties', {}).values():
            attrs.update(prop_meta.get('reads', []))
            attrs.update(prop_meta.get('writes', []))
    
    # register with coordinator
    self._coordinator.register_object(name, value, attrs=attrs)
    
    # create proxy or direct reference
    if has_meta:
        proxy = _ObjectProxy(name, self._coordinator, type(value))
        self._proxies[name] = proxy
    else:
        self._proxies[name] = None  # fetch directly
```

### Coordinator

The coordinator is a background process that serializes all writes.

```python
class _Coordinator:
    def __init__(self, manager=None):
        self._manager = manager or Manager()
        self._command_queue = self._manager.Queue()
        self._counter_registry = _AtomicCounterRegistry(self._manager)
        self._source_store = self._manager.dict()
        self._source_lock = self._manager.Lock()
        self._object_names = self._manager.list()
```

#### Command Queue

All writes go through the command queue.

```python
def queue_command(self, object_name, method_name, args=(), kwargs=None, written_attrs=None):
    serialized_args = cucumber.serialize(args)
    serialized_kwargs = cucumber.serialize(kwargs or {})
    
    command = (object_name, method_name, serialized_args, serialized_kwargs, written_attrs or [])
    self._command_queue.put(command)
```

#### Counter System

The counter system ensures reads see consistent state by tracking pending writes.

Two counters per attribute
- **Pending count**: Incremented when a write is **queued**
- **Completed count**: Incremented when a write is **processed**

How it prevents stale reads
1. Write queued: `pending = 5, completed = 3`
2. Read starts: captures `target = pending = 5`
3. Read waits until `completed >= 5`
4. Once coordinator processes all queued writes, `completed = 5`
5. Read proceeds with fresh data

Why this works
- Writes increment pending **before** queueing (guarantees we capture all prior writes)
- Coordinator increments completed **after** committing to source
- Reads see all writes that were queued before the read started

```python
def increment_pending(self, key):
    return self._counter_registry.increment_pending(key)

def get_read_target(self, key):
    targets = self._counter_registry.get_read_targets([key])
    return targets.get(key, 0)

def wait_for_read(self, keys, timeout=1.0):
    return self._counter_registry.wait_for_read(keys, timeout=timeout)
```

#### Background Process Loop

```python
def _coordinator_main(command_queue, counter_registry, source_store, 
                      source_lock, stop_event, error_event, poll_timeout):
    mirrors = {}  # local cache of deserialized objects
    
    while not stop_event.is_set():
        try:
            command = command_queue.get(timeout=poll_timeout)
        except queue.Empty:
            continue
        
        object_name, method_name, ser_args, ser_kwargs, written_attrs = command
        
        # special commands
        if object_name == "__clear__":
            mirrors.clear()
            continue
        if object_name == "__remove__":
            mirrors.pop(method_name, None)
            continue
        
        # deserialize args
        args = cucumber.deserialize(ser_args)
        kwargs = cucumber.deserialize(ser_kwargs)
        
        # get mirror (from cache or source)
        mirror = mirrors.get(object_name)
        if mirror is None:
            with source_lock:
                serialized = source_store.get(object_name)
                if serialized:
                    mirror = cucumber.deserialize(serialized)
                    mirrors[object_name] = mirror
        
        if mirror is None:
            _update_counters_after_write(counter_registry, object_name, written_attrs)
            continue
        
        # execute method on mirror
        try:
            method = getattr(mirror, method_name)
            method(*args, **kwargs)
        except Exception:
            traceback.print_exc()
        
        # commit to source of truth
        with source_lock:
            serialized = cucumber.serialize(mirror)
            source_store[object_name] = serialized
        
        # update counters
        _update_counters_after_write(counter_registry, object_name, written_attrs)
```

### Proxy

The proxy intercepts all attribute access and routes it through the coordinator.

What the proxy does on attribute access (`share.timer.start()`)
1. **Check if internal** - Proxy's own attributes bypass interception
2. **Check if method** - If in `_shared_meta['methods']`, return `_MethodProxy`
3. **Check if property** - If in `_shared_meta['properties']`, wait for writes then fetch
4. **Fallback** - Fetch object from source and get attribute directly

What the proxy does on attribute assignment (`share.timer.count = 5`)
1. **Check if internal** - Proxy's own attributes bypass interception
2. **Increment pending counter** - Signal that a write is queued
3. **Queue setattr command** - Send to coordinator to execute later

```python
class _ObjectProxy:
    _PROXY_ATTRS = frozenset({'_object_name', '_coordinator', '_wrapped_class', '_shared_meta'})
    
    def __init__(self, object_name, coordinator, wrapped_class):
        object.__setattr__(self, '_object_name', object_name)
        object.__setattr__(self, '_coordinator', coordinator)
        object.__setattr__(self, '_wrapped_class', wrapped_class)
        object.__setattr__(self, '_shared_meta', getattr(wrapped_class, '_shared_meta', None))
    
    def __getattr__(self, name):
        # method calls -> return callable that queues commands
        if self._shared_meta and name in self._shared_meta.get('methods', {}):
            return _MethodProxy(self, name)
        
        # properties -> wait for writes, then fetch
        if self._shared_meta and name in self._shared_meta.get('properties', {}):
            return self._read_property(name)
        
        # fallback -> fetch and get attr
        return self._read_attr(name)
    
    def __setattr__(self, name, value):
        if name in self._PROXY_ATTRS:
            object.__setattr__(self, name, value)
            return
        
        # queue setattr command
        self._coordinator.increment_pending(f"{self._object_name}.{name}")
        self._coordinator.queue_command(
            self._object_name,
            '__setattr__',
            (name, value),
            {},
            [name]
        )
```

#### Method Proxy

What happens when you call a method (`share.timer.start()`)
1. **Get write dependencies** - From `_shared_meta`, which attributes will this method modify?
2. **Increment pending counters** - For each written attribute, signal a pending write
3. **Queue the command** - Send method name, args, kwargs to coordinator
4. **Return immediately** - Fire-and-forget, don't wait for execution

This is why writes are "fire-and-forget" - the method call returns before the coordinator processes it.

```python
class _MethodProxy:
    def __init__(self, object_proxy, method_name):
        self._object_proxy = object_proxy
        self._method_name = method_name
    
    def __call__(self, *args, **kwargs):
        proxy = self._object_proxy
        meta = proxy._shared_meta
        
        # get write attrs from _shared_meta
        method_meta = meta['methods'].get(self._method_name, {})
        write_attrs = method_meta.get('writes', [])
        
        # increment pending counters
        for attr in write_attrs:
            key = f"{proxy._object_name}.{attr}"
            proxy._coordinator.increment_pending(key)
        
        # queue command (fire-and-forget)
        proxy._coordinator.queue_command(
            proxy._object_name,
            self._method_name,
            args,
            kwargs,
            write_attrs
        )
```

#### Property Reading

What happens when you read a property (`share.timer.elapsed`)
1. **Get read dependencies** - From `_shared_meta`, which attributes does this property depend on?
2. **Build counter keys** - For each dependency, create `"object_name.attr_name"` key
3. **Wait for writes** - Block until all pending writes to those attributes complete
4. **Fetch fresh snapshot** - Deserialize latest state from source store
5. **Return property value** - Get attribute from the fresh snapshot

This is why reads block on pending writes - to ensure you see consistent state.

```python
def _read_property(self, name):
    # get read dependencies from _shared_meta
    prop_meta = self._shared_meta['properties'].get(name, {})
    read_attrs = prop_meta.get('reads', [])
    
    keys = [f"{self._object_name}.{attr}" for attr in read_attrs]
    
    # wait for all writes to complete
    if keys:
        self._coordinator.wait_for_read(keys, timeout=10.0)
    
    # fetch fresh snapshot
    obj = self._coordinator.get_object(self._object_name)
    return getattr(obj, name)
```

---

## `Pipe`

### Endpoint Structure

What a pipe endpoint does
1. **Holds connection** - `_conn` is a `multiprocessing.Pipe` connection object
2. **Tracks lock state** - `_locked` prevents serialization (transfer to subprocess)
3. **Tracks role** - `"anchor"` (parent side) or `"point"` (transferable side)

*How `send()` works
1. Ensure connection is valid
2. Serialize the object using `cucumber`
3. Send raw bytes over the connection

How `recv()` works
1. Ensure connection is valid
2. Read raw bytes from the connection
3. Deserialize using `cucumber` and return

How serialization works
1. Check if locked - locked endpoints **cannot** be serialized
2. Pickle the connection handle (Python's multiprocessing handles this)
3. Package with lock state and role for reconstruction

```python
@dataclass
class _PipeEndpoint:
    _conn: Optional[Any]
    _locked: bool = False
    _role: str = "point"
    
    def send(self, obj):
        conn = self._ensure_conn()
        conn.send_bytes(cucumber.serialize(obj))
    
    def recv(self):
        conn = self._ensure_conn()
        data = conn.recv_bytes()
        return cucumber.deserialize(data)
    
    def __serialize__(self):
        if self._locked:
            raise PipeEndpointError("Locked endpoint cannot be serialized")
        
        # pickle the connection handle for multiprocessing
        payload = pickle.dumps(self._conn)
        return {
            "conn_pickle": payload,
            "locked": self._locked,
            "role": self._role
        }
```

### `Anchor` vs `Point`

Design
- **Anchor** - The "fixed" end that stays in the parent process. Always locked, cannot be serialized.
- **Point** - The "transferable" end that gets passed to a subprocess. Can be locked/unlocked.

Why this separation?
1. Prevents accidentally serializing both ends (which would break the connection)
2. Makes ownership clear - anchor stays, point goes
3. Explicit `lock()` on point after transfer prevents re-transfer

How `pair()` works
1. Create a `multiprocessing.Pipe` with two connection objects
2. Wrap one in `Anchor` (automatically locked)
3. Wrap other in `Point` (unlocked, ready to transfer)
4. Return both for parent to use anchor and pass point to subprocess

```python
class Pipe:
    class Anchor(_PipeEndpoint):
        def __init__(self, conn, locked=True, role="anchor"):
            super().__init__(conn, True, role)  # always locked
        
        def unlock(self):
            raise PipeEndpointError("Anchor endpoints are always locked")
    
    class Point(_PipeEndpoint):
        pass
    
    @staticmethod
    def pair(one_way=False):
        conn1, conn2 = multiprocessing.Pipe(duplex=not one_way)
        anchor = Pipe.Anchor(conn1)
        point = Pipe.Point(conn2, False, "point")
        return anchor, point
```

---

## `ProcessConfig`

### Structure

```python
@dataclass
class TimeoutConfig:
    prerun: float | None = None
    run: float | None = None
    postrun: float | None = None
    onfinish: float | None = None
    result: float | None = None
    error: float | None = None

@dataclass
class ProcessConfig:
    runs: int | None = None      # None = indefinite
    join_in: float | None = None # None = no time limit
    lives: int = 1               # 1 = no retries
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
```

---

## `ProcessTimers`

### Structure

```python
class ProcessTimers:
    def __init__(self):
        # individual section timers (created lazily)
        self.prerun: Sktimer | None = None
        self.run: Sktimer | None = None
        self.postrun: Sktimer | None = None
        self.onfinish: Sktimer | None = None
        self.result: Sktimer | None = None
        self.error: Sktimer | None = None
        
        # aggregate for full iterations
        self.full_run: Sktimer = Sktimer()
    
    def _ensure_timer(self, section):
        current = getattr(self, section, None)
        if current is None:
            new_timer = Sktimer()
            setattr(self, section, new_timer)
            return new_timer
        return current
    
    def _update_full_run(self):
        total = 0.0
        for timer in [self.prerun, self.run, self.postrun]:
            if timer and timer.num_times > 0 and timer.most_recent:
                total += timer.most_recent
        
        if total > 0:
            self.full_run.add_time(total)
```

---

## `autoreconnect()` Decorator

### Implementation

What `@autoreconnect` does at class definition time

1. Mark the class as requiring reconnection (`_auto_reconnect_enabled = True`)
2. Store authentication credentials for each connection type
3. Store thread start preference

The decorator does NOT reconnect anything - it just marks the class so deserialization knows to reconnect.

```python
def autoreconnect(*, start_threads=False, **auth):
    def decorator(cls):
        # mark class for reconnect on deserialize
        cls._auto_reconnect_enabled = True
        cls._auto_reconnect_kwargs = dict(auth) if auth else {}
        cls._auto_reconnect_start_threads = bool(start_threads)
        return cls
    return decorator
```

### Triggered in Deserialization

What happens when a marked class is deserialized in a subprocess
1. Check if `_auto_reconnect_enabled` is True
2. Get stored auth credentials
3. Call `reconnect_all()` which recursively finds `Reconnector` objects
4. Each `Reconnector` calls its `reconnect(auth)` method to restore the live connection
5. If `start_threads=True`, find all `Thread` objects and start them

Reconnect Flow
1. `Skprocess` serialized with a database connection
2. `cucumber` converts connection to `PostgresReconnector` (stores connection params)
3. Subprocess deserializes the process
4. `__deserialize__` sees `_auto_reconnect_enabled`
5. `reconnect_all()` finds the `PostgresReconnector`
6. Calls `reconnector.reconnect("password")` → returns new live connection
7. Replaces reconnector with live connection in the object

```python
# in Skprocess.__deserialize__
if getattr(new_class, '_auto_reconnect_enabled', False):
    reconnect_kwargs = getattr(new_class, '_auto_reconnect_kwargs', {})
    start_threads = getattr(new_class, '_auto_reconnect_start_threads', False)
    
    obj = reconnect_all(obj, **reconnect_kwargs)
    
    if start_threads:
        # recursively find and start Thread objects
        _start_threads(obj)
```

---

## Error Hierarchy

```
ProcessError (base)
├── PreRunError
├── RunError
├── PostRunError
├── OnFinishError
├── ResultError
├── ErrorHandlerError
├── ProcessTimeoutError
├── ResultTimeoutError
└── DuplicateTimeoutError
```

### Error Structure

```python
class ProcessError(Exception):
    def __init__(self, message, current_run=0, original_error=None):
        self.current_run = current_run
        self.original_error = original_error
        super().__init__(message)

class PreRunError(ProcessError):
    def __init__(self, current_run, original_error=None):
        super().__init__(
            f"Error in __prerun__ on run {current_run}",
            current_run,
            original_error
        )

class ProcessTimeoutError(ProcessError):
    def __init__(self, section, timeout, current_run):
        self.section = section
        self.timeout = timeout
        super().__init__(
            f"Timeout in {section} after {timeout}s on run {current_run}",
            current_run,
            None
        )
```

---

## Thread Safety

### `Skprocess`

Each `Skprocess` runs in its own subprocess, providing process isolation.

- **No shared memory** - Each subprocess has its own memory space
- **Communication via queues** - All cross-process data goes through serialization
- **Stop signals** - `multiprocessing.Event` for parent→child signaling

Within the subprocess:
- `threading.Event` used for stop signaling (in Pool inline execution)
- `multiprocessing.Event` used for cross-process signaling

### `Pool`

`Pool` thread safety
- **Built-in pool** - Uses `multiprocessing.Pool` which handles worker management internally
- **Manual mode** - For timeout scenarios, tracks workers in `_active_processes` list
- **Result isolation** - Each worker writes to its own result queue

### `Share`

`Share` thread safety
1. **Single writer** - All writes go through one coordinator process (no write conflicts)
2. **Command queue** - All writes serialized through a single queue
3. **Atomic counters** - Pending/completed counters use shared memory atomics
4. **Source lock** - Single lock protects source of truth access
5. **Manager-backed primitives** - `Manager.dict()`, `Manager.Queue()` handle inter-process sync

Reads wait for pending writes to complete before fetching, ensuring you see effects of prior writes from the same logical sequence.

---

## Serialization

All cross-process communication uses `cucumber` for serialization.

What gets serialized and where
- `Skprocess` - Full state + lifecycle methods
- `Pool` - Function/class + each item
- `Share` - Registered objects
- `Pipe` - Any object via `send()`

Why `cucumber` instead of `pickle`
1. **Locally-defined classes** - `pickle` fails on `<locals>` classes, `cucumber` reconstructs them
2. **Live resources** - Database connections become `Reconnector` objects that can restore themselves
3. **Circular references** - Handled correctly during serialization
4. **Complex nested structures** - Recursively handles arbitrary object graphs
5. **Custom handlers** - Extensible for any type

Serialization flow
1. Object passed to `cucumber.serialize()`
2. Handlers match by type and extract state
3. State converted to bytes
4. Bytes sent over queue/pipe/store
5. Receiving side calls `cucumber.deserialize()`
6. Handlers reconstruct objects from state
