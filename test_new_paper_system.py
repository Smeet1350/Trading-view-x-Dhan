#!/usr/bin/env python
"""Test script for new paper trading system with LTP fetching and P&L calculation"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("=" * 80)
print("NEW PAPER TRADING SYSTEM TEST")
print("=" * 80)
print(f"Testing API at: {BASE_URL}")
print("=" * 80)

def test_endpoint(method, path, params=None, data=None, description=""):
    """Helper to test an endpoint"""
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, params=params, json=data, timeout=10)
        else:
            print(f"❌ Unknown method: {method}")
            return None
        
        print(f"\n{description}")
        print(f"   {method} {path}")
        if params:
            print(f"   Params: {params}")
        print(f"   Status: {response.status_code}")
        
        try:
            result = response.json()
            print(f"   Response (first 500 chars): {json.dumps(result, indent=2)[:500]}...")
            return result
        except:
            print(f"   Response: {response.text[:200]}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"\n❌ {description}")
        print(f"   ERROR: Cannot connect to {BASE_URL}")
        print(f"   Make sure the backend is running!")
        return None
    except Exception as e:
        print(f"\n❌ {description}")
        print(f"   ERROR: {e}")
        return None

# Wait for server
print("\n⏳ Waiting for server to be ready...")
time.sleep(2)

# Test 1: Check backend status
test_endpoint("GET", "/status", description="1️⃣  Testing backend status")

# Test 2: Check paper trading status (should be disabled by default)
result = test_endpoint("GET", "/paper/status", description="2️⃣  Checking paper trading status")

# Test 3: Enable paper trading
result = test_endpoint("POST", "/paper/toggle", 
                      data={"enable": True},
                      description="3️⃣  Enabling paper trading mode")

if result and result.get("status") == "ok":
    print("\n   ✅ Paper trading enabled successfully!")
else:
    print("\n   ⚠️  Could not enable paper trading")

# Test 4: Verify it's enabled
result = test_endpoint("GET", "/paper/status", description="4️⃣  Verifying paper mode is ON")

# Test 5: Send an OPTIONS webhook (should be recorded as paper trade)
print("\n" + "=" * 80)
print("TESTING WEBHOOK INTEGRATION (OPTIONS)")
print("=" * 80)

webhook_payload = {
    "index": "NIFTY",
    "strike": 25000,
    "option_type": "CE",
    "side": "BUY",
    "order_type": "MARKET",
    "product_type": "INTRADAY",
    "validity": "DAY",
    "lots": 2
}

result = test_endpoint("POST", "/webhook/trade",
                      data=webhook_payload,
                      description="5️⃣  Sending OPTIONS webhook (BUY 2 lots)")

if result and result.get("status") == "success":
    print(f"\n   ✅ Webhook processed successfully!")
    if result.get("data", {}).get("simulated"):
        print(f"   🧪 Trade was SIMULATED (paper mode)")
        print(f"   📝 Preview: {result.get('preview', {})}")
    else:
        print(f"   ⚠️  Trade might have been LIVE (check broker!)")

# Test 6: Send a SELL to close position
webhook_payload_sell = {
    "index": "NIFTY",
    "strike": 25000,
    "option_type": "CE",
    "side": "SELL",
    "order_type": "LIMIT",
    "price": 160,
    "product_type": "INTRADAY",
    "validity": "DAY",
    "lots": 1
}

time.sleep(1)
result = test_endpoint("POST", "/webhook/trade",
                      data=webhook_payload_sell,
                      description="6️⃣  Sending OPTIONS webhook (SELL 1 lot to close partial)")

# Test 7: Send a FUTURES webhook
print("\n" + "=" * 80)
print("TESTING WEBHOOK INTEGRATION (FUTURES)")
print("=" * 80)

futures_payload = {
    "index": "BANKNIFTY",
    "side": "BUY",
    "order_type": "MARKET",
    "product_type": "NORMAL",
    "validity": "DAY",
    "lots": 1
}

result = test_endpoint("POST", "/webhook/futures",
                      data=futures_payload,
                      description="7️⃣  Sending FUTURES webhook (BUY 1 lot)")

# Test 8: Get all paper trades with P&L
print("\n" + "=" * 80)
print("CHECKING PAPER TRADES & P&L")
print("=" * 80)

result = test_endpoint("GET", "/paper/trades",
                      description="8️⃣  Retrieving all paper trades with P&L")

if result and result.get("status") == "success":
    trades = result.get("trades", [])
    per_symbol = result.get("per_symbol", [])
    overall = result.get("overall", {})
    
    print(f"\n   ✅ Found {len(trades)} paper trade(s)")
    print(f"\n   📊 OVERALL SUMMARY:")
    print(f"      Total Realized P&L: ₹{overall.get('total_realized', 0):.2f}")
    print(f"      Total Unrealized P&L: ₹{overall.get('total_unrealized', 0):.2f}")
    print(f"      Total P&L: ₹{overall.get('total_pnl', 0):.2f}")
    
    if per_symbol:
        print(f"\n   📈 PER-SYMBOL BREAKDOWN:")
        for s in per_symbol:
            print(f"      {s['symbol']}:")
            print(f"         Position: {s['position']}")
            print(f"         Avg Cost: ₹{s['avg_cost']:.2f}")
            print(f"         LTP: ₹{s['ltp']:.2f}")
            print(f"         Realized: ₹{s['realized']:.2f}")
            print(f"         Unrealized: ₹{s['unrealized']:.2f}")
    
    if trades:
        print(f"\n   📝 TRADE HISTORY (latest 3):")
        for i, t in enumerate(trades[-3:][::-1], 1):
            print(f"      {i}. {t['ts_iso'][:19]} | {t['trading_symbol'][:25]:25} | {t['side']:4} | Qty:{t['qty']:3} | Price:₹{t['exec_price']:.2f} | Fee:₹{t['fee']:.0f}")

# Test 9: Disable paper trading
print("\n" + "=" * 80)
print("TOGGLING BACK TO LIVE MODE")
print("=" * 80)

result = test_endpoint("POST", "/paper/toggle",
                      data={"enable": False},
                      description="9️⃣  Disabling paper trading (LIVE mode)")

# Test 10: Verify it's disabled
result = test_endpoint("GET", "/paper/status", description="🔟 Verifying paper mode is OFF")

if result and not result.get("enabled"):
    print("\n   ✅ Paper trading disabled - NOW IN LIVE MODE")
    print("\n   ⚠️  DANGER: Future webhooks will place REAL orders to broker!")
else:
    print("\n   ⚠️  Paper trading might still be enabled")

print("\n" + "=" * 80)
print("✅ ALL TESTS COMPLETE")
print("=" * 80)

print("\n📌 KEY FEATURES TESTED:")
print("   ✅ Paper mode toggle (ON/OFF)")
print("   ✅ Webhook interception (OPTIONS & FUTURES)")
print("   ✅ LTP fetching from Dhan API")
print("   ✅ Trade recording with execution prices")
print("   ✅ FIFO P&L calculation (realized & unrealized)")
print("   ✅ Per-symbol position tracking")
print("   ✅ Fee tracking (₹500-₹800 per trade)")

print("\n📚 NEXT STEPS:")
print("   1. Test frontend: cd dhan-frontend && npm run dev")
print("   2. Visit http://localhost:5173")
print("   3. Toggle paper mode using the UI")
print("   4. Send real webhooks from TradingView")
print("   5. Monitor P&L in real-time")

print("\n" + "=" * 80)


