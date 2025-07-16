#!/usr/bin/env python3
"""
FIXED Performance Benchmark: FDL vs Rich

This benchmark focuses on CORE update efficiency rather than animation overhead.
Tests the actual bottlenecks and measures what matters for performance.

Key fixes:
1. Separate animation from core update tests
2. Measure CPU/memory during pure updates (no animation)
3. Test batching efficiency 
4. Proper output suppression
5. Focus on threading performance and update throughput
"""

import sys
import time
import threading
import psutil
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from contextlib import contextmanager, redirect_stdout, redirect_stderr
from io import StringIO

# Add project paths
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
objects_path = project_root / "suitkaise" / "_int" / "_fdl" / "objects"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(objects_path))

# Try to import Rich for comparison
try:
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.spinner import Spinner
    from rich.console import Console
    from rich.live import Live
    RICH_AVAILABLE = True
    print("✅ Rich imported for comparison")
except ImportError:
    RICH_AVAILABLE = False
    print("❌ Rich not available - install with: pip install rich")

# Import our implementations
try:
    from suitkaise._int._fdl.objects.progress_bars import _create_progress_bar as fdl_create_progress_bar
    from suitkaise._int._fdl.objects.spinners import _create_spinner as fdl_create_spinner, _stop_spinner as fdl_stop_spinner
    FDL_AVAILABLE = True
    print("✅ FDL components imported")
except ImportError as e:
    FDL_AVAILABLE = False
    print(f"❌ FDL components not available: {e}")
    sys.exit(1)


@dataclass
class BenchmarkResult:
    """Results from a single benchmark test."""
    name: str
    implementation: str
    updates_per_second: float
    cpu_percent: float
    memory_mb: float
    duration: float
    total_updates: int
    notes: str = ""


@contextmanager
def proper_output_suppression():
    """Properly suppress all output during benchmarks."""
    # Create string buffers for output
    stdout_buffer = StringIO()
    stderr_buffer = StringIO()
    
    # Save original stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        # Redirect to buffers
        sys.stdout = stdout_buffer
        sys.stderr = stderr_buffer
        yield
    finally:
        # Restore original
        sys.stdout = original_stdout
        sys.stderr = original_stderr


class PerformanceMonitor:
    """Lightweight performance monitoring."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.start_cpu_time = None
        self.start_memory = None
    
    def start(self):
        """Start monitoring."""
        self.start_time = time.time()
        self.start_cpu_time = self.process.cpu_times()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024
    
    def stop(self) -> Tuple[float, float, float]:
        """Stop monitoring and return duration, CPU%, memory MB."""
        end_time = time.time()
        end_cpu_time = self.process.cpu_times()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        
        duration = end_time - self.start_time
        cpu_used = (end_cpu_time.user - self.start_cpu_time.user) + \
                   (end_cpu_time.system - self.start_cpu_time.system)
        cpu_percent = (cpu_used / duration) * 100 if duration > 0 else 0
        
        return duration, cpu_percent, end_memory


class CoreUpdateBenchmark:
    """Test core update performance without animation overhead."""
    
    def benchmark_fdl_core_updates(self, total_updates: int) -> BenchmarkResult:
        """Benchmark FDL core update performance (no animation)."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        with proper_output_suppression():
            # Create progress bar but DON'T start animation
            bar = fdl_create_progress_bar(total_updates, "blue")
            
            # Pure update test - no animation, no display
            for i in range(total_updates):
                bar.update(1)
                # Don't call tick() or display - pure logical updates only
        
        duration, cpu_percent, memory_mb = monitor.stop()
        
        return BenchmarkResult(
            name=f"Core Updates ({total_updates})",
            implementation="FDL",
            updates_per_second=total_updates / duration,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            duration=duration,
            total_updates=total_updates,
            notes="Pure logical updates, no animation"
        )
    
    def benchmark_rich_core_updates(self, total_updates: int) -> Optional[BenchmarkResult]:
        """Benchmark Rich core update performance."""
        if not RICH_AVAILABLE:
            return None
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        with proper_output_suppression():
            console = Console(file=StringIO())  # Use string buffer instead of /dev/null
            
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console,
                refresh_per_second=1  # Minimal refresh for pure update test
            ) as progress:
                task = progress.add_task("Test", total=total_updates)
                
                # Pure update test
                for i in range(total_updates):
                    progress.update(task, advance=1)
        
        duration, cpu_percent, memory_mb = monitor.stop()
        
        return BenchmarkResult(
            name=f"Core Updates ({total_updates})",
            implementation="Rich",
            updates_per_second=total_updates / duration,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            duration=duration,
            total_updates=total_updates,
            notes="Pure logical updates, minimal refresh"
        )


