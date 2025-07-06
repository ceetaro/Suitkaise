"""
Xprocess Internal Cross-processing Engine - Process Pool

This module provides process pool functionality for batch task execution
with worker processes, supporting both asynchronous and parallel execution modes.
"""

import multiprocessing
import threading
import time
import os
from typing import Dict, List, Optional, Any, Type, Callable, Union
from dataclasses import dataclass
from enum import Enum

from .process import _Process, _FunctionProcess, PStatus
from .config import _PConfig, _QPConfig
from .pdata import _PData, ProcessResultError
from .runner import _ProcessRunner
from suitkaise._int.core.time_ops import _get_current_time, _elapsed_time
from suitkaise._int.core.format_ops import _create_debug_message


class PoolMode(Enum):
    """Process pool execution modes."""
    ASYNC = "async"      # Processes start as workers become available
    PARALLEL = "parallel"  # Processes start and end in synchronized groups


class PoolTaskError(Exception):
    """
    Exception raised when process pool tasks fail.
    
    This exception provides detailed information about failed tasks including
    which worker failed, the task information, and the underlying errors.
    """
    
    def __init__(self, failed_tasks: List[Dict[str, Any]], message: str = None):
        self.failed_tasks = failed_tasks
        self.task_count = len(failed_tasks)
        
        if message is None:
            if self.task_count == 1:
                task = failed_tasks[0]
                message = (f"Pool task failed - Key: '{task['key']}', "
                          f"Class: {task['pclass_name']}, Worker: {task['worker_number']}, "
                          f"Error: {task['error']}")
            else:
                message = f"Pool execution failed - {self.task_count} tasks had errors"
        
        self.message = message
        super().__init__(message)


@dataclass
class _PTask:
    """
    Internal task definition for process pools.
    
    Represents a single task to be executed by a worker process,
    containing the process class, configuration, and metadata.
    """
    key: str                        # Unique task identifier
    process_class: Type[_Process]   # Process class to instantiate
    config: _PConfig = None        # Process configuration (defaults to _PConfig())
    process_name: str = None       # Name for process instance (defaults to class name)
    
    def __post_init__(self):
        """Set defaults for config and process name if not provided."""
        if self.config is None:
            self.config = _PConfig()
        if self.process_name is None:
            self.process_name = self.process_class.__name__


@dataclass 
class _PTaskResult:
    """
    Internal result container for completed pool tasks.
    
    Contains all information about a completed task including results,
    worker information, and execution metadata.
    """
    key: str                    # Task key
    pclass_name: str           # Process class name  
    worker_pid: int            # Worker process PID
    worker_number: int         # Worker number (1-N)
    task_num: int              # Task submission number
    result: Any                # Task result or None
    error: Optional[str]       # Error message if task failed
    pdata: _PData             # Full PData instance
    
    @property
    def success(self) -> bool:
        """Check if task completed successfully."""
        return self.error is None
        
    @property
    def failed(self) -> bool:
        """Check if task failed."""
        return self.error is not None


