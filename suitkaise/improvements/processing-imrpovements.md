# Processing Module Improvements

## Existing TODOs

- [ ] Add shared state patterns (shared memory, Manager() equivalent, etc)
- [ ] Add easy shared memory usage
- [ ] Document `Pool` better
- [ ] Ensure that `tell()` serializes data with cerial before putting it in the queue
- [ ] How do we handle Ctrl+C?

---

## Shared State Patterns

### The Problem

When running multiple processes, they often need to share data. Python's `multiprocessing` provides primitives like `Value`, `Array`, `Manager`, and shared memory, but they're awkward to use:

```python
# Current stdlib way - verbose and error-prone
from multiprocessing import Manager, Value
import ctypes

manager = Manager()
shared_dict = manager.dict()  # Slow, goes through a manager process
shared_counter = Value(ctypes.c_int, 0)  # Fast but limited to primitives
shared_lock = manager.Lock()  # Another thing to manage

# You have to pass these explicitly to every process
# And coordinate locking manually
```

The `Process` class abstracts away queues beautifully with `tell()`/`listen()`, but shared state is a different problem that needs its own solution.

### Design Goals

1. **Simple API** — As easy as using regular Python objects
2. **Automatic synchronization** — No manual locking for common operations
3. **Cerial integration** — Complex objects work out of the box
4. **Thread/process safe** — Works across multiple workers
5. **Minimal overhead** — Fast path for primitives, managed path for complex types

---

### Proposed API

#### `SharedState` Container

```python
from suitkaise.processing import Process, SharedState

class WorkerProcess(Process):
    
    def __init__(self, shared: SharedState):
        self.shared = shared
    
    def __run__(self):
        # Atomic increment - no manual locking needed
        self.shared.counter.increment()
        
        # Thread/process-safe dict operations
        self.shared.results[self.current_run] = self.compute_result()
        
        # Read latest value from another process
        if self.shared.flags.get('should_stop'):
            self.stop()


# Parent process
shared = SharedState()
shared.counter = 0  # Becomes a shared atomic counter
shared.results = {}  # Becomes a shared dict
shared.flags = {'should_stop': False}

workers = [WorkerProcess(shared) for _ in range(4)]
for w in workers:
    w.start()

# Later, signal all workers to stop
shared.flags['should_stop'] = True

for w in workers:
    w.wait()

print(f"Total processed: {shared.counter}")  # Aggregated from all workers
print(f"All results: {shared.results}")
```

---

### Implementation Plan

#### Phase 1: Core SharedState Class

##### File: `suitkaise/processing/_int/shared_state.py`

