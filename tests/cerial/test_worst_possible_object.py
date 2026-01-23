"""
Cerial WorstPossibleObject Tests

Ensures the worst possible object can:
- serialize and deserialize
- verify integrity after round-trip
- work with the reconnector system
"""

import sys
import random
from pathlib import Path


def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start


project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.cerial import serialize, deserialize, reconnect_all
from suitkaise.cerial._int.worst_possible_object.worst_possible_obj import WorstPossibleObject


# =============================================================================
# Test Infrastructure
# =============================================================================

class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error


class TestRunner:
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.results = []
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.CYAN = '\033[96m'
        self.BOLD = '\033[1m'
        self.RESET = '\033[0m'
    
    def run_test(self, name: str, test_func):
        try:
            test_func()
            self.results.append(TestResult(name, True))
        except AssertionError as e:
            self.results.append(TestResult(name, False, error=str(e)))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}"))
    
    def print_results(self):
        print(f"\n{self.BOLD}{self.CYAN}{'='*70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{self.suite_name:^70}{self.RESET}")
        print(f"{self.BOLD}{self.CYAN}{'='*70}{self.RESET}\n")
        
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        for result in self.results:
            if result.passed:
                status = f"{self.GREEN}✓ PASS{self.RESET}"
            else:
                status = f"{self.RED}✗ FAIL{self.RESET}"
            print(f"  {status}  {result.name}")
            if result.error:
                print(f"         {self.RED}└─ {result.error}{self.RESET}")
        
        print(f"\n{self.BOLD}{'-'*70}{self.RESET}")
        if failed == 0:
            print(f"  {self.GREEN}{self.BOLD}All {passed} tests passed!{self.RESET}")
        else:
            print(f"  {self.YELLOW}Passed: {passed}{self.RESET}  |  {self.RED}Failed: {failed}{self.RESET}")
        print(f"{self.BOLD}{'-'*70}{self.RESET}\n")

        if failed != 0:
            print(f"{self.BOLD}{self.RED}Failed tests (recap):{self.RESET}")
            for result in self.results:
                if not result.passed:
                    print(f"  {self.RED}✗ {result.name}{self.RESET}")
                    if result.error:
                        print(f"     {self.RED}└─ {result.error}{self.RESET}")
            print()

        try:
            from tests._failure_registry import record_failures
            record_failures(self.suite_name, [r for r in self.results if not r.passed])
        except Exception:
            pass

        return failed == 0


# =============================================================================
# Tests
# =============================================================================

def _format_failures(failures: list[str]) -> str:
    if not failures:
        return ""
    preview = "\n".join(failures[:10])
    remainder = len(failures) - 10
    suffix = f"\n... {remainder} more failures" if remainder > 0 else ""
    return preview + suffix


def test_worst_possible_object_roundtrip():
    """WorstPossibleObject should serialize, deserialize, and verify."""
    random.seed(1337)
    original = WorstPossibleObject()
    restored = None
    try:
        data = serialize(original)
        restored = deserialize(data)
        restored = reconnect_all(restored)
        passed, failures = original.verify(restored)
        assert passed, "Verification failed:\n" + _format_failures(failures)
    finally:
        try:
            original.cleanup()
        except Exception:
            pass
        if restored is not None:
            try:
                restored.cleanup()
            except Exception:
                pass


def run_all_tests():
    """Run all WorstPossibleObject tests."""
    runner = TestRunner("Cerial WorstPossibleObject Tests")
    runner.run_test("worst_possible_object_roundtrip", test_worst_possible_object_roundtrip)
    return runner.print_results()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)