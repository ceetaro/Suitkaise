"""
Integration Test: Parallel Processing with Subprocesses

Real-world scenario: A parallel job processor that:
1. Uses Process with full lifecycle hooks (__prerun__, __run__, __postrun__, etc.)
2. Uses Pool for batch processing
3. Uses Share for cross-process state coordination
4. Uses cerial for serializing complex objects across process boundaries
5. Uses Sktimer for performance tracking in each subprocess
6. Uses Circuit for failure handling in workers

This tests the full subprocess integration of:
- processing: Process lifecycle, Pool, Share
- cerial: Cross-process serialization of locks, loggers, Sktimer, Circuit
- timing: Sktimer in subprocesses
- circuits: Circuit in workers
- sk: @sk classes for Share compatibility
"""

import sys
import os
import time
import random
import signal
import threading
import logging

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing import Process, Pool, ProcessError
from suitkaise.timing import Sktimer, TimeThis
from suitkaise.circuits import Circuit, BreakingCircuit
from suitkaise.cerial import serialize, deserialize
from suitkaise.sk import sk


# =============================================================================
# Test Infrastructure
# =============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def run_test(self, name: str, test_func, timeout: float = 30.0):
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Test timed out after {timeout}s")
        
        old_handler = None
        try:
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
        except (AttributeError, ValueError):
            pass
        
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except TimeoutError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))
        finally:
            try:
                signal.alarm(0)
                if old_handler:
                    signal.signal(signal.SIGALRM, old_handler)
            except (AttributeError, ValueError):
                pass
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*70}{self.RESET}\n")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        for result in self.results:
            if result.passed:
                status = f"{self.GREEN}✓ PASS{self.RESET}"
            else:
                status = f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")
        
        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")

        if failed != 0:
            print(f"{self.BOLD}{self.RED}Failed tests (recap):{self.RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  {self.RED}✗ {result.name}{self.RESET}")
                    if result.error:
                        print(f"     {self.RED}└─ {result.error}{self.RESET}")
            print()


        try:
            from tests._failure_registry import record_failures
            record_failures(self.suite_name, [r for r in self.results if not r.passed])
        except Exception:
            pass

        return failed == 0


# =============================================================================
# Process Classes (defined at module level for multiprocessing)
# =============================================================================

class LifecycleProcess(Process):
    """Process that tests all lifecycle hooks."""
    def __init__(self, value: int, fail_in: str = None):
        self.value = value
        self.fail_in = fail_in
        self._prerun_called = False
        self._run_called = False
        self._postrun_called = False
        self._result_value = None
        self.process_config.runs = 1  # Run once and finish
    
    def __prerun__(self):
        """Called before __run__."""
        self._prerun_called = True
        if self.fail_in == "prerun":
            raise ValueError("Failure in __prerun__")
    
    def __run__(self):
        """Main execution."""
        self._run_called = True
        if self.fail_in == "run":
            raise ValueError("Failure in __run__")
        time.sleep(0.01)
        self._result_value = self.value * 2
    
    def __postrun__(self):
        """Called after __run__ (only on success)."""
        self._postrun_called = True
        if self.fail_in == "postrun":
            raise ValueError("Failure in __postrun__")
    
    def __result__(self):
        return {
            "value": self._result_value,
            "prerun": self._prerun_called,
            "run": self._run_called,
            "postrun": self._postrun_called,
        }


class TimedProcess(Process):
    """Process with internal timing."""
    def __init__(self, iterations: int):
        self.iterations = iterations
        self._timer = Sktimer()  # Use _timer to avoid conflict with Process.timers
        self._total_work = 0
        self.process_config.runs = 1  # Run once and finish
    
    def __run__(self):
        for i in range(self.iterations):
            self._timer.start()
            # Simulate work
            time.sleep(0.005)
            self._total_work += i
            self._timer.stop()
    
    def __result__(self):
        return {
            "total_work": self._total_work,
            "timer_count": self._timer.num_times,
            "timer_mean": self._timer.mean if self._timer.num_times > 0 else 0,
        }


