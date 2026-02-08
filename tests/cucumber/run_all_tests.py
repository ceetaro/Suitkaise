"""
Run All Cucumber Tests

Executes all test suites in the cucumber module.
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
    """Run all cucumber module tests."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' CUCUMBER MODULE - ALL TESTS ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    from tests.cucumber.test_primitives import run_all_tests as run_primitives_tests
    from tests.cucumber.test_complex import run_all_tests as run_complex_tests
    from tests.cucumber.test_edge_cases import run_all_tests as run_edge_cases_tests
    from tests.cucumber.test_handlers import run_all_tests as run_handlers_tests
    from tests.cucumber.test_worst_possible_object import run_all_tests as run_wpo_tests
    from tests.cucumber.test_handlers_extended import run_all_tests as run_handlers_extended_tests
    from tests.cucumber.test_ir_json import run_all_tests as run_ir_json_tests
    from tests.cucumber.test_reconnect import run_all_tests as run_reconnect_tests
    from tests.cucumber.test_network_handler import run_all_tests as run_network_handler_tests
    
    results = []
    
    print(f"\n{CYAN}Running Primitives tests...{RESET}")
    results.append(("Primitives", run_primitives_tests()))
    
    print(f"\n{CYAN}Running Complex Objects tests...{RESET}")
    results.append(("Complex Objects", run_complex_tests()))
    
    print(f"\n{CYAN}Running Edge Cases tests...{RESET}")
    results.append(("Edge Cases", run_edge_cases_tests()))
    
    print(f"\n{CYAN}Running Handlers tests...{RESET}")
    results.append(("Handlers", run_handlers_tests()))
    
    print(f"\n{CYAN}Running WorstPossibleObject stress tests...{RESET}")
    results.append(("WorstPossibleObject", run_wpo_tests()))

    print(f"\n{CYAN}Running Extended Handlers tests...{RESET}")
    results.append(("Extended Handlers", run_handlers_extended_tests()))
    
    print(f"\n{CYAN}Running IR JSON tests...{RESET}")
    results.append(("IR JSON", run_ir_json_tests()))
    
    print(f"\n{CYAN}Running Reconnect tests...{RESET}")
    results.append(("Reconnect", run_reconnect_tests()))
    
    print(f"\n{CYAN}Running Network Handler tests...{RESET}")
    results.append(("Network Handler", run_network_handler_tests()))
    
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
        print(f"  {GREEN}{BOLD}All cucumber tests passed!{RESET}")
    else:
        print(f"  {RED}{BOLD}Some cucumber tests failed.{RESET}")
    
    print(f"\n{BOLD}{'='*80}{RESET}\n")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
