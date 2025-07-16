"""
Custom Table Implementation for fdl - High Performance Table Rendering (REWRITTEN)

This module provides custom table functionality that targets 5x faster performance than Rich.
Features:
- Maximum 3 columns, 10 rows for performance optimization
- Coordinate system: (row, column) where (2,3) = second row down, third column over
- Dual addressing: numeric coordinates (1,1) or named ("Boxes", "Component")
- Format application per cell, row, or column with inheritance
- Box integration using our custom box styles
- Three table types: Table, ColumnTable, RowTable
- Cell management: populate, depopulate, repopulate

Performance optimizations:
- Pre-computed cell dimensions
- Cached format applications
- Direct ANSI output
- Minimal string operations
- Static layout calculations
"""

import warnings
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field

# Import our internal systems
from .boxes import _get_box_renderer, _BoxStyle
from ..core.command_processor import _get_command_processor, _FormattingState
from ..setup.terminal import _terminal


class TableError(Exception):
    """Raised when table operations fail."""
    pass


class TableDimensionError(TableError):
    """Raised when table dimensions exceed limits."""
    pass


class TableAddressError(TableError):
    """Raised when table addressing is invalid."""
    pass


class CellOccupiedError(TableError):
    """Raised when trying to populate an already occupied cell."""
    pass


@dataclass
class _CellData:
    """
    Represents a single table cell with content and formatting.
    
    Attributes:
        content (str): Cell content text
        is_occupied (bool): Whether this cell has been populated
        format_obj: Optional fdl.Format object for cell styling
        row_format_obj: Optional format inherited from row
        column_format_obj: Optional format inherited from column
    """
    content: str = ""
    is_occupied: bool = False
    format_obj: Optional[Any] = None
    row_format_obj: Optional[Any] = None
    column_format_obj: Optional[Any] = None
    
    def get_effective_format(self) -> Optional[Any]:
        """Get the effective format with precedence: cell > row > column."""
        if self.format_obj:
            return self.format_obj
        elif self.row_format_obj:
            return self.row_format_obj
        elif self.column_format_obj:
            return self.column_format_obj
        return None


@dataclass
class _TableLayout:
    """
    Pre-calculated table layout for performance optimization.
    
    Attributes:
        column_widths (List[int]): Width of each column (including row header column)
        total_width (int): Total table width including borders
        row_count (int): Number of data rows
        column_count (int): Number of data columns
        has_row_headers (bool): Whether table has row headers
        has_column_headers (bool): Whether table has column headers
    """
    column_widths: List[int] = field(default_factory=list)
    total_width: int = 0
    row_count: int = 0
    column_count: int = 0
    has_row_headers: bool = False
    has_column_headers: bool = False


