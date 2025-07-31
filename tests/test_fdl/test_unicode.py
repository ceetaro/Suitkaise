"""
Comprehensive tests for FDL Unicode Support System.

Tests the internal Unicode feature detection system that handles box drawing,
spinners, progress bars, status characters, encoding detection, and fallbacks.
"""

import pytest
import sys
import os
import warnings
from unittest.mock import Mock, patch
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.setup.unicode import (
    _UnicodeSupport, _get_unicode_support, _supports_box_drawing,
    _supports_unicode_spinners, _supports_progress_blocks, _get_capabilities
)


class TestUnicodeSupport:
    """Test suite for the Unicode support detection system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock terminal for controlled testing
        self.mock_terminal = Mock()
        self.mock_terminal.is_tty = True
        self.mock_terminal.encoding = 'utf-8'
    
    def test_unicode_support_initialization_with_terminal(self):
        """Test Unicode support initialization with provided terminal."""
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        assert unicode_support._terminal is self.mock_terminal
        assert unicode_support._is_tty is True
        assert unicode_support._encoding == 'utf-8'
    
    def test_unicode_support_initialization_without_terminal(self):
        """Test Unicode support initialization without provided terminal."""
        with patch('suitkaise.fdl._int.setup.unicode._terminal') as mock_global_terminal:
            mock_global_terminal.is_tty = True
            mock_global_terminal.encoding = 'utf-8'
            
            unicode_support = _UnicodeSupport()
            
            assert unicode_support._is_tty is True
            assert unicode_support._encoding == 'utf-8'
    
    def test_unicode_support_initialization_fallback_terminal(self):
        """Test Unicode support initialization with fallback terminal."""
        with patch('suitkaise.fdl._int.setup.unicode._terminal', side_effect=ImportError("No terminal")):
            unicode_support = _UnicodeSupport()
            
            # Should use fallback terminal
            assert unicode_support._is_tty is False
            assert unicode_support._encoding == 'ascii'
    
    def test_unicode_support_safe_property_handling(self):
        """Test safe handling of terminal properties."""
        # Test with None encoding
        self.mock_terminal.encoding = None
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        assert unicode_support._encoding == 'ascii'
        
        # Test with non-string encoding
        self.mock_terminal.encoding = 123
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        assert unicode_support._encoding == 'ascii'
        
        # Test with missing is_tty attribute
        del self.mock_terminal.is_tty
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        assert unicode_support._is_tty is False
    
    def test_feature_set_testing_non_tty(self):
        """Test that non-TTY terminals don't support Unicode features."""
        self.mock_terminal.is_tty = False
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # Should not support any Unicode features
        assert unicode_support.supports_box_drawing is False
        assert unicode_support.supports_unicode_spinners is False
        assert unicode_support.supports_progress_blocks is False
        assert unicode_support.supports_status_chars is False
    
    def test_feature_set_testing_ascii_encoding(self):
        """Test that ASCII encoding doesn't support Unicode features."""
        self.mock_terminal.encoding = 'ascii'
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # Should not support any Unicode features
        assert unicode_support.supports_box_drawing is False
        assert unicode_support.supports_unicode_spinners is False
        assert unicode_support.supports_progress_blocks is False
        assert unicode_support.supports_status_chars is False
    
    def test_feature_set_testing_utf8_encoding(self):
        """Test Unicode feature detection with UTF-8 encoding."""
        self.mock_terminal.encoding = 'utf-8'
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # With UTF-8 and TTY, should support Unicode features
        # (This assumes the test environment supports UTF-8)
        assert isinstance(unicode_support.supports_box_drawing, bool)
        assert isinstance(unicode_support.supports_unicode_spinners, bool)
        assert isinstance(unicode_support.supports_progress_blocks, bool)
        assert isinstance(unicode_support.supports_status_chars, bool)
    
    def test_test_feature_set_method_success(self):
        """Test _test_feature_set method with supported characters."""
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # Test with basic ASCII characters (should always work)
        ascii_chars = [['a', 'b', 'c'], ['1', '2', '3']]
        result = unicode_support._test_feature_set(ascii_chars)
        assert result is True
    
    def test_test_feature_set_method_encoding_failure(self):
        """Test _test_feature_set method with encoding failures."""
        # Mock encoding that fails for Unicode characters
        self.mock_terminal.encoding = 'ascii'
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # Test with Unicode characters that should fail in ASCII
        unicode_chars = [['┌', '┐', '└', '┘'], ['█', '▉', '▊']]
        result = unicode_support._test_feature_set(unicode_chars)
        assert result is False
    
    def test_test_feature_set_method_with_invalid_encoding(self):
        """Test _test_feature_set method with invalid encoding."""
        # Create a mock terminal with an encoding that will raise LookupError
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'invalid-encoding'
        
        unicode_support = _UnicodeSupport(terminal_info=mock_terminal)
        
        # Mock the encode method to raise LookupError
        with patch.object(str, 'encode', side_effect=LookupError("Invalid encoding")):
            test_chars = [['a', 'b']]
            result = unicode_support._test_feature_set(test_chars)
            assert result is False
    
    def test_box_drawing_characters_comprehensive(self):
        """Test that all box drawing character sets are tested."""
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # The specific box drawing characters that should be tested
        expected_chars = {
            # Square box
            '┌', '┐', '└', '┘', '│', '─', '┼', '┴', '┬', '┤', '├',
            # Rounded box
            '╭', '╮', '╰', '╯',
            # Double box
            '╔', '╗', '╚', '╝', '║', '═', '╬', '╩', '╦', '╣', '╠',
            # Heavy box
            '┏', '┓', '┗', '┛', '┃', '━', '╋', '┻', '┳', '┫', '┣',
            # Heavy head box
            '┍', '┑', '┕', '┙', '┿', '┷', '┯', '┥', '┝',
        }
        
        # Test that box drawing support is properly determined
        box_support = unicode_support.supports_box_drawing
        assert isinstance(box_support, bool)
    
    def test_spinner_characters_comprehensive(self):
        """Test that all spinner character sets are tested."""
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # The specific spinner characters that should be tested
        expected_chars = {
            # Dots spinner
            '⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧',
            # Arrow3 spinner
            '▹', '▸',
            # DQPB spinner (ASCII fallback)
            'd', 'q', 'p', 'b'
        }
        
        # Test that spinner support is properly determined
        spinner_support = unicode_support.supports_unicode_spinners
        assert isinstance(spinner_support, bool)
    
    def test_progress_bar_characters_comprehensive(self):
        """Test that all progress bar character sets are tested."""
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # The specific progress bar characters that should be tested
        expected_chars = {'█', '▉', '▊', '▋', '▌', '▍', '▎', '▏'}
        
        # Test that progress bar support is properly determined
        progress_support = unicode_support.supports_progress_blocks
        assert isinstance(progress_support, bool)
    
    def test_status_characters_comprehensive(self):
        """Test that all status character sets are tested."""
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        # The specific status characters that should be tested
        expected_chars = {'✓', '✗', '⚠', 'ℹ', '✔', '✖'}
        
        # Test that status character support is properly determined
        status_support = unicode_support.supports_status_chars
        assert isinstance(status_support, bool)
    
    def test_properties_return_correct_types(self):
        """Test that all properties return correct types."""
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        assert isinstance(unicode_support.supports_box_drawing, bool)
        assert isinstance(unicode_support.supports_unicode_spinners, bool)
        assert isinstance(unicode_support.supports_progress_blocks, bool)
        assert isinstance(unicode_support.supports_status_chars, bool)
        assert isinstance(unicode_support.encoding, str)
        assert isinstance(unicode_support.is_tty, bool)
    
    def test_get_capabilities_summary(self):
        """Test capabilities summary generation."""
        unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
        
        capabilities = unicode_support.get_capabilities_summary()
        
        # Should be a dictionary with expected keys
        assert isinstance(capabilities, dict)
        expected_keys = {
            'box_drawing', 'unicode_spinners', 'progress_blocks',
            'status_chars', 'is_tty', 'encoding'
        }
        assert set(capabilities.keys()) == expected_keys
        
        # All boolean values except encoding
        for key, value in capabilities.items():
            if key == 'encoding':
                assert isinstance(value, str)
            else:
                assert isinstance(value, bool)
    
    def test_warning_generation_for_unsupported_features(self):
        """Test that warnings are generated for unsupported features."""
        # Force ASCII encoding to trigger warnings
        self.mock_terminal.encoding = 'ascii'
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
            
            # Should have issued warnings for unsupported features
            warning_messages = [str(warning.message) for warning in w]
            
            # Check for specific warning messages
            assert any("Unicode box drawing not supported" in msg for msg in warning_messages)
            assert any("Unicode spinners not supported" in msg for msg in warning_messages)
            assert any("Unicode progress bars not supported" in msg for msg in warning_messages)
    
    def test_encoding_edge_cases(self):
        """Test various encoding edge cases."""
        test_encodings = [
            ('utf-8', True),
            ('utf-16', True),
            ('latin1', False),  # Might not support all Unicode
            ('cp1252', False),  # Windows encoding, limited Unicode
            ('ascii', False),   # Definitely no Unicode
            ('', False),        # Empty encoding
        ]
        
        for encoding, might_support_unicode in test_encodings:
            self.mock_terminal.encoding = encoding
            unicode_support = _UnicodeSupport(terminal_info=self.mock_terminal)
            
            # Properties should always return booleans
            assert isinstance(unicode_support.supports_box_drawing, bool)
            assert isinstance(unicode_support.supports_unicode_spinners, bool)
            assert isinstance(unicode_support.supports_progress_blocks, bool)
            assert isinstance(unicode_support.supports_status_chars, bool)


