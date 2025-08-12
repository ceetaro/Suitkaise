# Suitkaise Multiprocessing — Internal Architecture and Behavior

This document explains how the xprocess engine works under the hood. It is deliberately detailed and walks through the runtime flow, restart logic, timeouts, result passing, pools, and subprocess behavior. For usage-oriented examples, see `concept.md`.

## Top-level structure

- Managers: `CrossProcessing`, `SubProcessing` (process orchestration)
- Processes: `_Process` (base class), `_FunctionProcess` (function wrapper)
- Configuration: `_PConfig` (full), `_QPConfig` (function shorthand)
- Data and stats: `_PData` (process metadata + result), `ProcessStats` (timings/errors)
- Runner: `_ProcessRunner` (executes lifecycle in the child process)
- Pools: `ProcessPool`, `PoolMode`, `PoolTaskError`
- Exceptions: `PreloopError`, `MainLoopError`, `PostLoopError` and timeout variants

Note on naming: internal classes are underscored (e.g., `_Process`, `_PConfig`). The examples in `concept.md` use simplified public-facing names like `Process`, `PConfig` for readability; they correspond to these internal implementations.

## The `_Process` lifecycle (what your class actually does)

Location: `suitkaise/_int/mp/processes.py`

- You implement hooks on a subclass of `_Process`:
  - `__preloop__()` — optional per-iteration setup
  - `__loop__()` — required per-iteration work
  - `__postloop__()` — optional per-iteration cleanup
  - `__onfinish__()` — optional once-per-process finalization
  - `__result__()` — optional return value at the very end
- Timing controls (opt-in, call in `__init__`):
  - Start at: `start_timer_before_preloop()` or `start_timer_before_loop()` (default)
  - End at: `end_timer_after_loop()` (default) or `end_timer_after_postloop()`
- Control methods (you can call these inside your hooks):
  - `rejoin()` — finish the current iteration then stop
  - `skip_and_rejoin()` — stop immediately, skip `__postloop__`
  - `instakill()` — terminate now, no `__onfinish__`, no `__result__`
- Status: `PStatus` (`CREATED`, `STARTING`, `RUNNING`, `STOPPING`, `FINISHED`, `CRASHED`, `KILLED`)
- Loop continuation logic combines multiple signals:
  - if `num_loops` is set and reached → stop
  - if `_PConfig.join_after` loops reached → stop
  - if `_PConfig.join_in` duration elapsed → stop
  - if a control signal (rejoin/skip/kill) is set → stop
  - if cascading shutdown flag from a subprocess is set → stop

Key fields visible to your hooks:
- `self.current_loop` — 1-based loop counter (incremented at the start of each iteration)
- `self.last_loop_time` — duration of the last timed window (based on start/end settings)
- `self.stats` — a `ProcessStats` object; the runtime records loop times, errors, restarts

## The `_ProcessRunner` (how hooks actually run)

Location: `suitkaise/_int/mp/runner.py`

When a process starts, `CrossProcessing` or `ProcessPool` constructs a `_ProcessRunner` in the child process. It performs:

1) Initialization
- Calls `_start_process()` on your `_Process` to set `pid`, status to `RUNNING`, and mark start time.
- Logs initial configuration if `config.log_loops`.

2) Main loop execution
- While `_should_continue_loop()` returns True:
  - Checks for `instakill` or `skip_and_rejoin` control signals — exit immediately if set.
  - Executes a single iteration with granular timeout protection via threads:
    - `__preloop__()` (timeout: `preloop_timeout`)
    - `__loop__()` (timeout: `loop_timeout`)
    - `__postloop__()` (timeout: `postloop_timeout`)
  - If timing is configured to end after loop or postloop, records the duration into stats and `last_loop_time`.
  - After iteration, checks for `rejoin` control signal — exit the loop if set.

3) Error and timeout handling
- Each section’s exceptions are wrapped in a phase-specific error type:
  - `PreloopError`, `MainLoopError`, `PostLoopError`
  - `PreloopTimeoutError`, `MainLoopTimeoutError`, `PostLoopTimeoutError`
- On any of these errors:
  - Status is set to `CRASHED` immediately.
  - Error is recorded in `ProcessStats` and mirrored into the `_PData` (so the parent can read it).
  - Decision: if `config.crash_restart` and restarts remain (< `max_restarts`), return cleanly to allow the manager to restart the process; otherwise re-raise to crash the process with a non-zero exit code.
