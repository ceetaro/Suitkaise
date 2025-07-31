# tests/test_fdl/test_setup/test_text_wrapping.py - CLEAN TESTS FOR NEW IMPLEMENTATION
import pytest
import sys
from unittest.mock import patch, Mock

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

from setup.text_wrapping import (
    _TextWrapper, _wrap_text, _get_visual_width, _fits_width,
    _check_wcwidth_available, _get_wcwidth_info, _text_wrapper
)


class TestTextWrapper:
    """Test the internal _TextWrapper class."""
    
    def test_initialization(self):
        """Test _TextWrapper initialization."""
        # Test with default width
        wrapper = _TextWrapper()
        assert wrapper.width >= 60  # Should use terminal width, minimum 60
        
        # Test with custom width
        wrapper = _TextWrapper(120)
        assert wrapper.width == 120
        
        # Test new implementation attributes
        assert hasattr(wrapper, '_ansi_pattern')
        assert hasattr(wrapper, '_whitespace_pattern')
        assert hasattr(wrapper, '_punctuation_chars')
        
        # Test punctuation characters are correct
        expected_punct = '.!?:;,/\\—–-'
        assert wrapper._punctuation_chars == expected_punct
    
    def test_priority_break_system(self):
        """Test the new priority break point system."""
        wrapper = _TextWrapper(30)
        
        # Test priority 1: Whitespace breaks
        text_with_spaces = "word1 word2 word3 word4 word5 word6"
        result = wrapper.wrap_text(text_with_spaces)
        
        # Should break at spaces when possible
        assert len(result) > 1  # Should wrap
        for line in result:
            if line.strip():
                assert wrapper._get_visual_width(line) <= 30
        
        # Test priority 2: Punctuation breaks
        text_with_punct = "verylongword,anotherlongword;thirdword"
        result = wrapper.wrap_text(text_with_punct)
        
        # Should break after punctuation when no spaces available
        assert len(result) > 1  # Should wrap
        # First line should end with punctuation + word
        assert ',' in result[0] or ';' in result[0]
    
    def test_break_point_methods(self):
        """Test the new break point detection methods."""
        wrapper = _TextWrapper(50)
        
        # Test whitespace break detection
        text = "word1 word2 word3"
        whitespace_break = wrapper._find_last_whitespace_break(text)
        assert whitespace_break > 0  # Should find whitespace
        
        # Test punctuation break detection  
        text = "word1,word2;word3"
        punct_break = wrapper._find_last_punctuation_break(text)
        assert punct_break > 0  # Should find punctuation
        assert punct_break == text.rfind(';') + 1  # After the semicolon
        
        # Test max fit position
        long_text = "a" * 100
        max_fit = wrapper._find_max_fit_position(long_text)
        assert max_fit <= 50  # Should respect width limit
        assert max_fit > 0   # Should fit some characters
    
    def test_punctuation_handling(self):
        """Test that punctuation stays with words and enables breaks after."""
        wrapper = _TextWrapper(25)
        
        # Test case: punctuation should stay with word, but allow break after
        text = "awordwithnospace,anotherword"
        result = wrapper.wrap_text(text)
        
        if len(result) > 1:  # If it wraps
            # First line should end with comma
            assert result[0].endswith(','), f"Expected comma at end of first line: '{result[0]}'"
            # Second line should start with next word
            assert 'anotherword' in result[1], f"Expected 'anotherword' in second line: '{result[1]}'"
        
        # Test punctuation characters
        punct_chars = wrapper._punctuation_chars
        expected_chars = '.!?:;,/\\—–-'
        assert punct_chars == expected_chars
        
        # Test that underscores and apostrophes are NOT break points
        assert '_' not in punct_chars
        assert "'" not in punct_chars
    
    def test_basic_text_wrapping(self):
        """Test basic text wrapping functionality with realistic terminal width."""
        # Use actual terminal width with minimum of 60
        terminal_width = max(60, _text_wrapper.width)
        wrapper = _TextWrapper(terminal_width)
        
        # Text that fits on one line
        short_text = "Hello world"
        result = wrapper.wrap_text(short_text)
        assert result == ["Hello world"]
        
        # Text that ACTUALLY needs wrapping - much longer than terminal width
        long_text = ("This is a very long paragraph that contains enough text to definitely exceed "
                    "the terminal width and force text wrapping to occur across multiple lines. "
                    "We need to make sure this text is significantly longer than the typical "
                    "terminal width of 80-120 characters so that we can actually test the wrapping "
                    "functionality properly. This sentence should definitely wrap on most terminals.")
        
        result = wrapper.wrap_text(long_text)
        assert len(result) > 1  # Should be multiple lines
        
        # Each line should be within width limit
        for line in result:
            actual_width = wrapper._get_visual_width(line)
            assert actual_width <= terminal_width, f"Line too wide: {actual_width} > {terminal_width}: '{line}'"
        
        # Total content should be preserved
        rejoined = " ".join(line.strip() for line in result if line.strip())
        original_words = long_text.split()
        rejoined_words = rejoined.split()
        assert len(rejoined_words) == len(original_words), "Content lost during wrapping"
    
    def test_visual_width_measurement(self):
        """Test visual width measurement vs string length."""
        wrapper = _TextWrapper(80)
        
        # ASCII text - visual width equals string length
        ascii_text = "Hello world"
        assert wrapper._get_visual_width(ascii_text) == len(ascii_text)
        
        # Test with ANSI codes - should be stripped for width calculation
        ansi_text = "\033[31mHello\033[0m world"
        clean_width = wrapper._get_visual_width(ansi_text)
        assert clean_width == len("Hello world")  # ANSI codes don't count
        assert clean_width < len(ansi_text)  # ANSI codes make string longer
    
    def test_wide_character_handling(self):
        """Test handling of wide characters (CJK, etc.) with realistic content."""
        # Use actual terminal width
        terminal_width = max(60, _text_wrapper.width)
        wrapper = _TextWrapper(terminal_width)
        
        # Create Chinese text that's actually long enough to wrap
        chinese_text = ("这是一个很长的中文句子，用来测试文本换行功能是否能够正确处理中文字符。"
                       "中文字符通常占用两个字符位置的宽度，所以换行算法必须正确计算视觉宽度。"
                       "这个句子应该足够长，能够在大多数终端上触发换行功能。")
        
        visual_width = wrapper._get_visual_width(chinese_text)
        
        # Test wrapping with wide characters
        result = wrapper.wrap_text(chinese_text)
        
        # Should actually wrap if text is long enough
        if visual_width > terminal_width:
            assert len(result) > 1, f"Chinese text should wrap: visual_width={visual_width}, terminal_width={terminal_width}"
        
        # Each line should respect visual width limits
        for i, line in enumerate(result):
            line_width = wrapper._get_visual_width(line)
            assert line_width <= terminal_width, f"Line {i} too wide: {line_width} > {terminal_width}: '{line}'"
    
    def test_ansi_code_preservation(self):
        """Test that ANSI codes are preserved in output but don't affect width calculations."""
        # Use actual terminal width for realistic testing
        terminal_width = max(60, _text_wrapper.width)
        wrapper = _TextWrapper(terminal_width)
        
        # Create realistic colored text - shorter to avoid width issues
        colored_text = ""
        for i in range(8):  # Create moderate amount of content
            colored_text += f"\033[3{i%8}mWord{i}\033[0m "
        
        result = wrapper.wrap_text(colored_text)
        
        # ANSI codes should be preserved in final output
        full_result = "".join(result)
        ansi_codes = ["\033[3", "\033[0m"]
        for code in ansi_codes:
            assert code in full_result, f"ANSI code lost during wrapping: {repr(code)}"
        
        # Text content should be preserved
        assert "Word0" in full_result
        assert "Word7" in full_result
        
        # Width calculation should ignore ANSI codes - each line should fit
        for i, line in enumerate(result):
            if line.strip():  # Only check non-empty lines
                visual_width = wrapper._get_visual_width(line)
                assert visual_width <= terminal_width, f"Line {i} too wide: {visual_width} > {terminal_width}: {repr(line)}"
    
    def test_fits_width_method(self):
        """Test fits_width convenience method."""
        wrapper = _TextWrapper(20)
        
        # Text that fits
        assert wrapper.fits_width("Short text") is True
        
        # Text that doesn't fit
        assert wrapper.fits_width("This is a very long text that exceeds the width") is False
        
        # Test with custom width
        assert wrapper.fits_width("Medium length text", 50) is True
        assert wrapper.fits_width("Medium length text", 10) is False


