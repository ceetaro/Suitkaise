# elements/text_element.py
from .base_element import _ElementProcessor
from ..core.format_state import _FormatState


class _TextElement(_ElementProcessor):
    """
    Handles plain text content.
    
    Box content is handled separately by the box system.
    """
    
    def __init__(self, text: str):
        """
        Initialize text element.
        
        Args:
            text: Text content to process
        """
        self.text = text
    
    def process(self, format_state: _FormatState) -> _FormatState:
        """Process text element."""
        if not self.text:
            return format_state
        
        if format_state.in_box:
            # Inside box - add to box content
            format_state.box_content.append(self.text)
        else:
            # Outside box - use base element's automatic wrapping
            self._add_to_outputs(format_state, self.text)
        
        return format_state