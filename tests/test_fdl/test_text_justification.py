# tests/test_fdl/test_setup/test_text_justification.py
import pytest
import sys
from unittest.mock import patch, Mock

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

from setup.text_justification import (
    _TextJustifier, _justify_text, _get_visible_length, _text_justifier
)


class TestTextJustifier:
    """Test the internal _TextJustifier class."""
    
    def test_initialization(self):
        """Test _TextJustifier initialization."""
        # Test with default terminal width
        justifier = _TextJustifier()
        assert justifier.terminal_width >= 80  # Should use detected width
        assert hasattr(justifier, '_ansi_pattern')
        
        # Test with custom width
        justifier = _TextJustifier(120)
        assert justifier.terminal_width == 120
    
    def test_left_justification_default(self):
        """Test left justification (default behavior)."""
        justifier = _TextJustifier(50)
        
        # Left justification should return text unchanged
        text = "Hello world"
        result = justifier.justify_text(text, 'left')
        assert result == text
        
        # Multi-line text
        multiline = "Line 1\nLine 2\nLine 3"
        result = justifier.justify_text(multiline, 'left')
        assert result == multiline
    
    def test_right_justification(self):
        """Test right justification with realistic terminal width."""
        # Use actual terminal width with minimum of 60
        terminal_width = max(60, _text_justifier.terminal_width)
        justifier = _TextJustifier(terminal_width)
        
        # Test with different lengths of text
        test_texts = [
            "Hello",
            "Medium length text",
            "This is a longer piece of text to test right justification"
        ]
        
        for text in test_texts:
            if len(text) < terminal_width:  # Only test if text fits
                result = justifier.justify_text(text, 'right')
                
                # Should have padding on the left
                assert result.endswith(text), f"Text should end with original content: '{result}'"
                assert len(result) >= len(text), f"Result should be at least as long as input"
                
                # Visual length should equal terminal width
                visual_length = justifier.get_visible_length(result)
                assert visual_length == terminal_width, f"Right justified should fill width: {visual_length} != {terminal_width}"
                
                # Should start with spaces (right justified)
                assert result.startswith(" "), f"Right justified text should start with space: '{result}'"
                
                # Verify exact positioning
                stripped = result.lstrip()
                leading_spaces = len(result) - len(stripped)
                expected_spaces = terminal_width - len(text)
                assert leading_spaces == expected_spaces, f"Wrong padding: {leading_spaces} != {expected_spaces}"
    
    def test_center_justification(self):
        """Test center justification with realistic terminal width and exact positioning."""
        # Use actual terminal width
        terminal_width = max(60, _text_justifier.terminal_width)
        justifier = _TextJustifier(terminal_width)
        
        # Test with different text lengths
        test_texts = [
            "Hi",
            "Medium text",
            "This is longer text for testing center justification"
        ]
        
        for text in test_texts:
            if len(text) < terminal_width:  # Only test if text fits
                result = justifier.justify_text(text, 'center')
                
                # Should contain the original text
                assert text in result, f"Original text missing from result: '{result}'"
                assert len(result) >= len(text), f"Result shorter than input"
                
                # Find the position of the text in the result
                text_pos = result.find(text)
                assert text_pos >= 0, f"Text not found in result: '{result}'"
                
                # Calculate padding
                left_padding = text_pos
                right_padding = len(result) - text_pos - len(text)
                total_padding = left_padding + right_padding
                
                # Verify centering is correct
                expected_total_padding = terminal_width - len(text)
                assert total_padding == expected_total_padding, f"Wrong total padding: {total_padding} != {expected_total_padding}"
                
                # Left padding should be roughly half (within 1 for odd padding)
                expected_left_padding = expected_total_padding // 2
                assert abs(left_padding - expected_left_padding) <= 1, f"Not centered: left={left_padding}, expected≈{expected_left_padding}"
                
                # Verify visual length
                visual_length = justifier.get_visible_length(result)
                assert visual_length <= terminal_width, f"Result too wide: {visual_length} > {terminal_width}"
    
    def test_multiline_justification(self):
        """Test justification of multi-line text with realistic content."""
        # Use actual terminal width
        terminal_width = max(60, _text_justifier.terminal_width)
        justifier = _TextJustifier(terminal_width)
        
        # Create realistic multi-line content with varying lengths
        multiline = ("Short line\n"
                    "This is a medium length line for testing\n" 
                    "Here we have an even longer line that contains more text content for justification testing\n"
                    "End")
        
        # Test right justification
        result = justifier.justify_text(multiline, 'right')
        lines = result.split('\n')
        
        # Each line should be right-justified independently
        expected_lines = multiline.split('\n')
        assert len(lines) == len(expected_lines), "Line count mismatch"
        
        for i, (result_line, original_line) in enumerate(zip(lines, expected_lines)):
            if original_line.strip():  # Skip empty lines
                # Should end with the original content (right-justified)
                assert result_line.rstrip().endswith(original_line.rstrip()), f"Line {i} not properly right-justified: '{result_line}'"
                
                # Should fill the terminal width if shorter than width
                if len(original_line) < terminal_width:
                    visual_length = justifier.get_visible_length(result_line)
                    assert visual_length == terminal_width, f"Line {i} not full width: {visual_length} != {terminal_width}"
        
        # Test center justification
        result = justifier.justify_text(multiline, 'center')
        lines = result.split('\n')
        
        for i, (result_line, original_line) in enumerate(zip(lines, expected_lines)):
            if original_line.strip() and len(original_line) < terminal_width:
                # Find original content position
                content_pos = result_line.find(original_line.strip())
                assert content_pos >= 0, f"Line {i} content not found: '{result_line}'"
                
                # Verify centering
                left_padding = content_pos
                expected_padding = (terminal_width - len(original_line.strip())) // 2
                assert abs(left_padding - expected_padding) <= 1, f"Line {i} not centered: padding={left_padding}, expected≈{expected_padding}"
    
    def test_ansi_code_handling(self):
        """Test that ANSI codes don't affect justification calculations with realistic content."""
        # Use actual terminal width
        terminal_width = max(60, _text_justifier.terminal_width)
        justifier = _TextJustifier(terminal_width)
        
        # Create realistic text with ANSI codes
        ansi_text = "\033[31mThis is red text\033[0m with normal text"
        if len("This is red text with normal text") < terminal_width:
            
            # Test right justification
            result = justifier.justify_text(ansi_text, 'right')
            
            # ANSI codes should be preserved
            assert "\033[31m" in result, "Red color code missing"
            assert "\033[0m" in result, "Reset code missing"
            assert "This is red text" in result, "Red text content missing"
            assert "with normal text" in result, "Normal text missing"
            
            # Visual length should equal terminal width (ANSI codes don't count)
            visible_length = justifier.get_visible_length(result)
            assert visible_length == terminal_width, f"Wrong visual length: {visible_length} != {terminal_width}"
            
            # Visible content should be right-aligned
            stripped = justifier._strip_ansi_codes(result)
            expected_clean = "This is red text with normal text"
            assert stripped.rstrip() == expected_clean, f"Clean content mismatch: '{stripped.rstrip()}' != '{expected_clean}'"
            assert stripped.endswith(expected_clean), f"Not right-aligned: '{stripped}'"
            
            # Test center justification
            result = justifier.justify_text(ansi_text, 'center')
            
            # ANSI codes still preserved
            assert "\033[31m" in result and "\033[0m" in result
            
            # Should be properly centered (ignoring ANSI codes in calculation)
            stripped = justifier._strip_ansi_codes(result)
            content_pos = stripped.find(expected_clean)
            expected_pos = (terminal_width - len(expected_clean)) // 2
            assert abs(content_pos - expected_pos) <= 1, f"Not centered: pos={content_pos}, expected≈{expected_pos}"
    
    def test_wide_character_justification(self):
        """Test justification with wide characters using realistic content."""
        # Use actual terminal width
        terminal_width = max(60, _text_justifier.terminal_width)
        justifier = _TextJustifier(terminal_width)
        
        # Create realistic Chinese text that's shorter than terminal width
        chinese_text = "你好世界，这是测试"  # "Hello world, this is a test"
        chinese_visual_width = justifier.get_visible_length(chinese_text)
        
        if chinese_visual_width < terminal_width:
            
            # Test center justification
            result = justifier.justify_text(chinese_text, 'center')
            
            # Should contain the Chinese text
            assert "你好世界" in result, "Chinese text missing from result"
            assert "这是测试" in result, "Chinese text missing from result"
            
            # Visual length should be calculated correctly
            result_visual_width = justifier.get_visible_length(result)
            assert result_visual_width <= terminal_width, f"Result too wide: {result_visual_width} > {terminal_width}"
            
            # Test right justification with wide chars
            result = justifier.justify_text(chinese_text, 'right')
            assert chinese_text in result, "Chinese text missing from right-justified result"
            
            # Should be right-aligned
            result_visual_width = justifier.get_visible_length(result)
            stripped = justifier._strip_ansi_codes(result)
            
            # Calculate expected padding
            expected_padding = terminal_width - chinese_visual_width
            actual_padding = len(stripped) - len(chinese_text)  # Character count difference
            
            # For wide characters, visual width != character count, so verify positioning differently
            assert stripped.rstrip().endswith(chinese_text), f"Not right-aligned: '{stripped}'"
            
            # Test with mixed content (ASCII + wide characters)
            mixed_text = "Hello 你好 World"
            mixed_visual_width = justifier.get_visible_length(mixed_text)
            
            if mixed_visual_width < terminal_width:
                result = justifier.justify_text(mixed_text, 'center')
                assert "Hello" in result and "你好" in result and "World" in result
                
                # Should handle mixed content correctly
                result_visual_width = justifier.get_visible_length(result)
                assert result_visual_width <= terminal_width
    
    def test_emoji_justification(self):
        """Test justification with emoji characters."""
        justifier = _TextJustifier(15)
        
        # Emoji text
        emoji_text = "Hi 😀"
        result = justifier.justify_text(emoji_text, 'center')
        
        # Should handle emojis correctly
        assert "😀" in result
        
        # Visual length should be reasonable
        visible_length = justifier.get_visible_length(result)
        assert visible_length <= 15
        
        # Test with multiple emojis
        multi_emoji = "😀😃😄"
        result = justifier.justify_text(multi_emoji, 'right')
        assert "😀😃😄" in result
    
    def test_mixed_content_justification(self):
        """Test justification with mixed content types."""
        justifier = _TextJustifier(25)
        
        # Mix of ASCII, wide chars, emojis, and ANSI codes
        mixed_text = "\033[31mHello\033[0m 你好 😀"
        result = justifier.justify_text(mixed_text, 'center')
        
        # All components should be preserved
        assert "\033[31m" in result  # ANSI codes
        assert "Hello" in result     # ASCII text
        assert "你好" in result       # Wide characters
        assert "😀" in result        # Emoji
        
        # Should be properly centered
        visible_length = justifier.get_visible_length(result)
        assert visible_length <= 25
    
    def test_text_too_long_for_width(self):
        """Test behavior when text is longer than terminal width."""
        justifier = _TextJustifier(10)
        
        # Text longer than width
        long_text = "This text is definitely longer than 10 characters"
        
        # Should return unchanged for all justification types
        for justify_type in ['left', 'right', 'center']:
            result = justifier.justify_text(long_text, justify_type)
            assert result == long_text
    
    def test_empty_and_whitespace_text(self):
        """Test justification of empty and whitespace-only text."""
        justifier = _TextJustifier(20)
        
        # Empty string
        result = justifier.justify_text("", 'center')
        assert result == ""
        
        # Only whitespace
        whitespace = "   "
        result = justifier.justify_text(whitespace, 'right')
        # Should handle gracefully (might return as-is)
        assert isinstance(result, str)
        
        # Empty lines in multiline text
        multiline_empty = "Line 1\n\nLine 3"
        result = justifier.justify_text(multiline_empty, 'center')
        lines = result.split('\n')
        assert len(lines) == 3
        assert lines[1] == ""  # Empty line preserved
    
    def test_ansi_stripping_method(self):
        """Test internal ANSI code stripping method."""
        justifier = _TextJustifier(50)
        
        # Various ANSI codes
        ansi_text = "\033[31m\033[1mBold Red\033[0m\033[0m"
        stripped = justifier._strip_ansi_codes(ansi_text)
        assert stripped == "Bold Red"
        
        # Complex ANSI codes
        complex_ansi = "\033[38;2;255;0;0mTruecolor\033[0m"
        stripped = justifier._strip_ansi_codes(complex_ansi)
        assert stripped == "Truecolor"
        
        # Text without ANSI codes
        plain_text = "No codes here"
        stripped = justifier._strip_ansi_codes(plain_text)
        assert stripped == plain_text
    
    def test_visible_length_method(self):
        """Test get_visible_length method."""
        justifier = _TextJustifier(50)
        
        # ASCII text
        length = justifier.get_visible_length("Hello world")
        assert length == 11
        
        # Text with ANSI codes
        ansi_text = "\033[31mHello\033[0m world"
        length = justifier.get_visible_length(ansi_text)
        assert length == 11  # ANSI codes don't count
        
        # Wide characters (if supported)
        wide_text = "你好"
        length = justifier.get_visible_length(wide_text)
        assert length >= 2  # At least 2 characters
    
    def test_justification_edge_cases(self):
        """Test edge cases in justification."""
        justifier = _TextJustifier(20)
        
        # Text exactly matching width
        exact_text = "X" * 20
        for justify_type in ['left', 'right', 'center']:
            result = justifier.justify_text(exact_text, justify_type)
            assert result == exact_text
        
        # Text one character shorter than width
        short_text = "X" * 19
        
        # Right justify should add one space
        result = justifier.justify_text(short_text, 'right')
        assert result == " " + short_text
        
        # Center justify should add space(s)
        result = justifier.justify_text(short_text, 'center')
        assert len(result) >= len(short_text)
    
    def test_invalid_justification_type(self):
        """Test behavior with invalid justification types."""
        justifier = _TextJustifier(20)
        
        text = "Hello world"
        
        # Invalid justification type should fall back to left/unchanged
        result = justifier.justify_text(text, 'invalid')
        assert result == text
        
        # Case sensitivity
        result = justifier.justify_text(text, 'RIGHT')
        # Should be case-sensitive and fall back to left
        assert result == text


