# suitkaise/cereal/skpickle.py

# add license here

# Enhanced SKPickle with custom serialization support

"""
CloudPickle utilities for multiprocessing with enhanced custom serialization.

Provides enhanced multiprocessing support using cloudpickle, which can serialize
more complex objects than standard pickle (lambdas, local functions, etc.).

Now includes automatic handling of objects with __getstate__/__setstate__ methods
and a registry for custom serialization of common unserializable types.
"""

import cloudpickle
from multiprocessing.managers import BaseManager, DictProxy, ListProxy
from multiprocessing import reduction
import threading
from typing import Optional, Any, Dict, List, Callable, Type, Tuple
from contextlib import contextmanager
import time


class SKPickleError(Exception):
    """Base exception for SKPickle errors."""
    pass

class CloudpickleMGRError(SKPickleError):
    """Exception raised when the Cloudpickle manager fails to start."""
    pass

class SerializationHandler:
    """Handler for custom serialization of specific object types."""
    
    def __init__(self, 
                 serializer: Callable[[Any], Dict[str, Any]], 
                 deserializer: Callable[[Dict[str, Any]], Any],
                 description: str = ""):
        self.serializer = serializer
        self.deserializer = deserializer
        self.description = description
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """Serialize an object to a dictionary."""
        return self.serializer(obj)
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """Deserialize a dictionary back to an object."""
        return self.deserializer(data)

class CloudpickleMGR(BaseManager):
    """
    Custom multiprocessing Manager that uses cloudpickle for serialization.
    
    This allows serialization of more complex objects (lambdas, local functions, etc.)
    that regular pickle cannot handle.
    """
    
    def __init__(self):
        super().__init__()
    
    def start(self, initializer=None, initargs=()):
        """Start the manager with cloudpickle support."""
        original_pickler = reduction.ForkingPickler
        try:
            # Set cloudpickle as the pickler for multiprocessing
            reduction.ForkingPickler = cloudpickle.CloudPickler
            super().start(initializer, initargs)
        except Exception as e:
            # Restore original pickler on failure
            reduction.ForkingPickler = original_pickler
            raise e
        finally:
            # Ensure we restore the original pickler after starting
            reduction.ForkingPickler = original_pickler

    def dict(self, *args, **kwargs) -> DictProxy:
        """Create a shared dictionary using cloudpickle."""
        original_pickler = reduction.ForkingPickler
        try:
            reduction.ForkingPickler = cloudpickle.CloudPickler
            return self._create('dict', *args, **kwargs)
        finally:
            reduction.ForkingPickler = original_pickler

    def list(self, *args, **kwargs) -> ListProxy:
        """Create a shared list using cloudpickle."""
        original_pickler = reduction.ForkingPickler
        try:
            reduction.ForkingPickler = cloudpickle.CloudPickler
            return self._create('list', *args, **kwargs)
        finally:
            reduction.ForkingPickler = original_pickler

# Register the types with the manager
CloudpickleMGR.register('dict', dict, DictProxy)
CloudpickleMGR.register('list', list, ListProxy)

