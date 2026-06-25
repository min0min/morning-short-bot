from exchanges import get_crosslisted_futures_snapshot

async def scan_today_pump(threshold_pct=3.0):
    """
    개발용 즉시 테스트.
    기준가 저장 없이 현재 Bitget ticker의 24h/UTC 변동률 필드를 이용해
    교차상장 급등 TOP 후보를 확인한다.

    실제 09:00~09:15 전략과는 다르지만,
    '교차상장 필터 → 급등 필터 → TOP1 선정 → PAPER 진입'
    전체 흐름 검증용이다.
    """
    from exchanges import get_bitget_tickers, get_upbit_krw_markets, get_bithumb_krw_markets, get_bitget_usdt_futures_symbols, normalize_base

    upbit = await get_upbit_krw_markets()
    bithumb = await get_bithumb_krw_markets()
    futures = await get_bitget_usdt_futures_symbols()
    tickers = await get_bitget_tickers()

    cross = upbit & bithumb & set(futures.keys())

    candidates = []

    for t in tickers:
        symbol = t.get("symbol", "")
        base = t.get("baseCoin", "") or normalize_base(symbol)
        base_norm = normalize_base(base) or normalize_base(symbol)

        if base_norm not in cross:
            continue

        raw_change = (
            t.get("change24h")
            or t.get("priceChangePercent")
            or t.get("chgUtc")
            or t.get("changeUtc24h")
            or 0
        )

        try:
            value = float(raw_change)
            change_pct = value * 100 if abs(value) <= 1 else value
        except Exception:
            change_pct = 0.0

        try:
            price = float(t.get("lastPr"))
        except Exception:
            price = 0.0

        if change_pct >= threshold_pct:
            candidates.append({
                "base": base_norm,
                "symbol": futures.get(base_norm, symbol),
                "change_pct": change_pct,
                "last_change_pct": change_pct,
                "price": price,
                "baseline_price": None,
                "peak_price": price,
                "peak_time": None,
            })

    candidates.sort(key=lambda x: x["change_pct"], reverse=True)
    return candidates, candidates[0] if candidates else None
