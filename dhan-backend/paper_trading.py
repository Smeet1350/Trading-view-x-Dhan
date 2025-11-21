# paper_trading.py
# New FastAPI router to provide paper-trading features:
# - /paper/enabled (GET/POST) to toggle
# - /paper/execute (POST) to execute a paper trade (entry or exit)
# - /paper/trades (GET) to list trades
# - /paper/clear (POST) to clear all paper trades
# - /paper/ltp (GET) debug helper to fetch LTP from Dhan for a security

from fastapi import APIRouter, Query, HTTPException, Request
import os
import sqlite3
import time
import requests
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

# Load environment variables from .env file
from dotenv import load_dotenv
import logging

# Setup logging
LOG = logging.getLogger("paper_trading")

# Load .env file
load_dotenv()

# Paths & config (loaded from .env file)
SQLITE_PATH = os.getenv("INSTRUMENTS_DB", "instruments.db")
PAPER_DB = os.getenv("PAPER_TRADES_DB", "paper_trades.db")
DHAN_BASE = os.getenv("DHAN_BASE_URL", "https://api.dhan.co/v2")
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

# Config (can be overridden by env vars)
PAPER_CHARGE = int(os.getenv("PAPER_CHARGE", "600"))  # charge per round-trip (default)
DEFAULT_BUY_SLIPPAGE = float(os.getenv("PAPER_BUY_SLIPPAGE", "5"))   # points
DEFAULT_SELL_SLIPPAGE = float(os.getenv("PAPER_SELL_SLIPPAGE", "7"))  # points

# Log credential status on module load
if DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN:
    LOG.info(f"Paper trading: Dhan credentials loaded from .env (Client ID: {DHAN_CLIENT_ID[:6]}...)")
else:
    LOG.warning("Paper trading: Dhan credentials NOT found in .env file. Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN")

router = APIRouter(prefix="/paper", tags=["paper"])

# simple in-memory enabled flag; persisted via file for restart-preservation
_enabled_file = ".paper_enabled"


def _read_enabled() -> bool:
    try:
        if os.path.exists(_enabled_file):
            v = open(_enabled_file).read().strip().lower()
            return v in ("1", "true", "yes")
    except Exception:
        pass
    return False


def _write_enabled(val: bool):
    try:
        open(_enabled_file, "w").write("1" if val else "0")
    except Exception:
        pass


# === PAPER-TRADE: use provided price + slippage, FIFO pairing, PnL on round-trip ===

def _conn():
    return sqlite3.connect(PAPER_DB, timeout=30)

def _ensure_schema():
    conn = _conn(); cur = conn.cursor()
    # original table (if not exists)
    cur.execute("""
      CREATE TABLE IF NOT EXISTS paper_trades (
         id TEXT PRIMARY KEY,
         ts REAL,
         ts_iso TEXT,
         rid TEXT,
         security_id TEXT,
         trading_symbol TEXT,
         segment TEXT,
         side TEXT,
         qty INTEGER,
         order_type TEXT,
         exec_price REAL,
         raw_payload TEXT,
         status TEXT
      )
    """)
    conn.commit()
    # add columns for entry/exit/pnl if missing
    # safe ALTER TABLE (catch exceptions if column exists)
    extra_cols = {
        "entry_price": "REAL",
        "entry_ts": "TEXT",
        "exit_price": "REAL",
        "exit_ts": "TEXT",
        "gross_pnl": "REAL",
        "net_pnl": "REAL",
        "charge": "REAL",
        "matched_qty": "INTEGER",
        "price_source": "TEXT"
    }
    for col, ctype in extra_cols.items():
        try:
            cur.execute(f"ALTER TABLE paper_trades ADD COLUMN {col} {ctype}")
            conn.commit()
        except Exception:
            # column probably exists; ignore
            pass
    conn.close()

# initialize schema on import
_try_schema = _ensure_schema()

