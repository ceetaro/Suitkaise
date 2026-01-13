"""
Run All Sk Tests

Executes all test suites in the sk module.
"""

import sys

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'


def run_all_tests():
    """Run all sk module tests."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' SK MODULE - ALL TESTS ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    
    from tests.sk.test_skclass import run_all_tests as run_skclass_tests
    from tests.sk.test_skfunction import run_all_tests as run_skfunction_tests
    from tests.sk.test_decorator import run_all_tests as run_decorator_tests
    from tests.sk.test_async_chaining import run_all_tests as run_async_chaining_tests
    from tests.sk.test_async_skfunction import run_all_tests as run_async_skfunction_tests
    from tests.sk.test_shared_meta import run_all_tests as run_shared_meta_tests
    
    results = []
    
    print(f"\n{CYAN}Running Skclass tests...{RESET}")
    results.append(("Skclass", run_skclass_tests()))
    
    print(f"\n{CYAN}Running Skfunction tests...{RESET}")
    results.append(("Skfunction", run_skfunction_tests()))
    
    print(f"\n{CYAN}Running @sk decorator tests...{RESET}")
    results.append(("@sk Decorator", run_decorator_tests()))
    
    print(f"\n{CYAN}Running AsyncSkfunction chaining tests...{RESET}")
    results.append(("AsyncSkfunction Chaining", run_async_chaining_tests()))
    
    print(f"\n{CYAN}Running AsyncSkfunction tests...{RESET}")
    results.append(("AsyncSkfunction", run_async_skfunction_tests()))
    
    print(f"\n{CYAN}Running _shared_meta tests...{RESET}")
    results.append(("_shared_meta", run_shared_meta_tests()))
    
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
        print(f"  {GREEN}{BOLD}All sk tests passed!{RESET}")
    else:
        print(f"  {RED}{BOLD}Some sk tests failed.{RESET}")
    
    print(f"\n{BOLD}{'='*80}{RESET}\n")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
