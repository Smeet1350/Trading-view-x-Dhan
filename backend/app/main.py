"""
TradingView x Dhan Trading System - Main FastAPI Application
Phase 2: Webhook ingestion + idempotency
"""

from fastapi import FastAPI

from .api.webhook import router as webhook_router

# Create FastAPI instance
app = FastAPI(
    title="TradingView x Dhan Trading System",
    description="Low-latency options trading system with Dhan integration - Phase 2",
    version="1.0.0",
)

# Include API routers
app.include_router(webhook_router)

# Basic endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TradingView x Dhan Trading System",
        "version": "1.0.0",
        "phase": "2",
        "status": "operational",
        "features": [
            "TradingView webhook integration",
            "Alert idempotency with SHA256 hashing",
            "SQLite alert storage"
        ]
    }

@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok"
    }

@app.get("/orders")
async def get_orders():
    """Get orders - Phase 2 placeholder"""
    return {
        "orders": []
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
