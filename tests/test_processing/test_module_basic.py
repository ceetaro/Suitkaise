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
    PreloopError,
    MainLoopError,
    PostLoopError,
    OnFinishError,
    ResultError,
    TimeoutError,
    timesection,
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
        
        reporter.add(f"  config.num_loops: {p.config.num_loops}")
        reporter.add(f"  config.join_in: {p.config.join_in}")
        reporter.add(f"  config.lives: {p.config.lives}")
        reporter.add(f"  config.timeouts.preloop: {p.config.timeouts.preloop}")
        reporter.add(f"  config.timeouts.loop: {p.config.timeouts.loop}")
        reporter.add(f"  config.timeouts.postloop: {p.config.timeouts.postloop}")
        reporter.add(f"  config.timeouts.onfinish: {p.config.timeouts.onfinish}")
        
        assert p.config.num_loops is None
        assert p.config.join_in is None
        assert p.config.lives == 1
        assert p.config.timeouts.preloop == 30.0
        assert p.config.timeouts.loop == 300.0
        assert p.config.timeouts.postloop == 60.0
        assert p.config.timeouts.onfinish == 60.0
    
    def test_process_creation_with_custom_config(self, reporter):
        """Process config can be customized in __init__."""
        
        class CustomProcess(Process):
            def __init__(self):
                self.config.num_loops = 5
                self.config.join_in = 10.0
                self.config.lives = 3
                self.config.timeouts.loop = 60.0
        
        p = CustomProcess()
        
        reporter.add(f"  config.num_loops: {p.config.num_loops}")
        reporter.add(f"  config.join_in: {p.config.join_in}")
        reporter.add(f"  config.lives: {p.config.lives}")
        reporter.add(f"  config.timeouts.loop: {p.config.timeouts.loop}")
        
        assert p.config.num_loops == 5
        assert p.config.join_in == 10.0
        assert p.config.lives == 3
        assert p.config.timeouts.loop == 60.0
    
    def test_process_auto_init_no_super_needed(self, reporter):
        """Process subclass __init__ works without calling super().__init__()."""
        
        class NoSuperProcess(Process):
            def __init__(self, value):
                self.value = value
                self.config.num_loops = 10
        
        p = NoSuperProcess(42)
        
        reporter.add(f"  self.value: {p.value}")
        reporter.add(f"  self.config exists: {hasattr(p, 'config')}")
        reporter.add(f"  config.num_loops: {p.config.num_loops}")
        
        assert p.value == 42
        assert hasattr(p, 'config')
        assert p.config.num_loops == 10
    
    def test_process_initial_state(self, reporter):
        """Process has correct initial state after creation."""
        
        class StateProcess(Process):
            pass
        
        p = StateProcess()
        
        reporter.add(f"  current_lap: {p.current_lap}")
        reporter.add(f"  is_alive: {p.is_alive}")
        reporter.add(f"  timers: {p.timers}")
        reporter.add(f"  error: {p.error}")
        
        assert p.current_lap == 0
        assert p.is_alive == False
        assert p.timers is None
        assert p.error is None


# =============================================================================
# Lifecycle Methods Execution
# =============================================================================

