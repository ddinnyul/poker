# tests/test_card.py
from game.card import Deck

def test_deck():
    deck = Deck()
    print(f"초기 덱 카운트: {len(deck)}")  # 52장 확인
    
    deck.shuffle()
    print("덱을 섞었습니다.")

    # 카드 2장 뽑기 (Hole Cards)
    hole_cards = deck.draw(2)
    print(f"뽑은 카드 2장: {hole_cards}")
    print(f"남은 덱 카운트: {len(deck)}")  # 50장 확인

    # 커뮤니티 카드 3장 뽑기 (Flop)
    flop = deck.draw(3)
    print(f"플랍 카드 3장: {flop}")
    print(f"남은 덱 카운트: {len(deck)}")  # 47장 확인

if __name__ == "__main__":
    test_deck()