```python
"""
SharedState - Process-safe shared state container.

Provides a simple interface for sharing data between processes
with automatic synchronization and cerial integration.
"""

import multiprocessing
from multiprocessing import Manager
from multiprocessing.managers import SyncManager
from typing import Any, Dict, List, Optional, TypeVar, Generic
import threading

T = TypeVar('T')


class SharedCounter:
    """
    Process-safe atomic counter.
    
    Provides atomic increment/decrement operations without manual locking.
    
    Usage:
        counter = SharedCounter(0)
        counter.increment()      # Thread/process-safe
        counter.increment(5)     # Add 5
        counter.decrement()      # Subtract 1
        value = counter.value    # Read current value
    """
    
    def __init__(self, initial: int = 0, manager: Optional[SyncManager] = None):
        self._manager = manager or Manager()
        self._value = self._manager.Value('i', initial)
        self._lock = self._manager.Lock()
    
    def increment(self, amount: int = 1) -> int:
        """Atomically increment and return new value."""
        with self._lock:
            self._value.value += amount
            return self._value.value
    
    def decrement(self, amount: int = 1) -> int:
        """Atomically decrement and return new value."""
        with self._lock:
            self._value.value -= amount
            return self._value.value
    
    def set(self, value: int) -> None:
        """Set the counter value."""
        with self._lock:
            self._value.value = value
    
    @property
    def value(self) -> int:
        """Get current value."""
        with self._lock:
            return self._value.value
    
    def __int__(self) -> int:
        return self.value
    
    def __repr__(self) -> str:
        return f"SharedCounter({self.value})"


class SharedFlag:
    """
    Process-safe boolean flag.
    
    Provides atomic set/clear/toggle operations.
    
    Usage:
        flag = SharedFlag(False)
        flag.set()       # Set to True
        flag.clear()     # Set to False
        flag.toggle()    # Flip value
        if flag:         # Check value
            ...
    """
    
    def __init__(self, initial: bool = False, manager: Optional[SyncManager] = None):
        self._manager = manager or Manager()
        self._value = self._manager.Value('b', initial)
        self._lock = self._manager.Lock()
    
    def set(self) -> None:
        """Set flag to True."""
        with self._lock:
            self._value.value = True
    
    def clear(self) -> None:
        """Set flag to False."""
        with self._lock:
            self._value.value = False
    
    def toggle(self) -> bool:
        """Toggle and return new value."""
        with self._lock:
            self._value.value = not self._value.value
            return self._value.value
    
    @property
    def value(self) -> bool:
        """Get current value."""
        with self._lock:
            return self._value.value
    
    def __bool__(self) -> bool:
        return self.value
    
    def __repr__(self) -> str:
        return f"SharedFlag({self.value})"


class SharedDict(Generic[T]):
    """
    Process-safe dictionary with automatic locking.
    
    All operations are atomic. Supports cerial-serializable values.
    
    Usage:
        d = SharedDict()
        d['key'] = 'value'       # Thread/process-safe
        value = d['key']         # Thread/process-safe
        d.update({'a': 1, 'b': 2})  # Atomic batch update
    """
    
    def __init__(self, initial: Optional[Dict[str, T]] = None, manager: Optional[SyncManager] = None):
        self._manager = manager or Manager()
        self._dict = self._manager.dict()
        self._lock = self._manager.Lock()
        
        if initial:
            with self._lock:
                self._dict.update(initial)
    
    def __getitem__(self, key: str) -> T:
        with self._lock:
            return self._dict[key]
    
    def __setitem__(self, key: str, value: T) -> None:
        with self._lock:
            self._dict[key] = value
    
    def __delitem__(self, key: str) -> None:
        with self._lock:
            del self._dict[key]
    
    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._dict
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._dict)
    
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Get value or default if not found."""
        with self._lock:
            return self._dict.get(key, default)
    
    def pop(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Remove and return value."""
        with self._lock:
            return self._dict.pop(key, default)
    
    def update(self, data: Dict[str, T]) -> None:
        """Atomic batch update."""
        with self._lock:
            self._dict.update(data)
    
    def keys(self) -> list:
        """Return list of keys (snapshot)."""
        with self._lock:
            return list(self._dict.keys())
    
    def values(self) -> list:
        """Return list of values (snapshot)."""
        with self._lock:
            return list(self._dict.values())
    
    def items(self) -> list:
        """Return list of items (snapshot)."""
        with self._lock:
            return list(self._dict.items())
    
    def to_dict(self) -> Dict[str, T]:
        """Return a regular dict copy (snapshot)."""
        with self._lock:
            return dict(self._dict)
    
    def clear(self) -> None:
        """Remove all items."""
        with self._lock:
            self._dict.clear()
    
    def __repr__(self) -> str:
        return f"SharedDict({self.to_dict()})"


class SharedList(Generic[T]):
    """
    Process-safe list with automatic locking.
    
    All operations are atomic. Supports cerial-serializable values.
    
    Usage:
        lst = SharedList()
        lst.append('item')       # Thread/process-safe
        item = lst[0]            # Thread/process-safe
        lst.extend([1, 2, 3])    # Atomic batch extend
    """
    
    def __init__(self, initial: Optional[List[T]] = None, manager: Optional[SyncManager] = None):
        self._manager = manager or Manager()
        self._list = self._manager.list()
        self._lock = self._manager.Lock()
        
        if initial:
            with self._lock:
                self._list.extend(initial)
    
    def __getitem__(self, index: int) -> T:
        with self._lock:
            return self._list[index]
    
    def __setitem__(self, index: int, value: T) -> None:
        with self._lock:
            self._list[index] = value
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._list)
    
    def append(self, value: T) -> None:
        """Append item to list."""
        with self._lock:
            self._list.append(value)
    
    def extend(self, values: List[T]) -> None:
        """Atomic batch extend."""
        with self._lock:
            self._list.extend(values)
    
    def pop(self, index: int = -1) -> T:
        """Remove and return item at index."""
        with self._lock:
            return self._list.pop(index)
    
    def remove(self, value: T) -> None:
        """Remove first occurrence of value."""
        with self._lock:
            self._list.remove(value)
    
    def to_list(self) -> List[T]:
        """Return a regular list copy (snapshot)."""
        with self._lock:
            return list(self._list)
    
    def clear(self) -> None:
        """Remove all items."""
        with self._lock:
            # Manager list doesn't have clear(), iterate and pop
            while len(self._list) > 0:
                self._list.pop()
    
    def __repr__(self) -> str:
        return f"SharedList({self.to_list()})"


class SharedState:
    """
    Container for process-safe shared state.
    
    Automatically converts assigned values to their shared equivalents:
    - int → SharedCounter
    - bool → SharedFlag  
    - dict → SharedDict
    - list → SharedList
    
    Usage:
        shared = SharedState()
        shared.counter = 0           # Creates SharedCounter
        shared.results = {}          # Creates SharedDict
        shared.items = []            # Creates SharedList
        shared.should_stop = False   # Creates SharedFlag
        
        # Pass to workers
        worker = MyProcess(shared)
        worker.start()
        
        # Workers can read/write safely
        shared.counter.increment()
        shared.results['key'] = 'value'
    """
    
    def __init__(self):
        # Use a single manager for all shared objects (more efficient)
        self._manager = Manager()
        self._attrs: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return
        
        with self._lock:
            # Convert to appropriate shared type
            if isinstance(value, int) and not isinstance(value, bool):
                self._attrs[name] = SharedCounter(value, self._manager)
            elif isinstance(value, bool):
                self._attrs[name] = SharedFlag(value, self._manager)
            elif isinstance(value, dict):
                self._attrs[name] = SharedDict(value, self._manager)
            elif isinstance(value, list):
                self._attrs[name] = SharedList(value, self._manager)
            elif isinstance(value, (SharedCounter, SharedFlag, SharedDict, SharedList)):
                # Already a shared type
                self._attrs[name] = value
            else:
                # For other types, use a Manager.Value with cerial serialization
                # This is slower but handles any cerial-serializable type
                self._attrs[name] = self._create_shared_value(value)
    
    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        
        try:
            return self._attrs[name]
        except KeyError:
            raise AttributeError(f"SharedState has no attribute '{name}'")
    
    def _create_shared_value(self, value: Any) -> Any:
        """Create a shared wrapper for arbitrary cerial-serializable values."""
        # Use a dict to store arbitrary values (slower but flexible)
        wrapper = SharedDict({'value': value}, self._manager)
        return _SharedValue(wrapper)
    
    def __serialize__(self) -> dict:
        """Serialize for passing to subprocess."""
        from suitkaise import cerial
        
        state = {}
        for name, shared_obj in self._attrs.items():
            if isinstance(shared_obj, SharedCounter):
                state[name] = {'type': 'counter', 'value': shared_obj.value}
            elif isinstance(shared_obj, SharedFlag):
                state[name] = {'type': 'flag', 'value': shared_obj.value}
            elif isinstance(shared_obj, SharedDict):
                state[name] = {'type': 'dict', 'value': shared_obj.to_dict()}
            elif isinstance(shared_obj, SharedList):
                state[name] = {'type': 'list', 'value': shared_obj.to_list()}
            else:
                state[name] = {'type': 'value', 'value': cerial.serialize(shared_obj)}
        
        return state
    
    @classmethod
    def __deserialize__(cls, state: dict) -> "SharedState":
        """Deserialize in subprocess."""
        from suitkaise import cerial
        
        obj = cls()
        for name, data in state.items():
            if data['type'] == 'counter':
                obj._attrs[name] = SharedCounter(data['value'], obj._manager)
            elif data['type'] == 'flag':
                obj._attrs[name] = SharedFlag(data['value'], obj._manager)
            elif data['type'] == 'dict':
                obj._attrs[name] = SharedDict(data['value'], obj._manager)
            elif data['type'] == 'list':
                obj._attrs[name] = SharedList(data['value'], obj._manager)
            else:
                obj._attrs[name] = cerial.deserialize(data['value'])
        
        return obj


class _SharedValue:
    """Wrapper for arbitrary shared values stored in a SharedDict."""
    
    def __init__(self, wrapper: SharedDict):
        self._wrapper = wrapper
    
    @property
    def value(self) -> Any:
        return self._wrapper['value']
    
    @value.setter
    def value(self, new_value: Any) -> None:
        self._wrapper['value'] = new_value
    
    def __repr__(self) -> str:
        return f"SharedValue({self.value!r})"
```

---

#### Phase 2: Integration with Process

Update the `Process` class to support shared state more seamlessly:

```python
# In process_class.py, add support for SharedState in lifecycle

class Process:
    # ... existing code ...
    
    def start(self) -> None:
        """Start the process in a new subprocess."""
        from suitkaise import cerial
        
        # Serialize shared state separately for proper manager handling
        shared_attrs = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, SharedState):
                shared_attrs[attr_name] = attr
        
        # ... rest of start logic ...
```

---

#### Phase 3: Higher-Level Patterns

##### `SharedResults` - Collect Results from Multiple Workers

```python
class SharedResults(Generic[T]):
    """
    Collect results from multiple workers in order.
    
    Each worker writes to its assigned slot. Parent reads all results
    after workers complete.
    
    Usage:
        results = SharedResults(num_workers=4)
        
        for i in range(4):
            worker = MyProcess(results, worker_id=i)
            worker.start()
        
        # After all workers complete
        all_results = results.collect()  # [result0, result1, result2, result3]
    """
    
    def __init__(self, num_workers: int):
        self._manager = Manager()
        self._results = self._manager.dict()
        self._lock = self._manager.Lock()
        self._num_workers = num_workers
    
    def set_result(self, worker_id: int, result: T) -> None:
        """Called by worker to store its result."""
        with self._lock:
            self._results[worker_id] = result
    
    def collect(self) -> List[Optional[T]]:
        """Collect all results in order. Returns None for missing slots."""
        with self._lock:
            return [self._results.get(i) for i in range(self._num_workers)]
    
    def get_result(self, worker_id: int) -> Optional[T]:
        """Get result from specific worker."""
        with self._lock:
            return self._results.get(worker_id)
```

##### `SharedProgress` - Track Progress Across Workers

