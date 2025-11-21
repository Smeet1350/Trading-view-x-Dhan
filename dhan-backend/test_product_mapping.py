#!/usr/bin/env python3
"""
Quick test script to verify product mapping implementation.
Run this after deploying the changes to verify everything works.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def test_debug_endpoint():
    """Test the product mapping debug endpoint"""
    print_header("TEST 1: Product Mapping Debug Endpoint")
    
    try:
        r = requests.get(f"{BASE_URL}/debug/product-mapping", timeout=10)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print("\nProduct Mapping Test Results:")
            print("-" * 70)
            for case in data["test_cases"]:
                status_icon = "✅" if case["status"] == "OK" else "❌"
                print(f"{status_icon} {case['input_product']:12} + {case['segment']:10} → {case['mapped_product']}")
                if case["error"]:
                    print(f"   Error: {case['error']}")
            print("-" * 70)
        else:
            print(f"❌ Failed: {r.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_futures_webhook(product_type, description):
    """Test futures webhook with specific product type"""
    print_header(f"TEST: Futures Webhook - {description}")
    
    payload = {
        "index": "NIFTY",
        "side": "BUY",
        "order_type": "MARKET",
        "price": 0,
        "product_type": product_type,
        "validity": "DAY",
        "lots": 1,
        "qty": 0,
        "expiry": ""
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nSending request...")
    
    try:
        r = requests.post(f"{BASE_URL}/webhook/futures", json=payload, timeout=30)
        print(f"Status: {r.status_code}")
        
        response = r.json()
        print(f"\nResponse: {json.dumps(response, indent=2)}")
        
        # Analyze response
        if r.status_code == 200:
            if response.get("status") == "success":
                print("\n✅ ORDER SUCCESSFUL")
                if "data" in response:
                    order_data = response["data"]
                    if "orderId" in order_data:
                        print(f"   Order ID: {order_data['orderId']}")
            else:
                print("\n❌ ORDER FAILED")
                print(f"   Error: {response.get('message', 'Unknown error')}")
                if "broker" in response:
                    print(f"   Broker Response: {response.get('broker')}")
        else:
            print(f"\n❌ HTTP ERROR: {r.status_code}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def main():
    print("\n" + "#"*70)
    print("#  PRODUCT MAPPING IMPLEMENTATION - TEST SUITE")
    print("#"*70)
    
    # Test 1: Debug endpoint
    test_debug_endpoint()
    
    # Test 2: INTRADAY (should stay INTRA)
    test_futures_webhook("INTRADAY", "INTRADAY → INTRA")
    
    # Test 3: DELIVERY (should map to NORMAL for F&O)
    test_futures_webhook("DELIVERY", "DELIVERY → NORMAL (carry-forward)")
    
    # Test 4: NORMAL (explicit carry-forward)
    test_futures_webhook("NORMAL", "NORMAL (explicit)")
    
    # Test 5: NRML (alias for NORMAL)
    test_futures_webhook("NRML", "NRML → NORMAL (alias)")
    
    print_header("TESTS COMPLETE")
    print("\n📋 NEXT STEPS:")
    print("1. Check the logs in your backend terminal")
    print("2. Look for lines containing 'Product mapping:'")
    print("3. Verify mapped_sdk_product matches expected values")
    print("4. If broker rejects, check the Final broker payload log")
    print("\n💡 Expected log format:")
    print("   Product mapping: product_type(in)=DELIVERY -> mapped_sdk_product=NORMAL -> prod_const=... | segment=NSE_FNO")
    print("\n")

if __name__ == "__main__":
    main()


