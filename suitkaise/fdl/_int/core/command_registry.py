"""
Internal Command Processor Registry for FDL.

This module provides a registration system for command processors,
allowing new command types to be added without modifying core code.

This is internal to the FDL engine and not exposed to users.
"""

from typing import List, Type, Union
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
    
    _processors: List[Type[_CommandProcessor]] = []
    _sorted = False
    _lock = threading.RLock()
    
    @classmethod
    def register(cls, processor_class: Type[_CommandProcessor]) -> None:
        """
        Register a command processor.
        
        Args:
            processor_class: Command processor class to register
            
        Raises:
            TypeError: If processor doesn't inherit from _CommandProcessor
        """
        with cls._lock:
            if not issubclass(processor_class, _CommandProcessor):
                raise TypeError(f"Processor must inherit from _CommandProcessor: {processor_class}")
            
            cls._processors.append(processor_class)

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
            if not isinstance(processor_class, str):
                processor_class = processor_class.__name__

            for proc in cls._processors:
                if proc.__name__ == processor_class:
                    return True
    
    @classmethod
    def unregister(cls, processor_class: Type[_CommandProcessor]) -> None:
        """
        Unregister a command processor.
        
        Args:
            processor_class: Command processor class to unregister
        """
        with cls._lock:
            if processor_class in cls._processors:
                cls._processors.remove(processor_class)
    
    @classmethod
    def _ensure_sorted(cls) -> None:
        """Ensure processors are sorted by priority."""
        with cls._lock:
            if not cls._sorted:
                cls._processors.sort(key=lambda p: p.get_priority())
                cls._sorted = True
    
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
        cls._ensure_sorted()
        
        command = command.strip()
        if not command:
            return format_state
        
        # Try each processor in priority order
        for processor_class in cls._processors:
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
        cls._ensure_sorted()
        return cls._processors.copy()
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered processors (useful for testing)."""
        with cls._lock:
            cls._processors.clear()
            cls._sorted = False
    
    @classmethod
    def get_command_info(cls, command: str) -> dict:
        """
        Get information about which processor would handle a command.
        
        Args:
            command: Command to check
            
        Returns:
            dict: Information about the command processor
        """
        cls._ensure_sorted()
        
        for processor_class in cls._processors:
            if processor_class.can_process(command):
                return {
                    'processor': processor_class.__name__,
                    'priority': processor_class.get_priority(),
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

        # Set priority if not already set
        if not hasattr(processor_class, 'get_priority'):
            processor_class._priority = priority
            processor_class.get_priority = classmethod(lambda cls: cls._priority)
        
        # Register the processor
        _CommandRegistry.register(processor_class)
        
        return processor_class
    
    return decorator