```python
class SharedProgress:
    """
    Track progress across multiple workers.
    
    Usage:
        progress = SharedProgress(total=1000)
        
        workers = [MyProcess(progress) for _ in range(4)]
        for w in workers:
            w.start()
        
        while not progress.is_complete:
            print(f"Progress: {progress.percent:.1f}%")
            time.sleep(0.5)
    """
    
    def __init__(self, total: int):
        self._manager = Manager()
        self._completed = self._manager.Value('i', 0)
        self._total = total
        self._lock = self._manager.Lock()
    
    def increment(self, amount: int = 1) -> None:
        """Mark items as completed."""
        with self._lock:
            self._completed.value += amount
    
    @property
    def completed(self) -> int:
        with self._lock:
            return self._completed.value
    
    @property
    def percent(self) -> float:
        return (self.completed / self._total) * 100
    
    @property
    def is_complete(self) -> bool:
        return self.completed >= self._total
```

---

### Documentation Updates

Add to `processing-how-to-use.md`:

```markdown
## Shared State

When multiple processes need to share data, use `SharedState` for automatic synchronization.

### Basic Usage

```python
from suitkaise.processing import Process, SharedState

class CounterWorker(Process):
    def __init__(self, shared: SharedState, worker_id: int):
        self.shared = shared
        self.worker_id = worker_id
        self.config.runs = 100
    
    def __run__(self):
        # Atomic increment - safe across all workers
        self.shared.counter.increment()
        
        # Store result for this worker
        self.shared.results[f"worker_{self.worker_id}_{self.current_run}"] = "done"


# Create shared state
shared = SharedState()
shared.counter = 0    # Becomes SharedCounter
shared.results = {}   # Becomes SharedDict

# Start workers
workers = [CounterWorker(shared, i) for i in range(4)]
for w in workers:
    w.start()

for w in workers:
    w.wait()

print(f"Total: {shared.counter}")        # 400 (4 workers × 100 runs)
print(f"Results: {len(shared.results)}") # 400 entries
```

### Atomic Types

| Assignment | Becomes | Operations |
|------------|---------|------------|
| `shared.x = 0` | `SharedCounter` | `.increment()`, `.decrement()`, `.value` |
| `shared.x = False` | `SharedFlag` | `.set()`, `.clear()`, `.toggle()`, `if shared.x:` |
| `shared.x = {}` | `SharedDict` | `[]`, `.get()`, `.update()`, `.pop()` |
| `shared.x = []` | `SharedList` | `.append()`, `.extend()`, `.pop()`, `[]` |

### Signaling Between Processes

```python
class StoppableWorker(Process):
    def __init__(self, shared: SharedState):
        self.shared = shared
        self.config.runs = None  # Infinite loop
    
    def __run__(self):
        # Check for stop signal
        if self.shared.should_stop:
            self.stop()
            return
        
        # Do work...

# Create shared state with flag
shared = SharedState()
shared.should_stop = False

worker = StoppableWorker(shared)
worker.start()

# Later, from parent process
shared.should_stop.set()  # or shared.should_stop = True

worker.wait()
```
```

---

### Testing Plan

1. **Unit tests for SharedCounter**
   - Test increment/decrement from single process
   - Test concurrent increment from multiple processes
   - Test value consistency after many operations

2. **Unit tests for SharedDict/SharedList**
   - Test basic operations (get, set, delete)
   - Test batch operations (update, extend)
   - Test concurrent modifications
   - Test with cerial-serializable complex values

3. **Integration tests**
   - Test SharedState with Process class
   - Test serialization/deserialization across process boundary
   - Test with Pool

4. **Performance tests**
   - Compare SharedCounter vs raw Value
   - Compare SharedDict vs Manager.dict()
   - Measure contention under heavy concurrent access

---

## Async Processing Support

### Overview

Add async/await support for I/O-bound workloads. The current `Process` class is optimized for CPU-bound work (runs in separate OS processes). For I/O-bound work (API calls, database queries, file I/O), async is more efficient—a single process can handle thousands of concurrent I/O operations.

### Use Cases

1. **Batch API calls** — Fetch data from 1000 endpoints concurrently
2. **Database operations** — Run many queries without blocking
3. **Web scraping** — Crawl many pages simultaneously
4. **File I/O** — Read/write many files with async file handles
5. **Websocket handling** — Maintain many connections

### Design Goals

1. Mirror the existing `Process` API as closely as possible
2. Reuse existing infrastructure (config, timers, errors, cerial)
3. Keep it simple—don't over-engineer
4. Let users choose sync or async based on workload

---

## Implementation Plan

### Phase 1: AsyncProcess Base Class

Create a new base class that mirrors `Process` but with async lifecycle methods.

#### File: `suitkaise/processing/_int/async_process.py`

