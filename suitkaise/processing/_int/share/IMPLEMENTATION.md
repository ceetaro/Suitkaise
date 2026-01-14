# Share Implementation Plan

## Goal API

From `suitkaise/implementation.md`:

```python
from suitkaise.processing import Share
from suitkaise.timing import Sktimer

share = Share()
share.timer = Sktimer()  # actually a Sktimer.shared() instance
share.counter = 0
share.results = {}
```

The `Share` container:
- Holds arbitrary attributes
- Auto-converts suitkaise module objects (Sktimer, etc.) to their `.shared()` versions
- Holds regular values (counter, dict, list)
- Enables sharing data between processes with automatic synchronization

---

## Architecture Decision: Completion Counters

For tracking writes and preventing read starvation, we use **two counters per attribute**:

- `pending_counts`: How many writes are currently queued (goes up and down)
- `completed_counts`: How many writes have finished (monotonically increasing)

**Why two counters?**

A single pending counter causes read starvation:
```
Worker A writes → pending = 1
Worker B reads → waits for pending == 0
Worker C writes → pending = 2
Coordinator processes A → pending = 1
Worker D writes → pending = 2
... Worker B never gets to read!
```

**How completion counters solve this:**
```
completed=10, pending=3
Read starts: target = 10 + 3 = 13 (snapshot)

Worker D writes → pending=4 (doesn't affect Read's target)

Coordinator processes 3 writes:
  → completed=11, pending=3
  → completed=12, pending=2  
  → completed=13, pending=1

Read sees completed=13 >= target=13, proceeds
Worker D's write is still pending, but Read doesn't wait for it
```

**Key insight:** Reads only wait for writes that existed when the read started.
New writes don't extend the wait time.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   Worker Process A          Worker Process B          Worker Process C      │
│   ┌──────────────┐          ┌──────────────┐          ┌──────────────┐      │
│   │ Share proxy  │          │ Share proxy  │          │ Share proxy  │      │
│   │              │          │              │          │              │      │
│   │ .timer.lap() │          │ .timer.stop()│          │ .counter += 1│      │
│   └──────┬───────┘          └──────┬───────┘          └──────┬───────┘      │
│          │                         │                         │              │
│          │    ┌────────────────────┴─────────────────────────┤              │
│          │    │                                              │              │
│          ▼    ▼                                              ▼              │
│   ┌──────────────────────────────────────────────────────────────┐          │
│   │                    Command Queue (shared memory)             │          │
│   │  FIFO: [(obj_name, method_name, args, kwargs), ...]          │          │
│   └──────────────────────────────────────────────────────────────┘          │
│          │                                                                  │
│          ▼                                                                  │
│   ┌──────────────────────────────────────────────────────────────┐          │
│   │                  COORDINATOR PROCESS                         │          │
│   │                                                              │          │
│   │   Mirror objects (local copies)                              │          │
│   │   ┌────────┐ ┌─────────┐ ┌──────────┐                        │          │
│   │   │Sktimer │ │ Counter │ │ Results  │                        │          │
│   │   └────────┘ └─────────┘ └──────────┘                        │          │
│   │                                                              │          │
│   │   1. Consume command from queue                              │          │
│   │   2. Execute on mirror object                                │          │
│   │   3. Serialize state → Source of Truth                       │          │
│   │   4. Decrement write counter for affected attrs              │          │
│   └──────────────────────────────────────────────────────────────┘          │
│          │                                                                  │
│          ▼                                                                  │
│   ┌──────────────────────────────────────────────────────────────┐          │
│   │            SOURCE OF TRUTH (Manager dict)                    │          │
│   │  { "timer": <cerial bytes>, "counter": <bytes>, ... }        │          │
│   │                                                              │          │
│   │  Workers can READ from here (after checking counters)        │          │
│   └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────┐          │
│   │          WRITE COUNTERS (atomic Values, not Manager)         │          │
│   │  { "timer.times": Value(c_int), "counter.value": ... }       │          │
│   │                                                              │          │
│   │  Incremented by workers BEFORE queueing command              │          │
│   │  Decremented by coordinator AFTER commit                     │          │
│   │  Checked by workers BEFORE reading (read barrier)            │          │
│   └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Primitives

| File | Component | Description |
|------|-----------|-------------|
| `primitives.py` | `WriteCounter` | Atomic int using `Value(c_int)` with lock |
| `primitives.py` | `CounterRegistry` | Pre-allocates counters for object attrs |
| `primitives.py` | `CommandQueue` | Wrapper around `multiprocessing.Queue` |
| `primitives.py` | `SourceOfTruth` | Manager dict with cerial serialize/deserialize |

### Phase 2: Coordinator Process

| File | Component | Description |
|------|-----------|-------------|
| `coordinator.py` | `Coordinator` | Background process consuming commands |
| `coordinator.py` | `CoordinatorLoop` | Main loop: consume → execute → commit → decrement |
| `coordinator.py` | `CoordinatorLifecycle` | Start/stop/health check |

### Phase 3: Proxy System

