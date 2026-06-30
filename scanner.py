import asyncio
from datetime import datetime, timedelta
import pytz

from exchanges import get_crosslisted_futures_snapshot, get_bitget_closed_15m_candle_by_open

KST = pytz.timezone("Asia/Seoul")

def latest_closed_15m_open_ms(now=None):
    """
    현재 시각 기준 가장 최근에 마감된 15분봉의 open timestamp.
    09:15:20에 실행되면 09:00 open 캔들 선택.
    """
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

async def select_signal_by_closed_15m(target_open_ms, threshold_pct=3.0, debug_top_n=20):
    """
    v3.3 핵심 통합 함수.

    실시간 스캔과 날짜 백테스트가 반드시 이 함수 하나만 사용한다.
    기준:
    - Bitget 선물 15분봉
    - target_open_ms에 시작한 15분봉
    - 상승률 = (Close - Open) / Open * 100
    - 업비트 + 빗썸 + 비트겟 선물 교차상장 종목만 대상
    - +threshold 이상 후보 중 O→C 상승률 1등만 signal
    """
    snapshot = await get_crosslisted_futures_snapshot()
    items = list(snapshot.values())

    sem = asyncio.Semaphore(12)
    candidates = []
    errors = 0
    error_samples = []

    async def one(item):
        nonlocal errors
        async with sem:
            try:
                candle = await get_bitget_closed_15m_candle_by_open(item["symbol"], target_open_ms)
                if not candle:
                    errors += 1
                    if len(error_samples) < 10:
                        error_samples.append(f"{item['base']} no candle")
                    return None

                o = float(candle["open"])
                h = float(candle["high"])
                l = float(candle["low"])
                c = float(candle["close"])

                if o <= 0:
                    errors += 1
                    if len(error_samples) < 10:
                        error_samples.append(f"{item['base']} bad open")
                    return None

                oc_pct = ((c - o) / o) * 100
                high_pct = ((h - o) / o) * 100
                low_pct = ((l - o) / o) * 100

                return {
                    "base": item["base"],
                    "symbol": item["symbol"],
                    "change_pct": oc_pct,       # 최종 선정 기준
                    "last_change_pct": oc_pct,
                    "peak_change_pct": high_pct,
                    "low_change_pct": low_pct,
                    "price": c,
                    "baseline_price": o,
                    "peak_price": h,
                    "low_price": l,
                    "candle_ts": candle["ts"],
                    "target_open_ms": target_open_ms,
                    "passed": oc_pct >= threshold_pct,
                    "reason": "PASS" if oc_pct >= threshold_pct else f"BELOW_THRESHOLD_{threshold_pct}",
                }

            except Exception as e:
                errors += 1
                if len(error_samples) < 10:
                    error_samples.append(f"{item.get('base')} {type(e).__name__}: {e}")
                return None

    rows = await asyncio.gather(*(one(item) for item in items))

    for row in rows:
        if row:
            candidates.append(row)

    candidates.sort(key=lambda x: x["change_pct"], reverse=True)
    passed = [c for c in candidates if c["passed"]]
    signal = passed[0] if passed else None

    debug_top = candidates[:debug_top_n]

    return {
        "target_open_ms": target_open_ms,
        "total_symbols": len(items),
        "errors": errors,
        "error_samples": error_samples,
        "candidates": candidates,
        "top20": debug_top,
        "passed": passed,
        "signal": signal,
    }

async def scan_closed_15m_oc_by_open_ms(target_open_ms, threshold_pct=3.0):
    """
    호환 함수.
    내부적으로 통합 함수 사용.
    """
    return await select_signal_by_closed_15m(target_open_ms, threshold_pct)

async def scan_latest_closed_15m_oc(threshold_pct=3.0):
    target_open_ms, target_open_dt = latest_closed_15m_open_ms()
    result = await select_signal_by_closed_15m(target_open_ms, threshold_pct)
    result["target_open"] = target_open_dt.strftime("%Y-%m-%d %H:%M KST")
    return result
