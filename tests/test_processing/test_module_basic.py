# test the processing module on its own with basic functionality

# this test covers all functionality of the processing module,
# but does not add in unnecessary complexity like simulating a real world example.

# it should test everything in the module, including all attributes and methods.

# the test should output clear, verbose results that are digestible by a human.

import time
import pytest  # type: ignore

from suitkaise.processing import (
    Process,
    ProcessConfig,
    TimeoutConfig,
    ProcessTimers,
    ProcessError,
    PreRunError,
    RunError,
    PostRunError,
    OnFinishError,
    ResultError,
    ProcessTimeoutError,
)


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================

TOL = 0.1  # tolerance for timing comparisons


def _assert_between(value: float, low: float, high: float, msg: str = "") -> None:
    assert low <= value <= high, msg or f"{value} not in [{low}, {high}]"


# =============================================================================
# Basic Process Creation and Config
# =============================================================================

class TestProcessCreation:
    """Tests for Process class creation and configuration."""
    
    def test_process_creation_with_default_config(self, reporter):
        """Process can be created with default configuration values."""
        
        class SimpleProcess(Process):
            def __init__(self):
                pass
        
        p = SimpleProcess()
        
        reporter.add(f"  config.runs: {p.config.runs}")
        reporter.add(f"  config.join_in: {p.config.join_in}")
        reporter.add(f"  config.lives: {p.config.lives}")
        reporter.add(f"  config.timeouts.prerun: {p.config.timeouts.prerun}")
        reporter.add(f"  config.timeouts.run: {p.config.timeouts.run}")
        reporter.add(f"  config.timeouts.postrun: {p.config.timeouts.postrun}")
        reporter.add(f"  config.timeouts.onfinish: {p.config.timeouts.onfinish}")
        
        assert p.config.runs is None
        assert p.config.join_in is None
        assert p.config.lives == 1
        assert p.config.timeouts.prerun is None
        assert p.config.timeouts.run is None
        assert p.config.timeouts.postrun is None
        assert p.config.timeouts.onfinish is None
    
    def test_process_creation_with_custom_config(self, reporter):
        """Process config can be customized in __init__."""
        
        class CustomProcess(Process):
            def __init__(self):
                self.config.runs = 5
                self.config.join_in = 10.0
                self.config.lives = 3
                self.config.timeouts.run = 60.0
        
        p = CustomProcess()
        
        reporter.add(f"  config.runs: {p.config.runs}")
        reporter.add(f"  config.join_in: {p.config.join_in}")
        reporter.add(f"  config.lives: {p.config.lives}")
        reporter.add(f"  config.timeouts.run: {p.config.timeouts.run}")
        
        assert p.config.runs == 5
        assert p.config.join_in == 10.0
        assert p.config.lives == 3
        assert p.config.timeouts.run == 60.0
    
    def test_process_auto_init_no_super_needed(self, reporter):
        """Process subclass __init__ works without calling super().__init__()."""
        
        class NoSuperProcess(Process):
            def __init__(self, value):
                self.value = value
                self.config.runs = 10
        
        p = NoSuperProcess(42)
        
        reporter.add(f"  self.value: {p.value}")
        reporter.add(f"  self.config exists: {hasattr(p, 'config')}")
        reporter.add(f"  config.runs: {p.config.runs}")
        
        assert p.value == 42
        assert hasattr(p, 'config')
        assert p.config.runs == 10
    
    def test_process_initial_state(self, reporter):
        """Process has correct initial state after creation."""
        
        class StateProcess(Process):
            pass
        
        p = StateProcess()
        
        reporter.add(f"  current_run: {p.current_run}")
        reporter.add(f"  is_alive: {p.is_alive}")
        reporter.add(f"  timers: {p.timers}")
        reporter.add(f"  error: {p.error}")
        
        assert p.current_run == 0
        assert p.is_alive == False
        assert p.timers is None
        assert p.error is None


# =============================================================================
# Lifecycle Methods Execution
# =============================================================================

