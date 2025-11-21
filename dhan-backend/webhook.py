# webhook.py
import json
import logging
import sqlite3
import uuid
import os
from datetime import datetime
from fastapi import APIRouter, Request
from dateutil import parser

from orders import broker_ready, place_order_via_broker, normalize_response, map_product_for_sdk
from scheduler import ensure_fresh_db
from config import SQLITE_PATH, WEBHOOK_API_KEY, WEBHOOK_IP_WHITELIST, WEBHOOK_RATE_LIMIT
import time

LOG = logging.getLogger("webhook")
ALERTS_LOGGER = logging.getLogger("alerts")
router = APIRouter(prefix="/webhook", tags=["webhook"])

# Paper trading integration
def _paper_enabled():
    """Check if paper trading mode is enabled"""
    try:
        from paper_trading import _read_enabled
        return _read_enabled()
    except Exception:
        return False

# In-memory small rate-limiter store: { client_ip: [timestamps...] }
# Lightweight and resets when the process restarts.
RATE_LIMIT_STORE = {}
RATE_LIMIT_WINDOW_SECONDS = 60  # window for WEBHOOK_RATE_LIMIT (per-minute)

# Global alerts log - newest first
ALERTS_LOG = []
MAX_ALERTS = 100


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
    with sqlite3.connect(db_path) as conn:
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


def find_futures_instrument(db_path: str, index_symbol: str, expiry_hint: str | None = None) -> dict:
    """
    Find a futures instrument for the given index (e.g., NIFTY, BANKNIFTY).
    - If expiry_hint is provided (any parseable date), we prefer that expiry.
    - Otherwise we pick the nearest non-expired contract.
    Assumes Dhan tradingSymbol format includes '-FUT' and an expiry date string column.
    """
    with sqlite3.connect(db_path) as conn:
        sql = """
            SELECT securityId, tradingSymbol, segment, lotSize, expiry
            FROM instruments
            WHERE UPPER(tradingSymbol) LIKE ?
              AND UPPER(tradingSymbol) LIKE '%-FUT'
        """
        like_index = f"{index_symbol.upper()}%"
        rows = conn.execute(sql, (like_index,)).fetchall()
        if not rows:
            return {}

        cols = ["securityId", "tradingSymbol", "segment", "lotSize", "expiry"]
        today = datetime.now().date()

        # Parse rows with usable expiry >= today
        candidates = []
        for r in rows:
            rec = dict(zip(cols, r))
            expd = parse_expiry(rec.get("expiry", ""))
            if expd and expd >= today:
                candidates.append((expd, rec))

        if not candidates:
            return {}

        # If user hinted a specific expiry, try to match closest to that date
        if expiry_hint:
            try:
                target = parse_expiry(expiry_hint)
            except Exception:
                target = None
            if target:
                # sort by absolute distance from target, then by nearest future
                candidates.sort(key=lambda x: (abs((x[0] - target).days), x[0]))
                return candidates[0][1]

        # Default: nearest non-expired future (earliest expiry >= today)
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]


