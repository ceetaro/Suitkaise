from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from .cards import Card, Deck, RANKS, SUITS
from .hand_eval import evaluate_hand, compare_hands


def _bucket(value: float, thresholds: List[float]) -> int:
    for idx, t in enumerate(thresholds):
        if value <= t:
            return idx
    return len(thresholds)


def build_state_key(stage: int, position: int, stack: int, pot: int, to_call: int, hand_bucket: int, style_bucket: int) -> Tuple[int, ...]:
    stack_bucket = _bucket(stack, [20, 50, 100, 200])
    pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
    pot_bucket = _bucket(pot_odds, [0.1, 0.2, 0.3, 0.5])
    return (stage, position, stack_bucket, pot_bucket, hand_bucket, style_bucket)


def hand_strength_bucket(hole: List[Card], community: List[Card], rng: random.Random, samples: int) -> int:
    if not community:
        ranks = sorted([c.rank for c in hole], reverse=True)
        suited = hole[0].suit == hole[1].suit
        if ranks[0] == ranks[1]:
            return 5
        if suited and ranks[0] >= 11 and ranks[1] >= 10:
            return 4
        if ranks[0] >= 13:
            return 3
        if suited and abs(ranks[0] - ranks[1]) <= 2:
            return 2
        return 1

    base_hand = evaluate_hand(hole + community)
    strength = base_hand[0]
    if samples <= 0:
        return _bucket(strength, [1, 2, 3, 4, 5])

    wins = 0
    for _ in range(samples):
        deck = [Card(r, s) for r in RANKS for s in SUITS if Card(r, s) not in hole + community]
        rng.shuffle(deck)
        opp_hole = deck[:2]
        needed = 5 - len(community)
        board = community + deck[2:2 + needed]
        my_hand = evaluate_hand(hole + board)
        opp_hand = evaluate_hand(opp_hole + board)
        if compare_hands(my_hand, opp_hand) >= 0:
            wins += 1
    win_rate = wins / samples
    return _bucket(win_rate, [0.2, 0.4, 0.6, 0.8])


class PolicyTable:
    def __init__(self, actions: List[str], rng: random.Random):
        self._actions = actions
        self._rng = rng
        self._table: Dict[Tuple[int, ...], List[float]] = {}

    def _init_weights(self) -> List[float]:
        return [self._rng.uniform(-0.5, 0.5) for _ in self._actions]

    def get_weights(self, key: Tuple[int, ...]) -> List[float]:
        if key not in self._table:
            self._table[key] = self._init_weights()
        return self._table[key]

    def choose_action(self, key: Tuple[int, ...]) -> str:
        """Choose action using softmax sampling (exploration)."""
        weights = self.get_weights(key)
        max_w = max(weights)
        exps = [math.exp(w - max_w) for w in weights]
        total = sum(exps)
        probs = [e / total for e in exps]
        pick = self._rng.random()
        cumulative = 0.0
        for action, p in zip(self._actions, probs):
            cumulative += p
            if pick <= cumulative:
                return action
        return self._actions[-1]

    def best_action(self, key: Tuple[int, ...]) -> str:
        """Choose the best action deterministically (exploitation)."""
        weights = self.get_weights(key)
        best_idx = weights.index(max(weights))
        return self._actions[best_idx]

    def update(self, key: Tuple[int, ...], action: str, reward: float, lr: float) -> None:
        weights = self.get_weights(key)
        idx = self._actions.index(action)
        weights[idx] += lr * reward

    def snapshot(self) -> Dict[str, List[float]]:
        return {";".join(map(str, k)): v[:] for k, v in self._table.items()}

    def load_snapshot(self, snapshot: Dict[str, List[float]]) -> None:
        self._table = {tuple(int(x) for x in k.split(";")): v[:] for k, v in snapshot.items()}


def estimate_win_rate(hole: List[Card], community: List[Card], rng: random.Random, samples: int) -> float:
    wins = 0
    ties = 0
    for _ in range(samples):
        deck = [Card(r, s) for r in RANKS for s in SUITS if Card(r, s) not in hole + community]
        rng.shuffle(deck)
        opp_hole = deck[:2]
        needed = 5 - len(community)
        board = community + deck[2:2 + needed]
        my_hand = evaluate_hand(hole + board)
        opp_hand = evaluate_hand(opp_hole + board)
        cmp = compare_hands(my_hand, opp_hand)
        if cmp > 0:
            wins += 1
        elif cmp == 0:
            ties += 1
    return (wins + 0.5 * ties) / samples


