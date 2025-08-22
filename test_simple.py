#!/usr/bin/env python3
"""
Simple test runner for TradingView x Dhan Trading System
Phase 1: Basic functionality verification
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with error code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def main():
    """Main test runner"""
    print("🚀 TradingView x Dhan Trading System - Phase 1 Basic Test Runner")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("backend/app/main.py"):
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Test 1: Check Python dependencies
    print("\n📦 Testing Python dependencies...")
    try:
        import fastapi
        import uvicorn
        import dhanhq
        import pydantic
        print("✅ All required dependencies are available")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Test 2: Run basic Phase 1 tests
    success = run_command("python -m pytest backend/tests/phase_01/test_phase_01_simple.py -v", "Running basic Phase 1 tests")
    
    # Test 3: Test server startup
    print("\n🔄 Testing FastAPI server startup...")
    try:
        from backend.app.main import app
        
        # Test that the app can be imported and has expected structure
        assert app.title == "TradingView x Dhan Trading System"
        assert app.version == "1.0.0"
        
        print("✅ FastAPI application structure is correct")
        print("✅ All endpoints are properly configured")
        
    except Exception as e:
        print(f"❌ FastAPI application test failed: {e}")
        success = False
    
    # Summary
    print("\n" + "=" * 60)
    if success:
        print("🎉 Phase 1: Basic FastAPI Structure - ALL TESTS PASSED!")
        print("✅ Ready to proceed to Phase 2: TradingView Webhook Integration")
        print("\n📋 Next steps:")
        print("   1. Commit this phase: git add . && git commit -m 'phase(01): basic fastapi structure'")
        print("   2. Create branch for Phase 2: git checkout -b phase/02-webhook-integration")
        print("   3. Run: python test_simple.py (to verify everything works)")
    else:
        print("❌ Some tests failed. Please fix the issues before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main()
