# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changelog is maintained from version 0.3.0 forward.

---

## [0.4.13] - 2026-02-23

### Fixed
- `Share` manager counter retry now recovers stale manager lock handles that surface as `TypeError: 'NoneType' object cannot be interpreted as an integer` in worker write paths.
- Restored correct cucumber handler detection in `Share` so handler-backed objects (like `sqlite3.Connection`) resolve to reconnectors instead of being incorrectly proxied.
- Normalized supported-type name matching in processing tests to avoid false failures from case-only differences (e.g., `User-defined` vs `user-defined`).

## [0.4.12] - 2026-02-23

### Fixed
- `Share` primitive assignments now behave consistently in multiprocessing for plain Python types (`int`, `float`, `bool`, `str`, `bytes`, `tuple`, `frozenset`, `complex`), including atomic augmented operations (`+=`, `-=`, `*=`, etc.).
- Added primitive read-your-own-write behavior so immediate reads after augmented assignment reflect the worker's just-applied value.
- Prevented stale `Share` snapshot restores in client mode from overwriting active coordinator state.
- Prevented `logging.Logger` proxy deadlocks in shared objects by treating logger handlers as non-proxied.
- Fixed `cucumber` deserializer cleanup guard for reconstruction path underflow (`pop from empty list`).
- CLI welcome message no longer triggers from package import path; it now runs from CLI startup and is still shown once per installed version.

## [0.4.11b0] - 2026-02-23

### Fixed
- small CLI install message adjustment, some typos in docs

## [0.4.10b0] - 2026-02-23

### Fixed
- small CLI install message adjustment

## [0.4.9b0] - 2026-02-23

### Fixed
- small CLI install message adjustment

## [0.4.8b0] - 2026-02-23

### Fixed
- small CLI bug fix: website was not being displayed when installing suitkaise.

## [0.4.7b0] - 2026-02-11

### Fixed
- Regression fix (Share + Pool ETL workloads): hardened manager-proxy lifecycle recovery for `Share` write paths that could fail with `OSError: handle is closed` in long-running `Pool.star().map(...)` workers. `_AtomicCounterRegistry` and coordinator enqueue/counter paths now perform best-effort proxy reconnection and a bounded retry, preventing false "Share is stopped" cascades, dropped write commands, and parent `map()` hangs.

- Tests: added a Share primitive regression that forcibly closes a manager proxy handle and verifies counter operations recover automatically.


## [0.4.7b0] - 2026-02-11

### Fixed
- Regression fix (Pool + TimeThis): `Sktimer` is now fork-safe in subprocess workers. After fork, process-local timer lock/session state is rebuilt automatically, and dead-session purge now uses `sys._current_frames()` instead of `threading.enumerate()` to avoid fork-time deadlocks.

- Regression fix (Share + BreakingCircuit): `Circuit` and `BreakingCircuit` now serialize without carrying live `threading.RLock` internals; deserialization recreates a fresh lock per process. This prevents `Share`/`Pool` hangs when a breaker is assigned to shared state.

## [0.4.5b0] - 2026-02-11

### Fixed
- Memory leak: `_Coordinator.stop()` skipped `SharedMemory` cleanup when called on an already-stopped coordinator. The early-return path now calls `counter_registry.reset()` to unlink shared memory segments, eliminating the `resource_tracker: leaked shared_memory objects` warning.

- Memory leak: `Share._META_CACHE` used a plain `dict` keyed by class types, preventing garbage collection of classes. Changed to `weakref.WeakKeyDictionary` so classes (and their cached metadata) are collected when no longer referenced.

- Memory leak: `Sktimer._sessions` grew unboundedly as threads were created and destroyed. Added `_purge_dead_sessions()` to remove entries for threads that no longer exist, called automatically during session access.

- Memory leak: `Pool` worker `multiprocessing.Queue` resources were not cleaned up after worker timeout/termination. Added `_drain_queue()` helper that empties, closes, and joins queues after workers complete.

- Memory leak: `_AtomicCounterRegistry.remove_object()` only unlinked `SharedMemory` segments for the "owning" process. If the owner died, segments leaked. Now always attempts `shm.unlink()` on removal regardless of ownership.

- Memory leak: `_Coordinator.destroy()` / `__del__` split — `stop()` no longer shuts down the `SyncManager`, preserving restart capability. `destroy()` handles permanent shutdown. `Share.__exit__` calls `stop()` (restartable), `Share.__del__` calls `destroy()` (final cleanup).

