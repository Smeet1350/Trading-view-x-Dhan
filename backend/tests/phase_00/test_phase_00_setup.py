"""
Phase 0 Tests: Project Setup & Structure

Tests to verify:
- Project structure is correct
- Dependencies are available
- Basic FastAPI app can start
- Health endpoint works
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestPhase00Setup:
    """Test Phase 0: Project Setup & Structure"""

    def test_project_structure(self):
        """Test that project structure is correctly set up"""
        # Verify main app can be imported
        assert app is not None
        assert app.title == "TradingView x Dhan Trading System"
        assert app.version == "1.0.0"

    def test_health_endpoint(self, client: TestClient):
        """Test that /healthz endpoint returns correct response"""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["phase"] == "1"

    def test_root_endpoint(self, client: TestClient):
        """Test that root endpoint returns system information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "TradingView x Dhan Trading System"
        assert data["version"] == "1.0.0"
        assert data["phase"] == "1"
        assert data["status"] == "operational"

    def test_orders_endpoint(self, client: TestClient):
        """Test that /orders endpoint returns empty list in Phase 1"""
        response = client.get("/orders")
        assert response.status_code == 200
        data = response.json()
        assert data["orders"] == []
        assert data["phase"] == "1"
        assert "Orders functionality coming in Phase 2" in data["message"]

    def test_cors_middleware(self):
        """Test that CORS middleware is configured"""
        # Verify CORS middleware is added
        middleware_names = [
            middleware.cls.__name__ for middleware in app.user_middleware
        ]
        assert "CORSMiddleware" in middleware_names

    def test_dependencies_available(self):
        """Test that required dependencies can be imported"""
        try:
            # Test that all required dependencies can be imported
            import dhanhq
            import fastapi
            import pydantic
            import uvicorn

            # Verify the imports are working
            assert dhanhq is not None
            assert fastapi is not None
            assert pydantic is not None
            assert uvicorn is not None
        except ImportError as e:
            pytest.fail(f"Required dependency not available: {e}")

    def test_app_documentation_endpoints(self, client: TestClient):
        """Test that documentation endpoints are accessible"""
        # Test OpenAPI docs
        response = client.get("/docs")
        assert response.status_code == 200

        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
