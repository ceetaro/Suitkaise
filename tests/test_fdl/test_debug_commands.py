#!/usr/bin/env python3

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from suitkaise.fdl._int.processors.commands.debug_commands import _DebugCommandProcessor
from suitkaise.fdl._int.core.format_state import _FormatState


def test_debug_command_processor_creation():
    """Test debug command processor can be created."""
    print("🧪 Testing debug command processor creation...")
    
    processor = _DebugCommandProcessor()
    assert processor is not None
    assert hasattr(processor, 'can_process')
    assert hasattr(processor, 'process')
    
    print("✅ Debug command processor creation tests passed")


def test_can_process():
    """Test can_process method for debug commands."""
    print("🧪 Testing can_process method...")
    
    # Test debug command
    assert _DebugCommandProcessor.can_process('debug') == True
    assert _DebugCommandProcessor.can_process('DEBUG') == True  # Case insensitive
    assert _DebugCommandProcessor.can_process(' debug ') == True  # Whitespace
    
    # Test end debug command
    assert _DebugCommandProcessor.can_process('end debug') == True
    assert _DebugCommandProcessor.can_process('END DEBUG') == True
    assert _DebugCommandProcessor.can_process(' end debug ') == True
    
    # Test invalid commands
    assert _DebugCommandProcessor.can_process('debug_mode') == False
    assert _DebugCommandProcessor.can_process('debugger') == False
    assert _DebugCommandProcessor.can_process('end debugging') == False
    assert _DebugCommandProcessor.can_process('start debug') == False
    assert _DebugCommandProcessor.can_process('red') == False
    assert _DebugCommandProcessor.can_process('bold') == False
    
    print("✅ can_process tests passed")


def test_debug_mode_activation():
    """Test debug mode activation."""
    print("🧪 Testing debug mode activation...")
    
    format_state = _FormatState()
    assert format_state.debug_mode == False
    
    # Process debug command
    result = _DebugCommandProcessor.process('debug', format_state)
    
    # Should enable debug mode and reset formatting
    assert result.debug_mode == True
    assert result.text_color is None
    assert result.background_color is None
    assert result.bold == False
    assert result.italic == False
    assert result.underline == False
    assert result.strikethrough == False
    
    print("✅ Debug mode activation tests passed")


def test_debug_mode_deactivation():
    """Test debug mode deactivation."""
    print("🧪 Testing debug mode deactivation...")
    
    format_state = _FormatState(debug_mode=True)
    assert format_state.debug_mode == True
    
    # Process end debug command
    result = _DebugCommandProcessor.process('end debug', format_state)
    
    # Should disable debug mode
    assert result.debug_mode == False
    
    print("✅ Debug mode deactivation tests passed")


def test_debug_with_existing_formatting():
    """Test debug mode with existing formatting."""
    print("🧪 Testing debug mode with existing formatting...")
    
    # Create format state with existing formatting
    format_state = _FormatState(
        text_color='red',
        background_color='blue',
        bold=True,
        italic=True,
        underline=True
    )
    
    # Process debug command
    result = _DebugCommandProcessor.process('debug', format_state)
    
    # Should enable debug mode and reset all formatting
    assert result.debug_mode == True
    assert result.text_color is None
    assert result.background_color is None
    assert result.bold == False
    assert result.italic == False
    assert result.underline == False
    assert result.strikethrough == False
    
    print("✅ Debug with existing formatting tests passed")


def test_case_insensitivity():
    """Test case insensitivity of debug commands."""
    print("🧪 Testing case insensitivity...")
    
    format_state = _FormatState()
    
    # Test various case combinations
    test_cases = [
        'debug',
        'DEBUG',
        'Debug',
        'DeBuG',
        'end debug',
        'END DEBUG',
        'End Debug',
        'eNd DeBuG'
    ]
    
    for command in test_cases:
        assert _DebugCommandProcessor.can_process(command) == True
        
        # Test processing doesn't raise errors
        try:
            result = _DebugCommandProcessor.process(command, format_state)
            assert result is not None
        except Exception as e:
            assert False, f"Command '{command}' should not raise error: {e}"
    
    print("✅ Case insensitivity tests passed")


def test_whitespace_handling():
    """Test whitespace handling in commands."""
    print("🧪 Testing whitespace handling...")
    
    format_state = _FormatState()
    
    # Test commands with various whitespace
    whitespace_commands = [
        ' debug ',
        '  debug  ',
        '\tdebug\t',
        ' end debug ',
        '  end  debug  ',
        '\tend\tdebug\t'
    ]
    
    for command in whitespace_commands:
        assert _DebugCommandProcessor.can_process(command) == True
        
        try:
            result = _DebugCommandProcessor.process(command, format_state)
            assert result is not None
        except Exception as e:
            assert False, f"Command '{command}' should not raise error: {e}"
    
    print("✅ Whitespace handling tests passed")


def test_priority():
    """Test processor priority."""
    print("🧪 Testing processor priority...")
    
    # Debug commands should have high priority (processed early)
    priority = _DebugCommandProcessor.get_priority()
    assert isinstance(priority, int)
    assert 1 <= priority <= 100  # Valid priority range
    
    print(f"Debug command processor priority: {priority}")
    print("✅ Priority tests passed")


def test_edge_cases():
    """Test edge cases and error conditions."""
    print("🧪 Testing edge cases...")
    
    format_state = _FormatState()
    
    # Test empty command
    assert _DebugCommandProcessor.can_process('') == False
    assert _DebugCommandProcessor.can_process('   ') == False
    
    # Test partial matches
    assert _DebugCommandProcessor.can_process('deb') == False
    assert _DebugCommandProcessor.can_process('end deb') == False
    assert _DebugCommandProcessor.can_process('end') == False
    
    # Test commands with extra words
    assert _DebugCommandProcessor.can_process('debug mode') == False
    assert _DebugCommandProcessor.can_process('end debug mode') == False
    
    print("✅ Edge cases tests passed")


def run_tests():
    """Run all debug command processor tests."""
    print("🚀 Starting Debug Commands Processor Tests")
    print("="*50)
    
    try:
        test_debug_command_processor_creation()
        test_can_process()
        test_debug_mode_activation()
        test_debug_mode_deactivation()
        test_debug_with_existing_formatting()
        test_case_insensitivity()
        test_whitespace_handling()
        test_priority()
        test_edge_cases()
        
        print("\n" + "="*50)
        print("✅ ALL DEBUG COMMANDS PROCESSOR TESTS PASSED!")
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