# poker/evaluator.py
from itertools import combinations
from typing import List, Tuple
from game.card import Card, RANK_VALUES

# 족보 순위 상수 (숫자가 높을수록 높은 족보)
HAND_RANKS = {
    "High Card": 1,
    "One Pair": 2,
    "Two Pair": 3,
    "Three of a Kind": 4,
    "Straight": 5,
    "Flush": 6,
    "Full House": 7,
    "Four of a Kind": 8,
    "Straight Flush": 9,
    "Royal Flush": 10,
}

def evaluate_5cards(cards: List[Card]) -> Tuple[int, List[int]]:
    """
    정확히 5장의 카드를 받아 (족보 점수, [Kicker 순위 리스트]) 튜플을 반환합니다.
    """
    ranks = sorted([c.value for c in cards], reverse=True)
    suits = [c.suit for c in cards]
    
    is_flush = len(set(suits)) == 1
    
    # Straight 검사
    unique_ranks = sorted(list(set(ranks)), reverse=True)
    is_straight = False
    straight_high = 0
    
    if len(unique_ranks) == 5:
        # 일반 스트레이트 (예: 10, 9, 8, 7, 6)
        if unique_ranks[0] - unique_ranks[4] == 4:
            is_straight = True
            straight_high = unique_ranks[0]
        # Wheel 스트레이트 (A, 5, 4, 3, 2 -> A는 14, 5는 5)
        elif unique_ranks == [14, 5, 4, 3, 2]:
            is_straight = True
            straight_high = 5  # Wheel에서 가장 높은 카드는 5

    # 랭크별 빈도수 계산
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    # (빈도수 내림차순, 랭크값 내림차순) 정렬
    sorted_counts = sorted(
        rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True
    )

    # 1. Royal Flush / Straight Flush
    if is_flush and is_straight:
        if straight_high == 14:
            return HAND_RANKS["Royal Flush"], [14]
        return HAND_RANKS["Straight Flush"], [straight_high]

    # 2. Four of a Kind
    if sorted_counts[0][1] == 4:
        four_rank = sorted_counts[0][0]
        kicker = sorted_counts[1][0]
        return HAND_RANKS["Four of a Kind"], [four_rank, kicker]

    # 3. Full House
    if sorted_counts[0][1] == 3 and sorted_counts[1][1] == 2:
        three_rank = sorted_counts[0][0]
        pair_rank = sorted_counts[1][0]
        return HAND_RANKS["Full House"], [three_rank, pair_rank]

    # 4. Flush
    if is_flush:
        return HAND_RANKS["Flush"], ranks

    # 5. Straight
    if is_straight:
        return HAND_RANKS["Straight"], [straight_high]

    # 6. Three of a Kind
    if sorted_counts[0][1] == 3:
        three_rank = sorted_counts[0][0]
        kickers = [r for r, _ in sorted_counts[1:]]
        return HAND_RANKS["Three of a Kind"], [three_rank] + sorted(kickers, reverse=True)

    # 7. Two Pair
    if sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:
        high_pair = max(sorted_counts[0][0], sorted_counts[1][0])
        low_pair = min(sorted_counts[0][0], sorted_counts[1][0])
        kicker = sorted_counts[2][0]
        return HAND_RANKS["Two Pair"], [high_pair, low_pair, kicker]

    # 8. One Pair
    if sorted_counts[0][1] == 2:
        pair_rank = sorted_counts[0][0]
        kickers = [r for r, _ in sorted_counts[1:]]
        return HAND_RANKS["One Pair"], [pair_rank] + sorted(kickers, reverse=True)

    # 9. High Card
    return HAND_RANKS["High Card"], ranks


def evaluate_hand(cards: List[Card]) -> Tuple[int, List[int], str]:
    """
    5장 이상의 카드(보통 7장)를 받아 최선의 5장 조합 평가 결과를 반환합니다.
    반환값: (족보 점수, Kicker 리스트, 족보 이름)
    """
    if len(cards) < 5:
        raise ValueError("최소 5장의 카드가 필요합니다.")

    best_score = (-1, [])
    
    # 5장 조합 중 가장 높은 족보 찾기
    for combo in combinations(cards, 5):
        score = evaluate_5cards(list(combo))
        if score > best_score:
            best_score = score

    # 족보 이름 역매핑
    rank_name = [name for name, score in HAND_RANKS.items() if score == best_score[0]][0]
    return best_score[0], best_score[1], rank_name