"""
FDL Reconstructor - Combines parsed elements into final formatted strings

This module takes parsed fdl elements and reconstructs them into final output strings
with proper ANSI formatting, variable substitution, and object processing.

Key responsibilities:
- Process elements in position order
- Manage formatting state transitions  
- Handle mixed content (commands + objects at same position)
- Variable substitution and validation
- Error handling with detailed messages

FIXED: Removed circular import by removing dependency on removed function.
"""

import warnings
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

warnings.simplefilter("always")

# Fixed imports - removed _apply_format_to_state (no longer exists)
try:
    # Try relative imports first (when used as module)
    from .parser import _fdlParser, _ParseResult, _ParsedElement
    from .command_processor import _get_command_processor, _FormattingState
    from .object_processor import _get_object_processor
except ImportError:
    # Fall back to direct imports (when run as script)
    from parser import _fdlParser, _ParseResult, _ParsedElement
    from command_processor import _get_command_processor, _FormattingState
    from object_processor import _get_object_processor


class ReconstructionError(Exception):
    """Raised when string reconstruction fails."""
    pass


class VariableMismatchError(ReconstructionError):
    """Raised when variable count doesn't match provided values."""
    pass


def _reconstruct_fdl_string(format_string: str, values: Optional[Tuple] = None, 
                          default_state: Optional[_FormattingState] = None) -> str:
    """
    Reconstruct an fdl format string into final formatted output.

    Automatically adds reset codes at the end to prevent format bleed.

    Args:
        format_string (str): fdl format string to process
        values (Optional[Tuple]): Values for variable substitution
        default_state (Optional[_FormattingState]): Default formatting state
        
    Returns:
        str: Final formatted string with ANSI codes and automatic reset
        
    Raises:
        ReconstructionError: If reconstruction fails
        VariableMismatchError: If variable count mismatch
        
    Example:
        result = _reconstruct_fdl_string(
            "User </bold><name></end bold> at <time:>", 
            ("Alice",)
        )
        # Returns: "User \033[1mAlice\033[22m at 14:30:15.123456"
    """
    
    # Step 1: Parse the format string
    parser = _fdlParser()
    try:
        parsed = parser.parse(format_string, values)
    except Exception as e:
        raise ReconstructionError(f"Parsing failed: {e}")
    
    # Step 2: Validate variables before processing
    if not _validate_variables(parsed, values, format_string):
        return "[ERROR: Variable count mismatch - see warning above]"
    
    # Step 3: Initialize processors and state
    command_proc = _get_command_processor()
    object_proc = _get_object_processor()
    
    # Initialize formatting state
    current_state = default_state.copy() if default_state else _FormattingState()
    
    # Step 4: Group elements by position for ordered processing
    positions = _group_by_position(parsed.elements)
    
    # Step 5: Process each position in order
    output_parts = []
    var_index = 0
    
    try:
        for position in sorted(positions.keys()):
            elements = positions[position]
            
            # Process all elements at this position
            result, var_index = _process_position(
                elements, values, var_index, current_state, 
                command_proc, object_proc
            )
            
            if result:  # Only add non-empty results
                output_parts.append(result)
                
    except Exception as e:
        raise ReconstructionError(f"Processing failed at position {position}: {e}")
    
    # Step 6: Join all parts and add automatic reset if needed
    final_string = ''.join(output_parts)

    final_string += command_proc.generate_reset_ansi()

    return final_string