```python
"""
AsyncProcess base class for async subprocess execution.

Users inherit from AsyncProcess, define async lifecycle methods,
and the engine handles running them in an event loop within a subprocess.
"""

import asyncio
import multiprocessing
import queue as queue_module
from typing import Any, TYPE_CHECKING

from .config import ProcessConfig
from .timers import ProcessTimers

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event
    from multiprocessing import Queue
    from suitkaise.sktime import Timer


class AsyncTimedMethod:
    """
    Wrapper for async lifecycle methods that provides a .timer attribute.
    
    Same as TimedMethod but for coroutines.
    """
    
    def __init__(self, method, process: "AsyncProcess", timer_name: str):
        self._method = method
        self._process = process
        self._timer_name = timer_name
    
    async def __call__(self, *args, **kwargs):
        return await self._method(*args, **kwargs)
    
    @property
    def timer(self) -> "Timer | None":
        if self._process.timers is None:
            return None
        return getattr(self._process.timers, self._timer_name, None)


class AsyncProcess:
    """
    Base class for async subprocess execution.
    
    Same lifecycle as Process, but all methods are coroutines.
    Runs in an asyncio event loop within the subprocess.
    
    Usage:
        class MyAsyncProcess(AsyncProcess):
            async def __init__(self):
                self.session = None
                self.config.runs = 100
            
            async def __prerun__(self):
                if self.session is None:
                    self.session = aiohttp.ClientSession()
            
            async def __run__(self):
                async with self.session.get(self.url) as response:
                    self.data = await response.json()
            
            async def __onfinish__(self):
                if self.session:
                    await self.session.close()
            
            async def __result__(self):
                return self.data
        
        process = MyAsyncProcess()
        process.start()
        process.wait()
        result = process.result()
    """
    
    # Same class-level attributes as Process
    config: ProcessConfig
    timers: ProcessTimers | None
    timer: "Timer | None"
    error: BaseException | None
    _current_run: int
    _start_time: float | None
    _stop_event: "Event | None"
    _result_queue: "Queue[Any] | None"
    _tell_queue: "Queue[Any] | None"
    _listen_queue: "Queue[Any] | None"
    _subprocess: multiprocessing.Process | None
    _result: Any
    _has_result: bool
    
    _INTERNAL_ATTRS = frozenset({
        'config', 'timers', 'error', '_current_run', '_start_time',
        '_stop_event', '_result_queue', '_tell_queue', '_listen_queue',
        '_subprocess', '_result', '_has_result', '_timed_methods',
    })
    
    def __init_subclass__(cls, **kwargs):
        """Same pattern as Process - auto-wrap __init__, set up serialization."""
        super().__init_subclass__(**kwargs)
        
        # Wrap __init__ to call setup first
        if '__init__' in cls.__dict__:
            original_init = cls.__dict__['__init__']
            
            def wrapped_init(self, *args, **kwargs):
                AsyncProcess._setup(self)
                original_init(self, *args, **kwargs)
            
            wrapped_init.__name__ = original_init.__name__
            wrapped_init.__doc__ = original_init.__doc__
            cls.__init__ = wrapped_init
        else:
            def default_init(self, *args, **kwargs):
                AsyncProcess._setup(self)
            cls.__init__ = default_init
        
        # Set up serialization (same pattern as Process)
        user_serialize = cls.__dict__.get('__serialize__')
        user_deserialize = cls.__dict__.get('__deserialize__')
        
        def make_serialize(user_ser):
            def __serialize__(self):
                return AsyncProcess._serialize_with_user(self, user_ser)
            return __serialize__
        
        cls.__serialize__ = make_serialize(user_serialize)
        
        is_local = "<locals>" in cls.__qualname__
        
        if is_local:
            def make_deserialize_static(user_deser):
                def __deserialize__(reconstructed_cls, state):
                    return AsyncProcess._deserialize_with_user(reconstructed_cls, state, user_deser)
                return staticmethod(__deserialize__)
            cls.__deserialize__ = make_deserialize_static(user_deserialize)
        else:
            def make_deserialize_classmethod(user_deser):
                @classmethod
                def __deserialize__(inner_cls, state):
                    return AsyncProcess._deserialize_with_user(inner_cls, state, user_deser)
                return __deserialize__
            cls.__deserialize__ = make_deserialize_classmethod(user_deserialize)
    
    # =========================================================================
    # Serialization (reuse Process patterns)
    # =========================================================================
    
    _LIFECYCLE_METHODS = (
        '__prerun__', '__run__', '__postrun__', 
        '__onfinish__', '__result__', '__error__'
    )
    
    @staticmethod
    def _serialize_with_user(instance: "AsyncProcess", user_serialize=None) -> dict:
        """Same as Process._serialize_with_user but for AsyncProcess."""
        cls = instance.__class__
        
        lifecycle_methods = {}
        for name in AsyncProcess._LIFECYCLE_METHODS:
            if name in cls.__dict__:
                lifecycle_methods[name] = cls.__dict__[name]
        
        class_attrs = {}
        for name, value in cls.__dict__.items():
            if name.startswith('_'):
                continue
            if name in lifecycle_methods:
                continue
            class_attrs[name] = value
        
        instance_dict = {}
        for key, value in instance.__dict__.items():
            if isinstance(value, AsyncTimedMethod):
                continue
            instance_dict[key] = value
        
        state = {
            'instance_dict': instance_dict,
            'class_name': cls.__name__,
            'lifecycle_methods': lifecycle_methods,
            'class_attrs': class_attrs,
            'is_async': True,  # Mark as async for deserialization
        }
        
        if user_serialize is not None:
            state['user_custom_state'] = user_serialize(instance)
            state['has_user_serialize'] = True
        
        return state
    
    @staticmethod
    def _deserialize_with_user(reconstructed_cls: type, state: dict, user_deserialize=None) -> "AsyncProcess":
        """Same as Process._deserialize_with_user but for AsyncProcess."""
        class_dict = {}
        class_dict.update(state.get('class_attrs', {}))
        class_dict.update(state['lifecycle_methods'])
        
        new_class = type(
            state['class_name'],
            (AsyncProcess,),
            class_dict
        )
        
        obj = object.__new__(new_class)
        obj.__dict__.update(state['instance_dict'])
        AsyncProcess._setup_timed_methods(obj)
        
        if state.get('has_user_serialize') and user_deserialize is not None:
            user_state = state.get('user_custom_state', {})
            # Handle classmethod/staticmethod/function
            if isinstance(user_deserialize, classmethod):
                user_func = user_deserialize.__func__
                user_result = user_func(new_class, user_state)
            elif isinstance(user_deserialize, staticmethod):
                user_func = user_deserialize.__func__
                user_result = user_func(new_class, user_state)
            else:
                try:
                    user_result = user_deserialize(new_class, user_state)
                except TypeError:
                    user_result = user_deserialize(user_state)
            
            if user_result is not None and hasattr(user_result, '__dict__'):
                for key, value in user_result.__dict__.items():
                    if key not in obj.__dict__:
                        obj.__dict__[key] = value
        
        return obj
    
    def __serialize__(self) -> dict:
        return AsyncProcess._serialize_with_user(self, None)
    
    @classmethod
    def __deserialize__(cls, state: dict) -> "AsyncProcess":
        return AsyncProcess._deserialize_with_user(cls, state, None)
    
    # =========================================================================
    # Internal setup
    # =========================================================================
    
    @staticmethod
    def _setup(instance: "AsyncProcess") -> None:
        """Initialize internal process state."""
        instance.config = ProcessConfig()
        instance.timers = None
        instance._current_run = 0
        instance._start_time = None
        instance.error = None
        instance._stop_event = None
        instance._result_queue = None
        instance._tell_queue = None
        instance._listen_queue = None
        instance._subprocess = None
        instance._result = None
        instance._has_result = False
        AsyncProcess._setup_timed_methods(instance)
    
    @staticmethod
    def _setup_timed_methods(instance: "AsyncProcess") -> None:
        """Create AsyncTimedMethod wrappers for user-defined lifecycle methods."""
        cls = instance.__class__
        
        method_to_timer = {
            '__prerun__': 'prerun',
            '__run__': 'run',
            '__postrun__': 'postrun',
            '__onfinish__': 'onfinish',
            '__result__': 'result',
            '__error__': 'error',
        }
        
        for method_name, timer_name in method_to_timer.items():
            if method_name in cls.__dict__:
                method = getattr(instance, method_name)
                wrapper = AsyncTimedMethod(method, instance, timer_name)
                setattr(instance, method_name, wrapper)
    
    # =========================================================================
    # Async lifecycle methods (override these in subclass)
    # =========================================================================
    
    async def __prerun__(self) -> None:
        """Called before each __run__() iteration. Override in subclass."""
        pass
    
    async def __run__(self) -> None:
        """Main async work method. Called each iteration. Override in subclass."""
        pass
    
    async def __postrun__(self) -> None:
        """Called after each __run__() iteration. Override in subclass."""
        pass
    
    async def __onfinish__(self) -> None:
        """Called when process ends. Override in subclass."""
        pass
    
    async def __result__(self) -> Any:
        """Return data when process completes. Override in subclass."""
        return None
    
    async def __error__(self) -> Any:
        """Handle errors when all lives exhausted. Override in subclass."""
        return self.error
    
    # =========================================================================
    # Control methods (called from parent process - SYNC, not async)
    # These are the same as Process - they run in the parent
    # =========================================================================
    
    def start(self) -> None:
        """Start the async process in a new subprocess."""
        from .async_engine import _async_engine_main
        from suitkaise import cerial
        
        if self.timers is None:
            self.timers = ProcessTimers()
        
        serialized = cerial.serialize(self)
        original_state = serialized
        
        self._stop_event = multiprocessing.Event()
        self._result_queue = multiprocessing.Queue()
        self._tell_queue = multiprocessing.Queue()
        self._listen_queue = multiprocessing.Queue()
        
        from suitkaise import sktime
        self._start_time = sktime.time()
        
        self._subprocess = multiprocessing.Process(
            target=_async_engine_main,
            args=(serialized, self._stop_event, self._result_queue,
                  original_state, self._tell_queue, self._listen_queue)
        )
        self._subprocess.start()
    
    def stop(self) -> None:
        """Signal the process to stop gracefully."""
        if self._stop_event is not None:
            self._stop_event.set()
    
    def kill(self) -> None:
        """Forcefully terminate the process immediately."""
        if self._subprocess is not None and self._subprocess.is_alive():
            self._subprocess.terminate()
            self._subprocess.join(timeout=5)
            if self._subprocess.is_alive():
                self._subprocess.kill()
    
    def wait(self, timeout: float | None = None) -> bool:
        """Wait for the process to finish."""
        if self._subprocess is None:
            return True
        self._drain_result_queue(timeout)
        self._subprocess.join(timeout=timeout)
        return not self._subprocess.is_alive()
    
    def _drain_result_queue(self, timeout: float | None = None) -> None:
        """Read result from queue and store internally."""
        if self._has_result or self._result_queue is None:
            return
        
        from suitkaise import cerial
        
        try:
            message = self._result_queue.get(timeout=timeout if timeout else 1.0)
            
            if 'timers' in message and message['timers'] is not None:
                self.timers = cerial.deserialize(message['timers'])
                AsyncProcess._setup_timed_methods(self)
            
            if message["type"] == "error":
                error_data = cerial.deserialize(message["data"])
                if isinstance(error_data, BaseException):
                    self._result = error_data
                else:
                    from .errors import ProcessError
                    self._result = ProcessError(f"Process failed: {error_data}")
            else:
                self._result = cerial.deserialize(message["data"])
            
            self._has_result = True
        except queue_module.Empty:
            pass
    
    def result(self) -> Any:
        """Get the result from the process."""
        self.wait()
        
        if self._has_result:
            if isinstance(self._result, BaseException):
                raise self._result
            return self._result
        
        return None
    
    def tell(self, data: Any) -> None:
        """Send data to the subprocess (non-blocking)."""
        if self._tell_queue is None:
            raise RuntimeError("Cannot tell() - process not started")
        
        from suitkaise import cerial
        serialized = cerial.serialize(data)
        self._tell_queue.put(serialized)
    
    def listen(self, timeout: float | None = None) -> Any:
        """Receive data from the subprocess (blocking)."""
        if self._listen_queue is None:
            raise RuntimeError("Cannot listen() - process not started")
        
        from suitkaise import cerial
        
        try:
            serialized = self._listen_queue.get(timeout=timeout)
            return cerial.deserialize(serialized)
        except queue_module.Empty:
            return None
    
    # Async versions for use inside the subprocess
    async def async_tell(self, data: Any) -> None:
        """Async version of tell() for use inside the subprocess."""
        if self._listen_queue is None:
            raise RuntimeError("Cannot tell() - queues not set up")
        
        from suitkaise import cerial
        import asyncio
        
        serialized = cerial.serialize(data)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._listen_queue.put, serialized)
    
    async def async_listen(self, timeout: float | None = None) -> Any:
        """Async version of listen() for use inside the subprocess."""
        if self._tell_queue is None:
            raise RuntimeError("Cannot listen() - queues not set up")
        
        from suitkaise import cerial
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        def blocking_get():
            try:
                return self._tell_queue.get(timeout=timeout)
            except queue_module.Empty:
                return None
        
        serialized = await loop.run_in_executor(None, blocking_get)
        if serialized is None:
            return None
        return cerial.deserialize(serialized)
    
    @property
    def timer(self) -> "Timer | None":
        if self.timers is None:
            return None
        return self.timers.full_run
    
    @property
    def current_run(self) -> int:
        return self._current_run
    
    @property
    def is_alive(self) -> bool:
        return self._subprocess is not None and self._subprocess.is_alive()
```

