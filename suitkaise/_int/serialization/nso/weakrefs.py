"""
Weak References Serialization Handler

This module provides serialization support for weak reference objects that
cannot be pickled due to their special handling of object references and
automatic cleanup behavior.

SUPPORTED OBJECTS:
==================

1. WEAK REFERENCES:
   - weakref.ref objects
   - References to arbitrary objects with optional callbacks
   - Dead weak references (referent has been garbage collected)

2. WEAK PROXIES:
   - weakref.proxy objects
   - Callable and non-callable proxies
   - Proxy objects that behave like the referenced object

3. WEAK KEY/VALUE DICTIONARIES:
   - weakref.WeakKeyDictionary objects
   - weakref.WeakValueDictionary objects
   - weakref.WeakSet objects

4. WEAK METHOD REFERENCES:
   - weakref.WeakMethod objects (Python 3.4+)
   - Bound method references that don't prevent garbage collection

5. WEAK REFERENCE CALLBACKS:
   - Callback functions registered with weak references
   - Cleanup functions for when referents are collected

SERIALIZATION STRATEGY:
======================

Weak reference serialization is challenging because:
- Weak references don't prevent garbage collection
- The referenced object might be collected between serialize/deserialize
- Callbacks are functions that may not be serializable themselves
- Proxies behave like their referents but aren't the actual objects

Our approach:
1. **Store referent information** when the referent is still alive
2. **Handle dead references** with appropriate placeholders
3. **Preserve callback information** when callbacks are serializable
4. **Recreate weak references** to equivalent objects when possible
5. **Provide clear warnings** about weak reference limitations

LIMITATIONS:
============
- Referent objects might be garbage collected, making recreation impossible
- Callbacks that aren't serializable are lost
- Weak references to the same object may not maintain identity after recreation
- Timing issues may cause different garbage collection behavior
- Weak proxies lose their proxy behavior and become regular references

"""

