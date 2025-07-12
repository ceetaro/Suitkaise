"""
Core parsing engine for fdl's <command> and <objtype:obj> syntax.

This module handles the primary parsing of fdl format strings, extracting:
- Text segments with their positions
- Format commands with their positions  
- Variable references with their positions
- Object patterns with their positions

All elements are tracked with positional indices to maintain proper ordering
during reconstruction and formatting.
"""

import re
import warnings
from typing import List, Tuple, Dict, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class _ParsedElement:
    """
    Represents a single parsed element from an fdl format string.
    
    Attributes:
        content (str): The actual content/command/variable name
        position (int): Position index in the logical sequence
        element_type (str): Type of element ('text', 'command', 'variable', 'object')
        raw_match (str): Original matched string from input
        start_index (int): Character position where this element starts in input
        end_index (int): Character position where this element ends in input
    """
    content: str 
    position: int
    element_type: str
    raw_match: str
    start_index: int
    end_index: int


@dataclass 
class _ParseResult:
    """
    Result of parsing an fdl format string.
    
    Attributes:
        elements (List[_ParsedElement]): All parsed elements in position order
        text_segments (List[_ParsedElement]): Just the text segments
        commands (List[_ParsedElement]): Just the format commands
        variables (List[_ParsedElement]): Just the variable references
        objects (List[_ParsedElement]): Just the object patterns
        has_errors (bool): True if parsing encountered any warnings/errors
        error_messages (List[str]): List of error/warning messages
    """
    elements: List[_ParsedElement]
    text_segments: List[_ParsedElement] 
    commands: List[_ParsedElement]
    variables: List[_ParsedElement]
    objects: List[_ParsedElement]
    has_errors: bool
    error_messages: List[str]


