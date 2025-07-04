"""
Compiled Regex Patterns Serialization Handler

This module provides serialization support for compiled regular expression
patterns that are technically serializable but slow to pickle/unpickle due
to their complex internal state and compilation overhead.

SUPPORTED OBJECTS:
==================

1. COMPILED PATTERNS:
   - re.Pattern objects (Python 3.7+) / _sre.SRE_Pattern (older versions)
   - Patterns created with re.compile()
   - Patterns with various flags (IGNORECASE, MULTILINE, etc.)

2. MATCH OBJECTS:
   - re.Match objects (results from pattern.search(), pattern.match())
   - Match objects with groups, spans, and captured text
   - Failed match objects (None results)

3. REGEX FLAGS:
   - Individual flags (re.IGNORECASE, re.MULTILINE, etc.)
   - Combined flags (re.IGNORECASE | re.MULTILINE)
   - Custom flag combinations

SERIALIZATION STRATEGY:
======================

Regex serialization focuses on performance optimization:

1. **Pattern Storage**: Store the original pattern string and flags
2. **Recompilation**: Recompile patterns on deserialization for consistency
3. **Match Preservation**: Store match results with all group information
4. **Flag Preservation**: Maintain exact flag combinations
5. **Performance Optimization**: Avoid expensive pickle overhead

Our approach:
- **Store pattern source** (the original regex string)
- **Store compilation flags** (for exact recreation)
- **Cache compiled patterns** to avoid repeated compilation
- **Preserve match state** including groups and spans
- **Handle pattern variations** (raw strings, Unicode, etc.)

ADVANTAGES:
===========
- Much faster than pickle serialization of compiled patterns
- Consistent behavior across Python versions
- Preserves exact pattern semantics
- Enables pattern caching and reuse
- Smaller serialized size than pickle

LIMITATIONS:
============
- Custom pattern classes are not supported
- Some internal pattern optimizations may differ after recompilation
- Match objects lose connection to original pattern instance
- Very complex patterns might have slight performance differences

"""

