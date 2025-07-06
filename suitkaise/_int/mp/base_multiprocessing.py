"""
Xprocess Internal Cross-processing Engine - Internal Process Management System for Suitkaise

This module provides the core process management functionality that powers 
cross-process execution in Suitkaise. Built on multiprocessing with enhanced 
lifecycle management and automatic error handling.

This is an INTERNAL module. Front-facing APIs are provided in separate modules.

Key Features:
- Declarative process lifecycle management
- Graceful shutdown with multiple termination strategies  
- Loop timing and performance tracking
- Process status monitoring and crash recovery
- Clean separation between user code and process management
- Function-based quick process execution (internal implementation)
- Class-based advanced process management

Architecture:
- CrossProcessing: Main process manager and registry
- Process: User-defined process class with lifecycle hooks
- _ProcessRunner: Internal execution engine that runs in subprocess
- _FunctionProcess: Internal wrapper for function-based execution
"""

import multiprocessing
import threading
import time
import traceback
import signal
import os
from typing import Dict, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass

# Import internal Suitkaise operations
from suitkaise._int.core.time_ops import _get_current_time, _elapsed_time
from suitkaise._int.core.format_ops import _create_debug_message


class ProcessStatus(Enum):
    """Process status enumeration."""
    CREATED = "created"          # Process object created but not started
    STARTING = "starting"        # Process is being started
    RUNNING = "running"          # Process is actively running loops
    STOPPING = "stopping"       # Process received stop signal, finishing current loop
    FINISHED = "finished"       # Process completed normally
    CRASHED = "crashed"          # Process terminated due to error
    KILLED = "killed"           # Process was force-terminated


# ============================================================================
# CUSTOM ERROR CLASSES FOR LIFECYCLE SECTIONS
# ============================================================================

class XProcessError(Exception):
    """Base exception for XProcess-related errors."""
    pass


class PreloopError(XProcessError):
    """
    Raised when an error occurs during __preloop__() execution.
    
    This error specifically identifies problems in the setup phase
    of each loop iteration, making debugging easier.
    """
    def __init__(self, original_error: Exception, process_name: str, loop_number: int):
        self.original_error = original_error
        self.process_name = process_name
        self.loop_number = loop_number
        super().__init__(
            f"Error in __preloop__() for process '{process_name}' loop {loop_number}: {original_error}"
        )


class MainLoopError(XProcessError):
    """
    Raised when an error occurs during __loop__() execution.
    
    This error specifically identifies problems in the main work phase
    of each loop iteration, making debugging easier.
    """
    def __init__(self, original_error: Exception, process_name: str, loop_number: int):
        self.original_error = original_error
        self.process_name = process_name
        self.loop_number = loop_number
        super().__init__(
            f"Error in __loop__() for process '{process_name}' loop {loop_number}: {original_error}"
        )


class PostLoopError(XProcessError):
    """
    Raised when an error occurs during __postloop__() execution.
    
    This error specifically identifies problems in the cleanup phase
    of each loop iteration, making debugging easier.
    """
    def __init__(self, original_error: Exception, process_name: str, loop_number: int):
        self.original_error = original_error
        self.process_name = process_name
        self.loop_number = loop_number
        super().__init__(
            f"Error in __postloop__() for process '{process_name}' loop {loop_number}: {original_error}"
        )


class PreloopTimeoutError(PreloopError):
    """Raised when __preloop__() exceeds its configured timeout."""
    def __init__(self, timeout_duration: float, process_name: str, loop_number: int):
        self.timeout_duration = timeout_duration
        self.process_name = process_name
        self.loop_number = loop_number
        Exception.__init__(self, 
            f"__preloop__() timeout ({timeout_duration}s) for process '{process_name}' loop {loop_number}"
        )


class MainLoopTimeoutError(MainLoopError):
    """Raised when __loop__() exceeds its configured timeout."""
    def __init__(self, timeout_duration: float, process_name: str, loop_number: int):
        self.timeout_duration = timeout_duration
        self.process_name = process_name
        self.loop_number = loop_number
        Exception.__init__(self, 
            f"__loop__() timeout ({timeout_duration}s) for process '{process_name}' loop {loop_number}"
        )


class PostLoopTimeoutError(PostLoopError):
    """Raised when __postloop__() exceeds its configured timeout."""
    def __init__(self, timeout_duration: float, process_name: str, loop_number: int):
        self.timeout_duration = timeout_duration
        self.process_name = process_name
        self.loop_number = loop_number
        Exception.__init__(self, 
            f"__postloop__() timeout ({timeout_duration}s) for process '{process_name}' loop {loop_number}"
        )


@dataclass
class ProcessConfig:
    """Configuration for process execution."""
    join_in: Optional[float] = None      # Auto-join after N seconds
    join_after: Optional[int] = None     # Auto-join after N loops (separate from num_loops)
    crash_restart: bool = False          # Auto-restart on crash
    max_restarts: int = 3               # Maximum restart attempts
    log_loops: bool = False             # Log each loop iteration
    loop_timeout: float = 300.0         # Timeout for individual __loop__() calls (5 minutes default)
    preloop_timeout: float = 30.0       # Timeout for individual __preloop__() calls (30 seconds default)
    postloop_timeout: float = 60.0      # Timeout for individual __postloop__() calls (1 minute default)
    startup_timeout: float = 60.0       # Timeout for process startup (increased)
    shutdown_timeout: float = 20.0      # Timeout for graceful shutdown (increased)
    heartbeat_interval: float = 5.0     # Heartbeat check interval (foundation for monitoring)
    resource_monitoring: bool = False   # Enable resource monitoring (foundation for SKPerf)
    
    def disable_timeouts(self):
        """
        Disable all lifecycle timeouts (set to None).
        
        WARNING: This removes timeout protection and processes could hang indefinitely.
        Only use this if you're absolutely sure your process logic is robust.
        """
        self.preloop_timeout = None
        self.loop_timeout = None  
        self.postloop_timeout = None
        
    def set_quick_timeouts(self):
        """
        Set aggressive timeouts for fast processes.
        
        Useful for processes that should complete each section quickly.
        """
        self.preloop_timeout = 5.0   # 5 seconds for setup
        self.loop_timeout = 30.0     # 30 seconds for main work
        self.postloop_timeout = 10.0 # 10 seconds for cleanup
        
    def set_long_timeouts(self):
        """
        Set generous timeouts for slow processes.
        
        Useful for processes doing heavy computation, I/O, or network operations.
        """
        self.preloop_timeout = 120.0  # 2 minutes for setup
        self.loop_timeout = 1800.0    # 30 minutes for main work
        self.postloop_timeout = 300.0 # 5 minutes for cleanup
        
    def copy_with_overrides(self, **overrides) -> 'ProcessConfig':
        """Create a copy of this config with specific overrides."""
        import copy
        new_config = copy.deepcopy(self)
        for key, value in overrides.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
        return new_config


