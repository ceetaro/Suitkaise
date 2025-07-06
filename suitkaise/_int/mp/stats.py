"""
Xprocess Internal Cross-processing Engine - Statistics Tracking

This module contains the statistics tracking class for process performance
monitoring and error reporting.
"""

import time
import traceback
from typing import Dict, Any, Optional, List


class ProcessStats:
    """Statistics tracking for a process."""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_loops: int = 0
        self.loop_times: List[float] = []
        self.errors: List[Dict[str, Any]] = []
        self.restart_count: int = 0
        self.timeout_count: int = 0         # New: Track loop timeouts
        self.heartbeat_misses: int = 0      # New: Track heartbeat failures
        self.resource_peaks: Dict[str, Any] = {}  # New: Track resource usage peaks
        
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