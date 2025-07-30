# Complete Table Concept v5 - Final Implementation

## Core Design Principles

- **API-driven data management** - No direct data manipulation
- **Headers-first approach** - Must define structure before adding data
- **Clean content matching** with tuple formatting
- **Background color text-only** - No cell/border backgrounds
- **Smart display methods** with clear naming
- **Standalone feature** - Not integrated with fdl.print(), uses own display methods

## Table Creation & Header Setup

```python
from suitkaise import fdl

# Create table
table = fdl.Table(style="rounded")

# MUST set up headers first (defines table structure)
table.add_header("Component")
table.add_headers(["Status", "Usage", "Temperature"])

# Or all at once
server_table = fdl.Table(style="rounded")
server_table.add_headers(["Server", "Status", "CPU", "Memory", "Uptime"])
```

## API-Based Data Population

```python
# Add single row
table.add_row_data(["CPU", ("Critical", "</red, bold>"), "85%", "72°C"])

# Add multiple rows
table.add_row_data([
    ["GPU", "Normal", ("12%", "</green>"), "65°C"],
    ["RAM", ("Warning", "</yellow>"), "67%", "45°C"],
    ["SSD", ("Failed", "</red, blink>"), "0%", "N/A"]
])

# Remove rows by content matching (matches plain strings only)
table.remove_row_data(["CPU", "Critical", "85%", "72°C"])  # Matches plain text only

# Or remove multiple rows
table.remove_row_data([
    ["GPU", "Normal", "12%", "65°C"],
    ["RAM", "Warning", "67%", "45°C"]
])
```

## Header Management

```python
# Add new header (adds empty column to all existing rows)
table.add_header("Location")  # All existing rows get empty "" in this column

# Remove header (removes entire column and all its data)
table.remove_header("Temperature")  # Deletes column and all temperature data

# Useful for copying tables with different views
monitoring_table = fdl.Table(style="rounded")
monitoring_table.add_headers(["Server", "Status", "CPU", "Memory", "Uptime"])

# Copy for simplified view
simple_table = monitoring_table.copy()
simple_table.remove_header("Memory")    # Now only shows Server, Status, CPU, Uptime
simple_table.remove_header("Uptime")    # Now only shows Server, Status, CPU
```

## Cell Updates & Content Matching

```python
# Update by header + row position (1-based indexing)
table.set_cell(header="Status", row=3, value=("Critical", "</red, bold>"))

# Update by finding current content (matches tuple text or plain string)
table.update_cell(
    current_cell_content="GPU",  # Finds "GPU" in any cell
    new_cell_content=("Graphics Card", "</italic>")
)

# Content matching works on tuple text only
# ("GPU", "</bold>") matches search for "GPU"
# "</red>GPU</reset>" in plain string triggers format warning
```

## Tuple-Based Formatting

```python
# Clean separation of data and formatting
table.data = [
    ["Component", "Status", "Usage"],
    ["CPU", ("Critical", "</red, bold>"), "85%"],      # Formatted cell
    ["GPU", "Normal", ("12%", "</green>")],            # Formatted cell
    ["RAM", "Warning", "67%"]                          # Plain cell
]

# Or apply formatting after data creation
table.format_cell(header="Status", row=1, format="</red, bold>")
```

## Background Color Restriction

```python
# ✅ CORRECT - Background colors apply only to text content
table.add_row_data([
    ["CPU", ("Critical", "</red, bkg yellow>"), "85%"]  # Yellow background on "Critical" text only
])

table.format_column("Status", "</green, bkg blue>")  # Blue background on text in Status column

# The table cell whitespace and borders remain unchanged
# Only the actual text content gets the background color
```

## Display Methods

```python
# Default: shows rows 1-10
table.display()

# Custom range
table.display(start_row=1, end_row=20)    # Rows 1-20
table.display(start_row=25, end_row=35)   # Rows 25-35

# Show all rows (clear method name)
table.display_all_rows()  # Instead of end_row=None

# Alternative display method
table.print()  # Same as display()
table.print_all_rows()  # Same as display_all_rows()
```

## Format Validation & Warnings

```python
# ⚠️ INVALID - FDL commands in content
table.add_row_data([
    ["CPU", "</red>Critical</reset>", "85%"]  # ❌ Wrong!
])

# When table.display() is called (once per display session):
# Warning: FDL commands detected in cell content "</red>Critical</reset>". 
# Use tuple format: ("Critical", "</red>") instead.

# ✅ CORRECT - Tuple format
table.add_row_data([
    ["CPU", ("Critical", "</red>"), "85%"]  # ✅ Right!
])
```

## Formatting Methods

```python
# Column formatting (applies to all cells in column)
table.format_column("Status", "</green, bold>")
table.format_column("Usage", "warning_format")  # By format name

# Row formatting (applies to all cells in row)
table.format_row(3, "</italic>")

# Cell formatting (highest priority after tuples)
table.format_cell(header="Temperature", row=2, format="</yellow>")

# Header formatting
table.format_headers("</underline, bold>")

# Reset methods
table.reset_formatting()                           # Everything
table.reset_column_formatting("Status")            # Specific column
table.reset_row_formatting(5)                      # Specific row
table.reset_cell_formatting(header="Usage", row=3) # Specific cell
table.reset_header_formatting()                    # Just headers
```

