"""
Smooth Progress Bar Implementation - Ultra-simple and smooth

FIXES:
- Simpler batching logic to prevent race conditions
- Faster update interval for smoother animation (50ms instead of 100ms)
- More precise Unicode block rendering
- Atomic updates to prevent backwards movement
- Immediate display updates for responsiveness
"""

import threading
import time
import sys
from typing import Dict, Optional, Union
from collections import deque
from dataclasses import dataclass, field

# Always use real Unicode support
from ...setup.unicode import _get_unicode_support
from ...setup.terminal import _terminal
from ...core import _get_command_processor


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
        self._command_proc = _get_command_processor()
        
        # Choose character set
        self.blocks = self.UNICODE_BLOCKS if self._supports_unicode else self.ASCII_BLOCKS
        
        # Cache color codes
        self._color_ansi = ""
        self._reset_ansi = ""
        if self.color and self._supports_color:
            try:
                self._color_ansi = self._command_proc.converter._get_color_ansi(self.color)
                self._reset_ansi = self._command_proc.generate_reset_ansi()
            except:
                pass
    
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
            self._render_display()
    
    def update(self, increment: float) -> None:
        """
        Add progress increment with atomic batching.
        
        SMOOTH: Updates logical progress immediately, visual progress animates to catch up.
        """
        if increment <= 0:
            return
        
        with self._lock:
            if self._is_stopped:
                return
            
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
        """
        Animate one frame - smoothly move displayed_progress towards current.
        
        FAST ANIMATION: Keep visual progress within 2-5% of logical progress.
        """
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
        display = self.style.render_bar(display_ratio, self.current, self.total)
        
        try:
            # Simple same-line update
            if self._display_count > 0:
                sys.stdout.write(f'\r{display}')
            else:
                sys.stdout.write(display)
            sys.stdout.flush()
            
            self._last_display_time = time.time()
            self._display_count += 1
            
        except Exception:
            # Skip if stdout fails
            pass
    
    def tick(self) -> None:
        """Manual animation tick - advance animation frame."""
        with self._lock:
            self._animate_frame()
    
    def set_progress(self, current: float) -> None:
        """Set absolute progress (only forward)."""
        with self._lock:
            if self._is_stopped:
                return
            
            new_current = max(self.current, min(self.total, float(current)))
            if new_current != self.current:
                self.current = new_current
                # Don't immediately snap displayed_progress, let animation catch up
                self._render_display()
    
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
            
            # Move to next line
            if self._is_displayed:
                sys.stdout.write('\n')
                sys.stdout.flush()
    
    def force_newline(self) -> None:
        """Force newline before other output."""
        with self._lock:
            if self._is_displayed and not self._is_stopped:
                sys.stdout.write('\n')
                sys.stdout.flush()
                self._display_count = 0  # Reset for fresh start
    
    @property
    def progress_ratio(self) -> float:
        """Get logical progress ratio (0.0 to 1.0)."""
        with self._lock:
            return self.current / self.total if self.total > 0 else 0.0
    
    @property
    def displayed_ratio(self) -> float:
        """Get displayed progress ratio (0.0 to 1.0) - what's visually shown."""
        with self._lock:
            return self.displayed_progress / self.total if self.total > 0 else 0.0
    
    @property
    def is_complete(self) -> bool:
        """Check if logically complete."""
        with self._lock:
            return self.current >= self.total
    
    @property
    def is_stopped(self) -> bool:
        """Check if stopped."""
        return self._is_stopped
    
    def get_performance_stats(self) -> Dict[str, Union[int, float]]:
        """Get performance statistics."""
        with self._lock:
            lag = abs(self.current - self.displayed_progress)
            lag_percentage = (lag / self.total) * 100 if self.total > 0 else 0
            
            return {
                'total_updates': self._update_count,
                'display_updates': self._display_count,
                'update_efficiency': self._update_count / max(1, self._display_count),
                'logical_progress': self.progress_ratio,
                'displayed_progress': self.displayed_ratio,
                'animation_lag': lag,
                'lag_percentage': lag_percentage,
                'is_complete': self.is_complete,
                'unicode_supported': self.style._supports_unicode,
                'pending_increment': self._pending_increment
            }


def _create_progress_bar(total: float, color: str = "green", 
                        width: Optional[int] = None) -> _ProgressBar:
    """Create a smooth progress bar."""
    return _ProgressBar(total, color, width)