# tests/test_fdl/test_setup/test_color_conversion.py
import pytest
import sys
import warnings
from unittest.mock import patch, Mock

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

from setup.color_conversion import (
    _ColorConverter, _get_named_colors, _is_valid_color, _to_ansi_fg, _to_ansi_bg,
    _normalize_for_html, _get_color_info, _color_converter
)


class TestColorConverter:
    """Test the internal _ColorConverter class."""
    
    def test_initialization(self):
        """Test _ColorConverter initialization."""
        converter = _ColorConverter()
        
        # Should have regex patterns compiled
        assert hasattr(converter, '_hex_pattern')
        assert hasattr(converter, '_rgb_pattern')
        
        # Should have color dictionaries
        assert hasattr(converter, 'NAMED_COLORS_FG')
        assert hasattr(converter, 'NAMED_COLORS_BG')
        assert hasattr(converter, 'HTML_COLOR_NAMES')
    
    def test_named_colors_dictionaries(self):
        """Test named color dictionaries are properly defined."""
        converter = _ColorConverter()
        
        # Basic colors should be present
        basic_colors = ['red', 'green', 'blue', 'yellow', 'black', 'white']
        
        for color in basic_colors:
            assert color in converter.NAMED_COLORS_FG
            assert color in converter.NAMED_COLORS_BG
            assert color in converter.HTML_COLOR_NAMES
        
        # ANSI codes should be strings starting with escape sequence
        for color, ansi_code in converter.NAMED_COLORS_FG.items():
            assert isinstance(ansi_code, str)
            assert ansi_code.startswith('\033[')
            assert ansi_code.endswith('m')
        
        for color, ansi_code in converter.NAMED_COLORS_BG.items():
            assert isinstance(ansi_code, str)
            assert ansi_code.startswith('\033[')
            assert ansi_code.endswith('m')
    
    def test_get_named_colors(self):
        """Test get_named_colors method."""
        converter = _ColorConverter()
        named_colors = converter.get_named_colors()
        
        assert isinstance(named_colors, set)
        assert 'red' in named_colors
        assert 'blue' in named_colors
        assert 'green' in named_colors
        assert len(named_colors) > 0
    
    def test_is_named_color(self):
        """Test is_named_color method."""
        converter = _ColorConverter()
        
        # Valid named colors
        assert converter.is_named_color('red') is True
        assert converter.is_named_color('blue') is True
        assert converter.is_named_color('RED') is True  # Case insensitive
        assert converter.is_named_color(' green ') is True  # Strips whitespace
        
        # Invalid named colors
        assert converter.is_named_color('invalid_color') is False
        assert converter.is_named_color('') is False
        assert converter.is_named_color('123') is False
    
    def test_is_hex_color(self):
        """Test is_hex_color method."""
        converter = _ColorConverter()
        
        # Valid hex colors
        assert converter.is_hex_color('#fff') is True  # #RGB
        assert converter.is_hex_color('#ffffff') is True  # #RRGGBB
        assert converter.is_hex_color('#123') is True
        assert converter.is_hex_color('#abcdef') is True
        assert converter.is_hex_color('#ABCDEF') is True  # Case insensitive
        assert converter.is_hex_color(' #fff ') is True  # Strips whitespace
        
        # Invalid hex colors
        assert converter.is_hex_color('fff') is False  # Missing #
        assert converter.is_hex_color('#ff') is False  # Too short
        assert converter.is_hex_color('#ffff') is False  # Invalid length
        assert converter.is_hex_color('#gggggg') is False  # Invalid hex chars
        assert converter.is_hex_color('') is False
        assert converter.is_hex_color('#') is False
    
    def test_is_rgb_color(self):
        """Test is_rgb_color method."""
        converter = _ColorConverter()
        
        # Valid RGB colors
        assert converter.is_rgb_color('rgb(255, 255, 255)') is True
        assert converter.is_rgb_color('rgb(0, 0, 0)') is True
        assert converter.is_rgb_color('rgb(255,255,255)') is True  # No spaces
        assert converter.is_rgb_color(' rgb(255, 255, 255) ') is True  # Strips whitespace
        assert converter.is_rgb_color('rgb(   255  ,  255  ,  255  )') is True  # Extra spaces
        
        # Invalid RGB colors
        assert converter.is_rgb_color('rgb(256, 255, 255)') is False  # Values parsed separately
        assert converter.is_rgb_color('rgb(255, 255)') is False  # Missing value
        assert converter.is_rgb_color('rgb(255, 255, 255, 255)') is False  # Too many values
        assert converter.is_rgb_color('rgb(a, b, c)') is False  # Non-numeric
        assert converter.is_rgb_color('') is False
        assert converter.is_rgb_color('rgb()') is False
    
    def test_is_valid_color(self):
        """Test is_valid_color method (combines all color type checks)."""
        converter = _ColorConverter()
        
        # Valid colors of different types
        assert converter.is_valid_color('red') is True  # Named
        assert converter.is_valid_color('#fff') is True  # Hex short
        assert converter.is_valid_color('#ffffff') is True  # Hex long
        assert converter.is_valid_color('rgb(255, 255, 255)') is True  # RGB
        
        # Invalid colors
        assert converter.is_valid_color('invalid') is False
        assert converter.is_valid_color('') is False
        assert converter.is_valid_color('#gg') is False
        assert converter.is_valid_color('rgb(300, 300, 300)') is False
    
    def test_hex_to_ansi_conversion(self):
        """Test hex color to ANSI conversion."""
        converter = _ColorConverter()
        
        # Test #RGB format
        fg_code = converter.to_ansi_fg('#fff')
        assert fg_code.startswith('\033[38;2;')
        assert fg_code.endswith('m')
        assert '255;255;255' in fg_code  # #fff = rgb(255,255,255)
        
        bg_code = converter.to_ansi_bg('#fff')
        assert bg_code.startswith('\033[48;2;')
        assert bg_code.endswith('m')
        assert '255;255;255' in bg_code
        
        # Test #RRGGBB format
        fg_code = converter.to_ansi_fg('#ff0000')
        assert '255;0;0' in fg_code  # Red
        
        # Test case insensitivity
        fg_code1 = converter.to_ansi_fg('#abcdef')
        fg_code2 = converter.to_ansi_fg('#ABCDEF')
        assert fg_code1 == fg_code2
    
    def test_rgb_to_ansi_conversion(self):
        """Test RGB color to ANSI conversion."""
        converter = _ColorConverter()
        
        # Test basic RGB
        fg_code = converter.to_ansi_fg('rgb(255, 0, 0)')
        assert fg_code.startswith('\033[38;2;')
        assert '255;0;0' in fg_code
        
        bg_code = converter.to_ansi_bg('rgb(0, 255, 0)')
        assert bg_code.startswith('\033[48;2;')
        assert '0;255;0' in bg_code
        
        # Test with different spacing
        fg_code1 = converter.to_ansi_fg('rgb(255, 255, 255)')
        fg_code2 = converter.to_ansi_fg('rgb(255,255,255)')
        assert fg_code1 == fg_code2
    
    def test_named_color_to_ansi_conversion(self):
        """Test named color to ANSI conversion."""
        converter = _ColorConverter()
        
        # Test foreground
        red_fg = converter.to_ansi_fg('red')
        assert red_fg == converter.NAMED_COLORS_FG['red']
        
        # Test background
        red_bg = converter.to_ansi_bg('red')
        assert red_bg == converter.NAMED_COLORS_BG['red']
        
        # Test case insensitivity
        red_fg1 = converter.to_ansi_fg('red')
        red_fg2 = converter.to_ansi_fg('RED')
        assert red_fg1 == red_fg2
    
    def test_invalid_color_conversion(self):
        """Test conversion of invalid colors."""
        converter = _ColorConverter()
        
        with patch('warnings.warn') as mock_warn:
            # Invalid colors should return empty string and warn
            result = converter.to_ansi_fg('invalid_color')
            assert result == ""
            mock_warn.assert_called()
            
            result = converter.to_ansi_bg('invalid_color')
            assert result == ""
    
    def test_html_normalization(self):
        """Test HTML color normalization."""
        converter = _ColorConverter()
        
        # Named colors valid in CSS
        assert converter.normalize_for_html('red') == 'red'
        assert converter.normalize_for_html('blue') == 'blue'
        
        # Hex colors should be normalized to uppercase
        assert converter.normalize_for_html('#fff') == '#FFF'
        assert converter.normalize_for_html('#abcdef') == '#ABCDEF'
        
        # RGB colors should be normalized
        normalized = converter.normalize_for_html('rgb(255, 255, 255)')
        assert normalized == 'rgb(255, 255, 255)'
        
        # Spacing normalization
        normalized = converter.normalize_for_html('rgb(255,255,255)')
        assert normalized == 'rgb(255, 255, 255)'
    
    def test_parse_hex_color_internal(self):
        """Test internal hex color parsing method."""
        converter = _ColorConverter()
        
        # Test #RGB format
        r, g, b = converter._parse_hex_color('#fff')
        assert (r, g, b) == (255, 255, 255)
        
        r, g, b = converter._parse_hex_color('#f00')
        assert (r, g, b) == (255, 0, 0)
        
        # Test #RRGGBB format
        r, g, b = converter._parse_hex_color('#ff0000')
        assert (r, g, b) == (255, 0, 0)
        
        r, g, b = converter._parse_hex_color('#abcdef')
        assert (r, g, b) == (171, 205, 239)
        
        # Test invalid format
        with pytest.raises(ValueError):
            converter._parse_hex_color('invalid')
    
    def test_parse_rgb_color_internal(self):
        """Test internal RGB color parsing method."""
        converter = _ColorConverter()
        
        # Test valid RGB
        r, g, b = converter._parse_rgb_color('rgb(255, 0, 0)')
        assert (r, g, b) == (255, 0, 0)
        
        r, g, b = converter._parse_rgb_color('rgb(123, 45, 67)')
        assert (r, g, b) == (123, 45, 67)
        
        # Test with different spacing
        r, g, b = converter._parse_rgb_color('rgb(255,255,255)')
        assert (r, g, b) == (255, 255, 255)
        
        # Test invalid values
        with pytest.raises(ValueError):
            converter._parse_rgb_color('rgb(256, 255, 255)')  # Out of range
        
        with pytest.raises(ValueError):
            converter._parse_rgb_color('rgb(-1, 255, 255)')  # Negative
        
        with pytest.raises(ValueError):
            converter._parse_rgb_color('invalid')
    
    def test_get_conversion_info(self):
        """Test get_conversion_info method."""
        converter = _ColorConverter()
        
        # Test named color info
        info = converter.get_conversion_info('red')
        assert info['original'] == 'red'
        assert info['normalized'] == 'red'
        assert info['is_valid'] is True
        assert info['color_type'] == 'named'
        assert info['ansi_fg'] != ''
        assert info['ansi_bg'] != ''
        
        # Test hex color info
        info = converter.get_conversion_info('#ff0000')
        assert info['color_type'] == 'hex'
        assert info['is_valid'] is True
        assert 'rgb_values' in info
        assert info['rgb_values'] == (255, 0, 0)
        
        # Test RGB color info
        info = converter.get_conversion_info('rgb(0, 255, 0)')
        assert info['color_type'] == 'rgb'
        assert info['is_valid'] is True
        assert info['rgb_values'] == (0, 255, 0)
        
        # Test invalid color info
        info = converter.get_conversion_info('invalid')
        assert info['is_valid'] is False
        assert info['color_type'] == 'unknown'
    
    def test_caching_behavior(self):
        """Test that caching works for performance."""
        converter = _ColorConverter()
        
        # Multiple calls should return same result (testing caching indirectly)
        result1 = converter.to_ansi_fg('#ff0000')
        result2 = converter.to_ansi_fg('#ff0000')
        assert result1 == result2
        
        # Cache should work for different methods
        html1 = converter.normalize_for_html('#abcdef')
        html2 = converter.normalize_for_html('#abcdef')
        assert html1 == html2


