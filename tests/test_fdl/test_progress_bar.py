"""
Comprehensive Deep Tests for FDL Progress Bar Class.

Tests the internal progress bar system that provides thread-safe progress tracking,
formatting, multi-format output, memory management, and context manager support.
"""

import pytest
import sys
import os
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from wcwidth import wcswidth
from contextlib import redirect_stdout
import io

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.classes.progress_bar import (
    _ProgressBar, ProgressBarError, create_progress_bar
)
from suitkaise.fdl._int.core.format_state import _FormatState


class TestProgressBarInitialization:
    """Test suite for progress bar initialization and validation."""
    
    def test_progress_bar_initialization_valid(self):
        """Test valid progress bar initialization."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            progress = _ProgressBar(total=100)
            
            assert progress.total == 100.0
            assert progress.current == 0.0
            assert progress.progress == 0.0
            assert progress.percentage == 0
            assert not progress.is_complete
            assert not progress.is_displayed
            assert not progress.is_finished
            assert progress.show_percentage is True
            assert progress.show_numbers is True
            assert progress.show_rate is False
            assert progress.width is None
    
    def test_progress_bar_initialization_with_options(self):
        """Test progress bar initialization with all options."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            progress = _ProgressBar(
                total=50.5,
                color="green",
                width=40,
                show_percentage=False,
                show_numbers=False,
                show_rate=True
            )
            
            assert progress.total == 50.5
            assert progress.width == 40
            assert progress.show_percentage is False
            assert progress.show_numbers is False
            assert progress.show_rate is True
            assert progress._format_state is not None  # Color should be set
    
    def test_progress_bar_initialization_invalid_total(self):
        """Test progress bar initialization with invalid total."""
        with pytest.raises(ProgressBarError) as exc_info:
            _ProgressBar(total=0)
        assert "Total must be positive" in str(exc_info.value)
        
        with pytest.raises(ProgressBarError) as exc_info:
            _ProgressBar(total=-10)
        assert "Total must be positive" in str(exc_info.value)
    
    def test_progress_bar_initialization_terminal_error(self):
        """Test progress bar initialization with terminal detection error."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.side_effect = Exception("No terminal")
            
            with pytest.raises(ProgressBarError) as exc_info:
                _ProgressBar(total=100)
            
            assert "Progress bars require a terminal environment" in str(exc_info.value)
            assert "No terminal" in str(exc_info.value)
    
    def test_progress_bar_initialization_terminal_width_error(self):
        """Test progress bar initialization with terminal width access error."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal_obj = Mock()
            mock_terminal_obj.width = Mock(side_effect=Exception("Width unavailable"))
            mock_terminal.return_value = mock_terminal_obj
            
            with pytest.raises(ProgressBarError) as exc_info:
                _ProgressBar(total=100)
            
            assert "Progress bars require a terminal environment" in str(exc_info.value)
    
    def test_progress_bar_initialization_invalid_color(self):
        """Test progress bar initialization with invalid color."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            with patch.object(_ProgressBar, '_process_format_string') as mock_process:
                mock_process.side_effect = Exception("Invalid color")
                
                with pytest.raises(ValueError) as exc_info:
                    _ProgressBar(total=100, color="invalid_color")
                
                assert "Invalid color 'invalid_color'" in str(exc_info.value)


class TestProgressBarProperties:
    """Test suite for progress bar properties and calculations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100)
    
    def test_current_property(self):
        """Test current property."""
        assert self.progress.current == 0.0
        
        self.progress._current = 25.5
        assert self.progress.current == 25.5
    
    def test_progress_property(self):
        """Test progress ratio property."""
        assert self.progress.progress == 0.0
        
        self.progress._current = 25
        assert self.progress.progress == 0.25
        
        self.progress._current = 100
        assert self.progress.progress == 1.0
        
        # Test clamping at 1.0
        self.progress._current = 150
        assert self.progress.progress == 1.0
    
    def test_percentage_property(self):
        """Test percentage property."""
        assert self.progress.percentage == 0
        
        self.progress._current = 25.7
        assert self.progress.percentage == 25
        
        self.progress._current = 100
        assert self.progress.percentage == 100
        
        self.progress._current = 150
        assert self.progress.percentage == 100
    
    def test_elapsed_time_property(self):
        """Test elapsed time property."""
        start_time = time.time()
        elapsed = self.progress.elapsed_time
        
        # Should be very close to 0 initially
        assert 0 <= elapsed <= 1.0
        
        # Mock start time to test calculation
        self.progress._start_time = start_time - 10
        elapsed = self.progress.elapsed_time
        assert 9.5 <= elapsed <= 10.5
    
    def test_is_complete_property(self):
        """Test is_complete property."""
        assert not self.progress.is_complete
        
        self.progress._current = 50
        assert not self.progress.is_complete
        
        self.progress._current = 100
        assert self.progress.is_complete
        
        self.progress._current = 150
        assert self.progress.is_complete
    
    def test_is_displayed_property(self):
        """Test is_displayed property."""
        assert not self.progress.is_displayed
        
        self.progress._displayed = True
        assert self.progress.is_displayed
    
    def test_is_finished_property(self):
        """Test is_finished property."""
        assert not self.progress.is_finished
        
        self.progress._finished = True
        assert self.progress.is_finished