class _Table:
    """
    High-performance table with row and column headers.
    
    Coordinate system: (row, column) where (2,3) = second row down, third column over
    
    Table structure:
    ```
              | Col1 | Col2 | Col3 |  <- Column headers
    ----------|------|------|------|
    Row1      | (1,1)| (1,2)| (1,3)|  <- Row headers + data cells
    Row2      | (2,1)| (2,2)| (2,3)|
    ```
    
    Designed to be 5x faster than Rich tables through:
    - Static 3x10 grid pre-allocation
    - Pre-calculated layouts
    - Cached format applications
    - Direct ANSI rendering
    """
    
    # Performance limits
    MAX_COLUMNS = 3
    MAX_ROWS = 10
    
    def __init__(self, box_style: str = "square"):
        """
        Initialize table with specified box style.
        
        Args:
            box_style (str): Box style for table borders
        """
        self.box_style = box_style
        
        # Headers (separate from data grid)
        self._column_headers: List[str] = []  # Column names
        self._row_headers: List[str] = []     # Row names
        
        # Data grid: [row][column] - intersection of headers
        self._data_grid: List[List[_CellData]] = []
        for _ in range(self.MAX_ROWS):
            row = [_CellData() for _ in range(self.MAX_COLUMNS)]
            self._data_grid.append(row)
        
        # Current dimensions
        self._current_columns = 0
        self._current_rows = 0
        
        # Format objects for rows and columns
        self._row_formats: List[Optional[Any]] = [None] * self.MAX_ROWS
        self._column_formats: List[Optional[Any]] = [None] * self.MAX_COLUMNS
        
        # Layout cache
        self._layout: Optional[_TableLayout] = None
        self._layout_dirty = True
        
        # Rendering components
        self._box_renderer = _get_box_renderer()
        self._command_processor = _get_command_processor()
        
        # Performance tracking
        self._cell_updates = 0
        self._renders = 0
    
    def add_column(self, name: str) -> None:
        """
        Add a single column header to the table.
        
        Args:
            name (str): Column header name
            
        Raises:
            TableDimensionError: If would exceed MAX_COLUMNS
        """
        if self._current_columns >= self.MAX_COLUMNS:
            raise TableDimensionError(f"Cannot exceed {self.MAX_COLUMNS} columns")
        
        if name in self._column_headers:
            raise TableAddressError(f"Column '{name}' already exists")
        
        self._column_headers.append(name)
        self._current_columns += 1
        self._layout_dirty = True
    
    def add_columns(self, names: Union[List[str], Tuple[str, ...]]) -> None:
        """
        Add multiple column headers to the table.
        
        Args:
            names: List or tuple of column header names
            
        Raises:
            TableDimensionError: If would exceed MAX_COLUMNS
        """
        if self._current_columns + len(names) > self.MAX_COLUMNS:
            raise TableDimensionError(f"Cannot exceed {self.MAX_COLUMNS} columns")
        
        for name in names:
            self.add_column(name)
    
    def add_row(self, name: str) -> None:
        """
        Add a single row header to the table.
        
        Args:
            name (str): Row header name
            
        Raises:
            TableDimensionError: If would exceed MAX_ROWS
        """
        if self._current_rows >= self.MAX_ROWS:
            raise TableDimensionError(f"Cannot exceed {self.MAX_ROWS} rows")
        
        if name in self._row_headers:
            raise TableAddressError(f"Row '{name}' already exists")
        
        self._row_headers.append(name)
        self._current_rows += 1
        self._layout_dirty = True
    
    def add_rows(self, names: Union[List[str], Tuple[str, ...]]) -> None:
        """
        Add multiple row headers to the table.
        
        Args:
            names: List or tuple of row header names
            
        Raises:
            TableDimensionError: If would exceed MAX_ROWS
        """
        if self._current_rows + len(names) > self.MAX_ROWS:
            raise TableDimensionError(f"Cannot exceed {self.MAX_ROWS} rows")
        
        for name in names:
            self.add_row(name)
    
    def populate(self, row: Union[int, str], column: Union[int, str], 
                content: str) -> None:
        """
        Populate a cell with content using coordinates or names.
        
        Coordinate system: (row, column) where (2,3) = second row down, third column over
        
        Args:
            row: Row index (1-based) or row header name
            column: Column index (1-based) or column header name  
            content: Content to place in cell
            
        Raises:
            TableAddressError: If coordinates are invalid
            CellOccupiedError: If cell is already occupied
        """
        # Convert to 0-based indices
        row_idx = self._resolve_row_address(row)
        col_idx = self._resolve_column_address(column)
        
        # Validate indices
        if row_idx >= self._current_rows:
            raise TableAddressError(f"Row index {row_idx+1} exceeds current rows {self._current_rows}")
        if col_idx >= self._current_columns:
            raise TableAddressError(f"Column index {col_idx+1} exceeds current columns {self._current_columns}")
        
        # Check if cell is already occupied
        cell = self._data_grid[row_idx][col_idx]
        if cell.is_occupied:
            raise CellOccupiedError(f"Cell ({row_idx+1}, {col_idx+1}) is already occupied. Use repopulate() to override.")
        
        # Update cell content
        cell.content = str(content)
        cell.is_occupied = True
        self._cell_updates += 1
        self._layout_dirty = True
    
    def depopulate(self, row: Union[int, str], column: Union[int, str]) -> None:
        """
        Remove content from a cell.
        
        Args:
            row: Row index (1-based) or row header name
            column: Column index (1-based) or column header name
        """
        row_idx = self._resolve_row_address(row)
        col_idx = self._resolve_column_address(column)
        
        cell = self._data_grid[row_idx][col_idx]
        cell.content = ""
        cell.is_occupied = False
        self._layout_dirty = True
    
    def repopulate(self, row: Union[int, str], column: Union[int, str], 
                  content: str) -> None:
        """
        Override content in a cell, even if already occupied.
        
        Args:
            row: Row index (1-based) or row header name
            column: Column index (1-based) or column header name
            content: New content to place in cell
        """
        row_idx = self._resolve_row_address(row)
        col_idx = self._resolve_column_address(column)
        
        cell = self._data_grid[row_idx][col_idx]
        cell.content = str(content)
        cell.is_occupied = True
        self._cell_updates += 1
        self._layout_dirty = True
    
    def _resolve_row_address(self, address: Union[int, str]) -> int:
        """Convert row address to 0-based index."""
        if isinstance(address, int):
            if address < 1 or address > self.MAX_ROWS:
                raise TableAddressError(f"Row index must be 1-{self.MAX_ROWS}, got {address}")
            return address - 1  # Convert to 0-based
        elif isinstance(address, str):
            try:
                return self._row_headers.index(address)
            except ValueError:
                raise TableAddressError(f"Row header '{address}' not found")
        else:
            raise TableAddressError(f"Invalid row address type: {type(address)}")
    
    def _resolve_column_address(self, address: Union[int, str]) -> int:
        """Convert column address to 0-based index."""
        if isinstance(address, int):
            if address < 1 or address > self.MAX_COLUMNS:
                raise TableAddressError(f"Column index must be 1-{self.MAX_COLUMNS}, got {address}")
            return address - 1  # Convert to 0-based
        elif isinstance(address, str):
            try:
                return self._column_headers.index(address)
            except ValueError:
                raise TableAddressError(f"Column header '{address}' not found")
        else:
            raise TableAddressError(f"Invalid column address type: {type(address)}")
    
    def set_cell_format(self, row: Union[int, str], column: Union[int, str], 
                       format_obj: Any) -> None:
        """
        Set format for a specific cell.
        
        Args:
            row: Row index (1-based) or row header name
            column: Column index (1-based) or column header name
            format_obj: fdl.Format object
        """
        row_idx = self._resolve_row_address(row)
        col_idx = self._resolve_column_address(column)
        
        self._data_grid[row_idx][col_idx].format_obj = format_obj
    
    def set_row_format(self, row: Union[int, str], format_obj: Any) -> None:
        """
        Set format for an entire row.
        
        Args:
            row: Row index (1-based) or row header name
            format_obj: fdl.Format object
        """
        row_idx = self._resolve_row_address(row)
        self._row_formats[row_idx] = format_obj
        
        # Update all cells in this row
        for col_idx in range(self._current_columns):
            self._data_grid[row_idx][col_idx].row_format_obj = format_obj
    
    def set_column_format(self, column: Union[int, str], format_obj: Any) -> None:
        """
        Set format for an entire column.
        
        Args:
            column: Column index (1-based) or column header name
            format_obj: fdl.Format object
        """
        col_idx = self._resolve_column_address(column)
        self._column_formats[col_idx] = format_obj
        
        # Update all cells in this column
        for row_idx in range(self._current_rows):
            self._data_grid[row_idx][col_idx].column_format_obj = format_obj
    
    def _calculate_layout(self) -> _TableLayout:
        """Calculate optimal table layout."""
        if not self._layout_dirty and self._layout:
            return self._layout
        
        layout = _TableLayout()
        layout.row_count = self._current_rows
        layout.column_count = self._current_columns
        layout.has_row_headers = len(self._row_headers) > 0
        layout.has_column_headers = len(self._column_headers) > 0
        
        # Calculate column widths
        column_widths = []
        
        # First column: row headers (if any)
        if layout.has_row_headers:
            row_header_width = max(len(header) for header in self._row_headers) if self._row_headers else 0
            column_widths.append(max(row_header_width + 2, 4))  # +2 for padding, min 4
        
        # Data columns
        for col_idx in range(self._current_columns):
            max_width = 0
            
            # Check column header width
            if col_idx < len(self._column_headers):
                max_width = max(max_width, len(self._column_headers[col_idx]))
            
            # Check all cell contents in this column
            for row_idx in range(self._current_rows):
                cell_content = self._data_grid[row_idx][col_idx].content
                max_width = max(max_width, len(cell_content))
            
            # Add padding (minimum 4 chars)
            column_widths.append(max(max_width + 2, 4))
        
        layout.column_widths = column_widths
        layout.total_width = sum(column_widths) + len(column_widths) + 1  # +1 for borders
        
        # Cache the layout
        self._layout = layout
        self._layout_dirty = False
        
        return layout
    
    def _apply_cell_format(self, content: str, cell: _CellData) -> str:
        """Apply effective format to cell content."""
        format_obj = cell.get_effective_format()
        if not format_obj:
            return content
        
        try:
            # Try to apply format using command processor
            from ..core.command_processor import _FormattingState
            current_state = _FormattingState()
            
            # If format object has a method to get commands, use it
            if hasattr(format_obj, 'get_commands'):
                commands = format_obj.get_commands()
                new_state, ansi_sequence = self._command_processor.process_commands(
                    commands, current_state
                )
                reset_ansi = self._command_processor.generate_reset_ansi()
                return f"{ansi_sequence}{content}{reset_ansi}"
            elif hasattr(format_obj, 'format_string'):
                # If it has a format string, try to parse it
                format_str = format_obj.format_string
                # Simple parsing - look for color commands
                if format_str:
                    new_state, ansi_sequence = self._command_processor.process_command(
                        format_str, current_state
                    )
                    reset_ansi = self._command_processor.generate_reset_ansi()
                    return f"{ansi_sequence}{content}{reset_ansi}"
            
        except Exception as e:
            warnings.warn(f"Failed to apply cell format: {e}", UserWarning)
        
        return content
    
    def _render_header_row(self, layout: _TableLayout, box_chars: Dict[str, str]) -> str:
        """Render the column headers row."""
        if not layout.has_column_headers:
            return ""
        
        header_parts = [box_chars['vertical']]
        
        # First column: empty if we have row headers
        if layout.has_row_headers:
            width = layout.column_widths[0]
            padded_content = " " * width
            header_parts.append(padded_content)
            header_parts.append(box_chars['vertical'])
            start_col_idx = 1
        else:
            start_col_idx = 0
        
        # Column headers
        for i, col_idx in enumerate(range(start_col_idx, len(layout.column_widths))):
            width = layout.column_widths[col_idx]
            
            if i < len(self._column_headers):
                header_name = self._column_headers[i]
                available_width = width - 2  # -2 for padding
                if len(header_name) > available_width:
                    header_name = header_name[:available_width]
                padded_content = f" {header_name}".ljust(width - 1) + " "
                if len(padded_content) != width:
                    padded_content = padded_content[:width]
            else:
                padded_content = " " * width
            
            header_parts.append(padded_content)
            header_parts.append(box_chars['vertical'])
        
        return ''.join(header_parts)
    
    def _render_data_row(self, row_idx: int, layout: _TableLayout, 
                        box_chars: Dict[str, str]) -> str:
        """Render a single data row."""
        row_parts = [box_chars['vertical']]
        
        # First column: row header if we have them
        if layout.has_row_headers:
            width = layout.column_widths[0]
            if row_idx < len(self._row_headers):
                row_header = self._row_headers[row_idx]
                available_width = width - 2  # -2 for padding
                if len(row_header) > available_width:
                    row_header = row_header[:available_width]
                padded_content = f" {row_header}".ljust(width - 1) + " "
                if len(padded_content) != width:
                    padded_content = padded_content[:width]
            else:
                padded_content = " " * width
            
            row_parts.append(padded_content)
            row_parts.append(box_chars['vertical'])
            start_col_idx = 1
        else:
            start_col_idx = 0
        
        # Data cells
        for i, col_idx in enumerate(range(start_col_idx, len(layout.column_widths))):
            width = layout.column_widths[col_idx]
            
            if i < self._current_columns:
                cell = self._data_grid[row_idx][i]
                content = self._apply_cell_format(cell.content, cell)
                available_width = width - 2  # -2 for padding
                if len(content) > available_width:
                    content = content[:available_width]
                padded_content = f" {content}".ljust(width - 1) + " "
                if len(padded_content) != width:
                    padded_content = padded_content[:width]
            else:
                padded_content = " " * width
            
            row_parts.append(padded_content)
            row_parts.append(box_chars['vertical'])
        
        return ''.join(row_parts)
    
    def _render_separator(self, layout: _TableLayout, box_chars: Dict[str, str],
                         is_top: bool = False, is_bottom: bool = False) -> str:
        """Render a horizontal separator line."""
        if is_top:
            left_char = box_chars['top_left']
            right_char = box_chars['top_right']
            junction_char = box_chars.get('top_junction', '+')
        elif is_bottom:
            left_char = box_chars['bottom_left']
            right_char = box_chars['bottom_right']
            junction_char = box_chars.get('bottom_junction', '+')
        else:
            left_char = box_chars.get('left_junction', '+')
            right_char = box_chars.get('right_junction', '+')
            junction_char = box_chars.get('cross_junction', '+')
        
        separator_parts = [left_char]
        
        for col_idx, width in enumerate(layout.column_widths):
            separator_parts.append(box_chars['horizontal'] * width)
            if col_idx < len(layout.column_widths) - 1:
                separator_parts.append(junction_char)
        
        separator_parts.append(right_char)
        return ''.join(separator_parts)
    
    def display_table(self) -> str:
        """
        Render the complete table and return as string.
        
        Returns:
            str: Rendered table with separators between all rows
        """
        self._renders += 1
        
        if self._current_columns == 0 and self._current_rows == 0:
            return "[Empty Table]"
        
        # Calculate layout
        layout = self._calculate_layout()
        
        # Get box style characters from box renderer
        box_style = self._box_renderer.get_box_style(self.box_style)
        box_chars = box_style.chars
        
        # Build table lines
        table_lines = []
        
        # Top border
        table_lines.append(self._render_separator(layout, box_chars, is_top=True))
        
        # Column headers row (if we have column headers)
        if layout.has_column_headers:
            table_lines.append(self._render_header_row(layout, box_chars))
            table_lines.append(self._render_separator(layout, box_chars))
        
        # Data rows with separators between each row
        for row_idx in range(self._current_rows):
            table_lines.append(self._render_data_row(row_idx, layout, box_chars))
            
            # Add separator after each row except the last one
            if row_idx < self._current_rows - 1:
                table_lines.append(self._render_separator(layout, box_chars))
        
        # Bottom border
        table_lines.append(self._render_separator(layout, box_chars, is_bottom=True))
        
        return '\n'.join(table_lines)
    
    def get_performance_stats(self) -> Dict[str, Union[int, float]]:
        """Get performance statistics."""
        total_cells = self._current_rows * self._current_columns
        occupied_cells = sum(1 for row_idx in range(self._current_rows) 
                           for col_idx in range(self._current_columns)
                           if self._data_grid[row_idx][col_idx].is_occupied)
        utilization = (occupied_cells / max(total_cells, 1)) * 100
        
        return {
            'current_dimensions': f"{self._current_rows}x{self._current_columns}",
            'max_dimensions': f"{self.MAX_ROWS}x{self.MAX_COLUMNS}",
            'total_cells': total_cells,
            'occupied_cells': occupied_cells,
            'cell_updates': self._cell_updates,
            'cell_utilization': f"{utilization:.1f}%",
            'renders': self._renders,
            'has_row_headers': len(self._row_headers) > 0,
            'has_column_headers': len(self._column_headers) > 0,
            'layout_cache_valid': not self._layout_dirty
        }