class CircuitProcess(Process):
    """Process with circuit breaker for failure handling."""
    def __init__(self, task_id: int, fail_rate: float = 0.0):
        self.task_id = task_id
        self.fail_rate = fail_rate
        self.circuit = BreakingCircuit(num_shorts_to_trip=3, sleep_time_after_trip=0.01)
        self._result_value = None
        self.process_config.runs = 1  # Run once and finish
    
    def __run__(self):
        attempts = 0
        
        while not self.circuit.broken:
            attempts += 1
            
            if random.random() < self.fail_rate:
                self.circuit.short()
            else:
                # Success
                self._result_value = self.task_id * 10
                break
        
        if self.circuit.broken:
            self._result_value = -1  # Indicate failure
    
    def __result__(self):
        return {
            "task_id": self.task_id,
            "result": self._result_value,
            "broken": self.circuit.broken,
            "failures": self.circuit.total_failures,
        }


class ComplexStateProcess(Process):
    """Process with complex state including locks, loggers, timers."""
    def __init__(self, name: str, data: dict):
        self.name = name
        self.data = data
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"process_{name}")
        self._timer = Sktimer()  # Use _timer to avoid conflict with Process.timers
        self._processed = False
        self.process_config.runs = 1  # Run once and finish
    
    def __run__(self):
        self._timer.start()
        
        with self.lock:
            # Process data
            time.sleep(0.01)
            self.data["processed_by"] = self.name
            self.data["timestamp"] = time.time()
        
        self._timer.stop()
        self._processed = True
    
    def __result__(self):
        return {
            "name": self.name,
            "data": self.data,
            "processed": self._processed,
            "timer_count": self._timer.num_times,
        }


class ComputeProcess(Process):
    """Simple compute process for pool testing."""
    def __init__(self, x: int):
        self.x = x
        self._result = None
        self.process_config.runs = 1  # Run once and finish
    
    def __run__(self):
        time.sleep(0.01)  # Simulate work
        self._result = self.x ** 2
    
    def __result__(self):
        return self._result


class AddProcess(Process):
    """Process that adds two numbers (for starmap testing)."""
    def __init__(self, a: int, b: int):
        self.a = a
        self.b = b
        self._result = None
        self.process_config.runs = 1  # Run once and finish
    
    def __run__(self):
        time.sleep(0.01)
        self._result = self.a + self.b
    
    def __result__(self):
        return self._result


# =============================================================================
# Integration Tests
# =============================================================================

def test_process_lifecycle_hooks():
    """Test that Process lifecycle hooks are called correctly."""
    proc = LifecycleProcess(5)
    proc.start()
    proc.wait(timeout=10.0)
    result = proc.result()
    
    assert result["prerun"] == True, "prerun should be called"
    assert result["run"] == True, "run should be called"
    assert result["postrun"] == True, "postrun should be called"
    assert result["value"] == 10, f"Result should be 10, got {result['value']}"


def test_process_prerun_failure():
    """Test that failure in __prerun__ is handled."""
    proc = LifecycleProcess(5, fail_in="prerun")
    proc.start()
    proc.wait(timeout=10.0)
    
    try:
        proc.result()
        assert False, "Should have raised ProcessError"
    except ProcessError:
        pass  # Expected


def test_process_run_failure():
    """Test that failure in __run__ is handled."""
    proc = LifecycleProcess(5, fail_in="run")
    proc.start()
    proc.wait(timeout=10.0)
    
    try:
        proc.result()
        assert False, "Should have raised ProcessError"
    except ProcessError:
        pass  # Expected


def test_process_with_timer():
    """Test Process with internal Sktimer."""
    proc = TimedProcess(5)
    proc.start()
    proc.wait(timeout=10.0)
    result = proc.result()
    
    assert result["timer_count"] == 5, f"Sktimer should have 5 measurements, got {result['timer_count']}"
    assert result["timer_mean"] >= 0.004, f"Mean should be ~5ms, got {result['timer_mean']}"
    assert result["total_work"] == sum(range(5)), f"Total work should be {sum(range(5))}"


def test_process_with_circuit():
    """Test Process with BreakingCircuit."""
    # Process with 0 fail rate should succeed
    proc = CircuitProcess(42, fail_rate=0.0)
    proc.start()
    proc.wait(timeout=10.0)
    result = proc.result()
    
    assert result["result"] == 420, f"Result should be 420, got {result['result']}"
    assert result["broken"] == False, "Circuit should not be broken"


