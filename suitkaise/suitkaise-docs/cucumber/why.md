# Why you would use `cucumber`

## TLDR

- **Serialize anything** - No more `PicklingError` ever again
- **Handles types others can't** - threads, queues, sockets, generators, asyncio, sqlite, regex matches, and more
- **Live resource reconnection** - Database connections, sockets, threads reconnect safely with your manual permission
- **Classes in `__main__`** - Multiprocessing just works, even in one-file scripts or tests
- **Circular references** - All handled automatically
- **Debug-friendly** - `debug=True` and `verbose=True` show exactly what's happening
- **Surprising speed** - Competes with `cloudpickle` on basic types while covering vastly more types. Multiple times faster than `dill`

---

`cucumber` is a serialization engine.

It allows you to serialize and deserialize objects across `Python` processes.

It is built for the Python environment, and isn't directly meant for use in external or cross-language serialization.

However, it can do something that no other Python serializer can do: get rid of all of your `PicklingErrors`.

If you need super fast speed for simple types, use base `pickle`. It is literally what Python originally gave us! Of course it's the fastest.

But, if you need to serialize anything else, use `cucumber`.

### `pickle` vs `cucumber` — same object, different outcomes

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

With `pickle`:
```python
import pickle
pickle.dumps(worker)
# TypeError: cannot pickle '_thread.lock' objects
```

With `cloudpickle`:
```python
import cloudpickle
cloudpickle.dumps(worker)
# TypeError: cannot pickle '_thread.lock' objects
```

With `cucumber`:
```python
from suitkaise import cucumber
data = cucumber.serialize(worker)
restored = cucumber.deserialize(data)
# works. lock and thread become Reconnectors, ready to be recreated.
cucumber.reconnect_all(restored)
# lock and thread are live again.
```

No errors. No workarounds. No tiptoeing around types that cause `PicklingError`s.

### Serialize anything using `cucumber`

`cucumber` handles every type that `dill` and `cloudpickle` can handle.

It also handles many more types that are frequently used in higher level programming and parallel processing.

And, it can handle user created classes, with all of these objects!

- handles user created classes
- can handle generators with state
- handles asyncio
- handles multiprocessing and threading

#### Types only `cucumber` can handle

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

`cucumber` has a way to dissect your class instances, allowing you to serialize essentially anything.

#### Classes defined in `__main__`

`cucumber` can handle classes defined in `__main__`.

- enables multiprocessing when quickly prototyping in one file
- allows for easy testing using CodeRunners

#### Circular references

`cucumber` handles all circular references in your objects.

### Superior speed

`cucumber` is faster than `cloudpickle` and `dill` for most simple types.

Additionally, it is multiple times faster that both of them for many types.

- `NamedTemporaryFile` — 33x faster
- `TextIOWrapper` — 21x faster
- `threading.Thread` — 5x faster
- `dataclass` — 2.5x faster
- `int` — 2x faster
- and more

For a full performance breakdown, head to the performance page.

### Actually reconstructs objects

`cucumber` intelligently reconstructs complex objects using custom handlers.

- easy reconnection to live resources like database connections, sockets, threads, and more while maintaining security

All you have to do after deserializing is call `reconnect_all()` and provide any authentication needed, and all of your live resources will be recreated automatically.

You can even start threads automatically if you use `cucumber`.

#### The `Reconnector` pattern — nothing else does this

When `cucumber` encounters a live resource (a database connection, an open socket, a running thread), it doesn't try to freeze and resume it -- that would be unsafe and often impossible. Instead, it creates a `Reconnector` object that stores the information needed to recreate the resource.

```python
import psycopg2
from suitkaise import cucumber

# serialize a live database connection
conn = psycopg2.connect(host='localhost', database='mydb', password='secret')
data = cucumber.serialize(conn)

# deserialize it in another process
restored = cucumber.deserialize(data)
# restored.connection is a Reconnector, not a live connection yet

# reconnect with credentials (password is never stored in serialized data)
cucumber.reconnect_all(restored, password='secret')
# now restored.connection is a live psycopg2 connection again
```

This is a security-conscious design: authentication credentials are never stored in the serialized bytes. You provide them at reconnection time, so serialized data can be stored or transferred without leaking secrets.

No other Python serializer has this concept. Most either crash on live resources or silently produce broken objects.

Additionally, objects that don't need auth will be lazily reconstructed on first attribute access.

### Easy inspection and error analysis

`cucumber` creates an intermediate representation (IR) of the object using `pickle` native types before using base `pickle` to serialize it to bytes.

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

Additionally, `cucumber` functions provide traceable, simple explanations of what went wrong if something fails.

```python
# all you have to do is add debug=True
cucumber.serialize(obj, debug=True)
```

It also has an option to see how the object is getting serialized or reconstructed in real time with color-coded output.

```python
# all you have to do is add verbose=True
cucumber.serialize(obj, verbose=True)
```

## How do I know that `cucumber` can handle any user class?

`cucumber` can serialize any object as long as it contains supported types.

99% of Python objects only have supported types within them.

To prove to you that `cucumber` can handle any user class, I created a monster.

### The `WorstPossibleObject`

`WorstPossibleObject` is an object I created that would never exist in real life.

Its only goal: try and break `cucumber`.

It contains every type that `cucumber` can handle, in a super nested, circular-referenced, randomly-generated structure.

Each `WorstPossibleObject` is different from the last, and they all have ways to verify that they remain intact after being converted to and from bytes.

Not only does `cucumber` handle this object, but it can handle more than 100 different `WorstPossibleObjects` per second.

By handle, I mean:

1. Serialize it to bytes
2. I pass it to a different process
3. Deserialize it
3. Reconnect everything

It can then verify that it is the same object as it was when it got created, and that all of its complex objects within still work as expected.

Run the WorstPossibleObject round‑trip test:

```bash
python tests/cucumber/test_worst_possible_object.py
```
This test includes a full round trip.

```
`serialize()` → another process → `deserialize()` → `reconnect_all()` → verify → `serialize()` → back to original process → `deserialize()` → `reconnect_all()` → verify
```

To see the full `WorstPossibleObject` code, head to the worst possible object page. Have fun!

## Where `cucumber` sits in the landscape

`cucumber`'s real competitor is `dill`, not `cloudpickle`. Both `cucumber` and `dill` prioritize type coverage over raw speed. The difference: `cucumber` far outclasses `dill` on speed while exceeding its type coverage.

The fact that `cucumber` also competes with `cloudpickle` on speed -- despite covering vastly more types -- is the surprising part. `cloudpickle` is designed for speed with limited types. `cucumber` is designed for coverage and still keeps up.

- Need raw speed on simple types? Use base `pickle`.
- Need slightly more type coverage with great speed? `cloudpickle` is solid.
- Need everything to just work, with no `PicklingError` ever, and still competitive speed? That's `cucumber`.

For a full performance breakdown, head to the performance page.

## Works with the rest of `suitkaise`

`cucumber` is the serialization backbone of the `suitkaise` ecosystem.

- `processing` uses `cucumber` by default for all cross-process communication. Every `Skprocess`, every `Pool.map`, every `Share` operation goes through `cucumber`. You never think about serialization.
- `@autoreconnect` from `processing` builds on the `Reconnector` pattern to automatically reconnect live resources (like database connections) when they cross process boundaries.
- `Share` relies on `cucumber` to serialize any object you assign to it. This is what makes `share.anything = any_object` possible.
- All `suitkaise` objects (`Sktimer`, `Circuit`, `Skpath`, etc.) are designed to serialize cleanly through `cucumber`.