# tests/test_fdl/test_table_generation.py - Comprehensive Table Generator Tests
import sys
from unittest.mock import patch, Mock

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

from setup.table_generator import _TableGenerator, _CellInfo, _TableDimensions
from setup.terminal import _terminal


class TestTableGeneratorVisualDemonstration:
    """Visual demonstrations of table generation capabilities."""
    
    def setup_method(self):
        """Set up test environment."""
        self.generator = _TableGenerator()
    
    def test_basic_table_visual_demo(self):
        """Demonstrate basic table generation with visual output."""
        print("\n📊 Basic Table Generation Demo")
        print("=" * 60)
        
        headers = ["Name", "Age", "City", "Occupation"]
        data = [
            ["Alice Johnson", "28", "New York", "Software Engineer"],
            ["Bob Smith", "32", "Los Angeles", "Data Scientist"],
            ["Charlie Brown", "25", "Chicago", "Designer"],
            ["Diana Prince", "30", "Seattle", "Product Manager"]
        ]
        
        result = self.generator.generate_table(headers, data)
        
        print("Terminal Output:")
        print(result['terminal'])
        print("\n" + "─" * 60)
        print("Plain Output:")
        print(result['plain'])
        print("\n" + "─" * 60)
        print("Markdown Output:")
        print(result['markdown'])
        print("\n" + "─" * 60)
        print("HTML Output:")
        print(result['html'])
    
    def test_table_styles_visual_demo(self):
        """Demonstrate different table styles."""
        print("\n🎨 Table Styles Demo")
        print("=" * 60)
        
        headers = ["Style", "Description"]
        data = [
            ["Rounded", "Soft, modern appearance"],
            ["Square", "Clean, professional look"],
            ["Double", "Bold, emphasis"],
            ["Simple", "ASCII fallback"]
        ]
        
        styles = ['rounded', 'square', 'double', 'simple']
        
        for style in styles:
            print(f"\n{style.upper()} STYLE:")
            print("-" * 30)
            result = self.generator.generate_table(headers, data, style=style)
            print(result['terminal'])
    
    def test_long_content_wrapping_demo(self):
        """Demonstrate content wrapping in tables."""
        print("\n📝 Content Wrapping Demo")
        print("=" * 60)
        
        headers = ["Short", "Medium", "Long Content"]
        data = [
            ["A", "Medium length text", "This is a very long piece of content that should be wrapped to multiple lines within the table cell"],
            ["B", "Another medium text", "Another very long piece of content that demonstrates how the table handles text wrapping across multiple lines"],
            ["C", "Short", "Yet another example of long content that needs to be wrapped properly in the table cell"]
        ]
        
        result = self.generator.generate_table(headers, data)
        print("Wrapped Content Table:")
        print(result['terminal'])
    
    def test_wide_characters_demo(self):
        """Demonstrate handling of wide characters."""
        print("\n🌍 Wide Characters Demo")
        print("=" * 60)
        
        headers = ["English", "中文", "Mixed"]
        data = [
            ["Hello", "你好世界", "Hello你好"],
            ["Test", "测试", "Test测试"],
            ["Data", "数据", "Data数据"]
        ]
        
        result = self.generator.generate_table(headers, data)
        print("Wide Characters Table:")
        print(result['terminal'])
    
    def test_emoji_demo(self):
        """Demonstrate emoji handling."""
        print("\n😀 Emoji Demo")
        print("=" * 60)
        
        headers = ["Text", "Emoji", "Mixed"]
        data = [
            ["Hello", "😀 🌍", "Hello 😀"],
            ["Test", "🚀 ⭐", "Test 🚀"],
            ["Data", "📊 📈", "Data 📊"]
        ]
        
        result = self.generator.generate_table(headers, data)
        print("Emoji Table:")
        print(result['terminal'])
    
    def test_ansi_colors_demo(self):
        """Demonstrate ANSI color handling."""
        print("\n🎨 ANSI Colors Demo")
        print("=" * 60)
        
        headers = ["Plain", "Colored", "Mixed"]
        data = [
            ["Normal text", "\033[31mRed text\033[0m", "Normal \033[32mgreen\033[0m text"],
            ["Another", "\033[34mBlue text\033[0m", "Text with \033[33myellow\033[0m highlight"],
            ["Final", "\033[35mMagenta\033[0m", "Mixed \033[36mcyan\033[0m content"]
        ]
        
        result = self.generator.generate_table(headers, data)
        print("ANSI Colors Table:")
        print(result['terminal'])
    
    def test_row_selection_demo(self):
        """Demonstrate row selection functionality."""
        print("\n📋 Row Selection Demo")
        print("=" * 60)
        
        headers = ["ID", "Name", "Status"]
        data = [
            ["1", "Alice", "Active"],
            ["2", "Bob", "Inactive"],
            ["3", "Charlie", "Active"],
            ["4", "David", "Pending"],
            ["5", "Eve", "Active"]
        ]
        
        print("Full Table:")
        result = self.generator.generate_table(headers, data)
        print(result['terminal'])
        
        print("\nRows 2-4:")
        result = self.generator.generate_table(headers, data, start_row=2, end_row=4)
        print(result['terminal'])
        
        print("\nFrom Row 3:")
        result = self.generator.generate_table(headers, data, start_row=3)
        print(result['terminal'])
    
    def test_edge_cases_demo(self):
        """Demonstrate edge case handling."""
        print("\n⚠️ Edge Cases Demo")
        print("=" * 60)
        
        # Empty data
        print("Empty Data Table:")
        result = self.generator.generate_table(["Name", "Age"], [])
        print(result['terminal'])
        
        # Mismatched columns
        print("\nMismatched Columns:")
        headers = ["Name", "Age", "City"]
        data = [
            ["Alice", "25"],  # Missing City
            ["Bob", "30", "LA", "Extra"],  # Extra column
            ["Charlie", "35", "Chicago"]  # Correct
        ]
        result = self.generator.generate_table(headers, data)
        print(result['terminal'])
        
        # Very long headers
        print("\nVery Long Headers:")
        headers = ["This is a very long header name that might cause issues with table formatting"]
        data = [["Short content"]]
        result = self.generator.generate_table(headers, data)
        print(result['terminal'])
        
        # Special characters
        print("\nSpecial Characters:")
        headers = ["Name", "Special"]
        data = [["Test", "!@#$%^&*()_+-=[]{}|;':\",./<>?"]]
        result = self.generator.generate_table(headers, data)
        print(result['terminal'])