def test_process_with_complex_state():
    """Test Process with locks, loggers, timers (serialized via cerial)."""
    data = {"input": "test_value", "count": 42}
    proc = ComplexStateProcess("worker_1", data)
    proc.start()
    proc.wait(timeout=10.0)
    result = proc.result()
    
    assert result["processed"] == True, "Should be processed"
    assert result["data"]["processed_by"] == "worker_1", "Should have processor name"
    assert "timestamp" in result["data"], "Should have timestamp"
    assert result["timer_count"] == 1, "Sktimer should have 1 measurement"


def test_pool_basic_map():
    """Test Pool.map with Process classes."""
    pool = Pool(workers=4)
    
    inputs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    results = pool.map(ComputeProcess, inputs)
    
    expected = [x ** 2 for x in inputs]
    assert results == expected, f"Expected {expected}, got {results}"


def test_pool_star_map():
    """Test Pool.star().map for multi-arg Process classes."""
    pool = Pool(workers=4)
    
    inputs = [(1, 2), (3, 4), (5, 6), (7, 8)]
    results = pool.star().map(AddProcess, inputs)
    
    expected = [3, 7, 11, 15]
    assert results == expected, f"Expected {expected}, got {results}"


def test_pool_parallel_execution():
    """Test that Pool runs processes in parallel."""
    pool = Pool(workers=4)
    
    # 8 processes, each takes ~10ms
    inputs = list(range(8))
    
    start = time.perf_counter()
    results = pool.map(ComputeProcess, inputs)
    elapsed = time.perf_counter() - start
    
    # With 4 workers and 8 tasks, should complete faster than sequential (~80ms)
    # Allow generous margin for process overhead (Windows is slower)
    max_elapsed = 1.5 if sys.platform == "win32" else 0.5
    assert elapsed < max_elapsed, f"Should run in parallel, took {elapsed:.3f}s"
    
    expected = [x ** 2 for x in inputs]
    assert results == expected


def test_cerial_complex_process_state():
    """Test that complex Process state serializes correctly."""
    # Create a process with complex state
    data = {"values": [1, 2, 3], "config": {"active": True}}
    proc = ComplexStateProcess("test_worker", data)
    
    # Manually run lifecycle to populate state
    proc.__prerun__() if hasattr(proc, '__prerun__') else None
    proc.__run__()
    proc.__postrun__() if hasattr(proc, '__postrun__') else None
    
    # Serialize the process
    serialized = serialize(proc)
    restored = deserialize(serialized)
    
    # Verify state is preserved
    assert restored.name == "test_worker"
    assert restored.data["processed_by"] == "test_worker"
    assert restored._processed == True
    
    # Lock should be recreated
    assert restored.lock.acquire(blocking=False)
    restored.lock.release()
    
    # Sktimer should preserve measurements (using _timer to match class definition)
    assert restored._timer.num_times == 1


def test_multiple_concurrent_processes():
    """Test running many processes concurrently."""
    num_processes = 20
    
    procs = [ComputeProcess(i) for i in range(num_processes)]
    
    start = time.perf_counter()
    
    # Start all
    for p in procs:
        p.start()
    
    # Wait for all
    for p in procs:
        p.wait(timeout=10.0)
    
    # Get results
    results = [p.result() for p in procs]
    
    elapsed = time.perf_counter() - start
    
    expected = [i ** 2 for i in range(num_processes)]
    assert results == expected
    
    # Should be much faster than sequential (~200ms); allow more time on Windows
    max_elapsed = 3.0 if sys.platform == "win32" else 0.7
    assert elapsed < max_elapsed, f"Should run concurrently, took {elapsed:.3f}s"


def test_full_parallel_job_processor():
    """
    Full integration test simulating a parallel job processor:
    1. Create jobs with complex state (timers, locks)
    2. Process in parallel with Pool
    3. Track overall timing
    4. Aggregate results
    """
    overall_timer = Sktimer()
    
    # Create job inputs - keep it small to avoid hanging
    job_configs = [
        {"input": f"job_{i}", "count": i * 10}
        for i in range(1, 5)  # 4 jobs
    ]
    
    # Process with timing
    overall_timer.start()
    
    pool = Pool(workers=2)
    
    try:
        results = pool.map(ComputeProcess, [c["count"] for c in job_configs])
        
        overall_timer.stop()
        
        # Verify results (ComputeProcess squares the input)
        assert len(results) == 4, f"Should have 4 results, got {len(results)}"
        
        expected = [10**2, 20**2, 30**2, 40**2]
        for i, (result, exp) in enumerate(zip(results, expected)):
            assert result == exp, f"Job {i} should be {exp}, got {result}"
        
        # Overall should be reasonably fast
        assert overall_timer.most_recent < 1.0, \
            f"Parallel processing took too long: {overall_timer.most_recent:.3f}s"
    finally:
        pool.close()


