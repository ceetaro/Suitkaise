"""
Spinner Objects Processor for FDL.

This module handles spinner-related object patterns like <spinner:type>message
and includes the complete high-performance spinner system.

Unlike progress bars, spinners don't queue output - they animate alongside
normal FDL processing. Only one spinner can be active at a time.

This is internal to the FDL engine and not exposed to users.
"""

import threading
import time
import sys
from typing import Set, Optional, Dict, List, Union
from dataclasses import dataclass

from ...core.object_registry import _ObjectProcessor, _object_processor
from ...core.format_state import _FormatState
from ...setup.unicode import _get_unicode_support
from ...setup.terminal import _terminal


class SpinnerError(Exception):
    """Raised when spinner operations fail."""
    pass


@dataclass
class _SpinnerStyle:
    """
    Defines a spinner animation style.
    
    Attributes:
        name (str): Spinner name (dots, arrows, dqpb)
        frames (List[str]): Animation frames
        interval (float): Time between frames in seconds
        is_unicode (bool): Whether this spinner uses Unicode characters
    """
    name: str
    frames: List[str]
    interval: float
    is_unicode: bool


class _SpinnerManager:
    """
    Global spinner management with thread-safe operations.
    
    Ensures only one spinner is active at a time and provides
    efficient animation without Rich's threading bottlenecks.
    """
    
    # Define all spinner styles
    SPINNER_STYLES = {
        'dots': _SpinnerStyle(
            name='dots',
            frames=['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧'],
            interval=0.1,  #100ms - smooth but not too fast
            is_unicode=True
        ),
        'arrows': _SpinnerStyle(
            name='arrows',
            frames=['▸▹▹▹▹', '▸▸▹▹▹', '▸▸▸▹▹', '▹▸▸▸▹', '▹▹▸▸▸', '▹▹▹▸▸', '▹▹▹▹▸', '▹▹▹▹▹', '▹▹▹▹▹'],
            interval=0.15,   # 150ms - good speed for arrow movement
            is_unicode=True
        ),
        'dqpb': _SpinnerStyle(
            name='dqpb', 
            frames=['d', 'q', 'p', 'b'],
            interval=0.15,  # 150ms - moderate speed for ASCII
            is_unicode=False
        ),

        # Aliases for convenience
        'letters': _SpinnerStyle(
            name='letters',
            frames=['d', 'q', 'p', 'b'],
            interval=0.15,
            is_unicode=False
        )
    }
    
    def __init__(self):
        """Initialize spinner manager."""
        self._lock = threading.RLock()
        self._current_spinner: Optional['_ActiveSpinner'] = None
        
        # Always use real Unicode support detection
        self._unicode_support = _get_unicode_support()
        
        # Performance tracking
        self._created_count = 0
        self._stopped_count = 0
    
    def create_spinner(self, spinner_type: str, message: str = "") -> '_ActiveSpinner':
        """
        Create and start a new spinner, stopping any existing one.
        
        Args:
            spinner_type (str): Type of spinner (dots, arrows, dqpb, etc.)
            message (str): Message to display with spinner
            
        Returns:
            _ActiveSpinner: Active spinner instance
            
        Raises:
            SpinnerError: If spinner type is invalid
        """
        with self._lock:
            # Stop any existing spinner
            if self._current_spinner:
                self._current_spinner._stop_internal()
            
            # Get spinner style with fallback
            style = self._get_spinner_style(spinner_type)
            
            # Create new active spinner
            spinner = _ActiveSpinner(style, message, self)
            self._current_spinner = spinner
            self._created_count += 1
            
            # Start animation
            spinner._start_animation()
            
            return spinner
    
    def stop_current_spinner(self) -> bool:
        """
        Stop the currently active spinner.
        
        Returns:
            bool: True if a spinner was stopped, False if none was active
        """
        with self._lock:
            if self._current_spinner:
                self._current_spinner._stop_internal()
                self._current_spinner = None
                self._stopped_count += 1
                return True
            return False
    
    def _get_spinner_style(self, spinner_type: str) -> _SpinnerStyle:
        """
        Get spinner style with Unicode fallback logic.
        
        Args:
            spinner_type (str): Requested spinner type
            
        Returns:
            SpinnerStyle: Spinner style to use
            
        Raises:
            SpinnerError: If spinner type is completely invalid
        """
        spinner_type = spinner_type.lower().strip()
        
        # Check if requested type exists
        if spinner_type not in self.SPINNER_STYLES:
            raise SpinnerError(f"Unknown spinner type: {spinner_type}")
        
        style = self.SPINNER_STYLES[spinner_type]
        
        # If Unicode spinner requested but not supported, fall back to dqpb
        if style.is_unicode and not self._unicode_support.supports_unicode_spinners:
            return self.SPINNER_STYLES['dqpb']
        
        return style
    
    def get_performance_stats(self) -> Dict[str, int]:
        """Get performance statistics."""
        with self._lock:
            return {
                'spinners_created': self._created_count,
                'spinners_stopped': self._stopped_count,
                'currently_active': 1 if self._current_spinner else 0,
                'unicode_supported': self._unicode_support.supports_unicode_spinners
            }


