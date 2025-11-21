# test_webhook.py
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_trade(payload):
    url = f"{BASE_URL}/webhook/trade"
    print(f"\n>>> Sending to {url}")
    print("Payload:", json.dumps(payload, indent=2))
    try:
        r = requests.post(url, json=payload, timeout=30)
        print("Status:", r.status_code)
        print("Response:", json.dumps(r.json(), indent=2))
    except Exception as e:
        print("❌ Request failed:", e)

def test_futures(payload):
    url = f"{BASE_URL}/webhook/futures"
    print(f"\n>>> Sending to {url}")
    print("Payload:", json.dumps(payload, indent=2))
    try:
        r = requests.post(url, json=payload, timeout=30)
        print("Status:", r.status_code)
        response = r.json()
        print("Response:", json.dumps(response, indent=2))
        
        # Detailed analysis of the response
        if r.status_code == 200:
            if response.get("status") == "success":
                print("✅ FUTURES ORDER SUCCESSFUL")
                if "data" in response and response["data"]:
                    order_data = response["data"]
                    if "orderId" in order_data:
                        print(f"   Order ID: {order_data['orderId']}")
                    if "message" in response:
                        print(f"   Message: {response['message']}")
            else:
                print("❌ FUTURES ORDER FAILED")
                print(f"   Error: {response.get('message', 'Unknown error')}")
                if "broker" in response and response["broker"]:
                    print(f"   Broker Response: {response['broker']}")
        else:
            print(f"❌ HTTP ERROR: {r.status_code}")
            print(f"   Response: {response}")
            
    except Exception as e:
        print("❌ Request failed:", e)


if __name__ == "__main__":
    # Example 1: BANKNIFTY CE buy with strike rounding (45987 -> 46000)
    trade1 = {
        "index": "BANKNIFTY",
        "strike": 45987,  # Will be rounded to 46000
        "option_type": "CE",
        "side": "BUY",
        "lots": 1,  # New lots parameter
        "order_type": "MARKET",
        "price": 0
    }

    # Example 2: NIFTY PE sell with strike rounding (20023 -> 20000)
    trade2 = {
        "index": "NIFTY",
        "strike": 20023,  # Will be rounded to 20000
        "option_type": "PE",
        "side": "SELL",
        "lots": 2,  # 2 lots
        "order_type": "LIMIT",
        "price": 105.5
    }

    # Example 3: BANKNIFTY PE buy (no qty/lots → defaults to 1 lot)
    trade3 = {
        "index": "BANKNIFTY",
        "strike": 33000,
        "option_type": "PE",
        "side": "BUY"
    }

    # Example 4: Backward compatibility with qty parameter
    trade4 = {
        "index": "NIFTY",
        "strike": 20000,
        "option_type": "CE",
        "side": "BUY",
        "qty": 75,  # Old qty parameter still works
        "order_type": "MARKET"
    }

    # Futures test cases
    print("=" * 60)
    print("TESTING FUTURES WEBHOOK (with NORMAL/DELIVERY product mapping)")
    print("=" * 60)
    
    # Futures test 1: NIFTY futures buy (your provided JSON)
    futures1 = {
        "index": "NIFTY",
        "side": "BUY",
        "order_type": "MARKET",
        "price": 0,
        "product_type": "INTRADAY",
        "validity": "DAY",
        "lots": 1
    }
    
    # Futures test 2: BANKNIFTY futures sell with limit order
    futures2 = {
        "index": "BANKNIFTY",
        "side": "SELL",
        "order_type": "LIMIT",
        "price": 52000.0,
        "product_type": "INTRADAY",
        "validity": "DAY",
        "lots": 2
    }
    
    # Futures test 3: NIFTY futures with specific expiry hint
    futures3 = {
        "index": "NIFTY",
        "side": "BUY",
        "order_type": "MARKET",
        "price": 0,
        "product_type": "INTRADAY",
        "validity": "IOC",
        "lots": 1,
        "expiry": "2025-01-30"
    }
    
    # Futures test 4: FINNIFTY futures with qty instead of lots
    futures4 = {
        "index": "FINNIFTY",
        "side": "BUY",
        "order_type": "MARKET",
        "price": 0,
        "product_type": "INTRADAY",
        "validity": "DAY",
        "qty": 50  # Will be validated against lot size
    }
    
    # Futures test 5: NIFTY futures with DELIVERY product (should map to NORMAL for carry-forward)
    futures5 = {
        "index": "NIFTY",
        "side": "BUY",
        "order_type": "MARKET",
        "price": 0,
        "product_type": "DELIVERY",  # Should map to NORMAL for F&O
        "validity": "DAY",
        "lots": 1
    }
    
    # Futures test 6: BANKNIFTY futures with NORMAL product (explicit carry-forward)
    futures6 = {
        "index": "BANKNIFTY",
        "side": "SELL",
        "order_type": "LIMIT",
        "price": 51000.0,
        "product_type": "NORMAL",  # Explicit carry-forward
        "validity": "DAY",
        "lots": 1
    }
    
    # Futures test 7: NIFTY futures with NRML alias
    futures7 = {
        "index": "NIFTY",
        "side": "BUY",
        "order_type": "MARKET",
        "price": 0,
        "product_type": "NRML",  # Alias for NORMAL
        "validity": "DAY",
        "lots": 1
    }

    # Run options tests
    print("=" * 60)
    print("TESTING OPTIONS WEBHOOK")
    print("=" * 60)
    for t in [trade1, trade2, trade3, trade4]:
        test_trade(t)
    
    # Run futures tests
    print("\n" + "=" * 60)
    print("TESTING FUTURES WEBHOOK")
    print("=" * 60)
    for f in [futures1, futures2, futures3, futures4, futures5, futures6, futures7]:
        test_futures(f)
