"""
Circuits Module Benchmarks

Performance benchmarks for circuit operations:
- short() throughput
- Backoff calculation overhead
- Comparison with manual implementations
"""

import sys
import time as stdlib_time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.circuits import Circuit, BreakingCircuit


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
        self.DIM = '\033[2m'
    
    def bench(self, name: str, iterations: int, func, *args, **kwargs):
        # Warmup
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
            if result.extra:
                print(f"  {self.DIM}  └─ {result.extra}{self.RESET}")
        
        print(f"\n{self.BOLD}{'-'*80}{self.RESET}\n")


# =============================================================================
# Circuit Creation Benchmarks
# =============================================================================

def benchmark_circuit_creation():
    """Measure Circuit creation overhead."""
    runner = BenchmarkRunner("Circuit Creation Benchmarks")
    
    runner.bench("Circuit(5)", 100_000, Circuit, 5)
    runner.bench("Circuit(5, 0.1, 1.5, 10.0)", 100_000, 
                 lambda: Circuit(5, sleep_time_after_trip=0.1, backoff_factor=1.5, max_sleep_time=10.0))
    runner.bench("BreakingCircuit(5)", 100_000, BreakingCircuit, 5)
    
    return runner


# =============================================================================
# Short Operation Benchmarks
# =============================================================================

def benchmark_circuit_short():
    """Measure Circuit.short() throughput (no trip)."""
    runner = BenchmarkRunner("Circuit.short() Benchmarks (no trip)")
    
    # Large threshold so we don't trip
    circ = Circuit(1_000_000, sleep_time_after_trip=0.0)
    runner.bench("Circuit.short()", 100_000, circ.short)
    
    breaking = BreakingCircuit(1_000_000, sleep_time_after_trip=0.0)
    runner.bench("BreakingCircuit.short()", 100_000, breaking.short)
    
    return runner


def benchmark_circuit_trip():
    """Measure Circuit.trip() overhead (with zero sleep)."""
    runner = BenchmarkRunner("Circuit.trip() Benchmarks (zero sleep)")
    
    circ = Circuit(10, sleep_time_after_trip=0.0)
    runner.bench("Circuit.trip()", 50_000, circ.trip)
    
    # BreakingCircuit trip (need to reset each time)
    def breaking_trip_cycle():
        b = BreakingCircuit(10, sleep_time_after_trip=0.0)
        b.trip()
    
    runner.bench("BreakingCircuit.trip() [new instance]", 20_000, breaking_trip_cycle)
    
    return runner


# =============================================================================
# Backoff Calculation Benchmarks
# =============================================================================

def benchmark_backoff_calculation():
    """Measure backoff calculation overhead."""
    runner = BenchmarkRunner("Backoff Calculation Benchmarks")
    
    # With backoff (factor > 1)
    circ_with = Circuit(1, sleep_time_after_trip=0.0, backoff_factor=1.5)
    runner.bench("Circuit.short() with backoff", 50_000, circ_with.short)
    
    # Without backoff (factor = 1)
    circ_without = Circuit(1, sleep_time_after_trip=0.0, backoff_factor=1.0)
    runner.bench("Circuit.short() no backoff", 50_000, circ_without.short)
    
    return runner


# =============================================================================
# Property Access Benchmarks
# =============================================================================

def benchmark_property_access():
    """Measure property access overhead."""
    runner = BenchmarkRunner("Property Access Benchmarks")
    
    circ = Circuit(100, sleep_time_after_trip=0.1, backoff_factor=1.5)
    for _ in range(50):
        circ.short()
    
    runner.bench("Circuit.times_shorted", 100_000, lambda: circ.times_shorted)
    runner.bench("Circuit.total_trips", 100_000, lambda: circ.total_trips)
    runner.bench("Circuit.current_sleep_time", 100_000, lambda: circ.current_sleep_time)
    
    breaking = BreakingCircuit(100, sleep_time_after_trip=0.1)
    for _ in range(50):
        breaking.short()
    
    runner.bench("BreakingCircuit.broken", 100_000, lambda: breaking.broken)
    runner.bench("BreakingCircuit.total_failures", 100_000, lambda: breaking.total_failures)
    
    return runner


# =============================================================================
# Comparison with Manual Implementation
# =============================================================================

def benchmark_vs_manual():
    """Compare Circuit with manual counter implementation."""
    runner = BenchmarkRunner("Circuit vs Manual Implementation")
    
    # Using Circuit
    circ = Circuit(1_000_000, sleep_time_after_trip=0.0)
    runner.bench("Circuit.short()", 100_000, circ.short)
    
    # Manual counter (simplified)
    class ManualCircuit:
        def __init__(self, threshold):
            self.threshold = threshold
            self.count = 0
        
        def short(self):
            self.count += 1
            if self.count >= self.threshold:
                self.count = 0
                return True
            return False
    
    manual = ManualCircuit(1_000_000)
    runner.bench("ManualCircuit.short()", 100_000, manual.short)
    
    # Just increment
    counter = [0]
    def just_increment():
        counter[0] += 1
    
    runner.bench("Pure increment", 100_000, just_increment)
    
    return runner


# =============================================================================
# reset_backoff Benchmark
# =============================================================================

def benchmark_reset_backoff():
    """Measure reset_backoff() overhead."""
    runner = BenchmarkRunner("reset_backoff() Benchmarks")
    
    circ = Circuit(1, sleep_time_after_trip=0.01, backoff_factor=1.5)
    for _ in range(10):
        circ.short()
    
    runner.bench("Circuit.reset_backoff()", 100_000, circ.reset_backoff)
    
    breaking = BreakingCircuit(1, sleep_time_after_trip=0.01, backoff_factor=1.5)
    breaking.short()
    
    runner.bench("BreakingCircuit.reset_backoff()", 100_000, breaking.reset_backoff)
    
    return runner


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_benchmarks():
    """Run all circuit benchmarks."""
    print("\n" + "="*80)
    print(" CIRCUITS MODULE BENCHMARKS ".center(80, "="))
    print("="*80)
    
    runners = [
        benchmark_circuit_creation(),
        benchmark_circuit_short(),
        benchmark_circuit_trip(),
        benchmark_backoff_calculation(),
        benchmark_property_access(),
        benchmark_vs_manual(),
        benchmark_reset_backoff(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()
