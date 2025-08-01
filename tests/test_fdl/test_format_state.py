"""
Comprehensive tests for FDL Format State System.

Tests the internal format state system that manages all formatting, layout,
time settings, box state, variables, output streams, and progress bar state.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.core.format_state import (
    _FormatState, _create_format_state
)


class TestFormatState:
    """Test suite for the format state management system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.format_state = _FormatState()
    
    def test_format_state_initialization_defaults(self):
        """Test format state initialization with default values."""
        state = _FormatState()
        
        # Text formatting defaults
        assert state.text_color is None
        assert state.background_color is None
        assert state.bold is False
        assert state.italic is False
        assert state.underline is False
        assert state.strikethrough is False
        
        # Time formatting defaults
        assert state.twelve_hour_time is False
        assert state.timezone is None
        assert state.use_seconds is True
        assert state.use_minutes is True
        assert state.use_hours is True
        assert state.decimal_places == 6
        assert state.round_seconds is False
        assert state.smart_time == 0
        
        # Box state defaults
        assert state.in_box is False
        assert state.box_style == "square"
        assert state.box_title is None
        assert state.box_color is None
        assert state.box_background is None
        assert state.box_content == []
        assert state.box_width == 0  # Will be calculated in __post_init__
        
        # Layout defaults
        assert state.justify == 'left'
        
        # Debug mode defaults
        assert state.debug_mode is False
        
        # Variable handling defaults
        assert state.values == ()
        assert state.value_index == 0
        
        # Terminal defaults
        assert state.terminal_width == 60
        
        # Progress bar defaults
        assert state.bar_active is False
        assert state.active_progress_bar is None
        
        # Output streams defaults
        assert state.terminal_output == []
        assert state.plain_output == []
        assert state.markdown_output == []
        assert state.html_output == []
        assert state.queued_terminal_output == []
        assert state.queued_plain_output == []
        assert state.queued_markdown_output == []
        assert state.queued_html_output == []
    
    def test_format_state_initialization_with_values(self):
        """Test format state initialization with custom values."""
        values = ("test", 123, True)
        state = _FormatState(
            text_color="red",
            bold=True,
            values=values,
            terminal_width=120,
            debug_mode=True
        )
        
        assert state.text_color == "red"
        assert state.bold is True
        assert state.values == values
        assert state.terminal_width == 120
        assert state.debug_mode is True
    
    def test_post_init_terminal_width_minimum(self):
        """Test that __post_init__ enforces minimum terminal width."""
        # Test with width below minimum
        state = _FormatState(terminal_width=30)
        assert state.terminal_width == 60  # Should be enforced to minimum
        
        # Test with width above minimum
        state = _FormatState(terminal_width=120)
        assert state.terminal_width == 120  # Should remain unchanged
    
    def test_post_init_box_width_calculation(self):
        """Test that __post_init__ calculates box width correctly."""
        # Test with minimum terminal width
        state = _FormatState(terminal_width=60)
        expected_box_width = max(40, 60 - 4 - 4)  # 52, but max with 40
        assert state.box_width == expected_box_width
        
        # Test with larger terminal width
        state = _FormatState(terminal_width=120)
        expected_box_width = max(40, 120 - 4 - 4)  # 112
        assert state.box_width == expected_box_width
    
    def test_calculate_max_box_width_method(self):
        """Test the _calculate_max_box_width method."""
        state = _FormatState(terminal_width=100)
        
        # Should account for edges (4) and padding (4)
        expected_width = max(40, 100 - 4 - 4)  # 92
        calculated_width = state._calculate_max_box_width()
        assert calculated_width == expected_width
        
        # Test minimum width enforcement
        state = _FormatState(terminal_width=70)
        calculated_width = state._calculate_max_box_width()
        assert calculated_width >= 40  # Should never be less than 40
    
    def test_copy_method_complete(self):
        """Test that copy method creates complete copy of state."""
        # Set up original state with various values
        original = _FormatState(
            text_color="blue",
            background_color="yellow",
            bold=True,
            italic=True,
            underline=True,
            strikethrough=True,
            twelve_hour_time=True,
            timezone="PST",
            use_seconds=False,
            decimal_places=3,
            round_seconds=True,
            smart_time=5,
            in_box=True,
            box_style="rounded",
            box_title="Test Box",
            box_color="green",
            box_background="white",
            justify="center",
            debug_mode=True,
            values=("a", "b", "c"),
            value_index=2,
            terminal_width=100
        )
        original.box_content = ["line1", "line2"]
        
        # Create copy
        copied = original.copy()
        
        # Verify all formatting attributes are copied
        assert copied.text_color == "blue"
        assert copied.background_color == "yellow"
        assert copied.bold is True
        assert copied.italic is True
        assert copied.underline is True
        assert copied.strikethrough is True
        
        # Verify time settings are copied
        assert copied.twelve_hour_time is True
        assert copied.timezone == "PST"
        assert copied.use_seconds is False
        assert copied.decimal_places == 3
        assert copied.round_seconds is True
        assert copied.smart_time == 5
        
        # Verify box state is copied
        assert copied.in_box is True
        assert copied.box_style == "rounded"
        assert copied.box_title == "Test Box"
        assert copied.box_color == "green"
        assert copied.box_background == "white"
        assert copied.box_content == ["line1", "line2"]
        assert copied.box_content is not original.box_content  # Should be different list
        
        # Verify other attributes
        assert copied.justify == "center"
        assert copied.debug_mode is True
        assert copied.values == ("a", "b", "c")
        assert copied.value_index == 2
        assert copied.terminal_width == 100
        
        # Verify progress bar state is reset in copy
        assert copied.bar_active is False
        assert copied.active_progress_bar is None
        
        # Verify output streams start empty in copy
        assert copied.terminal_output == []
        assert copied.plain_output == []
        assert copied.markdown_output == []
        assert copied.html_output == []
    
    def test_copy_method_independence(self):
        """Test that copy is independent of original."""
        original = _FormatState()
        original.box_content = ["original"]
        
        copied = original.copy()
        
        # Modify original
        original.text_color = "red"
        original.box_content.append("modified")
        
        # Verify copy is unchanged
        assert copied.text_color is None
        assert copied.box_content == ["original"]
    
    def test_progress_bar_mode_start(self):
        """Test starting progress bar mode."""
        mock_progress_bar = Mock()
        state = _FormatState()
        
        # Add some existing queued output
        state.queued_terminal_output = ["old"]
        state.queued_plain_output = ["old"]
        
        # Start progress bar mode
        state.start_progress_bar_mode(mock_progress_bar)
        
        # Verify state changes
        assert state.bar_active is True
        assert state.active_progress_bar is mock_progress_bar
        
        # Verify queued output is cleared
        assert state.queued_terminal_output == []
        assert state.queued_plain_output == []
        assert state.queued_markdown_output == []
        assert state.queued_html_output == []
    
    def test_progress_bar_mode_stop_with_flush(self):
        """Test stopping progress bar mode with output flush."""
        mock_progress_bar = Mock()
        state = _FormatState()
        
        # Set up progress bar mode with queued output
        state.start_progress_bar_mode(mock_progress_bar)
        state.queued_terminal_output = ["queued1", "queued2"]
        state.queued_plain_output = ["plain1", "plain2"]
        
        # Stop with flush
        state.stop_progress_bar_mode(flush_output=True)
        
        # Verify state changes
        assert state.bar_active is False
        assert state.active_progress_bar is None
        
        # Verify output was flushed to main streams
        assert state.terminal_output == ["queued1", "queued2"]
        assert state.plain_output == ["plain1", "plain2"]
        
        # Verify queued output is cleared
        assert state.queued_terminal_output == []
        assert state.queued_plain_output == []
    
    def test_progress_bar_mode_stop_without_flush(self):
        """Test stopping progress bar mode without output flush."""
        mock_progress_bar = Mock()
        state = _FormatState()
        
        # Set up progress bar mode with queued output
        state.start_progress_bar_mode(mock_progress_bar)
        state.queued_terminal_output = ["queued1", "queued2"]
        state.queued_plain_output = ["plain1", "plain2"]
        
        # Stop without flush
        state.stop_progress_bar_mode(flush_output=False)
        
        # Verify state changes
        assert state.bar_active is False
        assert state.active_progress_bar is None
        
        # Verify output was NOT flushed to main streams
        assert state.terminal_output == []
        assert state.plain_output == []
        
        # Verify queued output is cleared anyway
        assert state.queued_terminal_output == []
        assert state.queued_plain_output == []
    
    def test_flush_queued_output_method(self):
        """Test the flush_queued_output method."""
        state = _FormatState()
        
        # Set up main and queued output
        state.terminal_output = ["main1"]
        state.plain_output = ["plain_main1"]
        state.queued_terminal_output = ["queued1", "queued2"]
        state.queued_plain_output = ["plain_queued1", "plain_queued2"]
        state.queued_markdown_output = ["md_queued1"]
        state.queued_html_output = ["html_queued1"]
        
        # Flush queued output
        state.flush_queued_output()
        
        # Verify main output contains both original and queued
        assert state.terminal_output == ["main1", "queued1", "queued2"]
        assert state.plain_output == ["plain_main1", "plain_queued1", "plain_queued2"]
        assert state.markdown_output == ["md_queued1"]
        assert state.html_output == ["html_queued1"]
    
    def test_add_to_output_streams_normal_mode(self):
        """Test adding to output streams in normal mode."""
        state = _FormatState()
        
        # Add content in normal mode
        state.add_to_output_streams(
            terminal="terminal_content",
            plain="plain_content",
            markdown="markdown_content",
            html="html_content"
        )
        
        # Verify content goes to main streams
        assert state.terminal_output == ["terminal_content"]
        assert state.plain_output == ["plain_content"]
        assert state.markdown_output == ["markdown_content"]
        assert state.html_output == ["html_content"]
        
        # Verify queued streams remain empty
        assert state.queued_terminal_output == []
        assert state.queued_plain_output == []
        assert state.queued_markdown_output == []
        assert state.queued_html_output == []
    
    def test_add_to_output_streams_progress_bar_mode(self):
        """Test adding to output streams in progress bar mode."""
        state = _FormatState()
        mock_progress_bar = Mock()
        
        # Start progress bar mode
        state.start_progress_bar_mode(mock_progress_bar)
        
        # Add content in progress bar mode
        state.add_to_output_streams(
            terminal="terminal_content",
            plain="plain_content",
            markdown="markdown_content",
            html="html_content"
        )
        
        # Verify content goes to queued streams
        assert state.queued_terminal_output == ["terminal_content"]
        assert state.queued_plain_output == ["plain_content"]
        assert state.queued_markdown_output == ["markdown_content"]
        assert state.queued_html_output == ["html_content"]
        
        # Verify main streams remain empty
        assert state.terminal_output == []
        assert state.plain_output == []
        assert state.markdown_output == []
        assert state.html_output == []
    
    def test_add_to_output_streams_partial_content(self):
        """Test adding partial content to output streams."""
        state = _FormatState()
        
        # Add only some content types
        state.add_to_output_streams(terminal="terminal_only")
        state.add_to_output_streams(plain="plain_only", markdown="markdown_only")
        
        # Verify only specified content is added
        assert state.terminal_output == ["terminal_only"]
        assert state.plain_output == ["plain_only"]
        assert state.markdown_output == ["markdown_only"]
        assert state.html_output == []
    
    def test_reset_formatting_method(self):
        """Test the reset_formatting method."""
        state = _FormatState(
            text_color="red",
            background_color="blue",
            bold=True,
            italic=True,
            underline=True,
            strikethrough=True
        )
        
        # Reset formatting
        state.reset_formatting()
        
        # Verify all formatting is reset
        assert state.text_color is None
        assert state.background_color is None
        assert state.bold is False
        assert state.italic is False
        assert state.underline is False
        assert state.strikethrough is False
    
    def test_reset_time_settings_method(self):
        """Test the reset_time_settings method."""
        state = _FormatState(
            twelve_hour_time=True,
            timezone="PST",
            use_seconds=False,
            use_minutes=False,
            use_hours=False,
            decimal_places=3,
            round_seconds=True,
            smart_time=5
        )
        
        # Reset time settings
        state.reset_time_settings()
        
        # Verify all time settings are reset to defaults
        assert state.twelve_hour_time is False
        assert state.timezone is None
        assert state.use_seconds is True
        assert state.use_minutes is True
        assert state.use_hours is True
        assert state.decimal_places == 6
        assert state.round_seconds is False
        assert state.smart_time == 0
    
    def test_reset_box_state_method(self):
        """Test the reset_box_state method."""
        state = _FormatState(
            in_box=True,
            box_style="rounded",
            box_title="Test",
            box_color="red",
            box_background="blue"
        )
        state.box_content = ["content1", "content2"]
        
        # Reset box state
        state.reset_box_state()
        
        # Verify all box state is reset
        assert state.in_box is False
        assert state.box_style == "square"
        assert state.box_title is None
        assert state.box_color is None
        assert state.box_background is None
        assert state.box_content == []
    
    def test_reset_debug_mode_method(self):
        """Test the reset_debug_mode method."""
        state = _FormatState(debug_mode=True)
        
        # Reset debug mode
        state.reset_debug_mode()
        
        # Verify debug mode is reset
        assert state.debug_mode is False
    
    def test_reset_all_formatting_method(self):
        """Test the reset_all_formatting method."""
        state = _FormatState(
            text_color="red",
            bold=True,
            twelve_hour_time=True,
            timezone="PST",
            in_box=True,
            box_style="rounded",
            debug_mode=True
        )
        state.box_content = ["content"]
        
        # Reset all formatting
        state.reset_all_formatting()
        
        # Verify everything is reset
        assert state.text_color is None
        assert state.bold is False
        assert state.twelve_hour_time is False
        assert state.timezone is None
        assert state.in_box is False
        assert state.box_style == "square"
        assert state.box_content == []
        assert state.debug_mode is False
    
    def test_reset_output_streams_method(self):
        """Test the reset_output_streams method."""
        state = _FormatState()
        
        # Add content to all streams
        state.terminal_output = ["terminal1", "terminal2"]
        state.plain_output = ["plain1", "plain2"]
        state.markdown_output = ["md1", "md2"]
        state.html_output = ["html1", "html2"]
        state.queued_terminal_output = ["queued_terminal1"]
        state.queued_plain_output = ["queued_plain1"]
        state.queued_markdown_output = ["queued_md1"]
        state.queued_html_output = ["queued_html1"]
        
        # Reset output streams
        state.reset_output_streams()
        
        # Verify all streams are cleared
        assert state.terminal_output == []
        assert state.plain_output == []
        assert state.markdown_output == []
        assert state.html_output == []
        assert state.queued_terminal_output == []
        assert state.queued_plain_output == []
        assert state.queued_markdown_output == []
        assert state.queued_html_output == []
    
    def test_get_next_value_success(self):
        """Test successful value retrieval."""
        values = ("first", "second", "third")
        state = _FormatState(values=values)
        
        # Get values in sequence
        assert state.get_next_value() == "first"
        assert state.value_index == 1
        
        assert state.get_next_value() == "second"
        assert state.value_index == 2
        
        assert state.get_next_value() == "third"
        assert state.value_index == 3
    
    def test_get_next_value_exhausted(self):
        """Test value retrieval when values are exhausted."""
        values = ("only_one",)
        state = _FormatState(values=values)
        
        # Get the only value
        assert state.get_next_value() == "only_one"
        
        # Try to get another value - should raise IndexError
        with pytest.raises(IndexError) as exc_info:
            state.get_next_value()
        
        assert "No more values available" in str(exc_info.value)
        assert "index 1" in str(exc_info.value)
    
    def test_get_next_value_empty_tuple(self):
        """Test value retrieval with empty values tuple."""
        state = _FormatState(values=())
        
        # Try to get value from empty tuple - should raise IndexError
        with pytest.raises(IndexError) as exc_info:
            state.get_next_value()
        
        assert "No more values available" in str(exc_info.value)
        assert "index 0" in str(exc_info.value)
    
    def test_has_more_values_method(self):
        """Test the has_more_values method."""
        values = ("first", "second")
        state = _FormatState(values=values)
        
        # Initially should have values
        assert state.has_more_values() is True
        
        # After getting one value
        state.get_next_value()
        assert state.has_more_values() is True
        
        # After getting all values
        state.get_next_value()
        assert state.has_more_values() is False
    
    def test_has_more_values_empty_tuple(self):
        """Test has_more_values with empty tuple."""
        state = _FormatState(values=())
        assert state.has_more_values() is False
    
    def test_get_final_outputs_normal_mode(self):
        """Test get_final_outputs in normal mode."""
        state = _FormatState()
        
        # Add content to main streams
        state.terminal_output = ["terminal1", "terminal2"]
        state.plain_output = ["plain1", "plain2"]
        state.markdown_output = ["md1", "md2"]
        state.html_output = ["html1", "html2"]
        
        outputs = state.get_final_outputs()
        
        # Verify final outputs contain main stream content
        assert outputs['terminal'] == "terminal1terminal2"
        assert outputs['plain'] == "plain1plain2"
        assert outputs['markdown'] == "md1md2"
        assert outputs['html'] == "html1html2"
    
    def test_get_final_outputs_with_queued_content(self):
        """Test get_final_outputs with queued content."""
        state = _FormatState()
        
        # Add content to both main and queued streams
        state.terminal_output = ["main1", "main2"]
        state.plain_output = ["plain_main1"]
        state.queued_terminal_output = ["queued1", "queued2"]
        state.queued_plain_output = ["plain_queued1"]
        state.queued_markdown_output = ["md_queued1"]
        state.queued_html_output = ["html_queued1"]
        
        outputs = state.get_final_outputs()
        
        # Verify final outputs contain both main and queued content
        assert outputs['terminal'] == "main1main2queued1queued2"
        assert outputs['plain'] == "plain_main1plain_queued1"
        assert outputs['markdown'] == "md_queued1"
        assert outputs['html'] == "html_queued1"
    
    def test_get_immediate_outputs_method(self):
        """Test get_immediate_outputs method."""
        state = _FormatState()
        
        # Add content to both main and queued streams
        state.terminal_output = ["main1", "main2"]
        state.plain_output = ["plain_main1"]
        state.queued_terminal_output = ["queued1", "queued2"]
        state.queued_plain_output = ["plain_queued1"]
        
        outputs = state.get_immediate_outputs()
        
        # Verify immediate outputs contain only main stream content
        assert outputs['terminal'] == "main1main2"
        assert outputs['plain'] == "plain_main1"
        assert outputs['markdown'] == ""
        assert outputs['html'] == ""


