"""
Internal Format State for FDL processing with Progress Bar support.

This module contains the private state object that tracks all formatting,
layout, and processing state throughout FDL string processing, including
progress bar output queuing.

This is internal to the FDL engine and not exposed to users.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Set, Dict, Any, Union
from enum import Enum
import re
import time

# Import terminal detection
from ..setup.terminal import _terminal
from ..setup.color_conversion import _ColorConverter
from ..setup.text_wrapping import _TextWrapper
from ..setup.text_justification import _TextJustifier
from ..setup.box_generator import _BoxGenerator
from ..elements.base_element import _BaseElement
from ..classes.progress_bar import _progress_bar_manager

# Module-level setup utilities
_color_converter = _ColorConverter()
_text_wrapper = _TextWrapper()
_text_justifier = _TextJustifier()
# Note: _BoxGenerator is instantiated per-box with specific settings

class ExtraVariableError(Exception):
    """
    Exception when a user adds more variables than expected based on <values>
    placed in the fdl string.
    """
    pass

class MissingVariableError(Exception):
    """
    Exception when a user adds less variables than expected based on <values>
    placed in the fdl string.
    """
    pass

class IncompleteOutputError(Exception):
    """
    Exception when the output is incomplete, meaning not all requested output
    streams have been processed correctly.
    """
    pass

class _OutputType(Enum):
    """
    Enum for output destinations supported by FDL.
    
    This is used to determine where the formatted output should be sent.
    """
    TERMINAL = 'terminal'
    PLAIN = 'plain'
    MARKDOWN = 'markdown'
    HTML = 'html'


class _Formatter:
    """
    Private central processor that orchestrates the entire formatting pipeline.
    
    This class is internal and should never be exposed to end users.
    """

    def __init__(self, fdl_string: str, 
                       values: Union[Tuple, Any],
                       custom_terminal_width: Optional[int] = None,
                       destinations: Set[_OutputType] = { _OutputType.TERMINAL }):
        """
        Initialize the formatting pipeline.

        Args:
            fdl_string (str): The given string in FDL syntax (using <>)
            values (Union[Tuple, Any]): Tuple of values for variable substitution
            custom_terminal_width (Optional[int]): Custom terminal width, if specified (for testing)
            destinations (Set[_OutputType]): Set of output types that we need to process.

        """
        self.fdl_string: str = fdl_string
        self.parsed_pieces: List[Dict[str, str]] = self._parse_fdl_string()

        self.output_types: Set[_OutputType] = destinations

        if not isinstance(values, tuple) and values is not None:
            values = (values,)

        for value in values:
            if not isinstance(value, (str, int, float, bool)):
                # for class objects, we will use their string, representation, or __name__
                if hasattr(value, '__str__'):
                    value = str(value)
                elif hasattr(value, '__repr__'):
                    value = repr(value)
                elif hasattr(value, '__name__'):
                    value = value.__name__
                else:
                    raise TypeError(f"Unsupported value type: {type(value)}")

        # Initialize values, terminal width, and max possible box width
        self.values: tuple = values if values is not None else ()
        self.value_index: int = 0

        if custom_terminal_width and custom_terminal_width > 0:
            self.terminal_width = custom_terminal_width
        else:
            self.terminal_width = max(60, _terminal.width if _terminal.width else 60)

        self.max_box_width: int = self._calculate_max_box_width()

        # True when all data is ready to output and no progress bar is active.
        self.ready_to_output: bool = False

        # ~ debug mode
        self.debug_mode: bool = False
        self.debug_printing = False  # True when fdl.dprint() or @autodebug is used
        
        # Regex for parsing FDL strings
        self._all_brackets_pattern = re.compile(r'<[^>]*>')
    
        # Text formatting
        self.text_color: Optional[str] = None
        self.current_text_color_command: Optional[str] = None  # Used to track current color command
        self.background_color: Optional[str] = None
        self.current_background_color_command: Optional[str] = None  # Used to track current background color command
        self.bold: bool = False
        self.italic: bool = False
        self.underline: bool = False
        self.strikethrough: bool = False
    
        # Time formatting settings
        self.twelve_hour_time: bool = False
        self.timezone: Optional[str] = None
        self.timestamp_decimal_places: int = 4
        self.use_seconds_in_timestamp: bool = False

        # for elapsed time formatting
        self.smart_time: int = 3 
        
        # Smart time formatting:
        # uses 3 most relevant units by default.
        # if < 1 second, uses 3 decimal places
        # if < 60 seconds, uses seconds and 2 decimal places
        # if < 60 minutes, uses minutes, seconds, and 1 decimal place
        # if < 24 hours, uses hours, minutes, and seconds
        # if > 24 hours, uses days, hours, and minutes
        # in debug mode, this is set to 10.

    
        # Box state
        self.in_box: bool = False
        self.box_style: str = "square"
        self.box_title: Optional[str] = None
        self.box_color: Optional[str] = None
        self.box_content: List[str] = field(default_factory=list)
        self.box_justify: str = 'center'
        self.actual_box_width: int = self.max_box_width
    
        # Layout settings
        self.justify: str = 'left'  # Default justification
    
        # Active format tracking
        # when a format is used for the first time, it is added here
        self.active_formats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
        # Output streams - all raw output goes here
        self.raw_terminal_output: List[str] = field(default_factory=list)
        self.raw_plain_output: List[str] = field(default_factory=list)
        self.raw_markdown_output: List[str] = field(default_factory=list)
        self.raw_html_output: List[str] = field(default_factory=list)
    
        # Output streams - all processed output goes here
        self.terminal_output: str = ""
        self.plain_output: str = ""
        self.markdown_output: str = ""
        self.html_output: str = ""

    def _parse_fdl_string(self) -> List[Dict[str, str]]:
        """
        Parse the FDL string into a list of content pieces.
        
        Returns:
            List[Dict[str, str]]: List of content pieces with type and content
        """
        pieces = []
        last_end = 0
        
        for match in self._all_brackets_pattern.finditer(self.fdl_string):
            start_idx = match.start()
            end_idx = match.end()
            bracket_content = match.group(0)
            
            # Add text before bracket
            if start_idx > last_end:
                text_content = self.fdl_string[last_end:start_idx]
                if text_content:
                    pieces.append({'type': 'text', 'content': text_content})
            
            # Parse bracket content
            piece = self._parse_bracket_content(bracket_content)
            if piece:
                pieces.append(piece)
            
            last_end = end_idx
        
        # Add remaining text
        if last_end < len(self.fdl_string):
            remaining = self.fdl_string[last_end:]
            if remaining:
                pieces.append({'type': 'text', 'content': remaining})
        
        return pieces
    
    def _parse_bracket_content(self, bracket_content: str) -> Optional[Dict[str, str]]:
        """Parse bracket content and determine its type."""
        inner = bracket_content[1:-1]  # Remove < >
        
        if not inner:
            return None
            
        # Command (starts with /)
        if inner.startswith('/'):
            return {'type': 'command', 'content': bracket_content}
        
        # Object (contains :)
        if ':' in inner:
            return {'type': 'object', 'content': bracket_content}
        
        # Variable (anything else valid)
        if inner.isidentifier():
            return {'type': 'variable', 'content': bracket_content}
        
        # Invalid - treat as literal text
        return {'type': 'text', 'content': bracket_content}
    
    def _process_piece(self, piece: Dict[str, str]):
        """Process a single piece according to its type."""
        piece_type = piece['type']
        content = piece['content']
        
        if piece_type == 'text':
            self._process_text(content)
        elif piece_type == 'variable':
            self._process_variable(content)
        elif piece_type == 'command':
            self._process_command(content)
        elif piece_type == 'object':
            self._process_object(content)
    
    def _process_text(self, text_content: str):
        """Process plain text by adding it to raw output."""
        if not text_content:
            return
            
        if self.debug_mode:
            # Type 3: Debug Text Processing - plain text only (no formatting)
            self._add_formatted_content_to_raw_output(text_content, use_current_formatting=False)
        else:
            # Type 2: Normal Text Processing - apply current formatting
            self._add_formatted_content_to_raw_output(text_content, use_current_formatting=True)
    
    def _process_variable(self, original: str):
        """Process a variable by substituting it with the next value."""
        # Extract variable name from <var_name>
        var_name = original[1:-1]  # Remove < >
        try:
            value = self.get_next_value()
            
            # Handle Case 2: Variables containing FDL syntax
            # Check if the value contains FDL commands or objects
            if self._is_fdl_syntax_string(str(value)):
                # Parse and process the command string from the variable
                self._process_fdl_command_from_variable(str(value))
                return
            
            if self.debug_mode:
                # Type 3: Debug Text Processing
                self._add_debug_formatted_variable(value)
            else:
                # Type 2: Normal Text Processing  
                self._add_formatted_content_to_raw_output(str(value), use_current_formatting=True)
                
        except ExtraVariableError:
            # No more values available - treat as literal text
            if self.debug_mode:
                # In debug mode, literal variables are plain text
                self._add_formatted_content_to_raw_output(original, use_current_formatting=False)
            else:
                # In normal mode, apply current formatting
                self._add_formatted_content_to_raw_output(original, use_current_formatting=True)
    
    def _process_command(self, original: str):
        """Process a command that modifies the formatter state."""
        # Extract command from </command>
        command = original[2:-1]  # Remove </ >
            
        if self.debug_mode:
            # Type 3: Debug Text Processing - render non-debug commands as literal text
            if not (command.strip().lower().startswith('debug') or 
                    command.strip().lower().startswith('end debug')):
                # Use the original command format and render as plain text
                self._add_formatted_content_to_raw_output(original, use_current_formatting=False)
                return
        
        # Check if we need to process raw output before this command
        if self._should_process_raw_output_before_command(command):
            self._process_raw_output()
        
        # Process the command - this only modifies formatter state
        self._execute_command_string(command, original)
    
    def _process_object(self, original: str):
        """Process an object that returns formatted text."""
        # Extract object content from <obj_content>
        obj_content = original[1:-1]  # Remove < >
            
        # Objects return plain text that gets formatted with current state
        obj_text = self._execute_object(obj_content)
        if obj_text:
            if self.debug_mode:
                # Type 3: Debug Text Processing - objects are plain text (no formatting)
                self._add_formatted_content_to_raw_output(obj_text, use_current_formatting=False)
            else:
                # Type 2: Normal Text Processing - apply current formatting
                self._add_formatted_content_to_raw_output(obj_text, use_current_formatting=True)
    
    def _generate_ansi_codes(self) -> str:
        """Generate ANSI codes based on current formatting state."""
        codes = []
        
        if self.bold:
            codes.append('1')
        if self.italic:
            codes.append('3')
        if self.underline:
            codes.append('4')
        if self.strikethrough:
            codes.append('9')
            
        if self.text_color:
            fg_code = _color_converter.to_ansi_fg(self.text_color)
            if fg_code:
                codes.append(fg_code.replace('\033[', '').replace('m', ''))
                
        if self.background_color:
            bg_code = _color_converter.to_ansi_bg(self.background_color)
            if bg_code:
                codes.append(bg_code.replace('\033[', '').replace('m', ''))
        
        if codes:
            return f"\033[{';'.join(codes)}m"
        return ""
    
    def _add_formatted_content_to_raw_output(self, content: str, use_current_formatting: bool = True):
        """Add content to raw output streams with appropriate formatting."""
        if not content:
            return
            
        if use_current_formatting:
            # Generate ANSI codes for current formatting state
            ansi_prefix = self._generate_ansi_codes()
            ansi_suffix = '\033[0m'  # Reset code
            formatted_content = f"{ansi_prefix}{content}{ansi_suffix}"
        else:
            formatted_content = content
        
        # Add to appropriate output streams
        if self.in_box:
            self.box_content.append(formatted_content)
        else:
            for output_type in self.output_types:
                if output_type == _OutputType.TERMINAL:
                    self.raw_terminal_output.append(formatted_content)
                elif output_type == _OutputType.PLAIN:
                    self.raw_plain_output.append(content)  # No ANSI for plain
                elif output_type == _OutputType.MARKDOWN:
                    self.raw_markdown_output.append(content)  # No ANSI for markdown
                elif output_type == _OutputType.HTML:
                    self.raw_html_output.append(content)  # Convert to HTML later
    
    def _add_debug_formatted_variable(self, value):
        """Add a variable with debug formatting based on its type."""
        # Get type and value string
        value_type = type(value).__name__
        
        # Generate debug formatting based on type
        if isinstance(value, int):
            # int: cyan, bold, italic + (int)
            debug_content = f"\033[36;1;3m{value}\033[0m \033[2m({value_type})\033[0m"
        elif isinstance(value, bool):
            # bool: green/red, bold, italic + (bool)
            color = '32' if value else '31'  # green for True, red for False
            debug_content = f"\033[{color};1;3m{value}\033[0m \033[2m({value_type})\033[0m"
        elif value is None:
            # None: blue, bold, italic + (None)
            debug_content = f"\033[34;1;3m{value}\033[0m \033[2m({value_type})\033[0m"
        elif isinstance(value, float):
            # float: cyan, bold, italic + (float)
            debug_content = f"\033[36;1;3m{value}\033[0m \033[2m({value_type})\033[0m"
        elif isinstance(value, str):
            # string: green quotes + content + green quotes + (str)
            # Strings are printed as-is without FDL processing
            debug_content = f'\033[32;1m"\033[0m{value}\033[32;1m"\033[0m \033[2m({value_type})\033[0m'
        else:
            # Other types: default formatting + type
            debug_content = f"\033[1;3m{value}\033[0m \033[2m({value_type})\033[0m"
        
        # Add to raw output streams (debug formatting already includes ANSI codes)
        self._add_formatted_content_to_raw_output(debug_content, use_current_formatting=False)
    
    def _should_process_raw_output_before_command(self, command: str) -> bool:
        """Check if raw output should be processed before this command."""
        # Process raw output before box commands and justify changes
        if command.startswith('box') or command.startswith('justify'):
            return True
        return False
    
    def _is_debug_command(self, command: str) -> bool:
        """Check if the command is a debug command."""
        return command in ['debug', 'end debug']
    
    def _is_text_formatting_command(self, command: str) -> bool:
        """Check if the command is a text formatting command."""
        text_formatting_commands = [
            'bold', 'italic', 'underline', 'strikethrough',
            'justify left', 'justify center', 'justify right',
            'left justify', 'center justify', 'right justify',
            'left', 'center', 'right'
        ]
        if command.startswith('fmt '):
            # Handle fmt commands as text formatting
            return True
        
        if _color_converter.is_valid_color(command):
            # If it's a color command, treat it as text formatting
            return True
        
        return command in text_formatting_commands
    
    def _is_time_command(self, command: str) -> bool:
        """Check if the command is a time formatting command."""
        time_commands = ['12hr', '24hr', 'seconds']
        return command in time_commands \
            or command.startswith('tz ') \
            or command.startswith('smart time ') \
            or command.startswith('decimals ')
    
    def _is_box_command(self, command: str) -> bool:
        """Check if the command is a box command."""
        # Box styles that can follow "box"
        box_styles = ['square', 'rounded', 'double', 'heavy', 'heavy_head', 'horizontals', 'ascii']
        
        # Check for "box style" patterns
        for style in box_styles:
            if command == f'box {style}':
                return True
        
        # Check for plain "box" command
        if command == 'box':
            return True
            
        return False
    
    def _execute_command_string(self, command_string: str, original: Optional[str] = None):
        """Execute a command that modifies formatter state (Type 1: State Update Processing)."""
        command_string = command_string.strip()

        # remove the < and > from start and end of string
        new_command_string = command_string
        if new_command_string.startswith('<') and new_command_string.endswith('>'):
            new_command_string = command_string[1:-1].strip()

        # Handle Case 1: Variables within command strings
        # Replace <variable> placeholders with actual values
        new_command_string = self._resolve_variables_in_command_string(new_command_string)

        # Split command by commas if it contains multiple commands
        commands = new_command_string.split(',') if ',' in new_command_string else [new_command_string]
        
        # Normalize command to lowercase for consistency
        first_command = commands[0].strip().lower()
        if first_command.startswith('/'):
            # If the command starts with a slash, remove it for consistency
            first_command = first_command[1:]  # Remove leading slash if present

        # Check if the first command is an end command
        end_commands = False
        if first_command.startswith('end'):
            end_commands = True

        # Normalize all commands to lowercase and handle end commands
        # if the first command is an end command, all subsequent commands are end commands
        for command in commands:
            command = command.strip().lower()
            if '/' in command:
                command = command[1:]  # Remove leading slash if present
            if end_commands and not command.startswith('end'):
                command = f'end {command}'

        # Determine the type of command based on the first command
        # check if not fmt command first (could be the name of a format)
        command_type: Optional[str] = None
        if 'fmt' not in first_command:
            if end_commands:
                # Handle end commands
                if first_command.startswith('end '):
                    command_type = 'end'
            elif self._is_debug_command(first_command):
                command_type = 'debug'
            elif self._is_text_formatting_command(first_command):
                command_type = 'text'
            elif self._is_time_command(first_command):
                command_type = 'time'
            elif self._is_box_command(first_command):
                command_type = 'box'
            else:
                # convert this element to a plain text element
                command_type = None

        elif first_command.startswith('fmt'):
            command_type = 'text'
        else:
            command_type = None

        # If no command type is determined, treat as plain text
        if command_type is None:
            self._convert_piece_to_text(original or f'</{command_string}>')
            return

        invalid_commands = []

        for command in commands:
            if command_type == 'debug':
                if not self._execute_debug_command(command):
                    invalid_commands.append(command)
            elif command_type == 'text':
                if not self._execute_text_formatting_command(command):
                    invalid_commands.append(command)
            elif command_type == 'time':
                if not self._execute_time_command(command):
                    invalid_commands.append(command)
            elif command_type == 'box':
                if not self._execute_box_command(command):
                    invalid_commands.append(command)
            elif command_type == 'end':
                if not self._execute_end_command(command):
                    invalid_commands.append(command)
        
        if invalid_commands:
            raise ValueError(
                f"There are invalid commands in this command string: {', '.join(invalid_commands)}."
                f"Command type: {command_type}. Please group commands correctly and ensure they are valid."
            )

    def _execute_debug_command(self, command: str) -> bool:
        """
        Execute a debug command, if the command is one.
        
        Returns:
            bool: True if the command was executed, False otherwise
        """
        if command == 'debug':
            self.debug_mode = True
            return True
        
        if command == 'end debug' and not self.debug_printing:
            self.debug_mode = False
            return True

        return False

    def _execute_text_command(self, command: str) -> bool:
        """
        Execute a command directly associated with text appearance, and not 
        related to color.

        Returns:
            bool: True if the command was executed, False otherwise
        """

        # Text formatting commands
        if command == 'bold':
            self.bold = True
            return True
        if command == 'italic':
            self.italic = True
            return True
        if command == 'underline':
            self.underline = True
            return True
        if command == 'strikethrough':
            self.strikethrough = True
            return True
            
        # End commands for text formatting
        if command == 'end bold':
            self.bold = False
            return True
        if command == 'end italic':
            self.italic = False
            return True
        if command == 'end underline':
            self.underline = False
            return True
        if command == 'end strikethrough':
            self.strikethrough = False
            return True
        
        # Justification commands
        if command in ['justify left', 'left justify', 'left']:
            if self.justify != 'left':
                self._handle_new_justification()
                self.justify = 'left'
            return True
        if command in ['justify center', 'center justify', 'center']:
            if self.justify != 'center':
                self._handle_new_justification()
                self.justify = 'center'
            return True
        if command in ['justify right', 'right justify', 'right']:
            if self.justify != 'right':
                self._handle_new_justification()
                self.justify = 'right'
            return True
        
        if command == 'end justify':
            # Reset justification to default
            if self.justify != 'left':
                self._handle_new_justification()
            self.justify = 'left'
            return True
 
        return False
    
    def _execute_color_command(self, command: str) -> bool:
        """
        Execute a color command, if the command is one.
        
        Returns:
            bool: True if the command was executed, False otherwise
        """

        # many issues:
        # we arent actually converting colors correctly here.
        
        if _color_converter.is_valid_color(command):
            self.current_text_color_command = command
            # actually set text_color correctly by converting to RGB
            return True
        
        # Background color commands
        if command.startswith('bkg '):
            bg_color = command[4:].strip()
            if _color_converter.is_valid_color(bg_color):
                self.current_background_color_command = bg_color
                # actually set background_color correctly by converting to RGB
            return True
            
        # End color commands
        if command.startswith('end '):
            color_name = command[4:]
            if color_name == self.current_text_color_command:
                self.text_color = None
                self.current_text_color_command = None
                return True
            elif 'bkg' in color_name:
                bg_color = color_name[4:].strip()
                if bg_color == self.current_background_color_command:
                    self.background_color = None
                    self.current_background_color_command = None
                return True
            else:
                raise ValueError(f"End color command '{command}' does not match any current color command.")
            
        return False
    
    def _execute_fmt_command(self, command: str) -> bool:
        """
        Execute a formatting command, if the command is one.
        
        Returns:
            bool: True if the command was executed, False otherwise
        """
        if not command.startswith('fmt '):
            return False
            
        format_name = command[4:].strip()
        return self._apply_format_internal(format_name)



    def _execute_text_formatting_command(self, command: str) -> bool:
        """
        Execute a text formatting command, if the command is one.
        
        Returns:
            bool: True if the command was executed, False otherwise
        """
        # Check if this is a text formatting command
        if self._execute_text_command(command):
            return True
        
        # Check if this is a color command
        if self._execute_color_command(command):
            return True
        
        # Check if this is a fmt command
        if self._execute_fmt_command(command):
            return True
        
        return False
    
    def _execute_time_command(self, command: str) -> bool:
        """
        Execute a time formatting command, if the command is one.

        Returns:
            bool: True if the command was executed, False otherwise
        """
        # Time formatting commands
        if command == '12hr':
            self.twelve_hour_time = True
            return True
        if command == '24hr':
            self.twelve_hour_time = False
            return True
        if command.startswith('tz '):
            timezone = command[3:].strip().lower()
            if not timezone:
                raise ValueError("Timezone cannot be empty.")
            self.timezone = timezone
            return True
        if command.startswith('smart time'):
            # get last char in command
            units = command[-1:]
            if units.isdigit():
                self.smart_time = int(units)
                return True
            else:
                raise ValueError(f"Invalid smart time units: {units}. Must be a digit.")
        if command.startswith('decimals '):
            decimal_places = command[9:].strip()
            if decimal_places.isdigit():
                decimal_value = int(decimal_places)
                if 0 <= decimal_value <= 10:
                    self.timestamp_decimal_places = decimal_value
                    return True
                else:
                    raise ValueError(f"Decimal places must be between 0 and 10, got {decimal_value}.")
            else:
                raise ValueError(f"Invalid decimal places: {decimal_places}. Must be a digit between 0 and 10.")
        if command == 'seconds':
            self.use_seconds_in_timestamp = True
            return True
        
        # End time commands
        if command == 'end 12hr':
            self.twelve_hour_time = False
            return True
        if command == 'end 24hr':
            self.twelve_hour_time = True
            return True
        if command == 'end tz':
            self.timezone = None
            return True
        if command == 'end smart time':
            self.smart_time = 3  # Reset to default
            return True
        if command == 'end decimals':
            self.timestamp_decimal_places = 4  # Reset to default
            return True
        if command == 'end seconds':
            self.use_seconds_in_timestamp = False  # Reset to default
            return True
            
        return False
    
    def _execute_box_command(self, command: str) -> bool:
        """
        Execute a box command, if the command is one.
        
        Returns:
            bool: True if the command was executed, False otherwise
        """
        # Box styles
        box_styles = ['square', 'rounded', 'double', 'heavy', 'heavy_head', 'horizontals', 'ascii']
        
        # Handle "box style" commands - these start a new box
        for style in box_styles:
            if command == f'box {style}':
                self._start_box(style)
                return True
        
        # Handle plain "box" command (default style)
        if command == 'box':
            self._start_box('square')  # default style
            return True
            
        # Handle "end box" command
        if command == 'end box':
            self._end_box()
            return True
            
        # Handle box-related parameters when we're in box context
        # These are commands that appear after the initial "box style" in a group
        
        # Title commands: "title Important" or "title <variable>"
        if command.startswith('title '):
            title_content = command[6:].strip()
            if title_content.startswith('<') and title_content.endswith('>'):
                # Variable reference - consume next value
                try:
                    self.box_title = str(self.get_next_value())
                except ExtraVariableError:
                    self.box_title = title_content  # fallback to literal
            else:
                # Literal title
                self.box_title = title_content
            return True
            
        # Color commands for box
        if _color_converter.is_valid_color(command):
            self.box_color = command
            return True
            
        # Special box color commands
        if command == 'color current':
            self.box_color = self.text_color
            return True
            
        # Box justification commands
        if command in ['justify left', 'justify center', 'justify right']:
            # This sets justification for the entire box, not just box content
            justify_type = command.split()[1]  # 'left', 'center', 'right'
            # TODO: Implement box justification
            return True
            
        return False


    def _execute_end_command(self, command: str) -> bool:
        """
        Execute an end command, if the command is one.

        End commands are unique because they can span multiple types command groups
        in one command string, such as: </end cyan, tz, 12hr, box>
        
        Returns:
            bool: True if the command was executed, False otherwise
        """
        if not command.startswith('end '):
            return False
            
        end_target = command[4:].strip()
        
        # Route to appropriate handler based on the target
        if end_target == 'debug':
            return self._execute_debug_command(command)
        elif end_target in ['bold', 'italic', 'underline', 'strikethrough', 'justify']:
            return self._execute_text_command(command)
        elif _color_converter.is_valid_color(end_target) or end_target.startswith('bkg '):
            return self._execute_color_command(command)
        elif end_target == 'box':
            return self._execute_box_command(command)
        elif end_target in ['12hr', '24hr', 'tz', 'smart time']:
            return self._execute_time_command(command)
        elif end_target == 'all':
            # End all formatting
            self.reset_non_box_formatting()
            return True
        else:
            return False
    
    def _convert_piece_to_text(self, command_string: str):
        """Convert a command piece to plain text when it's not recognized as a command."""
        # Add the text with current formatting
        self._add_formatted_content_to_raw_output(command_string, use_current_formatting=True)
    
    def _handle_new_justification(self):
        """Process raw output before changing justification."""
        self._process_raw_output()
    
    def _apply_format_internal(self, format_name: str) -> bool:
        """Apply a named format from the format registry."""
        # TODO: Implement format registry lookup and application
        # For now, handle the example "warning" format
        if format_name == 'warning':
            # From example: '</bkg yellow, black, bold>'
            self.background_color = 'yellow'
            self.current_background_color_command = 'yellow'
            self.text_color = 'black'
            self.current_text_color_command = 'black'
            self.bold = True
            return True
        return False
    
    def _resolve_variables_in_command_string(self, command_string: str) -> str:
        """
        Handle Case 1: Variables within command strings.
        
        Replace <variable> placeholders with actual values from the values tuple.
        Example: "bold, <self.current_text_color>" → "bold, red"
        """
        import re
        
        # Find all <variable> patterns in the command string
        variable_pattern = r'<([^>]+)>'
        variables = re.findall(variable_pattern, command_string)
        
        # Replace each variable with its value
        resolved_string = command_string
        for var_name in variables:
            try:
                # Get the next value from the tuple
                value = str(self.get_next_value())
                # Replace the <variable> with the actual value
                resolved_string = resolved_string.replace(f'<{var_name}>', value)
            except ExtraVariableError:
                # No more values available - leave the variable placeholder as is
                # This will cause it to be treated as literal text later
                pass
        
        return resolved_string
    
    def _is_fdl_syntax_string(self, value: str) -> bool:
        """
        Check if a string contains FDL syntax (commands or objects).
        
        Detect patterns like:
        - Commands: "</bold, italic>text"
        - Objects: "<time:>" or "<time:timestamp>"
        """
        import re
        
        # Check for FDL syntax patterns: </...> (commands) or <...:...> (objects)
        fdl_pattern = r'<\/[^>]*>|<[^>]*:[^>]*>'
        return bool(re.search(fdl_pattern, value))
    
    def _process_fdl_command_from_variable(self, fdl_string: str):
        """
        Handle Case 2: Process an FDL string that came from a variable.
        
        The embedded FDL string is processed in isolation - it does not modify
        the main formatter's state. Any formatting commands in the embedded string
        only affect the content within that string.
        
        Example: fmted_str = "</bold, italic>Bolded and italicized text"
                 fdl.print("<fmted_str>", fmted_str)
                 
        The resulting text will be bold and italic regardless of current state,
        and the main formatter's state remains unchanged.
        """
        # Create an isolated formatter for processing the embedded FDL string
        isolated_formatter = _Formatter(fdl_string, tuple())
        # Set debug mode to match the main formatter
        isolated_formatter.debug_mode = self.debug_mode
        
        # Process the embedded string in isolation
        isolated_formatter.process()
        
        # Get the terminal output from the isolated formatter
        isolated_output = isolated_formatter.terminal_output
        
        # Add the isolated output to our current outputs
        # The isolated output already contains all necessary ANSI codes
        if self.in_box:
            self.box_content.append(isolated_output)
        else:
            self.raw_terminal_output.append(isolated_output)
            self.raw_plain_output.append(isolated_formatter.plain_output)
            self.raw_markdown_output.append(isolated_formatter.markdown_output)
            self.raw_html_output.append(isolated_formatter.html_output)
    
    def _start_box(self, style: str):
        """Start a new box with the given style."""
        # Process raw output before starting box (from flow)
        self._process_raw_output()
        
        # Set box state
        self.in_box = True
        self.box_style = style
        self.box_color = self.text_color  # Default to current text color
        self.box_title = None
        # Clear any previous box content
        self.box_content = []
    
    def _end_box(self):
        """End the current box and generate its output."""
        if not self.in_box:
            return
            
        # Combine box_content into single string
        combined_content = ''.join(self.box_content)
        
        if combined_content.strip():
            # Step 1: Wrap and center the content (default inside boxes is center)
            wrapped_lines = _text_wrapper.wrap_text(combined_content)
            wrapped_text = '\n'.join(wrapped_lines)
            centered_content = _text_justifier.justify_text(wrapped_text, 'center')
            
            # Step 2: Measure maximum width (actual_box_width = max_width + 6 for padding/borders)
            content_lines = centered_content.split('\n')
            max_content_width = max(len(line) for line in content_lines) if content_lines else 0
            actual_box_width = max_content_width + 6  # 2 spaces padding + 2 borders on each side
            
            # Step 3: Create a new box generator with current settings
            box_gen = _BoxGenerator(
                style=self.box_style,
                title=self.box_title,
                color=self.box_color,
                box_justify=self.justify,  # Current text justification for the entire box
                terminal_width=self.terminal_width
            )
            
            # Step 4: Generate box around content
            box_outputs = box_gen.generate_box(content_lines)
            
            # Step 5: Add completed box directly to final output (bypasses raw output)
            for output_type in self.output_types:
                if output_type == _OutputType.TERMINAL:
                    self.terminal_output += box_outputs.get('terminal', '') + '\n'
                elif output_type == _OutputType.PLAIN:
                    self.plain_output += box_outputs.get('plain', '') + '\n'
                elif output_type == _OutputType.MARKDOWN:
                    self.markdown_output += box_outputs.get('markdown', '') + '\n'
                elif output_type == _OutputType.HTML:
                    self.html_output += box_outputs.get('html', '') + '\n'
        
        # Step 6: Reset box state
        self.reset_box_state()

    def _handle_box_command(self, box_params: str):
        """Handle box start command with parameters."""
        # Process raw output before starting box (from flow)
        self._process_raw_output()
        
        # Parse box parameters
        params = [p.strip() for p in box_params.split(',')]
        
        # Set box state
        self.in_box = True
        self.box_style = "square"  # default
        self.box_color = self.text_color  # "color current" from example
        self.box_title = None
        
        for param in params:
            param = param.lower()
            if param in ['square', 'rounded', 'double', 'thick']:
                self.box_style = param
            elif param == 'color current':
                self.box_color = self.text_color
            elif param.startswith('bkg '):
                # Background color for box
                pass  # TODO: implement box background
            elif param.startswith('title '):
                # Title is a variable reference - extract from values
                title_ref = param[6:].strip()
                if title_ref.startswith('<') and title_ref.endswith('>'):
                    # It's a variable like <self.name>
                    try:
                        self.box_title = str(self.get_next_value())
                    except ExtraVariableError:
                        self.box_title = title_ref
                else:
                    self.box_title = title_ref
    
    def _handle_end_box(self):
        """Handle box end command - generate and add box to output."""
        if not self.in_box:
            return
            
        # Combine box_content into single string
        combined_content = ''.join(self.box_content)
        
        if combined_content.strip():
            # Wrap content inside box constraints
            box_wrapper = _TextWrapper(width=self.actual_box_width)
            wrapped_lines = box_wrapper.wrap_text(combined_content)
            
            # Apply justification to content
            wrapped_text = '\n'.join(wrapped_lines)
            justified_content = _text_justifier.justify_text(wrapped_text, self.justify)
            
            # Create a new box generator with current settings
            box_gen = _BoxGenerator(
                style=self.box_style,
                title=self.box_title,
                color=self.box_color,
                box_justify=self.justify,
                terminal_width=self.terminal_width
            )
            
            # Generate box around content - split justified content into lines
            content_lines = justified_content.split('\n') if justified_content else ['']
            box_outputs = box_gen.generate_box(content_lines)
            
            # Add completed box directly to final output (bypasses raw output)
            for output_type in self.output_types:
                if output_type == _OutputType.TERMINAL:
                    self.terminal_output += box_outputs.get('terminal', '') + '\n'
                elif output_type == _OutputType.PLAIN:
                    self.plain_output += box_outputs.get('plain', '') + '\n'
                elif output_type == _OutputType.MARKDOWN:
                    self.markdown_output += box_outputs.get('markdown', '') + '\n'
                elif output_type == _OutputType.HTML:
                    self.html_output += box_outputs.get('html', '') + '\n'
        
        # Reset box state
        self.reset_box_state()
    
    def _apply_format(self, format_name: str):
        """Apply a named format from the format registry."""
        # TODO: Implement format registry lookup and application
        # For now, handle the example "warning" format
        if format_name == 'warning':
            # From example: '</bkg yellow, black, bold>'
            self.background_color = 'yellow'
            self.text_color = 'black'
            self.bold = True
    
    def _strip_ansi_codes(self, text: str) -> str:
        """Strip ANSI codes from text for plain/markdown/html output."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _execute_object(self, obj_content: str) -> Optional[str]:
        """Execute an object and return its text representation."""
        # Split object content by colon
        if ':' in obj_content:
            obj_type, obj_param = obj_content.split(':', 1)
            obj_type = obj_type.strip()
            obj_param = obj_param.strip()
        else:
            obj_type = obj_content.strip()
            obj_param = None
            
        # Handle type objects for debug mode
        if obj_type == 'type' and obj_param:
            # <type:variable> - get type annotation for the variable
            try:
                value = self.get_next_value()
                value_type = type(value).__name__
                return f" ({value_type})"
            except ExtraVariableError:
                return f" (unknown)"
                
        # Handle time objects - follow the exact flow from info.md
        if obj_type == 'time':
            if obj_param:
                # <time:self.time_connected_at> - get timestamp from values
                try:
                    timestamp = self.get_next_value()
                    if isinstance(timestamp, (int, float)):
                        return self._format_timestamp(timestamp)
                    else:
                        return "</ERROR>"  # From flow: "If it isn't a float, we display </ERROR>"
                except ExtraVariableError:
                    return "</ERROR>"
            else:
                # <time:> - current time
                import time
                current_time = time.time()
                return self._format_timestamp(current_time)
        
        # Handle spinner objects
        if obj_type == 'spinner':
            # TODO: Integrate refactored spinner system
            # Return simple spinner character for now
            return "●"
            
        # Note: Tables are separate fdl.Table class, not FDL objects
            
        return None
    
    def _format_timestamp(self, timestamp: float) -> str:
        """
        Format a timestamp according to current time settings using pure float-based formatting.
        
        No datetime objects are used - everything is based on Unix float timestamps for
        finer control and cleaner output.
        """
        # Apply timezone offset if set (convert timezone string to offset)
        if self.timezone:
            timezone_offset = self._get_timezone_offset(self.timezone)
            timestamp += timezone_offset
        
        # Calculate time components manually from Unix timestamp
        total_seconds = int(timestamp)
        fractional_seconds = timestamp - total_seconds
        
        # Get time components
        seconds_in_day = total_seconds % 86400  # 86400 seconds in a day
        hours = seconds_in_day // 3600
        minutes = (seconds_in_day % 3600) // 60
        seconds = seconds_in_day % 60
        
        # Add fractional seconds with decimal places
        seconds_with_decimals = seconds + fractional_seconds
        
        # Format based on 12hr/24hr setting
        if self.twelve_hour_time:
            # 12-hour format: 2:03:46.1234 AM or 2:03 AM
            display_hour = hours % 12
            if display_hour == 0:
                display_hour = 12
            am_pm = "AM" if hours < 12 else "PM"
            
            if not self.use_seconds_in_timestamp:
                # No seconds: 2:03 AM
                return f"{display_hour}:{minutes:02d} {am_pm}"
            elif self.timestamp_decimal_places > 0:
                # With seconds and decimals: 2:03:46.1234 AM
                return f"{display_hour}:{minutes:02d}:{seconds_with_decimals:0{3+self.timestamp_decimal_places}.{self.timestamp_decimal_places}f} {am_pm}"
            else:
                # With seconds, no decimals: 2:03:46 AM
                return f"{display_hour}:{minutes:02d}:{seconds:02d} {am_pm}"
        else:
            # 24-hour format: 02:03:46.1234, 14:03:46, or 02:03
            if not self.use_seconds_in_timestamp:
                # No seconds: 02:03
                return f"{hours:02d}:{minutes:02d}"
            elif self.timestamp_decimal_places > 0:
                # With seconds and decimals: 02:03:46.1234
                return f"{hours:02d}:{minutes:02d}:{seconds_with_decimals:0{3+self.timestamp_decimal_places}.{self.timestamp_decimal_places}f}"
            else:
                # With seconds, no decimals: 02:03:46
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _get_timezone_offset(self, timezone: str) -> float:
        """
        Get timezone offset in seconds from timezone string.
        
        Returns the offset to add to UTC timestamp to get local time.
        Supports common timezone abbreviations with daylight savings.
        """
        # Basic timezone mappings (in hours from UTC)
        timezone_offsets = {
            'utc': 0, 'gmt': 0,
            'est': -5, 'edt': -4,  # Eastern Time
            'cst': -6, 'cdt': -5,  # Central Time  
            'mst': -7, 'mdt': -6,  # Mountain Time
            'pst': -8, 'pdt': -7,  # Pacific Time
            'cet': 1, 'cest': 2,   # Central European Time
        }
        
        offset_hours = timezone_offsets.get(timezone.lower(), 0)
        return offset_hours * 3600  # Convert hours to seconds
    
    def _process_raw_output(self):
        """Process raw output into final formatted output using setup utilities."""
        # Update wrapper and justifier with current terminal width
        _text_wrapper.width = self.terminal_width
        _text_justifier.terminal_width = self.terminal_width
        
        # Process each output stream
        for output_type in self.output_types:
            if output_type == _OutputType.TERMINAL:
                self._process_raw_terminal_output()
            elif output_type == _OutputType.PLAIN:
                self._process_raw_plain_output()
            elif output_type == _OutputType.MARKDOWN:
                self._process_raw_markdown_output()
            elif output_type == _OutputType.HTML:
                self._process_raw_html_output()
    
    def _process_raw_terminal_output(self):
        """Process raw terminal output with wrapping and justification."""
        if not self.raw_terminal_output:
            return
            
        content = ''.join(self.raw_terminal_output)
        if content.strip():
            # Wrap text (handles ANSI codes properly)
            wrapped_lines = _text_wrapper.wrap_text(content)
            wrapped_text = '\n'.join(wrapped_lines)
            
            # Apply justification
            justified_text = _text_justifier.justify_text(wrapped_text, self.justify)
            
            self.terminal_output = justified_text
            self.raw_terminal_output.clear()
    
    def _process_raw_plain_output(self):
        """Process raw plain output with wrapping and justification."""
        if not self.raw_plain_output:
            return
            
        content = ''.join(self.raw_plain_output)
        if content.strip():
            # Plain text wrapping (no ANSI codes)
            wrapped_lines = _text_wrapper.wrap_text(content)
            wrapped_text = '\n'.join(wrapped_lines)
            
            # Apply justification (plain text)
            justified_text = _text_justifier.justify_text(wrapped_text, self.justify)
            
            self.plain_output = justified_text
            self.raw_plain_output.clear()
    
    def _process_raw_markdown_output(self):
        """Process raw markdown output."""
        if not self.raw_markdown_output:
            return
            
        content = ''.join(self.raw_markdown_output)
        self.markdown_output = content
        self.raw_markdown_output.clear()
    
    def _process_raw_html_output(self):
        """Process raw HTML output."""
        if not self.raw_html_output:
            return
            
        content = ''.join(self.raw_html_output)
        self.html_output = content
        self.raw_html_output.clear()
    
    def _calculate_max_box_width(self) -> int:
        """
        Calculate maximum usable box content width.
        
        Returns:
            int: Maximum width for box content
        """
        # Account for box edges - conservative estimate for Unicode
        edge_width = 4  # 2 chars on each side (left + right borders)
        
        # Account for horizontal padding inside box
        padding_width = 4  # 2 spaces on each side
        
        # Calculate usable width
        usable_width = self.terminal_width - edge_width - padding_width
        
        # Ensure minimum usable width for readability
        return max(40, usable_width)

    def process(self):
        """
        Process the FDL string according to the new architecture flow.
        """
        # Process each piece sequentially
        for piece in self.parsed_pieces:
            self._process_piece(piece)

        # Process any remaining raw output
        self._process_raw_output()

        # Wait for progress bars to complete
        while _progress_bar_manager.has_active_bar():
            time.sleep(0.0166)  # ~60 FPS

        self.ready_to_output = True
            
        return {
            'terminal': self.terminal_output,
            'plain': self.plain_output,
            'markdown': self.markdown_output,
            'html': self.html_output
        }
  
  
    def copy(self):
        pass
    
    def reset_text_formatting(self):
        """Reset all text formatting to defaults."""
        self.text_color = None
        self.current_text_color_command = None
        self.background_color = None
        self.current_background_color_command = None
        self.bold = False
        self.italic = False
        self.underline = False
        self.strikethrough = False
        if self.justify != 'left':
            self._handle_new_justification()
        self.justify = 'left'  # Default justification
    
    def reset_time_settings(self):
        """Reset all time formatting settings to defaults."""
        self.twelve_hour_time = False
        self.timezone = None
        self.smart_time = 4
    
    def reset_box_state(self):
        """Reset all box-related state, after completing a box."""
        self.in_box = False
        self.box_style = "square"
        self.box_title = None
        self.box_color = None
        self.box_content.clear()
        self.actual_box_width = self.max_box_width

    def reset_non_box_formatting(self):
        """
        Reset all formatting to default values, except for box state.
        
        This is called when /end all or /reset is used in the FDL string.
        """
        self.reset_text_formatting()
        self.reset_time_settings()

        if not self.debug_printing:
            self.debug_mode = False

    def reset_output_streams(self):
        """Reset all output streams to empty."""
        self.raw_terminal_output.clear()
        self.raw_plain_output.clear()
        self.raw_markdown_output.clear()
        self.raw_html_output.clear()

        self.terminal_output = ""
        self.plain_output = ""
        self.markdown_output = ""
        self.html_output = ""

        self.ready_to_output = False

    def reset_all(self):
        """
        Reset all state to initial values.
        
        This is used when starting a new FDL processing cycle.
        """
        self.reset_text_formatting()
        self.reset_time_settings()
        self.reset_box_state()
        self.reset_non_box_formatting()
        self.reset_output_streams()

        # Reset active formats
        self.active_formats.clear()

    def get_next_value(self):
        """
        Get the next value from the values tuple and increment index.
        
        Returns:
            Any: Next value from tuple
            
        Raises:
            ExtraVariableError: If no more values available
        """
        if self.value_index >= len(self.values):
            raise ExtraVariableError(f"No more values available (index {self.value_index})")
        
        value = self.values[self.value_index]
        self.value_index += 1
        return value
    
    def has_more_values(self) -> bool:
        """Check if there are more values available."""
        return self.value_index < len(self.values)

def _create_formatter(
    fdl_string: str,
    values: Union[Tuple, Any],
    custom_terminal_width: Optional[int] = None,
    destinations: Set[_OutputType] = {_OutputType.TERMINAL}) -> '_Formatter':
    """
    Create a new formatter instance for processing FDL strings.
    
    Args:
        fdl_string (str): The FDL string to process
        values (Union[Tuple, Any]): Values for variable substitution
        destinations (Set[_OutputType]): Output types to process
        
    Returns:
        _Formatter: Initialized formatter instance
    """
    return _Formatter(fdl_string, values, custom_terminal_width, destinations)