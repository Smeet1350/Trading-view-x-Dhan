#!/usr/bin/env python3
"""
Simple test runner for TradingView x Dhan Trading System
Tests all phases sequentially
"""

import subprocess
import sys
import os

def run_tests():
    """Run all tests for all phases"""
    print("🧪 Testing TradingView x Dhan Trading System")
    print("=" * 50)
    
    # Test Phase 0
    print("\n📋 Phase 0: Project Setup & Structure")
    print("-" * 40)
    result0 = subprocess.run([
        sys.executable, "-m", "pytest", 
        "backend/tests/phase_00/", "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    if result0.returncode == 0:
        print("✅ Phase 0: PASSED")
    else:
        print("❌ Phase 0: FAILED")
        print(result0.stdout)
        print(result0.stderr)
    
    # Test Phase 1
    print("\n📋 Phase 1: FastAPI Skeleton & Health Endpoint")
    print("-" * 40)
    result1 = subprocess.run([
        sys.executable, "-m", "pytest", 
        "backend/tests/phase_01/", "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    if result1.returncode == 0:
        print("✅ Phase 1: PASSED")
    else:
        print("❌ Phase 1: FAILED")
        print(result1.stdout)
        print(result1.stderr)
    
    # Test Phase 2
    print("\n📋 Phase 2: Webhook Endpoint & Idempotency")
    print("-" * 40)
    result2 = subprocess.run([
        sys.executable, "-m", "pytest", 
        "backend/tests/phase_02/", "-v", "--tb=short"
    ], capture_output=True, text=True)
    
    if result2.returncode == 0:
        print("✅ Phase 2: PASSED")
    else:
        print("❌ Phase 2: FAILED")
        print(result2.stdout)
        print(result2.stderr)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    phases = [
        ("Phase 0", result0.returncode == 0),
        ("Phase 1", result1.returncode == 0),
        ("Phase 2", result2.returncode == 0)
    ]
    
    passed = sum(1 for _, success in phases if success)
    total = len(phases)
    
    for phase, success in phases:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{phase}: {status}")
    
    print(f"\nOverall: {passed}/{total} phases passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready for production.")
        return 0
    else:
        print("⚠️  Some tests failed. Please review and fix issues.")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