class SKPickle:
    """
    Enhanced utility class for managing cloudpickle in multiprocessing contexts.
    
    Now includes automatic custom serialization support for objects that define
    __getstate__/__setstate__ methods, plus a registry for common unserializable types.
    
    Usage:
        # Simple manager usage
        manager = SKPickle.get_manager()
        shared_dict = manager.dict()
        
        # Convenience methods
        shared_dict = SKPickle.create_shared_dict({'key': 'value'})
        shared_list = SKPickle.create_shared_list([1, 2, 3])
        
        # Register custom serializer for a type
        SKPickle.register_serializer(MyClass, my_serializer, my_deserializer)
        
        # Enhanced serialization
        data = SKPickle.serialize(complex_object)
        restored = SKPickle.deserialize(data)
    """
    
    _manager_instance: Optional[CloudpickleMGR] = None
    _original_pickler = None
    _lock = threading.RLock()
    _globally_enabled = False
    _manager_failed = False
    _fallback_mode = False
    
    # Enhanced serialization support
    _custom_serializers: Dict[Type, SerializationHandler] = {}
    _serialization_lock = threading.RLock()
    
    @classmethod
    def register_serializer(cls, 
                          obj_type: Type, 
                          serializer: Callable[[Any], Dict[str, Any]], 
                          deserializer: Callable[[Dict[str, Any]], Any],
                          description: str = "") -> None:
        """
        Register a custom serializer for a specific object type.
        
        Args:
            obj_type: The type of object this serializer handles
            serializer: Function that converts object to dict
            deserializer: Function that converts dict back to object
            description: Optional description of what this serializer does
            
        Example:
            def serialize_lock(lock):
                return {'type': 'RLock', 'created_at': time.time()}
                
            def deserialize_lock(data):
                return threading.RLock()
                
            SKPickle.register_serializer(
                threading.RLock, 
                serialize_lock, 
                deserializer_lock,
                "Recreates threading locks"
            )
        """
        with cls._serialization_lock:
            handler = SerializationHandler(serializer, deserializer, description)
            cls._custom_serializers[obj_type] = handler
    
    @classmethod
    def unregister_serializer(cls, obj_type: Type) -> bool:
        """
        Remove a custom serializer for a type.
        
        Args:
            obj_type: The type to remove serializer for
            
        Returns:
            True if serializer existed and was removed, False otherwise
        """
        with cls._serialization_lock:
            if obj_type in cls._custom_serializers:
                del cls._custom_serializers[obj_type]
                return True
            return False
    
    @classmethod
    def list_custom_serializers(cls) -> Dict[str, str]:
        """
        Get a list of all registered custom serializers.
        
        Returns:
            Dict mapping type names to their descriptions
        """
        with cls._serialization_lock:
            return {
                str(obj_type.__name__): handler.description 
                for obj_type, handler in cls._custom_serializers.items()
            }
    
    @classmethod
    def _has_custom_state_methods(cls, obj: Any) -> bool:
        """Check if an object has __getstate__/__setstate__ methods."""
        return (hasattr(obj, '__getstate__') and callable(getattr(obj, '__getstate__')) and
                hasattr(obj, '__setstate__') and callable(getattr(obj, '__setstate__')))
    
    @classmethod
    def _serialize_with_custom_state(cls, obj: Any) -> Dict[str, Any]:
        """Serialize an object using its __getstate__ method."""
        try:
            state = obj.__getstate__()
            return {
                '_skpickle_custom_state': True,
                '_skpickle_type': f"{obj.__class__.__module__}.{obj.__class__.__qualname__}",
                '_skpickle_state': state
            }
        except Exception as e:
            raise SKPickleError(f"Failed to serialize object using __getstate__: {e}")
    
    @classmethod
    def _deserialize_with_custom_state(cls, data: Dict[str, Any]) -> Any:
        """Deserialize an object using its __setstate__ method."""
        try:
            # Get the class using safe import
            obj_class = cls._safe_import_class(data['_skpickle_type'])
            
            # Create instance without calling __init__
            obj = obj_class.__new__(obj_class)
            
            # Restore state
            obj.__setstate__(data['_skpickle_state'])
            
            return obj
        except Exception as e:
            raise SKPickleError(f"Failed to deserialize object using __setstate__: {e}")
    
    @classmethod
    def _is_custom_state_data(cls, data: Any) -> bool:
        """Check if data represents a custom state serialized object."""
        return (isinstance(data, dict) and 
                data.get('_skpickle_custom_state') is True and
                '_skpickle_type' in data and
                '_skpickle_state' in data)
    
    @classmethod
    def _safe_import_class(cls, type_str: str):
        """Safely import a class, handling __main__ and local scope issues."""
        try:
            if '.' in type_str:
                module_name, class_name = type_str.rsplit('.', 1)
            else:
                # Handle simple class names
                module_name = '__main__'
                class_name = type_str
            
            # Handle __main__ module specially
            if module_name == '__main__':
                import __main__
                if hasattr(__main__, class_name):
                    return getattr(__main__, class_name)
                else:
                    # Try to find the class in globals
                    import sys
                    main_module = sys.modules['__main__']
                    for name, obj in main_module.__dict__.items():
                        if (hasattr(obj, '__name__') and obj.__name__ == class_name and 
                            hasattr(obj, '__module__')):
                            return obj
                    raise ImportError(f"Class {class_name} not found in __main__")
            else:
                module = __import__(module_name, fromlist=[class_name])
                return getattr(module, class_name)
                
        except Exception as e:
            raise SKPickleError(f"Could not import class {type_str}: {e}")
    
    @classmethod
    def serialize(cls, obj: Any) -> bytes:
        """
        Enhanced serialize an object into bytes using cloudpickle with custom support.
        
        Automatically handles:
        - Objects with __getstate__/__setstate__ methods
        - Objects with registered custom serializers
        - Standard cloudpickle serialization as fallback
        """
        try:
            # First, try custom serializers for specific types
            obj_type = type(obj)
            with cls._serialization_lock:
                if obj_type in cls._custom_serializers:
                    handler = cls._custom_serializers[obj_type]
                    custom_data = handler.serialize(obj)
                    wrapper = {
                        '_skpickle_custom_serializer': True,
                        '_skpickle_type': f"{obj_type.__module__}.{obj_type.__qualname__}",
                        '_skpickle_data': custom_data
                    }
                    return cloudpickle.dumps(wrapper)
            
            # Try standard cloudpickle first
            return cloudpickle.dumps(obj)
            
        except Exception:
            # If cloudpickle fails, try custom state methods
            if cls._has_custom_state_methods(obj):
                try:
                    state_data = cls._serialize_with_custom_state(obj)
                    return cloudpickle.dumps(state_data)
                except Exception as state_error:
                    raise SKPickleError(f"Both cloudpickle and custom state serialization failed. "
                                      f"Custom state error: {state_error}")
            else:
                # Re-raise original cloudpickle error
                raise SKPickleError(f"Serialization failed: {obj} of type {type(obj)} is not serializable")
    
    @classmethod
    def deserialize(cls, data: bytes) -> Any:
        """
        Enhanced deserialize bytes back to an object using cloudpickle with custom support.
        
        Automatically handles:
        - Objects serialized with custom serializers
        - Objects serialized with __getstate__/__setstate__ methods
        - Standard cloudpickle deserialization as fallback
        """
        try:
            # First deserialize the data
            deserialized = cloudpickle.loads(data)
            
            # Check if it's a custom serializer wrapper
            if (isinstance(deserialized, dict) and 
                deserialized.get('_skpickle_custom_serializer') is True):
                
                # Find the custom serializer using safe import
                obj_class = cls._safe_import_class(deserialized['_skpickle_type'])
                
                with cls._serialization_lock:
                    if obj_class in cls._custom_serializers:
                        handler = cls._custom_serializers[obj_class]
                        return handler.deserialize(deserialized['_skpickle_data'])
                    else:
                        raise SKPickleError(f"No custom serializer found for type {obj_class}")
            
            # Check if it's custom state data
            elif cls._is_custom_state_data(deserialized):
                return cls._deserialize_with_custom_state(deserialized)
            
            # Otherwise, it's regular cloudpickle data
            else:
                return deserialized
                
        except Exception as e:
            raise SKPickleError(f"Deserialization failed: {e}")
    
    @classmethod
    def get_manager(cls) -> CloudpickleMGR:
        """Get a singleton CloudpickleMGR instance with enhanced serialization."""
        if cls._manager_failed:
            raise CloudpickleMGRError(
                "Cloudpickle manager failed to start. "
                "Fallback is not available in this context."
            )
        
        if cls._manager_instance is None:
            with cls._lock:
                if cls._manager_instance is None:
                    try:
                        cls._manager_instance = CloudpickleMGR()
                        cls._manager_instance.start()
                        cls._manager_failed = False
                    except Exception as e:
                        cls._manager_failed = True
                        cls._manager_instance = None
                        raise CloudpickleMGRError(
                            f"Failed to start Cloudpickle manager: {e}. "
                            f"Could be from platform restrictions or resource limitations."
                        ) from e
        return cls._manager_instance
    
    @classmethod
    def manager_is_available(cls) -> bool:
        """Check if the Cloudpickle manager is available."""
        if cls._manager_failed:
            return False
        
        try:
            cls.get_manager()
            return True
        except CloudpickleMGRError:
            return False
    
    @classmethod
    def shutdown_manager(cls):
        """Improved shutdown with timeout and error handling."""
        if cls._manager_instance is not None:
            with cls._lock:
                if cls._manager_instance is not None:
                    try:
                        # Give manager time to finish operations
                        import time
                        time.sleep(0.1)
                        
                        # Shutdown with timeout
                        cls._manager_instance.shutdown()
                        
                        # Wait for process to actually terminate
                        if hasattr(cls._manager_instance, '_process'):
                            cls._manager_instance._process.join(timeout=1.0)
                            
                    except Exception as e:
                        # Force terminate if graceful shutdown fails
                        try:
                            if hasattr(cls._manager_instance, '_process'):  
                                cls._manager_instance._process.terminate()
                        except:
                            pass
                    finally:
                        cls._manager_instance = None
                        cls._manager_failed = False

    @classmethod
    @contextmanager
    def cloudpickle_context(cls):
        """Context manager to temporarily use enhanced cloudpickle for multiprocessing."""
        original = reduction.ForkingPickler
        try:
            reduction.ForkingPickler = cloudpickle.CloudPickler
            yield
        finally:
            reduction.ForkingPickler = original

    @classmethod
    def enable_cloudpickle_globally(cls):
        """Enable enhanced cloudpickle globally for all multiprocessing operations."""
        if not cls._globally_enabled:
            cls._original_pickler = reduction.ForkingPickler
            reduction.ForkingPickler = cloudpickle.CloudPickler
            cls._globally_enabled = True

    @classmethod
    def disable_cloudpickle_globally(cls):
        """Restore the original pickler globally."""
        if cls._globally_enabled and cls._original_pickler is not None:
            reduction.ForkingPickler = cls._original_pickler
            cls._original_pickler = None
            cls._globally_enabled = False
    
    @classmethod
    def create_shared_dict(cls, initial_data: Optional[Dict] = None) -> DictProxy | Dict:
        """Create a shared dictionary using enhanced cloudpickle."""
        try:
            manager = cls.get_manager()
            if initial_data:
                return manager.dict(initial_data)
            return manager.dict()
        except CloudpickleMGRError:
            cls._fallback_mode = True
            if initial_data:
                return dict(initial_data)
            return dict()
    
    @classmethod
    def create_shared_list(cls, initial_data: Optional[List] = None) -> ListProxy | List:
        """Create a shared list using enhanced cloudpickle."""
        try:
            manager = cls.get_manager()
            if initial_data:
                return manager.list(initial_data)
            return manager.list()
        except Exception:
            cls._fallback_mode = True
            if initial_data:
                return list(initial_data)
            return list()
    
    @classmethod
    def in_fallback_mode(cls) -> bool:
        """Check if SKPickle is operating in fallback mode."""
        return cls._fallback_mode
    
    @classmethod
    def test_serialization(cls, obj: Any) -> bool:
        """
        Test if an object can be serialized with enhanced cloudpickle.
        
        Args:
            obj: Object to test for enhanced cloudpickle compatibility
            
        Returns:
            bool: True if the object can be serialized, False otherwise
        """
        try:
            cls.serialize(obj)
            return True
        except Exception:
            return False
    
    @classmethod
    def reset_manager_state(cls):
        """Reset manager state for recovery."""
        with cls._lock:
            cls._manager_failed = False
            cls._fallback_mode = False
    
    @classmethod
    def cloudpickle_is_enabled(cls) -> bool:
        """Check if cloudpickle is currently enabled globally."""
        return cls._globally_enabled
    
    @classmethod
    def get_pickler_info(cls) -> Dict[str, Any]:
        """Get information about the current pickler configuration."""
        with cls._serialization_lock:
            return {
                'current_pickler': reduction.ForkingPickler.__name__,
                'cloudpickle_enabled_globally': cls._globally_enabled,
                'manager_active': cls._manager_instance is not None,
                'manager_failed': cls._manager_failed,
                'fallback_mode': cls._fallback_mode,
                'cloudpickle_available': True,
                'custom_serializers_count': len(cls._custom_serializers),
                'custom_serializers': cls.list_custom_serializers()
            }

    @classmethod
    def reset_state(cls):
        """Reset SKPickle state. Useful for testing."""
        cls.shutdown_manager()
        cls.disable_cloudpickle_globally()
        cls._manager_failed = False
        cls._fallback_mode = False
        with cls._serialization_lock:
            cls._custom_serializers.clear()

