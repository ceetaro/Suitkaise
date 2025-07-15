"""
INTERNAL format compilation and registry system for fdl.

This module provides ONLY the internal machinery for format compilation.
All public interfaces are in suitkaise.fdl.api

Internal components:
- _CompiledFormat: Internal representation of compiled formats
- _FormatRegistry: Global registry with thread-safe access
- _compile_format_string: Internal compilation function
- _apply_format_to_state: Internal function for command processor integration
"""

import threading
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

try:
    # Try relative imports first (when used as module)
    from .parser import _fdlParser
    from .command_processor import _get_command_processor, _FormattingState
except ImportError:
    # Fall back to direct imports (when run as script)
    from parser import _fdlParser
    from command_processor import _get_command_processor, _FormattingState


# Exception classes - these will be re-exported by public API
class FormatError(Exception):
    """Raised when format compilation fails."""
    pass


class InvalidFormatError(FormatError):
    """Raised when format string is syntactically invalid."""
    pass


class CircularReferenceError(FormatError):
    """Raised when format inheritance creates circular references."""
    pass


class FormatNotFoundError(FormatError):
    """Raised when referenced format is not found in registry."""
    pass


@dataclass
class _CompiledFormat:
    """
    INTERNAL: Representation of a compiled format.
    
    This is purely internal - users never see this directly.
    """
    name: str
    formatting_state: _FormattingState
    direct_ansi: str
    referenced_formats: Set[str]
    original_string: str
    compilation_order: int


class _FormatRegistry:
    """
    INTERNAL: Global registry for compiled formats.
    
    Thread-safe registry that handles storage, lookup, and dependency resolution.
    Only accessed through internal functions.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._formats: Dict[str, _CompiledFormat] = {}
        self._compilation_counter = 0
        self._lock = threading.RLock()
    
    def _register(self, compiled_format: _CompiledFormat) -> None:
        """INTERNAL: Register a compiled format."""
        with self._lock:
            # Check for circular references before adding
            self._check_circular_references(compiled_format.name, compiled_format.referenced_formats)
            self._formats[compiled_format.name] = compiled_format
            self._compilation_counter += 1
    
    def _get(self, name: str) -> Optional[_CompiledFormat]:
        """INTERNAL: Get a compiled format by name."""
        with self._lock:
            return self._formats.get(name)
    
    def _exists(self, name: str) -> bool:
        """INTERNAL: Check if a format exists."""
        with self._lock:
            return name in self._formats
    
    def _list_all(self) -> List[str]:
        """INTERNAL: Get list of all format names."""
        with self._lock:
            return list(self._formats.keys())
    
    def _clear(self) -> None:
        """INTERNAL: Clear all formats."""
        with self._lock:
            self._formats.clear()
            self._compilation_counter = 0
    
    def _get_dependencies(self, name: str) -> Set[str]:
        """INTERNAL: Get all format dependencies recursively."""
        with self._lock:
            if name not in self._formats:
                return set()
            
            dependencies = set()
            to_check = [name]
            
            while to_check:
                current = to_check.pop()
                if current in self._formats:
                    current_deps = self._formats[current].referenced_formats
                    for dep in current_deps:
                        if dep not in dependencies:
                            dependencies.add(dep)
                            to_check.append(dep)
            
            return dependencies
    
    def _check_circular_references(self, format_name: str, references: Set[str]) -> None:
        """INTERNAL: Check for circular references."""
        for ref_name in references:
            if ref_name == format_name:
                raise CircularReferenceError(f"Format '{format_name}' cannot reference itself")
            
            if ref_name in self._formats:
                ref_dependencies = self._get_dependencies(ref_name)
                if format_name in ref_dependencies:
                    raise CircularReferenceError(
                        f"Circular reference: '{format_name}' -> '{ref_name}' -> ... -> '{format_name}'"
                    )


# Global format registry instance - purely internal
_global_registry: Optional[_FormatRegistry] = None


def _get_format_registry() -> _FormatRegistry:
    """INTERNAL: Get the global format registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = _FormatRegistry()
    return _global_registry


