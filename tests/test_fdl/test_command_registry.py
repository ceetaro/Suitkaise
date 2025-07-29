# tests/test_fdl/test_command_registry.py
"""
Tests for the FDL command registry module.

Tests the internal command registry system and command processor base class.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from suitkaise.fdl._int.core.command_registry import (
    _CommandRegistry, _CommandProcessor, _command_processor
)
from suitkaise.fdl._int.core.format_state import _FormatState


class TestCommandProcessor:
    """Test the _CommandProcessor base class."""
    
    def test_command_processor_interface(self):
        """Test that _CommandProcessor defines the correct interface."""
        # Should have abstract methods
        assert hasattr(_CommandProcessor, 'can_process')
        assert hasattr(_CommandProcessor, 'process')
        
        # Should be abstract (can't instantiate directly)
        with pytest.raises(TypeError):
            _CommandProcessor()


class TestCommandRegistry:
    """Test the _CommandRegistry class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear registry for clean tests
        _CommandRegistry._processors.clear()
        _CommandRegistry._priority_order.clear()
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clear registry after tests
        _CommandRegistry._processors.clear()
        _CommandRegistry._priority_order.clear()
    
    def test_registry_initialization(self):
        """Test registry starts empty."""
        assert len(_CommandRegistry._processors) == 0
        assert len(_CommandRegistry._priority_order) == 0
    
    def test_register_processor(self):
        """Test registering a command processor."""
        # Create a mock processor
        class MockProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'mock'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Register processor
        _CommandRegistry.register(MockProcessor, priority=10)
        
        assert len(_CommandRegistry._processors) == 1
        assert MockProcessor in _CommandRegistry._processors
        assert _CommandRegistry._processors[MockProcessor] == 10
        assert MockProcessor in _CommandRegistry._priority_order
    
    def test_register_multiple_processors_priority_order(self):
        """Test that processors are ordered by priority."""
        class HighPriorityProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'high'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        class LowPriorityProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'low'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Register in reverse priority order
        _CommandRegistry.register(LowPriorityProcessor, priority=1)
        _CommandRegistry.register(HighPriorityProcessor, priority=10)
        
        # Should be ordered by priority (high to low)
        assert _CommandRegistry._priority_order[0] == HighPriorityProcessor
        assert _CommandRegistry._priority_order[1] == LowPriorityProcessor
    
    def test_find_processor(self):
        """Test finding a processor for a command."""
        class TestProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command.startswith('test')
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        _CommandRegistry.register(TestProcessor, priority=5)
        
        # Should find processor for matching command
        processor = _CommandRegistry.find_processor('test_command')
        assert processor == TestProcessor
        
        # Should return None for non-matching command
        processor = _CommandRegistry.find_processor('other_command')
        assert processor is None
    
    def test_find_processor_priority_order(self):
        """Test that processor with higher priority is found first."""
        class HighPriorityProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True  # Accepts all commands
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        class LowPriorityProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True  # Accepts all commands
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Register in reverse priority order
        _CommandRegistry.register(LowPriorityProcessor, priority=1)
        _CommandRegistry.register(HighPriorityProcessor, priority=10)
        
        # Should find high priority processor first
        processor = _CommandRegistry.find_processor('any_command')
        assert processor == HighPriorityProcessor
    
    def test_process_command(self):
        """Test processing a command through the registry."""
        class TestProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'test'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.test_processed = True
                return format_state
        
        _CommandRegistry.register(TestProcessor, priority=5)
        
        format_state = _FormatState()
        result = _CommandRegistry.process_command('test', format_state)
        
        assert hasattr(result, 'test_processed')
        assert result.test_processed is True
    
    def test_process_unknown_command(self):
        """Test processing unknown command returns original state."""
        format_state = _FormatState()
        result = _CommandRegistry.process_command('unknown', format_state)
        
        assert result is format_state  # Should return unchanged
    
    def test_get_registry_info(self):
        """Test getting registry information."""
        class TestProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        _CommandRegistry.register(TestProcessor, priority=5)
        
        info = _CommandRegistry.get_registry_info()
        
        assert 'total_processors' in info
        assert info['total_processors'] == 1
        assert 'processors' in info
        assert len(info['processors']) == 1
        assert info['processors'][0]['name'] == 'TestProcessor'
        assert info['processors'][0]['priority'] == 5
    
    def test_is_registered(self):
        """Test checking if processor is registered."""
        class TestProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        assert not _CommandRegistry.is_registered(TestProcessor)
        
        _CommandRegistry.register(TestProcessor, priority=5)
        
        assert _CommandRegistry.is_registered(TestProcessor)


class TestCommandProcessorDecorator:
    """Test the @_command_processor decorator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear registry for clean tests
        _CommandRegistry._processors.clear()
        _CommandRegistry._priority_order.clear()
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clear registry after tests
        _CommandRegistry._processors.clear()
        _CommandRegistry._priority_order.clear()
    
    def test_decorator_registers_processor(self):
        """Test that decorator automatically registers processor."""
        @_command_processor(priority=8)
        class DecoratedProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'decorated'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Should be automatically registered
        assert _CommandRegistry.is_registered(DecoratedProcessor)
        assert _CommandRegistry._processors[DecoratedProcessor] == 8
    
    def test_decorator_with_default_priority(self):
        """Test decorator with default priority."""
        @_command_processor()
        class DefaultPriorityProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Should use default priority (0)
        assert _CommandRegistry._processors[DefaultPriorityProcessor] == 0
    
    def test_decorator_returns_class(self):
        """Test that decorator returns the original class."""
        @_command_processor(priority=5)
        class TestProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Should still be the same class
        assert TestProcessor.__name__ == 'TestProcessor'
        assert issubclass(TestProcessor, _CommandProcessor)


class TestCommandRegistryEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        _CommandRegistry._processors.clear()
        _CommandRegistry._priority_order.clear()
    
    def teardown_method(self):
        """Clean up after tests."""
        _CommandRegistry._processors.clear()
        _CommandRegistry._priority_order.clear()
    
    def test_register_non_processor_class(self):
        """Test registering non-processor class raises error."""
        class NotAProcessor:
            pass
        
        with pytest.raises(TypeError):
            _CommandRegistry.register(NotAProcessor, priority=5)
    
    def test_register_same_processor_twice(self):
        """Test registering same processor twice updates priority."""
        class TestProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        _CommandRegistry.register(TestProcessor, priority=5)
        _CommandRegistry.register(TestProcessor, priority=10)
        
        # Should update priority
        assert _CommandRegistry._processors[TestProcessor] == 10
        # Should only appear once in priority order
        assert _CommandRegistry._priority_order.count(TestProcessor) == 1
    
    def test_processor_exception_handling(self):
        """Test that processor exceptions are handled gracefully."""
        class FaultyProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'faulty'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                raise Exception("Processor error")
        
        _CommandRegistry.register(FaultyProcessor, priority=5)
        
        format_state = _FormatState()
        # Should not crash, should return original state
        result = _CommandRegistry.process_command('faulty', format_state)
        assert result is format_state


if __name__ == '__main__':
    pytest.main([__file__])