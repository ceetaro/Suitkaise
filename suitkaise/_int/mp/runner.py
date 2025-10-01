"""
Xprocess Internal Cross-processing Engine - Process Runner

This module contains the _ProcessRunner class that handles the actual execution
loop, timing, error handling, and lifecycle management in the subprocess.
"""

import threading
import traceback
from typing import Optional

from .processes import _Process, PStatus
from .configs import _PConfig
from .exceptions import (
    PreloopError, MainLoopError, PostLoopError,
    PreloopTimeoutError, MainLoopTimeoutError, PostLoopTimeoutError
)
from suitkaise.sktime._int.time_ops import _get_current_time, _elapsed_time
from suitkaise._int.core.format_ops import _create_debug_message


class _ProcessRunner:
    """
    Internal process runner that executes in the subprocess.
    
    This class handles the actual execution loop, timing, error handling,
    and lifecycle management for a user-defined Process instance.
    """
    
    def __init__(self, process_setup: _Process, config: _PConfig, result_queue):
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
                    f"Process {self.process_setup.pkey} started (PID: {self.process_setup.pid}){config_str}"
                ))
            
            # Main execution loop
            while self.process_setup._should_continue_loop():
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
                    break  # Timeout or error occurred (status already set in _execute_loop_iteration)
                    
                # Check for graceful termination signal
                if (self.process_setup._control_signal is not None and 
                    self.process_setup._control_signal.value == 1):  # rejoin
                    break
                    
        except Exception as e:
            # Fatal error in process runner itself (not lifecycle errors)
            self.process_setup._status = PStatus.CRASHED
            
            # Update PData instance if available 
            if hasattr(self.process_setup, '_pdata_instance') and self.process_setup._pdata_instance:
                self.process_setup._pdata_instance._update_status(PStatus.CRASHED)
                self.process_setup._pdata_instance._set_error(str(e))
            
            self.process_setup.stats.record_error(e, self.process_setup.current_loop)
            print(_create_debug_message(
                f"Fatal error in process {self.process_setup.pkey}: {e}",
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
                        f"Error in __onfinish__ for process {self.process_setup.pkey}: {e}"
                    ))
                    
            # Always call __result__ if it exists and serialize with Cerial
            if hasattr(self.process_setup, '__result__'):
                try:
                    # Check if __result__ is implemented (not just the default return None)
                    result_method = getattr(self.process_setup, '__result__')
                    if result_method.__func__ is not _Process.__result__:
                        result = self.process_setup.__result__()
                        
                        # Serialize result using Cerial for complex object support
                        try:
                            from suitkaise._int.serialization.cerial_core import _serialize
                            serialized_result = _serialize(result)
                            self.result_queue.put(('success', serialized_result))
                            if self.config.log_loops:
                                print(_create_debug_message(
                                    f"Process {self.process_setup.pkey} returned and serialized result"
                                ))
                        except Exception as serialize_error:
                            print(_create_debug_message(
                                f"Failed to serialize result from process {self.process_setup.pkey}: {serialize_error}"
                            ))
                            # Store error info instead
                            self.result_queue.put(('serialize_error', str(serialize_error)))
                    else:
                        # Default implementation, put None
                        self.result_queue.put(('success', None))
                except Exception as e:
                    print(_create_debug_message(
                        f"Error in __result__ for process {self.process_setup.pkey}: {e}"
                    ))
                    # Put error info in queue
                    self.result_queue.put(('result_error', str(e)))
            else:
                # No __result__ method, put None
                self.result_queue.put(('success', None))
                
            # CRITICAL: Only call _join_process if status is not CRASHED
            if self.process_setup._status != PStatus.CRASHED:
                self.process_setup._join_process()
            # If status is CRASHED, leave it as CRASHED for restart detection
            
            # CRITICAL: Ensure process exits with proper code for crash detection
            if self.process_setup._status == PStatus.CRASHED:
                if self.config.log_loops:
                    print(_create_debug_message(
                        f"Process {self.process_setup.pkey} exiting with error code 1 (CRASHED)"
                    ))
                import sys
                sys.exit(1)  # Force non-zero exit code for crash detection
            else:
                if self.config.log_loops:
                    print(_create_debug_message(
                        f"Process {self.process_setup.pkey} exiting with code 0 (SUCCESS)"
                    ))
                # Normal successful exit (status will be FINISHED from _join_process)
                

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
        
        # NOTE: All error handling is now done in _execute_with_granular_timeouts()
        # This method just returns True/False for loop continuation


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
            # CRITICAL: Lifecycle errors - handle restart logic here
            self.process_setup.stats.record_error(e, self.process_setup.current_loop)
            
            # IMMEDIATELY set status to CRASHED
            self.process_setup._status = PStatus.CRASHED
            
            # Update PData instance and ensure it's synchronized
            if hasattr(self.process_setup, '_pdata_instance') and self.process_setup._pdata_instance:
                self.process_setup._pdata_instance._update_status(PStatus.CRASHED)
                self.process_setup._pdata_instance._set_error(str(e))
            
            # Log the error
            error_type = type(e).__name__
            print(_create_debug_message(f"{error_type} in process {self.process_setup.pkey}: {e}"))
            
            # DECISION: Restart or crash?
            restart_enabled = self.config.crash_restart
            restarts_remaining = (self.process_setup._restart_count < self.config.max_restarts)
            
            if restart_enabled and restarts_remaining:
                # Return False to exit loop cleanly, allowing restart
                print(_create_debug_message(
                    f"Process {self.process_setup.pkey} will allow restart "
                    f"(attempt {self.process_setup._restart_count + 1}/{self.config.max_restarts})"
                ))
                return False  # This will break the main loop and exit normally for restart
            else:
                # CRASH the process immediately - don't return False
                if not restart_enabled:
                    print(_create_debug_message(f"Process {self.process_setup.pkey} crashing (restart disabled)"))
                else:
                    print(_create_debug_message(f"Process {self.process_setup.pkey} crashing (max restarts exceeded)"))
                
                # Force the process to crash by re-raising the error
                raise e
            
        except Exception as e:
            # Unexpected error - always crash
            self.process_setup._status = PStatus.CRASHED
            if hasattr(self.process_setup, '_pdata_instance') and self.process_setup._pdata_instance:
                self.process_setup._pdata_instance._update_status(PStatus.CRASHED)
                self.process_setup._pdata_instance._set_error(str(e))
            
            self.process_setup.stats.record_error(e, self.process_setup.current_loop)
            print(_create_debug_message(f"Unexpected error in process {self.process_setup.pkey}: {e}"))
            raise e


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
        """Execute a section with timeout protection using threading approach."""
        
        # If timeout is None (explicitly disabled), execute without timeout
        if timeout_duration is None:
            return self._execute_section_without_timeout(
                section_func, regular_error_class, section_name
            )
        
        # Use threading-based timeout for cross-platform compatibility
        result = [None]  # Mutable container for result
        exception = [None]  # Mutable container for exception
        
        def run_section():
            try:
                section_func()
                result[0] = True
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=run_section)
        thread.daemon = True
        thread.start()
        thread.join(timeout_duration)
        
        if thread.is_alive():
            # Timeout occurred - thread is still running
            timeout_error = timeout_error_class(
                timeout_duration, 
                self.process_setup.pkey, 
                self.process_setup.current_loop
            )
            
            # Record timeout in statistics
            self.process_setup.stats.record_timeout(
                section_name, timeout_duration, self.process_setup.current_loop
            )
            
            # Re-raise as our custom error
            raise timeout_error
        
        if exception[0]:
            # Wrap regular errors in section-specific error class
            section_error = regular_error_class(
                exception[0], self.process_setup.pkey, self.process_setup.current_loop
            )
            raise section_error
        
        return result[0] is True
            
    def _execute_section_without_timeout(self, section_func: callable, 
                                       regular_error_class: type, section_name: str) -> bool:
        """Execute a section without timeout protection."""
        try:
            section_func()
            return True
            
        except Exception as e:
            # Wrap in section-specific error class
            section_error = regular_error_class(
                e, self.process_setup.pkey, self.process_setup.current_loop
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
            f"Process {self.process_setup.pkey} completed loop {self.process_setup.current_loop}: {timing_info}"
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