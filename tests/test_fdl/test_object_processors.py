# tests/test_fdl/test_object_processors.py
"""
Tests for the FDL object processors.

Tests all object processors: time objects, progress bars, and spinners.
"""

import pytest
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from suitkaise.fdl._int.processors.objects.time_objects import _TimeObjectProcessor
from suitkaise.fdl._int.core.format_state import _FormatState


class TestTimeObjectProcessor:
    """Test the _TimeObjectProcessor class."""
    
    def test_get_supported_object_types(self):
        """Test that processor supports correct object types."""
        supported = _TimeObjectProcessor.get_supported_object_types()
        
        expected_types = {'time', 'date', 'date_words', 'day', 'time_elapsed', 'time_ago', 'time_until'}
        assert supported == expected_types
    
    def test_process_time_object_current(self):
        """Test processing current time object."""
        format_state = _FormatState()
        
        result = _TimeObjectProcessor.process_object('time', '', format_state)
        
        # Should return time in HH:MM:SS format
        assert ':' in result
        assert len(result.split(':')) >= 2  # At least hours and minutes
    
    def test_process_time_object_with_timestamp(self):
        """Test processing time object with specific timestamp."""
        format_state = _FormatState(values=(1640995200.0,))  # 2022-01-01 00:00:00 UTC
        
        result = _TimeObjectProcessor.process_object('time', 'timestamp', format_state)
        
        # Should return formatted time
        assert ':' in result
        assert isinstance(result, str)
    
    def test_process_date_object(self):
        """Test processing date object."""
        format_state = _FormatState()
        
        result = _TimeObjectProcessor.process_object('date', '', format_state)
        
        # Should return date in some format
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_process_date_words_object(self):
        """Test processing date_words object."""
        format_state = _FormatState()
        
        result = _TimeObjectProcessor.process_object('date_words', '', format_state)
        
        # Should return date in word format
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_process_day_object(self):
        """Test processing day object."""
        format_state = _FormatState()
        
        result = _TimeObjectProcessor.process_object('day', '', format_state)
        
        # Should return day of week
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_process_time_elapsed_object(self):
        """Test processing time_elapsed object."""
        past_time = time.time() - 3600  # 1 hour ago
        format_state = _FormatState(values=(past_time,))
        
        result = _TimeObjectProcessor.process_object('time_elapsed', 'timestamp', format_state)
        
        # Should return elapsed time format
        assert isinstance(result, str)
        # Should contain time units
        assert any(unit in result.lower() for unit in ['h', 'm', 's', 'hour', 'min', 'sec'])
    
    def test_process_time_ago_object(self):
        """Test processing time_ago object."""
        past_time = time.time() - 3600  # 1 hour ago
        format_state = _FormatState(values=(past_time,))
        
        result = _TimeObjectProcessor.process_object('time_ago', 'timestamp', format_state)
        
        # Should return time ago format
        assert isinstance(result, str)
        assert 'ago' in result.lower()
    
    def test_process_time_until_object(self):
        """Test processing time_until object."""
        future_time = time.time() + 3600  # 1 hour from now
        format_state = _FormatState(values=(future_time,))
        
        result = _TimeObjectProcessor.process_object('time_until', 'timestamp', format_state)
        
        # Should return time until format
        assert isinstance(result, str)
        assert 'until' in result.lower()
    
    def test_process_unsupported_object_type(self):
        """Test processing unsupported object type."""
        format_state = _FormatState()
        
        result = _TimeObjectProcessor.process_object('unsupported', '', format_state)
        
        # Should return error message
        assert 'ERROR' in result or 'UNKNOWN' in result
    
    def test_process_with_invalid_timestamp(self):
        """Test processing with invalid timestamp."""
        format_state = _FormatState(values=('invalid_timestamp',))
        
        result = _TimeObjectProcessor.process_object('time', 'timestamp', format_state)
        
        # Should handle gracefully and return current time or error
        assert isinstance(result, str)
    
    def test_process_with_no_values(self):
        """Test processing when no values available but variable expected."""
        format_state = _FormatState()  # No values
        
        result = _TimeObjectProcessor.process_object('time', 'timestamp', format_state)
        
        # Should handle gracefully (probably use current time)
        assert isinstance(result, str)
        assert ':' in result
    
    def test_process_with_none_timestamp(self):
        """Test processing with None timestamp."""
        format_state = _FormatState(values=(None,))
        
        result = _TimeObjectProcessor.process_object('time', 'timestamp', format_state)
        
        # Should handle gracefully
        assert isinstance(result, str)


class TestProgressBarIntegration:
    """Test progress bar integration (basic tests since it's already implemented)."""
    
    def test_progress_bar_import(self):
        """Test that progress bar module can be imported."""
        try:
            from suitkaise.fdl._int.processors.objects.progress_bars import _ProgressBarManager
            assert _ProgressBarManager is not None
        except ImportError:
            pytest.skip("Progress bar module not available")
    
    def test_progress_bar_manager_methods(self):
        """Test progress bar manager has expected methods."""
        try:
            from suitkaise.fdl._int.processors.objects.progress_bars import _ProgressBarManager
            
            # Should have key methods
            assert hasattr(_ProgressBarManager, 'get_active_bar')
            assert hasattr(_ProgressBarManager, 'create_progress_bar')
        except ImportError:
            pytest.skip("Progress bar module not available")


