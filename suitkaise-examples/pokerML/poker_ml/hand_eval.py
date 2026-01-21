from __future__ import annotations

# python imports
from typing import Dict, List, Tuple

# SUITKAISE IMPORTS
from suitkaise import timing

# example-specific imports
from .cards import Card


def _rank_counts(cards: List[Card]) -> Dict[int, int]:
    """
    Count occurrences of each rank in the hand.
    [Ah, Kh, Kd, Ks, 2c] -> {14: 1, 13: 3, 2: 1}
    """
    counts: Dict[int, int] = {}
    for c in cards:
        counts[c.rank] = counts.get(c.rank, 0) + 1
    return counts


def _is_straight(ranks: List[int]) -> int:
    """
    Check if ranks contain a 5-card straight.
    
    Returns the high card of the straight, or 0 if no straight.
    
    Special case: Ace can be low (A-2-3-4-5 "wheel") or high (10-J-Q-K-A).
    We handle this by adding 1 to the list when Ace (14) is present.
    """
    # get unique ranks sorted high to low
    unique = sorted(set(ranks), reverse=True)
    
    # ace can also act as 1 for the wheel (A-2-3-4-5)
    if 14 in unique:
        unique.append(1)
    
    # look for 5 consecutive cards
    run = 1
    for i in range(len(unique) - 1):
        if unique[i] - 1 == unique[i + 1]:
            # cards are consecutive, extend the run
            run += 1
            if run >= 5:
                # found a straight! Return the high card
                # (i - 3 because we're at position i and need to go back 4 spots)
                return unique[i - 3]
        else:
            # gap in sequence, reset the run
            run = 1
    return 0


@timing.timethis()
def evaluate_hand(cards: List[Card]) -> Tuple[int, List[int]]:
    """
    Evaluate best 5-card hand from 7 cards (2 hole + 5 community).

    Returns:
        (category, tiebreakers)
    category: 8 straight flush, 7 four, 6 full house, 5 flush,
              4 straight, 3 three, 2 two pair, 1 pair, 0 high
    """
    # count how many of each rank we have
    counts = _rank_counts(cards)
    
    # get unique ranks sorted high to low (for kicker comparisons)
    ranks_sorted = sorted(counts.keys(), reverse=True)

    # group cards by suit to check for flushes
    suit_groups: Dict[str, List[int]] = {}
    for c in cards:
        suit_groups.setdefault(c.suit, []).append(c.rank)

    # check if any suit has 5+ cards (flush possible)
    flush_ranks = []
    flush_suit = None
    for suit, ranks in suit_groups.items():
        if len(ranks) >= 5:
            flush_suit = suit
            flush_ranks = sorted(ranks, reverse=True)
            break

    # straight flush check (and royal flush)
    if flush_suit:
        flush_cards = [c for c in cards if c.suit == flush_suit]
        sf_high = _is_straight([c.rank for c in flush_cards])
        if sf_high:
            return (8, [sf_high])

    # four of a kind check
    four = [r for r, c in counts.items() if c == 4]
    if four:
        four_rank = max(four)
        # kicker is the highest remaining card
        kickers = [r for r in ranks_sorted if r != four_rank]
        return (7, [four_rank] + kickers[:1])

    # full house check
    three = sorted([r for r, c in counts.items() if c == 3], reverse=True)
    pairs = sorted([r for r, c in counts.items() if c == 2], reverse=True)

    if three and pairs:
        return (6, [three[0], pairs[0]])
    if len(three) >= 2:
        # if two three of a kinds, use the lower one as the pair
        return (6, [three[0], three[1]])

    # regular flush check
    if flush_ranks:
        return (5, flush_ranks[:5])

    # straight check
    straight_high = _is_straight([c.rank for c in cards])
    if straight_high:
        return (4, [straight_high])

    # 3 of a kind check
    if three:
        kickers = [r for r in ranks_sorted if r != three[0]]
        return (3, [three[0]] + kickers[:2])

    # 2 pair check
    if len(pairs) >= 2:
        high, low = pairs[:2]
        kicker = [r for r in ranks_sorted if r not in (high, low)]
        return (2, [high, low] + kicker[:1])

    # pair check
    if len(pairs) == 1:
        pair = pairs[0]
        kickers = [r for r in ranks_sorted if r != pair]
        return (1, [pair] + kickers[:3])

    # high card
    return (0, ranks_sorted[:5])


def compare_hands(hand_a: Tuple[int, List[int]], hand_b: Tuple[int, List[int]]) -> int:
    """
    Compare two evaluated hands.
    
    Returns:
        1 if hand_a wins, -1 if hand_b wins, 0 if tie
    """
    # compare hand categories (flush beats straight, etc.)
    if hand_a[0] != hand_b[0]:
        return 1 if hand_a[0] > hand_b[0] else -1
    
    # same category for tiebreakers
    for a, b in zip(hand_a[1], hand_b[1]):
        if a != b:
            return 1 if a > b else -1
    
    # if exact tie
    return 0
