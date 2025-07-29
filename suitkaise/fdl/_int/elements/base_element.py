"""
Private Base Element Processor for FDL processing.

This module provides the private base class that all FDL element processors 
inherit from. It includes methods for adding content to all output streams 
with appropriate formatting.

This is internal to the FDL engine and not exposed to users.
"""

from abc import ABC, abstractmethod
from ..core.format_state import _FormatState
from ..setup.color_conversion import _to_ansi_fg, _to_ansi_bg, _normalize_for_html


class _ElementProcessor(ABC):
    """
    Private base class for all FDL element processors.
    
    All element types (_TextElement, _CommandElement, etc.) inherit from this
    and must implement the process() method. This base class provides
    standardized methods for adding content to all output streams.
    
    This class is internal and should never be exposed to end users.
    """
    
    @abstractmethod
    def process(self, format_state: _FormatState) -> _FormatState:
        """
        Process this element and update the format state.
        
        Args:
            format_state: Current formatting state
            
        Returns:
            _FormatState: Updated formatting state
        """
        pass
    
    def _add_to_outputs(self, format_state: _FormatState, content: str) -> None:
        """
        Add content to all output streams with automatic wrapping and justification.
        """
        if not content:
            return
        
        if format_state.in_box:
            # Inside box - add directly without wrapping (box handles it)
            terminal_content = self._format_for_terminal(content, format_state)
            plain_content = self._format_for_plain(content, format_state)
            markdown_content = self._format_for_markdown(content, format_state)
            html_content = self._format_for_html(content, format_state)
            
            format_state.add_to_output_streams(
                terminal=terminal_content,
                plain=plain_content,
                markdown=markdown_content,
                html=html_content
            )
        else:
            # Outside box - apply wrapping and justification
            from ..setup.text_wrapping import _wrap_text
            from ..setup.text_justification import _justify_text
            
            # Wrap text to terminal width
            wrapped_lines = _wrap_text(content, format_state.terminal_width, True)
            justify = format_state.justify or 'left'
            
            for i, line in enumerate(wrapped_lines):
                # Don't skip whitespace-only lines - they preserve spacing
                # if not line.strip() and i == 0:
                #     continue
                
                if i > 0:
                    # Add newline between wrapped lines
                    format_state.add_to_output_streams('\n', '\n', '\n', '<br>\n')
                
                # Apply justification to terminal output
                justified_line = _justify_text(line, justify, format_state.terminal_width) if justify != 'left' else line
                
                # Format and add to streams
                terminal_content = self._format_for_terminal(justified_line, format_state)
                plain_content = self._format_for_plain(line, format_state)
                markdown_content = self._format_for_markdown(line, format_state)
                html_content = self._format_for_html(line, format_state)
                
                format_state.add_to_output_streams(
                    terminal=terminal_content,
                    plain=plain_content,
                    markdown=markdown_content,
                    html=html_content
                )
    
    def _format_for_terminal(self, content: str, format_state: _FormatState) -> str:
        """
        Apply ANSI formatting for terminal output.
        
        Args:
            content: Raw content
            format_state: Current formatting state
            
        Returns:
            str: Content with ANSI codes
        """
        ansi_codes = self._generate_ansi_codes(format_state)
        return f"{ansi_codes}{content}"
    
    def _format_for_plain(self, content: str, format_state: _FormatState) -> str:
        """
        Format for plain text output (no formatting).
        
        Args:
            content: Raw content
            format_state: Current formatting state (unused for plain text)
            
        Returns:
            str: Plain content
        """
        return content
    
    def _format_for_markdown(self, content: str, format_state: _FormatState) -> str:
        """
        Apply markdown formatting.
        
        Args:
            content: Raw content
            format_state: Current formatting state
            
        Returns:
            str: Content with markdown formatting
        """
        formatted = content
        
        # Apply text formatting
        if format_state.bold and format_state.italic:
            formatted = f"***{formatted}***"
        elif format_state.bold:
            formatted = f"**{formatted}**"
        elif format_state.italic:
            formatted = f"*{formatted}*"
        
        if format_state.strikethrough:
            formatted = f"~~{formatted}~~"
        
        # Note: Markdown doesn't have great support for colors or underline,
        # so we will skip those.
        
        return formatted
    
    def _format_for_html(self, content: str, format_state: _FormatState) -> str:
        """
        Apply HTML formatting.
        
        Args:
            content: Raw content
            format_state: Current formatting state
            
        Returns:
            str: Content with HTML tags and styles
        """
        if not self._needs_html_formatting(format_state):
            return content
        
        # Build CSS styles using centralized color conversion
        styles = []
        if format_state.text_color:
            normalized_color = _normalize_for_html(format_state.text_color)
            styles.append(f"color: {normalized_color}")
        if format_state.background_color:
            normalized_bg = _normalize_for_html(format_state.background_color)
            styles.append(f"background-color: {normalized_bg}")
        
        # Build CSS classes for text formatting
        classes = []
        if format_state.bold:
            classes.append("fdl-bold")
        if format_state.italic:
            classes.append("fdl-italic")
        if format_state.underline:
            classes.append("fdl-underline")
        if format_state.strikethrough:
            classes.append("fdl-strikethrough")
        
        # Build attributes
        attrs = []
        if styles:
            attrs.append(f'style="{"; ".join(styles)}"')
        if classes:
            attrs.append(f'class="{" ".join(classes)}"')
        
        attr_string = f' {" ".join(attrs)}' if attrs else ""
        return f"<span{attr_string}>{content}</span>"
    
    def _needs_html_formatting(self, format_state: _FormatState) -> bool:
        """Check if any formatting is applied that needs HTML tags."""
        return (
            format_state.text_color or
            format_state.background_color or
            format_state.bold or
            format_state.italic or
            format_state.underline or
            format_state.strikethrough
        )
    
    def _generate_ansi_codes(self, format_state: _FormatState) -> str:
        """
        Generate ANSI escape codes for current formatting state.
        
        Uses centralized color conversion system for all color handling.
        
        Args:
            format_state: Current formatting state
            
        Returns:
            str: ANSI escape codes
        """
        codes = []
        
        # Text color using centralized color conversion
        if format_state.text_color:
            color_code = _to_ansi_fg(format_state.text_color)
            if color_code:
                codes.append(color_code)
        
        # Background color using centralized color conversion
        if format_state.background_color:
            bg_code = _to_ansi_bg(format_state.background_color)
            if bg_code:
                codes.append(bg_code)
        
        # Text formatting
        if format_state.bold:
            codes.append("\033[1m")
        if format_state.italic:
            codes.append("\033[3m")
        if format_state.underline:
            codes.append("\033[4m")
        if format_state.strikethrough:
            codes.append("\033[9m")
        
        return "".join(codes)