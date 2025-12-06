# incorporate the processing module with the rest of the suitkaise library and
# test them in tandem using detailed, real world examples.

import pytest  # type: ignore

from suitkaise.processing import Process, timesection
from suitkaise import sktime


class TestWithSktime:
    """Tests for processing module integration with sktime."""
    
    def test_custom_timer_in_process(self, reporter):
        """Process can use sktime.Timer for custom timing within lifecycle methods."""
        
        class TimedWorkProcess(Process):
            def __init__(self):
                self.custom_timer = sktime.Timer()
                self.config.num_loops = 5
            
            def __loop__(self):
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
    
    def test_timesection_decorator_with_sktime_analysis(self, reporter):
        """@timesection() creates timers compatible with sktime analysis."""
        
        class AnalyzedProcess(Process):
            def __init__(self):
                self.config.num_loops = 10
            
            @timesection()
            def __preloop__(self):
                sktime.sleep(0.005)
            
            @timesection()
            def __loop__(self):
                sktime.sleep(0.01)
            
            @timesection()
            def __postloop__(self):
                sktime.sleep(0.005)
            
            def __result__(self):
                # Analyze timing statistics
                loop = self.timers.loop if self.timers else None
                full_loop = self.timers.full_loop if self.timers else None
                return {
                    'loop_mean': loop.mean if loop else None,
                    'loop_min': loop.min if loop else None,
                    'loop_max': loop.max if loop else None,
                    'loop_stdev': loop.stdev if loop else None,
                    'full_loop_mean': full_loop.mean if full_loop else None,
                    'full_loop_total': full_loop.total_time if full_loop else None,
                }
        
        p = AnalyzedProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  loop mean: {result['loop_mean']:.4f}s")
        reporter.add(f"  loop min: {result['loop_min']:.4f}s")
        reporter.add(f"  loop max: {result['loop_max']:.4f}s")
        reporter.add(f"  full_loop mean: {result['full_loop_mean']:.4f}s")
        reporter.add(f"  full_loop total: {result['full_loop_total']:.4f}s")
        
        assert result['loop_mean'] >= 0.008
        assert result['full_loop_mean'] >= 0.015  # preloop + loop + postloop
    
    def test_yawn_rate_limiting_in_process(self, reporter):
        """Process can use sktime.Yawn for rate limiting within loop."""
        
        class RateLimitedProcess(Process):
            def __init__(self):
                self.rate_limiter = sktime.Yawn(sleep_duration=0.1, yawn_threshold=3)
                self.yawn_count = 0
                self.config.num_loops = 10
            
            def __loop__(self):
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
        reporter.add(f"  num_loops: 10")
        reporter.add(f"  times slept: {result['yawn_count']}")
        reporter.add(f"  total elapsed: {elapsed:.2f}s")
        
        # Should have slept 3 times (at calls 3, 6, 9)
        assert result['yawn_count'] == 3
    
    def test_elapsed_time_tracking(self, reporter):
        """Process can use sktime.elapsed() for duration tracking."""
        
        class DurationTrackingProcess(Process):
            def __init__(self):
                self.start_time = None
                self.lap_durations = []
                self.config.num_loops = 5
            
            def __preloop__(self):
                self.start_time = sktime.now()
            
            def __loop__(self):
                sktime.sleep(0.02)
            
            def __postloop__(self):
                if self.start_time is not None:
                    duration = sktime.elapsed(self.start_time)
                    self.lap_durations.append(duration)
            
            def __result__(self):
                return {
                    'durations': self.lap_durations,
                    'mean_duration': sum(self.lap_durations) / len(self.lap_durations),
                }
        
        p = DurationTrackingProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  lap durations: {[f'{d:.4f}s' for d in result['durations']]}")
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
            
            @timesection()
            def __loop__(self):
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
                    'avg_batch_time': self.timers.loop.mean if self.timers and self.timers.loop else None,
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
        
        Note: Each retry starts with fresh state, so we use config.lives
        to track which attempt we're on (engine updates it to remaining lives).
        """
        
        class BackoffProcess(Process):
            def __init__(self):
                self.config.num_loops = 1
                self.config.lives = 5
            
            def __loop__(self):
                # Fresh state on each retry, but config.lives is updated.
                # Fail until we're on the last 2 lives
                if self.config.lives > 2:
                    raise ConnectionError(f"Failing with {self.config.lives} lives remaining")
                # Success on lives 1 or 2
            
            def __result__(self):
                return f"Succeeded with {self.config.lives} lives remaining"
        
        p = BackoffProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  configured lives: 5")
        reporter.add(f"  result: {result}")
        
        # Should succeed after using 3 lives (fails at 5, 4, 3 - succeeds at 2)
        assert "Succeeded" in result
        assert "2 lives" in result
    
    def test_progress_tracking_process(self, reporter):
        """
        Simulate a process that tracks its own progress.
        """
        
        class ProgressProcess(Process):
            def __init__(self, total_items):
                self.total_items = total_items
                self.processed = 0
                self.progress_snapshots = []
                self.config.num_loops = total_items
            
            def __loop__(self):
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
                self.config.num_loops = 1
            
            def __loop__(self):
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
