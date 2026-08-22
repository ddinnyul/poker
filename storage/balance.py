import json
import os

DATA_FILE = "data/balances.json"
DEFAULT_CHIPS = 1000

def _load_data():
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(DATA_FILE):
        return {}
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        # 파일이 비어있거나 올바르지 않은 형식일 경우 빈 객체 반환
        return {}

def _save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_balance(user_id: int) -> int:
    data = _load_data()
    user_id_str = str(user_id)
    return data.get(user_id_str, DEFAULT_CHIPS)

def update_balance(user_id: int, amount: int):
    """
    amount: 양수면 지급, 음수면 차감
    """
    data = _load_data()
    user_id_str = str(user_id)
    current = data.get(user_id_str, DEFAULT_CHIPS)
    data[user_id_str] = current + amount
    _save_data(data)
    return data[user_id_str]