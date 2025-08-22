"""
Simple Phase 1 Tests: Basic FastAPI functionality
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestPhase01Basic:
    """Test Phase 1: Basic functionality"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "TradingView x Dhan Trading System"
        assert data["version"] == "1.0.0"
        assert data["phase"] == "1"
        assert data["status"] == "operational"
    
    def test_healthz_endpoint(self, client):
        """Test healthz endpoint - should return {status: 'ok'}"""
        response = client.get("/healthz")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
    
    def test_orders_endpoint(self, client):
        """Test orders endpoint - should return empty list"""
        response = client.get("/orders")
        assert response.status_code == 200
        
        data = response.json()
        assert "orders" in data
        assert data["orders"] == []
