#!/usr/bin/env python3
"""
Development server startup script for TradingView x Dhan Trading System
Phase 0: Project Setup & Structure
"""

import uvicorn
import os
import sys

def main():
    """Start the development server"""
    print("🚀 Starting TradingView x Dhan Trading System Development Server")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists("backend/app/main.py"):
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Set default environment variables if not present
    if not os.getenv("WEBHOOK_TOKEN"):
        os.environ["WEBHOOK_TOKEN"] = "dev_webhook_token"
        print("⚠️  Using default WEBHOOK_TOKEN for development")
    
    if not os.getenv("ADMIN_TOKEN"):
        os.environ["ADMIN_TOKEN"] = "dev_admin_token"
        print("⚠️  Using default ADMIN_TOKEN for development")
    
    if not os.getenv("DRY_RUN"):
        os.environ["DRY_RUN"] = "true"
        print("⚠️  DRY_RUN mode enabled (no real trading)")
    
    print("\n📋 Server Configuration:")
    print(f"   Host: 0.0.0.0")
    print(f"   Port: 8000")
    print(f"   Environment: Development")
    print(f"   DRY_RUN: {os.getenv('DRY_RUN', 'true')}")
    
    print("\n🌐 Access URLs:")
    print(f"   API: http://localhost:8000")
    print(f"   Health: http://localhost:8000/healthz")
    print(f"   Docs: http://localhost:8000/docs")
    print(f"   Dashboard: http://localhost:8000/frontend/index.html")
    
    print("\n🔄 Starting server...")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        uvicorn.run(
            "backend.app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
