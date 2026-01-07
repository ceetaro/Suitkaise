# incorporate the processing module with the rest of the suitkaise library and
# test them in tandem using detailed, real world examples.

import pytest  # type: ignore

from suitkaise.processing import Process
from suitkaise import sktime


class TestWithSktime:
    """Tests for processing module integration with sktime."""
    
    def test_custom_timer_in_process(self, reporter):
        """Process can use sktime.Timer for custom timing within lifecycle methods."""
        
        class TimedWorkProcess(Process):
            def __init__(self):
                self.custom_timer = sktime.Timer()
                self.config.runs = 5
            
            def __run__(self):
                with sktime.TimeThis(self.custom_timer):
                    sktime.sleep(0.02)
            
            def __result__(self):
                return {
                    'num_times': self.custom_timer.num_times,
                    'mean': self.custom_timer.mean,
                    'total': self.custom_timer.total_time,
                }
        
        p = TimedWorkProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  custom timer measurements: {result['num_times']}")
        reporter.add(f"  mean time: {result['mean']:.4f}s")
        reporter.add(f"  total time: {result['total']:.4f}s")
        
        assert result['num_times'] == 5
        assert result['mean'] >= 0.015  # At least 15ms per iteration
    
    def test_auto_timing_with_sktime_analysis(self, reporter):
        """Auto timing creates timers compatible with sktime analysis."""
        
        class AnalyzedProcess(Process):
            def __init__(self):
                self.config.runs = 10
            
            def __prerun__(self):
                sktime.sleep(0.005)
            
            def __run__(self):
                sktime.sleep(0.01)
            
            def __postrun__(self):
                sktime.sleep(0.005)
            
            def __result__(self):
                # Analyze timing statistics
                run = self.timers.run if self.timers else None
                full_run = self.timers.full_run if self.timers else None
                return {
                    'run_mean': run.mean if run else None,
                    'run_min': run.min if run else None,
                    'run_max': run.max if run else None,
                    'run_stdev': run.stdev if run else None,
                    'full_run_mean': full_run.mean if full_run else None,
                    'full_run_total': full_run.total_time if full_run else None,
                }
        
        p = AnalyzedProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  run mean: {result['run_mean']:.4f}s")
        reporter.add(f"  run min: {result['run_min']:.4f}s")
        reporter.add(f"  run max: {result['run_max']:.4f}s")
        reporter.add(f"  full_run mean: {result['full_run_mean']:.4f}s")
        reporter.add(f"  full_run total: {result['full_run_total']:.4f}s")
        
        assert result['run_mean'] >= 0.008
        assert result['full_run_mean'] >= 0.015  # prerun + run + postrun
    
    def test_yawn_rate_limiting_in_process(self, reporter):
        """Process can use sktime.Yawn for rate limiting within run."""
        
        class RateLimitedProcess(Process):
            def __init__(self):
                self.rate_limiter = sktime.Yawn(sleep_duration=0.1, yawn_threshold=3)
                self.yawn_count = 0
                self.config.runs = 10
            
            def __run__(self):
                if self.rate_limiter.yawn():
                    self.yawn_count += 1
            
            def __result__(self):
                return {
                    'yawn_count': self.yawn_count,
                    'stats': self.rate_limiter.get_stats(),
                }
        
        p = RateLimitedProcess()
        start = sktime.now()
        p.start()
        p.wait()
        elapsed = sktime.elapsed(start)
        result = p.result
        
        reporter.add(f"  yawn threshold: 3")
        reporter.add(f"  runs: 10")
        reporter.add(f"  times slept: {result['yawn_count']}")
        reporter.add(f"  total elapsed: {elapsed:.2f}s")
        
        # Should have slept 3 times (at calls 3, 6, 9)
        assert result['yawn_count'] == 3
    
    def test_elapsed_time_tracking(self, reporter):
        """Process can use sktime.elapsed() for duration tracking."""
        
        class DurationTrackingProcess(Process):
            def __init__(self):
                self.start_time = None
                self.run_durations = []
                self.config.runs = 5
            
            def __prerun__(self):
                self.start_time = sktime.now()
            
            def __run__(self):
                sktime.sleep(0.02)
            
            def __postrun__(self):
                if self.start_time is not None:
                    duration = sktime.elapsed(self.start_time)
                    self.run_durations.append(duration)
            
            def __result__(self):
                return {
                    'durations': self.run_durations,
                    'mean_duration': sum(self.run_durations) / len(self.run_durations),
                }
        
        p = DurationTrackingProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  run durations: {[f'{d:.4f}s' for d in result['durations']]}")
        reporter.add(f"  mean duration: {result['mean_duration']:.4f}s")
        
        assert len(result['durations']) == 5
        assert result['mean_duration'] >= 0.015