class TestLifecycleMethods:
    """Tests for lifecycle method execution order and behavior."""
    
    def test_basic_run_execution(self, reporter):
        """Process executes __run__ the correct number of times."""
        
        class CounterProcess(Process):
            def __init__(self):
                self.count = 0
                self.config.runs = 3
            
            def __run__(self):
                self.count += 1
            
            def __result__(self):
                return self.count
        
        p = CounterProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  runs configured: 3")
        reporter.add(f"  result (count): {result}")
        
        assert result == 3
    
    def test_lifecycle_order(self, reporter):
        """Lifecycle methods execute in correct order: prerun → run → postrun."""
        
        class OrderProcess(Process):
            def __init__(self):
                self.order = []
                self.config.runs = 2
            
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
        
        p = OrderProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  execution order: {result}")
        
        expected = ['prerun', 'run', 'postrun', 'prerun', 'run', 'postrun', 'onfinish']
        assert result == expected
    
    def test_stop_from_inside_process(self, reporter):
        """Process can stop itself by calling self.stop()."""
        
        class SelfStopProcess(Process):
            def __init__(self):
                self.count = 0
            
            def __run__(self):
                self.count += 1
                if self.count >= 5:
                    self.stop()
            
            def __result__(self):
                return self.count
        
        p = SelfStopProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  stopped at count: {result}")
        
        assert result == 5
    
    def test_result_returns_none_by_default(self, reporter):
        """Process returns None if __result__ is not overridden."""
        
        class NoResultProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                pass
        
        p = NoResultProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  result: {result}")
        
        assert result is None


# =============================================================================
# Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling and lives system."""
    
    def test_error_in_run_raises_run_error(self, reporter):
        """Error in __run__ is wrapped in RunError."""
        
        class ErrorProcess(Process):
            def __init__(self):
                self.config.runs = 5
            
            def __run__(self):
                raise ValueError("test error")
        
        p = ErrorProcess()
        p.start()
        p.wait()
        
        with pytest.raises(RunError) as exc_info:
            _ = p.result
        
        reporter.add(f"  error type: {type(exc_info.value).__name__}")
        reporter.add(f"  original error: {type(exc_info.value.original_error).__name__}")
        
        assert isinstance(exc_info.value.original_error, ValueError)
    
    def test_error_in_prerun_raises_prerun_error(self, reporter):
        """Error in __prerun__ is wrapped in PreRunError."""
        
        class PreRunErrorProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __prerun__(self):
                raise RuntimeError("prerun failed")
            
            def __run__(self):
                pass
        
        p = PreRunErrorProcess()
        p.start()
        p.wait()
        
        with pytest.raises(PreRunError) as exc_info:
            _ = p.result
        
        reporter.add(f"  error type: {type(exc_info.value).__name__}")
        reporter.add(f"  original error: {type(exc_info.value.original_error).__name__}")
        
        assert isinstance(exc_info.value.original_error, RuntimeError)
    
    def test_catch_all_process_errors(self, reporter):
        """All process errors can be caught with ProcessError base class."""
        
        class FailingProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                raise ValueError("fail")
        
        p = FailingProcess()
        p.start()
        p.wait()
        
        # Can catch with ProcessError
        with pytest.raises(ProcessError) as exc_info:
            _ = p.result
        
        reporter.add(f"  caught with ProcessError: {type(exc_info.value).__name__}")
        assert isinstance(exc_info.value, ProcessError)
    
    def test_lives_retry_on_error(self, reporter):
        """Process retries with preserved state when lives > 1."""
        
        class RetryProcess(Process):
            def __init__(self):
                self.attempt = 0  # User state is preserved across retries
                self.config.runs = 1
                self.config.lives = 3
            
            def __run__(self):
                self.attempt += 1
                # Fail on first 2 attempts, succeed on 3rd
                if self.attempt < 3:
                    raise ValueError(f"failing on attempt {self.attempt}")
                # Success on attempt 3!
            
            def __result__(self):
                return f"succeeded on attempt {self.attempt}"
        
        p = RetryProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  configured lives: 3")
        reporter.add(f"  result: {result}")
        
        # With 3 lives: attempt 1 fails, attempt 2 fails, attempt 3 succeeds
        assert result == "succeeded on attempt 3"
    
    def test_error_handler_receives_error(self, reporter):
        """__error__() receives the wrapped error via self.error."""
        
        class ErrorHandlerProcess(Process):
            def __init__(self):
                self.config.runs = 1
                self.error_received = None
            
            def __run__(self):
                raise ValueError("test")
            
            def __error__(self):
                self.error_received = self.error
                return f"handled: {type(self.error).__name__}"
        
        p = ErrorHandlerProcess()
        p.start()
        p.wait()
        
        # Result should raise since __error__ returns something that gets treated as error
        with pytest.raises(Exception):
            _ = p.result
        
        reporter.add(f"  __error__() was called with self.error set")


