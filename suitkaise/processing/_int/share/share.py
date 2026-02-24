"""
Share api
"""

from typing import Any, Dict, Optional
import io
import threading
import weakref
import warnings
from multiprocessing.managers import SyncManager

from .coordinator import _Coordinator
from .proxy import _ObjectProxy

# import Skclass for auto-wrapping user objects (internal API)
from suitkaise.sk._int.analyzer import analyze_class

_NON_PROXY_CUCUMBER_HANDLERS = {
    "SQLiteConnectionHandler",
    "SQLiteCursorHandler",
    "SocketHandler",
    "DatabaseConnectionHandler",
    "ThreadHandler",
    "PopenHandler",
    "MatchObjectHandler",
    "MultiprocessingPipeHandler",
    "MultiprocessingManagerHandler",
    "LoggerHandler",
}


# ── Built-in mutable type metadata ──────────────────────────────────────
# Since we can't set _shared_meta on built-in types, we keep a registry.
# 'writes' = mutating attrs (fire-and-forget via proxy)
# 'reads'  = read-only attrs (fetched from source of truth)
_BUILTIN_SHARED_META: dict[type, dict] = {
    list: {
        'methods': {
            # mutating (fire-and-forget)
            'append':  {'writes': ['_data']},
            'extend':  {'writes': ['_data']},
            'insert':  {'writes': ['_data']},
            'remove':  {'writes': ['_data']},
            'pop':     {'writes': ['_data']},
            'clear':   {'writes': ['_data']},
            'sort':    {'writes': ['_data']},
            'reverse': {'writes': ['_data']},
            '__setitem__': {'writes': ['_data']},
            '__delitem__': {'writes': ['_data']},
            # read-only (return values directly)
            'copy':  {'reads': ['_data']},
            'count': {'reads': ['_data']},
            'index': {'reads': ['_data']},
        },
        'properties': {},
    },
    set: {
        'methods': {
            # mutating
            'add':     {'writes': ['_data']},
            'discard': {'writes': ['_data']},
            'remove':  {'writes': ['_data']},
            'pop':     {'writes': ['_data']},
            'clear':   {'writes': ['_data']},
            'update':  {'writes': ['_data']},
            'intersection_update':        {'writes': ['_data']},
            'difference_update':          {'writes': ['_data']},
            'symmetric_difference_update': {'writes': ['_data']},
            # read-only
            'copy':                 {'reads': ['_data']},
            'issubset':             {'reads': ['_data']},
            'issuperset':           {'reads': ['_data']},
            'union':                {'reads': ['_data']},
            'intersection':         {'reads': ['_data']},
            'difference':           {'reads': ['_data']},
            'symmetric_difference': {'reads': ['_data']},
        },
        'properties': {},
    },
    dict: {
        'methods': {
            # mutating
            'update':     {'writes': ['_data']},
            'pop':        {'writes': ['_data']},
            'popitem':    {'writes': ['_data']},
            'clear':      {'writes': ['_data']},
            'setdefault': {'writes': ['_data']},
            '__setitem__': {'writes': ['_data']},
            '__delitem__': {'writes': ['_data']},
            # read-only
            'get':    {'reads': ['_data']},
            'keys':   {'reads': ['_data']},
            'values': {'reads': ['_data']},
            'items':  {'reads': ['_data']},
            'copy':   {'reads': ['_data']},
        },
        'properties': {},
    },
}

_PRIMITIVE_PROXY_TYPES: tuple[type, ...] = (
    int, float, bool, str, bytes, complex, tuple, frozenset,
)