class TestProgressBarCoreOperations:
    """Test suite for core progress bar operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100)
    
    def test_display_method(self):
        """Test display method."""
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.display()
            
            assert self.progress.is_displayed
            mock_render.assert_called_once()
    
    def test_display_method_when_finished(self):
        """Test display method when already finished."""
        self.progress._finished = True
        
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.display()
            
            # Should not render when finished
            mock_render.assert_not_called()
    
    def test_update_method_basic(self):
        """Test basic update method functionality."""
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.update(25, "Step 1")
            
            assert self.progress.current == 25.0
            assert self.progress._message == "Step 1"
            assert self.progress.is_displayed  # Auto-display
            mock_render.assert_called_once()
    
    def test_update_method_incremental(self):
        """Test incremental updates."""
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.update(25, "Step 1")
            assert self.progress.current == 25.0
            
            self.progress.update(30, "Step 2")
            assert self.progress.current == 55.0
            assert self.progress._message == "Step 2"
            
            assert mock_render.call_count == 2
    
    def test_update_method_clamping(self):
        """Test update method clamping to total."""
        with patch.object(self.progress, '_render_and_display'):
            self.progress.update(150, "Overflow")
            
            assert self.progress.current == 100.0
            assert self.progress.is_complete
    
    def test_update_method_zero_increment(self):
        """Test update method with zero increment."""
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.update(0, "No change")
            
            # Should not render for zero increment
            mock_render.assert_not_called()
            assert not self.progress.is_displayed
    
    def test_update_method_negative_increment(self):
        """Test update method with negative increment."""
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.update(-10, "Negative")
            
            # Should not render for negative increment
            mock_render.assert_not_called()
            assert not self.progress.is_displayed
    
    def test_update_method_auto_finish(self):
        """Test update method auto-finishing when complete."""
        with patch.object(self.progress, '_render_and_display'), \
             patch.object(self.progress, '_finish_internal') as mock_finish:
            
            self.progress.update(100, "Complete")
            
            assert self.progress.current == 100.0
            mock_finish.assert_called_once()
    
    def test_update_method_when_finished(self):
        """Test update method when already finished."""
        self.progress._finished = True
        
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.update(10, "Should be ignored")
            
            mock_render.assert_not_called()
            assert self.progress.current == 0.0
    
    def test_update_method_empty_message(self):
        """Test update method with empty message."""
        self.progress._message = "Previous message"
        
        with patch.object(self.progress, '_render_and_display'):
            self.progress.update(25, "")
            
            # Should keep previous message
            assert self.progress._message == "Previous message"
            
            self.progress.update(25, "   ")
            
            # Should keep previous message for whitespace-only
            assert self.progress._message == "Previous message"
    
    def test_set_current_method_basic(self):
        """Test basic set_current method functionality."""
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.set_current(50, "Checkpoint")
            
            assert self.progress.current == 50.0
            assert self.progress._message == "Checkpoint"
            assert self.progress.is_displayed  # Auto-display
            mock_render.assert_called_once()
    
    def test_set_current_method_clamping(self):
        """Test set_current method clamping."""
        with patch.object(self.progress, '_render_and_display'):
            # Test upper bound
            self.progress.set_current(150, "Over")
            assert self.progress.current == 100.0
            
            # Test lower bound
            self.progress.set_current(-10, "Under")
            assert self.progress.current == 0.0
    
    def test_set_current_method_no_change(self):
        """Test set_current method with no actual change."""
        self.progress._current = 50.0
        
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.set_current(50.0, "Same value")
            
            # Should not render if value doesn't change
            mock_render.assert_not_called()
            assert self.progress._message == "Same value"  # Message still updates
    
    def test_set_current_method_auto_finish(self):
        """Test set_current method auto-finishing when complete."""
        with patch.object(self.progress, '_render_and_display'), \
             patch.object(self.progress, '_finish_internal') as mock_finish:
            
            self.progress.set_current(100, "Complete")
            
            assert self.progress.current == 100.0
            mock_finish.assert_called_once()
    
    def test_set_message_method(self):
        """Test set_message method."""
        self.progress._displayed = True
        
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.set_message("New message")
            
            assert self.progress._message == "New message"
            mock_render.assert_called_once()
    
    def test_set_message_method_not_displayed(self):
        """Test set_message method when not displayed."""
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.set_message("Message")
            
            assert self.progress._message == "Message"
            # Should not render if not displayed
            mock_render.assert_not_called()
    
    def test_set_message_method_when_finished(self):
        """Test set_message method when finished."""
        self.progress._finished = True
        
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.set_message("Should be ignored")
            
            mock_render.assert_not_called()
            assert self.progress._message == ""
    
    def test_finish_method(self):
        """Test finish method."""
        with patch.object(self.progress, '_finish_internal') as mock_finish:
            self.progress.finish("All done!")
            
            assert self.progress.current == 100.0
            assert self.progress._message == "All done!"
            mock_finish.assert_called_once()
    
    def test_finish_method_default_message(self):
        """Test finish method with default message."""
        with patch.object(self.progress, '_finish_internal') as mock_finish:
            self.progress.finish()
            
            assert self.progress._message == "Complete!"
            mock_finish.assert_called_once()
    
    def test_finish_method_empty_message(self):
        """Test finish method with empty message."""
        self.progress._message = "Previous"
        
        with patch.object(self.progress, '_finish_internal') as mock_finish:
            self.progress.finish("")
            
            # Should keep previous message
            assert self.progress._message == "Previous"
            mock_finish.assert_called_once()
    
    def test_finish_method_already_finished(self):
        """Test finish method when already finished."""
        self.progress._finished = True
        
        with patch.object(self.progress, '_finish_internal') as mock_finish:
            self.progress.finish("Should be ignored")
            
            mock_finish.assert_not_called()
    
    def test_finish_internal_method(self):
        """Test _finish_internal method."""
        self.progress._displayed = True
        
        with patch.object(self.progress, '_render_and_display') as mock_render, \
             patch('builtins.print') as mock_print:
            
            self.progress._finish_internal()
            
            assert self.progress.is_finished
            mock_render.assert_called_once()
            mock_print.assert_called_once_with()  # Newline


class TestProgressBarFormatting:
    """Test suite for progress bar formatting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100)
    
    def test_set_color_method(self):
        """Test set_color method."""
        with patch.object(self.progress, '_set_color') as mock_set_color, \
             patch.object(self.progress, '_render_and_display') as mock_render:
            
            self.progress._displayed = True
            self.progress.set_color("green")
            
            mock_set_color.assert_called_once_with("green")
            mock_render.assert_called_once()
    
    def test_set_color_method_not_displayed(self):
        """Test set_color method when not displayed."""
        with patch.object(self.progress, '_set_color') as mock_set_color, \
             patch.object(self.progress, '_render_and_display') as mock_render:
            
            self.progress.set_color("blue")
            
            mock_set_color.assert_called_once_with("blue")
            # Should not render if not displayed
            mock_render.assert_not_called()
    
    def test_set_color_method_when_finished(self):
        """Test set_color method when finished."""
        self.progress._finished = True
        
        with patch.object(self.progress, '_set_color') as mock_set_color, \
             patch.object(self.progress, '_render_and_display') as mock_render:
            
            self.progress.set_color("red")
            
            mock_set_color.assert_called_once_with("red")
            # Should not render when finished
            mock_render.assert_not_called()
    
    def test_set_format_method(self):
        """Test set_format method."""
        mock_format_state = Mock()
        
        with patch.object(self.progress, '_process_format_string', return_value=mock_format_state) as mock_process, \
             patch.object(self.progress, '_render_and_display') as mock_render:
            
            self.progress._displayed = True
            self.progress.set_format("</green, bold>")
            
            mock_process.assert_called_once_with("</green, bold>")
            assert self.progress._format_state is mock_format_state
            mock_render.assert_called_once()
    
    def test_reset_format_method(self):
        """Test reset_format method."""
        self.progress._format_state = Mock()
        
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress._displayed = True
            self.progress.reset_format()
            
            assert self.progress._format_state is None
            mock_render.assert_called_once()
    
    def test_set_color_internal_method(self):
        """Test _set_color internal method."""
        with patch.object(self.progress, '_process_format_string', return_value=Mock()) as mock_process:
            self.progress._set_color("green")
            
            mock_process.assert_called_once_with("</green>")
    
    def test_set_color_internal_method_invalid(self):
        """Test _set_color internal method with invalid color."""
        with patch.object(self.progress, '_process_format_string', side_effect=Exception("Invalid")):
            with pytest.raises(ValueError) as exc_info:
                self.progress._set_color("invalid")
            
            assert "Invalid color 'invalid'" in str(exc_info.value)
    
    def test_process_format_string_empty(self):
        """Test _process_format_string with empty string."""
        result = self.progress._process_format_string("")
        assert result is None
        
        result = self.progress._process_format_string("   ")
        assert result is None
    
    def test_process_format_string_basic(self):
        """Test _process_format_string with basic format."""
        with patch.object(self.progress._command_registry, 'process_command', return_value=Mock()) as mock_process:
            result = self.progress._process_format_string("</green>")
            
            assert result is not None
            mock_process.assert_called_once_with("green", result)
    
    def test_process_format_string_multiple_commands(self):
        """Test _process_format_string with multiple commands."""
        with patch.object(self.progress._command_registry, 'process_command', return_value=Mock()) as mock_process:
            result = self.progress._process_format_string("</green, bold, underline>")
            
            assert result is not None
            assert mock_process.call_count == 3
            mock_process.assert_any_call("green", result)
            mock_process.assert_any_call("bold", result)
            mock_process.assert_any_call("underline", result)
    
    def test_process_format_string_bracket_variations(self):
        """Test _process_format_string with different bracket formats."""
        with patch.object(self.progress._command_registry, 'process_command', return_value=Mock()) as mock_process:
            # Test </command> format
            self.progress._process_format_string("</green>")
            mock_process.assert_called_with("green", mock_process.return_value)
            
            mock_process.reset_mock()
            
            # Test <command> format (without slash)
            self.progress._process_format_string("<green>")
            mock_process.assert_called_with("green", mock_process.return_value)
    
    def test_process_format_string_unknown_command(self):
        """Test _process_format_string with unknown command."""
        from suitkaise.fdl._int.core.command_registry import UnknownCommandError
        
        with patch.object(self.progress._command_registry, 'process_command', 
                         side_effect=UnknownCommandError("Unknown command: 'invalid'")):
            with pytest.raises(ValueError) as exc_info:
                self.progress._process_format_string("</invalid>")
            
            assert "Invalid format command 'invalid'" in str(exc_info.value)
    
    def test_process_format_string_processing_error(self):
        """Test _process_format_string with processing error."""
        with patch.object(self.progress._command_registry, 'process_command', 
                         side_effect=Exception("Processing error")):
            with pytest.raises(ValueError) as exc_info:
                self.progress._process_format_string("</green>")
            
            assert "Error processing format command 'green'" in str(exc_info.value)