@dataclass
class QuickProcessConfig:
    """Simplified configuration for quick one-shot function processes."""
    join_in: Optional[float] = 30.0      # Default 30s timeout (shorter than ProcessConfig)
    crash_restart: bool = False          # Keep restart capability
    max_restarts: int = 1               # Lower default for quick processes
    heartbeat_interval: float = 5.0     # Heartbeat check interval
    resource_monitoring: bool = False   # Enable resource monitoring
    
    # Function-specific timeout (applies to the single function execution)
    function_timeout: float = 25.0      # Timeout for the function execution (5s buffer from join_in)
    
    def to_process_config(self) -> ProcessConfig:
        """Convert to full ProcessConfig for internal use."""
        return ProcessConfig(
            join_in=self.join_in,
            join_after=1,  # Always exactly 1 loop for functions
            crash_restart=self.crash_restart,
            max_restarts=self.max_restarts,
            log_loops=False,  # No loop logging for quick processes
            loop_timeout=self.function_timeout,
            preloop_timeout=1.0,   # Minimal preloop timeout
            postloop_timeout=1.0,  # Minimal postloop timeout
            startup_timeout=5.0,   # Quick startup
            shutdown_timeout=5.0,  # Quick shutdown
            heartbeat_interval=self.heartbeat_interval,
            resource_monitoring=self.resource_monitoring
        )
    join_in: Optional[float] = None      # Auto-join after N seconds
    join_after: Optional[int] = None     # Auto-join after N loops (separate from num_loops)
    crash_restart: bool = False          # Auto-restart on crash
    max_restarts: int = 3               # Maximum restart attempts
    log_loops: bool = False             # Log each loop iteration
    loop_timeout: float = 300.0         # Timeout for individual __loop__() calls (5 minutes default)
    preloop_timeout: float = 30.0       # Timeout for individual __preloop__() calls (30 seconds default)
    postloop_timeout: float = 60.0      # Timeout for individual __postloop__() calls (1 minute default)
    startup_timeout: float = 60.0       # Timeout for process startup (increased)
    shutdown_timeout: float = 20.0      # Timeout for graceful shutdown (increased)
    heartbeat_interval: float = 5.0     # Heartbeat check interval (foundation for monitoring)
    resource_monitoring: bool = False   # Enable resource monitoring (foundation for SKPerf)
    
    def disable_timeouts(self):
        """
        Disable all lifecycle timeouts (set to None).
        
        WARNING: This removes timeout protection and processes could hang indefinitely.
        Only use this if you're absolutely sure your process logic is robust.
        """
        self.preloop_timeout = None
        self.loop_timeout = None  
        self.postloop_timeout = None
        
    def set_quick_timeouts(self):
        """
        Set aggressive timeouts for fast processes.
        
        Useful for processes that should complete each section quickly.
        """
        self.preloop_timeout = 5.0   # 5 seconds for setup
        self.loop_timeout = 30.0     # 30 seconds for main work
        self.postloop_timeout = 10.0 # 10 seconds for cleanup
        
    def set_long_timeouts(self):
        """
        Set generous timeouts for slow processes.
        
        Useful for processes doing heavy computation, I/O, or network operations.
        """
        self.preloop_timeout = 120.0  # 2 minutes for setup
        self.loop_timeout = 1800.0    # 30 minutes for main work
        self.postloop_timeout = 300.0 # 5 minutes for cleanup
        
    def copy_with_overrides(self, **overrides) -> 'ProcessConfig':
        """Create a copy of this config with specific overrides."""
        import copy
        new_config = copy.deepcopy(self)
        for key, value in overrides.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
        return new_config


class ProcessStats:
    """Statistics tracking for a process."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_loops: int = 0
        self.loop_times: list = []
        self.errors: list = []
        self.restart_count: int = 0
        self.timeout_count: int = 0         # New: Track loop timeouts
        self.heartbeat_misses: int = 0      # New: Track heartbeat failures
        self.resource_peaks: dict = {}      # New: Track resource usage peaks
        
    def record_loop_time(self, duration: float) -> None:
        """Record the duration of a loop iteration."""
        self.loop_times.append(duration)
        
    def record_error(self, error: Exception, loop_number: int) -> None:
        """Record an error that occurred during execution."""
        self.errors.append({
            'error': str(error),
            'type': type(error).__name__,
            'loop': loop_number,
            'time': time.time(),
            'traceback': traceback.format_exc()
        })
        
    def record_timeout(self, timeout_type: str, duration: float, loop_number: int = -1) -> None:
        """Record a timeout event with specific section information."""
        self.timeout_count += 1
        self.errors.append({
            'error': f'{timeout_type} timeout after {duration:.2f}s',
            'type': f'{timeout_type.title()}TimeoutError',
            'loop': loop_number,
            'time': time.time(),
            'traceback': None,
            'section': timeout_type  # NEW: Track which section timed out
        })
        
    def record_restart(self, reason: str) -> None:
        """Record a process restart."""
        self.restart_count += 1
        self.errors.append({
            'error': f'Process restarted: {reason}',
            'type': 'ProcessRestart',
            'loop': -1,
            'time': time.time(),
            'traceback': None
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the process."""
        duration = None
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            
        avg_loop_time = None
        if self.loop_times:
            avg_loop_time = sum(self.loop_times) / len(self.loop_times)
            
        return {
            'total_runtime': duration,
            'total_loops': self.total_loops,
            'average_loop_time': avg_loop_time,
            'fastest_loop': min(self.loop_times) if self.loop_times else None,
            'slowest_loop': max(self.loop_times) if self.loop_times else None,
            'error_count': len(self.errors),
            'restart_count': self.restart_count,
            'timeout_count': self.timeout_count,
            'heartbeat_misses': self.heartbeat_misses
        }