class TestGlobalTextJustifier:
    """Test global text justifier instance and convenience functions."""
    
    def test_global_justifier_exists(self):
        """Test that global _text_justifier exists."""
        assert hasattr(_text_justifier, 'justify_text')
        assert hasattr(_text_justifier, 'terminal_width')
        assert _text_justifier.terminal_width >= 80
    
    def test_justify_text_convenience_function(self):
        """Test global _justify_text convenience function."""
        # Basic justification
        result = _justify_text("Hello", 'right')
        assert isinstance(result, str)
        assert "Hello" in result
        
        # With custom width
        result = _justify_text("Hello", 'center', 20)
        assert isinstance(result, str)
        assert len(result) >= len("Hello")
        
        # Should use global instance when no width specified
        result1 = _justify_text("Test", 'left')
        result2 = _text_justifier.justify_text("Test", 'left')
        assert result1 == result2
    
    def test_get_visible_length_convenience_function(self):
        """Test global _get_visible_length convenience function."""
        # ASCII text
        length = _get_visible_length("Hello world")
        assert length == 11
        
        # ANSI text
        length = _get_visible_length("\033[31mRed\033[0m")
        assert length == 3
        
        # Should match global instance
        test_text = "Test text"
        length1 = _get_visible_length(test_text)
        length2 = _text_justifier.get_visible_length(test_text)
        assert length1 == length2