class BatchingBenchmark:
    """Test batching efficiency."""
    
    def benchmark_fdl_batching(self, batch_size: int, num_batches: int) -> BenchmarkResult:
        """Test FDL batching performance."""
        total_updates = batch_size * num_batches
        monitor = PerformanceMonitor()
        monitor.start()
        
        with proper_output_suppression():
            bar = fdl_create_progress_bar(total_updates, "green")
            
            # Batched updates
            for batch in range(num_batches):
                bar.update(batch_size)
                # Small delay between batches to simulate real usage
                time.sleep(0.001)
        
        duration, cpu_percent, memory_mb = monitor.stop()
        
        return BenchmarkResult(
            name=f"Batching {num_batches}x{batch_size}",
            implementation="FDL",
            updates_per_second=total_updates / duration,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            duration=duration,
            total_updates=total_updates,
            notes=f"Batched updates: {batch_size} per batch"
        )
    
    def benchmark_rich_batching(self, batch_size: int, num_batches: int) -> Optional[BenchmarkResult]:
        """Test Rich batching performance."""
        if not RICH_AVAILABLE:
            return None
        
        total_updates = batch_size * num_batches
        monitor = PerformanceMonitor()
        monitor.start()
        
        with proper_output_suppression():
            console = Console(file=StringIO())
            
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console,
                refresh_per_second=10
            ) as progress:
                task = progress.add_task("Test", total=total_updates)
                
                # Batched updates
                for batch in range(num_batches):
                    progress.update(task, advance=batch_size)
                    time.sleep(0.001)
        
        duration, cpu_percent, memory_mb = monitor.stop()
        
        return BenchmarkResult(
            name=f"Batching {num_batches}x{batch_size}",
            implementation="Rich",
            updates_per_second=total_updates / duration,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            duration=duration,
            total_updates=total_updates,
            notes=f"Batched updates: {batch_size} per batch"
        )


class ThreadingBenchmark:
    """Test threading efficiency with proper isolation."""
    
    def benchmark_fdl_threading(self, num_threads: int, updates_per_thread: int) -> BenchmarkResult:
        """Test FDL threading without animation overhead."""
        total_updates = num_threads * updates_per_thread
        monitor = PerformanceMonitor()
        
        with proper_output_suppression():
            bar = fdl_create_progress_bar(total_updates, "red")
            
            # Start timing after setup
            monitor.start()
            
            def worker():
                for i in range(updates_per_thread):
                    bar.update(1)
                    # Minimal delay to simulate work
                    time.sleep(0.0001)
            
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=worker)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
        
        duration, cpu_percent, memory_mb = monitor.stop()
        
        return BenchmarkResult(
            name=f"Threading {num_threads}x{updates_per_thread}",
            implementation="FDL",
            updates_per_second=total_updates / duration,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            duration=duration,
            total_updates=total_updates,
            notes=f"No animation overhead"
        )
    
    def benchmark_rich_threading(self, num_threads: int, updates_per_thread: int) -> Optional[BenchmarkResult]:
        """Test Rich threading."""
        if not RICH_AVAILABLE:
            return None
        
        total_updates = num_threads * updates_per_thread
        monitor = PerformanceMonitor()
        
        with proper_output_suppression():
            console = Console(file=StringIO())
            
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                console=console,
                refresh_per_second=10
            ) as progress:
                task = progress.add_task("Test", total=total_updates)
                
                # Start timing after setup
                monitor.start()
                
                def worker():
                    for i in range(updates_per_thread):
                        progress.update(task, advance=1)
                        time.sleep(0.0001)
                
                threads = []
                for i in range(num_threads):
                    t = threading.Thread(target=worker)
                    threads.append(t)
                    t.start()
                
                for t in threads:
                    t.join()
        
        duration, cpu_percent, memory_mb = monitor.stop()
        
        return BenchmarkResult(
            name=f"Threading {num_threads}x{updates_per_thread}",
            implementation="Rich",
            updates_per_second=total_updates / duration,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            duration=duration,
            total_updates=total_updates,
            notes="Standard Rich threading"
        )


