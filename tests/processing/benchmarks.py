"""
Processing Module Benchmarks

Performance benchmarks for:
- Process spawn overhead
- Pool.map throughput
"""

import sys
import time as stdlib_time

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing import Skprocess, Pool, Share
from suitkaise.timing import Sktimer


# =============================================================================
# Benchmark Infrastructure
# =============================================================================

class Benchmark:
    def __init__(self, name: str, ops_per_sec: float, us_per_op: float, extra: str = ""):
        self.name = name
        self.ops_per_sec = ops_per_sec
        self.us_per_op = us_per_op
        self.extra = extra


class BenchmarkRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def bench_timed(self, name: str, iterations: int, total_time: float):
        """Record a benchmark given total time."""
        ops_per_sec = iterations / total_time
        us_per_op = (total_time / iterations) * 1_000_000
        self.results.append(Benchmark(name, ops_per_sec, us_per_op))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*80}{self.RESET}\n")
        
        print(f"  {'Benchmark':<40} {'ops/sec':>15} {'ms/op':>12}")
        print(f"  {'-'*40} {'-'*15} {'-'*12}")
        
        for result in self.results:
            ms_per_op = result.us_per_op / 1000
            print(f"  {result.name:<40} {result.ops_per_sec:>15,.1f} {ms_per_op:>12.2f}")
        
        print(f"\n{self.BOLD}{'-'*80}{self.RESET}\n")


# =============================================================================
# Test Processes
# =============================================================================

class NoopProcess(Skprocess):
    """Minimal process for overhead testing."""
    def __init__(self):
        self.process_config.runs = 1

    def __run__(self):
        pass
    
    def __result__(self):
        return None


class ComputeProcess(Skprocess):
    """Process that does some computation."""
    def __init__(self, n):
        self.n = n
        self._result = None
        self.process_config.runs = 1
    
    def __run__(self):
        total = 0
        for i in range(self.n):
            total += i
        self._result = total
    
    def __result__(self):
        return self._result


class EchoProcess(Skprocess):
    """Process that round-trips tell/listen data."""
    def __init__(self, runs: int = 1):
        self.process_config.runs = runs
        self._result = None
    
    def __run__(self):
        data = self.listen()
        self.tell(data)
        self._result = data
    
    def __result__(self):
        return self._result


# =============================================================================
# Process Spawn Benchmarks
# =============================================================================

def benchmark_process_spawn():
    """Measure process spawn overhead."""
    runner = BenchmarkRunner("Skprocess Spawn Benchmarks")
    
    # Single process spawn
    iterations = 10
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        proc = NoopProcess()
        proc.start()
        proc.wait()
        proc.result()
    elapsed = stdlib_time.perf_counter() - start
    
    runner.bench_timed("Single Skprocess spawn+run", iterations, elapsed)
    
    return runner


# =============================================================================
# Pool Benchmarks
# =============================================================================

def benchmark_pool_map():
    """Measure Pool.map performance."""
    runner = BenchmarkRunner("Pool.map Benchmarks")
    
    pool = Pool(workers=4)
    
    # Map over small inputs
    inputs = list(range(8))
    
    iterations = 5
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        pool.map(ComputeProcess, inputs)
    elapsed = stdlib_time.perf_counter() - start
    
    runner.bench_timed("Pool.map(8 items)", iterations * len(inputs), elapsed)
    
    return runner


def benchmark_pool_imap():
    """Measure Pool.imap performance."""
    runner = BenchmarkRunner("Pool.imap Benchmarks")
    
    pool = Pool(workers=4)
    inputs = list(range(8))
    
    iterations = 5
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        list(pool.imap(ComputeProcess, inputs))
    elapsed = stdlib_time.perf_counter() - start
    
    runner.bench_timed("Pool.imap(8 items)", iterations * len(inputs), elapsed)
    
    return runner


