"""
Pool class for parallel batch processing.

Provides map, imap, async_map, and unordered_imap operations with star() modifier.
Supports both regular functions and Skprocess-inheriting classes.
Uses cucumber for serialization, avoiding pickle limitations.
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

# shared executor used by background modifiers
# worker processes still run via multiprocessing
_pool_executor: ThreadPoolExecutor | None = None

def _get_pool_executor() -> ThreadPoolExecutor:
    """Get or create the shared thread pool executor for Pool operations."""
    global _pool_executor
    if _pool_executor is None:
        # thread pool only runs coordinator logic for background calls
        _pool_executor = ThreadPoolExecutor(max_workers=16, thread_name_prefix="pool_bg_")
    return _pool_executor



# pool method modifiers
# these wrap map and imap to add timeout background and async forms

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
        # hold pool reference and star flag for later calls
        self._pool = pool
        self._is_star = is_star
    
    def __call__(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
    ) -> list:
        """Apply function/Skprocess to each item, return list of results."""
        # dispatch to core map implementation
        return self._pool._map_impl(fn_or_process, iterable, is_star=self._is_star)
    
    def timeout(self, seconds: float) -> "_PoolMapTimeoutModifier":
        """Add timeout to the map operation."""
        # return modifier that injects timeout
        return _PoolMapTimeoutModifier(self._pool, self._is_star, seconds)
    
    def background(self) -> "_PoolMapBackgroundModifier":
        """Run map in background thread, return Future."""
        # return modifier that runs map in background thread
        return _PoolMapBackgroundModifier(self._pool, self._is_star)
    
    def asynced(self) -> "_PoolMapAsyncModifier":
        """Get async version of map."""
        # return async modifier for map
        return _PoolMapAsyncModifier(self._pool, self._is_star)


class _PoolMapTimeoutModifier:
    """Timeout modifier for Pool.map."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        # store pool and timeout config
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute map with timeout."""
        # run map with timeout value
        return self._pool._map_impl(fn_or_process, iterable, is_star=self._is_star, timeout=self._timeout)
    
    def background(self) -> "_PoolMapTimeoutBackgroundModifier":
        """Run map with timeout in background thread."""
        # return background modifier that preserves timeout
        return _PoolMapTimeoutBackgroundModifier(self._pool, self._is_star, self._timeout)
    
    def asynced(self) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        timeout = self._timeout
        
        async def async_map_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            # run map in a thread and apply asyncio timeout
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
        # store pool and timeout config
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute map with timeout in background, return Future."""
        # submit to thread pool for background execution
        executor = _get_pool_executor()
        return executor.submit(
            self._pool._map_impl, fn_or_process, iterable, self._is_star, self._timeout
        )


class _PoolMapBackgroundModifier:
    """Background modifier for Pool.map."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute map in background, return Future."""
        # submit to thread pool for background execution
        executor = _get_pool_executor()
        return executor.submit(self._pool._map_impl, fn_or_process, iterable, self._is_star, None)
    
    def timeout(self, seconds: float) -> "_PoolMapTimeoutBackgroundModifier":
        """Add timeout to background map."""
        # return timeout version of background modifier
        return _PoolMapTimeoutBackgroundModifier(self._pool, self._is_star, seconds)


class _PoolMapAsyncModifier:
    """Async modifier for Pool.map."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    async def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute map asynchronously."""
        # run map in a thread to avoid blocking the event loop
        return await asyncio.to_thread(self._pool._map_impl, fn_or_process, iterable, self._is_star, None)
    
    def timeout(self, seconds: float) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        
        async def async_map_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            # run map in a thread and apply asyncio timeout
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
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    def __call__(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
    ) -> Iterator:
        """Apply function/Skprocess to each item, return iterator of results."""
        # dispatch to core imap implementation
        return self._pool._imap_impl(fn_or_process, iterable, is_star=self._is_star)
    
    def timeout(self, seconds: float) -> "_PoolImapTimeoutModifier":
        """Add timeout to the imap operation."""
        # return modifier that injects timeout
        return _PoolImapTimeoutModifier(self._pool, self._is_star, seconds)
    
    def background(self) -> "_PoolImapBackgroundModifier":
        """Run imap collection in background, return Future of list."""
        # return background modifier that collects into list
        return _PoolImapBackgroundModifier(self._pool, self._is_star)
    
    def asynced(self) -> "_PoolImapAsyncModifier":
        """Get async version of imap (returns list, not iterator)."""
        # return async modifier that returns list
        return _PoolImapAsyncModifier(self._pool, self._is_star)


