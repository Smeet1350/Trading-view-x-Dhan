# webhook.py
import json, time, uuid
from datetime import datetime
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Dict

# import your existing stuff
from config import SQLITE_PATH
from scheduler import ensure_fresh_db
from orders import (
    broker_ready, place_order_via_broker, normalize_response
)

# ---- If importing LOG, ALERTS_LOG from main.py created a circular import: ----
# Comment the import above and paste small local shims here instead:
import logging
LOG = logging.getLogger("backend")
try:
    from collections import deque
    ALERTS_LOG = deque(maxlen=500)  # same shape as your in-memory feed
    def _prune_alerts(): pass
except Exception:
    pass
# ------------------------------------------------------------------------------

router = APIRouter()

async def _parse_tv_request(req: Request) -> Dict:
    """
    Accept JSON, raw JSON text, or form-encoded alert=<json>.
    """
    # 1) application/json
    try:
        return await req.json()
    except Exception:
        pass

    # 2) x-www-form-urlencoded (TradingView "alert" field)
    try:
        form = await req.form()
        if "alert" in form:
            return json.loads(str(form["alert"]))
    except Exception:
        pass

    # 3) raw body as JSON text
    try:
        raw = (await req.body() or b"").decode().strip()
        if raw:
            return json.loads(raw)
    except Exception:
        pass

    return {}

async def _process(req: Request) -> Dict:
    body = await _parse_tv_request(req)
    LOG.info("Webhook payload: %s", body)

    # Allow simple equity payloads as well (symbol/side/quantity)
    is_equity = "symbol" in body

    try:
        ensure_fresh_db(SQLITE_PATH)
        ok, why = broker_ready()
        if not ok:
            return {"status": "error", "message": f"Broker not ready: {why}"}

        if is_equity:
            symbol = str(body.get("symbol") or "").strip()
            if not symbol:
                return {"status":"error","message":"Missing symbol"}
            side = str(body.get("side","BUY")).upper()
            qty  = int(body.get("quantity") or body.get("qty") or 1)
            order_type = str(body.get("order_type","MARKET")).upper()
            price = float(body.get("price") or 0)
            product_type = str(body.get("product_type","INTRADAY")).upper()
            validity = str(body.get("validity","DAY")).upper()

            # For equity, we need to find by symbol directly
            from scheduler import resolve_symbol
            inst = resolve_symbol(SQLITE_PATH, symbol, "NSE_EQ")
            if not inst or not inst.get("securityId"):
                return {"status": "error", "message": f"No instrument for {symbol}"}
            segment = inst.get("segment") or "NSE_EQ"

            raw_res = place_order_via_broker(
                security_id=str(inst["securityId"]),
                segment=segment,
                side=side,
                qty=qty,
                order_type=order_type,
                price=None if order_type=="MARKET" else price,
                product_type=product_type,
                validity=validity,
                symbol=inst["tradingSymbol"],
                disclosed_qty=0,
            )
            res = normalize_response(raw_res, success_msg="Equity order placed", error_msg="Equity order failed")

        else:
            # Options payload (index/strike/option_type/lots or qty)
            index_symbol = str(body.get("index","")).upper()
            raw_strike = int(body.get("strike") or 0)
            option_type = str(body.get("option_type","")).upper()
            side = str(body.get("side","BUY")).upper()
            order_type = str(body.get("order_type","MARKET")).upper()
            price = float(body.get("price") or 0)
            product_type = str(body.get("product_type","INTRADAY")).upper()
            validity = str(body.get("validity","DAY")).upper()

            if not index_symbol or raw_strike <= 0 or option_type not in ("CE","PE"):
                return {"status":"error","message":"Invalid options payload"}

            # Import helper functions
            from webhook import round_strike, find_instrument, infer_segment_from_symbol
            
            strike = round_strike(raw_strike, index_symbol)
            inst = find_instrument(SQLITE_PATH, index_symbol, strike, option_type)
            if not inst:
                return {"status": "error", "message": f"No instrument for {index_symbol} {strike}{option_type}"}

            lot_size = int(inst.get("lotSize") or 1)
            lots = int(body.get("lots") or 0)
            qty  = int(body.get("qty") or 0)
            if lots > 0:
                qty = lots * lot_size
            elif qty <= 0:
                qty = lot_size
            elif qty % lot_size != 0:
                return {"status":"error","message":f"Qty {qty} not multiple of lot {lot_size}"}

            segment = inst.get("segment") or infer_segment_from_symbol(inst["tradingSymbol"])
            raw_res = place_order_via_broker(
                security_id=str(inst["securityId"]),
                segment=segment,
                side=side,
                qty=qty,
                order_type=order_type,
                price=None if order_type=="MARKET" else price,
                product_type=product_type,
                validity=validity,
                symbol=inst["tradingSymbol"],
                disclosed_qty=0,
            )
            res = normalize_response(raw_res, success_msg="F&O order placed", error_msg="F&O order failed")

        # append to in-memory alerts feed
        from webhook import _rollover_if_new_day
        _rollover_if_new_day()
        alert_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "ts_epoch": int(time.time()*1000),
            "request": body,
            "instrument": {k: res.get("symbol") if k=="tradingSymbol" else v for k,v in ({} if not is_equity else {"tradingSymbol": symbol}).items()},
            "response": res,
        }
        try:
            ALERTS_LOG.appendleft(alert_entry)  # if deque
        except Exception:
            ALERTS_LOG.insert(0, alert_entry)   # if list
        _prune_alerts()

        status_code = 200 if res.get("status") == "success" else 400
        return res | {"status_code": status_code}

    except Exception as e:
        LOG.exception("Webhook processing failed")
        return {"status":"error","message":str(e)}

