"""
Comprehensive tests for FDL Object Element Processor.

Tests the object element processor that handles object patterns like <time:timestamp>
and delegates to registered object processors, including validation and visual demonstrations.
"""

import pytest
import sys
import os
import time
from unittest.mock import Mock, patch
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.elements.object_element import (
    _ObjectElement, _create_object_element, _is_valid_object_pattern,
    _get_supported_object_types, _get_object_type_info, _get_available_object_processors
)
from suitkaise.fdl._int.core.format_state import _FormatState, _create_format_state
from suitkaise.fdl._int.core.object_registry import (
    _ObjectRegistry, _ObjectProcessor, UnsupportedObjectError, _parse_object_content
)


class MockTimeProcessor(_ObjectProcessor):
    """Mock time processor for testing."""
    
    @classmethod
    def get_supported_object_types(cls) -> set:
        """Mock supports time-related objects."""
        return {'time', 'date', 'elapsed'}
    
    @classmethod
    def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
        """Mock process - returns formatted time-like string."""
        if obj_type == 'time':
            if variable:
                return f"[TIME:{variable}]"
            else:
                return "[TIME:current]"
        elif obj_type == 'date':
            if variable:
                return f"[DATE:{variable}]"
            else:
                return "[DATE:current]"
        elif obj_type == 'elapsed':
            if variable:
                return f"[ELAPSED:{variable}]"
            else:
                return "[ELAPSED:current]"
        return f"[UNKNOWN:{obj_type}]"


class MockSpinnerProcessor(_ObjectProcessor):
    """Mock spinner processor for testing."""
    
    @classmethod
    def get_supported_object_types(cls) -> set:
        """Mock supports spinner objects."""
        return {'spinner'}
    
    @classmethod
    def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
        """Mock process - returns spinner representation."""
        if variable:
            return f"[SPINNER:{variable}]"
        else:
            return "[SPINNER:default]"


