# tests/test_fdl/test_elements.py
"""
Tests for the FDL element processors.

Tests all element types: text, variable, command, and object elements.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from suitkaise.fdl._int.elements.base_element import _ElementProcessor
from suitkaise.fdl._int.elements.text_element import _TextElement
from suitkaise.fdl._int.elements.variable_element import _VariableElement, _is_valid_variable_pattern
from suitkaise.fdl._int.elements.command_element import _CommandElement
from suitkaise.fdl._int.elements.object_element import _ObjectElement, _is_valid_object_pattern
from suitkaise.fdl._int.core.format_state import _FormatState


class TestBaseElement:
    """Test the _ElementProcessor base class."""
    
    def test_element_processor_interface(self):
        """Test that _ElementProcessor defines the correct interface."""
        # Should have abstract methods
        assert hasattr(_ElementProcessor, 'process')
        
        # Should be abstract (can't instantiate directly)
        with pytest.raises(TypeError):
            _ElementProcessor()


class TestTextElement:
    """Test the _TextElement class."""
    
    def test_text_element_creation(self):
        """Test creating a text element."""
        element = _TextElement("Hello World")
        assert element.content == "Hello World"
    
    def test_text_element_process(self):
        """Test processing a text element."""
        element = _TextElement("Hello World")
        format_state = _FormatState()
        
        result = element.process(format_state)
        
        # Should add text to all output streams
        assert "Hello World" in result.terminal_output
        assert "Hello World" in result.plain_output
        assert "Hello World" in result.markdown_output
        assert "Hello World" in result.html_output
    
    def test_text_element_with_unicode(self):
        """Test text element with unicode content."""
        element = _TextElement("Unicode: 🌟 ✨ 中文")
        format_state = _FormatState()
        
        result = element.process(format_state)
        
        assert "🌟" in result.terminal_output[0]
        assert "✨" in result.terminal_output[0]
        assert "中文" in result.terminal_output[0]
    
    def test_text_element_empty_content(self):
        """Test text element with empty content."""
        element = _TextElement("")
        format_state = _FormatState()
        
        result = element.process(format_state)
        
        # Should still add empty string to outputs
        assert "" in result.terminal_output
        assert "" in result.plain_output
    
    def test_text_element_box_mode(self):
        """Test text element when in box mode."""
        element = _TextElement("Box content")
        format_state = _FormatState()
        format_state.in_box = True
        
        result = element.process(format_state)
        
        # Should add to box content instead of output streams
        assert "Box content" in result.box_content
        assert len(result.terminal_output) == 0


class TestVariableElement:
    """Test the _VariableElement class."""
    
    def test_variable_element_creation(self):
        """Test creating a variable element."""
        element = _VariableElement("name")
        assert element.variable_name == "name"
    
    def test_variable_element_process(self):
        """Test processing a variable element."""
        element = _VariableElement("name")
        format_state = _FormatState(values=('Alice', 'Bob'))
        
        result = element.process(format_state)
        
        # Should substitute variable with value
        assert "Alice" in result.terminal_output
        assert "Alice" in result.plain_output
    
    def test_variable_element_no_values(self):
        """Test variable element when no values available."""
        element = _VariableElement("name")
        format_state = _FormatState()
        
        result = element.process(format_state)
        
        # Should handle gracefully
        assert len(result.terminal_output) >= 0  # Should not crash
    
    def test_variable_element_none_value(self):
        """Test variable element with None value."""
        element = _VariableElement("value")
        format_state = _FormatState(values=(None,))
        
        result = element.process(format_state)
        
        assert "None" in result.terminal_output[0]
    
    def test_is_valid_variable_pattern(self):
        """Test variable pattern validation."""
        # Valid patterns
        assert _is_valid_variable_pattern("name") is True
        assert _is_valid_variable_pattern("user_name") is True
        assert _is_valid_variable_pattern("count123") is True
        assert _is_valid_variable_pattern("_private") is True
        
        # Invalid patterns
        assert _is_valid_variable_pattern("123invalid") is False
        assert _is_valid_variable_pattern("has-dash") is False
        assert _is_valid_variable_pattern("has space") is False
        assert _is_valid_variable_pattern("") is False


class TestCommandElement:
    """Test the _CommandElement class."""
    
    def test_command_element_creation(self):
        """Test creating a command element."""
        element = _CommandElement("red")
        assert element.command == "red"
    
    def test_command_element_process(self):
        """Test processing a command element."""
        # This test requires the command registry to be set up
        # We'll test the basic structure
        element = _CommandElement("test_command")
        format_state = _FormatState()
        
        result = element.process(format_state)
        
        # Should return a format state (even if command not found)
        assert isinstance(result, _FormatState)
    
    def test_command_element_empty_command(self):
        """Test command element with empty command."""
        element = _CommandElement("")
        format_state = _FormatState()
        
        result = element.process(format_state)
        
        # Should handle gracefully
        assert isinstance(result, _FormatState)


class TestObjectElement:
    """Test the _ObjectElement class."""
    
    def test_object_element_creation(self):
        """Test creating an object element."""
        element = _ObjectElement("time", "")
        assert element.obj_type == "time"
        assert element.variable == ""
    
    def test_object_element_create_from_content(self):
        """Test creating object element from content string."""
        element = _ObjectElement.create_from_content("time:timestamp")
        assert element.obj_type == "time"
        assert element.variable == "timestamp"
    
    def test_object_element_create_from_content_no_variable(self):
        """Test creating object element without variable."""
        element = _ObjectElement.create_from_content("time:")
        assert element.obj_type == "time"
        assert element.variable == ""
    
    def test_object_element_process(self):
        """Test processing an object element."""
        # This test requires the object registry to be set up
        # We'll test the basic structure
        element = _ObjectElement("test_type", "test_var")
        format_state = _FormatState()
        
        result = element.process(format_state)
        
        # Should return a format state
        assert isinstance(result, _FormatState)
    
    def test_is_valid_object_pattern(self):
        """Test object pattern validation."""
        # Valid patterns
        assert _is_valid_object_pattern("time:") is True
        assert _is_valid_object_pattern("time:timestamp") is True
        assert _is_valid_object_pattern("spinner:dots") is True
        
        # Invalid patterns (no colon)
        assert _is_valid_object_pattern("time") is False
        assert _is_valid_object_pattern("") is False
        
        # Invalid patterns (invalid characters)
        assert _is_valid_object_pattern("time:has space") is False
        assert _is_valid_object_pattern("time:has-dash") is False


class TestElementIntegration:
    """Test integration between different element types."""
    
    def test_mixed_elements_processing(self):
        """Test processing different element types together."""
        format_state = _FormatState(values=('Alice',))
        
        # Process text element
        text_elem = _TextElement("Hello ")
        format_state = text_elem.process(format_state)
        
        # Process variable element
        var_elem = _VariableElement("name")
        format_state = var_elem.process(format_state)
        
        # Process more text
        text_elem2 = _TextElement("!")
        format_state = text_elem2.process(format_state)
        
        # Should have combined output
        terminal_output = ''.join(format_state.terminal_output)
        assert "Hello Alice!" in terminal_output
    
    def test_elements_with_box_mode(self):
        """Test elements when in box mode."""
        format_state = _FormatState(values=('test',))
        format_state.in_box = True
        
        # Process different elements
        text_elem = _TextElement("Text: ")
        format_state = text_elem.process(format_state)
        
        var_elem = _VariableElement("value")
        format_state = var_elem.process(format_state)
        
        # Should accumulate in box content
        box_content = ''.join(format_state.box_content)
        assert "Text: test" in box_content
        
        # Should not add to normal output streams
        assert len(format_state.terminal_output) == 0
    
    def test_elements_with_progress_bar_mode(self):
        """Test elements when progress bar is active."""
        format_state = _FormatState()
        
        # Mock progress bar
        class MockProgressBar:
            def __init__(self):
                self.is_stopped = False
        
        mock_bar = MockProgressBar()
        format_state.start_progress_bar_mode(mock_bar)
        
        # Process element
        text_elem = _TextElement("Progress text")
        format_state = text_elem.process(format_state)
        
        # Should add to queued output instead of normal output
        assert len(format_state.queued_terminal_output) > 0
        assert "Progress text" in format_state.queued_terminal_output[0]


class TestElementEdgeCases:
    """Test edge cases and error handling for elements."""
    
    def test_element_with_special_characters(self):
        """Test elements with special characters."""
        special_text = "Special: <>&\"'\n\t"
        element = _TextElement(special_text)
        format_state = _FormatState()
        
        result = element.process(format_state)
        
        # Should handle special characters (check joined output since text contains newlines)
        terminal_output = ''.join(result.terminal_output)
        assert special_text in terminal_output
    
    def test_variable_element_with_complex_types(self):
        """Test variable element with complex value types."""
        complex_values = ([1, 2, 3], {'key': 'value'}, None, True, 42)
        
        for value in complex_values:
            element = _VariableElement("test")
            format_state = _FormatState(values=(value,))
            
            result = element.process(format_state)
            
            # Should convert to string representation
            assert str(value) in result.terminal_output[0]
    
    def test_elements_with_empty_format_state(self):
        """Test elements with minimal format state."""
        format_state = _FormatState()
        
        # Should handle all element types
        elements = [
            _TextElement("test"),
            _VariableElement("missing"),  # No values available
            _CommandElement("unknown"),   # Unknown command
            _ObjectElement("unknown", "var")  # Unknown object type
        ]
        
        for element in elements:
            # Should not crash
            result = element.process(format_state)
            assert isinstance(result, _FormatState)


if __name__ == '__main__':
    pytest.main([__file__])