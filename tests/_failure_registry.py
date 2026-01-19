"""
Global registry for test failures across suites.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class FailedTest:
    suite: str
    name: str
    error: str


_failures: List[FailedTest] = []


def record_failures(suite: str, results: Iterable) -> None:
    """
    Record failed tests from a suite.
    """
    for result in results:
        if getattr(result, "passed", True):
            continue
        error = getattr(result, "error", "") or ""
        name = getattr(result, "name", "unknown")
        _failures.append(FailedTest(suite=suite, name=name, error=error))


def print_recap() -> None:
    """
    Print a recap of all failures recorded so far.
    """
    if not _failures:
        return
    print("\nFailed tests (recap across suites):")
    for failure in _failures:
        print(f"  ✗ [{failure.suite}] {failure.name}")
        if failure.error:
            print(f"     └─ {failure.error}")
    print()


def clear() -> None:
    _failures.clear()
