import asyncio
from datetime import datetime, timedelta
import pytz

from exchanges import get_crosslisted_futures_snapshot, get_bitget_15m_candles

KST = pytz.timezone("Asia/Seoul")

def kst_window_ms(date_text):
    start_dt = KST.localize(datetime.strptime(date_text + " 09:00:00", "%Y-%m-%d %H:%M:%S"))
    end_dt = KST.localize(datetime.strptime(date_text + " 09:15:00", "%Y-%m-%d %H:%M:%S"))
    return int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)

async def run_date_backtest(date_text, threshold_pct=3.0):
    """
    지정 날짜의 09:00~09:15 KST 15분봉 O→C 기준 백테스트.

    알림봇 기준에 맞춤:
    - 기준가 = 15분봉 open
    - 판정가 = 15분봉 close
    - 상승률 = (close - open) / open * 100
    - high는 참고용
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
                candles = await get_bitget_15m_candles(item["symbol"], start_ms, end_ms)
                if not candles:
                    errors += 1
                    return None

                candle = candles[0]

                baseline = float(candle["open"])
                peak = float(candle["high"])
                close = float(candle["close"])

                if baseline <= 0:
                    errors += 1
                    return None

                close_pct = ((close - baseline) / baseline) * 100
                peak_pct = ((peak - baseline) / baseline) * 100

                return {
                    "base": item["base"],
                    "symbol": item["symbol"],
                    "change_pct": close_pct,       # 최종 선정 기준
                    "last_change_pct": close_pct,
                    "peak_change_pct": peak_pct,   # 참고용
                    "price": close,
                    "baseline_price": baseline,
                    "peak_price": peak,
                    "peak_time": "09:00~09:15 15m candle",
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

def last_n_dates(n=7, end_date_text=None):
    if end_date_text:
        end_date = datetime.strptime(end_date_text, "%Y-%m-%d").date()
    else:
        end_date = datetime.now(KST).date()

    return [(end_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n - 1, -1, -1)]

async def run_recent_days_backtest(days=7, threshold_pct=3.0, end_date_text=None):
    dates = last_n_dates(days, end_date_text)
    results = []

    for d in dates:
        try:
            r = await run_date_backtest(d, threshold_pct)
            results.append(r)
        except Exception as e:
            results.append({
                "date": d,
                "total_symbols": 0,
                "errors": 1,
                "candidates": [],
                "error": f"{type(e).__name__}: {e}",
            })

    return results
