"""
Handler for compiled regex pattern objects.

Regex patterns are compiled regular expressions. We serialize the pattern
string and flags, then recompile in the target process.
"""

import re
from typing import Any, Dict
from .base_class import Handler


class RegexSerializationError(Exception):
    """Raised when regex serialization fails."""
    pass


class RegexPatternHandler(Handler):
    """
    Serializes compiled regular expression Pattern objects.
    
    Strategy:
    - Extract pattern string and flags
    - On reconstruction, recompile with same pattern and flags
    
    Note: Python's re.Pattern objects are already picklable in Python 3.7+,
    but we handle them explicitly for consistency and to support older versions.
    """
    
    type_name = "regex_pattern"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a compiled regex pattern.
        
        The type is re.Pattern (or _sre.SRE_Pattern in older Python).
        """
        return isinstance(obj, re.Pattern)
    
    def extract_state(self, obj: re.Pattern) -> Dict[str, Any]:
        """
        Extract regex pattern state.
        
        What we capture:
        - pattern: The regex pattern string (e.g., r'\d+')
        - flags: Compilation flags (re.IGNORECASE, re.MULTILINE, etc.)
        
        These are all we need to recreate the exact same compiled pattern.
        """
        return {
            "pattern": obj.pattern,  # The regex pattern string
            "flags": obj.flags,      # Integer bitmask of flags
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> re.Pattern:
        """
        Reconstruct regex pattern.
        
        Simply recompile with the same pattern and flags.
        """
        return re.compile(state["pattern"], state["flags"])

