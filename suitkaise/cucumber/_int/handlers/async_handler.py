"""
Handler for async/await objects.

Includes coroutines, async generators, asyncio Tasks, Futures, etc.
These are challenging because they represent suspended execution state.

AI helped me with technical details, but:
- all of the basic structure is mine.
- comments and code has all been reviewed (and revised if needed) by me.

Do I know how this works? Yes.
DO I know every internal attribute and method? No. That's where AI came in,
so I didn't have to crawl Stack Overflow myself.

Cheers
"""

import sys
import types
from typing import Any, Dict
from .base_class import Handler

# try to import asyncio (3.4+)
try:
    import asyncio
    HAS_ASYNCIO = True
except ImportError:
    HAS_ASYNCIO = False
    asyncio = None  # type: ignore


class AsyncSerializationError(Exception):
    """Raised when async object serialization fails."""
    pass


class CoroutineHandler(Handler):
    """
    Serializes coroutine objects (from async def functions).
    
    Strategy:
    - Extract the coroutine function and any captured state
    - On reconstruction, recreate the coroutine (but not resume it)
    
    Important: Coroutine execution state (where it's suspended) cannot
    be fully serialized. We preserve the coroutine function but not
    the exact execution position.
    """
    
    type_name = "coroutine"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a coroutine."""
        return isinstance(obj, types.CoroutineType)
    
    def extract_state(self, obj: types.CoroutineType) -> Dict[str, Any]:
        """
        Extract coroutine state.
        
        What we capture:
        - cr_code: Coroutine's code object
        - cr_frame: Frame info (if available)
        - __name__: Coroutine name
        - __qualname__: Qualified name
        
        Note: We can't capture the exact execution state, so the
        reconstructed coroutine will start from the beginning.
        """
        # get coroutine metadata
        cr_code = obj.cr_code if hasattr(obj, 'cr_code') else None
        cr_name = obj.__name__ if hasattr(obj, '__name__') else 'coroutine'
        cr_qualname = obj.__qualname__ if hasattr(obj, '__qualname__') else cr_name
        
        # try to get frame locals
        frame_locals = None
        if hasattr(obj, 'cr_frame') and obj.cr_frame:
            try:
                frame_locals = dict(obj.cr_frame.f_locals)
            except (AttributeError, RuntimeError):
                pass
        
        return {
            "cr_code": cr_code,  # will be recursively serialized
            "cr_name": cr_name,
            "cr_qualname": cr_qualname,
            "frame_locals": frame_locals,
            "note": "Coroutine execution state cannot be fully preserved. "
                    "Reconstructed coroutine will start from the beginning."
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct coroutine.
        
        Since we can't reconstruct the exact execution state,
        we return a placeholder that explains this limitation.
        """
        class DeserializedCoroutine:
            """
            A deserialized coroutine placeholder.
            
            Coroutine execution state cannot be transferred across processes.
            This object contains metadata about the original coroutine.
            """
            def __init__(self, state_dict):
                self.cr_name = state_dict["cr_name"]
                self.cr_qualname = state_dict["cr_qualname"]
                self.frame_locals = state_dict.get("frame_locals")
                self._note = state_dict["note"]
                self._deserialized = True
            
            def __repr__(self):
                return f"<DeserializedCoroutine {self.cr_qualname} (not running)>"
            
            def __await__(self):
                raise AsyncSerializationError(
                    f"Cannot await deserialized coroutine {self.cr_qualname}. "
                    f"Coroutine execution state is not preserved during serialization."
                )
        
        return DeserializedCoroutine(state)