class TestRealWorldScenarios:
    """Real-world usage scenarios combining processing with other modules."""
    
    def test_batch_data_processor(self, reporter):
        """
        Simulate a batch data processor that:
        - Processes items in batches
        - Tracks timing statistics
        - Stops after time limit
        """
        
        class BatchProcessor(Process):
            def __init__(self, batch_size):
                self.batch_size = batch_size
                self.items_processed = 0
                self.batch_count = 0
                self.config.join_in = 0.5  # Stop after 0.5 seconds
            
            def __run__(self):
                # Simulate processing a batch
                for _ in range(self.batch_size):
                    sktime.sleep(0.002)  # 2ms per item
                    self.items_processed += 1
                self.batch_count += 1
            
            def __result__(self):
                return {
                    'items_processed': self.items_processed,
                    'batch_count': self.batch_count,
                    'items_per_batch': self.batch_size,
                    'avg_batch_time': self.timers.run.mean if self.timers and self.timers.run else None,
                }
        
        p = BatchProcessor(batch_size=10)
        start = sktime.now()
        p.start()
        p.wait()
        elapsed = sktime.elapsed(start)
        result = p.result
        
        reporter.add(f"  batch size: {result['items_per_batch']}")
        reporter.add(f"  batches processed: {result['batch_count']}")
        reporter.add(f"  total items: {result['items_processed']}")
        reporter.add(f"  avg batch time: {result['avg_batch_time']:.4f}s" if result['avg_batch_time'] else "  avg batch time: N/A")
        reporter.add(f"  total elapsed: {elapsed:.2f}s")
        
        assert result['batch_count'] > 0
        assert result['items_processed'] == result['batch_count'] * result['items_per_batch']
    
    def test_retry_with_exponential_backoff(self, reporter):
        """
        Simulate a process that retries failed operations with backoff.
        Uses lives system for retries.
        
        User state is preserved across retries, so we can track attempts.
        """
        
        class BackoffProcess(Process):
            def __init__(self):
                self.attempt = 0
                self.config.runs = 1
                self.config.lives = 5
            
            def __run__(self):
                self.attempt += 1
                # Fail on first 3 attempts, succeed on 4th
                if self.attempt < 4:
                    raise ConnectionError(f"Failing on attempt {self.attempt}")
                # Success on attempt 4
            
            def __result__(self):
                return f"Succeeded on attempt {self.attempt}"
        
        p = BackoffProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  configured lives: 5")
        reporter.add(f"  result: {result}")
        
        # Should succeed on 4th attempt (fails at 1, 2, 3 - succeeds at 4)
        assert "Succeeded" in result
        assert "attempt 4" in result
    
    def test_progress_tracking_process(self, reporter):
        """
        Simulate a process that tracks its own progress.
        """
        
        class ProgressProcess(Process):
            def __init__(self, total_items):
                self.total_items = total_items
                self.processed = 0
                self.progress_snapshots = []
                self.config.runs = total_items
            
            def __run__(self):
                sktime.sleep(0.005)
                self.processed += 1
                progress = (self.processed / self.total_items) * 100
                self.progress_snapshots.append(progress)
            
            def __result__(self):
                return {
                    'final_progress': self.progress_snapshots[-1] if self.progress_snapshots else 0,
                    'processed': self.processed,
                    'total': self.total_items,
                }
        
        p = ProgressProcess(total_items=10)
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  total items: {result['total']}")
        reporter.add(f"  processed: {result['processed']}")
        reporter.add(f"  final progress: {result['final_progress']:.1f}%")
        
        assert result['final_progress'] == 100.0
        assert result['processed'] == result['total']
    
    def test_worker_pool_pattern(self, reporter):
        """
        Simulate a worker pool processing tasks.
        """
        
        class TaskWorker(Process):
            def __init__(self, task_id, task_data):
                self.task_id = task_id
                self.task_data = task_data
                self.result_value = None
                self.config.runs = 1
            
            def __run__(self):
                # Simulate computation based on task data
                sktime.sleep(0.02)
                self.result_value = sum(self.task_data) * self.task_id
            
            def __result__(self):
                return {
                    'task_id': self.task_id,
                    'input': self.task_data,
                    'output': self.result_value,
                }
        
        # Create tasks
        tasks = [
            (1, [1, 2, 3]),
            (2, [4, 5, 6]),
            (3, [7, 8, 9]),
            (4, [10, 11, 12]),
        ]
        
        # Create workers
        workers = [TaskWorker(tid, data) for tid, data in tasks]
        
        # Start all
        start = sktime.now()
        for w in workers:
            w.start()
        
        # Wait and collect
        for w in workers:
            w.wait()
        elapsed = sktime.elapsed(start)
        
        results = [w.result for w in workers]
        
        reporter.add(f"  tasks: {len(tasks)}")
        reporter.add(f"  total time: {elapsed:.2f}s")
        for r in results:
            reporter.add(f"    task {r['task_id']}: sum({r['input']}) * {r['task_id']} = {r['output']}")
        
        # Verify calculations
        assert results[0]['output'] == 6 * 1   # (1+2+3) * 1
        assert results[1]['output'] == 15 * 2  # (4+5+6) * 2
        assert results[2]['output'] == 24 * 3  # (7+8+9) * 3
        assert results[3]['output'] == 33 * 4  # (10+11+12) * 4


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
