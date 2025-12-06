# this test uses the multiple process pattern from the concept.md file

import time
import pytest  # type: ignore

from suitkaise.processing import Process


class TestMultipleProcesses:
    """Tests for running multiple Process instances concurrently."""
    
    def test_multiple_workers_pattern(self, reporter):
        """Multiple workers can run concurrently and collect results."""
        
        class Worker(Process):
            def __init__(self, worker_id):
                self.worker_id = worker_id
                self.config.num_loops = 5
            
            def __loop__(self):
                time.sleep(0.01)  # Simulate work
            
            def __result__(self):
                return f"Worker {self.worker_id} done"
        
        # Create multiple processes
        processes = [Worker(i) for i in range(5)]
        
        reporter.add(f"  created {len(processes)} worker processes")
        
        # Start all
        start_time = time.time()
        for p in processes:
            p.start()
        
        reporter.add(f"  all processes started")
        
        # Wait for all to finish
        for p in processes:
            p.wait()
        
        elapsed = time.time() - start_time
        reporter.add(f"  all processes finished in {elapsed:.2f}s")
        
        # Collect results
        results = [p.result for p in processes]
        
        reporter.add(f"  results: {results}")
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result == f"Worker {i} done"
    
    def test_parallel_execution_time(self, reporter):
        """
        Parallel processes take wall-clock time of slowest, not sum.
        
        If 5 processes each sleep 0.1s, total should be ~0.1s not ~0.5s.
        """
        
        class SleepWorker(Process):
            def __init__(self, sleep_time):
                self.sleep_time = sleep_time
                self.config.num_loops = 1
            
            def __loop__(self):
                time.sleep(self.sleep_time)
            
            def __result__(self):
                return self.sleep_time
        
        # All workers sleep 0.1s
        workers = [SleepWorker(0.1) for _ in range(5)]
        
        start = time.time()
        for w in workers:
            w.start()
        for w in workers:
            w.wait()
        elapsed = time.time() - start
        
        reporter.add(f"  5 workers, each sleeping 0.1s")
        reporter.add(f"  total wall-clock time: {elapsed:.2f}s")
        reporter.add(f"  (sequential would be ~0.5s)")
        
        # Should be closer to 0.1s than 0.5s (with some overhead)
        assert elapsed < 0.4, f"Parallel execution too slow: {elapsed:.2f}s"
    
    def test_staggered_finish_times(self, reporter):
        """
        Processes with different durations demonstrate parallel execution.
        
        Timeline from concept:
        Process 0: sleeps 0.12s
        Process 1: sleeps 0.04s  
        Process 2: sleeps 0.22s <- slowest
        Process 3: sleeps 0.06s
        Process 4: sleeps 0.08s
        
        Total time ≈ 0.22s (slowest), not sum.
        """
        
        class TimedWorker(Process):
            def __init__(self, worker_id, duration):
                self.worker_id = worker_id
                self.duration = duration
                self.config.num_loops = 1
            
            def __loop__(self):
                time.sleep(self.duration)
            
            def __result__(self):
                return f"Worker {self.worker_id} slept {self.duration}s"
        
        durations = [0.12, 0.04, 0.22, 0.06, 0.08]
        workers = [TimedWorker(i, d) for i, d in enumerate(durations)]
        
        start = time.time()
        for w in workers:
            w.start()
        for w in workers:
            w.wait()
        elapsed = time.time() - start
        
        results = [w.result for w in workers]
        
        reporter.add(f"  durations: {durations}")
        reporter.add(f"  slowest: {max(durations)}s")
        reporter.add(f"  sum: {sum(durations)}s")
        reporter.add(f"  actual wall-clock: {elapsed:.2f}s")
        
        # Should be around max duration, not sum
        assert elapsed < sum(durations) * 0.8, "Not running in parallel"
        assert elapsed >= max(durations) - 0.05, "Finished faster than slowest"
    
    def test_wait_order_independence(self, reporter):
        """
        Waiting on finished processes returns immediately.
        
        If we wait on processes in order [0,1,2,3,4] but process 1 finishes
        before process 0, wait(p[1]) should return instantly after wait(p[0]).
        """
        
        class OrderedWorker(Process):
            def __init__(self, worker_id, duration):
                self.worker_id = worker_id
                self.duration = duration
                self.config.num_loops = 1
                self.finish_time = None
            
            def __loop__(self):
                time.sleep(self.duration)
            
            def __result__(self):
                return self.worker_id
        
        # Process 0 takes longest, others are faster
        durations = [0.2, 0.05, 0.05, 0.05, 0.05]
        workers = [OrderedWorker(i, d) for i, d in enumerate(durations)]
        
        for w in workers:
            w.start()
        
        wait_times = []
        for i, w in enumerate(workers):
            t0 = time.time()
            w.wait()
            wait_times.append(time.time() - t0)
        
        reporter.add(f"  durations: {durations}")
        reporter.add(f"  wait times: {[f'{t:.3f}s' for t in wait_times]}")
        reporter.add(f"  (first wait blocks, rest should be instant)")
        
        # First wait should take ~0.2s, rest should be nearly instant
        assert wait_times[0] > 0.1, "First wait should block"
        for i in range(1, 5):
            assert wait_times[i] < 0.05, f"Wait {i} should be instant"
    
    def test_collect_mixed_results(self, reporter):
        """Multiple processes can return different types of results."""
        
        class ComputeWorker(Process):
            def __init__(self, operation, value):
                self.operation = operation
                self.value = value
                self.config.num_loops = 1
            
            def __loop__(self):
                pass
            
            def __result__(self):
                if self.operation == "square":
                    return self.value ** 2
                elif self.operation == "double":
                    return self.value * 2
                elif self.operation == "string":
                    return f"value is {self.value}"
                return None
        
        workers = [
            ComputeWorker("square", 5),
            ComputeWorker("double", 10),
            ComputeWorker("string", 42),
            ComputeWorker("square", 3),
        ]
        
        for w in workers:
            w.start()
        for w in workers:
            w.wait()
        
        results = [w.result for w in workers]
        
        reporter.add(f"  operations: square(5), double(10), string(42), square(3)")
        reporter.add(f"  results: {results}")
        
        assert results[0] == 25
        assert results[1] == 20
        assert results[2] == "value is 42"
        assert results[3] == 9


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
