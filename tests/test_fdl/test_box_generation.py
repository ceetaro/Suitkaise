# tests/test_fdl/test_setup/test_box_generator.py
import pytest
import sys
from unittest.mock import patch, Mock

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

from setup.box_generator import _BoxGenerator, BOX_STYLES
from setup.terminal import _terminal


class TestBoxStyles:
    """Test box style definitions and fallback logic."""
    
    def test_box_styles_defined(self):
        """Test that all expected box styles are defined."""
        expected_styles = [
            'square', 'rounded', 'double', 'heavy', 
            'heavy_head', 'horizontals', 'ascii'
        ]
        
        for style in expected_styles:
            assert style in BOX_STYLES
            
        # Each style should have required characters
        required_chars = ['tl', 'tr', 'bl', 'br', 'h', 'v']
        for style, chars in BOX_STYLES.items():
            for char_type in required_chars:
                assert char_type in chars
                assert isinstance(chars[char_type], str)
                assert len(chars[char_type]) > 0
    
    def test_ascii_style_compatibility(self):
        """Test that ASCII style uses only ASCII characters."""
        ascii_chars = BOX_STYLES['ascii']
        
        for char_type, char in ascii_chars.items():
            # All characters should be ASCII (ord < 128)
            for c in char:
                assert ord(c) < 128, f"Non-ASCII character in ascii style: {c}"
    
    def test_unicode_styles_use_unicode(self):
        """Test that Unicode styles use Unicode box drawing characters."""
        unicode_styles = ['square', 'rounded', 'double', 'heavy', 'heavy_head']
        
        for style in unicode_styles:
            chars = BOX_STYLES[style]
            # At least some characters should be Unicode (ord >= 128)
            has_unicode = any(ord(c) >= 128 for char in chars.values() for c in char)
            assert has_unicode, f"Style {style} should use Unicode characters"


class TestBoxGenerator:
    """Test the internal _BoxGenerator class."""
    
    def test_initialization_default(self):
        """Test _BoxGenerator initialization with defaults."""
        generator = _BoxGenerator()
        
        assert generator.style == 'square'
        assert generator.title is None
        assert generator.color is None
        assert generator.background is None
        assert generator.justify == 'left'
        assert generator.terminal_width >= 80
        assert generator.actual_style in BOX_STYLES
        assert hasattr(generator, 'chars')
        assert hasattr(generator, 'max_content_width')
    
    def test_initialization_custom(self):
        """Test _BoxGenerator initialization with custom parameters."""
        generator = _BoxGenerator(
            style='rounded',
            title='Test Title',
            color='red',
            background='blue',
            justify='center',
            terminal_width=120
        )
        
        assert generator.style == 'rounded'
        assert generator.title == 'Test Title'
        assert generator.color == 'red'
        assert generator.background == 'blue'
        assert generator.justify == 'center'
        assert generator.terminal_width == 120
    
    @patch('setup.box_generator._supports_box_drawing')
    def test_unicode_fallback_logic(self, mock_supports_unicode):
        """Test fallback to ASCII when Unicode not supported."""
        # Mock Unicode not supported
        mock_supports_unicode.return_value = False
        
        generator = _BoxGenerator(style='rounded')
        
        # Should fall back to ASCII
        assert generator.actual_style == 'ascii'
        assert generator.chars == BOX_STYLES['ascii']
    
    @patch('setup.box_generator._supports_box_drawing')
    def test_unicode_style_when_supported(self, mock_supports_unicode):
        """Test Unicode styles when Unicode is supported."""
        # Mock Unicode supported
        mock_supports_unicode.return_value = True
        
        generator = _BoxGenerator(style='rounded')
        
        # Should use requested Unicode style
        assert generator.actual_style == 'rounded'
        assert generator.chars == BOX_STYLES['rounded']
    
    def test_invalid_style_fallback(self):
        """Test fallback for invalid box styles."""
        with patch('setup.box_generator._supports_box_drawing', return_value=True):
            generator = _BoxGenerator(style='invalid_style')
            
            # Should fall back to square
            assert generator.actual_style == 'square'
        
        with patch('setup.box_generator._supports_box_drawing', return_value=False):
            generator = _BoxGenerator(style='invalid_style')
            
            # Should fall back to ASCII
            assert generator.actual_style == 'ascii'
    
    def test_box_width_calculation(self):
        """Test box width calculation."""
        generator = _BoxGenerator(terminal_width=100)
        
        # Simple content
        content_lines = ["Hello", "World"]
        width = generator._calculate_box_width(content_lines)
        
        # Width should accommodate content plus padding/borders
        assert width >= max(len(line) for line in content_lines) + 4
        assert width <= 100  # Terminal width limit
        assert width >= generator.min_box_width
    
    def test_title_width_consideration(self):
        """Test that title width affects box width calculation."""
        generator = _BoxGenerator(title="Very Long Title Here")
        
        content_lines = ["Hi"]
        width = generator._calculate_box_width(content_lines)
        
        # Width should accommodate title
        title_width = len("Very Long Title Here") + 4  # " Title " format
        assert width >= title_width + 4  # Plus borders


