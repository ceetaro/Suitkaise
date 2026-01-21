"""
Policy logic for poker agents.

Contains:
  - State key building (discretizing game state for lookup)
  - PolicyTable class (learned weights for action selection)
  - Hand strength calculations (win rate, potential, SPR, implied odds)
  - Optimal action logic (the "teacher" that agents learn from)
  - Policy scoring functions
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Tuple

from .cards import Card, Deck, RANKS, SUITS
from .hand_eval import evaluate_hand, compare_hands

# state key building

def _bucket(value: float, thresholds: List[float]) -> int:
    """
    Convert continuous value to discrete bucket.
    Returns index of first threshold that value is <= to, or len(thresholds) if above all.
    """
    for idx, t in enumerate(thresholds):
        if value <= t:
            return idx
    return len(thresholds)


def build_state_key(
    stage: int,          # 0=preflop, 1=flop, 2=turn, 3=river
    position: int,       # 0-5 seat position
    stack: int,          # chips remaining
    pot: int,            # current pot size
    to_call: int,        # amount to call
    hand_bucket: int,    # hand strength category (0-5)
    style_bucket: int,   # play style (0=passive, 1=aggressive)
) -> Tuple[int, ...]:
    """
    Build a hashable state key from game state.
    
    We bucket continuous values to reduce state space:
    - stack: [0-20, 21-50, 51-100, 101-200, 200+] = 5 buckets
    - pot odds: [0-10%, 10-20%, 20-30%, 30-50%, 50%+] = 5 buckets
    """
    stack_bucket = _bucket(stack, [20, 50, 100, 200])
    pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
    pot_bucket = _bucket(pot_odds, [0.1, 0.2, 0.3, 0.5])
    return (stage, position, stack_bucket, pot_bucket, hand_bucket, style_bucket)


def hand_strength_bucket(
    hole: List[Card],
    community: List[Card],
    rng: random.Random,
    samples: int
) -> int:
    """
    Categorize hand strength into buckets (0-5).
    
    Pre-flop: Uses simple hand categories (pairs, suited connectors, etc.)
    Post-flop: Uses monte carlo simulation to estimate win rate.
    """
    if not community:
        # pre-flop: use hand category heuristics
        ranks = sorted([c.rank for c in hole], reverse=True)
        suited = hole[0].suit == hole[1].suit
        
        if ranks[0] == ranks[1]:         # pair
            return 5
        if suited and ranks[0] >= 11 and ranks[1] >= 10:  # suited broadway
            return 4
        if ranks[0] >= 13:               # ace or king high
            return 3
        if suited and abs(ranks[0] - ranks[1]) <= 2:      # suited connector
            return 2
        return 1                         # weak hand

    # post-flop: monte carlo simulation against random opponent hands
    base_hand = evaluate_hand(hole + community)
    strength = base_hand[0]
    
    if samples <= 0:
        # no simulation, just use hand category
        return _bucket(strength, [1, 2, 3, 4, 5])

    # simulate vs random opponent hands to estimate win rate
    wins = 0
    for _ in range(samples):
        # build deck without known cards
        deck = [Card(r, s) for r in RANKS for s in SUITS if Card(r, s) not in hole + community]
        rng.shuffle(deck)
        
        # deal random opponent hole cards
        opp_hole = deck[:2]
        
        # complete the board if needed
        needed = 5 - len(community)
        board = community + deck[2:2 + needed]
        
        # compare hands
        my_hand = evaluate_hand(hole + board)
        opp_hand = evaluate_hand(opp_hole + board)
        if compare_hands(my_hand, opp_hand) >= 0:
            wins += 1
    
    win_rate = wins / samples
    return _bucket(win_rate, [0.2, 0.4, 0.6, 0.8])


# policy table
#
# How action selection works:
#
#   Each state has a list of weights, one per action. Example:
#     weights = [0.2, 0.8, 0.3, -0.1]  # for [fold, call, raise, all_in]
#
#   SOFTMAX (used during training - exploration):
#     Converts weights to probabilities so we can randomly sample.
#     Higher weights = higher probability, but ALL actions have SOME chance.
#     This lets the agent try new things and learn from mistakes.
#
#     Example: weights [0.2, 0.8, 0.3, -0.1] → probabilities [0.21, 0.38, 0.23, 0.16]
#     Even the worst action (all_in at 16%) can be chosen sometimes.
#
#   ARGMAX (used during evaluation - exploitation):
#     Simply picks the action with the highest weight. No randomness.
#     This shows what the agent actually learned.
#
#     Example: weights [0.2, 0.8, 0.3, -0.1] → always picks "call" (0.8 is highest)
#
class PolicyTable:
    """
    A simple policy table that maps state keys to action weights.
    
    Each state key (tuple of ints) maps to a list of weights, one per action.
    Higher weight = more likely to be chosen.
    """
    
    def __init__(self, actions: List[str], rng: random.Random):
        self._actions = actions      # ["fold", "call", "raise", "all_in"]
        self._rng = rng
        self._table: Dict[Tuple[int, ...], List[float]] = {}

    def _init_weights(self) -> List[float]:
        """Initialize random weights for a new state key."""
        return [self._rng.uniform(-0.5, 0.5) for _ in self._actions]

    def get_weights(self, key: Tuple[int, ...]) -> List[float]:
        """Get weights for a state, initializing if first time seeing this state."""
        if key not in self._table:
            self._table[key] = self._init_weights()
        return self._table[key]

    def choose_action(self, key: Tuple[int, ...]) -> str:
        """
        SOFTMAX: randomly sample an action, weighted by learned preferences.
        Used during training so the agent explores different actions.
        """
        weights = self.get_weights(key)
        
        # convert weights to probabilities using softmax formula
        # subtract max first to prevent math overflow with large numbers
        max_w = max(weights)
        exps = [math.exp(w - max_w) for w in weights]
        total = sum(exps)
        probs = [e / total for e in exps]
        
        # randomly pick action according to probabilities
        pick = self._rng.random()
        cumulative = 0.0
        for action, p in zip(self._actions, probs):
            cumulative += p
            if pick <= cumulative:
                return action
        return self._actions[-1]

    def best_action(self, key: Tuple[int, ...]) -> str:
        """
        ARGMAX: pick the action with the highest weight, no randomness.
        Used during evaluation to see what the agent actually learned.
        """
        weights = self.get_weights(key)
        best_idx = weights.index(max(weights))
        return self._actions[best_idx]

    def update(self, key: Tuple[int, ...], action: str, reward: float, lr: float) -> None:
        """
        Update weight for an action based on reward.
        
        weight[action] += learning_rate * reward
        Positive reward = increase weight (more likely next time)
        Negative reward = decrease weight (less likely next time)
        """
        weights = self.get_weights(key)
        idx = self._actions.index(action)
        weights[idx] += lr * reward

    def snapshot(self) -> Dict[str, List[float]]:
        """Export policy as serializable dict (keys as strings)."""
        return {";".join(map(str, k)): v[:] for k, v in self._table.items()}

    def load_snapshot(self, snapshot: Dict[str, List[float]]) -> None:
        """Load policy from serialized dict."""
        self._table = {tuple(int(x) for x in k.split(";")): v[:] for k, v in snapshot.items()}


# hand strength calculations with monte carlo simulation
#
# What is Monte Carlo?
#
#   Monte Carlo is a technique for estimating outcomes when there's too much
#   randomness to calculate exactly. Instead of computing every possibility,
#   we run many random trials and average the results.
#
#   In poker: There are millions of possible opponent hands and board runouts.
#   Instead of checking them all, we:
#     1. Randomly deal an opponent hand
#     2. Randomly complete the board
#     3. See who wins
#     4. Repeat N times (e.g., 50 samples)
#     5. Win rate ≈ wins / N
#
#   More samples = more accurate, but slower. Balance speed vs accuracy.

def estimate_win_rate(
    hole: List[Card],
    community: List[Card],
    rng: random.Random,
    samples: int
) -> float:
    """
    Estimate probability of winning against a random opponent hand.
    
    Uses monte carlo simulation:
    1. Remove known cards from deck
    2. Deal random opponent hole cards
    3. Complete the board if needed
    4. Compare hands and count wins/ties
    
    Returns win rate as 0.0-1.0 (ties count as 0.5 wins)
    """
    wins = 0
    ties = 0
    
    for _ in range(samples):
        # build deck without known cards
        deck = [Card(r, s) for r in RANKS for s in SUITS if Card(r, s) not in hole + community]
        rng.shuffle(deck)
        
        # deal opponent's hole cards
        opp_hole = deck[:2]
        
        # complete community cards if needed
        needed = 5 - len(community)
        board = community + deck[2:2 + needed]
        
        # evaluate and compare hands
        my_hand = evaluate_hand(hole + board)
        opp_hand = evaluate_hand(opp_hole + board)
        cmp = compare_hands(my_hand, opp_hand)
        
        if cmp > 0:
            wins += 1
        elif cmp == 0:
            ties += 1
    
    # ties count as half a win (split pot)
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
        return 0.0  # no more cards coming
    
    if len(community) == 0:
        # pre-flop: estimate based on hand type
        ranks = sorted([c.rank for c in hole], reverse=True)
        suited = hole[0].suit == hole[1].suit
        connected = abs(ranks[0] - ranks[1]) <= 2
        
        potential = 0.3  # base potential
        if suited:
            potential += 0.15  # flush draw potential
        if connected:
            potential += 0.1  # straight draw potential
        if ranks[0] >= 12:  # high cards
            potential += 0.1
        return min(potential, 1.0)
    
    all_cards = hole + community
    
    # check for flush draw
    suit_counts: Dict[str, int] = {}
    for card in all_cards:
        suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1
    flush_draw = any(count == 4 for count in suit_counts.values())
    
    # check for straight draw
    ranks = sorted(set(c.rank for c in all_cards))
    straight_draw = False

    # open-ended: 4 consecutive cards
    for i in range(len(ranks) - 3):
        if ranks[i+3] - ranks[i] == 3:
            straight_draw = True
            break

    # gutshot: 4 cards with one gap
    if not straight_draw:
        for i in range(len(ranks) - 3):
            if ranks[i+3] - ranks[i] == 4:
                straight_draw = True
                break
    
    # count overcards (hole cards higher than board)
    if community:
        board_high = max(c.rank for c in community)
        overcards = sum(1 for c in hole if c.rank > board_high)
    else:
        overcards = 0
    
    # calculate potential score
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
        return 20.0  # max spr
    return min(stack / pot, 20.0)


def calculate_implied_odds(win_prob: float, hand_potential: float, spr: float, to_call: int, pot: int) -> float:
    """
    Implied odds factor: how much more can we win if we hit?
    Higher SPR + higher potential = better implied odds.
    Returns a multiplier (1.0 = break even, >1.0 = profitable).
    """
    if to_call <= 0:
        return 1.5  # no cost to see more cards
    
    # base: pot odds
    immediate_odds = pot / to_call if to_call > 0 else float('inf')
    
    # potential future winnings based on SPR and hand potential
    # if we hit our draw, we can win more with deeper stacks
    future_value = hand_potential * min(spr, 10) * 0.3
    
    # combine immediate odds with future value
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


# optimal action

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
    Determine the mathematically optimal action.
    
    This is the "teacher" function that agents try to learn.
    It uses poker math to decide the best play based on:
    
    - win_prob: current hand strength (0-1)
    - pot_odds: cost to call vs pot size (0-1)
    - stack: chips remaining
    - to_call: amount needed to call
    - hand_potential: chance to improve (0-1)
    - spr: stack-to-pot ratio (commitment indicator)
    - position_value: positional advantage (0-1)
    - implied_odds: future winnings multiplier
    
    Returns: "fold", "call", "raise", or "all_in"
    """
    
    # effective strength = current strength + weighted potential
    # weight potential more when we have position and good implied odds
    potential_weight = 0.3 + (position_value * 0.2) + (min(implied_odds - 1.0, 0.5) * 0.2)
    effective_strength = win_prob + (hand_potential * potential_weight)
    
    # spr adjusts how easily we commit chips
    # low spr (<4): short stacked, commit easier
    # high spr (>12): deep stacked, need stronger hands
    spr_factor = 1.0
    if spr < 4:
        spr_factor = 0.85  # lower thresholds = more aggressive
    elif spr > 12:
        spr_factor = 1.15  # higher thresholds = more selective
    
    # position adjustment: late position can play more hands
    position_adjustment = (position_value - 0.5) * 0.1  # ±0.05
    
    # calculate action thresholds
    fold_threshold = (pot_odds * spr_factor) - position_adjustment
    all_in_threshold = (0.75 * spr_factor) - position_adjustment
    raise_threshold = (0.55 * spr_factor) - position_adjustment
    call_threshold = (0.35 * spr_factor) - position_adjustment
    
    # decision logic when facing a bet
    if to_call > 0:

        # better implied odds effectively improve our pot odds
        adjusted_odds = pot_odds / implied_odds
        
        # fold: weak hand with no potential
        if effective_strength < adjusted_odds and hand_potential < 0.25:
            return "fold"
        
        # all-in: very strong hand + short stacked
        if effective_strength > all_in_threshold and spr < 6:
            return "all_in"
        
        # raise: strong hand
        if effective_strength > raise_threshold:
            return "raise"
        
        # call: decent hand or drawing hand
        if effective_strength > call_threshold or hand_potential > 0.3:
            return "call"
        
        return "fold"
    
    # decision logic when checked to us (can check or bet)
    else:

        # all-in: monster hand + very short stacked
        if effective_strength > all_in_threshold and spr < 4:
            return "all_in"
        
        # bet/raise: strong hand
        if effective_strength > raise_threshold:
            return "raise"
        
        # bet lighter with position or draws
        if position_value > 0.6 and (effective_strength > 0.4 or hand_potential > 0.25):
            return "raise"
        
        return "call"  # check