class TestFormatStateFactory:
    """Test suite for the format state factory function."""
    
    def test_create_format_state_defaults(self):
        """Test _create_format_state with default parameters."""
        with patch('suitkaise.fdl._int.core.format_state._terminal') as mock_terminal:
            mock_terminal.width = 100
            
            state = _create_format_state()
            
            assert state.values == []  # Should be converted from tuple to list
            assert state.terminal_width == 100
    
    def test_create_format_state_with_values_tuple(self):
        """Test _create_format_state with values tuple."""
        values = ("a", "b", "c")
        
        with patch('suitkaise.fdl._int.core.format_state._terminal') as mock_terminal:
            mock_terminal.width = 80
            
            state = _create_format_state(values=values)
            
            assert state.values == ["a", "b", "c"]  # Should be converted to list
            assert state.terminal_width == 80
    
    def test_create_format_state_with_values_list(self):
        """Test _create_format_state with values list."""
        values = ["x", "y", "z"]
        
        with patch('suitkaise.fdl._int.core.format_state._terminal') as mock_terminal:
            mock_terminal.width = 80
            
            state = _create_format_state(values=values)
            
            assert state.values == ["x", "y", "z"]  # Should remain as list
            assert state.terminal_width == 80
    
    def test_create_format_state_with_terminal_width_override(self):
        """Test _create_format_state with terminal width override."""
        with patch('suitkaise.fdl._int.core.format_state._terminal') as mock_terminal:
            mock_terminal.width = 100
            
            state = _create_format_state(terminal_width=150)
            
            assert state.terminal_width == 150  # Should use override
    
    def test_create_format_state_minimum_width_enforcement(self):
        """Test that _create_format_state enforces minimum width."""
        with patch('suitkaise.fdl._int.core.format_state._terminal') as mock_terminal:
            mock_terminal.width = 40  # Below minimum
            
            state = _create_format_state()
            
            assert state.terminal_width == 60  # Should enforce minimum
    
    def test_create_format_state_minimum_width_override(self):
        """Test minimum width enforcement with override."""
        with patch('suitkaise.fdl._int.core.format_state._terminal') as mock_terminal:
            mock_terminal.width = 100
            
            state = _create_format_state(terminal_width=30)  # Below minimum
            
            assert state.terminal_width == 30  # Override should be respected even if below minimum


