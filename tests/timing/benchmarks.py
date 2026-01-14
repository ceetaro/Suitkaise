"""
Timing Module Benchmarks

Performance benchmarks for timing operations:
- Sktimer overhead
- Statistics calculation speed
- sleep precision
"""

import sys
import time as stdlib_time
import asyncio

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.timing import Sktimer, TimeThis, time, sleep, elapsed


# =============================================================================
# Benchmark Infrastructure
# =============================================================================

class Benchmark:
    """Single benchmark result."""
    def __init__(self, name: str, ops_per_sec: float, us_per_op: float, extra: str = ""):
        self.name = name
        self.ops_per_sec = ops_per_sec
        self.us_per_op = us_per_op
        self.extra = extra


class BenchmarkRunner:
    """Run and display benchmarks."""
    
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        
        # ANSI colors
        self.GREEN = '\033[92m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
        self.DIM = '\033[2m'
    
    def bench(self, name: str, iterations: int, func, *args, **kwargs):
        """Run a benchmark."""
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
    
    def bench_with_extra(self, name: str, iterations: int, func, extra_func):
        """Run a benchmark with extra info callback."""
        # Warmup
        for _ in range(min(100, iterations // 10)):
            func()
        
        start = stdlib_time.perf_counter()
        for _ in range(iterations):
            func()
        elapsed = stdlib_time.perf_counter() - start
        
        ops_per_sec = iterations / elapsed
        us_per_op = (elapsed / iterations) * 1_000_000
        extra = extra_func() if extra_func else ""
        
        self.results.append(Benchmark(name, ops_per_sec, us_per_op, extra))
    
    def print_results(self):
        """Print benchmark results."""
        print(f"\n{self.BOLD}{self.CYAN}{'='*80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^80}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*80}{self.RESET}\n")
        
        # Header
        print(f"  {'Benchmark':<40} {'ops/sec':>15} {'µs/op':>12}")
        print(f"  {'-'*40} {'-'*15} {'-'*12}")
        
        for result in self.results:
            print(f"  {result.name:<40} {result.ops_per_sec:>15,.0f} {result.us_per_op:>12.3f}")
            if result.extra:
                print(f"  {self.DIM}  └─ {result.extra}{self.RESET}")
        
        print(f"\n{self.BOLD}{'-'*80}{self.RESET}\n")


# =============================================================================
# Sktimer Overhead Benchmarks
# =============================================================================

def benchmark_timer_creation():
    """Measure Sktimer creation overhead."""
    runner = BenchmarkRunner("Sktimer Creation Benchmarks")
    
    # Create timer
    runner.bench("Sktimer()", 100_000, Sktimer)
    
    return runner


def benchmark_timer_start_stop():
    """Measure Sktimer start/stop overhead."""
    runner = BenchmarkRunner("Sktimer Start/Stop Benchmarks")
    
    timer = Sktimer()
    
    def start_stop():
        timer.start()
        timer.stop()
    
    runner.bench("timer.start() + timer.stop()", 50_000, start_stop)
    
    # Just start
    timer2 = Sktimer()
    runner.bench("timer.start()", 100_000, timer2.start)
    
    # Just stop (after start)
    timer3 = Sktimer()
    for _ in range(100_000):
        timer3.start()
    runner.bench("timer.stop()", 100_000, timer3.stop)
    
    return runner


def benchmark_timer_add_time():
    """Measure Sktimer.add_time() overhead."""
    runner = BenchmarkRunner("Sktimer add_time Benchmarks")
    
    timer = Sktimer()
    runner.bench("timer.add_time(1.0)", 100_000, timer.add_time, 1.0)
    
    return runner


# =============================================================================
# Statistics Calculation Benchmarks
# =============================================================================

def benchmark_statistics_small():
    """Measure statistics with small dataset."""
    runner = BenchmarkRunner("Statistics Benchmarks (100 measurements)")
    
    timer = Sktimer()
    for i in range(100):
        timer.add_time(float(i))
    
    runner.bench("timer.mean", 50_000, lambda: timer.mean)
    runner.bench("timer.median", 50_000, lambda: timer.median)
    runner.bench("timer.stdev", 50_000, lambda: timer.stdev)
    runner.bench("timer.min", 50_000, lambda: timer.min)
    runner.bench("timer.max", 50_000, lambda: timer.max)
    runner.bench("timer.percentile(95)", 50_000, timer.percentile, 95)
    runner.bench("timer.get_statistics()", 10_000, timer.get_statistics)
    
    return runner


def benchmark_statistics_large():
    """Measure statistics with large dataset."""
    runner = BenchmarkRunner("Statistics Benchmarks (10,000 measurements)")
    
    timer = Sktimer()
    for i in range(10_000):
        timer.add_time(float(i))
    
    runner.bench("timer.mean", 10_000, lambda: timer.mean)
    runner.bench("timer.median", 1_000, lambda: timer.median)
    runner.bench("timer.stdev", 1_000, lambda: timer.stdev)
    runner.bench("timer.percentile(95)", 1_000, timer.percentile, 95)
    runner.bench("timer.get_statistics()", 500, timer.get_statistics)
    
    return runner


# =============================================================================
# Pause/Resume Benchmarks
# =============================================================================

def benchmark_pause_resume():
    """Measure pause/resume overhead."""
    runner = BenchmarkRunner("Pause/Resume Benchmarks")
    
    timer = Sktimer()
    timer.start()
    
    def pause_resume():
        timer.pause()
        timer.resume()
    
    runner.bench("timer.pause() + timer.resume()", 50_000, pause_resume)
    
    return runner


# =============================================================================
# Function Benchmarks
# =============================================================================

def benchmark_time_function():
    """Measure time() function overhead."""
    runner = BenchmarkRunner("time() Function Benchmarks")
    
    runner.bench("suitkaise time()", 100_000, time)
    runner.bench("stdlib time.time()", 100_000, stdlib_time.time)
    runner.bench("stdlib time.perf_counter()", 100_000, stdlib_time.perf_counter)
    
    return runner


def benchmark_elapsed_function():
    """Measure elapsed() function overhead."""
    runner = BenchmarkRunner("elapsed() Function Benchmarks")
    
    t1 = time()
    t2 = time()
    
    runner.bench("elapsed(t1, t2)", 100_000, elapsed, t1, t2)
    runner.bench("elapsed(t1)", 50_000, elapsed, t1)
    
    return runner


# =============================================================================
# Sleep Precision Benchmarks
# =============================================================================

def benchmark_sleep_precision():
    """Measure sleep precision."""
    runner = BenchmarkRunner("Sleep Precision Benchmarks")
    
    # Measure actual sleep time vs requested
    test_durations = [0.001, 0.005, 0.01, 0.05]
    
    for duration in test_durations:
        samples = []
        for _ in range(20):
            start = stdlib_time.perf_counter()
            sleep(duration)
            actual = stdlib_time.perf_counter() - start
            samples.append(actual)
        
        mean_actual = sum(samples) / len(samples)
        error_pct = ((mean_actual - duration) / duration) * 100
        
        result = Benchmark(
            f"sleep({duration}s)", 
            1 / mean_actual,
            mean_actual * 1_000_000,
            f"target: {duration*1000:.1f}ms, actual: {mean_actual*1000:.2f}ms, error: {error_pct:+.1f}%"
        )
        runner.results.append(result)
    
    return runner


# =============================================================================
# TimeThis Benchmarks
# =============================================================================

def benchmark_timethis():
    """Measure TimeThis context manager overhead."""
    runner = BenchmarkRunner("TimeThis Context Manager Benchmarks")
    
    timer = Sktimer()
    
    def with_timethis():
        with TimeThis(timer):
            pass
    
    runner.bench("with TimeThis(timer)", 50_000, with_timethis)
    
    def with_new_timethis():
        with TimeThis() as t:
            pass
    
    runner.bench("with TimeThis() [new timer]", 50_000, with_new_timethis)
    
    return runner


# =============================================================================
# Comparison with Manual Timing
# =============================================================================

def benchmark_vs_manual():
    """Compare Sktimer vs manual time.time() usage."""
    runner = BenchmarkRunner("Sktimer vs Manual Timing Comparison")
    
    # Using Sktimer
    timer = Sktimer()
    def with_timer():
        timer.start()
        # simulated work (nothing)
        timer.stop()
    
    runner.bench("Sktimer.start()/stop()", 50_000, with_timer)
    
    # Using manual time.time()
    manual_times = []
    def with_manual():
        start = stdlib_time.time()
        # simulated work (nothing)
        end = stdlib_time.time()
        manual_times.append(end - start)
    
    runner.bench("time.time() manual", 50_000, with_manual)
    
    # Using perf_counter
    perf_times = []
    def with_perf():
        start = stdlib_time.perf_counter()
        # simulated work (nothing)
        end = stdlib_time.perf_counter()
        perf_times.append(end - start)
    
    runner.bench("perf_counter() manual", 50_000, with_perf)
    
    return runner


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_benchmarks():
    """Run all timing benchmarks."""
    print("\n" + "="*80)
    print(" TIMING MODULE BENCHMARKS ".center(80, "="))
    print("="*80)
    
    runners = [
        benchmark_timer_creation(),
        benchmark_timer_start_stop(),
        benchmark_timer_add_time(),
        benchmark_statistics_small(),
        benchmark_statistics_large(),
        benchmark_pause_resume(),
        benchmark_time_function(),
        benchmark_elapsed_function(),
        benchmark_sleep_precision(),
        benchmark_timethis(),
        benchmark_vs_manual(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()
