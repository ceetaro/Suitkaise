# setup/text_justification.py
"""
Internal text justification utilities for FDL.

This module provides text justification functions that handle ANSI codes,
terminal width constraints, and different justification modes.

This module ONLY handles justification - text wrapping should be done separately.

This is internal to the FDL engine and not exposed to users.
"""

import re
from typing import List, Optional


class _TextJustifier:
    """
    Internal text justification system for FDL.
    
    Handles left, right, and center justification while preserving ANSI codes
    and respecting terminal width constraints.
    
    This class ONLY handles justification - assumes text is already wrapped.
    """
    
    def __init__(self, terminal_width: Optional[int] = None):
        """
        Initialize text justifier.
        
        Args:
            terminal_width: Override terminal width (uses detected width if None)
        """
        # Import here to avoid circular imports
        try:
            from .terminal import _get_terminal
            terminal = _get_terminal()
            self.terminal_width = terminal_width or terminal.width
        except (ImportError, AttributeError):
            self.terminal_width = terminal_width or 60
            
        # ANSI escape sequence pattern for stripping codes
        self._ansi_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def justify_text(self, text: str, justify: str) -> str:
        """
        Apply justification to text.
        
        This method assumes text is already wrapped if needed.
        It justifies each line independently.
        
        Args:
            text: Text to justify (may contain ANSI codes, may be multi-line)
            justify: Justification mode ('left', 'right', 'center')
            
        Returns:
            str: Justified text
        """
        if not text or justify == 'left':
            return text  # Left is default, no processing needed
        
        # Split text into lines and justify each line independently
        lines = text.split('\n')
        justified_lines = []
        
        for line in lines:
            if justify == 'right':
                justified_line = self._justify_right(line)
            elif justify == 'center':
                justified_line = self._justify_center(line)
            else:  # fallback to left
                justified_line = line
            
            justified_lines.append(justified_line)
        
        return '\n'.join(justified_lines)
    
    def _justify_right(self, line: str) -> str:
        """
        Right-justify a single line.
        
        Args:
            line: Line to justify
            
        Returns:
            str: Right-justified line
        """
        if not line.strip():
            return line  # Empty line, no justification needed
        
        # Get visible length using visual width calculation
        visible_length = self._get_visual_width(line)
        
        if visible_length >= self.terminal_width:
            return line  # Line too long, no padding possible
        
        # Calculate padding needed to fill terminal width
        padding = self.terminal_width - visible_length
        
        return ' ' * padding + line
    
    def _justify_center(self, line: str) -> str:
        """
        Center-justify a single line.
        
        Args:
            line: Line to justify
            
        Returns:
            str: Center-justified line
        """
        if not line.strip():
            return line  # Empty line, no justification needed
        
        # Get visible length using visual width calculation
        visible_length = self._get_visual_width(line)
        
        if visible_length >= self.terminal_width:
            return line  # Line too long, no padding possible
        
        # Calculate padding needed - this should fill the entire terminal width
        total_padding = self.terminal_width - visible_length
        left_padding = total_padding // 2
        right_padding = total_padding - left_padding  # Handle odd padding
        
        # Build the centered line with exact padding
        return ' ' * left_padding + line + ' ' * right_padding
    
    def _get_visual_width(self, text: str) -> int:
        """
        Get visual width of text using wcwidth when available.
        
        Args:
            text: Text to measure
            
        Returns:
            int: Visual character count
        """
        if not text:
            return 0
        
        # Strip ANSI codes first
        clean_text = self._strip_ansi_codes(text)
        
        # Try to use wcwidth for accurate measurement
        try:
            import wcwidth
            if wcwidth is not None:
                width = wcwidth.wcswidth(clean_text)
                if width is not None:
                    return width
                
                # Fallback: character by character
                total_width = 0
                for char in clean_text:
                    char_width = wcwidth.wcwidth(char)
                    if char_width is not None:
                        total_width += char_width
                return total_width
        except ImportError:
            pass
        
        # Fallback to len() if wcwidth not available
        return len(clean_text)
    
    def _strip_ansi_codes(self, text: str) -> str:
        """
        Strip ANSI escape codes from text for length measurement.
        
        Args:
            text: Text with potential ANSI codes
            
        Returns:
            str: Text without ANSI codes
        """
        return self._ansi_pattern.sub('', text)
    
    def get_visible_length(self, text: str) -> int:
        """
        Get visible length of text (excluding ANSI codes).
        
        Args:
            text: Text to measure
            
        Returns:
            int: Visible character count
        """
        return self._get_visual_width(text)


# Global text justifier instance
try:
    from .terminal import _get_terminal
    terminal = _get_terminal()
    _text_justifier = _TextJustifier(terminal.width)
except (ImportError, AttributeError):
    _text_justifier = _TextJustifier(60)


def _justify_text(text: str, justify: str, terminal_width: Optional[int] = None) -> str:
    """
    Convenience function to justify text.
    
    Args:
        text: Text to justify
        justify: Justification mode ('left', 'right', 'center')
        terminal_width: Override terminal width
        
    Returns:
        str: Justified text
    """
    if terminal_width:
        justifier = _TextJustifier(terminal_width)
        return justifier.justify_text(text, justify)
    else:
        return _text_justifier.justify_text(text, justify)


def _get_visible_length(text: str) -> int:
    """
    Get visible length of text (excluding ANSI codes).
    
    Args:
        text: Text to measure
        
    Returns:
        int: Visible character count
    """
    return _text_justifier.get_visible_length(text)