@router.post("/trade")
async def webhook_trade(req: Request):
    """Webhook endpoint for option trades."""
    body = await req.json()
    LOG.info("Webhook payload: %s", body)

    # ------ Security checks (optional, enabled via env vars) ------
    client_host = None
    try:
        client_host = req.client.host if req.client else None
    except Exception:
        client_host = None

    # 1) IP whitelist (if configured)
    if WEBHOOK_IP_WHITELIST:
        if not client_host or client_host not in WEBHOOK_IP_WHITELIST:
            LOG.warning("Webhook rejected: client ip %s not in whitelist", client_host)
            return {"status": "error", "message": "IP not allowed"}

    # 2) API key check (if configured)
    if WEBHOOK_API_KEY:
        # Clients must set header "X-Webhook-Key"
        provided = req.headers.get("x-webhook-key") or req.headers.get("X-Webhook-Key")
        if not provided or provided != WEBHOOK_API_KEY:
            LOG.warning("Webhook rejected: missing/invalid API key from %s", client_host)
            return {"status": "error", "message": "Invalid or missing API key"}

    # 3) Simple in-memory rate limiting (per-client IP)
    if WEBHOOK_RATE_LIMIT and WEBHOOK_RATE_LIMIT > 0:
        now = time.time()
        ip = client_host or "unknown"
        bucket = RATE_LIMIT_STORE.setdefault(ip, [])
        # remove timestamps older than window
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= WEBHOOK_RATE_LIMIT:
            LOG.warning("Webhook rate-limited for %s (limit=%s/min)", ip, WEBHOOK_RATE_LIMIT)
            return {"status": "error", "message": "Rate limit exceeded"}
        # record this request
        bucket.append(now)
    # ---------------------------------------------------------------

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

        # Generate request ID for tracking
        rid = str(uuid.uuid4())[:8]
        
        LOG.info("(%s) Options webhook: index=%s strike=%s option_type=%s side=%s product_type=%s segment=%s", 
                 rid, index_symbol, strike, option_type, side, product_type, segment)
        LOG.debug("(%s) Final instrument: %s", rid, inst)

        # --- PAPER TRADING SHORT-CIRCUIT ---
        if _paper_enabled():
            # Record as paper trade instead of executing live
            from paper_trading import execute_paper_trade_using_alert, fetch_ltp_from_dhan
            
            # For MARKET orders, fetch LTP; for LIMIT orders, use provided price
            exec_price = price if order_type == "LIMIT" and price > 0 else None
            if exec_price is None:
                ltp = fetch_ltp_from_dhan(str(inst["securityId"]), segment)
                if ltp is None or ltp <= 0:
                    LOG.warning("(%s) Paper trade: Could not fetch LTP (market closed / no data), skipping paper trade", rid)
                    result = {"status": "success", "message": "Paper trade skipped - LTP unavailable (market closed)", "data": {"simulated": True, "skipped": True}}
                else:
                    exec_price = ltp
            
            if exec_price and exec_price > 0:
                # Build payload for paper trading
                paper_payload = {
                    "trading_symbol": inst["tradingSymbol"],
                    "security_id": str(inst["securityId"]),
                    "segment": segment,
                    "side": side,
                    "qty": qty,
                    "price": exec_price,
                    "order_type": order_type,
                    "rid": rid
                }
                result = execute_paper_trade_using_alert(paper_payload)
                if result.get("status") == "error":
                    LOG.error("(%s) Paper trade failed: %s", rid, result.get("message"))
                else:
                    result["data"] = {"simulated": True}
                    result["message"] = result.get("message", "Paper trade recorded")
        else:
            # real live order path (unchanged)
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
                rid=rid,
            )
            result = normalize_response(raw_res, success_msg="Order placed via webhook", error_msg="Webhook order failed")

        # Attach request info to alerts log
        from copy import deepcopy
        alert_entry = {
            "id": rid,
            "timestamp": datetime.now().isoformat(),
            "trade": deepcopy(body),     # full original trade payload
            "instrument": inst,          # resolved instrument details
            "qty": qty,                  # final computed quantity
            "lots": lots,                # explicit lots entered
            "lot_size": lot_size,        # lot size used for calculation
            "response": result,          # broker response (success/failure + orderId etc.)
        }

        # Store in in-memory list for dashboard
        ALERTS_LOG.insert(0, alert_entry)
        if len(ALERTS_LOG) > MAX_ALERTS:
            ALERTS_LOG.pop()

        # Log persistently for terminal/log files
        ALERTS_LOGGER.info("ALERT | %s", alert_entry)


        return result

    except Exception as e:
        LOG.exception("Webhook trade failed")
        return {"status": "error", "message": str(e)}


