"""
Comprehensive tests for FDL Command Registry System.

Tests the internal command registry that manages command processor registration,
routing, priority handling, and thread-safe operations.
"""

import pytest
import sys
import os
import threading
import time
from unittest.mock import Mock, patch
from wcwidth import wcswidth

# Add the suitkaise package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from suitkaise.fdl._int.core.command_registry import (
    _CommandRegistry, _CommandProcessor, UnknownCommandError,
    _register_command_processor, _process_command, _command_processor
)
from suitkaise.fdl._int.core.format_state import _FormatState


# Test command processors for testing
class TestCommandProcessor(_CommandProcessor):
    """Test command processor for unit testing."""
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        return command.startswith('test')
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        format_state.add_to_output_streams(terminal=f"Processed: {command}")
        return format_state


class HighPriorityProcessor(_CommandProcessor):
    """High priority test processor."""
    _priority = 10
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        return command == 'priority'
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        format_state.add_to_output_streams(terminal="High priority")
        return format_state


class LowPriorityProcessor(_CommandProcessor):
    """Low priority test processor."""
    _priority = 90
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        return command == 'priority'
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        format_state.add_to_output_streams(terminal="Low priority")
        return format_state


class UniversalProcessor(_CommandProcessor):
    """Processor that accepts all commands."""
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        return True
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        format_state.add_to_output_streams(terminal=f"Universal: {command}")
        return format_state


class TestCommandProcessor:
    """Test suite for the command processor base class."""
    
    def test_command_processor_abstract_methods(self):
        """Test that _CommandProcessor is abstract and requires implementation."""
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            _CommandProcessor()
    
    def test_command_processor_can_process_abstract(self):
        """Test that can_process is abstract."""
        class IncompleteProcessor(_CommandProcessor):
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Should raise TypeError due to missing can_process
        with pytest.raises(TypeError):
            IncompleteProcessor()
    
    def test_command_processor_process_abstract(self):
        """Test that process is abstract."""
        class IncompleteProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
        
        # Should raise TypeError due to missing process
        with pytest.raises(TypeError):
            IncompleteProcessor()
    
    def test_command_processor_get_priority_default(self):
        """Test get_priority default behavior."""
        class DefaultPriorityProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Should return default priority of 100
        assert DefaultPriorityProcessor.get_priority() == 100
    
    def test_command_processor_get_priority_custom(self):
        """Test get_priority with custom priority."""
        class CustomPriorityProcessor(_CommandProcessor):
            _priority = 50
            
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Should return custom priority
        assert CustomPriorityProcessor.get_priority() == 50
    
    def test_command_processor_get_priority_clamping(self):
        """Test get_priority priority clamping."""
        class InvalidPriorityProcessor(_CommandProcessor):
            _priority = 150  # Above maximum
            
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Should clamp to maximum of 100
        assert InvalidPriorityProcessor.get_priority() == 100
        assert InvalidPriorityProcessor._priority == 100  # Should be modified
        
        class NegativePriorityProcessor(_CommandProcessor):
            _priority = -10  # Below minimum
            
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Should clamp to minimum of 1
        assert NegativePriorityProcessor.get_priority() == 1
        assert NegativePriorityProcessor._priority == 1  # Should be modified


