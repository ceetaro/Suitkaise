"""
Run ALL Suitkaise Tests

Master script to run all test suites across all modules.

Usage:
    python tests/run_all_tests.py
"""

import sys
import time

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
BOLD = '\033[1m'
RESET = '\033[0m'
DIM = '\033[2m'


def run_unit_tests():
    """Run all unit test suites."""
    results = []
    
    # 1. Timing
    print(f"  {CYAN}▸ timing{RESET}")
    try:
        from tests.timing.run_all_tests import run_all_tests as run_timing
        results.append(("timing", run_timing()))
    except Exception as e:
        print(f"    {RED}Error: {e}{RESET}")
        results.append(("timing", False))
    
    # 2. Circuits
    print(f"  {CYAN}▸ circuits{RESET}")
    try:
        from tests.circuits.run_all_tests import run_all_tests as run_circuits
        results.append(("circuits", run_circuits()))
    except Exception as e:
        print(f"    {RED}Error: {e}{RESET}")
        results.append(("circuits", False))
    
    # 3. Paths
    print(f"  {CYAN}▸ paths{RESET}")
    try:
        from tests.paths.run_all_tests import run_all_tests as run_paths
        results.append(("paths", run_paths()))
    except Exception as e:
        print(f"    {RED}Error: {e}{RESET}")
        results.append(("paths", False))
    
    # 4. Cerial
    print(f"  {CYAN}▸ cerial{RESET}")
    try:
        from tests.cerial.run_all_tests import run_all_tests as run_cerial
        results.append(("cerial", run_cerial()))
    except Exception as e:
        print(f"    {RED}Error: {e}{RESET}")
        results.append(("cerial", False))
    
    # 5. Processing
    print(f"  {CYAN}▸ processing{RESET}")
    try:
        from tests.processing.run_all_tests import run_all_tests as run_processing
        results.append(("processing", run_processing()))
    except Exception as e:
        print(f"    {RED}Error: {e}{RESET}")
        results.append(("processing", False))
    
    # 6. SK
    print(f"  {CYAN}▸ sk{RESET}")
    try:
        from tests.sk.run_all_tests import run_all_tests as run_sk
        results.append(("sk", run_sk()))
    except Exception as e:
        print(f"    {RED}Error: {e}{RESET}")
        results.append(("sk", False))
    
    return results


def run_real_world_tests():
    """Run all real-world integration test suites."""
    results = []
    
    try:
        from tests.integration.test_async_patterns import run_all_tests as run_async
        from tests.integration.test_data_pipeline import run_all_tests as run_pipeline
        from tests.integration.test_async_web_scraper import run_all_tests as run_scraper
        from tests.integration.test_parallel_processing import run_all_tests as run_parallel
        from tests.integration.test_path_utilities import run_all_tests as run_paths
        
        print(f"\n  {MAGENTA}▸ Async Patterns{RESET}")
        results.append(("Async Patterns", run_async()))
        
        print(f"\n  {MAGENTA}▸ Data Pipeline{RESET}")
        results.append(("Data Pipeline", run_pipeline()))
        
        print(f"\n  {MAGENTA}▸ Async Web Scraper{RESET}")
        results.append(("Web Scraper", run_scraper()))
        
        print(f"\n  {MAGENTA}▸ Parallel Processing{RESET}")
        results.append(("Parallel Processing", run_parallel()))
        
        print(f"\n  {MAGENTA}▸ Path Utilities{RESET}")
        results.append(("Path Utilities", run_paths()))
        
    except Exception as e:
        print(f"    {RED}Error loading integration tests: {e}{RESET}")
        results.append(("integration", False))
    
    return results


