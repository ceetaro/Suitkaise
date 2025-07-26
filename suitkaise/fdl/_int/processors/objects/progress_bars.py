"""
Progress Bar Objects Processor for FDL.

This module handles progress bar-related object patterns like <progressbar:variable>
and integrates with the terminal progress bar system.

This is internal to the FDL engine and not exposed to users.
"""

import threading
import time
import sys
import warnings
from typing import Dict, Optional, Union, Set
from collections import deque
from dataclasses import dataclass, field

from core.object_registry import _ObjectProcessor, _object_processor
from core.format_state import _FormatState
from setup.unicode import _get_unicode_support
from setup.terminal import _terminal
from setup.color_conversion import _to_ansi_fg


class ProgressBarError(Exception):
    """Raised when progress bar operations fail."""
    pass


class _ProgressBarStyle:
    """Visual styling for progress bars with enhanced smoothness."""
    
    # High-precision Unicode blocks (8 levels)
    UNICODE_BLOCKS = ['█', '▉', '▊', '▋', '▌', '▍', '▎', '▏']
    ASCII_BLOCKS = ['#', '#', '#', '#', '#', '#', '#', '.']
    
    def __init__(self, color: Optional[str] = None, width: Optional[int] = None):
        self.color = color
        self.fixed_width = width
        
        # Unicode and color support
        self._unicode_support = _get_unicode_support()
        self._supports_unicode = self._unicode_support.supports_progress_blocks
        self._supports_color = _terminal.supports_color
        
        # Choose character set
        self.blocks = self.UNICODE_BLOCKS if self._supports_unicode else self.ASCII_BLOCKS
        
        # Cache color codes
        self._color_ansi = ""
        self._reset_ansi = "\033[0m"
        if self.color and self._supports_color:
            color_code = _to_ansi_fg(self.color)
            if color_code:
                self._color_ansi = color_code
    
    @property
    def bar_width(self) -> int:
        """Get available bar width."""
        if self.fixed_width:
            return max(10, self.fixed_width - 25)
        
        terminal_width = _terminal.width
        return max(10, terminal_width - 35)  # More space for smooth rendering
    
    def render_bar(self, progress: float, current: float, total: float) -> str:
        """Render progress bar with enhanced smoothness."""
        # Ensure valid progress range
        progress = max(0.0, min(1.0, progress))
        
        bar_width = self.bar_width
        filled_pixels = progress * bar_width * 8  # 8 sub-pixel precision
        
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
        
        bar_content = ''.join(bar_chars)
        
        # Apply color if available
        if self._color_ansi:
            bar_content = f"{self._color_ansi}{bar_content}{self._reset_ansi}"
        
        # Build complete display
        percentage = int(progress * 100)
        return f"{bar_content} {percentage:3d}% ({current:.0f}/{total:.0f})"


