# `cucumber` performance

Note from future me: I made some slight changes to how non module level functions, weakrefs, and enums are handled. This may change benchmark results, but the changes should be insignificant (less than 33% slower).

Here are the performance benchmarks for `cucumber` compared to other serialization libraries.

These benchmarks were run on a 2024 MacBook Pro M3 with 32GB of RAM.

Windows users: Python is significantly slower on Windows than on macOS, so benchmarks across the board will be slower on Windows with similar hardware specs.

Note: `cucumber` is tuned in order to cover the most types possible with as much consistency as possible. Speed is very competitive, but the data size and resource overhead is noticeably higher than other libraries due to the IR and extra complexity.

To run the benchmarks yourself, run the following command:
```bash
python -m tests.cucumber.run_all_benchmarks
```

## Types only `cucumber` can handle

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

### `suitkaise` specific types that only `cucumber` can handle

- `Pool`
- `Share`

## `cucumber` vs `pickle`

`cucumber` actually handles `requests.Session` 1.45x faster than base `pickle`.

## Primitive type comparison (excluding base `pickle`)

`bool`: `cucumber` is fastest
- `cucumber` 6.4µs 
- `cloudpickle` 10.4µs 
- `dill` 55.1µs

`int`: `cucumber` is fastest
- `cucumber` 1.2µs
- `cloudpickle` 2.6µs
- `dill` 10.7µs

`float`: `cucumber` is fastest
- `cucumber` 1.6µs
- `cloudpickle` 1.7µs
- `dill` 8.5µs

`complex`: `cucumber` is fastest
- `cucumber` 5.8µs
- `cloudpickle` 14.2µs
- `dill` 41.8µs

`str`: `cucumber` is fastest
- `cucumber` 1.0µs
- `cloudpickle` 1.5µs
- `dill` 7.3µs

`bytes`: `cucumber` is fastest
- `cucumber` 0.9µs
- `cloudpickle` 1.4µs
- `dill` 7.2µs

`bytearray`: `cloudpickle` is fastest
- `cloudpickle` 2.0µs
- `cucumber` 2.5µs
- `dill` 24.0µs

This is mainly because `cucumber` fast paths basic types directly to the IR instead of handling them normally.

## `cucumber` vs `cloudpickle` vs `dill`

### Types `cucumber` handles the fastest (>1.33x faster)

Here is a table of types that `cucumber` handles the fastest (>1.33x faster) compared to `cloudpickle` and `dill`, and how much faster `cucumber` is than the second fastest serializer.

If a 2nd place speed is less than 1.33x faster than `cucumber`, we consider this not significant enough to list, as times in microseconds (µs) are very small and can easily be affected by external factors.

────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  Type                                  speed with `cucumber`              How much faster than 2nd place?
────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  `NamedTemporaryFile`                  26.6µs                           33.62x (`dill`)
  `TextIOWrapper`                       46.0µs                           21.83x (`dill`)
  `queue.PriorityQueue`                 12.6µs                           7.49x (`dill`)
  `typing.NamedTuple`                   4.9µs                            6.98x (`dill`)
  `queue.LifoQueue`                     14.9µs                           6.95x (`dill`)
  `StreamHandler`                       9.3µs                            6.92x (`dill`)
  `threading.Barrier`                   11.0µs                           6.43x (`dill`)
  `threading.Event`                     9.6µs                            5.88x (`dill`)
  `queue.Queue`                         23.2µs                           5.76x (`dill`)
  `namedtuple`                          5.7µs                            5.51x (`dill`)
  `threading.Thread`                    57.0µs                           5.33x (`dill`)
  `FileHandler`                         19.1µs                           4.60x (`dill`)
  `dataclass`                           89.6µs                           2.65x (`cloudpickle`)
  `map`                                 14.0µs                           2.55x (`cloudpickle`)
  `filter`                              14.5µs                           2.51x (`cloudpickle`)
  `complex`                             5.8µs                            2.45x (`cloudpickle`)
  `int`                                 1.2µs                            2.17x (`cloudpickle`)
  `defaultdict`                         4.9µs                            2.02x (`cloudpickle`)
  `IntEnum`                             2.5µs                            2.00x (`cloudpickle`)
  `IntFlag`                             2.4µs                            1.92x (`cloudpickle`)
  `slots+dict class`                    31.0µs                           1.80x (`cloudpickle`)
  `threading.Semaphore`                 0.8µs                            1.75x (`cloudpickle`)
  `slice`                               3.3µs                            1.73x (`cloudpickle`)
  `threading.BoundedSemaphore`          0.7µs                            1.71x (`cloudpickle`)
  `classmethod`                         16.6µs                           1.70x (`cloudpickle`)
  `bool`                                6.4µs                            1.62x (`cloudpickle`)
  `threading.RLock`                     0.8µs                            1.62x (`cloudpickle`)
  `bytes`                               0.9µs                            1.56x (`cloudpickle`)
  `slots class`                         37.1µs                           1.51x (`cloudpickle`)
  `str`                                 1.0µs                            1.50x (`cloudpickle`)
  `range`                               4.2µs                            1.40x (`cloudpickle`)
  `FunctionType`                        49.1µs                           1.37x (`dill`)




