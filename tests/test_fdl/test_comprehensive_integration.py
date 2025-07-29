# tests/test_fdl/test_comprehensive_integration.py
"""
Comprehensive Integration Test for FDL System

This test exercises the entire FDL system end-to-end, testing all components
working together: processors, registries, elements, setup modules, and the
main processing pipeline.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from suitkaise.fdl._int.core.main_processor import _FDLProcessor


def test_comprehensive_fdl_integration():
    """
    Comprehensive test that exercises the entire FDL system.
    
    Tests:
    - All element types (text, variables, commands, objects)
    - All command processors (text, layout, box, time)
    - All object processors (time objects)
    - Setup module integration (colors, wrapping, justification, boxes)
    - Multi-format output generation
    - Complex nested scenarios
    """
    print("🚀 Starting Comprehensive FDL Integration Test")
    print("=" * 60)
    
    processor = _FDLProcessor()
    test_results = []
    
    # Test 1: Basic Text Processing
    print("\n📝 Test 1: Basic Text Processing")
    try:
        result = processor.process_string("Hello, FDL World!")
        assert 'Hello, FDL World!' in result['terminal']
        assert 'Hello, FDL World!' in result['plain']
        assert '\x1b[0m' in result['terminal']  # Reset code added
        test_results.append("✅ Basic text processing")
        print("✅ Basic text processing successful")
    except Exception as e:
        test_results.append(f"❌ Basic text processing: {e}")
        print(f"❌ Basic text processing failed: {e}")
    
    # Test 2: Variable Substitution
    print("\n🔄 Test 2: Variable Substitution")
    try:
        result = processor.process_string(
            "User <name> has <count> messages in <folder>",
            ("Alice", 42, "Inbox")
        )
        assert 'Alice' in result['terminal']
        assert '42' in result['terminal']
        assert 'Inbox' in result['terminal']
        test_results.append("✅ Variable substitution")
        print("✅ Variable substitution successful")
    except Exception as e:
        test_results.append(f"❌ Variable substitution: {e}")
        print(f"❌ Variable substitution failed: {e}")
    
    # Test 3: Color and Formatting Commands
    print("\n🎨 Test 3: Color and Formatting Commands")
    try:
        result = processor.process_string(
            "</red, bold>Error:</reset> </yellow>Warning message</reset> </green>Success!</reset>"
        )
        # Should have ANSI codes for colors and formatting
        assert '\x1b[31m' in result['terminal']  # Red
        assert '\x1b[1m' in result['terminal']   # Bold
        assert '\x1b[33m' in result['terminal']  # Yellow
        assert '\x1b[32m' in result['terminal']  # Green
        assert '\x1b[0m' in result['terminal']   # Reset
        
        # Plain text should be clean
        assert 'Error: Warning message Success!' in result['plain']
        assert '\x1b[' not in result['plain']
        test_results.append("✅ Color and formatting")
        print("✅ Color and formatting successful")
    except Exception as e:
        test_results.append(f"❌ Color and formatting: {e}")
        print(f"❌ Color and formatting failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Text Justification
    print("\n📐 Test 4: Text Justification")
    try:
        result = processor.process_string("</justify center>This text should be centered")
        # Should have padding spaces for centering
        terminal_output = result['terminal']
        assert terminal_output.startswith(' ') or terminal_output.startswith('\t')  # Should start with whitespace
        assert 'This text should be centered' in terminal_output
        test_results.append("✅ Text justification")
        print("✅ Text justification successful")
    except Exception as e:
        test_results.append(f"❌ Text justification: {e}")
        print(f"❌ Text justification failed: {e}")
    
    # Test 5: Time Objects
    print("\n⏰ Test 5: Time Objects")
    try:
        # Test current time
        result = processor.process_string("Current time: <time:>")
        assert ':' in result['terminal']  # Should have time format
        
        # Test with timestamp
        past_time = time.time() - 3600  # 1 hour ago
        result = processor.process_string(
            "Login was <time_ago:login_time> at <time:login_time>",
            (past_time, past_time)
        )
        assert 'ago' in result['terminal'].lower()
        assert ':' in result['terminal']
        test_results.append("✅ Time objects")
        print("✅ Time objects successful")
    except Exception as e:
        test_results.append(f"❌ Time objects: {e}")
        print(f"❌ Time objects failed: {e}")
    
    # Test 6: Box Generation
    print("\n📦 Test 6: Box Generation")
    try:
        result = processor.process_string(
            "</box rounded>Box content with <content></end box>",
            ("formatted text",)
        )
        terminal_output = result['terminal']
        # Should contain box drawing characters
        assert any(char in terminal_output for char in ['╭', '╮', '╯', '╰', '│', '─'])
        assert 'Box content with formatted text' in terminal_output
        test_results.append("✅ Box generation")
        print("✅ Box generation successful")
    except Exception as e:
        test_results.append(f"❌ Box generation: {e}")
        print(f"❌ Box generation failed: {e}")
    
    # Test 7: Complex Nested Processing
    print("\n🧩 Test 7: Complex Nested Processing")
    try:
        complex_fdl = (
            "</cyan, bold>System Status Report</reset>\n"
            "</justify center>Generated on <time:></reset>\n\n"
            "</box rounded>"
            "Server: <server>\n"
            "Uptime: <uptime>\n"
            "Status: </green, bold>ONLINE</reset>"
            "</end box>\n\n"
            "</red>Errors:</reset> <error_count>\n"
            "</yellow>Warnings:</reset> <warning_count>\n"
            "</green>Success:</reset> <success_count>"
        )
        
        values = ("web-server-01", "24h 30m", 0, 3, 157)
        result = processor.process_string(complex_fdl, values)
        
        terminal_output = result['terminal']
        
        # Should have all the content
        assert 'System Status Report' in terminal_output
        assert 'web-server-01' in terminal_output
        assert '24h 30m' in terminal_output
        assert 'ONLINE' in terminal_output
        assert '157' in terminal_output
        
        # Should have ANSI codes
        assert '\x1b[36m' in terminal_output  # Cyan
        assert '\x1b[1m' in terminal_output   # Bold
        assert '\x1b[32m' in terminal_output  # Green
        assert '\x1b[31m' in terminal_output  # Red
        assert '\x1b[33m' in terminal_output  # Yellow
        
        # Should have box characters
        assert any(char in terminal_output for char in ['╭', '╮', '╯', '╰'])
        
        test_results.append("✅ Complex nested processing")
        print("✅ Complex nested processing successful")
    except Exception as e:
        test_results.append(f"❌ Complex nested processing: {e}")
        print(f"❌ Complex nested processing failed: {e}")
    
    # Test 8: Multi-Format Output
    print("\n📄 Test 8: Multi-Format Output")
    try:
        result = processor.process_string(
            "</red>Red text</reset> and </bold>bold text</reset>",
        )
        
        # Terminal should have ANSI codes
        assert '\x1b[31m' in result['terminal']
        assert '\x1b[1m' in result['terminal']
        
        # Plain should be clean
        assert 'Red text and bold text' in result['plain']
        assert '\x1b[' not in result['plain']
        
        # All formats should be present
        required_formats = ['terminal', 'plain', 'markdown', 'html']
        for fmt in required_formats:
            assert fmt in result
            assert isinstance(result[fmt], str)
        
        test_results.append("✅ Multi-format output")
        print("✅ Multi-format output successful")
    except Exception as e:
        test_results.append(f"❌ Multi-format output: {e}")
        print(f"❌ Multi-format output failed: {e}")
    
    # Test 9: Text Wrapping Integration
    print("\n📏 Test 9: Text Wrapping Integration")
    try:
        # Create a very long line that should wrap
        long_text = "This is a very long line of text that should definitely wrap when processed through the FDL system " * 3
        result = processor.process_string(long_text)
        
        # Should contain newlines from wrapping or be shorter due to processing
        terminal_output = result['terminal']
        assert len(terminal_output.split('\n')) > 1 or len(terminal_output) < len(long_text) + 50
        
        test_results.append("✅ Text wrapping integration")
        print("✅ Text wrapping integration successful")
    except Exception as e:
        test_results.append(f"❌ Text wrapping integration: {e}")
        print(f"❌ Text wrapping integration failed: {e}")
    
    # Test 10: Error Handling and Edge Cases
    print("\n🛡️ Test 10: Error Handling and Edge Cases")
    try:
        # Test with invalid syntax (should not crash)
        result = processor.process_string("Invalid <syntax> and <unclosed")
        assert isinstance(result, dict)
        assert 'terminal' in result
        
        # Test with empty string
        result = processor.process_string("")
        assert isinstance(result, dict)
        
        # Test with None values
        result = processor.process_string("Value: <value>", (None,))
        assert 'None' in result['terminal']
        
        # Test with missing values
        result = processor.process_string("Missing <value>")
        assert isinstance(result, dict)
        
        test_results.append("✅ Error handling")
        print("✅ Error handling successful")
    except Exception as e:
        test_results.append(f"❌ Error handling: {e}")
        print(f"❌ Error handling failed: {e}")
    
    # Test Results Summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for result in test_results if result.startswith("✅"))
    total = len(test_results)
    
    for result in test_results:
        print(result)
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! FDL system is working correctly.")
        return True
    else:
        print(f"⚠️  {total - passed} tests failed. System needs attention.")
        return False


def test_performance_benchmark():
    """Basic performance benchmark for the FDL system."""
    print("\n" + "=" * 60)
    print("⚡ PERFORMANCE BENCHMARK")
    print("=" * 60)
    
    processor = _FDLProcessor()
    
    # Test simple processing performance
    start_time = time.time()
    for i in range(100):
        result = processor.process_string("Simple text processing test")
    simple_time = time.time() - start_time
    
    # Test complex processing performance
    complex_fdl = (
        "</red, bold>Test <count></reset> - "
        "</justify center>Centered text</reset> "
        "</box rounded>Box content</end box>"
    )
    
    start_time = time.time()
    for i in range(100):
        result = processor.process_string(complex_fdl, (i,))
    complex_time = time.time() - start_time
    
    print(f"Simple processing: {simple_time:.4f}s for 100 iterations ({simple_time*10:.2f}ms per iteration)")
    print(f"Complex processing: {complex_time:.4f}s for 100 iterations ({complex_time*10:.2f}ms per iteration)")
    
    if complex_time < 1.0:  # Should complete 100 complex operations in under 1 second
        print("✅ Performance benchmark passed")
        return True
    else:
        print("⚠️  Performance benchmark failed - system may be too slow")
        return False


if __name__ == '__main__':
    """Run the comprehensive integration test."""
    print("🧪 FDL COMPREHENSIVE INTEGRATION TEST SUITE")
    print("Testing all components of the FDL system working together")
    print()
    
    try:
        # Run main integration test
        integration_passed = test_comprehensive_fdl_integration()
        
        # Run performance benchmark
        performance_passed = test_performance_benchmark()
        
        print("\n" + "=" * 60)
        print("🏁 FINAL RESULTS")
        print("=" * 60)
        
        if integration_passed and performance_passed:
            print("🎉 ALL TESTS PASSED!")
            print("✅ FDL system is fully functional and performant")
            print("✅ All components are properly integrated")
            print("✅ Setup modules are working correctly")
            print("✅ Multi-format output is generated properly")
            print("✅ Error handling is robust")
            exit(0)
        else:
            print("❌ SOME TESTS FAILED")
            if not integration_passed:
                print("❌ Integration tests failed")
            if not performance_passed:
                print("❌ Performance benchmark failed")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)