# setup/box_generator.py
import re
from typing import Dict, List, Optional

# Import dependencies with proper error handling
try:
    from .unicode import _supports_box_drawing
except ImportError:
    def _supports_box_drawing():
        return False

try:
    from .color_conversion import _to_ansi_fg, _to_ansi_bg, _normalize_for_html
except ImportError:
    def _to_ansi_fg(color):
        return ""
    def _to_ansi_bg(color):
        return ""
    def _normalize_for_html(color):
        return str(color) if color else ""

try:
    from .text_wrapping import _wrap_text, _get_visual_width
except ImportError:
    def _wrap_text(text, width, preserve_newlines=True):
        return [text] if text else ['']
    def _get_visual_width(text):
        return len(text) if text else 0

# Box drawing character sets
BOX_STYLES = {
    'square': {
        'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
        'h': '─', 'v': '│', 'cross': '┼',
        'top_tee': '┬', 'bottom_tee': '┴', 'left_tee': '├', 'right_tee': '┤'
    },
    'rounded': {
        'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯', 
        'h': '─', 'v': '│', 'cross': '┼',
        'top_tee': '┬', 'bottom_tee': '┴', 'left_tee': '├', 'right_tee': '┤'
    },
    'double': {
        'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
        'h': '═', 'v': '║', 'cross': '╬', 
        'top_tee': '╦', 'bottom_tee': '╩', 'left_tee': '╠', 'right_tee': '╣'
    },
    'heavy': {
        'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛',
        'h': '━', 'v': '┃', 'cross': '╋',
        'top_tee': '┳', 'bottom_tee': '┻', 'left_tee': '┣', 'right_tee': '┫'
    },
    'heavy_head': {
        'tl': '┍', 'tr': '┑', 'bl': '┕', 'br': '┙',
        'h': '━', 'v': '│', 'cross': '┿',
        'top_tee': '┯', 'bottom_tee': '┷', 'left_tee': '┝', 'right_tee': '┥'
    },
    'horizontals': {
        'tl': '─', 'tr': '─', 'bl': '─', 'br': '─',
        'h': '─', 'v': ' ', 'cross': '─',
        'top_tee': '─', 'bottom_tee': '─', 'left_tee': '─', 'right_tee': '─'
    },
    'ascii': {
        'tl': '+', 'tr': '+', 'bl': '+', 'br': '+',
        'h': '-', 'v': '|', 'cross': '+',
        'top_tee': '+', 'bottom_tee': '+', 'left_tee': '+', 'right_tee': '+'
    }
}