class Process:
    """
    Base class for user-defined processes.
    
    Users inherit from this class and implement the lifecycle hooks:
    - __loop__(): Main process logic (required)
    - __beforeloop__(): Called before each loop iteration
    - __afterloop__(): Called after each loop iteration  
    - __onfinish__(): Called when process is terminating
    """
    
    def __init__(self, pname: str, num_loops: Optional[int] = None):
        """
        Initialize a new process.
        
        Args:
            pname: Unique name for this process
            num_loops: Maximum number of loops to execute (None = infinite)
        """
        self.pname = pname
        self.pid = None  # Set when actually started
        self.num_loops = num_loops
        self.current_loop = 0
        
        # Process data for future data syncing integration (auto-removed on join)
        self.pdata = {
            'pname': pname,
            'pid': None,
            'num_loops': num_loops,
            'completed_loops': 0,
            # 'result': None # NEW: to add when implementing new result handling
        }
        
        # Internal control flags (shared across processes)
        self._should_continue = None      # Will be multiprocessing.Value
        self._control_signal = None       # Will be multiprocessing.Value
        self._status = ProcessStatus.CREATED
        self._last_loop_time = 0.0,
        
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
        self._status = ProcessStatus.RUNNING
        self.stats.start_time = _get_current_time()
        self._process_start_time = self.stats.start_time  # For timing-based termination
        
    def _join_process(self):
        """Called when process ends - internal cleanup.""" 
        self._status = ProcessStatus.FINISHED
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


class _FunctionProcess(Process):
    """
    Internal process wrapper for function-based execution.
    
    This class wraps a regular function to make it compatible with the
    Process lifecycle system. It always runs exactly once (num_loops=1).
    """
    
    def __init__(self, pname: str, func: Callable, args: tuple = None, kwargs: dict = None):
        """
        Initialize a function process.
        
        Args:
            pname: Unique name for this process
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
        """
        super().__init__(pname, num_loops=1)  # Always exactly 1 loop
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


