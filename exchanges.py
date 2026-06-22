import aiohttp

async def fetch_json(url, params=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=10) as resp:
            resp.raise_for_status()
            return await resp.json()

async def get_upbit_krw_markets():
    data = await fetch_json("https://api.upbit.com/v1/market/all", {"isDetails": "false"})
    result = set()
    for item in data:
        market = item.get("market", "")
        if market.startswith("KRW-"):
            result.add(market.replace("KRW-", "").upper())
    return result

async def get_bithumb_krw_markets():
    data = await fetch_json("https://api.bithumb.com/public/ticker/ALL_KRW")
    tickers = data.get("data", {})
    return {k.upper() for k in tickers.keys() if k != "date"}

async def get_bitget_usdt_futures_symbols():
    url = "https://api.bitget.com/api/v2/mix/market/contracts"
    data = await fetch_json(url, {"productType": "USDT-FUTURES"})
    result = {}
    for item in data.get("data", []):
        base = item.get("baseCoin", "").upper()
        symbol = item.get("symbol", "")
        if base and symbol:
            result[base] = symbol
    return result

async def get_bitget_tickers():
    url = "https://api.bitget.com/api/v2/mix/market/tickers"
    data = await fetch_json(url, {"productType": "USDT-FUTURES"})
    return data.get("data", [])

async def get_bitget_price(symbol):
    tickers = await get_bitget_tickers()
    for t in tickers:
        if t.get("symbol") == symbol:
            return float(t.get("lastPr"))
    raise ValueError(f"price not found: {symbol}")

async def get_crosslisted_futures_snapshot():
    """
    업비트 KRW + 빗썸 KRW + 비트겟 USDT 선물 교차상장 종목들의 현재가 스냅샷.
    09:00 기준가 저장 → 09:15 현재가와 비교하는 용도.
    """
    upbit = await get_upbit_krw_markets()
    bithumb = await get_bithumb_krw_markets()
    futures = await get_bitget_usdt_futures_symbols()
    tickers = await get_bitget_tickers()

    cross = upbit & bithumb & set(futures.keys())

    snapshot = {}
    for t in tickers:
        base = t.get("baseCoin", "").upper()
        symbol = t.get("symbol", "")
        if base not in cross:
            continue
        try:
            price = float(t.get("lastPr"))
        except Exception:
            continue

        snapshot[base] = {
            "base": base,
            "symbol": symbol,
            "price": price
        }

    return snapshot

async def scan_top_15min_pump_crosslisted(baseline_snapshot, threshold_pct=3.0):
    """
    09:00 저장 가격 대비 09:15 현재 가격 상승률 계산.
    조건 만족 종목 중 가장 많이 튄 1개만 반환.
    """
    current = await get_crosslisted_futures_snapshot()
    candidates = []

    for base, now in current.items():
        old = baseline_snapshot.get(base)
        if not old:
            continue

        old_price = float(old["price"])
        now_price = float(now["price"])

        if old_price <= 0:
            continue

        pump_pct = ((now_price - old_price) / old_price) * 100

        if pump_pct >= threshold_pct:
            candidates.append({
                "base": base,
                "symbol": now["symbol"],
                "change_pct": pump_pct,
                "price": now_price,
                "baseline_price": old_price
            })

    candidates.sort(key=lambda x: x["change_pct"], reverse=True)
    return candidates[0] if candidates else None, candidates
