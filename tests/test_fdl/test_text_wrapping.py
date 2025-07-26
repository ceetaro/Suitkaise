# tests/test_fdl/test_setup/test_text_wrapping.py
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
        assert wrapper.width >= 80  # Should use terminal width, minimum 80
        
        # Test with custom width
        wrapper = _TextWrapper(120)
        assert wrapper.width == 120
        
        # Test patterns are compiled
        assert hasattr(wrapper, '_ansi_pattern')
        assert hasattr(wrapper, '_break_pattern')
        assert hasattr(wrapper, '_break_patterns')
    
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
                       "这个句子应该足够长，能够在大多数终端上触发换行功能，让我们能够验证换行是否正确工作。")
        
        visual_width = wrapper._get_visual_width(chinese_text)
        
        # Should be wider than string length if wcwidth is available
        if wrapper._get_visual_width("你") > 1:  # wcwidth detects wide chars
            assert visual_width > len(chinese_text), f"Wide chars not detected: visual={visual_width}, len={len(chinese_text)}"
        
        # Test wrapping with wide characters
        result = wrapper.wrap_text(chinese_text)
        
        # Should actually wrap if text is long enough
        if visual_width > terminal_width:
            assert len(result) > 1, f"Chinese text should wrap: visual_width={visual_width}, terminal_width={terminal_width}"
        
        # Each line should respect visual width limits
        for i, line in enumerate(result):
            line_width = wrapper._get_visual_width(line)
            assert line_width <= terminal_width, f"Line {i} too wide: {line_width} > {terminal_width}: '{line}'"
    
    def test_emoji_handling(self):
        """Test handling of emoji characters with realistic content."""
        # Use actual terminal width
        terminal_width = max(60, _text_wrapper.width)
        wrapper = _TextWrapper(terminal_width)
        
        # Create emoji-heavy text that's long enough to actually wrap
        emoji_text = ("Hello everyone! 😀 Today is a great day 😃 for testing emoji handling in our text wrapping system. "
                     "We have happy faces 😄, laughing faces 😁, and even complex family emojis 👨‍👩‍👧‍👦. "
                     "This text should be long enough 🤔 to actually trigger wrapping on most terminals 💻. "
                     "Let's see how our system handles these colorful characters! 🌈✨🎉🚀")
        
        visual_width = wrapper._get_visual_width(emoji_text)
        
        # Test wrapping with emojis - should actually wrap if long enough
        result = wrapper.wrap_text(emoji_text)
        
        if visual_width > terminal_width:
            assert len(result) > 1, f"Emoji text should wrap: visual_width={visual_width}, terminal_width={terminal_width}"
        
        # Each line should respect width limits
        for i, line in enumerate(result):
            line_width = wrapper._get_visual_width(line)
            assert line_width <= terminal_width, f"Line {i} too wide: {line_width} > {terminal_width}: '{line}'"
        
        # All emojis should be preserved
        full_result = "".join(result)
        test_emojis = ["😀", "😃", "😄", "😁", "👨‍👩‍👧‍👦", "🤔", "💻", "🌈", "✨", "🎉", "🚀"]
        for emoji in test_emojis:
            assert emoji in full_result, f"Emoji lost during wrapping: {emoji}"
    
    def test_combining_character_handling(self):
        """Test handling of combining characters."""
        wrapper = _TextWrapper(20)
        
        # Text with combining characters (zero-width)
        combining_text = "e\u0301"  # e with acute accent (é)
        visual_width = wrapper._get_visual_width(combining_text)
        
        # Should be 1 visual column (base char + combining char)
        if hasattr(wrapper, '_get_char_visual_width'):
            # If wcwidth available, should handle combining chars
            assert visual_width <= len(combining_text)
        
        # Test with more complex combining
        complex_combining = "a\u0300\u0301\u0302"  # a with multiple accents
        result = wrapper.wrap_text(complex_combining)
        assert len(result) >= 1
    
    def test_ansi_code_preservation(self):
        """Test that ANSI codes are preserved in output but don't affect width calculations."""
        # Use actual terminal width
        terminal_width = max(60, _text_wrapper.width)
        wrapper = _TextWrapper(terminal_width)
        
        # Create realistic text with ANSI codes that's long enough to wrap
        colored_text = ("\033[31mThis is red text\033[0m followed by normal text and then \033[32mgreen text\033[0m. "
                       "This paragraph contains multiple color changes and should be long enough to actually "
                       "trigger text wrapping on most terminals. \033[1m\033[34mThis is bold blue text\033[0m and "
                       "we need to ensure that all the ANSI escape codes are preserved during the wrapping process "
                       "while not affecting the width calculations used for determining where to break lines.")
        
        result = wrapper.wrap_text(colored_text)
        
        # ANSI codes should be preserved in final output
        full_result = "".join(result)
        ansi_codes = ["\033[31m", "\033[0m", "\033[32m", "\033[1m", "\033[34m"]
        for code in ansi_codes:
            assert code in full_result, f"ANSI code lost during wrapping: {repr(code)}"
        
        # Text content should be preserved
        assert "red text" in full_result
        assert "green text" in full_result
        assert "bold blue text" in full_result
        
        # Width calculation should ignore ANSI codes
        for i, line in enumerate(result):
            # Strip ANSI codes and check actual visual width
            clean_line = wrapper._strip_ansi_codes(line)
            visual_width = wrapper._get_visual_width(line)  # This should ignore ANSI codes
            assert visual_width <= terminal_width, f"Line {i} too wide: {visual_width} > {terminal_width}"
            # Visual width should approximately equal clean line length (for ASCII)
            if clean_line and all(ord(c) < 128 for c in clean_line):  # ASCII only
                assert abs(visual_width - len(clean_line)) <= 1, f"Visual width mismatch for line {i}"
    
    def test_smart_break_points(self):
        """Test smart break point detection with realistic content."""
        # Use actual terminal width
        terminal_width = max(60, _text_wrapper.width)
        wrapper = _TextWrapper(terminal_width)
        
        # Create text with various break opportunities that's long enough to wrap
        space_text = ("This sentence has many words separated by spaces and should demonstrate "
                     "how the text wrapping system prefers to break at word boundaries rather than "
                     "breaking words in the middle when wrapping long lines of text.")
        
        result = wrapper.wrap_text(space_text)
        if len(result) > 1:  # Only test if actually wrapped
            # Should break at spaces, not mid-word
            for line in result:
                if line.strip():  # Ignore empty lines
                    # Line shouldn't end with partial words (unless forced break)
                    if line.endswith(' '):
                        continue  # Ending with space is fine
                    # Check if line ends with a complete word from original text
                    words = space_text.split()
                    line_words = line.strip().split()
                    if line_words:
                        last_word = line_words[-1]
                        assert last_word in words, f"Line ends with partial word: '{last_word}' in line: '{line}'"
        
        # Test punctuation breaks
        punct_text = ("Here's a sentence with punctuation,semicolons;and.periods.that.should.allow.breaking/"
                     "and/slashes/and-dashes-that-create-break-opportunities:colons:everywhere!")
        # Make it long enough to actually wrap
        long_punct = punct_text * 3
        result = wrapper.wrap_text(long_punct)
        # Should successfully wrap without errors
        assert isinstance(result, list)
        assert len(result) >= 1
        
        # Test path-like content with slashes
        path_text = ("/usr/local/bin/very/long/path/that/goes/deep/into/filesystem/structure/"
                    "and/should/demonstrate/breaking/at/slash/boundaries/when/the/path/becomes/"
                    "longer/than/the/terminal/width/allows/for/proper/display")
        result = wrapper.wrap_text(path_text)
        if len(result) > 1:  # If it wrapped
            # Should be able to break at slashes
            full_result = "".join(result)
            assert path_text.replace('/', '') == full_result.replace('/', '').replace(' ', ''), "Path content altered"
    
    def test_word_preservation(self):
        """Test that words are preserved when possible."""
        wrapper = _TextWrapper(20)
        
        # Normal text should preserve words
        text = "The quick brown fox jumps"
        result = wrapper.wrap_text(text)
        
        # Check that complete words are preserved
        for line in result:
            words = line.strip().split()
            for word in words:
                # Word should not be broken unless it's too long
                if len(word) <= 20:
                    assert word in text
    
    def test_force_breaking_long_words(self):
        """Test force breaking of extremely long words with realistic scenarios."""
        # Use actual terminal width
        terminal_width = max(60, _text_wrapper.width)
        wrapper = _TextWrapper(terminal_width)
        
        # Create a word that's definitely longer than any reasonable terminal width
        very_long_word = "supercalifragilisticexpialidocious" * 5  # 170+ characters
        assert len(very_long_word) > terminal_width, f"Test word not long enough: {len(very_long_word)} <= {terminal_width}"
        
        result = wrapper.wrap_text(very_long_word)
        
        # Should be broken into multiple lines
        assert len(result) > 1, f"Long word should be force-broken: {len(very_long_word)} chars in {len(result)} lines"
        
        # Each piece should fit within width
        for i, line in enumerate(result):
            line_width = wrapper._get_visual_width(line)
            assert line_width <= terminal_width, f"Broken piece {i} too wide: {line_width} > {terminal_width}: '{line}'"
        
        # When rejoined, should reconstruct original word
        rejoined = "".join(result)
        assert rejoined == very_long_word, "Force-broken word not properly reconstructed"
        
        # Test with a realistic scenario - long URL
        long_url = ("https://example.com/very/long/path/with/many/segments/that/creates/an/extremely/"
                   "long/url/that/exceeds/terminal/width/and/needs/to/be/broken/somewhere?param1=value1"
                   "&param2=verylongvalue&param3=anotherlongvalue&param4=final")
        
        if len(long_url) > terminal_width:
            result = wrapper.wrap_text(long_url)
            assert len(result) > 1, "Long URL should be wrapped"
            
            # Should preserve URL integrity when rejoined
            rejoined = "".join(result)
            assert rejoined == long_url, "URL corrupted during force breaking"
    
    def test_newline_preservation(self):
        """Test preservation of existing newlines."""
        wrapper = _TextWrapper(50)
        
        # Text with existing newlines
        text_with_newlines = "Line 1\nLine 2\nLine 3"
        
        # With preserve_newlines=True (default)
        result = wrapper.wrap_text(text_with_newlines, preserve_newlines=True)
        assert len(result) >= 3  # At least one line per original line
        
        # With preserve_newlines=False
        result = wrapper.wrap_text(text_with_newlines, preserve_newlines=False)
        # Should treat as continuous text
    
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
    
    def test_tokenization_logic(self):
        """Test internal tokenization logic."""
        wrapper = _TextWrapper(50)
        
        # Test tokenization with mixed break points
        text = "word1, word2; word3/word4-word5"
        tokens = wrapper._tokenize_line(text)
        
        # Should include both words and separators
        assert len(tokens) > 5  # Multiple tokens
        assert "word1" in tokens
        assert "," in tokens or ", " in tokens
        assert "word2" in tokens
    
    def test_whitespace_detection(self):
        """Test whitespace detection helper."""
        wrapper = _TextWrapper(50)
        
        # Test whitespace detection
        assert wrapper._is_whitespace(" ") is True
        assert wrapper._is_whitespace("  ") is True
        assert wrapper._is_whitespace("\t") is True
        assert wrapper._is_whitespace(" \t ") is True
        
        # Non-whitespace
        assert wrapper._is_whitespace("word") is False
        assert wrapper._is_whitespace("") is False
        assert wrapper._is_whitespace("a ") is False
    
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
    
    def test_visual_width_with_mixed_content(self):
        """Test visual width calculation with mixed content."""
        wrapper = _TextWrapper(50)
        
        # Mix of ASCII, wide chars, emojis, and ANSI codes
        mixed_text = "\033[31mHello\033[0m 你好 😀 world"
        visual_width = wrapper._get_visual_width(mixed_text)
        
        # Should handle all components correctly
        assert isinstance(visual_width, int)
        assert visual_width >= 0
        
        # Visual width should be reasonable
        assert visual_width >= len("Hello  world")  # Minimum expected


