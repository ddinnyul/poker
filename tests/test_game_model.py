# tests/test_game_model.py
from game.game_manager import game_manager

def test_game_models():
    channel_1 = 1001
    channel_2 = 1002

    # 1. 채널 1에 게임 생성
    game1 = game_manager.create_game(channel_id=channel_1, host_id=111)
    print(f"채널 1001 게임 생성 성공: {game1 is not None}")

    # 2. 플레이어 참가
    game1.add_player(user_id=111, username="HostUser", chips=1000)
    game1.add_player(user_id=222, username="GuestUser", chips=1000)
    print(f"채널 1001 플레이어 수: {len(game1.players)}")

    # 3. 채널 2에 독립적인 게임 생성
    game2 = game_manager.create_game(channel_id=channel_2, host_id=333)
    game2.add_player(user_id=333, username="OtherHost", chips=1000)
    print(f"채널 1002 플레이어 수: {len(game2.players)}")

    # 4. 채널별 게임 분리 확인
    print(f"채널 1001 게임 객체와 1002 게임 객체 동일 여부: {game1 is game2}")

    # 5. 게임 제거 테스트
    game_manager.remove_game(channel_1)
    print(f"채널 1001 게임 제거 후 조회: {game_manager.get_game(channel_1)}")

if __name__ == "__main__":
    test_game_models()