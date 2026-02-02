# Why you would use `cucumber`

`cucumber` is a serialization engine.

It allows you to serialize and deserialize objects across `Python` processes.

It is built for the Python environment, and isn't directly meant for use in external or cross-language serialization.

However, it can do something that no other Python serializer can do: get rid of all of your `PicklingErrors`.

If you need super fast speed for simple types, use base `pickle`. It is literally what Python originally gave us! Of course it's the fastest.

But, if you need to serialize anything else, use `cucumber`.

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