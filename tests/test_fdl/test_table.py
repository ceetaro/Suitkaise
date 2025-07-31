#!/usr/bin/env python3

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from suitkaise.fdl._int.classes.table import _Table


def test_table_creation():
    """Test table creation and basic properties."""
    print("🧪 Testing table creation...")
    
    # Test basic creation
    table = _Table()
    assert table.row_count == 0
    assert table.column_count == 0
    assert table.header_count == 0
    assert table.style == "rounded"
    
    # Test with options
    table2 = _Table(style="square", max_columns=5, max_rows=100)
    assert table2.style == "square"
    assert table2.max_columns == 5
    assert table2.max_rows == 100
    
    print("✅ Table creation tests passed")


def test_header_management():
    """Test header management functionality."""
    print("🧪 Testing header management...")
    
    table = _Table()
    
    # Test adding single header
    table.add_header("Name")
    assert table.column_count == 1
    assert "Name" in table.get_headers()
    
    # Test adding multiple headers
    table.add_headers(["Age", "City", "Country"])
    assert table.column_count == 4
    headers = table.get_headers()
    assert headers == ["Name", "Age", "City", "Country"]
    
    # Test removing header
    table.remove_header("City")
    assert table.column_count == 3
    assert "City" not in table.get_headers()
    
    # Test max columns limit
    table_limited = _Table(max_columns=2)
    table_limited.add_header("Col1")
    table_limited.add_header("Col2")
    
    try:
        table_limited.add_header("Col3")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "max_columns" in str(e)
    
    print("✅ Header management tests passed")


def test_data_management():
    """Test data management functionality."""
    print("🧪 Testing data management...")
    
    table = _Table()
    table.add_headers(["Name", "Age", "City"])
    
    # Test adding single row
    table.add_row_data(["John", "25", "NYC"])
    assert table.row_count == 1
    
    # Test adding multiple rows
    table.add_row_data([
        ["Jane", "30", "LA"],
        ["Bob", "35", "Chicago"]
    ])
    assert table.row_count == 3
    
    # Test adding row with tuple formatting
    table.add_row_data([["Alice", ("28", "</bold>"), ("Boston", "</italic>")]])
    assert table.row_count == 4
    
    # Test removing rows
    table.remove_row_data([["John", "25", "NYC"]])
    assert table.row_count == 3
    
    # Test error on wrong row length
    try:
        table.add_row_data(["TooShort"])  # Only 1 item, need 3
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "length" in str(e).lower()
    
    # Test adding data without headers
    empty_table = _Table()
    try:
        empty_table.add_row_data(["Data"])
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "headers" in str(e).lower()
    
    print("✅ Data management tests passed")


def test_cell_operations():
    """Test individual cell operations."""
    print("🧪 Testing cell operations...")
    
    table = _Table()
    table.add_headers(["Name", "Age", "Status"])
    table.add_row_data([
        ["John", "25", "Active"],
        ["Jane", "30", "Inactive"],
        ["Bob", "35", "Active"]
    ])
    
    # Test get_cell
    assert table.get_cell("Name", 1) == "John"
    assert table.get_cell("Age", 2) == "30"
    
    # Test set_cell
    table.set_cell("Status", 2, ("Pending", "</yellow>"))
    assert table.get_cell("Status", 2) == ("Pending", "</yellow>")
    
    # Test update_cell (content matching)
    table.update_cell("Bob", ("Robert", "</bold>"))
    assert table.get_cell("Name", 3) == ("Robert", "</bold>")
    
    # Test get_row
    row1 = table.get_row(1)
    assert row1 == ["John", "25", "Active"]
    
    # Test get_column
    names = table.get_column("Name")
    assert "John" in names
    assert ("Robert", "</bold>") in names
    
    print("✅ Cell operations tests passed")


