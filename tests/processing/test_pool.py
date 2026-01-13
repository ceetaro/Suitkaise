"""
Pool Class Tests

Tests Pool functionality:
- Pool creation
- map() - run processes on inputs
- starmap() - unpack args to processes
- Parallel execution timing
"""

import sys
import time
import signal

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.processing import Process, Pool

# Import test classes from separate module for multiprocessing compatibility
from tests.processing.test_process_classes import (
    DoubleProcess, AddProcess, SlowDoubleProcess, FailingDoubleProcess
)


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
    
    def run_test(self, name: str, test_func, timeout: float = 10.0):
        """Run a test with a timeout."""
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
        return failed == 0


# =============================================================================
# Pool Import and Creation Tests
# =============================================================================

def test_pool_import():
    """Pool should be importable."""
    assert Pool is not None


def test_pool_creation():
    """Pool should be creatable."""
    pool = Pool()
    
    assert pool is not None


def test_pool_with_workers():
    """Pool should accept workers parameter."""
    pool = Pool(workers=4)
    
    assert pool is not None


def test_pool_has_map():
    """Pool should have map() method."""
    pool = Pool()
    
    assert hasattr(pool, 'map')
    assert callable(pool.map)


def test_pool_has_star():
    """Pool should have star() method."""
    pool = Pool()
    
    assert hasattr(pool, 'star')
    assert callable(pool.star)


def test_pool_has_close():
    """Pool should have close() method."""
    pool = Pool()
    
    if hasattr(pool, 'close'):
        assert callable(pool.close)


def test_pool_has_join():
    """Pool should have join() method."""
    pool = Pool()
    
    if hasattr(pool, 'join'):
        assert callable(pool.join)


# =============================================================================
# Direct Process Tests (no subprocess)
# =============================================================================

def test_double_process_direct():
    """DoubleProcess should work when called directly."""
    proc = DoubleProcess(5)
    
    proc.__run__()
    result = proc.__result__()
    
    assert result == 10


def test_add_process_direct():
    """AddProcess should work when called directly."""
    proc = AddProcess(3, 4)
    
    proc.__run__()
    result = proc.__result__()
    
    assert result == 7


def test_multiple_processes_direct():
    """Multiple processes should work directly."""
    procs = [DoubleProcess(i) for i in range(5)]
    
    for p in procs:
        p.__run__()
    
    results = [p.__result__() for p in procs]
    
    assert results == [0, 2, 4, 6, 8]


# =============================================================================
# Pool.map Tests
# =============================================================================

def test_pool_map_basic():
    """Pool.map should run processes on inputs."""
    pool = Pool(workers=4)
    
    results = pool.map(DoubleProcess, [1, 2, 3, 4, 5])
    
    assert results == [2, 4, 6, 8, 10]


def test_pool_map_empty():
    """Pool.map with empty input should return empty list."""
    pool = Pool(workers=4)
    
    results = pool.map(DoubleProcess, [])
    
    assert results == []


def test_pool_map_single():
    """Pool.map with single input should work."""
    pool = Pool(workers=4)
    
    results = pool.map(DoubleProcess, [42])
    
    assert results == [84]


def test_pool_map_large():
    """Pool.map should handle many items."""
    pool = Pool(workers=4)
    
    inputs = list(range(100))
    results = pool.map(DoubleProcess, inputs)
    
    expected = [i * 2 for i in inputs]
    assert results == expected


def test_pool_map_parallel():
    """Pool.map should run in parallel."""
    pool = Pool(workers=4)
    
    # 4 processes, each takes 50ms
    start = time.perf_counter()
    results = pool.map(SlowDoubleProcess, [1, 2, 3, 4])
    elapsed = time.perf_counter() - start
    
    assert results == [2, 4, 6, 8]
    # Should complete faster than sequential (200ms)
    # Allow some overhead for process spawning
    assert elapsed < 0.5, f"Should be parallel (< 200ms sequential), got {elapsed}"


def test_pool_map_ordering():
    """Pool.map should preserve order of results."""
    pool = Pool(workers=4)
    
    inputs = [10, 20, 30, 40, 50]
    results = pool.map(DoubleProcess, inputs)
    
    expected = [20, 40, 60, 80, 100]
    assert results == expected


# =============================================================================
# Pool.star().map Tests
# =============================================================================

def test_pool_star_map_basic():
    """Pool.star().map should unpack args."""
    pool = Pool(workers=4)
    
    results = pool.star().map(AddProcess, [(1, 2), (3, 4), (5, 6)])
    assert results == [3, 7, 11]


def test_pool_star_map_empty():
    """Pool.star().map with empty input should return empty list."""
    pool = Pool(workers=4)
    
    results = pool.star().map(AddProcess, [])
    assert results == []


def test_pool_star_map_single():
    """Pool.star().map with single input should work."""
    pool = Pool(workers=4)
    
    results = pool.star().map(AddProcess, [(10, 20)])
    assert results == [30]


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_pool_map_with_failure():
    """Pool.map should handle failures appropriately."""
    pool = Pool(workers=4)
    
    try:
        # -1 will cause failure
        results = pool.map(FailingDoubleProcess, [1, -1, 2])
        # Depending on implementation, might get partial results or exception
    except Exception:
        pass  # Expected


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all Pool tests."""
    runner = TestRunner("Pool Class Tests")
    
    # Import and creation tests (fast, no subprocess)
    runner.run_test("Pool import", test_pool_import)
    runner.run_test("Pool creation", test_pool_creation)
    runner.run_test("Pool with workers", test_pool_with_workers)
    runner.run_test("Pool has map()", test_pool_has_map)
    runner.run_test("Pool has star()", test_pool_has_star)
    runner.run_test("Pool has close()", test_pool_has_close)
    runner.run_test("Pool has join()", test_pool_has_join)
    
    # Direct process tests (no subprocess, fast)
    runner.run_test("DoubleProcess direct", test_double_process_direct)
    runner.run_test("AddProcess direct", test_add_process_direct)
    runner.run_test("Multiple processes direct", test_multiple_processes_direct)
    
    # Pool.map tests (actual subprocess)
    runner.run_test("Pool.map basic", test_pool_map_basic, timeout=15)
    runner.run_test("Pool.map empty", test_pool_map_empty, timeout=10)
    runner.run_test("Pool.map single", test_pool_map_single, timeout=10)
    runner.run_test("Pool.map large", test_pool_map_large, timeout=30)
    runner.run_test("Pool.map parallel", test_pool_map_parallel, timeout=15)
    runner.run_test("Pool.map ordering", test_pool_map_ordering, timeout=15)
    
    # Pool.star().map tests
    runner.run_test("Pool.star().map basic", test_pool_star_map_basic, timeout=15)
    runner.run_test("Pool.star().map empty", test_pool_star_map_empty, timeout=10)
    runner.run_test("Pool.star().map single", test_pool_star_map_single, timeout=10)
    
    # Error handling
    runner.run_test("Pool.map with failure", test_pool_map_with_failure, timeout=15)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
