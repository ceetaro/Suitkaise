"""
Run All Cucumber Benchmarks

Executes all benchmarks in the cucumber module.
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

from tests.cucumber.benchmarks import run_all_benchmarks


if __name__ == '__main__':
    run_all_benchmarks()
