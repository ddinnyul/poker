# game/game_manager.py
from typing import Dict, Optional
from game.game import Game

class GameManager:
    def __init__(self):
        # channel_id: Game
        self.games: Dict[int, Game] = {}

    def create_game(self, channel_id: int, host_id: int) -> Optional[Game]:
        """채널에 새 게임 생성 (이미 존재하면 None 반환)"""
        if channel_id in self.games:
            return None
        game = Game(channel_id=channel_id, host_id=host_id)
        self.games[channel_id] = game
        return game

    def get_game(self, channel_id: int) -> Optional[Game]:
        """채널의 게임 조회"""
        return self.games.get(channel_id)

    def remove_game(self, channel_id: int) -> bool:
        """게임 종료 및 삭제"""
        if channel_id in self.games:
            del self.games[channel_id]
            return True
        return False

# 싱글톤 인스턴스
game_manager = GameManager()