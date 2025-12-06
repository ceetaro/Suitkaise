"""
ProcessTimers container for timing lifecycle sections.

Created lazily - only when @processing.timethis() decorator is used.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from suitkaise.sktime import Timer


class ProcessTimers:
    """
    Container for timing lifecycle sections of a Process.
    
    Only created if at least one @processing.timethis() decorator is used.
    Each section timer is created when that section's decorator is first applied.
    
    The full_loop timer aggregates the most recent times from preloop, loop, 
    and postloop after each complete iteration.
    """
    
    def __init__(self):
        # Import here to avoid circular imports
        from suitkaise.sktime import Timer
        
        # Individual section timers (created on-demand by decorator)
        self.preloop: Timer | None = None
        self.loop: Timer | None = None
        self.postloop: Timer | None = None
        self.onfinish: Timer | None = None
        
        # Aggregate timer - always exists once ProcessTimers is created
        self.full_loop: Timer = Timer()
    
    def _update_full_loop(self) -> None:
        """
        Update full_loop timer by summing most recent times from section timers.
        
        Called by the engine after each complete loop iteration.
        Only includes timers that exist and have recorded times.
        """
        total = 0.0
        
        for timer in [self.preloop, self.loop, self.postloop]:
            if timer is not None and timer.num_times > 0:
                most_recent = timer.most_recent
                if most_recent is not None:
                    total += most_recent
        
        if total > 0:
            self.full_loop.add_time(total)
    
    def _ensure_timer(self, section: str) -> "Timer":
        """
        Get or create a timer for the specified section.
        
        Args:
            section: One of 'preloop', 'loop', 'postloop', 'onfinish'
        
        Returns:
            The Timer for that section
        """
        from suitkaise.sktime import Timer
        
        current = getattr(self, section, None)
        if current is None:
            new_timer = Timer()
            setattr(self, section, new_timer)
            return new_timer
        return current

