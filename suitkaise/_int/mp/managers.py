"""
Xprocess Internal Cross-processing Engine - Process Managers

This module contains the main process management classes for cross-process
and subprocess execution with lifecycle coordination and monitoring.
"""

import multiprocessing
import threading
import time
import signal
import os
import queue
from typing import Dict, Optional, Any, Callable

from .processes import _Process, _FunctionProcess, PStatus
from .configs import _PConfig, _QPConfig
from .runner import _ProcessRunner
from .pdata import _PData
from suitkaise._int.time.time_ops import _get_current_time, _elapsed_time
from suitkaise._int.core.format_ops import _create_debug_message
from suitkaise._int.serialization.cerial_core import _serialize, _deserialize

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
        self._processes_lock = threading.RLock()  # Use RLock for nested access
        
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
                with self._processes_lock:
                    process_items = list(self._processes.items())
                
                for key, info in process_items:
                    if not self._monitor_shutdown.is_set():
                        self._check_and_restart_process(key, info)
                        self._update_pdata_status(key, info)  # Update PData status
                        
                # Sleep for a short interval before next check
                self._monitor_shutdown.wait(1.0)  # Check every second
                
            except Exception as e:
                print(_create_debug_message(f"Error in process monitor: {e}"))
                time.sleep(5.0)  # Wait longer on error
                
    def _check_and_restart_process(self, key: str, info: Dict[str, Any]):
        """Check if a process needs to be restarted and handle restart logic."""
        process_setup = info['process_setup']
        config = info['config']
        mp_process = info['mp_process']
        
        # Skip if restart is not enabled
        if not config.crash_restart:
            return
            
        # Check if process has crashed (not alive but not finished normally)
        if (not mp_process.is_alive() and 
            process_setup._status not in [PStatus.FINISHED, PStatus.KILLED]):
            
            # Check if we've exceeded max restart attempts
            if process_setup._restart_count >= config.max_restarts:
                print(_create_debug_message(
                    f"Process {key} exceeded max restart attempts ({config.max_restarts}), giving up"
                ))
                process_setup._status = PStatus.CRASHED
                return
                
            # Record the restart
            process_setup.stats.record_restart(f"Process crashed, restart #{process_setup._restart_count + 1}")
            process_setup._restart_count += 1
            
            print(_create_debug_message(
                f"Restarting crashed process {key} (attempt {process_setup._restart_count}/{config.max_restarts})"
            ))
            
            # Reset process state for restart
            process_setup._status = PStatus.STARTING
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
                name=f"XProcess-{key}-restart{process_setup._restart_count}"  # Use key instead of name
            )
            
            # Update process info with lock
            with self._processes_lock:
                info['mp_process'] = new_mp_process
                info['runner'] = runner
                info['result_queue'] = new_result_queue
                info['restarted_at'] = _get_current_time()
            
            # Start the new process
            new_mp_process.start()
            
            print(_create_debug_message(
                f"Restarted process {key} with new PID (restart #{process_setup._restart_count})"
            ))
            
    def _update_pdata_status(self, key: str, info: Dict[str, Any]):
        """Update PData instance with current process state."""
        try:
            process_setup = info['process_setup']
            pdata_instance = info['pdata_instance']
            
            # Update status - prioritize process_setup status
            current_status = process_setup._status
            if current_status != pdata_instance.status:
                pdata_instance._update_status(current_status)
            
            # Update PID if changed
            if process_setup.pid != pdata_instance.pid:
                pdata_instance._update_pid(process_setup.pid)
                
            # Update completed loops
            if process_setup.current_loop != pdata_instance.completed_loops:
                pdata_instance._update_completed_loops(process_setup.current_loop)
                
        except Exception as e:
            # Don't let PData update errors crash the monitor
            print(_create_debug_message(f"Error updating PData for {key}: {e}"))
        

    def create_process(self, key: str, process_setup: _Process, config: Optional[_PConfig] = None) -> _PData:
        """
        Create and start a new process with key-based tracking.
        
        Args:
            key: Unique key for tracking this process
            process_setup: User's Process instance with lifecycle hooks
            config: Process configuration (uses defaults if None)
            
        Returns:
            PData instance for tracking and result access
            
        Raises:
            ValueError: If process with same key already exists
        """
        if not self._active:
            raise RuntimeError("CrossProcessing manager is not active")
            
        with self._processes_lock:
            if key in self._processes:
                raise ValueError(f"Process with key '{key}' already exists")
                
            # Set the process key 
            process_setup._set_process_key(key)
            
            # Create PData instance
            pdata_instance = _PData(
                pkey=key,
                pclass=process_setup.pclass,
                pid=None,  # Will be set when process starts
                num_loops=process_setup.num_loops,
                completed_loops=0
            )
            
            # Set PData instance in process
            process_setup._set_pdata_instance(pdata_instance)
                
            # Use default config if none provided
            if config is None:
                config = _PConfig()
                
            # Create result queue for this process
            result_queue = multiprocessing.Queue()
            
            # Initialize shared state for the process
            process_setup._initialize_shared_state(self._manager, result_queue)
            
            # Create the process runner
            runner = _ProcessRunner(process_setup, config, result_queue)
            
            # Create and start the multiprocessing.Process using standard approach
            mp_process = multiprocessing.Process(
                target=runner.run,
                name=f"XProcess-{key}"
            )
            
            # Store process information using key as the dict key
            process_info = {
                'process_setup': process_setup,
                'config': config,
                'mp_process': mp_process,
                'runner': runner,
                'result_queue': result_queue,
                'created_at': _get_current_time(),
                'pdata_instance': pdata_instance  # Store PData instance
            }
            
            self._processes[key] = process_info  # Use key instead of pname
            
            # Start the process
            mp_process.start()
            process_setup._status = PStatus.STARTING
            pdata_instance._update_status(PStatus.STARTING)
            
            print(_create_debug_message(f"Started process: {key} (class: {process_setup.pclass})"))
            
            return pdata_instance  # Return PData instead of key

    def get_pdata(self, key: str) -> Optional[_PData]:
        """Get the PData instance for a process by key."""
        with self._processes_lock:
            if key in self._processes:
                return self._processes[key]['pdata_instance']
        return None
        
    def get_process(self, key: str) -> Optional[_Process]:
        """Get a process by key."""
        with self._processes_lock:
            if key in self._processes:
                return self._processes[key]['process_setup']
        return None
        
    def get_process_status(self, key: str) -> Optional[PStatus]:
        """Get the current status of a process."""
        with self._processes_lock:
            if key not in self._processes:
                return None
                
            process_setup = self._processes[key]['process_setup']
            mp_process = self._processes[key]['mp_process']
            pdata_instance = self._processes[key]['pdata_instance']
            
            # ENHANCED: Check if process is dead and infer status
            if not mp_process.is_alive():
                exit_code = mp_process.exitcode
                
                # If process exited with error code, it crashed
                if exit_code != 0:
                    # Update both process_setup and pdata status to CRASHED
                    if process_setup._status not in [PStatus.CRASHED, PStatus.KILLED]:
                        process_setup._status = PStatus.CRASHED
                        pdata_instance._update_status(PStatus.CRASHED)
                        if exit_code == 1:
                            pdata_instance._set_error("Process crashed with error")
                else:
                    # Process exited normally - check if it was finished or killed
                    if process_setup._status not in [PStatus.FINISHED, PStatus.KILLED, PStatus.CRASHED]:
                        process_setup._status = PStatus.FINISHED
                        pdata_instance._update_status(PStatus.FINISHED)
            
            # Sync status between process_setup and pdata before returning
            if process_setup._status != pdata_instance.status:
                pdata_instance._update_status(process_setup._status)
            
            return process_setup._status
    

    def get_process_stats(self, key: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a process."""
        with self._processes_lock:
            if key in self._processes:
                return self._processes[key]['process_setup'].stats.get_summary()
        return None
        
    def get_process_result(self, key: str, timeout: Optional[float] = None):
        """
        Get the result from a completed process with Cerial deserialization support.
        
        Args:
            key: Key of process to get result from
            timeout: Maximum time to wait for result
            
        Returns:
            Result value from process, or None if no result/timeout/error
        """
        with self._processes_lock:
            if key not in self._processes:
                return None
                
            process_info = self._processes[key]
            mp_process = process_info['mp_process']
            result_queue = process_info['result_queue']
            pdata_instance = process_info['pdata_instance']
        
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
                            pdata_instance._set_result(None)
                            return None
                        else:
                            # Deserialize using Cerial
                            try:
                                from suitkaise._int.serialization.cerial_core import _deserialize
                                result = _deserialize(data)
                                pdata_instance._set_result(result)
                                return result
                            except Exception as deserialize_error:
                                error_msg = f"Failed to deserialize result: {deserialize_error}"
                                pdata_instance._set_error(error_msg)
                                print(_create_debug_message(
                                    f"Failed to deserialize result from process {key}: {deserialize_error}"
                                ))
                                return None
                    
                    elif status == 'serialize_error':
                        error_msg = f"Serialization error: {data}"
                        pdata_instance._set_error(error_msg)
                        print(_create_debug_message(f"Process {key} had serialization error: {data}"))
                        return None
                    
                    elif status == 'result_error':
                        error_msg = f"Result method error: {data}"
                        pdata_instance._set_error(error_msg)
                        print(_create_debug_message(f"Process {key} had __result__ error: {data}"))
                        return None
                    
                    else:
                        error_msg = f"Unknown status: {status}"
                        pdata_instance._set_error(error_msg)
                        print(_create_debug_message(f"Process {key} returned unknown status: {status}"))
                        return None
                        
                else:
                    # Legacy format or direct value - treat as success
                    return result_data
                    
            except (queue.Empty, EOFError, ValueError):
                return None
            except Exception as e:
                print(_create_debug_message(f"Unexpected error getting result: {e}"))
                return None
        else:
            return None
    
    def join_and_get_result(self, key: str, timeout: Optional[float] = None):
        """
        Convenience method to join a process and get its result in one call.
        
        Args:
            key: Key of process to join and get result from
            timeout: Maximum time to wait for process completion
            
        Returns:
            Tuple of (success: bool, result: Any)
            - success: True if process completed successfully
            - result: The process result, or None if no result/error
        """
        success = self.join_process(key, timeout)
        if success:
            result = self.get_process_result(key)
            return True, result
        else:
            return False, None
        
    def list_processes(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all managed processes."""
        result = {}
        
        with self._processes_lock:
            for key, info in self._processes.items():
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
                
                result[key] = {
                    'key': key,  # Include the key for clarity
                    'pclass': process_setup.pclass,  # Include process class name for reference
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
        
    def join_process(self, key: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a process to complete.
        
        Args:
            key: Key of process to join
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if process completed, False if timeout
        """
        with self._processes_lock:
            if key not in self._processes:
                return False
                
            mp_process = self._processes[key]['mp_process']
        
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
        
        with self._processes_lock:
            process_keys = list(self._processes.keys())
        
        for key in process_keys:
            if timeout is not None:
                elapsed = _elapsed_time(start_time)
                remaining = timeout - elapsed
                if remaining <= 0:
                    return False
            else:
                remaining = None
                
            if not self.join_process(key, remaining):
                return False
                
        return True
        
    def terminate_process(self, key: str, force: bool = False):
        """
        Terminate a specific process.
        
        Args:
            key: Key of process to terminate
            force: If True, use instakill. If False, use graceful rejoin.
        """
        with self._processes_lock:
            if key not in self._processes:
                return
                
            process_setup = self._processes[key]['process_setup']
        
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
        with self._processes_lock:
            process_keys = list(self._processes.keys())
        
        for key in process_keys:
            self.terminate_process(key, force=False)
            
        # Wait for graceful shutdown
        if not self.join_all(timeout):
            if force_after_timeout:
                print(_create_debug_message("Timeout reached, force-killing remaining processes"))
                for key in process_keys:
                    if self.get_process_status(key) not in [PStatus.FINISHED, PStatus.KILLED]:
                        self.terminate_process(key, force=True)
                        
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
        self._subprocesses_lock = threading.RLock()  # Use RLock for nested access
        
        # Set environment variable for subprocess depth tracking
        os.environ['XPROCESS_DEPTH'] = str(self._nesting_depth)
        
        print(_create_debug_message(
            f"SubProcessing manager initialized at depth {self._nesting_depth}"
        ))
        
    def create_process(self, key: str, subprocess_setup: _Process, config: Optional[_PConfig] = None) -> _PData:
        """
        Create and start a new subprocess with key-based tracking.
        
        Args:
            key: Unique key for tracking this subprocess
            subprocess_setup: Process instance with lifecycle hooks
            config: Process configuration (uses defaults if None)
            
        Returns:
            PData instance for tracking and result access
            
        Raises:
            ValueError: If subprocess with same key already exists
            RuntimeError: If manager is not active or depth limit exceeded
        """
        if not self._active:
            raise RuntimeError("SubProcessing manager is not active")
            
        with self._subprocesses_lock:
            if key in self._subprocesses:
                raise ValueError(f"SubProcess with key '{key}' already exists")
                
            # Set the process key 
            subprocess_setup._set_process_key(key)
            
            # Create PData instance
            pdata_instance = _PData(
                pkey=key,
                pclass=subprocess_setup.pclass,
                pid=None,  # Will be set when process starts
                num_loops=subprocess_setup.num_loops,
                completed_loops=0
            )
            
            # Set PData instance in process
            subprocess_setup._set_pdata_instance(pdata_instance)
                
            # Use default config if none provided
            if config is None:
                config = _PConfig()
                
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
                name=f"XSubProcess-{key}-depth{self._nesting_depth}"  # Use key instead of pname
            )
            
            # Store subprocess information using key as the dict key
            subprocess_info = {
                'subprocess_setup': subprocess_setup,
                'config': config,
                'mp_process': mp_process,
                'runner': runner,
                'result_queue': result_queue,
                'created_at': _get_current_time(),
                'nesting_depth': self._nesting_depth,
                'pdata_instance': pdata_instance  # Store PData instance
            }
            
            self._subprocesses[key] = subprocess_info  # Use key instead of pname
            
            # Start the subprocess
            mp_process.start()
            subprocess_setup._status = PStatus.STARTING
            pdata_instance._update_status(PStatus.STARTING)
            
            print(_create_debug_message(
                f"Started subprocess: {key} (class: {subprocess_setup.pclass}) (depth {self._nesting_depth})"
            ))
            
            return pdata_instance  # Return PData instead of key
        
    def get_pdata(self, key: str) -> Optional[_PData]:
        """Get the PData instance for a subprocess by key."""
        with self._subprocesses_lock:
            if key in self._subprocesses:
                return self._subprocesses[key]['pdata_instance']
        return None
        
    def get_subprocess(self, key: str) -> Optional[_Process]:
        """Get a subprocess by key."""
        with self._subprocesses_lock:
            if key in self._subprocesses:
                return self._subprocesses[key]['subprocess_setup']
        return None
        
    def get_subprocess_status(self, key: str) -> Optional[PStatus]:
        """Get the current status of a subprocess."""
        with self._subprocesses_lock:
            if key in self._subprocesses:
                return self._subprocesses[key]['subprocess_setup']._status
        return None
        
    def get_subprocess_result(self, key: str, timeout: Optional[float] = None):
        """
        Get the result from a completed subprocess with Cerial deserialization support.
        
        Args:
            key: Key of subprocess to get result from
            timeout: Maximum time to wait for result
            
        Returns:
            Result value from subprocess, or None if no result/timeout/error
        """
        with self._subprocesses_lock:
            if key not in self._subprocesses:
                return None
                
            subprocess_info = self._subprocesses[key]
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
                                from suitkaise._int.serialization.cerial_core import _deserialize
                                return _deserialize(data)
                            except Exception as deserialize_error:
                                print(_create_debug_message(
                                    f"Failed to deserialize result from subprocess {key}: {deserialize_error}"
                                ))
                                return None
                    
                    elif status == 'serialize_error':
                        print(_create_debug_message(f"Subprocess {key} had serialization error: {data}"))
                        return None
                    
                    elif status == 'result_error':
                        print(_create_debug_message(f"Subprocess {key} had __result__ error: {data}"))
                        return None
                    
                    else:
                        print(_create_debug_message(f"Subprocess {key} returned unknown status: {status}"))
                        return None
                        
                else:
                    # Legacy format or direct value - treat as success
                    return result_data
                    
            except (queue.Empty, EOFError, ValueError):
                return None
            except Exception as e:
                print(_create_debug_message(f"Unexpected error getting subprocess result: {e}"))
                return None
        else:
            return None
    
    def join_and_get_result(self, key: str, timeout: Optional[float] = None):
        """
        Convenience method to join a subprocess and get its result in one call.
        
        Args:
            key: Key of subprocess to join and get result from
            timeout: Maximum time to wait for subprocess completion
            
        Returns:
            Tuple of (success: bool, result: Any)
            - success: True if subprocess completed successfully
            - result: The subprocess result, or None if no result/error
        """
        success = self.join_subprocess(key, timeout)
        if success:
            result = self.get_subprocess_result(key)
            return True, result
        else:
            return False, None
        
    def list_subprocesses(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all managed subprocesses."""
        result = {}
        
        with self._subprocesses_lock:
            for key, info in self._subprocesses.items():
                subprocess_setup = info['subprocess_setup']
                mp_process = info['mp_process']
                
                result[key] = {
                    'key': key,  # Include the key for clarity
                    'pclass': subprocess_setup.pclass,  # Include process class name for reference
                    'status': subprocess_setup._status.value,
                    'pid': subprocess_setup.pid,
                    'current_loop': subprocess_setup.current_loop,
                    'is_alive': mp_process.is_alive(),
                    'created_at': info['created_at'],
                    'nesting_depth': info['nesting_depth'],
                }
                
        return result
        
    def join_subprocess(self, key: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a subprocess to complete.
        
        Args:
            key: Key of subprocess to join
            timeout: Maximum time to wait (None = wait forever)
            
        Returns:
            True if subprocess completed, False if timeout
        """
        with self._subprocesses_lock:
            if key not in self._subprocesses:
                return False
                
            mp_process = self._subprocesses[key]['mp_process']
        
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
        
        with self._subprocesses_lock:
            subprocess_keys = list(self._subprocesses.keys())
        
        for key in subprocess_keys:
            if timeout is not None:
                elapsed = _elapsed_time(start_time)
                remaining = timeout - elapsed
                if remaining <= 0:
                    return False
            else:
                remaining = None
                
            if not self.join_subprocess(key, remaining):
                return False
                
        return True
        
    def terminate_subprocess(self, key: str, force: bool = False):
        """
        Terminate a specific subprocess using signals.
        
        Args:
            key: Key of subprocess to terminate
            force: If True, use force signal. If False, use graceful signal.
        """
        with self._subprocesses_lock:
            if key not in self._subprocesses:
                return
                
            subprocess_info = self._subprocesses[key]
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
                    f"Sent {'force' if force else 'graceful'} shutdown signal to subprocess {key} (PID: {mp_process.pid})"
                ))
                
            except ProcessLookupError:
                # Process already dead
                pass
            except OSError as e:
                print(_create_debug_message(f"Error sending signal to subprocess {key}: {e}"))
                
    def _quick_process_internal(self, key: str, func: Callable, args: tuple = None, 
                               kwargs: dict = None, config: Optional[_QPConfig] = None) -> Any:
        """
        Internal implementation for quick function process execution.
        
        Args:
            key: Unique key for the process
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
            config = _QPConfig()
        
        # Create function process wrapper
        function_process = _FunctionProcess(key, func, args, kwargs)  # Use key as pname
        
        # Convert to full _PConfig
        process_config = config.to_process_config()
        
        # Create and start the process
        process_id = self.create_process(key, function_process, process_config)
        
        # Wait for completion and get result
        success, result = self.join_and_get_result(process_id, config.join_in)
        
        if not success:
            raise RuntimeError(f"Quick process '{key}' failed to complete within {config.join_in}s timeout")
        
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
        with self._subprocesses_lock:
            subprocess_keys = list(self._subprocesses.keys())
        
        for key in subprocess_keys:
            self.terminate_subprocess(key, force=False)
            
        # Phase 2: Wait for graceful shutdown
        graceful_timeout = timeout * 0.7  # Give 70% of time for graceful shutdown
        if not self.join_all(graceful_timeout):
            if force_after_timeout:
                print(_create_debug_message("Graceful timeout reached, sending force signals"))
                
                # Phase 3: Force termination for remaining subprocesses
                for key in subprocess_keys:
                    with self._subprocesses_lock:
                        if key in self._subprocesses:
                            subprocess_info = self._subprocesses[key]
                            if subprocess_info['mp_process'].is_alive():
                                self.terminate_subprocess(key, force=True)
                        
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