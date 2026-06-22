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

async def scan_top_pump_crosslisted(threshold_pct=3.0):
    upbit, bithumb, futures, tickers = await get_upbit_krw_markets(), await get_bithumb_krw_markets(), await get_bitget_usdt_futures_symbols(), await get_bitget_tickers()

    cross = upbit & bithumb & set(futures.keys())
    candidates = []

    for t in tickers:
        base = t.get("baseCoin", "").upper()
        symbol = t.get("symbol", "")
        if base not in cross:
            continue

        # Bitget ticker usually has price change percent. Field names may vary, so handle both.
        raw_change = t.get("change24h") or t.get("priceChangePercent") or t.get("chgUtc") or 0
        try:
            change_pct = float(raw_change) * 100 if abs(float(raw_change)) <= 1 else float(raw_change)
        except Exception:
            change_pct = 0.0

        if change_pct >= threshold_pct:
            candidates.append({
                "base": base,
                "symbol": symbol,
                "change_pct": change_pct,
                "price": float(t.get("lastPr"))
            })

    candidates.sort(key=lambda x: x["change_pct"], reverse=True)
    return candidates[0] if candidates else None, candidates
