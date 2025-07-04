"""
Queue Objects Serialization Handler

This module provides serialization support for queue objects used in threading
and async programming that cannot be pickled due to their internal synchronization
primitives and system-level state.

SUPPORTED OBJECTS:
==================

1. THREADING QUEUES:
   - queue.Queue (FIFO queue)
   - queue.LifoQueue (LIFO stack)
   - queue.PriorityQueue (priority-ordered queue)
   - queue.SimpleQueue (Python 3.7+)

2. ASYNCIO QUEUES:
   - asyncio.Queue (async FIFO queue)
   - asyncio.LifoQueue (async LIFO stack)
   - asyncio.PriorityQueue (async priority queue)

3. MULTIPROCESSING QUEUES:
   - multiprocessing.Queue
   - multiprocessing.JoinableQueue
   - multiprocessing.SimpleQueue

4. CUSTOM QUEUE IMPLEMENTATIONS:
   - Queues inheriting from queue.Queue
   - Custom queue-like objects with put/get methods

SERIALIZATION STRATEGY:
======================

Queue serialization is challenging because:
- Queues contain internal locks and conditions
- Items may be in transit during serialization
- Queue state includes waiting threads/tasks
- Size limits and blocking behavior are part of the state

Our approach:
1. **Extract current items** from the queue (drain and restore)
2. **Store queue configuration** (maxsize, queue type)
3. **Preserve queue metadata** (task counting, etc.)
4. **Handle blocking operations** carefully during extraction
5. **Recreate with same semantics** but new synchronization primitives

LIMITATIONS:
============
- Waiting threads/tasks are not preserved
- Queue performance characteristics may differ slightly
- Custom queue subclasses may lose specialized behavior  
- Multiprocessing queues lose cross-process capability
- Very large queues may impact serialization performance

"""

import queue
import asyncio
import multiprocessing
import threading
import time
from typing import Any, Dict, Optional, List, Union

try:
    from ..cerial_core import _NSO_Handler
except ImportError:
    # Fallback for testing
    from cerial_core import _NSO_Handler


