# game/player.py
from dataclasses import dataclass, field
from typing import List
from game.card import Card

@dataclass
class Player:
    user_id: int
    username: str
    chips: int
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: int = 0
    has_folded: bool = False
    is_all_in: bool = False

    def reset_hand(self):
        """매 판 시작 시 손패 및 베팅 상태 초기화"""
        self.hole_cards = []
        self.current_bet = 0
        self.has_folded = False
        self.is_all_in = False