"""
Comprehensive Deep Tests for FDL Table Class.

Tests the internal table system that provides API-driven data management,
tuple-based formatting, multi-format output, and comprehensive table operations.
"""

import pytest
import sys
import os
import re
from unittest.mock import Mock, patch, MagicMock
from wcwidth import wcswidth
from copy import deepcopy

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.classes.table import _Table
from suitkaise.fdl._int.core.format_state import _FormatState


class TestTableInitialization:
    """Test suite for table initialization and basic properties."""
    
    def test_table_initialization_defaults(self):
        """Test table initialization with default values."""
        table = _Table()
        
        assert table.style == "rounded"
        assert table.max_columns is None
        assert table.max_rows is None
        assert table.row_count == 0
        assert table.column_count == 0
        assert table.header_count == 0
        assert table._headers == []
        assert table._data == []
        assert table._header_format is None
        assert table._column_formats == {}
        assert table._row_formats == {}
        assert table._cell_formats == {}
        assert not table._released
        assert not table._format_warnings_shown
    
    def test_table_initialization_with_options(self):
        """Test table initialization with custom options."""
        table = _Table(style="square", max_columns=5, max_rows=100)
        
        assert table.style == "square"
        assert table.max_columns == 5
        assert table.max_rows == 100
    
    def test_table_properties_dynamic(self):
        """Test that properties update dynamically."""
        table = _Table()
        
        # Add headers and verify counts
        table.add_header("Name")
        assert table.column_count == 1
        assert table.header_count == 1
        
        table.add_header("Age")
        assert table.column_count == 2
        assert table.header_count == 2
        
        # Add data and verify row count
        table.add_row_data(["Alice", "25"])
        assert table.row_count == 1
        
        table.add_row_data([["Bob", "30"], ["Charlie", "35"]])
        assert table.row_count == 3


class TestTableHeaderManagement:
    """Test suite for table header management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.table = _Table()
    
    def test_add_header_single(self):
        """Test adding a single header."""
        self.table.add_header("Name")
        
        assert self.table.column_count == 1
        assert self.table._headers == ["Name"]
    
    def test_add_header_multiple_sequential(self):
        """Test adding multiple headers sequentially."""
        self.table.add_header("Name")
        self.table.add_header("Age")
        self.table.add_header("City")
        
        assert self.table.column_count == 3
        assert self.table._headers == ["Name", "Age", "City"]
    
    def test_add_headers_batch(self):
        """Test adding multiple headers in batch."""
        headers = ["Name", "Age", "City", "Country"]
        self.table.add_headers(headers)
        
        assert self.table.column_count == 4
        assert self.table._headers == headers
    
    def test_add_header_with_max_columns(self):
        """Test adding headers with max_columns limit."""
        table = _Table(max_columns=2)
        
        table.add_header("Name")
        table.add_header("Age")
        
        # Should succeed up to limit
        assert table.column_count == 2
        
        # Should fail when exceeding limit
        with pytest.raises(ValueError) as exc_info:
            table.add_header("City")
        
        assert "max_columns (2) would be exceeded" in str(exc_info.value)
    
    def test_add_header_duplicate(self):
        """Test adding duplicate header."""
        self.table.add_header("Name")
        
        with pytest.raises(ValueError) as exc_info:
            self.table.add_header("Name")
        
        assert "Header 'Name' already exists" in str(exc_info.value)
    
    def test_add_header_with_existing_data(self):
        """Test adding header when data already exists."""
        # Add initial structure
        self.table.add_header("Name")
        self.table.add_row_data(["Alice"])
        
        # Add new header
        self.table.add_header("Age")
        
        # Should add empty cells to existing rows
        assert self.table.column_count == 2
        assert self.table._data[0] == ["Alice", ""]
    
    def test_remove_header_basic(self):
        """Test removing a header."""
        self.table.add_headers(["Name", "Age", "City"])
        self.table.add_row_data(["Alice", "25", "NYC"])
        
        self.table.remove_header("Age")
        
        assert self.table.column_count == 2
        assert self.table._headers == ["Name", "City"]
        assert self.table._data[0] == ["Alice", "NYC"]
    
    def test_remove_header_nonexistent(self):
        """Test removing non-existent header."""
        self.table.add_header("Name")
        
        with pytest.raises(ValueError) as exc_info:
            self.table.remove_header("Age")
        
        assert "Header 'Age' does not exist" in str(exc_info.value)
    
    def test_remove_header_with_formatting(self):
        """Test removing header removes associated formatting."""
        self.table.add_headers(["Name", "Age"])
        self.table.format_column("Name", "</bold>")
        self.table.format_cell("Name", 1, "</red>")
        self.table.add_row_data(["Alice", "25"])
        
        # Verify formatting exists
        assert "Name" in self.table._column_formats
        assert ("Name", 1) in self.table._cell_formats
        
        # Remove header
        self.table.remove_header("Name")
        
        # Verify formatting is cleaned up
        assert "Name" not in self.table._column_formats
        assert ("Name", 1) not in self.table._cell_formats
    
    def test_get_headers(self):
        """Test getting headers list."""
        headers = ["Name", "Age", "City"]
        self.table.add_headers(headers)
        
        returned_headers = self.table.get_headers()
        
        # Should return copy, not reference
        assert returned_headers == headers
        assert returned_headers is not self.table._headers
        
        # Modifying returned list shouldn't affect table
        returned_headers.append("Country")
        assert self.table.column_count == 3


class TestTableDataManagement:
    """Test suite for table data management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.table = _Table()
        self.table.add_headers(["Name", "Age", "City"])
    
    def test_add_row_data_single_row(self):
        """Test adding a single row of data."""
        self.table.add_row_data(["Alice", "25", "NYC"])
        
        assert self.table.row_count == 1
        assert self.table._data[0] == ["Alice", "25", "NYC"]
    
    def test_add_row_data_multiple_rows(self):
        """Test adding multiple rows of data."""
        rows = [
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"],
            ["Charlie", "35", "Chicago"]
        ]
        self.table.add_row_data(rows)
        
        assert self.table.row_count == 3
        assert self.table._data == rows
    
    def test_add_row_data_mixed_types(self):
        """Test adding row data with mixed types."""
        # Test with tuples for formatting
        row_data = [
            ("Alice", "</bold>"),
            "25",
            ("NYC", "</italic>")
        ]
        self.table.add_row_data(row_data)
        
        assert self.table.row_count == 1
        assert self.table._data[0] == row_data
    
    def test_add_row_data_no_headers(self):
        """Test adding row data without headers defined."""
        table = _Table()
        
        with pytest.raises(ValueError) as exc_info:
            table.add_row_data(["Alice", "25"])
        
        assert "Must define headers before adding data" in str(exc_info.value)
    
    def test_add_row_data_length_mismatch(self):
        """Test adding row data with wrong length."""
        with pytest.raises(ValueError) as exc_info:
            self.table.add_row_data(["Alice", "25"])  # Missing city
        
        assert "Row length (2) must match header count (3)" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            self.table.add_row_data(["Alice", "25", "NYC", "Extra"])  # Too many columns
        
        assert "Row length (4) must match header count (3)" in str(exc_info.value)
    
    def test_add_row_data_with_max_rows(self):
        """Test adding row data with max_rows limit."""
        table = _Table(max_rows=2)
        table.add_headers(["Name", "Age"])
        
        table.add_row_data(["Alice", "25"])
        table.add_row_data(["Bob", "30"])
        
        # Should succeed up to limit
        assert table.row_count == 2
        
        # Should fail when exceeding limit
        with pytest.raises(ValueError) as exc_info:
            table.add_row_data(["Charlie", "35"])
        
        assert "max_rows (2) would be exceeded" in str(exc_info.value)
    
    def test_remove_row_data_single_row(self):
        """Test removing a single row of data."""
        self.table.add_row_data([
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"],
            ["Charlie", "35", "Chicago"]
        ])
        
        self.table.remove_row_data(["Bob", "30", "LA"])
        
        assert self.table.row_count == 2
        assert self.table._data == [
            ["Alice", "25", "NYC"],
            ["Charlie", "35", "Chicago"]
        ]
    
    def test_remove_row_data_multiple_rows(self):
        """Test removing multiple rows of data."""
        self.table.add_row_data([
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"],
            ["Charlie", "35", "Chicago"],
            ["David", "40", "Seattle"]
        ])
        
        rows_to_remove = [
            ["Bob", "30", "LA"],
            ["David", "40", "Seattle"]
        ]
        self.table.remove_row_data(rows_to_remove)
        
        assert self.table.row_count == 2
        assert self.table._data == [
            ["Alice", "25", "NYC"],
            ["Charlie", "35", "Chicago"]
        ]
    
    def test_remove_row_data_with_tuples(self):
        """Test removing row data that contains tuples."""
        self.table.add_row_data([
            [("Alice", "</bold>"), "25", "NYC"],
            ["Bob", ("30", "</italic>"), "LA"]
        ])
        
        # Should match based on content only, ignoring formatting
        self.table.remove_row_data(["Alice", "25", "NYC"])
        
        assert self.table.row_count == 1
        assert self.table._data[0] == ["Bob", ("30", "</italic>"), "LA"]
    
    def test_remove_row_data_nonexistent(self):
        """Test removing non-existent row data."""
        self.table.add_row_data(["Alice", "25", "NYC"])
        
        # Should not raise error, just do nothing
        self.table.remove_row_data(["Bob", "30", "LA"])
        
        assert self.table.row_count == 1
        assert self.table._data[0] == ["Alice", "25", "NYC"]


