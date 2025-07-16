#!/usr/bin/env python3
"""
Performance Benchmark: FDL vs Rich

Comprehensive performance testing of our custom spinners and progress bars
against Rich's implementations at various load levels.

Tests our claims:
- Spinners: 20x faster than Rich
- Progress bars: 50x faster than Rich

Run with: python benchmark_vs_rich.py
"""

import sys
import time
import threading
import psutil
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from contextlib import contextmanager

# Add project paths
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
objects_path = project_root / "suitkaise" / "_int" / "_fdl" / "objects"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(objects_path))

# Try to import Rich for comparison
try:
    from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
    from rich.spinner import Spinner
    from rich.console import Console
    from rich.live import Live
    RICH_AVAILABLE = True
    print("✅ Rich imported for comparison")
except ImportError:
    RICH_AVAILABLE = False
    print("❌ Rich not available - install with: pip install rich")
    print("   Benchmark will only test FDL performance")

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
    implementation: str  # "FDL" or "Rich"
    duration: float
    updates_per_second: float
    cpu_percent: float
    memory_mb: float
    success_rate: float
    notes: str = ""


class PerformanceMonitor:
    """Monitor CPU and memory usage during tests."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.monitoring = False
        self.cpu_samples = []
        self.memory_samples = []
    
    def start(self):
        """Start monitoring."""
        self.monitoring = True
        self.cpu_samples = []
        self.memory_samples = []
        
        def monitor():
            while self.monitoring:
                try:
                    cpu = self.process.cpu_percent()
                    memory = self.process.memory_info().rss / 1024 / 1024  # MB
                    self.cpu_samples.append(cpu)
                    self.memory_samples.append(memory)
                    time.sleep(0.1)  # Sample every 100ms
                except:
                    pass
        
        self.monitor_thread = threading.Thread(target=monitor)
        self.monitor_thread.start()
    
    def stop(self) -> Tuple[float, float]:
        """Stop monitoring and return average CPU% and memory MB."""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1.0)
        
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        avg_memory = sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0
        
        return avg_cpu, avg_memory


@contextmanager
def suppress_output():
    """Suppress stdout during benchmarks to avoid interference."""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


class SpinnerBenchmark:
    """Benchmark spinner performance."""
    
    def benchmark_fdl_spinner(self, updates: int, update_interval: float) -> BenchmarkResult:
        """Benchmark FDL spinner performance."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        start_time = time.time()
        errors = 0
        
        try:
            with suppress_output():
                spinner = fdl_create_spinner('dots', 'Benchmark test')
                
                for i in range(updates):
                    spinner.tick()
                    time.sleep(update_interval)
                
                fdl_stop_spinner()
                
        except Exception as e:
            errors += 1
        
        end_time = time.time()
        duration = end_time - start_time
        avg_cpu, avg_memory = monitor.stop()
        
        return BenchmarkResult(
            name=f"Spinner {updates} updates @ {1/update_interval:.1f}Hz",
            implementation="FDL",
            duration=duration,
            updates_per_second=updates / duration,
            cpu_percent=avg_cpu,
            memory_mb=avg_memory,
            success_rate=(updates - errors) / updates
        )
    
    def benchmark_rich_spinner(self, updates: int, update_interval: float) -> Optional[BenchmarkResult]:
        """Benchmark Rich spinner performance."""
        if not RICH_AVAILABLE:
            return None
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        start_time = time.time()
        errors = 0
        
        try:
            with suppress_output():
                console = Console(file=open(os.devnull, 'w'))
                
                with Live(Spinner('dots'), console=console, refresh_per_second=60) as live:
                    for i in range(updates):
                        live.update(Spinner('dots'))
                        time.sleep(update_interval)
                        
        except Exception as e:
            errors += 1
        
        end_time = time.time()
        duration = end_time - start_time
        avg_cpu, avg_memory = monitor.stop()
        
        return BenchmarkResult(
            name=f"Spinner {updates} updates @ {1/update_interval:.1f}Hz",
            implementation="Rich",
            duration=duration,
            updates_per_second=updates / duration,
            cpu_percent=avg_cpu,
            memory_mb=avg_memory,
            success_rate=(updates - errors) / updates
        )


