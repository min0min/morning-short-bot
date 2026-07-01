import time
import hmac
import hashlib
import math
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


async def _bingx_public_get(path: str, params: dict | None = None):
    query = urlencode(sorted((params or {}).items()))
    url = f"{BINGX_BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            text = await resp.text()
            try:
                data = await resp.json()
            except Exception:
                raise RuntimeError(f"BingX 공개 API JSON 파싱 실패: HTTP {resp.status} / {text[:300]}")

            if resp.status >= 400:
                raise RuntimeError(f"BingX 공개 API HTTP 오류: {resp.status} / {data}")

            code = str(data.get("code", "0"))
            if code not in ("0", "200"):
                raise RuntimeError(f"BingX 공개 API 오류: code={data.get('code')} msg={data.get('msg')}")

            return data

def normalize_bingx_symbol(base_or_symbol: str) -> str:
    s = str(base_or_symbol).upper().strip()
    s = s.replace("_", "-")
    if s.endswith("-USDT"):
        base = s[:-5]
    elif s.endswith("USDT"):
        base = s[:-4]
    else:
        base = s
    return f"{base}-USDT"

async def get_bingx_contracts():
    """
    BingX USDT-M perpetual futures contract list.
    """
    data = await _bingx_public_get("/openApi/swap/v2/quote/contracts", {})
    contracts = data.get("data", [])
    if contracts is None:
        contracts = []
    return contracts

async def is_bingx_futures_listed(base_or_symbol: str):
    """
    Bitget signal base/symbol -> BingX USDT-M futures listing check.
    Returns dict:
    {
      listed: bool,
      symbol: "POWR-USDT",
      raw_symbol: "POWR-USDT" or None,
      contract: {...} or None
    }
    """
    wanted = normalize_bingx_symbol(base_or_symbol)
    wanted_compact = wanted.replace("-", "")

    contracts = await get_bingx_contracts()
    for c in contracts:
        if not isinstance(c, dict):
            continue
        raw_symbol = str(c.get("symbol") or c.get("contractSymbol") or c.get("pair") or "").upper()
        raw_compact = raw_symbol.replace("-", "").replace("_", "")
        if raw_symbol == wanted or raw_compact == wanted_compact:
            status = str(c.get("status") or c.get("state") or c.get("enableTrade") or "").upper()
            listed = True
            if status in ("OFFLINE", "SUSPEND", "SUSPENDED", "FALSE", "0"):
                listed = False
            return {
                "listed": listed,
                "symbol": wanted,
                "raw_symbol": raw_symbol,
                "contract": c,
            }

    return {
        "listed": False,
        "symbol": wanted,
        "raw_symbol": None,
        "contract": None,
    }


async def _bingx_signed_request(api_key: str, api_secret: str, method: str, path: str, params: dict | None = None):
    """
    Signed request for BingX private endpoints.
    Order endpoints use signed query + X-BX-APIKEY.
    """
    if not api_key or not api_secret:
        raise ValueError("BingX API Key/Secret이 비어있습니다.")

    query = _build_signed_query(params or {}, api_secret)
    url = f"{BINGX_BASE_URL}{path}?{query}"
    headers = {"X-BX-APIKEY": api_key}

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        request_method = session.post if method.upper() == "POST" else session.get
        async with request_method(url, headers=headers) as resp:
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

async def get_bingx_symbol_price(symbol: str):
    symbol = normalize_bingx_symbol(symbol)
    data = await _bingx_public_get("/openApi/swap/v2/quote/price", {"symbol": symbol})
    obj = data.get("data", data)

    if isinstance(obj, dict):
        for key in ["price", "lastPrice", "last", "markPrice"]:
            if obj.get(key) is not None:
                return float(obj[key])

    if isinstance(obj, list) and obj:
        item = obj[0]
        for key in ["price", "lastPrice", "last", "markPrice"]:
            if item.get(key) is not None:
                return float(item[key])

    raise RuntimeError(f"BingX 가격을 찾지 못했습니다: {data}")

def _round_qty(qty: float) -> float:
    # 대부분 알트 테스트에 충분한 보수적 반올림.
    # 실제 주문 단계에서는 contract precision 기반 보정으로 업그레이드 예정.
    if qty >= 100:
        return round(qty, 0)
    if qty >= 10:
        return round(qty, 1)
    if qty >= 1:
        return round(qty, 2)
    if qty >= 0.1:
        return round(qty, 3)
    if qty >= 0.01:
        return round(qty, 4)
    return round(qty, 6)

