"""
Pool class for parallel batch processing.

Provides map, imap, async_map, and unordered_imap operations with star() modifier.
Supports both regular functions and Skprocess-inheriting classes.
Uses cerial for serialization, avoiding pickle limitations.
"""

import asyncio
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable, Iterator, TypeVar, Generic, Union, Iterable, TYPE_CHECKING
import queue as queue_module

if TYPE_CHECKING:
    from .process_class import Skprocess

T = TypeVar('T')
R = TypeVar('R')

# Shared executor for background operations
_pool_executor: ThreadPoolExecutor | None = None

def _get_pool_executor() -> ThreadPoolExecutor:
    """Get or create the shared thread pool executor for Pool operations."""
    global _pool_executor
    if _pool_executor is None:
        _pool_executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="pool_bg_")
    return _pool_executor


# =============================================================================
# Pool Method Modifiers
# =============================================================================

class _PoolMapModifier:
    """
    Bound method wrapper for Pool.map with modifier support.
    
    Usage:
        pool.map(fn, items)                    # sync, blocks
        pool.map.timeout(30)(fn, items)        # sync with timeout
        pool.map.background()(fn, items)       # returns Future
        await pool.map.asynced()(fn, items)    # async
    """
    
    def __init__(self, pool: "Pool", is_star: bool = False):
        self._pool = pool
        self._is_star = is_star
    
    def __call__(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
    ) -> list:
        """Apply function/Skprocess to each item, return list of results."""
        return self._pool._map_impl(fn_or_process, iterable, is_star=self._is_star)
    
    def timeout(self, seconds: float) -> "_PoolMapTimeoutModifier":
        """Add timeout to the map operation."""
        return _PoolMapTimeoutModifier(self._pool, self._is_star, seconds)
    
    def background(self) -> "_PoolMapBackgroundModifier":
        """Run map in background thread, return Future."""
        return _PoolMapBackgroundModifier(self._pool, self._is_star)
    
    def asynced(self) -> "_PoolMapAsyncModifier":
        """Get async version of map."""
        return _PoolMapAsyncModifier(self._pool, self._is_star)


class _PoolMapTimeoutModifier:
    """Timeout modifier for Pool.map."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute map with timeout."""
        return self._pool._map_impl(fn_or_process, iterable, is_star=self._is_star, timeout=self._timeout)
    
    def background(self) -> "_PoolMapTimeoutBackgroundModifier":
        """Run map with timeout in background thread."""
        return _PoolMapTimeoutBackgroundModifier(self._pool, self._is_star, self._timeout)
    
    def asynced(self) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        timeout = self._timeout
        
        async def async_map_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(pool._map_impl, fn_or_process, iterable, is_star, None),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.map timed out after {timeout}s")
        
        return async_map_with_timeout


class _PoolMapTimeoutBackgroundModifier:
    """Background modifier for Pool.map with timeout."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute map with timeout in background, return Future."""
        executor = _get_pool_executor()
        return executor.submit(
            self._pool._map_impl, fn_or_process, iterable, self._is_star, self._timeout
        )


class _PoolMapBackgroundModifier:
    """Background modifier for Pool.map."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        self._pool = pool
        self._is_star = is_star
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute map in background, return Future."""
        executor = _get_pool_executor()
        return executor.submit(self._pool._map_impl, fn_or_process, iterable, self._is_star, None)
    
    def timeout(self, seconds: float) -> "_PoolMapTimeoutBackgroundModifier":
        """Add timeout to background map."""
        return _PoolMapTimeoutBackgroundModifier(self._pool, self._is_star, seconds)