class AsyncGeneratorHandler(Handler):
    """
    Serializes async generator objects.
    
    Async generators are like regular generators but use 'async for'.
    """
    
    type_name = "async_generator"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is an async generator."""
        return isinstance(obj, types.AsyncGeneratorType)
    
    def extract_state(self, obj: types.AsyncGeneratorType) -> Dict[str, Any]:
        """
        Extract async generator state.
        
        Similar to coroutines, we can't preserve execution state.
        """
        ag_name = obj.__name__ if hasattr(obj, '__name__') else 'async_generator'
        ag_qualname = obj.__qualname__ if hasattr(obj, '__qualname__') else ag_name
        
        return {
            "ag_name": ag_name,
            "ag_qualname": ag_qualname,
            "note": "Async generator execution state cannot be preserved."
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """Reconstruct async generator placeholder."""
        class DeserializedAsyncGenerator:
            """Deserialized async generator placeholder."""
            def __init__(self, state_dict):
                self.ag_name = state_dict["ag_name"]
                self.ag_qualname = state_dict["ag_qualname"]
                self._deserialized = True
            
            def __repr__(self):
                return f"<DeserializedAsyncGenerator {self.ag_qualname} (not running)>"
            
            def __aiter__(self):
                raise AsyncSerializationError(
                    f"Cannot iterate deserialized async generator {self.ag_qualname}"
                )
        
        return DeserializedAsyncGenerator(state)


class TaskHandler(Handler):
    """
    Serializes asyncio.Task objects.
    
    Tasks wrap coroutines and manage their execution in the event loop.
    """
    
    type_name = "asyncio_task"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is an asyncio.Task."""
        if not HAS_ASYNCIO:
            return False
        return isinstance(obj, asyncio.Task)
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract Task state.
        
        What we capture:
        - Task name
        - Done status
        - Result (if done and no exception)
        - Exception (if done with exception)
        - Cancelled status
        """
        import asyncio
        
        is_done = obj.done()
        is_cancelled = obj.cancelled()
        
        result = None
        exception = None
        
        if is_done and not is_cancelled:
            try:
                result = obj.result()
            except Exception as e:
                exception = e
        
        task_name = obj.get_name() if hasattr(obj, 'get_name') else None
        
        return {
            "task_name": task_name,
            "is_done": is_done,
            "is_cancelled": is_cancelled,
            "result": result,  # will be recursively serialized
            "exception": exception,  # will be recursively serialized
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct Task.
        
        We create a completed Future-like object with the result/exception.
        """
        import asyncio
        
        class DeserializedTask:
            """Deserialized Task placeholder."""
            def __init__(self, state_dict):
                self._task_name = state_dict["task_name"]
                self._is_done = state_dict["is_done"]
                self._is_cancelled = state_dict["is_cancelled"]
                self._result = state_dict["result"]
                self._exception = state_dict["exception"]
                self._deserialized = True
            
            def done(self):
                return self._is_done
            
            def cancelled(self):
                return self._is_cancelled
            
            def result(self):
                if self._exception:
                    raise self._exception
                return self._result
            
            def exception(self):
                return self._exception
            
            def get_name(self):
                return self._task_name
            
            def __repr__(self):
                status = "done" if self._is_done else "pending"
                if self._is_cancelled:
                    status = "cancelled"
                return f"<DeserializedTask {self._task_name} {status}>"
        
        return DeserializedTask(state)


class FutureHandler(Handler):
    """
    Serializes asyncio.Future objects.
    
    Futures represent a result that will be available in the future.
    """
    
    type_name = "asyncio_future"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is an asyncio.Future."""
        if not HAS_ASYNCIO:
            return False

        # check for Future but not Task (Task is a subclass of Future)
        return isinstance(obj, asyncio.Future) and not isinstance(obj, asyncio.Task)
    
    def extract_state(self, obj: Any) -> Dict[str, Any]:
        """
        Extract Future state.
        
        Similar to Task extraction.
        """
        import asyncio
        
        is_done = obj.done()
        is_cancelled = obj.cancelled()
        
        result = None
        exception = None
        
        if is_done and not is_cancelled:
            try:
                result = obj.result()
            except Exception as e:
                exception = e
        
        return {
            "is_done": is_done,
            "is_cancelled": is_cancelled,
            "result": result,
            "exception": exception,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """Reconstruct Future."""
        import asyncio
        
        class DeserializedFuture:
            """Deserialized Future placeholder."""
            def __init__(self, state_dict):
                self._is_done = state_dict["is_done"]
                self._is_cancelled = state_dict["is_cancelled"]
                self._result = state_dict["result"]
                self._exception = state_dict["exception"]
                self._deserialized = True
            
            def done(self):
                return self._is_done
            
            def cancelled(self):
                return self._is_cancelled
            
            def result(self):
                if not self._is_done:
                    raise asyncio.InvalidStateError("Result is not ready")
                if self._exception:
                    raise self._exception
                return self._result
            
            def exception(self):
                if not self._is_done:
                    raise asyncio.InvalidStateError("Exception is not ready")
                return self._exception
            
            def __repr__(self):
                status = "done" if self._is_done else "pending"
                if self._is_cancelled:
                    status = "cancelled"
                return f"<DeserializedFuture {status}>"
        
        return DeserializedFuture(state)

