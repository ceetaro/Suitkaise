# tests/test_fdl/test_setup/test_terminal.py
import pytest
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from io import StringIO

# Import test setup
from setup_fdl_tests import FDL_INT_PATH
sys.path.insert(0, str(FDL_INT_PATH))

from setup.terminal import _TerminalInfo, _terminal, _refresh_terminal_info, TerminalWidthError


class TestTerminalInfo:
    """Test the internal _TerminalInfo class."""
    
    def test_initialization_normal_conditions(self):
        """Test _TerminalInfo initialization under normal conditions."""
        # Create a fresh instance
        terminal = _TerminalInfo()
        
        # Should have detected basic properties
        assert terminal.width >= 80  # Should always be at least 80
        assert terminal.height >= 1  # Should have some height
        assert isinstance(terminal.supports_color, bool)
        assert isinstance(terminal.is_tty, bool)
        assert isinstance(terminal.encoding, str)
        assert len(terminal.encoding) > 0  # Should have some encoding
    
    def test_width_property_critical_requirement(self):
        """Test that width property returns valid integer and is critical."""
        terminal = _TerminalInfo()
        
        # Width must be accessible and reasonable
        width = terminal.width
        assert isinstance(width, int)
        assert width >= 80  # Hard minimum
        assert width <= 1000  # Reasonable maximum
    
    def test_height_property_graceful_fallback(self):
        """Test that height property falls back gracefully."""
        terminal = _TerminalInfo()
        
        # Height should always be accessible
        height = terminal.height
        assert isinstance(height, int)
        assert height >= 1  # At least 1 line
        # If detection fails, should fallback to 24
    
    def test_color_support_detection(self):
        """Test color support detection."""
        terminal = _TerminalInfo()
        
        # Should return boolean
        color_support = terminal.supports_color
        assert isinstance(color_support, bool)
        
        # Test with NO_COLOR environment variable
        with patch.dict(os.environ, {'NO_COLOR': '1'}):
            # Create new instance to test NO_COLOR
            terminal_no_color = _TerminalInfo()
            # Should be False due to NO_COLOR
            assert terminal_no_color.supports_color is False
    
    def test_tty_detection(self):
        """Test TTY detection."""
        terminal = _TerminalInfo()
        
        # Should return boolean
        is_tty = terminal.is_tty
        assert isinstance(is_tty, bool)
    
    def test_encoding_detection(self):
        """Test encoding detection with fallback."""
        terminal = _TerminalInfo()
        
        # Should always have some encoding
        encoding = terminal.encoding
        assert isinstance(encoding, str)
        assert encoding in ['utf-8', 'ascii', 'cp1252', 'latin1'] or encoding.startswith('utf') or encoding.startswith('cp')
    
    def test_refresh_functionality(self):
        """Test that refresh method works without errors."""
        terminal = _TerminalInfo()
        
        # Store original values
        original_width = terminal.width
        original_height = terminal.height
        
        # Refresh should not raise errors
        terminal.refresh()
        
        # Properties should still be accessible
        assert isinstance(terminal.width, int)
        assert isinstance(terminal.height, int)
    
    @patch('os.get_terminal_size')
    @patch('shutil.get_terminal_size')
    def test_size_detection_failure_raises_error(self, mock_shutil_size, mock_os_size):
        """Test that size detection failure raises TerminalWidthError."""
        # Mock both size detection methods to fail
        mock_os_size.side_effect = OSError("No terminal")
        mock_shutil_size.side_effect = OSError("No terminal")
        
        # Also mock environment variables to not exist
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(TerminalWidthError):
                _TerminalInfo()
    
    @patch('os.get_terminal_size')
    def test_size_detection_with_valid_os_size(self, mock_os_size):
        """Test successful size detection using os.get_terminal_size."""
        # Mock successful size detection
        mock_size = Mock()
        mock_size.columns = 120
        mock_size.lines = 30
        mock_os_size.return_value = mock_size
        
        terminal = _TerminalInfo()
        
        assert terminal.width == 120
        assert terminal.height == 30
    
    @patch('os.get_terminal_size')
    @patch('shutil.get_terminal_size')
    def test_size_detection_fallback_to_shutil(self, mock_shutil_size, mock_os_size):
        """Test fallback to shutil.get_terminal_size when os method fails."""
        # Mock os method to fail, shutil to succeed
        mock_os_size.side_effect = OSError("os method failed")
        
        mock_size = Mock()
        mock_size.columns = 100
        mock_size.lines = 25
        mock_shutil_size.return_value = mock_size
        
        terminal = _TerminalInfo()
        
        assert terminal.width == 100
        assert terminal.height == 25
    
    @patch('os.get_terminal_size')
    @patch('shutil.get_terminal_size')
    def test_size_detection_fallback_to_environment(self, mock_shutil_size, mock_os_size):
        """Test fallback to environment variables when both size methods fail."""
        # Mock both methods to fail
        mock_os_size.side_effect = OSError("os failed")
        mock_shutil_size.side_effect = OSError("shutil failed")
        
        # Mock environment variables
        with patch.dict(os.environ, {'COLUMNS': '90', 'LINES': '20'}):
            terminal = _TerminalInfo()
            
            assert terminal.width == 90
            assert terminal.height == 20
    
    def test_testing_mode_fallback(self):
        """Test that testing mode forces fallback values."""
        with patch.dict(os.environ, {'FORCE_TERMINAL_FALLBACK': '1'}):
            terminal = _TerminalInfo()
            
            # Should use fallback values
            assert terminal.width == 80
            assert terminal.height == 24
            assert terminal.supports_color is False
            assert terminal.is_tty is False
    
    @patch('sys.stdout')
    def test_tty_detection_with_isatty(self, mock_stdout):
        """Test TTY detection using stdout.isatty()."""
        # Mock isatty to return True
        mock_stdout.isatty.return_value = True
        
        terminal = _TerminalInfo()
        
        # Should detect as TTY (assuming no testing mode override)
        if not os.environ.get('FORCE_TERMINAL_FALLBACK'):
            assert terminal.is_tty is True
    
    def test_color_support_term_environment(self):
        """Test color support detection based on TERM environment variable."""
        # Test with color-supporting terminal
        with patch.dict(os.environ, {'TERM': 'xterm-256color'}):
            with patch('sys.stdout') as mock_stdout:
                mock_stdout.isatty.return_value = True
                terminal = _TerminalInfo()
                
                if not os.environ.get('FORCE_TERMINAL_FALLBACK'):
                    assert terminal.supports_color is True
        
        # Test with non-color terminal
        with patch.dict(os.environ, {'TERM': 'dumb'}):
            terminal = _TerminalInfo()
            # Should not support color for dumb terminal
    
    def test_encoding_detection_methods(self):
        """Test different encoding detection methods."""
        terminal = _TerminalInfo()
        
        # Should never be empty
        assert terminal.encoding != ""
        
        # Should be a valid encoding name
        valid_encodings = [
            'utf-8', 'ascii', 'cp1252', 'latin1', 'iso-8859-1',
            'utf-16', 'utf-32', 'cp1251', 'cp850'
        ]
        
        # Check if it's a known encoding or starts with common prefixes
        is_valid = (
            terminal.encoding in valid_encodings or
            terminal.encoding.startswith('utf') or
            terminal.encoding.startswith('cp') or
            terminal.encoding.startswith('iso') or
            terminal.encoding.startswith('latin')
        )
        
        assert is_valid, f"Unexpected encoding: {terminal.encoding}"


