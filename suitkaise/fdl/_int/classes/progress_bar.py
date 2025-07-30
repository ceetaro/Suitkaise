# classes/progress_bar.py
"""
Standalone Progress Bar Class for FDL.

Provides a comprehensive API for creating, managing, and displaying progress bars
with formatting, threading support, and multi-format output.
"""

import threading
import time
from typing import Dict, Optional, Union, Any
from copy import deepcopy
from ..setup.progress_bar_generator import _ProgressBarGenerator
from ..setup.unicode import _get_unicode_support
from ..setup.terminal import _get_terminal
from ..core.format_state import _FormatState
from ..core.command_registry import _CommandRegistry, UnknownCommandError
# Import processors to ensure registration
from ..processors import commands


class ProgressBarError(Exception):
    """Raised when progress bar operations fail."""
    pass


class _ProgressBar:
    """
    Standalone progress bar class with comprehensive API.
    
    Features:
    - Thread-safe operations
    - Format state integration with FDL command processing
    - Multi-format output (terminal, plain, HTML)
    - Smooth Unicode rendering with ASCII fallback
    - Rate calculation and timing
    - Message display
    - Memory management
    
    Recommended Usage:
        Use update() for normal progress tracking (atomic incrementation):
        >>> progress = _ProgressBar(total=100, color="green")
        >>> progress.display()
        >>> progress.update(25, "Step 1 complete")  # Preferred method
        >>> progress.update(30, "Step 2 complete")  # Thread-safe increments
        >>> progress.finish("All done!")
        
        Only use set_current() for special cases like checkpoint restoration.
    """
    
    def __init__(self, total: float, color: Optional[str] = None, 
                 width: Optional[int] = None, show_percentage: bool = True,
                 show_numbers: bool = True, show_rate: bool = False):
        """
        Initialize a new progress bar.
        
        Args:
            total: Total/maximum value for the progress bar
            color: Color for the progress bar (FDL color name)
            width: Fixed width for the bar (None for auto-sizing)
            show_percentage: Whether to show percentage
            show_numbers: Whether to show current/total numbers
            show_rate: Whether to show rate information
            
        Raises:
            ProgressBarError: If total is not positive
        """
        if total <= 0:
            raise ProgressBarError("Total must be positive")
        
        self.total = float(total)
        self.width = width
        self.show_percentage = show_percentage
        self.show_numbers = show_numbers
        self.show_rate = show_rate
        
        # Progress tracking
        self._current = 0.0
        self._message = ""
        self._start_time = time.time()
        self._last_update_time = self._start_time
        
        # Thread safety
        self._lock = threading.Lock()
        
        # State management
        self._displayed = False
        self._finished = False
        self._released = False
        
        # Setup components (must be before formatting)
        self._progress_bar_generator = _ProgressBarGenerator()
        self._unicode_support = _get_unicode_support()
        
        # Early terminal check with helpful error (terminal-only feature)
        try:
            self._terminal = _get_terminal()
            # Test that we can actually get terminal width
            _ = self._terminal.width
        except Exception as e:
            raise ProgressBarError(
                "Progress bars require a terminal environment. "
                "This error typically occurs when running in automated environments, "
                "CI/CD pipelines, or redirected output. "
                f"Terminal detection failed: {e}"
            ) from e
        
        self._command_registry = _CommandRegistry()
        
        # Formatting (after command registry is initialized)
        self._format_state: Optional[_FormatState] = None
        if color:
            self._set_color(color)
    
    # ==================== PROPERTIES ====================
    
    @property
    def current(self) -> float:
        """Get current progress value."""
        with self._lock:
            return self._current
    
    @property
    def progress(self) -> float:
        """Get progress as a ratio (0.0 to 1.0)."""
        with self._lock:
            return min(1.0, self._current / self.total)
    
    @property
    def percentage(self) -> int:
        """Get progress as a percentage (0 to 100)."""
        return int(self.progress * 100)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since creation."""
        return time.time() - self._start_time
    
    @property
    def is_complete(self) -> bool:
        """Check if progress bar is complete."""
        with self._lock:
            return self._current >= self.total
    
    @property
    def is_displayed(self) -> bool:
        """Check if progress bar is currently displayed."""
        with self._lock:
            return self._displayed
    
    @property
    def is_finished(self) -> bool:
        """Check if progress bar has been finished."""
        with self._lock:
            return self._finished
    
    # ==================== CORE METHODS ====================
    
    def display(self) -> None:
        """
        Display the progress bar initially.
        
        Raises:
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            if self._finished:
                return
            
            self._displayed = True
            self._render_and_display()
    
    def update(self, increment: float, message: str = "") -> None:
        """
        Update progress by the given increment (RECOMMENDED for normal progress tracking).
        
        This is the preferred method for natural progress updates as it uses atomic
        incrementation, making it thread-safe and preventing race conditions.
        
        Args:
            increment: Amount to add to current progress
            message: Optional message to display
            
        Raises:
            RuntimeError: If progress bar has been released
            
        Example:
            >>> progress = _ProgressBar(total=100)
            >>> progress.display()
            >>> progress.update(25, "Loading configuration...")  # 0 → 25
            >>> progress.update(30, "Processing data...")        # 25 → 55
            >>> progress.update(45, "Finalizing...")             # 55 → 100
        """
        self._check_released()
        
        if increment <= 0:
            return
        
        with self._lock:
            if self._finished:
                return
            
            # Update progress
            old_current = self._current
            self._current = min(self.total, self._current + increment)
            self._last_update_time = time.time()
            
            # Update message if provided
            if message.strip():
                self._message = message.strip()
            
            # Auto-display if not already displayed
            if not self._displayed:
                self._displayed = True
            
            # Render if there was actual progress
            if self._current > old_current:
                self._render_and_display()
            
            # Auto-finish if complete
            if self._current >= self.total and not self._finished:
                self._finish_internal()
    
    def set_current(self, value: float, message: str = "") -> None:
        """
        Set current progress to a specific value (NOT RECOMMENDED for natural progression).
        
        This method directly sets the progress value and should only be used for special
        cases like checkpoint restoration, syncing with external systems, or testing.
        For normal progress tracking, use update() instead as it provides atomic
        incrementation and better thread safety.
        
        Args:
            value: New current value (will be clamped to 0-total range)
            message: Optional message to display
            
        Raises:
            RuntimeError: If progress bar has been released
            
        Warning:
            Avoid using this for natural progress updates. Use update() instead.
            
        Example (Valid use cases):
            >>> # Resuming from checkpoint
            >>> progress.set_current(saved_progress, "Resumed from checkpoint")
            >>> 
            >>> # Syncing with external progress system
            >>> external_pct = get_external_progress() * 100
            >>> progress.set_current(external_pct, "Synced with external system")
        """
        self._check_released()
        
        with self._lock:
            if self._finished:
                return
            
            old_current = self._current
            self._current = max(0.0, min(self.total, float(value)))
            self._last_update_time = time.time()
            
            # Update message if provided
            if message.strip():
                self._message = message.strip()
            
            # Auto-display if not already displayed
            if not self._displayed:
                self._displayed = True
            
            # Render if there was a change
            if self._current != old_current:
                self._render_and_display()
            
            # Auto-finish if complete
            if self._current >= self.total and not self._finished:
                self._finish_internal()
    
    def set_message(self, message: str) -> None:
        """
        Set the message without updating progress.
        
        Args:
            message: Message to display
            
        Raises:
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            if self._finished:
                return
            
            self._message = message.strip()
            
            if self._displayed:
                self._render_and_display()
    
    def finish(self, message: str = "Complete!") -> None:
        """
        Finish the progress bar and optionally set final message.
        
        Args:
            message: Final message to display
            
        Raises:
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            if self._finished:
                return
            
            # Set to complete
            self._current = self.total
            if message.strip():
                self._message = message.strip()
            
            self._finish_internal()
    
    def _finish_internal(self) -> None:
        """Internal finish method (assumes lock is held)."""
        self._finished = True
        
        if self._displayed:
            # Final render
            self._render_and_display()
            # Add newline to move cursor past the progress bar
            print()
    
    # ==================== FORMATTING METHODS ====================
    
    def set_color(self, color: str) -> None:
        """
        Set the color of the progress bar.
        
        Args:
            color: FDL color name (e.g., 'green', 'red', 'blue')
            
        Raises:
            ValueError: If color format is invalid
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            self._set_color(color)
            
            if self._displayed and not self._finished:
                self._render_and_display()
    
    def set_format(self, format_string: str) -> None:
        """
        Set formatting for the progress bar using FDL format string.
        
        Args:
            format_string: FDL format string like "</green, bold>"
            
        Raises:
            ValueError: If format string is invalid
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            self._format_state = self._process_format_string(format_string)
            
            if self._displayed and not self._finished:
                self._render_and_display()
    
    def reset_format(self) -> None:
        """
        Reset all formatting to default.
        
        Raises:
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            self._format_state = None
            
            if self._displayed and not self._finished:
                self._render_and_display()
    
    def _set_color(self, color: str) -> None:
        """Internal method to set color (assumes lock is held)."""
        try:
            self._format_state = self._process_format_string(f"</{color}>")
        except Exception as e:
            raise ValueError(f"Invalid color '{color}': {e}")
    
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
                    format_state = self._command_registry.process_command(command, format_state)
                except UnknownCommandError as e:
                    raise ValueError(f"Invalid format command '{command}': {e}")
                except Exception as e:
                    raise ValueError(f"Error processing format command '{command}': {e}")
        
        return format_state
    
    # ==================== OUTPUT METHODS ====================
    
    def get_output(self, format_type: str = 'terminal') -> str:
        """
        Get progress bar output in specified format without displaying.
        
        Args:
            format_type: Output format ('terminal', 'plain', 'html')
            
        Returns:
            Formatted progress bar string
            
        Raises:
            ValueError: If format_type is invalid
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        if format_type not in ('terminal', 'plain', 'html'):
            raise ValueError(f"Invalid format_type: {format_type}")
        
        with self._lock:
            output = self._progress_bar_generator.generate_progress_bar(
                current=self._current,
                total=self.total,
                width=self.width,
                format_state=self._format_state,
                message=self._message,
                show_percentage=self.show_percentage,
                show_numbers=self.show_numbers,
                show_rate=self.show_rate,
                elapsed_time=self.elapsed_time
            )
            
            return output[format_type]
    
    def get_all_outputs(self) -> Dict[str, str]:
        """
        Get progress bar output in all formats.
        
        Returns:
            Dict with keys: 'terminal', 'plain', 'html'
            
        Raises:
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            return self._progress_bar_generator.generate_progress_bar(
                current=self._current,
                total=self.total,
                width=self.width,
                format_state=self._format_state,
                message=self._message,
                show_percentage=self.show_percentage,
                show_numbers=self.show_numbers,
                show_rate=self.show_rate,
                elapsed_time=self.elapsed_time
            )
    
    def _render_and_display(self) -> None:
        """Internal method to render and display (assumes lock is held)."""
        if not self._displayed or self._released:
            return
        
        # Get terminal output
        terminal_output = self.get_output('terminal')
        
        # Clear current line and display
        print(f"\r{terminal_output}", end="", flush=True)
    
    # ==================== UTILITY METHODS ====================
    
    def copy(self) -> '_ProgressBar':
        """
        Create a copy of this progress bar.
        
        Returns:
            New progress bar with same configuration
            
        Raises:
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            new_bar = _ProgressBar(
                total=self.total,
                width=self.width,
                show_percentage=self.show_percentage,
                show_numbers=self.show_numbers,
                show_rate=self.show_rate
            )
            
            # Copy current state
            new_bar._current = self._current
            new_bar._message = self._message
            new_bar._format_state = deepcopy(self._format_state) if self._format_state else None
            
            return new_bar
    
    def reset(self) -> None:
        """
        Reset progress bar to initial state.
        
        Raises:
            RuntimeError: If progress bar has been released
        """
        self._check_released()
        
        with self._lock:
            self._current = 0.0
            self._message = ""
            self._start_time = time.time()
            self._last_update_time = self._start_time
            self._finished = False
            
            if self._displayed:
                self._render_and_display()
    
    # ==================== MEMORY MANAGEMENT ====================
    
    def release(self) -> None:
        """Release the progress bar from memory."""
        if self._released:
            return
        
        with self._lock:
            # Finish if not already finished
            if not self._finished and self._displayed:
                print()  # Move cursor past progress bar
            
            # Clear references
            self._format_state = None
            self._message = ""
            
            # Mark as released
            self._released = True
    
    def _check_released(self) -> None:
        """Check if progress bar has been released and raise error if so."""
        if self._released:
            raise RuntimeError("Progress bar has been released and cannot be used")
    
    # ==================== CONTEXT MANAGER ====================
    
    def __enter__(self) -> '_ProgressBar':
        """Enter context manager."""
        self.display()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if not self._finished:
            self.finish()
        self.release()
    
    # ==================== STRING REPRESENTATION ====================
    
    def __str__(self) -> str:
        """Get string representation."""
        with self._lock:
            return f"ProgressBar({self._current}/{self.total}, {self.percentage}%)"
    
    def __repr__(self) -> str:
        """Get detailed representation."""
        with self._lock:
            return (f"_ProgressBar(current={self._current}, total={self.total}, "
                   f"percentage={self.percentage}%, displayed={self._displayed}, "
                   f"finished={self._finished}, released={self._released})")


# ==================== CONVENIENCE FUNCTIONS ====================

def create_progress_bar(total: float, **kwargs) -> _ProgressBar:
    """
    Create a new progress bar with optional configuration.
    
    Args:
        total: Total/maximum value
        **kwargs: Additional arguments for _ProgressBar
        
    Returns:
        New progress bar instance
    """
    return _ProgressBar(total, **kwargs)