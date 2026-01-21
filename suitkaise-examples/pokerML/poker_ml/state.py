"""
State dataclasses for serializing training runs.

These are saved to disk via cerial.serialize() so training
can be resumed or best policies can be loaded for play mode.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RunConfig:
    """Configuration for a training run."""
    epochs: int                 # number of training epochs
    tables: int                 # number of parallel tables
    players_per_table: int      # agents per table
    hands_per_epoch: int        # 169 - all hands possible only measuring on or off suit
    starting_stack: int         # initial chip count per agent
    small_blind: int            # forced small blind bet
    big_blind: int              # forced big blind bet
    strength_samples: int       # random trials per hand strength estimate (more = slower but more accurate)
    learning_rate: float        # policy update learning rate
    seed: int                   # random seed for reproducibility


@dataclass
class RunState:
    """Complete state of a training run (saved to disk)."""
    config: RunConfig                               # the one above this
    stats: Dict[str, float]                         # metrics (hands played, best score, ...)
    policies: Dict[str, Dict[str, List[float]]]     # agent_id -> policy snapshot
    started_at: float                               # unix timestamp when training started
    finished_at: float                              # unix timestamp when training ended