class _ProcessRunner:
    """
    Internal process runner that executes in the subprocess.
    
    This class handles the actual execution loop, timing, error handling,
    and lifecycle management for a user-defined Process instance.
    """
    
    def __init__(self, process_setup: Process, config: ProcessConfig, result_queue):
        """
        Initialize the process runner.
        
        Args:
            process_setup: User's Process instance
            config: Process configuration
            result_queue: Queue for returning process results
        """
        self.process_setup = process_setup
        self.config = config
        self.result_queue = result_queue
        self._timer_start_time = None
        
        # Store config reference in process for termination checks
        self.process_setup._config = config
        
    def run(self):
        """
        Main execution method that runs in the subprocess.
        
        This method handles:
        - Process initialization
        - Main execution loop with timing and timeout handling
        - Error handling and recovery
        - Cleanup and termination
        """
        try:
            # Initialize process
            self.process_setup._start_process()
            
            if self.config.log_loops:
                config_info = []
                if self.config.join_in:
                    config_info.append(f"auto-join in {self.config.join_in}s")
                if self.config.join_after:
                    config_info.append(f"auto-join after {self.config.join_after} loops")
                
                # Always show timeout values (since they're always set with defaults)
                config_info.append(f"preloop timeout {self.config.preloop_timeout}s")
                config_info.append(f"loop timeout {self.config.loop_timeout}s") 
                config_info.append(f"postloop timeout {self.config.postloop_timeout}s")
                    
                config_str = f" ({', '.join(config_info)})" if config_info else ""
                print(_create_debug_message(
                    f"Process {self.process_setup.pname} started (PID: {self.process_setup.pid}){config_str}"
                ))
            
            # Main execution loop
            while self.process_setup._should_continue_loop():
                try:
                    # Check for immediate termination signals
                    if (self.process_setup._control_signal is not None and 
                        self.process_setup._control_signal.value == 3):  # instakill
                        break
                        
                    # Check for skip signal
                    if (self.process_setup._control_signal is not None and 
                        self.process_setup._control_signal.value == 2):  # skip and rejoin
                        break
                    
                    # Execute single loop iteration with granular timeout handling
                    if not self._execute_loop_iteration():
                        break  # Timeout or error occurred
                        
                    # Check for graceful termination signal
                    if (self.process_setup._control_signal is not None and 
                        self.process_setup._control_signal.value == 1):  # rejoin
                        break
                        
                except (PreloopError, MainLoopError, PostLoopError) as e:
                    # These are our custom lifecycle errors with detailed information
                    self.process_setup.stats.record_error(e, self.process_setup.current_loop)
                    
                    # Log the specific error type and section
                    error_type = type(e).__name__
                    section = error_type.replace("Error", "").replace("Timeout", "").lower()
                    
                    error_msg = _create_debug_message(
                        f"{error_type} in process {self.process_setup.pname}: {e}"
                    )
                    print(error_msg)
                    
                    # For now, break on any lifecycle error. Later we can add retry logic
                    self.process_setup._status = ProcessStatus.CRASHED
                    break
                    
                except Exception as e:
                    # Record error in statistics
                    self.process_setup.stats.record_error(e, self.process_setup.current_loop)
                    
                    # Handle error based on configuration
                    error_msg = _create_debug_message(
                        f"Unexpected error in process {self.process_setup.pname} loop {self.process_setup.current_loop}: {e}",
                        (traceback.format_exc(),)
                    )
                    print(error_msg)
                    
                    # For now, break on any error. Later we can add retry logic
                    self.process_setup._status = ProcessStatus.CRASHED
                    break
                    
        except Exception as e:
            # Fatal error in process runner itself
            self.process_setup._status = ProcessStatus.CRASHED
            self.process_setup.stats.record_error(e, self.process_setup.current_loop)
            print(_create_debug_message(
                f"Fatal error in process {self.process_setup.pname}: {e}",
                (traceback.format_exc(),)
            ))
            
        finally:
            # Always call onfinish hook unless instakilled
            if (self.process_setup._control_signal is None or 
                self.process_setup._control_signal.value != 3):
                try:
                    self.process_setup.__onfinish__()
                except Exception as e:
                    print(_create_debug_message(
                        f"Error in __onfinish__ for process {self.process_setup.pname}: {e}"
                    ))
                    
            # NEW: Always call __result__ if it exists and serialize with Cerial
            if hasattr(self.process_setup, '__result__'):
                try:
                    # Check if __result__ is implemented (not just the default return None)
                    result_method = getattr(self.process_setup, '__result__')
                    if result_method.__func__ is not Process.__result__:
                        result = self.process_setup.__result__()
                        
                        # Serialize result using Cerial for complex object support
                        try:
                            from suitkaise._int.serialization.cerial_core import serialize
                            serialized_result = serialize(result)
                            self.result_queue.put(('success', serialized_result))
                            if self.config.log_loops:
                                print(_create_debug_message(
                                    f"Process {self.process_setup.pname} returned and serialized result"
                                ))
                        except Exception as serialize_error:
                            print(_create_debug_message(
                                f"Failed to serialize result from process {self.process_setup.pname}: {serialize_error}"
                            ))
                            # Store error info instead
                            self.result_queue.put(('serialize_error', str(serialize_error)))
                    else:
                        # Default implementation, put None
                        self.result_queue.put(('success', None))
                except Exception as e:
                    print(_create_debug_message(
                        f"Error in __result__ for process {self.process_setup.pname}: {e}"
                    ))
                    # Put error info in queue
                    self.result_queue.put(('result_error', str(e)))
            else:
                # No __result__ method, put None
                self.result_queue.put(('success', None))
                    
            # Final cleanup
            self.process_setup._join_process()
            
            if self.config.log_loops:
                stats = self.process_setup.stats.get_summary()
                print(_create_debug_message(
                    f"Process {self.process_setup.pname} finished",
                    (stats,)
                ))
                
    def _execute_loop_iteration(self) -> bool:
        """
        Execute a single loop iteration with granular timeout handling.
        
        Returns:
            True if iteration completed successfully, False if timeout or error
        """
        # Increment loop counter
        self.process_setup.current_loop += 1
        self.process_setup.pdata['completed_loops'] = self.process_setup.current_loop
        
        # Execute with timeout protection for each section
        return self._execute_with_granular_timeouts()
            
    def _execute_with_granular_timeouts(self) -> bool:
        """Execute loop iteration with individual section timeout protection."""
        try:
            # Start timer if configured to start before preloop
            if self.process_setup._timer_start_point == "before_preloop":
                self._start_timer()
            
            # Execute preloop with timeout protection
            if not self._execute_preloop_with_timeout():
                return False
            
            # Start timer if configured to start before loop (DEFAULT)
            if self.process_setup._timer_start_point == "before_loop":
                self._start_timer()
            
            # Execute main loop with timeout protection
            if not self._execute_mainloop_with_timeout():
                return False
            
            # End timer if configured to end after loop (DEFAULT)
            loop_duration = None
            if self.process_setup._timer_end_point == "after_loop":
                loop_duration = self._end_timer()
                self.process_setup._last_loop_time = loop_duration
                self.process_setup.stats.record_loop_time(loop_duration)
                self.process_setup.stats.total_loops += 1
            
            # Execute postloop with timeout protection
            if not self._execute_postloop_with_timeout():
                return False
            
            # End timer if configured to end after postloop
            if self.process_setup._timer_end_point == "after_postloop":
                loop_duration = self._end_timer()
                self.process_setup._last_loop_time = loop_duration
                self.process_setup.stats.record_loop_time(loop_duration)
                self.process_setup.stats.total_loops += 1
                
            # Log completion with detailed timeout information
            if self.config.log_loops and loop_duration is not None:
                self._log_loop_completion(loop_duration)
                
            return True
            
        except (PreloopError, MainLoopError, PostLoopError) as e:
            # These are already properly formatted errors
            self.process_setup.stats.record_error(e, self.process_setup.current_loop)
            print(_create_debug_message(str(e)))
            return False
            
        except Exception as e:
            # Unexpected error - wrap it appropriately
            error_msg = f"Unexpected error in process {self.process_setup.pname} loop {self.process_setup.current_loop}: {e}"
            self.process_setup.stats.record_error(e, self.process_setup.current_loop)
            print(_create_debug_message(error_msg, (traceback.format_exc(),)))
            return False
            
    def _execute_preloop_with_timeout(self) -> bool:
        """Execute __preloop__() with timeout protection (always enabled with defaults)."""
        return self._execute_section_with_timeout(
            section_func=self.process_setup.__preloop__,
            timeout_duration=self.config.preloop_timeout,
            timeout_error_class=PreloopTimeoutError,
            regular_error_class=PreloopError,
            section_name="preloop"
        )
            
    def _execute_mainloop_with_timeout(self) -> bool:
        """Execute __loop__() with timeout protection (always enabled with defaults)."""
        return self._execute_section_with_timeout(
            section_func=self.process_setup.__loop__,
            timeout_duration=self.config.loop_timeout,
            timeout_error_class=MainLoopTimeoutError,
            regular_error_class=MainLoopError,
            section_name="mainloop"
        )
            
    def _execute_postloop_with_timeout(self) -> bool:
        """Execute __postloop__() with timeout protection (always enabled with defaults)."""
        return self._execute_section_with_timeout(
            section_func=self.process_setup.__postloop__,
            timeout_duration=self.config.postloop_timeout,
            timeout_error_class=PostLoopTimeoutError,
            regular_error_class=PostLoopError,
            section_name="postloop"
        )
            
    def _execute_section_with_timeout(self, section_func: callable, timeout_duration: Optional[float],
                                    timeout_error_class: type, regular_error_class: type,
                                    section_name: str) -> bool:
        """Execute a section with timeout protection."""
        
        # If timeout is None (explicitly disabled), execute without timeout
        if timeout_duration is None:
            return self._execute_section_without_timeout(
                section_func, regular_error_class, section_name
            )
        
        import signal
        
        class SectionTimeoutException(Exception):
            pass
            
        def timeout_handler(signum, frame):
            raise SectionTimeoutException()
            
        # Set up timeout signal
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout_duration))
        
        try:
            section_func()
            signal.alarm(0)  # Cancel timeout
            return True
            
        except SectionTimeoutException:
            # Create specific timeout error
            timeout_error = timeout_error_class(
                timeout_duration, 
                self.process_setup.pname, 
                self.process_setup.current_loop
            )
            
            # Record timeout in statistics
            self.process_setup.stats.record_timeout(
                section_name, timeout_duration, self.process_setup.current_loop
            )
            
            # Re-raise as our custom error
            raise timeout_error
            
        except Exception as e:
            # Wrap regular errors in section-specific error class
            section_error = regular_error_class(
                e, self.process_setup.pname, self.process_setup.current_loop
            )
            raise section_error
            
        finally:
            signal.signal(signal.SIGALRM, old_handler)  # Restore old handler
            signal.alarm(0)  # Ensure alarm is cancelled
            
    def _execute_section_without_timeout(self, section_func: callable, 
                                       regular_error_class: type, section_name: str) -> bool:
        """Execute a section without timeout protection."""
        try:
            section_func()
            return True
            
        except Exception as e:
            # Wrap in section-specific error class
            section_error = regular_error_class(
                e, self.process_setup.pname, self.process_setup.current_loop
            )
            raise section_error
            
    def _log_loop_completion(self, loop_duration: float):
        """Log loop completion with comprehensive timeout information."""
        termination_info = []
        if self.config.join_after:
            remaining_loops = self.config.join_after - self.process_setup.current_loop
            termination_info.append(f"{remaining_loops} loops remaining")
        if self.config.join_in:
            elapsed = _elapsed_time(self.process_setup._process_start_time)
            remaining_time = self.config.join_in - elapsed
            termination_info.append(f"{remaining_time:.1f}s remaining")
            
        # Always show timeout configuration (since we have defaults)
        timeout_info = [
            f"preloop_timeout={self.config.preloop_timeout}s",
            f"loop_timeout={self.config.loop_timeout}s", 
            f"postloop_timeout={self.config.postloop_timeout}s"
        ]
            
        start_point = self.process_setup._timer_start_point.replace("_", " ")
        end_point = self.process_setup._timer_end_point.replace("_", " ")
        timing_info = f"{start_point} to {end_point} = {loop_duration:.4f}s"
        
        # Combine all information
        all_info = []
        if termination_info:
            all_info.extend(termination_info)
        all_info.extend(timeout_info)
            
        timing_info += f" ({', '.join(all_info)})"
            
        print(_create_debug_message(
            f"Process {self.process_setup.pname} completed loop {self.process_setup.current_loop}: {timing_info}"
        ))
                
    def _start_timer(self):
        """Start timing the configured section."""
        self._timer_start_time = _get_current_time()
        
    def _end_timer(self) -> float:
        """End timing and return duration."""
        if self._timer_start_time is None:
            return 0.0
        
        duration = _elapsed_time(self._timer_start_time)
        self._timer_start_time = None
        return duration



