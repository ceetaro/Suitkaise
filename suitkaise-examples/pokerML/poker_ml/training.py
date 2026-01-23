"""
Policy training and evaluation for PokerML.

Architecture:
  Single-threaded evaluation of 169 canonical hands per agent.
  Each hand tested at all 4 stages (pre-flop, flop, turn, river).
  Policies learn online during evaluation (weights update immediately).
  Mastered hands (all agents correct) are skipped in future epochs.

This showcases:
  - Skprocess for isolated worker processes
  - @blocking decorator for CPU-heavy methods
  - .background() for parallel execution
  - Share for cross-process data
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from suitkaise.processing import Skprocess, Share
from suitkaise.sk import sk, blocking

from .cards import Card, RANKS, SUITS
from .policy import (
    PolicyTable, build_state_key,
    estimate_win_rate, calculate_hand_potential, calculate_spr,
    calculate_position_value, calculate_implied_odds, optimal_action,
)


# hand knowledge

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

# pre-flop hand tiers (5=premium, 1=trash)
PREFLOP_TIERS: Dict[Tuple[int, int, bool], int] = {}


def _init_preflop_tiers():
    """
    Initialize pre-flop hand strength tiers for all 169 canonical hands.
    
    There are 169 unique starting hands in poker:
    - 13 pairs (AA, KK, ..., 22)
    - 78 suited hands (AKs, AQs, ...)
    - 78 offsuit hands (AKo, AQo, ...)
    
    Tiers (5=best, 1=worst):
    - 5: Premium (AA, KK, QQ, JJ, TT, AKs, AQs)
    - 4: Strong (99-77, AJs, KQs, AKo)
    - 3: Playable (66-44, suited connectors, KQo)
    - 2: Marginal (33-22, weak suited, Axo)
    - 1: Trash (low offsuit, disconnected)
    """
    for r1 in RANKS:
        for r2 in RANKS:
            if r1 < r2:
                continue  # skip duplicates (keep r1 >= r2)
            for suited in [True, False]:
                if r1 == r2 and suited:
                    continue  # pairs can't be suited
                
                key = (r1, r2, suited)
                
                # pairs
                if r1 == r2:
                    if r1 >= 10:        # TT+
                        PREFLOP_TIERS[key] = 5
                    elif r1 >= 7:       # 77-99
                        PREFLOP_TIERS[key] = 4
                    else:               # 22-66
                        PREFLOP_TIERS[key] = 3
                
                # suited hands
                elif suited:
                    if r1 >= 14 and r2 >= 10:    # ATs+
                        PREFLOP_TIERS[key] = 5
                    elif r1 >= 13 and r2 >= 10:  # KTs+
                        PREFLOP_TIERS[key] = 4
                    elif abs(r1 - r2) <= 2:      # suited connectors/gappers
                        PREFLOP_TIERS[key] = 3
                    else:                         # other suited
                        PREFLOP_TIERS[key] = 2
                
                # offsuit hands
                else:
                    if r1 >= 14 and r2 >= 12:    # AQo+
                        PREFLOP_TIERS[key] = 4
                    elif r1 >= 13 and r2 >= 11:  # KJo+
                        PREFLOP_TIERS[key] = 3
                    elif r1 >= 12:               # Qxo+
                        PREFLOP_TIERS[key] = 2
                    else:                         # trash
                        PREFLOP_TIERS[key] = 1

# initialize the tiers dict at module load
_init_preflop_tiers()


def get_preflop_tier(card1: Card, card2: Card) -> int:
    """Get pre-flop strength tier (1-5) for a hand."""
    r1, r2 = max(card1.rank, card2.rank), min(card1.rank, card2.rank)
    suited = card1.suit == card2.suit
    return PREFLOP_TIERS.get((r1, r2, suited), 2)


# eval state
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
    
    if stage == 0:  # pre-flop
        return []
    elif stage == 1:  # flop
        return available[:3]
    elif stage == 2:  # turn
        return available[:4]
    else:  # river
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
    
    # distribute hands among workers
    start_idx = worker_id * len(all_hands) // num_workers
    end_idx = (worker_id + 1) * len(all_hands) // num_workers
    worker_hands = all_hands[start_idx:end_idx]
    
    states = []
    for card1, card2 in worker_hands:
        # random stage (weighted toward later streets for more learning)
        stage = rng.choices([0, 1, 2, 3], weights=[1, 2, 2, 2])[0]
        
        # generate random community cards
        community = generate_random_community(rng, [card1, card2], stage)
        
        # randomize game state within realistic ranges
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


# eval logic

def _win_prob_to_bucket(win_prob: float) -> int:
    """Convert win probability to a learnable bucket (0-5)."""
    if win_prob < 0.2:
        return 0  # very weak
    elif win_prob < 0.35:
        return 1  # weak
    elif win_prob < 0.5:
        return 2  # marginal
    elif win_prob < 0.65:
        return 3  # good
    elif win_prob < 0.8:
        return 4  # strong
    else:
        return 5  # very strong


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
    
    # calculate optimal action using poker math
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
    
    # use win_prob bucket so policy sees what optimal_action sees
    hand_strength_bucket = _win_prob_to_bucket(win_prob)
    
    # get policy's action using actual hand strength
    state_key = build_state_key(
        stage, state.position, state.stack, state.pot,
        state.to_call, hand_strength_bucket, style_bucket
    )
    
    # use BEST action (deterministic) for scoring, not random sampling
    predicted = policy.best_action(state_key)
    
    # score matching
    if predicted == optimal:
        score = 1.0
    elif predicted in ("raise", "all_in") and optimal in ("raise", "all_in"):
        score = 0.7
    elif predicted == "call" and optimal in ("call", "raise"):
        score = 0.4
    else:
        score = 0.0
    
    # ACTUAL LEARNING - reinforce correct actions, punish incorrect ones
    if learn:
        # always reinforce the optimal action strongly
        policy.update(state_key, optimal, +1.5, learning_rate)
        if predicted != optimal:
            # punish the wrong action
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


# actual worker to do evaluation
@dataclass
class EvalConfig:
    """Configuration for an evaluation worker."""
    worker_id: int
    num_workers: int
    num_models: int
    base_stack: int
    samples: int
    seed: int


@sk  # enables .background() for running methods in threads
class EvaluatorWorker(Skprocess):
    """
    Parallel policy evaluator running in a separate process.
    
    This is an Skprocess subclass, meaning it runs in its own process
    and can communicate with the parent via Share.
    
    Lifecycle (inherited from Skprocess):
      __init__   -> called in parent process
      __prerun__ -> called in child process before main work
      __run__    -> main work loop
      __postrun__ -> cleanup, store results
      __result__ -> return value to parent
      __error__  -> return value on failure
    
    Each worker:
      1. Generates its share of hands (2652 total / num_workers)
      2. Runs rotations using .background() for parallelism
      3. Evaluates policies with learning enabled
      4. Stores results in Share for parent to collect
    
    Showcases:
      - @sk decorator for .background() support
      - timing.sleep() to make methods detectable as blocking
      - .background() to run blocking code in thread pool
    """
    
    def __init__(self, share: Share, config: EvalConfig):
        # share object for cross-process communication
        self.share = share
        self.config = config
        
        # each worker gets its own rng (seeded by worker_id for reproducibility)
        self.rng = random.Random(config.seed + config.worker_id)
        
        # Skprocess config - run once, one life (no retries)
        self.process_config.runs = 1  # type: ignore[attr-defined]
        self.process_config.lives = 1  # type: ignore[attr-defined]
        
        # state populated in __prerun__
        self._states: List[EvalState] = []
        self._results: Dict[str, float] = {}

        # NOTE: I recommend populating state in __prerun__, so that 
        # if the process is doing multiple runs, things get initialized
        # per run correctly.

        # NOTE: only if you always want state to persist 
        # between runs should you populate state in __init__
    
    def __prerun__(self):
        """
        Called in child process before __run__.
        Generate this worker's share of evaluation states.
        """
        self._states = generate_eval_states_for_worker(
            worker_id=self.config.worker_id,
            num_workers=self.config.num_workers,
            rng=self.rng,
            base_stack=self.config.base_stack,
        )
    
    @blocking  # explicitly marks as blocking, enabling .background()
    def _evaluate_rotation(
        self,
        rotation_id: int,
        policies: Dict[str, Dict[str, List[float]]],
    ) -> Tuple[Dict[str, float], Dict[str, Dict[str, List[float]]]]:
        """
        Evaluate all policies on a rotated subset of states.
        Each rotation shifts which states each policy sees.
        
        Uses @blocking decorator to enable .background() for parallel execution.
        
        Returns (scores, updated_snapshots).
        """
        rotation_rng = random.Random(self.config.seed + rotation_id * 1000)
        n_states = len(self._states)
        n_policies = len(policies)
        
        if n_policies == 0 or n_states == 0:
            return {}, {}
        
        # divide states among policies for this rotation
        states_per_policy = max(1, n_states // n_policies)
        
        results: Dict[str, float] = {}
        updated_snapshots: Dict[str, Dict[str, List[float]]] = {}
        
        for idx, (agent_id, snapshot) in enumerate(policies.items()):
            # rotate starting position based on rotation_id
            start = ((idx + rotation_id) * states_per_policy) % n_states
            end = min(start + states_per_policy, n_states)
            
            # wrap around if needed
            policy_states = self._states[start:end]
            if end > n_states:
                policy_states.extend(self._states[:end - n_states])
            
            policy = PolicyTable(["fold", "call", "raise", "all_in"], rotation_rng)
            policy.load_snapshot(snapshot)
            style_bucket = 1 if rotation_rng.random() >= 0.5 else 0
            
            # evaluate WITH learning enabled
            score = evaluate_policy_on_states(
                policy, policy_states, rotation_rng, self.config.samples, style_bucket,
                learn=True, learning_rate=0.15
            )
            results[agent_id] = score
            # save the learned weights
            updated_snapshots[agent_id] = policy.snapshot()
        
        return results, updated_snapshots
    
    def __run__(self):
        """
        Run evaluation with rotations.
        Uses .background() to parallelize rotations within this process.
        
        .background() runs the method in a thread pool and returns
        a Future immediately. We collect all futures, then wait for results.
        
        This showcases suitkaise's .background() feature - no need for
        manual ThreadPoolExecutor setup!
        """
        policies = self.share.policies if self.share else {}
        if not policies:
            return
        
        num_rotations = min(6, self.config.num_models)
        
        # launch all rotations in parallel using .background()
        # .background() returns a callable, which we then call with our args
        # each call runs in a background thread and returns a Future immediately
        futures = [
            self._evaluate_rotation.background()(rotation_id, policies)  # type: ignore[attr-defined]
            for rotation_id in range(num_rotations)
        ]
        
        # collect results from all futures
        all_rotation_results: List[Tuple[Dict[str, float], Dict[str, Dict[str, List[float]]]]] = []
        for future in futures:
            try:
                result = future.result(timeout=30)
                all_rotation_results.append(result)
            except Exception:
                pass
        
        # average scores across rotations
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
        
        # collect the most recent learned policies (from last rotation)
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
        
        # store learned policies
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


# entry point

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
    
    # create shared state for results
    eval_share: Any = Share()
    eval_share.policies = policies
    eval_share.eval_results = {}
    eval_share.learned_policies = {}
    
    # create worker configs
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
    
    # run workers in parallel using Pool
    pool: Any = Pool(num_workers)
    results = list(pool.star().unordered_imap(EvaluatorWorker, worker_configs))
    
    # aggregate results from all workers
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
    
    # also check shared state
    if hasattr(eval_share, "eval_results"):
        for worker_id, worker_results in eval_share.eval_results.items():
            for agent_id, score in worker_results.items():
                if agent_id not in combined_scores:
                    combined_scores[agent_id] = []
                combined_scores[agent_id].append(score)
    
    if hasattr(eval_share, "learned_policies"):
        for agent_id, snapshot in eval_share.learned_policies.items():
            learned_policies[agent_id] = snapshot
    
    # average scores
    final_scores = {
        agent_id: sum(scores) / len(scores) if scores else 0.0
        for agent_id, scores in combined_scores.items()
    }
    
    # cleanup
    try:
        # exit sharing so that extra processes can be cleaned up
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
    newly_mastered: Set[Tuple[int, int, bool]]  # hands all agents got right
    total_hands: int
    mastered_count: int


def evaluate_policies_simple(
    policies: Dict[str, Dict[str, List[float]]],
    seed: int,
    base_stack: int = 100,
    samples: int = 10,
    variations_per_hand: int = 2,
    learn: bool = True,
    mastered_hands: Optional[Set[Tuple[int, int, bool]]] = None,
) -> EvalResult:
    """
    Single-threaded evaluation with learning and mastery tracking.
    
    This is the main training loop. For each agent:
      1. Load their policy weights
      2. Test on sampled hands (skipping already-mastered ones)
      3. Update weights based on correct/incorrect actions
      4. Track which hands ALL agents got right (newly mastered)
    
    Mastery optimization:
      Once all agents correctly handle a hand in both variations,
      that hand is "mastered" and skipped in future epochs.
      This speeds up training as agents converge.
    
    Args:
        policies: agent_id -> policy snapshot dict
        seed: random seed for this epoch
        mastered_hands: set of hand keys to skip (already mastered)
    
    Returns:
        EvalResult with scores, updated policies, and newly mastered hands
    """
    rng = random.Random(seed)
    all_hands = generate_all_hands()
    mastered_hands = mastered_hands or set()
    
    # sample hands, excluding already-mastered ones
    # take every 8th hand ≈ 332 base hands for speed
    sampled_hands = []
    for c1, c2 in all_hands[::8]:
        key = _hand_key(c1, c2)
        if key not in mastered_hands:
            sampled_hands.append((c1, c2, key))
    
    # generate variations per hand (different community cards, stacks, ...)
    states_with_keys: List[Tuple[EvalState, Tuple[int, int, bool]]] = []
    for c1, c2, hand_key in sampled_hands:
        for _ in range(max(1, variations_per_hand)):
            # random stage (weighted toward post-flop for more learning)
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
    
    # track which hands each agent got correct (for mastery detection)
    hand_correct_counts: Dict[Tuple[int, int, bool], int] = {}
    num_agents = len(policies)
    
    results: Dict[str, float] = {}
    learned_policies: Dict[str, Dict[str, List[float]]] = {}
    
    # evaluate each agent
    for agent_id, snapshot in policies.items():
        # load policy weights
        policy = PolicyTable(["fold", "call", "raise", "all_in"], rng)
        policy.load_snapshot(snapshot)
        
        total_score = 0.0
        for state, hand_key in states_with_keys:
            # evaluate and learn from this state
            score, optimal, predicted = evaluate_single_state(
                policy, state, rng, samples, 1,
                learn=learn, learning_rate=0.15
            )
            total_score += score
            
            # track perfect matches for mastery
            if score >= 1.0:
                hand_correct_counts[hand_key] = hand_correct_counts.get(hand_key, 0) + 1
        
        # save results
        results[agent_id] = total_score / len(states_with_keys) if states_with_keys else 0.0
        learned_policies[agent_id] = policy.snapshot()
    
    # find hands that ALL agents got correct in BOTH variations = newly mastered
    newly_mastered: Set[Tuple[int, int, bool]] = set()
    for hand_key, correct_count in hand_correct_counts.items():
        # each hand appears twice, need 2x num_agents perfect scores
        if correct_count >= num_agents * 2:
            newly_mastered.add(hand_key)
    
    return EvalResult(
        scores=results,
        learned_policies=learned_policies,
        newly_mastered=newly_mastered,
        total_hands=len(sampled_hands),
        mastered_count=len(mastered_hands) + len(newly_mastered),
    )
