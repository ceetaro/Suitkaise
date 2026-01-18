"""
Run All Timing Tests

Executes all test suites in the timing module.
"""

import sys
import os

# Add project root to path
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
RED = '\033[91m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'


def run_all_tests():
    """Run all timing module tests."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' TIMING MODULE - ALL TESTS ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    from tests.timing.test_timer import run_all_tests as run_timer_tests
    from tests.timing.test_timethis import run_all_tests as run_timethis_tests
    from tests.timing.test_timethis_context import run_all_tests as run_timethis_context_tests
    from tests.timing.test_functions import run_all_tests as run_functions_tests
    from tests.timing.test_decorators import run_all_tests as run_decorators_tests
    
    results = []
    
    print(f"\n{CYAN}Running Sktimer tests...{RESET}")
    results.append(("Sktimer", run_timer_tests()))
    
    print(f"\n{CYAN}Running @timethis Decorator tests...{RESET}")
    results.append(("@timethis Decorator", run_timethis_tests()))
    
    print(f"\n{CYAN}Running TimeThis Context tests...{RESET}")
    results.append(("TimeThis Context", run_timethis_context_tests()))
    
    print(f"\n{CYAN}Running Functions tests...{RESET}")
    results.append(("Functions", run_functions_tests()))
    
    print(f"\n{CYAN}Running Decorators tests...{RESET}")
    results.append(("Decorators", run_decorators_tests()))
    
    # Summary
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' SUMMARY ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    all_passed = True
    for name, passed in results:
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print(f"  {GREEN}{BOLD}All timing tests passed!{RESET}")
    else:
        print(f"  {RED}{BOLD}Some timing tests failed.{RESET}")
    
    print(f"\n{BOLD}{'='*80}{RESET}\n")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
