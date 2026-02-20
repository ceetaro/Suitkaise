/*

synced from suitkaise-docs/cucumber/why.md

*/

rows = 2
columns = 1

# 1.1

title = "Why you would use `cucumber`"

# 1.2

text = "
## TLDR

- **Serialize anything** - No more `PicklingError` ever again
- **Handles types others can't** - threads, queues, sockets, generators, asyncio, sqlite, regex matches, and more
- **Live resource reconnection** - Database connections, sockets, threads reconnect safely with your manual permission
- **Classes in `__main__`** - Multiprocessing just works, even in one-file scripts or tests
- **Circular references** - All handled automatically
- **Debug-friendly** - `debug=True` and `verbose=True` show exactly what's happening
- **Surprising speed** - Competes with `cloudpickle` on basic types while covering vastly more types. Multiple times faster than `dill`

---

`<suitkaise-api>cucumber</suitkaise-api>` is a serialization engine.

It allows you to serialize and deserialize objects across `Python` processes.

It is built for the Python environment, and isn't directly meant for use in external or cross-language serialization.

However, it can do something that no other Python serializer can do: get rid of all of your `PicklingErrors`.

If you need super fast speed for simple types, use base `pickle`. It is literally what Python originally gave us! Of course it's the fastest.

But, if you need to serialize anything else, use `<suitkaise-api>cucumber</suitkaise-api>`.

### `pickle` vs `<suitkaise-api>cucumber</suitkaise-api>` — same object, different outcomes

```python
import threading

class Worker:
    def __init__(self):
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.run)
        self.results = []
    
    def run(self):
        self.results.append("done")

worker = Worker()
```

**With `pickle`:**
```python
import pickle
pickle.dumps(worker)
# TypeError: cannot pickle '_thread.lock' objects
```

**With `cloudpickle`:**
```python
import cloudpickle
cloudpickle.dumps(worker)
# TypeError: cannot pickle '_thread.lock' objects
```

**With `<suitkaise-api>cucumber</suitkaise-api>`:**
```python
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(worker)
restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
# works. lock and thread become Reconnectors, ready to be recreated.
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>(restored)
# lock and thread are live again.
```

No errors. No workarounds. No tiptoeing around types that cause `PicklingErrors`.

### Serialize anything using `<suitkaise-api>cucumber</suitkaise-api>`

`<suitkaise-api>cucumber</suitkaise-api>` handles every type that `dill` and `cloudpickle` can handle.

It also handles many more types that are frequently used in higher level programming and parallel processing.

And, it can handle user created classes, with all of these objects!

- Handles user created classes
- Can handle generators with state
- Handles asyncio
- Handles multiprocessing and threading

#### Types only `<suitkaise-api>cucumber</suitkaise-api>` can handle

- `threading.local`
- `multiprocessing.Queue`
- `multiprocessing.Event`
- `multiprocessing.Manager`
- `queue.SimpleQueue`
- `mmap`
- `re.Match`
- `sqlite3.Connection`
- `sqlite3.Cursor`
- `socket.socket`
- `GeneratorType`
- `CoroutineType`
- `AsyncGeneratorType`
- `asyncio.Task`
- `asyncio.Future`
- `ThreadPoolExecutor`
- `ProcessPoolExecutor`
- `ContextVar`
- `Token`
- `subprocess.Popen`
- `FrameType`

#### User created classes

`<suitkaise-api>cucumber</suitkaise-api>` has a way to dissect your class instances, allowing you to serialize essentially anything.

#### Classes defined in `__main__`

`<suitkaise-api>cucumber</suitkaise-api>` can handle classes defined in `__main__`.

- Enables multiprocessing when quickly prototyping in one file
- Allows for easy testing using CodeRunners

#### Circular references

`<suitkaise-api>cucumber</suitkaise-api>` handles all circular references in your objects.

### Superior speed

`<suitkaise-api>cucumber</suitkaise-api>` is faster than `cloudpickle` and `dill` for most simple types.

Additionally, it is multiple times faster that both of them for many types.

- `NamedTemporaryFile` — 33x faster
- `TextIOWrapper` — 21x faster
- `threading.Thread` — 5x faster
- `dataclass` — 2.5x faster
- `int` — 2x faster
- And more

For a full performance breakdown, head to the performance page.

### Actually reconstructs objects

`<suitkaise-api>cucumber</suitkaise-api>` intelligently reconstructs complex objects using custom handlers.

- Easy reconnection to live resources like database connections, sockets, threads, and more while maintaining security

All you have to do after deserializing is call `<suitkaise-api>reconnect_all</suitkaise-api>()` and provide any authentication needed, and all of your live resources will be recreated automatically.

You can even start threads automatically if you use `<suitkaise-api>cucumber</suitkaise-api>`.

#### The `Reconnector` pattern — nothing else does this

When `<suitkaise-api>cucumber</suitkaise-api>` encounters a live resource (a database connection, an open socket, a running thread), it doesn't try to freeze and resume it -- that would be unsafe and often impossible. Instead, it creates a `Reconnector` object that stores the information needed to recreate the resource.

```python
import psycopg2
from <suitkaise-api>suitkaise</suitkaise-api> import <suitkaise-api>cucumber</suitkaise-api>

# serialize a live database connection
conn = psycopg2.connect(host='localhost', database='mydb', password='secret')
data = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(conn)

# deserialize it in another process
restored = <suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>deserialize</suitkaise-api>(data)
# restored.connection is a Reconnector, not a live connection yet

# reconnect with credentials (password is never stored in serialized data)
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>reconnect_all</suitkaise-api>(restored, password='secret')
# now restored.connection is a live psycopg2 connection again
```

