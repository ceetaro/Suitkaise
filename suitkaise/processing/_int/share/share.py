"""
Share - Main container for process-safe shared state.

Share is the user-facing API for sharing data between processes.
It wraps objects in proxies and manages the coordinator automatically.

Usage:
    from suitkaise.processing import Share
    from suitkaise.timing import Sktimer
    
    share = Share()
    share.timer = Sktimer()  # Auto-wrapped in proxy
    share.counter = 0      # Wrapped as SharedCounter
    share.results = {}     # Wrapped as SharedDict
    
    # Pass share to workers, they can access shared.timer, etc.
"""

from typing import Any, Dict, Optional
from multiprocessing.managers import SyncManager

from .coordinator import _Coordinator
from .proxy import _ObjectProxy

# Import Skclass for auto-wrapping user objects
from suitkaise.sk import Skclass


class Share:
    """
    Container for process-safe shared state.
    
    Automatically manages:
    - A coordinator process for handling writes
    - Proxies for suitkaise objects (Sktimer, Circuit, etc.)
    - Shared wrappers for primitives (int → SharedCounter, dict → SharedDict)
    
    Objects with `_shared_meta` are detected and wrapped in proxies.
    Other objects are stored directly in the source of truth.
    
    Usage:
        share = Share()
        share.timer = Sktimer()    # Has _shared_meta, gets proxied
        share.counter = 0        # No _shared_meta, stored directly
        share.results = {}       # No _shared_meta, stored directly
        
        share.start()  # Start the coordinator
        
        # In workers:
        share.timer.add_time(2.5)  # Queued, non-blocking
        print(share.timer.mean)    # Waits, then fetches
        
        share.stop()  # Stop the coordinator
    """
    
    # Attrs that belong to Share itself, not shared objects
    _SHARE_ATTRS = frozenset({
        '_coordinator', '_proxies', '_started',
    })
    
    def __init__(self, manager: Optional[SyncManager] = None):
        """
        Create a new Share container.
        
        Args:
            manager: Optional SyncManager to use. Creates one if not provided.
        """
        object.__setattr__(self, '_coordinator', _Coordinator(manager))
        object.__setattr__(self, '_proxies', {})  # name -> proxy
        object.__setattr__(self, '_started', False)
        # Auto-start coordinator on creation
        self.start()
    
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Assign an object to be shared.
        
        - Objects with _shared_meta get wrapped in a proxy
        - User class instances without _shared_meta are auto-wrapped with Skclass
        - Primitives (int, str, etc.) are stored directly in source of truth
        """
        if name in self._SHARE_ATTRS:
            object.__setattr__(self, name, value)
            return
        
        # Check if this is an object with _shared_meta (suitkaise or @sk wrapped)
        has_meta = hasattr(type(value), '_shared_meta')
        
        # If it's a class instance without _shared_meta, auto-wrap with Skclass
        if not has_meta and self._is_user_class_instance(value):
            # Apply Skclass to generate _shared_meta
            sk_wrapper = Skclass(type(value))
            # Now the class has _shared_meta attached
            has_meta = True
        
        # Register the object with coordinator
        attrs: set[str] = set()
        if has_meta:
            meta = getattr(type(value), '_shared_meta', {})
            for method_meta in meta.get('methods', {}).values():
                attrs.update(method_meta.get('writes', []))
                attrs.update(method_meta.get('reads', []))
            for prop_meta in meta.get('properties', {}).values():
                attrs.update(prop_meta.get('reads', []))
                attrs.update(prop_meta.get('writes', []))
        self._coordinator.register_object(name, value, attrs=attrs if attrs else None)
        
        if has_meta:
            # Create a proxy for this object
            proxy = _ObjectProxy(name, self._coordinator, type(value))
            self._proxies[name] = proxy
        else:
            # No proxy - we'll fetch directly from source of truth
            self._proxies[name] = None
    
    def _is_user_class_instance(self, value: Any) -> bool:
        """
        Check if value is an instance of a user-defined class.
        
        Returns False for primitives, builtins, and known non-shareable types.
        """
        # Skip primitives and builtins
        if isinstance(value, (
            int, float, str, bytes, bool, type(None),
            list, dict, tuple, set, frozenset,
        )):
            return False
        
        # It's a class instance
        return True
    
    def __getattr__(self, name: str) -> Any:
        """
        Get a shared object.
        
        Returns the proxy if one exists, otherwise fetches from source of truth.
        """
        if name in self._SHARE_ATTRS:
            return object.__getattribute__(self, name)
        
        try:
            proxies = object.__getattribute__(self, '_proxies')
        except AttributeError:
            raise AttributeError(f"Share has no attribute '{name}'")
        
        if name not in proxies:
            raise AttributeError(f"Share has no attribute '{name}'")
        
        proxy = proxies[name]
        if proxy is not None:
            return proxy
        
        # No proxy - fetch directly from source of truth
        coordinator = object.__getattribute__(self, '_coordinator')
        obj = coordinator.get_object(name)
        if obj is None:
            raise AttributeError(f"Object '{name}' not found in Share")
        return obj
    
    def __delattr__(self, name: str) -> None:
        """
        Remove a shared object.
        """
        if name in self._SHARE_ATTRS:
            raise AttributeError(f"Cannot delete Share attribute '{name}'")
        
        if name in self._proxies:
            del self._proxies[name]
            # TODO: Also remove from coordinator's source of truth
    
    def start(self) -> None:
        """
        Start the coordinator process.
        
        Must be called before workers access shared objects.
        """
        if not self._started:
            self._coordinator.start()
            object.__setattr__(self, '_started', True)
    
    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop the coordinator process.
        
        Args:
            timeout: Maximum seconds to wait for shutdown.
        
        Returns:
            True if stopped cleanly, False if timed out.
        """
        if self._started:
            result = self._coordinator.stop(timeout)
            object.__setattr__(self, '_started', False)
            return result
        return True
    
    def __enter__(self) -> "Share":
        """Context manager entry - starts the coordinator."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - stops the coordinator."""
        self.stop()
    
    @property
    def is_running(self) -> bool:
        """Check if the coordinator is running."""
        return self._coordinator.is_alive
    
    @property
    def has_error(self) -> bool:
        """Check if the coordinator encountered an error."""
        return self._coordinator.has_error
    
    def __repr__(self) -> str:
        status = "running" if self.is_running else "stopped"
        if self.has_error:
            status = "error"
        objects = list(self._proxies.keys())
        return f"Share(status={status}, objects={objects})"

    def exit(self, timeout: float = 5.0) -> bool:
        """Alias for stop()."""
        return self.stop(timeout)

    def clear(self) -> None:
        """Clear all shared objects and counters."""
        self._coordinator.clear()
        self._proxies.clear()

    def __serialize__(self) -> dict:
        """
        Serialize Share without manager internals.
        
        Captures a snapshot of shared objects as cerial bytes.
        """
        coordinator = object.__getattribute__(self, '_coordinator')
        objects: Dict[str, bytes] = {}
        try:
            names = list(coordinator._object_names)
        except Exception:
            names = []
        for name in names:
            try:
                serialized = coordinator._source_store.get(name)
            except Exception:
                serialized = None
            if serialized is not None:
                objects[name] = serialized
        return {
            "objects": objects,
            "started": object.__getattribute__(self, '_started'),
        }

    @staticmethod
    def __deserialize__(state: dict) -> "Share":
        """
        Reconstruct Share from serialized snapshot.
        """
        from suitkaise import cerial
        
        share = Share()
        for name, serialized in state.get("objects", {}).items():
            try:
                obj = cerial.deserialize(serialized)
            except Exception:
                continue
            setattr(share, name, obj)
        if state.get("started"):
            share.start()
        return share