async def calculate_market_qty_by_usdt(symbol: str, margin_usdt: float):
    symbol = normalize_bingx_symbol(symbol)
    price = await get_bingx_symbol_price(symbol)
    if price <= 0:
        raise RuntimeError("가격이 0 이하입니다.")
    qty = float(margin_usdt) / price
    qty = _round_qty(qty)
    if qty <= 0:
        raise RuntimeError("계산된 주문 수량이 0 이하입니다.")
    return {
        "symbol": symbol,
        "price": price,
        "qty": qty,
        "margin_usdt": float(margin_usdt),
    }

async def place_short_market_order(api_key: str, api_secret: str, symbol: str, margin_usdt: float):
    """
    v4.3 테스트용: market SHORT open.
    기본값은 1 USDT 수준 테스트.
    """
    calc = await calculate_market_qty_by_usdt(symbol, margin_usdt)
    params = {
        "symbol": calc["symbol"],
        "side": "SELL",
        "positionSide": "SHORT",
        "type": "MARKET",
        "quantity": calc["qty"],
    }
    data = await _bingx_signed_request(api_key, api_secret, "POST", "/openApi/swap/v2/trade/order", params)
    return {
        "ok": True,
        "action": "OPEN_SHORT",
        "symbol": calc["symbol"],
        "qty": calc["qty"],
        "price_ref": calc["price"],
        "margin_usdt": calc["margin_usdt"],
        "raw": data,
    }

def _extract_short_position_qty(positions_payload):
    positions = positions_payload.get("positions", positions_payload)
    if isinstance(positions, dict):
        positions = [positions]
    if not isinstance(positions, list):
        return 0.0, None

    for p in positions:
        if not isinstance(p, dict):
            continue
        side = str(p.get("positionSide") or p.get("side") or "").upper()
        if side and side != "SHORT":
            continue
        for key in ["positionAmt", "availableAmt", "quantity", "qty", "positionAmount", "position"]:
            val = p.get(key)
            if val is None:
                continue
            try:
                qty = abs(float(val))
                if qty > 0:
                    return qty, p
            except Exception:
                continue
    return 0.0, None

async def close_short_market_position(api_key: str, api_secret: str, symbol: str):
    """
    v4.3 테스트용: 현재 SHORT 포지션 수량을 조회해서 market BUY close.
    """
    symbol = normalize_bingx_symbol(symbol)
    positions = await get_bingx_positions(api_key, api_secret, symbol)
    qty, pos = _extract_short_position_qty(positions)

    if qty <= 0:
        raise RuntimeError(f"{symbol} SHORT 포지션 수량을 찾지 못했습니다. 이미 청산되었거나 포지션 조회 구조 확인 필요.")

    qty = _round_qty(qty)
    params = {
        "symbol": symbol,
        "side": "BUY",
        "positionSide": "SHORT",
        "type": "MARKET",
        "quantity": qty,
    }
    data = await _bingx_signed_request(api_key, api_secret, "POST", "/openApi/swap/v2/trade/order", params)
    return {
        "ok": True,
        "action": "CLOSE_SHORT",
        "symbol": symbol,
        "qty": qty,
        "position": pos,
        "raw": data,
    }


# =========================
# v4.3.1 ORDER RULES PATCH
# =========================

def _safe_float(v, default=None):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def _detect_qty_step(contract: dict):
    """
    BingX contract response fields may vary.
    Try common precision/step keys and fallback conservatively.
    """
    for key in ["quantityPrecision", "quantity_precision", "qtyPrecision", "amountPrecision", "volumePrecision"]:
        val = contract.get(key)
        if val is not None:
            try:
                p = int(float(val))
                return 10 ** (-p), p
            except Exception:
                pass

    for key in ["stepSize", "quantityStep", "qtyStep", "tradeStep", "minStep"]:
        val = _safe_float(contract.get(key))
        if val and val > 0:
            # decimal places from step
            s = f"{val:.12f}".rstrip("0")
            p = len(s.split(".")[1]) if "." in s else 0
            return val, p

    return 1.0, 0

