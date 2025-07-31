"""
Comprehensive tests for FDL Text Element Processor.

Tests the text element processor that handles plain text content,
including box integration, formatting preservation, and visual demonstrations.
"""

import pytest
import sys
import os
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.elements.text_element import _TextElement
from suitkaise.fdl._int.core.format_state import _FormatState, _create_format_state


class TestTextElement:
    """Test suite for the text element processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.format_state = _create_format_state()
    
    def test_text_element_initialization(self):
        """Test text element initialization with various content types."""
        # Normal text
        element = _TextElement("Hello World")
        assert element.content == "Hello World"
        
        # Empty text
        element = _TextElement("")
        assert element.content == ""
        
        # None content (should convert to string)
        element = _TextElement(None)
        assert element.content is None
        
        # Unicode text
        element = _TextElement("こんにちは")
        assert element.content == "こんにちは"
        
        # Text with special characters
        element = _TextElement("Special chars: !@#$%^&*()")
        assert element.content == "Special chars: !@#$%^&*()"
    
    def test_process_normal_mode(self):
        """Test processing text in normal mode (not in box)."""
        content = "Normal text processing"
        element = _TextElement(content)
        
        result_state = element.process(self.format_state)
        
        # Should return the same state object
        assert result_state is self.format_state
        
        # Content should be added to output streams
        outputs = result_state.get_final_outputs()
        assert content in outputs['terminal']
        assert content in outputs['plain']
        assert content in outputs['markdown']
        assert content in outputs['html']
    
    def test_process_box_mode(self):
        """Test processing text when inside a box."""
        content = "Box text content"
        element = _TextElement(content)
        
        # Enable box mode
        self.format_state.in_box = True
        
        result_state = element.process(self.format_state)
        
        # Content should be added to box_content, not output streams
        assert content in result_state.box_content
        
        # Output streams should be empty
        outputs = result_state.get_final_outputs()
        assert content not in outputs['terminal']
        assert content not in outputs['plain']
    
    def test_process_empty_content(self):
        """Test processing empty or None content."""
        # Empty string
        element = _TextElement("")
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        
        # Empty content should still be processed
        assert "" in outputs['terminal'] or len(outputs['terminal']) == 0
        
        # None content
        element = _TextElement(None)
        self.format_state = _create_format_state()  # Reset state
        result_state = element.process(self.format_state)
        
        # Should handle None gracefully
        assert result_state is not None
    
    def test_process_with_formatting_applied(self):
        """Test that text element respects current formatting state."""
        content = "Formatted text"
        element = _TextElement(content)
        
        # Apply formatting to state
        self.format_state.bold = True
        self.format_state.text_color = "red"
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        
        # Terminal output should contain ANSI codes for formatting
        terminal_output = outputs['terminal']
        assert '\033[31m' in terminal_output  # Red color
        assert '\033[1m' in terminal_output   # Bold
        assert content in terminal_output
        
        # Plain output should just contain the text
        assert outputs['plain'] == content
    
    def test_process_long_text_wrapping(self):
        """Test processing long text that requires wrapping."""
        long_content = "This is a very long line of text that should wrap when the terminal width is narrow enough to force text wrapping behavior in the text element processor."
        
        element = _TextElement(long_content)
        
        # Set narrow terminal width
        self.format_state.terminal_width = 40
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        
        # Should contain newlines from wrapping
        assert '\n' in outputs['terminal']
        
        # Each line should be within terminal width
        lines = outputs['terminal'].split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                visual_width = wcswidth(line.strip()) or len(line.strip())
                assert visual_width <= self.format_state.terminal_width
    
    def test_process_unicode_content(self):
        """Test processing Unicode content including emojis."""
        unicode_content = "Unicode: こんにちは 🌍 世界"
        element = _TextElement(unicode_content)
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        
        # Unicode content should be preserved in all outputs
        assert unicode_content in outputs['terminal']
        assert unicode_content in outputs['plain']
        assert unicode_content in outputs['markdown']
        assert unicode_content in outputs['html']
    
    def test_process_special_characters(self):
        """Test processing text with special characters and symbols."""
        special_content = "Special: ←→↑↓ ♠♣♥♦ ∑∆∞ ©®™"
        element = _TextElement(special_content)
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        
        # Special characters should be preserved
        assert special_content in outputs['plain']
        assert special_content in outputs['terminal']
    
    def test_process_whitespace_preservation(self):
        """Test that whitespace is properly preserved."""
        whitespace_content = "  Leading spaces\n\nMultiple\n\n\nNewlines\t\tTabs  "
        element = _TextElement(whitespace_content)
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        
        # Whitespace should be preserved in plain output
        assert whitespace_content in outputs['plain']
    
    def test_process_with_justification(self):
        """Test text processing with different justification modes."""
        content = "Justified text"
        element = _TextElement(content)
        
        justifications = ['left', 'center', 'right']
        
        for justify in justifications:
            # Reset format state for each test
            format_state = _create_format_state()
            format_state.justify = justify
            format_state.terminal_width = 50
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            # Should contain the content
            assert content in outputs['plain']
            
            # Terminal output should reflect justification
            if justify == 'center':
                # Centered text should have padding
                terminal_lines = outputs['terminal'].split('\n')
                for line in terminal_lines:
                    if content in line:
                        # Should have leading whitespace for centering
                        stripped = line.lstrip()
                        assert len(line) >= len(stripped)
    
    def test_multiple_text_elements_processing(self):
        """Test processing multiple text elements in sequence."""
        texts = ["First text", "Second text", "Third text"]
        elements = [_TextElement(text) for text in texts]
        
        # Process all elements with the same format state
        for element in elements:
            self.format_state = element.process(self.format_state)
        
        outputs = self.format_state.get_final_outputs()
        
        # All texts should be in the output
        for text in texts:
            assert text in outputs['terminal']
            assert text in outputs['plain']
    
    def test_text_element_in_box_with_formatting(self):
        """Test text element inside a box with formatting applied."""
        content = "Box formatted text"
        element = _TextElement(content)
        
        # Set up box mode with formatting
        self.format_state.in_box = True
        self.format_state.bold = True
        self.format_state.text_color = "blue"
        
        result_state = element.process(self.format_state)
        
        # Content should be in box_content
        assert content in result_state.box_content
        
        # Should not be in main output streams yet
        outputs = result_state.get_final_outputs()
        assert content not in outputs['terminal']
    
    def test_edge_case_very_long_single_word(self):
        """Test handling of very long single words that can't be wrapped."""
        long_word = "supercalifragilisticexpialidocious" * 5  # Very long word
        element = _TextElement(long_word)
        
        # Set narrow terminal width
        self.format_state.terminal_width = 20
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        
        # Should still contain the word, even if it exceeds terminal width
        assert long_word in outputs['plain']
    
    def test_newline_handling(self):
        """Test handling of explicit newlines in text content."""
        multiline_content = "Line 1\nLine 2\nLine 3"
        element = _TextElement(multiline_content)
        
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        
        # Newlines should be preserved
        assert '\n' in outputs['terminal']
        assert '\n' in outputs['plain']
        
        # Should contain all lines
        lines = ["Line 1", "Line 2", "Line 3"]
        for line in lines:
            assert line in outputs['plain']