- On truly unexpected exceptions, it also sets status to `CRASHED`, records details, and re-raises.

4) Finish, `__onfinish__`, and `__result__`
- Unless it was `instakill`, the runner calls your `__onfinish__()`.
- It then calls `__result__()` if you implemented your own (i.e., not the default):
  - The return value is serialized with Cerial (`_serialize`) and pushed to a queue as `('success', serialized_bytes)`.
  - If serialization fails: `('serialize_error', message)` is pushed instead.
  - If `__result__()` itself raises: `('result_error', message)` is pushed.
- If you did not override `__result__()`, it pushes `('success', None)`.
- If the process status is `CRASHED`, the runner forces exit code 1 (so the parent can detect a crash). Otherwise it exits with code 0 (status already set to `FINISHED`).

## What the manager does (parent side)

Location: `suitkaise/_int/mp/managers.py`

### `CrossProcessing`

Registry and monitoring
- `create_process(key, process_setup, config)` creates a new OS process, keeps an internal record, and returns a `_PData` for that key. It injects the `_PData` into your `_Process` instance.
- A background monitoring thread periodically:
  - Updates the `_PData` with current status, pid, and completed loops
  - Checks crashes and performs restarts if `config.crash_restart` is True and `max_restarts` not exceeded

Joining, results, and status
- `join_process(key, timeout=None)` waits for the child process to finish.
- `get_process_result(key, timeout=None)` joins the child, reads from the child’s result queue, and:
  - On `('success', bytes)`, deserializes with Cerial (`_deserialize`) and writes the concrete object into `_PData`, then returns it.
  - On `('serialize_error', message)` or `('result_error', message)`, records the error into `_PData` and returns `None`.
  - If nothing is available, returns `None`.
- `get_process_status(key)` translates exit codes back to `PStatus` (`CRASHED` if non-zero, otherwise `FINISHED` if not already set).
- `list_processes()` exposes a dictionary of tracked information (status, pid, loops, restarts, and remaining time/loops if configured).
- `terminate_process(key, force=False)` uses `_Process`’s control methods: graceful (`rejoin()`) or force (`instakill()`).
- `shutdown(...)` shuts down all processes, attempting graceful stop first, then force-kill remaining ones if requested.

Restart flow (high-level)
- Manager sees not-alive process with a status that’s not `FINISHED`/`KILLED`.
- If restarts remain:
  - Bumps `_restart_count`, resets state (pid, loops, result queue, shared flags), and starts a fresh OS process with a new `_ProcessRunner`.
  - `_PData` is kept and updated; the new run will rewrite results/status there.
- If out of restarts: mark `CRASHED` and stop.

### `SubProcessing`

Subordinate manager for processes created from inside another process.
- Enforces a maximum nesting depth of 2 via `XPROCESS_DEPTH` environment variable.
- API mirrors `CrossProcessing` (create/join/get/list/shutdown) but note termination helpers use signals:
  - `terminate_subprocess(..., force=False)` → sends `SIGUSR1` for graceful
  - `terminate_subprocess(..., force=True)`  → sends `SIGUSR2` for force
- Results are also read from a queue and deserialized just like in `CrossProcessing`.

## `_PData` (the process “handle” you get back)

Location: `suitkaise/_int/mp/pdata.py`

- Contains `pkey`, `pclass`, `pid`, `num_loops`, `completed_loops`, `status`, `result`, and any error string.
- If you access `.result` when there is an error, it raises `ProcessResultError` (so you handle failures explicitly).
- Managers continuously keep `_PData` in sync with the live process status and PID.

## `ProcessStats` (what is recorded)

Location: `suitkaise/_int/mp/stats.py`

- Tracks `start_time`, `end_time`, total loops, per-loop durations (`loop_times`), error events, restart count, timeout count, and placeholders for heartbeats/resources.
- `get_summary()` returns aggregate metrics (avg/fastest/slowest loop, restart count, timeouts, etc.).

## Configuration classes

Location: `suitkaise/_int/mp/configs.py`

