"""
WorstPossibleObject (WPO) Stress Tests (Cerial)

WPO was designed specifically to validate cerial's ability to serialize and
deserialize extremely complex, semi-randomly generated objects.

This suite uses WPO's built-in verification (`WorstPossibleObject.verify`) and
performs repeated roundtrips to catch flaky, "fails sometimes" serialization bugs.

Target:
- 100 roundtrip iterations
- across 5 distinct WPO objects (different deterministic seeds)
"""

import sys
import random

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from suitkaise.cerial import serialize, deserialize


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
        return failed == 0


# =============================================================================
# WPO Stress Tests
# =============================================================================

def _safe_cleanup(obj) -> None:
    """Best-effort cleanup to avoid leaking file descriptors/sockets across iterations."""
    try:
        if obj is not None and hasattr(obj, "cleanup"):
            obj.cleanup()
    except Exception:
        pass


def test_wpo_roundtrip_100_iterations_across_5_objects():
    """
    Create 5 distinct WPO objects (different deterministic seeds).
    
    Then perform 100 roundtrip iterations PER OBJECT (500 total roundtrips):
        serialize -> deserialize -> verify()
    
    This catches non-deterministic serialization failures that only appear
    after repeated cycles.
    """
    from suitkaise.cerial._int.worst_possible_object.worst_possible_obj import WorstPossibleObject
    
    # 5 distinct objects
    seeds = [0, 1, 2, 3, 4]
    wpos = []
    try:
        for seed in seeds:
            random.seed(seed)
            wpos.append(WorstPossibleObject(verbose=False))
        
        # 100 iterations across these 5 objects (100 per object)
        for obj_index, wpo in enumerate(wpos):
            for iteration in range(100):
                restored = None
                try:
                    data = serialize(wpo)
                    restored = deserialize(data)
                    
                    ok, failures = wpo.verify(restored)
                    assert ok, (
                        f"WPO verify failed (object={obj_index}, iteration={iteration}).\n"
                        + "\n".join(failures[:80])
                    )
                finally:
                    _safe_cleanup(restored)
    finally:
        for wpo in wpos:
            _safe_cleanup(wpo)


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all WPO stress tests."""
    runner = TestRunner("WorstPossibleObject (Cerial) Stress Tests")
    runner.run_test("WPO 100 iterations across 5 objects", test_wpo_roundtrip_100_iterations_across_5_objects)
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

