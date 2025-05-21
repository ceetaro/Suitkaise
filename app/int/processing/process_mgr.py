# -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0 or the GNU General Public License v3.
#
# ~~ Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
#
# ~~ GNU General Public License, Version 3 (http://www.gnu.org/licenses/gpl-3.0.html)
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -------------------------------------------------------------------------------------

# suitkaise/int/processing/process_mgr.py

"""
Process management for Suitkaise.

This module manages the process pool -- creating, reserving, and managing
processes with automatic initialization.

"""

import multiprocessing as mp
import threading
import os
import traceback
import pickle
from enum import Enum, auto
from typing import Callable, Dict, Optional, List, Any, Tuple, Union

import suitkaise_app.int.utils.time.sktime as sktime
from suitkaise_app.int.processing.init_registry import ProcessingInitRegistry
from suitkaise_app.int.processing.reservations import ReservedProcesses
from suitkaise_app.int.utils.fib.fib import FunctionInstance, FunctionInstanceBuilder


class ProcessError(Exception):
    """Exception raised when a process encounters an error."""
    pass

class ProcessState(Enum):
    """Enum for process states."""
    RUNNING = auto()               # Process is running normally
    FINISHING = auto()             # Process is finishing its last cycle
    CLEANING = auto()              # Process is cleaning up resources
    READY_TO_TERMINATE = auto()    # Process is ready to be terminated
    TERMINATED = auto()            # Process has been terminated
    ERROR = auto()                 # Process ended with error

class ShutdownInfo:
    """Container for shutdown related information."""

    def __init__(self, time_to_finish: float = 0.0,
                 time_to_cleanup: float = 0.0) -> None:
        """
        Initialize shutdown information.

        Args:
            time_to_finish (float): Allotted time to finish operations.
            time_to_cleanup (float): Allotted time to clean up.

        """
        self.state = ProcessState.RUNNING
        self.time_to_finish = time_to_finish
        self.time_to_cleanup = time_to_cleanup
        self.finishing_start_time = None # start when shutdown is requested
        self.cleaning_start_time = None # start when finished_event is set

        self.shutdown_requested_event = mp.Event() # parent sets to request shutdown
        self.finished_event = mp.Event() # child sets when it is done finishing its main loop
        self.ready_to_terminate_event = mp.Event() # child sets when it is done cleaning up


class ProcessInfo:
    """Container for process related information."""

    def __init__(self, process: mp.Process,
                 name: str,
                 reservation: Optional[str] = None,
                 time_to_finish: float = 0.0,
                 time_to_cleanup: float = 0.0) -> None:
        """
        Initialize a ProcessInfo object.

        Args:
            process (multiprocessing.Process): The process object.
            name (str): The name of the process.
            reservation (Optional[str]): The reservation name, if any.
            time_to_finish (float): Maximum time allowed to finish current operations.
            time_to_cleanup (float): Maximum time allowed for cleanup operations.
        """
        self.process = process
        self.pid = process.pid if process.pid else None
        self.name = name
        self.reservation = reservation
        self.created_at = sktime.now()
        self.is_alive = process.is_alive
        self.state = ProcessState.RUNNING
        self.last_state_change = sktime.now()
        
        # Results and errors
        self.init_results = {} # results from initialization functions
        self.result = None  # Return value from the process function
        self.error = None  # Error message if process failed
        self.error_traceback = None  # Traceback if process failed
        self.result_received = False  # Whether any result/error was received

        # shutdown information
        self.shutdown_info = ShutdownInfo(
            time_to_finish=time_to_finish,
            time_to_cleanup=time_to_cleanup
        )

    def __repr__(self) -> str:
        """Return a string representation of the ProcessInfo object."""
        status = "alive" if self.is_alive() else "not alive"
        return f"ProcessInfo(name={self.name}, pid={self.pid}, state={self.state.name}, status={status})"
    
    def update_state(self, state: ProcessState):
        """
        Update the process state.
        
        Args:
            state: The new process state.
        """
        self.state = state
        self.last_state_change = sktime.now()
    