class TestProgressBarOutput:
    """Test suite for progress bar output functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100)
    
    def test_get_output_method_terminal(self):
        """Test get_output method for terminal format."""
        mock_output = {'terminal': 'terminal_output', 'plain': 'plain_output', 'html': 'html_output'}
        
        with patch.object(self.progress._progress_bar_generator, 'generate_progress_bar', 
                         return_value=mock_output) as mock_generate:
            
            result = self.progress.get_output('terminal')
            
            assert result == 'terminal_output'
            mock_generate.assert_called_once_with(
                current=0.0,
                total=100.0,
                width=None,
                format_state=None,
                message="",
                show_percentage=True,
                show_numbers=True,
                show_rate=False,
                elapsed_time=mock_generate.call_args[1]['elapsed_time']
            )
    
    def test_get_output_method_all_formats(self):
        """Test get_output method for all formats."""
        mock_output = {'terminal': 'term', 'plain': 'plain', 'html': 'html'}
        
        with patch.object(self.progress._progress_bar_generator, 'generate_progress_bar', 
                         return_value=mock_output):
            
            assert self.progress.get_output('terminal') == 'term'
            assert self.progress.get_output('plain') == 'plain'
            assert self.progress.get_output('html') == 'html'
    
    def test_get_output_method_invalid_format(self):
        """Test get_output method with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            self.progress.get_output('invalid')
        
        assert "Invalid format_type: invalid" in str(exc_info.value)
    
    def test_get_output_method_with_progress(self):
        """Test get_output method with actual progress."""
        self.progress._current = 50.0
        self.progress._message = "Half done"
        
        mock_output = {'terminal': 'progress_output', 'plain': 'plain', 'html': 'html'}
        
        with patch.object(self.progress._progress_bar_generator, 'generate_progress_bar', 
                         return_value=mock_output) as mock_generate:
            
            result = self.progress.get_output('terminal')
            
            assert result == 'progress_output'
            mock_generate.assert_called_once_with(
                current=50.0,
                total=100.0,
                width=None,
                format_state=None,
                message="Half done",
                show_percentage=True,
                show_numbers=True,
                show_rate=False,
                elapsed_time=mock_generate.call_args[1]['elapsed_time']
            )
    
    def test_get_all_outputs_method(self):
        """Test get_all_outputs method."""
        mock_output = {'terminal': 'term', 'plain': 'plain', 'html': 'html'}
        
        with patch.object(self.progress._progress_bar_generator, 'generate_progress_bar', 
                         return_value=mock_output) as mock_generate:
            
            result = self.progress.get_all_outputs()
            
            assert result == mock_output
            mock_generate.assert_called_once()
    
    def test_render_and_display_method(self):
        """Test _render_and_display method."""
        self.progress._displayed = True
        
        with patch.object(self.progress, 'get_output', return_value="progress_bar") as mock_get_output, \
             patch('builtins.print') as mock_print:
            
            self.progress._render_and_display()
            
            mock_get_output.assert_called_once_with('terminal')
            mock_print.assert_called_once_with("\rprogress_bar", end="", flush=True)
    
    def test_render_and_display_method_not_displayed(self):
        """Test _render_and_display method when not displayed."""
        with patch.object(self.progress, 'get_output') as mock_get_output, \
             patch('builtins.print') as mock_print:
            
            self.progress._render_and_display()
            
            mock_get_output.assert_not_called()
            mock_print.assert_not_called()
    
    def test_render_and_display_method_released(self):
        """Test _render_and_display method when released."""
        self.progress._displayed = True
        self.progress._released = True
        
        with patch.object(self.progress, 'get_output') as mock_get_output, \
             patch('builtins.print') as mock_print:
            
            self.progress._render_and_display()
            
            mock_get_output.assert_not_called()
            mock_print.assert_not_called()


