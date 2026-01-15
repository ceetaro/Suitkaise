# Supported Types

Complete list of all Python types that `cerial` can serialize and deserialize.

## All `suitkaise` object types

- `Sktimer`
- `TimeThis`
- `Circuit`
- `BreakingCircuit`
- `Skpath`
- `CustomRoot`
- `Skprocess`
- `Pool`
- `Share`
- `ProcessTimers`
- all `suitkaise` error classes

---

## Primitives

These types are handled directly by `pickle` — `cerial` passes them through.

- `None`
- `bool`
- `int`
- `float`
- `complex`
- `str`
- `bytes`
- `bytearray`
- `Ellipsis`
- `NotImplemented`

---

## Collections

Cerial handles the container; contents are recursively serialized.

- `list`
- `tuple`
- `dict`
- `set`
- `frozenset`
- `range`
- `slice`
- `collections.deque`
- `collections.Counter`
- `collections.OrderedDict`
- `collections.defaultdict`
- `collections.ChainMap`
- `collections.namedtuple`

---

## Datetime

- `datetime.datetime`
- `datetime.date`
- `datetime.time`
- `datetime.timedelta`
- `datetime.timezone`

---

## Numeric

- `decimal.Decimal`
- `fractions.Fraction`

---

## Paths and UUIDs

- `uuid.UUID`
- `pathlib.Path`
- `pathlib.PurePath`
- `pathlib.PosixPath`
- `pathlib.WindowsPath`

---

## Logging

- `logging.Logger`
- `logging.StreamHandler`
- `logging.FileHandler`
- `logging.Formatter`

---

## Threading

- `threading.Lock`
- `threading.RLock`
- `threading.Semaphore`
- `threading.BoundedSemaphore`
- `threading.Barrier`
- `threading.Condition`
- `threading.Event`
- `threading.Thread`
- `threading.local`

---

## Multiprocessing

- `multiprocessing.Queue`
- `multiprocessing.Event`
- `multiprocessing.Pipe`
- `multiprocessing.Manager`
- `multiprocessing.shared_memory.SharedMemory`

---

## Queues

- `queue.Queue`
- `queue.LifoQueue`
- `queue.PriorityQueue`
- `queue.SimpleQueue`

---

## File I/O

- `io.TextIOWrapper`
- `io.BufferedReader`
- `io.BufferedWriter`
- `io.FileIO`
- `io.StringIO`
- `io.BytesIO`
- `tempfile.NamedTemporaryFile`
- `tempfile.SpooledTemporaryFile`
- `mmap.mmap`

---

## Regular Expressions

- `re.Pattern`
- `re.Match`

---

## Database

- `sqlite3.Connection`
- `sqlite3.Cursor`

---

## Network

- `requests.Session`
- `socket.socket`

---

## Functions and Methods

- `types.FunctionType`
- Lambda functions
- `functools.partial`
- `types.MethodType`
- `staticmethod`
- `classmethod`

---

## Generators and Iterators

- `types.GeneratorType`
- `range_iterator`
- `enumerate`
- `zip`
- `map`
- `filter`

---

## Async

- `types.CoroutineType`
- `types.AsyncGeneratorType`
- `asyncio.Task`
- `asyncio.Future`
- `concurrent.futures.Future`

---

## Executors

- `concurrent.futures.ThreadPoolExecutor`
- `concurrent.futures.ProcessPoolExecutor`

---

## Weak References

- `weakref.ref`
- `weakref.WeakValueDictionary`
- `weakref.WeakKeyDictionary`

---

## Enums

- `enum.Enum`
- `enum.IntEnum`
- `enum.Flag`
- `enum.IntFlag`

---

## Context Variables

- `contextvars.ContextVar`
- `contextvars.Token`

---

## Context Managers

- `contextlib.contextmanager` decorated functions
- Objects with `__enter__` / `__exit__`

---

## Subprocess

- `subprocess.Popen`
- `subprocess.CompletedProcess`

---

## Advanced Python Internals

- `types.CodeType`
- `types.FrameType`
- `property`
- Custom descriptors
- File descriptors

---

## Modules

- `types.ModuleType`
- OS pipes

---

## Typing

- `typing.NamedTuple`
- `typing.TypedDict`

---

## Classes

- Class objects (`type`)
- Class instances
- `@dataclass` classes
- `__slots__` classes
- `__dict__` classes
- classes with both `__dict__` and `__slots__`

---

## Circular References

Cerial handles circular references in:

- Lists, dicts, sets, tuples
- Class instances
- Any nested combination

```python
a = []
a.append(a)  # self-referential list

obj = Node(1)
obj.next = obj  # self-referential object

# both serialize correctly
```

---

## Not Supported

- C extension objects without `__reduce__`
Reason: no Python state to extract

- Live network connections (mid-request)
Reason: state is external

- Running threads/processes
Reason: cannot capture execution state

- Memory views of external buffers
Reason: buffer not owned

- `ctypes` pointers
Reason: raw memory addresses

