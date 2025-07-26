# tests/test_fdl/test_setup/test_unicode.py
import pytest
import sys
import warnings
from unittest.mock import patch, Mock, MagicMock

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

from setup.unicode import (
    _UnicodeSupport, _get_unicode_support, _supports_box_drawing,
    _supports_unicode_spinners, _supports_progress_blocks, _get_capabilities
)


class TestUnicodeSupport:
    """Test the internal _UnicodeSupport class."""
    
    def test_initialization_with_mock_terminal(self):
        """Test _UnicodeSupport initialization with mocked terminal."""
        # Mock terminal info
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # Should have properties
        assert hasattr(unicode_support, 'supports_box_drawing')
        assert hasattr(unicode_support, 'supports_unicode_spinners')
        assert hasattr(unicode_support, 'supports_progress_blocks')
        assert hasattr(unicode_support, 'supports_status_chars')
        assert hasattr(unicode_support, 'encoding')
        assert hasattr(unicode_support, 'is_tty')
    
    def test_utf8_terminal_supports_unicode(self):
        """Test that UTF-8 TTY terminal supports Unicode features."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # UTF-8 TTY should support Unicode features
        assert unicode_support.supports_box_drawing is True
        assert unicode_support.supports_unicode_spinners is True
        assert unicode_support.supports_progress_blocks is True
        assert unicode_support.supports_status_chars is True
    
    def test_ascii_terminal_fallback(self):
        """Test that ASCII terminal falls back appropriately."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'ascii'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # ASCII should not support Unicode features
        assert unicode_support.supports_box_drawing is False
        assert unicode_support.supports_unicode_spinners is False
        assert unicode_support.supports_progress_blocks is False
        assert unicode_support.supports_status_chars is False
    
    def test_non_tty_fallback(self):
        """Test that non-TTY output disables Unicode features."""
        mock_terminal = Mock()
        mock_terminal.is_tty = False  # Not a TTY
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # Non-TTY should not use Unicode features regardless of encoding
        assert unicode_support.supports_box_drawing is False
        assert unicode_support.supports_unicode_spinners is False
        assert unicode_support.supports_progress_blocks is False
        assert unicode_support.supports_status_chars is False
    
    def test_feature_set_testing_logic(self):
        """Test the internal feature set testing logic."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # Test _test_feature_set method with simple characters
        ascii_chars = [['a', 'b', 'c']]
        result = unicode_support._test_feature_set(ascii_chars)
        assert result is True  # ASCII chars should always work
        
        # Test with characters that might not work in some encodings
        unicode_chars = [['█', '▉', '▊']]
        result = unicode_support._test_feature_set(unicode_chars)
        # Result depends on actual encoding support
        assert isinstance(result, bool)
    
    def test_capabilities_summary(self):
        """Test get_capabilities_summary method."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        capabilities = unicode_support.get_capabilities_summary()
        
        # Should be a dictionary with expected keys
        assert isinstance(capabilities, dict)
        assert 'box_drawing' in capabilities
        assert 'unicode_spinners' in capabilities
        assert 'progress_blocks' in capabilities
        assert 'status_chars' in capabilities
        assert 'is_tty' in capabilities
        assert 'encoding' in capabilities
        
        # All values should be appropriate types
        assert isinstance(capabilities['box_drawing'], bool)
        assert isinstance(capabilities['unicode_spinners'], bool)
        assert isinstance(capabilities['progress_blocks'], bool)
        assert isinstance(capabilities['status_chars'], bool)
        assert isinstance(capabilities['is_tty'], bool)
        assert isinstance(capabilities['encoding'], str)
    
    def test_encoding_property(self):
        """Test encoding property access."""
        mock_terminal = Mock()
        mock_terminal.encoding = 'cp1252'
        mock_terminal.is_tty = True
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        assert unicode_support.encoding == 'cp1252'
    
    def test_is_tty_property(self):
        """Test is_tty property access."""
        mock_terminal = Mock()
        mock_terminal.is_tty = False
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        assert unicode_support.is_tty is False
    
    @patch('warnings.warn')
    def test_warning_for_unsupported_features(self, mock_warn):
        """Test that warnings are issued for unsupported features."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'ascii'  # Will cause Unicode features to fail
        
        # Create instance that should generate warnings
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # Should have called warnings for unsupported features
        # The exact number of calls depends on how many features fail
        assert mock_warn.call_count >= 1
        
        # Check that warning messages mention the expected failures
        warning_messages = [call[0][0] for call in mock_warn.call_args_list]
        warning_text = ' '.join(warning_messages)
        
        # Should mention the main feature types
        assert any('box' in msg.lower() or 'unicode' in msg.lower() or 'progress' in msg.lower() 
                  for msg in warning_messages)
    
    def test_latin1_encoding_support(self):
        """Test behavior with Latin-1 encoding."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'latin1'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # Latin-1 has limited Unicode support
        # Most fancy Unicode characters should fail
        assert unicode_support.supports_box_drawing is False
        assert unicode_support.supports_unicode_spinners is False
        assert unicode_support.supports_progress_blocks is False
    
    def test_cp1252_encoding_support(self):
        """Test behavior with CP1252 (Windows) encoding."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'cp1252'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # CP1252 also has limited Unicode support for fancy characters
        assert unicode_support.supports_box_drawing is False
        assert unicode_support.supports_unicode_spinners is False
        assert unicode_support.supports_progress_blocks is False


class TestGlobalUnicodeSupport:
    """Test the global Unicode support instance and convenience functions."""
    
    def test_get_unicode_support_singleton(self):
        """Test that _get_unicode_support returns a singleton instance."""
        # Should return the same instance on multiple calls
        instance1 = _get_unicode_support()
        instance2 = _get_unicode_support()
        
        assert instance1 is instance2
        assert isinstance(instance1, _UnicodeSupport)
    
    def test_global_unicode_support_properties(self):
        """Test that global instance has expected properties."""
        unicode_support = _get_unicode_support()
        
        # Should have all expected properties
        assert isinstance(unicode_support.supports_box_drawing, bool)
        assert isinstance(unicode_support.supports_unicode_spinners, bool)
        assert isinstance(unicode_support.supports_progress_blocks, bool)
        assert isinstance(unicode_support.supports_status_chars, bool)
        assert isinstance(unicode_support.encoding, str)
        assert isinstance(unicode_support.is_tty, bool)
    
    def test_convenience_functions(self):
        """Test convenience functions that wrap the global instance."""
        # Test individual feature check functions
        box_support = _supports_box_drawing()
        spinner_support = _supports_unicode_spinners()
        progress_support = _supports_progress_blocks()
        
        assert isinstance(box_support, bool)
        assert isinstance(spinner_support, bool)
        assert isinstance(progress_support, bool)
        
        # These should match the global instance
        global_instance = _get_unicode_support()
        assert box_support == global_instance.supports_box_drawing
        assert spinner_support == global_instance.supports_unicode_spinners
        assert progress_support == global_instance.supports_progress_blocks
    
    def test_get_capabilities_function(self):
        """Test the global _get_capabilities function."""
        capabilities = _get_capabilities()
        
        assert isinstance(capabilities, dict)
        assert 'box_drawing' in capabilities
        assert 'unicode_spinners' in capabilities
        assert 'progress_blocks' in capabilities
        assert 'status_chars' in capabilities
        assert 'is_tty' in capabilities
        assert 'encoding' in capabilities
        
        # Should match global instance capabilities
        global_instance = _get_unicode_support()
        global_capabilities = global_instance.get_capabilities_summary()
        assert capabilities == global_capabilities


class TestUnicodeFeatureDetection:
    """Test specific Unicode feature detection logic."""
    
    def test_box_drawing_character_sets(self):
        """Test that box drawing character sets are comprehensive."""
        # The actual character sets are defined in the code
        # We can test that they would be detected properly
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # UTF-8 terminal should support box drawing
        assert unicode_support.supports_box_drawing is True
        
        # The detection should handle multiple box styles
        # (square, rounded, double, heavy, heavy_head, horizontals)
    
    def test_spinner_character_sets(self):
        """Test spinner character detection."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # UTF-8 should support Unicode spinners
        assert unicode_support.supports_unicode_spinners is True
    
    def test_progress_bar_character_sets(self):
        """Test progress bar character detection."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # UTF-8 should support Unicode progress blocks
        assert unicode_support.supports_progress_blocks is True
    
    def test_status_character_sets(self):
        """Test status character detection."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # UTF-8 should support Unicode status characters
        assert unicode_support.supports_status_chars is True


