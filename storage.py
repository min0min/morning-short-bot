import json
import os
from datetime import datetime

from config import (
    PAPER_SEED_USDT,
    DEFAULT_LEVERAGE,
    DEFAULT_ENTRY_1_PCT,
    DEFAULT_ENTRY_2_PCT,
    DEFAULT_ENTRY_3_PCT,
    DEFAULT_PUMP_THRESHOLD_PCT,
    DEFAULT_ADD_ENTRY_PRICE_MOVE_PCT,
    DEFAULT_TAKE_PROFIT_LEVERAGED_PCT,
    DEFAULT_STOP_LOSS_LEVERAGED_PCT,
)

DATA_DIR = "data"
STATE_PATH = os.path.join(DATA_DIR, "state.json")
TRADES_PATH = os.path.join(DATA_DIR, "trades.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_0900.json")
WINDOW_PATH = os.path.join(DATA_DIR, "window_0900_0915.json")

DEFAULT_STATE = {
    "running": False,
    "seed_usdt": PAPER_SEED_USDT,
    "paper_balance": PAPER_SEED_USDT,
    "open_position": None,
    "settings": {
        "entry_1_pct": DEFAULT_ENTRY_1_PCT,
        "entry_2_pct": DEFAULT_ENTRY_2_PCT,
        "entry_3_pct": DEFAULT_ENTRY_3_PCT,
        "leverage": DEFAULT_LEVERAGE,
        "pump_threshold_pct": DEFAULT_PUMP_THRESHOLD_PCT,
        "add_entry_price_move_pct": DEFAULT_ADD_ENTRY_PRICE_MOVE_PCT,
        "tp_leveraged_pct": DEFAULT_TAKE_PROFIT_LEVERAGED_PCT,
        "sl_leveraged_pct": DEFAULT_STOP_LOSS_LEVERAGED_PCT,
    },
    "updated_at": None,
}

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_state():
    ensure_data_dir()
    if not os.path.exists(STATE_PATH):
        save_state(DEFAULT_STATE.copy())
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)

    # 신규 필드 누락 방지
    changed = False
    for k, v in DEFAULT_STATE.items():
        if k not in state:
            state[k] = v
            changed = True
    for k, v in DEFAULT_STATE["settings"].items():
        if k not in state["settings"]:
            state["settings"][k] = v
            changed = True
    if changed:
        save_state(state)

    return state

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
    ensure_data_dir()
    trades = load_trades()
    trade["created_at"] = datetime.now().isoformat()
    trades.append(trade)
    with open(TRADES_PATH, "w", encoding="utf-8") as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)

def save_baseline(snapshot):
    ensure_data_dir()
    payload = {
        "saved_at": datetime.now().isoformat(),
        "snapshot": snapshot,
    }
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def load_baseline():
    ensure_data_dir()
    if not os.path.exists(BASELINE_PATH):
        return None
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_window(window):
    ensure_data_dir()
    window["updated_at"] = datetime.now().isoformat()
    with open(WINDOW_PATH, "w", encoding="utf-8") as f:
        json.dump(window, f, ensure_ascii=False, indent=2)

def load_window():
    ensure_data_dir()
    if not os.path.exists(WINDOW_PATH):
        return None
    with open(WINDOW_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def reset_window(snapshot):
    ensure_data_dir()
    now = datetime.now().isoformat()
    window = {
        "started_at": now,
        "updated_at": now,
        "symbols": {},
    }

    for base, item in snapshot.items():
        price = float(item["price"])
        window["symbols"][base] = {
            "base": base,
            "symbol": item["symbol"],
            "baseline_price": price,
            "peak_price": price,
            "last_price": price,
            "peak_time": now,
            "updated_at": now,
        }

    save_window(window)
    return window

def update_window_with_snapshot(snapshot):
    window = load_window()
    if not window:
        window = reset_window(snapshot)

    now = datetime.now().isoformat()
    symbols = window.setdefault("symbols", {})

    for base, item in snapshot.items():
        price = float(item["price"])
        if base not in symbols:
            symbols[base] = {
                "base": base,
                "symbol": item["symbol"],
                "baseline_price": price,
                "peak_price": price,
                "last_price": price,
                "peak_time": now,
                "updated_at": now,
            }
            continue

        row = symbols[base]
        row["symbol"] = item["symbol"]
        row["last_price"] = price
        row["updated_at"] = now

        if price > float(row.get("peak_price", 0)):
            row["peak_price"] = price
            row["peak_time"] = now

    save_window(window)
    return window

def get_peak_candidates(threshold_pct=3.0, include_below=False, limit=None):
    window = load_window()
    if not window:
        return [], None

    all_rows = []
    passed = []

    for base, row in window.get("symbols", {}).items():
        baseline = float(row.get("baseline_price", 0))
        peak = float(row.get("peak_price", 0))
        last = float(row.get("last_price", 0))
        if baseline <= 0:
            continue

        peak_pct = ((peak - baseline) / baseline) * 100
        last_pct = ((last - baseline) / baseline) * 100

        candidate = {
            "base": base,
            "symbol": row.get("symbol"),
            "change_pct": peak_pct,
            "last_change_pct": last_pct,
            "price": last,
            "baseline_price": baseline,
            "peak_price": peak,
            "peak_time": row.get("peak_time"),
        }
        all_rows.append(candidate)
        if peak_pct >= threshold_pct:
            passed.append(candidate)

    all_rows.sort(key=lambda x: x["change_pct"], reverse=True)
    passed.sort(key=lambda x: x["change_pct"], reverse=True)

    result = all_rows if include_below else passed
    if limit:
        result = result[:limit]

    signal = passed[0] if passed else None
    return result, signal