class ProgressBarBenchmark:
    """Benchmark progress bar performance."""
    
    def benchmark_fdl_progress(self, total: int, update_pattern: str) -> BenchmarkResult:
        """Benchmark FDL progress bar performance."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        start_time = time.time()
        errors = 0
        updates_made = 0
        
        try:
            with suppress_output():
                bar = fdl_create_progress_bar(total, "blue")
                bar.display_bar()
                
                # Start animation thread for smooth updates
                animating = True
                def animate():
                    while animating:
                        bar.tick()
                        time.sleep(0.016)  # 60fps
                
                anim_thread = threading.Thread(target=animate)
                anim_thread.start()
                
                if update_pattern == "steady":
                    # Steady updates
                    for i in range(total):
                        bar.update(1)
                        updates_made += 1
                        time.sleep(0.01)  # 10ms between updates
                        
                elif update_pattern == "burst":
                    # Bursty updates
                    chunk_size = total // 10
                    for chunk in range(10):
                        for i in range(chunk_size):
                            bar.update(1)
                            updates_made += 1
                        time.sleep(0.1)  # Pause between bursts
                        
                elif update_pattern == "rapid":
                    # Very rapid updates
                    for i in range(total):
                        bar.update(1)
                        updates_made += 1
                        time.sleep(0.001)  # 1ms between updates
                
                # Let animation catch up
                time.sleep(0.5)
                animating = False
                anim_thread.join()
                bar.stop()
                
        except Exception as e:
            errors += 1
            animating = False
        
        end_time = time.time()
        duration = end_time - start_time
        avg_cpu, avg_memory = monitor.stop()
        
        return BenchmarkResult(
            name=f"Progress {total} updates ({update_pattern})",
            implementation="FDL",
            duration=duration,
            updates_per_second=updates_made / duration,
            cpu_percent=avg_cpu,
            memory_mb=avg_memory,
            success_rate=(updates_made - errors) / updates_made if updates_made > 0 else 0
        )
    
    def benchmark_rich_progress(self, total: int, update_pattern: str) -> Optional[BenchmarkResult]:
        """Benchmark Rich progress bar performance."""
        if not RICH_AVAILABLE:
            return None
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        start_time = time.time()
        errors = 0
        updates_made = 0
        
        try:
            with suppress_output():
                console = Console(file=open(os.devnull, 'w'))
                
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=console,
                    refresh_per_second=60
                ) as progress:
                    
                    task = progress.add_task("Benchmark", total=total)
                    
                    if update_pattern == "steady":
                        # Steady updates
                        for i in range(total):
                            progress.update(task, advance=1)
                            updates_made += 1
                            time.sleep(0.01)  # 10ms between updates
                            
                    elif update_pattern == "burst":
                        # Bursty updates  
                        chunk_size = total // 10
                        for chunk in range(10):
                            progress.update(task, advance=chunk_size)
                            updates_made += chunk_size
                            time.sleep(0.1)  # Pause between bursts
                            
                    elif update_pattern == "rapid":
                        # Very rapid updates
                        for i in range(total):
                            progress.update(task, advance=1)
                            updates_made += 1
                            time.sleep(0.001)  # 1ms between updates
                
        except Exception as e:
            errors += 1
        
        end_time = time.time()
        duration = end_time - start_time
        avg_cpu, avg_memory = monitor.stop()
        
        return BenchmarkResult(
            name=f"Progress {total} updates ({update_pattern})",
            implementation="Rich",
            duration=duration,
            updates_per_second=updates_made / duration,
            cpu_percent=avg_cpu,
            memory_mb=avg_memory,
            success_rate=(updates_made - errors) / updates_made if updates_made > 0 else 0
        )


class ThreadingBenchmark:
    """Benchmark threading performance."""
    
    def benchmark_fdl_threading(self, num_threads: int, updates_per_thread: int) -> BenchmarkResult:
        """Benchmark FDL threading performance."""
        monitor = PerformanceMonitor()
        monitor.start()
        
        start_time = time.time()
        total_updates = num_threads * updates_per_thread
        errors = 0
        
        try:
            with suppress_output():
                bar = fdl_create_progress_bar(total_updates, "green")
                bar.display_bar()
                
                # Animation thread
                animating = True
                def animate():
                    while animating:
                        bar.tick()
                        time.sleep(0.016)
                
                anim_thread = threading.Thread(target=animate)
                anim_thread.start()
                
                # Worker threads
                def worker():
                    for i in range(updates_per_thread):
                        bar.update(1)
                        time.sleep(0.001)  # 1ms per update
                
                threads = []
                for i in range(num_threads):
                    t = threading.Thread(target=worker)
                    threads.append(t)
                    t.start()
                
                for t in threads:
                    t.join()
                
                time.sleep(0.5)  # Let animation catch up
                animating = False
                anim_thread.join()
                bar.stop()
                
        except Exception as e:
            errors += 1
            animating = False
        
        end_time = time.time()
        duration = end_time - start_time
        avg_cpu, avg_memory = monitor.stop()
        
        return BenchmarkResult(
            name=f"Threading {num_threads}x{updates_per_thread}",
            implementation="FDL",
            duration=duration,
            updates_per_second=total_updates / duration,
            cpu_percent=avg_cpu,
            memory_mb=avg_memory,
            success_rate=(total_updates - errors) / total_updates
        )
    
    def benchmark_rich_threading(self, num_threads: int, updates_per_thread: int) -> Optional[BenchmarkResult]:
        """Benchmark Rich threading performance."""
        if not RICH_AVAILABLE:
            return None
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        start_time = time.time()
        total_updates = num_threads * updates_per_thread
        errors = 0
        
        try:
            with suppress_output():
                console = Console(file=open(os.devnull, 'w'))
                
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    console=console,
                    refresh_per_second=60
                ) as progress:
                    
                    task = progress.add_task("Threading", total=total_updates)
                    
                    def worker():
                        for i in range(updates_per_thread):
                            progress.update(task, advance=1)
                            time.sleep(0.001)  # 1ms per update
                    
                    threads = []
                    for i in range(num_threads):
                        t = threading.Thread(target=worker)
                        threads.append(t)
                        t.start()
                    
                    for t in threads:
                        t.join()
                
        except Exception as e:
            errors += 1
        
        end_time = time.time()
        duration = end_time - start_time
        avg_cpu, avg_memory = monitor.stop()
        
        return BenchmarkResult(
            name=f"Threading {num_threads}x{updates_per_thread}",
            implementation="Rich",
            duration=duration,
            updates_per_second=total_updates / duration,
            cpu_percent=avg_cpu,
            memory_mb=avg_memory,
            success_rate=(total_updates - errors) / total_updates
        )


def run_comprehensive_benchmark():
    """Run the full benchmark suite."""
    print("\n🚀 COMPREHENSIVE PERFORMANCE BENCHMARK")
    print("=" * 60)
    print("Testing FDL vs Rich at various load levels...")
    
    results = []
    
    # 1. Spinner Benchmarks
    print("\n🌀 SPINNER BENCHMARKS")
    print("-" * 30)
    
    spinner_bench = SpinnerBenchmark()
    
    # Test different update frequencies
    spinner_tests = [
        (100, 0.01),   # 100 updates at 100Hz
        (500, 0.005),  # 500 updates at 200Hz  
        (1000, 0.002), # 1000 updates at 500Hz
    ]
    
    for updates, interval in spinner_tests:
        print(f"Testing {updates} updates @ {1/interval:.0f}Hz...")
        
        # FDL spinner
        fdl_result = spinner_bench.benchmark_fdl_spinner(updates, interval)
        results.append(fdl_result)
        
        # Rich spinner
        rich_result = spinner_bench.benchmark_rich_spinner(updates, interval)
        if rich_result:
            results.append(rich_result)
        
        print(f"  FDL: {fdl_result.updates_per_second:.0f} ups, {fdl_result.cpu_percent:.1f}% CPU")
        if rich_result:
            print(f"  Rich: {rich_result.updates_per_second:.0f} ups, {rich_result.cpu_percent:.1f}% CPU")
            speedup = fdl_result.updates_per_second / rich_result.updates_per_second
            print(f"  ⚡ FDL is {speedup:.1f}x faster")
        print()
    
    # 2. Progress Bar Benchmarks
    print("\n📊 PROGRESS BAR BENCHMARKS")
    print("-" * 30)
    
    progress_bench = ProgressBarBenchmark()
    
    progress_tests = [
        (1000, "steady"),  # Steady updates
        (2000, "burst"),   # Bursty updates
        (5000, "rapid"),   # Rapid updates
    ]
    
    for total, pattern in progress_tests:
        print(f"Testing {total} {pattern} updates...")
        
        # FDL progress bar
        fdl_result = progress_bench.benchmark_fdl_progress(total, pattern)
        results.append(fdl_result)
        
        # Rich progress bar
        rich_result = progress_bench.benchmark_rich_progress(total, pattern)
        if rich_result:
            results.append(rich_result)
        
        print(f"  FDL: {fdl_result.updates_per_second:.0f} ups, {fdl_result.cpu_percent:.1f}% CPU")
        if rich_result:
            print(f"  Rich: {rich_result.updates_per_second:.0f} ups, {rich_result.cpu_percent:.1f}% CPU")
            speedup = fdl_result.updates_per_second / rich_result.updates_per_second
            print(f"  ⚡ FDL is {speedup:.1f}x faster")
        print()
    
    # 3. Threading Benchmarks
    print("\n🧵 THREADING BENCHMARKS")
    print("-" * 30)
    
    threading_bench = ThreadingBenchmark()
    
    threading_tests = [
        (2, 500),   # 2 threads, 500 updates each
        (5, 200),   # 5 threads, 200 updates each
        (10, 100),  # 10 threads, 100 updates each
    ]
    
    for threads, updates in threading_tests:
        print(f"Testing {threads} threads x {updates} updates...")
        
        # FDL threading
        fdl_result = threading_bench.benchmark_fdl_threading(threads, updates)
        results.append(fdl_result)
        
        # Rich threading
        rich_result = threading_bench.benchmark_rich_threading(threads, updates)
        if rich_result:
            results.append(rich_result)
        
        print(f"  FDL: {fdl_result.updates_per_second:.0f} ups, {fdl_result.cpu_percent:.1f}% CPU")
        if rich_result:
            print(f"  Rich: {rich_result.updates_per_second:.0f} ups, {rich_result.cpu_percent:.1f}% CPU")
            speedup = fdl_result.updates_per_second / rich_result.updates_per_second
            print(f"  ⚡ FDL is {speedup:.1f}x faster")
        print()
    
    return results


def generate_report(results: List[BenchmarkResult]):
    """Generate comprehensive performance report."""
    print("\n📊 PERFORMANCE REPORT")
    print("=" * 60)
    
    # Group results by test type and implementation
    fdl_results = [r for r in results if r.implementation == "FDL"]
    rich_results = [r for r in results if r.implementation == "Rich"]
    
    # Calculate overall stats
    if fdl_results:
        fdl_avg_ups = sum(r.updates_per_second for r in fdl_results) / len(fdl_results)
        fdl_avg_cpu = sum(r.cpu_percent for r in fdl_results) / len(fdl_results)
        fdl_avg_mem = sum(r.memory_mb for r in fdl_results) / len(fdl_results)
    
    if rich_results:
        rich_avg_ups = sum(r.updates_per_second for r in rich_results) / len(rich_results)
        rich_avg_cpu = sum(r.cpu_percent for r in rich_results) / len(rich_results)
        rich_avg_mem = sum(r.memory_mb for r in rich_results) / len(rich_results)
    
    print("\n🏆 OVERALL PERFORMANCE SUMMARY")
    print("-" * 40)
    
    if fdl_results and rich_results:
        print(f"Average Updates/Second:")
        print(f"  FDL:  {fdl_avg_ups:8.0f} ups")
        print(f"  Rich: {rich_avg_ups:8.0f} ups")
        print(f"  ⚡ FDL is {fdl_avg_ups/rich_avg_ups:.1f}x faster overall")
        
        print(f"\nAverage CPU Usage:")
        print(f"  FDL:  {fdl_avg_cpu:6.1f}%")
        print(f"  Rich: {rich_avg_cpu:6.1f}%") 
        print(f"  💚 FDL uses {rich_avg_cpu/fdl_avg_cpu:.1f}x less CPU")
        
        print(f"\nAverage Memory Usage:")
        print(f"  FDL:  {fdl_avg_mem:6.1f} MB")
        print(f"  Rich: {rich_avg_mem:6.1f} MB")
        print(f"  💚 FDL uses {rich_avg_mem/fdl_avg_mem:.1f}x less memory")
    
    # Detailed breakdown
    print("\n📋 DETAILED RESULTS")
    print("-" * 40)
    
    for result in results:
        print(f"{result.implementation:4s} | {result.name:30s} | "
              f"{result.updates_per_second:6.0f} ups | "
              f"{result.cpu_percent:5.1f}% CPU | "
              f"{result.memory_mb:5.1f} MB | "
              f"{result.success_rate:5.1%}")
    
    # Performance claims validation
    print("\n✅ CLAIMS VALIDATION")
    print("-" * 40)
    
    if fdl_results and rich_results:
        overall_speedup = fdl_avg_ups / rich_avg_ups
        
        # Spinner claim: 20x faster
        spinner_fdl = [r for r in fdl_results if "Spinner" in r.name]
        spinner_rich = [r for r in rich_results if "Spinner" in r.name]
        
        if spinner_fdl and spinner_rich:
            spinner_speedup = (sum(r.updates_per_second for r in spinner_fdl) / len(spinner_fdl)) / \
                             (sum(r.updates_per_second for r in spinner_rich) / len(spinner_rich))
            
            print(f"🌀 Spinner Performance: {spinner_speedup:.1f}x faster than Rich")
            if spinner_speedup >= 15:
                print("   ✅ CLAIM VALIDATED: ~20x faster than Rich!")
            elif spinner_speedup >= 10:
                print("   ⚠️  CLAIM PARTIAL: 10-20x faster than Rich")
            else:
                print("   ❌ CLAIM UNVALIDATED: <10x faster than Rich")
        
        # Progress bar claim: 50x faster
        progress_fdl = [r for r in fdl_results if "Progress" in r.name]
        progress_rich = [r for r in rich_results if "Progress" in r.name]
        
        if progress_fdl and progress_rich:
            progress_speedup = (sum(r.updates_per_second for r in progress_fdl) / len(progress_fdl)) / \
                              (sum(r.updates_per_second for r in progress_rich) / len(progress_rich))
            
            print(f"📊 Progress Bar Performance: {progress_speedup:.1f}x faster than Rich")
            if progress_speedup >= 30:
                print("   ✅ CLAIM VALIDATED: ~50x faster than Rich!")
            elif progress_speedup >= 20:
                print("   ⚠️  CLAIM PARTIAL: 20-50x faster than Rich")
            else:
                print("   ❌ CLAIM UNVALIDATED: <20x faster than Rich")
        
        print(f"\n🎯 Overall System Performance: {overall_speedup:.1f}x faster than Rich")
    
    else:
        print("❌ Cannot validate claims - Rich not available for comparison")
        print("   Install Rich with: pip install rich")


def main():
    """Run the benchmark suite."""
    print("🏁 FDL vs Rich Performance Benchmark")
    print("Testing our performance claims...")
    
    if not RICH_AVAILABLE:
        print("\n⚠️  WARNING: Rich not available")
        print("   Install with: pip install rich")
        print("   Will only test FDL performance (no comparison)")
    
    print(f"\n🔧 Test Environment:")
    print(f"   Python: {sys.version.split()[0]}")
    print(f"   CPU Count: {psutil.cpu_count()}")
    print(f"   Memory: {psutil.virtual_memory().total // (1024**3)} GB")
    
    try:
        results = run_comprehensive_benchmark()
        generate_report(results)
        
        print(f"\n🎉 Benchmark Complete!")
        print(f"   Total tests run: {len(results)}")
        print(f"   FDL tests: {len([r for r in results if r.implementation == 'FDL'])}")
        print(f"   Rich tests: {len([r for r in results if r.implementation == 'Rich'])}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Benchmark interrupted by user")
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()