# Enhanced state method utilities
class StateHelper:
    """Utilities for more precise __getstate__/__setstate__ handling."""
    
    # Get actual types by creating instances
    _sample_lock = threading.Lock()
    _sample_rlock = threading.RLock() 
    _sample_condition = threading.Condition()
    _sample_semaphore = threading.Semaphore()
    _sample_bounded_semaphore = threading.BoundedSemaphore()
    _sample_event = threading.Event()
    
    # Common unserializable types and their categories (using actual types)
    UNSERIALIZABLE_TYPES = {
        # Threading objects (actual types)
        type(_sample_lock): 'threading_lock',
        type(_sample_rlock): 'threading_rlock', 
        type(_sample_condition): 'threading_condition',
        type(_sample_semaphore): 'threading_semaphore',
        type(_sample_bounded_semaphore): 'threading_bounded_semaphore',
        type(_sample_event): 'threading_event',
        # Note: Thread and Timer are harder to handle since they need to be running
    }
    
    # Type categories that need special recreation
    RECREATION_STRATEGIES = {
        'threading_lock': lambda: threading.Lock(),
        'threading_rlock': lambda: threading.RLock(),
        'threading_condition': lambda: threading.Condition(),
        'threading_semaphore': lambda data: threading.Semaphore(data.get('value', 1)),
        'threading_bounded_semaphore': lambda data: threading.BoundedSemaphore(data.get('value', 1)),
        'threading_event': lambda: threading.Event(),
        'file_object': lambda data: None,  # Files can't be meaningfully recreated
        'socket_object': lambda data: None,  # Sockets can't be meaningfully recreated  
        'database_connection': lambda data: None,  # DB connections can't be recreated
        'generator': lambda data: iter([]),  # Return empty iterator
        'module': lambda data: None,  # Modules should be re-imported, not recreated
    }
    
    @classmethod
    def identify_unserializable_type(cls, obj) -> Optional[str]:
        """
        Identify what category of unserializable object this is.
        
        Returns:
            str: Category name if unserializable, None if serializable
        """
        obj_type = type(obj)
        
        # Direct type matches
        if obj_type in cls.UNSERIALIZABLE_TYPES:
            return cls.UNSERIALIZABLE_TYPES[obj_type]
        
        # Pattern-based detection
        type_name = obj_type.__name__
        module_name = getattr(obj_type, '__module__', '')
        
        # File-like objects
        if hasattr(obj, 'read') and hasattr(obj, 'write') and hasattr(obj, 'close'):
            if hasattr(obj, 'name') and isinstance(getattr(obj, 'name'), str):
                return 'file_object'
        
        # Socket objects
        if 'socket' in module_name.lower() or 'socket' in type_name.lower():
            return 'socket_object'
            
        # Database connections (common patterns)
        if any(db in module_name.lower() for db in ['sqlite3', 'psycopg', 'mysql', 'pymongo']):
            if any(word in type_name.lower() for word in ['connection', 'cursor', 'client']):
                return 'database_connection'
        
        # Generator objects
        if hasattr(obj, '__iter__') and hasattr(obj, '__next__') and hasattr(obj, 'gi_frame'):
            return 'generator'
            
        # Coroutine objects
        if hasattr(obj, '__await__') or 'coroutine' in type_name.lower():
            return 'coroutine'
            
        # Module objects
        if module_name == 'builtins' and type_name == 'module':
            return 'module'
            
        # Compiled regex patterns
        if module_name == 're' and 'Pattern' in type_name:
            return 'regex_pattern'
            
        # Weakref objects
        if 'weakref' in module_name:
            return 'weakref'
            
        return None
    
    @classmethod
    def create_safe_state(cls, obj) -> Dict[str, Any]:
        """
        Create a safe state dictionary by excluding unserializable attributes.
        
        Args:
            obj: Object to create state for
            
        Returns:
            Dict with serializable attributes only
        """
        if hasattr(obj, '__dict__'):
            state = {}
            excluded = []
            
            for key, value in obj.__dict__.items():
                # Skip private attributes that are likely system-related
                if key.startswith('_') and any(skip in key for skip in ['lock', 'thread', 'process', 'manager']):
                    excluded.append((key, 'private_system_attr'))
                    continue
                
                # Check if the value itself is unserializable
                unser_type = cls.identify_unserializable_type(value)
                if unser_type:
                    excluded.append((key, unser_type))
                    continue
                
                # Try basic serialization test
                try:
                    cloudpickle.dumps(value)
                    state[key] = value
                except Exception:
                    excluded.append((key, 'serialization_failed'))
            
            # Store metadata about what was excluded for debugging
            state['_skpickle_excluded'] = excluded
            return state
        else:
            # Object doesn't have __dict__, try to get its state another way
            try:
                # Some objects store state in __slots__
                if hasattr(obj, '__slots__'):
                    state = {}
                    for slot in obj.__slots__:
                        if hasattr(obj, slot):
                            value = getattr(obj, slot)
                            try:
                                cloudpickle.dumps(value) 
                                state[slot] = value
                            except Exception:
                                pass
                    return state
                else:
                    return {}
            except Exception:
                return {}
    
    @classmethod  
    def restore_safe_state(cls, obj, state: Dict[str, Any]):
        """
        Restore state to an object, recreating unserializable attributes.
        
        Args:
            obj: Object to restore state to
            state: State dictionary from create_safe_state
        """
        excluded = state.pop('_skpickle_excluded', [])
        
        # Restore serializable attributes
        if hasattr(obj, '__dict__'):
            obj.__dict__.update(state)
        else:
            # Try to set attributes individually
            for key, value in state.items():
                try:
                    setattr(obj, key, value)
                except (AttributeError, TypeError):
                    pass  # Skip read-only or invalid attributes
        
        # Recreate unserializable attributes
        for attr_name, category in excluded:
            if category in cls.RECREATION_STRATEGIES:
                try:
                    # Some strategies need the original data, most don't
                    strategy = cls.RECREATION_STRATEGIES[category] 
                    if callable(strategy):
                        if category in ['threading_semaphore', 'threading_bounded_semaphore']:
                            # These need the count value
                            recreated = strategy({'value': 1})  # Default value
                        else:
                            recreated = strategy()
                        
                        if recreated is not None:
                            setattr(obj, attr_name, recreated)
                except Exception:
                    # If recreation fails, skip it
                    pass

