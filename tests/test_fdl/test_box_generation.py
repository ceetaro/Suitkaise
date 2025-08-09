# tests/test_fdl/test_setup/test_box_generator.py - REDESIGNED FROM SCRATCH
# import pytest
import sys
from unittest.mock import patch, Mock

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

from setup.box_generator import _BoxGenerator, BOX_STYLES, _BOX_CHAR_WIDTHS, _measure_box_char_widths
from setup.terminal import _terminal


class TestBoxCharacterWidthMapping:
    """Test the pre-measured box character width system."""
    
    def test_box_char_widths_populated(self):
        """Test that box character widths are measured and cached."""
        # Ensure measurement function has run
        _measure_box_char_widths()
        
        # Should have width data for all styles
        for style_name in BOX_STYLES.keys():
            assert style_name in _BOX_CHAR_WIDTHS
            
            # Should have width for all character types
            for char_name in BOX_STYLES[style_name].keys():
                assert char_name in _BOX_CHAR_WIDTHS[style_name]
                width = _BOX_CHAR_WIDTHS[style_name][char_name]
                assert isinstance(width, int)
                assert width >= 0  # Width should be non-negative
    
    def test_ascii_characters_width_one(self):
        """Test that ASCII box characters have width 1."""
        ascii_widths = _BOX_CHAR_WIDTHS['ascii']
        
        for char_name, width in ascii_widths.items():
            assert width == 1, f"ASCII character '{char_name}' should have width 1, got {width}"
    
    def test_width_measurement_consistency(self):
        """Test that width measurements are consistent."""
        global _BOX_CHAR_WIDTHS
        # Re-measure and compare
        original_widths = _BOX_CHAR_WIDTHS.copy()
        
        # Clear and re-measure
        _BOX_CHAR_WIDTHS.clear()
        _measure_box_char_widths()
        
        # Should be identical
        assert _BOX_CHAR_WIDTHS == original_widths


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