### Types `cloudpickle` handles the fastest (>1.33x faster)

`cloudpickle` is great for fast handling of simple classes, but it has a much smaller list of supported types than even `dill`.

───────────────────────────────────────────────────────────────────────────────────────────────────────────────
  Type                                  speed with `cloudpickle`         How much faster than 2nd place?
───────────────────────────────────────────────────────────────────────────────────────────────────────────────
  `Skclass`                             9.8µs                            5.24x (`cucumber`)
  `multiprocessing.Pipe`                6.6µs                            4.77x (`dill`)
  `SQLiteReconnector`                   5.1µs                            4.06x (`cucumber`)
  `CodeType`                            9.4µs                            3.82x (`cucumber`)
  `PurePath`                            3.8µs                            3.82x (`dill`)
  `SpooledTemporaryFile`                9.9µs                            3.69x (`cucumber`)
  `Logger`                              4.0µs                            3.65x (`dill`)
  `SharedMemory`                        12.0µs                           3.61x (`dill`)
  `list`                                1.7µs                            3.29x (`cucumber`)
  `CompletedProcess`                    5.8µs                            3.19x (`cucumber`)
  `Enum`                                6.4µs                            2.95x (`dill`)
  `re.Pattern`                          6.4µs                            2.80x (`cucumber`)
  `tuple`                               1.5µs                            2.73x (`cucumber`)
  `Flag`                                5.1µs                            2.65x (`cucumber`)
  `Skpath`                              8.5µs                            2.65x (`cucumber`)
  `ModuleType`                          7.2µs                            2.58x (`dill`)
  `Class object`                        3.3µs                            2.58x (`cucumber`)
  `set`                                 1.4µs                            2.50x (`cucumber`)
  `OS pipes`                            1.7µs                            2.47x (`cucumber`)
  `functools.partial`                   22.4µs                           2.46x (`cucumber`)
  `date`                                4.0µs                            2.42x (`cucumber`)
  `Skfunction`                          34.4µs                           2.40x (`cucumber`)
  `frozenset`                           1.3µs                            2.31x (`cucumber`)
  `typing.TypedDict`                    2.0µs                            2.25x (`cucumber`)
  `enumerate`                           7.5µs                            2.23x (`cucumber`)
  `dict`                                1.8µs                            2.06x (`cucumber`)
  `timezone`                            6.6µs                            1.98x (`cucumber`)
  `StringIO`                            5.8µs                            1.90x (`cucumber`)
  `deque`                               5.7µs                            1.84x (`cucumber`)
  `ErrorHandlerError`                   4.1µs                            1.78x (`cucumber`)
  `PipeReconnector`                     6.2µs                            1.77x (`cucumber`)
  `Path`                                4.0µs                            1.75x (`cucumber`)
  `Formatter`                           7.3µs                            1.74x (`cucumber`)
  `ProcessTimeoutError`                 4.1µs                            1.73x (`cucumber`)
  `BytesIO`                             6.3µs                            1.73x (`cucumber`)
  `FunctionTimeoutError`                3.7µs                            1.70x (`cucumber`)
  `UUID`                                4.8µs                            1.69x (`cucumber`)
  `CustomRoot`                          4.7µs                            1.68x (`cucumber`)
  `Fraction`                            4.2µs                            1.67x (`cucumber`)
  `DeserializationError`                4.2µs                            1.67x (`cucumber`)
  `ProcessError`                        6.2µs                            1.66x (`cucumber`)
  `range_iterator`                      8.5µs                            1.65x (`cucumber`)
  `Class instance`                      4.2µs                            1.62x (`cucumber`)
  `zip`                                 9.2µs                            1.60x (`cucumber`)
  `PreRunError`                         5.0µs                            1.58x (`cucumber`)
  `PathDetectionError`                  4.1µs                            1.54x (`cucumber`)
  `ResultTimeoutError`                  4.0µs                            1.48x (`cucumber`)
  `PostRunError`                        4.2µs                            1.45x (`cucumber`)
  `ResultError`                         4.1µs                            1.44x (`cucumber`)
  `SkModifierError`                     3.9µs                            1.44x (`cucumber`)
  `timedelta`                           3.7µs                            1.43x (`cucumber`)
  `PosixPath`                           3.5µs                            1.43x (`cucumber`)
  `Decimal`                             4.6µs                            1.41x (`cucumber`)
  `OnFinishError`                       4.1µs                            1.37x (`cucumber`)
  `time`                                3.7µs                            1.35x (`cucumber`)


