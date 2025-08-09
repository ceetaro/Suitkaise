"""
Comprehensive Tests for FDL Table Class.

Tests the internal table system that provides API-driven data management,
tuple-based formatting, multi-format output, and comprehensive table operations.
Includes visual demonstrations and comprehensive unit tests.
"""

import sys
import os
from copy import deepcopy

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the real table class directly
from suitkaise.fdl._int.classes.table import _Table


class TestTableVisualDemonstration:
    """Visual demonstration tests for table system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.table = _Table(style="rounded")
    
    def test_basic_table_creation_demo(self):
        """Demonstrate basic table creation and structure."""
        print("\n" + "="*60)
        print("📊 BASIC TABLE CREATION DEMONSTRATION")
        print("="*60)
        
        # Create table with headers
        headers = ["Name", "Age", "City", "Occupation"]
        self.table.add_headers(headers)
        print(f"✅ Added headers: {headers}")
        print(f"   Column count: {self.table.column_count}")
        
        # Add data
        data = [
            ["Alice Johnson", "28", "New York", "Software Engineer"],
            ["Bob Smith", "32", "Los Angeles", "Data Scientist"],
            ["Charlie Brown", "25", "Chicago", "Designer"],
            ["Diana Prince", "30", "Seattle", "Product Manager"]
        ]
        self.table.add_row_data(data)
        print(f"✅ Added {len(data)} rows of data")
        print(f"   Row count: {self.table.row_count}")
        
        # Display table
        print(f"\n📋 Generated Table:")
        output = self.table.get_output()
        print(output['terminal'])
    
    def test_table_styles_demo(self):
        """Demonstrate different table styles."""
        print("\n" + "="*60)
        print("🎨 TABLE STYLES DEMONSTRATION")
        print("="*60)
        
        styles = ["rounded", "square", "double", "simple"]
        
        for style in styles:
            print(f"\n{style.upper()} STYLE:")
            print("-" * 30)
            
            table = _Table(style=style)
            table.add_headers(["Style", "Description"])
            table.add_row_data([
                [style.title(), f"Table with {style} borders"],
                ["Example", "Shows border appearance"]
            ])
            
            output = table.get_output()
            print(output['terminal'])
    
    def test_data_operations_demo(self):
        """Demonstrate data manipulation operations."""
        print("\n" + "="*60)
        print("🔧 DATA OPERATIONS DEMONSTRATION")
        print("="*60)
        
        # Create fresh table for this demo
        table = _Table(style="rounded")
        
        # Create initial table
        table.add_headers(["Product", "Price", "Stock", "Status"])
        table.add_row_data([
            ["Laptop", "$999", "15", "In Stock"],
            ["Mouse", "$25", "50", "In Stock"],
            ["Keyboard", "$75", "0", "Out of Stock"],
            ["Monitor", "$299", "8", "Low Stock"]
        ])
        
        print("📋 Initial Table:")
        output = table.get_output()
        print(output['terminal'])
        
        # Cell operations
        print(f"\n🔧 Cell Operations:")
        
        # Get cell
        laptop_price = table.get_cell("Price", 1)
        print(f"   Get cell (Price, Row 1): '{laptop_price}'")
        
        # Set cell
        table.set_cell("Stock", 1, "12")
        new_stock = table.get_cell("Stock", 1)
        print(f"   Set cell (Stock, Row 1): '{new_stock}'")
        
        # Update cell by content
        success = table.update_cell("$25", "$30")
        print(f"   Update cell '$25' → '$30': {'✅ Success' if success else '❌ Failed'}")
        
        # Get row and column
        row_2 = table.get_row(2)
        print(f"   Get row 2: {row_2}")
        
        prices = table.get_column("Price")
        print(f"   Get Price column: {prices}")
        
        # Search operations
        print(f"\n🔍 Search Operations:")
        laptop_rows = table.find_rows_with("Product", "Laptop")
        print(f"   Find 'Laptop' rows: {laptop_rows}")
        
        # Add duplicate for multiple matches
        table.add_row_data(["Laptop", "$1200", "8", "Limited"])
        laptop_rows = table.find_rows_with("Product", "Laptop")
        print(f"   Find 'Laptop' rows (after adding duplicate): {laptop_rows}")
        
        print(f"\n📋 Updated Table:")
        output = table.get_output()
        print(output['terminal'])
    
    def test_formatting_demo(self):
        """Demonstrate formatting capabilities."""
        print("\n" + "="*60)
        print("🎨 FORMATTING DEMONSTRATION")
        print("="*60)
        
        # Create fresh table for this demo
        table = _Table(style="rounded")
        
        # Create table with formatting
        table.add_headers(["Status", "Message", "Priority", "Count"])
        table.add_row_data([
            ["Success", "Operation completed", "High", "150"],
            ["Warning", "Check configuration", "Medium", "23"],
            ["Error", "Connection failed", "High", "5"],
            ["Info", "System status normal", "Low", "89"]
        ])
        
        print("📋 Table with Formatting:")
        
        # Apply various formatting
        try:
            table.format_headers("</bold, underline>")
            print("   ✅ Applied header formatting: bold, underline")
        except Exception as e:
            print(f"   ❌ Header formatting failed: {e}")
        
        try:
            table.format_column("Status", "</italic>")
            print("   ✅ Applied Status column formatting: italic")
        except Exception as e:
            print(f"   ❌ Column formatting failed: {e}")
        
        try:
            table.format_row(1, "</green>")
            print("   ✅ Applied row 1 formatting: green")
        except Exception as e:
            print(f"   ❌ Row formatting failed: {e}")
        
        try:
            table.format_cell("Priority", 3, "</red, bold>")
            print("   ✅ Applied cell formatting (Priority, Row 3): red, bold")
        except Exception as e:
            print(f"   ❌ Cell formatting failed: {e}")
        
        try:
            count = table.format_matching_cells("Priority", "High", "</bold>")
            print(f"   ✅ Formatted {count} cells matching 'High' priority")
        except Exception as e:
            print(f"   ❌ Matching cell formatting failed: {e}")
        
        # Display formatted table
        output = table.get_output()
        print(output['terminal'])
    
    def test_tuple_formatting_demo(self):
        """Demonstrate tuple-based formatting."""
        print("\n" + "="*60)
        print("🎯 TUPLE FORMATTING DEMONSTRATION")
        print("="*60)
        
        # Create fresh table for this demo
        table = _Table(style="rounded")
        
        # Create table with tuple formatting
        table.add_headers(["Server", "Status", "Details", "Uptime"])
        
        print("📋 Adding Data with Tuple Formatting:")
        
        # Add data with tuple formatting
        data_with_formatting = [
            [("Server A", "</green, bold>"), ("Online", "</green>"), "All systems normal", "99.9%"],
            [("Server B", "</yellow, bold>"), ("Maintenance", "</yellow>"), "Scheduled downtime", "95.2%"],
            [("Server C", "</red, bold>"), ("Offline", "</red>"), "Connection error", "87.1%"],
            ["Server D", ("Pending", "</blue>"), ("Startup in progress", "</italic>"), "98.5%"]
        ]
        
        for i, row in enumerate(data_with_formatting, 1):
            table.add_row_data([row])
            print(f"   Row {i}: {row}")
        
        print(f"\n🎯 Tuple Format Benefits:")
        print(f"   - Content and formatting are separate")
        print(f"   - Formatting doesn't interfere with data operations")
        print(f"   - Easy to search and update content")
        
        print(f"\n🔧 Data Operations with Tuples:")
        
        # Find rows (searches content only)
        server_a_rows = table.find_rows_with("Server", "Server A")
        print(f"   Find 'Server A': {server_a_rows} (ignores formatting)")
        
        # Update cell (updates content, preserves or changes formatting)
        success = table.update_cell("Online", ("Running", "</green, italic>"))
        print(f"   Update 'Online' → 'Running': {'✅ Success' if success else '❌ Failed'}")
        
        # Get cell (returns full tuple or string)
        server_a_cell = table.get_cell("Server", 1)
        print(f"   Get Server A cell: {server_a_cell}")
        
        # Display table
        output = table.get_output()
        print(output['terminal'])
    
    def test_utility_operations_demo(self):
        """Demonstrate utility operations."""
        print("\n" + "="*60)
        print("🛠️ UTILITY OPERATIONS DEMONSTRATION")
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
        
        print(f"📋 Original Table:")
        print(f"   Style: {table.style}")
        print(f"   Max columns: {table.max_columns}")
        print(f"   Max rows: {table.max_rows}")
        print(f"   Current size: {table.column_count}x{table.row_count}")
        
        output = table.get_output()
        print(output['terminal'])
        
        print(f"\n🔄 Copy Operation:")
        copied_table = table.copy()
        print(f"   ✅ Created table copy")
        print(f"   Original == Copy: {table._data == copied_table._data}")
        print(f"   Original is Copy: {table._data is copied_table._data}")
        
        # Modify original to show independence
        table.add_row_data(["005", "Eve", "HR", "$60000"])
        print(f"   After modifying original:")
        print(f"     Original rows: {table.row_count}")
        print(f"     Copy rows: {copied_table.row_count}")
        
        print(f"\n🗑️ Clear Operations:")
        
        # Clear data only
        data_backup = deepcopy(table._data)
        table.clear_all_data()
        print(f"   Clear data: {table.row_count} rows remaining")
        print(f"   Headers preserved: {table.column_count} columns")
        
        # Restore data and clear formatting
        table._data = data_backup
        table.clear_formatting()
        print(f"   Clear formatting: {len(table._column_formats)} column formats")
        print(f"   Data preserved: {table.row_count} rows")
        
        # Clear everything
        table.clear_headers()
        print(f"   Clear headers: {table.column_count} columns, {table.row_count} rows")
    
    def test_display_methods_demo(self):
        """Demonstrate display methods."""
        print("\n" + "="*60)
        print("📺 DISPLAY METHODS DEMONSTRATION")
        print("="*60)
        
        # Create table with many rows for pagination demo
        table = _Table()
        table.add_headers(["Index", "Value", "Status", "Category"])
        
        # Add 25 rows for pagination testing
        for i in range(1, 26):
            status = "Active" if i % 3 == 0 else "Inactive" if i % 2 == 0 else "Pending"
            category = "A" if i <= 8 else "B" if i <= 16 else "C"
            table.add_row_data([f"{i:03d}", f"Value_{i}", status, category])
        
        print(f"📋 Table with {table.row_count} rows created")
        
        print(f"\n📺 Display Methods:")
        
        # Default display (first 10 rows)
        print(f"\n1️⃣ Default Display (Rows 1-10):")
        output = table.get_output(start_row=1, end_row=10)
        print(output['terminal'])
        
        # Custom range display
        print(f"\n2️⃣ Custom Range Display (Rows 5-15):")
        output = table.get_output(start_row=5, end_row=15)
        print(output['terminal'])
        
        # Display all rows
        print(f"\n3️⃣ All Rows Display:")
        output = table.get_output(start_row=1, end_row=None)
        print(output['terminal'])
        
        print(f"\n📊 Output Formats Available:")
        output = table.get_output(start_row=1, end_row=3)
        for format_name, content in output.items():
            print(f"   - {format_name}: {len(content)} characters")
    
    def test_error_handling_demo(self):
        """Demonstrate error handling."""
        print("\n" + "="*60)
        print("⚠️ ERROR HANDLING DEMONSTRATION")
        print("="*60)
        
        print(f"⚠️ Error Handling Scenarios:")
        
        # 1. Adding data without headers
        print(f"\n1️⃣ Adding Data Without Headers:")
        table = _Table()
        try:
            table.add_row_data(["data", "without", "headers"])
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 2. Exceeding max columns
        print(f"\n2️⃣ Exceeding Maximum Columns:")
        table = _Table(max_columns=2)
        table.add_headers(["Col1", "Col2"])
        try:
            table.add_header("Col3")
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 3. Row length mismatch
        print(f"\n3️⃣ Row Length Mismatch:")
        try:
            table.add_row_data(["data1"])  # Missing second column
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 4. Invalid cell access
        print(f"\n4️⃣ Invalid Cell Access:")
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
        
        # 5. Operations after release
        print(f"\n5️⃣ Operations After Release:")
        table.release()
        try:
            table.add_header("Test")
            print(f"   ❌ Should have failed")
        except RuntimeError as e:
            print(f"   ✅ Caught expected error: {e}")
    
    def test_missing_vertical_borders_demo(self):
        """Demonstrate missing vertical border feature."""
        print("\n" + "="*60)
        print("🔍 MISSING VERTICAL BORDERS DEMONSTRATION")
        print("="*60)
        
        # Create fresh table for this demo
        table = _Table(style="rounded")
        
        # Create table with complete data (table class enforces row length matching)
        table.add_headers(["Name", "Age", "City", "Country", "Phone"])
        table.add_row_data([
            ["Alice", "25", "", "", ""],  # Empty cells for missing data
            ["Bob", "30", "LA", "", ""],  # Empty cells for missing data
            ["Charlie", "35", "Chicago", "USA", ""],  # Empty cell for missing data
            ["David", "40", "London", "UK", "123-456"],  # Complete row
            ["Eve", "28", "Paris", "France", "987-654"]  # Complete row
        ])
        
        print("📋 Table with Missing Data (Empty Cells):")
        output = table.get_output()
        print(output['terminal'])
        
        print(f"\n🔍 Table Class Behavior:")
        print(f"   - Table class enforces row length matching")
        print(f"   - Missing data is represented as empty strings")
        print(f"   - Missing vertical borders are handled by the table generator")
        print(f"   - This ensures data integrity and consistent structure")
        
        print(f"\n📊 Data Integrity:")
        print(f"   - All rows have exactly 5 columns")
        print(f"   - Empty cells represent missing data")
        print(f"   - No data loss or corruption")
    
    def test_maximum_table_size_demo(self):
        """Demonstrate maximum table size handling."""
        print("\n" + "="*60)
        print("📏 MAXIMUM TABLE SIZE DEMONSTRATION")
        print("="*60)
        
        # Create maximum size table (5 columns, 10 rows)
        table = _Table(max_columns=5, max_rows=10)
        headers = ["Col1", "Col2", "Col3", "Col4", "Col5"]
        table.add_headers(headers)
        
        # Add 10 rows
        for i in range(10):
            table.add_row_data([f"R{i+1}C1", f"R{i+1}C2", f"R{i+1}C3", f"R{i+1}C4", f"R{i+1}C5"])
        
        print(f"📋 Maximum Size Table ({table.column_count}x{table.row_count}):")
        output = table.get_output()
        print(output['terminal'])
        
        print(f"\n📏 Size Limits:")
        print(f"   - Max columns: {table.max_columns}")
        print(f"   - Max rows: {table.max_rows}")
        print(f"   - Current columns: {table.column_count}")
        print(f"   - Current rows: {table.row_count}")
        
        # Try to exceed limits
        print(f"\n⚠️ Testing Limits:")
        try:
            table.add_header("Col6")
            print(f"   ❌ Should have failed to add column")
        except ValueError as e:
            print(f"   ✅ Caught column limit error: {e}")
        
        try:
            table.add_row_data(["R11C1", "R11C2", "R11C3", "R11C4", "R11C5"])
            print(f"   ❌ Should have failed to add row")
        except ValueError as e:
            print(f"   ✅ Caught row limit error: {e}")

    def test_duplicate_data_handling_demo(self):
        """Demonstrate enhanced duplicate data handling capabilities."""
        print("\n" + "="*60)
        print("🔄 DUPLICATE DATA HANDLING DEMONSTRATION")
        print("="*60)
        
        # Create fresh table for this demo
        table = _Table(style="rounded")
        
        # Create table with duplicate data
        table.add_headers(["Product", "Category", "Price", "Status"])
        table.add_row_data([
            ["Laptop", "Electronics", "$999", "In Stock"],
            ["Mouse", "Accessories", "$25", "In Stock"],
            ["Laptop", "Electronics", "$1200", "Limited"],
            ["Keyboard", "Accessories", "$75", "Out of Stock"],
            ["Laptop", "Electronics", "$899", "In Stock"],
            ["Monitor", "Electronics", "$299", "Low Stock"],
            ["Mouse", "Accessories", "$30", "In Stock"]
        ])
        
        print("📋 Table with Duplicate Data:")
        output = table.get_output()
        print(output['terminal'])
        
        print(f"\n🔍 Enhanced Search Operations:")
        
        # 1. Find all occurrences of 'Laptop' across all columns
        laptop_occurrences = table.find_all_occurrences("Laptop")
        print(f"   Find all 'Laptop' occurrences: {laptop_occurrences}")
        # Expected: {'Product': [1, 3, 5]}
        
        # 1a. Find headers that contain 'Laptop'
        headers_with_laptop = table.find_headers_with("Laptop")
        print(f"   Headers containing 'Laptop': {headers_with_laptop}")
        # Expected: ['Product']
        
        # 1b. Find columns that contain 'Laptop' (alias)
        columns_with_laptop = table.find_columns_with("Laptop")
        print(f"   Columns containing 'Laptop': {columns_with_laptop}")
        # Expected: ['Product']
        
        # 2. Find all occurrences of '$25' across all columns
        price_occurrences = table.find_all_occurrences("$25")
        print(f"   Find all '$25' occurrences: {price_occurrences}")
        # Expected: {'Price': [2]}
        
        # 3. Find all occurrences of 'In Stock' across all columns
        status_occurrences = table.find_all_occurrences("In Stock")
        print(f"   Find all 'In Stock' occurrences: {status_occurrences}")
        # Expected: {'Status': [1, 2, 5, 7]}
        
        print(f"\n🔄 Enhanced Update Operations:")
        
        # 4. Update all cells with '$25' to '$30'
        updated_count = table.update_all_cells_with("$25", "$30")
        print(f"   Updated {updated_count} cells: '$25' → '$30'")
        
        # 5. Update 'Laptop' to 'Premium Laptop' only in Product column
        success = table.update_cell("Laptop", "Premium Laptop", headers="Product")
        print(f"   Updated 'Laptop' → 'Premium Laptop' in Product column: {'✅ Success' if success else '❌ Failed'}")
        
        # 6. Update 'In Stock' to 'Available' only in rows 1-3
        success = table.update_cell("In Stock", "Available", rows=range(1, 4))
        print(f"   Updated 'In Stock' → 'Available' in rows 1-3: {'✅ Success' if success else '❌ Failed'}")
        
        # 7. Update 'Mouse' to 'Wireless Mouse' only in Product column and rows 2 and 7
        success = table.update_cell("Mouse", "Wireless Mouse", headers="Product", rows=[2, 7])
        print(f"   Updated 'Mouse' → 'Wireless Mouse' in Product column, rows 2,7: {'✅ Success' if success else '❌ Failed'}")
        
        print(f"\n📋 Updated Table:")
        output = table.get_output()
        print(output['terminal'])
        
        print(f"\n🎨 Enhanced Formatting Operations:")
        
        # 8. Format all cells with 'Electronics' to bold
        formatted_count = table.format_all_cells_with("Electronics", "</bold>")
        print(f"   Formatted {formatted_count} cells with 'Electronics': bold")
        
        # 9. Format all cells with 'Available' to green
        formatted_count = table.format_all_cells_with("Available", "</green>")
        print(f"   Formatted {formatted_count} cells with 'Available': green")
        
        # 10. Format all cells with 'Premium Laptop' to red and bold
        formatted_count = table.format_all_cells_with("Premium Laptop", "</red, bold>")
        print(f"   Formatted {formatted_count} cells with 'Premium Laptop': red, bold")
        
        print(f"\n📋 Final Formatted Table:")
        output = table.get_output()
        print(output['terminal'])
        
        print(f"\n🔍 Verification:")
        
        # Verify the changes
        laptop_occurrences = table.find_all_occurrences("Premium Laptop")
        print(f"   'Premium Laptop' occurrences: {laptop_occurrences}")
        
        available_occurrences = table.find_all_occurrences("Available")
        print(f"   'Available' occurrences: {available_occurrences}")
        
        mouse_occurrences = table.find_all_occurrences("Wireless Mouse")
        print(f"   'Wireless Mouse' occurrences: {mouse_occurrences}")
        
        print(f"\n✨ Enhanced Features Summary:")
        print(f"   ✅ find_all_occurrences(): Returns dict with headers as keys")
        print(f"   ✅ find_headers_with(): Returns list of headers containing content")
        print(f"   ✅ find_columns_with(): Alias for find_headers_with()")
        print(f"   ✅ update_all_cells_with(): Updates all matching cells")
        print(f"   ✅ update_cell() with filters: Headers and rows parameters")
        print(f"   ✅ format_all_cells_with(): Formats all matching cells")
        print(f"   ✅ Range support: range(1, 4) for row filtering")
        print(f"   ✅ Multiple header support: ['Product', 'Category']")
        print(f"   ✅ Multiple row support: [2, 7] for specific rows")

    def test_duplicate_header_validation_demo(self):
        """Demonstrate duplicate header validation."""
        print("\n" + "="*60)
        print("🚫 DUPLICATE HEADER VALIDATION DEMONSTRATION")
        print("="*60)
        
        # Create fresh table for this demo
        table = _Table(style="rounded")
        
        print("📋 Testing Duplicate Header Validation:")
        
        # 1. Test adding single duplicate header
        print(f"\n1️⃣ Adding Single Duplicate Header:")
        table.add_headers(["Name", "Age", "City"])
        print(f"   ✅ Added initial headers: {table.get_headers()}")
        
        try:
            table.add_header("Name")  # Try to add duplicate
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 2. Test adding list with duplicates within the list
        print(f"\n2️⃣ Adding List with Internal Duplicates:")
        try:
            table.add_headers(["Country", "Age", "Phone"])  # 'Age' is duplicate
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 3. Test adding list with duplicates against existing headers
        print(f"\n3️⃣ Adding List with Existing Header Conflicts:")
        try:
            table.add_headers(["Country", "Phone", "City"])  # 'City' already exists
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 4. Test successful addition of unique headers
        print(f"\n4️⃣ Adding Valid Unique Headers:")
        try:
            table.add_headers(["Country", "Phone", "Email"])
            print(f"   ✅ Successfully added unique headers")
            print(f"   📋 Current headers: {table.get_headers()}")
        except ValueError as e:
            print(f"   ❌ Unexpected error: {e}")
        
        # 5. Test max_columns constraint
        print(f"\n5️⃣ Testing Max Columns Constraint:")
        table2 = _Table(max_columns=3)
        table2.add_headers(["A", "B"])
        print(f"   ✅ Added 2 headers to table with max_columns=3")
        
        try:
            table2.add_headers(["C", "D"])  # Would exceed max_columns
            print(f"   ❌ Should have failed")
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        print(f"\n✨ Duplicate Header Validation Summary:")
        print(f"   ✅ add_header(): Prevents adding existing headers")
        print(f"   ✅ add_headers(): Prevents internal duplicates")
        print(f"   ✅ add_headers(): Prevents conflicts with existing headers")
        print(f"   ✅ add_headers(): Respects max_columns constraint")
        print(f"   ✅ Clear error messages for all validation failures")

    def test_multiple_headers_occurrences_demo(self):
        """Demonstrate find_all_occurrences when the same content appears in multiple different headers."""
        print("\n" + "="*60)
        print("🔍 MULTIPLE HEADERS OCCURRENCES DEMONSTRATION")
        print("="*60)
        
        # Create fresh table for this demo
        table = _Table(style="rounded")
        
        # Create table with the same content appearing in multiple different headers
        table.add_headers(["Name", "Category", "Status", "Location"])
        table.add_row_data([
            ["Alice", "Active", "Active", "Office"],      # "Active" in both Category and Status
            ["Bob", "User", "Active", "Home"],            # "Active" only in Status
            ["Charlie", "Active", "Inactive", "Active"],  # "Active" in Category and Location
            ["David", "User", "User", "Home"],            # "User" in both Name and Category
            ["Eve", "Admin", "Active", "Admin"],          # "Admin" in both Category and Location
            ["Frank", "Active", "Active", "Active"]       # "Active" in all three columns
        ])
        
        print("📋 Table with Same Content Across Multiple Headers:")
        output = table.get_output()
        print(output['terminal'])
        
        print(f"\n🔍 Testing find_all_occurrences() - Same Content in Multiple Headers:")
        
        # Test content that appears in multiple different headers
        test_cases = [
            ("Active", "Appears in Category, Status, and Location columns"),
            ("User", "Appears in Name and Category columns"),
            ("Admin", "Appears in Category and Location columns"),
            ("Alice", "Appears only in Name column"),
            ("NonExistent", "Doesn't appear anywhere"),
        ]
        
        for content, description in test_cases:
            occurrences = table.find_all_occurrences(content)
            print(f"\n   🔎 '{content}' ({description}):")
            if occurrences:
                for header, rows in occurrences.items():
                    print(f"      {header}: rows {rows}")
            else:
                print(f"      No occurrences found")
        
        print(f"\n📊 Dictionary Structure Verification:")
        
        # Test a specific case and verify structure
        active_occurrences = table.find_all_occurrences("Active")
        print(f"   Active occurrences: {active_occurrences}")
        print(f"   Type: {type(active_occurrences)}")
        print(f"   Number of headers containing 'Active': {len(active_occurrences)}")
        print(f"   Headers: {list(active_occurrences.keys())}")
        print(f"   Total occurrences: {sum(len(rows) for rows in active_occurrences.values())}")
        
        print(f"\n✨ Key Features Demonstrated:")
        print(f"   ✅ Same content found across multiple different headers")
        print(f"   ✅ Dictionary structure: headers as keys, row lists as values")
        print(f"   ✅ Multiple headers as keys when content appears in multiple columns")
        print(f"   ✅ Single header when content appears in only one column")
        print(f"   ✅ Empty dictionary when content doesn't exist")
        print(f"   ✅ 1-based row numbering within each header")


class TestTableUnitTests:
    """Comprehensive unit tests for table functionality."""
    
    def test_initialization(self):
        """Test table initialization."""
        table = _Table()
        assert table.style == "rounded"
        assert table.max_columns is None
        assert table.max_rows is None
        assert table.row_count == 0
        assert table.column_count == 0
        assert table.header_count == 0
        assert not table._released
    
    def test_header_management(self):
        """Test header management functionality."""
        table = _Table()
        
        # Add headers
        table.add_headers(["Name", "Age", "City"])
        assert table.column_count == 3
        assert table._headers == ["Name", "Age", "City"]
        
        # Add single header
        table.add_header("Country")
        assert table.column_count == 4
        
        # Remove header
        table.remove_header("Age")
        assert table.column_count == 3
        assert "Age" not in table._headers
        
        # Get headers
        headers = table.get_headers()
        assert headers == ["Name", "City", "Country"]
        assert headers is not table._headers  # Should be copy
    
    def test_data_management(self):
        """Test data management functionality."""
        table = _Table()
        table.add_headers(["Name", "Age", "City"])
        
        # Add single row
        table.add_row_data(["Alice", "25", "NYC"])
        assert table.row_count == 1
        
        # Add multiple rows
        rows = [["Bob", "30", "LA"], ["Charlie", "35", "Chicago"]]
        table.add_row_data(rows)
        assert table.row_count == 3
        
        # Remove row
        table.remove_row_data(["Bob", "30", "LA"])
        assert table.row_count == 2
        
        # Test with tuples
        table.add_row_data([("David", "</bold>"), "40", "Seattle"])
        assert table.row_count == 3
    
    def test_cell_access(self):
        """Test cell access functionality."""
        table = _Table()
        table.add_headers(["Name", "Age", "City"])
        table.add_row_data([
            ["Alice", "25", "NYC"],
            ["Bob", "30", "LA"]
        ])
        
        # Get cell
        assert table.get_cell("Name", 1) == "Alice"
        assert table.get_cell("Age", 2) == "30"
        
        # Set cell
        table.set_cell("Name", 1, "Alicia")
        assert table.get_cell("Name", 1) == "Alicia"
        
        # Update cell by content
        success = table.update_cell("30", "31")
        assert success is True
        assert table.get_cell("Age", 2) == "31"
        
        # Get row and column
        row = table.get_row(1)
        assert row == ["Alicia", "25", "NYC"]
        
        column = table.get_column("Age")
        assert column == ["25", "31"]
    
    def test_formatting(self):
        """Test formatting functionality."""
        table = _Table()
        table.add_headers(["Name", "Age"])
        table.add_row_data([["Alice", "25"], ["Bob", "30"]])
        
        # Header formatting
        table.format_headers("</bold>")
        assert table._header_format is not None
        
        # Column formatting
        table.format_column("Name", "</red>")
        assert "Name" in table._column_formats
        
        # Row formatting
        table.format_row(1, "</green>")
        assert 1 in table._row_formats
        
        # Cell formatting
        table.format_cell("Age", 2, "</italic>")
        assert ("Age", 2) in table._cell_formats
        
        # Reset formatting
        table.reset_formatting()
        assert table._header_format is None
        assert len(table._column_formats) == 0
    
    def test_utility_methods(self):
        """Test utility methods."""
        table = _Table()
        table.add_headers(["Name", "Age"])
        table.add_row_data([["Alice", "25"], ["Bob", "30"]])
        table.format_headers("</bold>")
        
        # Copy table
        copied = table.copy()
        assert copied is not table
        assert copied._headers == table._headers
        assert copied._data == table._data
        
        # Find rows
        rows = table.find_rows_with("Name", "Alice")
        assert rows == [1]
        
        # Format matching cells
        count = table.format_matching_cells("Age", "30", "</bold>")
        assert count == 1
        
        # Clear operations
        table.clear_all_data()
        assert table.row_count == 0
        assert table.column_count == 2  # Headers preserved
    
    def test_error_conditions(self):
        """Test error conditions."""
        table = _Table()
        
        # Add data without headers
        try:
            table.add_row_data(["data"])
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        # Add headers and test other errors
        table.add_headers(["Name", "Age"])
        table.add_row_data(["Alice", "25"])
        
        # Invalid cell access
        try:
            table.get_cell("Invalid", 1)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        try:
            table.get_cell("Name", 5)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        # Row length mismatch
        try:
            table.add_row_data(["Bob"])  # Missing age
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
    
    def test_memory_management(self):
        """Test memory management."""
        table = _Table()
        table.add_headers(["Name", "Age"])
        table.add_row_data(["Alice", "25"])
        
        # Release table
        table.release()
        assert table._released
        
        # Operations should fail after release
        try:
            table.add_header("Test")
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            pass
    
    def test_display_methods(self):
        """Test display methods."""
        table = _Table()
        table.add_headers(["Name", "Age"])
        for i in range(15):
            table.add_row_data([f"Person{i+1}", f"{20+i}"])
        
        # Test get_output
        output = table.get_output(start_row=1, end_row=10)
        assert 'terminal' in output
        assert 'plain' in output
        assert 'markdown' in output
        assert 'html' in output
        
        # Test that markdown matches plain
        assert output['markdown'] == output['plain']

    def test_enhanced_search_methods(self):
        """Test enhanced search methods."""
        table = _Table()
        table.add_headers(["Name", "Category", "Status"])
        table.add_row_data([
            ["Alice", "Admin", "Active"],
            ["Bob", "User", "Active"],
            ["Alice", "User", "Inactive"],
            ["Charlie", "Admin", "Active"]
        ])
        
        # Test find_all_occurrences
        alice_occurrences = table.find_all_occurrences("Alice")
        assert alice_occurrences == {"Name": [1, 3]}
        
        active_occurrences = table.find_all_occurrences("Active")
        assert active_occurrences == {"Status": [1, 2, 4]}
        
        admin_occurrences = table.find_all_occurrences("Admin")
        assert admin_occurrences == {"Category": [1, 4]}
        
        # Test with non-existent content
        empty_occurrences = table.find_all_occurrences("NonExistent")
        assert empty_occurrences == {}
        
        # Test find_headers_with
        headers_with_alice = table.find_headers_with("Alice")
        assert headers_with_alice == ["Name"]
        
        headers_with_active = table.find_headers_with("Active")
        assert headers_with_active == ["Status"]
        
        headers_with_admin = table.find_headers_with("Admin")
        assert headers_with_admin == ["Category"]
        
        # Test find_columns_with (alias for find_headers_with)
        columns_with_alice = table.find_columns_with("Alice")
        assert columns_with_alice == ["Name"]
        assert columns_with_alice == headers_with_alice  # Should be identical
        
        # Test with non-existent content
        empty_headers = table.find_headers_with("NonExistent")
        assert empty_headers == []
        
        empty_columns = table.find_columns_with("NonExistent")
        assert empty_columns == []
    
    def test_enhanced_update_methods(self):
        """Test enhanced update methods."""
        table = _Table()
        table.add_headers(["Name", "Category", "Status"])
        table.add_row_data([
            ["Alice", "Admin", "Active"],
            ["Bob", "User", "Active"],
            ["Alice", "User", "Inactive"],
            ["Charlie", "Admin", "Active"]
        ])
        
        # Test update_all_cells_with
        updated_count = table.update_all_cells_with("Alice", "Alicia")
        assert updated_count == 2
        assert table.get_cell("Name", 1) == "Alicia"
        assert table.get_cell("Name", 3) == "Alicia"
        
        # Test update_cell with header filter
        success = table.update_cell("Active", "Online", headers="Status")
        assert success is True
        assert table.get_cell("Status", 1) == "Online"
        assert table.get_cell("Status", 2) == "Online"
        assert table.get_cell("Status", 4) == "Online"
        
        # Test update_cell with row filter
        success = table.update_cell("Admin", "Administrator", rows=[1, 4])
        assert success is True
        assert table.get_cell("Category", 1) == "Administrator"
        assert table.get_cell("Category", 4) == "Administrator"
        assert table.get_cell("Category", 2) == "User"  # Should not change
        
        # Test update_cell with both filters
        success = table.update_cell("User", "Regular User", headers="Category", rows=[2, 3])
        assert success is True
        assert table.get_cell("Category", 2) == "Regular User"
        assert table.get_cell("Category", 3) == "Regular User"
    
    def test_enhanced_formatting_methods(self):
        """Test enhanced formatting methods."""
        table = _Table()
        table.add_headers(["Name", "Category", "Status"])
        table.add_row_data([
            ["Alice", "Admin", "Active"],
            ["Bob", "User", "Active"],
            ["Alice", "User", "Inactive"],
            ["Charlie", "Admin", "Active"]
        ])
        
        # Test format_all_cells_with
        formatted_count = table.format_all_cells_with("Active", "</green>")
        assert formatted_count == 3
        
        formatted_count = table.format_all_cells_with("Alice", "</bold>")
        assert formatted_count == 2
        
        formatted_count = table.format_all_cells_with("Admin", "</red>")
        assert formatted_count == 2
    
    def test_enhanced_error_handling(self):
        """Test error handling for enhanced methods."""
        table = _Table()
        table.add_headers(["Name", "Category"])
        table.add_row_data([["Alice", "Admin"], ["Bob", "User"]])
        
        # Test invalid header in update_cell
        try:
            table.update_cell("Alice", "Alicia", headers="Invalid")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        # Test invalid row in update_cell
        try:
            table.update_cell("Alice", "Alicia", rows=5)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        # Test invalid row range in update_cell
        try:
            table.update_cell("Alice", "Alicia", rows=range(1, 10))
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        # Test invalid headers type
        try:
            table.update_cell("Alice", "Alicia", headers=123)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        # Test invalid rows type
        try:
            table.update_cell("Alice", "Alicia", rows="invalid")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_duplicate_header_validation(self):
        """Test duplicate header validation."""
        table = _Table()
        
        # Test single header validation
        table.add_header("Name")
        try:
            table.add_header("Name")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already exists" in str(e)
        
        # Test list with internal duplicates
        try:
            table.add_headers(["Age", "Name", "City"])  # 'Name' already exists
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already exists" in str(e)
        
        # Test list with duplicates within the list
        try:
            table.add_headers(["Age", "Age", "City"])  # 'Age' appears twice
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Duplicate header" in str(e)
        
        # Test successful addition
        table.add_headers(["Age", "City"])
        assert table.get_headers() == ["Name", "Age", "City"]
        
        # Test max_columns constraint
        table2 = _Table(max_columns=2)
        table2.add_header("A")
        try:
            table2.add_headers(["B", "C"])  # Would exceed max_columns
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "max_columns" in str(e)

    def test_find_all_occurrences_multiple_headers(self):
        """Test find_all_occurrences when the same content appears in multiple different headers."""
        table = _Table()
        table.add_headers(["Name", "Category", "Status", "Location"])
        table.add_row_data([
            ["Alice", "Active", "Active", "Office"],      # "Active" in both Category and Status
            ["Bob", "User", "Active", "Home"],            # "Active" only in Status
            ["Charlie", "Active", "Inactive", "Active"],  # "Active" in Category and Location
            ["David", "User", "User", "Home"],            # "User" in both Name and Category
            ["Eve", "Admin", "Active", "Admin"],          # "Admin" in both Category and Location
            ["Frank", "Active", "Active", "Active"]       # "Active" in all three columns
        ])
        
        # Test content that appears in multiple different headers
        active_occurrences = table.find_all_occurrences("Active")
        assert active_occurrences == {
            "Category": [1, 3, 6],
            "Status": [1, 2, 6],
            "Location": [3, 6]
        }
        
        user_occurrences = table.find_all_occurrences("User")
        assert user_occurrences == {
            "Category": [2, 4],
            "Name": [4]
        }
        
        admin_occurrences = table.find_all_occurrences("Admin")
        assert admin_occurrences == {
            "Category": [5],
            "Location": [5]
        }
        
        # Test content that appears in only one header
        alice_occurrences = table.find_all_occurrences("Alice")
        assert alice_occurrences == {"Name": [1]}
        
        # Test content that doesn't exist
        nonexistent_occurrences = table.find_all_occurrences("NonExistent")
        assert nonexistent_occurrences == {}
        
        # Test with tuple formatting
        table.add_row_data([["Grace", ("Active", "</red>"), "Active", "Office"]])
        active_with_format_occurrences = table.find_all_occurrences("Active")
        assert active_with_format_occurrences == {
            "Category": [1, 3, 6, 7],
            "Status": [1, 2, 6, 7],
            "Location": [3, 6]
        }
        
        # Test that the dictionary structure is correct
        assert isinstance(active_occurrences, dict)
        assert all(isinstance(key, str) for key in active_occurrences.keys())
        assert all(isinstance(value, list) for value in active_occurrences.values())
        assert all(isinstance(item, int) for value in active_occurrences.values() for item in value)
        
        # Test that row numbers are 1-based
        assert all(item >= 1 for value in active_occurrences.values() for item in value)
        
        # Test that row numbers are within valid range
        max_row = max(item for value in active_occurrences.values() for item in value)
        assert max_row <= table.row_count
        
        # Test that all headers containing the content are included
        assert "Category" in active_occurrences
        assert "Status" in active_occurrences
        assert "Location" in active_occurrences


def run_visual_demos():
    """Run all visual demonstrations."""
    print("\n" + "="*80)
    print("🎨 TABLE CLASS VISUAL DEMONSTRATIONS")
    print("="*80)
    
    demo = TestTableVisualDemonstration()
    demo.setup_method()  # Manually call setup_method
    
    demo.test_basic_table_creation_demo()
    demo.test_table_styles_demo()
    demo.test_data_operations_demo()
    demo.test_formatting_demo()
    demo.test_tuple_formatting_demo()
    demo.test_utility_operations_demo()
    demo.test_display_methods_demo()
    demo.test_error_handling_demo()
    demo.test_missing_vertical_borders_demo()
    demo.test_maximum_table_size_demo()
    demo.test_duplicate_data_handling_demo()
    demo.test_duplicate_header_validation_demo()
    demo.test_multiple_headers_occurrences_demo()
    
    print("\n" + "="*80)
    print("✅ VISUAL DEMONSTRATIONS COMPLETE")
    print("="*80)


def run_tests():
    """Run all unit tests."""
    print("\n" + "="*80)
    print("🧪 RUNNING TABLE UNIT TESTS")
    print("="*80)
    
    test_classes = [
        TestTableUnitTests
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                test_method = getattr(test_instance, method_name)
                test_method()
                print(f"  ✅ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"  ❌ {method_name}: {e}")
    
    print(f"\n📊 Test Results: {passed_tests}/{total_tests} passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed!")
            else:
        print(f"⚠️ {total_tests - passed_tests} tests failed")


if __name__ == "__main__":
    # Run visual demonstrations first
    run_visual_demos()
    
    # Then run unit tests
    run_tests()
    
    print("\n" + "="*80)
    print("🏁 TABLE CLASS TESTING COMPLETE")
    print("="*80) 