# setup/table_generator.py
"""
Table Generator for FDL.

Handles the generation of formatted tables with proper cell sizing,
text wrapping, and multi-format output support.
"""

import re
from typing import List, Dict, Tuple, Optional, Union, Any
from dataclasses import dataclass

# Import dependencies with proper error handling
try:
    from .text_wrapping import _TextWrapper
except ImportError:
    class _TextWrapper:
        def __init__(self):
            self.width = 26
        def wrap_text(self, text):
            return [text]

try:
    from .unicode import _get_unicode_support
except ImportError:
    def _get_unicode_support():
        return True

try:
    from .terminal import _get_terminal
except ImportError:
    def _get_terminal():
        return None

try:
    from ..core.format_state import _FormatState
except ImportError:
    # Fallback for testing/development
    class _FormatState:
        def __init__(self, **kwargs):
            self.text_color = kwargs.get('text_color', None)
            self.background_color = kwargs.get('background_color', None)
            self.bold = kwargs.get('bold', False)
            self.italic = kwargs.get('italic', False)
            self.underline = kwargs.get('underline', False)
            self.strikethrough = kwargs.get('strikethrough', False)
            # Add missing attributes that the real FormatState has
            self.twelve_hour_time = kwargs.get('twelve_hour_time', False)
            self.timezone = kwargs.get('timezone', None)
            self.use_seconds = kwargs.get('use_seconds', False)
            self.use_minutes = kwargs.get('use_minutes', False)
            self.use_hours = kwargs.get('use_hours', False)
            self.decimal_places = kwargs.get('decimal_places', None)
            self.round_seconds = kwargs.get('round_seconds', False)
            self.smart_time = kwargs.get('smart_time', False)
            self.in_box = kwargs.get('in_box', False)
            self.box_style = kwargs.get('box_style', None)
            self.box_title = kwargs.get('box_title', None)
            self.box_color = kwargs.get('box_color', None)
            self.box_background = kwargs.get('box_background', None)
            self.box_content = kwargs.get('box_content', [])
            self.box_width = kwargs.get('box_width', None)
            self.justify = kwargs.get('justify', None)
            self.debug_mode = kwargs.get('debug_mode', False)
            self.active_formats = kwargs.get('active_formats', [])
            self.values = kwargs.get('values', [])
            self.value_index = kwargs.get('value_index', 0)

try:
    from ..core.command_registry import _CommandRegistry, UnknownCommandError
except ImportError:
    class _CommandRegistry:
        def __init__(self):
            pass
        def process_command(self, command, format_state):
            return format_state
    class UnknownCommandError(Exception):
        pass

# Import processors to ensure registration
try:
    from ..processors import commands
except ImportError:
    pass


@dataclass
class _CellInfo:
    """Information about a single table cell."""
    row: int
    col: int
    header: str
    original_content: str
    original_format: Optional[str]
    combined_format: Optional[str]  # Tuple + cell + column + row formatting combined
    wrapped_lines: List[str]
    visual_width: int
    height: int


@dataclass
class _TableDimensions:
    """Calculated dimensions for the entire table."""
    column_widths: List[int]  # Visual width for each column
    row_heights: List[int]    # Height for each row (including header)
    total_width: int
    total_height: int