class ProcessPool:
    """
    Process pool for batch execution of tasks with worker processes.
    
    Provides both context manager and one-shot execution modes with support
    for asynchronous and parallel execution patterns.
    
    Features:
    - Dynamic worker scaling based on task count
    - Asynchronous and parallel execution modes  
    - Comprehensive error handling and reporting
    - Function and Process class task support
    - Automatic cleanup and resource management
    """
    
    def __init__(self, size: int = 8, mode: PoolMode = PoolMode.ASYNC):
        """
        Initialize process pool.
        
        Args:
            size: Maximum number of worker processes
            mode: Execution mode (ASYNC or PARALLEL)
        """
        # Check depth restrictions
        current_depth = int(os.environ.get('XPROCESS_DEPTH', '0'))
        if current_depth >= 2:
            raise RuntimeError(
                f"ProcessPool cannot be created at depth {current_depth}. "
                f"Maximum depth for ProcessPool is 1."
            )
        
        self.size = size
        self.mode = mode
        self._active = False
        self._tasks_submitted = 0
        self._tasks_completed = 0
        
        # Worker management
        self._workers: Dict[int, Dict[str, Any]] = {}  # worker_number -> worker_info
        self._available_workers: List[int] = []
        self._task_queue: List[_PTask] = []
        self._results: Dict[str, _PTaskResult] = {}
        self._parallel_batch: List[_PTask] = []
        
        # Threading for coordination
        self._lock = threading.RLock()
        self._coordinator_thread = None
        self._shutdown_event = threading.Event()
        
        # Multiprocessing manager
        self._manager = multiprocessing.Manager()
        
        print(_create_debug_message(
            f"ProcessPool initialized: size={size}, mode={mode.value}"
        ))
    
    def __enter__(self):
        """Context manager entry - start the pool."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - shutdown the pool."""
        self.shutdown()
        
    def start(self):
        """Start the process pool and coordinator thread."""
        if self._active:
            return
            
        self._active = True
        
        # Start coordinator thread
        self._coordinator_thread = threading.Thread(
            target=self._coordinate_workers,
            name="ProcessPool-Coordinator",
            daemon=True
        )
        self._coordinator_thread.start()
        
        print(_create_debug_message("ProcessPool started"))
        
    def submit(self, task: Union[_PTask, str], process_class: Type[_Process] = None, 
               config: _PConfig = None, process_name: str = None):
        """
        Submit a task to the pool.
        
        Args:
            task: Either a PTask instance or a task key
            process_class: Process class (required if task is a key)
            config: Process configuration (defaults to _PConfig() if None)
            process_name: Process name (optional, defaults to class name)
        """
        if not self._active:
            raise RuntimeError("ProcessPool is not active. Use start() or context manager.")
            
        # Handle both PTask and individual parameters
        if isinstance(task, _PTask):
            ptask = task
        elif isinstance(task, str):
            if process_class is None:
                raise ValueError("process_class required when submitting by key")
            
            # Default config if None provided
            if config is None:
                config = _PConfig()
                
            ptask = _PTask(
                key=task,
                process_class=process_class,
                config=config,
                process_name=process_name
            )
        else:
            raise ValueError("task must be a PTask instance or string key")
            
        with self._lock:
            if ptask.key in self._results:
                raise ValueError(f"Task with key '{ptask.key}' already submitted")
                
            self._tasks_submitted += 1
            
            if self.mode == PoolMode.ASYNC:
                self._task_queue.append(ptask)
                print(_create_debug_message(f"Submitted async task: {ptask.key}"))
            else:  # PARALLEL
                self._parallel_batch.append(ptask)
                print(_create_debug_message(f"Added task to parallel batch: {ptask.key}"))
                
    def submit_function(self, key: str, func: Callable, args: tuple = None, 
                       kwargs: dict = None, config: _QPConfig = None):
        """
        Submit a function to be executed as a task.
        
        Args:
            key: Unique task identifier
            func: Function to execute
            args: Function arguments
            kwargs: Function keyword arguments  
            config: Quick process configuration
        """
        if config is None:
            config = _QPConfig()
            
        # Convert to full PConfig
        process_config = config.to_process_config()
        
        # Create a dynamic process class for the function
        class FunctionProcessWrapper(_Process):
            def __init__(self, process_name: str):
                super().__init__(process_name, num_loops=1)
                self._func = func
                self._args = args or ()
                self._kwargs = kwargs or {}
                self._function_result = None
                
            def __loop__(self):
                self._function_result = self._func(*self._args, **self._kwargs)
                
            def __result__(self):
                return self._function_result
                
        # Submit as regular task
        function_name = getattr(func, '__name__', 'anonymous_function')
        self.submit(key, FunctionProcessWrapper, process_config, function_name)
        
    def submit_multiple(self, tasks: List[_PTask]):
        """
        Submit multiple tasks at once.
        
        Args:
            tasks: List of PTask instances to submit
        """
        for task in tasks:
            self.submit(task)
            
        # If in parallel mode, flush the batch
        if self.mode == PoolMode.PARALLEL:
            self._flush_parallel_batch()
            
    def set_parallel(self, size: Optional[int] = None):
        """
        Switch to parallel execution mode.
        
        Args:
            size: Override parallel batch size (uses pool size if None)
        """
        with self._lock:
            self.mode = PoolMode.PARALLEL
            if size is not None:
                # Note: This changes the batch size, not the pool size
                # Pool size remains the same for worker management
                self._parallel_size = min(size, self.size)
            else:
                self._parallel_size = self.size
                
            print(_create_debug_message(f"Switched to parallel mode (batch size: {self._parallel_size})"))
            
    def set_async(self):
        """Switch to asynchronous execution mode."""
        with self._lock:
            # Process any pending parallel batch first
            if self._parallel_batch:
                self._flush_parallel_batch()
                
            self.mode = PoolMode.ASYNC
            print(_create_debug_message("Switched to async mode"))
            
    def get_result(self, key: str, timeout: Optional[float] = None) -> _PTaskResult:
        """
        Get result for a specific task.
        
        Args:
            key: Task key
            timeout: Maximum time to wait for result
            
        Returns:
            PTaskResult instance
            
        Raises:
            PoolTaskError: If task failed
            TimeoutError: If timeout exceeded
        """
        start_time = _get_current_time()
        
        while True:
            with self._lock:
                if key in self._results:
                    result = self._results[key]
                    if result.failed:
                        raise PoolTaskError([{
                            'key': result.key,
                            'pclass_name': result.pclass_name,
                            'worker_number': result.worker_number,
                            'error': result.error
                        }])
                    return result
                    
            # Check timeout
            if timeout is not None:
                elapsed = _elapsed_time(start_time)
                if elapsed >= timeout:
                    raise TimeoutError(f"Timeout waiting for task '{key}' result")
                    
            time.sleep(0.1)  # Small delay before checking again
            
    def get_all_results(self, timeout: Optional[float] = None) -> List[_PTaskResult]:
        """
        Get results for all submitted tasks.
        
        Args:
            timeout: Maximum time to wait for all results
            
        Returns:
            List of PTaskResult instances
            
        Raises:
            PoolTaskError: If any tasks failed
            TimeoutError: If timeout exceeded
        """
        start_time = _get_current_time()
        
        while True:
            with self._lock:
                if self._tasks_completed >= self._tasks_submitted:
                    results = list(self._results.values())
                    
                    # Check for failures
                    failed_tasks = []
                    for result in results:
                        if result.failed:
                            failed_tasks.append({
                                'key': result.key,
                                'pclass_name': result.pclass_name,
                                'worker_number': result.worker_number,
                                'error': result.error
                            })
                            
                    if failed_tasks:
                        raise PoolTaskError(failed_tasks)
                        
                    return results
                    
            # Check timeout
            if timeout is not None:
                elapsed = _elapsed_time(start_time)
                if elapsed >= timeout:
                    raise TimeoutError("Timeout waiting for all task results")
                    
            time.sleep(0.1)
            
    def shutdown(self, timeout: float = 10.0):
        """
        Shutdown the process pool.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown
        """
        if not self._active:
            return
            
        print(_create_debug_message("Shutting down ProcessPool..."))
        
        # Signal shutdown
        self._shutdown_event.set()
        self._active = False
        
        # Wait for coordinator thread
        if self._coordinator_thread and self._coordinator_thread.is_alive():
            self._coordinator_thread.join(timeout=5.0)
            
        # Terminate any remaining workers
        with self._lock:
            for worker_info in self._workers.values():
                mp_process = worker_info['mp_process']
                if mp_process.is_alive():
                    mp_process.terminate()
                    mp_process.join(timeout=2.0)
                    
        print(_create_debug_message("ProcessPool shutdown complete"))
        
    @classmethod
    def submit_all(cls, tasks: List[_PTask], size: int = None, 
                   parallel: bool = False, timeout: float = None) -> List[_PTaskResult]:
        """
        One-shot method to submit and execute all tasks.
        
        Args:
            tasks: List of tasks to execute
            size: Pool size (defaults to min(8, len(tasks)))
            parallel: Use parallel mode instead of async
            timeout: Maximum time to wait for completion
            
        Returns:
            List of PTaskResult instances
            
        Raises:
            PoolTaskError: If any tasks failed
        """
        if size is None:
            size = min(8, len(tasks))
            
        mode = PoolMode.PARALLEL if parallel else PoolMode.ASYNC
        
        with cls(size=size, mode=mode) as pool:
            pool.submit_multiple(tasks)
            return pool.get_all_results(timeout=timeout)
            
    # =============================================================================
    # INTERNAL COORDINATION METHODS
    # =============================================================================
    
    def _coordinate_workers(self):
        """Main coordinator thread that manages worker allocation and task distribution."""
        while not self._shutdown_event.is_set():
            try:
                with self._lock:
                    # Handle parallel batch processing
                    if self.mode == PoolMode.PARALLEL and self._parallel_batch:
                        if len(self._parallel_batch) >= getattr(self, '_parallel_size', self.size):
                            self._flush_parallel_batch()
                            
                    # Handle async task processing
                    elif self.mode == PoolMode.ASYNC and self._task_queue:
                        self._process_async_tasks()
                        
                    # Clean up completed workers
                    self._cleanup_completed_workers()
                    
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                print(_create_debug_message(f"Error in pool coordinator: {e}"))
                time.sleep(1.0)
                
    def _flush_parallel_batch(self):
        """Process the current parallel batch."""
        if not self._parallel_batch:
            return
            
        batch_size = getattr(self, '_parallel_size', self.size)
        current_batch = self._parallel_batch[:batch_size]
        self._parallel_batch = self._parallel_batch[batch_size:]
        
        print(_create_debug_message(f"Processing parallel batch of {len(current_batch)} tasks"))
        
        # Wait for enough workers to be available
        needed_workers = min(len(current_batch), self.size)
        while len(self._available_workers) < needed_workers:
            if len(self._workers) < needed_workers:
                self._create_worker()
            time.sleep(0.1)
            
        # Assign all tasks in the batch
        for task in current_batch:
            if self._available_workers:
                worker_number = self._available_workers.pop(0)
                self._assign_task_to_worker(worker_number, task)
                
        # Wait for all tasks in batch to complete before next batch
        batch_keys = [task.key for task in current_batch]
        while not all(key in self._results for key in batch_keys):
            if self._shutdown_event.is_set():
                break
            time.sleep(0.1)
            
    def _process_async_tasks(self):
        """Process tasks asynchronously as workers become available."""
        while self._task_queue and self._available_workers:
            task = self._task_queue.pop(0)
            worker_number = self._available_workers.pop(0)
            self._assign_task_to_worker(worker_number, task)
            
        # Create workers if needed and we have tasks
        if self._task_queue and len(self._workers) < self.size:
            self._create_worker()
            
    def _create_worker(self) -> int:
        """Create a new worker process."""
        worker_number = len(self._workers) + 1
        
        worker_info = {
            'worker_number': worker_number,
            'mp_process': None,
            'current_task': None,
            'created_at': _get_current_time(),
            'tasks_completed': 0
        }
        
        self._workers[worker_number] = worker_info
        self._available_workers.append(worker_number)
        
        print(_create_debug_message(f"Created worker {worker_number}"))
        return worker_number
        
    def _assign_task_to_worker(self, worker_number: int, task: _PTask):
        """Assign a task to a specific worker."""
        worker_info = self._workers[worker_number]
        
        # Create process instance
        process_instance = task.process_class(task.process_name or task.process_class.__name__)
        process_instance._set_process_key(task.key)
        
        # Create PData instance
        pdata_instance = _PData(
            pkey=task.key,
            pclass=process_instance.pclass,
            pid=None,
            num_loops=process_instance.num_loops,
            completed_loops=0
        )
        process_instance._set_pdata_instance(pdata_instance)
        
        # Create result queue
        result_queue = multiprocessing.Queue()
        
        # Initialize shared state
        process_instance._initialize_shared_state(self._manager, result_queue)
        
        # Create runner
        runner = _ProcessRunner(process_instance, task.config, result_queue)
        
        # Create multiprocessing.Process
        mp_process = multiprocessing.Process(
            target=runner.run,
            name=f"PoolWorker-{worker_number}-{task.key}"
        )
        
        # Update worker info
        worker_info.update({
            'mp_process': mp_process,
            'current_task': task,
            'process_instance': process_instance,
            'pdata_instance': pdata_instance,
            'result_queue': result_queue,
            'task_start_time': _get_current_time()
        })
        
        # Start the process
        mp_process.start()
        
        print(_create_debug_message(f"Assigned task {task.key} to worker {worker_number}"))
        
    def _cleanup_completed_workers(self):
        """Check for completed workers and collect results."""
        completed_workers = []
        
        for worker_number, worker_info in self._workers.items():
            mp_process = worker_info.get('mp_process')
            if mp_process and not mp_process.is_alive():
                completed_workers.append(worker_number)
                
        for worker_number in completed_workers:
            self._collect_worker_result(worker_number)
            
    def _collect_worker_result(self, worker_number: int):
        """Collect result from a completed worker."""
        worker_info = self._workers[worker_number]
        task = worker_info['current_task']
        result_queue = worker_info['result_queue']
        mp_process = worker_info['mp_process']
        pdata_instance = worker_info['pdata_instance']
        
        # Get result from queue
        result_data = None
        error_msg = None
        
        try:
            result_data = result_queue.get_nowait()
            
            if isinstance(result_data, tuple) and len(result_data) == 2:
                status, data = result_data
                
                if status == 'success':
                    if data is not None:
                        try:
                            from suitkaise._int.serialization.cerial_core import deserialize
                            result = deserialize(data)
                            pdata_instance._set_result(result)
                        except Exception as e:
                            error_msg = f"Deserialization error: {e}"
                            pdata_instance._set_error(error_msg)
                    else:
                        pdata_instance._set_result(None)
                else:
                    error_msg = f"{status}: {data}"
                    pdata_instance._set_error(error_msg)
            else:
                # Legacy format
                pdata_instance._set_result(result_data)
                
        except Exception as e:
            error_msg = f"Failed to get result: {e}"
            pdata_instance._set_error(error_msg)
            
        # Create task result
        task_result = _PTaskResult(
            key=task.key,
            pclass_name=task.process_class.__name__,
            worker_pid=mp_process.pid,
            worker_number=worker_number,
            task_num=self._tasks_submitted - len(self._task_queue) - len(self._parallel_batch),
            result=pdata_instance.result if not pdata_instance.has_error else None,
            error=error_msg,
            pdata=pdata_instance
        )
        
        # Store result
        self._results[task.key] = task_result
        self._tasks_completed += 1
        
        # Update worker info
        worker_info['current_task'] = None
        worker_info['tasks_completed'] += 1
        
        # Make worker available again
        if worker_number not in self._available_workers:
            self._available_workers.append(worker_number)
            
        status_msg = "completed" if error_msg is None else f"failed ({error_msg})"
        print(_create_debug_message(f"Task {task.key} {status_msg} on worker {worker_number}"))