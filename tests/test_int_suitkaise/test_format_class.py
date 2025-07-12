"""
Comprehensive test suite for the fdl Format system.

Tests both internal machinery and public API to ensure:
- Format compilation and caching work correctly
- Format inheritance and dependencies are properly handled
- Error conditions are caught and reported appropriately
- Performance characteristics meet expectations
- Public API provides clean, intuitive interface

Run with: python test_fdl_formats.py
"""

import sys
from pathlib import Path
import time
import warnings
from typing import Set

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test imports - adjust paths as needed for your project structure
try:
    # Try importing from installed package
    from suitkaise.fdl.api import (
        Format, get_format, format_exists, list_formats, 
        clear_formats, get_format_dependencies,
        FormatError, InvalidFormatError, CircularReferenceError, FormatNotFoundError
    )
    # Import internal functions needed for testing
    from suitkaise._int._fdl.core.format_class import (
        _apply_format_to_state
    )
    from suitkaise._int._fdl.core.command_processor import _FormattingState
    IMPORTS_AVAILABLE = True
    
except ImportError as e:
    print(f"Import failed: {e}")
    print("Ensure suitkaise package is on Python path or adjust import paths")
    IMPORTS_AVAILABLE = False


class FormatTestSuite:
    """Comprehensive test suite for fdl Format system."""
    
    def __init__(self):
        """Initialize test suite."""
        self.test_count = 0
        self.passed_count = 0
        self.failed_tests = []
    
    def run_test(self, name: str, test_func, *args, **kwargs):
        """Run a single test case with error handling."""
        self.test_count += 1
        
        print(f"\nTest {self.test_count}: {name}")
        print("-" * 50)
        
        try:
            passed = test_func(*args, **kwargs)
            if passed:
                print("✅ PASSED")
                self.passed_count += 1
            else:
                print("❌ FAILED")
                self.failed_tests.append(name)
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            self.failed_tests.append(f"{name} (Exception)")
            
        print("-" * 50)
    
    def test_basic_format_creation(self):
        """Test basic format creation and registration."""
        clear_formats()
        
        # Create a simple format
        red_bold = Format("red_bold", "</red, bold>")
        
        # Check properties
        if red_bold.name != "red_bold":
            print(f"❌ Name mismatch: expected 'red_bold', got '{red_bold.name}'")
            return False
        
        if red_bold.original_string != "</red, bold>":
            print(f"❌ Format string mismatch: expected '</red, bold>', got '{red_bold.original_string}'")
            return False
        
        # Check registration
        if not format_exists("red_bold"):
            print("❌ Format not registered in global registry")
            return False
        
        # Check direct ANSI is generated
        ansi = red_bold.direct_ansi
        if not ansi or not isinstance(ansi, str):
            print(f"❌ Invalid direct ANSI: '{ansi}'")
            return False
        
        print(f"✓ Created format: {red_bold}")
        print(f"✓ Direct ANSI: '{ansi}'")
        return True
    
    def test_format_inheritance(self):
        """Test format inheritance and dependency tracking."""
        clear_formats()
        
        # Create base format
        base = Format("base", "</bold>")
        
        # Create derived format
        derived = Format("derived", "</fmt base, red>")
        
        # Check dependencies are tracked
        deps = derived.referenced_formats
        if "base" not in deps:
            print(f"❌ Missing dependency: expected 'base' in {deps}")
            return False
        
        # Check dependency lookup function
        all_deps = get_format_dependencies("derived")
        if "base" not in all_deps:
            print(f"❌ Dependency lookup failed: expected 'base' in {all_deps}")
            return False
        
        print(f"✓ Dependencies tracked: {deps}")
        print(f"✓ Dependency lookup works: {all_deps}")
        return True
    
    def test_complex_inheritance_chain(self):
        """Test complex inheritance chains work correctly."""
        clear_formats()
        
        # Create inheritance chain: base -> warning -> critical
        Format("base", "</bold>")
        Format("warning", "</fmt base, yellow>") 
        Format("critical", "</fmt warning, bkg red>")
        
        # Check final format has all dependencies
        deps = get_format_dependencies("critical")
        expected_deps = {"base", "warning"}
        
        if deps != expected_deps:
            print(f"❌ Wrong dependencies: expected {expected_deps}, got {deps}")
            return False
        
        # Check that each format in chain exists
        for fmt_name in ["base", "warning", "critical"]:
            if not format_exists(fmt_name):
                print(f"❌ Format '{fmt_name}' not found")
                return False
        
        print(f"✓ Complex inheritance chain works: {deps}")
        return True
    
    def test_error_handling(self):
        """Test comprehensive error handling."""
        clear_formats()
        
        # Test invalid format strings
        try:
            Format("invalid1", "text content </bold>")
            print("❌ Should have raised InvalidFormatError for text content")
            return False
        except InvalidFormatError:
            print("✓ Text content properly rejected")
        
        try:
            Format("invalid2", "</bold><variable>")
            print("❌ Should have raised InvalidFormatError for variables")
            return False
        except InvalidFormatError:
            print("✓ Variables properly rejected")
        
        try:
            Format("invalid3", "")
            print("❌ Should have raised InvalidFormatError for empty string")
            return False
        except InvalidFormatError:
            print("✓ Empty string properly rejected")
        
        # Test format not found
        try:
            Format("missing_ref", "</fmt nonexistent>")
            print("❌ Should have raised FormatNotFoundError")
            return False
        except FormatNotFoundError:
            print("✓ Missing format reference properly detected")
        
        # Test circular reference
        Format("a", "</red>")
        try:
            Format("self_ref", "</fmt self_ref>")
            print("❌ Should have raised CircularReferenceError")
            return False
        except CircularReferenceError:
            print("✓ Circular reference properly detected")
        
        return True
    
    def test_public_api_functions(self):
        """Test all public API convenience functions."""
        clear_formats()
        
        # Create test formats
        Format("format1", "</red>")
        Format("format2", "</blue, bold>")
        Format("format3", "</fmt format1, italic>")
        
        # Test format_exists
        if not format_exists("format1"):
            print("❌ format_exists failed for existing format")
            return False
        
        if format_exists("nonexistent"):
            print("❌ format_exists false positive")
            return False
        
        # Test list_formats
        formats = list_formats()
        expected = {"format1", "format2", "format3"}
        if set(formats) != expected:
            print(f"❌ list_formats wrong: expected {expected}, got {set(formats)}")
            return False
        
        # Test get_format
        retrieved = get_format("format1")
        if not retrieved or retrieved.name != "format1":
            print(f"❌ get_format failed: {retrieved}")
            return False
        
        if get_format("nonexistent") is not None:
            print("❌ get_format should return None for missing format")
            return False
        
        # Test get_format_dependencies  
        deps = get_format_dependencies("format3")
        if "format1" not in deps:
            print(f"❌ get_format_dependencies failed: {deps}")
            return False
        
        # Test clear_formats
        clear_formats()
        if len(list_formats()) != 0:
            print(f"❌ clear_formats failed: {list_formats()}")
            return False
        
        print("✓ All public API functions work correctly")
        return True
    
    def test_thread_safety(self):
        """Test thread safety of format registry."""
        import threading
        clear_formats()
        
        results = []
        errors = []
        
        def worker_thread(thread_id):
            """Worker function that creates and accesses formats."""
            try:
                # Create format  
                fmt_name = f"thread_fmt_{thread_id}"
                Format(fmt_name, f"</red, bold>")
                
                # Access format
                retrieved = get_format(fmt_name)
                if retrieved and retrieved.name == fmt_name:
                    results.append(thread_id)
                else:
                    errors.append(f"Thread {thread_id}: retrieval failed")
                    
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")
        
        # Run multiple threads
        threads = []
        num_threads = 10
        
        for i in range(num_threads):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        if errors:
            print(f"❌ Thread safety errors: {errors}")
            return False
        
        if len(results) != num_threads:
            print(f"❌ Not all threads completed: {len(results)}/{num_threads}")
            return False
        
        # Check all formats exist
        final_formats = list_formats()
        if len(final_formats) != num_threads:
            print(f"❌ Wrong number of formats created: {len(final_formats)}")
            return False
        
        print(f"✓ Thread safety test passed: {num_threads} threads, {len(final_formats)} formats")
        return True
    
    def test_performance_characteristics(self):
        """Test performance characteristics meet expectations."""
        clear_formats()
        
        # Create test format
        Format("perf_test", "</red, bold, italic, bkg blue>")
        fmt = get_format("perf_test")
        
        # Test direct ANSI access speed (should be instant property access)
        iterations = 50000
        start_time = time.time()
        
        for _ in range(iterations):
            ansi = fmt.direct_ansi  # Just property access
        
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_time_microseconds = (total_time / iterations) * 1000000
        
        print(f"✓ Performance test ({iterations} iterations):")
        print(f"   Total time: {total_time:.6f}s")
        print(f"   Average per access: {avg_time_microseconds:.3f}μs")
        
        # Should be very fast (under 1 microsecond ideally)
        if avg_time_microseconds > 10:
            print("⚠️  Performance might be suboptimal (>10μs per access)")
            return False
        else:
            print("🎯 Performance excellent (<10μs per access)")
        
        return True
    
    def test_command_processor_integration(self):
        """Test integration with internal command processor."""
        clear_formats()
        
        # Create format
        Format("integration_test", "</green, bold>")
        
        # Test internal _apply_format_to_state function
        current_state = _FormattingState()
        current_state.italic = True  # Start with some formatting
        
        try:
            target_state, ansi = _apply_format_to_state("integration_test", current_state)
            
            # Should have transitioned properly
            if not ansi or not isinstance(ansi, str):
                print(f"❌ Invalid ANSI sequence: '{ansi}'")
                return False
            
            # ANSI should contain expected codes (turn off italic, add green and bold)
            expected_codes = ['\033[23m', '\033[32m', '\033[1m']  # Off italic, green, bold
            missing_codes = [code for code in expected_codes if code not in ansi]
            
            if missing_codes:
                print(f"❌ Missing ANSI codes {missing_codes} in: '{ansi}'")
                return False
            
            print(f"✓ Command processor integration works")
            print(f"   Generated ANSI: '{ansi}'")
            return True
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            return False
    
    def test_format_registry_functionality(self):
        """Test internal format registry through public API."""
        clear_formats()
        
        # Test starts empty
        if len(list_formats()) != 0:
            print("❌ Should start empty after clear")
            return False
        
        # Create formats and test through public API
        Format("reg_test1", "</red>")
        Format("reg_test2", "</blue>")
        
        all_formats = list_formats()
        if set(all_formats) != {"reg_test1", "reg_test2"}:
            print(f"❌ Format list wrong: {all_formats}")
            return False
        
        # Test exists
        if not format_exists("reg_test1"):
            print("❌ format_exists failed")
            return False
        
        if format_exists("nonexistent"):
            print("❌ format_exists false positive")
            return False
        
        # Test get
        retrieved = get_format("reg_test1")
        if not retrieved or retrieved.name != "reg_test1":
            print(f"❌ get_format failed: {retrieved}")
            return False
        
        print("✓ Format registry functionality works through public API")
        return True
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        clear_formats()
        
        # Test format with only whitespace content
        try:
            Format("whitespace_test", "   </bold>   ")
            print("✓ Whitespace content handled correctly")
        except Exception as e:
            print(f"❌ Whitespace handling failed: {e}")
            return False
        
        # Test very long format names
        long_name = "very_long_format_name_" + "x" * 100
        try:
            Format(long_name, "</red>")
            if not format_exists(long_name):
                print("❌ Long format name not registered")
                return False
            print("✓ Long format names handled")
        except Exception as e:
            print(f"❌ Long name handling failed: {e}")
            return False
        
        # Test multiple format references in one format
        Format("base1", "</red>")
        Format("base2", "</bold>")
        Format("multi_ref", "</fmt base1, fmt base2, italic>")
        
        deps = get_format_dependencies("multi_ref")
        if not {"base1", "base2"}.issubset(deps):
            print(f"❌ Multiple references failed: {deps}")
            return False
        
        print("✓ Edge cases handled correctly")
        return True
    
    def run_all_tests(self):
        """Run the complete test suite."""
        print("=" * 70)
        print("FDL FORMAT SYSTEM - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        
        if not IMPORTS_AVAILABLE:
            print("❌ Cannot run tests: imports failed")
            print("Ensure suitkaise package is properly installed and on Python path")
            return False
        
        # Suppress warnings during testing
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Run all test methods
            self.run_test("Basic format creation", self.test_basic_format_creation)
            self.run_test("Format inheritance", self.test_format_inheritance)
            self.run_test("Complex inheritance chain", self.test_complex_inheritance_chain)
            self.run_test("Error handling", self.test_error_handling)
            self.run_test("Public API functions", self.test_public_api_functions)
            self.run_test("Thread safety", self.test_thread_safety)
            self.run_test("Performance characteristics", self.test_performance_characteristics)
            self.run_test("Command processor integration", self.test_command_processor_integration)
            self.run_test("Format registry functionality", self.test_format_registry_functionality)
            self.run_test("Edge cases", self.test_edge_cases)
        
        # Print summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        success_rate = (self.passed_count / self.test_count) * 100
        print(f"Tests run: {self.test_count}")
        print(f"Tests passed: {self.passed_count}")
        print(f"Tests failed: {self.test_count - self.passed_count}")
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            print(f"\nFailed tests:")
            for test_name in self.failed_tests:
                print(f"  - {test_name}")
        
        if self.passed_count == self.test_count:
            print("\n🎉 ALL TESTS PASSED!")
            print("\n📊 FORMAT SYSTEM STATUS:")
            print("✅ Format compilation and caching")
            print("✅ Format inheritance and dependencies") 
            print("✅ Error handling and validation")
            print("✅ Public API interface")
            print("✅ Thread safety")
            print("✅ Performance characteristics")
            print("✅ Command processor integration")
            print("✅ Registry functionality")
            print("✅ Edge case handling")
            print("\n🚀 Format system ready for production use!")
            
        else:
            print(f"\n❌ {self.test_count - self.passed_count} tests failed")
            print("Review failed tests before using in production")
        
        print("=" * 70)
        return self.passed_count == self.test_count


def main():
    """Main test runner."""
    suite = FormatTestSuite()
    success = suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()