def test_formatting():
    """Test table formatting functionality."""
    print("🧪 Testing formatting...")
    
    table = _Table()
    table.add_headers(["Name", "Age", "Status"])
    table.add_row_data([
        ["John", "25", "Active"],
        ["Jane", "30", "Inactive"]
    ])
    
    # Test header formatting
    table.format_headers("</bold, underline>")
    assert table._header_format is not None
    
    # Test column formatting
    table.format_column("Status", "</green>")
    assert "Status" in table._column_formats
    
    # Test row formatting
    table.format_row(1, "</italic>")
    assert 1 in table._row_formats
    
    # Test cell formatting
    table.format_cell("Age", 2, "</red>")
    assert ("Age", 2) in table._cell_formats
    
    # Test invalid format
    try:
        table.format_headers("</invalid_command>")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    
    # Test formatting reset
    table.reset_formatting()
    assert table._header_format is None
    assert len(table._column_formats) == 0
    assert len(table._row_formats) == 0
    assert len(table._cell_formats) == 0
    
    print("✅ Formatting tests passed")


def test_format_validation():
    """Test format validation and warnings."""
    print("🧪 Testing format validation...")
    
    table = _Table()
    table.add_headers(["Name", "Status"])
    
    # Test adding data with FDL commands in content (should warn)
    table.add_row_data([["John", "</red>Active</reset>"]])  # Wrong format
    
    # This should trigger validation when displaying
    # (We can't easily test the warning output in this simple test)
    
    # Test correct tuple format
    table.add_row_data([["Jane", ("Active", "</green>")]])  # Correct format
    
    print("✅ Format validation tests passed")


def test_utility_methods():
    """Test utility methods."""
    print("🧪 Testing utility methods...")
    
    table = _Table()
    table.add_headers(["Name", "Age", "Status"])
    table.add_row_data([
        ["John", "25", "Active"],
        ["Jane", "30", "Active"],
        ["Bob", "35", "Inactive"]
    ])
    table.format_headers("</bold>")
    
    # Test copy
    table_copy = table.copy()
    assert table_copy.row_count == table.row_count
    assert table_copy.column_count == table.column_count
    assert table_copy.get_headers() == table.get_headers()
    
    # Copies should be independent
    table_copy.add_row_data([["Alice", "28", "Active"]])
    assert table_copy.row_count == 4
    assert table.row_count == 3
    
    # Test find_rows
    active_rows = table.find_rows("Status", "Active")
    assert 1 in active_rows
    assert 2 in active_rows
    assert 3 not in active_rows
    
    # Test format_matching_cells
    count = table.format_matching_cells("Status", "Active", "</green>")
    assert count == 2
    
    # Test clear operations
    table.clear_all_data()
    assert table.row_count == 0
    assert table.column_count == 3  # Headers remain
    
    table.clear_headers()
    assert table.column_count == 0
    
    print("✅ Utility methods tests passed")


def test_memory_management():
    """Test memory management and release functionality."""
    print("🧪 Testing memory management...")
    
    table = _Table()
    table.add_headers(["Name", "Age"])
    table.add_row_data([["John", "25"]])
    
    # Test release
    table.release()
    
    # Test that methods raise errors after release
    methods_to_test = [
        lambda: table.add_header("Status"),
        lambda: table.add_row_data([["Jane", "30"]]),
        lambda: table.format_headers("</bold>"),
        lambda: table.display(),
        lambda: table.copy()
    ]
    
    for method in methods_to_test:
        try:
            method()
            assert False, "Method should have raised RuntimeError after release"
        except RuntimeError as e:
            assert "released" in str(e).lower()
    
    print("✅ Memory management tests passed")


