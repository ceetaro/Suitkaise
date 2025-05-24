#!/usr/bin/env python3
"""
Test runner for Suitkaise.

This script provides an easy way to run tests for the Suitkaise library
with different options and configurations.

Usage:
    python3.11 run_tests.py                    # Run all tests
    python3.11 run_tests.py --skglobals        # Run only SKGlobals tests
    python3.11 run_tests.py --unit             # Run only unit tests
    python3.11 run_tests.py --slow             # Run slow tests too
    python3.11 run_tests.py --verbose          # Verbose output
    python3.11 run_tests.py --help             # Show help
    python3.11 run_tests.py --check            # Check dependencies and imports only
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

INFO = "⬜️" * 40 + "\n\n\n"
FAIL = "\n\n   " + "❌" * 10 + " "
SUCCESS = "\n\n   " + "🟩" * 10 + " "
RUNNING = "🔄" * 40 + "\n\n"
CHECKING = "🧳" * 40 + "\n"
WARNING = "\n\n   " + "🟨" * 10 + " "


def run_with_unittest(test_module=None, verbose=False):
    """Run tests using unittest."""
    print(f"{RUNNING} Running tests with unittest...")
    
    if test_module:
        cmd = [sys.executable, '-m', 'unittest', test_module]
    else:
        cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py']
    
    if verbose:
        cmd.append('-v')
    
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode == 0


def run_with_pytest(test_path=None, markers=None, verbose=False):
    """Run tests using pytest."""
    print(f"{RUNNING} Running tests with pytest...")
    
    cmd = [sys.executable, '-m', 'pytest']
    
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append('tests/')
    
    if markers:
        cmd.extend(['-m', markers])
    
    if verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')
    
    # Add useful pytest options
    cmd.extend([
        '--tb=short',  # Short traceback format
        '--strict-markers',  # Strict marker checking
    ])
    
    try:
        result = subprocess.run(cmd, cwd=project_root)
        return result.returncode == 0
    except FileNotFoundError:
        print(f"{WARNING} pytest not found. Install with: pip install pytest")
        return False


def run_skglobals_tests_directly():
    """Run SKGlobals tests directly."""
    print(f"{RUNNING} Running SKGlobals tests directly...")
    
    try:
        from tests.test_suitkaise.test_skglobals.test_skglobals import run_tests
        return run_tests()
    except ImportError as e:
        print(f"{FAIL} Failed to import tests: {e}")
        print("Make sure you're running from the project root directory.")
        return False


def check_dependencies():
    """Check if required dependencies are available."""
    print(f"{CHECKING} Checking dependencies...")
    
    # Check if suitkaise can be imported
    try:
        import suitkaise.skglobals
        print(f"{SUCCESS} suitkaise.skglobals imported successfully\n")
    except ImportError as e:
        print(f"{FAIL} Failed to import suitkaise.skglobals: {e}\n")
        return False
    
    # Check if tests can be imported
    try:
        from tests.test_suitkaise.test_skglobals import test_skglobals
        print(f"{SUCCESS} Test modules imported successfully\n")
    except ImportError as e:
        print(f"{FAIL} Failed to import test modules: {e}\n")
        return False
    
    return True


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run tests for Suitkaise library",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_tests.py                    # Run all tests with pytest
    python run_tests.py --unittest         # Use unittest instead of pytest
    python run_tests.py --skglobals        # Run only SKGlobals tests
    python run_tests.py --unit             # Run only unit tests (skip slow tests)
    python run_tests.py --slow             # Include slow tests
    python run_tests.py --verbose          # Detailed output
    python run_tests.py --check            # Just check if imports work
        """
    )
    
    parser.add_argument('--unittest', action='store_true',
                        help='Use unittest instead of pytest')
    parser.add_argument('--pytest', action='store_true', 
                        help='Use pytest (default)')
    parser.add_argument('--direct', action='store_true',
                        help='Run tests directly (no external runner)')
    parser.add_argument('--skglobals', action='store_true',
                        help='Run only SKGlobals tests')
    parser.add_argument('--unit', action='store_true',
                        help='Run only unit tests (exclude slow tests)')
    parser.add_argument('--slow', action='store_true',
                        help='Include slow tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    parser.add_argument('--check', action='store_true',
                        help='Check dependencies and imports only')
    
    args = parser.parse_args()
    
    print(f"{RUNNING} Suitkaise Test Runner")
    
    # Check dependencies first
    if not check_dependencies():
        print(f"{FAIL} Dependency check failed!")
        return 1
    
    if args.check:
        print(f"{SUCCESS} All dependencies available!\n")
        return 0
    
    # Determine test method
    use_pytest = not args.unittest and not args.direct
    success = False
    
    try:
        if args.direct:
            # Run tests directly
            success = run_skglobals_tests_directly()
            
        elif use_pytest:
            # Use pytest
            test_path = None
            markers = None
            
            if args.skglobals:
                test_path = "tests/test_suitkaise/test_skglobals/"
            
            if args.unit:
                markers = "unit and not slow"
            elif not args.slow:
                markers = "not slow"
            
            success = run_with_pytest(test_path, markers, args.verbose)
            
        else:
            # Use unittest
            test_module = None
            if args.skglobals:
                test_module = "tests.test_suitkaise.test_skglobals.test_skglobals"
            
            success = run_with_unittest(test_module, args.verbose)
            
    except KeyboardInterrupt:
        print(f"{WARNING}Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"{FAIL} Error running tests: {e}")
        return 1
    
    if success:
        print(f"{SUCCESS} All tests passed successfully!\n")
        return 0
    else:
        print(f"{FAIL} Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())