def calculate_hand_potential(hole: List[Card], community: List[Card], rng: random.Random, samples: int) -> float:
    """
    Calculate how likely the hand is to improve on future streets.
    Returns 0.0-1.0 where higher = more potential to improve.
    
    Looks for:
    - Flush draws (4 to a flush)
    - Straight draws (open-ended or gutshot)
    - Overcards that could pair
    """
    if len(community) >= 5:
        return 0.0  # No more cards coming
    
    if len(community) == 0:
        # Pre-flop: estimate based on hand type
        ranks = sorted([c.rank for c in hole], reverse=True)
        suited = hole[0].suit == hole[1].suit
        connected = abs(ranks[0] - ranks[1]) <= 2
        
        potential = 0.3  # Base potential
        if suited:
            potential += 0.15  # Flush draw potential
        if connected:
            potential += 0.1  # Straight draw potential
        if ranks[0] >= 12:  # High cards
            potential += 0.1
        return min(potential, 1.0)
    
    all_cards = hole + community
    
    # Check for flush draw
    suit_counts: Dict[str, int] = {}
    for card in all_cards:
        suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1
    flush_draw = any(count == 4 for count in suit_counts.values())
    
    # Check for straight draw
    ranks = sorted(set(c.rank for c in all_cards))
    straight_draw = False
    # Open-ended: 4 consecutive cards
    for i in range(len(ranks) - 3):
        if ranks[i+3] - ranks[i] == 3:
            straight_draw = True
            break
    # Gutshot: 4 cards with one gap
    if not straight_draw:
        for i in range(len(ranks) - 3):
            if ranks[i+3] - ranks[i] == 4:
                straight_draw = True
                break
    
    # Count overcards (hole cards higher than board)
    if community:
        board_high = max(c.rank for c in community)
        overcards = sum(1 for c in hole if c.rank > board_high)
    else:
        overcards = 0
    
    # Calculate potential score
    potential = 0.0
    if flush_draw:
        potential += 0.35  # ~35% to hit flush with 2 cards to come
    if straight_draw:
        potential += 0.25  # ~31% open-ended, ~17% gutshot
    potential += overcards * 0.06  # ~6% per overcard to pair
    
    return min(potential, 1.0)


def calculate_spr(stack: int, pot: int) -> float:
    """
    Stack-to-Pot Ratio.
    Low SPR (<4): Favor commitment, all-ins
    Medium SPR (4-10): Standard play
    High SPR (>10): Favor speculative hands, position
    """
    if pot <= 0:
        return 20.0  # Max SPR
    return min(stack / pot, 20.0)


def calculate_implied_odds(win_prob: float, hand_potential: float, spr: float, to_call: int, pot: int) -> float:
    """
    Implied odds factor: how much more can we win if we hit?
    Higher SPR + higher potential = better implied odds.
    Returns a multiplier (1.0 = break even, >1.0 = profitable).
    """
    if to_call <= 0:
        return 1.5  # No cost to see more cards
    
    # Base: pot odds
    immediate_odds = pot / to_call if to_call > 0 else float('inf')
    
    # Potential future winnings based on SPR and hand potential
    # If we hit our draw, we can win more with deeper stacks
    future_value = hand_potential * min(spr, 10) * 0.3
    
    # Combine immediate odds with future value
    implied_multiplier = 1.0 + future_value
    
    return implied_multiplier


def calculate_position_value(position: int, num_players: int = 6) -> float:
    """
    Position value: later position = more information = higher value.
    Returns 0.0-1.0 where 1.0 = button (best position).
    
    Position 0 = small blind (worst)
    Position num_players-1 = button (best)
    """
    if num_players <= 1:
        return 0.5
    return position / (num_players - 1)


