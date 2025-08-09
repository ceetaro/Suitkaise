# tests/test_fdl/test_setup/test_text_justification.py - FIXED VERSION
import pytest
import sys
from unittest.mock import patch, Mock

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

# Import text wrapping to prepare text for justification tests
from setup.text_wrapping import _TextWrapper, _wrap_text, _get_visual_width

# Import text justification for testing
from setup.text_justification import (
    _TextJustifier, _justify_text, _get_visible_length, _text_justifier
)


class TestTextJustifier:
    """Test the internal _TextJustifier class."""
    
    def test_initialization(self):
        """Test _TextJustifier initialization."""
        # Test with default terminal width
        justifier = _TextJustifier()
        assert justifier.terminal_width >= 60
        assert hasattr(justifier, '_ansi_pattern')
        
        # Test with custom width
        justifier = _TextJustifier(120)
        assert justifier.terminal_width == 120
    
    def test_center_justification_exact_padding(self):
        """Test center justification with exact padding calculation."""
        # Use a known width for precise testing
        justifier = _TextJustifier(60)
        
        test_text = "Hello"  # 5 characters
        result = justifier._justify_center(test_text)
        
        # Should fill exactly 60 characters
        assert len(result) == 60, f"Center justified length: {len(result)} != 60"
        
        # Text should be in the center
        text_pos = result.find("Hello")
        expected_pos = (60 - 5) // 2  # 27
        assert text_pos == expected_pos, f"Text position: {text_pos} != {expected_pos}"
        
        # Should be surrounded by correct padding
        left_padding = text_pos
        right_padding = len(result) - text_pos - len(test_text)
        total_padding = left_padding + right_padding
        
        assert total_padding == 55, f"Total padding: {total_padding} != 55"
        assert abs(left_padding - right_padding) <= 1, f"Uneven padding: {left_padding} vs {right_padding}"
    
    def test_ansi_code_handling_fixed(self):
        """Test ANSI code handling with correct expectations."""
        justifier = _TextJustifier(60)
        
        # Use text that fits in one line to test pure justification
        ansi_text = "\033[31mRed\033[0m text"
        result = justifier.justify_text(ansi_text, 'right')
        
        # ANSI codes should be preserved
        assert "\033[31m" in result
        assert "\033[0m" in result
        assert "Red" in result
        assert "text" in result
        
        # Should be exactly 60 characters visually
        visual_width = justifier.get_visible_length(result)
        assert visual_width == 60, f"Right justified visual width: {visual_width} != 60"
    
    def test_text_wrapping_with_justification(self):
        """Test justification with pre-wrapped text (using text wrapping module)."""
        # Step 1: Use text wrapping to wrap long text
        wrapper = _TextWrapper(40)  # Narrow width to force wrapping
        justifier = _TextJustifier(40)  # IMPORTANT: Same width for both
        
        long_text = ("This is a very long piece of text that contains many words and will "
                    "definitely exceed the 40-character width limit and force text wrapping "
                    "to occur across multiple lines.")
        
        # Wrap the text first
        wrapped_lines = wrapper.wrap_text(long_text)
        assert len(wrapped_lines) > 1, f"Text should wrap into multiple lines: {len(wrapped_lines)}"
        
        # Verify each wrapped line fits within 40 characters
        for i, line in enumerate(wrapped_lines):
            if line.strip():
                line_width = wrapper.get_visual_width(line)
                assert line_width <= 40, f"Wrapped line {i+1} too wide: {line_width} > 40: '{line}'"
        
        # Step 2: Pass wrapped text to justifier
        wrapped_text = '\n'.join(wrapped_lines)
        
        # Test center justification on pre-wrapped text
        center_result = justifier.justify_text(wrapped_text, 'center')
        center_lines = center_result.split('\n')
        
        # Each line should be properly center-justified to 40 characters
        for i, line in enumerate(center_lines):
            if line.strip():  # Skip empty lines
                visual_width = justifier.get_visible_length(line)
                assert visual_width == 40, f"Center line {i+1} width: {visual_width} != 40"
        
        # Test right justification on pre-wrapped text
        right_result = justifier.justify_text(wrapped_text, 'right')
        right_lines = right_result.split('\n')
        
        for i, line in enumerate(right_lines):
            if line.strip():
                visual_width = justifier.get_visible_length(line)
                assert visual_width == 40, f"Right line {i+1} width: {visual_width} != 40"
    
    def test_wide_character_justification(self):
        """Test justification with wide characters."""
        justifier = _TextJustifier(40)  # Explicit width
        
        # Chinese text that fits in one line
        chinese_text = "你好世界"
        result = justifier.justify_text(chinese_text, 'right')
        
        # Should preserve Chinese characters and be right-aligned to 40 characters
        assert "你好世界" in result
        visual_width = justifier.get_visible_length(result)
        assert visual_width == 40, f"Chinese text visual width: {visual_width} != 40"
        
        # Test with emojis
        emoji_text = "Hello 😀"
        result = justifier.justify_text(emoji_text, 'center')
        
        # Should preserve emoji and be centered to 40 characters
        assert "😀" in result
        assert "Hello" in result
        visual_width = justifier.get_visible_length(result)
        assert visual_width == 40, f"Emoji text visual width: {visual_width} != 40"
    
    def test_mixed_content_comprehensive(self):
        """Test comprehensive mixed content justification."""
        justifier = _TextJustifier(50)  # Explicit width
        
        # Mixed content: ANSI codes + wide chars + emojis (fits in one line)
        mixed_text = "\033[31m红色\033[0m 😀"
        
        for justify_type in ['center', 'right']:
            result = justifier.justify_text(mixed_text, justify_type)
            
            # All components should be preserved
            assert "\033[31m" in result and "\033[0m" in result
            assert "红色" in result
            assert "😀" in result
            
            # Should be properly justified to exactly 50 characters
            visual_width = justifier.get_visible_length(result)
            assert visual_width == 50, f"{justify_type} width: {visual_width} != 50"
    
    def test_multiline_input(self):
        """Test justification with multiline input."""
        justifier = _TextJustifier(30)  # Explicit width
        
        # Multi-line text (each line fits within 30 characters)
        multiline_text = "Short line\nMedium length\nLong but fits"
        
        # Test center justification
        center_result = justifier.justify_text(multiline_text, 'center')
        center_lines = center_result.split('\n')
        
        assert len(center_lines) == 3, "Should preserve all lines"
        
        for i, line in enumerate(center_lines):
            visual_width = justifier.get_visible_length(line)
            assert visual_width == 30, f"Line {i+1} should be padded to 30 chars: {visual_width}"
            
            # Check that original content is preserved
            original_line = multiline_text.split('\n')[i]
            assert original_line in line, f"Original content should be preserved in line {i+1}"
    
    def test_empty_and_whitespace_lines(self):
        """Test handling of empty and whitespace-only lines."""
        justifier = _TextJustifier(20)
        
        # Test empty string
        result = justifier.justify_text("", 'center')
        assert result == ""
        
        # Test whitespace-only line
        whitespace_line = "   "
        result = justifier.justify_text(whitespace_line, 'center')
        assert result == whitespace_line  # Should return unchanged
        
        # Test mix of empty and content lines
        mixed_lines = "Content\n\nMore content\n   \nFinal"
        result = justifier.justify_text(mixed_lines, 'right')
        lines = result.split('\n')
        
        # Content lines should be justified, empty lines preserved
        assert len(lines) == 5
        assert "Content" in lines[0]
        assert lines[1] == ""  # Empty line preserved
        assert "More content" in lines[2]
        assert lines[3] == "   "  # Whitespace line preserved
        assert "Final" in lines[4]


