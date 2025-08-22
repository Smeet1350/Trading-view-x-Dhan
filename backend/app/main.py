"""
TradingView x Dhan Trading System - Main FastAPI Application
Phase 1: Basic FastAPI skeleton with health endpoint and initial API skeleton
"""

from fastapi import FastAPI

# Create FastAPI instance
app = FastAPI(
    title="TradingView x Dhan Trading System",
    description="Low-latency options trading system with Dhan integration - Phase 1",
    version="1.0.0",
)

# Basic endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TradingView x Dhan Trading System",
        "version": "1.0.0",
        "phase": "1",
        "status": "operational"
    }

@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok"
    }

@app.get("/orders")
async def get_orders():
    """Get orders - Phase 1 placeholder"""
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