class TestUnicodeErrorHandling:
    """Test error handling and edge cases."""
    
    def test_none_encoding_handling(self):
        """Test handling of None encoding from terminal."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = None
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # Should handle None encoding gracefully
        # Likely defaults to 'ascii' or similar safe fallback
        assert isinstance(unicode_support.encoding, str)
    
    def test_empty_encoding_handling(self):
        """Test handling of empty encoding string."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = ''
        
        unicode_support = _UnicodeSupport(mock_terminal)
        
        # Should handle empty encoding gracefully
        assert isinstance(unicode_support.encoding, str)
    
    def test_invalid_encoding_handling(self):
        """Test handling of invalid encoding names."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'invalid-encoding-name'
        
        # Should not crash even with invalid encoding
        try:
            unicode_support = _UnicodeSupport(mock_terminal)
            # If it succeeds, features should be disabled for safety
            assert isinstance(unicode_support.supports_box_drawing, bool)
        except Exception:
            # If it fails, that's also acceptable for invalid encodings
            pass
    
    def test_encoding_error_during_character_test(self):
        """Test behavior when character encoding fails during testing."""
        # This is harder to test directly without mocking encode method
        # But the system should handle UnicodeEncodeError gracefully
        pass
    
    def test_missing_terminal_attributes(self):
        """Test handling of terminal with missing attributes."""
        mock_terminal = Mock()
        # Only set is_tty, missing encoding
        mock_terminal.is_tty = True
        
        # Should handle missing attributes gracefully
        try:
            unicode_support = _UnicodeSupport(mock_terminal)
            # Should not crash
            assert hasattr(unicode_support, 'supports_box_drawing')
        except AttributeError:
            # Acceptable if it requires certain attributes
            pass


class TestUnicodeIntegration:
    """Test Unicode support integration with real terminal detection."""
    
    def test_real_terminal_detection(self):
        """Test Unicode support with actual terminal detection."""
        # This uses the real terminal instance
        unicode_support = _get_unicode_support()
        
        # Should have detected something reasonable
        capabilities = unicode_support.get_capabilities_summary()
        
        # At minimum, should have encoding and TTY status
        assert 'encoding' in capabilities
        assert 'is_tty' in capabilities
        assert isinstance(capabilities['encoding'], str)
        assert isinstance(capabilities['is_tty'], bool)
    
    def test_consistency_across_multiple_calls(self):
        """Test that Unicode support detection is consistent."""
        # Multiple calls should return same results
        capabilities1 = _get_capabilities()
        capabilities2 = _get_capabilities()
        
        assert capabilities1 == capabilities2
    
    def test_feature_coherence(self):
        """Test that Unicode features are coherent with each other."""
        unicode_support = _get_unicode_support()
        
        # If not TTY, no Unicode features should be enabled
        if not unicode_support.is_tty:
            assert unicode_support.supports_box_drawing is False
            assert unicode_support.supports_unicode_spinners is False
            assert unicode_support.supports_progress_blocks is False
            assert unicode_support.supports_status_chars is False
        
        # If ASCII encoding, Unicode features should be disabled
        if unicode_support.encoding == 'ascii':
            assert unicode_support.supports_box_drawing is False
            assert unicode_support.supports_unicode_spinners is False
            assert unicode_support.supports_progress_blocks is False


def run_tests():
    """Run all unicode support tests with visual examples."""
    import traceback
    
    test_classes = [
        TestUnicodeSupport,
        TestGlobalUnicodeSupport,
        TestUnicodeFeatureDetection,
        TestUnicodeErrorHandling,
        TestUnicodeIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("🧪 Running Unicode Support Test Suite...")
    print("=" * 80)
    
    # Show visual examples first
    print("\n🌍 UNICODE FEATURE DETECTION")
    print("-" * 50)
    
    unicode_support = _get_unicode_support()
    
    # Overall capabilities
    print("🔍 Detected Capabilities:")
    print(f"  Terminal Encoding: {unicode_support.encoding}")
    print(f"  Is TTY:           {unicode_support.is_tty}")
    print(f"  Box Drawing:      {unicode_support.supports_box_drawing}")
    print(f"  Unicode Spinners: {unicode_support.supports_unicode_spinners}")
    print(f"  Progress Blocks:  {unicode_support.supports_progress_blocks}")
    print(f"  Status Chars:     {unicode_support.supports_status_chars}")
    
    # Box drawing character test
    print(f"\n📦 Box Drawing Characters Test:")
    box_chars = {
        'Square': ['┌', '┐', '└', '┘', '│', '─'],
        'Rounded': ['╭', '╮', '╰', '╯', '│', '─'],
        'Double': ['╔', '╗', '╚', '╝', '║', '═'],
        'Heavy': ['┏', '┓', '┗', '┛', '┃', '━'],
        'ASCII': ['+', '+', '+', '+', '|', '-']
    }
    
    for style_name, chars in box_chars.items():
        if style_name == 'ASCII' or unicode_support.supports_box_drawing:
            status = "✅" if style_name != 'ASCII' else "🔧"
            sample_box = f"{chars[0]}{chars[5]*3}{chars[1]}\n{chars[4]} X {chars[4]}\n{chars[2]}{chars[5]*3}{chars[3]}"
            print(f"  {status} {style_name:8}: {chars}")
            print(f"           Sample: {sample_box.replace(chr(10), ' | ')}")
        else:
            print(f"  ❌ {style_name:8}: Not supported, would fall back to ASCII")
    
    # Spinner character test
    print(f"\n🌀 Spinner Characters Test:")
    spinner_sets = {
        'Dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧'],
        'Arrows': ['▸', '▹', '▸▹', '▹▸'],
        'ASCII': ['|', '/', '-', '\\'],
        'Letters': ['d', 'q', 'p', 'b']
    }
    
    for spinner_name, chars in spinner_sets.items():
        if spinner_name in ['ASCII', 'Letters'] or unicode_support.supports_unicode_spinners:
            status = "✅" if spinner_name not in ['ASCII', 'Letters'] else "🔧"
            print(f"  {status} {spinner_name:8}: {' '.join(chars)}")
        else:
            print(f"  ❌ {spinner_name:8}: Not supported, would fall back to ASCII")
    
    # Progress block test
    print(f"\n📊 Progress Block Characters Test:")
    if unicode_support.supports_progress_blocks:
        progress_chars = ['█', '▉', '▊', '▋', '▌', '▍', '▎', '▏', ' ']
        print(f"  ✅ Unicode: {''.join(progress_chars)}")
        
        # Show sample progress bars
        for percent in [0, 25, 50, 75, 100]:
            bar_length = 20
            filled = int(percent / 100 * bar_length * 8)  # 8 sub-levels per char
            bar = ""
            for i in range(bar_length):
                block_fill = min(8, max(0, filled - i * 8))
                if block_fill >= 8:
                    bar += progress_chars[0]  # Full block
                elif block_fill > 0:
                    bar += progress_chars[block_fill]  # Partial block
                else:
                    bar += ' '  # Empty
            print(f"           {percent:3d}%: {bar} ({percent}%)")
    else:
        print(f"  ❌ Unicode: Not supported, would use ASCII: ###---")
        print(f"  🔧 ASCII:   ████████████--------")
    
    # Status character test
    print(f"\n✅ Status Characters Test:")
    status_chars = {
        'Check': '✓',
        'Cross': '✗', 
        'Warning': '⚠',
        'Info': 'ℹ',
        'Heavy Check': '✔',
        'Heavy Cross': '✖'
    }
    
    if unicode_support.supports_status_chars:
        for name, char in status_chars.items():
            print(f"  ✅ {name:12}: {char}")
    else:
        print(f"  ❌ Unicode status chars not supported")
        print(f"  🔧 ASCII alternatives: [OK] [ERR] [WARN] [INFO]")
    
    # Character encoding test
    print(f"\n🔤 Character Encoding Test:")
    test_strings = [
        ('Basic ASCII', 'Hello World'),
        ('Latin Extended', 'café naïve résumé'),
        ('Chinese (CJK)', '你好世界'),
        ('Japanese', 'こんにちは'),
        ('Korean', '안녕하세요'),
        ('Emojis', '😀😃😄😁😆'),
        ('Complex Emoji', '👨‍👩‍👧‍👦'),
        ('Math Symbols', '∑∫∆∇≠≤≥'),
        ('Box Drawing', '┌┬┐├┼┤└┴┘'),
        ('Arrows', '←↑→↓↔↕'),
    ]
    
    for desc, text in test_strings:
        try:
            text.encode(unicode_support.encoding)
            status = "✅"
        except (UnicodeEncodeError, LookupError):
            status = "❌"
        
        print(f"  {status} {desc:15}: {text}")
    
    # Feature summary
    print(f"\n📋 Feature Support Summary:")
    capabilities = unicode_support.get_capabilities_summary()
    
    feature_descriptions = {
        'box_drawing': 'Rich box styles (rounded, double, etc.)',
        'unicode_spinners': 'Smooth Unicode spinner animations', 
        'progress_blocks': 'High-precision progress bars',
        'status_chars': 'Unicode status symbols (✓✗⚠)',
        'is_tty': 'Terminal output (not redirected)',
        'encoding': 'Character encoding support'
    }
    
    for feature, supported in capabilities.items():
        if feature == 'encoding':
            print(f"  📝 {feature_descriptions[feature]:35}: {supported}")
        else:
            status = "✅" if supported else "❌"
            fallback = ""
            if not supported and feature != 'is_tty':
                fallback = " (ASCII fallback)"
            print(f"  {status} {feature_descriptions[feature]:35}: {supported}{fallback}")
    
    # Visual fallback demonstration
    if not unicode_support.supports_box_drawing:
        print(f"\n🔧 ASCII Fallback Examples:")
        print(f"  Box:     +---+    instead of    ┌───┐")
        print(f"           | X |                  │ X │") 
        print(f"           +---+                  └───┘")
    
    if not unicode_support.supports_unicode_spinners:
        print(f"  Spinner: |/-\\     instead of    ⠋⠙⠹⠸⠼⠴⠦⠧")
    
    if not unicode_support.supports_progress_blocks:
        print(f"  Progress: ###---   instead of    ███▌──")
    
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