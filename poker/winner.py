# poker/winner.py
from typing import List, Dict, Any, Tuple
from game.card import Card
from poker.evaluator import evaluate_hand

def determine_winner(
    players_cards: Dict[Any, List[Card]], 
    community_cards: List[Card]
) -> Tuple[List[Any], Tuple[int, List[int], str]]:
    """
    각 플레이어의 카드와 커뮤니티 카드를 비교하여 승자(들)와 최선의 핸드 정보를 반환합니다.
    
    :param players_cards: {player_identifier: [Card, Card]} 형태의 딕셔너리
    :param community_cards: 5장의 커뮤니티 카드
    :return: (승자 목록 [player_identifier, ...], (best_rank_score, kickers, rank_name))
    """
    if len(community_cards) != 5:
        raise ValueError("승자를 결정하려면 5장의 커뮤니티 카드가 필요합니다.")
    
    best_score = (-1, [])
    best_hand_info = (0, [], "")
    winners = []

    for player_id, hole_cards in players_cards.items():
        all_cards = hole_cards + community_cards
        score, kickers, rank_name = evaluate_hand(all_cards)
        current_score = (score, kickers)

        if current_score > best_score:
            best_score = current_score
            best_hand_info = (score, kickers, rank_name)
            winners = [player_id]
        elif current_score == best_score:
            winners.append(player_id)

    return winners, best_hand_info