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


class MatchObjectHandler(Handler):
    """
    Serializes regex Match objects.
    
    Strategy:
    - Extract match information (matched string, groups, positions)
    - Store as a dict since Match objects cannot be reconstructed
    - On reconstruction, return a dict with the match info
    
    Note: re.Match objects have no public constructor and cannot be truly
    reconstructed. We serialize the data for inspection but return a dict.
    """
    
    type_name = "regex_match"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a regex Match object."""
        return isinstance(obj, re.Match)
    
    def extract_state(self, obj: re.Match) -> Dict[str, Any]:
        """
        Extract match object state.
        
        What we capture:
        - pattern: The pattern that was matched
        - string: The string that was searched
        - pos: Start position of search
        - endpos: End position of search
        - match_string: The matched substring
        - span: (start, end) of the match
        - groups: All captured groups
        - groupdict: Named groups
        """
        return {
            "pattern": obj.re.pattern,
            "flags": obj.re.flags,
            "string": obj.string,
            "pos": obj.pos,
            "endpos": obj.endpos,
            "match_string": obj.group(0),  # The matched text
            "span": obj.span(),  # (start, end)
            "groups": obj.groups(),  # All captured groups
            "groupdict": obj.groupdict(),  # Named groups
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reconstruct match information.
        
        Since Match objects cannot be instantiated directly, we return
        a dict containing all the match information. This preserves the
        data while being honest about the limitation.
        """
        return {
            "__match_info__": True,
            "pattern": state["pattern"],
            "flags": state["flags"],
            "string": state["string"],
            "pos": state["pos"],
            "endpos": state["endpos"],
            "matched": state["match_string"],
            "span": state["span"],
            "groups": state["groups"],
            "groupdict": state["groupdict"],
        }

