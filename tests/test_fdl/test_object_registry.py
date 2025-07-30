# tests/test_fdl/test_object_registry.py
"""
Tests for the FDL object registry module.

Tests the internal object registry system and object processor base class.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from suitkaise.fdl._int.core.object_registry import (
    _ObjectRegistry, _ObjectProcessor, _object_processor
)
from suitkaise.fdl._int.core.format_state import _FormatState


class TestObjectProcessor:
    """Test the _ObjectProcessor base class."""
    
    def test_object_processor_interface(self):
        """Test that _ObjectProcessor defines the correct interface."""
        # Should have abstract methods
        assert hasattr(_ObjectProcessor, 'get_supported_object_types')
        assert hasattr(_ObjectProcessor, 'process_object')
        
        # Should be abstract (can't instantiate directly)
        with pytest.raises(TypeError):
            _ObjectProcessor()


class TestObjectRegistry:
    """Test the _ObjectRegistry class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear registry for clean tests
        _ObjectRegistry._type_to_processor.clear()
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clear registry after tests
        _ObjectRegistry._type_to_processor.clear()
    
    def test_registry_initialization(self):
        """Test registry starts empty."""
        assert len(_ObjectRegistry._type_to_processor) == 0
    
    def test_register_processor(self):
        """Test registering an object processor."""
        # Create a mock processor
        class MockProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'mock', 'test'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return f"[{obj_type}:{variable}]"
        
        # Register processor
        _ObjectRegistry.register(MockProcessor)
        
        assert len(_ObjectRegistry._type_to_processor) == 2
        assert _ObjectRegistry._type_to_processor['mock'] == MockProcessor
        assert _ObjectRegistry._type_to_processor['test'] == MockProcessor
    
    def test_register_conflicting_types(self):
        """Test that registering conflicting types raises error."""
        class FirstProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'shared'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "first"
        
        class SecondProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'shared'}  # Conflict!
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "second"
        
        # First registration should work
        _ObjectRegistry.register(FirstProcessor)
        
        # Second registration should raise error
        with pytest.raises(ValueError, match="Object types already registered"):
            _ObjectRegistry.register(SecondProcessor)
    
    def test_is_supported_type(self):
        """Test checking if object type is supported."""
        class TestProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'supported'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "test"
        
        _ObjectRegistry.register(TestProcessor)
        
        assert _ObjectRegistry.is_supported_type('supported') is True
        assert _ObjectRegistry.is_supported_type('unsupported') is False
    
    def test_process_object(self):
        """Test processing an object through the registry."""
        class TestProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'test'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return f"processed:{obj_type}:{variable}"
        
        _ObjectRegistry.register(TestProcessor)
        
        format_state = _FormatState()
        result = _ObjectRegistry.process_object('test', 'variable', format_state)
        
        assert result == 'processed:test:variable'
    
    def test_process_unsupported_object(self):
        """Test processing unsupported object type."""
        format_state = _FormatState()
        result = _ObjectRegistry.process_object('unsupported', 'variable', format_state)
        
        assert result == '[UNKNOWN_OBJECT_TYPE:unsupported]'
    
    def test_get_supported_types(self):
        """Test getting all supported types."""
        class FirstProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'type1', 'type2'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "first"
        
        class SecondProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'type3'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "second"
        
        _ObjectRegistry.register(FirstProcessor)
        _ObjectRegistry.register(SecondProcessor)
        
        supported = _ObjectRegistry.get_supported_types()
        
        assert supported == {'type1', 'type2', 'type3'}
    
    def test_is_registered(self):
        """Test checking if processor is registered."""
        class TestProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'test'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "test"
        
        assert not _ObjectRegistry.is_registered(TestProcessor)
        
        _ObjectRegistry.register(TestProcessor)
        
        assert _ObjectRegistry.is_registered(TestProcessor)
    
    def test_get_registry_info(self):
        """Test getting registry information."""
        class TestProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'test1', 'test2'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "test"
        
        _ObjectRegistry.register(TestProcessor)
        
        info = _ObjectRegistry.get_registry_info()
        
        assert 'total_processors' in info
        assert info['total_processors'] == 1
        assert 'total_types' in info
        assert info['total_types'] == 2
        assert 'processors' in info
        assert len(info['processors']) == 1
        assert info['processors'][0]['name'] == 'TestProcessor'
        assert set(info['processors'][0]['supported_types']) == {'test1', 'test2'}


class TestObjectProcessorDecorator:
    """Test the @_object_processor decorator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear registry for clean tests
        _ObjectRegistry._type_to_processor.clear()
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clear registry after tests
        _ObjectRegistry._type_to_processor.clear()
    
    def test_decorator_registers_processor(self):
        """Test that decorator automatically registers processor."""
        @_object_processor
        class DecoratedProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'decorated'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "decorated"
        
        # Should be automatically registered
        assert _ObjectRegistry.is_registered(DecoratedProcessor)
        assert _ObjectRegistry.is_supported_type('decorated')
    
    def test_decorator_returns_class(self):
        """Test that decorator returns the original class."""
        @_object_processor
        class TestProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'test'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "test"
        
        # Should still be the same class
        assert TestProcessor.__name__ == 'TestProcessor'
        assert issubclass(TestProcessor, _ObjectProcessor)


class TestObjectRegistryEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        _ObjectRegistry._type_to_processor.clear()
    
    def teardown_method(self):
        """Clean up after tests."""
        _ObjectRegistry._type_to_processor.clear()
    
    def test_register_non_processor_class(self):
        """Test registering non-processor class raises error."""
        class NotAProcessor:
            pass
        
        with pytest.raises(TypeError):
            _ObjectRegistry.register(NotAProcessor)
    
    def test_register_processor_without_types(self):
        """Test registering processor that returns no types."""
        class EmptyProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return set()  # Empty set
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "empty"
        
        # Should register without error, but not add any types
        _ObjectRegistry.register(EmptyProcessor)
        assert len(_ObjectRegistry._type_to_processor) == 0
    
    def test_register_processor_with_none_types(self):
        """Test registering processor that returns None types."""
        class NoneProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return None  # This should cause an error
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "none"
        
        # Should raise an error when trying to iterate over None
        with pytest.raises(TypeError):
            _ObjectRegistry.register(NoneProcessor)
    
    def test_processor_exception_handling(self):
        """Test that processor exceptions are handled gracefully."""
        class FaultyProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'faulty'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                raise Exception("Processor error")
        
        _ObjectRegistry.register(FaultyProcessor)
        
        format_state = _FormatState()
        # Should not crash, should return error message
        result = _ObjectRegistry.process_object('faulty', 'variable', format_state)
        assert 'ERROR' in result or 'FAILED' in result
    
    def test_register_same_processor_twice(self):
        """Test registering same processor twice."""
        class TestProcessor(_ObjectProcessor):
            @classmethod
            def get_supported_object_types(cls):
                return {'test'}
            
            @classmethod
            def process_object(cls, obj_type: str, variable: str, format_state: _FormatState) -> str:
                return "test"
        
        # First registration should work
        _ObjectRegistry.register(TestProcessor)
        assert _ObjectRegistry.is_supported_type('test')
        
        # Second registration should raise error (conflict with itself)
        with pytest.raises(ValueError):
            _ObjectRegistry.register(TestProcessor)


if __name__ == '__main__':
    pytest.main([__file__])