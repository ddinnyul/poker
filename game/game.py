# game/game.py 파일 내부의 Game 클래스에 아래 메서드를 추가/수정합니다.
# (기존 필드 구조를 유지하며 아래 메서드들을 내부에 포함시켜 주세요)

import random
from game.card import Deck

# game/game.py 클래스 내부에 아래 필드와 메서드들을 추가/수정합니다.

class Game:
    def __init__(self, channel_id, host_id):
        self.channel_id = channel_id
        self.host_id = host_id
        self.players = {}  # {user_id: Player}
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.phase = "WAITING"
        
        self.player_order = []    
        self.btn_index = 0        
        self.sb_amount = 10       
        self.bb_amount = 20       
        
        # STEP 9 추가 필드
        self.current_turn_index = 0  # 현재 액션을 해야 하는 플레이어의 인덱스
        self.last_raiser_id = None   # 마지막으로 레이즈를 한 사람 (라운드 종료 판정용)
        self.action_counter = 0      # 라운드 내 총 액션 횟수

    def initialize_round(self):
        """기존 코드 유지 및 베팅 차례 초기화 설정 추가"""
        self.deck = Deck()
        self.deck.shuffle()
        self.community_cards = []
        self.pot = 0
        self.player_order = list(self.players.keys())
        self.action_counter = 0
        
        if self.phase == "PREFLOP":
            self.btn_index = random.randint(0, len(self.player_order) - 1)
            
        num_players = len(self.player_order)
        
        if num_players == 2:
            sb_index = self.btn_index
            bb_index = (self.btn_index + 1) % num_players
        else:
            sb_index = (self.btn_index + 1) % num_players
            bb_index = (self.btn_index + 2) % num_players
            
        sb_id = self.player_order[sb_index]
        bb_id = self.player_order[bb_index]
        
        # 블라인드 칩 차감
        sb_player = self.players[sb_id]
        actual_sb = min(sb_player.chips, self.sb_amount)
        sb_player.chips -= actual_sb
        sb_player.current_bet = actual_sb
        self.pot += actual_sb
        
        bb_player = self.players[bb_id]
        actual_bb = min(bb_player.chips, self.bb_amount)
        bb_player.chips -= actual_bb
        bb_player.current_bet = actual_bb
        self.pot += actual_bb
        
        self.current_bet = self.bb_amount
        self.last_raiser_id = bb_id  # 프리플롭에서 BB가 마지막 옵션을 가짐
        
        # 프리플롭 첫 액션 위치: BB 다음 사람 (헤즈업이면 딜러/스몰인 BTN 차례)
        if num_players == 2:
            self.current_turn_index = sb_index
        else:
            self.current_turn_index = (bb_index + 1) % num_players
            
        return sb_id, bb_id

    def get_current_player(self):
        """현재 차례의 플레이어 객체를 반환합니다."""
        p_id = self.player_order[self.current_turn_index]
        return self.players[p_id]

    def next_turn(self):
        """폴드했거나 올인한 사람을 건너뛰고 다음 플레이어에게 차례를 넘깁니다."""
        num_players = len(self.player_order)
        for _ in range(num_players):
            self.current_turn_index = (self.current_turn_index + 1) % num_players
            next_player = self.get_current_player()
            if not next_player.has_folded and not next_player.is_all_in:
                return True
        return False

    def is_betting_round_over(self):
        """모든 유저가 동일한 금액을 베팅했거나 폴드하여 라운드가 끝났는지 체크합니다."""
        active_players = [p for p in self.players.values() if not p.has_folded and not p.is_all_in]

        # 액션할 수 있는 사람이 없으면(전원 올인 등) 더 이상 액션을 받을 필요 없음
        if len(active_players) == 0:
            return True

        # 액션이 최소 한 바퀴는 돌아야 하므로, "액션 가능한 인원수"보다 액션 횟수가 적으면 종료 불가능
        # (주의: 폴드/올인한 사람은 더 이상 액션을 하지 않으므로 전체 인원(len(self.players))이 아니라
        #  active_players 기준으로 계산해야 함. 안 그러면 누가 폴드했을 때 남은 사람에게
        #  불필요하게 체크를 한 번 더 요구하는 버그가 생김)
        if self.action_counter < len(active_players):
            return False

        # 살아있는 모든 플레이어의 현재 라운드 베팅 금액이 테이블 최고 베팅과 같은지 확인
        for p in active_players:
            if p.current_bet != self.current_bet:
                return False
        return True

    # game/game.py 클래스 내부에 기존 deal_flop을 제거하거나 아래 코드로 대체/확장합니다.

    # game/game.py 파일의 advance_phase 함수 부분을 아래 코드로 덮어쓰기 하세요.

    def advance_phase(self):
        """베팅이 끝났을 때 다음 게임 페이즈(FLOP -> TURN -> RIVER -> SHOWDOWN)로 자동 전환합니다."""
        if self.phase == "PREFLOP":
            self.phase = "FLOP"
            self.deck.draw(1)  # 버닝 (Burn)
            self.community_cards.extend(self.deck.draw(3))  # 3장 오픈
        elif self.phase == "FLOP":
            self.phase = "TURN"
            self.deck.draw(1)  # 버닝
            # [버그 해결 포인트] draw(1)이 단일 객체를 반환하므로 [] 리스트로 감싸서 extend 처리합니다.
            cards = self.deck.draw(1)
            self.community_cards.extend(cards if isinstance(cards, list) else [cards])
        elif self.phase == "TURN":
            self.phase = "RIVER"
            self.deck.draw(1)  # 버닝
            # [버그 해결 포인트] 위와 동일하게 안전 장치 처리
            cards = self.deck.draw(1)
            self.community_cards.extend(cards if isinstance(cards, list) else [cards])
        elif self.phase == "RIVER":
            self.phase = "SHOWDOWN"
            return True
            
        # 보드판 및 라운드 베팅 상태 리셋
        self.current_bet = 0
        self.action_counter = 0
        self.last_raiser_id = None
        for p in self.players.values():
            p.current_bet = 0

        # 포지션 첫 차례 리셋 (스몰 블라인드가 살아있으면 SB 우선, 2인은 BB 우선)
        num_players = len(self.player_order)
        if num_players == 2:
            sb_index = self.btn_index
            self.current_turn_index = (sb_index + 1) % num_players
        else:
            self.current_turn_index = (self.btn_index + 1) % num_players
            
        # 첫 차례 유저가 죽었거나 올인이면 다음 생존자로 패스
        current_player = self.get_current_player()
        if current_player.has_folded or current_player.is_all_in:
            self.next_turn()
            
        return False



