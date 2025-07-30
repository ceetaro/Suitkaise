"""
Internal Command Processor Registry for FDL.

This module provides a registration system for command processors,
allowing new command types to be added without modifying core code.

This is internal to the FDL engine and not exposed to users.
"""

from typing import List, Type, Union, Optional, Dict
import threading
from abc import ABC, abstractmethod
from .format_state import _FormatState


class UnknownCommandError(Exception):
    """Raised when a command is not recognized by any processor."""
    pass


class _CommandProcessor(ABC):
    """
    Abstract base class for command processors.
    
    All command processors must inherit from this and implement
    the required methods for registration and processing.
    """
    
    @classmethod
    @abstractmethod
    def can_process(cls, command: str) -> bool:
        """
        Check if this processor can handle the given command.
        
        Args:
            command: Command string to check
            
        Returns:
            bool: True if this processor can handle the command
        """
        pass
    
    @classmethod
    @abstractmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a command and update format state.
        
        Args:
            command: Command to process
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        pass

    @classmethod
    def get_priority(cls) -> int:
        """
        Get processor priority for ordering.
        
        Lower numbers = higher priority (processed first).
        Default priority is 100.
        
        Returns:
            int: Priority value
        """
        if not hasattr(cls, '_priority'):
            return 100
        
        if 1 <= cls._priority <= 100:
            return cls._priority
        
        else:
            priority = max(1, min(100, cls._priority))
            cls._priority = priority

        return priority
        


class _CommandRegistry:
    """
    Registry for command processors with automatic registration and priority ordering.
    
    This class manages all command processors and routes commands to the
    appropriate processor based on can_process() checks.
    """
    
    _processors: Dict[Type[_CommandProcessor], int] = {}  # processor -> priority
    _priority_order: List[Type[_CommandProcessor]] = []   # ordered by priority
    _lock = threading.RLock()
    
    def __init__(self):
        """Initialize command registry instance (uses class-level processors)."""
        pass  # All functionality is at class level
    
    def process_command(self, command: str, format_state: _FormatState) -> _FormatState:
        """Instance method that delegates to class method."""
        return _CommandRegistry.process_command(command, format_state)
    
    @classmethod
    def register(cls, processor_class: Type[_CommandProcessor], priority: int = 100) -> None:
        """
        Register a command processor with priority.
        
        Args:
            processor_class: Command processor class to register
            priority: Priority value (lower = higher priority)
            
        Raises:
            TypeError: If processor doesn't inherit from _CommandProcessor
            ValueError: If processor is already registered
        """
        with cls._lock:
            if not issubclass(processor_class, _CommandProcessor):
                raise TypeError(f"Processor must inherit from _CommandProcessor: {processor_class}")
            
            if processor_class in cls._processors:
                raise ValueError(f"Processor already registered: {processor_class}")
            
            cls._processors[processor_class] = priority
            cls._update_priority_order()
    
    @classmethod
    def _update_priority_order(cls) -> None:
        """Update the priority order list."""
        cls._priority_order = sorted(cls._processors.keys(), 
                                   key=lambda p: cls._processors[p])
    
    @classmethod
    def find_processor(cls, command: str) -> Optional[Type[_CommandProcessor]]:
        """
        Find a processor that can handle the given command.
        
        Args:
            command: Command to find processor for
            
        Returns:
            Type[_CommandProcessor] or None: Processor that can handle the command
        """
        for processor_class in cls._priority_order:
            if processor_class.can_process(command):
                return processor_class
        return None

    @classmethod
    def is_registered(cls, processor_class: Union[Type[_CommandProcessor], str]) -> bool:
        """
        Check if a command processor is registered.
        
        Args:
            processor_class: Command processor class to check
            
        Returns:
            bool: True if the processor is registered
        """
        with cls._lock:
            if isinstance(processor_class, str):
                # Check by name
                for proc in cls._processors:
                    if proc.__name__ == processor_class:
                        return True
                return False
            else:
                # Check by class
                return processor_class in cls._processors
    
    @classmethod
    def unregister(cls, processor_class: Type[_CommandProcessor]) -> None:
        """
        Unregister a command processor.
        
        Args:
            processor_class: Command processor class to unregister
        """
        with cls._lock:
            if processor_class in cls._processors:
                del cls._processors[processor_class]
                cls._update_priority_order()
    
    @classmethod
    def _ensure_sorted(cls) -> None:
        """Ensure processors are sorted by priority."""
        # No longer needed - priority order is maintained automatically
        pass
    
    @classmethod
    def process_command(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a command by finding and using the appropriate processor.
        
        Args:
            command: Command to process
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
            
        Raises:
            UnknownCommandError: If no processor can handle the command
        """
        command = command.strip()
        if not command:
            return format_state
        
        # Try each processor in priority order
        for processor_class in cls._priority_order:
            if processor_class.can_process(command):
                return processor_class.process(command, format_state)
        
        # No processor could handle the command
        raise UnknownCommandError(f"Unknown command: '{command}'")
    
    @classmethod
    def get_registered_processors(cls) -> List[Type[_CommandProcessor]]:
        """
        Get list of all registered processors.
        
        Returns:
            List[Type[_CommandProcessor]]: List of registered processor classes
        """
        return list(cls._processors.keys())
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered processors (useful for testing)."""
        with cls._lock:
            cls._processors.clear()
            cls._priority_order.clear()
    
    @classmethod
    def get_command_info(cls, command: str) -> dict:
        """
        Get information about which processor would handle a command.
        
        Args:
            command: Command to check
            
        Returns:
            dict: Information about the command processor
        """
        for processor_class in cls._priority_order:
            if processor_class.can_process(command):
                return {
                    'processor': processor_class.__name__,
                    'priority': cls._processors[processor_class],
                    'can_process': True
                }
        
        return {
            'processor': None,
            'priority': None,
            'can_process': False
        }


def _register_command_processor(processor_class: Type[_CommandProcessor]) -> None:
    """
    Convenience function to register a command processor.
    
    Args:
        processor_class: Command processor class to register
    """
    _CommandRegistry.register(processor_class)


def _process_command(command: str, format_state: _FormatState) -> _FormatState:
    """
    Convenience function to process a command.
    
    Args:
        command: Command to process
        format_state: Current format state
        
    Returns:
        _FormatState: Updated format state
    """
    return _CommandRegistry.process_command(command, format_state)


# Registry decorator for easy registration
def _command_processor(priority: int = 100):
    """
    Decorator to automatically register command processors.
    
    Args:
        priority: Priority for this processor (lower = higher priority)
        
    Returns:
        Decorator function
        
    Usage:
        @_command_processor(priority=50)
        class _MyCommandProcessor(_CommandProcessor):
            ...
    """
    def decorator(processor_class: Type[_CommandProcessor]):

        if not issubclass(processor_class, _CommandProcessor):
            raise TypeError(f"Processor must inherit from _CommandProcessor: {processor_class}")
        
        # check if already registered
        if _CommandRegistry.is_registered(processor_class.__name__):
            raise ValueError(f"Processor already registered: {processor_class}")

        # Set priority 
        processor_class._priority = priority
        
        # Register the processor
        _CommandRegistry.register(processor_class)
        
        return processor_class
    
    return decorator