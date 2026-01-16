"""
Tests for Process and Pool method modifiers (.timeout, .background, .asynced).
"""

import asyncio
import time
import pytest
from concurrent.futures import Future

from suitkaise.processing import Process, Pool, ResultTimeoutError
from suitkaise.sk import SkModifierError


# =============================================================================
# Test Process Classes
# =============================================================================

class QuickProcess(Process):
    """A process that completes quickly."""
    
    def __init__(self, value: int):
        self.value = value
    
    def __run__(self):
        self.result_value = self.value * 2
    
    def __result__(self):
        return self.result_value


class SlowProcess(Process):
    """A process that takes a while to complete."""
    
    def __init__(self, sleep_time: float = 2.0):
        self.sleep_time = sleep_time
    
    def __run__(self):
        time.sleep(self.sleep_time)
        self.result_value = "completed"
    
    def __result__(self):
        return self.result_value


class TalkativeProcess(Process):
    """A process that communicates via tell/listen."""
    
    def __init__(self):
        pass
    
    def __run__(self):
        # Wait for parent to send data
        data = self.listen(timeout=5.0)
        # Send back processed data
        self.tell(f"received: {data}")
    
    def __result__(self):
        return "done"


# =============================================================================
# Process.result() Modifier Tests
# =============================================================================

class TestProcessResultModifiers:
    """Tests for Process.result() modifiers."""
    
    def test_result_direct_call(self):
        """result() works without modifiers (baseline)."""
        p = QuickProcess(5)
        p.start()
        result = p.result()
        assert result == 10
    
    def test_result_timeout_success(self):
        """result.timeout() succeeds when process completes in time."""
        p = QuickProcess(5)
        p.start()
        result = p.result.timeout(5.0)()
        assert result == 10
    
    def test_result_timeout_failure(self):
        """result.timeout() raises ResultTimeoutError when exceeded."""
        p = SlowProcess(sleep_time=10.0)  # very slow
        p.start()
        
        with pytest.raises(ResultTimeoutError):
            p.result.timeout(0.5)()
        
        # Clean up
        p.stop()
    
    def test_result_background(self):
        """result.background() returns Future immediately."""
        p = QuickProcess(5)
        p.start()
        
        future = p.result.background()()
        
        # Should return immediately with a Future
        assert isinstance(future, Future)
        
        # Get the result
        result = future.result(timeout=5.0)
        assert result == 10
    
    def test_result_background_allows_concurrent_work(self):
        """result.background() allows doing other work while waiting."""
        p = SlowProcess(sleep_time=0.5)
        p.start()
        
        start = time.perf_counter()
        future = p.result.background()()
        
        # This returns immediately
        immediate_time = time.perf_counter() - start
        assert immediate_time < 0.1, "background() should return immediately"
        
        # Do other work here...
        time.sleep(0.1)
        
        # Now wait for result
        result = future.result(timeout=5.0)
        assert result == "completed"
    
    @pytest.mark.asyncio
    async def test_result_asynced(self):
        """result.asynced() returns coroutine that can be awaited."""
        p = QuickProcess(5)
        p.start()
        
        result = await p.result.asynced()()
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_result_asynced_with_concurrent_tasks(self):
        """result.asynced() works with other async tasks."""
        p1 = QuickProcess(5)
        p2 = QuickProcess(10)
        p1.start()
        p2.start()
        
        # Run both awaits concurrently
        results = await asyncio.gather(
            p1.result.asynced()(),
            p2.result.asynced()(),
        )
        
        assert results == [10, 20]


# =============================================================================
# Process.wait() Modifier Tests
# =============================================================================

class TestProcessWaitModifiers:
    """Tests for Process.wait() modifiers."""
    
    def test_wait_direct_call(self):
        """wait() works without modifiers (baseline)."""
        p = QuickProcess(5)
        p.start()
        finished = p.wait()
        assert finished is True
    
    def test_wait_timeout_unsupported(self):
        """wait.timeout() raises SkModifierError (timeout param exists)."""
        p = QuickProcess(5)
        p.start()
        with pytest.raises(SkModifierError):
            p.wait.timeout(5.0)()
    
    def test_wait_background_unsupported(self):
        """wait.background() raises SkModifierError."""
        p = QuickProcess(5)
        p.start()
        with pytest.raises(SkModifierError):
            p.wait.background()()
    
    @pytest.mark.asyncio
    async def test_wait_asynced(self):
        """wait.asynced() returns coroutine."""
        p = QuickProcess(5)
        p.start()
        
        finished = await p.wait.asynced()()
        assert finished is True


