# setup/text_justification.py
"""
Internal text justification utilities for FDL.

This module provides text justification functions that handle ANSI codes,
terminal width constraints, and different justification modes.

This is internal to the FDL engine and not exposed to users.
"""

import re
from typing import List, Optional
from .terminal import _terminal


class _TextJustifier:
    """
    Internal text justification system for FDL.
    
    Handles left, right, and center justification while preserving ANSI codes
    and respecting terminal width constraints.
    """
    
    def __init__(self, terminal_width: Optional[int] = None):
        """
        Initialize text justifier.
        
        Args:
            terminal_width: Override terminal width (uses detected width if None)
        """
        self.terminal_width = terminal_width or _terminal.width
        # ANSI escape sequence pattern for stripping codes
        self._ansi_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def justify_text(self, text: str, justify: str) -> str:
        """
        Apply justification to text.
        
        Args:
            text: Text to justify (may contain ANSI codes)
            justify: Justification mode ('left', 'right', 'center')
            
        Returns:
            str: Justified text
        """
        if not text or justify == 'left':
            return text  # Left is default, no processing needed
        
        # Split text into lines
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
        
        # Get visible length (without ANSI codes)
        visible_length = len(self._strip_ansi_codes(line))
        
        if visible_length >= self.terminal_width:
            return line  # Line too long, no padding possible
        
        # Calculate padding needed
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
        
        # Get visible length (without ANSI codes)
        visible_length = len(self._strip_ansi_codes(line))
        
        if visible_length >= self.terminal_width:
            return line  # Line too long, no padding possible
        
        # Calculate padding needed
        total_padding = self.terminal_width - visible_length
        left_padding = total_padding // 2
        
        return ' ' * left_padding + line
    
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
        return len(self._strip_ansi_codes(text))


# Global text justifier instance
_text_justifier = _TextJustifier()


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