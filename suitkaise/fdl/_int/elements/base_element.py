"""
Private Base Element Processor for FDL processing.

This module provides the private base class that all FDL element processors 
inherit from. It includes methods for adding content to all output streams 
with appropriate formatting.

This is internal to the FDL engine and not exposed to users.
"""

from abc import ABC, abstractmethod
from core.format_state import _FormatState


class _ElementProcessor(ABC):
    """
    Private base class for all FDL element processors.
    
    All element types (_TextElement, _CommandElement, etc.) inherit from this
    and must implement the process() method. This base class provides
    standardized methods for adding content to all output streams.
    
    This class is internal and should never be exposed to end users.
    """
    
    @abstractmethod
    def process(self, format_state: _FormatState) -> _FormatState:
        """
        Process this element and update the format state.
        
        Args:
            format_state: Current formatting state
            
        Returns:
            _FormatState: Updated formatting state
        """
        pass
    
    def _add_to_outputs(self, format_state: _FormatState, content: str) -> None:
        """
        Add content to all output streams with appropriate formatting.
        
        This is the main method element processors use to add their content
        to the output. It applies the current formatting state to generate
        the appropriate output for each format type.
        
        Args:
            format_state: Current formatting state
            content: Raw content to add
        """
        if not content:
            return
        
        # Terminal output (with ANSI codes)
        terminal_content = self._format_for_terminal(content, format_state)
        format_state.terminal_output.append(terminal_content)
        
        # Plain text output (no formatting)
        plain_content = self._format_for_plain(content, format_state)
        format_state.plain_output.append(plain_content)
        
        # Markdown output
        markdown_content = self._format_for_markdown(content, format_state)
        format_state.markdown_output.append(markdown_content)
        
        # HTML output
        html_content = self._format_for_html(content, format_state)
        format_state.html_output.append(html_content)
    
    def _format_for_terminal(self, content: str, format_state: _FormatState) -> str:
        """
        Apply ANSI formatting for terminal output.
        
        Args:
            content: Raw content
            format_state: Current formatting state
            
        Returns:
            str: Content with ANSI codes
        """
        ansi_codes = self._generate_ansi_codes(format_state)
        return f"{ansi_codes}{content}"
    
    def _format_for_plain(self, content: str, format_state: _FormatState) -> str:
        """
        Format for plain text output (no formatting).
        
        Args:
            content: Raw content
            format_state: Current formatting state (unused for plain text)
            
        Returns:
            str: Plain content
        """
        return content
    
    def _format_for_markdown(self, content: str, format_state: _FormatState) -> str:
        """
        Apply markdown formatting.
        
        Args:
            content: Raw content
            format_state: Current formatting state
            
        Returns:
            str: Content with markdown formatting
        """
        formatted = content
        
        # Apply text formatting
        if format_state.bold and format_state.italic:
            formatted = f"***{formatted}***"
        elif format_state.bold:
            formatted = f"**{formatted}**"
        elif format_state.italic:
            formatted = f"*{formatted}*"
        
        if format_state.strikethrough:
            formatted = f"~~{formatted}~~"
        
        # Note: Markdown doesn't have great support for colors or underline,
        # so we will skip those.
        
        return formatted
    
    def _format_for_html(self, content: str, format_state: _FormatState) -> str:
        """
        Apply HTML formatting.
        
        Args:
            content: Raw content
            format_state: Current formatting state
            
        Returns:
            str: Content with HTML tags and styles
        """
        if not self._needs_html_formatting(format_state):
            return content
        
        # Build CSS styles
        styles = []
        if format_state.text_color:
            styles.append(f"color: {self._normalize_color_for_html(format_state.text_color)}")
        if format_state.background_color:
            styles.append(f"background-color: {self._normalize_color_for_html(format_state.background_color)}")
        
        # Build CSS classes for text formatting
        classes = []
        if format_state.bold:
            classes.append("fdl-bold")
        if format_state.italic:
            classes.append("fdl-italic")
        if format_state.underline:
            classes.append("fdl-underline")
        if format_state.strikethrough:
            classes.append("fdl-strikethrough")
        
        # Build attributes
        attrs = []
        if styles:
            attrs.append(f'style="{"; ".join(styles)}"')
        if classes:
            attrs.append(f'class="{" ".join(classes)}"')
        
        attr_string = f' {" ".join(attrs)}' if attrs else ""
        return f"<span{attr_string}>{content}</span>"
    
    def _needs_html_formatting(self, format_state: _FormatState) -> bool:
        """Check if any formatting is applied that needs HTML tags."""
        return (
            format_state.text_color or
            format_state.background_color or
            format_state.bold or
            format_state.italic or
            format_state.underline or
            format_state.strikethrough
        )
    
    def _normalize_color_for_html(self, color: str) -> str:
        """
        Normalize color for HTML output.
        
        Args:
            color: Color in various formats (named, hex, rgb())
            
        Returns:
            str: Color suitable for HTML/CSS
        """
        color = color.strip()
        
        # Named colors - pass through as-is
        if color in ['red', 'green', 'blue', 'yellow', 'purple', 'cyan', 'magenta',
                     'orange', 'pink', 'brown', 'tan', 'black', 'white', 'gray']:
            return color
        
        # Hex colors - pass through as-is
        if color.startswith('#'):
            return color
        
        # RGB colors - convert rgb(r,g,b) to rgb(r, g, b) if needed
        if color.startswith('rgb(') and color.endswith(')'):
            rgb_content = color[4:-1]
            rgb_parts = [part.strip() for part in rgb_content.split(',')]
            if len(rgb_parts) == 3:
                try:
                    r, g, b = map(int, rgb_parts)
                    return f'rgb({r}, {g}, {b})'
                except ValueError:
                    # If conversion fails, just return the original color
                    return color
        
        # Fallback
        return color
    
    def _generate_ansi_codes(self, format_state: _FormatState) -> str:
        """
        Generate ANSI escape codes for current formatting state.
        
        Args:
            format_state: Current formatting state
            
        Returns:
            str: ANSI escape codes
        """
        codes = []
        
        # Text color
        if format_state.text_color:
            color_code = self._color_to_ansi(format_state.text_color)
            if color_code:
                codes.append(color_code)
        
        # Background color
        if format_state.background_color:
            bg_code = self._bg_color_to_ansi(format_state.background_color)
            if bg_code:
                codes.append(bg_code)
        
        # Text formatting
        if format_state.bold:
            codes.append("\033[1m")
        if format_state.italic:
            codes.append("\033[3m")
        if format_state.underline:
            codes.append("\033[4m")
        if format_state.strikethrough:
            codes.append("\033[9m")
        
        return "".join(codes)
    
    def _color_to_ansi(self, color: str) -> str:
        """Convert color to ANSI foreground code."""
        color = color.strip().lower()
        
        # Named colors
        named_colors = {
            'red': '\033[31m',
            'green': '\033[32m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'magenta': '\033[35m',
            'purple': '\033[35m',
            'cyan': '\033[36m',
            'white': '\033[97m',
            'black': '\033[30m',
            'gray': '\033[37m',
            'orange': '\033[38;5;208m',
            'pink': '\033[38;5;205m',
            'brown': '\033[38;5;94m',
            'tan': '\033[38;5;180m',
        }
        
        if color in named_colors:
            return named_colors[color]
        
        # Hex colors
        if color.startswith('#'):
            return self._hex_to_ansi_fg(color)
        
        # RGB colors
        if color.startswith('rgb(') and color.endswith(')'):
            return self._rgb_to_ansi_fg(color)
        
        return ""
    
    def _bg_color_to_ansi(self, color: str) -> str:
        """Convert color to ANSI background code."""
        color = color.strip().lower()
        
        # Named background colors
        named_bg_colors = {
            'red': '\033[41m',
            'green': '\033[42m',
            'yellow': '\033[43m',
            'blue': '\033[44m',
            'magenta': '\033[45m',
            'purple': '\033[45m',
            'cyan': '\033[46m',
            'white': '\033[107m',
            'black': '\033[40m',
            'gray': '\033[47m',
            'orange': '\033[48;5;208m',
            'pink': '\033[48;5;205m',
            'brown': '\033[48;5;94m',
            'tan': '\033[48;5;180m',
        }
        
        if color in named_bg_colors:
            return named_bg_colors[color]
        
        # Hex colors
        if color.startswith('#'):
            return self._hex_to_ansi_bg(color)
        
        # RGB colors
        if color.startswith('rgb(') and color.endswith(')'):
            return self._rgb_to_ansi_bg(color)
        
        return ""
    
    def _hex_to_ansi_fg(self, hex_color: str) -> str:
        """Convert hex color to ANSI foreground."""
        try:
            if len(hex_color) == 4:  # #RGB
                r = int(hex_color[1] * 2, 16)
                g = int(hex_color[2] * 2, 16)
                b = int(hex_color[3] * 2, 16)
            elif len(hex_color) == 7:  # #RRGGBB
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
            else:
                return ""
            
            return f'\033[38;2;{r};{g};{b}m'
        except ValueError:
            return ""
    
    def _hex_to_ansi_bg(self, hex_color: str) -> str:
        """Convert hex color to ANSI background."""
        try:
            if len(hex_color) == 4:  # #RGB
                r = int(hex_color[1] * 2, 16)
                g = int(hex_color[2] * 2, 16)
                b = int(hex_color[3] * 2, 16)
            elif len(hex_color) == 7:  # #RRGGBB
                r = int(hex_color[1:3], 16)
                g = int(hex_color[3:5], 16)
                b = int(hex_color[5:7], 16)
            else:
                return ""
            
            return f'\033[48;2;{r};{g};{b}m'
        except ValueError:
            return ""
    
    def _rgb_to_ansi_fg(self, rgb_color: str) -> str:
        """Convert rgb() color to ANSI foreground."""
        try:
            rgb_content = rgb_color[4:-1]  # Remove 'rgb(' and ')'
            r, g, b = map(int, [x.strip() for x in rgb_content.split(',')])
            return f'\033[38;2;{r};{g};{b}m'
        except (ValueError, IndexError):
            return ""
    
    def _rgb_to_ansi_bg(self, rgb_color: str) -> str:
        """Convert rgb() color to ANSI background."""
        try:
            rgb_content = rgb_color[4:-1]  # Remove 'rgb(' and ')'
            r, g, b = map(int, [x.strip() for x in rgb_content.split(',')])
            return f'\033[48;2;{r};{g};{b}m'
        except (ValueError, IndexError):
            return ""