def run_all_tests():
    """Run all test suites."""
    print()
    print(f"{BOLD}{CYAN}╔{'═'*78}╗{RESET}")
    print(f"{BOLD}{CYAN}║{'SUITKAISE - COMPLETE TEST SUITE':^78}║{RESET}")
    print(f"{BOLD}{CYAN}╚{'═'*78}╝{RESET}")
    print()
    
    start_time = time.perf_counter()
    
    # =========================================================================
    # SECTION 1: UNIT TESTS
    # =========================================================================
    print(f"{BOLD}{CYAN}┌{'─'*78}┐{RESET}")
    print(f"{BOLD}{CYAN}│{'SECTION 1: UNIT TESTS':^78}│{RESET}")
    print(f"{BOLD}{CYAN}│{DIM}{'Testing individual components in isolation':^78}{RESET}{BOLD}{CYAN}│{RESET}")
    print(f"{BOLD}{CYAN}└{'─'*78}┘{RESET}")
    print()
    
    unit_results = run_unit_tests()
    
    # =========================================================================
    # SECTION 2: REAL-WORLD INTEGRATION TESTS
    # =========================================================================
    print()
    print(f"{BOLD}{MAGENTA}┌{'─'*78}┐{RESET}")
    print(f"{BOLD}{MAGENTA}│{'SECTION 2: REAL-WORLD SCENARIOS':^78}│{RESET}")
    print(f"{BOLD}{MAGENTA}│{DIM}{'Testing how components work together in realistic use cases':^78}{RESET}{BOLD}{MAGENTA}│{RESET}")
    print(f"{BOLD}{MAGENTA}└{'─'*78}┘{RESET}")
    
    real_world_results = run_real_world_tests()
    
    elapsed = time.perf_counter() - start_time
    
    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print()
    print(f"{BOLD}{CYAN}╔{'═'*78}╗{RESET}")
    print(f"{BOLD}{CYAN}║{'FINAL SUMMARY':^78}║{RESET}")
    print(f"{BOLD}{CYAN}╠{'═'*78}╣{RESET}")
    
    # Unit test results
    print(f"{BOLD}{CYAN}║{RESET}  {BOLD}Unit Tests:{RESET}{' '*66}{BOLD}{CYAN}║{RESET}")
    unit_passed = 0
    unit_failed = 0
    for name, passed in unit_results:
        if passed:
            status = f"{GREEN}✓ PASS{RESET}"
            unit_passed += 1
        else:
            status = f"{RED}✗ FAIL{RESET}"
            unit_failed += 1
        line = f"    {status}  {name}"
        print(f"{BOLD}{CYAN}║{RESET}{line:<77}{BOLD}{CYAN}║{RESET}")
    
    print(f"{BOLD}{CYAN}║{RESET}{' '*78}{BOLD}{CYAN}║{RESET}")
    
    # Real-world test results
    print(f"{BOLD}{CYAN}║{RESET}  {BOLD}Real-World Scenarios:{RESET}{' '*56}{BOLD}{CYAN}║{RESET}")
    rw_passed = 0
    rw_failed = 0
    for name, passed in real_world_results:
        if passed:
            status = f"{GREEN}✓ PASS{RESET}"
            rw_passed += 1
        else:
            status = f"{RED}✗ FAIL{RESET}"
            rw_failed += 1
        line = f"    {status}  {name}"
        print(f"{BOLD}{CYAN}║{RESET}{line:<77}{BOLD}{CYAN}║{RESET}")
    
    print(f"{BOLD}{CYAN}╠{'═'*78}╣{RESET}")
    
    total_passed = unit_passed + rw_passed
    total_failed = unit_failed + rw_failed
    
    if total_failed == 0:
        summary = f"  {GREEN}{BOLD}All {total_passed} test suites passed!{RESET}"
    else:
        summary = f"  {YELLOW}Passed: {total_passed}{RESET}  |  {RED}Failed: {total_failed}{RESET}"
    
    print(f"{BOLD}{CYAN}║{RESET}{summary:<77}{BOLD}{CYAN}║{RESET}")
    print(f"{BOLD}{CYAN}║{RESET}  {DIM}Total time: {elapsed:.2f}s{RESET}{' '*(65-len(f'{elapsed:.2f}'))}{BOLD}{CYAN}║{RESET}")
    print(f"{BOLD}{CYAN}╚{'═'*78}╝{RESET}")
    print()
    
    return total_failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
