"""
Sk Module Benchmarks

Performance benchmarks for:
- Skclass wrapping overhead
- Skfunction call overhead
- AST analysis speed
"""

import sys
import time as stdlib_time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.sk import Skclass, Skfunction, sk


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
# Test Classes and Functions
# =============================================================================

class SimpleCounter:
    def __init__(self):
        self.value = 0
    
    def increment(self):
        self.value += 1
    
    def get_value(self):
        return self.value


class LargeClass:
    """Class with many methods for AST analysis testing."""
    def __init__(self):
        self.a = 0
        self.b = 0
        self.c = 0
        self.d = 0
        self.e = 0
    
    def method1(self): self.a = 1
    def method2(self): self.b = 2
    def method3(self): self.c = 3
    def method4(self): self.d = 4
    def method5(self): self.e = 5
    def method6(self): self.a = self.b = 1
    def method7(self): self.c = self.d = 2
    def method8(self): return self.a + self.b
    def method9(self): return self.c + self.d
    def method10(self): return self.a + self.b + self.c + self.d + self.e


def simple_add(a, b):
    return a + b


def complex_function(a, b, c=0, d=0, e=0):
    result = a + b
    if c:
        result += c
    if d:
        result *= d
    return result + e


# =============================================================================
# Skclass Benchmarks
# =============================================================================

def benchmark_skclass_wrap():
    """Measure Skclass wrapping overhead (includes AST analysis)."""
    runner = BenchmarkRunner("Skclass Wrapping Benchmarks")
    
    # Simple class
    runner.bench("Skclass(SimpleCounter) [3 methods]", 1000, Skclass, SimpleCounter)
    
    # Large class
    runner.bench("Skclass(LargeClass) [10 methods]", 500, Skclass, LargeClass)
    
    return runner


def benchmark_skclass_instantiate():
    """Measure Skclass instance creation overhead."""
    runner = BenchmarkRunner("Skclass Instantiation Benchmarks")
    
    SkCounter = Skclass(SimpleCounter)
    
    runner.bench("Skclass instance creation", 50_000, SkCounter)
    runner.bench("Raw class instance creation", 100_000, SimpleCounter)
    
    return runner


def benchmark_skclass_method_call():
    """Measure Skclass method call overhead."""
    runner = BenchmarkRunner("Skclass Method Call Benchmarks")
    
    SkCounter = Skclass(SimpleCounter)
    sk_counter = SkCounter()
    
    raw_counter = SimpleCounter()
    
    runner.bench("SkCounter.increment()", 100_000, sk_counter.increment)
    runner.bench("RawCounter.increment()", 100_000, raw_counter.increment)
    
    return runner


# =============================================================================
# Skfunction Benchmarks
# =============================================================================

def benchmark_skfunction_wrap():
    """Measure Skfunction wrapping overhead."""
    runner = BenchmarkRunner("Skfunction Wrapping Benchmarks")
    
    runner.bench("Skfunction(simple_add)", 5000, Skfunction, simple_add)
    runner.bench("Skfunction(complex_function)", 5000, Skfunction, complex_function)
    
    return runner


def benchmark_skfunction_call():
    """Measure Skfunction call overhead."""
    runner = BenchmarkRunner("Skfunction Call Benchmarks")
    
    sk_add = Skfunction(simple_add)
    
    runner.bench("Skfunction call", 100_000, sk_add, 1, 2)
    runner.bench("Raw function call", 100_000, simple_add, 1, 2)
    
    return runner


def benchmark_skfunction_modifiers():
    """Measure modifier creation overhead."""
    runner = BenchmarkRunner("Skfunction Modifier Benchmarks")
    
    sk_add = Skfunction(simple_add)
    
    def create_retry():
        return sk_add.retry(times=3)
    
    def create_timeout():
        return sk_add.timeout(1.0)
    
    def create_background():
        return sk_add.background()
    
    runner.bench("Skfunction.retry()", 10_000, create_retry)
    runner.bench("Skfunction.timeout()", 10_000, create_timeout)
    runner.bench("Skfunction.background()", 10_000, create_background)
    
    return runner


# =============================================================================
# @sk Decorator Benchmarks
# =============================================================================

def benchmark_sk_decorator():
    """Measure @sk decorator overhead."""
    runner = BenchmarkRunner("@sk Decorator Benchmarks")
    
    def create_sk_class():
        @sk
        class TempCounter:
            def __init__(self):
                self.value = 0
            def increment(self):
                self.value += 1
        return TempCounter
    
    def create_sk_function():
        @sk
        def temp_add(a, b):
            return a + b
        return temp_add
    
    runner.bench("@sk on class", 500, create_sk_class)
    runner.bench("@sk on function", 2000, create_sk_function)
    
    return runner


# =============================================================================
# Comparison Benchmarks
# =============================================================================

def benchmark_vs_raw():
    """Compare wrapped vs raw performance."""
    runner = BenchmarkRunner("Wrapped vs Raw Comparison")
    
    # Class comparison
    SkCounter = Skclass(SimpleCounter)
    sk_inst = SkCounter()
    raw_inst = SimpleCounter()
    
    runner.bench("SkCounter.increment()", 100_000, sk_inst.increment)
    runner.bench("Counter.increment()", 100_000, raw_inst.increment)
    
    # Function comparison
    sk_add = Skfunction(simple_add)
    
    runner.bench("Skfunction(add)(1, 2)", 100_000, sk_add, 1, 2)
    runner.bench("add(1, 2)", 100_000, simple_add, 1, 2)
    
    return runner


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_benchmarks():
    """Run all sk module benchmarks."""
    print("\n" + "="*80)
    print(" SK MODULE BENCHMARKS ".center(80, "="))
    print("="*80)
    
    runners = [
        benchmark_skclass_wrap(),
        benchmark_skclass_instantiate(),
        benchmark_skclass_method_call(),
        benchmark_skfunction_wrap(),
        benchmark_skfunction_call(),
        benchmark_skfunction_modifiers(),
        benchmark_sk_decorator(),
        benchmark_vs_raw(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()
