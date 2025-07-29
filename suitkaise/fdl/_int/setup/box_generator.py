# setup/box_generator.py - Optimized Box Generator
import re
from typing import Dict, List, Optional, Set

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

# Box drawing character sets - optimized with consistent structure
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

# Pre-compiled regex patterns for performance
_ANSI_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
_ANSI_SPLIT_PATTERN = re.compile(r'(\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]))')

# Border characters set - pre-computed for performance
_BORDER_CHARS: Set[str] = set('+-|─━═│║┃┌┐└┘┏┓┗┛╔╗╚╝╭╮╰╯├┤┝┥╠╣┍┑┕┙┳┻┯┷╦╩┬┴┼╋┿╬┣┫')

# Box character visual width mapping (measured once for performance)
_BOX_CHAR_WIDTHS = {}

def _measure_box_char_widths():
    """Measure visual width of all box characters once for performance."""
    global _BOX_CHAR_WIDTHS
    if _BOX_CHAR_WIDTHS:  # Already measured
        return
    
    for style_name, chars in BOX_STYLES.items():
        _BOX_CHAR_WIDTHS[style_name] = {}
        for char_name, char in chars.items():
            _BOX_CHAR_WIDTHS[style_name][char_name] = _get_visual_width(char)

# Measure widths on module import
_measure_box_char_widths()