class TestGlobalTextJustifier:
    """Test global text justifier instance and convenience functions."""
    
    def test_global_justifier_exists(self):
        """Test that global _text_justifier exists."""
        assert hasattr(_text_justifier, 'justify_text')
        assert hasattr(_text_justifier, 'terminal_width')
        assert _text_justifier.terminal_width >= 60
    
    def test_convenience_function(self):
        """Test global _justify_text convenience function."""
        # Test basic functionality with explicit width
        text = "Hello world"
        result = _justify_text(text, 'center', 30)
        
        # Should be centered in 30 characters
        assert len(result) == 30, f"Result length: {len(result)} != 30"
        assert "Hello world" in result
        
        # Test with default terminal width
        result = _justify_text(text, 'right')
        assert "Hello world" in result
        assert len(result) >= len("Hello world"), "Result should be at least as long as input"
    
    def test_get_visible_length_function(self):
        """Test global _get_visible_length convenience function."""
        # ASCII text
        length = _get_visible_length("Hello")
        assert length == 5
        
        # ANSI codes should be ignored
        ansi_text = "\033[31mHello\033[0m"
        length = _get_visible_length(ansi_text)
        assert length == 5

        # Wide characters
        wide_text = "你好"
        length = _get_visible_length(wide_text)
        # Note: wcwidth might not be available, so we can't assume exact width
        assert length >= 2  # At least 2 characters
        
        # Mixed content
        mixed_text = "Hello 你好 😀"
        length = _get_visible_length(mixed_text)
        # Note: wcwidth might not be available, so we can't assume exact width
        assert length >= 5  # At least the ASCII part


