"""
Card and Deck primitives for poker.

Cards use integer ranks (2-14) where 11=J, 12=Q, 13=K, 14=A.
Suits are single characters: S=Spades, H=Hearts, D=Diamonds, C=Clubs.
"""
from __future__ import annotations

from dataclasses import dataclass
import random
from typing import List

# ranks 2-14 where face cards are 11-14 (J, Q, K, A)
RANKS = list(range(2, 15))

# suit abbreviations
SUITS = ["S", "H", "D", "C"]

# display names for face cards
RANK_TO_STR = {11: "J", 12: "Q", 13: "K", 14: "A"}


@dataclass(frozen=True)
class Card:
    """A poker card."""

    rank: int
    suit: str

    def __str__(self) -> str:
        r = RANK_TO_STR.get(self.rank, str(self.rank))
        return f"{r}{self.suit}"


class Deck:
    """A deck of cards."""
    
    def __init__(self, rng: random.Random):
        self._rng = rng
        self._cards = [Card(rank, suit) for rank in RANKS for suit in SUITS]
        self.shuffle()


    # shuffle the deck
    def shuffle(self) -> None:
        self._rng.shuffle(self._cards)


    # deal n cards from the deck
    def deal(self, n: int) -> List[Card]:
        dealt = self._cards[:n]
        self._cards = self._cards[n:]
        return dealt


# helper function to format cards as a string
def format_cards(cards: List[Card]) -> str:
    return " ".join(str(c) for c in cards)