class TestGlobalColorConverter:
    """Test the global color converter instance and convenience functions."""
    
    def test_global_instance_exists(self):
        """Test that global _color_converter instance exists."""
        from setup.color_conversion import _color_converter
        
        assert isinstance(_color_converter, _ColorConverter)
    
    def test_get_named_colors_function(self):
        """Test global _get_named_colors function."""
        named_colors = _get_named_colors()
        
        assert isinstance(named_colors, set)
        assert 'red' in named_colors
        assert 'blue' in named_colors
        assert len(named_colors) > 0
    
    def test_is_valid_color_function(self):
        """Test global _is_valid_color function."""
        assert _is_valid_color('red') is True
        assert _is_valid_color('#fff') is True
        assert _is_valid_color('rgb(255, 255, 255)') is True
        assert _is_valid_color('invalid') is False
    
    def test_to_ansi_fg_function(self):
        """Test global _to_ansi_fg function."""
        result = _to_ansi_fg('red')
        assert isinstance(result, str)
        assert result != ""
        assert result.startswith('\033[')
    
    def test_to_ansi_bg_function(self):
        """Test global _to_ansi_bg function."""
        result = _to_ansi_bg('red')
        assert isinstance(result, str)
        assert result != ""
        assert result.startswith('\033[')
    
    def test_normalize_for_html_function(self):
        """Test global _normalize_for_html function."""
        result = _normalize_for_html('red')
        assert result == 'red'
        
        result = _normalize_for_html('#fff')
        assert result == '#FFF'
    
    def test_get_color_info_function(self):
        """Test global _get_color_info function."""
        info = _get_color_info('red')
        
        assert isinstance(info, dict)
        assert 'original' in info
        assert 'is_valid' in info
        assert 'color_type' in info
        assert info['is_valid'] is True


class TestColorConversionEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_string_handling(self):
        """Test handling of empty strings."""
        converter = _ColorConverter()
        
        assert converter.is_valid_color('') is False
        assert converter.to_ansi_fg('') == ""
        assert converter.to_ansi_bg('') == ""
    
    def test_whitespace_handling(self):
        """Test handling of whitespace in colors."""
        converter = _ColorConverter()
        
        # Should strip whitespace
        assert converter.is_named_color(' red ') is True
        assert converter.is_hex_color(' #fff ') is True
        assert converter.is_rgb_color(' rgb(255, 255, 255) ') is True
        
        # Results should be same as without whitespace
        result1 = converter.to_ansi_fg('red')
        result2 = converter.to_ansi_fg(' red ')
        assert result1 == result2
    
    def test_case_insensitivity(self):
        """Test case insensitive color handling."""
        converter = _ColorConverter()
        
        # Named colors should be case insensitive
        assert converter.to_ansi_fg('red') == converter.to_ansi_fg('RED')
        assert converter.to_ansi_fg('red') == converter.to_ansi_fg('Red')
        
        # Hex colors should be case insensitive
        assert converter.to_ansi_fg('#abc') == converter.to_ansi_fg('#ABC')
        assert converter.to_ansi_fg('#abcdef') == converter.to_ansi_fg('#ABCDEF')
    
    def test_rgb_boundary_values(self):
        """Test RGB values at boundaries."""
        converter = _ColorConverter()
        
        # Valid boundary values
        assert converter.is_rgb_color('rgb(0, 0, 0)') is True
        assert converter.is_rgb_color('rgb(255, 255, 255)') is True
        
        # Test conversion of boundary values
        black = converter.to_ansi_fg('rgb(0, 0, 0)')
        assert '0;0;0' in black
        
        white = converter.to_ansi_fg('rgb(255, 255, 255)')
        assert '255;255;255' in white
    
    def test_invalid_rgb_values(self):
        """Test handling of invalid RGB values."""
        converter = _ColorConverter()
        
        # Values should be parsed during _parse_rgb_color
        # But is_rgb_color only checks format, not value ranges
        assert converter.is_rgb_color('rgb(256, 255, 255)') is False  # Caught by regex
        assert converter.is_rgb_color('rgb(-1, 255, 255)') is False  # Caught by regex
        
        # These should be invalid during parsing
        with pytest.raises(ValueError):
            converter._parse_rgb_color('rgb(256, 255, 255)')
        
        with pytest.raises(ValueError):
            converter._parse_rgb_color('rgb(-1, 255, 255)')
    
    def test_hex_edge_cases(self):
        """Test hex color edge cases."""
        converter = _ColorConverter()
        
        # Valid edge cases
        assert converter.is_hex_color('#000') is True
        assert converter.is_hex_color('#fff') is True
        assert converter.is_hex_color('#000000') is True
        assert converter.is_hex_color('#ffffff') is True
        
        # Invalid cases
        assert converter.is_hex_color('#') is False
        assert converter.is_hex_color('#f') is False
        assert converter.is_hex_color('#ff') is False
        assert converter.is_hex_color('#ffff') is False
        assert converter.is_hex_color('#fffff') is False
        assert converter.is_hex_color('#fffffff') is False
    
    def test_warning_suppression(self):
        """Test that warnings can be suppressed for invalid colors."""
        converter = _ColorConverter()
        
        with patch('warnings.warn') as mock_warn:
            # Multiple invalid colors should each generate warnings
            converter.to_ansi_fg('invalid1')
            converter.to_ansi_fg('invalid2')
            converter.to_ansi_bg('invalid3')
            
            # Should have called warn multiple times
            assert mock_warn.call_count >= 3
    
    def test_unknown_named_colors(self):
        """Test handling of unknown named colors."""
        converter = _ColorConverter()
        
        unknown_colors = ['crimson', 'turquoise', 'salmon', 'unknown_color']
        
        for color in unknown_colors:
            if color not in converter.NAMED_COLORS_FG:
                assert converter.is_named_color(color) is False
                
                with patch('warnings.warn'):
                    result = converter.to_ansi_fg(color)
                    assert result == ""


