"""
Configuration for TradingView x Dhan Trading System
Phase 1: Basic configuration only
"""

from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings"""
    app_name: str = "TradingView x Dhan Trading System"
    app_version: str = "1.0.0"
    app_phase: str = "1"


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()