class _PrimitiveProxy:
    """Proxy for primitive shared values without _shared_meta."""

    __slots__ = ("_object_name", "_coordinator", "_local")

    def __init__(self, object_name: str, coordinator: _Coordinator):
        self._object_name = object_name
        self._coordinator = coordinator
        self._local = threading.local()

    def _unwrap_other(self, value: Any) -> Any:
        if isinstance(value, _PrimitiveProxy):
            return value._value()
        return value

    def _set_local_override(self, value: Any) -> None:
        self._local.override = value

    def _consume_local_override(self) -> Any:
        if hasattr(self._local, "override"):
            value = self._local.override
            del self._local.override
            return value
        return None

    def _value(self) -> Any:
        override = self._consume_local_override()
        if override is not None:
            return override
        value = self._coordinator.get_object(self._object_name)
        if value is None and not self._coordinator.has_object(self._object_name):
            raise AttributeError(f"Object '{self._object_name}' not found in Share")
        return value

    def _atomic_apply(self, operation: str, operand: Any = None) -> "_PrimitiveProxy":
        operand = self._unwrap_other(operand)
        updated = self._coordinator.atomic_apply(self._object_name, operation, operand)
        if updated is None and not self._coordinator.has_object(self._object_name):
            raise AttributeError(f"Object '{self._object_name}' not found in Share")
        # make the next read in this worker observe its own write result
        self._set_local_override(updated)
        return self

    def __repr__(self) -> str:
        return repr(self._value())

    def __str__(self) -> str:
        return str(self._value())

    def __format__(self, format_spec: str) -> str:
        return format(self._value(), format_spec)

    def __len__(self) -> int:
        return len(self._value())

    def __iter__(self):
        return iter(self._value())

    def __contains__(self, item: Any) -> bool:
        return item in self._value()

    def __getitem__(self, key: Any) -> Any:
        return self._value()[key]

    def __bool__(self) -> bool:
        return bool(self._value())

    def __int__(self) -> int:
        return int(self._value())

    def __float__(self) -> float:
        return float(self._value())

    def __complex__(self) -> complex:
        return complex(self._value())

    def __bytes__(self) -> bytes:
        return bytes(self._value())

    def __index__(self) -> int:
        return self._value().__index__()

    def __hash__(self) -> int:
        return hash(self._value())

    def __getattr__(self, name: str) -> Any:
        return getattr(self._value(), name)

    def __lt__(self, other: Any) -> bool:
        return self._value() < self._unwrap_other(other)

    def __le__(self, other: Any) -> bool:
        return self._value() <= self._unwrap_other(other)

    def __eq__(self, other: Any) -> bool:
        return self._value() == self._unwrap_other(other)

    def __ne__(self, other: Any) -> bool:
        return self._value() != self._unwrap_other(other)

    def __gt__(self, other: Any) -> bool:
        return self._value() > self._unwrap_other(other)

    def __ge__(self, other: Any) -> bool:
        return self._value() >= self._unwrap_other(other)

    def __add__(self, other: Any) -> Any:
        return self._value() + self._unwrap_other(other)

    def __radd__(self, other: Any) -> Any:
        return self._unwrap_other(other) + self._value()

    def __sub__(self, other: Any) -> Any:
        return self._value() - self._unwrap_other(other)

    def __rsub__(self, other: Any) -> Any:
        return self._unwrap_other(other) - self._value()

    def __mul__(self, other: Any) -> Any:
        return self._value() * self._unwrap_other(other)

    def __rmul__(self, other: Any) -> Any:
        return self._unwrap_other(other) * self._value()

    def __truediv__(self, other: Any) -> Any:
        return self._value() / self._unwrap_other(other)

    def __rtruediv__(self, other: Any) -> Any:
        return self._unwrap_other(other) / self._value()

    def __floordiv__(self, other: Any) -> Any:
        return self._value() // self._unwrap_other(other)

    def __rfloordiv__(self, other: Any) -> Any:
        return self._unwrap_other(other) // self._value()

    def __mod__(self, other: Any) -> Any:
        return self._value() % self._unwrap_other(other)

    def __rmod__(self, other: Any) -> Any:
        return self._unwrap_other(other) % self._value()

    def __pow__(self, other: Any) -> Any:
        return self._value() ** self._unwrap_other(other)

    def __rpow__(self, other: Any) -> Any:
        return self._unwrap_other(other) ** self._value()

    def __and__(self, other: Any) -> Any:
        return self._value() & self._unwrap_other(other)

    def __rand__(self, other: Any) -> Any:
        return self._unwrap_other(other) & self._value()

    def __or__(self, other: Any) -> Any:
        return self._value() | self._unwrap_other(other)

    def __ror__(self, other: Any) -> Any:
        return self._unwrap_other(other) | self._value()

    def __xor__(self, other: Any) -> Any:
        return self._value() ^ self._unwrap_other(other)

    def __rxor__(self, other: Any) -> Any:
        return self._unwrap_other(other) ^ self._value()

    def __lshift__(self, other: Any) -> Any:
        return self._value() << self._unwrap_other(other)

    def __rlshift__(self, other: Any) -> Any:
        return self._unwrap_other(other) << self._value()

    def __rshift__(self, other: Any) -> Any:
        return self._value() >> self._unwrap_other(other)

    def __rrshift__(self, other: Any) -> Any:
        return self._unwrap_other(other) >> self._value()

    def __matmul__(self, other: Any) -> Any:
        return self._value() @ self._unwrap_other(other)

    def __rmatmul__(self, other: Any) -> Any:
        return self._unwrap_other(other) @ self._value()

    def __pos__(self) -> Any:
        return +self._value()

    def __neg__(self) -> Any:
        return -self._value()

    def __invert__(self) -> Any:
        return ~self._value()

    def __iadd__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("iadd", other)

    def __isub__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("isub", other)

    def __imul__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("imul", other)

    def __itruediv__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("itruediv", other)

    def __ifloordiv__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("ifloordiv", other)

    def __imod__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("imod", other)

    def __ipow__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("ipow", other)

    def __ilshift__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("ilshift", other)

    def __irshift__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("irshift", other)

    def __iand__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("iand", other)

    def __ixor__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("ixor", other)

    def __ior__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("ior", other)

    def __imatmul__(self, other: Any) -> "_PrimitiveProxy":
        return self._atomic_apply("imatmul", other)