def optimal_action(
    win_prob: float,
    pot_odds: float,
    stack: int,
    to_call: int,
    hand_potential: float = 0.0,
    spr: float = 10.0,
    position_value: float = 0.5,
    implied_odds: float = 1.0,
) -> str:
    """
    Determine optimal action considering all factors:
    - win_prob: Current hand strength (0-1)
    - pot_odds: Cost to call vs pot (0-1)
    - stack: Player's remaining chips
    - to_call: Amount needed to call
    - hand_potential: Likelihood of improving (0-1)
    - spr: Stack-to-pot ratio
    - position_value: Positional advantage (0-1)
    - implied_odds: Future value multiplier
    """
    
    # Effective hand strength = current strength + weighted potential
    # Weight potential more when we have position and good implied odds
    potential_weight = 0.3 + (position_value * 0.2) + (min(implied_odds - 1.0, 0.5) * 0.2)
    effective_strength = win_prob + (hand_potential * potential_weight)
    
    # Adjust thresholds based on SPR
    # Low SPR: commit more easily, raise/all-in thresholds lower
    # High SPR: be more selective, need stronger hands
    spr_factor = 1.0
    if spr < 4:
        spr_factor = 0.85  # Lower thresholds (more aggressive)
    elif spr > 12:
        spr_factor = 1.15  # Higher thresholds (more selective)
    
    # Position adjustment: better position = can play more hands
    position_adjustment = (position_value - 0.5) * 0.1  # ±0.05
    
    # Adjusted thresholds
    fold_threshold = (pot_odds * spr_factor) - position_adjustment
    all_in_threshold = (0.75 * spr_factor) - position_adjustment
    raise_threshold = (0.55 * spr_factor) - position_adjustment
    call_threshold = (0.35 * spr_factor) - position_adjustment
    
    # Decision logic
    if to_call > 0:
        # Facing a bet
        adjusted_odds = pot_odds / implied_odds  # Better implied odds = effectively better pot odds
        
        if effective_strength < adjusted_odds and hand_potential < 0.25:
            return "fold"
        
        if effective_strength > all_in_threshold and spr < 6:
            return "all_in"
        
        if effective_strength > raise_threshold:
            return "raise"
        
        if effective_strength > call_threshold or hand_potential > 0.3:
            return "call"
        
        return "fold"
    else:
        # No bet to call (can check or bet)
        if effective_strength > all_in_threshold and spr < 4:
            return "all_in"
        
        if effective_strength > raise_threshold:
            return "raise"
        
        # With good position and potential, can raise lighter
        if position_value > 0.6 and (effective_strength > 0.4 or hand_potential > 0.25):
            return "raise"
        
        return "call"  # Check