def _detect_min_qty(contract: dict):
    for key in [
        "minQty", "minQuantity", "minTradeNum", "minTradeQuantity",
        "minVolume", "minOrderQuantity", "minAmount"
    ]:
        val = _safe_float(contract.get(key))
        if val and val > 0:
            return val
    return None

def _detect_min_notional(contract: dict):
    for key in ["minNotional", "minOrderValue", "minTradeAmount", "minOrderAmount"]:
        val = _safe_float(contract.get(key))
        if val and val > 0:
            return val
    return None

def _ceil_to_step(value: float, step: float, precision: int):
    if step <= 0:
        return round(value, precision)
    return round(math.ceil((value / step) - 1e-12) * step, precision)

def _extract_min_qty_from_error(error_text: str):
    """
    Example:
    The minimum order amount is 28 DOGE.
    """
    import re
    m = re.search(r"minimum order amount is\s+([0-9]+(?:\.[0-9]+)?)", str(error_text), re.I)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

async def get_bingx_contract_rule(symbol: str):
    """
    Get contract rule from BingX contracts endpoint.
    """
    symbol = normalize_bingx_symbol(symbol)
    listing = await is_bingx_futures_listed(symbol)
    contract = listing.get("contract") or {}

    if not listing.get("listed"):
        raise RuntimeError(f"{symbol} is not listed on BingX USDT-M futures.")

    step, precision = _detect_qty_step(contract)
    min_qty = _detect_min_qty(contract)
    min_notional = _detect_min_notional(contract)

    return {
        "symbol": symbol,
        "listed": True,
        "raw_symbol": listing.get("raw_symbol") or symbol,
        "contract": contract,
        "qty_step": step,
        "qty_precision": precision,
        "min_qty": min_qty,
        "min_notional": min_notional,
    }

async def calculate_market_qty_by_usdt(symbol: str, margin_usdt: float):
    """
    v4.3.1:
    User can request 1 USDT, but actual order quantity is adjusted up to
    BingX contract minimum qty / minimum notional where available.
    """
    symbol = normalize_bingx_symbol(symbol)
    price = await get_bingx_symbol_price(symbol)
    if price <= 0:
        raise RuntimeError("가격이 0 이하입니다.")

    rule = await get_bingx_contract_rule(symbol)

    requested_qty = float(margin_usdt) / price
    min_qty = rule.get("min_qty")
    min_notional = rule.get("min_notional")
    step = float(rule.get("qty_step") or 1.0)
    precision = int(rule.get("qty_precision") or 0)

    required_qty = requested_qty

    if min_qty and min_qty > required_qty:
        required_qty = min_qty

    if min_notional and min_notional > 0:
        notional_qty = min_notional / price
        if notional_qty > required_qty:
            required_qty = notional_qty

    qty = _ceil_to_step(required_qty, step, precision)
    actual_notional = qty * price

    if qty <= 0:
        raise RuntimeError("계산된 주문 수량이 0 이하입니다.")

    return {
        "symbol": symbol,
        "price": price,
        "requested_margin_usdt": float(margin_usdt),
        "requested_qty": requested_qty,
        "qty": qty,
        "actual_notional_usdt": actual_notional,
        "rule": rule,
        "adjusted": qty > requested_qty,
    }

async def place_short_market_order(api_key: str, api_secret: str, symbol: str, margin_usdt: float):
    """
    v4.3.1 rule-aware market SHORT open.
    If BingX still returns min amount error, retry once using min qty parsed from error.
    """
    calc = await calculate_market_qty_by_usdt(symbol, margin_usdt)

    async def send(qty):
        params = {
            "symbol": calc["symbol"],
            "side": "SELL",
            "positionSide": "SHORT",
            "type": "MARKET",
            "quantity": qty,
        }
        return await _bingx_signed_request(api_key, api_secret, "POST", "/openApi/swap/v2/trade/order", params)

    try:
        data = await send(calc["qty"])
    except Exception as e:
        min_qty_from_err = _extract_min_qty_from_error(str(e))
        if not min_qty_from_err:
            raise

        rule = calc["rule"]
        step = float(rule.get("qty_step") or 1.0)
        precision = int(rule.get("qty_precision") or 0)
        retry_qty = _ceil_to_step(min_qty_from_err, step, precision)

        if retry_qty <= calc["qty"]:
            raise

        print(f"[ORDER RULE RETRY] {calc['symbol']} qty {calc['qty']} -> {retry_qty} from exchange error")
        calc["qty"] = retry_qty
        calc["actual_notional_usdt"] = retry_qty * calc["price"]
        calc["adjusted"] = True
        calc["min_qty_from_error"] = min_qty_from_err
        data = await send(calc["qty"])

    return {
        "ok": True,
        "action": "OPEN_SHORT",
        "symbol": calc["symbol"],
        "qty": calc["qty"],
        "price_ref": calc["price"],
        "margin_usdt": calc["requested_margin_usdt"],
        "requested_qty": calc["requested_qty"],
        "actual_notional_usdt": calc["actual_notional_usdt"],
        "adjusted": calc["adjusted"],
        "rule": calc["rule"],
        "raw": data,
    }


