# test edge cases and unusual scenarios for the processing module

import pytest  # type: ignore

from suitkaise.processing import Process, ProcessError
from suitkaise.processing._int.errors import (
    PreRunError, RunError, PostRunError, 
    OnFinishError, ResultError, ProcessTimeoutError
)
from suitkaise import sktime


# =============================================================================
# Empty / Minimal Process Tests
# =============================================================================

class TestMinimalProcesses:
    """Test processes with minimal or no implementation."""
    
    def test_completely_empty_process(self, reporter):
        """Process with no overrides at all."""
        
        class EmptyProcess(Process):
            pass
        
        p = EmptyProcess()
        p.start()
        
        # Should run indefinitely - stop it
        sktime.sleep(0.1)
        p.stop()
        p.wait()
        
        result = p.result()
        reporter.add(f"  empty process result: {result}")
        
        # Default __result__ returns None
        assert result is None
    
    def test_process_with_only_result(self, reporter):
        """Process that only defines __result__."""
        
        class ResultOnlyProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __result__(self):
                return "only result defined"
        
        p = ResultOnlyProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  result: {result}")
        assert result == "only result defined"
    
    def test_process_zero_runs(self, reporter):
        """Process configured for 0 runs."""
        
        class ZeroRunProcess(Process):
            def __init__(self):
                self.config.runs = 0
                self.run_called = False
            
            def __run__(self):
                self.run_called = True
            
            def __result__(self):
                return {"run_called": self.run_called}
        
        p = ZeroRunProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  run_called: {result['run_called']}")
        
        # 0 runs means __run__ should never be called
        assert result['run_called'] is False
    
    def test_process_one_run(self, reporter):
        """Process configured for exactly 1 run."""
        
        class OneRunProcess(Process):
            def __init__(self):
                self.config.runs = 1
                self.run_count = 0
            
            def __run__(self):
                self.run_count += 1
            
            def __result__(self):
                return self.run_count
        
        p = OneRunProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  run executed: {result} times")
        assert result == 1


# =============================================================================
# State and Data Edge Cases
# =============================================================================

class TestStateEdgeCases:
    """Test unusual state and data scenarios."""
    
    def test_large_state_serialization(self, reporter):
        """Process with large data structures."""
        
        class LargeStateProcess(Process):
            def __init__(self):
                # Create large data structures
                self.large_list = list(range(10000))
                self.large_dict = {f"key_{i}": i * 2 for i in range(1000)}
                self.nested = {"a": {"b": {"c": {"d": list(range(100))}}}}
                self.config.runs = 1
            
            def __run__(self):
                # Modify data
                self.large_list.append(99999)
                self.large_dict["final"] = "done"
            
            def __result__(self):
                return {
                    "list_len": len(self.large_list),
                    "dict_len": len(self.large_dict),
                    "nested_depth": len(self.nested["a"]["b"]["c"]["d"]),
                }
        
        p = LargeStateProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  list size: {result['list_len']}")
        reporter.add(f"  dict size: {result['dict_len']}")
        
        assert result['list_len'] == 10001
        assert result['dict_len'] == 1001
    
    def test_none_values_everywhere(self, reporter):
        """Process with None values in various places."""
        
        class NoneProcess(Process):
            def __init__(self):
                self.value = None
                self.config.runs = 1
            
            def __prerun__(self):
                return None  # Return None
            
            def __run__(self):
                self.value = None  # Set to None
            
            def __postrun__(self):
                pass  # Implicit None return
            
            def __result__(self):
                return None  # Explicitly return None
        
        p = NoneProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  result is None: {result is None}")
        assert result is None
    
    def test_complex_return_types(self, reporter):
        """Process returning various complex types."""
        
        class ComplexReturnProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __result__(self):
                return {
                    "tuple": (1, 2, 3),
                    "set": {1, 2, 3},  # Note: sets become lists in JSON
                    "bytes": b"hello",
                    "nested_tuple": ((1, 2), (3, 4)),
                    "mixed": [1, "two", 3.0, None, True],
                }
        
        p = ComplexReturnProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  tuple preserved: {result['tuple'] == (1, 2, 3)}")
        reporter.add(f"  bytes preserved: {result['bytes'] == b'hello'}")
        
        assert result['tuple'] == (1, 2, 3)
        assert result['mixed'] == [1, "two", 3.0, None, True]
    
    def test_mutable_default_argument_safety(self, reporter):
        """Ensure mutable defaults don't cause issues across instances."""
        
        class MutableDefaultProcess(Process):
            def __init__(self, items=None):
                self.items = items if items is not None else []
                self.config.runs = 3
            
            def __run__(self):
                self.items.append(self._current_run)
            
            def __result__(self):
                return self.items
        
        # Create two processes
        p1 = MutableDefaultProcess()
        p2 = MutableDefaultProcess()
        
        p1.start()
        p2.start()
        p1.wait()
        p2.wait()
        
        r1 = p1.result()
        r2 = p2.result()
        
        reporter.add(f"  p1 items: {r1}")
        reporter.add(f"  p2 items: {r2}")
        
        # Each should have independent lists
        assert r1 == [0, 1, 2]
        assert r2 == [0, 1, 2]
        assert r1 is not r2


