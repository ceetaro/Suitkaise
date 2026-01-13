"""
Paths Module Benchmarks

Performance benchmarks for path operations:
- Skpath creation
- Path property access
- Root detection
"""

import sys
import time as stdlib_time
from pathlib import Path

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.paths import Skpath, get_project_root, is_valid_filename, streamline_path


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
    
    def bench(self, name: str, iterations: int, func, *args, **kwargs):
        for _ in range(min(100, iterations // 10)):
            func(*args, **kwargs)
        
        start = stdlib_time.perf_counter()
        for _ in range(iterations):
            func(*args, **kwargs)
        elapsed = stdlib_time.perf_counter() - start
        
        ops_per_sec = iterations / elapsed
        us_per_op = (elapsed / iterations) * 1_000_000
        
        self.results.append(Benchmark(name, ops_per_sec, us_per_op))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*80}{self.RESET}\n")
        
        print(f"  {'Benchmark':<40} {'ops/sec':>15} {'µs/op':>12}")
        print(f"  {'-'*40} {'-'*15} {'-'*12}")
        
        for result in self.results:
            print(f"  {result.name:<40} {result.ops_per_sec:>15,.0f} {result.us_per_op:>12.3f}")
        
        print(f"\n{self.BOLD}{'-'*80}{self.RESET}\n")


# =============================================================================
# Skpath Creation Benchmarks
# =============================================================================

def benchmark_skpath_creation():
    """Measure Skpath creation overhead."""
    runner = BenchmarkRunner("Skpath Creation Benchmarks")
    
    runner.bench("Skpath(string)", 10_000, Skpath, "/path/to/file.txt")
    runner.bench("Skpath(Path)", 10_000, lambda: Skpath(Path("/path/to/file.txt")))
    runner.bench("Path(string) [stdlib]", 50_000, Path, "/path/to/file.txt")
    
    return runner


# =============================================================================
# Property Access Benchmarks
# =============================================================================

def benchmark_property_access():
    """Measure property access overhead."""
    runner = BenchmarkRunner("Skpath Property Benchmarks")
    
    path = Skpath("/Users/test/project/file.txt")
    stdlib_path = Path("/Users/test/project/file.txt")
    
    runner.bench("Skpath.name", 50_000, lambda: path.name)
    runner.bench("Path.name [stdlib]", 100_000, lambda: stdlib_path.name)
    
    runner.bench("Skpath.stem", 50_000, lambda: path.stem)
    runner.bench("Path.stem [stdlib]", 100_000, lambda: stdlib_path.stem)
    
    runner.bench("Skpath.suffix", 50_000, lambda: path.suffix)
    runner.bench("Path.suffix [stdlib]", 100_000, lambda: stdlib_path.suffix)
    
    runner.bench("Skpath.parent", 10_000, lambda: path.parent)
    runner.bench("Path.parent [stdlib]", 50_000, lambda: stdlib_path.parent)
    
    return runner


def benchmark_special_properties():
    """Measure Skpath-specific property access."""
    runner = BenchmarkRunner("Skpath Special Property Benchmarks")
    
    path = Skpath(__file__)
    
    runner.bench("Skpath.ap (absolute)", 10_000, lambda: path.ap)
    runner.bench("Skpath.id", 5_000, lambda: path.id)
    runner.bench("Skpath.rp (relative)", 5_000, lambda: path.rp)
    
    return runner


# =============================================================================
# Path Operations Benchmarks
# =============================================================================

def benchmark_path_operations():
    """Measure path operation overhead."""
    runner = BenchmarkRunner("Path Operations Benchmarks")
    
    path = Skpath("/path/to")
    stdlib_path = Path("/path/to")
    
    runner.bench("Skpath / 'subdir'", 10_000, lambda: path / "subdir")
    runner.bench("Path / 'subdir' [stdlib]", 50_000, lambda: stdlib_path / "subdir")
    
    existing_path = Skpath(__file__)
    existing_stdlib = Path(__file__)
    
    runner.bench("Skpath.exists()", 5_000, existing_path.exists)
    runner.bench("Path.exists() [stdlib]", 10_000, existing_stdlib.exists)
    
    return runner


# =============================================================================
# Root Detection Benchmarks
# =============================================================================

def benchmark_root_detection():
    """Measure root detection overhead."""
    runner = BenchmarkRunner("Root Detection Benchmarks")
    
    # First access (cold)
    path = Skpath(__file__)
    
    runner.bench("Skpath.root (cached)", 5_000, lambda: path.root)
    runner.bench("get_project_root()", 1_000, get_project_root)
    
    return runner


# =============================================================================
# Utility Benchmarks
# =============================================================================

def benchmark_utilities():
    """Measure utility function overhead."""
    runner = BenchmarkRunner("Path Utilities Benchmarks")
    
    runner.bench("is_valid_filename('file.txt')", 50_000, is_valid_filename, "file.txt")
    runner.bench("is_valid_filename('bad/file')", 50_000, is_valid_filename, "bad/file")
    
    runner.bench("streamline_path('My File.txt')", 10_000, streamline_path, "My File.txt")
    runner.bench("streamline_path(long, max_length=50)", 10_000, 
                 lambda: streamline_path("a" * 200, max_length=50))
    
    return runner


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_benchmarks():
    """Run all paths benchmarks."""
    print("\n" + "="*80)
    print(" PATHS MODULE BENCHMARKS ".center(80, "="))
    print("="*80)
    
    runners = [
        benchmark_skpath_creation(),
        benchmark_property_access(),
        benchmark_special_properties(),
        benchmark_path_operations(),
        benchmark_root_detection(),
        benchmark_utilities(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()