class _PoolMapAsyncModifier:
    """Async modifier for Pool.map."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        self._pool = pool
        self._is_star = is_star
    
    async def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute map asynchronously."""
        return await asyncio.to_thread(self._pool._map_impl, fn_or_process, iterable, self._is_star, None)
    
    def timeout(self, seconds: float) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        
        async def async_map_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            try:
                return await asyncio.wait_for(
                    asyncio.to_thread(pool._map_impl, fn_or_process, iterable, is_star, None),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.map timed out after {seconds}s")
        
        return async_map_with_timeout


class _PoolImapModifier:
    """
    Bound method wrapper for Pool.imap with modifier support.
    """
    
    def __init__(self, pool: "Pool", is_star: bool = False):
        self._pool = pool
        self._is_star = is_star
    
    def __call__(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
    ) -> Iterator:
        """Apply function/Skprocess to each item, return iterator of results."""
        return self._pool._imap_impl(fn_or_process, iterable, is_star=self._is_star)
    
    def timeout(self, seconds: float) -> "_PoolImapTimeoutModifier":
        """Add timeout to the imap operation."""
        return _PoolImapTimeoutModifier(self._pool, self._is_star, seconds)
    
    def background(self) -> "_PoolImapBackgroundModifier":
        """Run imap collection in background, return Future of list."""
        return _PoolImapBackgroundModifier(self._pool, self._is_star)
    
    def asynced(self) -> "_PoolImapAsyncModifier":
        """Get async version of imap (returns list, not iterator)."""
        return _PoolImapAsyncModifier(self._pool, self._is_star)


class _PoolImapTimeoutModifier:
    """Timeout modifier for Pool.imap."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Iterator:
        """Execute imap with timeout."""
        return self._pool._imap_impl(fn_or_process, iterable, is_star=self._is_star, timeout=self._timeout)


class _PoolImapBackgroundModifier:
    """Background modifier for Pool.imap (collects to list)."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        self._pool = pool
        self._is_star = is_star
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute imap in background, return Future of list."""
        def collect_imap():
            return list(self._pool._imap_impl(fn_or_process, iterable, self._is_star, None))
        
        executor = _get_pool_executor()
        return executor.submit(collect_imap)


class _PoolImapAsyncModifier:
    """Async modifier for Pool.imap (returns list)."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        self._pool = pool
        self._is_star = is_star
    
    async def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute imap asynchronously (returns list)."""
        def collect_imap():
            return list(self._pool._imap_impl(fn_or_process, iterable, self._is_star, None))
        
        return await asyncio.to_thread(collect_imap)
    
    def timeout(self, seconds: float) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        
        async def async_imap_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            def collect_imap():
                return list(pool._imap_impl(fn_or_process, iterable, is_star, None))
            
            try:
                return await asyncio.wait_for(asyncio.to_thread(collect_imap), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.imap timed out after {seconds}s")
        
        return async_imap_with_timeout


# =============================================================================
# Unordered Imap Modifiers
# =============================================================================

class _PoolUnorderedImapModifier:
    """
    Bound method wrapper for Pool.unordered_imap with modifier support.
    """
    
    def __init__(self, pool: "Pool", is_star: bool = False):
        self._pool = pool
        self._is_star = is_star
    
    def __call__(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
    ) -> Iterator:
        """Apply function/Skprocess to each item, yield results as they complete."""
        return self._pool._unordered_imap_impl(fn_or_process, iterable, is_star=self._is_star)
    
    def timeout(self, seconds: float) -> "_PoolUnorderedImapTimeoutModifier":
        """Add timeout to unordered_imap - raises if any result takes too long."""
        return _PoolUnorderedImapTimeoutModifier(self._pool, self._is_star, seconds)
    
    def background(self) -> "_PoolUnorderedImapBackgroundModifier":
        """Run unordered_imap collection in background, return Future of list."""
        return _PoolUnorderedImapBackgroundModifier(self._pool, self._is_star)
    
    def asynced(self) -> "_PoolUnorderedImapAsyncModifier":
        """Get async version of unordered_imap (returns list)."""
        return _PoolUnorderedImapAsyncModifier(self._pool, self._is_star)


class _PoolUnorderedImapTimeoutModifier:
    """Timeout modifier for Pool.unordered_imap."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Iterator:
        """Execute unordered_imap with timeout per result."""
        return self._pool._unordered_imap_impl(
            fn_or_process, iterable, is_star=self._is_star, timeout=self._timeout
        )
    
    def background(self) -> "_PoolUnorderedImapTimeoutBackgroundModifier":
        """Run with timeout in background."""
        return _PoolUnorderedImapTimeoutBackgroundModifier(self._pool, self._is_star, self._timeout)
    
    def asynced(self) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        timeout = self._timeout
        
        async def async_unordered_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            def collect():
                return list(pool._unordered_imap_impl(fn_or_process, iterable, is_star, timeout))
            
            try:
                return await asyncio.wait_for(asyncio.to_thread(collect), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.unordered_imap timed out after {timeout}s")
        
        return async_unordered_with_timeout


class _PoolUnorderedImapTimeoutBackgroundModifier:
    """Background modifier for Pool.unordered_imap with timeout."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute unordered_imap with timeout in background."""
        def collect():
            return list(self._pool._unordered_imap_impl(
                fn_or_process, iterable, self._is_star, self._timeout
            ))
        
        executor = _get_pool_executor()
        return executor.submit(collect)


class _PoolUnorderedImapBackgroundModifier:
    """Background modifier for Pool.unordered_imap (collects to list)."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        self._pool = pool
        self._is_star = is_star
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute unordered_imap in background, return Future of list."""
        def collect():
            return list(self._pool._unordered_imap_impl(fn_or_process, iterable, self._is_star))
        
        executor = _get_pool_executor()
        return executor.submit(collect)
    
    def timeout(self, seconds: float) -> "_PoolUnorderedImapTimeoutBackgroundModifier":
        """Add timeout to background unordered_imap."""
        return _PoolUnorderedImapTimeoutBackgroundModifier(self._pool, self._is_star, seconds)


class _PoolUnorderedImapAsyncModifier:
    """Async modifier for Pool.unordered_imap (returns list)."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        self._pool = pool
        self._is_star = is_star
    
    async def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute unordered_imap asynchronously (returns list)."""
        def collect():
            return list(self._pool._unordered_imap_impl(fn_or_process, iterable, self._is_star))
        
        return await asyncio.to_thread(collect)
    
    def timeout(self, seconds: float) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        
        async def async_unordered_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            def collect():
                return list(pool._unordered_imap_impl(fn_or_process, iterable, is_star))
            
            try:
                return await asyncio.wait_for(asyncio.to_thread(collect), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.unordered_imap timed out after {seconds}s")
        
        return async_unordered_with_timeout


# =============================================================================
# Star Modifier
# =============================================================================

class StarModifier:
    """
    Modifier returned by pool.star().
    
    Provides the same methods as Pool, but unpacks tuples as arguments.
    """
    
    def __init__(self, pool: "Pool"):
        self._pool = pool
    
    @property
    def map(self) -> _PoolMapModifier:
        """Get map method with tuple unpacking and modifier support."""
        return _PoolMapModifier(self._pool, is_star=True)
    
    @property
    def imap(self) -> _PoolImapModifier:
        """Get imap method with tuple unpacking and modifier support."""
        return _PoolImapModifier(self._pool, is_star=True)
    
    @property
    def unordered_imap(self) -> _PoolUnorderedImapModifier:
        """Get unordered_imap method with tuple unpacking and modifier support."""
        return _PoolUnorderedImapModifier(self._pool, is_star=True)


class Pool:
    """
    Pool for parallel batch processing.
    
    Uses cerial for serialization, supporting complex objects that
    pickle cannot handle. Also supports Skprocess-inheriting classes
    for structured lifecycle management.
    
    Usage:
        pool = Pool(workers=8)
        
        # Simple function
        results = pool.map(fn, items)
        
        # Skprocess class
        results = pool.map(MyProcessClass, items)
        
        # With modifiers
        results = pool.map.timeout(30.0)(fn, items)
        future = pool.map.background()(fn, items)
        results = await pool.map.asynced()(fn, items)
        
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
            workers: Max concurrent workers. None = number of CPUs.
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
        star().unordered_imap() unpacks tuples as function arguments.
        """
        return StarModifier(self)
    
    # =========================================================================
    # Main methods with modifier support
    # =========================================================================
    
    @property
    def map(self) -> _PoolMapModifier:
        """
        ────────────────────────────────────────────────────────
            ```python
            # Sync - blocks until all complete
            results = pool.map(fn, items)
            
            # With modifiers
            results = pool.map.timeout(30.0)(fn, items)
            future = pool.map.background()(fn, items)
            results = await pool.map.asynced()(fn, items)
            ```
        ────────────────────────────────────────────────────────
        
        Apply function/Skprocess to each item, return list of results.
        
        Blocks until all items are processed.
        Results are returned in the same order as inputs.
        
        Args:
            fn_or_process: Function or Skprocess class to apply.
            iterable: Items to process.
        
        Returns:
            List of results in order.
        
        Modifiers:
            .timeout(seconds): Raise TimeoutError if exceeded
            .background(): Return Future immediately
            .asynced(): Return coroutine for await
        """
        return _PoolMapModifier(self, is_star=False)
    
    @property
    def imap(self) -> _PoolImapModifier:
        """
        ────────────────────────────────────────────────────────
            ```python
            # Sync - iterator, blocks on each next()
            for result in pool.imap(fn, items):
                process(result)
            
            # With timeout
            for result in pool.imap.timeout(30.0)(fn, items):
                process(result)
            
            # Background (collects to list)
            future = pool.imap.background()(fn, items)
            results = future.result()
            
            # Async (collects to list)
            results = await pool.imap.asynced()(fn, items)
            ```
        ────────────────────────────────────────────────────────
        
        Apply function/Skprocess to each item, return iterator of results.
        
        Results are yielded in order. If the next result isn't ready,
        iteration blocks until it is.
        
        Args:
            fn_or_process: Function or Skprocess class to apply.
            iterable: Items to process.
        
        Returns:
            Iterator of results in order.
        
        Modifiers:
            .timeout(seconds): Raise TimeoutError if exceeded
            .background(): Return Future of list
            .asynced(): Return coroutine for list
        """
        return _PoolImapModifier(self, is_star=False)
    
    @property
    def unordered_imap(self) -> _PoolUnorderedImapModifier:
        """
        ────────────────────────────────────────────────────────
            ```python
            # Sync - iterator, yields as results complete
            for result in pool.unordered_imap(fn, items):
                process(result)
            
            # With timeout
            for result in pool.unordered_imap.timeout(30.0)(fn, items):
                process(result)
            
            # Background (collects to list)
            future = pool.unordered_imap.background()(fn, items)
            results = future.result()
            
            # Async (collects to list)
            results = await pool.unordered_imap.asynced()(fn, items)
            ```
        ────────────────────────────────────────────────────────
        
        Apply function/Skprocess to each item, yield results as they complete.
        
        Fastest way to get results, but order is not preserved.
        Results are yielded as soon as they're ready.
        
        Args:
            fn_or_process: Function or Skprocess class to apply.
            iterable: Items to process.
        
        Returns:
            Iterator of results in completion order.
        
        Modifiers:
            .timeout(seconds): Raise TimeoutError if exceeded
            .background(): Return Future of list
            .asynced(): Return coroutine for list
        """
        return _PoolUnorderedImapModifier(self, is_star=False)
    
    # =========================================================================
    # Implementation
    # =========================================================================
    
    def _spawn_worker(
        self,
        serialized_fn: bytes,
        serialized_item: bytes,
        is_star: bool,
    ) -> tuple[multiprocessing.Queue, multiprocessing.Process]:
        """Spawn a single worker for one item."""
        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        worker = multiprocessing.Process(
            target=_pool_worker,
            args=(serialized_fn, serialized_item, is_star, result_queue),
        )
        worker.start()
        self._active_processes.append(worker)
        return result_queue, worker
    
    def _map_impl(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
        is_star: bool,
        timeout: float | None = None,
    ) -> list:
        """Internal blocking map implementation."""
        from suitkaise import cerial
        
        items = list(iterable)
        if not items:
            return []
        
        # Serialize the function/Skprocess class once
        serialized_fn = cerial.serialize(fn_or_process)
        
        max_workers = self._workers
        if max_workers is None:
            max_workers = len(items)
        
        results = [None] * len(items)
        active: list[tuple[int, multiprocessing.Queue, multiprocessing.Process]] = []
        next_index = 0
        
        def start_one(idx: int) -> None:
            serialized_item = cerial.serialize(items[idx])
            q, w = self._spawn_worker(serialized_fn, serialized_item, is_star)
            active.append((idx, q, w))
        
        while active or next_index < len(items):
            while next_index < len(items) and len(active) < max_workers:
                start_one(next_index)
                next_index += 1
            
            for idx, q, w in list(active):
                w.join(timeout=timeout)
                
                if w.is_alive():
                    w.terminate()
                    raise TimeoutError(f"Pool.map worker {idx} timed out after {timeout}s")
                
                try:
                    message = q.get(timeout=1.0)
                    if message["type"] == "error":
                        error = cerial.deserialize(message["data"])
                        raise error
                    results[idx] = cerial.deserialize(message["data"])
                except queue_module.Empty:
                    results[idx] = None
                finally:
                    if w in self._active_processes:
                        self._active_processes.remove(w)
                    active.remove((idx, q, w))
                break
        
        return results
    
    def _imap_impl(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
        is_star: bool,
        timeout: float | None = None,
    ) -> Iterator:
        """Internal blocking ordered imap implementation."""
        from suitkaise import cerial
        
        items = list(iterable)
        if not items:
            return iter([])
        
        serialized_fn = cerial.serialize(fn_or_process)
        max_workers = self._workers
        if max_workers is None:
            max_workers = len(items)
        
        def generator() -> Iterator:
            active: dict[int, tuple[multiprocessing.Queue, multiprocessing.Process]] = {}
            next_index = 0
            next_yield = 0
            
            def start_one(idx: int) -> None:
                serialized_item = cerial.serialize(items[idx])
                q, w = self._spawn_worker(serialized_fn, serialized_item, is_star)
                active[idx] = (q, w)
            
            while next_yield < len(items):
                while next_index < len(items) and len(active) < max_workers:
                    start_one(next_index)
                    next_index += 1
                
                if next_yield not in active:
                    # if not started yet, loop to start
                    continue
                
                q, w = active[next_yield]
                w.join(timeout=timeout)
                
                if w.is_alive():
                    w.terminate()
                    raise TimeoutError(f"Pool.imap worker {next_yield} timed out after {timeout}s")
                
                try:
                    message = q.get(timeout=1.0)
                    if message["type"] == "error":
                        error = cerial.deserialize(message["data"])
                        raise error
                    yield cerial.deserialize(message["data"])
                except queue_module.Empty:
                    yield None
                finally:
                    if w in self._active_processes:
                        self._active_processes.remove(w)
                    active.pop(next_yield, None)
                    next_yield += 1
        
        return generator()
    
    def _unordered_imap_impl(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
        is_star: bool,
        timeout: float | None = None,
    ) -> Iterator:
        """Internal unordered imap implementation."""
        from suitkaise import cerial
        import time as time_module
        
        items = list(iterable)
        if not items:
            return iter([])
        
        serialized_fn = cerial.serialize(fn_or_process)
        max_workers = self._workers
        if max_workers is None:
            max_workers = len(items)
        
        def generator() -> Iterator:
            active: list[tuple[int, multiprocessing.Queue, multiprocessing.Process]] = []
            next_index = 0
            start_time = time_module.perf_counter() if timeout else None
            
            def start_one(idx: int) -> None:
                serialized_item = cerial.serialize(items[idx])
                q, w = self._spawn_worker(serialized_fn, serialized_item, is_star)
                active.append((idx, q, w))
            
            while active or next_index < len(items):
                while next_index < len(items) and len(active) < max_workers:
                    start_one(next_index)
                    next_index += 1
                
                for i, (idx, q, w) in enumerate(list(active)):
                    if w.is_alive():
                        continue
                    
                    w.join(timeout=0)
                    try:
                        message = q.get(timeout=1.0)
                        if message["type"] == "error":
                            error = cerial.deserialize(message["data"])
                            raise error
                        yield cerial.deserialize(message["data"])
                    except queue_module.Empty:
                        yield None
                    finally:
                        if w in self._active_processes:
                            self._active_processes.remove(w)
                        active.pop(i)
                    break
                else:
                    if timeout and start_time is not None:
                        elapsed = time_module.perf_counter() - start_time
                        if elapsed >= timeout:
                            for _, _, w in active:
                                if w.is_alive():
                                    w.terminate()
                            raise TimeoutError(f"Pool.unordered_imap timed out after {timeout}s")
                    time_module.sleep(0.01)
        
        return generator()


def _ordered_results(
    result_queues: list,
    workers: list,
    active_processes: list,
    timeout: float | None = None,
) -> Iterator:
    """Yield results in submission order."""
    from suitkaise import cerial
    
    for i, (q, w) in enumerate(zip(result_queues, workers)):
        w.join(timeout=timeout)
        
        # Check if worker timed out
        if w.is_alive():
            w.terminate()
            raise TimeoutError(f"Pool.imap worker {i} timed out after {timeout}s")
        
        try:
            message = q.get(timeout=1.0)
            if message["type"] == "error":
                error = cerial.deserialize(message["data"])
                raise error
            else:
                yield cerial.deserialize(message["data"])
        except queue_module.Empty:
            yield None
        finally:
            if w in active_processes:
                active_processes.remove(w)


def _unordered_results(
    result_queues: list,
    workers: list,
    active_processes: list,
    timeout: float | None = None,
) -> Iterator:
    """Yield results as they complete."""
    from suitkaise import cerial
    import time as time_module
    
    remaining = list(zip(result_queues, workers))
    start_time = time_module.perf_counter() if timeout else None
    
    while remaining:
        # Check timeout
        if timeout is not None:
            elapsed = time_module.perf_counter() - start_time
            if elapsed >= timeout:
                # Terminate remaining workers
                for q, w in remaining:
                    if w.is_alive():
                        w.terminate()
                    if w in active_processes:
                        active_processes.remove(w)
                raise TimeoutError(f"Pool.unordered_imap timed out after {timeout}s")
        
        for i, (q, w) in enumerate(remaining):
            if not w.is_alive():
                # Worker finished, get result
                try:
                    message = q.get(timeout=0.1)
                    if message["type"] == "error":
                        error = cerial.deserialize(message["data"])
                        raise error
                    else:
                        yield cerial.deserialize(message["data"])
                except queue_module.Empty:
                    yield None
                finally:
                    if w in active_processes:
                        active_processes.remove(w)
                    remaining.pop(i)
                break
        else:
            # No worker finished yet, wait a bit
            time_module.sleep(0.01)


def _pool_worker(
    serialized_fn: bytes,
    serialized_item: bytes,
    is_star: bool,
    result_queue: multiprocessing.Queue
) -> None:
    """
    Worker function that runs in subprocess.
    
    Uses cerial to deserialize function and arguments.
    Handles both regular functions and Skprocess classes.
    """
    from suitkaise import cerial
    
    try:
        # Deserialize using cerial
        fn_or_process = cerial.deserialize(serialized_fn)
        item = cerial.deserialize(serialized_item)
        
        # Unpack args if star mode
        if is_star:
            if isinstance(item, tuple):
                args = item
            else:
                args = (item,)
        else:
            args = (item,)
        
        # Check if this is a Skprocess class
        from .process_class import Skprocess
        
        if isinstance(fn_or_process, type) and issubclass(fn_or_process, Skprocess):
            # Create Skprocess instance with args
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
        serialized_result = cerial.serialize(result)
        result_queue.put({
            "type": "result",
            "data": serialized_result
        })
        
    except Exception as e:
        # Serialize and send error
        try:
            serialized_error = cerial.serialize(e)
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
                "data": cerial.serialize(RuntimeError(error_msg))
            })


def _run_process_inline(process: "Skprocess") -> Any:
    """
    Run a Skprocess instance inline (not in a subprocess).
    
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
    lives_remaining = process.process_config.lives
    
    def _unwrap_method(m: Any) -> Callable:
        """Unwrap TimedMethod wrapper if present."""
        return getattr(m, '_method', m)
    
    def _should_continue() -> bool:
        """Check if run loop should continue."""
        # Check stop signal (self.stop() was called)
        if stop_event.is_set():
            return False
        
        # Check run count limit
        if process.process_config.runs is not None:
            if process._current_run >= process.process_config.runs:
                return False
        
        # Check time limit (join_in)
        if process.process_config.join_in is not None and process._start_time is not None:
            elapsed = sktime.elapsed(process._start_time)
            if elapsed >= process.process_config.join_in:
                return False
        
        return True
    
    def _run_section_timed(method_name: str, timer_name: str, error_class: type) -> None:
        """Run a lifecycle section with timing, timeout, and error handling."""
        method_attr = getattr(process, method_name)
        method = _unwrap_method(method_attr)
        
        timeout = getattr(process.process_config.timeouts, timer_name, None)
        
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
                process.process_config.lives = lives_remaining
                continue
            else:
                # No lives left - run error sequence
                return _run_error_sequence_inline(process, e)


def _run_finish_sequence_inline(process: "Skprocess") -> Any:
    """Run __onfinish__ and __result__, return result."""
    from .timeout import run_with_timeout
    from .errors import OnFinishError, ResultError, ProcessTimeoutError
    
    def _unwrap_method(m: Any) -> Callable:
        return getattr(m, '_method', m)
    
    # === ONFINISH ===
    method = _unwrap_method(process.__onfinish__)
    timeout = process.process_config.timeouts.onfinish
    
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
    result_timeout = process.process_config.timeouts.result
    
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


def _run_error_sequence_inline(process: "Skprocess", error: BaseException) -> Any:
    """Call __error__ and return its result."""
    from .timeout import run_with_timeout
    
    def _unwrap_method(m: Any) -> Callable:
        return getattr(m, '_method', m)
    
    # Set error on process for __error__ to access
    process.error = error
    
    error_method = _unwrap_method(process.__error__)
    error_timeout = process.process_config.timeouts.error
    
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
