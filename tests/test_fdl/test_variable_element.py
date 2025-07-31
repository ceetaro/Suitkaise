"""
Comprehensive tests for FDL Variable Element Processor.

Tests the variable element processor that handles variable substitution patterns
like <variable_name> with values from tuples, including debug mode and visual demonstrations.
"""

import pytest
import sys
import os
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.elements.variable_element import (
    _VariableElement, _is_valid_variable_pattern, _create_variable_element
)
from suitkaise.fdl._int.core.format_state import _FormatState, _create_format_state


class TestVariableElement:
    """Test suite for the variable element processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.format_state = _create_format_state()
    
    def test_variable_element_initialization(self):
        """Test variable element initialization with various variable names."""
        # Valid variable names
        valid_names = [
            "variable",
            "var_name",
            "_private_var",
            "var123",
            "CamelCase",
            "snake_case_var",
            "_",
            "x",
            "a1b2c3"
        ]
        
        for name in valid_names:
            element = _VariableElement(name)
            assert element.variable_name == name
    
    def test_invalid_variable_names(self):
        """Test that invalid variable names raise ValueError."""
        invalid_names = [
            "",           # Empty
            "123var",     # Starts with number
            "var-name",   # Contains dash
            "var name",   # Contains space
            "var.name",   # Contains dot
            "var@name",   # Contains special char
            "var+name",   # Contains plus
            "var(name)",  # Contains parentheses
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError):
                _VariableElement(name)
    
    def test_process_with_values_available(self):
        """Test processing variable when values are available."""
        element = _VariableElement("test_var")
        
        # Set up format state with values
        self.format_state.values = ("Hello", "World", 123)
        self.format_state.value_index = 0
        
        result_state = element.process(self.format_state)
        
        # Should consume first value
        assert result_state.value_index == 1
        
        # Should add value to outputs
        outputs = result_state.get_final_outputs()
        assert "Hello" in outputs['terminal']
        assert "Hello" in outputs['plain']
    
    def test_process_with_no_values_available(self):
        """Test processing variable when no values are available."""
        element = _VariableElement("missing_var")
        
        # No values in format state
        self.format_state.values = ()
        self.format_state.value_index = 0
        
        result_state = element.process(self.format_state)
        
        # Should add error placeholder
        outputs = result_state.get_final_outputs()
        assert "[MISSING_VALUE_missing_var]" in outputs['terminal']
        assert "[MISSING_VALUE_missing_var]" in outputs['plain']
    
    def test_process_with_values_exhausted(self):
        """Test processing variable when all values are already consumed."""
        element = _VariableElement("exhausted_var")
        
        # Values exist but index is beyond available values
        self.format_state.values = ("value1", "value2")
        self.format_state.value_index = 2  # Beyond available values
        
        result_state = element.process(self.format_state)
        
        # Should add error placeholder
        outputs = result_state.get_final_outputs()
        assert "[MISSING_VALUE_exhausted_var]" in outputs['terminal']
    
    def test_process_in_box_mode(self):
        """Test processing variable when inside a box."""
        element = _VariableElement("box_var")
        
        # Set up box mode
        self.format_state.in_box = True
        self.format_state.values = ("Box Content",)
        self.format_state.value_index = 0
        
        result_state = element.process(self.format_state)
        
        # Should add to box_content instead of output streams
        assert "Box Content" in result_state.box_content
        
        # Should not be in main output streams
        outputs = result_state.get_final_outputs()
        assert "Box Content" not in outputs['terminal']
    
    def test_debug_mode_formatting(self):
        """Test variable processing in debug mode."""
        element = _VariableElement("debug_var")
        
        # Enable debug mode
        self.format_state.debug_mode = True
        self.format_state.values = (42, True, False, None, "string", 3.14)
        self.format_state.value_index = 0
        
        # Test different value types
        test_cases = [
            (42, "int"),
            (True, "bool"),
            (False, "bool"),
            (None, "NoneType"),
            ("string", "str"),
            (3.14, "float"),
        ]
        
        for expected_value, expected_type in test_cases:
            format_state = _create_format_state()
            format_state.debug_mode = True
            format_state.values = (expected_value,)
            format_state.value_index = 0
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            terminal_output = outputs['terminal']
            
            # Should contain the value and type annotation
            assert str(expected_value) in terminal_output
            assert f"({expected_type})" in terminal_output
            
            # Should contain ANSI codes for formatting
            assert '\033[' in terminal_output  # Some ANSI code present
    
    def test_debug_mode_string_handling(self):
        """Test debug mode string handling with quotes."""
        element = _VariableElement("string_var")
        
        self.format_state.debug_mode = True
        self.format_state.values = ("test string",)
        self.format_state.value_index = 0
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        terminal_output = outputs['terminal']
        
        # Should contain quotes around string
        assert '"test string"' in terminal_output
        # Should contain type annotation
        assert "(str)" in terminal_output
    
    def test_debug_mode_boolean_colors(self):
        """Test debug mode boolean color coding."""
        element = _VariableElement("bool_var")
        
        # Test True (should be green)
        format_state = _create_format_state()
        format_state.debug_mode = True
        format_state.values = (True,)
        format_state.value_index = 0
        
        result_state = element.process(format_state)
        outputs = result_state.get_final_outputs()
        terminal_output = outputs['terminal']
        
        assert "True" in terminal_output
        assert '\033[32m' in terminal_output  # Green color code
        
        # Test False (should be red)
        format_state = _create_format_state()
        format_state.debug_mode = True
        format_state.values = (False,)
        format_state.value_index = 0
        
        result_state = element.process(format_state)
        outputs = result_state.get_final_outputs()
        terminal_output = outputs['terminal']
        
        assert "False" in terminal_output
        assert '\033[31m' in terminal_output  # Red color code
    
    def test_regular_mode_string_processing(self):
        """Test regular mode string processing with FDL commands."""
        element = _VariableElement("fdl_string_var")
        
        # String with FDL formatting commands
        fdl_string = "</bold>Bold text</end bold>"
        self.format_state.values = (fdl_string,)
        self.format_state.value_index = 0
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        terminal_output = outputs['terminal']
        
        # Should process the FDL commands (though exact behavior depends on processor)
        # At minimum, should contain the text content
        assert "Bold text" in terminal_output
    
    def test_regular_mode_non_string_values(self):
        """Test regular mode with non-string values."""
        element = _VariableElement("number_var")
        
        test_values = [42, 3.14, True, False, None, [1, 2, 3], {"key": "value"}]
        
        for test_value in test_values:
            format_state = _create_format_state()
            format_state.values = (test_value,)
            format_state.value_index = 0
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            # Should convert to string representation
            assert str(test_value) in outputs['plain']
    
    def test_variable_name_validation_function(self):
        """Test the standalone variable name validation function."""
        # Valid names
        valid_names = ["var", "var_name", "_private", "x123", "CamelCase"]
        for name in valid_names:
            assert _is_valid_variable_pattern(name)
        
        # Invalid names
        invalid_names = ["", "123var", "var-name", "var name", "var.name"]
        for name in invalid_names:
            assert not _is_valid_variable_pattern(name)
    
    def test_create_variable_element_factory(self):
        """Test the factory function for creating variable elements."""
        # Valid creation
        element = _create_variable_element("valid_var")
        assert isinstance(element, _VariableElement)
        assert element.variable_name == "valid_var"
        
        # Invalid creation should raise ValueError
        with pytest.raises(ValueError):
            _create_variable_element("123invalid")
    
    def test_get_variable_info(self):
        """Test getting variable information."""
        element = _VariableElement("info_var")
        info = element.get_variable_info()
        
        assert info['variable_name'] == "info_var"
        assert info['is_valid'] is True
        assert info['element_type'] == 'variable'
    
    def test_unicode_variable_values(self):
        """Test variable substitution with Unicode values."""
        element = _VariableElement("unicode_var")
        
        unicode_values = [
            "こんにちは",  # Japanese
            "🌍🎉",        # Emojis
            "←→↑↓",        # Arrows
            "café",        # Accented characters
        ]
        
        for unicode_value in unicode_values:
            format_state = _create_format_state()
            format_state.values = (unicode_value,)
            format_state.value_index = 0
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            # Unicode should be preserved
            assert unicode_value in outputs['plain']
            assert unicode_value in outputs['terminal']
    
    def test_complex_data_structures(self):
        """Test variable substitution with complex data structures."""
        element = _VariableElement("complex_var")
        
        complex_values = [
            [1, 2, 3, 4],
            {"key": "value", "nested": {"inner": "data"}},
            (1, "tuple", True),
            {1, 2, 3, 4, 5},  # Set
        ]
        
        for complex_value in complex_values:
            format_state = _create_format_state()
            format_state.values = (complex_value,)
            format_state.value_index = 0
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            # Should convert to string representation
            str_repr = str(complex_value)
            assert str_repr in outputs['plain']
    
    def test_multiple_variable_processing(self):
        """Test processing multiple variables in sequence."""
        variables = ["var1", "var2", "var3"]
        values = ("first", "second", "third")
        
        format_state = _create_format_state()
        format_state.values = values
        format_state.value_index = 0
        
        for var_name in variables:
            element = _VariableElement(var_name)
            format_state = element.process(format_state)
        
        outputs = format_state.get_final_outputs()
        
        # All values should be in output
        for value in values:
            assert value in outputs['terminal']
            assert value in outputs['plain']
        
        # All values should be consumed
        assert format_state.value_index == len(values)
    
    def test_error_handling_edge_cases(self):
        """Test error handling for edge cases."""
        # Variable with whitespace (should be stripped)
        element = _VariableElement("  spaced_var  ")
        assert element.variable_name == "spaced_var"
        
        # Empty variable name after stripping
        with pytest.raises(ValueError):
            _VariableElement("   ")


class TestVariableElementVisualDemonstration:
    """Visual demonstration tests for variable element processor."""
    
    def test_visual_basic_substitution_demonstration(self):
        """Visual demonstration of basic variable substitution."""
        print("\n" + "="*60)
        print("VARIABLE ELEMENT - BASIC SUBSTITUTION DEMONSTRATION")
        print("="*60)
        
        test_cases = [
            ("name", "Alice"),
            ("age", 25),
            ("score", 98.5),
            ("active", True),
            ("inactive", False),
            ("empty", None),
            ("unicode", "こんにちは 🌍"),
        ]
        
        for var_name, value in test_cases:
            print(f"\nVariable: {var_name} = {value} ({type(value).__name__})")
            
            element = _VariableElement(var_name)
            format_state = _create_format_state()
            format_state.values = (value,)
            format_state.value_index = 0
            format_state.text_color = "cyan"
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            print(f"Output: ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
    
    def test_visual_debug_mode_demonstration(self):
        """Visual demonstration of debug mode formatting."""
        print("\n" + "="*60)
        print("VARIABLE ELEMENT - DEBUG MODE DEMONSTRATION")
        print("="*60)
        
        test_values = [
            ("integer", 42),
            ("float", 3.14159),
            ("string", "Hello World"),
            ("boolean_true", True),
            ("boolean_false", False),
            ("none_value", None),
            ("list", [1, 2, 3]),
            ("dict", {"key": "value"}),
            ("unicode", "こんにちは 🎉"),
        ]
        
        for var_name, value in test_values:
            print(f"\nDebug mode - {var_name}:")
            
            element = _VariableElement(var_name)
            format_state = _create_format_state()
            format_state.debug_mode = True
            format_state.values = (value,)
            format_state.value_index = 0
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            print(f"  ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
    
    def test_visual_error_handling_demonstration(self):
        """Visual demonstration of error handling."""
        print("\n" + "="*60)
        print("VARIABLE ELEMENT - ERROR HANDLING DEMONSTRATION")
        print("="*60)
        
        error_cases = [
            ("missing_value", (), 0, "No values provided"),
            ("exhausted_values", ("value1",), 1, "All values consumed"),
            ("out_of_range", ("a", "b"), 3, "Index out of range"),
        ]
        
        for var_name, values, index, description in error_cases:
            print(f"\n{description}:")
            print(f"  Variable: {var_name}")
            print(f"  Values: {values}")
            print(f"  Index: {index}")
            
            element = _VariableElement(var_name)
            format_state = _create_format_state()
            format_state.values = values
            format_state.value_index = index
            format_state.text_color = "red"
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            print(f"  Result: ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
    
    def test_visual_box_mode_demonstration(self):
        """Visual demonstration of variable processing in box mode."""
        print("\n" + "="*60)
        print("VARIABLE ELEMENT - BOX MODE DEMONSTRATION")
        print("="*60)
        
        variables = ["user", "status", "score"]
        values = ("Alice", "Active", 95)
        
        print("\nNormal mode:")
        format_state = _create_format_state()
        format_state.values = values
        format_state.value_index = 0
        format_state.text_color = "green"
        
        for var_name in variables:
            element = _VariableElement(var_name)
            format_state = element.process(format_state)
        
        outputs = format_state.get_final_outputs()
        print(f"  Output: ", end="")
        print(outputs['terminal'], end="")
        print("\033[0m")
        
        print("\nBox mode:")
        format_state = _create_format_state()
        format_state.in_box = True
        format_state.values = values
        format_state.value_index = 0
        format_state.text_color = "yellow"
        
        for var_name in variables:
            element = _VariableElement(var_name)
            format_state = element.process(format_state)
        
        print("  Box content accumulated:")
        for i, content in enumerate(format_state.box_content, 1):
            print(f"    {i}. '{content}'")
    
    def test_visual_unicode_width_demonstration(self):
        """Visual demonstration of Unicode character width handling."""
        print("\n" + "="*60)
        print("VARIABLE ELEMENT - UNICODE WIDTH DEMONSTRATION")
        print("="*60)
        
        unicode_test_cases = [
            ("ascii", "Hello"),
            ("japanese", "こんにちは"),
            ("chinese", "你好世界"),
            ("emojis", "🌍🎉🔥"),
            ("mixed", "Hello 世界 🌍"),
            ("symbols", "←→↑↓⚡"),
            ("math", "∑∆∞≈≠"),
        ]
        
        for var_name, value in unicode_test_cases:
            element = _VariableElement(var_name)
            format_state = _create_format_state()
            format_state.values = (value,)
            format_state.value_index = 0
            format_state.text_color = "magenta"
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            # Calculate visual width
            visual_width = wcswidth(value) or len(value)
            
            print(f"Width: {visual_width:2d} | {var_name:10} = ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
    
    def test_visual_multiple_variables_demonstration(self):
        """Visual demonstration of multiple variable processing."""
        print("\n" + "="*60)
        print("VARIABLE ELEMENT - MULTIPLE VARIABLES DEMONSTRATION")
        print("="*60)
        
        variables = ["name", "age", "city", "active", "score"]
        values = ("Alice", 28, "Tokyo", True, 95.5)
        
        print(f"Variables: {variables}")
        print(f"Values: {values}")
        print("\nProcessing sequence:")
        
        format_state = _create_format_state()
        format_state.values = values
        format_state.value_index = 0
        
        for i, var_name in enumerate(variables):
            print(f"\nStep {i+1}: Processing variable '{var_name}'")
            print(f"  Current index: {format_state.value_index}")
            print(f"  Available values: {format_state.values[format_state.value_index:]}")
            
            element = _VariableElement(var_name)
            format_state.text_color = ["red", "green", "blue", "yellow", "cyan"][i]
            
            format_state = element.process(format_state)
            
            print(f"  Result: ", end="")
            # Get just the latest addition to output
            outputs = format_state.get_final_outputs()
            print(outputs['terminal'], end="")
            print("\033[0m")
            print(f"  New index: {format_state.value_index}")
    
    def test_visual_validation_demonstration(self):
        """Visual demonstration of variable name validation."""
        print("\n" + "="*60)
        print("VARIABLE ELEMENT - VALIDATION DEMONSTRATION")
        print("="*60)
        
        test_names = [
            ("valid_var", True),
            ("_private", True),
            ("CamelCase", True),
            ("var123", True),
            ("123invalid", False),
            ("var-name", False),
            ("var name", False),
            ("var.name", False),
            ("", False),
        ]
        
        for name, should_be_valid in test_names:
            is_valid = _is_valid_variable_pattern(name)
            status = "✅ VALID" if is_valid else "❌ INVALID"
            expected = "✅" if should_be_valid else "❌"
            
            print(f"{name:15} -> {status:10} (Expected: {expected})")
            
            if is_valid == should_be_valid:
                print("  \033[32m✓ Correct validation\033[0m")
            else:
                print("  \033[31m✗ Validation mismatch\033[0m")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestVariableElementVisualDemonstration()
    demo.test_visual_basic_substitution_demonstration()
    demo.test_visual_debug_mode_demonstration()
    demo.test_visual_error_handling_demonstration()
    demo.test_visual_box_mode_demonstration()
    demo.test_visual_unicode_width_demonstration()
    demo.test_visual_multiple_variables_demonstration()
    demo.test_visual_validation_demonstration()
    
    print("\n" + "="*60)
    print("✅ VARIABLE ELEMENT PROCESSOR TESTS COMPLETE")
    print("="*60)