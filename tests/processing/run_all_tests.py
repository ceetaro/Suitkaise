"""
Run All Processing Tests

Executes all test suites in the processing module.
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
    """Run all processing module tests."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' PROCESSING MODULE - ALL TESTS ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    from tests.processing.test_process import run_all_tests as run_process_tests
    from tests.processing.test_pool import run_all_tests as run_pool_tests
    from tests.processing.test_share import run_all_tests as run_share_tests
    from tests.processing.test_share_comprehensive import run_all_tests as run_share_comprehensive_tests
    from tests.processing.test_config import run_all_tests as run_config_tests
    from tests.processing.test_timers import run_all_tests as run_timers_tests
    from tests.processing.test_engine import run_all_tests as run_engine_tests
    from tests.processing.test_timeout import run_all_tests as run_timeout_tests
    from tests.processing.test_errors import run_all_tests as run_errors_tests
    from tests.processing.test_share_primitives import run_all_tests as run_share_primitives_tests
    from tests.processing.test_share_proxy import run_all_tests as run_share_proxy_tests
    from tests.processing.test_pool_internal import run_all_tests as run_pool_internal_tests
    from tests.processing.test_pool_share import run_all_tests as run_pool_share_tests
    from tests.processing.test_coordinator import run_all_tests as run_coordinator_tests
    from tests.processing.test_modifiers import run_all_tests as run_modifiers_tests
    from tests.processing.test_pipe import run_all_tests as run_pipe_tests
    
    results = []
    
    print(f"\n{CYAN}Running Process tests...{RESET}")
    results.append(("Process", run_process_tests()))
    
    print(f"\n{CYAN}Running Pool tests...{RESET}")
    results.append(("Pool", run_pool_tests()))
    
    print(f"\n{CYAN}Running Share tests...{RESET}")
    results.append(("Share", run_share_tests()))
    
    print(f"\n{CYAN}Running Share Comprehensive tests...{RESET}")
    results.append(("Share Comprehensive", run_share_comprehensive_tests()))
    
    print(f"\n{CYAN}Running Config tests...{RESET}")
    results.append(("Config", run_config_tests()))
    
    print(f"\n{CYAN}Running Timers tests...{RESET}")
    results.append(("Timers", run_timers_tests()))

    print(f"\n{CYAN}Running Engine tests...{RESET}")
    results.append(("Engine", run_engine_tests()))

    print(f"\n{CYAN}Running Timeout tests...{RESET}")
    results.append(("Timeout", run_timeout_tests()))
    
    print(f"\n{CYAN}Running Error Types tests...{RESET}")
    results.append(("Error Types", run_errors_tests()))

    print(f"\n{CYAN}Running Share Primitives tests...{RESET}")
    results.append(("Share Primitives", run_share_primitives_tests()))

    print(f"\n{CYAN}Running Share Proxy tests...{RESET}")
    results.append(("Share Proxy", run_share_proxy_tests()))

    print(f"\n{CYAN}Running Pool Internal tests...{RESET}")
    results.append(("Pool Internal", run_pool_internal_tests()))

    print(f"\n{CYAN}Running Pool + Share tests...{RESET}")
    results.append(("Pool + Share", run_pool_share_tests()))

    print(f"\n{CYAN}Running Coordinator tests...{RESET}")
    results.append(("Coordinator", run_coordinator_tests()))

    print(f"\n{CYAN}Running Process & Pool Modifier tests...{RESET}")
    results.append(("Modifiers", run_modifiers_tests()))

    print(f"\n{CYAN}Running Pipe tests...{RESET}")
    results.append(("Pipe", run_pipe_tests()))
    
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
        print(f"  {GREEN}{BOLD}All processing tests passed!{RESET}")
    else:
        print(f"  {RED}{BOLD}Some processing tests failed.{RESET}")
    
    print(f"\n{BOLD}{'='*80}{RESET}\n")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
