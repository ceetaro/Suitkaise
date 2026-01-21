"""
Systematic Policy Evaluator using Skprocess Architecture

Architecture:
  Parent spawns 6 EvaluatorWorker sub-processes.
  Each sub handles 442 unique states (2652 / 6).
  Each sub runs 6 rotations using .background() so every model sees every hand.
  Results aggregate via Share.

This showcases:
  - Skprocess for sub-workers
  - .background() for internal parallelism
  - Share for cross-process result aggregation
"""

from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from suitkaise.processing import Skprocess, Share

from .cards import Card, RANKS, SUITS
from .policy import (
    PolicyTable, build_state_key,
    estimate_win_rate, calculate_hand_potential, calculate_spr,
    calculate_position_value, calculate_implied_odds, optimal_action,
)


# ═══════════════════════════════════════════════════════════════════════════════
# HAND KNOWLEDGE - Pre-encoded poker knowledge for agents
# ═══════════════════════════════════════════════════════════════════════════════

HAND_RANKINGS = {
    0: "High Card",
    1: "Pair",
    2: "Two Pair", 
    3: "Three of a Kind",
    4: "Straight",
    5: "Flush",
    6: "Full House",
    7: "Four of a Kind",
    8: "Straight Flush",
}

# Pre-flop hand tiers (5=premium, 1=trash)
PREFLOP_TIERS: Dict[Tuple[int, int, bool], int] = {}


def _init_preflop_tiers():
    """Initialize pre-flop hand strength tiers for all 169 canonical hands."""
    for r1 in RANKS:
        for r2 in RANKS:
            if r1 < r2:
                continue
            for suited in [True, False]:
                if r1 == r2 and suited:
                    continue
                
                key = (r1, r2, suited)
                
                if r1 == r2:  # Pairs
                    if r1 >= 10:
                        PREFLOP_TIERS[key] = 5
                    elif r1 >= 7:
                        PREFLOP_TIERS[key] = 4
                    else:
                        PREFLOP_TIERS[key] = 3
                elif suited:
                    if r1 >= 14 and r2 >= 10:
                        PREFLOP_TIERS[key] = 5
                    elif r1 >= 13 and r2 >= 10:
                        PREFLOP_TIERS[key] = 4
                    elif abs(r1 - r2) <= 2:
                        PREFLOP_TIERS[key] = 3
                    else:
                        PREFLOP_TIERS[key] = 2
                else:
                    if r1 >= 14 and r2 >= 12:
                        PREFLOP_TIERS[key] = 4
                    elif r1 >= 13 and r2 >= 11:
                        PREFLOP_TIERS[key] = 3
                    elif r1 >= 12:
                        PREFLOP_TIERS[key] = 2
                    else:
                        PREFLOP_TIERS[key] = 1

_init_preflop_tiers()