def _compile_format_string(name: str, format_string: str) -> _CompiledFormat:
    """
    INTERNAL: Compile a format string into internal representation.
    
    Called by public Format class constructor.
    """
    # Parse the format string
    parser = _fdlParser()
    try:
        parsed = parser.parse(format_string, values=())
    except Exception as e:
        raise InvalidFormatError(f"Failed to parse format string '{format_string}': {e}")
    
    # Validate format string content
    if parsed.variables:
        var_names = [var.content for var in parsed.variables]
        raise InvalidFormatError(f"Format strings cannot contain variables: {var_names}")
    
    if parsed.objects:
        obj_names = [obj.content for obj in parsed.objects]
        raise InvalidFormatError(f"Format strings cannot contain objects: {obj_names}")
    
    if parsed.text_segments:
        text_content = ''.join(seg.content for seg in parsed.text_segments).strip()
        if text_content:
            raise InvalidFormatError(f"Format strings cannot contain text content: '{text_content}'")
    
    # Extract and process commands
    command_elements = parsed.commands
    if not command_elements:
        raise InvalidFormatError("Format string must contain at least one command")
    
    command_proc = _get_command_processor()
    referenced_formats = set()
    formatting_commands = []
    
    for cmd_elem in command_elements:
        cmd_content = cmd_elem.content
        
        if cmd_content.startswith('fmt '):
            ref_name = cmd_content[4:].strip()
            if not ref_name:
                raise InvalidFormatError("Format reference cannot be empty")
            referenced_formats.add(ref_name)
            formatting_commands.append(cmd_content)
        else:
            formatting_commands.append(cmd_content)
    
    # Validate referenced formats exist
    registry = _get_format_registry()

    # Check for self-reference (circular reference) 
    if name in referenced_formats:
        raise CircularReferenceError(f"Format '{name}' cannot reference itself")

    # Validate non-self referenced formats exist
    for ref_name in referenced_formats:
        if ref_name != name and not registry._exists(ref_name):
            raise FormatNotFoundError(f"Referenced format '{ref_name}' not found")
    
    # Compile to target state
    try:
        blank_state = _FormattingState()
        target_state, _ = command_proc.process_commands(formatting_commands, blank_state)
    except Exception as e:
        raise InvalidFormatError(f"Failed to process commands: {e}")
    
    # Generate direct ANSI
    direct_ansi = command_proc.converter.generate_state_ansi(target_state)
    
    # Create compiled format
    compilation_order = _get_format_registry()._compilation_counter + 1
    
    return _CompiledFormat(
        name=name,
        formatting_state=target_state,
        direct_ansi=direct_ansi,
        referenced_formats=referenced_formats,
        original_string=format_string,
        compilation_order=compilation_order
    )


def _register_compiled_format(compiled_format: _CompiledFormat) -> None:
    """INTERNAL: Register a compiled format in the global registry."""
    _get_format_registry()._register(compiled_format)


def _get_compiled_format(name: str) -> Optional[_CompiledFormat]:
    """INTERNAL: Get a compiled format by name."""
    return _get_format_registry()._get(name)


def _apply_format_to_state(format_name: str, current_state: _FormattingState) -> Tuple[_FormattingState, str]:
    """
    INTERNAL: Apply a named format to a formatting state.
    
    Used by command processor when handling 'fmt formatname' commands.
    """
    registry = _get_format_registry()
    compiled = registry._get(format_name)
    
    if not compiled:
        raise FormatNotFoundError(f"Format '{format_name}' not found")
    
    command_proc = _get_command_processor()
    ansi_sequence = command_proc.converter.generate_transition_ansi(
        current_state, compiled.formatting_state
    )
    
    return compiled.formatting_state.copy(), ansi_sequence


# Additional internal functions for public API
def _format_exists_internal(name: str) -> bool:
    """INTERNAL: Check if format exists."""
    return _get_format_registry()._exists(name)


def _list_all_formats_internal() -> List[str]:
    """INTERNAL: List all format names."""
    return sorted(_get_format_registry()._list_all())


def _clear_all_formats_internal() -> None:
    """INTERNAL: Clear all formats."""
    _get_format_registry()._clear()


def _get_format_dependencies_internal(name: str) -> Set[str]:
    """INTERNAL: Get format dependencies."""
    return _get_format_registry()._get_dependencies(name)