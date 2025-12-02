# core/format_registry.py
"""
Format Registry for FDL.

Manages named format strings that can be reused across FDL processing.
Formats are essentially named command strings that get substituted during processing.
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class _Format:
    """
    Internal Format class for storing named format strings.
    
    This represents a reusable format that contains a string of FDL commands
    that can be substituted when referenced via </fmt name> syntax.
    """
    name: str
    format: str
    
    def __post_init__(self):
        """Validate format after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Format name cannot be empty")
        if not isinstance(self.format, str):
            raise ValueError("Format string must be a string")


class _FormatRegistry:
    """
    Registry for managing named format strings.
    
    This is a singleton registry that stores format definitions that can be
    referenced throughout FDL processing via </fmt name> commands.
    """
    
    _instance: Optional['_FormatRegistry'] = None
    _formats: Dict[str, _Format] = {}
    
    def __new__(cls) -> '_FormatRegistry':
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register_format(self, format_obj: _Format) -> None:
        """
        Register a new format in the registry.
        
        Args:
            format_obj: Format object to register
            
        Raises:
            ValueError: If format name is already registered
        """
        name = format_obj.name.strip().lower()
        
        if name in self._formats:
            raise ValueError(f"Format '{name}' is already registered")
        
        self._formats[name] = format_obj
    
    def get_format(self, name: str) -> Optional[_Format]:
        """
        Get a format by name.
        
        Args:
            name: Name of format to retrieve
            
        Returns:
            _Format: Format object if found, None otherwise
        """
        return self._formats.get(name.strip().lower())
    
    def has_format(self, name: str) -> bool:
        """
        Check if a format is registered.
        
        Args:
            name: Name of format to check
            
        Returns:
            bool: True if format exists, False otherwise
        """
        return name.strip().lower() in self._formats
    
    def unregister_format(self, name: str) -> bool:
        """
        Remove a format from the registry.
        
        Args:
            name: Name of format to remove
            
        Returns:
            bool: True if format was removed, False if not found
        """
        name = name.strip().lower()
        if name in self._formats:
            del self._formats[name]
            return True
        return False
    
    def clear_formats(self) -> None:
        """Clear all registered formats."""
        self._formats.clear()
    
    def list_formats(self) -> Dict[str, str]:
        """
        Get a dictionary of all registered formats.
        
        Returns:
            Dict[str, str]: Mapping of format names to format strings
        """
        return {name: fmt.format for name, fmt in self._formats.items()}


# Global registry instance
_format_registry = _FormatRegistry()


def get_format_registry() -> _FormatRegistry:
    """Get the global format registry instance."""
    return _format_registry


def register_format(name: str, format_string: str) -> None:
    """
    Convenience function to register a format.
    
    Args:
        name: Name of the format
        format_string: Format command string
    """
    format_obj = _Format(name=name, format=format_string)
    _format_registry.register_format(format_obj)