# =============================================================================
# Timing Edge Cases
# =============================================================================

class TestTimingEdgeCases:
    """Test timing-related edge cases."""
    
    def test_very_short_join_in(self, reporter):
        """Process with very short join_in timeout."""
        
        class ShortJoinProcess(Process):
            def __init__(self):
                self.config.join_in = 0.05  # 50ms
                self.runs_completed = 0
            
            def __run__(self):
                sktime.sleep(0.02)
                self.runs_completed += 1
            
            def __result__(self):
                return self.runs_completed
        
        p = ShortJoinProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  runs in 50ms: {result}")
        
        # Should complete 1-3 runs in 50ms
        assert result >= 1
        assert result <= 5
    
    def test_join_in_zero(self, reporter):
        """Process with join_in = 0 (immediate stop)."""
        
        class ZeroJoinProcess(Process):
            def __init__(self):
                self.config.join_in = 0.0
                self.runs = 0
            
            def __run__(self):
                self.runs += 1
            
            def __result__(self):
                return self.runs
        
        p = ZeroJoinProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  runs with join_in=0: {result}")
        
        # Should stop immediately or after 1 run
        assert result <= 1
    
    def test_auto_timing_on_all_methods(self, reporter):
        """Auto timing on every lifecycle method."""
        
        class FullyTimedProcess(Process):
            def __init__(self):
                self.config.runs = 3
            
            def __prerun__(self):
                sktime.sleep(0.005)
            
            def __run__(self):
                sktime.sleep(0.01)
            
            def __postrun__(self):
                sktime.sleep(0.005)
            
            def __onfinish__(self):
                sktime.sleep(0.005)
            
            def __result__(self):
                return {
                    "prerun_times": self.timers.prerun.num_times if self.timers.prerun else 0,
                    "run_times": self.timers.run.num_times if self.timers.run else 0,
                    "postrun_times": self.timers.postrun.num_times if self.timers.postrun else 0,
                    "onfinish_times": self.timers.onfinish.num_times if self.timers.onfinish else 0,
                    "full_run_times": self.timers.full_run.num_times if self.timers.full_run else 0,
                }
        
        p = FullyTimedProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  prerun calls: {result['prerun_times']}")
        reporter.add(f"  run calls: {result['run_times']}")
        reporter.add(f"  postrun calls: {result['postrun_times']}")
        reporter.add(f"  onfinish calls: {result['onfinish_times']}")
        reporter.add(f"  full_run aggregates: {result['full_run_times']}")
        
        assert result['prerun_times'] == 3
        assert result['run_times'] == 3
        assert result['postrun_times'] == 3
        assert result['onfinish_times'] == 1


# =============================================================================
# Error Edge Cases
# =============================================================================

