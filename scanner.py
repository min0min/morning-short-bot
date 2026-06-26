import asyncio
from datetime import datetime, timedelta
import pytz

from exchanges import get_crosslisted_futures_snapshot, get_bitget_closed_15m_candle_by_open

KST = pytz.timezone("Asia/Seoul")

def latest_closed_15m_open_ms(now=None):
    if now is None:
        now = datetime.now(KST)
    elif now.tzinfo is None:
        now = KST.localize(now)
    else:
        now = now.astimezone(KST)

    minute = (now.minute // 15) * 15
    boundary = now.replace(minute=minute, second=0, microsecond=0)
    target_open = boundary - timedelta(minutes=15)
    return int(target_open.timestamp() * 1000), target_open

async def scan_closed_15m_oc_by_open_ms(target_open_ms, threshold_pct=3.0):
    snapshot = await get_crosslisted_futures_snapshot()
    items = list(snapshot.values())

    sem = asyncio.Semaphore(15)
    candidates = []
    errors = 0

    async def one(item):
        nonlocal errors
        async with sem:
            try:
                candle = await get_bitget_closed_15m_candle_by_open(item["symbol"], target_open_ms)
                if not candle:
                    errors += 1
                    return None

                o = float(candle["open"])
                h = float(candle["high"])
                l = float(candle["low"])
                c = float(candle["close"])

                if o <= 0:
                    errors += 1
                    return None

                oc_pct = ((c - o) / o) * 100
                high_pct = ((h - o) / o) * 100

                return {
                    "base": item["base"],
                    "symbol": item["symbol"],
                    "change_pct": oc_pct,
                    "last_change_pct": oc_pct,
                    "peak_change_pct": high_pct,
                    "price": c,
                    "baseline_price": o,
                    "peak_price": h,
                    "low_price": l,
                    "candle_ts": candle["ts"],
                    "peak_time": None,
                }

            except Exception:
                errors += 1
                return None

    rows = await asyncio.gather(*(one(item) for item in items))

    for row in rows:
        if row:
            candidates.append(row)

    candidates.sort(key=lambda x: x["change_pct"], reverse=True)
    signal = candidates[0] if candidates and candidates[0]["change_pct"] >= threshold_pct else None

    return {
        "total_symbols": len(items),
        "errors": errors,
        "candidates": candidates,
        "signal": signal,
    }

async def scan_latest_closed_15m_oc(threshold_pct=3.0):
    target_open_ms, target_open_dt = latest_closed_15m_open_ms()
    result = await scan_closed_15m_oc_by_open_ms(target_open_ms, threshold_pct)
    result["target_open"] = target_open_dt.strftime("%Y-%m-%d %H:%M KST")
    return result
