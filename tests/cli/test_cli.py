"""
CLI Tests

Tests Suitkaise CLI commands and output.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout

from pathlib import Path

# Add project root to path (auto-detect by marker files)

def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / 'pyproject.toml').exists() or (parent / 'setup.py').exists():
            return parent
    return start

project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))

from suitkaise import __version__
from suitkaise.cli import main

try:
    from _suitkaise_wip.fdl._int.setup.text_wrapping import _TextWrapper
except Exception:
    _TextWrapper = None


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
        return failed == 0


# =============================================================================
# CLI Tests
# =============================================================================

def _run_cli(args: list[str]) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        exit_code = main(args)
    output = buf.getvalue()
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
    return output


def test_cli_version():
    """CLI --version prints current version."""
    output = _run_cli(["--version"]).strip()
    assert output == __version__


def test_cli_info():
    """CLI info prints version and modules."""
    output = _run_cli(["info"])
    assert __version__ in output
    assert "Modules:" in output


def test_cli_modules():
    """CLI modules lists available modules."""
    output = _run_cli(["modules"]).strip().splitlines()
    expected = {"timing", "paths", "circuits", "cerial", "processing", "sk"}
    assert set(output) == expected


def test_cli_help():
    """CLI with no args prints help."""
    output = _run_cli([])
    assert "usage:" in output.lower()
    assert "suitkaise" in output.lower()


# =============================================================================
# Main Entry Point
# =============================================================================

def run_all_tests():
    """Run all CLI tests."""
    runner = TestRunner("CLI Tests")

    runner.run_test("CLI --version", test_cli_version)
    runner.run_test("CLI info", test_cli_info)
    runner.run_test("CLI modules", test_cli_modules)
    runner.run_test("CLI help", test_cli_help)

    return runner.print_results()


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
