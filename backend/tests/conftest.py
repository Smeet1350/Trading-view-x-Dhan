"""
Pytest configuration and fixtures for the trading system tests.

This file provides common test setup and fixtures used across all test phases.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI application"""
    return TestClient(app)


@pytest.fixture
def app_instance():
    """FastAPI application instance for testing"""
    return app
