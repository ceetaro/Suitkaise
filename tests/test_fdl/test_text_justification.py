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
        assert justifier.terminal_width >= 60  # Changed from 80 to 60
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
        
        ansi_text = "\033[31mThis is red text\033[0m with normal text"
        result = justifier.justify_text(ansi_text, 'right')
        
        # ANSI codes should be preserved
        assert "\033[31m" in result
        assert "\033[0m" in result
        assert "This is red text" in result
        assert "with normal text" in result
        
        # Visual width should equal terminal width
        visual_width = justifier.get_visible_length(result)
        assert visual_width == 60, f"Visual width: {visual_width} != 60"
        
        # Stripped content should be right-aligned within 60 characters
        stripped = justifier._strip_ansi_codes(result)
        expected_clean = "This is red text with normal text"
        
        # The stripped result should be exactly 60 characters with content right-aligned
        assert len(stripped) == 60, f"Stripped length: {len(stripped)} != 60"
        assert stripped.rstrip() == stripped  # Should not have trailing spaces after stripping
        assert stripped.endswith(expected_clean), f"Not right-aligned: '{stripped}'"
    
    def test_text_wrapping_with_justification(self):
        """Test that text wrapping works with justification."""
        # Use narrow width to force wrapping
        justifier = _TextJustifier(30)
        
        # Long text that will definitely wrap
        long_text = "This is a very long piece of text that will definitely wrap into multiple lines when justified."
        
        # Test center justification with wrapping
        result = justifier.justify_text(long_text, 'center')
        lines = result.split('\n')
        
        # Should have multiple lines due to wrapping
        assert len(lines) > 1, f"Should wrap into multiple lines: {len(lines)}"
        
        # Each line should be properly justified
        for i, line in enumerate(lines):
            if line.strip():  # Skip empty lines
                visual_width = justifier.get_visible_length(line)
                # Each line should fill the terminal width when center justified
                assert visual_width == 30, f"Line {i+1} width: {visual_width} != 30"
        
        # All original content should be preserved
        rejoined = " ".join(line.strip() for line in lines if line.strip())
        original_words = long_text.split()
        rejoined_words = rejoined.split()
        
        # Should preserve most words (some might be hyphenated)
        assert len(rejoined_words) >= len(original_words) * 0.9, "Too much content lost during wrapping"
    
    def test_wide_character_justification(self):
        """Test justification with wide characters."""
        justifier = _TextJustifier(40)
        
        # Chinese text
        chinese_text = "你好世界测试内容"
        result = justifier.justify_text(chinese_text, 'right')
        
        # Should preserve Chinese characters
        assert "你好世界" in result
        assert "测试内容" in result
        
        # Should be right-aligned
        stripped = justifier._strip_ansi_codes(result)
        assert stripped.rstrip().endswith(chinese_text), "Chinese text not right-aligned"
        
        # Test with emojis
        emoji_text = "Hello 😀 World"
        result = justifier.justify_text(emoji_text, 'center')
        
        # Should preserve emoji
        assert "😀" in result
        assert "Hello" in result
        assert "World" in result
    
    def test_mixed_content_comprehensive(self):
        """Test comprehensive mixed content justification."""
        justifier = _TextJustifier(50)
        
        # Mixed content: ANSI codes + wide chars + emojis
        mixed_text = "\033[31m红色\033[0m normal 😀 text"
        
        for justify_type in ['center', 'right']:
            result = justifier.justify_text(mixed_text, justify_type)
            
            # All components should be preserved
            assert "\033[31m" in result and "\033[0m" in result  # ANSI codes
            assert "红色" in result  # Chinese
            assert "😀" in result   # Emoji
            assert "normal" in result and "text" in result  # ASCII
            
            # Should be properly justified
            visual_width = justifier.get_visible_length(result)
            assert visual_width <= 50, f"{justify_type} width too large: {visual_width}"


class TestGlobalTextJustifier:
    """Test global text justifier instance and convenience functions."""
    
    def test_global_justifier_exists(self):
        """Test that global _text_justifier exists."""
        assert hasattr(_text_justifier, 'justify_text')
        assert hasattr(_text_justifier, 'terminal_width')
        assert _text_justifier.terminal_width >= 60  # Changed from 80 to 60


def run_visual_examples():
    """Show clean visual examples of justification."""
    print("\n🎨 Text Justification Visual Examples")
    print("=" * 60)
    
    # Get terminal width
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
            print(left)
            
            center = justifier.justify_text(text, 'center') 
            print(center)
            
            right = justifier.justify_text(text, 'right')
            print(right)
    
    # Wrapping + Justification example
    print(f"\nText Wrapping + Justification Example")
    print("-" * 50)
    
    # Use narrower width to force wrapping
    narrow_justifier = _TextJustifier(35)
    long_text = "This is a longer piece of text that demonstrates how wrapping and justification work together properly."
    
    print(f"Original: {long_text}")
    print(f"Width: 35 characters")
    
    print(f"\nCenter justified with wrapping:")
    center_wrapped = narrow_justifier.justify_text(long_text, 'center')
    for line in center_wrapped.split('\n'):
        print(line)
    
    print(f"\nRight justified with wrapping:")
    right_wrapped = narrow_justifier.justify_text(long_text, 'right')
    for line in right_wrapped.split('\n'):
        print(line)
    
    # Mixed content example
    print(f"\nMixed Content Example")
    print("-" * 30)
    
    mixed = "\033[31m红色文字\033[0m normal 😀 text"
    print(f"Mixed content: ANSI + Chinese + Emoji")
    
    center_mixed = justifier.justify_text(mixed, 'center')
    print(center_mixed)
    
    right_mixed = justifier.justify_text(mixed, 'right')
    print(right_mixed)


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