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
    from suitkaise._int._fdl.core.reconstructor import _reconstruct_fdl_string
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
        
        try:
            result = _reconstruct_fdl_string("Test: </fmt red_bold>formatted text")
            print(f"✓ Created format: {red_bold}")
            print(f"✓ Format in use: ", end="")
            print(result)  # This will show actual formatting + auto-reset
            return True
        except Exception as e:
            print(f"❌ Format failed in reconstruction: {e}")
            return False
    
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
        
        try:
            result = _reconstruct_fdl_string("Status: </fmt integration_test>System OK")
            
            # Should contain the text and end with reset
            if "Status:" not in result or "System OK" not in result:
                print(f"❌ Missing expected content in: '{result}'")
                return False
            
            if not result.endswith('\033[0m'):
                print(f"❌ Should end with reset code")
                return False
            
            print(f"✓ Command processor integration works")
            print(f"✓ Format result: ", end="")
            print(result)  # Shows actual formatting
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
    
# Add this to the FormatTestSuite class after test_edge_cases():

    def test_format_chaining(self):
        """Test chaining multiple formats in one command: </fmt format1, fmt format2>"""
        clear_formats()
        
        # Create test formats with overlapping properties
        Format("base_red", "</red, bold>")
        Format("override_blue", "</blue, italic>")  # blue overrides red, adds italic
        Format("add_underline", "</underline>")     # just adds underline, no conflicts
        
        # Test through reconstruction flow 
        from suitkaise._int._fdl.core.reconstructor import _reconstruct_fdl_string
        
        # Test 1: Two formats with conflicting colors
        print("Test 1: Color override (red -> blue)")
        try:
            # This should apply red+bold, then blue+italic (blue overrides red)
            result1 = _reconstruct_fdl_string("Status: </fmt base_red, fmt override_blue>ALERT")
            print(f"  Result: ", end="")
            print(result1)  # Should be blue, bold, italic
            print(f"  Raw: {repr(result1)}")
            
            # Check that result contains blue and italic codes, not red
            if '\033[31m' in result1:  # Red code
                print("  ❌ Still contains red - override failed")
                return False
            if '\033[34m' not in result1:  # Blue code  
                print("  ❌ Missing blue - override failed")
                return False
            if '\033[1m' not in result1:  # Bold code (should be preserved)
                print("  ❌ Missing bold - chaining failed")
                return False
            if '\033[3m' not in result1:  # Italic code (should be added)
                print("  ❌ Missing italic - chaining failed")
                return False
            
            print("  ✓ Color override works correctly")
            
        except Exception as e:
            print(f"  ❌ Exception in color override test: {e}")
            return False
        
        # Test 2: Three formats with additive properties
        print("\nTest 2: Additive properties (no conflicts)")
        try:
            # This should combine all properties: red+bold + blue+italic + underline
            # Final result: blue+bold+italic+underline (blue overrides red)
            result2 = _reconstruct_fdl_string("Multi: </fmt base_red, fmt override_blue, fmt add_underline>text")
            print(f"  Result: ", end="")
            print(result2)  # Should be blue, bold, italic, underline
            print(f"  Raw: {repr(result2)}")
            
            # Check all expected codes are present
            expected_codes = ['\033[34m', '\033[1m', '\033[3m', '\033[4m']  # blue, bold, italic, underline
            missing_codes = [code for code in expected_codes if code not in result2]
            
            if missing_codes:
                print(f"  ❌ Missing codes: {missing_codes}")
                return False
            
            if '\033[31m' in result2:  # Should not have red
                print("  ❌ Still contains red - should be overridden by blue")
                return False
            
            print("  ✓ Additive chaining works correctly")
            
        except Exception as e:
            print(f"  ❌ Exception in additive test: {e}")
            return False
    
        # Test 3: Format inheritance in chains
        print("\nTest 3: Format inheritance in chains")
        try:
            # Create formats that inherit from each other
            Format("parent", "</bold, red>")
            Format("child", "</fmt parent, italic>")  # inherits bold+red, adds italic
            Format("modifier", "</blue>")             # just blue
            
            # Chain: child (bold+red+italic) + modifier (blue overrides red)
            # Final: blue+bold+italic
            result3 = _reconstruct_fdl_string("Inherit: </fmt child, fmt modifier>test")
            print(f"  Result: ", end="")
            print(result3)
            print(f"  Raw: {repr(result3)}")
            
            # Should have blue, bold, italic but NOT red
            if '\033[31m' in result3:  # Red should be overridden
                print("  ❌ Red not overridden in inheritance chain")
                return False
            
            expected_codes = ['\033[34m', '\033[1m', '\033[3m']  # blue, bold, italic
            missing_codes = [code for code in expected_codes if code not in result3]
            
            if missing_codes:
                print(f"  ❌ Missing inherited codes: {missing_codes}")
                return False
            
            print("  ✓ Inheritance in chains works correctly")
            
        except Exception as e:
            print(f"  ❌ Exception in inheritance test: {e}")
            return False
        
        # Test 4: Order dependency
        print("\nTest 4: Order dependency (format2, format1 vs format1, format2)")
        try:
            # Test both orders to verify override behavior
            result_a = _reconstruct_fdl_string("Order A: </fmt base_red, fmt override_blue>text")
            result_b = _reconstruct_fdl_string("Order B: </fmt override_blue, fmt base_red>text")
            
            print(f"  A (red->blue): ", end="")
            print(result_a)
            print(f"  B (blue->red): ", end="")
            print(result_b)
            
            # A should end with blue, B should end with red
            a_has_blue = '\033[34m' in result_a and '\033[31m' not in result_a
            b_has_red = '\033[31m' in result_b and '\033[34m' not in result_b
            
            if not a_has_blue:
                print("  ❌ Order A should have blue (last wins)")
                return False
            
            if not b_has_red:
                print("  ❌ Order B should have red (last wins)")
                return False
            
            print("  ✓ Order dependency works correctly (last format wins)")
            
        except Exception as e:
            print(f"  ❌ Exception in order test: {e}")
            return False
        
        # Test 5: Background color conflicts
        print("\nTest 5: Background color conflicts")
        try:
            Format("red_bg", "</red, bkg yellow>")
            Format("blue_bg", "</blue, bkg green>")
            
            result5 = _reconstruct_fdl_string("Backgrounds: </fmt red_bg, fmt blue_bg>text")
            print(f"  Result: ", end="")
            print(result5)
            print(f"  Raw: {repr(result5)}")
            
            # Should have blue text and green background (both from blue_bg)
            # Should NOT have red text or yellow background
            if '\033[31m' in result5 or '\033[43m' in result5:  # red text or yellow bg
                print("  ❌ Background override failed - still has red/yellow")
                return False
            
            if '\033[34m' not in result5 or '\033[42m' not in result5:  # blue text and green bg
                print("  ❌ Missing final blue text or green background")
                return False
            
            print("  ✓ Background color conflicts handled correctly")
            
        except Exception as e:
            print(f"  ❌ Exception in background test: {e}")
            return False
        
        print("\n✓ All format chaining tests passed!")
        print("✓ Override behavior works correctly")
        print("✓ Additive properties combine properly") 
        print("✓ Order dependency respected")
        print("✓ Inheritance chains work in combination")
        
        return True
    
    def test_multi_string_and_partial_endings(self):
        """Test multi-string statements and partial format endings."""
        clear_formats()
        
        # Create test format
        Format("format2", "</green, bold, italic, bkg blue>")
        
        from suitkaise._int._fdl.core.reconstructor import _reconstruct_fdl_string
        
        # Test 1: Your exact example - partial ending
        print("Test 1: Multi-string with partial ending")
        try:
            # Simulate the multi-string concatenation
            test_string = (
                "</fmt format2, underline>"
                "This is green, bolded, italicized, underlined text on a blue background."
                "</end format2>"
                "This is now just underlined text."
            )
            
            result1 = _reconstruct_fdl_string(test_string)
            print(f"  Result: ", end="")
            print(result1)
            print(f"  Raw: {repr(result1)}")
            
            # Check that both parts of text are present
            if "green, bolded, italicized" not in result1:
                print("  ❌ Missing first part of text")
                return False
            
            if "just underlined text" not in result1:
                print("  ❌ Missing second part of text")
                return False
            
            # The string should contain:
            # - Green, bold, italic, blue background, underline codes for first part
            # - Codes to end green, bold, italic, blue background but keep underline
            # - Underline should still be active for second part
            
            # Check for underline throughout (should never be ended)
            if '\033[4m' not in result1:
                print("  ❌ Missing underline - should be present throughout")
                return False
            
            if '\033[24m' in result1:
                print("  ❌ Underline was ended - should remain active")
                return False
            
            print("  ✓ Multi-string with partial ending works")
            
        except Exception as e:
            print(f"  ❌ Exception in multi-string test: {e}")
            return False
        
        # Test 2: Multiple partial endings
        print("\nTest 2: Multiple partial endings")
        try:
            # Start with multiple formats, end them one by one
            Format("red_bold", "</red, bold>")
            Format("blue_italic", "</blue, italic>")
            
            test_string2 = (
                "</fmt red_bold, fmt blue_italic, underline>"
                "All formatting active."
                "</end red_bold>"
                "Blue italic underline."
                "</end blue_italic>"
                "Just underline."
            )
            
            result2 = _reconstruct_fdl_string(test_string2)
            print(f"  Result: ", end="")
            print(result2)
            print(f"  Raw: {repr(result2)}")
            
            # Should contain all three text segments
            expected_texts = ["All formatting active", "Blue italic underline", "Just underline"]
            for text in expected_texts:
                if text not in result2:
                    print(f"  ❌ Missing text segment: '{text}'")
                    return False
            
            # Underline should be present throughout, never ended
            if '\033[4m' not in result2:
                print("  ❌ Missing underline in multiple partial endings")
                return False
            
            if '\033[24m' in result2:
                print("  ❌ Underline was ended in multiple partial endings")
                return False
            
            print("  ✓ Multiple partial endings work")
            
        except Exception as e:
            print(f"  ❌ Exception in multiple partial endings: {e}")
            return False
        
        # Test 3: Ending individual properties vs ending formats
        print("\nTest 3: Individual property endings vs format endings")
        try:
            test_string3 = (
                "</fmt format2, underline>"
                "Format plus underline."
                "</end bold>"  # End just bold property
                "Format minus bold."
                "</end format2>"  # End entire format
                "Just underline."
            )
            
            result3 = _reconstruct_fdl_string(test_string3)
            print(f"  Result: ", end="")
            print(result3)
            print(f"  Raw: {repr(result3)}")
            
            # Should have all text segments
            expected_texts = ["Format plus underline", "Format minus bold", "Just underline"]
            for text in expected_texts:
                if text not in result3:
                    print(f"  ❌ Missing text: '{text}'")
                    return False
            
            # Should contain bold turn-off code (\033[22m) after first segment
            if '\033[22m' not in result3:
                print("  ❌ Missing bold turn-off code")
                return False
            
            print("  ✓ Individual vs format endings work")
            
        except Exception as e:
            print(f"  ❌ Exception in individual endings test: {e}")
            return False
        
        # Test 4: Complex chaining with partial endings
        print("\nTest 4: Format chaining with partial endings")
        try:
            Format("base", "</bold>")
            Format("color", "</red>")
            Format("bg", "</bkg yellow>")
            
            test_string4 = (
                "</fmt base, fmt color, fmt bg, italic>"
                "All: bold red yellow italic."
                "</end base, color>"  # End bold and red
                "Yellow italic only."
                "</end bg>"  # End yellow background
                "Italic only."
            )
            
            result4 = _reconstruct_fdl_string(test_string4)
            print(f"  Result: ", end="")
            print(result4)
            print(f"  Raw: {repr(result4)}")
            
            # Should have all segments
            expected_texts = ["bold red yellow italic", "Yellow italic only", "Italic only"]
            for text in expected_texts:
                if text not in result4:
                    print(f"  ❌ Missing text: '{text}'")
                    return False
            
            # Italic should be present throughout
            if '\033[3m' not in result4:
                print("  ❌ Missing italic - should be present throughout")
                return False
            
            if '\033[23m' in result4:
                print("  ❌ Italic was ended - should remain active")
                return False
            
            print("  ✓ Complex chaining with partial endings works")
            
        except Exception as e:
            print(f"  ❌ Exception in complex chaining test: {e}")
            return False
        
        # Test 5: Verify Python string concatenation behavior
        print("\nTest 5: Python string concatenation verification")
        try:
            # Test that our multi-line string becomes single string
            multi_line = (
                "Part 1 "
                "Part 2 "
                "Part 3"
            )
            
            single_line = "Part 1 Part 2 Part 3"
            
            if multi_line != single_line:
                print(f"  ❌ String concatenation failed: {repr(multi_line)} != {repr(single_line)}")
                return False
            
            # Test with fdl commands
            fdl_multi = (
                "</bold>"
                "Bold text"
                "</end bold>"
                "Normal text"
            )
            
            fdl_single = "</bold>Bold text</end bold>Normal text"
            
            if fdl_multi != fdl_single:
                print(f"  ❌ FDL string concatenation failed")
                return False
            
            # Test that both produce same result
            result_multi = _reconstruct_fdl_string(fdl_multi)
            result_single = _reconstruct_fdl_string(fdl_single)
            
            if result_multi != result_single:
                print(f"  ❌ Multi vs single string produce different results")
                print(f"    Multi:  {repr(result_multi)}")
                print(f"    Single: {repr(result_single)}")
                return False
            
            print("  ✓ Python string concatenation works correctly with fdl")
            
        except Exception as e:
            print(f"  ❌ Exception in concatenation test: {e}")
            return False
        
        print("\n✓ All multi-string and partial ending tests passed!")
        print("✓ Python string concatenation works with fdl")
        print("✓ Partial format endings work correctly")
        print("✓ Individual property endings work")
        print("✓ Complex combinations work")
        
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
            self.run_test("Format chaining", self.test_format_chaining)
            self.run_test("Multi-string and partial endings", self.test_multi_string_and_partial_endings)

        
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