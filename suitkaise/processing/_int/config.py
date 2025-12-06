"""
Configuration dataclasses for Process.

Created automatically by Process._setup() before user's __init__ runs.
Users can override defaults by assigning to self.config.* in their __init__.
"""

from dataclasses import dataclass, field


@dataclass
class TimeoutConfig:
    """
    Timeout settings for each lifecycle section.
    
    Set to None to disable timeout for that section.
    """
    preloop: float | None = 30.0
    loop: float | None = 300.0
    postloop: float | None = 60.0
    onfinish: float | None = 60.0


@dataclass
class ProcessConfig:
    """
    Configuration for a Process instance.
    
    Attributes:
        num_loops: Number of loop iterations before auto-stopping.
                   None = run indefinitely until stop() is called.
        join_in: Maximum total runtime in seconds before auto-stopping.
                 None = no time limit.
        lives: Number of times to retry after a crash before giving up.
               1 = no retries (fail on first error).
        timeouts: Timeout settings for each lifecycle section.
    """
    num_loops: int | None = None
    join_in: float | None = None
    lives: int = 1
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
