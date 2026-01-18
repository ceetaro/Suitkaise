"""
Run All Circuits Tests

Executes all test suites in the circuits module.
"""

import sys

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
    """Run all circuits module tests."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' CIRCUITS MODULE - ALL TESTS ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    from tests.circuits.test_circuit import run_all_tests as run_circuit_tests
    from tests.circuits.test_breaking_circuit import run_all_tests as run_breaking_tests
    from tests.circuits.test_async import run_all_tests as run_async_tests
    from tests.circuits.test_backoff import run_all_tests as run_backoff_tests
    
    results = []
    
    print(f"\n{CYAN}Running Circuit tests...{RESET}")
    results.append(("Circuit", run_circuit_tests()))
    
    print(f"\n{CYAN}Running BreakingCircuit tests...{RESET}")
    results.append(("BreakingCircuit", run_breaking_tests()))
    
    print(f"\n{CYAN}Running Async tests...{RESET}")
    results.append(("Async", run_async_tests()))
    
    print(f"\n{CYAN}Running Backoff tests...{RESET}")
    results.append(("Backoff", run_backoff_tests()))
    
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
        print(f"  {GREEN}{BOLD}All circuits tests passed!{RESET}")
    else:
        print(f"  {RED}{BOLD}Some circuits tests failed.{RESET}")
    
    print(f"\n{BOLD}{'='*80}{RESET}\n")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