### `_PConfig` (full)
- Termination controls: `join_in` (seconds), `join_after` (loops)
- Restart policy: `crash_restart`, `max_restarts`
- Logging: `log_loops`
- Per-section timeouts: `preloop_timeout`, `loop_timeout`, `postloop_timeout`
- Lifecycle: `startup_timeout`, `shutdown_timeout`
- Monitoring: `heartbeat_interval`, `resource_monitoring`
- Helpers: `disable_timeouts()`, `set_quick_timeouts()`, `set_long_timeouts()`, `copy_with_overrides(...)`

### `_QPConfig` (function shorthand)
- For one-shot function tasks; converts to a `_PConfig` via `to_process_config()` with `join_after=1` and a tighter `startup/shutdown` profile and `function_timeout` mapped to the main loop timeout.

## Pools (how tasks are executed in batches)

Location: `suitkaise/_int/mp/pool.py`

Key pieces
- `ProcessPool(size=8, mode=PoolMode.ASYNC)` controls the number of workers and scheduling mode.
- Modes:
  - `ASYNC`: tasks are dispatched as workers become available
  - `PARALLEL`: tasks are dispatched in synchronized batches
- Submitting tasks:
  - `submit(_PTask)` where `_PTask` wraps a process class and optional config
  - `submit(key, process_class, config)` convenience path
  - `submit_function(key, func, args=(), kwargs={}, config=_QPConfig())` wraps a function into `_FunctionProcess`
  - `submit_multiple([...])` and `set_parallel()`/`set_async()` to switch modes
- Collecting results:
  - `get_result(key) -> _PTaskResult` for a specific task (raises `PoolTaskError` on failure)
  - `get_all_results(timeout=None)` for all submitted tasks (raises `PoolTaskError` if any failed)
- Error strategy (important detail): the pool prioritizes the child process exit code; even if the result queue says success, a non-zero exit code is treated as failure. If both indicate success, the queue payload is deserialized using Cerial and attached to the task’s `_PData`.

Worker lifecycle
- A coordinator thread creates workers on demand (up to pool size), assigns tasks, and collects results.
- On completion, a `_PTaskResult` is created with: key, class name, worker PID/number, task order, deserialized result or error, and the `_PData` snapshot.

## Control methods vs control signals

In the child process, control methods set a shared integer signal:
- `rejoin()` → `1` (finish current iteration then stop)
- `skip_and_rejoin()` → `2` (stop immediately, skip `__postloop__`)
- `instakill()` → `3` (terminate without any cleanup/result)

The runner checks these signals at safe points in the loop and exits accordingly.

## Typical status transitions

1) Parent creates process → `_ProcessRunner` starts → status: `STARTING` → `RUNNING`
2) Normal completion → runner calls `__onfinish__` → queues result → `_join_process()` sets status: `FINISHED`
3) Lifecycle error or timeout → status: `CRASHED` → exit code 1
   - If restart enabled and attempts remain, parent restarts with a fresh OS process, preserving the same `_PData` handle
4) Forced kill → status: `KILLED`

## Subprocess depth and signals

`SubProcessing` enforces a maximum nesting depth of 2 via the `XPROCESS_DEPTH` env var. If exceeded, it raises an error immediately. Its `terminate_subprocess` method uses `SIGUSR1` (graceful) and `SIGUSR2` (force) to request shutdown from the parent side.

## Result format details

- Child-to-parent message is a 2-tuple `(status, data)` in the result queue:
  - `('success', cerial_bytes_or_None)`
  - `('serialize_error', str_message)`
  - `('result_error', str_message)`
- Parent deserializes `cerial_bytes` with `_deserialize`. On any error, it records `.error` into `_PData` and returns `None`.

## Where things live (quick map)

- `_Process`, `_FunctionProcess`, `PStatus`: `suitkaise/_int/mp/processes.py`
- `_ProcessRunner`: `suitkaise/_int/mp/runner.py`
- `CrossProcessing`, `SubProcessing`: `suitkaise/_int/mp/managers.py`
- `ProcessPool`, `PoolMode`, `PoolTaskError`: `suitkaise/_int/mp/pool.py`
- `_PConfig`, `_QPConfig`: `suitkaise/_int/mp/configs.py`
- `_PData`: `suitkaise/_int/mp/pdata.py`
- `ProcessStats`: `suitkaise/_int/mp/stats.py`
- Exception classes: `suitkaise/_int/mp/exceptions.py`



