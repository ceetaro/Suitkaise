# setup/text_wrapping.py - CLEAN PRIORITY SYSTEM IMPLEMENTATION
"""
Smart text wrapping system for FDL that handles:
- Visual width measurement using wcwidth (terminal-accurate)
- Prioritized break points: 1) whitespace, 2) after punctuation/slashes/dashes
- Word preservation (no mid-word breaks unless necessary)
- Terminal width constraints
- ANSI code safety to prevent color bleeding

This is internal to the FDL engine and not exposed to users.
"""

import re
from typing import List, Tuple, Optional

try:
    import wcwidth
except ImportError:
    # Fallback if wcwidth not available
    wcwidth = None


class _TextWrapper:
    """
    Advanced text wrapper that handles visual width and prioritized break points.
    
    Features:
    - Visual width measurement using wcwidth (terminal-accurate)
    - ANSI code awareness (strips for measurement, preserves in output)
    - Prioritized break points: 1) whitespace, 2) after punctuation/slashes/dashes
    - Word preservation (avoids mid-word breaks)
    - Forced breaks for extremely long words
    """
    
    def __init__(self, width: Optional[int] = None):
        """
        Initialize text wrapper.
        
        Args:
            width: Maximum line width (uses terminal width if None)
        """
        if width is not None:
            # Use explicit width if provided (no minimum enforcement for explicit widths)
            self.width = width
        else:
            # Only use detected terminal width if no explicit width provided
            try:
                from .terminal import _get_terminal
                terminal = _get_terminal()
                self.width = terminal.width
            except (ImportError, AttributeError):
                self.width = 60
            
            # Only enforce minimum when using detected/default width
            self.width = max(60, self.width)
        
        # ANSI escape sequence pattern
        self._ansi_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        # Priority 1: Whitespace (spaces, tabs)
        self._whitespace_pattern = re.compile(r'[ \t]+')
        
        # Priority 2: After punctuation/slashes/dashes (but not underscores or apostrophes)
        self._punctuation_chars = '.!?:;,/\\—–-'
    
    def wrap_text(self, text: str, preserve_newlines: bool = True) -> List[str]:
        """
        Wrap text to fit within specified width.
        
        Args:
            text: Text to wrap (may contain ANSI codes)
            preserve_newlines: Whether to preserve existing newlines
            
        Returns:
            List[str]: List of wrapped lines
        """
        if not text:
            return ['']
        
        if preserve_newlines:
            # Handle existing newlines by processing each line separately
            lines = text.split('\n')
            wrapped_lines = []
            
            for line in lines:
                if not line.strip():
                    wrapped_lines.append(line)  # Preserve whitespace-only lines as-is
                else:
                    wrapped_lines.extend(self._wrap_line(line))
            
            return wrapped_lines
        else:
            # Treat entire text as one continuous block
            return self._wrap_line(text)
    
    def _wrap_line(self, line: str) -> List[str]:
        """
        Wrap a single line of text using prioritized break points.
        
        Args:
            line: Line to wrap
            
        Returns:
            List[str]: List of wrapped line segments
        """
        if not line.strip():
            return [line]  # Preserve whitespace-only lines as-is
        
        # Check if line fits without wrapping
        if self._get_visual_width(line) <= self.width:
            # Expand tabs in the output text
            expanded_line = self._expand_tabs(line)
            return [self._ensure_ansi_reset(expanded_line)]
        
        wrapped_lines = []
        remaining_text = line
        
        while remaining_text and remaining_text.strip():
            current_line, remaining_text = self._fit_line_with_priority_breaks(remaining_text)
            
            if current_line:
                # Expand tabs in the output text
                expanded_line = self._expand_tabs(current_line.rstrip())
                wrapped_lines.append(self._ensure_ansi_reset(expanded_line))
        
        return wrapped_lines if wrapped_lines else ['']
    
    def _fit_line_with_priority_breaks(self, text: str) -> Tuple[str, str]:
        """
        Fit as much text as possible on one line using prioritized break points.
        
        Args:
            text: Text to fit
            
        Returns:
            Tuple: (line_content, remaining_text)
        """
        if not text:
            return ('', '')
        
        # If entire text fits, return it all
        if self._get_visual_width(text) <= self.width:
            return (text, '')
        
        # Find how much text we can fit
        max_fit_pos = self._find_max_fit_position(text)
        
        if max_fit_pos == 0:
            # Even first character doesn't fit, force take it anyway
            return (text[0], text[1:])
        
        # Look for best break point within the fitting text
        break_pos = self._find_best_break_point(text, max_fit_pos)
        
        if break_pos > 0:
            line_content = text[:break_pos]
            remaining_text = text[break_pos:].lstrip()  # Remove leading whitespace from next line
            return (line_content, remaining_text)
        else:
            # No good break point found, force break at max fit position
            return (text[:max_fit_pos], text[max_fit_pos:])
    
    def _find_max_fit_position(self, text: str) -> int:
        """
        Find the maximum position where text still fits within width.
        
        Args:
            text: Text to measure
            
        Returns:
            int: Maximum position that fits
        """
        if not text:
            return 0
        
        # Simple iteration for reliability with ANSI codes
        max_fit = 0
        for i in range(1, len(text) + 1):
            if self._get_visual_width(text[:i]) <= self.width:
                max_fit = i
            else:
                break
        
        return max_fit
    
    def _find_best_break_point(self, text: str, max_pos: int) -> int:
        """
        Find the best break point within max_pos using priority system.
        
        Args:
            text: Text to search in
            max_pos: Maximum position to consider
            
        Returns:
            int: Best break position (0 if no good break found)
        """
        search_text = text[:max_pos]
        
        # Priority 1: Find the last whitespace break
        best_whitespace = self._find_last_whitespace_break(search_text)
        if best_whitespace > 0:
            return best_whitespace
        
        # Priority 2: Find the last punctuation break (after punctuation)
        best_punctuation = self._find_last_punctuation_break(search_text)
        if best_punctuation > 0:
            return best_punctuation
        
        # No good break point found
        return 0
    
    def _find_last_whitespace_break(self, text: str) -> int:
        """
        Find the last whitespace break point.
        
        Args:
            text: Text to search
            
        Returns:
            int: Position after last whitespace (0 if none found)
        """
        # Find all whitespace matches and return the end of the last one
        matches = list(self._whitespace_pattern.finditer(text))
        if matches:
            return matches[-1].end()  # Break after the whitespace
        return 0
    
    def _find_last_punctuation_break(self, text: str) -> int:
        """
        Find the last punctuation break point (after punctuation).
        
        Args:
            text: Text to search
            
        Returns:
            int: Position after last punctuation (0 if none found)
        """
        best_pos = 0
        
        # Look for punctuation characters and find the last one
        for i, char in enumerate(text):
            if char in self._punctuation_chars:
                best_pos = i + 1  # Break AFTER the punctuation
        
        return best_pos
    
    def _get_visual_width(self, text: str) -> int:
        """
        Get visual width of text using wcwidth (terminal-accurate).
        
        Args:
            text: Text to measure
            
        Returns:
            int: Visual width in terminal columns
        """
        if not text:
            return 0
        
        # Strip ANSI codes first
        clean_text = self._strip_ansi_codes(text)
        
        # Expand tabs to spaces for proper width calculation
        clean_text = self._expand_tabs(clean_text)
        
        if wcwidth is None:
            # Fallback to simple len() if wcwidth not available
            return len(clean_text)
        
        # Use wcwidth for accurate terminal width measurement
        width = wcwidth.wcswidth(clean_text)
        
        # wcwidth returns None for control characters or invalid sequences
        # In that case, fall back to character-by-character measurement
        if width is None:
            width = 0
            for char in clean_text:
                char_width = wcwidth.wcwidth(char)
                if char_width is not None:
                    width += char_width
                # Skip characters that wcwidth can't measure (treat as 0 width)
        
        return max(0, width)
    
    def _get_char_visual_width(self, char: str) -> int:
        """
        Get visual width of a single character using wcwidth.
        
        Args:
            char: Character to measure
            
        Returns:
            int: Visual width (0, 1, or 2)
        """
        if not char:
            return 0
        
        if wcwidth is None:
            # Fallback to 1 if wcwidth not available
            return 1
        
        width = wcwidth.wcwidth(char)
        
        # wcwidth returns None for control characters
        return width if width is not None else 0
    
    def _expand_tabs(self, text: str, tab_size: int = 8) -> str:
        """
        Expand tab characters to spaces for proper width calculation.
        
        Args:
            text: Text that may contain tab characters
            tab_size: Number of spaces per tab stop (default: 8)
            
        Returns:
            str: Text with tabs expanded to spaces
        """
        if '\t' not in text:
            return text
        
        result = []
        column = 0
        
        for char in text:
            if char == '\t':
                # Calculate spaces needed to reach next tab stop
                spaces_needed = tab_size - (column % tab_size)
                result.append(' ' * spaces_needed)
                column += spaces_needed
            else:
                result.append(char)
                # For width calculation, assume most characters are 1 column
                # wcwidth will handle wide characters properly
                column += 1
        
        return ''.join(result)
    
    def _strip_ansi_codes(self, text: str) -> str:
        """
        Strip ANSI escape codes from text for length measurement.
        
        Args:
            text: Text with potential ANSI codes
            
        Returns:
            str: Text without ANSI codes
        """
        return self._ansi_pattern.sub('', text)
    
    def _ensure_ansi_reset(self, text: str) -> str:
        """
        Ensure text ends with ANSI reset if it contains ANSI codes.
        
        Args:
            text: Text that may contain ANSI codes
            
        Returns:
            str: Text with proper ANSI reset to prevent bleeding
        """
        if not text:
            return text
        
        # Check if text contains ANSI codes
        if self._ansi_pattern.search(text):
            # Check if it already ends with a reset code
            reset_pattern = re.compile(r'\x1B\[0?m$')
            if not reset_pattern.search(text):
                # Add reset code to prevent color bleeding
                return text + '\x1B[0m'
        
        return text
    
    def get_visual_width(self, text: str) -> int:
        """
        Public method to get visual width of text.
        
        Args:
            text: Text to measure
            
        Returns:
            int: Visual width in terminal columns
        """
        return self._get_visual_width(text)
    
    def fits_width(self, text: str, width: Optional[int] = None) -> bool:
        """
        Check if text fits within specified width.
        
        Args:
            text: Text to check
            width: Width to check against (uses wrapper width if None)
            
        Returns:
            bool: True if text fits
        """
        check_width = width or self.width
        return self._get_visual_width(text) <= check_width


