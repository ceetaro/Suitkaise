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


class SleepProcess(Skprocess):
    """Process that sleeps for a fixed duration."""
    def __init__(self, duration: float):
        self.duration = duration
        self.process_config.runs = 1
    
    def __run__(self):
        stdlib_time.sleep(self.duration)
    
    def __result__(self):
        return None


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
# Share Cross-Process Benchmarks (the important ones)
# =============================================================================

class ShareIncrementProcess(Skprocess):
    """Process that increments a shared counter."""
    def __init__(self, share: Share, increments: int):
        self.share = share
        self.increments = increments
        self.process_config.runs = 1
    
    def __run__(self):
        for _ in range(self.increments):
            self.share.counter += 1
    
    def __result__(self):
        return self.increments


class ShareTimerProcess(Skprocess):
    """Process that uses a shared timer."""
    def __init__(self, share: Share, iterations: int):
        self.share = share
        self.iterations = iterations
        self.process_config.runs = 1
    
    def __run__(self):
        for _ in range(self.iterations):
            self.share.timer.start()
            # tiny bit of work
            _ = sum(range(100))
            self.share.timer.stop()
    
    def __result__(self):
        return self.iterations


def benchmark_share_cross_process():
    """Measure Share performance across actual subprocess boundaries."""
    runner = BenchmarkRunner("Share Cross-Process Benchmarks")
    
    # Single process incrementing shared counter
    increments = 50
    with Share() as share:
        share.counter = 0
        
        start = stdlib_time.perf_counter()
        proc = ShareIncrementProcess(share, increments)
        proc.start()
        proc.wait()
        proc.result()
        # Give coordinator time to process final writes
        stdlib_time.sleep(0.2)
        elapsed = stdlib_time.perf_counter() - start
        
        runner.bench_timed(f"Cross-process increment ({increments}x)", increments, elapsed)
        
        final = share.counter
        print(f"  [Single process: expected {increments}, got {final}]")
    
    # Multiple processes incrementing shared counter
    num_workers = 4
    increments_per_worker = 10
    with Share() as share:
        share.counter = 0
        
        pool = Pool(workers=num_workers)
        
        start = stdlib_time.perf_counter()
        pool.star().map(ShareIncrementProcess, [(share, increments_per_worker)] * num_workers)
        # Give coordinator time to process final writes
        stdlib_time.sleep(0.5)
        elapsed = stdlib_time.perf_counter() - start
        
        total_increments = num_workers * increments_per_worker
        runner.bench_timed(f"Cross-process increment ({num_workers} workers × {increments_per_worker})", total_increments, elapsed)
        
        final = share.counter
        print(f"  [Multi process: expected {total_increments}, got {final}]")
        
        pool.close()
    
    return runner


def benchmark_share_timer_cross_process():
    """Measure shared Sktimer across process boundaries."""
    runner = BenchmarkRunner("Share Timer Cross-Process Benchmarks")
    
    iterations = 20
    with Share() as share:
        share.timer = Sktimer()
        
        start = stdlib_time.perf_counter()
        proc = ShareTimerProcess(share, iterations)
        proc.start()
        proc.wait()
        proc.result()
        # Give coordinator time to process final writes
        stdlib_time.sleep(0.2)
        elapsed = stdlib_time.perf_counter() - start
        
        runner.bench_timed(f"Cross-process timer start/stop ({iterations}x)", iterations * 2, elapsed)
        
        recorded = share.timer.num_times
        print(f"  [Timer: expected {iterations} times, got {recorded}]")
    
    return runner


def benchmark_share_vs_baseline():
    """Compare Share overhead to baseline (no sharing)."""
    runner = BenchmarkRunner("Share vs Baseline Comparison")
    
    # Baseline: local variable increment (no sharing)
    iterations = 10000
    counter = 0
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        counter += 1
    elapsed = stdlib_time.perf_counter() - start
    runner.bench_timed("Baseline: local int increment", iterations, elapsed)
    
    # Share: same process, increment via Share
    iterations = 100
    with Share() as share:
        share.counter = 0
        
        start = stdlib_time.perf_counter()
        for _ in range(iterations):
            share.counter += 1
        elapsed = stdlib_time.perf_counter() - start
        runner.bench_timed("Share: same process increment", iterations, elapsed)
    
    # multiprocessing.Value baseline
    from multiprocessing import Value
    iterations = 100
    mp_counter = Value('i', 0)
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        mp_counter.value += 1
    elapsed = stdlib_time.perf_counter() - start
    runner.bench_timed("mp.Value: same process increment", iterations, elapsed)
    
    # multiprocessing.Manager.Value baseline  
    from multiprocessing import Manager
    iterations = 100
    manager = Manager()
    mgr_counter = manager.Value('i', 0)
    start = stdlib_time.perf_counter()
    for _ in range(iterations):
        mgr_counter.value += 1
    elapsed = stdlib_time.perf_counter() - start
    runner.bench_timed("Manager.Value: same process increment", iterations, elapsed)
    manager.shutdown()
    
    return runner