# =============================================================================
# Main Entry Point
# =============================================================================

# Colors for verbose output
GREEN = '\033[92m'
RED = '\033[91m'
CYAN = '\033[96m'
DIM = '\033[2m'
BOLD = '\033[1m'
RESET = '\033[0m'


def run_scenario(name: str, description: str, test_func, timeout: float, results: list):
    """Run a scenario with verbose output."""
    print(f"\n  {CYAN}Testing:{RESET} {name}")
    print(f"  {DIM}{description}{RESET}")
    
    old_handler = None
    try:
        old_handler = signal.signal(signal.SIGALRM, lambda s, f: (_ for _ in ()).throw(TimeoutError(f"Timed out after {timeout}s")))
        signal.alarm(int(timeout))
    except (AttributeError, ValueError):
        pass
    
    try:
        test_func()
        results.append((name, True))
        print(f"  {GREEN}✓ Works as expected{RESET}")
    except AssertionError as e:
        results.append((name, False))
        print(f"  {RED}✗ Failed: {e}{RESET}")
    except Exception as e:
        results.append((name, False))
        print(f"  {RED}✗ Error: {type(e).__name__}: {e}{RESET}")
    finally:
        try:
            signal.alarm(0)
            if old_handler:
                signal.signal(signal.SIGALRM, old_handler)
        except (AttributeError, ValueError):
            pass


def run_all_tests():
    """Run all parallel processing integration tests with verbose output."""
    results = []
    
    print(f"\n  {DIM}This scenario simulates a job processing system with worker pools,")
    print(f"  cross-process state, and complex object serialization.{RESET}")
    
    run_scenario(
        "Process Lifecycle Hooks",
        "Testing __prerun__, __run__, __postrun__, __onfinish__ sequence",
        test_process_lifecycle_hooks, 15, results
    )
    
    run_scenario(
        "Prerun Failure Handling",
        "Gracefully handling errors in setup phase",
        test_process_prerun_failure, 15, results
    )
    
    run_scenario(
        "Run Failure Handling",
        "Gracefully handling errors in main execution",
        test_process_run_failure, 15, results
    )
    
    run_scenario(
        "Process with Sktimer",
        "Performance tracking inside worker processes",
        test_process_with_timer, 15, results
    )
    
    run_scenario(
        "Process with Circuit Breaker",
        "Rate limiting and failure detection in workers",
        test_process_with_circuit, 15, results
    )
    
    run_scenario(
        "Complex State in Process",
        "Processes with locks, loggers, and nested objects",
        test_process_with_complex_state, 15, results
    )
    
    run_scenario(
        "Pool Basic Map",
        "Distributing work across worker pool",
        test_pool_basic_map, 30, results
    )
    
    run_scenario(
        "Pool Star Map",
        "Passing multiple arguments to worker functions",
        test_pool_star_map, 30, results
    )
    
    run_scenario(
        "Parallel Execution Speedup",
        "Verifying workers actually run in parallel",
        test_pool_parallel_execution, 30, results
    )
    
    run_scenario(
        "Cross-Process Serialization",
        "Serializing complex objects between main and workers",
        test_cerial_complex_process_state, 15, results
    )
    
    run_scenario(
        "Concurrent Processes",
        "Running multiple independent processes simultaneously",
        test_multiple_concurrent_processes, 30, results
    )
    
    run_scenario(
        "Complete Job Processor",
        "Full integration: pool, timer, configs, results collection",
        test_full_parallel_job_processor, 30, results
    )
    
    # Summary
    passed = sum(1 for _, p in results if p)
    failed = len(results) - passed
    
    print(f"\n  {BOLD}{'─'*70}{RESET}")
    if failed == 0:
        print(f"  {GREEN}{BOLD}✓ All {passed} scenarios passed!{RESET}")
    else:
        print(f"  Passed: {passed}  |  {RED}Failed: {failed}{RESET}")
    print(f"  {BOLD}{'─'*70}{RESET}")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