class _ActiveSpinner:
    """
    Represents an active spinner with animation control.
    
    Handles the animation loop and display updates without
    creating expensive threads or blocking operations.
    """
    
    def __init__(self, style: _SpinnerStyle, message: str, manager: _SpinnerManager):
        """
        Initialize active spinner.
        
        Args:
            style (SpinnerStyle): Spinner animation style
            message (str): Message to display
            manager (_SpinnerManager): Parent manager
        """
        self.style = style
        self.message = message
        self._manager = manager
        
        # Animation state
        self._frame_index = 0
        self._last_update = 0.0
        self._is_running = False
        self._lock = threading.Lock()
        
        # Display state
        self._last_output_length = 0
        self._supports_color = _terminal.supports_color
        self._is_tty = _terminal.is_tty
    
    def _start_animation(self) -> None:
        """Start the spinner animation."""
        with self._lock:
            self._is_running = True
            self._last_update = time.time()
            self._frame_index = 0
            
            # Show initial frame
            self._update_display()
    
    def _update_display(self) -> None:
        """
        Update the spinner display.
        
        This is the core performance method - it updates the display
        efficiently without expensive operations.
        """
        if not self._is_running:
            return
        
        current_time = time.time()
        
        # Check if it's time to advance to next frame
        if current_time - self._last_update >= self.style.interval:
            self._frame_index = (self._frame_index + 1) % len(self.style.frames)
            self._last_update = current_time
        
        # Build output string
        current_frame = self.style.frames[self._frame_index]
        output = f"{current_frame} {self.message}" if self.message else current_frame
        
        # Clear previous output and show new content
        if self._last_output_length > 0:
            # Move cursor back and clear
            sys.stdout.write('\b' * self._last_output_length)
            sys.stdout.write(' ' * self._last_output_length)
            sys.stdout.write('\b' * self._last_output_length)
        
        # Write new content
        sys.stdout.write(output)
        sys.stdout.flush()
        
        self._last_output_length = len(output)
    
    def _stop_internal(self) -> None:
        """Internal method to stop the spinner."""
        with self._lock:
            if not self._is_running:
                return
            
            self._is_running = False
            
            # Clear the spinner display
            if self._last_output_length > 0:
                sys.stdout.write('\b' * self._last_output_length)
                sys.stdout.write(' ' * self._last_output_length) 
                sys.stdout.write('\b' * self._last_output_length)
                sys.stdout.flush()
                self._last_output_length = 0
    
    def update_message(self, new_message: str) -> None:
        """
        Update the spinner message.
        
        Args:
            new_message (str): New message to display
        """
        with self._lock:
            self.message = new_message
            if self._is_running:
                self._update_display()
    
    def tick(self) -> None:
        """
        Manually advance the spinner animation.
        
        Call this in your main loop for non-blocking animation.
        Much more efficient than Rich's threaded approach.
        """
        if self._is_running:
            self._update_display()
    
    def stop(self) -> None:
        """Stop this spinner."""
        self._manager.stop_current_spinner()
    
    @property
    def is_running(self) -> bool:
        """Check if spinner is currently running."""
        with self._lock:
            return self._is_running


# Global spinner manager instance
_global_spinner_manager: Optional[_SpinnerManager] = None


def _get_spinner_manager() -> _SpinnerManager:
    """Get the global spinner manager instance."""
    global _global_spinner_manager
    if _global_spinner_manager is None:
        _global_spinner_manager = _SpinnerManager()
    return _global_spinner_manager


# Internal API functions
def _create_spinner(spinner_type: str, message: str = "") -> _ActiveSpinner:
    """Create a new spinner, stopping any existing one."""
    return _get_spinner_manager().create_spinner(spinner_type, message)


def _stop_spinner() -> bool:
    """Stop the currently active spinner."""
    return _get_spinner_manager().stop_current_spinner()


def _get_available_spinners() -> List[str]:
    """Get list of available spinner types."""
    return list(_SpinnerManager.SPINNER_STYLES.keys())


def _get_spinner_performance_stats() -> Dict[str, int]:
    """Get spinner performance statistics."""
    return _get_spinner_manager().get_performance_stats()


