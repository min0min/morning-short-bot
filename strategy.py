from datetime import datetime

from storage import load_state, save_state, append_trade

def margin_amount(seed, pct):
    return round(float(seed) * float(pct), 4)

def position_notional(margin, leverage):
    return round(float(margin) * float(leverage), 4)

def recalc_avg(entries):
    total_notional = sum(float(e["notional"]) for e in entries)
    if total_notional <= 0:
        return 0
    return sum(float(e["price"]) * float(e["notional"]) for e in entries) / total_notional

def leveraged_pnl_pct_short(avg_price, current_price, leverage):
    raw_pct = ((float(avg_price) - float(current_price)) / float(avg_price)) * 100
    return raw_pct * float(leverage)

def create_position(signal, reason="CLOSED_15M_OC_TOP1"):
    state = load_state()
    settings = state["settings"]
    seed = float(state["seed_usdt"])
    leverage = int(settings["leverage"])
    price = float(signal["price"])

    m1 = margin_amount(seed, settings["entry_1_pct"])

    pos = {
        "status": "OPEN",
        "side": "SHORT",
        "base": signal["base"],
        "symbol": signal["symbol"],
        "opened_at": datetime.now().isoformat(),
        "reason": reason,
        "signal": signal,
        "entries": [
            {
                "level": 1,
                "price": price,
                "margin": m1,
                "notional": position_notional(m1, leverage),
                "time": datetime.now().isoformat(),
            }
        ],
        "avg_price": price,
        "total_margin": m1,
        "total_notional": position_notional(m1, leverage),

        # 2순위 기능: 진입 후 최대 유리/불리 구간 추적
        "max_pnl_pct": 0.0,
        "min_pnl_pct": 0.0,
        "max_pnl_price": price,
        "min_pnl_price": price,
        "max_pnl_time": datetime.now().isoformat(),
        "min_pnl_time": datetime.now().isoformat(),

        "closed_at": None,
        "close_reason": None,
        "realized_pnl": 0,
    }

    state["open_position"] = pos
    save_state(state)
    append_trade({"type": "ENTRY_1", "reason": reason, "position": pos})
    return pos

def update_open_position_metrics(current_price):
    """
    오픈 포지션의 최대 수익률/최대 손실률을 계속 갱신.
    SHORT 기준 레버리지 수익률.
    """
    state = load_state()
    pos = state.get("open_position")
    if not pos or pos.get("status") != "OPEN":
        return None

    leverage = state["settings"]["leverage"]
    pnl_pct = leveraged_pnl_pct_short(pos["avg_price"], current_price, leverage)
    now = datetime.now().isoformat()

    changed = False

    if "max_pnl_pct" not in pos or pnl_pct > float(pos.get("max_pnl_pct", -999999)):
        pos["max_pnl_pct"] = round(pnl_pct, 4)
        pos["max_pnl_price"] = float(current_price)
        pos["max_pnl_time"] = now
        changed = True

    if "min_pnl_pct" not in pos or pnl_pct < float(pos.get("min_pnl_pct", 999999)):
        pos["min_pnl_pct"] = round(pnl_pct, 4)
        pos["min_pnl_price"] = float(current_price)
        pos["min_pnl_time"] = now
        changed = True

    pos["last_pnl_pct"] = round(pnl_pct, 4)
    pos["last_price"] = float(current_price)
    pos["last_checked_at"] = now
    changed = True

    if changed:
        state["open_position"] = pos
        save_state(state)

    return pos

