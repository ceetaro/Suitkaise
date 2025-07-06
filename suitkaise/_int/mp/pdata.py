"""
Xprocess Internal Cross-processing Engine - Process Data Classes

This module contains the PData class for standardized process data representation
and result handling across the multiprocessing system.
"""

from typing import Any, Optional, Dict
from .processes import PStatus


class _PData:
    """
    Internal standardized process data container.
    
    This class provides a unified interface for accessing process metadata,
    status, and results. It replaces the previous mixed return types with
    a consistent data structure.
    """
    
    def __init__(self, pkey: str, pclass: str, pid: Optional[int], 
                 num_loops: Optional[int], completed_loops: int = 0):
        """
        Initialize process data container.
        
        Args:
            pkey: Unique process key for tracking
            pclass: Process class name/identifier  
            pid: Process ID (None if not started)
            num_loops: Maximum number of loops (None = infinite)
            completed_loops: Number of completed loops
        """
        self._pkey = pkey
        self._pclass = pclass
        self._pid = pid
        self._num_loops = num_loops
        self._completed_loops = completed_loops
        self._result = None  # Result from __result__ method or error
        self._status = PStatus.CREATED
        self._error = None   # Error information if process failed
        
    # =============================================================================
    # PUBLIC PROPERTIES - Clean interface for accessing process data
    # =============================================================================
    
    @property
    def pkey(self) -> str:
        """Unique process key for tracking."""
        return self._pkey
        
    @property
    def name(self) -> str:
        """Alias for pkey - the unique tracking key."""
        return self._pkey
        
    @property
    def pclass(self) -> str:
        """Process class name/identifier."""
        return self._pclass
        
    @property
    def pid(self) -> Optional[int]:
        """Process ID (None if not started)."""
        return self._pid
        
    @property
    def num_loops(self) -> Optional[int]:
        """Maximum number of loops (None = infinite)."""
        return self._num_loops
        
    @property
    def completed_loops(self) -> int:
        """Number of completed loops."""
        return self._completed_loops
        
    @property
    def status(self) -> PStatus:
        """Current process status."""
        return self._status
        
    @property
    def result(self) -> Any:
        """
        Get the process result.
        
        Returns:
            The result from the process __result__ method
            
        Raises:
            ProcessResultError: If the process had an error
        """
        if self._error is not None:
            raise ProcessResultError(f"Process '{self._pkey}' failed: {self._error}")
        return self._result
        
    @property
    def has_error(self) -> bool:
        """Check if the process had an error."""
        return self._error is not None
        
    @property
    def error(self) -> Optional[str]:
        """Get error information if process failed."""
        return self._error
        
    # =============================================================================
    # INTERNAL METHODS - Used by process management system
    # =============================================================================
    
    def _update_pid(self, pid: int):
        """Update the process ID."""
        self._pid = pid
        
    def _update_completed_loops(self, completed_loops: int):
        """Update the number of completed loops."""
        self._completed_loops = completed_loops
        
    def _update_status(self, status: PStatus):
        """Update the process status."""
        self._status = status
        
    def _set_result(self, result: Any):
        """Set the process result."""
        self._result = result
        self._error = None  # Clear any previous error
        
    def _set_error(self, error: str):
        """Set an error for this process."""
        self._error = error
        self._result = None  # Clear any previous result
        
    def _has_result(self) -> bool:
        """Check if process has a result (internal use)."""
        return self._result is not None and self._error is None
        
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert PData to dictionary representation.
        
        Returns:
            Dictionary with all process data
        """
        return {
            'pkey': self._pkey,
            'pclass': self._pclass,
            'pid': self._pid,
            'num_loops': self._num_loops,
            'completed_loops': self._completed_loops,
            'status': self._status.value,
            'result': self._result,
            'error': self._error,
            'has_error': self.has_error
        }
        
    def copy_with_updates(self, **updates) -> '_PData':
        """
        Create a copy of this PData with specific updates.
        
        Args:
            **updates: Fields to update in the copy
            
        Returns:
            New PData instance with updates applied
        """
        new_pdata = _PData(
            pkey=self._pkey,
            pclass=self._pclass,
            pid=self._pid,
            num_loops=self._num_loops,
            completed_loops=self._completed_loops
        )
        
        # Copy current state
        new_pdata._result = self._result
        new_pdata._status = self._status
        new_pdata._error = self._error
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(new_pdata, f'_{key}'):
                setattr(new_pdata, f'_{key}', value)
                
        return new_pdata
        
    def __repr__(self) -> str:
        """String representation of PData."""
        status_str = self._status.value
        if self._error:
            status_str += f" (ERROR: {self._error})"
        elif self._result is not None:
            status_str += " (HAS_RESULT)"
            
        return (f"PData(key='{self._pkey}', class='{self._pclass}', "
                f"status={status_str}, loops={self._completed_loops}/{self._num_loops})")
        
    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.__repr__()


class ProcessResultError(Exception):
    """
    Exception raised when trying to access result from a failed process.
    
    This provides clear error messaging when users try to access .result
    on a PData instance that represents a failed process.
    """
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)