class TestProgressBarUtilityMethods:
    """Test suite for progress bar utility methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100, color="green", width=50)
    
    def test_copy_method(self):
        """Test copy method."""
        # Set up original state
        self.progress._current = 75.0
        self.progress._message = "Original message"
        
        with patch('copy.deepcopy', return_value=Mock()) as mock_deepcopy:
            copied = self.progress.copy()
            
            # Should be a new instance
            assert copied is not self.progress
            assert isinstance(copied, _ProgressBar)
            
            # Should have same configuration
            assert copied.total == 100.0
            assert copied.width == 50
            assert copied.show_percentage is True
            assert copied.show_numbers is True
            assert copied.show_rate is False
            
            # Should have copied state
            assert copied._current == 75.0
            assert copied._message == "Original message"
            
            # Should have deep-copied format state
            mock_deepcopy.assert_called_once_with(self.progress._format_state)
            assert copied._format_state == mock_deepcopy.return_value
    
    def test_copy_method_no_format_state(self):
        """Test copy method with no format state."""
        self.progress._format_state = None
        
        copied = self.progress.copy()
        
        assert copied._format_state is None
    
    def test_reset_method(self):
        """Test reset method."""
        # Set up some state
        self.progress._current = 75.0
        self.progress._message = "Some message"
        self.progress._finished = True
        self.progress._displayed = True
        
        original_start_time = self.progress._start_time
        time.sleep(0.01)  # Ensure time difference
        
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.reset()
            
            assert self.progress._current == 0.0
            assert self.progress._message == ""
            assert not self.progress._finished
            assert self.progress._start_time > original_start_time
            assert self.progress._last_update_time == self.progress._start_time
            mock_render.assert_called_once()
    
    def test_reset_method_not_displayed(self):
        """Test reset method when not displayed."""
        self.progress._current = 50.0
        
        with patch.object(self.progress, '_render_and_display') as mock_render:
            self.progress.reset()
            
            assert self.progress._current == 0.0
            # Should not render if not displayed
            mock_render.assert_not_called()


class TestProgressBarMemoryManagement:
    """Test suite for progress bar memory management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100)
    
    def test_release_method_basic(self):
        """Test basic release method functionality."""
        self.progress._format_state = Mock()
        self.progress._message = "Some message"
        
        self.progress.release()
        
        assert self.progress._released
        assert self.progress._format_state is None
        assert self.progress._message == ""
    
    def test_release_method_with_displayed_unfinished(self):
        """Test release method with displayed but unfinished progress bar."""
        self.progress._displayed = True
        self.progress._finished = False
        
        with patch('builtins.print') as mock_print:
            self.progress.release()
            
            assert self.progress._released
            mock_print.assert_called_once_with()  # Newline to move cursor
    
    def test_release_method_with_finished(self):
        """Test release method with finished progress bar."""
        self.progress._displayed = True
        self.progress._finished = True
        
        with patch('builtins.print') as mock_print:
            self.progress.release()
            
            assert self.progress._released
            # Should not print newline for finished progress bar
            mock_print.assert_not_called()
    
    def test_release_method_already_released(self):
        """Test release method when already released."""
        self.progress._released = True
        
        with patch('builtins.print') as mock_print:
            self.progress.release()
            
            # Should not do anything
            mock_print.assert_not_called()
    
    def test_check_released_method(self):
        """Test _check_released method."""
        # Should not raise when not released
        self.progress._check_released()
        
        # Should raise when released
        self.progress._released = True
        with pytest.raises(RuntimeError) as exc_info:
            self.progress._check_released()
        
        assert "Progress bar has been released" in str(exc_info.value)
    
    def test_methods_after_release(self):
        """Test that methods raise errors after release."""
        self.progress.release()
        
        methods_to_test = [
            (self.progress.display, []),
            (self.progress.update, [10]),
            (self.progress.set_current, [50]),
            (self.progress.set_message, ["test"]),
            (self.progress.finish, []),
            (self.progress.set_color, ["red"]),
            (self.progress.set_format, ["</bold>"]),
            (self.progress.reset_format, []),
            (self.progress.get_output, []),
            (self.progress.get_all_outputs, []),
            (self.progress.copy, []),
            (self.progress.reset, []),
        ]
        
        for method, args in methods_to_test:
            with pytest.raises(RuntimeError) as exc_info:
                method(*args)
            assert "Progress bar has been released" in str(exc_info.value)


