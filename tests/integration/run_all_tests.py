"""
Run All Integration Tests

Executes all example-based integration suites.
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
    """Run all integration example tests."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' INTEGRATION EXAMPLES - ALL TESTS ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

    from tests.integration.test_examples_sk import run_all_tests as run_sk_tests
    from tests.integration.test_examples_processing import run_all_tests as run_processing_tests
    from tests.integration.test_examples_timing import run_all_tests as run_timing_tests
    from tests.integration.test_examples_circuits import run_all_tests as run_circuits_tests
    from tests.integration.test_examples_paths import run_all_tests as run_paths_tests

    results = []

    print(f"\n{CYAN}Running sk examples...{RESET}")
    results.append(("sk examples", run_sk_tests()))

    print(f"\n{CYAN}Running processing examples...{RESET}")
    results.append(("processing examples", run_processing_tests()))

    print(f"\n{CYAN}Running timing examples...{RESET}")
    results.append(("timing examples", run_timing_tests()))

    print(f"\n{CYAN}Running circuits examples...{RESET}")
    results.append(("circuits examples", run_circuits_tests()))

    print(f"\n{CYAN}Running paths examples...{RESET}")
    results.append(("paths examples", run_paths_tests()))

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
        print(f"  {GREEN}{BOLD}All integration tests passed!{RESET}")
    else:
        print(f"  {RED}{BOLD}Some integration tests failed.{RESET}")

    print(f"\n{BOLD}{'='*80}{RESET}\n")

    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)