@router.post("/futures")
async def webhook_futures(req: Request):
    """
    Webhook endpoint for FUTURES trades.
    Body example:
    {
      "index": "NIFTY" | "BANKNIFTY" | "FINNIFTY" | "MIDCPNIFTY" | <F&O stock>,
      "side": "BUY" | "SELL",
      "order_type": "MARKET" | "LIMIT",
      "price": 0,                          # required for LIMIT
      "product_type": "INTRADAY" | "INTRA" | "DELIVERY" | "CNC",   # F&O will auto-force INTRADAY if CNC passed
      "validity": "DAY" | "IOC",
      "lots": 1,                            # preferred (qty = lots * lotSize)
      "qty": 0,                             # optional; multiple of lotSize if used
      "expiry": "2025-09-25"                # optional hint; nearest non-expired FUT will be chosen if omitted
    }
    """
    body = await req.json()
    LOG.info("Futures webhook payload: %s", body)

    # ------ Security checks (same as options) ------
    client_host = None
    try:
        client_host = req.client.host if req.client else None
    except Exception:
        client_host = None

    if WEBHOOK_IP_WHITELIST:
        if not client_host or client_host not in WEBHOOK_IP_WHITELIST:
            LOG.warning("Webhook rejected: client ip %s not in whitelist", client_host)
            return {"status": "error", "message": "IP not allowed"}

    if WEBHOOK_API_KEY:
        provided = req.headers.get("x-webhook-key") or req.headers.get("X-Webhook-Key")
        if not provided or provided != WEBHOOK_API_KEY:
            LOG.warning("Webhook rejected: missing/invalid API key from %s", client_host)
            return {"status": "error", "message": "Invalid or missing API key"}

    # Simple in-memory rate limiting (same as options)
    if WEBHOOK_RATE_LIMIT and WEBHOOK_RATE_LIMIT > 0:
        now = time.time()
        ip = client_host or "unknown"
        bucket = RATE_LIMIT_STORE.setdefault(ip, [])
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= WEBHOOK_RATE_LIMIT:
            LOG.warning("Webhook rate-limited for %s (limit=%s/min)", ip, WEBHOOK_RATE_LIMIT)
            return {"status": "error", "message": "Rate limit exceeded"}
        bucket.append(now)
    # ------------------------------------------------

    try:
        ensure_fresh_db(SQLITE_PATH)  # keep instruments up-to-date

        ok, why = broker_ready()
        if not ok:
            return {"status": "error", "message": f"Broker not ready: {why}"}

        index_symbol = str(body.get("index", "")).upper().strip()
        side        = str(body.get("side", "BUY")).upper().strip()
        order_type  = str(body.get("order_type", "MARKET")).upper().strip()
        price       = float(body.get("price") or 0)
        product_type= str(body.get("product_type", "INTRADAY")).upper().strip()
        validity    = str(body.get("validity", "DAY")).upper().strip()
        lots        = int(body.get("lots", 0))
        qty         = int(body.get("qty", 0))
        expiry_hint = body.get("expiry")  # any parseable string or YYYY-MM-DD

        if not index_symbol or side not in ("BUY", "SELL"):
            return {"status": "error", "message": "Invalid input"}

        # Find FUT instrument
        inst = find_futures_instrument(SQLITE_PATH, index_symbol, expiry_hint)
        if not inst:
            return {"status": "error", "message": f"No FUT instrument found for {index_symbol} (expiry={expiry_hint or 'nearest'})"}

        lot_size = int(inst.get("lotSize") or 1)

        # Quantity resolution (identical policy to options)
        if lots > 0:
            qty = lots * lot_size
        elif qty > 0:
            if qty % lot_size != 0:
                return {"status": "error", "message": f"Qty {qty} not multiple of lot {lot_size}"}
        else:
            qty = lot_size  # default: 1 lot

        # Segment fallback logic, same as options
        segment = inst.get("segment") or infer_segment_from_symbol(inst["tradingSymbol"])
        if not segment:
            return {"status": "error", "message": f"Could not infer segment for {inst}"}

        # Generate request ID for tracking
        import uuid
        rid = str(uuid.uuid4())[:8]
        
        LOG.info("(%s) Futures webhook: index=%s side=%s product_type=%s segment=%s", 
                 rid, index_symbol, side, product_type, segment)

        # --- PAPER TRADING SHORT-CIRCUIT ---
        if _paper_enabled():
            # Record as paper trade instead of executing live
            from paper_trading import execute_paper_trade_using_alert, fetch_ltp_from_dhan
            
            # For MARKET orders, fetch LTP; for LIMIT orders, use provided price
            exec_price = price if order_type == "LIMIT" and price > 0 else None
            if exec_price is None:
                ltp = fetch_ltp_from_dhan(str(inst["securityId"]), segment)
                if ltp is None or ltp <= 0:
                    LOG.warning("(%s) Paper trade: Could not fetch LTP (market closed / no data), skipping paper trade", rid)
                    result = {"status": "success", "message": "Paper trade skipped - LTP unavailable (market closed)", "data": {"simulated": True, "skipped": True}}
                else:
                    exec_price = ltp
            
            if exec_price and exec_price > 0:
                # Build payload for paper trading
                paper_payload = {
                    "trading_symbol": inst["tradingSymbol"],
                    "security_id": str(inst["securityId"]),
                    "segment": segment,
                    "side": side,
                    "qty": qty,
                    "price": exec_price,
                    "order_type": order_type,
                    "rid": rid
                }
                result = execute_paper_trade_using_alert(paper_payload)
                if result.get("status") == "error":
                    LOG.error("(%s) Paper trade failed: %s", rid, result.get("message"))
                else:
                    result["data"] = {"simulated": True}
                    result["message"] = result.get("message", "Paper trade recorded")
        else:
            # real live order path (unchanged)
            raw_res = place_order_via_broker(
                security_id=str(inst["securityId"]),
                segment=segment,
                side=side,
                qty=qty,
                order_type=order_type,
                price=None if order_type == "MARKET" else price,
                product_type=product_type,  # Pass original, let place_order_via_broker map it
                validity=validity,
                symbol=inst["tradingSymbol"],
                disclosed_qty=0,
                rid=rid,
            )
            result = normalize_response(raw_res, success_msg="Futures order placed via webhook", error_msg="Futures webhook order failed")

        # record in the same in-memory alerts log used by options
        from copy import deepcopy
        alert_entry = {
            "id": rid,
            "timestamp": datetime.now().isoformat(),
            "trade": deepcopy(body),
            "instrument": inst,
            "qty": qty,
            "lots": lots,
            "lot_size": lot_size,
            "response": result,
        }
        ALERTS_LOG.insert(0, alert_entry)
        if len(ALERTS_LOG) > MAX_ALERTS:
            ALERTS_LOG.pop()
        ALERTS_LOGGER.info("ALERT-FUT | %s", alert_entry)


        return result

    except Exception as e:
        LOG.exception("Webhook futures trade failed")
        return {"status": "error", "message": str(e)}