def benchmark_share_latency():
    """Measure Share read/write latency in detail."""
    runner = BenchmarkRunner("Share Latency Benchmarks")
    
    iterations = 100
    
    with Share() as share:
        share.value = 0
        
        # Write latency
        write_times = []
        for i in range(iterations):
            start = stdlib_time.perf_counter()
            share.value = i
            elapsed = stdlib_time.perf_counter() - start
            write_times.append(elapsed)
        
        avg_write = sum(write_times) / len(write_times)
        min_write = min(write_times)
        max_write = max(write_times)
        
        # Read latency (after writes settle)
        stdlib_time.sleep(0.1)  # let coordinator catch up
        
        read_times = []
        for _ in range(iterations):
            start = stdlib_time.perf_counter()
            _ = share.value
            elapsed = stdlib_time.perf_counter() - start
            read_times.append(elapsed)
        
        avg_read = sum(read_times) / len(read_times)
        min_read = min(read_times)
        max_read = max(read_times)
    
    # Report using custom format
    print(f"\n  Share Latency Details:")
    print(f"  {'Write latency (avg)':<40} {avg_write*1000:>12.3f} ms")
    print(f"  {'Write latency (min)':<40} {min_write*1000:>12.3f} ms")
    print(f"  {'Write latency (max)':<40} {max_write*1000:>12.3f} ms")
    print(f"  {'Read latency (avg)':<40} {avg_read*1000:>12.3f} ms")
    print(f"  {'Read latency (min)':<40} {min_read*1000:>12.3f} ms")
    print(f"  {'Read latency (max)':<40} {max_read*1000:>12.3f} ms")
    
    runner.bench_timed("Share write (avg)", iterations, sum(write_times))
    runner.bench_timed("Share read (avg)", iterations, sum(read_times))
    
    return runner


# =============================================================================
# Concurrency Benchmarks
# =============================================================================

def benchmark_concurrency_vs_multiprocessing():
    """Compare Skprocess vs base multiprocessing concurrency."""
    print("\n" + "-"*80)
    print(" Concurrency Comparison ".center(80, "-"))
    print("-"*80)
    
    workers = 6
    sleep_s = 0.1
    long_sleep_s = 3.0
    
    # Skprocess concurrent
    start = stdlib_time.perf_counter()
    procs = [SleepProcess(sleep_s) for _ in range(workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.wait()
    for p in procs:
        p.result()
    sk_concurrent = stdlib_time.perf_counter() - start
    
    # Skprocess sequential
    start = stdlib_time.perf_counter()
    for _ in range(workers):
        p = SleepProcess(sleep_s)
        p.start()
        p.wait()
        p.result()
    sk_sequential = stdlib_time.perf_counter() - start
    
    # Base multiprocessing concurrent
    import multiprocessing as mp
    start = stdlib_time.perf_counter()
    mp_procs = [mp.Process(target=stdlib_time.sleep, args=(sleep_s,)) for _ in range(workers)]
    for p in mp_procs:
        p.start()
    for p in mp_procs:
        p.join()
    mp_concurrent = stdlib_time.perf_counter() - start
    
    def _speedup(seq: float, conc: float) -> float:
        return (seq / conc) if conc > 0 else float("inf")
    
    print(f"Workers: {workers}, sleep: {sleep_s:.2f}s each\n")
    print(f"{'Scenario':<35} {'Elapsed (s)':>12} {'Speedup':>10}")
    print(f"{'-'*35} {'-'*12} {'-'*10}")
    print(f"{'Skprocess concurrent':<35} {sk_concurrent:>12.3f} {_speedup(sk_sequential, sk_concurrent):>10.2f}x")
    print(f"{'Skprocess sequential':<35} {sk_sequential:>12.3f} {'1.00x':>10}")
    print(f"{'multiprocessing concurrent':<35} {mp_concurrent:>12.3f} {_speedup(sk_sequential, mp_concurrent):>10.2f}x")
    print("-"*80 + "\n")

    # Longer workload comparison (concurrency only)
    print("\n" + "-"*80)
    print(" Concurrency Comparison (Long Workload) ".center(80, "-"))
    print("-"*80)

    start = stdlib_time.perf_counter()
    procs = [SleepProcess(long_sleep_s) for _ in range(workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.wait()
    for p in procs:
        p.result()
    sk_concurrent_long = stdlib_time.perf_counter() - start

    start = stdlib_time.perf_counter()
    mp_procs = [mp.Process(target=stdlib_time.sleep, args=(long_sleep_s,)) for _ in range(workers)]
    for p in mp_procs:
        p.start()
    for p in mp_procs:
        p.join()
    mp_concurrent_long = stdlib_time.perf_counter() - start

    print(f"Workers: {workers}, sleep: {long_sleep_s:.2f}s each\n")
    print(f"{'Scenario':<35} {'Elapsed (s)':>12}")
    print(f"{'-'*35} {'-'*12}")
    print(f"{'Skprocess concurrent':<35} {sk_concurrent_long:>12.3f}")
    print(f"{'multiprocessing concurrent':<35} {mp_concurrent_long:>12.3f}")
    print("-"*80 + "\n")


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
        benchmark_share_cross_process(),
        benchmark_share_timer_cross_process(),
        benchmark_share_vs_baseline(),
        benchmark_share_latency(),
    ]
    
    for runner in runners:
        runner.print_results()

    benchmark_concurrency_vs_multiprocessing()
    
    print("\n" + "="*80)
    print(" BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


def run_share_benchmarks_only():
    """Run only Share benchmarks for quick testing."""
    print("\n" + "="*80)
    print(" SHARE BENCHMARKS ".center(80, "="))
    print("="*80 + "\n")
    
    runners = [
        benchmark_share_primitives(),
        benchmark_share_proxy(),
        benchmark_share_cross_process(),
        benchmark_share_timer_cross_process(),
        benchmark_share_vs_baseline(),
        benchmark_share_latency(),
    ]
    
    for runner in runners:
        runner.print_results()
    
    print("\n" + "="*80)
    print(" SHARE BENCHMARKS COMPLETE ".center(80, "="))
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_benchmarks()