def _save_trade_row(row: dict):
    """Insert or replace trade row (row is a dict matching columns)."""
    _ensure_schema()
    conn = _conn(); cur = conn.cursor()
    # ensure id
    tid = row.get("id") or str(uuid.uuid4())
    row["id"] = tid
    cols = ",".join(row.keys())
    placeholders = ",".join(["?"] * len(row))
    vals = list(row.values())
    # use REPLACE INTO to simplify updates (if pk exists it will replace)
    cur.execute(f"REPLACE INTO paper_trades ({cols}) VALUES ({placeholders})", vals)
    conn.commit()
    conn.close()
    return tid

def _fetch_open_entries(symbol: str, opposite_side: str):
    """Fetch open entries (status != 'CLOSED') for given symbol and opposite_side (e.g., 'BUY' entries when we are SELLing). FIFO ORDER BY ts."""
    _ensure_schema()
    conn = _conn(); cur = conn.cursor()
    cur.execute("""
       SELECT id, ts_iso, rid, security_id, trading_symbol, segment, side, qty, entry_price, matched_qty
       FROM paper_trades
       WHERE trading_symbol = ? AND side = ? AND (status IS NULL OR status != 'CLOSED')
       ORDER BY ts ASC
    """, (symbol, opposite_side))
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "ts_iso": r[1],
            "rid": r[2],
            "security_id": r[3],
            "trading_symbol": r[4],
            "segment": r[5],
            "side": r[6],
            "qty": int(r[7] or 0),
            "entry_price": float(r[8] or 0.0),
            "matched_qty": int(r[9] or 0)
        })
    return result

def _update_trade_exit(trade_id, exit_price, exit_ts, matched_qty, gross_pnl, net_pnl, charge):
    conn = _conn(); cur = conn.cursor()
    cur.execute("""
       UPDATE paper_trades SET exit_price = ?, exit_ts = ?, matched_qty = ?, gross_pnl = ?, net_pnl = ?, charge = ?, status = 'CLOSED' WHERE id = ?
    """, (float(exit_price), exit_ts, int(matched_qty), float(gross_pnl), float(net_pnl), float(charge), trade_id))
    conn.commit()
    conn.close()