def _validate_variables(parse_result: _ParseResult, values: Optional[Tuple], 
                       format_string: str) -> bool:
    """
    Validate that variable count matches provided values.
    
    Args:
        parse_result (_ParseResult): Parsed format string
        values (Optional[Tuple]): Provided values
        format_string (str): Original format string for error messages
        
    Returns:
        bool: True if validation passes, False if mismatch
        
    Logs detailed warning messages on mismatch.
    """
    # Count regular variables
    regular_vars = len(parse_result.variables)
    
    # Count object variables that need values (have non-empty variable part)
    object_vars = 0
    object_var_names = []
    
    for obj in parse_result.objects:
        if ':' in obj.content:
            obj_type, obj_var = obj.content.split(':', 1)
            obj_var = obj_var.strip()
            if obj_var:  # Only count if variable part is not empty
                object_vars += 1
                object_var_names.append(obj.content)
    
    # Calculate totals
    total_expected = regular_vars + object_vars
    provided = len(values) if values else 0
    
    # Check for mismatch
    if total_expected != provided:
        # Build detailed error message
        var_names = [var.content for var in parse_result.variables]
        all_var_names = var_names + object_var_names
        
        error_msg = f"""
fdl.print() variable mismatch:
  Expected {total_expected} values for: {all_var_names}
  Received {provided} values: {list(values) if values else []}
  
Format string: "{format_string}"
        """.strip()
        
        warnings.warn(error_msg, UserWarning)
        return False
    
    return True


def _group_by_position(elements: List[_ParsedElement]) -> Dict[int, List[_ParsedElement]]:
    """
    Group parsed elements by their position index.
    
    Args:
        elements (List[_ParsedElement]): All parsed elements
        
    Returns:
        Dict[int, List[_ParsedElement]]: Elements grouped by position
        
    Example:
        {
            0: [text_element],
            1: [command_element1, command_element2],  # Multiple at same position
            2: [variable_element],
            3: [object_element, command_element3]     # Mixed content
        }
    """
    positions = defaultdict(list)
    
    for element in elements:
        positions[element.position].append(element)
    
    return dict(positions)


def _process_position(elements: List[_ParsedElement], values: Optional[Tuple], 
                     var_index: int, current_state: _FormattingState,
                     command_proc, object_proc) -> Tuple[str, int]:
    """
    Process all elements at a single position.
    
    Args:
        elements (List[_ParsedElement]): All elements at this position
        values (Optional[Tuple]): Values for substitution
        var_index (int): Current index in values tuple
        current_state (_FormattingState): Current formatting state (modified in-place)
        command_proc: Command processor instance
        object_proc: Object processor instance
        
    Returns:
        Tuple[str, int]: (output_string, new_var_index)
        
    Processing order:
    1. Text elements - add directly to output
    2. Mixed content (commands + objects) - delegate to object processor
    3. Pure commands - update formatting state
    4. Variables - substitute values
    """
    # Separate elements by type
    text_elements = [e for e in elements if e.element_type == 'text']
    command_elements = [e for e in elements if e.element_type == 'command']
    variable_elements = [e for e in elements if e.element_type == 'variable']
    object_elements = [e for e in elements if e.element_type == 'object']
    
    output_parts = []
    new_var_index = var_index
    
    # Handle text elements (always first)
    for text_elem in text_elements:
        output_parts.append(text_elem.content)
    
    # Handle mixed content (objects with commands)
    if object_elements:
        result, new_var_index = _handle_mixed_content(
            object_elements, command_elements, values, new_var_index, object_proc
        )
        output_parts.append(result)
        
    # Handle pure commands (no objects at this position)
    elif command_elements:
        ansi_codes = _handle_pure_commands(command_elements, current_state, command_proc)
        output_parts.append(ansi_codes)
    
    # Handle variables
    for var_elem in variable_elements:
        if new_var_index < len(values):
            output_parts.append(str(values[new_var_index]))
            new_var_index += 1
        else:
            # This should be caught by validation, but handle gracefully
            output_parts.append(f"[MISSING_VALUE_{new_var_index}]")
            new_var_index += 1
    
    return ''.join(output_parts), new_var_index


