import asyncio
from datetime import datetime
import pytz

from exchanges import get_crosslisted_futures_snapshot, get_bitget_1m_candles

KST = pytz.timezone("Asia/Seoul")

def kst_window_ms(date_text):
    """
    YYYY-MM-DD 기준 KST 09:00~09:15 ms 반환.
    """
    start_dt = KST.localize(datetime.strptime(date_text + " 09:00:00", "%Y-%m-%d %H:%M:%S"))
    end_dt = KST.localize(datetime.strptime(date_text + " 09:15:00", "%Y-%m-%d %H:%M:%S"))

    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    return start_ms, end_ms

async def run_date_backtest(date_text, threshold_pct=3.0):
    """
    지정 날짜의 09:00~09:15 KST 구간을 과거 1분봉으로 재현.
    - 교차상장+비트겟 선물 가능 종목 전체 조회
    - 각 종목 1분봉 조회
    - 09:00 open 기준, 09:00~09:15 high 최고 상승률 계산
    - TOP 후보 반환
    """
    start_ms, end_ms = kst_window_ms(date_text)

    snapshot = await get_crosslisted_futures_snapshot()
    items = list(snapshot.values())

    sem = asyncio.Semaphore(15)
    candidates = []
    errors = 0

    async def one(item):
        nonlocal errors
        async with sem:
            try:
                candles = await get_bitget_1m_candles(item["symbol"], start_ms, end_ms)
                if not candles:
                    errors += 1
                    return None

                baseline = float(candles[0]["open"])
                peak = max(float(c["high"]) for c in candles)
                last = float(candles[-1]["close"])

                if baseline <= 0:
                    errors += 1
                    return None

                peak_pct = ((peak - baseline) / baseline) * 100
                last_pct = ((last - baseline) / baseline) * 100

                return {
                    "base": item["base"],
                    "symbol": item["symbol"],
                    "change_pct": peak_pct,
                    "last_change_pct": last_pct,
                    "price": last,
                    "baseline_price": baseline,
                    "peak_price": peak,
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

    return {
        "date": date_text,
        "total_symbols": len(items),
        "errors": errors,
        "candidates": candidates,
        "signal": candidates[0] if candidates and candidates[0]["change_pct"] >= threshold_pct else None,
    }
