"""
Configuration dataclasses for Skprocess.

Created automatically by Skprocess._setup() before user's __init__ runs.
Users can override defaults by assigning to self.process_config.* in their __init__.
"""

from dataclasses import dataclass, field


@dataclass
class TimeoutConfig:
    """
    Timeout settings for each lifecycle section.
    
    All default to None (no timeout). Set a value to enable timeout for that section.
    """
    prerun: float | None = None
    run: float | None = None
    postrun: float | None = None
    onfinish: float | None = None
    result: float | None = None
    error: float | None = None


@dataclass
class ProcessConfig:
    """
    Configuration for a Skprocess instance.
    
    Attributes:
        runs: Number of run iterations before auto-stopping.
              None = run indefinitely until stop() is called.
        join_in: Maximum total runtime in seconds before auto-stopping.
                 None = no time limit.
        lives: Number of times to retry after a crash before giving up.
               1 = no retries (fail on first error).
        timeouts: Timeout settings for each lifecycle section.
    """
    runs: int | None = None
    join_in: float | None = None
    lives: int = 1
    timeouts: TimeoutConfig = field(default_factory=TimeoutConfig)
