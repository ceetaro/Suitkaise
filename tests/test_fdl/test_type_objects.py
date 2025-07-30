#!/usr/bin/env python3

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from suitkaise.fdl._int.processors.objects.type_objects import _TypeObjectProcessor
from suitkaise.fdl._int.core.format_state import _FormatState


def test_type_object_processor_creation():
    """Test type object processor can be created."""
    print("🧪 Testing type object processor creation...")
    
    processor = _TypeObjectProcessor()
    assert processor is not None
    assert hasattr(processor, 'get_supported_object_types')
    assert hasattr(processor, 'process_object')
    
    print("✅ Type object processor creation tests passed")


def test_supported_object_types():
    """Test supported object types."""
    print("🧪 Testing supported object types...")
    
    supported_types = _TypeObjectProcessor.get_supported_object_types()
    assert isinstance(supported_types, set)
    assert 'type' in supported_types
    
    print("✅ Supported object types tests passed")


def test_basic_types():
    """Test basic type processing."""
    print("🧪 Testing basic types...")
    
    # Test integer
    format_state = _FormatState(values=[42])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'int' in result
    
    # Test string
    format_state = _FormatState(values=["hello"])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'str' in result
    
    # Test float
    format_state = _FormatState(values=[3.14])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'float' in result
    
    # Test boolean
    format_state = _FormatState(values=[True])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'bool' in result
    
    # Test None
    format_state = _FormatState(values=[None])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'NoneType' in result
    
    # Test list
    format_state = _FormatState(values=[[1, 2, 3]])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'list' in result
    
    # Test dict
    format_state = _FormatState(values=[{'key': 'value'}])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'dict' in result
    
    print("✅ Basic types tests passed")


def test_debug_mode():
    """Test type processing in debug mode."""
    print("🧪 Testing debug mode...")
    
    # Test integer in debug mode
    format_state = _FormatState(debug_mode=True, values=[42])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'type[int]' in result
    # Should contain aquamarine color code in debug mode
    assert '\x1b[96m' in result  # Aquamarine ANSI code (96m, not 38;5;79m)
    
    # Test string in debug mode
    format_state = _FormatState(debug_mode=True, values=["hello"])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'type[str]' in result
    assert '\x1b[96m' in result  # Aquamarine ANSI code
    
    print("✅ Debug mode tests passed")


def test_regular_mode():
    """Test type processing in regular mode."""
    print("🧪 Testing regular mode...")
    
    # Test integer in regular mode
    format_state = _FormatState(debug_mode=False, values=[42])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert result == 'int'
    # Should not contain ANSI codes in regular mode
    assert '\x1b[' not in result
    
    # Test string in regular mode
    format_state = _FormatState(debug_mode=False, values=["hello"])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert result == 'str'
    assert '\x1b[' not in result
    
    print("✅ Regular mode tests passed")


def test_complex_types():
    """Test complex and custom types."""
    print("🧪 Testing complex types...")
    
    # Test tuple
    format_state = _FormatState(values=[(1, 2, 3)])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'tuple' in result
    
    # Test set
    format_state = _FormatState(values=[{1, 2, 3}])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'set' in result
    
    # Test custom class
    class CustomClass:
        pass
    
    custom_obj = CustomClass()
    format_state = _FormatState(values=[custom_obj])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'CustomClass' in result
    
    # Test function
    def test_function():
        pass
    
    format_state = _FormatState(values=[test_function])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'function' in result
    
    print("✅ Complex types tests passed")


def test_nested_types():
    """Test nested container types."""
    print("🧪 Testing nested types...")
    
    # Test list of lists
    nested_list = [[1, 2], [3, 4]]
    format_state = _FormatState(values=[nested_list])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'list' in result
    
    # Test dict with mixed values
    nested_dict = {'numbers': [1, 2, 3], 'text': 'hello'}
    format_state = _FormatState(values=[nested_dict])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'dict' in result
    
    print("✅ Nested types tests passed")


def test_builtin_types():
    """Test various builtin types."""
    print("🧪 Testing builtin types...")
    
    # Test range
    format_state = _FormatState(values=[range(10)])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'range' in result
    
    # Test bytes
    format_state = _FormatState(values=[b'hello'])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'bytes' in result
    
    # Test complex number
    format_state = _FormatState(values=[3+4j])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'complex' in result
    
    print("✅ Builtin types tests passed")


def test_invalid_object_type():
    """Test handling of invalid object type."""
    print("🧪 Testing invalid object type...")
    
    format_state = _FormatState(values=[42])
    
    # Test with unsupported object type
    result = _TypeObjectProcessor.process_object('invalid', 'test_var', format_state)
    
    # Should return error message for unknown object type
    assert '[UNKNOWN_OBJECT_TYPE:invalid]' in result
    
    print("✅ Invalid object type tests passed")


def test_none_value():
    """Test handling of None value specifically."""
    print("🧪 Testing None value...")
    
    # Test None in regular mode
    format_state = _FormatState(values=[None])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'NoneType' in result
    
    # Test None in debug mode
    format_state = _FormatState(debug_mode=True, values=[None])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'type[NoneType]' in result
    assert '\x1b[96m' in result  # Aquamarine color
    
    print("✅ None value tests passed")


def test_edge_cases():
    """Test edge cases and special scenarios."""
    print("🧪 Testing edge cases...")
    
    # Test empty containers
    format_state = _FormatState(values=[[]])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'list' in result
    
    format_state = _FormatState(values=[{}])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'dict' in result
    
    format_state = _FormatState(values=[set()])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'set' in result
    
    # Test empty string
    format_state = _FormatState(values=[""])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'str' in result
    
    # Test zero values
    format_state = _FormatState(values=[0])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'int' in result
    
    format_state = _FormatState(values=[0.0])
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    assert 'float' in result
    
    print("✅ Edge cases tests passed")


def test_format_state_preservation():
    """Test that format state is preserved during processing."""
    print("🧪 Testing format state preservation...")
    
    # Create format state with some settings
    format_state = _FormatState(
        text_color='red',
        bold=True,
        debug_mode=False,
        values=[42]
    )
    
    original_color = format_state.text_color
    original_bold = format_state.bold
    original_debug = format_state.debug_mode
    
    # Process type object
    result = _TypeObjectProcessor.process_object('type', 'test_var', format_state)
    
    # Format state should be unchanged
    assert format_state.text_color == original_color
    assert format_state.bold == original_bold
    assert format_state.debug_mode == original_debug
    
    print("✅ Format state preservation tests passed")


def run_tests():
    """Run all type object processor tests."""
    print("🚀 Starting Type Objects Processor Tests")
    print("="*50)
    
    try:
        test_type_object_processor_creation()
        test_supported_object_types()
        test_basic_types()
        test_debug_mode()
        test_regular_mode()
        test_complex_types()
        test_nested_types()
        test_builtin_types()
        test_invalid_object_type()
        test_none_value()
        test_edge_cases()
        test_format_state_preservation()
        
        print("\n" + "="*50)
        print("✅ ALL TYPE OBJECTS PROCESSOR TESTS PASSED!")
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