---

#### File: `suitkaise/processing/_int/async_engine.py`

```python
"""
Async engine for running AsyncProcess instances in a subprocess.

This runs the async lifecycle methods in an asyncio event loop.
"""

import asyncio
from typing import Any

from .errors import (
    ProcessError, PreRunError, RunError, PostRunError,
    OnFinishError, ResultError, ProcessTimeoutError
)
from .timers import ProcessTimers


async def _async_engine_loop(process, stop_event):
    """
    Main async loop that runs the lifecycle methods.
    
    Args:
        process: The AsyncProcess instance
        stop_event: multiprocessing.Event to signal stop
    
    Returns:
        The result from __result__() or __error__()
    """
    from suitkaise import sktime
    
    # Ensure timers exist
    if process.timers is None:
        process.timers = ProcessTimers()
    
    runs = process.config.runs
    max_runs = runs if runs is not None else float('inf')
    
    try:
        run = 0
        while run < max_runs:
            # Check for stop signal
            if stop_event.is_set():
                break
            
            process._current_run = run
            
            # Start timing this full run
            process.timers.full_run.start()
            
            # __prerun__
            if hasattr(process.__class__, '__prerun__'):
                process.timers.prerun.start()
                try:
                    timeout = process.config.timeouts.prerun
                    if timeout:
                        await asyncio.wait_for(
                            process.__prerun__(),
                            timeout=timeout
                        )
                    else:
                        await process.__prerun__()
                except asyncio.TimeoutError:
                    raise ProcessTimeoutError("prerun", timeout, run)
                finally:
                    process.timers.prerun.stop()
            
            # Check for stop signal again
            if stop_event.is_set():
                process.timers.full_run.discard()
                break
            
            # __run__
            process.timers.run.start()
            try:
                timeout = process.config.timeouts.run
                if timeout:
                    await asyncio.wait_for(
                        process.__run__(),
                        timeout=timeout
                    )
                else:
                    await process.__run__()
            except asyncio.TimeoutError:
                raise ProcessTimeoutError("run", timeout, run)
            finally:
                process.timers.run.stop()
            
            # __postrun__
            if hasattr(process.__class__, '__postrun__'):
                process.timers.postrun.start()
                try:
                    timeout = process.config.timeouts.postrun
                    if timeout:
                        await asyncio.wait_for(
                            process.__postrun__(),
                            timeout=timeout
                        )
                    else:
                        await process.__postrun__()
                except asyncio.TimeoutError:
                    raise ProcessTimeoutError("postrun", timeout, run)
                finally:
                    process.timers.postrun.stop()
            
            # Record full run time
            process.timers.full_run.stop()
            
            run += 1
        
        # __onfinish__
        if hasattr(process.__class__, '__onfinish__'):
            process.timers.onfinish.start()
            try:
                timeout = process.config.timeouts.onfinish
                if timeout:
                    await asyncio.wait_for(
                        process.__onfinish__(),
                        timeout=timeout
                    )
                else:
                    await process.__onfinish__()
            except asyncio.TimeoutError:
                raise ProcessTimeoutError("onfinish", timeout, run)
            finally:
                process.timers.onfinish.stop()
        
        # __result__
        process.timers.result.start()
        try:
            timeout = process.config.timeouts.result
            if timeout:
                result = await asyncio.wait_for(
                    process.__result__(),
                    timeout=timeout
                )
            else:
                result = await process.__result__()
        except asyncio.TimeoutError:
            raise ProcessTimeoutError("result", timeout, run)
        finally:
            process.timers.result.stop()
        
        return ("result", result)
    
    except Exception as e:
        # Store error for __error__ method
        process.error = e
        
        # Wrap in appropriate error type
        if isinstance(e, ProcessTimeoutError):
            wrapped_error = e
        elif 'prerun' in str(e).lower() or (hasattr(e, '__traceback__') and '__prerun__' in str(e.__traceback__)):
            wrapped_error = PreRunError(str(e), original_error=e, current_run=process._current_run)
        elif 'postrun' in str(e).lower():
            wrapped_error = PostRunError(str(e), original_error=e, current_run=process._current_run)
        elif 'onfinish' in str(e).lower():
            wrapped_error = OnFinishError(str(e), original_error=e, current_run=process._current_run)
        else:
            wrapped_error = RunError(str(e), original_error=e, current_run=process._current_run)
        
        process.error = wrapped_error
        
        # Call __error__
        process.timers.error.start()
        try:
            error_result = await process.__error__()
        finally:
            process.timers.error.stop()
        
        return ("error", error_result if error_result is not None else wrapped_error)


def _async_engine_main(serialized, stop_event, result_queue, original_state, tell_queue, listen_queue):
    """
    Entry point for the subprocess.
    
    Creates an event loop and runs the async engine.
    """
    from suitkaise import cerial
    
    # Deserialize the process
    process = cerial.deserialize(serialized)
    
    # Attach communication primitives
    process._stop_event = stop_event
    process._result_queue = result_queue
    process._tell_queue = tell_queue
    process._listen_queue = listen_queue
    
    # Create and run the event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result_type, result_data = loop.run_until_complete(
            _async_engine_loop(process, stop_event)
        )
        
        # Send result back
        result_queue.put({
            "type": result_type,
            "data": cerial.serialize(result_data),
            "timers": cerial.serialize(process.timers),
        })
    
    except Exception as e:
        # Catastrophic failure - couldn't even run the loop
        from .errors import ProcessError
        result_queue.put({
            "type": "error",
            "data": cerial.serialize(ProcessError(f"Engine failure: {e}")),
            "timers": cerial.serialize(process.timers) if process.timers else None,
        })
    
    finally:
        # Clean up the event loop
        try:
            # Cancel all pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Wait for cancellations
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()
```

