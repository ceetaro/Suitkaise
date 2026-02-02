"""
Pool class for parallel batch processing.

Provides map, imap, async_map, and unordered_imap operations with star() modifier.
Supports both regular functions and Process-inheriting classes.
Uses cucumber for serialization, avoiding pickle limitations.
"""

import multiprocessing
from typing import Any, Callable, Iterator, TypeVar, Generic, Union, Iterable, TYPE_CHECKING
import queue as queue_module

if TYPE_CHECKING:
    from .process_class import Process

T = TypeVar('T')
R = TypeVar('R')


class AsyncResult(Generic[T]):
    """
    Future-like object returned by async_map().
    
    Provides methods to check status and retrieve results.
    """
    
    def __init__(self, result_queues: list, workers: list):
        self._result_queues = result_queues
        self._workers = workers
        self._results: list[T] | None = None
        self._collected = False
    
    def ready(self) -> bool:
        """Check if all results are ready."""
        if self._collected:
            return True
        # Check if all workers are done
        return all(not w.is_alive() for w in self._workers)
    
    def wait(self, timeout: float | None = None) -> None:
        """Block until all results are ready."""
        for w in self._workers:
            w.join(timeout=timeout)
    
    def get(self, timeout: float | None = None) -> list[T]:
        """
        Block until results are ready and return them.
        
        Args:
            timeout: Maximum seconds to wait per result. None = wait forever.
        
        Returns:
            List of results in order.
        
        Raises:
            TimeoutError: If timeout reached before results ready.
        """
        if self._results is not None:
            return self._results
        
        from suitkaise import cucumber
        
        results = []
        for q in self._result_queues:
            try:
                message = q.get(timeout=timeout)
                if message["type"] == "error":
                    error = cucumber.deserialize(message["data"])
                    raise error
                else:
                    results.append(cucumber.deserialize(message["data"]))
            except queue_module.Empty:
                raise TimeoutError("Timeout waiting for result")
        
        self._results = results
        self._collected = True
        return results