def _handle_mixed_content(object_elements: List[_ParsedElement], 
                         command_elements: List[_ParsedElement],
                         values: Optional[Tuple], var_index: int,
                         object_proc) -> Tuple[str, int]:
    """
    Handle mixed content where objects and commands appear at same position.
    
    Args:
        object_elements (List[_ParsedElement]): Object elements at this position
        command_elements (List[_ParsedElement]): Command elements at this position  
        values (Optional[Tuple]): Values for substitution
        var_index (int): Current index in values tuple
        object_proc: Object processor instance
        
    Returns:
        Tuple[str, int]: (formatted_object_result, new_var_index)
        
    Strategy:
    - Pass ALL commands to object processor
    - Object processor filters valid vs invalid commands
    - Invalid commands (like formatting commands) are warned about and ignored
    - Object processor handles the object with valid commands only
    """
    if len(object_elements) != 1:
        # Should only be one object at a position, but handle gracefully
        warnings.warn(f"Multiple objects at same position: {[obj.content for obj in object_elements]}")
        object_elem = object_elements[0]  # Use first one
    else:
        object_elem = object_elements[0]
    
    # Extract all command content strings
    command_strings = [cmd.content for cmd in command_elements]
    
    # Let object processor handle everything (it will filter valid vs invalid commands)
    try:
        result, new_var_index = object_proc.process_object(
            object_elem.content, command_strings, values or (), var_index
        )
        return result, new_var_index
        
    except Exception as e:
        warnings.warn(f"Object processing failed: {e}")
        return f"[OBJECT_ERROR: {e}]", var_index


def _handle_pure_commands(command_elements: List[_ParsedElement], 
                         current_state: _FormattingState,
                         command_proc) -> str:
    """
    Handle pure formatting commands (no objects at this position).
    
    ENHANCED VERSION: Properly handles format chaining and format ending.
    
    Args:
        command_elements (List[_ParsedElement]): Command elements at this position
        current_state (_FormattingState): Current formatting state (modified in-place)
        command_proc: Command processor instance
        
    Returns:
        str: ANSI codes to apply formatting changes
        
    Special handling:
    - Reset commands clear state completely (no default restoration)
    - Format commands are chained properly (later formats override earlier ones)
    - Format ending commands properly remove format effects
    - State is properly tracked for all command types
    """
    if not command_elements:
        return ""
    
    # Extract command content strings
    command_strings = [cmd.content for cmd in command_elements]
    
    # Check for reset commands first (they override everything)
    reset_commands = [cmd for cmd in command_strings if cmd in ['reset', 'end all']]
    if reset_commands:
        # True reset - completely blank slate
        current_state.reset()
        # Generate reset ANSI
        return command_proc.generate_reset_ansi()
    
    # Separate different types of commands
    format_commands = [cmd for cmd in command_strings if cmd.startswith('fmt ')]
    end_commands = [cmd for cmd in command_strings if cmd.startswith('end ')]
    regular_commands = [cmd for cmd in command_strings if not cmd.startswith(('fmt ', 'end '))]
    
    # Store the starting state for ANSI generation
    starting_state = current_state.copy()
    
    # Process format ending commands FIRST (remove effects)
    for end_cmd in end_commands:
        _process_end_command(end_cmd, current_state)
    
    # Process format commands (apply effects, with proper chaining)
    for fmt_cmd in format_commands:
        format_name = fmt_cmd[4:].strip()  # Remove 'fmt ' prefix
        try:
            _apply_format_to_current_state(format_name, current_state)
        except Exception as e:
            warnings.warn(f"Format command '{fmt_cmd}' failed: {e}")
    
    # Process regular commands (apply to current accumulated state)
    if regular_commands:
        try:
            temp_state = current_state.copy()
            new_state, _ = command_proc.process_commands(regular_commands, temp_state)
            
            # Update current state with regular command results
            current_state.text_color = new_state.text_color
            current_state.background_color = new_state.background_color
            current_state.bold = new_state.bold
            current_state.italic = new_state.italic
            current_state.underline = new_state.underline
            current_state.strikethrough = new_state.strikethrough
            current_state.active_formats = new_state.active_formats.copy()
            
        except Exception as e:
            warnings.warn(f"Regular command processing failed: {e}")
    
    # Generate single ANSI transition from starting state to final state
    ansi_codes = command_proc.converter.generate_transition_ansi(starting_state, current_state)
    
    return ansi_codes


