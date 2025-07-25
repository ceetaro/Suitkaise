# elements/_text_element.py
from .base_element import _ElementProcessor
from ..core.format_state import _FormatState

class _TextElement(_ElementProcessor):
    """Handles plain text content."""
    
    def __init__(self, text: str):
        self.text = text
    
    def process(self, format_state: _FormatState) -> _FormatState:
        if not self.text:
            return format_state
        
        if format_state.in_box:
            format_state.box_content.append(self.text)
        else:
            self._add_to_outputs(format_state, self.text)
        
        return format_state
    
    def __repr__(self):
        return f"_TextElement({self.text!r})"