def execute_paper_trade_using_alert(payload: dict):
    """
    New unified handler to be used by webhook / manual calls.
    Payload must include:
      - trading_symbol (recommended) OR security_id
      - segment
      - side: 'BUY' or 'SELL'
      - qty: integer
      - price: the price you send with alert (required)
      - optional: buy_slippage, sell_slippage, charge (round-trip)
      - rid: optional request id
      - action: 'entry' or 'exit' (optional; inferred from side)
    Behavior:
      - For entry: record a row with entry_price = price +/- buy_slippage (BUY -> +slippage)
      - For exit: compute executed_price similarly, then FIFO-match with open opposite-side entries to compute gross/net PnL for matched quantities. Charge applied once per matched pair (charge in payload or default)
    Returns: dict with recorded trade(s) and computed PnL details
    """
    _ensure_schema()
    # validate
    side = (payload.get("side") or "BUY").upper()
    qty = int(payload.get("qty", 0) or 0)
    if qty <= 0:
        return {"status": "error", "message": "qty must be > 0"}
    if "price" not in payload and payload.get("order_type","").upper() != "LIMIT":
        return {"status": "error", "message": "price is required in payload for paper execution"}
    provided_price = float(payload.get("price", 0.0))
    if provided_price <= 0:
        return {"status": "error", "message": "price must be > 0 in payload"}
    trading_symbol = payload.get("trading_symbol") or payload.get("symbol") or payload.get("security_id")
    segment = payload.get("segment") or payload.get("seg") or ""
    rid = payload.get("rid") or str(uuid.uuid4())[:12]
    buy_sl = float(payload.get("buy_slippage", os.getenv("PAPER_BUY_SLIPPAGE", DEFAULT_BUY_SLIPPAGE)))
    sell_sl = float(payload.get("sell_slippage", os.getenv("PAPER_SELL_SLIPPAGE", DEFAULT_SELL_SLIPPAGE)))
    charge_per_pair = float(payload.get("charge", os.getenv("PAPER_CHARGE", PAPER_CHARGE)))

    action = (payload.get("action") or "").lower()
    
    # Smart action detection: Check if there are open opposite positions
    if not action:
        # Check for open positions in opposite direction
        opposite_side = "SELL" if side == "BUY" else "BUY"
        open_opposite = _fetch_open_entries(trading_symbol, opposite_side)
        
        if open_opposite:
            # There are open opposite positions, so this is an exit/close trade
            action = "exit"
        else:
            # No open opposite positions, so this is an entry trade
            action = "entry"

    ts = time.time(); ts_iso = datetime.utcnow().isoformat() + "Z"
    results = {"status": "ok", "records": []}

    if action == "entry":
        # compute executed price for entry: BUY pays worse price -> add slippage
        exec_price = provided_price + buy_sl if side == "BUY" else provided_price - sell_sl
        # record entry row
        row = {
            "id": str(uuid.uuid4()),
            "ts": ts,
            "ts_iso": ts_iso,
            "rid": rid,
            "security_id": str(payload.get("security_id","") or ""),
            "trading_symbol": trading_symbol,
            "segment": segment,
            "side": side,
            "qty": int(qty),
            "order_type": payload.get("order_type","MARKET"),
            "exec_price": exec_price,
            "raw_payload": json.dumps(payload),
            "status": "OPEN",
            "entry_price": exec_price,
            "entry_ts": ts_iso,
            "price_source": payload.get("price_source","alert")
        }
        _save_trade_row(row)
        results["records"].append({"id": row["id"], "entry_price": exec_price, "qty": qty, "status": "OPEN"})
        return results

    # action == 'exit' -> need to match against opposite-side open entries (FIFO)
    # compute executed exit price for this alert
    exit_exec_price = provided_price - sell_sl if side == "SELL" else provided_price + buy_sl
    # Opposite side
    opp_side = "BUY" if side == "SELL" else "SELL"
    remaining_to_match = qty
    open_entries = _fetch_open_entries(trading_symbol, opp_side)
    if not open_entries:
        # no open entries; record exit as orphan (we'll still store it)
        row = {
            "id": str(uuid.uuid4()),
            "ts": ts,
            "ts_iso": ts_iso,
            "rid": rid,
            "security_id": str(payload.get("security_id","") or ""),
            "trading_symbol": trading_symbol,
            "segment": segment,
            "side": side,
            "qty": int(qty),
            "order_type": payload.get("order_type","MARKET"),
            "exec_price": exit_exec_price,
            "raw_payload": json.dumps(payload),
            "status": "CLOSED",
            "exit_price": exit_exec_price,
            "exit_ts": ts_iso,
            "gross_pnl": 0.0,
            "net_pnl": -charge_per_pair,
            "charge": charge_per_pair,
            "matched_qty": 0,
            "price_source": payload.get("price_source","alert")
        }
        _save_trade_row(row)
        results["records"].append({"id": row["id"], "exit_price": exit_exec_price, "qty": qty, "status": "ORPHAN_EXIT", "message": "no open entries to match"})
        return results

    # iterate FIFO over open entries and match
    total_matched = 0
    total_gross = 0.0
    total_net = 0.0
    matches = []
    for e in open_entries:
        if remaining_to_match <= 0:
            break
        open_qty = e["qty"] - (e.get("matched_qty") or 0)
        if open_qty <= 0:
            continue
        take = min(open_qty, remaining_to_match)
        entry_price = float(e["entry_price"] or 0.0)
        # For PnL calculation: 
        # Long position (BUY entry, SELL exit): profit = exit_price - entry_price
        # Short position (SELL entry, BUY exit): profit = entry_price - exit_price
        if opp_side == "BUY" and side == "SELL":
            # Closing a long position: BUY entry -> SELL exit
            gross = (exit_exec_price - entry_price) * take
        elif opp_side == "SELL" and side == "BUY":
            # Closing a short position: SELL entry -> BUY exit
            gross = (entry_price - exit_exec_price) * take
        else:
            # Same side? This shouldn't happen with proper logic, but set to 0
            gross = 0.0
        # apply charge once per completed matched portion. We'll split full charge proportionally if multiple matches.
        # compute proportional charge
        proportional_charge = (take / qty) * charge_per_pair if qty > 0 else charge_per_pair
        net = gross - proportional_charge

        # update matched_qty on entry record and possibly close entry if fully matched
        # fetch entry full row, update matched_qty and status
        conn = _conn(); cur = conn.cursor()
        # compute new matched_qty
        cur.execute("SELECT matched_qty, qty FROM paper_trades WHERE id = ?", (e["id"],))
        rr = cur.fetchone()
        prev_matched = int(rr[0] or 0) if rr else 0
        total_entry_qty = int(rr[1] or e["qty"]) if rr else e["qty"]
        new_matched = prev_matched + take
        new_status = "CLOSED" if new_matched >= total_entry_qty else "OPEN"
        cur.execute("UPDATE paper_trades SET matched_qty = ?, status = ? WHERE id = ?", (new_matched, new_status, e["id"]))
        conn.commit(); conn.close()

        # record exit row for this matched piece (we create a dedicated closed record)
        match_row = {
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            "ts_iso": datetime.utcnow().isoformat() + "Z",
            "rid": rid,
            "security_id": e.get("security_id"),
            "trading_symbol": trading_symbol,
            "segment": e.get("segment"),
            "side": side,
            "qty": int(take),
            "order_type": payload.get("order_type","MARKET"),
            "exec_price": exit_exec_price,
            "raw_payload": json.dumps(payload),
            "status": "CLOSED",
            "entry_price": entry_price,
            "entry_ts": e.get("ts_iso"),
            "exit_price": exit_exec_price,
            "exit_ts": datetime.utcnow().isoformat() + "Z",
            "gross_pnl": round(gross, 2),
            "charge": round(proportional_charge, 2),
            "net_pnl": round(net, 2),
            "matched_qty": int(take),
            "price_source": payload.get("price_source","alert")
        }
        _save_trade_row(match_row)

        total_matched += take
        total_gross += gross
        total_net += net
        matches.append({"entry_id": e["id"], "exit_row": match_row, "matched_qty": take, "gross": gross, "net": net})

        remaining_to_match -= take

    results["records"].append({
        "matched_total": total_matched,
        "gross_total": round(total_gross, 2),
        "net_total": round(total_net, 2),
        "matches": matches
    })
    return results


