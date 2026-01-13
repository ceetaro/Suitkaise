# test the Pool class for batch parallel processing

import time
import pytest  # type: ignore

from suitkaise.processing import Process, Pool, AsyncResult
from suitkaise import sktime


# =============================================================================
# Test Functions for Pool
# =============================================================================

def square(x):
    """Simple function that squares a number."""
    return x ** 2


def add_pair(a, b):
    """Function that takes two arguments and adds them."""
    return a + b


def slow_square(x):
    """Square with a small delay to test parallelism."""
    time.sleep(0.02)
    return x ** 2


def failing_function(x):
    """Function that always fails."""
    raise ValueError(f"Failed on {x}")


# =============================================================================
# Basic Pool Tests
# =============================================================================

class TestPoolBasics:
    """Tests for basic Pool functionality."""
    
    def test_pool_creation(self, reporter):
        """Pool can be created with default or custom worker count."""
        
        pool = Pool()
        reporter.add(f"  default pool created")
        
        pool8 = Pool(workers=8)
        reporter.add(f"  pool with 8 workers created")
        
        assert pool is not None
        assert pool8 is not None
    
    def test_pool_map_with_function(self, reporter):
        """Pool.map() applies function to each item and returns ordered list."""
        
        pool = Pool(workers=4)
        items = [1, 2, 3, 4, 5]
        
        results = pool.map(square, items)
        
        reporter.add(f"  input: {items}")
        reporter.add(f"  results: {results}")
        
        assert results == [1, 4, 9, 16, 25]
        pool.close()
    
    def test_pool_map_preserves_order(self, reporter):
        """Pool.map() returns results in the same order as inputs."""
        
        pool = Pool(workers=4)
        items = [5, 1, 3, 2, 4]  # Not sorted
        
        results = pool.map(square, items)
        
        reporter.add(f"  input: {items}")
        reporter.add(f"  results: {results}")
        
        expected = [25, 1, 9, 4, 16]  # Same order as input
        assert results == expected
        pool.close()
    
    def test_pool_map_empty_iterable(self, reporter):
        """Pool.map() with empty iterable returns empty list."""
        
        pool = Pool(workers=4)
        results = pool.map(square, [])
        
        reporter.add(f"  results for empty input: {results}")
        
        assert results == []
        pool.close()
    
    def test_pool_context_manager(self, reporter):
        """Pool can be used as context manager."""
        
        with Pool(workers=4) as pool:
            results = pool.map(square, [1, 2, 3])
        
        reporter.add(f"  results: {results}")
        
        assert results == [1, 4, 9]


# =============================================================================
# Pool.imap() Tests
# =============================================================================

class TestPoolImap:
    """Tests for Pool.imap() ordered iterator."""
    
    def test_imap_returns_iterator(self, reporter):
        """Pool.imap() returns an iterator, not a list."""
        
        pool = Pool(workers=4)
        result = pool.imap(square, [1, 2, 3])
        
        reporter.add(f"  imap returns: {type(result).__name__}")
        
        # Consume iterator
        results = list(result)
        reporter.add(f"  collected results: {results}")
        
        assert results == [1, 4, 9]
        pool.close()
    
    def test_imap_preserves_order(self, reporter):
        """Pool.imap() yields results in input order."""
        
        pool = Pool(workers=4)
        items = [5, 1, 3, 2, 4]
        
        results = []
        for r in pool.imap(slow_square, items):
            results.append(r)
        
        reporter.add(f"  input: {items}")
        reporter.add(f"  results: {results}")
        
        expected = [25, 1, 9, 4, 16]
        assert results == expected
        pool.close()
    
    def test_imap_can_process_incrementally(self, reporter):
        """Pool.imap() allows processing results as they become available."""
        
        pool = Pool(workers=4)
        
        processed = []
        for i, result in enumerate(pool.imap(slow_square, [1, 2, 3, 4])):
            processed.append(f"item {i}: {result}")
        
        reporter.add(f"  processed incrementally: {len(processed)} items")
        for p in processed:
            reporter.add(f"    {p}")
        
        assert len(processed) == 4
        pool.close()


# =============================================================================
# Pool.async_map() Tests
# =============================================================================

