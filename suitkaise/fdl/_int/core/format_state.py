"""
Internal Format State for FDL processing with Progress Bar support.

This module contains the private state object that tracks all formatting,
layout, and processing state throughout FDL string processing, including
progress bar output queuing.

This is internal to the FDL engine and not exposed to users.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Set, Dict, Any, TYPE_CHECKING

# Import terminal detection
try:
    from ..setup.terminal import _terminal
except ImportError:
    # Fallback for testing/development
    class _MockTerminal:
        width = 60
    _terminal = _MockTerminal()

# Avoid circular imports
if TYPE_CHECKING:
    from ..processors.objects.progress_bars import _ProgressBar


@dataclass
class _FormatState:
    """
    Private central state object for FDL processing.
    
    Tracks all formatting, layout, time settings, box state, variables,
    output streams, and progress bar state throughout the processing pipeline.
    
    This class is internal and should never be exposed to end users.
    """
    
    # Text formatting
    text_color: Optional[str] = None
    background_color: Optional[str] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    
    # Time formatting settings
    twelve_hour_time: bool = False
    timezone: Optional[str] = None
    use_seconds: bool = True
    use_minutes: bool = True
    use_hours: bool = True
    decimal_places: int = 6
    round_seconds: bool = False
    smart_time: int = 0  # Smart time formatting (0 = no smart time)
    
    # Box state
    in_box: bool = False
    box_style: str = "square"
    box_title: Optional[str] = None
    box_color: Optional[str] = None
    box_background: Optional[str] = None
    box_content: List[str] = field(default_factory=list)
    box_width: int = 0
    
    # Layout settings
    justify: Optional[str] = None  # 'left', 'right', 'center'
    
    # Debug mode settings
    debug_mode: bool = False
    
    # Active format tracking
    active_formats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Variable handling
    values: Tuple = ()
    value_index: int = 0
    
    # Terminal information
    terminal_width: int = 60
    
    # Progress bar state
    bar_active: bool = False
    active_progress_bar: Optional['_ProgressBar'] = None
    
    # Output streams - all processed content goes here
    terminal_output: List[str] = field(default_factory=list)
    plain_output: List[str] = field(default_factory=list)
    markdown_output: List[str] = field(default_factory=list)
    html_output: List[str] = field(default_factory=list)
    
    # Queued output (used when progress bar is active)
    queued_terminal_output: List[str] = field(default_factory=list)
    queued_plain_output: List[str] = field(default_factory=list)
    queued_markdown_output: List[str] = field(default_factory=list)
    queued_html_output: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Initialize calculated values after object creation."""
        # Ensure minimum terminal width of 60
        self.terminal_width = max(60, self.terminal_width)
        
        # Calculate maximum box width
        self.box_width = self._calculate_max_box_width()
    
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
    
    def copy(self) -> '_FormatState':
        """Create a copy of the current state."""
        return _FormatState(
            # Text formatting
            text_color=self.text_color,
            background_color=self.background_color,
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            strikethrough=self.strikethrough,
            
            # Time settings
            twelve_hour_time=self.twelve_hour_time,
            timezone=self.timezone,
            use_seconds=self.use_seconds,
            use_minutes=self.use_minutes,
            use_hours=self.use_hours,
            decimal_places=self.decimal_places,
            round_seconds=self.round_seconds,
            smart_time=self.smart_time,
            
            # Box state
            in_box=self.in_box,
            box_style=self.box_style,
            box_title=self.box_title,
            box_color=self.box_color,
            box_background=self.box_background,
            box_content=self.box_content.copy(),
            
            # Layout
            justify=self.justify,
            
            # Variables
            values=self.values,
            value_index=self.value_index,
            debug_mode=self.debug_mode,
            
            # Terminal info
            terminal_width=self.terminal_width,
            
            # Progress bar state (don't copy active bar reference)
            bar_active=False,
            active_progress_bar=None,
            
            # Output streams start empty in copy
        )
    
    def start_progress_bar_mode(self, progress_bar: '_ProgressBar') -> None:
        """
        Start progress bar mode - queue all future output.
        
        Args:
            progress_bar: The active progress bar instance
        """
        self.bar_active = True
        self.active_progress_bar = progress_bar
        
        # Clear any existing queued output
        self.queued_terminal_output.clear()
        self.queued_plain_output.clear()
        self.queued_markdown_output.clear()
        self.queued_html_output.clear()
    
    def stop_progress_bar_mode(self, flush_output: bool = True) -> None:
        """
        Stop progress bar mode and optionally flush queued output.
        
        Args:
            flush_output: Whether to flush queued output to main streams
        """
        if flush_output:
            self.flush_queued_output()
        
        self.bar_active = False
        self.active_progress_bar = None
        
        # Clear queued output
        self.queued_terminal_output.clear()
        self.queued_plain_output.clear()
        self.queued_markdown_output.clear()
        self.queued_html_output.clear()
    
    def flush_queued_output(self) -> None:
        """Move all queued output to main output streams."""
        self.terminal_output.extend(self.queued_terminal_output)
        self.plain_output.extend(self.queued_plain_output)
        self.markdown_output.extend(self.queued_markdown_output)
        self.html_output.extend(self.queued_html_output)
    
    def add_to_output_streams(self, terminal: str = '', plain: str = '', 
                             markdown: str = '', html: str = '') -> None:
        """
        Add content to appropriate output streams (main or queued based on bar state).
        
        Args:
            terminal: Terminal output with ANSI codes
            plain: Plain text output
            markdown: Markdown formatted output  
            html: HTML formatted output
        """
        if self.bar_active:
            # Queue ALL output while progress bar is active
            if terminal:
                self.queued_terminal_output.append(terminal)
            if plain:
                self.queued_plain_output.append(plain)
            if markdown:
                self.queued_markdown_output.append(markdown)
            if html:
                self.queued_html_output.append(html)
        else:
            # Normal output to main streams
            if terminal:
                self.terminal_output.append(terminal)
            if plain:
                self.plain_output.append(plain)
            if markdown:
                self.markdown_output.append(markdown)
            if html:
                self.html_output.append(html)
    
    def reset_formatting(self):
        """Reset all text formatting to defaults."""
        self.text_color = None
        self.background_color = None
        self.bold = False
        self.italic = False
        self.underline = False
        self.strikethrough = False
    
    def reset_time_settings(self):
        """Reset all time formatting settings to defaults."""
        self.twelve_hour_time = False
        self.timezone = None
        self.use_seconds = True
        self.use_minutes = True
        self.use_hours = True
        self.decimal_places = 6
        self.round_seconds = False
        self.smart_time = 0  # No smart time formatting by default
    
    def reset_box_state(self):
        """Reset all box-related state."""
        self.in_box = False
        self.box_style = "square"
        self.box_title = None
        self.box_color = None
        self.box_background = None
        self.box_content.clear()

    def reset_debug_mode(self):
        """Reset debug mode state."""
        self.debug_mode = False

    def reset_all_formatting(self):
        """Reset all formatting to default values."""
        self.reset_formatting()
        self.reset_time_settings()
        self.reset_box_state()
        self.reset_debug_mode()

    def reset_output_streams(self):
        """Reset all output streams to empty."""
        self.terminal_output.clear()
        self.plain_output.clear()
        self.markdown_output.clear()
        self.html_output.clear()
        
        # Also reset queued output
        self.queued_terminal_output.clear()
        self.queued_plain_output.clear()
        self.queued_markdown_output.clear()
        self.queued_html_output.clear()

    def get_next_value(self):
        """
        Get the next value from the values tuple and increment index.
        
        Returns:
            Any: Next value from tuple
            
        Raises:
            IndexError: If no more values available
        """
        if self.value_index >= len(self.values):
            raise IndexError(f"No more values available (index {self.value_index})")
        
        value = self.values[self.value_index]
        self.value_index += 1
        return value
    
    def has_more_values(self) -> bool:
        """Check if there are more values available."""
        return self.value_index < len(self.values)
    
    def get_final_outputs(self) -> dict:
        """
        Get all output streams as final strings, including queued content.
        
        This ensures perfect synchronization - all formats contain exactly
        the same content in exactly the same order, regardless of progress bar state.
        
        Returns:
            dict: All output formats joined as strings (main + queued)
        """
        return {
            'terminal': ''.join(self.terminal_output + self.queued_terminal_output),
            'plain': ''.join(self.plain_output + self.queued_plain_output),
            'markdown': ''.join(self.markdown_output + self.queued_markdown_output),
            'html': ''.join(self.html_output + self.queued_html_output)
        }
    
    def get_immediate_outputs(self) -> dict:
        """
        Get output streams that are immediately available (not queued).
        
        This is used internally by the progress bar system to determine
        what content can be displayed immediately vs. what should wait.
        
        Returns:
            dict: Main output streams only (excludes queued content)
        """
        return {
            'terminal': ''.join(self.terminal_output),
            'plain': ''.join(self.plain_output),
            'markdown': ''.join(self.markdown_output),
            'html': ''.join(self.html_output)
        }


def _create_format_state(values: Tuple = (), terminal_width: Optional[int] = None) -> _FormatState:
    """
    Private factory function to create a _FormatState with proper initialization.
    
    Args:
        values: Tuple of values for variable substitution
        terminal_width: Override terminal width (uses detected width if None)
        
    Returns:
        _FormatState: Initialized format state object
    """
    if terminal_width is None:
        terminal_width = max(60, _terminal.width)
    
    return _FormatState(
        values=values,
        terminal_width=terminal_width
    )