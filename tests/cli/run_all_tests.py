"""
Run All CLI Tests
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
    """Run all CLI tests."""
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}{' CLI - ALL TESTS ':=^80}{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")

    from tests.cli.test_cli import run_all_tests as run_cli_tests

    results = []
    print(f"\n{CYAN}Running CLI tests...{RESET}")
    results.append(("CLI", run_cli_tests()))

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
        print(f"  {GREEN}{BOLD}All CLI tests passed!{RESET}")
    else:
        print(f"  {RED}{BOLD}Some CLI tests failed.{RESET}")

    print(f"\n{BOLD}{'='*80}{RESET}\n")
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
