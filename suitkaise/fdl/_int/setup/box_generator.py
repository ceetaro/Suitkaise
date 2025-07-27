# setup/box_generator.py - REDESIGNED FROM SCRATCH
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
    from .text_wrapping import _get_visual_width
except ImportError:
    def _get_visual_width(text):
        return len(text) if text else 0

try:
    from .text_justification import _justify_text
except ImportError:
    def _justify_text(text, justify, terminal_width=None):
        return text

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

# Box character visual width mapping (measured once to save resources)
BOX_CHAR_WIDTHS = {}

def _measure_box_char_widths():
    """Measure visual width of all box characters once to save resources."""
    global BOX_CHAR_WIDTHS
    if BOX_CHAR_WIDTHS:  # Already measured
        return
    
    for style_name, chars in BOX_STYLES.items():
        BOX_CHAR_WIDTHS[style_name] = {}
        for char_name, char in chars.items():
            BOX_CHAR_WIDTHS[style_name][char_name] = _get_visual_width(char)

# Measure widths on module import
_measure_box_char_widths()


class _BoxGenerator:
    """
    Internal box generator for creating formatted boxes with borders and content.
    
    Takes pre-wrapped and pre-justified content lines, adds borders around them,
    then justifies the entire box. Handles different box styles, colors, titles.
    """
    
    def __init__(self, style: str = 'square', title: Optional[str] = None,
                 color: Optional[str] = None, background: Optional[str] = None,
                 box_justify: str = 'left', terminal_width: Optional[int] = None):
        """
        Initialize box generator.
        
        Args:
            style: Box style ('square', 'rounded', 'double', 'heavy', 'heavy_head', 'horizontals', 'ascii')
            title: Optional box title (always centered in border)
            color: Optional box border color
            background: Optional box background color  
            box_justify: Box position justification ('left', 'center', 'right')
            terminal_width: Terminal width for box sizing and justification
        """
        self.style = style or 'square'
        self.title = title
        self.color = color
        self.background = background
        self.box_justify = box_justify or 'left'
        
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
        self.char_widths = BOX_CHAR_WIDTHS[self.actual_style]
        
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
    
    def generate_box(self, content_lines: List[str]) -> Dict[str, str]:
        """
        Generate box with pre-wrapped content for all output formats.
        
        Args:
            content_lines: List of pre-wrapped and pre-justified content lines
            
        Returns:
            Dict[str, str]: Box output for each format {'terminal', 'plain', 'markdown', 'html'}
        """
        # Step 1: Handle empty content (8 spaces + 4 padding = 12 total width)
        if not content_lines or all(not line.strip() for line in content_lines):
            content_lines = [' ' * 8]  # 8 spaces for empty content
        
        # Step 2: Calculate box width based on widest line + 4 padding
        box_width = self._calculate_box_width(content_lines)
        
        # Step 3: Add box borders around content  
        box_lines = self._add_box_borders(content_lines, box_width)
        
        # Step 4: Add newlines before and after box
        box_lines_with_newlines = [''] + box_lines + ['']
        
        # Step 5: Justify entire box
        box_text = '\n'.join(box_lines_with_newlines)
        justified_box_text = _justify_text(box_text, self.box_justify, self.terminal_width)
        justified_box_lines = justified_box_text.split('\n')
        
        # Step 6: Generate output for all formats (colors applied in format methods)
        return {
            'terminal': self._format_for_terminal(justified_box_lines),
            'plain': self._format_for_plain(justified_box_lines),
            'markdown': self._format_for_markdown(justified_box_lines),
            'html': self._format_for_html(justified_box_lines)
        }
    
    def _calculate_box_width(self, content_lines: List[str]) -> int:
        """
        Calculate box width needed: widest content line + 4 padding.
        
        Args:
            content_lines: List of content lines
            
        Returns:
            int: Total box width including borders
        """
        # Find widest content line using visual width
        max_content_width = 0
        for line in content_lines:
            visual_width = _get_visual_width(line)
            max_content_width = max(max_content_width, visual_width)
        
        # Account for title if present
        title_width = 0
        if self.title:
            title_with_spaces = f" {self.title} "
            title_width = _get_visual_width(title_with_spaces)
        
        # Box width = max(content, title) + padding + borders  
        content_area_width = max(max_content_width, title_width)
        
        # Add 4 padding (2 left + 2 right) + border widths
        left_border_width = self.char_widths['v']
        right_border_width = self.char_widths['v'] 
        box_width = content_area_width + 4 + left_border_width + right_border_width
        
        # Ensure doesn't exceed terminal width
        box_width = min(box_width, self.terminal_width)
        
        return box_width
    
    def _add_box_borders(self, content_lines: List[str], box_width: int) -> List[str]:
        """
        Add box borders around content lines.
        
        Args:
            content_lines: List of content lines
            box_width: Total box width
            
        Returns:
            List[str]: Box lines with borders
        """
        box_lines = []
        
        # Generate top border (with title if present)
        top_border = self._generate_top_border(box_width)
        box_lines.append(top_border)
        
        # Generate content lines with side borders
        for line in content_lines:
            content_line = self._generate_content_line(line, box_width)
            box_lines.append(content_line)
        
        # Generate bottom border
        bottom_border = self._generate_bottom_border(box_width)
        box_lines.append(bottom_border)
        
        return box_lines
    
    def _generate_top_border(self, box_width: int) -> str:
        """
        Generate top border with optional title.
        
        Args:
            box_width: Total box width
            
        Returns:
            str: Top border line
        """
        if self.title:
            return self._generate_title_border(box_width)
        else:
            return self._generate_simple_border(box_width, 'top')
    
    def _generate_title_border(self, box_width: int) -> str:
        """
        Generate top border with centered title.
        
        Args:
            box_width: Total box width
            
        Returns:
            str: Top border with centered title
        """
        title_with_spaces = f" {self.title} "
        title_visual_width = _get_visual_width(title_with_spaces)
        
        # Calculate available space for horizontal lines
        corner_width = self.char_widths['tl'] + self.char_widths['tr']
        available_width = box_width - corner_width - title_visual_width
        
        if available_width <= 0:
            # Title too long, truncate it
            max_title_width = box_width - corner_width - 4  # Leave some space for borders
            truncated_title = self._truncate_to_visual_width(self.title, max_title_width)
            title_with_spaces = f" {truncated_title} "
            title_visual_width = _get_visual_width(title_with_spaces)
            available_width = box_width - corner_width - title_visual_width
        
        # Split available space evenly
        left_width = max(0, available_width // 2)
        right_width = max(0, available_width - left_width)
        
        # Build title border
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
            str: Truncated text with ellipsis if needed
        """
        if not text:
            return ""
        
        if _get_visual_width(text) <= max_width:
            return text
        
        # Truncate character by character until it fits with ellipsis
        truncated = ""
        for char in text:
            test_text = truncated + char + "..."
            if _get_visual_width(test_text) > max_width:
                break
            truncated += char
        
        return truncated + "..." if truncated else ""
    
    def _generate_simple_border(self, box_width: int, position: str) -> str:
        """
        Generate simple border line (top or bottom).
        
        Args:
            box_width: Total box width
            position: 'top' or 'bottom'
            
        Returns:
            str: Border line
        """
        if position == 'top':
            left_corner = self.chars['tl']
            right_corner = self.chars['tr']
        else:  # bottom
            left_corner = self.chars['bl']
            right_corner = self.chars['br']
        
        # Calculate horizontal line width
        corner_width = self.char_widths['tl'] + self.char_widths['tr']  # Assume corners same width
        horizontal_width = box_width - corner_width
        
        horizontal_line = self.chars['h'] * horizontal_width
        return f"{left_corner}{horizontal_line}{right_corner}"
    
    def _generate_bottom_border(self, box_width: int) -> str:
        """
        Generate bottom border.
        
        Args:
            box_width: Total box width
            
        Returns:
            str: Bottom border line
        """
        return self._generate_simple_border(box_width, 'bottom')
    
    def _generate_content_line(self, content: str, box_width: int) -> str:
        """
        Generate content line with side borders and padding.
        
        Args:
            content: Content line (pre-justified)
            box_width: Total box width
            
        Returns:
            str: Content line with borders
        """
        # Calculate content area width
        border_width = self.char_widths['v'] * 2  # Left + right borders
        content_area_width = box_width - border_width - 4  # Subtract borders and 4 padding
        
        # Pad content to fill content area
        content_visual_width = _get_visual_width(content)
        if content_visual_width < content_area_width:
            padding_needed = content_area_width - content_visual_width
            content = content + (' ' * padding_needed)
        elif content_visual_width > content_area_width:
            # Content too wide, truncate
            content = self._truncate_to_visual_width(content, content_area_width)
            remaining_padding = content_area_width - _get_visual_width(content)
            content = content + (' ' * remaining_padding)
        
        # Add borders and padding
        return f"{self.chars['v']}  {content}  {self.chars['v']}"
    
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
        
        # Apply colors to border characters only
        colored_lines = []
        for line in box_lines:
            colored_line = self._apply_color_to_borders(line)
            colored_lines.append(colored_line)
        
        return '\n'.join(colored_lines)
    
    def _apply_color_to_borders(self, line: str) -> str:
        """
        Apply color to border characters while preserving content formatting.
        
        Args:
            line: Box line
            
        Returns:
            str: Line with colored borders
        """
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
            # Apply color to entire line but ensure proper reset
            return f"{color_code}{line}\033[0m"
        
        return line
    
    def _format_for_plain(self, box_lines: List[str]) -> str:
        """
        Format box for plain text output.
        
        Args:
            box_lines: List of box lines
            
        Returns:
            str: Plain text box
        """
        # Strip any ANSI codes
        plain_lines = [self._strip_ansi_codes(line) for line in box_lines]
        return '\n'.join(plain_lines)
    
    def _strip_ansi_codes(self, text: str) -> str:
        """
        Strip ANSI escape codes from text.
        
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
        # Create CSS styles
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
        
        # Escape HTML and strip ANSI codes
        escaped_lines = []
        for line in box_lines:
            clean_line = self._strip_ansi_codes(line)
            escaped_line = (clean_line
                           .replace('&', '&amp;')
                           .replace('<', '&lt;')
                           .replace('>', '&gt;')
                           .replace('"', '&quot;')
                           .replace("'", '&#x27;'))
            escaped_lines.append(escaped_line)
        
        return f'<pre class="fdl-box"{style_attr}>\n' + '\n'.join(escaped_lines) + '\n</pre>'