class TestSpinnerIntegration:
    """Test spinner integration (basic tests since it's already implemented)."""
    
    def test_spinner_functions_import(self):
        """Test that spinner functions can be imported."""
        try:
            from suitkaise.fdl._int.processors.objects.spinner_objects import (
                _stop_current_spinner, _get_spinner_types, _is_valid_spinner_type
            )
            assert _stop_current_spinner is not None
            assert _get_spinner_types is not None
            assert _is_valid_spinner_type is not None
        except ImportError:
            pytest.skip("Spinner module not available")
    
    def test_spinner_type_validation(self):
        """Test spinner type validation."""
        try:
            from suitkaise.fdl._int.processors.objects.spinner_objects import _is_valid_spinner_type
            
            # Test with some expected spinner types
            # Note: Actual types depend on implementation
            result = _is_valid_spinner_type('dots')
            assert isinstance(result, bool)
            
            result = _is_valid_spinner_type('invalid_spinner_type_12345')
            assert result is False
        except ImportError:
            pytest.skip("Spinner module not available")
    
    def test_get_spinner_types(self):
        """Test getting available spinner types."""
        try:
            from suitkaise.fdl._int.processors.objects.spinner_objects import _get_spinner_types
            
            types = _get_spinner_types()
            assert isinstance(types, list)
            assert len(types) >= 0  # Should return a list (even if empty)
        except ImportError:
            pytest.skip("Spinner module not available")


class TestObjectProcessorEdgeCases:
    """Test edge cases and error handling for object processors."""
    
    def test_time_processor_with_extreme_timestamps(self):
        """Test time processor with extreme timestamp values."""
        processor = _TimeObjectProcessor
        
        # Test with very large timestamp
        large_timestamp = 9999999999.0  # Far future
        format_state = _FormatState(values=(large_timestamp,))
        
        result = processor.process_object('time', 'timestamp', format_state)
        assert isinstance(result, str)
        
        # Test with negative timestamp
        negative_timestamp = -1000.0
        format_state = _FormatState(values=(negative_timestamp,))
        
        result = processor.process_object('time', 'timestamp', format_state)
        assert isinstance(result, str)
    
    def test_time_processor_with_zero_timestamp(self):
        """Test time processor with zero timestamp."""
        processor = _TimeObjectProcessor
        format_state = _FormatState(values=(0.0,))
        
        result = processor.process_object('time', 'timestamp', format_state)
        assert isinstance(result, str)
    
    def test_time_processor_with_float_precision(self):
        """Test time processor with high precision floats."""
        processor = _TimeObjectProcessor
        precise_time = time.time() + 0.123456789
        format_state = _FormatState(values=(precise_time,))
        
        result = processor.process_object('time', 'timestamp', format_state)
        assert isinstance(result, str)
        assert ':' in result
    
    def test_time_ago_with_future_timestamp(self):
        """Test time_ago with future timestamp (should handle error)."""
        processor = _TimeObjectProcessor
        future_time = time.time() + 3600  # 1 hour in future
        format_state = _FormatState(values=(future_time,))
        
        result = processor.process_object('time_ago', 'timestamp', format_state)
        
        # Should handle gracefully (might return error or adjust)
        assert isinstance(result, str)
    
    def test_time_until_with_past_timestamp(self):
        """Test time_until with past timestamp (should handle error)."""
        processor = _TimeObjectProcessor
        past_time = time.time() - 3600  # 1 hour ago
        format_state = _FormatState(values=(past_time,))
        
        result = processor.process_object('time_until', 'timestamp', format_state)
        
        # Should handle gracefully (might return error or adjust)
        assert isinstance(result, str)


class TestObjectProcessorIntegration:
    """Test integration between object processors and format state."""
    
    def test_time_processor_with_format_state_modifications(self):
        """Test time processor with modified format state."""
        processor = _TimeObjectProcessor
        format_state = _FormatState()
        
        # Modify format state
        format_state.twelve_hour_time = True
        format_state.use_seconds = False
        format_state.timezone = 'pst'
        
        result = processor.process_object('time', '', format_state)
        
        # Should respect format state settings
        assert isinstance(result, str)
        # Note: Actual behavior depends on implementation
    
    def test_multiple_time_objects_same_state(self):
        """Test processing multiple time objects with same format state."""
        processor = _TimeObjectProcessor
        timestamp = time.time()
        format_state = _FormatState(values=(timestamp, timestamp, timestamp))
        
        # Process multiple objects
        result1 = processor.process_object('time', 'ts', format_state)
        result2 = processor.process_object('date', 'ts', format_state)
        result3 = processor.process_object('day', 'ts', format_state)
        
        # All should be valid strings
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert isinstance(result3, str)
        
        # Should consume values from format state
        assert len(format_state.values) == 0  # All values consumed


if __name__ == '__main__':
    pytest.main([__file__])