class StarModifier:
    """
    Modifier returned by pool.star().
    
    Provides the same methods as Pool, but unpacks tuples as arguments.
    """
    
    def __init__(self, pool: "Pool"):
        self._pool = pool
    
    def map(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Apply function/Process with tuple unpacking, return list of results."""
        return self._pool._map_impl(fn_or_process, iterable, is_star=True)
    
    def imap(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Iterator:
        """Apply function/Process with tuple unpacking, return iterator of ordered results."""
        return self._pool._imap_impl(fn_or_process, iterable, is_star=True)
    
    def async_map(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> AsyncResult:
        """Apply function/Process with tuple unpacking, return AsyncResult immediately."""
        return self._pool._async_map_impl(fn_or_process, iterable, is_star=True)
    
    def unordered_imap(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Iterator:
        """Apply function/Process with tuple unpacking, return iterator of unordered results."""
        return self._pool._unordered_imap_impl(fn_or_process, iterable, is_star=True)


class Pool:
    """
    Pool for parallel batch processing.
    
    Uses cucumber for serialization, supporting complex objects that
    pickle cannot handle. Also supports Process-inheriting classes
    for structured lifecycle management.
    
    Usage:
        pool = Pool(workers=8)
        
        # Simple function
        results = pool.map(process_item, items)
        
        # Process class
        results = pool.map(MyProcessClass, items)
        
        # Async (non-blocking)
        async_result = pool.async_map(fn, items)
        results = async_result.get()
        
        # Unordered (fastest)
        for result in pool.unordered_imap(fn, items):
            ...
        
        # Star modifier (unpack tuples)
        results = pool.star().map(fn, [(1, 2), (3, 4)])
    """
    
    def __init__(self, workers: int | None = None):
        """
        Create a new Pool.
        
        Args:
            workers: Number of worker processes. None = number of CPUs.
        """
        self._workers = workers or multiprocessing.cpu_count()
        self._active_processes: list[multiprocessing.Process] = []
    
    def close(self) -> None:
        """Wait for all active processes to finish."""
        for p in self._active_processes:
            if p.is_alive():
                p.join()
        self._active_processes.clear()
    
    def terminate(self) -> None:
        """Forcefully terminate all active processes."""
        for p in self._active_processes:
            if p.is_alive():
                p.terminate()
        self._active_processes.clear()
    
    def __enter__(self) -> "Pool":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    
    # =========================================================================
    # Modifier method
    # =========================================================================
    
    def star(self) -> StarModifier:
        """
        Return modifier for tuple unpacking.
        
        star().map() unpacks tuples as function arguments.
        star().imap() unpacks tuples as function arguments.
        star().async_map() unpacks tuples as function arguments.
        star().unordered_imap() unpacks tuples as function arguments.
        """
        return StarModifier(self)
    
    # =========================================================================
    # Main methods
    # =========================================================================
    
    def map(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """
        Apply function/Process to each item, return list of results.
        
        Blocks until all items are processed.
        Results are returned in the same order as inputs.
        
        Args:
            fn_or_process: Function or Process class to apply.
            iterable: Items to process.
        
        Returns:
            List of results in order.
        """
        return self._map_impl(fn_or_process, iterable, is_star=False)
    
    def imap(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Iterator:
        """
        Apply function/Process to each item, return iterator of results.
        
        Results are yielded in order. If the next result isn't ready,
        iteration blocks until it is.
        
        Args:
            fn_or_process: Function or Process class to apply.
            iterable: Items to process.
        
        Returns:
            Iterator of results in order.
        """
        return self._imap_impl(fn_or_process, iterable, is_star=False)
    
    def async_map(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> AsyncResult:
        """
        Apply function/Process to each item, return AsyncResult immediately.
        
        Non-blocking. Returns immediately with a future-like object
        that can be checked for completion and used to retrieve results.
        
        Args:
            fn_or_process: Function or Process class to apply.
            iterable: Items to process.
        
        Returns:
            AsyncResult with ready(), wait(), and get() methods.
        """
        return self._async_map_impl(fn_or_process, iterable, is_star=False)
    
    def unordered_imap(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Iterator:
        """
        Apply function/Process to each item, yield results as they complete.
        
        Fastest way to get results, but order is not preserved.
        Results are yielded as soon as they're ready.
        
        Args:
            fn_or_process: Function or Process class to apply.
            iterable: Items to process.
        
        Returns:
            Iterator of results in completion order.
        """
        return self._unordered_imap_impl(fn_or_process, iterable, is_star=False)
    
    # =========================================================================
    # Implementation
    # =========================================================================
    
    def _spawn_workers(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
        is_star: bool
    ) -> tuple[list[multiprocessing.Queue], list[multiprocessing.Process]]:
        """Spawn worker processes for all items."""
        from suitkaise import cucumber
        
        items = list(iterable)
        
        if not items:
            return [], []
        
        # Serialize the function/Process class once
        serialized_fn = cucumber.serialize(fn_or_process)
        
        # Spawn workers for each item
        result_queues = []
        workers = []
        
        for item in items:
            result_queue = multiprocessing.Queue()
            serialized_item = cucumber.serialize(item)
            
            worker = multiprocessing.Process(
                target=_pool_worker,
                args=(serialized_fn, serialized_item, is_star, result_queue)
            )
            worker.start()
            
            result_queues.append(result_queue)
            workers.append(worker)
            self._active_processes.append(worker)
        
        return result_queues, workers
    
    def _map_impl(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
        is_star: bool
    ) -> list:
        """Internal blocking map implementation."""
        from suitkaise import cucumber
        
        result_queues, workers = self._spawn_workers(fn_or_process, iterable, is_star)
        
        if not workers:
            return []
        
        # Block and collect results in order
        results = []
        for q, w in zip(result_queues, workers):
            w.join()
            try:
                message = q.get(timeout=1.0)
                if message["type"] == "error":
                    error = cucumber.deserialize(message["data"])
                    raise error
                else:
                    results.append(cucumber.deserialize(message["data"]))
            except queue_module.Empty:
                results.append(None)
        
        # Clean up
        for w in workers:
            if w in self._active_processes:
                self._active_processes.remove(w)
        
        return results
    
    def _imap_impl(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
        is_star: bool
    ) -> Iterator:
        """Internal blocking ordered imap implementation."""
        result_queues, workers = self._spawn_workers(fn_or_process, iterable, is_star)
        
        if not workers:
            return iter([])
        
        return _ordered_results(result_queues, workers, self._active_processes)
    
    def _async_map_impl(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
        is_star: bool
    ) -> AsyncResult:
        """Internal async map implementation."""
        result_queues, workers = self._spawn_workers(fn_or_process, iterable, is_star)
        return AsyncResult(result_queues, workers)
    
    def _unordered_imap_impl(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
        is_star: bool
    ) -> Iterator:
        """Internal unordered imap implementation."""
        result_queues, workers = self._spawn_workers(fn_or_process, iterable, is_star)
        
        if not workers:
            return iter([])
        
        return _unordered_results(result_queues, workers, self._active_processes)


def _ordered_results(
    result_queues: list,
    workers: list,
    active_processes: list
) -> Iterator:
    """Yield results in submission order."""
    from suitkaise import cucumber
    
    for q, w in zip(result_queues, workers):
        w.join()
        try:
            message = q.get(timeout=1.0)
            if message["type"] == "error":
                error = cucumber.deserialize(message["data"])
                raise error
            else:
                yield cucumber.deserialize(message["data"])
        except queue_module.Empty:
            yield None
        finally:
            if w in active_processes:
                active_processes.remove(w)


def _unordered_results(
    result_queues: list,
    workers: list,
    active_processes: list
) -> Iterator:
    """Yield results as they complete."""
    from suitkaise import cucumber
    
    remaining = list(zip(result_queues, workers))
    
    while remaining:
        for i, (q, w) in enumerate(remaining):
            if not w.is_alive():
                # Worker finished, get result
                try:
                    message = q.get(timeout=0.1)
                    if message["type"] == "error":
                        error = cucumber.deserialize(message["data"])
                        raise error
                    else:
                        yield cucumber.deserialize(message["data"])
                except queue_module.Empty:
                    yield None
                finally:
                    if w in active_processes:
                        active_processes.remove(w)
                    remaining.pop(i)
                break
        else:
            # No worker finished yet, wait a bit
            import time
            time.sleep(0.01)


def _pool_worker(
    serialized_fn: bytes,
    serialized_item: bytes,
    is_star: bool,
    result_queue: multiprocessing.Queue
) -> None:
    """
    Worker function that runs in subprocess.
    
    Uses cucumber to deserialize function and arguments.
    Handles both regular functions and Process classes.
    """
    from suitkaise import cucumber
    
    try:
        # Deserialize using cucumber
        fn_or_process = cucumber.deserialize(serialized_fn)
        item = cucumber.deserialize(serialized_item)
        
        # Unpack args if star mode
        if is_star:
            if isinstance(item, tuple):
                args = item
            else:
                args = (item,)
        else:
            args = (item,)
        
        # Check if this is a Process class
        from .process_class import Process
        
        if isinstance(fn_or_process, type) and issubclass(fn_or_process, Process):
            # Create Process instance with args
            process_instance = fn_or_process(*args)
            
            # Run the process inline (we're already in a subprocess)
            result = _run_process_inline(process_instance)
        else:
            # Regular function
            if is_star:
                result = fn_or_process(*args)
            else:
                result = fn_or_process(item)
        
        # Serialize and send result
        serialized_result = cucumber.serialize(result)
        result_queue.put({
            "type": "result",
            "data": serialized_result
        })
        
    except Exception as e:
        # Serialize and send error
        try:
            serialized_error = cucumber.serialize(e)
            result_queue.put({
                "type": "error",
                "data": serialized_error
            })
        except Exception:
            # If we can't serialize the error, send a generic one
            import traceback
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            result_queue.put({
                "type": "error",
                "data": cucumber.serialize(RuntimeError(error_msg))
            })


def _run_process_inline(process: "Process") -> Any:
    """
    Run a Process instance inline (not in a subprocess).
    
    Used by Pool workers since they're already in a subprocess.
    Replicates full engine behavior including:
    - config.runs (looping)
    - config.lives (retry on error)
    - config.timeouts (timeout enforcement)
    - config.join_in (max total time)
    - Timing for all lifecycle sections
    """
    import threading
    from .timers import ProcessTimers
    from .timeout import run_with_timeout
    from .errors import (
        PreRunError, RunError, PostRunError,
        OnFinishError, ResultError, ProcessTimeoutError
    )
    from suitkaise import sktime
    
    # Ensure timers exist
    if process.timers is None:
        process.timers = ProcessTimers()
    
    # Initialize run state
    process._current_run = 0
    process._start_time = sktime.time()
    
    # Create stop event so self.stop() works in Pool
    # Using threading.Event since we're already in a subprocess
    stop_event = threading.Event()
    process._stop_event = stop_event  # type: ignore[assignment]
    
    # Track lives for retry system
    lives_remaining = process.config.lives
    
    def _unwrap_method(m: Any) -> Callable:
        """Unwrap TimedMethod wrapper if present."""
        return getattr(m, '_method', m)
    
    def _should_continue() -> bool:
        """Check if run loop should continue."""
        # Check stop signal (self.stop() was called)
        if stop_event.is_set():
            return False
        
        # Check run count limit
        if process.config.runs is not None:
            if process._current_run >= process.config.runs:
                return False
        
        # Check time limit (join_in)
        if process.config.join_in is not None and process._start_time is not None:
            elapsed = sktime.elapsed(process._start_time)
            if elapsed >= process.config.join_in:
                return False
        
        return True
    
    def _run_section_timed(method_name: str, timer_name: str, error_class: type) -> None:
        """Run a lifecycle section with timing, timeout, and error handling."""
        method_attr = getattr(process, method_name)
        method = _unwrap_method(method_attr)
        
        timeout = getattr(process.config.timeouts, timer_name, None)
        
        # Get timer (we ensured timers exist above)
        assert process.timers is not None
        timer = process.timers._ensure_timer(timer_name)
        
        timer.start()
        try:
            run_with_timeout(
                method,
                timeout,
                method_name,
                process._current_run
            )
            timer.stop()
        except ProcessTimeoutError:
            timer.discard()
            raise
        except Exception as e:
            timer.discard()
            raise error_class(process._current_run, e) from e
    
    while lives_remaining > 0:
        try:
            # Main execution loop
            while _should_continue():
                # === PRERUN ===
                _run_section_timed('__prerun__', 'prerun', PreRunError)
                
                if stop_event.is_set():
                    break
                
                # === RUN ===
                _run_section_timed('__run__', 'run', RunError)
                
                if stop_event.is_set():
                    break
                
                # === POSTRUN ===
                _run_section_timed('__postrun__', 'postrun', PostRunError)
                
                # Increment run counter
                process._current_run += 1
                
                # Update full_run timer
                if process.timers is not None:
                    process.timers._update_full_run()
            
            # === Normal exit - run finish sequence ===
            return _run_finish_sequence_inline(process)
            
        except (PreRunError, RunError, PostRunError, ProcessTimeoutError) as e:
            # Error in run - check if we have lives to retry
            lives_remaining -= 1
            
            if lives_remaining > 0:
                # Retry: keep user state and run counter, retry current iteration
                process.config.lives = lives_remaining
                continue
            else:
                # No lives left - run error sequence
                return _run_error_sequence_inline(process, e)


def _run_finish_sequence_inline(process: "Process") -> Any:
    """Run __onfinish__ and __result__, return result."""
    from .timeout import run_with_timeout
    from .errors import OnFinishError, ResultError, ProcessTimeoutError
    
    def _unwrap_method(m: Any) -> Callable:
        return getattr(m, '_method', m)
    
    # === ONFINISH ===
    method = _unwrap_method(process.__onfinish__)
    timeout = process.config.timeouts.onfinish
    
    timer = None
    if process.timers is not None:
        timer = process.timers._ensure_timer('onfinish')
        timer.start()
    
    try:
        run_with_timeout(method, timeout, '__onfinish__', process._current_run)
    except ProcessTimeoutError:
        raise
    except Exception as e:
        raise OnFinishError(process._current_run, e) from e
    finally:
        if timer is not None:
            timer.stop()
    
    # === RESULT ===
    result_method = _unwrap_method(process.__result__)
    result_timeout = process.config.timeouts.result
    
    result_timer = None
    if process.timers is not None:
        result_timer = process.timers._ensure_timer('result')
        result_timer.start()
    
    try:
        result = run_with_timeout(result_method, result_timeout, '__result__', process._current_run)
    except ProcessTimeoutError:
        raise
    except Exception as e:
        raise ResultError(process._current_run, e) from e
    finally:
        if result_timer is not None:
            result_timer.stop()
    
    return result


def _run_error_sequence_inline(process: "Process", error: BaseException) -> Any:
    """Call __error__ and return its result."""
    from .timeout import run_with_timeout
    
    def _unwrap_method(m: Any) -> Callable:
        return getattr(m, '_method', m)
    
    # Set error on process for __error__ to access
    process.error = error
    
    error_method = _unwrap_method(process.__error__)
    error_timeout = process.config.timeouts.error
    
    error_timer = None
    if process.timers is not None:
        error_timer = process.timers._ensure_timer('error')
        error_timer.start()
    
    try:
        error_result = run_with_timeout(
            error_method,
            error_timeout,
            '__error__',
            process._current_run
        )
    except Exception:
        # If __error__ itself fails, re-raise the original error
        raise error
    finally:
        if error_timer is not None:
            error_timer.stop()
    
    # If __error__ returns an exception, raise it
    if isinstance(error_result, BaseException):
        raise error_result
    
    return error_result
