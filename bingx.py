import time
import hmac
import hashlib
from urllib.parse import urlencode

import aiohttp

BINGX_BASE_URL = "https://open-api.bingx.com"

def _sign(query_string: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

def _build_signed_query(params: dict, secret: str) -> str:
    payload = dict(params or {})
    payload["timestamp"] = int(time.time() * 1000)
    payload.setdefault("recvWindow", 5000)
    query_string = urlencode(sorted(payload.items()))
    signature = _sign(query_string, secret)
    return f"{query_string}&signature={signature}"

async def _bingx_get(api_key: str, api_secret: str, path: str, params: dict | None = None):
    if not api_key or not api_secret:
        raise ValueError("BingX API Key/Secret이 비어있습니다.")

    query = _build_signed_query(params or {}, api_secret)
    url = f"{BINGX_BASE_URL}{path}?{query}"
    headers = {"X-BX-APIKEY": api_key}

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as resp:
            text = await resp.text()
            try:
                data = await resp.json()
            except Exception:
                raise RuntimeError(f"BingX 응답 JSON 파싱 실패: HTTP {resp.status} / {text[:300]}")

            if resp.status >= 400:
                raise RuntimeError(f"BingX HTTP 오류: {resp.status} / {data}")

            code = str(data.get("code", "0"))
            if code not in ("0", "200"):
                raise RuntimeError(f"BingX API 오류: code={data.get('code')} msg={data.get('msg')}")

            return data

def _extract_available_usdt_from_balance_response(data: dict) -> float:
    obj = data.get("data", data)

    if isinstance(obj, dict) and isinstance(obj.get("balance"), dict):
        b = obj["balance"]
        for key in ["availableMargin", "availableBalance", "available", "free", "balance"]:
            if b.get(key) is not None:
                return float(b[key])

    if isinstance(obj, dict):
        for key in ["availableMargin", "availableBalance", "available", "free", "balance"]:
            if obj.get(key) is not None:
                return float(obj[key])

    if isinstance(obj, list):
        for item in obj:
            if not isinstance(item, dict):
                continue
            asset = str(item.get("asset") or item.get("currency") or item.get("coin") or "").upper()
            if asset and asset != "USDT":
                continue
            for key in ["availableMargin", "availableBalance", "available", "free", "balance"]:
                if item.get(key) is not None:
                    return float(item[key])

    raise RuntimeError(f"USDT 사용 가능 잔고를 찾지 못했습니다. 응답 구조 확인 필요: {data}")

async def get_bingx_swap_balance(api_key: str, api_secret: str):
    data = await _bingx_get(api_key, api_secret, "/openApi/swap/v3/user/balance", {})
    available_usdt = _extract_available_usdt_from_balance_response(data)
    return {"available_usdt": available_usdt, "raw": data}

async def get_bingx_positions(api_key: str, api_secret: str, symbol: str | None = None):
    params = {}
    if symbol:
        params["symbol"] = symbol
    data = await _bingx_get(api_key, api_secret, "/openApi/swap/v2/user/positions", params)
    positions = data.get("data", [])
    if positions is None:
        positions = []
    return {"positions": positions, "raw": data}

async def test_bingx_read_connection(api_key: str, api_secret: str):
    balance = await get_bingx_swap_balance(api_key, api_secret)
    positions = await get_bingx_positions(api_key, api_secret)
    pos = positions["positions"]
    return {
        "ok": True,
        "available_usdt": balance["available_usdt"],
        "positions_count": len(pos) if isinstance(pos, list) else 0,
    }