class TestErrorEdgeCases:
    """Test unusual error scenarios."""
    
    def test_error_in_first_run(self, reporter):
        """Error on the very first run iteration."""
        
        class FirstRunErrorProcess(Process):
            def __init__(self):
                self.config.runs = 10
            
            def __run__(self):
                raise ValueError("First run fails")
        
        p = FirstRunErrorProcess()
        p.start()
        p.wait()
        
        with pytest.raises(RunError) as exc_info:
            _ = p.result()
        
        reporter.add(f"  error type: {type(exc_info.value).__name__}")
        reporter.add(f"  original: {type(exc_info.value.original_error).__name__}")
        
        assert exc_info.value.current_run == 0
        assert isinstance(exc_info.value.original_error, ValueError)
    
    def test_error_in_onfinish(self, reporter):
        """Error in __onfinish__ after successful runs."""
        
        class OnfinishErrorProcess(Process):
            def __init__(self):
                self.config.runs = 3
                self.runs_done = 0
            
            def __run__(self):
                self.runs_done += 1
            
            def __onfinish__(self):
                raise RuntimeError("Cleanup failed")
            
            def __result__(self):
                return self.runs_done
        
        p = OnfinishErrorProcess()
        p.start()
        p.wait()
        
        with pytest.raises(OnFinishError) as exc_info:
            _ = p.result()
        
        reporter.add(f"  error type: {type(exc_info.value).__name__}")
        assert isinstance(exc_info.value.original_error, RuntimeError)
    
    def test_error_in_result(self, reporter):
        """Error in __result__ method."""
        
        class ResultErrorProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                pass
            
            def __result__(self):
                raise TypeError("Can't create result")
        
        p = ResultErrorProcess()
        p.start()
        p.wait()
        
        with pytest.raises(ResultError) as exc_info:
            _ = p.result()
        
        reporter.add(f"  error type: {type(exc_info.value).__name__}")
        assert isinstance(exc_info.value.original_error, TypeError)
    
    def test_error_with_all_lives_exhausted(self, reporter):
        """Process that always fails, exhausting all lives."""
        
        class AlwaysFailProcess(Process):
            def __init__(self):
                self.attempt = 0
                self.config.runs = 1
                self.config.lives = 3
            
            def __run__(self):
                self.attempt += 1
                raise Exception(f"Failing on attempt {self.attempt}")
        
        p = AlwaysFailProcess()
        p.start()
        p.wait()
        
        with pytest.raises(RunError) as exc_info:
            _ = p.result()
        
        # Should have exhausted all lives (3 attempts)
        reporter.add(f"  error on final attempt: {exc_info.value.original_error}")
        assert "attempt 3" in str(exc_info.value.original_error)
    
    def test_custom_error_handler(self, reporter):
        """Test __error__ method is called and can transform errors."""
        
        class CustomErrorProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                raise ValueError("Original error")
            
            def __error__(self):
                # __error__ should return an exception to be raised
                # or the original error (self.error) which is what default does
                return Exception(f"Transformed: {type(self.error).__name__}")
        
        p = CustomErrorProcess()
        p.start()
        p.wait()
        
        # __error__ returns a transformed exception
        with pytest.raises(Exception) as exc_info:
            _ = p.result()
        
        reporter.add(f"  transformed error: {exc_info.value}")
        assert "Transformed: RunError" in str(exc_info.value)


# =============================================================================
# Control Flow Edge Cases
# =============================================================================