class TestFormatStateEdgeCases:
    """Test suite for format state edge cases and error conditions."""
    
    def test_format_state_with_none_values(self):
        """Test format state with None values in tuple."""
        values = ("valid", None, "also_valid")
        state = _FormatState(values=values)
        
        assert state.get_next_value() == "valid"
        assert state.get_next_value() is None
        assert state.get_next_value() == "also_valid"
    
    def test_format_state_with_complex_values(self):
        """Test format state with complex value types."""
        values = ([1, 2, 3], {"key": "value"}, Mock(), 42.5)
        state = _FormatState(values=values)
        
        assert state.get_next_value() == [1, 2, 3]
        assert state.get_next_value() == {"key": "value"}
        assert isinstance(state.get_next_value(), Mock)
        assert state.get_next_value() == 42.5
    
    def test_output_streams_with_empty_strings(self):
        """Test output streams with empty string content."""
        state = _FormatState()
        
        # Add empty strings
        state.add_to_output_streams(
            terminal="",
            plain="",
            markdown="",
            html=""
        )
        
        # Empty strings should not be added
        assert state.terminal_output == []
        assert state.plain_output == []
        assert state.markdown_output == []
        assert state.html_output == []
    
    def test_output_streams_with_whitespace_strings(self):
        """Test output streams with whitespace-only content."""
        state = _FormatState()
        
        # Add whitespace strings
        state.add_to_output_streams(
            terminal="   ",
            plain="\n",
            markdown="\t",
            html=" \n\t "
        )
        
        # Whitespace strings should be added
        assert state.terminal_output == ["   "]
        assert state.plain_output == ["\n"]
        assert state.markdown_output == ["\t"]
        assert state.html_output == [" \n\t "]
    
    def test_progress_bar_mode_multiple_start_calls(self):
        """Test multiple calls to start_progress_bar_mode."""
        mock_bar1 = Mock()
        mock_bar2 = Mock()
        state = _FormatState()
        
        # Start with first bar
        state.start_progress_bar_mode(mock_bar1)
        state.queued_terminal_output = ["content1"]
        
        # Start with second bar (should clear previous queued content)
        state.start_progress_bar_mode(mock_bar2)
        
        assert state.active_progress_bar is mock_bar2
        assert state.queued_terminal_output == []  # Should be cleared
    
    def test_copy_with_active_progress_bar(self):
        """Test copying state with active progress bar."""
        mock_bar = Mock()
        original = _FormatState()
        original.start_progress_bar_mode(mock_bar)
        
        copied = original.copy()
        
        # Progress bar state should be reset in copy
        assert copied.bar_active is False
        assert copied.active_progress_bar is None
        
        # Original should still have active bar
        assert original.bar_active is True
        assert original.active_progress_bar is mock_bar
    
    def test_box_content_list_mutation(self):
        """Test that box_content list mutations work correctly."""
        state = _FormatState()
        
        # Add content to box
        state.box_content.append("line1")
        state.box_content.extend(["line2", "line3"])
        
        assert state.box_content == ["line1", "line2", "line3"]
        
        # Test copy independence
        copied = state.copy()
        state.box_content.append("line4")
        
        assert state.box_content == ["line1", "line2", "line3", "line4"]
        assert copied.box_content == ["line1", "line2", "line3"]
    
    def test_value_index_manipulation(self):
        """Test manual value_index manipulation."""
        values = ("a", "b", "c", "d")
        state = _FormatState(values=values)
        
        # Skip first value by incrementing index
        state.value_index = 1
        assert state.get_next_value() == "b"
        
        # Reset index
        state.value_index = 0
        assert state.get_next_value() == "a"
        
        # Set index beyond bounds
        state.value_index = 10
        assert state.has_more_values() is False
        
        with pytest.raises(IndexError):
            state.get_next_value()


