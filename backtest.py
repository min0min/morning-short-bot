from datetime import datetime, timedelta
import pytz

from scanner import scan_closed_15m_oc_by_open_ms

KST = pytz.timezone("Asia/Seoul")

def kst_0900_open_ms(date_text):
    dt = KST.localize(datetime.strptime(date_text + " 09:00:00", "%Y-%m-%d %H:%M:%S"))
    return int(dt.timestamp() * 1000)

async def run_date_backtest(date_text, threshold_pct=3.0):
    target_open_ms = kst_0900_open_ms(date_text)
    result = await scan_closed_15m_oc_by_open_ms(target_open_ms, threshold_pct)
    result["date"] = date_text
    return result

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
            r["date"] = d
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
