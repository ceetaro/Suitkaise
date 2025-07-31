# tests/test_fdl/test_command_processors.py
"""
Tests for the FDL command processors.

Tests all command processors: text, layout, box, and time commands.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from suitkaise.fdl._int.processors.commands.text_commands import _TextCommandProcessor
from suitkaise.fdl._int.processors.commands.layout_commands import _LayoutCommandProcessor
from suitkaise.fdl._int.processors.commands.box_commands import _BoxCommandProcessor
from suitkaise.fdl._int.processors.commands.time_commands import _TimeCommandProcessor
from suitkaise.fdl._int.processors.commands.debug_commands import _DebugCommandProcessor
from suitkaise.fdl._int.processors.commands.fmt_commands import _FormatCommandProcessor
from suitkaise.fdl._int.core.format_state import _FormatState


class TestTextCommandProcessor:
    """Test the _TextCommandProcessor class."""
    
    def test_can_process_text_formatting(self):
        """Test recognition of text formatting commands."""
        processor = _TextCommandProcessor
        
        # Should recognize text formatting
        assert processor.can_process('bold') is True
        assert processor.can_process('italic') is True
        assert processor.can_process('underline') is True
        assert processor.can_process('strikethrough') is True
        
        # Should recognize reset
        assert processor.can_process('reset') is True
    
    def test_can_process_named_colors(self):
        """Test recognition of named color commands."""
        processor = _TextCommandProcessor
        
        # Should recognize named colors
        assert processor.can_process('red') is True
        assert processor.can_process('green') is True
        assert processor.can_process('blue') is True
        assert processor.can_process('yellow') is True
        
        # Should not recognize invalid colors
        assert processor.can_process('invalid_color') is False
    
    def test_can_process_hex_colors(self):
        """Test recognition of hex color commands."""
        processor = _TextCommandProcessor
        
        # Should recognize valid hex colors
        assert processor.can_process('#FF0000') is True
        assert processor.can_process('#00ff00') is True
        assert processor.can_process('#123') is True
        
        # Should not recognize invalid hex colors
        assert processor.can_process('#GGGGGG') is False
        assert processor.can_process('#12') is False
    
    def test_can_process_rgb_colors(self):
        """Test recognition of RGB color commands."""
        processor = _TextCommandProcessor
        
        # Should recognize valid RGB colors
        assert processor.can_process('rgb(255, 0, 0)') is True
        assert processor.can_process('rgb(0,255,0)') is True
        
        # Should not recognize invalid RGB colors
        assert processor.can_process('rgb(256, 0, 0)') is False
        assert processor.can_process('rgb(255, 0)') is False
    
    def test_can_process_background_colors(self):
        """Test recognition of background color commands."""
        processor = _TextCommandProcessor
        
        # Should recognize background colors
        assert processor.can_process('bkg red') is True
        assert processor.can_process('bkg #FF0000') is True
        assert processor.can_process('bkg rgb(255, 0, 0)') is True
        
        # Should not recognize invalid background colors
        assert processor.can_process('bkg invalid') is False
    
    def test_can_process_end_commands(self):
        """Test recognition of end commands."""
        processor = _TextCommandProcessor
        
        # Should recognize end commands
        assert processor.can_process('end bold') is True
        assert processor.can_process('end red') is True
        assert processor.can_process('end bkg') is True
        assert processor.can_process('end all') is True
    
    def test_process_text_formatting(self):
        """Test processing text formatting commands."""
        processor = _TextCommandProcessor
        format_state = _FormatState()
        
        # Process bold command
        result = processor.process('bold', format_state)
        assert result.bold is True
        assert '\x1b[1m' in result.terminal_output  # ANSI bold code
        
        # Process italic command
        result = processor.process('italic', result)
        assert result.italic is True
        assert '\x1b[3m' in result.terminal_output  # ANSI italic code
    
    def test_process_color_commands(self):
        """Test processing color commands."""
        processor = _TextCommandProcessor
        format_state = _FormatState()
        
        # Process red color command
        result = processor.process('red', format_state)
        assert result.text_color == 'red'
        assert '\x1b[31m' in result.terminal_output  # ANSI red code
    
    def test_process_reset_command(self):
        """Test processing reset command."""
        processor = _TextCommandProcessor
        format_state = _FormatState()
        
        # Set some formatting first
        format_state.bold = True
        format_state.text_color = 'red'
        
        # Process reset command
        result = processor.process('reset', format_state)
        assert result.bold is False
        assert result.text_color is None
        assert '\x1b[0m' in result.terminal_output  # ANSI reset code
    
    def test_process_end_commands(self):
        """Test processing end commands."""
        processor = _TextCommandProcessor
        format_state = _FormatState()
        
        # Set formatting first
        format_state.bold = True
        format_state.text_color = 'red'
        
        # End bold formatting
        result = processor.process('end bold', format_state)
        assert result.bold is False
        assert result.text_color == 'red'  # Should still be red
        
        # End color
        result = processor.process('end red', result)
        assert result.text_color is None


class TestLayoutCommandProcessor:
    """Test the _LayoutCommandProcessor class."""
    
    def test_can_process_justify_commands(self):
        """Test recognition of justify commands."""
        processor = _LayoutCommandProcessor
        
        # Should recognize justify commands
        assert processor.can_process('justify left') is True
        assert processor.can_process('justify right') is True
        assert processor.can_process('justify center') is True
        
        # Should recognize end justify
        assert processor.can_process('end justify') is True
        
        # Should not recognize invalid justify commands
        assert processor.can_process('justify invalid') is False
        assert processor.can_process('justify') is False
    
    def test_process_justify_commands(self):
        """Test processing justify commands."""
        processor = _LayoutCommandProcessor
        format_state = _FormatState()
        
        # Process center justify
        result = processor.process('justify center', format_state)
        assert result.justify == 'center'
        
        # Process right justify
        result = processor.process('justify right', result)
        assert result.justify == 'right'
    
    def test_process_end_justify(self):
        """Test processing end justify command."""
        processor = _LayoutCommandProcessor
        format_state = _FormatState()
        
        # Set justify first
        format_state.justify = 'center'
        
        # End justify
        result = processor.process('end justify', format_state)
        assert result.justify == 'left'  # Should reset to left
    
    def test_justify_with_newlines(self):
        """Test that justify commands add newlines when needed."""
        processor = _LayoutCommandProcessor
        format_state = _FormatState()
        
        # Add some content first
        format_state.terminal_output.append('Some text')
        
        # Change from left to center (should add newline)
        result = processor.process('justify center', format_state)
        
        # Should have added newline to output
        assert '\n' in result.terminal_output


class TestBoxCommandProcessor:
    """Test the _BoxCommandProcessor class."""
    
    def test_can_process_box_commands(self):
        """Test recognition of box commands."""
        processor = _BoxCommandProcessor
        
        # Should recognize box commands
        assert processor.can_process('box square') is True
        assert processor.can_process('box rounded') is True
        assert processor.can_process('box double') is True
        
        # Should recognize end box
        assert processor.can_process('end box') is True
        
        # Should not recognize invalid box commands
        assert processor.can_process('box invalid') is False
    
    def test_can_process_box_with_options(self):
        """Test recognition of box commands with options."""
        processor = _BoxCommandProcessor
        
        # Should recognize box with title
        assert processor.can_process('box rounded, title Test') is True
        
        # Should recognize box with color
        assert processor.can_process('box square, red') is True
        
        # Should recognize box with justify
        assert processor.can_process('box double, justify center') is True
    
    def test_process_basic_box_command(self):
        """Test processing basic box command."""
        processor = _BoxCommandProcessor
        format_state = _FormatState()
        
        # Process box command
        result = processor.process('box rounded', format_state)
        
        assert result.in_box is True
        assert result.box_style == 'rounded'
    
    def test_process_box_with_title(self):
        """Test processing box command with title."""
        processor = _BoxCommandProcessor
        format_state = _FormatState(values=('Test Title',))
        
        # Process box command with title
        result = processor.process('box rounded, title title_var', format_state)
        
        assert result.in_box is True
        assert result.box_style == 'rounded'
        assert result.box_title == 'Test Title'
    
    def test_process_box_with_color(self):
        """Test processing box command with color."""
        processor = _BoxCommandProcessor
        format_state = _FormatState()
        
        # Process box command with color
        result = processor.process('box square, red', format_state)
        
        assert result.in_box is True
        assert result.box_style == 'square'
        assert result.box_color == 'red'
    
    def test_process_end_box(self):
        """Test processing end box command."""
        processor = _BoxCommandProcessor
        format_state = _FormatState()
        
        # Set up box state
        format_state.in_box = True
        format_state.box_style = 'rounded'
        format_state.box_content.append('Box content')
        
        # Process end box
        result = processor.process('end box', format_state)
        
        # Should generate box and reset state
        assert result.in_box is False
        assert result.box_style is None
        assert len(result.box_content) == 0


class TestTimeCommandProcessor:
    """Test the _TimeCommandProcessor class."""
    
    def test_can_process_time_commands(self):
        """Test recognition of time commands."""
        processor = _TimeCommandProcessor
        
        # Should recognize time format commands
        assert processor.can_process('12hr') is True
        assert processor.can_process('24hr') is True
        assert processor.can_process('no sec') is True
        assert processor.can_process('no secs') is True
        
        # Should recognize timezone commands
        assert processor.can_process('tz pst') is True
        assert processor.can_process('tz est') is True
        assert processor.can_process('tz utc') is True
    
    def test_process_hour_format_commands(self):
        """Test processing hour format commands."""
        processor = _TimeCommandProcessor
        format_state = _FormatState()
        
        # Process 12hr command
        result = processor.process('12hr', format_state)
        assert result.twelve_hour_time is True
        
        # Process 24hr command
        result = processor.process('24hr', result)
        assert result.twelve_hour_time is False
    
    def test_process_seconds_commands(self):
        """Test processing seconds display commands."""
        processor = _TimeCommandProcessor
        format_state = _FormatState()
        
        # Process no sec command
        result = processor.process('no sec', format_state)
        assert result.use_seconds is False
        
        # Process no secs command (alternative)
        format_state = _FormatState()
        result = processor.process('no secs', format_state)
        assert result.use_seconds is False
    
    def test_process_timezone_commands(self):
        """Test processing timezone commands."""
        processor = _TimeCommandProcessor
        format_state = _FormatState()
        
        # Process timezone command
        result = processor.process('tz pst', format_state)
        assert result.timezone == 'pst'


class TestCommandProcessorIntegration:
    """Test integration between command processors."""
    
    def test_multiple_processors_same_state(self):
        """Test that multiple processors can work on the same format state."""
        format_state = _FormatState()
        
        # Apply text formatting
        format_state = _TextCommandProcessor.process('bold', format_state)
        format_state = _TextCommandProcessor.process('red', format_state)
        
        # Apply layout
        format_state = _LayoutCommandProcessor.process('justify center', format_state)
        
        # Apply time formatting
        format_state = _TimeCommandProcessor.process('12hr', format_state)
        
        # All should be applied
        assert format_state.bold is True
        assert format_state.text_color == 'red'
        assert format_state.justify == 'center'
        assert format_state.twelve_hour_time is True
    
    def test_processor_priorities(self):
        """Test that processors handle overlapping commands correctly."""
        # This would be tested with the actual registry system
        # For now, we test individual processor behavior
        format_state = _FormatState()
        
        # Text processor should handle color commands
        assert _TextCommandProcessor.can_process('red') is True
        
        # Layout processor should handle justify commands
        assert _LayoutCommandProcessor.can_process('justify center') is True
        
        # Box processor should handle box commands
        assert _BoxCommandProcessor.can_process('box rounded') is True


class TestCommandProcessorEdgeCases:
    """Test edge cases and error handling for command processors."""
    
    def test_invalid_commands(self):
        """Test processing invalid commands."""
        processors = [
            _TextCommandProcessor,
            _LayoutCommandProcessor,
            _BoxCommandProcessor,
            _TimeCommandProcessor
        ]
        
        format_state = _FormatState()
        
        for processor in processors:
            # Should handle invalid commands gracefully
            result = processor.process('invalid_command', format_state)
            assert isinstance(result, _FormatState)
    
    def test_empty_commands(self):
        """Test processing empty commands."""
        processors = [
            _TextCommandProcessor,
            _LayoutCommandProcessor,
            _BoxCommandProcessor,
            _TimeCommandProcessor
        ]
        
        format_state = _FormatState()
        
        for processor in processors:
            # Should handle empty commands gracefully
            result = processor.process('', format_state)
            assert isinstance(result, _FormatState)
    
    def test_case_insensitive_commands(self):
        """Test that commands are case insensitive."""
        # Test text commands
        assert _TextCommandProcessor.can_process('BOLD') is True
        assert _TextCommandProcessor.can_process('Bold') is True
        assert _TextCommandProcessor.can_process('RED') is True
        
        # Test layout commands
        assert _LayoutCommandProcessor.can_process('JUSTIFY CENTER') is True
        assert _LayoutCommandProcessor.can_process('Justify Right') is True
        
        # Test box commands
        assert _BoxCommandProcessor.can_process('BOX ROUNDED') is True
        assert _BoxCommandProcessor.can_process('Box Square') is True


class TestDebugCommandProcessor:
    """Test the _DebugCommandProcessor class."""
    
    def test_can_process_debug_commands(self):
        """Test recognition of debug commands."""
        processor = _DebugCommandProcessor
        
        # Should recognize debug commands
        assert processor.can_process('debug') is True
        assert processor.can_process('debug on') is True
        assert processor.can_process('debug off') is True
        
        # Should not recognize invalid debug commands
        assert processor.can_process('debug invalid') is False
    
    def test_process_debug_commands(self):
        """Test processing debug commands."""
        processor = _DebugCommandProcessor
        format_state = _FormatState()
        
        # Test debug on
        result = processor.process('debug on', format_state)
        assert result.debug_mode is True
        
        # Test debug off
        result = processor.process('debug off', result)
        assert result.debug_mode is False
        
        # Test simple debug
        result = processor.process('debug', result)
        assert result.debug_mode is True
    
    def test_debug_mode_affects_text_formatting(self):
        """Test that debug mode affects text formatting."""
        format_state = _FormatState()
        
        # Enable debug mode
        format_state = _DebugCommandProcessor.process('debug on', format_state)
        assert format_state.debug_mode is True
        
        # Try to apply text formatting in debug mode
        result = _TextCommandProcessor.process('bold', format_state)
        assert result.bold is False  # Should not apply formatting in debug mode
        
        # Reset should still work
        result = _TextCommandProcessor.process('reset', result)
        assert result.debug_mode is False  # Reset should exit debug mode
    
    def test_debug_visual_examples(self):
        """Test debug commands with visual examples."""
        processor = _DebugCommandProcessor
        format_state = _FormatState()
        
        # Test debug on - should show debug mode enabled
        result = processor.process('debug on', format_state)
        assert result.debug_mode is True
        
        # Test debug off - should show debug mode disabled
        result = processor.process('debug off', result)
        assert result.debug_mode is False
        
        # Test debug toggle - should enable debug mode
        result = processor.process('debug', result)
        assert result.debug_mode is True


class TestFormatCommandProcessor:
    """Test the _FormatCommandProcessor class."""
    
    def test_can_process_format_commands(self):
        """Test recognition of format commands."""
        processor = _FormatCommandProcessor
        
        # Should recognize format commands
        assert processor.can_process('fmt') is True
        assert processor.can_process('fmt red') is True
        assert processor.can_process('fmt bold, red') is True
        assert processor.can_process('fmt #FF0000') is True
        assert processor.can_process('fmt rgb(255, 0, 0)') is True
        
        # Should not recognize invalid format commands
        assert processor.can_process('fmt invalid') is False
    
    def test_process_format_commands(self):
        """Test processing format commands."""
        processor = _FormatCommandProcessor
        format_state = _FormatState()
        
        # Test simple format
        result = processor.process('fmt red', format_state)
        assert result.text_color == 'red'
        
        # Test multiple formats
        result = processor.process('fmt bold, red', result)
        assert result.bold is True
        assert result.text_color == 'red'
        
        # Test hex color
        result = processor.process('fmt #00FF00', result)
        assert result.text_color == '#00FF00'
        
        # Test RGB color
        result = processor.process('fmt rgb(0, 0, 255)', result)
        assert result.text_color == 'rgb(0, 0, 255)'
    
    def test_format_visual_examples(self):
        """Test format commands with visual examples."""
        processor = _FormatCommandProcessor
        format_state = _FormatState()
        
        # Test single color format
        result = processor.process('fmt blue', format_state)
        assert result.text_color == 'blue'
        assert '\033[34m' in result.terminal_output  # ANSI blue code
        
        # Test multiple format attributes
        result = processor.process('fmt bold, italic, green', result)
        assert result.bold is True
        assert result.italic is True
        assert result.text_color == 'green'
        assert '\033[1m' in result.terminal_output  # ANSI bold code
        assert '\033[3m' in result.terminal_output  # ANSI italic code
        assert '\033[32m' in result.terminal_output  # ANSI green code
        
        # Test hex color format
        result = processor.process('fmt #FF0000', result)
        assert result.text_color == '#FF0000'
        
        # Test RGB color format
        result = processor.process('fmt rgb(255, 255, 0)', result)
        assert result.text_color == 'rgb(255, 255, 0)'


if __name__ == '__main__':
    pytest.main([__file__])