class TestCommandRegistry:
    """Test suite for the command registry system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear registry before each test
        _CommandRegistry.clear_registry()
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clear registry after each test
        _CommandRegistry.clear_registry()
    
    def test_command_registry_initialization(self):
        """Test command registry initialization."""
        registry = _CommandRegistry()
        
        # Should initialize without error
        assert registry is not None
        
        # Should have empty processors initially
        assert len(_CommandRegistry.get_registered_processors()) == 0
    
    def test_register_processor_success(self):
        """Test successful processor registration."""
        _CommandRegistry.register(TestCommandProcessor)
        
        # Should be registered
        assert _CommandRegistry.is_registered(TestCommandProcessor)
        
        # Should be in registered processors list
        processors = _CommandRegistry.get_registered_processors()
        assert TestCommandProcessor in processors
    
    def test_register_processor_with_priority(self):
        """Test processor registration with custom priority."""
        _CommandRegistry.register(TestCommandProcessor, priority=50)
        
        # Should be registered with correct priority
        assert _CommandRegistry.is_registered(TestCommandProcessor)
        assert _CommandRegistry._processors[TestCommandProcessor] == 50
    
    def test_register_processor_invalid_type(self):
        """Test processor registration with invalid type."""
        class NotAProcessor:
            pass
        
        with pytest.raises(TypeError) as exc_info:
            _CommandRegistry.register(NotAProcessor)
        
        assert "must inherit from _CommandProcessor" in str(exc_info.value)
    
    def test_register_processor_duplicate(self):
        """Test registering the same processor twice."""
        _CommandRegistry.register(TestCommandProcessor)
        
        with pytest.raises(ValueError) as exc_info:
            _CommandRegistry.register(TestCommandProcessor)
        
        assert "already registered" in str(exc_info.value)
    
    def test_unregister_processor(self):
        """Test processor unregistration."""
        _CommandRegistry.register(TestCommandProcessor)
        assert _CommandRegistry.is_registered(TestCommandProcessor)
        
        _CommandRegistry.unregister(TestCommandProcessor)
        assert not _CommandRegistry.is_registered(TestCommandProcessor)
        
        # Should not be in registered processors list
        processors = _CommandRegistry.get_registered_processors()
        assert TestCommandProcessor not in processors
    
    def test_unregister_processor_not_registered(self):
        """Test unregistering processor that wasn't registered."""
        # Should not raise error
        _CommandRegistry.unregister(TestCommandProcessor)
        
        # Should still not be registered
        assert not _CommandRegistry.is_registered(TestCommandProcessor)
    
    def test_is_registered_by_class(self):
        """Test is_registered check by class."""
        assert not _CommandRegistry.is_registered(TestCommandProcessor)
        
        _CommandRegistry.register(TestCommandProcessor)
        assert _CommandRegistry.is_registered(TestCommandProcessor)
    
    def test_is_registered_by_name(self):
        """Test is_registered check by name."""
        assert not _CommandRegistry.is_registered("TestCommandProcessor")
        
        _CommandRegistry.register(TestCommandProcessor)
        assert _CommandRegistry.is_registered("TestCommandProcessor")
    
    def test_find_processor_success(self):
        """Test finding processor for command."""
        _CommandRegistry.register(TestCommandProcessor)
        
        processor = _CommandRegistry.find_processor("test_command")
        assert processor == TestCommandProcessor
    
    def test_find_processor_not_found(self):
        """Test finding processor when none can handle command."""
        _CommandRegistry.register(TestCommandProcessor)
        
        processor = _CommandRegistry.find_processor("unknown_command")
        assert processor is None
    
    def test_find_processor_priority_order(self):
        """Test that find_processor respects priority order."""
        _CommandRegistry.register(LowPriorityProcessor, priority=90)
        _CommandRegistry.register(HighPriorityProcessor, priority=10)
        
        # Both can process 'priority' command, but high priority should be found first
        processor = _CommandRegistry.find_processor("priority")
        assert processor == HighPriorityProcessor
    
    def test_process_command_success(self):
        """Test successful command processing."""
        _CommandRegistry.register(TestCommandProcessor)
        format_state = _FormatState()
        
        result_state = _CommandRegistry.process_command("test_command", format_state)
        
        # Should have processed the command
        outputs = result_state.get_final_outputs()
        assert "Processed: test_command" in outputs['terminal']
    
    def test_process_command_unknown(self):
        """Test processing unknown command."""
        format_state = _FormatState()
        
        with pytest.raises(UnknownCommandError) as exc_info:
            _CommandRegistry.process_command("unknown_command", format_state)
        
        assert "Unknown command: 'unknown_command'" in str(exc_info.value)
    
    def test_process_command_empty(self):
        """Test processing empty command."""
        format_state = _FormatState()
        
        # Should return unchanged format state
        result_state = _CommandRegistry.process_command("", format_state)
        assert result_state is format_state
        
        # Should also handle whitespace-only commands
        result_state = _CommandRegistry.process_command("   ", format_state)
        assert result_state is format_state
    
    def test_process_command_priority_order(self):
        """Test that process_command respects priority order."""
        _CommandRegistry.register(LowPriorityProcessor, priority=90)
        _CommandRegistry.register(HighPriorityProcessor, priority=10)
        format_state = _FormatState()
        
        result_state = _CommandRegistry.process_command("priority", format_state)
        
        # Should use high priority processor
        outputs = result_state.get_final_outputs()
        assert "High priority" in outputs['terminal']
        assert "Low priority" not in outputs['terminal']
    
    def test_update_priority_order(self):
        """Test that priority order is maintained correctly."""
        # Register processors in reverse priority order
        _CommandRegistry.register(LowPriorityProcessor, priority=90)
        _CommandRegistry.register(HighPriorityProcessor, priority=10)
        
        # Priority order should be correct
        assert _CommandRegistry._priority_order[0] == HighPriorityProcessor
        assert _CommandRegistry._priority_order[1] == LowPriorityProcessor
    
    def test_get_command_info_found(self):
        """Test get_command_info for found command."""
        _CommandRegistry.register(TestCommandProcessor, priority=50)
        
        info = _CommandRegistry.get_command_info("test_command")
        
        assert info['processor'] == "TestCommandProcessor"
        assert info['priority'] == 50
        assert info['can_process'] is True
    
    def test_get_command_info_not_found(self):
        """Test get_command_info for command not found."""
        info = _CommandRegistry.get_command_info("unknown_command")
        
        assert info['processor'] is None
        assert info['priority'] is None
        assert info['can_process'] is False
    
    def test_clear_registry(self):
        """Test clearing the registry."""
        _CommandRegistry.register(TestCommandProcessor)
        _CommandRegistry.register(HighPriorityProcessor)
        
        assert len(_CommandRegistry.get_registered_processors()) == 2
        
        _CommandRegistry.clear_registry()
        
        assert len(_CommandRegistry.get_registered_processors()) == 0
        assert len(_CommandRegistry._priority_order) == 0
    
    def test_instance_method_delegation(self):
        """Test that instance methods delegate to class methods."""
        registry = _CommandRegistry()
        _CommandRegistry.register(TestCommandProcessor)
        format_state = _FormatState()
        
        # Instance method should delegate to class method
        result_state = registry.process_command("test_command", format_state)
        
        outputs = result_state.get_final_outputs()
        assert "Processed: test_command" in outputs['terminal']


