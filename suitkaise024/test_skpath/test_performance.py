"""
Performance Tests: @autopath decorator overhead

Compares the speed difference between using @autopath and not using it
on functions that accept path parameters.

Test configuration:
- 1 single string path parameter
- 3 list[str] path parameters with varying sizes

Sizes tested: 10, 100, 1000, 10000 items per list
"""

import time
import statistics
from pathlib import Path
from typing import Callable

# Import directly to avoid package-level import issues
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from suitkaise.skpath._int.autopath import autopath
from suitkaise.skpath._int.skpath import SKPath


# ============================================================================
# Test Functions
# ============================================================================

def process_without_autopath(
    single_path: str,
    paths_a: list[str],
    paths_b: list[str],
    paths_c: list[str],
) -> int:
    """Function without autopath - just counts all paths."""
    return 1 + len(paths_a) + len(paths_b) + len(paths_c)


@autopath()
def process_with_autopath(
    single_path: str,
    paths_a: list[str],
    paths_b: list[str],
    paths_c: list[str],
) -> int:
    """Function with autopath (all params) - normalizes all paths, then counts."""
    return 1 + len(paths_a) + len(paths_b) + len(paths_c)


@autopath(only="single_path")
def process_with_autopath_optimized(
    single_path: str,
    paths_a: list[str],
    paths_b: list[str],
    paths_c: list[str],
) -> int:
    """Function with autopath (only single_path) - only normalizes the single path."""
    return 1 + len(paths_a) + len(paths_b) + len(paths_c)


# ============================================================================
# Timing Utilities
# ============================================================================

def measure_time(func: Callable, *args, iterations: int = 10) -> dict:
    """
    Measure execution time of a function over multiple iterations.
    
    Returns dict with min, max, mean, median, and stdev in milliseconds.
    """
    times = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms
    
    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "total": sum(times),
    }


def generate_test_paths(count: int) -> list[str]:
    """Generate a list of fake path strings for testing."""
    return [f"project/module_{i}/subdir/file_{i}.py" for i in range(count)]


# ============================================================================
# Display Utilities
# ============================================================================

# ANSI colors
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def format_ms(ms: float) -> str:
    """Format milliseconds with appropriate precision."""
    if ms < 0.01:
        return f"{ms * 1000:.2f}μs"
    elif ms < 1:
        return f"{ms:.3f}ms"
    elif ms < 1000:
        return f"{ms:.2f}ms"
    else:
        return f"{ms / 1000:.2f}s"


def format_percentage(value: float, inverse: bool = False) -> str:
    """Format percentage with color based on value."""
    sign = "+" if value > 0 else ""
    if inverse:
        # For overhead, positive is bad (red), negative is good (green)
        color = RED if value > 50 else YELLOW if value > 10 else GREEN
    else:
        color = GREEN if value > 0 else YELLOW if value > -10 else RED
    return f"{color}{sign}{value:.1f}%{RESET}"


def print_header(title: str):
    """Print a section header."""
    print(f"\n{BOLD}{CYAN}{'=' * 70}{RESET}")
    print(f"{BOLD}{CYAN}{title.center(70)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 70}{RESET}\n")


def print_subheader(title: str):
    """Print a subsection header."""
    print(f"\n{BOLD}{title}{RESET}")
    print(f"{DIM}{'-' * 50}{RESET}")


# ============================================================================
# Performance Test Runner
# ============================================================================

def run_performance_test(size: int, iterations: int = 20) -> dict:
    """
    Run performance comparison for a given list size.
    
    Args:
        size: Number of paths in each list
        iterations: Number of times to run each function
        
    Returns:
        Dict with timing results and comparison metrics
    """
    # Generate test data
    single_path = "project/main/entry.py"
    paths_a = generate_test_paths(size)
    paths_b = generate_test_paths(size)
    paths_c = generate_test_paths(size)
    
    # Warm up (first run is often slower)
    process_without_autopath(single_path, paths_a, paths_b, paths_c)
    process_with_autopath(single_path, paths_a, paths_b, paths_c)
    process_with_autopath_optimized(single_path, paths_a, paths_b, paths_c)
    
    # Measure without autopath
    without_times = measure_time(
        process_without_autopath,
        single_path, paths_a, paths_b, paths_c,
        iterations=iterations,
    )
    
    # Measure with autopath (all params)
    with_times = measure_time(
        process_with_autopath,
        single_path, paths_a, paths_b, paths_c,
        iterations=iterations,
    )
    
    # Measure with autopath optimized (only single_path)
    optimized_times = measure_time(
        process_with_autopath_optimized,
        single_path, paths_a, paths_b, paths_c,
        iterations=iterations,
    )
    
    # Calculate comparison metrics for unoptimized
    overhead_ms = with_times["mean"] - without_times["mean"]
    overhead_pct = (overhead_ms / without_times["mean"]) * 100 if without_times["mean"] > 0 else 0
    
    # Calculate comparison metrics for optimized
    opt_overhead_ms = optimized_times["mean"] - without_times["mean"]
    opt_overhead_pct = (opt_overhead_ms / without_times["mean"]) * 100 if without_times["mean"] > 0 else 0
    
    # Speedup: how much faster is optimized vs unoptimized?
    speedup = with_times["mean"] / optimized_times["mean"] if optimized_times["mean"] > 0 else 0
    savings_pct = ((with_times["mean"] - optimized_times["mean"]) / with_times["mean"]) * 100 if with_times["mean"] > 0 else 0
    
    # Per-path overhead (total paths = 1 + 3 * size)
    total_paths = 1 + 3 * size
    per_path_overhead_us = (overhead_ms * 1000) / total_paths if total_paths > 0 else 0
    
    return {
        "size": size,
        "total_paths": total_paths,
        "iterations": iterations,
        "without": without_times,
        "with": with_times,
        "optimized": optimized_times,
        "overhead_ms": overhead_ms,
        "overhead_pct": overhead_pct,
        "opt_overhead_ms": opt_overhead_ms,
        "opt_overhead_pct": opt_overhead_pct,
        "speedup": speedup,
        "savings_pct": savings_pct,
        "per_path_overhead_us": per_path_overhead_us,
    }