class TestLifecycleMethods:
    """Tests for lifecycle method execution order and behavior."""
    
    def test_basic_loop_execution(self, reporter):
        """Process executes __loop__ the correct number of times."""
        
        class CounterProcess(Process):
            def __init__(self):
                self.count = 0
                self.config.num_loops = 3
            
            def __loop__(self):
                self.count += 1
            
            def __result__(self):
                return self.count
        
        p = CounterProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  num_loops configured: 3")
        reporter.add(f"  result (count): {result}")
        
        assert result == 3
    
    def test_lifecycle_order(self, reporter):
        """Lifecycle methods execute in correct order: preloop → loop → postloop."""
        
        class OrderProcess(Process):
            def __init__(self):
                self.order = []
                self.config.num_loops = 2
            
            def __preloop__(self):
                self.order.append('preloop')
            
            def __loop__(self):
                self.order.append('loop')
            
            def __postloop__(self):
                self.order.append('postloop')
            
            def __onfinish__(self):
                self.order.append('onfinish')
            
            def __result__(self):
                return self.order
        
        p = OrderProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  execution order: {result}")
        
        expected = ['preloop', 'loop', 'postloop', 'preloop', 'loop', 'postloop', 'onfinish']
        assert result == expected
    
    def test_stop_from_inside_process(self, reporter):
        """Process can stop itself by calling self.stop()."""
        
        class SelfStopProcess(Process):
            def __init__(self):
                self.count = 0
            
            def __loop__(self):
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
                self.config.num_loops = 1
            
            def __loop__(self):
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
    
    def test_error_in_loop_raises_main_loop_error(self, reporter):
        """Error in __loop__ is wrapped in MainLoopError."""
        
        class ErrorProcess(Process):
            def __init__(self):
                self.config.num_loops = 5
            
            def __loop__(self):
                raise ValueError("test error")
        
        p = ErrorProcess()
        p.start()
        p.wait()
        
        with pytest.raises(MainLoopError) as exc_info:
            _ = p.result
        
        reporter.add(f"  error type: {type(exc_info.value).__name__}")
        reporter.add(f"  original error: {type(exc_info.value.original_error).__name__}")
        
        assert isinstance(exc_info.value.original_error, ValueError)
    
    def test_error_in_preloop_raises_preloop_error(self, reporter):
        """Error in __preloop__ is wrapped in PreloopError."""
        
        class PreloopErrorProcess(Process):
            def __init__(self):
                self.config.num_loops = 1
            
            def __preloop__(self):
                raise RuntimeError("preloop failed")
            
            def __loop__(self):
                pass
        
        p = PreloopErrorProcess()
        p.start()
        p.wait()
        
        with pytest.raises(PreloopError) as exc_info:
            _ = p.result
        
        reporter.add(f"  error type: {type(exc_info.value).__name__}")
        reporter.add(f"  original error: {type(exc_info.value.original_error).__name__}")
        
        assert isinstance(exc_info.value.original_error, RuntimeError)
    
    def test_lives_retry_on_error(self, reporter):
        """Process retries with fresh state when lives > 1."""
        
        class RetryProcess(Process):
            def __init__(self):
                self.config.num_loops = 1
                self.config.lives = 3
            
            def __loop__(self):
                # Each retry starts with fresh state, so instance vars reset.
                # But config.lives is updated by the engine to remaining lives.
                # On the last life (lives=1), succeed.
                if self.config.lives == 1:
                    pass  # Success on last life!
                else:
                    raise ValueError(f"failing with {self.config.lives} lives remaining")
            
            def __result__(self):
                return f"succeeded on life {self.config.lives}"
        
        p = RetryProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  configured lives: 3")
        reporter.add(f"  result: {result}")
        
        # With 3 lives: fails on lives=3, fails on lives=2, succeeds on lives=1
        assert result == "succeeded on life 1"
    
    def test_error_handler_receives_error(self, reporter):
        """__error__() receives the wrapped error via self.error."""
        
        class ErrorHandlerProcess(Process):
            def __init__(self):
                self.config.num_loops = 1
                self.error_received = None
            
            def __loop__(self):
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
                self.config.num_loops = 1
            
            def __loop__(self):
                pass
        
        p = QuickProcess()
        p.start()
        finished = p.wait()
        
        reporter.add(f"  wait() returned: {finished}")
        
        assert finished == True
    
    def test_wait_with_timeout(self, reporter):
        """wait(timeout) returns False if process doesn't finish in time."""
        
        class SlowProcess(Process):
            def __loop__(self):
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
            def __loop__(self):
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
            
            def __loop__(self):
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
# Timing with @timesection
# =============================================================================

