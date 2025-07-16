"""
Custom Box Implementation for fdl - High Performance Box Drawing

This module provides custom box drawing functionality that avoids Rich Panel overhead.
Features:
- Unicode box styles with automatic ASCII fallback
- Title support with color formatting
- Direct ANSI output for maximum performance
- Integration with fdl command processor for colors
- Thread-safe design

Supported box styles:
- square: ┌─┐ style boxes
- rounded: ╭─╮ style boxes  
- double: ╔═╗ style boxes
- heavy: ┏━┓ style boxes
- heavy_head: ┍━┑ style boxes (heavy top, light sides)
- horizontals: ─── style (horizontal lines only)
- ascii: +--+ style (fallback)

Usage:
- </box rounded>content</end box>
- </box rounded, title Important>content
- </box rounded, title Important, green>content
"""

import warnings
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

# Import our internal systems
from ..setup.unicode import _get_unicode_support
from ..setup.terminal import _terminal
from ..core.command_processor import _get_command_processor


class BoxError(Exception):
    """Raised when box operations fail."""
    pass


class InvalidBoxStyleError(BoxError):
    """Raised when box style is invalid."""
    pass


@dataclass
class _BoxStyle:
    """
    Defines a box drawing style with character mappings.
    
    Attributes:
        name (str): Style name (square, rounded, etc.)
        chars (Dict[str, str]): Character mapping for box parts
        is_unicode (bool): Whether this style uses Unicode characters
    """
    name: str
    chars: Dict[str, str]
    is_unicode: bool