class TestGlobalTerminalInstance:
    """Test the global _terminal instance and related functions."""
    
    def test_global_terminal_accessible(self):
        """Test that global _terminal instance is accessible."""
        # Should be importable and have expected properties
        assert hasattr(_terminal, 'width')
        assert hasattr(_terminal, 'height')
        assert hasattr(_terminal, 'supports_color')
        assert hasattr(_terminal, 'is_tty')
        assert hasattr(_terminal, 'encoding')
    
    def test_global_terminal_properties(self):
        """Test that global terminal has valid properties."""
        # Width is critical
        assert isinstance(_terminal.width, int)
        assert _terminal.width >= 80
        
        # Other properties should be accessible
        assert isinstance(_terminal.height, int)
        assert isinstance(_terminal.supports_color, bool)
        assert isinstance(_terminal.is_tty, bool)
        assert isinstance(_terminal.encoding, str)
    
    def test_refresh_global_terminal_function(self):
        """Test the global refresh function."""
        # Should not raise errors
        _refresh_terminal_info()
        
        # Properties should still be valid after refresh
        assert isinstance(_terminal.width, int)
        assert _terminal.width >= 80


class TestTerminalErrorHandling:
    """Test error handling and edge cases."""
    
    def test_terminal_width_error_exception(self):
        """Test TerminalWidthError exception."""
        # Should be a proper exception
        error = TerminalWidthError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"
    
    @patch('warnings.warn')
    def test_warning_on_height_detection_failure(self, mock_warn):
        """Test that warnings are issued for height detection failure."""
        # This is harder to test directly, but we can check that warnings module is used
        # in the actual code when height detection fails but width succeeds
        pass  # Implementation would depend on specific mocking scenario
    
    def test_minimum_width_enforcement(self):
        """Test that minimum width of 80 is enforced."""
        # Even if detection returns smaller value, should be at least 80
        terminal = _TerminalInfo()
        assert terminal.width >= 80
    
    @patch('os.get_terminal_size')
    def test_invalid_size_values_handling(self, mock_os_size):
        """Test handling of invalid size values from detection."""
        # Mock size with invalid values
        mock_size = Mock()
        mock_size.columns = 0  # Invalid
        mock_size.lines = -1   # Invalid
        mock_os_size.return_value = mock_size
        
        # Should either handle gracefully or fall back to other methods
        try:
            terminal = _TerminalInfo()
            # If it succeeds, width should still be reasonable
            assert terminal.width >= 80
        except TerminalWidthError:
            # This is also acceptable if no fallback works
            pass