def enhanced_getstate(obj):
    """
    Enhanced __getstate__ implementation that can be used by any class.
    
    Usage in your class:
        def __getstate__(self):
            return enhanced_getstate(self)
    """
    return StateHelper.create_safe_state(obj)

def enhanced_setstate(obj, state):
    """
    Enhanced __setstate__ implementation that can be used by any class.
    
    Usage in your class:  
        def __setstate__(self, state):
            enhanced_setstate(self, state)
    """
    StateHelper.restore_safe_state(obj, state)

# Initialize common unserializable type handlers
def _init_common_serializers():
    """Initialize serializers for common unserializable types."""
    
    # Get the actual types by creating instances
    sample_lock = threading.Lock()
    sample_rlock = threading.RLock()
    sample_condition = threading.Condition()
    sample_event = threading.Event()
    sample_semaphore = threading.Semaphore()
    
    actual_lock_type = type(sample_lock)
    actual_rlock_type = type(sample_rlock)
    actual_condition_type = type(sample_condition)
    actual_event_type = type(sample_event)
    actual_semaphore_type = type(sample_semaphore)
    
    # Debug: Print actual types being registered
    # print(f"Registering actual types:")
    # print(f"  Lock: {actual_lock_type}")
    # print(f"  RLock: {actual_rlock_type}")
    # print(f"  Condition: {actual_condition_type}")
    # print(f"  Event: {actual_event_type}")
    # print(f"  Semaphore: {actual_semaphore_type}")
    
    # Threading RLock
    def serialize_rlock(lock):
        return {'type': 'RLock', 'created_at': time.time()}
    
    def deserialize_rlock(data):
        return threading.RLock()
    
    SKPickle.register_serializer(
        actual_rlock_type,  # Use actual type
        serialize_rlock,
        deserialize_rlock,
        "Recreates threading RLock objects"
    )
    
    # Threading Lock
    def serialize_lock(lock):
        return {'type': 'Lock', 'created_at': time.time()}
    
    def deserialize_lock(data):
        return threading.Lock()
    
    SKPickle.register_serializer(
        actual_lock_type,  # Use actual type
        serialize_lock,
        deserialize_lock,
        "Recreates threading Lock objects"
    )
    
    # Threading Condition
    def serialize_condition(condition):
        return {'type': 'Condition', 'created_at': time.time()}
    
    def deserialize_condition(data):
        return threading.Condition()
    
    SKPickle.register_serializer(
        actual_condition_type,  # Use actual type
        serialize_condition,
        deserialize_condition,
        "Recreates threading Condition objects"
    )
    
    # Threading Event
    def serialize_event(event):
        return {
            'type': 'Event', 
            'is_set': event.is_set(),
            'created_at': time.time()
        }
    
    def deserialize_event(data):
        event = threading.Event()
        if data.get('is_set', False):
            event.set()
        return event
    
    SKPickle.register_serializer(
        actual_event_type,  # Use actual type
        serialize_event,
        deserialize_event,
        "Recreates threading Event objects with state"
    )
    
    # Threading Semaphore
    def serialize_semaphore(semaphore):
        # Try to get the current value (tricky with semaphores)
        return {
            'type': 'Semaphore',
            'value': 1,  # Default, can't easily get current value
            'created_at': time.time()
        }
    
    def deserialize_semaphore(data):
        return threading.Semaphore(data.get('value', 1))
    
    SKPickle.register_serializer(
        actual_semaphore_type,  # Use actual type
        serialize_semaphore,
        deserialize_semaphore,
        "Recreates threading Semaphore objects"
    )
    
    # Also register BoundedSemaphore if it's different
    sample_bounded_semaphore = threading.BoundedSemaphore()
    actual_bounded_semaphore_type = type(sample_bounded_semaphore)
    
    if actual_bounded_semaphore_type != actual_semaphore_type:
        def serialize_bounded_semaphore(semaphore):
            return {
                'type': 'BoundedSemaphore',
                'value': 1,  # Default
                'created_at': time.time()
            }
        
        def deserialize_bounded_semaphore(data):
            return threading.BoundedSemaphore(data.get('value', 1))
        
        SKPickle.register_serializer(
            actual_bounded_semaphore_type,
            serialize_bounded_semaphore,
            deserialize_bounded_semaphore,
            "Recreates threading BoundedSemaphore objects"
        )
    
    # Compiled regex patterns
    try:
        import re
        def serialize_pattern(pattern):
            return {
                'type': 'Pattern',
                'pattern': pattern.pattern,
                'flags': pattern.flags,
                'created_at': time.time()
            }
        
        def deserialize_pattern(data):
            return re.compile(data['pattern'], data.get('flags', 0))
        
        # Get the Pattern type (it's not directly accessible)
        sample_pattern = re.compile(r'test')
        pattern_type = type(sample_pattern)
        
        SKPickle.register_serializer(
            pattern_type,
            serialize_pattern,
            deserialize_pattern,
            "Recreates compiled regex Pattern objects"
        )
    except ImportError:
        pass  # Skip if re module not available

# Initialize common serializers
_init_common_serializers()

# Convenience aliases for common operations
create_shared_dict = SKPickle.create_shared_dict
create_shared_list = SKPickle.create_shared_list
test_serialization = SKPickle.test_serialization
cloudpickle_context = SKPickle.cloudpickle_context

# Module-level cleanup function
def cleanup():
    """Clean up SKPickle resources."""
    SKPickle.shutdown_manager()
    SKPickle.disable_cloudpickle_globally()

# Register cleanup to happen on module unload
import atexit
atexit.register(cleanup)