"""
Run All Processing Benchmarks

Executes all benchmarks in the processing module.
"""

import sys

sys.path.insert(0, '/Users/ctaro/projects/code/Suitkaise')

from tests.processing.benchmarks import run_all_benchmarks


if __name__ == '__main__':
    run_all_benchmarks()