class TestPoolAsyncMap:
    """Tests for Pool.async_map() non-blocking operation."""
    
    def test_async_map_returns_immediately(self, reporter):
        """Pool.async_map() returns immediately without blocking."""
        
        pool = Pool(workers=4)
        
        start = time.time()
        async_result = pool.async_map(slow_square, [1, 2, 3, 4])
        call_time = time.time() - start
        
        reporter.add(f"  async_map returned in: {call_time:.4f}s")
        reporter.add(f"  returned type: {type(async_result).__name__}")
        
        # Should return almost immediately
        assert call_time < 0.1
        assert isinstance(async_result, AsyncResult)
        
        # Now wait and get results
        results = async_result.get()
        reporter.add(f"  final results: {results}")
        
        assert results == [1, 4, 9, 16]
        pool.close()
    
    def test_async_result_ready(self, reporter):
        """AsyncResult.ready() correctly reports completion status."""
        
        pool = Pool(workers=4)
        async_result = pool.async_map(slow_square, [1, 2, 3, 4])
        
        # Immediately after call, probably not ready
        immediately_ready = async_result.ready()
        reporter.add(f"  ready immediately: {immediately_ready}")
        
        # Wait for completion
        async_result.wait()
        
        after_wait_ready = async_result.ready()
        reporter.add(f"  ready after wait: {after_wait_ready}")
        
        assert after_wait_ready == True
        pool.close()
    
    def test_async_result_wait(self, reporter):
        """AsyncResult.wait() blocks until all results are ready."""
        
        pool = Pool(workers=4)
        async_result = pool.async_map(slow_square, [1, 2, 3, 4])
        
        start = time.time()
        async_result.wait()
        wait_time = time.time() - start
        
        reporter.add(f"  wait() blocked for: {wait_time:.3f}s")
        
        # Should have waited for workers to complete
        assert wait_time > 0.01
        assert async_result.ready()
        pool.close()
    
    def test_async_result_get_with_timeout(self, reporter):
        """AsyncResult.get() with timeout raises TimeoutError if not ready."""
        
        pool = Pool(workers=4)
        
        # Very slow function
        def very_slow(x):
            time.sleep(5)
            return x
        
        async_result = pool.async_map(very_slow, [1])
        
        with pytest.raises(TimeoutError):
            async_result.get(timeout=0.1)
        
        reporter.add(f"  get(timeout=0.1) raised TimeoutError as expected")
        
        pool.terminate()


# =============================================================================
# Pool.unordered_imap() Tests
# =============================================================================

class TestPoolUnorderedImap:
    """Tests for Pool.unordered_imap() fast unordered iteration."""
    
    def test_unordered_imap_returns_all_results(self, reporter):
        """Pool.unordered_imap() returns all results eventually."""
        
        pool = Pool(workers=4)
        items = [1, 2, 3, 4, 5]
        
        results = list(pool.unordered_imap(square, items))
        
        reporter.add(f"  input: {items}")
        reporter.add(f"  results (any order): {sorted(results)}")
        
        # All results present, order may vary
        assert sorted(results) == [1, 4, 9, 16, 25]
        pool.close()
    
    def test_unordered_imap_may_differ_from_input_order(self, reporter):
        """Pool.unordered_imap() results may come in different order than input."""
        
        pool = Pool(workers=4)
        
        # Different sleep times to encourage out-of-order completion
        def variable_delay(x):
            time.sleep(0.01 * (5 - x))  # Lower x = longer sleep
            return x
        
        items = [1, 2, 3, 4, 5]
        results = list(pool.unordered_imap(variable_delay, items))
        
        reporter.add(f"  input: {items}")
        reporter.add(f"  results (completion order): {results}")
        
        # Results should all be present
        assert sorted(results) == sorted(items)
        pool.close()


# =============================================================================
# Pool.star() Modifier Tests
# =============================================================================