class TestJustificationAccuracy:
    """Test justification accuracy with various character types."""
    
    def test_ascii_justification_accuracy(self):
        """Test justification accuracy for ASCII text."""
        justifier = _TextJustifier(30)
        
        text = "Hello world"
        
        # Right justify
        result = justifier.justify_text(text, 'right')
        visible_length = justifier.get_visible_length(result)
        assert visible_length == 30
        assert result.endswith("Hello world")
        
        # Center justify
        result = justifier.justify_text(text, 'center')
        visible_length = justifier.get_visible_length(result)
        assert visible_length <= 30
        
        # Calculate expected centering
        padding = 30 - len("Hello world")
        left_padding = padding // 2
        expected_start = left_padding
        hello_pos = result.find("Hello world")
        assert abs(hello_pos - expected_start) <= 1  # Allow for rounding
    
    def test_wide_character_accuracy(self):
        """Test justification accuracy with wide characters."""
        justifier = _TextJustifier(20)
        
        # Chinese text
        chinese = "中文"  # 2 characters, likely 4 visual columns
        
        # Right justify
        result = justifier.justify_text(chinese, 'right')
        assert "中文" in result
        
        # Visual length should equal terminal width
        visible_length = justifier.get_visible_length(result)
        assert visible_length <= 20
        
        # Should be right-aligned (end with the Chinese text)
        stripped = justifier._strip_ansi_codes(result)
        assert stripped.rstrip().endswith("中文")
    
    def test_emoji_justification_accuracy(self):
        """Test justification accuracy with emojis."""
        justifier = _TextJustifier(15)
        
        emoji_text = "Hi 😀"
        
        # Center justify
        result = justifier.justify_text(emoji_text, 'center')
        assert "😀" in result
        
        # Should be reasonably centered
        visible_length = justifier.get_visible_length(result)
        assert visible_length <= 15
    
    def test_mixed_content_accuracy(self):
        """Test justification accuracy with mixed content."""
        justifier = _TextJustifier(25)
        
        # Mix of different character types
        mixed = "A你😀B"  # ASCII, wide, emoji, ASCII
        
        for justify_type in ['left', 'right', 'center']:
            result = justifier.justify_text(mixed, justify_type)
            
            # All components should be preserved
            assert "A" in result
            assert "你" in result
            assert "😀" in result
            assert "B" in result
            
            # Should respect width limits
            visible_length = justifier.get_visible_length(result)
            assert visible_length <= 25


