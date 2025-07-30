# setup/progress_bar_generator.py
"""
Progress Bar Generator for FDL.

Handles the generation of formatted progress bars with proper visual rendering,
text formatting, and multi-format output support.
"""

import re
import time
from typing import List, Dict, Tuple, Optional, Union, Any
from dataclasses import dataclass
from .unicode import _get_unicode_support
from .terminal import _get_terminal
from ..core.format_state import _FormatState
from ..core.command_registry import _CommandRegistry, UnknownCommandError
# Import processors to ensure registration
from ..processors import commands


@dataclass
class _ProgressBarDimensions:
    """Calculated dimensions for a progress bar."""
    bar_width: int          # Width of the actual bar
    total_width: int        # Total width including labels
    terminal_width: int     # Available terminal width


class _ProgressBarGenerator:
    """
    Generator for creating formatted progress bars with proper visual rendering.
    
    Features:
    - Unicode block characters for smooth progress visualization
    - ASCII fallback for compatibility
    - Multi-format output (terminal, plain, HTML)
    - Format state integration for styling
    - Thread-safe rendering
    - Customizable width and colors
    """
    
    # Unicode blocks for smooth progress (8 levels of precision)
    UNICODE_BLOCKS = ['█', '▉', '▊', '▋', '▌', '▍', '▎', '▏']
    ASCII_BLOCKS = ['#', '#', '#', '#', '#', '#', '#', '.']
    
    def __init__(self):
        """Initialize the progress bar generator."""
        self._unicode_support = _get_unicode_support()
        self._terminal = _get_terminal()
        # CommandRegistry is a class with class methods, not instantiated
        
        # Choose character set based on Unicode support
        self._supports_unicode = self._unicode_support.supports_progress_blocks
        self.blocks = self.UNICODE_BLOCKS if self._supports_unicode else self.ASCII_BLOCKS
    
    def generate_progress_bar(self, current: float, total: float, 
                             width: Optional[int] = None,
                             format_state: Optional[_FormatState] = None,
                             message: str = "",
                             show_percentage: bool = True,
                             show_numbers: bool = True,
                             show_rate: bool = False,
                             elapsed_time: float = 0.0) -> Dict[str, str]:
        """
        Generate a formatted progress bar in multiple output formats.
        
        Args:
            current: Current progress value
            total: Total/maximum value
            width: Fixed width for the bar (None for auto-sizing)
            format_state: Formatting to apply to the bar
            message: Optional message to display
            show_percentage: Whether to show percentage
            show_numbers: Whether to show current/total numbers
            show_rate: Whether to show rate information
            elapsed_time: Elapsed time for rate calculation
            
        Returns:
            Dict with keys: 'terminal', 'plain', 'html'
        """
        # Ensure valid values
        current = max(0.0, min(total, float(current)))
        total = max(0.001, float(total))  # Prevent division by zero
        progress = current / total
        
        # Calculate dimensions
        dimensions = self._calculate_dimensions(width, message, 
                                              show_percentage, show_numbers, show_rate)
        
        # Generate different output formats
        return {
            'terminal': self._generate_terminal_output(
                current, total, progress, dimensions, format_state, 
                message, show_percentage, show_numbers, show_rate, elapsed_time
            ),
            'plain': self._generate_plain_output(
                current, total, progress, dimensions, message, 
                show_percentage, show_numbers, show_rate, elapsed_time
            ),
            'html': self._generate_html_output(
                current, total, progress, message, 
                show_percentage, show_numbers, show_rate, elapsed_time
            )
        }
    
    def _calculate_dimensions(self, fixed_width: Optional[int], message: str,
                            show_percentage: bool, show_numbers: bool, 
                            show_rate: bool) -> _ProgressBarDimensions:
        """Calculate optimal dimensions for the progress bar."""
        terminal_width = self._terminal.width
        
        # Calculate space needed for labels
        label_space = 0
        if show_percentage:
            label_space += 5  # " 100%"
        if show_numbers:
            label_space += 20  # " (999999/999999)"
        if show_rate:
            label_space += 15  # " 999.9/s"
        
        # Account for brackets and spaces
        bracket_space = 4  # "[] " + padding
        
        # Calculate bar width
        if fixed_width:
            bar_width = max(10, fixed_width)
            total_width = bar_width + bracket_space + label_space
        else:
            available_width = terminal_width - bracket_space - label_space
            bar_width = max(10, min(60, available_width))  # Between 10-60 chars
            total_width = bar_width + bracket_space + label_space
        
        return _ProgressBarDimensions(bar_width, total_width, terminal_width)
    
    def _generate_terminal_output(self, current: float, total: float, progress: float,
                                 dimensions: _ProgressBarDimensions, 
                                 format_state: Optional[_FormatState],
                                 message: str, show_percentage: bool, 
                                 show_numbers: bool, show_rate: bool,
                                 elapsed_time: float) -> str:
        """Generate terminal output with ANSI formatting."""
        # Generate the visual bar
        bar_content = self._render_bar(progress, dimensions.bar_width)
        
        # Apply formatting if provided
        if format_state:
            bar_content = self._apply_format_state(bar_content, format_state)
        
        # Build the complete progress bar
        parts = [f"[{bar_content}]"]
        
        # Add percentage
        if show_percentage:
            percentage = int(progress * 100)
            parts.append(f" {percentage:3d}%")
        
        # Add numbers
        if show_numbers:
            parts.append(f" ({current:.0f}/{total:.0f})")
        
        # Add rate
        if show_rate and elapsed_time > 0:
            rate = current / elapsed_time
            parts.append(f" {rate:.1f}/s")
        
        result = "".join(parts)
        
        # Add message on new line if provided
        if message.strip():
            result += f"\n{message}"
        
        return result
    
    def _generate_plain_output(self, current: float, total: float, progress: float,
                              dimensions: _ProgressBarDimensions,
                              message: str, show_percentage: bool, 
                              show_numbers: bool, show_rate: bool,
                              elapsed_time: float) -> str:
        """Generate plain text output without formatting."""
        # Generate bar using ASCII characters
        bar_width = dimensions.bar_width
        filled_chars = int(progress * bar_width)
        bar_content = '#' * filled_chars + '-' * (bar_width - filled_chars)
        
        # Build the complete progress bar
        parts = [f"[{bar_content}]"]
        
        # Add percentage
        if show_percentage:
            percentage = int(progress * 100)
            parts.append(f" {percentage:3d}%")
        
        # Add numbers
        if show_numbers:
            parts.append(f" ({current:.0f}/{total:.0f})")
        
        # Add rate
        if show_rate and elapsed_time > 0:
            rate = current / elapsed_time
            parts.append(f" {rate:.1f}/s")
        
        result = "".join(parts)
        
        # Add message on new line if provided
        if message.strip():
            result += f"\n{message}"
        
        return result
    
    def _generate_html_output(self, current: float, total: float, progress: float,
                             message: str, show_percentage: bool, 
                             show_numbers: bool, show_rate: bool,
                             elapsed_time: float) -> str:
        """Generate HTML progress bar output."""
        percentage = int(progress * 100)
        
        # Build HTML progress bar
        html_parts = [
            '<div class="fdl-progress-container">',
            f'  <div class="fdl-progress-bar" style="width: 100%; background-color: #f0f0f0; border-radius: 4px;">',
            f'    <div class="fdl-progress-fill" style="width: {percentage}%; background-color: #4CAF50; height: 20px; border-radius: 4px; transition: width 0.3s ease;"></div>',
            f'  </div>',
        ]
        
        # Add labels
        labels = []
        if show_percentage:
            labels.append(f"{percentage}%")
        if show_numbers:
            labels.append(f"({current:.0f}/{total:.0f})")
        if show_rate and elapsed_time > 0:
            rate = current / elapsed_time
            labels.append(f"{rate:.1f}/s")
        
        if labels:
            html_parts.append(f'  <div class="fdl-progress-labels" style="margin-top: 4px; font-size: 12px; color: #666;">{" ".join(labels)}</div>')
        
        # Add message
        if message.strip():
            escaped_message = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(f'  <div class="fdl-progress-message" style="margin-top: 4px; font-size: 14px;">{escaped_message}</div>')
        
        html_parts.append('</div>')
        
        return "\n".join(html_parts)
    
    def _render_bar(self, progress: float, bar_width: int) -> str:
        """Render the visual progress bar with smooth Unicode blocks."""
        # Calculate filled pixels with sub-character precision
        filled_pixels = progress * bar_width * 8  # 8 levels of precision
        
        # Build bar character by character
        bar_chars = []
        for i in range(bar_width):
            pixel_start = i * 8
            pixel_end = (i + 1) * 8
            
            if filled_pixels >= pixel_end:
                # Fully filled
                bar_chars.append(self.blocks[0])
            elif filled_pixels > pixel_start:
                # Partially filled - calculate which block
                partial_pixels = filled_pixels - pixel_start
                block_index = min(7, max(0, int(8 - partial_pixels)))
                bar_chars.append(self.blocks[block_index])
            else:
                # Empty
                bar_chars.append(' ')
        
        return ''.join(bar_chars)
    
    def _apply_format_state(self, content: str, format_state: _FormatState) -> str:
        """Apply format state to content, generating ANSI codes."""
        if not format_state:
            return content
        
        # Build ANSI codes from format state
        ansi_codes = []
        
        # Text color
        if format_state.text_color:
            color_code = self._get_color_code(format_state.text_color)
            if color_code:
                ansi_codes.append(color_code)
        
        # Background color
        if format_state.background_color:
            bg_color_code = self._get_background_color_code(format_state.background_color)
            if bg_color_code:
                ansi_codes.append(bg_color_code)
        
        # Text styles
        if format_state.bold:
            ansi_codes.append('1')
        if format_state.italic:
            ansi_codes.append('3')
        if format_state.underline:
            ansi_codes.append('4')
        if format_state.strikethrough:
            ansi_codes.append('9')
        
        # Apply formatting
        if ansi_codes:
            ansi_start = f"\x1b[{';'.join(ansi_codes)}m"
            ansi_end = "\x1b[0m"
            return f"{ansi_start}{content}{ansi_end}"
        
        return content
    
    def _get_color_code(self, color: str) -> Optional[str]:
        """Get ANSI color code for text color."""
        color_map = {
            'black': '30', 'red': '31', 'green': '32', 'yellow': '33',
            'blue': '34', 'magenta': '35', 'cyan': '36', 'white': '37',
            'bright_black': '90', 'bright_red': '91', 'bright_green': '92',
            'bright_yellow': '93', 'bright_blue': '94', 'bright_magenta': '95',
            'bright_cyan': '96', 'bright_white': '97'
        }
        return color_map.get(color)
    
    def _get_background_color_code(self, color: str) -> Optional[str]:
        """Get ANSI background color code."""
        bg_color_map = {
            'black': '40', 'red': '41', 'green': '42', 'yellow': '43',
            'blue': '44', 'magenta': '45', 'cyan': '46', 'white': '47',
            'bright_black': '100', 'bright_red': '101', 'bright_green': '102',
            'bright_yellow': '103', 'bright_blue': '104', 'bright_magenta': '105',
            'bright_cyan': '106', 'bright_white': '107'
        }
        return bg_color_map.get(color)
    
    def _process_format_string(self, format_string: str) -> Optional[_FormatState]:
        """Process format string into format state using command processors."""
        if not format_string.strip():
            return None
        
        # Create a new format state for processing
        format_state = _FormatState()
        
        # Remove leading/trailing whitespace and angle brackets
        clean_format = format_string.strip()
        if clean_format.startswith('</') and clean_format.endswith('>'):
            clean_format = clean_format[2:-1]  # Remove </ and >
        elif clean_format.startswith('<') and clean_format.endswith('>'):
            clean_format = clean_format[1:-1]   # Remove < and >
        
        # Split commands by comma and process each
        commands = [cmd.strip() for cmd in clean_format.split(',')]
        
        for command in commands:
            if command:  # Skip empty commands
                try:
                    format_state = _CommandRegistry.process_command(command, format_state)
                except (UnknownCommandError, Exception):
                    # If command processing fails, return None
                    return None
        
        return format_state