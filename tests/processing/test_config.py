"""
ProcessConfig and TimeoutConfig Tests

Tests the configuration dataclasses:
- ProcessConfig: runs, join_in, lives, timeouts
- TimeoutConfig: prerun, run, postrun, onfinish, result, error
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

# Config dataclasses are intentionally NOT part of the public API.
# Tests import them from the internal module to validate implementation behavior.
from suitkaise.processing._int.config import ProcessConfig, TimeoutConfig


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
# ProcessConfig Tests
# =============================================================================

def test_processconfig_creation():
    """ProcessConfig should be creatable with defaults."""
    config = ProcessConfig()
    assert config is not None


def test_processconfig_runs():
    """ProcessConfig should accept runs parameter."""
    config = ProcessConfig(runs=5)
    assert config.runs == 5


def test_processconfig_runs_none():
    """ProcessConfig runs=None means run indefinitely."""
    config = ProcessConfig(runs=None)
    assert config.runs is None


def test_processconfig_join_in():
    """ProcessConfig should accept join_in (max runtime)."""
    config = ProcessConfig(join_in=10.0)
    assert config.join_in == 10.0


def test_processconfig_join_in_none():
    """ProcessConfig join_in=None means no time limit."""
    config = ProcessConfig(join_in=None)
    assert config.join_in is None


def test_processconfig_lives():
    """ProcessConfig should accept lives (retry count)."""
    config = ProcessConfig(lives=3)
    assert config.lives == 3


def test_processconfig_lives_default():
    """ProcessConfig lives defaults to 1 (no retries)."""
    config = ProcessConfig()
    assert config.lives == 1


def test_processconfig_timeouts():
    """ProcessConfig should accept timeouts config."""
    timeout_config = TimeoutConfig(run=5.0)
    config = ProcessConfig(timeouts=timeout_config)
    assert config.timeouts == timeout_config


def test_processconfig_multiple_params():
    """ProcessConfig should accept multiple parameters."""
    config = ProcessConfig(runs=10, join_in=30.0, lives=2)
    assert config.runs == 10
    assert config.join_in == 30.0
    assert config.lives == 2


def test_processconfig_defaults():
    """ProcessConfig should have sensible defaults."""
    config = ProcessConfig()
    assert config.runs is None
    assert config.join_in is None
    assert config.lives == 1


# =============================================================================
# TimeoutConfig Tests
# =============================================================================

def test_timeoutconfig_creation():
    """TimeoutConfig should be creatable with defaults."""
    config = TimeoutConfig()
    assert config is not None


def test_timeoutconfig_prerun():
    """TimeoutConfig should accept prerun timeout."""
    config = TimeoutConfig(prerun=5.0)
    assert config.prerun == 5.0


def test_timeoutconfig_run():
    """TimeoutConfig should accept run timeout."""
    config = TimeoutConfig(run=10.0)
    assert config.run == 10.0


def test_timeoutconfig_postrun():
    """TimeoutConfig should accept postrun timeout."""
    config = TimeoutConfig(postrun=3.0)
    assert config.postrun == 3.0


def test_timeoutconfig_onfinish():
    """TimeoutConfig should accept onfinish timeout."""
    config = TimeoutConfig(onfinish=2.0)
    assert config.onfinish == 2.0


def test_timeoutconfig_result():
    """TimeoutConfig should accept result timeout."""
    config = TimeoutConfig(result=1.0)
    assert config.result == 1.0


def test_timeoutconfig_error():
    """TimeoutConfig should accept error timeout."""
    config = TimeoutConfig(error=1.0)
    assert config.error == 1.0


def test_timeoutconfig_defaults():
    """TimeoutConfig should default all to None (no timeout)."""
    config = TimeoutConfig()
    assert config.prerun is None
    assert config.run is None
    assert config.postrun is None
    assert config.onfinish is None
    assert config.result is None
    assert config.error is None


def test_timeoutconfig_multiple():
    """TimeoutConfig should accept multiple timeouts."""
    config = TimeoutConfig(prerun=1.0, run=10.0, postrun=2.0)
    assert config.prerun == 1.0
    assert config.run == 10.0
    assert config.postrun == 2.0


def test_timeoutconfig_integer():
    """TimeoutConfig should accept integer values."""
    config = TimeoutConfig(run=5)
    assert config.run == 5


def test_timeoutconfig_float():
    """TimeoutConfig should accept float values."""
    config = TimeoutConfig(run=2.5)
    assert config.run == 2.5


# =============================================================================
# Integration Tests
# =============================================================================

def test_processconfig_with_timeoutconfig():
    """ProcessConfig timeouts field should work with TimeoutConfig."""
    timeout = TimeoutConfig(run=10.0, prerun=1.0)
    config = ProcessConfig(runs=5, lives=2, timeouts=timeout)
    
    assert config.timeouts.run == 10.0
    assert config.timeouts.prerun == 1.0


def test_configs_are_dataclasses():
    """Both configs should behave as dataclasses."""
    # ProcessConfig
    pc1 = ProcessConfig(runs=5, lives=2)
    pc2 = ProcessConfig(runs=5, lives=2)
    assert pc1 == pc2
    
    # TimeoutConfig
    tc1 = TimeoutConfig(run=5.0)
    tc2 = TimeoutConfig(run=5.0)
    assert tc1 == tc2


def test_config_inequality():
    """Different configs should not be equal."""
    pc1 = ProcessConfig(runs=5)
    pc2 = ProcessConfig(runs=10)
    assert pc1 != pc2
    
    tc1 = TimeoutConfig(run=5.0)
    tc2 = TimeoutConfig(run=10.0)
    assert tc1 != tc2


# =============================================================================
# Edge Cases
# =============================================================================

def test_processconfig_zero_runs():
    """ProcessConfig should handle runs=0."""
    config = ProcessConfig(runs=0)
    assert config.runs == 0


def test_processconfig_large_runs():
    """ProcessConfig should handle large runs value."""
    config = ProcessConfig(runs=1000000)
    assert config.runs == 1000000


def test_timeoutconfig_zero():
    """TimeoutConfig should handle zero timeout."""
    config = TimeoutConfig(run=0)
    assert config.run == 0


def test_timeoutconfig_small():
    """TimeoutConfig should handle very small timeout."""
    config = TimeoutConfig(run=0.001)
    assert config.run == 0.001


def test_timeoutconfig_large():
    """TimeoutConfig should handle large timeout."""
    config = TimeoutConfig(run=86400)  # 24 hours
    assert config.run == 86400


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all config tests."""
    runner = TestRunner("ProcessConfig & TimeoutConfig Tests")
    
    # ProcessConfig tests
    runner.run_test("ProcessConfig creation", test_processconfig_creation)
    runner.run_test("ProcessConfig runs", test_processconfig_runs)
    runner.run_test("ProcessConfig runs=None", test_processconfig_runs_none)
    runner.run_test("ProcessConfig join_in", test_processconfig_join_in)
    runner.run_test("ProcessConfig join_in=None", test_processconfig_join_in_none)
    runner.run_test("ProcessConfig lives", test_processconfig_lives)
    runner.run_test("ProcessConfig lives default", test_processconfig_lives_default)
    runner.run_test("ProcessConfig timeouts", test_processconfig_timeouts)
    runner.run_test("ProcessConfig multiple params", test_processconfig_multiple_params)
    runner.run_test("ProcessConfig defaults", test_processconfig_defaults)
    
    # TimeoutConfig tests
    runner.run_test("TimeoutConfig creation", test_timeoutconfig_creation)
    runner.run_test("TimeoutConfig prerun", test_timeoutconfig_prerun)
    runner.run_test("TimeoutConfig run", test_timeoutconfig_run)
    runner.run_test("TimeoutConfig postrun", test_timeoutconfig_postrun)
    runner.run_test("TimeoutConfig onfinish", test_timeoutconfig_onfinish)
    runner.run_test("TimeoutConfig result", test_timeoutconfig_result)
    runner.run_test("TimeoutConfig error", test_timeoutconfig_error)
    runner.run_test("TimeoutConfig defaults", test_timeoutconfig_defaults)
    runner.run_test("TimeoutConfig multiple", test_timeoutconfig_multiple)
    runner.run_test("TimeoutConfig integer", test_timeoutconfig_integer)
    runner.run_test("TimeoutConfig float", test_timeoutconfig_float)
    
    # Integration tests
    runner.run_test("ProcessConfig with TimeoutConfig", test_processconfig_with_timeoutconfig)
    runner.run_test("Configs are dataclasses", test_configs_are_dataclasses)
    runner.run_test("Config inequality", test_config_inequality)
    
    # Edge cases
    runner.run_test("ProcessConfig zero runs", test_processconfig_zero_runs)
    runner.run_test("ProcessConfig large runs", test_processconfig_large_runs)
    runner.run_test("TimeoutConfig zero", test_timeoutconfig_zero)
    runner.run_test("TimeoutConfig small", test_timeoutconfig_small)
    runner.run_test("TimeoutConfig large", test_timeoutconfig_large)
    
    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
