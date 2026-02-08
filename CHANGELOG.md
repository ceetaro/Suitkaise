# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changelog is maintained from version 0.3.0 forward.

---

## [Unreleased]

### Fixed
- **Python 3.12/3.13 compatibility**: `TemporaryFileHandler` no longer crashes on `_TemporaryFileCloser` objects. Python 3.12 restructured `NamedTemporaryFile` internals — the handler now requires file-like interface (`tell`/`seek`/`read`) and supports the moved `delete` attribute via `_closer`.
- **Flaky multiprocess Share test**: Coordinator `stop()` now handles dead Manager connections gracefully (`OSError`/`EOFError`/`BrokenPipeError`). Test verification and cleanup are resilient to Manager process death under heavy load.

### Added
- Comprehensive network handler test suite (116 tests) covering all 16 database reconnector classes, the factory function, `SocketHandler`/`SocketReconnector`, `DatabaseConnectionHandler` with mock objects, and `HTTPSessionHandler`.

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
