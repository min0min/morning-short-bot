import aiohttp
import re

LAST_DEBUG = {
    "upbit_count": 0,
    "bithumb_count": 0,
    "bitget_contract_count": 0,
    "bitget_ticker_count": 0,
    "upbit_samples": [],
    "bithumb_samples": [],
    "bitget_contract_samples": [],
    "bitget_ticker_samples": [],
    "cross_upbit_bithumb_count": 0,
    "cross_final_count": 0,
    "cross_final_samples": [],
    "error": None
}

def normalize_base(symbol: str) -> str:
    if not symbol:
        return ""
    s = str(symbol).upper()
    s = s.replace("-", "").replace("_UMCBL", "").replace("_DMCBL", "").replace("_SUMCBL", "")
    s = s.replace("USDT", "").replace("USDC", "").replace("USD", "")
    s = re.sub(r"^\d+", "", s)
    return s.strip()

async def fetch_json(url, params=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, timeout=15) as resp:
            resp.raise_for_status()
            return await resp.json()

async def get_upbit_krw_markets():
    data = await fetch_json("https://api.upbit.com/v1/market/all", {"isDetails": "false"})
    result = set()
    for item in data:
        market = item.get("market", "")
        if market.startswith("KRW-"):
            result.add(market.replace("KRW-", "").upper())
    LAST_DEBUG["upbit_count"] = len(result)
    LAST_DEBUG["upbit_samples"] = sorted(list(result))[:20]
    return result

async def get_bithumb_krw_markets():
    data = await fetch_json("https://api.bithumb.com/public/ticker/ALL_KRW")
    tickers = data.get("data", {})
    result = {k.upper() for k in tickers.keys() if k != "date"}
    LAST_DEBUG["bithumb_count"] = len(result)
    LAST_DEBUG["bithumb_samples"] = sorted(list(result))[:20]
    return result

async def get_bitget_usdt_futures_symbols():
    url = "https://api.bitget.com/api/v2/mix/market/contracts"
    data = await fetch_json(url, {"productType": "USDT-FUTURES"})
    rows = data.get("data", [])
    result = {}
    samples = []

    for item in rows:
        symbol = item.get("symbol", "")
        base = item.get("baseCoin", "") or normalize_base(symbol)
        base_norm = normalize_base(base) or normalize_base(symbol)
        if base_norm and symbol:
            result[base_norm] = symbol
            if len(samples) < 20:
                samples.append(f"{base_norm}:{symbol}")

    LAST_DEBUG["bitget_contract_count"] = len(result)
    LAST_DEBUG["bitget_contract_samples"] = samples
    return result

async def get_bitget_tickers():
    url = "https://api.bitget.com/api/v2/mix/market/tickers"
    data = await fetch_json(url, {"productType": "USDT-FUTURES"})
    rows = data.get("data", [])
    LAST_DEBUG["bitget_ticker_count"] = len(rows)
    LAST_DEBUG["bitget_ticker_samples"] = [
        str({"symbol": t.get("symbol"), "baseCoin": t.get("baseCoin"), "lastPr": t.get("lastPr")})
        for t in rows[:20]
    ]
    return rows

async def get_bitget_price(symbol):
    tickers = await get_bitget_tickers()
    for t in tickers:
        if t.get("symbol") == symbol:
            return float(t.get("lastPr"))
    raise ValueError(f"price not found: {symbol}")

async def get_crosslisted_futures_snapshot():
    try:
        LAST_DEBUG["error"] = None
        upbit = await get_upbit_krw_markets()
        bithumb = await get_bithumb_krw_markets()
        futures = await get_bitget_usdt_futures_symbols()
        tickers = await get_bitget_tickers()

        cross_kr = upbit & bithumb
        cross_final = cross_kr & set(futures.keys())

        LAST_DEBUG["cross_upbit_bithumb_count"] = len(cross_kr)
        LAST_DEBUG["cross_final_count"] = len(cross_final)
        LAST_DEBUG["cross_final_samples"] = sorted(list(cross_final))[:30]

        snapshot = {}
        for t in tickers:
            symbol = t.get("symbol", "")
            base = t.get("baseCoin", "") or normalize_base(symbol)
            base_norm = normalize_base(base) or normalize_base(symbol)

            if base_norm not in cross_final:
                continue

            try:
                price = float(t.get("lastPr"))
            except Exception:
                continue

            snapshot[base_norm] = {
                "base": base_norm,
                "symbol": futures.get(base_norm, symbol),
                "price": price
            }
        return snapshot

    except Exception as e:
        LAST_DEBUG["error"] = f"{type(e).__name__}: {e}"
        raise

def get_exchange_debug_text():
    def samples(key):
        arr = LAST_DEBUG.get(key) or []
        return ", ".join(arr[:10]) if arr else "없음"

    return f"""🧪 [거래소 디버그]

업비트 KRW 종목 수 : {LAST_DEBUG.get('upbit_count')}
빗썸 KRW 종목 수 : {LAST_DEBUG.get('bithumb_count')}
비트겟 선물 계약 수 : {LAST_DEBUG.get('bitget_contract_count')}
비트겟 티커 수 : {LAST_DEBUG.get('bitget_ticker_count')}

업비트 ∩ 빗썸 : {LAST_DEBUG.get('cross_upbit_bithumb_count')}개
업비트 ∩ 빗썸 ∩ 비트겟선물 : {LAST_DEBUG.get('cross_final_count')}개

최종 교차 예시:
{samples('cross_final_samples')}

비트겟 계약 예시:
{samples('bitget_contract_samples')}

에러:
{LAST_DEBUG.get('error') or '없음'}"""