class _fdlParser:
    """
    Parser for fdl format strings with angle bracket syntax.
    
    Handles:
    - Commands: </bold>, </red, bkg blue>, </end bold>
    - Variables: <username>, <value1> 
    - Objects: <time:timestamp>, <elapsed:duration>
    - Text segments: Everything between the above
    
    Maintains positional ordering for proper reconstruction.
    """

    def __init__(self):
        """Initialize the parser with regex patterns."""
        # Regex patterns for different element types
        
        # Command pattern: </command> or </command, args>
        # Matches: </bold>, </red, bkg blue>, </end bold, italic>
        self._command_pattern = re.compile(r'</([^>]+)>')
        
        # Object pattern: <type:variable>
        # Matches: <time:timestamp>, <elapsed:duration>, <table:mytable>
        self._object_pattern = re.compile(r'<([a-zA-Z_][a-zA-Z0-9_]*):([^>]+)>')
        
        # Variable pattern: <variable> (not matching commands or objects)
        # Matches: <username>, <value1> but NOT </bold> or <time:stamp>
        self._variable_pattern = re.compile(r'<([a-zA-Z_][a-zA-Z0-9_]*)>')
        
        # Combined pattern to find all angle bracket elements in order
        self._all_pattern = re.compile(r'<[^>]+>')


    def parse(self, format_string: str, values: Optional[Tuple] = None) -> _ParseResult:
        """
        Parse an fdl format string into structured elements.
        
        Args:
            format_string (str): The format string to parse
            values (Optional[Tuple]): Values for variable substitution
            
        Returns:
            ParseResult: Structured parsing results with positional tracking
            
        Example:
            parser = fdlParser()
            result = parser.parse("User </bold><name></end bold> at <time:login>", ("Alice", timestamp))
            
            # result.elements contains all elements in position order:
            # [("User ", 0), ("bold", 1), ("name", 2), ("end bold", 3), (" at ", 4), ("time:login", 5)]
        """
        elements = []
        text_segments = []
        commands = []
        variables = []
        objects = []
        error_messages = []
        has_errors = False
        
        # Find all angle bracket matches with their positions
        bracket_matches = list(self._all_pattern.finditer(format_string))
        
        # Track logical position counter
        position_counter = 0
        last_end = 0
        
        for match in bracket_matches:
            start_idx = match.start()
            end_idx = match.end()
            raw_content = match.group(0)  # Full match including < >
            inner_content = match.group(0)[1:-1]  # Content without < >
            
            # Add text segment before this match (if any)
            if start_idx > last_end:
                text_content = format_string[last_end:start_idx]
                text_element = _ParsedElement(
                    content=text_content,
                    position=position_counter,
                    element_type='text',
                    raw_match=text_content,
                    start_index=last_end,
                    end_index=start_idx
                )
                elements.append(text_element)
                text_segments.append(text_element)
                position_counter += 1
            
            # Determine what type of element this is and parse it
            parsed_elements = self._parse_bracket_content(
                raw_content, inner_content, position_counter, start_idx, end_idx
            )

            if parsed_elements:
                # Add all parsed elements (handles multiple commands from one bracket)
                for element in parsed_elements:
                    elements.append(element)
                    
                    # Check for parse errors from mixed content
                    if hasattr(element, '_has_parse_errors') and element._has_parse_errors:
                        has_errors = True
                        if hasattr(element, '_parse_error_messages'):
                            error_messages.extend(element._parse_error_messages)
                    
                    # Add to appropriate category list
                    if element.element_type == 'command':
                        commands.append(element)
                    elif element.element_type == 'variable':
                        variables.append(element)
                    elif element.element_type == 'object':
                        objects.append(element)
                        
                position_counter += 1
            else:
                # Failed to parse - treat as text and warn
                error_msg = f"Warning: Could not parse '{raw_content}', treating as literal text"
                error_messages.append(error_msg)
                warnings.warn(error_msg, UserWarning)
                has_errors = True
                
                # Add as text element
                text_element = _ParsedElement(
                    content=raw_content,
                    position=position_counter,
                    element_type='text',
                    raw_match=raw_content,
                    start_index=start_idx,
                    end_index=end_idx
                )
                elements.append(text_element)
                text_segments.append(text_element)
                position_counter += 1
            
            last_end = end_idx

        # Add any remaining text after the last match
        if last_end < len(format_string):
            text_content = format_string[last_end:]
            text_element = _ParsedElement(
                content=text_content,
                position=position_counter,
                element_type='text',
                raw_match=text_content,
                start_index=last_end,
                end_index=len(format_string)
            )
            elements.append(text_element)
            text_segments.append(text_element)
    
        # FIXED: Count both variables AND object variables for validation
        if values is not None:
            # Count regular variables
            expected_vars = len(variables)
            
            # Count object variables that need values (non-empty variable part)
            object_vars = 0
            for obj in objects:
                obj_content = obj.content
                if ':' in obj_content:
                    obj_type, obj_var = obj_content.split(':', 1)
                    obj_var = obj_var.strip()
                    if obj_var:  # Only count if variable part is not empty
                        object_vars += 1
            
            total_expected = expected_vars + object_vars
            provided_values = len(values)
            
            if total_expected != provided_values:
                error_msg = f"Variable count mismatch: found {expected_vars} variables + {object_vars} object variables = {total_expected} total, but got {provided_values} values"
                error_messages.append(error_msg)
                warnings.warn(error_msg, UserWarning)
                has_errors = True
        
        return _ParseResult(
            elements=elements,
            text_segments=text_segments,
            commands=commands,
            variables=variables,
            objects=objects,
            has_errors=has_errors,
            error_messages=error_messages
        )

    def _parse_bracket_content(self, raw_content: str, inner_content: str, 
                             position: int, start_idx: int, end_idx: int) -> List[_ParsedElement]:
        """
        Parse the content inside angle brackets to determine element type.
        
        Args:
            raw_content (str): Full content including < >
            inner_content (str): Content without < >
            position (int): Logical position in sequence
            start_idx (int): Start character index in original string
            end_idx (int): End character index in original string
            
        Returns:
            List[ParsedElement]: List of parsed elements (multiple for comma-separated commands)
        """
        # Check for mixed content: commands + objects in same brackets
        # Example: </12hr, tz pst, time:timestamp>
        if inner_content.startswith('/') and ':' in inner_content:
            return self._parse_mixed_content(raw_content, inner_content[1:], position, start_idx, end_idx)
        
        # Check if it's a command (starts with /)
        elif inner_content.startswith('/'):
            return self._parse_command(raw_content, inner_content[1:], position, start_idx, end_idx)
        
        # Check if it's an object pattern (contains :)
        elif ':' in inner_content:
            element = self._parse_object(raw_content, inner_content, position, start_idx, end_idx)
            return [element] if element else []
        
        # Check if it's a valid variable name
        elif self._is_valid_variable_name(inner_content):
            return [_ParsedElement(
                content=inner_content,
                position=position,
                element_type='variable',
                raw_match=raw_content,
                start_index=start_idx,
                end_index=end_idx
            )]
        
        # Could not determine type
        return []

    def _parse_mixed_content(self, raw_content: str, command_content: str, 
                           position: int, start_idx: int, end_idx: int) -> List[_ParsedElement]:
        """
        Parse mixed content with commands and objects in same brackets.
        
        Example: </12hr, tz pst, time:timestamp>
        
        Args:
            raw_content (str): Full content including < >
            command_content (str): Content without < / >
            position (int): Logical position in sequence
            start_idx (int): Start character index
            end_idx (int): End character index
            
        Returns:
            List[_ParsedElement]: List of commands and object at same position
        """
        elements = []
        error_messages = []
        has_errors = False
        
        # Split on commas to find commands and object
        parts = [part.strip() for part in command_content.split(',')]
        
        object_parts = []
        command_parts = []
        
        # Separate commands from object patterns
        for part in parts:
            if ':' in part and not part.startswith('tz '):  # Object pattern (but not timezone)
                object_parts.append(part)
            else:
                command_parts.append(part)
        
        # Validate: should have exactly one object
        if len(object_parts) != 1:
            if len(object_parts) == 0:
                error_msg = f"Mixed content without object pattern: {raw_content}"
                error_messages.append(error_msg)
                warnings.warn(error_msg, UserWarning)
                has_errors = True
            else:
                error_msg = f"Multiple object patterns in same brackets: {raw_content}"
                error_messages.append(error_msg)
                warnings.warn(error_msg, UserWarning)
                has_errors = True
            return []
        
        object_pattern = object_parts[0]
        
        # Validate object pattern
        if not self._is_valid_object_pattern(object_pattern):
            error_msg = f"Invalid object pattern: {object_pattern}"
            error_messages.append(error_msg)
            warnings.warn(error_msg, UserWarning)
            has_errors = True
            return []
        
        # Validate commands are object-specific
        valid_commands = []
        for cmd in command_parts:
            if self._is_object_specific_command(cmd):
                valid_commands.append(cmd)
            else:
                error_msg = f"Non-object command '{cmd}' ignored in object context: {raw_content}"
                error_messages.append(error_msg)
                warnings.warn(error_msg, UserWarning)
                has_errors = True
        
        # Store errors in the element for later propagation
        # We'll handle this by returning a special marker or propagating differently
        
        # Create command elements at same position
        for cmd in valid_commands:
            elements.append(_ParsedElement(
                content=cmd,
                position=position,
                element_type='command',
                raw_match=raw_content,
                start_index=start_idx,
                end_index=end_idx
            ))
        
        # Create object element at same position
        elements.append(_ParsedElement(
            content=object_pattern,
            position=position,
            element_type='object',
            raw_match=raw_content,
            start_index=start_idx,
            end_index=end_idx
        ))
        
        # We need to propagate the error state back to the main parse method
        # Let's add error info to elements or handle this differently
        if has_errors:
            # Add a special marker to indicate this parsing had errors
            for elem in elements:
                elem._has_parse_errors = True
                elem._parse_error_messages = error_messages
        
        return elements
    
    def _is_valid_object_pattern(self, pattern: str) -> bool:
        """Check if a string is a valid object pattern."""
        if ':' not in pattern:
            return False
        
        parts = pattern.split(':', 1)
        if len(parts) != 2:
            return False
        
        obj_type, obj_var = parts
        obj_type = obj_type.strip()
        obj_var = obj_var.strip()
        
        # Valid object types
        valid_types = ['time', 'date', 'datelong', 'elapsed', 'elapsed2', 'timeprefix']
        if obj_type not in valid_types:
            return False
        
        # Object variable can be empty (for current time) or valid identifier
        if obj_var and not self._is_valid_variable_name(obj_var):
            return False
        
        return True
    
    def _is_object_specific_command(self, command: str) -> bool:
        """Check if a command is object-specific (not formatting)."""
        command = command.strip()
        
        # Object-specific commands
        object_commands = [
            '12hr',           # 12-hour format
            'time ago',       # Add "ago" suffix
            'time until',     # Add "until" suffix  
            'no sec',         # Remove seconds
        ]
        
        # Check exact matches
        if command in object_commands:
            return True
        
        # Check timezone commands: "tz pst", "tz utc", etc.
        if command.startswith('tz ') and len(command) > 3:
            return True
        
        return False
    
    def _parse_command(self, raw_content: str, command_content: str, 
                      position: int, start_idx: int, end_idx: int) -> List[_ParsedElement]:
        """
        Parse a command element (starts with /).

        Commands starting with /end populate end to every command in the comma'd list.
        </end bold, italic> means end bold AND italic commands.
        
        Handles multiple commands separated by commas:
        - </bold> -> [("bold", position, "command")]
        - </bold, italic> -> [("bold", position, "command"), ("italic", position, "command")]
        - </fmt greentext_bluebkg> -> [("fmt greentext_bluebkg", position, "command")]
        - </bkg blue> -> [("bkg blue", position, "command")]
        - </end bold, italic> -> [("end bold", position, "command"), ("end italic", position, "command")]
        
        Args:
            raw_content (str): Full content including < >
            command_content (str): Command content without / prefix
            position (int): Logical position in sequence
            start_idx (int): Start character index
            end_idx (int): End character index
            
        Returns:
            List[_ParsedElement]: List of parsed command elements (multiple if comma-separated)
        """
        # Clean up the command content (strip whitespace)
        command_content = command_content.strip()
        
        if not command_content:
            return []
        
        # Check if this is an "end" command
        is_end_command = command_content.startswith('end ')
        
        if is_end_command:
            # Remove "end " prefix and split the remaining commands
            remaining_content = command_content[4:]  # Remove "end "
            command_parts = [cmd.strip() for cmd in remaining_content.split(',')]
            
            # Create "end X" for each command
            elements = []
            for cmd in command_parts:
                if cmd:  # Skip empty commands
                    elements.append(_ParsedElement(
                        content=f"end {cmd}",
                        position=position,
                        element_type='command',
                        raw_match=raw_content,
                        start_index=start_idx,
                        end_index=end_idx
                    ))
        else:
            # Split on commas to handle multiple commands like </bold, italic>
            command_parts = [cmd.strip() for cmd in command_content.split(',')]
            
            # Create a ParsedElement for each command
            elements = []
            for cmd in command_parts:
                if cmd:  # Skip empty commands
                    elements.append(_ParsedElement(
                        content=cmd,
                        position=position,
                        element_type='command',
                        raw_match=raw_content,
                        start_index=start_idx,
                        end_index=end_idx
                    ))
        
        return elements

    def _parse_object(self, raw_content: str, object_content: str,
                     position: int, start_idx: int, end_idx: int) -> Optional[_ParsedElement]:
        """
        Parse an object pattern (contains :).
        
        Args:
            raw_content (str): Full content including < >
            object_content (str): Object content
            position (int): Logical position in sequence
            start_idx (int): Start character index  
            end_idx (int): End character index
            
        Returns:
            Optional[_ParsedElement]: Parsed object element
        """
        # Split on first colon only
        parts = object_content.split(':', 1)
        if len(parts) != 2:
            return None
            
        obj_type, obj_var = parts
        obj_type = obj_type.strip()
        obj_var = obj_var.strip()
        
        # Validate object type (must be valid identifier)
        # Variable part can be empty (for patterns like <time:>)
        if not self._is_valid_variable_name(obj_type):
            return None
            
        return _ParsedElement(
            content=object_content,
            position=position,
            element_type='object',
            raw_match=raw_content,
            start_index=start_idx,
            end_index=end_idx
        )
    
    def _is_valid_variable_name(self, name: str) -> bool:
        """
        Check if a string is a valid variable name.
        
        Args:
            name (str): Name to validate
            
        Returns:
            bool: True if valid variable name
        """
        if not name:
            return False
        
        # Must start with letter or underscore, followed by letters, digits, or underscores
        return re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name) is not None
    
    def get_commands_at_position(self, parse_result: _ParseResult, position: int) -> List[_ParsedElement]:
        """
        Get all commands that occur at a specific position.
        
        This handles cases like </bold, italic> where multiple commands
        share the same position.
        
        Args:
            parse_result (_ParseResult): Result from parse()
            position (int): Position to check
            
        Returns:
            List[_ParsedElement]: All commands at that position
        """
        return [cmd for cmd in parse_result.commands if cmd.position == position]
    
    def get_elements_at_position(self, parse_result: _ParseResult, position: int) -> List[_ParsedElement]:
        """
        Get all elements (commands, objects, etc.) that occur at a specific position.
        
        This handles mixed content like </12hr, tz pst, time:timestamp> where
        commands and objects share the same position.
        
        Args:
            parse_result (_ParseResult): Result from parse()
            position (int): Position to check
            
        Returns:
            List[_ParsedElement]: All elements at that position
        """
        return [elem for elem in parse_result.elements if elem.position == position]
    
