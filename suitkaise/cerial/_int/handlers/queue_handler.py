"""
Handler for queue objects.

Queues are thread-safe data structures for producer-consumer patterns.
We serialize the queue type, maxsize, and all items currently in the queue.
"""

import queue
import threading
import multiprocessing
import multiprocessing.queues
import multiprocessing.synchronize
from typing import Any, Dict, List
from .base_class import Handler


class QueueSerializationError(Exception):
    """Raised when queue serialization fails."""
    pass


class QueueHandler(Handler):
    """
    Serializes queue.Queue objects (threading queues).
    
    Strategy:
    - Non-destructive: snapshot queue contents using queue.queue
    - Capture maxsize and queue type
    - On reconstruction, create new queue and put items back
    
    Note: We create a snapshot of the queue without draining it,
    preserving the original queue's state.
    """
    
    type_name = "queue"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a queue.Queue."""
        return isinstance(obj, queue.Queue)
    
    def extract_state(self, obj: queue.Queue) -> Dict[str, Any]:
        """
        Extract queue state non-destructively.
        
        What we capture:
        - queue_type: Type name (Queue, LifoQueue, PriorityQueue)
        - maxsize: Maximum queue size (0 = unlimited)
        - items: Snapshot of items currently in queue
        
        Note: We access the internal deque to create a snapshot without draining.
        This preserves the original queue's state for continued use.
        """
        # Determine specific queue type
        queue_type_name = type(obj).__name__
        
        # Get maxsize
        maxsize = obj.maxsize
        
        # Non-destructive snapshot: access internal queue
        # queue.Queue uses a collections.deque internally as .queue
        with obj.mutex:  # Lock the queue to get consistent snapshot
            items = list(obj.queue)  # Copy the deque contents
        
        return {
            "queue_type": queue_type_name,
            "maxsize": maxsize,
            "items": items,  # Will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> queue.Queue:
        """
        Reconstruct queue from state.
        
        Process:
        1. Create new queue of appropriate type and maxsize
        2. Put all items back in (already deserialized)
        """
        # Create queue of appropriate type
        queue_type = state["queue_type"]
        maxsize = state["maxsize"]
        
        if queue_type == "LifoQueue":
            q = queue.LifoQueue(maxsize=maxsize)
        elif queue_type == "PriorityQueue":
            q = queue.PriorityQueue(maxsize=maxsize)
        else:
            q = queue.Queue(maxsize=maxsize)
        
        # Put items back (already deserialized by central deserializer)
        for item in state["items"]:
            q.put(item)
        
        return q


class MultiprocessingQueueHandler(Handler):
    """
    Serializes multiprocessing.Queue objects.
    
    These are inter-process queues that use pipes and shared memory.
    They're more complex than threading queues.
    """
    
    type_name = "mp_queue"
    
    def can_handle(self, obj: Any) -> bool:
        """
        Check if object is a multiprocessing.Queue.
        
        Note: multiprocessing.Queue is actually a function that returns
        a queue object, so we check for the internal queue types.
        """
        return isinstance(obj, multiprocessing.queues.Queue)
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract multiprocessing queue state.
        
        What we capture:
        - maxsize: Maximum queue size
        - items: Snapshot of items currently in queue
        
        Note: Multiprocessing queues don't expose internal state easily.
        We attempt a non-blocking snapshot up to a reasonable limit.
        """
        maxsize = obj._maxsize if hasattr(obj, '_maxsize') else 0
        
        # Attempt to snapshot queue non-destructively
        # Unfortunately, mp.Queue doesn't expose internal deque like queue.Queue
        # Best we can do is qsize() if available
        items = []
        try:
            size = obj.qsize()
            # Get items without blocking (limited snapshot)
            for _ in range(min(size, 10000)):  # Safety limit
                try:
                    items.append(obj.get_nowait())
                except:
                    break
            # Put items back to restore state
            for item in items:
                obj.put(item)
        except (NotImplementedError, AttributeError):
            # qsize() not available on all platforms
            pass
        
        return {
            "maxsize": maxsize,
            "items": items,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct multiprocessing queue.
        
        Note: We create a new queue. It will have different underlying
        pipes and shared memory than the original.
        """
        # Create new multiprocessing queue
        q = multiprocessing.Queue(maxsize=state["maxsize"])
        
        # Put items back
        for item in state["items"]:
            q.put(item)
        
        return q


class EventHandler(Handler):
    """
    Serializes threading.Event objects.
    
    Events are simple synchronization primitives - they're either
    set (signaled) or clear (not signaled).
    """
    
    type_name = "event"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a threading.Event."""
        return isinstance(obj, threading.Event)
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract event state.
        
        What we capture:
        - is_set: Whether event is currently set (True) or clear (False)
        
        This is all we need - Events are very simple!
        """
        return {
            "is_set": obj.is_set(),
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> threading.Event:
        """
        Reconstruct event.
        
        Process:
        1. Create new Event
        2. Set it if it was set
        """
        event = threading.Event()
        
        if state["is_set"]:
            event.set()
        
        return event


class MultiprocessingEventHandler(Handler):
    """
    Serializes multiprocessing.Event objects.
    
    Similar to threading.Event but for cross-process synchronization.
    """
    
    type_name = "mp_event"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a multiprocessing.Event."""
        return isinstance(obj, multiprocessing.synchronize.Event)
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract multiprocessing event state.
        
        Same as threading.Event - just whether it's set or not.
        """
        return {
            "is_set": obj.is_set(),
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct multiprocessing event.
        
        Note: Creates new event with different underlying shared memory.
        """
        event = multiprocessing.Event()
        
        if state["is_set"]:
            event.set()
        
        return event