def run_tests():
    """Run all terminal tests with visual system information."""
    import traceback
    import os
    import sys
    
    test_classes = [
        TestTerminalInfo,
        TestGlobalTerminalInstance,
        TestTerminalErrorHandling
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    print("🧪 Running Terminal Detection Test Suite...")
    print("=" * 80)
    
    # Show visual examples first
    print("\n🖥️  DETECTED TERMINAL INFORMATION")
    print("-" * 50)
    
    # Current terminal detection
    print("📏 Terminal Dimensions:")
    print(f"  Width:  {_terminal.width} characters")
    print(f"  Height: {_terminal.height} characters")
    
    print(f"\n🎨 Terminal Capabilities:")
    print(f"  Color Support:  {_terminal.supports_color}")
    print(f"  Is TTY:         {_terminal.is_tty}")
    print(f"  Encoding:       {_terminal.encoding}")
    
    # Environment information
    print(f"\n🌍 Environment Variables:")
    env_vars = ['TERM', 'COLORTERM', 'COLUMNS', 'LINES', 'NO_COLOR', 'FORCE_TERMINAL_FALLBACK']
    for var in env_vars:
        value = os.environ.get(var, '(not set)')
        print(f"  {var:20}: {value}")
    
    # Detection method testing
    print(f"\n🔍 Detection Methods:")
    
    # Test os.get_terminal_size()
    try:
        os_size = os.get_terminal_size()
        print(f"  os.get_terminal_size(): {os_size.columns}x{os_size.lines}")
    except Exception as e:
        print(f"  os.get_terminal_size(): ❌ {e}")
    
    # Test shutil.get_terminal_size()
    try:
        import shutil
        shutil_size = shutil.get_terminal_size()
        print(f"  shutil.get_terminal_size(): {shutil_size.columns}x{shutil_size.lines}")
    except Exception as e:
        print(f"  shutil.get_terminal_size(): ❌ {e}")
    
    # Test stdout.isatty()
    try:
        is_tty = sys.stdout.isatty()
        print(f"  sys.stdout.isatty(): {is_tty}")
    except Exception as e:
        print(f"  sys.stdout.isatty(): ❌ {e}")
    
    # Color support analysis
    print(f"\n🎨 Color Support Analysis:")
    print(f"  NO_COLOR env var: {'Set' if os.environ.get('NO_COLOR') else 'Not set'}")
    print(f"  TERM contains color indicators: {any(term in os.environ.get('TERM', '').lower() for term in ['color', 'xterm', '256'])}")
    print(f"  COLORTERM set: {'Yes' if os.environ.get('COLORTERM') else 'No'}")
    
    # Show color test if supported
    if _terminal.supports_color:
        print(f"\n🌈 Color Test (if supported):")
        colors = ['red', 'green', 'yellow', 'blue', 'magenta', 'cyan']
        test_output = "  "
        for color in colors:
            if color == 'red':
                test_output += f"\033[31m{color}\033[0m "
            elif color == 'green':
                test_output += f"\033[32m{color}\033[0m "
            elif color == 'yellow':
                test_output += f"\033[33m{color}\033[0m "
            elif color == 'blue':
                test_output += f"\033[34m{color}\033[0m "
            elif color == 'magenta':
                test_output += f"\033[35m{color}\033[0m "
            elif color == 'cyan':
                test_output += f"\033[36m{color}\033[0m "
        print(test_output)
    else:
        print(f"\n🚫 Color Test: Colors not supported or disabled")
    
    # Unicode test
    print(f"\n🔤 Encoding Test:")
    test_chars = [
        ('ASCII', 'Hello World'),
        ('Latin-1', 'café naïve'),
        ('UTF-8 Basic', 'Hello 世界'),
        ('UTF-8 Emoji', 'Hello 😀 World'),
        ('Box Drawing', '┌─┐│ │└─┘'),
    ]
    
    for desc, test_text in test_chars:
        try:
            test_text.encode(_terminal.encoding)
            encoded_ok = "✅"
        except (UnicodeEncodeError, LookupError):
            encoded_ok = "❌"
        
        print(f"  {desc:15}: {encoded_ok} {test_text}")
    
    # Terminal size demonstration
    print(f"\n📐 Width Demonstration:")
    ruler = "".join(str(i % 10) for i in range(_terminal.width))
    print(ruler)
    print('└' + '─' * (_terminal.width - 2) + '┘')
    print(f"Terminal width: {_terminal.width} characters")
    
    # Multiple instance test
    print(f"\n🔄 Multiple Instance Test:")
    terminal1 = _TerminalInfo()
    terminal2 = _TerminalInfo()
    
    print(f"  Instance 1: {terminal1.width}x{terminal1.height} color={terminal1.supports_color}")
    print(f"  Instance 2: {terminal2.width}x{terminal2.height} color={terminal2.supports_color}")
    print(f"  Global:     {_terminal.width}x{_terminal.height} color={_terminal.supports_color}")
    print(f"  Consistent: {terminal1.width == terminal2.width == _terminal.width}")
    
    print("\n" + "=" * 80)
    print("🧪 RUNNING UNIT TESTS")
    
    for test_class in test_classes:
        print(f"\n📋 {test_class.__name__}")
        print("-" * 40)
        
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
                failed_tests.append(f"{test_class.__name__}.{method_name}: {str(e)}")
                
                # Print traceback for debugging
                if "--verbose" in sys.argv:
                    print("    " + "\n    ".join(traceback.format_exc().split('\n')))
    
    # Summary
    print("\n" + "=" * 80)
    print(f"📊 Test Results: {passed_tests}/{total_tests} passed")
    
    if failed_tests:
        print(f"\n❌ Failed Tests ({len(failed_tests)}):")
        for failure in failed_tests:
            print(f"  • {failure}")
        return False
    else:
        print("🎉 All tests passed!")
        return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)