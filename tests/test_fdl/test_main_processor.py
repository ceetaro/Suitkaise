"""
Comprehensive tests for FDL Main Processor System.

Tests the internal main processor that orchestrates FDL string parsing,
element processing, progress bar integration, and final formatting.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.core.main_processor import _FDLProcessor
from suitkaise.fdl._int.core.format_state import _FormatState
from suitkaise.fdl._int.elements.text_element import _TextElement
from suitkaise.fdl._int.elements.variable_element import _VariableElement
from suitkaise.fdl._int.elements.command_element import _CommandElement
from suitkaise.fdl._int.elements.object_element import _ObjectElement


class TestFDLProcessor:
    """Test suite for the main FDL processor system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = _FDLProcessor()
    
    def test_fdl_processor_initialization(self):
        """Test FDL processor initialization."""
        processor = _FDLProcessor()
        
        # Should have compiled regex pattern
        assert hasattr(processor, '_all_brackets_pattern')
        assert processor._all_brackets_pattern is not None
        
        # Regex should match bracket patterns
        test_string = "Hello <world> and <test>"
        matches = list(processor._all_brackets_pattern.finditer(test_string))
        assert len(matches) == 2
        assert matches[0].group(0) == "<world>"
        assert matches[1].group(0) == "<test>"
    
    def test_process_string_simple_text(self):
        """Test processing simple text without any FDL elements."""
        simple_text = "Hello, World!"
        
        with patch('suitkaise.fdl._int.core.main_processor._create_format_state') as mock_create_state:
            mock_state = Mock()
            mock_state.get_final_outputs.return_value = {
                'terminal': simple_text,
                'plain': simple_text,
                'markdown': simple_text,
                'html': simple_text
            }
            mock_create_state.return_value = mock_state
            
            with patch.object(self.processor, '_integrate_progress_bar_state'), \
                 patch.object(self.processor, '_apply_final_formatting'):
                
                result = self.processor.process_string(simple_text)
                
                assert result['terminal'] == simple_text
                assert result['plain'] == simple_text
                assert result['markdown'] == simple_text
                assert result['html'] == simple_text
    
    def test_process_string_with_values(self):
        """Test processing string with variable values."""
        fdl_string = "Hello <name>!"
        values = ("World",)
        
        with patch('suitkaise.fdl._int.core.main_processor._create_format_state') as mock_create_state:
            mock_state = Mock()
            mock_state.get_final_outputs.return_value = {
                'terminal': "Hello World!",
                'plain': "Hello World!",
                'markdown': "Hello World!",
                'html': "Hello World!"
            }
            mock_create_state.return_value = mock_state
            
            with patch.object(self.processor, '_integrate_progress_bar_state'), \
                 patch.object(self.processor, '_apply_final_formatting'):
                
                result = self.processor.process_string(fdl_string, values)
                
                # Verify _create_format_state was called with values
                mock_create_state.assert_called_once_with(values)
                
                assert result['terminal'] == "Hello World!"
    
    def test_process_string_progress_bar_integration(self):
        """Test processing string with progress bar integration."""
        fdl_string = "Processing..."
        
        with patch('suitkaise.fdl._int.core.main_processor._create_format_state') as mock_create_state:
            mock_state = Mock()
            mock_state.get_final_outputs.return_value = {'terminal': 'test'}
            mock_create_state.return_value = mock_state
            
            with patch.object(self.processor, '_integrate_progress_bar_state') as mock_integrate, \
                 patch.object(self.processor, '_apply_final_formatting'):
                
                # Test with progress bar check enabled
                self.processor.process_string(fdl_string, check_progress_bar=True)
                mock_integrate.assert_called_once_with(mock_state)
                
                # Test with progress bar check disabled
                mock_integrate.reset_mock()
                self.processor.process_string(fdl_string, check_progress_bar=False)
                mock_integrate.assert_not_called()
    
    def test_integrate_progress_bar_state_with_active_bar(self):
        """Test progress bar state integration with active bar."""
        format_state = Mock()
        mock_active_bar = Mock()
        mock_active_bar.is_stopped = False
        
        mock_manager = Mock()
        mock_manager.get_active_bar.return_value = mock_active_bar
        
        with patch('suitkaise.fdl._int.core.main_processor._ProgressBarManager', mock_manager):
            self.processor._integrate_progress_bar_state(format_state)
            
            # Should start progress bar mode
            format_state.start_progress_bar_mode.assert_called_once_with(mock_active_bar)
    
    def test_integrate_progress_bar_state_with_stopped_bar(self):
        """Test progress bar state integration with stopped bar."""
        format_state = Mock()
        mock_active_bar = Mock()
        mock_active_bar.is_stopped = True
        
        mock_manager = Mock()
        mock_manager.get_active_bar.return_value = mock_active_bar
        
        with patch('suitkaise.fdl._int.core.main_processor._ProgressBarManager', mock_manager):
            self.processor._integrate_progress_bar_state(format_state)
            
            # Should not start progress bar mode for stopped bar
            format_state.start_progress_bar_mode.assert_not_called()
    
    def test_integrate_progress_bar_state_no_active_bar(self):
        """Test progress bar state integration with no active bar."""
        format_state = Mock()
        
        mock_manager = Mock()
        mock_manager.get_active_bar.return_value = None
        
        with patch('suitkaise.fdl._int.core.main_processor._ProgressBarManager', mock_manager):
            self.processor._integrate_progress_bar_state(format_state)
            
            # Should not start progress bar mode
            format_state.start_progress_bar_mode.assert_not_called()
    
    def test_integrate_progress_bar_state_import_error(self):
        """Test progress bar state integration with import error."""
        format_state = Mock()
        
        with patch('suitkaise.fdl._int.core.main_processor._ProgressBarManager', side_effect=ImportError("Module not found")):
            # Should not raise exception
            self.processor._integrate_progress_bar_state(format_state)
            
            # Should not start progress bar mode
            format_state.start_progress_bar_mode.assert_not_called()
    
    def test_parse_sequential_simple_text(self):
        """Test parsing sequential elements from simple text."""
        fdl_string = "Hello World"
        
        elements = self.processor._parse_sequential(fdl_string)
        
        assert len(elements) == 1
        assert isinstance(elements[0], _TextElement)
        assert elements[0].content == "Hello World"
    
    def test_parse_sequential_text_with_brackets(self):
        """Test parsing sequential elements with brackets."""
        fdl_string = "Hello <name> and <age>"
        
        with patch.object(self.processor, '_parse_bracket_element') as mock_parse:
            mock_parse.side_effect = [
                _VariableElement("name"),
                _VariableElement("age")
            ]
            
            elements = self.processor._parse_sequential(fdl_string)
            
            assert len(elements) == 4
            assert isinstance(elements[0], _TextElement)
            assert elements[0].content == "Hello "
            assert isinstance(elements[1], _VariableElement)
            assert isinstance(elements[2], _TextElement)
            assert elements[2].content == " and "
            assert isinstance(elements[3], _VariableElement)
    
    def test_parse_sequential_only_brackets(self):
        """Test parsing sequential elements with only brackets."""
        fdl_string = "<first><second><third>"
        
        with patch.object(self.processor, '_parse_bracket_element') as mock_parse:
            mock_parse.side_effect = [
                _VariableElement("first"),
                _VariableElement("second"),
                _VariableElement("third")
            ]
            
            elements = self.processor._parse_sequential(fdl_string)
            
            assert len(elements) == 3
            assert all(isinstance(elem, _VariableElement) for elem in elements)
    
    def test_parse_sequential_empty_brackets(self):
        """Test parsing sequential elements with empty brackets."""
        fdl_string = "Hello <> World"
        
        with patch.object(self.processor, '_parse_bracket_element') as mock_parse:
            mock_parse.return_value = None  # Empty bracket returns None
            
            elements = self.processor._parse_sequential(fdl_string)
            
            assert len(elements) == 2
            assert isinstance(elements[0], _TextElement)
            assert elements[0].content == "Hello "
            assert isinstance(elements[1], _TextElement)
            assert elements[1].content == " World"
    
    def test_parse_sequential_nested_brackets(self):
        """Test parsing sequential elements with nested-looking brackets."""
        fdl_string = "Hello <name<inner>> World"
        
        # The regex should match the first complete bracket
        elements = self.processor._parse_sequential(fdl_string)
        
        # Should parse as: "Hello ", "<name<inner>", "> World"
        assert len(elements) >= 2
        assert isinstance(elements[0], _TextElement)
        assert elements[0].content == "Hello "
    
    def test_parse_bracket_element_command(self):
        """Test parsing bracket element for commands."""
        bracket_content = "</bold>"
        
        element = self.processor._parse_bracket_element(bracket_content)
        
        assert isinstance(element, _CommandElement)
    
    def test_parse_bracket_element_object(self):
        """Test parsing bracket element for objects."""
        bracket_content = "<time:now>"
        
        with patch('suitkaise.fdl._int.core.main_processor._is_valid_object_pattern', return_value=True):
            with patch.object(_ObjectElement, 'create_from_content') as mock_create:
                mock_create.return_value = Mock(spec=_ObjectElement)
                
                element = self.processor._parse_bracket_element(bracket_content)
                
                mock_create.assert_called_once_with("time:now")
                assert element is not None
    
    def test_parse_bracket_element_variable(self):
        """Test parsing bracket element for variables."""
        bracket_content = "<variable_name>"
        
        with patch('suitkaise.fdl._int.core.main_processor._is_valid_object_pattern', return_value=False), \
             patch('suitkaise.fdl._int.core.main_processor._is_valid_variable_pattern', return_value=True):
            
            element = self.processor._parse_bracket_element(bracket_content)
            
            assert isinstance(element, _VariableElement)
            assert element.variable_name == "variable_name"
    
    def test_parse_bracket_element_invalid_as_text(self):
        """Test parsing invalid bracket element as text."""
        bracket_content = "<invalid-pattern!>"
        
        with patch('suitkaise.fdl._int.core.main_processor._is_valid_object_pattern', return_value=False), \
             patch('suitkaise.fdl._int.core.main_processor._is_valid_variable_pattern', return_value=False):
            
            element = self.processor._parse_bracket_element(bracket_content)
            
            assert isinstance(element, _TextElement)
            assert element.content == "<invalid-pattern!>"
    
    def test_parse_bracket_element_empty(self):
        """Test parsing empty bracket element."""
        bracket_content = "<>"
        
        element = self.processor._parse_bracket_element(bracket_content)
        
        assert element is None
    
    def test_parse_bracket_element_exception_handling(self):
        """Test parsing bracket element with exception handling."""
        bracket_content = "<test>"
        
        with patch('suitkaise.fdl._int.core.main_processor._is_valid_object_pattern', side_effect=Exception("Test error")):
            
            element = self.processor._parse_bracket_element(bracket_content)
            
            # Should fallback to text element
            assert isinstance(element, _TextElement)
            assert element.content == "<test>"
    
    def test_apply_final_formatting_with_output(self):
        """Test applying final formatting with output content."""
        format_state = Mock()
        format_state.terminal_output = ["content"]
        format_state.queued_terminal_output = []
        format_state.bar_active = False
        
        with patch.object(self.processor, '_apply_wrapping_and_justification') as mock_wrap:
            self.processor._apply_final_formatting(format_state)
            
            mock_wrap.assert_called_once_with(format_state)
            
            # Should add reset code to terminal output
            format_state.terminal_output.append.assert_called_once_with('\033[0m')
    
    def test_apply_final_formatting_with_queued_output(self):
        """Test applying final formatting with queued output."""
        format_state = Mock()
        format_state.terminal_output = []
        format_state.queued_terminal_output = ["queued_content"]
        format_state.bar_active = True
        
        with patch.object(self.processor, '_apply_wrapping_and_justification') as mock_wrap:
            self.processor._apply_final_formatting(format_state)
            
            mock_wrap.assert_called_once_with(format_state)
            
            # Should add reset code to queued terminal output
            format_state.queued_terminal_output.append.assert_called_once_with('\033[0m')
    
    def test_apply_final_formatting_no_output(self):
        """Test applying final formatting with no output."""
        format_state = Mock()
        format_state.terminal_output = []
        format_state.queued_terminal_output = []
        format_state.bar_active = False
        
        with patch.object(self.processor, '_apply_wrapping_and_justification') as mock_wrap:
            self.processor._apply_final_formatting(format_state)
            
            mock_wrap.assert_called_once_with(format_state)
            
            # Should not add reset codes
            format_state.terminal_output.append.assert_not_called()
            format_state.queued_terminal_output.append.assert_not_called()
    
    def test_apply_wrapping_and_justification_complete(self):
        """Test applying wrapping and justification to all streams."""
        format_state = Mock()
        format_state.terminal_width = 80
        format_state.justify = 'center'
        format_state.terminal_output = ["long content that needs wrapping"]
        format_state.queued_terminal_output = ["queued content"]
        format_state.plain_output = ["plain content"]
        format_state.markdown_output = ["markdown content"]
        
        mock_wrapper = Mock()
        mock_wrapper.wrap_text.return_value = ["wrapped line 1", "wrapped line 2"]
        
        mock_justifier = Mock()
        mock_justifier.justify_text.return_value = "justified content"
        
        with patch('suitkaise.fdl._int.core.main_processor._TextWrapper', return_value=mock_wrapper), \
             patch('suitkaise.fdl._int.core.main_processor._TextJustifier', return_value=mock_justifier):
            
            self.processor._apply_wrapping_and_justification(format_state)
            
            # Should create wrapper and justifier with correct width
            mock_wrapper.wrap_text.assert_called()
            mock_justifier.justify_text.assert_called()
    
    def test_apply_wrapping_and_justification_empty_streams(self):
        """Test applying wrapping and justification to empty streams."""
        format_state = Mock()
        format_state.terminal_width = 80
        format_state.justify = 'left'
        format_state.terminal_output = []
        format_state.queued_terminal_output = []
        format_state.plain_output = []
        format_state.markdown_output = []
        
        mock_wrapper = Mock()
        mock_justifier = Mock()
        
        with patch('suitkaise.fdl._int.core.main_processor._TextWrapper', return_value=mock_wrapper), \
             patch('suitkaise.fdl._int.core.main_processor._TextJustifier', return_value=mock_justifier):
            
            self.processor._apply_wrapping_and_justification(format_state)
            
            # Should not call wrapper or justifier for empty streams
            mock_wrapper.wrap_text.assert_not_called()
            mock_justifier.justify_text.assert_not_called()
    
    def test_apply_wrapping_and_justification_whitespace_only(self):
        """Test applying wrapping and justification to whitespace-only content."""
        format_state = Mock()
        format_state.terminal_width = 80
        format_state.justify = 'left'
        format_state.terminal_output = ["   \n  \t  "]
        format_state.queued_terminal_output = []
        format_state.plain_output = []
        format_state.markdown_output = []
        
        mock_wrapper = Mock()
        mock_justifier = Mock()
        
        with patch('suitkaise.fdl._int.core.main_processor._TextWrapper', return_value=mock_wrapper), \
             patch('suitkaise.fdl._int.core.main_processor._TextJustifier', return_value=mock_justifier):
            
            self.processor._apply_wrapping_and_justification(format_state)
            
            # Should not process whitespace-only content
            mock_wrapper.wrap_text.assert_not_called()
            mock_justifier.justify_text.assert_not_called()


