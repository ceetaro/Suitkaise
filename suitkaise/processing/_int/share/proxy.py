"""
Share Proxy - Transparent wrapper for shared objects.

The proxy intercepts all access to shared objects:
- Method calls → increment counters, queue command, return immediately
- Property reads → wait for pending writes, fetch from source of truth
- Property writes → increment counters, queue command

Uses _shared_meta on the wrapped class to know which attrs each method/property touches.
"""

from typing import Any, Optional, TYPE_CHECKING
import warnings

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
    
    # attributes that belong to the proxy itself, not the wrapped object
    _PROXY_ATTRS = frozenset({
        '_object_name', '_coordinator', '_wrapped_class', '_shared_meta',
    })
    
    def __init__(
        self,
        object_name: str,
        coordinator: "_Coordinator",
        wrapped_class: type,
        shared_meta: Optional[dict] = None,
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
        
        # cache the _shared_meta if it exists
        meta = shared_meta if shared_meta is not None else getattr(wrapped_class, '_shared_meta', None)
        object.__setattr__(self, '_shared_meta', meta)
    
    def __getattr__(self, name: str) -> Any:
        """
        Intercept attribute access.
        
        - If it's a blocked method in _share_blocked_methods, raise TypeError
        - If it's a write method in _shared_meta, return a callable that queues commands
        - If it's a read-only method in _shared_meta, fetch object and return bound method
        - If it's a property in _shared_meta, wait for writes and return value
        - Otherwise, fetch from source of truth and return the attr
        """
        # check for methods that are explicitly blocked in Share
        blocked = getattr(self._wrapped_class, '_share_blocked_methods', None)
        if blocked and name in blocked:
            raise TypeError(blocked[name])

        if self._shared_meta and name in self._shared_meta.get('methods', {}):
            method_meta = self._shared_meta['methods'][name]
            if 'writes' in method_meta:
                # mutating method → fire-and-forget via coordinator
                return _MethodProxy(self, name)
            else:
                # read-only method → fetch fresh object and return bound method
                return getattr(self._fetch_object(), name)
        
        # properties in _shared_meta require read barriers before access
        if self._shared_meta and name in self._shared_meta.get('properties', {}):
            return self._read_property(name)
        
        # fallback: fetch object and get attr directly for untracked attrs
        return self._read_attr(name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Intercept attribute assignment.
        
        Proxy attrs are set directly. All others queue a setattr command.
        """
        if name in self._PROXY_ATTRS:
            object.__setattr__(self, name, value)
            return
        
        if not self._coordinator.is_alive:
            warnings.warn(
                "Share is stopped. Changes are queued but will not take "
                "effect until share.start() is called.",
                RuntimeWarning,
            )

        # queue a setattr command and mark the attr as written
        self._coordinator.increment_pending(f"{self._object_name}.{name}")
        self._coordinator.queue_command(
            self._object_name,
            '__setattr__',
            (name, value),
            {},
            [name],
        )
    
    # ── helpers ──────────────────────────────────────────────────────────

    def _fetch_object(self) -> Any:
        """
        Fetch the real object from source of truth, waiting for
        all pending writes on this object to complete first.
        """
        all_keys = self._coordinator.get_object_keys(self._object_name)
        if all_keys:
            self._coordinator.wait_for_read(all_keys, timeout=10.0)
        obj = self._coordinator.get_object(self._object_name)
        if obj is None:
            raise AttributeError(f"Object '{self._object_name}' not found in Share")
        return obj

    # ── dunder protocol methods ─────────────────────────────────────────
    # Python looks up special methods on the *type*, not the instance,
    # so __getattr__ never sees them. We define them explicitly so that
    # len(), iter(), in, indexing, etc. work on proxied builtins.

    def __len__(self) -> int:
        return len(self._fetch_object())

    def __iter__(self):
        return iter(self._fetch_object())

    def __contains__(self, item) -> bool:
        return item in self._fetch_object()

    def __bool__(self) -> bool:
        return bool(self._fetch_object())

    def __getitem__(self, key):
        return self._fetch_object()[key]

    def __setitem__(self, key, value):
        """Queue a __setitem__ write through the coordinator."""
        _MethodProxy(self, '__setitem__')(key, value)

    def __delitem__(self, key):
        """Queue a __delitem__ write through the coordinator."""
        _MethodProxy(self, '__delitem__')(key)

    def __str__(self) -> str:
        return str(self._fetch_object())

    # ── property reads ──────────────────────────────────────────────────

    def _read_property(self, name: str) -> Any:
        """
        Read a property, waiting for pending writes first.
        
        Uses _shared_meta to know which attrs the property reads from,
        then waits for all those attrs to have no pending writes.
        """
        # translate property read deps into counter keys
        prop_meta = self._shared_meta['properties'].get(name, {})
        read_attrs = prop_meta.get('reads', [])
        
        keys = [f"{self._object_name}.{attr}" for attr in read_attrs]
        
        # wait for all relevant writes to complete before reading
        if keys:
            self._coordinator.wait_for_read(keys, timeout=10.0)
        
        # fetch a fresh snapshot from the coordinator and read the property
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
        # unknown attrs: wait on all registered keys for this object
        all_keys = self._coordinator.get_object_keys(self._object_name)
        
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
        
        If the wrapped class defines _share_method_aliases, the actual
        method executed by the coordinator may differ from the one the
        user called (e.g. a no-sleep variant).
        """
        proxy = self._object_proxy
        
        if not proxy._coordinator.is_alive:
            warnings.warn(
                "Share is stopped. Changes are queued but will not take "
                "effect until share.start() is called.",
                RuntimeWarning,
            )
        meta = proxy._shared_meta
        
        # determine which attrs this method mutates (from _shared_meta)
        method_meta = meta['methods'].get(self._method_name, {})
        write_attrs = method_meta.get('writes', [])
        
        # increment pending counters before queueing so reads block properly
        for attr in write_attrs:
            key = f"{proxy._object_name}.{attr}"
            proxy._coordinator.increment_pending(key)
        
        # resolve method alias (e.g. 'short' → '_nosleep_short')
        aliases = getattr(proxy._wrapped_class, '_share_method_aliases', None)
        target_method = self._method_name
        if aliases and self._method_name in aliases:
            target_method = aliases[self._method_name]
        
        # queue the command to be executed by the coordinator process
        proxy._coordinator.queue_command(
            proxy._object_name,
            target_method,
            args,
            kwargs,
            write_attrs,
        )
    
    def __repr__(self) -> str:
        return f"MethodProxy({self._object_proxy._object_name}.{self._method_name})"