class TestPoolStar:
    """Tests for Pool.star() tuple unpacking modifier."""
    
    def test_star_map_unpacks_tuples(self, reporter):
        """star().map() unpacks tuples as function arguments."""
        
        pool = Pool(workers=4)
        items = [(1, 2), (3, 4), (5, 6)]
        
        results = pool.star().map(add_pair, items)
        
        reporter.add(f"  input tuples: {items}")
        reporter.add(f"  results (unpacked as args): {results}")
        
        assert results == [3, 7, 11]  # 1+2, 3+4, 5+6
        pool.close()
    
    def test_star_imap_unpacks_tuples(self, reporter):
        """star().imap() unpacks tuples as function arguments."""
        
        pool = Pool(workers=4)
        items = [(1, 2), (3, 4), (5, 6)]
        
        results = list(pool.star().imap(add_pair, items))
        
        reporter.add(f"  input tuples: {items}")
        reporter.add(f"  results: {results}")
        
        assert results == [3, 7, 11]
        pool.close()
    
    def test_star_async_map_unpacks_tuples(self, reporter):
        """star().async_map() unpacks tuples as function arguments."""
        
        pool = Pool(workers=4)
        items = [(1, 2), (3, 4), (5, 6)]
        
        async_result = pool.star().async_map(add_pair, items)
        results = async_result.get()
        
        reporter.add(f"  input tuples: {items}")
        reporter.add(f"  results: {results}")
        
        assert results == [3, 7, 11]
        pool.close()
    
    def test_star_unordered_imap_unpacks_tuples(self, reporter):
        """star().unordered_imap() unpacks tuples as function arguments."""
        
        pool = Pool(workers=4)
        items = [(1, 2), (3, 4), (5, 6)]
        
        results = list(pool.star().unordered_imap(add_pair, items))
        
        reporter.add(f"  input tuples: {items}")
        reporter.add(f"  results (any order): {sorted(results)}")
        
        assert sorted(results) == [3, 7, 11]
        pool.close()
    
    def test_without_star_tuple_is_single_arg(self, reporter):
        """Without star(), entire tuple is passed as single argument."""
        
        pool = Pool(workers=4)
        
        def process_tuple(t):
            return sum(t)
        
        items = [(1, 2, 3), (4, 5, 6)]
        results = pool.map(process_tuple, items)
        
        reporter.add(f"  input tuples: {items}")
        reporter.add(f"  results (tuple as single arg): {results}")
        
        assert results == [6, 15]  # sum((1,2,3)), sum((4,5,6))
        pool.close()


# =============================================================================
# Pool with Process Classes
# =============================================================================

class TestPoolWithProcessClasses:
    """Tests for Pool with Process-inheriting classes."""
    
    def test_pool_map_with_process_class(self, reporter):
        """Pool.map() works with Process classes."""
        
        class SquareProcess(Process):
            def __init__(self, value):
                self.value = value
                self.config.runs = 1
            
            def __run__(self):
                self.result_value = self.value ** 2
            
            def __result__(self):
                return self.result_value
        
        pool = Pool(workers=4)
        items = [1, 2, 3, 4, 5]
        
        results = pool.map(SquareProcess, items)
        
        reporter.add(f"  input: {items}")
        reporter.add(f"  results: {results}")
        
        assert results == [1, 4, 9, 16, 25]
        pool.close()
    
    def test_pool_imap_with_process_class(self, reporter):
        """Pool.imap() works with Process classes."""
        
        class DoubleProcess(Process):
            def __init__(self, value):
                self.value = value
                self.config.runs = 1
            
            def __run__(self):
                self.result_value = self.value * 2
            
            def __result__(self):
                return self.result_value
        
        pool = Pool(workers=4)
        items = [1, 2, 3, 4, 5]
        
        results = list(pool.imap(DoubleProcess, items))
        
        reporter.add(f"  input: {items}")
        reporter.add(f"  results: {results}")
        
        assert results == [2, 4, 6, 8, 10]
        pool.close()
    
    def test_pool_star_with_process_class(self, reporter):
        """Pool.star().map() unpacks args to Process.__init__()."""
        
        class AddProcess(Process):
            def __init__(self, a, b):
                self.a = a
                self.b = b
                self.config.runs = 1
            
            def __run__(self):
                self.sum = self.a + self.b
            
            def __result__(self):
                return self.sum
        
        pool = Pool(workers=4)
        items = [(1, 2), (3, 4), (5, 6)]
        
        results = pool.star().map(AddProcess, items)
        
        reporter.add(f"  input tuples: {items}")
        reporter.add(f"  results: {results}")
        
        assert results == [3, 7, 11]
        pool.close()
    
    def test_pool_process_with_multiple_runs(self, reporter):
        """Pool respects Process.config.runs for multiple iterations."""
        
        class CountingProcess(Process):
            def __init__(self, start):
                self.counter = start
                self.config.runs = 3  # Run 3 times
            
            def __run__(self):
                self.counter += 1
            
            def __result__(self):
                return self.counter
        
        pool = Pool(workers=4)
        items = [0, 10, 100]
        
        results = pool.map(CountingProcess, items)
        
        reporter.add(f"  start values: {items}")
        reporter.add(f"  after 3 runs each: {results}")
        
        # Each starts at N and increments 3 times
        assert results == [3, 13, 103]
        pool.close()
    
    def test_pool_process_with_lives(self, reporter):
        """Pool respects Process.config.lives for retry on error."""
        
        class FlakeyProcess(Process):
            def __init__(self, value):
                self.value = value
                self.attempts = 0
                self.config.runs = 1
                self.config.lives = 3
            
            def __run__(self):
                self.attempts += 1
                # Fail first 2 attempts for odd values
                if self.value % 2 == 1 and self.attempts < 3:
                    raise ValueError(f"Failing attempt {self.attempts}")
            
            def __result__(self):
                return f"{self.value}: attempt {self.attempts}"
        
        pool = Pool(workers=4)
        items = [1, 2, 3]
        
        results = pool.map(FlakeyProcess, items)
        
        reporter.add(f"  input: {items}")
        reporter.add(f"  results: {results}")
        
        # Odd values needed 3 attempts, even values needed 1
        assert "1: attempt 3" in results
        assert "2: attempt 1" in results
        assert "3: attempt 3" in results
        pool.close()
    
    def test_pool_process_with_self_stop(self, reporter):
        """Pool respects self.stop() called from within Process."""
        
        class StopAtFiveProcess(Process):
            def __init__(self, start):
                self.counter = start
                # config.runs = None means infinite
            
            def __run__(self):
                self.counter += 1
                if self.counter >= 5:
                    self.stop()
            
            def __result__(self):
                return self.counter
        
        pool = Pool(workers=4)
        items = [0, 2, 4]
        
        results = pool.map(StopAtFiveProcess, items)
        
        reporter.add(f"  start values: {items}")
        reporter.add(f"  stopped at: {results}")
        
        # All should stop at 5
        assert results == [5, 5, 5]
        pool.close()
    
    def test_pool_process_uses_lifecycle_methods(self, reporter):
        """Pool executes all Process lifecycle methods."""
        
        class LifecycleProcess(Process):
            def __init__(self, value):
                self.value = value
                self.config.runs = 2
                self.order = []
            
            def __prerun__(self):
                self.order.append('prerun')
            
            def __run__(self):
                self.order.append('run')
            
            def __postrun__(self):
                self.order.append('postrun')
            
            def __onfinish__(self):
                self.order.append('onfinish')
            
            def __result__(self):
                return self.order
        
        pool = Pool(workers=4)
        items = [1]
        
        results = pool.map(LifecycleProcess, items)
        
        reporter.add(f"  lifecycle order: {results[0]}")
        
        expected = ['prerun', 'run', 'postrun', 'prerun', 'run', 'postrun', 'onfinish']
        assert results[0] == expected
        pool.close()