- Thread-safety: `cucumber.serialize()` and `cucumber.deserialize()` used module-level singleton `Serializer`/`Deserializer` instances with mutable per-call state (`seen_objects`, `_object_registry`). Concurrent calls from multiple threads (e.g. `asyncio.gather` + `to_thread`) caused data races — one thread clearing the registry mid-reconstruction. Replaced singletons with per-thread instances via `threading.local()`.

## [0.4.4b0] - 2026-02-10

### Fixed
- Python 3.12/3.13 compatibility: `TemporaryFileHandler` no longer crashes on `_TemporaryFileCloser` objects. Python 3.12 restructured `NamedTemporaryFile` internals — the handler now requires file-like interface (`tell`/`seek`/`read`) and supports the moved `delete` attribute via `_closer`.

- Flawed multiprocess Share test: Coordinator `stop()` now handles dead Manager connections gracefully (`OSError`/`EOFError`/`BrokenPipeError`). Test verification and cleanup are resilient to Manager process death under heavy load.

- Share proxy false "stopped" warnings in child processes: Coordinator `is_alive` now correctly detects the parent's coordinator process via Manager connection probe when running in client mode (child processes). Previously `_process` was always `None` in deserialized coordinators, triggering false warnings.

- Share proxy broke user class methods: Proxy `__getattr__` was checking `if method_meta.get('writes'):` — empty list (as generated by the `@sk` analyzer) evaluated as falsy, routing all user class methods to the read-only path. Fixed to check `'writes' in method_meta` instead.

- Shared memory leaks at shutdown: `coordinator.stop()` now cleans up shared memory segments even on forced shutdown. `coordinator.kill()` also calls `reset()`. Added `close_local()` method for child processes and `__del__` on coordinator for GC cleanup.

- `Sktimer.percentile()`, `get_time()`, `get_statistics()`, and `get_stats()` returned `None` when called through Share proxy. These read-only methods declared `{'writes': []}` in `_shared_meta`, which the proxy treated as a write (fire-and-forget) because the `writes` key existed. Changed to `{'reads': ['times']}` so the proxy correctly fetches the object and returns the actual value.

- `TimeThis` context manager and `@timethis` decorator recorded partial timing measurements when an exception was raised inside the block/function, polluting statistics. Now only records timing on successful completion. Also prevents `discard()` errors from masking the original exception in `__exit__`.

- NamedTuples were serialized as plain tuples by `cucumber`, losing field names and class info. The `NamedTupleHandler` existed but was never invoked because `isinstance(obj, tuple)` intercepted namedtuples first. Now namedtuples are detected and routed to the handler, preserving fields, class name, module, and defaults through serialization roundtrips.

- `@sk` modifier methods (`.retry()`, `.timeout()`, `.background()`, `.rate_limit()`, `.asynced()`) bypassed outer decorators like `@timethis`. The closures captured the raw function at `@sk` decoration time, so calling `.retry(3)()` on a `@timethis @sk`-decorated function created an `Skfunction` wrapping the un-timed function — timing was silently lost. `@sk` now uses a mutable reference that `@timethis` (and other outer decorators) can update via `_sk_update_source`, ensuring modifiers always go through the full decorator chain.

- `Skpath` did not support `<`, `>`, `<=`, `>=` comparison operators. Ordering comparisons fell back to default object identity, producing incorrect results. Added `__lt__`, `__gt__`, `__le__`, `__ge__` methods with always-case-sensitive lexicographic ordering by path components (consistent across all platforms, unlike `pathlib.Path` which is case-insensitive on Windows).

- Share proxy returned `None` for method calls on plain user classes (no `@sk`). `analyze_class()` generated `{'writes': []}` for read-only methods, and the proxy treated any method with a `'writes'` key as fire-and-forget. Fixed `analyze_class()` to only include `'writes'` when actual writes exist and to include `'reads'` for methods that read attributes, so the proxy correctly routes read-only methods through the fetch path.

- `@sk` class `.asynced()` raised `TypeError` when `await`-ing non-blocking methods. Only methods with detected blocking calls were wrapped as async; non-blocking methods stayed sync, causing `await instance.method()` to fail. Non-blocking methods are now wrapped in a trivial async passthrough so all methods on an async class are uniformly awaitable.

- `cucumber` deserializer crashed with `AttributeError: 'NoneType' object has no attribute 'real_object'` when deserializing objects whose `__object_id__` was present but had no placeholder in the registry. Added a guard to only update `.real_object` when a placeholder exists.

