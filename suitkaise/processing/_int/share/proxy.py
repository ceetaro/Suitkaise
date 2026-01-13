"""
Share Proxy - Transparent wrapper for shared objects.

The proxy intercepts all access to shared objects:
- Method calls → increment counters, queue command, return immediately
- Property reads → wait for pending writes, fetch from source of truth
- Property writes → increment counters, queue command

Uses _shared_meta on the wrapped class to know which attrs each method/property touches.
"""

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .coordinator import _Coordinator


class _ObjectProxy:
    """
    Proxy wrapper for shared objects.
    
    Makes shared objects look and feel like regular objects, but all
    access goes through the coordinator:
    
    - Method calls are queued as commands (fire-and-forget)
    - Property reads wait for pending writes, then fetch current state
    - The wrapped object is never accessed directly after creation
    
    Usage:
        coordinator.register_object('timer', timer)
        proxy = _ObjectProxy('timer', coordinator, type(timer))
        
        proxy.add_time(2.5)  # Queues command, returns immediately
        print(proxy.mean)    # Waits for writes, fetches fresh value
    """
    
    # Attributes that belong to the proxy itself, not the wrapped object
    _PROXY_ATTRS = frozenset({
        '_object_name', '_coordinator', '_wrapped_class', '_shared_meta',
    })
    
    def __init__(
        self,
        object_name: str,
        coordinator: "_Coordinator",
        wrapped_class: type,
    ):
        """
        Create a proxy for a shared object.
        
        Args:
            object_name: Name of the object in the coordinator.
            coordinator: The coordinator managing this object.
            wrapped_class: The class of the wrapped object (for _shared_meta lookup).
        """
        object.__setattr__(self, '_object_name', object_name)
        object.__setattr__(self, '_coordinator', coordinator)
        object.__setattr__(self, '_wrapped_class', wrapped_class)
        
        # Cache the _shared_meta if it exists
        meta = getattr(wrapped_class, '_shared_meta', None)
        object.__setattr__(self, '_shared_meta', meta)
    
    def __getattr__(self, name: str) -> Any:
        """
        Intercept attribute access.
        
        - If it's a method in _shared_meta, return a callable that queues commands
        - If it's a property in _shared_meta, wait for writes and return value
        - Otherwise, fetch from source of truth and return the attr
        """
        # Check if it's a method
        if self._shared_meta and name in self._shared_meta.get('methods', {}):
            return _MethodProxy(self, name)
        
        # Check if it's a property in metadata
        if self._shared_meta and name in self._shared_meta.get('properties', {}):
            return self._read_property(name)
        
        # Fallback: fetch object and get attr directly
        # This handles attrs not in _shared_meta
        return self._read_attr(name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Intercept attribute assignment.
        
        Proxy attrs are set directly. All others queue a setattr command.
        """
        if name in self._PROXY_ATTRS:
            object.__setattr__(self, name, value)
            return
        
        # Queue a setattr command
        # We treat this as writing to the attr itself
        self._coordinator.increment_pending(f"{self._object_name}.{name}")
        self._coordinator.queue_command(
            self._object_name,
            '__setattr__',
            (name, value),
            {},
            [name],
        )
    
    def _read_property(self, name: str) -> Any:
        """
        Read a property, waiting for pending writes first.
        
        Uses _shared_meta to know which attrs the property reads from,
        then waits for all those attrs to have no pending writes.
        """
        # Get the attrs this property reads from
        prop_meta = self._shared_meta['properties'].get(name, {})
        read_attrs = prop_meta.get('reads', [])
        
        # Build counter keys
        keys = [f"{self._object_name}.{attr}" for attr in read_attrs]
        
        # Wait for pending writes to complete
        if keys:
            self._coordinator.wait_for_read(keys, timeout=10.0)
        
        # Fetch current state and return the property value
        obj = self._coordinator.get_object(self._object_name)
        if obj is None:
            raise AttributeError(f"Object '{self._object_name}' not found")
        
        return getattr(obj, name)
    
    def _read_attr(self, name: str) -> Any:
        """
        Read an attr that's not in _shared_meta.
        
        Conservatively waits for ALL pending writes on this object,
        then fetches the current state.
        """
        # Get all pending counter keys for this object
        # This is conservative but safe
        all_keys = [
            key for key in self._coordinator._pending_counts.keys()
            if key.startswith(f"{self._object_name}.")
        ]
        
        if all_keys:
            self._coordinator.wait_for_read(all_keys, timeout=10.0)
        
        obj = self._coordinator.get_object(self._object_name)
        if obj is None:
            raise AttributeError(f"Object '{self._object_name}' not found")
        
        return getattr(obj, name)
    
    def __repr__(self) -> str:
        return f"Proxy({self._object_name}: {self._wrapped_class.__name__})"


class _MethodProxy:
    """
    Proxy for a method call on a shared object.
    
    When called, increments write counters and queues the command.
    Returns immediately (fire-and-forget).
    """
    
    def __init__(self, object_proxy: _ObjectProxy, method_name: str):
        self._object_proxy = object_proxy
        self._method_name = method_name
    
    def __call__(self, *args, **kwargs) -> None:
        """
        Queue the method call as a command.
        
        Increments pending counters for all attrs this method writes,
        then queues the command. Returns immediately.
        """
        proxy = self._object_proxy
        meta = proxy._shared_meta
        
        # Get the attrs this method writes to
        method_meta = meta['methods'].get(self._method_name, {})
        write_attrs = method_meta.get('writes', [])
        
        # Increment pending counters
        for attr in write_attrs:
            key = f"{proxy._object_name}.{attr}"
            proxy._coordinator.increment_pending(key)
        
        # Queue the command
        proxy._coordinator.queue_command(
            proxy._object_name,
            self._method_name,
            args,
            kwargs,
            write_attrs,
        )
    
    def __repr__(self) -> str:
        return f"MethodProxy({self._object_proxy._object_name}.{self._method_name})"
