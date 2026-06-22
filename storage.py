import json
import os
from datetime import datetime

DATA_DIR = "data"
STATE_PATH = os.path.join(DATA_DIR, "state.json")
TRADES_PATH = os.path.join(DATA_DIR, "trades.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_0900.json")

DEFAULT_STATE = {
    "running": False,
    "seed_usdt": 1000.0,
    "paper_balance": 1000.0,
    "open_position": None,
    "settings": {
        "entry_1_pct": 0.02,
        "entry_2_pct": 0.01,
        "entry_3_pct": 0.01,
        "leverage": 4,
        "pump_threshold_pct": 3.0,
        "add_entry_price_move_pct": 5.0,
        "tp_leveraged_pct": 12.0,
        "sl_leveraged_pct": -30.0
    },
    "updated_at": None
}

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_state():
    ensure_data_dir()
    if not os.path.exists(STATE_PATH):
        save_state(DEFAULT_STATE.copy())
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(state):
    ensure_data_dir()
    state["updated_at"] = datetime.now().isoformat()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_trades():
    ensure_data_dir()
    if not os.path.exists(TRADES_PATH):
        with open(TRADES_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    with open(TRADES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def append_trade(trade):
    trades = load_trades()
    trades.append(trade)
    with open(TRADES_PATH, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)

def save_baseline(snapshot):
    ensure_data_dir()
    payload = {
        "saved_at": datetime.now().isoformat(),
        "snapshot": snapshot
    }
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def load_baseline():
    ensure_data_dir()
    if not os.path.exists(BASELINE_PATH):
        return None
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
