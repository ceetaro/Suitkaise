"""
Run All Circuits Benchmarks

Executes all benchmarks in the circuits module.
"""

import sys

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from tests.circuits.benchmarks import run_all_benchmarks


if __name__ == '__main__':
    run_all_benchmarks()
