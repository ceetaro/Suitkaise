"""
ProcessTimers container for timing lifecycle sections.

Timers are automatically created for any lifecycle method the user defines.
Access via process.__run__.timer, process.__prerun__.timer, etc.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from suitkaise.timing import Timer


class ProcessTimers:
    """
    Container for timing lifecycle sections of a Process.
    
    Automatically created when Process starts. Each section timer is populated
    when that section runs.
    
    The full_run timer aggregates the times from prerun, run, and postrun
    after each complete iteration.
    """
    
    def __init__(self):
        # Import here to avoid circular imports
        from suitkaise.timing import Timer
        
        # Individual section timers
        self.prerun: Timer | None = None
        self.run: Timer | None = None
        self.postrun: Timer | None = None
        self.onfinish: Timer | None = None
        self.result: Timer | None = None
        self.error: Timer | None = None
        
        # Aggregate timer for full iteration (prerun + run + postrun)
        self.full_run: Timer = Timer()
    
    def _update_full_run(self) -> None:
        """
        Update full_run timer by summing most recent times from section timers.
        
        Called by the engine after each complete run iteration.
        Only includes timers that exist and have recorded times.
        """
        total = 0.0
        
        for timer in [self.prerun, self.run, self.postrun]:
            if timer is not None and timer.num_times > 0:
                most_recent = timer.most_recent
                if most_recent is not None:
                    total += most_recent
        
        if total > 0:
            self.full_run.add_time(total)
    
    def _ensure_timer(self, section: str) -> "Timer":
        """
        Get or create a timer for the specified section.
        
        Args:
            section: One of 'prerun', 'run', 'postrun', 'onfinish', 'result', 'error'
        
        Returns:
            The Timer for that section
        """
        from suitkaise.timing import Timer
        
        current = getattr(self, section, None)
        if current is None:
            new_timer = Timer()
            setattr(self, section, new_timer)
            return new_timer
        return current
    
    def _reset(self) -> None:
        """
        Reset all timers to fresh state.
        
        Called when a process crashes and restarts with a life.
        """
        from suitkaise.timing import Timer
        
        self.prerun = None
        self.run = None
        self.postrun = None
        self.onfinish = None
        self.result = None
        self.error = None
        self.full_run = Timer()