# =============================================================================
# Process.listen() Modifier Tests
# =============================================================================

class TestProcessListenModifiers:
    """Tests for Process.listen() modifiers."""
    
    def test_listen_timeout(self):
        """listen.timeout() works with timeout modifier."""
        p = TalkativeProcess()
        p.start()
        
        # Send data to process
        p.tell("hello")
        
        # Listen for response with timeout modifier
        response = p.listen.timeout(5.0)()
        assert response == "received: hello"
    
    def test_listen_background(self):
        """listen.background() returns Future immediately."""
        p = TalkativeProcess()
        p.start()
        
        # Start listening in background first
        future = p.listen.background()()
        assert isinstance(future, Future)
        
        # Send data
        p.tell("world")
        
        # Get response from future
        response = future.result(timeout=5.0)
        assert response == "received: world"
    
    @pytest.mark.asyncio
    async def test_listen_asynced(self):
        """listen.asynced() returns coroutine."""
        p = TalkativeProcess()
        p.start()
        
        # Start async listen task
        async def listen_and_send():
            # Start listening (will await)
            listen_task = asyncio.create_task(p.listen.asynced()())
            
            # Give process time to start
            await asyncio.sleep(0.1)
            
            # Send data
            p.tell("async hello")
            
            return await listen_task
        
        response = await listen_and_send()
        assert response == "received: async hello"


# =============================================================================
# Pool.map() Modifier Tests
# =============================================================================

class TestPoolMapModifiers:
    """Tests for Pool.map() modifiers."""
    
    def test_map_direct_call(self):
        """map() works without modifiers (baseline)."""
        pool = Pool(workers=2)
        
        def double(x):
            return x * 2
        
        results = pool.map(double, [1, 2, 3])
        assert results == [2, 4, 6]
    
    def test_map_timeout_success(self):
        """map.timeout() succeeds when all complete in time."""
        pool = Pool(workers=2)
        
        def quick(x):
            time.sleep(0.1)
            return x * 2
        
        results = pool.map.timeout(5.0)(quick, [1, 2, 3])
        assert results == [2, 4, 6]
    
    def test_map_timeout_failure(self):
        """map.timeout() raises TimeoutError when exceeded."""
        pool = Pool(workers=2)
        
        def slow(x):
            time.sleep(10.0)  # very slow
            return x
        
        with pytest.raises(TimeoutError):
            pool.map.timeout(0.5)(slow, [1, 2])
        
        # Clean up
        pool.terminate()
    
    def test_map_background(self):
        """map.background() returns Future immediately."""
        pool = Pool(workers=2)
        
        def quick(x):
            time.sleep(0.1)
            return x * 2
        
        future = pool.map.background()(quick, [1, 2, 3])
        
        # Should return immediately with a Future
        assert isinstance(future, Future)
        
        # Get the result
        results = future.result(timeout=5.0)
        assert results == [2, 4, 6]
    
    @pytest.mark.asyncio
    async def test_map_asynced(self):
        """map.asynced() returns coroutine that can be awaited."""
        pool = Pool(workers=2)
        
        def quick(x):
            return x * 2
        
        results = await pool.map.asynced()(quick, [1, 2, 3])
        assert results == [2, 4, 6]


