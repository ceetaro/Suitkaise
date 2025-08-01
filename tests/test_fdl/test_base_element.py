"""
Comprehensive tests for FDL Base Element Processor.

Tests the abstract base class that all element processors inherit from,
including output stream handling, formatting methods, and visual demonstrations.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.elements.base_element import _ElementProcessor
from suitkaise.fdl._int.core.format_state import _FormatState, _create_format_state


class ConcreteElementProcessor(_ElementProcessor):
    """Concrete implementation for testing the abstract base class."""
    
    def __init__(self, content: str = "test content"):
        self.content = content
    
    def process(self, format_state: _FormatState) -> _FormatState:
        """Simple implementation that adds content to outputs."""
        self._add_to_outputs(format_state, self.content)
        return format_state


class TestBaseElementProcessor:
    """Test suite for the base element processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ConcreteElementProcessor()
        self.format_state = _create_format_state()
    
    def test_abstract_base_class_cannot_be_instantiated(self):
        """Test that the abstract base class cannot be instantiated directly."""
        with pytest.raises(TypeError):
            _ElementProcessor()
    
    def test_concrete_implementation_can_be_instantiated(self):
        """Test that concrete implementations work properly."""
        processor = ConcreteElementProcessor("hello world")
        assert processor.content == "hello world"
        
        # Test processing
        state = _create_format_state()
        result_state = processor.process(state)
        assert result_state is not None
        
        # Check output was added
        outputs = result_state.get_final_outputs()
        assert "hello world" in outputs['terminal']
        assert "hello world" in outputs['plain']
    
    def test_add_to_outputs_normal_mode(self):
        """Test adding content to outputs in normal mode (not in box)."""
        content = "Normal output test"
        self.processor._add_to_outputs(self.format_state, content)
        
        outputs = self.format_state.get_final_outputs()
        assert content in outputs['terminal']
        assert content in outputs['plain']
        assert content in outputs['markdown']
        assert content in outputs['html']
    
    def test_add_to_outputs_box_mode(self):
        """Test adding content to outputs when inside a box."""
        self.format_state.in_box = True
        content = "Box content test"
        
        self.processor._add_to_outputs(self.format_state, content)
        
        # In box mode, content should be added to box_content
        assert content in self.format_state.box_content
    
    def test_add_to_outputs_empty_content(self):
        """Test that empty content is handled gracefully."""
        self.processor._add_to_outputs(self.format_state, "")
        self.processor._add_to_outputs(self.format_state, None)
        
        outputs = self.format_state.get_final_outputs()
        # Should not add empty content
        assert outputs['terminal'] == ""
        assert outputs['plain'] == ""
    
    def test_format_for_terminal_with_ansi_codes(self):
        """Test terminal formatting with ANSI codes."""
        self.format_state.bold = True
        self.format_state.text_color = "red"
        
        content = "Bold red text"
        result = self.processor._format_for_terminal(content, self.format_state)
        
        # Should contain ANSI codes for bold and red
        assert '\033[31m' in result  # Red color
        assert '\033[1m' in result   # Bold
        assert content in result
    
    def test_format_for_plain_text_no_formatting(self):
        """Test plain text formatting removes all formatting."""
        self.format_state.bold = True
        self.format_state.text_color = "blue"
        self.format_state.italic = True
        
        content = "Plain text with no formatting"
        result = self.processor._format_for_plain(content, self.format_state)
        
        # Should be exactly the same as input - no formatting
        assert result == content
        assert '\033[' not in result  # No ANSI codes
    
    def test_format_for_markdown_basic_formatting(self):
        """Test markdown formatting conversion."""
        content = "markdown text"
        
        # Test bold
        self.format_state.bold = True
        result = self.processor._format_for_markdown(content, self.format_state)
        assert result == f"**{content}**"
        
        # Test italic
        self.format_state.bold = False
        self.format_state.italic = True
        result = self.processor._format_for_markdown(content, self.format_state)
        assert result == f"*{content}*"
        
        # Test bold + italic
        self.format_state.bold = True
        result = self.processor._format_for_markdown(content, self.format_state)
        assert result == f"***{content}***"
        
        # Test strikethrough
        self.format_state.bold = False
        self.format_state.italic = False
        self.format_state.strikethrough = True
        result = self.processor._format_for_markdown(content, self.format_state)
        assert result == f"~~{content}~~"
    
    def test_format_for_html_with_styles(self):
        """Test HTML formatting with CSS styles."""
        content = "HTML styled text"
        
        # Test with color
        self.format_state.text_color = "#FF0000"
        result = self.processor._format_for_html(content, self.format_state)
        assert 'style="color: #FF0000"' in result
        assert f"<span" in result
        assert f">{content}</span>" in result
        
        # Test with background
        self.format_state.background_color = "blue"
        result = self.processor._format_for_html(content, self.format_state)
        assert 'background-color:' in result
        
        # Test with classes
        self.format_state.bold = True
        self.format_state.italic = True
        result = self.processor._format_for_html(content, self.format_state)
        assert 'class="fdl-bold fdl-italic"' in result
    
    def test_format_for_html_no_formatting_needed(self):
        """Test HTML formatting when no formatting is applied."""
        content = "Plain HTML text"
        result = self.processor._format_for_html(content, self.format_state)
        
        # Should return content unchanged when no formatting
        assert result == content
        assert '<span' not in result
    
    def test_needs_html_formatting_detection(self):
        """Test detection of when HTML formatting is needed."""
        # No formatting needed
        assert not self.processor._needs_html_formatting(self.format_state)
        
        # Text color needs formatting
        self.format_state.text_color = "red"
        assert self.processor._needs_html_formatting(self.format_state)
        
        # Reset and test background color
        self.format_state.text_color = None
        self.format_state.background_color = "blue"
        assert self.processor._needs_html_formatting(self.format_state)
        
        # Test text formatting flags
        self.format_state.background_color = None
        self.format_state.bold = True
        assert self.processor._needs_html_formatting(self.format_state)
        
        self.format_state.bold = False
        self.format_state.italic = True
        assert self.processor._needs_html_formatting(self.format_state)
        
        self.format_state.italic = False
        self.format_state.underline = True
        assert self.processor._needs_html_formatting(self.format_state)
        
        self.format_state.underline = False
        self.format_state.strikethrough = True
        assert self.processor._needs_html_formatting(self.format_state)
    
    def test_generate_ansi_codes_comprehensive(self):
        """Test ANSI code generation for all formatting options."""
        # Test no formatting
        codes = self.processor._generate_ansi_codes(self.format_state)
        assert codes == ""
        
        # Test text color
        self.format_state.text_color = "red"
        codes = self.processor._generate_ansi_codes(self.format_state)
        assert '\033[31m' in codes
        
        # Test background color
        self.format_state.background_color = "blue"
        codes = self.processor._generate_ansi_codes(self.format_state)
        assert '\033[44m' in codes
        
        # Test all text formatting
        self.format_state.bold = True
        self.format_state.italic = True
        self.format_state.underline = True
        self.format_state.strikethrough = True
        
        codes = self.processor._generate_ansi_codes(self.format_state)
        assert '\033[1m' in codes   # Bold
        assert '\033[3m' in codes   # Italic
        assert '\033[4m' in codes   # Underline
        assert '\033[9m' in codes   # Strikethrough
    
    def test_text_wrapping_and_justification(self):
        """Test text wrapping and justification in normal mode."""
        # Create long content that will wrap
        long_content = "This is a very long line of text that should definitely wrap to multiple lines when processed through the text wrapping system in the base element processor."
        
        processor = ConcreteElementProcessor(long_content)
        
        # Set narrow terminal width to force wrapping
        self.format_state.terminal_width = 40
        processor.process(self.format_state)
        
        outputs = self.format_state.get_final_outputs()
        terminal_output = outputs['terminal']
        
        # Should contain newlines from wrapping
        assert '\n' in terminal_output
        
        # Each line should be within terminal width (accounting for ANSI codes)
        lines = terminal_output.split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                # Use visual width to account for ANSI codes
                visual_width = wcswidth(line) or len(line)
                assert visual_width <= self.format_state.terminal_width
    
    def test_justification_modes(self):
        """Test different text justification modes."""
        content = "Center me"
        processor = ConcreteElementProcessor(content)
        
        # Test center justification
        self.format_state.justify = 'center'
        self.format_state.terminal_width = 80
        processor.process(self.format_state)
        
        outputs = self.format_state.get_final_outputs()
        terminal_output = outputs['terminal'].strip()
        
        # Should have padding for centering
        assert len(terminal_output) >= len(content)
    
    def test_unicode_and_emoji_handling(self):
        """Test handling of wide Unicode characters and emojis."""
        # Test with East Asian characters (width 2)
        unicode_content = "こんにちは世界"  # "Hello World" in Japanese
        processor = ConcreteElementProcessor(unicode_content)
        processor.process(self.format_state)
        
        outputs = self.format_state.get_final_outputs()
        assert unicode_content in outputs['plain']
        
        # Test with emojis
        emoji_content = "Hello 👋 World 🌍"
        processor = ConcreteElementProcessor(emoji_content)
        
        # Reset format state
        self.format_state = _create_format_state()
        processor.process(self.format_state)
        
        outputs = self.format_state.get_final_outputs()
        assert emoji_content in outputs['plain']
    
    def test_mixed_content_types(self):
        """Test processing mixed content with various character types."""
        mixed_content = "ASCII text, 中文字符, emojis 🎉🔥, and symbols ←→↑↓"
        processor = ConcreteElementProcessor(mixed_content)
        processor.process(self.format_state)
        
        outputs = self.format_state.get_final_outputs()
        assert mixed_content in outputs['plain']
        assert mixed_content in outputs['terminal']


