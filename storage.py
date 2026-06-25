import json
import os
from datetime import datetime

DATA_DIR = "data"
STATE_PATH = os.path.join(DATA_DIR, "state.json")
TRADES_PATH = os.path.join(DATA_DIR, "trades.json")
BASELINE_PATH = os.path.join(DATA_DIR, "baseline_0900.json")
WINDOW_PATH = os.path.join(DATA_DIR, "window_0900_0915.json")

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
    payload = {"saved_at": datetime.now().isoformat(), "snapshot": snapshot}
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
    window = {"started_at": now, "updated_at": now, "symbols": {}}
    for base, item in snapshot.items():
        price = float(item["price"])
        window["symbols"][base] = {
            "base": base,
            "symbol": item["symbol"],
            "baseline_price": price,
            "peak_price": price,
            "last_price": price,
            "peak_time": now,
            "updated_at": now
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
                "updated_at": now
            }
            continue

        s = symbols[base]
        s["last_price"] = price
        s["symbol"] = item["symbol"]
        s["updated_at"] = now

        if price > float(s.get("peak_price", 0)):
            s["peak_price"] = price
            s["peak_time"] = now

    save_window(window)
    return window

def get_peak_candidates(threshold_pct=3.0):
    window = load_window()
    if not window:
        return [], None

    candidates = []
    for base, s in window.get("symbols", {}).items():
        baseline = float(s.get("baseline_price", 0))
        peak = float(s.get("peak_price", 0))
        last = float(s.get("last_price", 0))
        if baseline <= 0:
            continue

        peak_pct = ((peak - baseline) / baseline) * 100
        last_pct = ((last - baseline) / baseline) * 100

        if peak_pct >= threshold_pct:
            candidates.append({
                "base": base,
                "symbol": s.get("symbol"),
                "change_pct": peak_pct,
                "last_change_pct": last_pct,
                "price": last,
                "baseline_price": baseline,
                "peak_price": peak,
                "peak_time": s.get("peak_time")
            })

    candidates.sort(key=lambda x: x["change_pct"], reverse=True)
    signal = candidates[0] if candidates else None
    return candidates, signal
