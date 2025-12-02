# setup/text_justification.py - REVERTED TO PURE JUSTIFICATION
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
        if terminal_width is not None:
            # Use explicit width if provided, but enforce minimum only for 0/negative
            if terminal_width <= 0:
                self.terminal_width = 60
            else:
                self.terminal_width = terminal_width
        else:
            # Use detected terminal width if no explicit width provided
            try:
                from .terminal import _get_terminal
                terminal = _get_terminal()
                self.terminal_width = terminal.width
            except (ImportError, AttributeError):
                self.terminal_width = 60
            
            # Enforce minimum when using detected/default width
            self.terminal_width = max(60, self.terminal_width)
            
        # ANSI escape sequence pattern for stripping codes
        self._ansi_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def justify_text(self, text: str, justify: str) -> str:
        """
        Apply justification to text and pad each line to terminal width.

        Assumes text is already wrapped if needed. Justifies each line
        independently, then right-pads with spaces to self.terminal_width
        based on visual width (ANSI-safe).

        Args:
            text: Text to justify (may contain ANSI codes, may be multi-line)
            justify: Justification mode ('left', 'right', 'center')

        Returns:
            str: Justified and padded text
        """
        if text is None:
            return ""

        lines = text.split('\n')
        justified_lines = []

        for line in lines:
            if justify == 'right':
                justified_line = self._justify_right(line)
            elif justify == 'center':
                justified_line = self._justify_center(line)
            else:  # left
                justified_line = line

            # Ensure right padding to terminal width based on visual width
            padded_line = self._pad_to_terminal_width(justified_line)
            justified_lines.append(padded_line)

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

    def _pad_to_terminal_width(self, line: str) -> str:
        """Right-pad line with spaces to reach terminal width (ANSI-safe)."""
        visible_length = self._get_visual_width(line)
        if visible_length >= self.terminal_width:
            return line
        return line + (' ' * (self.terminal_width - visible_length))
    
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
            import wcwidth  # type: ignore
        except Exception:
            wcwidth = None  # type: ignore
        if wcwidth is not None:
            width = wcwidth.wcswidth(clean_text)
            if width is not None:
                return width

            # Fallback: character by character
            total_width = 0
            for char in clean_text:
                char_width = wcwidth.wcwidth(char)
                if char_width is not None and char_width >= 0:
                    total_width += char_width
                else:
                    # Handle control characters (like tabs) as single characters
                    total_width += 1
            return total_width
        
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
def _create_text_justifier():
    """Create text justifier instance with proper error handling."""
    try:
        from .terminal import _get_terminal
        terminal = _get_terminal()
        return _TextJustifier(terminal.width)
    except (ImportError, AttributeError):
        return _TextJustifier(60)


_text_justifier = _create_text_justifier()


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