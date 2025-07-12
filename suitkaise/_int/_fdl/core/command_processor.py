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
        active_formats (Set[str]): Set of active named formats
    """
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
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
        self.active_formats.clear()

    def apply_defaults_from(self, default_state: '_FormattingState') -> None:
        """Apply default state values to this state."""
        self.text_color = default_state.text_color
        self.background_color = default_state.background_color
        self.bold = default_state.bold
        self.italic = default_state.italic
        self.underline = default_state.underline
        self.strikethrough = default_state.strikethrough
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
        
        # Handle format references (placeholder for future implementation)
        if command.startswith('fmt '):
            format_name = command[4:].strip()
            # TODO: This will be implemented when Format class is integrated
            state.active_formats.add(format_name)
            return
        
        # Check if this is an object-specific command that got through
        if self._is_object_specific_command(command):
            # This shouldn't happen if process_command filtered correctly
            warnings.warn(f"Object-specific command '{command}' in formatting context", UserWarning)
            return
        
        # Unknown command
        raise UnsupportedCommandError(f"Unknown command: {command}")
    
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
            state.active_formats.discard(format_name)
            return
        
        # Unknown end target
        raise UnsupportedCommandError(f"Unknown end target: {end_target}")
    
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


# Test script for Command Processor - comprehensive validation
if __name__ == "__main__":
    def test_command_processor():
        """Comprehensive test suite for the command processor."""
        
        print("=" * 60)
        print("COMMAND PROCESSOR TEST SUITE")
        print("=" * 60)
        
        processor = _CommandProcessor()
        test_count = 0
        passed_count = 0
        
        def run_test(name: str, test_func):
            """Run a single test case."""
            nonlocal test_count, passed_count
            test_count += 1
            
            print(f"\nTest {test_count}: {name}")
            
            try:
                passed = test_func(processor)
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
        
        # Test 1: Basic text formatting commands
        def test_basic_formatting(proc):
            initial_state = _FormattingState()
            
            # Test bold
            new_state, ansi = proc.process_command("bold", initial_state)
            if not new_state.bold or ansi != '\033[1m':
                print(f"❌ Bold failed: bold={new_state.bold}, ansi='{ansi}'")
                return False
            
            # Test italic
            new_state, ansi = proc.process_command("italic", new_state)
            if not new_state.italic or ansi != '\033[3m':
                print(f"❌ Italic failed: italic={new_state.italic}, ansi='{ansi}'")
                return False
            
            print("✓ Basic formatting commands work")
            return True
        
        # Test 2: Color commands
        def test_color_commands(proc):
            initial_state = _FormattingState()
            
            # Test named color
            new_state, ansi = proc.process_command("red", initial_state)
            if new_state.text_color != "red" or ansi != '\033[31m':
                print(f"❌ Red color failed: color={new_state.text_color}, ansi='{ansi}'")
                return False
            
            # Test hex color
            new_state, ansi = proc.process_command("#FF0000", initial_state)
            if new_state.text_color != "#FF0000" or not ansi.startswith('\033[38;2;255;0;0m'):
                print(f"❌ Hex color failed: color={new_state.text_color}, ansi='{ansi}'")
                return False
            
            # Test RGB color
            new_state, ansi = proc.process_command("rgb(0, 255, 0)", initial_state)
            if new_state.text_color != "rgb(0, 255, 0)" or not ansi.startswith('\033[38;2;0;255;0m'):
                print(f"❌ RGB color failed: color={new_state.text_color}, ansi='{ansi}'")
                return False
            
            print("✓ Color commands work")
            return True
        
        # Test 3: Background color commands
        def test_background_commands(proc):
            initial_state = _FormattingState()
            
            # Test named background
            new_state, ansi = proc.process_command("bkg blue", initial_state)
            if new_state.background_color != "blue" or ansi != '\033[44m':
                print(f"❌ Background failed: bg={new_state.background_color}, ansi='{ansi}'")
                return False
            
            # Test hex background
            new_state, ansi = proc.process_command("bkg #00FF00", initial_state)
            if new_state.background_color != "#00FF00" or not ansi.startswith('\033[48;2;0;255;0m'):
                print(f"❌ Hex background failed: bg={new_state.background_color}, ansi='{ansi}'")
                return False
            
            print("✓ Background commands work")
            return True
        
        # Test 4: End commands
        def test_end_commands(proc):
            # Set up initial state with formatting
            initial_state = _FormattingState()
            initial_state.bold = True
            initial_state.text_color = "red"
            
            # Test end bold
            new_state, ansi = proc.process_command("end bold", initial_state)
            if new_state.bold or ansi != '\033[22m':
                print(f"❌ End bold failed: bold={new_state.bold}, ansi='{ansi}'")
                return False
            
            # Test end color
            new_state, ansi = proc.process_command("end red", initial_state)
            if new_state.text_color is not None or ansi != '\033[39m':
                print(f"❌ End color failed: color={new_state.text_color}, ansi='{ansi}'")
                return False
            
            print("✓ End commands work")
            return True
        
        # Test 5: Reset commands
        def test_reset_commands(proc):
            # Set up state with all formatting
            initial_state = _FormattingState()
            initial_state.bold = True
            initial_state.italic = True
            initial_state.text_color = "red"
            initial_state.background_color = "blue"
            
            # Test reset command
            new_state, ansi = proc.process_command("reset", initial_state)
            # State should be cleared
            if (new_state.bold or new_state.italic or new_state.text_color or 
                new_state.background_color):
                print(f"❌ Reset failed: state not cleared properly")
                print(f"   bold={new_state.bold}, italic={new_state.italic}")
                print(f"   color={new_state.text_color}, bg={new_state.background_color}")
                return False
            
            # ANSI should show transition from formatted state to clear state
            # This will generate codes to turn off bold, italic, reset colors
            expected_ansi_parts = ['\033[22m', '\033[23m', '\033[39m', '\033[49m']
            if not all(part in ansi for part in expected_ansi_parts):
                print(f"❌ Reset ANSI incomplete: got '{ansi}'")
                print(f"   Expected parts: {expected_ansi_parts}")
                return False
            
            # Test end all command
            new_state, ansi = proc.process_command("end all", initial_state)
            # State should be cleared
            if (new_state.bold or new_state.italic or new_state.text_color or 
                new_state.background_color):
                print(f"❌ End all failed: state not cleared properly")
                return False
            
            # ANSI should be the same as reset
            if not all(part in ansi for part in expected_ansi_parts):
                print(f"❌ End all ANSI incomplete: got '{ansi}'")
                return False
            
            print("✓ Reset commands work")
            return True
        
        # Test 6: Object-specific commands (should be ignored)
        def test_object_commands(proc):
            initial_state = _FormattingState()
            initial_state.bold = True  # Should remain unchanged
            
            # Test 12hr command (object-specific)
            new_state, ansi = proc.process_command("12hr", initial_state)
            if not new_state.bold or ansi != '':
                print(f"❌ Object command not ignored: bold={new_state.bold}, ansi='{ansi}'")
                return False
            
            # Test timezone command (object-specific)
            new_state, ansi = proc.process_command("tz pst", initial_state)
            if not new_state.bold or ansi != '':
                print(f"❌ Timezone command not ignored: bold={new_state.bold}, ansi='{ansi}'")
                return False
            
            # Test time ago command (object-specific)
            new_state, ansi = proc.process_command("time ago", initial_state)
            if not new_state.bold or ansi != '':
                print(f"❌ Time ago command not ignored: bold={new_state.bold}, ansi='{ansi}'")
                return False
            
            print("✓ Object-specific commands properly ignored")
            return True
        
        # Test 7: Batch command processing
        def test_batch_processing(proc):
            initial_state = _FormattingState()
            
            # Test multiple formatting commands
            commands = ["bold", "red", "bkg blue"]
            new_state, ansi = proc.process_commands(commands, initial_state)
            
            if not new_state.bold or new_state.text_color != "red" or new_state.background_color != "blue":
                print(f"❌ Batch processing failed: bold={new_state.bold}, color={new_state.text_color}, bg={new_state.background_color}")
                return False
            
            # Should combine all ANSI codes
            expected_ansi = '\033[1m\033[31m\033[44m'
            if ansi != expected_ansi:
                print(f"❌ Batch ANSI failed: expected='{expected_ansi}', got='{ansi}'")
                return False
            
            print("✓ Batch processing works")
            return True
        
        # Test 8: Mixed formatting and object commands
        def test_mixed_commands(proc):
            initial_state = _FormattingState()
            
            # Mix formatting and object commands
            commands = ["bold", "12hr", "red", "time ago", "bkg blue"]
            new_state, ansi = proc.process_commands(commands, initial_state)
            
            # Only formatting commands should be applied
            if (not new_state.bold or new_state.text_color != "red" or 
                new_state.background_color != "blue"):
                print(f"❌ Mixed commands failed: formatting not applied correctly")
                return False
            
            # ANSI should only include formatting commands
            expected_ansi = '\033[1m\033[31m\033[44m'
            if ansi != expected_ansi:
                print(f"❌ Mixed ANSI failed: expected='{expected_ansi}', got='{ansi}'")
                return False
            
            print("✓ Mixed command filtering works")
            return True
        
        # Test 9: State transitions and caching
        def test_state_transitions(proc):
            state1 = _FormattingState()
            state1.bold = True
            
            state2 = _FormattingState()
            state2.bold = True
            state2.italic = True
            
            # Test transition from state1 to state2
            ansi = proc.converter.generate_transition_ansi(state1, state2)
            if ansi != '\033[3m':  # Should only add italic
                print(f"❌ State transition failed: expected='\\033[3m', got='{ansi}'")
                return False
            
            # Test caching - same transition should hit cache
            ansi2 = proc.converter.generate_transition_ansi(state1, state2)
            if ansi2 != ansi:
                print(f"❌ Caching failed: results differ")
                return False
            
            # Check cache stats
            stats = proc.get_performance_stats()
            if stats['cache_hits'] == 0:
                print(f"❌ Cache not working: no hits recorded")
                return False
            
            print("✓ State transitions and caching work")
            return True
        
        # Test 10: Helper methods
        def test_helper_methods(proc):
            commands = ["bold", "12hr", "red", "tz pst", "underline", "time ago"]
            
            # Test object command filtering
            obj_commands = proc.get_object_commands(commands)
            expected_obj = ["12hr", "tz pst", "time ago"]
            if obj_commands != expected_obj:
                print(f"❌ Object filtering failed: expected={expected_obj}, got={obj_commands}")
                return False
            
            # Test formatting command filtering
            fmt_commands = proc.get_formatting_commands(commands)
            expected_fmt = ["bold", "red", "underline"]
            if fmt_commands != expected_fmt:
                print(f"❌ Formatting filtering failed: expected={expected_fmt}, got={fmt_commands}")
                return False
            
            print("✓ Helper methods work")
            return True
        
        # Test 11: Default state handling
        def test_default_state(proc):
            # Create default state
            default_state = proc.create_default_state(text_color="blue", bold=True)
            
            if default_state.text_color != "blue" or not default_state.bold:
                print(f"❌ Default state creation failed")
                return False
            
            # Test end command with default state
            current_state = _FormattingState()
            current_state.text_color = "red"
            
            new_state, ansi = proc.process_command("end red", current_state, default_state)
            if new_state.text_color != "blue":  # Should revert to default
                print(f"❌ Default state revert failed: color={new_state.text_color}")
                return False
            
            print("✓ Default state handling works")
            return True
        
        # Test 12: Error handling
        def test_error_handling(proc):
            initial_state = _FormattingState()
            
            try:
                # Test unknown command
                proc.process_command("unknown_command", initial_state)
                print("❌ Should have raised UnsupportedCommandError")
                return False
            except UnsupportedCommandError:
                pass  # Expected
            
            try:
                # Test invalid property in default state
                proc.create_default_state(invalid_property="value")
                print("❌ Should have raised ValueError")
                return False
            except ValueError:
                pass  # Expected
            
            print("✓ Error handling works")
            return True
        
        # Run all tests
        run_test("Basic text formatting commands", test_basic_formatting)
        run_test("Color commands", test_color_commands)
        run_test("Background color commands", test_background_commands)
        run_test("End commands", test_end_commands)
        run_test("Reset commands", test_reset_commands)
        run_test("Object-specific commands (ignored)", test_object_commands)
        run_test("Batch command processing", test_batch_processing)
        run_test("Mixed formatting and object commands", test_mixed_commands)
        run_test("State transitions and caching", test_state_transitions)
        run_test("Helper methods", test_helper_methods)
        run_test("Default state handling", test_default_state)
        run_test("Error handling", test_error_handling)
        
        print("\n" + "=" * 60)
        print(f"TEST RESULTS: {passed_count}/{test_count} tests passed")
        if passed_count == test_count:
            print("🎉 ALL TESTS PASSED!")
            print("\n📊 PERFORMANCE STATS:")
            stats = processor.get_performance_stats()
            print(f"Cache hits: {stats['cache_hits']}")
            print(f"Cache misses: {stats['cache_misses']}")
            print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
            print(f"Transition cache size: {stats['transition_cache_size']}")
        else:
            print(f"❌ {test_count - passed_count} tests failed")
        print("=" * 60)
        
        return passed_count == test_count
    
    # Run the tests
    test_command_processor()