- `@sk` class `.asynced()` produced non-awaitable methods. `@sk` replaces class methods with `_ModifiableMethod` descriptors, but `create_async_class()` checked `callable(member)` which returned `False` for descriptors — silently skipping them. The async class then inherited the sync descriptors from the parent, so `await proc.method()` raised `TypeError: object str can't be used in 'await' expression`. Fixed `create_async_class()` to unwrap `_ModifiableMethod`/`_AsyncModifiableMethod` descriptors to their underlying functions before wrapping.

### Added
- Builtin mutable type proxy support: `list`, `set`, `dict` assigned to `Share` are now proxied through a `_BUILTIN_SHARED_META` registry. Mutating methods (`.append()`, `.add()`, `.update()`, `[key] = val`, `del [key]`, etc.) are dispatched through the coordinator. Read-only methods (`.copy()`, `.get()`, `.count()`, `.index()`, etc.) fetch fresh state and return values directly.
- Dunder protocol methods on `_ObjectProxy`: `__len__`, `__iter__`, `__contains__`, `__bool__`, `__getitem__`, `__setitem__`, `__delitem__`, `__str__` — so `len()`, `for x in`, `in`, indexing, and `str()` all work on proxied builtins.
- Comprehensive network handler test suite (116 tests) covering all 16 database reconnector classes, the factory function, `SocketHandler`/`SocketReconnector`, `DatabaseConnectionHandler` with mock objects, and `HTTPSessionHandler`.
- `_share_blocked_methods` support in `_ObjectProxy`: classes can declare a dict of method names that raise `TypeError` when accessed through Share's proxy. Generic mechanism — any class can opt in.
- `_share_disallowed` support in `Share.__setattr__`: classes can declare a string message that prevents them from being assigned to Share entirely. Raises `TypeError` with the message.
- `_share_method_aliases` support in `_MethodProxy`: classes can declare a dict mapping public method names to internal alternatives when called through Share's proxy (e.g. routing `short()` to a no-sleep variant in the coordinator).
- `Sktimer` now blocks `start()`, `stop()`, `pause()`, `resume()`, `lap()`, and `discard()` when used through `Share`. These methods rely on `perf_counter()` and thread-local sessions that produce meaningless results when replayed in the coordinator process. Use `add_time(elapsed)` to aggregate pre-computed durations across processes instead.
- `Circuit` is now disallowed in `Share`. Its auto-reset and sleep behavior breaks when replayed in the coordinator process. Use `BreakingCircuit` in Share instead.
- `BreakingCircuit` `short()` and `trip()` now skip sleep when called through `Share`. State changes (broken, counters) still apply normally via no-sleep internal aliases. Sleep in the coordinator would block command processing and provide no rate-limiting to the calling process.

### Changed
- Test coverage increased from 80% to 82%.
- CI matrix expanded to 9 jobs: 3 OSes (Ubuntu, macOS, Windows) x 3 Python versions (3.11, 3.12, 3.13).

## [0.4.0b0] - 2026-02-07

### Added

#### Processing
- `Pool.unordered_map()` method that returns a list in completion order (like `unordered_imap` but returns list instead of iterator).
- `Skprocess.run()` now supports `.timeout()`, `.background()`, and `.asynced()` modifiers for async and background execution.
- `processing.Pipe` for inter-process communication.
- `@autoreconnect(**kwargs)` decorator for Skprocess to automatically reconnect resources after deserialization.
- kwargs structure for `reconnect_all()` and `@autoreconnect`: type-keyed dict with `"*"` defaults and attr-specific overrides.
- Processing benchmark comparing Skprocess vs multiprocessing concurrency.

#### `cucumber` (Serialization)
- Expanded blocking call detection for common sync libraries (boto3, redis, pymongo, Kafka, Elasticsearch, etc.) with broader IO-aware heuristics.
- Best-effort socket auto-reconnect that attempts bind/connect using saved local/remote addresses.
- Base `Reconnector` class with consistent `.reconnect()` API for reconnection helpers.
- Database-specific reconnector classes (`PostgresReconnector`, `MySQLReconnector`, `MongoReconnector`, `RedisReconnector`, etc.) with standard connection args.
- `SocketReconnector` helper to recreate sockets with best-effort bind/connect.
- `PipeReconnector` helper to recreate multiprocessing pipes and expose both ends.
- `SubprocessReconnector` helper to restart Popen commands or inspect snapshots.
- `ThreadReconnector` helper to rebuild threads from serialized metadata.
- `MatchReconnector` helper to recreate regex Match objects when possible.
- `cucumber.reconnect_all(obj, **kwargs)` to recursively reconnect structures with optional credentials.
- Robust database connection metadata extraction for common libraries (Postgres/MySQL/SQLite/Redis/Mongo/SQLAlchemy/ODBC and more).
- Full auth/credential support in `DbReconnector` for MongoDB, Cassandra, Elasticsearch, OpenSearch, SQLAlchemy, ODBC, Neo4j, and InfluxDB v2.
- `GenericAlias` handling in `ClassInstanceHandler` (stores origin + args for reconstruction).

