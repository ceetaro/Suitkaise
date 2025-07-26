# setup/text_wrapping.py
"""
Smart text wrapping system for FDL that handles:
- Visual width measurement using wcwidth (terminal-accurate)
- Custom break points (spaces, punctuation, slashes, dashes)
- Word preservation (no mid-word breaks unless necessary)
- Terminal width constraints

This is internal to the FDL engine and not exposed to users.
"""

import re
from typing import List, Tuple, Optional
from .terminal import _terminal

try:
    import wcwidth
except ImportError:
    # Fallback if wcwidth not available
    wcwidth = None


class _TextWrapper:
    """
    Advanced text wrapper that handles visual width and smart break points.
    
    Features:
    - Visual width measurement using wcwidth (terminal-accurate)
    - ANSI code awareness (strips for measurement, preserves in output)
    - Smart break points: spaces, punctuation, slashes, dashes
    - Word preservation (avoids mid-word breaks)
    - Forced breaks for extremely long words
    """
    
    def __init__(self, width: Optional[int] = None):
        """
        Initialize text wrapper.
        
        Args:
            width: Maximum line width (uses terminal width if None)
        """
        self.width = width or _terminal.width
        
        # ANSI escape sequence pattern
        self._ansi_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        # Break point patterns (in order of preference)
        self._break_patterns = [
            r'[ \t]+',              # Spaces and tabs (highest preference)
            r'[.!?:;,]+',           # Punctuation marks
            r'[/\\]+',              # Slashes
            r'[-—–]+',              # Dashes (various types)
        ]
        
        # Compiled break pattern (matches any break point)
        break_chars = r'[ \t.!?:;,/\\—–-]'
        self._break_pattern = re.compile(f'({break_chars}+)')
    
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
                    wrapped_lines.append('')
                else:
                    wrapped_lines.extend(self._wrap_line(line))
            
            return wrapped_lines
        else:
            # Treat entire text as one continuous block
            return self._wrap_line(text)
    
    def _wrap_line(self, line: str) -> List[str]:
        """
        Wrap a single line of text.
        
        Args:
            line: Line to wrap
            
        Returns:
            List[str]: List of wrapped line segments
        """
        if not line.strip():
            return ['']
        
        # Check if line fits without wrapping
        if self._get_visual_width(line) <= self.width:
            return [line]
        
        # Split line into tokens (words and break points)
        tokens = self._tokenize_line(line)
        
        # Build wrapped lines
        wrapped_lines = []
        current_line = ""
        current_width = 0
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            token_width = self._get_visual_width(token)
            
            # Check if adding this token would exceed width
            if current_width + token_width > self.width and current_line:
                # Current line is full, start new line
                wrapped_lines.append(current_line.rstrip())
                current_line = ""
                current_width = 0
                
                # Skip leading whitespace on new line
                if self._is_whitespace(token):
                    i += 1
                    continue
            
            # Handle extremely long tokens that don't fit on any line
            if token_width > self.width and not current_line:
                # Force break the token
                broken_parts = self._force_break_token(token)
                wrapped_lines.extend(broken_parts[:-1])  # Add all but last part
                if broken_parts:
                    current_line = broken_parts[-1]
                    current_width = self._get_visual_width(current_line)
            else:
                # Add token to current line
                current_line += token
                current_width += token_width
            
            i += 1
        
        # Add final line if not empty
        if current_line:
            wrapped_lines.append(current_line.rstrip())
        
        return wrapped_lines if wrapped_lines else ['']
    
    def _tokenize_line(self, line: str) -> List[str]:
        """
        Split line into tokens (words and break points).
        
        Args:
            line: Line to tokenize
            
        Returns:
            List[str]: List of tokens
        """
        # Split on break points while preserving them
        tokens = self._break_pattern.split(line)
        
        # Remove empty tokens
        return [token for token in tokens if token]
    
    def _is_whitespace(self, token: str) -> bool:
        """
        Check if token is whitespace.
        
        Args:
            token: Token to check
            
        Returns:
            bool: True if token is whitespace
        """
        return bool(re.match(r'^[ \t]+$', token))
    
    def _force_break_token(self, token: str) -> List[str]:
        """
        Force break a token that's too long for any line.
        
        Args:
            token: Token to break
            
        Returns:
            List[str]: List of token parts
        """
        if not token:
            return ['']
        
        parts = []
        current_part = ""
        current_width = 0
        
        # Break character by character if necessary
        for char in token:
            char_width = self._get_char_visual_width(char)
            
            if current_width + char_width > self.width and current_part:
                parts.append(current_part)
                current_part = char
                current_width = char_width
            else:
                current_part += char
                current_width += char_width
        
        if current_part:
            parts.append(current_part)
        
        return parts if parts else ['']
    
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
        clean_text = self._ansi_pattern.sub('', text)
        
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
_text_wrapper = _TextWrapper()


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