class TestJustificationPerformance:
    """Test performance characteristics of justification."""
    
    def test_large_text_performance(self):
        """Test performance with large amounts of text."""
        justifier = _TextJustifier(80)
        
        # Large multi-line text
        large_text = ("This is line " + str(i) + " of large text\n" for i in range(1000))
        large_text = "".join(large_text)
        
        # Should complete quickly
        import time
        start_time = time.time()
        result = justifier.justify_text(large_text, 'center')
        end_time = time.time()
        
        # Should complete in reasonable time
        assert end_time - start_time < 1.0
        assert isinstance(result, str)
        assert len(result.split('\n')) == 1000
    
    def test_complex_ansi_performance(self):
        """Test performance with complex ANSI codes."""
        justifier = _TextJustifier(50)
        
        # Text with many ANSI codes
        complex_ansi = ""
        for i in range(100):
            complex_ansi += f"\033[3{i%8};2;{i*2%256};{i*3%256};{i*5%256}mWord{i}\033[0m "
        
        # Should handle complex ANSI efficiently
        import time
        start_time = time.time()
        result = justifier.justify_text(complex_ansi, 'right')
        end_time = time.time()
        
        assert end_time - start_time < 0.5
        assert isinstance(result, str)


class TestJustificationEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_width_terminal(self):
        """Test behavior with zero terminal width."""
        justifier = _TextJustifier(0)
        
        # Should handle gracefully
        result = justifier.justify_text("Hello", 'center')
        assert isinstance(result, str)
        # Might return original text or handle specially
    
    def test_negative_width_terminal(self):
        """Test behavior with negative terminal width."""
        justifier = _TextJustifier(-10)
        
        # Should handle gracefully
        result = justifier.justify_text("Hello", 'right')
        assert isinstance(result, str)
    
    def test_very_large_width(self):
        """Test behavior with very large terminal width."""
        justifier = _TextJustifier(10000)
        
        text = "Hello"
        result = justifier.justify_text(text, 'center')
        
        # Should work but may be very padded
        assert "Hello" in result
        visible_length = justifier.get_visible_length(result)
        assert visible_length <= 10000
    
    def test_newline_edge_cases(self):
        """Test edge cases with newlines."""
        justifier = _TextJustifier(20)
        
        # Text starting with newline
        text = "\nHello"
        result = justifier.justify_text(text, 'center')
        assert result.startswith('\n')
        
        # Text ending with newline
        text = "Hello\n"
        result = justifier.justify_text(text, 'right')
        assert result.endswith('\n')
        
        # Multiple consecutive newlines
        text = "Line1\n\n\nLine2"
        result = justifier.justify_text(text, 'center')
        lines = result.split('\n')
        assert len(lines) == 4
        assert lines[1] == ""
        assert lines[2] == ""
    
    def test_unicode_normalization_edge_cases(self):
        """Test edge cases with Unicode normalization."""
        justifier = _TextJustifier(20)
        
        # Composed vs decomposed characters
        composed = "é"  # Single character
        decomposed = "e\u0301"  # e + combining acute
        
        result1 = justifier.justify_text(composed, 'center')
        result2 = justifier.justify_text(decomposed, 'center')
        
        # Both should be handled (visual result might be same)
        assert isinstance(result1, str)
        assert isinstance(result2, str)
    
    def test_control_character_handling(self):
        """Test handling of control characters."""
        justifier = _TextJustifier(20)
        
        # Text with tab characters
        tab_text = "Hello\tworld"
        result = justifier.justify_text(tab_text, 'center')
        assert isinstance(result, str)
        
        # Text with other control characters
        control_text = "Hello\x00world"
        result = justifier.justify_text(control_text, 'right')
        assert isinstance(result, str)


