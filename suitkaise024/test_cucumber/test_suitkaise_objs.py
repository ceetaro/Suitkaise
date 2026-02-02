# test that cucumber can serialize/deserialize suitkaise objects correctly
# WITHOUT custom __serialize__ and __deserialize__ methods

import pytest
import time
from pathlib import Path


# =============================================================================
# sktime Tests
# =============================================================================

class TestTimerSerialization:
    """Test Timer serialization and deserialization."""
    
    def test_timer_basic_roundtrip(self):
        """Timer serializes and deserializes with times preserved."""
        from suitkaise import cucumber
        from suitkaise.sktime import Timer
        
        timer = Timer()
        timer.add_time(1.5)
        timer.add_time(2.0)
        timer.add_time(0.5)
        
        # Full cucumber roundtrip
        serialized = cucumber.serialize(timer)
        restored = cucumber.deserialize(serialized)
        
        # Verify state
        assert restored.num_times == 3
        assert restored.get_time(0) == 1.5
        assert restored.get_time(1) == 2.0
        assert restored.get_time(2) == 0.5
        assert restored.mean == pytest.approx(4.0 / 3, rel=1e-6)
        assert restored.total_time == pytest.approx(4.0, rel=1e-6)
    
    def test_timer_empty_roundtrip(self):
        """Empty timer serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.sktime import Timer
        
        timer = Timer()
        
        serialized = cucumber.serialize(timer)
        restored = cucumber.deserialize(serialized)
        
        assert restored.num_times == 0
        assert restored.most_recent is None
        assert restored.mean is None
    
    def test_timer_with_original_start_time(self):
        """Timer preserves original_start_time across serialization."""
        from suitkaise import cucumber
        from suitkaise.sktime import Timer
        
        timer = Timer()
        timer.start()
        original_start = timer.original_start_time
        timer.stop()
        
        serialized = cucumber.serialize(timer)
        restored = cucumber.deserialize(serialized)
        
        assert restored.original_start_time == original_start
        assert restored.num_times == 1
    
    def test_timer_still_functional_after_deserialize(self):
        """Deserialized timer can still record new times."""
        from suitkaise import cucumber
        from suitkaise.sktime import Timer
        
        timer = Timer()
        timer.add_time(1.0)
        
        serialized = cucumber.serialize(timer)
        restored = cucumber.deserialize(serialized)
        
        # Add more times to the restored timer
        restored.add_time(2.0)
        restored.start()
        time.sleep(0.01)
        elapsed = restored.stop()
        
        assert restored.num_times == 3
        assert elapsed > 0
        assert restored.get_time(1) == 2.0


class TestYawnSerialization:
    """Test Yawn serialization and deserialization."""
    
    def test_yawn_basic_roundtrip(self):
        """Yawn serializes and deserializes with state preserved."""
        from suitkaise import cucumber
        from suitkaise.sktime import Yawn
        
        yawn = Yawn(sleep_duration=2.0, yawn_threshold=5, log_sleep=True)
        
        # Increment yawn count
        yawn.yawn()  # count = 1
        yawn.yawn()  # count = 2
        
        serialized = cucumber.serialize(yawn)
        restored = cucumber.deserialize(serialized)
        
        assert restored.sleep_duration == 2.0
        assert restored.yawn_threshold == 5
        assert restored.log_sleep is True
        stats = restored.get_stats()
        assert stats['current_yawns'] == 2
        assert stats['total_sleeps'] == 0
    
    def test_yawn_still_functional_after_deserialize(self):
        """Deserialized Yawn can still trigger sleep."""
        from suitkaise import cucumber
        from suitkaise.sktime import Yawn
        
        yawn = Yawn(sleep_duration=0.01, yawn_threshold=3)
        yawn.yawn()  # count = 1
        yawn.yawn()  # count = 2
        
        serialized = cucumber.serialize(yawn)
        restored = cucumber.deserialize(serialized)
        
        # One more yawn should trigger sleep
        start = time.time()
        slept = restored.yawn()  # count = 3 -> sleep
        elapsed = time.time() - start
        
        assert slept is True
        assert elapsed >= 0.01
        
        # Counter should be reset
        stats = restored.get_stats()
        assert stats['current_yawns'] == 0
        assert stats['total_sleeps'] == 1


# =============================================================================
# skpath Tests
# =============================================================================

class TestSKPathSerialization:
    """Test SKPath serialization and deserialization."""
    
    def test_skpath_basic_roundtrip(self):
        """SKPath serializes and deserializes with paths preserved."""
        from suitkaise import cucumber
        from suitkaise.skpath import SKPath
        
        # Use a path that exists
        path = SKPath(__file__)
        
        serialized = cucumber.serialize(path)
        restored = cucumber.deserialize(serialized)
        
        assert restored.ap == path.ap
        assert restored.np == path.np
        assert restored.name == path.name
        assert restored.suffix == path.suffix
    
    def test_skpath_preserves_project_root(self):
        """SKPath preserves project root across serialization."""
        from suitkaise import cucumber
        from suitkaise.skpath import SKPath
        
        path = SKPath(__file__)
        original_root = path.root  # root is a str property
        
        serialized = cucumber.serialize(path)
        restored = cucumber.deserialize(serialized)
        
        if original_root is not None:
            assert restored.root is not None
            assert restored.root == original_root  # Compare strings directly
    
    def test_skpath_still_functional_after_deserialize(self):
        """Deserialized SKPath can still perform path operations."""
        from suitkaise import cucumber
        from suitkaise.skpath import SKPath
        
        path = SKPath(__file__)
        
        serialized = cucumber.serialize(path)
        restored = cucumber.deserialize(serialized)
        
        # Check that path operations still work
        assert restored.exists is True
        assert restored.is_file is True
        parent = restored.parent
        assert parent.is_dir is True


# =============================================================================
# circuit Tests
# =============================================================================

class TestCircuitSerialization:
    """Test Circuit serialization and deserialization."""
    
    def test_circuit_basic_roundtrip(self):
        """Circuit serializes and deserializes with state preserved."""
        from suitkaise import cucumber
        from suitkaise.circuit import Circuit
        
        circuit = Circuit(num_shorts_to_trip=5, sleep_time_after_trip=0.5)
        
        # Short a few times
        circuit.short()
        circuit.short()
        
        serialized = cucumber.serialize(circuit)
        restored = cucumber.deserialize(serialized)
        
        assert restored.num_shorts_to_trip == 5
        assert restored.sleep_time_after_trip == 0.5
        assert restored.broken is False  # not broken = flowing
        assert restored.times_shorted == 2
    
    def test_circuit_broken_state_roundtrip(self):
        """Broken circuit state is preserved across serialization."""
        from suitkaise import cucumber
        from suitkaise.circuit import Circuit
        
        circuit = Circuit(num_shorts_to_trip=2, sleep_time_after_trip=0)
        circuit.short()
        circuit.short()  # This should break the circuit
        
        serialized = cucumber.serialize(circuit)
        restored = cucumber.deserialize(serialized)
        
        assert restored.broken is True
        # times_shorted is reset to 0 when circuit breaks
        assert restored.times_shorted == 0
    
    def test_circuit_still_functional_after_deserialize(self):
        """Deserialized Circuit can still be used."""
        from suitkaise import cucumber
        from suitkaise.circuit import Circuit
        
        circuit = Circuit(num_shorts_to_trip=3, sleep_time_after_trip=0)
        circuit.short()
        
        serialized = cucumber.serialize(circuit)
        restored = cucumber.deserialize(serialized)
        
        # Continue using the circuit
        assert restored.broken is False  # not broken = flowing
        restored.short()
        restored.short()  # This should break
        
        assert restored.broken is True
        
        # Reset and use again
        restored.reset()
        assert restored.broken is False  # not broken = flowing
        assert restored.times_shorted == 0


# =============================================================================
# processing Tests
# =============================================================================

class TestTimeoutConfigSerialization:
    """Test TimeoutConfig serialization and deserialization."""
    
    def test_timeout_config_roundtrip(self):
        """TimeoutConfig serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.config import TimeoutConfig
        
        config = TimeoutConfig(
            preloop=10.0,
            loop=60.0,
            postloop=None,
            onfinish=30.0
        )
        
        serialized = cucumber.serialize(config)
        restored = cucumber.deserialize(serialized)
        
        assert restored.preloop == 10.0
        assert restored.loop == 60.0
        assert restored.postloop is None
        assert restored.onfinish == 30.0
    
    def test_timeout_config_default_values(self):
        """TimeoutConfig with default values serializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.config import TimeoutConfig
        
        config = TimeoutConfig()
        
        serialized = cucumber.serialize(config)
        restored = cucumber.deserialize(serialized)
        
        assert restored.preloop == 30.0
        assert restored.loop == 300.0
        assert restored.postloop == 60.0
        assert restored.onfinish == 60.0


class TestProcessConfigSerialization:
    """Test ProcessConfig serialization and deserialization."""
    
    def test_process_config_roundtrip(self):
        """ProcessConfig serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.config import ProcessConfig, TimeoutConfig
        
        config = ProcessConfig(
            num_loops=100,
            join_in=30.0,
            lives=3,
            timeouts=TimeoutConfig(preloop=5.0, loop=120.0)
        )
        
        serialized = cucumber.serialize(config)
        restored = cucumber.deserialize(serialized)
        
        assert restored.num_loops == 100
        assert restored.join_in == 30.0
        assert restored.lives == 3
        assert restored.timeouts.preloop == 5.0
        assert restored.timeouts.loop == 120.0
    
    def test_process_config_default_values(self):
        """ProcessConfig with default values serializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.config import ProcessConfig
        
        config = ProcessConfig()
        
        serialized = cucumber.serialize(config)
        restored = cucumber.deserialize(serialized)
        
        assert restored.num_loops is None
        assert restored.join_in is None
        assert restored.lives == 1
        assert restored.timeouts.preloop == 30.0


class TestProcessTimersSerialization:
    """Test ProcessTimers serialization and deserialization."""
    
    def test_process_timers_empty_roundtrip(self):
        """ProcessTimers with no section timers serializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.timers import ProcessTimers
        
        timers = ProcessTimers()
        
        serialized = cucumber.serialize(timers)
        restored = cucumber.deserialize(serialized)
        
        assert restored.preloop is None
        assert restored.loop is None
        assert restored.postloop is None
        assert restored.onfinish is None
        assert restored.full_loop is not None
    
    def test_process_timers_with_data_roundtrip(self):
        """ProcessTimers with recorded times serializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.timers import ProcessTimers
        
        timers = ProcessTimers()
        
        # Create some timers with data
        loop_timer = timers._ensure_timer('loop')
        loop_timer.add_time(1.0)
        loop_timer.add_time(2.0)
        
        preloop_timer = timers._ensure_timer('preloop')
        preloop_timer.add_time(0.5)
        
        serialized = cucumber.serialize(timers)
        restored = cucumber.deserialize(serialized)
        
        assert restored.loop is not None
        assert restored.loop.num_times == 2
        assert restored.loop.get_time(0) == 1.0
        
        assert restored.preloop is not None
        assert restored.preloop.num_times == 1
        
        assert restored.postloop is None


class TestProcessErrorsSerialization:
    """Test processing error classes serialization and deserialization."""
    
    def test_preloop_error_roundtrip(self):
        """PreloopError serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.errors import PreloopError
        
        error = PreloopError(current_lap=5)
        
        serialized = cucumber.serialize(error)
        restored = cucumber.deserialize(serialized)
        
        # Data is preserved (str() message is not reconstructed, but that's acceptable)
        assert restored.current_lap == 5
    
    def test_main_loop_error_roundtrip(self):
        """MainLoopError serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.errors import MainLoopError
        
        error = MainLoopError(current_lap=10)
        
        serialized = cucumber.serialize(error)
        restored = cucumber.deserialize(serialized)
        
        assert restored.current_lap == 10
    
    def test_postloop_error_roundtrip(self):
        """PostLoopError serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.errors import PostLoopError
        
        error = PostLoopError(current_lap=3)
        
        serialized = cucumber.serialize(error)
        restored = cucumber.deserialize(serialized)
        
        assert restored.current_lap == 3
    
    def test_onfinish_error_roundtrip(self):
        """OnFinishError serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.errors import OnFinishError
        
        error = OnFinishError(current_lap=7)
        
        serialized = cucumber.serialize(error)
        restored = cucumber.deserialize(serialized)
        
        assert restored.current_lap == 7
    
    def test_result_error_roundtrip(self):
        """ResultError serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.errors import ResultError
        
        error = ResultError(current_lap=2)
        
        serialized = cucumber.serialize(error)
        restored = cucumber.deserialize(serialized)
        
        assert restored.current_lap == 2
    
    def test_timeout_error_roundtrip(self):
        """TimeoutError serializes and deserializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.errors import TimeoutError
        
        error = TimeoutError(section="__loop__", timeout=30.0, current_lap=4)
        
        serialized = cucumber.serialize(error)
        restored = cucumber.deserialize(serialized)
        
        # Data is preserved (str() message is not reconstructed, but that's acceptable)
        assert restored.section == "__loop__"
        assert restored.timeout == 30.0
        assert restored.current_lap == 4


class TestProcessSerialization:
    """Test Process class serialization and deserialization."""
    
    def test_process_basic_roundtrip(self):
        """Process serializes and deserializes with config preserved."""
        from suitkaise import cucumber
        from suitkaise.processing._int.process_class import Process
        
        class MyProcess(Process):
            def __init__(self):
                self.counter = 0
                self.data = [1, 2, 3]
                self.config.num_loops = 10
                self.config.lives = 3
            
            def __loop__(self):
                self.counter += 1
        
        process = MyProcess()
        process.counter = 5
        process.data.append(4)
        
        serialized = cucumber.serialize(process)
        restored = cucumber.deserialize(serialized)
        
        # Check config
        assert restored.config.num_loops == 10
        assert restored.config.lives == 3
        
        # Check user attributes
        assert restored.counter == 5
        assert restored.data == [1, 2, 3, 4]
    
    def test_process_with_timers_roundtrip(self):
        """Process with ProcessTimers serializes correctly."""
        from suitkaise import cucumber
        from suitkaise.processing._int.process_class import Process
        from suitkaise.processing._int.timers import ProcessTimers
        
        class TimedProcess(Process):
            def __init__(self):
                self.value = 42
        
        process = TimedProcess()
        process.timers = ProcessTimers()
        loop_timer = process.timers._ensure_timer('loop')
        loop_timer.add_time(1.5)
        loop_timer.add_time(2.5)
        
        serialized = cucumber.serialize(process)
        restored = cucumber.deserialize(serialized)
        
        assert restored.timers is not None
        assert restored.timers.loop is not None
        assert restored.timers.loop.num_times == 2
        assert restored.timers.loop.mean == pytest.approx(2.0, rel=1e-6)
    
    def test_process_runtime_state_preserved(self):
        """Process runtime state (_current_lap, etc.) is preserved."""
        from suitkaise import cucumber
        from suitkaise.processing._int.process_class import Process
        
        class SimpleProcess(Process):
            def __init__(self):
                pass
        
        process = SimpleProcess()
        process._current_lap = 15
        process._start_time = 1234567890.0
        process._result = {"status": "done"}
        process._has_result = True
        
        serialized = cucumber.serialize(process)
        restored = cucumber.deserialize(serialized)
        
        assert restored._current_lap == 15
        assert restored._start_time == 1234567890.0
        assert restored._result == {"status": "done"}
        assert restored._has_result is True


# =============================================================================
# Nested Objects
# =============================================================================

class TestNestedObjects:
    """Test complex nested objects through cucumber."""
    
    def test_nested_objects_through_cucumber(self):
        """Complex nested objects work through cucumber."""
        from suitkaise import cucumber
        from suitkaise.sktime import Timer
        from suitkaise.circuit import Circuit
        
        # Object containing multiple suitkaise objects
        data = {
            "timer": Timer(),
            "circuit": Circuit(num_shorts_to_trip=3),
            "values": [1, 2, 3],
        }
        data["timer"].add_time(5.0)
        data["circuit"].short()
        
        serialized = cucumber.serialize(data)
        restored = cucumber.deserialize(serialized)
        
        assert restored["timer"].num_times == 1
        assert restored["timer"].most_recent == 5.0
        assert restored["circuit"].times_shorted == 1
        assert restored["values"] == [1, 2, 3]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