class CrossProcessing:
    """
    Main process manager for cross-process execution.
    
    This class manages multiple processes, provides a registry for tracking
    active processes, and handles process lifecycle coordination including
    automatic restart on crash.
    """
    
    def __init__(self):
        """Initialize the cross-processing manager."""
        self._processes: Dict[str, Dict[str, Any]] = {}
        self._active = True
        self._manager = multiprocessing.Manager()
        self._monitoring_thread = None
        self._monitor_shutdown = threading.Event()
        
        # Start background monitoring thread for restart logic
        self._start_monitoring_thread()
        
    def _start_monitoring_thread(self):
        """Start background thread for process monitoring and restart logic."""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            self._monitoring_thread = threading.Thread(
                target=self._monitor_processes,
                name="XProcess-Monitor",
                daemon=True
            )
            self._monitoring_thread.start()
            
    def _monitor_processes(self):
        """Background thread that monitors processes and handles restarts."""
        while not self._monitor_shutdown.is_set():
            try:
                # Check each process for crashes and restart if needed
                for name, info in list(self._processes.items()):
                    if not self._monitor_shutdown.is_set():
                        self._check_and_restart_process(name, info)
                        
                # Sleep for a short interval before next check
                self._monitor_shutdown.wait(1.0)  # Check every second
                
            except Exception as e:
                print(_create_debug_message(f"Error in process monitor: {e}"))
                time.sleep(5.0)  # Wait longer on error
                
    def _check_and_restart_process(self, name: str, info: Dict[str, Any]):
        """Check if a process needs to be restarted and handle restart logic."""
        process_setup = info['process_setup']
        config = info['config']
        mp_process = info['mp_process']
        
        # Skip if restart is not enabled
        if not config.crash_restart:
            return
            
        # Check if process has crashed (not alive but not finished normally)
        if (not mp_process.is_alive() and 
            process_setup._status not in [ProcessStatus.FINISHED, ProcessStatus.KILLED]):
            
            # Check if we've exceeded max restart attempts
            if process_setup._restart_count >= config.max_restarts:
                print(_create_debug_message(
                    f"Process {name} exceeded max restart attempts ({config.max_restarts}), giving up"
                ))
                process_setup._status = ProcessStatus.CRASHED
                return
                
            # Record the restart
            process_setup.stats.record_restart(f"Process crashed, restart #{process_setup._restart_count + 1}")
            process_setup._restart_count += 1
            
            print(_create_debug_message(
                f"Restarting crashed process {name} (attempt {process_setup._restart_count}/{config.max_restarts})"
            ))
            
            # Reset process state for restart
            process_setup._status = ProcessStatus.STARTING
            process_setup.current_loop = 0
            process_setup.pdata['completed_loops'] = 0
            process_setup.pid = None
            process_setup.pdata['pid'] = None
            
            # Create new result queue for restart
            new_result_queue = multiprocessing.Queue()
            
            # Re-initialize shared state
            process_setup._initialize_shared_state(self._manager, new_result_queue)
            
            # Create new process runner and multiprocessing.Process
            runner = _ProcessRunner(process_setup, config, new_result_queue)
            new_mp_process = multiprocessing.Process(
                target=runner.run,
                name=f"XProcess-{name}-restart{process_setup._restart_count}"
            )
            
            # Update process info
            info['mp_process'] = new_mp_process
            info['runner'] = runner
            info['result_queue'] = new_result_queue
            info['restarted_at'] = _get_current_time()
            
            # Start the new process
            new_mp_process.start()
            
            print(_create_debug_message(
                f"Restarted process {name} with new PID (restart #{process_setup._restart_count})"
            ))
        
    def create_process(self, process_setup: Process, config: Optional[ProcessConfig] = None) -> str:
        """
        Create and start a new process.
        
        Args:
            process_setup: User's Process instance with lifecycle hooks
            config: Process configuration (uses defaults if None)
            
        Returns:
            Process ID string for tracking
            
        Raises:
            ValueError: If process with same name already exists
        """
        if not self._active:
            raise RuntimeError("CrossProcessing manager is not active")
            
        if process_setup.pname in self._processes:
            raise ValueError(f"Process with name '{process_setup.pname}' already exists")
            
        # Use default config if none provided
        if config is None:
            config = ProcessConfig()
            
        # Create result queue for this process
        result_queue = multiprocessing.Queue()
        
        # Initialize shared state for the process
        process_setup._initialize_shared_state(self._manager, result_queue)
        
        # Create the process runner
        runner = _ProcessRunner(process_setup, config, result_queue)
        
        # Create and start the multiprocessing.Process
        mp_process = multiprocessing.Process(
            target=runner.run,
            name=f"XProcess-{process_setup.pname}"
        )
        
        # Store process information
        process_info = {
            'process_setup': process_setup,
            'config': config,
            'mp_process': mp_process,
            'runner': runner,
            'result_queue': result_queue,
            'created_at': _get_current_time()
        }
        
        self._processes[process_setup.pname] = process_info
        
        # Start the process
        mp_process.start()
        process_setup._status = ProcessStatus.STARTING
        
        print(_create_debug_message(f"Started process: {process_setup.pname}"))
        
        return process_setup.pname
        
    def get_process(self, name: str) -> Optional[Process]:
        """Get a process by name."""
        if name in self._processes:
            return self._processes[name]['process_setup']
        return None
        
    def get_process_status(self, name: str) -> Optional[ProcessStatus]:
        """Get the current status of a process."""
        if name in self._processes:
            return self._processes[name]['process_setup']._status
        return None
        
    def get_process_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a process."""
        if name in self._processes:
            return self._processes[name]['process_setup'].stats.get_summary()
        return None
        
    def get_process_result(self, name: str, timeout: Optional[float] = None):
        """
        Get the result from a completed process with Cerial deserialization support.
        
        Args:
            name: Name of process to get result from
            timeout: Maximum time to wait for result
            
        Returns:
            Result value from process, or None if no result/timeout/error
        """
        if name not in self._processes:
            return None
            
        process_info = self._processes[name]
        mp_process = process_info['mp_process']
        result_queue = process_info['result_queue']
        
        # Wait for process to complete first
        mp_process.join(timeout)
        
        if not mp_process.is_alive():
            try:
                # Get result from queue (non-blocking since process is done)
                result_data = result_queue.get_nowait()
                
                # Handle new tuple format: (status, data)
                if isinstance(result_data, tuple) and len(result_data) == 2:
                    status, data = result_data
                    
                    if status == 'success':
                        if data is None:
                            return None
                        else:
                            # Deserialize using Cerial
                            try:
                                from suitkaise._int.serialization.cerial_core import deserialize
                                return deserialize(data)
                            except Exception as deserialize_error:
                                print(_create_debug_message(
                                    f"Failed to deserialize result from process {name}: {deserialize_error}"
                                ))
                                return None
                    
                    elif status == 'serialize_error':
                        print(_create_debug_message(f"Process {name} had serialization error: {data}"))
                        return None
                    
                    elif status == 'result_error':
                        print(_create_debug_message(f"Process {name} had __result__ error: {data}"))
                        return None
                    
                    else:
                        print(_create_debug_message(f"Process {name} returned unknown status: {status}"))
                        return None
                        
                else:
                    # Legacy format or direct value - treat as success
                    return result_data
                    
            except:
                return None
        else:
            return None
    
    def join_and_get_result(self, name: str, timeout: Optional[float] = None):
        """
        Convenience method to join a process and get its result in one call.
        
        Args:
            name: Name of process to join and get result from
            timeout: Maximum time to wait for process completion
            
        Returns:
            Tuple of (success: bool, result: Any)
            - success: True if process completed successfully
            - result: The process result, or None if no result/error
        """
        success = self.join_process(name, timeout)
        if success:
            result = self.get_process_result(name)
            return True, result
        else:
            return False, None
        
    def list_processes(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all managed processes."""
        result = {}
        for name, info in self._processes.items():
            process_setup = info['process_setup']
            mp_process = info['mp_process']
            config = info['config']
            
            # Calculate remaining time/loops if configured
            remaining_info = {}
            if config.join_in and process_setup._process_start_time:
                elapsed = _elapsed_time(process_setup._process_start_time)
                remaining_info['time_remaining'] = max(0, config.join_in - elapsed)
            if config.join_after:
                remaining_info['loops_remaining'] = max(0, config.join_after - process_setup.current_loop)
            
            result[name] = {
                'status': process_setup._status.value,
                'pid': process_setup.pid,
                'current_loop': process_setup.current_loop,
                'is_alive': mp_process.is_alive(),
                'created_at': info['created_at'],
                'restart_count': process_setup._restart_count,
                'can_restart': config.crash_restart,
                'max_restarts': config.max_restarts,
                **remaining_info
            }
            
        return result
        
    def join_process(self, name: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a process to complete.
        
        Args:
            name: Name of process to join
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if process completed, False if timeout
        """
        if name not in self._processes:
            return False
            
        mp_process = self._processes[name]['mp_process']
        mp_process.join(timeout)
        
        return not mp_process.is_alive()
        
    def join_all(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all processes to complete.
        
        Args:
            timeout: Maximum time to wait for all processes
            
        Returns:
            True if all processes completed, False if timeout
        """
        start_time = _get_current_time()
        
        for name in list(self._processes.keys()):
            if timeout is not None:
                elapsed = _elapsed_time(start_time)
                remaining = timeout - elapsed
                if remaining <= 0:
                    return False
            else:
                remaining = None
                
            if not self.join_process(name, remaining):
                return False
                
        return True
        
    def terminate_process(self, name: str, force: bool = False):
        """
        Terminate a specific process.
        
        Args:
            name: Name of process to terminate
            force: If True, use instakill. If False, use graceful rejoin.
        """
        if name not in self._processes:
            return
            
        process_setup = self._processes[name]['process_setup']
        
        if force:
            process_setup.instakill()
        else:
            process_setup.rejoin()
            
    def shutdown(self, timeout: float = 10.0, force_after_timeout: bool = True):
        """
        Shutdown the process manager and all processes.
        
        Args:
            timeout: Time to wait for graceful shutdown
            force_after_timeout: Whether to force-kill processes after timeout
        """
        if not self._active:
            return
            
        print(_create_debug_message(f"Shutting down {len(self._processes)} processes..."))
        
        # Stop monitoring thread first
        self._monitor_shutdown.set()
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)
        
        # Signal all processes to terminate gracefully
        for name in self._processes:
            self.terminate_process(name, force=False)
            
        # Wait for graceful shutdown
        if not self.join_all(timeout):
            if force_after_timeout:
                print(_create_debug_message("Timeout reached, force-killing remaining processes"))
                for name in list(self._processes.keys()):
                    if self.get_process_status(name) not in [ProcessStatus.FINISHED, ProcessStatus.KILLED]:
                        self.terminate_process(name, force=True)
                        
        self._active = False
        print(_create_debug_message("CrossProcessing shutdown complete"))
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic shutdown."""
        self.shutdown()



class SubProcessing:
    """
    Subprocess manager for creating and managing SubProcess instances.
    
    This manager provides the same interface as CrossProcessing but is designed
    for use within existing processes to create lightweight subprocesses.
    
    Features:
    - Automatic nesting depth protection (max depth 2)
    - Signal-based cascading shutdown
    - Full lifecycle management for subprocesses
    - Compatible with Process lifecycle hooks
    """
    
    def __init__(self):
        """Initialize the subprocess manager with nesting depth protection."""
        # Check current nesting depth to prevent infinite nesting
        current_depth = int(os.environ.get('XPROCESS_DEPTH', '0'))
        if current_depth >= 2:
            raise RuntimeError(
                f"Maximum subprocess nesting depth (2) exceeded. Current depth: {current_depth}. "
                f"SubProcesses cannot create their own subprocesses if they are already at depth 2."
            )
            
        self._subprocesses: Dict[str, Dict[str, Any]] = {}
        self._active = True
        self._nesting_depth = current_depth + 1
        
        # Set environment variable for subprocess depth tracking
        os.environ['XPROCESS_DEPTH'] = str(self._nesting_depth)
        
        print(_create_debug_message(
            f"SubProcessing manager initialized at depth {self._nesting_depth}"
        ))
        
    def create_process(self, subprocess_setup: Process, config: Optional[ProcessConfig] = None) -> str:
        """
        Create and start a new subprocess.
        
        Args:
            subprocess_setup: Process instance with lifecycle hooks
            config: Process configuration (uses defaults if None)
            
        Returns:
            Process ID string for tracking
            
        Raises:
            ValueError: If subprocess with same name already exists
            RuntimeError: If manager is not active or depth limit exceeded
        """
        if not self._active:
            raise RuntimeError("SubProcessing manager is not active")
            
        if subprocess_setup.pname in self._subprocesses:
            raise ValueError(f"SubProcess with name '{subprocess_setup.pname}' already exists")
            
        # Use default config if none provided
        if config is None:
            config = ProcessConfig()
            
        # Create result queue for this subprocess
        result_queue = multiprocessing.Queue()
        
        # Initialize shared state for the subprocess
        subprocess_setup._initialize_shared_state(multiprocessing.Manager(), result_queue)
        
        # Store config reference in subprocess for termination checks
        subprocess_setup._config = config
        
        # Create the process runner (same as regular processes)
        runner = _ProcessRunner(subprocess_setup, config, result_queue)
        
        # Create and start the multiprocessing.Process
        mp_process = multiprocessing.Process(
            target=runner.run,
            name=f"XSubProcess-{subprocess_setup.pname}-depth{self._nesting_depth}"
        )
        
        # Store subprocess information
        subprocess_info = {
            'subprocess_setup': subprocess_setup,
            'config': config,
            'mp_process': mp_process,
            'runner': runner,
            'result_queue': result_queue,
            'created_at': _get_current_time(),
            'nesting_depth': self._nesting_depth
        }
        
        self._subprocesses[subprocess_setup.pname] = subprocess_info
        
        # Start the subprocess
        mp_process.start()
        subprocess_setup._status = ProcessStatus.STARTING
        
        print(_create_debug_message(
            f"Started subprocess: {subprocess_setup.pname} (depth {self._nesting_depth})"
        ))
        
        return subprocess_setup.pname
        
    def get_subprocess(self, name: str) -> Optional[Process]:
        """Get a subprocess by name."""
        if name in self._subprocesses:
            return self._subprocesses[name]['subprocess_setup']
        return None
        
    def get_subprocess_status(self, name: str) -> Optional[ProcessStatus]:
        """Get the current status of a subprocess."""
        if name in self._subprocesses:
            return self._subprocesses[name]['subprocess_setup']._status
        return None
        
    def get_subprocess_result(self, name: str, timeout: Optional[float] = None):
        """
        Get the result from a completed subprocess with Cerial deserialization support.
        
        Args:
            name: Name of subprocess to get result from
            timeout: Maximum time to wait for result
            
        Returns:
            Result value from subprocess, or None if no result/timeout/error
        """
        if name not in self._subprocesses:
            return None
            
        subprocess_info = self._subprocesses[name]
        mp_process = subprocess_info['mp_process']
        result_queue = subprocess_info['result_queue']
        
        # Wait for process to complete first
        mp_process.join(timeout)
        
        if not mp_process.is_alive():
            try:
                # Get result from queue (non-blocking since process is done)
                result_data = result_queue.get_nowait()
                
                # Handle new tuple format: (status, data)
                if isinstance(result_data, tuple) and len(result_data) == 2:
                    status, data = result_data
                    
                    if status == 'success':
                        if data is None:
                            return None
                        else:
                            # Deserialize using Cerial
                            try:
                                from suitkaise._int.serialization.cerial_core import deserialize
                                return deserialize(data)
                            except Exception as deserialize_error:
                                print(_create_debug_message(
                                    f"Failed to deserialize result from subprocess {name}: {deserialize_error}"
                                ))
                                return None
                    
                    elif status == 'serialize_error':
                        print(_create_debug_message(f"Subprocess {name} had serialization error: {data}"))
                        return None
                    
                    elif status == 'result_error':
                        print(_create_debug_message(f"Subprocess {name} had __result__ error: {data}"))
                        return None
                    
                    else:
                        print(_create_debug_message(f"Subprocess {name} returned unknown status: {status}"))
                        return None
                        
                else:
                    # Legacy format or direct value - treat as success
                    return result_data
                    
            except:
                return None
        else:
            return None
    
    def join_and_get_result(self, name: str, timeout: Optional[float] = None):
        """
        Convenience method to join a subprocess and get its result in one call.
        
        Args:
            name: Name of subprocess to join and get result from
            timeout: Maximum time to wait for subprocess completion
            
        Returns:
            Tuple of (success: bool, result: Any)
            - success: True if subprocess completed successfully
            - result: The subprocess result, or None if no result/error
        """
        success = self.join_subprocess(name, timeout)
        if success:
            result = self.get_subprocess_result(name)
            return True, result
        else:
            return False, None
        
    def list_subprocesses(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all managed subprocesses."""
        result = {}
        for name, info in self._subprocesses.items():
            subprocess_setup = info['subprocess_setup']
            mp_process = info['mp_process']
            config = info['config']
            
            result[name] = {
                'status': subprocess_setup._status.value,
                'pid': subprocess_setup.pid,
                'current_loop': subprocess_setup.current_loop,
                'is_alive': mp_process.is_alive(),
                'created_at': info['created_at'],
                'nesting_depth': info['nesting_depth'],
            }
            
        return result
        
    def join_subprocess(self, name: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a subprocess to complete.
        
        Args:
            name: Name of subprocess to join
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if subprocess completed, False if timeout
        """
        if name not in self._subprocesses:
            return False
            
        mp_process = self._subprocesses[name]['mp_process']
        mp_process.join(timeout)
        
        return not mp_process.is_alive()
        
    def join_all(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all subprocesses to complete.
        
        Args:
            timeout: Maximum time to wait for all subprocesses
            
        Returns:
            True if all subprocesses completed, False if timeout
        """
        start_time = _get_current_time()
        
        for name in list(self._subprocesses.keys()):
            if timeout is not None:
                elapsed = _elapsed_time(start_time)
                remaining = timeout - elapsed
                if remaining <= 0:
                    return False
            else:
                remaining = None
                
            if not self.join_subprocess(name, remaining):
                return False
                
        return True
        
    def terminate_subprocess(self, name: str, force: bool = False):
        """
        Terminate a specific subprocess using signals.
        
        Args:
            name: Name of subprocess to terminate
            force: If True, use force signal. If False, use graceful signal.
        """
        if name not in self._subprocesses:
            return
            
        subprocess_info = self._subprocesses[name]
        mp_process = subprocess_info['mp_process']
        
        if mp_process.is_alive():
            try:
                if force:
                    # Send force shutdown signal
                    os.kill(mp_process.pid, signal.SIGUSR2)
                else:
                    # Send graceful shutdown signal
                    os.kill(mp_process.pid, signal.SIGUSR1)
                    
                print(_create_debug_message(
                    f"Sent {'force' if force else 'graceful'} shutdown signal to subprocess {name} (PID: {mp_process.pid})"
                ))
                
            except ProcessLookupError:
                # Process already dead
                pass
            except OSError as e:
                print(_create_debug_message(f"Error sending signal to subprocess {name}: {e}"))
                
    def _quick_process_internal(self, name: str, func: Callable, args: tuple = None, 
                               kwargs: dict = None, config: Optional[QuickProcessConfig] = None) -> Any:
        """
        Internal implementation for quick function process execution.
        
        Args:
            name: Unique name for the process
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            config: Optional configuration (uses defaults if None)
            
        Returns:
            Result from the function execution
            
        Raises:
            RuntimeError: If process fails to complete within timeout
        """
        if config is None:
            config = QuickProcessConfig()
        
        # Create function process wrapper
        function_process = _FunctionProcess(name, func, args, kwargs)
        
        # Convert to full ProcessConfig
        process_config = config.to_process_config()
        
        # Create and start the process
        process_id = self.create_process(function_process, process_config)
        
        # Wait for completion and get result
        success, result = self.join_and_get_result(process_id, config.join_in)
        
        if not success:
            raise RuntimeError(f"Quick process '{name}' failed to complete within {config.join_in}s timeout")
        
        return result
        
    def shutdown(self, timeout: float = 10.0, force_after_timeout: bool = True):
        """
        Shutdown the subprocess manager and all subprocesses using signal-based coordination.
        
        Args:
            timeout: Time to wait for graceful shutdown
            force_after_timeout: Whether to force-kill subprocesses after timeout
        """
        if not self._active:
            return
            
        print(_create_debug_message(f"Shutting down {len(self._subprocesses)} subprocesses..."))
        
        # Phase 1: Signal all subprocesses to terminate gracefully
        for name in self._subprocesses:
            self.terminate_subprocess(name, force=False)
            
        # Phase 2: Wait for graceful shutdown
        graceful_timeout = timeout * 0.7  # Give 70% of time for graceful shutdown
        if not self.join_all(graceful_timeout):
            if force_after_timeout:
                print(_create_debug_message("Graceful timeout reached, sending force signals"))
                
                # Phase 3: Force termination for remaining subprocesses
                for name in list(self._subprocesses.keys()):
                    subprocess_info = self._subprocesses[name]
                    if subprocess_info['mp_process'].is_alive():
                        self.terminate_subprocess(name, force=True)
                        
                # Wait a bit more for force termination
                remaining_timeout = timeout - graceful_timeout
                self.join_all(remaining_timeout)
                        
        self._active = False
        print(_create_debug_message("SubProcessing shutdown complete"))
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic shutdown."""
        self.shutdown()