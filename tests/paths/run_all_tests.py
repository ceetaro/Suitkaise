"""
Run All Paths Tests

Executes all test suites in the paths module.
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
    """Run all paths module tests."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' PATHS MODULE - ALL TESTS ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    from tests.paths.test_skpath import run_all_tests as run_skpath_tests
    from tests.paths.test_utilities import run_all_tests as run_utilities_tests
    from tests.paths.test_root_detection import run_all_tests as run_root_tests
    from tests.paths.test_autopath import run_all_tests as run_autopath_tests
    from tests.paths.test_id_encoding import run_all_tests as run_id_encoding_tests
    from tests.paths.test_project_utils import run_all_tests as run_project_utils_tests
    
    results = []
    
    print(f"\n{CYAN}Running Skpath tests...{RESET}")
    results.append(("Skpath", run_skpath_tests()))
    
    print(f"\n{CYAN}Running Utilities tests...{RESET}")
    results.append(("Utilities", run_utilities_tests()))
    
    print(f"\n{CYAN}Running Root Detection tests...{RESET}")
    results.append(("Root Detection", run_root_tests()))
    
    print(f"\n{CYAN}Running @autopath tests...{RESET}")
    results.append(("@autopath", run_autopath_tests()))
    
    print(f"\n{CYAN}Running ID Encoding tests...{RESET}")
    results.append(("ID Encoding", run_id_encoding_tests()))
    
    print(f"\n{CYAN}Running Project Utils tests...{RESET}")
    results.append(("Project Utils", run_project_utils_tests()))
    
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
        print(f"  {GREEN}{BOLD}All paths tests passed!{RESET}")
    else:
        print(f"  {RED}{BOLD}Some paths tests failed.{RESET}")
    
    print(f"\n{BOLD}{'='*80}{RESET}\n")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
