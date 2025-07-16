"""
Internal, Stateless Command Processor for fdl - Maximum Performance Utility

This module provides a stateless command processing utility that converts
fdl format commands to ANSI escape sequences with aggressive caching.

The command processor is a pure utility - it takes commands and current state,
returns new state and ANSI codes. State management is handled by the reconstructor.

Features:
- Stateless design - no internal state management
- Pure functions for easy testing and reasoning
- Aggressive caching of color conversions and state transitions
- Thread-safe caching design
- Support for all fdl command types including reset commands
- Minimal ANSI output through incremental state changes
- Format application during compilation (breaks circular imports)
"""

import threading
from typing import Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
import warnings

warnings.simplefilter("always")

class CommandError(Exception):
    """Raised when command processing fails."""
    pass


class InvalidCommandError(CommandError):
    """Raised when a command is syntactically invalid."""
    pass


class UnsupportedCommandError(CommandError):
    """Raised when a command is not supported."""
    pass

@dataclass
class _FormattingState:
    """
    Represents the complete formatting state of the terminal.
    
    Attributes:
        text_color (Optional[str]): Current text color (None = default)
        background_color (Optional[str]): Current background color (None = default)
        bold (bool): Bold text formatting active
        italic (bool): Italic text formatting active  
        underline (bool): Underline text formatting active
        strikethrough (bool): Strikethrough text formatting active
        justify (Optional[str]): Text justification type (left, right, center)
        active_formats (Set[str]): Set of active named formats
    """
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    justify: Optional[str] = None
    active_formats: Set[str] = field(default_factory=set)

    def copy(self) -> '_FormattingState':
        """Create a deep copy of this state."""
        return _FormattingState(
            text_color=self.text_color,
            background_color=self.background_color,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            strikethrough=self.strikethrough,
            justify=self.justify,
            active_formats=self.active_formats.copy()
        )
    
    def reset(self) -> None:
        """Reset all formatting to None/False."""
        self.text_color = None
        self.background_color = None
        self.bold = False
        self.italic = False
        self.underline = False
        self.strikethrough = False
        self.justify = None
        self.active_formats.clear()

    def apply_defaults_from(self, default_state: '_FormattingState') -> None:
        """Apply default state values to this state."""
        self.text_color = default_state.text_color
        self.background_color = default_state.background_color
        self.bold = default_state.bold
        self.italic = default_state.italic
        self.underline = default_state.underline
        self.strikethrough = default_state.strikethrough
        self.justify = default_state.justify
        self.active_formats = default_state.active_formats.copy()

    def __eq__(self, other) -> bool:
        """Check equality for state comparison."""
        if not isinstance(other, _FormattingState):
            return False
        return (
            self.text_color == other.text_color and
            self.background_color == other.background_color and
            self.bold == other.bold and
            self.italic == other.italic and
            self.underline == other.underline and
            self.strikethrough == other.strikethrough and
            self.justify == other.justify and
            self.active_formats == other.active_formats
        )
    
    def __hash__(self) -> int:
        """Hash for use in caching."""
        return hash((
            self.text_color,
            self.background_color,
            self.bold,
            self.italic,
            self.underline,
            self.strikethrough,
            self.justify,
            tuple(sorted(self.active_formats))
        ))
    
