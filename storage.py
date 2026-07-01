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
BINGX_API_PATH = os.path.join(DATA_DIR, "bingx_api.json")

DEFAULT_STATE = {
    "running": False,
    "seed_usdt": PAPER_SEED_USDT,
    "paper_balance": PAPER_SEED_USDT,
    "open_position": None,
    "seed_mode": "fixed",
    "exchange": "BingX",
    "api_registered": False,
    "api_tested": False,
    "approval_status": "PAPER_ONLY",
    "real_test_position": None,
    "real_test_stats": {"total": 0, "wins": 0, "losses": 0, "total_pnl": 0.0, "best": None, "worst": None},
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


def save_bingx_api(api_key, api_secret):
    ensure_data_dir()
    payload = {
        "api_key": str(api_key).strip(),
        "api_secret": str(api_secret).strip(),
        "updated_at": datetime.now().isoformat(),
    }
    with open(BINGX_API_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    state = load_state()
    state["exchange"] = "BingX"
    state["api_registered"] = True
    save_state(state)

    print("[BINGX API SAVED] api_key=***")
    return payload

def load_bingx_api():
    ensure_data_dir()
    if not os.path.exists(BINGX_API_PATH):
        return None
    try:
        with open(BINGX_API_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if not payload.get("api_key") or not payload.get("api_secret"):
            return None
        return payload
    except Exception as e:
        print(f"[BINGX API LOAD ERROR] {type(e).__name__}: {e}")
        return None

def mark_bingx_api_tested(ok=True):
    state = load_state()
    state["api_tested"] = bool(ok)
    save_state(state)

def set_seed_auto_mode():
    state = load_state()
    state["seed_mode"] = "auto"
    state["seed_usdt"] = 0
    save_state(state)

def set_seed_fixed_mode(value):
    state = load_state()
    state["seed_mode"] = "fixed"
    state["seed_usdt"] = float(value)
    state["paper_balance"] = float(value)
    save_state(state)

def is_seed_auto():
    state = load_state()
    return state.get("seed_mode") == "auto" or float(state.get("seed_usdt", 0) or 0) == 0


def save_real_test_open(order_result):
    """
    실전 주문 테스트 OPEN 기록.
    v4.3.3: 체결 평균가/실제 체결수량 우선 저장.
    """
    state = load_state()

    fill = order_result.get("fill") or {}
    filled_avg = fill.get("avg_price") or order_result.get("filled_avg_price") or order_result.get("price_ref")
    executed_qty = fill.get("executed_qty") or order_result.get("executed_qty") or order_result.get("qty")

    pos = {
        "mode": "REAL_TEST",
        "base": str(order_result.get("symbol", "")).replace("-USDT", "").replace("USDT", ""),
        "symbol": order_result.get("symbol"),
        "side": "SHORT",
        "leverage": int(order_result.get("leverage", 4) or 4),
        "qty": float(executed_qty or 0),
        "entry_price": float(filled_avg or 0),
        "entry_price_source": fill.get("source", "fallback"),
        "requested_usdt": float(order_result.get("margin_usdt", 0) or 0),
        "actual_notional_usdt": float(order_result.get("actual_notional_usdt", 0) or 0),
        "order_id": order_result.get("order_id"),
        "order_raw": order_result.get("raw"),
        "fill_raw": fill.get("raw"),
        "opened_at": datetime.now().isoformat(),
    }
    state["real_test_position"] = pos
    save_state(state)

    append_trade({
        "type": "ENTRY",
        "reason": "REAL_TEST_OPEN",
        "position": pos,
    })
    print(f"[REAL TEST OPEN SAVED] {pos['symbol']} qty={pos['qty']} entry={pos['entry_price']} lev={pos['leverage']}")
    return pos


def save_real_test_close(close_result, close_price=None):
    """
    실전 주문 테스트 CLOSE 기록.
    v4.3.3: BingX 체결 평균가/realizedPnl 우선 사용.
    없으면 참고가 기준 fallback.
    """
    state = load_state()
    pos = state.get("real_test_position")

    if not pos:
        pos = {
            "mode": "REAL_TEST",
            "base": str(close_result.get("symbol", "")).replace("-USDT", "").replace("USDT", ""),
            "symbol": close_result.get("symbol"),
            "side": "SHORT",
            "leverage": 4,
            "qty": float(close_result.get("qty", 0) or 0),
            "entry_price": 0.0,
            "opened_at": None,
        }

    fill = close_result.get("fill") or {}
    fill_avg = fill.get("avg_price") or close_result.get("filled_avg_price")
    fill_qty = fill.get("executed_qty") or close_result.get("executed_qty")

    qty = float(fill_qty or close_result.get("qty", pos.get("qty", 0)) or 0)
    entry = float(pos.get("entry_price", 0) or 0)
    close = float(fill_avg or close_price or 0)

    realized_from_exchange = close_result.get("realized_pnl")
    if realized_from_exchange is None:
        realized_from_exchange = fill.get("realized_pnl")

    if realized_from_exchange is not None:
        realized_pnl = float(realized_from_exchange)
        source = fill.get("source", "bingx_realized_pnl")
    else:
        # SHORT PnL fallback
        realized_pnl = (entry - close) * qty if qty > 0 and entry > 0 and close > 0 else 0.0
        source = "fallback_entry_close_price"

    notional = entry * qty
    pnl_pct = (realized_pnl / notional * 100) if notional else 0.0

    fee = float(close_result.get("fee") if close_result.get("fee") is not None else (fill.get("fee") or 0.0))

    closed_pos = dict(pos)
    closed_pos.update({
        "qty": qty,
        "close_price": close,
        "close_price_source": fill.get("source", "fallback"),
        "realized_pnl": realized_pnl,
        "realized_pnl_source": source,
        "fee": fee,
        "pnl_pct": pnl_pct,
        "close_reason": "REAL_TEST_CLOSE",
        "close_order_id": close_result.get("order_id"),
        "close_raw": close_result.get("raw"),
        "close_fill_raw": fill.get("raw"),
        "closed_at": datetime.now().isoformat(),
    })

    state["real_test_position"] = None

    stats = state.get("real_test_stats") or {"total": 0, "wins": 0, "losses": 0, "total_pnl": 0.0, "best": None, "worst": None}
    stats["total"] = int(stats.get("total", 0)) + 1
    stats["total_pnl"] = float(stats.get("total_pnl", 0) or 0) + realized_pnl
    if realized_pnl > 0:
        stats["wins"] = int(stats.get("wins", 0)) + 1
    elif realized_pnl < 0:
        stats["losses"] = int(stats.get("losses", 0)) + 1

    item = {
        "base": closed_pos.get("base"),
        "symbol": closed_pos.get("symbol"),
        "pnl": realized_pnl,
        "pnl_pct": pnl_pct,
    }
    best = stats.get("best")
    worst = stats.get("worst")
    if best is None or pnl_pct > float(best.get("pnl_pct", -999999)):
        stats["best"] = item
    if worst is None or pnl_pct < float(worst.get("pnl_pct", 999999)):
        stats["worst"] = item

    state["real_test_stats"] = stats
    save_state(state)

    append_trade({
        "type": "CLOSE",
        "reason": "REAL_TEST_CLOSE",
        "position": closed_pos,
    })
    print(f"[REAL TEST CLOSE SAVED] {closed_pos.get('symbol')} pnl={realized_pnl} source={source}")
    return closed_pos


def get_real_test_stats():
    state = load_state()
    stats = state.get("real_test_stats") or {"total": 0, "wins": 0, "losses": 0, "total_pnl": 0.0, "best": None, "worst": None}
    total = int(stats.get("total", 0))
    wins = int(stats.get("wins", 0))
    win_rate = (wins / total * 100) if total else 0.0
    stats["win_rate"] = win_rate
    return stats