def score_policy(
    policy: PolicyTable,
    rng: random.Random,
    samples: int,
    scenarios: int,
    style_bucket: int,
) -> float:
    score = 0.0
    num_players = 6  # Typical table size
    
    for _ in range(scenarios):
        deck = Deck(rng)
        hole = deck.deal(2)
        stage = rng.choice([0, 1, 2, 3])
        community = deck.deal(3) if stage >= 1 else []
        if stage >= 2:
            community += deck.deal(1)
        if stage >= 3:
            community += deck.deal(1)
        stack = rng.choice([20, 50, 100, 200, 400])
        pot = rng.choice([10, 20, 40, 80, 120])
        to_call = rng.choice([0, 2, 5, 10, 20])
        position = rng.randint(0, num_players - 1)

        # Calculate all factors
        win_prob = estimate_win_rate(hole, community, rng, samples)
        pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
        hand_potential = calculate_hand_potential(hole, community, rng, samples)
        spr = calculate_spr(stack, pot)
        position_value = calculate_position_value(position, num_players)
        implied_odds = calculate_implied_odds(win_prob, hand_potential, spr, to_call, pot)
        
        optimal = optimal_action(
            win_prob=win_prob,
            pot_odds=pot_odds,
            stack=stack,
            to_call=to_call,
            hand_potential=hand_potential,
            spr=spr,
            position_value=position_value,
            implied_odds=implied_odds,
        )

        hand_bucket = hand_strength_bucket(hole, community, rng, max(5, samples // 2))
        state_key = build_state_key(stage, position, stack, pot, to_call, hand_bucket, style_bucket)
        predicted = policy.choose_action(state_key)

        if predicted == optimal:
            score += 1.0
        elif predicted in ("raise", "all_in") and optimal in ("raise", "all_in"):
            score += 0.6
        elif predicted == "call" and optimal == "call":
            score += 1.0
        else:
            score += 0.0
    return score / scenarios


def select_best_policy(
    policies: Dict[str, Dict[str, List[float]]],
    seed: int,
    samples: int,
    scenarios: int,
) -> Tuple[str, float]:
    rng = random.Random(seed)
    best_id = ""
    best_score = -1.0
    for agent_id, snapshot in policies.items():
        policy = PolicyTable(["fold", "call", "raise", "all_in"], rng)
        policy.load_snapshot(snapshot)
        style_bucket = 1 if rng.random() >= 0.5 else 0
        score = score_policy(policy, rng, samples, scenarios, style_bucket)
        if score > best_score:
            best_score = score
            best_id = agent_id
    return best_id, best_score


def rank_policies(
    policies: Dict[str, Dict[str, List[float]]],
    seed: int,
    samples: int,
    scenarios: int,
) -> List[Tuple[str, float]]:
    rng = random.Random(seed)
    ranked: List[Tuple[str, float]] = []
    for agent_id, snapshot in policies.items():
        policy = PolicyTable(["fold", "call", "raise", "all_in"], rng)
        policy.load_snapshot(snapshot)
        style_bucket = 1 if rng.random() >= 0.5 else 0
        score = score_policy(policy, rng, samples, scenarios, style_bucket)
        ranked.append((agent_id, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked


def score_policy_comprehensive(
    policy: PolicyTable,
    rng: random.Random,
    samples: int,
    style_bucket: int,
) -> float:
    """
    Comprehensive evaluation: test policy against ALL 52×51 = 2652 starting hands.
    Each hand tested with randomized stack/pot/position for realism.
    
    This is slower but much more accurate than random sampling.
    """
    score = 0.0
    total_tests = 0
    num_players = 6
    
    # Generate all possible hole card combinations
    all_cards = [Card(r, s) for r in RANKS for s in SUITS]
    
    for i, card1 in enumerate(all_cards):
        for card2 in all_cards[i + 1:]:  # Avoid duplicates and same card
            hole = [card1, card2]
            
            # Test pre-flop only (most important street, and faster)
            stage = 0
            community: List[Card] = []
            
            # Randomize game state within reasonable tournament ranges
            stack = rng.choice([30, 50, 75, 100, 150, 200])
            pot = rng.choice([3, 6, 10, 15, 20, 30])
            to_call = rng.choice([0, 2, 4, 6, 10, 15])
            position = rng.randint(0, num_players - 1)
            
            # Calculate factors
            win_prob = estimate_win_rate(hole, community, rng, max(10, samples // 5))
            pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
            hand_potential = calculate_hand_potential(hole, community, rng, samples)
            spr = calculate_spr(stack, pot)
            position_value = calculate_position_value(position, num_players)
            implied_odds = calculate_implied_odds(win_prob, hand_potential, spr, to_call, pot)
            
            optimal = optimal_action(
                win_prob=win_prob,
                pot_odds=pot_odds,
                stack=stack,
                to_call=to_call,
                hand_potential=hand_potential,
                spr=spr,
                position_value=position_value,
                implied_odds=implied_odds,
            )
            
            hand_bucket = hand_strength_bucket(hole, community, rng, max(5, samples // 4))
            state_key = build_state_key(stage, position, stack, pot, to_call, hand_bucket, style_bucket)
            predicted = policy.choose_action(state_key)
            
            if predicted == optimal:
                score += 1.0
            elif predicted in ("raise", "all_in") and optimal in ("raise", "all_in"):
                score += 0.7
            elif predicted == "call" and optimal in ("call", "raise"):
                score += 0.5
            
            total_tests += 1
    
    return score / total_tests if total_tests > 0 else 0.0


def score_policy_fast(
    policy: PolicyTable,
    rng: random.Random,
    style_bucket: int,
) -> float:
    """
    Fast evaluation using representative hand categories.
    Tests ~169 canonical hands (accounting for suits) with varied game states.
    """
    score = 0.0
    total_tests = 0
    num_players = 6
    
    # Representative hands: pairs, suited connectors, offsuit high cards, etc.
    # Group by canonical hand type (reduces 2652 -> 169 unique hand types)
    tested_types: set = set()
    all_cards = [Card(r, s) for r in RANKS for s in SUITS]
    
    for i, card1 in enumerate(all_cards):
        for card2 in all_cards[i + 1:]:
            # Canonical type: (high_rank, low_rank, suited)
            r1, r2 = max(card1.rank, card2.rank), min(card1.rank, card2.rank)
            suited = card1.suit == card2.suit
            hand_type = (r1, r2, suited)
            
            if hand_type in tested_types:
                continue
            tested_types.add(hand_type)
            
            hole = [card1, card2]
            stage = 0
            community: List[Card] = []
            
            # Test each hand type with 3 different game states
            for _ in range(3):
                stack = rng.choice([50, 100, 200])
                pot = rng.choice([5, 15, 30])
                to_call = rng.choice([0, 4, 10])
                position = rng.randint(0, num_players - 1)
                
                win_prob = estimate_win_rate(hole, community, rng, 20)
                pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
                hand_potential = calculate_hand_potential(hole, community, rng, 10)
                spr = calculate_spr(stack, pot)
                position_value = calculate_position_value(position, num_players)
                implied_odds = calculate_implied_odds(win_prob, hand_potential, spr, to_call, pot)
                
                optimal = optimal_action(
                    win_prob=win_prob, pot_odds=pot_odds, stack=stack, to_call=to_call,
                    hand_potential=hand_potential, spr=spr, position_value=position_value,
                    implied_odds=implied_odds,
                )
                
                hand_bucket = hand_strength_bucket(hole, community, rng, 10)
                state_key = build_state_key(stage, position, stack, pot, to_call, hand_bucket, style_bucket)
                predicted = policy.choose_action(state_key)
                
                if predicted == optimal:
                    score += 1.0
                elif predicted in ("raise", "all_in") and optimal in ("raise", "all_in"):
                    score += 0.7
                elif predicted == "call" and optimal in ("call", "raise"):
                    score += 0.5
                
                total_tests += 1
    
    return score / total_tests if total_tests > 0 else 0.0
