"""
Xprocess Internal Cross-processing Engine - Process Base Classes

This module contains the base process classes that users inherit from and
internal wrapper classes for function-based execution.
"""

import os
import multiprocessing
from typing import Optional, Callable
from enum import Enum

from .configs import _PConfig
from .stats import ProcessStats
from suitkaise._int.time.time_ops import _get_current_time, _elapsed_time


class PStatus(Enum):
    """Process status enumeration."""
    CREATED = "created"          # Process object created but not started
    STARTING = "starting"        # Process is being started
    RUNNING = "running"          # Process is actively running loops
    STOPPING = "stopping"       # Process received stop signal, finishing current loop
    FINISHED = "finished"       # Process completed normally
    CRASHED = "crashed"          # Process terminated due to error
    KILLED = "killed"           # Process was force-terminated


class _Process:
    """
    Internal base class for user-defined processes.
    
    Users inherit from this class and implement the lifecycle hooks:
    - __loop__(): Main process logic (required)
    - __beforeloop__(): Called before each loop iteration
    - __afterloop__(): Called after each loop iteration  
    - __onfinish__(): Called when process is terminating
    """
    
    def __init__(self, num_loops: Optional[int] = None):
        """
        Initialize a new process.
        
        Args:
            process_name: Name/identifier for this process class
            num_loops: Maximum number of loops to execute (None = infinite)
        """
        self.pclass = self.__class__.__name__  # Actual class name
        self.pkey = None  # Will be set by manager when process is created
        self.pid = None   # Set when actually started
        self.num_loops = num_loops
        self.current_loop = 0
        
        # Process data - will be converted to _PData by manager
        self.pdata = {
            'pclass': self.__class__.__name__,  # Process class name
            'pkey': None,  # Will be set by manager
            'pid': None,
            'num_loops': num_loops,
            'completed_loops': 0
            # 'result': None # Will be handled by _PData system
        }
        
        # Internal _PData instance (will be created by manager)
        self._pdata_instance = None
        
        # Internal control flags (shared across processes)
        self._should_continue = None      # Will be multiprocessing.Value
        self._control_signal = None       # Will be multiprocessing.Value
        self._status = PStatus.CREATED
        self._last_loop_time = 0.0
        
        # Timing configuration
        self._timer_start_point = "before_loop"  # Default: start before __loop__()
        self._timer_end_point = "after_loop"     # Default: end after __loop__()
        
        # Process lifecycle tracking
        self._process_start_time = None
        self._config = None                # Will be set by CrossProcessing
        self._restart_count = 0
        self._subprocess_manager = None    # Will be set if process creates subprocesses
        
        # Statistics tracking
        self.stats = ProcessStats()
        
        # Return value support (will be set by CrossProcessing)
        self._result_queue = None
        
    # =============================================================================
    # LIFECYCLE HOOKS - Users override these methods
    # =============================================================================
    
    def __preloop__(self):
        """Called automatically before every loop iteration."""
        pass
        
    def __loop__(self):
        """
        Main process logic - REQUIRED.
        
        Users must implement this method with their main process work.
        This method is called once per loop iteration.
        
        DEFAULT TIMING: Timer starts before __loop__() and ends after __loop__()
        """
        raise NotImplementedError("Subclasses must implement __loop__() method")
        
    def __postloop__(self):
        """Called automatically after every loop iteration.""" 
        pass
        
    def __onfinish__(self):
        """Called automatically when process needs to join."""
        pass
        
    def __result__(self):
        """
        Return value method - OPTIONAL.
        
        Users can implement this method to return a value from the process.
        This method is called automatically when the process finishes.
        
        Returns:
            Any serializable value to return from the process
        """
        return None
        
    # =============================================================================
    # TIMING CONFIGURATION - Users can call these in __init__() to customize timing
    # =============================================================================
    
    def start_timer_before_preloop(self):
        """Configure timer to start before __preloop__()."""
        self._timer_start_point = "before_preloop"
        
    def start_timer_after_preloop(self):
        """Configure timer to start after __preloop__() (same as start_timer_before_loop)."""
        self._timer_start_point = "before_loop"
        
    def start_timer_before_loop(self):
        """Configure timer to start before __loop__() (DEFAULT)."""
        self._timer_start_point = "before_loop"
        
    def end_timer_after_loop(self):
        """Configure timer to end after __loop__() (same as end_timer_before_postloop) (DEFAULT)."""
        self._timer_end_point = "after_loop"
        
    def end_timer_before_postloop(self):
        """Configure timer to end before __postloop__() (same as end_timer_after_loop)."""
        self._timer_end_point = "after_loop"
        
    def end_timer_after_postloop(self):
        """
        Configure timer to end after __postloop__().
        
        NOTE: With this setting, timing results are available in the NEXT __preloop__(),
        not the current __postloop__(). Less intuitive but sometimes needed.
        """
        self._timer_end_point = "after_postloop"
    
    # =============================================================================
    # CONTROL METHODS - Users call these to control process execution
    # =============================================================================
    
    def rejoin(self):
        """
        Graceful shutdown after current loop.
        
        Finishes current loop cycle (__preloop__, __loop__, __postloop__)
        then calls __onfinish__ and terminates.
        """
        if self._control_signal is not None:
            self._control_signal.value = 1  # Signal: rejoin
            
    def skip_and_rejoin(self):
        """
        Immediate shutdown without finishing current loop.
        
        Skips to __onfinish__ immediately. Use with caution!
        """
        if self._control_signal is not None:
            self._control_signal.value = 2  # Signal: skip and rejoin
            
    def instakill(self):
        """
        Kill process immediately with no hooks called.
        
        Nuclear option - terminates process without any cleanup.
        Use with extreme caution!
        """
        if self._control_signal is not None:
            self._control_signal.value = 3  # Signal: instakill
            
    # =============================================================================
    # INTERNAL METHODS - Used by process management system
    # =============================================================================
    
    def _initialize_shared_state(self, manager, result_queue):
        """Initialize shared state objects for cross-process communication."""
        self._should_continue = manager.Value('i', 1)  # 1 = continue, 0 = stop
        self._control_signal = manager.Value('i', 0)   # 0 = none, 1 = rejoin, 2 = skip, 3 = kill
        self._result_queue = result_queue
        
    def _start_process(self):
        """Called when process starts - internal initialization."""
        self.pid = os.getpid()
        self.pdata['pid'] = self.pid
        self._status = PStatus.RUNNING
        self.stats.start_time = _get_current_time()
        self._process_start_time = self.stats.start_time  # For timing-based termination
        
    def _join_process(self):
        """Called when process ends - internal cleanup.""" 
        self._status = PStatus.FINISHED
        self.stats.end_time = _get_current_time()
        
    def _should_continue_loop(self) -> bool:
        """Check if process should continue looping."""
        # Check shared continue flag
        if self._should_continue is not None and not self._should_continue.value:
            return False
            
        # Check if we've reached max loops (from Process definition)
        if self.num_loops is not None and self.current_loop >= self.num_loops:
            return False
            
        # Check if we've reached config-based loop limit (join_after)
        if (self._config and self._config.join_after is not None and 
            self.current_loop >= self._config.join_after):
            return False
            
        # Check if we've reached time-based limit (join_in)
        if (self._config and self._config.join_in is not None and 
            self._process_start_time is not None):
            elapsed = _elapsed_time(self._process_start_time)
            if elapsed >= self._config.join_in:
                return False
            
        # NEW: Check for subprocess shutdown signal (cascading shutdown)
        if hasattr(self, '_shutdown_requested') and self._shutdown_requested:
            return False
            
        # Check control signals
        if self._control_signal is not None and self._control_signal.value > 0:
            return False
            
        return True
        
    @property 
    def last_loop_time(self) -> float:
        """Get the duration of the last completed timed section."""
        return self._last_loop_time
        
    @property
    def is_last_loop(self) -> bool:
        """Check if this is the last loop before termination."""
        if self.num_loops is None:
            return False
        return self.current_loop >= (self.num_loops - 1)
        
    def _set_process_key(self, pkey: str):
        """Set the process key (called by manager during creation)."""
        self.pkey = pkey
        self.pdata['pkey'] = pkey
        
    def _set_pdata_instance(self, pdata_instance):
        """Set the PData instance (called by manager)."""
        self._pdata_instance = pdata_instance
        
    @property
    def name(self) -> str:
        """Alias for pkey - the unique tracking key for this process instance."""
        return self.pkey
        
    @property
    def data(self):
        """Access to the PData instance for this process."""
        return self._pdata_instance


class _FunctionProcess(_Process):
    """
    Internal process wrapper for function-based execution.
    
    This class wraps a regular function to make it compatible with the
    Process lifecycle system. It always runs exactly once (num_loops=1).
    """
    
    def __init__(self, func: Callable, args: tuple = None, kwargs: dict = None):
        """
        Initialize a function process.
        
        Args:
            process_name: Name/identifier for this process (will be used as pclass)
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        super().__init__(num_loops=1)  # Always exactly 1 loop
        self.func = func
        self.args = args or ()
        self.kwargs = kwargs or {}
        self._function_result = None
        
        # Update pdata to indicate this is a function process
        self.pdata['process_type'] = 'function'
        self.pdata['function_name'] = getattr(func, '__name__', 'anonymous')
        
    def __loop__(self):
        """Execute the function once and store result."""
        self._function_result = self.func(*self.args, **self.kwargs)
        
    def __result__(self):
        """Return the function result."""
        return self._function_result