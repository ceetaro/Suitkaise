"""
Cerial Module Benchmarks

Performance benchmarks for serialization:
- Primitive serialization speed
- Complex object serialization speed
- Comparison with pickle
"""

import sys
import time as stdlib_time
import pickle
import threading
import logging

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.cerial import serialize, deserialize


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
# Test Data
# =============================================================================

class SimpleClass:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class ClassWithLock:
    def __init__(self, value):
        self.value = value
        self.lock = threading.Lock()


# =============================================================================
# Primitive Benchmarks
# =============================================================================

def benchmark_primitives():
    """Measure primitive serialization speed."""
    runner = BenchmarkRunner("Primitive Serialization Benchmarks")
    
    # Integer
    runner.bench("cerial: int", 10_000, lambda: serialize(42))
    runner.bench("pickle: int", 50_000, lambda: pickle.dumps(42))
    
    # String
    runner.bench("cerial: str", 10_000, lambda: serialize("hello world"))
    runner.bench("pickle: str", 50_000, lambda: pickle.dumps("hello world"))
    
    # List
    test_list = [1, 2, 3, 4, 5]
    runner.bench("cerial: list[5]", 5_000, lambda: serialize(test_list))
    runner.bench("pickle: list[5]", 20_000, lambda: pickle.dumps(test_list))
    
    # Dict
    test_dict = {"a": 1, "b": 2, "c": 3}
    runner.bench("cerial: dict[3]", 5_000, lambda: serialize(test_dict))
    runner.bench("pickle: dict[3]", 20_000, lambda: pickle.dumps(test_dict))
    
    return runner


def benchmark_deserialization():
    """Measure deserialization speed."""
    runner = BenchmarkRunner("Deserialization Benchmarks")
    
    # Pre-serialize data
    int_data = serialize(42)
    str_data = serialize("hello world")
    list_data = serialize([1, 2, 3, 4, 5])
    dict_data = serialize({"a": 1, "b": 2, "c": 3})
    
    int_pickle = pickle.dumps(42)
    str_pickle = pickle.dumps("hello world")
    list_pickle = pickle.dumps([1, 2, 3, 4, 5])
    
    runner.bench("cerial: deserialize int", 10_000, lambda: deserialize(int_data))
    runner.bench("pickle: loads int", 50_000, lambda: pickle.loads(int_pickle))
    
    runner.bench("cerial: deserialize str", 10_000, lambda: deserialize(str_data))
    runner.bench("pickle: loads str", 50_000, lambda: pickle.loads(str_pickle))
    
    runner.bench("cerial: deserialize list", 5_000, lambda: deserialize(list_data))
    runner.bench("pickle: loads list", 20_000, lambda: pickle.loads(list_pickle))
    
    return runner


# =============================================================================
# Complex Object Benchmarks
# =============================================================================

def benchmark_complex():
    """Measure complex object serialization speed."""
    runner = BenchmarkRunner("Complex Object Serialization Benchmarks")
    
    # Simple class (pickle can handle)
    simple = SimpleClass(1, 2)
    runner.bench("cerial: SimpleClass", 2_000, lambda: serialize(simple))
    runner.bench("pickle: SimpleClass", 10_000, lambda: pickle.dumps(simple))
    
    # Class with lock (pickle cannot handle)
    with_lock = ClassWithLock(42)
    runner.bench("cerial: ClassWithLock", 2_000, lambda: serialize(with_lock))
    # pickle.dumps(with_lock) would fail
    
    # Nested structure
    nested = {"data": [SimpleClass(i, i*2) for i in range(5)]}
    runner.bench("cerial: nested structure", 1_000, lambda: serialize(nested))
    runner.bench("pickle: nested structure", 5_000, lambda: pickle.dumps(nested))
    
    return runner


# =============================================================================
# Large Data Benchmarks
# =============================================================================

def benchmark_large_data():
    """Measure large data serialization speed."""
    runner = BenchmarkRunner("Large Data Serialization Benchmarks")
    
    # Large list
    large_list = list(range(1000))
    runner.bench("cerial: list[1000]", 500, lambda: serialize(large_list))
    runner.bench("pickle: list[1000]", 2_000, lambda: pickle.dumps(large_list))
    
    # Large dict
    large_dict = {str(i): i for i in range(500)}
    runner.bench("cerial: dict[500]", 200, lambda: serialize(large_dict))
    runner.bench("pickle: dict[500]", 1_000, lambda: pickle.dumps(large_dict))
    
    # Large string
    large_str = "x" * 10000
    runner.bench("cerial: str[10000]", 1_000, lambda: serialize(large_str))
    runner.bench("pickle: str[10000]", 5_000, lambda: pickle.dumps(large_str))
    
    return runner


# =============================================================================
# Round-Trip Benchmarks
# =============================================================================

def benchmark_roundtrip():
    """Measure full round-trip (serialize + deserialize)."""
    runner = BenchmarkRunner("Round-Trip Benchmarks")
    
    def cerial_roundtrip(obj):
        return deserialize(serialize(obj))
    
    def pickle_roundtrip(obj):
        return pickle.loads(pickle.dumps(obj))
    
    test_data = {"users": [{"name": f"user{i}", "age": 20 + i} for i in range(10)]}
    
    runner.bench("cerial: roundtrip dict", 500, lambda: cerial_roundtrip(test_data))
    runner.bench("pickle: roundtrip dict", 2_000, lambda: pickle_roundtrip(test_data))
    
    simple = SimpleClass(100, 200)
    runner.bench("cerial: roundtrip SimpleClass", 1_000, lambda: cerial_roundtrip(simple))
    runner.bench("pickle: roundtrip SimpleClass", 5_000, lambda: pickle_roundtrip(simple))
    
    return runner


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_benchmarks():
    """Run all cerial benchmarks."""
    print("\n" + "="*80)
    print(" CERIAL MODULE BENCHMARKS ".center(80, "="))
    print("="*80)
    
    runners = [
        benchmark_primitives(),
        benchmark_deserialization(),
        benchmark_complex(),
        benchmark_large_data(),
        benchmark_roundtrip(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()