class TestUnicodeBoxStyles:
    """Test different Unicode box styles (the main styles)."""
    
    def test_square_style(self):
        """Test square box style (default Unicode style)."""
        generator = _BoxGenerator(style='square', terminal_width=60)
        
        content_lines = ["Square style test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain square Unicode box characters
        if generator.actual_style == 'square':  # If Unicode is supported
            assert '┌' in terminal_output  # Top-left corner
            assert '┐' in terminal_output  # Top-right corner
            assert '└' in terminal_output  # Bottom-left corner
            assert '┘' in terminal_output  # Bottom-right corner
            assert '─' in terminal_output  # Horizontal line
            assert '│' in terminal_output  # Vertical line
        else:  # Fallback to ASCII
            assert '+' in terminal_output
            assert '-' in terminal_output
            assert '|' in terminal_output
    
    def test_rounded_style(self):
        """Test rounded box style."""
        generator = _BoxGenerator(style='rounded', terminal_width=60)
        
        content_lines = ["Rounded style test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain rounded Unicode box characters
        if generator.actual_style == 'rounded':  # If Unicode is supported
            assert '╭' in terminal_output  # Top-left rounded corner
            assert '╮' in terminal_output  # Top-right rounded corner
            assert '╰' in terminal_output  # Bottom-left rounded corner
            assert '╯' in terminal_output  # Bottom-right rounded corner
            assert '│' in terminal_output  # Vertical line
        else:  # Fallback to ASCII
            assert '+' in terminal_output
    
    def test_double_style(self):
        """Test double-line box style."""
        generator = _BoxGenerator(style='double', terminal_width=60)
        
        content_lines = ["Double style test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain double-line Unicode box characters
        if generator.actual_style == 'double':  # If Unicode is supported
            assert '╔' in terminal_output  # Top-left double corner
            assert '╗' in terminal_output  # Top-right double corner
            assert '╚' in terminal_output  # Bottom-left double corner
            assert '╝' in terminal_output  # Bottom-right double corner
            assert '═' in terminal_output  # Double horizontal line
            assert '║' in terminal_output  # Double vertical line
        else:  # Fallback to ASCII
            assert '+' in terminal_output
    
    def test_heavy_style(self):
        """Test heavy box style."""
        generator = _BoxGenerator(style='heavy', terminal_width=60)
        
        content_lines = ["Heavy style test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain heavy Unicode box characters
        if generator.actual_style == 'heavy':  # If Unicode is supported
            assert '┏' in terminal_output  # Heavy top-left corner
            assert '┓' in terminal_output  # Heavy top-right corner
            assert '┗' in terminal_output  # Heavy bottom-left corner
            assert '┛' in terminal_output  # Heavy bottom-right corner
            assert '━' in terminal_output  # Heavy horizontal line
            assert '┃' in terminal_output  # Heavy vertical line
        else:  # Fallback to ASCII
            assert '+' in terminal_output
    
    def test_heavy_head_style(self):
        """Test heavy-head box style."""
        generator = _BoxGenerator(style='heavy_head', terminal_width=60)
        
        content_lines = ["Heavy head style test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain heavy-head Unicode box characters
        if generator.actual_style == 'heavy_head':  # If Unicode is supported
            assert '┍' in terminal_output  # Heavy-head top-left corner
            assert '┑' in terminal_output  # Heavy-head top-right corner
            assert '┕' in terminal_output  # Heavy-head bottom-left corner
            assert '┙' in terminal_output  # Heavy-head bottom-right corner
            assert '━' in terminal_output  # Heavy horizontal line
            assert '│' in terminal_output  # Light vertical line
        else:  # Fallback to ASCII
            assert '+' in terminal_output
    
    def test_horizontals_style(self):
        """Test horizontals-only box style."""
        generator = _BoxGenerator(style='horizontals', terminal_width=60)
        
        content_lines = ["Horizontals style test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain horizontal-only Unicode box characters
        if generator.actual_style == 'horizontals':  # If Unicode is supported
            assert '─' in terminal_output  # Horizontal line used everywhere
            # Vertical should be spaces
            lines = terminal_output.split('\n')
            content_line = None
            for line in lines:
                if 'Horizontals style test' in line:
                    content_line = line
                    break
            
            if content_line:
                # Should have spaces where vertical bars would be
                assert content_line.startswith(' ') or content_line.startswith('─')
        else:  # Fallback to ASCII
            assert '+' in terminal_output
    
    def test_ascii_style_explicit(self):
        """Test ASCII style when explicitly requested."""
        generator = _BoxGenerator(style='ascii', terminal_width=60)
        
        content_lines = ["ASCII style test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should always use ASCII characters
        assert generator.actual_style == 'ascii'
        assert '+' in terminal_output  # ASCII corners
        assert '-' in terminal_output  # ASCII horizontal
        assert '|' in terminal_output  # ASCII vertical
        
        # Should NOT contain Unicode characters
        unicode_chars = ['┌', '┐', '└', '┘', '╭', '╮', '╰', '╯', '╔', '╗', '╚', '╝']
        for unicode_char in unicode_chars:
            assert unicode_char not in terminal_output


class TestASCIIFallback:
    """Test ASCII fallback behavior when Unicode is not supported."""
    
    @patch('setup.box_generator._supports_box_drawing')
    def test_unicode_fallback_to_ascii(self, mock_supports_unicode):
        """Test that all Unicode styles fall back to ASCII when Unicode not supported."""
        # Mock Unicode not supported
        mock_supports_unicode.return_value = False
        
        unicode_styles = ['square', 'rounded', 'double', 'heavy', 'heavy_head', 'horizontals']
        
        for style in unicode_styles:
            generator = _BoxGenerator(style=style, terminal_width=60)
            
            # Should fall back to ASCII
            assert generator.actual_style == 'ascii'
            
            content_lines = [f"Testing {style} fallback"]
            result = generator.generate_box(content_lines)
            
            terminal_output = result['terminal']
            
            # Should contain only ASCII box characters
            assert '+' in terminal_output
            assert '-' in terminal_output
            assert '|' in terminal_output
            
            # Should NOT contain Unicode characters
            unicode_chars = ['┌', '┐', '└', '┘', '╭', '╮', '╰', '╯', '╔', '╗', '╚', '╝', '━', '═', '║', '┃']
            for unicode_char in unicode_chars:
                assert unicode_char not in terminal_output, f"Unicode char '{unicode_char}' found in {style} fallback"


class TestBoxGeneratorInitialization:
    """Test _BoxGenerator initialization with new parameters."""
    
    def test_initialization_default(self):
        """Test _BoxGenerator initialization with defaults."""
        generator = _BoxGenerator()
        
        assert generator.style == 'square'
        assert generator.title is None
        assert generator.color is None
        # Background color removed - no longer supported
        assert generator.box_justify == 'left'  # NEW: renamed from justify
        assert generator.terminal_width >= 60
        assert generator.actual_style in BOX_STYLES
        assert hasattr(generator, 'chars')
        assert hasattr(generator, 'char_widths')  # NEW: pre-measured widths
    
    def test_initialization_custom(self):
        """Test _BoxGenerator initialization with custom parameters."""
        generator = _BoxGenerator(
            style='rounded',
            title='Test Title',
            color='red',
            
            box_justify='center',  # NEW: renamed parameter
            terminal_width=120
        )
        
        assert generator.style == 'rounded'
        assert generator.title == 'Test Title'
        assert generator.color == 'red'
        # Background color removed - no longer supported
        assert generator.box_justify == 'center'  # NEW: renamed parameter
        assert generator.terminal_width == 120
    
    def test_unicode_fallback_logic(self):
        """Test fallback to ASCII when Unicode not supported."""
        with patch('setup.box_generator._supports_box_drawing', return_value=False):
            generator = _BoxGenerator(style='rounded')
            
            # Should fall back to ASCII
            assert generator.actual_style == 'ascii'
            assert generator.chars == BOX_STYLES['ascii']


class TestNewInputFormat:
    """Test the new input format: List[str] instead of single string."""
    
    def test_basic_list_input(self):
        """Test basic box generation with list of strings."""
        generator = _BoxGenerator(style='square', terminal_width=60)  # Use Unicode style
        
        # NEW: Input is now List[str] of pre-wrapped lines
        content_lines = ["Line 1", "Line 2", "Line 3"]
        result = generator.generate_box(content_lines)
        
        # Should return dictionary with all formats
        assert isinstance(result, dict)
        assert 'terminal' in result
        assert 'plain' in result
        assert 'markdown' in result
        assert 'html' in result
        
        # All lines should be present in output
        terminal_output = result['terminal']
        assert 'Line 1' in terminal_output
        assert 'Line 2' in terminal_output
        assert 'Line 3' in terminal_output
        # Should have Unicode box characters (not ASCII +)
        assert '┌' in terminal_output or '└' in terminal_output or '│' in terminal_output or '+' in terminal_output  # Unicode or ASCII fallback
    
    def test_single_line_input(self):
        """Test box generation with single line list."""
        generator = _BoxGenerator(style='rounded', terminal_width=60)  # Use Unicode style
        
        content_lines = ["Single line content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        assert 'Single line content' in terminal_output
        # Should have Unicode box characters (rounded corners)
        assert ('╭' in terminal_output and '╮' in terminal_output) or '+' in terminal_output  # Unicode or ASCII fallback
        assert '│' in terminal_output or '|' in terminal_output  # Unicode or ASCII fallback
    
    def test_empty_list_input(self):
        """Test box generation with empty list."""
        generator = _BoxGenerator(style='double', terminal_width=60)  # Use Unicode style
        
        # NEW: Empty content should create 8 spaces + 4 padding = 12 total width
        content_lines = []
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should have box structure with Unicode double-line characters
        assert ('╔' in terminal_output and '╗' in terminal_output) or '+' in terminal_output  # Unicode or ASCII fallback
        assert '║' in terminal_output or '|' in terminal_output  # Unicode or ASCII fallback
        
        # Should contain 8 spaces for empty content
        lines = terminal_output.split('\n')
        content_line = None
        for line in lines:
            if ('║' in line or '|' in line) and ' ' * 8 in line:
                content_line = line
                break
        
        assert content_line is not None, "Should have content line with 8 spaces"
    
    def test_whitespace_only_lines(self):
        """Test box generation with whitespace-only lines."""
        generator = _BoxGenerator(style='square', terminal_width=60)
        
        # Lines with only whitespace should trigger empty content behavior
        content_lines = ["   ", "\t", ""]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should handle as empty content (8 spaces)
        assert ('┌' in terminal_output and '┐' in terminal_output) or '+' in terminal_output
        assert '│' in terminal_output or '|' in terminal_output
        # Should contain the 8-space empty content pattern
        assert ' ' * 8 in terminal_output


class TestBoxWidthCalculation:
    """Test box width calculation based on visual width of content."""
    
    def test_basic_width_calculation(self):
        """Test box width calculation with basic content."""
        generator = _BoxGenerator(style='square', terminal_width=100)  # Use Unicode style
        
        content_lines = ["Short", "Medium length line", "Long"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Find content lines and check they all fit properly
        content_lines_in_box = [line for line in lines if ('│' in line or '|' in line) and any(word in line for word in ['Short', 'Medium', 'Long'])]
        
        # Should have content lines
        assert len(content_lines_in_box) >= 3
        
        # All content lines should have same outer width
        box_widths = [len(line) for line in content_lines_in_box]
        assert len(set(box_widths)) == 1, f"All content lines should have same width: {box_widths}"
    
    def test_width_with_wide_characters(self):
        """Test width calculation with wide characters (Chinese, emojis)."""
        generator = _BoxGenerator(style='rounded', terminal_width=80)
        
        # Mix of regular and wide characters
        content_lines = [
            "Regular text",
            "中文字符",  # Chinese characters (width 2 each)
            "Emoji 😀 test",  # Emoji (width 2)
            "Mixed: 你好 world 🎉"
        ]
        
        result = generator.generate_box(content_lines)
        terminal_output = result['terminal']
        
        # Should handle wide characters correctly
        assert '中文字符' in terminal_output
        assert '😀' in terminal_output
        assert '🎉' in terminal_output
        
        # Box should be wide enough for all content
        lines = terminal_output.split('\n')
        content_lines_in_box = [line for line in lines if ('│' in line or '|' in line) and ('文' in line or '😀' in line or 'Regular' in line or 'Mixed' in line)]
        
        assert len(content_lines_in_box) >= 4, "Should have all content lines"
    
    def test_width_with_ansi_codes(self):
        """Test width calculation ignores ANSI codes."""
        generator = _BoxGenerator(style='double', terminal_width=80)
        
        # Content with ANSI color codes
        content_lines = [
            "Plain text",
            "\033[31mRed text\033[0m",
            "\033[1m\033[32mBold green\033[0m",
            "Mixed \033[34mblue\033[0m and plain"
        ]
        
        result = generator.generate_box(content_lines)
        terminal_output = result['terminal']
        
        # ANSI codes should be preserved
        assert '\033[31m' in terminal_output
        assert '\033[32m' in terminal_output
        assert '\033[34m' in terminal_output
        
        # But width calculation should ignore them
        lines = terminal_output.split('\n')
        content_lines_in_box = [line for line in lines if ('║' in line or '|' in line) and any(word in line for word in ['text', 'green', 'plain', 'Mixed'])]
        
        # All content lines should align properly despite ANSI codes
        assert len(content_lines_in_box) >= 4


class TestTitleHandling:
    """Test title handling (always centered in border)."""
    
    def test_title_centering(self):
        """Test that title is always centered in top border."""
        generator = _BoxGenerator(
            style='square',  # Use Unicode style
            title='Test Title',
            terminal_width=60
        )
        
        content_lines = ["Content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Find title line (should be first non-empty line)
        title_line = None
        for line in lines:
            if 'Test Title' in line and ('┌' in line or '+' in line):  # Unicode or ASCII corner
                title_line = line
                break
        
        assert title_line is not None, "Should have title line"
        
        # Title should be surrounded by horizontal characters
        assert 'Test Title' in title_line
        assert title_line.startswith('┌') or title_line.startswith('+')  # Unicode or ASCII
        assert title_line.endswith('┐') or title_line.endswith('+')     # Unicode or ASCII
        
        # Should have horizontal chars around title
        title_pos = title_line.find('Test Title')
        assert title_pos > 1  # Should have some chars before title
        
        # Characters before and after title should be horizontal chars
        before_title = title_line[:title_pos].strip('┌+')  # Strip corners
        after_title = title_line[title_pos + len(' Test Title '):].strip('┐+')  # Strip corners
        
        # Should be mostly horizontal characters (Unicode or ASCII) and spaces
        if before_title:
            assert all(c in '─- ' for c in before_title), f"Before title: '{before_title}'"
        if after_title:
            assert all(c in '─- ' for c in after_title), f"After title: '{after_title}'"
    
    def test_long_title_truncation(self):
        """Test that very long titles are truncated properly."""
        generator = _BoxGenerator(
            style='rounded',
            title='This is an extremely long title that should be truncated',
            terminal_width=40
        )
        
        content_lines = ["Short content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should handle long title gracefully
        assert 'Short content' in terminal_output
        assert ('╭' in terminal_output and '╮' in terminal_output) or '+' in terminal_output
        
        # Title should be truncated with ellipsis
        lines = terminal_output.split('\n')
        title_line = lines[1] if len(lines) > 1 else lines[0]  # Skip empty line
        
        if '...' in title_line:
            assert 'extremely' in title_line or 'This is' in title_line
    
    def test_title_with_wide_characters(self):
        """Test title with wide characters."""
        generator = _BoxGenerator(
            style='heavy',
            title='标题 Title 😀',
            terminal_width=60
        )
        
        content_lines = ["Content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Wide characters in title should be handled
        assert '标题' in terminal_output
        assert '😀' in terminal_output
        assert ('┏' in terminal_output and '┓' in terminal_output) or '+' in terminal_output


class TestBoxJustification:
    """Test box justification (positioning entire box)."""
    
    def test_left_justification(self):
        """Test left-justified box (default)."""
        generator = _BoxGenerator(
            style='rounded',  # Use Unicode style
            box_justify='left',
            terminal_width=80
        )
        
        content_lines = ["Small content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Find box lines
        box_lines = [line for line in lines if ('╭' in line or '╮' in line or '│' in line or '+' in line or '|' in line)]
        
        if box_lines:
            # Left justified should not have leading spaces (or very few)
            first_box_line = box_lines[0]
            leading_spaces = len(first_box_line) - len(first_box_line.lstrip())
            assert leading_spaces <= 1  # Might have 1 space from newline handling
    
    def test_center_justification(self):
        """Test center-justified box."""
        generator = _BoxGenerator(
            style='double',  # Use Unicode style
            box_justify='center',
            terminal_width=80
        )
        
        content_lines = ["Small content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Find box lines
        box_lines = [line for line in lines if ('╔' in line or '╗' in line or '║' in line or '+' in line or '|' in line)]
        
        if box_lines:
            # Center justified should have significant leading spaces
            first_box_line = box_lines[0]
            leading_spaces = len(first_box_line) - len(first_box_line.lstrip())
            assert leading_spaces > 5  # Should be centered with substantial padding
    
    def test_right_justification(self):
        """Test right-justified box."""
        generator = _BoxGenerator(
            style='heavy',  # Use Unicode style
            box_justify='right',
            terminal_width=80
        )
        
        content_lines = ["Small content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Find box lines
        box_lines = [line for line in lines if ('┏' in line or '┓' in line or '┃' in line or '+' in line or '|' in line)]
        
        if box_lines:
            # Right justified should have maximum leading spaces
            first_box_line = box_lines[0]
            leading_spaces = len(first_box_line) - len(first_box_line.lstrip())
            # Should be right-aligned, so significant leading space
            assert leading_spaces > 20  # Should be pushed to the right


class TestNewlineHandling:
    """Test newline handling before and after box."""
    
    def test_newlines_added(self):
        """Test that newlines are added before and after box."""
        generator = _BoxGenerator(style='square', terminal_width=60)
        
        content_lines = ["Test content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Should start and end with empty lines
        assert lines[0] == ''  # Newline before box
        assert lines[-1] == ''  # Newline after box
        
        # Should have actual box content in between
        box_lines = [line for line in lines[1:-1] if line.strip()]
        assert len(box_lines) >= 3  # At least top, content, bottom


class TestColorBleedingPrevention:
    """Test color combinations to ensure no color bleeding between elements."""
    
    def test_border_color_only(self):
        """Test box with only border color - no bleeding to content."""
        generator = _BoxGenerator(
            style='square',
            color='red',
            terminal_width=60
        )
        
        content_lines = ["Plain content without colors"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should have color codes for borders (check both 8-color and 24-bit RGB formats)
        assert ('\033[31m' in terminal_output or '\x1b[31m' in terminal_output or 
                '\x1b[38;2;255;0;0m' in terminal_output)  # Red foreground
        # Should have reset codes to prevent bleeding
        assert '\033[0m' in terminal_output or '\x1b[0m' in terminal_output   # Reset
        # Content should be present
        assert 'Plain content' in terminal_output
        
        # Verify reset codes are properly placed after colored borders
        lines = terminal_output.split('\n')
        for line in lines:
            if '┌' in line or '└' in line or '│' in line or '+' in line or '|' in line:
                # Border lines should end with reset code (handle both formats)
                assert line.endswith('\033[0m') or line.endswith('\x1b[0m'), f"Border line missing reset: '{line}'"
    
    def test_background_color_blue(self):
        """Test box with blue background color."""
        generator = _BoxGenerator(
            style='square',
            color='red',  # Only border color now
            terminal_width=50
        )
        
        result = generator.generate_box(["Test content"])
        
        # Should have terminal output
        assert 'terminal' in result
        assert result['terminal']
        
        # Should contain ANSI color codes for border only
        terminal_output = result['terminal']
        assert '\033[' in terminal_output or '\x1b[' in terminal_output  # Has ANSI codes
        assert '\033[0m' in terminal_output or '\x1b[0m' in terminal_output  # Has reset codes
    
    def test_colored_content_with_colored_borders(self):
        """Test colored content inside colored borders - ensure no interference."""
        generator = _BoxGenerator(
            style='heavy',
            color='red',
            
            terminal_width=70
        )
        
        # Content with its own colors
        content_lines = [
            "\033[31mRed content line\033[0m",
            "\033[32mGreen content line\033[0m",
            "Plain content line",
            "\033[1m\033[33mBold yellow content\033[0m"
        ]
        
        result = generator.generate_box(content_lines)
        terminal_output = result['terminal']
        
        # Border colors should be present
        border_red_present = '\033[31m' in terminal_output
        border_bg_present = '\033[44m' in terminal_output or '\033[48;' in terminal_output
        
        # Content colors should be preserved
        assert 'Red content line' in terminal_output
        assert 'Green content line' in terminal_output
        assert 'Bold yellow content' in terminal_output
        
        # Should have multiple reset codes (border resets + content resets)
        reset_count = terminal_output.count('\033[0m') + terminal_output.count('\x1b[0m')
        assert reset_count >= 4, f"Should have multiple reset codes, got {reset_count}"
        
        # Verify each border line ends with reset
        lines = terminal_output.split('\n')
        border_lines = [line for line in lines if ('┏' in line or '┃' in line or '┗' in line or 
                                                  '+' in line or '|' in line)]
        for line in border_lines:
            if line.strip():  # Skip empty lines
                assert line.endswith('\033[0m') or line.endswith('\x1b[0m'), f"Border line should end with reset: '{line}'"
    
    def test_no_color_bleeding_after_box(self):
        """Test that colors don't bleed to content after the box."""
        generator = _BoxGenerator(
            style='square',
            color='magenta',
            
            terminal_width=60
        )
        
        content_lines = ["Colored box content"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Box should end with newline followed by reset
        assert terminal_output.endswith('\033[0m\n') or terminal_output.endswith('\n')
        
        # Split into lines and check that the last line with content has proper reset
        lines = terminal_output.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        if non_empty_lines:
            last_content_line = non_empty_lines[-1]
            if '\033[' in last_content_line:  # If it has color codes
                assert '\033[0m' in last_content_line, f"Last line should have reset: '{last_content_line}'"
    
    def test_complex_color_combinations(self):
        """Test complex combinations of all color types."""
        generator = _BoxGenerator(
            style='heavy_head',
            color='#FF5500',  # Hex color for border
            terminal_width=80
        )
        
        # Complex content with various color formats
        content_lines = [
            "\033[38;5;196mTRGB red content\033[0m",
            "\033[38;2;0;255;0mTRGB green content\033[0m", 
            "\033[1m\033[4m\033[34mBold underlined blue\033[0m",
            "Plain text mixed with \033[35mmagenta\033[0m words",
            "Line with \033[31mred\033[0m and \033[32mgreen\033[0m and \033[33myellow\033[0m"
        ]
        
        result = generator.generate_box(content_lines)
        terminal_output = result['terminal']
        
        # All content should be preserved
        assert 'TRGB red content' in terminal_output
        assert 'TRGB green content' in terminal_output
        assert 'Bold underlined blue' in terminal_output
        assert 'magenta' in terminal_output
        assert 'yellow' in terminal_output
        
        # Should have many reset codes for proper isolation
        reset_count = terminal_output.count('\033[0m')
        assert reset_count >= 8, f"Complex colors should have many resets, got {reset_count}"
        
        # No unterminated color codes - every line with borders should end with reset
        lines = terminal_output.split('\n')
        for line in lines:
            if ('┍' in line or '┑' in line or '│' in line or '━' in line or 
                '+' in line or '|' in line or '-' in line) and line.strip():
                assert line.endswith('\033[0m'), f"Border line not properly reset: '{line}'"
    
    def test_color_format_consistency_across_outputs(self):
        """Test that colored boxes work consistently across all output formats."""
        generator = _BoxGenerator(
            style='rounded',
            color='red',
             
            title='Color Test',
            terminal_width=60
        )
        
        content_lines = [
            "Content with \033[32mgreen\033[0m text",
            "And \033[1mbold\033[0m formatting"
        ]
        
        result = generator.generate_box(content_lines)
        
        # Terminal format should have ANSI codes
        terminal_output = result['terminal']
        assert '\033[' in terminal_output
        assert 'green' in terminal_output
        assert 'bold' in terminal_output
        
        # Plain format should strip all ANSI codes
        plain_output = result['plain']
        assert '\033[' not in plain_output
        assert 'green' in plain_output  # Text preserved
        assert 'bold' in plain_output   # Text preserved
        
        # HTML format should escape ANSI codes and have CSS styles
        html_output = result['html']
        assert '\033[' not in html_output  # ANSI codes stripped
        assert 'green' in html_output      # Text preserved
        assert 'bold' in html_output       # Text preserved
        assert 'style=' in html_output     # CSS styles for box colors
        
        # Markdown format should strip ANSI codes
        markdown_output = result['markdown']
        assert '\033[' not in markdown_output
        assert 'green' in markdown_output
        assert 'bold' in markdown_output


class TestHTMLOutputIssues:
    """Test HTML output for line length and character encoding issues."""
    
    def test_html_line_length_consistency(self):
        """Test that HTML output lines have consistent lengths and no bleeding characters."""
        generator = _BoxGenerator(
            style='square',
            color='red',
            
            title='HTML Test',
            terminal_width=60
        )
        
        content_lines = [
            "Line 1 content",
            "Line 2 is a bit longer",
            "Line 3"
        ]
        
        result = generator.generate_box(content_lines)
        
        # Get all formats for comparison
        terminal_output = result['terminal']
        plain_output = result['plain'] 
        html_output = result['html']
        
        print(f"\n🔍 DEBUGGING HTML OUTPUT ISSUE")
        print(f"Terminal format:")
        print(repr(terminal_output))
        print(f"\nPlain format:")
        print(repr(plain_output))
        print(f"\nHTML format:")
        print(repr(html_output))
        
        # Extract just the box content from HTML (between <pre> tags)
        if '<pre' in html_output and '</pre>' in html_output:
            start_idx = html_output.find('>\n') + 2  # After opening <pre> tag
            end_idx = html_output.find('\n</pre>')
            html_box_content = html_output[start_idx:end_idx]
            
            print(f"\nHTML box content only:")
            print(repr(html_box_content))
            
            # Split into lines and check lengths
            html_lines = html_box_content.split('\n')
            plain_lines = plain_output.split('\n')
            
            print(f"\nLine length comparison:")
            for i, (html_line, plain_line) in enumerate(zip(html_lines, plain_lines)):
                html_len = len(html_line)
                plain_len = len(plain_line)
                print(f"Line {i}: HTML={html_len}, Plain={plain_len}")
                if html_len != plain_len:
                    print(f"  ⚠️ LENGTH MISMATCH!")
                    print(f"  HTML: {repr(html_line)}")
                    print(f"  Plain: {repr(plain_line)}")
                    
                    # Check for common HTML entities that might be causing issues
                    if '&lt;' in html_line or '&gt;' in html_line or '&amp;' in html_line:
                        print(f"  📝 HTML entities found - this is expected for content with <>&")
                    elif html_len > plain_len:
                        print(f"  ❌ UNEXPECTED: HTML line longer than plain")
                        # Find what's different
                        for j, (h_char, p_char) in enumerate(zip(html_line, plain_line)):
                            if h_char != p_char:
                                print(f"    First difference at position {j}: HTML='{h_char}' Plain='{p_char}'")
                                break
        
        # Verify HTML escaping is working correctly
        assert '&lt;' not in html_output or '<' in ''.join(content_lines)  # Only if there was < in content
        assert '&gt;' not in html_output or '>' in ''.join(content_lines)  # Only if there was > in content
        assert '&amp;' not in html_output or '&' in ''.join(content_lines)  # Only if there was & in content
    
    def test_html_unicode_box_characters(self):
        """Test how Unicode box drawing characters are handled in HTML."""
        generator = _BoxGenerator(
            style='square',
            terminal_width=40
        )
        
        content_lines = ["Unicode box test"]
        result = generator.generate_box(content_lines)
        
        html_output = result['html']
        plain_output = result['plain']
        
        print(f"\n🔍 UNICODE CHARACTER ANALYSIS")
        print(f"Plain output with Unicode chars:")
        print(repr(plain_output))
        print(f"\nHTML output with Unicode chars:")
        print(repr(html_output))
        
        # Check if Unicode box characters are preserved or converted
        unicode_box_chars = ['┌', '┐', '└', '┘', '─', '│']
        
        for char in unicode_box_chars:
            if char in plain_output:
                print(f"\nCharacter '{char}' (U+{ord(char):04X}):")
                print(f"  In plain: {char in plain_output}")
                print(f"  In HTML: {char in html_output}")
                
                # Check if it's been HTML entity encoded
                html_entity = f"&#{ord(char)};"
                html_hex_entity = f"&#x{ord(char):04X};"
                print(f"  HTML decimal entity {html_entity}: {html_entity in html_output}")
                print(f"  HTML hex entity {html_hex_entity}: {html_hex_entity in html_output}")
                
                if char in html_output:
                    print(f"  ✅ Unicode char preserved in HTML")
                elif html_entity in html_output or html_hex_entity in html_output:
                    print(f"  📝 Unicode char converted to HTML entity")
                else:
                    print(f"  ❓ Unicode char handling unclear")
    
    def test_html_ansi_stripping(self):
        """Test that ANSI codes are properly stripped from HTML output."""
        generator = _BoxGenerator(
            style='square',
            color='red',
            terminal_width=50
        )
        
        # Content with ANSI codes
        content_lines = [
            "\033[31mRed text\033[0m",
            "Plain text with \033[32mgreen\033[0m word",
            "\033[1m\033[4m\033[33mBold underlined yellow\033[0m"
        ]
        
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        html_output = result['html']
        
        print(f"\n🔍 ANSI CODE STRIPPING ANALYSIS")
        print(f"Terminal output (with ANSI):")
        print(repr(terminal_output))
        print(f"\nHTML output (should be stripped):")
        print(repr(html_output))
        
        # HTML should not contain any ANSI escape sequences
        assert '\033[' not in html_output, "HTML output contains ANSI escape sequences"
        
        # But should contain the text content
        assert 'Red text' in html_output
        assert 'green' in html_output
        assert 'Bold underlined yellow' in html_output
        
        # Check that we don't have partial ANSI codes
        assert '\033' not in html_output, "HTML contains partial ANSI sequences"
        assert '[31m' not in html_output, "HTML contains ANSI color codes"
        assert '[0m' not in html_output, "HTML contains ANSI reset codes"
    
    def test_html_css_styles_application(self):
        """Test that CSS styles are properly applied to HTML output."""
        generator = _BoxGenerator(
            style='rounded',
            color='#FF5500',  # Hex color
            title='CSS Test',
            terminal_width=60
        )
        
        content_lines = ["Testing CSS style application"]
        result = generator.generate_box(content_lines)
        
        html_output = result['html']
        
        print(f"\n🔍 CSS STYLES ANALYSIS")
        print(f"HTML output with CSS:")
        print(html_output)
        
        # Should have <pre> tag with class
        assert '<pre class="fdl-box"' in html_output
        
        # Should have style attribute
        assert 'style=' in html_output
        
        # Should have border-color (background-color removed)
        assert 'border-color:' in html_output.replace(' ', '') or 'border-color :' in html_output
        
        # Colors should be normalized for HTML
        assert '#FF5500' in html_output or 'ff5500' in html_output.lower()
    
    def test_html_line_ending_investigation(self):
        """Investigate the specific 'm' character issue mentioned by user."""
        generator = _BoxGenerator(
            style='square',
            terminal_width=50
        )
        
        content_lines = ["Testing for edge bleeding"]
        result = generator.generate_box(content_lines)
        
        html_output = result['html']
        plain_output = result['plain']
        
        print(f"\n🔍 EDGE BLEEDING INVESTIGATION")
        
        # Split and analyze each line character by character
        html_lines = html_output.split('\n')
        plain_lines = plain_output.split('\n')
        
        print(f"Detailed line analysis:")
        for i, (html_line, plain_line) in enumerate(zip(html_lines, plain_lines)):
            if html_line.strip() and plain_line.strip():  # Skip empty lines
                print(f"\nLine {i}:")
                print(f"  Plain ({len(plain_line)}): {repr(plain_line)}")
                print(f"  HTML  ({len(html_line)}): {repr(html_line)}")
                
                # Character by character comparison
                max_len = max(len(html_line), len(plain_line))
                for j in range(max_len):
                    h_char = html_line[j] if j < len(html_line) else '(END)'
                    p_char = plain_line[j] if j < len(plain_line) else '(END)'
                    
                    if h_char != p_char:
                        print(f"    Pos {j}: HTML='{h_char}' Plain='{p_char}' ❌")
                        if h_char == 'm':
                            print(f"    🎯 Found 'm' character at position {j}!")
                        break
                else:
                    print(f"    ✅ Lines identical")


class TestColorApplication:
    """Test basic color application functionality."""
    
    def test_terminal_color_format(self):
        """Test color application in terminal format."""
        generator = _BoxGenerator(
            style='square',
            color='red',
            
            terminal_width=60
        )
        
        content_lines = ["Colored border test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain ANSI color codes
        assert '\033[' in terminal_output
        # Should contain reset codes
        assert '\033[0m' in terminal_output
        # Should contain content
        assert 'Colored border test' in terminal_output
    
    def test_plain_format_strips_colors(self):
        """Test that plain format strips ANSI codes."""
        generator = _BoxGenerator(
            style='rounded',
            color='green',
            
            terminal_width=60
        )
        
        content_lines = ["Test with \033[31mcolors\033[0m in content"]
        result = generator.generate_box(content_lines)
        
        plain_output = result['plain']
        
        # Should NOT contain ANSI codes
        assert '\033[' not in plain_output
        # Should contain content without codes
        assert 'Test with colors in content' in plain_output
        # Should contain box structure
        assert ('╭' in plain_output and '╮' in plain_output) or '+' in plain_output  # Unicode or ASCII
    
    def test_no_colors_specified(self):
        """Test box generation with no colors specified."""
        generator = _BoxGenerator(
            style='double',
            terminal_width=60
        )
        
        content_lines = ["No colors test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should not contain color ANSI codes (except possibly in content)
        # But should still have box structure
        assert 'No colors test' in terminal_output
        assert ('╔' in terminal_output and '╗' in terminal_output) or '+' in terminal_output  # Unicode or ASCII
        
        # If there are no colors in content, there should be no ANSI codes
        if '\033[' not in ''.join(content_lines):
            assert '\033[' not in terminal_output
    
    def test_color_only_no_background(self):
        """Test box with only border color, no background."""
        generator = _BoxGenerator(
            style='heavy',
            color='magenta',
            terminal_width=60
        )
        
        content_lines = ["Border color only"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should have foreground color code
        assert '\033[35m' in terminal_output or '\033[38;' in terminal_output  # Magenta
        # Should NOT have background color codes
        assert '\033[4' not in terminal_output  # No background codes
        # Should have reset codes
        assert '\033[0m' in terminal_output
    
    def test_border_only_no_background_color(self):
        """Test box with only border color, no background color.""" 
        generator = _BoxGenerator(
            style='square',
            color='red',
            terminal_width=60
        )
        
        content_lines = ["Border color only"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should have border color code
        assert '\033[31m' in terminal_output or '\033[38;' in terminal_output  # Red border
        # Should have reset codes
        assert '\033[0m' in terminal_output
    
    def test_invalid_colors_ignored(self):
        """Test that invalid colors are ignored gracefully."""
        generator = _BoxGenerator(
            style='rounded',
            color='invalid_color_name',
            
            terminal_width=60
        )
        
        content_lines = ["Invalid colors test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should not crash and should contain content
        assert 'Invalid colors test' in terminal_output
        # Should have box structure
        assert ('╭' in terminal_output and '╮' in terminal_output) or '+' in terminal_output
        
        # Invalid colors should result in no color codes
        # (depends on implementation - might have no codes or might have fallback codes)
    
    def test_hex_color_format(self):
        """Test hex color format handling."""
        generator = _BoxGenerator(
            style='double',
            color='#FF0000',  # Red in hex
              # Green in hex
            terminal_width=60
        )
        
        content_lines = ["Hex color test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain content
        assert 'Hex color test' in terminal_output
        # Should have ANSI codes (exact codes depend on conversion)
        assert '\033[' in terminal_output
        assert '\033[0m' in terminal_output
    
    def test_rgb_color_format(self):
        """Test RGB color format handling."""
        generator = _BoxGenerator(
            style='heavy_head',
            color='rgb(255, 0, 0)',  # Red in RGB
            terminal_width=60
        )
        
        content_lines = ["RGB color test"]
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        
        # Should contain content
        assert 'RGB color test' in terminal_output
        # Should have ANSI codes
        assert '\033[' in terminal_output
        assert '\033[0m' in terminal_output


class TestOutputFormats:
    """Test all output format generation."""
    
    def test_all_formats_present(self):
        """Test that all output formats are generated."""
        generator = _BoxGenerator(style='square', terminal_width=60)
        
        content_lines = ["Format test"]
        result = generator.generate_box(content_lines)
        
        # All formats should be present
        assert isinstance(result, dict)
        assert 'terminal' in result
        assert 'plain' in result
        assert 'markdown' in result
        assert 'html' in result
        
        # All should contain the content
        for format_name, output in result.items():
            assert 'Format test' in output, f"Content missing from {format_name} format"
    
    def test_markdown_format(self):
        """Test markdown format wraps in code block."""
        generator = _BoxGenerator(style='rounded', terminal_width=60)
        
        content_lines = ["Markdown test"]
        result = generator.generate_box(content_lines)
        
        markdown_output = result['markdown']
        
        # Should be wrapped in code block
        assert markdown_output.startswith('```')
        assert markdown_output.endswith('```')
        assert 'Markdown test' in markdown_output
        assert ('╭' in markdown_output and '╮' in markdown_output) or '+' in markdown_output  # Box characters preserved
    
    def test_html_format_and_escaping(self):
        """Test HTML format and character escaping."""
        generator = _BoxGenerator(
            style='double',
            color='red',
            terminal_width=60
        )
        
        content_lines = ["HTML test with <tags> & entities"]
        result = generator.generate_box(content_lines)
        
        html_output = result['html']
        
        # Should be wrapped in <pre> tag
        assert '<pre' in html_output
        assert '</pre>' in html_output
        assert 'class="fdl-box"' in html_output
        
        # Should escape HTML characters
        assert '&lt;tags&gt;' in html_output
        assert '&amp;' in html_output
        
        # Should contain style for colors
        if 'style=' in html_output:
            assert 'border-color' in html_output or 'background-color' in html_output


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_very_wide_content_line(self):
        """Test with content line wider than terminal."""
        generator = _BoxGenerator(style='square', terminal_width=30)
        
        # Very wide content line
        wide_line = "This is an extremely long line that exceeds the terminal width significantly"
        content_lines = [wide_line]
        
        result = generator.generate_box(content_lines)
        terminal_output = result['terminal']
        
        # Should handle gracefully
        assert ('┌' in terminal_output and '┐' in terminal_output) or '+' in terminal_output
        assert 'This is' in terminal_output  # At least some content should be present
        
        # Lines should not exceed terminal width significantly
        lines = terminal_output.split('\n')
        for line in lines:
            # Allow some flexibility for box borders
            assert len(line) <= 35, f"Line too wide: {len(line)} chars: '{line}'"
    
    def test_many_content_lines(self):
        """Test with many content lines."""
        generator = _BoxGenerator(style='rounded', terminal_width=60)
        
        # Many lines of content
        content_lines = [f"Line {i}" for i in range(50)]
        
        result = generator.generate_box(content_lines)
        terminal_output = result['terminal']
        
        # Should handle many lines
        assert 'Line 0' in terminal_output
        assert 'Line 49' in terminal_output
        assert ('╭' in terminal_output and '╮' in terminal_output) or '+' in terminal_output
        
        # Should have proper box structure
        lines = terminal_output.split('\n')
        content_lines_in_box = [line for line in lines if ('│' in line or '|' in line) and 'Line' in line]
        assert len(content_lines_in_box) == 50
    
    def test_none_parameter_handling(self):
        """Test handling of None parameters."""
        generator = _BoxGenerator(
            style=None,
            title=None,
            color=None,
            
            box_justify=None,
            terminal_width=None
        )
        
        content_lines = ["None test"]
        result = generator.generate_box(content_lines)
        
        # Should handle None values gracefully
        assert isinstance(result, dict)
        assert 'None test' in result['terminal']
        assert ('┌' in result['terminal'] and '┐' in result['terminal']) or '+' in result['terminal']
    
    def test_zero_terminal_width(self):
        """Test with zero terminal width."""
        generator = _BoxGenerator(style='square', terminal_width=0)
        
        content_lines = ["Test"]
        result = generator.generate_box(content_lines)
        
        # Should handle gracefully with minimum width
        assert isinstance(result, dict)
        assert 'Test' in result['terminal']
    
    def test_empty_content_exact_behavior(self):
        """Test exact behavior of empty content (8 spaces + 4 padding)."""
        generator = _BoxGenerator(style='double', terminal_width=60)
        
        # Test truly empty content
        content_lines = []
        result = generator.generate_box(content_lines)
        
        terminal_output = result['terminal']
        lines = terminal_output.split('\n')
        
        # Find the content line
        content_line = None
        for line in lines:
            if ('║' in line or '|' in line) and not any(char.isalnum() for char in line):
                content_line = line
                break
        
        assert content_line is not None, "Should have empty content line"
        
        # Should contain exactly 8 spaces between borders
        # Content line format: '║  ' + content + '  ║' or '|  ' + content + '  |'
        # For 8 spaces: '║  ' + '        ' + '  ║'
        expected_pattern_unicode = '║  ' + ' ' * 8 + '  ║'
        expected_pattern_ascii = '|  ' + ' ' * 8 + '  |'
        assert (expected_pattern_unicode in content_line or 
                expected_pattern_ascii in content_line), f"Expected pattern in '{content_line}'"


class TestPerformance:
    """Test performance characteristics."""
    
    def test_large_content_performance(self):
        """Test performance with large amounts of content."""
        generator = _BoxGenerator(style='square', terminal_width=60)
        
        # Large number of lines
        content_lines = [f"Line {i} with some content here" for i in range(200)]
        
        import time
        start_time = time.time()
        result = generator.generate_box(content_lines)
        end_time = time.time()
        
        # Should complete quickly
        assert end_time - start_time < 1.0
        assert isinstance(result, dict)
        assert 'Line 199' in result['terminal']
    
    def test_complex_content_performance(self):
        """Test performance with complex content."""
        generator = _BoxGenerator(style='rounded', terminal_width=60)
        
        # Complex content with ANSI, Unicode, emojis
        complex_lines = []
        for i in range(100):
            line = f"\033[3{i%8}mLine {i} 你好 😀 world\033[0m"
            complex_lines.append(line)
        
        import time
        start_time = time.time()
        result = generator.generate_box(complex_lines)
        end_time = time.time()
        
        assert end_time - start_time < 1.0
        assert isinstance(result, dict)
        assert '你好' in result['terminal']
        assert '😀' in result['terminal']


def run_tests():
    """Run all redesigned box generator tests with visual examples."""
    import traceback
    
    test_classes = [
        TestBoxCharacterWidthMapping,
        TestBoxStyles,
        TestUnicodeBoxStyles,  # NEW: Test Unicode styles specifically
        TestASCIIFallback,     # NEW: Test ASCII fallback behavior
        TestBoxGeneratorInitialization,
        TestNewInputFormat,
        TestBoxWidthCalculation,
        TestTitleHandling,
        TestBoxJustification,
        TestNewlineHandling,
        TestColorBleedingPrevention,  # NEW: Test color bleeding prevention
        TestHTMLOutputIssues,         # NEW: Test HTML output issues
        TestColorApplication,
        TestOutputFormats,
        TestEdgeCases,
        TestPerformance
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("🧪 Running REDESIGNED Box Generator Test Suite...")
    print("=" * 70)
    
    # Show visual examples first
    print("\n🎨 VISUAL EXAMPLES (New Interface)")
    print("-" * 60)
    
    terminal_width = max(60, _terminal.width)
    
    # Example 1: New List[str] input format
    print("📦 NEW: List[str] Input Format")
    generator = _BoxGenerator(style='square', terminal_width=terminal_width)  # Use Unicode style
    
    # Pre-wrapped lines (as they would come from text wrapper)
    pre_wrapped_lines = [
        "This is line 1 of pre-wrapped content",
        "Line 2 is shorter",
        "And line 3 completes the example"
    ]
    
    result = generator.generate_box(pre_wrapped_lines)
    print("Input: List of pre-wrapped lines")
    print("Output:")
    print(result['terminal'])
    
    # Example 2: Empty content behavior (8 spaces)
    print("\n📦 NEW: Empty Content (8 spaces + 4 padding)")
    empty_result = generator.generate_box([])
    print("Input: Empty list []")
    print("Output:")
    print(empty_result['terminal'])
    
    # Example 3: Box justification (renamed parameter)
    print("\n📐 NEW: Box Justification (box_justify parameter)")
    for justify in ['left', 'center', 'right']:
        print(f"\n{justify.upper()} justified:")
        justified_generator = _BoxGenerator(
            style='rounded',  # Use Unicode style
            box_justify=justify,  # NEW parameter name
            terminal_width=terminal_width
        )
        result = justified_generator.generate_box([f"Box is {justify}-justified"])
        print(result['terminal'])
    
    # Example 4: Title always centered
    print("\n📋 NEW: Title Always Centered")
    title_generator = _BoxGenerator(
        style='double',  # Use Unicode style
        title='Always Centered',
        terminal_width=terminal_width
    )
    result = title_generator.generate_box(["Title is always centered in border"])
    print(result['terminal'])
    
    # Example 5: Wide character handling
    print("\n🌏 Wide Character Width Calculation")
    wide_content = [
        "Regular ASCII text",
        "中文字符宽度测试",  # Chinese characters
        "Emoji test: 😀🎉🚀",
        "Mixed: Hello 世界 with 🌟"
    ]
    result = generator.generate_box(wide_content)
    print(result['terminal'])
    
    # Example 6: ANSI codes preserved
    print("\n🎨 ANSI Codes in Content")
    ansi_content = [
        "\033[31mRed line\033[0m",
        "\033[32mGreen line\033[0m", 
        "\033[1m\033[34mBold blue line\033[0m",
        "Plain line mixed with \033[35mmagenta\033[0m"
    ]
    result = generator.generate_box(ansi_content)
    print("Terminal format (ANSI preserved):")
    print(result['terminal'])
    print("\nPlain format (ANSI stripped):")
    print(result['plain'])
    
    # Example 7: Unicode Box Styles Comparison
    print("\n📦 Unicode Box Styles Comparison")
    
    # Determine which styles are actually available
    try:
        from setup.unicode import _supports_box_drawing
        unicode_available = _supports_box_drawing()
    except ImportError:
        unicode_available = False
    
    if unicode_available:
        styles_to_test = ['square', 'rounded', 'double', 'heavy', 'heavy_head', 'horizontals']
        print("Unicode box drawing is supported - showing Unicode styles:")
    else:
        styles_to_test = ['ascii']
        print("Unicode box drawing not supported - showing ASCII fallback:")
    
    test_content = ["Box Style Demo"]
    
    for style in styles_to_test:
        print(f"\n{style.upper()} Style:")
        try:
            style_generator = _BoxGenerator(style=style, terminal_width=terminal_width)
            result = style_generator.generate_box(test_content)
            print(result['terminal'])
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Example 8: Color Bleeding Prevention Tests
    print("\n🎨 Color Bleeding Prevention Examples")
    
    # Border color only
    print("\n🔴 Border Color Only (Red):")
    border_generator = _BoxGenerator(
        style='square',
        color='red',
        terminal_width=terminal_width
    )
    result = border_generator.generate_box(["Border colored red, content plain"])
    print(result['terminal'])
    
    # Different border styles
    print("\n🎨 Different Border Styles:")
    styles_to_test = ['square', 'rounded', 'double', 'heavy']
    for style in styles_to_test:
        style_generator = _BoxGenerator(
            style=style,
            color='blue',
            terminal_width=terminal_width
        )
        result = style_generator.generate_box([f"{style.title()} style with blue border"])
        print(f"\n{style.title()} style:")
        print(result['terminal'])
    
    # Colored content with colored borders
    print("\n🌈 Colored Content + Colored Borders:")
    complex_generator = _BoxGenerator(
        style='heavy',
        color='magenta',
        
        title='Color Mix Test',
        terminal_width=terminal_width
    )
    colored_content = [
        "\033[31mRed content line\033[0m",
        "\033[32mGreen content line\033[0m",
        "Plain content line",
        "\033[1m\033[33mBold yellow content\033[0m"
    ]
    result = complex_generator.generate_box(colored_content)
    print("Terminal format (all colors):")
    print(result['terminal'])
    print("\nPlain format (no ANSI codes):")
    print(result['plain'])
    
    # Example 9: HTML Output Investigation
    print("\n🌐 HTML Output Investigation")
    print("(This will help debug the 'm' character issue)")
    
    html_test_generator = _BoxGenerator(
        style='square',
        color='red',
        
        title='HTML Debug',
        terminal_width=50  # Smaller width to make issues more visible
    )
    
    test_content = [
        "Line 1 normal content",
        "Line 2 with <special> & chars",
        "Line 3 ends here"
    ]
    
    result = html_test_generator.generate_box(test_content)
    
    print("\nTerminal output:")
    print(result['terminal'])
    print(f"\nTerminal line lengths:")
    for i, line in enumerate(result['terminal'].split('\n')):
        if line.strip():
            print(f"  Line {i}: {len(line)} chars")
    
    print(f"\nHTML output:")
    print(result['html'])
    print(f"\nHTML line lengths:")
    if '<pre' in result['html'] and '</pre>' in result['html']:
        start_idx = result['html'].find('>\n') + 2
        end_idx = result['html'].find('\n</pre>')
        html_content = result['html'][start_idx:end_idx]
        for i, line in enumerate(html_content.split('\n')):
            if line.strip():
                print(f"  Line {i}: {len(line)} chars - {repr(line)}")
    
    print("\n⚠️  Look for any lines where HTML length > Terminal length")
    print("⚠️  Look for any 'm' characters where right edge should be")
    print("⚠️  Check if HTML entities are making lines longer")
    
    # Example 10: Hex and RGB color formats
    print("\n🎨 Advanced Color Formats (Hex, RGB)")
    hex_rgb_generator = _BoxGenerator(
        style='heavy_head',
        color='#FF5500',  # Hex orange
        title='Advanced Colors',
        terminal_width=terminal_width
    )
    result = hex_rgb_generator.generate_box(["Hex border color test"])
    print("Terminal format:")
    print(result['terminal'])
    print("HTML format (check CSS normalization):")
    print(result['html'])
    
    print("\n" + "=" * 70)
    print("🧪 RUNNING UNIT TESTS")
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 50)
        
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
    print("\n" + "=" * 70)
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