# Routes that all hit the same processor
@router.post("/")
async def webhook_root(req: Request):
    out = await _process(req); code = out.pop("status_code", 200)
    return JSONResponse(status_code=code, content=out)

@router.post("/webhook")
async def webhook_compat(req: Request):
    out = await _process(req); code = out.pop("status_code", 200)
    return JSONResponse(status_code=code, content=out)

@router.post("/webhook/trade")
async def webhook_trade(req: Request):
    out = await _process(req); code = out.pop("status_code", 200)
    return JSONResponse(status_code=code, content=out)

# Helper functions for options trading
def round_strike(strike: int, index_symbol: str) -> int:
    """Round strike price to valid trading levels based on index."""
    step = 50 if "NIFTY" in index_symbol.upper() else 100
    return round(strike / step) * step

def infer_segment_from_symbol(symbol: str) -> str:
    """Infer segment from trading symbol when database segment is None."""
    s = symbol.upper()
    if any(idx in s for idx in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")):
        return "NSE_FNO"
    if "MCX" in s:
        return "MCX"
    if "BSE" in s:
        return "BSE_EQ"
    if "NSE" in s:
        return "NSE_EQ"
    return "NSE_FNO"  # safe default

def find_instrument(db_path: str, index_symbol: str, strike: int, option_type: str) -> dict:
    """Find instrument based on actual DB format."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        sql = """
            SELECT securityId, tradingSymbol, segment, lotSize, expiry
            FROM instruments
            WHERE UPPER(tradingSymbol) LIKE ?
              AND UPPER(tradingSymbol) LIKE ?
        """
        like_index = f"{index_symbol.upper()}%"
        like_suffix = f"%-{strike}-{option_type.upper()}"
        rows = conn.execute(sql, (like_index, like_suffix)).fetchall()

        if not rows:
            return {}

        cols = ["securityId", "tradingSymbol", "segment", "lotSize", "expiry"]
        today = datetime.now().date()

        valid = []
        for r in rows:
            rec = dict(zip(cols, r))
            expd = parse_expiry(rec.get("expiry", ""))
            if expd and expd >= today:
                valid.append((expd, rec))

        if not valid:
            return {}

        valid.sort(key=lambda x: x[0])
        return valid[0][1]

    finally:
        conn.close()

def parse_expiry(exp_str: str):
    """Robust expiry date parsing."""
    if not exp_str or exp_str == "0001-01-01":
        return None
    try:
        return datetime.strptime(exp_str, "%Y-%m-%d").date()
    except Exception:
        try:
            from dateutil import parser
            return parser.parse(exp_str, fuzzy=True).date()
        except Exception:
            return None

def _rollover_if_new_day():
    """Simple rollover function."""
    pass

# Alerts endpoint
@router.get("/webhook/alerts")
def get_alerts(limit: int = 100):
    """Get recent webhook alerts."""
    limit = max(1, min(limit, 500))
    alerts_list = list(ALERTS_LOG)[:limit] if hasattr(ALERTS_LOG, '__iter__') else []
    return {"status": "success", "alerts": alerts_list}

# Test endpoint
@router.post("/webhook/test")
async def webhook_test(req: Request):
    sample = {
        "index": "NIFTY", "strike": 20000, "option_type": "CE", "side": "BUY",
        "order_type": "MARKET", "lots": 1
    }
    from fastapi import Request
    class MockRequest:
        async def json(self): return sample
        async def form(self): return {}
        async def body(self): return b""
    return await _process(MockRequest())