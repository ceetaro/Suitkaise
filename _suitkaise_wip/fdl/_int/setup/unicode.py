"""
INTERNAL Unicode feature support detection and fallback system.

This file works internally to detect whether the terminal supports various Unicode features.

This module tests whether entire feature sets (box styles, spinners, progress bars)
are supported and provides complete fallback alternatives when they're not.

Supported features:
- Box styles: square, rounded, double, heavy, heavy_head, horizontals (fallback: ascii)
- Spinners: dots, arrow3 (fallback: dqpb)  
- Progress bars: unicode blocks (fallback: ascii)
- Syntax themes: material, native, paraiso-dark, solarized-dark, 
                nord, nord-darker, gruvbox-dark
"""

import sys
import warnings
from typing import Dict, List, Optional


class _UnicodeSupport:
    """
    Detects Unicode feature support and provides complete fallback systems.
    
    Tests entire feature sets rather than individual characters:
    - If any box drawing character fails → use ASCII boxes for all styles
    - If any spinner character fails → fall back to dqpb spinner
    - If progress bar characters fail → use ASCII progress bars
    
    This ensures consistent appearance and reliable functionality.
    """
    
    def __init__(self, terminal_info=None):
        """
        Initialize Unicode support detection.
        
        Args:
            terminal_info: Terminal info object (uses global _terminal if None)
            
        Immediately tests all required characters and builds the supported
        character dictionary.
        """
        if terminal_info is not None:
            self._terminal = terminal_info
        else:
            try:
                from .terminal import _terminal
                self._terminal = _terminal
            except (ImportError, AttributeError):
                # Fallback terminal if import fails
                class _FallbackTerminal:
                    is_tty = False
                    encoding = 'ascii'
                self._terminal = _FallbackTerminal()
        
        # Safely get terminal properties with fallbacks
        self._is_tty = getattr(self._terminal, 'is_tty', False)
        
        # Handle encoding more safely
        encoding = getattr(self._terminal, 'encoding', 'ascii')
        if encoding is None or not isinstance(encoding, str):
            encoding = 'ascii'
        self._encoding = encoding
        
        # Feature support flags
        self._supports_box_drawing = False
        self._supports_unicode_spinners = False
        self._supports_progress_blocks = False
        self._supports_status_chars = False
        
        # Test all feature sets immediately
        self._test_all_features()

    def _test_feature_set(self, characters: List[List[str]]) -> bool:
        """
        Test if all characters in a feature set are supported.
        
        Args:
            characters (List[List[str]]): List of character sets to test
            
        Returns:
            bool: True if ALL characters are supported, False if ANY fail
        """
        # If not a TTY, don't use Unicode features
        if not self._is_tty:
            return False
        
        # If encoding is not available or is ASCII, skip Unicode
        if not self._encoding or self._encoding == 'ascii':
            return False
        
        # Test each character set, then each character in the set
        for char_set in characters:
            for char in char_set:
                try:
                    # Try to encode each character using the terminal's encoding
                    char.encode(self._encoding)
                except (UnicodeEncodeError, LookupError, AttributeError, TypeError):
                    return False  # If any character fails, the feature is unsupported
                
        return True
    
    def _test_all_features(self) -> None:
        """
        Test all Unicode feature sets and set support flags.
        
        Tests each feature set as a unit. If any character in a set fails,
        the entire feature is marked as unsupported.
        """
        # Define character sets for each box style (removed trailing commas)
        square_box = ['┌','┐','└','┘','│','─','┼','┴','┬','┤','├']
        rounded_box = ['╭','╮','╰','╯','│','─','┼','┴','┬','┤','├']
        double_box = ['╔','╗','╚','╝','║','═','╬','╩','╦','╣','╠']
        heavy_box = ['┏', '┓', '┗', '┛', '┃', '━', '╋', '┻', '┳', '┫', '┣']
        heavy_head_box = ['┍', '┑', '┕', '┙', '│', '━', '┿', '┷', '┯', '┥', '┝']
        horizontals_box = ['─']

        # Define spinner character sets (removed trailing commas)
        dots = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧']
        arrow3 = ['▹', '▸', '▹']
        dqpb = ['d', 'q', 'p', 'b']

        # Define progress bar character set
        progress_bar = ['█', '▉', '▊', '▋', '▌', '▍', '▎', '▏']

        # status characters
        status_chars = ['✓', '✗', '⚠', 'ℹ', '✔', '✖']

        # Group character sets for testing
        box_chars = [
            square_box, rounded_box, double_box, heavy_box, heavy_head_box, horizontals_box
        ]
        spinner_chars = [dots, arrow3, dqpb]
        progress_bar_chars = [progress_bar]
        status_chars_list = [status_chars]

        
        # Test each feature set
        self._supports_box_drawing = self._test_feature_set(box_chars)
        self._supports_unicode_spinners = self._test_feature_set(spinner_chars)
        self._supports_progress_blocks = self._test_feature_set(progress_bar_chars)
        self._supports_status_chars = self._test_feature_set(status_chars_list)

        # Warning messages for unsupported features
        if not self._supports_box_drawing:
            warnings.warn("Unicode box drawing not supported, using ASCII boxes", UserWarning)
        if not self._supports_unicode_spinners:
            warnings.warn("Unicode spinners not supported, using dqpb spinner", UserWarning)
        if not self._supports_progress_blocks:
            warnings.warn("Unicode progress bars not supported, using ASCII progress", UserWarning)

    @property
    def supports_box_drawing(self) -> bool:
        """
        Check if Unicode box drawing is supported.
        
        Returns:
            bool: True if Rich can use fancy box styles (rounded, double, etc.)
                  False if Rich should stick to ASCII boxes
        """
        return self._supports_box_drawing
    
    @property
    def supports_unicode_spinners(self) -> bool:
        """
        Check if Unicode spinners are supported.
        
        Returns:
            bool: True if Rich can use fancy spinners (dots, arrows, etc.)
                  False if Rich should use basic ASCII spinners (dqpb, |/-\\)
        """
        return self._supports_unicode_spinners
    
    @property
    def supports_progress_blocks(self) -> bool:
        """
        Check if Unicode progress blocks are supported.
        
        Returns:
            bool: True if Rich can use smooth block progress bars
                  False if Rich should use ASCII progress bars (#, -, etc.)
        """
        return self._supports_progress_blocks
    
    @property
    def supports_status_chars(self) -> bool:
        """
        Check if Unicode status characters are supported.
        
        Returns:
            bool: True if Rich can use Unicode status symbols '✓', '✗', '⚠', 'ℹ', '✔', '✖'
                  False if Rich should use ASCII alternatives
        """
        return self._supports_status_chars

    @property
    def encoding(self) -> str:
        """Get the detected terminal encoding."""
        return self._encoding
    
    @property
    def is_tty(self) -> bool:
        """Check if output is going to a terminal."""
        return self._is_tty
    
    def get_capabilities_summary(self) -> Dict[str, bool]:
        """
        Get a summary of all Unicode capabilities.
        
        Returns:
            Dict[str, bool]: Feature names mapped to support status
            
        Useful for debugging, logging, or choosing Rich rendering options.
        """
        return {
            'box_drawing': self._supports_box_drawing,
            'unicode_spinners': self._supports_unicode_spinners,
            'progress_blocks': self._supports_progress_blocks,
            'status_chars': self._supports_status_chars,
            'is_tty': self._is_tty,
            'encoding': self._encoding,
        }


# Global Unicode support instance
# This will be initialized when the module is imported
_unicode_support: Optional[_UnicodeSupport] = None


def _get_unicode_support() -> _UnicodeSupport:
    """
    Get the global Unicode support instance.
    
    Returns:
        _UnicodeSupport: Global Unicode support object
        
    Creates the instance on first call, returns cached instance afterward.
    """
    global _unicode_support
    if _unicode_support is None:
        _unicode_support = _UnicodeSupport()
    return _unicode_support


def _supports_box_drawing() -> bool:
    """Quick check if Unicode box drawing is supported."""
    return _get_unicode_support().supports_box_drawing


def _supports_unicode_spinners() -> bool:
    """Quick check if Unicode spinners are supported."""
    return _get_unicode_support().supports_unicode_spinners


def _supports_progress_blocks() -> bool:
    """Quick check if Unicode progress blocks are supported."""
    return _get_unicode_support().supports_progress_blocks


def _get_capabilities() -> Dict[str, bool]:
    """Get summary of all Unicode capabilities."""
    return _get_unicode_support().get_capabilities_summary()