def benchmark_pool_unordered_imap():
    """Measure Pool.unordered_imap performance."""
    runner = BenchmarkRunner("Pool.unordered_imap Benchmarks")
    
    pool = Pool(workers=4)
    inputs = list(range(8))
    
    iterations = 5
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        list(pool.unordered_imap(ComputeProcess, inputs))
    elapsed = stdlib_time.perf_counter() - start
    
    runner.bench_timed("Pool.unordered_imap(8 items)", iterations * len(inputs), elapsed)
    
    return runner


def benchmark_pool_star():
    """Measure Pool.star() performance."""
    runner = BenchmarkRunner("Pool.star Benchmarks")
    
    pool = Pool(workers=4)
    inputs = [(i,) for i in range(8)]
    
    iterations = 5
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        pool.star().map(ComputeProcess, inputs)
    elapsed = stdlib_time.perf_counter() - start
    
    runner.bench_timed("Pool.star().map(8 items)", iterations * len(inputs), elapsed)
    
    return runner


def benchmark_process_methods():
    """Measure process method overhead."""
    runner = BenchmarkRunner("Skprocess Method Benchmarks")
    
    iterations = 5
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        proc = NoopProcess()
        proc.start()
        proc.wait()
        proc.result()
    elapsed = stdlib_time.perf_counter() - start
    
    runner.bench_timed("Skprocess start/wait/result", iterations, elapsed)
    
    return runner


# =============================================================================
# tell/listen Benchmarks
# =============================================================================

def benchmark_tell_listen():
    """Measure tell/listen round-trip throughput."""
    runner = BenchmarkRunner("tell/listen Benchmarks")
    
    iterations = 10
    proc = EchoProcess(runs=iterations)
    
    start = stdlib_time.perf_counter()
    proc.start()
    for i in range(iterations):
        proc.tell(i)
        proc.listen()
    proc.wait()
    elapsed = stdlib_time.perf_counter() - start
    
    runner.bench_timed("tell+listen roundtrip", iterations, elapsed)
    
    return runner


# =============================================================================
# Share Benchmarks
# =============================================================================

def benchmark_share_primitives():
    """Measure Share set/get overhead for primitives."""
    runner = BenchmarkRunner("Share Primitive Benchmarks")
    
    iterations = 100
    with Share() as share:
        start = stdlib_time.perf_counter()
        for i in range(iterations):
            share.counter = i
        elapsed = stdlib_time.perf_counter() - start
        runner.bench_timed("Share set int", iterations, elapsed)
        
        share.counter = 0
        start = stdlib_time.perf_counter()
        for _ in range(iterations):
            _ = share.counter
        elapsed = stdlib_time.perf_counter() - start
        runner.bench_timed("Share get int", iterations, elapsed)
    
    return runner


def benchmark_share_proxy():
    """Measure Share proxy overhead for suitkaise objects."""
    runner = BenchmarkRunner("Share Proxy Benchmarks")
    
    iterations = 50
    with Share() as share:
        share.timer = Sktimer()
        
        start = stdlib_time.perf_counter()
        for _ in range(iterations):
            share.timer.add_time(1.0)
        elapsed = stdlib_time.perf_counter() - start
        runner.bench_timed("Share proxy add_time", iterations, elapsed)
        
        start = stdlib_time.perf_counter()
        for _ in range(iterations):
            _ = share.timer.mean
        elapsed = stdlib_time.perf_counter() - start
        runner.bench_timed("Share proxy mean", iterations, elapsed)
    
    return runner


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_benchmarks():
    """Run all processing benchmarks."""
    print("\n" + "="*80)
    print(" PROCESSING MODULE BENCHMARKS ".center(80, "="))
    print("="*80)
    
    print("\nNote: Process benchmarks involve actual subprocess spawning.")
    print("Results will be slower than in-process operations.\n")
    
    runners = [
        benchmark_process_spawn(),
        benchmark_process_methods(),
        benchmark_tell_listen(),
        benchmark_pool_map(),
        benchmark_pool_imap(),
        benchmark_pool_unordered_imap(),
        benchmark_pool_star(),
        benchmark_share_primitives(),
        benchmark_share_proxy(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()