---

### Phase 2: AsyncPool

Add a pool class optimized for async work with controlled concurrency.

#### File: `suitkaise/processing/_int/async_pool.py`

```python
"""
AsyncPool for batch async operations with controlled concurrency.

Unlike Pool (which spawns subprocesses), AsyncPool runs everything
in a single event loop with semaphore-controlled concurrency.
"""

import asyncio
from typing import Any, Callable, Iterable, TypeVar, AsyncIterator

T = TypeVar('T')
R = TypeVar('R')


class AsyncPool:
    """
    Pool for async operations with controlled concurrency.
    
    Unlike the regular Pool (which spawns OS processes), AsyncPool runs
    all operations in a single asyncio event loop. This is ideal for
    I/O-bound work like API calls, database queries, and file I/O.
    
    Usage:
        async def fetch_url(url):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
        
        # Process 1000 URLs with max 50 concurrent requests
        pool = AsyncPool(max_concurrent=50)
        results = await pool.map(fetch_url, urls)
    
    Args:
        max_concurrent: Maximum number of concurrent operations (default 10)
    """
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None
    
    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore (must be called within event loop)."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore
    
    async def map(self, func: Callable[[T], R], items: Iterable[T]) -> list[R]:
        """
        Apply async function to all items concurrently.
        
        Blocks until all items are processed, then returns results
        in the same order as the input items.
        
        Args:
            func: Async function to apply to each item
            items: Iterable of items to process
        
        Returns:
            List of results in same order as input
        """
        semaphore = self._get_semaphore()
        
        async def bounded_call(item: T) -> R:
            async with semaphore:
                return await func(item)
        
        return await asyncio.gather(*[bounded_call(item) for item in items])
    
    async def imap(self, func: Callable[[T], R], items: Iterable[T]) -> AsyncIterator[R]:
        """
        Apply async function to items, yielding results in order.
        
        Results are yielded in the same order as input items.
        If the next result isn't ready, waits for it.
        
        Args:
            func: Async function to apply to each item
            items: Iterable of items to process
        
        Yields:
            Results in order
        """
        semaphore = self._get_semaphore()
        items_list = list(items)
        
        async def bounded_call(item: T) -> R:
            async with semaphore:
                return await func(item)
        
        # Create all tasks
        tasks = [asyncio.create_task(bounded_call(item)) for item in items_list]
        
        # Yield results in order
        for task in tasks:
            yield await task
    
    async def unordered_imap(self, func: Callable[[T], R], items: Iterable[T]) -> AsyncIterator[R]:
        """
        Apply async function to items, yielding results as they complete.
        
        Results are yielded as soon as they're ready, regardless of order.
        Fastest way to process items when order doesn't matter.
        
        Args:
            func: Async function to apply to each item
            items: Iterable of items to process
        
        Yields:
            Results as they complete (unordered)
        """
        semaphore = self._get_semaphore()
        items_list = list(items)
        
        async def bounded_call(item: T) -> R:
            async with semaphore:
                return await func(item)
        
        # Create all tasks
        tasks = [asyncio.create_task(bounded_call(item)) for item in items_list]
        
        # Yield results as they complete
        for coro in asyncio.as_completed(tasks):
            yield await coro
    
    async def starmap(self, func: Callable[..., R], items: Iterable[tuple]) -> list[R]:
        """
        Apply async function to items, unpacking each item as arguments.
        
        Each item should be a tuple of arguments to pass to func.
        
        Args:
            func: Async function to apply
            items: Iterable of argument tuples
        
        Returns:
            List of results in same order as input
        """
        semaphore = self._get_semaphore()
        
        async def bounded_call(args: tuple) -> R:
            async with semaphore:
                return await func(*args)
        
        return await asyncio.gather(*[bounded_call(item) for item in items])


class AsyncPoolContext:
    """
    Context manager for AsyncPool that handles event loop creation.
    
    For use in synchronous code that wants to use AsyncPool.
    
    Usage:
        with AsyncPoolContext(max_concurrent=50) as pool:
            results = pool.run(pool.map(fetch_url, urls))
    """
    
    def __init__(self, max_concurrent: int = 10):
        self.pool = AsyncPool(max_concurrent)
        self._loop: asyncio.AbstractEventLoop | None = None
    
    def __enter__(self) -> "AsyncPoolContext":
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._loop:
            self._loop.close()
    
    def run(self, coro):
        """Run a coroutine in the event loop."""
        if self._loop is None:
            raise RuntimeError("Must be used within context manager")
        return self._loop.run_until_complete(coro)
    
    async def map(self, func, items):
        return await self.pool.map(func, items)
    
    async def imap(self, func, items):
        async for result in self.pool.imap(func, items):
            yield result
    
    async def unordered_imap(self, func, items):
        async for result in self.pool.unordered_imap(func, items):
            yield result
```

---

### Phase 3: Update Exports

#### Update: `suitkaise/processing/__init__.py`

```python
# Add to existing imports
from ._int.async_process import AsyncProcess, AsyncTimedMethod
from ._int.async_pool import AsyncPool, AsyncPoolContext

# Add to __all__
__all__ = [
    # Existing
    'Process',
    'Pool',
    'ProcessConfig',
    'TimeoutConfig',
    'ProcessTimers',
    'ProcessError',
    'PreRunError',
    'RunError',
    'PostRunError',
    'OnFinishError',
    'ResultError',
    'ProcessTimeoutError',
    
    # New async support
    'AsyncProcess',
    'AsyncPool',
    'AsyncPoolContext',
]
```

---

### Phase 4: Cerial Handlers for Async Objects

Extend cerial to handle common async objects.

#### File: `suitkaise/cerial/_int/handlers/async_handler.py` (update existing)

Add handlers for:
- `asyncio.Semaphore` — Recreate with same value
- `asyncio.Lock` — Recreate (unlocked)
- `asyncio.Event` — Recreate with same state
- `asyncio.Queue` — Recreate and restore items
- `aiohttp.ClientSession` — Cannot serialize (raise helpful error)
- `asyncpg.Connection` — Cannot serialize (raise helpful error)