# Global text wrapper instance
def _create_text_wrapper():
    """Create text wrapper instance with proper error handling."""
    try:
        from .terminal import _get_terminal
        terminal = _get_terminal()
        return _TextWrapper(terminal.width)  # This will use detected width with minimum enforcement
    except (ImportError, AttributeError):
        return _TextWrapper()  # This will use default 60 with minimum enforcement


_text_wrapper = _create_text_wrapper()


def _wrap_text(text: str, width: Optional[int] = None, 
               preserve_newlines: bool = True) -> List[str]:
    """
    Convenience function to wrap text.
    
    Args:
        text: Text to wrap
        width: Maximum line width (uses terminal width if None)
        preserve_newlines: Whether to preserve existing newlines
        
    Returns:
        List[str]: List of wrapped lines
    """
    if width and width != _text_wrapper.width:
        wrapper = _TextWrapper(width)
        return wrapper.wrap_text(text, preserve_newlines)
    else:
        return _text_wrapper.wrap_text(text, preserve_newlines)


def _get_visual_width(text: str) -> int:
    """
    Get visual width of text using wcwidth (terminal-accurate).
    
    Args:
        text: Text to measure
        
    Returns:
        int: Visual width in terminal columns
    """
    return _text_wrapper.get_visual_width(text)


def _fits_width(text: str, width: Optional[int] = None) -> bool:
    """
    Check if text fits within specified width.
    
    Args:
        text: Text to check
        width: Width to check against (uses terminal width if None)
        
    Returns:
        bool: True if text fits
    """
    return _text_wrapper.fits_width(text, width)


def _check_wcwidth_available() -> bool:
    """
    Check if wcwidth is available.
    
    Returns:
        bool: True if wcwidth is installed and working
    """
    return wcwidth is not None


def _get_wcwidth_info() -> dict:
    """
    Get information about wcwidth availability and version.
    
    Returns:
        dict: Information about wcwidth
    """
    if wcwidth is None:
        return {
            'available': False,
            'version': None,
            'fallback_mode': True,
            'warning': 'wcwidth not available, using len() fallback (less accurate)'
        }
    else:
        return {
            'available': True,
            'version': getattr(wcwidth, '__version__', 'unknown'),
            'fallback_mode': False,
            'info': 'Using wcwidth for accurate terminal width measurement'
        }