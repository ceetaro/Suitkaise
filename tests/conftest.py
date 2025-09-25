from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Dict, List, Tuple

import pytest  # type: ignore


_TEST_DETAILS: Dict[str, List[str]] = {}


def _c(s: str, color: str) -> str:
    colors = {
        'red': '\u001b[31m',
        'green': '\u001b[32m',
        'yellow': '\u001b[33m',
        'blue': '\u001b[34m',
        'magenta': '\u001b[35m',
        'cyan': '\u001b[36m',
        'reset': '\u001b[0m',
    }
    return f"{colors.get(color,'')}{s}{colors['reset']}"


def _doc_parts(item: pytest.Item) -> Tuple[str, List[str]]:
    try:
        fn = getattr(item, "function", None)
        if fn is None:
            return "", []
        doc = inspect.getdoc(fn) or ""
        if not doc:
            return "", []
        lines = [line.rstrip() for line in doc.splitlines()]
        title = lines[0].strip()
        rest = [l for l in lines[1:] if l.strip()]
        return title, rest
    except Exception:
        return "", []


@pytest.fixture
def reporter(request: pytest.FixtureRequest) -> SimpleNamespace:
    nodeid = request.node.nodeid
    _TEST_DETAILS[nodeid] = []

    def add(line: str) -> None:
        _TEST_DETAILS[nodeid].append(line)

    return SimpleNamespace(add=add)


def pytest_runtest_setup(item: pytest.Item) -> None:
    title, desc_lines = _doc_parts(item)
    if title:
        print(_c(f"\n{title}", 'cyan'))
    for line in desc_lines:
        print(line)
    if title or desc_lines:
        print("")


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if report.when != "call":
        return
    details = _TEST_DETAILS.get(report.nodeid, [])
    for line in details:
        print(line)
    outcome = report.outcome.upper()
    color = 'green' if outcome == 'PASSED' else ('red' if outcome == 'FAILED' else 'yellow')
    print(f"{_c('Test:', color)} {outcome}")