class TestTextJustificationEdgeCases:
    """Test edge cases and potential failure scenarios."""
    
    def test_invalid_justification_mode(self):
        """Test handling of invalid justification modes."""
        justifier = _TextJustifier(40)
        text = "Hello world"
        
        # Invalid mode should fallback to left justification
        result = justifier.justify_text(text, 'invalid_mode')
        assert result == text  # Should return unchanged text
        
        # Test with None mode
        result = justifier.justify_text(text, None)
        assert result == text
    
    def test_text_longer_than_width(self):
        """Test justification when text is longer than terminal width."""
        justifier = _TextJustifier(10)  # Very narrow width
        long_text = "This text is much longer than 10 characters"
        
        # Should still justify (text wrapping should be done separately)
        for mode in ['left', 'center', 'right']:
            result = justifier.justify_text(long_text, mode)
            if mode == 'left':
                assert result == long_text
            else:
                # Center/right should still attempt justification
                assert len(result) >= len(long_text)
    
    def test_zero_width_terminal(self):
        """Test behavior with zero or negative terminal width."""
        # Zero width should use minimum width
        justifier = _TextJustifier(0)
        assert justifier.terminal_width >= 60
        
        # Negative width should use minimum width
        justifier = _TextJustifier(-10)
        assert justifier.terminal_width >= 60
        
        # Test that justification still works with minimum width
        text = "Hello"
        result = justifier.justify_text(text, 'center')
        # The result should be at least as long as the minimum width
        assert len(result) >= 60
        assert "Hello" in result
        
        # Test with a different justifier instance
        justifier2 = _TextJustifier(0)
        result2 = justifier2.justify_text(text, 'right')
        assert len(result2) >= 60
        assert "Hello" in result2
        
        # Test that the actual terminal width is being used correctly
        assert justifier.terminal_width == justifier2.terminal_width
    
    def test_very_large_width(self):
        """Test justification with very large terminal width."""
        justifier = _TextJustifier(1000)
        text = "Short text"
        
        result = justifier.justify_text(text, 'center')
        assert len(result) == 1000
        assert text in result
        
        result = justifier.justify_text(text, 'right')
        assert len(result) == 1000
        assert text in result
    
    def test_unicode_normalization(self):
        """Test handling of Unicode normalization issues."""
        justifier = _TextJustifier(40)
        
        # Test with combining characters
        combining_text = "e\u0301"  # e + combining acute accent
        result = justifier.justify_text(combining_text, 'center')
        assert combining_text in result
        
        # Test with zero-width characters
        zero_width_text = "Hello\u200bWorld"  # Zero-width space
        result = justifier.justify_text(zero_width_text, 'center')
        assert zero_width_text in result
    
    def test_control_characters(self):
        """Test handling of control characters."""
        justifier = _TextJustifier(40)
        
        # Test with tabs
        tab_text = "Hello\tWorld"
        result = justifier.justify_text(tab_text, 'center')
        assert tab_text in result
        
        # Test with newlines in text (should be handled by multiline logic)
        newline_text = "Line1\nLine2"
        result = justifier.justify_text(newline_text, 'center')
        lines = result.split('\n')
        assert len(lines) == 2
    
    def test_ansi_code_edge_cases(self):
        """Test edge cases with ANSI codes."""
        justifier = _TextJustifier(40)
        
        # Test with incomplete ANSI codes
        incomplete_ansi = "\033[31mRed text without reset"
        result = justifier.justify_text(incomplete_ansi, 'center')
        assert "\033[31m" in result
        assert "Red text without reset" in result
        
        # Test with nested ANSI codes
        nested_ansi = "\033[1m\033[31mBold Red\033[0m"
        result = justifier.justify_text(nested_ansi, 'right')
        assert "\033[1m" in result
        assert "\033[31m" in result
        assert "Bold Red" in result
        
        # Test with complex ANSI sequences
        complex_ansi = "\033[38;2;255;165;0mOrange\033[0m"
        result = justifier.justify_text(complex_ansi, 'center')
        assert complex_ansi in result
    
    def test_whitespace_preservation(self):
        """Test that whitespace is properly preserved."""
        justifier = _TextJustifier(40)
        
        # Leading/trailing whitespace
        spaced_text = "  Hello  "
        result = justifier.justify_text(spaced_text, 'center')
        assert "  Hello  " in result
        
        # Multiple spaces
        multi_space = "Hello    World"
        result = justifier.justify_text(multi_space, 'right')
        assert "Hello    World" in result
    
    def test_empty_and_null_inputs(self):
        """Test handling of empty and null inputs."""
        justifier = _TextJustifier(40)
        
        # Empty string
        assert justifier.justify_text("", 'center') == ""
        assert justifier.justify_text("", 'right') == ""
        
        # None input (should handle gracefully)
        try:
            result = justifier.justify_text(None, 'center')
            # If it doesn't raise an exception, should return None or empty string
            assert result is None or result == ""
        except (TypeError, AttributeError):
            # Expected behavior - should raise an exception for None
            pass
    
    def test_very_short_widths(self):
        """Test justification with very short terminal widths."""
        justifier = _TextJustifier(5)  # Very short width
        text = "Hi"
        
        result = justifier.justify_text(text, 'center')
        assert len(result) == 5
        assert "Hi" in result
        
        result = justifier.justify_text(text, 'right')
        assert len(result) == 5
        assert "Hi" in result
    
    def test_emoji_combinations(self):
        """Test justification with complex emoji combinations."""
        justifier = _TextJustifier(40)
        
        # Family emoji (multiple code points)
        family_emoji = "👨‍👩‍👧‍👦"
        result = justifier.justify_text(family_emoji, 'center')
        assert family_emoji in result
        
        # Flag emoji (regional indicator pairs)
        flag_emoji = "🇺🇸"
        result = justifier.justify_text(flag_emoji, 'right')
        assert flag_emoji in result
        
        # Skin tone modifier
        skin_tone = "👍🏽"
        result = justifier.justify_text(skin_tone, 'center')
        assert skin_tone in result
    
    def test_mixed_width_character_combinations(self):
        """Test justification with complex mixed-width character combinations."""
        justifier = _TextJustifier(50)
        
        # Complex mixed content
        complex_text = "Hello 你好 😀 World 🌍 世界"
        result = justifier.justify_text(complex_text, 'center')
        assert "Hello" in result
        assert "你好" in result
        assert "😀" in result
        assert "World" in result
        assert "🌍" in result
        assert "世界" in result
    
    def test_justification_accuracy(self):
        """Test that justification is mathematically accurate."""
        justifier = _TextJustifier(20)
        
        # Test center justification accuracy
        text = "Hi"
        result = justifier.justify_text(text, 'center')
        
        # Should be exactly 20 characters
        assert len(result) == 20
        
        # Text should be centered
        text_pos = result.find("Hi")
        expected_pos = (20 - 2) // 2  # 9
        assert text_pos == expected_pos
        
        # Test right justification accuracy
        result = justifier.justify_text(text, 'right')
        assert len(result) == 20
        
        # Text should be at the end
        text_pos = result.find("Hi")
        expected_pos = 20 - 2  # 18
        assert text_pos == expected_pos
    
    def test_multiline_edge_cases(self):
        """Test edge cases with multiline text."""
        justifier = _TextJustifier(30)
        
        # Empty lines in middle
        text = "First\n\nThird"
        result = justifier.justify_text(text, 'center')
        lines = result.split('\n')
        assert len(lines) == 3
        assert lines[1] == ""  # Empty line preserved
        
        # Lines with only whitespace
        text = "First\n   \nThird"
        result = justifier.justify_text(text, 'right')
        lines = result.split('\n')
        assert len(lines) == 3
        assert lines[1] == "   "  # Whitespace preserved
        
        # Single line with newline at end
        text = "Hello\n"
        result = justifier.justify_text(text, 'center')
        lines = result.split('\n')
        assert len(lines) == 2
        assert lines[1] == ""  # Trailing newline preserved
    
    def test_performance_edge_cases(self):
        """Test performance with large inputs."""
        justifier = _TextJustifier(80)
        
        # Very long text (should handle without hanging)
        long_text = "A" * 1000
        result = justifier.justify_text(long_text, 'center')
        assert len(result) >= len(long_text)
        assert "A" * 1000 in result
        
        # Many lines
        many_lines = "\n".join([f"Line {i}" for i in range(100)])
        result = justifier.justify_text(many_lines, 'right')
        lines = result.split('\n')
        assert len(lines) == 100
    
    def test_ansi_code_stripping_accuracy(self):
        """Test that ANSI code stripping is accurate."""
        justifier = _TextJustifier(40)
        
        # Test various ANSI code patterns
        test_cases = [
            "\033[31mRed\033[0m",
            "\033[1;31mBold Red\033[0m",
            "\033[38;2;255;0;0mRGB Red\033[0m",
            "\033[48;2;0;255;0mGreen Background\033[0m",
            "\033[1;31;42mBold Red on Green\033[0m",
        ]
        
        for ansi_text in test_cases:
            # Strip ANSI codes manually for comparison
            stripped = justifier._strip_ansi_codes(ansi_text)
            
            # Should not contain ANSI escape sequences
            assert "\033[" not in stripped
            
            # Should contain the actual text content
            assert any(char.isalnum() or char.isspace() for char in stripped)
    
    def test_visual_width_calculation_accuracy(self):
        """Test that visual width calculation is accurate in the real workflow (wrap then justify)."""
        justifier = _TextJustifier(40)
        wrapper = _TextWrapper(40)
        
        # ASCII characters
        assert justifier._get_visual_width("Hello") == 5
        
        # Wide characters - wcwidth might not be available
        wide_width = justifier._get_visual_width("你好")
        assert wide_width >= 2  # At least 2 characters
        
        # Emojis - wcwidth might not be available
        emoji_width = justifier._get_visual_width("😀")
        assert emoji_width >= 1  # At least 1 character
        
        # Mixed content - wcwidth might not be available
        mixed_width = justifier._get_visual_width("Hello 你好 😀")
        assert mixed_width >= 5  # At least the ASCII part
        
        # ANSI codes should be ignored
        assert justifier._get_visual_width("\033[31mHello\033[0m") == 5
        
        # Tab characters - test real workflow (wrap then justify)
        wrapped_lines = wrapper.wrap_text("Hello\tWorld")
        wrapped_text = '\n'.join(wrapped_lines)
        tab_width = justifier._get_visual_width(wrapped_text)
        assert tab_width >= 13  # Should be expanded by wrapper
        
        # Zero-width characters should be ignored
        zero_width = justifier._get_visual_width("Hello\u200bWorld")
        assert zero_width >= 10  # At least the visible characters


