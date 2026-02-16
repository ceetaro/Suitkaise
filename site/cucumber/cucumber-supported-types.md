/*

synced from suitkaise-docs/cucumber/supported-types.md

*/

rows = 2
columns = 1

# 1.1

title = "cucumber supported types"

# 1.2

text = "
Note: Iterator-style objects (including `enumerate` and `zip`) are exhausted during serialization. Reconstruction returns a plain iterator over the remaining values, not the original iterator type.

Note: Objects that turn into `Reconnector` objects may need to be reconnected after deserialization to fully work. Reconnectors that do not require auth will lazily reconnect on first attribute access; auth-based reconnectors still require an explicit `reconnect(...)` call (or `<suitkaise-api>reconnect_all</suitkaise-api>(...)` with credentials).

Note: Due to Python limitations, some types are not supported by `<suitkaise-api>Share</suitkaise-api>`.
- `multiprocessing.*` objects (queues, managers, events, shared_memory, connections)
- `os.pipe()` file handles / pipe-backed `io.FileIO`
- `weakref.ref` objects (recreated as weak references; dead refs become placeholders)
- tokens with authentication (cannot serialize authentication strings)


- user-defined class instances --> new instance of same type with same state
- `None` --> `None`
- `bool` --> `bool`
- `int` --> `int`
- `float` --> `float`
- `str` --> `str`
- `bytes` --> `bytes`
- `list` --> `list`
- `tuple` --> `tuple`
- `set` --> `set`
- `frozenset` --> `frozenset`
- `dict` --> `dict`
- `datetime.datetime` --> `datetime.datetime`
- `datetime.date` --> `datetime.date`
- `datetime.time` --> `datetime.time`
- `datetime.timedelta` --> `datetime.timedelta`
- `datetime.timezone` --> `datetime.timezone`
- `decimal.Decimal` --> `decimal.Decimal`
- `fractions.Fraction` --> `fractions.Fraction`
- `uuid.UUID` --> `uuid.UUID`
- `pathlib.Path` --> `pathlib.Path`
- `pathlib.PurePath` --> `pathlib.PurePath`
- `pathlib.PosixPath` --> `pathlib.PosixPath`
- `pathlib.WindowsPath` --> `pathlib.WindowsPath`
- `types.FunctionType` --> `types.FunctionType`
- `functools.partial` --> `functools.partial`
- `types.MethodType` --> `types.MethodType`
- `staticmethod` --> `staticmethod`
- `classmethod` --> `classmethod`
- `type` --> `type`
- `logging.Logger` --> `logging.Logger`
- `logging.StreamHandler` --> `logging.StreamHandler`
- `logging.FileHandler` --> `logging.FileHandler`
- `logging.Formatter` --> `logging.Formatter`
- `_thread.lock` --> `_thread.lock`
- `threading.RLock` --> `threading.RLock`
- `threading.Semaphore` --> `threading.Semaphore`
- `threading.BoundedSemaphore` --> `threading.BoundedSemaphore`
- `threading.Barrier` --> `threading.Barrier`
- `threading.Condition` --> `threading.Condition`
- `io.TextIOBase` --> `io.TextIOBase`
- `tempfile._TemporaryFileWrapper` --> `tempfile._TemporaryFileWrapper`
- `io.StringIO` --> `io.StringIO`
- `io.BytesIO` --> `io.BytesIO`
- `queue.Queue` --> `queue.Queue`
- `multiprocessing.Queue` --> `multiprocessing.Queue` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `threading.Event` --> `threading.Event`
- `multiprocessing.Event` --> `multiprocessing.Event` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `re.Pattern` --> `re.Pattern`
- `re.Match` --> `MatchReconnector`
- `sqlite3.Connection` --> `SQLiteConnectionReconnector`
- `sqlite3.Cursor` --> `SQLiteCursorReconnector`
- `contextvars.ContextVar` --> `contextvars.ContextVar`
- `contextvars.Token` --> `contextvars.Token` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `requests.Session` --> `requests.Session`
- `socket.socket` --> `SocketReconnector`
- `psycopg2.Connection` --> `DbReconnector`
- `pymysql.Connection` --> `DbReconnector`
- `pymongo.MongoClient` --> `DbReconnector`
- `redis.Redis` --> `DbReconnector`
- `sqlalchemy.Engine` --> `DbReconnector`
- `cassandra.Cluster` --> `DbReconnector`
- `elasticsearch.Elasticsearch` --> `DbReconnector`
- `neo4j.Driver` --> `DbReconnector`
- `influxdb_client.InfluxDBClient` --> `DbReconnector`
- `pyodbc.Connection` --> `DbReconnector`
- `clickhouse_driver.Client` --> `DbReconnector`
- `pymssql.Connection` --> `DbReconnector`
- `oracledb.Connection` --> `DbReconnector`
- `snowflake.Connection` --> `DbReconnector`
- `duckdb.Connection` --> `DbReconnector`
- `collections.abc.Iterator` --> `iterator`
- `range` --> `range`
- `enumerate` --> `iterator`
- `zip` --> `iterator`
- `mmap.mmap` --> `mmap.mmap`
- `multiprocessing.shared_memory.SharedMemory` --> `multiprocessing.shared_memory.SharedMemory` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `int` (file descriptors) --> `int` (file descriptors)
- `memoryview` --> `memoryview`
- `threading.Thread` --> `ThreadReconnector`
- `concurrent.futures.ThreadPoolExecutor` --> `concurrent.futures.ThreadPoolExecutor`
- `concurrent.futures.ProcessPoolExecutor` --> `concurrent.futures.ProcessPoolExecutor`
- `threading.local` --> `threading.local`
- `io.FileIO` (from `os.pipe`) --> `io.FileIO` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `multiprocessing.connection.Connection` --> `multiprocessing.connection.Connection` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `multiprocessing.managers.BaseProxy` --> `multiprocessing.managers.BaseProxy` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `types.CodeType` --> `types.CodeType`
- `types.FrameType` --> `types.FrameType` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `property` --> `property`
- `types.MemberDescriptorType` --> `types.MemberDescriptorType` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `types.GetSetDescriptorType` --> `types.GetSetDescriptorType` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `types.WrapperDescriptorType` --> `types.WrapperDescriptorType` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `types.MethodDescriptorType` --> `types.MethodDescriptorType` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `types.MethodWrapperType` --> `types.MethodWrapperType`
- `types.GeneratorType` --> `iterator`
- `weakref.ref` --> `weakref.ref` (`<suitkaise-api>Share</suitkaise-api>` not supported)
- `weakref.WeakValueDictionary` --> `weakref.WeakValueDictionary`
- `weakref.WeakKeyDictionary` --> `weakref.WeakKeyDictionary`
- `enum.Enum` --> `enum.Enum`
- `enum.EnumMeta` --> `enum.EnumMeta`
- `contextlib._GeneratorContextManager` --> `contextlib._GeneratorContextManager`
- `subprocess.Popen` --> `SubprocessReconnector`
- `subprocess.CompletedProcess` --> `subprocess.CompletedProcess`
- `types.CoroutineType` --> `types.CoroutineType`
- `types.AsyncGeneratorType` --> `types.AsyncGeneratorType`
- `asyncio.Task` --> `asyncio.Task`
- `asyncio.Future` --> `asyncio.Future`
- `types.ModuleType` --> `types.ModuleType`
- `collections.namedtuple` --> `collections.namedtuple`
- `typing.NamedTuple` --> `typing.NamedTuple`
- `typing.TypedDict` --> `typing.TypedDict`
- `DbReconnector` --> `DbReconnector`
- `SocketReconnector` --> `SocketReconnector`
- `ThreadReconnector` --> `ThreadReconnector`
- `PipeReconnector` --> `PipeReconnector`
- `SubprocessReconnector` --> `SubprocessReconnector`
- `MatchReconnector` --> `MatchReconnector`
"