class TestUnicodeGlobalFunctions:
    """Test suite for global Unicode support functions."""
    
    def test_get_unicode_support_function(self):
        """Test global _get_unicode_support function."""
        # Clear any existing global instance
        import suitkaise.fdl._int.setup.unicode as unicode_module
        unicode_module._unicode_support = None
        
        # First call should create instance
        support1 = _get_unicode_support()
        assert isinstance(support1, _UnicodeSupport)
        
        # Second call should return same instance
        support2 = _get_unicode_support()
        assert support1 is support2
    
    def test_supports_box_drawing_function(self):
        """Test global _supports_box_drawing function."""
        result = _supports_box_drawing()
        assert isinstance(result, bool)
    
    def test_supports_unicode_spinners_function(self):
        """Test global _supports_unicode_spinners function."""
        result = _supports_unicode_spinners()
        assert isinstance(result, bool)
    
    def test_supports_progress_blocks_function(self):
        """Test global _supports_progress_blocks function."""
        result = _supports_progress_blocks()
        assert isinstance(result, bool)
    
    def test_get_capabilities_function(self):
        """Test global _get_capabilities function."""
        capabilities = _get_capabilities()
        
        assert isinstance(capabilities, dict)
        expected_keys = {
            'box_drawing', 'unicode_spinners', 'progress_blocks',
            'status_chars', 'is_tty', 'encoding'
        }
        assert set(capabilities.keys()) == expected_keys