This is a security-conscious design: authentication credentials are never stored in the serialized bytes. You provide them at reconnection time, so serialized data can be stored or transferred without leaking secrets.

No other Python serializer has this concept. Most either crash on live resources or silently produce broken objects.

Additionally, objects that don't need auth will be lazily reconstructed on first attribute access.

### Easy inspection and error analysis

`<suitkaise-api>cucumber</suitkaise-api>` creates an intermediate representation (IR) of the object using `pickle` native types before using base `pickle` to serialize it to bytes.

```python
{
    "__cucumber_type__": "<type_name>",
    "__handler__": "<handler_name>",
    "__object_id__": <id>,
    "state": {
        # object's state in IR form
    }
}
```

This allows everything to be cleanly organized and inspected.

Additionally, `<suitkaise-api>cucumber</suitkaise-api>` functions provide traceable, simple explanations of what went wrong if something fails.

```python
# all you have to do is add debug=True
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj, debug=True)
```

It also has an option to see how the object is getting serialized or reconstructed in real time with color-coded output.

```python
# all you have to do is add verbose=True
<suitkaise-api>cucumber</suitkaise-api>.<suitkaise-api>serialize</suitkaise-api>(obj, verbose=True)
```

## How do I know that `<suitkaise-api>cucumber</suitkaise-api>` can handle any user class?

`<suitkaise-api>cucumber</suitkaise-api>` can serialize any object as long as it contains supported types.

99% of Python objects only have supported types within them.

To prove to you that `<suitkaise-api>cucumber</suitkaise-api>` can handle any user class, I created a monster.

### The `WorstPossibleObject`

`WorstPossibleObject` is an object I created that would never exist in real life.

Its only goal: try and break `<suitkaise-api>cucumber</suitkaise-api>`.

It contains every type that `<suitkaise-api>cucumber</suitkaise-api>` can handle, in a super nested, circular-referenced, randomly-generated structure.

Each `WorstPossibleObject` is different from the last, and they all have ways to verify that they remain intact after being converted to and from bytes.

Not only does `<suitkaise-api>cucumber</suitkaise-api>` handle this object, but it can handle more than 100 different `WorstPossibleObjects` per second.

**By handle, I mean:**

1. Serialize it to bytes
2. I pass it to a different process
3. Deserialize it
4. Reconnect everything

It can then verify that it is the same object as it was when it got created, and that all of its complex objects within still work as expected.

This test includes a full round trip.

```text
`<suitkaise-api>serialize</suitkaise-api>()` → another process → `<suitkaise-api>deserialize</suitkaise-api>()` → `<suitkaise-api>reconnect_all</suitkaise-api>()` → verify → `<suitkaise-api>serialize</suitkaise-api>()` → back to original process → `<suitkaise-api>deserialize</suitkaise-api>()` → `<suitkaise-api>reconnect_all</suitkaise-api>()` → verify
```

To see the full `WorstPossibleObject` code, head to the worst possible object page. Have fun!

## Where `<suitkaise-api>cucumber</suitkaise-api>` sits in the landscape

`<suitkaise-api>cucumber</suitkaise-api>`'s real competitor is `dill`, not `cloudpickle`. Both `<suitkaise-api>cucumber</suitkaise-api>` and `dill` prioritize type coverage over raw speed. The difference: `<suitkaise-api>cucumber</suitkaise-api>` far outclasses `dill` on speed while exceeding its type coverage.

The fact that `<suitkaise-api>cucumber</suitkaise-api>` also competes with `cloudpickle` on speed -- despite covering vastly more types -- is the surprising part. `cloudpickle` is designed for speed with limited types. `<suitkaise-api>cucumber</suitkaise-api>` is designed for coverage and still keeps up.

- Need raw speed on simple types? Use base `pickle`.
- Need slightly more type coverage with great speed? `cloudpickle` is solid.
- Need everything to just work, with no `PicklingError` ever, and still competitive speed? That's `<suitkaise-api>cucumber</suitkaise-api>`.

For a full performance breakdown, head to the performance page.

## Works with the rest of `<suitkaise-api>suitkaise</suitkaise-api>`

`<suitkaise-api>cucumber</suitkaise-api>` is the serialization backbone of the `<suitkaise-api>suitkaise</suitkaise-api>` ecosystem.

- `<suitkaise-api>processing</suitkaise-api>` uses `<suitkaise-api>cucumber</suitkaise-api>` by default for all cross-process communication. Every `<suitkaise-api>Skprocess</suitkaise-api>`, every `<suitkaise-api>Pool</suitkaise-api>.<suitkaise-api>map</suitkaise-api>`, every `<suitkaise-api>Share</suitkaise-api>` operation goes through `<suitkaise-api>cucumber</suitkaise-api>`. You never think about serialization.
- `<suitkaise-api>@autoreconnect</suitkaise-api>` from `<suitkaise-api>processing</suitkaise-api>` builds on the `Reconnector` pattern to automatically reconnect live resources (like database connections) when they cross process boundaries.
- `<suitkaise-api>Share</suitkaise-api>` relies on `<suitkaise-api>cucumber</suitkaise-api>` to serialize any object you assign to it. This is what makes `share.anything = any_object` possible.
- All `<suitkaise-api>suitkaise</suitkaise-api>` objects (`<suitkaise-api>Sktimer</suitkaise-api>`, `<suitkaise-api>Circuit</suitkaise-api>`, `<suitkaise-api>Skpath</suitkaise-api>`, etc.) are designed to serialize cleanly through `<suitkaise-api>cucumber</suitkaise-api>`.
"
