# add license here

# suitkaise/cereal/skpickle.py

"""
CloudPickle utilities for multiprocessing.

Provides enhanced multiprocessing support using cloudpickle, which can serialize
more complex objects than standard pickle (lambdas, local functions, etc.).

"""

import cloudpickle
from multiprocessing.managers import BaseManager, DictProxy, ListProxy
from multiprocessing import reduction
import threading
from typing import Optional, Any, Dict, List
from contextlib import contextmanager

import suitkaise.sktime.sktime as sktime

class SKPickleError(Exception):
    """Base exception for SKPickle errors."""
    pass

class CloudpickleMGRError(SKPickleError):
    """Exception raised when the Cloudpickle manager fails to start."""
    pass

class CloudpickleMGR(BaseManager):
    """
    Custom multiprocessing Manager that uses cloudpickle for serialization.
    
    This allows serialization of more complex objects (lambdas, local functions, etc.)
    that regular pickle cannot handle.
    """
    
    def __init__(self):
        super().__init__()
    
    def start(self, initializer=None, initargs=()):
        """Start the manager with cloupickle support."""
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
        # temp set cloudpickle as the pickler
        original_pickler = reduction.ForkingPickler
        try:
            reduction.ForkingPickler = cloudpickle.CloudPickler
            return self._create('dict', *args, **kwargs)
        finally:
            # Restore original pickler
            reduction.ForkingPickler = original_pickler

    def list(self, *args, **kwargs) -> ListProxy:
        """Create a shared list using cloudpickle."""
        # temp set cloudpickle as the pickler
        original_pickler = reduction.ForkingPickler
        try:
            reduction.ForkingPickler = cloudpickle.CloudPickler
            return self._create('list', *args, **kwargs)
        finally:
            # Restore original pickler
            reduction.ForkingPickler = original_pickler

# Register the types with the manager
CloudpickleMGR.register('dict', dict, DictProxy)
CloudpickleMGR.register('list', list, ListProxy)