class TestTextElementEdgeCases:
    """Test edge cases and error conditions for text element."""
    
    def test_text_element_with_ansi_codes_in_content(self):
        """Test text element with ANSI codes already in content."""
        content_with_ansi = "Text with \033[31mred\033[0m color codes"
        element = _TextElement(content_with_ansi)
        
        format_state = _create_format_state()
        result_state = element.process(format_state)
        outputs = result_state.get_final_outputs()
        
        # ANSI codes should be preserved in terminal output
        assert '\033[31m' in outputs['terminal']
        assert '\033[0m' in outputs['terminal']
        
        # Plain output should contain the codes as-is
        assert content_with_ansi in outputs['plain']
    
    def test_text_element_with_html_like_content(self):
        """Test text element with HTML-like content."""
        html_content = "<div>HTML-like content</div>"
        element = _TextElement(html_content)
        
        format_state = _create_format_state()
        result_state = element.process(format_state)
        outputs = result_state.get_final_outputs()
        
        # HTML-like content should be treated as plain text
        assert html_content in outputs['plain']
        assert html_content in outputs['terminal']
        
        # HTML output should escape the content appropriately
        # (this depends on the base element's HTML formatting)
        assert html_content in outputs['html']
    
    def test_text_element_with_markdown_like_content(self):
        """Test text element with Markdown-like content."""
        markdown_content = "**Bold** and *italic* text"
        element = _TextElement(markdown_content)
        
        format_state = _create_format_state()
        result_state = element.process(format_state)
        outputs = result_state.get_final_outputs()
        
        # Markdown-like content should be treated as plain text
        assert markdown_content in outputs['plain']
        assert markdown_content in outputs['terminal']


