# tests/test_fdl/test_format_state.py
"""
Tests for the FDL format state module.

Tests the internal _FormatState class and related functions.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from suitkaise.fdl._int.core.format_state import _FormatState, _create_format_state


class TestFormatState:
    """Test the _FormatState class."""
    
    def test_format_state_initialization(self):
        """Test _FormatState initializes with correct defaults."""
        state = _FormatState()
        
        # Text formatting defaults
        assert state.bold is False
        assert state.italic is False
        assert state.underline is False
        assert state.strikethrough is False
        
        # Color defaults
        assert state.text_color is None
        assert state.background_color is None
        
        # Layout defaults
        assert state.justify == 'left'
        
        # Box defaults
        assert state.in_box is False
        assert state.box_style is None
        assert state.box_title is None
        assert state.box_color is None
        assert state.box_content == []
        
        # Output streams
        assert state.terminal_output == []
        assert state.queued_terminal_output == []
        assert state.plain_output == []
        assert state.markdown_output == []
        assert state.html_output == []
        
        # Progress bar state
        assert state.bar_active is False
        
        # Terminal width should be set
        assert isinstance(state.terminal_width, int)
        assert state.terminal_width >= 60
    
    def test_format_state_with_values(self):
        """Test _FormatState with values tuple."""
        values = ('test', 42, True)
        state = _FormatState(values=values, terminal_width=80)
        
        assert state.values == list(values)
        assert state.terminal_width == 80
        
        # Test getting values
        assert state.get_next_value() == 'test'
        assert state.get_next_value() == 42
        assert state.get_next_value() == True
        
        # Test has_more_values
        assert state.has_more_values() is False
    
    def test_reset_formatting(self):
        """Test reset_formatting method."""
        state = _FormatState()
        
        # Set some formatting
        state.bold = True
        state.italic = True
        state.text_color = 'red'
        state.background_color = 'blue'
        
        # Reset formatting
        state.reset_formatting()
        
        assert state.bold is False
        assert state.italic is False
        assert state.underline is False
        assert state.strikethrough is False
        assert state.text_color is None
        assert state.background_color is None
    
    def test_add_to_output_streams(self):
        """Test adding content to output streams."""
        state = _FormatState()
        
        state.add_to_output_streams(
            terminal='terminal text',
            plain='plain text',
            markdown='markdown text',
            html='html text'
        )
        
        assert state.terminal_output == ['terminal text']
        assert state.plain_output == ['plain text']
        assert state.markdown_output == ['markdown text']
        assert state.html_output == ['html text']
    
    def test_box_mode(self):
        """Test box mode functionality."""
        state = _FormatState()
        
        # Start box mode
        state.in_box = True
        state.box_style = 'rounded'
        state.box_title = 'Test Box'
        state.box_color = 'red'
        
        # Add content to box
        state.box_content.append('Box content line 1')
        state.box_content.append('Box content line 2')
        
        assert state.in_box is True
        assert len(state.box_content) == 2
        assert ''.join(state.box_content) == 'Box content line 1Box content line 2'
    
    def test_progress_bar_mode(self):
        """Test progress bar mode functionality."""
        state = _FormatState()
        
        # Mock progress bar
        class MockProgressBar:
            def __init__(self):
                self.is_stopped = False
        
        mock_bar = MockProgressBar()
        state.start_progress_bar_mode(mock_bar)
        
        assert state.bar_active is True
        assert state.active_progress_bar is mock_bar
    
    def test_get_final_outputs(self):
        """Test getting final outputs."""
        state = _FormatState()
        
        state.terminal_output = ['terminal ', 'content']
        state.plain_output = ['plain ', 'content']
        state.markdown_output = ['markdown ', 'content']
        state.html_output = ['html ', 'content']
        
        outputs = state.get_final_outputs()
        
        assert outputs['terminal'] == 'terminal content'
        assert outputs['plain'] == 'plain content'
        assert outputs['markdown'] == 'markdown content'
        assert outputs['html'] == 'html content'
    
    def test_get_final_outputs_with_queued(self):
        """Test getting final outputs with queued content."""
        state = _FormatState()
        
        state.terminal_output = ['terminal ']
        state.queued_terminal_output = ['queued']
        state.plain_output = ['plain']
        
        outputs = state.get_final_outputs()
        
        assert outputs['terminal'] == 'terminal queued'
        assert outputs['plain'] == 'plain'


class TestCreateFormatState:
    """Test the _create_format_state function."""
    
    def test_create_format_state_defaults(self):
        """Test creating format state with defaults."""
        state = _create_format_state()
        
        assert isinstance(state, _FormatState)
        assert state.values == []
        assert state.terminal_width >= 60
    
    def test_create_format_state_with_values(self):
        """Test creating format state with values."""
        values = ('test', 123)
        state = _create_format_state(values)
        
        assert state.values == list(values)
    
    def test_create_format_state_with_terminal_width(self):
        """Test creating format state with custom terminal width."""
        state = _create_format_state(terminal_width=100)
        
        assert state.terminal_width == 100
    
    def test_create_format_state_minimum_width(self):
        """Test that minimum terminal width is enforced."""
        state = _create_format_state(terminal_width=30)
        
        assert state.terminal_width == 60  # Should be enforced to minimum


if __name__ == '__main__':
    pytest.main([__file__])