# Dhan LTP fetcher (robust with detailed logging and multiple payload strategies)
def fetch_ltp_from_dhan(security_id: str, segment: str, log_details: bool = False) -> Optional[float]:
    """Fetch LTP from Dhan /marketfeed/ltp endpoint.
    Returns float or None if not available/zero.
    This version tries a few payload shapes and segment variants to increase success rate.
    """
    if not DHAN_ACCESS_TOKEN or not DHAN_CLIENT_ID:
        LOG.error("LTP fetch failed: DHAN_ACCESS_TOKEN or DHAN_CLIENT_ID not set (paper_trading)")
        return None

    url = DHAN_BASE.rstrip("/") + "/marketfeed/ltp"
    headers = {
        "access-token": DHAN_ACCESS_TOKEN,
        "client-id": DHAN_CLIENT_ID,
        "Content-Type": "application/json",
    }

    # Build candidate segment keys to try (the API sometimes expects short exchange codes)
    # include given segment, mapped exchange short name, and a few common alternatives
    candidate_segments = [segment]
    # common mappings (segment values used across your project)
    SEG_TO_EXCHANGE_MAP = {
        "NSE_EQ": "NSE",
        "BSE_EQ": "BSE",
        "NSE_FNO": "NSE_FNO",
        "MCX": "MCX"
    }
    if segment in SEG_TO_EXCHANGE_MAP:
        candidate_segments.append(SEG_TO_EXCHANGE_MAP[segment])
    # also try uppercase short names
    candidate_segments += [s.upper() for s in candidate_segments if s]
    # ensure unique
    candidate_segments = list(dict.fromkeys([s for s in candidate_segments if s]))

    # candidate payload formats to try
    payloads = []
    # shape 1: { segment: [securityId] }
    for segk in candidate_segments:
        try:
            payloads.append({segk: [int(security_id)]})
        except Exception:
            payloads.append({segk: [str(security_id)]})
    # shape 2: { "data": { segment: [securityId] } } — sometimes APIs wrap under 'data'
    for p in payloads[:]:
        payloads.append({"data": p})

    # Keep last-resort single-instrument payloads too
    payloads.append({"security_id": str(security_id)})
    payloads.append({"id": str(security_id)})

    # Try each payload until we get a usable LTP
    tried = []
    for payload in payloads:
        tried.append(payload)
        try:
            LOG.info(f"Fetching LTP for security_id={security_id}, segment={segment} using payload keys: {list(payload.keys())}")
            LOG.debug(f"API URL: {url}")
            LOG.debug(f"Payload: {payload}")
            r = requests.post(url, json=payload, headers=headers, timeout=8)
            LOG.info(f"Dhan API response status: {r.status_code}")
            if r.status_code != 200:
                LOG.warning(f"Dhan API returned status {r.status_code}: {r.text[:200]}")
                continue
            j = r.json()
            LOG.debug(f"Dhan API response: {j}")

            # Now parse various possible response structures for numeric last-price / ltp
            def _scan_for_ltp(obj):
                # If a dict that contains ltp-like keys at this level, return it
                if isinstance(obj, dict):
                    for k in ("last_price", "lastPrice", "LastPrice", "ltp", "LTP", "lastTradedPrice", "last_traded_price"):
                        if k in obj and obj[k] not in (None, "", 0):
                            try:
                                v = float(obj[k])
                                if v > 0:
                                    return v
                            except Exception:
                                pass
                    # otherwise, recurse
                    for v in obj.values():
                        res = _scan_for_ltp(v)
                        if res:
                            return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = _scan_for_ltp(item)
                        if res:
                            return res
                elif isinstance(obj, (int, float)):
                    if obj > 0:
                        return float(obj)
                return None

            found = _scan_for_ltp(j)
            if found:
                LOG.info(f"LTP found: {found} (payload tried count={len(tried)})")
                return float(found)

            # else continue trying payloads
            LOG.debug("No LTP found in response for this payload; trying next payload if any.")
        except requests.exceptions.RequestException as e:
            LOG.error(f"Network error fetching LTP (payload tried): {e}")
            continue
        except Exception as e:
            LOG.exception("Unexpected error parsing Dhan LTP response")
            continue

    # All payloads tried, nothing found
    LOG.warning(f"Could not parse LTP from any response for {security_id}. Tried payloads: {tried}")
    if log_details:
        LOG.warning("Full attempted payloads and last response logged above.")
    return None