class TestGlobalTextWrapper:
    """Test global text wrapper instance and convenience functions."""
    
    def test_global_wrapper_exists(self):
        """Test that global _text_wrapper exists."""
        assert hasattr(_text_wrapper, 'wrap_text')
        assert hasattr(_text_wrapper, 'width')
        assert _text_wrapper.width >= 80
    
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
        
        # Wide characters (if supported)
        width = _get_visual_width("你好")
        assert width >= 2  # At least 2 characters
    
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


class TestWcwidthIntegration:
    """Test wcwidth integration and fallback behavior."""
    
    @patch('setup.text_wrapping.wcwidth', None)
    def test_wcwidth_fallback_mode(self):
        """Test behavior when wcwidth is not available."""
        # Create wrapper without wcwidth
        wrapper = _TextWrapper(20)
        
        # Should fall back to len() for width calculation
        width = wrapper._get_visual_width("Hello")
        assert width == 5  # Simple len() fallback
        
        # Wide characters should use fallback
        width = wrapper._get_visual_width("你好")
        assert width == 2  # len() fallback, not visual width
    
    def test_wcwidth_available_behavior(self):
        """Test behavior when wcwidth is available."""
        # This test runs with real wcwidth if available
        wrapper = _TextWrapper(20)
        
        # Check if wcwidth is actually available
        try:
            import wcwidth
            wcwidth_available = True
        except ImportError:
            wcwidth_available = False
        
        if wcwidth_available:
            # Test wide character detection
            width = wrapper._get_visual_width("你")
            # Should be 2 if wcwidth detects it as wide
            assert width >= 1
            
            # Test emoji detection
            width = wrapper._get_visual_width("😀")
            assert width >= 1
    
    def test_wcwidth_none_handling(self):
        """Test handling when wcwidth returns None."""
        wrapper = _TextWrapper(20)
        
        # Some control characters return None from wcwidth
        # The wrapper should handle this gracefully
        control_char = "\x00"  # Null character
        width = wrapper._get_visual_width(control_char)
        assert width >= 0  # Should not be negative
    
    def test_mixed_wcwidth_results(self):
        """Test handling of mixed wcwidth results."""
        wrapper = _TextWrapper(30)
        
        # String with characters that might return different wcwidth values
        mixed_text = "a\x00你🔥"  # ASCII, control, wide, emoji
        width = wrapper._get_visual_width(mixed_text)
        
        # Should handle gracefully
        assert isinstance(width, int)
        assert width >= 0


class TestTextWrappingEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_very_narrow_width(self):
        """Test behavior with very narrow widths."""
        # Width of 1
        wrapper = _TextWrapper(1)
        result = wrapper.wrap_text("Hello")
        
        # Should break character by character if needed
        assert len(result) >= 5
        for line in result:
            assert wrapper._get_visual_width(line) <= 1
    
    def test_zero_width(self):
        """Test behavior with zero width."""
        wrapper = _TextWrapper(0)
        
        # Should handle gracefully (probably force to minimum)
        result = wrapper.wrap_text("Hello")
        assert isinstance(result, list)
        assert len(result) >= 1
    
    def test_negative_width(self):
        """Test behavior with negative width."""
        wrapper = _TextWrapper(-5)
        
        # Should handle gracefully
        result = wrapper.wrap_text("Hello")
        assert isinstance(result, list)
    
    def test_extremely_long_text(self):
        """Test with extremely long text."""
        wrapper = _TextWrapper(50)
        
        # Very long text
        long_text = "word " * 1000  # 5000 characters
        result = wrapper.wrap_text(long_text)
        
        # Should complete without errors
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should respect width limits
        for line in result:
            assert wrapper._get_visual_width(line) <= 50
    
    def test_only_break_characters(self):
        """Test text consisting only of break characters."""
        wrapper = _TextWrapper(20)
        
        # Only spaces
        result = wrapper.wrap_text("     ")
        assert isinstance(result, list)
        
        # Only punctuation
        result = wrapper.wrap_text(".,;:")
        assert isinstance(result, list)
        
        # Only slashes
        result = wrapper.wrap_text("////")
        assert isinstance(result, list)
    
    def test_unicode_edge_cases(self):
        """Test Unicode edge cases."""
        wrapper = _TextWrapper(20)
        
        # Surrogate pairs
        surrogate_text = "𝐀𝐁𝐂"  # Mathematical bold capitals
        result = wrapper.wrap_text(surrogate_text)
        assert isinstance(result, list)
        
        # Invalid Unicode sequences (if any)
        # Note: Python strings are usually well-formed Unicode
        
        # Very long Unicode word
        long_unicode = "😀" * 50
        result = wrapper.wrap_text(long_unicode)
        assert len(result) > 1  # Should be wrapped
    
    def test_ansi_edge_cases(self):
        """Test ANSI code edge cases."""
        wrapper = _TextWrapper(15)
        
        # Malformed ANSI codes
        malformed_ansi = "\033[Hello world"  # Missing closing
        result = wrapper.wrap_text(malformed_ansi)
        assert isinstance(result, list)
        
        # Very long ANSI codes
        long_ansi = "\033[38;2;255;255;255mText\033[0m"
        result = wrapper.wrap_text(long_ansi)
        # Should preserve ANSI codes
        full_result = "".join(result)
        assert "\033[" in full_result
        
        # Multiple nested ANSI codes
        nested_ansi = "\033[31m\033[1mBold Red\033[0m\033[0m"
        result = wrapper.wrap_text(nested_ansi)
        assert isinstance(result, list)
    
    def test_performance_with_large_text(self):
        """Test performance characteristics with large text."""
        wrapper = _TextWrapper(80)
        
        # Large text with various character types
        large_text = (
            "The quick brown fox jumps over the lazy dog. " * 100 +
            "你好世界。" * 50 +
            "😀😃😄😁😆" * 20
        )
        
        # Should complete in reasonable time
        import time
        start_time = time.time()
        result = wrapper.wrap_text(large_text)
        end_time = time.time()
        
        # Should complete quickly (less than 1 second for this size)
        assert end_time - start_time < 1.0
        assert isinstance(result, list)
        assert len(result) > 0