class Share:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import Share, Sktimer, Skprocess, Pool
        
        share = Share()
        share.timer = Sktimer() # use add_time() to aggregate across processes
        share.counter = 0

        class ProcessUsingShare(Skprocess):

            def __init__(self, share: Share):

                self.share = share
                self.process_config.runs = 10

            def __run__(self):

                # ...

            def __postrun__(self):

                self.share.counter += 1

        
        pool = Pool(workers=2)
        results = pool.map(ProcessUsingShare, [share] * 10)

        assert share.counter == 100 # 10 processes, 10 runs each
        ```
    ────────────────────────────────────────────────────────\n

    Container for shared memory across process boundaries.
    
    Uses a coordinator-proxy system to ensure that all reads
    and writes happen in the order they are supposed to.

    All you have to do is:
    1. Create a Share instance
    2. Add objects as Share attributes (share.counter = 0)
    3. Pass the Share instance to whatever you want to share it with
    4. update objects as normal
    
    This works by automatically calculating a `_shared_meta` for each
    object as it gets added to the Share instance.

    Share uses memory and resources to run.
    To stop sharing, call `Share.stop()` or `Share.exit()`.

    While stopped, changes are queued but will not take effect until sharing is started again.
    A warning will be issued if you try to access or update, or add a new object to the Share instance
    while it is not running.

    To start sharing again, call `Share.start()`.

    Context manager support:
    ```python
    with Share() as share:
        # on entry, starts up Share
        share.counter += 1

    # on exit, stops Share
    ```
    """
    
    # attrs that belong to Share itself, not shared objects
    _SHARE_ATTRS = frozenset({
        '_coordinator', '_proxies', '_started',
    })
    _META_CACHE: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
    
    def __init__(
        self,
        manager: Optional[SyncManager] = None,
        *,
        auto_start: bool = True,
        client_mode: bool = False,
        coordinator: Optional[_Coordinator] = None,
    ):
        """
        Create a new Share container.
        
        Args:
            manager: Optional SyncManager to use. Creates one if not provided.
        """
        object.__setattr__(self, '_coordinator', coordinator or _Coordinator(manager))
        object.__setattr__(self, '_proxies', {})  # name -> proxy
        object.__setattr__(self, '_started', False)
        object.__setattr__(self, '_client_mode', client_mode)
        # auto-start coordinator on creation
        if auto_start and not client_mode:
            self.start()
    
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Assign an object to be shared.
        
        - Objects with _shared_meta get wrapped in a proxy
        - User class instances without _shared_meta are auto-wrapped with Skclass
        - Primitives (int, str, etc.) are stored directly in source of truth
        """
        if name in self._SHARE_ATTRS:
            # internal attributes are stored directly on the Share instance
            object.__setattr__(self, name, value)
            return

        if isinstance(value, _PrimitiveProxy):
            # Augmented assignment on primitive proxies (e.g. share.x += 1)
            # stores back the proxy object; the atomic update already happened.
            if name in self._proxies and value._object_name == name:
                return
            value = value._value()

        if not object.__getattribute__(self, '_client_mode'):
            if not object.__getattribute__(self, '_started'):
                warnings.warn(
                    "Share is stopped. Changes are queued but will not take "
                    "effect until share.start() is called.",
                    RuntimeWarning,
                )

        # check for objects that explicitly disallow Share usage
        disallowed_msg = getattr(type(value), '_share_disallowed', None)
        if disallowed_msg:
            raise TypeError(disallowed_msg)

        obj_module = getattr(type(value), "__module__", "")
        if obj_module.startswith("multiprocessing"):
            raise ValueError(
                "Share does not support multiprocessing.* objects. "
                "Use Share primitives or plain data instead."
            )
        if isinstance(value, io.IOBase):
            try:
                file_name = getattr(value, "name", None)
            except Exception:
                file_name = None
            if isinstance(file_name, int):
                raise ValueError(
                    "Share does not support os.pipe() file handles. "
                    "Use Share primitives or Suitkaise Pipe instead."
                )
        
        # check if this is an object with _shared_meta (suitkaise or @sk wrapped)
        meta = getattr(type(value), '_shared_meta', None)
        
        # check built-in mutable types (list, set, dict)
        if meta is None:
            meta = _BUILTIN_SHARED_META.get(type(value))
        
        # if it's a user class instance without _shared_meta, auto-generate meta
        if meta is None and self._is_user_class_instance(value):
            meta = self._ensure_shared_meta(type(value))
        has_meta = meta is not None
        
        # register the object with the coordinator and compute read/write attrs
        #   for efficient barrier waits in the proxy
        attrs: set[str] = set()
        if has_meta:
            for method_meta in meta.get('methods', {}).values():
                attrs.update(method_meta.get('writes', []))
                attrs.update(method_meta.get('reads', []))
            for prop_meta in meta.get('properties', {}).values():
                attrs.update(prop_meta.get('reads', []))
                attrs.update(prop_meta.get('writes', []))
        self._coordinator.register_object(name, value, attrs=attrs if attrs else None)

        should_proxy = has_meta
        if should_proxy:
            handler = self._get_cucumber_handler(value)
            if handler and handler.__class__.__name__ in _NON_PROXY_CUCUMBER_HANDLERS:
                should_proxy = False
        if should_proxy:
            # create a proxy for this object
            proxy = _ObjectProxy(name, self._coordinator, type(value), shared_meta=meta)
            self._proxies[name] = proxy
        else:
            # immutable primitives still get lightweight proxies so augmented
            # assignment operators can apply atomically in the coordinator.
            if isinstance(value, _PRIMITIVE_PROXY_TYPES):
                self._proxies[name] = _PrimitiveProxy(name, self._coordinator)
            else:
                self._proxies[name] = None
    
    def _is_user_class_instance(self, value: Any) -> bool:
        """
        Check if value is an instance of a user-defined class.
        
        Returns False for primitives, builtins, and known non-shareable types.
        """
        # skip primitives and builtins
        if isinstance(value, (
            int, float, str, bytes, bool, type(None),
            list, dict, tuple, set, frozenset,
        )):
            return False
        
        # it's a class instance
        return True

    def _ensure_shared_meta(self, cls: type) -> dict:
        """
        Generate and attach _shared_meta for a class if possible.
        """
        cached = self._META_CACHE.get(cls)
        if cached is not None:
            return cached
        try:
            meta, _ = analyze_class(cls)
        except Exception:
            meta = {'methods': {}, 'properties': {}}
        self._META_CACHE[cls] = meta
        try:
            setattr(cls, '_shared_meta', meta)
        except (TypeError, AttributeError):
            pass
        return meta

    def _get_cucumber_handler(self, value: Any) -> Any | None:
        """
        Check whether cucumber already has a dedicated handler for this object.
        """
        try:
            from suitkaise.cucumber._int.serializer import Serializer
            serializer = Serializer()
            return serializer._find_handler(value)
        except Exception:
            return None

    def _build_proxy_for(self, name: str, obj: Any) -> Any:
        """
        Build and cache the appropriate proxy entry for a shared object.
        """
        meta = getattr(type(obj), '_shared_meta', None)
        if meta is None:
            meta = _BUILTIN_SHARED_META.get(type(obj))
        if meta is None and self._is_user_class_instance(obj):
            meta = self._ensure_shared_meta(type(obj))

        should_proxy = meta is not None
        if should_proxy:
            handler = self._get_cucumber_handler(obj)
            if handler and handler.__class__.__name__ in _NON_PROXY_CUCUMBER_HANDLERS:
                should_proxy = False

        if should_proxy:
            proxy = _ObjectProxy(name, self._coordinator, type(obj), shared_meta=meta)
        elif isinstance(obj, _PRIMITIVE_PROXY_TYPES):
            proxy = _PrimitiveProxy(name, self._coordinator)
        else:
            proxy = None
        self._proxies[name] = proxy
        return proxy
    
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
            coordinator = object.__getattribute__(self, '_coordinator')
            if coordinator.has_object(name):
                obj = coordinator.get_object(name)
                if obj is None:
                    raise AttributeError(f"Object '{name}' not found in Share")
                proxy = self._build_proxy_for(name, obj)
                if proxy is not None:
                    return proxy
                return obj
            raise AttributeError(f"Share has no attribute '{name}'")
        
        proxy = proxies[name]
        if proxy is not None:
            # proxy handles read/write barriers and command queueing
            return proxy
        
        # no proxy - fetch directly from source of truth (serialized state)
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
            # remove local proxy first to avoid future access
            del self._proxies[name]
            coordinator = object.__getattribute__(self, '_coordinator')
            # drop coordinator state so the object can't be resurrected
            coordinator.remove_object(name)
    
    def start(self) -> None:
        """
        ────────────────────────────────────────────────────────
            ```python
            # auto starts on creation
            share = Share()

            # is stopped
            share.exit() # or share.stop()

            # use start() to start sharing again
            share.start()
            ```
        ────────────────────────────────────────────────────────\n

        Start the coordinator process up again.
        """
        if object.__getattribute__(self, '_client_mode'):
            return
        if not self._started:
            self._coordinator.start()
            object.__setattr__(self, '_started', True)
    
    def stop(self, timeout: float = 5.0) -> bool:
        """
        ────────────────────────────────────────────────────────
            ```python
            # auto starts on creation
            share = Share()

            # stop using stop()
            share.stop(timeout=5.0) # or share.exit()
            ```
        ────────────────────────────────────────────────────────\n
        Stop the coordinator process.
        
        Args:
            timeout: Maximum seconds to wait for shutdown.
        
        Returns:
            True if stopped cleanly, False if timed out.
        """
        if object.__getattribute__(self, '_client_mode'):
            return True
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

    def __del__(self) -> None:
        """Destroy the coordinator on garbage collection to prevent resource leaks."""
        try:
            if not object.__getattribute__(self, '_client_mode'):
                coordinator = object.__getattribute__(self, '_coordinator')
                coordinator.destroy()
        except Exception:
            pass

    def clear(self) -> None:
        """Clear all shared objects and counters."""
        self._coordinator.clear()
        self._proxies.clear()

    def reconnect_all(self, *, start_threads: bool = False, **auth) -> Dict[str, Any]:
        """
        Reconnect all Reconnectors currently stored in Share.

        Uses cucumber.reconnect_all() against each stored object snapshot and
        returns the reconnected values keyed by object name.
        """
        from suitkaise import cucumber

        try:
            names = list(self._coordinator._object_names)
        except Exception:
            names = []

        results: Dict[str, Any] = {}
        for name in names:
            try:
                obj = self._coordinator.get_object(name)
            except Exception:
                continue
            if obj is None:
                continue
            reconnected = cucumber.reconnect_all(obj, start_threads=start_threads, **auth)
            results[name] = reconnected
        return results

    def __serialize__(self) -> dict:
        """
        Serialize Share without manager internals.
        
        Captures a snapshot of shared objects as cucumber bytes.
        """
        import pickle
        coordinator = object.__getattribute__(self, '_coordinator')
        started = object.__getattribute__(self, '_started')
        objects: Dict[str, bytes] = {}
        if not started:
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
        coordinator_state = None
        if started:
            # pickle raw manager proxies to preserve Share internals
            coordinator_state = pickle.dumps(coordinator.get_state())
        return {
            "mode": "live" if started else "snapshot",
            "objects": objects,
            "started": started,
            "coordinator_state": coordinator_state,
        }

    @staticmethod
    def __deserialize__(state: dict) -> "Share":
        """
        Reconstruct Share from serialized snapshot.
        """
        import pickle
        from suitkaise.cucumber._int.deserializer import Deserializer
        deserializer = Deserializer()
        coordinator_state = state.get("coordinator_state")
        if coordinator_state:
            if isinstance(coordinator_state, (bytes, bytearray)):
                coordinator_state = pickle.loads(coordinator_state)
            else:
                coordinator_state = deserializer.deserialize(coordinator_state)
            coordinator = _Coordinator.from_state(coordinator_state)
            share = Share(
                manager=None,
                auto_start=False,
                client_mode=True,
                coordinator=coordinator,
            )
            object.__setattr__(share, '_started', True)
        else:
            share = Share()

        def _restore_snapshot(name: str, serialized_obj: bytes, obj: Any) -> None:
            coordinator = object.__getattribute__(share, '_coordinator')
            proxies = object.__getattribute__(share, '_proxies')
            meta = getattr(type(obj), '_shared_meta', None)
            if meta is None:
                meta = _BUILTIN_SHARED_META.get(type(obj))
            if meta is None and share._is_user_class_instance(obj):
                meta = share._ensure_shared_meta(type(obj))

            should_proxy = meta is not None
            if should_proxy:
                handler = share._get_cucumber_handler(obj)
                if handler and handler.__class__.__name__ in _NON_PROXY_CUCUMBER_HANDLERS:
                    should_proxy = False

            if should_proxy:
                proxies[name] = _ObjectProxy(name, coordinator, type(obj), shared_meta=meta)
            else:
                if isinstance(obj, _PRIMITIVE_PROXY_TYPES):
                    proxies[name] = _PrimitiveProxy(name, coordinator)
                else:
                    proxies[name] = None

            # In client mode (workers connected to parent coordinator), never
            # clobber existing shared state with deserialized snapshots.
            should_seed_state = (
                not object.__getattribute__(share, '_client_mode')
                or not coordinator.has_object(name)
            )
            if should_seed_state:
                try:
                    with coordinator._source_lock:
                        coordinator._source_store[name] = serialized_obj
                except Exception:
                    try:
                        coordinator._source_store[name] = serialized_obj
                    except Exception:
                        pass
                try:
                    if name not in list(coordinator._object_names):
                        coordinator._object_names.append(name)
                except Exception:
                    pass

        for name, serialized in state.get("objects", {}).items():
            try:
                obj = deserializer.deserialize(serialized)
            except Exception:
                continue
            if object.__getattribute__(share, '_client_mode'):
                _restore_snapshot(name, serialized, obj)
            else:
                setattr(share, name, obj)
        if state.get("started") and not object.__getattribute__(share, '_client_mode'):
            share.start()
        return share
