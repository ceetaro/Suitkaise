"""
SK Objects Serialization Handler

This module provides serialization support for Suitkaise-specific objects
that may contain complex state or non-serializable components.

Supported Objects:
- SKPath objects (dual-path architecture)
- Timer objects (statistical timing data)
- Stopwatch objects (timing state and laps)
- Yawn objects (sleep controller state)
- FDPrint objects (_Colors, _FormatMode, etc.)

Strategy:
- Extract essential state from SK objects
- Preserve configuration and statistical data
- Recreate objects with identical functionality
- Handle cross-module dependencies carefully
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional, List, Union

from suitkaise._int.core.path_ops import _is_suitkaise_module, _get_module_file_path

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class SKObjectsHandler(_NSO_Handler):
    """Handler for Suitkaise-specific objects."""
    
    def can_handle(self, obj: Any) -> bool:
        """Check if this handler can serialize the given SK object."""
        # Check if object is from suitkaise module
        obj_module = getattr(obj, '__module__', '')
        if not obj_module or not _is_suitkaise_module(_get_module_file_path(obj_module)):
            return False
        
        # Check for specific SK object types
        obj_type_name = obj.__class__.__name__
        
        # SKPath objects
        if obj_type_name == 'SKPath':
            return True
        
        # SKTime objects
        if obj_type_name in ['Timer', 'Stopwatch', 'Yawn']:
            return True
        
        # FDPrint objects
        if obj_type_name in ['_Colors', '_FormatMode']:
            return True
        
        # Check for internal SK objects
        if obj_type_name.startswith('_') and 'suitkaise' in obj_module:
            return True
        
        return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """Serialize an SK object to a dictionary representation."""
        obj_type = type(obj)
        obj_module = obj_type.__module__
        obj_name = obj_type.__name__
        
        # Base serialization data
        data = {
            "sk_object_type": obj_name,
            "module": obj_module,
            "full_type": f"{obj_module}.{obj_name}"
        }
        
        # Handle specific SK object types
        if obj_name == 'SKPath':
            data.update(self._serialize_skpath(obj))
        
        elif obj_name == 'Timer':
            data.update(self._serialize_timer(obj))
        
        elif obj_name == 'Stopwatch':
            data.update(self._serialize_stopwatch(obj))
        
        elif obj_name == 'Yawn':
            data.update(self._serialize_yawn(obj))
        
        elif obj_name == '_Colors':
            data.update(self._serialize_colors(obj))
        
        elif obj_name == '_FormatMode':
            data.update(self._serialize_format_mode(obj))
        
        else:
            # Generic SK object serialization
            data.update(self._serialize_generic_sk_object(obj))
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """Deserialize an SK object from dictionary representation."""
        sk_object_type = data.get("sk_object_type")
        module = data.get("module", "")
        
        # Route to appropriate deserialization method
        if sk_object_type == 'SKPath':
            return self._deserialize_skpath(data)
        
        elif sk_object_type == 'Timer':
            return self._deserialize_timer(data)
        
        elif sk_object_type == 'Stopwatch':
            return self._deserialize_stopwatch(data)
        
        elif sk_object_type == 'Yawn':
            return self._deserialize_yawn(data)
        
        elif sk_object_type == '_Colors':
            return self._deserialize_colors(data)
        
        elif sk_object_type == '_FormatMode':
            return self._deserialize_format_mode(data)
        
        else:
            raise ValueError(f"Unknown SK object type: {sk_object_type}")
    
    def _serialize_skpath(self, obj) -> Dict[str, Any]:
        """Serialize SKPath objects."""
        return {
            "absolute_path": str(obj._absolute_path),
            "normalized_path": obj._normalized_path,
            "project_root": str(obj._project_root) if obj._project_root else None,
            "note": "SKPath dual-path architecture preserved"
        }
    
    def _serialize_timer(self, obj) -> Dict[str, Any]:
        """Serialize Timer objects."""
        return {
            "times": obj._timer.times.copy() if hasattr(obj._timer, 'times') else [],
            "current_start": obj._timer.current_start,
            "note": "Timer statistical data preserved"
        }
    
    def _serialize_stopwatch(self, obj) -> Dict[str, Any]:
        """Serialize Stopwatch objects."""
        return {
            "start_time": obj._stopwatch.start_time,
            "pause_time": obj._stopwatch.pause_time,
            "total_paused_time": obj._stopwatch.total_paused_time,
            "lap_times": obj._stopwatch.lap_times.copy(),
            "is_running": obj._stopwatch.is_running,
            "is_paused": obj._stopwatch.is_paused,
            "final_time": obj._stopwatch.final_time,
            "note": "Stopwatch state and laps preserved"
        }
    
    def _serialize_yawn(self, obj) -> Dict[str, Any]:
        """Serialize Yawn objects."""
        return {
            "sleep_duration": obj._yawn.sleep_duration,
            "yawn_threshold": obj._yawn.yawn_threshold,
            "log_sleep": obj._yawn.log_sleep,
            "yawn_count": obj._yawn.yawn_count,
            "total_sleeps": obj._yawn.total_sleeps,
            "note": "Yawn controller state preserved"
        }
    
    def _serialize_colors(self, obj) -> Dict[str, Any]:
        """Serialize _Colors objects."""
        return {
            "enabled": obj._enabled,
            "note": "Colors configuration preserved"
        }
    
    def _serialize_format_mode(self, obj) -> Dict[str, Any]:
        """Serialize _FormatMode enum objects."""
        return {
            "value": obj.value,
            "note": "Format mode enum value preserved"
        }
    
    def _serialize_generic_sk_object(self, obj) -> Dict[str, Any]:
        """Generic serialization for unknown SK objects."""
        # Try to extract basic attributes
        attrs = {}
        for attr_name in dir(obj):
            if not attr_name.startswith('__'):
                try:
                    attr_value = getattr(obj, attr_name)
                    # Only serialize simple types
                    if isinstance(attr_value, (int, float, str, bool, list, dict, type(None))):
                        attrs[attr_name] = attr_value
                except:
                    pass
        
        return {
            "attributes": attrs,
            "note": "Generic SK object with basic attributes preserved"
        }
    
    def _deserialize_skpath(self, data: Dict[str, Any]) -> Any:
        """Deserialize SKPath objects."""
        # Import SKPath at runtime to avoid circular imports
        try:
            from suitkaise.skpath import SKPath
        except ImportError:
            raise ImportError("Cannot deserialize SKPath: suitkaise.skpath not available")
        
        absolute_path = data.get("absolute_path")
        project_root = data.get("project_root")
        
        if not absolute_path:
            raise ValueError("Missing absolute_path for SKPath deserialization")
        
        # Create SKPath with explicit project root if available
        if project_root:
            return SKPath(absolute_path, Path(project_root))
        else:
            return SKPath(absolute_path)
    
    def _deserialize_timer(self, data: Dict[str, Any]) -> Any:
        """Deserialize Timer objects."""
        # Import Timer at runtime to avoid circular imports
        try:
            from suitkaise.sktime import Timer
        except ImportError:
            raise ImportError("Cannot deserialize Timer: suitkaise.sktime not available")
        
        # Create new Timer and restore state
        timer = Timer()
        
        # Restore timing data
        times = data.get("times", [])
        if times:
            timer._timer.times = times
        
        current_start = data.get("current_start")
        if current_start:
            timer._timer.current_start = current_start
        
        return timer
    
    def _deserialize_stopwatch(self, data: Dict[str, Any]) -> Any:
        """Deserialize Stopwatch objects."""
        # Import Stopwatch at runtime to avoid circular imports
        try:
            from suitkaise.sktime import Stopwatch
        except ImportError:
            raise ImportError("Cannot deserialize Stopwatch: suitkaise.sktime not available")
        
        # Create new Stopwatch and restore state
        stopwatch = Stopwatch()
        
        # Restore all state
        stopwatch._stopwatch.start_time = data.get("start_time")
        stopwatch._stopwatch.pause_time = data.get("pause_time") 
        stopwatch._stopwatch.total_paused_time = data.get("total_paused_time", 0.0)
        stopwatch._stopwatch.lap_times = data.get("lap_times", [])
        stopwatch._stopwatch.is_running = data.get("is_running", False)
        stopwatch._stopwatch.is_paused = data.get("is_paused", False)
        stopwatch._stopwatch.final_time = data.get("final_time")
        
        return stopwatch
    
    def _deserialize_yawn(self, data: Dict[str, Any]) -> Any:
        """Deserialize Yawn objects."""
        # Import Yawn at runtime to avoid circular imports
        try:
            from suitkaise.sktime import Yawn
        except ImportError:
            raise ImportError("Cannot deserialize Yawn: suitkaise.sktime not available")
        
        # Create new Yawn with original configuration
        sleep_duration = data.get("sleep_duration", 1.0)
        yawn_threshold = data.get("yawn_threshold", 1)
        log_sleep = data.get("log_sleep", False)
        
        yawn = Yawn(sleep_duration, yawn_threshold, log_sleep)
        
        # Restore state
        yawn._yawn.yawn_count = data.get("yawn_count", 0)
        yawn._yawn.total_sleeps = data.get("total_sleeps", 0)
        
        return yawn
    
    def _deserialize_colors(self, data: Dict[str, Any]) -> Any:
        """Deserialize _Colors objects."""
        # Import _Colors at runtime to avoid circular imports
        try:
            from suitkaise._int.core.format_ops import _Colors
        except ImportError:
            raise ImportError("Cannot deserialize _Colors: suitkaise._int.core.format_ops not available")
        
        # _Colors is a class, not an instance - restore its state
        enabled = data.get("enabled", True)
        if enabled:
            _Colors.enable()
        else:
            _Colors.disable()
        
        return _Colors
    
    def _deserialize_format_mode(self, data: Dict[str, Any]) -> Any:
        """Deserialize _FormatMode enum objects."""
        # Import _FormatMode at runtime to avoid circular imports
        try:
            from suitkaise._int.core.format_ops import _FormatMode
        except ImportError:
            raise ImportError("Cannot deserialize _FormatMode: suitkaise._int.core.format_ops not available")
        
        value = data.get("value")
        if value == "display":
            return _FormatMode.DISPLAY
        elif value == "debug":
            return _FormatMode.DEBUG
        else:
            raise ValueError(f"Unknown _FormatMode value: {value}")


# Create a singleton instance
sk_objects_handler = SKObjectsHandler()