class _TableGenerator:
    """
    Generator for creating formatted tables with proper cell sizing and borders.
    
    Features:
    - Smart cell sizing with 30 character limit per cell
    - Text wrapping at 26 characters (with 2 chars padding)
    - Visual width calculation using wcwidth
    - Multi-format output (terminal, plain, markdown, HTML)
    - Format state integration for each cell
    - Visual indicators for missing data: rows with fewer columns than headers
      will have missing vertical borders, clearly marking incomplete data
    """
    
    # Box drawing characters for different styles
    BOX_STYLES = {
        'rounded': {
            'top_left': '╭', 'top_right': '╮', 'bottom_left': '╰', 'bottom_right': '╯',
            'horizontal': '─', 'vertical': '│',
            'cross': '┼', 'top_tee': '┬', 'bottom_tee': '┴', 'left_tee': '├', 'right_tee': '┤'
        },
        'square': {
            'top_left': '┌', 'top_right': '┐', 'bottom_left': '└', 'bottom_right': '┘',
            'horizontal': '─', 'vertical': '│',
            'cross': '┼', 'top_tee': '┬', 'bottom_tee': '┴', 'left_tee': '├', 'right_tee': '┤'
        },
        'double': {
            'top_left': '╔', 'top_right': '╗', 'bottom_left': '╚', 'bottom_right': '╝',
            'horizontal': '═', 'vertical': '║',
            'cross': '╬', 'top_tee': '╦', 'bottom_tee': '╩', 'left_tee': '╠', 'right_tee': '╣'
        },
        'simple': {
            'top_left': '+', 'top_right': '+', 'bottom_left': '+', 'bottom_right': '+',
            'horizontal': '-', 'vertical': '|',
            'cross': '+', 'top_tee': '+', 'bottom_tee': '+', 'left_tee': '+', 'right_tee': '+'
        }
    }
    
    def __init__(self):
        """Initialize the table generator."""
        self._text_wrapper = _TextWrapper()
        self._unicode_support = _get_unicode_support()
        self._terminal = _get_terminal()
        self._command_registry = _CommandRegistry()
        
        # Cell sizing constants
        self.MAX_CELL_WIDTH = 30  # Maximum width from left edge to right edge
        self.PADDING = 1          # Space padding on each side
        self.USABLE_WIDTH = self.MAX_CELL_WIDTH - (2 * self.PADDING)  # 26 characters
    
    def generate_table(self, headers: List[str], data: List[List[Union[str, Tuple[str, str]]]], 
                      style: str = "rounded", start_row: int = 1, end_row: Optional[int] = None,
                      header_format: Optional[_FormatState] = None,
                      column_formats: Dict[str, _FormatState] = None,
                      row_formats: Dict[int, _FormatState] = None,
                      cell_formats: Dict[Tuple[str, int], _FormatState] = None) -> Dict[str, str]:
        """
        Generate a formatted table in multiple output formats.
        
        Args:
            headers: List of column headers
            data: List of data rows
            style: Box style ('rounded', 'square', 'double', 'simple')
            start_row: Starting row number (1-based)
            end_row: Ending row number (1-based), None for all
            header_format: Formatting for headers
            column_formats: Formatting for columns
            row_formats: Formatting for rows
            cell_formats: Formatting for specific cells
            
        Returns:
            Dict with keys: 'terminal', 'plain', 'markdown', 'html'
        """
        if not headers:
            return self._generate_empty_table()
        
        # Set defaults
        column_formats = column_formats or {}
        row_formats = row_formats or {}
        cell_formats = cell_formats or {}
        
        # Determine which rows to display
        if end_row is None:
            end_row = len(data)
        display_data = data[start_row-1:end_row] if data else []
        
        # Create pseudo matrix with cell information
        pseudo_matrix = self._create_pseudo_matrix(
            headers, display_data, start_row,
            header_format, column_formats, row_formats, cell_formats
        )
        
        # Calculate table dimensions
        dimensions = self._calculate_dimensions(pseudo_matrix, headers)
        
        # Generate different output formats
        return {
            'terminal': self._generate_terminal_output(pseudo_matrix, dimensions, style, headers),
            'plain': self._generate_plain_output(pseudo_matrix, dimensions, headers),
            'markdown': self._generate_markdown_output(pseudo_matrix, headers),
            'html': self._generate_html_output(pseudo_matrix, headers)
        }
    
    def _create_pseudo_matrix(self, headers: List[str], data: List[List[Union[str, Tuple[str, str]]]], 
                             start_row: int, header_format: Optional[_FormatState],
                             column_formats: Dict[str, _FormatState], row_formats: Dict[int, _FormatState],
                             cell_formats: Dict[Tuple[str, int], _FormatState]) -> List[List[_CellInfo]]:
        """Create a pseudo matrix with detailed cell information."""
        matrix = []
        
        # Process header row
        header_row = []
        for col_idx, header in enumerate(headers):
            cell_info = self._process_cell(
                content=header,
                row=0,  # Header row
                col=col_idx,
                header=header,
                header_format=header_format,
                column_formats=column_formats,
                row_formats=row_formats,
                cell_formats=cell_formats,
                actual_row_num=0
            )
            header_row.append(cell_info)
        matrix.append(header_row)
        
        # Process data rows
        for data_row_idx, row_data in enumerate(data):
            actual_row_num = start_row + data_row_idx
            matrix_row = []
            
            for col_idx, cell_data in enumerate(row_data):
                if col_idx < len(headers):  # Only process cells that have headers
                    cell_info = self._process_cell(
                        content=cell_data,
                        row=data_row_idx + 1,  # Matrix row (1-based for data)
                        col=col_idx,
                        header=headers[col_idx],
                        header_format=None,  # Not a header
                        column_formats=column_formats,
                        row_formats=row_formats,
                        cell_formats=cell_formats,
                        actual_row_num=actual_row_num
                    )
                    matrix_row.append(cell_info)
            
            matrix.append(matrix_row)
        
        return matrix
    
    def _process_cell(self, content: Union[str, Tuple[str, str]], row: int, col: int, header: str,
                     header_format: Optional[_FormatState], column_formats: Dict[str, _FormatState],
                     row_formats: Dict[int, _FormatState], cell_formats: Dict[Tuple[str, int], _FormatState],
                     actual_row_num: int) -> _CellInfo:
        """Process a single cell and create cell info."""
        # Extract content and tuple formatting
        if isinstance(content, tuple):
            original_content, tuple_format = content
        else:
            original_content = str(content)
            tuple_format = None
        
        # Combine formatting (priority: tuple > cell > column > row > header)
        combined_format_state = self._combine_format_states(
            tuple_format=tuple_format,
            cell_format=cell_formats.get((header, actual_row_num)),
            column_format=column_formats.get(header),
            row_format=row_formats.get(actual_row_num),
            header_format=header_format if row == 0 else None
        )
        
        # Apply formatting to content
        formatted_content = self._apply_format_state(original_content, combined_format_state)
        
        # Wrap text to fit cell width
        wrapped_lines = self._wrap_cell_content(formatted_content)
        
        # Calculate visual dimensions
        visual_width = min(self.MAX_CELL_WIDTH, max(
            self._calculate_visual_width(line) + (2 * self.PADDING) 
            for line in wrapped_lines
        ))
        height = len(wrapped_lines)
        
        return _CellInfo(
            row=row,
            col=col,
            header=header,
            original_content=original_content,
            original_format=tuple_format,
            combined_format=str(combined_format_state) if combined_format_state else None,
            wrapped_lines=wrapped_lines,
            visual_width=visual_width,
            height=height
        )
    
    def _combine_format_states(self, tuple_format: Optional[str], cell_format: Optional[_FormatState],
                              column_format: Optional[_FormatState], row_format: Optional[_FormatState],
                              header_format: Optional[_FormatState]) -> Optional[_FormatState]:
        """
        Combine format states with proper priority system.
        
        Priority order: tuple > cell > column > row > header
        Higher priority formatting overrides lower priority formatting.
        """
        # Start with a base format state
        final_format = _FormatState()
        
        # Apply formatting in reverse priority order (lowest to highest)
        # This way higher priority will override lower priority
        
        # 1. Header format (lowest priority)
        if header_format:
            final_format = self._merge_format_states(final_format, header_format)
        
        # 2. Row format
        if row_format:
            final_format = self._merge_format_states(final_format, row_format)
        
        # 3. Column format
        if column_format:
            final_format = self._merge_format_states(final_format, column_format)
        
        # 4. Cell format
        if cell_format:
            final_format = self._merge_format_states(final_format, cell_format)
        
        # 5. Tuple format (highest priority)
        if tuple_format:
            tuple_format_state = self._process_tuple_format(tuple_format)
            if tuple_format_state:
                final_format = self._merge_format_states(final_format, tuple_format_state)
        
        # Return None if no formatting was applied
        if self._is_empty_format_state(final_format):
            return None
        
        return final_format
    
    def _merge_format_states(self, base: _FormatState, override: _FormatState) -> _FormatState:
        """
        Merge two format states, with override taking precedence.
        
        Args:
            base: Base format state
            override: Override format state (takes precedence)
            
        Returns:
            New format state with merged formatting
        """
        # Create a copy of the base format state
        merged = _FormatState(
            text_color=base.text_color,
            background_color=base.background_color,
            bold=base.bold,
            italic=base.italic,
            underline=base.underline,
            strikethrough=base.strikethrough,
            twelve_hour_time=base.twelve_hour_time,
            timezone=base.timezone,
            use_seconds=base.use_seconds,
            use_minutes=base.use_minutes,
            use_hours=base.use_hours,
            decimal_places=base.decimal_places,
            round_seconds=base.round_seconds,
            smart_time=base.smart_time,
            in_box=base.in_box,
            box_style=base.box_style,
            box_title=base.box_title,
            box_color=base.box_color,
            box_background=base.box_background,
            box_content=base.box_content.copy(),
            box_width=base.box_width,
            justify=base.justify,
            debug_mode=base.debug_mode,
            active_formats=base.active_formats.copy(),
            values=base.values,
            value_index=base.value_index
        )
        
        # Apply overrides (only if they're set in the override state)
        if override.text_color is not None:
            merged.text_color = override.text_color
        if override.background_color is not None:
            merged.background_color = override.background_color
        if override.bold:
            merged.bold = override.bold
        if override.italic:
            merged.italic = override.italic
        if override.underline:
            merged.underline = override.underline
        if override.strikethrough:
            merged.strikethrough = override.strikethrough
        if override.justify is not None:
            merged.justify = override.justify
        
        return merged
    
    def _process_tuple_format(self, tuple_format: str) -> Optional[_FormatState]:
        """Process tuple format string into format state."""
        if not tuple_format.strip():
            return None
        
        # Create a new format state for processing
        format_state = _FormatState()
        
        # Remove leading/trailing whitespace and angle brackets
        clean_format = tuple_format.strip()
        if clean_format.startswith('</') and clean_format.endswith('>'):
            clean_format = clean_format[2:-1]  # Remove </ and >
        elif clean_format.startswith('<') and clean_format.endswith('>'):
            clean_format = clean_format[1:-1]   # Remove < and >
        
        # Split commands by comma and process each
        commands = [cmd.strip() for cmd in clean_format.split(',')]
        
        for command in commands:
            if command:  # Skip empty commands
                try:
                    format_state = self._command_registry.process_command(command, format_state)
                except (UnknownCommandError, Exception):
                    # If command processing fails, return None
                    return None
        
        return format_state
    
    def _is_empty_format_state(self, format_state: _FormatState) -> bool:
        """Check if format state has any formatting applied."""
        return (format_state.text_color is None and
                format_state.background_color is None and
                not format_state.bold and
                not format_state.italic and
                not format_state.underline and
                not format_state.strikethrough)
    
    def _apply_format_state(self, content: str, format_state: Optional[_FormatState]) -> str:
        """Apply format state to content, generating ANSI codes."""
        if not format_state:
            return content
        
        # Build ANSI codes from format state
        ansi_codes = []
        
        # Text color
        if format_state.text_color:
            color_code = self._get_color_code(format_state.text_color)
            if color_code:
                ansi_codes.append(color_code)
        
        # Background color
        if format_state.background_color:
            bg_color_code = self._get_background_color_code(format_state.background_color)
            if bg_color_code:
                ansi_codes.append(bg_color_code)
        
        # Text styles
        if format_state.bold:
            ansi_codes.append('1')
        if format_state.italic:
            ansi_codes.append('3')
        if format_state.underline:
            ansi_codes.append('4')
        if format_state.strikethrough:
            ansi_codes.append('9')
        
        # Apply formatting
        if ansi_codes:
            ansi_start = f"\x1b[{';'.join(ansi_codes)}m"
            ansi_end = "\x1b[0m"
            return f"{ansi_start}{content}{ansi_end}"
        
        return content
    
    def _get_color_code(self, color: str) -> Optional[str]:
        """Get ANSI color code for text color."""
        color_map = {
            'black': '30', 'red': '31', 'green': '32', 'yellow': '33',
            'blue': '34', 'magenta': '35', 'cyan': '36', 'white': '37',
            'bright_black': '90', 'bright_red': '91', 'bright_green': '92',
            'bright_yellow': '93', 'bright_blue': '94', 'bright_magenta': '95',
            'bright_cyan': '96', 'bright_white': '97'
        }
        return color_map.get(color)
    
    def _get_background_color_code(self, color: str) -> Optional[str]:
        """Get ANSI background color code."""
        bg_color_map = {
            'black': '40', 'red': '41', 'green': '42', 'yellow': '43',
            'blue': '44', 'magenta': '45', 'cyan': '46', 'white': '47',
            'bright_black': '100', 'bright_red': '101', 'bright_green': '102',
            'bright_yellow': '103', 'bright_blue': '104', 'bright_magenta': '105',
            'bright_cyan': '106', 'bright_white': '107'
        }
        return bg_color_map.get(color)
    
    def _wrap_cell_content(self, content: str) -> List[str]:
        """Wrap content to fit within cell width."""
        # Configure text wrapper for cell width
        self._text_wrapper.width = self.USABLE_WIDTH
        return self._text_wrapper.wrap_text(content)
    
    def _calculate_visual_width(self, text: str) -> int:
        """Calculate visual width of text using wcwidth."""
        # Remove ANSI codes for width calculation
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        
        try:
            import wcwidth
            width = wcwidth.wcswidth(clean_text)
            if width is not None:
                return width
        except ImportError:
            pass
        
        # Fallback: assume each character is width 1
        return len(clean_text)
    
    def _calculate_dimensions(self, matrix: List[List[_CellInfo]], headers: List[str]) -> _TableDimensions:
        """Calculate optimal dimensions for the table."""
        if not matrix or not matrix[0]:
            return _TableDimensions([], [], 0, 0)
        
        num_cols = len(headers)
        num_rows = len(matrix)
        
        # Calculate column widths (max width in each column)
        column_widths = []
        for col_idx in range(num_cols):
            max_width = 0
            for row in matrix:
                if col_idx < len(row):
                    max_width = max(max_width, row[col_idx].visual_width)
            column_widths.append(min(self.MAX_CELL_WIDTH, max_width))
        
        # Calculate row heights (max height in each row)
        row_heights = []
        for row in matrix:
            max_height = max(cell.height for cell in row) if row else 1
            row_heights.append(max_height)
        
        # Calculate total dimensions
        total_width = sum(column_widths) + (num_cols + 1)  # +1 for borders
        total_height = sum(row_heights) + num_rows + 1     # +1 for borders
        
        return _TableDimensions(column_widths, row_heights, total_width, total_height)
    
    def _generate_terminal_output(self, matrix: List[List[_CellInfo]], 
                                 dimensions: _TableDimensions, style: str,
                                 headers: List[str]) -> str:
        """Generate terminal output with ANSI formatting and box borders."""
        if not matrix:
            return "[EMPTY_TABLE]"
        
        box_chars = self.BOX_STYLES.get(style, self.BOX_STYLES['simple'])
        lines = []
        
        # Top border
        lines.append(self._generate_border_line(dimensions.column_widths, box_chars, 'top'))
        
        # Process each row
        for row_idx, row in enumerate(matrix):
            # Generate content lines for this row
            row_height = dimensions.row_heights[row_idx]
            
            for line_idx in range(row_height):
                line_parts = [box_chars['vertical']]
                
                for col_idx, cell in enumerate(row):
                    col_width = dimensions.column_widths[col_idx]
                    
                    # Get the line content for this cell
                    if line_idx < len(cell.wrapped_lines):
                        content = cell.wrapped_lines[line_idx]
                    else:
                        content = ""  # Empty line for cells shorter than row height
                    
                    # Pad content to column width
                    padded_content = self._pad_content(content, col_width)
                    line_parts.append(f" {padded_content} ")
                    line_parts.append(box_chars['vertical'])
                
                lines.append("".join(line_parts))
            
            # Add separator line (except after last row)
            if row_idx < len(matrix) - 1:
                if row_idx == 0:  # After header
                    lines.append(self._generate_border_line(dimensions.column_widths, box_chars, 'header_sep'))
                else:  # Between data rows
                    lines.append(self._generate_border_line(dimensions.column_widths, box_chars, 'middle'))
        
        # Bottom border
        lines.append(self._generate_border_line(dimensions.column_widths, box_chars, 'bottom'))
        
        return "\n".join(lines)
    
    def _generate_border_line(self, column_widths: List[int], box_chars: Dict[str, str], 
                             position: str) -> str:
        """Generate a border line for the table."""
        if position == 'top':
            left, right, middle = box_chars['top_left'], box_chars['top_right'], box_chars['top_tee']
        elif position == 'bottom':
            left, right, middle = box_chars['bottom_left'], box_chars['bottom_right'], box_chars['bottom_tee']
        elif position == 'header_sep':
            left, right, middle = box_chars['left_tee'], box_chars['right_tee'], box_chars['cross']
        else:  # middle
            left, right, middle = box_chars['left_tee'], box_chars['right_tee'], box_chars['cross']
        
        parts = [left]
        for i, width in enumerate(column_widths):
            parts.append(box_chars['horizontal'] * (width + 2))  # +2 for padding
            if i < len(column_widths) - 1:
                parts.append(middle)
        parts.append(right)
        
        return "".join(parts)
    
    def _pad_content(self, content: str, target_width: int) -> str:
        """Pad content to target width, accounting for ANSI codes."""
        visual_width = self._calculate_visual_width(content)
        padding_needed = max(0, target_width - visual_width)
        return content + (" " * padding_needed)
    
    def _generate_plain_output(self, matrix: List[List[_CellInfo]], 
                              dimensions: _TableDimensions, headers: List[str]) -> str:
        """Generate plain text output without formatting."""
        if not matrix:
            return "[EMPTY_TABLE]"
        
        lines = []
        
        # Process each row
        for row in matrix:
            row_height = max(cell.height for cell in row) if row else 1
            
            for line_idx in range(row_height):
                line_parts = []
                
                for col_idx, cell in enumerate(row):
                    col_width = dimensions.column_widths[col_idx]
                    
                    # Get clean content (remove ANSI codes)
                    if line_idx < len(cell.wrapped_lines):
                        content = re.sub(r'\x1b\[[0-9;]*m', '', cell.wrapped_lines[line_idx])
                    else:
                        content = ""
                    
                    # Pad content
                    padded_content = content.ljust(col_width)
                    line_parts.append(f" {padded_content} ")
                    
                    if col_idx < len(row) - 1:
                        line_parts.append("|")
                
                lines.append("".join(line_parts))
            
            # Add separator after header
            if row == matrix[0] and len(matrix) > 1:
                separator_parts = []
                for col_idx in range(len(row)):
                    col_width = dimensions.column_widths[col_idx]
                    separator_parts.append("-" * (col_width + 2))
                    if col_idx < len(row) - 1:
                        separator_parts.append("+")
                lines.append("".join(separator_parts))
        
        return "\n".join(lines)
    
    def _generate_markdown_output(self, matrix: List[List[_CellInfo]], headers: List[str]) -> str:
        """Generate markdown table output with proper alignment."""
        if not matrix:
            return "[EMPTY_TABLE]"
        
        lines = []
        
        # Calculate dimensions for proper alignment
        dimensions = self._calculate_dimensions(matrix, headers)
        
        # Header row
        if matrix:
            header_cells = []
            for col_idx, cell in enumerate(matrix[0]):
                col_width = dimensions.column_widths[col_idx]
                # Clean content for markdown
                content = re.sub(r'\x1b\[[0-9;]*m', '', cell.original_content)
                # Pad content to column width
                padded_content = content.ljust(col_width)
                header_cells.append(padded_content)
            lines.append(" " + " | ".join(header_cells) + " ")
            
            # Separator row with proper column widths
            separator_parts = []
            for col_idx in range(len(dimensions.column_widths)):
                col_width = dimensions.column_widths[col_idx]
                separator_parts.append("-" * (col_width + 2))
                if col_idx < len(dimensions.column_widths) - 1:
                    separator_parts.append("+")
            lines.append("".join(separator_parts))
            
            # Data rows
            for row in matrix[1:]:
                data_cells = []
                for col_idx, cell in enumerate(row):
                    col_width = dimensions.column_widths[col_idx]
                    # Clean content for markdown
                    content = re.sub(r'\x1b\[[0-9;]*m', '', cell.original_content)
                    # Pad content to column width
                    padded_content = content.ljust(col_width)
                    data_cells.append(padded_content)
                lines.append(" " + " | ".join(data_cells) + " ")
        
        return "\n".join(lines)
    
    def _generate_html_output(self, matrix: List[List[_CellInfo]], headers: List[str]) -> str:
        """Generate HTML table output."""
        if not matrix:
            return "<p>[EMPTY_TABLE]</p>"
        
        lines = ["<table>"]
        
        # Header row
        if matrix:
            lines.append("  <thead>")
            lines.append("    <tr>")
            for cell in matrix[0]:
                # Clean content for HTML
                content = re.sub(r'\x1b\[[0-9;]*m', '', cell.original_content)
                content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lines.append(f"      <th>{content}</th>")
            lines.append("    </tr>")
            lines.append("  </thead>")
            
            # Data rows
            if len(matrix) > 1:
                lines.append("  <tbody>")
                for row in matrix[1:]:
                    lines.append("    <tr>")
                    for cell in row:
                        # Clean content for HTML
                        content = re.sub(r'\x1b\[[0-9;]*m', '', cell.original_content)
                        content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                        lines.append(f"      <td>{content}</td>")
                    lines.append("    </tr>")
                lines.append("  </tbody>")
        
        lines.append("</table>")
        return "\n".join(lines)
    
    def _generate_empty_table(self) -> Dict[str, str]:
        """Generate output for an empty table."""
        return {
            'terminal': '[EMPTY_TABLE]',
            'plain': '[EMPTY_TABLE]',
            'markdown': '[EMPTY_TABLE]',
            'html': '<p>[EMPTY_TABLE]</p>'
        }