class TestFDLProcessorIntegration:
    """Test suite for FDL processor integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = _FDLProcessor()
    
    def test_full_processing_pipeline_text_only(self):
        """Test full processing pipeline with text only."""
        fdl_string = "Hello, World!"
        
        # Mock the dependencies to isolate the processor logic
        with patch('suitkaise.fdl._int.core.main_processor._create_format_state') as mock_create_state:
            mock_state = _FormatState()
            mock_state.terminal_output = []
            mock_state.queued_terminal_output = []
            mock_create_state.return_value = mock_state
            
            with patch.object(self.processor, '_integrate_progress_bar_state'), \
                 patch.object(self.processor, '_apply_final_formatting'):
                
                # Process the string
                elements = self.processor._parse_sequential(fdl_string)
                
                # Should create one text element
                assert len(elements) == 1
                assert isinstance(elements[0], _TextElement)
                assert elements[0].content == "Hello, World!"
    
    def test_full_processing_pipeline_mixed_elements(self):
        """Test full processing pipeline with mixed elements."""
        fdl_string = "Hello <name>, you are </bold>awesome</end bold>!"
        
        # Mock element creation to verify parsing
        with patch.object(self.processor, '_parse_bracket_element') as mock_parse:
            mock_parse.side_effect = [
                _VariableElement("name"),
                _CommandElement("bold"),
                _CommandElement("end bold")
            ]
            
            elements = self.processor._parse_sequential(fdl_string)
            
            # Should create: text, variable, text, command, text, command, text
            assert len(elements) == 7
            assert isinstance(elements[0], _TextElement)  # "Hello "
            assert isinstance(elements[1], _VariableElement)  # "<name>"
            assert isinstance(elements[2], _TextElement)  # ", you are "
            assert isinstance(elements[3], _CommandElement)  # "</bold>"
            assert isinstance(elements[4], _TextElement)  # "awesome"
            assert isinstance(elements[5], _CommandElement)  # "</end bold>"
            assert isinstance(elements[6], _TextElement)  # "!"
    
    def test_element_processing_sequence(self):
        """Test that elements are processed in correct sequence."""
        fdl_string = "Start <var> Middle </cmd> End"
        values = ("VALUE",)
        
        processed_elements = []
        
        def mock_process(format_state):
            processed_elements.append(self)
            return format_state
        
        with patch('suitkaise.fdl._int.core.main_processor._create_format_state') as mock_create_state:
            mock_state = Mock()
            mock_state.get_final_outputs.return_value = {'terminal': 'result'}
            mock_create_state.return_value = mock_state
            
            with patch.object(_TextElement, 'process', mock_process), \
                 patch.object(_VariableElement, 'process', mock_process), \
                 patch.object(_CommandElement, 'process', mock_process), \
                 patch.object(self.processor, '_integrate_progress_bar_state'), \
                 patch.object(self.processor, '_apply_final_formatting'):
                
                self.processor.process_string(fdl_string, values)
                
                # Should process elements in sequence
                assert len(processed_elements) > 0


class TestFDLProcessorEdgeCases:
    """Test suite for FDL processor edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = _FDLProcessor()
    
    def test_empty_string_processing(self):
        """Test processing empty string."""
        fdl_string = ""
        
        elements = self.processor._parse_sequential(fdl_string)
        
        assert len(elements) == 0
    
    def test_whitespace_only_string(self):
        """Test processing whitespace-only string."""
        fdl_string = "   \n\t  "
        
        elements = self.processor._parse_sequential(fdl_string)
        
        assert len(elements) == 1
        assert isinstance(elements[0], _TextElement)
        assert elements[0].content == "   \n\t  "
    
    def test_malformed_brackets(self):
        """Test processing malformed brackets."""
        fdl_string = "Hello < incomplete"
        
        elements = self.processor._parse_sequential(fdl_string)
        
        # Should treat as plain text
        assert len(elements) == 1
        assert isinstance(elements[0], _TextElement)
        assert elements[0].content == "Hello < incomplete"
    
    def test_unmatched_brackets(self):
        """Test processing unmatched brackets."""
        fdl_string = "Hello > unmatched < brackets"
        
        elements = self.processor._parse_sequential(fdl_string)
        
        # Should treat as plain text
        assert len(elements) == 1
        assert isinstance(elements[0], _TextElement)
        assert elements[0].content == "Hello > unmatched < brackets"
    
    def test_consecutive_brackets(self):
        """Test processing consecutive brackets."""
        fdl_string = "<first><second><third>"
        
        with patch.object(self.processor, '_parse_bracket_element') as mock_parse:
            mock_parse.side_effect = [
                _VariableElement("first"),
                _VariableElement("second"),
                _VariableElement("third")
            ]
            
            elements = self.processor._parse_sequential(fdl_string)
            
            assert len(elements) == 3
            assert all(isinstance(elem, _VariableElement) for elem in elements)
    
    def test_special_characters_in_text(self):
        """Test processing special characters in text."""
        fdl_string = "Special chars: !@#$%^&*()_+-=[]{}|;:,.<>?"
        
        elements = self.processor._parse_sequential(fdl_string)
        
        # Should parse as text, but < and > might be interpreted as brackets
        # The exact behavior depends on whether they form valid bracket pairs
        assert len(elements) >= 1
        assert any(isinstance(elem, _TextElement) for elem in elements)
    
    def test_unicode_characters(self):
        """Test processing Unicode characters."""
        fdl_string = "Unicode: 你好世界 😀🎉 café naïve"
        
        elements = self.processor._parse_sequential(fdl_string)
        
        assert len(elements) == 1
        assert isinstance(elements[0], _TextElement)
        assert elements[0].content == "Unicode: 你好世界 😀🎉 café naïve"
    
    def test_very_long_string(self):
        """Test processing very long string."""
        fdl_string = "Long text " * 1000 + "<var>" + " more text " * 1000
        
        with patch.object(self.processor, '_parse_bracket_element') as mock_parse:
            mock_parse.return_value = _VariableElement("var")
            
            elements = self.processor._parse_sequential(fdl_string)
            
            # Should handle long strings without issues
            assert len(elements) == 3
            assert isinstance(elements[0], _TextElement)
            assert isinstance(elements[1], _VariableElement)
            assert isinstance(elements[2], _TextElement)
    
    def test_deeply_nested_processing(self):
        """Test processing with many nested elements."""
        # Create string with many bracket pairs
        fdl_string = ""
        for i in range(100):
            fdl_string += f"text{i} <var{i}> "
        
        with patch.object(self.processor, '_parse_bracket_element') as mock_parse:
            mock_parse.side_effect = [_VariableElement(f"var{i}") for i in range(100)]
            
            elements = self.processor._parse_sequential(fdl_string)
            
            # Should handle many elements
            assert len(elements) == 200  # 100 text + 100 variable elements


