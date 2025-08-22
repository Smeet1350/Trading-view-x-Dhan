"""
Phase 0 Tests: Project Setup & Structure
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestPhase00Setup:
    """Test Phase 0: Project setup and structure"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_project_structure(self):
        """Test that project has correct structure"""
        # Check that main app exists
        assert app is not None
        assert app.title == "TradingView x Dhan Trading System"
        assert app.version == "1.0.0"
    
    def test_health_endpoint(self, client: TestClient):
        """Test that /healthz endpoint returns correct response"""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_root_endpoint(self, client: TestClient):
        """Test that root endpoint returns system information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "TradingView x Dhan Trading System"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"
    
    def test_orders_endpoint(self, client: TestClient):
        """Test that /orders endpoint returns empty list"""
        response = client.get("/orders")
        assert response.status_code == 200
        data = response.json()
        assert data["orders"] == []
    
    def test_dependencies_available(self):
        """Test that required dependencies are available"""
        try:
            import fastapi
            import uvicorn
            import pydantic
            import pytest
            assert True
        except ImportError as e:
            pytest.fail(f"Required dependency not available: {e}")
    
    def test_app_documentation_endpoints(self, client: TestClient):
        """Test that API documentation endpoints are accessible"""
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        # Test Swagger docs
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