def test_multi_format_output():
    """Test multi-format output generation."""
    print("🧪 Testing multi-format output...")
    
    table = _Table(style="rounded")
    table.add_headers(["Name", "Age", "Status"])
    table.add_row_data([
        ["John", "25", ("Active", "</green>")],
        ["Jane", "30", "Inactive"]
    ])
    
    # Test getting output
    output = table.get_output()
    
    # Should have all format types
    assert 'terminal' in output
    assert 'plain' in output
    assert 'markdown' in output
    assert 'html' in output
    
    # Terminal output should have box characters
    terminal = output['terminal']
    assert '│' in terminal or '|' in terminal  # Vertical borders
    assert '─' in terminal or '-' in terminal  # Horizontal borders
    
    # Markdown output should have table format
    markdown = output['markdown']
    assert '|' in markdown
    assert '---' in markdown
    
    # HTML output should have table tags
    html = output['html']
    assert '<table>' in html
    assert '<th>' in html
    assert '<td>' in html
    
    print("✅ Multi-format output tests passed")


def test_display_methods():
    """Test display methods."""
    print("🧪 Testing display methods...")
    
    table = _Table()
    table.add_headers(["Name", "Age", "Status"])
    
    # Add more than 10 rows to test pagination
    for i in range(15):
        table.add_row_data([[f"Person{i}", f"{20+i}", "Active"]])
    
    assert table.row_count == 15
    
    # Test display with default range (should show 1-10)
    # We can't easily test the actual output, but we can ensure no errors
    try:
        table.display()  # This will print to stdout
        table.display(start_row=5, end_row=10)
        table.display_all_rows()
        table.display()  # Main display method
        table.display_all_rows()  # Display all rows method
    except Exception as e:
        assert False, f"Display methods should not raise errors: {e}"
    
    print("✅ Display methods tests passed")


def visual_demo():
    """Visual demonstration of table functionality."""
    print("\n" + "="*60)
    print("🎬 VISUAL TABLE DEMONSTRATION")
    print("="*60)
    
    print("\n1️⃣ Basic Table:")
    table1 = _Table(style="rounded")
    table1.add_headers(["Name", "Age", "City"])
    table1.add_row_data([
        ["John", "25", "New York"],
        ["Jane", "30", "Los Angeles"],
        ["Bob", "35", "Chicago"]
    ])
    table1.display()
    
    print("\n2️⃣ Formatted Table:")
    table2 = _Table(style="square")
    table2.add_headers(["Component", "Status", "Usage"])
    table2.add_row_data([
        ["CPU", ("Critical", "</red, bold>"), "85%"],
        ["GPU", ("Normal", "</green>"), ("12%", "</cyan>")],
        ["RAM", ("Warning", "</yellow>"), "67%"]
    ])
    table2.format_headers("</bold, underline>")
    table2.format_column("Usage", "</blue>")
    table2.display()
    
    print("\n3️⃣ Large Table with Pagination:")
    table3 = _Table(style="double")
    table3.add_headers(["ID", "Name", "Score", "Grade"])
    for i in range(12):
        grade = "A" if i < 3 else "B" if i < 8 else "C"
        table3.add_row_data([[f"{i+1:03d}", f"Student{i+1}", f"{90-i*2}", grade]])
    
    print("Showing first 5 rows:")
    table3.display(start_row=1, end_row=5)
    
    print("\n4️⃣ Multi-Format Output:")
    table4 = _Table()
    table4.add_headers(["Format", "Description"])
    table4.add_row_data([
        ["Terminal", "ANSI formatted with box borders"],
        ["Plain", "Clean text without formatting"],
        ["HTML", "Web-ready table with CSS classes"]
    ])
    
    outputs = table4.get_output()
    print("Markdown format:")
    print(outputs['markdown'])
    
    print("\n" + "="*60)
    print("🎉 VISUAL TABLE DEMONSTRATION COMPLETE!")
    print("="*60)


def run_tests():
    """Run all table tests."""
    print("🚀 Starting Table Tests")
    print("="*50)
    
    try:
        test_table_creation()
        test_header_management()
        test_data_management()
        test_cell_operations()
        test_formatting()
        test_format_validation()
        test_utility_methods()
        test_memory_management()
        test_multi_format_output()
        test_display_methods()
        
        print("\n" + "="*50)
        print("✅ ALL TABLE TESTS PASSED!")
        print("="*50)
        
        # Run visual demo
        visual_demo()
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)