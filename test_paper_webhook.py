import requests
import json

# Test the paper trading webhook
try:
    url = "http://localhost:8000/webhook/paper"
    payload = {
        "index": "NIFTY",
        "side": "BUY",
        "price": 25500,
        "lots": 1,
        "order_type": "MARKET",
        "product_type": "INTRADAY",
        "validity": "DAY"
    }
    
    print(f"Testing: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, timeout=10)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    if response.status_code != 200:
        print(f"\n❌ ERROR: Expected 200, got {response.status_code}")
    else:
        print("\n✅ SUCCESS")
        
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: Server might not be running on localhost:8000")
    print(f"Details: {e}")
except Exception as e:
    print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()


