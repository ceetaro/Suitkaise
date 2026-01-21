"""
Poker Agent - the AI player that learns to play poker.

Uses:
  - @sk decorator for Share serialization and async modifiers
  - Circuit breakers to prevent runaway resource usage
  - PolicyTable for action selection based on learned weights
"""
from __future__ import annotations

# python imports
from typing import Dict, Tuple
import random

# SUITKAISE IMPORTS
from suitkaise import timing
from suitkaise.circuits import Circuit, BreakingCircuit
from suitkaise.sk import sk

# example-specific imports
from .policy import PolicyTable


@sk  # enables .background(), .asynced(), and Share serialization
class PokerAgent:
    """Poker agent that chooses actions based on learned policy."""

    def __init__(self, agent_id: str, rng: random.Random, style: float):
        # agent identity and randomness source
        self.agent_id = agent_id
        self.rng = rng
        
        # style affects aggression (0.0 = passive, 1.0 = aggressive)
        self.style = style
        
        # possible poker actions
        self.actions = ["fold", "call", "raise", "all_in"]
        
        # the learned policy table (state -> action weights)
        self.policy = PolicyTable(self.actions, rng)
        
        # track invalid action attempts
        self.invalid_actions = 0

        # circuit breaker: trips after 5 invalid actions, forces sleep
        # prevents infinite loops from buggy decision logic
        self.breaker = BreakingCircuit(
            num_shorts_to_trip=5, 
            sleep_time_after_trip=0.1, 
            backoff_factor=1.0, 
            max_sleep_time=10.0
        )

        # rate limiter: prevents agents from overloading the system
        # trips after 3 rapid calls, adds small delay
        self.rate_limit = Circuit(
            num_shorts_to_trip=3, 
            sleep_time_after_trip=0.02, 
            backoff_factor=1.5, 
            max_sleep_time=0.2
        )

    def choose_action(
        self, 
        state_key: Tuple[int, ...], 
        stack: int, 
        to_call: int, 
        pot: int, 
        min_raise: int
    ) -> Dict[str, int | str]:
        """
        Choose an action based on current game state.
        
        Args:
            state_key: tuple encoding the game state (stage, position, stacks, etc.)
            stack: agent's remaining chips
            to_call: amount needed to call current bet
            pot: current pot size
            min_raise: minimum legal raise amount
        
        Returns:
            dict with 'action' and 'amount' keys
        """

        # check rate limiter - if tripped, fold immediately to prevent spam
        if self.rate_limit.short():
            self.breaker.short()
            return {"action": "fold", "amount": 0}

        # query the policy table for action based on state
        action = self.policy.choose_action(state_key)

        # fold and call have no bet amount
        if action == "fold":
            return {"action": "fold", "amount": 0}

        if action == "call":
            return {"action": "call", "amount": 0}

        # all-in uses entire stack
        if action == "all_in":
            return {"action": "all_in", "amount": stack}

        # raise: calculate bet size based on style (aggression factor)
        aggression = 0.5 + self.style
        target = int(min_raise + aggression * max(pot, min_raise))
        
        # clamp to valid range: at least min_raise, at most entire stack
        return {"action": "raise", "amount": max(min_raise, min(target, stack))}


    def update_policy(self, 
        state_key: Tuple[int, ...], 
        action: str, 
        reward: float, 
        lr: float
    ) -> None:
        """Update the policy."""

        # update policy w args
        self.policy.update(state_key, action, reward, lr)


    def export_policy(self) -> Dict[str, list[float]]:
        """Export the policy."""

        # export policy
        return self.policy.snapshot()


    def import_policy(self, snapshot: Dict[str, list[float]]) -> None:
        """Load the policy."""

        # load policy snapshot
        self.policy.load_snapshot(snapshot)