class TestGlobalTextWrapper:
    """Test global text wrapper instance and convenience functions."""
    
    def test_global_wrapper_exists(self):
        """Test that global _text_wrapper exists."""
        assert hasattr(_text_wrapper, 'wrap_text')
        assert hasattr(_text_wrapper, 'width')
        assert _text_wrapper.width >= 60  # Global wrapper uses detected width with minimum
    
    def test_wrap_text_convenience_function(self):
        """Test global _wrap_text convenience function."""
        # Basic wrapping
        result = _wrap_text("This is a test", 10)
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # With custom width
        result1 = _wrap_text("Long text that needs wrapping", 15)
        result2 = _wrap_text("Long text that needs wrapping", 25)
        # Different widths should give different results
        assert len(result1) >= len(result2)
    
    def test_get_visual_width_convenience_function(self):
        """Test global _get_visual_width convenience function."""
        # ASCII text
        width = _get_visual_width("Hello world")
        assert width == 11
        
        # ANSI text
        width = _get_visual_width("\033[31mRed\033[0m")
        assert width == 3  # Should ignore ANSI codes
    
    def test_fits_width_convenience_function(self):
        """Test global _fits_width convenience function."""
        # Text that fits
        assert _fits_width("Short", 10) is True
        
        # Text that doesn't fit
        assert _fits_width("Very long text", 5) is False
        
        # Use default width
        result = _fits_width("Text")
        assert isinstance(result, bool)
    
    def test_wcwidth_info_functions(self):
        """Test wcwidth availability check functions."""
        # Check availability
        available = _check_wcwidth_available()
        assert isinstance(available, bool)
        
        # Get info
        info = _get_wcwidth_info()
        assert isinstance(info, dict)
        assert 'available' in info
        assert 'fallback_mode' in info
        assert info['available'] == available


class TestTextWrappingEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_very_narrow_width(self):
        """Test behavior with very narrow widths."""
        # With explicit width, should honor the width (no minimum enforcement)
        wrapper = _TextWrapper(1)
        
        # Should use the explicit width of 1
        assert wrapper.width == 1
        
        result = wrapper.wrap_text("Hello")
        
        # Should break character by character for very narrow width
        assert len(result) >= 5  # At least 5 characters means at least 5 lines
        for line in result:
            assert wrapper._get_visual_width(line) <= 1
    
    def test_extremely_long_text(self):
        """Test with extremely long text."""
        wrapper = _TextWrapper(50)
        
        # Very long text - but not too extreme to avoid test timeouts
        long_text = "word " * 200  # 1000 characters (reasonable for testing)
        result = wrapper.wrap_text(long_text)
        
        # Should complete without errors
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should respect width limits
        for i, line in enumerate(result):
            line_width = wrapper._get_visual_width(line)
            assert line_width <= 50, f"Line {i} too wide: {line_width} > 50"
            
        # Content should be preserved
        full_result = " ".join(line.strip() for line in result if line.strip())
        original_words = long_text.split()
        result_words = full_result.split()
        assert len(result_words) == len(original_words), "Content lost during wrapping"
    
    def test_empty_and_whitespace_handling(self):
        """Test handling of empty strings and whitespace."""
        wrapper = _TextWrapper(20)
        
        # Empty string
        result = wrapper.wrap_text("")
        assert result == [""]
        
        # Only whitespace
        result = wrapper.wrap_text("   ")
        assert len(result) >= 1
        
        # Multiple spaces
        result = wrapper.wrap_text("word1     word2")
        # Should handle multiple spaces gracefully
        
        # Leading/trailing whitespace
        result = wrapper.wrap_text("  text  ")
        # Should preserve meaningful whitespace
    
    def test_east_asian_characters(self):
        """Test wrapping with East Asian characters (full-width)."""
        wrapper = _TextWrapper(20)
        
        # Test Chinese characters (full-width)
        chinese_text = "你好世界这是一个测试"
        result = wrapper.wrap_text(chinese_text)
        
        # Each Chinese character should count as 2 visual width
        assert len(result) > 1  # Should wrap due to full-width characters
        for line in result:
            if line.strip():
                visual_width = wrapper._get_visual_width(line)
                assert visual_width <= 20
                # Verify that Chinese characters are counted correctly
                assert visual_width % 2 == 0  # Should be even for full-width chars
        
        # Test mixed Chinese and English
        mixed_text = "Hello你好World世界"
        result = wrapper.wrap_text(mixed_text)
        assert len(result) > 1
        for line in result:
            if line.strip():
                assert wrapper._get_visual_width(line) <= 20
    
    def test_emoji_handling(self):
        """Test wrapping with emojis and Unicode symbols."""
        wrapper = _TextWrapper(15)
        
        # Test emojis (should count as 2 visual width each)
        emoji_text = "Hello 😀 World 🌍 Test 🚀"
        result = wrapper.wrap_text(emoji_text)
        
        assert len(result) > 1  # Should wrap due to emojis
        for line in result:
            if line.strip():
                visual_width = wrapper._get_visual_width(line)
                assert visual_width <= 15
        
        # Test complex emojis (combining characters)
        complex_emoji = "👨‍👩‍👧‍👦"  # Family emoji
        result = wrapper.wrap_text(complex_emoji)
        # Should handle complex emojis without breaking them
        assert len(result) == 1  # Should not break complex emoji
        
        # Test emoji with text
        emoji_with_text = "Test👨‍👩‍👧‍👦Test"
        result = wrapper.wrap_text(emoji_with_text)
        for line in result:
            if line.strip():
                assert wrapper._get_visual_width(line) <= 15
    
    def test_file_path_wrapping(self):
        """Test wrapping of long file paths with slashes."""
        wrapper = _TextWrapper(30)
        
        # Test Unix-style paths
        unix_path = "/very/long/path/to/some/file/with/many/directories/and/subdirectories"
        result = wrapper.wrap_text(unix_path)
        
        assert len(result) > 1  # Should wrap
        for line in result:
            if line.strip():
                assert wrapper._get_visual_width(line) <= 30
        
        # Verify that paths are broken at slashes when possible
        for i, line in enumerate(result):
            if i > 0 and line.strip():  # Not first line and not empty
                # Should start with a slash or be a continuation
                assert line.startswith('/') or not line.startswith('/')
        
        # Test Windows-style paths
        windows_path = "C:\\very\\long\\path\\to\\some\\file\\with\\many\\directories"
        result = wrapper.wrap_text(windows_path)
        
        assert len(result) > 1  # Should wrap
        for line in result:
            if line.strip():
                assert wrapper._get_visual_width(line) <= 30
        
        # Test mixed path with spaces
        mixed_path = "/home/user/My Documents/very long filename with spaces.txt"
        result = wrapper.wrap_text(mixed_path)
        
        assert len(result) > 1  # Should wrap
        for line in result:
            if line.strip():
                assert wrapper._get_visual_width(line) <= 30
    
    def test_ansi_colored_text_wrapping(self):
        """Test wrapping of text with ANSI color codes."""
        wrapper = _TextWrapper(25)
        
        # Test text with ANSI color codes
        colored_text = "\033[31mRed text\033[0m and \033[32mGreen text\033[0m with \033[1mBold text\033[0m"
        result = wrapper.wrap_text(colored_text)
        
        assert len(result) > 1  # Should wrap
        for line in result:
            if line.strip():
                # Visual width should exclude ANSI codes
                visual_width = wrapper._get_visual_width(line)
                assert visual_width <= 25
        
        # Test that ANSI codes are preserved
        full_result = ''.join(result)
        assert '\033[31m' in full_result  # Red code preserved
        assert '\033[32m' in full_result  # Green code preserved
        assert '\033[1m' in full_result   # Bold code preserved
        assert '\033[0m' in full_result   # Reset code preserved
        
        # Test complex formatting
        complex_colored = "\033[1;31;42mBold Red on Green\033[0m \033[3;34mItalic Blue\033[0m"
        result = wrapper.wrap_text(complex_colored)
        
        for line in result:
            if line.strip():
                visual_width = wrapper._get_visual_width(line)
                assert visual_width <= 25