class QueuesHandler(_NSO_Handler):
    """Handler for queue objects including threading, asyncio, and multiprocessing queues."""
    
    def __init__(self):
        """Initialize the queues handler."""
        super().__init__()
        self._handler_name = "QueuesHandler"
        self._priority = 35  # High priority since queues are common in concurrent code
        
        # Timeout for queue operations during serialization
        self._operation_timeout = 0.1  # 100ms timeout to avoid blocking
        
        # Maximum number of items to extract from queue
        self._max_queue_items = 10000
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if this handler can serialize the given queue object.
        
        Args:
            obj: Object to check
            
        Returns:
            True if this handler can process the object
            
        DETECTION LOGIC:
        - Check for threading queue types (queue.Queue, etc.)
        - Check for asyncio queue types (asyncio.Queue, etc.)
        - Check for multiprocessing queue types
        - Check for queue-like objects with put/get methods
        """
        try:
            # Threading queues
            if isinstance(obj, queue.Queue):
                return True
            if isinstance(obj, queue.LifoQueue):
                return True
            if isinstance(obj, queue.PriorityQueue):
                return True
            if hasattr(queue, 'SimpleQueue') and isinstance(obj, queue.SimpleQueue):
                return True
            
            # Asyncio queues
            if hasattr(asyncio, 'Queue') and isinstance(obj, asyncio.Queue):
                return True
            if hasattr(asyncio, 'LifoQueue') and isinstance(obj, asyncio.LifoQueue):
                return True
            if hasattr(asyncio, 'PriorityQueue') and isinstance(obj, asyncio.PriorityQueue):
                return True
            
            # Multiprocessing queues
            try:
                if isinstance(obj, multiprocessing.Queue):
                    return True
                if hasattr(multiprocessing, 'JoinableQueue') and isinstance(obj, multiprocessing.JoinableQueue):
                    return True
                if hasattr(multiprocessing, 'SimpleQueue') and isinstance(obj, multiprocessing.SimpleQueue):
                    return True
            except (ImportError, AttributeError):
                # Some multiprocessing types might not be available
                pass
            
            # Check by type name and module for queue-like objects
            obj_type_name = type(obj).__name__
            obj_module = getattr(type(obj), '__module__', '')
            
            # Threading queue types
            if 'queue' in obj_module and obj_type_name in [
                'Queue', 'LifoQueue', 'PriorityQueue', 'SimpleQueue'
            ]:
                return True
            
            # Asyncio queue types
            if 'asyncio' in obj_module and 'queue' in obj_type_name.lower():
                return True
            
            # Multiprocessing queue types
            if 'multiprocessing' in obj_module and 'queue' in obj_type_name.lower():
                return True
            
            # Generic queue-like object detection
            has_put = hasattr(obj, 'put')
            has_get = hasattr(obj, 'get')
            has_empty = hasattr(obj, 'empty')
            has_qsize = hasattr(obj, 'qsize')
            
            # Must have basic queue interface
            if has_put and has_get and (has_empty or has_qsize):
                # But exclude common non-queue objects
                excluded_types = {
                    'dict', 'list', 'tuple', 'set', 'frozenset', 'str', 'bytes'
                }
                if obj_type_name not in excluded_types:
                    return True
            
            return False
            
        except Exception:
            # If type checking fails, assume we can't handle it
            return False
    
    def serialize(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize a queue object to a dictionary representation.
        
        Args:
            obj: Queue object to serialize
            
        Returns:
            Dictionary containing all data needed to recreate the queue
            
        SERIALIZATION PROCESS:
        1. Determine queue type and characteristics
        2. Extract current queue items safely
        3. Store queue configuration (maxsize, etc.)
        4. Handle different queue semantics
        5. Restore queue state after extraction
        """
        # Base serialization data
        data = {
            "queue_type": self._get_queue_type(obj),
            "object_class": f"{type(obj).__module__}.{type(obj).__name__}",
            "serialization_strategy": None,  # Will be determined below
            "recreation_possible": False,
            "note": None
        }
        
        # Route to appropriate serialization method based on type
        queue_type = data["queue_type"]
        
        if queue_type in ["threading_queue", "threading_lifo", "threading_priority", "threading_simple"]:
            data.update(self._serialize_threading_queue(obj))
            data["serialization_strategy"] = "threading_queue_recreation"
            
        elif queue_type in ["asyncio_queue", "asyncio_lifo", "asyncio_priority"]:
            data.update(self._serialize_asyncio_queue(obj))
            data["serialization_strategy"] = "asyncio_queue_recreation"
            
        elif queue_type in ["multiprocessing_queue", "multiprocessing_joinable", "multiprocessing_simple"]:
            data.update(self._serialize_multiprocessing_queue(obj))
            data["serialization_strategy"] = "multiprocessing_queue_recreation"
            
        elif queue_type == "custom_queue":
            data.update(self._serialize_custom_queue(obj))
            data["serialization_strategy"] = "custom_queue_recreation"
            
        else:
            # Unknown queue type
            data.update(self._serialize_unknown_queue(obj))
            data["serialization_strategy"] = "fallback_placeholder"
        
        return data
    
    def deserialize(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize a queue object from dictionary representation.
        
        Args:
            data: Dictionary containing serialized queue data
            
        Returns:
            Recreated queue object (with limitations noted in documentation)
            
        DESERIALIZATION PROCESS:
        1. Determine serialization strategy used
        2. Route to appropriate recreation method
        3. Restore queue with configuration and items
        4. Handle errors gracefully with placeholders
        """
        strategy = data.get("serialization_strategy", "fallback_placeholder")
        queue_type = data.get("queue_type", "unknown")
        
        try:
            if strategy == "threading_queue_recreation":
                return self._deserialize_threading_queue(data)
            
            elif strategy == "asyncio_queue_recreation":
                return self._deserialize_asyncio_queue(data)
            
            elif strategy == "multiprocessing_queue_recreation":
                return self._deserialize_multiprocessing_queue(data)
            
            elif strategy == "custom_queue_recreation":
                return self._deserialize_custom_queue(data)
            
            elif strategy == "fallback_placeholder":
                return self._deserialize_unknown_queue(data)
            
            else:
                raise ValueError(f"Unknown serialization strategy: {strategy}")
                
        except Exception as e:
            # If deserialization fails, return a placeholder
            return self._create_error_placeholder(queue_type, str(e))
    
    # ========================================================================
    # QUEUE TYPE DETECTION METHODS
    # ========================================================================
    
    def _get_queue_type(self, obj: Any) -> str:
        """
        Determine the specific type of queue object.
        
        Args:
            obj: Queue object to analyze
            
        Returns:
            String identifying the queue type
        """
        obj_type = type(obj)
        obj_module = getattr(obj_type, '__module__', '')
        obj_name = obj_type.__name__
        
        # Threading queues
        if isinstance(obj, queue.Queue) and not isinstance(obj, (queue.LifoQueue, queue.PriorityQueue)):
            return "threading_queue"
        elif isinstance(obj, queue.LifoQueue):
            return "threading_lifo"
        elif isinstance(obj, queue.PriorityQueue):
            return "threading_priority"
        elif hasattr(queue, 'SimpleQueue') and isinstance(obj, queue.SimpleQueue):
            return "threading_simple"
        
        # Asyncio queues
        elif hasattr(asyncio, 'Queue') and isinstance(obj, asyncio.Queue):
            if isinstance(obj, getattr(asyncio, 'LifoQueue', type(None))):
                return "asyncio_lifo"
            elif isinstance(obj, getattr(asyncio, 'PriorityQueue', type(None))):
                return "asyncio_priority"
            else:
                return "asyncio_queue"
        
        # Multiprocessing queues
        elif 'multiprocessing' in obj_module:
            if 'JoinableQueue' in obj_name:
                return "multiprocessing_joinable"
            elif 'SimpleQueue' in obj_name:
                return "multiprocessing_simple"
            else:
                return "multiprocessing_queue"
        
        # Custom queue-like objects
        elif hasattr(obj, 'put') and hasattr(obj, 'get'):
            return "custom_queue"
        
        return "unknown"
    
    # ========================================================================
    # THREADING QUEUE SERIALIZATION
    # ========================================================================
    
    def _serialize_threading_queue(self, q) -> Dict[str, Any]:
        """
        Serialize threading queue objects.
        
        Extract items and configuration from threading queues.
        """
        result = {
            "queue_maxsize": getattr(q, 'maxsize', 0),
            "queue_items": [],
            "queue_size": 0,
            "extraction_successful": False,
            "queue_subtype": type(q).__name__
        }
        
        try:
            # Get current queue size
            try:
                result["queue_size"] = q.qsize()
            except Exception:
                result["queue_size"] = 0
            
            # Extract items from queue
            items = []
            extracted_count = 0
            
            # Use a timeout to avoid blocking indefinitely
            while extracted_count < self._max_queue_items:
                try:
                    # Try to get an item without blocking for too long
                    item = q.get(timeout=self._operation_timeout)
                    items.append(item)
                    extracted_count += 1
                except queue.Empty:
                    # Queue is empty, we're done
                    break
                except Exception as e:
                    # Some other error occurred
                    result["note"] = f"Error extracting item {extracted_count}: {e}"
                    break
            
            # Store the extracted items
            result["queue_items"] = items
            result["extraction_successful"] = True
            
            # Try to restore items to the queue (be a good citizen)
            for item in reversed(items):  # Restore in reverse order for FIFO
                try:
                    q.put(item, timeout=self._operation_timeout)
                except Exception:
                    # If we can't restore, note it but don't fail
                    result["note"] = f"Could not restore all items to queue after extraction"
                    break
            
        except Exception as e:
            result["note"] = f"Error serializing threading queue: {e}"
        
        result["recreation_possible"] = result["extraction_successful"]
        result["limitation"] = "Queue synchronization state and waiting threads are lost"
        
        return result
    
    def _deserialize_threading_queue(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize threading queue objects by recreating with items.
        """
        queue_maxsize = data.get("queue_maxsize", 0)
        queue_items = data.get("queue_items", [])
        queue_subtype = data.get("queue_subtype", "Queue")
        
        try:
            # Create the appropriate queue type
            if queue_subtype == "LifoQueue":
                q = queue.LifoQueue(maxsize=queue_maxsize)
            elif queue_subtype == "PriorityQueue":
                q = queue.PriorityQueue(maxsize=queue_maxsize)
            elif queue_subtype == "SimpleQueue" and hasattr(queue, 'SimpleQueue'):
                q = queue.SimpleQueue()
            else:
                q = queue.Queue(maxsize=queue_maxsize)
            
            # Add items back to the queue
            for item in queue_items:
                try:
                    q.put(item, timeout=self._operation_timeout)
                except Exception:
                    # If we can't add an item, skip it but continue
                    pass
            
            return q
            
        except Exception as e:
            raise ValueError(f"Could not recreate threading queue: {e}")
    
    # ========================================================================
    # ASYNCIO QUEUE SERIALIZATION
    # ========================================================================
    
    def _serialize_asyncio_queue(self, q) -> Dict[str, Any]:
        """
        Serialize asyncio queue objects.
        
        Extract items and configuration from asyncio queues.
        """
        result = {
            "queue_maxsize": getattr(q, '_maxsize', 0),
            "queue_items": [],
            "queue_size": 0,
            "extraction_successful": False,
            "queue_subtype": type(q).__name__
        }
        
        try:
            # Get current queue size
            try:
                result["queue_size"] = q.qsize()
            except Exception:
                result["queue_size"] = 0
            
            # Extract items from asyncio queue
            # Note: asyncio queues don't have blocking get with timeout,
            # so we use get_nowait() in a loop
            items = []
            extracted_count = 0
            
            while extracted_count < self._max_queue_items:
                try:
                    item = q.get_nowait()
                    items.append(item)
                    extracted_count += 1
                except asyncio.QueueEmpty:
                    # Queue is empty, we're done
                    break
                except Exception as e:
                    result["note"] = f"Error extracting item {extracted_count}: {e}"
                    break
            
            # Store the extracted items
            result["queue_items"] = items
            result["extraction_successful"] = True
            
            # Try to restore items to the queue
            for item in reversed(items):  # Restore in reverse order for FIFO
                try:
                    q.put_nowait(item)
                except Exception:
                    result["note"] = f"Could not restore all items to asyncio queue after extraction"
                    break
            
        except Exception as e:
            result["note"] = f"Error serializing asyncio queue: {e}"
        
        result["recreation_possible"] = result["extraction_successful"]
        result["limitation"] = "Queue async state and waiting tasks are lost"
        
        return result
    
    def _deserialize_asyncio_queue(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize asyncio queue objects by recreating with items.
        """
        queue_maxsize = data.get("queue_maxsize", 0)
        queue_items = data.get("queue_items", [])
        queue_subtype = data.get("queue_subtype", "Queue")
        
        try:
            # Create the appropriate asyncio queue type
            if queue_subtype == "LifoQueue" and hasattr(asyncio, 'LifoQueue'):
                q = asyncio.LifoQueue(maxsize=queue_maxsize)
            elif queue_subtype == "PriorityQueue" and hasattr(asyncio, 'PriorityQueue'):
                q = asyncio.PriorityQueue(maxsize=queue_maxsize)
            else:
                q = asyncio.Queue(maxsize=queue_maxsize)
            
            # Add items back to the queue
            for item in queue_items:
                try:
                    q.put_nowait(item)
                except Exception:
                    # If we can't add an item, skip it but continue
                    pass
            
            return q
            
        except Exception as e:
            raise ValueError(f"Could not recreate asyncio queue: {e}")
    
    # ========================================================================
    # MULTIPROCESSING QUEUE SERIALIZATION
    # ========================================================================
    
    def _serialize_multiprocessing_queue(self, q) -> Dict[str, Any]:
        """
        Serialize multiprocessing queue objects.
        
        Extract items and configuration from multiprocessing queues.
        """
        result = {
            "queue_maxsize": getattr(q, '_maxsize', 0),
            "queue_items": [],
            "queue_size": 0,
            "extraction_successful": False,
            "queue_subtype": type(q).__name__
        }
        
        try:
            # Get current queue size (if available)
            try:
                result["queue_size"] = q.qsize() if hasattr(q, 'qsize') else 0
            except Exception:
                result["queue_size"] = 0
            
            # Extract items from multiprocessing queue
            items = []
            extracted_count = 0
            
            while extracted_count < self._max_queue_items:
                try:
                    # Try to get an item without blocking
                    item = q.get(timeout=self._operation_timeout) if hasattr(q, 'get') else q.get_nowait()
                    items.append(item)
                    extracted_count += 1
                except:
                    # Queue is empty or get failed
                    break
            
            # Store the extracted items
            result["queue_items"] = items
            result["extraction_successful"] = True
            
            # Try to restore items to the queue
            for item in reversed(items):
                try:
                    if hasattr(q, 'put'):
                        q.put(item, timeout=self._operation_timeout)
                    else:
                        q.put_nowait(item)
                except Exception:
                    result["note"] = f"Could not restore all items to multiprocessing queue after extraction"
                    break
            
        except Exception as e:
            result["note"] = f"Error serializing multiprocessing queue: {e}"
        
        result["recreation_possible"] = result["extraction_successful"]
        result["limitation"] = "Multiprocessing queue will be converted to threading queue"
        
        return result
    
    def _deserialize_multiprocessing_queue(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize multiprocessing queue objects.
        
        Note: We convert to threading queues since multiprocessing queues
        can't be recreated without a multiprocessing context.
        """
        queue_maxsize = data.get("queue_maxsize", 0)
        queue_items = data.get("queue_items", [])
        queue_subtype = data.get("queue_subtype", "Queue")
        
        try:
            # Convert to threading queue since multiprocessing queues
            # require specific multiprocessing context
            if "Joinable" in queue_subtype:
                # Create a regular queue for joinable queues
                q = queue.Queue(maxsize=queue_maxsize)
            else:
                q = queue.Queue(maxsize=queue_maxsize)
            
            # Add items back to the queue
            for item in queue_items:
                try:
                    q.put(item, timeout=self._operation_timeout)
                except Exception:
                    pass
            
            return q
            
        except Exception as e:
            raise ValueError(f"Could not recreate multiprocessing queue: {e}")
    
    # ========================================================================
    # CUSTOM QUEUE SERIALIZATION
    # ========================================================================
    
    def _serialize_custom_queue(self, q) -> Dict[str, Any]:
        """
        Serialize custom queue-like objects.
        
        Attempt to extract items using standard queue interface.
        """
        result = {
            "queue_class": f"{type(q).__module__}.{type(q).__name__}",
            "queue_items": [],
            "queue_size": 0,
            "extraction_successful": False,
            "has_maxsize": hasattr(q, 'maxsize'),
            "queue_maxsize": getattr(q, 'maxsize', 0)
        }
        
        try:
            # Get current queue size
            if hasattr(q, 'qsize'):
                try:
                    result["queue_size"] = q.qsize()
                except Exception:
                    result["queue_size"] = 0
            elif hasattr(q, '__len__'):
                try:
                    result["queue_size"] = len(q)
                except Exception:
                    result["queue_size"] = 0
            
            # Try to extract items
            items = []
            extracted_count = 0
            
            while extracted_count < self._max_queue_items:
                try:
                    # Try different methods to get items
                    if hasattr(q, 'get_nowait'):
                        item = q.get_nowait()
                    elif hasattr(q, 'get'):
                        # Try get with timeout if available
                        item = q.get(timeout=self._operation_timeout)
                    else:
                        break  # No way to get items
                    
                    items.append(item)
                    extracted_count += 1
                    
                except:
                    # Queue is empty or method failed
                    break
            
            result["queue_items"] = items
            result["extraction_successful"] = True
            
            # Try to restore items
            for item in reversed(items):
                try:
                    if hasattr(q, 'put_nowait'):
                        q.put_nowait(item)
                    elif hasattr(q, 'put'):
                        q.put(item)
                    else:
                        break
                except Exception:
                    result["note"] = f"Could not restore all items to custom queue after extraction"
                    break
            
        except Exception as e:
            result["note"] = f"Error serializing custom queue: {e}"
        
        result["recreation_possible"] = False  # Custom queues are hard to recreate
        result["limitation"] = "Custom queue will be converted to standard threading queue"
        
        return result
    
    def _deserialize_custom_queue(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize custom queue objects.
        
        Convert to standard threading queue since we can't recreate custom classes.
        """
        queue_items = data.get("queue_items", [])
        queue_maxsize = data.get("queue_maxsize", 0)
        
        try:
            # Create standard threading queue
            q = queue.Queue(maxsize=queue_maxsize)
            
            # Add items back
            for item in queue_items:
                try:
                    q.put(item, timeout=self._operation_timeout)
                except Exception:
                    pass
            
            return q
            
        except Exception as e:
            raise ValueError(f"Could not recreate custom queue: {e}")
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _serialize_unknown_queue(self, obj: Any) -> Dict[str, Any]:
        """
        Serialize unknown queue types with basic metadata.
        """
        return {
            "object_repr": repr(obj)[:200],
            "object_type": type(obj).__name__,
            "object_module": getattr(type(obj), '__module__', 'unknown'),
            "has_put": hasattr(obj, 'put'),
            "has_get": hasattr(obj, 'get'),
            "has_qsize": hasattr(obj, 'qsize'),
            "has_empty": hasattr(obj, 'empty'),
            "note": f"Unknown queue type {type(obj).__name__} - limited serialization"
        }
    
    def _deserialize_unknown_queue(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize unknown queue types with placeholder.
        """
        object_type = data.get("object_type", "unknown")
        
        class QueuePlaceholder:
            def __init__(self, obj_type):
                self.obj_type = obj_type
                self._items = []
                self.maxsize = 0
            
            def put(self, item, block=True, timeout=None):
                self._items.append(item)
            
            def get(self, block=True, timeout=None):
                if self._items:
                    return self._items.pop(0)
                else:
                    raise queue.Empty()
            
            def put_nowait(self, item):
                self.put(item, block=False)
            
            def get_nowait(self):
                return self.get(block=False)
            
            def empty(self):
                return len(self._items) == 0
            
            def qsize(self):
                return len(self._items)
            
            def __repr__(self):
                return f"<QueuePlaceholder type='{self.obj_type}' size={len(self._items)}>"
        
        return QueuePlaceholder(object_type)
    
    def _create_error_placeholder(self, queue_type: str, error_message: str) -> Any:
        """
        Create a placeholder queue object for objects that failed to deserialize.
        """
        class QueueErrorPlaceholder:
            def __init__(self, obj_type, error):
                self.obj_type = obj_type
                self.error = error
            
            def put(self, *args, **kwargs):
                raise RuntimeError(f"Queue ({self.obj_type}) deserialization failed: {self.error}")
            
            def get(self, *args, **kwargs):
                raise RuntimeError(f"Queue ({self.obj_type}) deserialization failed: {self.error}")
            
            def __repr__(self):
                return f"<QueueErrorPlaceholder type='{self.obj_type}' error='{self.error}'>"
        
        return QueueErrorPlaceholder(queue_type, error_message)


# Create a singleton instance for auto-registration
queues_handler = QueuesHandler()