import weakref
import gc
import sys
from typing import Any, Dict, Optional, List, Union, Callable

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class WeakReferencesHandler(_NSO_Handler):
    """Handler for weak reference objects and related weak reference types."""
    
    def __init__(self):
        """Initialize the weak references handler."""
        super().__init__()
        self._handler_name = "WeakReferencesHandler"
        self._priority = 25  # High priority since weak refs are common in frameworks
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given weak reference object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for weakref.ref objects
        - Check for weakref.proxy objects
        - Check for WeakKeyDictionary, WeakValueDictionary, WeakSet
        - Check for WeakMethod objects (Python 3.4+)
        - Check for other weakref module types
        """
        try:
            # Weak reference objects
            if isinstance(obj, weakref.ref):
                return True
            
            # Weak proxy objects
            if isinstance(obj, weakref.ProxyType):
                return True
            if isinstance(obj, weakref.CallableProxyType):
                return True
            
            # Weak collections
            if isinstance(obj, weakref.WeakKeyDictionary):
                return True
            if isinstance(obj, weakref.WeakValueDictionary):
                return True
            if isinstance(obj, weakref.WeakSet):
                return True
            
            # WeakMethod (Python 3.4+)
            if hasattr(weakref, 'WeakMethod') and isinstance(obj, weakref.WeakMethod):
                return True
            
            # Check by type name for other weakref objects
            obj_type_name = type(obj).__name__
            obj_module = getattr(type(obj), '__module__', '')
            
            if 'weakref' in obj_module and obj_type_name in [
                'ref', 'proxy', 'WeakKeyDictionary', 'WeakValueDictionary', 
                'WeakSet', 'WeakMethod'
            ]:
                return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a weak reference object to a dictionary representation.
        
        Args:
            obj: Weak reference object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the object
            
        SERIALIZATION PROCESS:
        1. Determine weak reference type
        2. Check if referent is still alive
        3. Extract referent information and metadata
        4. Handle callbacks when possible
        5. Store collection contents for weak collections
        """
        # Base serialization data
        data = {
            "weakref_type": self._get_weakref_type(obj),
            "object_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "serialization_strategy": None,  # Will be determined below
            "recreation_possible": False,
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        weakref_type = data["weakref_type"]
        
        if weakref_type == "ref":
            data.update(self._serialize_ref(obj))
            data["serialization_strategy"] = "ref_recreation"
            
        elif weakref_type == "proxy":
            data.update(self._serialize_proxy(obj))
            data["serialization_strategy"] = "proxy_recreation"
            
        elif weakref_type == "weak_key_dict":
            data.update(self._serialize_weak_key_dict(obj))
            data["serialization_strategy"] = "weak_key_dict_recreation"
            
        elif weakref_type == "weak_value_dict":
            data.update(self._serialize_weak_value_dict(obj))
            data["serialization_strategy"] = "weak_value_dict_recreation"
            
        elif weakref_type == "weak_set":
            data.update(self._serialize_weak_set(obj))
            data["serialization_strategy"] = "weak_set_recreation"
            
        elif weakref_type == "weak_method":
            data.update(self._serialize_weak_method(obj))
            data["serialization_strategy"] = "weak_method_recreation"
            
        else:
            # Unknown weak reference type
            data.update(self._serialize_unknown_weakref(obj))
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a weak reference object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized weak reference data
            
        Returns:
            Recreated weak reference object (with limitations noted in documentation)
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Restore weak reference with available referent information
        4. Handle errors gracefully with placeholders
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        weakref_type = data.get("weakref_type", "unknown")
        
        try:
            if strategy == "ref_recreation":
                return self._deserialize_ref(data)
            
            elif strategy == "proxy_recreation":
                return self._deserialize_proxy(data)
            
            elif strategy == "weak_key_dict_recreation":
                return self._deserialize_weak_key_dict(data)
            
            elif strategy == "weak_value_dict_recreation":
                return self._deserialize_weak_value_dict(data)
            
            elif strategy == "weak_set_recreation":
                return self._deserialize_weak_set(data)
            
            elif strategy == "weak_method_recreation":
                return self._deserialize_weak_method(data)
            
            elif strategy == "fallback_placeholder":
                return self._deserialize_unknown_weakref(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a placeholder
            return self._create_error_placeholder(weakref_type, str(e))
    
    # ========================================================================
    # WEAK REFERENCE TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_weakref_type(self, obj: Any) -> str:
        """
        Determine the specific type of weak reference object.
        
        Args:
            obj: Weak reference object to analyze
            
        Returns:
            String identifying the weak reference type
        """
        if isinstance(obj, weakref.ref):
            return "ref"
        elif isinstance(obj, (weakref.ProxyType, weakref.CallableProxyType)):
            return "proxy"
        elif isinstance(obj, weakref.WeakKeyDictionary):
            return "weak_key_dict"
        elif isinstance(obj, weakref.WeakValueDictionary):
            return "weak_value_dict"
        elif isinstance(obj, weakref.WeakSet):
            return "weak_set"
        elif hasattr(weakref, 'WeakMethod') and isinstance(obj, weakref.WeakMethod):
            return "weak_method"
        else:
            return "unknown"
    
    # ========================================================================
    # WEAK REFERENCE SERIALIZATION
    # ========================================================================
    
    def _serialize_ref(self, ref_obj: weakref.ref) -> Dict[str, Any]:
        """
        Serialize weakref.ref objects.
        
        Extract referent information and callback details.
        """
        result = {
            "referent_alive": False,
            "referent_info": None,
            "callback_info": None,
            "is_dead": False
        }
        
        try:
            # Try to get the referent
            referent = ref_obj()
            
            if referent is not None:
                result["referent_alive"] = True
                result["referent_info"] = {
                    "type": f"{type(referent).__module__}.{type(referent).__name__}",
                    "repr": repr(referent)[:100],  # Truncated representation
                    "id": id(referent),
                    "has_weakref_slot": hasattr(type(referent), '__weakref__')
                }
                
                # For simple types, store the actual value
                if isinstance(referent, (int, float, str, bool, bytes, type(None))):
                    result["referent_info"]["value"] = referent
                    result["referent_info"]["is_simple_type"] = True
                else:
                    result["referent_info"]["is_simple_type"] = False
            else:
                result["is_dead"] = True
                result["referent_info"] = {"dead_reference": True}
            
            # Try to get callback information
            # Note: weakref doesn't provide direct access to callbacks,
            # but we can try to detect if there is one
            try:
                # This is a workaround - create a test weak reference to see
                # if callbacks are supported with this referent type
                if referent is not None:
                    test_ref = weakref.ref(referent, lambda x: None)
                    test_ref = None  # Clean up
                    result["callback_info"] = {"callback_supported": True}
            except (TypeError, AttributeError):
                result["callback_info"] = {"callback_supported": False}
                
        except Exception as e:
            result["note"] = f"Error accessing weak reference: {e}"
            result["is_dead"] = True
        
        result["recreation_possible"] = (
            result["referent_alive"] and 
            result["referent_info"] and 
            result["referent_info"].get("has_weakref_slot", False)
        )
        
        if result["is_dead"]:
            result["limitation"] = "Original referent was garbage collected - cannot recreate"
        elif not result["recreation_possible"]:
            result["limitation"] = "Referent type does not support weak references"
        else:
            result["limitation"] = "Weak reference will point to a new instance if referent is recreated"
        
        return result
    
    def _deserialize_ref(self, data: Dict[str, Any]) -> weakref.ref:
        """
        Deserialize weakref.ref objects.
        
        Create new weak reference to equivalent object when possible.
        """
        referent_info = data.get("referent_info", {})
        is_dead = data.get("is_dead", False)
        
        if is_dead or referent_info.get("dead_reference"):
            # Create a dead weak reference
            # This is tricky because we can't create a dead weak reference directly
            # We'll create a reference to a temporary object and let it die
            temp_obj = object()
            weak_ref = weakref.ref(temp_obj)
            del temp_obj  # This should make the weak reference dead
            return weak_ref
        
        if referent_info.get("is_simple_type", False):
            # For simple types, recreate the value and create weak reference
            value = referent_info.get("value")
            if value is not None:
                try:
                    # Note: Most simple types don't support weak references
                    # This will likely fail, but we try anyway
                    return weakref.ref(value)
                except TypeError:
                    # Simple types usually don't support weak references
                    pass
        
        # For complex types, we can't recreate the exact object
        # Create a placeholder object that supports weak references
        class WeakRefPlaceholder:
            def __init__(self, original_type, original_repr):
                self.original_type = original_type
                self.original_repr = original_repr
            
            def __repr__(self):
                return f"<WeakRefPlaceholder for {self.original_type}>"
        
        original_type = referent_info.get("type", "unknown")
        original_repr = referent_info.get("repr", "unknown")
        placeholder = WeakRefPlaceholder(original_type, original_repr)
        
        try:
            return weakref.ref(placeholder)
        except TypeError:
            # If even our placeholder doesn't work, return a callable that
            # always returns None (simulating a dead reference)
            return lambda: None
    
    # ========================================================================
    # WEAK PROXY SERIALIZATION
    # ========================================================================
    
    def _serialize_proxy(self, proxy_obj) -> Dict[str, Any]:
        """
        Serialize weakref.proxy objects.
        
        Extract referent information and proxy type.
        """
        result = {
            "proxy_type": "unknown",
            "referent_alive": False,
            "referent_info": None,
            "is_callable": False
        }
        
        try:
            # Determine proxy type
            if isinstance(proxy_obj, weakref.CallableProxyType):
                result["proxy_type"] = "callable"
                result["is_callable"] = True
            elif isinstance(proxy_obj, weakref.ProxyType):
                result["proxy_type"] = "non_callable"
                result["is_callable"] = False
            
            # Try to access the proxy to get referent info
            # This is tricky because proxies behave like their referents
            try:
                # Get type information
                result["referent_info"] = {
                    "type": f"{type(proxy_obj).__module__}.{type(proxy_obj).__name__}",
                    "repr": repr(proxy_obj)[:100],
                    "callable": callable(proxy_obj)
                }
                result["referent_alive"] = True
                
            except ReferenceError:
                # Proxy's referent is dead
                result["referent_alive"] = False
                result["referent_info"] = {"dead_proxy": True}
                
        except Exception as e:
            result["note"] = f"Error accessing weak proxy: {e}"
        
        result["recreation_possible"] = result["referent_alive"]
        result["limitation"] = "Proxy will be recreated as regular weak reference, not proxy"
        
        return result
    
    def _deserialize_proxy(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize weakref.proxy objects.
        
        Create placeholder object and return weak reference (not proxy).
        """
        referent_alive = data.get("referent_alive", False)
        referent_info = data.get("referent_info", {})
        is_callable = data.get("is_callable", False)
        
        if not referent_alive or referent_info.get("dead_proxy"):
            # Return a callable that raises ReferenceError (like a dead proxy)
            def dead_proxy_placeholder(*args, **kwargs):
                raise ReferenceError("weakly-referenced object no longer exists")
            return dead_proxy_placeholder
        
        # Create placeholder object for the proxy referent
        class ProxyPlaceholder:
            def __init__(self, original_type, is_callable):
                self.original_type = original_type
                self.is_callable = is_callable
            
            def __repr__(self):
                return f"<ProxyPlaceholder for {self.original_type}>"
            
            def __call__(self, *args, **kwargs):
                if self.is_callable:
                    raise RuntimeError("Proxy referent was not serialized - cannot call")
                else:
                    raise TypeError("'ProxyPlaceholder' object is not callable")
        
        original_type = referent_info.get("type", "unknown")
        placeholder = ProxyPlaceholder(original_type, is_callable)
        
        # Return weak reference instead of proxy (we can't easily recreate proxies)
        try:
            return weakref.ref(placeholder)
        except TypeError:
            return lambda: placeholder
    
    # ========================================================================
    # WEAK COLLECTIONS SERIALIZATION
    # ========================================================================
    
    def _serialize_weak_key_dict(self, weak_dict: weakref.WeakKeyDictionary) -> Dict[str, Any]:
        """
        Serialize WeakKeyDictionary objects.
        
        Store the current key-value pairs.
        """
        result = {
            "dict_items": [],
            "dict_size": 0
        }
        
        try:
            # Get current items (this creates strong references temporarily)
            items = list(weak_dict.items())
            result["dict_size"] = len(items)
            
            # Store items with key/value information
            for key, value in items:
                item_info = {
                    "key_type": f"{type(key).__module__}.{type(key).__name__}",
                    "key_repr": repr(key)[:100],
                    "key_id": id(key),
                    "value": value,  # Values are stored normally
                    "key_supports_weakref": hasattr(type(key), '__weakref__')
                }
                
                # For simple key types, store the actual value
                if isinstance(key, (int, float, str, bool, bytes)):
                    item_info["key_value"] = key
                    item_info["key_is_simple"] = True
                else:
                    item_info["key_is_simple"] = False
                
                result["dict_items"].append(item_info)
                
        except Exception as e:
            result["note"] = f"Error serializing WeakKeyDictionary: {e}"
        
        result["recreation_possible"] = True  # We can always create an empty one
        result["limitation"] = "Keys that don't support weak references will be lost"
        
        return result
    
    def _deserialize_weak_key_dict(self, data: Dict[str, Any]) -> weakref.WeakKeyDictionary:
        """
        Deserialize WeakKeyDictionary objects.
        
        Recreate with available key-value pairs.
        """
        dict_items = data.get("dict_items", [])
        
        weak_dict = weakref.WeakKeyDictionary()
        
        for item_info in dict_items:
            try:
                # Try to recreate the key
                if item_info.get("key_is_simple", False):
                    key = item_info.get("key_value")
                    if key is not None and item_info.get("key_supports_weakref", False):
                        # Simple types usually don't support weak references
                        # but we try anyway
                        try:
                            weak_dict[key] = item_info["value"]
                        except TypeError:
                            pass  # Key type doesn't support weak references
                else:
                    # For complex keys, create placeholder
                    class WeakKeyPlaceholder:
                        def __init__(self, original_type, original_repr):
                            self.original_type = original_type
                            self.original_repr = original_repr
                        
                        def __repr__(self):
                            return f"<WeakKeyPlaceholder for {self.original_type}>"
                        
                        def __hash__(self):
                            return hash(self.original_repr)
                        
                        def __eq__(self, other):
                            return isinstance(other, WeakKeyPlaceholder) and self.original_repr == other.original_repr
                    
                    if item_info.get("key_supports_weakref", False):
                        try:
                            key_placeholder = WeakKeyPlaceholder(
                                item_info.get("key_type", "unknown"),
                                item_info.get("key_repr", "unknown")
                            )
                            weak_dict[key_placeholder] = item_info["value"]
                        except (TypeError, AttributeError):
                            pass  # Couldn't create weak reference to placeholder
                            
            except Exception:
                pass  # Skip items we can't recreate
        
        return weak_dict
    
    def _serialize_weak_value_dict(self, weak_dict: weakref.WeakValueDictionary) -> Dict[str, Any]:
        """
        Serialize WeakValueDictionary objects.
        
        Store the current key-value pairs.
        """
        result = {
            "dict_items": [],
            "dict_size": 0
        }
        
        try:
            # Get current items
            items = list(weak_dict.items())
            result["dict_size"] = len(items)
            
            # Store items with key/value information
            for key, value in items:
                item_info = {
                    "key": key,  # Keys are stored normally
                    "value_type": f"{type(value).__module__}.{type(value).__name__}",
                    "value_repr": repr(value)[:100],
                    "value_id": id(value),
                    "value_supports_weakref": hasattr(type(value), '__weakref__')
                }
                
                # For simple value types, store the actual value
                if isinstance(value, (int, float, str, bool, bytes, type(None))):
                    item_info["value_value"] = value
                    item_info["value_is_simple"] = True
                else:
                    item_info["value_is_simple"] = False
                
                result["dict_items"].append(item_info)
                
        except Exception as e:
            result["note"] = f"Error serializing WeakValueDictionary: {e}"
        
        result["recreation_possible"] = True
        result["limitation"] = "Values that don't support weak references will be lost"
        
        return result
    
    def _deserialize_weak_value_dict(self, data: Dict[str, Any]) -> weakref.WeakValueDictionary:
        """
        Deserialize WeakValueDictionary objects.
        
        Recreate with available key-value pairs.
        """
        dict_items = data.get("dict_items", [])
        
        weak_dict = weakref.WeakValueDictionary()
        
        for item_info in dict_items:
            try:
                key = item_info["key"]
                
                # Try to recreate the value
                if item_info.get("value_is_simple", False):
                    value = item_info.get("value_value")
                    if value is not None and item_info.get("value_supports_weakref", False):
                        try:
                            weak_dict[key] = value
                        except TypeError:
                            pass  # Value type doesn't support weak references
                else:
                    # For complex values, create placeholder
                    class WeakValuePlaceholder:
                        def __init__(self, original_type, original_repr):
                            self.original_type = original_type
                            self.original_repr = original_repr
                        
                        def __repr__(self):
                            return f"<WeakValuePlaceholder for {self.original_type}>"
                    
                    if item_info.get("value_supports_weakref", False):
                        try:
                            value_placeholder = WeakValuePlaceholder(
                                item_info.get("value_type", "unknown"),
                                item_info.get("value_repr", "unknown")
                            )
                            weak_dict[key] = value_placeholder
                        except (TypeError, AttributeError):
                            pass  # Couldn't create weak reference to placeholder
                            
            except Exception:
                pass  # Skip items we can't recreate
        
        return weak_dict
    
    def _serialize_weak_set(self, weak_set: weakref.WeakSet) -> Dict[str, Any]:
        """
        Serialize WeakSet objects.
        
        Store the current set members.
        """
        result = {
            "set_items": [],
            "set_size": 0
        }
        
        try:
            # Get current items
            items = list(weak_set)
            result["set_size"] = len(items)
            
            # Store items with member information
            for item in items:
                item_info = {
                    "item_type": f"{type(item).__module__}.{type(item).__name__}",
                    "item_repr": repr(item)[:100],
                    "item_id": id(item),
                    "item_supports_weakref": hasattr(type(item), '__weakref__')
                }
                
                # For simple types, store the actual value
                if isinstance(item, (int, float, str, bool, bytes)):
                    item_info["item_value"] = item
                    item_info["item_is_simple"] = True
                else:
                    item_info["item_is_simple"] = False
                
                result["set_items"].append(item_info)
                
        except Exception as e:
            result["note"] = f"Error serializing WeakSet: {e}"
        
        result["recreation_possible"] = True
        result["limitation"] = "Items that don't support weak references will be lost"
        
        return result
    
    def _deserialize_weak_set(self, data: Dict[str, Any]) -> weakref.WeakSet:
        """
        Deserialize WeakSet objects.
        
        Recreate with available set members.
        """
        set_items = data.get("set_items", [])
        
        weak_set = weakref.WeakSet()
        
        for item_info in set_items:
            try:
                # Try to recreate the item
                if item_info.get("item_is_simple", False):
                    item = item_info.get("item_value")
                    if item is not None and item_info.get("item_supports_weakref", False):
                        try:
                            weak_set.add(item)
                        except TypeError:
                            pass  # Item type doesn't support weak references
                else:
                    # For complex items, create placeholder
                    class WeakSetPlaceholder:
                        def __init__(self, original_type, original_repr):
                            self.original_type = original_type
                            self.original_repr = original_repr
                        
                        def __repr__(self):
                            return f"<WeakSetPlaceholder for {self.original_type}>"
                        
                        def __hash__(self):
                            return hash(self.original_repr)
                        
                        def __eq__(self, other):
                            return isinstance(other, WeakSetPlaceholder) and self.original_repr == other.original_repr
                    
                    if item_info.get("item_supports_weakref", False):
                        try:
                            item_placeholder = WeakSetPlaceholder(
                                item_info.get("item_type", "unknown"),
                                item_info.get("item_repr", "unknown")
                            )
                            weak_set.add(item_placeholder)
                        except (TypeError, AttributeError):
                            pass  # Couldn't create weak reference to placeholder
                            
            except Exception:
                pass  # Skip items we can't recreate
        
        return weak_set
    
    # ========================================================================
    # WEAK METHOD SERIALIZATION
    # ========================================================================
    
    def _serialize_weak_method(self, weak_method) -> Dict[str, Any]:
        """
        Serialize WeakMethod objects (Python 3.4+).
        
        Store method and instance information.
        """
        result = {
            "method_alive": False,
            "method_info": None,
            "instance_info": None
        }
        
        try:
            # Try to get the method
            method = weak_method()
            
            if method is not None:
                result["method_alive"] = True
                result["method_info"] = {
                    "method_name": getattr(method, '__name__', '<unknown>'),
                    "method_qualname": getattr(method, '__qualname__', None),
                    "method_module": getattr(method, '__module__', None),
                    "method_repr": repr(method)[:100]
                }
                
                # Get instance information
                if hasattr(method, '__self__'):
                    instance = method.__self__
                    result["instance_info"] = {
                        "instance_type": f"{type(instance).__module__}.{type(instance).__name__}",
                        "instance_repr": repr(instance)[:100],
                        "instance_id": id(instance)
                    }
            else:
                result["method_alive"] = False
                result["method_info"] = {"dead_method": True}
                
        except Exception as e:
            result["note"] = f"Error accessing weak method: {e}"
        
        result["recreation_possible"] = False  # Very difficult to recreate methods
        result["limitation"] = "WeakMethod objects cannot be meaningfully recreated"
        
        return result
    
    def _deserialize_weak_method(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize WeakMethod objects.
        
        Create placeholder since methods can't be meaningfully recreated.
        """
        method_info = data.get("method_info", {})
        method_alive = data.get("method_alive", False)
        
        if not method_alive or method_info.get("dead_method"):
            # Return callable that raises ReferenceError
            def dead_method_placeholder(*args, **kwargs):
                raise ReferenceError("weakly-referenced method no longer exists")
            return dead_method_placeholder
        
        # Return placeholder function
        method_name = method_info.get("method_name", "unknown")
        
        def method_placeholder(*args, **kwargs):
            raise RuntimeError(
                f"WeakMethod '{method_name}' cannot be recreated because "
                f"the original instance and method were not serialized"
            )
        
        method_placeholder.__name__ = f"<weak_method_{method_name}>"
        return method_placeholder
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _serialize_unknown_weakref(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown weak reference types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_type": type(obj).__name__,
            "object_module": getattr(type(obj), '__module__', 'unknown'),
            "note": f"Unknown weak reference type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_weakref(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown weak reference types with placeholder.
        """
        object_type = data.get("object_type", "unknown")
        
        class WeakRefPlaceholder:
            def __init__(self, obj_type):
                self.obj_type = obj_type
            
            def __repr__(self):
                return f"<WeakRefPlaceholder type='{self.obj_type}'>"
            
            def __call__(self):
                return None  # Simulate dead weak reference
        
        return WeakRefPlaceholder(object_type)
    
    def _create_error_placeholder(self, weakref_type: str, error_message: str) -> Any:
        """
        Create a placeholder weak reference object for objects that failed to deserialize.
        """
        class WeakRefErrorPlaceholder:
            def __init__(self, obj_type, error):
                self.obj_type = obj_type
                self.error = error
            
            def __repr__(self):
                return f"<WeakRefErrorPlaceholder type='{self.obj_type}' error='{self.error}'>"
            
            def __call__(self):
                raise RuntimeError(f"Weak reference ({self.obj_type}) deserialization failed: {self.error}")
        
        return WeakRefErrorPlaceholder(weakref_type, error_message)


# Create a singleton instance for auto-registration
weak_references_handler = WeakReferencesHandler()