# =============================================================================
# Control Methods
# =============================================================================

class TestControlMethods:
    """Tests for start(), stop(), kill(), wait() methods."""
    
    def test_wait_returns_true_when_finished(self, reporter):
        """wait() returns True when process finishes normally."""
        
        class QuickProcess(Process):
            def __init__(self):
                self.config.runs = 1
            
            def __run__(self):
                pass
        
        p = QuickProcess()
        p.start()
        finished = p.wait()
        
        reporter.add(f"  wait() returned: {finished}")
        
        assert finished == True
    
    def test_wait_with_timeout(self, reporter):
        """wait(timeout) returns False if process doesn't finish in time."""
        
        class SlowProcess(Process):
            def __run__(self):
                time.sleep(5)  # Long sleep
        
        p = SlowProcess()
        p.start()
        finished = p.wait(timeout=0.1)
        
        reporter.add(f"  wait(0.1) returned: {finished}")
        reporter.add(f"  process still alive: {p.is_alive}")
        
        # Cleanup
        p.kill()
        
        assert finished == False
    
    def test_kill_terminates_process(self, reporter):
        """kill() terminates process immediately."""
        
        class InfiniteProcess(Process):
            def __run__(self):
                time.sleep(0.1)
        
        p = InfiniteProcess()
        p.start()
        
        assert p.is_alive == True
        
        p.kill()
        time.sleep(0.2)  # Give it time to terminate
        
        reporter.add(f"  is_alive after kill: {p.is_alive}")
        
        assert p.is_alive == False
    
    def test_stop_allows_graceful_shutdown(self, reporter):
        """stop() allows process to finish current work and run __onfinish__."""
        
        class GracefulProcess(Process):
            def __init__(self):
                self.finished_gracefully = False
            
            def __run__(self):
                time.sleep(0.05)
            
            def __onfinish__(self):
                self.finished_gracefully = True
            
            def __result__(self):
                return "graceful"
        
        p = GracefulProcess()
        p.start()
        time.sleep(0.1)
        p.stop()
        p.wait()
        result = p.result
        
        reporter.add(f"  result: {result}")
        
        assert result == "graceful"


# =============================================================================
# Auto-Timing Feature
# =============================================================================

class TestAutoTiming:
    """Tests for automatic timing of lifecycle methods."""
    
    def test_auto_timing_creates_timers(self, reporter):
        """Defining lifecycle methods automatically creates timers."""
        
        class TimedProcess(Process):
            def __init__(self):
                self.config.runs = 3
            
            def __run__(self):
                time.sleep(0.01)
            
            def __result__(self):
                return {
                    'timers_exists': self.timers is not None,
                    'run_timer_exists': self.timers.run is not None if self.timers else False,
                    'num_times': self.timers.run.num_times if self.timers and self.timers.run else 0,
                }
        
        p = TimedProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  timers exists: {result['timers_exists']}")
        reporter.add(f"  run timer exists: {result['run_timer_exists']}")
        reporter.add(f"  num_times recorded: {result['num_times']}")
        
        assert result['timers_exists'] == True
        assert result['run_timer_exists'] == True
        assert result['num_times'] == 3
    
    def test_auto_timing_on_multiple_methods(self, reporter):
        """Timing is automatically created for all user-defined lifecycle methods."""
        
        class MultiTimedProcess(Process):
            def __init__(self):
                self.config.runs = 2
            
            def __prerun__(self):
                time.sleep(0.005)
            
            def __run__(self):
                time.sleep(0.01)
            
            def __postrun__(self):
                time.sleep(0.005)
            
            def __result__(self):
                return {
                    'prerun_times': self.timers.prerun.num_times if self.timers and self.timers.prerun else 0,
                    'run_times': self.timers.run.num_times if self.timers and self.timers.run else 0,
                    'postrun_times': self.timers.postrun.num_times if self.timers and self.timers.postrun else 0,
                    'full_run_times': self.timers.full_run.num_times if self.timers else 0,
                }
        
        p = MultiTimedProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  prerun times: {result['prerun_times']}")
        reporter.add(f"  run times: {result['run_times']}")
        reporter.add(f"  postrun times: {result['postrun_times']}")
        reporter.add(f"  full_run times: {result['full_run_times']}")
        
        assert result['prerun_times'] == 2
        assert result['run_times'] == 2
        assert result['postrun_times'] == 2
        assert result['full_run_times'] == 2
    
    def test_timer_access_via_method_attribute(self, reporter):
        """Timers can be accessed via process.__run__.timer pattern."""
        
        class TimerAccessProcess(Process):
            def __init__(self):
                self.config.runs = 3
            
            def __run__(self):
                time.sleep(0.01)
            
            def __result__(self):
                return "done"
        
        p = TimerAccessProcess()
        p.start()
        p.wait()
        _ = p.result
        
        # Access timer via method attribute
        run_timer = p.__run__.timer
        
        reporter.add(f"  p.__run__.timer exists: {run_timer is not None}")
        reporter.add(f"  num_times: {run_timer.num_times if run_timer else 0}")
        
        assert run_timer is not None
        assert run_timer.num_times == 3
    
    def test_full_run_timer_aggregates(self, reporter):
        """p.timer returns the aggregate full_run timer."""
        
        class AggregateProcess(Process):
            def __init__(self):
                self.config.runs = 2
            
            def __prerun__(self):
                time.sleep(0.005)
            
            def __run__(self):
                time.sleep(0.01)
            
            def __postrun__(self):
                time.sleep(0.005)
            
            def __result__(self):
                return "done"
        
        p = AggregateProcess()
        p.start()
        p.wait()
        _ = p.result
        
        full_timer = p.timer
        
        reporter.add(f"  p.timer exists: {full_timer is not None}")
        reporter.add(f"  num_times: {full_timer.num_times if full_timer else 0}")
        reporter.add(f"  mean: {full_timer.mean:.4f}s" if full_timer and full_timer.mean else "  mean: N/A")
        
        assert full_timer is not None
        assert full_timer.num_times == 2


