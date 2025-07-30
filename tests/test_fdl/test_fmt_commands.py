#!/usr/bin/env python3

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from suitkaise.fdl._int.processors.commands.fmt_commands import _FormatCommandProcessor
from suitkaise.fdl._int.core.format_state import _FormatState
from suitkaise.fdl._int.core.format_registry import _FormatRegistry, register_format


def test_fmt_command_processor_creation():
    """Test fmt command processor can be created."""
    print("🧪 Testing fmt command processor creation...")
    
    processor = _FormatCommandProcessor()
    assert processor is not None
    assert hasattr(processor, 'can_process')
    assert hasattr(processor, 'process')
    
    print("✅ Fmt command processor creation tests passed")


def test_can_process():
    """Test can_process method for fmt commands."""
    print("🧪 Testing can_process method...")
    
    # Test fmt commands
    assert _FormatCommandProcessor.can_process('fmt myformat') == True
    assert _FormatCommandProcessor.can_process('FMT MYFORMAT') == True  # Case insensitive
    assert _FormatCommandProcessor.can_process(' fmt myformat ') == True  # Whitespace
    
    # Test end commands
    assert _FormatCommandProcessor.can_process('end myformat') == True
    assert _FormatCommandProcessor.can_process('END MYFORMAT') == True
    assert _FormatCommandProcessor.can_process(' end myformat ') == True
    
    # Test invalid commands
    assert _FormatCommandProcessor.can_process('fmt') == False  # No format name
    assert _FormatCommandProcessor.can_process('format myformat') == False
    assert _FormatCommandProcessor.can_process('end') == False  # No format name
    assert _FormatCommandProcessor.can_process('red') == False
    assert _FormatCommandProcessor.can_process('bold') == False
    
    print("✅ can_process tests passed")


def test_fmt_command_basic():
    """Test basic fmt command functionality."""
    print("🧪 Testing basic fmt command...")
    
    # Register a test format
    register_format('testformat', '</red, bold>')
    
    format_state = _FormatState()
    
    # Process fmt command
    result = _FormatCommandProcessor.process('fmt testformat', format_state)
    
    # Should apply the registered format
    assert result.text_color == 'red'
    assert result.bold == True
    
    print("✅ Basic fmt command tests passed")


def test_fmt_with_additional_commands():
    """Test fmt command with additional comma-separated commands."""
    print("🧪 Testing fmt with additional commands...")
    
    # Register a test format
    register_format('baseformat', '</blue>')
    
    format_state = _FormatState()
    
    # Process fmt command with additional commands
    result = _FormatCommandProcessor.process('fmt baseformat, italic, underline', format_state)
    
    # Should apply both the format and additional commands
    assert result.text_color == 'blue'  # From format
    assert result.italic == True        # Additional command
    assert result.underline == True     # Additional command
    
    print("✅ Fmt with additional commands tests passed")


def test_nested_fmt_expansion():
    """Test nested fmt command expansion."""
    print("🧪 Testing nested fmt expansion...")
    
    # Register nested formats
    register_format('inner', '</bold>')
    register_format('outer', '</fmt inner, red>')
    
    format_state = _FormatState()
    
    # Process nested fmt command
    result = _FormatCommandProcessor.process('fmt outer', format_state)
    
    # Should expand both levels
    assert result.text_color == 'red'  # From outer format
    assert result.bold == True         # From inner format
    
    print("✅ Nested fmt expansion tests passed")


def test_end_command():
    """Test end command functionality."""
    print("🧪 Testing end command...")
    
    # Register a test format
    register_format('endtest', '</green, italic>')
    
    format_state = _FormatState()
    
    # Apply format
    format_state = _FormatCommandProcessor.process('fmt endtest', format_state)
    assert format_state.text_color == 'green'
    assert format_state.italic == True
    
    # Add additional formatting that should persist
    format_state.bold = True
    
    # End the format
    result = _FormatCommandProcessor.process('end endtest', format_state)
    
    # Format contributions should be removed, but additional formatting should persist
    assert result.text_color is None  # Format contribution removed
    assert result.italic == False     # Format contribution removed
    assert result.bold == True        # Additional formatting persists
    
    print("✅ End command tests passed")


def test_format_contribution_tracking():
    """Test format contribution tracking."""
    print("🧪 Testing format contribution tracking...")
    
    # Register a test format
    register_format('tracktest', '</yellow, bold>')
    
    format_state = _FormatState()
    
    # Apply format
    result = _FormatCommandProcessor.process('fmt tracktest', format_state)
    
    # Should track active formats
    assert 'tracktest' in result.active_formats
    
    # End the format
    result = _FormatCommandProcessor.process('end tracktest', format_state)
    
    # Should remove from active formats
    assert 'tracktest' not in result.active_formats
    
    print("✅ Format contribution tracking tests passed")


def test_nonexistent_format():
    """Test handling of nonexistent format."""
    print("🧪 Testing nonexistent format...")
    
    format_state = _FormatState()
    
    # Try to use a format that doesn't exist
    result = _FormatCommandProcessor.process('fmt nonexistent', format_state)
    
    # Should not change the format state
    assert result.text_color is None
    assert result.bold == False
    assert result.italic == False
    
    print("✅ Nonexistent format tests passed")