class TestFormatStateVisualDemonstration:
    """Visual demonstration tests for format state system."""
    
    def test_visual_format_state_demonstration(self):
        """Visual demonstration of format state capabilities."""
        print("\n" + "="*60)
        print("FORMAT STATE - CAPABILITIES DEMONSTRATION")
        print("="*60)
        
        # Create format state with various settings
        state = _FormatState(
            text_color="blue",
            background_color="yellow",
            bold=True,
            italic=True,
            twelve_hour_time=True,
            timezone="PST",
            in_box=True,
            box_style="rounded",
            box_title="Demo Box",
            justify="center",
            debug_mode=True,
            values=("Hello", "World", 123, True),
            terminal_width=100
        )
        
        print(f"\nFormat State Configuration:")
        print(f"  Text Color: {state.text_color}")
        print(f"  Background: {state.background_color}")
        print(f"  Bold: {state.bold}")
        print(f"  Italic: {state.italic}")
        print(f"  Box Style: {state.box_style}")
        print(f"  Box Title: {state.box_title}")
        print(f"  Justification: {state.justify}")
        print(f"  Debug Mode: {state.debug_mode}")
        print(f"  Terminal Width: {state.terminal_width}")
        print(f"  Box Width: {state.box_width}")
        print(f"  Values: {state.values}")
    
    def test_visual_output_streams_demonstration(self):
        """Visual demonstration of output stream management."""
        print("\n" + "="*60)
        print("FORMAT STATE - OUTPUT STREAMS DEMONSTRATION")
        print("="*60)
        
        state = _FormatState()
        
        print(f"\n1. Normal Mode Output:")
        state.add_to_output_streams(
            terminal="\033[31mRed Terminal Text\033[0m",
            plain="Plain Text Content",
            markdown="**Bold Markdown**",
            html="<b>Bold HTML</b>"
        )
        
        outputs = state.get_final_outputs()
        print(f"  Terminal: {outputs['terminal']}")
        print(f"  Plain: {outputs['plain']}")
        print(f"  Markdown: {outputs['markdown']}")
        print(f"  HTML: {outputs['html']}")
        
        print(f"\n2. Progress Bar Mode (Queued Output):")
        mock_bar = Mock()
        state.start_progress_bar_mode(mock_bar)
        
        state.add_to_output_streams(
            terminal="\033[32mQueued Green Text\033[0m",
            plain="Queued Plain Text"
        )
        
        immediate = state.get_immediate_outputs()
        final = state.get_final_outputs()
        
        print(f"  Immediate Terminal: '{immediate['terminal']}'")
        print(f"  Final Terminal: '{final['terminal']}'")
        print(f"  Bar Active: {state.bar_active}")
        
        print(f"\n3. After Stopping Progress Bar:")
        state.stop_progress_bar_mode(flush_output=True)
        
        final_after_stop = state.get_final_outputs()
        print(f"  Final Terminal: {final_after_stop['terminal']}")
        print(f"  Bar Active: {state.bar_active}")
    
    def test_visual_value_processing_demonstration(self):
        """Visual demonstration of value processing."""
        print("\n" + "="*60)
        print("FORMAT STATE - VALUE PROCESSING DEMONSTRATION")
        print("="*60)
        
        values = ("Hello", "World", 42, True, None, [1, 2, 3])
        state = _FormatState(values=values)
        
        print(f"\nOriginal Values: {values}")
        print(f"Value Index: {state.value_index}")
        print(f"Has More Values: {state.has_more_values()}")
        
        print(f"\nProcessing Values:")
        while state.has_more_values():
            value = state.get_next_value()
            print(f"  Index {state.value_index - 1}: {value} ({type(value).__name__})")
        
        print(f"\nAfter Processing:")
        print(f"  Value Index: {state.value_index}")
        print(f"  Has More Values: {state.has_more_values()}")
        
        # Try to get another value
        try:
            state.get_next_value()
        except IndexError as e:
            print(f"  Error: {e}")
    
    def test_visual_state_copying_demonstration(self):
        """Visual demonstration of state copying."""
        print("\n" + "="*60)
        print("FORMAT STATE - STATE COPYING DEMONSTRATION")
        print("="*60)
        
        # Create original state
        original = _FormatState(
            text_color="red",
            bold=True,
            in_box=True,
            box_title="Original Box",
            values=("original", "values"),
            terminal_width=120
        )
        original.box_content = ["original content"]
        original.terminal_output = ["original output"]
        
        print(f"\nOriginal State:")
        print(f"  Text Color: {original.text_color}")
        print(f"  Bold: {original.bold}")
        print(f"  Box Title: {original.box_title}")
        print(f"  Box Content: {original.box_content}")
        print(f"  Terminal Output: {original.terminal_output}")
        print(f"  Values: {original.values}")
        
        # Create copy
        copied = original.copy()
        
        print(f"\nCopied State:")
        print(f"  Text Color: {copied.text_color}")
        print(f"  Bold: {copied.bold}")
        print(f"  Box Title: {copied.box_title}")
        print(f"  Box Content: {copied.box_content}")
        print(f"  Terminal Output: {copied.terminal_output}")
        print(f"  Values: {copied.values}")
        
        # Modify original
        original.text_color = "blue"
        original.box_content.append("modified content")
        original.terminal_output.append("modified output")
        
        print(f"\nAfter Modifying Original:")
        print(f"  Original Text Color: {original.text_color}")
        print(f"  Copied Text Color: {copied.text_color}")
        print(f"  Original Box Content: {original.box_content}")
        print(f"  Copied Box Content: {copied.box_content}")
        print(f"  Original Terminal Output: {original.terminal_output}")
        print(f"  Copied Terminal Output: {copied.terminal_output}")
    
    def test_visual_reset_methods_demonstration(self):
        """Visual demonstration of reset methods."""
        print("\n" + "="*60)
        print("FORMAT STATE - RESET METHODS DEMONSTRATION")
        print("="*60)
        
        # Create state with various settings
        state = _FormatState(
            text_color="red",
            background_color="blue",
            bold=True,
            italic=True,
            twelve_hour_time=True,
            timezone="EST",
            in_box=True,
            box_style="double",
            box_title="Test Box",
            debug_mode=True
        )
        state.box_content = ["box line 1", "box line 2"]
        state.terminal_output = ["output 1", "output 2"]
        
        def show_state(label):
            print(f"\n{label}:")
            print(f"  Text Color: {state.text_color}")
            print(f"  Bold: {state.bold}")
            print(f"  12hr Time: {state.twelve_hour_time}")
            print(f"  Timezone: {state.timezone}")
            print(f"  In Box: {state.in_box}")
            print(f"  Box Style: {state.box_style}")
            print(f"  Box Content: {state.box_content}")
            print(f"  Debug Mode: {state.debug_mode}")
            print(f"  Terminal Output: {state.terminal_output}")
        
        show_state("Initial State")
        
        # Test individual reset methods
        state.reset_formatting()
        show_state("After reset_formatting()")
        
        state.reset_time_settings()
        show_state("After reset_time_settings()")
        
        state.reset_box_state()
        show_state("After reset_box_state()")
        
        state.reset_debug_mode()
        show_state("After reset_debug_mode()")
        
        state.reset_output_streams()
        show_state("After reset_output_streams()")
        
        # Reset everything and test reset_all_formatting
        state = _FormatState(
            text_color="green",
            bold=True,
            twelve_hour_time=True,
            in_box=True,
            debug_mode=True
        )
        state.box_content = ["content"]
        
        show_state("Before reset_all_formatting()")
        state.reset_all_formatting()
        show_state("After reset_all_formatting()")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestFormatStateVisualDemonstration()
    demo.test_visual_format_state_demonstration()
    demo.test_visual_output_streams_demonstration()
    demo.test_visual_value_processing_demonstration()
    demo.test_visual_state_copying_demonstration()
    demo.test_visual_reset_methods_demonstration()
    
    print("\n" + "="*60)
    print("✅ FORMAT STATE TESTS COMPLETE")
    print("="*60)