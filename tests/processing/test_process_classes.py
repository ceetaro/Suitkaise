"""
Test Process classes for multiprocessing tests.

These classes are defined in a separate module so they can be properly
serialized/deserialized by cerial across processes.

Classes defined in __main__ cannot be deserialized in subprocess because
the subprocess has a different __main__ module.
"""

import sys
import time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.processing import Process


class SimpleProcess(Process):
    """Simple process that computes a value."""
    def __init__(self, value):
        self.value = value
        self._result_value = None
        self.process_config.runs = 1  # Run exactly once, then finish
    
    def __run__(self):
        self._result_value = self.value * 2
    
    def __result__(self):
        return self._result_value


class SlowProcess(Process):
    """Process that takes time to complete."""
    def __init__(self, delay):
        self.delay = delay
        self._result_value = None
        self.process_config.runs = 1  # Run exactly once, then finish
    
    def __run__(self):
        time.sleep(self.delay)
        self._result_value = "done"
    
    def __result__(self):
        return self._result_value


class FailingProcess(Process):
    """Process that raises an error."""
    def __init__(self, message="test error"):
        self.message = message
        self.process_config.runs = 1  # Run exactly once (will fail immediately)
    
    def __run__(self):
        raise ValueError(self.message)
    
    def __result__(self):
        return None


class ProcessWithCallbacks(Process):
    """Process with all lifecycle callbacks."""
    def __init__(self):
        self.pre_run_called = False
        self.run_called = False
        self._result_value = None
        self.finish_called = False
        self.process_config.runs = 1  # Run exactly once, then finish
    
    def __prerun__(self):
        self.pre_run_called = True
    
    def __run__(self):
        self.run_called = True
        self._result_value = "completed"
    
    def __result__(self):
        return self._result_value
    
    def __onfinish__(self):
        self.finish_called = True


class DoubleProcess(Process):
    """Process that doubles a value (for Pool tests)."""
    def __init__(self, value):
        self.value = value
        self._result_value = None
        self.process_config.runs = 1  # Run exactly once, then finish
    
    def __run__(self):
        self._result_value = self.value * 2
    
    def __result__(self):
        return self._result_value


class AddProcess(Process):
    """Process that adds two values (for Pool tests)."""
    def __init__(self, a, b):
        self.a = a
        self.b = b
        self._result_value = None
        self.process_config.runs = 1  # Run exactly once, then finish
    
    def __run__(self):
        self._result_value = self.a + self.b
    
    def __result__(self):
        return self._result_value


class SlowDoubleProcess(Process):
    """Slow process for Pool timing tests."""
    def __init__(self, value):
        self.value = value
        self._result_value = None
        self.process_config.runs = 1  # Run exactly once, then finish
    
    def __run__(self):
        time.sleep(0.05)  # 50ms
        self._result_value = self.value * 2
    
    def __result__(self):
        return self._result_value


class FailingDoubleProcess(Process):
    """Process that fails on certain values."""
    def __init__(self, value):
        self.value = value
        self._result_value = None
        self.process_config.runs = 1  # Run exactly once, then finish
    
    def __run__(self):
        if self.value < 0:
            raise ValueError(f"Cannot double negative: {self.value}")
        self._result_value = self.value * 2
    
    def __result__(self):
        return self._result_value


class InfiniteCounterProcess(Process):
    """Process that counts forever until stopped."""
    def __init__(self):
        self.count = 0
        # No config.runs set - runs indefinitely until stop() is called
    
    def __run__(self):
        self.count += 1
        time.sleep(0.01)  # Small delay to not hog CPU
    
    def __result__(self):
        return self.count


class LimitedCounterProcess(Process):
    """Process that counts up to a limit."""
    def __init__(self, limit):
        self.count = 0
        self.limit = limit
        self.process_config.runs = limit
    
    def __run__(self):
        self.count += 1
        time.sleep(0.01)  # Small delay
    
    def __result__(self):
        return self.count


class HangingProcess(Process):
    """Process that hangs forever (for kill() testing)."""
    def __init__(self):
        self.started = False
        self.process_config.runs = 1
    
    def __run__(self):
        self.started = True
        # Hang forever - will only exit via kill()
        while True:
            time.sleep(1)
    
    def __result__(self):
        return "never reached"


class SelfStoppingProcess(Process):
    """Process that stops itself after reaching a target count."""
    def __init__(self, target: int):
        self.target = target
        self.count = 0
        # Runs indefinitely until self.stop() is called
    
    def __run__(self):
        self.count += 1
        time.sleep(0.01)
        
        # Stop itself when target is reached
        if self.count >= self.target:
            self.stop()
    
    def __result__(self):
        return self.count