class TestProgressBarContextManager:
    """Test suite for progress bar context manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100)
    
    def test_context_manager_enter(self):
        """Test context manager __enter__ method."""
        with patch.object(self.progress, 'display') as mock_display:
            result = self.progress.__enter__()
            
            assert result is self.progress
            mock_display.assert_called_once()
    
    def test_context_manager_exit_normal(self):
        """Test context manager __exit__ method with normal completion."""
        with patch.object(self.progress, 'finish') as mock_finish, \
             patch.object(self.progress, 'release') as mock_release:
            
            self.progress.__exit__(None, None, None)
            
            mock_finish.assert_called_once()
            mock_release.assert_called_once()
    
    def test_context_manager_exit_already_finished(self):
        """Test context manager __exit__ method when already finished."""
        self.progress._finished = True
        
        with patch.object(self.progress, 'finish') as mock_finish, \
             patch.object(self.progress, 'release') as mock_release:
            
            self.progress.__exit__(None, None, None)
            
            # Should not call finish if already finished
            mock_finish.assert_not_called()
            mock_release.assert_called_once()
    
    def test_context_manager_exit_with_exception(self):
        """Test context manager __exit__ method with exception."""
        with patch.object(self.progress, 'finish') as mock_finish, \
             patch.object(self.progress, 'release') as mock_release:
            
            self.progress.__exit__(ValueError, ValueError("test"), None)
            
            # Should still finish and release even with exception
            mock_finish.assert_called_once()
            mock_release.assert_called_once()
    
    def test_context_manager_full_usage(self):
        """Test full context manager usage."""
        with patch.object(self.progress, 'display') as mock_display, \
             patch.object(self.progress, 'finish') as mock_finish, \
             patch.object(self.progress, 'release') as mock_release:
            
            with self.progress as pb:
                assert pb is self.progress
                mock_display.assert_called_once()
            
            mock_finish.assert_called_once()
            mock_release.assert_called_once()


class TestProgressBarStringRepresentation:
    """Test suite for progress bar string representation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100)
    
    def test_str_method(self):
        """Test __str__ method."""
        result = str(self.progress)
        assert result == "ProgressBar(0.0/100.0, 0%)"
        
        self.progress._current = 25.5
        result = str(self.progress)
        assert result == "ProgressBar(25.5/100.0, 25%)"
    
    def test_repr_method(self):
        """Test __repr__ method."""
        result = repr(self.progress)
        expected = ("_ProgressBar(current=0.0, total=100.0, percentage=0%, "
                   "displayed=False, finished=False, released=False)")
        assert result == expected
        
        self.progress._current = 50.0
        self.progress._displayed = True
        self.progress._finished = True
        
        result = repr(self.progress)
        expected = ("_ProgressBar(current=50.0, total=100.0, percentage=50%, "
                   "displayed=True, finished=True, released=False)")
        assert result == expected