# policy scoring

def score_policy(
    policy: PolicyTable,
    rng: random.Random,
    samples: int,
    scenarios: int,
    style_bucket: int,
) -> float:
    """
    Score a policy by testing it against random scenarios.
    
    For each scenario:
    1. Generate random hole cards, community, pot, stack, etc.
    2. Calculate the optimal action using poker math
    3. Compare to what the policy would choose
    4. Award points for matching (partial credit for close matches)
    
    Returns average score across all scenarios (0.0-1.0)
    """
    score = 0.0
    num_players = 6  # typical table size
    
    # generate random scenarios
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

        # calculate everything in order to then calculate the optimal action
        win_prob = estimate_win_rate(hole, community, rng, samples)
        pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
        hand_potential = calculate_hand_potential(hole, community, rng, samples)
        spr = calculate_spr(stack, pot)
        position_value = calculate_position_value(position, num_players)
        implied_odds = calculate_implied_odds(win_prob, hand_potential, spr, to_call, pot)
        
        # calculate the optimal action
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

        # choose an action based on the state key
        hand_bucket = hand_strength_bucket(hole, community, rng, max(5, samples // 2))
        state_key = build_state_key(stage, position, stack, pot, to_call, hand_bucket, style_bucket)
        predicted = policy.choose_action(state_key)

        # score the action
        if predicted == optimal:
            score += 1.0
        elif predicted in ("raise", "all_in") and optimal in ("raise", "all_in"):
            score += 0.6
        elif predicted == "call" and optimal == "call":
            score += 1.0
        else:
            score += 0.0
    return score / scenarios


# select the best policy
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


# rank policies
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


# test policy against all possible starting hands at all stages
def score_policy_comprehensive(
    policy: PolicyTable,
    rng: random.Random,
    samples: int,
    style_bucket: int,
) -> float:
    """
    Comprehensive evaluation: test policy against ALL 2652 starting hands
    at ALL 4 stages (pre-flop, flop, turn, river).
    
    This is the most thorough test but also the slowest.
    Total tests = 2652 hands × 4 stages = 10,608 scenarios.
    """
    score = 0.0
    total_tests = 0
    num_players = 6
    
    # generate all possible hole card combinations (52 choose 2 = 1326, but ordered = 2652)
    all_cards = [Card(r, s) for r in RANKS for s in SUITS]
    
    for i, card1 in enumerate(all_cards):
        for card2 in all_cards[i + 1:]:  # avoid duplicates and same card
            hole = [card1, card2]
            
            # test at all 4 stages with progressive community cards
            for stage in [0, 1, 2, 3]:
                # generate random community cards for this stage
                # (excluding hole cards from the deck)
                remaining_deck = [c for c in all_cards if c not in hole]
                rng.shuffle(remaining_deck)
                
                if stage == 0:    # pre-flop: no community cards
                    community = []
                elif stage == 1:  # flop: 3 cards
                    community = remaining_deck[:3]
                elif stage == 2:  # turn: 4 cards
                    community = remaining_deck[:4]
                else:             # river: 5 cards
                    community = remaining_deck[:5]
                
                # randomize game state within reasonable tournament ranges
                stack = rng.choice([30, 50, 75, 100, 150, 200])
                pot = rng.choice([3, 6, 10, 15, 20, 30])
                to_call = rng.choice([0, 2, 4, 6, 10, 15])
                position = rng.randint(0, num_players - 1)
                
                # calculate all the factors
                win_prob = estimate_win_rate(hole, community, rng, max(10, samples // 5))
                pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
                hand_potential = calculate_hand_potential(hole, community, rng, samples)
                spr = calculate_spr(stack, pot)
                position_value = calculate_position_value(position, num_players)
                implied_odds = calculate_implied_odds(win_prob, hand_potential, spr, to_call, pot)
                
                # get the optimal action
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
                
                # get the policy's prediction
                hand_bucket = hand_strength_bucket(hole, community, rng, max(5, samples // 4))
                state_key = build_state_key(stage, position, stack, pot, to_call, hand_bucket, style_bucket)
                predicted = policy.choose_action(state_key)
                
                # score: 1.0 for exact match, partial credit for close
                if predicted == optimal:
                    score += 1.0
                elif predicted in ("raise", "all_in") and optimal in ("raise", "all_in"):
                    score += 0.7  # aggressive moves are similar
                elif predicted == "call" and optimal in ("call", "raise"):
                    score += 0.5  # call when should raise is okay-ish
                
                total_tests += 1
    
    return score / total_tests if total_tests > 0 else 0.0


# fast scoring using canonical hands only
def score_policy_fast(
    policy: PolicyTable,
    rng: random.Random,
    style_bucket: int,
) -> float:
    """
    Fast evaluation using 169 canonical hands instead of all 2652.
    
    Why 169? In poker, many hands are strategically equivalent:
      - A♠K♠ plays the same as A♥K♥ (both are "AKs" = ace-king suited)
      - A♠K♥ plays the same as A♦K♣ (both are "AKo" = ace-king offsuit)
    
    So we group hands into canonical types:
      - 13 pairs (AA, KK, QQ, ..., 22)
      - 78 suited combos (AKs, AQs, ..., 32s)
      - 78 offsuit combos (AKo, AQo, ..., 32o)
      = 169 total
    
    Tests each canonical hand 3 times with different stacks/pots/positions.
    Total tests = 169 × 3 = 507 (vs 10,608 for comprehensive).
    """
    score = 0.0
    total_tests = 0
    num_players = 6
    
    # track which canonical types we've already tested
    # key = (high_rank, low_rank, is_suited)
    tested_types: set = set()
    all_cards = [Card(r, s) for r in RANKS for s in SUITS]
    
    for i, card1 in enumerate(all_cards):
        for card2 in all_cards[i + 1:]:
            # convert to canonical type: (high_rank, low_rank, suited)
            r1, r2 = max(card1.rank, card2.rank), min(card1.rank, card2.rank)
            suited = card1.suit == card2.suit
            hand_type = (r1, r2, suited)
            
            # skip if we already tested this canonical type
            if hand_type in tested_types:
                continue
            tested_types.add(hand_type)
            
            hole = [card1, card2]
            
            # test pre-flop only for speed (post-flop adds too much variance)
            stage = 0
            community: List[Card] = []
            
            # test same hand with 3 different game states
            for _ in range(3):
                stack = rng.choice([50, 100, 200])
                pot = rng.choice([5, 15, 30])
                to_call = rng.choice([0, 4, 10])
                position = rng.randint(0, num_players - 1)
                
                # calculate all the factors
                win_prob = estimate_win_rate(hole, community, rng, 20)
                pot_odds = 0.0 if to_call == 0 else to_call / max(pot + to_call, 1)
                hand_potential = calculate_hand_potential(hole, community, rng, 10)
                spr = calculate_spr(stack, pot)
                position_value = calculate_position_value(position, num_players)
                implied_odds = calculate_implied_odds(win_prob, hand_potential, spr, to_call, pot)
                
                # get optimal action
                optimal = optimal_action(
                    win_prob=win_prob, pot_odds=pot_odds, stack=stack, to_call=to_call,
                    hand_potential=hand_potential, spr=spr, position_value=position_value,
                    implied_odds=implied_odds,
                )
                
                # get policy's prediction
                hand_bucket = hand_strength_bucket(hole, community, rng, 10)
                state_key = build_state_key(stage, position, stack, pot, to_call, hand_bucket, style_bucket)
                predicted = policy.choose_action(state_key)
                
                # score with partial credit
                if predicted == optimal:
                    score += 1.0
                elif predicted in ("raise", "all_in") and optimal in ("raise", "all_in"):
                    score += 0.7
                elif predicted == "call" and optimal in ("call", "raise"):
                    score += 0.5
                
                total_tests += 1
    
    return score / total_tests if total_tests > 0 else 0.0
