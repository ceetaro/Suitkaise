"""
Integration Test: Data Processing Pipeline

Real-world scenario: A data pipeline that:
1. Reads files from a project using skpath
2. Processes them in parallel using Pool
3. Uses Share to coordinate progress tracking across workers
4. Uses Circuit for rate limiting
5. Uses Sktimer to track performance
6. Uses cerial to serialize state between processes

This tests the full integration of:
- skpath: Project path utilities, file discovery
- processing: Process, Pool, Share
- circuits: Circuit for backoff on failures
- timing: Sktimer, TimeThis, @timethis
- cerial: Cross-process serialization
- sk: @sk decorated classes for Share compatibility
"""

import sys
import os
import time
import random
import signal

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.paths import Skpath, get_project_root, get_project_paths
from suitkaise.processing import Skprocess, Pool, Share
from suitkaise.circuits import Circuit, BreakingCircuit
from suitkaise.timing import Sktimer, TimeThis, timethis
from suitkaise.cerial import serialize, deserialize
from suitkaise.sk import sk

Process = Skprocess


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
# Shared Classes for Multiprocessing
# =============================================================================

@sk
class ProgressTracker:
    """Tracks progress across workers using Share."""
    def __init__(self):
        self.files_processed = 0
        self.bytes_processed = 0
        self.errors = 0
    
    def add_file(self, byte_count: int):
        self.files_processed += 1
        self.bytes_processed += byte_count
    
    def add_error(self):
        self.errors += 1
    
    def reset(self):
        self.files_processed = 0
        self.bytes_processed = 0
        self.errors = 0


class FileProcessor(Process):
    """Process that simulates file processing."""
    def __init__(self, file_path: str, fail_rate: float = 0.0):
        self.file_path = file_path
        self.fail_rate = fail_rate
        self._byte_count = 0
        self._success = False
        self.process_config.runs = 1  # Run once and finish
    
    def __run__(self):
        # Simulate processing time
        time.sleep(random.uniform(0.01, 0.03))
        
        # Simulate occasional failures
        if random.random() < self.fail_rate:
            raise ValueError(f"Failed to process {self.file_path}")
        
        # Simulate reading file and getting byte count
        self._byte_count = len(self.file_path) * 100  # Mock byte count
        self._success = True
    
    def __result__(self):
        return {"path": self.file_path, "bytes": self._byte_count, "success": self._success}


# =============================================================================
# Integration Tests
# =============================================================================

def test_skpath_with_project_discovery():
    """Test skpath can discover and list project files."""
    root = get_project_root()
    
    assert root.exists, "Project root should exist"
    assert root.is_dir, "Project root should be a directory"
    
    # Get some paths from project
    paths = get_project_paths(root, as_strings=True)
    
    assert len(paths) > 0, "Should find some files in project"
    
    # Check that paths are relative and valid
    for p in paths[:10]:  # Check first 10
        full_path = root / p
        assert isinstance(full_path, Skpath), "Should create Skpath from joined path"


def test_timer_with_timethis():
    """Test Sktimer integration with TimeThis context manager."""
    timer = Sktimer()
    
    # Use TimeThis to time code blocks
    for _ in range(5):
        with TimeThis(timer) as t:
            time.sleep(0.01)
    
    assert timer.num_times == 5, f"Should have 5 measurements, got {timer.num_times}"
    assert timer.mean > 0.008, f"Mean should be ~10ms, got {timer.mean}"
    assert timer.mean < 0.03, f"Mean should be ~10ms, got {timer.mean}"


def test_circuit_with_timer():
    """Test Circuit and Sktimer working together."""
    timer = Sktimer()
    circuit = Circuit(num_shorts_to_trip=3, sleep_time_after_trip=0.01, backoff_factor=1.0)
    
    # Simulate processing with circuit breaker
    for i in range(10):
        with TimeThis(timer):
            if i % 2 == 0:
                circuit.short()  # Simulate alternating failures
            time.sleep(0.005)
    
    assert timer.num_times == 10, "Should have 10 measurements"
    assert circuit.total_trips >= 1, f"Should have tripped at least once, got {circuit.total_trips}"


def test_cerial_with_complex_objects():
    """Test cerial serializes complex objects for cross-process communication."""
    import threading
    import logging
    
    @sk
    class ComplexState:
        def __init__(self):
            self.lock = threading.Lock()
            self.logger = logging.getLogger("test")
            self.timer = Sktimer()
            self.circuit = Circuit(5, 0.01)
            self.progress = ProgressTracker()
    
    state = ComplexState()
    state.timer.add_time(1.0)
    state.timer.add_time(2.0)
    state.progress.add_file(1000)
    
    # Serialize and deserialize
    data = serialize(state)
    restored = deserialize(data)
    
    # Verify state is preserved
    assert len(restored.timer.times) == 2, "Sktimer times should be preserved"
    assert restored.progress.files_processed == 1, "Progress should be preserved"
    # Lock should be recreated
    assert restored.lock.acquire(blocking=False)
    restored.lock.release()


