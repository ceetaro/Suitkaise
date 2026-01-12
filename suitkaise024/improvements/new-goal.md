1. everything needs have an async version

how?

different naming, same module

ex. `Timer` vs `TimerAsync`

or:

`Timer` vs `Async.Timer` or `Timer` vs `Timer.Async`

this will be done manually, not with to_thread()

2. everything needs to be shareable in shared memory/shared state patterns

pattern below

3. everything needs to be serializable with cerial (already done)

- functions need to serialize faster
- simple classes need to serialize faster



5. other idea for shared state patterns:

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




Skf: wrapped function objects


1. store changing attrs on creation for shared state

2. can call function normally or async

3. so, supports shared state and async with a simple conversion

4. easy decorator

```python
@skf()
def my_function():

    # Your code here
    return result


# turns into...

class Skfunction:

    def __init__(self, func):

        # store changing attrs here...

        # calculate async version here...


# regular version
def my_function():

    return result


# async version

async def my_function():

    # Your code here
    await result


# calling 
result = my_function()

# or
result = await my_function()

```


---

skf internal pieces (ideas, not finalized):

function wrapping
- convert functions to objects that store metadata
- needs: original function, function name, reads/writes info
- possibly: cached async version

async version options
- to_thread(): runs sync function in thread pool, ~100μs overhead, no code changes needed

serialization for shared state
- don't serialize function code (slow)
- just serialize reference: (object_name, method_name, args, kwargs)
- coordinator looks up method by name
- function code already exists on coordinator side

method binding
- if wrapping methods, need to handle self binding
- descriptor protocol (__get__) can bind instance when accessed
- or handle at call time



---

function serialization (cerial improvement):

reference vs full serialization
- goal: serialize functions faster by using references when possible
- reference: just store module path + qualname, look up on other end
- full: serialize bytecode, globals, closures, etc (slow but complete)

when to use reference
- function must be guaranteed to be exactly the same on both ends
- module-level functions: yes
- class methods: yes
- both sides have the same codebase/module installed

when to fall back to full serialization
- lambdas: anonymous, no unique name to look up
- closures: depend on captured variables from outer scope
- dynamically created functions: runtime generated, don't exist in module
- anything where lookup might give a different function

the check
- has __module__ and __qualname__
- qualname doesn't contain '<lambda>' or '<locals>'
- can actually look it up and get the same object back
- if any of these fail, fall back to full serialization

performance difference
- reference: ~50-100 bytes, ~1-10μs to serialize
- full: ~1-10KB, ~1-10ms to serialize
- 100-1000x faster with references

implementation
- try reference first
- if can_use_reference() fails, fall back to full
- deserialize by importing module and walking qualname

