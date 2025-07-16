# final rendering for output to console/file

"""
FDL Renderer - Final output processing and destination handling

This module provides the final rendering stage for fdl formatted strings.
Takes ANSI-formatted strings from the reconstructor and outputs them to various
destinations with appropriate format conversion.

Current support:
- Console output (direct ANSI passthrough)
- Plain text files (ANSI stripped)

Planned support:
- Markdown files (ANSI → markdown formatting)
- HTML files (ANSI → HTML/CSS)

Architecture designed for easy expansion without breaking existing code.
"""

import re
import sys
import warnings
from typing import Optional, Union, TextIO
from pathlib import Path

# Import terminal detection for capability checking
try:
    from setup.terminal import _terminal
except ImportError:
    try:
        from setup.terminal import _terminal
    except ImportError:
        # Fallback if terminal detection not available
        class _FallbackTerminal:
            supports_color = True
            is_tty = True
        _terminal = _FallbackTerminal()

warnings.simplefilter("always")


class RendererError(Exception):
    """Raised when rendering fails."""
    pass


class _FDLRenderer:
    """
    Core renderer for FDL formatted strings.
    
    Handles output to multiple destinations with format conversion:
    - Console: Direct ANSI output with capability detection
    - Plain text: ANSI codes stripped for clean file output
    - Markdown: ANSI → Markdown conversion (planned)
    - HTML: ANSI → HTML/CSS conversion (planned)
    
    Thread-safe design for concurrent usage.
    """
    
    def __init__(self):
        """Initialize renderer with capability detection."""
        self._ansi_regex = re.compile(r'\033\[[0-9;]*m')
        self._supports_color = _terminal.supports_color
        self._is_tty = _terminal.is_tty
    
    def render_to_console(self, formatted_string: str, 
                         force_color: Optional[bool] = None) -> None:
        """
        Render formatted string to console with capability detection.
        
        Args:
            formatted_string (str): ANSI-formatted string from reconstructor
            force_color (Optional[bool]): Override color detection if provided
            
        Automatically strips ANSI codes if terminal doesn't support color
        or if output is being piped/redirected.
        """
        # Determine if we should use color
        use_color = force_color if force_color is not None else (
            self._supports_color and self._is_tty
        )
        
        if use_color:
            # Output with ANSI codes
            print(formatted_string, end='')
        else:
            # Strip ANSI codes for plain output
            clean_string = self._strip_ansi(formatted_string)
            print(clean_string, end='')
    
    def render_to_plaintext(self, formatted_string: str, 
                           destination: Union[str, Path, TextIO]) -> None:
        """
        Render formatted string to plain text file or stream.
        
        Args:
            formatted_string (str): ANSI-formatted string from reconstructor
            destination: File path, Path object, or open text stream
            
        Strips all ANSI codes for clean text output suitable for:
        - Log files
        - Configuration files  
        - Text processing pipelines
        - Non-terminal environments
        """
        clean_string = self._strip_ansi(formatted_string)
        
        if isinstance(destination, (str, Path)):
            # Write to file path
            path = Path(destination)
            try:
                # Create parent directories if needed
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('a', encoding='utf-8') as f:
                    f.write(clean_string)
            except Exception as e:
                raise RendererError(f"Failed to write to file '{path}': {e}")
        else:
            # Write to stream (file object)
            try:
                destination.write(clean_string)
                destination.flush()
            except Exception as e:
                raise RendererError(f"Failed to write to stream: {e}")
    
    def render_to_markdown(self, formatted_string: str,
                          destination: Union[str, Path, TextIO]) -> None:
        """
        Render formatted string to Markdown format.
        
        Args:
            formatted_string (str): ANSI-formatted string from reconstructor
            destination: File path, Path object, or open text stream
            
        Converts ANSI formatting to Markdown equivalents:
        - Bold: **text**
        - Italic: *text*
        - Colors: Markdown doesn't support colors, so stripped
        - Code-like formatting: `text` (for monospace effects)
        
        PLANNED IMPLEMENTATION - Currently falls back to plain text.
        """
        warnings.warn("Markdown rendering not yet implemented, using plain text", UserWarning)
        
        # TODO: Implement ANSI → Markdown conversion
        # For now, fall back to plain text
        self.render_to_plaintext(formatted_string, destination)
    
    def render_to_html(self, formatted_string: str,
                      destination: Union[str, Path, TextIO],
                      css_classes: bool = False,
                      standalone: bool = True) -> None:
        """
        Render formatted string to HTML format.
        
        Args:
            formatted_string (str): ANSI-formatted string from reconstructor
            destination: File path, Path object, or open text stream
            css_classes (bool): Use CSS classes instead of inline styles
            standalone (bool): Generate complete HTML document
            
        Converts ANSI formatting to HTML equivalents:
        - Bold: <strong> or <span class="bold">
        - Italic: <em> or <span class="italic">
        - Colors: style="color: red" or class="color-red"
        - Background: style="background-color: blue" or class="bg-blue"
        
        PLANNED IMPLEMENTATION - Currently falls back to plain text.
        """
        warnings.warn("HTML rendering not yet implemented, using plain text", UserWarning)
        
        # TODO: Implement ANSI → HTML conversion
        # For now, fall back to plain text
        self.render_to_plaintext(formatted_string, destination)
    
    def _strip_ansi(self, text: str) -> str:
        """
        Strip all ANSI escape sequences from text.
        
        Args:
            text (str): Text containing ANSI codes
            
        Returns:
            str: Clean text with all ANSI codes removed
            
        Removes all ANSI escape sequences including:
        - Color codes (\033[31m, \033[38;2;255;0;0m)
        - Format codes (\033[1m, \033[3m)
        - Reset codes (\033[0m)
        - Cursor positioning (\033[H, \033[2J) - if any slip through
        """
        return self._ansi_regex.sub('', text)
    
    def get_capabilities(self) -> dict:
        """
        Get renderer capabilities for debugging/optimization.
        
        Returns:
            dict: Capability information
        """
        return {
            'supports_color': self._supports_color,
            'is_tty': self._is_tty,
            'formats_available': ['console', 'plaintext'],
            'formats_planned': ['markdown', 'html'],
            'ansi_regex_pattern': self._ansi_regex.pattern
        }