class TestColorConversionPerformance:
    """Test performance-related aspects like caching."""
    
    def test_caching_consistency(self):
        """Test that cached results are consistent."""
        converter = _ColorConverter()
        
        # Same color should always return same result
        colors_to_test = ['red', '#ff0000', 'rgb(255, 0, 0)', '#f00']
        
        for color in colors_to_test:
            if converter.is_valid_color(color):
                result1 = converter.to_ansi_fg(color)
                result2 = converter.to_ansi_fg(color)
                assert result1 == result2
                
                result1 = converter.normalize_for_html(color)
                result2 = converter.normalize_for_html(color)
                assert result1 == result2
    
    def test_cache_size_limits(self):
        """Test that cache respects size limits."""
        # This is difficult to test directly since we can't easily access
        # the cache internals, but we can verify behavior doesn't change
        # with many different colors
        converter = _ColorConverter()
        
        # Generate many different valid colors
        for r in range(0, 256, 50):
            for g in range(0, 256, 50):
                for b in range(0, 256, 50):
                    color = f'rgb({r}, {g}, {b})'
                    result = converter.to_ansi_fg(color)
                    assert result.startswith('\033[38;2;')


def run_tests():
    """Run all color conversion tests with visual examples."""
    import traceback
    
    test_classes = [
        TestColorConverter,
        TestGlobalColorConverter,
        TestColorConversionEdgeCases,
        TestColorConversionPerformance
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("🧪 Running Color Conversion Test Suite...")
    print("=" * 80)
    
    # Show visual examples first
    print("\n🎨 VISUAL EXAMPLES")
    print("-" * 50)
    
    # Example 1: Named colors
    print("🌈 Named Color Conversions")
    named_colors = ['red', 'green', 'blue', 'yellow', 'magenta', 'cyan']
    
    for color in named_colors:
        fg_ansi = _to_ansi_fg(color)
        bg_ansi = _to_ansi_bg(color)
        html_norm = _normalize_for_html(color)
        
        print(f"  {color:8} → FG: {repr(fg_ansi):15} BG: {repr(bg_ansi):15} HTML: {html_norm}")
        # Show actual colored output if terminal supports it
        print(f"           → {fg_ansi}Foreground{chr(27)}[0m  {bg_ansi}Background{chr(27)}[0m")
    
    # Example 2: Hex colors
    print(f"\n🔢 Hex Color Conversions")
    hex_colors = ['#fff', '#000', '#ff0000', '#00ff00', '#0000ff', '#ffff00']
    
    for hex_color in hex_colors:
        if _is_valid_color(hex_color):
            fg_ansi = _to_ansi_fg(hex_color)
            bg_ansi = _to_ansi_bg(hex_color)
            html_norm = _normalize_for_html(hex_color)
            
            print(f"  {hex_color:8} → FG: {repr(fg_ansi):20} HTML: {html_norm}")
            print(f"           → {fg_ansi}Sample Text{chr(27)}[0m  {bg_ansi}Background{chr(27)}[0m")
    
    # Example 3: RGB colors
    print(f"\n🎯 RGB Color Conversions")
    rgb_colors = ['rgb(255, 0, 0)', 'rgb(0, 255, 0)', 'rgb(0, 0, 255)', 'rgb(255, 255, 0)']
    
    for rgb_color in rgb_colors:
        if _is_valid_color(rgb_color):
            fg_ansi = _to_ansi_fg(rgb_color)
            html_norm = _normalize_for_html(rgb_color)
            
            print(f"  {rgb_color:16} → {repr(fg_ansi):20}")
            print(f"  {' ':16} → HTML: {html_norm}")
            print(f"  {' ':16} → {fg_ansi}Sample Text{chr(27)}[0m")
    
    # Example 4: Color validation
    print(f"\n✅ Color Validation Examples")
    test_colors = [
        'red',           # Valid named
        'invalid_color', # Invalid named
        '#ff0000',       # Valid hex
        '#gggggg',       # Invalid hex
        'rgb(255, 0, 0)', # Valid RGB
        'rgb(300, 0, 0)', # Invalid RGB (out of range)
        '',              # Empty
        '#fff',          # Valid short hex
    ]
    
    for color in test_colors:
        is_valid = _is_valid_color(color)
        info = _get_color_info(color)
        status = "✅" if is_valid else "❌"
        print(f"  {status} {color:16} → Valid: {is_valid:5} Type: {info['color_type']:8}")
    
    # Example 5: HTML normalization comparison
    print(f"\n🌐 HTML Normalization")
    html_test_colors = ['red', '#abc', '#ABCDEF', 'rgb(255,128,0)', 'rgb(255, 128, 0)']
    
    for color in html_test_colors:
        if _is_valid_color(color):
            normalized = _normalize_for_html(color)
            print(f"  {color:18} → {normalized}")
    
    # Example 6: Named colors list
    print(f"\n📋 Available Named Colors")
    all_named = _get_named_colors()
    print(f"  Total: {len(all_named)} colors")
    colors_per_line = 6
    named_list = sorted(list(all_named))
    
    for i in range(0, len(named_list), colors_per_line):
        line_colors = named_list[i:i+colors_per_line]
        # Show colors with actual coloring
        colored_output = "  "
        for color in line_colors:
            ansi_code = _to_ansi_fg(color)
            colored_output += f"{ansi_code}{color:12}{chr(27)}[0m"
        print(colored_output)
    
    # Example 7: Complex color info
    print(f"\n📊 Detailed Color Information")
    detail_colors = ['red', '#ff0000', 'rgb(255, 0, 0)']
    
    for color in detail_colors:
        info = _get_color_info(color)
        print(f"\n  Color: {color}")
        for key, value in info.items():
            # Display ANSI codes as strings, not interpreted colors
            if key in ['ansi_fg', 'ansi_bg'] and isinstance(value, str) and '\033[' in value:
                print(f"    {key:15}: {repr(value)}")
            else:
                print(f"    {key:15}: {value}")
    
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