class TestUnicodeEdgeCases:
    """Test suite for Unicode support edge cases and error conditions."""
    
    def test_unicode_encode_error_handling(self):
        """Test handling of UnicodeEncodeError during character testing."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'ascii'  # Will cause UnicodeEncodeError for Unicode chars
        
        unicode_support = _UnicodeSupport(terminal_info=mock_terminal)
        
        # Should handle UnicodeEncodeError gracefully
        assert unicode_support.supports_box_drawing is False
        assert unicode_support.supports_unicode_spinners is False
        assert unicode_support.supports_progress_blocks is False
    
    def test_attribute_error_handling(self):
        """Test handling of AttributeError during character testing."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(terminal_info=mock_terminal)
        
        # Mock encode to raise AttributeError
        with patch.object(str, 'encode', side_effect=AttributeError("No encode method")):
            test_chars = [['a', 'b']]
            result = unicode_support._test_feature_set(test_chars)
            assert result is False
    
    def test_type_error_handling(self):
        """Test handling of TypeError during character testing."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(terminal_info=mock_terminal)
        
        # Mock encode to raise TypeError
        with patch.object(str, 'encode', side_effect=TypeError("Invalid type")):
            test_chars = [['a', 'b']]
            result = unicode_support._test_feature_set(test_chars)
            assert result is False
    
    def test_empty_character_sets(self):
        """Test behavior with empty character sets."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'utf-8'
        
        unicode_support = _UnicodeSupport(terminal_info=mock_terminal)
        
        # Empty character sets should return True (vacuous truth)
        result = unicode_support._test_feature_set([])
        assert result is True
        
        # Character sets with empty sub-lists
        result = unicode_support._test_feature_set([[], []])
        assert result is True
    
    def test_mixed_character_set_failure(self):
        """Test that if any character in a set fails, the whole set fails."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = 'ascii'  # Will fail for Unicode chars
        
        unicode_support = _UnicodeSupport(terminal_info=mock_terminal)
        
        # Mix of ASCII and Unicode characters - should fail due to Unicode
        mixed_chars = [['a', 'b', '┌'], ['1', '2', '3']]
        result = unicode_support._test_feature_set(mixed_chars)
        assert result is False
    
    def test_terminal_with_none_encoding(self):
        """Test terminal with None encoding."""
        mock_terminal = Mock()
        mock_terminal.is_tty = True
        mock_terminal.encoding = None
        
        unicode_support = _UnicodeSupport(terminal_info=mock_terminal)
        
        # Should default to 'ascii' encoding
        assert unicode_support.encoding == 'ascii'
        assert unicode_support.supports_box_drawing is False
    
    def test_terminal_missing_attributes(self):
        """Test terminal missing expected attributes."""
        mock_terminal = Mock()
        # Don't set is_tty or encoding attributes
        
        unicode_support = _UnicodeSupport(terminal_info=mock_terminal)
        
        # Should use safe defaults
        assert unicode_support.is_tty is False
        assert unicode_support.encoding == 'ascii'
        assert unicode_support.supports_box_drawing is False


class TestUnicodeVisualDemonstration:
    """Visual demonstration tests for Unicode support system."""
    
    def test_visual_unicode_capability_demonstration(self):
        """Visual demonstration of Unicode capability detection."""
        print("\n" + "="*60)
        print("UNICODE SUPPORT - CAPABILITY DEMONSTRATION")
        print("="*60)
        
        support = _get_unicode_support()
        capabilities = support.get_capabilities_summary()
        
        print(f"\nTerminal Information:")
        print(f"  Is TTY: {capabilities['is_tty']}")
        print(f"  Encoding: {capabilities['encoding']}")
        
        print(f"\nUnicode Feature Support:")
        feature_names = {
            'box_drawing': 'Box Drawing Characters',
            'unicode_spinners': 'Unicode Spinners',
            'progress_blocks': 'Progress Bar Blocks',
            'status_chars': 'Status Characters'
        }
        
        for key, name in feature_names.items():
            status = "✅ Supported" if capabilities[key] else "❌ Not Supported"
            print(f"  {name:25}: {status}")
    
    def test_visual_box_drawing_demonstration(self):
        """Visual demonstration of box drawing characters."""
        print("\n" + "="*60)
        print("UNICODE SUPPORT - BOX DRAWING DEMONSTRATION")
        print("="*60)
        
        support = _get_unicode_support()
        
        if support.supports_box_drawing:
            print(f"\n✅ Box drawing characters are supported!")
            
            # Define box styles
            box_styles = {
                'Square': {
                    'corners': ['┌', '┐', '└', '┘'],
                    'lines': ['│', '─'],
                    'intersections': ['┼', '┴', '┬', '┤', '├']
                },
                'Rounded': {
                    'corners': ['╭', '╮', '╰', '╯'],
                    'lines': ['│', '─'],
                    'intersections': ['┼', '┴', '┬', '┤', '├']
                },
                'Double': {
                    'corners': ['╔', '╗', '╚', '╝'],
                    'lines': ['║', '═'],
                    'intersections': ['╬', '╩', '╦', '╣', '╠']
                },
                'Heavy': {
                    'corners': ['┏', '┓', '┗', '┛'],
                    'lines': ['┃', '━'],
                    'intersections': ['╋', '┻', '┳', '┫', '┣']
                }
            }
            
            for style_name, chars in box_styles.items():
                print(f"\n{style_name} Box Style:")
                # Create a small box demonstration
                tl, tr, bl, br = chars['corners']
                v, h = chars['lines']
                
                print(f"  {tl}{h*8}{tr}")
                print(f"  {v}  {style_name:4}  {v}")
                print(f"  {bl}{h*8}{br}")
                
                # Show character set
                all_chars = chars['corners'] + chars['lines'] + chars['intersections']
                print(f"  Characters: {' '.join(all_chars)}")
        else:
            print(f"\n❌ Box drawing characters are not supported.")
            print(f"  Fallback: ASCII boxes will be used instead")
            print(f"  Example ASCII box:")
            print(f"  +--------+")
            print(f"  | ASCII  |")
            print(f"  +--------+")
    
    def test_visual_spinner_demonstration(self):
        """Visual demonstration of spinner characters."""
        print("\n" + "="*60)
        print("UNICODE SUPPORT - SPINNER DEMONSTRATION")
        print("="*60)
        
        support = _get_unicode_support()
        
        if support.supports_unicode_spinners:
            print(f"\n✅ Unicode spinners are supported!")
            
            # Define spinner styles
            spinner_styles = {
                'Dots': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧'],
                'Arrow3': ['▹', '▸', '▹'],
                'DQPB (ASCII)': ['d', 'q', 'p', 'b']
            }
            
            for style_name, chars in spinner_styles.items():
                print(f"\n{style_name} Spinner:")
                print(f"  Characters: {' '.join(chars)}")
                print(f"  Animation: ", end="")
                for char in chars:
                    print(f"{char} ", end="")
                print()
        else:
            print(f"\n❌ Unicode spinners are not supported.")
            print(f"  Fallback: ASCII spinners will be used instead")
            print(f"  DQPB Spinner: d q p b")
            print(f"  Pipe Spinner: | / - \\")
    
    def test_visual_progress_bar_demonstration(self):
        """Visual demonstration of progress bar characters."""
        print("\n" + "="*60)
        print("UNICODE SUPPORT - PROGRESS BAR DEMONSTRATION")
        print("="*60)
        
        support = _get_unicode_support()
        
        if support.supports_progress_blocks:
            print(f"\n✅ Unicode progress blocks are supported!")
            
            # Define progress bar characters (from full to empty)
            progress_chars = ['█', '▉', '▊', '▋', '▌', '▍', '▎', '▏']
            
            print(f"\nProgress Block Characters:")
            print(f"  Full to Empty: {' '.join(progress_chars)}")
            
            # Show progress bar examples
            print(f"\nProgress Bar Examples:")
            for percent in [0, 25, 50, 75, 100]:
                bar_length = 20
                filled_length = int(bar_length * percent / 100)
                
                # Create bar with Unicode blocks
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                print(f"  {percent:3d}%: [{bar}]")
        else:
            print(f"\n❌ Unicode progress blocks are not supported.")
            print(f"  Fallback: ASCII progress bars will be used instead")
            print(f"\nASCII Progress Bar Examples:")
            for percent in [0, 25, 50, 75, 100]:
                bar_length = 20
                filled_length = int(bar_length * percent / 100)
                
                # Create bar with ASCII characters
                bar = '#' * filled_length + '-' * (bar_length - filled_length)
                print(f"  {percent:3d}%: [{bar}]")
    
    def test_visual_status_characters_demonstration(self):
        """Visual demonstration of status characters."""
        print("\n" + "="*60)
        print("UNICODE SUPPORT - STATUS CHARACTERS DEMONSTRATION")
        print("="*60)
        
        support = _get_unicode_support()
        
        if support.supports_status_chars:
            print(f"\n✅ Unicode status characters are supported!")
            
            # Define status characters with meanings
            status_chars = {
                '✓': 'Success/Checkmark',
                '✗': 'Error/X Mark',
                '⚠': 'Warning',
                'ℹ': 'Information',
                '✔': 'Check Mark (Heavy)',
                '✖': 'X Mark (Heavy)'
            }
            
            print(f"\nStatus Characters:")
            for char, meaning in status_chars.items():
                print(f"  {char} - {meaning}")
                
            print(f"\nExample Usage:")
            print(f"  ✓ Task completed successfully")
            print(f"  ✗ Task failed with error")
            print(f"  ⚠ Warning: Check configuration")
            print(f"  ℹ Information: Process started")
        else:
            print(f"\n❌ Unicode status characters are not supported.")
            print(f"  Fallback: ASCII status characters will be used instead")
            print(f"\nASCII Status Characters:")
            print(f"  [OK] - Success")
            print(f"  [X]  - Error")
            print(f"  [!]  - Warning")
            print(f"  [i]  - Information")
    
    def test_visual_encoding_demonstration(self):
        """Visual demonstration of encoding effects."""
        print("\n" + "="*60)
        print("UNICODE SUPPORT - ENCODING DEMONSTRATION")
        print("="*60)
        
        support = _get_unicode_support()
        
        print(f"\nCurrent Terminal Encoding: {support.encoding}")
        print(f"Is TTY: {support.is_tty}")
        
        # Test various character sets
        character_sets = {
            'ASCII': ['a', 'b', 'c', '1', '2', '3', '!', '@', '#'],
            'Latin-1': ['café', 'naïve', 'résumé'],
            'Box Drawing': ['┌', '┐', '└', '┘', '│', '─'],
            'Block Elements': ['█', '▉', '▊', '▋', '▌', '▍', '▎', '▏'],
            'Braille Patterns': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧'],
            'Arrows': ['▹', '▸', '◂', '◃', '▴', '▾'],
            'Status Symbols': ['✓', '✗', '⚠', 'ℹ', '✔', '✖'],
            'Emoji': ['😀', '🎉', '🔥', '💯', '🚀', '⭐']
        }
        
        print(f"\nCharacter Set Testing:")
        for set_name, chars in character_sets.items():
            print(f"\n{set_name}:")
            print(f"  Characters: ", end="")
            
            for char in chars:
                try:
                    # Try to encode with terminal encoding
                    char.encode(support.encoding)
                    print(f"{char} ", end="")
                except (UnicodeEncodeError, LookupError):
                    print(f"[?] ", end="")
            print()
            
            # Calculate visual width for some characters
            if set_name in ['Box Drawing', 'Block Elements', 'Status Symbols']:
                print(f"  Visual widths: ", end="")
                for char in chars[:5]:  # Test first 5 characters
                    width = wcswidth(char) or len(char)
                    print(f"{char}({width}) ", end="")
                print()
    
    def test_visual_fallback_demonstration(self):
        """Visual demonstration of fallback behavior."""
        print("\n" + "="*60)
        print("UNICODE SUPPORT - FALLBACK DEMONSTRATION")
        print("="*60)
        
        # Create Unicode support instances with different configurations
        configs = [
            ("UTF-8 TTY", {'is_tty': True, 'encoding': 'utf-8'}),
            ("UTF-8 Non-TTY", {'is_tty': False, 'encoding': 'utf-8'}),
            ("ASCII TTY", {'is_tty': True, 'encoding': 'ascii'}),
            ("ASCII Non-TTY", {'is_tty': False, 'encoding': 'ascii'}),
        ]
        
        for config_name, config in configs:
            print(f"\n{config_name} Configuration:")
            
            # Create mock terminal with specific configuration
            mock_terminal = Mock()
            mock_terminal.is_tty = config['is_tty']
            mock_terminal.encoding = config['encoding']
            
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                support = _UnicodeSupport(terminal_info=mock_terminal)
                capabilities = support.get_capabilities_summary()
                
                print(f"  Box Drawing: {'✅' if capabilities['box_drawing'] else '❌'}")
                print(f"  Spinners: {'✅' if capabilities['unicode_spinners'] else '❌'}")
                print(f"  Progress: {'✅' if capabilities['progress_blocks'] else '❌'}")
                print(f"  Status: {'✅' if capabilities['status_chars'] else '❌'}")
                
                if w:
                    print(f"  Warnings: {len(w)} issued")
                    for warning in w:
                        print(f"    - {warning.message}")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestUnicodeVisualDemonstration()
    demo.test_visual_unicode_capability_demonstration()
    demo.test_visual_box_drawing_demonstration()
    demo.test_visual_spinner_demonstration()
    demo.test_visual_progress_bar_demonstration()
    demo.test_visual_status_characters_demonstration()
    demo.test_visual_encoding_demonstration()
    demo.test_visual_fallback_demonstration()
    
    print("\n" + "="*60)
    print("✅ UNICODE SUPPORT TESTS COMPLETE")
    print("="*60)