```python
# Example handler for asyncio.Semaphore
class AsyncioSemaphoreHandler(BaseHandler):
    """Handler for asyncio.Semaphore objects."""
    
    type_name = "asyncio_semaphore"
    
    def can_handle(self, obj: Any) -> bool:
        return isinstance(obj, asyncio.Semaphore)
    
    def serialize(self, obj: asyncio.Semaphore, path: str) -> dict:
        # Semaphore._value is the current value
        return {
            "__cerial_type__": self.type_name,
            "state": {
                "value": obj._value,
            }
        }
    
    def deserialize(self, data: dict, path: str) -> asyncio.Semaphore:
        value = data["state"]["value"]
        return asyncio.Semaphore(value)
```

---

## Documentation Updates

### Add to `processing-how-to-use.md`

```markdown
## Async Processing

For I/O-bound workloads (API calls, database queries, file I/O), use `AsyncProcess` instead of `Process`.

### When to Use What

| Workload Type | Use | Why |
|--------------|-----|-----|
| CPU-bound (calculations, image processing) | `Process` | Needs separate OS process to bypass GIL |
| I/O-bound (API calls, database, files) | `AsyncProcess` | Event loop handles concurrency efficiently |
| Mixed | `Process` with async inside | Run event loop in subprocess |

### AsyncProcess Usage

```python
from suitkaise.processing import AsyncProcess
import aiohttp

class FetchUsers(AsyncProcess):
    
    def __init__(self, user_ids):
        self.user_ids = user_ids
        self.users = []
        self.session = None
    
    async def __prerun__(self):
        self.session = aiohttp.ClientSession()
    
    async def __run__(self):
        tasks = [self.fetch_user(uid) for uid in self.user_ids]
        self.users = await asyncio.gather(*tasks)
    
    async def fetch_user(self, user_id):
        async with self.session.get(f"https://api.com/users/{user_id}") as resp:
            return await resp.json()
    
    async def __onfinish__(self):
        if self.session:
            await self.session.close()
    
    async def __result__(self):
        return self.users


# Usage (same as Process!)
fetcher = FetchUsers([1, 2, 3, 4, 5])
fetcher.start()
fetcher.wait()
users = fetcher.result()
```

### AsyncPool for Simple Batch Operations

```python
from suitkaise.processing import AsyncPool
import aiohttp

async def fetch_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Run from async code
async def main():
    pool = AsyncPool(max_concurrent=50)
    urls = [f"https://api.com/item/{i}" for i in range(1000)]
    results = await pool.map(fetch_url, urls)
    return results

# Run from sync code
from suitkaise.processing import AsyncPoolContext

with AsyncPoolContext(max_concurrent=50) as ctx:
    urls = [f"https://api.com/item/{i}" for i in range(1000)]
    results = ctx.run(ctx.map(fetch_url, urls))
```
```

---

## Testing Plan

1. **Unit tests for AsyncProcess**
   - Test all lifecycle methods are called in order
   - Test timeout handling with `asyncio.TimeoutError`
   - Test `async_tell()` and `async_listen()` communication
   - Test error handling and `__error__()` method
   - Test timer recording

2. **Unit tests for AsyncPool**
   - Test `map()` returns results in order
   - Test `imap()` yields in order
   - Test `unordered_imap()` yields as completed
   - Test semaphore limits concurrency correctly
   - Test `starmap()` unpacks arguments

3. **Integration tests**
   - Real HTTP requests with aiohttp
   - Real database queries with asyncpg
   - Mixed sync/async operations

4. **Performance tests**
   - Compare AsyncProcess vs Process for I/O-bound work
   - Measure overhead of cerial serialization for async objects
   - Test with 1000+ concurrent operations

---

## Migration Guide

For users upgrading from sync Process to async:

1. Change `class MyProcess(Process)` to `class MyProcess(AsyncProcess)`
2. Add `async` keyword to all lifecycle methods
3. Change `self.tell()` to `await self.async_tell()` inside subprocess
4. Change `self.listen()` to `await self.async_listen()` inside subprocess
5. Replace blocking I/O with async equivalents:
   - `requests` → `aiohttp`
   - `psycopg2` → `asyncpg`
   - `open()` → `aiofiles.open()`

---

## Cross-Module Async Support

Beyond `AsyncProcess` and `AsyncPool`, async variants could be added to other suitkaise modules for consistency and better integration with async codebases.

---

### sktime Async Variants

The `sktime` module can benefit from async variants for use in async contexts.

#### `async_sleep()`

Non-blocking sleep that doesn't freeze the event loop.

```python
# In suitkaise/sktime/api.py

import asyncio

async def async_sleep(seconds: float) -> float:
    """
    Async sleep that doesn't block the event loop.
    
    Args:
        seconds: Number of seconds to sleep
    
    Returns:
        Current time after sleeping
    
    Usage:
        await sktime.async_sleep(1.0)
    """
    await asyncio.sleep(seconds)
    return time()
```

#### `AsyncTimeThis` Context Manager

```python
class AsyncTimeThis:
    """
    Async context manager for timing async code blocks.
    
    Usage:
        async with sktime.AsyncTimeThis() as timer:
            await fetch_data()
            await process_data()
        
        print(f"Took: {timer.most_recent:.3f}s")
    
        # With explicit timer for stats aggregation
        timer = sktime.Timer()
        
        for url in urls:
            async with sktime.AsyncTimeThis(timer):
                await fetch(url)
        
        print(f"Average: {timer.mean:.3f}s")
    """
    
    def __init__(self, timer: Timer | None = None):
        self.timer = timer or Timer()
    
    async def __aenter__(self) -> Timer:
        self.timer.start()
        return self.timer
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.timer.stop()


# Usage
async with sktime.AsyncTimeThis() as timer:
    await some_async_operation()

print(f"Time: {timer.most_recent:.3f}s")
```

#### `@async_timethis` Decorator

```python
def async_timethis(timer_instance: Timer | None = None) -> Callable:
    """
    Decorator for timing async functions.
    
    Usage:
        @sktime.async_timethis()
        async def fetch_user(user_id: int):
            async with aiohttp.ClientSession() as session:
                async with session.get(f"/users/{user_id}") as resp:
                    return await resp.json()
        
        await fetch_user(123)
        print(f"Time: {fetch_user.timer.most_recent:.3f}s")
    """
    def decorator(func: Callable) -> Callable:
        # Create or use provided timer
        nonlocal timer_instance
        if timer_instance is None:
            timer_instance = Timer()
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            timer_instance.start()
            try:
                return await func(*args, **kwargs)
            finally:
                timer_instance.stop()
        
        wrapper.timer = timer_instance
        return wrapper
    
    return decorator


# Usage
@sktime.async_timethis()
async def fetch_data(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

await fetch_data("https://api.example.com/data")
print(f"Fetch took: {fetch_data.timer.most_recent:.3f}s")

# Multiple calls build statistics
for url in urls:
    await fetch_data(url)

print(f"Average: {fetch_data.timer.mean:.3f}s")
print(f"P95: {fetch_data.timer.percentile(95):.3f}s")
```

#### Exports Update

```python
# Add to suitkaise/sktime/__init__.py

__all__ = [
    # Existing
    'time', 'sleep', 'elapsed',
    'Timer', 'Yawn', 'TimeThis', 'timethis',
    'clear_global_timers',
    
    # New async variants
    'async_sleep',
    'AsyncTimeThis', 
    'async_timethis',
]
```

---

### cerial Async Variants

For very large objects, serialization can block the event loop. Async variants run serialization in a thread pool.

#### `async_serialize()` and `async_deserialize()`