class _BoxRenderer:
    """
    High-performance box renderer with Unicode fallback support.
    
    Handles all box drawing with direct ANSI output for maximum performance.
    Uses cached character sets and integrates with fdl command processor.
    """
    
    # Unicode character sets (updated with junction characters for table support)
    UNICODE_STYLES = {
        'square': {
            'top_left': '┌', 'top_right': '┐', 'bottom_left': '└', 'bottom_right': '┘',
            'vertical': '│', 'horizontal': '─',
            'top_junction': '┬', 'bottom_junction': '┴', 'cross_junction': '┼',
            'left_junction': '├', 'right_junction': '┤'
        },
        'rounded': {
            'top_left': '╭', 'top_right': '╮', 'bottom_left': '╰', 'bottom_right': '╯',
            'vertical': '│', 'horizontal': '─',
            'top_junction': '┬', 'bottom_junction': '┴', 'cross_junction': '┼',
            'left_junction': '├', 'right_junction': '┤'
        },
        'double': {
            'top_left': '╔', 'top_right': '╗', 'bottom_left': '╚', 'bottom_right': '╝',
            'vertical': '║', 'horizontal': '═',
            'top_junction': '╦', 'bottom_junction': '╩', 'cross_junction': '╬',
            'left_junction': '╠', 'right_junction': '╣'
        },
        'heavy': {
            'top_left': '┏', 'top_right': '┓', 'bottom_left': '┗', 'bottom_right': '┛',
            'vertical': '┃', 'horizontal': '━',
            'top_junction': '┳', 'bottom_junction': '┻', 'cross_junction': '╋',
            'left_junction': '┣', 'right_junction': '┫'
        },
        'heavy_head': {
            'top_left': '┍', 'top_right': '┑', 'bottom_left': '┕', 'bottom_right': '┙',
            'vertical': '│', 'horizontal': '━',
            'top_junction': '┯', 'bottom_junction': '┷', 'cross_junction': '┿',
            'left_junction': '┝', 'right_junction': '┥'
        },
        'horizontals': {
            'top_left': '─', 'top_right': '─', 'bottom_left': '─', 'bottom_right': '─',
            'vertical': ' ', 'horizontal': '─',
            'top_junction': '─', 'bottom_junction': '─', 'cross_junction': '─',
            'left_junction': '─', 'right_junction': '─'
        }
    }
    
    # ASCII fallback style (updated with junction characters)
    ASCII_STYLE = {
        'top_left': '+', 'top_right': '+', 'bottom_left': '+', 'bottom_right': '+',
        'vertical': '|', 'horizontal': '-',
        'top_junction': '+', 'bottom_junction': '+', 'cross_junction': '+',
        'left_junction': '+', 'right_junction': '+'
    }
    
    def __init__(self):
        """Initialize box renderer with Unicode detection."""
        self._unicode_support = _get_unicode_support()
        self._supports_unicode = self._unicode_support.supports_box_drawing
        self._command_processor = _get_command_processor()
        self._terminal_width = _terminal.width
        
        # Cache compiled box styles
        self._style_cache: Dict[str, _BoxStyle] = {}
        self._compile_all_styles()
        
        # Performance tracking
        self._rendered_count = 0
    
    def _compile_all_styles(self) -> None:
        """Compile all box styles with appropriate character sets."""
        # Unicode styles (if supported)
        if self._supports_unicode:
            for style_name, chars in self.UNICODE_STYLES.items():
                self._style_cache[style_name] = _BoxStyle(
                    name=style_name,
                    chars=chars.copy(),  # Make a copy to avoid reference issues
                    is_unicode=True
                )
        else:
            # If Unicode not supported, use ASCII for all styles
            for style_name in self.UNICODE_STYLES.keys():
                self._style_cache[style_name] = _BoxStyle(
                    name=style_name,
                    chars=self.ASCII_STYLE.copy(),
                    is_unicode=False
                )
        
        # Always add ASCII style as explicit option
        self._style_cache['ascii'] = _BoxStyle(
            name='ascii',
            chars=self.ASCII_STYLE.copy(),
            is_unicode=False
        )
    
    def get_box_style(self, style_name: str) -> _BoxStyle:
        """
        Get a compiled box style with fallback logic.
        
        Args:
            style_name (str): Requested box style name
            
        Returns:
            _BoxStyle: Box style to use
            
        Raises:
            InvalidBoxStyleError: If style is completely unknown
        """
        style_name = style_name.lower().strip()
        
        # Check if style exists
        if style_name in self._style_cache:
            return self._style_cache[style_name]
        
        # Unknown style - fallback to ASCII
        if 'ascii' in self._style_cache:
            warnings.warn(f"Unknown box style '{style_name}', using ASCII fallback", UserWarning)
            return self._style_cache['ascii']
        
        # This should never happen
        raise InvalidBoxStyleError(f"No fallback available for unknown style: {style_name}")
    
    def calculate_box_dimensions(self, content_lines: List[str], 
                                title: Optional[str] = None,
                                min_width: int = 10) -> Tuple[int, int]:
        """
        Calculate box dimensions based on content.
        
        Args:
            content_lines (List[str]): Lines of content to box
            title (Optional[str]): Box title (affects width)
            min_width (int): Minimum box width
            
        Returns:
            Tuple[int, int]: (box_width, box_height)
        """
        # Calculate content width (longest line)
        content_width = max(len(line) for line in content_lines) if content_lines else 0
        
        # Title width consideration
        title_width = len(title) + 4 if title else 0  # Account for title formatting
        
        # Box width = max(content_width, title_width, min_width) + 4 (for borders + padding)
        box_width = max(content_width, title_width, min_width) + 4
        
        # Respect terminal width
        max_width = self._terminal_width - 2
        box_width = min(box_width, max_width)
        
        # Box height = content lines + 2 (for top/bottom borders)
        box_height = len(content_lines) + 2
        
        return box_width, box_height
    
    def render_box(self, content: str, style_name: str = "square",
                  title: Optional[str] = None, color: Optional[str] = None,
                  justify: str = "left") -> str:
        """
        Render a complete box with content and optional justification.
        
        Args:
            content (str): Content to display in box
            style_name (str): Box style to use
            title (Optional[str]): Box title
            color (Optional[str]): Box color
            justify (str): Justification - 'left', 'right', 'center' (default: 'left')
            
        Returns:
            str: Complete rendered box as string with optional justification and newlines
        """
        self._rendered_count += 1
        
        # Render the box content
        box_content = self._render_box_internal(content, style_name, title, color)
        
        # Apply justification if requested
        if justify != "left":
            justified_lines = []
            terminal_width = self._terminal_width
            
            for line in box_content.split('\n'):
                if line.strip():  # Only justify non-empty lines
                    line_length = len(line)
                    available_space = terminal_width - line_length
                    
                    if justify == "right":
                        padding = max(0, available_space)
                        justified_line = ' ' * padding + line
                    elif justify == "center":
                        padding = max(0, available_space // 2)
                        justified_line = ' ' * padding + line
                    else:
                        justified_line = line
                    
                    justified_lines.append(justified_line)
                else:
                    justified_lines.append(line)
            
            box_content = '\n'.join(justified_lines)
        
        # Add newlines before and after
        return '\n' + box_content + '\n'
    
    def _render_box_internal(self, content: str, style_name: str = "square",
                            title: Optional[str] = None, color: Optional[str] = None) -> str:
        """Internal method to render box content without centering."""
        # Get box style
        style = self.get_box_style(style_name)
        
        # Split content into lines
        content_lines = content.split('\n')
        
        # Calculate box dimensions
        box_width, box_height = self.calculate_box_dimensions(content_lines, title)
        
        # Build the box
        box_lines = []
        
        # Top border with optional title
        top_line = self._render_top_border(style, box_width, title, color)
        box_lines.append(top_line)
        
        # Content lines
        content_box_lines = self._render_content_lines(style, content_lines, box_width, color)
        box_lines.extend(content_box_lines)
        
        # Bottom border
        bottom_line = self._render_bottom_border(style, box_width, color)
        box_lines.append(bottom_line)
        
        return '\n'.join(box_lines)
    
    def _render_top_border(self, style: _BoxStyle, width: int, 
                          title: Optional[str], color: Optional[str]) -> str:
        """Render the top border with optional title."""
        chars = style.chars
        
        if title:
            # Top border with title: ┌── Title ──┐
            title_text = f" {title} "
            title_len = len(title_text)
            
            # Calculate spacing
            remaining_width = width - 2 - title_len  # -2 for corners
            left_fill = remaining_width // 2
            right_fill = remaining_width - left_fill
            
            border = (chars['top_left'] + 
                     chars['horizontal'] * left_fill +
                     title_text +
                     chars['horizontal'] * right_fill +
                     chars['top_right'])
        else:
            # Simple top border: ┌────────┐
            border = (chars['top_left'] + 
                     chars['horizontal'] * (width - 2) + 
                     chars['top_right'])
        
        # Apply color if specified
        if color:
            border = self._apply_color(border, color)
        
        return border
    
    def _render_content_lines(self, style: _BoxStyle, content_lines: List[str], 
                             width: int, color: Optional[str]) -> List[str]:
        """Render content lines with side borders and padding."""
        chars = style.chars
        content_width = width - 4  # Available width inside box (account for borders + padding)
        
        box_lines = []
        for line in content_lines:
            # Truncate or pad line to fit
            if len(line) > content_width:
                padded_line = line[:content_width]
            else:
                padded_line = line.ljust(content_width)
            
            # Add side borders with padding
            bordered_line = chars['vertical'] + ' ' + padded_line + ' ' + chars['vertical']
            
            # Apply color to borders only (preserve content formatting)
            if color:
                left_border = self._apply_color(chars['vertical'] + ' ', color)
                right_border = self._apply_color(' ' + chars['vertical'], color)
                bordered_line = left_border + padded_line + right_border
            
            box_lines.append(bordered_line)
        
        return box_lines
    
    def _render_bottom_border(self, style: _BoxStyle, width: int, 
                             color: Optional[str]) -> str:
        """Render the bottom border."""
        chars = style.chars
        
        # Simple bottom border: └────────┘
        border = (chars['bottom_left'] + 
                 chars['horizontal'] * (width - 2) + 
                 chars['bottom_right'])
        
        # Apply color if specified
        if color:
            border = self._apply_color(border, color)
        
        return border
    
    def _apply_color(self, text: str, color: str) -> str:
        """Apply color to text using command processor."""
        try:
            # Create a temporary state and apply color
            from ..core.command_processor import _FormattingState
            current_state = _FormattingState()
            
            # Process color command
            new_state, ansi_sequence = self._command_processor.process_command(
                color, current_state
            )
            
            # Generate reset sequence
            reset_ansi = self._command_processor.generate_reset_ansi()
            
            return f"{ansi_sequence}{text}{reset_ansi}"
            
        except Exception:
            # If color processing fails, return text as-is
            warnings.warn(f"Failed to apply color '{color}' to box", UserWarning)
            return text
    
    def get_available_styles(self) -> List[str]:
        """Get list of available box styles."""
        return list(self._style_cache.keys())
    
    def get_performance_stats(self) -> Dict[str, Union[int, bool]]:
        """Get performance statistics."""
        return {
            'boxes_rendered': self._rendered_count,
            'unicode_supported': self._supports_unicode,
            'styles_available': len(self._style_cache),
            'terminal_width': self._terminal_width
        }


class _BoxCommand:
    """
    Represents a parsed box command with its parameters.
    
    Handles parsing of commands like:
    - </box rounded>
    - </box rounded, title Important>
    - </box rounded, title Important, green>
    """
    
    def __init__(self, command_text: str):
        """
        Parse a box command string.
        
        Args:
            command_text (str): Command text to parse (e.g., "box rounded, title Important, green")
        """
        self.style = "square"  # Default style
        self.title: Optional[str] = None
        self.color: Optional[str] = None
        
        self._parse_command(command_text)
    
    def _parse_command(self, command_text: str) -> None:
        """Parse the command text into components."""
        # Remove "box" prefix if present
        if command_text.startswith('box '):
            command_text = command_text[4:]
        elif command_text == 'box':
            return  # Just "box" with no parameters
        
        # Split by commas and process each part
        parts = [part.strip() for part in command_text.split(',')]
        
        for part in parts:
            if not part:
                continue
            
            # Check for title
            if part.startswith('title '):
                self.title = part[6:].strip()
            # Check for known box styles
            elif part in ['square', 'rounded', 'double', 'heavy', 'heavy_head', 'horizontals', 'ascii']:
                self.style = part
            # Assume it's a color
            else:
                self.color = part


# Global box renderer instance
_global_box_renderer: Optional[_BoxRenderer] = None


def _get_box_renderer() -> _BoxRenderer:
    """Get the global box renderer instance."""
    global _global_box_renderer
    if _global_box_renderer is None:
        _global_box_renderer = _BoxRenderer()
    return _global_box_renderer


# Internal API functions for use by reconstructor and public API
def _create_box(content: str, style: str = "square", 
               title: Optional[str] = None, color: Optional[str] = None,
               justify: str = "left") -> str:
    """
    INTERNAL: Create a box around content.
    
    Args:
        content (str): Content to display in box
        style (str): Box style (square, rounded, double, heavy, heavy_head, horizontals)
        title (Optional[str]): Box title
        color (Optional[str]): Box color
        justify (str): Justification - 'left', 'right', 'center' (default: 'left')
        
    Returns:
        str: Rendered box as string
    """
    renderer = _get_box_renderer()
    return renderer.render_box(content, style, title, color, justify)


def _parse_box_command(command_text: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    INTERNAL: Parse a box command into components.
    
    Args:
        command_text (str): Command text (e.g., "box rounded, title Important, green")
        
    Returns:
        Tuple[str, Optional[str], Optional[str]]: (style, title, color)
    """
    cmd = _BoxCommand(command_text)
    return cmd.style, cmd.title, cmd.color


def _get_available_box_styles() -> List[str]:
    """INTERNAL: Get list of available box styles."""
    return _get_box_renderer().get_available_styles()


def _get_box_performance_stats() -> Dict[str, Union[int, bool]]:
    """INTERNAL: Get box rendering performance statistics."""
    return _get_box_renderer().get_performance_stats()