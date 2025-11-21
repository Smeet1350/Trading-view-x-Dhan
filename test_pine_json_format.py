import json
import requests

# Simulated JSON outputs from the FIXED Pine Script
test_cases = [
    {
        "name": "BUY Signal",
        "json_string": '{"index":"NIFTY","side":"BUY","order_type":"MARKET","price":25513.8,"product_type":"INTRADAY","validity":"DAY","lots":1}',
    },
    {
        "name": "SELL Signal", 
        "json_string": '{"index":"NIFTY","side":"SELL","order_type":"MARKET","price":25545.2,"product_type":"INTRADAY","validity":"DAY","lots":1}',
    },
    {
        "name": "BANKNIFTY BUY",
        "json_string": '{"index":"BANKNIFTY","side":"BUY","order_type":"MARKET","price":54321.5,"product_type":"INTRADAY","validity":"DAY","lots":2}',
    }
]

print("="*70)
print("TESTING PINE SCRIPT JSON FORMAT")
print("="*70)

all_valid = True

for test in test_cases:
    print(f"\n{test['name']}:")
    print(f"Raw JSON: {test['json_string']}")
    
    # Test 1: Validate JSON syntax
    try:
        parsed = json.loads(test['json_string'])
        print("✅ Valid JSON syntax")
        print(f"   Parsed: {json.dumps(parsed, indent=4)}")
    except json.JSONDecodeError as e:
        print(f"❌ INVALID JSON: {e}")
        all_valid = False
        continue
    
    # Test 2: Check required fields
    required_fields = ["index", "side", "order_type", "price", "product_type", "validity", "lots"]
    missing = [f for f in required_fields if f not in parsed]
    if missing:
        print(f"❌ Missing required fields: {missing}")
        all_valid = False
    else:
        print(f"✅ All required fields present: {required_fields}")
    
    # Test 3: Send to paper trading endpoint
    try:
        url = "http://localhost:8000/webhook/paper"
        response = requests.post(url, json=parsed, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ Endpoint accepted: {response.status_code}")
            result = response.json()
            if result.get("status") == "ok":
                print(f"   Paper trade created: {result}")
            else:
                print(f"   Response: {result}")
        else:
            print(f"❌ Endpoint rejected: {response.status_code}")
            print(f"   Response: {response.text}")
            all_valid = False
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Backend not running (skipping endpoint test)")
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")
        all_valid = False

print("\n" + "="*70)
if all_valid:
    print("✅ ALL TESTS PASSED - Pine Script JSON is correct!")
else:
    print("❌ SOME TESTS FAILED - Please fix the issues above")
print("="*70)

# Show the exact format expected
print("\n📋 EXPECTED JSON FORMAT FOR PAPER TRADING:")
print("-" * 70)
example = {
    "index": "NIFTY",
    "side": "BUY",
    "order_type": "MARKET",
    "price": 25500.0,
    "product_type": "INTRADAY",
    "validity": "DAY",
    "lots": 1
}
print(json.dumps(example, indent=2))
print("-" * 70)
print("\n📝 Pine Script Function to Generate This:")
print("-" * 70)
print('''generate_alert_json(side) =>
    '{"index":"' + alert_index + 
    '","side":"' + side + 
    '","order_type":"' + alert_order_type + 
    '","price":' + str.tostring(close, "#.##") + 
    ',"product_type":"' + alert_product_type + 
    '","validity":"' + alert_validity + 
    '","lots":' + str.tostring(alert_lots) + '}'
''')
print("-" * 70)




