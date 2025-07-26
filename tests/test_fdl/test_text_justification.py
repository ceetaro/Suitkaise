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


def run_visual_examples():
    """Show clean visual examples of justification."""
    print("\n🎨 Text Justification Visual Examples")
    print("=" * 60)
    
    # Get terminal width for realistic examples
    try:
        terminal_width = max(60, _text_justifier.terminal_width)
    except:
        terminal_width = 60
    
    justifier = _TextJustifier(terminal_width)
    
    # Simple examples
    print(f"\nSimple Text Justification (width: {terminal_width})")
    print("-" * 50)
    
    simple_texts = ["Short", "Medium length text", "你好世界", "Hello 😀"]
    
    for text in simple_texts:
        if justifier.get_visible_length(text) < terminal_width - 5:
            print(f"\nText: {text}")
            
            left = justifier.justify_text(text, 'left')
            center = justifier.justify_text(text, 'center') 
            right = justifier.justify_text(text, 'right')
            
            print(f"Left:")
            print(left)
            print(f"Center:")
            print(center)
            print(f"Right:")
            print(right)
    
    # Narrow width examples
    print(f"\nNarrow Width Examples (width: 40)")
    print("-" * 40)
    
    narrow_justifier = _TextJustifier(40)
    narrow_texts = ["Short", "Medium text", "你好", "Hi 😀"]
    
    for text in narrow_texts:
        print(f"\nText: {text}")
        
        left = narrow_justifier.justify_text(text, 'left')
        center = narrow_justifier.justify_text(text, 'center') 
        right = narrow_justifier.justify_text(text, 'right')
        
        print(f"Left:")
        print(left)
        print(f"Center:")
        print(center)
        print(f"Right:")
        print(right)
    
    # Text Wrapping + Justification workflow example
    print(f"\n📝 Text Wrapping + Justification Workflow")
    print("-" * 50)
    
    wrapper = _TextWrapper(45)
    workflow_justifier = _TextJustifier(45)
    long_text = ("This is a longer piece of text that demonstrates the proper workflow: "
                "first we use the text wrapping module to wrap the text, then we pass "
                "the wrapped text to the justification module for alignment.")
    
    print(f"Original: {long_text}")
    print(f"Width: 45 characters")
    
    # Step 1: Wrap with text wrapping module
    print(f"\nStep 1 - Text Wrapping:")
    wrapped_lines = wrapper.wrap_text(long_text)
    wrapped_text = '\n'.join(wrapped_lines)
    for i, line in enumerate(wrapped_lines):
        print(line)
    
    # Step 2: Justify with justification module  
    print(f"\nStep 2 - Center Justified:")
    center_result = workflow_justifier.justify_text(wrapped_text, 'center')
    for line in center_result.split('\n'):
        print(line)
    
    print(f"\nStep 3 - Right Justified:")
    right_result = workflow_justifier.justify_text(wrapped_text, 'right')
    for line in right_result.split('\n'):
        print(line)
    
    # Mixed content example
    print(f"\n🌈 Mixed Content Example (width: {terminal_width})")
    print("-" * 50)
    
    mixed = "\033[31m红色文字\033[0m normal 😀 text"
    print(f"Mixed content: ANSI + Chinese + Emoji")
    print(f"Text: {mixed}")
    
    center_mixed = justifier.justify_text(mixed, 'center')
    print(f"Center:")
    print(center_mixed)
    
    right_mixed = justifier.justify_text(mixed, 'right')
    print(f"Right:")
    print(right_mixed)
    
    # ANSI code preservation
    print(f"\n🎨 ANSI Code Preservation (width: 40)")
    print("-" * 40)
    
    ansi_justifier = _TextJustifier(40)
    ansi_text = "\033[31mRed\033[0m \033[32mGreen\033[0m text"
    print(f"Text: {ansi_text}")
    
    ansi_center = ansi_justifier.justify_text(ansi_text, 'center')
    ansi_right = ansi_justifier.justify_text(ansi_text, 'right')
    
    print(f"Center:")
    print(ansi_center)
    print(f"Right:")
    print(ansi_right)
    
    # Multiline example
    print(f"\n📄 Multiline Input Example (width: 35)")
    print("-" * 35)
    
    multiline_justifier = _TextJustifier(35)
    multiline_text = "First line\nSecond line here\nThird line"
    print(f"Original multiline text:")
    for line in multiline_text.split('\n'):
        print(line)
    
    print(f"\nCenter justified:")
    multiline_center = multiline_justifier.justify_text(multiline_text, 'center')
    for line in multiline_center.split('\n'):
        print(line)
    
    print(f"\nRight justified:")
    multiline_right = multiline_justifier.justify_text(multiline_text, 'right')
    for line in multiline_right.split('\n'):
        print(line)
    
    # Wide character handling
    print(f"\n🌏 Wide Character Handling (width: 30)")
    print("-" * 30)
    
    wide_justifier = _TextJustifier(30)
    chinese_text = "中文测试文本"
    emoji_text = "Emoji test 🎉🚀✨"
    
    print(f"Chinese text: {chinese_text}")
    chinese_center = wide_justifier.justify_text(chinese_text, 'center')
    chinese_right = wide_justifier.justify_text(chinese_text, 'right')
    print(f"Center:")
    print(chinese_center)
    print(f"Right:")
    print(chinese_right)
    
    print(f"\nEmoji text: {emoji_text}")
    emoji_center = wide_justifier.justify_text(emoji_text, 'center')
    emoji_right = wide_justifier.justify_text(emoji_text, 'right')
    print(f"Center:")
    print(emoji_center)
    print(f"Right:")
    print(emoji_right)


def run_tests():
    """Run all text justification tests."""
    import traceback
    
    # Show visual examples first
    run_visual_examples()
    
    test_classes = [
        TestTextJustifier,
        TestGlobalTextJustifier,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("\n" + "=" * 60)
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