"""
Comprehensive tests for FDL Color Conversion System.

Tests the internal color conversion system that handles named colors, hex colors,
RGB colors, ANSI code generation, HTML normalization, and caching.
"""

import pytest
import sys
import os
import warnings
from unittest.mock import patch

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.setup.color_conversion import (
    _ColorConverter, _get_named_colors, _is_valid_color, _to_ansi_fg, _to_ansi_bg,
    _normalize_for_html, _get_color_info
)


class TestColorConverter:
    """Test suite for the color converter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = _ColorConverter()
    
    def test_color_converter_initialization(self):
        """Test color converter initialization."""
        converter = _ColorConverter()
        
        # Should have compiled regex patterns
        assert hasattr(converter, '_hex_pattern')
        assert hasattr(converter, '_rgb_pattern')
        
        # Should have color dictionaries
        assert hasattr(converter, 'NAMED_COLORS_FG')
        assert hasattr(converter, 'NAMED_COLORS_BG')
        assert hasattr(converter, 'HTML_COLOR_NAMES')
    
    def test_get_named_colors(self):
        """Test getting all supported named colors."""
        colors = self.converter.get_named_colors()
        
        # Should be a set
        assert isinstance(colors, set)
        
        # Should contain expected colors
        expected_colors = {
            'red', 'green', 'yellow', 'blue', 'magenta', 'purple', 'cyan',
            'white', 'black', 'gray', 'orange', 'pink', 'brown', 'tan'
        }
        assert expected_colors.issubset(colors)
        
        # Should match foreground color keys
        assert colors == set(self.converter.NAMED_COLORS_FG.keys())
    
    def test_is_named_color_valid_colors(self):
        """Test named color detection with valid colors."""
        valid_colors = [
            'red', 'green', 'blue', 'yellow', 'magenta', 'purple', 'cyan',
            'white', 'black', 'gray', 'orange', 'pink', 'brown', 'tan'
        ]
        
        for color in valid_colors:
            assert self.converter.is_named_color(color)
            assert self.converter.is_named_color(color.upper())  # Case insensitive
            assert self.converter.is_named_color(f"  {color}  ")  # Whitespace handling
    
    def test_is_named_color_invalid_colors(self):
        """Test named color detection with invalid colors."""
        invalid_colors = [
            'crimson', 'lime', 'navy', 'maroon', 'teal', 'olive',
            'invalid', '', None, 123, []
        ]
        
        for color in invalid_colors:
            assert not self.converter.is_named_color(color)
    
    def test_is_hex_color_valid_formats(self):
        """Test hex color detection with valid formats."""
        valid_hex_colors = [
            '#FF0000', '#00FF00', '#0000FF',  # Full hex
            '#fff', '#000', '#f0f',          # Short hex
            '#123456', '#ABCDEF', '#abcdef',  # Mixed case
            '  #FF0000  ',                   # With whitespace
        ]
        
        for color in valid_hex_colors:
            assert self.converter.is_hex_color(color), f"Should be valid: {color}"
    
    def test_is_hex_color_invalid_formats(self):
        """Test hex color detection with invalid formats."""
        invalid_hex_colors = [
            'FF0000',      # Missing #
            '#GG0000',     # Invalid hex digits
            '#FF',         # Too short
            '#FF00000',    # Too long (7 digits)
            '#FF000',      # Invalid length (5 digits)
            '',            # Empty
            None,          # None
            123,           # Number
        ]
        
        for color in invalid_hex_colors:
            assert not self.converter.is_hex_color(color), f"Should be invalid: {color}"
    
    def test_is_rgb_color_valid_formats(self):
        """Test RGB color detection with valid formats."""
        valid_rgb_colors = [
            'rgb(255, 0, 0)',      # Standard format
            'rgb(0, 255, 0)',      # Green
            'rgb(0, 0, 255)',      # Blue
            'rgb(128, 128, 128)',  # Gray
            'rgb(0,0,0)',          # No spaces
            'rgb( 255 , 255 , 255 )',  # Extra spaces
            '  rgb(100, 100, 100)  ',  # Whitespace around
        ]
        
        for color in valid_rgb_colors:
            assert self.converter.is_rgb_color(color), f"Should be valid: {color}"
    
    def test_is_rgb_color_invalid_formats(self):
        """Test RGB color detection with invalid formats."""
        invalid_rgb_colors = [
            'rgb(256, 0, 0)',      # Value > 255
            'rgb(-1, 0, 0)',       # Negative value
            'rgb(255, 0)',         # Missing value
            'rgb(255, 0, 0, 0)',   # Too many values
            'rgb(255.5, 0, 0)',    # Decimal values
            'rgb(a, b, c)',        # Non-numeric
            'rgb 255, 0, 0',       # Missing parentheses
            '',                    # Empty
            None,                  # None
        ]
        
        for color in invalid_rgb_colors:
            assert not self.converter.is_rgb_color(color), f"Should be invalid: {color}"
    
    def test_is_valid_color_comprehensive(self):
        """Test comprehensive color validation."""
        # Valid colors of all types
        valid_colors = [
            # Named colors
            'red', 'blue', 'green',
            # Hex colors
            '#FF0000', '#00f', '#123456',
            # RGB colors
            'rgb(255, 0, 0)', 'rgb(0, 255, 0)',
        ]
        
        for color in valid_colors:
            assert self.converter.is_valid_color(color), f"Should be valid: {color}"
        
        # Invalid colors
        invalid_colors = [
            '', None, 123, [], 'invalid_color',
            '#GG0000', 'rgb(256, 0, 0)', 'not_a_color'
        ]
        
        for color in invalid_colors:
            assert not self.converter.is_valid_color(color), f"Should be invalid: {color}"
    
    def test_to_ansi_fg_named_colors(self):
        """Test ANSI foreground conversion for named colors."""
        test_cases = [
            ('red', '\033[31m'),
            ('green', '\033[32m'),
            ('blue', '\033[34m'),
            ('yellow', '\033[33m'),
            ('magenta', '\033[35m'),
            ('purple', '\033[35m'),  # Alias for magenta
            ('cyan', '\033[36m'),
            ('white', '\033[97m'),
            ('black', '\033[30m'),
        ]
        
        for color, expected_ansi in test_cases:
            result = self.converter.to_ansi_fg(color)
            assert result == expected_ansi, f"Color {color}: expected {expected_ansi}, got {result}"
            
            # Test case insensitivity
            result_upper = self.converter.to_ansi_fg(color.upper())
            assert result_upper == expected_ansi
    
    def test_to_ansi_bg_named_colors(self):
        """Test ANSI background conversion for named colors."""
        test_cases = [
            ('red', '\033[41m'),
            ('green', '\033[42m'),
            ('blue', '\033[44m'),
            ('yellow', '\033[43m'),
            ('magenta', '\033[45m'),
            ('purple', '\033[45m'),  # Alias for magenta
            ('cyan', '\033[46m'),
            ('white', '\033[107m'),
            ('black', '\033[40m'),
        ]
        
        for color, expected_ansi in test_cases:
            result = self.converter.to_ansi_bg(color)
            assert result == expected_ansi, f"Color {color}: expected {expected_ansi}, got {result}"
    
    def test_to_ansi_fg_hex_colors(self):
        """Test ANSI foreground conversion for hex colors."""
        test_cases = [
            ('#FF0000', '\033[38;2;255;0;0m'),    # Red
            ('#00FF00', '\033[38;2;0;255;0m'),    # Green
            ('#0000FF', '\033[38;2;0;0;255m'),    # Blue
            ('#ffffff', '\033[38;2;255;255;255m'), # White (lowercase)
            ('#000000', '\033[38;2;0;0;0m'),      # Black
            ('#f0f', '\033[38;2;255;0;255m'),     # Short hex (magenta)
            ('#abc', '\033[38;2;170;187;204m'),   # Short hex
        ]
        
        for color, expected_ansi in test_cases:
            result = self.converter.to_ansi_fg(color)
            assert result == expected_ansi, f"Color {color}: expected {expected_ansi}, got {result}"
    
    def test_to_ansi_bg_hex_colors(self):
        """Test ANSI background conversion for hex colors."""
        test_cases = [
            ('#FF0000', '\033[48;2;255;0;0m'),    # Red background
            ('#00FF00', '\033[48;2;0;255;0m'),    # Green background
            ('#0000FF', '\033[48;2;0;0;255m'),    # Blue background
        ]
        
        for color, expected_ansi in test_cases:
            result = self.converter.to_ansi_bg(color)
            assert result == expected_ansi, f"Color {color}: expected {expected_ansi}, got {result}"
    
    def test_to_ansi_fg_rgb_colors(self):
        """Test ANSI foreground conversion for RGB colors."""
        test_cases = [
            ('rgb(255, 0, 0)', '\033[38;2;255;0;0m'),    # Red
            ('rgb(0, 255, 0)', '\033[38;2;0;255;0m'),    # Green
            ('rgb(0, 0, 255)', '\033[38;2;0;0;255m'),    # Blue
            ('rgb(128, 128, 128)', '\033[38;2;128;128;128m'),  # Gray
            ('rgb( 255 , 255 , 255 )', '\033[38;2;255;255;255m'),  # With spaces
        ]
        
        for color, expected_ansi in test_cases:
            result = self.converter.to_ansi_fg(color)
            assert result == expected_ansi, f"Color {color}: expected {expected_ansi}, got {result}"
    
    def test_to_ansi_bg_rgb_colors(self):
        """Test ANSI background conversion for RGB colors."""
        test_cases = [
            ('rgb(255, 0, 0)', '\033[48;2;255;0;0m'),    # Red background
            ('rgb(0, 255, 0)', '\033[48;2;0;255;0m'),    # Green background
        ]
        
        for color, expected_ansi in test_cases:
            result = self.converter.to_ansi_bg(color)
            assert result == expected_ansi, f"Color {color}: expected {expected_ansi}, got {result}"
    
    def test_ansi_conversion_invalid_colors(self):
        """Test ANSI conversion with invalid colors."""
        invalid_colors = ['', None, 'invalid', '#GG0000', 'rgb(256, 0, 0)']
        
        for color in invalid_colors:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                fg_result = self.converter.to_ansi_fg(color)
                bg_result = self.converter.to_ansi_bg(color)
                
                # Should return empty string for invalid colors
                assert fg_result == ""
                assert bg_result == ""
                
                # Should issue warnings for string colors (but not None/empty)
                if color and isinstance(color, str):
                    assert len(w) >= 1
                    assert "Invalid color format" in str(w[0].message)
    
    def test_parse_hex_color_valid(self):
        """Test hex color parsing with valid colors."""
        test_cases = [
            ('#FF0000', (255, 0, 0)),
            ('#00FF00', (0, 255, 0)),
            ('#0000FF', (0, 0, 255)),
            ('#ffffff', (255, 255, 255)),
            ('#000000', (0, 0, 0)),
            ('#f0f', (255, 0, 255)),     # Short format
            ('#abc', (170, 187, 204)),   # Short format
        ]
        
        for hex_color, expected_rgb in test_cases:
            result = self.converter._parse_hex_color(hex_color)
            assert result == expected_rgb, f"Hex {hex_color}: expected {expected_rgb}, got {result}"
    
    def test_parse_hex_color_invalid(self):
        """Test hex color parsing with invalid colors."""
        invalid_hex_colors = ['#GG0000', '#FF', '#FF00000', 'FF0000', '']
        
        for hex_color in invalid_hex_colors:
            with pytest.raises(ValueError):
                self.converter._parse_hex_color(hex_color)
    
    def test_parse_rgb_color_valid(self):
        """Test RGB color parsing with valid colors."""
        test_cases = [
            ('rgb(255, 0, 0)', (255, 0, 0)),
            ('rgb(0, 255, 0)', (0, 255, 0)),
            ('rgb(0, 0, 255)', (0, 0, 255)),
            ('rgb(128, 128, 128)', (128, 128, 128)),
            ('rgb( 255 , 255 , 255 )', (255, 255, 255)),  # With spaces
        ]
        
        for rgb_color, expected_rgb in test_cases:
            result = self.converter._parse_rgb_color(rgb_color)
            assert result == expected_rgb, f"RGB {rgb_color}: expected {expected_rgb}, got {result}"
    
    def test_parse_rgb_color_invalid(self):
        """Test RGB color parsing with invalid colors."""
        invalid_rgb_colors = [
            'rgb(256, 0, 0)',      # Out of range
            'rgb(-1, 0, 0)',       # Negative
            'rgb(255, 0)',         # Missing value
            'rgb(a, b, c)',        # Non-numeric
            'invalid',             # Not RGB format
        ]
        
        for rgb_color in invalid_rgb_colors:
            with pytest.raises(ValueError):
                self.converter._parse_rgb_color(rgb_color)
    
    def test_normalize_for_html_named_colors(self):
        """Test HTML normalization for named colors."""
        html_colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan', 'white', 'black']
        
        for color in html_colors:
            result = self.converter.normalize_for_html(color)
            assert result == color.lower()
            
            # Test case handling
            result_upper = self.converter.normalize_for_html(color.upper())
            assert result_upper == color.lower()
    
    def test_normalize_for_html_hex_colors(self):
        """Test HTML normalization for hex colors."""
        test_cases = [
            ('#ff0000', '#FF0000'),    # Lowercase to uppercase
            ('#FF0000', '#FF0000'),    # Already uppercase
            ('#f0f', '#F0F'),          # Short format
        ]
        
        for input_color, expected in test_cases:
            result = self.converter.normalize_for_html(input_color)
            assert result == expected
    
    def test_normalize_for_html_rgb_colors(self):
        """Test HTML normalization for RGB colors."""
        test_cases = [
            ('rgb(255,0,0)', 'rgb(255, 0, 0)'),           # Add spaces
            ('rgb( 255 , 0 , 0 )', 'rgb(255, 0, 0)'),     # Normalize spaces
            ('rgb(128, 128, 128)', 'rgb(128, 128, 128)'), # Already normalized
        ]
        
        for input_color, expected in test_cases:
            result = self.converter.normalize_for_html(input_color)
            assert result == expected
    
    def test_normalize_for_html_invalid_colors(self):
        """Test HTML normalization with invalid colors."""
        invalid_colors = ['', None, 'invalid_color', '#GG0000']
        
        for color in invalid_colors:
            result = self.converter.normalize_for_html(color)
            # Should return the original color for invalid inputs
            assert result == color
    
    def test_get_conversion_info_comprehensive(self):
        """Test comprehensive color information retrieval."""
        # Test named color
        info = self.converter.get_conversion_info('red')
        assert info['original'] == 'red'
        assert info['normalized'] == 'red'
        assert info['is_valid'] is True
        assert info['color_type'] == 'named'
        assert info['ansi_fg'] == '\033[31m'
        assert info['ansi_bg'] == '\033[41m'
        assert info['html_normalized'] == 'red'
        
        # Test hex color
        info = self.converter.get_conversion_info('#FF0000')
        assert info['color_type'] == 'hex'
        assert info['rgb_values'] == (255, 0, 0)
        assert info['ansi_fg'] == '\033[38;2;255;0;0m'
        
        # Test RGB color
        info = self.converter.get_conversion_info('rgb(255, 0, 0)')
        assert info['color_type'] == 'rgb'
        assert info['rgb_values'] == (255, 0, 0)
        assert info['ansi_fg'] == '\033[38;2;255;0;0m'
        
        # Test invalid color
        info = self.converter.get_conversion_info('invalid')
        assert info['is_valid'] is False
        assert info['color_type'] == 'unknown'
        assert info['ansi_fg'] == ''
        assert info['ansi_bg'] == ''
    
    def test_get_conversion_info_edge_cases(self):
        """Test color information with edge cases."""
        # None input
        info = self.converter.get_conversion_info(None)
        assert info['is_valid'] is False
        assert info['original'] is None
        
        # Empty string
        info = self.converter.get_conversion_info('')
        assert info['is_valid'] is False
        assert info['original'] == ''
        
        # Non-string input
        info = self.converter.get_conversion_info(123)
        assert info['is_valid'] is False
    
    def test_caching_functionality(self):
        """Test that caching works for performance optimization."""
        # Clear cache if it exists
        self.converter.to_ansi_fg.cache_clear()
        self.converter.to_ansi_bg.cache_clear()
        self.converter.normalize_for_html.cache_clear()
        
        # First call should cache the result
        color = 'red'
        result1 = self.converter.to_ansi_fg(color)
        cache_info1 = self.converter.to_ansi_fg.cache_info()
        
        # Second call should use cache
        result2 = self.converter.to_ansi_fg(color)
        cache_info2 = self.converter.to_ansi_fg.cache_info()
        
        # Results should be identical
        assert result1 == result2
        
        # Cache hits should increase
        assert cache_info2.hits > cache_info1.hits


class TestColorConversionGlobalFunctions:
    """Test suite for global color conversion functions."""
    
    def test_get_named_colors_function(self):
        """Test global get_named_colors function."""
        colors = _get_named_colors()
        
        assert isinstance(colors, set)
        assert 'red' in colors
        assert 'blue' in colors
        assert 'green' in colors
    
    def test_is_valid_color_function(self):
        """Test global is_valid_color function."""
        assert _is_valid_color('red') is True
        assert _is_valid_color('#FF0000') is True
        assert _is_valid_color('rgb(255, 0, 0)') is True
        assert _is_valid_color('invalid') is False
    
    def test_to_ansi_fg_function(self):
        """Test global to_ansi_fg function."""
        assert _to_ansi_fg('red') == '\033[31m'
        assert _to_ansi_fg('#FF0000') == '\033[38;2;255;0;0m'
        assert _to_ansi_fg('rgb(255, 0, 0)') == '\033[38;2;255;0;0m'
    
    def test_to_ansi_bg_function(self):
        """Test global to_ansi_bg function."""
        assert _to_ansi_bg('red') == '\033[41m'
        assert _to_ansi_bg('#FF0000') == '\033[48;2;255;0;0m'
        assert _to_ansi_bg('rgb(255, 0, 0)') == '\033[48;2;255;0;0m'
    
    def test_normalize_for_html_function(self):
        """Test global normalize_for_html function."""
        assert _normalize_for_html('red') == 'red'
        assert _normalize_for_html('#ff0000') == '#FF0000'
        assert _normalize_for_html('rgb(255,0,0)') == 'rgb(255, 0, 0)'
    
    def test_get_color_info_function(self):
        """Test global get_color_info function."""
        info = _get_color_info('red')
        
        assert info['color_type'] == 'named'
        assert info['is_valid'] is True
        assert info['ansi_fg'] == '\033[31m'


class TestColorConversionEdgeCases:
    """Test suite for edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = _ColorConverter()
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in color strings."""
        test_cases = [
            ('  red  ', 'red'),
            ('\tblue\n', 'blue'),
            ('  #FF0000  ', '#FF0000'),
            ('  rgb(255, 0, 0)  ', 'rgb(255, 0, 0)'),
        ]
        
        for input_color, expected_base in test_cases:
            # Should handle whitespace in validation
            assert self.converter.is_valid_color(input_color)
            
            # Should produce same ANSI as trimmed version
            expected_ansi = self.converter.to_ansi_fg(expected_base)
            actual_ansi = self.converter.to_ansi_fg(input_color)
            assert actual_ansi == expected_ansi
    
    def test_case_insensitivity(self):
        """Test case insensitivity for color names."""
        test_cases = ['red', 'RED', 'Red', 'rEd']
        expected_ansi = '\033[31m'
        
        for color in test_cases:
            assert self.converter.is_valid_color(color)
            assert self.converter.to_ansi_fg(color) == expected_ansi
    
    def test_hex_color_case_handling(self):
        """Test hex color case handling."""
        test_cases = ['#ff0000', '#FF0000', '#Ff0000', '#fF0000']
        expected_ansi = '\033[38;2;255;0;0m'
        
        for color in test_cases:
            assert self.converter.is_valid_color(color)
            assert self.converter.to_ansi_fg(color) == expected_ansi
    
    def test_rgb_color_spacing_variations(self):
        """Test RGB color with different spacing."""
        test_cases = [
            'rgb(255,0,0)',
            'rgb(255, 0, 0)',
            'rgb( 255 , 0 , 0 )',
            'rgb(  255  ,  0  ,  0  )',
        ]
        expected_ansi = '\033[38;2;255;0;0m'
        
        for color in test_cases:
            assert self.converter.is_valid_color(color)
            assert self.converter.to_ansi_fg(color) == expected_ansi
    
    def test_boundary_rgb_values(self):
        """Test RGB colors at boundary values."""
        boundary_cases = [
            ('rgb(0, 0, 0)', True),      # Minimum values
            ('rgb(255, 255, 255)', True), # Maximum values
            ('rgb(256, 0, 0)', False),   # Over maximum
            ('rgb(-1, 0, 0)', False),    # Under minimum
        ]
        
        for color, should_be_valid in boundary_cases:
            assert self.converter.is_valid_color(color) == should_be_valid
    
    def test_hex_color_boundary_cases(self):
        """Test hex colors at boundaries."""
        boundary_cases = [
            ('#000000', True),  # All zeros
            ('#FFFFFF', True),  # All max
            ('#000', True),     # Short format zeros
            ('#FFF', True),     # Short format max
        ]
        
        for color, should_be_valid in boundary_cases:
            assert self.converter.is_valid_color(color) == should_be_valid
    
    def test_warning_generation(self):
        """Test that warnings are generated for invalid colors."""
        invalid_colors = ['invalid_color', '#GG0000', 'rgb(256, 0, 0)']
        
        for color in invalid_colors:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                result = self.converter.to_ansi_fg(color)
                
                assert result == ""
                assert len(w) == 1
                assert "Invalid color format" in str(w[0].message)
                assert color in str(w[0].message)


class TestColorConversionVisualDemonstration:
    """Visual demonstration tests for color conversion system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = _ColorConverter()
    
    def test_visual_named_colors_demonstration(self):
        """Visual demonstration of all named colors."""
        print("\n" + "="*60)
        print("COLOR CONVERSION - NAMED COLORS DEMONSTRATION")
        print("="*60)
        
        named_colors = sorted(self.converter.get_named_colors())
        
        print(f"\nSupported named colors ({len(named_colors)}):")
        
        for color in named_colors:
            fg_ansi = self.converter.to_ansi_fg(color)
            bg_ansi = self.converter.to_ansi_bg(color)
            
            # Show foreground color
            print(f"  {color:8} -> ", end="")
            print(f"{fg_ansi}{color} text\033[0m", end="")
            print(f" | ", end="")
            print(f"{bg_ansi} {color} bg \033[0m")
    
    def test_visual_hex_colors_demonstration(self):
        """Visual demonstration of hex color conversion."""
        print("\n" + "="*60)
        print("COLOR CONVERSION - HEX COLORS DEMONSTRATION")
        print("="*60)
        
        hex_colors = [
            ('#FF0000', 'Red'),
            ('#00FF00', 'Green'),
            ('#0000FF', 'Blue'),
            ('#FFFF00', 'Yellow'),
            ('#FF00FF', 'Magenta'),
            ('#00FFFF', 'Cyan'),
            ('#FFFFFF', 'White'),
            ('#000000', 'Black'),
            ('#808080', 'Gray'),
            ('#f0f', 'Short Magenta'),
            ('#0f0', 'Short Green'),
        ]
        
        print(f"\nHex color conversions:")
        
        for hex_color, description in hex_colors:
            ansi = self.converter.to_ansi_fg(hex_color)
            rgb_values = self.converter._parse_hex_color(hex_color)
            
            print(f"  {hex_color:8} ({description:12}) -> ", end="")
            print(f"{ansi}■■■ Sample Text\033[0m", end="")
            print(f" RGB{rgb_values}")
    
    def test_visual_rgb_colors_demonstration(self):
        """Visual demonstration of RGB color conversion."""
        print("\n" + "="*60)
        print("COLOR CONVERSION - RGB COLORS DEMONSTRATION")
        print("="*60)
        
        rgb_colors = [
            ('rgb(255, 0, 0)', 'Red'),
            ('rgb(0, 255, 0)', 'Green'),
            ('rgb(0, 0, 255)', 'Blue'),
            ('rgb(255, 255, 0)', 'Yellow'),
            ('rgb(255, 0, 255)', 'Magenta'),
            ('rgb(0, 255, 255)', 'Cyan'),
            ('rgb(128, 128, 128)', 'Gray'),
            ('rgb(255, 165, 0)', 'Orange'),
            ('rgb(128, 0, 128)', 'Purple'),
        ]
        
        print(f"\nRGB color conversions:")
        
        for rgb_color, description in rgb_colors:
            ansi = self.converter.to_ansi_fg(rgb_color)
            
            print(f"  {rgb_color:18} ({description:8}) -> ", end="")
            print(f"{ansi}■■■ Sample Text\033[0m")
    
    def test_visual_color_validation_demonstration(self):
        """Visual demonstration of color validation."""
        print("\n" + "="*60)
        print("COLOR CONVERSION - VALIDATION DEMONSTRATION")
        print("="*60)
        
        test_colors = [
            # Valid colors
            ('red', True, 'Named color'),
            ('#FF0000', True, 'Hex color (full)'),
            ('#f0f', True, 'Hex color (short)'),
            ('rgb(255, 0, 0)', True, 'RGB color'),
            
            # Invalid colors
            ('invalid', False, 'Unknown named color'),
            ('#GG0000', False, 'Invalid hex digits'),
            ('rgb(256, 0, 0)', False, 'RGB value out of range'),
            ('not_a_color', False, 'Invalid format'),
            ('', False, 'Empty string'),
        ]
        
        print(f"\nColor validation results:")
        
        for color, expected_valid, description in test_colors:
            is_valid = self.converter.is_valid_color(color)
            status = "✅ Valid" if is_valid else "❌ Invalid"
            expected = "✅" if expected_valid else "❌"
            
            print(f"  {color:20} -> {status:10} (Expected: {expected}) - {description}")
            
            if is_valid == expected_valid:
                print(f"    \033[32m✓ Correct validation\033[0m")
            else:
                print(f"    \033[31m✗ Validation mismatch\033[0m")
    
    def test_visual_html_normalization_demonstration(self):
        """Visual demonstration of HTML color normalization."""
        print("\n" + "="*60)
        print("COLOR CONVERSION - HTML NORMALIZATION DEMONSTRATION")
        print("="*60)
        
        test_colors = [
            ('red', 'Named color'),
            ('RED', 'Named color (uppercase)'),
            ('#ff0000', 'Hex color (lowercase)'),
            ('#FF0000', 'Hex color (uppercase)'),
            ('#f0f', 'Short hex color'),
            ('rgb(255,0,0)', 'RGB color (no spaces)'),
            ('rgb( 255 , 0 , 0 )', 'RGB color (extra spaces)'),
            ('invalid', 'Invalid color'),
        ]
        
        print(f"\nHTML normalization results:")
        
        for color, description in test_colors:
            normalized = self.converter.normalize_for_html(color)
            
            print(f"  {color:20} -> {normalized:20} ({description})")
    
    def test_visual_color_info_demonstration(self):
        """Visual demonstration of comprehensive color information."""
        print("\n" + "="*60)
        print("COLOR CONVERSION - COMPREHENSIVE INFO DEMONSTRATION")
        print("="*60)
        
        test_colors = ['red', '#FF0000', 'rgb(255, 0, 0)', 'invalid']
        
        for color in test_colors:
            print(f"\nColor: '{color}'")
            info = self.converter.get_conversion_info(color)
            
            print(f"  Original: {info['original']}")
            print(f"  Normalized: {info['normalized']}")
            print(f"  Valid: {info['is_valid']}")
            print(f"  Type: {info['color_type']}")
            print(f"  ANSI FG: {repr(info['ansi_fg'])}")
            print(f"  ANSI BG: {repr(info['ansi_bg'])}")
            print(f"  HTML: {info['html_normalized']}")
            
            if 'rgb_values' in info:
                print(f"  RGB Values: {info['rgb_values']}")
            
            # Show visual sample if valid
            if info['is_valid'] and info['ansi_fg']:
                print(f"  Visual: {info['ansi_fg']}■■■ Sample Text\033[0m")
    
    def test_visual_caching_demonstration(self):
        """Visual demonstration of caching functionality."""
        print("\n" + "="*60)
        print("COLOR CONVERSION - CACHING DEMONSTRATION")
        print("="*60)
        
        # Clear caches
        self.converter.to_ansi_fg.cache_clear()
        self.converter.to_ansi_bg.cache_clear()
        self.converter.normalize_for_html.cache_clear()
        
        test_colors = ['red', 'blue', 'green', '#FF0000', 'rgb(255, 0, 0)']
        
        print(f"\nInitial cache state:")
        print(f"  FG Cache: {self.converter.to_ansi_fg.cache_info()}")
        print(f"  BG Cache: {self.converter.to_ansi_bg.cache_info()}")
        print(f"  HTML Cache: {self.converter.normalize_for_html.cache_info()}")
        
        print(f"\nProcessing colors (first time):")
        for color in test_colors:
            fg = self.converter.to_ansi_fg(color)
            bg = self.converter.to_ansi_bg(color)
            html = self.converter.normalize_for_html(color)
            print(f"  Processed: {color}")
        
        print(f"\nCache state after first processing:")
        print(f"  FG Cache: {self.converter.to_ansi_fg.cache_info()}")
        print(f"  BG Cache: {self.converter.to_ansi_bg.cache_info()}")
        print(f"  HTML Cache: {self.converter.normalize_for_html.cache_info()}")
        
        print(f"\nProcessing same colors (second time - should hit cache):")
        for color in test_colors:
            fg = self.converter.to_ansi_fg(color)
            bg = self.converter.to_ansi_bg(color)
            html = self.converter.normalize_for_html(color)
            print(f"  Processed: {color}")
        
        print(f"\nFinal cache state (should show cache hits):")
        print(f"  FG Cache: {self.converter.to_ansi_fg.cache_info()}")
        print(f"  BG Cache: {self.converter.to_ansi_bg.cache_info()}")
        print(f"  HTML Cache: {self.converter.normalize_for_html.cache_info()}")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestColorConversionVisualDemonstration()
    demo.setup_method()  # Manually call setup since we're not using pytest
    demo.test_visual_named_colors_demonstration()
    demo.test_visual_hex_colors_demonstration()
    demo.test_visual_rgb_colors_demonstration()
    demo.test_visual_color_validation_demonstration()
    demo.test_visual_html_normalization_demonstration()
    demo.test_visual_color_info_demonstration()
    demo.test_visual_caching_demonstration()
    
    print("\n" + "="*60)
    print("✅ COLOR CONVERSION TESTS COMPLETE")
    print("="*60)