class _BoxGenerator:
    """
    Internal box generator for creating formatted boxes with borders and content.
    
    Handles different box styles, colors, titles, and content wrapping.
    Automatically falls back to ASCII if Unicode box drawing isn't supported.
    Uses smart text wrapping that handles visual width and break points correctly.
    """
    
    def __init__(self, style: str = 'square', title: Optional[str] = None,
                 color: Optional[str] = None, background: Optional[str] = None,
                 justify: str = 'left', terminal_width: Optional[int] = None):
        """
        Initialize box generator.
        
        Args:
            style: Box style ('square', 'rounded', etc.)
            title: Optional box title
            color: Optional box border color
            background: Optional box background color
            justify: Box justification ('left', 'center', 'right')
            terminal_width: Terminal width for box sizing
        """
        # Handle None values safely
        self.style = style or 'square'
        self.title = title
        self.color = color
        self.background = background
        self.justify = justify or 'left'
        
        # Get terminal width safely
        if terminal_width is not None:
            self.terminal_width = terminal_width
        else:
            try:
                from .terminal import _terminal
                self.terminal_width = _terminal.width
            except (ImportError, AttributeError):
                self.terminal_width = 60
        
        # Ensure minimum terminal width
        self.terminal_width = max(60, self.terminal_width or 60)
        
        # Determine actual style to use (fallback to ASCII if needed)
        self.actual_style = self._get_actual_style()
        self.chars = BOX_STYLES[self.actual_style]
        
        # Calculate box dimensions
        self.max_content_width = max(20, self.terminal_width - 6)  # Account for borders + padding
        self.min_box_width = 10  # Reduced for 60-char terminals
        
        # ANSI pattern for stripping codes
        self._ansi_pattern = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    def _get_actual_style(self) -> str:
        """
        Get the actual style to use, with Unicode fallback.
        
        Returns:
            str: Style name to use
        """
        if self.style == 'ascii':
            return 'ascii'
        
        if not _supports_box_drawing():
            return 'ascii'
        
        if self.style in BOX_STYLES:
            return self.style
        
        # Unknown style, default to square or ASCII
        return 'square' if _supports_box_drawing() else 'ascii'
    
    def generate_box(self, content: str) -> Dict[str, str]:
        """
        Generate box with content for all output formats.
        
        Args:
            content: Content to put inside the box
            
        Returns:
            Dict[str, str]: Box output for each format
        """
        # Ensure content is a string
        content = str(content) if content is not None else ""
        
        # Wrap and prepare content using smart wrapper
        wrapped_lines = self._wrap_content(content)
        
        # Calculate box width
        box_width = self._calculate_box_width(wrapped_lines)
        
        # Generate box parts
        top_border = self._generate_top_border(box_width)
        bottom_border = self._generate_bottom_border(box_width)
        content_lines = self._generate_content_lines(wrapped_lines, box_width)
        
        # Combine all parts
        box_lines = [top_border] + content_lines + [bottom_border]
        
        # Apply justification to entire box
        justified_lines = self._apply_box_justification(box_lines)
        
        # Generate output for all formats
        return {
            'terminal': self._format_for_terminal(justified_lines),
            'plain': self._format_for_plain(justified_lines),
            'markdown': self._format_for_markdown(justified_lines),
            'html': self._format_for_html(justified_lines)
        }
    
    def _wrap_content(self, content: str) -> List[str]:
        """
        Wrap content to fit within box width using smart text wrapper.
        
        Args:
            content: Raw content string
            
        Returns:
            List[str]: List of wrapped lines
        """
        if not content or not content.strip():
            return ['']
        
        # Use smart text wrapper with box content width
        wrapped_lines = _wrap_text(
            text=content,
            width=self.max_content_width,
            preserve_newlines=True
        )
        
        return wrapped_lines
    
    def _calculate_box_width(self, content_lines: List[str]) -> int:
        """
        Calculate the width needed for the box using visual width measurement.
        
        Args:
            content_lines: List of content lines
            
        Returns:
            int: Box width in characters
        """
        # Find the longest content line using visual width
        max_content_length = 0
        for line in content_lines:
            # Use visual width measurement instead of len()
            visual_length = _get_visual_width(line)
            max_content_length = max(max_content_length, visual_length)
        
        # Account for title if present using visual width
        title_length = 0
        if self.title:
            title_length = _get_visual_width(self.title) + 4  # " Title " with spaces
        
        # Box width = content + padding + borders
        content_width = max(max_content_length, title_length)
        box_width = content_width + 4  # 2 chars padding + 2 chars borders
        
        # Ensure minimum width
        box_width = max(box_width, self.min_box_width)
        
        # Ensure doesn't exceed terminal width
        box_width = min(box_width, self.terminal_width - 2)
        
        return box_width
    
    def _generate_top_border(self, box_width: int) -> str:
        """
        Generate top border with optional title.
        
        Args:
            box_width: Width of the box
            
        Returns:
            str: Top border line
        """
        if self.title:
            return self._generate_title_border(box_width)
        else:
            return self._generate_simple_border(box_width, 'top')
    
    def _generate_title_border(self, box_width: int) -> str:
        """
        Generate top border with title using visual width measurement.
        
        Args:
            box_width: Width of the box
            
        Returns:
            str: Top border with title
        """
        title_with_spaces = f" {self.title} "
        title_visual_length = _get_visual_width(title_with_spaces)
        
        # Calculate remaining space for horizontal lines
        remaining_width = box_width - 2 - title_visual_length  # -2 for corners
        
        if remaining_width <= 0:
            # Title too long, truncate based on visual width
            max_title_visual_length = box_width - 6  # Account for corners and minimum borders
            truncated_title = self._truncate_to_visual_width(self.title, max_title_visual_length)
            title_with_spaces = f" {truncated_title} "
            remaining_width = box_width - 2 - _get_visual_width(title_with_spaces)
        
        # Split remaining space on both sides
        left_width = max(0, remaining_width // 2)
        right_width = max(0, remaining_width - left_width)
        
        # Build border
        left_part = self.chars['h'] * left_width
        right_part = self.chars['h'] * right_width
        
        return f"{self.chars['tl']}{left_part}{title_with_spaces}{right_part}{self.chars['tr']}"
    
    def _truncate_to_visual_width(self, text: str, max_width: int) -> str:
        """
        Truncate text to fit within visual width.
        
        Args:
            text: Text to truncate
            max_width: Maximum visual width
            
        Returns:
            str: Truncated text
        """
        if not text:
            return ""
            
        if _get_visual_width(text) <= max_width:
            return text
        
        # Truncate character by character until it fits
        truncated = ""
        for char in text:
            if _get_visual_width(truncated + char + "...") > max_width:
                break
            truncated += char
        
        return truncated + "..." if truncated else ""
    
    def _generate_simple_border(self, box_width: int, position: str) -> str:
        """
        Generate simple border line (top or bottom).
        
        Args:
            box_width: Width of the box
            position: 'top' or 'bottom'
            
        Returns:
            str: Border line
        """
        corner_left = self.chars['tl'] if position == 'top' else self.chars['bl']
        corner_right = self.chars['tr'] if position == 'top' else self.chars['br']
        
        horizontal = self.chars['h'] * (box_width - 2)
        return f"{corner_left}{horizontal}{corner_right}"
    
    def _generate_bottom_border(self, box_width: int) -> str:
        """
        Generate bottom border.
        
        Args:
            box_width: Width of the box
            
        Returns:
            str: Bottom border line
        """
        return self._generate_simple_border(box_width, 'bottom')
    
    def _generate_content_lines(self, content_lines: List[str], box_width: int) -> List[str]:
        """
        Generate content lines with borders and padding.
        
        Args:
            content_lines: List of content lines
            box_width: Width of the box
            
        Returns:
            List[str]: Content lines with borders
        """
        formatted_lines = []
        content_width = box_width - 4  # Account for borders and padding
        
        for line in content_lines:
            # Center the content by default (as specified in requirements)
            centered_line = self._center_text(line, content_width)
            bordered_line = f"{self.chars['v']} {centered_line} {self.chars['v']}"
            formatted_lines.append(bordered_line)
        
        return formatted_lines
    
    def _center_text(self, text: str, width: int) -> str:
        """
        Center text within given width using visual width measurement.
        
        Args:
            text: Text to center
            width: Available width
            
        Returns:
            str: Centered text with padding
        """
        # Use visual width instead of len()
        text_visual_length = _get_visual_width(text)
        
        if text_visual_length >= width:
            return text[:width]  # Truncate if too long
        
        # Calculate padding
        total_padding = width - text_visual_length
        left_padding = total_padding // 2
        right_padding = total_padding - left_padding
        
        return ' ' * left_padding + text + ' ' * right_padding
    
    def _apply_box_justification(self, box_lines: List[str]) -> List[str]:
        """
        Apply justification to the entire box.
        
        Args:
            box_lines: List of box lines
            
        Returns:
            List[str]: Justified box lines
        """
        if self.justify == 'left':
            return box_lines
        
        # Find box width using visual width measurement
        if not box_lines:
            return box_lines
        
        box_visual_width = _get_visual_width(box_lines[0])
        terminal_width = self.terminal_width
        
        if box_visual_width >= terminal_width:
            return box_lines
        
        if self.justify == 'center':
            padding = (terminal_width - box_visual_width) // 2
            return [' ' * padding + line for line in box_lines]
        elif self.justify == 'right':
            padding = terminal_width - box_visual_width
            return [' ' * padding + line for line in box_lines]
        
        return box_lines
    
    def _format_for_terminal(self, box_lines: List[str]) -> str:
        """
        Format box for terminal output with ANSI colors.
        
        Args:
            box_lines: List of box lines
            
        Returns:
            str: Terminal formatted box
        """
        if not self.color and not self.background:
            return '\n'.join(box_lines)
        
        # Generate color codes
        color_code = ''
        if self.color:
            fg_code = _to_ansi_fg(self.color)
            if fg_code:
                color_code += fg_code
        
        if self.background:
            bg_code = _to_ansi_bg(self.background)
            if bg_code:
                color_code += bg_code
        
        if color_code:
            colored_lines = []
            for line in box_lines:
                # Apply color to border characters only and ensure proper reset
                colored_line = self._apply_color_to_borders(line, color_code)
                colored_lines.append(colored_line)
            return '\n'.join(colored_lines)
        
        return '\n'.join(box_lines)
    
    def _apply_color_to_borders(self, line: str, color_code: str) -> str:
        """
        Apply color to border characters while preserving content formatting.
        
        Args:
            line: Box line
            color_code: ANSI color code
            
        Returns:
            str: Line with colored borders
        """
        # For box borders, we want to color the entire line but ensure proper reset
        # This ensures colors don't bleed to subsequent content
        return f"{color_code}{line}\033[0m"
    
    def _format_for_plain(self, box_lines: List[str]) -> str:
        """
        Format box for plain text output.
        
        Args:
            box_lines: List of box lines
            
        Returns:
            str: Plain text box
        """
        # Strip any ANSI codes that might be in the content
        plain_lines = [self._strip_ansi_codes(line) for line in box_lines]
        return '\n'.join(plain_lines)
    
    def _strip_ansi_codes(self, text: str) -> str:
        """
        Strip ANSI escape codes from text for length measurement.
        
        Args:
            text: Text with potential ANSI codes
            
        Returns:
            str: Text without ANSI codes
        """
        if not text:
            return ""
        return self._ansi_pattern.sub('', text)
    
    def _format_for_markdown(self, box_lines: List[str]) -> str:
        """
        Format box for markdown output.
        
        Args:
            box_lines: List of box lines
            
        Returns:
            str: Markdown formatted box (as code block)
        """
        plain_lines = [self._strip_ansi_codes(line) for line in box_lines]
        return '```\n' + '\n'.join(plain_lines) + '\n```'
    
    def _format_for_html(self, box_lines: List[str]) -> str:
        """
        Format box for HTML output.
        
        Args:
            box_lines: List of box lines
            
        Returns:
            str: HTML formatted box
        """
        # Create CSS styles for the box
        styles = []
        if self.color:
            normalized_color = _normalize_for_html(self.color)
            if normalized_color:
                styles.append(f"border-color: {normalized_color}")
        if self.background:
            normalized_bg = _normalize_for_html(self.background)
            if normalized_bg:
                styles.append(f"background-color: {normalized_bg}")
        
        style_attr = f' style="{"; ".join(styles)}"' if styles else ''
        
        # Strip ANSI codes and escape HTML
        plain_lines = []
        for line in box_lines:
            clean_line = self._strip_ansi_codes(line)
            # Proper HTML escaping
            escaped_line = (clean_line
                           .replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('"', '&quot;')
                           .replace("'", '&#x27;'))
            plain_lines.append(escaped_line)
        
        return f'<pre class="fdl-box"{style_attr}>\n' + '\n'.join(plain_lines) + '\n</pre>'