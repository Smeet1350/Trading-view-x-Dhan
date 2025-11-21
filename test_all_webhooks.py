import requests
import json

def test_endpoint(name, url, payload):
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print('='*60)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code >= 400:
            print(f"❌ FAILED with status {response.status_code}")
            return False
        else:
            print(f"✅ SUCCESS")
            return True
            
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

# Test 1: Paper Trading Endpoint
test_endpoint(
    "Paper Trading Endpoint",
    "http://localhost:8000/webhook/paper",
    {
        "index": "NIFTY",
        "side": "BUY",
        "price": 25500,
        "lots": 1,
        "order_type": "MARKET",
        "product_type": "INTRADAY",
        "validity": "DAY"
    }
)

# Test 2: Options Webhook (when paper trading is enabled)
test_endpoint(
    "Options Trade Endpoint",
    "http://localhost:8000/webhook/trade",
    {
        "index": "NIFTY",
        "strike": 25500,
        "option_type": "CE",
        "side": "BUY",
        "lots": 1,
        "order_type": "MARKET",
        "product_type": "INTRADAY",
        "validity": "DAY"
    }
)

# Test 3: Futures Webhook (when paper trading is enabled)
test_endpoint(
    "Futures Trade Endpoint",
    "http://localhost:8000/webhook/futures",
    {
        "index": "NIFTY",
        "side": "BUY",
        "lots": 1,
        "order_type": "MARKET",
        "price": 0,
        "product_type": "INTRADAY",
        "validity": "DAY"
    }
)

print(f"\n{'='*60}")
print("Test Complete")
print('='*60)


