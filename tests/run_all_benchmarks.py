"""
Run ALL Suitkaise Benchmarks

Master script to run all benchmarks across all modules.

Usage:
    python tests/run_all_benchmarks.py
"""

import sys
import time

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

# Colors
GREEN = '\033[92m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'
DIM = '\033[2m'


def run_all_benchmarks():
    """Run all benchmark suites."""
    print()
    print(f"{BOLD}{CYAN}╔{'═'*78}╗{RESET}")
    print(f"{BOLD}{CYAN}║{'SUITKAISE - COMPLETE BENCHMARK SUITE':^78}║{RESET}")
    print(f"{BOLD}{CYAN}╚{'═'*78}╝{RESET}")
    print()
    
    start_time = time.perf_counter()
    
    # 1. Timing Benchmarks
    print(f"\n{BOLD}{CYAN}{'─'*80}{RESET}")
    print(f"{BOLD}TIMING MODULE{RESET}")
    print(f"{BOLD}{CYAN}{'─'*80}{RESET}")
    try:
        from tests.timing.benchmarks import run_all_benchmarks as run_timing
        run_timing()
    except Exception as e:
        print(f"  Error: {e}")
    
    # 2. Circuits Benchmarks
    print(f"\n{BOLD}{CYAN}{'─'*80}{RESET}")
    print(f"{BOLD}CIRCUITS MODULE{RESET}")
    print(f"{BOLD}{CYAN}{'─'*80}{RESET}")
    try:
        from tests.circuits.benchmarks import run_all_benchmarks as run_circuits
        run_circuits()
    except Exception as e:
        print(f"  Error: {e}")
    
    # 3. Paths Benchmarks
    print(f"\n{BOLD}{CYAN}{'─'*80}{RESET}")
    print(f"{BOLD}PATHS MODULE{RESET}")
    print(f"{BOLD}{CYAN}{'─'*80}{RESET}")
    try:
        from tests.paths.benchmarks import run_all_benchmarks as run_paths
        run_paths()
    except Exception as e:
        print(f"  Error: {e}")
    
    # 4. Cucumber Benchmarks
    print(f"\n{BOLD}{CYAN}{'─'*80}{RESET}")
    print(f"{BOLD}CUCUMBER MODULE{RESET}")
    print(f"{BOLD}{CYAN}{'─'*80}{RESET}")
    try:
        from tests.cucumber.benchmarks import run_all_benchmarks as run_cucumber
        run_cucumber()
    except Exception as e:
        print(f"  Error: {e}")
    
    # 5. Processing Benchmarks
    print(f"\n{BOLD}{CYAN}{'─'*80}{RESET}")
    print(f"{BOLD}PROCESSING MODULE{RESET}")
    print(f"{BOLD}{CYAN}{'─'*80}{RESET}")
    try:
        from tests.processing.benchmarks import run_all_benchmarks as run_processing
        run_processing()
    except Exception as e:
        print(f"  Error: {e}")
    
    # 6. SK Benchmarks
    print(f"\n{BOLD}{CYAN}{'─'*80}{RESET}")
    print(f"{BOLD}SK MODULE{RESET}")
    print(f"{BOLD}{CYAN}{'─'*80}{RESET}")
    try:
        from tests.sk.benchmarks import run_all_benchmarks as run_sk
        run_sk()
    except Exception as e:
        print(f"  Error: {e}")
    
    elapsed = time.perf_counter() - start_time
    
    # Summary
    print()
    print(f"{BOLD}{CYAN}╔{'═'*78}╗{RESET}")
    print(f"{BOLD}{CYAN}║{'BENCHMARKS COMPLETE':^78}║{RESET}")
    print(f"{BOLD}{CYAN}╠{'═'*78}╣{RESET}")
    print(f"{BOLD}{CYAN}║{RESET}  {GREEN}All benchmarks completed!{RESET}{' '*51}{BOLD}{CYAN}║{RESET}")
    print(f"{BOLD}{CYAN}║{RESET}  {DIM}Total time: {elapsed:.2f}s{RESET}{' '*(64-len(f'{elapsed:.2f}'))}{BOLD}{CYAN}║{RESET}")
    print(f"{BOLD}{CYAN}╚{'═'*78}╝{RESET}")
    print()


if __name__ == '__main__':
    run_all_benchmarks()
