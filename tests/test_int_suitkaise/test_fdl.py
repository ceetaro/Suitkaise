#!/usr/bin/env python3
"""
Comprehensive test suite for FDL core components.

Tests all core functionality:
- Parser: command/variable/object extraction
- Command Processor: ANSI generation with caching
- Object Processor: time/date/elapsed handling
- Format Class: compilation and inheritance
- Reconstructor: final string assembly
- Integration: end-to-end functionality

Run with: python comprehensive_fdl_test.py
"""

import sys
import os
import time
import threading
import warnings
from pathlib import Path
from typing import Set, List, Optional, Tuple

# Add project paths for imports
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent
core_path = project_root / "suitkaise" / "_int" / "_fdl" / "core"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(core_path))

# Set environment variable to help with imports
os.environ["PYTHONPATH"] = str(core_path)

print("=" * 70)
print("COMPREHENSIVE FDL CORE TEST SUITE")
print("=" * 70)

# Try to import all modules with fallbacks
IMPORTS_AVAILABLE = True
import_errors = []

try:
    # Parser
    from parser import _fdlParser, _parse_fdl_string
    print("✓ Parser imported successfully")
except Exception as e:
    print(f"❌ Parser import failed: {e}")
    import_errors.append(f"Parser: {e}")
    IMPORTS_AVAILABLE = False

try:
    # Command Processor
    from command_processor import (
        _CommandProcessor, _get_command_processor, _FormattingState, 
        _ANSIConverter, CommandError, InvalidCommandError, UnsupportedCommandError
    )
    print("✓ Command Processor imported successfully")
except Exception as e:
    print(f"❌ Command Processor import failed: {e}")
    import_errors.append(f"Command Processor: {e}")
    IMPORTS_AVAILABLE = False

try:
    # Object Processor
    from object_processor import (
        _ObjectProcessor, _get_object_processor, _TimeZoneHandler,
        ObjectProcessorError, InvalidObjectError, UnsupportedObjectError
    )
    print("✓ Object Processor imported successfully")
except Exception as e:
    print(f"❌ Object Processor import failed: {e}")
    import_errors.append(f"Object Processor: {e}")
    IMPORTS_AVAILABLE = False

try:
    # Format Class
    from format_class import (
        _compile_format_string, _register_compiled_format, _get_compiled_format,
        _format_exists_internal, _list_all_formats_internal, _clear_all_formats_internal,
        _get_format_dependencies_internal, FormatError, InvalidFormatError,
        CircularReferenceError, FormatNotFoundError, _get_format_registry
    )
    print("✓ Format Class imported successfully")
except Exception as e:
    print(f"❌ Format Class import failed: {e}")
    import_errors.append(f"Format Class: {e}")
    IMPORTS_AVAILABLE = False

try:
    # Reconstructor
    from reconstructor import (
        _reconstruct_fdl_string, ReconstructionError, VariableMismatchError
    )
    print("✓ Reconstructor imported successfully")
except Exception as e:
    print(f"❌ Reconstructor import failed: {e}")
    import_errors.append(f"Reconstructor: {e}")
    IMPORTS_AVAILABLE = False

if not IMPORTS_AVAILABLE:
    print("\n" + "=" * 70)
    print("IMPORT FAILURES")
    print("=" * 70)
    for error in import_errors:
        print(f"  {error}")
    print("\nCannot run tests without all modules available.")
    sys.exit(1)

print("✓ All modules imported successfully!\n")


