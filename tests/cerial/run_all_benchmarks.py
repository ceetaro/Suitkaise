"""
Run All Cerial Benchmarks

Executes all benchmarks in the cerial module.
"""

import sys

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from tests.cerial.benchmarks import run_all_benchmarks


if __name__ == '__main__':
    run_all_benchmarks()
