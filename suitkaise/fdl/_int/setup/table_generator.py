# setup/table_generator.py
"""
Table Generator for FDL.

Handles the generation of formatted tables with proper cell sizing,
text wrapping, and multi-format output support.
"""

import re
from typing import List, Dict, Tuple, Optional, Union, Any
from dataclasses import dataclass
from .text_wrapping import _TextWrapper
from .unicode import _get_unicode_support
from .terminal import _get_terminal


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
        
        # Cell sizing constants
        self.MAX_CELL_WIDTH = 30  # Maximum width from left edge to right edge
        self.PADDING = 1          # Space padding on each side
        self.USABLE_WIDTH = self.MAX_CELL_WIDTH - (2 * self.PADDING)  # 26 characters
    
    def generate_table(self, headers: List[str], data: List[List[Union[str, Tuple[str, str]]]], 
                      style: str = "rounded", start_row: int = 1, end_row: Optional[int] = None,
                      header_format: Optional[str] = None,
                      column_formats: Dict[str, str] = None,
                      row_formats: Dict[int, str] = None,
                      cell_formats: Dict[Tuple[str, int], str] = None) -> Dict[str, str]:
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
                             start_row: int, header_format: Optional[str],
                             column_formats: Dict[str, str], row_formats: Dict[int, str],
                             cell_formats: Dict[Tuple[str, int], str]) -> List[List[_CellInfo]]:
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
                     header_format: Optional[str], column_formats: Dict[str, str],
                     row_formats: Dict[int, str], cell_formats: Dict[Tuple[str, int], str],
                     actual_row_num: int) -> _CellInfo:
        """Process a single cell and create cell info."""
        # Extract content and tuple formatting
        if isinstance(content, tuple):
            original_content, tuple_format = content
        else:
            original_content = str(content)
            tuple_format = None
        
        # Combine formatting (priority: tuple > cell > column > row)
        combined_format = self._combine_formatting(
            tuple_format=tuple_format,
            cell_format=cell_formats.get((header, actual_row_num)),
            column_format=column_formats.get(header),
            row_format=row_formats.get(actual_row_num),
            header_format=header_format if row == 0 else None
        )
        
        # Apply formatting to content
        formatted_content = self._apply_formatting(original_content, combined_format)
        
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
            combined_format=combined_format,
            wrapped_lines=wrapped_lines,
            visual_width=visual_width,
            height=height
        )
    
    def _combine_formatting(self, tuple_format: Optional[str], cell_format: Optional[str],
                           column_format: Optional[str], row_format: Optional[str],
                           header_format: Optional[str]) -> Optional[str]:
        """Combine formatting from different sources with proper priority."""
        # Priority: tuple > cell > column > row > header
        return (tuple_format or cell_format or column_format or 
                row_format or header_format)
    
    def _apply_formatting(self, content: str, format_string: Optional[str]) -> str:
        """Apply FDL formatting to content."""
        if not format_string:
            return content
        
        # For now, return content with format applied
        # This would integrate with the FDL processor in full implementation
        return content  # TODO: Integrate with FDL string processing
    
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
        """Generate markdown table output."""
        if not matrix:
            return "[EMPTY_TABLE]"
        
        lines = []
        
        # Header row
        if matrix:
            header_cells = []
            for cell in matrix[0]:
                # Clean content for markdown
                content = re.sub(r'\x1b\[[0-9;]*m', '', cell.original_content)
                header_cells.append(content)
            lines.append("| " + " | ".join(header_cells) + " |")
            
            # Separator row
            separator = "| " + " | ".join(["---"] * len(header_cells)) + " |"
            lines.append(separator)
            
            # Data rows
            for row in matrix[1:]:
                data_cells = []
                for cell in row:
                    # Clean content for markdown
                    content = re.sub(r'\x1b\[[0-9;]*m', '', cell.original_content)
                    data_cells.append(content)
                lines.append("| " + " | ".join(data_cells) + " |")
        
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