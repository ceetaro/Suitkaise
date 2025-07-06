"""
Xprocess Internal Cross-processing Engine - Configuration Classes

This module contains configuration classes for process execution settings.
These are internal classes that will be wrapped by external API classes.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class _PConfig:
    """Internal configuration for process execution."""
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
        
    def copy_with_overrides(self, **overrides) -> '_PConfig':
        """Create a copy of this config with specific overrides."""
        import copy
        new_config = copy.deepcopy(self)
        for key, value in overrides.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
        return new_config


@dataclass
class _QPConfig:
    """Internal simplified configuration for quick one-shot function processes."""
    join_in: Optional[float] = 30.0      # Default 30s timeout (shorter than _PConfig)
    crash_restart: bool = False          # Keep restart capability
    max_restarts: int = 1               # Lower default for quick processes
    heartbeat_interval: float = 5.0     # Heartbeat check interval
    resource_monitoring: bool = False   # Enable resource monitoring
    
    # Function-specific timeout (applies to the single function execution)
    function_timeout: float = 25.0      # Timeout for the function execution (5s buffer from join_in)
    
    def to_process_config(self) -> _PConfig:
        """Convert to full _PConfig for internal use."""
        return _PConfig(
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