```python
# In suitkaise/cerial/api.py

import asyncio
from concurrent.futures import ThreadPoolExecutor

# Shared thread pool for serialization work
_serialization_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cerial_async")


async def async_serialize(obj, debug: bool = False, verbose: bool = False) -> bytes:
    """
    Async serialization that doesn't block the event loop.
    
    Runs serialization in a thread pool, allowing other async tasks
    to continue while serializing large objects.
    
    Args:
        obj: Object to serialize
        debug: Enable debug mode
        verbose: Enable verbose mode
    
    Returns:
        Serialized bytes
    
    Usage:
        large_data = load_huge_dataset()
        
        # Non-blocking - other async tasks can run
        serialized = await cerial.async_serialize(large_data)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _serialization_pool,
        lambda: serialize(obj, debug=debug, verbose=verbose)
    )


async def async_deserialize(data: bytes, debug: bool = False, verbose: bool = False):
    """
    Async deserialization that doesn't block the event loop.
    
    Runs deserialization in a thread pool, allowing other async tasks
    to continue while deserializing large objects.
    
    Args:
        data: Serialized bytes
        debug: Enable debug mode
        verbose: Enable verbose mode
    
    Returns:
        Deserialized object
    
    Usage:
        # Non-blocking - other async tasks can run
        obj = await cerial.async_deserialize(data)
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _serialization_pool,
        lambda: deserialize(data, debug=debug, verbose=verbose)
    )
```

#### Use Case: Web Server with Large Objects

```python
from suitkaise import cerial
from aiohttp import web

async def handle_upload(request):
    """Handle large object upload without blocking other requests."""
    data = await request.read()
    
    # Deserialize in background - doesn't block event loop
    obj = await cerial.async_deserialize(data)
    
    # Process object...
    result = process(obj)
    
    # Serialize response in background
    response_data = await cerial.async_serialize(result)
    
    return web.Response(body=response_data)
```

#### Exports Update

```python
# Add to suitkaise/cerial/__init__.py

__all__ = [
    # Existing
    'serialize', 'deserialize',
    
    # New async variants
    'async_serialize',
    'async_deserialize',
]
```

---

### circuit Async Variants

Circuit breakers often wrap async operations. An async-aware variant provides non-blocking sleep on trip.

#### `AsyncCircuit` Class

```python
# In suitkaise/circuit/api.py

import asyncio

class AsyncCircuit:
    """
    Async-aware circuit breaker for use in async code.
    
    Same API as Circuit, but sleep operations are non-blocking.
    
    Usage:
        breaker = circuit.AsyncCircuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)
        
        async def fetch_with_retry(url: str):
            while not breaker.broken:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as response:
                            return await response.json()
                except aiohttp.ClientError:
                    await breaker.async_short()  # Non-blocking sleep on trip
            
            return None
    """
    
    def __init__(self, num_shorts_to_trip: int, sleep_time_after_trip: float = 0.0):
        self.num_shorts_to_trip = num_shorts_to_trip
        self.sleep_time_after_trip = sleep_time_after_trip
        self._broken = False
        self._times_shorted = 0
        self._total_failures = 0
        self._lock = asyncio.Lock()
    
    @property
    def broken(self) -> bool:
        return self._broken
    
    @property
    def times_shorted(self) -> int:
        return self._times_shorted
    
    @property
    def total_failures(self) -> int:
        return self._total_failures
    
    async def async_short(self, custom_sleep: float | None = None) -> None:
        """
        Async version of short() - non-blocking sleep on trip.
        
        Args:
            custom_sleep: Override default sleep duration for this short
        """
        should_trip = False
        sleep_duration = custom_sleep if custom_sleep is not None else self.sleep_time_after_trip
        
        async with self._lock:
            self._times_shorted += 1
            self._total_failures += 1
            
            if self._times_shorted >= self.num_shorts_to_trip:
                should_trip = True
        
        if should_trip:
            await self._async_break_circuit(sleep_duration)
    
    async def async_trip(self, custom_sleep: float | None = None) -> None:
        """
        Async version of trip() - immediately break with non-blocking sleep.
        
        Args:
            custom_sleep: Override default sleep duration
        """
        async with self._lock:
            self._total_failures += 1
        
        sleep_duration = custom_sleep if custom_sleep is not None else self.sleep_time_after_trip
        await self._async_break_circuit(sleep_duration)
    
    async def _async_break_circuit(self, sleep_duration: float) -> None:
        """Break the circuit with async sleep."""
        async with self._lock:
            self._broken = True
            self._times_shorted = 0
        
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration)
    
    async def async_reset(self) -> None:
        """Reset the circuit to operational state."""
        async with self._lock:
            self._broken = False
            self._times_shorted = 0
    
    # Sync versions for compatibility (use from sync code or when sleep doesn't matter)
    def short(self, custom_sleep: float | None = None) -> None:
        """Sync version - blocks on sleep. Use async_short() in async code."""
        import time
        
        should_trip = False
        sleep_duration = custom_sleep if custom_sleep is not None else self.sleep_time_after_trip
        
        self._times_shorted += 1
        self._total_failures += 1
        
        if self._times_shorted >= self.num_shorts_to_trip:
            should_trip = True
        
        if should_trip:
            self._broken = True
            self._times_shorted = 0
            if sleep_duration > 0:
                time.sleep(sleep_duration)
    
    def trip(self, custom_sleep: float | None = None) -> None:
        """Sync version - blocks on sleep. Use async_trip() in async code."""
        import time
        
        self._total_failures += 1
        self._broken = True
        self._times_shorted = 0
        
        sleep_duration = custom_sleep if custom_sleep is not None else self.sleep_time_after_trip
        if sleep_duration > 0:
            time.sleep(sleep_duration)
    
    def reset(self) -> None:
        """Reset the circuit to operational state."""
        self._broken = False
        self._times_shorted = 0
```

#### Use Case: API Rate Limiting

```python
from suitkaise import circuit
import aiohttp

# Shared circuit for API calls
api_circuit = circuit.AsyncCircuit(num_shorts_to_trip=3, sleep_time_after_trip=5.0)

async def call_api(endpoint: str):
    """Call API with circuit breaker protection."""
    while not api_circuit.broken:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.example.com{endpoint}") as response:
                    if response.status == 429:  # Rate limited
                        await api_circuit.async_short(custom_sleep=10.0)
                        continue
                    
                    response.raise_for_status()
                    return await response.json()
        
        except aiohttp.ClientError:
            await api_circuit.async_short()  # Non-blocking 5s sleep on trip
    
    raise Exception("Circuit breaker tripped - API unavailable")


async def main():
    # These can run concurrently - circuit is shared
    results = await asyncio.gather(
        call_api("/users/1"),
        call_api("/users/2"),
        call_api("/users/3"),
    )
```

#### Exports Update

```python
# Add to suitkaise/circuit/__init__.py

__all__ = [
    'Circuit',
    'AsyncCircuit',
]
```

---

### Priority and Effort Summary

| Module | Feature | Effort | Value | Priority |
|--------|---------|--------|-------|----------|
| sktime | `async_sleep()` | Low | Medium | High |
| sktime | `AsyncTimeThis` | Low | Medium | High |
| sktime | `@async_timethis` | Low | High | High |
| cerial | `async_serialize()` | Low | Medium | Medium |
| cerial | `async_deserialize()` | Low | Medium | Medium |
| circuit | `AsyncCircuit` | Medium | Medium | Medium |

The sktime async variants are highest priority because:
1. Low implementation effort (mostly wrappers around asyncio equivalents)
2. Common need in async codebases
3. Natural complement to existing sync API