class TestControlFlowEdgeCases:
    """Test unusual control flow scenarios."""
    
    def test_stop_before_start(self, reporter):
        """Call stop() before start()."""
        
        class StopBeforeStartProcess(Process):
            def __init__(self):
                self.config.runs = 100
            
            def __run__(self):
                sktime.sleep(0.1)
            
            def __result__(self):
                return "done"
        
        p = StopBeforeStartProcess()
        p.stop()  # Stop before start
        p.start()
        p.wait()
        
        result = p.result()
        reporter.add(f"  result after stop-before-start: {result}")
        
        # Stop event was set before start, so should exit quickly
        # Result might be None or "done" depending on timing
        assert result is None or result == "done"
    
    def test_multiple_stop_calls(self, reporter):
        """Call stop() multiple times."""
        
        class MultiStopProcess(Process):
            def __init__(self):
                self.runs = 0
            
            def __run__(self):
                self.runs += 1
                sktime.sleep(0.05)
            
            def __result__(self):
                return self.runs
        
        p = MultiStopProcess()
        p.start()
        sktime.sleep(0.1)
        
        # Call stop multiple times
        p.stop()
        p.stop()
        p.stop()
        
        p.wait()
        result = p.result()
        
        reporter.add(f"  runs before multi-stop: {result}")
        assert isinstance(result, int)
    
    def test_kill_immediately(self, reporter):
        """Kill process immediately after start."""
        
        class KillImmediateProcess(Process):
            def __run__(self):
                sktime.sleep(10)  # Long sleep
            
            def __result__(self):
                return "should not reach"
        
        p = KillImmediateProcess()
        p.start()
        
        # Give the subprocess a moment to actually spawn
        sktime.sleep(0.05)
        
        p.kill()  # Kill after subprocess exists
        
        # Result should be None (abandoned)
        result = p.result()
        reporter.add(f"  result after immediate kill: {result}")
        assert result is None
    
    def test_wait_without_start(self, reporter):
        """Call wait() without start()."""
        
        class NoStartProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __result__(self):
                return "never"
        
        p = NoStartProcess()
        p.wait()  # Should not block - no process to wait for
        
        result = p.result()
        reporter.add(f"  result without start: {result}")
        assert result is None
    
    def test_result_called_twice(self, reporter):
        """Access result property multiple times."""
        
        class DoubleResultProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __result__(self):
                return {"value": 42}
        
        p = DoubleResultProcess()
        p.start()
        p.wait()
        
        r1 = p.result()
        r2 = p.result()
        r3 = p.result()
        
        reporter.add(f"  r1: {r1}")
        reporter.add(f"  r2: {r2}")
        reporter.add(f"  same object: {r1 is r2}")
        
        # Should return same cached result
        assert r1 == r2 == r3
        assert r1 is r2  # Same object (cached)


# =============================================================================
# Lifecycle Method Interaction Edge Cases
# =============================================================================

class TestLifecycleInteractions:
    """Test interactions between lifecycle methods."""
    
    def test_prerun_modifies_state_for_run(self, reporter):
        """__prerun__ sets up state that __run__ uses."""
        
        class SetupProcess(Process):
            def __init__(self):
                self.config.runs = 3
                self.multiplier = 1
                self.results = []
            
            def __prerun__(self):
                self.multiplier = self._current_run + 1
            
            def __run__(self):
                self.results.append(10 * self.multiplier)
            
            def __result__(self):
                return self.results
        
        p = SetupProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  results: {result}")
        assert result == [10, 20, 30]
    
    def test_postrun_validates_run_result(self, reporter):
        """__postrun__ validates what __run__ did."""
        
        class ValidatingProcess(Process):
            def __init__(self):
                self.config.runs = 5
                self.last_value = 0
                self.validation_count = 0
            
            def __run__(self):
                self.last_value = self._current_run * 2
            
            def __postrun__(self):
                if self.last_value != self._current_run * 2:
                    raise ValueError("Validation failed")
                self.validation_count += 1
            
            def __result__(self):
                return {"validations": self.validation_count}
        
        p = ValidatingProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  validations passed: {result['validations']}")
        assert result['validations'] == 5
    
    def test_onfinish_aggregates_run_data(self, reporter):
        """__onfinish__ aggregates data from all runs."""
        
        class AggregatingProcess(Process):
            def __init__(self):
                self.config.runs = 5
                self.values = []
                self.summary = None
            
            def __run__(self):
                self.values.append(self._current_run ** 2)
            
            def __onfinish__(self):
                self.summary = {
                    "count": len(self.values),
                    "sum": sum(self.values),
                    "values": self.values,
                }
            
            def __result__(self):
                return self.summary
        
        p = AggregatingProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  summary: {result}")
        assert result['count'] == 5
        assert result['sum'] == 0 + 1 + 4 + 9 + 16  # 30
        assert result['values'] == [0, 1, 4, 9, 16]


