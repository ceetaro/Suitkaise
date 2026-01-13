"""
Processing Module Benchmarks

Performance benchmarks for:
- Process spawn overhead
- Pool.map throughput
"""

import sys
import time as stdlib_time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.processing import Process, Pool


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

class NoopProcess(Process):
    """Minimal process for overhead testing."""
    def __run__(self):
        pass
    
    def __result__(self):
        return None


class ComputeProcess(Process):
    """Process that does some computation."""
    def __init__(self, n):
        self.n = n
        self._result = None
    
    def __run__(self):
        total = 0
        for i in range(self.n):
            total += i
        self._result = total
    
    def __result__(self):
        return self._result


# =============================================================================
# Process Spawn Benchmarks
# =============================================================================

def benchmark_process_spawn():
    """Measure process spawn overhead."""
    runner = BenchmarkRunner("Process Spawn Benchmarks")
    
    # Single process spawn
    iterations = 10
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        proc = NoopProcess()
        proc.start()
        proc.wait()
        proc.result()
    elapsed = stdlib_time.perf_counter() - start
    
    runner.bench_timed("Single Process spawn+run", iterations, elapsed)
    
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
        benchmark_pool_map(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()
