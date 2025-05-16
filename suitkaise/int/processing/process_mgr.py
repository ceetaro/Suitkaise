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
from typing import Callable, Dict, Optional, List, Any, Tuple, Union

import suitkaise.int.utils.time.sktime as sktime
from suitkaise.int.processing.init_registry import ProcessingInitRegistry
from suitkaise.int.processing.reservations import ReservedProcesses
from suitkaise.int.utils.fib.fib import FunctionInstance, FunctionInstanceBuilder

class ShutdownState:
    """
    Pseudo-enum for shutdown states.

    """
    # process is normally operating, not shutting down
    RUNNING = "running" 

    # process has received a shutdown signal and is finishing its last cycle
    FINISHING = "finishing"

    # process has finished its last normal operations, and cleaning up
    CLEANING = "cleaning"

    # process has finished cleaning up and is ready to terminate
    READY_TO_TERMINATE = "ready_to_terminate"

    # process has been terminated
    TERMINATED = "terminated"

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
        self.state = ShutdownState.RUNNING
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
        """
        self.process = process
        self.pid = process.pid if process.pid else None
        self.name = name
        self.reservation = reservation
        self.created_at = sktime.now()
        self.is_alive = process.is_alive
        self.init_results = {} # results from initialization functions

        # shutdown information
        self.shutdown_info = ShutdownInfo(
            time_to_finish=time_to_finish,
            time_to_cleanup=time_to_cleanup
        )

    def __repr__(self) -> str:
        """Return a string representation of the ProcessInfo object."""
        status = "alive" if self.is_alive() else "not alive"
        return f"ProcessInfo(name={self.name}, pid={self.pid}, status={status})"
    
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
        
    def _init_process_manager(self):
        """
        Initialize the ProcessManager instance.

        This method is called only once when the singleton instance is created.
        
        """
        self.processes: Dict[int, ProcessInfo] = {}
        self.reserved_processes: Dict[str, int] = {}
        self.main_pid = os.getpid()

        # track this process as the main process
        main_process = mp.current_process()
        self.processes[self.main_pid] = ProcessInfo(
            main_process,
            main_process.name,
            "main_process"
        )

        print(f"ProcessManager initialized in main process: {self.main_pid}")


    def create_process(self, target: FunctionInstance,
                       name: str,
                       reservation: Optional[str] = None,
                       daemon: bool = False,
                       init_results_callback: Union[Callable[Dict[str, Any]], FunctionInstance] = None,
                       comoponent_threads: Dict[str, Union[Callable, FunctionInstance]] = None,
                       time_to_finish_before_shutdown: float = 0.0,
                       time_to_cleanup_before_shutdown: float = 0.0) -> ProcessInfo:
        """
        Create a new process with automatic initialization.

        Args:
            target: The function to be run in the process's main thread
            name: Name for the process (optional)
            reservation: Reserve this process for a specific purpose
            daemon: Whether the process should be a daemon
            init_results_callback: Function to call with initialization results
            component_threads: Dictionary mapping component names to their thread functions

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
            
        if comoponent_threads is None:
            comoponent_threads = {}

        # create a pipe to receive initialization results and thread info
        parent_conn, child_conn = mp.Pipe()

        shutdown_info = ShutdownInfo(
            time_to_finish=time_to_finish_before_shutdown,
            time_to_cleanup=time_to_cleanup_before_shutdown
        )

        args = target.get_args()
        kwargs = target.get_kwargs()

        # wrap the target function to include initialization and component threads
        def wrapped_target(*args, **kwargs):
            # initialize process using registry
            init_registry = ProcessingInitRegistry()
            init_results = init_registry.execute_process_initializers()

            from suitkaise.int.processing.thread_mgr import ThreadManager
            thread_mgr = ThreadManager()

            component_thread_info = {}
            for comp_name, thread_func in comoponent_threads.items():
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

            # send initialization results and thread info to the child process
            child_conn.send({
                'init_results': init_results,
                'component_threads': component_thread_info
            })

            # run original with shutdown support
            if hasattr(target, 'can_shutdown'):
                with FunctionInstanceBuilder() as fib:
                    fib.add_function_instance(target)
                    fib.update_argument('shutdown_info', shutdown_info)
                    wrapped_target = fib.build()

                args = wrapped_target.get_args()
                kwargs = wrapped_target.get_kwargs()
                
                return wrapped_target(*args, **kwargs)
            
            else:
                # regular target function just gets monitored
                def shutdown_monitor():
                    # wait for shutdown signal
                    shutdown_info.shutdown_event.wait()

                    # once shutdown is signaled, set all flags
                    shutdown_info.state = ShutdownState.FINISHING
                    shutdown_info.finishing_start_time = sktime.now()
                    shutdown_info.finishing_event.set()
                    shutdown_info.state = ShutdownState.CLEANING
                    shutdown_info.cleaning_start_time = sktime.now()
                    shutdown_info.cleaning_event.set()
                    shutdown_info.state = ShutdownState.READY_TO_TERMINATE
                    shutdown_info.ready_to_terminate_event.set()


                # start the shutdown monitor
                monitor_thread = threading.Thread(
                    target=shutdown_monitor,
                    daemon=True,
                    name=f"{name}_shutdown_monitor"
                )
                monitor_thread.start()

            return target(*args, **kwargs)
        
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
            self.reserved_processes[reservation] = process.pid
            print(f"Process {process.pid} reserved for {reservation}")
        else:
            print(f"Process {process.pid} created without reservation")

        # receive initialization results from pipe
        if parent_conn.poll(5):
            init_results = parent_conn.recv()
            process_info.init_results = init_results

            # call the init results callback if provided
            if init_results_callback:
                if isinstance(init_results_callback, FunctionInstance):
                    with FunctionInstanceBuilder() as fib:
                        fib.add_function_instance(init_results_callback)
                        fib.update_argument('init_results', init_results)
                        with_results_callback = fib.build()

                    with_results_callback.execute()

                else:
                    init_results_callback(init_results)

        else:
            print(f"Process {process.pid} did not send initialization results")

        # close the pipe
        parent_conn.close()

        # return the process info
        return process_info


    def reserve_process(self, target: FunctionInstance,
                        reservation: str,
                        daemon: bool = False,
                        init_results_callback: Union[Callable[Dict[str, Any]], FunctionInstance] = None,
                        comoponent_threads: Dict[str, Union[Callable, FunctionInstance]] = None
                        ) -> ProcessInfo:
        """
        Create a reserved process for a specific purpose.

        This is a convenience method for create_process with a reservation.
        
        """
        if reservation in self.reserved_processes:
            raise ValueError(f"Process already reserved for {reservation}")
        
        # create the process
        return self.create_process(
            target=target,
            name=reservation,
            reservation=reservation,
            daemon=daemon,
            init_results_callback=init_results_callback,
            comoponent_threads=comoponent_threads
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
        
        # Step 2: Wait for the process to finish its normal operations
        finishing_timeout = custom_time_to_finish or shutdown_info.time_to_finish
        print(f"Waiting up to {finishing_timeout} seconds for process to finish normal operations...")
        
        operations_finished = shutdown_info.finished_event.wait(timeout=finishing_timeout)
        if not operations_finished:
            print(f"Process {process_info.name} did not finish operations within {finishing_timeout} seconds.")
            print("Forcing termination...")
            return self._force_terminate_process(process_info)
        
        print(f"Process {process_info.name} has finished normal operations.")
        
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
        
        # Step 4: Terminate the process
        try:
            process_info.process.terminate()
            
            # Wait a moment for the process to terminate
            process_info.process.join(1.0)
            
            # If it's still alive, use SIGKILL
            if process_info.process.is_alive():
                print(f"Process {process_info.name} did not terminate normally, sending SIGKILL...")
                os.kill(process_info.pid, 9)
            
            shutdown_info.state = ShutdownState.TERMINATED
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
            process_info.shutdown_info.state = ShutdownState.READY_TO_TERMINATE

            # terminate the process
            process_info.process.terminate()
            process_info.process.join(1.0)

            # check if the process is still alive and SIGKILL if needed
            if process_info.process.is_alive():
                print(f"Process {process_info.name} did not terminate, "
                      "sending SIGKILL...")
                os.kill(process_info.pid, 9)

            process_info.shutdown_info.state = ShutdownState.TERMINATED
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



    # decorator
    def can_shutdown(func: Union[Callable, FunctionInstance]
                     ) -> Callable:
        """
        Decorator to mark a function as capable of handling shutdown signals.

        Functions marked with this decorator will receive a shutdown_info
        when run as a process target. The function being decorated should use
        this to coordinate a clean shutdown.

        Example:

        @can_shutdown
        def my_process(arg1, shutdown_info=None, arg2):
            try:
                while not finishing_up:
                    if shutdown_info.shutdown_event.is_set(): # parent requested shutdown
                        finishing_up = True
                        
                    # do work
                    do_work(arg1, arg2)

                
                # on exit, set the finished_event
                shutdown_info.finished_event.set()

                # clean up and transfer resources if needed
                clean_up_resources()

                # signal ready to terminate
                shutdown_info.ready_to_terminate_event.set()

            except Exception as e:
                print(f"Error in process {shutdown_info.name}: {e}")

        """
        if isinstance(func, FunctionInstance):
            func.func.__can_shutdown__ = True
        else:
            func.__can_shutdown__ = True

        return func
        




        