class TestPoolModifierChaining:
    """Tests for Pool modifier chaining on map/imap/unordered_imap."""

    def test_map_timeout_background_chain(self):
        """map.timeout().background() works."""
        pool = Pool(workers=2)

        def quick(x):
            time.sleep(0.05)
            return x * 2

        future = pool.map.timeout(2.0).background()(quick, [1, 2, 3])
        assert isinstance(future, Future)
        assert future.result(timeout=5.0) == [2, 4, 6]

    def test_map_background_timeout_chain(self):
        """map.background().timeout() works."""
        pool = Pool(workers=2)

        def quick(x):
            time.sleep(0.05)
            return x * 2

        future = pool.map.background().timeout(2.0)(quick, [1, 2, 3])
        assert isinstance(future, Future)
        assert future.result(timeout=5.0) == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_map_asynced_timeout_chain(self):
        """map.asynced().timeout() works."""
        pool = Pool(workers=2)

        def quick(x):
            time.sleep(0.05)
            return x * 2

        results = await pool.map.asynced().timeout(2.0)(quick, [1, 2, 3])
        assert results == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_imap_asynced_timeout_chain(self):
        """imap.asynced().timeout() works."""
        pool = Pool(workers=2)

        def quick(x):
            time.sleep(0.05)
            return x * 2

        results = await pool.imap.asynced().timeout(2.0)(quick, [1, 2, 3])
        assert results == [2, 4, 6]

    def test_unordered_timeout_background_chain(self):
        """unordered_imap.timeout().background() works."""
        pool = Pool(workers=2)

        def quick(x):
            time.sleep(0.05)
            return x * 2

        future = pool.unordered_imap.timeout(2.0).background()(quick, [1, 2, 3])
        assert isinstance(future, Future)
        assert sorted(future.result(timeout=5.0)) == [2, 4, 6]

    def test_unordered_background_timeout_chain(self):
        """unordered_imap.background().timeout() works."""
        pool = Pool(workers=2)

        def quick(x):
            time.sleep(0.05)
            return x * 2

        future = pool.unordered_imap.background().timeout(2.0)(quick, [1, 2, 3])
        assert isinstance(future, Future)
        assert sorted(future.result(timeout=5.0)) == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_unordered_asynced_timeout_chain(self):
        """unordered_imap.asynced().timeout() works."""
        pool = Pool(workers=2)

        def quick(x):
            time.sleep(0.05)
            return x * 2

        results = await pool.unordered_imap.asynced().timeout(2.0)(quick, [1, 2, 3])
        assert sorted(results) == [2, 4, 6]
    
    def test_imap_timeout_success(self):
        """imap.timeout() succeeds when all complete in time."""
        pool = Pool(workers=2)
        
        def quick(x):
            time.sleep(0.1)
            return x * 2
        
        results = list(pool.imap.timeout(5.0)(quick, [1, 2, 3]))
        assert results == [2, 4, 6]
    
    def test_imap_timeout_failure(self):
        """imap.timeout() raises TimeoutError when exceeded."""
        pool = Pool(workers=2)
        
        def slow(x):
            time.sleep(10.0)
            return x
        
        with pytest.raises(TimeoutError):
            # Iterate to trigger the timeout
            list(pool.imap.timeout(0.5)(slow, [1, 2]))
        
        pool.terminate()
    
    def test_star_map_timeout(self):
        """star().map.timeout() works with tuple unpacking."""
        pool = Pool(workers=2)
        
        def add(a, b):
            time.sleep(0.1)
            return a + b
        
        results = pool.star().map.timeout(5.0)(add, [(1, 2), (3, 4)])
        assert results == [3, 7]
    
    def test_unordered_imap_background(self):
        """unordered_imap.background() returns Future of list."""
        pool = Pool(workers=2)
        
        def quick(x):
            time.sleep(0.1)
            return x * 2
        
        future = pool.unordered_imap.background()(quick, [1, 2, 3])
        
        assert isinstance(future, Future)
        results = future.result(timeout=5.0)
        # Results may be in any order
        assert sorted(results) == [2, 4, 6]
    
    @pytest.mark.asyncio
    async def test_unordered_imap_asynced(self):
        """unordered_imap.asynced() returns coroutine for list."""
        pool = Pool(workers=2)
        
        def quick(x):
            return x * 2
        
        results = await pool.unordered_imap.asynced()(quick, [1, 2, 3])
        # Results may be in any order
        assert sorted(results) == [2, 4, 6]


# =============================================================================
# Integration Tests
# =============================================================================

class TestModifierChaining:
    """Tests for modifier chaining patterns."""
    
    def test_result_timeout_asynced_chain(self):
        """result.timeout().asynced() chains work."""
        p = QuickProcess(5)
        p.start()
        
        # Get the async callable with timeout
        async_fn = p.result.timeout(5.0).asynced()
        
        # Run it
        result = asyncio.run(async_fn())
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_multiple_processes_async(self):
        """Multiple processes can be awaited concurrently."""
        processes = [QuickProcess(i) for i in range(5)]
        for p in processes:
            p.start()
        
        # Await all results concurrently
        results = await asyncio.gather(
            *[p.result.asynced()() for p in processes]
        )
        
        assert results == [0, 2, 4, 6, 8]


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
