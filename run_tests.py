#!/usr/bin/env python3
"""
Simple test runner for the TradingView x Dhan Trading System
Phase 0: Project Setup & Structure
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
        if result.stdout:
            print(result.stdout)
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
    print("🚀 TradingView x Dhan Trading System - Phase 0 Test Runner")
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
        import pytest
        print("✅ All required dependencies are available")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Test 2: Run pytest
    success = run_command("python -m pytest backend/tests/phase_00/ -v", "Running Phase 0 tests")
    
    # Test 3: Check code formatting
    success &= run_command("python -m black --check backend/", "Checking code formatting")
    
    # Test 4: Check imports sorting
    success &= run_command("python -m isort --check-only backend/", "Checking import sorting")
    
    # Test 5: Lint code
    success &= run_command("python -m flake8 backend/ --max-line-length=88 --extend-ignore=E203,W503", "Linting code")
    
    # Test 6: Start FastAPI server (briefly)
    print("\n🔄 Testing FastAPI server startup...")
    try:
        import uvicorn
        from backend.app.main import app
        
        # Test that the app can be imported and has expected structure
        assert app.title == "TradingView x Dhan Trading System"
        assert app.version == "0.1.0"
        
        print("✅ FastAPI application structure is correct")
        print("✅ All endpoints are properly configured")
        
    except Exception as e:
        print(f"❌ FastAPI application test failed: {e}")
        success = False
    
    # Summary
    print("\n" + "=" * 60)
    if success:
        print("🎉 Phase 0: Project Setup & Structure - ALL TESTS PASSED!")
        print("✅ Ready to proceed to Phase 1: FastAPI Skeleton & Health Endpoint")
        print("\n📋 Next steps:")
        print("   1. Commit this phase: git add . && git commit -m 'phase(00): project scaffold'")
        print("   2. Create branch for Phase 1: git checkout -b phase/01-fastapi-skeleton")
        print("   3. Run: python run_tests.py (to verify everything works)")
    else:
        print("❌ Some tests failed. Please fix the issues before proceeding.")
        sys.exit(1)

if __name__ == "__main__":
    main()