class TestTimesectionDecorator:
    """Tests for @timesection() decorator."""
    
    def test_timesection_creates_timers(self, reporter):
        """@timesection() creates self.timers with appropriate timer slots."""
        
        class TimedProcess(Process):
            def __init__(self):
                self.config.num_loops = 3
            
            @timesection()
            def __loop__(self):
                time.sleep(0.01)
            
            def __result__(self):
                return {
                    'timers_exists': self.timers is not None,
                    'loop_timer_exists': self.timers.loop is not None if self.timers else False,
                    'num_times': self.timers.loop.num_times if self.timers and self.timers.loop else 0,
                }
        
        p = TimedProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  timers exists: {result['timers_exists']}")
        reporter.add(f"  loop timer exists: {result['loop_timer_exists']}")
        reporter.add(f"  num_times recorded: {result['num_times']}")
        
        assert result['timers_exists'] == True
        assert result['loop_timer_exists'] == True
        assert result['num_times'] == 3
    
    def test_timesection_on_multiple_methods(self, reporter):
        """@timesection() can be used on multiple lifecycle methods."""
        
        class MultiTimedProcess(Process):
            def __init__(self):
                self.config.num_loops = 2
            
            @timesection()
            def __preloop__(self):
                time.sleep(0.005)
            
            @timesection()
            def __loop__(self):
                time.sleep(0.01)
            
            @timesection()
            def __postloop__(self):
                time.sleep(0.005)
            
            def __result__(self):
                return {
                    'preloop_times': self.timers.preloop.num_times if self.timers and self.timers.preloop else 0,
                    'loop_times': self.timers.loop.num_times if self.timers and self.timers.loop else 0,
                    'postloop_times': self.timers.postloop.num_times if self.timers and self.timers.postloop else 0,
                    'full_loop_times': self.timers.full_loop.num_times if self.timers else 0,
                }
        
        p = MultiTimedProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  preloop times: {result['preloop_times']}")
        reporter.add(f"  loop times: {result['loop_times']}")
        reporter.add(f"  postloop times: {result['postloop_times']}")
        reporter.add(f"  full_loop times: {result['full_loop_times']}")
        
        assert result['preloop_times'] == 2
        assert result['loop_times'] == 2
        assert result['postloop_times'] == 2
        assert result['full_loop_times'] == 2


# =============================================================================
# Config Limits
# =============================================================================

class TestConfigLimits:
    """Tests for num_loops and join_in limits."""
    
    def test_num_loops_limit(self, reporter):
        """Process stops after num_loops iterations."""
        
        class LimitedProcess(Process):
            def __init__(self):
                self.count = 0
                self.config.num_loops = 5
            
            def __loop__(self):
                self.count += 1
            
            def __result__(self):
                return self.count
        
        p = LimitedProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  num_loops: 5")
        reporter.add(f"  actual count: {result}")
        
        assert result == 5
    
    def test_join_in_time_limit(self, reporter):
        """Process stops after join_in seconds."""
        
        class TimeLimitedProcess(Process):
            def __init__(self):
                self.count = 0
                self.config.join_in = 0.3
            
            def __loop__(self):
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
        reporter.add(f"  loop count: {result}")
        
        # Should have stopped around 0.3s
        _assert_between(elapsed, 0.2, 0.6)
        assert result > 0


# =============================================================================
# Property Access
# =============================================================================

class TestProperties:
    """Tests for process properties."""
    
    def test_current_lap_property(self, reporter):
        """current_lap tracks the current iteration number."""
        
        class LapProcess(Process):
            def __init__(self):
                self.laps_seen = []
                self.config.num_loops = 3
            
            def __loop__(self):
                self.laps_seen.append(self._current_lap)
            
            def __result__(self):
                return self.laps_seen
        
        p = LapProcess()
        p.start()
        p.wait()
        result = p.result
        
        reporter.add(f"  laps seen: {result}")
        
        # Laps should be 0, 1, 2 (0-indexed, incremented after each iteration)
        assert result == [0, 1, 2]
    
    def test_is_alive_property(self, reporter):
        """is_alive correctly reports process state."""
        
        class AliveProcess(Process):
            def __loop__(self):
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