class ComprehensiveFDLTestSuite:
    """Complete test suite for all FDL core components."""
    
    def __init__(self):
        """Initialize test suite."""
        self.test_count = 0
        self.passed_count = 0
        self.failed_tests = []
        self.section_results = {}
    
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
    
    def run_section(self, section_name: str, tests: List[Tuple[str, callable]]):
        """Run a section of tests and track results."""
        print(f"\n{'='*20} {section_name} {'='*20}")
        
        section_start_count = self.passed_count
        section_start_total = self.test_count
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        section_passed = self.passed_count - section_start_count
        section_total = self.test_count - section_start_total
        section_rate = (section_passed / section_total * 100) if section_total > 0 else 0
        
        self.section_results[section_name] = {
            'passed': section_passed,
            'total': section_total,
            'rate': section_rate
        }
        
        print(f"\n{section_name} Results: {section_passed}/{section_total} ({section_rate:.1f}%)")
    
    # ===============================
    # PARSER TESTS
    # ===============================
    
    def test_parser_basic(self):
        """Test basic parser functionality."""
        parser = _fdlParser()
        
        # Test 1: Simple text only
        result = parser.parse("Hello world")
        if len(result.text_segments) != 1 or result.text_segments[0].content != "Hello world":
            print("❌ Simple text parsing failed")
            return False
        
        # Test 2: Single command
        result = parser.parse("Text </bold>more text")
        if (len(result.commands) != 1 or result.commands[0].content != "bold" or
            len(result.text_segments) != 2):
            print("❌ Single command parsing failed")
            return False
        
        # Test 3: Multiple commands at same position
        result = parser.parse("Text </bold, italic>styled")
        if (len(result.commands) != 2 or 
            result.commands[0].content != "bold" or 
            result.commands[1].content != "italic" or
            result.commands[0].position != result.commands[1].position):
            print("❌ Multiple commands parsing failed")
            return False
        
        # Test 4: Variables
        result = parser.parse("Hello <name>!", ("Alice",))
        if (len(result.variables) != 1 or result.variables[0].content != "name"):
            print("❌ Variable parsing failed")
            return False
        
        # Test 5: Objects
        result = parser.parse("Time: <time:timestamp>", (123456,))
        if (len(result.objects) != 1 or result.objects[0].content != "time:timestamp"):
            print("❌ Object parsing failed")
            return False
        
        print("✓ All basic parser tests passed")
        return True
    
    def test_parser_complex(self):
        """Test complex parser scenarios."""
        parser = _fdlParser()
        
        # Test mixed content
        result = parser.parse("User </bold><name></end bold> at </12hr, time:login>", ("Alice", 123456))
        
        # Should have: text, bold, name, end bold, text, 12hr+time:login
        expected_positions = {
            0: ['text'],  # "User "
            1: ['command'],  # "bold"
            2: ['variable'],  # "name" 
            3: ['command'],  # "end bold"
            4: ['text'],  # " at "
            5: ['command', 'object']  # "12hr" + "time:login"
        }
        
        # Group elements by position
        positions = {}
        for elem in result.elements:
            if elem.position not in positions:
                positions[elem.position] = []
            positions[elem.position].append(elem.element_type)
        
        for pos, expected_types in expected_positions.items():
            if pos not in positions:
                print(f"❌ Missing position {pos}")
                return False
            if sorted(positions[pos]) != sorted(expected_types):
                print(f"❌ Wrong types at position {pos}: expected {expected_types}, got {positions[pos]}")
                return False
        
        print("✓ Complex parser test passed")
        return True
    
    # ===============================
    # COMMAND PROCESSOR TESTS
    # ===============================
    
    def test_command_processor_basic(self):
        """Test basic command processor functionality."""
        processor = _get_command_processor()
        initial_state = _FormattingState()
        
        # Test 1: Text formatting
        new_state, ansi = processor.process_command("bold", initial_state)
        if not new_state.bold or ansi != '\033[1m':
            print(f"❌ Bold failed: bold={new_state.bold}, ansi='{ansi}'")
            return False
        
        # Test 2: Color
        new_state, ansi = processor.process_command("red", initial_state)
        if new_state.text_color != "red" or ansi != '\033[31m':
            print(f"❌ Red failed: color={new_state.text_color}, ansi='{ansi}'")
            return False
        
        # Test 3: Background
        new_state, ansi = processor.process_command("bkg blue", initial_state)
        if new_state.background_color != "blue" or ansi != '\033[44m':
            print(f"❌ Background failed: bg={new_state.background_color}, ansi='{ansi}'")
            return False
        
        # Test 4: Batch processing
        commands = ["bold", "red", "bkg blue"]
        new_state, ansi = processor.process_commands(commands, initial_state)
        expected_ansi = '\033[1m\033[31m\033[44m'
        if ansi != expected_ansi:
            print(f"❌ Batch failed: expected='{expected_ansi}', got='{ansi}'")
            return False
        
        print("✓ Command processor basic tests passed")
        return True
    
    def test_command_processor_performance(self):
        """Test command processor performance and caching."""
        processor = _get_command_processor()
        
        # Test caching performance
        state1 = _FormattingState()
        state1.bold = True
        state2 = _FormattingState() 
        state2.bold = True
        state2.italic = True
        
        # First call (cache miss)
        ansi1 = processor.converter.generate_transition_ansi(state1, state2)
        
        # Second call (should hit cache)
        ansi2 = processor.converter.generate_transition_ansi(state1, state2)
        
        if ansi1 != ansi2:
            print("❌ Caching inconsistency")
            return False
        
        # Check cache stats
        stats = processor.get_performance_stats()
        if stats['cache_hits'] == 0:
            print("❌ No cache hits recorded")
            return False
        
        print(f"✓ Cache stats: {stats['cache_hits']} hits, {stats['cache_misses']} misses")
        return True
    
    # ===============================
    # OBJECT PROCESSOR TESTS
    # ===============================
    
    def test_object_processor_basic(self):
        """Test basic object processor functionality."""
        processor = _get_object_processor()
        
        # Test 1: Current time
        result, new_idx = processor.process_object("time:", [], (), 0)
        if not result or ':' not in result:
            print(f"❌ Current time failed: '{result}'")
            return False
        
        # Test 2: Timestamp
        timestamp = 1640995200.0  # 2022-01-01 00:00:00 UTC
        result, new_idx = processor.process_object("time:ts", [], (timestamp,), 0)
        if new_idx != 1 or "00:00:00" not in result:
            print(f"❌ Timestamp failed: '{result}', idx={new_idx}")
            return False
        
        # Test 3: 12hr format
        result, _ = processor.process_object("time:ts", ["12hr"], (timestamp,), 0)
        if "AM" not in result and "PM" not in result:
            print(f"❌ 12hr format failed: '{result}'")
            return False
        
        # Test 4: Elapsed time
        past_time = time.time() - 3665  # ~1h 1m ago
        result, _ = processor.process_object("elapsed:ts", [], (past_time,), 0)
        if "h" not in result or "m" not in result:
            print(f"❌ Elapsed failed: '{result}'")
            return False
        
        print("✓ Object processor basic tests passed")
        return True
    
    def test_object_processor_commands(self):
        """Test object processor command handling."""
        processor = _get_object_processor()
        timestamp = time.time() - 3600  # 1 hour ago
        
        # Test elapsed with time ago
        result, _ = processor.process_object("elapsed:ts", ["time ago"], (timestamp,), 0)
        if "ago" not in result:
            print(f"❌ Time ago failed: '{result}'")
            return False
        
        # Test timezone conversion
        result, _ = processor.process_object("time:ts", ["tz pst"], (1640995200.0,), 0)
        if "16:00:00" not in result:  # PST is UTC-8
            print(f"❌ Timezone failed: '{result}'")
            return False
        
        # Test smart formatting
        long_ago = time.time() - (2 * 86400 + 3 * 3600 + 15 * 60)  # 2d 3h 15m ago
        result, _ = processor.process_object("elapsed:ts", ["smart units 1"], (long_ago,), 0)
        if "d" not in result or "h" in result:  # Should only show days
            print(f"❌ Smart units failed: '{result}'")
            return False
        
        print("✓ Object processor command tests passed")
        return True
    
    # ===============================
    # FORMAT CLASS TESTS
    # ===============================
    
    def test_format_class_basic(self):
        """Test basic format class functionality."""
        _clear_all_formats_internal()
        
        # Test 1: Create simple format
        try:
            compiled = _compile_format_string("test_format", "</bold, red>")
            _register_compiled_format(compiled)
        except Exception as e:
            print(f"❌ Format creation failed: {e}")
            return False
        
        if not _format_exists_internal("test_format"):
            print("❌ Format not registered")
            return False
        
        # Test 2: Check compiled properties
        retrieved = _get_compiled_format("test_format")
        if not retrieved:
            print("❌ Could not retrieve format")
            return False
        
        state = retrieved.formatting_state
        if not state.bold or state.text_color != "red":
            print(f"❌ Wrong state: bold={state.bold}, color={state.text_color}")
            return False
        
        # Test 3: Direct ANSI
        expected_ansi = '\033[1m\033[31m'  # bold + red
        if retrieved.direct_ansi != expected_ansi:
            print(f"❌ Wrong ANSI: expected '{expected_ansi}', got '{retrieved.direct_ansi}'")
            return False
        
        print("✓ Format class basic tests passed")
        return True
    
    def test_format_class_inheritance(self):
        """Test format inheritance - THE KEY TEST!"""
        _clear_all_formats_internal()
        
        # Create parent format
        try:
            parent = _compile_format_string("parent", "</bold, red>")
            _register_compiled_format(parent)
            print(f"✓ Created parent: bold={parent.formatting_state.bold}, color={parent.formatting_state.text_color}")
        except Exception as e:
            print(f"❌ Parent creation failed: {e}")
            return False
        
        # Create child format that inherits from parent
        try:
            child = _compile_format_string("child", "</fmt parent, italic>")
            _register_compiled_format(child)
            
            child_state = child.formatting_state
            print(f"✓ Created child: bold={child_state.bold}, italic={child_state.italic}, color={child_state.text_color}")
            
            # Check inheritance worked
            if not child_state.bold:
                print("❌ Child did not inherit bold from parent")
                return False
            if child_state.text_color != "red":
                print("❌ Child did not inherit red color from parent")
                return False
            if not child_state.italic:
                print("❌ Child did not add italic")
                return False
            
        except Exception as e:
            print(f"❌ Child creation failed: {e}")
            return False
        
        # Test dependencies
        deps = _get_format_dependencies_internal("child")
        if "parent" not in deps:
            print(f"❌ Dependencies not tracked: {deps}")
            return False
        
        print("✓ Format inheritance works correctly!")
        print(f"  ✓ Child inherited bold and red from parent")
        print(f"  ✓ Child added italic")
        print(f"  ✓ Dependencies tracked: {deps}")
        return True
    
    def test_format_class_chaining(self):
        """Test format chaining in reconstructor."""
        _clear_all_formats_internal()
        
        # Create the test formats
        parent = _compile_format_string("parent", "</bold, red>")
        _register_compiled_format(parent)
        
        child = _compile_format_string("child", "</fmt parent, italic>") 
        _register_compiled_format(child)
        
        modifier = _compile_format_string("modifier", "</blue>")
        _register_compiled_format(modifier)
        
        # Test chaining through reconstructor
        test_string = "Inherit: </fmt child, fmt modifier>test"
        try:
            result = _reconstruct_fdl_string(test_string)
            
            print(f"✓ Reconstructed: {repr(result)}")
            
            # Check for expected codes
            has_bold = '\033[1m' in result
            has_italic = '\033[3m' in result
            has_blue = '\033[34m' in result
            has_red = '\033[31m' in result  # Should NOT be present
            
            print(f"  Bold: {has_bold}, Italic: {has_italic}, Blue: {has_blue}, Red: {has_red}")
            
            if not has_bold:
                print("❌ Missing bold (inheritance failed)")
                return False
            if not has_italic:
                print("❌ Missing italic (child format failed)")
                return False
            if not has_blue:
                print("❌ Missing blue (modifier failed)")
                return False
            if has_red:
                print("❌ Red present (override failed)")
                return False
            
            print("✓ Format chaining works correctly!")
            print("  ✓ Inherited properties preserved")
            print("  ✓ Color override worked")
            return True
            
        except Exception as e:
            print(f"❌ Chaining test failed: {e}")
            return False
    
    # ===============================
    # RECONSTRUCTOR TESTS
    # ===============================
    
    def test_reconstructor_basic(self):
        """Test basic reconstructor functionality."""
        
        # Test 1: Simple text
        result = _reconstruct_fdl_string("Hello world")
        if "Hello world" not in result or not result.endswith('\033[0m'):
            print(f"❌ Simple text failed: '{result}'")
            return False
        
        # Test 2: Variable substitution
        result = _reconstruct_fdl_string("Hello <name>!", ("Alice",))
        if "Hello Alice!" not in result:
            print(f"❌ Variable substitution failed: '{result}'")
            return False
        
        # Test 3: Basic formatting
        result = _reconstruct_fdl_string("This is </bold>bold text")
        if '\033[1m' not in result or "bold text" not in result:
            print(f"❌ Basic formatting failed: '{result}'")
            return False
        
        # Test 4: Time objects
        result = _reconstruct_fdl_string("Time: <time:>")
        if "Time:" not in result or ':' not in result:
            print(f"❌ Time object failed: '{result}'")
            return False
        
        print("✓ Reconstructor basic tests passed")
        return True
    
    def test_reconstructor_complex(self):
        """Test complex reconstructor scenarios."""
        
        # Test mixed content with objects and commands
        timestamp = time.time() - 3600  # 1 hour ago
        result = _reconstruct_fdl_string(
            "Login </time ago, elapsed:login_time> with </bold><username>",
            (timestamp, "Alice")
        )
        
        if "ago" not in result or "Alice" not in result:
            print(f"❌ Complex mixing failed: '{result}'")
            return False
        
        # Test format bleed prevention
        result1 = _reconstruct_fdl_string("</bold>Bold text")
        result2 = _reconstruct_fdl_string("Normal text")
        
        if not result1.endswith('\033[0m'):
            print("❌ Missing auto-reset")
            return False
        
        print("✓ Reconstructor complex tests passed")
        return True
    
    # ===============================
    # INTEGRATION TESTS  
    # ===============================
    
    def test_integration_end_to_end(self):
        """Test complete end-to-end integration."""
        _clear_all_formats_internal()
        
        # Create formats with inheritance
        parent = _compile_format_string("error_base", "</bold, red>")
        _register_compiled_format(parent)
        
        child = _compile_format_string("critical_error", "</fmt error_base, underline, bkg yellow>")
        _register_compiled_format(child)
        
        # Test complex fdl string with everything
        current_time = time.time()
        login_time = current_time - 8274  # ~2h 17m ago
        
        fdl_string = (
            "System Alert at </smart units 2, time:current_time>:\n"
            "</fmt critical_error>CRITICAL ERROR:</end critical_error> "
            "User <username> login failed (<elapsed:login_time> ago)\n"
            "Details: </italic>Authentication timeout</end italic>"
        )
        
        values = (current_time, "admin_user", login_time)
        
        try:
            result = _reconstruct_fdl_string(fdl_string, values)
            
            # Check components are present
            checks = [
                ("time object", ":" in result),
                ("username variable", "admin_user" in result),
                ("elapsed object", "ago" in result),
                ("critical format", '\033[1m' in result),  # bold
                ("format end", "CRITICAL ERROR:" in result),
                ("italic", '\033[3m' in result),
                ("auto reset", result.endswith('\033[0m'))
            ]
            
            failed_checks = [name for name, check in checks if not check]
            
            if failed_checks:
                print(f"❌ Failed checks: {failed_checks}")
                print(f"Result: {repr(result)}")
                return False
            
            print("✓ End-to-end integration successful!")
            print(f"✓ All components working together")
            return True
            
        except Exception as e:
            print(f"❌ Integration test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_integration_performance(self):
        """Test overall system performance."""
        
        # Test repeated format usage
        iterations = 1000
        start_time = time.time()
        
        for i in range(iterations):
            result = _reconstruct_fdl_string(
                "Message <i>: </bold>Status OK",
                (i,)
            )
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_ms = (total_time / iterations) * 1000
        
        print(f"✓ Performance test:")
        print(f"  {iterations} iterations in {total_time:.4f}s")
        print(f"  Average: {avg_time_ms:.3f}ms per operation")
        
        if avg_time_ms > 10:  # Arbitrary threshold
            print("⚠️  Performance might be suboptimal")
            return False
        
        print("🎯 Performance excellent!")
        return True
    
    def run_all_tests(self):
        """Run the complete test suite."""
        print("Starting comprehensive FDL core test suite...\n")
        
        # Parser tests
        parser_tests = [
            ("Basic parser functionality", self.test_parser_basic),
            ("Complex parser scenarios", self.test_parser_complex),
        ]
        self.run_section("PARSER", parser_tests)
        
        # Command processor tests
        command_tests = [
            ("Basic command processing", self.test_command_processor_basic),
            ("Performance and caching", self.test_command_processor_performance),
        ]
        self.run_section("COMMAND PROCESSOR", command_tests)
        
        # Object processor tests
        object_tests = [
            ("Basic object processing", self.test_object_processor_basic),
            ("Object command handling", self.test_object_processor_commands),
        ]
        self.run_section("OBJECT PROCESSOR", object_tests)
        
        # Format class tests
        format_tests = [
            ("Basic format functionality", self.test_format_class_basic),
            ("Format inheritance", self.test_format_class_inheritance),
            ("Format chaining", self.test_format_class_chaining),
        ]
        self.run_section("FORMAT CLASS", format_tests)
        
        # Reconstructor tests
        reconstructor_tests = [
            ("Basic reconstruction", self.test_reconstructor_basic),
            ("Complex reconstruction", self.test_reconstructor_complex),
        ]
        self.run_section("RECONSTRUCTOR", reconstructor_tests)
        
        # Integration tests
        integration_tests = [
            ("End-to-end integration", self.test_integration_end_to_end),
            ("Performance integration", self.test_integration_performance),
        ]
        self.run_section("INTEGRATION", integration_tests)
        
        # Print final summary
        self.print_final_summary()
        
        return self.passed_count == self.test_count
    
    def print_final_summary(self):
        """Print comprehensive test results."""
        print("\n" + "=" * 70)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 70)
        
        # Section breakdown
        for section, results in self.section_results.items():
            status = "✅" if results['rate'] == 100 else "❌" if results['rate'] < 50 else "⚠️"
            print(f"{status} {section}: {results['passed']}/{results['total']} ({results['rate']:.1f}%)")
        
        # Overall results
        success_rate = (self.passed_count / self.test_count) * 100
        print(f"\nOverall Results: {self.passed_count}/{self.test_count} ({success_rate:.1f}%)")
        
        if self.failed_tests:
            print(f"\nFailed tests:")
            for test_name in self.failed_tests:
                print(f"  - {test_name}")
        
        if self.passed_count == self.test_count:
            print("\n🎉 ALL TESTS PASSED!")
            print("\n📊 FDL CORE SYSTEM STATUS:")
            print("✅ Parser: command/variable/object extraction")
            print("✅ Command Processor: ANSI generation with caching") 
            print("✅ Object Processor: time/date/elapsed handling")
            print("✅ Format Class: compilation and inheritance")
            print("✅ Reconstructor: final string assembly")
            print("✅ Integration: end-to-end functionality")
            print("\n🚀 FDL core system ready for public API!")
            
        else:
            print(f"\n❌ {self.test_count - self.passed_count} tests failed")
            print("Review failed tests before proceeding to public API")
        
        print("=" * 70)


def main():
    """Main test runner."""
    suite = ComprehensiveFDLTestSuite()
    success = suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()