class _ANSIConverter:
    """
    Converts formatting state changes to minimal ANSI escape sequences.
    
    Stateless utility that handles all color conversions with aggressive caching
    for maximum performance. Thread-safe design for concurrent usage.
    """
    
    # ANSI escape code constants
    RESET_ALL = '\033[0m'
    
    # Text formatting codes
    TEXT_FORMATTING = {
        'bold': ('\033[1m', '\033[22m'),
        'italic': ('\033[3m', '\033[23m'),
        'underline': ('\033[4m', '\033[24m'),
        'strikethrough': ('\033[9m', '\033[29m'),
    }

    # Named color codes (foreground)
    NAMED_COLORS = {
        'red': '\033[31m',
        'orange': '\033[38;5;208m',
        'yellow': '\033[33m',
        'green': '\033[32m',
        'blue': '\033[34m',
        'purple': '\033[35m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'pink': '\033[38;5;205m',
        'brown': '\033[38;5;94m',
        'tan': '\033[38;5;180m',
        'black': '\033[30m',
        'dark gray': '\033[90m',
        'gray': '\033[37m',
        'light gray': '\033[37m',
        'white': '\033[97m',
    }

    # Named background color codes
    NAMED_BG_COLORS = {
        'red': '\033[41m',
        'orange': '\033[48;5;208m',
        'yellow': '\033[43m',
        'green': '\033[42m',
        'blue': '\033[44m',
        'purple': '\033[45m',
        'magenta': '\033[45m',
        'cyan': '\033[46m',
        'pink': '\033[48;5;205m',
        'brown': '\033[48;5;94m',
        'tan': '\033[48;5;180m',
        'black': '\033[40m',
        'dark gray': '\033[100m',
        'gray': '\033[47m',
        'light gray': '\033[47m',
        'white': '\033[107m',
    }

    def __init__(self):
        """Initialize converter with caching."""
        # Cache for expensive color conversions
        self._hex_color_cache: Dict[str, str] = {}
        self._rgb_color_cache: Dict[Tuple[int, int, int], str] = {}
        self._hex_bg_cache: Dict[str, str] = {}
        self._rgb_bg_cache: Dict[Tuple[int, int, int], str] = {}
        
        # Cache for state transitions (key performance optimization)
        self._transition_cache: Dict[Tuple[_FormattingState, _FormattingState], str] = {}
        
        # Thread lock for cache safety
        self._cache_lock = threading.RLock()
        
        # Performance tracking
        self._cache_hits = 0
        self._cache_misses = 0

    def generate_transition_ansi(self, from_state: _FormattingState, to_state: _FormattingState) -> str:
        """
        Generate minimal ANSI sequence to transition between states.
        
        Args:
            from_state (FormattingState): Current formatting state
            to_state (FormattingState): Target formatting state
            
        Returns:
            str: Minimal ANSI escape sequence for the transition
            
        This is the core performance method - generates only the ANSI codes
        needed to change from one state to another, with aggressive caching.
        """
        # Check transition cache first
        cache_key = (from_state, to_state)
        with self._cache_lock:
            if cache_key in self._transition_cache:
                self._cache_hits += 1
                return self._transition_cache[cache_key]
            
            self._cache_misses += 1

        # If states are identical, no transition needed
        if from_state == to_state:
            ansi_sequence = ""
        else:
            ansi_sequence = self._calculate_transition_ansi(from_state, to_state)
        
        # Cache the result
        with self._cache_lock:
            self._transition_cache[cache_key] = ansi_sequence
        
        return ansi_sequence
    
    def _calculate_transition_ansi(self, from_state: _FormattingState, to_state: _FormattingState) -> str:
        """Calculate the actual ANSI transition sequence."""
        ansi_parts = []
        
        # Handle text formatting changes
        for fmt_name in ['bold', 'italic', 'underline', 'strikethrough']:
            from_value = getattr(from_state, fmt_name)
            to_value = getattr(to_state, fmt_name)
            
            if from_value != to_value:
                if to_value:
                    # Turn on formatting
                    ansi_parts.append(self.TEXT_FORMATTING[fmt_name][0])
                else:
                    # Turn off formatting
                    ansi_parts.append(self.TEXT_FORMATTING[fmt_name][1])
        
        # Handle text color changes
        if from_state.text_color != to_state.text_color:
            if to_state.text_color is None:
                ansi_parts.append('\033[39m')  # Reset to default color
            else:
                color_ansi = self._get_color_ansi(to_state.text_color)
                if color_ansi:
                    ansi_parts.append(color_ansi)

        # Handle background color changes
        if from_state.background_color != to_state.background_color:
            if to_state.background_color is None:
                ansi_parts.append('\033[49m')  # Reset to default background
            else:
                bg_ansi = self._get_background_ansi(to_state.background_color)
                if bg_ansi:
                    ansi_parts.append(bg_ansi)
        
        return ''.join(ansi_parts)
    
    def generate_reset_ansi(self) -> str:
        """Generate ANSI sequence to reset all formatting."""
        return self.RESET_ALL
    
    def generate_state_ansi(self, state: _FormattingState) -> str:
        """
        Generate complete ANSI sequence to achieve a formatting state from scratch.
        
        Args:
            state (FormattingState): Target formatting state
            
        Returns:
            str: Complete ANSI sequence to achieve the state
            
        Used when starting a new message or after a complete reset.
        """
        ansi_parts = []

        # Apply text formatting
        for fmt_name in ['bold', 'italic', 'underline', 'strikethrough']:
            if getattr(state, fmt_name):
                ansi_parts.append(self.TEXT_FORMATTING[fmt_name][0])
        
        # Apply text color
        if state.text_color:
            color_ansi = self._get_color_ansi(state.text_color)
            if color_ansi:
                ansi_parts.append(color_ansi)
        
        # Apply background color
        if state.background_color:
            bg_ansi = self._get_background_ansi(state.background_color)
            if bg_ansi:
                ansi_parts.append(bg_ansi)
        
        return ''.join(ansi_parts)
    
    def _get_color_ansi(self, color: str) -> str:
        """Get ANSI code for text color with caching."""
        color = color.strip()
        
        # Named color
        if color in self.NAMED_COLORS:
            return self.NAMED_COLORS[color]
        
        # Hex color
        if color.startswith('#'):
            with self._cache_lock:
                if color in self._hex_color_cache:
                    return self._hex_color_cache[color]
            
            try:
                if len(color) == 4:  # #RGB
                    r = int(color[1] * 2, 16)
                    g = int(color[2] * 2, 16)
                    b = int(color[3] * 2, 16)
                elif len(color) == 7:  # #RRGGBB
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                else:
                    raise ValueError("Invalid hex format")
                
                ansi_code = f'\033[38;2;{r};{g};{b}m'
                with self._cache_lock:
                    self._hex_color_cache[color] = ansi_code
                return ansi_code
            
            except ValueError:
                warnings.warn(f"Invalid hex color: {color}", UserWarning)
                return ""
        
        # RGB color
        if color.startswith('rgb(') and color.endswith(')'):
            try:
                rgb_content = color[4:-1]
                r, g, b = map(int, [x.strip() for x in rgb_content.split(',')])
                
                if not all(0 <= val <= 255 for val in [r, g, b]):
                    raise ValueError("RGB values must be 0-255")
                
                rgb_tuple = (r, g, b)
                with self._cache_lock:
                    if rgb_tuple in self._rgb_color_cache:
                        return self._rgb_color_cache[rgb_tuple]
                
                ansi_code = f'\033[38;2;{r};{g};{b}m'
                with self._cache_lock:
                    self._rgb_color_cache[rgb_tuple] = ansi_code
                return ansi_code
                
            except (ValueError, IndexError):
                warnings.warn(f"Invalid RGB color: {color}", UserWarning)
                return ""
        
        warnings.warn(f"Unknown color: {color}", UserWarning)
        return ""
    
    def _get_background_ansi(self, color: str) -> str:
        """Get ANSI code for background color with caching."""
        color = color.strip()
        
        # Named background color
        if color in self.NAMED_BG_COLORS:
            return self.NAMED_BG_COLORS[color]
        
        # Hex background color
        if color.startswith('#'):
            with self._cache_lock:
                if color in self._hex_bg_cache:
                    return self._hex_bg_cache[color]
            
            try:
                if len(color) == 4:  # #RGB
                    r = int(color[1] * 2, 16)
                    g = int(color[2] * 2, 16)
                    b = int(color[3] * 2, 16)
                elif len(color) == 7:  # #RRGGBB
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                else:
                    raise ValueError("Invalid hex format")
                
                ansi_code = f'\033[48;2;{r};{g};{b}m'
                with self._cache_lock:
                    self._hex_bg_cache[color] = ansi_code
                return ansi_code
                
            except ValueError:
                warnings.warn(f"Invalid hex background color: {color}", UserWarning)
                return ""
            
        # RGB background color
        if color.startswith('rgb(') and color.endswith(')'):
            try:
                rgb_content = color[4:-1]
                r, g, b = map(int, [x.strip() for x in rgb_content.split(',')])
                
                if not all(0 <= val <= 255 for val in [r, g, b]):
                    raise ValueError("RGB values must be 0-255")
                
                rgb_tuple = (r, g, b)
                with self._cache_lock:
                    if rgb_tuple in self._rgb_bg_cache:
                        return self._rgb_bg_cache[rgb_tuple]
                
                ansi_code = f'\033[48;2;{r};{g};{b}m'
                with self._cache_lock:
                    self._rgb_bg_cache[rgb_tuple] = ansi_code
                return ansi_code
                
            except (ValueError, IndexError):
                warnings.warn(f"Invalid RGB background color: {color}", UserWarning)
                return ""
        
        warnings.warn(f"Unknown background color: {color}", UserWarning)
        return ""
    
    def clear_caches(self) -> None:
        """Clear all caches (useful for testing or memory management)."""
        with self._cache_lock:
            self._hex_color_cache.clear()
            self._rgb_color_cache.clear()
            self._hex_bg_cache.clear()
            self._rgb_bg_cache.clear()
            self._transition_cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for performance monitoring."""
        with self._cache_lock:
            return {
                'hex_color_cache_size': len(self._hex_color_cache),
                'rgb_color_cache_size': len(self._rgb_color_cache),
                'hex_bg_cache_size': len(self._hex_bg_cache),
                'rgb_bg_cache_size': len(self._rgb_bg_cache),
                'transition_cache_size': len(self._transition_cache),
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses,
                'cache_hit_rate': self._cache_hits / max(self._cache_hits + self._cache_misses, 1)
            }
        
class _CommandProcessor:
    """
    Stateless command processor utility for fdl formatting system.
    
    Provides pure functions to process individual commands and convert them
    to ANSI escape sequences. State management is handled by the reconstructor.
    
    This is a utility class - create one instance and reuse it for all processing.
    """

    def __init__(self):
        """Initialize the command processor with ANSI converter."""
        self.converter = _ANSIConverter()
    
    def process_command(self, command: str, current_state: _FormattingState, 
                       default_state: Optional[_FormattingState] = None) -> Tuple[_FormattingState, str]:
        """
        Process a single formatting command.
        
        Args:
            command (str): Command to process (e.g., "bold", "red", "end bold")
            current_state (_FormattingState): Current formatting state
            default_state (Optional[_FormattingState]): Default state for end commands
            
        Returns:
            Tuple[_FormattingState, str]: (new_state, ansi_sequence)
            
        Raises:
            InvalidCommandError: If command syntax is invalid
            UnsupportedCommandError: If command is not supported
            
        This is a pure function - it doesn't modify the input state, returns new state.
        Note: Object-specific commands (12hr, tz, time ago) don't affect formatting state.
        """

        command = command.strip()
        if not command:
            return current_state.copy(), ""
        
        # Check if this is an object-specific command
        if self._is_object_specific_command(command):
            # Object commands don't affect formatting state, return unchanged
            return current_state.copy(), ""
        
        # Create new state as copy of current
        new_state = current_state.copy()
        
        # Apply command to new state
        self._apply_command_to_state(command, new_state, default_state)
        
        # Generate transition ANSI
        ansi_sequence = self.converter.generate_transition_ansi(current_state, new_state)
        
        return new_state, ansi_sequence
    
    def process_commands(self, commands: List[str], current_state: _FormattingState,
                        default_state: Optional[_FormattingState] = None) -> Tuple[_FormattingState, str]:
        """
        Process multiple commands efficiently in batch.
        
        Args:
            commands (List[str]): List of commands to process
            current_state (_FormattingState): Current formatting state
            default_state (Optional[_FormattingState]): Default state for end commands
            
        Returns:
            Tuple[_FormattingState, str]: (new_state, ansi_sequence)
            
        More efficient than calling process_command multiple times as it
        generates a single transition for all changes.
        Object-specific commands are ignored for formatting state.
        """
        if not commands:
            return current_state.copy(), ""
        
        # Create new state as copy of current
        new_state = current_state.copy()
        
        # Apply only formatting commands to new state
        for command in commands:
            command = command.strip()
            if command and not self._is_object_specific_command(command):
                self._apply_command_to_state(command, new_state, default_state)
        
        # Generate single transition for all changes
        ansi_sequence = self.converter.generate_transition_ansi(current_state, new_state)
        
        return new_state, ansi_sequence
    
    def _apply_command_to_state(self, command: str, state: _FormattingState, 
                               default_state: Optional[_FormattingState] = None) -> None:
        """
        Apply a single command to a formatting state.
        
        Args:
            command (str): Command to apply
            state (_FormattingState): State to modify in-place
            default_state (Optional[_FormattingState]): Default state for end commands
            
        Raises:
            InvalidCommandError: If command syntax is invalid
            UnsupportedCommandError: If command is not supported
        """
        command = command.strip()

        # Handle special reset commands first (before end command processing)
        if command in ['end all', 'reset']:
            state.reset()
            return

        if command.startswith('end '):
            self._apply_end_command(command[4:].strip(), state, default_state)
            return
        
        # Handle text formatting commands
        if command in ['bold', 'italic', 'underline', 'strikethrough']:
            setattr(state, command, True)
            return
        
        # Handle named colors
        if command in self.converter.NAMED_COLORS:
            state.text_color = command
            return
        
        # Handle hex colors
        if command.startswith('#') and len(command) in [4, 7]:
            state.text_color = command
            return
        
        # Handle RGB colors
        if command.startswith('rgb(') and command.endswith(')'):
            state.text_color = command
            return
        
        # Handle background colors
        if command.startswith('bkg '):
            bg_color = command[4:].strip()
            state.background_color = bg_color
            return
        
        # Add after the background color handling:
        if command.startswith('justify '):
            justify_type = command[8:].strip()
            if justify_type in ['left', 'right', 'center']:
                state.justify = justify_type
                return
        
        # Handle format references - IMPLEMENTED!
        if command.startswith('fmt '):
            format_name = command[4:].strip()
            try:
                self._apply_format_to_state(format_name, state)
            except Exception as e:
                raise UnsupportedCommandError(f"Failed to apply format '{format_name}': {e}")
            return
        
        # Check if this is an object-specific command that got through
        if self._is_object_specific_command(command):
            # This shouldn't happen if process_command filtered correctly
            warnings.warn(f"Object-specific command '{command}' in formatting context", UserWarning)
            return
        
        # Unknown command
        raise UnsupportedCommandError(f"Unknown command: {command}")
    
    def _apply_format_to_state(self, format_name: str, state: _FormattingState) -> None:
        """
        Apply a named format to a formatting state.
        
        Args:
            format_name (str): Name of format to apply
            state (_FormattingState): State to modify in-place
            
        This implements format application directly in the command processor
        to avoid circular imports. Uses late import to access the format registry.
        """
        try:
            # Use different import approaches for different contexts
            registry = None
            try:
                # Try relative import first
                from .format_class import _get_format_registry
                registry = _get_format_registry()
            except ImportError:
                try:
                    # Try absolute import for testing
                    from format_class import _get_format_registry
                    registry = _get_format_registry()
                except ImportError:
                    # If we can't import, warn and skip
                    warnings.warn(f"Format system not available, ignoring format '{format_name}'", UserWarning)
                    return
            
            if registry is None:
                warnings.warn(f"Format registry not available, ignoring format '{format_name}'", UserWarning)
                return
            
            compiled = registry._get(format_name)
            
            if not compiled:
                raise Exception(f"Format '{format_name}' not found in registry")
            
            # Apply the format's state to current state (override conflicts)
            format_state = compiled.formatting_state
            
            # DEBUG: Print what we're applying (can remove in production)
            # print(f"DEBUG: Applying format '{format_name}':")
            # print(f"  Format state: bold={format_state.bold}, color={format_state.text_color}, italic={format_state.italic}")
            # print(f"  Before: bold={state.bold}, color={state.text_color}, italic={state.italic}")
            
            # Apply all properties from the format state
            # Color properties: only apply if format has them set
            if format_state.text_color is not None:
                state.text_color = format_state.text_color
            if format_state.background_color is not None:
                state.background_color = format_state.background_color
            
            # Boolean properties: apply if format has them as True
            # (This preserves existing True values and adds new ones)
            if format_state.bold:
                state.bold = True
            if format_state.italic:
                state.italic = True
            if format_state.underline:
                state.underline = True
            if format_state.strikethrough:
                state.strikethrough = True
            
            # Copy active formats
            state.active_formats.update(format_state.active_formats)
            state.active_formats.add(format_name)
            
            # DEBUG: Print result (can remove in production)
            # print(f"  After: bold={state.bold}, color={state.text_color}, italic={state.italic}")
            
        except Exception as e:
            raise Exception(f"Failed to apply format '{format_name}': {e}")
    
    def _is_object_specific_command(self, command: str) -> bool:
        """
        Check if a command is object-specific (not formatting).
        
        Args:
            command (str): Command to check
            
        Returns:
            bool: True if command is object-specific, False if formatting command
        """
        command = command.strip()
        
        # Object-specific commands
        object_commands = [
            '12hr',           # 12-hour format
            'time ago',       # Add "ago" suffix
            'time until',     # Add "until" suffix  
            'no sec',         # Remove seconds
            'no min',         # Remove minutes
            'no hr',          # Remove hours
            'round sec',      # Round to nearest second
            'smart units 1',  # Smart formatting
            'smart units 2',  # Smart formatting
            'spinner dots',
            'spinner arrows',
            'spinner letters',
            'spinner dqpb'
        ]
        
        # Check exact matches
        if command in object_commands:
            return True
        
        # Check timezone commands: "tz pst", "tz utc", etc.
        if command.startswith('tz ') and len(command) > 3:
            return True
        
        return False
    
    def get_object_commands(self, commands: List[str]) -> List[str]:
        """
        Filter and return only object-specific commands from a command list.
        
        Args:
            commands (List[str]): List of commands to filter
            
        Returns:
            List[str]: Only the object-specific commands
        """
        return [cmd for cmd in commands if self._is_object_specific_command(cmd.strip())]
    
    def get_formatting_commands(self, commands: List[str]) -> List[str]:
        """
        Filter and return only formatting commands from a command list.
        
        Args:
            commands (List[str]): List of commands to filter
            
        Returns:
            List[str]: Only the formatting commands
        """
        return [cmd for cmd in commands if not self._is_object_specific_command(cmd.strip())]
    
    def _apply_end_command(self, end_target: str, state: _FormattingState,
                          default_state: Optional[_FormattingState] = None) -> None:
        """
        Apply an end/reset command to a formatting state.
        
        Args:
            end_target (str): What to end (e.g., "bold", "red")
            state (_FormattingState): State to modify
            default_state (Optional[_FormattingState]): Default state to revert to
        """
        end_target = end_target.strip()
        
        # Handle text formatting end commands
        if end_target in ['bold', 'italic', 'underline', 'strikethrough']:
            setattr(state, end_target, False)
            return
        
        # Handle color end commands (reset to default or None)
        if (end_target in self.converter.NAMED_COLORS or 
            end_target.startswith('#') or
            end_target.startswith('rgb(')):
            if default_state:
                state.text_color = default_state.text_color
            else:
                state.text_color = None
            return
        
        # Handle background end commands
        if end_target.startswith('bkg'):
            if default_state:
                state.background_color = default_state.background_color
            else:
                state.background_color = None
            return
        
        # Handle format reference end commands
        if end_target.startswith('fmt '):
            format_name = end_target[4:].strip()
            if format_name in state.active_formats:
                self._remove_format_from_state(format_name, state, default_state)
            return
        
        # Handle ending named formats directly - IMPLEMENTED!
        if end_target in state.active_formats:
            self._remove_format_from_state(end_target, state, default_state)
            return
        
        # Unknown end target
        raise UnsupportedCommandError(f"Unknown end target: {end_target}")
    
    def _remove_format_from_state(self, format_name: str, state: _FormattingState, 
                                 default_state: Optional[_FormattingState] = None) -> None:
        """
        Remove a format's effects from the current state using recomputation.
        
        Args:
            format_name (str): Name of format to remove
            state (_FormattingState): State to modify
            default_state (Optional[_FormattingState]): Default state
            
        Strategy: Recompute the state from scratch by applying all remaining formats.
        This ensures correctness without complex property tracking.
        """
        # Remove the format from active formats first
        state.active_formats.discard(format_name)
        
        # Store current non-format properties (directly set properties)
        # These are properties that weren't set by formats
        remaining_formats = state.active_formats.copy()
        
        # Store any directly-set properties by checking what would remain 
        # if we only had the remaining formats
        temp_state = _FormattingState()
        temp_state.active_formats = remaining_formats.copy()
        
        # Apply default state if provided
        if default_state:
            temp_state.text_color = default_state.text_color
            temp_state.background_color = default_state.background_color
            temp_state.bold = default_state.bold
            temp_state.italic = default_state.italic
            temp_state.underline = default_state.underline
            temp_state.strikethrough = default_state.strikethrough
        
        # Reapply all remaining formats to get the correct final state
        for remaining_format in remaining_formats:
            try:
                self._apply_format_to_state_direct(remaining_format, temp_state)
            except Exception as e:
                warnings.warn(f"Failed to reapply format '{remaining_format}' during removal: {e}")
        
        # Update the original state with the recomputed state
        state.text_color = temp_state.text_color
        state.background_color = temp_state.background_color
        state.bold = temp_state.bold
        state.italic = temp_state.italic
        state.underline = temp_state.underline
        state.strikethrough = temp_state.strikethrough
        state.active_formats = temp_state.active_formats
    
    def _apply_format_to_state_direct(self, format_name: str, state: _FormattingState) -> None:
        """
        Apply a format directly to a state without error handling wrapper.
        
        Used internally by _remove_format_from_state for recomputation.
        """
        try:
            # Use different import approaches for different contexts
            registry = None
            try:
                # Try relative import first
                from .format_class import _get_format_registry
                registry = _get_format_registry()
            except ImportError:
                try:
                    # Try absolute import for testing
                    from format_class import _get_format_registry
                    registry = _get_format_registry()
                except ImportError:
                    # If we can't import, skip silently (used in recomputation)
                    return
            
            if registry is None:
                return
            
            compiled = registry._get(format_name)
            if not compiled:
                return  # Format not found, skip silently during recomputation
            
            # Apply the format's state to current state
            format_state = compiled.formatting_state
            
            # Apply all properties from the format state
            if format_state.text_color is not None:
                state.text_color = format_state.text_color
            if format_state.background_color is not None:
                state.background_color = format_state.background_color
            
            # Boolean properties: apply if format has them as True
            if format_state.bold:
                state.bold = True
            if format_state.italic:
                state.italic = True
            if format_state.underline:
                state.underline = True
            if format_state.strikethrough:
                state.strikethrough = True
            
            # Copy active formats
            state.active_formats.update(format_state.active_formats)
            state.active_formats.add(format_name)
            
        except Exception:
            # Silent failure during recomputation - don't break the process
            pass
    
    def create_default_state(self, **kwargs) -> _FormattingState:
        """
        Create a default formatting state with specified properties.
        
        Args:
            **kwargs: Formatting properties (text_color, bold, etc.)
            
        Returns:
            _FormattingState: New default state
            
        Example:
            default = processor.create_default_state(text_color="blue", bold=True)
        """
        state = _FormattingState()
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                raise ValueError(f"Unknown formatting property: {key}")
        return state
    
    def generate_reset_ansi(self) -> str:
        """Generate ANSI sequence to reset all formatting."""
        return self.converter.generate_reset_ansi()
    
    def generate_state_ansi(self, state: _FormattingState) -> str:
        """Generate ANSI sequence to achieve a formatting state from scratch."""
        return self.converter.generate_state_ansi(state)
    
    def get_performance_stats(self) -> Dict[str, Union[int, float]]:
        """Get performance statistics for monitoring."""
        return self.converter.get_cache_stats()
    
    def clear_caches(self) -> None:
        """Clear all caches (useful for testing)."""
        self.converter.clear_caches()

# Global command processor instance for the fdl system
_global_processor: Optional[_CommandProcessor] = None


def _get_command_processor() -> _CommandProcessor:
    """
    Get the global command processor instance.
    
    Returns:
        _CommandProcessor: Global processor instance
        
    Creates the processor on first call, returns cached instance afterward.
    """
    global _global_processor
    if _global_processor is None:
        _global_processor = _CommandProcessor()
    return _global_processor