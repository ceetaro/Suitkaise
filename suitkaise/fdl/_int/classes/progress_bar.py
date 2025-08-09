"""
Progress Bar Implementation.

A simple progress bar that works with FDL but is not part of FDL strings.
"""

import sys
import os
import time
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass





class _ProgressBarManager:
    """
    Global progress bar management with thread-safe operations.
    
    Ensures only one progress bar is active at a time and provides
    efficient progress tracking and output blocking.
    """
    
    def __init__(self):
        """Initialize progress bar manager."""
        self._lock = threading.RLock()
        self._active_progress_bar: Optional['_ProgressBar'] = None
    
    def get_active_progress_bar(self) -> Optional['_ProgressBar']:
        """Get the currently active progress bar."""
        with self._lock:
            return self._active_progress_bar
    
    def set_active_progress_bar(self, progress_bar: Optional['_ProgressBar']) -> None:
        """Set the currently active progress bar."""
        with self._lock:
            self._active_progress_bar = progress_bar
    
    def has_active_bar(self) -> bool:
        """Check if any progress bar is currently active."""
        return self._active_progress_bar is not None
    
    def deactivate_current(self) -> None:
        """Deactivate the currently active progress bar."""
        with self._lock:
            self._active_progress_bar = None


# Global progress bar manager instance
_progress_bar_manager = _ProgressBarManager()