def print_result(result: dict):
    """Print the result of a single performance test."""
    size = result["size"]
    total = result["total_paths"]
    
    print_subheader(f"List Size: {size:,} paths each ({total:,} total paths)")
    
    without = result["without"]
    with_ = result["with"]
    optimized = result["optimized"]
    
    # Timing comparison table
    print(f"  {'Metric':<16} {'No decorator':<16} {'@autopath()':<16} {'@autopath(only=...)':<20}")
    print(f"  {'-' * 70}")
    print(f"  {'Mean:':<16} {format_ms(without['mean']):<16} {format_ms(with_['mean']):<16} {format_ms(optimized['mean']):<20}")
    print(f"  {'Median:':<16} {format_ms(without['median']):<16} {format_ms(with_['median']):<16} {format_ms(optimized['median']):<20}")
    
    # Overhead summary
    print(f"\n  {BOLD}Comparison:{RESET}")
    print(f"    @autopath() overhead:            {format_ms(result['overhead_ms'])} ({format_percentage(result['overhead_pct'], inverse=True)})")
    print(f"    With only=... overhead:          {format_ms(result['opt_overhead_ms'])} ({format_percentage(result['opt_overhead_pct'], inverse=True)})")
    print(f"    {GREEN}Speedup with only=...:           {result['speedup']:.1f}x faster ({result['savings_pct']:.1f}% time saved){RESET}")


def print_summary(results: list[dict]):
    """Print a summary comparison across all sizes."""
    print_header("SUMMARY")
    
    # Table header
    print(f"  {'Size':<10} {'Paths':<10} {'No dec.':<12} {'@autopath':<12} {'only=...':<12} {'Speedup':<10}")
    print(f"  {'-' * 68}")
    
    for r in results:
        size_str = f"{r['size']:,}"
        total_str = f"{r['total_paths']:,}"
        without_str = format_ms(r['without']['mean'])
        with_str = format_ms(r['with']['mean'])
        opt_str = format_ms(r['optimized']['mean'])
        speedup_str = f"{GREEN}{r['speedup']:.1f}x{RESET}"
        
        print(f"  {size_str:<10} {total_str:<10} {without_str:<12} {with_str:<12} {opt_str:<12} {speedup_str:<10}")
    
    # Observations
    print(f"\n{BOLD}Key Takeaways:{RESET}")
    
    avg_speedup = statistics.mean(r['speedup'] for r in results)
    avg_savings = statistics.mean(r['savings_pct'] for r in results)
    
    print(f"  • Using {CYAN}only{RESET} gives {GREEN}{avg_speedup:.0f}x average speedup{RESET}")
    print(f"  • Average time savings: {GREEN}{avg_savings:.1f}%{RESET}")
    
    # Per-path overhead
    avg_per_path = statistics.mean(r['per_path_overhead_us'] for r in results)
    print(f"  • Per-path normalization cost: ~{avg_per_path:.0f}μs")
    
    # Recommendation
    print(f"\n{BOLD}Recommendation:{RESET}")
    print(f"  When functions have str/list[str] params that aren't file paths,")
    print(f"  use {CYAN}@autopath(only=['param1', 'param2']){RESET} to normalize only those params.")
    print(f"  This is especially impactful with large lists.")


# ============================================================================
# Main Test Entry Point
# ============================================================================

def test_autopath_performance():
    """Main performance test - runs all size comparisons."""
    print_header("@autopath Performance Test")
    
    print(f"{DIM}Testing function with 1 single path + 3 list[str] params{RESET}")
    print(f"{DIM}Each list contains N paths, measuring {BOLD}20 iterations{RESET}{DIM} per test{RESET}")
    
    sizes = [10, 100, 1000, 10000]
    results = []
    
    for size in sizes:
        result = run_performance_test(size, iterations=20)
        results.append(result)
        print_result(result)
    
    print_summary(results)
    
    print(f"\n{GREEN}✓ Performance test complete{RESET}\n")


if __name__ == "__main__":
    test_autopath_performance()

