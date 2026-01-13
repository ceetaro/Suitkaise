


idea for shared state patterns:

instances of Share in each process

goes into a shared memory queue that goes into:

1 process.

this process mirrors calls from every other process as they come in

and then this commits to the real shared memory

which every other process can pull from



for reads, we need to know if the shared memory will be stale or not.

so we send flags quickly that say if the attribute will change before your read was called

each function could do somehting like auto detecting reads and writes and adding flags for each attr that could get read

so a function that needs to read would know if an attr could change

we create flags with attr name

then, reads to those attrs will be blocked until flags are cleared


---

shared state technical concepts (ideas, not finalized):

coordinator process
- single process that handles all writes
- runs a loop consuming from command queue
- holds local mirror copies of all shared objects
- executes methods on mirror objects
- commits updated state to source of truth after each command
- clears write flags after committing

command queue
- multiprocessing queue in shared memory
- entries: (object_name, method_name, args, kwargs)
- FIFO ordering
- all processes push to this queue
- only coordinator consumes from it

source of truth
- multiprocessing Manager dict
- keyed by object name
- values are cerial-serialized object state
- only coordinator writes to this
- all processes can read from it (coordinator reads from itself)

write flags
- NOT a Manager dict (too slow, RPC overhead on every access)
- use atomic primitives in shared memory instead
- multiprocessing.Value or shared_memory for raw bytes
- one flag per writable attr, pre-allocated at setup
- direct memory read for checking (~10-50ns vs ~50-100μs for Manager dict)
- keyed by "object_name.attr_name" in local lookup dict
- set to True when a write to that attr is queued
- cleared by coordinator after commit
- used by read barrier to block stale reads

atomic flag options
- multiprocessing.Value(ctypes.c_bool, False) - simple, but must exist before fork
- multiprocessing.shared_memory - raw bytes, any process can open by name
- lookup is local dict (fast), flag itself is shared memory (also fast)

flag pre-allocation
- at shared state setup, determine all writable attrs for the object
- create one atomic flag per attr
- writable attrs known from metadata attached to methods
- if not known, could fall back to flagging all attrs or analyzing code

read barrier
- before reading an attr, check if any flags exist for attrs it depends on
- if flags exist, wait until they clear
- then read from source of truth
- ensures reads never see stale data

proxy wrapper
- wraps user objects automatically when assigned to shared state
- intercepts __getattr__ and __setattr__
- for method calls: set flags, queue command
- for property reads: wait for flags, read from source of truth
- for property writes: set flag, queue command
- user code unchanged, proxy handles sync

nested object handling
- nested objects are part of parent's state
- accessing shared.stats.timer returns a nested proxy
- nested proxy syncs parent object (shared.stats), not just the nested attr
- entire parent state is the unit of sharing

attr read/write detection
- each method needs to declare or auto-detect which attrs it reads/writes
- for suitkaise objects: define _shared_meta dict with reads/writes per method
- for user objects: use AST analysis on method source to find self.attr assignments (writes) and self.attr accesses (reads)
- alternatively: execute method once and track attr access via __setattr__/__getattr__ overrides

coordinator lifecycle
- started automatically when shared state is created
- runs in background process
- stops when shared state is garbage collected or explicitly closed
- needs heartbeat/health check if coordinator crashes

blocking vs non-blocking writes
- default: non-blocking (fire and forget)
- method call queues command and returns immediately
- if return value needed: use response queue, caller waits for result
- optional blocking mode: wait for coordinator ack before returning






internal pieces (ideas, not finalized):

function wrapping
- convert functions to objects that store metadata
- needs: original function, function name, reads/writes info
- possibly: cached async version

async version options
- to_thread(): runs sync function in thread pool, ~100μs overhead, no code changes needed
- (manual implementation for suitkaise objects to increase speed)

method binding
- if wrapping methods, need to handle self binding
- descriptor protocol (__get__) can bind instance when accessed
- or handle at call time