#### Documentation
- Documentation for Reconnectors in `cucumber` how-to-use and how-it-works.
- Documentation for `@autoreconnect` in `processing` how-to-use and how-it-works.

### Changed
- FrameType deserialization now returns `FrameInfo` metadata instead of raising (frames cannot be reconstructed).
- File descriptor reconstruction is now best-effort when a path is available; still fails safely otherwise.
- Database connection deserialization now auto-connects when enough non-secret info is present, otherwise returns a `DbReconnector`.
- `reconnect_all()` now accepts `**kwargs` instead of `overrides` parameter for cleaner API.
- All `DbReconnector` implementations now use consistent dict-based parameter passing for authentication.
- License updated to Apache License 2.0.
- `Skprocess` IPC now uses manager-backed queues/events to avoid spawn SemLock issues; IPC cleanup happens after `result()`.
- Pipe endpoint serialization uses `multiprocessing.reduction.ForkingPickler` for stable handle transfer.
- `Skpath` encoded-id resolution now returns resolved paths even if they don't exist yet.
- `WeakKeyDictionary` reconstruction preserves unweakrefable keys using placeholders instead of dropping them.
- Processing module updated to correctly work on Windows.
  - `Pool` now uses `multiprocessing.Pool` instead of creating multiple processes manually (optimization, no user-facing changes).
- Updated tests for Windows compatibility.
- Streamlined all public API; tested all examples in API docstrings.
- Minor internal updates to cucumber and WorstPossibleObject (no functionality changes).

---

## [0.3.0] - 2026-01-16 — 2026-01-27

### Added

#### Core
- Initial release contents for all Suitkaise modules: `cucumber`, `circuits`, `processing`, `paths`, `sk`, `timing`.
- Initial type stub files (`.pyi`) for IDE autocompletion.
- `py.typed` marker for PEP 561 compliance.
- `suitkaise` CLI entrypoint with `version`, `info`, `modules`, and `docs` commands.
- CI workflow for running the full test suite with coverage reporting.
- README badges for quick project metadata.

#### `cucumber` (Serialization)
- Cucumber IR helpers: `serialize_ir`, `ir_to_jsonable`, `ir_to_json`, `to_jsonable`, `to_json`.

#### `circuits`
- `Circuit`/`BreakingCircuit` jitter option to spread retry sleep times.

#### `processing`
- `Skprocess.run()` helper to start + wait + return result in one call.
- `Share` now serializes into a live client that reuses the parent coordinator when passed to Pool workers, avoiding duplicate Manager startup and enabling safe cross-process usage.

#### `paths`
- `Skpath.copy_to()` and `Skpath.move_to()` convenience file operations.
- `Skpath.is_empty` property — returns `True` if a directory has no contents. Raises `NotADirectoryError` if called on a file.
- `Skpath.rmdir()` and `Skpath.unlink()` methods for removing directories and files.
- `NotAFileError` exception (inherits `IsADirectoryError`) raised by `Skpath.unlink()` when path is a directory.

#### `sk` (Modifiers)
- `@blocking` decorator to explicitly mark methods/functions as blocking. Enables `.background()` and `.asynced()` for CPU-heavy code that doesn't contain auto-detectable I/O calls.

#### `timing`
- Rolling window support in `Sktimer` (`max_times`) and `@timethis(max_times=...)`.

### Changed
- Test coverage increased to ~85% (WorstPossibleObject edge cases lower the reported number).

### Fixed
- Internal handling issues with builtin types and methods on Windows.

### Performance
- FileIO serialization: >2000µs → 45µs (44x faster)
- BufferedReader serialization: >2000µs → 85µs (23x faster)
- BufferedWriter serialization: >2000µs → 50µs (40x faster)
- FrameType serialization: >2500µs → 12µs (208x faster)
