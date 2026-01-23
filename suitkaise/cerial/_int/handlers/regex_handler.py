"""
Handler for compiled regex pattern objects.

Regex patterns are compiled regular expressions. We serialize the pattern
string and flags, then recompile in the target process.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional
from .base_class import Handler
from .reconnector import Reconnector


class RegexSerializationError(Exception):
    """Raised when regex serialization fails."""
    pass


class RegexPatternHandler(Handler):
    """
    Serializes compiled regular expression Pattern objects.
    
    Strategy:
    - Extract pattern string and flags
    - On reconstruction, recompile with same pattern and flags
    
    NOTE: Python's re.Pattern objects are already picklable in Python 3.7+,
    but we handle them explicitly for consistency.
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
            "pattern": obj.pattern,  # the regex pattern string
            "flags": obj.flags,      # integer bitmask of flags
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
    - On reconstruction, return a MatchReconnector that can rerun the match
      and return a live Match object when possible.
    
    Note: re.Match objects have no public constructor. We can't instantiate
    them directly, but we can re-run the same pattern on the same input to
    retrieve a matching object.
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
            "match_string": obj.group(0),  # the matched text
            "span": obj.span(),  # (start, end)
            "groups": obj.groups(),  # all captured groups
            "groupdict": obj.groupdict(),  # named groups
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct match information.
        
        Returns a MatchReconnector and attempts to reconnect immediately.
        """
        reconnector = MatchReconnector(state=state)
        try:
            match = reconnector.reconnect()
            return match if match is not None else reconnector
        except Exception:
            return reconnector


@dataclass
class MatchReconnector(Reconnector):
    """
    Recreate a Match object by re-running the regex on the original string.
    
    If the match can't be re-created (pattern or string changed), reconnect()
    returns None and the caller can fall back to the stored state.
    """
    state: Dict[str, Any]
    
    def reconnect(self) -> Optional[re.Match]:
        pattern = self.state["pattern"]
        flags = self.state["flags"]
        string = self.state["string"]
        pos = self.state["pos"]
        endpos = self.state["endpos"]
        span = tuple(self.state["span"])
        compiled = re.compile(pattern, flags)
        match = compiled.search(string, pos, endpos)
        if match and match.span() == span:
            return match
        return None

