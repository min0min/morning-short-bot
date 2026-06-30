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
DAILY_SIGNALS_PATH = os.path.join(DATA_DIR, "daily_signals.json")
ACTIVE_CHAT_PATH = os.path.join(DATA_DIR, "active_chat.json")

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

    changed = False
    for k, v in DEFAULT_STATE.items():
        if k not in state:
            state[k] = v
            changed = True
    if "settings" not in state or not isinstance(state["settings"], dict):
        state["settings"] = DEFAULT_STATE["settings"].copy()
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

def load_daily_signals():
    ensure_data_dir()
    if not os.path.exists(DAILY_SIGNALS_PATH):
        with open(DAILY_SIGNALS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    with open(DAILY_SIGNALS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def append_daily_signal(signal_payload):
    ensure_data_dir()
    rows = load_daily_signals()
    signal_payload["saved_at"] = datetime.now().isoformat()
    rows.append(signal_payload)
    with open(DAILY_SIGNALS_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def calc_trade_stats():
    trades = load_trades()
    closed = [t for t in trades if t.get("type") == "CLOSE" and t.get("position")]

    total = len(closed)
    wins = 0
    losses = 0
    total_pnl = 0.0
    best = None
    worst = None
    max_win_streak = 0
    max_loss_streak = 0
    cur_win = 0
    cur_loss = 0

    for t in closed:
        p = t["position"]
        pnl = float(p.get("realized_pnl", 0))
        pnl_pct = float(p.get("pnl_pct", 0))
        total_pnl += pnl

        if pnl > 0:
            wins += 1
            cur_win += 1
            cur_loss = 0
        elif pnl < 0:
            losses += 1
            cur_loss += 1
            cur_win = 0
        else:
            cur_win = 0
            cur_loss = 0

        max_win_streak = max(max_win_streak, cur_win)
        max_loss_streak = max(max_loss_streak, cur_loss)

        if best is None or pnl_pct > float(best.get("pnl_pct", -999999)):
            best = {"base": p.get("base"), "pnl_pct": pnl_pct, "pnl": pnl, "reason": p.get("close_reason")}

        if worst is None or pnl_pct < float(worst.get("pnl_pct", 999999)):
            worst = {"base": p.get("base"), "pnl_pct": pnl_pct, "pnl": pnl, "reason": p.get("close_reason")}

    win_rate = (wins / total * 100) if total else 0.0
    avg_pnl = (total_pnl / total) if total else 0.0

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_pnl": avg_pnl,
        "best": best,
        "worst": worst,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
    }


def save_active_chat_id(chat_id):
    """
    /start를 누른 현재 텔레그램 chat_id를 저장.
    스케줄러 알림은 env TELEGRAM_CHAT_ID보다 이 값을 우선 사용한다.
    """
    ensure_data_dir()
    payload = {
        "chat_id": str(chat_id),
        "updated_at": datetime.now().isoformat(),
    }
    with open(ACTIVE_CHAT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[CHAT ID SAVED] active_chat_id={chat_id}")
    return payload

def load_active_chat_id():
    """
    저장된 active chat_id 반환. 없으면 None.
    """
    ensure_data_dir()
    if not os.path.exists(ACTIVE_CHAT_PATH):
        return None
    try:
        with open(ACTIVE_CHAT_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("chat_id")
    except Exception as e:
        print(f"[CHAT ID LOAD ERROR] {type(e).__name__}: {e}")
        return None


def get_active_chat_debug():
    ensure_data_dir()
    if not os.path.exists(ACTIVE_CHAT_PATH):
        return {
            "exists": False,
            "chat_id": None,
            "updated_at": None,
        }
    try:
        with open(ACTIVE_CHAT_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return {
            "exists": True,
            "chat_id": payload.get("chat_id"),
            "updated_at": payload.get("updated_at"),
        }
    except Exception as e:
        return {
            "exists": False,
            "chat_id": None,
            "updated_at": None,
            "error": f"{type(e).__name__}: {e}",
        }
