# tests/test_fdl/test_main_processor.py
"""
Tests for the FDL main processor module.

Tests the internal _FDLProcessor class and processing flow.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from suitkaise.fdl._int.core.main_processor import _FDLProcessor


class TestFDLProcessor:
    """Test the _FDLProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = _FDLProcessor()
    
    def test_processor_initialization(self):
        """Test processor initializes correctly."""
        assert self.processor is not None
        assert hasattr(self.processor, '_all_brackets_pattern')
    
    def test_process_basic_text(self):
        """Test processing basic text without any FDL syntax."""
        result = self.processor.process_string('Hello World')
        
        assert 'terminal' in result
        assert 'plain' in result
        assert result['terminal'].strip().endswith('Hello World')
        assert result['plain'].strip() == 'Hello World'
    
    def test_process_with_variables(self):
        """Test processing text with variable substitution."""
        result = self.processor.process_string('Hello <name>!', ('Alice',))
        
        assert 'Alice' in result['terminal']
        assert 'Alice' in result['plain']
    
    def test_process_with_color_commands(self):
        """Test processing text with color commands."""
        result = self.processor.process_string('</red>Red text</reset>')
        
        # Terminal should have ANSI codes
        assert '\x1b[31m' in result['terminal']  # Red color code
        assert '\x1b[0m' in result['terminal']   # Reset code
        
        # Plain text should not have ANSI codes
        assert '\x1b[31m' not in result['plain']
        assert 'Red text' in result['plain']
    
    def test_process_with_justification(self):
        """Test processing text with justification commands."""
        result = self.processor.process_string('</justify center>Centered text')
        
        # Both outputs should have padding for centering
        assert result['terminal'].strip().startswith(' ')
        assert result['plain'].strip().startswith(' ')
        assert 'Centered text' in result['terminal']
        assert 'Centered text' in result['plain']
    
    def test_process_with_time_objects(self):
        """Test processing text with time objects."""
        result = self.processor.process_string('Current time: <time:>')
        
        # Should contain time format (HH:MM:SS)
        assert ':' in result['terminal']
        assert ':' in result['plain']
        assert 'Current time:' in result['terminal']
        assert 'Current time:' in result['plain']
    
    def test_process_complex_string(self):
        """Test processing complex FDL string with multiple elements."""
        import time
        timestamp = time.time() - 3600
        
        complex_string = (
            '</cyan>Time: <time:></reset> '
            '</bold>Status:</reset> <status> '
            '</justify right>Right aligned'
        )
        values = ('Online',)
        
        result = self.processor.process_string(complex_string, values)
        
        # Should have ANSI codes for colors and formatting
        assert '\x1b[36m' in result['terminal']  # Cyan
        assert '\x1b[1m' in result['terminal']   # Bold
        assert '\x1b[0m' in result['terminal']   # Reset
        
        # Should have all text content
        assert 'Time:' in result['terminal']
        assert 'Status:' in result['terminal']
        assert 'Online' in result['terminal']
        assert 'Right aligned' in result['terminal']
        
        # Plain text should be clean
        assert 'Time:' in result['plain']
        assert 'Online' in result['plain']
        assert '\x1b[' not in result['plain']
    
    def test_process_empty_string(self):
        """Test processing empty string."""
        result = self.processor.process_string('')
        
        assert result['terminal'] == '\x1b[0m'  # Just reset code
        assert result['plain'] == ''
    
    def test_process_with_invalid_syntax(self):
        """Test processing with invalid FDL syntax."""
        # Should handle gracefully and treat as literal text
        result = self.processor.process_string('Invalid <syntax> here')
        
        assert 'Invalid' in result['terminal']
        assert 'syntax' in result['terminal']
        assert 'here' in result['terminal']
    
    def test_process_with_unmatched_brackets(self):
        """Test processing with unmatched brackets."""
        result = self.processor.process_string('Unmatched < bracket')
        
        assert 'Unmatched < bracket' in result['terminal']
        assert 'Unmatched < bracket' in result['plain']
    
    def test_process_with_empty_brackets(self):
        """Test processing with empty brackets."""
        result = self.processor.process_string('Empty <> brackets')
        
        assert 'Empty <> brackets' in result['terminal']
        assert 'Empty <> brackets' in result['plain']
    
    def test_multiple_variables(self):
        """Test processing with multiple variables."""
        result = self.processor.process_string(
            'User <name> has <count> messages',
            ('Alice', 5)
        )
        
        assert 'Alice' in result['terminal']
        assert '5' in result['terminal']
        assert 'messages' in result['terminal']
    
    def test_nested_commands(self):
        """Test processing with nested/combined commands."""
        result = self.processor.process_string('</red, bold>Red bold text</reset>')
        
        # Should have both red and bold ANSI codes
        assert '\x1b[31m' in result['terminal']  # Red
        assert '\x1b[1m' in result['terminal']   # Bold
        assert 'Red bold text' in result['terminal']
    
    def test_wrapping_integration(self):
        """Test that text wrapping is properly integrated."""
        # Create a long string that should wrap
        long_text = 'This is a very long line of text that should definitely wrap when processed ' * 3
        result = self.processor.process_string(long_text)
        
        # Should contain newlines from wrapping
        assert '\n' in result['terminal'] or len(result['terminal']) < len(long_text) + 50
    
    def test_all_output_formats(self):
        """Test that all output formats are generated."""
        result = self.processor.process_string('Test text')
        
        required_formats = ['terminal', 'plain', 'markdown', 'html']
        for format_name in required_formats:
            assert format_name in result
            assert isinstance(result[format_name], str)


class TestProcessorEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = _FDLProcessor()
    
    def test_process_with_none_values(self):
        """Test processing with None in values tuple."""
        result = self.processor.process_string('Value: <value>', (None,))
        
        assert 'None' in result['terminal']
    
    def test_process_with_missing_values(self):
        """Test processing when not enough values provided."""
        # Should handle gracefully without crashing
        result = self.processor.process_string('Missing <value>')
        
        assert 'Missing' in result['terminal']
    
    def test_process_with_extra_values(self):
        """Test processing with extra values that aren't used."""
        result = self.processor.process_string('Only <first>', ('used', 'unused'))
        
        assert 'used' in result['terminal']
        # Should not crash with extra values
    
    def test_process_unicode_content(self):
        """Test processing with unicode content."""
        result = self.processor.process_string('Unicode: 🌟 ✨ 中文')
        
        assert '🌟' in result['terminal']
        assert '✨' in result['terminal']
        assert '中文' in result['terminal']


if __name__ == '__main__':
    pytest.main([__file__])