class TestVisualWidthAccuracy:
    """Test visual width calculation accuracy with various character types."""
    
    def test_ascii_accuracy(self):
        """Test visual width accuracy for ASCII characters."""
        wrapper = _TextWrapper(50)
        
        ascii_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        width = wrapper._get_visual_width(ascii_chars)
        assert width == len(ascii_chars)
    
    def test_latin_extended_accuracy(self):
        """Test visual width for Latin extended characters."""
        wrapper = _TextWrapper(50)
        
        # Characters with diacritics
        latin_text = "café naïve résumé"
        width = wrapper._get_visual_width(latin_text)
        # Should be same as string length for composed characters
        assert width <= len(latin_text)
    
    def test_cjk_accuracy(self):
        """Test visual width for CJK (Chinese, Japanese, Korean) characters."""
        wrapper = _TextWrapper(50)
        
        # Chinese characters
        chinese = "中文测试"
        width = wrapper._get_visual_width(chinese)
        
        # Japanese hiragana and katakana
        japanese = "ひらがなカタカナ"
        jp_width = wrapper._get_visual_width(japanese)
        
        # Korean hangul
        korean = "한글테스트"
        kr_width = wrapper._get_visual_width(korean)
        
        # All should be wider than string length if wcwidth available
        if _check_wcwidth_available():
            assert width >= len(chinese)
            assert jp_width >= len(japanese)
            assert kr_width >= len(korean)
    
    def test_emoji_width_accuracy(self):
        """Test visual width for various emoji types."""
        wrapper = _TextWrapper(50)
        
        # Basic emojis
        basic_emoji = "😀😃😄"
        width = wrapper._get_visual_width(basic_emoji)
        
        # Complex emojis (might be multiple codepoints)
        complex_emoji = "👨‍👩‍👧‍👦"  # Family emoji (ZWJ sequence)
        complex_width = wrapper._get_visual_width(complex_emoji)
        
        # Skin tone modifiers
        skin_tone = "👋🏽"  # Waving hand with skin tone
        skin_width = wrapper._get_visual_width(skin_tone)
        
        # All should have reasonable widths
        assert width >= 0
        assert complex_width >= 0
        assert skin_width >= 0