def _parse_fdl_string(format_string: str, values: Optional[Tuple] = None) -> _ParseResult:
    """
    Convenience function to parse an fdl format string.
    
    Args:
        format_string (str): The format string to parse
        values (Optional[Tuple]): Values for variable substitution
        
    Returns:
        _ParseResult: Structured parsing results
    """
    parser = _fdlParser()
    return parser.parse(format_string, values)

# Test script for FDL Parser - add this to the bottom of your parser.py file

# Test script - run this to verify parser functionality
if __name__ == "__main__":
    def test_parser():
        """Comprehensive test suite for the FDL parser."""
        
        print("=" * 60)
        print("FDL PARSER TEST SUITE")
        print("=" * 60)
        
        parser = _fdlParser()
        test_count = 0
        passed_count = 0
        
        def run_test(name: str, format_string: str, values: Optional[Tuple] = None, 
                    expected_elements: Optional[List] = None, should_have_errors: bool = False):
            """Run a single test case."""
            nonlocal test_count, passed_count
            test_count += 1
            
            print(f"\nTest {test_count}: {name}")
            print(f"Input: '{format_string}'")
            if values:
                print(f"Values: {values}")
            
            try:
                result = parser.parse(format_string, values)
                
                print(f"Parsed {len(result.elements)} elements:")
                for i, elem in enumerate(result.elements):
                    print(f"  {i}: ({elem.content!r}, {elem.position}, {elem.element_type!r})")
                
                print(f"Commands: {[(cmd.content, cmd.position) for cmd in result.commands]}")
                print(f"Variables: {[(var.content, var.position) for var in result.variables]}")  
                print(f"Objects: {[(obj.content, obj.position) for obj in result.objects]}")
                print(f"Has errors: {result.has_errors}")
                
                if result.error_messages:
                    print(f"Errors: {result.error_messages}")
                
                # Basic validation
                passed = True
                if should_have_errors and not result.has_errors:
                    print("❌ EXPECTED ERRORS BUT GOT NONE")
                    passed = False
                elif not should_have_errors and result.has_errors:
                    print("❌ UNEXPECTED ERRORS")
                    passed = False
                
                if expected_elements:
                    actual = [(e.content, e.position, e.element_type) for e in result.elements]
                    if actual != expected_elements:
                        print(f"❌ EXPECTED: {expected_elements}")
                        print(f"❌ ACTUAL:   {actual}")
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
        run_test(
            "Simple text only",
            "Hello world",
            expected_elements=[("Hello world", 0, "text")]
        )
        
        # Test 2: Single command
        run_test(
            "Single command",
            "This is </bold>bold text",
            expected_elements=[
                ("This is ", 0, "text"),
                ("bold", 1, "command"),
                ("bold text", 2, "text")
            ]
        )
        
        # Test 3: Command with end
        run_test(
            "Command with end",
            "This is </bold>bold</end bold> text",
            expected_elements=[
                ("This is ", 0, "text"),
                ("bold", 1, "command"), 
                ("bold", 2, "text"),
                ("end bold", 3, "command"),
                (" text", 4, "text")
            ]
        )
        
        # Test 4: Multiple commands at same position
        run_test(
            "Multiple commands at same position",
            "Text </bold, italic>styled</end bold, italic> text",
            expected_elements=[
                ("Text ", 0, "text"),
                ("bold", 1, "command"),
                ("italic", 1, "command"),
                ("styled", 2, "text"),
                ("end bold", 3, "command"),
                ("end italic", 3, "command"),
                (" text", 4, "text")
            ]
        )
        
        # Test 5: Multi-word commands
        run_test(
            "Multi-word commands",
            "Text </fmt greentext_bluebkg>formatted text",
            expected_elements=[
                ("Text ", 0, "text"),
                ("fmt greentext_bluebkg", 1, "command"),
                ("formatted text", 2, "text")
            ]
        )
        
        # Test 6: Background color commands
        run_test(
            "Background color commands",
            "Text </red, bkg blue>colored text",
            expected_elements=[
                ("Text ", 0, "text"),
                ("red", 1, "command"),
                ("bkg blue", 1, "command"),
                ("colored text", 2, "text")
            ]
        )
        
        # Test 7: Single variable
        run_test(
            "Single variable",
            "Hello <n>!",
            ("Alice",),
            expected_elements=[
                ("Hello ", 0, "text"),
                ("n", 1, "variable"),
                ("!", 2, "text")
            ]
        )
        
        # Test 8: Multiple variables
        run_test(
            "Multiple variables", 
            "User <username> has <count> items",
            ("Alice", 42),
            expected_elements=[
                ("User ", 0, "text"),
                ("username", 1, "variable"),
                (" has ", 2, "text"),
                ("count", 3, "variable"),
                (" items", 4, "text")
            ]
        )
        
        # Test 9: Time objects
        run_test(
            "Time objects",
            "Current time: <time:> and login was at <time:login_time>",
            (1234567890,),
            expected_elements=[
                ("Current time: ", 0, "text"),
                ("time:", 1, "object"),
                (" and login was at ", 2, "text"),
                ("time:login_time", 3, "object")
            ]
        )
        
        # Test 10: Mixed everything
        run_test(
            "Mixed commands, variables, and objects",
            "User </bold><username></end bold> logged in at <time:login_time>",
            ("Alice", 1234567890),
            expected_elements=[
                ("User ", 0, "text"),
                ("bold", 1, "command"),
                ("username", 2, "variable"),
                ("end bold", 3, "command"),
                (" logged in at ", 4, "text"),
                ("time:login_time", 5, "object")
            ]
        )
        
        # Test 11: Complex nested formatting
        run_test(
            "Complex nested formatting",
            "Status: </box rounded, title Important, green><status>",
            ("online",),
            expected_elements=[
                ("Status: ", 0, "text"),
                ("box rounded", 1, "command"),
                ("title Important", 1, "command"),
                ("green", 1, "command"),
                ("status", 2, "variable")
            ]
        )
        
        # Test 12: Edge case - empty commands
        run_test(
            "Edge case - empty commands",
            "Text </>more text",
            should_have_errors=True
        )
        
        # Test 13: Edge case - invalid variable names
        run_test(
            "Edge case - invalid variable names",
            "Text <123invalid> and <-invalid> text",
            should_have_errors=True
        )
        
        # Test 14: Edge case - variable count mismatch
        run_test(
            "Edge case - variable count mismatch",
            "User <username> has <count> items",
            ("Alice",),  # Missing second value
            should_have_errors=True
        )
        
        # Test 15: Edge case - malformed objects
        run_test(
            "Edge case - malformed objects",
            "Time <time> and <:invalid> and <invalid:>",
            should_have_errors=True
        )
        
        # Test 16: Edge case - no angle brackets
        run_test(
            "Edge case - no angle brackets",
            "Just plain text with no formatting",
            expected_elements=[("Just plain text with no formatting", 0, "text")]
        )
        
        # Test 17: Whitespace handling in commands
        run_test(
            "Whitespace handling in commands",
            "Text </ bold , italic >formatted</ end bold , italic > text",
            expected_elements=[
                ("Text ", 0, "text"),
                ("bold", 1, "command"),
                ("italic", 1, "command"),
                ("formatted", 2, "text"),
                ("end bold", 3, "command"),
                ("end italic", 3, "command"),
                (" text", 4, "text")
            ]
        )
        
        # Test 18: Variable named like a command
        run_test(
            "Variable named like a command",
            "Value <bold> should be a variable, not a command",
            (True,),
            expected_elements=[
                ("Value ", 0, "text"),
                ("bold", 1, "variable"),
                (" should be a variable, not a command", 2, "text")
            ]
        )
        
        # Test 19: Real-world example
        run_test(
            "Real-world logging example",
            "Process <pid> (<time:start_time>): </green>Successfully</end green> loaded <module_count> modules",
            (1234, 1234567890, 15),
            expected_elements=[
                ("Process ", 0, "text"),
                ("pid", 1, "variable"),
                (" (", 2, "text"),
                ("time:start_time", 3, "object"),
                ("): ", 4, "text"),
                ("green", 5, "command"),
                ("Successfully", 6, "text"),
                ("end green", 7, "command"),
                (" loaded ", 8, "text"),
                ("module_count", 9, "variable"),
                (" modules", 10, "text")
            ]
        )
        
        # Test 20: Your exact examples from specification
        run_test(
            "Your example 1",
            "User </bold><n></end bold> logged in at <time:login_time>",
            ("Alice", 1234567890),
            expected_elements=[
                ("User ", 0, "text"),
                ("bold", 1, "command"),
                ("n", 2, "variable"),
                ("end bold", 3, "command"),
                (" logged in at ", 4, "text"),
                ("time:login_time", 5, "object")
            ]
        )
        
        # Test 21: Your example 2
        run_test(
            "Your example 2",
            "User </bold, italic><n></end bold, italic> logged in at <time:login_time>",
            ("Alice", 1234567890),
            expected_elements=[
                ("User ", 0, "text"),
                ("bold", 1, "command"),
                ("italic", 1, "command"),
                ("n", 2, "variable"),
                ("end bold", 3, "command"),
                ("end italic", 3, "command"),
                (" logged in at ", 4, "text"),
                ("time:login_time", 5, "object")
            ]
        )
        
        # Test 22: Mixed content - object with commands
        run_test(
            "Mixed content - object with commands",
            "Current time: </12hr, tz pst, time:>",
            expected_elements=[
                ("Current time: ", 0, "text"),
                ("12hr", 1, "command"),
                ("tz pst", 1, "command"),
                ("time:", 1, "object")
            ]
        )
        
        # Test 23: Mixed content with variable
        run_test(
            "Mixed content with variable",
            "Login at </time ago, time:login_time>",
            (1234567890,),
            expected_elements=[
                ("Login at ", 0, "text"),
                ("time ago", 1, "command"),
                ("time:login_time", 1, "object")
            ]
        )
        
        # Test 24: Invalid mixed content - formatting command with object
        run_test(
            "Invalid mixed content - formatting command with object",
            "Time: </bold, time:>",
            should_have_errors=True  # Should warn about bold being invalid with time object
        )
        
        # Test 25: Complex time formatting
        run_test(
            "Complex time formatting",
            "Meeting </12hr, no sec, time until, elapsed:duration> from now",
            (3600,),
            expected_elements=[
                ("Meeting ", 0, "text"),
                ("12hr", 1, "command"),
                ("no sec", 1, "command"),
                ("time until", 1, "command"),
                ("elapsed:duration", 1, "object"),
                (" from now", 2, "text")
            ]
        )
        
        # Test 26: Multiple object types
        import time
        run_test(
            "Multiple object types",
            "Current: <time:> | Elapsed: <elapsed:start> | Date: </tz utc, datelong:>",
            (time.time() - 3600,),
            expected_elements=[
                ("Current: ", 0, "text"),
                ("time:", 1, "object"),
                (" | Elapsed: ", 2, "text"),
                ("elapsed:start", 3, "object"),
                (" | Date: ", 4, "text"),
                ("tz utc", 5, "command"),
                ("datelong:", 5, "object")
            ]
        )
        
        print("\n" + "=" * 60)
        print(f"TEST RESULTS: {passed_count}/{test_count} tests passed")
        if passed_count == test_count:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"❌ {test_count - passed_count} tests failed")
        print("=" * 60)
        
        return passed_count == test_count
    
    # Run the tests
    test_parser()