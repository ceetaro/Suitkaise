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
from typing import Optional, Any, Dict, List, Union
from contextlib import contextmanager

class CloudPickleManager(BaseManager):
    """
    Custom multiprocessing Manager that uses cloudpickle for serialization.
    
    This allows serialization of more complex objects (lambdas, local functions, etc.)
    that regular pickle cannot handle.
    """
    
    def __init__(self):
        # Set cloudpickle as the pickler before initialization
        reduction.ForkingPickler = cloudpickle.CloudPickler
        super().__init__()
    
    def dict(self, *args, **kwargs) -> DictProxy:
        """Create a shared dictionary using cloudpickle."""
        return self._create('dict', *args, **kwargs)
    
    def list(self, *args, **kwargs) -> ListProxy:
        """Create a shared list using cloudpickle."""
        return self._create('list', *args, **kwargs)

# Register the types with the manager
CloudPickleManager.register('dict', dict, DictProxy)
CloudPickleManager.register('list', list, ListProxy)

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
    
    _manager_instance: Optional[CloudPickleManager] = None
    _original_pickler = None
    _lock = threading.RLock()
    _globally_enabled = False
    
    @classmethod
    def get_manager(cls) -> CloudPickleManager:
        """
        Get a singleton CloudPickleManager instance.
        
        The manager is automatically started and ready for use.
        
        Returns:
            CloudPickleManager: A started manager instance using cloudpickle.
            
        Example:
            manager = SKPickle.get_manager()
            shared_data = manager.dict({'initial': 'data'})
        """
        if cls._manager_instance is None:
            with cls._lock:
                if cls._manager_instance is None:
                    cls._manager_instance = CloudPickleManager()
                    cls._manager_instance.start()
        return cls._manager_instance
    
    @classmethod
    def shutdown_manager(cls):
        """
        Shutdown the singleton manager instance.
        
        Call this when you're done with multiprocessing to clean up resources.
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
                    cls._manager_instance = None
    
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
    def create_shared_dict(cls, initial_data: Optional[Dict] = None) -> DictProxy:
        """
        Create a shared dictionary using cloudpickle.
        
        Args:
            initial_data: Optional dictionary to initialize with.
            
        Returns:
            DictProxy: A cloudpickle-enabled shared dictionary.
            
        Example:
            # Empty dict
            shared_dict = SKPickle.create_shared_dict()
            
            # With initial data
            shared_dict = SKPickle.create_shared_dict({'key': 'value'})
        """
        manager = cls.get_manager()
        if initial_data:
            return manager.dict(initial_data)
        return manager.dict()
    
    @classmethod
    def create_shared_list(cls, initial_data: Optional[List] = None) -> ListProxy:
        """
        Create a shared list using cloudpickle.
        
        Args:
            initial_data: Optional list to initialize with.
            
        Returns:
            ListProxy: A cloudpickle-enabled shared list.
            
        Example:
            # Empty list
            shared_list = SKPickle.create_shared_list()
            
            # With initial data
            shared_list = SKPickle.create_shared_list([1, 2, 3])
        """
        manager = cls.get_manager()
        if initial_data:
            return manager.list(initial_data)
        return manager.list()
    
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
        """
        Serialize an object using cloudpickle.
        
        Args:
            obj: Object to serialize.
            
        Returns:
            bytes: Serialized object data.
            
        Raises:
            Exception: If serialization fails.
        """
        return cloudpickle.dumps(obj)
    
    @classmethod
    def deserialize(cls, data: bytes) -> Any:
        """
        Deserialize an object using cloudpickle.
        
        Args:
            data: Serialized object data.
            
        Returns:
            Any: The deserialized object.
            
        Raises:
            Exception: If deserialization fails.
        """
        return cloudpickle.loads(data)
    
    @classmethod
    def is_cloudpickle_enabled(cls) -> bool:
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
            'cloudpickle_available': True  # Since we import it successfully
        }


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