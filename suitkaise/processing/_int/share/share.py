"""
Share api
"""

from typing import Any, Dict, Optional
import warnings
from multiprocessing.managers import SyncManager

from .coordinator import _Coordinator
from .proxy import _ObjectProxy

# import Skclass for auto-wrapping user objects (internal API)
from suitkaise.sk.api import Skclass


class Share:
    """
    ────────────────────────────────────────────────────────
        ```python
        from suitkaise import Share, Sktimer, Skprocess, Pool
        
        share = Share()
        share.timer = Sktimer() # complex objs work too
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

        if not object.__getattribute__(self, '_client_mode'):
            if not object.__getattribute__(self, '_started'):
                warnings.warn(
                    "Share is stopped. Changes are queued but will not take "
                    "effect until share.start() is called.",
                    RuntimeWarning,
                )
        
        # check if this is an object with _shared_meta (suitkaise or @sk wrapped)
        has_meta = hasattr(type(value), '_shared_meta')
        
        # if it's a user class instance without _shared_meta, auto-wrap with Skclass
        if not has_meta and self._is_user_class_instance(value):
            # apply Skclass to generate _shared_meta
            sk_wrapper = Skclass(type(value))
            # now the class has _shared_meta attached
            has_meta = True
        
        # register the object with the coordinator and compute read/write attrs
        #   for efficient barrier waits in the proxy
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
            # create a proxy for this object
            proxy = _ObjectProxy(name, self._coordinator, type(value))
            self._proxies[name] = proxy
        else:
            # no proxy - we'll fetch directly from source of truth
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

    def clear(self) -> None:
        """Clear all shared objects and counters."""
        self._coordinator.clear()
        self._proxies.clear()

    def __serialize__(self) -> dict:
        """
        Serialize Share without manager internals.
        
        Captures a snapshot of shared objects as cucumber bytes.
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
        from suitkaise import cucumber
        coordinator_state = None
        if object.__getattribute__(self, '_started'):
            # serialize coordinator state separately to avoid proxy pickling issues
            coordinator_state = cucumber.serialize(coordinator.get_state())
        return {
            "mode": "live" if object.__getattribute__(self, '_started') else "snapshot",
            "objects": objects,
            "started": object.__getattribute__(self, '_started'),
            "coordinator_state": coordinator_state,
        }

    @staticmethod
    def __deserialize__(state: dict) -> "Share":
        """
        Reconstruct Share from serialized snapshot.
        """
        from suitkaise.cucumber._int.deserializer import Deserializer
        deserializer = Deserializer()
        coordinator_state = state.get("coordinator_state")
        if coordinator_state:
            coordinator = _Coordinator.from_state(deserializer.deserialize(coordinator_state))
            share = Share(
                manager=None,
                auto_start=False,
                client_mode=True,
                coordinator=coordinator,
            )
            object.__setattr__(share, '_started', True)
        else:
            share = Share()

        for name, serialized in state.get("objects", {}).items():
            try:
                obj = deserializer.deserialize(serialized)
            except Exception:
                continue
            setattr(share, name, obj)
        if state.get("started") and not object.__getattribute__(share, '_client_mode'):
            share.start()
        return share