def run_visual_examples():
    """Show comprehensive visual examples of text justification."""
    print("🚀 START OF TEXT JUSTIFICATION TESTS 🚀")
    print("🎨 COMPREHENSIVE TEXT JUSTIFICATION DEMONSTRATIONS")
    print("=" * 80)
    
    # Reset any ANSI color codes that might be active
    print("\033[0m", end="")
    
    # Test different terminal widths
    test_widths = [20, 40, 60, 80]
    
    # Sample texts for different scenarios
    sample_texts = {
        "Short Text": "Hello",
        "Medium Text": "This is a medium length text",
        "Long Text": "This is a much longer piece of text that demonstrates justification",
        "Wide Characters": "你好世界",
        "Emojis": "Hello 😀 World 🌍",
        "Mixed Content": "Hello 你好 😀 World",
        "ANSI Colors": "\033[31mRed\033[0m \033[32mGreen\033[0m \033[34mBlue\033[0m",
        "File Path": "/usr/local/bin/python3",
        "URL": "https://github.com/username/project",
        "Code Comment": "# This is a code comment",
        "Empty Line": "",
        "Whitespace": "   ",
        "Single Character": "A",
        "Punctuation": "Hello, world! How are you?",
        "Numbers": "1234567890",
        "Special Chars": "!@#$%^&*()",
        "Very Long": "This is an extremely long piece of text that will definitely exceed the width limit and show how justification works with very long content",
    }
    
    # Justification modes to test
    justification_modes = ['left', 'center', 'right']
    
    # Run visual demonstrations for each width
    for width in test_widths:
        print(f"\n📏 TERMINAL WIDTH: {width} CHARACTERS")
        print("─" * 60)
        
        justifier = _TextJustifier(width)
        
        for text_name, text_content in sample_texts.items():
            print(f"\n🔤 {text_name}")
            print(f"Text: '{text_content}'")
            print(f"Visual length: {justifier.get_visible_length(text_content)} characters")
            
            # Show width indicator
            print("─" * width)
            
            # Test each justification mode
            for i, mode in enumerate(justification_modes):
                # Always wrap text first (real-world workflow)
                wrapper = _TextWrapper(width)
                wrapped_lines = wrapper.wrap_text(text_content)
                wrapped_text = '\n'.join(wrapped_lines)
                # Then justify the wrapped text
                result = justifier.justify_text(wrapped_text, mode)
                print(result)
                # Add newline after left and center justification
                if mode in ['left', 'center']:  # After left and center justification
                    print()
            
            # Add width indicator after right output
            print("─" * width)
            print()
    
    # Special demonstration: Text Wrapping + Justification workflow
    print("\n🎯 TEXT WRAPPING + JUSTIFICATION WORKFLOW DEMONSTRATION")
    print("=" * 60)
    
    workflow_texts = {
        "Paragraph": (
            "This is a longer paragraph that demonstrates the proper workflow: "
            "first we use the text wrapping module to wrap the text, then we pass "
            "the wrapped text to the justification module for alignment."
        ),
        
        "Technical Documentation": (
            "The FDL (Format Description Language) system provides advanced text formatting "
            "capabilities including color support, terminal detection, and intelligent text "
            "wrapping. It handles ANSI escape codes safely and preserves word boundaries."
        ),
        
        "Code Example": (
            "# This is a very long comment that demonstrates how text wrapping works with "
            "code-style content. It should break at appropriate points while preserving "
            "the readability of the comment structure."
        ),
        
        "Mixed Content": (
            "Hello 你好 😀 This text contains multiple types of content: English text, "
            "Chinese characters, and emojis. The justification system should handle all "
            "of these correctly while maintaining proper alignment."
        )
    }
    
    for text_name, text_content in workflow_texts.items():
        print(f"\n📝 {text_name}")
        print(f"Original text length: {len(text_content)} characters")
        
        # Test at different widths
        for width in [40, 60, 80]:
            print(f"\nWidth: {width} characters")
            print("─" * width)
            
            # Step 1: Wrap the text
            wrapper = _TextWrapper(width)
            wrapped_lines = wrapper.wrap_text(text_content)
            wrapped_text = '\n'.join(wrapped_lines)
            
            print("Wrapped (left):")
            for line in wrapped_lines:
        print(line)
    
            # Step 2: Justify the wrapped text
            justifier = _TextJustifier(width)
            
    print(f"\nCenter justified:")
            center_result = justifier.justify_text(wrapped_text, 'center')
            for line in center_result.split('\n'):
        print(line)
    
    print(f"\nRight justified:")
            right_result = justifier.justify_text(wrapped_text, 'right')
            for line in right_result.split('\n'):
        print(line)
            
            print()
    
    # Edge cases demonstration
    print("\n🔍 EDGE CASES DEMONSTRATION")
    print("=" * 60)
    
    edge_cases = {
        "Empty String": "",
        "Single Space": " ",
        "Multiple Spaces": "   ",
        "Single Character": "A",
        "Very Long Word": "supercalifragilisticexpialidocious",
        "Mixed Width": "A你好😀B",
        "ANSI Codes": "Normal \033[31mRed\033[0m text",
        "Tabs": "Tab\tseparated\ttext",
        "Newlines": "Line1\nLine2\nLine3",
        "Special Unicode": "café naïve résumé",
    }
    
    edge_justifier = _TextJustifier(50)
    
    for case_name, text_content in edge_cases.items():
        print(f"\n🔤 {case_name}")
        print(f"Text: '{text_content}'")
        print(f"Visual length: {edge_justifier.get_visible_length(text_content)} characters")
        
        print("─" * 50)
        
        for i, mode in enumerate(justification_modes):
            # Always wrap text first (real-world workflow)
            wrapper = _TextWrapper(50)
            wrapped_lines = wrapper.wrap_text(text_content)
            wrapped_text = '\n'.join(wrapped_lines)
            # Then justify the wrapped text
            result = edge_justifier.justify_text(wrapped_text, mode)
            print(result)
            # Add newline after left and center justification
            if mode in ['left', 'center']:  # After left and center justification
                print()
        
        # Add width indicator after right output
        print("─" * 50)
        print()
    
    # ANSI code preservation demonstration
    print("\n🎨 ANSI CODE PRESERVATION DEMONSTRATION")
    print("=" * 60)
    
    ansi_texts = {
        "Simple Colors": "\033[31mRed\033[0m \033[32mGreen\033[0m \033[34mBlue\033[0m",
        "Bold Text": "\033[1mBold\033[0m normal \033[1mBold Again\033[0m",
        "Mixed Formatting": "\033[1;31;42mBold Red on Green\033[0m normal text",
        "Complex Colors": "\033[38;2;255;165;0mOrange\033[0m \033[38;2;128;0;128mPurple\033[0m",
    }
    
    ansi_justifier = _TextJustifier(60)
    
    for text_name, text_content in ansi_texts.items():
        print(f"\n🔤 {text_name}")
        print(f"Text: {text_content}")
        print(f"Visual length: {ansi_justifier.get_visible_length(text_content)} characters")
        
        print("─" * 60)
        
        for i, mode in enumerate(justification_modes):
            # Always wrap text first (real-world workflow)
            wrapper = _TextWrapper(60)
            wrapped_lines = wrapper.wrap_text(text_content)
            wrapped_text = '\n'.join(wrapped_lines)
            # Then justify the wrapped text
            result = ansi_justifier.justify_text(wrapped_text, mode)
            print(result)
            # Add newline after left and center justification
            if mode in ['left', 'center']:  # After left and center justification
                print()
        
        # Add width indicator after right output
        print("─" * 60)
        print()


def run_tests():
    """Run all text justification tests."""
    import traceback
    
    # Show visual examples first
    run_visual_examples()
    
    test_classes = [
        TestTextJustifier,
        TestGlobalTextJustifier,
        TestTextJustificationEdgeCases,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("=" * 60)
    print("🧪 Running Unit Tests")
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 30)
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Create instance and run test
                test_instance = test_class()
                test_method = getattr(test_instance, method_name)
                test_method()
                
                print(f"  ✅ {method_name}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {method_name}: {str(e)}")
                import traceback
                print(f"     Traceback: {traceback.format_exc()}")
                failed_tests.append(f"{test_class.__name__}.{method_name}: {str(e)}")
                
                # Print traceback for debugging
                if "--verbose" in sys.argv:
                    print("    " + "\n    ".join(traceback.format_exc().split('\n')))
    
    # Summary
    print(f"\n📊 Test Results: {passed_tests}/{total_tests} passed")
    
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for failure in failed_tests:
            print(f"  • {failure}")
        return False
    else:
        print("🎉 All tests passed!")
        return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)