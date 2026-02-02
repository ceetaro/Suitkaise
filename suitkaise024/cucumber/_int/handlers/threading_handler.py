"""
Handler for threading-related objects.

Includes Thread objects, Executors, and threading.local storage.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Any, Dict
from .base_class import Handler


class ThreadingSerializationError(Exception):
    """Raised when threading object serialization fails."""
    pass


class ThreadHandler(Handler):
    """
    Serializes threading.Thread objects (8% importance).
    
    Threads are execution contexts. We can't truly serialize a running thread,
    but we can capture its configuration.
    
    Important: The actual thread execution state (call stack, local variables)
    cannot be serialized. We only capture thread metadata.
    """
    
    type_name = "thread"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a Thread."""
        return isinstance(obj, threading.Thread)
    
    def extract_state(self, obj: threading.Thread) -> Dict[str, Any]:
        """
        Extract thread metadata.
        
        What we capture:
        - name: Thread name
        - daemon: Whether thread is a daemon
        - target: Target function (will be recursively serialized)
        - args: Arguments for target
        - kwargs: Keyword arguments for target
        - is_alive: Whether thread is currently running
        
        Note: We can't serialize the thread's execution state.
        If the thread is running, it will NOT be running after deserialization.
        """
        return {
            "name": obj.name,
            "daemon": obj.daemon,
            "target": getattr(obj, '_target', None),
            "args": getattr(obj, '_args', ()),
            "kwargs": getattr(obj, '_kwargs', {}),
            "is_alive": obj.is_alive(),
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> threading.Thread:
        """
        Reconstruct thread.
        
        Creates new thread with same configuration.
        Note: Thread is NOT started automatically. User must call start().
        """
        thread = threading.Thread(
            name=state["name"],
            target=state["target"],
            args=state["args"],
            kwargs=state["kwargs"],
            daemon=state["daemon"]
        )
        
        # Don't start the thread automatically - let user decide
        # This prevents unexpected execution
        
        return thread


class ThreadPoolExecutorHandler(Handler):
    """
    Serializes ThreadPoolExecutor objects (7% importance).
    
    Executors manage pools of threads/processes for parallel execution.
    We serialize the configuration, not running tasks.
    """
    
    type_name = "thread_pool_executor"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a ThreadPoolExecutor."""
        return isinstance(obj, ThreadPoolExecutor)
    
    def extract_state(self, obj: ThreadPoolExecutor) -> Dict[str, Any]:
        """
        Extract executor configuration.
        
        What we capture:
        - max_workers: Number of worker threads
        - thread_name_prefix: Prefix for thread names
        
        Note: Running tasks and futures are NOT serialized.
        User must resubmit tasks after deserialization.
        """
        return {
            "max_workers": getattr(obj, '_max_workers', None),
            "thread_name_prefix": getattr(obj, '_thread_name_prefix', ''),
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> ThreadPoolExecutor:
        """
        Reconstruct executor.
        
        Creates fresh executor with same configuration.
        No tasks are running.
        """
        return ThreadPoolExecutor(
            max_workers=state["max_workers"],
            thread_name_prefix=state["thread_name_prefix"]
        )


class ProcessPoolExecutorHandler(Handler):
    """
    Serializes ProcessPoolExecutor objects (7% importance).
    
    Similar to ThreadPoolExecutor but for processes.
    """
    
    type_name = "process_pool_executor"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a ProcessPoolExecutor."""
        return isinstance(obj, ProcessPoolExecutor)
    
    def extract_state(self, obj: ProcessPoolExecutor) -> Dict[str, Any]:
        """
        Extract executor configuration.
        
        What we capture:
        - max_workers: Number of worker processes
        """
        return {
            "max_workers": getattr(obj, '_max_workers', None),
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> ProcessPoolExecutor:
        """
        Reconstruct executor.
        
        Creates fresh executor with same configuration.
        """
        return ProcessPoolExecutor(
            max_workers=state["max_workers"]
        )


class ThreadLocalHandler(Handler):
    """
    Serializes threading.local objects (2% importance).
    
    threading.local provides thread-local storage - each thread
    sees its own values. We serialize the current thread's values.
    """
    
    type_name = "thread_local"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is threading.local."""
        return isinstance(obj, threading.local)
    
    def extract_state(self, obj: threading.local) -> Dict[str, Any]:
        """
        Extract thread-local storage.
        
        What we capture:
        - data: Dict of current thread's local values
        
        Note: Only the CURRENT thread's values are serialized.
        Other threads' values are lost (which is usually fine since
        we're serializing for a different process anyway).
        """
        # Get current thread's local data
        # threading.local stores data in obj.__dict__
        data = {}
        try:
            data = dict(obj.__dict__)
        except AttributeError:
            # No __dict__ on this threading.local - use empty dict
            pass
        except Exception as e:
            # Unexpected error accessing thread-local data
            import warnings
            warnings.warn(f"Failed to extract threading.local data: {e}")
        
        return {
            "data": data,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> threading.local:
        """
        Reconstruct threading.local.
        
        Creates new threading.local and populates it with data.
        """
        local = threading.local()
        
        # Set attributes
        for key, value in state["data"].items():
            setattr(local, key, value)
        
        return local

