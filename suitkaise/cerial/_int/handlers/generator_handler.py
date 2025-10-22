"""
Handler for generator objects.

Generators maintain state and can be paused/resumed. Serializing their
full execution state is extremely challenging, so we take a pragmatic approach.
"""

import types
from typing import Any, Dict, List
from .base_class import Handler


class GeneratorSerializationError(Exception):
    """Raised when generator serialization fails."""
    pass


class GeneratorHandler(Handler):
    """
    Serializes generator objects.
    
    Strategy:
    - Exhaust the generator and capture remaining values
    - Store the generator function if available
    - On reconstruction, return an iterator over the remaining values
    
    Important: Generator execution state (local variables, instruction pointer)
    cannot be fully reconstructed. We can only preserve remaining values.
    """
    
    type_name = "generator"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a generator."""
        return isinstance(obj, types.GeneratorType)
    
    def extract_state(self, obj: types.GeneratorType) -> Dict[str, Any]:
        """
        Extract generator state.
        
        What we capture:
        - remaining_values: Values not yet yielded from the generator
        - generator_name: Name of the generator function (if available)
        - generator_code: Code object of the generator function (if available)
        
        Note: This EXHAUSTS the generator! Original will be empty.
        This is the only way to preserve the remaining values.
        """
        # Get generator function info if available
        generator_name = obj.__name__ if hasattr(obj, '__name__') else None
        generator_qualname = obj.__qualname__ if hasattr(obj, '__qualname__') else None
        
        # Try to get the generator's code object
        generator_code = None
        if hasattr(obj, 'gi_code'):
            generator_code = obj.gi_code
        
        # Try to get generator frame locals (current state)
        frame_locals = None
        if hasattr(obj, 'gi_frame') and obj.gi_frame:
            try:
                frame_locals = dict(obj.gi_frame.f_locals)
            except (AttributeError, RuntimeError):
                # Frame might be None if generator is exhausted
                pass
        
        # Exhaust generator to get remaining values
        remaining_values = []
        try:
            for value in obj:
                remaining_values.append(value)
        except StopIteration:
            pass
        except Exception as e:
            raise GeneratorSerializationError(
                f"Failed to exhaust generator {generator_name}: {e}"
            )
        
        return {
            "generator_name": generator_name,
            "generator_qualname": generator_qualname,
            "generator_code": generator_code,  # Will be recursively serialized
            "frame_locals": frame_locals,  # Will be recursively serialized
            "remaining_values": remaining_values,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct generator.
        
        Since we cannot reconstruct true generator execution state, we return
        an iterator over the remaining values. This preserves the values but
        not the generator's pause/resume behavior.
        
        For more advanced use cases, users should implement custom
        __serialize__/__deserialize__ methods on classes that wrap generators.
        """
        # Return iterator over remaining values
        # This is not a true generator but preserves the values
        return iter(state["remaining_values"])

