"""
Run All Real-World Integration Tests

These tests simulate realistic use cases where multiple Suitkaise
components work together to solve actual problems.
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
MAGENTA = '\033[95m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'


def run_all_tests():
    """Run all real-world integration tests."""
    print(f"\n{BOLD}{MAGENTA}{'='*80}{RESET}")
    print(f"{BOLD}{MAGENTA}{' REAL-WORLD SCENARIO TESTS ':=^80}{RESET}")
    print(f"{BOLD}{MAGENTA}{'='*80}{RESET}")
    print(f"\n{DIM}These tests simulate how Suitkaise components work together")
    print(f"in realistic applications and workflows.{RESET}\n")
    
    from tests.integration.test_async_patterns import run_all_tests as run_async_tests
    from tests.integration.test_data_pipeline import run_all_tests as run_pipeline_tests
    from tests.integration.test_async_web_scraper import run_all_tests as run_scraper_tests
    from tests.integration.test_parallel_processing import run_all_tests as run_parallel_tests
    from tests.integration.test_path_utilities import run_all_tests as run_path_tests
    from tests.integration.test_pokerml_dealer import run_all_tests as run_pokerml_tests
    
    results = []
    
    # Scenario 1: Async Patterns
    print(f"\n{BOLD}{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}Scenario: Async Patterns{RESET}")
    print(f"{DIM}Simulates: An application using async sleep, circuits, and functions together{RESET}")
    print(f"{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    results.append(("Async Patterns", run_async_tests()))
    
    # Scenario 2: Data Pipeline
    print(f"\n{BOLD}{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}Scenario: Data Processing Pipeline{RESET}")
    print(f"{DIM}Simulates: A batch data processor using serialization, parallel pools, and timing{RESET}")
    print(f"{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    results.append(("Data Pipeline", run_pipeline_tests()))
    
    # Scenario 3: Web Scraper
    print(f"\n{BOLD}{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}Scenario: Async Web Scraper{RESET}")
    print(f"{DIM}Simulates: A rate-limited web scraper with circuit breakers and retry logic{RESET}")
    print(f"{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    results.append(("Web Scraper", run_scraper_tests()))
    
    # Scenario 4: Parallel Processing
    print(f"\n{BOLD}{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}Scenario: Parallel Processing{RESET}")
    print(f"{DIM}Simulates: A multi-process worker pool with shared state and performance tracking{RESET}")
    print(f"{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    results.append(("Parallel Processing", run_parallel_tests()))
    
    # Scenario 5: Path Utilities
    print(f"\n{BOLD}{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}Scenario: Path Utilities in Action{RESET}")
    print(f"{DIM}Simulates: A project analyzer using path detection and structure utilities{RESET}")
    print(f"{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    results.append(("Path Utilities", run_path_tests()))
    
    # Scenario 6: PokerML Dealer
    print(f"\n{BOLD}{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}Scenario: PokerML Dealer{RESET}")
    print(f"{DIM}Simulates: A full Dealer lifecycle using timing, Share, and poker logic{RESET}")
    print(f"{MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    results.append(("PokerML Dealer", run_pokerml_tests()))
    
    # Summary
    print(f"\n{BOLD}{MAGENTA}{'='*80}{RESET}")
    print(f"{BOLD}{MAGENTA}{' REAL-WORLD SCENARIO RESULTS ':=^80}{RESET}")
    print(f"{BOLD}{MAGENTA}{'='*80}{RESET}\n")
    
    all_passed = True
    for name, passed in results:
        status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print(f"  {GREEN}{BOLD}All real-world scenarios passed!{RESET}")
        print(f"  {DIM}Your library handles realistic use cases correctly.{RESET}")
    else:
        print(f"  {RED}{BOLD}Some scenarios failed.{RESET}")
    
    print(f"\n{BOLD}{'='*80}{RESET}\n")
    
    return all_passed


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