class _ProgressBar:
    """Ultra-smooth progress bar with interpolated animation."""
    
    def __init__(self, total: float, color: Optional[str] = None, 
                 width: Optional[int] = None, update_interval: float = 0.016):
        """
        Initialize smooth progress bar.
        
        Args:
            total (float): Total value when complete
            color (Optional[str]): Bar color
            width (Optional[int]): Fixed width
            update_interval (float): Animation frame rate (16ms = 60fps)
        """
        if total <= 0:
            raise ProgressBarError("Total must be positive")
        
        self.total = float(total)
        self.current = 0.0  # Logical progress (actual value)
        self.displayed_progress = 0.0  # Visual progress (what's shown, animates to current)
        self.update_interval = update_interval  # 16ms for 60fps smooth animation
        
        # Style
        self.style = _ProgressBarStyle(color, width)
        
        # Simplified state
        self._pending_increment = 0.0  # Atomic accumulator
        self._lock = threading.Lock()  # Simple lock
        self._last_display_time = 0.0
        self._is_displayed = False
        self._is_stopped = False
        
        # Message display
        self._current_message = ""
        self._message_lines = 0  # Track how many lines the message uses
        
        # Performance tracking
        self._update_count = 0
        self._display_count = 0
    
    def display_bar(self, color: Optional[str] = None) -> None:
        """Display the progress bar initially."""
        with self._lock:
            if self._is_stopped:
                return
            
            if color and color != self.style.color:
                self.style = _ProgressBarStyle(color, self.style.fixed_width)
            
            self._is_displayed = True
            
            # Register with global progress bar manager
            _ProgressBarManager.set_active_bar(self)
            
            self._render_display()
    
    def update(self, increment: float, message: str = "") -> None:
        """
        Add progress increment with atomic batching and optional message.
        
        Args:
            increment: Progress increment to add
            message: Optional message to display under the bar
        """
        if increment <= 0:
            return
        
        with self._lock:
            if self._is_stopped:
                return
            
            # Update message if provided
            if message != self._current_message:
                self._current_message = message
            
            # Atomically add to pending increment
            self._pending_increment += increment
            self._update_count += 1
            
            # Check if we should update display/animation
            current_time = time.time()
            if current_time - self._last_display_time >= self.update_interval:
                self._animate_frame()
    
    def _flush_updates(self) -> None:
        """Flush pending updates to logical progress (called with lock held)."""
        if self._pending_increment <= 0:
            return
        
        # Apply all pending increments atomically to logical progress
        self.current = min(self.total, self.current + self._pending_increment)
        self._pending_increment = 0.0
    
    def _animate_frame(self) -> None:
        """Animate one frame - smoothly move displayed_progress towards current."""
        # First, flush any logical updates
        self._flush_updates()
        
        # Calculate animation step
        target_progress = self.current
        current_displayed = self.displayed_progress
        
        # SNAP TO COMPLETION: If logical progress is complete, immediately show 100%
        if target_progress >= self.total:
            self.displayed_progress = self.total
            self._render_display()
            return
        
        # Calculate how far behind we are
        lag = target_progress - current_displayed
        lag_percentage = (lag / self.total) * 100 if self.total > 0 else 0
        
        if abs(lag) < 0.01:
            # Very close, just snap to target
            self.displayed_progress = target_progress
        else:
            # RESPONSIVE ANIMATION: Much faster animation to keep within 2-5% lag
            if lag_percentage > 5.0:
                # If we're more than 5% behind, catch up very aggressively
                animation_step = lag * 0.8  # Take 80% of the gap each frame
            elif lag_percentage > 2.0:
                # If we're 2-5% behind, catch up moderately fast
                animation_step = lag * 0.4  # Take 40% of the gap each frame
            else:
                # If we're less than 2% behind, smooth normal animation
                animation_step = lag * 0.2  # Take 20% of the gap each frame
            
            # Ensure minimum step size for very small differences
            min_step = max(0.5, self.total * 0.005)  # At least 0.5% of total per frame
            if animation_step > 0:
                animation_step = max(min_step, animation_step)
            else:
                animation_step = min(-min_step, animation_step)
            
            # Apply the animation step
            if lag > 0:
                self.displayed_progress = min(target_progress, current_displayed + animation_step)
            else:
                self.displayed_progress = max(target_progress, current_displayed + animation_step)
        
        # Render the display with animated progress
        self._render_display()
    
    def _render_display(self) -> None:
        """Render the progress bar display using displayed_progress (called with lock held)."""
        if not self._is_displayed or self._is_stopped:
            return
        
        # Use displayed_progress for smooth animation, but show logical current in text
        display_ratio = self.displayed_progress / self.total if self.total > 0 else 0.0
        bar_display = self.style.render_bar(display_ratio, self.current, self.total)
        
        try:
            # Clear previous message lines if any
            if self._message_lines > 0:
                for _ in range(self._message_lines + 1):  # +1 for bar line
                    sys.stdout.write('\033[1A\033[2K')  # Move up and clear line
                self._message_lines = 0
            elif self._display_count > 0:
                sys.stdout.write('\r\033[2K')  # Clear current line
            
            # Write bar
            sys.stdout.write(bar_display)
            
            # Write message if present
            if self._current_message:
                sys.stdout.write('\n')
                sys.stdout.write(self._current_message)
                self._message_lines = 1  # Simple single-line messages for now
            
            sys.stdout.flush()
            
            self._last_display_time = time.time()
            self._display_count += 1
            
        except Exception:
            # Skip if stdout fails
            pass
    
    def stop(self) -> None:
        """Stop and complete the progress bar."""
        with self._lock:
            if self._is_stopped:
                return
            
            # Flush any remaining updates
            self._flush_updates()
            
            # Mark complete and snap to final state immediately
            self.current = self.total
            self.displayed_progress = self.total  # SNAP to completion
            self._is_stopped = True
            self._render_display()
            
            # Move to next line and clear message
            if self._is_displayed:
                sys.stdout.write('\n')
                sys.stdout.flush()
            
            # Unregister from global manager and flush any queued FDL output
            _ProgressBarManager.clear_active_bar()
    
    @property
    def is_complete(self) -> bool:
        """Check if logically complete."""
        with self._lock:
            return self.current >= self.total
    
    @property
    def is_stopped(self) -> bool:
        """Check if stopped."""
        return self._is_stopped