class TestBaseElementVisualDemonstration:
    """Visual demonstration tests for base element processor."""
    
    def test_visual_formatting_demonstration(self):
        """Visual demonstration of different formatting options."""
        print("\n" + "="*60)
        print("BASE ELEMENT PROCESSOR - VISUAL DEMONSTRATION")
        print("="*60)
        
        # Test different formatting combinations
        test_cases = [
            ("Plain text", {}),
            ("Bold text", {"bold": True}),
            ("Italic text", {"italic": True}),
            ("Underlined text", {"underline": True}),
            ("Red text", {"text_color": "red"}),
            ("Blue background", {"background_color": "blue"}),
            ("Bold red on yellow", {"bold": True, "text_color": "red", "background_color": "yellow"}),
            ("All formatting", {"bold": True, "italic": True, "underline": True, "text_color": "green", "background_color": "black"}),
        ]
        
        for content, formatting in test_cases:
            format_state = _create_format_state()
            
            # Apply formatting
            for attr, value in formatting.items():
                setattr(format_state, attr, value)
            
            processor = ConcreteElementProcessor(content)
            processor.process(format_state)
            
            outputs = format_state.get_final_outputs()
            
            print(f"\n{content:20} -> ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")  # Reset formatting
    
    def test_visual_text_wrapping_demonstration(self):
        """Visual demonstration of text wrapping with different widths."""
        print("\n" + "="*60)
        print("TEXT WRAPPING DEMONSTRATION")
        print("="*60)
        
        long_text = "This is a very long line of text that demonstrates how the base element processor handles text wrapping at different terminal widths. It should wrap cleanly at word boundaries."
        
        widths = [40, 60, 80]
        
        for width in widths:
            print(f"\nTerminal width: {width}")
            print("-" * width)
            
            format_state = _create_format_state()
            format_state.terminal_width = width
            
            processor = ConcreteElementProcessor(long_text)
            processor.process(format_state)
            
            outputs = format_state.get_final_outputs()
            print(outputs['terminal'])
    
    def test_visual_unicode_emoji_demonstration(self):
        """Visual demonstration of Unicode and emoji handling."""
        print("\n" + "="*60)
        print("UNICODE AND EMOJI DEMONSTRATION")
        print("="*60)
        
        test_strings = [
            "ASCII: Hello World!",
            "Japanese: こんにちは世界！",
            "Chinese: 你好世界！",
            "Korean: 안녕하세요 세계!",
            "Emojis: 🌍🎉🔥💫⭐",
            "Mixed: Hello 世界 🌍 Test!",
            "Symbols: ←→↑↓⚡⚠️✅❌",
            "Math: ∑∆∞≈≠±×÷√",
        ]
        
        for test_string in test_strings:
            format_state = _create_format_state()
            format_state.text_color = "cyan"
            
            processor = ConcreteElementProcessor(test_string)
            processor.process(format_state)
            
            outputs = format_state.get_final_outputs()
            
            # Calculate visual width
            visual_width = wcswidth(test_string) or len(test_string)
            
            print(f"Visual width: {visual_width:2d} | ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
    
    def test_visual_justification_demonstration(self):
        """Visual demonstration of text justification."""
        print("\n" + "="*60)
        print("TEXT JUSTIFICATION DEMONSTRATION")
        print("="*60)
        
        test_text = "Justified Text"
        terminal_width = 50
        
        justifications = ['left', 'center', 'right']
        
        for justify in justifications:
            print(f"\n{justify.upper()} JUSTIFICATION:")
            print("┌" + "─" * (terminal_width - 2) + "┐")
            
            format_state = _create_format_state()
            format_state.terminal_width = terminal_width
            format_state.justify = justify
            format_state.text_color = "green"
            
            processor = ConcreteElementProcessor(test_text)
            processor.process(format_state)
            
            outputs = format_state.get_final_outputs()
            
            print("│", end="")
            print(outputs['terminal'], end="")
            print("\033[0m│")
            print("└" + "─" * (terminal_width - 2) + "┘")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestBaseElementVisualDemonstration()
    demo.test_visual_formatting_demonstration()
    demo.test_visual_text_wrapping_demonstration()
    demo.test_visual_unicode_emoji_demonstration()
    demo.test_visual_justification_demonstration()
    
    print("\n" + "="*60)
    print("✅ BASE ELEMENT PROCESSOR TESTS COMPLETE")
    print("="*60)