def get_preflop_tier(card1: Card, card2: Card) -> int:
    """Get pre-flop strength tier (1-5) for a hand."""
    r1, r2 = max(card1.rank, card2.rank), min(card1.rank, card2.rank)
    suited = card1.suit == card2.suit
    return PREFLOP_TIERS.get((r1, r2, suited), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATION STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EvalState:
    """A single evaluation state with hole cards, community cards, and game context."""
    card1: Card
    card2: Card
    community: List[Card]  # 0, 3, 4, or 5 cards (pre-flop, flop, turn, river)
    stage: int  # 0=preflop, 1=flop, 2=turn, 3=river
    stack: int
    pot: int
    to_call: int
    position: int
    preflop_tier: int


def generate_all_hands() -> List[Tuple[Card, Card]]:
    """Generate all 2652 ordered hole card combinations (52 × 51)."""
    all_cards = [Card(r, s) for r in RANKS for s in SUITS]
    hands = []
    for i, c1 in enumerate(all_cards):
        for j, c2 in enumerate(all_cards):
            if i != j:
                hands.append((c1, c2))
    return hands


def generate_random_community(
    rng: random.Random,
    exclude: List[Card],
    stage: int,
) -> List[Card]:
    """Generate random community cards for a given stage, excluding hole cards."""
    all_cards = [Card(r, s) for r in RANKS for s in SUITS]
    available = [c for c in all_cards if c not in exclude]
    rng.shuffle(available)
    
    if stage == 0:  # Pre-flop
        return []
    elif stage == 1:  # Flop
        return available[:3]
    elif stage == 2:  # Turn
        return available[:4]
    else:  # River
        return available[:5]


def generate_eval_states_for_worker(
    worker_id: int,
    num_workers: int,
    rng: random.Random,
    base_stack: int = 100,
    variance: float = 0.2,
) -> List[EvalState]:
    """
    Generate this worker's share of evaluation states.
    
    Total hands = 2652 (52 × 51)
    Each worker gets 2652 / num_workers = 442 hands
    
    Community cards are randomly generated for each hand.
    Stage is randomly chosen (pre-flop, flop, turn, or river).
    """
    all_hands = generate_all_hands()
    
    # Distribute hands among workers
    start_idx = worker_id * len(all_hands) // num_workers
    end_idx = (worker_id + 1) * len(all_hands) // num_workers
    worker_hands = all_hands[start_idx:end_idx]
    
    states = []
    for card1, card2 in worker_hands:
        # Random stage (weighted toward later streets for more learning)
        stage = rng.choices([0, 1, 2, 3], weights=[1, 2, 2, 2])[0]
        
        # Generate random community cards
        community = generate_random_community(rng, [card1, card2], stage)
        
        # Randomize game state within realistic ranges
        stack = int(base_stack * (1 + rng.uniform(-variance, variance)))
        pot = rng.choice([3, 6, 10, 15, 20, 30, 50, 80])
        to_call = rng.choice([0, 0, 0, 2, 4, 6, 10, 15, 25])  # More checks
        position = rng.randint(0, 5)
        preflop_tier = get_preflop_tier(card1, card2)
        
        states.append(EvalState(
            card1=card1,
            card2=card2,
            community=community,
            stage=stage,
            stack=stack,
            pot=pot,
            to_call=to_call,
            position=position,
            preflop_tier=preflop_tier,
        ))
    
    return states


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATION LOGIC
# ═══════════════════════════════════════════════════════════════════════════════

def _win_prob_to_bucket(win_prob: float) -> int:
    """Convert win probability to a learnable bucket (0-5)."""
    if win_prob < 0.2:
        return 0  # Very weak
    elif win_prob < 0.35:
        return 1  # Weak
    elif win_prob < 0.5:
        return 2  # Marginal
    elif win_prob < 0.65:
        return 3  # Good
    elif win_prob < 0.8:
        return 4  # Strong
    else:
        return 5  # Very strong


def evaluate_single_state(
    policy: PolicyTable,
    state: EvalState,
    rng: random.Random,
    samples: int,
    style_bucket: int,
    learn: bool = True,
    learning_rate: float = 0.1,
) -> Tuple[float, str, str]:
    """
    Evaluate policy on a single state.
    Returns (score, optimal_action, predicted_action).
    
    If learn=True, updates policy weights based on correctness.
    """
    hole = [state.card1, state.card2]
    community = state.community
    stage = state.stage
    
    # Calculate optimal action using poker math
    win_prob = estimate_win_rate(hole, community, rng, samples)
    pot_odds = 0.0 if state.to_call == 0 else state.to_call / max(state.pot + state.to_call, 1)
    hand_potential = calculate_hand_potential(hole, community, rng, samples)
    spr = calculate_spr(state.stack, state.pot)
    position_value = calculate_position_value(state.position, 6)
    implied_odds = calculate_implied_odds(win_prob, hand_potential, spr, state.to_call, state.pot)
    
    optimal = optimal_action(
        win_prob=win_prob,
        pot_odds=pot_odds,
        stack=state.stack,
        to_call=state.to_call,
        hand_potential=hand_potential,
        spr=spr,
        position_value=position_value,
        implied_odds=implied_odds,
    )
    
    # Use win_prob bucket so policy sees what optimal_action sees
    hand_strength_bucket = _win_prob_to_bucket(win_prob)
    
    # Get policy's action using actual hand strength
    state_key = build_state_key(
        stage, state.position, state.stack, state.pot,
        state.to_call, hand_strength_bucket, style_bucket
    )
    
    # Use BEST action (deterministic) for scoring, not random sampling
    predicted = policy.best_action(state_key)
    
    # Score matching
    if predicted == optimal:
        score = 1.0
    elif predicted in ("raise", "all_in") and optimal in ("raise", "all_in"):
        score = 0.7
    elif predicted == "call" and optimal in ("call", "raise"):
        score = 0.4
    else:
        score = 0.0
    
    # ACTUAL LEARNING: Reinforce correct actions, punish incorrect ones
    if learn:
        # Always reinforce the optimal action strongly
        policy.update(state_key, optimal, +1.5, learning_rate)
        if predicted != optimal:
            # Punish the wrong action
            policy.update(state_key, predicted, -0.8, learning_rate)
    
    return score, optimal, predicted


def evaluate_policy_on_states(
    policy: PolicyTable,
    states: List[EvalState],
    rng: random.Random,
    samples: int,
    style_bucket: int,
    learn: bool = False,
    learning_rate: float = 0.1,
) -> float:
    """Evaluate policy on a batch of states. Returns average score."""
    if not states:
        return 0.0
    total = sum(
        evaluate_single_state(policy, s, rng, samples, style_bucket, learn, learning_rate)[0]
        for s in states
    )
    return total / len(states)


# ═══════════════════════════════════════════════════════════════════════════════
# EVALUATOR WORKER (Skprocess)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class EvalConfig:
    """Configuration for an evaluation worker."""
    worker_id: int
    num_workers: int
    num_models: int
    base_stack: int
    samples: int
    seed: int


class EvaluatorWorker(Skprocess):
    """
    Sub-worker that evaluates policies against a batch of hands.
    
    Uses .background() to run rotations in parallel, ensuring every
    model sees every hand in this worker's batch.
    """
    
    def __init__(self, share: Any, config: EvalConfig):
        self.share = share
        self.config = config
        self.rng = random.Random(config.seed + config.worker_id)
        
        self.process_config.runs = 1  # type: ignore[attr-defined]
        self.process_config.lives = 1  # type: ignore[attr-defined]
        
        self._states: List[EvalState] = []
        self._results: Dict[str, float] = {}
    
    def __prerun__(self):
        """Generate this worker's share of evaluation states."""
        self._states = generate_eval_states_for_worker(
            worker_id=self.config.worker_id,
            num_workers=self.config.num_workers,
            rng=self.rng,
            base_stack=self.config.base_stack,
        )
    
    def _evaluate_rotation(
        self,
        rotation_id: int,
        policies: Dict[str, Dict[str, List[float]]],
    ) -> Tuple[Dict[str, float], Dict[str, Dict[str, List[float]]]]:
        """
        Evaluate all policies on a rotated subset of states.
        Each rotation shifts which states each policy sees.
        
        Returns (scores, updated_snapshots).
        """
        rotation_rng = random.Random(self.config.seed + rotation_id * 1000)
        n_states = len(self._states)
        n_policies = len(policies)
        
        if n_policies == 0 or n_states == 0:
            return {}, {}
        
        # Divide states among policies for this rotation
        states_per_policy = max(1, n_states // n_policies)
        
        results: Dict[str, float] = {}
        updated_snapshots: Dict[str, Dict[str, List[float]]] = {}
        
        for idx, (agent_id, snapshot) in enumerate(policies.items()):
            # Rotate starting position based on rotation_id
            start = ((idx + rotation_id) * states_per_policy) % n_states
            end = min(start + states_per_policy, n_states)
            
            # Wrap around if needed
            policy_states = self._states[start:end]
            if end > n_states:
                policy_states.extend(self._states[:end - n_states])
            
            policy = PolicyTable(["fold", "call", "raise", "all_in"], rotation_rng)
            policy.load_snapshot(snapshot)
            style_bucket = 1 if rotation_rng.random() >= 0.5 else 0
            
            # Evaluate WITH learning enabled
            score = evaluate_policy_on_states(
                policy, policy_states, rotation_rng, self.config.samples, style_bucket,
                learn=True, learning_rate=0.15
            )
            results[agent_id] = score
            # Save the learned weights
            updated_snapshots[agent_id] = policy.snapshot()
        
        return results, updated_snapshots
    
    def __run__(self):
        """
        Run evaluation with rotations.
        Uses ThreadPoolExecutor to parallelize rotations within this process.
        """
        policies = self.share.policies if self.share else {}
        if not policies:
            return
        
        num_rotations = min(6, self.config.num_models)
        
        # Run rotations in parallel using threads
        with ThreadPoolExecutor(max_workers=num_rotations) as executor:
            futures = [
                executor.submit(self._evaluate_rotation, rotation_id, policies)
                for rotation_id in range(num_rotations)
            ]
            
            all_rotation_results: List[Tuple[Dict[str, float], Dict[str, Dict[str, List[float]]]]] = []
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    all_rotation_results.append(result)
                except Exception:
                    pass
        
        # Average scores across rotations
        combined: Dict[str, List[float]] = {}
        for scores, _ in all_rotation_results:
            for agent_id, score in scores.items():
                if agent_id not in combined:
                    combined[agent_id] = []
                combined[agent_id].append(score)
        
        self._results = {
            agent_id: sum(scores) / len(scores) if scores else 0.0
            for agent_id, scores in combined.items()
        }
        
        # Collect the most recent learned policies (from last rotation)
        self._updated_policies: Dict[str, Dict[str, List[float]]] = {}
        if all_rotation_results:
            _, last_snapshots = all_rotation_results[-1]
            self._updated_policies = last_snapshots
    
    def __postrun__(self):
        """Store results in shared memory."""
        if self.share and hasattr(self.share, "eval_results"):
            results = self.share.eval_results
            results[self.config.worker_id] = self._results
            self.share.eval_results = results
        
        # Store learned policies
        if self.share and hasattr(self.share, "learned_policies"):
            learned = self.share.learned_policies
            for agent_id, snapshot in self._updated_policies.items():
                learned[agent_id] = snapshot
            self.share.learned_policies = learned
    
    def __result__(self):
        return {
            "worker_id": self.config.worker_id,
            "num_states": len(self._states),
            "scores": self._results,
            "learned_policies": self._updated_policies,
        }
    
    def __error__(self):
        return {"worker_id": self.config.worker_id, "error": True}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EVALUATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_all_policies_parallel(
    policies: Dict[str, Dict[str, List[float]]],
    seed: int,
    base_stack: int = 100,
    samples: int = 15,
    num_workers: int = 6,
) -> Tuple[Dict[str, float], Dict[str, Dict[str, List[float]]]]:
    """
    Evaluate all policies using parallel Skprocess workers.
    
    Architecture:
      - Spawns `num_workers` EvaluatorWorker sub-processes
      - Each worker handles 2652/num_workers = 442 hands
      - Each worker runs rotations so every model sees every hand
      - Results aggregate via Share
      - Learning is applied during evaluation
    
    Returns (scores, learned_policies):
      - scores: dict of agent_id -> score (0.0-1.0)
      - learned_policies: dict of agent_id -> updated policy snapshot
    """
    from suitkaise.processing import Pool
    
    # Create shared state for results
    eval_share: Any = Share()
    eval_share.policies = policies
    eval_share.eval_results = {}
    eval_share.learned_policies = {}
    
    # Create worker configs
    worker_configs = [
        (
            eval_share,
            EvalConfig(
                worker_id=i,
                num_workers=num_workers,
                num_models=len(policies),
                base_stack=base_stack,
                samples=samples,
                seed=seed + i,
            ),
        )
        for i in range(num_workers)
    ]
    
    # Run workers in parallel using Pool
    pool: Any = Pool(num_workers)
    results = list(pool.star().unordered_imap(EvaluatorWorker, worker_configs))
    
    # Aggregate results from all workers
    combined_scores: Dict[str, List[float]] = {}
    learned_policies: Dict[str, Dict[str, List[float]]] = {}
    
    for result in results:
        if isinstance(result, dict):
            if "scores" in result:
                for agent_id, score in result["scores"].items():
                    if agent_id not in combined_scores:
                        combined_scores[agent_id] = []
                    combined_scores[agent_id].append(score)
            if "learned_policies" in result:
                for agent_id, snapshot in result["learned_policies"].items():
                    learned_policies[agent_id] = snapshot
    
    # Also check shared state
    if hasattr(eval_share, "eval_results"):
        for worker_id, worker_results in eval_share.eval_results.items():
            for agent_id, score in worker_results.items():
                if agent_id not in combined_scores:
                    combined_scores[agent_id] = []
                combined_scores[agent_id].append(score)
    
    if hasattr(eval_share, "learned_policies"):
        for agent_id, snapshot in eval_share.learned_policies.items():
            learned_policies[agent_id] = snapshot
    
    # Average scores
    final_scores = {
        agent_id: sum(scores) / len(scores) if scores else 0.0
        for agent_id, scores in combined_scores.items()
    }
    
    # Cleanup
    try:
        eval_share.exit()
    except Exception:
        pass
    
    return final_scores, learned_policies


def _hand_key(c1: Card, c2: Card) -> Tuple[int, int, bool]:
    """Create a canonical key for a hole card combination."""
    r1, r2 = max(c1.rank, c2.rank), min(c1.rank, c2.rank)
    suited = c1.suit == c2.suit
    return (r1, r2, suited)


@dataclass
class EvalResult:
    """Result of evaluating policies with mastery tracking."""
    scores: Dict[str, float]
    learned_policies: Dict[str, Dict[str, List[float]]]
    newly_mastered: Set[Tuple[int, int, bool]]  # Hands all agents got right
    total_hands: int
    mastered_count: int


def evaluate_policies_simple(
    policies: Dict[str, Dict[str, List[float]]],
    seed: int,
    base_stack: int = 100,
    samples: int = 10,
    learn: bool = True,
    mastered_hands: Optional[Set[Tuple[int, int, bool]]] = None,
) -> EvalResult:
    """
    Single-threaded evaluation with learning and mastery tracking.
    
    Args:
        policies: Agent policies to evaluate
        seed: Random seed for this epoch
        mastered_hands: Set of hand keys to SKIP (already mastered)
    
    Returns:
        EvalResult with scores, learned policies, and newly mastered hands.
    """
    rng = random.Random(seed)
    all_hands = generate_all_hands()
    mastered_hands = mastered_hands or set()
    
    # Sample hands, excluding already-mastered ones
    sampled_hands = []
    for c1, c2 in all_hands[::8]:  # Every 8th hand ≈ 332 base hands
        key = _hand_key(c1, c2)
        if key not in mastered_hands:
            sampled_hands.append((c1, c2, key))
    
    # Generate states with hand keys for tracking
    states_with_keys: List[Tuple[EvalState, Tuple[int, int, bool]]] = []
    for c1, c2, hand_key in sampled_hands:
        for _ in range(2):  # 2 variations per hand
            stage = rng.choices([0, 1, 2, 3], weights=[1, 2, 2, 2])[0]
            community = generate_random_community(rng, [c1, c2], stage)
            
            state = EvalState(
                card1=c1, card2=c2,
                community=community,
                stage=stage,
                stack=int(base_stack * rng.uniform(0.8, 1.2)),
                pot=rng.choice([5, 15, 30]),
                to_call=rng.choice([0, 5, 15]),
                position=rng.randint(0, 5),
                preflop_tier=get_preflop_tier(c1, c2),
            )
            states_with_keys.append((state, hand_key))
    
    # Track which hands each agent got correct
    hand_correct_counts: Dict[Tuple[int, int, bool], int] = {}
    num_agents = len(policies)
    
    results: Dict[str, float] = {}
    learned_policies: Dict[str, Dict[str, List[float]]] = {}
    
    for agent_id, snapshot in policies.items():
        policy = PolicyTable(["fold", "call", "raise", "all_in"], rng)
        policy.load_snapshot(snapshot)
        
        total_score = 0.0
        for state, hand_key in states_with_keys:
            score, optimal, predicted = evaluate_single_state(
                policy, state, rng, samples, 1,
                learn=learn, learning_rate=0.15
            )
            total_score += score
            
            # Track if this agent got this hand right
            if score >= 1.0:  # Perfect match
                hand_correct_counts[hand_key] = hand_correct_counts.get(hand_key, 0) + 1
        
        results[agent_id] = total_score / len(states_with_keys) if states_with_keys else 0.0
        learned_policies[agent_id] = policy.snapshot()
    
    # Find hands that ALL agents got correct (newly mastered)
    newly_mastered: Set[Tuple[int, int, bool]] = set()
    for hand_key, correct_count in hand_correct_counts.items():
        # Each hand appears twice (2 variations), so need 2x num_agents correct
        if correct_count >= num_agents * 2:
            newly_mastered.add(hand_key)
    
    return EvalResult(
        scores=results,
        learned_policies=learned_policies,
        newly_mastered=newly_mastered,
        total_hands=len(sampled_hands),
        mastered_count=len(mastered_hands) + len(newly_mastered),
    )