@router.post("/paper")
async def webhook_paper_trade(req: Request):
    """
    Webhook endpoint for paper trading using the new unified system.
    Supports both new format and legacy TradingView format.
    
    New format:
    {
      "trading_symbol": "RELIANCE",
      "segment": "NSE_EQ",
      "side": "BUY",
      "qty": 1,
      "price": 2850.50,
      "rid": "alert-001"
    }
    
    Legacy format (your current format):
    {
      "index": "NIFTY",
      "symbol": "EXCHANGE:SYMBOL",
      "side": "BUY",
      "order_type": "MARKET",
      "price": 18345.25,
      "product_type": "INTRADAY",
      "validity": "DAY",
      "lots": 1
    }
    """
    body = await req.json()
    LOG.info("Paper trading webhook payload: %s", body)

    # ------ Security checks (same as other webhooks) ------
    client_host = None
    try:
        client_host = req.client.host if req.client else None
    except Exception:
        client_host = None

    if WEBHOOK_IP_WHITELIST:
        if not client_host or client_host not in WEBHOOK_IP_WHITELIST:
            LOG.warning("Webhook rejected: client ip %s not in whitelist", client_host)
            return {"status": "error", "message": "IP not allowed"}

    if WEBHOOK_API_KEY:
        provided = req.headers.get("x-webhook-key") or req.headers.get("X-Webhook-Key")
        if not provided or provided != WEBHOOK_API_KEY:
            LOG.warning("Webhook rejected: missing/invalid API key from %s", client_host)
            return {"status": "error", "message": "Invalid or missing API key"}

    # Simple in-memory rate limiting
    if WEBHOOK_RATE_LIMIT and WEBHOOK_RATE_LIMIT > 0:
        now = time.time()
        ip = client_host or "unknown"
        bucket = RATE_LIMIT_STORE.setdefault(ip, [])
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= WEBHOOK_RATE_LIMIT:
            LOG.warning("Webhook rate-limited for %s (limit=%s/min)", ip, WEBHOOK_RATE_LIMIT)
            return {"status": "error", "message": "Rate limit exceeded"}
        bucket.append(now)
    # ------------------------------------------------

    try:
        # Convert legacy format to new format
        paper_payload = convert_legacy_format(body)
        
        # Validate required fields
        if "price" not in paper_payload or float(paper_payload.get("price", 0)) <= 0:
            return {"status": "error", "message": "price is required and must be > 0"}
        
        if "qty" not in paper_payload or int(paper_payload.get("qty", 0)) <= 0:
            return {"status": "error", "message": "qty is required and must be > 0"}
        
        if not paper_payload.get("trading_symbol") and not paper_payload.get("security_id"):
            return {"status": "error", "message": "trading_symbol or security_id is required"}
        
        if not paper_payload.get("segment"):
            return {"status": "error", "message": "segment is required"}

        # Generate request ID for tracking
        rid = str(uuid.uuid4())[:8]
        paper_payload["rid"] = paper_payload.get("rid", rid)
        
        LOG.info("(%s) Paper trading webhook: symbol=%s side=%s qty=%s price=%s", 
                 rid, paper_payload.get("trading_symbol"), paper_payload.get("side"), paper_payload.get("qty"), paper_payload.get("price"))

        # Execute using the new paper trading system
        from paper_trading import execute_paper_trade_using_alert
        result = execute_paper_trade_using_alert(paper_payload)
        
        if result.get("status") == "error":
            LOG.error("(%s) Paper trade failed: %s", rid, result.get("message"))
            return result

        # Record in alerts log
        from copy import deepcopy
        alert_entry = {
            "id": rid,
            "timestamp": datetime.now().isoformat(),
            "trade": deepcopy(body),  # Original payload
            "converted_payload": deepcopy(paper_payload),  # Converted payload
            "response": result,
        }
        ALERTS_LOG.insert(0, alert_entry)
        if len(ALERTS_LOG) > MAX_ALERTS:
            ALERTS_LOG.pop()
        ALERTS_LOGGER.info("ALERT-PAPER | %s", alert_entry)

        return result

    except Exception as e:
        LOG.exception("Paper trading webhook failed")
        return {"status": "error", "message": str(e)}


