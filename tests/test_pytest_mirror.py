"""
Pytest mirror runner for custom test suites.

This file discovers test modules that expose run_all_tests() and runs them
through pytest so every custom suite has a matching pytest entry point.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _ensure_project_root() -> None:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def _iter_test_modules():
    base = Path(__file__).resolve().parent
    mirror_name = Path(__file__).name
    for path in base.rglob("test_*.py"):
        if path.name == mirror_name:
            continue
        rel = path.relative_to(base).with_suffix("")
        module_name = ".".join(["tests", *rel.parts])
        yield module_name


def _collect_suites():
    _ensure_project_root()
    for module_name in _iter_test_modules():
        module = importlib.import_module(module_name)
        run_all = getattr(module, "run_all_tests", None)
        if callable(run_all):
            yield module_name, run_all


@pytest.mark.parametrize("module_name, run_all", list(_collect_suites()))
def test_pytest_mirror_runner(module_name, run_all):
    assert run_all(), f"Suite failed: {module_name}"
