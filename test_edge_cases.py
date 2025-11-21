import requests
import json

BASE_URL = "http://localhost:8000"

def test(name, endpoint, payload):
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    try:
        r = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=5)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:200]}")
        if r.status_code >= 500:
            print("❌ INTERNAL SERVER ERROR FOUND!")
            return False
        return True
    except Exception as e:
        print(f"Exception: {e}")
        return False

# Test edge cases that might cause internal server error
tests = [
    # Missing required fields
    ("Missing price", "/webhook/paper", {"index": "NIFTY", "side": "BUY", "lots": 1}),
    ("Missing side", "/webhook/paper", {"index": "NIFTY", "price": 25500, "lots": 1}),
    ("Missing symbol", "/webhook/paper", {"side": "BUY", "price": 25500, "lots": 1}),
    
    # Invalid values
    ("Zero price", "/webhook/paper", {"index": "NIFTY", "side": "BUY", "price": 0, "lots": 1}),
    ("Negative price", "/webhook/paper", {"index": "NIFTY", "side": "BUY", "price": -100, "lots": 1}),
    ("Zero qty", "/webhook/paper", {"index": "NIFTY", "side": "BUY", "price": 25500, "lots": 0}),
    
    # Invalid request body
    ("Empty JSON", "/webhook/paper", {}),
    ("Null values", "/webhook/paper", {"index": None, "side": None, "price": None}),
    
    # Valid request (should work)
    ("Valid request", "/webhook/paper", {"index": "NIFTY", "side": "BUY", "price": 25500, "lots": 1, "order_type": "MARKET", "product_type": "INTRADAY", "validity": "DAY"}),
]

print("Testing Edge Cases for Internal Server Errors")
print("="*60)

failures = []
for name, endpoint, payload in tests:
    if not test(name, endpoint, payload):
        failures.append(name)

print(f"\n{'='*60}")
print(f"Tests Complete")
print(f"Failures: {len(failures)}")
if failures:
    print("Failed tests:", failures)
else:
    print("✅ All tests passed - no internal server errors found!")
print('='*60)




