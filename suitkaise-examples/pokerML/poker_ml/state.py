from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RunConfig:
    epochs: int
    tables: int
    players_per_table: int
    hands_per_epoch: int  # 2652 = all possible starting hands
    starting_stack: int
    small_blind: int
    big_blind: int
    strength_samples: int
    learning_rate: float
    seed: int


@dataclass
class RunState:
    config: RunConfig
    stats: Dict[str, float]
    policies: Dict[str, Dict[str, List[float]]]
    started_at: float
    finished_at: float