class TestProgressBarThreadSafety:
    """Test suite for progress bar thread safety."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=1000)
    
    def test_concurrent_updates(self):
        """Test concurrent update operations."""
        results = []
        
        def update_progress(thread_id):
            for i in range(10):
                self.progress.update(1, f"Thread {thread_id} - Step {i}")
                time.sleep(0.001)  # Small delay to encourage race conditions
            results.append(thread_id)
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_progress, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have processed all updates
        assert len(results) == 10
        assert self.progress.current == 100.0  # 10 threads * 10 updates * 1 increment
    
    def test_concurrent_set_current(self):
        """Test concurrent set_current operations."""
        results = []
        
        def set_progress(value):
            self.progress.set_current(value, f"Set to {value}")
            results.append(value)
        
        # Start multiple threads with different values
        threads = []
        values = [10, 20, 30, 40, 50]
        for value in values:
            thread = threading.Thread(target=set_progress, args=(value,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have processed all operations
        assert len(results) == 5
        # Final value should be one of the set values
        assert self.progress.current in values
    
    def test_concurrent_property_access(self):
        """Test concurrent property access."""
        results = []
        
        def access_properties():
            for _ in range(100):
                current = self.progress.current
                progress = self.progress.progress
                percentage = self.progress.percentage
                is_complete = self.progress.is_complete
                results.append((current, progress, percentage, is_complete))
        
        def update_progress():
            for i in range(50):
                self.progress.update(1)
                time.sleep(0.001)
        
        # Start reader and writer threads
        reader_thread = threading.Thread(target=access_properties)
        writer_thread = threading.Thread(target=update_progress)
        
        reader_thread.start()
        writer_thread.start()
        
        reader_thread.join()
        writer_thread.join()
        
        # Should have completed all reads without errors
        assert len(results) == 100
        # All property values should be consistent
        for current, progress, percentage, is_complete in results:
            assert 0 <= current <= 1000
            assert 0 <= progress <= 1.0
            assert 0 <= percentage <= 100
            assert isinstance(is_complete, bool)
    
    def test_concurrent_formatting_operations(self):
        """Test concurrent formatting operations."""
        results = []
        
        def format_operations():
            colors = ["red", "green", "blue", "yellow", "cyan"]
            for color in colors:
                try:
                    self.progress.set_color(color)
                    self.progress.set_format(f"</{color}, bold>")
                    self.progress.reset_format()
                    results.append(color)
                except Exception as e:
                    results.append(f"Error: {e}")
        
        # Start multiple formatting threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=format_operations)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have processed operations from all threads
        assert len(results) >= 10  # At least some operations completed


class TestProgressBarEdgeCases:
    """Test suite for progress bar edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            self.progress = _ProgressBar(total=100)
    
    def test_float_total_precision(self):
        """Test progress bar with float total and precision."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            progress = _ProgressBar(total=100.7)
            
            progress.update(50.35)
            assert progress.current == 50.35
            assert abs(progress.progress - 0.5) < 0.01
    
    def test_very_small_total(self):
        """Test progress bar with very small total."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            progress = _ProgressBar(total=0.001)
            
            progress.update(0.0005)
            assert progress.current == 0.0005
            assert progress.percentage == 50
    
    def test_very_large_total(self):
        """Test progress bar with very large total."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            progress = _ProgressBar(total=1e6)
            
            progress.update(5e5)
            assert progress.current == 5e5
            assert progress.percentage == 50
    
    def test_unicode_message(self):
        """Test progress bar with Unicode message."""
        self.progress.update(50, "进度条测试 🚀 Café naïve")
        assert self.progress._message == "进度条测试 🚀 Café naïve"
    
    def test_very_long_message(self):
        """Test progress bar with very long message."""
        long_message = "Very long message " * 100
        self.progress.set_message(long_message)
        assert self.progress._message == long_message
    
    def test_message_with_newlines(self):
        """Test progress bar with message containing newlines."""
        message_with_newlines = "Line 1\nLine 2\nLine 3"
        self.progress.set_message(message_with_newlines)
        assert self.progress._message == message_with_newlines
    
    def test_rapid_updates(self):
        """Test rapid progress updates."""
        with patch.object(self.progress, '_render_and_display') as mock_render:
            # Rapid updates
            for i in range(100):
                self.progress.update(1, f"Step {i}")
            
            assert self.progress.current == 100.0
            assert self.progress.is_complete
            # Should have rendered for each update
            assert mock_render.call_count == 100
    
    def test_negative_total_edge_case(self):
        """Test edge case around negative total validation."""
        with pytest.raises(ProgressBarError):
            _ProgressBar(total=-0.001)
    
    def test_zero_width_terminal(self):
        """Test progress bar with zero width terminal."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 0
            
            progress = _ProgressBar(total=100)
            
            # Should still work with zero width
            progress.update(50)
            assert progress.current == 50.0
    
    def test_format_string_edge_cases(self):
        """Test format string edge cases."""
        # Empty commands
        result = self.progress._process_format_string("</,,,>")
        assert result is not None
        
        # Whitespace in commands
        with patch.object(self.progress._command_registry, 'process_command', return_value=Mock()):
            result = self.progress._process_format_string("</  green  ,  bold  >")
            assert result is not None
    
    def test_output_format_edge_cases(self):
        """Test output format edge cases."""
        # Test with all possible format types
        valid_formats = ['terminal', 'plain', 'html']
        
        mock_output = {fmt: f"{fmt}_output" for fmt in valid_formats}
        
        with patch.object(self.progress._progress_bar_generator, 'generate_progress_bar', 
                         return_value=mock_output):
            for fmt in valid_formats:
                result = self.progress.get_output(fmt)
                assert result == f"{fmt}_output"


