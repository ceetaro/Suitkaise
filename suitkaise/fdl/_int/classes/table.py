# classes/table.py
"""
Internal Table Class for FDL.

Provides table creation, data management, and display functionality with
API-driven data population and tuple-based formatting.
"""

import re
from typing import List, Tuple, Union, Optional, Dict, Any
from copy import deepcopy
from ..setup.table_generator import _TableGenerator
from ..setup.text_wrapping import _TextWrapper
from ..setup.unicode import _get_unicode_support
from ..setup.terminal import _get_terminal
from ..core.format_state import _FormatState
from ..core.command_registry import _CommandRegistry, UnknownCommandError
# Import processors to ensure registration
from ..processors import commands


class _Table:
    """
    Internal Table class for creating and displaying formatted tables.
    
    Features:
    - API-driven data management (no direct data manipulation)
    - Headers-first approach (structure before data)
    - Tuple-based formatting: (content, format_string)
    - Content-based matching and updates
    - Multi-format output (terminal, plain, markdown, HTML)
    """
    
    def __init__(self, style: str = "rounded", max_columns: Optional[int] = None, 
                 max_rows: Optional[int] = None):
        """
        Initialize a new table.
        
        Args:
            style: Box style for table borders ("rounded", "square", "double", etc.)
            max_columns: Maximum number of columns (None for unlimited)
            max_rows: Maximum number of rows (None for unlimited)
        """
        self.style = style
        self.max_columns = max_columns
        self.max_rows = max_rows
        
        # Table structure
        self._headers: List[str] = []
        self._data: List[List[Union[str, Tuple[str, str]]]] = []
        
        # Formatting (using format states)
        self._header_format: Optional[_FormatState] = None
        self._column_formats: Dict[str, _FormatState] = {}
        self._row_formats: Dict[int, _FormatState] = {}  # 1-based row numbers
        self._cell_formats: Dict[Tuple[str, int], _FormatState] = {}  # (header, row)
        
        # Command registry for processing format strings
        self._command_registry = _CommandRegistry()
        
        # Warning tracking
        self._format_warnings_shown = False
        
        # Setup components
        self._table_generator = _TableGenerator()
        self._text_wrapper = _TextWrapper()
        self._unicode_support = _get_unicode_support()
        self._terminal = _get_terminal()
        
        # Memory management
        self._released = False
    
    # ==================== PROPERTIES ====================
    
    @property
    def row_count(self) -> int:
        """Get the number of data rows (excludes headers)."""
        return len(self._data)
    
    @property
    def column_count(self) -> int:
        """Get the number of columns (same as header count)."""
        return len(self._headers)
    
    @property
    def header_count(self) -> int:
        """Alias for column_count."""
        return self.column_count
    
    # ==================== HEADER MANAGEMENT ====================
    
    def add_header(self, header: str) -> None:
        """
        Add a single header to the table.
        
        Args:
            header: Header name
            
        Raises:
            ValueError: If max_columns would be exceeded
        """
        self._check_released()
        
        if self.max_columns and len(self._headers) >= self.max_columns:
            raise ValueError(f"Cannot add header: max_columns ({self.max_columns}) would be exceeded")
        
        if header in self._headers:
            raise ValueError(f"Header '{header}' already exists")
        
        self._headers.append(header)
        
        # Add empty cell to all existing rows
        for row in self._data:
            row.append("")
    
    def add_headers(self, headers: List[str]) -> None:
        """
        Add multiple headers to the table.
        
        Args:
            headers: List of header names
        """
        for header in headers:
            self.add_header(header)
    
    def remove_header(self, header: str) -> None:
        """
        Remove a header and its entire column of data.
        
        Args:
            header: Header name to remove
            
        Raises:
            ValueError: If header doesn't exist
        """
        if header not in self._headers:
            raise ValueError(f"Header '{header}' does not exist")
        
        header_index = self._headers.index(header)
        
        # Remove header
        self._headers.remove(header)
        
        # Remove column data from all rows
        for row in self._data:
            if header_index < len(row):
                row.pop(header_index)
        
        # Clean up formatting for this header
        self._column_formats.pop(header, None)
        
        # Clean up cell formatting for this header
        keys_to_remove = [key for key in self._cell_formats.keys() if key[0] == header]
        for key in keys_to_remove:
            del self._cell_formats[key]
    
    def get_headers(self) -> List[str]:
        """Get a copy of the current headers list."""
        return self._headers.copy()
    
    # ==================== DATA MANAGEMENT ====================
    
    def add_row_data(self, data: Union[List[Union[str, Tuple[str, str]]], 
                                     List[List[Union[str, Tuple[str, str]]]]]) -> None:
        """
        Add row data to the table.
        
        Args:
            data: Single row or list of rows to add
            
        Raises:
            ValueError: If no headers defined or row length mismatch
        """
        self._check_released()
        
        if not self._headers:
            raise ValueError("Must define headers before adding data")
        
        # Handle single row vs multiple rows
        if isinstance(data[0], list):
            # Multiple rows
            rows_to_add = data
        else:
            # Single row
            rows_to_add = [data]
        
        for row in rows_to_add:
            if self.max_rows and len(self._data) >= self.max_rows:
                raise ValueError(f"Cannot add row: max_rows ({self.max_rows}) would be exceeded")
            
            if len(row) != len(self._headers):
                raise ValueError(f"Row length ({len(row)}) must match header count ({len(self._headers)})")
            
            self._data.append(row.copy())
    
    def remove_row_data(self, data: Union[List[Union[str, Tuple[str, str]]], 
                                        List[List[Union[str, Tuple[str, str]]]]]) -> None:
        """
        Remove row data by content matching (matches plain strings only).
        
        Args:
            data: Single row or list of rows to remove
        """
        # Handle single row vs multiple rows
        if isinstance(data[0], list):
            rows_to_remove = data
        else:
            rows_to_remove = [data]
        
        for target_row in rows_to_remove:
            # Convert target row to plain strings for matching
            target_strings = []
            for cell in target_row:
                if isinstance(cell, tuple):
                    target_strings.append(cell[0])  # Just the content
                else:
                    target_strings.append(str(cell))
            
            # Find matching row in data
            for i, existing_row in enumerate(self._data):
                existing_strings = []
                for cell in existing_row:
                    if isinstance(cell, tuple):
                        existing_strings.append(cell[0])
                    else:
                        existing_strings.append(str(cell))
                
                if existing_strings == target_strings:
                    self._data.pop(i)
                    break
    
    # ==================== CELL ACCESS ====================
    
    def set_cell(self, header: str, row: int, value: Union[str, Tuple[str, str]]) -> None:
        """
        Set a cell value by header and row number.
        
        Args:
            header: Header name
            row: Row number (1-based)
            value: Cell value (string or tuple)
            
        Raises:
            ValueError: If header doesn't exist or row is out of range
        """
        if header not in self._headers:
            raise ValueError(f"Header '{header}' does not exist")
        
        if row < 1 or row > len(self._data):
            raise ValueError(f"Row {row} is out of range (1-{len(self._data)})")
        
        header_index = self._headers.index(header)
        self._data[row - 1][header_index] = value
    
    def get_cell(self, header: str, row: int) -> Union[str, Tuple[str, str]]:
        """
        Get a cell value by header and row number.
        
        Args:
            header: Header name
            row: Row number (1-based)
            
        Returns:
            Cell value
        """
        if header not in self._headers:
            raise ValueError(f"Header '{header}' does not exist")
        
        if row < 1 or row > len(self._data):
            raise ValueError(f"Row {row} is out of range (1-{len(self._data)})")
        
        header_index = self._headers.index(header)
        return self._data[row - 1][header_index]
    
    def update_cell(self, current_cell_content: str, 
                   new_cell_content: Union[str, Tuple[str, str]]) -> bool:
        """
        Update cell by finding current content (matches plain strings only).
        
        Args:
            current_cell_content: Content to find
            new_cell_content: New content to set
            
        Returns:
            bool: True if cell was found and updated, False otherwise
        """
        for row_idx, row in enumerate(self._data):
            for col_idx, cell in enumerate(row):
                cell_content = cell[0] if isinstance(cell, tuple) else str(cell)
                
                if cell_content == current_cell_content:
                    self._data[row_idx][col_idx] = new_cell_content
                    return True
        
        return False
    
    def get_row(self, row: int) -> List[Union[str, Tuple[str, str]]]:
        """
        Get an entire row by row number.
        
        Args:
            row: Row number (1-based)
            
        Returns:
            List of cell values
        """
        if row < 1 or row > len(self._data):
            raise ValueError(f"Row {row} is out of range (1-{len(self._data)})")
        
        return self._data[row - 1].copy()
    
    def get_column(self, header: str) -> List[Union[str, Tuple[str, str]]]:
        """
        Get an entire column by header name.
        
        Args:
            header: Header name
            
        Returns:
            List of cell values
        """
        if header not in self._headers:
            raise ValueError(f"Header '{header}' does not exist")
        
        header_index = self._headers.index(header)
        return [row[header_index] for row in self._data]
    
    # ==================== FORMATTING ====================
    
    def format_headers(self, format_string: str) -> None:
        """
        Set formatting for all headers.
        
        Args:
            format_string: FDL format string like "</bold, underline>"
            
        Raises:
            ValueError: If format string is invalid
        """
        self._check_released()
        self._header_format = self._process_format_string(format_string)
    
    def format_column(self, header: str, format_string: str) -> None:
        """
        Set formatting for an entire column.
        
        Args:
            header: Column header name
            format_string: FDL format string like "</red, italic>"
            
        Raises:
            ValueError: If header doesn't exist or format string is invalid
        """
        self._check_released()
        if header not in self._headers:
            raise ValueError(f"Header '{header}' does not exist")
        self._column_formats[header] = self._process_format_string(format_string)
    
    def format_row(self, row: int, format_string: str) -> None:
        """
        Set formatting for an entire row.
        
        Args:
            row: Row number (1-based)
            format_string: FDL format string like "</yellow>"
            
        Raises:
            ValueError: If row is out of range or format string is invalid
        """
        self._check_released()
        if row < 1 or row > len(self._data):
            raise ValueError(f"Row {row} is out of range (1-{len(self._data)})")
        self._row_formats[row] = self._process_format_string(format_string)
    
    def format_cell(self, header: str, row: int, format_string: str) -> None:
        """
        Set formatting for a specific cell.
        
        Args:
            header: Column header name
            row: Row number (1-based)
            format_string: FDL format string like "</bold, green>"
            
        Raises:
            ValueError: If header/row doesn't exist or format string is invalid
        """
        self._check_released()
        if header not in self._headers:
            raise ValueError(f"Header '{header}' does not exist")
        if row < 1 or row > len(self._data):
            raise ValueError(f"Row {row} is out of range (1-{len(self._data)})")
        self._cell_formats[(header, row)] = self._process_format_string(format_string)
    
    # Reset formatting methods
    def reset_formatting(self) -> None:
        """Reset all formatting."""
        self._header_format = None
        self._column_formats.clear()
        self._row_formats.clear()
        self._cell_formats.clear()
    
    def reset_header_formatting(self) -> None:
        """Reset header formatting."""
        self._header_format = None
    
    def reset_column_formatting(self, header: str) -> None:
        """Reset formatting for a column."""
        self._column_formats.pop(header, None)
    
    def reset_row_formatting(self, row: int) -> None:
        """Reset formatting for a row."""
        self._row_formats.pop(row, None)
    
    def reset_cell_formatting(self, header: str, row: int) -> None:
        """Reset formatting for a specific cell."""
        self._cell_formats.pop((header, row), None)
    
    # ==================== UTILITY METHODS ====================
    
    def copy(self) -> '_Table':
        """Create a deep copy of this table."""
        new_table = _Table(style=self.style, max_columns=self.max_columns, max_rows=self.max_rows)
        new_table._headers = self._headers.copy()
        new_table._data = deepcopy(self._data)
        new_table._header_format = self._header_format
        new_table._column_formats = self._column_formats.copy()
        new_table._row_formats = self._row_formats.copy()
        new_table._cell_formats = self._cell_formats.copy()
        return new_table
    
    def find_rows(self, header: str, content: str) -> List[int]:
        """
        Find rows where a specific column contains specific content.
        
        Args:
            header: Header name to search in
            content: Content to find (matches plain strings)
            
        Returns:
            List of row numbers (1-based) that match
        """
        if header not in self._headers:
            raise ValueError(f"Header '{header}' does not exist")
        
        header_index = self._headers.index(header)
        matching_rows = []
        
        for row_idx, row in enumerate(self._data):
            cell = row[header_index]
            cell_content = cell[0] if isinstance(cell, tuple) else str(cell)
            
            if cell_content == content:
                matching_rows.append(row_idx + 1)  # 1-based
        
        return matching_rows
    
    def format_matching_cells(self, header: str, content: str, format_string: str) -> int:
        """
        Apply formatting to all cells in a column that match specific content.
        
        Args:
            header: Header name
            content: Content to match
            format_string: Format to apply
            
        Returns:
            Number of cells formatted
        """
        matching_rows = self.find_rows(header, content)
        
        for row in matching_rows:
            self.format_cell(header, row, format_string)
        
        return len(matching_rows)
    
    def clear_all_data(self) -> None:
        """Remove all data rows, keep headers and formatting."""
        self._data.clear()
    
    def clear_formatting(self) -> None:
        """Remove all formatting, keep headers and data."""
        self.reset_formatting()
    
    def clear_headers(self) -> None:
        """Remove all headers and data (complete reset)."""
        self._headers.clear()
        self._data.clear()
        self.reset_formatting()
    
    def _validate_format_strings(self) -> None:
        """Check for FDL commands in cell content and warn user."""
        if self._format_warnings_shown:
            return
        
        fdl_pattern = re.compile(r'</[^>]*>')
        warnings_found = False
        
        for row in self._data:
            for cell in row:
                if isinstance(cell, tuple):
                    content = cell[0]
                else:
                    content = str(cell)
                
                if fdl_pattern.search(content):
                    print(f"Warning: FDL commands detected in cell content \"{content}\". "
                          f"Use tuple format: (\"{fdl_pattern.sub('', content).strip()}\", \"</format>\") instead.")
                    warnings_found = True
        
        if warnings_found:
            self._format_warnings_shown = True
    
    # ==================== MEMORY MANAGEMENT ====================
    
    def release(self) -> None:
        """Release the table from memory."""
        if self._released:
            return
        
        # Clear all data structures
        self._headers.clear()
        self._data.clear()
        self._column_formats.clear()
        self._row_formats.clear()
        self._cell_formats.clear()
        self._header_format = None
        
        # Mark as released
        self._released = True
    
    def _check_released(self) -> None:
        """Check if table has been released and raise error if so."""
        if self._released:
            raise RuntimeError("Table has been released and cannot be used")
    
    def _process_format_string(self, format_string: str) -> _FormatState:
        """
        Process a format string into a format state using command processors.
        
        Args:
            format_string: FDL format string like "</red, bold>"
            
        Returns:
            _FormatState: Processed format state
            
        Raises:
            ValueError: If format string is invalid
        """
        if not format_string.strip():
            return _FormatState()
        
        # Create a new format state for processing
        format_state = _FormatState()
        
        # Remove leading/trailing whitespace and angle brackets
        clean_format = format_string.strip()
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
                except UnknownCommandError as e:
                    raise ValueError(f"Invalid format command '{command}': {e}")
                except Exception as e:
                    raise ValueError(f"Error processing format command '{command}': {e}")
        
        return format_state
    
    # ==================== DISPLAY METHODS ====================
    
    def display(self, start_row: int = 1, end_row: Optional[int] = 10) -> None:
        """
        Display the table with optional row range.
        
        Args:
            start_row: Starting row number (1-based)
            end_row: Ending row number (1-based), None for default of 10
        """
        self._check_released()
        
        if end_row is None:
            end_row = 10
        
        self._validate_format_strings()
        
        # Generate table output using table generator
        output = self._table_generator.generate_table(
            headers=self._headers,
            data=self._data,
            style=self.style,
            start_row=start_row,
            end_row=end_row,
            header_format=self._header_format,
            column_formats=self._column_formats,
            row_formats=self._row_formats,
            cell_formats=self._cell_formats
        )
        
        # Display terminal output
        print(output['terminal'])
        
        # Show row count info
        actual_end = min(end_row, self.row_count)
        if self.row_count > actual_end:
            print(f"Showing rows {start_row}-{actual_end} of {self.row_count} total rows")
    
    def display_all_rows(self) -> None:
        """Display all rows in the table."""
        self._check_released()
        
        self._validate_format_strings()
        
        # Generate table output for all rows
        output = self._table_generator.generate_table(
            headers=self._headers,
            data=self._data,
            style=self.style,
            start_row=1,
            end_row=None,
            header_format=self._header_format,
            column_formats=self._column_formats,
            row_formats=self._row_formats,
            cell_formats=self._cell_formats
        )
        
        # Display terminal output
        print(output['terminal'])
        
        if self.row_count > 0:
            print(f"Showing all {self.row_count} rows")
    
    def print(self, start_row: int = 1, end_row: Optional[int] = 10) -> None:
        """Alias for display()."""
        self.display(start_row, end_row)
    
    def print_all_rows(self) -> None:
        """Alias for display_all_rows()."""
        self.display_all_rows()
    
    def get_output(self, start_row: int = 1, end_row: Optional[int] = 10) -> Dict[str, str]:
        """
        Get table output in all formats without displaying.
        
        Args:
            start_row: Starting row number (1-based)
            end_row: Ending row number (1-based), None for default of 10
            
        Returns:
            Dict with keys: 'terminal', 'plain', 'markdown', 'html'
        """
        self._check_released()
        
        if end_row is None:
            end_row = 10
        
        self._validate_format_strings()
        
        return self._table_generator.generate_table(
            headers=self._headers,
            data=self._data,
            style=self.style,
            start_row=start_row,
            end_row=end_row,
            header_format=self._header_format,
            column_formats=self._column_formats,
            row_formats=self._row_formats,
            cell_formats=self._cell_formats
        )