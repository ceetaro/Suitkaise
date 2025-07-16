"""
Internal FDL print functions - Foundation for public API

These functions provide the core printing functionality used throughout
suitkaise modules. They combine the reconstructor and renderer to provide
complete fdl string processing with output destination control.

Architecture:
- _print() → Console output with formatting
- _print_plaintext() → Plain text files 
- _print_markdown() → Markdown files (planned)
- _print_html() → HTML files (planned)

These functions will be wrapped by the public API:
fdl.print() → _print()
fdl.plaintext() → _print_plaintext()
fdl.markdown() → _print_markdown()  
fdl.html() → _print_html()
"""

import warnings
from typing import Optional, Tuple, Union, TextIO
from pathlib import Path

# Import core components
from core.reconstructor import _reconstruct_fdl_string, _FormattingState
from core.renderer import (
    _render_to_console, _render_to_plaintext, 
    _render_to_markdown, _render_to_html
)

warnings.simplefilter("always")


class PrintError(Exception):
    """Raised when printing fails."""
    pass


def _print(format_string: str, values: Optional[Tuple] = None,
          default_state: Optional[_FormattingState] = None,
          force_color: Optional[bool] = None,
          add_newline: bool = True) -> None:
    """
    INTERNAL: Print formatted string to console.
    
    This is the core printing function used throughout suitkaise modules.
    Combines reconstructor and renderer for complete fdl processing.
    
    Args:
        format_string (str): FDL format string with commands/variables/objects
        values (Optional[Tuple]): Values for variable substitution
        default_state (Optional[_FormattingState]): Default formatting state
        force_color (Optional[bool]): Override terminal color detection
        add_newline (bool): Add newline after output
        
    Raises:
        PrintError: If reconstruction or rendering fails
        
    Example:
        _print("Status: </bold, green>OK</end bold, green>")
        _print("User <username> logged in at <time:>", ("alice",))
        _print("Error: </red>Failed", force_color=False)  # Force plain text
    """
    try:
        # Step 1: Reconstruct the fdl string
        formatted_string = _reconstruct_fdl_string(format_string, values, default_state)
        
        # Step 2: Add newline if requested
        if add_newline:
            formatted_string += '\n'
        
        # Step 3: Render to console
        _render_to_console(formatted_string, force_color)
        
    except Exception as e:
        raise PrintError(f"Failed to print to console: {e}")


def _print_plaintext(format_string: str, destination: Union[str, Path, TextIO],
                    values: Optional[Tuple] = None,
                    default_state: Optional[_FormattingState] = None,
                    add_newline: bool = True) -> None:
    """
    INTERNAL: Print formatted string to plain text file/stream.
    
    Processes fdl string and outputs clean text with all ANSI codes stripped.
    Perfect for log files, configuration files, and text processing.
    
    Args:
        format_string (str): FDL format string with commands/variables/objects
        destination: File path, Path object, or open text stream
        values (Optional[Tuple]): Values for variable substitution
        default_state (Optional[_FormattingState]): Default formatting state
        add_newline (bool): Add newline after output
        
    Raises:
        PrintError: If reconstruction or rendering fails
        
    Example:
        _print_plaintext("Error: </red>Critical failure", "error.log")
        _print_plaintext("Status: <status>", "status.txt", ("OK",))
        
        with open("output.txt", "w") as f:
            _print_plaintext("Data: <value>", f, (42,))
    """
    try:
        # Step 1: Reconstruct the fdl string
        formatted_string = _reconstruct_fdl_string(format_string, values, default_state)
        
        # Step 2: Add newline if requested
        if add_newline:
            formatted_string += '\n'
        
        # Step 3: Render to plain text
        _render_to_plaintext(formatted_string, destination)
        
    except Exception as e:
        raise PrintError(f"Failed to print to plain text: {e}")


def _print_markdown(format_string: str, destination: Union[str, Path, TextIO],
                   values: Optional[Tuple] = None,
                   default_state: Optional[_FormattingState] = None,
                   add_newline: bool = True) -> None:
    """
    INTERNAL: Print formatted string to markdown file/stream.
    
    Processes fdl string and converts formatting to markdown equivalents.
    Perfect for documentation, README files, and markdown-based systems.
    
    Args:
        format_string (str): FDL format string with commands/variables/objects
        destination: File path, Path object, or open text stream
        values (Optional[Tuple]): Values for variable substitution
        default_state (Optional[_FormattingState]): Default formatting state
        add_newline (bool): Add newline after output
        
    Raises:
        PrintError: If reconstruction or rendering fails
        
    PLANNED IMPLEMENTATION - Currently uses plain text fallback.
    
    Future conversion mapping:
    - </bold>text</end bold> → **text**
    - </italic>text</end italic> → *text*
    - </code>text</end code> → `text`
    
    Example:
        _print_markdown("# Status: </bold>OK", "README.md")
        _print_markdown("User: **<username>**", "users.md", ("alice",))
    """
    try:
        # Step 1: Reconstruct the fdl string
        formatted_string = _reconstruct_fdl_string(format_string, values, default_state)
        
        # Step 2: Add newline if requested
        if add_newline:
            formatted_string += '\n'
        
        # Step 3: Render to markdown (currently falls back to plain text)
        _render_to_markdown(formatted_string, destination)
        
    except Exception as e:
        raise PrintError(f"Failed to print to markdown: {e}")