class TestBoxGeneration:
    """Test box generation functionality."""
    
    def test_basic_box_generation(self):
        """Test basic box generation."""
        generator = _BoxGenerator(style='ascii', terminal_width=30)
        
        content = "Hello world"
        result = generator.generate_box(content)
        
        # Should return dictionary with all formats
        assert isinstance(result, dict)
        assert 'terminal' in result
        assert 'plain' in result
        assert 'markdown' in result
        assert 'html' in result
        
        # Terminal output should contain box characters
        terminal_output = result['terminal']
        assert '+' in terminal_output  # ASCII corners
        assert '-' in terminal_output  # ASCII horizontal
        assert '|' in terminal_output  # ASCII vertical
        assert 'Hello world' in terminal_output
    
    def test_box_with_title(self):
        """Test box generation with title."""
        generator = _BoxGenerator(
            style='ascii', 
            title='Test Title',
            terminal_width=40
        )
        
        content = "Content here"
        result = generator.generate_box(content)
        
        terminal_output = result['terminal']
        
        # Title should be in the top border
        assert 'Test Title' in terminal_output
        assert 'Content here' in terminal_output
        
        # Title should be surrounded by border characters
        lines = terminal_output.split('\n')
        top_line = lines[0]
        assert 'Test Title' in top_line
        assert '-' in top_line  # ASCII horizontal around title
    
    def test_box_with_colors(self):
        """Test box generation with colors."""
        generator = _BoxGenerator(
            style='ascii',
            color='red',
            background='blue',
            terminal_width=30
        )
        
        content = "Colored box"
        result = generator.generate_box(content)
        
        terminal_output = result['terminal']
        
        # Should contain ANSI color codes
        assert '\033[' in terminal_output  # ANSI escape sequences
        assert 'Colored box' in terminal_output
        
        # Plain output should not have ANSI codes
        plain_output = result['plain']
        assert '\033[' not in plain_output
        assert 'Colored box' in plain_output
    
    def test_content_wrapping(self):
        """Test that long content is wrapped properly with realistic terminal width."""
        # Use actual terminal width
        terminal_width = max(60, _terminal.width)
        generator = _BoxGenerator(style='ascii', terminal_width=terminal_width)
        
        # Create content that's definitely longer than any reasonable box width
        long_content = ("This is a very long paragraph that contains enough text to definitely exceed "
                       "the available box content width and force text wrapping to occur across multiple lines. "
                       "We need to make sure this text is significantly longer than the typical box content "
                       "width so that we can actually test the wrapping functionality properly. This content "
                       "should wrap on most terminals and demonstrate how the box generator handles long text.")
        
        # Verify content is actually long enough to wrap
        max_content_width = generator.max_content_width
        assert len(long_content) > max_content_width, f"Test content not long enough: {len(long_content)} <= {max_content_width}"
        
        result = generator.generate_box(long_content)
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Should have multiple content lines (wrapped)
        content_lines = [line for line in lines if '|' in line and any(word in line for word in long_content.split())]
        assert len(content_lines) > 1, f"Content should wrap into multiple lines: {len(content_lines)} lines"
        
        # Each content line should fit within box width
        for i, line in enumerate(content_lines):
            # Remove border characters to check content width
            if '|' in line:
                # Extract content between borders
                parts = line.split('|')
                if len(parts) >= 3:  # Should have left border, content, right border
                    content_part = parts[1].strip() if len(parts) > 1 else ""
                    if content_part:  # Skip empty lines
                        content_width = len(content_part)
                        assert content_width <= max_content_width, f"Line {i} content too wide: {content_width} > {max_content_width}: '{content_part}'"
        
        # Verify all content is preserved
        full_box_text = terminal_output.replace('|', '').replace('+', '').replace('-', '')
        preserved_words = [word for word in long_content.split() if word in full_box_text]
        original_words = long_content.split()
        preservation_ratio = len(preserved_words) / len(original_words)
        assert preservation_ratio > 0.9, f"Too much content lost: {preservation_ratio:.2%} preserved"
    
    def test_content_centering(self):
        """Test that content is centered within box using realistic terminal width."""
        # Use actual terminal width
        terminal_width = max(60, _terminal.width)
        generator = _BoxGenerator(style='ascii', terminal_width=terminal_width)
        
        # Test with various content lengths
        test_contents = [
            "Short",
            "Medium length content",
            "This is longer content for testing centering"
        ]
        
        for content in test_contents:
            result = generator.generate_box(content)
            terminal_output = result['terminal']
            lines = terminal_output.split('\n')
            
            # Find content line
            content_line = None
            for line in lines:
                if content in line and '|' in line:
                    content_line = line
                    break
            
            assert content_line is not None, f"Content '{content}' not found in box output"
            
            # Remove borders and check centering
            if '|' in content_line:
                parts = content_line.split('|')
                if len(parts) >= 3:  # left border, content, right border
                    inner_content = parts[1]  # Content between borders
                    
                    # Find the actual content position
                    content_pos = inner_content.find(content)
                    assert content_pos >= 0, f"Content not found in inner area: '{inner_content}'"
                    
                    # Calculate padding
                    left_padding = content_pos
                    right_padding = len(inner_content) - content_pos - len(content)
                    
                    # Should be roughly centered (within 1 space for odd padding)
                    assert abs(left_padding - right_padding) <= 1, f"Content not centered: left={left_padding}, right={right_padding} in '{inner_content}'"
                    
                    # Verify content area is reasonable size
                    total_content_width = len(inner_content)
                    assert total_content_width >= len(content), f"Content area too small: {total_content_width} < {len(content)}"
    
    def test_box_justification(self):
        """Test box justification (entire box positioning)."""
        # Center justified box
        generator = _BoxGenerator(
            style='ascii',
            justify='center',
            terminal_width=50
        )
        
        content = "Small"
        result = generator.generate_box(content)
        
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Box should be centered on terminal
        if lines:
            first_line = lines[0]
            # Should have leading spaces for centering
            assert first_line.startswith(' ')
            
            # Right justified box
            generator.justify = 'right'
            result = generator.generate_box(content)
            terminal_output = result['terminal']
            lines = terminal_output.split('\n')
            
            if lines:
                first_line = lines[0]
                # Should have more leading spaces for right alignment
                right_spaces = len(first_line) - len(first_line.lstrip())
                # (Exact calculation depends on box width vs terminal width)


