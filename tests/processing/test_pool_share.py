"""
Pool + Share Integration Tests

Validates passing Share into Pool workers and round-tripping state.
"""

from __future__ import annotations

import sys
import traceback
import time
from pathlib import Path

from suitkaise import timing, cucumber

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start


project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise.processing import Skprocess, Pool, Share
from suitkaise.processing._int.share.coordinator import _Coordinator

try:
    from _suitkaise_wip.fdl._int.setup.text_wrapping import _TextWrapper
except Exception:
    _TextWrapper = None


class ShareWorker(Skprocess):
    def __init__(self, share: Share, value: int):
        self.share = share
        self.value = value
        self.process_config.runs = 1  # type: ignore[attr-defined]

    def __run__(self):
        # write to per-worker key to avoid race condition on read-modify-write
        # (read-modify-write is not atomic, but individual writes are)
        worker_key = f"worker_{self.value}"
        setattr(self.share, worker_key, {"hands": 1, "reward": float(self.value)})
        return {"ok": True, "value": self.value}


class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", error: str = "", traceback_text: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.error = error
        self.traceback_text = traceback_text


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
            self.results.append(TestResult(name, False, error=str(e), traceback_text=traceback.format_exc()))
        except Exception as e:
            self.results.append(TestResult(name, False, error=f"{type(e).__name__}: {e}", traceback_text=traceback.format_exc()))

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
            if result.traceback_text:
                print(f"{self.RED}{result.traceback_text}{self.RESET}")

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


def test_share_serialization_roundtrip():
    share = Share()
    try:
        share.stats = {"hands": 1, "wins": 0, "total_reward": 0.5}
        data = cucumber.serialize(share)
        restored = cucumber.deserialize(data)
        stats = restored.stats
        assert stats["hands"] == 1, f"Expected hands=1, got {stats}"
    finally:
        share._coordinator.stop()
        time.sleep(0.1)


def test_share_coordinator_state_roundtrip():
    share = Share()
    try:
        share.stats = {"hands": 0, "wins": 0, "total_reward": 0.0}
        state = share._coordinator.get_state()
        try:
            encoded = cucumber.serialize(state)
            decoded = cucumber.deserialize(encoded)
            rebuilt = _Coordinator.from_state(decoded)
            assert rebuilt is not None, "Coordinator should rebuild from state"
        except Exception as e:
            sizes = {k: (len(v) if isinstance(v, (bytes, bytearray)) else None) for k, v in state.items()}
            raise AssertionError(f"Coordinator state roundtrip failed: {type(e).__name__}: {e} | sizes={sizes}") from e
        finally:
            share._coordinator.stop()
            time.sleep(0.1)
    finally:
        share._coordinator.stop()
        time.sleep(0.1)


def test_pool_share_roundtrip_timing():
    share = Share()
    pool = Pool(workers=2)

    try:
        timer = timing.Sktimer()
        with timing.TimeThis(timer=timer):
            results = list(pool.star().unordered_imap(ShareWorker, [(share, 1), (share, 2)]))
            assert len(results) == 2, f"Expected 2 results, got {len(results)}"

        time.sleep(0.3)
        # each worker writes to its own key - no race condition
        w1 = share._coordinator.get_object("worker_1")
        w2 = share._coordinator.get_object("worker_2")
        assert w1 is not None, "Worker 1 data should exist"
        assert w2 is not None, "Worker 2 data should exist"
        total_hands = w1["hands"] + w2["hands"]
        total_reward = w1["reward"] + w2["reward"]
        assert total_hands == 2, f"Expected hands=2, got {total_hands}"
        assert total_reward == 3.0, f"Expected total_reward=3.0, got {total_reward}"
        assert timer.num_times == 1, f"Expected 1 timing, got {timer.num_times}"
    finally:
        # clean up to avoid orphaned processes affecting later tests
        pool.close()
        share._coordinator.stop()
        time.sleep(0.1)


def run_all_tests():
    runner = TestRunner("Pool + Share Tests")
    runner.run_test("Share serialize/deserialize", test_share_serialization_roundtrip)
    runner.run_test("Share coordinator state roundtrip", test_share_coordinator_state_roundtrip)
    runner.run_test("Pool with Share roundtrip + timing", test_pool_share_roundtrip_timing)
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