class _ProgressBar:
    """
    Simple progress bar implementation.
    
    Features:
    - Unicode block characters for smooth progress visualization
    - ASCII fallback for compatibility
    - Automatic line width calculation based on title
    - Multi-format output (terminal, plain, HTML)
    - Proper width constraints and overflow handling
    """
    
    # Unicode blocks for smooth progress (8 levels of precision)
    UNICODE_BLOCKS = ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']
    ASCII_BLOCKS = ['.', ':', 'i', 'l', 'I', 'H', '$', '#']
    
    def __init__(self, total: int, title: Optional[str] = None, 
                 bar_color: Optional[str] = None, text_color: Optional[str] = None, 
                 bkg_color: Optional[str] = None, ratio: bool = True, 
                 percent: bool = False, rate: bool = False, 
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize progress bar.
        
        Args:
            total: Total increments to completion (must be int of 2 or higher)
            title: Leading text before bar (bar will be on separate line if too long)
            bar_color: Color of progress bar
            text_color: Color of statistic text and "--" before update messages
            bkg_color: Background color of bar and message lines
            ratio: Whether to display N/total completed
            percent: Whether to display percent completion
            rate: Whether to display rate per second
            config: Dict setup of params (overrides individual params)
        """
        # Validate total
        if not isinstance(total, int) or total < 2:
            raise ValueError("total must be an int of 2 or higher")
        
        # Apply config if provided
        if config:
            title = config.get('title', title)
            bar_color = config.get('bar_color', bar_color)
            text_color = config.get('text_color', config.get('message_color', text_color))
            bkg_color = config.get('bkg_color', bkg_color)
            ratio = config.get('ratio', ratio)
            percent = config.get('percent', percent)
            rate = config.get('rate', rate)
        
        # Store parameters
        self.total = total
        self.title = title
        self.bar_color = bar_color
        self.text_color = text_color
        self.bkg_color = bkg_color
        self.ratio = ratio
        self.percent = percent
        self.rate = rate
        
        # Unicode support detection
        try:
            from ..setup.unicode import _supports_progress_blocks
            self._supports_unicode = _supports_progress_blocks()
        except (ImportError, AttributeError):
            self._supports_unicode = False  # Fallback to ASCII
        
        self.blocks = self.UNICODE_BLOCKS if self._supports_unicode else self.ASCII_BLOCKS
        
        # Progress tracking
        self.current = 0
        self.elapsed_time = 0.0
        self.start_time = None
        self.is_stopped = False
        self.is_displayed = False
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Batching for large totals (will be calculated after bar width)
        self._batch_threshold = 500  # New threshold
        self._pending_updates = []  # List of increments waiting to be applied
        self._pending_message = None  # Message to display when batch is applied
        
        # Calculate and store constant dimensions once
        self._terminal_width = self._get_terminal_width()
        
        # Wrap title first, then calculate its width (ignoring ANSI codes)
        wrapped_title_lines = self._wrap_text(self.title) if self.title else [""]
        self._wrapped_title = (wrapped_title_lines[0] + " ") if wrapped_title_lines and wrapped_title_lines[0] else " "
        self._title_width = self._get_visual_width(self._wrapped_title)
        
        self._max_stats_width = self._calculate_max_stats_width()
        
        # Calculate bar width using the clear formula: terminal_width - title_width - max_stats_width
        # Subtract 1 to ensure we don't exceed terminal width and cause wrapping
        self._bar_width = self._terminal_width - self._title_width - self._max_stats_width - 1
        
        # Ensure bar width is not negative and has a reasonable minimum
        if self._bar_width < 0:
            self._bar_width = 0
        
        # Now calculate batch size after bar width is available
        self._batch_size = self._calculate_batch_size()
        
        # Check if bar width would be less than 40% of terminal width
        min_bar_width = int(self._terminal_width * 0.4)
        
        if self._bar_width < min_bar_width:
            # Calculate max allowed title width to help user
            max_title_width = self._terminal_width - self._max_stats_width - min_bar_width
            raise ValueError(
                f"Title too long for terminal width. "
                f"Current title width: {self._title_width}, "
                f"Max allowed: {max_title_width}. "
                f"Please use a shorter title."
            )
        
        # Ensure bar width is not negative
        if self._bar_width < 0:
            raise ValueError(
                f"Title and stats too wide for terminal. "
                f"Terminal width: {self._terminal_width}, "
                f"Title width: {self._title_width}, "
                f"Stats width: {self._max_stats_width}, "
                f"Required space: {self._title_width + self._max_stats_width}. "
                f"Please use a shorter title."
            )
        
        # Visual progress tracking
        self.visual_total = self._bar_width * 8  # 8 states per position
        self.visual_position = 0
        
        # Output tracking
        self._last_output_lines = 0
        self._last_output_length = 0
    
    def _calculate_batch_size(self) -> int:
        """
        Calculate batch size to ensure each batch shows visual progress.
        
        Each batch should represent at least 1 visual unit (1/8th of a bar position).
        Formula: batch_size = ceiling(total / (bar_width * 8))
        """
        if self.total < 500:  # New threshold
            return 1  # No batching for small totals
        
        # Calculate batch size to ensure visual progress
        visual_units = self._bar_width * 8  # Each bar position has 8 visual states
        batch_size = (self.total + visual_units - 1) // visual_units  # Ceiling division
        
        return max(1, batch_size)
    
    def _get_terminal_width(self) -> int:
        """Get terminal width using the setup terminal module."""
        try:
            from ..setup.terminal import _get_terminal
            terminal = _get_terminal()
            return terminal.width
        except (ImportError, AttributeError):
            # Fallback to shutil if setup module not available
            try:
                import shutil
                return shutil.get_terminal_size().columns
            except (AttributeError, OSError):
                return 80
    
    def _get_visual_width(self, text: Optional[str]) -> int:
        """Calculate visual width of text using the setup text_wrapping module."""
        if not text:
            return 0
        
        try:
            from ..setup.text_wrapping import _get_visual_width
            return _get_visual_width(text)
        except (ImportError, AttributeError):
            # Fallback to simple implementation
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            clean_text = ansi_escape.sub('', text)
            return len(clean_text)
    
    def _wrap_text(self, text: str) -> list[str]:
        """Wrap text and return list of lines using the setup text_wrapping module."""
        if not text:
            return [""]
        
        try:
            from suitkaise.fdl._int.setup.text_wrapping import _wrap_text
            wrapped_lines = _wrap_text(text, preserve_newlines=True)
            return wrapped_lines if wrapped_lines else [""]
        except (ImportError, AttributeError):
            # Fallback to simple implementation
            lines = text.split('\n')
            return lines if lines else [""]
    
    def _truncate_message_with_dots(self, message: str) -> str:
        """
        Truncate message by replacing trailing non-whitespace characters with dots.
        
        Replaces the last 4 visual width characters with dots:
        - 1-wide characters are replaced with 1 dot
        - 2-wide Unicode characters are replaced with 2 dots
        """
        if not message:
            return message
        
        # Calculate visual width of the message
        message_width = self._get_visual_width(message)
        max_width = self._terminal_width - 4  # Leave space for " -- " prefix
        
        if message_width <= max_width:
            return message
        
        # Need to truncate - find where to cut
        dots_needed = 4
        dots_placed = 0
        truncated_chars = 0
        
        # Work backwards from the end, replacing non-whitespace characters
        for i in range(len(message) - 1, -1, -1):
            char = message[i]
            
            # Skip whitespace characters
            if char.isspace():
                continue
            
            char_width = self._get_visual_width(char)
            
            # Replace this character with dots
            if char_width == 1:
                dots_placed += 1
            elif char_width == 2:
                dots_placed += 2
            
            truncated_chars += 1
            
            # Check if we've placed enough dots
            if dots_placed >= dots_needed:
                break
        
        # Return the truncated message
        return message[:-truncated_chars] + ("." * dots_needed)
    

    
    def _calculate_max_stats_width(self) -> int:
        """Calculate maximum possible stats width."""
        # Choose divider based on Unicode support
        divider = '│' if self._supports_unicode else '|'
        
        # Build the max stats text with fixed-width formatting
        stats_parts = []
        
        # Add percent if requested (fixed width: 6 characters)
        if self.percent:
            stats_parts.append("100.0%")
        
        # Add ratio if requested (fixed width: 7 characters)
        if self.ratio:
            # Use max possible current value (the total itself)
            max_current = self.total
            stats_parts.append(f'{max_current:3d}/{self.total}')
        
        # Add rate if requested (fixed width: 7 characters)
        if self.rate:
            # Rate is capped at total in _build_stats_text, so use the same cap here
            max_rate = self.total
            stats_parts.append(f'{max_rate:6.1f}/s')
        
        # If no stats, return 0
        if not stats_parts:
            return 0
        
        # Add dividers between stats
        result_parts = []
        result_parts.append(" ")  # Initial space
        for i, part in enumerate(stats_parts):
            result_parts.append(part)
            if i < len(stats_parts) - 1:
                # Add divider after this part (except the last part)
                result_parts.append(f" {divider} ")
        
        # Add 2 spaces of padding at the end
        result_parts.append("  ")
        
        return self._get_visual_width("".join(result_parts))
    
    @classmethod
    def is_any_active(cls) -> bool:
        """Check if any progress bar is currently active."""
        return _progress_bar_manager.is_any_active()
    
    def _activate_progress_bar(self) -> None:
        """Activate this progress bar (deactivates any existing one)."""
        # Deactivate any existing progress bar
        current_active = _progress_bar_manager.get_active_progress_bar()
        if current_active is not None and current_active is not self:
            current_active._deactivate_progress_bar()
        
        # Activate this one
        _progress_bar_manager.set_active_progress_bar(self)
    
    def _deactivate_progress_bar(self) -> None:
        """Deactivate this progress bar."""
        current_active = _progress_bar_manager.get_active_progress_bar()
        if current_active is self:
            _progress_bar_manager.deactivate_current()
    
    def _render_bar(self, progress: float, bar_width: int) -> str:
        """Render the visual progress bar."""
        if bar_width <= 0:
            return ""
        
        # Calculate filled positions (each position can be 0-8 states)
        filled_positions = self.visual_position // 8
        
        # Calculate partial state for the next position (0-7)
        partial_state = self.visual_position % 8
        
        # Build the bar
        bar_parts = []
        
        # Add filled positions with full blocks
        bar_parts.append(self.blocks[-1] * filled_positions)  # Use full block (█)
        
        # Add partial character if needed
        if partial_state > 0 and filled_positions < bar_width:
            bar_parts.append(self.blocks[partial_state - 1])  # Use partial block
        
        # Add empty characters
        empty_chars = bar_width - filled_positions - (1 if partial_state > 0 and filled_positions < bar_width else 0)
        if empty_chars > 0:
            bar_parts.append(' ' * empty_chars)
        
        return "".join(bar_parts)
    
    def _build_stats_text(self, progress: float) -> str:
        """Build the stats text with consistent divider positioning."""
        # Choose divider based on Unicode support
        divider = '│' if self._supports_unicode else '|'
        
        # Build the stats text with fixed-width formatting
        stats_parts = []
        
        # Add percent if requested (fixed width: 6 characters)
        if self.percent:
            percentage = progress * 100
            stats_parts.append(f"{percentage:6.1f}%")
        
        # Add ratio if requested (fixed width: 7 characters)
        if self.ratio:
            stats_parts.append(f"{int(self.current):3d}/{self.total}")
        
        # Add rate if requested (fixed width: 7 characters)
        if self.rate:
            if self.elapsed_time > 0:
                rate = min(self.current / self.elapsed_time, self.total)  # Cap rate at total
                stats_parts.append(f"{rate:6.1f}/s")
            else:
                stats_parts.append("  0.0/s")
        
        # If no stats, return empty string
        if not stats_parts:
            return ""
        
        # Add dividers between stats
        result_parts = []
        result_parts.append(" ")  # Initial space
        for i, part in enumerate(stats_parts):
            result_parts.append(part)
            if i < len(stats_parts) - 1:
                # Add divider after this part (except the last part)
                result_parts.append(f" {divider} ")
        
        # Add one space of padding at the end
        result_parts.append("  ")
        
        return "".join(result_parts)
    
    def _apply_colors(self, text: str, color: Optional[str] = None, bkg_color: Optional[str] = None) -> str:
        """Apply colors to text (simplified implementation)."""
        if not color and not bkg_color:
            return text
        
        # Simple color mapping - in practice you'd use a proper color system
        color_codes = {
            'black': '30', 'red': '31', 'green': '32', 'yellow': '33',
            'blue': '34', 'magenta': '35', 'cyan': '36', 'white': '37',
            'gray': '90'
        }
        
        codes = []
        if color and color in color_codes:
            codes.append(color_codes[color])
        if bkg_color and bkg_color in color_codes:
            codes.append(str(int(color_codes[bkg_color]) + 10))
        
        if codes:
            return f"\033[{';'.join(codes)}m{text}\033[0m"
        return text
    
    def _generate_terminal_output(self, progress: float, message: Optional[str] = None) -> tuple[str, str, str]:
        """Generate terminal output as two lines."""
        # First line: title + bar + stats
        first_line_parts = []
        
        # Add title if provided (use pre-wrapped title)
        if self._wrapped_title:
            title_text_colored = self._apply_colors(self._wrapped_title, self.text_color)
            first_line_parts.append(title_text_colored)
        
        # Generate the visual bar
        bar_content = self._render_bar(progress, self._bar_width)
        bar_text = self._apply_colors(bar_content, self.bar_color)
        first_line_parts.append(bar_text)
        
        # Add stats text
        stats_text = self._build_stats_text(progress)
        stats_text_colored = self._apply_colors(stats_text, self.text_color)
        first_line_parts.append(stats_text_colored)
        
        first_line = "".join(first_line_parts)
        
        # Second line: blank line for spacing
        second_line = " " * self._terminal_width
        
        # Third line: message or whitespace
        if message:
            # Check for newlines in raw message
            if '\n' in message:
                self._deactivate_progress_bar()
                raise ValueError("Progress bar messages cannot contain newlines. Please use a single line message.")
            
            # Format message: truncate if needed, add ' -- ' prefix, wrap, take first line, center it
            truncated_message = self._truncate_message_with_dots(message)
            formatted_message = f" -- {truncated_message}"
            wrapped_lines = self._wrap_text(formatted_message)
            first_wrapped_line = wrapped_lines[0] if wrapped_lines else " -- "
            
            # Position message to start at the same position as the progress bar
            # Calculate the position where the bar starts (after title or minimum offset)
            bar_start_position = self._title_width
            
            # Pad the message to align with the bar start
            padded_message = (' ' * bar_start_position) + first_wrapped_line
            
            # Pad to terminal width
            current_width = self._get_visual_width(padded_message)
            padding_needed = self._terminal_width - current_width
            if padding_needed > 0:
                padded_message += ' ' * padding_needed
            
            third_line = self._apply_colors(padded_message, self.text_color)
        else:
            # Empty line filled with spaces to ensure consistent width
            third_line = " " * self._terminal_width
        
        # Ensure the first line doesn't exceed terminal width and pad it
        first_line_width = self._get_visual_width(first_line)
        
        if first_line_width > self._terminal_width:
            # Debug information for overflows
            title_part = first_line_parts[0] if first_line_parts else ""
            bar_part = first_line_parts[1] if len(first_line_parts) > 1 else ""
            stats_part = first_line_parts[2] if len(first_line_parts) > 2 else ""
            
            title_width = self._get_visual_width(title_part)
            bar_width = self._get_visual_width(bar_part)
            stats_width = self._get_visual_width(stats_part)
            
            raise RuntimeError(
                f"Progress bar first line exceeds terminal width. "
                f"Expected: {self._terminal_width}, Actual: {first_line_width}. "
                f"Title width: {title_width}, Bar width: {bar_width}, Stats width: {stats_width}. "
                f"Title: '{title_part}', Bar: '{bar_part}', Stats: '{stats_part}'. "
                f"This indicates a calculation error."
            )
        
        # Pad the first line to full terminal width to ensure complete clearing
        padding_needed = self._terminal_width - first_line_width
        if padding_needed > 0:
            first_line += ' ' * padding_needed
        
        return first_line, second_line, third_line
    
    def _generate_plain_output(self, progress: float, message: Optional[str] = None) -> str:
        """Generate plain text output."""
        parts = ["[ProgressBar"]
        
        # Add percentage
        if self.percent:
            percentage = int(progress * 100)
            parts.append(f" - {percentage}%")
        
        # Add numbers
        if self.ratio:
            parts.append(f", ({self.current}/{self.total})")
        
        # Add rate
        if self.rate and self.elapsed_time > 0:
            rate = self.current / self.elapsed_time
            parts.append(f", {rate:.1f}/s")
        
        parts.append("]")
        
        # Add message
        if message:
            parts.append(f" - {message}")
        
        return "".join(parts)
    
    def _generate_html_output(self, progress: float, message: Optional[str] = None) -> str:
        """Generate HTML output."""
        html_parts = ['<div class="progress-bar">']
        
        # Add title if provided
        if self.title:
            html_parts.append(f'<span class="title">{self.title}</span>')
        
        # Add progress bar
        percentage = int(progress * 100)
        html_parts.append(f'<div class="bar" style="width: {percentage}%"></div>')
        
        # Add stats
        stats_parts = []
        if self.percent:
            stats_parts.append(f"{percentage}%")
        if self.ratio:
            stats_parts.append(f"({self.current}/{self.total})")
        if self.rate and self.elapsed_time > 0:
            rate = self.current / self.elapsed_time
            stats_parts.append(f"{rate:.1f}/s")
        
        if stats_parts:
            html_parts.append(f'<span class="stats">{" ".join(stats_parts)}</span>')
        
        # Add message
        if message:
            html_parts.append(f'<span class="message">{message}</span>')
        
        html_parts.append('</div>')
        return "".join(html_parts)
    
    def _create_snapshot(self, progress: float, message: Optional[str] = None) -> tuple[str, str, str]:
        """
        Create a snapshot of the current progress bar state.
        
        Args:
            progress: Current progress ratio (0.0 to 1.0)
            message: Optional message to display
            
        Returns:
            tuple[str, str]: (first_line, second_line) for terminal output
        """
        # Calculate visual position based on progress
        self.visual_position = round(progress * self.visual_total)
        
        # Generate terminal output
        return self._generate_terminal_output(progress, message)
    
    def display(self) -> None:
        """
        Display the progress bar for the first time.
        This method should be called to initially show the bar.
        """
        with self._lock:
            if self.is_displayed:
                raise RuntimeError("Progress bar is already displayed. Use update() to modify it.")
            
            # Activate this progress bar (deactivates any existing one)
            self._activate_progress_bar()
            
            # Create initial snapshot and display
            progress = self.current / self.total if self.total > 0 else 0.0
            first_line, second_line, third_line = self._create_snapshot(progress, None)
            output = first_line + "\n" + second_line + "\n" + third_line
            print(output, end='', flush=True)
            self.is_displayed = True
            self._last_output_lines = 3  # Track number of lines printed
    
    def update(self, *args) -> Dict[str, str]:
        """
        Update progress bar with flexible parameter ordering.
        
        Usage examples:
            bar.update()                    # increment by 1 with no message
            bar.update(1)                   # increment by 1 with no message  
            bar.update("textures loaded.")  # increment by 1 with a message
            bar.update(f"Loading {component_name}", 12)  # increment by 12 with a message
            bar.update(12)                  # increment by 12 with no message
            
        Args:
            *args: Flexible arguments - can be (increments, message) or (message, increments) or just increments or just message
            
        Returns:
            Dict[str, str]: Progress bar in all output formats
        """
        with self._lock:
            if self.is_stopped:
                raise RuntimeError("Progress bar is stopped and cannot be updated")
            
            if not self.is_displayed:
                raise RuntimeError("Progress bar must be displayed first. Call display() before update().")
            
            # Parse arguments
            increments = 1  # Default increment
            message = None
            
            for arg in args:
                if isinstance(arg, int):
                    increments = arg
                elif isinstance(arg, str):
                    message = arg
                else:
                    raise ValueError(f"Invalid argument type: {type(arg)}. Expected int or str.")
            
            if not isinstance(increments, int):
                raise ValueError("increments must be an int")
            
                    # Add to pending updates for batching
            self._pending_updates.append(increments)
            
            # Store message if provided (overrides any previous message in this batch)
            if message is not None:
                self._pending_message = message
            
                    # Check if we should update the display (batching logic)
            # Count total increments in pending updates
            total_pending_increments = sum(self._pending_updates)
            would_complete = (self.current + total_pending_increments) >= self.total
            should_update = (
                total_pending_increments >= self._batch_size or  # Batch threshold reached (increments)
                message is not None or                           # Message provided (always update)
                would_complete                                   # Would complete the bar (always update)
            )
            
            if should_update:
                # Apply all pending updates to current progress
                total_increment = sum(self._pending_updates)
                self.current = min(self.current + total_increment, self.total)
                
                # Get the stored message (if any) and clear pending data
                stored_message = self._pending_message
                self._pending_updates = []
                
                # Update stored message if a new one is provided
                if message is not None:
                    self._pending_message = message
                    stored_message = message  # Use the new message
                # (If message is None, keep the last stored message)
                
                # Update elapsed time if tracking rate
                if self.rate and self.start_time is None:
                    self.start_time = time.time()
                elif self.rate and self.start_time:
                    self.elapsed_time = time.time() - self.start_time
                
                # Calculate progress percentage for display
                progress = self.current / self.total if self.total > 0 else 0.0
                
                # Create snapshot of current state (use stored message if no immediate message)
                display_message = stored_message
                first_line, second_line, third_line = self._create_snapshot(progress, display_message)
                terminal_output = first_line + "\n" + second_line + "\n" + third_line
                plain_output = self._generate_plain_output(progress, message)
                html_output = self._generate_html_output(progress, message)
                
                # Optimized cursor movement: move up 3 lines, clear them, and position cursor
                print('\033[3A\033[K\033[1A\033[K\033[1A\033[K\033[3B\r', end='', flush=True)
                
                # Print the new output
                print(terminal_output, end='', flush=True)
                
                # Check if bar is complete and auto-deactivate
                if self.current >= self.total:
                    self._deactivate_progress_bar()  # Allow other output again
                
                return {
                    'terminal': terminal_output,
                    'plain': plain_output,
                    'html': html_output
                }
            else:
                # Return empty output when not updating (batching)
                return {
                    'terminal': '',
                    'plain': '',
                    'html': ''
                }
    
    def stop(self):
        """Stop the progress bar (stays in output but does not complete)."""
        with self._lock:
            self.is_stopped = True
            self._deactivate_progress_bar()  # Allow other output again
    
    def is_complete(self) -> bool:
        """Check if progress bar is complete."""
        with self._lock:
            return self.current >= self.total
    
    def get_progress(self) -> float:
        """Get current progress as a percentage."""
        with self._lock:
            return (self.current / self.total) * 100 if self.total > 0 else 0.0


# Module-level functions for global progress bar management
def _get_progress_bar_manager() -> _ProgressBarManager:
    """Get the global progress bar manager."""
    return _progress_bar_manager


def _get_active_progress_bar() -> Optional['_ProgressBar']:
    """Get the currently active progress bar."""
    return _progress_bar_manager.get_active_progress_bar()


def _is_progress_bar_active() -> bool:
    """Check if any progress bar is currently active."""
    return _progress_bar_manager.is_any_active()


def _deactivate_current_progress_bar() -> None:
    """Deactivate the currently active progress bar."""
    _progress_bar_manager.deactivate_current()