# =============================================================================
# Pool Error Handling
# =============================================================================

class TestPoolErrorHandling:
    """Tests for Pool error handling."""
    
    def test_pool_raises_on_function_error(self, reporter):
        """Pool raises exception when function fails."""
        
        pool = Pool(workers=4)
        
        with pytest.raises(ValueError) as exc_info:
            pool.map(failing_function, [1, 2, 3])
        
        reporter.add(f"  error raised: {type(exc_info.value).__name__}")
        reporter.add(f"  message: {exc_info.value}")
        
        pool.terminate()
    
    def test_pool_async_get_raises_on_error(self, reporter):
        """AsyncResult.get() raises exception when function fails."""
        
        pool = Pool(workers=4)
        async_result = pool.async_map(failing_function, [1])
        
        with pytest.raises(ValueError):
            async_result.get()
        
        reporter.add(f"  async_result.get() raised ValueError as expected")
        pool.terminate()


# =============================================================================
# Pool Parallelism Tests
# =============================================================================

class TestPoolParallelism:
    """Tests for Pool parallel execution."""
    
    def test_pool_runs_in_parallel(self, reporter):
        """Pool executes items in parallel, not sequentially."""
        
        pool = Pool(workers=4)
        
        # 4 items, each sleeping 0.1s
        items = [0.1, 0.1, 0.1, 0.1]
        
        def sleep_and_return(duration):
            time.sleep(duration)
            return duration
        
        start = time.time()
        results = pool.map(sleep_and_return, items)
        elapsed = time.time() - start
        
        sequential_time = sum(items)  # 0.4s
        
        reporter.add(f"  4 workers, each sleeping 0.1s")
        reporter.add(f"  sequential would take: {sequential_time:.2f}s")
        reporter.add(f"  actual elapsed: {elapsed:.2f}s")
        
        # Should be much faster than sequential
        assert elapsed < sequential_time * 0.7
        pool.close()
    
    def test_pool_with_more_items_than_workers(self, reporter):
        """Pool handles more items than workers correctly."""
        
        pool = Pool(workers=2)
        items = list(range(10))
        
        results = pool.map(square, items)
        
        reporter.add(f"  workers: 2, items: {len(items)}")
        reporter.add(f"  all results correct: {results == [x**2 for x in items]}")
        
        assert results == [x ** 2 for x in items]
        pool.close()


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])

