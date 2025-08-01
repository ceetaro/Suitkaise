"""
Comprehensive tests for FDL Terminal Detection System.

Tests the internal terminal detection system that provides width, height,
color support, TTY detection, and encoding detection with fallbacks.
"""

import pytest
import sys
import os
import warnings
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.setup.terminal import (
    _TerminalInfo, TerminalWidthError, _get_terminal, _refresh_terminal_info
)


class TestTerminalInfo:
    """Test suite for the terminal information detection system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear any existing environment variables that might interfere
        self.original_env = {}
        env_vars = ['FORCE_TERMINAL_FALLBACK', 'COLUMNS', 'LINES', 'TERM', 'COLORTERM', 'NO_COLOR']
        for var in env_vars:
            if var in os.environ:
                self.original_env[var] = os.environ[var]
                del os.environ[var]
    
    def teardown_method(self):
        """Clean up after tests."""
        # Restore original environment
        for var, value in self.original_env.items():
            os.environ[var] = value
    
    @contextmanager
    def mock_terminal_methods(self, width=80, height=24, tty=True, color=True):
        """Context manager to mock terminal detection methods."""
        with patch('os.get_terminal_size') as mock_os_size, \
             patch('shutil.get_terminal_size') as mock_shutil_size, \
             patch('sys.stdout.isatty') as mock_isatty:
            
            # Configure mocks
            mock_os_size.return_value = Mock(columns=width, lines=height)
            mock_shutil_size.return_value = Mock(columns=width, lines=height)
            mock_isatty.return_value = tty
            
            # Set up environment for color detection
            if color:
                os.environ['TERM'] = 'xterm-256color'
            
            yield {
                'os_size': mock_os_size,
                'shutil_size': mock_shutil_size,
                'isatty': mock_isatty
            }
    
    def test_terminal_info_initialization_success(self):
        """Test successful terminal initialization."""
        with self.mock_terminal_methods(width=100, height=30, tty=True, color=True):
            terminal = _TerminalInfo()
            
            assert terminal.width == 100
            assert terminal.height == 30
            assert terminal.is_tty is True
            assert terminal.supports_color is True
            assert isinstance(terminal.encoding, str)
    
    def test_terminal_info_minimum_width_enforcement(self):
        """Test that minimum width of 60 is enforced."""
        with self.mock_terminal_methods(width=40, height=24):  # Below minimum
            terminal = _TerminalInfo()
            
            # Should enforce minimum width of 60
            assert terminal.width == 60
            assert terminal.height == 24
    
    def test_terminal_width_detection_failure(self):
        """Test behavior when width detection fails completely."""
        with patch('os.get_terminal_size', side_effect=OSError("No terminal")), \
             patch('shutil.get_terminal_size', side_effect=OSError("No terminal")):
            
            # Should raise TerminalWidthError when width cannot be detected
            with pytest.raises(TerminalWidthError):
                _TerminalInfo()
    
    def test_terminal_width_property_with_none(self):
        """Test width property when _width is None."""
        terminal = _TerminalInfo.__new__(_TerminalInfo)  # Create without __init__
        terminal._width = None
        
        with pytest.raises(TerminalWidthError):
            _ = terminal.width
    
    def test_terminal_height_fallback(self):
        """Test height property fallback behavior."""
        terminal = _TerminalInfo.__new__(_TerminalInfo)  # Create without __init__
        terminal._height = None
        
        # Should return 24 as fallback
        assert terminal.height == 24
        
        # Should return actual value when available
        terminal._height = 50
        assert terminal.height == 50
    
    def test_terminal_color_support_fallback(self):
        """Test color support property fallback behavior."""
        terminal = _TerminalInfo.__new__(_TerminalInfo)  # Create without __init__
        terminal._supports_color = None
        
        # Should return False as fallback
        assert terminal.supports_color is False
        
        # Should return actual value when available
        terminal._supports_color = True
        assert terminal.supports_color is True
    
    def test_terminal_tty_fallback(self):
        """Test TTY property fallback behavior."""
        terminal = _TerminalInfo.__new__(_TerminalInfo)  # Create without __init__
        terminal._is_tty = None
        
        # Should return False as fallback
        assert terminal.is_tty is False
        
        # Should return actual value when available
        terminal._is_tty = True
        assert terminal.is_tty is True
    
    def test_terminal_encoding_fallback(self):
        """Test encoding property fallback behavior."""
        terminal = _TerminalInfo.__new__(_TerminalInfo)  # Create without __init__
        terminal._encoding = None
        
        # Should return 'ascii' as fallback
        assert terminal.encoding == 'ascii'
        
        # Should return actual value when available
        terminal._encoding = 'utf-8'
        assert terminal.encoding == 'utf-8'
    
    def test_testing_mode_activation(self):
        """Test testing mode activation via environment variable."""
        test_values = ['1', 'true', 'yes', 'TRUE', 'YES']
        
        for value in test_values:
            os.environ['FORCE_TERMINAL_FALLBACK'] = value
            
            terminal = _TerminalInfo()
            
            # Should use testing mode defaults
            assert terminal.width == 60
            assert terminal.height == 24
            assert terminal.is_tty is False
            assert terminal.supports_color is False
            
            # Clean up
            del os.environ['FORCE_TERMINAL_FALLBACK']
    
    def test_size_detection_methods_priority(self):
        """Test that size detection methods are tried in correct priority order."""
        with patch('os.get_terminal_size', side_effect=OSError("Method 1 failed")) as mock_os, \
             patch('shutil.get_terminal_size') as mock_shutil:
            
            mock_shutil.return_value = Mock(columns=90, lines=25)
            
            terminal = _TerminalInfo()
            
            # Should have tried os.get_terminal_size first, then shutil
            mock_os.assert_called_once()
            mock_shutil.assert_called_once()
            
            assert terminal.width == 90
            assert terminal.height == 25
    
    def test_size_detection_environment_variables(self):
        """Test size detection from environment variables."""
        os.environ['COLUMNS'] = '120'
        os.environ['LINES'] = '40'
        
        with patch('os.get_terminal_size', side_effect=OSError("No terminal")), \
             patch('shutil.get_terminal_size', side_effect=OSError("No terminal")):
            
            terminal = _TerminalInfo()
            
            assert terminal.width == 120
            assert terminal.height == 40
    
    def test_size_detection_environment_variables_minimum_width(self):
        """Test that environment variables still respect minimum width."""
        os.environ['COLUMNS'] = '30'  # Below minimum
        os.environ['LINES'] = '40'
        
        with patch('os.get_terminal_size', side_effect=OSError("No terminal")), \
             patch('shutil.get_terminal_size', side_effect=OSError("No terminal")):
            
            terminal = _TerminalInfo()
            
            assert terminal.width == 60  # Enforced minimum
            assert terminal.height == 40
    
    def test_tty_detection_success(self):
        """Test successful TTY detection."""
        with patch('sys.stdout.isatty', return_value=True):
            terminal = _TerminalInfo()
            assert terminal.is_tty is True
        
        with patch('sys.stdout.isatty', return_value=False):
            terminal = _TerminalInfo()
            assert terminal.is_tty is False
    
    def test_tty_detection_failure(self):
        """Test TTY detection failure handling."""
        with patch('sys.stdout.isatty', side_effect=OSError("TTY detection failed")):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                terminal = _TerminalInfo()
                
                # Should default to False and issue warning
                assert terminal.is_tty is False
                assert len(w) > 0
                assert "TTY detection failed" in str(w[-1].message)
    
    def test_color_support_no_color_environment(self):
        """Test that NO_COLOR environment variable disables colors."""
        os.environ['NO_COLOR'] = '1'
        os.environ['TERM'] = 'xterm-256color'  # Would normally support colors
        
        with patch('sys.stdout.isatty', return_value=True):
            terminal = _TerminalInfo()
            assert terminal.supports_color is False
    
    def test_color_support_term_detection(self):
        """Test color support detection based on TERM variable."""
        color_terms = ['xterm', 'xterm-256color', 'screen', 'tmux', 'vt100', 'color', 'ansi', 'cygwin']
        
        with patch('sys.stdout.isatty', return_value=True):
            for term in color_terms:
                os.environ['TERM'] = term
                terminal = _TerminalInfo()
                assert terminal.supports_color is True, f"Term {term} should support colors"
                del os.environ['TERM']
    
    def test_color_support_colorterm_detection(self):
        """Test color support detection based on COLORTERM variable."""
        color_terms = ['truecolor', '24bit', 'yes']
        
        with patch('sys.stdout.isatty', return_value=True):
            for colorterm in color_terms:
                os.environ['COLORTERM'] = colorterm
                terminal = _TerminalInfo()
                assert terminal.supports_color is True, f"COLORTERM {colorterm} should support colors"
                del os.environ['COLORTERM']
    
    def test_color_support_no_tty(self):
        """Test that color support is disabled when not a TTY."""
        os.environ['TERM'] = 'xterm-256color'
        
        with patch('sys.stdout.isatty', return_value=False):
            terminal = _TerminalInfo()
            assert terminal.supports_color is False
    
    def test_encoding_detection_stdout(self):
        """Test encoding detection from stdout."""
        with patch('sys.stdout.encoding', 'UTF-8'):
            terminal = _TerminalInfo()
            assert terminal.encoding == 'utf-8'  # Should be lowercase
    
    def test_encoding_detection_system_default(self):
        """Test encoding detection from system default."""
        with patch('sys.stdout.encoding', None), \
             patch('sys.getdefaultencoding', return_value='CP1252'):
            terminal = _TerminalInfo()
            assert terminal.encoding == 'cp1252'  # Should be lowercase
    
    def test_encoding_detection_fallback(self):
        """Test encoding detection fallback to ascii."""
        with patch('sys.stdout.encoding', None), \
             patch('sys.getdefaultencoding', side_effect=AttributeError("No default encoding")):
            terminal = _TerminalInfo()
            assert terminal.encoding == 'ascii'
    
    def test_refresh_method(self):
        """Test the refresh method re-detects properties."""
        with self.mock_terminal_methods(width=80, height=24) as mocks:
            terminal = _TerminalInfo()
            
            # Initial values
            assert terminal.width == 80
            assert terminal.height == 24
            
            # Change mock return values
            mocks['os_size'].return_value = Mock(columns=120, lines=40)
            
            # Refresh should re-detect
            terminal.refresh()
            
            assert terminal.width == 120
            assert terminal.height == 40
    
    def test_fallback_width_in_testing_mode(self):
        """Test fallback width behavior in testing mode."""
        os.environ['FORCE_TERMINAL_FALLBACK'] = '1'
        
        terminal = _TerminalInfo()
        fallback_width = terminal._get_fallback_width()
        
        assert fallback_width == 60
    
    def test_fallback_width_normal_mode(self):
        """Test fallback width behavior in normal mode."""
        terminal = _TerminalInfo.__new__(_TerminalInfo)  # Create without __init__
        terminal._testing_mode = False
        
        fallback_width = terminal._get_fallback_width()
        
        # Should return one of the standard fallback widths
        assert fallback_width in [60, 80, 120, 100]
        assert fallback_width >= 60


class TestTerminalGlobalFunctions:
    """Test suite for global terminal functions."""
    
    def test_get_terminal_function(self):
        """Test _get_terminal function returns terminal instance."""
        terminal = _get_terminal()
        
        assert terminal is not None
        assert hasattr(terminal, 'width')
        assert hasattr(terminal, 'height')
        assert hasattr(terminal, 'supports_color')
        assert hasattr(terminal, 'is_tty')
        assert hasattr(terminal, 'encoding')
    
    def test_get_terminal_fallback_creation(self):
        """Test _get_terminal creates fallback when needed."""
        # Import the module-level _terminal and temporarily set it to None
        from suitkaise.fdl._int.setup import terminal as terminal_module
        original_terminal = terminal_module._terminal
        terminal_module._terminal = None
        
        try:
            terminal = _get_terminal()
            
            # Should create fallback terminal
            assert terminal.width == 60
            assert terminal.height == 24
            assert terminal.supports_color is False
            assert terminal.is_tty is False
            assert terminal.encoding == 'ascii'
            
        finally:
            # Restore original terminal
            terminal_module._terminal = original_terminal
    
    def test_refresh_terminal_info_function(self):
        """Test _refresh_terminal_info function."""
        # This should not raise an exception
        _refresh_terminal_info()
        
        # Should work even with fallback terminal
        from suitkaise.fdl._int.setup import terminal as terminal_module
        original_terminal = terminal_module._terminal
        
        # Create a mock terminal without refresh method
        mock_terminal = Mock()
        del mock_terminal.refresh  # Remove refresh method
        terminal_module._terminal = mock_terminal
        
        try:
            # Should not raise exception even without refresh method
            _refresh_terminal_info()
        finally:
            terminal_module._terminal = original_terminal


class TestTerminalErrorHandling:
    """Test suite for terminal error handling and edge cases."""
    
    def test_terminal_width_error_exception(self):
        """Test TerminalWidthError exception."""
        error = TerminalWidthError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_complete_detection_failure_with_warnings(self):
        """Test behavior when all detection methods fail."""
        with patch('os.get_terminal_size', side_effect=OSError("Method 1 failed")), \
             patch('shutil.get_terminal_size', side_effect=OSError("Method 2 failed")), \
             patch.dict(os.environ, {}, clear=True):  # Clear environment variables
            
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                with pytest.raises(TerminalWidthError):
                    _TerminalInfo()
                
                # Should have issued warnings
                assert len(w) > 0
    
    def test_partial_detection_failure_with_fallbacks(self):
        """Test behavior when some detection methods fail but fallbacks work."""
        with patch('os.get_terminal_size', side_effect=OSError("Primary method failed")), \
             patch('shutil.get_terminal_size') as mock_shutil, \
             patch('sys.stdout.isatty', side_effect=OSError("TTY detection failed")):
            
            mock_shutil.return_value = Mock(columns=100, lines=30)
            
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                terminal = _TerminalInfo()
                
                # Should succeed with fallbacks
                assert terminal.width == 100
                assert terminal.height == 30
                assert terminal.is_tty is False  # Fallback value
                
                # Should have issued warnings for failed detections
                warning_messages = [str(warning.message) for warning in w]
                assert any("TTY detection failed" in msg for msg in warning_messages)
    
    def test_invalid_environment_variables(self):
        """Test handling of invalid environment variable values."""
        os.environ['COLUMNS'] = 'not_a_number'
        os.environ['LINES'] = 'also_not_a_number'
        
        with patch('os.get_terminal_size', side_effect=OSError("No terminal")), \
             patch('shutil.get_terminal_size', side_effect=OSError("No terminal")):
            
            # Should handle invalid values gracefully and raise TerminalWidthError
            with pytest.raises(TerminalWidthError):
                _TerminalInfo()
    
    def test_missing_stdout_attributes(self):
        """Test handling when stdout lacks expected attributes."""
        # Mock stdout without isatty method
        mock_stdout = Mock()
        del mock_stdout.isatty
        
        with patch('sys.stdout', mock_stdout):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                
                terminal = _TerminalInfo()
                
                # Should handle gracefully
                assert terminal.is_tty is False
    
    def test_zero_or_negative_terminal_size(self):
        """Test handling of zero or negative terminal sizes."""
        with patch('os.get_terminal_size') as mock_size:
            mock_size.return_value = Mock(columns=0, lines=0)
            
            with patch('shutil.get_terminal_size', side_effect=OSError("Backup failed")):
                # Should fail because width is 0
                with pytest.raises(TerminalWidthError):
                    _TerminalInfo()


class TestTerminalVisualDemonstration:
    """Visual demonstration tests for terminal detection (no actual visual output)."""
    
    def test_terminal_detection_demonstration(self):
        """Demonstrate terminal detection capabilities."""
        print("\n" + "="*60)
        print("TERMINAL DETECTION - CAPABILITY DEMONSTRATION")
        print("="*60)
        
        try:
            terminal = _get_terminal()
            
            print(f"\nTerminal Properties:")
            print(f"  Width: {terminal.width} characters")
            print(f"  Height: {terminal.height} characters")
            print(f"  Is TTY: {terminal.is_tty}")
            print(f"  Supports Color: {terminal.supports_color}")
            print(f"  Encoding: {terminal.encoding}")
            
            # Test color support visually if available
            if terminal.supports_color:
                print(f"\nColor Test:")
                print(f"  \033[31mRed Text\033[0m")
                print(f"  \033[32mGreen Text\033[0m")
                print(f"  \033[34mBlue Text\033[0m")
            else:
                print(f"\nColor support disabled - no color test")
            
            # Test width by drawing a line
            print(f"\nWidth Demonstration:")
            print("  " + "─" * min(terminal.width - 4, 50))
            
        except Exception as e:
            print(f"\nTerminal detection failed: {e}")
    
    def test_terminal_fallback_demonstration(self):
        """Demonstrate terminal fallback behavior."""
        print("\n" + "="*60)
        print("TERMINAL DETECTION - FALLBACK DEMONSTRATION")
        print("="*60)
        
        # Test with forced fallback mode
        original_env = os.environ.get('FORCE_TERMINAL_FALLBACK')
        
        try:
            os.environ['FORCE_TERMINAL_FALLBACK'] = '1'
            
            terminal = _TerminalInfo()
            
            print(f"\nFallback Mode Properties:")
            print(f"  Width: {terminal.width} characters (fallback)")
            print(f"  Height: {terminal.height} characters (fallback)")
            print(f"  Is TTY: {terminal.is_tty} (fallback)")
            print(f"  Supports Color: {terminal.supports_color} (fallback)")
            print(f"  Encoding: {terminal.encoding} (fallback)")
            
        finally:
            # Restore original environment
            if original_env is not None:
                os.environ['FORCE_TERMINAL_FALLBACK'] = original_env
            else:
                os.environ.pop('FORCE_TERMINAL_FALLBACK', None)
    
    def test_terminal_environment_variable_demonstration(self):
        """Demonstrate environment variable effects on terminal detection."""
        print("\n" + "="*60)
        print("TERMINAL DETECTION - ENVIRONMENT VARIABLE EFFECTS")
        print("="*60)
        
        env_tests = [
            ("NO_COLOR", "1", "Disables color support"),
            ("TERM", "xterm-256color", "Enables color support"),
            ("COLORTERM", "truecolor", "Enables color support"),
            ("COLUMNS", "100", "Sets terminal width"),
            ("LINES", "50", "Sets terminal height"),
        ]
        
        for env_var, value, description in env_tests:
            print(f"\nTesting {env_var}={value} ({description}):")
            
            # Store original value
            original_value = os.environ.get(env_var)
            
            try:
                os.environ[env_var] = value
                
                # Force testing mode to avoid actual terminal detection conflicts
                os.environ['FORCE_TERMINAL_FALLBACK'] = '1'
                
                terminal = _TerminalInfo()
                
                print(f"  Width: {terminal.width}")
                print(f"  Height: {terminal.height}")
                print(f"  Supports Color: {terminal.supports_color}")
                
            except Exception as e:
                print(f"  Error: {e}")
            
            finally:
                # Restore original environment
                if original_value is not None:
                    os.environ[env_var] = original_value
                else:
                    os.environ.pop(env_var, None)
                os.environ.pop('FORCE_TERMINAL_FALLBACK', None)


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestTerminalVisualDemonstration()
    demo.test_terminal_detection_demonstration()
    demo.test_terminal_fallback_demonstration()
    demo.test_terminal_environment_variable_demonstration()
    
    print("\n" + "="*60)
    print("✅ TERMINAL DETECTION TESTS COMPLETE")
    print("="*60)