def test_case_insensitivity():
    """Test case insensitivity of fmt commands."""
    print("🧪 Testing case insensitivity...")
    
    # Register a test format
    register_format('CaseTest', '</cyan>')
    
    format_state = _FormatState()
    
    # Test various case combinations
    test_cases = [
        'fmt CaseTest',
        'FMT CaseTest',
        'Fmt CaseTest',
        'fmt casetest',
        'fmt CASETEST'
    ]
    
    for command in test_cases:
        assert _FormatCommandProcessor.can_process(command) == True
        
        # Test processing doesn't raise errors
        try:
            result = _FormatCommandProcessor.process(command, format_state)
            assert result is not None
        except Exception as e:
            assert False, f"Command '{command}' should not raise error: {e}"
    
    print("✅ Case insensitivity tests passed")


def test_priority():
    """Test processor priority."""
    print("🧪 Testing processor priority...")
    
    # Format commands should have high priority (processed early)
    priority = _FormatCommandProcessor.get_priority()
    assert isinstance(priority, int)
    assert 1 <= priority <= 100  # Valid priority range
    assert priority == 10  # Should be high priority
    
    print(f"Format command processor priority: {priority}")
    print("✅ Priority tests passed")


def test_whitespace_handling():
    """Test whitespace handling in commands."""
    print("🧪 Testing whitespace handling...")
    
    # Register a test format
    register_format('whitespace', '</magenta>')
    
    format_state = _FormatState()
    
    # Test commands with various whitespace
    whitespace_commands = [
        ' fmt whitespace ',
        '  fmt  whitespace  ',
        '\tfmt\twhitespace\t',
        ' end whitespace ',
        '  end  whitespace  '
    ]
    
    for command in whitespace_commands:
        assert _FormatCommandProcessor.can_process(command) == True
        
        try:
            result = _FormatCommandProcessor.process(command, format_state)
            assert result is not None
        except Exception as e:
            assert False, f"Command '{command}' should not raise error: {e}"
    
    print("✅ Whitespace handling tests passed")


def test_complex_scenario():
    """Test complex scenario with multiple formats and overrides."""
    print("🧪 Testing complex scenario...")
    
    # Register multiple formats
    register_format('base', '</blue, bold>')
    register_format('override', '</red>')
    register_format('complex', '</fmt base, italic>')
    
    format_state = _FormatState()
    
    # Apply base format
    format_state = _FormatCommandProcessor.process('fmt base', format_state)
    assert format_state.text_color == 'blue'
    assert format_state.bold == True
    
    # Apply override format (should override color but keep bold)
    format_state = _FormatCommandProcessor.process('fmt override', format_state)
    assert format_state.text_color == 'red'  # Overridden
    assert format_state.bold == True         # Still from base
    
    # End override (should restore base color)
    format_state = _FormatCommandProcessor.process('end override', format_state)
    assert format_state.text_color == 'blue'  # Restored from base
    assert format_state.bold == True          # Still from base
    
    # Apply complex format
    format_state = _FormatCommandProcessor.process('fmt complex', format_state)
    assert format_state.text_color == 'blue'  # From nested base
    assert format_state.bold == True          # From nested base
    assert format_state.italic == True        # From complex
    
    print("✅ Complex scenario tests passed")


def test_edge_cases():
    """Test edge cases and error conditions."""
    print("🧪 Testing edge cases...")
    
    format_state = _FormatState()
    
    # Test empty command parts
    assert _FormatCommandProcessor.can_process('fmt ') == False
    assert _FormatCommandProcessor.can_process('end ') == False
    assert _FormatCommandProcessor.can_process('fmt') == False
    assert _FormatCommandProcessor.can_process('end') == False
    
    # Test commands with extra spaces
    assert _FormatCommandProcessor.can_process('fmt  test  format') == True
    
    # Test ending non-active format (should be safe)
    try:
        result = _FormatCommandProcessor.process('end nonactive', format_state)
        assert result is not None
    except Exception as e:
        assert False, f"Ending non-active format should not raise error: {e}"
    
    print("✅ Edge cases tests passed")


def run_tests():
    """Run all fmt command processor tests."""
    print("🚀 Starting Fmt Commands Processor Tests")
    print("="*50)
    
    try:
        # Clear any existing formats
        registry = _FormatRegistry()
        registry.clear_formats()
        
        test_fmt_command_processor_creation()
        test_can_process()
        test_fmt_command_basic()
        test_fmt_with_additional_commands()
        test_nested_fmt_expansion()
        test_end_command()
        test_format_contribution_tracking()
        test_nonexistent_format()
        test_case_insensitivity()
        test_priority()
        test_whitespace_handling()
        test_complex_scenario()
        test_edge_cases()
        
        print("\n" + "="*50)
        print("✅ ALL FMT COMMANDS PROCESSOR TESTS PASSED!")
        print("="*50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)