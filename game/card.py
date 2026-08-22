# game/card.py
import random

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUES = {rank: i for i, rank in enumerate(RANKS, start=2)}

class Card:
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        self.value = RANK_VALUES[rank]

    def __repr__(self):
        return f"{self.suit}{self.rank}"

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.rank == other.rank


class Deck:
    def __init__(self):
        self.cards = [Card(suit, rank) for suit in SUITS for rank in RANKS]

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, count: int = 1):
        if count > len(self.cards):
            raise ValueError("덱에 남아있는 카드가 부족합니다.")
        drawn = self.cards[:count]
        self.cards = self.cards[count:]
        return drawn if count > 1 else drawn[0]

    def __len__(self):
        return len(self.cards)