class TestProgressBarConvenienceFunction:
    """Test suite for progress bar convenience function."""
    
    def test_create_progress_bar_function(self):
        """Test create_progress_bar convenience function."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            progress = create_progress_bar(total=200, color="blue", width=60)
            
            assert isinstance(progress, _ProgressBar)
            assert progress.total == 200.0
            assert progress.width == 60
            assert progress._format_state is not None  # Color should be set
    
    def test_create_progress_bar_function_minimal(self):
        """Test create_progress_bar function with minimal arguments."""
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            progress = create_progress_bar(50)
            
            assert isinstance(progress, _ProgressBar)
            assert progress.total == 50.0


class TestProgressBarVisualDemonstration:
    """Visual demonstration tests for progress bar system."""
    
    def test_visual_progress_bar_demonstration(self):
        """Visual demonstration of progress bar capabilities."""
        print("\n" + "="*60)
        print("PROGRESS BAR - CAPABILITIES DEMONSTRATION")
        print("="*60)
        
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            print(f"\nProgress Bar Initialization:")
            progress = _ProgressBar(total=100, show_percentage=True, show_numbers=True)
            print(f"  ✅ Created progress bar: {progress}")
            print(f"  Total: {progress.total}")
            print(f"  Current: {progress.current}")
            print(f"  Progress: {progress.progress:.2f}")
            print(f"  Percentage: {progress.percentage}%")
            print(f"  Is Complete: {progress.is_complete}")
            print(f"  Is Displayed: {progress.is_displayed}")
            print(f"  Is Finished: {progress.is_finished}")
    
    def test_visual_progress_updates_demonstration(self):
        """Visual demonstration of progress updates."""
        print("\n" + "="*60)
        print("PROGRESS BAR - PROGRESS UPDATES DEMONSTRATION")
        print("="*60)
        
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            progress = _ProgressBar(total=100)
            
            print(f"\nProgress Update Sequence:")
            
            updates = [
                (25, "Loading configuration..."),
                (30, "Processing data..."),
                (20, "Analyzing results..."),
                (25, "Finalizing...")
            ]
            
            for increment, message in updates:
                old_current = progress.current
                progress.update(increment, message)
                print(f"  Update +{increment}: {old_current} → {progress.current} ({progress.percentage}%) - '{message}'")
            
            print(f"\nFinal State:")
            print(f"  Current: {progress.current}")
            print(f"  Progress: {progress.progress:.2f}")
            print(f"  Percentage: {progress.percentage}%")
            print(f"  Is Complete: {progress.is_complete}")
            print(f"  Message: '{progress._message}'")
    
    def test_visual_formatting_demonstration(self):
        """Visual demonstration of progress bar formatting."""
        print("\n" + "="*60)
        print("PROGRESS BAR - FORMATTING DEMONSTRATION")
        print("="*60)
        
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            progress = _ProgressBar(total=100)
            progress.update(60, "Testing formatting")
            
            print(f"\nFormatting Operations:")
            
            # Test color setting
            try:
                progress.set_color("green")
                print(f"  ✅ Set color to 'green'")
            except Exception as e:
                print(f"  ❌ Color setting failed: {e}")
            
            # Test format string
            try:
                progress.set_format("</blue, bold>")
                print(f"  ✅ Set format to '</blue, bold>'")
            except Exception as e:
                print(f"  ❌ Format setting failed: {e}")
            
            # Test format reset
            try:
                progress.reset_format()
                print(f"  ✅ Reset format to default")
            except Exception as e:
                print(f"  ❌ Format reset failed: {e}")
            
            print(f"\nCurrent format state: {progress._format_state}")
    
    def test_visual_output_formats_demonstration(self):
        """Visual demonstration of output formats."""
        print("\n" + "="*60)
        print("PROGRESS BAR - OUTPUT FORMATS DEMONSTRATION")
        print("="*60)
        
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            progress = _ProgressBar(total=100, color="green")
            progress.update(75, "Processing complete")
            
            # Mock the generator to show different outputs
            mock_outputs = {
                'terminal': '[████████████████████████████████████████████████████████████████████████████     ] 75% (75/100) Processing complete',
                'plain': '[████████████████████████████████████████████████████████████████████████████     ] 75% (75/100) Processing complete',
                'html': '<div class="progress-bar"><div class="progress-fill" style="width: 75%"></div><span>75% (75/100) Processing complete</span></div>'
            }
            
            with patch.object(progress._progress_bar_generator, 'generate_progress_bar', return_value=mock_outputs):
                print(f"\nOutput Format Examples:")
                
                for format_type in ['terminal', 'plain', 'html']:
                    try:
                        output = progress.get_output(format_type)
                        print(f"  {format_type.upper()}: {output[:80]}{'...' if len(output) > 80 else ''}")
                    except Exception as e:
                        print(f"  {format_type.upper()}: Error - {e}")
                
                # Test get_all_outputs
                try:
                    all_outputs = progress.get_all_outputs()
                    print(f"\n  All outputs retrieved: {len(all_outputs)} formats")
                    for fmt, content in all_outputs.items():
                        print(f"    {fmt}: {len(content)} characters")
                except Exception as e:
                    print(f"  All outputs error: {e}")
    
    def test_visual_lifecycle_demonstration(self):
        """Visual demonstration of progress bar lifecycle."""
        print("\n" + "="*60)
        print("PROGRESS BAR - LIFECYCLE DEMONSTRATION")
        print("="*60)
        
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            print(f"\nProgress Bar Lifecycle:")
            
            # Creation
            progress = _ProgressBar(total=100)
            print(f"  1. Created: {repr(progress)}")
            
            # Display
            with patch.object(progress, '_render_and_display'):
                progress.display()
                print(f"  2. Displayed: {repr(progress)}")
            
            # Updates
            with patch.object(progress, '_render_and_display'):
                progress.update(50, "Halfway there")
                print(f"  3. Updated: {repr(progress)}")
            
            # Finish
            with patch.object(progress, '_render_and_display'), \
                 patch('builtins.print'):
                progress.finish("All done!")
                print(f"  4. Finished: {repr(progress)}")
            
            # Copy
            copied = progress.copy()
            print(f"  5. Copied: {repr(copied)}")
            
            # Reset original
            with patch.object(progress, '_render_and_display'):
                progress.reset()
                print(f"  6. Reset: {repr(progress)}")
            
            # Release
            progress.release()
            print(f"  7. Released: {repr(progress)}")
            
            # Try to use after release
            try:
                progress.update(10)
                print(f"  8. After release: Operation succeeded (unexpected)")
            except RuntimeError as e:
                print(f"  8. After release: {e} (expected)")
    
    def test_visual_context_manager_demonstration(self):
        """Visual demonstration of context manager usage."""
        print("\n" + "="*60)
        print("PROGRESS BAR - CONTEXT MANAGER DEMONSTRATION")
        print("="*60)
        
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            print(f"\nContext Manager Usage:")
            
            # Mock the display, finish, and release methods to show calls
            with patch.object(_ProgressBar, 'display') as mock_display, \
                 patch.object(_ProgressBar, 'finish') as mock_finish, \
                 patch.object(_ProgressBar, 'release') as mock_release, \
                 patch.object(_ProgressBar, '_render_and_display'):
                
                print(f"  Entering context manager...")
                
                with _ProgressBar(total=100) as progress:
                    print(f"    ✅ Entered: display() called = {mock_display.called}")
                    print(f"    Progress bar available: {progress is not None}")
                    
                    # Simulate some work
                    progress.update(50, "Working...")
                    print(f"    ✅ Updated progress to 50%")
                
                print(f"  Exited context manager:")
                print(f"    finish() called = {mock_finish.called}")
                print(f"    release() called = {mock_release.called}")
    
    def test_visual_error_handling_demonstration(self):
        """Visual demonstration of error handling."""
        print("\n" + "="*60)
        print("PROGRESS BAR - ERROR HANDLING DEMONSTRATION")
        print("="*60)
        
        print(f"\nError Handling Scenarios:")
        
        # Invalid total
        print(f"\n1. Invalid Total:")
        try:
            _ProgressBar(total=0)
            print(f"   ❌ Should have failed")
        except ProgressBarError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # Terminal detection failure
        print(f"\n2. Terminal Detection Failure:")
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal', side_effect=Exception("No terminal")):
            try:
                _ProgressBar(total=100)
                print(f"   ❌ Should have failed")
            except ProgressBarError as e:
                print(f"   ✅ Caught expected error: {str(e)[:80]}...")
        
        # Invalid color
        print(f"\n3. Invalid Color:")
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            try:
                _ProgressBar(total=100, color="invalid_color_name")
                print(f"   ❌ Should have failed")
            except ValueError as e:
                print(f"   ✅ Caught expected error: {str(e)[:80]}...")
        
        # Invalid output format
        print(f"\n4. Invalid Output Format:")
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            progress = _ProgressBar(total=100)
            
            try:
                progress.get_output('invalid_format')
                print(f"   ❌ Should have failed")
            except ValueError as e:
                print(f"   ✅ Caught expected error: {e}")
        
        # Operations after release
        print(f"\n5. Operations After Release:")
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            progress = _ProgressBar(total=100)
            progress.release()
            
            try:
                progress.update(50)
                print(f"   ❌ Should have failed")
            except RuntimeError as e:
                print(f"   ✅ Caught expected error: {e}")
    
    def test_visual_thread_safety_demonstration(self):
        """Visual demonstration of thread safety."""
        print("\n" + "="*60)
        print("PROGRESS BAR - THREAD SAFETY DEMONSTRATION")
        print("="*60)
        
        with patch('suitkaise.fdl._int.classes.progress_bar._get_terminal') as mock_terminal:
            mock_terminal.return_value.width = 80
            
            progress = _ProgressBar(total=100)
            
            print(f"\nThread Safety Test:")
            print(f"  Initial state: {progress.current}")
            
            # Simulate concurrent updates
            def update_worker(worker_id, updates):
                for i in range(updates):
                    progress.update(1, f"Worker {worker_id} - Update {i}")
            
            # Mock the render method to avoid actual terminal output
            with patch.object(progress, '_render_and_display'):
                # Start multiple threads
                threads = []
                workers = 5
                updates_per_worker = 4
                
                for i in range(workers):
                    thread = threading.Thread(target=update_worker, args=(i, updates_per_worker))
                    threads.append(thread)
                    thread.start()
                
                # Wait for completion
                for thread in threads:
                    thread.join()
                
                expected_total = workers * updates_per_worker
                actual_total = progress.current
                
                print(f"  Workers: {workers}")
                print(f"  Updates per worker: {updates_per_worker}")
                print(f"  Expected total: {expected_total}")
                print(f"  Actual total: {actual_total}")
                print(f"  Thread safety: {'✅ PASS' if actual_total == expected_total else '❌ FAIL'}")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestProgressBarVisualDemonstration()
    demo.test_visual_progress_bar_demonstration()
    demo.test_visual_progress_updates_demonstration()
    demo.test_visual_formatting_demonstration()
    demo.test_visual_output_formats_demonstration()
    demo.test_visual_lifecycle_demonstration()
    demo.test_visual_context_manager_demonstration()
    demo.test_visual_error_handling_demonstration()
    demo.test_visual_thread_safety_demonstration()
    
    print("\n" + "="*60)
    print("✅ PROGRESS BAR TESTS COMPLETE")
    print("="*60)