@router.get("/enabled")
def api_paper_enabled():
    return {
        "enabled": _read_enabled(), 
        "charge_per_round_trip": PAPER_CHARGE,
        "buy_slippage": DEFAULT_BUY_SLIPPAGE,
        "sell_slippage": DEFAULT_SELL_SLIPPAGE
    }


@router.post("/enabled")
def api_set_enabled(value: bool = Query(...)):
    _write_enabled(bool(value))
    return {"enabled": _read_enabled()}


@router.post("/execute")
def api_execute(request: Request):
    """Execute a paper trade using the new unified system.
    Accepts JSON payload with:
    - trading_symbol (recommended) OR security_id
    - segment
    - side: 'BUY' or 'SELL'
    - qty: integer
    - price: the price you send with alert (required)
    - optional: buy_slippage, sell_slippage, charge (round-trip)
    - rid: optional request id
    - action: 'entry' or 'exit' (optional; inferred from side)
    """
    try:
        payload = request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")
    
    # Validate required fields
    if "price" not in payload:
        raise HTTPException(status_code=400, detail="price is required in payload")
    
    if "qty" not in payload or int(payload.get("qty", 0)) <= 0:
        raise HTTPException(status_code=400, detail="qty must be > 0")
    
    if not payload.get("trading_symbol") and not payload.get("security_id"):
        raise HTTPException(status_code=400, detail="trading_symbol or security_id is required")
    
    if not payload.get("segment"):
        raise HTTPException(status_code=400, detail="segment is required")
    
    # Execute the trade using the new system
    result = execute_paper_trade_using_alert(payload)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))
    
    return result