def _process_end_command(end_cmd: str, current_state: _FormattingState) -> None:
    """
    Process an end command to remove format effects.
    
    Args:
        end_cmd (str): End command (e.g., "end format2", "end bold")
        current_state (_FormattingState): State to modify
    """
    end_target = end_cmd[4:].strip()  # Remove "end " prefix
    
    # Handle ending specific formats
    if end_target.startswith('fmt '):
        format_name = end_target[4:].strip()
        _remove_format_from_state(format_name, current_state)
        return
    
    # Handle ending named formats directly
    if end_target in current_state.active_formats:
        _remove_format_from_state(end_target, current_state)
        return
    
    # Handle ending individual properties
    if end_target == 'bold':
        current_state.bold = False
    elif end_target == 'italic':
        current_state.italic = False
    elif end_target == 'underline':
        current_state.underline = False
    elif end_target == 'strikethrough':
        current_state.strikethrough = False
    elif end_target in ['red', 'green', 'blue', 'yellow', 'purple', 'cyan', 'magenta', 'white', 'black'] or end_target.startswith('#') or end_target.startswith('rgb('):
        current_state.text_color = None
    elif end_target.startswith('bkg '):
        current_state.background_color = None
    else:
        warnings.warn(f"Unknown end target: {end_target}")


def _apply_format_to_current_state(format_name: str, current_state: _FormattingState) -> None:
    """
    Apply a format to the current state (for chaining).
    
    Args:
        format_name (str): Name of format to apply
        current_state (_FormattingState): State to modify
    """
    try:
        # Use late import to avoid circular dependencies
        try:
            from .format_class import _get_compiled_format
        except ImportError:
            from format_class import _get_compiled_format
        
        compiled = _get_compiled_format(format_name)
        if not compiled:
            raise Exception(f"Format '{format_name}' not found")
        
        # Apply the format's state to current state (override conflicts)
        format_state = compiled.formatting_state
        
        # Override properties (later formats win)
        if format_state.text_color is not None:
            current_state.text_color = format_state.text_color
        if format_state.background_color is not None:
            current_state.background_color = format_state.background_color
        if format_state.bold:
            current_state.bold = True
        if format_state.italic:
            current_state.italic = True
        if format_state.underline:
            current_state.underline = True
        if format_state.strikethrough:
            current_state.strikethrough = True
        
        # Track active format
        current_state.active_formats.add(format_name)
        
    except Exception as e:
        raise Exception(f"Failed to apply format '{format_name}': {e}")


def _remove_format_from_state(format_name: str, current_state: _FormattingState) -> None:
    """
    Remove a format's effects from the current state.
    
    Args:
        format_name (str): Name of format to remove
        current_state (_FormattingState): State to modify
    """
    try:
        # Use late import to avoid circular dependencies
        try:
            from .format_class import _get_compiled_format
        except ImportError:
            from format_class import _get_compiled_format
        
        compiled = _get_compiled_format(format_name)
        if not compiled:
            warnings.warn(f"Format '{format_name}' not found for removal")
            return
        
        format_state = compiled.formatting_state
        
        # Remove the format's effects (reset to None/False if this format set them)
        # Note: This is a simplified approach - in reality we'd need to track
        # which format set which property to avoid removing effects from other formats
        
        if format_state.text_color is not None:
            current_state.text_color = None
        if format_state.background_color is not None:
            current_state.background_color = None
        if format_state.bold:
            current_state.bold = False
        if format_state.italic:
            current_state.italic = False
        if format_state.underline:
            current_state.underline = False
        if format_state.strikethrough:
            current_state.strikethrough = False
        
        # Remove from active formats
        current_state.active_formats.discard(format_name)
        
    except Exception as e:
        warnings.warn(f"Failed to remove format '{format_name}': {e}")