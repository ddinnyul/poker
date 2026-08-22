# tests/test_winner.py
from game.card import Card
from poker.winner import determine_winner

def test_winner_determination():
    # 커뮤니티 카드
    community = [
        Card("♠", "10"), Card("♥", "J"), Card("♦", "Q"),
        Card("♣", "K"), Card("♠", "2")
    ]

    # 플레이어 카드 설정
    players = {
        "Player_A (A 스트레이트)": [Card("♠", "A"), Card("♥", "3")],  # A-K-Q-J-10 스트레이트
        "Player_B (9 스트레이트)": [Card("♦", "9"), Card("♣", "4")],  # K-Q-J-10-9 스트레이트
        "Player_C (동점 A 스트레이트)": [Card("♦", "A"), Card("♣", "5")] # A-K-Q-J-10 스트레이트
    }

    winners, (score, kickers, rank_name) = determine_winner(players, community)
    print(f"최고 족보: {rank_name} (Kickers/High Card: {kickers})")
    print(f"승자 목록: {winners}")

if __name__ == "__main__":
    test_winner_determination()