class TestBoxWithSpecialContent:
    """Test box generation with special content types."""
    
    def test_wide_character_content(self):
        """Test box with wide character content."""
        generator = _BoxGenerator(style='ascii', terminal_width=30)
        
        # Chinese characters
        chinese_content = "你好世界"
        result = generator.generate_box(chinese_content)
        
        terminal_output = result['terminal']
        
        # Should contain the Chinese text
        assert '你好世界' in terminal_output
        
        # Should handle wide character width correctly
        lines = terminal_output.split('\n')
        for line in lines:
            if '你好世界' in line:
                # Line should be properly formatted
                assert line.startswith('|')
                assert line.endswith('|')
    
    def test_emoji_content(self):
        """Test box with emoji content."""
        generator = _BoxGenerator(style='ascii', terminal_width=25)
        
        emoji_content = "Hello 😀 World"
        result = generator.generate_box(emoji_content)
        
        terminal_output = result['terminal']
        
        # Should contain the emoji
        assert '😀' in terminal_output
        
        # Should handle emoji width correctly
        lines = terminal_output.split('\n')
        content_lines = [line for line in lines if 'Hello' in line]
        assert len(content_lines) >= 1
    
    def test_ansi_code_content(self):
        """Test box with ANSI codes in content."""
        generator = _BoxGenerator(style='ascii', terminal_width=35)
        
        ansi_content = "\033[31mRed text\033[0m in box"
        result = generator.generate_box(ansi_content)
        
        terminal_output = result['terminal']
        
        # ANSI codes should be preserved
        assert '\033[31m' in terminal_output
        assert '\033[0m' in terminal_output
        assert 'Red text' in terminal_output
        
        # Plain output should strip ANSI codes
        plain_output = result['plain']
        assert '\033[' not in plain_output
        assert 'Red text in box' in plain_output
    
    def test_mixed_content(self):
        """Test box with mixed content types."""
        generator = _BoxGenerator(style='ascii', terminal_width=40)
        
        mixed_content = "\033[31mHello\033[0m 你好 😀 world"
        result = generator.generate_box(mixed_content)
        
        terminal_output = result['terminal']
        
        # All components should be present
        assert 'Hello' in terminal_output
        assert '你好' in terminal_output
        assert '😀' in terminal_output
        assert 'world' in terminal_output
        assert '\033[31m' in terminal_output  # ANSI codes preserved
    
    def test_empty_content(self):
        """Test box with empty content."""
        generator = _BoxGenerator(style='ascii', terminal_width=20)
        
        # Empty string
        result = generator.generate_box("")
        terminal_output = result['terminal']
        
        # Should still generate a box structure
        lines = terminal_output.split('\n')
        assert len(lines) >= 3  # Top, content, bottom
        
        # Should have proper box characters
        assert '+' in terminal_output
        assert '-' in terminal_output
        assert '|' in terminal_output
    
    def test_whitespace_only_content(self):
        """Test box with whitespace-only content."""
        generator = _BoxGenerator(style='ascii', terminal_width=25)
        
        whitespace_content = "   \t  \n  "
        result = generator.generate_box(whitespace_content)
        
        terminal_output = result['terminal']
        
        # Should handle gracefully
        assert '+' in terminal_output  # Box structure
        assert '|' in terminal_output
    
    def test_multiline_content(self):
        """Test box with multiline content."""
        generator = _BoxGenerator(style='ascii', terminal_width=30)
        
        multiline_content = "Line 1\nLine 2\nLine 3"
        result = generator.generate_box(multiline_content)
        
        terminal_output = result['terminal']
        
        # All lines should be present
        assert 'Line 1' in terminal_output
        assert 'Line 2' in terminal_output
        assert 'Line 3' in terminal_output
        
        # Should have proper box structure around all lines
        lines = terminal_output.split('\n')
        content_lines = [line for line in lines if 'Line' in line]
        assert len(content_lines) >= 3