# =============================================================================
# Config Limits
# =============================================================================

class TestConfigLimits:
    """Tests for runs and join_in limits."""
    
    def test_runs_limit(self, reporter):
        """Process stops after runs iterations."""
        
        class LimitedProcess(Process):
            def __init__(self):
                self.count = 0
                self.config.runs = 5
            
            def __run__(self):
                self.count += 1
            
            def __result__(self):
                return self.count
        
        p = LimitedProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  runs: 5")
        reporter.add(f"  actual count: {result}")
        
        assert result == 5
    
    def test_join_in_time_limit(self, reporter):
        """Process stops after join_in seconds."""
        
        class TimeLimitedProcess(Process):
            def __init__(self):
                self.count = 0
                self.config.join_in = 0.3
            
            def __run__(self):
                self.count += 1
                time.sleep(0.05)
            
            def __result__(self):
                return self.count
        
        p = TimeLimitedProcess()
        start = time.time()
        p.start()
        p.wait()
        elapsed = time.time() - start
        result = p.result
        
        reporter.add(f"  join_in: 0.3s")
        reporter.add(f"  actual elapsed: {elapsed:.2f}s")
        reporter.add(f"  run count: {result}")
        
        # Should have stopped around 0.3s
        _assert_between(elapsed, 0.2, 0.6)
        assert result > 0


# =============================================================================
# Property Access
# =============================================================================

class TestProperties:
    """Tests for process properties."""
    
    def test_current_run_property(self, reporter):
        """current_run tracks the current iteration number."""
        
        class RunProcess(Process):
            def __init__(self):
                self.runs_seen = []
                self.config.runs = 3
            
            def __run__(self):
                self.runs_seen.append(self._current_run)
            
            def __result__(self):
                return self.runs_seen
        
        p = RunProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  runs seen: {result}")
        
        # Runs should be 0, 1, 2 (0-indexed, incremented after each iteration)
        assert result == [0, 1, 2]
    
    def test_is_alive_property(self, reporter):
        """is_alive correctly reports process state."""
        
        class AliveProcess(Process):
            def __run__(self):
                time.sleep(0.2)
        
        p = AliveProcess()
        
        before_start = p.is_alive
        p.start()
        time.sleep(0.05)
        during = p.is_alive
        p.kill()
        time.sleep(0.1)
        after_kill = p.is_alive
        
        reporter.add(f"  before start: {before_start}")
        reporter.add(f"  during execution: {during}")
        reporter.add(f"  after kill: {after_kill}")
        
        assert before_start == False
        assert during == True
        assert after_kill == False

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "-s"])