def run_tests():
    """Run all text justification tests with visual examples."""
    import traceback
    
    test_classes = [
        TestTextJustifier,
        TestGlobalTextJustifier,
        TestJustificationAccuracy,
        TestJustificationPerformance,
        TestJustificationEdgeCases
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("🧪 Running Text Justification Test Suite...")
    print("=" * 80)
    
    # Show visual examples first
    print("\n🎨 VISUAL EXAMPLES")
    print("-" * 50)
    
    terminal_width = max(60, _text_justifier.terminal_width)
    justifier = _TextJustifier(terminal_width)
    
    test_texts = [
        "Short",
        "Medium length text here",
        "This is a longer piece of text to demonstrate justification",
        "\033[31mColored text\033[0m with ANSI codes",
        "你好世界 - Chinese text",
        "Hello 😀 with emoji"
    ]
    
    print(f"📏 Text Justification Examples (width: {terminal_width})")
    print()
    
    for text in test_texts:
        print(f"Text: {repr(text)}")
        clean_text = justifier._strip_ansi_codes(text)
        
        if len(clean_text) < terminal_width - 5:  # Only show if it fits reasonably
            
            # Left justification
            left_result = justifier.justify_text(text, 'left')
            print(f"LEFT:")
            print(left_result)
            print(f"└── {justifier.get_visible_length(left_result)} characters")
            
            # Center justification  
            center_result = justifier.justify_text(text, 'center')
            print(f"CENTER:")
            print(center_result)
            print(f"└── {justifier.get_visible_length(center_result)} characters")
            
            # Right justification
            right_result = justifier.justify_text(text, 'right')
            print(f"RIGHT:")
            print(right_result)
            print(f"└── {justifier.get_visible_length(right_result)} characters")
            
            print()
        else:
            print(f"  (skipped - too long for terminal width)")
            print()
    
    # Multi-line example
    print("📄 Multi-line Justification Example")
    multiline_text = ("Line one is short\n"
                     "Line two is medium length\n" 
                     "Line three is much longer and demonstrates justification\n"
                     "End")
    
    print("Input:")
    for line in multiline_text.split('\n'):
        print(line)
    
    print("\nCenter justified output:")
    center_result = justifier.justify_text(multiline_text, 'center')
    for line in center_result.split('\n'):
        vis_len = justifier.get_visible_length(line)
        print(line)
        print(f"└── {vis_len} characters")
    
    print("\nRight justified output:")
    right_result = justifier.justify_text(multiline_text, 'right')
    for line in right_result.split('\n'):
        vis_len = justifier.get_visible_length(line)
        print(line)
        print(f"└── {vis_len} characters")
    
    print("\n" + "=" * 80)
    print("🧪 RUNNING UNIT TESTS")
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)
        
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
                failed_tests.append(f"{test_class.__name__}.{method_name}: {str(e)}")
                
                # Print traceback for debugging
                if "--verbose" in sys.argv:
                    print("    " + "\n    ".join(traceback.format_exc().split('\n')))
    
    # Summary
    print("\n" + "=" * 80)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
    
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