class ProcessManager:
    """
    Manages processes for the Suitkaise application.

    This class handles creation, reservation, and management of processes,
    including automatic initialization of processes using registered functions.
    
    """
    _process_mgr_instance = None
    _process_mgr_lock = threading.Lock()

    def __new__(cls):
        with cls._process_mgr_lock:
            if cls._process_mgr_instance is None:
                cls._process_mgr_instance = super(ProcessManager, cls).__new__(cls)
                cls._init_process_manager()
            return cls._process_mgr_instance
        
    @classmethod
    def _init_process_manager(cls):
        """
        Initialize the ProcessManager instance.

        This method is called only once when the singleton instance is created.
        
        """
        instance = cls._process_mgr_instance
        instance.processes = {}  # Dict[int, ProcessInfo]
        instance.reserved_processes = {}  # Dict[str, int]
        instance.main_pid = os.getpid()

        # track this process as the main process
        main_process = mp.current_process()
        process_info = ProcessInfo(
            main_process,
            main_process.name,
            "main_process"
        )
        instance.processes[instance.main_pid] = process_info

        # Monitor thread for cleanup
        instance._shutdown_event = threading.Event()
        instance._monitor_thread = threading.Thread(
            target=instance._monitor_processes,
            daemon=True,
            name="process_manager_monitor"
        )
        instance._monitor_thread.start()

        print(f"ProcessManager initialized in main process: {instance.main_pid}")
    
    def _monitor_processes(self):
        """
        Monitor thread that periodically checks process status.
        """
        while not self._shutdown_event.is_set():
            try:
                # Check for processes that have terminated
                for pid, process_info in list(self.processes.items()):
                    if pid != self.main_pid and not process_info.is_alive():
                        if process_info.state not in (ProcessState.TERMINATED, ProcessState.ERROR):
                            if process_info.error:
                                process_info.update_state(ProcessState.ERROR)
                            else:
                                process_info.update_state(ProcessState.TERMINATED)
            except Exception as e:
                print(f"Error in process monitor: {e}")
            
            # Sleep before next check
            self._shutdown_event.wait(2.0)  # Check every 2 seconds


    def create_process(self, target: FunctionInstance,
                       name: str,
                       reservation: Optional[str] = None,
                       daemon: bool = False,
                       init_results_callback: Union[Callable[[Dict[str, Any]], None], FunctionInstance] = None,
                       component_threads: Dict[str, Union[Callable, FunctionInstance]] = None,
                       time_to_finish_before_shutdown: float = 0.0,
                       time_to_cleanup_before_shutdown: float = 0.0,
                       result_timeout: float = 30.0) -> ProcessInfo:
        """
        Create a new process with automatic initialization.

        Args:
            target: The function to be run in the process's main thread
            name: Name for the process
            reservation: Reserve this process for a specific purpose
            daemon: Whether the process should be a daemon
            init_results_callback: Function to call with initialization results
            component_threads: Dictionary mapping component names to their thread functions
            time_to_finish_before_shutdown: Time allowed to finish operations before shutdown
            time_to_cleanup_before_shutdown: Time allowed for cleanup before shutdown
            result_timeout: Time to wait for process result before giving up

        Returns:
            ProcessInfo object containing information about the created process
        """
        # check init_results_callback if it is a function instance
        if isinstance(init_results_callback, FunctionInstance):
            if hasattr(init_results_callback, 'return_type'):
                if init_results_callback.return_type != 'dict':
                    raise ValueError("init_results_callback must return a dictionary.")
            else:
                raise ValueError("init_results_callback must be a FunctionInstance with a return type.")
            
        if component_threads is None:
            component_threads = {}

        # create pipes for communication
        init_parent_conn, init_child_conn = mp.Pipe()  # For initialization results
        result_parent_conn, result_child_conn = mp.Pipe()  # For function results/errors

        shutdown_info = ShutdownInfo(
            time_to_finish=time_to_finish_before_shutdown,
            time_to_cleanup=time_to_cleanup_before_shutdown
        )

        args = target.get_args()
        kwargs = target.get_kwargs()

        # wrap the target function to include initialization, error handling, and component threads
        def wrapped_target(*args, **kwargs):
            try:
                # initialize process using registry
                init_registry = ProcessingInitRegistry()
                init_results = init_registry.execute_process_initializers()

                # Create thread manager for component threads
                from suitkaise_app.int.processing.thread_mgr import ThreadManager
                thread_mgr = ThreadManager()

                # Create component threads
                component_thread_info = {}
                for comp_name, thread_func in component_threads.items():
                    thread_info = thread_mgr.create_thread(
                        target=thread_func if isinstance(thread_func, Callable) \
                                       else thread_func.execute,
                        name=f"{comp_name}_thread",
                        daemon=True,
                    )
                    component_thread_info[comp_name] = {
                        'thread_id': thread_info.thread_id,
                        'name': thread_info.name
                    }

                # send initialization results and thread info to the parent process
                try:
                    init_child_conn.send({
                        'init_results': init_results,
                        'component_threads': component_thread_info
                    })
                except (pickle.PickleError, TypeError) as e:
                    # Handle serialization errors
                    init_child_conn.send({
                        'init_results': {"error": f"Could not serialize initialization results: {str(e)}"},
                        'component_threads': {}
                    })
                
                # Execute the target function with shutdown support
                try:
                    if hasattr(target, 'can_shutdown'):
                        # Function is shutdown-aware
                        with FunctionInstanceBuilder() as fib:
                            fib.add_function_instance(target)
                            fib.update_argument('shutdown_info', shutdown_info)
                            wrapped_target = fib.build()

                        modified_args = wrapped_target.get_args()
                        modified_kwargs = wrapped_target.get_kwargs()
                        
                        result = wrapped_target.execute(*modified_args, **modified_kwargs)
                    else:
                        # Regular target function - monitor shutdown
                        def shutdown_monitor():
                            # Wait for shutdown signal
                            shutdown_info.shutdown_requested_event.wait()

                            # Signal finishing
                            shutdown_info.state = ProcessState.FINISHING
                            shutdown_info.finishing_start_time = sktime.now()
                            shutdown_info.finished_event.set()
                            
                            # Signal cleaning
                            shutdown_info.state = ProcessState.CLEANING
                            shutdown_info.cleaning_start_time = sktime.now()
                            
                            # Signal ready to terminate
                            shutdown_info.state = ProcessState.READY_TO_TERMINATE
                            shutdown_info.ready_to_terminate_event.set()

                        # Start the shutdown monitor
                        monitor_thread = threading.Thread(
                            target=shutdown_monitor,
                            daemon=True,
                            name=f"{name}_shutdown_monitor"
                        )
                        monitor_thread.start()
                        
                        # Execute the target function
                        result = target.execute(*args, **kwargs)
                    
                    # Send successful result
                    try:
                        result_child_conn.send({
                            "success": True,
                            "result": result
                        })
                    except (pickle.PickleError, TypeError):
                        # Handle serialization errors
                        result_child_conn.send({
                            "success": False,
                            "error": "Result could not be serialized",
                            "error_type": "SerializationError",
                            "error_traceback": "Result object was not serializable"
                        })
                        
                except Exception as e:
                    # Capture and send error information
                    error_traceback = traceback.format_exc()
                    try:
                        result_child_conn.send({
                            "success": False,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "error_traceback": error_traceback
                        })
                    except (pickle.PickleError, TypeError):
                        # Handle serialization errors with the error itself
                        result_child_conn.send({
                            "success": False,
                            "error": "Error occurred but could not be serialized",
                            "error_type": "SerializationError",
                            "error_traceback": "Error details could not be sent through pipe"
                        })
                    
                    # Re-raise the exception
                    raise
                
            except Exception as e:
                # Handle any exceptions in the wrapper itself
                print(f"Critical error in process wrapper: {str(e)}")
                try:
                    result_child_conn.send({
                        "success": False,
                        "error": f"Critical error in process wrapper: {str(e)}",
                        "error_type": type(e).__name__,
                        "error_traceback": traceback.format_exc()
                    })
                except:
                    # Last resort - if we can't send the error, just re-raise
                    pass
                raise
            finally:
                # Close the pipes
                try:
                    init_child_conn.close()
                    result_child_conn.close()
                except:
                    pass
        
        # create the process
        process = mp.Process(
            target=wrapped_target,
            args=args,
            kwargs=kwargs,
            name=name,
            daemon=daemon
        )

        # start the process
        process.start()

        # create process info
        process_info = ProcessInfo(
            process=process,
            name=name,
            reservation=reservation,
            time_to_finish=time_to_finish_before_shutdown,
            time_to_cleanup=time_to_cleanup_before_shutdown
        )

        # transfer the shutdown info to the process
        process_info.shutdown_info = shutdown_info

        # store the process
        self.processes[process.pid] = process_info

        # if a reservation is provided, store it
        if reservation:
            if reservation in self.reserved_processes:
                raise ValueError(f"Process already reserved for {reservation}")
            self.reserved_processes[reservation] = process.pid
            print(f"Process {process.pid} reserved for {reservation}")
        else:
            print(f"Process {process.pid} created without reservation")

        # Function to receive initialization results
        def receive_init_results():
            try:
                if init_parent_conn.poll(5):  # Wait up to 5 seconds
                    try:
                        init_data = init_parent_conn.recv()
                        process_info.init_results = init_data.get('init_results', {})
                        
                        # Call the init results callback if provided
                        if init_results_callback:
                            if isinstance(init_results_callback, FunctionInstance):
                                with FunctionInstanceBuilder() as fib:
                                    fib.add_function_instance(init_results_callback)
                                    fib.update_argument('init_results', process_info.init_results)
                                    with_results_callback = fib.build()
                                with_results_callback.execute()
                            else:
                                init_results_callback(process_info.init_results)
                    except EOFError:
                        print(f"Initialization pipe closed unexpectedly for process {process_info.name}")
                    except Exception as e:
                        print(f"Error receiving initialization results for process {process_info.name}: {e}")
                else:
                    print(f"Process {process_info.name} did not send initialization results within timeout")
            finally:
                # Close the parent end of the initialization pipe
                init_parent_conn.close()
        
        # Function to receive process results
        def receive_process_results():
            try:
                if result_parent_conn.poll(result_timeout):  # Wait for result with timeout
                    try:
                        result_data = result_parent_conn.recv()
                        process_info.result_received = True
                        
                        if result_data.get("success", False):
                            process_info.result = result_data.get("result")
                        else:
                            process_info.error = result_data.get("error")
                            process_info.error_traceback = result_data.get("error_traceback")
                            process_info.update_state(ProcessState.ERROR)
                    except EOFError:
                        print(f"Result pipe closed unexpectedly for process {process_info.name}")
                    except Exception as e:
                        print(f"Error receiving results for process {process_info.name}: {e}")
                else:
                    # Timeout occurred - process didn't send results
                    print(f"Timed out waiting for process {process_info.name} to return results")
            finally:
                # Close the parent end of the result pipe
                result_parent_conn.close()
        
        # Start threads to receive initialization results and process results
        init_thread = threading.Thread(
            target=receive_init_results,
            daemon=True,
            name=f"{name}_init_receiver"
        )
        init_thread.start()
        
        result_thread = threading.Thread(
            target=receive_process_results,
            daemon=True,
            name=f"{name}_result_receiver"
        )
        result_thread.start()

        # return the process info
        return process_info


    def reserve_process(self, target: FunctionInstance,
                        reservation: str,
                        daemon: bool = False,
                        init_results_callback: Union[Callable[[Dict[str, Any]], None], FunctionInstance] = None,
                        component_threads: Dict[str, Union[Callable, FunctionInstance]] = None
                        ) -> ProcessInfo:
        """
        Create a reserved process for a specific purpose.

        This is a convenience method for create_process with a reservation.
        
        Args:
            target: Function to run in the process
            reservation: Name of reservation
            daemon: Whether the process should be a daemon
            init_results_callback: Function to call with initialization results
            component_threads: Dictionary of component threads to create
            
        Returns:
            ProcessInfo for the created process
        """
        return self.create_process(
            target=target,
            name=reservation,
            reservation=reservation,
            daemon=daemon,
            init_results_callback=init_results_callback,
            component_threads=component_threads
        )
    
    def get_process(self, name_or_pid: Union[str, int]) -> Optional[ProcessInfo]:
        """
        Get a process by name or PID.

        Args:
            name_or_pid (Union[str, int]): The name or PID of the process.

        Returns:
            Optional[ProcessInfo]: The ProcessInfo object if found, else None.
        
        """
        if isinstance(name_or_pid, int):
            return self.processes.get(name_or_pid)
        
        if name_or_pid in self.reserved_processes:
            pid = self.reserved_processes[name_or_pid]
            return self.processes.get(pid)
        
        # search by name
        for process_info in self.processes.values():
            if process_info.name == name_or_pid:
                return process_info
            
        return None
    
    def shutdown_process(self,
                        name_or_id: Union[str, int],
                        force_termination: bool = False,
                        custom_time_to_finish: Optional[float] = None,
                        custom_time_to_cleanup: Optional[float] = None) -> bool:
        """
        Attempt to cleanly shut down a process following these steps:
        1. Signal the process to finish its operations (sets shutdown_requested_event)
        2. Wait for the process to finish its normal operations (waits for finished_event)
        3. Wait for the process to signal it's ready for termination (waits for ready_to_terminate_event)
        4. Terminate the process
        
        Args:
            name_or_id: The name or PID of the process
            force_termination: If True, skip the phased shutdown and terminate immediately
            custom_time_to_finish: Override the process's time to finish timeout
            custom_time_to_cleanup: Override the process's time to cleanup timeout
            
        Returns:
            True if the process was shut down successfully, False otherwise

        """
        process_info = self.get_process(name_or_id)
        if not process_info:
            print(f"Process {name_or_id} not found.")
            return False
        
        # Check if the process is already dead
        if not process_info.is_alive():
            print(f"Process {name_or_id} is already terminated.")
            self._cleanup_process_resources(process_info)
            return True
        
        # If force requested, just terminate the process
        if force_termination:
            print(f"Force terminating process {name_or_id}.")
            return self._force_terminate_process(process_info)
        
        shutdown_info = process_info.shutdown_info

        # Step 1: Signal the process that shutdown is requested
        print(f"Signaling process {process_info.name} to shut down...")
        shutdown_info.finishing_start_time = sktime.now()  # Start the finishing timer
        shutdown_info.shutdown_requested_event.set()
        process_info.update_state(ProcessState.FINISHING)
        
        # Step 2: Wait for the process to finish its normal operations
        finishing_timeout = custom_time_to_finish or shutdown_info.time_to_finish
        print(f"Waiting up to {finishing_timeout} seconds for process to finish normal operations...")
        
        operations_finished = shutdown_info.finished_event.wait(timeout=finishing_timeout)
        if not operations_finished:
            print(f"Process {process_info.name} did not finish operations within {finishing_timeout} seconds.")
            print("Forcing termination...")
            return self._force_terminate_process(process_info)
        
        print(f"Process {process_info.name} has finished normal operations.")
        process_info.update_state(ProcessState.CLEANING)
        
        # Set cleaning start time when finished_event is received
        shutdown_info.cleaning_start_time = sktime.now()
        
        # Step 3: Wait for cleanup to complete
        cleanup_timeout = custom_time_to_cleanup or shutdown_info.time_to_cleanup
        print(f"Waiting up to {cleanup_timeout} seconds for cleanup to complete...")
        
        cleanup_completed = shutdown_info.ready_to_terminate_event.wait(timeout=cleanup_timeout)
        if not cleanup_completed:
            print(f"Process {process_info.name} did not complete cleanup within {cleanup_timeout} seconds.")
            print("Forcing termination...")
            return self._force_terminate_process(process_info)
        
        print(f"Process {process_info.name} has completed cleanup and is ready for termination.")
        process_info.update_state(ProcessState.READY_TO_TERMINATE)
        
        # Step 4: Terminate the process
        try:
            process_info.process.terminate()
            
            # Wait a moment for the process to terminate
            process_info.process.join(1.0)
            
            # If it's still alive, use SIGKILL
            if process_info.process.is_alive():
                print(f"Process {process_info.name} did not terminate normally, sending SIGKILL...")
                os.kill(process_info.pid, 9)
            
            process_info.update_state(ProcessState.TERMINATED)
            self._cleanup_process_resources(process_info)
            return True
            
        except Exception as e:
            print(f"Error terminating process {process_info.name}: {e}")
            return False

    def _force_terminate_process(self, process_info: ProcessInfo) -> bool:
        """
        Forcefully terminate a process.

        Args:
            process_info (ProcessInfo): The ProcessInfo object of the process to terminate.

        Returns:
            bool: True if the process was terminated successfully, False otherwise.
        
        """
        try:
            process_info.update_state(ProcessState.READY_TO_TERMINATE)

            # terminate the process
            process_info.process.terminate()
            process_info.process.join(1.0)

            # check if the process is still alive and SIGKILL if needed
            if process_info.process.is_alive():
                print(f"Process {process_info.name} did not terminate, "
                      "sending SIGKILL...")
                os.kill(process_info.pid, 9)

            process_info.update_state(ProcessState.TERMINATED)
            self._cleanup_process_resources(process_info)
            return True
        
        except Exception as e:
            print(f"Error force terminating process {process_info.name}: {e}")
            return False
        
    def _cleanup_process_resources(self, process_info: ProcessInfo) -> None:
        """
        Clean up resources associated with a terminated process.

        Args:
            process_info (ProcessInfo): The ProcessInfo object of the terminated process.
        
        """
        # remove from reserved processes if applicable
        if process_info.reservation and process_info.reservation in self.reserved_processes:
            self.reserved_processes.pop(process_info.reservation)
            print(f"Process {process_info.name} released reservation {process_info.reservation}")

        # remove from processes
        if process_info.pid in self.processes:
            self.processes.pop(process_info.pid)
            print(f"Process {process_info.name} cleaned up from process list.")

        print(f"Process {process_info.name} resources cleaned up.")
    
    def get_process_result(self, name_or_id: Union[str, int], timeout: Optional[float] = None) -> Any:
        """
        Get the result from a process.
        
        Args:
            name_or_id: The name or PID of the process
            timeout: Maximum time to wait for process to complete
            
        Returns:
            The result from the process or None if not available
            
        Raises:
            ValueError: If the process is not found
            ProcessError: If the process ended with an error
            TimeoutError: If the timeout is reached waiting for the process
        """
        process_info = self.get_process(name_or_id)
        if not process_info:
            raise ValueError(f"Process {name_or_id} not found")
            
        # If process is still running and timeout specified, wait for it
        if process_info.is_alive() and timeout is not None:
            process_info.process.join(timeout)
            if process_info.is_alive():
                raise TimeoutError(f"Process {process_info.name} did not complete within timeout")
                
        # Check for errors
        if process_info.error:
            error_msg = f"Process {process_info.name} failed with error: {process_info.error}"
            if process_info.error_traceback:
                error_msg += f"\n{process_info.error_traceback}"
            raise ProcessError(error_msg)
            
        # Return the result
        return process_info.result
        
    def shutdown(self, wait_timeout: float = 5.0):
        """
        Shutdown the process manager and all managed processes.
        
        Args:
            wait_timeout: Maximum time to wait for each process to shut down
            
        Returns:
            True if all processes were shut down successfully, False otherwise
        """
        print("Shutting down ProcessManager...")
        
        # Signal monitor thread to stop
        self._shutdown_event.set()
        
        # Get all active processes except the main process
        processes_to_shutdown = []
        for pid, process_info in list(self.processes.items()):
            if pid != self.main_pid and process_info.is_alive():
                processes_to_shutdown.append(pid)
                
        # Shut down each process
        success = True
        for pid in processes_to_shutdown:
            process_info = self.processes.get(pid)
            if process_info:
                if not self.shutdown_process(pid, custom_time_to_finish=wait_timeout):
                    # If clean shutdown fails, force terminate
                    if not self._force_terminate_process(process_info):
                        success = False
                        
        # Wait for monitor thread to stop
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            
        print("ProcessManager shutdown complete.")
        return success
            