class SKPickle:
    """
    Utility class for managing cloudpickle in multiprocessing contexts.
    
    Provides both Manager instances and context management for cloudpickle,
    making it easy to use enhanced serialization across processes.
    
    Usage:
        # Simple manager usage
        manager = SKPickle.get_manager()
        shared_dict = manager.dict()
        
        # Convenience methods
        shared_dict = SKPickle.create_shared_dict({'key': 'value'})
        shared_list = SKPickle.create_shared_list([1, 2, 3])
        
        # Context manager for temporary cloudpickle
        with SKPickle.cloudpickle_context():
            # All multiprocessing here uses cloudpickle
            pass
            
        # Global enable/disable
        SKPickle.enable_cloudpickle_globally()
        # ... your multiprocessing code ...
        SKPickle.disable_cloudpickle_globally()

    """
    _manager_instance: Optional[CloudpickleMGR] = None
    _original_pickler = None
    _lock = threading.RLock()
    _globally_enabled = False
    _manager_failed = False
    _fallback_mode = False
    
    @classmethod
    def get_manager(cls) -> CloudpickleMGR:
        """
        Get a singleton CloudpickleMGR instance.
        
        The manager is automatically started and ready for use.
        
        Returns:
            CloudpickleMGR: A started manager instance using cloudpickle.
            
        Example:
            manager = SKPickle.get_manager()
            shared_data = manager.dict({'initial': 'data'})

        """
        if cls._manager_failed:
            raise CloudpickleMGRError(
                "Cloudpickle manager failed to start. "
                "Fallback is not available in this context. "
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
                            f"Failed to start Cloudpickle manager: {e}"
                            f"Could be from platform restrictions or "
                            f"resource limitations. "
                        ) from e
        return cls._manager_instance
    
    @classmethod
    def manager_is_available(cls) -> bool:
        """
        Check if the Cloudpickle manager is available.

        Returns:
            bool: True if the manager is available, False otherwise.
        
        """
        if cls._manager_failed:
            return False
        
        try:
            cls.get_manager()
            return True
        except CloudpickleMGRError:
            return False
        
    @classmethod
    def shutdown_manager(cls):
        """
        Shutdown the singleton manager instance if it exists.
        
        This is useful for cleaning up resources when done with multiprocessing.
        After calling this, get_manager() will create a new instance if called again.

        """
        if cls._manager_instance is not None:
            with cls._lock:
                if cls._manager_instance is not None:
                    try:
                        cls._manager_instance.shutdown()
                    except Exception:
                        # Ignore shutdown errors
                        pass
                    finally:
                        cls._manager_instance = None
                        cls._manager_failed = False

    @classmethod
    @contextmanager
    def cloudpickle_context(cls):
        """
        Context manager to temporarily use cloudpickle for multiprocessing.
        
        Within this context, ALL multiprocessing operations will use cloudpickle
        instead of regular pickle. The original pickler is restored when exiting.
        
        Usage:
            with SKPickle.cloudpickle_context():
                from multiprocessing import Manager
                manager = Manager()  # Uses cloudpickle
                shared_dict = manager.dict()
                
        Note:
            This is useful when you want to use standard multiprocessing classes
            but need cloudpickle serialization.

        """
        # Save current pickler
        original = reduction.ForkingPickler
        try:
            # Set cloudpickle
            reduction.ForkingPickler = cloudpickle.CloudPickler
            yield
        finally:
            # Restore original
            reduction.ForkingPickler = original

    @classmethod
    def enable_cloudpickle_globally(cls):
        """
        Enable cloudpickle globally for all multiprocessing operations.
        
        Warning: This affects ALL multiprocessing in the current process,
        including operations outside your code. Use with caution.
        
        Call disable_cloudpickle_globally() to restore the original pickler.

        """
        if not cls._globally_enabled:
            cls._original_pickler = reduction.ForkingPickler
            reduction.ForkingPickler = cloudpickle.CloudPickler
            cls._globally_enabled = True

    @classmethod
    def disable_cloudpickle_globally(cls):
        """
        Restore the original pickler globally.
        
        This undoes the effect of enable_cloudpickle_globally().

        """
        if cls._globally_enabled and cls._original_pickler is not None:
            reduction.ForkingPickler = cls._original_pickler
            cls._original_pickler = None
            cls._globally_enabled = False

    
    @classmethod
    def create_shared_dict(cls, initial_data: Optional[Dict] = None) -> DictProxy | Dict:
        """
        Create a shared dictionary using cloudpickle, with fallback to regular dict.
        
        Args:
            initial_data: Optional dictionary to initialize with.
            
        Returns:
            DictProxy or Dict: A cloudpickle-enabled shared dictionary, or regular dict if manager fails.
            
        Example:
            # Empty dict
            shared_dict = SKPickle.create_shared_dict()
            
            # With initial data
            shared_dict = SKPickle.create_shared_dict({'key': 'value'})
        """
        try:
            manager = cls.get_manager()
            if initial_data:
                return manager.dict(initial_data)
            return manager.dict()
        except CloudpickleMGRError:
            # Fallback to regular dict if manager fails
            cls._fallback_mode = True
            if initial_data:
                return dict(initial_data)
            return dict()
    
    @classmethod
    def create_shared_list(cls, initial_data: Optional[List] = None) -> ListProxy | List:
        """
        Create a shared list using cloudpickle, with fallback to regular list.
        
        Args:
            initial_data: Optional list to initialize with.
            
        Returns:
            ListProxy or List: A cloudpickle-enabled shared list, or regular list if manager fails.
            
        Example:
            # Empty list
            shared_list = SKPickle.create_shared_list()
            
            # With initial data
            shared_list = SKPickle.create_shared_list([1, 2, 3])
        """
        try:
            manager = cls.get_manager()
            if initial_data:
                return manager.list(initial_data)
            return manager.list()
        except Exception:
            # Fallback to regular list
            cls._fallback_mode = True
            if initial_data:
                return list(initial_data)
            return list()
        
    @classmethod
    def in_fallback_mode(cls) -> bool:
        """
        Check if SKPickle is operating in fallback mode (using regular dicts/lists).
        
        Returns:
            bool: True if in fallback mode, False if using multiprocessing.
        """
        return cls._fallback_mode
    

    @classmethod
    def test_serialization(cls, obj: Any) -> bool:
        """
        Test if an object can be serialized with cloudpickle.
        
        Args:
            obj: Object to test for cloudpickle compatibility.
            
        Returns:
            bool: True if the object can be serialized, False otherwise.
            
        Example:
            # Test a lambda function
            func = lambda x: x * 2
            if SKPickle.test_serialization(func):
                shared_dict = SKPickle.create_shared_dict({'func': func})
        """
        try:
            cloudpickle.dumps(obj)
            return True
        except Exception:
            return False
    
    @classmethod
    def serialize(cls, obj: Any) -> bytes:
        """Serialize an object into bytes using cloudpickle."""
        try:
            return cloudpickle.dumps(obj)
        except Exception as e:
            raise SKPickleError(f"Serialization failed: {e}") from e
    
    @classmethod
    def deserialize(cls, data: bytes) -> Any:
        """Deserialize bytes back to an object using cloudpickle."""
        try:
            return cloudpickle.loads(data)
        except Exception as e:
            raise SKPickleError(f"Deserialization failed: {e}") from e
    
    @classmethod
    def cloudpickle_is_enabled(cls) -> bool:
        """
        Check if cloudpickle is currently enabled globally.
        
        Returns:
            bool: True if cloudpickle is enabled globally, False otherwise.
        """
        return cls._globally_enabled
    
    @classmethod
    def get_pickler_info(cls) -> Dict[str, Any]:
        """
        Get information about the current pickler configuration.
        
        Returns:
            Dict: Information about current pickler setup.
        """
        return {
            'current_pickler': reduction.ForkingPickler.__name__,
            'cloudpickle_enabled_globally': cls._globally_enabled,
            'manager_active': cls._manager_instance is not None,
            'manager_failed': cls._manager_failed,
            'fallback_mode': cls._fallback_mode,
            'cloudpickle_available': True  # Since we import it successfully
        }

    @classmethod
    def reset_state(cls):
        """Reset SKPickle state. Useful for testing."""
        cls.shutdown_manager()
        cls.disable_cloudpickle_globally()
        cls._manager_failed = False
        cls._fallback_mode = False

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