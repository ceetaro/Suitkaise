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

# suitkaise/int/processing/thread_mgr.py

"""
Thread management for Suitkaise.

This module implements a thread pool and management system optimized for
cooperative thread cancellation and lifecycle management.

"""

import threading
import queue
import weakref
import traceback
from typing import Callable, Dict, Optional, List, Any, Tuple, Union, Set
from enum import Enum, auto

import suitkaise_app.int.utils.time.sktime as sktime
from suitkaise_app.int.processing.init_registry import ProcessingInitRegistry
from suitkaise_app.int.processing.reservations import ReservedThreads
from suitkaise_app.int.utils.fib.fib import FunctionInstance, FunctionInstanceBuilder

class ThreadCancellationError(Exception):
    """Custom exception for thread cancellation."""
    pass

class ThreadState(Enum):
    """Enumeration for thread states."""
    IDLE = auto() # Thread is idle and waiting for work
    RUNNING = auto() # Thread is currently running normally
    CANCELLING = auto() # Thread is being cancelled
    STOPPING = auto() # Thread is stopping
    CANCELLED = auto() # Thread has been cancelled
    COMPLETED = auto() # Thread has completed its work (stopped)
    ERROR = auto() # Thread ended with an error

class CancellationToken:
    """
    Token that can be used to signal cancellation to a thread.

    This is the primary mechanism for cancelling threads safely.
    
    """

    def __init__(self):
        self._cancelled_event = threading.Event()
        self._cancelled_time = None

    def cancel(self):
        """Signal cancellation to the thread."""
        self._cancelled_time = sktime.now()
        self._cancelled_event.set()

    @property
    def is_cancelled(self):
        """Check if the cancellation has been signaled."""
        return self._cancelled_event.is_set()
    
    def check_cancelled(self):
        """
        Check if cancellation has been requested.

        Raises:
            ThreadCancellationError: If cancellation has been requested.

        """
        if self.is_cancelled:
            raise ThreadCancellationError("Thread has been cancelled.")
        
    def wait(self, timeout: Optional[float] = None):
        """
        Wait for the cancellation signal.

        Args:
            timeout (float, optional): Timeout in seconds. If None, wait indefinitely.

        Returns:
            bool: True if cancelled, False if not.

        """
        return self._cancelled_event.wait(timeout)
    
class ThreadInfo:
    """Container for thread related information."""

    def __init__(self, thread: threading.Thread, 
                 name: str,
                 reservation: Optional[str] = None) -> None:
        """
        Initialize ThreadInfo.

        Args:
            thread (threading.Thread): The thread object.
            name (str): The name of the thread.
            reservation (Optional[str]): Optional reservation name.
        
        """
        self.thread = thread
        self.thread_id = thread.ident if hasattr(thread, 'ident') else None
        self.name = name
        self.reservation = reservation
        self.created_at = sktime.now()
        self.state = ThreadState.RUNNING
        self.last_state_change = sktime.now()

        # cancellation and coordination
        self.cancellation_token = CancellationToken()
        self.completion_event = threading.Event()

        # results and errors
        self.init_results = {}
        self.result = None
        self.error = None
        self.error_traceback = None
        self.execution_completed = False # flag for if thread function has completed/returned

    def __repr__(self):
        """Return a string representation of ThreadInfo."""
        return f"ThreadInfo(name={self.name}, id={self.thread_id}, state={self.state.name})"
    
    def update_state(self, new_state: ThreadState):
        """
        Update the state of the thread.

        Args:
            new_state (ThreadState): The new state to set.

        """
        self.state = new_state
        self.last_state_change = sktime.now()

    def is_alive(self) -> bool:
        """Check if the thread is alive."""
        return self.thread.is_alive() if self.thread else False
    

    def join(self, timeout: Optional[float] = None):
        """
        Wait for the thread to finish.

        Args:
            timeout (Optional[float]): Timeout in seconds.

        """
        if not self.thread:
            return True
        
        self.update_state(ThreadState.STOPPING)
        self.thread.join(timeout)

        if not self.thread.is_alive():
            if self.error:
                self.update_state(ThreadState.ERROR)
            else:
                self.update_state(ThreadState.COMPLETED)
            return True
        return False
    
class ThreadManager:
    """
    Manages threads in each process.

    This class creates a thread pool and manages the created threads.
    Aims for cooperative cancellation and clean lifecycle management.
    
    """
    _thread_mgr_instance
    
    
        
    
        

            