# Decorator for marking functions as shutdown-aware
def can_shutdown(func: Union[Callable, FunctionInstance]) -> Union[Callable, FunctionInstance]:
    """
    Decorator to mark a function as capable of handling shutdown signals.

    Functions marked with this decorator will receive a shutdown_info
    when run as a process target. The function being decorated should use
    this to coordinate a clean shutdown.

    Example:

    @can_shutdown
    def my_process(arg1, shutdown_info=None, arg2):
        try:
            finishing_up = False  # Internal flag, not a shared Event
            
            while not finishing_up:
                if shutdown_info.shutdown_requested_event.is_set():
                    # Set internal flag to exit after this iteration
                    finishing_up = True
                    shutdown_info.state = ProcessState.FINISHING
                    
                # Do normal work for this iteration
                do_work(arg1, arg2)
            
            # Loop has exited naturally after completing the last iteration
            # Signal that normal operations are complete
            shutdown_info.finished_event.set()
            
            # Now in cleaning phase
            shutdown_info.state = ProcessState.CLEANING
            
            # Perform cleanup
            clean_up_resources()
            
            # Signal ready to terminate
            shutdown_info.state = ProcessState.READY_TO_TERMINATE
            shutdown_info.ready_to_terminate_event.set()
            
        except Exception as e:
            print(f"Error in process: {e}")
    """
    if isinstance(func, FunctionInstance):
        func.func.__can_shutdown__ = True
    else:
        func.__can_shutdown__ = True

    return func
    
