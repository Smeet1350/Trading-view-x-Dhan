# webhook.py
import logging
import sqlite3
import uuid
import time
import pytz
from datetime import datetime, date
from fastapi import APIRouter, Request
from dateutil import parser

from orders import broker_ready, place_order_via_broker, normalize_response
from scheduler import ensure_fresh_db
from config import SQLITE_PATH

LOG = logging.getLogger("webhook")
ALERTS_LOGGER = logging.getLogger("alerts")
router = APIRouter(prefix="/webhook", tags=["webhook"])

# Global alerts log - newest first
IST = pytz.timezone("Asia/Kolkata")
ALERTS_LOG = []         # newest first
MAX_ALERTS = 200
_LOG_DAY = None         # IST date for rollover

def _today_ist():
    return datetime.now(IST).date()

def _rollover_if_new_day():
    global _LOG_DAY, ALERTS_LOG
    today = _today_ist()
    if _LOG_DAY is None:
        _LOG_DAY = today
    elif _LOG_DAY != today:
        ALERTS_LOG.clear()
        _LOG_DAY = today

def _prune_alerts():
    """Bound memory: drop alerts older than 24h and cap to MAX_ALERTS."""
    from datetime import timedelta
    cutoff = datetime.now(IST) - timedelta(days=1)
    keep = []
    for a in ALERTS_LOG:
        try:
            ts = datetime.fromisoformat(a.get("timestamp", ""))
        except Exception:
            ts = None
        if ts and ts >= cutoff:
            keep.append(a)
    ALERTS_LOG[:] = keep[:MAX_ALERTS]


def parse_expiry(exp_str: str):
    """Robust expiry date parsing."""
    if not exp_str or exp_str == "0001-01-01":
        return None
    try:
        return datetime.strptime(exp_str, "%Y-%m-%d").date()
    except Exception:
        try:
            return parser.parse(exp_str, fuzzy=True).date()
        except Exception:
            return None


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


def round_strike(strike: int, index_symbol: str) -> int:
    """Round strike price to valid trading levels based on index."""
    step = 50 if "NIFTY" in index_symbol.upper() else 100
    return round(strike / step) * step


def find_instrument(db_path: str, index_symbol: str, strike: int, option_type: str) -> dict:
    """Find instrument based on actual DB format."""
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


# Backward compat: accept POST /webhook and POST /webhook/
@router.post("")
async def webhook_root(req: Request):
    return await webhook_trade(req)

@router.post("/")
async def webhook_slash(req: Request):
    return await webhook_trade(req)

@router.post("/trade")
async def webhook_trade(req: Request):
    """Webhook endpoint for option trades."""
    body = await req.json()
    LOG.info("Webhook payload: %s", body)

    try:
        ensure_fresh_db(SQLITE_PATH)

        ok, why = broker_ready()
        if not ok:
            return {"status": "error", "message": f"Broker not ready: {why}"}

        index_symbol = str(body.get("index", "")).upper()
        raw_strike = int(body.get("strike", 0))
        option_type = str(body.get("option_type", "")).upper()
        side = str(body.get("side", "BUY")).upper()
        order_type = str(body.get("order_type", "MARKET")).upper()
        price = float(body.get("price") or 0)
        product_type = str(body.get("product_type", "INTRADAY")).upper()
        validity = str(body.get("validity", "DAY")).upper()

        if not index_symbol or raw_strike <= 0 or option_type not in ("CE", "PE"):
            return {"status": "error", "message": "Invalid input"}

        # Round strike to valid trading levels
        strike = round_strike(raw_strike, index_symbol)
        LOG.info("Strike rounded: %s -> %s (%s)", raw_strike, strike, index_symbol)

        inst = find_instrument(SQLITE_PATH, index_symbol, strike, option_type)
        if not inst:
            return {"status": "error", "message": f"No instrument found for {index_symbol} {strike}{option_type}"}

        lot_size = int(inst.get("lotSize") or 1)

        # Quantity calculation
        lots = int(body.get("lots", 0))   # new param
        qty = int(body.get("qty", 0))     # backward-compatible

        if lots > 0:
            qty = lots * lot_size
        elif qty > 0:
            if qty % lot_size != 0:
                return {"status": "error", "message": f"Qty {qty} not multiple of lot {lot_size}"}
        else:
            qty = lot_size  # default to 1 lot if nothing given

        LOG.info("Order qty resolved: lots=%s lotSize=%s -> qty=%s", lots, lot_size, qty)

        # Instrument validation
        if not inst.get("securityId"):
            return {"status": "error", "message": "Instrument missing securityId"}
        
        if not inst.get("lotSize"):
            return {"status": "error", "message": "Instrument missing lotSize"}

        # Segment fallback logic
        segment = inst.get("segment") or infer_segment_from_symbol(inst["tradingSymbol"])
        if not segment:
            return {"status": "error", "message": f"Could not infer segment for {inst}"}

        LOG.debug("Final instrument for order: %s", inst)
        LOG.debug("Using segment=%s, lotSize=%s, securityId=%s",
                  segment, inst.get("lotSize"), inst.get("securityId"))

        raw_res = place_order_via_broker(
            security_id=str(inst["securityId"]),
            segment=segment,
            side=side,
            qty=qty,
            order_type=order_type,
            price=None if order_type == "MARKET" else price,
            product_type=product_type,
            validity=validity,
            symbol=inst["tradingSymbol"],
            disclosed_qty=0,
        )
        result = normalize_response(raw_res, success_msg="Order placed via webhook", error_msg="Webhook order failed")

        _rollover_if_new_day()
        alert_entry = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(IST).isoformat(),
            "ts_epoch": int(time.time() * 1000),
            "request": body,
            "instrument": inst,
            "response": result,
        }
        ALERTS_LOG.insert(0, alert_entry)
        _prune_alerts()
        ALERTS_LOGGER.info("ALERT | %s", alert_entry)
        return result

    except Exception as e:
        LOG.exception("Webhook trade failed")
        return {"status": "error", "message": str(e)}


@router.post("/test")
async def webhook_test(req: Request):
    sample = {
        "index": "NIFTY", "strike": 20000, "option_type": "CE", "side": "BUY",
        "order_type": "MARKET", "lots": 1
    }
    return await webhook_trade(type("obj", (object,), {"json": lambda: sample})())

@router.get("/alerts")
def get_alerts(limit: int = 100):
    """Get recent webhook alerts."""
    _rollover_if_new_day()
    _prune_alerts()
    limit = max(1, min(limit, MAX_ALERTS))
    return {"status": "success", "alerts": ALERTS_LOG[:limit]}