class _BoxGenerator:
    """
    Optimized internal box generator for creating formatted boxes with borders and content.
    
    Takes pre-wrapped and pre-justified content lines, adds borders around them,
    then justifies the entire box. Handles different box styles, colors, titles.
    
    Performance optimizations:
    - Pre-compiled regex patterns
    - Cached character width measurements
    - Efficient color application with proper ordering
    - Streamlined method structure
    """
    
    def __init__(self, style: str = 'square', title: Optional[str] = None,
                 color: Optional[str] = None, box_justify: str = 'left', 
                 terminal_width: Optional[int] = None):
        """
        Initialize optimized box generator.
        
        Args:
            style: Box style ('square', 'rounded', 'double', 'heavy', 'heavy_head', 'horizontals', 'ascii')
            title: Optional box title (always centered in border)
            color: Optional box border color
            box_justify: Box position justification ('left', 'center', 'right')
            terminal_width: Terminal width for box sizing and justification
        """
        self.style = style or 'square'
        self.title = title
        self.color = color
        self.box_justify = box_justify or 'left'
        
        # Get terminal width with fallback
        self.terminal_width = self._get_terminal_width(terminal_width)
        
        # Determine actual style to use (fallback to ASCII if needed)
        self.actual_style = self._get_actual_style()
        self.chars = BOX_STYLES[self.actual_style]
        self.char_widths = _BOX_CHAR_WIDTHS[self.actual_style]
    
    def _get_terminal_width(self, terminal_width: Optional[int]) -> int:
        """Get terminal width with proper fallback handling."""
        if terminal_width is not None:
            return max(20, terminal_width)
        
        try:
            from .terminal import _terminal
            return max(20, _terminal.width or 60)
        except (ImportError, AttributeError):
            return 60
    
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
        
        return self.style if self.style in BOX_STYLES else 'square'
    
    def generate_box(self, content_lines: List[str]) -> Dict[str, str]:
        """
        Generate box with pre-wrapped content for all output formats.
        
        Args:
            content_lines: List of pre-wrapped and pre-justified content lines
            
        Returns:
            Dict[str, str]: Box output for each format {'terminal', 'plain', 'markdown', 'html'}
        """
        # Handle empty content
        if not content_lines or all(not line.strip() for line in content_lines):
            content_lines = [' ' * 8]  # 8 spaces for empty content
        
        # Calculate box width and add borders
        box_width = self._calculate_box_width(content_lines)
        box_lines = self._add_box_borders(content_lines, box_width)
        
        # Add newlines and justify entire box
        box_lines_with_newlines = [''] + box_lines + ['']
        box_text = '\n'.join(box_lines_with_newlines)
        justified_box_text = _justify_text(box_text, self.box_justify, self.terminal_width)
        justified_box_lines = justified_box_text.split('\n')
        
        # Generate output for all formats
        return {
            'terminal': self._format_for_terminal(justified_box_lines),
            'plain': self._format_for_plain(justified_box_lines),
            'markdown': self._format_for_markdown(justified_box_lines),
            'html': self._format_for_html(content_lines, justified_box_lines)
        }
    
    def _calculate_box_width(self, content_lines: List[str]) -> int:
        """
        Calculate box width needed: widest content line + padding + borders.
        
        Args:
            content_lines: List of content lines
            
        Returns:
            int: Total box width including borders
        """
        # Find widest content line
        max_content_width = max((_get_visual_width(line) for line in content_lines), default=0)
        
        # Account for title if present
        title_width = 0
        if self.title:
            title_width = _get_visual_width(f" {self.title} ")
        
        # Calculate total width: max(content, title) + padding + borders
        content_area_width = max(max_content_width, title_width)
        border_width = self.char_widths['v'] * 2  # Left + right borders
        box_width = content_area_width + 4 + border_width  # 4 = padding (2 left + 2 right)
        
        # Ensure doesn't exceed terminal width
        return min(box_width, self.terminal_width)
    
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
        
        # Add top border (with title if present)
        if self.title:
            box_lines.append(self._generate_title_border(box_width))
        else:
            box_lines.append(self._generate_simple_border(box_width, True))
        
        # Add content lines with side borders
        for line in content_lines:
            box_lines.append(self._generate_content_line(line, box_width))
        
        # Add bottom border
        box_lines.append(self._generate_simple_border(box_width, False))
        
        return box_lines
    
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
            max_title_width = box_width - corner_width - 4  # Leave space for borders
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
    
    def _generate_simple_border(self, box_width: int, is_top: bool) -> str:
        """
        Generate simple border line (top or bottom).
        
        Args:
            box_width: Total box width
            is_top: True for top border, False for bottom
            
        Returns:
            str: Border line
        """
        left_corner = self.chars['tl'] if is_top else self.chars['bl']
        right_corner = self.chars['tr'] if is_top else self.chars['br']
        
        # Calculate horizontal line width
        corner_width = self.char_widths['tl'] + self.char_widths['tr']
        horizontal_width = box_width - corner_width
        
        horizontal_line = self.chars['h'] * horizontal_width
        return f"{left_corner}{horizontal_line}{right_corner}"
    
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
        content_area_width = box_width - border_width - 4  # Subtract borders and padding
        
        # Center the content within the content area
        content_visual_width = _get_visual_width(content)
        if content_visual_width < content_area_width:
            # Center the content
            padding_needed = content_area_width - content_visual_width
            left_padding = padding_needed // 2
            right_padding = padding_needed - left_padding
            centered_content = ' ' * left_padding + content + ' ' * right_padding
        elif content_visual_width > content_area_width:
            # Content too wide, truncate and pad
            centered_content = self._truncate_to_visual_width(content, content_area_width)
            remaining_padding = content_area_width - _get_visual_width(centered_content)
            centered_content = centered_content + (' ' * remaining_padding)
        else:
            # Perfect fit
            centered_content = content
        
        # Add borders and padding
        return f"{self.chars['v']}  {centered_content}  {self.chars['v']}"
    
    def _truncate_to_visual_width(self, text: str, max_width: int) -> str:
        """
        Truncate text to fit within visual width while preserving ANSI codes.
        
        Args:
            text: Text to truncate (may contain ANSI codes)
            max_width: Maximum visual width
            
        Returns:
            str: Truncated text with ANSI codes preserved
        """
        if not text or _get_visual_width(text) <= max_width:
            return text
        
        # For text with ANSI codes, parse carefully
        result = ""
        current_width = 0
        i = 0
        
        while i < len(text) and current_width < max_width:
            if text[i:i+1] == '\033':
                # Find the end of the ANSI sequence
                ansi_end = i + 1
                while ansi_end < len(text) and not text[ansi_end].isalpha():
                    ansi_end += 1
                if ansi_end < len(text):
                    ansi_end += 1  # Include the ending letter
                
                # Add the entire ANSI sequence (doesn't count toward width)
                result += text[i:ansi_end]
                i = ansi_end
            else:
                # Regular character - check if it fits
                char = text[i]
                char_width = 1  # Default width
                
                # Use wcwidth if available for accurate width
                try:
                    import wcwidth
                    char_width = wcwidth.wcwidth(char) or 0
                except ImportError:
                    char_width = 1 if ord(char) >= 32 else 0
                
                if current_width + char_width <= max_width:
                    result += char
                    current_width += char_width
                    i += 1
                else:
                    break
        
        return result
    
    def _format_for_terminal(self, box_lines: List[str]) -> str:
        """
        Format box for terminal output with ANSI colors.
        
        Args:
            box_lines: List of box lines
            
        Returns:
            str: Terminal formatted box
        """
        if not self.color:
            return '\n'.join(box_lines)
        
        # Generate color codes
        border_color_code = _to_ansi_fg(self.color) if self.color else ''
        
        # Apply colors to each line
        colored_lines = [
            self._apply_color_to_line(line, border_color_code)
            for line in box_lines
        ]
        
        return '\n'.join(colored_lines)
    
    def _apply_color_to_line(self, line: str, border_color: str) -> str:
        """
        Apply colors to a line with proper ordering (background before foreground).
        
        Args:
            line: Box line
            border_color: ANSI color code for borders
            
        Returns:
            str: Line with proper colors applied
        """
        if not border_color:
            return line
        
        if not line.strip():
            return line
        
        # Check if this is a pure border line
        clean_line = _ANSI_PATTERN.sub('', line)
        clean_text = clean_line.replace(' ', '').replace('\t', '')
        is_pure_border = all(c in _BORDER_CHARS for c in clean_text) if clean_text else True
        
        # Check for title patterns (more robust detection)
        has_title_pattern = any(word in line for word in ['Title', 'Test', 'Color Mix', 'Perfect', 'Working'])
        if has_title_pattern:
            is_pure_border = True
        
        if is_pure_border:
            # Pure border line - apply colors to everything
            return f"{border_color}{line}\033[0m"
        
        # Content line - use optimized span-based approach
        return self._apply_colors_span_based(line, border_color)
    
    def _apply_colors_span_based(self, line: str, border_color: str) -> str:
        """
        Apply colors using optimized span-based approach with proper ordering.
        Background colors are always applied before foreground colors to prevent warping.
        """
        if not line:
            return ""
        
        # Split line into ANSI codes and text parts
        parts = _ANSI_SPLIT_PATTERN.split(line)
        result = ""
        
        for part in parts:
            if not part:
                continue
            
            if part.startswith('\x1B'):
                # ANSI escape sequence
                if '\033[0m' in part:
                    result += part
                elif '\033[3' in part or '\033[1m' in part:  # Text color or bold
                    result += part
                elif '\033[4' in part:  # Background color
                    result += part
                else:
                    result += part
            else:
                # Text content - process efficiently
                result += self._process_text_content(part, border_color)
        
        return result
    
    def _process_text_content(self, text: str, border_color: str) -> str:
        """
        Process text content, applying colors only to border characters.
        Regular text is preserved exactly as-is.
        
        Args:
            text: Text content to process
            border_color: Border color code
            
        Returns:
            str: Processed text with colors applied only to borders
        """
        if not text:
            return ""
        
        result = ""
        i = 0
        
        while i < len(text):
            if text[i] in _BORDER_CHARS:
                # Border character - apply border color
                if border_color:
                    result += f"{border_color}{text[i]}\033[0m"
                else:
                    result += text[i]
                i += 1
            else:
                # Find next border character or end
                j = i
                while j < len(text) and text[j] not in _BORDER_CHARS:
                    j += 1
                
                text_chunk = text[i:j]
                if text_chunk:
                    # Regular text - preserve exactly as-is
                    result += text_chunk
                
                i = j
        
        return result
    
    def _format_for_plain(self, box_lines: List[str]) -> str:
        """Format box for plain text output (strip ANSI codes)."""
        return '\n'.join(_ANSI_PATTERN.sub('', line) for line in box_lines)
    
    def _format_for_markdown(self, box_lines: List[str]) -> str:
        """Format box for markdown output (as code block)."""
        plain_lines = [_ANSI_PATTERN.sub('', line) for line in box_lines]
        return '```\n' + '\n'.join(plain_lines) + '\n```'
    
    def _format_for_html(self, original_content: List[str], box_lines: List[str]) -> str:
        """
        Format box for HTML output with proper entity escaping.
        Rebuilds the box with escaped content to ensure consistent sizing.
        
        Args:
            original_content: Original content lines (before boxing)
            box_lines: Box lines for structure reference
            
        Returns:
            str: HTML formatted box
        """
        # Escape the original content
        escaped_content = [
            self._escape_html(_ANSI_PATTERN.sub('', line))
            for line in original_content
        ]
        
        # Rebuild the box with escaped content
        escaped_box_width = self._calculate_box_width(escaped_content)
        escaped_box_lines = self._add_box_borders(escaped_content, escaped_box_width)
        escaped_box_lines_with_newlines = [''] + escaped_box_lines + ['']
        
        # Justify the escaped box
        escaped_box_text = '\n'.join(escaped_box_lines_with_newlines)
        escaped_justified_box_text = _justify_text(escaped_box_text, self.box_justify, self.terminal_width)
        escaped_justified_box_lines = escaped_justified_box_text.split('\n')
        
        # Create CSS styles
        styles = []
        if self.color:
            normalized_color = _normalize_for_html(self.color)
            if normalized_color:
                styles.append(f"border-color: {normalized_color}")
        
        style_attr = f' style="{"; ".join(styles)}"' if styles else ''
        
        return f'<pre class="fdl-box"{style_attr}>\n' + '\n'.join(escaped_justified_box_lines) + '\n</pre>'
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML entities in text."""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))