def _process_spinner_object(spinner_type: str, message: str) -> str:
    """
    Process a spinner object for inline display.
    
    Args:
        spinner_type (str): Type of spinner
        message (str): Message to display
        
    Returns:
        str: Formatted spinner output
        
    This creates a spinner that auto-starts and can be manually ticked.
    Used by the object processor for <spinner:type> syntax.
    """
    try:
        spinner = _create_spinner(spinner_type, message)
        # Return the current frame for immediate display
        current_frame = spinner.style.frames[spinner._frame_index]
        return f"{current_frame} {message}" if message else current_frame
    except SpinnerError as e:
        return f"[SPINNER_ERROR: {e}]"


@_object_processor
class _SpinnerObjectProcessor(_ObjectProcessor):
    """
    Processor for spinner object patterns in FDL strings.
    
    Handles patterns like:
    - <spinner:dots> - Start dots spinner with no message
    - <spinner:arrows>Processing... - Start arrows spinner with message
    - <spinner:letters>Loading - Start letters/dqpb spinner with message
    
    Key behaviors:
    - Only one spinner can be active at a time
    - New spinners automatically stop previous ones
    - Spinners animate alongside normal output (no queuing)
    - Returns current frame for immediate display
    """
    
    @classmethod
    def get_supported_object_types(cls) -> Set[str]:
        """Get supported spinner object types."""
        return {'spinner'}
    
    @classmethod
    def process_object(cls, obj_type: str, variable: Optional[str], 
                      format_state: _FormatState) -> str:
        """
        Process spinner object and return current frame.
        
        Args:
            obj_type: Always 'spinner' for this processor
            variable: Spinner type (dots, arrows, letters, dqpb)
            format_state: Current format state
            
        Returns:
            str: Current spinner frame for immediate display
        """
        if obj_type != 'spinner':
            return f"[UNKNOWN_SPINNER_TYPE:{obj_type}]"
        
        # Get spinner type and message
        spinner_type, message = cls._parse_spinner_content(variable, format_state)
        
        if not spinner_type:
            return "[SPINNER_NO_TYPE]"
        
        # Validate spinner type
        available_spinners = _get_available_spinners()
        if spinner_type not in available_spinners:
            return f"[UNKNOWN_SPINNER:{spinner_type}]"
        
        try:
            # Process spinner - this handles global state management
            result = _process_spinner_object(spinner_type, message)
            return result
            
        except SpinnerError as e:
            return f"[SPINNER_ERROR:{e}]"
        except Exception as e:
            return f"[SPINNER_FAILED:{e}]"
    
    @classmethod
    def _parse_spinner_content(cls, variable: Optional[str], 
                              format_state: _FormatState) -> tuple[str, str]:
        """
        Parse spinner variable and get spinner type and message.
        
        Args:
            variable: Variable content (spinner type)
            format_state: Current format state for getting values
            
        Returns:
            tuple: (spinner_type, message)
        """
        # If no variable specified, can't determine spinner type
        if not variable:
            return "", ""
        
        spinner_type = variable.strip().lower()
        
        # Try to get message from values tuple
        message = ""
        try:
            if format_state.has_more_values():
                message_value = format_state.get_next_value()
                message = str(message_value) if message_value is not None else ""
        except (IndexError, ValueError):
            # No message value available, use empty message
            pass
        
        return spinner_type, message
    
    @classmethod
    def get_spinner_info(cls) -> dict:
        """
        Get information about available spinners.
        
        Returns:
            dict: Spinner system information
        """
        try:
            available = _get_available_spinners()
            return {
                'available_spinners': available,
                'total_count': len(available),
                'unicode_spinners': [s for s in available if s in ['dots', 'arrows']],
                'ascii_spinners': [s for s in available if s in ['dqpb', 'letters']],
                'processor': 'SpinnerObjectProcessor'
            }
        except Exception as e:
            return {
                'error': str(e),
                'available_spinners': [],
                'total_count': 0
            }


# Convenience functions for integration
def _stop_current_spinner() -> bool:
    """Stop the currently active spinner."""
    return _stop_spinner()


def _get_spinner_types() -> list:
    """Get list of available spinner types."""
    return _get_available_spinners()


def _is_valid_spinner_type(spinner_type: str) -> bool:
    """Check if spinner type is valid."""
    return spinner_type.lower() in _get_available_spinners()




# Convenience functions for integration
def _stop_current_spinner() -> bool:
    """
    Stop the currently active spinner.
    
    Returns:
        bool: True if a spinner was stopped
    """
    return _stop_spinner()


def _get_spinner_types() -> list:
    """Get list of available spinner types."""
    return _get_available_spinners()


def _is_valid_spinner_type(spinner_type: str) -> bool:
    """Check if spinner type is valid."""
    return spinner_type.lower() in _get_available_spinners()