### Types `dill` handles the fastest (>1.33x faster)

`dill` handles more types than `cloudpickle`, but it pretty slow.

`cucumber` handles more types than `dill` and is almost always faster.

───────────────────────────────────────────────────────────────────────────────────────────────────────────────
  Type                                  speed with `dill`                How much faster than 2nd place?
───────────────────────────────────────────────────────────────────────────────────────────────────────────────
  `BufferedReader`                      28.7µs                           3.19x (`cucumber`)
  `BufferedWriter`                      25.5µs                           1.84x (`cucumber`)
  `FileIO`                              24.7µs                           1.81x (`cucumber`)

```

## All Benchmarks

```
────────────────────────────────────────────────────────────────────────────────────────────────────────────────
                                   Supported Types Compatibility Benchmarks                                   
────────────────────────────────────────────────────────────────────────────────────────────────────────────────

  Type                           cucumber             pickle             dill               cloudpickle
────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  bool                           6.4µs              0.8µs              55.1µs             10.4µs            
  int                            1.2µs              0.3µs              10.7µs             2.6µs             
  float                          1.6µs              0.3µs              8.5µs              1.7µs             
  complex                        5.8µs              1.1µs              41.8µs             14.2µs            
  str                            1.0µs              0.3µs              7.3µs              1.5µs             
  bytes                          0.9µs              0.3µs              7.2µs              1.4µs             
  bytearray                      2.5µs              2.3µs              24.0µs             2.0µs             
  Ellipsis                       5.6µs              1.8µs              25.0µs             6.6µs             
  NotImplemented                 5.0µs              1.4µs              15.8µs             4.1µs             
  list                           5.6µs              0.3µs              10.0µs             1.7µs             
  tuple                          4.1µs              0.3µs              6.8µs              1.5µs             
  dict                           3.7µs              0.3µs              13.5µs             1.8µs             
  set                            3.5µs              0.4µs              6.7µs              1.4µs             
  frozenset                      3.0µs              0.6µs              5.8µs              1.3µs             
  range                          4.2µs              1.2µs              14.1µs             5.9µs             
  slice                          3.3µs              1.0µs              20.0µs             5.7µs             
  deque                          10.5µs             1.6µs              21.2µs             5.7µs             
  Counter                        4.7µs              1.0µs              24.2µs             4.8µs             
  OrderedDict                    5.5µs              1.6µs              17.0µs             5.7µs             
  defaultdict                    4.9µs              1.6µs              28.0µs             9.9µs             
  ChainMap                       7.0µs              1.4µs              27.4µs             5.5µs             
  namedtuple                     5.7µs              fail               31.4µs             376.0µs           
  datetime                       9.0µs              1.7µs              28.8µs             7.1µs             
  date                           9.7µs              1.6µs              20.2µs             4.0µs             
  time                           5.0µs              1.1µs              13.9µs             3.7µs             
  timedelta                      5.3µs              0.9µs              15.0µs             3.7µs             
  timezone                       13.1µs             2.2µs              23.7µs             6.6µs             
  Decimal                        6.5µs              1.3µs              13.7µs             4.6µs             
  Fraction                       7.0µs              1.0µs              12.9µs             4.2µs             
  UUID                           8.1µs              1.6µs              21.1µs             4.8µs             
  Path                           7.0µs              1.1µs              19.3µs             4.0µs             
  PurePath                       24.2µs             1.8µs              14.5µs             3.8µs             
  PosixPath                      5.0µs              1.0µs              13.0µs             3.5µs             
  Logger                         15.7µs             5.2µs              14.6µs             4.0µs             
  StreamHandler                  9.3µs              fail               64.4µs             fail              
  FileHandler                    19.1µs             fail               87.9µs             fail              
  Formatter                      12.7µs             8.5µs              36.2µs             7.3µs             
  threading.Lock                 1.3µs              0.3µs              5.3µs              1.6µs             
  threading.RLock                0.8µs              0.3µs              4.0µs              1.3µs             
  threading.Semaphore            0.8µs              0.3µs              4.2µs              1.4µs             
  threading.BoundedSemaphore     0.7µs              0.2µs              3.7µs              1.2µs             
  threading.Barrier              11.0µs             fail               70.7µs             fail              
  threading.Condition            1.7µs              0.3µs              5.0µs              1.5µs             
  threading.Event                9.6µs              fail               56.4µs             fail              
  threading.Thread               57.0µs             fail               303.9µs            fail              
  threading.local                17.0µs             fail               fail               fail              
  multiprocessing.Queue          14.0µs             fail               fail               fail              
  multiprocessing.Event          35.1µs             fail               fail               fail              
  multiprocessing.Pipe           44.6µs             3.4µs              31.5µs             6.6µs             
  multiprocessing.Manager        190.5µs            fail               fail               fail              
  SharedMemory                   52.8µs             5.9µs              43.3µs             12.0µs            
  queue.Queue                    23.2µs             fail               133.7µs            fail              
  queue.LifoQueue                14.9µs             fail               103.6µs            fail              
  queue.PriorityQueue            12.6µs             fail               94.4µs             fail              
  queue.SimpleQueue              13.1µs             fail               fail               fail              
  TextIOWrapper                  46.0µs             fail               1004.0µs           fail              
  BufferedReader                 91.5µs             fail               28.7µs             fail              
  BufferedWriter                 47.0µs             fail               25.5µs             fail              
  FileIO                         44.7µs             fail               24.7µs             fail              
  StringIO                       11.0µs             3.0µs              18.8µs             5.8µs             
  BytesIO                        10.9µs             2.0µs              17.5µs             6.3µs             
  NamedTemporaryFile             26.6µs             fail               894.3µs            fail              
  SpooledTemporaryFile           36.5µs             6.0µs              49.2µs             9.9µs             
  mmap                           42.1µs             fail               fail               fail              
  re.Pattern                     17.9µs             2.6µs              24.3µs             6.4µs             
  re.Match                       26.7µs             fail               fail               fail              
  sqlite3.Connection             82.3µs             fail               fail               fail              
  sqlite3.Cursor                 41.6µs             fail               fail               fail              
  requests.Session               29.5µs             42.7µs             349.4µs            39.0µs            
  socket.socket                  43.4µs             fail               fail               fail              
  FunctionType                   49.1µs             fail               67.4µs             75.8µs            
  lambda                         44.5µs             fail               66.7µs             38.5µs            
  functools.partial              55.2µs             fail               79.5µs             22.4µs            
  MethodType                     25.0µs             3.9µs              77.5µs             21.5µs            
  staticmethod                   18.8µs             fail               63.1µs             18.5µs            
  classmethod                    16.6µs             fail               63.5µs             28.3µs            
  GeneratorType                  14.3µs             fail               fail               fail              
  range_iterator                 14.0µs             5.5µs              24.0µs             8.5µs             
  enumerate                      16.7µs             3.5µs              24.5µs             7.5µs             
  zip                            14.7µs             3.2µs              28.8µs             9.2µs             
  map                            14.0µs             fail               71.4µs             35.7µs            
  filter                         14.5µs             fail               72.5µs             36.4µs            
  CoroutineType                  37.3µs             fail               fail               fail              
  AsyncGeneratorType             8.8µs              fail               fail               fail              
  asyncio.Task                   24.0µs             fail               fail               fail              
  asyncio.Future                 15.6µs             fail               fail               fail              
  concurrent.futures.Future      44.4µs             fail               108.4µs            fail              
  ThreadPoolExecutor             14.5µs             fail               fail               fail              
  ProcessPoolExecutor            12.5µs             fail               fail               fail              
  weakref.ref                    12.2µs             fail               16.8µs             fail              
  WeakValueDictionary            16.7µs             fail               101.2µs            fail              
  WeakKeyDictionary              15.1µs             fail               93.9µs             fail              
  Enum                           19.0µs             2.6µs              18.9µs             6.4µs             
  IntEnum                        2.5µs              0.9µs              15.3µs             5.0µs             
  Flag                           13.5µs             1.3µs              15.3µs             5.1µs             
  IntFlag                        2.4µs              0.8µs              13.2µs             4.6µs             
  ContextVar                     10.9µs             fail               fail               fail              
  Token                          11.1µs             fail               fail               fail              
  contextmanager                 88.8µs             fail               322.5µs            74.3µs            
  ContextObject                  61.8µs             fail               143.3µs            73.5µs            
  subprocess.Popen               229.1µs            fail               fail               fail              
  CompletedProcess               18.5µs             4.5µs              27.7µs             5.8µs             
  CodeType                       35.9µs             fail               38.0µs             9.4µs             
  FrameType                      79.3µs             fail               fail               fail              
  property                       52.6µs             fail               73.7µs             53.4µs            
  CustomDescriptor               74.0µs             fail               107.1µs            60.6µs            
  ModuleType                     142.9µs            fail               18.6µs             7.2µs             
  OS pipes                       4.2µs              0.5µs              7.2µs              1.7µs             
  File descriptors               2.0µs              0.4µs              6.2µs              1.8µs             
  PipeReconnector                11.0µs             5.5µs              29.7µs             6.2µs             
  SQLiteReconnector              20.7µs             4.1µs              20.8µs             5.1µs             
  typing.NamedTuple              4.9µs              fail               34.2µs             136.7µs           
  typing.TypedDict               4.5µs              0.4µs              10.3µs             2.0µs             
  Class object                   8.5µs              0.7µs              11.1µs             3.3µs             
  Class instance                 6.8µs              2.1µs              16.9µs             4.2µs             
  dataclass                      89.6µs             fail               752.2µs            237.6µs           
  slots class                    37.1µs             fail               107.1µs            56.0µs            
  slots+dict class               31.0µs             fail               107.5µs            55.8µs            
  Sktimer                        28.9µs             fail               42.3µs             fail              
  TimeThis                       54.6µs             fail               74.4µs             fail              
  Circuit                        25.5µs             fail               37.7µs             fail              
  BreakingCircuit                24.7µs             fail               38.7µs             fail              
  Skpath                         22.5µs             11.3µs             40.9µs             8.5µs             
  CustomRoot                     7.9µs              3.6µs              20.2µs             4.7µs             
  Skprocess                      212.1µs            fail               402.9µs            201.8µs           
  Pool                           115.5µs            fail               fail               fail              
  Share                          852.0µs            fail               fail               fail              
  ProcessTimers                  106.4µs            fail               100.8µs            fail              
  ProcessError                   10.3µs             2.0µs              22.3µs             6.2µs             
  PreRunError                    7.9µs              1.5µs              20.3µs             5.0µs             
  RunError                       6.4µs              1.4µs              18.6µs             5.0µs             
  PostRunError                   6.1µs              1.3µs              17.5µs             4.2µs             
  OnFinishError                  5.6µs              1.2µs              17.6µs             4.1µs             
  ResultError                    5.9µs              1.3µs              16.8µs             4.1µs             
  ErrorHandlerError              7.3µs              1.2µs              18.3µs             4.1µs             
  ProcessTimeoutError            7.1µs              1.5µs              22.7µs             4.1µs             
  ResultTimeoutError             5.9µs              1.3µs              17.2µs             4.0µs             
  PathDetectionError             6.3µs              2.7µs              17.5µs             4.1µs             
  SerializationError             5.4µs              1.3µs              17.9µs             4.3µs             
  DeserializationError           7.0µs              1.3µs              14.4µs             4.2µs             
  SkModifierError                5.6µs              3.5µs              15.2µs             3.9µs             
  FunctionTimeoutError           6.3µs              1.5µs              14.3µs             3.7µs             
  Skclass                        51.4µs             7.5µs              170.0µs            9.8µs             
  Skfunction                     82.6µs             fail               92.8µs             34.4µs            
  Skfunction.asynced()           59.7µs             fail               78.7µs             65.0µs
  ```