# processors/objects/table_objects.py
"""
Table Objects Processor for FDL.

Handles table objects that display formatted tables within FDL strings.
Tables are passed as variables and referenced by name in the FDL string.
"""

from ...core.object_registry import _ObjectProcessor, _object_processor
from ...core.format_state import _FormatState
from ...classes.table import _Table


@_object_processor
class _TableObjectProcessor(_ObjectProcessor):
    """
    Processor for table objects.
    
    Handles:
    - <table_name> - Display a table object
    
    Tables are passed as variables in the values tuple and referenced
    by name in the FDL string.
    """
    
    @classmethod
    def get_supported_object_types(cls):
        """Return the set of object types this processor supports."""
        return {'table'}
    
    @classmethod
    def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
        """
        Process a table object and return the formatted table string.
        
        Args:
            obj_type: The object type (should be 'table')
            variable: Variable name (table name)
            format_state: Current format state
            
        Returns:
            str: Formatted table string
        """
        if obj_type != 'table':
            return f'[UNKNOWN_OBJECT_TYPE:{obj_type}]'
        
        # Get the table object from format state values
        if not format_state.has_more_values():
            return '[NO_TABLE_PROVIDED]'
        
        table_obj = format_state.get_next_value()
        
        # Validate that it's actually a table object
        if not isinstance(table_obj, _Table):
            return f'[INVALID_TABLE_TYPE:{type(table_obj).__name__}]'
        
        # Render the table to terminal format
        # For now, return a placeholder - full rendering will be implemented later
        return cls._render_table_to_terminal(table_obj, format_state)
    
    @classmethod
    def _render_table_to_terminal(cls, table: _Table, format_state: _FormatState) -> str:
        """
        Render a table to terminal format with ANSI codes.
        
        Args:
            table: Table object to render
            format_state: Current format state
            
        Returns:
            str: Terminal-formatted table string
        """
        if not table._headers:
            return '[EMPTY_TABLE]'
        
        if table.row_count == 0:
            return '[TABLE_NO_DATA]'
        
        # Simple rendering for now - will be enhanced later
        lines = []
        
        # Header line
        header_line = " | ".join(table._headers)
        lines.append(header_line)
        
        # Separator line
        separator = "-" * len(header_line)
        lines.append(separator)
        
        # Data rows (show up to 10 by default)
        max_rows = min(10, table.row_count)
        for i in range(max_rows):
            row_data = table.get_row(i + 1)  # 1-based
            
            # Convert cells to strings, handling tuples
            cell_strings = []
            for cell in row_data:
                if isinstance(cell, tuple):
                    # Apply tuple formatting
                    content, format_str = cell
                    # For now, just use the content - formatting will be added later
                    cell_strings.append(str(content))
                else:
                    cell_strings.append(str(cell))
            
            row_line = " | ".join(cell_strings)
            lines.append(row_line)
        
        # Add row count info if table has more rows
        if table.row_count > max_rows:
            lines.append(f"... and {table.row_count - max_rows} more rows")
        
        return "\n".join(lines)