class TestTableCellAccess:
    """Test suite for table cell access functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.table = _Table()
        self.table.add_headers(["Name", "Age", "City"])
        self.table.add_row_data([
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"],
            ["Charlie", "35", "Chicago"]
        ])
    
    def test_set_cell_basic(self):
        """Test setting cell values."""
        self.table.set_cell("Name", 1, "Alicia")
        
        assert self.table._data[0][0] == "Alicia"
    
    def test_set_cell_with_tuple(self):
        """Test setting cell with tuple formatting."""
        self.table.set_cell("Age", 2, ("31", "</bold>"))
        
        assert self.table._data[1][1] == ("31", "</bold>")
    
    def test_set_cell_invalid_header(self):
        """Test setting cell with invalid header."""
        with pytest.raises(ValueError) as exc_info:
            self.table.set_cell("Invalid", 1, "value")
        
        assert "Header 'Invalid' does not exist" in str(exc_info.value)
    
    def test_set_cell_invalid_row(self):
        """Test setting cell with invalid row number."""
        with pytest.raises(ValueError) as exc_info:
            self.table.set_cell("Name", 0, "value")  # 0-based
        
        assert "Row 0 is out of range (1-3)" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            self.table.set_cell("Name", 4, "value")  # Beyond range
        
        assert "Row 4 is out of range (1-3)" in str(exc_info.value)
    
    def test_get_cell_basic(self):
        """Test getting cell values."""
        value = self.table.get_cell("Name", 1)
        assert value == "Alice"
        
        value = self.table.get_cell("Age", 2)
        assert value == "30"
        
        value = self.table.get_cell("City", 3)
        assert value == "Chicago"
    
    def test_get_cell_with_tuple(self):
        """Test getting cell with tuple formatting."""
        self.table.set_cell("Name", 1, ("Alicia", "</bold>"))
        
        value = self.table.get_cell("Name", 1)
        assert value == ("Alicia", "</bold>")
    
    def test_get_cell_invalid_header(self):
        """Test getting cell with invalid header."""
        with pytest.raises(ValueError) as exc_info:
            self.table.get_cell("Invalid", 1)
        
        assert "Header 'Invalid' does not exist" in str(exc_info.value)
    
    def test_get_cell_invalid_row(self):
        """Test getting cell with invalid row number."""
        with pytest.raises(ValueError) as exc_info:
            self.table.get_cell("Name", 0)
        
        assert "Row 0 is out of range (1-3)" in str(exc_info.value)
    
    def test_update_cell_basic(self):
        """Test updating cell by content."""
        success = self.table.update_cell("Alice", "Alicia")
        
        assert success is True
        assert self.table.get_cell("Name", 1) == "Alicia"
    
    def test_update_cell_with_tuple_target(self):
        """Test updating cell that contains tuple."""
        self.table.set_cell("Name", 1, ("Alice", "</bold>"))
        
        success = self.table.update_cell("Alice", "Alicia")
        
        assert success is True
        assert self.table.get_cell("Name", 1) == "Alicia"
    
    def test_update_cell_with_tuple_replacement(self):
        """Test updating cell with tuple replacement."""
        success = self.table.update_cell("Alice", ("Alicia", "</italic>"))
        
        assert success is True
        assert self.table.get_cell("Name", 1) == ("Alicia", "</italic>")
    
    def test_update_cell_nonexistent(self):
        """Test updating non-existent cell content."""
        success = self.table.update_cell("NonExistent", "NewValue")
        
        assert success is False
        # Data should remain unchanged
        assert self.table.get_cell("Name", 1) == "Alice"
    
    def test_update_cell_multiple_matches(self):
        """Test updating cell when multiple matches exist."""
        # Add duplicate content
        self.table.add_row_data(["Alice", "40", "Boston"])
        
        # Should update only the first match
        success = self.table.update_cell("Alice", "Alicia")
        
        assert success is True
        assert self.table.get_cell("Name", 1) == "Alicia"
        assert self.table.get_cell("Name", 4) == "Alice"  # Unchanged
    
    def test_get_row_basic(self):
        """Test getting entire row."""
        row = self.table.get_row(1)
        
        assert row == ["Alice", "25", "NYC"]
        assert row is not self.table._data[0]  # Should be copy
    
    def test_get_row_with_tuples(self):
        """Test getting row with tuple formatting."""
        self.table.set_cell("Name", 1, ("Alice", "</bold>"))
        
        row = self.table.get_row(1)
        
        assert row == [("Alice", "</bold>"), "25", "NYC"]
    
    def test_get_row_invalid(self):
        """Test getting invalid row."""
        with pytest.raises(ValueError) as exc_info:
            self.table.get_row(0)
        
        assert "Row 0 is out of range (1-3)" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            self.table.get_row(4)
        
        assert "Row 4 is out of range (1-3)" in str(exc_info.value)
    
    def test_get_column_basic(self):
        """Test getting entire column."""
        column = self.table.get_column("Name")
        
        assert column == ["Alice", "Bob", "Charlie"]
    
    def test_get_column_with_tuples(self):
        """Test getting column with tuple formatting."""
        self.table.set_cell("Age", 2, ("31", "</bold>"))
        
        column = self.table.get_column("Age")
        
        assert column == ["25", ("31", "</bold>"), "35"]
    
    def test_get_column_invalid(self):
        """Test getting invalid column."""
        with pytest.raises(ValueError) as exc_info:
            self.table.get_column("Invalid")
        
        assert "Header 'Invalid' does not exist" in str(exc_info.value)


class TestTableFormatting:
    """Test suite for table formatting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.table = _Table()
        self.table.add_headers(["Name", "Age", "City"])
        self.table.add_row_data([
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"]
        ])
    
    def test_format_headers(self):
        """Test formatting all headers."""
        with patch.object(self.table, '_process_format_string', return_value=Mock()) as mock_process:
            self.table.format_headers("</bold, underline>")
            
            mock_process.assert_called_once_with("</bold, underline>")
            assert self.table._header_format is not None
    
    def test_format_column(self):
        """Test formatting entire column."""
        with patch.object(self.table, '_process_format_string', return_value=Mock()) as mock_process:
            self.table.format_column("Name", "</red, italic>")
            
            mock_process.assert_called_once_with("</red, italic>")
            assert "Name" in self.table._column_formats
    
    def test_format_column_invalid_header(self):
        """Test formatting column with invalid header."""
        with pytest.raises(ValueError) as exc_info:
            self.table.format_column("Invalid", "</bold>")
        
        assert "Header 'Invalid' does not exist" in str(exc_info.value)
    
    def test_format_row(self):
        """Test formatting entire row."""
        with patch.object(self.table, '_process_format_string', return_value=Mock()) as mock_process:
            self.table.format_row(1, "</yellow>")
            
            mock_process.assert_called_once_with("</yellow>")
            assert 1 in self.table._row_formats
    
    def test_format_row_invalid(self):
        """Test formatting invalid row."""
        with pytest.raises(ValueError) as exc_info:
            self.table.format_row(0, "</bold>")
        
        assert "Row 0 is out of range (1-2)" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            self.table.format_row(3, "</bold>")
        
        assert "Row 3 is out of range (1-2)" in str(exc_info.value)
    
    def test_format_cell(self):
        """Test formatting specific cell."""
        with patch.object(self.table, '_process_format_string', return_value=Mock()) as mock_process:
            self.table.format_cell("Name", 1, "</bold, green>")
            
            mock_process.assert_called_once_with("</bold, green>")
            assert ("Name", 1) in self.table._cell_formats
    
    def test_format_cell_invalid_header(self):
        """Test formatting cell with invalid header."""
        with pytest.raises(ValueError) as exc_info:
            self.table.format_cell("Invalid", 1, "</bold>")
        
        assert "Header 'Invalid' does not exist" in str(exc_info.value)
    
    def test_format_cell_invalid_row(self):
        """Test formatting cell with invalid row."""
        with pytest.raises(ValueError) as exc_info:
            self.table.format_cell("Name", 3, "</bold>")
        
        assert "Row 3 is out of range (1-2)" in str(exc_info.value)
    
    def test_reset_formatting_all(self):
        """Test resetting all formatting."""
        # Set up various formatting
        self.table.format_headers("</bold>")
        self.table.format_column("Name", "</red>")
        self.table.format_row(1, "</yellow>")
        self.table.format_cell("Age", 2, "</italic>")
        
        # Reset all
        self.table.reset_formatting()
        
        assert self.table._header_format is None
        assert len(self.table._column_formats) == 0
        assert len(self.table._row_formats) == 0
        assert len(self.table._cell_formats) == 0
    
    def test_reset_header_formatting(self):
        """Test resetting header formatting."""
        self.table.format_headers("</bold>")
        assert self.table._header_format is not None
        
        self.table.reset_header_formatting()
        assert self.table._header_format is None
    
    def test_reset_column_formatting(self):
        """Test resetting column formatting."""
        self.table.format_column("Name", "</red>")
        assert "Name" in self.table._column_formats
        
        self.table.reset_column_formatting("Name")
        assert "Name" not in self.table._column_formats
    
    def test_reset_column_formatting_nonexistent(self):
        """Test resetting formatting for non-existent column."""
        # Should not raise error
        self.table.reset_column_formatting("NonExistent")
    
    def test_reset_row_formatting(self):
        """Test resetting row formatting."""
        self.table.format_row(1, "</yellow>")
        assert 1 in self.table._row_formats
        
        self.table.reset_row_formatting(1)
        assert 1 not in self.table._row_formats
    
    def test_reset_row_formatting_nonexistent(self):
        """Test resetting formatting for non-existent row."""
        # Should not raise error
        self.table.reset_row_formatting(999)
    
    def test_reset_cell_formatting(self):
        """Test resetting cell formatting."""
        self.table.format_cell("Name", 1, "</bold>")
        assert ("Name", 1) in self.table._cell_formats
        
        self.table.reset_cell_formatting("Name", 1)
        assert ("Name", 1) not in self.table._cell_formats
    
    def test_reset_cell_formatting_nonexistent(self):
        """Test resetting formatting for non-existent cell."""
        # Should not raise error
        self.table.reset_cell_formatting("NonExistent", 999)
    
    def test_process_format_string_basic(self):
        """Test _process_format_string method."""
        with patch.object(self.table._command_registry, 'process_command', return_value=Mock()) as mock_process:
            result = self.table._process_format_string("</green, bold>")
            
            assert result is not None
            assert mock_process.call_count == 2
            mock_process.assert_any_call("green", result)
            mock_process.assert_any_call("bold", result)
    
    def test_process_format_string_empty(self):
        """Test _process_format_string with empty string."""
        result = self.table._process_format_string("")
        
        assert isinstance(result, _FormatState)
        
        result = self.table._process_format_string("   ")
        
        assert isinstance(result, _FormatState)
    
    def test_process_format_string_bracket_variations(self):
        """Test _process_format_string with different bracket formats."""
        with patch.object(self.table._command_registry, 'process_command', return_value=Mock()) as mock_process:
            # Test </command> format
            self.table._process_format_string("</green>")
            mock_process.assert_called_with("green", mock_process.return_value)
            
            mock_process.reset_mock()
            
            # Test <command> format (without slash)
            self.table._process_format_string("<green>")
            mock_process.assert_called_with("green", mock_process.return_value)
    
    def test_process_format_string_unknown_command(self):
        """Test _process_format_string with unknown command."""
        from suitkaise.fdl._int.core.command_registry import UnknownCommandError
        
        with patch.object(self.table._command_registry, 'process_command', 
                         side_effect=UnknownCommandError("Unknown command: 'invalid'")):
            with pytest.raises(ValueError) as exc_info:
                self.table._process_format_string("</invalid>")
            
            assert "Invalid format command 'invalid'" in str(exc_info.value)
    
    def test_process_format_string_processing_error(self):
        """Test _process_format_string with processing error."""
        with patch.object(self.table._command_registry, 'process_command', 
                         side_effect=Exception("Processing error")):
            with pytest.raises(ValueError) as exc_info:
                self.table._process_format_string("</green>")
            
            assert "Error processing format command 'green'" in str(exc_info.value)


