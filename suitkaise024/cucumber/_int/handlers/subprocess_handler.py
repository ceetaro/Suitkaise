"""
Handler for subprocess objects.

Subprocess objects (Popen) represent running or completed processes.
We serialize the process configuration and optionally the output.
"""

import subprocess
import sys
from typing import Any, Dict, Optional
from .base_class import Handler


class SubprocessSerializationError(Exception):
    """Raised when subprocess serialization fails."""
    pass


class PopenHandler(Handler):
    """
    Serializes subprocess.Popen objects.
    
    Strategy:
    - For running processes: serialize configuration only (can't transfer PID)
    - For completed processes: serialize configuration + return code + output
    - Capture stdout/stderr if they were set to PIPE
    
    Important: Process IDs (PIDs) don't transfer across processes/machines.
    A serialized Popen object will be reconstructed as a reference to the
    original command, but the actual process won't be running in the target.
    
    For long-running processes, users should:
    1. Start the process in the target environment
    2. Use process management tools (systemd, supervisord, etc.)
    3. Serialize only the configuration, not the running process
    """
    
    type_name = "subprocess_popen"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a subprocess.Popen instance."""
        return isinstance(obj, subprocess.Popen)
    
    def extract_state(self, obj: subprocess.Popen) -> Dict[str, Any]:
        """
        Extract subprocess state.
        
        What we capture:
        - args: Command and arguments
        - returncode: Exit code (if process has finished)
        - pid: Process ID (for reference only - won't work in target)
        - stdout: Output if captured
        - stderr: Error output if captured
        - stdin: Input data (if any)
        
        Note: We don't transfer the actual running process, just its configuration
        and results.
        """
        # Get command args
        args = obj.args
        
        # Get return code (None if still running)
        returncode = obj.returncode
        
        # Get PID (for reference, won't be valid in target process)
        pid = obj.pid
        
        # Try to get output if it was captured
        stdout_data = None
        stderr_data = None
        
        # If process has finished and stdout was PIPE, try to read it
        if returncode is not None:
            try:
                if obj.stdout:
                    # Try to read remaining data
                    remaining = obj.stdout.read()
                    if remaining:
                        stdout_data = remaining
            except (OSError, IOError, ValueError) as e:
                # Stream closed or not readable - that's okay, no output to capture
                pass
            except Exception as e:
                # Unexpected error reading stdout
                import warnings
                warnings.warn(f"Failed to read subprocess stdout: {e}")
            
            try:
                if obj.stderr:
                    remaining = obj.stderr.read()
                    if remaining:
                        stderr_data = remaining
            except (OSError, IOError, ValueError):
                # Stream closed or not readable - that's okay
                pass
            except Exception as e:
                # Unexpected error reading stderr
                import warnings
                warnings.warn(f"Failed to read subprocess stderr: {e}")
        
        # Get process state
        poll_result = obj.poll()  # Check if process is done
        
        return {
            "args": args,  # Command and arguments
            "returncode": returncode,
            "pid": pid,  # Original PID (won't be valid in target)
            "poll_result": poll_result,
            "stdout_data": stdout_data,
            "stderr_data": stderr_data,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> Any:
        """
        Reconstruct subprocess.Popen object.
        
        Important: We DON'T actually start a new process.
        We create a "mock" Popen object that contains the original
        command and results, but doesn't represent a running process.
        
        If users need the process to actually run, they should:
        1. Detect that it's a deserialized Popen
        2. Start it again with subprocess.run() or Popen()
        """
        # Create a mock Popen-like object that holds the state
        # but doesn't represent a running process
        
        class DeserializedPopen:
            """
            A deserialized Popen object.
            
            This is NOT a running process. It contains the original
            command configuration and results (if the process had finished).
            
            To actually run the command in the target environment,
            use subprocess.run() or subprocess.Popen() with the args attribute.
            """
            def __init__(self, state_dict):
                self.args = state_dict["args"]
                self.returncode = state_dict["returncode"]
                self.original_pid = state_dict["pid"]
                self.poll_result = state_dict["poll_result"]
                self.stdout_data = state_dict["stdout_data"]
                self.stderr_data = state_dict["stderr_data"]
                
                # Mark as deserialized
                self._deserialized = True
                self._serialization_note = (
                    "This is a deserialized subprocess.Popen object. "
                    "It does NOT represent a running process. "
                    "To run the command, use subprocess.run(self.args)"
                )
            
            def poll(self):
                """Return the cached poll result."""
                return self.poll_result
            
            def wait(self, timeout=None):
                """Fake wait - process is not actually running."""
                return self.returncode
            
            def communicate(self, input=None, timeout=None):
                """Return cached output."""
                return (self.stdout_data, self.stderr_data)
            
            def __repr__(self):
                return (
                    f"<DeserializedPopen args={self.args!r} "
                    f"returncode={self.returncode} "
                    f"original_pid={self.original_pid}>"
                )
        
        return DeserializedPopen(state)


class CompletedProcessHandler(Handler):
    """
    Serializes subprocess.CompletedProcess objects.
    
    CompletedProcess is returned by subprocess.run() and contains
    the results of a completed process.
    """
    
    type_name = "subprocess_completed_process"
    
    def can_handle(self, obj: Any) -> bool:
        """Check if object is a CompletedProcess."""
        return isinstance(obj, subprocess.CompletedProcess)
    
    def extract_state(self, obj: subprocess.CompletedProcess) -> Dict[str, Any]:
        """
        Extract CompletedProcess state.
        
        CompletedProcess has:
        - args: Command that was run
        - returncode: Exit code
        - stdout: Output (if captured)
        - stderr: Error output (if captured)
        """
        return {
            "args": obj.args,
            "returncode": obj.returncode,
            "stdout": obj.stdout,
            "stderr": obj.stderr,
        }
    
    def reconstruct(self, state: Dict[str, Any]) -> subprocess.CompletedProcess:
        """
        Reconstruct CompletedProcess.
        
        This is straightforward since CompletedProcess is just a data container.
        """
        return subprocess.CompletedProcess(
            args=state["args"],
            returncode=state["returncode"],
            stdout=state["stdout"],
            stderr=state["stderr"]
        )

