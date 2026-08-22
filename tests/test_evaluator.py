# tests/test_evaluator.py
from game.card import Card
from poker.evaluator import evaluate_hand

def test_evaluator():
    # 1. Wheel Straight 테스트 (A-2-3-4-5)
    wheel_cards = [
        Card("♠", "A"), Card("♥", "2"), Card("♦", "3"),
        Card("♣", "4"), Card("♠", "5"), Card("♥", "K"), Card("♦", "Q")
    ]
    score, kickers, name = evaluate_hand(wheel_cards)
    print(f"Wheel Straight 결과: {name}, High Card: {kickers}")

    # 2. Flush 테스트
    flush_cards = [
        Card("♠", "A"), Card("♠", "10"), Card("♠", "7"),
        Card("♠", "4"), Card("♠", "2"), Card("♥", "K"), Card("♦", "Q")
    ]
    score, kickers, name = evaluate_hand(flush_cards)
    print(f"Flush 결과: {name}, Kickers: {kickers}")

    # 3. Full House 테스트
    fullhouse_cards = [
        Card("♠", "J"), Card("♥", "J"), Card("♦", "J"),
        Card("♣", "8"), Card("♠", "8"), Card("♥", "2"), Card("♦", "3")
    ]
    score, kickers, name = evaluate_hand(fullhouse_cards)
    print(f"Full House 결과: {name}, Kickers: {kickers}")

if __name__ == "__main__":
    test_evaluator()