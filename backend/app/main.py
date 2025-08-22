"""
TradingView x Dhan Trading System - Main FastAPI Application

This is the main entry point for the FastAPI application.
Phase 0: Basic structure only - no business logic yet.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI instance
app = FastAPI(
    title="TradingView x Dhan Trading System",
    description="Low-latency options trading system with Dhan integration",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Phase 0: Basic endpoints only
@app.get("/")
async def root():
    """Root endpoint - system status"""
    return {
        "message": "TradingView x Dhan Trading System",
        "version": "0.1.0",
        "phase": "0",
        "status": "initialized",
    }


@app.get("/healthz")
async def health_check():
    """Health check endpoint for monitoring and deployment"""
    return {"status": "ok", "phase": "0"}


@app.get("/orders")
async def get_orders():
    """Get orders - Phase 0: returns empty list"""
    return []


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
