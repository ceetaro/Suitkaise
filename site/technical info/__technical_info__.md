# Technical Info

Currently, `suitkaise` is version `0.4.8 beta`.

`suitkaise` supports Python 3.11 and above.

It has no dependencies outside of the Python standard library.

(start of dropdown for readme)
## README

### Suitkaise

Making things easier for developers of all skill levels to develop complex Python programs.

(pronounced exactly like the word suitcase)

All files in this repository are licensed under the Apache License 2.0, including:
- source code
- examples
- documentation
- tests
- site content code
- and everything else


#### Installation

```bash
pip install suitkaise
```

#### Info

Explicitly supported Python versions: 3.11 and above

Currently, `suitkaise` is version `0.4.8 beta`.

`suitkaise` contains the following modules:

- `cucumber`: serialization engine
- `circuits`: flow control with the Circuit and BreakingCircuit classes.
- `processing`: upgraded multiprocessing with easy shared state
- `paths`: upgraded path class and utilities for path ops
- `sk`: modifiers for functions and class methods
- `timing`: timer class with deep statistics usable in many ways

### Documentation

All documentation is available for download.

CLI:
- downloads to project root
- cwd must be within project root

```bash
suitkaise docs
```

Python:

```python
from suitkaise import docs

# download to project root
docs.download()

# download to a specific path within your project
docs.download("path/within/project")
```

To place docs outside your project root, use the `Permission` context manager.

```python
from suitkaise import docs

with docs.Permission():
    docs.download("/Users/joe/Documents")
```