class TestObjectElement:
    """Test suite for the object element processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.format_state = _create_format_state()
        
        # Clear registry and register mock processors
        _ObjectRegistry.clear_registry()
        _ObjectRegistry.register(MockTimeProcessor)
        _ObjectRegistry.register(MockSpinnerProcessor)
    
    def teardown_method(self):
        """Clean up after tests."""
        _ObjectRegistry.clear_registry()
    
    def test_object_element_initialization(self):
        """Test object element initialization with various object types."""
        # Time object with variable
        element = _ObjectElement("time", "timestamp")
        assert element.obj_type == "time"
        assert element.variable == "timestamp"
        
        # Time object without variable (current)
        element = _ObjectElement("time", None)
        assert element.obj_type == "time"
        assert element.variable is None
        
        # Date object with empty string variable (should become None)
        element = _ObjectElement("date", "")
        assert element.obj_type == "date"
        assert element.variable is None
        
        # Spinner object with variable
        element = _ObjectElement("spinner", "dots")
        assert element.obj_type == "spinner"
        assert element.variable == "dots"
    
    def test_object_element_initialization_unsupported_type(self):
        """Test that unsupported object types raise UnsupportedObjectError."""
        with pytest.raises(UnsupportedObjectError):
            _ObjectElement("unsupported_type", "variable")
    
    def test_object_element_initialization_whitespace_handling(self):
        """Test whitespace handling in initialization."""
        # Whitespace in obj_type and variable should be stripped
        element = _ObjectElement("  time  ", "  timestamp  ")
        assert element.obj_type == "time"
        assert element.variable == "timestamp"
        
        # Empty variable after stripping should become None
        element = _ObjectElement("time", "   ")
        assert element.variable is None
    
    def test_create_from_content_method(self):
        """Test creating object element from content string."""
        # Time with variable
        element = _ObjectElement.create_from_content("time:timestamp")
        assert element.obj_type == "time"
        assert element.variable == "timestamp"
        
        # Date without variable (empty after colon)
        element = _ObjectElement.create_from_content("date:")
        assert element.obj_type == "date"
        assert element.variable is None
        
        # Spinner with variable
        element = _ObjectElement.create_from_content("spinner:dots")
        assert element.obj_type == "spinner"
        assert element.variable == "dots"
    
    def test_create_from_content_invalid_format(self):
        """Test create_from_content with invalid formats."""
        # Missing colon
        with pytest.raises(ValueError):
            _ObjectElement.create_from_content("time_no_colon")
        
        # Empty object type
        with pytest.raises(ValueError):
            _ObjectElement.create_from_content(":variable")
        
        # Unsupported object type
        with pytest.raises(UnsupportedObjectError):
            _ObjectElement.create_from_content("unsupported:variable")
    
    def test_process_time_object_with_variable(self):
        """Test processing time object with variable."""
        element = _ObjectElement("time", "my_timestamp")
        
        result_state = element.process(self.format_state)
        
        # Should add formatted result to outputs
        outputs = result_state.get_final_outputs()
        assert "[TIME:my_timestamp]" in outputs['terminal']
        assert "[TIME:my_timestamp]" in outputs['plain']
    
    def test_process_time_object_without_variable(self):
        """Test processing time object without variable (current time)."""
        element = _ObjectElement("time", None)
        
        result_state = element.process(self.format_state)
        
        # Should add formatted result for current time
        outputs = result_state.get_final_outputs()
        assert "[TIME:current]" in outputs['terminal']
        assert "[TIME:current]" in outputs['plain']
    
    def test_process_object_in_box_mode(self):
        """Test processing object when inside a box."""
        element = _ObjectElement("spinner", "arrows")
        
        # Enable box mode
        self.format_state.in_box = True
        
        result_state = element.process(self.format_state)
        
        # Should add to box_content instead of output streams
        assert "[SPINNER:arrows]" in result_state.box_content
        
        # Should not be in main output streams
        outputs = result_state.get_final_outputs()
        assert "[SPINNER:arrows]" not in outputs['terminal']
    
    def test_process_different_object_types(self):
        """Test processing different supported object types."""
        test_cases = [
            ("time", "timestamp", "[TIME:timestamp]"),
            ("date", "event_date", "[DATE:event_date]"),
            ("elapsed", "start_time", "[ELAPSED:start_time]"),
            ("spinner", "dots", "[SPINNER:dots]"),
        ]
        
        for obj_type, variable, expected in test_cases:
            format_state = _create_format_state()
            element = _ObjectElement(obj_type, variable)
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            assert expected in outputs['terminal']
            assert expected in outputs['plain']
    
    def test_get_object_summary(self):
        """Test getting object summary."""
        # Object with variable
        element = _ObjectElement("time", "timestamp")
        summary = element.get_object_summary()
        assert summary == "time:timestamp"
        
        # Object without variable
        element = _ObjectElement("date", None)
        summary = element.get_object_summary()
        assert summary == "date: (current/default)"
    
    def test_get_object_info(self):
        """Test getting detailed object information."""
        element = _ObjectElement("spinner", "dots")
        info = element.get_object_info()
        
        assert info['obj_type'] == "spinner"
        assert info['variable'] == "dots"
        assert info['is_supported'] is True
        assert info['element_type'] == 'object'
        assert 'processor' in info
        assert 'processor_supported_types' in info
    
    def test_validate_object(self):
        """Test object validation without processing."""
        # Valid object
        element = _ObjectElement("time", "timestamp")
        validation = element.validate_object()
        
        assert validation['obj_type'] == "time"
        assert validation['variable'] == "timestamp"
        assert validation['is_supported'] is True
        assert validation['is_valid'] is True
        assert validation['processor'] is not None
    
    def test_object_element_repr(self):
        """Test string representation of object element."""
        element = _ObjectElement("time", "timestamp")
        repr_str = repr(element)
        
        assert "_ObjectElement" in repr_str
        assert "time" in repr_str
        assert "timestamp" in repr_str
    
    def test_create_object_element_factory(self):
        """Test the factory function for creating object elements."""
        # Valid creation
        element = _create_object_element("time:timestamp")
        assert isinstance(element, _ObjectElement)
        assert element.obj_type == "time"
        assert element.variable == "timestamp"
        
        # Invalid format should raise ValueError
        with pytest.raises(ValueError):
            _create_object_element("invalid_format")
        
        # Unsupported type should raise UnsupportedObjectError
        with pytest.raises(UnsupportedObjectError):
            _create_object_element("unsupported:variable")
    
    def test_is_valid_object_pattern_function(self):
        """Test the standalone object pattern validation function."""
        # Valid patterns
        valid_patterns = [
            "time:timestamp",
            "date:",
            "spinner:dots",
            "elapsed:duration",
        ]
        
        for pattern in valid_patterns:
            assert _is_valid_object_pattern(pattern)
        
        # Invalid patterns
        invalid_patterns = [
            "no_colon",
            ":empty_type",
            "",
            "time:var with space",  # Spaces not allowed in variable
            "date:var-with-dash",   # Dashes not allowed in variable
            "unsupported:variable", # Unsupported type
        ]
        
        for pattern in invalid_patterns:
            assert not _is_valid_object_pattern(pattern)
    
    def test_get_supported_object_types_function(self):
        """Test getting supported object types."""
        supported_types = _get_supported_object_types()
        
        # Should contain our mock processor types
        assert 'time' in supported_types
        assert 'date' in supported_types
        assert 'elapsed' in supported_types
        assert 'spinner' in supported_types
        
        # Should be a set
        assert isinstance(supported_types, set)
    
    def test_get_object_type_info_function(self):
        """Test getting information about specific object types."""
        # Supported type
        info = _get_object_type_info("time")
        assert info['is_supported'] is True
        assert info['processor'] is not None
        assert 'time' in info['supported_types']
        
        # Unsupported type
        info = _get_object_type_info("unsupported")
        assert info['is_supported'] is False
        assert info['processor'] is None
    
    def test_get_available_object_processors_function(self):
        """Test getting information about available object processors."""
        info = _get_available_object_processors()
        
        assert 'total_object_types' in info
        assert 'total_processors' in info
        assert 'processors' in info
        
        # Should have our mock processors
        assert info['total_processors'] == 2  # MockTimeProcessor and MockSpinnerProcessor
        assert info['total_object_types'] >= 4  # time, date, elapsed, spinner
    
    def test_parse_object_content_function(self):
        """Test the parse_object_content utility function."""
        # Valid content
        obj_type, variable = _parse_object_content("time:timestamp")
        assert obj_type == "time"
        assert variable == "timestamp"
        
        # Content without variable
        obj_type, variable = _parse_object_content("date:")
        assert obj_type == "date"
        assert variable is None
        
        # Content with whitespace
        obj_type, variable = _parse_object_content("  spinner : dots  ")
        assert obj_type == "spinner"
        assert variable == "dots"
        
        # Invalid content
        with pytest.raises(ValueError):
            _parse_object_content("no_colon")
        
        with pytest.raises(ValueError):
            _parse_object_content(":empty_type")
    
    def test_edge_case_empty_variable_handling(self):
        """Test handling of empty variables."""
        # Empty string variable should become None
        element = _ObjectElement("time", "")
        assert element.variable is None
        
        # Whitespace-only variable should become None
        element = _ObjectElement("time", "   ")
        assert element.variable is None
        
        # Processing should work with None variable
        result_state = element.process(self.format_state)
        outputs = result_state.get_final_outputs()
        assert "[TIME:current]" in outputs['terminal']
    
    def test_edge_case_special_characters_in_variables(self):
        """Test handling of special characters in variables."""
        # Valid variable names (no spaces or dashes)
        valid_variables = ["timestamp", "event_time", "start123", "var_name"]
        
        for variable in valid_variables:
            element = _ObjectElement("time", variable)
            assert element.variable == variable
            
            result_state = element.process(self.format_state)
            outputs = result_state.get_final_outputs()
            assert f"[TIME:{variable}]" in outputs['terminal']
    
    def test_multiple_object_processing(self):
        """Test processing multiple objects in sequence."""
        objects = [
            ("time", "start"),
            ("date", "event"),
            ("spinner", "loading"),
            ("elapsed", "duration"),
        ]
        
        format_state = _create_format_state()
        
        for obj_type, variable in objects:
            element = _ObjectElement(obj_type, variable)
            format_state = element.process(format_state)
        
        outputs = format_state.get_final_outputs()
        
        # All object results should be in output
        expected_results = [
            "[TIME:start]",
            "[DATE:event]", 
            "[SPINNER:loading]",
            "[ELAPSED:duration]"
        ]
        
        for expected in expected_results:
            assert expected in outputs['terminal']
            assert expected in outputs['plain']


class TestObjectElementVisualDemonstration:
    """Visual demonstration tests for object element processor."""
    
    def setup_method(self):
        """Set up test fixtures with enhanced mock processors."""
        _ObjectRegistry.clear_registry()
        
        # Enhanced mock processors for visual demonstrations
        class VisualTimeProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls) -> set:
                return {'time', 'date', 'datelong', 'elapsed', 'time_ago', 'time_until'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                current_time = time.time()
                
                if obj_type == 'time':
                    if variable:
                        return f"🕐 {variable}_time"
                    else:
                        return f"🕐 {time.strftime('%H:%M:%S')}"
                elif obj_type == 'date':
                    if variable:
                        return f"📅 {variable}_date"
                    else:
                        return f"📅 {time.strftime('%Y-%m-%d')}"
                elif obj_type == 'datelong':
                    if variable:
                        return f"📆 {variable}_long_date"
                    else:
                        return f"📆 {time.strftime('%B %d, %Y')}"
                elif obj_type == 'elapsed':
                    return f"⏱️ {variable or 'current'}_elapsed"
                elif obj_type == 'time_ago':
                    return f"⏪ {variable or 'current'} ago"
                elif obj_type == 'time_until':
                    return f"⏩ {variable or 'current'} until"
                return f"❓ {obj_type}:{variable or 'current'}"
        
        class VisualSpinnerProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls) -> set:
                return {'spinner'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                spinner_types = {
                    'dots': '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏',
                    'arrows': '←↖↑↗→↘↓↙',
                    'bars': '▁▂▃▄▅▆▇█▇▆▅▄▃▁',
                    'default': '|/-\\'
                }
                
                spinner_chars = spinner_types.get(variable, spinner_types['default'])
                return f"🔄 [{spinner_chars[0]}] {variable or 'default'}"
        
        class VisualTypeProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls) -> set:
                return {'type'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                if variable:
                    return f"🏷️ type({variable})"
                else:
                    return f"🏷️ type(current)"
        
        _ObjectRegistry.register(VisualTimeProcessor)
        _ObjectRegistry.register(VisualSpinnerProcessor)
        _ObjectRegistry.register(VisualTypeProcessor)
    
    def teardown_method(self):
        """Clean up after tests."""
        _ObjectRegistry.clear_registry()
    
    def test_visual_basic_object_demonstration(self):
        """Visual demonstration of basic object processing."""
        print("\n" + "="*60)
        print("OBJECT ELEMENT - BASIC OBJECT DEMONSTRATION")
        print("="*60)
        
        test_objects = [
            ("time", None, "Current time"),
            ("time", "start_time", "Variable time"),
            ("date", None, "Current date"),
            ("date", "event_date", "Variable date"),
            ("datelong", None, "Long date format"),
            ("elapsed", "duration", "Elapsed time"),
            ("time_ago", "login", "Time ago"),
            ("time_until", "deadline", "Time until"),
            ("spinner", "dots", "Dots spinner"),
            ("spinner", "arrows", "Arrows spinner"),
            ("type", "value", "Type annotation"),
        ]
        
        for obj_type, variable, description in test_objects:
            print(f"\n{description}:")
            print(f"  Object: {obj_type}:{variable or '(current)'}")
            
            try:
                element = _ObjectElement(obj_type, variable)
                format_state = _create_format_state()
                
                result_state = element.process(format_state)
                outputs = result_state.get_final_outputs()
                
                print(f"  Result: ", end="")
                print(outputs['terminal'], end="")
                print("\033[0m")
                
            except Exception as e:
                print(f"  Error: {e}")
    
    def test_visual_object_parsing_demonstration(self):
        """Visual demonstration of object content parsing."""
        print("\n" + "="*60)
        print("OBJECT ELEMENT - PARSING DEMONSTRATION")
        print("="*60)
        
        parsing_examples = [
            ("Simple time", "time:timestamp"),
            ("Date without variable", "date:"),
            ("Spinner with type", "spinner:dots"),
            ("Elapsed time", "elapsed:start_time"),
            ("Time ago", "time_ago:login_time"),
            ("Type annotation", "type:variable_name"),
            ("With whitespace", "  time : timestamp  "),
        ]
        
        for description, content in parsing_examples:
            print(f"\n{description}: '{content}'")
            
            try:
                obj_type, variable = _parse_object_content(content)
                print(f"  Parsed: type='{obj_type}', variable='{variable}'")
                
                element = _ObjectElement.create_from_content(content)
                print(f"  Summary: {element.get_object_summary()}")
                
                # Show validation
                validation = element.validate_object()
                status = "✅ Valid" if validation['is_valid'] else "❌ Invalid"
                print(f"  Validation: {status}")
                
            except Exception as e:
                print(f"  Error: {e}")
    
    def test_visual_object_validation_demonstration(self):
        """Visual demonstration of object validation."""
        print("\n" + "="*60)
        print("OBJECT ELEMENT - VALIDATION DEMONSTRATION")
        print("="*60)
        
        validation_examples = [
            ("Valid time object", "time:timestamp", True),
            ("Valid date object", "date:", True),
            ("Valid spinner", "spinner:dots", True),
            ("Invalid: no colon", "time_no_colon", False),
            ("Invalid: empty type", ":variable", False),
            ("Invalid: unsupported type", "unknown:variable", False),
            ("Invalid: space in variable", "time:var name", False),
            ("Invalid: dash in variable", "time:var-name", False),
        ]
        
        for description, content, should_be_valid in validation_examples:
            print(f"\n{description}: '{content}'")
            
            try:
                is_valid = _is_valid_object_pattern(content)
                status = "✅ Valid" if is_valid else "❌ Invalid"
                expected = "✅" if should_be_valid else "❌"
                
                print(f"  Pattern validation: {status} (Expected: {expected})")
                
                if is_valid == should_be_valid:
                    print("  \033[32m✓ Correct validation\033[0m")
                else:
                    print("  \033[31m✗ Validation mismatch\033[0m")
                
                if is_valid:
                    element = _ObjectElement.create_from_content(content)
                    obj_validation = element.validate_object()
                    print(f"  Object validation: {'✅' if obj_validation['is_valid'] else '❌'}")
                    print(f"  Processor: {obj_validation['processor'] or 'None'}")
                
            except Exception as e:
                print(f"  Exception: {e}")
    
    def test_visual_box_mode_demonstration(self):
        """Visual demonstration of object processing in box mode."""
        print("\n" + "="*60)
        print("OBJECT ELEMENT - BOX MODE DEMONSTRATION")
        print("="*60)
        
        objects = [
            ("time", None),
            ("date", "event"),
            ("spinner", "loading"),
        ]
        
        print("\nNormal mode:")
        for obj_type, variable in objects:
            element = _ObjectElement(obj_type, variable)
            format_state = _create_format_state()
            
            result_state = element.process(format_state)
            outputs = result_state.get_final_outputs()
            
            print(f"  {obj_type}:{variable or 'current'} -> ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")
        
        print("\nBox mode:")
        format_state = _create_format_state()
        format_state.in_box = True
        
        for obj_type, variable in objects:
            element = _ObjectElement(obj_type, variable)
            format_state = element.process(format_state)
        
        print("  Box content accumulated:")
        for i, content in enumerate(format_state.box_content, 1):
            print(f"    {i}. {content}")
    
    def test_visual_unicode_width_demonstration(self):
        """Visual demonstration of Unicode handling in object results."""
        print("\n" + "="*60)
        print("OBJECT ELEMENT - UNICODE WIDTH DEMONSTRATION")
        print("="*60)
        
        # Objects that produce Unicode output
        unicode_objects = [
            ("time", None, "Time with emoji"),
            ("date", None, "Date with emoji"),
            ("datelong", None, "Long date with emoji"),
            ("spinner", "dots", "Spinner with emoji"),
            ("spinner", "arrows", "Arrow spinner"),
            ("type", "unicode_var", "Type with emoji"),
        ]
        
        for obj_type, variable, description in unicode_objects:
            try:
                element = _ObjectElement(obj_type, variable)
                format_state = _create_format_state()
                
                result_state = element.process(format_state)
                outputs = result_state.get_final_outputs()
                result_text = outputs['terminal']
                
                # Calculate visual width
                visual_width = wcswidth(result_text) or len(result_text)
                
                print(f"Width: {visual_width:2d} | {description:20} -> ", end="")
                print(result_text, end="")
                print("\033[0m")
                
            except Exception as e:
                print(f"Error with {obj_type}:{variable} - {e}")
    
    def test_visual_registry_information_demonstration(self):
        """Visual demonstration of object registry information."""
        print("\n" + "="*60)
        print("OBJECT ELEMENT - REGISTRY INFORMATION DEMONSTRATION")
        print("="*60)
        
        # Show supported object types
        supported_types = _get_supported_object_types()
        print(f"\nSupported object types ({len(supported_types)}):")
        for obj_type in sorted(supported_types):
            print(f"  • {obj_type}")
        
        # Show processor information
        processor_info = _get_available_object_processors()
        print(f"\nRegistered processors ({processor_info['total_processors']}):")
        
        for processor in processor_info['processors']:
            print(f"\n  • {processor['class']}:")
            for obj_type in sorted(processor['supported_types']):
                print(f"    - {obj_type}")
        
        # Show object type routing
        print(f"\nObject type routing:")
        test_types = ['time', 'date', 'spinner', 'type', 'unknown']
        
        for obj_type in test_types:
            info = _get_object_type_info(obj_type)
            processor_name = info['processor'] or "None"
            supported = "✅" if info['is_supported'] else "❌"
            
            print(f"  '{obj_type}' -> {processor_name} {supported}")
    
    def test_visual_error_handling_demonstration(self):
        """Visual demonstration of error handling."""
        print("\n" + "="*60)
        print("OBJECT ELEMENT - ERROR HANDLING DEMONSTRATION")
        print("="*60)
        
        error_examples = [
            ("Unsupported object type", "unknown:variable"),
            ("Invalid format: no colon", "time_no_colon"),
            ("Invalid format: empty type", ":variable"),
            ("Invalid variable: space", "time:var name"),
            ("Invalid variable: dash", "time:var-name"),
        ]
        
        for description, content in error_examples:
            print(f"\n{description}: '{content}'")
            
            try:
                element = _ObjectElement.create_from_content(content)
                format_state = _create_format_state()
                result_state = element.process(format_state)
                outputs = result_state.get_final_outputs()
                
                print(f"  Result: ✅ ", end="")
                print(outputs['terminal'], end="")
                print("\033[0m")
                
            except UnsupportedObjectError as e:
                print(f"  Result: ❌ UnsupportedObjectError: {e}")
            except ValueError as e:
                print(f"  Result: ❌ ValueError: {e}")
            except Exception as e:
                print(f"  Result: ❌ Other error: {e}")
    
    def test_visual_multiple_objects_demonstration(self):
        """Visual demonstration of multiple object processing."""
        print("\n" + "="*60)
        print("OBJECT ELEMENT - MULTIPLE OBJECTS DEMONSTRATION")
        print("="*60)
        
        objects = [
            ("time", "start"),
            ("date", "event"),
            ("spinner", "loading"),
            ("elapsed", "duration"),
            ("type", "result"),
        ]
        
        print(f"Processing {len(objects)} objects in sequence:")
        
        format_state = _create_format_state()
        
        for i, (obj_type, variable) in enumerate(objects, 1):
            print(f"\nStep {i}: Processing {obj_type}:{variable}")
            
            element = _ObjectElement(obj_type, variable)
            format_state = element.process(format_state)
            
            # Show cumulative output
            outputs = format_state.get_final_outputs()
            print(f"  Cumulative result: ", end="")
            print(outputs['terminal'], end="")
            print("\033[0m")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestObjectElementVisualDemonstration()
    demo.test_visual_basic_object_demonstration()
    demo.test_visual_object_parsing_demonstration()
    demo.test_visual_object_validation_demonstration()
    demo.test_visual_box_mode_demonstration()
    demo.test_visual_unicode_width_demonstration()
    demo.test_visual_registry_information_demonstration()
    demo.test_visual_error_handling_demonstration()
    demo.test_visual_multiple_objects_demonstration()
    
    print("\n" + "="*60)
    print("✅ OBJECT ELEMENT PROCESSOR TESTS COMPLETE")
    print("="*60)