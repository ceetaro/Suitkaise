"""
INTERNAL color conversion and management system for FDL.

This module provides centralized color handling including:
- Named color definitions and ANSI code mappings
- Hex color conversion to ANSI codes
- RGB color conversion to ANSI codes  
- HTML color normalization
- Caching for performance optimization

This is internal to the FDL engine and not exposed to users.
"""

import re
import warnings
from typing import Dict, Optional, Tuple
from functools import lru_cache


class _ColorConverter:
    """
    Internal color conversion system for FDL.
    
    Handles all color format conversions with caching for performance.
    Supports named colors, hex colors (#RGB, #RRGGBB), and rgb() colors.
    """
    
    # Named colors with their ANSI foreground codes
    NAMED_COLORS_FG = {
        'red': '\033[31m',
        'green': '\033[32m', 
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'purple': '\033[35m',  # alias for magenta
        'cyan': '\033[36m',
        'white': '\033[97m',   # bright white
        'black': '\033[30m',
        'gray': '\033[37m',    # light gray
        'orange': '\033[38;5;208m',  # 256-color orange
        'pink': '\033[38;5;205m',    # 256-color pink
        'brown': '\033[38;5;94m',    # 256-color brown
        'tan': '\033[38;5;180m',     # 256-color tan
    }
    
    # Named colors with their ANSI background codes
    NAMED_COLORS_BG = {
        'red': '\033[41m',
        'green': '\033[42m',
        'yellow': '\033[43m', 
        'blue': '\033[44m',
        'magenta': '\033[45m',
        'purple': '\033[45m',  # alias for magenta
        'cyan': '\033[46m',
        'white': '\033[107m',  # bright white background
        'black': '\033[40m',
        'gray': '\033[47m',    # light gray background
        'orange': '\033[48;5;208m',  # 256-color orange background
        'pink': '\033[48;5;205m',    # 256-color pink background
        'brown': '\033[48;5;94m',    # 256-color brown background
        'tan': '\033[48;5;180m',     # 256-color tan background
    }
    
    # HTML/CSS color names (subset that matches our named colors)
    HTML_COLOR_NAMES = {
        'red', 'green', 'yellow', 'blue', 'magenta', 'purple', 'cyan',
        'white', 'black', 'gray', 'orange', 'pink', 'brown', 'tan'
    }
    
    def __init__(self):
        """Initialize color converter."""
        # Regex patterns for color parsing
        self._hex_pattern = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
        # Updated RGB pattern to accept any digits (validation happens in parsing)
        self._rgb_pattern = re.compile(r'^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$')
    
    def get_named_colors(self) -> set:
        """
        Get set of all supported named colors.
        
        Returns:
            set: All supported color names
        """
        return set(self.NAMED_COLORS_FG.keys())
    
    def is_named_color(self, color: str) -> bool:
        """
        Check if color is a supported named color.
        
        Args:
            color: Color string to check
            
        Returns:
            bool: True if color is a named color
        """
        return color.strip().lower() in self.NAMED_COLORS_FG
    
    def is_hex_color(self, color: str) -> bool:
        """
        Check if color is a valid hex color.
        
        Args:
            color: Color string to check
            
        Returns:
            bool: True if color is valid hex format (#RGB or #RRGGBB)
        """
        return bool(self._hex_pattern.match(color.strip()))
    
    def is_rgb_color(self, color: str) -> bool:
        """
        Check if color is a valid rgb() color format.
        
        This only checks the format, not the value ranges.
        Value validation happens during parsing.
        
        Args:
            color: Color string to check
            
        Returns:
            bool: True if color is valid rgb() format
        """
        match = self._rgb_pattern.match(color.strip())
        if not match:
            return False
        
        # Additional validation for value ranges
        try:
            r, g, b = map(int, match.groups())
            return all(0 <= val <= 255 for val in (r, g, b))
        except ValueError:
            return False
    
    def is_valid_color(self, color: str) -> bool:
        """
        Check if color is valid in any supported format.
        
        Args:
            color: Color string to check
            
        Returns:
            bool: True if color is valid
        """
        if not color or not isinstance(color, str):
            return False
            
        return (
            self.is_named_color(color) or
            self.is_hex_color(color) or 
            self.is_rgb_color(color)
        )
    
    @lru_cache(maxsize=128)
    def to_ansi_fg(self, color: str) -> str:
        """
        Convert color to ANSI foreground code with caching.
        
        Args:
            color: Color in any supported format
            
        Returns:
            str: ANSI foreground code, empty string if invalid
        """
        if not color or not isinstance(color, str):
            return ""
            
        color = color.strip().lower()
        
        # Named colors
        if color in self.NAMED_COLORS_FG:
            return self.NAMED_COLORS_FG[color]
        
        # Hex colors
        if self.is_hex_color(color):
            return self._hex_to_ansi_fg(color)
        
        # RGB colors  
        if self.is_rgb_color(color):
            return self._rgb_to_ansi_fg(color)
        
        # Invalid color
        warnings.warn(f"Invalid color format: '{color}'", UserWarning)
        return ""
    
    @lru_cache(maxsize=128)
    def to_ansi_bg(self, color: str) -> str:
        """
        Convert color to ANSI background code with caching.
        
        Args:
            color: Color in any supported format
            
        Returns:
            str: ANSI background code, empty string if invalid
        """
        if not color or not isinstance(color, str):
            return ""
            
        color = color.strip().lower()
        
        # Named colors
        if color in self.NAMED_COLORS_BG:
            return self.NAMED_COLORS_BG[color]
        
        # Hex colors
        if self.is_hex_color(color):
            return self._hex_to_ansi_bg(color)
        
        # RGB colors
        if self.is_rgb_color(color):
            return self._rgb_to_ansi_bg(color)
        
        # Invalid color
        warnings.warn(f"Invalid color format: '{color}'", UserWarning)
        return ""
    
    def _hex_to_ansi_fg(self, hex_color: str) -> str:
        """Convert hex color to ANSI foreground code."""
        try:
            r, g, b = self._parse_hex_color(hex_color)
            return f'\033[38;2;{r};{g};{b}m'
        except ValueError:
            return ""
    
    def _hex_to_ansi_bg(self, hex_color: str) -> str:
        """Convert hex color to ANSI background code."""
        try:
            r, g, b = self._parse_hex_color(hex_color)
            return f'\033[48;2;{r};{g};{b}m'
        except ValueError:
            return ""
    
    def _rgb_to_ansi_fg(self, rgb_color: str) -> str:
        """Convert rgb() color to ANSI foreground code."""
        try:
            r, g, b = self._parse_rgb_color(rgb_color)
            return f'\033[38;2;{r};{g};{b}m'
        except ValueError:
            return ""
    
    def _rgb_to_ansi_bg(self, rgb_color: str) -> str:
        """Convert rgb() color to ANSI background code."""
        try:
            r, g, b = self._parse_rgb_color(rgb_color)
            return f'\033[48;2;{r};{g};{b}m'
        except ValueError:
            return ""
    
    def _parse_hex_color(self, hex_color: str) -> Tuple[int, int, int]:
        """
        Parse hex color into RGB values.
        
        Args:
            hex_color: Hex color string (#RGB or #RRGGBB)
            
        Returns:
            Tuple[int, int, int]: RGB values (0-255)
            
        Raises:
            ValueError: If hex color format is invalid
        """
        hex_color = hex_color.strip()
        if not self.is_hex_color(hex_color):
            raise ValueError(f"Invalid hex color: {hex_color}")
        
        hex_digits = hex_color[1:]  # Remove #
        
        if len(hex_digits) == 3:  # #RGB format
            r = int(hex_digits[0] * 2, 16)
            g = int(hex_digits[1] * 2, 16) 
            b = int(hex_digits[2] * 2, 16)
        elif len(hex_digits) == 6:  # #RRGGBB format
            r = int(hex_digits[0:2], 16)
            g = int(hex_digits[2:4], 16)
            b = int(hex_digits[4:6], 16)
        else:
            raise ValueError(f"Invalid hex color length: {hex_color}")
        
        return r, g, b
    
    def _parse_rgb_color(self, rgb_color: str) -> Tuple[int, int, int]:
        """
        Parse rgb() color into RGB values.
        
        Args:
            rgb_color: RGB color string (rgb(r, g, b))
            
        Returns:
            Tuple[int, int, int]: RGB values (0-255)
            
        Raises:
            ValueError: If rgb color format is invalid
        """
        match = self._rgb_pattern.match(rgb_color.strip())
        if not match:
            raise ValueError(f"Invalid rgb color: {rgb_color}")
        
        try:
            r, g, b = map(int, match.groups())
        except ValueError:
            raise ValueError(f"Invalid rgb values: {rgb_color}")
        
        # Validate RGB ranges
        if not all(0 <= val <= 255 for val in (r, g, b)):
            raise ValueError(f"RGB values must be 0-255: {rgb_color}")
        
        return r, g, b
    
    @lru_cache(maxsize=64)
    def normalize_for_html(self, color: str) -> str:
        """
        Normalize color for HTML/CSS output with caching.
        
        Args:
            color: Color in any supported format
            
        Returns:
            str: Color normalized for HTML/CSS use
        """
        if not color or not isinstance(color, str):
            return color
            
        color = color.strip().lower()
        
        # Named colors that are valid in CSS
        if color in self.HTML_COLOR_NAMES:
            return color
        
        # Hex colors - pass through as-is
        if self.is_hex_color(color):
            return color.upper()  # Normalize to uppercase
        
        # RGB colors - normalize spacing
        if self.is_rgb_color(color):
            try:
                r, g, b = self._parse_rgb_color(color)
                return f'rgb({r}, {g}, {b})'
            except ValueError:
                return color  # Return original if parsing fails
        
        # Unknown format - return as-is
        return color
    
    def get_conversion_info(self, color: str) -> dict:
        """
        Get detailed information about a color and its conversions.
        
        Args:
            color: Color to analyze
            
        Returns:
            dict: Color information and conversion results
        """
        if not color or not isinstance(color, str):
            return {
                'original': color,
                'normalized': '',
                'is_valid': False,
                'color_type': 'unknown',
                'ansi_fg': '',
                'ansi_bg': '',
                'html_normalized': str(color) if color else ''
            }
            
        info = {
            'original': color,
            'normalized': color.strip().lower(),
            'is_valid': self.is_valid_color(color),
            'color_type': 'unknown',
            'ansi_fg': '',
            'ansi_bg': '',
            'html_normalized': self.normalize_for_html(color)
        }
        
        if self.is_named_color(color):
            info['color_type'] = 'named'
            info['ansi_fg'] = self.to_ansi_fg(color)
            info['ansi_bg'] = self.to_ansi_bg(color)
        elif self.is_hex_color(color):
            info['color_type'] = 'hex'
            info['ansi_fg'] = self.to_ansi_fg(color)
            info['ansi_bg'] = self.to_ansi_bg(color)
            try:
                r, g, b = self._parse_hex_color(color)
                info['rgb_values'] = (r, g, b)
            except ValueError:
                pass
        elif self.is_rgb_color(color):
            info['color_type'] = 'rgb'
            info['ansi_fg'] = self.to_ansi_fg(color)
            info['ansi_bg'] = self.to_ansi_bg(color)
            try:
                r, g, b = self._parse_rgb_color(color)
                info['rgb_values'] = (r, g, b)
            except ValueError:
                pass
        
        return info


# Global color converter instance
_color_converter = _ColorConverter()


# Convenience functions for external use
def _get_named_colors() -> set:
    """Get set of all supported named colors."""
    return _color_converter.get_named_colors()


def _is_valid_color(color: str) -> bool:
    """Check if color is valid in any supported format."""
    return _color_converter.is_valid_color(color)


def _to_ansi_fg(color: str) -> str:
    """Convert color to ANSI foreground code."""
    return _color_converter.to_ansi_fg(color)


def _to_ansi_bg(color: str) -> str:
    """Convert color to ANSI background code."""
    return _color_converter.to_ansi_bg(color)


def _normalize_for_html(color: str) -> str:
    """Normalize color for HTML/CSS output."""
    return _color_converter.normalize_for_html(color)


def _get_color_info(color: str) -> dict:
    """Get detailed information about a color."""
    return _color_converter.get_conversion_info(color)