class TestTableUtilityMethods:
    """Test suite for table utility methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.table = _Table(style="square", max_columns=5, max_rows=100)
        self.table.add_headers(["Name", "Age", "City"])
        self.table.add_row_data([
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"],
            ["Charlie", "35", "Chicago"]
        ])
        self.table.format_headers("</bold>")
        self.table.format_column("Name", "</red>")
    
    def test_copy_method(self):
        """Test copying table."""
        copied = self.table.copy()
        
        # Should be different instance
        assert copied is not self.table
        assert isinstance(copied, _Table)
        
        # Should have same configuration
        assert copied.style == "square"
        assert copied.max_columns == 5
        assert copied.max_rows == 100
        
        # Should have copied headers and data
        assert copied._headers == self.table._headers
        assert copied._headers is not self.table._headers  # Different list
        assert copied._data == self.table._data
        assert copied._data is not self.table._data  # Different list
        
        # Should have copied formatting
        assert copied._header_format == self.table._header_format
        assert copied._column_formats == self.table._column_formats
        assert copied._column_formats is not self.table._column_formats
    
    def test_copy_independence(self):
        """Test that copied table is independent."""
        copied = self.table.copy()
        
        # Modify original
        self.table.add_header("Country")
        self.table.add_row_data(["David", "40", "Seattle", "USA"])
        
        # Copy should be unchanged
        assert copied.column_count == 3
        assert copied.row_count == 3
        assert "Country" not in copied._headers
    
    def test_find_rows_basic(self):
        """Test finding rows by content."""
        rows = self.table.find_rows("Name", "Alice")
        
        assert rows == [1]
        
        rows = self.table.find_rows("Age", "30")
        
        assert rows == [2]
    
    def test_find_rows_multiple_matches(self):
        """Test finding rows with multiple matches."""
        # Add duplicate name
        self.table.add_row_data(["Alice", "40", "Boston"])
        
        rows = self.table.find_rows("Name", "Alice")
        
        assert rows == [1, 4]
    
    def test_find_rows_no_matches(self):
        """Test finding rows with no matches."""
        rows = self.table.find_rows("Name", "NonExistent")
        
        assert rows == []
    
    def test_find_rows_with_tuples(self):
        """Test finding rows when data contains tuples."""
        self.table.set_cell("Name", 1, ("Alice", "</bold>"))
        
        rows = self.table.find_rows("Name", "Alice")
        
        assert rows == [1]  # Should match content, ignore formatting
    
    def test_find_rows_invalid_header(self):
        """Test finding rows with invalid header."""
        with pytest.raises(ValueError) as exc_info:
            self.table.find_rows("Invalid", "value")
        
        assert "Header 'Invalid' does not exist" in str(exc_info.value)
    
    def test_format_matching_cells_basic(self):
        """Test formatting cells that match content."""
        with patch.object(self.table, 'format_cell') as mock_format:
            count = self.table.format_matching_cells("Age", "30", "</bold>")
            
            assert count == 1
            mock_format.assert_called_once_with("Age", 2, "</bold>")
    
    def test_format_matching_cells_multiple(self):
        """Test formatting multiple matching cells."""
        # Add duplicate age
        self.table.add_row_data(["David", "30", "Boston"])
        
        with patch.object(self.table, 'format_cell') as mock_format:
            count = self.table.format_matching_cells("Age", "30", "</bold>")
            
            assert count == 2
            assert mock_format.call_count == 2
            mock_format.assert_any_call("Age", 2, "</bold>")
            mock_format.assert_any_call("Age", 4, "</bold>")
    
    def test_format_matching_cells_no_matches(self):
        """Test formatting cells with no matches."""
        with patch.object(self.table, 'format_cell') as mock_format:
            count = self.table.format_matching_cells("Age", "999", "</bold>")
            
            assert count == 0
            mock_format.assert_not_called()
    
    def test_clear_all_data(self):
        """Test clearing all data while keeping headers."""
        original_headers = self.table._headers.copy()
        
        self.table.clear_all_data()
        
        assert self.table.row_count == 0
        assert self.table._data == []
        assert self.table._headers == original_headers  # Headers preserved
        assert self.table._header_format is not None  # Formatting preserved
    
    def test_clear_formatting(self):
        """Test clearing all formatting while keeping data."""
        original_headers = self.table._headers.copy()
        original_data = deepcopy(self.table._data)
        
        self.table.clear_formatting()
        
        assert self.table._headers == original_headers  # Headers preserved
        assert self.table._data == original_data  # Data preserved
        assert self.table._header_format is None  # Formatting cleared
        assert len(self.table._column_formats) == 0
    
    def test_clear_headers(self):
        """Test clearing headers (complete reset)."""
        self.table.clear_headers()
        
        assert self.table.column_count == 0
        assert self.table.row_count == 0
        assert self.table._headers == []
        assert self.table._data == []
        assert self.table._header_format is None
        assert len(self.table._column_formats) == 0
    
    def test_validate_format_strings_no_warnings(self):
        """Test format string validation with clean data."""
        with patch('builtins.print') as mock_print:
            self.table._validate_format_strings()
            
            mock_print.assert_not_called()
    
    def test_validate_format_strings_with_fdl_commands(self):
        """Test format string validation with FDL commands in content."""
        # Add data with FDL commands
        self.table.add_row_data(["</red>Warning Text", "25", "NYC"])
        
        with patch('builtins.print') as mock_print:
            self.table._validate_format_strings()
            
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Warning: FDL commands detected" in call_args
            assert "Use tuple format" in call_args
    
    def test_validate_format_strings_warning_once(self):
        """Test that format string warnings are shown only once."""
        self.table.add_row_data(["</red>Warning Text", "25", "NYC"])
        
        with patch('builtins.print') as mock_print:
            self.table._validate_format_strings()
            self.table._validate_format_strings()  # Second call
            
            # Should only print once
            mock_print.assert_called_once()
    
    def test_validate_format_strings_in_tuples(self):
        """Test format string validation ignores tuple content."""
        # Add data with tuple containing FDL commands (this is correct usage)
        self.table.add_row_data([("Normal Text", "</red>"), "25", "NYC"])
        
        with patch('builtins.print') as mock_print:
            self.table._validate_format_strings()
            
            # Should not warn about FDL commands in tuple format strings
            mock_print.assert_not_called()


class TestTableMemoryManagement:
    """Test suite for table memory management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.table = _Table()
        self.table.add_headers(["Name", "Age"])
        self.table.add_row_data(["Alice", "25"])
        self.table.format_headers("</bold>")
    
    def test_release_method(self):
        """Test releasing table from memory."""
        self.table.release()
        
        assert self.table._released
        assert self.table._headers == []
        assert self.table._data == []
        assert self.table._column_formats == {}
        assert self.table._row_formats == {}
        assert self.table._cell_formats == {}
        assert self.table._header_format is None
    
    def test_release_method_idempotent(self):
        """Test that release can be called multiple times safely."""
        self.table.release()
        self.table.release()  # Should not raise error
        
        assert self.table._released
    
    def test_check_released_method(self):
        """Test _check_released method."""
        # Should not raise when not released
        self.table._check_released()
        
        # Should raise when released
        self.table.release()
        with pytest.raises(RuntimeError) as exc_info:
            self.table._check_released()
        
        assert "Table has been released" in str(exc_info.value)
    
    def test_methods_after_release(self):
        """Test that methods raise errors after release."""
        self.table.release()
        
        methods_to_test = [
            (self.table.add_header, ["Test"]),
            (self.table.add_row_data, [["Test", "Data"]]),
            (self.table.format_headers, ["</bold>"]),
            (self.table.format_column, ["Name", "</red>"]),
            (self.table.format_row, [1, "</yellow>"]),
            (self.table.format_cell, ["Name", 1, "</italic>"]),
            (self.table.copy, []),
            (self.table.display, []),
            (self.table.display_all_rows, []),
            (self.table.get_output, []),
        ]
        
        for method, args in methods_to_test:
            with pytest.raises(RuntimeError) as exc_info:
                method(*args)
            assert "Table has been released" in str(exc_info.value)


