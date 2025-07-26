# processors/commands/__init__.py
"""
Command processors module.

Imports all command processors to ensure automatic registration.
"""

# Import all command processors for automatic registration
from .text_commands import _TextCommandProcessor
from .time_commands import _TimeCommandProcessor  
from .box_commands import _BoxCommandProcessor
from .layout_commands import _LayoutCommandProcessor
# from .fmt_commands import _FormatCommandProcessor      # When implemented
# from .debug_commands import _DebugCommandProcessor     # When implemented

__all__ = [
    '_TextCommandProcessor',
    '_TimeCommandProcessor', 
    '_BoxCommandProcessor',
    '_LayoutCommandProcessor',
]