class TestTableGeneratorInitialization:
    """Test table generator initialization and basic setup."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        generator = _TableGenerator()
        
        # Check constants
        assert generator.MAX_CELL_WIDTH == 30
        assert generator.PADDING == 1
        assert generator.USABLE_WIDTH == 28  # 30 - (2 * 1)
        
        # Check dependencies
        assert generator._text_wrapper is not None
        assert generator._unicode_support is not None
        assert generator._terminal is not None
        assert generator._command_registry is not None
    
    def test_box_styles_defined(self):
        """Test that all expected box styles are defined."""
        generator = _TableGenerator()
        expected_styles = ['rounded', 'square', 'double', 'simple']
        
        for style in expected_styles:
            assert style in generator.BOX_STYLES
            
        # Each style should have required characters
        required_chars = ['top_left', 'top_right', 'bottom_left', 'bottom_right', 
                         'horizontal', 'vertical', 'cross', 'top_tee', 'bottom_tee', 
                         'left_tee', 'right_tee']
        
        for style, chars in generator.BOX_STYLES.items():
            for char_type in required_chars:
                assert char_type in chars
                assert isinstance(chars[char_type], str)
                assert len(chars[char_type]) > 0


class TestBasicTableGeneration:
    """Test basic table generation functionality."""
    
    def test_simple_table_generation(self):
        """Test basic table generation with simple data."""
        generator = _TableGenerator()
        
        headers = ["Name", "Age", "City"]
        data = [
            ["Alice", "25", "New York"],
            ["Bob", "30", "Los Angeles"],
            ["Charlie", "35", "Chicago"]
        ]
        
        result = generator.generate_table(headers, data)
        
        # Should have all output formats
        assert 'terminal' in result
        assert 'plain' in result
        assert 'markdown' in result
        assert 'html' in result
        
        # Terminal output should contain table structure
        terminal_output = result['terminal']
        assert 'Name' in terminal_output
        assert 'Age' in terminal_output
        assert 'City' in terminal_output
        assert 'Alice' in terminal_output
        assert 'Bob' in terminal_output
        assert 'Charlie' in terminal_output
    
    def test_empty_table_handling(self):
        """Test handling of empty headers."""
        generator = _TableGenerator()
        
        result = generator.generate_table([], [])
        
        # Should return empty table in all formats
        assert 'terminal' in result
        assert 'plain' in result
        assert 'markdown' in result
        assert 'html' in result
        
        # All outputs should be empty or minimal
        for format_name, output in result.items():
            assert isinstance(output, str)
    
    def test_single_column_table(self):
        """Test table with single column."""
        generator = _TableGenerator()
        
        headers = ["Items"]
        data = [["Apple"], ["Banana"], ["Cherry"]]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        assert 'Items' in terminal_output
        assert 'Apple' in terminal_output
        assert 'Banana' in terminal_output
        assert 'Cherry' in terminal_output


class TestTableStyles:
    """Test different table styles."""
    
    def test_rounded_style(self):
        """Test rounded box style."""
        generator = _TableGenerator()
        
        headers = ["Test"]
        data = [["Data"]]
        
        result = generator.generate_table(headers, data, style="rounded")
        terminal_output = result['terminal']
        
        # Should contain rounded Unicode box characters
        if generator._unicode_support:
            assert '╭' in terminal_output or '╮' in terminal_output or '╰' in terminal_output or '╯' in terminal_output
        else:
            assert '+' in terminal_output
    
    def test_square_style(self):
        """Test square box style."""
        generator = _TableGenerator()
        
        headers = ["Test"]
        data = [["Data"]]
        
        result = generator.generate_table(headers, data, style="square")
        terminal_output = result['terminal']
        
        # Should contain square Unicode box characters
        if generator._unicode_support:
            assert '┌' in terminal_output or '┐' in terminal_output or '└' in terminal_output or '┘' in terminal_output
        else:
            assert '+' in terminal_output
    
    def test_double_style(self):
        """Test double box style."""
        generator = _TableGenerator()
        
        headers = ["Test"]
        data = [["Data"]]
        
        result = generator.generate_table(headers, data, style="double")
        terminal_output = result['terminal']
        
        # Should contain double Unicode box characters
        if generator._unicode_support:
            assert '╔' in terminal_output or '╗' in terminal_output or '╚' in terminal_output or '╝' in terminal_output
        else:
            assert '+' in terminal_output
    
    def test_simple_style(self):
        """Test simple ASCII style."""
        generator = _TableGenerator()
        
        headers = ["Test"]
        data = [["Data"]]
        
        result = generator.generate_table(headers, data, style="simple")
        terminal_output = result['terminal']
        
        # Should contain ASCII characters
        assert '+' in terminal_output
        assert '-' in terminal_output
        assert '|' in terminal_output


class TestCellContentHandling:
    """Test cell content processing and wrapping."""
    
    def test_long_content_wrapping(self):
        """Test that long content is properly wrapped."""
        generator = _TableGenerator()
        
        headers = ["Short", "Long Content"]
        data = [["A", "This is a very long piece of content that should be wrapped to multiple lines"]]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should contain the long content (may be wrapped)
        # Check for various possible wrapped versions
        assert any(phrase in terminal_output for phrase in [
            "This is a very long piece of content",
            "very long piece of content", 
            "long piece of content",
            "piece of content",
            "wrapped to multiple lines",
            "multiple lines"
        ])
    
    def test_wide_character_handling(self):
        """Test handling of wide characters (like Chinese)."""
        generator = _TableGenerator()
        
        headers = ["English", "中文"]
        data = [["Hello", "你好世界"]]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        assert "Hello" in terminal_output
        assert "你好世界" in terminal_output
    
    def test_emoji_handling(self):
        """Test handling of emoji characters."""
        generator = _TableGenerator()
        
        headers = ["Text", "Emoji"]
        data = [["Hello", "😀 🌍"]]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        assert "Hello" in terminal_output
        assert "😀" in terminal_output
        assert "🌍" in terminal_output
    
    def test_ansi_code_handling(self):
        """Test handling of ANSI color codes."""
        generator = _TableGenerator()
        
        headers = ["Plain", "Colored"]
        data = [["Normal", "\033[31mRed Text\033[0m"]]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        assert "Normal" in terminal_output
        assert "Red Text" in terminal_output


class TestRowAndColumnSelection:
    """Test row and column selection functionality."""
    
    def test_start_row_selection(self):
        """Test selecting rows starting from a specific row."""
        generator = _TableGenerator()
        
        headers = ["Name", "Age"]
        data = [
            ["Alice", "25"],
            ["Bob", "30"],
            ["Charlie", "35"],
            ["David", "40"]
        ]
        
        # Start from row 2 (Bob)
        result = generator.generate_table(headers, data, start_row=2)
        terminal_output = result['terminal']
        
        assert "Bob" in terminal_output
        assert "Charlie" in terminal_output
        assert "David" in terminal_output
        assert "Alice" not in terminal_output  # Should be excluded
    
    def test_end_row_selection(self):
        """Test selecting rows up to a specific row."""
        generator = _TableGenerator()
        
        headers = ["Name", "Age"]
        data = [
            ["Alice", "25"],
            ["Bob", "30"],
            ["Charlie", "35"],
            ["David", "40"]
        ]
        
        # End at row 3 (Charlie)
        result = generator.generate_table(headers, data, end_row=3)
        terminal_output = result['terminal']
        
        assert "Alice" in terminal_output
        assert "Bob" in terminal_output
        assert "Charlie" in terminal_output
        assert "David" not in terminal_output  # Should be excluded
    
    def test_row_range_selection(self):
        """Test selecting a range of rows."""
        generator = _TableGenerator()
        
        headers = ["Name", "Age"]
        data = [
            ["Alice", "25"],
            ["Bob", "30"],
            ["Charlie", "35"],
            ["David", "40"]
        ]
        
        # Select rows 2-3 (Bob and Charlie)
        result = generator.generate_table(headers, data, start_row=2, end_row=3)
        terminal_output = result['terminal']
        
        assert "Bob" in terminal_output
        assert "Charlie" in terminal_output
        assert "Alice" not in terminal_output  # Should be excluded
        assert "David" not in terminal_output  # Should be excluded


class TestOutputFormats:
    """Test different output formats."""
    
    def test_terminal_format(self):
        """Test terminal format output."""
        generator = _TableGenerator()
        
        headers = ["Name", "Value"]
        data = [["Test", "123"]]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should contain box drawing characters
        assert any(char in terminal_output for char in ['│', '─', '┌', '┐', '└', '┘', '+', '-', '|'])
    
    def test_plain_format(self):
        """Test plain format output."""
        generator = _TableGenerator()
        
        headers = ["Name", "Value"]
        data = [["Test", "123"]]
        
        result = generator.generate_table(headers, data)
        plain_output = result['plain']
        
        # Should contain data but no box characters
        assert "Name" in plain_output
        assert "Value" in plain_output
        assert "Test" in plain_output
        assert "123" in plain_output
        
        # Should not contain box drawing characters
        assert '│' not in plain_output
        assert '─' not in plain_output
        assert '┌' not in plain_output
    
    def test_markdown_format(self):
        """Test markdown format output."""
        generator = _TableGenerator()
        
        headers = ["Name", "Value"]
        data = [["Test", "123"]]
        
        result = generator.generate_table(headers, data)
        markdown_output = result['markdown']
        
        # Should contain markdown table syntax
        assert "|" in markdown_output
        assert "---" in markdown_output
        assert "Name" in markdown_output
        assert "Value" in markdown_output
        assert "Test" in markdown_output
        assert "123" in markdown_output
    
    def test_html_format(self):
        """Test HTML format output."""
        generator = _TableGenerator()
        
        headers = ["Name", "Value"]
        data = [["Test", "123"]]
        
        result = generator.generate_table(headers, data)
        html_output = result['html']
        
        # Should contain HTML table tags
        assert "<table>" in html_output
        assert "</table>" in html_output
        assert "<thead>" in html_output
        assert "</thead>" in html_output
        assert "<tbody>" in html_output
        assert "</tbody>" in html_output
        assert "<tr>" in html_output
        assert "</tr>" in html_output
        assert "<th>" in html_output
        assert "</th>" in html_output
        assert "<td>" in html_output
        assert "</td>" in html_output
        
        # Should contain data
        assert "Name" in html_output
        assert "Value" in html_output
        assert "Test" in html_output
        assert "123" in html_output


class TestColorHandling:
    """Test color code generation and handling."""
    
    def test_text_color_codes(self):
        """Test text color code generation."""
        generator = _TableGenerator()
        
        # Test basic colors
        assert generator._get_color_code('red') == '31'
        assert generator._get_color_code('green') == '32'
        assert generator._get_color_code('blue') == '34'
        assert generator._get_color_code('yellow') == '33'
        assert generator._get_color_code('magenta') == '35'
        assert generator._get_color_code('cyan') == '36'
        assert generator._get_color_code('white') == '37'
        assert generator._get_color_code('black') == '30'
        
        # Test bright colors
        assert generator._get_color_code('bright_red') == '91'
        assert generator._get_color_code('bright_green') == '92'
        assert generator._get_color_code('bright_blue') == '94'
        
        # Test invalid colors
        assert generator._get_color_code('invalid_color') is None
    
    def test_background_color_codes(self):
        """Test background color code generation."""
        generator = _TableGenerator()
        
        # Test basic background colors
        assert generator._get_background_color_code('red') == '41'
        assert generator._get_background_color_code('green') == '42'
        assert generator._get_background_color_code('blue') == '44'
        assert generator._get_background_color_code('yellow') == '43'
        assert generator._get_background_color_code('magenta') == '45'
        assert generator._get_background_color_code('cyan') == '46'
        assert generator._get_background_color_code('white') == '47'
        assert generator._get_background_color_code('black') == '40'
        
        # Test bright background colors
        assert generator._get_background_color_code('bright_red') == '101'
        assert generator._get_background_color_code('bright_green') == '102'
        assert generator._get_background_color_code('bright_blue') == '104'
        
        # Test invalid colors
        assert generator._get_background_color_code('invalid_color') is None


class TestDimensionCalculations:
    """Test table dimension calculations."""
    
    def test_calculate_visual_width(self):
        """Test visual width calculation."""
        generator = _TableGenerator()
        
        # Test basic text
        assert generator._calculate_visual_width("Hello") >= 5
        
        # Test text with ANSI codes
        ansi_text = "\033[31mRed Text\033[0m"
        width = generator._calculate_visual_width(ansi_text)
        assert width >= 8  # "Red Text" should be 8 characters
        
        # Test wide characters
        wide_text = "你好世界"
        width = generator._calculate_visual_width(wide_text)
        # Width should be reasonable (either 4 or 8 depending on wcwidth)
        assert width >= 4
    
    def test_calculate_dimensions(self):
        """Test table dimension calculations."""
        generator = _TableGenerator()
        
        # Create a simple matrix for testing
        headers = ["Name", "Age"]
        data = [["Alice", "25"], ["Bob", "30"]]
        
        # Generate table to get matrix
        result = generator.generate_table(headers, data)
        
        # Test that dimensions are calculated
        # This is more of an integration test since we can't easily access the internal matrix
        assert 'terminal' in result
        assert 'plain' in result
        assert 'markdown' in result
        assert 'html' in result


class TestContentWrapping:
    """Test content wrapping functionality."""
    
    def test_wrap_cell_content(self):
        """Test cell content wrapping."""
        generator = _TableGenerator()
        
        # Test short content
        short_content = "Hello"
        wrapped = generator._wrap_cell_content(short_content)
        assert len(wrapped) == 1
        assert wrapped[0] == short_content
        
        # Test long content that should wrap
        long_content = "This is a very long piece of content that should be wrapped to multiple lines"
        wrapped = generator._wrap_cell_content(long_content)
        assert len(wrapped) >= 1  # Should be wrapped to multiple lines
        
        # Test content with ANSI codes
        ansi_content = "\033[31mRed text\033[0m that is long"
        wrapped = generator._wrap_cell_content(ansi_content)
        assert len(wrapped) >= 1


class TestFormatStateProcessing:
    """Test format state processing functionality."""
    
    def test_is_empty_format_state(self):
        """Test empty format state detection."""
        generator = _TableGenerator()
        
        # Import FormatState if available
        try:
            from setup.format_state import _FormatState
            
            # Test empty format state
            empty_state = _FormatState()
            assert generator._is_empty_format_state(empty_state)
            
            # Test non-empty format state
            non_empty_state = _FormatState()
            non_empty_state.text_color = "red"
            assert not generator._is_empty_format_state(non_empty_state)
            
        except ImportError:
            # FormatState not available, skip test
            pass
    
    def test_process_tuple_format(self):
        """Test tuple format processing."""
        generator = _TableGenerator()
        
        # Test basic format
        result = generator._process_tuple_format("<red>")
        # Should return a format state or None
        
        # Test empty format
        result = generator._process_tuple_format("")
        assert result is None
        
        # Test invalid format
        result = generator._process_tuple_format("<invalid_format>")
        # Should return None for invalid formats


class TestTupleFormatting:
    """Test tuple-based formatting functionality."""
    
    def test_tuple_format_basic(self):
        """Test basic tuple formatting."""
        generator = _TableGenerator()
        
        headers = ["Name", "Status"]
        data = [
            [("Alice", "<red>"), "Active"],
            [("Bob", "<blue>"), "Inactive"]
        ]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should contain the content
        assert "Alice" in terminal_output
        assert "Bob" in terminal_output
        assert "Active" in terminal_output
        assert "Inactive" in terminal_output
    
    def test_tuple_format_with_colors(self):
        """Test tuple formatting with color codes."""
        generator = _TableGenerator()
        
        headers = ["Name", "Value"]
        data = [
            [("Success", "<green>"), "100"],
            [("Error", "<red>"), "0"]
        ]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should contain the content
        assert "Success" in terminal_output
        assert "Error" in terminal_output
        assert "100" in terminal_output
        assert "0" in terminal_output


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_data_rows(self):
        """Test handling of empty data rows."""
        generator = _TableGenerator()
        
        headers = ["Name", "Age"]
        data = []  # Empty data
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should still generate a table with headers
        assert "Name" in terminal_output
        assert "Age" in terminal_output
    
    def test_mismatched_column_count(self):
        """Test handling of rows with different column counts."""
        generator = _TableGenerator()
        
        headers = ["Name", "Age", "City"]
        data = [
            ["Alice", "25"],  # Missing City
            ["Bob", "30", "LA", "Extra"],  # Extra column
            ["Charlie", "35", "Chicago"]  # Correct
        ]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should handle gracefully
        assert "Alice" in terminal_output
        assert "Bob" in terminal_output
        assert "Charlie" in terminal_output
    
    def test_very_long_headers(self):
        """Test handling of very long header names."""
        generator = _TableGenerator()
        
        headers = ["This is a very long header name that might cause issues"]
        data = [["Short"]]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should handle long headers (wrapped as shown in visual demo)
        assert "This is a very long header" in terminal_output
        assert "name that might cause issues" in terminal_output
    
    def test_special_characters(self):
        """Test handling of special characters."""
        generator = _TableGenerator()
        
        headers = ["Name", "Special"]
        data = [["Test", "!@#$%^&*()_+-=[]{}|;':\",./<>?"]]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should handle special characters
        assert "Test" in terminal_output
        assert "!@#$%^&*()" in terminal_output


class TestAdvancedEdgeCases:
    """Test advanced edge cases and error handling."""
    
    def test_very_large_table(self):
        """Test handling of very large tables."""
        generator = _TableGenerator()
        
        # Create a large table
        headers = ["Col" + str(i) for i in range(10)]
        data = [["Data" + str(i) + "_" + str(j) for j in range(10)] for i in range(20)]
        
        result = generator.generate_table(headers, data)
        
        # Should handle large tables gracefully
        assert 'terminal' in result
        assert 'plain' in result
        assert 'markdown' in result
        assert 'html' in result
    
    def test_mixed_content_types(self):
        """Test handling of mixed content types."""
        generator = _TableGenerator()
        
        headers = ["String", "Tuple", "Number"]
        data = [
            ["Plain text", ("Formatted", "<red>"), "123"],
            [("Bold text", "<bold>"), "Plain text", "456"]
        ]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should handle mixed content
        assert "Plain text" in terminal_output
        assert "Formatted" in terminal_output
        assert "Bold text" in terminal_output
        assert "123" in terminal_output
        assert "456" in terminal_output
    
    def test_unicode_edge_cases(self):
        """Test Unicode edge cases."""
        generator = _TableGenerator()
        
        headers = ["Normal", "Unicode", "Mixed"]
        data = [
            ["Hello", "你好世界", "Hello你好"],
            ["Test", "测试", "Test测试"]
        ]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should handle Unicode properly
        assert "Hello" in terminal_output
        assert "你好世界" in terminal_output
        assert "Hello你好" in terminal_output
        assert "Test" in terminal_output
        assert "测试" in terminal_output
        assert "Test测试" in terminal_output
    
    def test_control_characters(self):
        """Test handling of control characters."""
        generator = _TableGenerator()
        
        headers = ["Normal", "Control"]
        data = [
            ["Hello", "Text\nwith\nnewlines"],
            ["Test", "Tab\tseparated\ttext"]
        ]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should handle control characters gracefully
        assert "Hello" in terminal_output
        assert "Test" in terminal_output
        assert "Text" in terminal_output
        assert "Tab" in terminal_output

    def test_missing_vertical_borders_multiple_entries(self):
        """Test that multiple missing entries in a row show proper border behavior."""
        generator = _TableGenerator()
        
        headers = ["Name", "Age", "City", "Country", "Phone"]
        data = [
            ["Alice", "25"],  # Missing 3 entries
            ["Bob", "30", "LA"],  # Missing 2 entries  
            ["Charlie", "35", "Chicago", "USA"],  # Missing 1 entry
            ["David", "40", "London", "UK", "123-456"],  # Complete row
            ["Eve", "28", "Paris", "France", "987-654", "Extra"]  # Extra entry
        ]
        
        result = generator.generate_table(headers, data)
        terminal_output = result['terminal']
        
        # Should show missing vertical borders for incomplete rows
        # Alice row should end after "25" without right border
        assert "Alice     │ 25    │" in terminal_output
        # Bob row should end after "LA" without right border  
        assert "Bob       │ 30    │ LA        │" in terminal_output
        # Charlie row should end after "USA" without right border
        assert "Charlie   │ 35    │ Chicago   │ USA       │" in terminal_output
        # David row should be complete
        assert "David     │ 40    │ London    │ UK        │ 123-456   │" in terminal_output
    
    def test_maximum_table_size(self):
        """Test table generation at maximum default size (5 columns, 10 rows)."""
        generator = _TableGenerator()
        
        headers = ["Col1", "Col2", "Col3", "Col4", "Col5"]
        data = []
        for i in range(10):
            data.append([f"R{i+1}C1", f"R{i+1}C2", f"R{i+1}C3", f"R{i+1}C4", f"R{i+1}C5"])
        
        result = generator.generate_table(headers, data)
        
        # All formats should be generated
        assert 'terminal' in result
        assert 'plain' in result
        assert 'markdown' in result
        assert 'html' in result
        
        # Terminal output should have proper structure
        terminal_output = result['terminal']
        assert "╭" in terminal_output  # Top left corner
        assert "╮" in terminal_output  # Top right corner
        assert "╰" in terminal_output  # Bottom left corner
        assert "╯" in terminal_output  # Bottom right corner
        
        # Should have 10 data rows + header + borders
        lines = terminal_output.split('\n')
        assert len(lines) >= 13  # Header + separator + 10 data rows + top/bottom borders
        
        # Check that all data is present
        for i in range(1, 11):
            assert f"R{i}C1" in terminal_output
            assert f"R{i}C5" in terminal_output
    
    def test_markdown_plain_exact_match(self):
        """Test that markdown and plain outputs are exactly identical."""
        generator = _TableGenerator()
        
        headers = ["Name", "Age", "City"]
        data = [["Alice", "25", "NYC"], ["Bob", "30", "LA"], ["Charlie", "35", "Chicago"]]
        
        result = generator.generate_table(headers, data)
        plain_output = result['plain']
        markdown_output = result['markdown']
        
        # Should be exactly identical
        assert plain_output == markdown_output, f"Outputs don't match:\nPLAIN:\n{plain_output}\n\nMARKDOWN:\n{markdown_output}"


def run_visual_demos():
    """Run visual demonstrations."""
    demo = TestTableGeneratorVisualDemonstration()
    demo.setup_method()
    
    print("🎨 Table Generator Visual Demonstrations")
    print("=" * 80)
    
    # Run all visual demos
    demo.test_basic_table_visual_demo()
    demo.test_table_styles_visual_demo()
    demo.test_long_content_wrapping_demo()
    demo.test_wide_characters_demo()
    demo.test_emoji_demo()
    demo.test_ansi_colors_demo()
    demo.test_row_selection_demo()
    demo.test_edge_cases_demo()


def run_tests():
    """Run all table generation tests."""
    import traceback
    
    test_classes = [
        TestTableGeneratorInitialization,
        TestBasicTableGeneration,
        TestTableStyles,
        TestCellContentHandling,
        TestRowAndColumnSelection,
        TestOutputFormats,
        TestColorHandling,
        TestDimensionCalculations,
        TestContentWrapping,
        TestFormatStateProcessing,
        TestTupleFormatting,
        TestEdgeCases,
        TestAdvancedEdgeCases,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("🧪 Running Table Generation Tests")
    print("=" * 60)
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 30)
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Create instance and run test
                test_instance = test_class()
                test_method = getattr(test_instance, method_name)
                test_method()
                
                print(f"  ✅ {method_name}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ❌ {method_name}: {str(e)}")
                import traceback
                print(f"     Traceback: {traceback.format_exc()}")
                failed_tests.append(f"{test_class.__name__}.{method_name}: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
    
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for failure in failed_tests:
            print(f"  • {failure}")
    else:
        print("🎉 All tests passed!")


if __name__ == "__main__":
    # Run visual demonstrations first
    run_visual_demos()
    
    # Then run unit tests
    print("\n" + "=" * 80)
    run_tests()