# =============================================================================
# Concurrency Edge Cases
# =============================================================================

class TestConcurrencyEdgeCases:
    """Test concurrent process edge cases."""
    
    def test_many_processes_same_class(self, reporter):
        """Many instances of the same Process class."""
        
        class CounterProcess(Process):
            def __init__(self, process_id):
                self.process_id = process_id
                self.config.runs = 1
            
            def __result__(self):
                return self.process_id
        
        NUM_PROCESSES = 20
        
        processes = [CounterProcess(i) for i in range(NUM_PROCESSES)]
        
        for p in processes:
            p.start()
        
        for p in processes:
            p.wait()
        
        results = [p.result() for p in processes]
        
        reporter.add(f"  {NUM_PROCESSES} processes completed")
        reporter.add(f"  unique results: {len(set(results))}")
        
        assert results == list(range(NUM_PROCESSES))
    
    def test_processes_with_different_durations(self, reporter):
        """Processes with varying execution times."""
        
        class VariableDurationProcess(Process):
            def __init__(self, duration):
                self.duration = duration
                self.config.runs = 1
            
            def __run__(self):
                sktime.sleep(self.duration)
            
            def __result__(self):
                return self.duration
        
        durations = [0.05, 0.02, 0.08, 0.01, 0.04]
        processes = [VariableDurationProcess(d) for d in durations]
        
        start = sktime.time()
        for p in processes:
            p.start()
        for p in processes:
            p.wait()
        elapsed = sktime.elapsed(start)
        
        results = [p.result() for p in processes]
        
        # Sequential time = if we ran all processes one after another
        # Each process has ~100ms overhead + work time
        sequential_estimate = len(durations) * 0.1 + sum(durations)
        
        reporter.add(f"  durations: {durations}")
        reporter.add(f"  total elapsed: {elapsed:.3f}s")
        reporter.add(f"  sequential estimate: {sequential_estimate:.3f}s")
        
        # All results should match
        assert results == durations
        
        # Parallel execution: should be much faster than sequential
        # (spawn overhead is shared, not multiplied)
        assert elapsed < sequential_estimate


# =============================================================================
# Circuit Integration Example (User-level, not baked in)
# =============================================================================

class TestCircuitComposition:
    """Test using Circuit inside a Process (composable pattern)."""
    
    def test_circuit_within_run(self, reporter):
        """Use Circuit for failure tracking within __run__."""
        from suitkaise.circuit import Circuit
        
        class CircuitProtectedProcess(Process):
            def __init__(self):
                self.config.runs = 20
                self.circuit = Circuit(num_shorts_to_trip=3)
                self.successful_ops = 0
                self.failed_ops = 0
            
            def __run__(self):
                # Simulate occasional failures
                if self._current_run % 4 == 0:
                    self.circuit.short()
                    self.failed_ops += 1
                else:
                    self.successful_ops += 1
                
                # Check if circuit broken - stop early
                if self.circuit.broken:
                    self._stop_event.set()
            
            def __result__(self):
                return {
                    "successful": self.successful_ops,
                    "failed": self.failed_ops,
                    "circuit_broken": self.circuit.broken,
                }
        
        p = CircuitProtectedProcess()
        p.start()
        p.wait()
        result = p.result()
        
        reporter.add(f"  successful ops: {result['successful']}")
        reporter.add(f"  failed ops: {result['failed']}")
        reporter.add(f"  circuit broken: {result['circuit_broken']}")
        
        # Circuit should break after 3 shorts (at runs 0, 4, 8)
        assert result['circuit_broken'] is True
        assert result['failed'] == 3


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
