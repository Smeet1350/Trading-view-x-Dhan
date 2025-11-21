#!/usr/bin/env python
"""Test paper trading API endpoints"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

print("=" * 70)
print("PAPER TRADING API TEST")
print("=" * 70)
print(f"Testing API at: {BASE_URL}")
print("=" * 70)

def test_endpoint(method, path, params=None, data=None, description=""):
    """Helper to test an endpoint"""
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=5)
        elif method == "POST":
            response = requests.post(url, params=params, json=data, timeout=5)
        else:
            print(f"❌ Unknown method: {method}")
            return None
        
        print(f"\n{description}")
        print(f"   {method} {path}")
        if params:
            print(f"   Params: {params}")
        print(f"   Status: {response.status_code}")
        result = response.json()
        print(f"   Response: {json.dumps(result, indent=6)}")
        return result
    except requests.exceptions.ConnectionError:
        print(f"\n❌ {description}")
        print(f"   ERROR: Cannot connect to {BASE_URL}")
        print(f"   Make sure the backend is running: cd dhan-backend && uvicorn main:app")
        return None
    except Exception as e:
        print(f"\n❌ {description}")
        print(f"   ERROR: {e}")
        return None

# Wait a moment for server to be ready
print("\nWaiting for server to start...")
time.sleep(2)

# Test 1: Check backend status
test_endpoint("GET", "/status", description="1️⃣  Testing backend status")

# Test 2: Check paper trading status
result = test_endpoint("GET", "/paper/status", description="2️⃣  Checking paper trading status")

# Test 3: Enable paper trading
result = test_endpoint("POST", "/paper/toggle", 
                      params={"enabled": True, "commission": 650},
                      description="3️⃣  Enabling paper trading with ₹650 commission")

# Test 4: Verify it's enabled
result = test_endpoint("GET", "/paper/status", description="4️⃣  Verifying paper trading is enabled")

if result and result.get("enabled"):
    print("\n   ✅ Paper trading successfully enabled!")
else:
    print("\n   ⚠️  Paper trading might not be enabled")

# Test 5: Simulate a webhook - Options trade
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
                      description="5️⃣  Sending OPTIONS webhook (should be simulated)")

if result and result.get("status") == "success":
    print(f"\n   ✅ Webhook processed successfully!")
    if result.get("data", {}).get("simulated"):
        print(f"   🧪 Trade was SIMULATED (paper mode)")
    else:
        print(f"   ⚠️  Trade might have been LIVE (check broker!)")

# Test 6: Simulate a futures webhook
futures_payload = {
    "index": "BANKNIFTY",
    "side": "SELL",
    "order_type": "LIMIT",
    "price": 52500,
    "product_type": "NORMAL",
    "validity": "DAY",
    "lots": 1
}

result = test_endpoint("POST", "/webhook/futures",
                      data=futures_payload,
                      description="6️⃣  Sending FUTURES webhook (should be simulated)")

# Test 7: Get paper trades
result = test_endpoint("GET", "/paper/trades",
                      params={"limit": 10},
                      description="7️⃣  Retrieving paper trades")

if result and result.get("trades"):
    trades = result.get("trades", [])
    summary = result.get("summary", {})
    print(f"\n   ✅ Found {len(trades)} paper trade(s)")
    print(f"   📊 Summary:")
    print(f"      Total trades: {summary.get('count', 0)}")
    print(f"      Gross P&L: ₹{summary.get('cumulative_pnl', 0):.2f}")
    print(f"      Net P&L: ₹{summary.get('cumulative_pnl_after_commission', 0):.2f}")
    
    if trades:
        print(f"\n   Latest trade:")
        t = trades[0]
        print(f"      Symbol: {t.get('symbol')}")
        print(f"      Side: {t.get('side')}")
        print(f"      Qty: {t.get('qty')}")
        print(f"      Price: ₹{t.get('executed_price', 0):.2f}")
        print(f"      Commission: ₹{t.get('commission', 0)}")

# Test 8: Disable paper trading
result = test_endpoint("POST", "/paper/toggle",
                      params={"enabled": False},
                      description="8️⃣  Disabling paper trading (back to LIVE mode)")

# Test 9: Verify it's disabled
result = test_endpoint("GET", "/paper/status", description="9️⃣  Verifying paper trading is disabled")

if result and not result.get("enabled"):
    print("\n   ✅ Paper trading successfully disabled - NOW IN LIVE MODE")
    print("   ⚠️  Future webhooks will place REAL orders!")
else:
    print("\n   ⚠️  Paper trading might still be enabled")

print("\n" + "=" * 70)
print("✅ API TESTING COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("  1. Open frontend: cd dhan-frontend && npm run dev")
print("  2. Visit http://localhost:5173")
print("  3. Toggle paper trading using the UI button")
print("  4. Send webhooks from TradingView")
print("=" * 70)