def add_entry_if_needed(current_price):
    state = load_state()
    pos = state.get("open_position")
    if not pos or pos.get("status") != "OPEN":
        return None

    settings = state["settings"]
    entries = pos["entries"]
    next_level = len(entries) + 1

    if next_level > 3:
        return None

    last_entry_price = float(entries[-1]["price"])
    move_up_pct = ((float(current_price) - last_entry_price) / last_entry_price) * 100

    if move_up_pct < float(settings["add_entry_price_move_pct"]):
        return None

    pct = settings["entry_2_pct"] if next_level == 2 else settings["entry_3_pct"]
    margin = margin_amount(float(state["seed_usdt"]), pct)
    leverage = int(settings["leverage"])

    entry = {
        "level": next_level,
        "price": float(current_price),
        "margin": margin,
        "notional": position_notional(margin, leverage),
        "time": datetime.now().isoformat(),
    }

    entries.append(entry)

    pos["entries"] = entries
    pos["avg_price"] = recalc_avg(entries)
    pos["total_margin"] = round(sum(float(e["margin"]) for e in entries), 4)
    pos["total_notional"] = round(sum(float(e["notional"]) for e in entries), 4)

    # 추가진입 후 평단이 바뀌므로 메트릭 초기/갱신
    pnl_pct = leveraged_pnl_pct_short(pos["avg_price"], current_price, leverage)
    now = datetime.now().isoformat()
    pos["last_pnl_pct"] = round(pnl_pct, 4)
    pos["last_price"] = float(current_price)
    if pnl_pct > float(pos.get("max_pnl_pct", -999999)):
        pos["max_pnl_pct"] = round(pnl_pct, 4)
        pos["max_pnl_price"] = float(current_price)
        pos["max_pnl_time"] = now
    if pnl_pct < float(pos.get("min_pnl_pct", 999999)):
        pos["min_pnl_pct"] = round(pnl_pct, 4)
        pos["min_pnl_price"] = float(current_price)
        pos["min_pnl_time"] = now

    state["open_position"] = pos
    save_state(state)
    append_trade({"type": f"ENTRY_{next_level}", "position": pos})
    return entry, pos

def close_position(current_price, reason):
    state = load_state()
    pos = state.get("open_position")
    if not pos:
        return None

    # 청산 직전 메트릭 최신화
    leverage = state["settings"]["leverage"]
    pnl_pct = leveraged_pnl_pct_short(pos["avg_price"], current_price, leverage)
    pnl_usdt = float(pos["total_margin"]) * (pnl_pct / 100)

    now = datetime.now().isoformat()

    if pnl_pct > float(pos.get("max_pnl_pct", -999999)):
        pos["max_pnl_pct"] = round(pnl_pct, 4)
        pos["max_pnl_price"] = float(current_price)
        pos["max_pnl_time"] = now

    if pnl_pct < float(pos.get("min_pnl_pct", 999999)):
        pos["min_pnl_pct"] = round(pnl_pct, 4)
        pos["min_pnl_price"] = float(current_price)
        pos["min_pnl_time"] = now

    pos["status"] = "CLOSED"
    pos["closed_at"] = now
    pos["close_price"] = float(current_price)
    pos["close_reason"] = reason
    pos["pnl_pct"] = round(pnl_pct, 4)
    pos["realized_pnl"] = round(pnl_usdt, 4)

    state["paper_balance"] = round(float(state["paper_balance"]) + pnl_usdt, 4)
    state["open_position"] = None
    save_state(state)

    append_trade({"type": "CLOSE", "reason": reason, "position": pos})
    return pos, state["paper_balance"]

def check_tp(current_price):
    state = load_state()
    pos = state.get("open_position")
    if not pos:
        return None

    pnl_pct = leveraged_pnl_pct_short(pos["avg_price"], current_price, state["settings"]["leverage"])
    if pnl_pct >= float(state["settings"]["tp_leveraged_pct"]):
        return close_position(current_price, "TAKE_PROFIT")
    return None

def check_sl_after_16(current_price):
    state = load_state()
    pos = state.get("open_position")
    if not pos:
        return None

    pnl_pct = leveraged_pnl_pct_short(pos["avg_price"], current_price, state["settings"]["leverage"])
    if pnl_pct <= float(state["settings"]["sl_leveraged_pct"]):
        return close_position(current_price, "STOP_LOSS_16_CHECK")
    return None
