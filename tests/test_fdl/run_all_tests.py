#!/usr/bin/env python3
"""
Comprehensive FDL Test Runner

This script runs all FDL tests in the correct order and provides
a comprehensive report of the results.
"""

import sys
import os
import time
import subprocess
from typing import List, Tuple, Dict

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


class TestRunner:
    """Manages running all FDL tests and reporting results."""
    
    def __init__(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.results: List[Tuple[str, bool, float, str]] = []
        
    def run_test_file(self, test_file: str) -> Tuple[bool, float, str]:
        """Run a single test file and return (success, duration, output)."""
        test_path = os.path.join(self.test_dir, test_file)
        
        if not os.path.exists(test_path):
            return False, 0.0, f"Test file not found: {test_file}"
        
        print(f"🏃 Running {test_file}...")
        start_time = time.time()
        
        try:
            # Run the test file
            result = subprocess.run(
                [sys.executable, test_path],
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout per test
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            if success:
                print(f"✅ {test_file} passed ({duration:.2f}s)")
            else:
                print(f"❌ {test_file} failed ({duration:.2f}s)")
                print(f"   Error: {result.stderr[:200]}...")
            
            return success, duration, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ {test_file} timed out ({duration:.2f}s)")
            return False, duration, "Test timed out after 60 seconds"
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {test_file} crashed ({duration:.2f}s): {e}")
            return False, duration, str(e)
    
    def run_all_tests(self) -> Dict[str, any]:
        """Run all tests and return comprehensive results."""
        print("🚀 Starting Comprehensive FDL Test Suite")
        print("=" * 60)
        
        # Define test order (setup/core tests first, then processors, then integration)
        test_order = [
            # Core Infrastructure Tests
            "test_format_state.py",
            "test_command_registry.py",
            "test_object_registry.py",
            
            # Setup Module Tests
            "test_color_conversion.py",
            "test_terminal.py",
            "test_text_justification.py", 
            "test_text_wrapping.py",
            "test_unicode.py",
            "test_box_generation.py",
            
            # Element Tests
            "test_elements.py",
            "test_main_processor.py",
            
            # Command Processor Tests
            "test_command_processors.py",
            "test_debug_commands.py",
            "test_fmt_commands.py",
            
            # Object Processor Tests
            "test_object_processors.py",
            "test_type_objects.py",
            
            # Standalone Feature Tests
            "test_table.py",
            "test_progress_bar.py",
            
            # Integration Tests
            "test_comprehensive_integration.py"
        ]
        
        total_start_time = time.time()
        
        for test_file in test_order:
            success, duration, output = self.run_test_file(test_file)
            self.results.append((test_file, success, duration, output))
        
        total_duration = time.time() - total_start_time
        
        # Generate comprehensive report
        return self.generate_report(total_duration)
    
    def generate_report(self, total_duration: float) -> Dict[str, any]:
        """Generate comprehensive test report."""
        passed = sum(1 for _, success, _, _ in self.results if success)
        failed = len(self.results) - passed
        total_test_time = sum(duration for _, _, duration, _ in self.results)
        
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        # Summary
        print(f"📈 Overall Results:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📊 Success Rate: {(passed/len(self.results)*100):.1f}%")
        print(f"   ⏱️  Total Time: {total_duration:.2f}s")
        print(f"   🧪 Test Time: {total_test_time:.2f}s")
        print(f"   🔧 Overhead: {(total_duration - total_test_time):.2f}s")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for test_file, success, duration, _ in self.results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status} {test_file:<35} ({duration:.2f}s)")
        
        # Failed test details
        failed_tests = [(name, output) for name, success, _, output in self.results if not success]
        if failed_tests:
            print(f"\n🔍 Failed Test Details:")
            for test_name, output in failed_tests:
                print(f"\n   ❌ {test_name}:")
                # Show last few lines of output
                lines = output.strip().split('\n')
                for line in lines[-5:]:
                    print(f"      {line}")
        
        # Performance analysis
        print(f"\n⚡ Performance Analysis:")
        sorted_tests = sorted(self.results, key=lambda x: x[2], reverse=True)
        print(f"   🐌 Slowest Tests:")
        for test_file, _, duration, _ in sorted_tests[:3]:
            print(f"      {test_file:<35} {duration:.2f}s")
        
        print(f"   🚀 Fastest Tests:")
        for test_file, _, duration, _ in sorted_tests[-3:]:
            print(f"      {test_file:<35} {duration:.2f}s")
        
        # Module coverage analysis
        print(f"\n🎯 Module Coverage:")
        categories = {
            'Core': ['format_state', 'command_registry', 'object_registry'],
            'Setup': ['color_conversion', 'terminal', 'text_justification', 'text_wrapping', 'unicode', 'box_generation'],
            'Elements': ['elements', 'main_processor'],
            'Commands': ['command_processors', 'debug_commands', 'fmt_commands'],
            'Objects': ['object_processors', 'type_objects'],
            'Features': ['table', 'progress_bar'],
            'Integration': ['comprehensive_integration']
        }
        
        for category, modules in categories.items():
            category_results = [r for r in self.results if any(mod in r[0] for mod in modules)]
            if category_results:
                category_passed = sum(1 for _, success, _, _ in category_results if success)
                category_total = len(category_results)
                success_rate = (category_passed / category_total * 100) if category_total > 0 else 0
                print(f"   {category:<12} {category_passed}/{category_total} ({success_rate:.0f}%)")
        
        # Final verdict
        print("\n" + "=" * 60)
        if failed == 0:
            print("🎉 ALL TESTS PASSED! FDL MODULE IS READY FOR TESTING!")
        else:
            print(f"⚠️  {failed} TEST(S) FAILED. ISSUES NEED TO BE RESOLVED.")
        print("=" * 60)
        
        return {
            'total_tests': len(self.results),
            'passed': passed,
            'failed': failed,
            'success_rate': passed / len(self.results) * 100,
            'total_duration': total_duration,
            'test_duration': total_test_time,
            'results': self.results,
            'failed_tests': failed_tests
        }


def main():
    """Main entry point."""
    runner = TestRunner()
    
    try:
        results = runner.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if results['failed'] == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test run interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n💥 Test runner crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()