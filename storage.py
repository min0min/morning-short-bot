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
    "joined_at": None,
    "seed_usdt": PAPER_SEED_USDT,
    "paper_balance": PAPER_SEED_USDT,
    "open_position": None,
    "seed_mode": "fixed",
    "exchange": "BingX",
    "api_registered": False,
    "api_tested": False,
    "approval_status": "PENDING",
    "user_chat_id": None,
    "approved_at": None,
    "admin_note": None,
    "real_test_position": None,
    "live_position": None,
    "live_daily_entry_date": None,
    "live_daily_entry_count": 0,
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

    if not state.get("joined_at"):
        state["joined_at"] = datetime.now().date().isoformat()
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
    if state.get("approval_status") not in ("APPROVED", "PAUSED", "BLOCKED"):
        state["approval_status"] = "PENDING"
    save_state(state)

def set_seed_fixed_mode(value):
    state = load_state()
    state["seed_mode"] = "fixed"
    state["seed_usdt"] = float(value)
    state["paper_balance"] = float(value)
    if state.get("approval_status") not in ("APPROVED", "PAUSED", "BLOCKED"):
        state["approval_status"] = "PENDING"
    save_state(state)

def is_seed_auto():
    state = load_state()
    return state.get("seed_mode") == "auto" or float(state.get("seed_usdt", 0) or 0) == 0


def save_real_test_open(order_result):
    """
    실전 주문 테스트 OPEN 기록.
    실제 전략 거래와 구분하기 위해 reason=REAL_TEST_OPEN 사용.
    """
    state = load_state()
    pos = {
        "mode": "REAL_TEST",
        "base": str(order_result.get("symbol", "")).replace("-USDT", "").replace("USDT", ""),
        "symbol": order_result.get("symbol"),
        "side": "SHORT",
        "qty": float(order_result.get("qty", 0) or 0),
        "entry_price": float(order_result.get("price_ref", 0) or 0),
        "requested_usdt": float(order_result.get("margin_usdt", 0) or 0),
        "actual_notional_usdt": float(order_result.get("actual_notional_usdt", 0) or 0),
        "order_raw": order_result.get("raw"),
        "opened_at": datetime.now().isoformat(),
    }
    state["real_test_position"] = pos
    save_state(state)

    append_trade({
        "type": "ENTRY",
        "reason": "REAL_TEST_OPEN",
        "position": pos,
    })
    print(f"[REAL TEST OPEN SAVED] {pos['symbol']} qty={pos['qty']}")
    return pos