# Internal API functions for use by public API and object processor
def _create_table(box_style: str = "square") -> _Table:
    """
    INTERNAL: Create a new table with specified box style.
    
    Args:
        box_style (str): Box style for table borders
        
    Returns:
        _Table: New table instance
    """
    return _Table(box_style)


def _process_table_object(table_obj: _Table) -> str:
    """
    INTERNAL: Process a table object for inline display.
    
    Args:
        table_obj (_Table): Table object to render
        
    Returns:
        str: Rendered table string
        
    Used by object processor for <table_obj> syntax.
    """
    try:
        return table_obj.display_table()
    except Exception as e:
        warnings.warn(f"Table rendering failed: {e}")
        return f"[TABLE_ERROR: {e}]"


# Test script for Table System
if __name__ == "__main__":
    def test_table_system():
        """Comprehensive test suite for the rewritten table system."""
        
        print("=" * 60)
        print("TABLE SYSTEM TEST SUITE (REWRITTEN)")
        print("=" * 60)
        
        test_count = 0
        passed_count = 0
        
        def run_test(name: str, test_func):
            """Run a single test case."""
            nonlocal test_count, passed_count
            test_count += 1
            
            print(f"\nTest {test_count}: {name}")
            
            try:
                passed = test_func()
                if passed:
                    print("✅ PASSED")
                    passed_count += 1
                else:
                    print("❌ FAILED")
                    
            except Exception as e:
                print(f"❌ EXCEPTION: {e}")
                import traceback
                traceback.print_exc()
                
            print("-" * 40)
        
        # Test 1: Basic table creation and population
        def test_basic_table():
            table = _create_table("square")
            
            # Add headers
            table.add_columns(["Component", "Status"])
            table.add_rows(["Boxes", "Tables"])
            
            # Populate cells using (row, column) coordinates
            table.populate(1, 1, "Working")  # Boxes + Component
            table.populate(2, 2, "Working")  # Tables + Status
            
            # Render table
            result = table.display_table()
            
            if not result or "[Empty Table]" in result:
                print("❌ Table failed to render")
                return False
            
            # Check that headers and content are present
            if ("Boxes" not in result or "Tables" not in result or 
                "Component" not in result or "Status" not in result or
                "Working" not in result):
                print("❌ Table content not found in output")
                return False
            
            print(f"✓ Basic table:\n{result}")
            return True
        
        # Test 2: Coordinate system verification
        def test_coordinate_system():
            table = _create_table("square")
            table.add_columns(["Col1", "Col2"])
            table.add_rows(["Row1", "Row2"])
            
            # Test (row, column) coordinates
            table.populate(1, 1, "(1,1)")  # Row1 + Col1
            table.populate(1, 2, "(1,2)")  # Row1 + Col2  
            table.populate(2, 1, "(2,1)")  # Row2 + Col1
            table.populate(2, 2, "(2,2)")  # Row2 + Col2
            
            result = table.display_table()
            
            # All coordinate labels should be present
            expected = ["(1,1)", "(1,2)", "(2,1)", "(2,2)"]
            for content in expected:
                if content not in result:
                    print(f"❌ Content '{content}' not found")
                    return False
            
            print("✓ Coordinate system works correctly")
            return True
        
        # Test 3: Mixed addressing (coordinates and names)
        def test_mixed_addressing():
            table = _create_table("rounded")
            table.add_columns(["A", "B"])
            table.add_rows(["X", "Y"])
            
            # Mixed addressing
            table.populate(1, "A", "NumRow_NameCol")       # (1, 1)
            table.populate("X", 2, "NameRow_NumCol")       # (1, 2)
            table.populate("Y", "B", "NameRow_NameCol")    # (2, 2)
            
            result = table.display_table()
            
            expected = ["NumRow_NameCol", "NameRow_NumCol", "NameRow_NameCol"]
            for content in expected:
                if content not in result:
                    print(f"❌ Content '{content}' not found")
                    return False
            
            print("✓ Mixed addressing works")
            return True
        
        # Test 4: Cell occupation and repopulate
        def test_cell_management():
            table = _create_table("square")
            table.add_columns(["Test"])
            table.add_rows(["Data"])
            
            # Initial populate
            table.populate(1, 1, "First")
            
            # Try to populate same cell (should fail)
            try:
                table.populate(1, 1, "Second")
                print("❌ Should have failed on occupied cell")
                return False
            except CellOccupiedError:
                pass  # Expected
            
            # Repopulate should work
            table.repopulate(1, 1, "Replaced")
            result = table.display_table()
            
            if "Replaced" not in result:
                print("❌ Repopulate failed")
                return False
            
            print("✓ Cell management works")
            return True
        
        # Test 5: Headers-only tables
        def test_headers_only():
            # Table with only column headers
            table1 = _create_table("square")
            table1.add_columns(["A", "B", "C"])
            result1 = table1.display_table()
            
            # Table with only row headers  
            table2 = _create_table("square")
            table2.add_rows(["X", "Y", "Z"])
            result2 = table2.display_table()
            
            # Both should render without crashing
            passed = (result1 and result2 and 
                     len(result1) > 0 and len(result2) > 0)
            
            if passed:
                print("✓ Headers-only tables work")
            
            return passed
        
        # Test 6: Performance stats
        def test_performance_stats():
            table = _create_table()
            table.add_columns(["A", "B"])
            table.add_rows(["1", "2"])
            
            # Make some updates
            table.populate(1, 1, "Data1")
            table.populate(2, 2, "Data2")
            
            # Render table
            table.display_table()
            
            stats = table.get_performance_stats()
            
            if stats['cell_updates'] != 2:
                print(f"❌ Expected 2 cell updates, got {stats['cell_updates']}")
                return False
            
            if stats['renders'] != 1:
                print(f"❌ Expected 1 render, got {stats['renders']}")
                return False
            
            if stats['occupied_cells'] != 2:
                print(f"❌ Expected 2 occupied cells, got {stats['occupied_cells']}")
                return False
            
            print("✓ Performance stats working")
            return True
        
        # Run all tests
        run_test("Basic table creation and population", test_basic_table)
        run_test("Coordinate system verification", test_coordinate_system)
        run_test("Mixed addressing", test_mixed_addressing)
        run_test("Cell occupation and repopulate", test_cell_management)
        run_test("Headers-only tables", test_headers_only)
        run_test("Performance stats", test_performance_stats)
        
        print("\n" + "=" * 60)
        print(f"TEST RESULTS: {passed_count}/{test_count} tests passed")
        if passed_count == test_count:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"❌ {test_count - passed_count} tests failed")
        print("=" * 60)
        
        return passed_count == test_count
    
    # Run the tests
    test_table_system()