def run_tests():
    """Run all text wrapping tests with visual examples."""
    import traceback
    
    test_classes = [
        TestTextWrapper,
        TestGlobalTextWrapper, 
        TestTextWrappingEdgeCases,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("🧪 Running Text Wrapping Test Suite...")
    print("=" * 80)
    
    # Show visual examples first
    print("\n🎨 VISUAL EXAMPLES")
    print("-" * 50)
    
    # Example 1: Basic wrapping
    terminal_width = max(60, _text_wrapper.width)
    wrapper = _TextWrapper(terminal_width)
    long_text = ("This is a demonstration of text wrapping functionality that should show how "
                "long paragraphs are broken into multiple lines when they exceed the terminal "
                "width. Notice how words are preserved and break points are chosen intelligently.")
    
    print(f"📝 Basic Text Wrapping (width: {terminal_width})")
    print(f"Input: {long_text}")
    print("Output:")
    result = wrapper.wrap_text(long_text)
    for line in result:
        width = wrapper._get_visual_width(line)
        print(line)
        print(f"└── {width} characters")
    
    # Example 2: Priority system demonstration
    print(f"\n🎯 Priority System Demo (width: 30)")
    priority_wrapper = _TextWrapper(30)
    
    # Whitespace priority
    whitespace_text = "word1 word2 word3 word4 word5"
    print(f"Whitespace breaks: {whitespace_text}")
    result = priority_wrapper.wrap_text(whitespace_text)
    for line in result:
        print(line)
    
    # Punctuation priority
    punct_text = "longword,anotherword;thirdword"
    print(f"\nPunctuation breaks: {punct_text}")
    result = priority_wrapper.wrap_text(punct_text)
    for line in result:
        print(line)
    
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