# ==============================
# v4.4.1 IMPORT HOTFIX
# Missing v4.3.3 leverage/fill wrappers restored.
# ==============================

def _extract_order_id(raw):
    if not isinstance(raw, dict):
        return None
    data = raw.get("data")
    if isinstance(data, dict):
        return data.get("orderId") or data.get("orderID") or data.get("id")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0].get("orderId") or data[0].get("orderID") or data[0].get("id")
    return raw.get("orderId") or raw.get("orderID") or raw.get("id")

def _parse_avg_price_and_qty_from_order_payload(payload):
    if not isinstance(payload, dict):
        return {"avg_price": None, "executed_qty": None, "fee": 0.0, "realized_pnl": None, "raw": payload}

    obj = payload.get("data", payload)

    if isinstance(obj, list):
        total_qty = 0.0
        total_value = 0.0
        fee = 0.0
        realized = 0.0
        realized_seen = False

        for item in obj:
            if not isinstance(item, dict):
                continue

            price = _safe_float(item.get("price") or item.get("filledPrice") or item.get("avgPrice") or item.get("dealPrice"), None)
            qty = _safe_float(item.get("qty") or item.get("quantity") or item.get("executedQty") or item.get("filledQty") or item.get("volume"), None)

            if price is not None and qty is not None:
                total_qty += abs(qty)
                total_value += abs(qty) * price

            fee += float(_safe_float(item.get("fee") or item.get("commission"), 0.0) or 0.0)

            rp = _safe_float(item.get("realizedPnl") or item.get("realizedPNL") or item.get("profit"), None)
            if rp is not None:
                realized += rp
                realized_seen = True

        avg = (total_value / total_qty) if total_qty else None
        return {
            "avg_price": avg,
            "executed_qty": total_qty if total_qty else None,
            "fee": fee,
            "realized_pnl": realized if realized_seen else None,
            "raw": payload,
        }

    if isinstance(obj, dict):
        avg = _safe_float(
            obj.get("avgPrice") or obj.get("priceAvg") or obj.get("executedPrice") or
            obj.get("filledPrice") or obj.get("price") or obj.get("dealAvgPrice"),
            None
        )
        qty = _safe_float(
            obj.get("executedQty") or obj.get("filledQty") or obj.get("cumQty") or
            obj.get("quantity") or obj.get("qty") or obj.get("volume"),
            None
        )
        fee = _safe_float(obj.get("fee") or obj.get("commission"), 0.0) or 0.0
        realized = _safe_float(obj.get("realizedPnl") or obj.get("realizedPNL") or obj.get("profit"), None)
        return {
            "avg_price": avg,
            "executed_qty": abs(qty) if qty is not None else None,
            "fee": fee,
            "realized_pnl": realized,
            "raw": payload,
        }

    return {"avg_price": None, "executed_qty": None, "fee": 0.0, "realized_pnl": None, "raw": payload}

async def set_bingx_leverage(api_key: str, api_secret: str, symbol: str, leverage: int = 4):
    symbol = normalize_bingx_symbol(symbol)
    params = {"symbol": symbol, "side": "SHORT", "leverage": int(leverage)}
    return await _bingx_signed_request(api_key, api_secret, "POST", "/openApi/swap/v2/trade/leverage", params)

async def get_bingx_order_detail(api_key: str, api_secret: str, symbol: str, order_id):
    symbol = normalize_bingx_symbol(symbol)
    if not order_id:
        return None

    candidates = [
        ("/openApi/swap/v2/trade/order", {"symbol": symbol, "orderId": order_id}),
        ("/openApi/swap/v2/trade/allOrders", {"symbol": symbol, "orderId": order_id, "limit": 1}),
    ]

    last_error = None
    for path, params in candidates:
        try:
            return await _bingx_signed_request(api_key, api_secret, "GET", path, params)
        except Exception as e:
            last_error = e
            continue

    print(f"[ORDER DETAIL ERROR] {type(last_error).__name__}: {last_error}")
    return None