# Global renderer instance
_global_renderer: Optional[_FDLRenderer] = None


def _get_renderer() -> _FDLRenderer:
    """
    Get the global renderer instance.
    
    Returns:
        _FDLRenderer: Global renderer instance
        
    Creates the renderer on first call, returns cached instance afterward.
    Thread-safe singleton pattern.
    """
    global _global_renderer
    if _global_renderer is None:
        _global_renderer = _FDLRenderer()
    return _global_renderer


# Internal rendering functions for use by _print() functions
def _render_to_console(formatted_string: str, force_color: Optional[bool] = None) -> None:
    """INTERNAL: Render to console with capability detection."""
    _get_renderer().render_to_console(formatted_string, force_color)


def _render_to_plaintext(formatted_string: str, destination: Union[str, Path, TextIO]) -> None:
    """INTERNAL: Render to plain text file or stream."""
    _get_renderer().render_to_plaintext(formatted_string, destination)


def _render_to_markdown(formatted_string: str, destination: Union[str, Path, TextIO]) -> None:
    """INTERNAL: Render to markdown (planned implementation)."""
    _get_renderer().render_to_markdown(formatted_string, destination)


def _render_to_html(formatted_string: str, destination: Union[str, Path, TextIO],
                   css_classes: bool = False, standalone: bool = True) -> None:
    """INTERNAL: Render to HTML (planned implementation)."""
    _get_renderer().render_to_html(formatted_string, destination, css_classes, standalone)


# Test function to verify renderer functionality
def _test_renderer():
    """Test the renderer with sample formatted strings."""
    
    print("=" * 60)
    print("FDL RENDERER TEST")
    print("=" * 60)
    
    # Create test formatted string (what reconstructor would produce)
    test_string = "\033[1m\033[31mError:\033[0m Something went wrong at \033[3m14:30:15\033[0m\n"
    
    print("Test string from reconstructor:")
    print(repr(test_string))
    
    print("\nConsole output (with formatting):")
    _render_to_console(test_string)
    
    print("\nPlain text version:")
    renderer = _get_renderer()
    clean = renderer._strip_ansi(test_string)
    print(repr(clean))
    print("Stripped:", clean)
    
    print("\nCapabilities:")
    caps = renderer.get_capabilities()
    for key, value in caps.items():
        print(f"  {key}: {value}")
    
    # Test file output
    print("\nTesting file output...")
    try:
        test_file = Path("test_output.txt")
        _render_to_plaintext(test_string, test_file)
        
        # Read it back
        content = test_file.read_text()
        print(f"File content: {repr(content)}")
        
        # Clean up
        test_file.unlink()
        print("✓ File output test passed")
        
    except Exception as e:
        print(f"❌ File output test failed: {e}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    _test_renderer()