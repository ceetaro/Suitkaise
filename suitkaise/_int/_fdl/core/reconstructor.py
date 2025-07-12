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
"""

import warnings
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

warnings.simplefilter("always")

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
    
    Args:
        format_string (str): fdl format string to process
        values (Optional[Tuple]): Values for variable substitution
        default_state (Optional[_FormattingState]): Default formatting state
        
    Returns:
        str: Final formatted string with ANSI codes
        
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
    
    # Step 6: Join all parts and add final reset if any formatting was applied
    final_string = ''.join(output_parts)
    
    # Add reset if we have any active formatting to prevent bleed-through
    if not current_state.__eq__(_FormattingState()):  # If state is not default/empty
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
    
    Args:
        command_elements (List[_ParsedElement]): Command elements at this position
        current_state (_FormattingState): Current formatting state (modified in-place)
        command_proc: Command processor instance
        
    Returns:
        str: ANSI codes to apply formatting changes
        
    Special handling:
    - Reset commands clear state completely (no default restoration)
    - Multiple commands are processed as a batch for efficiency
    - Format override warnings are generated for conflicting commands
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
    
    # Process regular commands
    try:
        new_state, ansi_codes = command_proc.process_commands(
            command_strings, current_state
        )
        
        # Update current state in-place by copying all attributes
        current_state.text_color = new_state.text_color
        current_state.background_color = new_state.background_color
        current_state.bold = new_state.bold
        current_state.italic = new_state.italic
        current_state.underline = new_state.underline
        current_state.strikethrough = new_state.strikethrough
        current_state.active_formats = new_state.active_formats.copy()
        
        return ansi_codes
        
    except Exception as e:
        warnings.warn(f"Command processing failed: {e}")
        return ""


# Test script for reconstructor
if __name__ == "__main__":
    def test_reconstructor():
        """Test suite for the reconstructor."""
        
        print("=" * 60)
        print("FDL RECONSTRUCTOR TEST SUITE")
        print("=" * 60)
        
        test_count = 0
        passed_count = 0
        
        def run_test(name: str, format_string: str, values: Optional[Tuple] = None, 
                    expected_contains: Optional[List[str]] = None):
            """Run a single test case."""
            nonlocal test_count, passed_count
            test_count += 1
            
            print(f"\nTest {test_count}: {name}")
            print(f"Input: '{format_string}'")
            if values:
                print(f"Values: {values}")
            
            try:
                result = _reconstruct_fdl_string(format_string, values)
                print(f"Output: '{result}'")
                
                passed = True
                if expected_contains:
                    for expected in expected_contains:
                        if expected not in result:
                            print(f"❌ Missing expected content: '{expected}'")
                            passed = False
                
                if passed:
                    print("✅ PASSED")
                    passed_count += 1
                else:
                    print("❌ FAILED")
                    
            except Exception as e:
                print(f"❌ EXCEPTION: {e}")
                import traceback
                traceback.print_exc()
                
            print("-" * 40)
        
        # Test 1: Simple text only
        run_test("Simple text only", "Hello world", expected_contains=["Hello world"])
        
        # Test 2: Variable substitution
        run_test("Variable substitution", "Hello <name>!", ("Alice",), expected_contains=["Hello Alice!"])
        
        # Test 3: Simple formatting
        run_test("Simple formatting", "This is </bold>bold text", expected_contains=["This is", "bold text"])
        
        # Test 4: Time object
        run_test("Time object", "Current time: <time:>", expected_contains=["Current time:"])
        
        # Test 5: Mixed content
        run_test("Mixed content", "Time: </12hr, time:>", expected_contains=["Time:", "M"])  # Will match AM or PM
        
        # Test 6: Variable mismatch (should return error)
        run_test("Variable mismatch", "Hello <name> and <other>!", ("Alice",), expected_contains=["ERROR"])
        
        # Test 7: Format bleed prevention (should auto-reset at end)
        result1 = _reconstruct_fdl_string("This is </bold>bold text")
        result2 = _reconstruct_fdl_string("This should be normal")
        
        print(f"\nFormat bleed test:")
        print(f"Bold string:   '{result1}'") 
        print(f"Normal string: '{result2}'")
        
        # Check if first result ends with reset code (\033[0m)
        ends_with_reset = result1.endswith('\033[0m')
        print(f"First string ends with reset: {ends_with_reset}")
        
        if ends_with_reset:
            print("✅ Format bleed prevention working")
            passed_count += 1
        else:
            print("❌ Missing auto-reset - formatting will bleed!")
        test_count += 1
        
        # Test 8: Multiple formatting commands
        run_test("Multiple formatting", "Text </bold, italic, red>formatted</end bold, italic, red> normal", 
                expected_contains=["Text", "formatted", "normal"])
        
        # Test 9: Color commands
        run_test("Color commands", "Red </red>text</end red> and </bkg blue>blue background</end bkg blue>",
                expected_contains=["Red", "text", "blue background"])
        
        # Test 10: Complex variable substitution
        run_test("Complex variables", "User <username> has <count> items at <time>",
                ("Alice", 42, "14:30"), expected_contains=["Alice", "42", "14:30"])
        
        # Test 11: Date objects
        run_test("Date objects", "Today: <date:> and long: <datelong:>",
                expected_contains=["Today:", "long:"])
        
        # Test 12: Elapsed objects with timestamps
        import time
        past_time = time.time() - 3665  # About 1 hour, 1 minute, 5 seconds ago
        run_test("Elapsed objects", "Login was <elapsed:login_time> ago", (past_time,),
                expected_contains=["Login was", "h", "m", "ago"])
        
        # Test 13: Timezone and 12hr formatting
        timestamp = 1640995200.0  # Known timestamp for testing
        run_test("Timezone formatting", "Time: </12hr, tz pst, time:ts>", (timestamp,),
                expected_contains=["Time:", "PM"])
        
        # Test 14: Object with time suffixes (ONLY for elapsed objects)
        run_test("Time suffixes with elapsed", "Event </time ago, elapsed:event_time>", (past_time,),
                expected_contains=["Event", "ago"])
        
        # Test 15: No seconds command
        run_test("No seconds", "Brief time: </no sec, 12hr, time:ts>", (timestamp,),
                expected_contains=["Brief time:"])
        
        # Test 16: Reset commands
        run_test("Reset commands", "Before </bold>bold </reset>after reset",
                expected_contains=["Before", "bold", "after reset"])
        
        # Test 17: End commands
        run_test("End commands", "Start </bold, red>formatted</end bold> partial </end red>normal",
                expected_contains=["Start", "formatted", "partial", "normal"])
        
        # Test 18: Mixed complex content (should warn about invalid time ago with time object)
        run_test("Mixed complex - invalid combo", "Status: </12hr, no sec, tz est, time ago, time:login_time>", (past_time,),
                expected_contains=["Status:"])  # Should ignore time ago and just show time
        
        # Test 19: Correct usage of time ago/until with elapsed
        run_test("Elapsed with time ago", "Login </time ago, elapsed:login_time>", (past_time,),
                expected_contains=["Login", "ago"])
        
        # Test 20: Future timestamp with time until
        future_time = time.time() + 3600  # 1 hour from now
        run_test("Elapsed with time until", "Meeting </time until, elapsed:meeting_time>", (future_time,),
                expected_contains=["Meeting", "until"])
        
        # Test 21: Multiple objects and variables  
        login_time = time.time() - 7200  # 2 hours ago
        session_start = time.time() - 3600  # 1 hour ago
        run_test("Multiple objects", "User <user> logged in <elapsed:login> ago, session started <elapsed:session> ago",
                ("TestUser", login_time, session_start), expected_contains=["User", "TestUser", "ago"])
        
        # Test 22: Error handling - invalid commands with objects
        run_test("Invalid commands with objects", "Time: </bold, red, 12hr, time:>",
                expected_contains=["Time:"])  # Should work despite invalid commands
        
        # Test 23: NEW SMART FORMATTING COMMANDS
        past_time_long = time.time() - (2 * 86400 + 3 * 3600 + 15 * 60 + 30)  # 2d 3h 15m 30s ago
        
        # Smart units 1 - only highest unit
        run_test("Smart units 1", "Duration: </smart units 1, elapsed:duration>", (past_time_long,),
                expected_contains=["Duration:", "d"])
        
        # Smart units 2 - two highest units  
        run_test("Smart units 2", "Duration: </smart units 2, elapsed:duration>", (past_time_long,),
                expected_contains=["Duration:", "d", "h"])
        
        # No hr - only days
        run_test("No hours", "Duration: </no hr, elapsed:duration>", (past_time_long,),
                expected_contains=["Duration:", "d"])
        
        # No min - days and hours only
        run_test("No minutes", "Duration: </no min, elapsed:duration>", (past_time_long,),
                expected_contains=["Duration:", "d", "h"])
        
        # Round sec - no decimals
        short_time = time.time() - 65.789  # 1m 5.789s ago
        run_test("Round seconds", "Duration: </round sec, elapsed:duration>", (short_time,),
                expected_contains=["Duration:", "m", "s"])
        
        # Combined smart commands
        run_test("Combined smart", "Brief: </smart units 1, time ago, elapsed:duration>", (short_time,),
                expected_contains=["Brief:", "ago"])
        
        # Test 30: THE ULTIMATE TEST - Everything together (except Format class)
        current_time = time.time()
        login_timestamp = current_time - 8274  # 2h 17m 54s ago
        run_test(
            "Ultimate comprehensive test",
            "Server Status Report:\n"
            "</bold>User:</end bold> <username> (ID: <user_id>)\n"
            "</bold>Login:</end bold> </12hr, tz est, time:login_time> (</time ago, elapsed:login_time2>)\n"  
            "</bold>Current:</end bold> </12hr, tz est, time:> \n"
            "</bold>Session:</end bold> Active for <elapsed:login_time3>\n"
            "</red>Alert:</end red> </bold>System maintenance</end bold> in </italic>30 minutes</end italic>\n"
            "</bkg green, black>Status: ONLINE</end bkg green, black> | </reset>All systems normal",
            ("alice_cooper", 12345, login_timestamp, login_timestamp, login_timestamp),  # Provide 5 values
            expected_contains=[
                "Server Status Report:",
                "User:", "alice_cooper", "12345",
                "Login:", "PM", "ago", 
                "Current:", 
                "Session:", "Active for",
                "Alert:", "System maintenance", "30 minutes",
                "Status: ONLINE", "All systems normal"
            ]
        )
        
        print(f"\nTEST RESULTS: {passed_count}/{test_count} tests passed")
        return passed_count == test_count
    
    # Run the tests
    test_reconstructor()