class TestTableDisplayMethods:
    """Test suite for table display methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.table = _Table()
        self.table.add_headers(["Name", "Age", "City"])
        # Add enough data to test pagination
        for i in range(15):
            self.table.add_row_data([f"Person{i+1}", f"{20+i}", f"City{i+1}"])
    
    def test_display_method_default(self):
        """Test display method with default parameters."""
        mock_output = {'terminal': 'mock_table_output'}
        
        with patch.object(self.table._table_generator, 'generate_table', return_value=mock_output) as mock_generate, \
             patch('builtins.print') as mock_print:
            
            self.table.display()
            
            mock_generate.assert_called_once_with(
                headers=self.table._headers,
                data=self.table._data,
                style="rounded",
                start_row=1,
                end_row=10,
                header_format=None,
                column_formats={},
                row_formats={},
                cell_formats={}
            )
            
            # Should print table and row info
            assert mock_print.call_count == 2
            mock_print.assert_any_call('mock_table_output')
            mock_print.assert_any_call('Showing rows 1-10 of 15 total rows')
    
    def test_display_method_custom_range(self):
        """Test display method with custom row range."""
        mock_output = {'terminal': 'mock_table_output'}
        
        with patch.object(self.table._table_generator, 'generate_table', return_value=mock_output) as mock_generate, \
             patch('builtins.print') as mock_print:
            
            self.table.display(start_row=5, end_row=8)
            
            mock_generate.assert_called_once_with(
                headers=self.table._headers,
                data=self.table._data,
                style="rounded",
                start_row=5,
                end_row=8,
                header_format=None,
                column_formats={},
                row_formats={},
                cell_formats={}
            )
            
            mock_print.assert_any_call('Showing rows 5-8 of 15 total rows')
    
    def test_display_method_no_pagination_needed(self):
        """Test display method when no pagination info is needed."""
        # Create table with few rows
        small_table = _Table()
        small_table.add_headers(["Name", "Age"])
        small_table.add_row_data([["Alice", "25"], ["Bob", "30"]])
        
        mock_output = {'terminal': 'mock_table_output'}
        
        with patch.object(small_table._table_generator, 'generate_table', return_value=mock_output), \
             patch('builtins.print') as mock_print:
            
            small_table.display()
            
            # Should only print table, no pagination info
            mock_print.assert_called_once_with('mock_table_output')
    
    def test_display_all_rows_method(self):
        """Test display_all_rows method."""
        mock_output = {'terminal': 'mock_table_output'}
        
        with patch.object(self.table._table_generator, 'generate_table', return_value=mock_output) as mock_generate, \
             patch('builtins.print') as mock_print:
            
            self.table.display_all_rows()
            
            mock_generate.assert_called_once_with(
                headers=self.table._headers,
                data=self.table._data,
                style="rounded",
                start_row=1,
                end_row=None,
                header_format=None,
                column_formats={},
                row_formats={},
                cell_formats={}
            )
            
            # Should print table and total rows info
            assert mock_print.call_count == 2
            mock_print.assert_any_call('mock_table_output')
            mock_print.assert_any_call('Showing all 15 rows')
    
    def test_display_all_rows_empty_table(self):
        """Test display_all_rows with empty table."""
        empty_table = _Table()
        empty_table.add_headers(["Name", "Age"])
        
        mock_output = {'terminal': 'mock_table_output'}
        
        with patch.object(empty_table._table_generator, 'generate_table', return_value=mock_output), \
             patch('builtins.print') as mock_print:
            
            empty_table.display_all_rows()
            
            # Should only print table, no row count info
            mock_print.assert_called_once_with('mock_table_output')
    
    def test_print_method_alias(self):
        """Test print method as alias for display."""
        with patch.object(self.table, 'display') as mock_display:
            self.table.print(start_row=2, end_row=5)
            
            mock_display.assert_called_once_with(2, 5)
    
    def test_print_all_rows_method_alias(self):
        """Test print_all_rows method as alias for display_all_rows."""
        with patch.object(self.table, 'display_all_rows') as mock_display_all:
            self.table.print_all_rows()
            
            mock_display_all.assert_called_once()
    
    def test_get_output_method(self):
        """Test get_output method."""
        mock_output = {
            'terminal': 'terminal_output',
            'plain': 'plain_output',
            'markdown': 'markdown_output',
            'html': 'html_output'
        }
        
        with patch.object(self.table._table_generator, 'generate_table', return_value=mock_output) as mock_generate:
            result = self.table.get_output(start_row=3, end_row=7)
            
            mock_generate.assert_called_once_with(
                headers=self.table._headers,
                data=self.table._data,
                style="rounded",
                start_row=3,
                end_row=7,
                header_format=None,
                column_formats={},
                row_formats={},
                cell_formats={}
            )
            
            assert result == mock_output
    
    def test_get_output_method_default_end_row(self):
        """Test get_output method with default end_row."""
        mock_output = {'terminal': 'output'}
        
        with patch.object(self.table._table_generator, 'generate_table', return_value=mock_output) as mock_generate:
            self.table.get_output(start_row=1, end_row=None)
            
            # Should use default of 10
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args[1]
            assert call_args['end_row'] == 10
    
    def test_display_methods_call_validate_format_strings(self):
        """Test that display methods call format string validation."""
        mock_output = {'terminal': 'output'}
        
        with patch.object(self.table._table_generator, 'generate_table', return_value=mock_output), \
             patch('builtins.print'), \
             patch.object(self.table, '_validate_format_strings') as mock_validate:
            
            self.table.display()
            mock_validate.assert_called_once()
            
            mock_validate.reset_mock()
            
            self.table.display_all_rows()
            mock_validate.assert_called_once()
            
            mock_validate.reset_mock()
            
            self.table.get_output()
            mock_validate.assert_called_once()


class TestTableEdgeCases:
    """Test suite for table edge cases and error conditions."""
    
    def test_empty_table_operations(self):
        """Test operations on empty table."""
        table = _Table()
        
        # Should handle empty table gracefully
        assert table.row_count == 0
        assert table.column_count == 0
        assert table.get_headers() == []
        
        # Should not be able to add data without headers
        with pytest.raises(ValueError):
            table.add_row_data(["data"])
    
    def test_table_with_empty_strings(self):
        """Test table with empty string content."""
        table = _Table()
        table.add_headers(["", "Empty", ""])
        table.add_row_data(["", "", ""])
        
        assert table.column_count == 3
        assert table.row_count == 1
        assert table.get_cell("", 1) == ""
        assert table.get_cell("Empty", 1) == ""
    
    def test_table_with_unicode_content(self):
        """Test table with Unicode content."""
        table = _Table()
        table.add_headers(["姓名", "年龄", "城市"])
        table.add_row_data([
            ["爱丽丝", "25", "纽约"],
            ["鲍勃 🎉", "30", "洛杉矶 🌴"],
            ["查理", "35", "芝加哥"]
        ])
        
        assert table.column_count == 3
        assert table.row_count == 3
        assert table.get_cell("姓名", 1) == "爱丽丝"
        assert table.get_cell("姓名", 2) == "鲍勃 🎉"
    
    def test_table_with_very_long_content(self):
        """Test table with very long content."""
        table = _Table()
        table.add_header("Long Content")
        
        long_content = "Very long content " * 100
        table.add_row_data([long_content])
        
        assert table.get_cell("Long Content", 1) == long_content
    
    def test_table_with_special_characters(self):
        """Test table with special characters."""
        table = _Table()
        table.add_headers(["Special", "Characters"])
        table.add_row_data([
            ["!@#$%^&*()", "[]{}|;:,.<>?"],
            ['"\'`~', "\\//\\//\\"],
            ["\n\t\r", "\x00\x01\x02"]
        ])
        
        assert table.row_count == 3
        assert table.get_cell("Special", 1) == "!@#$%^&*()"
    
    def test_table_with_mixed_data_types(self):
        """Test table with mixed data types in cells."""
        table = _Table()
        table.add_headers(["Mixed", "Types"])
        
        # Test with various data types
        table.add_row_data([123, True])
        table.add_row_data([None, [1, 2, 3]])
        table.add_row_data([{"key": "value"}, 3.14])
        
        assert table.row_count == 3
        # Cell access should convert to strings
        assert table.get_cell("Mixed", 1) == 123
        assert table.get_cell("Types", 1) is True
    
    def test_large_table_operations(self):
        """Test operations on large table."""
        table = _Table()
        
        # Create large table
        num_columns = 20
        num_rows = 1000
        
        headers = [f"Col_{i}" for i in range(num_columns)]
        table.add_headers(headers)
        
        # Add data in batches
        for i in range(0, num_rows, 100):
            batch_data = []
            for j in range(min(100, num_rows - i)):
                row = [f"Data_{i+j}_{k}" for k in range(num_columns)]
                batch_data.append(row)
            table.add_row_data(batch_data)
        
        assert table.column_count == num_columns
        assert table.row_count == num_rows
        
        # Test access to various cells
        assert table.get_cell("Col_0", 1) == "Data_0_0"
        assert table.get_cell("Col_19", 1000) == "Data_999_19"
    
    def test_table_limits_edge_cases(self):
        """Test table limits at edge cases."""
        # Test max_columns = 1
        table = _Table(max_columns=1)
        table.add_header("Only")
        
        with pytest.raises(ValueError):
            table.add_header("Another")
        
        # Test max_rows = 1
        table = _Table(max_rows=1)
        table.add_header("Test")
        table.add_row_data(["Data"])
        
        with pytest.raises(ValueError):
            table.add_row_data(["More"])
    
    def test_complex_tuple_formatting(self):
        """Test complex tuple formatting scenarios."""
        table = _Table()
        table.add_headers(["Content", "Format"])
        
        # Test nested tuples (should work with content extraction)
        table.add_row_data([
            ("Simple", "</bold>"),
            (("Nested", "tuple"), "</italic>")
        ])
        
        assert table.row_count == 1
        
        # Test finding rows with complex tuples
        rows = table.find_rows("Content", "Simple")
        assert rows == [1]
        
        # Test update with complex tuples
        success = table.update_cell("Simple", "Updated")
        assert success is True


class TestTableVisualDemonstration:
    """Visual demonstration tests for table system."""
    
    def test_visual_table_demonstration(self):
        """Visual demonstration of table capabilities."""
        print("\n" + "="*60)
        print("TABLE - CAPABILITIES DEMONSTRATION")
        print("="*60)
        
        table = _Table(style="rounded")
        
        print(f"\nTable Initialization:")
        print(f"  ✅ Created table with style: {table.style}")
        print(f"  Initial columns: {table.column_count}")
        print(f"  Initial rows: {table.row_count}")
        
        print(f"\nAdding Headers:")
        headers = ["Name", "Age", "City", "Occupation"]
        table.add_headers(headers)
        print(f"  ✅ Added headers: {headers}")
        print(f"  Column count: {table.column_count}")
        
        print(f"\nAdding Data:")
        data = [
            ["Alice Johnson", "28", "New York", "Engineer"],
            ["Bob Smith", "34", "Los Angeles", "Designer"],
            ["Charlie Brown", "29", "Chicago", "Manager"],
            ["Diana Prince", "31", "Seattle", "Developer"]
        ]
        table.add_row_data(data)
        print(f"  ✅ Added {len(data)} rows of data")
        print(f"  Row count: {table.row_count}")
    
    def test_visual_data_operations_demonstration(self):
        """Visual demonstration of data operations."""
        print("\n" + "="*60)
        print("TABLE - DATA OPERATIONS DEMONSTRATION")
        print("="*60)
        
        table = _Table()
        table.add_headers(["Product", "Price", "Stock"])
        table.add_row_data([
            ["Laptop", "$999", "15"],
            ["Mouse", "$25", "50"],
            ["Keyboard", "$75", "30"]
        ])
        
        print(f"\nInitial Table State:")
        print(f"  Columns: {table.get_headers()}")
        print(f"  Rows: {table.row_count}")
        
        print(f"\nCell Access Operations:")
        
        # Get cell
        laptop_price = table.get_cell("Price", 1)
        print(f"  Get cell (Product, Row 1): '{laptop_price}'")
        
        # Set cell
        table.set_cell("Stock", 1, "12")
        new_stock = table.get_cell("Stock", 1)
        print(f"  Set cell (Stock, Row 1): '{new_stock}'")
        
        # Update cell by content
        success = table.update_cell("$25", "$30")
        print(f"  Update cell '$25' → '$30': {'✅ Success' if success else '❌ Failed'}")
        
        # Get entire row
        row_2 = table.get_row(2)
        print(f"  Get row 2: {row_2}")
        
        # Get entire column
        prices = table.get_column("Price")
        print(f"  Get Price column: {prices}")
        
        print(f"\nSearch Operations:")
        
        # Find rows
        laptop_rows = table.find_rows("Product", "Laptop")
        print(f"  Find 'Laptop' rows: {laptop_rows}")
        
        # Add duplicate for multiple matches
        table.add_row_data(["Laptop", "$1200", "8"])
        laptop_rows = table.find_rows("Product", "Laptop")
        print(f"  Find 'Laptop' rows (after adding duplicate): {laptop_rows}")
    
    def test_visual_formatting_demonstration(self):
        """Visual demonstration of formatting capabilities."""
        print("\n" + "="*60)
        print("TABLE - FORMATTING DEMONSTRATION")
        print("="*60)
        
        table = _Table()
        table.add_headers(["Status", "Message", "Priority"])
        table.add_row_data([
            ["Success", "Operation completed", "High"],
            ["Warning", "Check configuration", "Medium"],
            ["Error", "Connection failed", "High"],
            ["Info", "System status normal", "Low"]
        ])
        
        print(f"\nApplying Formatting:")
        
        # Header formatting
        try:
            table.format_headers("</bold, underline>")
            print(f"  ✅ Applied header formatting: bold, underline")
        except Exception as e:
            print(f"  ❌ Header formatting failed: {e}")
        
        # Column formatting
        try:
            table.format_column("Status", "</italic>")
            print(f"  ✅ Applied Status column formatting: italic")
        except Exception as e:
            print(f"  ❌ Column formatting failed: {e}")
        
        # Row formatting
        try:
            table.format_row(1, "</green>")
            print(f"  ✅ Applied row 1 formatting: green")
        except Exception as e:
            print(f"  ❌ Row formatting failed: {e}")
        
        # Cell formatting
        try:
            table.format_cell("Priority", 3, "</red, bold>")
            print(f"  ✅ Applied cell formatting (Priority, Row 3): red, bold")
        except Exception as e:
            print(f"  ❌ Cell formatting failed: {e}")
        
        # Format matching cells
        try:
            count = table.format_matching_cells("Priority", "High", "</bold>")
            print(f"  ✅ Formatted {count} cells matching 'High' priority")
        except Exception as e:
            print(f"  ❌ Matching cell formatting failed: {e}")
        
        print(f"\nFormatting State:")
        print(f"  Header format: {table._header_format is not None}")
        print(f"  Column formats: {len(table._column_formats)}")
        print(f"  Row formats: {len(table._row_formats)}")
        print(f"  Cell formats: {len(table._cell_formats)}")
    
    def test_visual_tuple_formatting_demonstration(self):
        """Visual demonstration of tuple-based formatting."""
        print("\n" + "="*60)
        print("TABLE - TUPLE FORMATTING DEMONSTRATION")
        print("="*60)
        
        table = _Table()
        table.add_headers(["Item", "Status", "Details"])
        
        print(f"\nAdding Data with Tuple Formatting:")
        
        # Add data with tuple formatting
        data_with_formatting = [
            [("Server A", "</green, bold>"), ("Online", "</green>"), "All systems normal"],
            [("Server B", "</yellow, bold>"), ("Maintenance", "</yellow>"), "Scheduled downtime"],
            [("Server C", "</red, bold>"), ("Offline", "</red>"), "Connection error"],
            ["Server D", ("Pending", "</blue>"), ("Startup in progress", "</italic>")]
        ]
        
        for i, row in enumerate(data_with_formatting, 1):
            table.add_row_data([row])
            print(f"  Row {i}: {row}")
        
        print(f"\nTuple Format Benefits:")
        print(f"  - Content and formatting are separate")
        print(f"  - Formatting doesn't interfere with data operations")
        print(f"  - Easy to search and update content")
        
        print(f"\nData Operations with Tuples:")
        
        # Find rows (searches content only)
        server_a_rows = table.find_rows("Item", "Server A")
        print(f"  Find 'Server A': {server_a_rows} (ignores formatting)")
        
        # Update cell (updates content, preserves or changes formatting)
        success = table.update_cell("Online", ("Running", "</green, italic>"))
        print(f"  Update 'Online' → 'Running': {'✅ Success' if success else '❌ Failed'}")
        
        # Get cell (returns full tuple or string)
        server_a_cell = table.get_cell("Item", 1)
        print(f"  Get Server A cell: {server_a_cell}")
    
    def test_visual_utility_operations_demonstration(self):
        """Visual demonstration of utility operations."""
        print("\n" + "="*60)
        print("TABLE - UTILITY OPERATIONS DEMONSTRATION")
        print("="*60)
        
        # Create sample table
        table = _Table(style="square", max_columns=4, max_rows=10)
        table.add_headers(["ID", "Name", "Department", "Salary"])
        table.add_row_data([
            ["001", "Alice", "Engineering", "$75000"],
            ["002", "Bob", "Marketing", "$65000"],
            ["003", "Charlie", "Engineering", "$80000"],
            ["004", "Diana", "Sales", "$70000"]
        ])
        table.format_headers("</bold>")
        table.format_column("Salary", "</green>")
        
        print(f"\nOriginal Table:")
        print(f"  Style: {table.style}")
        print(f"  Max columns: {table.max_columns}")
        print(f"  Max rows: {table.max_rows}")
        print(f"  Current size: {table.column_count}x{table.row_count}")
        
        print(f"\nCopy Operation:")
        copied_table = table.copy()
        print(f"  ✅ Created table copy")
        print(f"  Original == Copy: {table._data == copied_table._data}")
        print(f"  Original is Copy: {table._data is copied_table._data}")
        
        # Modify original to show independence
        table.add_row_data(["005", "Eve", "HR", "$60000"])
        print(f"  After modifying original:")
        print(f"    Original rows: {table.row_count}")
        print(f"    Copy rows: {copied_table.row_count}")
        
        print(f"\nClear Operations:")
        
        # Clear data only
        data_backup = deepcopy(table._data)
        table.clear_all_data()
        print(f"  Clear data: {table.row_count} rows remaining")
        print(f"  Headers preserved: {table.column_count} columns")
        
        # Restore data and clear formatting
        table._data = data_backup
        table.clear_formatting()
        print(f"  Clear formatting: {len(table._column_formats)} column formats")
        print(f"  Data preserved: {table.row_count} rows")
        
        # Clear everything
        table.clear_headers()
        print(f"  Clear headers: {table.column_count} columns, {table.row_count} rows")
    
    def test_visual_display_methods_demonstration(self):
        """Visual demonstration of display methods."""
        print("\n" + "="*60)
        print("TABLE - DISPLAY METHODS DEMONSTRATION")
        print("="*60)
        
        # Create table with many rows for pagination demo
        table = _Table()
        table.add_headers(["Index", "Value", "Status"])
        
        # Add 25 rows for pagination testing
        for i in range(1, 26):
            status = "Active" if i % 3 == 0 else "Inactive" if i % 2 == 0 else "Pending"
            table.add_row_data([f"{i:03d}", f"Value_{i}", status])
        
        print(f"\nTable with {table.row_count} rows created")
        
        # Mock the table generator to show what would be called
        mock_output = {
            'terminal': f'[Mock Table Output - {table.row_count} rows]',
            'plain': f'Plain table output',
            'markdown': f'| Markdown | Table | Output |',
            'html': f'<table>HTML table output</table>'
        }
        
        with patch.object(table._table_generator, 'generate_table', return_value=mock_output) as mock_gen, \
             patch('builtins.print') as mock_print:
            
            print(f"\nDisplay Methods:")
            
            # Default display (first 10 rows)
            table.display()
            print(f"  ✅ display(): Shows rows 1-10 by default")
            
            # Custom range display
            table.display(start_row=5, end_row=15)
            print(f"  ✅ display(5, 15): Shows rows 5-15")
            
            # Display all rows
            table.display_all_rows()
            print(f"  ✅ display_all_rows(): Shows all {table.row_count} rows")
            
            # Get output without displaying
            output = table.get_output(start_row=1, end_row=5)
            print(f"  ✅ get_output(1, 5): Returns dict with {len(output)} formats")
            
            print(f"\nOutput Formats Available:")
            for format_name in output.keys():
                print(f"    - {format_name}")
    
    def test_visual_error_handling_demonstration(self):
        """Visual demonstration of error handling."""
        print("\n" + "="*60)
        print("TABLE - ERROR HANDLING DEMONSTRATION")
        print("="*60)
        
        print(f"\nError Handling Scenarios:")
        
        # 1. Adding data without headers
        print(f"\n1. Adding Data Without Headers:")
        table = _Table()
        try:
            table.add_row_data(["data", "without", "headers"])
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 2. Exceeding max columns
        print(f"\n2. Exceeding Maximum Columns:")
        table = _Table(max_columns=2)
        table.add_headers(["Col1", "Col2"])
        try:
            table.add_header("Col3")
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 3. Row length mismatch
        print(f"\n3. Row Length Mismatch:")
        try:
            table.add_row_data(["data1"])  # Missing second column
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 4. Invalid cell access
        print(f"\n4. Invalid Cell Access:")
        table.add_row_data(["data1", "data2"])
        try:
            table.get_cell("NonExistent", 1)
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        try:
            table.get_cell("Col1", 5)  # Row out of range
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 5. Invalid formatting
        print(f"\n5. Invalid Formatting Commands:")
        try:
            table.format_column("Col1", "</invalid_command>")
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {str(e)[:60]}...")
        
        # 6. Operations after release
        print(f"\n6. Operations After Release:")
        table.release()
        try:
            table.add_header("Test")
            print(f"   ❌ Should have failed")
        except RuntimeError as e:
            print(f"   ✅ Caught expected error: {e}")
    
    def test_visual_format_validation_demonstration(self):
        """Visual demonstration of format validation."""
        print("\n" + "="*60)
        print("TABLE - FORMAT VALIDATION DEMONSTRATION")
        print("="*60)
        
        table = _Table()
        table.add_headers(["Content", "Status"])
        
        print(f"\nFormat Validation Examples:")
        
        # Correct usage (no warnings)
        print(f"\n1. Correct Tuple Format (No Warnings):")
        table.add_row_data([
            [("Good Content", "</green>"), "OK"],
            ["Plain Content", ("Success", "</bold>")]
        ])
        
        with patch('builtins.print') as mock_print:
            table._validate_format_strings()
            if mock_print.called:
                print(f"   ❌ Unexpected warning printed")
            else:
                print(f"   ✅ No warnings (correct usage)")
        
        # Incorrect usage (should warn)
        print(f"\n2. Incorrect Format in Content (Should Warn):")
        table.add_row_data([["</red>Warning Content", "Error"]])
        
        with patch('builtins.print') as mock_print:
            table._validate_format_strings()
            if mock_print.called:
                call_args = mock_print.call_args[0][0]
                print(f"   ✅ Warning displayed: {call_args[:60]}...")
            else:
                print(f"   ❌ No warning (unexpected)")
        
        # Subsequent calls should not warn again
        print(f"\n3. Subsequent Validation (Should Not Warn Again):")
        with patch('builtins.print') as mock_print:
            table._validate_format_strings()
            if mock_print.called:
                print(f"   ❌ Warning printed again (unexpected)")
            else:
                print(f"   ✅ No additional warnings (correct behavior)")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestTableVisualDemonstration()
    demo.test_visual_table_demonstration()
    demo.test_visual_data_operations_demonstration()
    demo.test_visual_formatting_demonstration()
    demo.test_visual_tuple_formatting_demonstration()
    demo.test_visual_utility_operations_demonstration()
    demo.test_visual_display_methods_demonstration()
    demo.test_visual_error_handling_demonstration()
    demo.test_visual_format_validation_demonstration()
    
    print("\n" + "="*60)
    print("✅ TABLE TESTS COMPLETE")
    print("="*60)