| File | Component | Description |
|------|-----------|-------------|
| `meta.py` | `SharedMeta` | Metadata about which attrs each method reads/writes |
| `proxy.py` | `ObjectProxy` | Wraps objects, intercepts access |
| `proxy.py` | `ReadBarrier` | Wait for counters before reading |

### Phase 4: Share Container

| File | Component | Description |
|------|-----------|-------------|
| `share.py` | `Share` | Main container, auto-wraps objects |
| `share.py` | Auto-detection | Detect suitkaise objects vs user objects |

### Phase 5: Suitkaise Object Metadata

| Location | Component | Description |
|----------|-----------|-------------|
| `timing/_int/time_ops.py` | `Sktimer._shared_meta` | Declare reads/writes for Sktimer methods |
| `circuits/api.py` | `Circuit._shared_meta` | Declare reads/writes for Circuit methods |

---

## File Structure

```
suitkaise/processing/_int/share/
├── __init__.py          # Exports
├── IMPLEMENTATION.md    # This file
├── primitives.py        # WriteCounter, CounterRegistry, CommandQueue, SourceOfTruth
├── coordinator.py       # Coordinator process
├── proxy.py             # ObjectProxy, ReadBarrier
├── meta.py              # SharedMeta
└── share.py             # Share container
```

---

## Open Questions

1. **Counter pre-allocation** — Create counters:
   - Lazily when objects are assigned
   
   **Current plan:** Lazily when objects are assigned, with synchronization.

2. **Blocking reads** — For `wait_for_clear()`:
   - `Process.listen()` uses `queue.get(timeout=timeout)` which blocks natively
   - For write counters, we're checking an atomic int, not a queue
   - Options: busy-wait with small sleeps, or use an Event the coordinator signals
   
   **Current plan:** Busy-wait with small sleep (100μs) and configurable timeout.
   Simpler than Events, and the wait should be short in practice. 

3. **Suitkaise object detection** — How to detect for auto-conversion:
   - Check for `_shared_meta` attribute on the class
   
   **Current plan:** Check for `_shared_meta` attribute. This serves double duty:
   detecting shareable objects AND providing the read/write metadata for the proxy.

4. **Coordinator failure** — If coordinator crashes:
   - Restart automatically?
   - Propagate error to all workers?
   
   **Current plan:** Both - restart + notify via error flag.

---

## `_shared_meta` Specification

Classes that support sharing define a `_shared_meta` class attribute with this structure:

```python
class Sktimer:
    _shared_meta = {
        'methods': {
            'start': {'reads': [], 'writes': ['_sessions', 'original_start_time']},
            'stop': {'reads': ['_sessions'], 'writes': ['times', '_paused_durations']},
            'lap': {'reads': ['_sessions'], 'writes': ['times', '_paused_durations']},
            'pause': {'reads': ['_sessions'], 'writes': ['_sessions']},
            'resume': {'reads': ['_sessions'], 'writes': ['_sessions']},
            'add_time': {'reads': [], 'writes': ['times', '_paused_durations']},
            'reset': {'reads': [], 'writes': ['times', '_sessions', '_paused_durations', 'original_start_time']},
            'discard': {'reads': ['_sessions'], 'writes': []},
            'get_time': {'reads': ['times'], 'writes': []},
            'percentile': {'reads': ['times'], 'writes': []},
            'get_statistics': {'reads': ['times', 'original_start_time', '_paused_durations'], 'writes': []},
            'get_stats': {'reads': ['times', 'original_start_time', '_paused_durations'], 'writes': []},
        },
        'properties': {
            'num_times': {'reads': ['times']},
            'most_recent': {'reads': ['times']},
            'result': {'reads': ['times']},
            'most_recent_index': {'reads': ['times']},
            'total_time': {'reads': ['times']},
            'total_time_paused': {'reads': ['_paused_durations']},
            'mean': {'reads': ['times']},
            'median': {'reads': ['times']},
            'slowest_index': {'reads': ['times']},
            'fastest_index': {'reads': ['times']},
            'slowest_time': {'reads': ['times']},
            'fastest_time': {'reads': ['times']},
            'min': {'reads': ['times']},
            'max': {'reads': ['times']},
            'stdev': {'reads': ['times']},
            'variance': {'reads': ['times']},
        }
    }
```

**How the proxy uses this:**

1. **Method call** → Look up `_shared_meta['methods'][method_name]['writes']`
   → Increment counter for each attr in `writes`
   → Queue command
   
2. **Property read** → Look up `_shared_meta['properties'][prop_name]['reads']`
   → Wait for counters on each attr in `reads` to reach 0
   → Read from source of truth

---

## Next Steps

1. [ ] Implement `primitives.py` with `WriteCounter`, `CounterRegistry`
2. [ ] Add basic tests for primitives
3. [ ] Implement `coordinator.py`
4. [ ] Implement `proxy.py`
5. [ ] Implement `share.py`
6. [ ] Add `_shared_meta` to Sktimer
7. [ ] Integration tests
8. [ ] Update processing `__init__.py` to export `Share`