import re
import sys
from typing import Any, Dict, Optional, List, Union, Pattern, Match

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class RegexPatternsHandler(_NSO_Handler):
    """Handler for compiled regex patterns and match objects."""
    
    def __init__(self):
        """Initialize the regex patterns handler."""
        super().__init__()
        self._handler_name = "RegexPatternsHandler"
        self._priority = 20  # High priority since regex is very common and performance-critical
        
        # Cache for compiled patterns to avoid recompilation
        self._pattern_cache = {}
        
        # Maximum cache size to prevent memory issues
        self._max_cache_size = 1000
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given regex object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for compiled regex patterns (re.Pattern)
        - Check for match objects (re.Match)
        - Check for older pattern types (_sre.SRE_Pattern)
        - Handle different Python version variations
        """
        try:
            # Python 3.7+ has re.Pattern type
            if hasattr(re, 'Pattern') and isinstance(obj, re.Pattern):
                return True
            
            # Match objects
            if hasattr(re, 'Match') and isinstance(obj, re.Match):
                return True
            
            # Older Python versions use _sre module types
            # Check by type name since _sre types can vary
            obj_type_name = type(obj).__name__
            obj_module = getattr(type(obj), '__module__', '')
            
            # Common pattern type names across Python versions
            pattern_types = {
                'Pattern', 'SRE_Pattern', '_sre.SRE_Pattern'
            }
            
            # Common match type names
            match_types = {
                'Match', 'SRE_Match', '_sre.SRE_Match'
            }
            
            if obj_type_name in pattern_types and ('re' in obj_module or '_sre' in obj_module):
                return True
            
            if obj_type_name in match_types and ('re' in obj_module or '_sre' in obj_module):
                return True
            
            # Additional check for objects that have pattern-like methods
            if hasattr(obj, 'pattern') and hasattr(obj, 'flags') and hasattr(obj, 'search'):
                return True
            
            # Additional check for objects that have match-like methods
            if hasattr(obj, 'group') and hasattr(obj, 'groups') and hasattr(obj, 'span'):
                return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a regex object to a dictionary representation.
        
        Args:
            obj: Regex object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the object
            
        SERIALIZATION PROCESS:
        1. Determine regex object type (pattern vs match)
        2. Extract pattern string and flags
        3. For matches, extract all group information
        4. Store metadata for exact recreation
        5. Optimize for fast deserialization
        """
        # Base serialization data
        data = {
            "regex_type": self._get_regex_type(obj),
            "object_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "serialization_strategy": None,  # Will be determined below
            "recreation_possible": True,
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        regex_type = data["regex_type"]
        
        if regex_type == "pattern":
            data.update(self._serialize_pattern(obj))
            data["serialization_strategy"] = "pattern_recompilation"
            
        elif regex_type == "match":
            data.update(self._serialize_match(obj))
            data["serialization_strategy"] = "match_recreation"
            
        else:
            # Unknown regex type
            data.update(self._serialize_unknown_regex(obj))
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a regex object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized regex data
            
        Returns:
            Recreated regex object (compiled pattern or match object)
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Use pattern cache for performance
        4. Restore object with exact semantics
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        regex_type = data.get("regex_type", "unknown")
        
        try:
            if strategy == "pattern_recompilation":
                return self._deserialize_pattern(data)
            
            elif strategy == "match_recreation":
                return self._deserialize_match(data)
            
            elif strategy == "fallback_placeholder":
                return self._deserialize_unknown_regex(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a placeholder
            return self._create_error_placeholder(regex_type, str(e))
    
    # ========================================================================
    # REGEX TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_regex_type(self, obj: Any) -> str:
        """
        Determine the specific type of regex object.
        
        Args:
            obj: Regex object to analyze
            
        Returns:
            String identifying the regex object type
        """
        # Check for pattern objects
        if hasattr(obj, 'pattern') and hasattr(obj, 'flags') and hasattr(obj, 'search'):
            return "pattern"
        
        # Check for match objects
        if hasattr(obj, 'group') and hasattr(obj, 'groups') and hasattr(obj, 'span'):
            return "match"
        
        # Check by type name
        obj_type_name = type(obj).__name__
        
        if 'Pattern' in obj_type_name or 'SRE_Pattern' in obj_type_name:
            return "pattern"
        
        if 'Match' in obj_type_name or 'SRE_Match' in obj_type_name:
            return "match"
        
        return "unknown"
    
    # ========================================================================
    # PATTERN SERIALIZATION
    # ========================================================================
    
    def _serialize_pattern(self, pattern) -> Dict[str, Any]:
        """
        Serialize compiled regex pattern objects.
        
        Store pattern string, flags, and metadata for recompilation.
        """
        result = {
            "pattern_string": None,
            "pattern_flags": 0,
            "pattern_groups": 0,
            "pattern_groupindex": {},
            "pattern_metadata": {}
        }
        
        try:
            # Get the original pattern string
            result["pattern_string"] = pattern.pattern
            
            # Get compilation flags
            result["pattern_flags"] = pattern.flags
            
            # Get group information
            result["pattern_groups"] = pattern.groups
            result["pattern_groupindex"] = getattr(pattern, 'groupindex', {})
            
            # Get additional metadata
            result["pattern_metadata"] = {
                "groups": pattern.groups,
                "groupindex": getattr(pattern, 'groupindex', {}),
            }
            
            # Store flag breakdown for debugging
            result["flag_breakdown"] = self._breakdown_flags(pattern.flags)
            
        except Exception as e:
            result["note"] = f"Error serializing pattern: {e}"
            result["recreation_possible"] = False
        
        result["recreation_possible"] = result["pattern_string"] is not None
        result["performance_note"] = "Pattern will be recompiled for optimal performance"
        
        return result
    
    def _deserialize_pattern(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize compiled regex pattern objects by recompiling.
        """
        pattern_string = data.get("pattern_string")
        pattern_flags = data.get("pattern_flags", 0)
        
        if pattern_string is None:
            raise ValueError("No pattern string available for pattern recreation")
        
        try:
            # Create cache key
            cache_key = (pattern_string, pattern_flags)
            
            # Check cache first
            if cache_key in self._pattern_cache:
                return self._pattern_cache[cache_key]
            
            # Recompile the pattern
            compiled_pattern = re.compile(pattern_string, pattern_flags)
            
            # Add to cache (with size limit)
            if len(self._pattern_cache) < self._max_cache_size:
                self._pattern_cache[cache_key] = compiled_pattern
            elif len(self._pattern_cache) >= self._max_cache_size:
                # Clear cache when it gets too large
                self._pattern_cache.clear()
                self._pattern_cache[cache_key] = compiled_pattern
            
            return compiled_pattern
            
        except Exception as e:
            raise ValueError(f"Could not recompile regex pattern: {e}")
    
    # ========================================================================
    # MATCH SERIALIZATION
    # ========================================================================
    
    def _serialize_match(self, match) -> Dict[str, Any]:
        """
        Serialize regex match objects.
        
        Store all match information including groups, spans, and text.
        """
        result = {
            "match_string": None,
            "match_pattern": None,
            "match_pos": 0,
            "match_endpos": 0,
            "match_groups": [],
            "match_groupdict": {},
            "match_spans": [],
            "pattern_info": {}
        }
        
        try:
            # Get the matched string
            result["match_string"] = match.string
            
            # Get match position information
            result["match_pos"] = match.pos
            result["match_endpos"] = match.endpos
            
            # Get all groups (including group 0 which is the entire match)
            try:
                # Get the number of groups
                groups_count = match.lastindex if match.lastindex else 0
                
                # Store all groups (0 to groups_count)
                for i in range(groups_count + 1):
                    try:
                        group_text = match.group(i)
                        group_span = match.span(i)
                        result["match_groups"].append({
                            "index": i,
                            "text": group_text,
                            "span": group_span
                        })
                        result["match_spans"].append(group_span)
                    except IndexError:
                        # Group doesn't exist
                        result["match_groups"].append({
                            "index": i,
                            "text": None,
                            "span": (-1, -1)
                        })
                        result["match_spans"].append((-1, -1))
                
                # Get group dictionary (named groups)
                result["match_groupdict"] = match.groupdict()
                
            except Exception as e:
                result["note"] = f"Error extracting match groups: {e}"
            
            # Get pattern information from the match
            if hasattr(match, 're') and match.re:
                pattern = match.re
                result["pattern_info"] = {
                    "pattern_string": getattr(pattern, 'pattern', None),
                    "pattern_flags": getattr(pattern, 'flags', 0),
                    "pattern_groups": getattr(pattern, 'groups', 0),
                    "pattern_groupindex": getattr(pattern, 'groupindex', {})
                }
                result["match_pattern"] = getattr(pattern, 'pattern', None)
            
        except Exception as e:
            result["note"] = f"Error serializing match: {e}"
            result["recreation_possible"] = False
        
        result["recreation_possible"] = (
            result["match_string"] is not None and 
            result["match_groups"] and
            result["pattern_info"].get("pattern_string") is not None
        )
        
        result["limitation"] = "Match object will be recreated but won't be identical to original"
        
        return result
    
    def _deserialize_match(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize regex match objects.
        
        Recreate match by re-executing the pattern on the original string.
        """
        match_string = data.get("match_string")
        pattern_info = data.get("pattern_info", {})
        match_groups = data.get("match_groups", [])
        match_pos = data.get("match_pos", 0)
        match_endpos = data.get("match_endpos")
        
        if not match_string or not pattern_info.get("pattern_string"):
            raise ValueError("Insufficient data to recreate match object")
        
        try:
            # Recreate the pattern
            pattern_string = pattern_info["pattern_string"]
            pattern_flags = pattern_info.get("pattern_flags", 0)
            pattern = re.compile(pattern_string, pattern_flags)
            
            # Try to recreate the match by searching in the original string
            # We'll try different approaches to find the same match
            
            # Approach 1: Search in the full string
            match = pattern.search(match_string, match_pos, match_endpos)
            
            if match:
                # Verify this is the same match by checking groups
                if match_groups and len(match_groups) > 0:
                    expected_match_text = match_groups[0].get("text")
                    if expected_match_text is not None and match.group(0) == expected_match_text:
                        return match
                else:
                    return match
            
            # Approach 2: If we have group information, try to find the exact match
            if match_groups and len(match_groups) > 0:
                main_group = match_groups[0]
                expected_text = main_group.get("text")
                expected_span = main_group.get("span", (-1, -1))
                
                if expected_text and expected_span != (-1, -1):
                    start, end = expected_span
                    if 0 <= start < len(match_string) and start < end <= len(match_string):
                        # Check if the expected text is at the expected position
                        actual_text = match_string[start:end]
                        if actual_text == expected_text:
                            # Create a match by searching exactly at this position
                            match = pattern.match(match_string, start, end)
                            if match:
                                return match
            
            # Approach 3: Create a placeholder match object
            return self._create_match_placeholder(data)
            
        except Exception as e:
            raise ValueError(f"Could not recreate match object: {e}")
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _breakdown_flags(self, flags: int) -> Dict[str, bool]:
        """
        Break down regex flags into individual components.
        
        Args:
            flags: Combined flags integer
            
        Returns:
            Dictionary showing which flags are set
        """
        flag_breakdown = {}
        
        # Common regex flags
        flag_mapping = {
            'IGNORECASE': getattr(re, 'IGNORECASE', 0),
            'LOCALE': getattr(re, 'LOCALE', 0),
            'MULTILINE': getattr(re, 'MULTILINE', 0),
            'DOTALL': getattr(re, 'DOTALL', 0),
            'UNICODE': getattr(re, 'UNICODE', 0),
            'VERBOSE': getattr(re, 'VERBOSE', 0),
            'ASCII': getattr(re, 'ASCII', 0) if hasattr(re, 'ASCII') else 0,
        }
        
        for flag_name, flag_value in flag_mapping.items():
            if flag_value and (flags & flag_value):
                flag_breakdown[flag_name] = True
            else:
                flag_breakdown[flag_name] = False
        
        return flag_breakdown
    
    def _create_match_placeholder(self, data: Dict[str, Any]) -> Any:
        """
        Create a placeholder match object when recreation fails.
        
        Args:
            data: Serialized match data
            
        Returns:
            Placeholder object that mimics match interface
        """
        match_string = data.get("match_string", "")
        match_groups = data.get("match_groups", [])
        match_groupdict = data.get("match_groupdict", {})
        
        class MatchPlaceholder:
            def __init__(self, string, groups, groupdict):
                self.string = string
                self._groups = groups
                self._groupdict = groupdict
                self.pos = data.get("match_pos", 0)
                self.endpos = data.get("match_endpos", len(string))
                
                # Find the last non-None group index
                self.lastindex = None
                for i in range(len(groups) - 1, 0, -1):  # Start from end, skip group 0
                    if groups[i].get("text") is not None:
                        self.lastindex = i
                        break
            
            def group(self, *args):
                if not args:
                    # Return group 0 (entire match)
                    return self._groups[0].get("text") if self._groups else None
                
                if len(args) == 1:
                    arg = args[0]
                    if isinstance(arg, int):
                        if 0 <= arg < len(self._groups):
                            return self._groups[arg].get("text")
                        else:
                            raise IndexError(f"no such group: {arg}")
                    elif isinstance(arg, str):
                        return self._groupdict.get(arg)
                    else:
                        raise TypeError("group() argument must be an integer or string")
                else:
                    # Multiple arguments
                    result = []
                    for arg in args:
                        if isinstance(arg, int):
                            if 0 <= arg < len(self._groups):
                                result.append(self._groups[arg].get("text"))
                            else:
                                raise IndexError(f"no such group: {arg}")
                        elif isinstance(arg, str):
                            result.append(self._groupdict.get(arg))
                        else:
                            raise TypeError("group() argument must be an integer or string")
                    return tuple(result)
            
            def groups(self):
                # Return all groups except group 0
                return tuple(
                    group.get("text") for group in self._groups[1:]
                    if group.get("text") is not None
                )
            
            def groupdict(self):
                return self._groupdict.copy()
            
            def span(self, group=0):
                if isinstance(group, int):
                    if 0 <= group < len(self._groups):
                        return self._groups[group].get("span", (-1, -1))
                    else:
                        raise IndexError(f"no such group: {group}")
                elif isinstance(group, str):
                    # Find named group
                    for i, g in enumerate(self._groups):
                        if group in self._groupdict and self._groupdict[group] == g.get("text"):
                            return g.get("span", (-1, -1))
                    return (-1, -1)
                else:
                    raise TypeError("span() argument must be an integer or string")
            
            def start(self, group=0):
                span = self.span(group)
                return span[0] if span != (-1, -1) else -1
            
            def end(self, group=0):
                span = self.span(group)
                return span[1] if span != (-1, -1) else -1
            
            def __repr__(self):
                if self._groups:
                    match_text = self._groups[0].get("text", "")
                    span = self._groups[0].get("span", (-1, -1))
                    return f"<MatchPlaceholder object; span={span}, match='{match_text}'>"
                else:
                    return "<MatchPlaceholder object; no match data>"
        
        return MatchPlaceholder(match_string, match_groups, match_groupdict)
    
    def _serialize_unknown_regex(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown regex types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_type": type(obj).__name__,
            "object_module": getattr(type(obj), '__module__', 'unknown'),
            "has_pattern": hasattr(obj, 'pattern'),
            "has_search": hasattr(obj, 'search'),
            "has_groups": hasattr(obj, 'groups'),
            "note": f"Unknown regex type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_regex(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown regex types with placeholder.
        """
        object_type = data.get("object_type", "unknown")
        
        class RegexPlaceholder:
            def __init__(self, obj_type):
                self.obj_type = obj_type
            
            def __repr__(self):
                return f"<RegexPlaceholder type='{self.obj_type}'>"
            
            def search(self, *args, **kwargs):
                raise RuntimeError(f"Regex object ({self.obj_type}) could not be recreated")
            
            def match(self, *args, **kwargs):
                raise RuntimeError(f"Regex object ({self.obj_type}) could not be recreated")
        
        return RegexPlaceholder(object_type)
    
    def _create_error_placeholder(self, regex_type: str, error_message: str) -> Any:
        """
        Create a placeholder regex object for objects that failed to deserialize.
        """
        class RegexErrorPlaceholder:
            def __init__(self, obj_type, error):
                self.obj_type = obj_type
                self.error = error
            
            def __repr__(self):
                return f"<RegexErrorPlaceholder type='{self.obj_type}' error='{self.error}'>"
            
            def search(self, *args, **kwargs):
                raise RuntimeError(f"Regex object ({self.obj_type}) deserialization failed: {self.error}")
            
            def match(self, *args, **kwargs):
                raise RuntimeError(f"Regex object ({self.obj_type}) deserialization failed: {self.error}")
        
        return RegexErrorPlaceholder(regex_type, error_message)


# Create a singleton instance for auto-registration
regex_patterns_handler = RegexPatternsHandler()