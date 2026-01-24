"""
ProcessTimers container for timing lifecycle sections.

Timers are automatically created for any lifecycle method the user defines.
Access via process.__run__.timer, process.__prerun__.timer, etc.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from suitkaise.timing import Sktimer


class ProcessTimers:
    """
    Container for timing lifecycle sections of a Skprocess.
    
    Automatically created when Skprocess starts. Each section timer is populated
    when that section runs.
    
    The full_run timer aggregates the times from prerun, run, and postrun
    after each complete iteration.
    """
    
    def __init__(self):
        # import here to avoid circular imports
        from suitkaise.timing import Sktimer
        
        # individual section timers created lazily
        self.prerun: Sktimer | None = None
        self.run: Sktimer | None = None
        self.postrun: Sktimer | None = None
        self.onfinish: Sktimer | None = None
        self.result: Sktimer | None = None
        self.error: Sktimer | None = None
        
        # aggregate timer for full iteration (prerun + run + postrun)
        self.full_run: Sktimer = Sktimer()
    
    def _update_full_run(self) -> None:
        """
        Update full_run timer by summing most recent times from section timers.
        
        Called by the engine after each complete run iteration.
        Only includes timers that exist and have recorded times.
        """
        total = 0.0
        
        for timer in [self.prerun, self.run, self.postrun]:
            if timer is not None and timer.num_times > 0:
                # only count timers with recorded values
                most_recent = timer.most_recent
                if most_recent is not None:
                    total += most_recent
        
        if total > 0:
            self.full_run.add_time(total)
    
    def _ensure_timer(self, section: str) -> "Sktimer":
        """
        Get or create a timer for the specified section.
        
        Args:
            section: One of 'prerun', 'run', 'postrun', 'onfinish', 'result', 'error'
        
        Returns:
            The Sktimer for that section
        """
        from suitkaise.timing import Sktimer
        
        current = getattr(self, section, None)
        if current is None:
            # allocate timer for this section on first use
            new_timer = Sktimer()
            setattr(self, section, new_timer)
            return new_timer
        return current
    
    def _reset(self) -> None:
        """
        Reset all timers to fresh state.
        
        Called when a process crashes and restarts with a life.
        """
        from suitkaise.timing import Sktimer
        
        self.prerun = None
        self.run = None
        self.postrun = None
        self.onfinish = None
        self.result = None
        self.error = None
        self.full_run = Sktimer()