class TestCommandRegistryThreadSafety:
    """Test suite for command registry thread safety."""
    
    def setup_method(self):
        """Set up test fixtures."""
        _CommandRegistry.clear_registry()
    
    def teardown_method(self):
        """Clean up after tests."""
        _CommandRegistry.clear_registry()
    
    def test_concurrent_registration(self):
        """Test concurrent processor registration."""
        processors = []
        
        # Create multiple test processors
        for i in range(10):
            class DynamicProcessor(_CommandProcessor):
                _id = i
                
                @classmethod
                def can_process(cls, command: str) -> bool:
                    return command == f"test_{cls._id}"
                
                @classmethod
                def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                    return format_state
            
            DynamicProcessor.__name__ = f"DynamicProcessor_{i}"
            processors.append(DynamicProcessor)
        
        # Register processors concurrently
        threads = []
        for processor in processors:
            thread = threading.Thread(target=_CommandRegistry.register, args=(processor,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All processors should be registered
        registered = _CommandRegistry.get_registered_processors()
        assert len(registered) == 10
        
        for processor in processors:
            assert _CommandRegistry.is_registered(processor)
    
    def test_concurrent_processing(self):
        """Test concurrent command processing."""
        _CommandRegistry.register(TestCommandProcessor)
        
        results = []
        
        def process_command():
            format_state = _FormatState()
            result_state = _CommandRegistry.process_command("test_concurrent", format_state)
            results.append(result_state.get_final_outputs()['terminal'])
        
        # Process commands concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=process_command)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All should have processed successfully
        assert len(results) == 5
        for result in results:
            assert "Processed: test_concurrent" in result


class TestCommandRegistryConvenienceFunctions:
    """Test suite for command registry convenience functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        _CommandRegistry.clear_registry()
    
    def teardown_method(self):
        """Clean up after tests."""
        _CommandRegistry.clear_registry()
    
    def test_register_command_processor_function(self):
        """Test _register_command_processor convenience function."""
        _register_command_processor(TestCommandProcessor)
        
        assert _CommandRegistry.is_registered(TestCommandProcessor)
    
    def test_process_command_function(self):
        """Test _process_command convenience function."""
        _CommandRegistry.register(TestCommandProcessor)
        format_state = _FormatState()
        
        result_state = _process_command("test_command", format_state)
        
        outputs = result_state.get_final_outputs()
        assert "Processed: test_command" in outputs['terminal']
    
    def test_command_processor_decorator(self):
        """Test _command_processor decorator."""
        @_command_processor(priority=25)
        class DecoratedProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'decorated'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.add_to_output_streams(terminal="Decorated")
                return format_state
        
        # Should be automatically registered
        assert _CommandRegistry.is_registered(DecoratedProcessor)
        assert _CommandRegistry._processors[DecoratedProcessor] == 25
        
        # Should work correctly
        format_state = _FormatState()
        result_state = _process_command("decorated", format_state)
        
        outputs = result_state.get_final_outputs()
        assert "Decorated" in outputs['terminal']
    
    def test_command_processor_decorator_invalid_type(self):
        """Test _command_processor decorator with invalid type."""
        with pytest.raises(TypeError):
            @_command_processor()
            class NotAProcessor:
                pass
    
    def test_command_processor_decorator_duplicate(self):
        """Test _command_processor decorator with duplicate registration."""
        @_command_processor()
        class FirstProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return True
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        # Try to register another processor with same name
        with pytest.raises(ValueError):
            @_command_processor()
            class FirstProcessor(_CommandProcessor):  # Same name
                @classmethod
                def can_process(cls, command: str) -> bool:
                    return True
                
                @classmethod
                def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                    return format_state


class TestCommandRegistryEdgeCases:
    """Test suite for command registry edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        _CommandRegistry.clear_registry()
    
    def teardown_method(self):
        """Clean up after tests."""
        _CommandRegistry.clear_registry()
    
    def test_processor_exception_handling(self):
        """Test handling of exceptions in processors."""
        class ExceptionProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'exception'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                raise ValueError("Test exception")
        
        _CommandRegistry.register(ExceptionProcessor)
        format_state = _FormatState()
        
        # Exception should propagate
        with pytest.raises(ValueError) as exc_info:
            _CommandRegistry.process_command("exception", format_state)
        
        assert "Test exception" in str(exc_info.value)
    
    def test_processor_can_process_exception(self):
        """Test handling of exceptions in can_process method."""
        class CanProcessExceptionProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                raise RuntimeError("can_process exception")
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                return format_state
        
        _CommandRegistry.register(CanProcessExceptionProcessor)
        
        # Exception in can_process should propagate during find_processor
        with pytest.raises(RuntimeError):
            _CommandRegistry.find_processor("any_command")
    
    def test_multiple_processors_same_command(self):
        """Test multiple processors that can handle the same command."""
        class FirstProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'shared'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.add_to_output_streams(terminal="First")
                return format_state
        
        class SecondProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'shared'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.add_to_output_streams(terminal="Second")
                return format_state
        
        # Register in specific order
        _CommandRegistry.register(SecondProcessor, priority=50)
        _CommandRegistry.register(FirstProcessor, priority=30)  # Higher priority
        
        format_state = _FormatState()
        result_state = _CommandRegistry.process_command("shared", format_state)
        
        # Should use higher priority processor
        outputs = result_state.get_final_outputs()
        assert "First" in outputs['terminal']
        assert "Second" not in outputs['terminal']
    
    def test_processor_modifying_command(self):
        """Test processor that modifies the command during processing."""
        class ModifyingProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command.startswith('modify')
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                # Modify the command (though this shouldn't affect the original)
                modified_command = command.upper()
                format_state.add_to_output_streams(terminal=f"Modified: {modified_command}")
                return format_state
        
        _CommandRegistry.register(ModifyingProcessor)
        format_state = _FormatState()
        
        result_state = _CommandRegistry.process_command("modify_test", format_state)
        
        outputs = result_state.get_final_outputs()
        assert "Modified: MODIFY_TEST" in outputs['terminal']
    
    def test_empty_registry_operations(self):
        """Test operations on empty registry."""
        # Should handle empty registry gracefully
        assert len(_CommandRegistry.get_registered_processors()) == 0
        assert _CommandRegistry.find_processor("any_command") is None
        
        info = _CommandRegistry.get_command_info("any_command")
        assert info['can_process'] is False
        
        # Clear empty registry should not error
        _CommandRegistry.clear_registry()


class TestCommandRegistryVisualDemonstration:
    """Visual demonstration tests for command registry system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        _CommandRegistry.clear_registry()
    
    def teardown_method(self):
        """Clean up after tests."""
        _CommandRegistry.clear_registry()
    
    def test_visual_command_registry_demonstration(self):
        """Visual demonstration of command registry capabilities."""
        print("\n" + "="*60)
        print("COMMAND REGISTRY - CAPABILITIES DEMONSTRATION")
        print("="*60)
        
        print(f"\nInitial Registry State:")
        processors = _CommandRegistry.get_registered_processors()
        print(f"  Registered processors: {len(processors)}")
        print(f"  Priority order: {[p.__name__ for p in _CommandRegistry._priority_order]}")
        
        print(f"\nRegistering Test Processors:")
        
        # Register processors with different priorities
        _CommandRegistry.register(TestCommandProcessor, priority=50)
        print(f"  ✅ Registered TestCommandProcessor (priority: 50)")
        
        _CommandRegistry.register(HighPriorityProcessor, priority=10)
        print(f"  ✅ Registered HighPriorityProcessor (priority: 10)")
        
        _CommandRegistry.register(LowPriorityProcessor, priority=90)
        print(f"  ✅ Registered LowPriorityProcessor (priority: 90)")
        
        _CommandRegistry.register(UniversalProcessor, priority=100)
        print(f"  ✅ Registered UniversalProcessor (priority: 100)")
        
        print(f"\nFinal Registry State:")
        processors = _CommandRegistry.get_registered_processors()
        print(f"  Registered processors: {len(processors)}")
        print(f"  Priority order: {[p.__name__ for p in _CommandRegistry._priority_order]}")
        
        # Show priority mapping
        print(f"\nPriority Mapping:")
        for processor in _CommandRegistry._priority_order:
            priority = _CommandRegistry._processors[processor]
            print(f"  {processor.__name__}: {priority}")
    
    def test_visual_command_processing_demonstration(self):
        """Visual demonstration of command processing."""
        print("\n" + "="*60)
        print("COMMAND REGISTRY - COMMAND PROCESSING DEMONSTRATION")
        print("="*60)
        
        # Register processors
        _CommandRegistry.register(TestCommandProcessor, priority=50)
        _CommandRegistry.register(HighPriorityProcessor, priority=10)
        _CommandRegistry.register(LowPriorityProcessor, priority=90)
        _CommandRegistry.register(UniversalProcessor, priority=100)
        
        test_commands = [
            ("test_basic", "Should match TestCommandProcessor"),
            ("priority", "Should match HighPriorityProcessor (higher priority)"),
            ("unknown_command", "Should match UniversalProcessor (catch-all)"),
            ("anything", "Should match UniversalProcessor"),
            ("", "Empty command - should return unchanged"),
        ]
        
        print(f"\nCommand Processing Tests:")
        for command, description in test_commands:
            print(f"\n  Command: '{command}'")
            print(f"  Expected: {description}")
            
            if command == "":
                # Special case for empty command
                format_state = _FormatState()
                result_state = _CommandRegistry.process_command(command, format_state)
                print(f"  Result: Returned unchanged format state")
            else:
                # Find which processor would handle it
                processor = _CommandRegistry.find_processor(command)
                if processor:
                    print(f"  Processor: {processor.__name__}")
                    
                    # Get command info
                    info = _CommandRegistry.get_command_info(command)
                    print(f"  Priority: {info['priority']}")
                    
                    # Process the command
                    format_state = _FormatState()
                    try:
                        result_state = _CommandRegistry.process_command(command, format_state)
                        outputs = result_state.get_final_outputs()
                        print(f"  Output: '{outputs['terminal']}'")
                    except Exception as e:
                        print(f"  Error: {type(e).__name__}: {e}")
                else:
                    print(f"  Processor: None found")
                    try:
                        format_state = _FormatState()
                        _CommandRegistry.process_command(command, format_state)
                    except UnknownCommandError as e:
                        print(f"  Error: {e}")
    
    def test_visual_priority_demonstration(self):
        """Visual demonstration of priority handling."""
        print("\n" + "="*60)
        print("COMMAND REGISTRY - PRIORITY DEMONSTRATION")
        print("="*60)
        
        # Create processors with different priorities for same command
        class Priority10Processor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'priority_test'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.add_to_output_streams(terminal="Priority 10 processor")
                return format_state
        
        class Priority50Processor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'priority_test'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.add_to_output_streams(terminal="Priority 50 processor")
                return format_state
        
        class Priority90Processor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'priority_test'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.add_to_output_streams(terminal="Priority 90 processor")
                return format_state
        
        # Register in random order
        print(f"\nRegistering processors in random order:")
        _CommandRegistry.register(Priority50Processor, priority=50)
        print(f"  ✅ Priority50Processor (priority: 50)")
        
        _CommandRegistry.register(Priority10Processor, priority=10)
        print(f"  ✅ Priority10Processor (priority: 10)")
        
        _CommandRegistry.register(Priority90Processor, priority=90)
        print(f"  ✅ Priority90Processor (priority: 90)")
        
        print(f"\nPriority Order After Registration:")
        for i, processor in enumerate(_CommandRegistry._priority_order):
            priority = _CommandRegistry._processors[processor]
            print(f"  {i+1}. {processor.__name__} (priority: {priority})")
        
        print(f"\nProcessing 'priority_test' command:")
        format_state = _FormatState()
        result_state = _CommandRegistry.process_command("priority_test", format_state)
        outputs = result_state.get_final_outputs()
        
        print(f"  Result: '{outputs['terminal']}'")
        print(f"  ✅ Highest priority processor (Priority 10) was used")
    
    def test_visual_decorator_demonstration(self):
        """Visual demonstration of decorator usage."""
        print("\n" + "="*60)
        print("COMMAND REGISTRY - DECORATOR DEMONSTRATION")
        print("="*60)
        
        print(f"\nUsing @_command_processor decorator:")
        
        @_command_processor(priority=25)
        class DecoratedCommandProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command.startswith('decorated')
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                format_state.add_to_output_streams(terminal=f"Decorated processor handled: {command}")
                return format_state
        
        print(f"  ✅ DecoratedCommandProcessor automatically registered")
        print(f"  Priority: {_CommandRegistry._processors[DecoratedCommandProcessor]}")
        print(f"  Can process 'decorated*' commands")
        
        # Test the decorated processor
        test_commands = ['decorated_test', 'decorated_example', 'not_decorated']
        
        print(f"\nTesting decorated processor:")
        for command in test_commands:
            can_process = DecoratedCommandProcessor.can_process(command)
            print(f"  Command '{command}': Can process = {can_process}")
            
            if can_process:
                format_state = _FormatState()
                result_state = _CommandRegistry.process_command(command, format_state)
                outputs = result_state.get_final_outputs()
                print(f"    Output: '{outputs['terminal']}'")
    
    def test_visual_registry_management_demonstration(self):
        """Visual demonstration of registry management."""
        print("\n" + "="*60)
        print("COMMAND REGISTRY - REGISTRY MANAGEMENT DEMONSTRATION")
        print("="*60)
        
        print(f"\nRegistry Management Operations:")
        
        # Show initial state
        print(f"\n1. Initial State:")
        processors = _CommandRegistry.get_registered_processors()
        print(f"   Registered processors: {len(processors)}")
        
        # Register some processors
        print(f"\n2. Registering Processors:")
        _CommandRegistry.register(TestCommandProcessor, priority=50)
        print(f"   ✅ Registered TestCommandProcessor")
        
        _CommandRegistry.register(HighPriorityProcessor, priority=10)
        print(f"   ✅ Registered HighPriorityProcessor")
        
        processors = _CommandRegistry.get_registered_processors()
        print(f"   Total registered: {len(processors)}")
        
        # Show registration status
        print(f"\n3. Registration Status Checks:")
        processors_to_check = [TestCommandProcessor, HighPriorityProcessor, LowPriorityProcessor]
        for processor in processors_to_check:
            is_registered = _CommandRegistry.is_registered(processor)
            status = "✅ Registered" if is_registered else "❌ Not registered"
            print(f"   {processor.__name__}: {status}")
        
        # Show command info
        print(f"\n4. Command Information:")
        test_commands = ['test_command', 'priority', 'unknown']
        for command in test_commands:
            info = _CommandRegistry.get_command_info(command)
            if info['can_process']:
                print(f"   '{command}': {info['processor']} (priority: {info['priority']})")
            else:
                print(f"   '{command}': No processor found")
        
        # Unregister a processor
        print(f"\n5. Unregistering Processor:")
        _CommandRegistry.unregister(TestCommandProcessor)
        print(f"   ✅ Unregistered TestCommandProcessor")
        
        is_registered = _CommandRegistry.is_registered(TestCommandProcessor)
        status = "✅ Still registered" if is_registered else "❌ Successfully unregistered"
        print(f"   Status: {status}")
        
        # Clear registry
        print(f"\n6. Clearing Registry:")
        processors_before = len(_CommandRegistry.get_registered_processors())
        print(f"   Processors before clear: {processors_before}")
        
        _CommandRegistry.clear_registry()
        processors_after = len(_CommandRegistry.get_registered_processors())
        print(f"   Processors after clear: {processors_after}")
        print(f"   ✅ Registry cleared successfully")
    
    def test_visual_error_handling_demonstration(self):
        """Visual demonstration of error handling."""
        print("\n" + "="*60)
        print("COMMAND REGISTRY - ERROR HANDLING DEMONSTRATION")
        print("="*60)
        
        print(f"\nError Handling Scenarios:")
        
        # 1. Unknown command
        print(f"\n1. Unknown Command:")
        try:
            format_state = _FormatState()
            _CommandRegistry.process_command("completely_unknown", format_state)
        except UnknownCommandError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 2. Invalid processor registration
        print(f"\n2. Invalid Processor Registration:")
        class NotAProcessor:
            pass
        
        try:
            _CommandRegistry.register(NotAProcessor)
        except TypeError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 3. Duplicate registration
        print(f"\n3. Duplicate Registration:")
        _CommandRegistry.register(TestCommandProcessor)
        try:
            _CommandRegistry.register(TestCommandProcessor)
        except ValueError as e:
            print(f"   ✅ Caught expected error: {e}")
        
        # 4. Processor that raises exception
        print(f"\n4. Processor Exception:")
        class ErrorProcessor(_CommandProcessor):
            @classmethod
            def can_process(cls, command: str) -> bool:
                return command == 'error_test'
            
            @classmethod
            def process(cls, command: str, format_state: _FormatState) -> _FormatState:
                raise RuntimeError("Processor error for demonstration")
        
        _CommandRegistry.register(ErrorProcessor)
        
        try:
            format_state = _FormatState()
            _CommandRegistry.process_command("error_test", format_state)
        except RuntimeError as e:
            print(f"   ✅ Caught processor error: {e}")


if __name__ == "__main__":
    # Run visual demonstrations
    demo = TestCommandRegistryVisualDemonstration()
    demo.test_visual_command_registry_demonstration()
    demo.test_visual_command_processing_demonstration()
    demo.test_visual_priority_demonstration()
    demo.test_visual_decorator_demonstration()
    demo.test_visual_registry_management_demonstration()
    demo.test_visual_error_handling_demonstration()
    
    print("\n" + "="*60)
    print("✅ COMMAND REGISTRY TESTS COMPLETE")
    print("="*60)