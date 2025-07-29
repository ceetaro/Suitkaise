# processors/commands/box_commands.py
from typing import Optional, Dict, Any
from ...core.command_registry import _CommandProcessor, _command_processor
from ...core.format_state import _FormatState
from ...setup.color_conversion import _is_valid_color


@_command_processor(priority=5)  # High priority for box commands
class _BoxCommandProcessor(_CommandProcessor):
    """
    Processor for box-related commands.
    
    Handles:
    - Box creation: </box style, title Title, color, justify, bkg color>
    - Box termination: </end box>
    
    Box styles: square, rounded, double, heavy, heavy_head, horizontals, ascii
    Box justification: left, center, right (for box placement)
    Box content is always centered by default unless overridden
    """
    
    # Supported box styles
    SUPPORTED_STYLES = {
        'square', 'rounded', 'double', 'heavy', 'heavy_head', 
        'horizontals', 'ascii'
    }
    
    # Supported justification options
    SUPPORTED_JUSTIFY = {'left', 'center', 'right'}
    
    @classmethod
    def can_process(cls, command: str) -> bool:
        """
        Check if this processor can handle the given command.
        
        Handles:
        - box <style> [, title <title>] [, color] [, bkg <color>] [, justify <direction>]
        - end box
        
        Args:
            command: Command string to check
            
        Returns:
            bool: True if this processor can handle the command
        """
        command = command.strip().lower()
        
        # End box command
        if command == 'end box':
            return True
        
        # Box start command
        if command.startswith('box '):
            return True
        
        return False
    
    @classmethod
    def process(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process a box command and update format state.
        
        Args:
            command: Command to process
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        command = command.strip()
        command_lower = command.lower()
        
        if command_lower == 'end box':
            return cls._process_end_box(format_state)
        elif command_lower.startswith('box '):
            return cls._process_start_box(command, format_state)
        
        return format_state
    
    @classmethod
    def _process_start_box(cls, command: str, format_state: _FormatState) -> _FormatState:
        """
        Process box start command.
        
        Args:
            command: Full box command
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        # Cannot create boxes inside boxes
        if format_state.in_box:
            # Silently ignore nested box attempts or could add warning
            return format_state
        
        # Parse box parameters
        box_params = cls._parse_box_parameters(command)
        
        # Validate style
        style = box_params.get('style', 'square')
        if style not in cls.SUPPORTED_STYLES:
            style = 'square'  # Default fallback
        
        # Set box state
        format_state.in_box = True
        format_state.box_style = style
        format_state.box_title = box_params.get('title')
        
        # Handle colors
        if 'color' in box_params:
            if box_params['color'] == 'current':
                # Use current text color
                format_state.box_color = format_state.text_color
            elif _is_valid_color(box_params['color']):
                format_state.box_color = box_params['color']
        
        if 'background' in box_params:
            if _is_valid_color(box_params['background']):
                format_state.box_background = box_params['background']
        
        # Handle justification (for box placement, not content)
        if 'justify' in box_params:
            justify = box_params['justify']
            if justify in cls.SUPPORTED_JUSTIFY:
                format_state.justify = justify
        
        # Clear any existing box content
        format_state.box_content.clear()
        
        return format_state
    
    @classmethod
    def _process_end_box(cls, format_state: _FormatState) -> _FormatState:
        """
        Process end box command - generates and outputs the box.
        
        Args:
            format_state: Current format state
            
        Returns:
            _FormatState: Updated format state
        """
        if not format_state.in_box:
            # Not in a box, ignore silently
            return format_state
        
        # Generate the box
        box_output = cls._generate_box(format_state)
        
        # Add newline before box (boxes are on their own lines)
        format_state.add_to_output_streams(
            terminal='\n',
            plain='\n', 
            markdown='\n',
            html='<br>\n'
        )
        
        # Add the box to all output streams
        format_state.add_to_output_streams(
            terminal=box_output['terminal'],
            plain=box_output['plain'],
            markdown=box_output['markdown'], 
            html=box_output['html']
        )
        
        # Add newline after box
        format_state.add_to_output_streams(
            terminal='\n',
            plain='\n',
            markdown='\n', 
            html='<br>\n'
        )
        
        # Reset box state
        format_state.reset_box_state()
        
        return format_state
    
    @classmethod
    def _parse_box_parameters(cls, command: str) -> Dict[str, Any]:
        """
        Parse box command parameters.
        
        Format: box <style>[, title <title>][, <color>][, bkg <color>][, justify <direction>]
        
        Args:
            command: Full box command string
            
        Returns:
            Dict[str, Any]: Parsed parameters
        """
        params = {}
        
        # Remove 'box ' prefix
        param_string = command[4:].strip()
        
        # Handle the case where title might contain commas
        # We need to be careful about parsing
        parts = []
        current_part = ""
        in_title = False
        title_content = ""
        
        i = 0
        while i < len(param_string):
            char = param_string[i]
            
            if not in_title and char == ',' and not param_string[i:i+6].lower().startswith('title'):
                # Regular comma separator
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
            elif param_string[i:i+5].lower() == 'title':
                # Found title keyword
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
                in_title = True
                title_start = i + 5
                # Skip whitespace after 'title'
                while title_start < len(param_string) and param_string[title_start].isspace():
                    title_start += 1
                # Find the end of the title (next comma or end of string)
                title_end = title_start
                while title_end < len(param_string) and param_string[title_end] != ',':
                    title_end += 1
                title_content = param_string[title_start:title_end].strip()
                params['title'] = title_content
                i = title_end - 1  # Will be incremented at end of loop
                in_title = False
            else:
                current_part += char
            
            i += 1
        
        # Add the last part
        if current_part.strip():
            parts.append(current_part.strip())
        
        # Process parts
        for part in parts:
            part_lower = part.lower()
            
            # Box style (first parameter, or explicit style)
            if not params.get('style') and part_lower in cls.SUPPORTED_STYLES:
                params['style'] = part_lower
            
            # Color (not background)
            elif part_lower.startswith('bkg '):
                bg_color = part[4:].strip()
                if _is_valid_color(bg_color) or bg_color.lower() == 'current':
                    params['background'] = bg_color.lower()
            
            # Justification
            elif part_lower.startswith('justify '):
                justify = part[8:].strip().lower()
                if justify in cls.SUPPORTED_JUSTIFY:
                    params['justify'] = justify
            
            # Color (standalone)
            elif _is_valid_color(part) or part_lower == 'current':
                if 'color' not in params:  # Don't override if already set
                    params['color'] = part_lower
        
        # Set default style if none provided
        if 'style' not in params:
            params['style'] = 'square'
        
        return params
    
    @classmethod
    def _generate_box(cls, format_state: _FormatState) -> Dict[str, str]:
        """
        Generate box output for all formats.
        
        Args:
            format_state: Current format state with box content
            
        Returns:
            Dict[str, str]: Generated box for each output format
        """
        from ...setup.box_generator import _BoxGenerator
        
        # Create box generator with updated parameters
        generator = _BoxGenerator(
            style=format_state.box_style,
            title=format_state.box_title,
            color=format_state.box_color,
            box_justify=format_state.justify or 'left',
            terminal_width=format_state.terminal_width
        )
        
        # Join all box content and split into lines for the generator
        content = ''.join(format_state.box_content)
        
        # Wrap the content using text wrapper before passing to box generator
        from ...setup.text_wrapping import _TextWrapper
        wrapper = _TextWrapper(width=format_state.terminal_width - 4)  # Account for box borders
        content_lines = wrapper.wrap_text(content) if content.strip() else [' ']
        
        # Generate box for all formats
        return generator.generate_box(content_lines)


def _is_box_command(command: str) -> bool:
    """
    Check if command is a box-related command.
    
    Args:
        command: Command to check
        
    Returns:
        bool: True if box command
    """
    command_lower = command.strip().lower()
    return command_lower == 'end box' or command_lower.startswith('box ')