def run_tests():
    """Run all text wrapping tests with visual examples."""
    import traceback
    
    test_classes = [
        TestTextWrapper,
        TestGlobalTextWrapper, 
        TestWcwidthIntegration,
        TestTextWrappingEdgeCases,
        TestVisualWidthAccuracy
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
    
    # Example 2: Wide characters
    print(f"\n🌏 Wide Character Handling")
    chinese_text = "这是中文测试：每个汉字通常占用两个字符位置的宽度，所以文本换行必须正确计算视觉宽度。"
    print(f"Input: {chinese_text}")
    print("Output:")
    result = wrapper.wrap_text(chinese_text)
    for line in result:
        width = wrapper._get_visual_width(line)
        print(line)
        print(f"└── {width} visual characters")
    
    # Example 3: Emojis
    print(f"\n😀 Emoji Handling")
    emoji_text = "Hello! 😀 This text contains emojis 🎉 and should wrap properly 🚀 while preserving all emoji characters! ✨"
    print(f"Input: {emoji_text}")
    print("Output:")
    result = wrapper.wrap_text(emoji_text)
    for line in result:
        width = wrapper._get_visual_width(line)
        print(line)
        print(f"└── {width} characters")
    
    # Example 4: ANSI codes
    print(f"\n🎨 ANSI Code Preservation")
    ansi_text = "\033[31mThis red text\033[0m should wrap while \033[32mpreserving\033[0m all color codes \033[1m\033[34mbold blue\033[0m."
    print(f"Input: {repr(ansi_text)}")
    print("Output:")
    result = wrapper.wrap_text(ansi_text)
    for line in result:
        width = wrapper._get_visual_width(line)
        print(line)
        print(f"└── {width} visual characters")
        print(f"Raw: {repr(line)}\033[0m")  # Reset after showing raw to prevent bleed
    
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