async def get_bingx_order_fills(api_key: str, api_secret: str, symbol: str, order_id=None):
    symbol = normalize_bingx_symbol(symbol)
    candidates = []

    if order_id:
        candidates.extend([
            ("/openApi/swap/v2/trade/allFillOrders", {"symbol": symbol, "orderId": order_id, "limit": 50}),
            ("/openApi/swap/v2/trade/fillHistory", {"symbol": symbol, "orderId": order_id, "limit": 50}),
            ("/openApi/swap/v2/trade/fills", {"symbol": symbol, "orderId": order_id, "limit": 50}),
        ])

    candidates.extend([
        ("/openApi/swap/v2/trade/allFillOrders", {"symbol": symbol, "limit": 20}),
        ("/openApi/swap/v2/trade/fillHistory", {"symbol": symbol, "limit": 20}),
        ("/openApi/swap/v2/trade/fills", {"symbol": symbol, "limit": 20}),
    ])

    last_error = None
    for path, params in candidates:
        try:
            return await _bingx_signed_request(api_key, api_secret, "GET", path, params)
        except Exception as e:
            last_error = e
            continue

    print(f"[ORDER FILLS ERROR] {type(last_error).__name__}: {last_error}")
    return None

async def get_fill_summary(api_key: str, api_secret: str, symbol: str, order_id=None, fallback_raw=None):
    detail = await get_bingx_order_detail(api_key, api_secret, symbol, order_id)
    summary = _parse_avg_price_and_qty_from_order_payload(detail)
    if summary.get("avg_price") or summary.get("executed_qty") or summary.get("realized_pnl") is not None:
        summary["source"] = "order_detail"
        return summary

    fills = await get_bingx_order_fills(api_key, api_secret, symbol, order_id)
    summary = _parse_avg_price_and_qty_from_order_payload(fills)
    if summary.get("avg_price") or summary.get("executed_qty") or summary.get("realized_pnl") is not None:
        summary["source"] = "fills"
        return summary

    summary = _parse_avg_price_and_qty_from_order_payload(fallback_raw)
    summary["source"] = "order_response_fallback"
    return summary

async def place_short_market_order_with_leverage(api_key: str, api_secret: str, symbol: str, margin_usdt: float, leverage: int = 4):
    leverage_result = None
    leverage_error = None

    try:
        leverage_result = await set_bingx_leverage(api_key, api_secret, symbol, leverage)
        print(f"[LEVERAGE SET] {symbol} {leverage}x")
    except Exception as e:
        leverage_error = f"{type(e).__name__}: {e}"
        print(f"[LEVERAGE SET ERROR] {leverage_error}")

    result = await place_short_market_order(api_key, api_secret, symbol, margin_usdt)
    order_id = _extract_order_id(result.get("raw"))
    fill = await get_fill_summary(api_key, api_secret, result["symbol"], order_id, fallback_raw=result.get("raw"))

    result["order_id"] = order_id
    result["leverage"] = int(leverage)
    result["leverage_result"] = leverage_result
    result["leverage_error"] = leverage_error
    result["fill"] = fill

    if fill.get("avg_price"):
        result["filled_avg_price"] = fill.get("avg_price")
    if fill.get("executed_qty"):
        result["executed_qty"] = fill.get("executed_qty")

    return result

async def close_short_market_position_with_fills(api_key: str, api_secret: str, symbol: str):
    result = await close_short_market_position(api_key, api_secret, symbol)
    order_id = _extract_order_id(result.get("raw"))
    fill = await get_fill_summary(api_key, api_secret, result["symbol"], order_id, fallback_raw=result.get("raw"))

    result["order_id"] = order_id
    result["fill"] = fill

    if fill.get("avg_price"):
        result["filled_avg_price"] = fill.get("avg_price")
    if fill.get("executed_qty"):
        result["executed_qty"] = fill.get("executed_qty")
    if fill.get("realized_pnl") is not None:
        result["realized_pnl"] = fill.get("realized_pnl")
    if fill.get("fee") is not None:
        result["fee"] = fill.get("fee")

    return result