def convert_legacy_format(body):
    """
    Convert legacy TradingView format to new paper trading format.
    
    Legacy format:
    {
      "index": "NIFTY",
      "symbol": "EXCHANGE:SYMBOL", 
      "side": "BUY",
      "order_type": "MARKET",
      "price": 18345.25,
      "product_type": "INTRADAY",
      "validity": "DAY",
      "lots": 1
    }
    
    New format:
    {
      "trading_symbol": "NIFTY",
      "segment": "NSE_FNO",
      "side": "BUY", 
      "qty": 1,
      "price": 18345.25,
      "rid": "generated_id"
    }
    """
    # Check if this is legacy format (has 'index' field)
    if "index" in body:
        LOG.info("Converting legacy format to new paper trading format")
        
        # Extract trading symbol from index
        trading_symbol = str(body.get("index", "")).upper()
        
        # Determine segment based on trading symbol
        segment = infer_segment_from_symbol(trading_symbol)
        
        # Convert lots to qty (assume 1 lot = 1 qty for simplicity, or use lot size if available)
        lots = int(body.get("lots", 1))
        qty = lots  # For paper trading, we'll use lots as qty directly
        
        # Build new payload
        paper_payload = {
            "trading_symbol": trading_symbol,
            "segment": segment,
            "side": str(body.get("side", "BUY")).upper(),
            "qty": qty,
            "price": float(body.get("price", 0)),
            "rid": str(uuid.uuid4())[:8]
        }
        
        LOG.info("Converted legacy format: %s -> %s", body, paper_payload)
        return paper_payload
    
    # If not legacy format, return as-is (already in new format)
    return body


@router.get("/alerts")
def get_alerts():
    """Get recent webhook alerts."""
    return {"status": "success", "alerts": ALERTS_LOG}


