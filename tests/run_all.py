"""
Run all tests + benchmarks.
"""

import sys
from pathlib import Path


def _find_project_root(start: Path) -> Path:
    for parent in [start] + list(start.parents):
        if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
            return parent
    return start


project_root = _find_project_root(Path(__file__).resolve())
sys.path.insert(0, str(project_root))


def run_all() -> bool:
    ok = True
    try:
        from tests.run_all_tests import run_all_tests

        ok = run_all_tests() and ok
    except Exception as exc:
        print(f"Error running tests: {exc}")
        ok = False

    try:
        from tests.run_all_benchmarks import run_all_benchmarks

        run_all_benchmarks()
    except Exception as exc:
        print(f"Error running benchmarks: {exc}")
        ok = False

    return ok


if __name__ == "__main__":
    sys.exit(0 if run_all() else 1)