## Formatting Priority System

```python
# Priority order (highest to lowest):
# 1. Tuple formatting
table.data[1][1] = ("Critical", "</red, bold>")

# 2. Cell formatting  
table.format_cell(header="Status", row=1, format="</green>")

# 3. Column formatting
table.format_column("Status", "</blue>")

# 4. Row formatting (lowest)
table.format_row(1, "</italic>")

# Result: "Critical" displays as red/bold (tuple wins)
```

## Properties

```python
# Property methods (not function calls)
total_rows = table.row_count        # Number of data rows
total_cols = table.column_count     # Number of columns
headers = table.header_count        # Alias for column_count
```

## Advanced API Methods

```python
# Table information
headers = table.get_headers()         # Returns ["Server", "Status", ...]

# Cell access
table.get_cell(header="Status", row=2)  # Get specific cell
table.get_row(3)                        # Get entire row
table.get_column("Status")              # Get entire column

# Find operations
critical_rows = table.find_rows(header="Status", content="Critical")
# Returns list of row numbers where Status content = "Critical"

# Bulk operations
table.format_matching_cells(
    header="Status", 
    content="Critical", 
    format="</red, bold, blink>"
)

# Clear operations
table.clear_all_data()        # Removes all rows, keeps headers
table.clear_formatting()      # Removes all formatting, keeps data
table.clear_headers()         # Removes headers and all data (reset table)

# Memory management
table.release()               # Releases table from memory (new requirement)
```

## Table Generation System

### Cell Dimension Rules
- **30 character limit** per cell (left edge to right edge)
- **1 space padding** on each side (26 usable characters)
- **Text wrapping** at 26 characters using text wrapper
- **Visual width calculation** using wcwidth for Unicode/emojis
- **Row height** determined by tallest cell in that row
- **Column width** determined by widest cell in that column

### Pseudo Matrix System
Each cell contains:
- Cell dimensions (width, height)
- Original plain string content
- Original formatting string (from tuple)
- Format state for the cell (combined from tuple + column + row + cell formatting)
- Formatted and wrapped string output
- Visual width calculations

### Format State Integration
- **Column format states** - Store column-wide formatting
- **Row format states** - Store row-wide formatting  
- **Cell format states** - Combined formatting from all sources
- **Priority system** - Tuple > Cell > Column > Row

### Multi-Format Output
All display methods generate 4 output streams:
- **Terminal**: ANSI formatted table with proper box borders
- **Plain**: Clean text table without formatting
- **Markdown**: `| Header | Header |` table format
- **HTML**: `<table><tr><td>` with CSS classes

## Complete Working Example

```python
from suitkaise import fdl

# Create server monitoring table
server_table = fdl.Table(style="rounded")

# Define structure first
server_table.add_headers(["Server", "Status", "CPU", "Memory", "Uptime"])

# Add data rows
server_table.add_row_data([
    ["Web-01", "Running", "45%", "2.1GB", "15 days"],
    ["Web-02", ("Critical", "</red, bold>"), ("89%", "</yellow, bkg red>"), "3.8GB", "2 days"],
    ["DB-01", "Running", "78%", "15.2GB", "45 days"],
    ["DB-02", ("Maintenance", "</orange, italic>"), "5%", "1.2GB", "0 days"],
    ["Cache-01", ("Stopped", "</red>"), "0%", "512MB", "0 days"]
])

# Add more servers one by one
server_table.add_row_data(["Load-01", ("Online", "</green>"), ("12%", "</cyan>"), "8GB", "30 days"])

# Update existing data
server_table.update_cell(
    current_cell_content="Cache-01", 
    new_cell_content=("Cache-Primary", "</bold>")
)

server_table.set_cell(header="Status", row=2, value=("Recovered", "</green, bold>"))

# Apply formatting
server_table.format_headers("</bold, underline>")
server_table.format_column("CPU", "</cyan>")
server_table.format_column("Memory", "</blue>")

# Display first 5 rows
server_table.display(start_row=1, end_row=5)

# Clean up memory when done
server_table.release()
```

## Key Benefits

✅ **Error Prevention** - API prevents malformed data structures  
✅ **Headers-First Design** - Clear table structure before data  
✅ **Safe Content Matching** - Match on content, preserve formatting  
✅ **Flexible Views** - Copy and modify tables for different audiences  
✅ **Clear Display Options** - Explicit methods for different ranges  
✅ **Text-Only Backgrounds** - Proper background color handling  
✅ **Format Validation** - Helps users adopt correct tuple format  
✅ **Smart Cell Sizing** - Automatic width/height calculation with wrapping  
✅ **Visual Width Aware** - Proper Unicode and emoji support  
✅ **Multi-Format Output** - Terminal, plain, markdown, HTML support  
✅ **Memory Management** - Explicit resource cleanup with release()  
✅ **Standalone System** - Independent of fdl.print() for dedicated table display  

This API-driven approach eliminates user errors while providing maximum flexibility for table creation, management, and display with proper resource management and multi-format output support.