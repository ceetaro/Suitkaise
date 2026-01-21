"""
PokerML Dealer Integration Tests

Validates the Dealer lifecycle and timing behavior in a realistic flow.
"""

from __future__ import annotations

import sys
from pathlib import Path

from suitkaise import timing
from typing import Any

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start


project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "suitkaise-examples" / "pokerML"))

from suitkaise.processing import Share

from poker_ml.dealer import Dealer  # type: ignore[import-not-found]
from poker_ml.state import DealerConfig  # type: ignore[import-not-found]

try:
    from _suitkaise_wip.fdl._int.setup.text_wrapping import _TextWrapper  # type: ignore[import-not-found]
except Exception:
    _TextWrapper = None


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
        self._wrapper = _TextWrapper(width=72) if _TextWrapper else None

    def _wrap(self, text: str) -> list[str]:
        if self._wrapper:
            return self._wrapper.wrap_text(text, preserve_newlines=True)
        return [text]

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
                for line in self._wrap(result.error):
                    print(f"         {self.RED}└─ {line}{self.RESET}")

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


def _build_dealer():
    share: Any = Share()
    share.stats = {"hands": 0, "wins": 0, "total_reward": 0.0}
    share.policies = {}
    config = DealerConfig(
        table_id=0,
        players_per_table=4,
        starting_stack=50,
        small_blind=1,
        big_blind=2,
        hands_per_table=1,
        strength_samples=10,
        learning_rate=0.05,
        seed=123,
        verbose=False,
    )
    return Dealer(share, config), share


def test_dealer_lifecycle_timing():
    dealer, share = _build_dealer()

    timer: Any = timing.Sktimer()

    with timing.TimeThis(timer=timer):
        dealer.__prerun__()
    with timing.TimeThis(timer=timer):
        dealer.__run__()
    with timing.TimeThis(timer=timer):
        dealer.__postrun__()
    with timing.TimeThis(timer=timer):
        dealer.__onfinish__()

    result = dealer.__result__()
    assert result["done"] is True, f"Expected done=True, got {result}"
    assert "deltas" in result, f"Missing deltas in result: {result}"
    assert share.stats["hands"] >= 1, f"Expected hands>=1, got {share.stats}"
    assert timer.num_times == 4, f"Expected 4 timings, got {timer.num_times}"
    assert timer.most_recent >= 0.0, f"Expected most_recent>=0, got {timer.most_recent}"


def run_all_tests():
    runner = TestRunner("PokerML Dealer Tests")
    runner.run_test("Dealer lifecycle + timing", test_dealer_lifecycle_timing)
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