def _print_html(format_string: str, destination: Union[str, Path, TextIO],
               values: Optional[Tuple] = None,
               default_state: Optional[_FormattingState] = None,
               add_newline: bool = True,
               css_classes: bool = False,
               standalone: bool = True) -> None:
    """
    INTERNAL: Print formatted string to HTML file/stream.
    
    Processes fdl string and converts formatting to HTML/CSS equivalents.
    Perfect for web dashboards, reports, and HTML-based documentation.
    
    Args:
        format_string (str): FDL format string with commands/variables/objects
        destination: File path, Path object, or open text stream
        values (Optional[Tuple]): Values for variable substitution
        default_state (Optional[_FormattingState]): Default formatting state
        add_newline (bool): Add newline after output
        css_classes (bool): Use CSS classes instead of inline styles
        standalone (bool): Generate complete HTML document with headers
        
    Raises:
        PrintError: If reconstruction or rendering fails
        
    PLANNED IMPLEMENTATION - Currently uses plain text fallback.
    
    Future conversion mapping:
    - </bold>text</end bold> → <strong>text</strong>
    - </italic>text</end italic> → <em>text</em>
    - </red>text</end red> → <span style="color: red">text</span>
    - </bkg blue>text</end bkg blue> → <span style="background-color: blue">text</span>
    
    Example:
        _print_html("Status: </green>OK", "status.html")
        _print_html("Error: </red, bold>Failed", "error.html", css_classes=True)
    """
    try:
        # Step 1: Reconstruct the fdl string
        formatted_string = _reconstruct_fdl_string(format_string, values, default_state)
        
        # Step 2: Add newline if requested (converts to <br> in HTML)
        if add_newline:
            formatted_string += '\n'
        
        # Step 3: Render to HTML (currently falls back to plain text)
        _render_to_html(formatted_string, destination, css_classes, standalone)
        
    except Exception as e:
        raise PrintError(f"Failed to print to HTML: {e}")


# Convenience functions for common use cases
def _print_error(message: str, values: Optional[Tuple] = None,
                destination: Optional[Union[str, Path, TextIO]] = None) -> None:
    """
    INTERNAL: Print error message with standard error formatting.
    
    Args:
        message (str): Error message (can include fdl formatting)
        values (Optional[Tuple]): Values for variable substitution
        destination: If provided, also write to file as plain text
        
    Example:
        _print_error("Failed to load <filename>", ("config.json",))
        _print_error("Critical error", destination="error.log")
    """
    error_format = "</bold, red>Error:</end bold, red> " + message
    
    # Always print to console
    _print(error_format, values)
    
    # Also write to file if requested
    if destination:
        _print_plaintext(f"Error: {message}", destination, values)


def _print_success(message: str, values: Optional[Tuple] = None,
                  destination: Optional[Union[str, Path, TextIO]] = None) -> None:
    """
    INTERNAL: Print success message with standard success formatting.
    
    Args:
        message (str): Success message (can include fdl formatting)
        values (Optional[Tuple]): Values for variable substitution
        destination: If provided, also write to file as plain text
        
    Example:
        _print_success("Loaded <count> items", (42,))
        _print_success("Startup complete", destination="startup.log")
    """
    success_format = "</bold, green>Success:</end bold, green> " + message
    
    # Always print to console
    _print(success_format, values)
    
    # Also write to file if requested
    if destination:
        _print_plaintext(f"Success: {message}", destination, values)


def _print_warning(message: str, values: Optional[Tuple] = None,
                  destination: Optional[Union[str, Path, TextIO]] = None) -> None:
    """
    INTERNAL: Print warning message with standard warning formatting.
    
    Args:
        message (str): Warning message (can include fdl formatting)
        values (Optional[Tuple]): Values for variable substitution
        destination: If provided, also write to file as plain text
        
    Example:
        _print_warning("Config file <filename> not found, using defaults", ("app.conf",))
        _print_warning("Performance issue detected", destination="warnings.log")
    """
    warning_format = "</bold, yellow>Warning:</end bold, yellow> " + message
    
    # Always print to console
    _print(warning_format, values)
    
    # Also write to file if requested
    if destination:
        _print_plaintext(f"Warning: {message}", destination, values)