You can also view more at [suitkaise.info](https://suitkaise.info).

### Quick Start

#### Parallel processing with shared state

```python
from suitkaise.processing import Share, Pool, Skprocess
import logging

# put anything on Share — literally anything
share = Share()
share.counter = 0
share.results = []
share.log = logging.getLogger("worker")

class Worker(Skprocess):
    def __init__(self, share, item):
        self.share = share
        self.item = item

    def __run__(self):
        result = self.item * 2
        self.share.results.append(result)       # shared list
        self.share.counter += 1                 # shared counter
        self.share.log.info(f"done: {result}")  # shared logger

pool = Pool(workers=4)
pool.star().map(Worker, [(share, x) for x in range(20)])

print(share.counter)         # 20
print(len(share.results))    # 20
print(share.log.handlers)    # still works
```

#### Serialize anything

```python
from suitkaise import cucumber

data = cucumber.serialize(any_object)
restored = cucumber.deserialize(data)
```

#### Time anything

```python
from suitkaise.timing import timethis

@timethis()
def my_function():
    do_work()

my_function()
print(my_function.timer.mean)
```

```python
from suitkaise.timing import TimeThis

with TimeThis() as timer:
    do_this()
    then_this()
    this_too()

# stops timing and records on exit

# get most recent time
print(timer.most_recent)
```

#### Add retry, timeout, background execution to any function

```python
from suitkaise import sk

@sk
def fetch(url):
    return requests.get(url).json()

# retry 3 times, timeout after 5 seconds each attempt
data = fetch.retry(3).timeout(5.0)("https://api.example.com")
```

#### Cross-platform paths, normalized path types

```python
from suitkaise.paths import Skpath

path = Skpath("data/file.txt")
print(path.rp)  # "data/file.txt" — same on every machine, every OS
```

```python
from suitkaise.paths import autopath

@autopath()
def process(path: AnyPath):
    print(path.rp)  # always an Skpath, no matter what was passed in

process("data/file.txt")        # str → Skpath
process(Path("data/file.txt"))  # Path → Skpath
```


#### Circuit breakers

```python
from suitkaise import Circuit

circuit = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=1.0)

for request in requests:
    try:
        process(request)
    except ServiceError:
        circuit.short()
```

```python
from suitkaise import BreakingCircuit

breaker = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=1.0)

while not breaker.broken:
    try:
        result = risky_operation()
        break  # success
    except OperationError:
        breaker.short()  # count the failure

if breaker.broken:
    handle_failure()
```

For more, see the full documentation at [suitkaise.info](https://suitkaise.info) or download the docs with `suitkaise docs` in your terminal after installation.

(end of dropdown for readme)

(start of dropdown for license)
## License

                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   Copyright 2025 Casey Eddings

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

(end of dropdown for license)

(start of dropdown for changelog)
## Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Changelog is maintained from version 0.3.0 forward.


### [0.4.7b0] - 2026-02-11

### Fixed
- Regression fix (Share + Pool ETL workloads): hardened manager-proxy lifecycle recovery for `Share` write paths that could fail with `OSError: handle is closed` in long-running `Pool.star().map(...)` workers. `_AtomicCounterRegistry` and coordinator enqueue/counter paths now perform best-effort proxy reconnection and a bounded retry, preventing false "Share is stopped" cascades, dropped write commands, and parent `map()` hangs.

- Tests: added a Share primitive regression that forcibly closes a manager proxy handle and verifies counter operations recover automatically.

(start of dropdown for [0.4.7b0])
### [0.4.7b0] - 2026-02-11

#### Fixed
- Regression fix (Pool + TimeThis): `Sktimer` is now fork-safe in subprocess workers. After fork, process-local timer lock/session state is rebuilt automatically, and dead-session purge now uses `sys._current_frames()` instead of `threading.enumerate()` to avoid fork-time deadlocks.

- Regression fix (Share + BreakingCircuit): `Circuit` and `BreakingCircuit` now serialize without carrying live `threading.RLock` internals; deserialization recreates a fresh lock per process. This prevents `Share`/`Pool` hangs when a breaker is assigned to shared state.

(end of dropdown for [0.4.7b0])

(start of dropdown for [0.4.5b0])
### [0.4.5b0] - 2026-02-11

#### Fixed
- Memory leak: `_Coordinator.stop()` skipped `SharedMemory` cleanup when called on an already-stopped coordinator. The early-return path now calls `counter_registry.reset()` to unlink shared memory segments, eliminating the `resource_tracker: leaked shared_memory objects` warning.

- Memory leak: `Share._META_CACHE` used a plain `dict` keyed by class types, preventing garbage collection of classes. Changed to `weakref.WeakKeyDictionary` so classes (and their cached metadata) are collected when no longer referenced.

- Memory leak: `Sktimer._sessions` grew unboundedly as threads were created and destroyed. Added `_purge_dead_sessions()` to remove entries for threads that no longer exist, called automatically during session access.

- Memory leak: `Pool` worker `multiprocessing.Queue` resources were not cleaned up after worker timeout/termination. Added `_drain_queue()` helper that empties, closes, and joins queues after workers complete.

- Memory leak: `_AtomicCounterRegistry.remove_object()` only unlinked `SharedMemory` segments for the "owning" process. If the owner died, segments leaked. Now always attempts `shm.unlink()` on removal regardless of ownership.

- Memory leak: `_Coordinator.destroy()` / `__del__` split — `stop()` no longer shuts down the `SyncManager`, preserving restart capability. `destroy()` handles permanent shutdown. `Share.__exit__` calls `stop()` (restartable), `Share.__del__` calls `destroy()` (final cleanup).

- Thread-safety: `cucumber.serialize()` and `cucumber.deserialize()` used module-level singleton `Serializer`/`Deserializer` instances with mutable per-call state (`seen_objects`, `_object_registry`). Concurrent calls from multiple threads (e.g. `asyncio.gather` + `to_thread`) caused data races — one thread clearing the registry mid-reconstruction. Replaced singletons with per-thread instances via `threading.local()`.

(end of dropdown for [0.4.5b0])

(start of dropdown for [0.4.4b0])
### [0.4.4b0] - 2026-02-10

#### Fixed
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

#### Changed
- Test coverage increased from 80% to 82%.
- CI matrix expanded to 9 jobs: 3 OSes (Ubuntu, macOS, Windows) x 3 Python versions (3.11, 3.12, 3.13).

(end of dropdown for [0.4.4b0])

(start of dropdown for [0.4.0b0])
### [0.4.0b0] - 2026-02-07

#### Added

##### Processing
- `Pool.unordered_map()` method that returns a list in completion order (like `unordered_imap` but returns list instead of iterator).
- `Skprocess.run()` now supports `.timeout()`, `.background()`, and `.asynced()` modifiers for async and background execution.
- `processing.Pipe` for inter-process communication.
- `@autoreconnect(**kwargs)` decorator for Skprocess to automatically reconnect resources after deserialization.
- kwargs structure for `reconnect_all()` and `@autoreconnect`: type-keyed dict with `"*"` defaults and attr-specific overrides.
- Processing benchmark comparing Skprocess vs multiprocessing concurrency.

##### `cucumber` (Serialization)
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

##### Documentation
- Documentation for Reconnectors in `cucumber` how-to-use and how-it-works.
- Documentation for `@autoreconnect` in `processing` how-to-use and how-it-works.

#### Changed
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

(end of dropdown for [0.4.0b0])

(start of dropdown for [0.3.0])
### [0.3.0] - 2026-01-16 — 2026-01-27

#### Added

##### Core
- Initial release contents for all Suitkaise modules: `cucumber`, `circuits`, `processing`, `paths`, `sk`, `timing`.
- Initial type stub files (`.pyi`) for IDE autocompletion.
- `py.typed` marker for PEP 561 compliance.
- `suitkaise` CLI entrypoint with `version`, `info`, `modules`, and `docs` commands.
- CI workflow for running the full test suite with coverage reporting.
- README badges for quick project metadata.

##### `cucumber` (Serialization)
- Cucumber IR helpers: `serialize_ir`, `ir_to_jsonable`, `ir_to_json`, `to_jsonable`, `to_json`.

##### `circuits`
- `Circuit`/`BreakingCircuit` jitter option to spread retry sleep times.

##### `processing`
- `Skprocess.run()` helper to start + wait + return result in one call.
- `Share` now serializes into a live client that reuses the parent coordinator when passed to Pool workers, avoiding duplicate Manager startup and enabling safe cross-process usage.

##### `paths`
- `Skpath.copy_to()` and `Skpath.move_to()` convenience file operations.
- `Skpath.is_empty` property — returns `True` if a directory has no contents. Raises `NotADirectoryError` if called on a file.
- `Skpath.rmdir()` and `Skpath.unlink()` methods for removing directories and files.
- `NotAFileError` exception (inherits `IsADirectoryError`) raised by `Skpath.unlink()` when path is a directory.

##### `sk` (Modifiers)
- `@blocking` decorator to explicitly mark methods/functions as blocking. Enables `.background()` and `.asynced()` for CPU-heavy code that doesn't contain auto-detectable I/O calls.

##### `timing`
- Rolling window support in `Sktimer` (`max_times`) and `@timethis(max_times=...)`.

#### Changed
- Test coverage increased to ~85% (WorstPossibleObject edge cases lower the reported number).

#### Fixed
- Internal handling issues with builtin types and methods on Windows.

#### Performance
- FileIO serialization: >2000µs → 45µs (44x faster)
- BufferedReader serialization: >2000µs → 85µs (23x faster)
- BufferedWriter serialization: >2000µs → 50µs (40x faster)
- FrameType serialization: >2500µs → 12µs (208x faster)

(end of dropdown for [0.3.0])

(end of dropdown for changelog)

(start of dropdown for cli commands)
## CLI Commands

Run `suitkaise` from the terminal after installation. If no command is provided, the help menu is printed.

### `suitkaise --version`

Print the current version of `suitkaise`.

```
$ suitkaise --version
0.4.8b0
```

### `suitkaise info`

Print version, module list, and supported Python versions.

```
$ suitkaise info
Suitkaise 0.4.8b0
Modules: timing, paths, circuits, cucumber, processing, sk
Python: 3.11+
```

### `suitkaise modules`

List all available modules, one per line.

```
$ suitkaise modules
timing
paths
circuits
cucumber
processing
sk
```

### `suitkaise docs`

Download the full `suitkaise` documentation to your project root. Your current working directory must be inside the project root.

```
$ suitkaise docs
```

You can also download docs from Python:

```python
from suitkaise import docs

docs.download()

# or to a specific path within your project
docs.download("path/within/project")
```

To place docs outside your project root, use the `Permission` context manager:

```python
from suitkaise import docs

with docs.Permission():
    docs.download("/Users/joe/Documents")
```

(end of dropdown for cli commands)

(start of dropdown for modules)
## Modules

(start of dropdown for `cucumber`)
### `cucumber`

Serialization engine that eliminates `PicklingError`s by handling types that `pickle`, `cloudpickle`, and `dill` cannot — threads, queues, sockets, generators, database connections, and more. Provides live resource reconnection and supports classes defined in `__main__` for multiprocessing.

```python
from suitkaise.cucumber import (
    serialize,
    deserialize,
    serialize_ir,
    reconnect_all,
    ir_to_jsonable,
    ir_to_json,
    to_jsonable,
    to_json,
    SerializationError,
    DeserializationError,
)
```

Or from the top level:

```python
from suitkaise import serialize, deserialize, reconnect_all
```

(end of dropdown for `cucumber`)

(start of dropdown for `circuits`)
### `circuits`

Circuit breaker module for managing failures with exponential backoff, jitter, and thread-safe coordination. `Circuit` auto-resets after sleeping, ideal for rate limiting and transient failures. `BreakingCircuit` stays broken until manually reset, ideal for coordinated shutdown. `BreakingCircuit` works with `Share` for cross-process failure coordination.

```python
from suitkaise.circuits import (
    Circuit,
    BreakingCircuit,
)
```

Or from the top level:

```python
from suitkaise import Circuit, BreakingCircuit
```

(end of dropdown for `circuits`)

(start of dropdown for `processing`)
### `processing`

Parallel processing module that simplifies multiprocessing with class-based processes (`Skprocess`), easy shared state (`Share`), and automatic serialization using `cucumber`. Supports lifecycle hooks, automatic retries, timeouts, and inter-process communication via `Pipe` and `tell()`/`listen()`.

```python
from suitkaise.processing import (
    Skprocess,
    Pool,
    Share,
    Pipe,
    autoreconnect,
    ProcessTimers,
    ProcessError,
    PreRunError,
    RunError,
    PostRunError,
    OnFinishError,
    ResultError,
    ErrorHandlerError,
    ProcessTimeoutError,
    ResultTimeoutError,
)
```

Or from the top level:

```python
from suitkaise import Skprocess, Pool, Share, Pipe, autoreconnect
```

(end of dropdown for `processing`)

(start of dropdown for `paths`)
### `paths`

Cross-platform path handling with project-relative paths that are identical across machines and operating systems. Automatically detects project root, normalizes path separators, and provides `@autopath` for automatic type conversion. Drop-in upgrade from `pathlib.Path` with project awareness.

```python
from suitkaise.paths import (
    Skpath,
    AnyPath,
    autopath,
    CustomRoot,
    set_custom_root,
    get_custom_root,
    clear_custom_root,
    get_project_root,
    get_caller_path,
    get_current_dir,
    get_cwd,
    get_module_path,
    get_id,
    get_project_paths,
    get_project_structure,
    get_formatted_project_tree,
    is_valid_filename,
    streamline_path,
    PathDetectionError,
    NotAFileError,
)
```

Or from the top level:

```python
from suitkaise import Skpath, AnyPath, autopath
```

(end of dropdown for `paths`)

(start of dropdown for `sk`)
### `sk`

Modifier system that adds retry, timeout, background execution, rate limiting, and async support to any function or class. Modifiers are applied at the call site, not the definition, allowing flexible per-call configuration. Generates `_shared_meta` for efficient `Share` integration on classes.

```python
from suitkaise.sk import (
    sk,
    blocking,
    SkModifierError,
    FunctionTimeoutError,
)
```

Or from the top level:

```python
from suitkaise import sk, blocking
```

(end of dropdown for `sk`)

(start of dropdown for `timing`)
### `timing`

Performance timing with deep statistics (mean, median, stdev, percentiles) and thread-safe measurement. Use the `@timethis` decorator, `TimeThis` context manager, or `Sktimer` directly. Supports pause/resume, discarding bad measurements, rolling windows, and threshold filtering. Works natively with `Share` for cross-process timing aggregation.

```python
from suitkaise.timing import (
    time,
    sleep,
    elapsed,
    Sktimer,
    TimeThis,
    timethis,
    clear_global_timers,
)
```

Or from the top level:

```python
from suitkaise import Sktimer, TimeThis, timethis, time, sleep, elapsed
```

(end of dropdown for `timing`)

(end of dropdown for modules)