class _ProgressBarManager:
    """Global manager for progress bar state integration with FDL system."""
    
    _active_bar: Optional[_ProgressBar] = None
    _lock = threading.Lock()
    
    @classmethod
    def set_active_bar(cls, bar: _ProgressBar) -> None:
        """Set the active progress bar."""
        with cls._lock:
            cls._active_bar = bar
    
    @classmethod
    def clear_active_bar(cls) -> None:
        """Clear the active progress bar."""
        with cls._lock:
            cls._active_bar = None
    
    @classmethod
    def get_active_bar(cls) -> Optional[_ProgressBar]:
        """Get the currently active progress bar."""
        with cls._lock:
            return cls._active_bar
    
    @classmethod
    def is_bar_active(cls) -> bool:
        """Check if a progress bar is currently active."""
        with cls._lock:
            return cls._active_bar is not None and not cls._active_bar.is_stopped


@_object_processor
class _ProgressBarObjectProcessor(_ObjectProcessor):
    """
    Processor for progress bar object patterns in FDL strings.
    
    Handles patterns like:
    - <progressbar:variable> - Display progress bar value/percentage
    - <progressbar_percent:variable> - Display just percentage
    - <progressbar_status:variable> - Display current/total values
    """
    
    @classmethod
    def get_supported_object_types(cls) -> Set[str]:
        """Get supported progress bar object types."""
        return {
            'progressbar',
            'progressbar_percent', 
            'progressbar_status',
            'progressbar_ratio'
        }
    
    @classmethod
    def process_object(cls, obj_type: str, variable: Optional[str], 
                      format_state: _FormatState) -> str:
        """
        Process progress bar object and return formatted result.
        
        Args:
            obj_type: Type of progress bar object
            variable: Variable name for progress bar reference
            format_state: Current format state
            
        Returns:
            str: Formatted progress bar information
        """
        # Get progress bar from variable or active bar
        progress_bar = cls._get_progress_bar(variable, format_state)
        
        if not progress_bar:
            return f"[NO_PROGRESS_BAR_{variable or 'ACTIVE'}]"
        
        # Route to appropriate formatting method
        if obj_type == 'progressbar':
            return cls._format_full_info(progress_bar)
        elif obj_type == 'progressbar_percent':
            return cls._format_percentage(progress_bar)
        elif obj_type == 'progressbar_status':
            return cls._format_status(progress_bar)
        elif obj_type == 'progressbar_ratio':
            return cls._format_ratio(progress_bar)
        
        return f"[UNKNOWN_PROGRESSBAR_TYPE:{obj_type}]"
    
    @classmethod
    def _get_progress_bar(cls, variable: Optional[str], 
                         format_state: _FormatState) -> Optional[_ProgressBar]:
        """Get progress bar from variable or active bar."""
        if variable:
            try:
                # Get progress bar from values tuple
                progress_bar = format_state.get_next_value()
                if isinstance(progress_bar, _ProgressBar):
                    return progress_bar
            except (IndexError, ValueError):
                pass
        
        # Fall back to active progress bar
        return _ProgressBarManager.get_active_bar()
    
    @classmethod
    def _format_full_info(cls, progress_bar: _ProgressBar) -> str:
        """Format full progress bar information."""
        with progress_bar._lock:
            percentage = int((progress_bar.current / progress_bar.total) * 100)
            return f"{percentage}% ({progress_bar.current:.0f}/{progress_bar.total:.0f})"
    
    @classmethod
    def _format_percentage(cls, progress_bar: _ProgressBar) -> str:
        """Format just the percentage."""
        with progress_bar._lock:
            percentage = int((progress_bar.current / progress_bar.total) * 100)
            return f"{percentage}%"
    
    @classmethod
    def _format_status(cls, progress_bar: _ProgressBar) -> str:
        """Format current/total status."""
        with progress_bar._lock:
            return f"{progress_bar.current:.0f}/{progress_bar.total:.0f}"
    
    @classmethod
    def _format_ratio(cls, progress_bar: _ProgressBar) -> str:
        """Format progress ratio (0.0 to 1.0)."""
        with progress_bar._lock:
            ratio = progress_bar.current / progress_bar.total if progress_bar.total > 0 else 0.0
            return f"{ratio:.3f}"


def _create_progress_bar(total: float, color: str = "green", 
                        width: Optional[int] = None) -> _ProgressBar:
    """Create a smooth progress bar."""
    return _ProgressBar(total, color, width)


def _get_active_progress_bar() -> Optional[_ProgressBar]:
    """Get the currently active progress bar."""
    return _ProgressBarManager.get_active_bar()


def _is_progress_bar_active() -> bool:
    """Check if a progress bar is currently active."""
    return _ProgressBarManager.is_bar_active()