class MemoryLeakTest:
    """Test for memory leaks during intensive usage."""
    
    def test_fdl_memory_stability(self, iterations: int) -> BenchmarkResult:
        """Test FDL memory stability over many iterations."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        with proper_output_suppression():
            for i in range(iterations):
                bar = fdl_create_progress_bar(100, "purple")
                for j in range(100):
                    bar.update(1)
                bar.stop()
                # Force garbage collection periodically
                if i % 100 == 0:
                    import gc
                    gc.collect()
        
        duration, cpu_percent, memory_mb = monitor.stop()
        
        return BenchmarkResult(
            name=f"Memory Stability ({iterations} iterations)",
            implementation="FDL",
            updates_per_second=(iterations * 100) / duration,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            duration=duration,
            total_updates=iterations * 100,
            notes="Create/destroy cycles"
        )


def run_focused_benchmark():
    """Run focused performance tests that isolate bottlenecks."""
    print("\n🎯 FOCUSED PERFORMANCE BENCHMARK")
    print("=" * 60)
    print("Testing core update efficiency (no animation overhead)")
    
    results = []
    
    # 1. Core Update Performance
    print("\n⚡ CORE UPDATE TESTS")
    print("-" * 30)
    
    core_bench = CoreUpdateBenchmark()
    
    for updates in [1000, 5000, 10000]:
        print(f"Testing {updates} core updates...")
        
        fdl_result = core_bench.benchmark_fdl_core_updates(updates)
        results.append(fdl_result)
        
        rich_result = core_bench.benchmark_rich_core_updates(updates)
        if rich_result:
            results.append(rich_result)
        
        print(f"  FDL:  {fdl_result.updates_per_second:6.0f} ups, {fdl_result.cpu_percent:4.1f}% CPU")
        if rich_result:
            print(f"  Rich: {rich_result.updates_per_second:6.0f} ups, {rich_result.cpu_percent:4.1f}% CPU")
            speedup = fdl_result.updates_per_second / rich_result.updates_per_second
            cpu_ratio = rich_result.cpu_percent / fdl_result.cpu_percent if fdl_result.cpu_percent > 0 else 1
            print(f"  📊 FDL is {speedup:.1f}x faster, uses {cpu_ratio:.1f}x less CPU")
        print()
    
    # 2. Batching Performance
    print("\n📦 BATCHING TESTS")
    print("-" * 30)
    
    batch_bench = BatchingBenchmark()
    
    batch_tests = [
        (10, 100),    # Small batches
        (100, 50),    # Medium batches
        (500, 10),    # Large batches
    ]
    
    for batch_size, num_batches in batch_tests:
        print(f"Testing {num_batches} batches of {batch_size}...")
        
        fdl_result = batch_bench.benchmark_fdl_batching(batch_size, num_batches)
        results.append(fdl_result)
        
        rich_result = batch_bench.benchmark_rich_batching(batch_size, num_batches)
        if rich_result:
            results.append(rich_result)
        
        print(f"  FDL:  {fdl_result.updates_per_second:6.0f} ups, {fdl_result.cpu_percent:4.1f}% CPU")
        if rich_result:
            print(f"  Rich: {rich_result.updates_per_second:6.0f} ups, {rich_result.cpu_percent:4.1f}% CPU")
            speedup = fdl_result.updates_per_second / rich_result.updates_per_second
            print(f"  📊 FDL is {speedup:.1f}x faster")
        print()
    
    # 3. Threading Performance (focused)
    print("\n🧵 FOCUSED THREADING TESTS")
    print("-" * 30)
    
    thread_bench = ThreadingBenchmark()
    
    threading_tests = [
        (2, 500),
        (4, 250),
        (8, 125),
    ]
    
    for threads, updates in threading_tests:
        print(f"Testing {threads} threads × {updates} updates...")
        
        fdl_result = thread_bench.benchmark_fdl_threading(threads, updates)
        results.append(fdl_result)
        
        rich_result = thread_bench.benchmark_rich_threading(threads, updates)
        if rich_result:
            results.append(rich_result)
        
        print(f"  FDL:  {fdl_result.updates_per_second:6.0f} ups, {fdl_result.cpu_percent:4.1f}% CPU")
        if rich_result:
            print(f"  Rich: {rich_result.updates_per_second:6.0f} ups, {rich_result.cpu_percent:4.1f}% CPU")
            speedup = fdl_result.updates_per_second / rich_result.updates_per_second
            print(f"  📊 FDL is {speedup:.1f}x faster")
        print()
    
    # 4. Memory Stability Test
    print("\n💾 MEMORY STABILITY TEST")
    print("-" * 30)
    
    memory_test = MemoryLeakTest()
    fdl_memory = memory_test.test_fdl_memory_stability(500)
    results.append(fdl_memory)
    
    print(f"FDL Memory Test: {fdl_memory.updates_per_second:.0f} ups, {fdl_memory.memory_mb:.1f} MB")
    
    return results


def analyze_bottlenecks(results: List[BenchmarkResult]):
    """Analyze what's causing performance differences."""
    print("\n🔍 BOTTLENECK ANALYSIS")
    print("=" * 60)
    
    fdl_results = [r for r in results if r.implementation == "FDL"]
    rich_results = [r for r in results if r.implementation == "Rich"]
    
    if not rich_results:
        print("❌ Cannot compare - Rich not available")
        return
    
    # Group by test type
    core_fdl = [r for r in fdl_results if "Core Updates" in r.name]
    core_rich = [r for r in rich_results if "Core Updates" in r.name]
    
    batch_fdl = [r for r in fdl_results if "Batching" in r.name]
    batch_rich = [r for r in rich_results if "Batching" in r.name]
    
    thread_fdl = [r for r in fdl_results if "Threading" in r.name]
    thread_rich = [r for r in rich_results if "Threading" in r.name]
    
    def avg_performance(results_list):
        if not results_list:
            return 0, 0
        avg_ups = sum(r.updates_per_second for r in results_list) / len(results_list)
        avg_cpu = sum(r.cpu_percent for r in results_list) / len(results_list)
        return avg_ups, avg_cpu
    
    # Analyze each category
    print("\n📊 PERFORMANCE BY CATEGORY")
    print("-" * 40)
    
    if core_fdl and core_rich:
        fdl_ups, fdl_cpu = avg_performance(core_fdl)
        rich_ups, rich_cpu = avg_performance(core_rich)
        print(f"💡 Core Updates:")
        print(f"   FDL:  {fdl_ups:6.0f} ups, {fdl_cpu:4.1f}% CPU")
        print(f"   Rich: {rich_ups:6.0f} ups, {rich_cpu:4.1f}% CPU")
        print(f"   🎯 FDL is {fdl_ups/rich_ups:.1f}x faster")
    
    if batch_fdl and batch_rich:
        fdl_ups, fdl_cpu = avg_performance(batch_fdl)
        rich_ups, rich_cpu = avg_performance(batch_rich)
        print(f"📦 Batching:")
        print(f"   FDL:  {fdl_ups:6.0f} ups, {fdl_cpu:4.1f}% CPU")
        print(f"   Rich: {rich_ups:6.0f} ups, {rich_cpu:4.1f}% CPU")
        print(f"   🎯 FDL is {fdl_ups/rich_ups:.1f}x faster")
    
    if thread_fdl and thread_rich:
        fdl_ups, fdl_cpu = avg_performance(thread_fdl)
        rich_ups, rich_cpu = avg_performance(thread_rich)
        print(f"🧵 Threading:")
        print(f"   FDL:  {fdl_ups:6.0f} ups, {fdl_cpu:4.1f}% CPU")
        print(f"   Rich: {rich_ups:6.0f} ups, {rich_cpu:4.1f}% CPU")
        print(f"   🎯 FDL is {fdl_ups/rich_ups:.1f}x faster")
    
    # Identify bottlenecks
    print("\n🚨 BOTTLENECK IDENTIFICATION")
    print("-" * 40)
    
    bottlenecks = []
    
    if thread_fdl and thread_rich:
        fdl_thread_ups, _ = avg_performance(thread_fdl)
        rich_thread_ups, _ = avg_performance(thread_rich)
        if rich_thread_ups > fdl_thread_ups * 1.5:
            bottlenecks.append("Threading: Rich scales better with multiple threads")
    
    if core_fdl and core_rich:
        fdl_core_ups, _ = avg_performance(core_fdl)
        rich_core_ups, _ = avg_performance(core_rich)
        if rich_core_ups > fdl_core_ups * 1.2:
            bottlenecks.append("Core Updates: Rich has more efficient update logic")
    
    if bottlenecks:
        for bottleneck in bottlenecks:
            print(f"⚠️  {bottleneck}")
    else:
        print("✅ No major bottlenecks identified - FDL performs well!")
    
    print("\n💡 OPTIMIZATION RECOMMENDATIONS")
    print("-" * 40)
    
    if thread_fdl and thread_rich:
        fdl_thread_ups, _ = avg_performance(thread_fdl)
        rich_thread_ups, _ = avg_performance(thread_rich)
        if rich_thread_ups > fdl_thread_ups * 1.3:
            print("🔧 Consider optimizing FDL's locking strategy for better thread scaling")
            print("   - Use fewer locks or lock-free data structures")
            print("   - Batch updates before acquiring locks")
    
    print("🔧 Consider separating animation from core logic completely")
    print("🔧 Profile with py-spy or cProfile to find specific hot spots")


def main():
    """Run the focused benchmark suite."""
    print("🎯 FOCUSED FDL vs Rich Performance Benchmark")
    print("Testing core performance without animation overhead...")
    
    if not RICH_AVAILABLE:
        print("\n⚠️  WARNING: Rich not available for comparison")
        print("   Install with: pip install rich")
    
    print(f"\n🔧 Test Environment:")
    print(f"   Python: {sys.version.split()[0]}")
    print(f"   CPU Count: {psutil.cpu_count()}")
    
    try:
        results = run_focused_benchmark()
        analyze_bottlenecks(results)
        
        print(f"\n🎉 Focused Benchmark Complete!")
        print(f"   Tests run: {len(results)}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Benchmark interrupted")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()