class TestFDLProcessorVisualDemonstration:
    """Visual demonstration tests for FDL processor system."""
    
    def test_visual_fdl_processor_demonstration(self):
        """Visual demonstration of FDL processor capabilities."""
        print("\n" + "="*60)
        print("FDL PROCESSOR - CAPABILITIES DEMONSTRATION")
        print("="*60)
        
        processor = _FDLProcessor()
        
        print(f"\nFDL Processor Initialization:")
        print(f"  Has regex pattern: {hasattr(processor, '_all_brackets_pattern')}")
        print(f"  Pattern type: {type(processor._all_brackets_pattern)}")
        
        # Test regex pattern matching
        test_strings = [
            "Simple text",
            "Text with <variable>",
            "Multiple <var1> and <var2>",
            "Command </bold>text</end>",
            "Object <time:now>",
            "Mixed <var> and </cmd> and <obj:val>"
        ]
        
        print(f"\nRegex Pattern Testing:")
        for test_string in test_strings:
            matches = list(processor._all_brackets_pattern.finditer(test_string))
            match_strings = [m.group(0) for m in matches]
            print(f"  '{test_string}'")
            print(f"    Matches: {match_strings}")
    
    def test_visual_parsing_demonstration(self):
        """Visual demonstration of FDL string parsing."""
        print("\n" + "="*60)
        print("FDL PROCESSOR - PARSING DEMONSTRATION")
        print("="*60)
        
        processor = _FDLProcessor()
        
        test_cases = [
            ("Simple text", "Plain text without any FDL elements"),
            ("Hello <name>!", "Text with variable substitution"),
            ("</bold>Bold text</end bold>", "Text with formatting commands"),
            ("<time:now> is the time", "Text with object element"),
            ("Mix <var> and </cmd> plus <obj:val>", "Mixed element types"),
            ("<><empty><>", "Empty and invalid brackets"),
        ]
        
        print(f"\nParsing Test Cases:")
        for fdl_string, description in test_cases:
            print(f"\n  Input: '{fdl_string}'")
            print(f"  Description: {description}")
            
            # Mock the bracket parsing to show element types
            with patch.object(processor, '_parse_bracket_element') as mock_parse:
                def mock_bracket_parser(bracket):
                    inner = bracket[1:-1]  # Remove < >
                    if not inner:
                        return None
                    elif inner.startswith('/'):
                        return f"CommandElement('{inner[1:]}')"
                    elif ':' in inner:
                        return f"ObjectElement('{inner}')"
                    else:
                        return f"VariableElement('{inner}')"
                
                mock_parse.side_effect = mock_bracket_parser
                
                try:
                    elements = processor._parse_sequential(fdl_string)
                    print(f"  Elements ({len(elements)}):")
                    for i, element in enumerate(elements):
                        if isinstance(element, _TextElement):
                            content_preview = element.content[:20] + "..." if len(element.content) > 20 else element.content
                            print(f"    {i}: TextElement('{content_preview}')")
                        else:
                            print(f"    {i}: {element}")
                except Exception as e:
                    print(f"    Error: {e}")
    
    def test_visual_element_type_detection_demonstration(self):
        """Visual demonstration of element type detection."""
        print("\n" + "="*60)
        print("FDL PROCESSOR - ELEMENT TYPE DETECTION DEMONSTRATION")
        print("="*60)
        
        processor = _FDLProcessor()
        
        bracket_test_cases = [
            ("<variable>", "Variable element"),
            ("</command>", "Command element"),
            ("<object:value>", "Object element"),
            ("<invalid-pattern!>", "Invalid - becomes text"),
            ("<>", "Empty - returns None"),
            ("<123invalid>", "Invalid identifier - becomes text"),
            ("</end command>", "End command element"),
        ]
        
        print(f"\nBracket Element Type Detection:")
        for bracket_content, expected_type in bracket_test_cases:
            print(f"\n  Bracket: '{bracket_content}'")
            print(f"  Expected: {expected_type}")
            
            # Mock the validation functions for demonstration
            with patch('suitkaise.fdl._int.core.main_processor._is_valid_object_pattern') as mock_obj, \
                 patch('suitkaise.fdl._int.core.main_processor._is_valid_variable_pattern') as mock_var:
                
                inner = bracket_content[1:-1]  # Remove < >
                
                # Set up mocks based on content
                if ':' in inner:
                    mock_obj.return_value = True
                    mock_var.return_value = False
                elif inner.startswith('/'):
                    mock_obj.return_value = False
                    mock_var.return_value = False
                elif inner.isidentifier():
                    mock_obj.return_value = False
                    mock_var.return_value = True
                else:
                    mock_obj.return_value = False
                    mock_var.return_value = False
                
                try:
                    element = processor._parse_bracket_element(bracket_content)
                    if element is None:
                        print(f"    Result: None")
                    else:
                        print(f"    Result: {type(element).__name__}")
                        if hasattr(element, 'content'):
                            print(f"    Content: '{element.content}'")
                        elif hasattr(element, 'variable_name'):
                            print(f"    Variable: '{element.variable_name}'")
                except Exception as e:
                    print(f"    Error: {e}")
    
    def test_visual_processing_pipeline_demonstration(self):
        """Visual demonstration of the complete processing pipeline."""
        print("\n" + "="*60)
        print("FDL PROCESSOR - PROCESSING PIPELINE DEMONSTRATION")
        print("="*60)
        
        processor = _FDLProcessor()
        
        # Simulate processing pipeline steps
        fdl_string = "Hello <name>, you are </bold>awesome</end bold>!"
        values = ("World",)
        
        print(f"\nProcessing Pipeline Steps:")
        print(f"  Input FDL String: '{fdl_string}'")
        print(f"  Input Values: {values}")
        
        print(f"\n  Step 1: Create Format State")
        print(f"    - Initialize with values: {values}")
        print(f"    - Set terminal width and defaults")
        
        print(f"\n  Step 2: Progress Bar Integration")
        print(f"    - Check for active progress bars")
        print(f"    - Configure output queuing if needed")
        
        print(f"\n  Step 3: Parse Sequential Elements")
        elements = processor._parse_sequential(fdl_string)
        print(f"    - Found {len(elements)} elements:")
        for i, element in enumerate(elements):
            element_type = type(element).__name__
            if hasattr(element, 'content'):
                content = element.content[:15] + "..." if len(element.content) > 15 else element.content
                print(f"      {i}: {element_type}('{content}')")
            else:
                print(f"      {i}: {element_type}")
        
        print(f"\n  Step 4: Process Each Element")
        print(f"    - Each element updates format state")
        print(f"    - Variables substitute values")
        print(f"    - Commands modify formatting")
        print(f"    - Objects generate content")
        
        print(f"\n  Step 5: Apply Final Formatting")
        print(f"    - Text wrapping and justification")
        print(f"    - Add ANSI reset codes")
        print(f"    - Generate final outputs")
        
        print(f"\n  Step 6: Return Results")
        print(f"    - Terminal output (with ANSI codes)")
        print(f"    - Plain text output")
        print(f"    - Markdown output")
        print(f"    - HTML output")
    
    def test_visual_error_handling_demonstration(self):
        """Visual demonstration of error handling."""
        print("\n" + "="*60)
        print("FDL PROCESSOR - ERROR HANDLING DEMONSTRATION")
        print("="*60)
        
        processor = _FDLProcessor()
        
        error_test_cases = [
            ("Malformed < bracket", "Incomplete bracket"),
            ("Empty <> brackets", "Empty bracket content"),
            ("<invalid!@#>", "Invalid characters in bracket"),
            ("Normal text", "No brackets at all"),
            ("<very_long_variable_name_that_might_cause_issues>", "Very long variable name"),
        ]
        
        print(f"\nError Handling Test Cases:")
        for fdl_string, description in error_test_cases:
            print(f"\n  Input: '{fdl_string}'")
            print(f"  Scenario: {description}")
            
            try:
                elements = processor._parse_sequential(fdl_string)
                print(f"  Result: Successfully parsed {len(elements)} elements")
                for i, element in enumerate(elements):
                    element_type = type(element).__name__
                    if hasattr(element, 'content'):
                        content = element.content[:20] + "..." if len(element.content) > 20 else element.content
                        print(f"    {i}: {element_type}('{content}')")
                    else:
                        print(f"    {i}: {element_type}")
            except Exception as e:
                print(f"  Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestFDLProcessorVisualDemonstration()
    demo.test_visual_fdl_processor_demonstration()
    demo.test_visual_parsing_demonstration()
    demo.test_visual_element_type_detection_demonstration()
    demo.test_visual_processing_pipeline_demonstration()
    demo.test_visual_error_handling_demonstration()
    
    print("\n" + "="*60)
    print("✅ FDL PROCESSOR TESTS COMPLETE")
    print("="*60)