def save_real_test_close(close_result, close_price=None):
    """
    실전 주문 테스트 CLOSE 기록.
    BingX 실현손익 조회는 다음 단계에서 정교화하고,
    v4.3.2에서는 entry/close 기준 추정 PnL을 저장한다.
    """
    state = load_state()
    pos = state.get("real_test_position")

    if not pos:
        pos = {
            "mode": "REAL_TEST",
            "base": str(close_result.get("symbol", "")).replace("-USDT", "").replace("USDT", ""),
            "symbol": close_result.get("symbol"),
            "side": "SHORT",
            "qty": float(close_result.get("qty", 0) or 0),
            "entry_price": 0.0,
            "opened_at": None,
        }

    qty = float(close_result.get("qty", pos.get("qty", 0)) or 0)
    entry = float(pos.get("entry_price", 0) or 0)
    close = float(close_price or 0)

    realized_pnl = 0.0
    pnl_pct = 0.0

    if qty > 0 and entry > 0 and close > 0:
        # SHORT PnL approximation
        realized_pnl = (entry - close) * qty
        notional = entry * qty
        pnl_pct = (realized_pnl / notional * 100) if notional else 0.0

    closed_pos = dict(pos)
    closed_pos.update({
        "qty": qty,
        "close_price": close,
        "realized_pnl": realized_pnl,
        "pnl_pct": pnl_pct,
        "close_reason": "REAL_TEST_CLOSE",
        "close_raw": close_result.get("raw"),
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
    print(f"[REAL TEST CLOSE SAVED] {closed_pos.get('symbol')} pnl={realized_pnl}")
    return closed_pos

def get_real_test_stats():
    state = load_state()
    stats = state.get("real_test_stats") or {"total": 0, "wins": 0, "losses": 0, "total_pnl": 0.0, "best": None, "worst": None}
    total = int(stats.get("total", 0))
    wins = int(stats.get("wins", 0))
    win_rate = (wins / total * 100) if total else 0.0
    stats["win_rate"] = win_rate
    return stats


def reset_live_daily_if_needed(state=None):
    today = datetime.now().date().isoformat()
    if state is None:
        state = load_state()
    if state.get("live_daily_entry_date") != today:
        state["live_daily_entry_date"] = today
        state["live_daily_entry_count"] = 0
    return state

def can_live_enter_today():
    state = reset_live_daily_if_needed(load_state())
    return int(state.get("live_daily_entry_count", 0) or 0) < 1

def save_live_entry(order_result, signal=None, entry_level=1, margin_usdt=0.0, order_value_usdt=0.0):
    state = reset_live_daily_if_needed(load_state())

    fill = order_result.get("fill") or {}
    filled_avg = fill.get("avg_price") or order_result.get("filled_avg_price") or order_result.get("price_ref")
    executed_qty = fill.get("executed_qty") or order_result.get("executed_qty") or order_result.get("qty")

    base = str(order_result.get("symbol", "")).replace("-USDT", "").replace("USDT", "")
    existing = state.get("live_position")

    entry = {
        "level": entry_level,
        "qty": float(executed_qty or 0),
        "price": float(filled_avg or 0),
        "margin": float(margin_usdt or 0),
        "order_value_usdt": float(order_value_usdt or order_result.get("actual_notional_usdt", 0) or 0),
        "order_id": order_result.get("order_id"),
        "raw": order_result.get("raw"),
        "fill_raw": fill.get("raw"),
        "created_at": datetime.now().isoformat(),
    }

    if existing:
        entries = existing.get("entries", [])
        entries.append(entry)
        total_qty = sum(float(e.get("qty", 0) or 0) for e in entries)
        weighted = sum(float(e.get("qty", 0) or 0) * float(e.get("price", 0) or 0) for e in entries)
        avg_price = weighted / total_qty if total_qty else 0.0
        total_margin = sum(float(e.get("margin", 0) or 0) for e in entries)
        total_order_value = sum(float(e.get("order_value_usdt", 0) or 0) for e in entries)
        pos = existing
        pos.update({
            "entries": entries,
            "qty": total_qty,
            "avg_price": avg_price,
            "total_margin": total_margin,
            "total_order_value_usdt": total_order_value,
            "updated_at": datetime.now().isoformat(),
        })
    else:
        pos = {
            "mode": "LIVE",
            "base": base,
            "symbol": order_result.get("symbol"),
            "side": "SHORT",
            "leverage": int(order_result.get("leverage", 4) or 4),
            "entries": [entry],
            "qty": float(entry["qty"]),
            "avg_price": float(entry["price"]),
            "total_margin": float(margin_usdt or 0),
            "total_order_value_usdt": float(order_value_usdt or order_result.get("actual_notional_usdt", 0) or 0),
            "signal": signal,
            "opened_at": datetime.now().isoformat(),
            "max_pnl_pct": 0.0,
            "min_pnl_pct": 0.0,
        }
        state["live_daily_entry_count"] = int(state.get("live_daily_entry_count", 0) or 0) + 1

    state["live_position"] = pos
    save_state(state)

    append_trade({
        "type": "ENTRY",
        "reason": "LIVE_STRATEGY_ENTRY" if entry_level == 1 else "LIVE_STRATEGY_ADD",
        "position": pos,
    })
    print(f"[LIVE ENTRY SAVED] {pos['symbol']} level={entry_level} qty={pos['qty']} avg={pos['avg_price']}")
    return pos

def update_live_position_metrics(current_price):
    state = load_state()
    pos = state.get("live_position")
    if not pos:
        return None

    avg = float(pos.get("avg_price", 0) or 0)
    lev = float(pos.get("leverage", 4) or 4)
    if avg <= 0 or current_price <= 0:
        return pos

    # SHORT leveraged pnl %
    pnl_pct = ((avg - float(current_price)) / avg) * 100 * lev
    pos["last_price"] = float(current_price)
    pos["last_pnl_pct"] = pnl_pct
    pos["max_pnl_pct"] = max(float(pos.get("max_pnl_pct", pnl_pct) or pnl_pct), pnl_pct)
    pos["min_pnl_pct"] = min(float(pos.get("min_pnl_pct", pnl_pct) or pnl_pct), pnl_pct)
    pos["updated_at"] = datetime.now().isoformat()
    state["live_position"] = pos
    save_state(state)
    return pos

def should_live_add_entry(current_price):
    state = load_state()
    pos = state.get("live_position")
    if not pos:
        return None
    entries = pos.get("entries", [])
    if len(entries) >= 3:
        return None

    avg = float(pos.get("avg_price", 0) or 0)
    pct = float(state.get("settings", {}).get("add_entry_price_move_pct", 3.0) or 3.0)
    if avg <= 0:
        return None

    # SHORT adverse move: price rises by pct from avg
    if float(current_price) >= avg * (1 + pct / 100):
        return len(entries) + 1
    return None

def save_live_close(close_result, close_price=None):
    state = load_state()
    pos = state.get("live_position")
    if not pos:
        return None

    fill = close_result.get("fill") or {}
    fill_avg = fill.get("avg_price") or close_result.get("filled_avg_price")
    close = float(fill_avg or close_price or pos.get("last_price") or 0)
    qty = float(fill.get("executed_qty") or close_result.get("executed_qty") or close_result.get("qty") or pos.get("qty") or 0)

    realized_from_exchange = close_result.get("realized_pnl")
    if realized_from_exchange is None:
        realized_from_exchange = fill.get("realized_pnl")

    entry = float(pos.get("avg_price", 0) or 0)
    if realized_from_exchange is not None:
        realized_pnl = float(realized_from_exchange)
        pnl_source = fill.get("source", "bingx_realized_pnl")
    else:
        realized_pnl = (entry - close) * qty if entry > 0 and close > 0 and qty > 0 else 0.0
        pnl_source = "fallback_entry_close_price"

    notional = entry * qty
    pnl_pct = (realized_pnl / notional * 100 * float(pos.get("leverage", 4) or 4)) if notional else 0.0
    fee = float(close_result.get("fee") if close_result.get("fee") is not None else (fill.get("fee") or 0.0))

    closed = dict(pos)
    closed.update({
        "qty": qty,
        "close_price": close,
        "realized_pnl": realized_pnl,
        "realized_pnl_source": pnl_source,
        "fee": fee,
        "pnl_pct": pnl_pct,
        "close_order_id": close_result.get("order_id"),
        "close_reason": "LIVE_CLOSE",
        "close_raw": close_result.get("raw"),
        "close_fill_raw": fill.get("raw"),
        "closed_at": datetime.now().isoformat(),
    })

    state["live_position"] = None
    save_state(state)

    append_trade({
        "type": "CLOSE",
        "reason": "LIVE_STRATEGY_CLOSE",
        "position": closed,
    })
    print(f"[LIVE CLOSE SAVED] {closed.get('symbol')} pnl={realized_pnl} pct={pnl_pct}")
    return closed

def get_live_trade_stats():
    trades = load_trades()
    closed = [t for t in trades if t.get("type") == "CLOSE" and t.get("reason") in ("LIVE_STRATEGY_CLOSE", "REAL_TEST_CLOSE")]
    total = len(closed)
    wins = losses = 0
    total_pnl = 0.0
    best = None
    worst = None

    now = datetime.now()
    month_pnl = 0.0
    week_pnl = 0.0

    for t in closed:
        p = t.get("position", {})
        pnl = float(p.get("realized_pnl", 0) or 0)
        pct = float(p.get("pnl_pct", 0) or 0)
        total_pnl += pnl
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1

        try:
            created = datetime.fromisoformat(t.get("created_at"))
        except Exception:
            created = now
        if created.year == now.year and created.month == now.month:
            month_pnl += pnl
        if (now - created).days <= 7:
            week_pnl += pnl

        item = {"base": p.get("base"), "symbol": p.get("symbol"), "pnl": pnl, "pnl_pct": pct}
        if best is None or pct > float(best.get("pnl_pct", -999999)):
            best = item
        if worst is None or pct < float(worst.get("pnl_pct", 999999)):
            worst = item

    state = load_state()
    holding = 1 if state.get("live_position") else 0
    win_rate = (wins / total * 100) if total else 0.0

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "month_pnl": month_pnl,
        "week_pnl": week_pnl,
        "holding": holding,
        "best": best,
        "worst": worst,
    }


def set_user_pending_approval(chat_id=None):
    state = load_state()
    if chat_id is not None:
        state["user_chat_id"] = str(chat_id)
    if state.get("approval_status") not in ("APPROVED", "PAUSED", "BLOCKED"):
        state["approval_status"] = "PENDING"
    save_state(state)
    return state

def approve_user(chat_id=None):
    state = load_state()
    if chat_id is not None:
        state["user_chat_id"] = str(chat_id)
    state["approval_status"] = "APPROVED"
    state["approved_at"] = datetime.now().isoformat()
    save_state(state)
    return state

def reject_user(chat_id=None):
    state = load_state()
    if chat_id is not None:
        state["user_chat_id"] = str(chat_id)
    state["approval_status"] = "REJECTED"
    save_state(state)
    return state

def pause_user(chat_id=None):
    state = load_state()
    if chat_id is not None:
        state["user_chat_id"] = str(chat_id)
    state["approval_status"] = "PAUSED"
    state["running"] = False
    save_state(state)
    return state

def is_user_approved():
    state = load_state()
    return state.get("approval_status") == "APPROVED"


def get_admin_user_snapshot():
    """
    현재 단일 유저 운영 상태 스냅샷.
    v4.5.5 기준은 단일 사용자 저장 구조이며,
    다음 멀티유저 DB 단계에서 리스트 구조로 확장 예정.
    """
    state = load_state()
    stats = get_live_trade_stats() if "get_live_trade_stats" in globals() else {}
    return {
        "state": state,
        "stats": stats,
        "api": load_bingx_api() is not None,
    }


# =========================
# v4.6 TRUE MULTIUSER LAYER
# =========================
USERS_PATH = os.path.join(DATA_DIR, "users.json")
CURRENT_CHAT_ID = None

def _now_iso():
    return datetime.now().isoformat()

def _today():
    return datetime.now().date().isoformat()

def _base_user_state(chat_id):
    s = DEFAULT_STATE.copy()
    s["user_chat_id"] = str(chat_id)
    s["joined_at"] = _today()
    s["approval_status"] = "PENDING"
    s["running"] = False
    s["api_registered"] = False
    s["api_tested"] = False
    # nested mutable copy
    s["settings"] = dict(DEFAULT_STATE.get("settings", {}))
    s["real_test_stats"] = dict(DEFAULT_STATE.get("real_test_stats", {}))
    s["trades"] = []
    s["daily_signals"] = []
    s["bingx_api"] = None
    return s

def load_users():
    ensure_data_dir()
    if not os.path.exists(USERS_PATH):
        # 기존 단일 저장소가 있으면 현재 관리자/active chat 기준으로 마이그레이션 시도
        users = {}
        try:
            legacy = {}
            if os.path.exists(STATE_PATH):
                with open(STATE_PATH, "r", encoding="utf-8") as f:
                    legacy = json.load(f)
            chat_id = legacy.get("user_chat_id") or load_active_chat_id() or "default"
            if chat_id != "default":
                legacy_user = _base_user_state(chat_id)
                legacy_user.update(legacy)
                try:
                    if os.path.exists(BINGX_API_PATH):
                        with open(BINGX_API_PATH, "r", encoding="utf-8") as f:
                            legacy_user["bingx_api"] = json.load(f)
                            legacy_user["api_registered"] = True
                    if os.path.exists(TRADES_PATH):
                        with open(TRADES_PATH, "r", encoding="utf-8") as f:
                            legacy_user["trades"] = json.load(f)
                    if os.path.exists(DAILY_SIGNALS_PATH):
                        with open(DAILY_SIGNALS_PATH, "r", encoding="utf-8") as f:
                            legacy_user["daily_signals"] = json.load(f)
                except Exception:
                    pass
                users[str(chat_id)] = legacy_user
        except Exception as e:
            print(f"[MULTIUSER MIGRATION ERROR] {type(e).__name__}: {e}")
            users = {}
        save_users(users)
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    ensure_data_dir()
    with open(USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def set_current_user(chat_id):
    global CURRENT_CHAT_ID
    if chat_id is None:
        return
    CURRENT_CHAT_ID = str(chat_id)
    users = load_users()
    if str(chat_id) not in users:
        users[str(chat_id)] = _base_user_state(chat_id)
        save_users(users)

def get_current_user_id():
    if CURRENT_CHAT_ID:
        return str(CURRENT_CHAT_ID)
    active = load_active_chat_id()
    if active:
        return str(active)
    return "default"

def get_user_state(chat_id):
    users = load_users()
    sid = str(chat_id)
    if sid not in users:
        users[sid] = _base_user_state(sid)
        save_users(users)
    u = users[sid]
    # 신규 필드 보정
    base = _base_user_state(sid)
    changed = False
    for k, v in base.items():
        if k not in u:
            u[k] = v
            changed = True
    if changed:
        users[sid] = u
        save_users(users)
    return u

def save_user_state(chat_id, state):
    users = load_users()
    sid = str(chat_id)
    state["user_chat_id"] = sid
    state["updated_at"] = _now_iso()
    users[sid] = state
    save_users(users)

# 기존 함수명 override: 이후 코드 변경 최소화
def load_state():
    return get_user_state(get_current_user_id())

def save_state(state):
    save_user_state(get_current_user_id(), state)

def save_bingx_api(api_key, api_secret):
    state = load_state()
    state["bingx_api"] = {"api_key": api_key, "api_secret": api_secret}
    state["api_registered"] = True
    state["approval_status"] = "PENDING" if state.get("approval_status") != "APPROVED" else state.get("approval_status")
    save_state(state)
    print(f"[BINGX API SAVED] chat_id={state.get('user_chat_id')} api_key=***")

def load_bingx_api():
    state = load_state()
    return state.get("bingx_api")

def mark_bingx_api_tested():
    state = load_state()
    state["api_tested"] = True
    if state.get("approval_status") != "APPROVED":
        state["approval_status"] = "PENDING"
    save_state(state)

def set_seed_auto_mode():
    state = load_state()
    state["seed_mode"] = "auto"
    state["seed_usdt"] = 0
    if state.get("approval_status") != "APPROVED":
        state["approval_status"] = "PENDING"
    save_state(state)

def set_seed_fixed_mode(value):
    state = load_state()
    state["seed_mode"] = "fixed"
    state["seed_usdt"] = float(value)
    state["paper_balance"] = float(value)
    if state.get("approval_status") != "APPROVED":
        state["approval_status"] = "PENDING"
    save_state(state)

def append_trade(item):
    state = load_state()
    trades = state.get("trades", [])
    item["created_at"] = _now_iso()
    item["chat_id"] = state.get("user_chat_id")
    trades.append(item)
    state["trades"] = trades
    save_state(state)

def load_trades():
    return load_state().get("trades", [])

def append_daily_signal(item):
    state = load_state()
    signals = state.get("daily_signals", [])
    item["created_at"] = _now_iso()
    item["chat_id"] = state.get("user_chat_id")
    signals.append(item)
    state["daily_signals"] = signals
    save_state(state)

def set_user_pending_approval(chat_id=None):
    if chat_id is not None:
        set_current_user(chat_id)
    state = load_state()
    if chat_id is not None:
        state["user_chat_id"] = str(chat_id)
    if state.get("approval_status") not in ("APPROVED", "PAUSED", "BLOCKED"):
        state["approval_status"] = "PENDING"
    save_state(state)
    return state

def approve_user(chat_id=None):
    if chat_id is not None:
        set_current_user(chat_id)
    state = load_state()
    state["approval_status"] = "APPROVED"
    state["approved_at"] = _now_iso()
    save_state(state)
    return state

def reject_user(chat_id=None):
    if chat_id is not None:
        set_current_user(chat_id)
    state = load_state()
    state["approval_status"] = "REJECTED"
    state["running"] = False
    save_state(state)
    return state

def pause_user(chat_id=None):
    if chat_id is not None:
        set_current_user(chat_id)
    state = load_state()
    state["approval_status"] = "PAUSED"
    state["running"] = False
    save_state(state)
    return state

def is_user_approved():
    return load_state().get("approval_status") == "APPROVED"

def list_users():
    users = load_users()
    # stable order: approved/running first then joined
    return sorted(users.values(), key=lambda u: (u.get("approval_status") != "APPROVED", not u.get("running"), u.get("joined_at") or ""))

def iter_live_users():
    return [u for u in list_users() if u.get("approval_status") == "APPROVED" and u.get("running")]

def get_admin_user_snapshot():
    return {
        "users": list_users(),
        "total": len(list_users()),
    }

def get_live_trade_stats_for_state(state):
    closed = [t for t in state.get("trades", []) if t.get("type") == "CLOSE"]
    total = len(closed)
    wins = losses = 0
    total_pnl = month_pnl = week_pnl = 0.0
    best = worst = None
    now = datetime.now()
    for t in closed:
        p = t.get("position", {})
        pnl = float(p.get("realized_pnl", 0) or 0)
        pct = float(p.get("pnl_pct", 0) or 0)
        total_pnl += pnl
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
        try:
            created = datetime.fromisoformat(t.get("created_at"))
        except Exception:
            created = now
        if created.year == now.year and created.month == now.month:
            month_pnl += pnl
        if (now - created).days <= 7:
            week_pnl += pnl
        item = {"base": p.get("base"), "symbol": p.get("symbol"), "pnl": pnl, "pnl_pct": pct}
        if best is None or pct > float(best.get("pnl_pct", -999999)):
            best = item
        if worst is None or pct < float(worst.get("pnl_pct", 999999)):
            worst = item
    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / total * 100) if total else 0.0,
        "total_pnl": total_pnl,
        "month_pnl": month_pnl,
        "week_pnl": week_pnl,
        "holding": 1 if state.get("live_position") else 0,
        "best": best,
        "worst": worst,
    }

def get_live_trade_stats():
    return get_live_trade_stats_for_state(load_state())

def reset_live_daily_if_needed(state=None):
    today = _today()
    if state is None:
        state = load_state()
    if state.get("live_daily_entry_date") != today:
        state["live_daily_entry_date"] = today
        state["live_daily_entry_count"] = 0
    return state

def can_live_enter_today():
    state = reset_live_daily_if_needed(load_state())
    return int(state.get("live_daily_entry_count", 0) or 0) < 1