class TestBoxOutputFormats:
    """Test different output format generation."""
    
    def test_terminal_format(self):
        """Test terminal format output."""
        generator = _BoxGenerator(
            style='ascii',
            color='red',
            background='blue',
            terminal_width=30
        )
        
        content = "Terminal test"
        result = generator.generate_box(content)
        
        terminal_output = result['terminal']
        
        # Should contain ANSI color codes
        assert '\033[' in terminal_output
        # Should contain box characters
        assert '+' in terminal_output
        assert 'Terminal test' in terminal_output
    
    def test_plain_format(self):
        """Test plain text format output."""
        generator = _BoxGenerator(
            style='ascii',
            color='red',
            background='blue',
            terminal_width=30
        )
        
        content = "Plain test"
        result = generator.generate_box(content)
        
        plain_output = result['plain']
        
        # Should NOT contain ANSI codes
        assert '\033[' not in plain_output
        # Should contain box characters
        assert '+' in plain_output
        assert 'Plain test' in plain_output
    
    def test_markdown_format(self):
        """Test markdown format output."""
        generator = _BoxGenerator(style='ascii', terminal_width=30)
        
        content = "Markdown test"
        result = generator.generate_box(content)
        
        markdown_output = result['markdown']
        
        # Should be wrapped in code block
        assert markdown_output.startswith('```')
        assert markdown_output.endswith('```')
        assert 'Markdown test' in markdown_output
        assert '+' in markdown_output  # Box characters preserved
    
    def test_html_format(self):
        """Test HTML format output."""
        generator = _BoxGenerator(
            style='ascii',
            color='red',
            background='blue',
            terminal_width=30
        )
        
        content = "HTML test"
        result = generator.generate_box(content)
        
        html_output = result['html']
        
        # Should be wrapped in <pre> tag
        assert '<pre' in html_output
        assert '</pre>' in html_output
        assert 'class="fdl-box"' in html_output
        
        # Should contain style attributes for colors
        assert 'style=' in html_output
        assert 'border-color' in html_output or 'background-color' in html_output
        
        # Should escape HTML characters
        assert 'HTML test' in html_output
        # Box characters should be HTML-escaped if needed
    
    def test_html_escaping(self):
        """Test HTML character escaping in HTML format."""
        generator = _BoxGenerator(style='ascii', terminal_width=30)
        
        # Content with HTML characters
        html_content = "<script>alert('test')</script>"
        result = generator.generate_box(html_content)
        
        html_output = result['html']
        
        # HTML characters should be escaped
        assert '&lt;script&gt;' in html_output
        assert '&lt;/script&gt;' in html_output
        assert 'alert(&#x27;test&#x27;)' in html_output or "alert('test')" not in html_output


class TestBoxEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_very_narrow_terminal(self):
        """Test box generation with very narrow terminal."""
        generator = _BoxGenerator(style='ascii', terminal_width=10)
        
        # Content that's too wide for terminal
        wide_content = "This content is definitely too wide"
        result = generator.generate_box(wide_content)
        
        terminal_output = result['terminal']
        
        # Should still generate a box (wrapped content)
        assert '+' in terminal_output
        assert 'This' in terminal_output  # At least some content
        
        # Lines should not exceed terminal width
        lines = terminal_output.split('\n')
        for line in lines:
            assert len(line) <= 10
    
    def test_very_wide_terminal(self):
        """Test box generation with very wide terminal."""
        generator = _BoxGenerator(style='ascii', terminal_width=200)
        
        content = "Small content"
        result = generator.generate_box(content)
        
        terminal_output = result['terminal']
        
        # Should still work
        assert 'Small content' in terminal_output
        assert '+' in terminal_output
    
    def test_zero_terminal_width(self):
        """Test box generation with zero terminal width."""
        generator = _BoxGenerator(style='ascii', terminal_width=0)
        
        content = "Test"
        result = generator.generate_box(content)
        
        # Should handle gracefully
        assert isinstance(result, dict)
        assert 'terminal' in result
    
    def test_extremely_long_title(self):
        """Test box with extremely long title."""
        generator = _BoxGenerator(
            style='ascii',
            title="This is an extremely long title that is much longer than the terminal width",
            terminal_width=30
        )
        
        content = "Short content"
        result = generator.generate_box(content)
        
        terminal_output = result['terminal']
        
        # Should handle long title (truncate or wrap)
        assert 'Short content' in terminal_output
        assert '+' in terminal_output  # Box structure maintained
    
    def test_title_with_special_characters(self):
        """Test box title with special characters."""
        generator = _BoxGenerator(
            style='ascii',
            title="Title with 你好 😀 & <special>",
            terminal_width=50
        )
        
        content = "Content"
        result = generator.generate_box(content)
        
        terminal_output = result['terminal']
        
        # Title content should be preserved
        assert '你好' in terminal_output
        assert '😀' in terminal_output
        assert 'special' in terminal_output
        
        # HTML output should escape special chars
        html_output = result['html']
        assert '&lt;special&gt;' in html_output or '&amp;' in html_output
    
    def test_invalid_color_handling(self):
        """Test handling of invalid colors."""
        generator = _BoxGenerator(
            style='ascii',
            color='invalid_color',
            background='also_invalid',
            terminal_width=30
        )
        
        content = "Test content"
        result = generator.generate_box(content)
        
        # Should not crash
        assert isinstance(result, dict)
        assert 'Test content' in result['terminal']
    
    def test_none_values_handling(self):
        """Test handling of None values in parameters."""
        generator = _BoxGenerator(
            style=None,
            title=None,
            color=None,
            background=None,
            justify=None,
            terminal_width=None
        )
        
        content = "Test"
        result = generator.generate_box(content)
        
        # Should handle None values gracefully
        assert isinstance(result, dict)
        assert 'Test' in result['terminal']