@router.get("/trades")
def api_trades(limit: int = Query(200)):
    _ensure_schema()
    conn = sqlite3.connect(PAPER_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM paper_trades ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    # add cumulative pnl sums
    cum_gross = 0.0
    cum_net = 0.0
    for r in reversed(out):
        if r.get("gross_pnl") is not None:
            cum_gross += float(r.get("gross_pnl") or 0)
        if r.get("net_pnl") is not None:
            cum_net += float(r.get("net_pnl") or 0)
        r["cumulative_gross"] = cum_gross
        r["cumulative_net"] = cum_net
    return {"trades": out, "cumulative_net": cum_net, "cumulative_gross": cum_gross}


@router.get("/trades/open")
def api_open_trades():
    """Get only open trades (status != 'CLOSED')"""
    _ensure_schema()
    conn = sqlite3.connect(PAPER_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM paper_trades WHERE status IS NULL OR status != 'CLOSED' ORDER BY ts ASC").fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    return {"open_trades": out, "count": len(out)}


@router.get("/trades/closed")
def api_closed_trades(limit: int = Query(200)):
    """Get only closed trades with PnL"""
    _ensure_schema()
    conn = sqlite3.connect(PAPER_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM paper_trades WHERE status = 'CLOSED' ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    out = [dict(r) for r in rows]
    conn.close()
    # add cumulative pnl sums
    cum_gross = 0.0
    cum_net = 0.0
    for r in reversed(out):
        if r.get("gross_pnl") is not None:
            cum_gross += float(r.get("gross_pnl") or 0)
        if r.get("net_pnl") is not None:
            cum_net += float(r.get("net_pnl") or 0)
        r["cumulative_gross"] = cum_gross
        r["cumulative_net"] = cum_net
    return {"closed_trades": out, "cumulative_net": cum_net, "cumulative_gross": cum_gross, "count": len(out)}


@router.post("/clear")
def api_clear():
    _ensure_schema()
    conn = sqlite3.connect(PAPER_DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM paper_trades")
    conn.commit()
    conn.close()
    return {"status": "cleared"}


@router.get("/ltp")
def api_debug_ltp(security_id: str = Query(...), segment: str = Query(...)):
    """Debug endpoint to test LTP fetching with detailed logging.
    Check backend logs for detailed information about the API call."""
    # Set log level to DEBUG temporarily for this call
    old_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    
    val = fetch_ltp_from_dhan(security_id, segment, log_details=True)
    
    # Restore log level
    LOG.setLevel(old_level)
    
    if val is None:
        return {
            "ok": False,
            "ltp": None,
            "message": "Could not fetch LTP. Check backend logs for details.",
            "credentials_set": bool(DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN),
            "api_url": DHAN_BASE + "/marketfeed/ltp",
            "security_id": security_id,
            "segment": segment
        }
    return {
        "ok": True,
        "ltp": val,
        "security_id": security_id,
        "segment": segment
    }

# End of paper_trading.py