class _PoolImapTimeoutModifier:
    """Timeout modifier for Pool.imap."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        # store pool and timeout config
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Iterator:
        """Execute imap with timeout."""
        # run imap with timeout value
        return self._pool._imap_impl(fn_or_process, iterable, is_star=self._is_star, timeout=self._timeout)


class _PoolImapBackgroundModifier:
    """Background modifier for Pool.imap (collects to list)."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute imap in background, return Future of list."""
        # collect imap iterator into a list in a background thread
        def collect_imap():
            return list(self._pool._imap_impl(fn_or_process, iterable, self._is_star, None))
        
        executor = _get_pool_executor()
        return executor.submit(collect_imap)


class _PoolImapAsyncModifier:
    """Async modifier for Pool.imap (returns list)."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    async def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute imap asynchronously (returns list)."""
        # collect imap iterator into list off the event loop
        def collect_imap():
            return list(self._pool._imap_impl(fn_or_process, iterable, self._is_star, None))
        
        return await asyncio.to_thread(collect_imap)
    
    def timeout(self, seconds: float) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        
        async def async_imap_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            # collect imap results and apply asyncio timeout
            def collect_imap():
                return list(pool._imap_impl(fn_or_process, iterable, is_star, None))
            
            try:
                return await asyncio.wait_for(asyncio.to_thread(collect_imap), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.imap timed out after {seconds}s")
        
        return async_imap_with_timeout



# Unordered Imap Modifiers


class _PoolUnorderedImapModifier:
    """
    Bound method wrapper for Pool.unordered_imap with modifier support.
    """
    
    def __init__(self, pool: "Pool", is_star: bool = False):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    def __call__(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
    ) -> Iterator:
        """Apply function/Skprocess to each item, yield results as they complete."""
        # dispatch to core unordered imap implementation
        return self._pool._unordered_imap_impl(fn_or_process, iterable, is_star=self._is_star)
    
    def timeout(self, seconds: float) -> "_PoolUnorderedImapTimeoutModifier":
        """Add timeout to unordered_imap - raises if any result takes too long."""
        # return modifier that injects timeout
        return _PoolUnorderedImapTimeoutModifier(self._pool, self._is_star, seconds)
    
    def background(self) -> "_PoolUnorderedImapBackgroundModifier":
        """Run unordered_imap collection in background, return Future of list."""
        # return background modifier that collects into list
        return _PoolUnorderedImapBackgroundModifier(self._pool, self._is_star)
    
    def asynced(self) -> "_PoolUnorderedImapAsyncModifier":
        """Get async version of unordered_imap (returns list)."""
        # return async modifier that returns list
        return _PoolUnorderedImapAsyncModifier(self._pool, self._is_star)


class _PoolUnorderedImapTimeoutModifier:
    """Timeout modifier for Pool.unordered_imap."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        # store pool and timeout config
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Iterator:
        """Execute unordered_imap with timeout per result."""
        # run unordered imap with timeout value
        return self._pool._unordered_imap_impl(
            fn_or_process, iterable, is_star=self._is_star, timeout=self._timeout
        )
    
    def background(self) -> "_PoolUnorderedImapTimeoutBackgroundModifier":
        """Run with timeout in background."""
        # return background modifier that preserves timeout
        return _PoolUnorderedImapTimeoutBackgroundModifier(self._pool, self._is_star, self._timeout)
    
    def asynced(self) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        timeout = self._timeout
        
        async def async_unordered_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            # collect unordered results with a timeout
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
        # store pool and timeout config
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute unordered_imap with timeout in background."""
        # collect unordered results in background thread
        def collect():
            return list(self._pool._unordered_imap_impl(
                fn_or_process, iterable, self._is_star, self._timeout
            ))
        
        executor = _get_pool_executor()
        return executor.submit(collect)


class _PoolUnorderedImapBackgroundModifier:
    """Background modifier for Pool.unordered_imap (collects to list)."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute unordered_imap in background, return Future of list."""
        # collect unordered results in background thread
        def collect():
            return list(self._pool._unordered_imap_impl(fn_or_process, iterable, self._is_star))
        
        executor = _get_pool_executor()
        return executor.submit(collect)
    
    def timeout(self, seconds: float) -> "_PoolUnorderedImapTimeoutBackgroundModifier":
        """Add timeout to background unordered_imap."""
        # return timeout background modifier
        return _PoolUnorderedImapTimeoutBackgroundModifier(self._pool, self._is_star, seconds)


class _PoolUnorderedImapAsyncModifier:
    """Async modifier for Pool.unordered_imap (returns list)."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    async def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute unordered_imap asynchronously (returns list)."""
        # collect unordered results into list off the event loop
        def collect():
            return list(self._pool._unordered_imap_impl(fn_or_process, iterable, self._is_star))
        
        return await asyncio.to_thread(collect)
    
    def timeout(self, seconds: float) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        
        async def async_unordered_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            # collect unordered results with a timeout
            def collect():
                return list(pool._unordered_imap_impl(fn_or_process, iterable, is_star))
            
            try:
                return await asyncio.wait_for(asyncio.to_thread(collect), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.unordered_imap timed out after {seconds}s")
        
        return async_unordered_with_timeout



# Unordered Map Modifiers (returns list in completion order)


class _PoolUnorderedMapModifier:
    """
    Bound method wrapper for Pool.unordered_map with modifier support.
    
    Usage:
        pool.unordered_map(fn, items)                    # sync, blocks, returns list
        pool.unordered_map.timeout(30)(fn, items)        # sync with timeout
        pool.unordered_map.background()(fn, items)       # returns Future
        await pool.unordered_map.asynced()(fn, items)    # async
    """
    
    def __init__(self, pool: "Pool", is_star: bool = False):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    def __call__(
        self,
        fn_or_process: Union[Callable, type],
        iterable: Iterable,
    ) -> list:
        """Apply function/Skprocess to each item, return list in completion order."""
        # collect unordered results into list
        return list(self._pool._unordered_imap_impl(fn_or_process, iterable, is_star=self._is_star))
    
    def timeout(self, seconds: float) -> "_PoolUnorderedMapTimeoutModifier":
        """Add timeout to unordered_map - raises if exceeded."""
        # return modifier that injects timeout
        return _PoolUnorderedMapTimeoutModifier(self._pool, self._is_star, seconds)
    
    def background(self) -> "_PoolUnorderedMapBackgroundModifier":
        """Run unordered_map in background thread, return Future."""
        # return background modifier
        return _PoolUnorderedMapBackgroundModifier(self._pool, self._is_star)
    
    def asynced(self) -> "_PoolUnorderedMapAsyncModifier":
        """Get async version of unordered_map."""
        # return async modifier
        return _PoolUnorderedMapAsyncModifier(self._pool, self._is_star)


class _PoolUnorderedMapTimeoutModifier:
    """Timeout modifier for Pool.unordered_map."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        # store pool and timeout config
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute unordered_map with timeout."""
        # collect unordered results with timeout
        return list(self._pool._unordered_imap_impl(
            fn_or_process, iterable, is_star=self._is_star, timeout=self._timeout
        ))
    
    def background(self) -> "_PoolUnorderedMapTimeoutBackgroundModifier":
        """Run unordered_map with timeout in background thread."""
        # return background modifier that preserves timeout
        return _PoolUnorderedMapTimeoutBackgroundModifier(self._pool, self._is_star, self._timeout)
    
    def asynced(self) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        timeout = self._timeout
        
        async def async_unordered_map_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            # collect unordered results and apply asyncio timeout
            def collect():
                return list(pool._unordered_imap_impl(fn_or_process, iterable, is_star, timeout))
            
            try:
                return await asyncio.wait_for(asyncio.to_thread(collect), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.unordered_map timed out after {timeout}s")
        
        return async_unordered_map_with_timeout


class _PoolUnorderedMapTimeoutBackgroundModifier:
    """Background modifier for Pool.unordered_map with timeout."""
    
    def __init__(self, pool: "Pool", is_star: bool, timeout_seconds: float):
        # store pool and timeout config
        self._pool = pool
        self._is_star = is_star
        self._timeout = timeout_seconds
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute unordered_map with timeout in background, return Future."""
        # submit to thread pool for background execution
        def collect():
            return list(self._pool._unordered_imap_impl(
                fn_or_process, iterable, self._is_star, self._timeout
            ))
        
        executor = _get_pool_executor()
        return executor.submit(collect)


class _PoolUnorderedMapBackgroundModifier:
    """Background modifier for Pool.unordered_map."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> Future:
        """Execute unordered_map in background, return Future."""
        # submit to thread pool for background execution
        def collect():
            return list(self._pool._unordered_imap_impl(fn_or_process, iterable, self._is_star, None))
        
        executor = _get_pool_executor()
        return executor.submit(collect)
    
    def timeout(self, seconds: float) -> "_PoolUnorderedMapTimeoutBackgroundModifier":
        """Add timeout to background unordered_map."""
        # return timeout version of background modifier
        return _PoolUnorderedMapTimeoutBackgroundModifier(self._pool, self._is_star, seconds)


class _PoolUnorderedMapAsyncModifier:
    """Async modifier for Pool.unordered_map."""
    
    def __init__(self, pool: "Pool", is_star: bool):
        # store pool reference and star flag
        self._pool = pool
        self._is_star = is_star
    
    async def __call__(self, fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
        """Execute unordered_map asynchronously."""
        # collect unordered results in a thread to avoid blocking event loop
        def collect():
            return list(self._pool._unordered_imap_impl(fn_or_process, iterable, self._is_star, None))
        
        return await asyncio.to_thread(collect)
    
    def timeout(self, seconds: float) -> Callable:
        """Get async version with timeout."""
        pool = self._pool
        is_star = self._is_star
        
        async def async_unordered_map_with_timeout(fn_or_process: Union[Callable, type], iterable: Iterable) -> list:
            # collect unordered results and apply asyncio timeout
            def collect():
                return list(pool._unordered_imap_impl(fn_or_process, iterable, is_star, None))
            
            try:
                return await asyncio.wait_for(asyncio.to_thread(collect), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Pool.unordered_map timed out after {seconds}s")
        
        return async_unordered_map_with_timeout



# Star Modifier

class StarModifier:
    """
    Modifier returned by pool.star().
    
    Provides the same methods as Pool, but unpacks tuples as arguments.
    """
    
    def __init__(self, pool: "Pool"):
        # store pool reference for forwarding calls
        self._pool = pool
    
    @property
    def map(self) -> _PoolMapModifier:
        """Get map method with tuple unpacking and modifier support."""
        # return map modifier configured for tuple unpacking
        return _PoolMapModifier(self._pool, is_star=True)
    
    @property
    def imap(self) -> _PoolImapModifier:
        """Get imap method with tuple unpacking and modifier support."""
        # return imap modifier configured for tuple unpacking
        return _PoolImapModifier(self._pool, is_star=True)
    
    @property
    def unordered_imap(self) -> _PoolUnorderedImapModifier:
        """Get unordered_imap method with tuple unpacking and modifier support."""
        # return unordered imap modifier configured for tuple unpacking
        return _PoolUnorderedImapModifier(self._pool, is_star=True)
    
    @property
    def unordered_map(self) -> _PoolUnorderedMapModifier:
        """Get unordered_map method with tuple unpacking and modifier support."""
        # return unordered map modifier configured for tuple unpacking
        return _PoolUnorderedMapModifier(self._pool, is_star=True)

class Pool:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise.processing import Pool
        
        pool = Pool(workers=4)
        
        # map: returns list, preserves order
        results = pool.map(sum, [(1, 2), (3, 4)])
        # each item is passed as a single argument (no tuple unpacking):
        #   worker1 gets ((1, 2), nothing else)
        #   worker2 gets ((3, 4), nothing else)

        # star() modifier: tuple-unpacking into the function
        results = pool.star().map(sum, [(1, 2), (3, 4)])
        # each tuple is unpacked into positional args:
        #   worker1 gets (1, 2)
        #   worker2 gets (3, 4)
        
        # imap: iterator, preserves order
        for result in pool.imap(sum, [(1, 2), (3, 4)]):
            print(result)
        
        # unordered_imap: iterator, yields as completed (fastest)
        for result in pool.unordered_imap(sum, [(1, 2), (3, 4)]):
            print(result)
        
        # unordered_map: list, in completion order (fastest list)
        results = pool.unordered_map(sum, [(1, 2), (3, 4)])

        # star() works with map, imap, unordered_imap, and unordered_map
        ```
    ────────────────────────────────────────────────────────\n

    Pool for parallel batch processing.

    Supports both functions and Skprocess-inheriting classes.
    
    Uses cucumber for serialization, supporting complex objects that
    pickle and others cannot handle.
    
    ────────────────────────────────────────────────────────
        ```python
        # modifier usage (map / imap / unordered_imap)

        # with timeout - raises TimeoutError if exceeded
        results = pool.map.timeout(30.0)(fn, items)

        # background - returns Future immediately
        future = pool.map.background()(fn, items)
        results = future.result()

        # native async support
        results = await pool.map.asynced()(fn, items)
        

        for result in pool.imap.timeout(10.0)(fn, items):
            print(result)
        
        # returns a Future
        future = pool.unordered_imap.background()(fn, items)
        results = future.result() # is a list
        
        # star() modifier composes with other modifiers
        results = pool.star().map.timeout(5.0)(fn, args_iter)
        results = await pool.star().unordered_imap.asynced()(fn, args_iter)
        ```
    ────────────────────────────────────────────────────────\n
    """
    
    def __init__(self, workers: int | None = None):
        """
        Create a new Pool.
        
        Args:
            workers: Max concurrent workers. None = number of CPUs.
        """
        self._workers = workers or multiprocessing.cpu_count()
        self._active_processes: list[multiprocessing.Process] = []
        self._mp_pool: multiprocessing.pool.Pool | None = multiprocessing.Pool(
            processes=self._workers
        )

    def __serialize__(self) -> dict:
        """
        Serialize Pool without multiprocessing internals.
        
        Avoids serializing locks/queues inside multiprocessing.Pool.
        """
        return {
            "workers": self._workers,
            "closed": self._mp_pool is None,
        }

    @classmethod
    def __deserialize__(cls, state: dict) -> "Pool":
        """
        Reconstruct Pool from serialized state.
        """
        obj = cls.__new__(cls)
        workers = state.get("workers") or multiprocessing.cpu_count()
        obj._workers = workers
        obj._active_processes = []
        if state.get("closed"):
            obj._mp_pool = None
        else:
            obj._mp_pool = multiprocessing.Pool(processes=workers)
        return obj
    
    def close(self) -> None:
        """Wait for all active processes to finish."""
        for p in self._active_processes:
            if p.is_alive():
                p.join()
        self._active_processes.clear()
        if self._mp_pool is not None:
            self._mp_pool.close()
            self._mp_pool.join()
            self._mp_pool = None
    
    def terminate(self) -> None:
        """Forcefully terminate all active processes."""
        for p in self._active_processes:
            if p.is_alive():
                p.terminate()
        self._active_processes.clear()
        if self._mp_pool is not None:
            self._mp_pool.terminate()
            self._mp_pool.join()
            self._mp_pool = None
    
    def __enter__(self) -> "Pool":
        return self
    
    def __exit__(self, *args) -> None:
        self.close()
    

    # star modifier method
    
    def star(self) -> StarModifier:
        """
        Return modifier for tuple unpacking.
        
        star().map() unpacks tuples as function arguments.
        star().imap() unpacks tuples as function arguments.
        star().unordered_imap() unpacks tuples as function arguments.
        star().unordered_map() unpacks tuples as function arguments.
        """
        return StarModifier(self)
    


    # main methods with modifier support
    
    @property
    def map(self) -> _PoolMapModifier:
        """
        ────────────────────────────────────────────────────────
            ```python
            # sync - blocks until all complete
            results = pool.map(fn, items)
            
            # with timeout - raises TimeoutError if exceeded
            results = pool.map.timeout(30.0)(fn, items)
            
            # background - returns Future immediately
            future = pool.map.background()(fn, items)
            results = future.result()
            
            # async - returns coroutine for await
            coro = pool.map.asynced()
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
            # sync - iterator, blocks on each next()
            for result in pool.imap(fn, items):
                do_something_with(result)
            
            # with timeout - raises TimeoutError if exceeded
            for result in pool.imap.timeout(30.0)(fn, items):
                process(result)
            
            # background (collects to list)
            future = pool.imap.background()(fn, items)
            results = future.result() # is a list
            
            # async (collects to list)
            coro = pool.imap.asynced()
            results = await pool.imap.asynced()(fn, items) # is a list
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
            # sync - iterator, yields as results complete
            for result in pool.unordered_imap(fn, items):
                process(result)
            
            # with timeout
            for result in pool.unordered_imap.timeout(30.0)(fn, items):
                process(result)
            
            # background (collects to list)
            future = pool.unordered_imap.background()(fn, items)
            results = future.result() # is a list
            
            # async (collects to list)
            results = await pool.unordered_imap.asynced()(fn, items) # is a list
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
    
    @property
    def unordered_map(self) -> _PoolUnorderedMapModifier:
        """
        ────────────────────────────────────────────────────────
            ```python
            # sync - blocks until all complete, returns list in completion order
            results = pool.unordered_map(fn, items)
            
            # with timeout - raises TimeoutError if exceeded
            results = pool.unordered_map.timeout(30.0)(fn, items)
            
            # background - returns Future immediately
            future = pool.unordered_map.background()(fn, items)
            results = future.result()
            
            # async - returns coroutine for await
            results = await pool.unordered_map.asynced()(fn, items)
            ```
        ────────────────────────────────────────────────────────
        
        Apply function/Skprocess to each item, return list in completion order.
        
        Like map(), returns a list. Like unordered_imap(), results are in
        completion order (fastest items first), not input order.
        
        Fastest when you need all results as a list but don't care about order.
        
        Args:
            fn_or_process: Function or Skprocess class to apply.
            iterable: Items to process.
        
        Returns:
            List of results in completion order.
        
        Modifiers:
            .timeout(seconds): Raise TimeoutError if exceeded
            .background(): Return Future immediately
            .asynced(): Return coroutine for await
        """
        return _PoolUnorderedMapModifier(self, is_star=False)
    


    # implementation

    def _spawn_worker(
        self,
        serialized_fn: bytes,
        serialized_item: bytes,
        is_star: bool,
    ) -> tuple[multiprocessing.Queue, multiprocessing.Process]:
        """Spawn a single worker for one item."""
        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        # worker process executes the function for one item and writes to queue
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
        from suitkaise import cucumber
        
        items = list(iterable)
        if not items:
            return []
        
        # serialize the function or Skprocess class once for reuse
        serialized_fn = cucumber.serialize(fn_or_process)

        # results preserves input order for map
        results = [None] * len(items)

        if timeout is None and self._mp_pool is not None:
            args = [
                (serialized_fn, cucumber.serialize(item), is_star)
                for item in items
            ]
            messages = self._mp_pool.map(_pool_worker_bytes_args, args)
            for idx, message in enumerate(messages):
                if message["type"] == "error":
                    error = cucumber.deserialize(message["data"])
                    raise error
                results[idx] = cucumber.deserialize(message["data"])
            return results
        
        max_workers = self._workers
        if max_workers is None:
            max_workers = len(items)
        
        active: list[tuple[int, multiprocessing.Queue, multiprocessing.Process]] = []
        next_index = 0
        
        def start_one(idx: int) -> None:
            # serialize each item and start one worker
            serialized_item = cucumber.serialize(items[idx])
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
                    w.join(timeout=1.0)
                    _drain_queue(q)
                    raise TimeoutError(f"Pool.map worker {idx} timed out after {timeout}s")
                
                try:
                    # read one message per worker and decode result or error
                    message = q.get()
                    if message["type"] == "error":
                        error = cucumber.deserialize(message["data"])
                        raise error
                    results[idx] = cucumber.deserialize(message["data"])
                except queue_module.Empty:
                    results[idx] = None
                finally:
                    # drop worker from active list after collecting result
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
        from suitkaise import cucumber
        
        items = list(iterable)
        if not items:
            return iter([])
        
        # serialize the function or Skprocess class once for reuse
        serialized_fn = cucumber.serialize(fn_or_process)
        if timeout is None and self._mp_pool is not None:
            args = [
                (serialized_fn, cucumber.serialize(item), is_star)
                for item in items
            ]
            def iterator() -> Iterator:
                for message in self._mp_pool.imap(_pool_worker_bytes_args, args):
                    if message["type"] == "error":
                        error = cucumber.deserialize(message["data"])
                        raise error
                    yield cucumber.deserialize(message["data"])
            return iterator()

        max_workers = self._workers
        if max_workers is None:
            max_workers = len(items)
        
        def generator() -> Iterator:
            active: dict[int, tuple[multiprocessing.Queue, multiprocessing.Process]] = {}
            next_index = 0
            next_yield = 0
            
            def start_one(idx: int) -> None:
                # serialize each item and start one worker
                serialized_item = cucumber.serialize(items[idx])
                q, w = self._spawn_worker(serialized_fn, serialized_item, is_star)
                active[idx] = (q, w)
            
            while next_yield < len(items):
                while next_index < len(items) and len(active) < max_workers:
                    start_one(next_index)
                    next_index += 1
                
                if next_yield not in active:
                    # if not started yet keep starting workers
                    continue
                
                q, w = active[next_yield]
                w.join(timeout=timeout)
                
                if w.is_alive():
                    w.terminate()
                    w.join(timeout=1.0)
                    _drain_queue(q)
                    raise TimeoutError(f"Pool.imap worker {next_yield} timed out after {timeout}s")
                
                try:
                    # decode the next result in order
                    message = q.get()
                    if message["type"] == "error":
                        error = cucumber.deserialize(message["data"])
                        raise error
                    yield cucumber.deserialize(message["data"])
                except queue_module.Empty:
                    yield None
                finally:
                    # remove worker and advance yield cursor
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
        from suitkaise import cucumber
        import time as time_module

        def _decode_payload(payload: Any, kind: str) -> Any:
            try:
                return cucumber.deserialize(payload)
            except Exception as exc:
                payload_type = type(payload).__name__
                payload_len = len(payload) if isinstance(payload, (bytes, bytearray)) else None
                raise cucumber.DeserializationError(
                    f"Pool failed to deserialize {kind} payload ({payload_type}, len={payload_len}): {type(exc).__name__}: {exc}"
                ) from exc
        
        items = list(iterable)
        if not items:
            return iter([])
        
        # serialize the function or Skprocess class once for reuse
        serialized_fn = cucumber.serialize(fn_or_process)
        if timeout is None and self._mp_pool is not None:
            args = [
                (serialized_fn, cucumber.serialize(item), is_star)
                for item in items
            ]
            def iterator() -> Iterator:
                for message in self._mp_pool.imap_unordered(_pool_worker_bytes_args, args):
                    if message["type"] == "error":
                        error = _decode_payload(message["data"], "error")
                        raise error
                    yield _decode_payload(message["data"], "result")
            return iterator()

        max_workers = self._workers
        if max_workers is None:
            max_workers = len(items)
        
        def generator() -> Iterator:
            active: list[tuple[int, multiprocessing.Queue, multiprocessing.Process]] = []
            next_index = 0
            start_time = time_module.perf_counter() if timeout else None
            
            def start_one(idx: int) -> None:
                # serialize each item and start one worker
                serialized_item = cucumber.serialize(items[idx])
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
                        # decode next completed result as soon as it is ready
                        message = q.get()
                        if message["type"] == "error":
                            error = _decode_payload(message["data"], "error")
                            raise error
                        yield _decode_payload(message["data"], "result")
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
                            # terminate remaining workers on timeout
                            for _, q_drain, w in active:
                                if w.is_alive():
                                    w.terminate()
                                    w.join(timeout=1.0)
                                _drain_queue(q_drain)
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
    from suitkaise import cucumber
    
    for i, (q, w) in enumerate(zip(result_queues, workers)):
        w.join(timeout=timeout)
        
        # check if worker timed out
        if w.is_alive():
            w.terminate()
            w.join(timeout=1.0)
            _drain_queue(q)
            raise TimeoutError(f"Pool.imap worker {i} timed out after {timeout}s")
        
        try:
            # decode the result or error message
            message = q.get()
            if message["type"] == "error":
                error = cucumber.deserialize(message["data"])
                raise error
            else:
                yield cucumber.deserialize(message["data"])
        except queue_module.Empty:
            yield None
        finally:
            # cleanup active process tracking
            if w in active_processes:
                active_processes.remove(w)


def _unordered_results(
    result_queues: list,
    workers: list,
    active_processes: list,
    timeout: float | None = None,
) -> Iterator:
    """Yield results as they complete."""
    from suitkaise import cucumber
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
                        w.join(timeout=1.0)
                    _drain_queue(q)
                    if w in active_processes:
                        active_processes.remove(w)
                raise TimeoutError(f"Pool.unordered_imap timed out after {timeout}s")
        
        for i, (q, w) in enumerate(remaining):
            if not w.is_alive():
                # Worker finished, get result
                try:
                    message = q.get()
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
            time_module.sleep(0.01)


def _drain_queue(q) -> None:
    """Drain a multiprocessing.Queue to prevent resource leaks after worker termination."""
    import queue as _q
    try:
        while True:
            q.get_nowait()
    except (_q.Empty, EOFError, OSError):
        pass
    try:
        q.close()
        q.join_thread()
    except Exception:
        pass


def _pool_worker(
    serialized_fn: bytes,
    serialized_item: bytes,
    is_star: bool,
    result_queue: multiprocessing.Queue
) -> None:
    """
    Worker function that runs in subprocess.
    
    Uses cucumber to deserialize function and arguments.
    Handles both regular functions and Skprocess classes.
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
        serialized_result = cucumber.serialize(result)
        result_queue.put({
            "type": "result",
            "data": serialized_result
        })
        
    except Exception as e:
        # Always include traceback details for clarity across processes.
        import traceback
        error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        result_queue.put({
            "type": "error",
            "data": cucumber.serialize(RuntimeError(error_msg))
        })


def _pool_worker_bytes(
    serialized_fn: bytes,
    serialized_item: bytes,
    is_star: bool,
) -> dict:
    """
    Worker for multiprocessing.Pool that returns serialized result/error.
    """
    from suitkaise import cucumber

    try:
        fn_or_process = cucumber.deserialize(serialized_fn)
        item = cucumber.deserialize(serialized_item)

        if is_star:
            if isinstance(item, tuple):
                args = item
            else:
                args = (item,)
        else:
            args = (item,)

        from .process_class import Skprocess

        if isinstance(fn_or_process, type) and issubclass(fn_or_process, Skprocess):
            process_instance = fn_or_process(*args)
            result = _run_process_inline(process_instance)
        else:
            result = fn_or_process(*args) if is_star else fn_or_process(item)

        return {"type": "result", "data": cucumber.serialize(result)}
    except Exception as e:
        import traceback
        error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        return {"type": "error", "data": cucumber.serialize(RuntimeError(error_msg))}


def _pool_worker_bytes_args(args: tuple[bytes, bytes, bool]) -> dict:
    """Unpack args for Pool.imap/imap_unordered."""
    return _pool_worker_bytes(*args)


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
    from suitkaise import timing
    
    # ensure timers exist
    if process.timers is None:
        process.timers = ProcessTimers()
    
    # initialize run state
    process._current_run = 0
    process._start_time = timing.time()
    
    # create stop event so self.stop() works in Pool
    # use threading.Event since we're already in a subprocess
    stop_event = threading.Event()
    process._stop_event = stop_event  # type: ignore[assignment]
    
    # track lives for retry system
    lives_remaining = process.process_config.lives
    
    def _unwrap_method(m: Any) -> Callable:
        """Unwrap TimedMethod wrapper if present."""
        return getattr(m, '_method', m)
    
    def _should_continue() -> bool:
        """Check if run loop should continue."""
        # check stop signal for self.stop calls
        if stop_event.is_set():
            return False
        
        # check run count limit
        if process.process_config.runs is not None:
            if process._current_run >= process.process_config.runs:
                return False
        
        # check time limit for join_in
        if process.process_config.join_in is not None and process._start_time is not None:
            elapsed = timing.elapsed(process._start_time)
            if elapsed >= process.process_config.join_in:
                return False
        
        return True
    
    def _run_section_timed(method_name: str, timer_name: str, error_class: type) -> None:
        """Run a lifecycle section with timing, timeout, and error handling."""
        method_attr = getattr(process, method_name)
        method = _unwrap_method(method_attr)
        
        timeout = getattr(process.process_config.timeouts, timer_name, None)
        
        # get timer since we ensured timers exist above
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
            # main execution loop
            while _should_continue():
                # PRE RUN
                _run_section_timed('__prerun__', 'prerun', PreRunError)
                
                if stop_event.is_set():
                    break
                
                # RUN
                _run_section_timed('__run__', 'run', RunError)
                
                if stop_event.is_set():
                    break
                
                # POST RUN
                _run_section_timed('__postrun__', 'postrun', PostRunError)
                
                # increment run counter
                process._current_run += 1
                
                # update full_run timer
                if process.timers is not None:
                    process.timers._update_full_run()
            
            # normal exit - run finish sequence
            return _run_finish_sequence_inline(process)
            
        except (PreRunError, RunError, PostRunError, ProcessTimeoutError) as e:
            # error in run - check if we have lives to retry
            lives_remaining -= 1
            
            if lives_remaining > 0:
                # retry: keep user state and run counter, retry current iteration
                process.process_config.lives = lives_remaining
                continue
            else:
                # no lives left - run error sequence
                return _run_error_sequence_inline(process, e)


def _run_finish_sequence_inline(process: "Skprocess") -> Any:
    """Run __onfinish__ and __result__, return result."""
    from .timeout import run_with_timeout
    from .errors import OnFinishError, ResultError, ProcessTimeoutError
    
    def _unwrap_method(m: Any) -> Callable:
        return getattr(m, '_method', m)
    
    # ON FINISH
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
    
    # RESULT
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
