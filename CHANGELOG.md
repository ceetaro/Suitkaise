# Changelog

All notable changes to this project will be documented in this file. (to the best of my ability)

## Overview

- changelog is being kept from version 0.3.0 and forward.

Reason: this is the first complete rendition that is ready for release.

All further changes will be changes to 0.3.0 (or the most recent version once 0.3.0 is not the most recent version).

## [Unreleased]

As of version 0.3.0, the project is still unreleased.

### Added
- Expanded blocking call detection for common sync libraries (boto3, redis, pymongo, Kafka, Elasticsearch, etc.) with broader IO-aware heuristics.
- Best-effort socket auto-reconnect that attempts bind/connect using saved local/remote addresses.
- Base `Reconnector` class with consistent `.reconnect()` API for reconnection helpers.
- Database-specific reconnector classes (`PostgresReconnector`, `MySQLReconnector`, `MongoReconnector`, `RedisReconnector`, etc.) with standard connection args.
- SocketReconnector helper to recreate sockets with best-effort bind/connect.
- PipeReconnector helper to recreate multiprocessing pipes and expose both ends.
- SubprocessReconnector helper to restart Popen commands or inspect snapshots.
- ThreadReconnector helper to rebuild threads from serialized metadata.
- MatchReconnector helper to recreate regex Match objects when possible.
- `cerial.reconnect_all(obj, **kwargs)` to recursively reconnect structures with optional credentials.
- Robust database connection metadata extraction for common libraries (Postgres/MySQL/SQLite/Redis/Mongo/SQLAlchemy/ODBC and more).
- `@autoreconnect(**kwargs)` decorator for Skprocess to automatically reconnect resources after deserialization.
- kwargs structure for `reconnect_all()` and `@autoreconnect`: type-keyed dict with `"*"` defaults and attr-specific overrides.
- Full auth/credential support in DbReconnector for MongoDB, Cassandra, Elasticsearch, OpenSearch, SQLAlchemy, ODBC, Neo4j, and InfluxDB v2.
- Documentation for Reconnectors in `cerial` how-to-use and how-it-works.
- Documentation for `@autoreconnect` in `processing` how-to-use and how-it-works.

### Changed
- FrameType deserialization now returns `FrameInfo` metadata instead of raising (frames cannot be reconstructed).
- File descriptor reconstruction is now best-effort when a path is available; still fails safely otherwise.
- Database connection deserialization now auto-connects when enough non-secret info is present, otherwise returns a `DbReconnector`.
- `reconnect_all()` now accepts `**kwargs` instead of `overrides` parameter for cleaner API.
- All DbReconnector implementations now use consistent dict-based parameter passing for authentication.
- License updated to Apache License 2.0.

## [0.3.0] - 2026-01-16 - 2026-01-27

### Added
- Initial release contents for Suitkaise modules.
- Initial type stub files for IDE autocompletion.
- `suitkaise` CLI entrypoint with version and module info.
- CI workflow for running the full test suite.
- README badges for quick project metadata.
- increased test coverage to 85%
  - WorstPossibleObject causes this number to be lower than it would be otherwise

- increased speed for:
  - FileIO - >2000µs --> 45µs (44x)
  - BufferedReader - >2000µs --> 85µs (23x)
  - BufferedWriter - >2000µs --> 50µs (40x)
  - FrameType - >2500µs --> 12µs (208x)

- fixed some internal handling issues with builtin types and methods on Windows

- `Circuit`/`BreakingCircuit` jitter option to spread retry sleep times.

- `Skpath.copy_to()` and `Skpath.move_to()` convenience file operations.

- `Skprocess.run()` helper to start + wait + return result in one call.

- Rolling window support in `Sktimer` (`max_times`) and `@timethis(max_times=...)`.

- Cerial IR helpers: `serialize_ir`, `ir_to_jsonable`, `ir_to_json`, `to_jsonable`, `to_json`.

- `@blocking` decorator in `suitkaise.sk` to explicitly mark methods/functions as blocking. This enables `.background()` and `.asynced()` for CPU-heavy code that doesn't contain auto-detectable I/O calls (like `timing.sleep`).

- `Skpath.is_empty` property that returns `True` if a directory has no contents. Raises `NotADirectoryError` if called on a file.

- `Skpath.rmdir()` and `Skpath.unlink()` methods for removing directories and files.

- `NotAFileError` exception (inherits `IsADirectoryError`) raised by `Skpath.unlink()` when path is a directory.

- Share now serializes into a live client that reuses the parent coordinator when passed to Pool workers, avoiding duplicate Manager startup and enabling safe cross-process usage.

1/27/26

- updated processing module to correctly work on Windows
  - Pool now uses multiprocessing.Pool instead of creating multiple processes manually (optimization, nothing changes for users)
- updated tests to work on Windows
- updated all api to be streamlined and tested all examples in api docstrs