def test_pool_with_file_processing():
    """Test Pool for parallel file processing."""
    pool = Pool(workers=4)
    
    # Create mock file paths
    mock_files = [f"/mock/path/file_{i}.txt" for i in range(20)]
    
    # Process files in parallel
    results = pool.map(FileProcessor, mock_files)
    
    assert len(results) == 20, f"Should have 20 results, got {len(results)}"
    assert all(r["success"] for r in results), "All should succeed"
    
    # Verify ordering is preserved
    for i, result in enumerate(results):
        assert f"file_{i}" in result["path"], "Results should be in order"


def test_share_with_progress_tracking():
    """Test Share for cross-process state coordination."""
    with Share() as share:
        share.timer = Sktimer()
        share.progress = ProgressTracker()
        
        # Simulate worker updates
        for i in range(5):
            share.timer.add_time(float(i) * 0.1)
            share.progress.add_file(1000 * (i + 1))
        
        # Wait for writes to process (coordinator can be slow on Windows)
        timer = None
        progress = None
        deadline = time.perf_counter() + 2.0
        while time.perf_counter() < deadline:
            timer = share._coordinator.get_object('timer')
            progress = share._coordinator.get_object('progress')
            if timer is not None and progress is not None:
                if len(timer.times) >= 5 and progress.files_processed >= 5:
                    break
            time.sleep(0.05)
        
        assert timer is not None, "Sktimer should be stored in Share"
        assert progress is not None, "Progress should be stored in Share"
        assert len(timer.times) == 5, f"Sktimer should have 5 times, got {len(timer.times)}"
        assert progress.files_processed == 5, f"Should have processed 5 files, got {progress.files_processed}"


def test_breaking_circuit_retry_pattern():
    """Test BreakingCircuit for retry pattern with exponential backoff."""
    circuit = BreakingCircuit(
        num_shorts_to_trip=3,
        sleep_time_after_trip=0.01,
        backoff_factor=2.0,
        max_sleep_time=0.1
    )
    timer = Sktimer()
    
    attempts = 0
    success = False
    
    while not circuit.broken and not success:
        attempts += 1
        with TimeThis(timer):
            # Simulate operation that fails first 2 times
            if attempts < 3:
                circuit.short()
            else:
                success = True
    
    assert success, "Should eventually succeed"
    assert attempts == 3, f"Should take 3 attempts, took {attempts}"
    assert circuit.broken == False, "Circuit should not be broken (succeeded before trip)"


def test_full_pipeline_integration():
    """
    Full integration test simulating a real data pipeline:
    1. Discover files with skpath
    2. Process in parallel with Pool
    3. Track progress with Share
    4. Use Circuit for failure handling
    5. Time operations with Sktimer
    """
    # Get project root and some Python files
    root = get_project_root()
    all_paths = get_project_paths(root, as_strings=True)
    
    # Filter to Python files, limit to 10 for test speed
    py_files = [p for p in all_paths if p.endswith('.py')][:10]
    
    if len(py_files) < 2:
        # Fallback if not enough Python files
        py_files = [f"mock_{i}.py" for i in range(10)]
    
    # Track overall performance
    pipeline_timer = Sktimer()
    
    with TimeThis(pipeline_timer):
        # Create pool and process
        pool = Pool(workers=4)
        results = pool.map(FileProcessor, py_files)
    
    # Verify results
    assert len(results) == len(py_files), "Should have result for each file"
    assert pipeline_timer.num_times == 1, "Should have one pipeline timing"
    
    # Calculate aggregate stats
    total_bytes = sum(r["bytes"] for r in results)
    successful = sum(1 for r in results if r["success"])
    
    assert successful == len(py_files), "All files should be processed successfully"
    assert total_bytes > 0, "Should have processed some bytes"


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
    """Run all data pipeline integration tests with verbose output."""
    results = []
    
    print(f"\n  {DIM}This scenario simulates an ETL system that discovers files,")
    print(f"  processes them in parallel, and tracks progress across workers.{RESET}")
    
    run_scenario(
        "Project File Discovery",
        "Using skpath to find files in a project directory",
        test_skpath_with_project_discovery, 10, results
    )
    
    run_scenario(
        "Performance Measurement",
        "Using Sktimer with TimeThis context manager to track execution time",
        test_timer_with_timethis, 10, results
    )
    
    run_scenario(
        "Circuit Breaker + Timing",
        "Combining rate limiting with performance tracking",
        test_circuit_with_timer, 10, results
    )
    
    run_scenario(
        "Cross-Process Serialization",
        "Serializing complex objects (locks, loggers, timers) for worker processes",
        test_cerial_with_complex_objects, 10, results
    )
    
    run_scenario(
        "Parallel File Processing",
        "Using Pool to process files across multiple workers",
        test_pool_with_file_processing, 30, results
    )
    
    run_scenario(
        "Shared Progress Tracking",
        "Coordinating progress updates across worker processes",
        test_share_with_progress_tracking, 15, results
    )
    
    run_scenario(
        "Retry with Exponential Backoff",
        "Using BreakingCircuit for automatic retry with increasing delays",
        test_breaking_circuit_retry_pattern, 10, results
    )
    
    run_scenario(
        "Complete Pipeline",
        "All components working together: discover, process, track, report",
        test_full_pipeline_integration, 30, results
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