class TestBoxPerformance:
    """Test performance characteristics of box generation."""
    
    def test_large_content_performance(self):
        """Test performance with large amounts of content."""
        generator = _BoxGenerator(style='ascii', terminal_width=80)
        
        # Large content
        large_content = ""
        for i in range(100):
            large_content_line = f"This is line {i} with some content\n"
            large_content += large_content_line
        
        # Should complete quickly
        import time
        start_time = time.time()
        result = generator.generate_box(large_content)
        end_time = time.time()
        
        # Should complete in reasonable time
        assert end_time - start_time < 2.0
        assert isinstance(result, dict)
        assert 'line 99' in result['terminal']  # Should contain all content
    
    def test_complex_content_performance(self):
        """Test performance with complex content (ANSI, Unicode, emojis)."""
        generator = _BoxGenerator(style='ascii', terminal_width=60)
        
        # Complex content with various character types
        complex_content = ""
        for i in range(50):
            complex_content += f"\033[3{i%8}m你好{i}😀\033[0m "
        
        # Should handle complex content efficiently
        import time
        start_time = time.time()
        result = generator.generate_box(complex_content)
        end_time = time.time()
        
        assert end_time - start_time < 1.0
        assert isinstance(result, dict)
        assert '你好' in result['terminal']
        assert '😀' in result['terminal']