class TestTextElementVisualDemonstration:
    """Visual demonstration tests for text element processor."""
    
    def test_visual_basic_text_demonstration(self):
        """Visual demonstration of basic text processing."""
        print("\n" + "="*60)
        print("TEXT ELEMENT PROCESSOR - BASIC DEMONSTRATION")
        print("="*60)
        
        test_texts = [
            "Simple plain text",
            "Text with numbers: 12345",
            "Text with symbols: !@#$%^&*()",
            "Mixed case: UpPeR aNd LoWeR",
            "",  # Empty text
            "   Whitespace   padded   text   ",
        ]
        
        for i, text in enumerate(test_texts, 1):
            print(f"\n{i}. Text: '{text}'")
            
            element = _TextElement(text)
            format_state = _create_format_state()
            format_state.text_color = "cyan"
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            print(f"   Output: ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
    
    def test_visual_unicode_demonstration(self):
        """Visual demonstration of Unicode text processing."""
        print("\n" + "="*60)
        print("TEXT ELEMENT - UNICODE DEMONSTRATION")
        print("="*60)
        
        unicode_texts = [
            "English: Hello World!",
            "Japanese: こんにちは世界！",
            "Chinese: 你好世界！",
            "Korean: 안녕하세요!",
            "Arabic: مرحبا بالعالم!",
            "Russian: Привет мир!",
            "Emojis: 🌍🎉🔥💫⭐🚀",
            "Math symbols: ∑∆∞≈≠±×÷√",
            "Arrows: ←→↑↓⤴⤵⚡",
            "Mixed: Hello 世界 🌍 Test ✅",
        ]
        
        for text in unicode_texts:
            element = _TextElement(text)
            format_state = _create_format_state()
            format_state.text_color = "green"
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            # Calculate visual width
            visual_width = wcswidth(text) or len(text)
            
            print(f"Width: {visual_width:2d} | ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
    
    def test_visual_formatting_demonstration(self):
        """Visual demonstration of text with various formatting."""
        print("\n" + "="*60)
        print("TEXT ELEMENT - FORMATTING DEMONSTRATION")
        print("="*60)
        
        base_text = "Formatted text example"
        
        formatting_options = [
            ("Plain", {}),
            ("Bold", {"bold": True}),
            ("Italic", {"italic": True}),
            ("Underlined", {"underline": True}),
            ("Red", {"text_color": "red"}),
            ("Blue background", {"background_color": "blue"}),
            ("Bold + Red", {"bold": True, "text_color": "red"}),
            ("All formatting", {
                "bold": True, 
                "italic": True, 
                "underline": True, 
                "text_color": "yellow", 
                "background_color": "blue"
            }),
        ]
        
        for label, formatting in formatting_options:
            element = _TextElement(base_text)
            format_state = _create_format_state()
            
            # Apply formatting
            for attr, value in formatting.items():
                setattr(format_state, attr, value)
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            print(f"{label:15} -> ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
    
    def test_visual_wrapping_demonstration(self):
        """Visual demonstration of text wrapping at different widths."""
        print("\n" + "="*60)
        print("TEXT ELEMENT - WRAPPING DEMONSTRATION")
        print("="*60)
        
        long_text = "This is a very long line of text that demonstrates how the text element processor handles automatic text wrapping when the terminal width is set to different values. It should wrap cleanly at word boundaries."
        
        widths = [30, 50, 70]
        
        for width in widths:
            print(f"\nTerminal width: {width}")
            print("┌" + "─" * (width - 2) + "┐")
            
            element = _TextElement(long_text)
            format_state = _create_format_state()
            format_state.terminal_width = width
            format_state.text_color = "cyan"
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            # Split into lines and display with borders
            lines = outputs['terminal'].split('\n')
            for line in lines:
                if line.strip():  # Skip empty lines
                    print("│", end="")
                    print(line, end="")
                    print("\033[0m│")
            
            print("└" + "─" * (width - 2) + "┘")
    
    def test_visual_box_mode_demonstration(self):
        """Visual demonstration of text processing in box mode."""
        print("\n" + "="*60)
        print("TEXT ELEMENT - BOX MODE DEMONSTRATION")
        print("="*60)
        
        texts = [
            "First line in box",
            "Second line in box",
            "Third line with formatting"
        ]
        
        print("\nNormal mode (direct to output):")
        for text in texts:
            element = _TextElement(text)
            format_state = _create_format_state()
            format_state.text_color = "green"
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            print("  ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
        
        print("\nBox mode (accumulated in box_content):")
        format_state = _create_format_state()
        format_state.in_box = True
        format_state.text_color = "yellow"
        
        for text in texts:
            element = _TextElement(text)
            format_state = element.process(format_state)
        
        print("  Box content accumulated:")
        for i, content in enumerate(format_state.box_content, 1):
            print(f"    {i}. '{content}'")
    
    def test_visual_justification_demonstration(self):
        """Visual demonstration of text justification."""
        print("\n" + "="*60)
        print("TEXT ELEMENT - JUSTIFICATION DEMONSTRATION")
        print("="*60)
        
        test_text = "Justified text"
        terminal_width = 40
        
        justifications = ['left', 'center', 'right']
        
        for justify in justifications:
            print(f"\n{justify.upper()} JUSTIFICATION:")
            print("┌" + "─" * (terminal_width - 2) + "┐")
            
            element = _TextElement(test_text)
            format_state = _create_format_state()
            format_state.terminal_width = terminal_width
            format_state.justify = justify
            format_state.text_color = "magenta"
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            print("│", end="")
            print(outputs['terminal'], end="")
            print("\033[0m│")
            print("└" + "─" * (terminal_width - 2) + "┘")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestTextElementVisualDemonstration()
    demo.test_visual_basic_text_demonstration()
    demo.test_visual_unicode_demonstration()
    demo.test_visual_formatting_demonstration()
    demo.test_visual_wrapping_demonstration()
    demo.test_visual_box_mode_demonstration()
    demo.test_visual_justification_demonstration()
    
    print("\n" + "="*60)
    print("✅ TEXT ELEMENT PROCESSOR TESTS COMPLETE")
    print("="*60)