def run_tests():
    """Run all box generator tests with visual examples."""
    import traceback
    
    test_classes = [
        TestBoxStyles,
        TestBoxGenerator,
        TestBoxGeneration,
        TestBoxWithSpecialContent,
        TestBoxOutputFormats,
        TestBoxEdgeCases,
        TestBoxPerformance
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("🧪 Running Box Generator Test Suite...")
    print("=" * 80)
    
    # Show visual examples first
    print("\n🎨 VISUAL EXAMPLES")
    print("-" * 50)
    
    terminal_width = max(60, _terminal.width)
    
    # Example 1: Different box styles
    print("📦 Box Styles Comparison")
    
    # Determine which styles are actually available
    try:
        from setup.unicode import _supports_box_drawing
        unicode_available = _supports_box_drawing()
    except ImportError:
        unicode_available = False
    
    if unicode_available:
        styles_to_test = ['square', 'rounded', 'double', 'ascii']
        print("Unicode box drawing is supported - showing Unicode styles:")
    else:
        styles_to_test = ['ascii']
        print("Unicode box drawing not supported - showing ASCII fallback:")
    
    test_content = "Box Style Demo"
    
    for style in styles_to_test:
        print(f"\n{style.upper()} Style:")
        try:
            generator = _BoxGenerator(style=style, terminal_width=terminal_width)
            result = generator.generate_box(test_content)
            print(result['terminal'])
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Example 2: Box with title - use best available style
    print(f"\n📋 Box with Title")
    best_style = 'square' if unicode_available else 'ascii'
    generator = _BoxGenerator(
        style=best_style,
        title='Important Notice',
        terminal_width=terminal_width
    )
    result = generator.generate_box("This box has a title in the top border")
    print(result['terminal'])
    
    # Example 3: Long content wrapping - use best available style
    print(f"\n📝 Long Content Wrapping")
    long_content = ("This is a demonstration of how the box generator handles long content that "
                   "exceeds the available width. The text should be wrapped properly while "
                   "maintaining the box structure and keeping all content within the borders.")
    generator = _BoxGenerator(style=best_style, terminal_width=terminal_width)
    result = generator.generate_box(long_content)
    print(result['terminal'])
    
    # Example 4: Wide characters
    print(f"\n🌏 Wide Characters (Chinese)")
    chinese_content = "中文测试：这个盒子包含中文字符，每个字符通常占用两个字符位置的宽度。"
    result = generator.generate_box(chinese_content)
    print(result['terminal'])
    
    # Example 5: Emojis
    print(f"\n😀 Emoji Content")
    emoji_content = "Hello! 😀 This box contains emojis 🎉 and symbols ✨ that should display correctly! 🚀"
    result = generator.generate_box(emoji_content)
    print(result['terminal'])
    
    # Example 6: ANSI colors (terminal format)
    print(f"\n🎨 ANSI Color Content (Terminal Format)")
    ansi_content = "\033[31mRed text\033[0m and \033[32mgreen text\033[0m with \033[1m\033[34mbold blue\033[0m"
    result = generator.generate_box(ansi_content)
    print("Terminal format (with ANSI codes):")
    print(result['terminal'])
    print("\nPlain format (without ANSI codes):")
    print(result['plain'])
    
    # Example 7: Box with colors (if color conversion works)
    print(f"\n🌈 Colored Box Border")
    try:
        colored_generator = _BoxGenerator(
            style=best_style,
            color='red',
            background='blue',
            title='Colored Box',
            terminal_width=terminal_width
        )
        result = colored_generator.generate_box("This box should have colored borders")
        print("Terminal format:")
        print(result['terminal'])
    except Exception as e:
        print(f"❌ Colored box error: {e}")
    
    # Example 8: Different justifications
    print(f"\n📐 Box Justification Examples")
    for justify in ['left', 'center', 'right']:
        print(f"\n{justify.upper()} justified:")
        justified_generator = _BoxGenerator(
            style=best_style,
            justify=justify,
            terminal_width=terminal_width
        )
        result = justified_generator.generate_box(f"This box is {justify}-justified")
        print(result['terminal'])
    
    # Example 9: Multi-line content
    print(f"\n📄 Multi-line Content")
    multiline_content = ("Line one of content\n"
                        "Line two is longer\n"
                        "Line three\n"
                        "Final line")
    result = generator.generate_box(multiline_content)
    print(result['terminal'])
    
    # Example 10: HTML output format
    print(f"\n🌐 HTML Output Format")
    html_generator = _BoxGenerator(
        style=best_style,
        color='red',
        title='HTML Box',
        terminal_width=terminal_width
    )
    result = html_generator.generate_box("Content with <special> & characters")
    print("HTML format:")
    print(result['html'])
    
    # Example 11: Markdown output format
    print(f"\n📝 Markdown Output Format")
    result = generator.generate_box("This is markdown formatted box content")
    print("Markdown format:")
    print(result['markdown'])
    
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